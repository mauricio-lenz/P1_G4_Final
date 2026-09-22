# ============================================================
# PARTE C - SUPERPOSICION LINEAL DE CASOS (Semana 3)
# ============================================================
# Verifica la validez de la superposicion lineal de los casos base
# G (muerta), Q (viva), EX y EY para un modelo lineal elastico:
#
#   R = lambda_G * G + lambda_Q * Q + lambda_EX * EX + lambda_EY * EY
#
# Se compara la combinacion (suma ponderada de los resultados de cada
# corrida independiente) contra una corrida EXPLICITA donde los cuatro
# patrones de carga actuan simultaneamente sobre el mismo modelo, en:
#   - desplazamientos nodales
#   - reacciones de apoyo
#   - fuerzas internas de elementos (vigas + columnas)
#
# Si el modelo es lineal, la diferencia debe ser ~precision de maquina.
# Unidades: kN y metros.
# ============================================================
import json, os
from math import fsum

from base_cases import (build, run_case, D_BY_LEVEL, Q_BY_LEVEL,
                        apply_floor_loads, build_model, run_analysis,
                        extract_displacements, extract_reactions,
                        extract_element_forces, floor_masses, apply_seismic)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")

# Factores de combinacion (lineal elastico)
LAMBDAS = {"G": 1.00, "Q": 0.50, "EX": 0.30, "EY": 0.20}


def run_explicit_combined(geometry, structure, beam_data, lambdas):
    """Corre los 4 casos simultaneamente en UN modelo y devuelve resultados."""
    build_model(structure, geometry)  # limpia y reconstruye

    # G y Q se aplican como carga uniforme sobre las vigas
    qm_g = {lv: D_BY_LEVEL.get(lv, 0.0) * lambdas["G"] for lv in D_BY_LEVEL}
    apply_floor_loads(structure, beam_data, qm_g, 10, 10)
    qm_q = {lv: Q_BY_LEVEL.get(lv, 0.0) * lambdas["Q"] for lv in Q_BY_LEVEL}
    apply_floor_loads(structure, beam_data, qm_q, 11, 11)

    # EX y EY como fuerzas en el centro de masa de cada piso
    _, _, F = floor_masses(structure, geometry)
    F_ex = {lv: f * lambdas["EX"] for lv, f in F.items()}
    F_ey = {lv: f * lambdas["EY"] for lv, f in F.items()}
    apply_seismic(structure, F_ex, 'x', 12, 12)
    apply_seismic(structure, F_ey, 'y', 13, 13)

    ok = run_analysis()
    return {
        "convergio": ok == 0,
        "displacements": extract_displacements(structure),
        "reactions": extract_reactions(structure),
        "element_forces": extract_element_forces(structure),
    }


def _max_node_error(case_out, explicit, lambda_key, tag):
    """Max diferencia absoluta de un campo por nodo/elemento."""
    worst = 0.0
    worst_key = None
    for nid, vals in case_out[tag].items():
        for i, v in enumerate(vals):
            diff = abs(v - explicit[tag][nid][i])
            if diff > worst:
                worst = diff
                worst_key = nid
    return worst, worst_key


