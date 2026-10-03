"""Sensibilidad a la rigidez fisurada (ACI 318-19 6.6.3.1.1).

Compara el modelo con seccion bruta y con inercias reducidas por tipo de
elemento: desplazamientos y derivas sismicas, corte que toman los muros y
utilizacion P-M de columnas COL70/70 y muros (C1-C3).

Uso: python -X utf8 Proyecto1/scripts/sensibilidad_rigidez.py
Salida: Proyecto1/resultados/sensibilidad_rigidez.json
"""
import json
import math
from pathlib import Path

import carga_viva_sismo as cvm

ROOT = Path(__file__).resolve().parents[1]
UNITY_JSON = ROOT / "edificio_G4" / "Assets" / "Resources" / "estructura_p1l4_unity.json"
OUT = ROOT / "resultados" / "sensibilidad_rigidez.json"
H_PISO = 3.96

ESCENARIOS = {
    "bruta": None,
    "ACI_fisurada": {"viga": 0.35, "columna": 0.70, "muro": 0.35},
    "muros_no_fisurados": {"viga": 0.35, "columna": 0.70, "muro": 0.70},
}


def capacity_at(points, p):
    pts = sorted(points, key=lambda q: q["P_kN"])
    if p <= pts[0]["P_kN"] or p >= pts[-1]["P_kN"]:
        return 0.0
    for a, b in zip(pts, pts[1:]):
        if a["P_kN"] <= p <= b["P_kN"]:
            t = (p - a["P_kN"]) / max(1e-9, b["P_kN"] - a["P_kN"])
            return abs(a["M_kN_m"]) + t * (abs(b["M_kN_m"]) - abs(a["M_kN_m"]))
    return 0.0


def max_drift(data, res, comp):
    """Deriva de entrepiso maxima (columnas y muros): |du| / h."""
    nodes = cvm.node_map(data)
    best = 0.0
    for e in cvm.structural_elements(data):
        if e.get("type") not in ("columna", "muro"):
            continue
        a, b = nodes[e["nodeI"]], nodes[e["nodeJ"]]
        h = abs(b["z"] - a["z"])
        if h < 1.0:
            continue
        da, db = res["displacements"].get(e["nodeI"]), res["displacements"].get(e["nodeJ"])
        if da and db:
            best = max(best, abs(db[comp] - da[comp]) / h)
    return best


def main():
    u = json.loads(UNITY_JSON.read_text(encoding="utf-8"))
    curves = {c["sectionId"]: c for c in u["p1l4"]["pmCurves"]}
    registry = {r["index"]: r.get("pmSectionId") for r in u["p1l4"].get("wallRegistry", [])}
    col_pts = curves["COL70/70_FIBER"]["points"]
    combos = cvm.load_combinations()
    out = {}
    for name, factors in ESCENARIOS.items():
        data = cvm.load_json(cvm.JSON_PATH)
        params = cvm.load_analysis_params()
        cvm.apply_model_params(data, params.get("q_G_kN_m2"), params.get("sections"), factors)
        q_q = cvm.kg_m2_to_kn_m2(float(params.get("Q_kg_m2", 500.0)))
        sc = float(params.get("coeficienteSismico", cvm.DEFAULT_SEISMIC_COEFF))
        live = cvm.transfer_live_load(data, q_q)
        seis = cvm.build_seismic_cases(data, live, sc)
        loads = {"G": cvm.dead_nodal_loads(data), "Q": cvm.vector_loads_from_dict(live["cargas_nodales_Q"]),
                 "EX": cvm.vector_loads_from_dict(seis["cargas_nodales_EX"]), "EY": cvm.vector_loads_from_dict(seis["cargas_nodales_EY"])}
        walls_nodes = set()
        for e in data["elements"]:
            if e.get("type") in ("muro", "rigido"):
                walls_nodes.update((e["nodeI"], e["nodeJ"]))
        res = {c: cvm.run_and_extract(data, l) for c, l in loads.items()}
        row = {}
        for c, comp in (("EX", "ux"), ("EY", "uy")):
            r = res[c]
            umax = max(abs(d[comp]) for d in r["displacements"].values()) * 1000.0
            share = sum(v[0 if c == "EX" else 1] for k, v in r["per_node_reactions"].items() if int(k) in walls_nodes)
            total = sum(v[0 if c == "EX" else 1] for v in r["per_node_reactions"].values())
            row[c] = {"u_max_mm": umax, "deriva_max": max_drift(data, r, comp), "corte_muros_pct": 100.0 * share / total}
        row["G_uz_max_mm"] = max(abs(d["uz"]) for d in res["G"]["displacements"].values()) * 1000.0
        # combinaciones por superposicion lineal (analisis lineal)
        col_worst, n_col_over, wall_over, wall_worst = 0.0, 0, set(), 0.0
        elems = {e["id"]: e for e in data["elements"]}
        for combo, lam in combos.items():
            for eid, e in elems.items():
                if e.get("sectionId") != "COL70/70" and e.get("type") != "muro":
                    continue
                f = [sum(lam.get(k, 0.0) * res[k]["element_forces"][eid][i] for k in loads) for i in range(12)]
                p = 0.5 * (f[0] - f[6])
                if e.get("type") == "muro":
                    k_m = 4 if e.get("wallInPlaneAxis", "X") == "X" else 5
                    m = max(abs(f[k_m]), abs(f[6 + k_m]))
                    pts = curves.get(registry.get(e["wallIndex"]) or "W_DPRIME_OPENING_TO_3")["points"]
                    cap = capacity_at(pts, p)
                    c_ratio = m / cap if cap > 0 else 99.0
                    wall_worst = max(wall_worst, c_ratio)
                    if c_ratio > 1.0:
                        wall_over.add(e["elementTag"])
                else:
                    m = max(math.hypot(f[4], f[5]), math.hypot(f[10], f[11]))
                    cap = capacity_at(col_pts, p)
                    c_ratio = m / cap if cap > 0 else 99.0
                    col_worst = max(col_worst, c_ratio)
        row["columnas_C_max"] = col_worst
        row["muros_C_mayor_1"] = sorted(wall_over)
        row["muros_C_max"] = min(wall_worst, 99.0)
        out[name] = {"factores": factors or "seccion bruta", **row}
        print(f"{name:20s} | EX: u={row['EX']['u_max_mm']:5.1f} mm deriva={row['EX']['deriva_max']*1000:.2f} o/oo muros {row['EX']['corte_muros_pct']:4.0f}% "
              f"| EY: u={row['EY']['u_max_mm']:5.1f} mm deriva={row['EY']['deriva_max']*1000:.2f} o/oo muros {row['EY']['corte_muros_pct']:4.0f}% "
              f"| G uz={row['G_uz_max_mm']:.1f} mm | col C max={col_worst:.2f} | muros C>1: {len(wall_over)} {sorted(wall_over)}")
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nEvidencia: {OUT}")


if __name__ == "__main__":
    main()
