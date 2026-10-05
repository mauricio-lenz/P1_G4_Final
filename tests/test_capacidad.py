"""Capacidad RC: fiber section / M-phi, P-M de columna (ACI 318-19), vigas y P-M de muro."""
import math

import pytest

import capacidad_ha as cha
from conftest import cvm

FC, FY = 35.0, 420.0


def test_mphi_convergencia_de_malla():
    """Mmax de la seccion de fibras COL70/70 (P = 0): malla 20x20 vs 40x40 dentro del 1 %."""
    mmax = {}
    for n in (20, 40):
        curv, m = cvm._fiber_moment_curvature(0.0, n, 0.12, 300)
        mmax[n] = max(m)
    assert abs(mmax[20] - mmax[40]) / mmax[40] < 0.01


def test_pm_columna_puntos_aci():
    """COL70/70 8f25: P0, phiPmax = 0.80*0.65*P0 y traccion pura -0.9 fy Ast (calculo a mano)."""
    curva = cha.curva_pm_columna(700, 700, 8, 25)
    ast = 8 * math.pi * 25 ** 2 / 4
    p0 = (0.85 * FC * (700 * 700 - ast) + FY * ast) / 1000.0           # 16 110 kN
    assert curva["Ast_mm2"] == pytest.approx(ast)
    assert curva["P0_kN"] == pytest.approx(p0)
    assert curva["phiPmax_kN"] == pytest.approx(0.80 * 0.65 * p0)
    ps = [q["P_kN"] for q in curva["puntos"]]
    assert min(ps) == pytest.approx(-0.9 * FY * ast / 1000.0)
    assert max(ps) == pytest.approx(0.80 * 0.65 * p0)
    for q in curva["puntos"]:
        assert 0.65 - 1e-9 <= q["phi"] <= 0.90 + 1e-9


def test_pm_columna_vs_fibras(monkeypatch):
    """Flexion pura de la COL70/70 por dos metodos independientes con las mismas hipotesis
    (acero elastoplastico, eps_cu = 0.003): bloque de Whitney (capacidad_ha) vs integracion de
    fibras hasta el aplastamiento (carga_viva_sismo). Deben coincidir dentro del 5 %."""
    curva = cha.curva_pm_columna(700, 700, 8, 25)
    pts = sorted(curva["puntos"], key=lambda q: q["Pn_kN"])
    lo = max((q for q in pts if q["Pn_kN"] <= 0), key=lambda q: q["Pn_kN"])
    hi = min((q for q in pts if q["Pn_kN"] > 0), key=lambda q: q["Pn_kN"])
    mn_whitney = lo["Mn_kN_m"] + (hi["Mn_kN_m"] - lo["Mn_kN_m"]) * (0 - lo["Pn_kN"]) / (hi["Pn_kN"] - lo["Pn_kN"])
    monkeypatch.setattr(cvm, "_FIB_EH", 0.0)
    monkeypatch.setattr(cvm, "_FIB_EPS_CU", 0.003)
    curv, m = cvm._fiber_moment_curvature(0.0, 20, 0.12, 2000)
    assert abs(mn_whitney - m[-1]) / m[-1] < 0.05, f"Whitney {mn_whitney:.0f} vs fibras {m[-1]:.0f} kN-m"


def test_mphi_termina_en_aplastamiento():
    """La curva M-phi se corta cuando la fibra extrema comprimida llega a eps_cu (no en el fin del rango)."""
    curv, m = cvm._fiber_moment_curvature(0.0, 20, 0.12, 300)
    assert curv[-1] < 0.12
    assert 500.0 < max(m) < 650.0


def test_flexion_viga_a_mano():
    """phiMn de V60/80 con 4f22: a = As fy / (0.85 f'c b), Mn = As fy (d - a/2), phi = 0.9."""
    b, d = 600.0, 739.0
    as_ = 4 * math.pi * 22 ** 2 / 4
    a = as_ * FY / (0.85 * FC * b)
    mn = as_ * FY * (d - a / 2) / 1e6
    phimn, mn_calc, eps_t = cha.flexion_rectangular(b, d, as_)
    assert mn_calc == pytest.approx(mn)
    assert eps_t > 0.005 and phimn == pytest.approx(0.9 * mn)


def test_notacion_de_barras():
    assert cha.bars_area_mm2("4φ22")[0] == pytest.approx(4 * math.pi * 22 ** 2 / 4)
    assert cha.bars_area_mm2("2f22+2f25")[0] == pytest.approx(2 * math.pi * (22 ** 2 + 25 ** 2) / 4)
    av, s, d = cha.stirrup("EDf10a10")
    assert (av, s, d) == (pytest.approx(4 * math.pi * 100 / 4), 100.0, 10)


def test_pm_muro_diseno_a_mano():
    """Muro 20x340 con doble malla V f10a20 sin barras de borde: 17 posiciones (de 35 mm a 3365 mm
    cada 200 mm) x 2 barras; P0 y traccion pura a mano. 4 mallas duplican la armadura de la malla."""
    curva = cha.curva_pm_muro(0.20, 3.40, "10a20")
    ast = 17 * 2 * math.pi * 10 ** 2 / 4
    assert curva["n_barras"] == 17
    assert curva["Ast_mm2"] == pytest.approx(ast)
    assert curva["P0_kN"] == pytest.approx((0.85 * FC * (200 * 3400 - ast) + FY * ast) / 1000.0)
    assert min(q["P_kN"] for q in curva["puntos"]) == pytest.approx(-0.9 * FY * ast / 1000.0)
    assert cha.curva_pm_muro(0.20, 3.40, "10a20", n_mallas=4)["Ast_mm2"] == pytest.approx(2 * ast)


def test_pm_muro_barras_de_borde():
    """Las barras de borde suben la capacidad en flexion pura (P = 0) y reemplazan la malla en la punta."""
    sin = cha.curva_pm_muro(0.20, 3.40, "10a20")
    con = cha.curva_pm_muro(0.20, 3.40, "10a20", {"ini": [(2, 22), (2, 22)], "fin": [(2, 22), (2, 22)]})
    assert cha.m_capacidad(con["puntos"], 0.0) > 1.3 * cha.m_capacidad(sin["puntos"], 0.0)
    # 2 pares de f22 por punta (en 35 y 135 mm) en vez de las posiciones de malla de esa zona
    assert con["Ast_mm2"] == pytest.approx(sin["Ast_mm2"] - 2 * 2 * math.pi * 10 ** 2 / 4 + 8 * math.pi * 22 ** 2 / 4)


def test_pm_muros_unity(unity):
    """Cada muro del JSON de Unity tiene su curva de diseno: de los planos (W_PL_) o con malla supuesta (W_DM_)."""
    curvas = {c["sectionId"]: c for c in unity["p1l4"]["pmCurves"]}
    for r in unity["p1l4"]["wallRegistry"]:
        sid = r["pmSectionId"]
        assert sid in curvas and sid.startswith(("W_PL_", "W_DM_")), sid
        assert (r["fuenteArmadura"] == "supuesta") == sid.startswith("W_DM_")
