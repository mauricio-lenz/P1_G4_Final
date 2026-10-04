"""Semana 6: QA final estructural, reproducible.

Corre las pruebas de la tabla del informe con el modelo vigente y guarda la
evidencia en Proyecto1/resultados/qa_semana06.json:

  Equilibrio G y Q      carga vertical aplicada = suma de reacciones (OpenSees)
  Corte basal EX y EY   fuerza lateral aplicada = suma de reacciones horizontales
  Superposicion         C1..C3 explicitas vs suma de casos base (desplazamientos, reacciones, fuerzas)
  M-phi                 seccion de fibras COL70/70: convergencia de malla 10x10 / 20x20 / 40x40
  P-M columna           demanda C1..C3 de las COL70/70 vs curva COL70/70_FIBER (G35)
  P-M muro              demanda de los muros vs curva W_DPRIME_OPENING_TO_3
  IDs Unity             ids y elementTag unicos, fuerzas para cada elemento y combo, nodos validos

Uso: python -X utf8 Proyecto1/scripts/qa_semana06.py
"""
import json
import math
from pathlib import Path

import carga_viva_sismo as cvm

ROOT = Path(__file__).resolve().parents[1]
UNITY_JSON = ROOT / "edificio_G4" / "Assets" / "Resources" / "estructura_p1l4_unity.json"
OUT = ROOT / "resultados" / "qa_semana06.json"
TOL_KN = 1e-6


def capacity_at(points, p):
    """M resistente para P interpolando la curva por tramos ordenada por P (0 fuera de la curva)."""
    pts = sorted(points, key=lambda q: q["P_kN"])
    if p <= pts[0]["P_kN"] or p >= pts[-1]["P_kN"]:
        return 0.0
    for a, b in zip(pts, pts[1:]):
        if a["P_kN"] <= p <= b["P_kN"]:
            t = (p - a["P_kN"]) / max(1e-9, b["P_kN"] - a["P_kN"])
            return abs(a["M_kN_m"]) + t * (abs(b["M_kN_m"]) - abs(a["M_kN_m"]))
    return 0.0


def wall_capacity_at(points, p):
    """Curva del muro (lista P-M de part_e_wall / Unity): misma interpolacion."""
    return capacity_at(points, p)


