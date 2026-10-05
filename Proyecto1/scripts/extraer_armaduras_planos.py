#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Armaduras longitudinales reales de las vigas, leidas de las elevaciones DXF -> data/armaduras_planos.json.

Cada elevacion de eje (laminas 2017_67-300..310 y 2024_22-300..305) es un bloque con:
  - burbujas de los ejes perpendiculares (texto en capa *EJE*),
  - marcas de nivel (bloque "nivel-el", atributo %%P0.00 = cota del plano),
  - marcas de barra: un INSERT por grupo de barras con atributos NUM (cantidad), DIAM [mm],
    TEXTO_FE1 (L=largo [cm]), TEXTO_FE2 ("(2°C)" = capa) y MINUS ("-" = barra inferior). La
    geometria del bloque de la marca es la propia barra: de x_insercion a x_insercion + largo.

El script ajusta la coordenada horizontal del bloque a la del modelo con las burbujas (minimos
cuadrados contra data/ejes_grilla.json), asigna cada barra al piso de la marca de nivel que tiene
encima (z modelo = cota plano + 4.01) y guarda por elevacion la lista de barras en coordenadas del
modelo. capacidad_ha.py usa estas barras seccion por seccion en las vigas de esos ejes.

Los DXF no estan en el repositorio (carpeta ../Planos_1_dxf); el JSON generado si.

Uso:
  python -X utf8 Proyecto1/scripts/extraer_armaduras_planos.py [--planos RUTA]
