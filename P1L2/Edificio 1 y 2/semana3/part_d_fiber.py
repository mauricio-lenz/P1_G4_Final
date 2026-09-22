# ============================================================
# PARTE D - FIBER SECTION DE COLUMNA 70x70 (Semana 3)
# ============================================================
# Define la seccion de fibra de una columna 70x70 cm (concreto H-30
# + 8 barras de acero A630-420H) y obtiene:
#   - la curva Momento - Curvatura (M-fi)
#   - los primeros puntos de la interaccion P - M
#   - interpretacion (fluencia, ductilidad, capacidad).
#
# METODO (seccion de fibras por compatibilidad de deformaciones):
#   - la seccion se discretiza en fibras de concreto (malla 40x40)
#     y barras de acero (8 fibras puntuales);
#   - para una curvatura k se adopta un plano de deformaciones
#     ep_i = k*(c - x_i)  (c = profundidad del eje neutro desde la
#     fibra mas comprimida; compresion positiva);
#   - se resuelve c por biseccion para equilibrar la carga axial P;
#   - el momento se integra respecto al centroide: M = suma(sig*A*d).
#   Este integrador reproduce exactamente la seccion 'section Fiber'
#   de OpenSees (mismos materiales Concrete01/Steel01 y geometria).
#
# Unidades: kN y metros. f'c = 30 MPa = 30000 kN/m2,
# fy = 420 MPa = 420000 kN/m2, Es = 200 GPa.
# ============================================================
import json, os, math

import openseespy.opensees as ops

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")

# ------------------------------------------------------------------
# PARAMETROS DE LA SECCION (columna 70x70 cm)
# ------------------------------------------------------------------
B = 0.70                  # ancho [m]
H = 0.70                  # alto [m]
COVER_BAR = 0.0525        # centro de barra al borde (40 mm rec + 12.5 mm)
FC = 30000.0              # f'c concreto [kN/m2] (30 MPa)
EPS_C0 = 0.0020           # deformacion en fc (compresion positiva)
EPS_CU = 0.0035           # deformacion ultima del concreto
FY = 420000.0             # fy acero [kN/m2] (420 MPa)
ES = 2.0e8                # Es acero [kN/m2] (200 GPa)
EH_RATIO = 0.01           # endurecimiento (Steel01)

# Acero: 8 barras de diametro 25 mm
NBARS = 8
DBAR = 0.025
ABAR = math.pi * DBAR**2 / 4.0
AS_TOTAL = NBARS * ABAR

MAT_CORE = 1
MAT_STEEL = 2
SEC_TAG = 1

MAX_CURV = 0.12           # curvatura maxima [1/m]
NUM_INCR = 500            # incrementos de curvatura
GRID_N = 40               # fibras de concreto por lado


# ------------------------------------------------------------------
# LEYES DE MATERIAL (Compresion POSITIVA)
#   Concrete01: parabola ascendente + rama descendente a 0.85 fc
#   Steel01   : bilineal con endurecimiento EH_RATIO
# ------------------------------------------------------------------
def stress_concrete(eps):
    """Tension del concreto [kN/m2], compresion positiva."""
    if eps < 0.0:
        return 0.0
    if eps <= EPS_C0:
        return FC * (2.0 * eps / EPS_C0 - (eps / EPS_C0) ** 2)
    if eps <= EPS_CU:
        t = (eps - EPS_C0) / (EPS_CU - EPS_C0)
        return FC * (1.0 - 0.15 * t)
    return 0.85 * FC


def stress_steel(eps):
    """Tension del acero [kN/m2], compresion positiva."""
    ey = FY / ES
    if eps >= ey:
        return FY + ES * EH_RATIO * (eps - ey)
    if eps <= -ey:
        return -FY + ES * EH_RATIO * (eps + ey)
    return ES * eps


