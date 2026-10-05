"""Honors H4: reanalisis OpenSees desde Unity (validacion, errores, reproducibilidad y
comparacion contra la corrida directa)."""
import json

import pytest

import validacion_entradas as val
from conftest import DATA, cvm, run_exporter

ARGS_UNITY = [  # lo que envia AnalysisSession.StartReanalysis con los parametros vigentes
    "--q-kg-m2", "500", "--q-cubierta-kg-m2", "200", "--sismo", "nch433", "--zona", "3", "--suelo", "C",
    "--R", "7", "--I", "1", "--fraccionQ", "0.25", "--qG", "6.22722275", "--fisurada", "0.35,0.7,0.35",
]


def cargar(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- validacion
@pytest.mark.parametrize("kwargs, texto", [
    ({"q_kg_m2": -5}, "Q = -5"),
    ({"q_cubierta_kg_m2": 9000}, "Q cubierta"),
    ({"q_g": 0}, "q_G"),
    ({"fisurada": {"viga": 0.0, "columna": 0.7, "muro": 0.35}}, "rigidez fisurada viga"),
    ({"sismo": {"metodo": "NCh433", "zona": 4, "suelo": "C", "R": 7, "I": 1, "fraccionQ": 0.25}}, "zona"),
    ({"sismo": {"metodo": "NCh433", "zona": 3, "suelo": "C", "R": 40, "I": 1, "fraccionQ": 0.25}}, "R = 40"),
    ({"secciones": {"E1_62": {"width_m": 0.05, "height_m": 0.8}}}, "width_m"),
])
def test_validacion_rechaza(kwargs, texto):
    base = dict(q_kg_m2=500, q_cubierta_kg_m2=200, q_g=6.2, fisurada={"viga": 0.35},
                sismo={"metodo": "NCh433", "zona": 3, "suelo": "C", "R": 7, "I": 1, "fraccionQ": 0.25})
    base.update(kwargs)
    with pytest.raises(val.ErrorValidacion, match=texto):
        val.validar(base["q_kg_m2"], base["q_cubierta_kg_m2"], base["q_g"], base["fisurada"], base["sismo"],
                    base.get("secciones"))


def test_validacion_acepta_parametros_vigentes(params):
    val.validar(params["Q_kg_m2"], params["Q_cubierta_kg_m2"], params["q_G_kN_m2"], params["rigidezFisurada"],
                cvm.seismic_setting(params), params.get("sections"), combos_path=cvm.COMBINATIONS_PATH,
                armaduras_path=DATA / "armaduras.json")


def test_validacion_combinaciones_y_armaduras(tmp_path):
    malas = tmp_path / "combos.json"
    malas.write_text(json.dumps({"combinaciones": [{"name": "C1", "G": 1, "Q": "x"}, {"name": "C1", "G": 9}]}))
    errores = []
    val.validar_combinaciones(json.loads(malas.read_text()), errores)
    assert any("no es un numero" in e for e in errores) and any("repetido" in e for e in errores)
    errores = []
    val.validar_armaduras({"elementos": {"E1_62": {"inferior": "6x", "estribosApoyo": "Ef10a2"}}}, errores)
    assert any("no se entiende" in e for e in errores) and any("espaciamiento" in e for e in errores)


@pytest.mark.lento
def test_exportador_sale_con_codigo_2(tmp_path):
    """Una entrada invalida no llega a OpenSees: codigo 2, mensaje legible y sin JSON de salida."""
    out = tmp_path / "x.json"
    r = run_exporter(out, "--q-kg-m2", "-5", "--R", "50")
    assert r.returncode == 2
    assert "ERROR de validacion" in r.stderr and "Q = -5" in r.stderr and "R = 50" in r.stderr
    assert not out.exists()


# ------------------------------------------------- comparacion contra corrida directa
@pytest.fixture(scope="module")
def corrida_unity(tmp_session):
    out = tmp_session / "unity.json"
    mods = tmp_session / "mods.json"
    mods.write_text('{"sections": {}}', encoding="utf-8")
    r = run_exporter(out, *ARGS_UNITY, "--combos", cvm.COMBINATIONS_PATH, "--mods", mods)
    assert r.returncode == 0, r.stderr[-2000:]
    return cargar(out)


@pytest.mark.lento
def test_unity_igual_a_opensees_directo(corrida_unity, resultados, unity):
    """Reanalisis con los argumentos de Unity = OpenSees en proceso = JSON vigente (mismo modelo)."""
    disp = {(d["node"], d["combo"]): d for d in corrida_unity["p1l4"]["displacements"]}
    err = 0.0
    for caso in ("G", "Q", "EX", "EY"):
        for nid, d in resultados[caso]["displacements"].items():
            err = max(err, *(abs(disp[(nid, caso)][k] - d[k]) for k in ("ux", "uy", "uz")))
    assert err < 1e-9
    f_vig = {(f["id"], f["combo"]): f["f"] for f in unity["p1l4"]["elementForces"]}
    for f in corrida_unity["p1l4"]["elementForces"]:
        assert max(abs(a - b) for a, b in zip(f["f"], f_vig[(f["id"], f["combo"])])) < 1e-6
    assert corrida_unity["corrida"]["comando"].count("--sismo nch433") == 1


@pytest.mark.lento
def test_escenario_q300_vs_directo(tmp_session, params):
    """Cambio de Q en Unity (300 kg/m2): la reaccion de Q coincide con el calculo directo en proceso."""
    out = tmp_session / "q300.json"
    r = run_exporter(out, "--q-kg-m2", "300", "--q-cubierta-kg-m2", "200")
    assert r.returncode == 0, r.stderr[-2000:]
    esc = cargar(out)
    data = cvm.load_json(cvm.JSON_PATH)
    cvm.apply_model_params(data, params.get("q_G_kN_m2"), params.get("sections"), params.get("rigidezFisurada"), 200.0)
    live = cvm.transfer_live_load(data, cvm.kg_m2_to_kn_m2(300.0))
    directo = cvm.run_and_extract(data, cvm.vector_loads_from_dict(live["cargas_nodales_Q"]))
    assert esc["resumenAnalisis"]["Q_reaccion_kN"] == pytest.approx(directo["reactions"]["sum_Fz"], rel=1e-9)
    assert esc["resumenAnalisis"]["Q_kN_m2"] == pytest.approx(cvm.kg_m2_to_kn_m2(300.0))
