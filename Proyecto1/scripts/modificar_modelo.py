#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Modifica el modelo de estructura y re-exporta los resultados a Unity.

Este script es el punto UNICO para cambiar la geometria/estructura y que
los esfuerzos internos y las cargas tributarias se recalculen bien:

    - Quitar vigas/columnas (por elementTag, id o tipo+piso)
    - Cambiar dimensiones de seccion (width_m / height_m)
    - Mover nodos (cambia longitudes de los elementos conectados)
    - Cambiar/quitar apoyos (restricciones por nodo)
    - Redistribuir el area tributaria de un vano eliminado a las vigas
      vecinas del mismo piso (opcional, activado por bandera)

El modelo fuente es Proyecto1/data/estructura_completo_unity.json.
Despues de aplicar los cambios, ejecuta exportar_resultados_unity.py, que
corre OpenSees para las cargas G/Q/EX/EY + combos C1/C2/C3 y regenera
edificio_G4/Assets/Resources/estructura_p1l4_unity.json (el JSON que Unity
lee y visualiza: geometria, deformada, diagramas, punto P-M).

Uso:
    python modificar_modelo.py            # aplica las EDICIONES de abajo y re-exporta
    python modificar_modelo.py --dry-run  # aplica y guarda el modelo, pero NO exporta
    python modificar_modelo.py --restore  # restaura el JSON base desde el backup .bak
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# ── Rutas ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
JSON_BASE = ROOT_DIR / "data" / "estructura_completo_unity.json"
JSON_BACKUP = JSON_BASE.with_suffix(".json.bak")
EXPORTER = BASE_DIR / "exportar_resultados_unity.py"

# Secciones validas para cambiar_seccion()
SECCIONES = {
    "V60/80": (0.60, 0.80),
    "V40/80": (0.40, 0.80),
    "V30/80": (0.30, 0.80),
    "V30/45": (0.30, 0.45),
    "COL70/70": (0.70, 0.70),
}


# ──────────────────────────────────────────────────────────────────────
#  AYUDA PARA BUSCAR QUE QUITAR
# ──────────────────────────────────────────────────────────────────────
def ejemplo_tags_y_pisos():
    """Imprime un listado util para elegir que elemento editar."""
    data = load_json(JSON_BASE)
    por_tipo = {}
    for e in data["elements"]:
        por_tipo.setdefault(e.get("type", "?"), []).append(e)
    for t, elems in por_tipo.items():
        tags = [e.get("elementTag") for e in elems[:6]]
        pisos = sorted({e.get("piso", "?") for e in elems})
        secs = sorted({e.get("sectionId", "?") for e in elems})
        print(f"[{t}] x{len(elems)}  tags(ej): {tags}")
        print(f"  pisos: {pisos}")
        print(f"  secciones: {secs}")
    print(f"[slabs] x{len(data.get('slabs', []))}")
    listar_lozas(data)


# ── Carga / guardado ─────────────────────────────────────────────────
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)


def _match(e, tag=None, elem_id=None, tipo=None, piso=None):
    if tag is not None and e.get("elementTag") != tag:
        return False
    if elem_id is not None and int(e.get("id", -1)) != int(elem_id):
        return False
    if tipo is not None and e.get("type") != tipo:
        return False
    if piso is not None and e.get("piso") != piso:
        return False
    return True


def find_elements(data, tag=None, elem_id=None, tipo=None, piso=None):
    return [e for e in data["elements"] if _match(e, tag, elem_id, tipo, piso)]


def show(e, extra=""):
    print(
        f"    - id={e.get('id')} tag={e.get('elementTag')} "
        f"({e.get('type')}) {e.get('nodeI')}->{e.get('nodeJ')} "
        f"{e.get('sectionId')} piso={e.get('piso')} {extra}".strip()
    )


# ── Operaciones de modificacion ───────────────────────────────────────
def quitar_elemento(data, tag=None, elem_id=None, tipo=None, piso=None,
                    redistribuir=True, dry=False):
    """Elimina elementos del modelo. Si redistribuir=True, reparte el area
    tributaria de cada elemento eliminado entre las vigas del MISMO piso
    que comparten apoyo (heuristica de vano eliminado)."""
    matches = find_elements(data, tag, elem_id, tipo, piso)
    if not matches:
        print(f"  AVISO: no se encontro ningun elemento con tag={tag} id={elem_id} "
              f"tipo={tipo} piso={piso}")
        return 0

    eliminados_ids = set()
    for e in matches:
        eliminados_ids.add(int(e["id"]))
        print(f"  Quitando elemento {e.get('elementTag')} (id={e['id']}, {e.get('type')}, {e.get('sectionId')})")
        if not dry:
            if redistribuir:
                repartir_area_eliminada(data, e)
    if dry:
        return len(matches)

    data["elements"] = [e for e in data["elements"] if int(e["id"]) not in eliminados_ids]
    return len(matches)


