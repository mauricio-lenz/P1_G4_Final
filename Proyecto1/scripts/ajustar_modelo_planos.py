#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ajusta el modelo (estructura_completo_unity.json) a los planos DXF.

Correcciones detectadas al superponer las plantas y elevaciones
estructurales (Planos_1_dxf: 2017_67 = edificio_1, 2024_22 = edificio_2)
con el modelo. La base del modelo (grilla, secciones tipo V60/80 y
COL70/70) coincide con los planos; aqui se corrigen detalles:

  1. edificio_2 estaba reflejado en Y respecto del plano 2024_22
     (y_modelo = 1.65 - y_plano): el eje 2 quedaba en y=1.65 en vez de y=0
     y el nucleo del ascensor al sur en vez de al norte.
  2. Muro de borde en eje A' (edificio_2, eje 3 tras reflejar) llega a
     x=-39.625 (L=1.85), igual que el del eje 1.
  3. Muros del edificio_1: los nodos estaban en la cota SUPERIOR del piso,
     pero Unity y el exportador los tratan como base -> se bajan un piso.
  4. Nucleo norte edificio_1 (ejes Ea/Ed): muros laterales e=30 (no 25) y
     llegan hasta y=2.57 (plano 2017_67-101/102/103).
  5. Muros faltantes edificio_1: muro e=20 sobre eje 1'' entre E y el
     nucleo (todos los pisos), muros perimetrales del subterraneo (ejes E,
     F, 3 y 1) y muros del piso 1 (eje E, eje I y eje 1 entre H e I').
  6. Secciones de vigas: eje x=37.55 en CIELO_3/CIELO_4 es V.40/60 y la
     viga de borde y=-9.71 (CIELO_2, G-H) es V.30/45.
  7. Altura de piso 3.96 m (niveles -7.97 / -4.01 / -0.05 / +3.91 / +7.87 /
     +11.83 de los planos, con z=0 en el cielo 1S) en ambos edificios.
  8. Subterraneo del edificio_2: el piso bajo el cielo 1S estaba reducido a
     0.15 m; se extiende hasta el radier (-7.97, plano 2024_22-100).
  9. Pilares metalicos P.M. 300x300x20 (voladizos y zona I'-J) y arriostres
     V.M. 300x300x5 segun elevaciones 2017_67-800/801/802.
 10. Vigas secundarias del edificio_2 que llegaban a mitad de otra viga sin
     nodo comun: se parte la viga principal para conectarlas.
 11. Edificio_2: extremos de vigas apoyados en muros sin pilar (ejes A' y
     D'): columnas equivalentes de gravedad.
 12. Losas L91-L94 de la zona I'-J (pisos 3 y 4) cargan a sus vigas.
 13. Losas en voladizo: borde norte (eje 1) de ambos edificios y bordes sur
     y este de la zona I'-J en los pisos 3 y 4; su area tributaria se suma
     a las vigas de borde.
 14. Muros en el analisis: cada pano (un piso) como columna ancha equivalente
     (A = t*L, I en el plano t*L^3/12) unida por brazos rigidos a los nodos del
     marco sobre la linea del muro y empotrada en la fundacion. Reemplaza a las
     columnas equivalentes de gravedad del paso 11.
 15. E1_255 (eje 3, x=7.51, piso 2) es pilar metalico P.M. 300x300x20 sobre
     vigas (plano 2017_67-102), no columna COL70/70.
 16. Reparto tributario recalculado desde las losas (metodo b/a): cada borde de
     losa carga las vigas o brazos rigidos de muro que lo cubren, y la parte de
     un borde libre pasa a los bordes apoyados del mismo panel. Antes ~1600 m2
     de losa (vigas intermedias del edificio_2, bordes sobre muros) no cargaban.
     El paso 14 indexa los nodos por edificio: los muros de ambos lados de la
     junta (linea x = -10) ya no comparten nodos.

El script siempre parte del respaldo previo a los ajustes, por lo que se
puede volver a ejecutar sin duplicar cambios.

Uso:
    python ajustar_modelo_planos.py            # aplica, guarda y re-exporta a Unity
    python ajustar_modelo_planos.py --dry-run  # solo muestra el resumen
    python ajustar_modelo_planos.py --restore  # vuelve al JSON previo a los ajustes
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
JSON_BASE = ROOT_DIR / "data" / "estructura_completo_unity.json"
JSON_BACKUP = ROOT_DIR / "data" / "estructura_completo_unity.pre_planos.json"
EXPORTER = BASE_DIR / "exportar_resultados_unity.py"
MARCA = "ajustesPlanos"

# Eje de reflexion del edificio_2: y_plano = E2_MIRROR - y_modelo
E2_MIRROR = 1.65

# Cotas originales del edificio_1 por nombre de nivel (antes del paso 7)
E1_Z = {"FOUNDATION": -4.0, "CIELO_1S": 0.0, "CIELO_1": 4.0,
        "CIELO_2": 8.0, "CIELO_3": 12.0, "CIELO_4": 16.0}
E1_STOREYS = [("FOUNDATION", "CIELO_1S"), ("CIELO_1S", "CIELO_1"),
              ("CIELO_1", "CIELO_2"), ("CIELO_2", "CIELO_3"),
              ("CIELO_3", "CIELO_4")]

# Paso 7-8: cota original -> cota con pisos de 3.96 m (z=0 en cielo 1S).
# Edificio_1 usaba pisos de 4.00 m; edificio_2 los reales desplazados +4.17
# y con el subterraneo reducido a 0.01 -> 0.16.
H_PISO = 3.96
Z_NUEVA = {
    -4.0: -H_PISO, 0.0: 0.0, 4.0: H_PISO, 8.0: 2 * H_PISO, 12.0: 3 * H_PISO, 16.0: 4 * H_PISO,
    0.01: -H_PISO, 0.16: 0.0, 4.12: H_PISO, 8.08: 2 * H_PISO, 12.04: 3 * H_PISO,
}
Z_NIVEL = {"CIELO_1S": 0.0, "CIELO_1": H_PISO, "CIELO_2": 2 * H_PISO,
           "CIELO_3": 3 * H_PISO, "CIELO_4": 4 * H_PISO}
E2_Z_ORIGINAL = {0.01, 0.16, 4.12, 8.08, 12.04}
E2_WALL_LABELS = {"E2_Z-4.16": "E2_Z-7.97"}

# Muros nuevos del edificio_1: (bottom, top, (x0, y0), (x1, y1), espesor)
MUROS_NUEVOS = [
    # Subterraneo (bajo CIELO_1S), plano 2017_67-101 planta cielo 1S
    ("FOUNDATION", "CIELO_1S", (-10.0, -7.25), (-10.0, 0.0), 0.20),
    ("FOUNDATION", "CIELO_1S", (-10.0, 2.57), (-10.0, 8.9), 0.20),
    ("FOUNDATION", "CIELO_1S", (0.0, -7.25), (0.0, 0.0), 0.30),
    ("FOUNDATION", "CIELO_1S", (0.0, 0.0), (0.0, 8.9), 0.30),
    ("FOUNDATION", "CIELO_1S", (-10.0, -7.25), (0.0, -7.25), 0.30),
    ("FOUNDATION", "CIELO_1S", (-10.0, 8.9), (-5.32, 8.9), 0.20),
    ("FOUNDATION", "CIELO_1S", (-3.52, 8.9), (0.0, 8.9), 0.20),
    # Piso 1 (bajo CIELO_1), plano 2017_67-101 planta cielo piso 1
    ("CIELO_1S", "CIELO_1", (-10.0, -7.25), (-10.0, 0.0), 0.20),
    ("CIELO_1S", "CIELO_1", (30.0, -7.25), (30.0, 0.0), 0.30),
    ("CIELO_1S", "CIELO_1", (30.0, 0.0), (30.0, 8.9), 0.30),
    ("CIELO_1S", "CIELO_1", (20.0, 8.9), (30.0, 8.9), 0.30),
    ("CIELO_1S", "CIELO_1", (30.0, 8.9), (35.0, 8.9), 0.30),
] + [
    # Muro e=20 sobre eje 1'' (y=5.0) entre eje E y el nucleo, pisos 1 a 4
    (bottom, top, (-10.0, 5.0), (-6.7, 5.0), 0.20)
    for bottom, top in E1_STOREYS[1:]
]

# Nucleo norte edificio_1: muros laterales x=-6.7 / x=-3.3 desde y=5.0
NUCLEO_Y_TOP = 5.0
NUCLEO_Y_OLD = 3.425
NUCLEO_Y_NEW = 2.57
NUCLEO_E = 0.30

CAMBIOS_SECCION = {
    "E1_191": "V40/60", "E1_192": "V40/60",
    "E1_201": "V40/60", "E1_202": "V40/60",
    "E1_221": "V30/45",
}
SECCIONES = {"V40/60": (0.40, 0.60), "V30/45": (0.30, 0.45)}


def perfil_cajon(b, t):
    """Propiedades de un perfil cajon cuadrado b x b x t [m]."""
    bi = b - 2.0 * t
    area = b * b - bi * bi
    inercia = (b ** 4 - bi ** 4) / 12.0
    bm = b - t                       # linea media
    torsion = 4.0 * (bm * bm) ** 2 * t / (4.0 * bm)   # Bredt: 4 Am^2 t / perimetro
    return {"A_m2": area, "Iy_m4": inercia, "Iz_m4": inercia, "J_m4": torsion}


PERFILES_ACERO = {
    "PM300x300x20": (0.30, 0.020),   # pilar metalico P.M. 300x300x20
    "VM300x300x5": (0.30, 0.005),    # arriostre V.M. 300x300x5
}

# Paso 9: pilares P.M. 300x300x20 (plantas 2017_67-102/103, elevaciones 800-802)
PILARES_METALICOS = ["E1_241", "E1_254",                      # voladizo piso 2 (F y x=7.51)
                     "E1_255",                                # eje 3 x=7.51, piso 2 (plano 102: P.M. 300x300x20 sobre vigas)
                     "E1_304", "E1_305", "E1_306",            # x=37.55, piso 4
                     "E1_307", "E1_308", "E1_309",            # eje J, piso 4
                     "E1_310", "E1_311"]                      # voladizo piso 4 (G y H)

# Arriostres V.M. 300x300x5: (nivel inferior, nivel superior, extremo I, extremo J)
# con extremos (x, y, "inf"|"sup").
Y_EJES_123 = (8.9, 0.0, -7.25)
ARRIOSTRES = (
    # Elevacion viga 112 (2017_67-802): desde la punta del voladizo arriba
    # hasta el pilar del eje 3 abajo, piso 2 (x=0 y x=7.51)
    [("CIELO_1", "CIELO_2", (x, -11.37, "sup"), (x, -7.25, "inf")) for x in (0.0, 7.51)]
    # Elevacion eje F-G-H (2017_67-801): desde la punta abajo hasta el pilar
    # del eje 3 arriba, piso 4 (ejes G y H)
    + [("CIELO_3", "CIELO_4", (x, -11.37, "inf"), (x, -7.25, "sup")) for x in (10.0, 20.0)]
    # Elevacion eje 1-2-3 (2017_67-800): V invertida entre I' y J, piso 4
    + [("CIELO_3", "CIELO_4", (35.0, y, "inf"), (37.55, y, "sup")) for y in Y_EJES_123]
    + [("CIELO_3", "CIELO_4", (37.55, y, "sup"), (40.0, y, "inf")) for y in Y_EJES_123]
)

# Paso 10: losas en voladizo (bordes medidos en las plantas DXF).
# (edificio, nivel, eje del borde "y"|"x", coordenada del eje de vigas,
#  extension a lo largo del eje, extension perpendicular)
VOLADIZOS = (
    [("edificio_1", "CIELO_1", "y", 8.9, (-10.35, 23.75), (8.9, 9.87)),
     ("edificio_1", "CIELO_2", "y", 8.9, (-10.35, 35.35), (8.9, 9.87))]
    + [v for nivel in ("CIELO_3", "CIELO_4") for v in (
        ("edificio_1", nivel, "y", 8.9, (-10.35, 41.15), (8.9, 9.87)),
        ("edificio_1", nivel, "y", -7.25, (34.65, 41.15), (-8.58, -7.25)),
        ("edificio_1", nivel, "x", 40.0, (-7.25, 8.9), (40.0, 41.15)))]
    + [("edificio_2", nivel, "y", 8.9, (-41.87, -9.87), (8.9, 10.05)) for nivel in Z_NIVEL]
)
CAMPOS_CARGA = ("areaTributaria", "cargaTributaria", "deadLoad", "liveLoad", "gravityLoad",
                "factoredLoad12D16L", "factoredLoad14D", "uniformLoad",
                "momentI", "momentJ", "shearI", "shearJ")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)


def close(a, b, tol=1e-3):
    return abs(a - b) < tol


def reflejar_edificio_2(data, log):
    nodes = {n["id"]: n for n in data["nodes"]}
    e2_nodes = set()
    other_nodes = set()
    for item in data["elements"] + data["walls"]:
        target = e2_nodes if item.get("sourceBuilding") == "edificio_2" else other_nodes
        target.update((item["nodeI"], item["nodeJ"]))
    shared = e2_nodes & other_nodes
    if shared:
        raise RuntimeError(f"Nodos compartidos entre edificios, no se puede reflejar: {sorted(shared)}")
    referenced = e2_nodes | other_nodes | {s["node"] for s in data["supports"]}
    for d in data["diaphragmList"]:
        referenced.update(d["slaves"])
        referenced.add(d["maestro"])
    # Nodos auxiliares sin referencias del edificio_2 (cotas propias o x < -10)
    for n in data["nodes"]:
        if n["id"] not in referenced and (round(n["z"], 2) in E2_Z_ORIGINAL or n["x"] < -10.001):
            e2_nodes.add(n["id"])
    for nid in e2_nodes:
        nodes[nid]["y"] = round(E2_MIRROR - nodes[nid]["y"], 6)

    n_slabs = 0
    for s in data["slabs"]:
        if s["x1"] <= -10.0 + 1e-6:
            s["y0"], s["y1"] = round(E2_MIRROR - s["y1"], 6), round(E2_MIRROR - s["y0"], 6)
            n_slabs += 1
    log.append(f"edificio_2 reflejado en Y (y -> {E2_MIRROR} - y): {len(e2_nodes)} nodos, {n_slabs} losas")

    # Muro de borde en eje A' sobre eje 3: debe llegar a x=-39.625 como el del eje 1
    n_fix = 0
    for w in data["walls"]:
        if w.get("sourceBuilding") != "edificio_2" or not close(w["longitud"], 1.45):
            continue
        ni, nj = nodes[w["nodeI"]], nodes[w["nodeJ"]]
        far = nj if nj["x"] > ni["x"] else ni
        far["x"] = -39.625
        w["longitud"] = 1.85
        n_fix += 1
    log.append(f"edificio_2: {n_fix} muros de borde eje A'/3 extendidos a L=1.85")


def bajar_muros_edificio_1(data, log):
    nodes = {n["id"]: n for n in data["nodes"]}
    frame_nodes = {nid for e in data["elements"] for nid in (e["nodeI"], e["nodeJ"])}
    moved = set()
    for w in data["walls"]:
        if w.get("sourceBuilding") == "edificio_2":
            continue
        z_base = E1_Z[w["bottom"]]
        for nid in (w["nodeI"], w["nodeJ"]):
            if nid in frame_nodes:
                raise RuntimeError(f"Nodo de muro {nid} compartido con un elemento")
            if nid not in moved:
                nodes[nid]["z"] = z_base
                moved.add(nid)
    log.append(f"edificio_1: {len(moved)} nodos de muro bajados a la cota base del piso")


def ajustar_nucleo_norte(data, log):
    nodes = {n["id"]: n for n in data["nodes"]}
    n = 0
    for w in data["walls"]:
        if w.get("sourceBuilding") == "edificio_2":
            continue
        ni, nj = nodes[w["nodeI"]], nodes[w["nodeJ"]]
        ys = sorted((ni["y"], nj["y"]))
        if not (close(ni["x"], nj["x"]) and any(close(ni["x"], x) for x in (-6.7, -3.3))):
            continue
        if not (close(ys[0], NUCLEO_Y_OLD) and close(ys[1], NUCLEO_Y_TOP)):
            continue
        low = ni if ni["y"] < nj["y"] else nj
        low["y"] = NUCLEO_Y_NEW
        w["grosor"] = NUCLEO_E
        w["longitud"] = round(NUCLEO_Y_TOP - NUCLEO_Y_NEW, 4)
        n += 1
    log.append(f"edificio_1: {n} muros laterales del nucleo norte -> e={NUCLEO_E}, L={NUCLEO_Y_TOP - NUCLEO_Y_NEW:.2f}")


def agregar_muros(data, log):
    next_id = max(n["id"] for n in data["nodes"]) + 1
    for bottom, top, (x0, y0), (x1, y1), t in MUROS_NUEVOS:
        z = E1_Z[bottom]
        ids = []
        for x, y in ((x0, y0), (x1, y1)):
            data["nodes"].append({"id": next_id, "x": x, "y": y, "z": z})
            ids.append(next_id)
            next_id += 1
        data["walls"].append({
            "bottom": bottom, "top": top, "type": "muro",
            "grosor": t, "longitud": round(math.hypot(x1 - x0, y1 - y0), 4),
            "nodeI": ids[0], "nodeJ": ids[1], "fuente": "planos 2017_67",
        })
    log.append(f"edificio_1: {len(MUROS_NUEVOS)} muros agregados segun planos")


def cambiar_secciones(data, log):
    for sid, (b, h) in SECCIONES.items():
        data["sections"].setdefault(sid, {"id": sid, "shape": "RECTANGULAR", "width_m": b, "height_m": h})
    hechos = []
    for e in data["elements"]:
        sid = CAMBIOS_SECCION.get(e.get("elementTag"))
        if not sid:
            continue
        b, h = SECCIONES[sid]
        e["sectionId"], e["width_m"], e["height_m"] = sid, b, h
        hechos.append(f"{e['elementTag']}->{sid}")
    faltan = set(CAMBIOS_SECCION) - {x.split("->")[0] for x in hechos}
    if faltan:
        raise RuntimeError(f"No se encontraron los elementos {sorted(faltan)}")
    log.append("secciones: " + ", ".join(hechos))


def conectar_vigas(data, log):
    """Parte cada viga en los nodos de otros elementos que caen dentro de su tramo.

    En el edificio_2 varias vigas secundarias llegaban a mitad de una viga
    principal sin nodo comun, por lo que quedaban desconectadas (el analisis
    las empotraba artificialmente). Las cargas por area se reparten segun el
    largo de cada tramo.
    """
    nodes = {n["id"]: n for n in data["nodes"]}
    por_piso = {}
    for e in data["elements"]:
        for nid in (e["nodeI"], e["nodeJ"]):
            por_piso.setdefault((e.get("sourceBuilding"), round(nodes[nid]["z"], 3)), set()).add(nid)
    next_id = max(e["id"] for e in data["elements"]) + 1
    nuevas, partidas = [], []
    for e in data["elements"]:
        a, b = nodes[e["nodeI"]], nodes[e["nodeJ"]]
        if e.get("type") != "viga" or not close(a["z"], b["z"]):
            nuevas.append(e)
            continue
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        length = math.hypot(dx, dy)
        internos = []
        for nid in por_piso[(e.get("sourceBuilding"), round(a["z"], 3))]:
            n = nodes[nid]
            t = ((n["x"] - a["x"]) * dx + (n["y"] - a["y"]) * dy) / length ** 2
            dist = abs((n["x"] - a["x"]) * dy - (n["y"] - a["y"]) * dx) / length
            if 1e-3 < t < 1 - 1e-3 and dist < 1e-3:
                internos.append((t, nid))
        if not internos:
            nuevas.append(e)
            continue
        cortes = [(0.0, e["nodeI"])] + sorted(internos) + [(1.0, e["nodeJ"])]
        for k, ((t0, n0), (t1, n1)) in enumerate(zip(cortes, cortes[1:])):
            frac = t1 - t0
            tramo = dict(e, id=e["id"] if k == 0 else next_id, nodeI=n0, nodeJ=n1,
                         elementTag=f"{e['elementTag']}{chr(ord('a') + k)}")
            if k:
                next_id += 1
            for c in CAMPOS_POR_AREA + ("areaTributaria",):
                if c in tramo:
                    tramo[c] = e[c] * frac
            w, lt = e.get("uniformLoad", 0.0), length * frac
            tramo["shearI"], tramo["shearJ"] = 0.5 * w * lt, -0.5 * w * lt
            tramo["momentI"] = tramo["momentJ"] = -w * lt ** 2 / 12.0
            nuevas.append(tramo)
        partidas.append(e["elementTag"])
    data["elements"] = nuevas
    log.append(f"vigas conectadas: {len(partidas)} vigas partidas en nodos intermedios "
               f"({', '.join(partidas[:6])}{'...' if len(partidas) > 6 else ''})")


def alturas_y_subterraneo(data, log):
    for n in data["nodes"]:
        z = round(n["z"], 2)
        if z not in Z_NUEVA:
            raise RuntimeError(f"Nodo {n['id']} con cota no esperada z={n['z']}")
        n["z"] = round(Z_NUEVA[z], 6)
    for s in data["slabs"]:
        s["z"] = round(Z_NUEVA[round(s["z"], 2)], 6)
    for key in ("diaphragmList", "diaphragms"):
        for d in data.get(key, []):
            d["z"] = round(Z_NUEVA[round(d["z"], 2)], 6)
    n_labels = 0
    for w in data["walls"]:
        for k in ("bottom", "top"):
            if w.get(k) in E2_WALL_LABELS:
                w[k] = E2_WALL_LABELS[w[k]]
                n_labels += 1
    log.append(f"altura de piso {H_PISO} m en ambos edificios (z=0 en cielo 1S, radier en z={-H_PISO})")
    log.append(f"edificio_2: subterraneo extendido hasta el radier -7.97 ({n_labels} muros de subterraneo)")


def pilares_y_arriostres(data, log):
    props = {sid: perfil_cajon(b, t) for sid, (b, t) in PERFILES_ACERO.items()}
    for sid, (b, t) in PERFILES_ACERO.items():
        data["sections"][sid] = {"id": sid, "shape": "CAJON", "material": "acero",
                                 "width_m": b, "height_m": b, "t_m": t, **props[sid]}

    n_col = 0
    for e in data["elements"]:
        if e.get("elementTag") in PILARES_METALICOS:
            if e["type"] != "columna":
                raise RuntimeError(f"{e['elementTag']} no es columna")
            e.update({"sectionId": "PM300x300x20", "seccion": "PM300x300x20", "material": "acero",
                      "width_m": 0.30, "height_m": 0.30, **props["PM300x300x20"]})
            n_col += 1
    if n_col != len(PILARES_METALICOS):
        raise RuntimeError("No se encontraron todos los pilares metalicos")

    index = {(round(n["x"], 2), round(n["y"], 2), round(n["z"], 2)): n["id"] for n in data["nodes"]}
    next_id = max(e["id"] for e in data["elements"]) + 1
    for k, (inf, sup, a, b) in enumerate(ARRIOSTRES, start=1):
        ends = []
        for x, y, pos in (a, b):
            z = Z_NIVEL[inf if pos == "inf" else sup]
            nid = index.get((round(x, 2), round(y, 2), round(z, 2)))
            if nid is None:
                raise RuntimeError(f"Arriostre {k}: no existe nodo en ({x}, {y}, {z})")
            ends.append(nid)
        elem = {"id": next_id, "nodeI": ends[0], "nodeJ": ends[1], "type": "arriostre",
                "sectionId": "VM300x300x5", "seccion": "VM300x300x5", "material": "acero",
                "width_m": 0.30, "height_m": 0.30, "elementTag": f"ARR_{k:02d}", "piso": sup,
                "sourceBuilding": "edificio_1", "sourceId": f"arriostre_{k:02d}",
                "sourceEdges": [], **props["VM300x300x5"]}
        elem.update({c: 0.0 for c in CAMPOS_CARGA + ("axialI", "axialJ")})
        data["elements"].append(elem)
        next_id += 1
    log.append(f"acero: {n_col} pilares P.M. 300x300x20 y {len(ARRIOSTRES)} arriostres V.M. 300x300x5")


CAMPOS_POR_AREA = ("cargaTributaria", "deadLoad", "liveLoad", "gravityLoad",
                   "factoredLoad12D16L", "factoredLoad14D")


def cargas_por_m2(data, nodes, edif, z):
    """Carga por m2 promedio de las vigas cargadas de un piso (para vigas sin area)."""
    suma = {c: 0.0 for c in CAMPOS_POR_AREA}
    area = 0.0
    for e in data["elements"]:
        if e.get("type") != "viga" or e.get("sourceBuilding") != edif:
            continue
        if not (close(nodes[e["nodeI"]]["z"], z) and close(nodes[e["nodeJ"]]["z"], z)):
            continue
        a = float(e.get("areaTributaria") or 0.0)
        if a > 0.0:
            area += a
            for c in CAMPOS_POR_AREA:
                suma[c] += float(e.get(c) or 0.0)
    return {c: v / area for c, v in suma.items()}


def cargar_viga_sin_area(e, d_area, q, length):
    """Asigna a una viga sin area tributaria la carga de d_area (viga empotrada-empotrada)."""
    e["areaTributaria"] = d_area
    for c in CAMPOS_POR_AREA:
        e[c] = q[c] * d_area
    w = e["cargaTributaria"] / length
    e["uniformLoad"] = w
    e["shearI"], e["shearJ"] = 0.5 * w * length, -0.5 * w * length
    e["momentI"] = e["momentJ"] = -w * length ** 2 / 12.0


def repartir_franja(data, nodes, edif, nivel, eje, coord, extension, depth, side, sin_area):
    """Suma el area de una franja (extension x depth) a las vigas del eje eje=coord.

    El area se reparte por largo de viga cubierto; las esquinas que quedan
    fuera de las vigas van a la viga extrema. Devuelve el area agregada.
    """
    a0, a1 = extension
    z = Z_NIVEL[nivel]
    along = "x" if eje == "y" else "y"
    tramos = []
    for e in data["elements"]:
        if e.get("type") != "viga" or e.get("sourceBuilding") != edif:
            continue
        ni, nj = nodes[e["nodeI"]], nodes[e["nodeJ"]]
        if not (close(ni["z"], z) and close(nj["z"], z) and close(ni[eje], coord) and close(nj[eje], coord)):
            continue
        s0, s1 = sorted((ni[along], nj[along]))
        if s1 > a0 and s0 < a1:
            tramos.append([s0, s1, e])
    if not tramos:
        raise RuntimeError(f"{side} {edif} {nivel}: no hay vigas en {eje}={coord}")
    tramos.sort(key=lambda t: t[0])
    tramos[0][0] = min(tramos[0][0], a0)
    tramos[-1][1] = max(tramos[-1][1], a1)
    total = 0.0
    for s0, s1, e in tramos:
        d_area = (min(s1, a1) - max(s0, a0)) * depth
        if d_area <= 1e-9:
            continue
        area = float(e.get("areaTributaria") or 0.0)
        if area <= 0.0:
            length = math.dist(*[(nodes[n]["x"], nodes[n]["y"], nodes[n]["z"]) for n in (e["nodeI"], e["nodeJ"])])
            cargar_viga_sin_area(e, d_area, cargas_por_m2(data, nodes, edif, z), length)
            sin_area.append(e["elementTag"])
        else:
            factor = (area + d_area) / area
            for campo in CAMPOS_CARGA:
                if campo in e:
                    e[campo] = e[campo] * factor
        e.setdefault("sourceEdges", []).append({"side": side, "tributary_area_m2": round(d_area, 4)})
        total += d_area
    return total


def losas_zona_ij(data, log):
    """Losas L91-L94 (zona I'-J, pisos 3 y 4): no transmitian carga a ninguna viga.

    Cada panel (x0..x1 entre ejes I', x=37.55 y J; y entre ejes 3-2 o 2-1)
    tiene b/a >= 2, asi que trabaja en una direccion: cada viga larga (eje y)
    recibe a*b/2.
    """
    nodes = {n["id"]: n for n in data["nodes"]}
    sin_area = []
    total = 0.0
    for nivel in ("CIELO_3", "CIELO_4"):
        for x0, x1 in ((35.0, 37.55), (37.55, 40.0)):
            for y0, y1 in ((-7.25, 0.0), (0.0, 8.9)):
                a = x1 - x0
                for xb in (x0, x1):
                    total += repartir_franja(data, nodes, "edificio_1", nivel, "x", xb, (y0, y1), a / 2.0,
                                             "losa_zona_IJ", sin_area)
    log.append(f"losas zona I'-J: {total:.2f} m2 asignados a las vigas de los ejes I', x=37.55 y J (pisos 3 y 4)")


# Muros del edificio_2 que sostienen extremos de vigas sin pilar (plano 2024_22):
# (tag, x, y, espesor, largo de muro asignado al nodo)
MUROS_GRAVEDAD_E2 = [
    ("MUROA_N", -41.475, 8.9, 0.60, 2.92),    # eje A', muro e=60 L=2.92 (esquina eje 1)
    ("MUROA_S", -41.475, -7.25, 0.60, 2.92),  # eje A', muro e=60 L=2.92 (esquina eje 3)
    ("MURODp_2", -10.0, 0.0, 0.25, 3.975),    # eje D', muro e=25 L=7.95 (mitad al eje 2)
    ("MURODp_3", -10.0, -7.25, 0.25, 3.975),  # eje D', muro e=25 L=7.95 (mitad al eje 3)
]


def muros_gravedad_e2(data, log):
    """Extremos de vigas del edificio_2 apoyados en muros (sin pilar en el plano).

    Como los muros no estan en el analisis OpenSees, esos nodos quedaban
    colgando de las vigas (la esquina A' bajaba ~9 cm y el eje D' ~5 cm). Se
    modelan como columnas equivalentes de GRAVEDAD: area axial del tramo de
    muro que sostiene el nodo y flexion de una columna t x t, para no
    introducir una rigidez lateral que el resto de los muros tampoco tiene.
    """
    # solo nodos del edificio_2: en x=-10 coinciden el eje E del edificio_1 y
    # el eje D' del edificio_2 (separados por la junta de dilatacion)
    usados = {nid for e in data["elements"] if e.get("sourceBuilding") == "edificio_2"
              for nid in (e["nodeI"], e["nodeJ"])}
    next_node = max(n["id"] for n in data["nodes"]) + 1
    next_elem = max(e["id"] for e in data["elements"]) + 1
    niveles = [-H_PISO] + sorted(Z_NIVEL.values())
    creados = apoyos = 0
    for tag, x, y, t, largo in MUROS_GRAVEDAD_E2:
        area = t * largo
        inercia = t ** 4 / 12.0
        sid = f"MURO_EQ_{int(t * 100)}x{int(round(largo * 100))}"
        cadena = []
        for z in niveles:
            nid = next((n["id"] for n in data["nodes"] if n["id"] in usados and close(n["x"], x)
                        and close(n["y"], y) and close(n["z"], z)), None)
            if nid is None and close(z, -H_PISO):
                data["nodes"].append({"id": next_node, "x": x, "y": y, "z": z})
                data["supports"].append({"node": next_node, "type": "fixed",
                                         "ux": 1, "uy": 1, "uz": 1, "rx": 1, "ry": 1, "rz": 1})
                nid = next_node
                next_node += 1
                apoyos += 1
            if nid is None:
                raise RuntimeError(f"Muro {tag}: falta nodo en ({x}, {y}, {z})")
            cadena.append(nid)
        for k, (ni, nj) in enumerate(zip(cadena, cadena[1:]), start=1):
            data["elements"].append({
                "id": next_elem, "nodeI": ni, "nodeJ": nj, "type": "columna",
                "sectionId": sid, "seccion": sid, "elementTag": f"E2_{tag}_{k}", "piso": "",
                "sourceBuilding": "edificio_2", "sourceId": "muro_gravedad",
                "width_m": t, "height_m": t,
                "A_m2": area, "Iy_m4": inercia, "Iz_m4": inercia, "J_m4": 2 * inercia,
                "nota": f"Columna equivalente de gravedad del muro e={t:.2f} (tramo L={largo:.2f} m)",
            })
            next_elem += 1
            creados += 1
        data["sections"][sid] = {"id": sid, "shape": "EQUIVALENTE", "width_m": t, "height_m": t,
                                 "A_m2": area, "Iy_m4": inercia, "Iz_m4": inercia}
    log.append(f"edificio_2: {creados} columnas equivalentes de gravedad en muros de los ejes A' y D' "
               f"({apoyos} apoyos nuevos)")


def losas_en_voladizo(data, log):
    nodes = {n["id"]: n for n in data["nodes"]}
    area_total = 0.0
    sin_area = []
    for k, (edif, nivel, eje, coord, (a0, a1), (b0, b1)) in enumerate(VOLADIZOS, start=1):
        area_total += repartir_franja(data, nodes, edif, nivel, eje, coord, (a0, a1), b1 - b0, "voladizo", sin_area)
        x0, x1, y0, y1 = (a0, a1, b0, b1) if eje == "y" else (b0, b1, a0, a1)
        data["slabs"].append({"id": f"VOL{k:02d}", "nivel": nivel, "tipo": "voladizo",
                              "sourceBuilding": edif, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "z": Z_NIVEL[nivel]})
    log.append(f"losas en voladizo: {len(VOLADIZOS)} paneles, {area_total:.2f} m2 sumados a las vigas de borde")
    if sin_area:
        log.append("vigas sin area previa cargadas con q promedio del piso: " + ", ".join(sin_area))


# Paso 14: muros en el analisis (modelo de columna ancha equivalente).
# Cada pano de muro (un piso) es un elemento vertical en el eje del muro con
# A = t*L e inercia en el plano t*L^3/12, unido arriba y abajo por brazos
# rigidos a los nodos del marco que caen sobre la linea del muro. Reemplaza a
# las columnas equivalentes de gravedad del paso 11.
RIGIDO = {"A_m2": 10.0, "Iy_m4": 50.0, "Iz_m4": 50.0, "J_m4": 50.0}
TOL_LINEA = 0.20   # m: nodo del marco "sobre" el muro (distancia al eje y a los extremos)


def muros_en_el_modelo(data, log):
    nodes = {n["id"]: n for n in data["nodes"]}
    soportes = {s["node"] for s in data["supports"]}
    # nodos del marco por (edificio, z): los que ya usan vigas, columnas o arriostres
    marco = {}
    for e in data["elements"]:
        b = e.get("sourceBuilding") or "edificio_1"
        for nid in (e["nodeI"], e["nodeJ"]):
            n = nodes[nid]
            marco.setdefault((b, round(n["z"], 2)), set()).add(nid)
    # indice de nodos por (edificio, coordenada): los edificios estan separados por la
    # junta de dilatacion, asi que un muro nunca toma un nodo del otro edificio aunque
    # ambos queden en la misma coordenada (linea x = -10 entre 2017_67 y 2024_22)
    def coord(n):
        return (round(n["x"], 3), round(n["y"], 3), round(n["z"], 3))
    owner = {}
    for e in data["elements"]:
        for nid in (e["nodeI"], e["nodeJ"]):
            owner.setdefault(nid, e.get("sourceBuilding") or "edificio_1")
    index = {(owner[n["id"]],) + coord(n): n["id"] for n in data["nodes"] if n["id"] in owner}
    libres = {coord(n): n["id"] for n in data["nodes"] if n["id"] not in owner}
    next_node = max(nodes) + 1
    next_elem = max(e["id"] for e in data["elements"]) + 1
    z_min = min(n["z"] for n in data["nodes"])

    def nodo(x, y, z, edificio):
        nonlocal next_node
        key = (edificio, round(x, 3), round(y, 3), round(z, 3))
        if key in index:
            return index[key]
        if key[1:] in libres:
            index[key] = libres.pop(key[1:])
            return index[key]
        data["nodes"].append({"id": next_node, "x": x, "y": y, "z": z})
        nodes[next_node] = data["nodes"][-1]
        index[key] = next_node
        next_node += 1
        return next_node - 1

    def sobre_linea(nid, a, b):
        n = nodes[nid]
        vx, vy = b["x"] - a["x"], b["y"] - a["y"]
        largo = math.hypot(vx, vy)
        if largo < 1e-6:
            return False
        t = ((n["x"] - a["x"]) * vx + (n["y"] - a["y"]) * vy) / largo
        d = abs((n["x"] - a["x"]) * vy - (n["y"] - a["y"]) * vx) / largo
        return d <= TOL_LINEA and -TOL_LINEA <= t <= largo + TOL_LINEA

    def elemento(ni, nj, tipo, tag, edificio, extra):
        nonlocal next_elem
        e = {"id": next_elem, "nodeI": ni, "nodeJ": nj, "type": tipo, "elementTag": tag,
             "sourceBuilding": edificio, "sourceId": "muro_columna_ancha", "sourceEdges": []}
        e.update({c: 0.0 for c in CAMPOS_CARGA + ("axialI", "axialJ")})
        e.update(extra)
        data["elements"].append(e)
        next_elem += 1
        return e

    # quitar las columnas equivalentes de gravedad (paso 11): ahora el muro completo esta en el modelo
    antes = len(data["elements"])
    data["elements"] = [e for e in data["elements"] if e.get("sourceId") != "muro_gravedad"]
    quitadas = antes - len(data["elements"])

    # 1) nodos en los extremos de cada pano, arriba y abajo. Se indexan por
    #    coordenada: muros que se encuentran en una esquina comparten el nodo, y
    #    si en ese punto ya hay un nodo del marco, se usa ese.
    panos = []
    for i, w in enumerate(data.get("walls", [])):
        a, b = nodes[w["nodeI"]], nodes[w["nodeJ"]]
        edificio = w.get("sourceBuilding") or "edificio_1"
        z0 = round(a["z"], 2)
        z1 = round(z0 + H_PISO, 2)
        ext = {zc: [nodo(a["x"], a["y"], zc, edificio), nodo(b["x"], b["y"], zc, edificio)] for zc in (z0, z1)}
        panos.append((i, w, a, b, z0, z1, ext))
    candidatos = {}   # (edificio, z) -> nodos del marco + extremos de muros
    for (bz, z), ids in marco.items():
        candidatos.setdefault((bz, z), set()).update(ids)
    for i, w, a, b, z0, z1, ext in panos:
        edificio = w.get("sourceBuilding") or "edificio_1"
        for zc in (z0, z1):
            candidatos.setdefault((edificio, zc), set()).update(ext[zc])

    # 2) columna ancha en el eje del muro + brazos rigidos a todo nodo sobre su linea
    n_muros = n_brazos = n_apoyos = 0
    for i, w, a, b, z0, z1, ext in panos:
        edificio = w.get("sourceBuilding") or "edificio_1"
        t = float(w["grosor"])
        largo = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
        cx, cy = (a["x"] + b["x"]) / 2.0, (a["y"] + b["y"]) / 2.0
        nb, nt = nodo(cx, cy, z0, edificio), nodo(cx, cy, z1, edificio)
        a_lo_largo_x = abs(b["x"] - a["x"]) >= abs(b["y"] - a["y"])
        i_plano, i_fuera = t * largo ** 3 / 12.0, largo * t ** 3 / 12.0
        # columna vertical: eje local y = -Y global, z = +X global (geomTransf vecxz = X)
        iy, iz = (i_plano, i_fuera) if a_lo_largo_x else (i_fuera, i_plano)
        tag = "MURO-{:03d}".format(i + 1)
        sid = f"MURO_{int(round(t * 100))}x{int(round(largo * 100))}"
        elemento(nb, nt, "muro", "W_" + tag, edificio, {
            "sectionId": sid, "seccion": sid, "piso": w.get("top", ""), "material": "hormigon",
            "width_m": t, "height_m": largo, "A_m2": t * largo, "Iy_m4": iy, "Iz_m4": iz,
            "J_m4": largo * t ** 3 / 3.0, "wallIndex": i + 1, "wallInPlaneAxis": "X" if a_lo_largo_x else "Y",
            "nota": f"Muro {tag} e={t:.2f} L={largo:.2f} m: columna ancha equivalente (seccion bruta)",
        })
        n_muros += 1
        for zc, centro in ((z0, nb), (z1, nt)):
            for nid in sorted(candidatos.get((edificio, zc), ())):
                if nid != centro and sobre_linea(nid, a, b):
                    elemento(centro, nid, "rigido", f"RIG_{tag}_{nid}", edificio,
                             {"sectionId": "RIGIDO", "seccion": "RIGIDO", "piso": w.get("top", ""),
                              "width_m": 0.0, "height_m": 0.0, **RIGIDO})
                    n_brazos += 1
        if z0 <= z_min + 1e-6:
            for nid in [nb] + ext[z0]:
                if nid not in soportes:
                    data["supports"].append({"node": nid, "type": "fixed", "ux": 1, "uy": 1, "uz": 1, "rx": 1, "ry": 1, "rz": 1})
                    soportes.add(nid)
                    n_apoyos += 1
    sin_conexion = []
    data["sections"]["RIGIDO"] = {"id": "RIGIDO", "shape": "BRAZO_RIGIDO", **RIGIDO}
    log.append(f"muros en el analisis: {n_muros} panos como columna ancha, {n_brazos} brazos rigidos al marco, "
               f"{n_apoyos} empotramientos en fundacion; {quitadas} columnas equivalentes de gravedad reemplazadas"
               + (f"; sin nodos del marco sobre la linea (solo diafragma): {', '.join(sin_conexion)}" if sin_conexion else ""))


# Paso 16: reparto tributario recalculado desde las losas del modelo.
TOL_BORDE = 0.15        # m: viga o brazo rigido "sobre" un borde de losa
Q_VIVA_KN_M2 = 0.500 * 9.80665   # liveLoad de referencia (500 kg/m2); el analisis usa q_Q * areaTributaria


def reparto_tributario(data, log):
    """Recalcula areaTributaria y deadLoad de todas las vigas desde data["slabs"].

    El reparto original (semana 2) dejaba sin carga los bordes de losa que caen
    sobre vigas transversales intermedias del edificio_2 o sobre muros: ~1600 m2
    de losa no cargaban la estructura. Ahora cada panel reparte su area con el
    metodo b/a (b/a < 2: triangulos a^2/4 en los lados cortos y trapecios
    a(2b-a)/4 en los largos; b/a >= 2: a*b/2 en cada lado largo) a los elementos
    que cubren cada borde, en proporcion al largo cubierto:
      - vigas del mismo piso,
      - brazos rigidos de muro (borde apoyado en un muro: la carga entra al muro),
    y la parte de un borde libre (sin apoyo) se reparte entre los bordes apoyados
    del mismo panel, de modo que el panel completo carga la estructura.
    q por nivel = el que ya tenia el modelo (deadLoad / areaTributaria)."""
    nodes = {n["id"]: n for n in data["nodes"]}
    soportes = []   # (elemento, eje "x"|"y", coordenada fija, (lo, hi), z, edificio)
    for e in data["elements"]:
        if e.get("type") not in ("viga", "rigido") or e.get("removed"):
            continue
        a, b = nodes[e["nodeI"]], nodes[e["nodeJ"]]
        if abs(a["z"] - b["z"]) > 0.01:
            continue
        if abs(a["y"] - b["y"]) < 0.02 and abs(a["x"] - b["x"]) > 0.02:
            soportes.append((e, "x", a["y"], tuple(sorted((a["x"], b["x"]))), round(a["z"], 2), e.get("sourceBuilding") or "edificio_1"))
        elif abs(a["x"] - b["x"]) < 0.02 and abs(a["y"] - b["y"]) > 0.02:
            soportes.append((e, "y", a["x"], tuple(sorted((a["y"], b["y"]))), round(a["z"], 2), e.get("sourceBuilding") or "edificio_1"))

    # q de losa por (edificio, nivel) segun el modelo vigente; campos derivados por m2
    q_nivel, ratios = {}, {}
    for e in data["elements"]:
        area = float(e.get("areaTributaria") or 0.0)
        if e.get("type") == "viga" and area > 0.0:
            key = (e.get("sourceBuilding") or "edificio_1", round(nodes[e["nodeI"]]["z"], 2))
            q_nivel.setdefault(key, []).append(round(float(e.get("deadLoad") or 0.0) / area, 4))
            for campo in ("cargaTributaria", "gravityLoad", "factoredLoad12D16L", "factoredLoad14D"):
                ratios.setdefault((key, campo), []).append(float(e.get(campo) or 0.0) / area)
    moda = lambda vals: max(set(vals), key=vals.count)
    mediana = lambda vals: sorted(vals)[len(vals) // 2]
    q_def = float(data.get("q_G", 6.227))

    nueva = {}
    sin_apoyo = []
    for s in data.get("slabs", []):
        x0, x1, y0, y1, z = s["x0"], s["x1"], s["y0"], s["y1"], round(s["z"], 2)
        # edificio de la losa: los dos edificios se tocan en la linea x = -10 (junta)
        edificio_losa = s.get("sourceBuilding") or ("edificio_2" if (x0 + x1) / 2.0 < -10.0 else "edificio_1")
        lx, ly = x1 - x0, y1 - y0
        if lx <= 0 or ly <= 0:
            continue
        a, b = min(lx, ly), max(lx, ly)
        if b / a < 2.0:
            corto, largo = a * a / 4.0, a * (2.0 * b - a) / 4.0
        else:
            corto, largo = 0.0, a * b / 2.0
        lado_x = largo if lx >= ly else corto      # bordes paralelos a x (largo lx)
        lado_y = corto if lx >= ly else largo
        if abs(lx - ly) < 1e-9:
            lado_x = lado_y = a * a / 4.0
        bordes = [("x", y0, (x0, x1), lado_x), ("x", y1, (x0, x1), lado_x),
                  ("y", x0, (y0, y1), lado_y), ("y", x1, (y0, y1), lado_y)]
        reparto = []   # por borde: [(elemento, largo cubierto)], area
        for eje, c, (lo, hi), area in bordes:
            cubre = []
            for e, eje_s, c_s, (slo, shi), zs, eb in soportes:
                if eb != edificio_losa or eje_s != eje or abs(zs - z) > 0.05 or abs(c_s - c) > TOL_BORDE:
                    continue
                largo_c = min(hi, shi) - max(lo, slo)
                if largo_c > 0.05:
                    cubre.append((e, largo_c))
            reparto.append((cubre, area))
        apoyada = sum(area for cubre, area in reparto if cubre)
        if apoyada <= 0.0:
            sin_apoyo.append(s.get("id"))
            continue
        escala = (lx * ly) / apoyada       # bordes libres -> bordes apoyados del panel
        for cubre, area in reparto:
            total_c = sum(l for _, l in cubre)
            for e, l in cubre:
                nueva[e["id"]] = nueva.get(e["id"], 0.0) + area * escala * l / total_c

    antes = {b: 0.0 for b in ("edificio_1", "edificio_2")}
    despues = dict(antes)
    for e in data["elements"]:
        if e.get("type") not in ("viga", "rigido"):
            continue
        edificio = e.get("sourceBuilding") or "edificio_1"
        key = (edificio, round(nodes[e["nodeI"]]["z"], 2))
        viejo = float(e.get("areaTributaria") or 0.0)
        area = nueva.get(e["id"], 0.0)
        antes[edificio] += viejo
        despues[edificio] += area
        if area <= 0.0 and viejo <= 0.0:
            continue
        q = moda(q_nivel[key]) if key in q_nivel else q_def
        largo = math.dist((nodes[e["nodeI"]]["x"], nodes[e["nodeI"]]["y"]), (nodes[e["nodeJ"]]["x"], nodes[e["nodeJ"]]["y"]))
        e["areaTributaria"] = area
        e["deadLoad"] = q * area
        e["liveLoad"] = Q_VIVA_KN_M2 * area
        for campo in ("cargaTributaria", "gravityLoad", "factoredLoad12D16L", "factoredLoad14D"):
            r = ratios.get((key, campo))
            e[campo] = (mediana(r) if r else 0.0) * area
        w = e["gravityLoad"] / largo if largo > 0 else 0.0
        e["uniformLoad"] = w
        e["shearI"], e["shearJ"] = w * largo / 2.0, -w * largo / 2.0
        e["momentI"], e["momentJ"] = -w * largo ** 2 / 12.0, w * largo ** 2 / 12.0

    # totales por piso que muestra el viewer (tributaryList / tributaryAreasByFloor)
    pisos = {}
    for e in data["elements"]:
        if e.get("type") == "viga" and float(e.get("areaTributaria") or 0.0) > 0.0:
            p = pisos.setdefault(e.get("piso") or "", {"area_total": 0.0, "carga_total": 0.0, "vigas": 0})
            p["area_total"] += e["areaTributaria"]
            p["carga_total"] += e["deadLoad"]
            p["vigas"] += 1
    for clave in ("tributaryList", "tributaryAreasByFloor"):
        if isinstance(data.get(clave), list):
            for fila in data[clave]:
                fila.update(pisos.get(fila.get("piso"), {}))
    n_rig = sum(1 for e in data["elements"] if e.get("type") == "rigido" and float(e.get("areaTributaria") or 0.0) > 0.0)
    log.append("reparto tributario desde losas: area cargada edificio_1 {:.0f} -> {:.0f} m2, edificio_2 {:.0f} -> {:.0f} m2 "
               "({} brazos de muro reciben losa){}".format(antes["edificio_1"], despues["edificio_1"], antes["edificio_2"],
                                                         despues["edificio_2"], n_rig,
                                                         "; paneles sin apoyo: " + ", ".join(sin_apoyo) if sin_apoyo else ""))


def aplicar(data):
    log = []
    reflejar_edificio_2(data, log)
    bajar_muros_edificio_1(data, log)
    ajustar_nucleo_norte(data, log)
    agregar_muros(data, log)
    cambiar_secciones(data, log)
    conectar_vigas(data, log)
    alturas_y_subterraneo(data, log)
    pilares_y_arriostres(data, log)
    muros_gravedad_e2(data, log)
    losas_zona_ij(data, log)
    losas_en_voladizo(data, log)
    muros_en_el_modelo(data, log)
    reparto_tributario(data, log)
    data[MARCA] = log
    return log


def main():
    parser = argparse.ArgumentParser(description="Ajustar el modelo a los planos DXF.")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar el resumen, sin guardar.")
    parser.add_argument("--restore", action="store_true", help="Restaurar el JSON previo a los ajustes.")
    args = parser.parse_args()

    if args.restore:
        if not JSON_BACKUP.exists():
            print("No hay respaldo previo a los ajustes. No se restaura nada.")
            return
        shutil.copyfile(JSON_BACKUP, JSON_BASE)
        print(f"Restaurado {JSON_BASE.name} desde {JSON_BACKUP.name}")
        return

    if JSON_BACKUP.exists():
        data = load_json(JSON_BACKUP)
        print(f"Partiendo del respaldo {JSON_BACKUP.name}")
    else:
        data = load_json(JSON_BASE)
        if MARCA in data:
            print("El modelo ya tiene ajustes aplicados y no hay respaldo; no se puede rehacer.")
            return

    log = aplicar(data)
    for line in log:
        print("  - " + line)
    if args.dry_run:
        print("\n[dry-run] No se guarda el modelo ni se exporta.")
        return

    if not JSON_BACKUP.exists():
        shutil.copyfile(JSON_BASE, JSON_BACKUP)
        print(f"Respaldo creado: {JSON_BACKUP.name}")
    write_json(JSON_BASE, data)
    print(f"Modelo guardado en {JSON_BASE}")

    print("\n── Re-exportando resultados (OpenSees) ──")
    r = subprocess.run([sys.executable, "-X", "utf8", str(EXPORTER)], cwd=str(BASE_DIR))
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
