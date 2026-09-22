#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Modelo OpenSees y verificador de cargas del edificio completo.

Uso rapido:
  python opensees_edificio_completo.py
  python opensees_edificio_completo.py --id B3002_V60/80
  python opensees_edificio_completo.py --id 359
  python opensees_edificio_completo.py --id L1
"""

import argparse
import json
import math
from pathlib import Path

import openseespy.opensees as ops


BASE_DIR = Path(__file__).resolve().parent
COMPLETO_DIR = BASE_DIR.parent
JSON_PATH = COMPLETO_DIR / "unity_visualizador" / "Assets" / "Resources" / "estructura_completo_unity.json"

# Si prefieres no usar argumentos en consola, escribe aqui el ID y ejecuta el script.
# Ejemplos: "B3002_V60/80", "359", "E1_122", "L1".
ID_A_CONSULTAR = ""

E_CONCRETE_KN_M2 = 25_000_000.0
NU_CONCRETE = 0.20
G_CONCRETE_KN_M2 = E_CONCRETE_KN_M2 / (2.0 * (1.0 + NU_CONCRETE))


def load_data(path=JSON_PATH):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def section_properties(width, height):
    area = width * height
    iy = width * height**3 / 12.0
    iz = height * width**3 / 12.0
    j = iy + iz
    return area, iy, iz, j


def element_length(element, nodes):
    ni = nodes[element["nodeI"]]
    nj = nodes[element["nodeJ"]]
    return math.dist((ni["x"], ni["y"], ni["z"]), (nj["x"], nj["y"], nj["z"]))


def add_transformations():
    ops.geomTransf("Linear", 1, 0.0, 0.0, 1.0)  # vigas horizontales
    ops.geomTransf("Linear", 2, 1.0, 0.0, 0.0)  # columnas verticales


def transformation_tag(element, nodes):
    ni = nodes[element["nodeI"]]
    nj = nodes[element["nodeJ"]]
    dz = abs(nj["z"] - ni["z"])
    length = element_length(element, nodes)
    if length > 0.0 and dz / length > 0.90:
        return 2
    return 1


def build_opensees_model(data):
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    nodes = {node["id"]: node for node in data.get("nodes", [])}
    for node in nodes.values():
        ops.node(node["id"], node["x"], node["y"], node["z"])

    fixed_supports = []
    for support in data.get("supports", []):
        node_id = support.get("node")
        if node_id not in nodes:
            continue
        ops.fix(
            node_id,
            support.get("ux", 0),
            support.get("uy", 0),
            support.get("uz", 0),
            support.get("rx", 0),
            support.get("ry", 0),
            support.get("rz", 0),
        )
        fixed_supports.append(node_id)

    add_transformations()
    created_elements = []
    skipped_elements = []
    for element in data.get("elements", []):
        if element.get("nodeI") not in nodes or element.get("nodeJ") not in nodes:
            skipped_elements.append(element.get("id"))
            continue

        width = float(element.get("width_m") or 0.60)
        height = float(element.get("height_m") or 0.80)
        area, iy, iz, j = section_properties(width, height)
        transf_tag = transformation_tag(element, nodes)

        ops.element(
            "elasticBeamColumn",
            element["id"],
            element["nodeI"],
            element["nodeJ"],
            area,
            E_CONCRETE_KN_M2,
            G_CONCRETE_KN_M2,
            j,
            iy,
            iz,
            transf_tag,
        )
        created_elements.append(element["id"])

    return {
        "nodes_created": len(nodes),
        "fixed_supports": fixed_supports,
        "elements_created": created_elements,
        "skipped_elements": skipped_elements,
    }


def normalized_text(value):
    return str(value).strip().lower()


def matches_id(item, wanted):
    wanted_text = normalized_text(wanted)
    for key in ("id", "elementTag", "sourceId", "beam_id"):
        if key in item and normalized_text(item[key]) == wanted_text:
            return True
    return False


def load_info(element):
    length = element.get("length_m")
    uniform = float(element.get("uniformLoad") or 0.0)
    area = float(element.get("areaTributaria") or element.get("tributaryArea") or 0.0)
    gravity = float(element.get("gravityLoad") or element.get("cargaTributaria") or 0.0)
    dead = element.get("deadLoad")
    live = element.get("liveLoad")
    u14 = element.get("factoredLoad14D")
    u1216 = element.get("factoredLoad12D16L")

    if dead is None and element.get("sourceBuilding") == "edificio_1":
        dead = gravity
    if live is None and element.get("sourceBuilding") == "edificio_1":
        live = 0.0
    if u14 is None and dead is not None:
        u14 = 1.4 * float(dead)
    if u1216 is None and dead is not None and live is not None:
        u1216 = 1.2 * float(dead) + 1.6 * float(live)

    return {
        "area_tributaria_m2": area,
        "carga_gravitacional_disponible_kN": gravity,
        "carga_muerta_D_kN": dead,
        "carga_viva_L_kN": live,
        "U_1_4D_kN": u14,
        "U_1_2D_1_6L_kN": u1216,
        "carga_lineal_uniformLoad_kN_m": uniform,
        "largo_m": length,
    }


def estimated_beam_forces(element):
    length = float(element.get("length_m") or 0.0)
    uniform = abs(float(element.get("uniformLoad") or 0.0))
    moment_i = float(element.get("momentI") or 0.0)
    moment_j = float(element.get("momentJ") or 0.0)
    span_moment = uniform * length * length / 8.0 if length > 0.0 else 0.0
    max_shear = uniform * length / 2.0 if length > 0.0 else 0.0
    return {
        "momento_extremo_i_kN_m": moment_i,
        "momento_extremo_j_kN_m": moment_j,
        "momento_max_vano_estimado_kN_m": span_moment,
        "corte_max_estimado_kN": max_shear,
        "formula_momento_vano": "Mmax = qL^2/8 usando uniformLoad",
        "formula_corte": "Vmax = qL/2 usando uniformLoad",
    }


def find_element(data, wanted_id):
    for element in data.get("elements", []):
        if matches_id(element, wanted_id):
            return element
    return None


def find_slab(data, wanted_id):
    wanted = normalized_text(wanted_id)
    for slab in data.get("slabs", []):
        slab_id = str(slab.get("id"))
        slab_number = slab_id[1:] if slab_id[:1].lower() in ("l", "s") else slab_id
        slab_ids = [slab_id, slab_number, f"L{slab_number}", f"S{slab_number}"]
        if any(normalized_text(value) == wanted for value in slab_ids):
            return slab
    return None


def slab_report(slab, data):
    area = abs((slab["x1"] - slab["x0"]) * (slab["y1"] - slab["y0"]))
    q_g = float(data.get("q_G") or 0.0)
    gravity = area * q_g
    return {
        "tipo": "losa/diafragma_area",
        "id": slab.get("id"),
        "nivel": slab.get("nivel"),
        "area_m2": area,
        "q_G_kN_m2": q_g,
        "carga_gravitacional_estim_kN": gravity,
        "nota": "La losa se consulta como area. No esta modelada como shell en OpenSees.",
    }


def element_report(element, data):
    nodes = {node["id"]: node for node in data.get("nodes", [])}
    out = dict(element)
    if element.get("nodeI") in nodes and element.get("nodeJ") in nodes:
        out["length_m"] = element_length(element, nodes)

    report = {
        "tipo": element.get("type"),
        "opensees_element_id": element.get("id"),
        "elementTag": element.get("elementTag"),
        "sourceBuilding": element.get("sourceBuilding"),
        "sourceId": element.get("sourceId"),
        "sectionId": element.get("sectionId"),
        "dimensiones_m": {"ancho": element.get("width_m"), "alto": element.get("height_m")},
        "nodos": {"i": element.get("nodeI"), "j": element.get("nodeJ")},
        "cargas": load_info(out),
        "fuerzas_para_unity": {
            "axialI_kN": element.get("axialI"),
            "axialJ_kN": element.get("axialJ"),
            "shearI_kN": element.get("shearI"),
            "shearJ_kN": element.get("shearJ"),
            "momentI_kN_m": element.get("momentI"),
            "momentJ_kN_m": element.get("momentJ"),
        },
    }
    if element.get("type") == "viga":
        report["momento_y_corte_estimado"] = estimated_beam_forces(out)
    if element.get("type") == "columna":
        report["nota"] = "Para columnas se reporta axial acumulado si viene en el JSON. Area tributaria directa puede venir en 0."
    if element.get("loadNote"):
        report["nota_carga"] = element.get("loadNote")
    return report


def query_id(data, wanted_id):
    element = find_element(data, wanted_id)
    if element is not None:
        return element_report(element, data)
    slab = find_slab(data, wanted_id)
    if slab is not None:
        return slab_report(slab, data)
    return {
        "error": "No se encontro el ID solicitado.",
        "id_buscado": wanted_id,
        "ayuda": "Usa IDs numericos de elementos OpenSees, elementTag/sourceId si existen, o IDs de losa tipo L1 o D101.",
    }


def main():
    parser = argparse.ArgumentParser(description="OpenSees + consulta de cargas del edificio completo")
    parser.add_argument("--id", dest="query", help="ID de viga, columna o losa a consultar")
    parser.add_argument("--json", default=str(JSON_PATH), help="Ruta al JSON del edificio completo")
    parser.add_argument("--solo-consulta", action="store_true", help="No arma el modelo OpenSees, solo consulta el JSON")
    args = parser.parse_args()

    data = load_data(Path(args.json))
    if not args.solo_consulta:
        status = build_opensees_model(data)
        print("OpenSees edificio completo creado")
        print(f"  Nodos     : {status['nodes_created']}")
        print(f"  Apoyos    : {len(status['fixed_supports'])}")
        print(f"  Elementos : {len(status['elements_created'])}")
        if status["skipped_elements"]:
            print(f"  Saltados  : {len(status['skipped_elements'])}")

    query = args.query or ID_A_CONSULTAR
    if query:
        print(json.dumps(query_id(data, query), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
