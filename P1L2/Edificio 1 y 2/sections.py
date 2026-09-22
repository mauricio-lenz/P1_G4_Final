# ============================================================
# SECCIONES - Edificio de Ingenieria UANDES
# ============================================================
# Secciones de columnas, vigas y muros equivalentes.
# Cada seccion entrega A, Iy, Iz, J para elasticBeamColumn.
# Unidades: kN y metros.
# ============================================================
from materials import ConcreteMaterial, CONCRETO_H30


def rect_section_props(b, h):
    """Propiedades de una seccion rectangular solida (b x h)."""
    A = b * h
    Iy = (h * b**3) / 12.0   # inercia respecto al eje local y (ancho b)
    Iz = (b * h**3) / 12.0   # inercia respecto al eje local z (alto h)
    J = 0.141 * b * h**3     # torsion de Saint-Venant (aprox. AISC)
    return {"A": A, "Iy": Iy, "Iz": Iz, "J": J, "b": b, "h": h}


# -----------------------------------------------------------------
# COLUMNAS
# -----------------------------------------------------------------
# Todas las columnas del edificio son 70x70 cm (definidas en geometry_data).
COL = rect_section_props(0.70, 0.70)


# -----------------------------------------------------------------
# VIGAS (segun SUPERSTRUCTURE_BEAM_SPECS)
# -----------------------------------------------------------------
BEAM_SECTIONS = {
    "V40/80": rect_section_props(0.40, 0.80),
    "V60/80": rect_section_props(0.60, 0.80),
    "V30/80": rect_section_props(0.30, 0.80),
}


# -----------------------------------------------------------------
# MURO EQUIVALENTE
# -----------------------------------------------------------------
def wall_section_props(thickness, length):
    """Seccion rectangular equivalente de un muro:
    espesor 't' y longitud 'L' (en el plano).
    A = t*L, I_plano = t*L^3/12 (flexion en el plano),
    I_fuera = L*t^3/12 (flexion fuera del plano).
    """
    t = thickness
    L = length
    A = t * L
    # Iy: inercia alrededor del eje y local (b=espesor) -> flexion en el plano
    Iy = (L * t**3) / 12.0
    # Iz: inercia alrededor del eje z local (h=longitud) -> flexion fuera del plano
    Iz = (t * L**3) / 12.0
    J = 0.141 * t * L**3
    return {"A": A, "Iy": Iy, "Iz": Iz, "J": J, "b": t, "h": L}


def materials():
    return {"Concreto H30": CONCRETO_H30}
