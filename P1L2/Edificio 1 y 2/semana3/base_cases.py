# ============================================================
# BASE CASES - Semana 3 (Edificio de Ingenieria UANDES)
# ============================================================
# Construye el modelo OpenSees del Edificio 1 una vez (gravedad con
# areas tributarias de Semana 2) y permite correr casos de carga base:
#   G  : carga muerta (peso propio + terminaciones)
#   Q  : carga viva (sobrecarga de uso)
#   EX : sismo pseudoestatico en X (Nch433, 20% g basal)
#   EY : sismo pseudoestatico en Y
# Cada caso se corre como una corrida OpenSees independiente y devuelve
# resultados: desplazamientos nodales, reacciones y fuerzas internas.
#
# Unidades: kN y metros.
# ============================================================
import os
from math import hypot

import openseespy.opensees as ops

from materials import (PP_LOSA_KNM2, PM_ADIC_INF, SC_INF, PM_ADIC_CUB,
                       SC_CUB, KGM2_TO_KNM2, G, Q_G_BY_LEVEL)
from structural_model import load_geometry, assemble, build_model, PISO_LEVELS
from tributary import classify_panel, beams_covering_edge, build_beam_index

# ------------------------------------------------------------------
# CARGAS UNIFORMES POR NIVEL [kN/m2]
# ------------------------------------------------------------------
# Peso propio losa (PP) + terminaciones (PM_adic) = carga muerta D.
# Sobrecarga de uso (SC) = carga viva Q.
def _kgm2_to_knm2(x):
    return x * KGM2_TO_KNM2

D_BY_LEVEL = {
    "CIELO_1S": _kgm2_to_knm2(PP_LOSA_KNM2 / G * 1000.0 + PM_ADIC_INF),
    "CIELO_1":  _kgm2_to_knm2(PP_LOSA_KNM2 / G * 1000.0 + PM_ADIC_INF),
    "CIELO_2":  _kgm2_to_knm2(PP_LOSA_KNM2 / G * 1000.0 + PM_ADIC_INF),
    "CIELO_3":  _kgm2_to_knm2(PP_LOSA_KNM2 / G * 1000.0 + PM_ADIC_INF),
    "CIELO_4":  _kgm2_to_knm2(PP_LOSA_KNM2 / G * 1000.0 + PM_ADIC_CUB),
}

Q_BY_LEVEL = {
    "CIELO_1S": _kgm2_to_knm2(SC_INF),
    "CIELO_1":  _kgm2_to_knm2(SC_INF),
    "CIELO_2":  _kgm2_to_knm2(SC_INF),
    "CIELO_3":  _kgm2_to_knm2(SC_INF),
    "CIELO_4":  _kgm2_to_knm2(SC_CUB),
}

# Porcentaje de g (Nch433, ejemplo del enunciado)
C_G_PCT = 0.20
C_G = C_G_PCT            # 20% de g
MASA_VIVA_FRACCION = 0.50  # 50% de la carga viva se suma a la masa


# ------------------------------------------------------------------
# AREAS TRIBUTARIAS GEO (independientes de la intensidad de carga)
# ------------------------------------------------------------------
def tributary_areas_geometry(geometry, structure):
    """Devuelve beam_data = {tag: {area, largo, piso, seccion, iNode, jNode}}
    usando el mismo metodo b/a de Semana 2, PERO sin multiplicar por q_G.
    Asi se puede aplicar luego cualquier intensidad (D, Q)."""
    index = build_beam_index(structure)
    nm = structure["node_map"]
    beam_data = {}

    def acc(tag, area, piso):
        d = beam_data.setdefault(tag, {"area": 0.0, "piso": piso})
        d["area"] += area

    for slab in geometry["slabs"]:
        if slab["x1"] is None:
            continue
        x1, x2 = sorted([slab["x1"], slab["x2"]])
        y1, y2 = sorted([slab["y1"], slab["y2"]])
        lv = slab["level"]
        if lv not in Q_BY_LEVEL:
            continue
        a, b, modo = classify_panel(x2 - x1, y2 - y1)
        if modo == 'none':
            continue
        areas = _panel_areas(x1, x2, y1, y2)
        for lado, (coord, lo, hi) in {
            'bottom': (y1, x1, x2), 'top': (y2, x1, x2)}.items():
            area = areas.get(lado, 0.0)
            if area <= 0:
                continue
            cover = beams_covering_edge(index, lv, 'H', coord, lo, hi)
            total = sum(c[0] for c in cover)
            if total <= 0:
                continue
            for ov, _, _, beam in cover:
                acc(beam["tag"], area * ov / total, lv)
        for lado, (coord, lo, hi) in {
            'left': (x1, y1, y2), 'right': (x2, y1, y2)}.items():
            area = areas.get(lado, 0.0)
            if area <= 0:
                continue
            cover = beams_covering_edge(index, lv, 'V', coord, lo, hi)
            total = sum(c[0] for c in cover)
            if total <= 0:
                continue
            for ov, _, _, beam in cover:
                acc(beam["tag"], area * ov / total, lv)

    for b in structure["beams"]:
        tag = b["tag"]
        if tag not in beam_data:
            beam_data[tag] = {"area": 0.0, "piso": b["piso"]}
        d = beam_data[tag]
        n1 = nm[b["iNode"]]; n2 = nm[b["jNode"]]
        d["largo"] = hypot(n1["x"] - n2["x"], n1["y"] - n2["y"])
        d["seccion"] = b["seccion"]
        d["iNode"] = b["iNode"]
        d["jNode"] = b["jNode"]
    return beam_data