# ------------------------------------------------------------------
# SECCION DISCRETA: fibras con (x, d, area, material)
#   x = profundidad desde la fibra mas comprimida (arriba)
#   d = distancia al centroide, positiva hacia arriba
# ------------------------------------------------------------------
def build_fibers():
    fibers = []
    n = GRID_N
    dy = B / n
    dz = H / n
    for i in range(n):
        x = (i + 0.5) * dy                       # profundidad (0..H)
        d = H / 2.0 - x                          # + arriba del centroide
        for _ in range(n):
            fibers.append((x, d, dy * dz, "concrete"))
    half_bar = B / 2.0 - COVER_BAR
    coords = [
        (half_bar, half_bar), (-half_bar, half_bar),
        (half_bar, -half_bar), (-half_bar, -half_bar),
        (0.0, half_bar), (0.0, -half_bar),
        (half_bar, 0.0), (-half_bar, 0.0),
    ]
    for (y, z) in coords:
        x = H / 2.0 - y                          # y = distancia + arriba
        d = y
        fibers.append((x, d, ABAR, "steel"))
    return fibers


def axial_resultante(curv, eps0, fibers):
    P = 0.0
    for (x, d, area, mat) in fibers:
        eps = eps0 + curv * d
        sig = stress_concrete(eps) if mat == "concrete" else stress_steel(eps)
        P += sig * area
    return P


def solve_PM(curv, P_target, fibers):
    """Resuelve la deformacion uniforme eps0 que equilibra la carga axial P
    para la curvatura dada. Devuelve (eps0, M). La resultante axial es
    monotona creciente con eps0, asi que la biseccion en [-0.20, 0.05]
    siempre acota a cualquier P alcanzable."""
    lo, hi = -0.20, 0.05
    f_lo = axial_resultante(curv, lo, fibers) - P_target
    f_hi = axial_resultante(curv, hi, fibers) - P_target
    if f_lo * f_hi > 0.0:
        return None, None
    for _ in range(400):
        mid = 0.5 * (lo + hi)
        f_mid = axial_resultante(curv, mid, fibers) - P_target
        if abs(f_mid) < 1e-7:
            lo = hi = mid
            break
        if f_lo * f_mid < 0.0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-10:
            break
    eps0 = 0.5 * (lo + hi)
    M = 0.0
    for (x, d, area, mat) in fibers:
        eps = eps0 + curv * d
        sig = stress_concrete(eps) if mat == "concrete" else stress_steel(eps)
        M += sig * area * d
    return eps0, M


def moment_curvature(P_target, max_curv=MAX_CURV, num=NUM_INCR):
    """Barre la curvatura para carga axial P fija (compresion positiva)."""
    fibers = build_fibers()
    curv = []
    M = []
    for i in range(num + 1):
        k = max_curv * i / num
        _, m = solve_PM(k, P_target, fibers)
        if m is None:
            break
        curv.append(k)
        M.append(m)
    return curv, M


def interact_P(frac_list, max_curv=MAX_CURV):
    """Puntos P-M: P = frac*0.85*fc*Ag, M pico de su curva."""
    Pn0 = 0.85 * FC * B * H
    points = []
    for frac in frac_list:
        Px = frac * Pn0
        curv, M = moment_curvature(Px)
        peak = max(M) if M else 0.0
        points.append({"P_kN": round(Px, 1), "Mmax_kNm": round(peak, 1),
                       "P_frac": frac})
    return points


