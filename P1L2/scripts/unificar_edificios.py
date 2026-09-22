#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unifica el edificio 1 y el edificio 2 en un unico JSON (formato Unity del
viewer del edificio 1) que los muestra conectados como una sola pieza continua.

Conexion (criterio del usuario, Semana 2 MCOC):
  - El edificio 2 se coloca a la IZQUIERDA del edificio 1.
  - Su cara X+ (donde estan los ascensores del edificio 2) se pega a la cara
    X- del edificio 1 (opuesta al voladizo X+, donde estan los ascensores del
    edificio 1). Ambos nucleos de ascensores quedan contiguos.
  - Los pisos se alinean por el piso 1 (Z=0) de ambos edificios.

Salidas:
  - resultados/estructura_completo_unity.json
  - unity_visualizador/Assets/Resources/estructura_completo_unity.json  (si el viewer existe)
"""

import json
import math
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPLETO_DIR = os.path.dirname(BASE_DIR)                      # "P1L2"
RESULT_DIR = os.path.join(COMPLETO_DIR, "resultados")

# Rutas a los JSON de origen (relativos a la raiz del repo)
REPO_DIR = os.path.normpath(os.path.join(COMPLETO_DIR, ".."))
EDIFICIO1_JSON = os.path.join(
    COMPLETO_DIR, "Edificio 1 y 2", "edificio 1",
    "unity_visualizador", "Assets", "Resources", "estructura_edificio1_unity.json")
EDIFICIO2_JSON = os.path.join(
    REPO_DIR, "edificio_2", "unity_visualizador", "Assets", "Resources",
    "estructura_edificio_ingenieria_unity.json")
EDIFICIO2_GEOMETRY_JSON = os.path.join(
    REPO_DIR, "edificio_2", "modelo_python", "structural_geometry.json")
EDIFICIO1_BEAM_LOADS_JSON = os.path.join(
    COMPLETO_DIR, "Edificio 1 y 2", "edificio 1",
    "resultados", "beam_tributary_loads.json")

OUT_JSON = os.path.join(RESULT_DIR, "estructura_completo_unity.json")
UNITY_JSON_NAME = "estructura_completo_unity.json"

# ----------------------------------------------------------------------
# Parametros de la conexion (ajustables)
# ----------------------------------------------------------------------
# Contacto: columna derecha del edificio 2 (X=31.475) se alinea exacto en
# X=-10, justo al lado del edificio 1.
ED1_CARA_X = -10.0
ED2_X_COL_MAX = 31.475
OFFSET_X = ED1_CARA_X - ED2_X_COL_MAX            # -41.475

# Mover el edificio 2 en Y: -7.25 para que su borde de losa bajo (Y=0 en la cara
# de contacto) coincida con el borde bajo del edificio 1 (Y=-7.25), haciendo
# continuo el "lado izquierdo" (borde de Y baja) de la union.
OFFSET_Y = -7.25

# El edificio 1 se deja en su posicion original en Y (sin centrado).
OFFSET_Y_E1 = 0.0

# Alineacion vertical: el cielo mas alto del edificio 2 (CIELO_4=11.83) se sube
# para que coincida con el techo del edificio 1 (Z=16.0). Shift = 16.0 - 11.83 = 4.17.
OFFSET_Z = 4.17

# Offset para remapear los IDs de nodos del edificio 2 (evitar colisiones con
# el edificio 1). El edificio 1 usa ids pequenos; usamos base alta.
ID_OFFSET = 100000

SECTIONS = {
    "V30/45": {"id": "V30/45", "shape": "RECTANGULAR", "width_m": 0.30, "height_m": 0.45},
    "V30/80": {"id": "V30/80", "shape": "RECTANGULAR", "width_m": 0.30, "height_m": 0.80},
    "V40/80": {"id": "V40/80", "shape": "RECTANGULAR", "width_m": 0.40, "height_m": 0.80},
    "V60/80": {"id": "V60/80", "shape": "RECTANGULAR", "width_m": 0.60, "height_m": 0.80},
    "COL70/70": {"id": "COL70/70", "shape": "RECTANGULAR", "width_m": 0.70, "height_m": 0.70},
}


def inferir_seccion(el):
    if el.get("sectionId"):
        return el["sectionId"]
    tipo = el.get("tipo", "") or el.get("type", "")
    seccion = el.get("seccion", "")
    if tipo == "columna" or seccion == "COL":
        return "COL70/70"
    if tipo == "viga_long_voladizo_p2":
        return "V30/45"
    if seccion in SECTIONS:
        return seccion
    if seccion == "V":
        return "V60/80"
    return "V60/80" if el.get("type") == "viga" else "COL70/70"


def agregar_seccion(el):
    out = dict(el)
    section_id = inferir_seccion(out)
    section = SECTIONS.get(section_id, SECTIONS["V60/80"])
    out["sectionId"] = section_id
    out["width_m"] = section["width_m"]
    out["height_m"] = section["height_m"]
    return out


def cargar_cargas_vigas_edificio1():
    if not os.path.exists(EDIFICIO1_BEAM_LOADS_JSON):
        return {}
    data = cargar_json(EDIFICIO1_BEAM_LOADS_JSON)
    return {item["beam_index"] + 1: item for item in data.get("beam_tributary_loads", [])}


def enriquecer_edificio1(el, cargas_por_id):
    out = agregar_seccion(el)
    out["sourceBuilding"] = "edificio_1"
    out["sourceId"] = el.get("sourceId", el.get("id"))
    out["elementTag"] = el.get("elementTag", f"E1_{el.get('id')}")

    carga = cargas_por_id.get(el.get("id"))
    if carga:
        out["areaTributaria"] = carga.get("tributary_area_m2", out.get("areaTributaria", 0.0))
        out["deadLoad"] = carga.get("loads_kN", {}).get("D", 0.0)
        out["liveLoad"] = carga.get("loads_kN", {}).get("L", 0.0)
        out["factoredLoad14D"] = carga.get("load_combinations_kN", {}).get("U_1_4D", 0.0)
        out["factoredLoad12D16L"] = carga.get("load_combinations_kN", {}).get("U_1_2D_1_6L", out.get("cargaTributaria", 0.0))
        out["cargaTributaria"] = out["factoredLoad12D16L"]
        out["gravityLoad"] = out["factoredLoad12D16L"]
        out["sourceEdges"] = carga.get("source_edges", [])
    else:
        gravity_load = out.get("cargaTributaria", 0.0)
        out["deadLoad"] = gravity_load
        out["liveLoad"] = 0.0
        out["factoredLoad14D"] = 1.4 * gravity_load
        out["factoredLoad12D16L"] = 1.2 * gravity_load
        out["gravityLoad"] = gravity_load
        out["loadNote"] = "Edificio 1 sin desglose D/L para este elemento: se usa D=cargaTributaria y L=0."
    return out


def cargar_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def transformar_nodo(n):
    return {
        "id": n["id"],
        "x": round(n["x"] + OFFSET_X, 6),
        "y": round(n["y"] + OFFSET_Y, 6),
        "z": round(n["z"] + OFFSET_Z, 6),
    }


def convertir_slabs(e2):
    """Convierte los rigidDiaphragms del edificio 2 a slabs (formato e1)."""
    slabs = []
    for d in e2.get("rigidDiaphragms", []):
        slabs.append({
            "id": str(d["id"]),
            "nivel": d.get("level", ""),
            "x0": round(d["x1"] + OFFSET_X, 6),
            "y0": round(d["y1"] + OFFSET_Y, 6),
            "x1": round(d["x2"] + OFFSET_X, 6),
            "y1": round(d["y2"] + OFFSET_Y, 6),
            "z": round(d.get("z", 0.0) + OFFSET_Z, 6),
        })
    return slabs


def transformar_coord_e2(x, y, z):
    return {
        "x": round(x + OFFSET_X, 6),
        "y": round(y + OFFSET_Y, 6),
        "z": round(z + OFFSET_Z, 6),
    }


def agregar_nodo_muro(nodos, prox_id, x, y, z):
    coord = transformar_coord_e2(x, y, z)
    nodos.append({"id": prox_id, **coord})
    return prox_id, prox_id + 1


def convertir_muros_edificio2(e2_geometry, nodos, prox_id, start_wall_id):
    walls = []
    wall_id = start_wall_id
    for wall in e2_geometry.get("walls", []):
        if wall.get("status") != "ACTIVE":
            continue
        x1 = float(wall["x1"])
        y1 = float(wall["y1"])
        x2 = float(wall["x2"])
        y2 = float(wall["y2"])
        z_bottom = float(wall["z_bottom"])
        z_top = float(wall["z_top"])
        thickness = float(wall.get("thickness", 0.2))
        length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        node_i, prox_id = agregar_nodo_muro(nodos, prox_id, x1, y1, z_bottom)
        node_j, prox_id = agregar_nodo_muro(nodos, prox_id, x2, y2, z_bottom)
        # Nodos superiores auxiliares: permiten que Unity estime la altura real del panel.
        _, prox_id = agregar_nodo_muro(nodos, prox_id, x1, y1, z_top)
        _, prox_id = agregar_nodo_muro(nodos, prox_id, x2, y2, z_top)

        walls.append({
            "id": wall_id,
            "type": "muro",
            "nodeI": node_i,
            "nodeJ": node_j,
            "grosor": round(thickness, 4),
            "longitud": round(length, 4),
            "bottom": f"E2_Z{z_bottom:.2f}",
            "top": f"E2_Z{z_top:.2f}",
            "sourceBuilding": "edificio_2",
            "sourceId": wall.get("id", f"E2_W{wall_id}"),
        })
        wall_id += 1
    return walls, prox_id


def transformar_elementos(e2_elements, id_map):
    out = []
    for i, el in enumerate(e2_elements):
        out.append(agregar_seccion({
            "id": el["id"],
            "type": el.get("type", "viga"),
            "seccion": el.get("seccion", ""),
            "sectionId": el.get("sectionId", ""),
            "nodeI": id_map[el["nodeI"]],
            "nodeJ": id_map[el["nodeJ"]],
            "uniformLoad": el.get("uniformLoad", 0.0),
            "axialI": el.get("axialI", 0.0),
            "axialJ": el.get("axialJ", 0.0),
            "shearI": el.get("shearI", 0.0),
            "shearJ": el.get("shearJ", 0.0),
            "momentI": el.get("momentI", 0.0),
            "momentJ": el.get("momentJ", 0.0),
            "piso": el.get("piso", ""),
            "areaTributaria": el.get("tributaryArea", 0.0),
            "cargaTributaria": el.get("factoredLoad12D16L", 0.0),
        }))
    return out


def build_estructura_completa():
    e1 = cargar_json(EDIFICIO1_JSON)
    e2 = cargar_json(EDIFICIO2_JSON)
    e2_geometry = cargar_json(EDIFICIO2_GEOMETRY_JSON) if os.path.exists(EDIFICIO2_GEOMETRY_JSON) else {"walls": []}
    cargas_e1 = cargar_cargas_vigas_edificio1()

    # --- Nodos: edificio 1 (desplazado en Y para centrado) + edificio 2 (transformado) ---
    nodos = []
    for n in e1.get("nodes", []):
        nn = dict(n)
        nn["y"] = round(n["y"] + OFFSET_Y_E1, 6)
        nodos.append(nn)
    prox_id = max((n["id"] for n in nodos), default=0) + 1
    id_map = {}
    e2_nodes_sorted = sorted(e2.get("nodes", []), key=lambda n: n["id"])
    for n in e2_nodes_sorted:
        new_id = prox_id
        id_map[n["id"]] = new_id
        nodos.append({
            "id": new_id,
            "x": round(n["x"] + OFFSET_X, 6),
            "y": round(n["y"] + OFFSET_Y, 6),
            "z": round(n["z"] + OFFSET_Z, 6),
        })
        prox_id += 1

    # --- Elementos: edificio 1 + edificio 2 (remap ids) ---
    elementos = [enriquecer_edificio1(el, cargas_e1) for el in e1.get("elements", [])]
    id_e = max((el["id"] for el in elementos), default=0)
    e2_elems = []
    for el in e2.get("elements", []):
        id_e += 1
        e2_elems.append(agregar_seccion({
            "id": id_e,
            "type": el.get("type", "viga"),
            "seccion": el.get("seccion", ""),
            "sectionId": el.get("sectionId", ""),
            "sourceBuilding": "edificio_2",
            "sourceId": el.get("sourceId", el.get("id")),
            "elementTag": el.get("elementTag", el.get("sourceId", f"E2_{el.get('id')}")),
            "nodeI": id_map[el["nodeI"]],
            "nodeJ": id_map[el["nodeJ"]],
            "uniformLoad": el.get("uniformLoad", 0.0),
            "deadLoad": el.get("deadLoad", 0.0),
            "liveLoad": el.get("liveLoad", 0.0),
            "factoredLoad14D": el.get("factoredLoad14D", 0.0),
            "factoredLoad12D16L": el.get("factoredLoad12D16L", 0.0),
            "axialI": el.get("axialI", 0.0),
            "axialJ": el.get("axialJ", 0.0),
            "shearI": el.get("shearI", 0.0),
            "shearJ": el.get("shearJ", 0.0),
            "momentI": el.get("momentI", 0.0),
            "momentJ": el.get("momentJ", 0.0),
            "piso": "",
            "areaTributaria": el.get("tributaryArea", 0.0),
            "cargaTributaria": el.get("factoredLoad12D16L", 0.0),
        }))
    elementos.extend(e2_elems)

    # --- Calculo de momentos de empotramiento en vigas: M = -w*L^2/12 ---
    # Los JSON de origen solo traen cortante (shearI/J) y carga repartida
    # (uniformLoad); no traen momentos. Para que el diagrama de momentos del
    # viewer muestre valores reales, se calcula el momento de empotramiento de
    # cada viga con su luz L y su carga repartida w (convencion: negativo en los
    # extremos de una viga empotrada con carga hacia abajo). Solo se sobrescribe
    # si el elemento no tiene ya un momento calculado.
    coords = {n["id"]: (n["x"], n["y"], n["z"]) for n in nodos}
    for el in elementos:
        if el.get("type") != "viga":
            continue
        if el.get("momentI") != 0.0 or el.get("momentJ") != 0.0:
            continue
        w = el.get("uniformLoad", 0.0)
        if not w:
            continue
        a = coords.get(el["nodeI"])
        b = coords.get(el["nodeJ"])
        if a is None or b is None:
            continue
        luz = math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 + (b[2] - a[2]) ** 2)
        if luz <= 0.0:
            continue
        m = -w * luz * luz / 12.0
        el["momentI"] = round(m, 6)
        el["momentJ"] = round(m, 6)


    # --- Slabs: losas del edificio 1 (desplazadas en Y) + diafragmas del edificio 2 ---
    slabs = []
    for s in e1.get("slabs", []):
        ss = dict(s)
        ss["id"] = f"L{ss.get('id')}"
        ss["y0"] = round(s["y0"] + OFFSET_Y_E1, 6)
        ss["y1"] = round(s["y1"] + OFFSET_Y_E1, 6)
        slabs.append(ss)
    slabs.extend(convertir_slabs(e2))

    # --- Walls: edificio 1 + muros estructurales del edificio 2 ---
    walls = [dict(w) for w in e1.get("walls", [])]
    for w in walls:
        if w.get("nodeI") in id_map:
            w["nodeI"] = id_map[w["nodeI"]]
        if w.get("nodeJ") in id_map:
            w["nodeJ"] = id_map[w["nodeJ"]]
    next_wall_id = max((int(w.get("id", 0)) for w in walls if str(w.get("id", "")).isdigit()), default=0) + 1
    e2_walls, prox_id = convertir_muros_edificio2(e2_geometry, nodos, prox_id, next_wall_id)
    walls.extend(e2_walls)

    # --- Supports ---
    supports = list(e1.get("supports", []))
    for s in e2.get("supports", []):
        sp = dict(s)
        sp["node"] = id_map[s["node"]]
        supports.append(sp)

    # --- Point loads (cargas puntuales) ---
    point_loads = list(e1.get("pointLoads", []))
    for pl in e2.get("pointLoads", []):
        p = dict(pl)
        p["node"] = id_map[pl["node"]]
        point_loads.append(p)

    # --- Tributary floors (info de areas por piso, edificio 1) ---
    tributary = list(e1.get("tributaryList", []))

    estructura = {
        "units": e1.get("units", "kN-m"),
        "q_G": e1.get("q_G", 5.1),
        "nodes": nodos,
        "elements": elementos,
        "walls": walls,
        "supports": supports,
        "diaphragms": e1.get("diaphragms", []),
        "diaphragmList": e1.get("diaphragmList", []),
        "slabs": slabs,
        "tributaryAreasByFloor": e1.get("tributaryAreasByFloor", {}),
        "tributaryList": tributary,
        "localAxes": e1.get("localAxes", []),
        "pointLoads": point_loads,
        "sections": SECTIONS,
        "statistics": (
            e1.get("statistics", {})
            if isinstance(e1.get("statistics"), dict)
            else {"buildings": {"edificio1": len(e1["nodes"]), "edificio2": len(e2["nodes"])}}
        ),
    }
    return estructura


def main():
    estructura = build_estructura_completa()
    os.makedirs(RESULT_DIR, exist_ok=True)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(estructura, f, ensure_ascii=False, indent=2)
    print(f"JSON unificado: {OUT_JSON}")

    # Copiar al viewer Unity del edificio completo (si existe)
    unity_resources = os.path.join(COMPLETO_DIR, "unity_visualizador", "Assets", "Resources")
    if os.path.isdir(unity_resources):
        unity_path = os.path.join(unity_resources, UNITY_JSON_NAME)
        with open(unity_path, "w", encoding="utf-8") as f:
            json.dump(estructura, f, ensure_ascii=False, indent=2)
        print(f"Exportado Unity: {unity_path}")
    else:
        print(f"(no hay viewer Unity en {unity_resources}; JSON en resultados/)")

    print(f"\nResumen:")
    print(f"  Nodos      : {len(estructura['nodes'])}  (e1: {len([n for n in estructura['nodes'] if n['id']<=300])}, e2: {len([n for n in estructura['nodes'] if n['id']>300])})")
    print(f"  Elementos  : {len(estructura['elements'])}")
    print(f"  Losas/slabs: {len(estructura['slabs'])}")
    print(f"  Muros      : {len(estructura['walls'])}")
    print(f"  Apoyos     : {len(estructura['supports'])}")
    xs = [n["x"] for n in estructura["nodes"]]
    ys = [n["y"] for n in estructura["nodes"]]
    print(f"  Rango X    : [{min(xs):.3f}, {max(xs):.3f}]")
    print(f"  Rango Y    : [{min(ys):.3f}, {max(ys):.3f}]")


if __name__ == "__main__":
    main()