"""
import argparse
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
OUT = ROOT_DIR / "data" / "armaduras_planos.json"
EJES = ROOT_DIR / "data" / "ejes_grilla.json"
PLANOS_DEFAULT = ROOT_DIR.parent.parent / "Planos_1_dxf"

LAMINAS = {
    "edificio_1": ["2017_67-300", "2017_67-301", "2017_67-302", "2017_67-303", "2017_67-304", "2017_67-305",
                   "2017_67-306", "2017_67-307", "2017_67-308", "2017_67-309", "2017_67-310"],
    "edificio_2": ["2024_22-300", "2024_22-301", "2024_22-302", "2024_22-303", "2024_22-304", "2024_22-305"],
}
Z_MODELO = (0.0, 3.96, 7.92, 11.88, 15.84)
DZ_PLANO = 4.01            # z modelo = cota plano + 4.01 (cielo 1S del plano en -4.01)
FILA_MAX_CM = 130.0        # una barra pertenece a la marca de nivel que tiene encima, a menos de esto


def texto(e):
    return (e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text).strip()


def capa_real(e):
    """Nombre de la capa sin el prefijo del bloque ("EJE 3$0$RLA-EJE" -> "RLA-EJE")."""
    return e.dxf.layer.split("$")[-1].upper()


def attribs(e):
    return {a.dxf.tag: a.dxf.text for a in e.attribs} if e.dxftype() == "INSERT" and e.attribs else {}


def extension_barra(doc, nombre, cache):
    """Extremos horizontales [cm, coordenadas del bloque de la marca] de la barra (sin ganchos)."""
    if nombre not in cache:
        xs = []
        for s in doc.blocks[nombre]:
            if s.dxftype() == "LINE" and abs(s.dxf.start.y - s.dxf.end.y) < 0.5 and abs(s.dxf.start.x - s.dxf.end.x) > 1:
                xs += [s.dxf.start.x, s.dxf.end.x]
        cache[nombre] = (min(xs), max(xs)) if xs else None
    return cache[nombre]


def capa(a):
    m = re.search(r"\((\d)\s*°?\s*C\)", a.get("TEXTO_FE2", "") or "")
    return int(m.group(1)) if m else 1


ESCALA_M_POR_CM = 0.01     # los bloques de elevacion estan en cm: 1 unidad = 0.01 m
TOL_ESCALA = 0.05


def burbujas_consistentes(unicas):
    """Mayor subconjunto de burbujas {eje: (x_bloque, coord_modelo)} cuyas distancias entre vecinas
    calzan con la escala del dibujo (0.01 m/cm +-5 %): las burbujas de ejes vecinos (E y E',
    F y F') se dibujan corridas para no montarse y deforman el mapeo si se usan."""
    from itertools import combinations
    items = sorted(unicas.items(), key=lambda kv: kv[1][0])
    for k in range(len(items), 1, -1):
        for sub in combinations(items, k):
            pend = [(q1 - q0) / (p1 - p0) for (_, (p0, q0)), (_, (p1, q1)) in zip(sub, sub[1:]) if p1 != p0]
            if len(pend) == k - 1 and all(abs(abs(m) - ESCALA_M_POR_CM) <= TOL_ESCALA * ESCALA_M_POR_CM for m in pend)                     and len({m > 0 for m in pend}) == 1:
                return dict(sub)
    return {}


def mapeo_por_tramos(pares):
    """Coordenada del bloque -> modelo interpolando entre burbujas consecutivas.
    Las elevaciones acortan algunos vanos (p. ej. E-F del eje 2 dibujado con 954 cm para 10 m),
    asi que un ajuste lineal unico deja errores de hasta ~0.9 m; por tramos el error en las
    burbujas es cero. Fuera de las burbujas extremas se extrapola con la pendiente del tramo vecino.
    Devuelve (funcion, pendientes por tramo)."""
    pts = sorted(pares)
    pend = [(q1 - q0) / (p1 - p0) for (p0, q0), (p1, q1) in zip(pts, pts[1:])]

    def f(x):
        if x <= pts[0][0]:
            return pts[0][1] + pend[0] * (x - pts[0][0])
        for (p0, q0), (p1, q1), m in zip(pts, pts[1:], pend):
            if x <= p1:
                return q0 + m * (x - p0)
        return pts[-1][1] + pend[-1] * (x - pts[-1][0])
    return f, pend


def columnas_modelo(edificio, direccion):
    """Posiciones (x, y) de las columnas del modelo de un edificio y de los muros perpendiculares a una
    linea de direccion 'x'|'y' (su posicion a lo largo de la linea es la del muro). Los muros paralelos
    a la linea no sirven de ancla: su nodo es el centro del muro, y en la elevacion A' (muros e=60)
    las caras interiores dibujadas se tomaban como una columna en ese centro (error de hasta 0.5 m)."""
    data = json.loads((ROOT_DIR / "data" / "estructura_completo_unity.json").read_text(encoding="utf-8"))
    nodes = {nd["id"]: nd for nd in data["nodes"]}
    paralelo = "X" if direccion == "x" else "Y"
    return {(round(nodes[e["nodeI"]]["x"], 3), round(nodes[e["nodeI"]]["y"], 3)) for e in data["elements"]
            if (e.get("sourceBuilding") or "edificio_1") == edificio
            and (e.get("type") == "columna" or (e.get("type") == "muro" and e.get("wallInPlaneAxis", "X") != paralelo))}


def extremos_muros_modelo(edificio):
    """(direccion de la linea 'x'|'y', coord de la linea, s0, s1) de cada muro del modelo."""
    data = json.loads((ROOT_DIR / "data" / "estructura_completo_unity.json").read_text(encoding="utf-8"))
    nodes = {nd["id"]: nd for nd in data["nodes"]}
    out = set()
    for e in data["elements"]:
        if e.get("type") == "muro" and (e.get("sourceBuilding") or "edificio_1") == edificio:
            a = nodes[e["nodeI"]]
            L = float(e["height_m"])
            if e.get("wallInPlaneAxis") == "X":
                out.add(("x", round(a["y"], 3), round(a["x"] - L / 2, 3), round(a["x"] + L / 2, 3)))
            else:
                out.add(("y", round(a["x"], 3), round(a["y"] - L / 2, 3), round(a["y"] + L / 2, 3)))
    return out


def sentido_por_muros(blk, bx, mc, direccion, coords_linea, edificio):
    """Sentido (+1/-1) de la coordenada del modelo a lo largo del bloque cuando hay una sola burbuja:
    el que lleva los bordes verticales dibujados del muro a los extremos de los muros del modelo."""
    bordes = sorted({round(e.dxf.start.x, 1) for e in blk if e.dxftype() == "LINE" and "CONTORNO" in capa_real(e)
                     and abs(e.dxf.start.x - e.dxf.end.x) < 0.5 and abs(e.dxf.start.y - e.dxf.end.y) > 150})
    extremos = [v for d, c, s0, s1 in extremos_muros_modelo(edificio) if d == direccion
                and any(abs(c - q) < 0.3 for q in coords_linea) for v in (s0, s1)]
    if not bordes or not extremos:
        return None, None
    mejor = (None, None)
    for sentido in (1, -1):
        errs = sorted(min(abs(mc + sentido * ESCALA_M_POR_CM * (x - bx) - v) for v in extremos) for x in bordes)
        buenos = [e for e in errs if e < 0.3]
        if len(buenos) >= 2:
            err = sum(buenos) / len(buenos)
            if mejor[0] is None or (len(buenos), -err) > (mejor[2], -mejor[1]):
                mejor = (sentido, err, len(buenos))
    return (mejor[0], mejor[1]) if mejor[0] is not None else (None, None)


def columnas_dibujadas(blk):
    """Centros [cm del bloque] de columnas dibujadas: pares de caras verticales largas a 25-75 cm."""
    xs = sorted({round(e.dxf.start.x, 1) for e in blk if e.dxftype() == "LINE" and "CONTORNO" in capa_real(e)
                 and abs(e.dxf.start.x - e.dxf.end.x) < 0.5 and abs(e.dxf.start.y - e.dxf.end.y) > 150})
    return [(a + b) / 2 for a, b in zip(xs, xs[1:]) if 25 <= b - a <= 75]


def anclar_a_columnas(blk, mapa, direccion, coords_linea, cols):
    """Pares (centro de columna dibujada, coordenada de la columna del modelo) sobre la linea del eje.
    Las burbujas de ejes vecinos se dibujan a veces desplazadas para no montarse (en el eje 2 la
    burbuja E queda 46 cm al lado de la columna E), asi que el mapeo final pasa por las columnas,
    que son geometria a escala; las burbujas solo identifican cual columna es cual."""
    sobre = sorted({c[0] if direccion == "x" else c[1] for c in cols
                    if any(abs((c[1] if direccion == "x" else c[0]) - v) < 0.5 for v in coords_linea)})
    mejor = {}
    for c in columnas_dibujadas(blk):
        m = mapa(c)
        if not sobre:
            break
        v = min(sobre, key=lambda q: abs(q - m))
        if abs(v - m) < 1.2 and (v not in mejor or abs(mapa(mejor[v]) - v) > abs(m - v)):
            mejor[v] = c
    return sorted((c, v) for v, c in mejor.items())


def piso_de(y, niveles):
    """(z modelo del cielo del piso, y_inferior, y_superior) del piso que contiene la altura y del bloque."""
    ys = sorted(niveles)
    for (y0, v0), (y1, v1) in zip(ys, ys[1:]):
        if y0 <= y < y1:
            z = min(Z_MODELO, key=lambda zz: abs(zz - (v1 + DZ_PLANO)))
            if abs(z - (v1 + DZ_PLANO)) <= 0.2:
                return z, y0, y1
            return None
    return None


def extraer_muros(doc, blk, mapa, niveles, cache):
    """Armadura de los muros de la elevacion, por piso:
      - mallas: bloque "M.H.A. e= / D.M. H.φ / V.φ" con atributos ESPESOR, MALLA_2 (horizontal) y
        MALLA_3 (vertical), p. ej. "10a20" = φ10 @ 20 cm en cada cara (doble malla);
      - barras verticales (marcas de barra rotadas 90/270°): las de las puntas del muro.
    Una barra vertical cuenta en un piso si pasa por la mitad de su altura."""
    mallas, verticales = [], []
    for e in blk:
        at = attribs(e)
        if "MALLA_3" in at or "MALLA_2" in at or "MALLA_1" in at:
            # bloque dinamico con dos estados de visibilidad: "D.M. φ[MALLA_1]" (misma malla en ambas
            # direcciones) o "D.M. H.φ[MALLA_2] / V.φ[MALLA_3]"; si H/V estan llenos mandan ellos
            m1 = (at.get("MALLA_1") or "").strip()
            mv = (at.get("MALLA_3") or "").strip() or m1
            mh = (at.get("MALLA_2") or "").strip() or m1
            p = piso_de(e.dxf.insert.y, niveles)
            if p and mv:
                mallas.append({"z": p[0], "s": round(mapa(e.dxf.insert.x), 3), "espesor_cm": (at.get("ESPESOR") or "").strip(),
                               "malla_h": mh, "malla_v": mv, "n_mallas": 2, "rotulo": "bloque"})
        elif at.get("DIAM") and abs(abs(e.dxf.get("rotation", 0.0)) % 180.0 - 90.0) < 1.0:
            ext = extension_barra(doc, e.dxf.name, cache)
            if ext is None:
                continue
            rot = e.dxf.get("rotation", 0.0) % 360.0
            y = e.dxf.insert.y
            ya, yb = (y + ext[0], y + ext[1]) if abs(rot - 90.0) < 1.0 else (y - ext[1], y - ext[0])
            for (y0, v0), (y1, v1) in zip(sorted(niveles), sorted(niveles)[1:]):
                ym = 0.5 * (y0 + y1)
                if ya <= ym <= yb:
                    z = min(Z_MODELO, key=lambda zz: abs(zz - (v1 + DZ_PLANO)))
                    if abs(z - (v1 + DZ_PLANO)) <= 0.2:
                        verticales.append({"z": z, "s": round(mapa(e.dxf.insert.x), 3),
                                           "n": int(re.sub(r"\D", "", at.get("NUM", "0")) or 0), "d": int(at["DIAM"])})
    mallas += mallas_texto(blk, mapa, niveles)
    return {"mallas": mallas, "verticales": verticales}


N_MALLAS = {"D": 2, "T": 3}


def mallas_texto(blk, mapa, niveles):
    """Rotulos de malla escritos como texto suelto (no como bloque): "M.H.A. e=60" y al lado
    "4.M. %%C10a20" (4 mallas, 2 por cara) o "T.M." / "D.M." con "H.%%C12a10" y "V.%%C12a20" cerca.
    D.M. = doble malla (1 por cara), T.M. = triple, n.M. = n mallas."""
    textos = [(texto(e), e.dxf.insert.x, e.dxf.insert.y) for e in blk if e.dxftype() in ("TEXT", "MTEXT")]
    cerca = lambda x, y, r: sorted(((abs(ux - x) + abs(uy - y), u, ux, uy) for u, ux, uy in textos
                                    if 0 < abs(ux - x) + abs(uy - y) <= r), key=lambda q: q[0])
    out = []
    for t, x, y in textos:
        me = re.match(r"M\.H\.A\.\s*e\s*=\s*(\d+)", t)
        if not me:
            continue
        rot = [q for q in cerca(x, y, 45) if re.match(r"(D|T|\d)\.M\.", q[1])]
        if not rot:
            continue
        _, u, ux, uy = rot[0]
        k = u[0]
        n = N_MALLAS.get(k) or int(k)
        dir_ = re.search(r"(\d{1,2}\s*a\s*\d{1,3})", u)
        hv = {q[1][0]: re.search(r"(\d{1,2}\s*a\s*\d{1,3})", q[1]).group(1) for q in cerca(ux, uy, 60)
              if re.match(r"[HV]\.\s*(%%C|φ)\s*\d{1,2}\s*a\s*\d{1,3}", q[1])}
        mv = hv.get("V") or (dir_.group(1) if dir_ else "")
        mh = hv.get("H") or (dir_.group(1) if dir_ else "")
        p = piso_de(y, niveles)
        if p and mv:
            out.append({"z": p[0], "s": round(mapa(x), 3), "espesor_cm": me.group(1), "malla_h": mh.replace(" ", ""),
                        "malla_v": mv.replace(" ", ""), "n_mallas": n, "rotulo": "texto"})
    return out


def elevaciones(doc, plano, edificio, ejes_coord, log):
    msp = doc.modelspace()
    vistos = set()
    out = []
    por_minuscula = {k.lower(): k for k in ejes_coord}
    titulos_hoja = {}
    for ins in msp.query("INSERT"):
        blk = doc.blocks.get(ins.dxf.name)
        if blk is not None:
            t = [texto(e) for e in blk if e.dxftype() in ("TEXT", "MTEXT") and "ELEVACI" in texto(e).upper()]
            if t:
                titulos_hoja.setdefault(t[0], set()).add(ins.dxf.name)
    for ins in msp.query("INSERT"):
        blk = doc.blocks.get(ins.dxf.name)
        if blk is None or ins.dxf.name in vistos:
            continue
        marcas = [e for e in blk if e.dxftype() == "INSERT" and attribs(e).get("DIAM")]
        if not marcas:
            continue
        vistos.add(ins.dxf.name)
        titulos = [texto(e) for e in blk if e.dxftype() in ("TEXT", "MTEXT") and "ELEVACI" in texto(e).upper()]
        m = re.search(r"EJES?\s+([A-Za-z0-9'\- ]+)", titulos[0]) if titulos else None
        nombre_eje = m.group(1).strip() if m else ins.dxf.name
        if titulos and len(titulos_hoja.get(titulos[0], ())) > 1:      # titulo repetido (EJEEb y EJEEc dicen "Ec")
            nombre_eje = re.sub(r"^EJE\s*", "", ins.dxf.name)
        lineas = [por_minuscula[s.strip().lower()] for s in re.split(r"[-,]", nombre_eje) if s.strip().lower() in por_minuscula]
        if not lineas:
            log.append(f"{plano} {nombre_eje}: eje secundario sin coordenada en ejes_grilla.json, se omite")
            continue
        dir_linea = ejes_coord[lineas[0]][0]          # "x": eje paralelo a X (numeros); "y": paralelo a Y (letras)
        # burbujas: centro del CIRCULO (el punto de insercion del texto depende de su alineacion) y su
        # nombre (texto mas cercano). Solo ejes principales: los secundarios (E', F'...) se dibujan
        # desplazados para no montarse sobre el principal y no sirven para la escala.
        # los circulos y textos pueden estar sueltos en el bloque o dentro de bloques de grilla
        # ("Grid - RLE-EJE..."), cuyo punto de insercion no coincide con la linea del eje
        circulos, textos_eje = [], []
        for e in blk:
            if "EJE" not in capa_real(e):
                continue
            if e.dxftype() == "INSERT":
                partes = list(e.virtual_entities())
                textos_eje += [(a.dxf.text.strip(), a.dxf.insert.x, a.dxf.insert.y) for a in (e.attribs or [])]
            else:
                partes = [e]
            for v in partes:
                if v.dxftype() == "CIRCLE":
                    circulos.append((v.dxf.center.x, v.dxf.center.y, v.dxf.radius))
                elif v.dxftype() in ("TEXT", "MTEXT"):
                    textos_eje.append((texto(v), v.dxf.insert.x, v.dxf.insert.y))
        unicas, secundarias = {}, {}
        for cx, cy, r in circulos:
            cerca = [(abs(tx - cx) + abs(ty - cy), t) for t, tx, ty in textos_eje if abs(tx - cx) <= 2 * r and abs(ty - cy) <= 2 * r]
            if not cerca:
                continue
            t = por_minuscula.get(min(cerca)[1].lower(), min(cerca)[1])
            if t in ejes_coord and ejes_coord[t][0] != dir_linea:
                (secundarias if ejes_coord[t][2] else unicas).setdefault(t, (cx, ejes_coord[t][1]))
        if len(unicas) < 2:          # elevaciones de muros del nucleo: solo tienen burbujas secundarias (Ea, Ed)
            unicas.update(secundarias)
        if len(unicas) == 1:
            # una sola burbuja (elevaciones de muros del nucleo): escala del dibujo + sentido que hace
            # calzar los bordes dibujados del muro con los extremos de los muros del modelo
            (t1, (bx1, mc1)), = unicas.items()
            sentido, err = sentido_por_muros(blk, bx1, mc1, dir_linea, [ejes_coord[t][1] for t in lineas], edificio)
            if sentido is None:
                log.append(f"{plano} {nombre_eje}: 1 burbuja y bordes de muro que no calzan con el modelo, se omite")
                continue
            unicas = {t1: (bx1, mc1), "_escala": (bx1 + 100.0, mc1 + sentido * 100.0 * ESCALA_M_POR_CM)}
            log.append(f"{plano} {nombre_eje}: 1 burbuja ({t1}) + escala 1 cm = 0.01 m, sentido {sentido:+d} (bordes de muro a {err:.2f} m)")
        if len(unicas) < 2:
            log.append(f"{plano} {nombre_eje}: menos de 2 burbujas conocidas, se omite")
            continue
        consistentes = burbujas_consistentes(unicas)
        if len(consistentes) < 2:
            log.append(f"{plano} {nombre_eje}: burbujas sin un par consistente con la escala del dibujo, se omite")
            continue
        descartadas = sorted(set(unicas) - set(consistentes))
        if descartadas:
            log.append(f"{plano} {nombre_eje}: burbujas desplazadas descartadas {descartadas}")
        unicas = consistentes
        mapa, pend = mapeo_por_tramos(list(unicas.values()))
        pares_col = anclar_a_columnas(blk, mapa, dir_linea, [ejes_coord[t][1] for t in lineas], columnas_modelo(edificio, dir_linea))
        correccion = max((abs(mapa(c) - v) for c, v in pares_col), default=0.0)
        if len(pares_col) >= 2:
            mapa_col, pend_col = mapeo_por_tramos(pares_col)
            if all(0.008 < abs(m) < 0.0125 for m in pend_col) and len({m > 0 for m in pend_col}) == 1:
                mapa, pend = mapa_col, pend_col
            else:
                log.append(f"{plano} {nombre_eje}: columnas inconsistentes, se usan las burbujas")
                pares_col = []
        niveles = []
        for e in blk:
            v = attribs(e).get("%%P0.00")
            if v:
                try:
                    niveles.append((e.dxf.insert.y, float(v.replace(",", "."))))
                except ValueError:
                    pass
        cache, barras, sin_piso = {}, [], 0
        for e in marcas:
            at = attribs(e)
            ext = extension_barra(doc, e.dxf.name, cache)
            if ext is None or abs(e.dxf.get("rotation", 0.0)) > 0.1 or abs(e.dxf.get("xscale", 1.0) - 1.0) > 1e-6:
                continue
            y = e.dxf.insert.y
            arriba = [(yl, v) for yl, v in niveles if 0.0 <= yl - y <= FILA_MAX_CM]
            if not arriba:
                sin_piso += 1
                continue
            yl, cota = min(arriba)
            z = min(Z_MODELO, key=lambda zz: abs(zz - (cota + DZ_PLANO)))
            if abs(z - (cota + DZ_PLANO)) > 0.2:
                sin_piso += 1                     # vigas de fundacion u otras cotas: no son del modelo
                continue
            s0, s1 = sorted((mapa(ext[0] + e.dxf.insert.x), mapa(ext[1] + e.dxf.insert.x)))
            # superior/inferior por la profundidad de la barra bajo la cara superior (off_cm): el
            # atributo MINUS no es confiable (bloques copiados). capacidad_ha la reclasifica con la
            # altura real de la viga; aqui se usa h = 80 cm solo como referencia.
            off = round(yl - y, 1)
            barras.append({
                "z": z, "pos": "sup" if off < 40.0 else "inf", "off_cm": off,
                "minus": (at.get("MINUS") or "").strip() == "-",
                "n": int(re.sub(r"\D", "", at.get("NUM", "0")) or 0), "d": int(at["DIAM"]), "capa": capa(at),
                "s0": round(s0, 3), "s1": round(s1, 3), "L_cm": at.get("TEXTO_FE1", ""),
            })
        # barras "explotadas": la marca quedo como textos sueltos ("2", "%%C", "22", "L=1200",
        # "(1°C)(40+1160)") y una linea horizontal. Inicio = linea suelta mas cercana a la etiqueta;
        # largo = tramo recto del rotulo (el mayor sumando de "(40+1160)", o L).
        textos_fe = [(texto(e), e.dxf.insert.x, e.dxf.insert.y) for e in blk
                     if e.dxftype() in ("TEXT", "MTEXT") and "FE" in capa_real(e)]
        lineas_fe = [(min(e.dxf.start.x, e.dxf.end.x), e.dxf.start.y) for e in blk
                     if e.dxftype() == "LINE" and "FE" in capa_real(e)
                     and abs(e.dxf.start.y - e.dxf.end.y) < 0.5 and abs(e.dxf.start.x - e.dxf.end.x) > 100]
        for t, tx, ty in textos_fe:
            if t != "%%C":
                continue
            fila = [(u, ux) for u, ux, uy in textos_fe if abs(uy - ty) < 3]
            num = [(tx - ux, u) for u, ux in fila if re.fullmatch(r"\+?\d+", u) and 0 < tx - ux < 40]
            dia = [(ux - tx, u) for u, ux in fila if re.fullmatch(r"\d{1,2}", u) and 0 < ux - tx < 30]
            lar = [(ux - tx, u) for u, ux in fila if u.startswith("L=") and 0 < ux - tx < 120]
            par = [(ux - tx, u) for u, ux in fila if u.startswith("(") and 0 < ux - tx < 250]
            if not (num and dia and lar and lineas_fe):
                continue
            rotulo = min(par)[1] if par else ""
            sumandos = [int(v) for v in re.findall(r"\d+", re.sub(r"\(\d\s*°?\s*C\)", "", rotulo))]
            recto = max(sumandos) if sumandos else int(re.sub(r"\D", "", min(lar)[1]))
            x0, yl_bar = min(lineas_fe, key=lambda q: abs(q[0] - (tx - 60)) + abs(q[1] - ty) * 0.5)
            arriba = [(yl, v) for yl, v in niveles if 0.0 <= yl - yl_bar <= 100]
            if not arriba:
                continue
            yl, cota = min(arriba)
            z = min(Z_MODELO, key=lambda zz: abs(zz - (cota + DZ_PLANO)))
            if abs(z - (cota + DZ_PLANO)) > 0.2:
                continue
            m = re.search(r"\((\d)\s*°?\s*C\)", rotulo)
            s0, s1 = sorted((mapa(x0), mapa(x0 + recto)))
            barras.append({"z": z, "pos": "inf" if yl - yl_bar > 40 else "sup", "off_cm": round(yl - yl_bar, 1), "n": int(min(num)[1].lstrip("+")),
                           "d": int(min(dia)[1]), "capa": int(m.group(1)) if m else 1,
                           "s0": round(s0, 3), "s1": round(s1, 3), "L_cm": min(lar)[1], "explotada": True})
        # "IDEM CIELO PISO n°": el piso no se dibuja y repite la armadura del cielo del piso n
        # (el texto viene partido: "IDEM CIELO" y debajo "PISO 1°")
        idem = []
        textos = [(texto(e).upper().replace("\n", " "), e.dxf.insert.x, e.dxf.insert.y) for e in blk
                  if e.dxftype() in ("TEXT", "MTEXT")]
        for t, tx, ty in textos:
            if "IDEM" not in t:
                continue
            mt = re.search(r"PISO\s*(\d)", t)
            if not mt:
                cerca = [(abs(ux - tx) + abs(uy - ty), re.search(r"PISO\s*(\d)", u)) for u, ux, uy in textos
                         if abs(ux - tx) < 60 and 0 < ty - uy < 40 and re.search(r"PISO\s*(\d)", u)]
                mt = min(cerca, key=lambda c: c[0])[1] if cerca else None
            arriba = [(yl, v) for yl, v in niveles if 0.0 <= yl - ty <= FILA_MAX_CM]
            if mt and arriba:
                destino = min(Z_MODELO, key=lambda zz: abs(zz - (min(arriba)[1] + DZ_PLANO)))
                idem.append((destino, Z_MODELO[int(mt.group(1))]))
        for destino, fuente in sorted(set(idem)):
            if not any(b["z"] == destino for b in barras):
                copia = [dict(b, z=destino, idem=f"cielo piso {Z_MODELO.index(fuente)}") for b in barras if b["z"] == fuente]
                barras += copia
                log.append(f"{plano} {nombre_eje}: z={destino} = IDEM z={fuente} ({len(copia)} grupos)")
        muros = extraer_muros(doc, blk, mapa, niveles, cache)
        if muros["mallas"] or muros["verticales"]:
            log.append(f"{plano} {nombre_eje}: muros -> {len(muros['mallas'])} mallas, {len(muros['verticales'])} grupos de barras verticales")
        out.append({
            "plano": plano, "bloque": ins.dxf.name, "muros": muros, "titulo": titulos[0] if titulos else "", "edificio": edificio,
            "direccion": dir_linea, "lineas": [{"eje": s, "coord": ejes_coord[s][1]} for s in lineas],
            "ajuste": {"burbujas": {t: [round(bx, 1), mc] for t, (bx, mc) in sorted(unicas.items())},
                       "escala_por_tramo_m_por_cm": [round(m, 5) for m in pend],
                       "anclaje": "columnas dibujadas" if len(pares_col) >= 2 else "burbujas",
                       "columnas": [[round(c, 1), v] for c, v in pares_col],
                       "correccion_max_vs_burbujas_m": round(correccion, 3)},
            "barras": barras, "omitidas_sin_piso": sin_piso,
        })
        log.append(f"{plano} {nombre_eje}: {len(barras)} grupos de barras ({len(unicas)} burbujas, {sin_piso} fuera de pisos del modelo; "
                   f"anclada a {len(pares_col)} columnas, correccion max vs burbujas {correccion:.2f} m)")
    return out


def main():
    parser = argparse.ArgumentParser(description="Armaduras de vigas desde las elevaciones DXF")
    parser.add_argument("--planos", type=Path, default=PLANOS_DEFAULT)
    args = parser.parse_args()
    import ezdxf
    ejes = json.loads(EJES.read_text(encoding="utf-8"))["ejes"]
    log, todas = [], []
    for edificio, laminas in LAMINAS.items():
        # direccion de la linea del eje: numeros = paralelos a X (coord = y); letras = paralelos a Y (coord = x)
        coord = {e["nombre"]: ("x" if e["direccion"] == "x" else "y", e["coord"], e["secundario"] or "'" in e["nombre"])
                 for e in ejes if e["edificio"] == edificio}
        for plano in laminas:
            path = args.planos / f"{plano}.dxf"
            if not path.exists():
                log.append(f"{plano}: no encontrado")
                continue
            doc = ezdxf.readfile(str(path))
            todas += elevaciones(doc, plano, edificio, coord, log)
    salida = {
        "descripcion": "Barras longitudinales de vigas leidas de las elevaciones DXF (scripts/extraer_armaduras_planos.py). "
                       "Por elevacion: eje(s), direccion ('x' = viga paralela a X), barras con piso z del modelo, "
                       "pos sup/inf, n x phi d [mm], capa y extension s0..s1 [m] en la coordenada del modelo a lo largo del eje.",
        "elevaciones": todas,
        "log": log,
    }
    OUT.write_text(json.dumps(salida, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(log))
    print(f"{len(todas)} elevaciones, {sum(len(e['barras']) for e in todas)} grupos de barras -> {OUT}")


if __name__ == "__main__":
    main()
