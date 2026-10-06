"""JSON que lee Unity (viewer y AR): integridad, trazabilidad y consistencia con el analisis."""
import pytest

from conftest import cvm


def test_ids_y_fuerzas_completas(unity):
    ids = [e["id"] for e in unity["elements"]]
    tags = [e["elementTag"] for e in unity["elements"]]
    assert len(ids) == len(set(ids)) and len(tags) == len(set(tags))
    casos = ["G", "Q", "EX", "EY"] + [c["name"] for c in unity["p1l4"]["combinations"]]
    fuerzas = {(f["id"], f["combo"]) for f in unity["p1l4"]["elementForces"]}
    faltan = [(i, c) for i in ids for c in casos if (i, c) not in fuerzas]
    assert not faltan, faltan[:10]
    nodos = {n["id"] for n in unity["nodes"]}
    assert all(e["nodeI"] in nodos and e["nodeJ"] in nodos for e in unity["elements"])


def test_capas_de_la_demo(unity):
    """Ejes de grilla (planos), diafragmas con sus fuerzas y apoyos presentes."""
    assert len(unity["ejesGrilla"]) >= 20
    assert {"A'", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "1", "2", "3"} <= {e["nombre"] for e in unity["ejesGrilla"]}
    d = unity["diafragmasSismo"]
    assert len(d) == 10
    assert abs(sum(x["F_EX_kN"] for x in d) - unity["resumenAnalisis"]["corteBasal_EX_kN"]) < 1e-6
    assert abs(sum(x["F_EY_kN"] for x in d) - unity["resumenAnalisis"]["corteBasal_EY_kN"]) < 1e-6
    assert len(unity["supports"]) > 0


def test_resumen_equilibrio(unity):
    r = unity["resumenAnalisis"]
    assert abs(r["G_aplicada_kN"] - r["G_reaccion_kN"]) < 1e-3
    assert abs(r["Q_aplicada_kN"] - r["Q_reaccion_kN"]) < 1e-3


def test_columnas_con_curva_de_diseno(unity):
    curvas = {c["sectionId"]: c for c in unity["p1l4"]["pmCurves"]}
    for e in unity["elements"]:
        if e["type"] == "columna" and e.get("material") != "acero":
            assert e.get("pmCurveId") in curvas, e["elementTag"]
            assert curvas[e["pmCurveId"]]["Ast_mm2"] > 0
            assert e["capacidad"]["DCR"] >= 0


def test_trazabilidad_de_la_corrida(unity):
    c = unity["corrida"]
    assert c["comando"].startswith("python -X utf8 Proyecto1/scripts/exportar_resultados_unity.py")
    assert c["openseespy"] and c["python"]
    assert all(c["entradas_sha256"][k] for k in ("modelo", "parametros", "combinaciones", "armaduras"))


def test_json_unity_coincide_con_opensees(unity, resultados):
    """El JSON vigente (lo que muestran viewer y AR) = corrida directa de OpenSees en esta sesion."""
    by = {(d["node"], d["combo"]): d for d in unity["p1l4"]["displacements"]}
    err = 0.0
    for caso in ("G", "Q", "EX", "EY"):
        for nid, d in resultados[caso]["displacements"].items():
            u = by.get((nid, caso))
            if u is None:
                continue
            err = max(err, *(abs(u[k] - d[k]) for k in ("ux", "uy", "uz")))
    assert err < 1e-9, f"diferencia maxima {err:.2e} m: re-exportar el JSON de Unity"


def test_panel_areas_tributarias(unity, modelo):
    """El panel "Áreas tributarias por piso" del viewer suma los dos edificios (vigas y brazos de muro):
    su total es el área que reparte el análisis (antes mostraba solo las vigas del edificio 1, ~3 180 m²)."""
    filas = unity["tributaryList"]
    total = next(f for f in filas if f["piso"].startswith("Total"))
    pisos = [f for f in filas if not f["piso"].startswith("Total")]
    assert {f["piso"].split(" · ")[1] for f in pisos} == {"E1", "E2"}
    assert sum(f["area_total"] for f in pisos) == pytest.approx(total["area_total"])
    assert total["area_total"] == pytest.approx(modelo["live"]["area_total_m2"], rel=1e-9)


