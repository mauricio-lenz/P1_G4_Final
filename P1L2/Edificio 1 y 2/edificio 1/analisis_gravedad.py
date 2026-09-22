# ============================================================
# ANALISIS DE GRAVEDAD - Edificio 1 (Dos Pasillos) UANDES
# ============================================================
# Replica el analisis del "edificio 2" sobre la geometria del
# edificio 1 (modelo dos pasillos de modelo_pasillos.py).
#
# Pipeline (identico en concepto al edificio 2):
#   Leer geometria (JSON) -> areas tributarias b/a por losa
#   -> cargas de diseno (perfiles FLOOR / ROOF, D y L por
#   separado) -> combinaciones U_1_4D y U_1_2D_1_6L
#   -> reduccion nodal simplificada (corte = w*L/2, axial de
#   columna por acarreo, momentos = 0) -> verificaciones
#   -> exportar JSON Unity (nodes/elements/walls/supports/
#      diaphragms/tributary) listo para el viewer 3D.
#
# Este modulo NO usa OpenSees (igual que el edificio 2): calcula
# las fuerzas con una reduccion nodal simplificada para el viewer.
#
# Unidades: kN y metros.
# ============================================================
import json
import os
from math import hypot

GEOM_TOL = 0.005

# ------------------------------------------------------------------
# Rutas
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(BASE_DIR, "resultados")
UNITY_JSON_NAME = "estructura_edificio1_unity.json"

# ------------------------------------------------------------------
# Parametros geometricos del edificio 1 (para apoyos/diafragmas)
# ------------------------------------------------------------------
Y_P1, Y_COMP, Y_P2 = 8.90, 0.0, -7.25
Y_EXT = -11.37
X_NEG = -10.0
X_LINEAS = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0]
X_ELIMINADA = 5.0
X_EXTRA = 7.51
H_PISO = 4.0
Z_SOTANO = -4.0
Z_PRIMER_PISO = 0.0
# Criterio de apoyos de modelo_pasillos.construir_opensees:
#   - sotano (z=-4): Y en {P1,COMP,P2}, X en {-10, 0}
#   - planta baja (z=0): Y en {P1,COMP,P2}, X en {10,20,30,35}
YS_APOYO = (Y_P1, Y_COMP, Y_P2)
XS_SUB = (X_NEG, 0.0)
XS_PB = (10.0, 20.0, 30.0, 35.0)

# ------------------------------------------------------------------
# Perfiles de carga (identicos a edificio_2 / materials local)
#   FLOOR (cielos 1S..3): D=635, L=500 kg/m2
#   ROOF  (cubierta 4)  : D=575, L=200 kg/m2
# ------------------------------------------------------------------
LOAD_SLAB_THICKNESS = 0.15
CONCRETE_UNIT_WEIGHT = 2500.0
ADDITIONAL_DEAD_FLOOR = 260.0
LIVE_FLOOR = 500.0
ADDITIONAL_DEAD_ROOF = 200.0
LIVE_ROOF = 200.0
KG2KN = 9.80665 / 1000.0

ROOF_LEVEL_Z = 16.0                 # nivel (z) de la cubierta

LOAD_COMBINATIONS = {
    "U_1_4D": {"D": 1.4, "L": 0.0},
    "U_1_2D_1_6L": {"D": 1.2, "L": 1.6},
}

# Nombres aproximados de nivel para viewer (para coherencia con edificio 2)
def level_name(z):
    names = {-4.0: "FOUNDATION", 0.0: "CIELO_1S", 4.0: "CIELO_1",
             8.0: "CIELO_2", 12.0: "CIELO_3", 16.0: "CIELO_4"}
    for k, v in names.items():
        if abs(z - k) < GEOM_TOL:
            return v
    return f"Z{int(round(z))}"