def repartir_area_eliminada(data, elemento):
    """Reparte areaTributaria/loads de 'elemento' hacia vigas del mismo piso
    con el MAESTRO comun mas cercano (por nodoI/nodoJ). Si no hay vecina,
    el area simplemente deja de transferirse (la losa queda sin apoyo)."""
    if elemento.get("type") != "viga":
        return
    vecinas = set()
    for nd in (elemento.get("nodeI"), elemento.get("nodeJ")):
        for e in data["elements"]:
            if e.get("type") != "viga":
                continue
            if e.get("piso") != elemento.get("piso"):
                continue
            if e is elemento or int(e["id"]) == int(elemento["id"]):
                continue
            if nd in (e.get("nodeI"), e.get("nodeJ")):
                vecinas.add(int(e["id"]))
    if not vecinas:
        return
    n = len(vecinas)
    cargas = {
        "areaTributaria": float(elemento.get("areaTributaria") or 0.0),
        "deadLoad": float(elemento.get("deadLoad") or 0.0),
        "liveLoad": float(elemento.get("liveLoad") or 0.0),
        "uniformLoad": float(elemento.get("uniformLoad") or 0.0),
        "cargaTributaria": float(elemento.get("cargaTributaria") or 0.0),
        "factoredLoad14D": float(elemento.get("factoredLoad14D") or 0.0),
        "factoredLoad12D16L": float(elemento.get("factoredLoad12D16L") or 0.0),
        "gravityLoad": float(elemento.get("gravityLoad") or 0.0),
    }
    for e in data["elements"]:
        if int(e["id"]) in vecinas:
            for k, v in cargas.items():
                if k in e:
                    e[k] = float(e.get(k) or 0.0) + v / n
    print(f"  Repartida tributaria (/{n}): {sorted(vecinas)}")


def cambiar_seccion(data, tag=None, elem_id=None, tipo=None, seccion=None,
                    width_m=None, height_m=None, dry=False):
    """Cambia las dimensiones de seccion de elementos. Se puede dar:
       - seccion: nombre conocido ('V60/80', 'COL70/70', ...) o
       - width_m/height_m: dimensiones libres (m).
    OJO: cambiar la seccion modifica la RIGIDEZ; el area tributaria y las
    cargas de la viga se conservan (la losa sigue siendo la misma)."""
    if seccion and seccion not in SECCIONES:
        raise ValueError(
            f"Seccion '{seccion}' no reconocida. Usa una de: {sorted(SECCIONES)} "
            "o pasa width_m/height_m directo."
        )
    if seccion:
        width_m, height_m = SECCIONES[seccion]
    w = width_m or 0.60
    h = height_m or 0.80
    matches = find_elements(data, tag, elem_id, tipo)
    if not matches:
        print(f"  AVISO: sin elementos tag={tag} id={elem_id} tipo={tipo}")
        return 0
    for e in matches:
        print(f"  Seccion {e.get('elementTag')}: {e.get('width_m')}x{e.get('height_m')}"
              f" -> {w}x{h}")
        if not dry:
            e["width_m"] = w
            e["height_m"] = h
            if seccion:
                e["sectionId"] = seccion
    return len(matches)


def mover_nodo(data, node_id, x=None, y=None, z=None, dry=False):
    """Mueve un nodo a las coordenadas dadas (None = no cambia). Los
    elementos conectados cambian de longitud automaticamente."""
    for n in data["nodes"]:
        if int(n["id"]) != int(node_id):
            continue
        old = (n["x"], n["y"], n["z"])
        if x is not None:
            n["x"] = float(x)
        if y is not None:
            n["y"] = float(y)
        if z is not None:
            n["z"] = float(z)
        print(f"  Nodo {node_id}: {old} -> ({n['x']}, {n['y']}, {n['z']})")
        return 1 if not dry else 0
    print(f"  AVISO: nodo {node_id} no existe.")
    return 0


