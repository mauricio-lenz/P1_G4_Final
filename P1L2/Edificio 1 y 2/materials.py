# ============================================================
# MATERIALES - Edificio de Ingenieria UANDES
# ============================================================
# Unidades: kN y metros.
# Concreto estructural para elementos de la superestructura.
# ============================================================


class ConcreteMaterial:
    """Concreto estructural isotropico lineal."""

    def __init__(self, name, fc_MPa, gamma_kNm3):
        self.name = name
        self.fc_MPa = fc_MPa
        # fc en kN/m^2
        self.fc = fc_MPa * 1000.0
        self.gamma = gamma_kNm3
        # Modulo de elasticidad (ACI 318 aproximado, en kN/m^2)
        # Ec = 4700 * sqrt(fc[MPa]) [MPa], en kN/m^2 multiplicar por 1000
        self.E = 4700.0 * (fc_MPa ** 0.5) * 1000.0
        self.nu = 0.20
        self.G = self.E / (2.0 * (1.0 + self.nu))


# Concreto H-30 (fc ~ 30 MPa), tipico de un edificio real.
CONCRETO_H30 = ConcreteMaterial(name="H30", fc_MPa=30.0, gamma_kNm3=24.0)

# Concreto H-25 (fc ~ 25 MPa), para fundaciones/soleras si se requieren.
CONCRETO_H25 = ConcreteMaterial(name="H25", fc_MPa=25.0, gamma_kNm3=24.0)

# ------------------------------------------------------------------
# CARGAS DE DISENO (según Cuadro 1 del enunciado)
# Unidades del cuadro: kg/m^2  (g = 9.81 m/s^2)
# ------------------------------------------------------------------
G = 9.81                       # m/s^2
KGM2_TO_KNM2 = G / 1000.0

# Peso propio losa: PP = e(m) * 2500 kg/m^3
ESPESOR_LOSA = 0.15            # m
PP_LOSA_KGM2 = ESPESOR_LOSA * 2500.0            # 375 kg/m^2
PP_LOSA_KNM2 = PP_LOSA_KGM2 * KGM2_TO_KNM2      # 3.679 kN/m^2

# Pisos CIELO 1°Subterráneo a CIELO Piso 3°: PM adic. 260, SC 500
PM_ADIC_INF = 260.0            # kg/m^2
SC_INF = 500.0                 # kg/m^2
# Pisos CIELO Piso 4° (cubierta): PM adic. 200, SC 200
PM_ADIC_CUB = 200.0            # kg/m^2
SC_CUB = 200.0                 # kg/m^2


def carga_diseno_kgm2(pp, pm_adic, sc, g_acc=G):
    """Mayor de las combinaciones ACI 318 (kg/m^2).
    Se usan las combinaciones que gobiernan para esta sobrecarga:
    1.4D  y  1.2D + 1.6L."""
    D = pp + pm_adic
    L = sc
    U14 = 1.4 * D
    U1216 = 1.2 * D + 1.6 * L
    return max(U14, U1216)


# Pisos inferiores
D_INF = PP_LOSA_KGM2 + PM_ADIC_INF              # 635 kg/m^2
QG_INF_KGM2 = carga_diseno_kgm2(PP_LOSA_KGM2, PM_ADIC_INF, SC_INF)   # 1562
Q_G_INF = QG_INF_KGM2 * KGM2_TO_KNM2            # 15.323 kN/m^2

# Cubierta (CIELO Piso 4°)
D_CUB = PP_LOSA_KGM2 + PM_ADIC_CUB             # 575 kg/m^2
QG_CUB_KGM2 = carga_diseno_kgm2(PP_LOSA_KGM2, PM_ADIC_CUB, SC_CUB)   # 1010
Q_G_CUB = QG_CUB_KGM2 * KGM2_TO_KNM2           # 9.908 kN/m^2

# q_G por nivel de losa (piso analizado)
Q_G_BY_LEVEL = {
    "CIELO_1S": Q_G_INF,
    "CIELO_1": Q_G_INF,
    "CIELO_2": Q_G_INF,
    "CIELO_3": Q_G_INF,
    "CIELO_4": Q_G_CUB,
}

# Backward-compatible: q_G de pisos inferiores
Q_G = Q_G_INF

# Tolerancias para verificaciones [kN] y [m^2]
TOL_CONSERVACION_KN = 0.05
TOL_AREA_M2 = 0.02
