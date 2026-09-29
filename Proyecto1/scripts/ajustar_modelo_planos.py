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
 11. Losas en voladizo: borde norte (eje 1) de ambos edificios y bordes sur
     y este de la zona I'-J en los pisos 3 y 4; su area tributaria se suma
     a las vigas de borde.

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


def losas_en_voladizo(data, log):
    nodes = {n["id"]: n for n in data["nodes"]}
    area_total = 0.0
    sin_area = []
    for k, (edif, nivel, eje, coord, (a0, a1), (b0, b1)) in enumerate(VOLADIZOS, start=1):
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
            raise RuntimeError(f"Voladizo {edif} {nivel}: no hay vigas en {eje}={coord}")
        tramos.sort(key=lambda t: t[0])
        tramos[0][0] = min(tramos[0][0], a0)      # las esquinas van a la viga extrema
        tramos[-1][1] = max(tramos[-1][1], a1)
        depth = b1 - b0
        for s0, s1, e in tramos:
            d_area = (min(s1, a1) - max(s0, a0)) * depth
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
            e.setdefault("sourceEdges", []).append({"side": "voladizo", "tributary_area_m2": round(d_area, 4)})
            area_total += d_area
        x0, x1, y0, y1 = (a0, a1, b0, b1) if eje == "y" else (b0, b1, a0, a1)
        data["slabs"].append({"id": f"VOL{k:02d}", "nivel": nivel, "tipo": "voladizo",
                              "sourceBuilding": edif, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "z": z})
    log.append(f"losas en voladizo: {len(VOLADIZOS)} paneles, {area_total:.2f} m2 sumados a las vigas de borde")
    if sin_area:
        log.append("vigas sin area previa cargadas con q promedio del piso: " + ", ".join(sin_area))


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
    losas_en_voladizo(data, log)
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