def apoyos_predefinidos(tipo):
    fixed = {"type": "fixed", "ux": 1, "uy": 1, "uz": 1, "rx": 1, "ry": 1, "rz": 1}
    pinned = {"type": "pinned", "ux": 1, "uy": 1, "uz": 1, "rx": 0, "ry": 0, "rz": 0}
    roller = {"type": "roller", "ux": 0, "uy": 0, "uz": 1, "rx": 0, "ry": 0, "rz": 0}
    if tipo == "fixed":
        return dict(fixed)
    if tipo == "pinned":
        return dict(pinned)
    if tipo == "roller":
        return dict(roller)
    raise ValueError("tipo de apoyo: 'fixed' | 'pinned' | 'roller'")


def cambiar_apoyo(data, node_id, tipo=None, ux=None, uy=None, uz=None,
                  rx=None, ry=None, rz=None, dry=False):
    """Cambia restricciones de apoyo de un nodo. Con 'tipo' se usan
    plantillas (fixed/pinned/roller); tambien se pueden dar grados sueltos."""
    for a in data["supports"]:
        if int(a.get("node", -1)) != int(node_id):
            continue
        if tipo:
            pre = apoyos_predefinidos(tipo)
            print(f"  Apoyo nodo {node_id}: {a.get('type')} -> {tipo}")
            if not dry:
                a.update(pre)
                return 1
        else:
            print(f"  Apoyo nodo {node_id}: {a}")
            if not dry:
                for k, v in {"ux": ux, "uy": uy, "uz": uz,
                             "rx": rx, "ry": ry, "rz": rz}.items():
                    if v is not None:
                        a[k] = int(v)
                return 1
        return 0
    print(f"  AVISO: no hay apoyo en nodo {node_id}.")
    return 0


def quitar_apoyo(data, node_id, dry=False):
    """Elimina el apoyo de un nodo (el nodo queda libre)."""
    antes = len(data["supports"])
    data["supports"] = [a for a in data["supports"] if int(a.get("node", -1)) != int(node_id)]
    despues = len(data["supports"])
    print(f"  Apoyos: {antes} -> {despues} (nodo {node_id})")
    return 0 if dry else (antes - despues)


# ── Losas (slabs) ─────────────────────────────────────────────────────
def listar_lozas(data):
    """Lista las lozas del modelo agrupadas por piso, con su area."""
    lozas = data.get("slabs", [])
    if not lozas:
        print("  No hay lozas (slabs) en el modelo.")
        return
    por_piso = {}
    for s in lozas:
        por_piso.setdefault(s.get("nivel", "?"), []).append(s)
    for nivel, items in por_piso.items():
        area_piso = 0.0
        for s in items:
            area_piso += abs(float(s.get("x1", 0)) - float(s.get("x0", 0))) * abs(float(s.get("y1", 0)) - float(s.get("y0", 0)))
        print(f"  [{nivel}] {len(items)} lozas ({area_piso:.1f} m2):")
        for s in items:
            x0, y0, x1, y1 = s.get("x0"), s.get("y0"), s.get("x1"), s.get("y1")
            area = abs(float(x1) - float(x0)) * abs(float(y1) - float(y0))
            print(f"    - {s.get('id')}: x[{x0},{x1}] y[{y0},{y1}]  A={area:.2f} m2")


def _nodos_dict(data):
    return {n["id"]: n for n in data.get("nodes", [])}


def _viga_en_borde(viga, nodos, slab, tol=1e-4):
    """Devuelve la longitud del tramo de 'viga' que coincide con un borde
    del rectangulo de 'slab' (en metros), o 0 si no coincide con ninguno.
    Una viga solo recibe tributaria de una losa si esta co-lineal con un
    lado del rectangulo y a la altura (z) y piso de la loza."""
    ni = nodos.get(viga.get("nodeI"))
    nj = nodos.get(viga.get("nodeJ"))
    if not ni or not nj:
        return 0.0
    x0, y0 = float(slab.get("x0")), float(slab.get("y0"))
    x1, y1 = float(slab.get("x1")), float(slab.get("y1"))
    tol_area = 1e-6
    if abs(x1 - x0) <= tol_area or abs(y1 - y0) <= tol_area:
        return 0.0
    ax, ay = ni["x"], ni["y"]
    bx, by = nj["x"], nj["y"]
    # viga vertical (x cte): coincide con borde vertical x0 o x1
    if abs(ax - bx) < tol:
        for xborde in (x0, x1):
            if abs(ax - xborde) < tol:
                lo = max(min(ay, by), y0)
                hi = min(max(ay, by), y1)
                if hi > lo:
                    return hi - lo
    # viga horizontal (y cte): coincide con borde horizontal y0 o y1
    if abs(ay - by) < tol:
        for yborde in (y0, y1):
            if abs(ay - yborde) < tol:
                lo = max(min(ax, bx), x0)
                hi = min(max(ax, bx), x1)
                if hi > lo:
                    return hi - lo
    return 0.0


