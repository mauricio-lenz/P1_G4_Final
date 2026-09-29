#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sidequest semana 5: carga movil sobre un recorrido de vigas.

Regla fisica
    Una carga puntual vertical P (hacia abajo) recorre un camino recto de
    vigas de un piso; su posicion es s en [0, L_camino]. Dentro de la viga
    que la contiene (nodos A->B, largo L, a = s - s_A, b = L - a) la carga se
    reemplaza por sus fuerzas de empotramiento perfecto en los nodos:

        F_A = P b^2 (3a + b) / L^3        M_A = +P a b^2 / L^2
        F_B = P a^2 (a + 3b) / L^3        M_B = -P a^2 b / L^2

    con F hacia abajo y M en torno al eje z x d (d = direccion del camino).

Reparto (lineal y exacto)
    Como el modelo es elastico lineal, se precalcula con OpenSees la
    respuesta a cargas UNITARIAS en cada nodo del camino (Fz = -1 kN y
    M = 1 kN*m). Unity combina esos casos con los coeficientes de arriba para
    cualquier s y cualquier P (P es solo un factor de escala), asi la carga se
    mueve de forma continua sin volver a correr el analisis.

Conservacion
    F_A + F_B = P en la viga cargada y la suma de reacciones verticales de
    los apoyos es P; ademas se valida contra un analisis directo con la viga
    partida en el punto de carga.
