# ============================================================
# PARTE A - CARGA VIVA (Semana 3)
# ============================================================
# Usa la MISMA geometria tributaria de Semana 2 (metodo b/a) para
# repartir la carga viva q_Q sobre las vigas y verifica conservacion:
#       sum(Q transferida a vigas) = q_Q * A_losa
# para cada piso y globalmente.
#
# Unidades: kN y metros.
# ============================================================
import json, os

from materials import PP_LOSA_KNM2, PM_ADIC_INF, SC_INF, PM_ADIC_CUB, SC_CUB, \
    KGM2_TO_KNM2, G
from structural_model import load_geometry, assemble, PISO_LEVELS
from base_cases import (Q_BY_LEVEL, D_BY_LEVEL, tributary_areas_geometry,
                        build, floor_masses)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")


def conservacion_caso(geometry, structure, beam_data, qmap):
    """Verifica sum(Q_beam) = q_Q * A_losa por nivel y total."""
    # area total de losa por nivel
    A_losa = {}
    for slab in geometry["slabs"]:
        if slab["x1"] is None:
            continue
        lv = slab["level"]
        if lv not in qmap:
            continue
        A_losa[lv] = A_losa.get(lv, 0.0) + \
            abs(slab["x2"] - slab["x1"]) * abs(slab["y2"] - slab["y1"])

    # carga viva transferida a cada viga
    Q_beam = {}
    for tag, d in beam_data.items():
        q = qmap.get(d["piso"], 0.0)
        Q_beam[tag] = {"q": q, "area": d["area"],
                       "Q": q * d["area"], "piso": d["piso"]}

    total_Q_beam = sum(v["Q"] for v in Q_beam.values())
    total_area = sum(A_losa.values())
    total_expected = sum(qmap.get(lv, 0.0) * A_losa.get(lv, 0.0)
                         for lv in qmap)

    por_nivel = {}
    for lv in PISO_LEVELS:
        if lv not in qmap:
            continue
        q = qmap[lv]
        A = A_losa.get(lv, 0.0)
        Q_lv = sum(v["Q"] for v in Q_beam.values() if v["piso"] == lv)
        esperado = q * A
        por_nivel[lv] = {
            "q_Q_kNm2": q,
            "A_losa_m2": A,
            "Q_transferida_kN": Q_lv,
            "Q_esperada_kN": esperado,
            "error_kN": abs(Q_lv - esperado),
            "error_rel": (abs(Q_lv - esperado) / esperado * 100.0
                          if esperado else 0.0),
        }

    return {
        "total": {
            "Q_transferida_kN": total_Q_beam,
            "Q_esperada_kN": total_expected,
            "A_total_m2": total_area,
            "error_kN": abs(total_Q_beam - total_expected),
            "error_rel_pct": (abs(total_Q_beam - total_expected) /
                              total_expected * 100.0 if total_expected else 0.0),
        },
        "por_nivel": por_nivel,
        "n_vigas_con_carga": sum(1 for v in Q_beam.values() if v["Q"] > 0),
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    geometry = load_geometry()
    structure = assemble(geometry)
    beam_data = tributary_areas_geometry(geometry, structure)

    # conservacion de la carga viva (q_Q)
    qmap = Q_BY_LEVEL
    cons = conservacion_caso(geometry, structure, beam_data, qmap)
    cons["tipo_caso"] = "Q (carga viva)"
    cons["intensidades_knm2"] = dict(Q_BY_LEVEL)

    print("=" * 70)
    print("PARTE A - CARGA VIVA q_Q (misma geometria tributaria Semana 2)")
    print("=" * 70)
    for lv in PISO_LEVELS:
        if lv not in cons["por_nivel"]:
            continue
        c = cons["por_nivel"][lv]
        print(f"  {lv}: q_Q={c['q_Q_kNm2']:.4f} kN/m2 | A={c['A_losa_m2']:.2f} m2 | "
              f"Q_transf={c['Q_transferida_kN']:.3f} | Q_esp={c['Q_esperada_kN']:.3f} | "
              f"err={c['error_kN']:.2e} ({c['error_rel']:.4f}%)")
    t = cons["total"]
    print("-" * 70)
    print(f"TOTAL: Q_transferida={t['Q_transferida_kN']:.3f} kN | "
          f"Q_esperada={t['Q_esperada_kN']:.3f} kN | A={t['A_total_m2']:.2f} m2 | "
          f"error={t['error_kN']:.2e} kN ({t['error_rel_pct']:.5f}%)")
    print(f"Vigas con carga viva: {cons['n_vigas_con_carga']}")

    # guardar
    with open(os.path.join(OUT_DIR, "part_a_carga_viva.json"), "w",
              encoding="utf-8") as f:
        json.dump(cons, f, indent=2, ensure_ascii=False)
    print(f"\nResultados guardados en {OUT_DIR}\\part_a_carga_viva.json")

    # Tabla resumen para el informe
    tabla = []
    for lv in PISO_LEVELS:
        if lv in cons["por_nivel"]:
            c = cons["por_nivel"][lv]
            tabla.append([lv, c["q_Q_kNm2"], c["A_losa_m2"],
                          c["Q_transferida_kN"], c["Q_esperada_kN"],
                          c["error_kN"]])
    return cons, tabla


if __name__ == "__main__":
    main()