def main():
    data = cvm.load_json(cvm.JSON_PATH)
    params = cvm.load_analysis_params()
    cvm.apply_model_params(data, params.get("q_G_kN_m2"), params.get("sections"), params.get("rigidezFisurada"))
    q_q = cvm.kg_m2_to_kn_m2(float(params.get("Q_kg_m2", 500.0)))
    sc = cvm.seismic_setting(params)
    live = cvm.transfer_live_load(data, q_q)
    seis = cvm.build_seismic_cases(data, live, sc)
    loads = {
        "G": cvm.dead_nodal_loads(data),
        "Q": cvm.vector_loads_from_dict(live["cargas_nodales_Q"]),
        "EX": cvm.vector_loads_from_dict(seis["cargas_nodales_EX"]),
        "EY": cvm.vector_loads_from_dict(seis["cargas_nodales_EY"]),
    }
    qa = {"parametros": {"q_G_kN_m2": data.get("q_G"), "Q_kN_m2": q_q, "sismo": sc}}

    # ---- sismo NCh433: C dentro de [Cmin, Cmax], sum F = Q0 por edificio, sum A_k = 1 ----
    if seis.get("edificios"):
        filas = []
        for b in seis["edificios"]:
            pisos = [r for r in seis["pisos"] if r["edificio"] == b["edificio"]]
            fx, fy = sum(r["F_EX_kN"] for r in pisos), sum(r["F_EY_kN"] for r in pisos)
            filas.append({
                "edificio": b["edificio"], "P_kN": b["P_kN"], "T_X_s": b["T_X_s"], "T_Y_s": b["T_Y_s"],
                "C_X": b["C_X"], "C_Y": b["C_Y"], "Q0_X_kN": b["Q0_X_kN"], "Q0_Y_kN": b["Q0_Y_kN"],
                "C_en_limites": all(b["Cmin"] - 1e-12 <= b[c] <= b["Cmax"] + 1e-12 for c in ("C_X", "C_Y")),
                "sumF_igual_Q0": abs(fx - b["Q0_X_kN"]) < 1e-6 and abs(fy - b["Q0_Y_kN"]) < 1e-6,
                "sumA_k": sum(r["A_k"] for r in pisos),
            })
        qa["sismo_NCh433"] = {"hipotesis": seis["hipotesis_masa"], "edificios": filas,
                              "ok": all(f["C_en_limites"] and f["sumF_igual_Q0"] and abs(f["sumA_k"] - 1.0) < 1e-9 for f in filas)}

    # ---- equilibrio y corte basal ----
    for case, comp, key in (("G", 2, "sum_Fz"), ("Q", 2, "sum_Fz"), ("EX", 0, "sum_Fx"), ("EY", 1, "sum_Fy")):
        res = cvm.run_and_extract(data, loads[case])
        applied = sum(v[comp] for v in loads[case].values())
        reaction = res["reactions"][key]
        err = applied + reaction
        qa[case] = {"aplicada_kN": abs(applied), "reaccion_kN": abs(reaction), "error_kN": err,
                    "ok": abs(err) < max(TOL_KN, 1e-9 * abs(applied))}
        print(f"{case:2s}: aplicada {abs(applied):10.1f} kN | reaccion {abs(reaction):10.1f} kN | error {err:.2e} kN")
    qa["EX"]["esperado_kN"] = seis["corte_basal_EX_kN"]
    qa["EY"]["esperado_kN"] = seis["corte_basal_EY_kN"]

    # ---- superposicion ----
    combos = cvm.load_combinations()
    sup = cvm.superposition_check_multi(data, live, seis, combos)
    qa["superposicion"] = {
        "combinaciones": list(combos.keys()),
        "max_err_global": sup.get("max_err_global"),
        "valida": bool(sup.get("superposicion_valida")),
    }
    print(f"Superposicion: max error {sup.get('max_err_global'):.2e} | valida {sup.get('superposicion_valida')}")

    # ---- M-phi: convergencia de malla de la seccion de fibras ----
    mphi = {}
    for n in (10, 20, 40):
        curv, m = cvm._fiber_moment_curvature(0.0, n, 0.12, 300)
        k = curv[m.index(max(m))]
        mphi[n] = {"Mmax_kN_m": max(m), "phi_Mmax_1_m": k, "EI0_kN_m2": cvm._fiber_rigidez_inicial(curv, m)}
    dif = abs(mphi[20]["Mmax_kN_m"] - mphi[40]["Mmax_kN_m"]) / mphi[40]["Mmax_kN_m"] * 100.0
    qa["M_phi"] = {"mallas": {str(k): v for k, v in mphi.items()}, "dif_20_vs_40_pct": dif, "ok": dif < 1.0}
    print(f"M-phi (P=0): Mmax 10x10 {mphi[10]['Mmax_kN_m']:.1f} | 20x20 {mphi[20]['Mmax_kN_m']:.1f} | 40x40 {mphi[40]['Mmax_kN_m']:.1f} kN-m | dif 20 vs 40 = {dif:.3f} %")

    # ---- P-M columna y muro (con el JSON que lee Unity) ----
    u = json.loads(UNITY_JSON.read_text(encoding="utf-8"))
    curves = {c["sectionId"]: c for c in u["p1l4"]["pmCurves"]}
    col_pts = curves["COL70/70_FIBER"]["points"]
    forces = {}
    for f in u["p1l4"]["elementForces"]:
        forces[(f["id"], f["combo"])] = f["f"]
    worst = None
    n_cols = 0
    for e in u["elements"]:
        if e.get("sectionId") != "COL70/70":
            continue
        n_cols += 1
        for combo in combos:
            f = forces.get((e["id"], combo))
            if not f:
                continue
            p = -0.5 * (-f[0] + f[6])                       # compresion +, N interno al centro
            m = max(math.hypot(f[4], f[5]), math.hypot(f[10], f[11]))
            cap = capacity_at(col_pts, p)
            ratio = m / cap if cap > 0 else float("inf")
            if worst is None or ratio > worst["C"]:
                worst = {"elementTag": e["elementTag"], "combo": combo, "P_kN": p, "M_kN_m": m, "Mcap_kN_m": cap, "C": ratio}
    qa["PM_columna"] = {"columnas": n_cols, "peor": worst, "ok": worst is not None and worst["C"] <= 1.0}
    print(f"P-M columna: {n_cols} COL70/70 | peor {worst['elementTag']} {worst['combo']}: P={worst['P_kN']:.0f} kN, "
          f"M={worst['M_kN_m']:.0f} kN-m, Mcap={worst['Mcap_kN_m']:.0f} -> C={worst['C']:.2f}")

    registry = {r["index"]: r.get("pmSectionId") for r in u["p1l4"].get("wallRegistry", [])}
    wworst = None
    n_walls = 0
    n_over = 0
    for w in u.get("walls", []):
        n_walls += 1
        sid = registry.get(w.get("id")) or "W_DPRIME_OPENING_TO_3"
        wall_pts = curves.get(sid, curves["W_DPRIME_OPENING_TO_3"])["points"]
        over = False
        for d in w.get("demands", []):
            cap = wall_capacity_at(wall_pts, d["P_kN"])
            ratio = d["M_kN_m"] / cap if cap > 0 else 99.0   # 99: P fuera de la curva (traccion o compresion excedida)
            over = over or ratio > 1.0
            if wworst is None or ratio > wworst["C"]:
                wworst = {"muro": w.get("elementTag"), "curva": sid, "combo": d["combo"], "P_kN": d["P_kN"], "M_kN_m": d["M_kN_m"], "Mcap_kN_m": cap, "C": ratio}
        n_over += over
    qa["PM_muro"] = {"muros": n_walls, "muros_C_mayor_1": n_over, "peor": wworst, "ok": n_over == 0,
                     "nota": "demanda del analisis OpenSees (columna ancha); curva escalada por geometria de cada muro (misma cuantia)"}
    print(f"P-M muro: {n_walls} muros, {n_over} con C>1 | peor {wworst['muro']} {wworst['combo']}: P={wworst['P_kN']:.0f}, "
          f"M={wworst['M_kN_m']:.0f}, Mcap={wworst['Mcap_kN_m']:.0f} -> C={wworst['C']:.2f}")

    # ---- IDs Unity ----
    ids = [e["id"] for e in u["elements"]]
    tags = [e["elementTag"] for e in u["elements"]]
    node_ids = {n["id"] for n in u["nodes"]}
    casos = ["G", "Q", "EX", "EY"] + list(combos.keys())
    missing = [(i, c) for i in ids for c in casos if (i, c) not in forces]
    bad_nodes = [e["elementTag"] for e in u["elements"] if e["nodeI"] not in node_ids or e["nodeJ"] not in node_ids]
    qa["IDs_Unity"] = {
        "elementos": len(ids), "ids_unicos": len(set(ids)) == len(ids), "tags_unicos": len(set(tags)) == len(tags),
        "fuerzas_faltantes": len(missing), "nodos_invalidos": len(bad_nodes), "casos": casos,
        "ok": len(set(ids)) == len(ids) and len(set(tags)) == len(tags) and not missing and not bad_nodes,
    }
    print(f"IDs Unity: {len(ids)} elementos | ids unicos {qa['IDs_Unity']['ids_unicos']} | tags unicos {qa['IDs_Unity']['tags_unicos']} | "
          f"fuerzas faltantes {len(missing)} | nodos invalidos {len(bad_nodes)}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(qa, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(f"\nEvidencia: {OUT}")


if __name__ == "__main__":
    main()