def quitar_loza(data, slab_id, dry=False):
    """Quita UNA loza especifica (ej: 'L1') y recalcula la tributaria.

    Efectos:
      1. La loza deja de dibujarse en Unity (se elimina de 'slabs').
      2. Las vigas perimetrales que la soportaban pierden la franja de
         MEDIA LUZ que recibian de esa loza (regla verificada con el
         modelo real: la viga del borde t.llevaba exactamente
         (luz/2) x longitud, p.ej. L1 de 29.37 m2 -> v225 tomo 14.685).
      3. El area total del piso en tributaryList baja proporcionalmente.

    NOTA: si una loza no tiene viga en alguno de sus lados (borde libre o
    apoyado en otra cosa), el area de ese lado NO se resta de ninguna viga
    y simplemente desaparece con la losa. El cambio se imprime en consola
    para que puedas revisarlo."""
    lozas = data.get("slabs", [])
    slab = next((s for s in lozas if str(s.get("id")) == str(slab_id)), None)
    if slab is None:
        print(f"  AVISO: loza '{slab_id}' no encontrada en slabs.")
        return 0

    nivel = slab.get("nivel", "")
    x0, y0 = float(slab.get("x0")), float(slab.get("y0"))
    x1, y1 = float(slab.get("x1")), float(slab.get("y1"))
    area_slab = abs(x1 - x0) * abs(y1 - y0)
    print(f"  Quitando LOZA {slab_id} (nivel={nivel}) x[{x0},{x1}] y[{y0},{y1}]  A={area_slab:.2f} m2")

    nodos = _nodos_dict(data)
    restado_total = 0.0
    for e in data.get("elements", []):
        if e.get("type") != "viga":
            continue
        if e.get("piso") != nivel:
            continue
        tramo = _viga_en_borde(e, nodos, slab)
        if tramo <= 0.0:
            continue

        # franja tributaria de media luz: (luz perpendicular al borde)/2 x tramo
        na, nb = nodos[e["nodeI"]], nodos[e["nodeJ"]]
        if abs(na["x"] - nb["x"]) < 1e-4:   # viga vertical: la franja se mide en x
            luz = abs(x1 - x0)
        else:                                # viga horizontal: la franja se mide en y
            luz = abs(y1 - y0)
        franja = 0.5 * luz * tramo

        antes = float(e.get("areaTributaria") or 0.0)
        nuevo = max(0.0, antes - franja)
        restado_total += antes - nuevo
        print(f"    Viga {e.get('elementTag')} (id={e.get('id')}, borde co-lineal {tramo:.2f} m): "
              f"A_trib {antes:.2f} -> {nuevo:.2f} m2  (-{antes - nuevo:.2f})")
        if not dry:
            if "areaTributaria" in e:
                e["areaTributaria"] = nuevo
            # las cargas derivadas se escalan (unicamente si cambia el area)
            if antes > 0.0:
                ratio = nuevo / antes
                for campo in ("cargaTributaria", "uniformLoad", "deadLoad", "liveLoad",
                              "factoredLoad14D", "factoredLoad12D16L", "gravityLoad"):
                    if campo in e and isinstance(e[campo], (int, float)):
                        e[campo] = float(e[campo]) * ratio
                # los lados tributarios conservados se re-escalan igual
                for ed in e.get("sourceEdges", []):
                    if isinstance(ed, dict) and isinstance(ed.get("tributary_area_m2"), (int, float)):
                        ed["tributary_area_m2"] = float(ed["tributary_area_m2"]) * ratio

    if not dry:
        data["slabs"] = [s for s in lozas if str(s.get("id")) != str(slab_id)]
        # ajusta los totales por piso (tributaryList Y tributaryAreasByFloor)
        # restando del piso el area de la losa que dejo de existir
        for clave in ("tributaryList", "tributaryAreasByFloor"):
            for t in data.get(clave, []):
                if t.get("piso") == nivel:
                    viejo_area = float(t.get("area_total") or 0.0)
                    viejo_carga = float(t.get("carga_total") or 0.0)
                    t["area_total"] = max(0.0, viejo_area - area_slab)
                    if viejo_area > 0.0:
                        t["carga_total"] = max(0.0, viejo_carga * (t["area_total"] / viejo_area))
                    print(f"    {clave} [{nivel}]: area_total {viejo_area:.2f} -> {t['area_total']:.2f}")

    print(f"  Area tributaria restada a vigas: {restado_total:.2f} m2 "
          f"(loza {area_slab:.2f} m2; diferencia = bordes sin viga / no transferidos)")
    return 1