def _load_geometry():
    with open(os.path.join(RESULT_DIR, "coordenadas_nodos.json"), encoding="utf-8") as f:
        coords = json.load(f)                        # {nid: [x, y, z]}
    with open(os.path.join(RESULT_DIR, "elementos.json"), encoding="utf-8") as f:
        elems = json.load(f)                         # [{tipo, plano, nodo_i, nodo_j}]
    with open(os.path.join(RESULT_DIR, "losas.json"), encoding="utf-8") as f:
        losas = json.load(f)
    with open(os.path.join(RESULT_DIR, "muros.json"), encoding="utf-8") as f:
        muros = json.load(f)
    return coords, elems, losas, muros


def _load_profiles():
    pp = LOAD_SLAB_THICKNESS * CONCRETE_UNIT_WEIGHT        # 375 kg/m2
    profiles = {
        "FLOOR": {
            "description": "Cielos 1 subterraneo a cielo piso 3",
            "D_kg_m2": pp + ADDITIONAL_DEAD_FLOOR,
            "L_kg_m2": LIVE_FLOOR,
        },
        "ROOF": {
            "description": "Cielo piso 4 (cubierta)",
            "D_kg_m2": pp + ADDITIONAL_DEAD_ROOF,
            "L_kg_m2": LIVE_ROOF,
        },
    }
    for p in profiles.values():
        p["D_kN_m2"] = p["D_kg_m2"] * KG2KN
        p["L_kN_m2"] = p["L_kg_m2"] * KG2KN
    combos = {}
    for pid, p in profiles.items():
        combos[pid] = {}
        for cid, fac in LOAD_COMBINATIONS.items():
            combos[pid][cid] = {
                "factors": fac,
                "q_kN_m2": fac["D"] * p["D_kN_m2"] + fac["L"] * p["L_kN_m2"],
            }
    return profiles, combos


def _profile_for_level(z):
    return "ROOF" if abs(z - ROOF_LEVEL_Z) < GEOM_TOL else "FLOOR"


def _edge_areas(dx, dy):
    total = dx * dy
    short = min(dx, dy)
    long = max(dx, dy)
    ratio = long / short if short > 0 else 0.0
    areas = {"bottom": 0.0, "right": 0.0, "top": 0.0, "left": 0.0}
    if ratio > 2.0:
        if dx >= dy:
            areas["bottom"] = total / 2.0
            areas["top"] = total / 2.0
        else:
            areas["left"] = total / 2.0
            areas["right"] = total / 2.0
    elif dx <= dy:
        tri = dx * dx / 4.0
        tra = total / 2.0 - tri
        areas["bottom"] = tri
        areas["top"] = tri
        areas["left"] = tra
        areas["right"] = tra
    else:
        tri = dy * dy / 4.0
        tra = total / 2.0 - tri
        areas["left"] = tri
        areas["right"] = tri
        areas["bottom"] = tra
        areas["top"] = tra
    return ratio, areas


def _build_beams(coords, elems):
    columns = []
    beams = []
    for e in elems:
        ni = str(e["nodo_i"])
        nj = str(e["nodo_j"])
        if ni not in coords or nj not in coords:
            continue
        xi, yi, zi = coords[ni]
        xj, yj, zj = coords[nj]
        if e["tipo"] == "columna":
            if zi > zj:
                node_i, node_j = e["nodo_j"], e["nodo_i"]
                xb, yb, zb = xj, yj, zj
                xt, yt, zt = xi, yi, zi
            else:
                node_i, node_j = e["nodo_i"], e["nodo_j"]
                xb, yb, zb = xi, yi, zi
                xt, yt, zt = xj, yj, zj
            columns.append({
                "id": e.get("id"), "nodo_i": node_i, "nodo_j": node_j,
                "x": xb, "y": yb, "z_bottom": zb, "z_top": zt,
                "tipo": "columna", "plano": e.get("plano"),
            })
        else:
            if abs(zi - zj) > GEOM_TOL:
                continue
            beams.append({
                "id": e.get("id"), "nodo_i": e["nodo_i"], "nodo_j": e["nodo_j"],
                "nivel": (zi + zj) / 2.0,
                "x1": xi, "y1": yi, "x2": xj, "y2": yj,
                "plano": e.get("plano"),
            })
    return columns, beams


