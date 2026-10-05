"""Fixtures comunes de la suite (python -m pytest).

El modelo se analiza una vez por sesion con las mismas funciones que usan el
exportador y Unity (scripts/carga_viva_sismo.py). Ningun test escribe en los
datos del proyecto: las corridas del exportador van a una carpeta temporal.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "Proyecto1" / "scripts"
DATA = REPO / "Proyecto1" / "data"
UNITY_JSON = REPO / "Proyecto1" / "edificio_G4" / "Assets" / "Resources" / "estructura_p1l4_unity.json"
EXPORTER = SCRIPTS / "exportar_resultados_unity.py"
sys.path.insert(0, str(SCRIPTS))

import carga_viva_sismo as cvm  # noqa: E402


@pytest.fixture(scope="session")
def params():
    return cvm.load_analysis_params()


@pytest.fixture(scope="session")
def modelo(params):
    """Modelo vigente con los parametros guardados (rigidez fisurada, q_G, Q cubierta, sismo)."""
    data = cvm.load_json(cvm.JSON_PATH)
    cvm.apply_model_params(data, params.get("q_G_kN_m2"), params.get("sections"), params.get("rigidezFisurada"))
    q_q = cvm.kg_m2_to_kn_m2(float(params.get("Q_kg_m2", 500.0)))
    live = cvm.transfer_live_load(data, q_q)
    seismic = cvm.build_seismic_cases(data, live, cvm.seismic_setting(params))
    loads = {
        "G": cvm.dead_nodal_loads(data),
        "Q": cvm.vector_loads_from_dict(live["cargas_nodales_Q"]),
        "EX": cvm.vector_loads_from_dict(seismic["cargas_nodales_EX"]),
        "EY": cvm.vector_loads_from_dict(seismic["cargas_nodales_EY"]),
    }
    return {"data": data, "live": live, "seismic": seismic, "loads": loads, "q_q": q_q}


@pytest.fixture(scope="session")
def resultados(modelo):
    """Casos base resueltos con OpenSees."""
    return {caso: cvm.run_and_extract(modelo["data"], cargas) for caso, cargas in modelo["loads"].items()}


@pytest.fixture(scope="session")
def unity():
    return json.loads(UNITY_JSON.read_text(encoding="utf-8"))


def run_exporter(out, *args, timeout=600):
    """Corre el exportador como lo hace Unity (PythonJob): python -X utf8 script args --out <tmp>."""
    cmd = [sys.executable, "-X", "utf8", str(EXPORTER), *map(str, args), "--out", str(out)]
    return subprocess.run(cmd, cwd=SCRIPTS, capture_output=True, text=True, encoding="utf-8", timeout=timeout)


@pytest.fixture(scope="session")
def tmp_session(tmp_path_factory):
    return tmp_path_factory.mktemp("corridas")