def _panel_areas(x1, x2, y1, y2):
    """Replica de tributary.panel_tributary_areas (independiente)."""
    from tributary import panel_tributary_areas
    return panel_tributary_areas(x1, x2, y1, y2)


# ------------------------------------------------------------------
# APLICAR CARGAS DE PISO A LAS VIGAS (uniforme, -Z)
# ------------------------------------------------------------------
def apply_floor_loads(structure, beam_data, qmap, pattern_tag=1, ts_tag=1):
    """Aplica w = qmap[piso] * area / largo sobre cada viga, en -Z."""
    ops.timeSeries("Linear", ts_tag)
    ops.pattern("Plain", pattern_tag, ts_tag)
    n_applied = 0
    for b in structure["beams"]:
        d = beam_data.get(b["tag"])
        if not d or d.get("largo", 0.0) <= 0 or d.get("area", 0.0) <= 0:
            continue
        q = qmap.get(d["piso"])
        if not q:
            continue
        w = q * d["area"] / d["largo"]
        ops.eleLoad("-ele", b["tag"], "-type", "-beamUniform", 0.0, -w)
        n_applied += 1
    return n_applied


# ------------------------------------------------------------------
# MASA Y FUERZAS SISMICAS POR PISO
# ------------------------------------------------------------------
def floor_masses(structure, geometry):
    """Masa (peso) por piso: W = (D + 0.5 Q) * A_losa.
    Devuelve dict nivel -> fuerza sismica F = C_G * W [kN]."""
    from math import fsum
    W = {}
    A = {}
    for level in PISO_LEVELS:
        lv = level
        qd = D_BY_LEVEL.get(lv, 0.0)
        qq = Q_BY_LEVEL.get(lv, 0.0)
        # area de losa del nivel desde la geometria (suma de paneles)
        area = 0.0
        for slab in geometry["slabs"]:
            if slab["level"] != level or slab["x1"] is None:
                continue
            area += (abs(slab["x2"] - slab["x1"]) *
                     abs(slab["y2"] - slab["y1"]))
        W[level] = (qd + MASA_VIVA_FRACCION * qq) * area
        A[level] = area
    F = {lv: C_G * W[lv] for lv in W}
    return W, A, F


def apply_seismic(structure, F, direction, pattern_tag=2, ts_tag=2):
    """Aplica fuerzas laterales F[level] en el nodo maestro del diafragma
    de cada piso, en 'x' o 'y'. Devuelve total y lista (nodo, fuerza)."""
    ops.timeSeries("Linear", ts_tag)
    ops.pattern("Plain", pattern_tag, ts_tag)
    dof = 0 if direction == 'x' else 1
    applied = []
    total = 0.0
    for level in PISO_LEVELS:
        df = structure["diafragmas"].get(level)
        if not df:
            continue
        f = F.get(level, 0.0)
        if abs(f) < 1e-9:
            continue
        m = df["maestro"]
        vals = [0.0] * 6
        vals[dof] = f
        ops.load(m, *vals)
        applied.append((level, m, f, dof))
        total += f
    return total, applied


# ------------------------------------------------------------------
# ANALISIS ESTATICO LINEAL
# ------------------------------------------------------------------
def run_analysis():
    ok = -1
    try:
        ops.system("BandGeneral")
        ops.numberer("RCM")
        ops.constraints("Transformation")
        ops.integrator("LoadControl", 1.0)
        ops.algorithm("Linear")
        ops.analysis("Static")
        ok = ops.analyze(1)
    except Exception as exc:  # noqa
        ok = -2
    if ok == 0:
        ops.reactions()
    return ok


