"""Armaduras y capacidad de vigas y columnas de hormigon armado (ACI 318-19).

Las armaduras se leen de data/armaduras.json (tipo por seccion + excepciones
por elemento, editable en VS Code o desde Unity). Con las fuerzas del analisis
se calcula para cada elemento:

  Vigas     phiMn+ (armadura inferior), phiMn- (superior + suple de apoyo),
            phiVn = 0.75 (Vc + Vs) con los estribos de apoyo; demanda Mu+, Mu-, Vu
  Columnas  curva P-M de diseno (compatibilidad de deformaciones, phi 0.65-0.90,
            Pmax = 0.80 phi P0) y phiVn con Vc segun el axial; demanda (Pu, Mu), Vu

y el factor de uso DCR = demanda / capacidad (el mayor de flexion y corte).

Notacion de barras: "4φ22", "4f22", "4x22" o "2φ22+2φ25"; estribos "Eφ10a10"
(1 estribo = 2 ramas), "EDφ10a10" (estribo doble = 4 ramas) o "φ10a20".
Unidades: kN, m, MPa.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMADURAS_PATH = ROOT / "data" / "armaduras.json"
PLANOS_PATH = ROOT / "data" / "armaduras_planos.json"     # barras reales de las elevaciones (extraer_armaduras_planos.py)
SEP_CAPAS_MM = 25.0        # separacion libre entre capas de barras (ACI 318-19 25.2.2)
M_DESPRECIABLE_KN_M = 5.0  # bajo este momento no se exige armadura de ese signo en la seccion (ruido numerico)

FC_MPA = 35.0      # G35
FY_MPA = 420.0     # A630-420H
ES_MPA = 200000.0
EPS_CU = 0.003


# ----------------------------------------------------------------------
# Lectura de armaduras
# ----------------------------------------------------------------------
_BARS = re.compile(r"(\d+)\s*(?:φ|ø|Ø|f|x|%%[cC])\s*(\d{1,2})", re.IGNORECASE)
_STIRRUP = re.compile(r"(ED|ET|E)?\s*(?:φ|ø|Ø|f|%%[cC])?\s*(\d{1,2})\s*(?:a|@)\s*(\d{1,3})", re.IGNORECASE)


def bars_area_mm2(text):
    """Area total [mm2] y lista de diametros de un texto como '4φ22+2φ25'."""
    area, diams = 0.0, []
    for n, d in _BARS.findall(text or ""):
        n, d = int(n), int(d)
        area += n * math.pi * d * d / 4.0
        diams += [d] * n
    return area, diams


def stirrup(text, legs_default=2):
    """(Av [mm2], s [mm], diametro) de un texto 'EDφ10a10' (ED = 4 ramas, E = 2)."""
    m = _STIRRUP.search(text or "")
    if not m:
        return 0.0, 0.0, 0
    kind, d, s_cm = (m.group(1) or "").upper(), int(m.group(2)), int(m.group(3))
    legs = 4 if kind == "ED" else 3 if kind == "ET" else legs_default
    return legs * math.pi * d * d / 4.0, s_cm * 10.0, d


def load_armaduras(path=ARMADURAS_PATH, overrides=None):
    """Armaduras por seccion y por elemento; overrides (mismo formato) tiene prioridad."""
    data = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}
    secciones = dict(data.get("secciones", {}))
    elementos = dict(data.get("elementos", {}))
    if overrides:
        for k, v in (overrides.get("secciones") or {}).items():
            secciones[k] = {**secciones.get(k, {}), **v}
        for k, v in (overrides.get("elementos") or {}).items():
            elementos[k] = {**elementos.get(k, {}), **v}
    return {"recubrimiento_m": float(data.get("recubrimiento_m", 0.04)), "secciones": secciones, "elementos": elementos}


def armadura_de(element, arm):
    """Armadura efectiva del elemento: la de su seccion con las excepciones del elemento. Si la seccion se
    cambio (Unity / --mods) a una que no tiene armadura tipo, se usa la de su seccion original: mismas
    barras con las dimensiones nuevas."""
    base = arm["secciones"].get(element.get("sectionId")) or arm["secciones"].get(element.get("sectionIdOriginal"), {})
    extra = arm["elementos"].get(element.get("elementTag"), {}) or arm["elementos"].get(str(element.get("id")), {})
    return {**base, **extra}


# ----------------------------------------------------------------------
# Barras reales de los planos (elevaciones de ejes)
# ----------------------------------------------------------------------
_PLANOS = {}


def load_planos(path=PLANOS_PATH):
    key = str(path)
    if key not in _PLANOS:
        _PLANOS[key] = json.loads(Path(path).read_text(encoding="utf-8"))["elevaciones"] if Path(path).exists() else []
    return _PLANOS[key]


def barras_planos(element, nodes, planos=None):
    """Barras de la elevacion de su eje que cubren la viga, con t en [0, 1] a lo largo de I->J:
    {"barras": [(pos, n, d, capa, t0, t1)], "fuente": "2017_67-302 ELEVACION EJE 2"} o None."""
    if nodes is None or element.get("type") != "viga":
        return None
    planos = load_planos() if planos is None else planos
    a, b = nodes.get(element["nodeI"]), nodes.get(element["nodeJ"])
    if a is None or b is None or abs(a["z"] - b["z"]) > 0.01:
        return None
    if abs(a["y"] - b["y"]) < 0.02:
        direccion, c, si, sj = "x", a["y"], a["x"], b["x"]
    elif abs(a["x"] - b["x"]) < 0.02:
        direccion, c, si, sj = "y", a["x"], a["y"], b["y"]
    else:
        return None
    largo = sj - si
    # superior/inferior por la profundidad de la barra en el dibujo: se compara con la altura de la viga
    # en el plano (si la seccion se cambio, la original); la altura util d se calcula con la seccion actual
    h_cm = float(element.get("height_m_original") or element.get("height_m") or 0.8) * 100.0
    edificio = element.get("sourceBuilding") or "edificio_1"
    for el in planos:
        if el["edificio"] != edificio or el["direccion"] != direccion or not any(abs(l["coord"] - c) < 0.3 for l in el["lineas"]):
            continue
        barras = []
        for x in el["barras"]:
            if abs(x["z"] - a["z"]) > 0.05:
                continue
            t0, t1 = sorted(((x["s0"] - si) / largo, (x["s1"] - si) / largo))
            off = x.get("off_cm")
            if off is None:
                pos = x["pos"]
            elif off <= h_cm / 2.0:
                pos = "sup"                       # mitad superior de esta viga
            elif off <= h_cm + 5.0:
                pos = "inf"
            else:
                continue                          # barra bajo el fondo de esta viga: es de otra mas profunda
            if t1 > 0.0 and t0 < 1.0:
                barras.append((pos, int(x["n"]), int(x["d"]), int(x.get("capa", 1)), t0, t1))
        if any(q[0] == "inf" for q in barras) and any(q[0] == "sup" for q in barras):
            return {"barras": barras, "fuente": f'{el["plano"]} {el["titulo"]}'.strip()}
    return None


def indice_apoyos(elements, nodes):
    """Columnas (semiancho por nodo) y muros del modelo, para ubicar las caras de apoyo de las vigas."""
    cols, muros = {}, []
    for e in elements:
        if e.get("removed"):
            continue
        a, b = nodes.get(e.get("nodeI")), nodes.get(e.get("nodeJ"))
        if a is None or b is None:
            continue
        if e.get("type") == "columna":
            h = max(float(e.get("width_m") or 0.3), float(e.get("height_m") or 0.3)) / 2.0
            for n in (e["nodeI"], e["nodeJ"]):
                cols[n] = max(cols.get(n, 0.0), h)
        elif e.get("type") == "muro":
            muros.append((a["x"], a["y"], e.get("wallInPlaneAxis"), float(e["height_m"]), float(e["width_m"]),
                          min(a["z"], b["z"]), max(a["z"], b["z"])))
    return cols, muros


def zonas_apoyo(element, nodes, indice):
    """Tramos [t0, t1] de la viga (t en 0..1 de I a J) que estan dentro de un apoyo: media seccion de
    las columnas de sus extremos y muros que la cruzan o son colineales con ella. ACI 318-19 9.4.2:
    la flexion se verifica en la cara del apoyo, no dentro de el."""
    cols, muros = indice
    a, b = nodes[element["nodeI"]], nodes[element["nodeJ"]]
    if abs(a["y"] - b["y"]) < 0.02:
        direccion, c, si, sj = "X", a["y"], a["x"], b["x"]
    elif abs(a["x"] - b["x"]) < 0.02:
        direccion, c, si, sj = "Y", a["x"], a["y"], b["y"]
    else:
        return []
    largo, z = sj - si, a["z"]
    tramos = [(s - cols[n], s + cols[n]) for n, s in ((element["nodeI"], si), (element["nodeJ"], sj)) if n in cols]
    for wx, wy, eje, wl, wt, z0, z1 in muros:
        if not (abs(z1 - z) < 0.05 or abs(z0 - z) < 0.05):
            continue
        perp, along = (wy, wx) if direccion == "X" else (wx, wy)
        if eje == direccion and abs(perp - c) < 0.3:                       # muro colineal
            tramos.append((along - wl / 2.0, along + wl / 2.0))
        elif eje and eje != direccion and abs(c - perp) <= wl / 2.0 + 1e-6:   # muro que la cruza
            tramos.append((along - wt / 2.0, along + wt / 2.0))
    out = []
    for s0, s1 in tramos:
        t0, t1 = sorted(((s0 - si) / largo, (s1 - si) / largo))
        if t1 > 0.0 and t0 < 1.0:
            out.append((max(0.0, t0), min(1.0, t1)))
    return out


def estaciones(n, apoyos):
    """Estaciones t para verificar: n+1 uniformes + caras de apoyo, sin las que caen dentro de un apoyo."""
    ts = {i / n for i in range(n + 1)} | {t for tr in apoyos for t in tr if 0.0 < t < 1.0}
    dentro = lambda t: any(t0 + 1e-9 < t < t1 - 1e-9 or (t in (0.0, 1.0) and t0 - 1e-9 <= t <= t1 + 1e-9 and t1 - t0 > 1e-6)
                           for t0, t1 in apoyos)
    return sorted(t for t in ts if not dentro(t))


def acero_en(barras, pos, t, h_mm, recub_mm, d_estribo):
    """Area [mm2], altura util d [mm] (centroide de las capas) y diametros de las barras pos en t."""
    area = brazo = 0.0
    diams = []
    for p, n, d, capa_k, t0, t1 in barras:
        if p != pos or not (t0 - 1e-9 <= t <= t1 + 1e-9):
            continue
        a_g = n * math.pi * d * d / 4.0
        y = recub_mm + d_estribo + d / 2.0 + (capa_k - 1) * (d + SEP_CAPAS_MM)   # centro de la capa desde la cara
        area += a_g
        brazo += a_g * y
        diams += [d] * n
    if area <= 0.0:
        return 0.0, 0.0, []
    return area, h_mm - brazo / area, diams


def texto_barras(diams):
    cuenta = {}
    for d in diams:
        cuenta[d] = cuenta.get(d, 0) + 1
    return "+".join(f"{n}φ{d}" for d, n in sorted(cuenta.items()))


# ----------------------------------------------------------------------
# Vigas
# ----------------------------------------------------------------------
def phi_flexion(eps_t):
    """ACI 318-19 tabla 21.2.2 (estribos): 0.65 controlada por compresion -> 0.90 por traccion."""
    if eps_t >= 0.005:
        return 0.90
    if eps_t <= FY_MPA / ES_MPA:
        return 0.65
    return 0.65 + 0.25 * (eps_t - FY_MPA / ES_MPA) / (0.005 - FY_MPA / ES_MPA)


def flexion_rectangular(b_mm, d_mm, as_mm2):
    """phiMn [kN m] de seccion rectangular con armadura de traccion (sin aporte de compresion)."""
    if as_mm2 <= 0 or d_mm <= 0:
        return 0.0, 0.0, 0.0
    a = as_mm2 * FY_MPA / (0.85 * FC_MPA * b_mm)
    c = a / 0.80                                   # beta1 = 0.80 para f'c = 35 MPa
    eps_t = EPS_CU * (d_mm - c) / c
    mn = as_mm2 * FY_MPA * (d_mm - a / 2.0) / 1e6
    phi = phi_flexion(eps_t)
    return phi * mn, mn, eps_t


def corte(b_mm, d_mm, av_mm2, s_mm, nu_kn=0.0, ag_mm2=None):
    """phiVn [kN] ACI 22.5: Vc = 0.17 (1 + Nu/(14 Ag)) sqrt(f'c) b d; Vs = Av fy d / s <= 0.66 sqrt(f'c) b d."""
    factor_n = 1.0
    if ag_mm2 and nu_kn > 0:
        factor_n = 1.0 + (nu_kn * 1000.0) / (14.0 * ag_mm2)
    vc = 0.17 * factor_n * math.sqrt(FC_MPA) * b_mm * d_mm / 1000.0
    vs = (av_mm2 * FY_MPA * d_mm / s_mm / 1000.0) if s_mm > 0 else 0.0
    vs = min(vs, 0.66 * math.sqrt(FC_MPA) * b_mm * d_mm / 1000.0)
    return 0.75 * (vc + vs), vc, vs


def capacidad_viga(element, a, recub):
    b, h = float(element["width_m"]) * 1000.0, float(element["height_m"]) * 1000.0
    as_inf, d_inf = bars_area_mm2(a.get("inferior"))
    as_sup, d_sup = bars_area_mm2(a.get("superior"))
    as_sup_apoyo, d_sa = bars_area_mm2(a.get("supleApoyo"))
    av, s, d_est = stirrup(a.get("estribosApoyo"))
    av_t, s_t, _ = stirrup(a.get("estribosTramo"))
    db_inf = max(d_inf) if d_inf else 20
    db_sup = max(d_sup + d_sa) if (d_sup or d_sa) else 20
    d_pos = h - recub * 1000.0 - d_est - db_inf / 2.0
    d_neg = h - recub * 1000.0 - d_est - db_sup / 2.0
    phi_mp, mn_p, et_p = flexion_rectangular(b, d_pos, as_inf)
    phi_mn_apoyo, mn_n, et_n = flexion_rectangular(b, d_neg, as_sup + as_sup_apoyo)
    phi_v, vc, vs = corte(b, d_pos, av, s)
    phi_v_t, _, _ = corte(b, d_pos, av_t, s_t) if s_t > 0 else (phi_v, 0, 0)
    return {
        "phiMn_pos_kN_m": phi_mp, "phiMn_neg_kN_m": phi_mn_apoyo, "phiVn_apoyo_kN": phi_v, "phiVn_tramo_kN": phi_v_t,
        "As_inf_mm2": as_inf, "As_sup_apoyo_mm2": as_sup + as_sup_apoyo, "d_mm": d_pos,
        "eps_t_pos": et_p, "eps_t_neg": et_n, "Vc_kN": vc, "Vs_kN": vs,
    }


# ----------------------------------------------------------------------
# Columnas: curva P-M de diseno por compatibilidad de deformaciones
# ----------------------------------------------------------------------
def barras_perimetro(b_mm, h_mm, n, recub_c_mm):
    """n barras repartidas en el perimetro de un rectangulo (4 esquinas + intermedias)."""
    xs, ys = b_mm / 2.0 - recub_c_mm, h_mm / 2.0 - recub_c_mm
    pts = [(-xs, -ys), (xs, -ys), (xs, ys), (-xs, ys)]
    resto = max(0, n - 4)
    # reparte las intermedias entre las 4 caras en proporcion a su largo
    caras = [((-xs, -ys), (xs, -ys)), ((xs, -ys), (xs, ys)), ((xs, ys), (-xs, ys)), ((-xs, ys), (-xs, -ys))]
    por_cara = [resto // 4 + (1 if k < resto % 4 else 0) for k in range(4)]
    for (p0, p1), k in zip(caras, por_cara):
        for i in range(1, k + 1):
            t = i / (k + 1)
            pts.append((p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1])))
    return pts[:max(n, 4)] if n >= 4 else pts[:n]


def curva_pm_seccion(b_mm, h_mm, barras, n_puntos=40):
    """Curva de diseno (phiPn, phiMn) ACI 318-19 de una seccion rectangular b x h (flexion en h) por
    compatibilidad de deformaciones: barras = [(y [mm] desde el centroide, area [mm2])].
    Bloque de Whitney (beta1 = 0.80, G35), eps_cu = 0.003, acero elastoplastico, phi 0.65-0.90 segun
    eps_t de la barra extrema, phiPmax = 0.80 phi P0 (estribos). P compresion +."""
    ast = sum(ab for _, ab in barras)
    ag = b_mm * h_mm
    p0 = (0.85 * FC_MPA * (ag - ast) + FY_MPA * ast) / 1000.0
    pmax = 0.80 * 0.65 * p0
    puntos = []
    d_t = h_mm / 2.0 + max(abs(y) for y, _ in barras)
    for k in range(n_puntos + 1):
        # c desde 0.05 h (traccion) hasta 3 h (compresion)
        c = h_mm * (0.05 + 2.95 * (k / n_puntos) ** 1.6)
        a = min(0.80 * c, h_mm)
        cc = 0.85 * FC_MPA * a * b_mm / 1000.0
        pn = cc
        mn = cc * (h_mm / 2.0 - a / 2.0) / 1000.0
        for y, ab in barras:
            dist = h_mm / 2.0 - y            # desde la fibra comprimida
            eps = EPS_CU * (c - dist) / c
            fs = max(-FY_MPA, min(FY_MPA, eps * ES_MPA))
            if dist <= a:                    # barra dentro del bloque: descontar hormigon desplazado
                fs -= 0.85 * FC_MPA
            f = fs * ab / 1000.0
            pn += f
            mn += f * y / 1000.0               # brazo: y desde el centroide (= h/2 - dist)
        eps_t = EPS_CU * (d_t - c) / c
        phi = phi_flexion(eps_t)
        puntos.append({"P_kN": min(phi * pn, pmax), "M_kN_m": phi * abs(mn), "Pn_kN": pn, "Mn_kN_m": abs(mn), "phi": phi})
    # traccion pura
    puntos.append({"P_kN": -0.9 * FY_MPA * ast / 1000.0, "M_kN_m": 0.0, "Pn_kN": -FY_MPA * ast / 1000.0, "Mn_kN_m": 0.0, "phi": 0.9})
    puntos.append({"P_kN": pmax, "M_kN_m": 0.0, "Pn_kN": p0, "Mn_kN_m": 0.0, "phi": 0.65})
    puntos.sort(key=lambda q: q["P_kN"])
    return {"puntos": puntos, "P0_kN": p0, "phiPmax_kN": pmax, "Ast_mm2": ast, "n_barras": len(barras)}


def curva_pm_columna(b_mm, h_mm, n_barras, diam_mm, recub_m=0.04, d_estribo=10, n_puntos=40):
    """Curva de diseno (phiPn, phiMn) en flexion sobre el eje fuerte (simetrica). P compresion +."""
    recub_c = recub_m * 1000.0 + d_estribo + diam_mm / 2.0
    a_bar = math.pi * diam_mm * diam_mm / 4.0
    barras = barras_perimetro(b_mm, h_mm, n_barras, recub_c)
    return curva_pm_seccion(b_mm, h_mm, [(y, a_bar) for _, y in barras], n_puntos)


MALLA = re.compile(r"(\d{1,2})\s*a\s*(\d{1,3})", re.IGNORECASE)
PASO_BORDE_MM = 100.0      # separacion de los pares de barras de borde desde la punta del muro


def curva_pm_muro(t_m, L_m, malla_v="12a20", bordes=None, recub_m=0.03, n_puntos=40, n_mallas=2):
    """Curva de diseno P-M en el plano de un muro t x L con n_mallas mallas verticales "d a s" (phi d
    @ s cm; doble malla = 1 por cara) y barras de borde por punta: bordes = {"ini": [(n, d)], "fin": [...]}.
    Las barras de borde van en pares (una por cara) cada 10 cm desde la punta; la malla no se repite en
    esa zona."""
    t, L = t_m * 1000.0, L_m * 1000.0
    m = MALLA.search(malla_v or "")
    dv, sv = (int(m.group(1)), int(m.group(2)) * 10.0) if m else (12, 200.0)
    c0 = recub_m * 1000.0 + dv / 2.0
    barras = []
    zona = {"ini": 0.0, "fin": 0.0}
    for lado, grupos in (bordes or {}).items():
        x = c0
        for n, d in grupos:
            for k in range(0, int(n), 2):          # pares (una barra por cara)
                pos = x if lado == "ini" else L - x
                nb = 2 if k + 1 < n else 1
                barras.append((pos - L / 2.0, nb * math.pi * d * d / 4.0))
                x += PASO_BORDE_MM
        zona[lado] = x - PASO_BORDE_MM / 2.0 if grupos else 0.0
    x = c0
    while x <= L - c0 + 1e-6:
        if x > zona["ini"] and x < L - zona["fin"]:
            barras.append((x - L / 2.0, n_mallas * math.pi * dv * dv / 4.0))
        x += sv
    curva = curva_pm_seccion(t, L, barras, n_puntos)
    curva.update({"malla_v": f"{dv}a{int(sv / 10)}", "n_mallas": n_mallas, "rho_percent": 100.0 * curva["Ast_mm2"] / (t * L)})
    return curva


def m_capacidad(puntos, p):
    """Mayor phiMn de la envolvente para la carga axial p (0 si p queda fuera)."""
    best = 0.0
    pts = sorted(puntos, key=lambda q: q["P_kN"])
    if p < pts[0]["P_kN"] or p > pts[-1]["P_kN"]:
        return 0.0
    for q0, q1 in zip(pts, pts[1:]):
        if q0["P_kN"] <= p <= q1["P_kN"] and q1["P_kN"] > q0["P_kN"]:
            t = (p - q0["P_kN"]) / (q1["P_kN"] - q0["P_kN"])
            best = max(best, q0["M_kN_m"] + t * (q1["M_kN_m"] - q0["M_kN_m"]))
    return best


def capacidad_columna(element, a, recub):
    b, h = float(element["width_m"]) * 1000.0, float(element["height_m"]) * 1000.0
    _, diams = bars_area_mm2(a.get("barras"))
    av, s, d_est = stirrup(a.get("estribos"), legs_default=2)
    n = len(diams)
    diam = max(diams) if diams else 25
    curva = curva_pm_columna(b, h, n, diam, recub, d_est or 10)
    d = h - recub * 1000.0 - (d_est or 10) - diam / 2.0
    return {"curva": curva, "b_mm": b, "h_mm": h, "d_mm": d, "Av_mm2": av, "s_mm": s, "Ag_mm2": b * h}


# ----------------------------------------------------------------------
# Demanda y factor de uso
# ----------------------------------------------------------------------
def evaluar(element, forces_by_combo, w_by_combo, length, arm, nodes=None, apoyos=None):
    """Capacidad y factor de uso del elemento con las fuerzas del analisis (12 componentes locales).
    w_by_combo: carga repartida vertical del tramo [kN/m] por combo (para el momento al centro).
    nodes: si se da, las vigas con elevacion en los planos usan sus barras reales seccion por
    seccion (salvo que la armadura longitudinal del elemento se haya cambiado a mano)."""
    a = armadura_de(element, arm)
    if not a:
        return None
    recub = arm["recubrimiento_m"]
    tipo = element.get("type")
    out = {"armadura": a, "porCombo": []}
    if element.get("sectionIdOriginal") and element.get("sectionId") not in arm["secciones"]:
        out["nota"] = (f"seccion cambiada {element['sectionIdOriginal']} -> {element.get('sectionId')}: "
                       f"armadura de la seccion original con las dimensiones nuevas")
    manual = arm["elementos"].get(element.get("elementTag"), {}) or arm["elementos"].get(str(element.get("id")), {})
    planos = barras_planos(element, nodes) if tipo == "viga" else None
    if planos:
        res_planos = evaluar_viga_planos(element, forces_by_combo, w_by_combo, length, a, recub, planos, apoyos=apoyos)
        if element.get("sectionIdOriginal") and element.get("sectionId") != element["sectionIdOriginal"]:
            res_planos.setdefault("nota", f"seccion cambiada {element['sectionIdOriginal']} -> {element.get('sectionId')}: "
                                          f"barras de los planos con las dimensiones nuevas")
        if not any(k in manual for k in ("inferior", "superior", "supleApoyo")):
            return res_planos
        # cambio manual (Unity / armaduras.json) sobre las barras de los planos en las secciones gobernantes
        base = res_planos.get("armadura") or {}
        a = {**a, "inferior": base.get("inferior", a.get("inferior")), "superior": base.get("superior", a.get("superior")),
             "supleApoyo": "", **manual}
        out["armadura"] = a
        out["nota"] = f"armadura cambiada a mano sobre la de los planos ({planos['fuente']})"
    if tipo == "viga":
        cap = capacidad_viga(element, a, recub)
        out.update({k: round(v, 3) for k, v in cap.items()})
        worst = None
        ts = estaciones(20, apoyos or [])
        for combo, f in forces_by_combo.items():
            w = w_by_combo.get(combo, 0.0)
            mu_pos = mu_neg = vu = 0.0
            for t in ts:
                my = -(1 - t) * f[4] + t * f[10] - w * length * length * t * (1 - t) / 2.0
                vz = -(1 - t) * f[2] + t * f[8]
                # convencion de diseno: My local < 0 = traccion abajo (M+)
                mu_pos = max(mu_pos, -my)
                mu_neg = max(mu_neg, my)
                vu = max(vu, abs(vz))
            dcr_f = max(mu_pos / cap["phiMn_pos_kN_m"] if cap["phiMn_pos_kN_m"] > 0 else 9.99,
                        mu_neg / cap["phiMn_neg_kN_m"] if cap["phiMn_neg_kN_m"] > 0 else 9.99)
            dcr_v = vu / cap["phiVn_apoyo_kN"] if cap["phiVn_apoyo_kN"] > 0 else 9.99
            row = {"combo": combo, "Mu_pos": round(mu_pos, 2), "Mu_neg": round(mu_neg, 2), "Vu": round(vu, 2),
                   "DCR_flexion": round(dcr_f, 3), "DCR_corte": round(dcr_v, 3)}
            out["porCombo"].append(row)
            if worst is None or max(dcr_f, dcr_v) > max(worst["DCR_flexion"], worst["DCR_corte"]):
                worst = row
    elif tipo == "columna" and element.get("material") != "acero":
        cap = capacidad_columna(element, a, recub)
        out.update({"P0_kN": round(cap["curva"]["P0_kN"], 1), "phiPmax_kN": round(cap["curva"]["phiPmax_kN"], 1),
                    "Ast_mm2": round(cap["curva"]["Ast_mm2"], 1), "curvaPM": [
                        {"P_kN": round(q["P_kN"], 1), "M_kN_m": round(q["M_kN_m"], 1)} for q in cap["curva"]["puntos"]]})
        worst = None
        for combo, f in forces_by_combo.items():
            pu = 0.5 * (f[0] - f[6])                 # compresion +
            mu = max(math.hypot(f[4], f[5]), math.hypot(f[10], f[11]))
            vu = max(math.hypot(f[1], f[2]), math.hypot(f[7], f[8]))
            mcap = m_capacidad(cap["curva"]["puntos"], pu)
            phi_v, _, _ = corte(cap["b_mm"], cap["d_mm"], cap["Av_mm2"], cap["s_mm"], max(pu, 0.0), cap["Ag_mm2"])
            dcr_pm = mu / mcap if mcap > 0 else 9.99
            dcr_v = vu / phi_v if phi_v > 0 else 9.99
            row = {"combo": combo, "Pu": round(pu, 1), "Mu": round(mu, 1), "phiMn_at_Pu": round(mcap, 1), "Vu": round(vu, 1),
                   "phiVn": round(phi_v, 1), "DCR_PM": round(dcr_pm, 3), "DCR_corte": round(dcr_v, 3)}
            out["porCombo"].append(row)
            if worst is None or max(dcr_pm, dcr_v) > max(worst["DCR_PM"], worst["DCR_corte"]):
                worst = row
    else:
        return None
    if worst:
        out["DCR"] = round(max(v for k, v in worst.items() if k.startswith("DCR")), 3)
        out["comboGobernante"] = worst["combo"]
    return out


def evaluar_viga_planos(element, forces_by_combo, w_by_combo, length, a, recub, planos, n_est=20, apoyos=None):
    """Flexion seccion por seccion con las barras reales: en cada estacion t, phiMn+ con las barras
    inferiores que pasan por t y phiMn- con las superiores, contra Mu+ y Mu- en esa misma t.
    Corte con los estribos tipo de la seccion (17EDf10a10 / EDf10a20 en las elevaciones de V60/80)."""
    b = float(element["width_m"]) * 1000.0
    h = float(element["height_m"]) * 1000.0
    recub_mm = recub * 1000.0
    av, s_est, d_est = stirrup(a.get("estribosApoyo"))
    d_est = d_est or 10
    barras = planos["barras"]
    est = []
    for t in estaciones(n_est, apoyos or []):
        as_i, d_i, di_i = acero_en(barras, "inf", t, h, recub_mm, d_est)
        as_s, d_s, di_s = acero_en(barras, "sup", t, h, recub_mm, d_est)
        pos = flexion_rectangular(b, d_i, as_i) if as_i > 0 else (0.0, 0.0, 0.0)
        neg = flexion_rectangular(b, d_s, as_s) if as_s > 0 else (0.0, 0.0, 0.0)
        est.append({"t": t, "As_inf": as_i, "d_inf": d_i, "inf": di_i, "As_sup": as_s, "d_sup": d_s, "sup": di_s,
                    "phiMn_pos": pos[0], "phiMn_neg": neg[0], "eps_t_pos": pos[2], "eps_t_neg": neg[2]})
    if not est:   # la viga queda entera dentro de un apoyo (tramo corto embebido en un muro)
        return {"armadura": a, "porCombo": [], "fuenteArmadura": planos["fuente"], "DCR": 0.0,
                "nota": "viga dentro de un apoyo: sin seccion que verificar en flexion",
                "carasApoyo": [[round(t0, 3), round(t1, 3)] for t0, t1 in (apoyos or [])]}
    d_corte = min((e["d_inf"] for e in est if e["d_inf"] > 0), default=h - recub_mm - d_est - 12.5)
    phi_v, vc, vs = corte(b, d_corte, av, s_est)
    out = {"porCombo": [], "fuenteArmadura": planos["fuente"], "carasApoyo": [[round(t0, 3), round(t1, 3)] for t0, t1 in (apoyos or [])]}
    worst = gob = None
    for combo, f in forces_by_combo.items():
        w = w_by_combo.get(combo, 0.0)
        mu_pos = mu_neg = vu = 0.0
        r_max, r_est = 0.0, None
        for e in est:
            t = e["t"]
            my = -(1 - t) * f[4] + t * f[10] - w * length * length * t * (1 - t) / 2.0
            vz = -(1 - t) * f[2] + t * f[8]
            mp, mn = max(0.0, -my), max(0.0, my)        # M+ = traccion abajo
            mu_pos, mu_neg, vu = max(mu_pos, mp), max(mu_neg, mn), max(vu, abs(vz))
            for m, cap, signo in ((mp, e["phiMn_pos"], "+"), (mn, e["phiMn_neg"], "-")):
                if m < M_DESPRECIABLE_KN_M:
                    continue
                r = m / cap if cap > 0 else 9.99      # momento donde no pasa armadura: no cumple
                if r > r_max:
                    r_max, r_est = r, (e, signo, m)
        dcr_v = vu / phi_v if phi_v > 0 else 9.99
        row = {"combo": combo, "Mu_pos": round(mu_pos, 2), "Mu_neg": round(mu_neg, 2), "Vu": round(vu, 2),
               "DCR_flexion": round(r_max, 3), "DCR_corte": round(dcr_v, 3)}
        if r_est:
            row.update({"t_gobierna": round(r_est[0]["t"], 2), "signo": r_est[1]})
        out["porCombo"].append(row)
        if worst is None or max(r_max, dcr_v) > max(worst["DCR_flexion"], worst["DCR_corte"]):
            worst, gob = row, r_est
    # valores para mostrar: armadura de la estacion de mayor M+ y de la de mayor M- del combo gobernante
    def estacion(signo):
        f = forces_by_combo[worst["combo"]]
        w = w_by_combo.get(worst["combo"], 0.0)
        def m(e):
            t = e["t"]
            my = -(1 - t) * f[4] + t * f[10] - w * length * length * t * (1 - t) / 2.0
            return -my if signo == "+" else my
        return max(est, key=m)
    ep, en = estacion("+"), estacion("-")
    out["armadura"] = {
        "inferior": texto_barras(ep["inf"]), "superior": texto_barras(en["sup"]), "supleApoyo": "",
        "estribosApoyo": a.get("estribosApoyo", ""), "estribosTramo": a.get("estribosTramo", ""),
    }
    out.update({
        "phiMn_pos_kN_m": round(ep["phiMn_pos"], 3), "phiMn_neg_kN_m": round(en["phiMn_neg"], 3),
        "phiVn_apoyo_kN": round(phi_v, 3), "phiVn_tramo_kN": round(phi_v, 3),
        "As_inf_mm2": round(ep["As_inf"], 3), "As_sup_apoyo_mm2": round(en["As_sup"], 3), "d_mm": round(ep["d_inf"] or d_corte, 3),
        "eps_t_pos": round(ep["eps_t_pos"], 5), "eps_t_neg": round(en["eps_t_neg"], 5), "Vc_kN": round(vc, 3), "Vs_kN": round(vs, 3),
        "perfil": [{"t": e["t"], "As_inf_mm2": round(e["As_inf"], 1), "As_sup_mm2": round(e["As_sup"], 1),
                    "phiMn_pos": round(e["phiMn_pos"], 1), "phiMn_neg": round(e["phiMn_neg"], 1)} for e in est],
        "DCR": round(max(worst["DCR_flexion"], worst["DCR_corte"]), 3), "comboGobernante": worst["combo"],
    })
    return out


def merge_into_file(overrides_path, path=ARMADURAS_PATH):
    """Agrega los cambios (mismo formato) a data/armaduras.json conservando descripcion y origen."""
    base = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {"secciones": {}, "elementos": {}}
    ov = json.loads(Path(overrides_path).read_text(encoding="utf-8"))
    for key in ("secciones", "elementos"):
        base.setdefault(key, {})
        for k, v in (ov.get(key) or {}).items():
            base[key][k] = {**base[key].get(k, {}), **v}
    Path(path).write_text(json.dumps(base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return base


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Armaduras ACI 318: fusionar cambios en data/armaduras.json")
    parser.add_argument("--merge", type=Path, required=True, help="JSON con cambios {secciones, elementos}")
    parser.add_argument("--out", type=Path, default=None, help="(lo usa PythonJob) archivo de confirmacion")
    a = parser.parse_args()
    merged = merge_into_file(a.merge)
    print(f"armaduras.json: {len(merged['secciones'])} secciones, {len(merged['elementos'])} excepciones por elemento")
    if a.out:
        Path(a.out).write_text("ok", encoding="utf-8")
