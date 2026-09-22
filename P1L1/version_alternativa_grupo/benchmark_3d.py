import openseespy.opensees as ops
import json
import os

ops.wipe()

# ============================================================
# BENCHMARK 3D - Marco Portal de 1 Vano x 1 Vano
# Con losa que descarga sobre vigas
# ============================================================
#
#   Planta (vista superior):
#
#     7 -------- 8 -------- 9      Z = 3.5 m (nivel superior)
#     |          |          |
#     |  Viga X  |  Viga X  |
#     |          |          |
#     4 -------- 5 -------- 6      Z = 3.5 m
#     |          |          |
#     |  Viga Y  |  Viga Y  |
#     |          |          |
#     1 -------- 2 -------- 3      Z = 0.0 m (base)
#
#   Ejes: X = 6.0 m, Y = 5.0 m
#   Altura: Z = 3.5 m
#   Apoyos: Nodos 1-4 empotrados (6 GDL fijos)
#
# ============================================================

ops.model('basic', '-ndm', 3, '-ndf', 6)

# -----------------------------------------------------------
# GEOMETRIA
# -----------------------------------------------------------
Lx = 6.0        # Vano en X [m]
Ly = 5.0        # Vano en Y [m]
H  = 3.5        # Altura del piso [m]
t_losa = 0.15   # Espesor de losa [m]

# -----------------------------------------------------------
# MATERIALES
# -----------------------------------------------------------
Ec = 25e6        # Concreto [kN/m^2]
Es = 200e6       # Acero [kN/m^2]
nu_concreto = 0.2  # Coef. Poisson concreto
nu_acero = 0.3     # Coef. Poisson acero
Gc = Ec / (2.0 * (1.0 + nu_concreto))  # Modulo cortante concreto
Gs = Es / (2.0 * (1.0 + nu_acero))     # Modulo cortante acero
gamma_concreto = 24.0  # Peso unitario [kN/m^3]

# -----------------------------------------------------------
# SECCIONES
# -----------------------------------------------------------
# Columna: 0.35 x 0.35 m
b_col = 0.35
h_col = 0.35
A_col = b_col * h_col
Iy_col = (b_col * h_col**3) / 12.0
Iz_col = (h_col * b_col**3) / 12.0
J_col = 0.141 * b_col * h_col**3  # Aproximacion para seccion rectangular

# Viga en X: 0.25 x 0.50 m (b x h)
bv_x = 0.25
hv_x = 0.50
A_vx = bv_x * hv_x
Iy_vx = (bv_x * hv_x**3) / 12.0
Iz_vx = (hv_x * bv_x**3) / 12.0
J_vx = 0.141 * bv_x * hv_x**3

# Viga en Y: 0.25 x 0.50 m (b x h)
bv_y = 0.25
hv_y = 0.50
A_vy = bv_y * hv_y
Iy_vy = (bv_y * hv_y**3) / 12.0
Iz_vy = (hv_y * bv_y**3) / 12.0
J_vy = 0.141 * bv_y * hv_y**3

# Material elastico para todas las secciones
ops.uniaxialMaterial('Elastic', 1, Es)

print("Propiedades de secciones:")
print(f"  Columna: A={A_col:.4f} m^2, Iy={Iy_col:.6f} m^4, Iz={Iz_col:.6f} m^4, G={Gc:.2e} kN/m^2")
print(f"  Viga X:  A={A_vx:.4f} m^2, Iy={Iy_vx:.6f} m^4, Iz={Iz_vx:.6f} m^4, G={Gs:.2e} kN/m^2")
print(f"  Viga Y:  A={A_vy:.4f} m^2, Iy={Iy_vy:.6f} m^4, Iz={Iz_vy:.6f} m^4, G={Gs:.2e} kN/m^2")
print()

# -----------------------------------------------------------
# NODOS
# -----------------------------------------------------------
# Base (Z = 0): Nodos 1-4
ops.node(1, 0.0, 0.0, 0.0)
ops.node(2, Lx, 0.0, 0.0)
ops.node(3, Lx, Ly, 0.0)
ops.node(4, 0.0, Ly, 0.0)

# Nivel superior (Z = H): Nodos 5-8
ops.node(5, 0.0, 0.0, H)
ops.node(6, Lx, 0.0, H)
ops.node(7, Lx, Ly, H)
ops.node(8, 0.0, Ly, H)

