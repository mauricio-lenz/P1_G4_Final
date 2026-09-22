#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extrae indicadores comparables entre escenarios del JSON de Unity.

Uso:
    python P1L4/extraer_indicadores.py [ruta_json]

Indicadores:
- Desplazamiento horizontal maximo por combo (|dh| = sqrt(ux^2+uy^2))
- Demandas del muro 1 (index=1) por combo
- Corte basal (Q_kN_m2 y seismic_coefficient del escenario)
"""

import json
import math
import sys
from pathlib import Path

JSON_PATH = (Path(__file__).resolve().parent / "unity_visualizador"
             / "Assets" / "Resources" / "estructura_p1l4_unity.json")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else JSON_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    p1l4 = data.get("p1l4", {})

    print("=== Escenario ===")
    print(f"Q_kN_m2: {data.get('Q_kN_m2')} | sc: {data.get('seismic_coefficient')} | q_G: {data.get('q_G')}")

    print("\n=== Desplazamiento horizontal maximo por combo ===")
    for combo_name in ["C1", "C2", "C3"]:
        recs = [r for r in p1l4.get("displacements", []) if r["combo"] == combo_name]
        if not recs:
            print(f"{combo_name}: sin datos")
            continue
        best = max(recs, key=lambda r: math.hypot(r["ux"], r["uy"]))
        dh = math.hypot(best["ux"], best["uy"])
        print(f"{combo_name}: dh_max={dh:.6f} m (nodo {best['node']}, ux={best['ux']:.6f}, uy={best['uy']:.6f})")

    print("\n=== Muro 1 (index=1) demandas por combo ===")
    for wall in p1l4.get("wallRegistry", []):
        if wall.get("index") == 1:
            for d in wall.get("demands", []):
                print(f"{d['combo']}: P={d['P_kN']:.2f} kN | M={d['M_kN_m']:.2f} kN*m | V={d['V_kN']:.2f} kN")

    total_v = 0.0
    checksum = 0
    for rec in p1l4.get("displacements", []):
        checksum = (checksum + int(rec["node"]) * 7 + sum(abs(v) for v in (rec["ux"], rec["uy"], rec["uz"])) * 1e6) % (10 ** 8)
    print(f"\nChecksum displacement records: {checksum}")


if __name__ == "__main__":
    main()