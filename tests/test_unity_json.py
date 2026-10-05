"""JSON que lee Unity (viewer y AR): integridad, trazabilidad y consistencia con el analisis."""
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