def combinados_suma(casos, lambdas, tag_comb):
    """Suma de un campo 'disp' (dict nid->dict) o 'forces' (dict).
    Cada caso ya viene escalado por su lambda (run_case aplica la carga),
    por lo que aqui solo se suman directamente."""
    if tag_comb == "disp":
        keys = set()
        for c in casos.values():
            keys.update(c["displacements"].keys())
        total = {}
        for k in keys:
            total[k] = {
                d: fsum(c["displacements"][k][d] for c in casos.values()
                        if k in c["displacements"] and
                        d in c["displacements"][k])
                for d in ("ux", "uy", "uz", "rx", "ry", "rz")}
        return total
    else:  # forces
        tags = set()
        for c in casos.values():
            tags.update(c["element_forces"].keys())
        total = {}
        for t in tags:
            total[t] = [fsum(
                c["element_forces"][t][i] for c in casos.values()
                if t in c["element_forces"] and
                i < len(c["element_forces"][t]))
                for i in range(12)]
        return total


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    geometry, structure, beam_data = build()

    casos = {}
    for case, lam in LAMBDAS.items():
        casos[case] = run_case(geometry, structure, beam_data, case, lam)
        print(f"  caso {case}: lambda={lam}  convergio="
              f"{casos[case]['convergio']}")

    print("\nCorriendo combinacion EXPLICITA (4 patrones simultaneos)...")
    explicit = run_explicit_combined(geometry, structure, beam_data, LAMBDAS)
    print(f"  convergio = {explicit['convergio']}")

    # --- Desplazamientos ---
    disp_sum = combinados_suma(casos, LAMBDAS, "disp")
    worstD = 0.0; worstD_key = None; worstD_dof = None
    for nid, d in disp_sum.items():
        e = explicit["displacements"].get(nid)
        if not e:
            continue
        for dof in ("ux", "uy", "uz", "rx", "ry", "rz"):
            diff = abs(d[dof] - e[dof])
            if diff > worstD:
                worstD, worstD_key, worstD_dof = diff, nid, dof

    # --- Reacciones ---
    def suma_reac(d):
        return {"sum_Rx": fsum(d[cn]["reactions"]["sum_Rx"]
                               for cn in d),
                "sum_Ry": fsum(d[cn]["reactions"]["sum_Ry"]
                               for cn in d),
                "sum_Rz": fsum(d[cn]["reactions"]["sum_Rz"]
                               for cn in d)}
    reac_sum = {}
    for comp in ("sum_Rx", "sum_Ry", "sum_Rz"):
        reac_sum[comp] = fsum(casos[cn]["reactions"][comp] for cn in casos)
    reac_err = max(abs(reac_sum[c] - explicit["reactions"][c])
                   for c in ("sum_Rx", "sum_Ry", "sum_Rz"))

    # per-node reactions
    worstR = 0.0; worstR_key = None
    nodesR = set()
    for cn in casos:
        nodesR.update(casos[cn]["reactions"]["per_node"].keys())
    for n in nodesR:
        vals = [fsum(casos[cn]["reactions"]["per_node"].get(n, [0]*6)[i]
                     for cn in casos) for i in range(6)]
        e = explicit["reactions"]["per_node"].get(n, [0]*6)
        for i in range(6):
            diff = abs(vals[i] - e[i])
            if diff > worstR:
                worstR, worstR_key = diff, n

    # --- Fuerzas internas ---
    forces_sum = combinados_suma(casos, LAMBDAS, "forces")
    worstF = 0.0; worstF_key = None; worstF_i = None
    for t, vals in forces_sum.items():
        e = explicit["element_forces"].get(t)
        if not e:
            continue
        for i in range(len(vals)):
            diff = abs(vals[i] - e[i])
            if diff > worstF:
                worstF, worstF_key, worstF_i = diff, t, i

    print("=" * 70)
    print("P A R T E   C   -   V E R I F I C A C I O N   D E   "
          "S U P E R P O S I C I O N")
    print("=" * 70)
    print(f"Factores: {LAMBDAS}")
    print(f"  Desplazamiento: max error  = {worstD:.3e} m "
          f"(nodo {worstD_key}, dof {worstD_dof})")
    print(f"  Reaccion (suma): max error = {reac_err:.3e} kN")
    print(f"  Reaccion (por nodo): error = {worstR:.3e} kN "
          f"(nodo {worstR_key})")
    print(f"  Fuerzas internas: max error= {worstF:.3e} kN "
          f"(elem {worstF_key}, comp {worstF_i})")

    scale = max(abs(worstD), abs(reac_err), abs(worstR), abs(worstF))
    super_OK = scale < 1e-6
    print("-" * 70)
    print(f"  Max error global            = {scale:.3e}")
    print(f"  SUPERPOSICION LINEAL VALIDA = {super_OK}  "
          f"(err < 1e-6)")

    report = {
        "lambdas": LAMBDAS,
        "max_err_desplazamiento_m": worstD,
        "worst_node_disp": worstD_key,
        "max_err_reaccion_suma_kN": reac_err,
        "max_err_reaccion_nodo_kN": worstR,
        "max_err_fuerzas_kN": worstF,
        "max_err_global": scale,
        "superposicion_valida": super_OK,
        "convergio_explicito": explicit["convergio"],
        "reacciones_suma": reac_sum,
        "reacciones_explicitas": explicit["reactions"],
    }
    with open(os.path.join(OUT_DIR, "part_c_superposicion.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nResultados guardados en {OUT_DIR}\\part_c_superposicion.json")
    return report


if __name__ == "__main__":
    main()