def resumen(data):
    n = len(data["nodes"])
    e = len(data["elements"])
    apoyos = len(data["supports"])
    vigas = sum(1 for x in data["elements"] if x.get("type") == "viga")
    cols = sum(1 for x in data["elements"] if x.get("type") == "columna")
    lozas = len(data.get("slabs", []))
    print(f"  Modelo: {n} nodos | {e} elementos "
          f"(vigas={vigas}, columnas={cols}) | {apoyos} apoyos | {lozas} lozas")


# ──────────────────────────────────────────────────────────────────────
#  EDICIONES DEL MODELO
# ──────────────────────────────────────────────────────────────────────
# AQUI se declaran los cambios. Cada linea es una operacion. Ejemplos:
#
#   quitar_elemento(data, tag="E1_5")                      # quita UNA viga
#   quitar_elemento(data, tipo="viga", piso="CIELO_2")     # quita TODAS las vigas de un piso
#   quitar_elemento(data, elem_id=229, redistribuir=False) # quita una columna sin repartir
#   quitar_loza(data, "L1")                                # quita UNA losa (+ recalcula tributaria perimetral)
#   cambiar_seccion(data, tag="E1_10", seccion="V30/45")   # adelgaza una viga
#   cambiar_seccion(data, tipo="columna", seccion="COL70/70")
#   mover_nodo(data, node_id=25, z=12.0)                   # sube un nodo
#   cambiar_apoyo(data, node_id=7, tipo="pinned")
#   cambiar_apoyo(data, node_id=8, uz=0)                   # suelta vertical
#   quitar_apoyo(data, node_id=9)
#   listar_lozas(data)                                     # lista los lozas por piso
def aplicar_ediciones(data, dry=False):
    print("\n── Aplicando ediciones al modelo ──")
    resumen(data)

    # === EDITAR DESDE AQUI ===
    quitar_elemento(data, tag="E1_5")
    # quitar_elemento(data, tipo="viga", piso="CIELO_2")
    # quitar_loza(data, "L1")
    # cambiar_seccion(data, tag="E1_10", seccion="V30/45")
    # mover_nodo(data, node_id=25, z=12.0)
    # cambiar_apoyo(data, node_id=7, tipo="pinned")
    # quitar_apoyo(data, node_id=9)
    # === FIN DE EDICIONES ===

    resumen(data)


# ── Orquestacion ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Modificar el modelo y re-exportar a Unity.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo imprimir resumen y guardar backup, sin exportar.")
    parser.add_argument("--restore", action="store_true",
                        help="Restaurar JSON_BASE desde el backup .bak.")
    parser.add_argument("--ejemplo", action="store_true",
                        help="Listar tags/pisos/secciones disponibles.")
    args = parser.parse_args()

    if args.ejemplo:
        ejemplo_tags_y_pisos()
        return

    if args.restore:
        if not JSON_BACKUP.exists():
            print("No hay backup .bak. No se restaura nada.")
            return
        shutil.copyfile(JSON_BACKUP, JSON_BASE)
        print(f"Restaurado {JSON_BASE} desde {JSON_BACKUP.name}")
        return

    if not JSON_BASE.exists():
        print(f"No existe {JSON_BASE}")
        return

    # Backup la primera vez
    if not JSON_BACKUP.exists():
        shutil.copyfile(JSON_BASE, JSON_BACKUP)
        print(f"Backup inicial creado: {JSON_BACKUP.name}")

    data = load_json(JSON_BASE)
    aplicar_ediciones(data, dry=args.dry_run)

    if args.dry_run:
        print("\n[dry-run] No se guarda el modelo ni se exporta.")
        return

    write_json(JSON_BASE, data)
    print(f"Modelo guardado en {JSON_BASE}")

    print("\n── Re-exportando resultados (OpenSees) ──")
    py = sys.executable
    if shutil.which("python"):
        py = "python"
    cmd = [py, str(EXPORTER)]
    print("  " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(BASE_DIR))
    if r.returncode != 0:
        sys.exit(r.returncode)
    print("\nListo. Unity (Assets/Resources/estructura_p1l4_unity.json) "
          "ya tiene los resultados recalculados.")


if __name__ == "__main__":
    main()