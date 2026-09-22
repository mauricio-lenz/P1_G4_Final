# ============================================================
# PARTE B - SISMO PSEUDOESTATICO EX / EY (Semana 3)
# ============================================================
# Construye casos independientes EX y EY. El sismo se modela como
# fuerza lateral en el centro de masa de cada piso, proporcional a la
# masa (peso proprio + 50% carga viva) por el porcentaje de g:
#       F_i = C * W_i ,  W_i = (D_i + 0.5 Q_i) * A_i
# con C = 20% g (ejemplo Nch433).
#
# Verificaciones:
#   - carga lateral total por piso
#   - corte basal (suma de reacciones horizontales = total lateral)
#   - sentido de la deformada (desplazamientos en la direccion del sismo,
#     crecientes hacia arriba)
#   - torsion de piso (rotacion rz del diafragma)
#
# Unidades: kN y metros.
# ============================================================
import json, os

from base_cases import (build, floor_masses, run_case, build_model, C_G,
                        MASA_VIVA_FRACCION, C_G_PCT, D_BY_LEVEL, Q_BY_LEVEL)
from structural_model import PISO_LEVELS

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")
DIR_DOF = {"EX": 0, "EY": 1}
DIR_LABEL = {"EX": "X", "EY": "Y"}


def floor_summary(masas, F, structure):
    """Resumen por piso: masa (peso), fuerza lateral, centro de masa."""
    out = []
    for level in PISO_LEVELS:
        df = structure["diafragmas"].get(level)
        cx = cy = z = 0.0
        if df:
            cx, cy, z = structure["centroids"][level]
        out.append({
            "nivel": level,
            "W_kN": masas[level],
            "F_kN": F[level],
            "centro_masa": [cx, cy, z],
        })
    return out


def verificacion(case, res, F, structure, geom_area):
    dof = DIR_DOF[case]
    direccion = DIR_LABEL[case]

    # 1) carga lateral total
    F_total = sum(F.values())

    # 2) corte basal = reacciones horizontales (magnitud)
    bas = res["reactions"]
    corte_basal = abs(bas["sum_Rx"]) if dof == 0 else abs(bas["sum_Ry"])

    # 3) sentido de la deformada: promedio de desplazamiento por piso
    disp_por_piso = {}
    for nid, d in res["displacements"].items():
        lv = _level_of_node(structure, nid)
        if lv is None:
            continue
        u = d["ux"] if dof == 0 else d["uy"]
        disp_por_piso.setdefault(lv, []).append(u)
    prom_piso = {lv: sum(v) / len(v) for lv, v in disp_por_piso.items()}

    # 4) torsion de piso
    torsion = res["floor_twist"]

    check = {
        "caso": case,
        "direccion": direccion,
        "c_total_kN": F_total,
        "corte_basal_kN": corte_basal,
        "error_corte_kN": abs(corte_basal - F_total),
        "sentido_deformada_OK": all(
            (v >= -1e-9 if dof == 0 else v >= -1e-9) for v in prom_piso.values()),
        "desplaz_piso": {lv: round(prom_piso[lv], 6) for lv in prom_piso},
        "max_desplaz_m": max(prom_piso.values()) if prom_piso else 0.0,
        "torsion_rz": {lv: round(t["rz"], 6) for lv, t in torsion.items()},
        "resumen_pisos": floor_summary({lv: F[lv] / C_G for lv in F},
                                       F, structure),
    }
    return check


def _level_of_node(structure, nid):
    nm = structure["node_map"]
    n = nm.get(nid)
    return n.get("level") if n else None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    geometry, structure, beam_data = build()

    masas, areas, F = floor_masses(structure, geometry)

    print("=" * 70)
    print(f"PARTE B - SISMO PSEUDOESTATICO (C = {C_G_PCT*100:.0f}% g, "
          f"masa = D + {MASA_VIVA_FRACCION*100:.0f}% Q)")
    print("=" * 70)
    print("Fuerza lateral por piso  [F_i = C * (D+0.5Q)*A]:")
    for lv in PISO_LEVELS:
        print(f"  {lv}: A={areas[lv]:.2f} m2 | W(D+0.5Q)={masas[lv]:.2f} kN | "
              f"F={F[lv]:.3f} kN")

    results = {}
    checks = {}
    for case in ("EX", "EY"):
        res = run_case(geometry, structure, beam_data, case, 1.0)
        results[case] = res
        check = verificacion(case, res, F, structure, areas)
        checks[case] = check
        print("-" * 70)
        c = check
        print(f"[{case}] Direccion {c['direccion']}")
        print(f"  Carga lateral total F      = {c['c_total_kN']:.3f} kN")
        print(f"  Corte basal (reacciones)   = {c['corte_basal_kN']:.3f} kN")
        print(f"  Error |F - corte basal|    = {c['error_corte_kN']:.3e} kN")
        print(f"  Sentido deformada OK       = {c['sentido_deformada_OK']}")
        max_floor = max(c["desplaz_piso"], key=lambda k: abs(c["desplaz_piso"][k]))
        print(f"  Desplazamiento max (cima)  = {c['desplaz_piso'][max_floor]:.6f} m "
              f"en {max_floor}")
        print(f"  Torsion de piso rz (rad):")
        for lv, rz in c["torsion_rz"].items():
            print(f"      {lv}: rz={rz:.6e}")

    with open(os.path.join(OUT_DIR, "part_b_sismo.json"), "w",
              encoding="utf-8") as f:
        json.dump({"C_g": C_G, "masa_viva_frac": MASA_VIVA_FRACCION,
                   "F_por_piso": F, "masas_por_piso": masas,
                   "checks": checks}, f, indent=2, ensure_ascii=False)
    print(f"\nResultados guardados en {OUT_DIR}\\part_b_sismo.json")
    return checks, F, masas


if __name__ == "__main__":
    main()
