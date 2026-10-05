#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ejes de grilla de los planos estructurales -> data/ejes_grilla.json.

Lee las burbujas de ejes (capa *EJE*) de las plantas DXF y las lleva a
coordenadas del modelo:
  - 2017_67 (edificio_1): x = (px - E)/100 - 10, y = (py - eje 2)/100, con E
    y eje 2 de cada planta (plantas 101, 102 y 103).
  - 2024_22 (edificio_2): misma escala en cm; cada eje se ajusta a la linea de
    columnas o muros del modelo mas cercana (diferencias de ~0.1 m entre la
    planta y el modelo); se reporta la diferencia. Los ejes D' y E' de esa
    planta quedan al otro lado de la junta (pertenecen a 2017_67) y se omiten.

Los planos DXF no estan en el repositorio (carpeta ../Planos_1_dxf); el JSON
generado si, y lo lee exportar_resultados_unity.py (capa "Ejes" del viewer).

Uso:
  python -X utf8 Proyecto1/scripts/generar_ejes_grilla.py [--planos RUTA]
"""
import argparse
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
OUT = ROOT_DIR / "data" / "ejes_grilla.json"
MODEL = ROOT_DIR / "data" / "estructura_completo_unity.json"
PLANOS_DEFAULT = ROOT_DIR.parent.parent / "Planos_1_dxf"

# (archivo, edificio, filtro de la planta por y del DXF, px del eje E o A', py del eje 2, x modelo del eje de referencia)
PLANTAS = [
    ("2017_67-101.dxf", "edificio_1", (0, 4970), "E", 1061.3, 2686.2, -10.0),        # cielo piso 1
    ("2017_67-101.dxf", "edificio_1", (4970, 9000), "E", 1061.3, 6293.3, -10.0),     # cielo 1S
    ("2017_67-102.dxf", "edificio_1", (0, 5000), "E", 535.0, 3388.5, -10.0),         # cielo 3
    ("2017_67-102.dxf", "edificio_1", (5000, 9000), "E", 893.2, 7013.1, -10.0),      # cielo 2
    ("2017_67-103.dxf", "edificio_1", (0, 9000), "E", 490.3, 5407.3, -10.0),         # cielo 4
    ("2024_22-101.dxf", "edificio_2", (0, 9000), "A'", 1096.5, 1829.7, -41.475),     # cielo 1S a 3
]
OMITIR_E2 = {"D'", "E'"}       # al otro lado de la junta de dilatacion
SECUNDARIOS = {"F'", "H'", "1'", "3'", "8", "B'"}
SNAP_E2 = 0.35                 # m


def burbujas(path, y_range):
    import ezdxf
    msp = ezdxf.readfile(str(path)).modelspace()
    out = []
    for e in msp.query("TEXT MTEXT"):
        t = (e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text).strip()
        if re.fullmatch(r"[A-Z]'?|\d{1,2}'?", t) and "EJE" in e.dxf.layer.upper():
            if y_range[0] <= e.dxf.insert.y < y_range[1]:
                out.append((t, e.dxf.insert.x, e.dxf.insert.y))
    return out


def lineas_modelo(edificio, eje):
    """Coordenadas x (eje "x") o y de columnas y muros del modelo de un edificio."""
    data = json.loads(MODEL.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in data["nodes"]}
    vals = set()
    for e in data["elements"]:
        if (e.get("sourceBuilding") or "edificio_1") == edificio and e.get("type") in ("columna", "muro"):
            vals.add(round(nodes[e["nodeI"]]["x" if eje == "x" else "y"], 3))
    return sorted(vals)


def main():
    parser = argparse.ArgumentParser(description="Ejes de grilla desde los planos DXF")
    parser.add_argument("--planos", type=Path, default=PLANOS_DEFAULT)
    args = parser.parse_args()

    ejes = {}   # (edificio, nombre) -> dict
    for archivo, edificio, y_range, ref, px_ref, py_2, x_ref in PLANTAS:
        for nombre, px, py in burbujas(args.planos / archivo, y_range):
            if edificio == "edificio_2" and nombre in OMITIR_E2:
                continue
            letra = nombre[0].isalpha()
            valor = (px - px_ref) / 100.0 + x_ref if letra else (py - py_2) / 100.0
            key = (edificio, nombre)
            if key not in ejes:
                ejes[key] = {"nombre": nombre, "edificio": edificio, "direccion": "y" if letra else "x",
                             "coord": round(valor, 3), "plano": archivo, "secundario": nombre in SECUNDARIOS}
    # edificio_2: ajuste a las lineas del modelo
    for (edificio, nombre), eje in ejes.items():
        if edificio != "edificio_2" or eje["direccion"] != "y":
            continue
        lineas = lineas_modelo(edificio, "x")
        cerca = min(lineas, key=lambda v: abs(v - eje["coord"]))
        if abs(cerca - eje["coord"]) <= SNAP_E2:
            eje["ajuste_m"] = round(cerca - eje["coord"], 3)
            eje["coord"] = cerca
    # extension de cada eje: entre los ejes extremos del edificio, con 1.5 m de margen
    for edificio in ("edificio_1", "edificio_2"):
        xs = [e["coord"] for (b, _), e in ejes.items() if b == edificio and e["direccion"] == "y" and not e["secundario"]]
        ys = [e["coord"] for (b, _), e in ejes.items() if b == edificio and e["direccion"] == "x" and not e["secundario"]]
        for (b, _), e in ejes.items():
            if b != edificio:
                continue
            lo, hi = (min(ys), max(ys)) if e["direccion"] == "y" else (min(xs), max(xs))
            e["desde"], e["hasta"] = round(lo - 1.5, 3), round(hi + 1.5, 3)
    salida = {
        "descripcion": "Ejes de grilla de los planos (burbujas de las plantas DXF) en coordenadas del modelo. "
                       "direccion 'y' = eje paralelo a Y (letras, coord = x); 'x' = paralelo a X (numeros, coord = y). "
                       "Generado por scripts/generar_ejes_grilla.py.",
        "ejes": sorted(ejes.values(), key=lambda e: (e["edificio"], e["direccion"], e["coord"])),
    }
    OUT.write_text(json.dumps(salida, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for e in salida["ejes"]:
        print(f"  {e['edificio']} eje {e['nombre']:<3} {'x' if e['direccion'] == 'y' else 'y'} = {e['coord']:8.3f}"
              f"{'  (secundario)' if e['secundario'] else ''}{'  ajuste ' + str(e['ajuste_m']) + ' m' if 'ajuste_m' in e else ''}")
    print(f"{len(salida['ejes'])} ejes -> {OUT}")


if __name__ == "__main__":
    main()
