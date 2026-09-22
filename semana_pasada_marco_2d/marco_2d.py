import openseespy.opensees as ops


# Marco 2D de la figura
# Unidades usadas:
# - Longitud: m
# - Fuerza: tonf
# - Momento: tonf*m

ops.wipe()

# Modelo plano con 3 GDL por nodo: Ux, Uy, Rz
ops.model("basic", "-ndm", 2, "-ndf", 3)

# -------------------------
# Datos del problema
# -------------------------
H = 3.00        # altura de columnas, m
L = 5.00        # luz de la viga, m
EI = 500.0      # rigidez flexural, tonf*m2
w_h = 4.0       # carga horizontal distribuida, tonf/m
w_v = 4.0       # carga vertical distribuida, tonf/m

# Como el enunciado dice EA = infinito, se usa un valor muy grande.
E = 1.0
A = 1.0e12
Iz = EI / E

# -------------------------
# Nodos
# -------------------------
# A: base izquierda
# B: esquina superior izquierda
# E: punto medio de la viga
# C: esquina superior derecha
# D: base derecha
ops.node(1, 0.0, 0.0)        # A
ops.node(2, 0.0, H)          # B
ops.node(3, L / 2.0, H)      # E
ops.node(4, L, H)            # C
ops.node(5, L, 0.0)          # D

# -------------------------
# Apoyos empotrados
# -------------------------
ops.fix(1, 1, 1, 1)  # A
ops.fix(5, 1, 1, 1)  # D

# -------------------------
# Elementos
# -------------------------
ops.geomTransf("Linear", 1)

ops.element("elasticBeamColumn", 1, 1, 2, A, E, Iz, 1)  # columna AB
ops.element("elasticBeamColumn", 2, 2, 3, A, E, Iz, 1)  # viga BE
ops.element("elasticBeamColumn", 3, 3, 4, A, E, Iz, 1)  # viga EC
ops.element("elasticBeamColumn", 4, 5, 4, A, E, Iz, 1)  # columna DC

# -------------------------
# Cargas distribuidas
# -------------------------
ops.timeSeries("Linear", 1)
ops.pattern("Plain", 1, 1)

# Carga horizontal en columna izquierda AB.
# En una columna vertical, la direccion local y queda horizontal.
ops.eleLoad("-ele", 1, "-type", "-beamUniform", -w_h)

# Carga vertical hacia abajo en la viga superior.
# La viga se dividio en dos elementos para medir el desplazamiento en E.
ops.eleLoad("-ele", 2, 3, "-type", "-beamUniform", -w_v)

# -------------------------
# Analisis estatico lineal
# -------------------------
ops.system("BandGeneral")
ops.numberer("Plain")
ops.constraints("Plain")
ops.integrator("LoadControl", 1.0)
ops.algorithm("Linear")
ops.analysis("Static")

resultado = ops.analyze(1)

# -------------------------
# Resultados
# -------------------------
ops.reactions()

delta_ve = ops.nodeDisp(3, 2)  # desplazamiento vertical en E
delta_hc = ops.nodeDisp(4, 1)  # desplazamiento horizontal en C

print("=== MARCO 2D EN OPENSEESPY ===")
print("Resultado del analisis:", resultado)
print("0 significa que el analisis corrio correctamente")
print()

print("--- Desplazamientos pedidos ---")
print(f"Delta_VE = {delta_ve:.6f} m")
print(f"Delta_HC = {delta_hc:.6f} m")
print()

print("--- Reacciones en los apoyos ---")
for nodo, nombre in [(1, "A"), (5, "D")]:
    rx = ops.nodeReaction(nodo, 1)
    ry = ops.nodeReaction(nodo, 2)
    mz = ops.nodeReaction(nodo, 3)
    print(f"Apoyo {nombre}: H = {rx:.3f} tonf, V = {ry:.3f} tonf, M = {mz:.3f} tonf*m")

print()
print("--- Fuerzas internas de elementos ---")
for ele, nombre in [(1, "AB"), (2, "BE"), (3, "EC"), (4, "DC")]:
    print(f"Elemento {nombre}: {ops.eleForce(ele)}")

ops.wipe()