def _find_beam_for_edge(beams, level, p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    eh = abs(y1 - y2) <= GEOM_TOL
    ev = abs(x1 - x2) <= GEOM_TOL
    if not (eh or ev):
        return None
    for b in beams:
        if abs(b["nivel"] - level) > GEOM_TOL:
            continue
        if eh:
            if abs(b["y1"] - y1) > GEOM_TOL or abs(b["y2"] - y1) > GEOM_TOL:
                continue
            bxmin, bxmax = sorted([b["x1"], b["x2"]])
            exmin, exmax = sorted([x1, x2])
            if bxmin <= exmin + GEOM_TOL and bxmax >= exmax - GEOM_TOL:
                return b
        if ev:
            if abs(b["x1"] - x1) > GEOM_TOL or abs(b["x2"] - x1) > GEOM_TOL:
                continue
            bymin, bymax = sorted([b["y1"], b["y2"]])
            eymin, eymax = sorted([y1, y2])
            if bymin <= eymin + GEOM_TOL and bymax >= eymax - GEOM_TOL:
                return b
    return None


def compute_tributary(losas, beams):
    profiles, combos = _load_profiles()
    tributary_areas = []
    beam_loads = {}
    checks = {}

    for sl in losas:
        if sl.get("x0") is None or "zona_muro" in sl.get("detalle", ""):
            continue
        nivel = sl["nivel"]
        pid = _profile_for_level(nivel)
        prof = profiles[pid]
        x1, x2 = sorted((sl["x0"], sl["x1"]))
        y1, y2 = sorted((sl["y0"], sl["y1"]))
        dx = x2 - x1
        dy = y2 - y1
        if dx <= 0 or dy <= 0:
            continue
        panel = dx * dy
        lc = checks.setdefault(str(nivel), {
            "panel_area_m2": 0.0, "tributary_area_m2": 0.0,
            "D_kN": 0.0, "L_kN": 0.0,
            "D_expected_kN": 0.0, "L_expected_kN": 0.0,
        })
        lc["panel_area_m2"] += panel
        lc["D_expected_kN"] += panel * prof["D_kN_m2"]
        lc["L_expected_kN"] += panel * prof["L_kN_m2"]

        ratio, areas = _edge_areas(dx, dy)
        edges = {
            "bottom": ((x1, y1), (x2, y1)),
            "right": ((x2, y1), (x2, y2)),
            "top": ((x2, y2), (x1, y2)),
            "left": ((x1, y2), (x1, y1)),
        }
        for side, area in areas.items():
            if area <= 0:
                continue
            p1, p2 = edges[side]
            edge_len = hypot(p2[0] - p1[0], p2[1] - p1[1])
            beam = _find_beam_for_edge(beams, nivel, p1, p2)
            ld = prof["D_kN_m2"] * area
            ll = prof["L_kN_m2"] * area
            combo = {cid: c["q_kN_m2"] * area for cid, c in combos[pid].items()}
            tributary_areas.append({
                "level": nivel, "load_profile": pid, "side": side,
                "action": "ONE_WAY" if ratio > 2.0 else "TWO_WAY",
                "ratio_b_over_a": ratio, "panel_area_m2": panel,
                "tributary_area_m2": area, "edge_length_m": edge_len,
                "beam_index": beams.index(beam) if beam is not None else None,
                "loads_kN": {"D": ld, "L": ll},
                "load_combinations_kN": combo,
            })
            lc["tributary_area_m2"] += area
            lc["D_kN"] += ld
            lc["L_kN"] += ll

            if beam is None:
                continue
            key = beams.index(beam)
            be = beam_loads.setdefault(key, {
                "beam_index": key, "nivel": nivel,
                "tributary_area_m2": 0.0,
                "loads_kN": {"D": 0.0, "L": 0.0},
                "load_combinations_kN": {cid: 0.0 for cid in LOAD_COMBINATIONS},
                "source_edges": [],
            })
            be["tributary_area_m2"] += area
            be["loads_kN"]["D"] += ld
            be["loads_kN"]["L"] += ll
            for cid, v in combo.items():
                be["load_combinations_kN"][cid] += v
            be["source_edges"].append({"side": side, "tributary_area_m2": area})

    for nivel, c in checks.items():
        c["area_error_m2"] = c["tributary_area_m2"] - c["panel_area_m2"]
        c["D_error_kN"] = c["D_kN"] - c["D_expected_kN"]
        c["L_error_kN"] = c["L_kN"] - c["L_expected_kN"]

    return profiles, combos, tributary_areas, beam_loads, checks


def reduce_nodal(columns, beams, beam_loads, coords):
    """Elementos unificados con fuerzas de diagrama (Unity StructureData)."""
    elements = []

    for i, b in enumerate(beams):
        length = hypot(b["x2"] - b["x1"], b["y2"] - b["y1"])
        loads = beam_loads.get(i, {})
        combo = loads.get("load_combinations_kN", {})
        factored = combo.get("U_1_2D_1_6L", 0.0)
        uniform = factored / length if length > 0 else 0.0
        end_shear = uniform * length / 2.0
        elements.append({
            "id": i + 1,
            "type": "viga",
            "nodeI": b["nodo_i"], "nodeJ": b["nodo_j"],
            "seccion": "V",
            "piso": level_name(b["nivel"]),
            "uniformLoad": uniform,
            "areaTributaria": loads.get("tributary_area_m2", 0.0),
            "cargaTributaria": combo.get("U_1_2D_1_6L", 0.0),
            "axialI": 0.0, "axialJ": 0.0,
            "shearI": end_shear, "shearJ": -end_shear,
            "momentI": 0.0, "momentJ": 0.0,
            "_nivel": b["nivel"], "_plano": b.get("plano"),
        })

    # Acarreo de carga (1.2D+1.6L) a nodos
    carried = {}
    n_start = len(elements)
    for j, c in enumerate(columns):
        length = c["z_top"] - c["z_bottom"]
        elements.append({
            "id": n_start + j + 1,
            "type": "columna",
            "nodeI": c["nodo_i"], "nodeJ": c["nodo_j"],
            "seccion": "COL",
            "piso": level_name(c["z_top"]),
            "uniformLoad": 0.0, "areaTributaria": 0.0, "cargaTributaria": 0.0,
            "axialI": 0.0, "axialJ": 0.0,
            "shearI": 0.0, "shearJ": 0.0,
            "momentI": 0.0, "momentJ": 0.0,
            "_nivel": c["z_top"], "_z_bottom": c["z_bottom"],
        })

    # acarreo desde vigas + columnas (axial de columna)
    for i, b in enumerate(beams):
        loads = beam_loads.get(i, {})
        factored = loads.get("load_combinations_kN", {}).get("U_1_2D_1_6L", 0.0)
        carried[b["nodo_i"]] = carried.get(b["nodo_i"], 0.0) + factored / 2.0
        carried[b["nodo_j"]] = carried.get(b["nodo_j"], 0.0) + factored / 2.0

    col_by_id = {c["nodo_j"]: c for c in columns}  # nodo_j = tope
    col_order = sorted(columns, key=lambda c: c["z_top"], reverse=True)
    for c in col_order:
        axial = carried.get(c["nodo_j"], 0.0)
        # escribir axial de compresion (negativo) en el elemento de la columna
        for e in elements:
            if e["type"] == "columna" and e["nodeI"] == c["nodo_i"] and e["nodeJ"] == c["nodo_j"]:
                e["axialI"] = -axial
                e["axialJ"] = -axial
                e["cargaTributaria"] = axial
        carried[c["nodo_i"]] = carried.get(c["nodo_i"], 0.0) + axial

    # limpiar campos internos
    for e in elements:
        e.pop("_nivel", None)
        e.pop("_plano", None)
        e.pop("_z_bottom", None)
    return elements, carried


def build_diaphragms(coords, losas):
    """Diafragma rigido por nivel: maestro = nodo con menor (y, x)."""
    level_nodes = {}
    for sl in losas:
        if sl.get("x0") is None or "zona_muro" in sl.get("detalle", ""):
            continue
        nivel = sl["nivel"]
        for n in sl.get("nodos", []):
            level_nodes.setdefault(nivel, set()).add(n)
    diaphragms = []
    for nivel in sorted(level_nodes):
        nodos = list(level_nodes[nivel])
        # maestro = menor Y, luego menor X
        maestro = min(nodos, key=lambda n: (coords[str(n)][1], coords[str(n)][0]))
        slaves = [n for n in nodos if n != maestro]
        # centro (x,y) promedio del nivel para la losa del viewer
        xs = [coords[str(n)][0] for n in nodos]
        ys = [coords[str(n)][1] for n in nodos]
        cxs = sum(xs) / len(xs)
        cys = sum(ys) / len(ys)
        diaphragms.append({
            "level": level_name(nivel),
            "x": cxs, "y": cys, "z": nivel,
            "maestro": maestro,
            "slaves": sorted(slaves),
        })
    return diaphragms


def build_walls(coords, muros):
    """Muros del edificio 1 (muros.json -> nodos[00,10,11,01]) como tramo."""
    walls = []
    seen = set()
    for m in muros:
        nids = m.get("nodos")
        if not nids or len(nids) < 4:
            continue
        key = tuple(sorted(nids))
        if key in seen:
            continue
        seen.add(key)
        p0 = coords.get(str(nids[0]))
        p10 = coords.get(str(nids[1]))
        if not p0 or not p10:
            continue
        L = max(abs(p10[0] - p0[0]), abs(p10[1] - p0[1]))
        # tramo superior del muro (01-11) = nodos[3]-nodos[2]
        z0 = coords[str(nids[0])][2]
        z1 = coords[str(nids[2])][2]
        bottom = level_name(z0)
        top = level_name(z1)
        walls.append({
            "nodeI": nids[3], "nodeJ": nids[2],
            "type": "muro",
            "grosor": m.get("t", 0.2),
            "longitud": L,
            "bottom": bottom, "top": top,
        })
    return walls


def build_supports(coords):
    supports = []
    for nid, (x, y, z) in coords.items():
        en_y = any(abs(y - yy) < GEOM_TOL for yy in YS_APOYO)
        if not en_y:
            continue
        if abs(z - Z_SOTANO) < GEOM_TOL and any(abs(x - xx) < GEOM_TOL for xx in XS_SUB):
            supports.append({"node": int(nid), "type": "fixed",
                             "ux": 1, "uy": 1, "uz": 1, "rx": 1, "ry": 1, "rz": 1})
        elif abs(z - Z_PRIMER_PISO) < GEOM_TOL and any(abs(x - xx) < GEOM_TOL for xx in XS_PB):
            supports.append({"node": int(nid), "type": "fixed",
                             "ux": 1, "uy": 1, "uz": 1, "rx": 1, "ry": 1, "rz": 1})
    return supports


def build_tributary_list(checks, beam_loads):
    lista = []
    for z, c in checks.items():
        nivel = float(z)
        vigas = sum(1 for k, v in beam_loads.items() if abs(v["nivel"] - nivel) < GEOM_TOL)
        lista.append({
            "piso": level_name(nivel),
            "area_total": c["panel_area_m2"],
            "carga_total": c["D_kN"] + c["L_kN"],
            "vigas": vigas,
        })
    return lista


def export_unity_json(out_data, unity_path):
    os.makedirs(os.path.dirname(unity_path), exist_ok=True)
    with open(unity_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)
    return unity_path


def build_slabs(losas):
    """Paneles de losa reales por nivel (para el viewer Unity)."""
    slabs = []
    for i, sl in enumerate(losas):
        if sl.get("x0") is None or "zona_muro" in sl.get("detalle", ""):
            continue
        slabs.append({
            "id": i + 1,
            "nivel": level_name(sl["nivel"]),
            "x0": sl["x0"], "y0": sl["y0"], "x1": sl["x1"], "y1": sl["y1"],
            "z": sl["nivel"],
        })
    return slabs


def main():
    coords, elems, losas, muros = _load_geometry()
    live_losas = [l for l in losas if l.get("x0") is not None]

    columns, beams = _build_beams(coords, elems)
    profiles, combos, tributary_areas, beam_loads, checks = compute_tributary(live_losas, beams)
    elements, carried = reduce_nodal(columns, beams, beam_loads, coords)
    diaphragms = build_diaphragms(coords, live_losas)
    walls = build_walls(coords, muros)
    supports = build_supports(coords)
    tributary_list = build_tributary_list(checks, beam_loads)
    slabs = build_slabs(live_losas)

    # ------------------------------------------------------------------
    # Resumen / verificacion
    # ------------------------------------------------------------------
    print("=" * 70)
    print("EDIFICIO 1 - ANALISIS DE GRAVEDAD (areas tributarias b/a)")
    print("=" * 70)
    print(f"Nodos: {len(coords)} | Columnas: {len(columns)} | "
          f"Vigas: {len(beams)} | Paneles losa: {len(live_losas)}")
    print(f"Elementos (Unity): {len(elements)} | Diafragmas: {len(diaphragms)} | "
          f"Losas: {len(slabs)} | Muros: {len(walls)} | Apoyos: {len(supports)}")
    print()
    print("Conservacion por nivel (b/a):")
    for z in sorted(checks, key=float):
        c = checks[z]
        print(f"  {level_name(float(z)):>8} (z={float(z):>4}): A_panel={c['panel_area_m2']:8.2f}  "
              f"A_trib={c['tributary_area_m2']:8.2f}  err={c['area_error_m2']:+.4f}  "
              f"D={c['D_kN']:9.2f}  L={c['L_kN']:9.2f}")
    total_D = sum(c["D_kN"] for c in checks.values())
    total_L = sum(c["L_kN"] for c in checks.values())
    print()
    print(f"Carga total D = {total_D:.2f} kN | L = {total_L:.2f} kN | "
          f"1.2D+1.6L = {1.2*total_D + 1.6*total_L:.2f} kN")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Export JSON Unity (StructureData)
    # ------------------------------------------------------------------
    nodes_out = [{"id": int(nid), "x": xyz[0], "y": xyz[1], "z": xyz[2]}
                 for nid, xyz in coords.items()]

    out = {
        "units": "m, kN, kN*m",
        "q_G": 9.80665 / 1000.0 * (LOAD_SLAB_THICKNESS * CONCRETE_UNIT_WEIGHT + 260.0),
        "nodes": nodes_out,
        "elements": elements,
        "walls": walls,
        "supports": supports,
        "diaphragms": diaphragms,
        "diaphragmList": diaphragms,
        "slabs": slabs,
        "tributaryAreasByFloor": tributary_list,
        "tributaryList": tributary_list,
        "localAxes": [],
        "pointLoads": [],
        "statistics": {
            "columnas": len(columns), "vigas": len(beams),
            "muros": len(walls), "apoyos": len(supports),
            "paneles_losa": len(live_losas),
        },
        "loadCases": profiles,
        "loadCombinations": combos,
        "tributaryChecks": checks,
    }

    result_path = os.path.join(RESULT_DIR, "analisis_gravedad_unity.json")
    export_unity_json(out, result_path)

    # Copiar al proyecto Unity (Assets/Resources)
    unity_resources = os.path.normpath(os.path.join(
        BASE_DIR, "unity_visualizador", "Assets", "Resources"))
    unity_path = os.path.join(unity_resources, UNITY_JSON_NAME)
    if os.path.isdir(unity_resources):
        export_unity_json(out, unity_path)
        print(f"\nExportado Unity: {unity_path}")
    else:
        print(f"\n(no se encontro {unity_resources}; JSON en {result_path})")

    print(f"JSON resultados: {result_path}")
    return out


if __name__ == "__main__":
    main()