print("Nodos:")
for i in range(1, 9):
    c = ops.nodeCoord(i)
    print(f"  Nodo {i}: ({c[0]:.1f}, {c[1]:.1f}, {c[2]:.1f})")
print()

# -----------------------------------------------------------
# CONDICIONES DE BORDE (Empotrados en la base)
# -----------------------------------------------------------
for i in range(1, 5):
    ops.fix(i, 1, 1, 1, 1, 1, 1)

print("Condiciones de borde: Nodos 1-4 empotrados (6 GDL fijos)")
print()

# -----------------------------------------------------------
# TRANSFORMACIONES GEOMETRICAS
# -----------------------------------------------------------
# Columnas (eje Z)
ops.geomTransf('Linear', 1, 0, -1, 0)    # Col: vecUz global = (0,-1,0) para orientacion Y local
# Vigas en X (eje X)
ops.geomTransf('Linear', 2, 0, 0, 1)     # VigX: vecUz global = (0,0,1) para orientacion Y local
# Vigas en Y (eje Y)
ops.geomTransf('Linear', 3, 1, 0, 0)     # VigY: vecUz global = (1,0,0) para orientacion Y local

print("Transformaciones geometricas:")
print("  Tag 1: Columnas (eje Z)")
print("  Tag 2: Vigas en X")
print("  Tag 3: Vigas en Y")
print()

# -----------------------------------------------------------
# ELEMENTOS
# -----------------------------------------------------------
# Columnas: 1(1-5), 2(2-6), 3(3-7), 4(4-8)
for i, (nodo_i, nodo_f) in enumerate([(1,5), (2,6), (3,7), (4,8)], start=1):
    ops.element('elasticBeamColumn', i, nodo_i, nodo_f,
                A_col, Ec, Gc, J_col, Iy_col, Iz_col, 1)

# Vigas en X: 5(5-6), 6(7-8) - perimetro
for i, (nodo_i, nodo_f) in enumerate([(5,6), (7,8)], start=5):
    ops.element('elasticBeamColumn', i, nodo_i, nodo_f,
                A_vx, Es, Gs, J_vx, Iy_vx, Iz_vx, 2)

# Vigas en Y: 7(6-7), 8(8-5) - perimetro
for i, (nodo_i, nodo_f) in enumerate([(6,7), (8,5)], start=7):
    ops.element('elasticBeamColumn', i, nodo_i, nodo_f,
                A_vy, Es, Gs, J_vy, Iy_vy, Iz_vy, 3)

print("Elementos:")
print("  Columnas: 1(1-5), 2(2-6), 3(3-7), 4(4-8)")
print("  Vigas X:  5(5-6), 6(7-8)")
print("  Vigas Y:  7(6-7), 8(8-5)")
print()

# -----------------------------------------------------------
# CARGAS DE LOSA SOBRE VIGAS (Metodo de areas tributarias)
# -----------------------------------------------------------
# Peso de la losa: gamma * t_losa = 24 * 0.15 = 3.6 kN/m^2
w_losa = gamma_concreto * t_losa  # 3.6 kN/m^2

# Distribucion de cargas segun areas tributarias (losa bidireccional):
#
#   Vigas en X (corto, Ly=5m): area tributaria = Ly/2 = 2.5 m
#     w_viga_X = w_losa * Ly/2 = 3.6 * 2.5 = 9.0 kN/m
#
#   Vigas en Y (largo, Lx=6m): area tributaria = Lx/2 = 3.0 m
#     w_viga_Y = w_losa * Lx/2 = 3.6 * 3.0 = 10.8 kN/m

w_viga_X = w_losa * (Ly / 2.0)  # 9.0 kN/m
w_viga_Y = w_losa * (Lx / 2.0)  # 10.8 kN/m

print("Cargas de losa:")
print(f"  Peso losa: {w_losa:.1f} kN/m^2 (gamma={gamma_concreto} kN/m^3, t={t_losa} m)")
print(f"  Viga X (corto): w = {w_viga_X:.1f} kN/m (tributaria = Ly/2 = {Ly/2:.1f} m)")
print(f"  Viga Y (largo): w = {w_viga_Y:.1f} kN/m (tributaria = Lx/2 = {Lx/2:.1f} m)")
print()

