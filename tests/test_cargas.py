"""Cargas: areas tributarias, carga viva por nivel y sismo estatico NCh433."""
import collections

import pytest

from conftest import cvm

RES = 0.05   # m, grilla para el area de losa sin traslapes


def area_losas_por_edificio(data):
    """Area real de losa [m2] (union de paneles, sin traslapes) por edificio y nivel."""
    import numpy as np
    por = collections.defaultdict(list)
    for s in data["slabs"]:
        edificio = s.get("sourceBuilding") or ("edificio_2" if (s["x0"] + s["x1"]) / 2 < -10 else "edificio_1")
        por[(edificio, round(s["z"], 2))].append(s)
    out = {}
    for key, ss in por.items():
        x0, y0 = min(s["x0"] for s in ss), min(s["y0"] for s in ss)
        nx = int((max(s["x1"] for s in ss) - x0) / RES) + 2
        ny = int((max(s["y1"] for s in ss) - y0) / RES) + 2
        g = np.zeros((ny, nx), dtype=bool)
        for s in ss:
            g[int(round((s["y0"] - y0) / RES)):int(round((s["y1"] - y0) / RES)),
              int(round((s["x0"] - x0) / RES)):int(round((s["x1"] - x0) / RES))] = True
        out[key] = g.sum() * RES * RES
    return out


def test_area_tributaria_conserva_losa(modelo):
    """Suma de areas tributarias = area real de losa de cada edificio (paso 16 de ajustar_modelo_planos)."""
    data = modelo["data"]
    areas = area_losas_por_edificio(data)
    for edificio in ("edificio_1", "edificio_2"):
        losa = sum(a for (b, _z), a in areas.items() if b == edificio)
        trib = sum(float(e.get("areaTributaria") or 0) for e in data["elements"]
                   if cvm.lleva_losa(e) and (e.get("sourceBuilding") or "edificio_1") == edificio)
        assert abs(trib - losa) / losa < 0.01, f"{edificio}: tributaria {trib:.0f} m2 vs losa {losa:.0f} m2"


def test_carga_viva_por_nivel(modelo, params):
    """Q = 500 kg/m2 en pisos y Q_cubierta en el nivel superior de cada edificio; se conserva q*A."""
    live = modelo["live"]
    q_piso = cvm.kg_m2_to_kn_m2(float(params["Q_kg_m2"]))
    q_techo = cvm.kg_m2_to_kn_m2(float(params["Q_cubierta_kg_m2"]))
    techo = collections.defaultdict(float)
    for v in live["vigas"]:
        techo[v["sourceBuilding"] or "edificio_1"] = max(techo[v["sourceBuilding"] or "edificio_1"], v["floor_z_m"])
    total = 0.0
    for v in live["vigas"]:
        esperado = q_techo if abs(v["floor_z_m"] - techo[v["sourceBuilding"] or "edificio_1"]) < 0.05 else q_piso
        assert abs(v["q_Q_kN_m2"] - esperado) < 1e-12
        total += esperado * v["area_tributaria_m2"]
    aplicada = -sum(f[2] for f in modelo["loads"]["Q"].values())
    assert abs(aplicada - total) < 1e-6


def test_peso_sismico_nch433(modelo, params):
    """P de cada piso = D + fraccionQ * Q (NCh433 5.5.1)."""
    f = float(params["sismo"]["fraccionQ"])
    for row in modelo["seismic"]["pisos"]:
        assert abs(row["W_sismico_kN"] - (row["D_kN"] + f * row["Q_kN"])) < 1e-6


def test_coeficiente_nch433_a_mano(modelo, params):
    """C = 2.75 S A0/(g R) (T'/T*)^n acotado a [A0 S/6g, Cmax]; Q0 = C I P; sum F = Q0; sum Ak = 1."""
    cfg = cvm.seismic_setting(params)
    s, _t0, tp, n, _p = cvm.SUELOS_DS61[cfg["suelo"]]
    a0 = cvm.ZONAS_A0_G[cfg["zona"]]
    cmax = cvm.cmax_factor(cfg["R"]) * s * a0
    for b in modelo["seismic"]["edificios"]:
        pisos = [r for r in modelo["seismic"]["pisos"] if r["edificio"] == b["edificio"]]
        for d in ("X", "Y"):
            c = 2.75 * s * a0 / cfg["R"] * (tp / b[f"T_{d}_s"]) ** n
            c = max(a0 * s / 6.0, min(cmax, c))
            assert abs(b[f"C_{d}"] - c) < 1e-12
            assert abs(b[f"Q0_{d}_kN"] - c * cfg["I"] * b["P_kN"]) < 1e-6
            assert abs(sum(r[f"F_E{d}_kN"] for r in pisos) - b[f"Q0_{d}_kN"]) < 1e-6
        assert abs(sum(r["A_k"] for r in pisos) - 1.0) < 1e-12


def test_tabla_cmax_nch433():
    assert cvm.cmax_factor(7.0) == pytest.approx(0.35)
    assert cvm.cmax_factor(4.0) == pytest.approx(0.55)
    assert cvm.cmax_factor(2.0) == pytest.approx(0.90)


def test_c_fijo_criterio_anterior(modelo):
    """El metodo C fijo reproduce el criterio de las semanas 3-6: F = C (D + 0.5Q) en cada piso."""
    s = cvm.build_seismic_cases(modelo["data"], modelo["live"], 0.20)
    for row in s["pisos"]:
        assert abs(row["F_EX_kN"] - 0.20 * (row["D_kN"] + 0.5 * row["Q_kN"])) < 1e-9
