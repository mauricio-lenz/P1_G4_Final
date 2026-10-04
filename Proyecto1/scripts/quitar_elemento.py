#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reanalisis del edificio al quitar uno o mas elementos (viewer Unity).

Marca los elementos como "removed" (no aportan rigidez en OpenSees), mantiene
sus cargas tributarias en sus nodos (la losa sigue ahi), recalcula el sismo
con diafragma rigido y corre G, Q, EX, EY, C1, C2, C3. Entrega los mismos
registros que el exportador de Unity para reemplazar los resultados en vivo.

No modifica ningun archivo del modelo: el cambio vive solo en el viewer.

Uso:
    python quitar_elemento.py --elements E1_29,E1_30 --out resultado.json
"""

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carga_viva_sismo as cvm   # noqa: E402

COMBOS = cvm.load_combinations()   # data/combinaciones.json
Q_KG_M2 = 500.0   # mismos parametros por defecto que exportar_resultados_unity.py


def _sig(v, digits=7):
    return float(f"{v:.{digits}g}")


def buscar(data, clave):
    clave = str(clave).strip().lower()
    for e in data["elements"]:
        if str(e["id"]) == clave or str(e.get("elementTag", "")).lower() == clave:
            return e
    return None


def cargas_perdidas(data, load_sets):
    """Carga aplicada en nodos que quedaron sin ningun elemento estructural."""
    conectados = set()
    for e in cvm.structural_elements(data):
        conectados.update((e["nodeI"], e["nodeJ"]))
    soportes = {s["node"] for s in data.get("supports", [])}
    extremos = {e["id"]: (e["nodeI"], e["nodeJ"]) for e in data.get("elements", [])}
    activos = {e["id"] for e in cvm.structural_elements(data)}
    # clave < 0 = carga repartida del elemento -clave; si fue quitado, va mitad a cada nodo
    por_nodo = {}
    for nid, vec in load_sets["G"].items():
        if nid >= 0:
            por_nodo[nid] = por_nodo.get(nid, 0.0) + vec[2]
        elif -nid not in activos and -nid in extremos:
            for n in extremos[-nid]:
                por_nodo[n] = por_nodo.get(n, 0.0) + 0.5 * vec[2]
    perdida = 0.0
    nodos = []
    for nid, fz in por_nodo.items():
        if nid not in conectados and nid not in soportes and abs(fz) > 1e-9:
            perdida += abs(fz)
            nodos.append(nid)
    return perdida, nodos


def main():
    parser = argparse.ArgumentParser(description="Quitar elementos y reanalizar (OpenSees).")
    parser.add_argument("--elements", required=True, help="ids o tags separados por coma")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)

    data = cvm.load_json(cvm.JSON_PATH)
    quitados = []
    for clave in [c for c in args.elements.split(",") if c.strip()]:
        e = buscar(data, clave)
        if e is None:
            out.write_text(json.dumps({"error": f"No existe el elemento '{clave.strip()}'"}), encoding="utf-8")
            sys.exit(2)
        e["removed"] = True
        quitados.append({"id": e["id"], "tag": e.get("elementTag", str(e["id"])), "type": e.get("type", "")})

    params = cvm.load_analysis_params()
    cvm.apply_model_params(data, params.get("q_G_kN_m2"), params.get("sections"), params.get("rigidezFisurada"))
    q_q = cvm.kg_m2_to_kn_m2(float(params.get("Q_kg_m2", Q_KG_M2)))
    live = cvm.transfer_live_load(data, q_q)
    seismic = cvm.build_seismic_cases(data, live, cvm.seismic_setting(params))
    load_sets = {
        "G": cvm.dead_nodal_loads(data),
        "Q": cvm.vector_loads_from_dict(live["cargas_nodales_Q"]),
        "EX": cvm.vector_loads_from_dict(seismic["cargas_nodales_EX"]),
        "EY": cvm.vector_loads_from_dict(seismic["cargas_nodales_EY"]),
    }
    perdida, nodos_sueltos = cargas_perdidas(data, load_sets)

    casos = dict(load_sets)
    for nombre, lambdas in COMBOS.items():
        casos[nombre] = cvm.combine_nodal_loads(load_sets, lambdas)

    displacements, forces, estado = [], [], {}
    g_aplicada = sum(v[2] for v in load_sets["G"].values())
    g_reaccion = 0.0
    for nombre, cargas in casos.items():
        res = cvm.run_and_extract(data, cargas)
        u_max = 0.0
        for nid, d in res["displacements"].items():
            vals = [d.get(k, 0.0) for k in ("ux", "uy", "uz", "rx", "ry", "rz")]
            if any(math.isnan(v) or math.isinf(v) for v in vals):
                res["ok"] = False
                vals = [0.0] * 6
            u_max = max(u_max, math.sqrt(vals[0] ** 2 + vals[1] ** 2 + vals[2] ** 2))
            displacements.append({"combo": nombre, "node": int(nid), **{k: _sig(v) for k, v in
                                  zip(("ux", "uy", "uz", "rx", "ry", "rz"), vals)}})
        for e in data["elements"]:
            f = res["element_forces"].get(e["id"], [0.0] * 12)
            forces.append({"combo": nombre, "id": e["id"], "f": [_sig(v) for v in list(f)[:12]]})
        estado[nombre] = {"ok": bool(res["ok"]), "u_max_m": u_max}
        if nombre == "G":
            g_reaccion = res["reactions"]["sum_Fz"]

    resultado = {
        "removed": quitados,
        "estado": [{"combo": k, **v} for k, v in estado.items()],
        "G_aplicada_kN": g_aplicada,
        "G_reaccion_kN": g_reaccion,
        "carga_perdida_kN": perdida,
        "nodos_sin_elementos": nodos_sueltos,
        "displacements": displacements,
        "elementForces": forces,
    }
    out.write_text(json.dumps(resultado, separators=(",", ":")), encoding="utf-8")
    print(f"OK quitados={[q['tag'] for q in quitados]} | G aplicada={g_aplicada:.1f} kN, "
          f"reaccion={g_reaccion:.1f} kN, perdida={perdida:.1f} kN | "
          + ", ".join(f"{k}: u_max={v['u_max_m']:.4f} m ok={v['ok']}" for k, v in estado.items()))


if __name__ == "__main__":
    main()
