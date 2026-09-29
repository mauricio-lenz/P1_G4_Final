#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Carga puntual o distribuida sobre un elemento elegido (viewer Unity).

Calcula con OpenSees los 12 casos unitarios del elemento (Fx, Fy, Fz, Mx,
My, Mz = 1 en su nodo I y en su nodo J). Unity combina esos casos con las
fuerzas de empotramiento perfecto de la carga que el usuario define
(puntual P en a, o distribuida w en [x1, x2], en direccion -Z, X o Y), igual
que en la carga movil: el resultado es exacto porque el modelo es lineal.

Uso:
    python carga_elemento.py --element E1_29 --out casos.json
    python carga_elemento.py --element 29 --validar      # compara con analisis directo
"""

import argparse
import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carga_viva_sismo as cvm   # noqa: E402


def _sig(v, digits=6):
    return float(f"{v:.{digits}g}")


def buscar_elemento(data, clave):
    clave = str(clave).strip().lower()
    for e in data["elements"]:
        if str(e["id"]) == clave or str(e.get("elementTag", "")).lower() == clave:
            return e
    return None


def casos_unitarios(data, elem):
    nodes = cvm.node_map(data)
    building = cvm.node_buildings(data)
    edificio = elem.get("sourceBuilding") or "edificio_1"
    node_ids = [n["id"] for n in data["nodes"] if building.get(n["id"]) == edificio]
    element_ids = [e["id"] for e in data["elements"] if e.get("sourceBuilding") == edificio]
    casos = []
    for nid in (elem["nodeI"], elem["nodeJ"]):
        for dof in range(6):
            load = [0.0] * 6
            load[dof] = 1.0
            res = cvm.run_and_extract(data, {nid: load})
            disp = []
            for n in node_ids:
                d = res["displacements"].get(n, {})
                disp += [_sig(d.get(k, 0.0)) for k in ("ux", "uy", "uz")]
            forces = []
            for e in element_ids:
                f = list(res["element_forces"].get(e, [0.0] * 12))[:12]
                forces += [_sig(v) for v in f + [0.0] * (12 - len(f))]
            sum_r = [sum(r[k] for r in res["per_node_reactions"].values()) for k in range(3)]
            casos.append({"node": nid, "dof": dof, "sumR": [_sig(v) for v in sum_r],
                          "disp": disp, "forces": forces, "_res": res})
    ni, nj = nodes[elem["nodeI"]], nodes[elem["nodeJ"]]
    length = math.dist((ni["x"], ni["y"], ni["z"]), (nj["x"], nj["y"], nj["z"]))
    return {
        "element": elem["id"], "tag": elem.get("elementTag", str(elem["id"])), "type": elem.get("type", ""),
        "edificio": edificio, "nodeI": elem["nodeI"], "nodeJ": elem["nodeJ"], "length": length,
        "nodeIds": node_ids, "elementIds": element_ids, "unitCases": casos,
    }


def cargas_equivalentes(data, elem, a, P, u):
    """Fuerzas de empotramiento de una carga puntual P (direccion global u) en a."""
    nodes = cvm.node_map(data)
    ni, nj = nodes[elem["nodeI"]], nodes[elem["nodeJ"]]
    d = [nj[k] - ni[k] for k in ("x", "y", "z")]
    L = math.sqrt(sum(v * v for v in d))
    d = [v / L for v in d]
    b = L - a
    pa = P * sum(ui * di for ui, di in zip(u, d))
    t = [ui - (pa / P) * di for ui, di in zip(u, d)] if P else [0.0] * 3
    tn = math.sqrt(sum(v * v for v in t))
    pt = P * tn
    t = [v / tn for v in t] if tn > 1e-12 else [0.0] * 3
    ax = [d[1] * t[2] - d[2] * t[1], d[2] * t[0] - d[0] * t[2], d[0] * t[1] - d[1] * t[0]]   # d x t
    fi = [pa * b / L * di + pt * b * b * (3 * a + b) / L ** 3 * ti for di, ti in zip(d, t)]
    fj = [pa * a / L * di + pt * a * a * (a + 3 * b) / L ** 3 * ti for di, ti in zip(d, t)]
    mi = [pt * a * b * b / L ** 2 * v for v in ax]
    mj = [-pt * a * a * b / L ** 2 * v for v in ax]
    return fi + mi, fj + mj


def validar(data, elem, casos):
    """Carga puntual de 50 kN a 0.37 L en -Z y en X: combinacion vs analisis directo."""
    nodes = cvm.node_map(data)
    ni, nj = nodes[elem["nodeI"]], nodes[elem["nodeJ"]]
    L = casos["length"]
    for nombre, u in (("-Z", [0.0, 0.0, -1.0]), ("X", [1.0, 0.0, 0.0]), ("Y", [0.0, 1.0, 0.0])):
        a = 0.37 * L
        qi, qj = cargas_equivalentes(data, elem, a, 50.0, u)
        coef = {(elem["nodeI"], k): qi[k] for k in range(6)}
        coef.update({(elem["nodeJ"], k): qj[k] for k in range(6)})
        ref = copy.deepcopy(data)
        nid = max(n["id"] for n in ref["nodes"]) + 1
        t = a / L
        ref["nodes"].append({"id": nid, **{k: ni[k] + t * (nj[k] - ni[k]) for k in ("x", "y", "z")}})
        e_ref = next(e for e in ref["elements"] if e["id"] == elem["id"])
        nuevo = dict(e_ref, id=max(e["id"] for e in ref["elements"]) + 1, nodeI=nid)
        e_ref["nodeJ"], nuevo["nodeJ"] = nid, e_ref["nodeJ"]
        ref["elements"].append(nuevo)
        # el nodo nuevo pertenece al diafragma de su piso si esta a la cota del piso
        directo = cvm.run_and_extract(ref, {nid: [50.0 * v for v in u]})
        err = 0.0
        for n in casos["nodeIds"]:
            for k in ("ux", "uy", "uz"):
                comb = sum(c * casos["unitCases"][6 * (0 if key[0] == elem["nodeI"] else 1) + key[1]]["_res"]
                           ["displacements"].get(n, {}).get(k, 0.0) for key, c in coef.items())
                err = max(err, abs(comb - directo["displacements"].get(n, {}).get(k, 0.0)))
        sum_r = [sum(r[k] for r in directo["per_node_reactions"].values()) for k in range(3)]
        print(f"  {nombre}: err desplazamiento max = {err:.2e} m | suma reacciones = "
              f"({sum_r[0]:.4f}, {sum_r[1]:.4f}, {sum_r[2]:.4f}) kN")


def main():
    parser = argparse.ArgumentParser(description="Casos unitarios de un elemento para cargas en Unity.")
    parser.add_argument("--element", required=True, help="id o elementTag del elemento")
    parser.add_argument("--out", help="archivo JSON de salida")
    parser.add_argument("--validar", action="store_true", help="comparar con analisis directo")
    args = parser.parse_args()

    data = cvm.load_json(cvm.JSON_PATH)
    elem = buscar_elemento(data, args.element)
    if elem is None:
        print(json.dumps({"error": f"No existe el elemento '{args.element}'"}))
        if args.out:
            Path(args.out).write_text(json.dumps({"error": f"No existe el elemento '{args.element}'"}), encoding="utf-8")
        sys.exit(2)

    casos = casos_unitarios(data, elem)
    if args.validar:
        validar(data, elem, casos)
    for c in casos["unitCases"]:
        c.pop("_res", None)
    if args.out:
        Path(args.out).write_text(json.dumps(casos, separators=(",", ":")), encoding="utf-8")
        print(f"OK {casos['tag']} -> {args.out}")


if __name__ == "__main__":
    main()
