"""Armadura leida de los planos (data/armaduras_planos.json, scripts/extraer_armaduras_planos.py):
barras de vigas por estacion, caras de apoyo, mapeo de las elevaciones y mallas de muros.
Los DXF no estan en el repositorio; los tests usan el JSON extraido."""
import math

import pytest

import capacidad_ha as cha

FC, FY = 35.0, 420.0


@pytest.fixture(scope="module")
def planos():
    return cha.load_planos()


@pytest.fixture(scope="module")
def elevacion(planos):
    def buscar(plano, sufijo):
        return next(e for e in planos if e["plano"] == plano and e["titulo"].endswith(sufijo))
    return buscar


@pytest.fixture(scope="module")
def e1_62(unity):
    nodos = {n["id"]: n for n in unity["nodes"]}
    elemento = next(e for e in unity["elements"] if e["elementTag"] == "E1_62")
    return elemento, nodos


def test_barras_viga_E1_62(e1_62):
    """E1_62 (V60/80, eje 2, x 25-30, cielo piso 2): en la cara del apoyo pasan 12f25 inferiores en
    3 capas (2 / 6 / 4) de la elevacion 2017_67-302. d y phiMn+ a mano."""
    elemento, nodos = e1_62
    bp = cha.barras_planos(elemento, nodos)
    assert bp["fuente"] == "2017_67-302 ELEVACION EJE 2"
    capas = {}
    for pos, n, d, capa, t0, t1 in bp["barras"]:
        if pos == "inf" and t0 <= 0.05 <= t1:
            assert d == 25
            capas[capa] = capas.get(capa, 0) + n
    assert capas == {1: 2, 2: 6, 3: 4}
    # centros de capa desde la cara inferior: 40 + 10 + 12.5 = 62.5, +50 = 112.5, +50 = 162.5 mm
    d_util = 800.0 - (2 * 62.5 + 6 * 112.5 + 4 * 162.5) / 12.0
    as_ = 12 * math.pi * 25 ** 2 / 4
    area, d_calc, _ = cha.acero_en(bp["barras"], "inf", 0.05, 800.0, 40.0, 10)
    assert area == pytest.approx(as_) and d_calc == pytest.approx(d_util)
    a = as_ * FY / (0.85 * FC * 600.0)
    phimn = 0.9 * as_ * FY * (d_util - a / 2.0) / 1e6                  # 1357.9 kN-m
    assert phimn == pytest.approx(1357.9, abs=0.1)
    assert elemento["capacidad"]["phiMn_pos_kN_m"] == pytest.approx(phimn, abs=0.1)
    assert elemento["capacidad"]["fuenteArmadura"] == bp["fuente"]


def test_caras_de_apoyo_E1_62(unity, e1_62):
    """La columna 70/70 del nodo J (x = 30) ocupa t en [0.93, 1] (0.35 m de 5 m): la flexion se
    verifica en la cara (t = 0.93, ACI 318-19 9.4.2) y no dentro de la columna."""
    elemento, nodos = e1_62
    zonas = cha.zonas_apoyo(elemento, nodos, cha.indice_apoyos(unity["elements"], nodos))
    assert [tuple(round(t, 3) for t in z) for z in zonas] == [(0.93, 1.0)]
    assert elemento["capacidad"]["carasApoyo"] == [[0.93, 1.0]]
    ts = cha.estaciones(20, zonas)
    assert max(ts) == pytest.approx(0.93)            # la ultima estacion es la cara, no t = 1
    assert 0.95 not in ts and 1.0 not in ts


def test_mapeo_elevaciones(planos, elevacion):
    """Todas las elevaciones con escala ~0.01 m/cm; la A' de 2024_22 usa sus burbujas (1 y 3): anclarla
    al centro de los muros e=60 la deformaba hasta 0.5 m."""
    for e in planos:
        assert all(0.0090 < abs(m) < 0.0110 for m in e["ajuste"]["escala_por_tramo_m_por_cm"]), e["titulo"]
    a = elevacion("2024_22-303", "EJE A'")
    assert a["ajuste"]["anclaje"] == "burbujas"
    assert a["ajuste"]["escala_por_tramo_m_por_cm"] == [0.01]


def test_mallas_de_muros(elevacion):
    """Rotulos de malla: bloque con H/V (eje 1''), bloque con MALLA_1 sola (eje 1 de 2024_22) y texto
    suelto "M.H.A. e=60 / 4.M. f10a20" (eje A') o "T.M." con H/V al lado (eje 1')."""
    m = elevacion("2017_67-301", "EJE 1''")["muros"]["mallas"]
    assert {(x["malla_v"], x["malla_h"], x["n_mallas"]) for x in m} == {("10a20", "10a12", 2)}
    m = elevacion("2024_22-300", "EJE 1")["muros"]["mallas"]
    assert all(x["malla_v"] for x in m) and ("10a20", "10a20") in {(x["malla_v"], x["malla_h"]) for x in m}
    m = elevacion("2024_22-303", "EJE A'")["muros"]["mallas"]
    assert len(m) == 10 and {(x["espesor_cm"], x["n_mallas"], x["rotulo"]) for x in m} == {("60", 4, "texto")}
    m = elevacion("2024_22-300", "EJE 1'")["muros"]["mallas"]
    assert any(x["n_mallas"] == 3 and x["malla_v"] == "12a20" and x["malla_h"] == "12a10" for x in m)


def test_barras_de_borde_en_esquina(unity):
    """MURO-091 (eje 1'', x -10 a -6.7): el muro del modelo termina en el eje E (-10.00) y el dibujado en
    la cara exterior (-10.35); sus barras de borde (-10.31 y -10.19, 2f18 c/u) son del muro."""
    curvas = {c["sectionId"]: c for c in unity["p1l4"]["pmCurves"]}
    reg = next(r for r in unity["p1l4"]["wallRegistry"] if r["pmSectionId"] == "W_PL_MURO-091")
    assert "bordes 2φ18+2φ18 / -" in curvas[reg["pmSectionId"]]["interpretation"]