@pytest.mark.parametrize("tag", ["E1_72", "E1_62"])
def test_flecha_de_viga_como_en_unity(modelo, tag):
    """La deformada y la flecha que muestra Unity (UnityData.DeformedOffset) = Hermite con los desplazamientos
    y giros de los nodos + q x^2 (L-x)^2 / (24 E I) de la carga repartida. Debe ser igual al desplazamiento
    del nodo central de OpenSees con la viga partida en dos (caso G)."""
    import copy
    import math
    base = modelo["data"]
    k = cvm.load_analysis_params()["rigidezFisurada"]["viga"]
    E = 4700.0 * 35.0 ** 0.5 * 1000.0
    nodes = cvm.node_map(base)
    res = cvm.run_and_extract(base, cvm.dead_nodal_loads(base))
    D = res["displacements"]
    g = lambda n: D.get(n) or D.get(str(n))
    e = next(x for x in base["elements"] if x["elementTag"] == tag)
    a, b = nodes[e["nodeI"]], nodes[e["nodeJ"]]
    L = math.dist((a["x"], a["y"], a["z"]), (b["x"], b["y"], b["z"]))
    lx = [(b[c] - a[c]) / L for c in "xyz"]
    cruz = lambda u, v: [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    ly = cruz([0.0, 0.0, 1.0], lx)
    ly = [c / math.sqrt(sum(q * q for q in ly)) for c in ly]
    lz = cruz(lx, ly)
    dot = lambda u, v: sum(p * q for p, q in zip(u, v))
    dI, dJ = g(e["nodeI"]), g(e["nodeJ"])
    wI, wJ = dot([dI["ux"], dI["uy"], dI["uz"]], lz), dot([dJ["ux"], dJ["uy"], dJ["uz"]], lz)
    tyI, tyJ = -dot([dI["rx"], dI["ry"], dI["rz"]], ly), -dot([dJ["rx"], dJ["ry"], dJ["rz"]], ly)
    s = 0.5
    w_hermite = 0.5 * wI + L / 8.0 * tyI + 0.5 * wJ - L / 8.0 * tyJ
    q = (e["deadLoad"] + cvm.self_weight_kN(e, nodes)) / L
    w_carga = q * (L / 2.0) ** 4 / (24.0 * E * k * e["width_m"] * e["height_m"] ** 3 / 12.0)
    uz_unity = w_hermite * lz[2] - w_carga
    # OpenSees con la viga partida en su punto medio
    d2 = copy.deepcopy(base)
    n2 = cvm.node_map(d2)
    e2 = next(x for x in d2["elements"] if x["elementTag"] == tag)
    nid = max(n["id"] for n in d2["nodes"]) + 1
    d2["nodes"].append({"id": nid, "x": (a["x"] + b["x"]) / 2, "y": (a["y"] + b["y"]) / 2, "z": (a["z"] + b["z"]) / 2})
    e3 = copy.deepcopy(e2)
    e3.update(id=max(x["id"] for x in d2["elements"]) + 1, elementTag=tag + "_b", nodeI=nid)
    e2["nodeJ"] = nid
    for kk in ("deadLoad", "liveLoad", "areaTributaria", "cargaTributaria", "gravityLoad"):
        if isinstance(e2.get(kk), (int, float)):
            e2[kk] /= 2.0
            e3[kk] /= 2.0
    d2["elements"].append(e3)
    D2 = cvm.run_and_extract(d2, cvm.dead_nodal_loads(d2))["displacements"]
    uz_partida = (D2.get(nid) or D2.get(str(nid)))["uz"]
    assert uz_unity == pytest.approx(uz_partida, abs=2e-6)      # 0,002 mm
    assert abs(w_hermite * lz[2] - uz_partida) > 1e-4     # sin el termino de carga no calza (> 0,1 mm)