# Aplicar cargas como fuerzas nodales equivalentes
# Cada viga recibe w * L / 2 en cada extremo
Fx5 = w_viga_X * Lx / 2.0  # 27.0 kN por nodo en vigas X
Fx6 = w_viga_Y * Ly / 2.0  # 27.0 kN por nodo en vigas Y

# Suma total por nodo superior
# Nodo 5: 1 viga X (5-6) + 1 viga Y (5-8) = 27.0 + 27.0 = 54.0 kN
# Nodo 6: 1 viga X (6-7) + 1 viga Y (6-10) = 27.0 + 27.0 = 54.0 kN
# Nodo 7: 1 viga X (7-8) + 1 viga Y (7-10) = 27.0 + 27.0 = 54.0 kN
# Nodo 8: 1 viga X (8-5) + 1 viga Y (8-5) = 27.0 + 27.0 = 54.0 kN

carga_nodo = Fx5 + Fx6  # 54.0 kN

print("Cargas nodales equivalentes:")
print(f"  Por viga X en cada nodo: {Fx5:.1f} kN")
print(f"  Por viga Y en cada nodo: {Fx6:.1f} kN")
print(f"  Total por nodo: {carga_nodo:.1f} kN")
print()

# Definir patron de carga
ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)

# Aplicar carga en nodos del nivel superior (5, 6, 7, 8)
# Direccion 3 = Z vertical (hacia abajo = negativo)
for nodo in [5, 6, 7, 8]:
    ops.load(nodo, 0.0, 0.0, -carga_nodo, 0.0, 0.0, 0.0)

carga_total = carga_nodo * 4
print(f"Carga total aplicada: {carga_total:.1f} kN")
print(f"  (4 nodos x {carga_nodo:.1f} kN)")
print()

# -----------------------------------------------------------
# CONFIGURACION DEL ANALISIS
# -----------------------------------------------------------
ops.constraints('Plain')
ops.numberer('RCM')
ops.system('BandSPD')
ops.test('NormDispIncr', 1e-10, 20)
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')

# Ejecutar analisis
ok = ops.analyze(1)

if ok != 0:
    print("ERROR: El analisis no convergio.")
    ops.wipe()
    exit(1)

# Calcular reacciones
ops.reactions()

print("Analisis completado exitosamente.")
print()

# ============================================================
# EXTRAccion DE RESULTADOS
# ============================================================
resultados = {}

print("=" * 70)
print("RESULTADOS DEL BENCHMARK 3D")
print("=" * 70)

# --- DESPLAZAMIENTOS ---
print("\n--- DESPLAZAMIENTOS (Nodos nivel superior) ---")
print(f"{'Nodo':<6} {'Ux [m]':<12} {'Uy [m]':<12} {'Uz [m]':<12} {'RotX':<12} {'RotY':<12} {'RotZ':<12}")
print("-" * 84)

desplazamientos_nodos = {}
for nodo in [5, 6, 7, 8]:
    disp = ops.nodeDisp(nodo)
    desplazamientos_nodos[nodo] = list(disp)
    print(f"{nodo:<6} {disp[0]:<12.6e} {disp[1]:<12.6e} {disp[2]:<12.6e} "
          f"{disp[3]:<12.6e} {disp[4]:<12.6e} {disp[5]:<12.6e}")

resultados['desplazamientos'] = desplazamientos_nodos

# --- DESPLAZAMIENTO PROMEDIO EN Z ---
uz_promedio = sum(ops.nodeDisp(n)[2] for n in [5,6,7,8]) / 4.0
print(f"\nDesplazamiento vertical promedio (Uz): {uz_promedio:.6e} m ({uz_promedio*1000:.4f} mm)")

# --- REACCIONES ---
print("\n--- REACCIONES EN LOS APOYOS ---")
print(f"{'Nodo':<6} {'Rx [kN]':<12} {'Ry [kN]':<12} {'Rz [kN]':<12} {'Mx [kN*m]':<12} {'My [kN*m]':<12} {'Mz [kN*m]':<12}")
print("-" * 84)

reacciones_nodos = {}
for nodo in [1, 2, 3, 4]:
    reac = ops.nodeReaction(nodo)
    reacciones_nodos[nodo] = list(reac)
    print(f"{nodo:<6} {reac[0]:<12.4f} {reac[1]:<12.4f} {reac[2]:<12.4f} "
          f"{reac[3]:<12.4f} {reac[4]:<12.4f} {reac[5]:<12.4f}")

