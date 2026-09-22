import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

# ============================================================
# DATOS GENERALES
# ============================================================

E = 200e6  # kN/m2, acero ASTM A36 aprox. 200 GPa

# Seccion horizontal cuadrada 20 cm x 20 cm
b = 0.20  # m
A_beam = b * b
I_beam = b**4 / 12

# Seccion vertical doble T
# Cambiar estos valores segun el perfil real
A_col = 0.0060      # m2, ejemplo
I_col = 8.0e-5      # m4, ejemplo

# Cargas
q_col = 17.0        # kN/m, carga horizontal sobre columna superior
P_beam = 20.0       # kN, carga puntual vertical

# ============================================================
# NODOS
# Cada nodo tiene coordenadas x, y
# ============================================================

nodes = {
    0: (0.0, 0.0),   # base empotrada
    1: (0.0, 2.0),   # union columna-viga
    2: (0.0, 5.0),   # cabeza columna
    3: (5.0, 2.0),   # punto donde actua P = 20 kN
    4: (8.0, 2.0),   # apoyo derecho
}

# Elementos: nodo_i, nodo_j, A, I
elements = {
    0: (0, 1, A_col, I_col),    # columna inferior
    1: (1, 2, A_col, I_col),    # columna superior
    2: (1, 3, A_beam, I_beam),  # viga tramo izquierdo
    3: (3, 4, A_beam, I_beam),  # viga tramo derecho
}

ndof_per_node = 3
total_dof = len(nodes) * ndof_per_node

# ============================================================
# FUNCIONES DE ELEMENTO DE PORTICO 2D
# ============================================================

def dof_map(n1, n2):
    return [
        3*n1, 3*n1+1, 3*n1+2,
        3*n2, 3*n2+1, 3*n2+2
    ]


def element_geometry(n1, n2):
    x1, y1 = nodes[n1]
    x2, y2 = nodes[n2]
    dx = x2 - x1
    dy = y2 - y1
    L = np.sqrt(dx**2 + dy**2)
    c = dx / L
    s = dy / L
    return L, c, s


def local_stiffness(E, A, I, L):
    EA_L = E*A/L
    EI = E*I

    k = np.array([
        [ EA_L,        0,          0, -EA_L,        0,          0],
        [    0,  12*EI/L**3,  6*EI/L**2,     0, -12*EI/L**3,  6*EI/L**2],
        [    0,   6*EI/L**2,    4*EI/L,      0,  -6*EI/L**2,    2*EI/L],
        [-EA_L,        0,          0,  EA_L,        0,          0],
        [    0, -12*EI/L**3, -6*EI/L**2,     0,  12*EI/L**3, -6*EI/L**2],
        [    0,   6*EI/L**2,    2*EI/L,      0,  -6*EI/L**2,    4*EI/L]
    ])

    return k


def transformation(c, s):
    T = np.array([
        [ c,  s, 0,  0,  0, 0],
        [-s,  c, 0,  0,  0, 0],
        [ 0,  0, 1,  0,  0, 0],
        [ 0,  0, 0,  c,  s, 0],
        [ 0,  0, 0, -s,  c, 0],
        [ 0,  0, 0,  0,  0, 1]
    ])
    return T


def dibujar_estructura_inicial():
    fig, ax = plt.subplots(figsize=(8, 5))

    # Elementos del marco
    for eid, (n1, n2, A, I) in elements.items():
        x1, y1 = nodes[n1]
        x2, y2 = nodes[n2]
        ax.plot([x1, x2], [y1, y2], color="black", linewidth=3)
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, f"E{eid}", fontsize=9)

    # Nodos
    for nid, (x, y) in nodes.items():
        ax.plot(x, y, "ko", markersize=4)
        ax.text(x + 0.08, y + 0.08, f"N{nid}", fontsize=9)

    # Apoyo empotrado en la base
    x0, y0 = nodes[0]
    ax.plot([x0 - 0.35, x0 + 0.35], [y0, y0], color="black", linewidth=2)
    for i in range(6):
        xi = x0 - 0.3 + i * 0.12
        ax.plot([xi, xi - 0.08], [y0, y0 - 0.18], color="black", linewidth=1)
    ax.text(x0 - 0.55, y0 - 0.45, "Empotramiento", fontsize=9)

    # Apoyo tipo pasador en el extremo derecho
    x4, y4 = nodes[4]
    ax.plot([x4 - 0.25, x4 + 0.25], [y4 - 0.35, y4 - 0.35], color="black", linewidth=2)
    ax.plot([x4, x4 - 0.28, x4 + 0.28, x4], [y4, y4 - 0.35, y4 - 0.35, y4], color="black")
    ax.text(x4 - 0.35, y4 - 0.65, "Pasador", fontsize=9)

    # Carga distribuida horizontal en toda la columna vertical
    for y in np.linspace(nodes[0][1] + 0.35, nodes[2][1] - 0.35, 9):
        ax.arrow(-0.75, y, 0.55, 0.0, head_width=0.08, head_length=0.12,
                 length_includes_head=True, color="tab:red")
    ax.text(-1.25, 2.5, f"q = {q_col:.0f} kN/m", color="tab:red", fontsize=10, rotation=90)

    # Carga puntual vertical en la viga
    xp, yp = nodes[3]
    ax.arrow(xp, yp + 0.9, 0.0, -0.65, head_width=0.16, head_length=0.18,
             length_includes_head=True, color="tab:blue")
    ax.text(xp + 0.15, yp + 0.55, f"P = {P_beam:.0f} kN", color="tab:blue", fontsize=10)

    # Cotas principales
    ax.annotate("5 m", xy=(2.5, 1.65), ha="center", fontsize=9)
    ax.annotate("3 m", xy=(6.5, 1.65), ha="center", fontsize=9)
    ax.annotate("2 m", xy=(-0.45, 1.0), va="center", fontsize=9, rotation=90)
    ax.annotate("3 m", xy=(-0.45, 3.5), va="center", fontsize=9, rotation=90)

    ax.set_title("Estructura inicial del marco 2D")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.set_xlim(-1.6, 8.8)
    ax.set_ylim(-0.8, 5.8)
    plt.tight_layout()
    plt.savefig(BASE_DIR / "estructura_inicial.png", dpi=200)
    plt.show()


