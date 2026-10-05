"""Modelo y analisis global: equilibrio, superposicion, unidades, ejes y junta."""
import collections
import math

import pytest

from conftest import cvm

TOL_KN = 1e-6


@pytest.mark.parametrize("caso, comp, key", [("G", 2, "sum_Fz"), ("Q", 2, "sum_Fz"), ("EX", 0, "sum_Fx"), ("EY", 1, "sum_Fy")])
def test_equilibrio(modelo, resultados, caso, comp, key):
    """Carga aplicada + reaccion = 0 en cada caso base (repartidas incluidas)."""
    aplicada = sum(v[comp] for v in modelo["loads"][caso].values())
    reaccion = resultados[caso]["reactions"][key]
    assert resultados[caso]["ok"]
    assert abs(aplicada + reaccion) < max(TOL_KN, 1e-9 * abs(aplicada))


def test_corte_basal_igual_a_fuerzas_sismicas(modelo, resultados):
    s = modelo["seismic"]
    assert abs(resultados["EX"]["reactions"]["sum_Fx"]) == pytest.approx(s["corte_basal_EX_kN"], rel=1e-9)
    assert abs(resultados["EY"]["reactions"]["sum_Fy"]) == pytest.approx(s["corte_basal_EY_kN"], rel=1e-9)


def test_superposicion_lineal(modelo, resultados):
    """Cada combinacion resuelta por separado = suma lambda * casos base (analisis lineal)."""
    combos = cvm.load_combinations()
    for nombre, lam in combos.items():
        cargas = cvm.combine_nodal_loads(modelo["loads"], lam)
        directa = cvm.run_and_extract(modelo["data"], cargas)
        err = 0.0
        for nid, d in directa["displacements"].items():
            for k in ("ux", "uy", "uz"):
                sup = sum(lam.get(c, 0.0) * resultados[c]["displacements"][nid][k] for c in ("G", "Q", "EX", "EY"))
                err = max(err, abs(d[k] - sup))
        assert err < 1e-9, f"{nombre}: error de superposicion {err:.2e} m"


def test_unidades():
    """kN, m, kN/m2: E del G35, conversion kg/m2 -> kN/m2 y peso propio de una columna."""
    assert abs(cvm.E_CONCRETE - 4700.0 * math.sqrt(35.0) * 1000.0) < 1e-6      # 27 806 MPa en kN/m2
    assert abs(cvm.kg_m2_to_kn_m2(500.0) - 4.903325) < 1e-9
    col = {"type": "columna", "width_m": 0.70, "height_m": 0.70, "nodeI": 1, "nodeJ": 2}
    nodes = {1: {"x": 0, "y": 0, "z": 0}, 2: {"x": 0, "y": 0, "z": 3.96}}
    assert abs(cvm.self_weight_kN(col, nodes) - 25.0 * 0.49 * 3.96) < 1e-9          # 48.51 kN


def test_ejes_locales_ortonormales(modelo):
    data = modelo["data"]
    nodes = cvm.node_map(data)
    for e in data["elements"]:
        pi = [nodes[e["nodeI"]][k] for k in "xyz"]
        pj = [nodes[e["nodeJ"]][k] for k in "xyz"]
        vertical = abs(pi[0] - pj[0]) < 1e-9 and abs(pi[1] - pj[1]) < 1e-9
        x, y, z, length = cvm._local_axes(pi, pj, 2 if vertical else 1)
        assert length > 0
        for a, b in ((x, y), (y, z), (x, z)):
            assert abs(sum(p * q for p, q in zip(a, b))) < 1e-9
        for v in (x, y, z):
            assert abs(math.sqrt(sum(c * c for c in v)) - 1.0) < 1e-9
        if vertical:
            assert abs(abs(x[2]) - 1.0) < 1e-9      # columnas y muros: x local vertical


def test_junta_sin_nodos_compartidos(modelo):
    """Los edificios 1 (2017_67) y 2 (2024_22) estan separados por junta: ningun nodo es de ambos."""
    duenos = collections.defaultdict(set)
    for e in modelo["data"]["elements"]:
        for n in (e["nodeI"], e["nodeJ"]):
            duenos[n].add(e.get("sourceBuilding") or "edificio_1")
    compartidos = [n for n, b in duenos.items() if len(b) > 1]
    assert not compartidos, f"nodos compartidos entre edificios: {compartidos[:10]}"


def test_diafragmas_por_edificio(modelo):
    owner = cvm.node_buildings(modelo["data"])
    for (edificio, _z), g in cvm.diaphragm_groups(modelo["data"]).items():
        assert {owner[n] for n in [g["master"]] + g["slaves"]} == {edificio}
