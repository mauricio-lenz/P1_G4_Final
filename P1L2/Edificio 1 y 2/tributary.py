# ============================================================
# AREAS TRIBUTARIAS - Edificio de Ingenieria UANDES
# ============================================================
# Metodo de areas tributarias por losa segun relacion de lados b/a
# (opcion a: rectangulo envolvente del panel).
#
# Para cada panel de losa (lado corto "a", lado largo "b"):
#   - b/a < 2  -> losa EN DOS DIRECCIONES:
#       + cada lado corto recibe un TRIANGULO  de area a^2/4
#       + cada lado largo recibe un TRAPECIO    de area a(2b-a)/4
#       (suma = ab, conservacion exacta)
#   - b/a >= 2 -> losa EN UNA DIRECCION:
#       + solo los lados largos, cada uno recibe a*b/2 (rectangulo)
#       (los lados cortos no reciben carga)
#
# Cada area resultante se asigna a la(s) viga(s) de la malla que
# cubren ese borde del panel (prorrateo por largo cuando hay varias).
#
# La carga gravitacional q_G se define POR NIVEL (Q_G_BY_LEVEL):
#   CIELO_1S..CIELO_3 : 15.32 kN/m^2  (gobierna 1.2D+1.6L, 1562 kg/m2)
#   CIELO_4 (cubierta): 9.91 kN/m^2   (gobierna 1.2D+1.6L, 1010 kg/m2)
#
# Verificacion: Sigma(A_trib) = Sigma(A_losa analizada) con error 0,
# SIN factor de ajuste artificial.
# ============================================================
from math import hypot

from materials import Q_G_BY_LEVEL, Q_G


# ---------------------------------------------------------------
# Clasificacion de un panel
# ---------------------------------------------------------------
def classify_panel(dx, dy):
    """Devuelve (a, b, modo) con a= lado corto, b= lado largo,
    modo = '2d' o '1d' segun b/a."""
    a, b = sorted([dx, dy])
    if a < 1e-6:
        return 0.0, 0.0, 'none'
    if b / a < 2.0:
        return a, b, '2d'
    return a, b, '1d'