resultados['reacciones'] = reacciones_nodos

# Suma de reacciones
suma_Rx = sum(ops.nodeReaction(i)[0] for i in [1,2,3,4])
suma_Ry = sum(ops.nodeReaction(i)[1] for i in [1,2,3,4])
suma_Rz = sum(ops.nodeReaction(i)[2] for i in [1,2,3,4])
suma_Mx = sum(ops.nodeReaction(i)[3] for i in [1,2,3,4])
suma_My = sum(ops.nodeReaction(i)[4] for i in [1,2,3,4])
suma_Mz = sum(ops.nodeReaction(i)[5] for i in [1,2,3,4])

print(f"\nSuma total de reacciones:")
print(f"  Rx = {suma_Rx:.4f} kN  (esperado: 0.0)")
print(f"  Ry = {suma_Ry:.4f} kN  (esperado: 0.0)")
print(f"  Rz = {suma_Rz:.4f} kN  (esperado: -{carga_total:.1f} kN)")
print(f"  Mx = {suma_Mx:.4f} kN*m (esperado: ~0.0)")
print(f"  My = {suma_My:.4f} kN*m (esperado: ~0.0)")
print(f"  Mz = {suma_Mz:.4f} kN*m (esperado: ~0.0)")

resultados['suma_reacciones'] = {
    'Rx': suma_Rx, 'Ry': suma_Ry, 'Rz': suma_Rz,
    'Mx': suma_Mx, 'My': suma_My, 'Mz': suma_Mz
}

# --- FUERZAS EN ELEMENTOS ---
print("\n--- FUERZAS EN ELEMENTOS ---")
print("  [N: axial, Vy: cortante local Y, Vz: cortante local Z]")
print("  [T: torsion, My: momento local Y, Mz: momento local Z]")
print()

nombres_elem = {
    1: "Col 1 (1-5)", 2: "Col 2 (2-6)", 3: "Col 3 (3-7)", 4: "Col 4 (4-8)",
    5: "VigaX 5 (5-6)", 6: "VigaX 6 (7-8)",
    7: "VigaY 7 (6-7)", 8: "VigaY 8 (8-5)"
}

fuerzas_elementos = {}
for ele in range(1, 9):
    f = ops.eleForce(ele)
    fuerzas_elementos[ele] = list(f)
    print(f"  Elemento {ele} - {nombres_elem[ele]}:")
    print(f"    Extremo I:  N={f[0]:>10.4f}  Vy={f[1]:>10.4f}  Vz={f[2]:>10.4f}  "
          f"T={f[3]:>10.4f}  My={f[4]:>10.4f}  Mz={f[5]:>10.4f}")
    print(f"    Extremo J:  N={f[6]:>10.4f}  Vy={f[7]:>10.4f}  Vz={f[8]:>10.4f}  "
          f"T={f[9]:>10.4f}  My={f[10]:>10.4f}  Mz={f[11]:>10.4f}")
    print()

resultados['fuerzas_elementos'] = fuerzas_elementos

# --- VERIFICACION DE EQUILIBRIO ---
print("=" * 70)
print("VERIFICACION DE EQUILIBRIO")
print("=" * 70)

print(f"\n  Carga total aplicada:   {carga_total:.2f} kN")
print(f"  Suma Rz (reacciones):   {abs(suma_Rz):.2f} kN")
error_equilibrio = abs(abs(suma_Rz) - carga_total) / carga_total * 100
print(f"  Error de equilibrio:    {error_equilibrio:.6f}%")

# Guardar resultados en JSON
resultados['metadata'] = {
    'geometria': {'Lx': Lx, 'Ly': Ly, 'H': H, 't_losa': t_losa},
    'materiales': {'Ec': Ec, 'Es': Es, 'gamma_concreto': gamma_concreto},
    'cargas': {'w_losa': w_losa, 'w_viga_X': w_viga_X, 'w_viga_Y': w_viga_Y,
               'carga_nodo': carga_nodo, 'carga_total': carga_total},
    'verificacion': {
        'suma_Rz': suma_Rz, 'carga_total': carga_total,
        'error_equilibrio_pct': error_equilibrio
    }
}

with open('resultados.json', 'w') as f:
    json.dump(resultados, f, indent=2)

print("\nResultados guardados en 'resultados.json'")
print("=" * 70)

ops.wipe()
