#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verifica superposicion interactiva (Semana 5).

Compara, para las combinaciones C1/C2/C3, la suma ponderada de los casos
base G/Q/EX/EY con la corrida directa de OpenSees guardada en el JSON de
Unity. Usa los mismos coeficientes NCh433 que define el JSON.

Uso:
    python P1L4/verificar_superposicion.py [ruta_json]

Salida: error maximo por combinacion sobre fuerzas internas de TODOS los
elementos (12 componentes por elemento).
"""

import json
import sys
from pathlib import Path

JSON_PATH = (Path(__file__).resolve().parent / "unity_visualizador"
             / "Assets" / "Resources" / "estructura_p1l4_unity.json")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else JSON_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    p1l4 = data.get("p1l4", {})
    element_forces = p1l4.get("elementForces", [])
    combos = {c["name"]: c for c in p1l4.get("combinations", [])}

    casos = ["G", "Q", "EX", "EY"]
    for c in casos:
        if c not in combos:
            combos[c] = {"G": 1 if c == "G" else 0,
                         "Q": 1 if c == "Q" else 0,
                         "EX": 1 if c == "EX" else 0,
                         "EY": 1 if c == "EY" else 0}

    by_combo = {}
    for rec in element_forces:
        by_combo.setdefault(rec["combo"], {})[int(rec["id"])] = rec["f"]

    ids = set()
    for c in casos:
        ids.update(by_combo.get(c, {}).keys())

    print(f"Elementos con fuerzas por caso base: {len(ids)}")
    print(f"{'Combo':<5} {'Elementos':<10} {'err rel max (frac de |F|max compuesto|)':<20} {'err abs max (kN o kN*m)':<10}")
    for combo_name in ["C1", "C2", "C3"]:
        coef = combos.get(combo_name)
        if coef is None or combo_name not in by_combo:
            print(f"{combo_name}: sin datos")
            continue
        err_abs_max = 0.0
        err_rel_max = 0.0
        checked = 0
        fmax_global = 0.0
        for elem_id, direct in sorted(by_combo[combo_name].items()):
            if elem_id not in ids:
                continue
            ref = [0.0] * 12
            for caso in casos:
                vec = by_combo.get(caso, {}).get(elem_id, [0.0] * 12)
                lam = coef.get(caso, 0.0)
                for i in range(12):
                    ref[i] += lam * vec[i]
            fmax_global = max(fmax_global, max(abs(v) for v in ref))
            scale = max(abs(v) for v in ref) or 1.0
            per_el = 0.0
            for i in range(min(len(direct), 12)):
                e = abs(ref[i] - direct[i])
                if e > err_abs_max:
                    err_abs_max = e
                rel = e / scale
                if rel > per_el:
                    per_el = rel
            if per_el > err_rel_max:
                err_rel_max = per_el
            checked += 1
        rel_global = err_abs_max / fmax_global if fmax_global else 0.0
        print(f"{combo_name:<5} {checked:<10} {err_rel_max:<30.3e} {err_abs_max:<10.3e} {rel_global:<10.3e}")
        print(f"       expresion: {coef.get('G',0)}G+{coef.get('Q',0)}Q+{coef.get('EX',0)}EX+{coef.get('EY',0)}EY")

    # Tambien verificar demanda-capacidad: los puntos P-M de columna del
    # panel se calculan con estas mismas fuerzas (se reporta M resultante).
    curvas = p1l4.get("pmCurves", [])
    for curva in curvas:
        if curva.get("elementType") == "columna":
            print(f"\nCurva P-M columna: {curva['sectionId']} | puntos={len(curva.get('points', []))} | Po={curva.get('Po_kN')} kN")


if __name__ == "__main__":
    main()