# ------------------------------------------------------------------
# EXTRACCION DE RESULTADOS
# ------------------------------------------------------------------
def extract_displacements(structure):
    nm = structure["node_map"]
    disp = {}
    nodes_used = set()
    for c in structure["columns"]:
        nodes_used.add(c["iNode"]); nodes_used.add(c["jNode"])
    for b in structure["beams"]:
        nodes_used.add(b["iNode"]); nodes_used.add(b["jNode"])
    for s in structure["supports"]:
        nodes_used.add(s["node"])
    for nid in nodes_used:
        if nid not in nm:
            continue
        try:
            vals = [ops.nodeDisp(nid, i) for i in range(1, 7)]
            disp[nid] = {
                "x": nm[nid]["x"], "y": nm[nid]["y"], "z": nm[nid]["z"],
                "ux": vals[0], "uy": vals[1], "uz": vals[2],
                "rx": vals[3], "ry": vals[4], "rz": vals[5],
            }
        except Exception:  # nodo sin dofs
            pass
    return disp


def extract_reactions(structure):
    rx = ry = rz = 0.0
    per_node = {}
    for s in structure["supports"]:
        n = s["node"]
        try:
            r = ops.nodeReaction(n)
            per_node[n] = list(r)
            rx += r[0]; ry += r[1]; rz += r[2]
        except Exception:
            pass
    return {"sum_Rx": rx, "sum_Ry": ry, "sum_Rz": rz, "per_node": per_node}


def extract_element_forces(structure):
    forces = {}
    for b in structure["beams"]:
        try:
            forces[b["tag"]] = list(ops.eleForce(b["tag"]))
        except Exception:
            pass
    for c in structure["columns"]:
        try:
            forces[c["tag"]] = list(ops.eleForce(c["tag"]))
        except Exception:
            pass
    return forces


def extract_floor_twist(structure):
    """Torsion de piso: rotacion rz del nodo maestro del diafragma."""
    out = {}
    for level, df in structure["diafragmas"].items():
        m = df["maestro"]
        try:
            out[level] = {"maestro": m, "rz": ops.nodeDisp(m, 6)}
        except Exception:
            out[level] = {"maestro": m, "rz": 0.0}
    return out


# ------------------------------------------------------------------
# CORRIDA DE UN CASO BASE
# ------------------------------------------------------------------
def run_case(geometry, structure, beam_data, case, lambda_=1.0):
    """Corre un caso 'G','Q','EX','EY' y devuelve dict de resultados.
    lambda_: factor aplicado a la carga del caso."""
    build_model(structure, geometry)   # limpia y reconstruye
    if case == "G":
        qm = {lv: D_BY_LEVEL.get(lv, 0.0) * lambda_ for lv in D_BY_LEVEL}
        apply_floor_loads(structure, beam_data, qm, 1, 1)
    elif case == "Q":
        qm = {lv: Q_BY_LEVEL.get(lv, 0.0) * lambda_ for lv in Q_BY_LEVEL}
        apply_floor_loads(structure, beam_data, qm, 1, 1)
    elif case in ("EX", "EY"):
        _, _, F = floor_masses(structure, geometry)
        F = {lv: f * lambda_ for lv, f in F.items()}
        direction = 'x' if case == 'EX' else 'y'
        total, applied = apply_seismic(structure, F, direction, 2, 2)
    else:
        raise ValueError(f"Caso desconocido: {case}")

    ok = run_analysis()
    results = {
        "case": case,
        "lambda": lambda_,
        "convergio": ok == 0,
        "ok_code": ok,
        "displacements": extract_displacements(structure),
        "reactions": extract_reactions(structure),
        "element_forces": extract_element_forces(structure),
        "floor_twist": extract_floor_twist(structure),
    }
    ops.wipe()
    return results


# ------------------------------------------------------------------
# CONSTRUCCION Y CASOS PREPARADOS
# ------------------------------------------------------------------
def build():
    geometry = load_geometry()
    structure = assemble(geometry)
    beam_data = tributary_areas_geometry(geometry, structure)
    return geometry, structure, beam_data


def run_all_base_cases():
    geometry, structure, beam_data = build()
    out = {}
    for case in ("G", "Q", "EX", "EY"):
        out[case] = run_case(geometry, structure, beam_data, case, 1.0)
    return geometry, structure, beam_data, out
