# ============================================================
# GRAVITY ANALYSIS - Edificio de Ingenieria UANDES
# ============================================================
# Orquesta: ensamblar malla -> construir modelo OpenSees ->
# areas tributarias q_G (metodo b/a) -> aplicar cargas ->
# analizar -> verificaciones -> guardar resultados.
# Unidades: kN y metros.
# ============================================================
import os, json

import openseespy.opensees as ops

from materials import Q_G, Q_G_BY_LEVEL, CONCRETO_H30, TOL_CONSERVACION_KN
from sections import BEAM_SECTIONS
from structural_model import (load_geometry, assemble, build_model,
                              PISO_LEVELS, DEFAULT_REPART)
from tributary import compute_tributary_areas

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(PROJECT_DIR, "outputs", "resultados_gravedad.json")


# -----------------------------------------------------------------
# APLICAR CARGAS (distribuidas sobre vigas, en -Z)
# -----------------------------------------------------------------
def apply_slab_loads(structure, beam_data):
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for b in structure["beams"]:
        d = beam_data.get(b["tag"])
        if not d or d.get("largo", 0.0) <= 0 or d.get("area", 0.0) <= 0:
            continue
        w = d["carga"] / d["largo"]
        ops.eleLoad("-ele", b["tag"], "-type", "-beamUniform", 0.0, -w)


# -----------------------------------------------------------------
# ANALISIS
# -----------------------------------------------------------------
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
    except Exception as exc:
        ok = -2
    ops.reactions()
    return ok


# -----------------------------------------------------------------
# VERIFICACIONES
# -----------------------------------------------------------------
def verify(geometry, structure, beam_data, piso, norm):
    checks = {}

    # 1 y 2: conservacion de areas y carga por piso (sin factor)
    carga_piso = {}
    for level in PISO_LEVELS:
        ps = piso.get(level, {"area_losa": 0.0, "area_trib": 0.0,
                              "carga": 0.0})
        carga_piso[level] = ps["carga"]
        checks[level] = {
            "area_losa": ps["area_losa"],
            "area_tributaria": ps["area_trib"],
            "q_G_knm2": Q_G_BY_LEVEL[level],
            "carga_tributaria": ps["carga"],
            "carga_esperada": Q_G_BY_LEVEL[level] * ps["area_losa"],
            "err_area_m2": ps["err_area"],
            "err_carga_kn": abs(ps["carga"] - Q_G_BY_LEVEL[level] * ps["area_losa"]),
            "n_paneles": ps["n_paneles"],
            "n_paneles_excluidos": ps["n_excluidos"],
        }

    # 4: equilibrio global (todos los apoyos)
    rx = ry = rz = 0.0
    for node in [s["node"] for s in structure["supports"]]:
        r = ops.nodeReaction(node)
        rx += r[0]; ry += r[1]; rz += r[2]
    carga_total_edif = sum(carga_piso.values())
    checks["equilibrio_global"] = {
        "suma_Rx": rx, "suma_Ry": ry, "suma_Rz": rz,
        "carga_total": carga_total_edif,
        "error_Rz": abs(rz - carga_total_edif),
    }

    # 5: compatibilidad diafragma
    diaf = {}
    for level, df in structure["diafragmas"].items():
        uz = [ops.nodeDisp(n, 3) for n in df["slaves"]] or [0.0]
        diaf[level] = {"maestro": df["maestro"],
                       "n_esclavos": len(df["slaves"]),
                       "uz_min": min(uz), "uz_max": max(uz),
                       "delta_vertical": max(uz) - min(uz)}
    checks["compatibilidad_diafragma"] = diaf

    return checks, carga_piso


# -----------------------------------------------------------------
# RESUMEN
# -----------------------------------------------------------------
def summary(geometry, structure, checks, carga_piso):
    lines = []
    lines.append("=" * 70)
    lines.append("UANDES - ANALISIS DE GRAVEDAD (Semana 2)")
    lines.append("=" * 70)
    lines.append(f"Columnas: {len(structure['columns'])} | "
                 f"Vigas: {len(structure['beams'])} | "
                 f"Muros equiv: {len(structure['walls'])} | "
                 f"Apoyos: {len(structure['supports'])}")
    lines.append("")
    lines.append("Conservacion de areas y cargas por piso (metodo b/a):")
    for level in PISO_LEVELS:
        c = checks[level]
        lines.append(
            f"  {level}: Q_G={c['q_G_knm2']:.3f} kN/m2 | "
            f"A_losa={c['area_losa']:.2f} m2 | A_trib={c['area_tributaria']:.2f} m2 | "
            f"carga={c['carga_tributaria']:.2f} kN | "
            f"esperada={c['carga_esperada']:.2f} kN | "
            f"err_area={c['err_area_m2']:.5f} | err_carga={c['err_carga_kn']:.5f} | "
            f"paneles={c['n_paneles']} excl={c['n_paneles_excluidos']}")
    eg = checks["equilibrio_global"]
    lines.append("")
    lines.append(f"Equilibrio global: Rz={eg['suma_Rz']:.3f} vs carga "
                 f"{eg['carga_total']:.3f} (err={eg['error_Rz']:.4f})")
    lines.append(f"  Rx={eg['suma_Rx']:.4f}  Ry={eg['suma_Ry']:.4f}")
    for level, d in checks["compatibilidad_diafragma"].items():
        lines.append(f"  Diafragma {level}: {d['n_esclavos']} esclavos, "
                     f"delta_vertical={d['delta_vertical']:.2e}")
    return "\n".join(lines)


# -----------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------
def main():
    geometry = load_geometry()
    structure = assemble(geometry)
    build_model(structure, geometry)

    beam_data, piso = compute_tributary_areas(geometry, structure)
    norm = {}   # sin normalizacion (conservacion real)
    apply_slab_loads(structure, beam_data)

    ok = run_analysis()
    if ok != 0:
        print("!! El analisis NO convergio (codigo", ok, ")")
    else:
        print("Analisis estatico de gravedad: convergio OK")

    checks, carga_piso = verify(geometry, structure, beam_data, piso, norm)
    print(summary(geometry, structure, checks, carga_piso))

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "q_G_knm2": Q_G,
            "q_G_by_level_knm2": Q_G_BY_LEVEL,
            "statistics": {
                "columnas": len(structure["columns"]),
                "vigas": len(structure["beams"]),
                "muros_equiv": len(structure["walls"]),
                "apoyos": len(structure["supports"]),
            },
            "carga_por_piso": carga_piso,
            "checks": checks,
            "areas_por_viga": {
                k: {"area": v["area"], "carga": v["carga"],
                    "largo": v.get("largo", 0.0), "seccion": v.get("seccion", ""),
                    "piso": v["piso"]}
                for k, v in beam_data.items()
            },
        }, f, indent=2)
    print(f"\nResultados guardados en: {OUT_FILE}")

    from export_structural import export_extended, extract_forces
    structure["beam_data"] = beam_data
    forces = extract_forces(structure)
    ex = export_extended(structure, geometry, beam_data, forces=forces)
    print(f"Export Unity ampliado: {ex}")

    ops.wipe()
    return structure, beam_data, piso


if __name__ == "__main__":
    main()