"""

import copy
import math

P_DEFAULT_KN = 50.0

# Pisos (nombre, z) y edificios donde puede recorrer la carga (eje 2, y=0)
PISOS = [("CIELO_1S", 0.0), ("CIELO_1", 3.96), ("CIELO_2", 7.92), ("CIELO_3", 11.88), ("CIELO_4", 15.84)]
EDIFICIOS = [("E1", "Edificio 1", "edificio_1"), ("E2", "Edificio 2", "edificio_2")]

# Recorridos: (id, nombre, edificio, nivel, z del piso, eje fijo, coordenada del eje)
CAMINOS = [
    (f"{eid}_EJE2_{nivel}", f"{enom} · eje 2 · {nivel}", edificio, nivel, z, "y", 0.0)
    for eid, enom, edificio in EDIFICIOS
    for nivel, z in PISOS
]
VALIDACION_FRACCIONES = (0.13, 0.5, 0.81)   # posiciones de control (fraccion del camino)


def _close(a, b, tol=1e-3):
    return abs(a - b) < tol


def _sig(v, digits=5):
    return float(f"{v:.{digits}g}")


def armar_camino(data, edificio, z, eje, coord):
    """Vigas del camino ordenadas por la coordenada libre (x si eje='y')."""
    nodes = {n["id"]: n for n in data["nodes"]}
    libre = "x" if eje == "y" else "y"
    tramos = []
    for e in data["elements"]:
        if e.get("type") != "viga" or e.get("sourceBuilding") != edificio:
            continue
        ni, nj = nodes[e["nodeI"]], nodes[e["nodeJ"]]
        if not all(_close(n["z"], z) and _close(n[eje], coord) for n in (ni, nj)):
            continue
        a_node, b_node = sorted((ni, nj), key=lambda n: n[libre])
        tramos.append({"element": e["id"], "tag": e.get("elementTag", str(e["id"])),
                       "nodeA": a_node["id"], "nodeB": b_node["id"],
                       "s0": a_node[libre], "s1": b_node[libre]})
    if not tramos:
        raise RuntimeError(f"No hay vigas en {edificio} z={z} {eje}={coord}")
    tramos.sort(key=lambda t: t["s0"])
    origen = tramos[0]["s0"]
    for t in tramos:
        t["s0"] -= origen
        t["s1"] -= origen
    for prev, nxt in zip(tramos, tramos[1:]):
        if not _close(prev["s1"], nxt["s0"]) or prev["nodeB"] != nxt["nodeA"]:
            raise RuntimeError(f"Camino discontinuo entre {prev['tag']} y {nxt['tag']}")
    direccion = (1.0, 0.0) if eje == "y" else (0.0, 1.0)
    return tramos, origen, direccion


def coeficientes(tramos, s, P):
    """Fuerzas de empotramiento de la carga P en s -> {(nodo, 'F'|'M'): coef}."""
    s = min(max(s, 0.0), tramos[-1]["s1"])
    t = next(t for t in tramos if t["s0"] - 1e-9 <= s <= t["s1"] + 1e-9)
    L = t["s1"] - t["s0"]
    a = s - t["s0"]
    b = L - a
    return t, {
        (t["nodeA"], "F"): P * b * b * (3 * a + b) / L ** 3,
        (t["nodeB"], "F"): P * a * a * (a + 3 * b) / L ** 3,
        (t["nodeA"], "M"): P * a * b * b / L ** 2,
        (t["nodeB"], "M"): -P * a * a * b / L ** 2,
    }


def _carga_unitaria(tipo, direccion):
    if tipo == "F":
        return [0.0, 0.0, -1.0, 0.0, 0.0, 0.0]
    # momento unitario en torno a z x d
    ax, ay = -direccion[1], direccion[0]
    return [0.0, 0.0, 0.0, ax, ay, 0.0]


def _suma_rz(cvm, data, result):
    return sum(v[2] for v in result["per_node_reactions"].values())


def _referencia_directa(cvm, data, tramos, origen, direccion, eje, coord, z, s, P):
    """Analisis directo: parte la viga en el punto de carga y aplica P ahi."""
    t, _ = coeficientes(tramos, s, P)
    if abs(s - t["s0"]) < 1e-6 or abs(t["s1"] - s) < 1e-6:
        # la carga cae sobre un nodo: no se parte la viga
        nodo = t["nodeA"] if abs(s - t["s0"]) < 1e-6 else t["nodeB"]
        return cvm.run_and_extract(data, {nodo: [0.0, 0.0, -P]})
    ref = copy.deepcopy(data)
    elem = next(e for e in ref["elements"] if e["id"] == t["element"])
    nid = max(n["id"] for n in ref["nodes"]) + 1
    x = origen + s if eje == "y" else coord
    y = coord if eje == "y" else origen + s
    ref["nodes"].append({"id": nid, "x": x, "y": y, "z": z})
    nuevo = dict(elem, id=max(e["id"] for e in ref["elements"]) + 1, nodeI=nid)
    elem["nodeJ"], nuevo["nodeJ"] = nid, elem["nodeJ"]
    ref["elements"].append(nuevo)
    return cvm.run_and_extract(ref, {nid: [0.0, 0.0, -P]})


def construir(data, cvm):
    """Bloque 'cargaMovil' para el JSON de Unity."""
    # Los edificios estan separados por junta de dilatacion: la respuesta a
    # una carga en un edificio es nula en el otro, asi que cada recorrido
    # guarda solo los nodos y elementos de su edificio.
    building = cvm.node_buildings(data)
    caminos = []
    for cid, nombre, edificio, nivel, z, eje, coord in CAMINOS:
        node_order = [n["id"] for n in data["nodes"] if building.get(n["id"]) == edificio]
        element_order = [e["id"] for e in data["elements"] if e.get("sourceBuilding") == edificio]
        try:
            tramos, origen, direccion = armar_camino(data, edificio, z, eje, coord)
        except RuntimeError as exc:
            print(f"  Carga movil {cid}: se omite ({exc})")
            continue
        nodos = [tramos[0]["nodeA"]] + [t["nodeB"] for t in tramos]
        unit = {}
        casos = []
        for nid in nodos:
            for tipo in ("F", "M"):
                res = cvm.run_and_extract(data, {nid: _carga_unitaria(tipo, direccion)})
                unit[(nid, tipo)] = res
                disp = []
                for n in node_order:
                    d = res["displacements"].get(n, {})
                    disp += [_sig(d.get("ux", 0.0)), _sig(d.get("uy", 0.0)), _sig(d.get("uz", 0.0))]
                forces = []
                for e in element_order:
                    f = list(res["element_forces"].get(e, [0.0] * 12))[:12]
                    forces += [_sig(v) for v in f + [0.0] * (12 - len(f))]
                casos.append({"node": nid, "tipo": tipo, "sumRz": _sig(_suma_rz(cvm, data, res)),
                              "disp": disp, "forces": forces})

        # Validacion contra el analisis directo con la viga partida
        largo = tramos[-1]["s1"]
        checks = []
        for frac in VALIDACION_FRACCIONES:
            s = frac * largo
            _, coef = coeficientes(tramos, s, P_DEFAULT_KN)
            ref = _referencia_directa(cvm, data, tramos, origen, direccion, eje, coord, z, s, P_DEFAULT_KN)
            err_u = 0.0
            for n in node_order:
                comb = sum(c * unit[k]["displacements"].get(n, {}).get("uz", 0.0) for k, c in coef.items())
                err_u = max(err_u, abs(comb - ref["displacements"].get(n, {}).get("uz", 0.0)))
            rz_comb = sum(c * _suma_rz(cvm, data, unit[k]) for k, c in coef.items())
            rz_ref = _suma_rz(cvm, data, ref)
            checks.append({"s": round(s, 4), "sumRz_comb_kN": rz_comb, "sumRz_directo_kN": rz_ref,
                           "errDisp_m": err_u, "errReac_kN": abs(rz_comb - P_DEFAULT_KN)})
            print(f"  [{cid}] s={s:6.2f} m | sumRz={rz_comb:.6f} kN (P={P_DEFAULT_KN}) | "
                  f"directo={rz_ref:.6f} | err uz max={err_u:.2e} m")

        caminos.append({
            "id": cid, "nombre": nombre, "edificio": edificio, "nivel": nivel, "z": z,
            "nodeIds": node_order, "elementIds": element_order,
            "origen": {"x": origen if eje == "y" else coord, "y": coord if eje == "y" else origen},
            "dir": list(direccion), "largo": largo,
            "beams": [{"element": t["element"], "tag": t["tag"], "nodeA": t["nodeA"], "nodeB": t["nodeB"],
                       "s0": t["s0"], "s1": t["s1"]} for t in tramos],
            "unitCases": casos,
            "validacion": checks,
        })
        print(f"  Carga movil {cid}: {len(tramos)} vigas, L={largo:.2f} m, {len(casos)} casos unitarios")
    return {
        "P_default_kN": P_DEFAULT_KN,
        "paths": caminos,
        "nota": "Respuesta = sum(coef_k * caso_unitario_k); coef por fuerzas de empotramiento de P en s.",
    }
