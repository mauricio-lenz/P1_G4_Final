"""Validacion de las entradas del analisis (consola o Unity, Honors H4).

exportar_resultados_unity.py la llama antes de analizar: si algo no es valido
termina con codigo 2 y un mensaje "ERROR de validacion: ..." en stderr, que
Unity muestra tal cual en la pestana ANALISIS. Asi un valor fuera de rango o un
archivo mal escrito no llega a OpenSees ni produce un resultado silencioso.
"""
import json
import math
import re
from pathlib import Path

import capacidad_ha as cha

Q_MAX_KG_M2 = 5000.0        # sobrecarga de uso razonable (NCh1537: <= 1000 en bodegas)
QG_MAX_KN_M2 = 50.0
SECCION_MIN_M, SECCION_MAX_M = 0.10, 3.00
LAMBDA_MAX = 5.0
CASOS = ("G", "Q", "EX", "EY")


class ErrorValidacion(ValueError):
    """Una o mas entradas invalidas; el mensaje lista todas."""


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _leer_json(path, que, errores):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        errores.append(f"no existe el archivo de {que}: {path}")
    except json.JSONDecodeError as ex:
        errores.append(f"el archivo de {que} no es JSON valido ({path}, linea {ex.lineno}): {ex.msg}")
    return None


def validar_combinaciones(data, errores, origen="combinaciones"):
    combos = (data or {}).get("combinaciones")
    if not isinstance(combos, list) or not combos:
        errores.append(f"{origen}: falta la lista 'combinaciones' (al menos una)")
        return
    nombres = set()
    for i, c in enumerate(combos, start=1):
        nombre = str(c.get("name", "")).strip()
        if not nombre:
            errores.append(f"{origen}: la combinacion {i} no tiene nombre")
        elif nombre in nombres:
            errores.append(f"{origen}: nombre repetido '{nombre}'")
        elif nombre in CASOS:
            errores.append(f"{origen}: '{nombre}' es un caso base; usar otro nombre")
        nombres.add(nombre)
        for caso in CASOS:
            v = c.get(caso, 0.0)
            if not _num(v):
                errores.append(f"{origen}: {nombre or i}.{caso} no es un numero ({v!r})")
            elif abs(v) > LAMBDA_MAX:
                errores.append(f"{origen}: {nombre or i}.{caso} = {v} fuera de rango (|lambda| <= {LAMBDA_MAX})")


def validar_secciones(secciones, errores):
    for key, s in (secciones or {}).items():
        for campo in ("width_m", "height_m"):
            v = s.get(campo)
            if not _num(v) or not (SECCION_MIN_M <= v <= SECCION_MAX_M):
                errores.append(f"seccion de {key}: {campo} = {v!r} fuera de rango ({SECCION_MIN_M}-{SECCION_MAX_M} m)")


_CAMPOS_BARRAS = ("inferior", "superior", "supleApoyo", "barras")
_CAMPOS_ESTRIBOS = ("estribosApoyo", "estribosTramo", "estribos")


def validar_armaduras(data, errores):
    for grupo in ("secciones", "elementos"):
        for key, arm in ((data or {}).get(grupo) or {}).items():
            for campo, texto in (arm or {}).items():
                if campo in _CAMPOS_BARRAS and texto:
                    area, diams = cha.bars_area_mm2(texto)
                    resto = re.sub(r"\s|\+", "", cha._BARS.sub("", texto))
                    if area <= 0 or resto:
                        errores.append(f"armadura {key}.{campo} = '{texto}' no se entiende (usar 4f22, 4φ22 o 2f22+2f25)")
                    elif any(d < 8 or d > 36 for d in diams):
                        errores.append(f"armadura {key}.{campo} = '{texto}': diametro fuera de 8-36 mm")
                elif campo in _CAMPOS_ESTRIBOS and texto:
                    av, s, d = cha.stirrup(texto)
                    if av <= 0 or s <= 0:
                        errores.append(f"armadura {key}.{campo} = '{texto}' no se entiende (usar Ef10a10 o EDf10a20)")
                    elif not (50 <= s <= 400):
                        errores.append(f"armadura {key}.{campo} = '{texto}': espaciamiento {s:.0f} mm fuera de 50-400 mm")


def validar(q_kg_m2, q_cubierta_kg_m2, q_g, fisurada, sismo, secciones=None,
            combos_path=None, mods_path=None, armaduras_path=None):
    """Revisa todas las entradas; lanza ErrorValidacion con la lista de problemas."""
    errores = []
    for nombre, v in (("Q", q_kg_m2), ("Q cubierta", q_cubierta_kg_m2)):
        if not _num(v) or not (0.0 <= v <= Q_MAX_KG_M2):
            errores.append(f"{nombre} = {v!r} kg/m2 fuera de rango (0-{Q_MAX_KG_M2:.0f})")
    if q_g is not None and (not _num(q_g) or not (0.0 < q_g <= QG_MAX_KN_M2)):
        errores.append(f"q_G = {q_g!r} kN/m2 fuera de rango (0-{QG_MAX_KN_M2:.0f})")
    for tipo, k in (fisurada or {}).items():
        if not _num(k) or not (0.05 <= k <= 1.0):
            errores.append(f"rigidez fisurada {tipo} = {k!r} fuera de rango (0,05-1,0 x Ig)")
    if sismo.get("metodo") == "NCh433":
        if sismo.get("zona") not in (1, 2, 3):
            errores.append(f"zona sismica {sismo.get('zona')!r} invalida (1, 2 o 3)")
        if str(sismo.get("suelo", "")).upper() not in ("A", "B", "C", "D", "E"):
            errores.append(f"suelo {sismo.get('suelo')!r} invalido (A a E, DS61)")
        if not _num(sismo.get("R")) or not (1.0 <= sismo["R"] <= 11.0):
            errores.append(f"R = {sismo.get('R')!r} fuera de rango (1-11, NCh433 tabla 5.1)")
        if not _num(sismo.get("I")) or not (0.5 <= sismo["I"] <= 1.5):
            errores.append(f"I = {sismo.get('I')!r} fuera de rango (0,5-1,5)")
        if not _num(sismo.get("fraccionQ")) or not (0.0 <= sismo["fraccionQ"] <= 1.0):
            errores.append(f"fraccion de Q en el peso sismico = {sismo.get('fraccionQ')!r} fuera de 0-1")
    else:
        c = sismo.get("C")
        if not _num(c) or not (0.0 <= c <= 1.5):
            errores.append(f"coeficiente sismico C = {c!r} fuera de rango (0-1,5)")
    validar_secciones(secciones, errores)
    if combos_path is not None:
        data = _leer_json(combos_path, "combinaciones", errores)
        if data is not None:
            validar_combinaciones(data, errores)
    if mods_path is not None:
        data = _leer_json(mods_path, "modificaciones", errores)
        if data is not None:
            validar_secciones(data.get("sections"), errores)
    if armaduras_path is not None:
        data = _leer_json(armaduras_path, "armaduras", errores)
        if data is not None:
            validar_armaduras(data, errores)
    if errores:
        raise ErrorValidacion("; ".join(errores))
