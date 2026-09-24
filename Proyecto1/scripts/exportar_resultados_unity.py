#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exporta resultados enriquecidos para el visualizador Unity P1L4.

Genera un JSON estructurado a partir de los resultados de OpenSeesPy que incluye:
- Geometria original del edificio completo
- Desplazamientos por combinacion (para deformada)
- Fuerzas internas por combinacion (N, Vy, Vz, T, My, Mz) por elemento
- Curvas P-M para columna (COL70/70_FIBER) y muro (W_DPRIME_OPENING_TO_3)
- Puntos de demanda por combinacion
- Materiales por seccion
- Combinaciones NCh433 (C1, C2, C3)

Requiere: openseespy, matplotlib (opcional).

Uso:
  python P1L4/exportar_resultados_unity.py
  python P1L4/exportar_resultados_unity.py --q-kg-m2 500 --sc 0.20

El JSON se escribe en:
  P1L4/edificio_G4/Assets/Resources/estructura_p1l4_unity.json
"""

import sys
import os
import json
from pathlib import Path

# ── Configuracion de rutas ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
P1L3_DIR = ROOT_DIR / "scripts"          # carga_viva_sismo.py consolidado en Proyecto1
P1L2_RESOURCES = ROOT_DIR / "data"       # JSON base + resultados Unity consolidados en Proyecto1
JSON_BASE = P1L2_RESOURCES / "estructura_completo_unity.json"
JSON_OUT = ROOT_DIR / "edificio_G4" / "Assets" / "Resources" / "estructura_p1l4_unity.json"

# Metadata de materiales para las secciones
SECTION_MATERIALS = [
    {
        "sectionId": "COL70/70",
        "elementType": "columna",
        "materialName": "H-30 / Acero A630-420",
        "fc_MPa": 30.0,
        "fy_MPa": 420.0,
        "E_MPa": 30000.0,
        "b_m": 0.70,
        "h_m": 0.70,
        "note": "Seccion rectangular 70x70 cm, H-30 (fc=30 MPa), fy=420 MPa"
    },
    {
        "sectionId": "COL70/70_FIBER",
        "elementType": "columna",
        "materialName": "H-30 / Acero A630-420 (analisis fibra)",
        "fc_MPa": 30.0,
        "fy_MPa": 420.0,
        "E_MPa": 30000.0,
        "b_m": 0.70,
        "h_m": 0.70,
        "steelBars": 8,
        "barDiameter_mm": 25.0,
        "Ast_mm2": 3927.0,
        "rho_percent": 0.80,
        "Po_kN": 14044.2,
        "note": "Analisis fibra P-M: H-30, fy=420, 8 phi25, rec=52.5mm"
    },
    {
        "sectionId": "W_DPRIME_OPENING_TO_3",
        "elementType": "muro",
        "materialName": "H-30 / Acero A630-420 (muro con abertura)",
        "fc_MPa": 30.0,
        "fy_MPa": 420.0,
        "E_MPa": 30000.0,
        "b_m": 0.25,
        "h_m": 7.60,
        "steelBars": 76,
        "barDiameter_mm": 12.0,
        "As_total_mm2": 8595.4,
        "rho_percent": 0.45,
        "Pn0_kN": 48450.0,
        "note": "Muro D-PRIME-OPENING-TO-3, t=0.25, L=7.60, 2 capas phi12@200"
    },
    {
        "sectionId": "V60/80",
        "elementType": "viga",
        "materialName": "H-25 / Acero A630-420 (viga)",
        "fc_MPa": 25.0,
        "fy_MPa": 420.0,
        "E_MPa": 25000.0,
        "b_m": 0.60,
        "h_m": 0.80,
        "note": "Viga 60x80 cm"
    },
    {
        "sectionId": "V40/80",
        "elementType": "viga",
        "materialName": "H-25 / Acero A630-420 (viga)",
        "fc_MPa": 25.0,
        "fy_MPa": 420.0,
        "E_MPa": 25000.0,
        "b_m": 0.40,
        "h_m": 0.80,
        "note": "Viga 40x80 cm"
    },
    {
        "sectionId": "V30/80",
        "elementType": "viga",
        "materialName": "H-25 / Acero A630-420 (viga)",
        "fc_MPa": 25.0,
        "fy_MPa": 420.0,
        "E_MPa": 25000.0,
        "b_m": 0.30,
        "h_m": 0.80,
        "note": "Viga 30x80 cm"
    },
    {
        "sectionId": "V30/45",
        "elementType": "viga",
        "materialName": "H-25 / Acero A630-420 (viga)",
        "fc_MPa": 25.0,
        "fy_MPa": 420.0,
        "E_MPa": 25000.0,
        "b_m": 0.30,
        "h_m": 0.45,
        "note": "Viga 30x45 cm"
    }
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)


def main():
    # ── Agregar P1L3 al path para reutilizar funciones ──────────────
    p1l3_str = str(P1L3_DIR)
    if p1l3_str not in sys.path:
        sys.path.insert(0, p1l3_str)

    try:
        import carga_viva_sismo as cvm
    except ImportError as e:
        print(f"ERROR: No se pudo importar carga_viva_sismo de P1L3: {e}")
        print(f"  Asegurate de que {p1l3_str}/carga_viva_sismo.py existe.")
        sys.exit(1)

    if cvm.ops is None:
        print("ERROR: openseespy no disponible. Instala con: pip install openseespy")
        sys.exit(1)

    # ── Parametros ──────────────────────────────────────────────────
    import argparse
    parser = argparse.ArgumentParser(description="Exportar resultados enriquecidos para Unity P1L4")
    parser.add_argument("--q-kg-m2", type=float, default=500.0,
                        help="Carga viva Q en kg/m2 (default: 500)")
    parser.add_argument("--sc", type=float, default=cvm.DEFAULT_SEISMIC_COEFF,
                        help="Coeficiente sismico (default: 0.20)")
    args = parser.parse_args()

    q_Q = cvm.kg_m2_to_kn_m2(args.q_kg_m2)
    sc = args.sc
    print(f"Parametros: Q={q_Q:.3f} kN/m2 ({args.q_kg_m2:.0f} kg/m2), Coef. sismico={sc}")

    # ── Cargar datos base ───────────────────────────────────────────
    print("Cargando estructura base...")
    data = load_json(JSON_BASE)
    q_g = float(data.get("q_G", 6.227))
    print(f"  Nodos: {len(data.get('nodes', []))}")
    print(f"  Elementos: {len(data.get('elements', []))}")
    print(f"  Muros: {len(data.get('walls', []))}")
    print(f"  Apoyos: {len(data.get('supports', []))}")
    print(f"  q_G = {q_g:.4f} kN/m2")

    # ── Cargar curva P-M del muro (part_e_wall.json) ───────────────
    wall_pm_data = None
    wall_pm_path = ROOT_DIR / "data" / "part_e_wall.json"
    if wall_pm_path.exists():
        print("Cargando curva P-M del muro...")
        wall_pm_full = load_json(wall_pm_path)
        wall_pm_data = wall_pm_full.get("interaccion_PM", [])
        print(f"  Puntos P-M muro: {len(wall_pm_data)}")
    else:
        print(f"  AVISO: No se encontro {wall_pm_path}, se omite curva P-M muro.")

    # ── Curva P-M columna (COL70/70_FIBER) ─────────────────────────
    # Se recomputa con la seccion de fibra (H-30, fc=30 MPa) usando las
    # mismas funciones de P1L3/carga_viva_sismo.py para evitar la
    # inconsistencia historica entre la curva guardada (fc=25 MPa) y el
    # material del modelo (H-30 en materials.py / structural_model.py).
    print("Calculando curva P-M columna COL70/70_FIBER (H-30)...")
    try:
        col_section = cvm.make_column_fibers()
        col_ag = col_section["b"] * col_section["h"]
        col_ast = len(col_section["rebar_xy"]) * col_section["bar_area_m2"]
        col_po = 0.85 * col_section["fc"] * (col_ag - col_ast) + col_section["fy"] * col_ast
        col_pm_raw = cvm.simplified_pm_points(col_section, col_po)
        col_pm_data = [{
            "label": p["estado"],
            "P_kN": p["Pn_kN"],
            "M_kN_m": p["Mn_kN_m"],
        } for p in col_pm_raw]
        col_fc_mpa = col_section["fc"] / 1000.0
        col_fy_mpa = col_section["fy"] / 1000.0
        print(f"  Po = {col_po:.1f} kN | fc' = {col_fc_mpa:.0f} MPa | puntos = {len(col_pm_data)}")
    except Exception as e:
        print(f"  AVISO: No se pudo recalcular la curva P-M columna ({e}); se omite.")
        col_pm_data = None
        col_fc_mpa = 30.0
        col_fy_mpa = 420.0
        col_po = 0.0

    # ── Construir casos de carga ─────────────────────────────────────
    print("Construyendo casos de carga G, Q, EX, EY...")
    live_transfer = cvm.transfer_live_load(data, q_Q)
    seismic = cvm.build_seismic_cases(data, live_transfer, sc)

    G = cvm.dead_nodal_loads(data)
    Q = cvm.vector_loads_from_dict(live_transfer["cargas_nodales_Q"])
    EX = cvm.vector_loads_from_dict(seismic["cargas_nodales_EX"])
    EY = cvm.vector_loads_from_dict(seismic["cargas_nodales_EY"])

    load_sets = {"G": G, "Q": Q, "EX": EX, "EY": EY}

    # ── Combinaciones NCh433 ─────────────────────────────────────────
    combos = {
        "C1": {"G": 1.00, "Q": 0.50, "EX": 0.30, "EY": 0.20},
        "C2": {"G": 1.00, "Q": 0.50, "EX": 0.30, "EY": -0.20},
        "C3": {"G": 1.00, "Q": 0.50, "EX": -0.30, "EY": 0.20},
    }

    combo_labels = {
        "C1": "C1: G+0.5Q+0.3EX+0.2EY",
        "C2": "C2: G+0.5Q+0.3EX-0.2EY",
        "C3": "C3: G+0.5Q-0.3EX+0.2EY",
    }

    # ── Correr analisis base y por combinacion ───────────────────────
    base_results = {}
    for case_name, nodal_loads in load_sets.items():
        print(f"\nAnalizando caso base {case_name}...")
        try:
            result = cvm.run_and_extract(data, nodal_loads)
            base_results[case_name] = result
            print(f"  OK={result.get('ok', False)} | fuerzas_elem={len(result.get('element_forces', {}))}")
        except Exception as e:
            print(f"  ERROR: {e}")
            base_results[case_name] = None

    all_results = {}
    for combo_name, lambdas in combos.items():
        print(f"\nAnalizando combinacion {combo_name}...")
        combined_loads = cvm.combine_nodal_loads(load_sets, lambdas)
        try:
            result = cvm.run_and_extract(data, combined_loads)
            ok = result.get("ok", False)
            all_results[combo_name] = result
            disp = result.get("displacements", {})
            forces = result.get("element_forces", {})
            n_disp = len(disp)
            n_forces = len(forces)
            print(f"  OK={ok} | desplazamientos={n_disp} | fuerzas_elem={n_forces}")
        except Exception as e:
            print(f"  ERROR: {e}")
            all_results[combo_name] = None

    # ── Empaquetar desplazamientos ───────────────────────────────────
    print("\nEmpaquetando resultados...")
    displacements_flat = []
    # Incluye los casos base (G/Q/EX/EY) Y los combos (C1/C2/C3).
    # El JSON de Unity ya almacenaba fuerzas por caso base; ahora los
    # desplazamientos tambien quedan por caso base para permitir en el
    # viewer la superposicion en vivo (sliders G/Q/EX/EY -> deformada).
    for combo_name, result in {**base_results, **all_results}.items():
        if result is None:
            continue
        disp_dict = result.get("displacements", {})
        for node_id, d in disp_dict.items():
            displacements_flat.append({
                "combo": combo_name,
                "node": int(node_id),
                "ux": d.get("ux", 0.0),
                "uy": d.get("uy", 0.0),
                "uz": d.get("uz", 0.0),
                "rx": d.get("rx", 0.0),
                "ry": d.get("ry", 0.0),
                "rz": d.get("rz", 0.0),
            })

    # ── Empaquetar fuerzas por elemento ──────────────────────────────
    element_meta = {}
    for el in data.get("elements", []):
        element_meta[int(el["id"])] = el

    element_forces_flat = []
    for combo_name, result in {**base_results, **all_results}.items():
        if result is None:
            continue
        forces_dict = result.get("element_forces", {})
        for elem_id, f in forces_dict.items():
            meta = element_meta.get(int(elem_id), {})
            element_forces_flat.append({
                "combo": combo_name,
                "id": int(elem_id),
                "tag": meta.get("elementTag", str(int(elem_id))),
                "type": meta.get("type", ""),
                "sourceBuilding": meta.get("sourceBuilding", ""),
                "f": [float(v) for v in f[:12]] if len(f) >= 12 else [float(v) for v in f] + [0.0] * (12 - len(f))
            })

    # ── Construir curvas P-M ─────────────────────────────────────────
    pm_curves = []

    if col_pm_data:
        pm_curves.append({
            "sectionId": "COL70/70_FIBER",
            "elementType": "columna",
            "b_m": 0.70,
            "h_m": 0.70,
            "fc_MPa": col_fc_mpa,
            "fy_MPa": col_fy_mpa,
            "steelBars": 8,
            "barDiameter_mm": 25.0,
            "Ast_mm2": 3927.0,
            "rho_percent": 0.80,
            "Po_kN": col_po,
            "interpretation": "Diagrama P-M COL70/70 (5 puntos manuales: compresion pura, balance, falla ductil, flexion pura, traccion pura), fc=H-30.",
            "points": [{"label": p["label"], "P_kN": p["P_kN"], "M_kN_m": p["M_kN_m"]} for p in col_pm_data]
        })

    if wall_pm_data:
        wall_points = [{"label": f'P/Pn0={p["P_frac"]:.2f}', "P_kN": p["P_kN"], "M_kN_m": p["Mmax_kNm"]} for p in wall_pm_data]
        pm_curves.append({
            "sectionId": "W_DPRIME_OPENING_TO_3",
            "elementType": "muro",
            "b_m": 0.25,
            "h_m": 7.60,
            "fc_MPa": 30.0,
            "fy_MPa": 420.0,
            "steelBars": 76,
            "barDiameter_mm": 12.0,
            "Ast_mm2": 8595.4,
            "rho_percent": 0.45,
            "Po_kN": 48450.0,
            "interpretation": f"Envolvente P-M W_DPRIME_OPENING_TO_3 (t=0.25m, L=7.60m, 2 capas phi12@200). {len(wall_points)} puntos de la envolvente.",
            "points": wall_points
        })

    # ── Regenerar semana3_resultados_unity.json (H-30) ─────────────
    # Deja el archivo de capacidad de P1L2 consistente con el modelo
    # (concrete H-30) y con lo que Unity carga en la escena P1L2.
    if col_pm_data:
        try:
            col_bar_area = col_section["bar_area_m2"]
            col_bar_phi_mm = (2.0 * (col_bar_area / 3.141592653589793) ** 0.5) * 1000.0
            col_ast_m2 = len(col_section["rebar_xy"]) * col_bar_area
            col_capacity_unity = {
                "capacityTitle": "Parte D - Capacidad HA COL70/70_FIBER",
                "sectionId": "COL70/70_FIBER",
                "b_m": col_section["b"],
                "h_m": col_section["h"],
                "fc_MPa": col_fc_mpa,
                "fy_MPa": col_fy_mpa,
                "steelBars": len(col_section["rebar_xy"]),
                "barArea_m2": col_bar_area,
                "barArea_mm2": col_bar_area * 1e6,
                "barDiameter_mm": col_bar_phi_mm,
                "Ast_m2": col_ast_m2,
                "Ast_mm2": col_ast_m2 * 1e6,
                "rho_percent": 100.0 * (col_ast_m2 / (col_section["b"] * col_section["h"])),
                "Po_kN": col_po,
                "interpretation": "Diagrama P-M COL70/70 (5 puntos manuales), fc=H-30. Regenerado por P1L4/exportar_resultados_unity.py.",
                "pmPoints": [
                    {
                        "label": p["estado"],
                        "P_kN": p["Pn_kN"],
                        "M_kN_m": p["Mn_kN_m"],
                        "phiP_kN": p["phiPn_kN"],
                        "phiM_kN_m": p["phiMn_kN_m"],
                        "phi_1_m": 0.0,
                    }
                    for p in col_pm_raw
                ],
            }
            write_json(P1L2_RESOURCES / "semana3_resultados_unity.json", col_capacity_unity)
            print("  semana3_resultados_unity.json regenerado (H-30).")
        except Exception as e:
            print(f"  AVISO: no se pudo regenerar semana3_resultados_unity.json: {e}")

    # ── Calcular demandas por muro ───────────────────────────────────
    nodes_map = {n["id"]: (n["x"], n["y"], n["z"]) for n in data.get("nodes", [])}

    def wall_mid_and_z(wall):
        ni = nodes_map.get(wall.get("nodeI"))
        nj = nodes_map.get(wall.get("nodeJ"))
        if not ni or not nj:
            return 0.0, 0.0, 0.0
        return 0.5 * (ni[0] + nj[0]), 0.5 * (ni[1] + nj[1]), 0.5 * (ni[2] + nj[2])

    wall_base_info = []
    for wall in data.get("walls", []):
        x, y, z = wall_mid_and_z(wall)
        grosor = float(wall.get("grosor", 0.0))
        longitud = float(wall.get("longitud", 0.0))
        wall_base_info.append({"wall": wall, "x": x, "y": y, "z": z, "weight": max(grosor * longitud, 0.01)})

    total_wall_weight = sum(item["weight"] for item in wall_base_info) or 1.0

    def levels_above_for_wall(item):
        count = 0
        for other in wall_base_info:
            same_stack = abs(other["x"] - item["x"]) < 0.08 and abs(other["y"] - item["y"]) < 0.08
            if same_stack and other["z"] >= item["z"] - 0.05:
                count += 1
        return max(count, 1)

    def demands_for_wall(wall):
        if not wall_pm_data:
            return []
        x, y, z = wall_mid_and_z(wall)
        grosor = float(wall.get("grosor", 0.0))
        longitud = float(wall.get("longitud", 0.0))
        item = {"wall": wall, "x": x, "y": y, "z": z, "weight": max(grosor * longitud, 0.01)}
        tributary_width = 3.0
        tributary_area = max(longitud, 0.1) * tributary_width
        n_levels = levels_above_for_wall(item)
        h_eff = max(3.0, n_levels * 3.2)
        lateral_share = item["weight"] / total_wall_weight
        out = []
        for combo_name, lambdas in combos.items():
            p_wall = tributary_area * (lambdas.get("G", 0) * q_g + lambdas.get("Q", 0) * q_Q) * n_levels
            v_base_x = seismic.get("corte_basal_EX_kN", 0.0) * abs(lambdas.get("EX", 0))
            v_base_y = seismic.get("corte_basal_EY_kN", 0.0) * abs(lambdas.get("EY", 0))
            v_wall = (v_base_x + v_base_y) * lateral_share
            m_wall = v_wall * h_eff
            out.append({
                "combo": combo_name,
                "P_kN": round(p_wall, 2),
                "M_kN_m": round(m_wall, 2),
                "V_kN": round(v_wall, 2),
                "note": f"Muro {wall.get('id')}: Atrib={tributary_area:.1f} m2, niveles sobre muro={n_levels}, reparto sismico por t*L={lateral_share:.3f}. V de corte en plano y M estimados por reparto del corte basal."
            })
        return out

    # ── Empaquetar combinaciones ─────────────────────────────────────
    combos_list = []
    for name in ["C1", "C2", "C3"]:
        combos_list.append({
            "name": name,
            "label": combo_labels[name],
            "G": combos[name].get("G", 0),
            "Q": combos[name].get("Q", 0),
            "EX": combos[name].get("EX", 0),
            "EY": combos[name].get("EY", 0)
        })

    # ── Empaquetar metadatos del muro analizado ──────────────────────
    walls_enriched = []
    wall_registry = []
    for i, wall in enumerate(data.get("walls", [])):
        grosor = float(wall.get("grosor", 0.0))
        longitud = float(wall.get("longitud", 0.0))
        has_curve = bool(wall_pm_data)
        entry = dict(wall)
        entry["id"] = i + 1
        entry["elementTag"] = "MURO-{:03d}".format(i + 1)
        entry["sourceBuilding"] = wall.get("sourceBuilding", "edificio_1")
        entry["sourceId"] = wall.get("sourceId", str(i + 1))
        entry["demands"] = demands_for_wall(entry)
        walls_enriched.append(entry)
        wall_registry.append({
            "index": i + 1,
            "nodeI": wall.get("nodeI"),
            "nodeJ": wall.get("nodeJ"),
            "grosor": grosor,
            "longitud": longitud,
            "bottom": wall.get("bottom", ""),
            "top": wall.get("top", ""),
            "pmSectionId": "W_DPRIME_OPENING_TO_3" if has_curve else "",
            "hasCurve": has_curve,
            "demands": entry["demands"]
        })

    # ── JSON de salida ───────────────────────────────────────────────
    curva_muro_n = len(wall_pm_data) if wall_pm_data else 0
    output = {
        "p1l4": {
            "version": "1.0",
            "combinations": combos_list,
            "displacements": displacements_flat,
            "elementForces": element_forces_flat,
            "pmCurves": pm_curves,
            "sectionMaterials": SECTION_MATERIALS,
            "wallRegistry": wall_registry
        },
        "units": data.get("units", "m, kN, kN*m"),
        "q_G": data.get("q_G", q_g),
        "seismic_coefficient": sc,
        "Q_kN_m2": q_Q,
        "notes": [
            "JSON enriquecido para Unity P1L4",
            "Desplazamientos y fuerzas internas de analisis estatico lineal OpenSees",
            "Fuerzas internas en coordenadas locales del elemento (12 componentes: N, Vy, Vz, T, My, Mz x2 extremos)",
            "Curvas P-M: COL70/70_FIBER (5 puntos, semana3) y W_DPRIME_OPENING_TO_3 ({} puntos, P1L3)".format(curva_muro_n),
            "Demandas muro: estimadas por tributaria + sismo (hipotesis documentadas)"
        ],
        "nodes": data.get("nodes", []),
        "elements": data.get("elements", []),
        "walls": walls_enriched,
        "supports": data.get("supports", []),
        "diaphragmList": data.get("diaphragmList", []),
        "slabs": data.get("slabs", []),
        "pointLoads": data.get("pointLoads", []),
        "tributaryList": data.get("tributaryList", [])
    }

    # ── Guardar ──────────────────────────────────────────────────────
    write_json(JSON_OUT, output)
    n_nodes = len(data.get("nodes", []))
    n_elements = len(data.get("elements", []))
    n_combos = len(combos_list)
    n_disp = len(displacements_flat)
    n_forces = len(element_forces_flat)
    n_pm = len(pm_curves)
    print(f"\nJSON enriquecido guardado en: {JSON_OUT}")
    print(f"  Nodos: {n_nodes}")
    print(f"  Elementos: {n_elements}")
    print(f"  Combinaciones: {n_combos}")
    print(f"  Registros desplazamientos: {n_disp} ({n_disp // max(n_nodes, 1)} por nodo)")
    print(f"  Registros fuerzas_elem: {n_forces} (casos G/Q/EX/EY + C1/C2/C3)")
    print(f"  Curvas P-M: {n_pm}")
    print("Listo.")


if __name__ == "__main__":
    main()