def panel_tributary_areas(x1, x2, y1, y2):
    """Areas tributarias por lado del panel (rectangulo envolvente).
    Retorna dict con claves 'bottom','top','left','right' y su area.
    No incluye bordes sin carga ('1d' deja los lados cortos en 0)."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    a, b, modo = classify_panel(dx, dy)
    if modo == 'none':
        return {}

    # geometria: lados horizontales (bottom/top) tienen largo dx,
    #            lados verticales (left/right) tienen largo dy.
    hor = dx   # largo de lados horizontales
    ver = dy   # largo de lados verticales

    areas = {}
    if modo == '2d':
        # b = lado mayor. Si dy>=dx -> lados largos son verticales (left/right)
        if dy >= dx:
            # lados largos = verticales (left, right) -> trapecios
            # lados cortos = horizontales (bottom, top) -> triangulos
            tri = a * a / 4.0
            tra = a * (2.0 * b - a) / 4.0
            areas['bottom'] = tri
            areas['top'] = tri
            areas['left'] = tra
            areas['right'] = tra
        else:
            # lados largos = horizontales (bottom, top) -> trapecios
            # lados cortos = verticales (left, right) -> triangulos
            tri = a * a / 4.0
            tra = a * (2.0 * b - a) / 4.0
            areas['bottom'] = tra
            areas['top'] = tra
            areas['left'] = tri
            areas['right'] = tri
    else:  # '1d' -> solo lados largos, cada uno a*b/2
        total = a * b / 2.0
        if dy >= dx:
            # lados largos = verticales
            areas['left'] = total
            areas['right'] = total
        else:
            # lados largos = horizontales
            areas['bottom'] = total
            areas['top'] = total
    return areas


# ---------------------------------------------------------------
# Indice de vigas por recta (nivel + coordenada constante)
# ---------------------------------------------------------------
def _edge_key_h(x1, x2, y):
    return ('H', y, x1, x2)


def build_beam_index(structure):
    """Indice de vigas por (nivel, orientacion, coord fija)."""
    # H: vigas horizontales (y const) -> lista (y, xmin, xmax, beam)
    # V: vigas verticales (x const)   -> lista (x, ymin, ymax, beam)
    nm = structure["node_map"]
    h = {}
    v = {}
    for b in structure["beams"]:
        n1 = nm[b["iNode"]]; n2 = nm[b["jNode"]]
        x1, y1 = n1["x"], n1["y"]
        x2, y2 = n2["x"], n2["y"]
        xmin, xmax = sorted([x1, x2])
        ymin, ymax = sorted([y1, y2])
        L = hypot(xmax - xmin, ymax - ymin)
        if L < 1e-9:
            continue
        piso = b["piso"]
        if abs(ymax - ymin) / L < 1e-6:      # horizontal
            h.setdefault(piso, []).append((y1, xmin, xmax, L, b))
        elif abs(xmax - xmin) / L < 1e-6:    # vertical
            v.setdefault(piso, []).append((x1, ymin, ymax, L, b))
    return {"H": h, "V": v}


def beams_covering_edge(index, piso, orient, coord, lo, hi, tol=0.10):
    """Vigas (del index) que yacen sobre una recta y cubren [lo,hi]."""
    if orient == 'H':
        lst = index["H"].get(piso, [])
        out = []
        for y, xmin, xmax, L, b in lst:
            if abs(y - coord) < tol and xmax >= lo - tol and xmin <= hi + tol:
                ov = min(xmax, hi) - max(xmin, lo)
                if ov > 0:
                    out.append((ov, xmin, xmax, b))
        return out
    else:  # 'V'
        lst = index["V"].get(piso, [])
        out = []
        for x, ymin, ymax, L, b in lst:
            if abs(x - coord) < tol and ymax >= lo - tol and ymin <= hi + tol:
                ov = min(ymax, hi) - max(ymin, lo)
                if ov > 0:
                    out.append((ov, ymin, ymax, b))
        return out


# ---------------------------------------------------------------
# Calculo principal
# ---------------------------------------------------------------
def compute_tributary_areas(geometry, structure):
    """Para cada piso, asigna area tributaria a cada viga segun la
    regla b/a de los paneles analizados.
    Retorna (beam_data, piso_summary).
    beam_data: dict tag -> {area, carga, largo, piso, seccion, ...}
    piso_summary: dict nivel -> {area_losa, area_trib, carga, n_paneles,
                                 n_paneles_excluidos, err_area}
    """
    index = build_beam_index(structure)
    beam_data = {}

    def acc(tag, area, piso):
        d = beam_data.setdefault(tag, {"area": 0.0, "carga": 0.0,
                                       "piso": piso})
        d["area"] += area
        d["piso"] = piso

    piso = {}
    nm = structure["node_map"]

    for slab in geometry["slabs"]:
        if slab["x1"] is None:
            continue
        x1, x2 = sorted([slab["x1"], slab["x2"]])
        y1, y2 = sorted([slab["y1"], slab["y2"]])
        lv = slab["level"]
        if lv not in Q_G_BY_LEVEL:
            continue
        qg = Q_G_BY_LEVEL[lv]
        a, b, modo = classify_panel(x2 - x1, y2 - y1)
        A_losa = (x2 - x1) * (y2 - y1)
        ps = piso.setdefault(lv, {"area_losa": 0.0, "area_trib": 0.0,
                                  "n_paneles": 0, "n_excluidos": 0})

        if modo == 'none' or A_losa < 1e-6:
            ps["n_excluidos"] += 1
            continue

        areas = panel_tributary_areas(x1, x2, y1, y2)
        # asignar cada lado a sus vigas
        asignado = 0.0
        # lados horizontales (y const)
        for lado, (coord, lo, hi) in {
            'bottom': (y1, x1, x2),
            'top': (y2, x1, x2),
        }.items():
            area = areas.get(lado, 0.0)
            if area <= 0:
                continue
            cover = beams_covering_edge(index, lv, 'H', coord, lo, hi)
            total_len = sum(c[0] for c in cover)
            if total_len <= 0:
                continue
            for ov, _, _, beam in cover:
                frac = ov / total_len
                acc(beam["tag"], area * frac, lv)
                asignado += area * frac
        # lados verticales (x const)
        for lado, (coord, lo, hi) in {
            'left': (x1, y1, y2),
            'right': (x2, y1, y2),
        }.items():
            area = areas.get(lado, 0.0)
            if area <= 0:
                continue
            cover = beams_covering_edge(index, lv, 'V', coord, lo, hi)
            total_len = sum(c[0] for c in cover)
            if total_len <= 0:
                continue
            for ov, _, _, beam in cover:
                frac = ov / total_len
                acc(beam["tag"], area * frac, lv)
                asignado += area * frac

        ps["n_paneles"] += 1
        ps["area_losa"] += A_losa
        ps["area_trib"] += asignado
        ps["carga"] = ps.get("carga", 0.0) + asignado * qg

    # completar datos de largo/seccion/carga final
    for b in structure["beams"]:
        tag = b["tag"]
        if tag not in beam_data:
            beam_data[tag] = {"area": 0.0, "carga": 0.0, "piso": b["piso"]}
        d = beam_data[tag]
        n1 = nm[b["iNode"]]; n2 = nm[b["jNode"]]
        L = hypot(n1["x"] - n2["x"], n1["y"] - n2["y"])
        d["largo"] = L
        d["seccion"] = b["seccion"]
        d["iNode"] = b["iNode"]
        d["jNode"] = b["jNode"]
        qg = Q_G_BY_LEVEL.get(b["piso"], Q_G)
        d["carga"] = d["area"] * qg

    # resumen por piso
    summary = {}
    for lv in Q_G_BY_LEVEL:
        ps = piso.get(lv, {"area_losa": 0.0, "area_trib": 0.0,
                           "n_paneles": 0, "n_excluidos": 0, "carga": 0.0})
        qg = Q_G_BY_LEVEL[lv]
        ps["carga"] = ps.get("carga", 0.0)
        ps.setdefault("carga", ps["area_losa"] * qg)
        ps["err_area"] = abs(ps["area_trib"] - ps["area_losa"])
        summary[lv] = ps
    return beam_data, summary