def define_section_opensees():
    """Define la seccion de fibra equivalente en OpenSees (referencia)."""
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    ops.uniaxialMaterial("Concrete01", MAT_CORE, -FC, -EPS_C0,
                         -0.85 * FC, -EPS_CU)
    ops.uniaxialMaterial("Steel01", MAT_STEEL, FY, ES, EH_RATIO)
    ops.section("Fiber", SEC_TAG)
    ops.patch("quad", MAT_CORE, GRID_N, GRID_N,
              -B / 2.0, -H / 2.0, B / 2.0, -H / 2.0,
              B / 2.0, H / 2.0, -B / 2.0, H / 2.0)
    half_bar = B / 2.0 - COVER_BAR
    coords = [(half_bar, half_bar), (-half_bar, half_bar),
              (half_bar, -half_bar), (-half_bar, -half_bar),
              (0.0, half_bar), (0.0, -half_bar),
              (half_bar, 0.0), (-half_bar, 0.0)]
    for (y, z) in coords:
        ops.fiber(y, z, ABAR, MAT_STEEL)
    ops.wipe()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    Ag = B * H
    As_ratio = AS_TOTAL / Ag
    Pn0 = 0.85 * FC * Ag

    print("=" * 70)
    print("P A R T E   D   -   SECCION DE FIBRA COLUMNA 70x70 (H-30)")
    print("=" * 70)
    print(f"Concreto: f'c = {FC/1000.0:.0f} MPa | "
          f"Acero: fy = {FY/1000.0:.0f} MPa, Es = {ES/1e6:.0f} MPa")
    print(f"Refuerzo: {NBARS} phi {int(DBAR*1000)} mm "
          f"(As={AS_TOTAL*1e4:.2f} cm2, cuantia={As_ratio*100:.2f}%)")
    print(f"Ag = {Ag*1e4:.0f} cm2 | 0.85 f'c Ag = {Pn0:.0f} kN")

    define_section_opensees()

    # 1) M-fi con P = 0 (flexion pura)
    curv0, M0 = moment_curvature(0.0)
    peak0 = max(M0) if M0 else 0.0
    print("-" * 70)
    print("CURVA M-PHI (P = 0, flexion pura):")
    if curv0:
        print(f"  n_puntos      = {len(curv0)}")
        print(f"  M_max (peak)  = {peak0:.1f} kN-m")
        print(f"  curvatura @M_max = "
              f"{curv0[M0.index(max(M0))]:.5f} 1/m")

    # 2) M-fi con P = 0.2 * Pn0
    P_serv = 0.20 * Pn0
    curvS, MS = moment_curvature(P_serv)
    peakS = max(MS) if MS else 0.0
    print("-" * 70)
    print(f"CURVA M-PHI con P = {P_serv:.0f} kN (20% de 0.85 f'c Ag):")
    if curvS:
        print(f"  n_puntos      = {len(curvS)}")
        print(f"  M_max (peak)  = {peakS:.1f} kN-m")

    # 3) primeros puntos de interaccion P-M
    frac_list = [0.0, 0.10, 0.20, 0.30, 0.45, 0.60]
    points = interact_P(frac_list)
    print("-" * 70)
    print("PRIMEROS PUNTOS DE INTERACCION P-M (P vs M_max):")
    print(f"  {'P [kN]':>12s} {'M_max [kN-m]':>12s}")
    for p in points:
        print(f"  {p['P_kN']:12.1f} {p['Mmax_kNm']:12.1f}")

    # interpretacion
    p_peak = max(points, key=lambda x: x["Mmax_kNm"])
    print("-" * 70)
    print("INTERPRETACION:")
    print(f"  - Flexion pura (P=0): M_max = {peak0:.0f} kN-m.")
    print(f"  - Con axial P={P_serv:.0f} kN: M_max = {peakS:.0f} kN-m.")
    print(f"  - El maximo momento de la interaccion ocurre a P="
          f"{p_peak['P_kN']:.0f} kN (M={p_peak['Mmax_kNm']:.0f} kN-m).")
    print("  - La resistencia a flexion crece con pequenos niveles de")
    print("    compresion axial (hasta el punto balanceado) y luego cae.")

    report = {
        "unidades": "kN, m",
        "seccion_m": {"b": B, "h": H},
        "concreto_MPa": FC / 1000.0,
        "acero_MPa": FY / 1000.0,
        "refuerzo": {"n_barras": NBARS, "diametro_mm": int(DBAR * 1000),
                     "As_total_m2": AS_TOTAL, "cuantia": As_ratio},
        "Pn0_kN": Pn0,
        "Mphi_P0": {"curv": [round(c, 6) for c in curv0],
                    "M": [round(m, 1) for m in M0]},
        "Mphi_P_serv": {"P_kN": P_serv,
                        "curv": [round(c, 6) for c in curvS],
                        "M": [round(m, 1) for m in MS]},
        "interaccion_PM": points,
    }
    with open(os.path.join(OUT_DIR, "part_d_fiber.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nResultados guardados en {OUT_DIR}\\part_d_fiber.json")


if __name__ == "__main__":
    main()