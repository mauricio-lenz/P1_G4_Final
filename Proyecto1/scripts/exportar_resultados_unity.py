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
  python P1L4/exportar_resultados_unity.py --q-kg-m2 500 --sc 0.20      (C fijo)
  python P1L4/exportar_resultados_unity.py --sismo nch433 --suelo D --R 7  (NCh433)

El JSON se escribe en:
  P1L4/edificio_G4/Assets/Resources/estructura_p1l4_unity.json
"""

import sys
import os
import json
import math
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
        "materialName": "G35 / Acero A630-420H",
        "fc_MPa": 35.0,
        "fy_MPa": 420.0,
        "E_MPa": 27806.0,
        "b_m": 0.70,
        "h_m": 0.70,
        "note": "Seccion rectangular 70x70 cm, G35 (fc=35 MPa), fy=420 MPa"
    },
    {
        "sectionId": "COL70/70_FIBER",
        "elementType": "columna",
        "materialName": "G35 / Acero A630-420H (analisis fibra)",
        "fc_MPa": 35.0,
        "fy_MPa": 420.0,
        "E_MPa": 27806.0,
        "b_m": 0.70,
        "h_m": 0.70,
        "steelBars": 8,
        "barDiameter_mm": 25.0,
        "Ast_mm2": 3927.0,
        "rho_percent": 0.80,
        "Po_kN": 14044.2,
        "note": "Analisis fibra P-M: G35, fy=420, 8 phi25, rec=52.5mm"
    },
    {
        "sectionId": "W_DPRIME_OPENING_TO_3",
        "elementType": "muro",
        "materialName": "G35 / Acero A630-420H (muro con abertura)",
        "fc_MPa": 35.0,
        "fy_MPa": 420.0,
        "E_MPa": 27806.0,
        "b_m": 0.25,
        "h_m": 7.60,
        "steelBars": 76,
        "barDiameter_mm": 12.0,
        "As_total_mm2": 8595.4,
        "rho_percent": 0.45,
        "Pn0_kN": 0.85 * 35000.0 * 0.25 * 7.60,
        "note": "Muro D-PRIME-OPENING-TO-3, t=0.25, L=7.60, 2 capas phi12@200"
    },
    {
        "sectionId": "V60/80",
        "elementType": "viga",
        "materialName": "G35 / Acero A630-420H (viga)",
        "fc_MPa": 35.0,
        "fy_MPa": 420.0,
        "E_MPa": 27806.0,
        "b_m": 0.60,
        "h_m": 0.80,
        "note": "Viga 60x80 cm"
    },
    {
        "sectionId": "V40/80",
        "elementType": "viga",
        "materialName": "G35 / Acero A630-420H (viga)",
        "fc_MPa": 35.0,
        "fy_MPa": 420.0,
        "E_MPa": 27806.0,
        "b_m": 0.40,
        "h_m": 0.80,
        "note": "Viga 40x80 cm"
    },
    {
        "sectionId": "V30/80",
        "elementType": "viga",
        "materialName": "G35 / Acero A630-420H (viga)",
        "fc_MPa": 35.0,
        "fy_MPa": 420.0,
        "E_MPa": 27806.0,
        "b_m": 0.30,
        "h_m": 0.80,
        "note": "Viga 30x80 cm"
    },
    {
        "sectionId": "V30/45",
        "elementType": "viga",
        "materialName": "G35 / Acero A630-420H (viga)",
        "fc_MPa": 35.0,
        "fy_MPa": 420.0,
        "E_MPa": 27806.0,
        "b_m": 0.30,
        "h_m": 0.45,
        "note": "Viga 30x45 cm"
    },
    {
        "sectionId": "V40/60",
        "elementType": "viga",
        "materialName": "G35 / Acero A630-420H (viga)",
        "fc_MPa": 35.0,
        "fy_MPa": 420.0,
        "E_MPa": 27806.0,
        "b_m": 0.40,
        "h_m": 0.60,
        "note": "Viga 40x60 cm (eje x=37.55, pisos 3 y 4)"
    },
    {
        "sectionId": "PM300x300x20",
        "elementType": "columna",
        "materialName": "Acero A36 (perfil cajon)",
        "fy_MPa": 250.0,
        "E_MPa": 200000.0,
        "b_m": 0.30,
        "h_m": 0.30,
        "t_m": 0.020,
        "note": "Pilar metalico cajon 300x300x20 mm (P.M. planos 2017_67)"
    },
    {
        "sectionId": "VM300x300x5",
        "elementType": "arriostre",
        "materialName": "Acero A36 (perfil cajon)",
        "fy_MPa": 250.0,
        "E_MPa": 200000.0,
        "b_m": 0.30,
        "h_m": 0.30,
        "t_m": 0.005,
        "note": "Arriostre metalico cajon 300x300x5 mm (V.M. (ARR) planos 2017_67)"
    }
]


# Acero de las estructuras metalicas segun la nota general de los planos
# (2017_67-100 / 2024_22-100): A36, fy = 250 MPa.
STEEL_FY_MPA = 250.0
PHI_STEEL = 0.90


def steel_box_pm_curve(section_id, b, t, fy_mpa=STEEL_FY_MPA, phi=PHI_STEEL):
    """Curva P-M de un perfil cajon cuadrado b x b x t segun AISC 360 H1-1.

    Pc = phi*A*fy y Mc = phi*Z*fy (Z plastico del cajon); sin reduccion por
    pandeo (columna corta). Simetrica en compresion (P > 0) y traccion (P < 0).
    """
    fy = fy_mpa * 1000.0                     # kN/m2
    bi = b - 2.0 * t
    area = b * b - bi * bi
    z_plastic = (b ** 3 - bi ** 3) / 4.0
    pc = phi * area * fy
    mc = phi * z_plastic * fy
    points = []
    for frac in (1.0, 0.6, 0.2, 0.0, -0.2, -0.6, -1.0):
        r = abs(frac)
        m_frac = 9.0 / 8.0 * (1.0 - r) if r >= 0.2 else 1.0 - r / 2.0
        label = "compresion pura" if frac == 1.0 else "traccion pura" if frac == -1.0 else f"P/Pc={frac:+.1f}"
        points.append({"label": label, "P_kN": round(frac * pc, 2), "M_kN_m": round(m_frac * mc, 2)})
    return {
        "sectionId": section_id,
        "elementType": "columna",
        "b_m": b,
        "h_m": b,
        "fc_MPa": 0.0,
        "fy_MPa": fy_mpa,
        "steelBars": 0,
        "barDiameter_mm": 0.0,
        "Ast_mm2": round(area * 1e6, 1),
        "rho_percent": 0.0,
        "Po_kN": round(pc, 2),
        "interpretation": (f"Interaccion AISC 360 H1-1 para cajon {int(b*1000)}x{int(b*1000)}x{int(t*1000)} mm, "
                           f"A36 fy={fy_mpa:.0f} MPa (planos), phi={phi}; Pc={pc:.0f} kN, Mc={mc:.0f} kN*m; "
                           "sin pandeo (columna corta)."),
        "points": points,
    }


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            json.dump(data, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        else:
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
    parser.add_argument("--q-kg-m2", type=float, default=None,
                        help="Carga viva Q en kg/m2 (default: data/parametros_analisis.json o 500)")
    parser.add_argument("--q-cubierta-kg-m2", type=float, default=None,
                        help="Sobrecarga de la cubierta (nivel superior) en kg/m2 (default: data/parametros_analisis.json o Q)")
    parser.add_argument("--sc", type=float, default=None,
                        help="Coeficiente sismico FIJO: F = C (D + 0.5Q). Si se da, reemplaza el metodo NCh433")
    parser.add_argument("--sismo", choices=("nch433", "fijo"), default=None,
                        help='Metodo sismico (default: "sismo" de data/parametros_analisis.json, NCh433)')
    parser.add_argument("--zona", type=int, default=None, help="NCh433: zona sismica 1, 2 o 3")
    parser.add_argument("--suelo", default=None, help="NCh433: tipo de suelo DS61 A, B, C, D o E")
    parser.add_argument("--R", type=float, default=None, help="NCh433: factor de modificacion de la respuesta R")
    parser.add_argument("--I", type=float, default=None, help="NCh433: coeficiente de importancia I")
    parser.add_argument("--fraccionQ", type=float, default=None, help="NCh433: fraccion de Q en el peso sismico (0.25 o 0.50)")
    parser.add_argument("--qG", type=float, default=None,
                        help="Carga muerta de losa q_G en kN/m2 (default: la del modelo). Escala la carga tributaria D de las vigas")
    parser.add_argument("--combos", type=Path, default=None,
                        help="Archivo de combinaciones (default: data/combinaciones.json)")
    parser.add_argument("--mods", type=Path, default=None,
                        help='JSON de modificaciones: {"sections": {"<id o tag>": {"width_m": b, "height_m": h, "sectionId": "V40/80"}}}')
    parser.add_argument("--armaduras", type=Path, default=None,
                        help="JSON con cambios de armadura (mismo formato que data/armaduras.json) sobre la armadura vigente")
    parser.add_argument("--fisurada", default=None,
                        help='Factores de inercia "viga,columna,muro" (ej. 0.35,0.70,0.35) o "bruta". Default: data/parametros_analisis.json')
    parser.add_argument("--out", type=Path, default=None,
                        help="JSON de salida (default: Assets/Resources/estructura_p1l4_unity.json). Desde Unity: escenario temporal")
    args = parser.parse_args()

    # Parametros guardados (los escribe Unity con "Guardar como modelo vigente"; editable en VS Code).
    # Los argumentos de consola tienen prioridad.
    params = cvm.load_analysis_params()
    if args.q_kg_m2 is None:
        args.q_kg_m2 = float(params.get("Q_kg_m2", 500.0))
    if args.q_cubierta_kg_m2 is None:
        args.q_cubierta_kg_m2 = float(params.get("Q_cubierta_kg_m2", args.q_kg_m2))
    c_fijo = float(args.sc if args.sc is not None else params.get("coeficienteSismico", cvm.DEFAULT_SEISMIC_COEFF))
    sismo_cfg = cvm.seismic_setting(params, sc=args.sc, overrides={
        "metodo": {"nch433": "NCh433", "fijo": "fijo"}.get(args.sismo), "C": c_fijo, "zona": args.zona,
        "suelo": args.suelo, "R": args.R, "I": args.I, "fraccionQ": args.fraccionQ})
    if args.qG is None and params.get("q_G_kN_m2"):
        args.qG = float(params["q_G_kN_m2"])
    secciones_param = params.get("sections", {}) or {}
    if args.fisurada is None:
        fisurada = params.get("rigidezFisurada")
    elif args.fisurada.strip().lower() == "bruta":
        fisurada = None
    else:
        kv, kc, km = (float(v) for v in args.fisurada.split(","))
        fisurada = {"viga": kv, "columna": kc, "muro": km}
    if params:
        print(f"Parametros de data/parametros_analisis.json: Q={args.q_kg_m2} kg/m2, q_G={args.qG}, secciones={len(secciones_param)}")

    q_Q = cvm.kg_m2_to_kn_m2(args.q_kg_m2)
    print(f"Parametros: Q={q_Q:.3f} kN/m2 ({args.q_kg_m2:.0f} kg/m2), Q cubierta={args.q_cubierta_kg_m2:.0f} kg/m2, sismo={sismo_cfg}")

    # ── Cargar datos base ───────────────────────────────────────────
    print("Cargando estructura base...")
    data = load_json(JSON_BASE)
    q_g = float(data.get("q_G", 6.227))
    secciones = dict(secciones_param)
    if args.mods is not None:
        secciones = load_json(args.mods).get("sections", {}) or {}
    modificaciones = cvm.apply_model_params(data, args.qG, secciones, fisurada, args.q_cubierta_kg_m2)
    q_g = float(data.get("q_G", q_g))

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
    # Se recomputa con la seccion de fibra (G35, fc=35 MPa) usando las
    # mismas funciones de P1L3/carga_viva_sismo.py para evitar la
    # inconsistencia historica entre la curva guardada (fc=25 MPa) y el
    # material del modelo (G35 segun planos).
    print("Calculando curva P-M columna COL70/70_FIBER (G35)...")
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
    seismic = cvm.build_seismic_cases(data, live_transfer, sismo_cfg)
    sc = seismic["coeficiente_sismico"]   # Q0x / P total (equivalente)
    for b in seismic.get("edificios", []):
        print(f"  NCh433 {b['edificio']}: T*x={b['T_X_s']:.3f} s Cx={b['C_X']:.3f} Q0x={b['Q0_X_kN']:.0f} kN | "
              f"T*y={b['T_Y_s']:.3f} s Cy={b['C_Y']:.3f} Q0y={b['Q0_Y_kN']:.0f} kN | P={b['P_kN']:.0f} kN")
    print(f"  Corte basal EX={seismic['corte_basal_EX_kN']:.0f} kN, EY={seismic['corte_basal_EY_kN']:.0f} kN ({seismic['hipotesis_masa']})")

    G = cvm.dead_nodal_loads(data)
    Q = cvm.vector_loads_from_dict(live_transfer["cargas_nodales_Q"])
    EX = cvm.vector_loads_from_dict(seismic["cargas_nodales_EX"])
    EY = cvm.vector_loads_from_dict(seismic["cargas_nodales_EY"])

    load_sets = {"G": G, "Q": Q, "EX": EX, "EY": EY}

    # ── Combinaciones: data/combinaciones.json (editable en VS Code) ──
    combos = cvm.load_combinations(args.combos) if args.combos else cvm.load_combinations()
    combo_labels = {name: cvm.combination_label(name, lam) for name, lam in combos.items()}
    print("Combinaciones: " + " | ".join(combo_labels.values()))

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

    # ── Peso propio por elemento (Unity lo suma como carga repartida) ──
    nodes_by_id = cvm.node_map(data)
    elements_out = []
    for el in data.get("elements", []):
        el_out = dict(el)
        if el.get("nodeI") in nodes_by_id and el.get("nodeJ") in nodes_by_id:
            el_out["selfWeight_kN"] = cvm.self_weight_kN(el, nodes_by_id)
        elements_out.append(el_out)

    # ── Armadura y capacidad ACI 318 (vigas y columnas de hormigon) ──
    import capacidad_ha as cha
    overrides = load_json(args.armaduras) if args.armaduras else None
    arm = cha.load_armaduras(overrides=overrides)
    col_curves = {}   # una curva P-M de diseno por seccion + armadura (no una por elemento)
    resumen_arm = {"vigas": 0, "columnas": 0, "vigas_DCR_mayor_1": 0, "columnas_DCR_mayor_1": 0,
                   "DCR_max_viga": 0.0, "DCR_max_columna": 0.0, "peorViga": "", "peorColumna": ""}
    for el_out in elements_out:
        if el_out.get("type") not in ("viga", "columna") or el_out.get("removed"):
            continue
        if el_out.get("nodeI") not in nodes_by_id or el_out.get("nodeJ") not in nodes_by_id:
            continue
        length = cvm.element_length(el_out, nodes_by_id)
        fbc, wbc = {}, {}
        for combo_name, lambdas in combos.items():
            f = ((all_results.get(combo_name) or {}).get("element_forces") or {}).get(el_out["id"])
            if f:
                fbc[combo_name] = f
                wbc[combo_name] = cvm.gravity_w(el_out, nodes_by_id, lambdas) if el_out.get("type") == "viga" else 0.0
        cap = cha.evaluar(el_out, fbc, wbc, length, arm)
        if not cap:
            continue
        if "curvaPM" in cap:
            cid = "{}_{}".format(el_out.get("sectionId"), cap["armadura"].get("barras", "")).replace("φ", "f")
            col_curves[cid] = {"puntos": cap.pop("curvaPM"), "P0": cap.get("P0_kN", 0.0), "arm": dict(cap["armadura"]),
                               "b": el_out.get("width_m"), "h": el_out.get("height_m")}
            el_out["pmCurveId"] = cid
        el_out["capacidad"] = cap
        key = "vigas" if el_out["type"] == "viga" else "columnas"
        resumen_arm[key] += 1
        dcr = cap.get("DCR", 0.0)
        if dcr > 1.0:
            resumen_arm[key + "_DCR_mayor_1"] += 1
        tag_key, max_key = ("peorViga", "DCR_max_viga") if key == "vigas" else ("peorColumna", "DCR_max_columna")
        if dcr > resumen_arm[max_key]:
            resumen_arm[max_key] = dcr
            resumen_arm[tag_key] = el_out.get("elementTag", "")
    print(f"Armadura/capacidad: {resumen_arm}")

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
            "interpretation": "Diagrama P-M COL70/70 (5 puntos manuales: compresion pura, balance, falla ductil, flexion pura, traccion pura), fc=G35 (35 MPa).",
            "points": [{"label": p["label"], "P_kN": p["P_kN"], "M_kN_m": p["M_kN_m"]} for p in col_pm_data]
        })

    # Pilar metalico P.M. 300x300x20: interaccion AISC 360 H1-1 (sin pandeo)
    pm_curves.append(steel_box_pm_curve("PM300x300x20", 0.30, 0.020))

    if wall_pm_data:
        wall_points = [{"label": f'P/Pn0={p["P_frac"]:.2f}', "P_kN": p["P_kN"], "M_kN_m": p["Mmax_kNm"]} for p in wall_pm_data]
        pm_curves.append({
            "sectionId": "W_DPRIME_OPENING_TO_3",
            "elementType": "muro",
            "b_m": 0.25,
            "h_m": 7.60,
            "fc_MPa": 35.0,
            "fy_MPa": 420.0,
            "steelBars": 76,
            "barDiameter_mm": 12.0,
            "Ast_mm2": 8595.4,
            "rho_percent": 0.45,
            "Po_kN": float(wall_pm_full.get("Pn0_kN", 0.0)),
            "interpretation": f"Envolvente P-M W_DPRIME_OPENING_TO_3 (t=0.25m, L=7.60m, 2 capas phi12@200). {len(wall_points)} puntos de la envolvente.",
            "points": wall_points
        })

    # Curva por geometria de muro: escalada de la de referencia (t=0.25, L=7.60) con la misma
    # cuantia y disposicion (2 capas phi12@200): P ~ t*L, M ~ t*L^2. Aproximacion de primer orden.
    wall_curve_id = {}
    if wall_pm_data:
        for wall in data.get("walls", []):
            t = float(wall.get("grosor", 0.0)); L = float(wall.get("longitud", 0.0))
            sid = "W_ESC_{:d}x{:d}".format(int(round(t * 100)), int(round(L * 100)))
            wall_curve_id[id(wall)] = sid
            if any(c["sectionId"] == sid for c in pm_curves):
                continue
            fp = t * L / (0.25 * 7.60)
            fm = t * L * L / (0.25 * 7.60 * 7.60)
            pm_curves.append({
                "sectionId": sid, "elementType": "muro", "b_m": t, "h_m": L, "fc_MPa": 35.0, "fy_MPa": 420.0,
                "steelBars": 0, "barDiameter_mm": 12.0, "Ast_mm2": round(8595.4 * fp, 1), "rho_percent": 0.45,
                "Po_kN": float(wall_pm_full.get("Pn0_kN", 0.0)) * fp,
                "interpretation": f"Muro t={t:.2f} m, L={L:.2f} m: envolvente W_DPRIME escalada (P x{fp:.3f}, M x{fm:.3f}), "
                                  f"misma cuantia 0.45 % (2 capas phi12@200). Aproximacion: falta el detalle de armadura real.",
                "points": [{"label": p["label"], "P_kN": p["P_kN"] * fp, "M_kN_m": p["M_kN_m"] * fm} for p in wall_points],
            })

    # ── Regenerar semana3_resultados_unity.json (G35) ─────────────
    # Deja el archivo de capacidad de P1L2 consistente con el modelo
    # (hormigon G35) y con lo que Unity carga en la escena P1L2.
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
                "interpretation": "Diagrama P-M COL70/70 (5 puntos manuales), fc=G35 (35 MPa). Regenerado por P1L4/exportar_resultados_unity.py.",
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
            print("  semana3_resultados_unity.json regenerado (G35).")
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

    # Reparto sismico: cada muro toma el corte de piso de SU edificio (suma de
    # las fuerzas de los pisos sobre su base), segun su orientacion (un muro
    # en X resiste EX, uno en Y resiste EY) y su rigidez relativa t*L entre
    # los muros del mismo edificio y piso.
    def wall_axis(wall):
        ni = nodes_map.get(wall.get("nodeI"))
        nj = nodes_map.get(wall.get("nodeJ"))
        if not ni or not nj:
            return 0.0, 0.0
        dx, dy = abs(nj[0] - ni[0]), abs(nj[1] - ni[1])
        length = (dx * dx + dy * dy) ** 0.5 or 1.0
        return dx / length, dy / length

    def wall_building(wall):
        return wall.get("sourceBuilding") or "edificio_1"

    storey_weight = {}
    for item in wall_base_info:
        cx, cy = wall_axis(item["wall"])
        key = (wall_building(item["wall"]), round(item["z"], 2))
        wx, wy = storey_weight.get(key, (0.0, 0.0))
        storey_weight[key] = (wx + item["weight"] * cx, wy + item["weight"] * cy)

    def storey_shear(building, z_base):
        return sum(row["F_EX_kN"] for row in seismic.get("pisos", [])
                   if row.get("edificio") == building and row["floor_z_m"] > z_base + 0.05)

    def levels_above_for_wall(item):
        count = 0
        for other in wall_base_info:
            same_stack = abs(other["x"] - item["x"]) < 0.08 and abs(other["y"] - item["y"]) < 0.08
            if same_stack and other["z"] >= item["z"] - 0.05:
                count += 1
        return max(count, 1)

    # Muros en el analisis (columna ancha, paso 14 de ajustar_modelo_planos):
    # la demanda sale de las fuerzas del elemento del muro en cada combinacion.
    wall_elements = {int(e["wallIndex"]): e for e in data.get("elements", []) if e.get("type") == "muro" and e.get("wallIndex")}

    def analysis_demands(wall):
        e = wall_elements.get(int(wall.get("id", 0)))
        if e is None:
            return None
        out = []
        for combo_name in combos:
            res = all_results.get(combo_name) or {}
            f = (res.get("element_forces") or {}).get(e["id"])
            if not f or len(f) < 12:
                continue
            # columna vertical: local y = -Y, z = +X. Muro a lo largo de X: plano (Vz, My); a lo largo de Y: (Vy, Mz)
            in_x = e.get("wallInPlaneAxis", "X") == "X"
            k_v, k_m = (2, 4) if in_x else (1, 5)
            p_comp = 0.5 * (f[0] - f[6])                     # compresion +, N al centro del pano
            m_base = max(abs(f[k_m]), abs(f[6 + k_m]))     # momento en el plano, el mayor de base y tope
            v_plano = -f[k_v]                               # corte en el plano en la base (signo del caso)
            out.append({
                "combo": combo_name,
                "P_kN": round(p_comp, 2),
                "M_kN_m": round(m_base, 2),
                "V_kN": round(v_plano, 2),
                "note": f"Muro {e['elementTag'][2:]} ({e.get('sourceBuilding')}): fuerzas del analisis OpenSees "
                        f"(columna ancha {e.get('sectionId')}, elemento {e['id']}), M en el plano del muro ({'X' if in_x else 'Y'})."
            })
        return out

    def demands_for_wall(wall):
        analysed = analysis_demands(wall)
        if analysed is not None:
            return analysed
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
        building = wall_building(wall)
        cx, cy = wall_axis(wall)
        wx, wy = storey_weight.get((building, round(z, 2)), (0.0, 0.0))
        share_x = item["weight"] * cx / wx if wx > 1e-9 else 0.0
        share_y = item["weight"] * cy / wy if wy > 1e-9 else 0.0
        v_storey = storey_shear(building, z)
        out = []
        for combo_name, lambdas in combos.items():
            p_wall = tributary_area * (lambdas.get("G", 0) * q_g + lambdas.get("Q", 0) * q_Q) * n_levels
            # V en el plano del muro con signo: + en el sentido +X/+Y del sismo
            v_wall = v_storey * (lambdas.get("EX", 0) * share_x + lambdas.get("EY", 0) * share_y)
            m_wall = v_wall * h_eff
            out.append({
                "combo": combo_name,
                "P_kN": round(p_wall, 2),
                "M_kN_m": round(m_wall, 2),
                "V_kN": round(v_wall, 2),
                "note": f"Muro {wall.get('id')} ({building}): Atrib={tributary_area:.1f} m2, niveles sobre muro={n_levels}, "
                        f"corte de piso={v_storey:.1f} kN, reparto t*L por direccion X={share_x:.3f} Y={share_y:.3f}. "
                        f"V en plano y M estimados (el muro no esta en el analisis OpenSees)."
            })
        return out

    # ── Empaquetar combinaciones ─────────────────────────────────────
    combos_list = []
    for name in combos:
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
            "pmSectionId": wall_curve_id.get(id(wall), "W_DPRIME_OPENING_TO_3") if has_curve else "",
            "hasCurve": has_curve,
            "demands": entry["demands"]
        })

    # ── Sidequest: carga movil (casos unitarios por nodo del recorrido) ──
    print("\nPrecalculando carga movil (casos unitarios OpenSees)...")
    import carga_movil
    carga_movil_data = carga_movil.construir(data, cvm)

    # ── Resumen para la interfaz (equilibrio, corte basal, |u| maximo) ──
    def _u_max_mm(res):
        best = 0.0
        for d in (res or {}).get("displacements", {}).values():
            best = max(best, math.sqrt(d.get("ux", 0.0) ** 2 + d.get("uy", 0.0) ** 2 + d.get("uz", 0.0) ** 2))
        return 1000.0 * best
    resumen = {
        "q_G_kN_m2": q_g,
        "Q_kN_m2": q_Q,
        "coeficienteSismico": sc,
        "sismo": {
            "metodo": sismo_cfg["metodo"], "C_fijo": c_fijo,
            "zona": sismo_cfg.get("zona", 0), "suelo": sismo_cfg.get("suelo", ""), "R": sismo_cfg.get("R", 0.0),
            "I": sismo_cfg.get("I", 0.0), "fraccionQ": sismo_cfg.get("fraccionQ", 0.5),
            "hipotesis": seismic["hipotesis_masa"],
            "C_equivalente_X": seismic["coeficiente_sismico"], "C_equivalente_Y": seismic["coeficiente_sismico_Y"],
            "edificios": [{k: b[k] for k in ("edificio", "P_kN", "T_X_s", "T_Y_s", "C_X", "C_Y", "Q0_X_kN", "Q0_Y_kN")}
                          for b in seismic.get("edificios", [])],
        },
        "G_aplicada_kN": -sum(v[2] for v in G.values()),
        "G_reaccion_kN": (base_results.get("G") or {}).get("reactions", {}).get("sum_Fz", 0.0),
        "Q_aplicada_kN": -sum(v[2] for v in Q.values()),
        "Q_reaccion_kN": (base_results.get("Q") or {}).get("reactions", {}).get("sum_Fz", 0.0),
        "corteBasal_EX_kN": seismic.get("corte_basal_EX_kN", 0.0),
        "corteBasal_EY_kN": seismic.get("corte_basal_EY_kN", 0.0),
        "uMax": [{"caso": k, "u_mm": _u_max_mm(v)} for k, v in {**base_results, **all_results}.items()],
        "secciones": modificaciones,
        "armadura": resumen_arm,
        "rigidezViga": (fisurada or {}).get("viga", 1.0),
        "rigidezColumna": (fisurada or {}).get("columna", 1.0),
        "rigidezMuro": (fisurada or {}).get("muro", 1.0),
    }

    # Curvas P-M de diseno de columnas (capacidad_ha): una por seccion + armadura
    for cid, cc in col_curves.items():
        pm_curves.append({
            "sectionId": cid, "elementType": "columna", "b_m": cc["b"], "h_m": cc["h"], "fc_MPa": 35.0, "fy_MPa": 420.0,
            "Po_kN": cc["P0"], "Ast_mm2": 0.0, "barDiameter_mm": 0.0, "steelBars": 0, "rho_percent": 0.0,
            "interpretation": f"Curva de DISENO (phiPn, phiMn) ACI 318-19 por compatibilidad de deformaciones: "
                              f"{cc['arm'].get('barras', '')}, estribos {cc['arm'].get('estribos', '')}; phi 0.65-0.90, phiPmax = 0.80 phi P0.",
            "points": [{"label": "", "P_kN": q["P_kN"], "M_kN_m": q["M_kN_m"]} for q in cc["puntos"]],
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
            "wallRegistry": wall_registry,
            "cargaMovil": carga_movil_data
        },
        "units": data.get("units", "m, kN, kN*m"),
        "q_G": data.get("q_G", q_g),
        "seismic_coefficient": c_fijo,   # C del metodo fijo (el NCh433 queda en resumenAnalisis.sismo)
        "Q_kN_m2": q_Q,
        "Q_cubierta_kN_m2": data.get("Q_cubierta_kN_m2", q_Q),
        "resumenAnalisis": resumen,
        "notes": [
            "JSON enriquecido para Unity P1L4",
            "Desplazamientos y fuerzas internas de analisis estatico lineal OpenSees",
            "Fuerzas internas en coordenadas locales del elemento (12 componentes: N, Vy, Vz, T, My, Mz x2 extremos)",
            "G y Q se aplican como cargas repartidas sobre cada elemento (eleLoad -beamUniform): las fuerzas de extremo ya incluyen los momentos de empotramiento",
            "G incluye el peso propio de vigas, columnas y arriostres (selfWeight_kN; 25 kN/m3 hormigon, 78.5 kN/m3 acero)",
            "Curvas P-M: COL70/70_FIBER (5 puntos, semana3) y W_DPRIME_OPENING_TO_3 ({} puntos, P1L3)".format(curva_muro_n),
            "Demandas muro: estimadas por tributaria + sismo (hipotesis documentadas)"
        ],
        "nodes": data.get("nodes", []),
        "elements": elements_out,
        "walls": walls_enriched,
        "supports": data.get("supports", []),
        "diaphragmList": data.get("diaphragmList", []),
        "slabs": data.get("slabs", []),
        "pointLoads": data.get("pointLoads", []),
        "tributaryList": data.get("tributaryList", [])
    }

    # ── Guardar ──────────────────────────────────────────────────────
    # Compacto: el JSON de Unity es generado y la indentacion lo triplica de tamano
    out_path = args.out if args.out else JSON_OUT
    write_json(out_path, output, compact=True)
    n_nodes = len(data.get("nodes", []))
    n_elements = len(data.get("elements", []))
    n_combos = len(combos_list)
    n_disp = len(displacements_flat)
    n_forces = len(element_forces_flat)
    n_pm = len(pm_curves)
    print(f"\nJSON enriquecido guardado en: {out_path}")
    print(f"  Nodos: {n_nodes}")
    print(f"  Elementos: {n_elements}")
    print(f"  Combinaciones: {n_combos}")
    print(f"  Registros desplazamientos: {n_disp} ({n_disp // max(n_nodes, 1)} por nodo)")
    print(f"  Registros fuerzas_elem: {n_forces} (casos G/Q/EX/EY + C1/C2/C3)")
    print(f"  Curvas P-M: {n_pm}")
    print("Listo.")


if __name__ == "__main__":
    main()
