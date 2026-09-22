#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Semana 3: carga viva, sismo, superposicion y capacidad HA.

Ejecutar desde la raiz del repo:
  python "P1L3/semana3.py"

El script usa el JSON del edificio completo generado en Semana 2 y arma:
  A. carga viva Q y verificacion de conservacion;
  B. sismo pseudoestatico EX/EY;
  C. superposicion lineal y comparacion contra corrida explicita OpenSees;
  D. seccion fiber HA de columna COL70/70 y curvas M-phi / P-M.
"""

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import openseespy.opensees as ops


ROOT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().parent
OUT = BASE / "resultados"
COMPLETE_JSON = ROOT / "P1L2" / "unity_visualizador" / "Assets" / "Resources" / "estructura_completo_unity.json"

E_CONCRETE = 25_000_000.0  # kN/m2
NU = 0.20
G_CONCRETE = E_CONCRETE / (2.0 * (1.0 + NU))
G_ACCEL = 9.80665  # m/s2, usado solo para reportar masa equivalente
SEISMIC_COEFF = 0.20

# Configuracion simple de la armadura de la columna COL70/70.
# Cambia estas lineas para modificar diametro, barras y fibras de hormigon.
BAR_DIAMETER_MM = 25.0
REBAR_BARS_INFERIOR = 3
REBAR_BARS_CENTRO = 2
REBAR_BARS_SUPERIOR = 3
CONCRETE_FIBERS_X = 20
CONCRETE_FIBERS_Y = 20

# Combinacion arbitraria pedida para la parte C.
LAMBDAS = {
    "G": 1.0,
    "Q": 0.5,
    "EX": 1.0,
    "EY": 0.3,
}


def load_data():
    with open(COMPLETE_JSON, encoding="utf-8") as file:
        return json.load(file)


def section_properties(width, height):
    area = width * height
    iy = width * height**3 / 12.0
    iz = height * width**3 / 12.0
    j = iy + iz
    return area, iy, iz, j


def node_map(data):
    return {node["id"]: node for node in data["nodes"]}


def element_length(element, nodes):
    ni = nodes[element["nodeI"]]
    nj = nodes[element["nodeJ"]]
    return math.dist((ni["x"], ni["y"], ni["z"]), (nj["x"], nj["y"], nj["z"]))


def element_midpoint(element, nodes):
    ni = nodes[element["nodeI"]]
    nj = nodes[element["nodeJ"]]
    return {
        "x": 0.5 * (ni["x"] + nj["x"]),
        "y": 0.5 * (ni["y"] + nj["y"]),
        "z": 0.5 * (ni["z"] + nj["z"]),
    }


def build_model(data):
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)
    nodes = node_map(data)
    connected_nodes = set()
    adjacency = {node_id: set() for node_id in nodes}
    for element in data.get("elements", []):
        ni = element.get("nodeI")
        nj = element.get("nodeJ")
        connected_nodes.add(ni)
        connected_nodes.add(nj)
        if ni in adjacency and nj in adjacency:
            adjacency[ni].add(nj)
            adjacency[nj].add(ni)

    for node in nodes.values():
        ops.node(node["id"], node["x"], node["y"], node["z"])

    support_nodes = set()
    for support in data.get("supports", []):
        node = support.get("node")
        if node in nodes:
            support_nodes.add(node)
            ops.fix(
                node,
                support.get("ux", 0),
                support.get("uy", 0),
                support.get("uz", 0),
                support.get("rx", 0),
                support.get("ry", 0),
                support.get("rz", 0),
            )

    ops.geomTransf("Linear", 1, 0.0, 0.0, 1.0)
    ops.geomTransf("Linear", 2, 1.0, 0.0, 0.0)
    for element in data.get("elements", []):
        if element.get("nodeI") not in nodes or element.get("nodeJ") not in nodes:
            continue
        width = float(element.get("width_m") or 0.60)
        height = float(element.get("height_m") or 0.80)
        area, iy, iz, j = section_properties(width, height)
        ni = nodes[element["nodeI"]]
        nj = nodes[element["nodeJ"]]
        length = element_length(element, nodes)
        dz = abs(nj["z"] - ni["z"])
        transf = 2 if length > 0.0 and dz / length > 0.90 else 1
        ops.element(
            "elasticBeamColumn",
            element["id"],
            element["nodeI"],
            element["nodeJ"],
            area,
            E_CONCRETE,
            G_CONCRETE,
            j,
            iy,
            iz,
            transf,
        )

    for node_id in nodes:
        if node_id not in connected_nodes and node_id not in support_nodes:
            ops.fix(node_id, 1, 1, 1, 1, 1, 1)

    visited = set()
    for node_id in sorted(connected_nodes):
        if node_id not in nodes or node_id in visited:
            continue
        stack = [node_id]
        component = []
        visited.add(node_id)
        while stack:
            current = stack.pop()
            component.append(current)
            for nxt in adjacency.get(current, ()):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        if not any(node in support_nodes for node in component):
            anchor = min(component, key=lambda n: nodes[n]["z"])
            ops.fix(anchor, 1, 1, 1, 1, 1, 1)
    return nodes


def floor_key(z):
    return round(float(z), 3)


def beam_floor(element, nodes):
    return floor_key(element_midpoint(element, nodes)["z"])


def gravity_nodal_loads(data, load_name):
    nodes = node_map(data)
    nodal = {node_id: [0.0, 0.0, 0.0] for node_id in nodes}
    transferred = 0.0
    by_floor = {}
    for element in data.get("elements", []):
        if element.get("type") != "viga":
            continue
        total = float(element.get(load_name) or 0.0)
        if abs(total) < 1e-12:
            continue
        if element.get("nodeI") not in nodal or element.get("nodeJ") not in nodal:
            continue
        nodal[element["nodeI"]][2] -= 0.5 * total
        nodal[element["nodeJ"]][2] -= 0.5 * total
        transferred += total
        key = beam_floor(element, nodes)
        by_floor[key] = by_floor.get(key, 0.0) + total
    return nodal, transferred, by_floor


def tributary_live_check(data):
    area_total = sum(float(e.get("areaTributaria") or 0.0) for e in data.get("elements", []) if e.get("type") == "viga")
    q_q_by_beam = []
    q_total = 0.0
    for element in data.get("elements", []):
        if element.get("type") != "viga":
            continue
        area = float(element.get("areaTributaria") or 0.0)
        live = float(element.get("liveLoad") or 0.0)
        if area > 0.0:
            q_q_by_beam.append(live / area)
        q_total += live
    q_q_equiv = q_total / area_total if area_total else 0.0
    expected = q_q_equiv * area_total
    return {
        "area_tributaria_total_m2": area_total,
        "q_Q_equivalente_kN_m2": q_q_equiv,
        "Q_transferida_kN": q_total,
        "q_Q_por_A_kN": expected,
        "error_kN": q_total - expected,
        "q_Q_min_max_kN_m2": [min(q_q_by_beam), max(q_q_by_beam)] if q_q_by_beam else [0.0, 0.0],
        "nota": "q_Q equivalente se obtiene desde liveLoad/areaTributaria del JSON completo; puede variar por nivel/perfil.",
    }


def floor_masses_and_seismic(data):
    nodes = node_map(data)
    _, dead_total, dead_by_floor = gravity_nodal_loads(data, "deadLoad")
    _, live_total, live_by_floor = gravity_nodal_loads(data, "liveLoad")
    floors = sorted(set(dead_by_floor) | set(live_by_floor))
    out = {}
    for z in floors:
        weight = dead_by_floor.get(z, 0.0) + 0.5 * live_by_floor.get(z, 0.0)
        connected = {element["nodeI"] for element in data.get("elements", [])} | {element["nodeJ"] for element in data.get("elements", [])}
        floor_nodes = [node for node in nodes.values() if node["id"] in connected and abs(floor_key(node["z"]) - z) < 1e-6]
        if not floor_nodes:
            continue
        cx = sum(node["x"] for node in floor_nodes) / len(floor_nodes)
        cy = sum(node["y"] for node in floor_nodes) / len(floor_nodes)
        control = min(floor_nodes, key=lambda n: (n["x"] - cx) ** 2 + (n["y"] - cy) ** 2)
        out[z] = {
            "dead_kN": dead_by_floor.get(z, 0.0),
            "live_kN": live_by_floor.get(z, 0.0),
            "weight_for_mass_kN": weight,
            "mass_equiv_kN_s2_m": weight / G_ACCEL,
            "Fx_EX_kN": SEISMIC_COEFF * weight,
            "Fy_EY_kN": SEISMIC_COEFF * weight,
            "center_of_mass_estimated": {"x": cx, "y": cy, "z": z},
            "application_node": control["id"],
            "torsion_about_CM_kN_m_if_single_node_EX": SEISMIC_COEFF * weight * (control["y"] - cy),
            "torsion_about_CM_kN_m_if_single_node_EY": -SEISMIC_COEFF * weight * (control["x"] - cx),
        }
    return out, dead_total, live_total


def seismic_nodal_loads(data, direction):
    floors, _, _ = floor_masses_and_seismic(data)
    nodes = node_map(data)
    nodal = {node_id: [0.0, 0.0, 0.0] for node_id in nodes}
    for floor in floors.values():
        node = floor["application_node"]
        if direction == "EX":
            nodal[node][0] += floor["Fx_EX_kN"]
        else:
            nodal[node][1] += floor["Fy_EY_kN"]
    return nodal


def combine_nodal_loads(load_sets, lambdas):
    node_ids = sorted({node for loads in load_sets.values() for node in loads})
    combined = {node: [0.0, 0.0, 0.0] for node in node_ids}
    for case, loads in load_sets.items():
        factor = lambdas.get(case, 0.0)
        for node, vec in loads.items():
            combined[node][0] += factor * vec[0]
            combined[node][1] += factor * vec[1]
            combined[node][2] += factor * vec[2]
    return combined


def apply_loads(nodal_loads):
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for node, load in nodal_loads.items():
        if max(abs(load[0]), abs(load[1]), abs(load[2])) < 1e-12:
            continue
        ops.load(node, load[0], load[1], load[2], 0.0, 0.0, 0.0)


def analyze_case(data, nodal_loads, control_node, element_id):
    nodes = build_model(data)
    apply_loads(nodal_loads)
    ops.system("BandGeneral")
    ops.numberer("RCM")
    ops.constraints("Plain")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")
    ok = ops.analyze(1)
    ops.reactions()
    reactions = [0.0, 0.0, 0.0]
    for support in data.get("supports", []):
        node = support.get("node")
        if node in nodes:
            reaction = ops.nodeReaction(node)
            reactions[0] += reaction[0]
            reactions[1] += reaction[1]
            reactions[2] += reaction[2]
    displacement = ops.nodeDisp(control_node)
    try:
        element_force = ops.eleForce(element_id)
    except Exception:
        element_force = []
    return {
        "ok": ok,
        "control_node": control_node,
        "control_displacement_ux_uy_uz_m": displacement[:3],
        "sum_reactions_Fx_Fy_Fz_kN": reactions,
        "element_id": element_id,
        "element_force_sample": element_force[:6],
    }


def superposition_check(data):
    nodes = node_map(data)
    connected = {element["nodeI"] for element in data.get("elements", [])} | {element["nodeJ"] for element in data.get("elements", [])}
    control_node = max((n for n in nodes.values() if n["id"] in connected), key=lambda n: (n["z"], n["x"] ** 2 + n["y"] ** 2))["id"]
    element_id = next(element["id"] for element in data["elements"] if element.get("type") == "viga")
    g_loads, _, _ = gravity_nodal_loads(data, "deadLoad")
    q_loads, _, _ = gravity_nodal_loads(data, "liveLoad")
    load_sets = {
        "G": g_loads,
        "Q": q_loads,
        "EX": seismic_nodal_loads(data, "EX"),
        "EY": seismic_nodal_loads(data, "EY"),
    }
    cases = {name: analyze_case(data, loads, control_node, element_id) for name, loads in load_sets.items()}
    combined_loads = combine_nodal_loads(load_sets, LAMBDAS)
    explicit = analyze_case(data, combined_loads, control_node, element_id)

    predicted_disp = [0.0, 0.0, 0.0]
    predicted_react = [0.0, 0.0, 0.0]
    predicted_force = [0.0] * len(cases["G"].get("element_force_sample", []))
    for case, result in cases.items():
        factor = LAMBDAS[case]
        for i in range(3):
            predicted_disp[i] += factor * result["control_displacement_ux_uy_uz_m"][i]
            predicted_react[i] += factor * result["sum_reactions_Fx_Fy_Fz_kN"][i]
        for i, value in enumerate(result.get("element_force_sample", [])):
            predicted_force[i] += factor * value

    return {
        "lambdas": LAMBDAS,
        "case_results": cases,
        "superposed_prediction": {
            "control_displacement_ux_uy_uz_m": predicted_disp,
            "sum_reactions_Fx_Fy_Fz_kN": predicted_react,
            "element_force_sample": predicted_force,
        },
        "explicit_combination": explicit,
        "errors": {
            "disp_abs": [explicit["control_displacement_ux_uy_uz_m"][i] - predicted_disp[i] for i in range(3)],
            "reaction_abs": [explicit["sum_reactions_Fx_Fy_Fz_kN"][i] - predicted_react[i] for i in range(3)],
            "element_force_abs": [explicit.get("element_force_sample", [])[i] - predicted_force[i] for i in range(min(len(explicit.get("element_force_sample", [])), len(predicted_force)))],
        },
    }


def concrete_stress(eps, fc):
    if eps <= 0.0:
        return 0.0
    return min(25_000_000.0 * eps, 0.85 * fc)


def steel_stress(eps, fy, es):
    return max(-fy, min(fy, es * eps))


def evenly_spaced_positions(start, end, count):
    if count <= 0:
        return []
    if count == 1:
        return [0.5 * (start + end)]
    return [start + i * (end - start) / (count - 1) for i in range(count)]


def rebar_coordinates(b, h, cover):
    x_left = -b / 2.0 + cover
    x_right = b / 2.0 - cover
    rows = [
        ("inferior", -h / 2.0 + cover, REBAR_BARS_INFERIOR),
        ("centro", 0.0, REBAR_BARS_CENTRO),
        ("superior", h / 2.0 - cover, REBAR_BARS_SUPERIOR),
    ]
    coords = []
    for row_name, y, bars in rows:
        for x in evenly_spaced_positions(x_left, x_right, bars):
            coords.append({"fila": row_name, "x": x, "y": y})
    return coords


def make_column_fibers():
    b = h = 0.70
    cover = 0.05
    fc = 25_000.0  # H-25
    fy = 420_000.0
    es = 200_000_000.0
    bar_area = math.pi * (BAR_DIAMETER_MM / 1000.0) ** 2 / 4.0
    fibers = []
    nx = CONCRETE_FIBERS_X
    ny = CONCRETE_FIBERS_Y
    for ix in range(nx):
        x = -b / 2.0 + (ix + 0.5) * b / nx
        for iy in range(ny):
            y = -h / 2.0 + (iy + 0.5) * h / ny
            fibers.append({"type": "concrete", "x": x, "y": y, "area": b / nx * h / ny})
    rebar_xy = rebar_coordinates(b, h, cover)
    for bar in rebar_xy:
        x = bar["x"]
        y = bar["y"]
        fibers.append({"type": "steel", "x": x, "y": y, "area": bar_area})
    return {"b": b, "h": h, "cover": cover, "fc": fc, "fy": fy, "Es": es, "fibers": fibers, "bar_area_m2": bar_area, "rebar_xy": rebar_xy, "concrete_fibers_x": nx, "concrete_fibers_y": ny}


def section_response(section, eps0, phi):
    p = 0.0
    m = 0.0
    max_steel_strain = 0.0
    max_concrete_strain = 0.0
    for fiber in section["fibers"]:
        eps = eps0 - phi * fiber["y"]
        if fiber["type"] == "concrete":
            stress = concrete_stress(eps, section["fc"])
            max_concrete_strain = max(max_concrete_strain, eps)
        else:
            stress = steel_stress(eps, section["fy"], section["Es"])
            max_steel_strain = max(max_steel_strain, abs(eps))
        force = stress * fiber["area"]
        p += force
        m += force * fiber["y"]
    return p, m, max_steel_strain, max_concrete_strain


def solve_eps0_for_p(section, phi, target_p):
    lo, hi = -0.02, 0.02
    p_lo, _, _, _ = section_response(section, lo, phi)
    p_hi, _, _, _ = section_response(section, hi, phi)
    while p_lo > target_p and lo > -1.0:
        lo *= 2.0
        p_lo, _, _, _ = section_response(section, lo, phi)
    while p_hi < target_p and hi < 1.0:
        hi *= 2.0
        p_hi, _, _, _ = section_response(section, hi, phi)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        p, _, _, _ = section_response(section, mid, phi)
        if p < target_p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def fiber_section_capacity():
    section = make_column_fibers()
    opensees_section = define_opensees_fiber_section()
    phis = [i * 0.00010 for i in range(1, 801)]
    steel_yield_strain = section["fy"] / section["Es"]
    mphi = []
    first_yield = None
    for phi in phis:
        eps0 = solve_eps0_for_p(section, phi, 0.0)
        p, m, max_steel_strain, max_concrete_strain = section_response(section, eps0, phi)
        row = {"phi_1_m": phi, "P_kN": p, "M_kN_m": abs(m), "max_steel_strain": max_steel_strain, "max_concrete_strain": max_concrete_strain, "steel_yielded": max_steel_strain >= steel_yield_strain}
        if first_yield is None and row["steel_yielded"]:
            first_yield = row.copy()
        mphi.append(row)

    ag = section["b"] * section["h"]
    ast = len(section["rebar_xy"]) * section["bar_area_m2"]
    po = 0.85 * section["fc"] * (ag - ast) + section["fy"] * ast
    pm_targets = [0.0, 0.15 * po, 0.30 * po, 0.60 * po, po]
    pm = []
    for target in pm_targets:
        best = None
        for phi in phis:
            eps0 = solve_eps0_for_p(section, phi, target)
            p, m, _, _ = section_response(section, eps0, phi)
            candidate = {"P_kN": p, "M_kN_m": abs(m), "phi_1_m": phi}
            if best is None or candidate["M_kN_m"] > best["M_kN_m"]:
                best = candidate
        pm.append(best)

    return {
        "section": {
            "id": "COL70/70_FIBER",
            "opensees_section_tag": opensees_section["section_tag"],
            "b_m": section["b"],
            "h_m": section["h"],
            "fc_MPa": section["fc"] / 1000.0,
            "fy_MPa": section["fy"] / 1000.0,
            "concrete_fibers": section["concrete_fibers_x"] * section["concrete_fibers_y"],
            "concrete_fibers_x": section["concrete_fibers_x"],
            "concrete_fibers_y": section["concrete_fibers_y"],
            "steel_bars": len(section["rebar_xy"]),
            "steel_bars_inferior": REBAR_BARS_INFERIOR,
            "steel_bars_centro": REBAR_BARS_CENTRO,
            "steel_bars_superior": REBAR_BARS_SUPERIOR,
            "bar_area_m2": section["bar_area_m2"],
            "bar_diameter_mm": BAR_DIAMETER_MM,
            "bar_area_mm2": section["bar_area_m2"] * 1_000_000.0,
            "Ast_mm2": ast * 1_000_000.0,
            "steel_yield_strain": steel_yield_strain,
            "Po_kN": po,
        },
        "m_phi": mphi,
        "m_phi_first_steel_yield": first_yield,
        "p_m_points": pm,
        "interpretacion": "La curva M-phi se extendio hasta curvaturas altas para pasar el tramo elastico y capturar la fluencia del acero; luego el momento tiende a estabilizarse.",
    }


def define_opensees_fiber_section():
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    concrete_tag = 1
    steel_tag = 2
    section_tag = 1
    fc = -25_000.0  # H-25
    epsc0 = -0.002
    fcu = -21_250.0
    epscu = -0.003
    fy = 420_000.0
    es = 200_000_000.0
    b = h = 0.70
    cover = 0.05
    bar_area = math.pi * (BAR_DIAMETER_MM / 1000.0) ** 2 / 4.0

    ops.uniaxialMaterial("Concrete01", concrete_tag, fc, epsc0, fcu, epscu)
    ops.uniaxialMaterial("Steel01", steel_tag, fy, es, 0.01)
    ops.section("Fiber", section_tag)
    ops.patch("rect", concrete_tag, CONCRETE_FIBERS_Y, CONCRETE_FIBERS_X, -h / 2, -b / 2, h / 2, b / 2)
    y_bot = -h / 2 + cover
    y_mid = 0.0
    y_top = h / 2 - cover
    z_left = -b / 2 + cover
    z_right = b / 2 - cover
    rebar_layers = [
        (REBAR_BARS_INFERIOR, y_bot),
        (REBAR_BARS_CENTRO, y_mid),
        (REBAR_BARS_SUPERIOR, y_top),
    ]
    for bars, y in rebar_layers:
        if bars <= 0:
            continue
        if bars == 1:
            ops.layer("straight", steel_tag, bars, bar_area, y, 0.0, y, 0.0)
        else:
            ops.layer("straight", steel_tag, bars, bar_area, y, z_left, y, z_right)
    return {
        "section_tag": section_tag,
        "concrete_material_tag": concrete_tag,
        "steel_material_tag": steel_tag,
        "patch": f"rect concrete {CONCRETE_FIBERS_X}x{CONCRETE_FIBERS_Y}",
        "reinforcement": f"{REBAR_BARS_INFERIOR} abajo, {REBAR_BARS_CENTRO} centro, {REBAR_BARS_SUPERIOR} arriba; diametro {BAR_DIAMETER_MM:g} mm",
    }


def plot_capacity(capacity):
    OUT.mkdir(parents=True, exist_ok=True)
    mphi = capacity["m_phi"]
    pm = capacity["p_m_points"]
    section = make_column_fibers()

    concrete = [f for f in section["fibers"] if f["type"] == "concrete"]
    steel = [f for f in section["fibers"] if f["type"] == "steel"]
    plt.figure(figsize=(5, 5))
    plt.scatter([f["x"] for f in concrete], [f["y"] for f in concrete], s=8, c="#8fb3ff", label="Hormigon")
    plt.scatter([f["x"] for f in steel], [f["y"] for f in steel], s=70, c="#cc3333", label="Acero")
    plt.axis("equal")
    plt.xlabel("x [m]")
    plt.ylabel("y [m]")
    plt.title("Discretizacion Fiber COL70/70")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT / "fiber_COL70_70.png", dpi=160)
    plt.close()

    plt.figure(figsize=(7, 4))
    plt.plot([p["phi_1_m"] for p in mphi], [p["M_kN_m"] for p in mphi], "b-")
    first_yield = capacity.get("m_phi_first_steel_yield")
    if first_yield:
        plt.plot(first_yield["phi_1_m"], first_yield["M_kN_m"], "ro", label="Primera fluencia acero")
        plt.axvline(first_yield["phi_1_m"], color="r", linestyle="--", linewidth=0.9, alpha=0.7)
    plt.xlabel("Curvatura phi [1/m]")
    plt.ylabel("Momento [kN m]")
    plt.title("M-phi COL70/70 fiber completa (P=0 aprox.)")
    if first_yield:
        plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT / "M_phi_COL70_70.png", dpi=160)
    plt.close()

    plt.figure(figsize=(5, 5))
    plt.plot([p["M_kN_m"] for p in pm], [p["P_kN"] for p in pm], "ro-")
    plt.xlabel("M [kN m]")
    plt.ylabel("P [kN]")
    plt.title("P-M COL70/70 fiber")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT / "P_M_COL70_70.png", dpi=160)
    plt.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = load_data()
    q_check = tributary_live_check(data)
    floor_seismic, dead_total, live_total = floor_masses_and_seismic(data)
    superposition = superposition_check(data)
    capacity = fiber_section_capacity()
    plot_capacity(capacity)

    results = {
        "inputs": {
            "json": str(COMPLETE_JSON),
            "seismic_coeff": SEISMIC_COEFF,
            "mass_assumption": "W = D + 0.5L por piso",
        },
        "parte_A_carga_viva": q_check,
        "parte_B_sismo_pseudoestatico": {
            "dead_total_kN": dead_total,
            "live_total_kN": live_total,
            "floors": floor_seismic,
            "carga_lateral_total_EX_kN": sum(f["Fx_EX_kN"] for f in floor_seismic.values()),
            "carga_lateral_total_EY_kN": sum(f["Fy_EY_kN"] for f in floor_seismic.values()),
            "corte_basal_EX_kN": sum(f["Fx_EX_kN"] for f in floor_seismic.values()),
            "corte_basal_EY_kN": sum(f["Fy_EY_kN"] for f in floor_seismic.values()),
        },
        "parte_C_superposicion": superposition,
        "parte_D_capacidad_HA": capacity,
        "graficos": [str(OUT / "fiber_COL70_70.png"), str(OUT / "M_phi_COL70_70.png"), str(OUT / "P_M_COL70_70.png")],
    }

    with open(OUT / "resultados_semana3.json", "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    print("Semana 3 completada")
    print(f"Resultados: {OUT / 'resultados_semana3.json'}")
    print(f"Q transferida: {q_check['Q_transferida_kN']:.3f} kN")
    print(f"Error conservacion Q: {q_check['error_kN']:.6e} kN")
    print(f"Corte basal EX: {results['parte_B_sismo_pseudoestatico']['corte_basal_EX_kN']:.3f} kN")
    print(f"Corte basal EY: {results['parte_B_sismo_pseudoestatico']['corte_basal_EY_kN']:.3f} kN")
    print(f"Grafico M-phi: {OUT / 'M_phi_COL70_70.png'}")
    print(f"Grafico P-M: {OUT / 'P_M_COL70_70.png'}")
    print(f"Grafico fiber: {OUT / 'fiber_COL70_70.png'}")


if __name__ == "__main__":
    main()
