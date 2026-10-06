"""Honors H5: cambio de armadura con regeneracion de la curva de interaccion P-M y del DCR."""
import json
import math

import pytest

import capacidad_ha as cha
from conftest import run_exporter

FC, FY = 35.0, 420.0


@pytest.fixture(scope="module")
def con_12f25(tmp_session):
    """Escenario como el editor de armadura de Unity: COL70/70 pasa de 8f25 a 12f25."""
    arm = tmp_session / "armaduras_unity.json"
    arm.write_text(json.dumps({"secciones": {"COL70/70": {"barras": "12f25"}}, "elementos": {}}), encoding="utf-8")
    out = tmp_session / "arm12.json"
    r = run_exporter(out, "--armaduras", arm)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.lento
def test_curva_regenerada(con_12f25):
    curvas = {c["sectionId"]: c for c in con_12f25["p1l4"]["pmCurves"]}
    assert "COL70/70_12f25" in curvas
    c = curvas["COL70/70_12f25"]
    ast = 12 * math.pi * 25 ** 2 / 4
    p0 = (0.85 * FC * (700 * 700 - ast) + FY * ast) / 1000.0
    assert c["Ast_mm2"] == pytest.approx(ast) and c["steelBars"] == 12
    assert c["Po_kN"] == pytest.approx(p0, abs=0.1)        # exportado con 0.1 kN
    assert max(p["P_kN"] for p in c["points"]) == pytest.approx(0.80 * 0.65 * p0, abs=0.1)
    # la curva exportada es la misma que calcula capacidad_ha directamente
    arm = cha.load_armaduras()                                  # recubrimiento y estribo reales (EDf12a10)
    d_estribo = cha.stirrup(arm["secciones"]["COL70/70"]["estribos"])[2]
    directa = cha.curva_pm_columna(700, 700, 12, 25, arm["recubrimiento_m"], d_estribo)["puntos"]
    assert len(directa) == len(c["points"])
    ordenar = lambda pts: sorted(pts, key=lambda q: (round(q["P_kN"], 1), round(q["M_kN_m"], 1)))
    for p, q in zip(ordenar(c["points"]), ordenar(directa)):
        assert p["P_kN"] == pytest.approx(q["P_kN"], abs=0.1) and p["M_kN_m"] == pytest.approx(q["M_kN_m"], abs=0.1)


@pytest.mark.lento
def test_mas_armadura_mas_capacidad_menor_dcr(con_12f25, unity):
    """Con mas acero cada columna COL70/70 tiene capacidad mayor y DCR menor o igual (mismas fuerzas)."""
    base = {e["elementTag"]: e for e in unity["elements"] if e.get("sectionId") == "COL70/70"}
    for e in con_12f25["elements"]:
        if e.get("sectionId") != "COL70/70":
            continue
        assert e["pmCurveId"] == "COL70/70_12f25"
        assert e["capacidad"]["DCR"] <= base[e["elementTag"]]["capacidad"]["DCR"] + 1e-9
    peor = max(base.values(), key=lambda x: x["capacidad"]["DCR"])["elementTag"]
    nuevo = next(e for e in con_12f25["elements"] if e["elementTag"] == peor)
    assert nuevo["capacidad"]["DCR"] < base[peor]["capacidad"]["DCR"]


@pytest.mark.lento
def test_cambio_de_seccion_conserva_la_capacidad(tmp_session):
    """Cambiar la seccion de una viga (Unity -> --mods) a una que no esta en armaduras.json no la deja sin
    verificacion: usa la armadura de su seccion original con las dimensiones nuevas. E1_62 (barras del plano,
    12f25 inferiores en 3 capas) de V60/80 a V60/60: phiMn+ a mano con d = 600 - 120,8 = 479,2 mm."""
    mods = tmp_session / "mods_seccion.json"
    mods.write_text(json.dumps({"sections": {"E1_62": {"width_m": 0.6, "height_m": 0.6, "sectionId": "V60/60"},
                                             "E1_72": {"width_m": 0.6, "height_m": 1.0, "sectionId": "V60/100"}}}), encoding="utf-8")
    out = tmp_session / "seccion.json"
    r = run_exporter(out, "--mods", mods)
    assert r.returncode == 0, r.stderr[-2000:]
    elems = {e["elementTag"]: e for e in json.loads(out.read_text(encoding="utf-8"))["elements"]}
    for tag in ("E1_62", "E1_72"):
        assert elems[tag].get("capacidad"), f"{tag} quedo sin capacidad"
        assert "seccion cambiada" in elems[tag]["capacidad"]["nota"]
    d = 600.0 - (2 * 62.5 + 6 * 112.5 + 4 * 162.5) / 12.0
    a_s = 12 * math.pi * 25 ** 2 / 4
    a = a_s * FY / (0.85 * FC * 600.0)
    assert elems["E1_62"]["capacidad"]["phiMn_pos_kN_m"] == pytest.approx(0.9 * a_s * FY * (d - a / 2.0) / 1e6, abs=0.1)