def obtener_fuerzas_elementos(U):
    fuerzas = {}

    for eid, (n1, n2, A, I) in elements.items():
        L, c, s = element_geometry(n1, n2)
        T = transformation(c, s)
        k_local = local_stiffness(E, A, I, L)
        dofs = dof_map(n1, n2)

        u_global = U[dofs]
        u_local = T @ u_global
        f_local = k_local @ u_local

        if eid in fixed_loads_local:
            f_local -= fixed_loads_local[eid]

        fuerzas[eid] = f_local

    return fuerzas


def dibujar_deformada(U):
    fig, ax = plt.subplots(figsize=(8, 5))

    max_disp = max(np.hypot(U[3*nid], U[3*nid + 1]) for nid in nodes)
    escala = 0.8 / max_disp if max_disp > 0 else 1.0

    for n1, n2, A, I in elements.values():
        x1, y1 = nodes[n1]
        x2, y2 = nodes[n2]
        ax.plot([x1, x2], [y1, y2], color="0.75", linewidth=2, linestyle="--")

        xd1 = x1 + escala * U[3*n1]
        yd1 = y1 + escala * U[3*n1 + 1]
        xd2 = x2 + escala * U[3*n2]
        yd2 = y2 + escala * U[3*n2 + 1]
        ax.plot([xd1, xd2], [yd1, yd2], color="tab:blue", linewidth=3)

    ax.set_title(f"Deformada del marco 2D, escala = {escala:.1f}x")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.set_xlim(-1.0, 8.8)
    ax.set_ylim(-0.8, 5.8)
    plt.tight_layout()
    plt.savefig(BASE_DIR / "deformada.png", dpi=200)
    plt.show()


def dibujar_diagrama(fuerzas, tipo):
    fig, ax = plt.subplots(figsize=(8, 5))

    valores = []
    diagramas = {}

    for eid, (n1, n2, A, I) in elements.items():
        L, c, s = element_geometry(n1, n2)
        f = fuerzas[eid]
        x_local = np.linspace(0, L, 40)

        w = -q_col if eid in fixed_loads_local else 0.0

        if tipo == "axial":
            y_diag = np.full_like(x_local, f[0])
            titulo = "Diagrama de fuerza axial"
            archivo = "diagrama_axial.png"
            etiqueta = "N [kN]"
        elif tipo == "corte":
            y_diag = f[1] + w * x_local
            titulo = "Diagrama de corte"
            archivo = "diagrama_corte.png"
            etiqueta = "V [kN]"
        else:
            y_diag = f[2] - f[1] * x_local - 0.5 * w * x_local**2
            titulo = "Diagrama de momento flector"
            archivo = "diagrama_momento.png"
            etiqueta = "M [kN*m]"

        valores.extend(np.abs(y_diag))
        diagramas[eid] = (x_local, y_diag)

    max_valor = max(valores) if valores else 1.0
    escala = 0.55 / max_valor if max_valor > 0 else 1.0

    for eid, (n1, n2, A, I) in elements.items():
        x1, y1 = nodes[n1]
        x2, y2 = nodes[n2]
        L, c, s = element_geometry(n1, n2)
        nx, ny = -s, c

        ax.plot([x1, x2], [y1, y2], color="black", linewidth=2)

        x_local, y_diag = diagramas[eid]
        xb = x1 + c * x_local
        yb = y1 + s * x_local
        xd = xb + nx * y_diag * escala
        yd = yb + ny * y_diag * escala

        ax.plot(xd, yd, color="tab:red", linewidth=2)
        ax.fill(np.r_[xb, xd[::-1]], np.r_[yb, yd[::-1]], color="tab:red", alpha=0.18)

        ax.text(xd[0], yd[0], f"{y_diag[0]:.1f}", fontsize=8, color="tab:red")
        ax.text(xd[-1], yd[-1], f"{y_diag[-1]:.1f}", fontsize=8, color="tab:red")

    ax.set_title(f"{titulo} ({etiqueta})")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.set_xlim(-1.8, 9.0)
    ax.set_ylim(-1.0, 6.0)
    plt.tight_layout()
    plt.savefig(BASE_DIR / archivo, dpi=200)
    plt.show()


