#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Añade arriostres diagonales a los voladizos del JSON Unity P1L4.

Inserta elementos de tipo "arriostre" (seccion 30x45) conectando en diagonal
las columnas de los dos voladizos del modelo:

  * Voladizo X+ (elevadores, losa superior z=12..16, planos x=37.55 y x=40).
  * Voladizo Y- (marco exterior y=-11.37, vanos 0..7.51 y 10..20).

Uso:
  python P1L4/anadir_arriostres_unity.py
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
JSON_UNITY = BASE_DIR / "edificio_G4" / "Assets" / "Resources" / "estructura_p1l4_unity.json"

# (x, y, z) de extremos: diagonales A LO LARGO del voladizo (desde la columna
# del marco interior hasta el borde exterior de la losa volada).
PAREJAS = [
    # Y- voladizo (proyeccion -Y, marco interior y=-7.25 -> borde y=-11.37)
    ((0.00, -7.25, 4.00), (0.00, -11.37, 8.00)),
    ((10.00, -7.25, 12.00), (10.00, -11.37, 16.00)),
    ((20.00, -7.25, 12.00), (20.00, -11.37, 16.00)),
    # X+ voladizo ascensores (proyeccion +X, marco interior x=35 -> borde x=40)
    ((35.00, 8.90, 12.00), (37.55, 8.90, 16.00)),
    ((37.55, 8.90, 12.00), (40.00, 8.90, 16.00)),
    ((35.00, 0.00, 12.00), (37.55, 0.00, 16.00)),
    ((37.55, 0.00, 12.00), (40.00, 0.00, 16.00)),
    ((35.00, -7.25, 12.00), (37.55, -7.25, 16.00)),
    ((37.55, -7.25, 12.00), (40.00, -7.25, 16.00)),
]

# Sentido contrario de cada diagonal (celosia en cruz por vano).
# Nota: el usuario pidio ponerla en EL OTRO COSTADO del voladizo Y- inferior
# (plano x=7.51, losa z4-8).
PAREJAS_INVERSAS = [
    ((7.51, -11.37, 4.00), (7.51, -7.25, 8.00)),
]


def key(x, y, z, tol=0.01):
    return (round(x, 2), round(y, 2), round(z, 2))


def main():
    data = json.loads(JSON_UNITY.read_text(encoding="utf-8"))

    # Limpieza previa: elimina arriostres existentes del mismo tipo
    antes = len(data.get("elements", []))
    data["elements"] = [e for e in data.get("elements", []) if e.get("type") != "arriostre"]
    eliminados = antes - len(data["elements"])
    if eliminados:
        print(f"  Se eliminaron {eliminados} arriostres previos.")

    node_index = {}
    for n in data.get("nodes", []):
        node_index[key(n["x"], n["y"], n["z"])] = n["id"]

    piso_by_node = {}
    for e in data.get("elements", []):
        for nd in (e.get("nodeI"), e.get("nodeJ")):
            piso_by_node.setdefault(nd, e.get("piso", ""))

    max_id = max((int(e["id"]) for e in data.get("elements", [])), default=0)

    added = 0
    for i, (a, b) in enumerate(PAREJAS + PAREJAS_INVERSAS, start=1):
        nid_a = node_index.get(key(*a))
        nid_b = node_index.get(key(*b))
        if nid_a is None or nid_b is None:
            print(f"  AVISO: nodos no encontrados para {a} -> {b}; se omite.")
            continue

        piso = piso_by_node.get(nid_a) or piso_by_node.get(nid_b) or ""
        data["elements"].append({
            "id": max_id + added + 1,
            "nodeI": nid_a,
            "nodeJ": nid_b,
            "type": "arriostre",
            "sectionId": "V30/45",
            "seccion": "V30/45",
            "elementTag": "ARRIOSTRE-{:03d}".format(i),
            "piso": piso,
            "width_m": 0.30,
            "height_m": 0.45,
            "sourceBuilding": "edificio_1",
            "sourceId": "arriostre_{:03d}".format(i),
        })
        added += 1
        print(f"  Arriostre {i}: nodos {nid_a} -> {nid_b}  ({float(a[0]):0.2f},{float(a[1]):0.2f},z{float(a[2]):0.0f}) a ({float(b[0]):0.2f},{float(b[1]):0.2f},z{float(b[2]):0.0f}))")

    JSON_UNITY.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Listo: {added} arriostres añadidos a {JSON_UNITY.name}.")


if __name__ == "__main__":
    main()