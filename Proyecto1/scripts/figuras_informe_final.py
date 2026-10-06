#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figuras y cifras del informe final (reports/final.md) desde los resultados vigentes.

Lee el JSON de Unity (Assets/Resources/estructura_p1l4_unity.json, generado por
exportar_resultados_unity.py) y vuelve a correr en OpenSees lo que ese JSON no guarda
(modal, derivas por piso, M-phi). Ademas corre el exportador con las combinaciones de
diseno NCh3171 (data/combinaciones_nch3171.json) en una carpeta temporal, para la
verificacion de sensibilidad de la seccion 12. No modifica datos del proyecto.

Salida: reports/img/final/*.png y reports/img/final/cifras_informe_final.json

Uso:
  python -X utf8 Proyecto1/scripts/figuras_informe_final.py
"""
import json
import math
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
import capacidad_ha as cha  # noqa: E402
import carga_viva_sismo as cvm  # noqa: E402

REPO = BASE_DIR.parents[1]
UNITY_JSON = BASE_DIR.parent / "edificio_G4" / "Assets" / "Resources" / "estructura_p1l4_unity.json"
COMBOS_NCH3171 = BASE_DIR.parent / "data" / "combinaciones_nch3171.json"
OUT = REPO / "reports" / "img" / "final"

# paleta categorica validada (dataviz, modo claro): azul, naranjo, aqua; texto y grilla neutros
AZUL, NARANJO, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, GRILLA, NEUTRO = "#0b0b0b", "#52514e", "#e4e3df", "#8f8e88"
plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9, "axes.edgecolor": NEUTRO,
    "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.titlesize": 10,
    "axes.titleweight": "bold", "axes.titlecolor": TINTA, "axes.grid": True, "grid.color": GRILLA,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "figure.dpi": 100, "savefig.dpi": 200, "savefig.bbox": "tight", "lines.linewidth": 2.0,
})


def guardar(fig, nombre):
    fig.savefig(OUT / nombre, facecolor="white")
    plt.close(fig)
    print("  ", nombre)


def m_capacidad_muro(puntos, p):
    return cha.m_capacidad(puntos, p)


# ----------------------------------------------------------------------------------------------
def modelo_vigente():
    params = cvm.load_analysis_params()
    data = cvm.load_json(cvm.JSON_PATH)
    cvm.apply_model_params(data, params.get("q_G_kN_m2"), params.get("sections"), params.get("rigidezFisurada"))
    live = cvm.transfer_live_load(data, cvm.kg_m2_to_kn_m2(float(params["Q_kg_m2"])))
    seis = cvm.build_seismic_cases(data, live, cvm.seismic_setting(params))
    return params, data, live, seis


def modal(data, live, fraccion_q):
    out = {}
    for b in ("edificio_1", "edificio_2"):
        r = cvm.modal_periods(cvm.building_subset(data, b), live, fraccion_q, n_modes=12)
        out[b] = {"modos": [{"modo": k, "T_s": round(t, 4), "UX": round(ux, 3), "UY": round(uy, 3)} for k, t, ux, uy in r["modos"][:6]],
                  "suma_UX_12": round(sum(m[2] for m in r["modos"]), 3), "suma_UY_12": round(sum(m[3] for m in r["modos"]), 3)}
    return out


def derivas(data, seis):
    """Deriva de entrepiso en el nodo maestro de cada diafragma (NCh433 5.9.2) y mayor exceso de
    la deriva de una columna o muro sobre la del centro de masa del mismo piso (5.9.3)."""
    nodes = cvm.node_map(data)
    dg = cvm.diaphragm_groups(data)
    own = cvm.node_buildings(data)
    res = {c: cvm.run_and_extract(data, cvm.vector_loads_from_dict(seis["cargas_nodales_" + c])) for c in ("EX", "EY")}
    out = {"cm": {}, "exceso_punto": {}}
    for c, comp in (("EX", "ux"), ("EY", "uy")):
        disp = res[c]["displacements"]
        u = lambda n: (disp.get(n) or disp.get(str(n)))[comp]
        for b in ("edificio_1", "edificio_2"):
            base = min(nodes[s["node"]]["z"] for s in data["supports"] if own.get(s["node"]) == b)
            prev_u, prev_z, filas = 0.0, base, []
            for k in sorted(k for k in dg if k[0] == b):
                uk = u(dg[k]["master"])
                filas.append({"z": k[1], "u_mm": round(uk * 1000, 2), "deriva_por_mil": round(1000 * abs(uk - prev_u) / (k[1] - prev_z), 3)})
                prev_u, prev_z = uk, k[1]
            out["cm"][f"{b}_{c}"] = filas
        peor = (0.0, None)
        for e in cvm.structural_elements(data):
            if e.get("type") not in ("columna", "muro"):
                continue
            a, b_ = nodes[e["nodeI"]], nodes[e["nodeJ"]]
            lo, hi = (a, b_) if a["z"] < b_["z"] else (b_, a)
            h = hi["z"] - lo["z"]
            bld = e.get("sourceBuilding") or "edificio_1"
            kt, kb = (bld, round(hi["z"], 3)), (bld, round(lo["z"], 3))
            if h < 1.0 or kt not in dg:
                continue
            d_cm = abs(u(dg[kt]["master"]) - (u(dg[kb]["master"]) if kb in dg else 0.0)) / h
            d_p = abs(u(hi["id"]) - u(lo["id"])) / h
            if d_p - d_cm > peor[0]:
                peor = (d_p - d_cm, {"elemento": e["elementTag"], "edificio": bld, "z": hi["z"],
                                     "deriva_punto_por_mil": round(1000 * d_p, 3), "deriva_cm_por_mil": round(1000 * d_cm, 3)})
        out["exceso_punto"][c] = dict(peor[1] or {}, exceso_por_mil=round(1000 * peor[0], 3))
    return out


def resumen_dcr(U):
    """Conteos de demanda/capacidad de vigas, columnas y muros de un JSON de resultados."""
    import qa_semana06 as qa
    els = [e for e in U["elements"] if e.get("capacidad")]
    out = {}
    for t in ("viga", "columna"):
        d = [(e["capacidad"]["DCR"], e["elementTag"], e["capacidad"].get("comboGobernante"), bool(e["capacidad"].get("fuenteArmadura"))) for e in els if e["type"] == t]
        d.sort(reverse=True)
        out[t] = {"n": len(d), "DCR_mayor_1": sum(x[0] > 1 for x in d), "DCR_mayor_1_planos": sum(x[0] > 1 and x[3] for x in d),
                  "DCR_max": d[0][0], "peor": d[0][1], "combo_peor": d[0][2], "top5": [[x[1], x[0], x[2]] for x in d[:5]],
                  "gobierna_en_fallas": Counter(x[2] for x in d if x[0] > 1).most_common(), "valores": [x[0] for x in d]}
    curvas = {c["sectionId"]: c for c in U["p1l4"]["pmCurves"]}
    reg = {r["index"]: r for r in U["p1l4"]["wallRegistry"]}
    filas = []
    for w in U["walls"]:
        c = curvas[reg[w["id"]]["pmSectionId"]]
        peor = max(((d["M_kN_m"] / qa.wall_capacity_at(c["points"], d["P_kN"]) if qa.wall_capacity_at(c["points"], d["P_kN"]) > 0 else 99.0),
                    d["combo"], d["P_kN"], d["M_kN_m"]) for d in w["demands"])
        filas.append((round(peor[0], 3), w["elementTag"], reg[w["id"]]["pmSectionId"], peor[1], round(peor[2], 1), round(peor[3], 1)))
    filas.sort(reverse=True)
    out["muro"] = {"n": len(filas), "C_mayor_1": sum(f[0] > 1 for f in filas), "fuera_de_curva": sum(f[0] >= 99 for f in filas),
                   "C_max": filas[0][0], "top5": [list(f) for f in filas[:5]], "valores": [f[0] for f in filas]}
    return out


# ----------------------------------------------------------------------------------------------
def fig_modelo_3d(data):
    """Vista isometrica del modelo OpenSees: vigas, columnas/pilares, arriostres y muros (columna ancha)."""
    from mpl_toolkits.mplot3d.art3d import Line3DCollection
    nodes = cvm.node_map(data)
    estilos = {"viga": (NEUTRO, 0.7, "Vigas"), "columna": (AZUL, 1.4, "Columnas y pilares"),
               "arriostre": (AQUA, 1.4, "Arriostres"), "muro": (NARANJO, 3.2, "Muros (columna ancha)")}
    fig = plt.figure(figsize=(8.0, 3.9))
    ax = fig.add_subplot(projection="3d")
    fig.subplots_adjust(left=0, right=1, top=1.08, bottom=0.08)
    for tipo, (color, ancho, etiqueta) in estilos.items():
        segs = []
        for e in data["elements"]:
            if e.get("type") != tipo:
                continue
            a, b = nodes[e["nodeI"]], nodes[e["nodeJ"]]
            segs.append([(a["x"], a["y"], a["z"]), (b["x"], b["y"], b["z"])])
        ax.add_collection3d(Line3DCollection(segs, colors=color, linewidths=ancho, label=f"{etiqueta} ({len(segs)})"))
    xs = [n["x"] for n in data["nodes"]]
    ys = [n["y"] for n in data["nodes"]]
    zs = [n["z"] for n in data["nodes"]]
    ax.set_xlim(min(xs), max(xs))
    ax.set_ylim(min(ys), max(ys))
    ax.set_zlim(min(zs), max(zs))
    ax.set_box_aspect((max(xs) - min(xs), (max(ys) - min(ys)) * 1.25, (max(zs) - min(zs)) * 1.25), zoom=1.0)
    ax.view_init(elev=22, azim=-58)
    ax.set_xlabel("x [m]  (edificio 2: x < −10 · edificio 1: x > −10)", labelpad=8, fontsize=7.5)
    ax.set_ylabel("y [m]", labelpad=2, fontsize=7.5)
    ax.set_zlabel("z [m]", labelpad=-2, fontsize=7.5)
    ax.tick_params(labelsize=6.5, pad=0)
    fig.legend(*ax.get_legend_handles_labels(), loc="lower center", ncol=4, fontsize=7.5, bbox_to_anchor=(0.5, 0.02))
    guardar(fig, "modelo_3d.png")


def fig_fuerzas_piso(seis):
    pisos = seis["pisos"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    for ax, b, titulo in zip(axs, ("edificio_1", "edificio_2"), ("Edificio 1 (2017_67)", "Edificio 2 (2024_22)")):
        filas = [r for r in pisos if r["edificio"] == b]
        z = [r["floor_z_m"] for r in filas]
        ax.barh([v + 0.55 for v in z], [r["F_EX_kN"] for r in filas], height=1.0, color=AZUL, label="EX")
        ax.barh([v - 0.55 for v in z], [r["F_EY_kN"] for r in filas], height=1.0, color=NARANJO, label="EY")
        for r in filas:
            ax.text(max(r["F_EX_kN"], r["F_EY_kN"]) + 40, r["floor_z_m"], f'{r["F_EX_kN"]:.0f} / {r["F_EY_kN"]:.0f}', va="center", fontsize=7.5, color=TINTA2)
        ax.set_title(titulo)
        ax.set_xlabel("Fuerza sísmica del piso [kN]")
        ax.set_xlim(0, max(max(r["F_EX_kN"], r["F_EY_kN"]) for r in filas) * 1.35)
        ax.grid(axis="y", visible=False)
    axs[0].set_yticks(sorted({r["floor_z_m"] for r in pisos}))
    axs[0].set_ylabel("z del diafragma [m]")
    axs[0].legend(loc="lower right")
    guardar(fig, "fuerzas_sismicas_piso.png")


def fig_derivas(der):
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True, sharex=True)
    for ax, b, titulo in zip(axs, ("edificio_1", "edificio_2"), ("Edificio 1", "Edificio 2")):
        for c, color, est in (("EX", AZUL, "-"), ("EY", NARANJO, "--")):
            filas = der["cm"][f"{b}_{c}"]
            ax.plot([f["deriva_por_mil"] for f in filas], [f["z"] for f in filas], est, color=color, marker="o", markersize=4, label=c)
        ax.axvline(2.0, color=NEUTRO, linewidth=1.2, linestyle=":")
        ax.text(1.96, 1.0, "límite NCh433 2 ‰", ha="right", rotation=90, fontsize=7.5, color=TINTA2)
        ax.set_title(titulo)
        ax.set_xlabel("Deriva de entrepiso en el centro de masa [‰]")
    axs[0].set_ylabel("z del diafragma [m]")
    axs[0].set_xlim(0, 2.2)
    axs[0].legend(loc="center right")
    guardar(fig, "derivas_cm.png")


def fig_mphi(params):
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    datos = {}
    for n, color, est in ((10, AQUA, ":"), (20, AZUL, "-"), (40, NARANJO, "--")):
        curv, m = cvm._fiber_moment_curvature(0.0, n, 0.12, 300)
        datos[n] = round(max(m), 1)
        ax.plot([1000 * c for c in curv], m, est, color=color, label=f"{n}×{n} fibras · Mmax {max(m):.0f} kN·m")
    ax.set_xlabel("Curvatura φ [10⁻³ 1/m]")
    ax.set_ylabel("Momento M [kN·m]")
    ax.set_title("M-φ de la COL70/70 (8φ25, G35) con P = 0")
    ax.legend(loc="lower right")
    guardar(fig, "mphi_col70.png")
    return datos


def fig_pm_columna(U):
    curvas = {c["sectionId"]: c for c in U["p1l4"]["pmCurves"]}
    dis = sorted(curvas["COL70/70_8f25"]["points"], key=lambda q: q["P_kN"])
    fib = sorted(curvas["COL70/70_FIBER"]["points"], key=lambda q: q["P_kN"])
    nom = cha.curva_pm_columna(700, 700, 8, 25, 0.04, 12)
    nomp = sorted(nom["puntos"], key=lambda q: q["Pn_kN"])
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    ax.plot([q["Mn_kN_m"] for q in nomp], [q["Pn_kN"] for q in nomp], "--", color=NARANJO, label="Nominal (Pn, Mn) ACI 318-19")
    ax.plot([q["M_kN_m"] for q in dis], [q["P_kN"] for q in dis], "-", color=AZUL, label="Diseño (φPn, φMn) ACI 318-19")
    ax.plot([abs(q["M_kN_m"]) for q in fib], [q["P_kN"] for q in fib], ":", color=AQUA, label="Sección de fibras (OpenSees)")
    pts = [(r["Mu"], r["Pu"]) for e in U["elements"] if e["type"] == "columna" and e.get("capacidad") and e["sectionId"] == "COL70/70"
           for r in e["capacidad"]["porCombo"] if "Pu" in r]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=9, color=NEUTRO, alpha=0.55, linewidths=0, label=f"Demandas C1–C3 ({len(pts)})")
    peor = max((e for e in U["elements"] if e["type"] == "columna" and e.get("capacidad")), key=lambda e: e["capacidad"]["DCR"])
    r = max(peor["capacidad"]["porCombo"], key=lambda r: r.get("DCR_PM", 0))
    ax.scatter([r["Mu"]], [r["Pu"]], s=40, color=TINTA, edgecolor="white", linewidth=1.5, zorder=5)
    ax.annotate(f'{peor["elementTag"]} ({r["combo"]}): DCR {peor["capacidad"]["DCR"]:.2f}', (r["Mu"], r["Pu"]), xytext=(12, -14),
                textcoords="offset points", fontsize=8, color=TINTA)
    ax.set_xlabel("M [kN·m]")
    ax.set_ylabel("P [kN] (compresión +)")
    ax.set_title("P-M de la COL70/70 con 8φ25 (armadura tipo supuesta)")
    ax.legend(loc="upper right", fontsize=7.5)
    guardar(fig, "pm_columna.png")
    return {"P0_kN": round(nom["P0_kN"], 1), "phiPmax_kN": round(nom["phiPmax_kN"], 1),
            "phiMn_P0_kN_m": round(cha.m_capacidad(dis, 0.0), 1), "Mn_fibras_P0_kN_m": round(cha.m_capacidad([dict(q, M_kN_m=abs(q["M_kN_m"])) for q in fib], 0.0), 1)}


def fig_pm_muros(U, tags=("MURO-020", "MURO-056")):
    curvas = {c["sectionId"]: c for c in U["p1l4"]["pmCurves"]}
    reg = {r["index"]: r for r in U["p1l4"]["wallRegistry"]}
    fig, axs = plt.subplots(1, len(tags), figsize=(7.4, 3.6))
    info = {}
    for ax, tag in zip(axs, tags):
        w = next(x for x in U["walls"] if x["elementTag"] == tag)
        c = curvas[reg[w["id"]]["pmSectionId"]]
        pts = sorted(c["points"], key=lambda q: q["P_kN"])
        ax.plot([q["M_kN_m"] for q in pts], [q["P_kN"] for q in pts], "-", color=AZUL, label="Diseño (φPn, φMn)")
        ax.scatter([abs(d["M_kN_m"]) for d in w["demands"]], [d["P_kN"] for d in w["demands"]], s=30, color=NARANJO,
                   edgecolor="white", linewidth=1.2, zorder=5, label="Demandas C1–C3")
        armado = (c.get("armado") or "").replace(" + bordes ", "\nbordes ")
        ax.set_title(f'{tag}: t {c["b_m"]:.2f} m × L {c["h_m"]:.2f} m\n\n', fontsize=9)
        ax.text(0.5, 1.0, armado, transform=ax.transAxes, ha="center", va="bottom", fontsize=7, color=TINTA2)
        ax.set_xlabel("M en el plano [kN·m]")
        info[tag] = {"curva": c["sectionId"], "armado": c.get("armado"), "rho_percent": c["rho_percent"]}
    axs[0].set_ylabel("P [kN] (compresión +)")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, fontsize=7.5, bbox_to_anchor=(0.5, -0.06))
    guardar(fig, "pm_muros.png")
    return info


def fig_viga_E1_62(U, data):
    """Perfil de capacidad phiMn+ / -phiMn- de las barras de los planos y momento Mu(t) de C1-C3."""
    e = next(x for x in U["elements"] if x["elementTag"] == "E1_62")
    nodes = cvm.node_map(data)
    el_m = next(x for x in data["elements"] if x["id"] == e["id"])
    L = cvm.element_length(el_m, nodes)
    combos = cvm.load_combinations()
    fuerzas = {r["combo"]: r["f"] for r in U["p1l4"]["elementForces"] if r["id"] == e["id"]}
    cap = e["capacidad"]
    per = cap["perfil"]
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    for t0, t1 in cap["carasApoyo"]:
        ax.axvspan(t0 * L, t1 * L, color=GRILLA, alpha=0.8, linewidth=0)
        ax.text((t0 + t1) / 2 * L, 0, "columna", rotation=90, ha="center", va="center", fontsize=7, color=TINTA2)
    ts = [p["t"] * L for p in per]
    ax.step(ts, [p["phiMn_pos"] for p in per], where="mid", color=AZUL, label="φMn+ (barras inferiores del plano)")
    ax.step(ts, [-p["phiMn_neg"] for p in per], where="mid", color=AZUL, linestyle="--", label="−φMn− (barras superiores)")
    mx_pos = 0.0
    for k, (nombre, lam) in enumerate(combos.items()):
        f = fuerzas[nombre]
        w = cvm.gravity_w(el_m, nodes, lam)
        xs = [L * i / 100 for i in range(101)]
        m = [-(-(1 - x / L) * f[4] + (x / L) * f[10] - w * L * L * (x / L) * (1 - x / L) / 2.0) for x in xs]
        mx_pos = max(mx_pos, max(m))
        ax.plot(xs, m, color=NARANJO, linewidth=1.4, alpha=0.95 if k == 0 else 0.55, label="Mu(x) C1–C3 (+ tracciona abajo)" if k == 0 else None)
    ax.axhline(0, color=NEUTRO, linewidth=0.8)
    ax.set_xlabel("x desde el nodo I [m]")
    ax.set_ylabel("M [kN·m]")
    ax.set_title(f'E1_62 (V60/80, eje 2, CIELO_2): DCR {cap["DCR"]:.2f}', fontsize=9.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3, fontsize=7.2)
    guardar(fig, "viga_E1_62.png")
    return {"L_m": round(L, 3), "Mu_pos_max_reconstruido": round(mx_pos, 2), "Mu_pos_exportado": max(r["Mu_pos"] for r in cap["porCombo"])}


def fig_dcr(curso, nch):
    fig, axs = plt.subplots(1, 3, figsize=(7.6, 2.8))
    for ax, clave, titulo in zip(axs, ("viga", "columna", "muro"), ("Vigas (DCR)", "Columnas (DCR)", "Muros (C = Mu/φMn)")):
        bins = [i * 0.1 for i in range(0, 21)]
        recorte = lambda v: [min(x, 1.999) for x in v]
        ax.hist(recorte(curso[clave]["valores"]), bins=bins, histtype="step", linewidth=2, color=AZUL, label="C1–C3 (curso)")
        ax.hist(recorte(nch[clave]["valores"]), bins=bins, histtype="step", linewidth=2, linestyle="--", color=NARANJO, label="NCh3171 U1–U10")
        ax.axvline(1.0, color=TINTA2, linewidth=1, linestyle=":")
        ax.set_title(titulo, fontsize=9)
    fig.supxlabel("demanda / capacidad (los valores ≥ 2 se acumulan en la última barra)", fontsize=8.5, color=TINTA2, y=-0.04)
    axs[0].set_ylabel("elementos")
    axs[0].legend(loc="upper right", fontsize=7)
    guardar(fig, "dcr_histogramas.png")


# ----------------------------------------------------------------------------------------------
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    U = json.loads(UNITY_JSON.read_text(encoding="utf-8"))
    params, data, live, seis = modelo_vigente()
    print("Figuras ->", OUT)
    cifras = {"corrida_unity": U.get("corrida"), "resumenAnalisis": {k: v for k, v in U["resumenAnalisis"].items() if k != "secciones"}}
    cifras["sismo_pisos"] = [{k: r[k] for k in ("piso", "edificio", "floor_z_m", "D_kN", "Q_kN", "W_sismico_kN", "A_k", "F_EX_kN", "F_EY_kN")} for r in seis["pisos"]]
    cifras["Q"] = {k: live[k] for k in ("q_Q_kN_m2", "q_Q_cubierta_kN_m2", "area_total_m2", "Q_transferida_kN", "q_Q_por_A_kN", "error_conservacion_kN")}
    cifras["modal"] = modal(data, live, seis["config"]["fraccionQ"])
    cifras["derivas"] = derivas(data, seis)
    fig_modelo_3d(data)
    fig_fuerzas_piso(seis)
    fig_derivas(cifras["derivas"])
    cifras["mphi_Mmax_P0"] = fig_mphi(params)
    cifras["pm_columna"] = fig_pm_columna(U)
    cifras["pm_muros"] = fig_pm_muros(U)
    cifras["viga_E1_62"] = fig_viga_E1_62(U, data)
    curso = resumen_dcr(U)
    with tempfile.TemporaryDirectory() as tmp:
        salida = Path(tmp) / "nch3171.json"
        r = subprocess.run([sys.executable, "-X", "utf8", str(BASE_DIR / "exportar_resultados_unity.py"), "--combos", str(COMBOS_NCH3171),
                            "--out", str(salida)], cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            raise SystemExit("exportador NCh3171 fallo:\n" + r.stdout[-2000:] + r.stderr[-2000:])
        nch = resumen_dcr(json.loads(salida.read_text(encoding="utf-8")))
    fig_dcr(curso, nch)
    quitar = lambda d: {k: {kk: vv for kk, vv in v.items() if kk != "valores"} for k, v in d.items()}
    cifras["dcr_curso"], cifras["dcr_nch3171"] = quitar(curso), quitar(nch)
    (OUT / "cifras_informe_final.json").write_text(json.dumps(cifras, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("   cifras_informe_final.json")


if __name__ == "__main__":
    main()