# ============================================================
# ENSAMBLAJE GLOBAL
# ============================================================

K = np.zeros((total_dof, total_dof))
F = np.zeros(total_dof)

for eid, (n1, n2, A, I) in elements.items():
    L, c, s = element_geometry(n1, n2)
    k_local = local_stiffness(E, A, I, L)
    T = transformation(c, s)
    k_global = T.T @ k_local @ T

    dofs = dof_map(n1, n2)

    for i in range(6):
        for j in range(6):
            K[dofs[i], dofs[j]] += k_global[i, j]

# ============================================================
# CARGAS NODALES
# ============================================================

# Carga puntual de 20 kN hacia abajo en nodo 3
F[3*3 + 1] += -P_beam

# ============================================================
# CARGA DISTRIBUIDA EN TODA LA COLUMNA VERTICAL
# Elementos 0 y 1
# Carga horizontal global +X de 17 kN/m
# Como la columna es vertical, esa carga corresponde a carga local transversal.
# ============================================================

fixed_loads_local = {}

for eid in [0, 1]:
    n1, n2, A, I = elements[eid]
    L, c, s = element_geometry(n1, n2)
    T = transformation(c, s)

    # Para elementos verticales de abajo hacia arriba:
    # eje local x va hacia arriba.
    # carga global +X equivale a carga local y negativa.
    w_local_y = -q_col

    f_fixed_local = np.array([
        0,
        w_local_y * L / 2,
        w_local_y * L**2 / 12,
        0,
        w_local_y * L / 2,
        -w_local_y * L**2 / 12
    ])
    fixed_loads_local[eid] = f_fixed_local

    # Vector equivalente global
    f_fixed_global = T.T @ f_fixed_local

    dofs = dof_map(n1, n2)
    for i in range(6):
        F[dofs[i]] += f_fixed_global[i]

# ============================================================
# CONDICIONES DE APOYO
# ============================================================

restrained_dofs = []

# Nodo 0 empotrado: Ux, Uy, rotacion
restrained_dofs += [0, 1, 2]

# Nodo 4 apoyo tipo pasador: Ux, Uy
restrained_dofs += [3*4, 3*4 + 1]

free_dofs = [i for i in range(total_dof) if i not in restrained_dofs]

# ============================================================
# SOLUCION
# ============================================================

Kff = K[np.ix_(free_dofs, free_dofs)]
Ff = F[free_dofs]

Uf = np.linalg.solve(Kff, Ff)

U = np.zeros(total_dof)
U[free_dofs] = Uf

R = K @ U - F

# ============================================================
# RESULTADOS
# ============================================================

dibujar_estructura_inicial()
fuerzas_elementos = obtener_fuerzas_elementos(U)
dibujar_deformada(U)
dibujar_diagrama(fuerzas_elementos, "axial")
dibujar_diagrama(fuerzas_elementos, "corte")
dibujar_diagrama(fuerzas_elementos, "momento")

print("\n================ DESPLAZAMIENTOS NODALES ================")
for nid in nodes:
    ux = U[3*nid]
    uy = U[3*nid + 1]
    rz = U[3*nid + 2]
    print(f"Nodo {nid}: Ux = {ux:.6e} m, Uy = {uy:.6e} m, Rz = {rz:.6e} rad")

print("\n================ REACCIONES ================")
for dof in restrained_dofs:
    nodo = dof // 3
    tipo = ["Rx", "Ry", "Mz"][dof % 3]
    print(f"Nodo {nodo} {tipo}: {R[dof]:.3f} kN o kN*m")

print("\n================ FUERZAS INTERNAS POR ELEMENTO ================")

for eid, (n1, n2, A, I) in elements.items():
    L, c, s = element_geometry(n1, n2)
    f_local = fuerzas_elementos[eid]

    print(f"\nElemento {eid}: nodo {n1} -> nodo {n2}")
    print(f"Longitud = {L:.3f} m")
    print(f"N_i = {f_local[0]:.3f} kN")
    print(f"V_i = {f_local[1]:.3f} kN")
    print(f"M_i = {f_local[2]:.3f} kN*m")
    print(f"N_j = {f_local[3]:.3f} kN")
    print(f"V_j = {f_local[4]:.3f} kN")
    print(f"M_j = {f_local[5]:.3f} kN*m")
