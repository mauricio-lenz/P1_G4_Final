import openseespy.opensees as ops


# Modelo 2D minimo en OpenSeesPy
# Viga simplemente apoyada con una carga vertical en el nodo central.

ops.wipe()

# Modelo 2D con 3 grados de libertad por nodo:
# desplazamiento X, desplazamiento Y y rotacion Z.
ops.model("basic", "-ndm", 2, "-ndf", 3)

# -------------------------
# 1. Nodos
# -------------------------
L = 6.0  # longitud total de la viga, m

ops.node(1, 0.0, 0.0)
ops.node(2, L / 2.0, 0.0)
ops.node(3, L, 0.0)

# -------------------------
# 2. Apoyos
# -------------------------
# Nodo 1: apoyo fijo en X e Y, rotacion libre.
# Nodo 3: apoyo movil vertical, rotacion libre.
ops.fix(1, 1, 1, 0)
ops.fix(3, 0, 1, 0)

# -------------------------
# 3. Propiedades y elementos
# -------------------------
E = 200_000_000_000.0  # modulo de elasticidad del acero, Pa = N/m2
A = 0.02               # area, m2
Iz = 8.0e-5            # inercia, m4

ops.geomTransf("Linear", 1)

# Dos elementos viga-columna elasticos: 1-2 y 2-3.
ops.element("elasticBeamColumn", 1, 1, 2, A, E, Iz, 1)
ops.element("elasticBeamColumn", 2, 2, 3, A, E, Iz, 1)

# -------------------------
# 4. Carga
# -------------------------
P = -10_000.0  # carga vertical hacia abajo, N

ops.timeSeries("Linear", 1)
ops.pattern("Plain", 1, 1)
ops.load(2, 0.0, P, 0.0)

# -------------------------
# 5. Analisis estatico lineal
# -------------------------
ops.system("BandGeneral")
ops.numberer("Plain")
ops.constraints("Plain")
ops.integrator("LoadControl", 1.0)
ops.algorithm("Linear")
ops.analysis("Static")

resultado = ops.analyze(1)

# -------------------------
# 6. Resultados basicos
# -------------------------
print("=== MODELO 2D MINIMO EN OPENSEESPY ===")
print("Resultado del analisis:", resultado)
print("0 significa que el analisis se ejecuto correctamente")
print()

print("--- Desplazamientos nodales ---")
for nodo in [1, 2, 3]:
    ux = ops.nodeDisp(nodo, 1)
    uy = ops.nodeDisp(nodo, 2)
    rz = ops.nodeDisp(nodo, 3)
    print(f"Nodo {nodo}: Ux = {ux:.6e} m, Uy = {uy:.6e} m, Rz = {rz:.6e} rad")

ops.reactions()

print()
print("--- Reacciones en apoyos ---")
for nodo in [1, 3]:
    rx = ops.nodeReaction(nodo, 1)
    ry = ops.nodeReaction(nodo, 2)
    mz = ops.nodeReaction(nodo, 3)
    print(f"Nodo {nodo}: Rx = {rx:.3f} N, Ry = {ry:.3f} N, Mz = {mz:.3f} N*m")

print()
print("--- Fuerzas internas de elementos ---")
for elemento in [1, 2]:
    fuerzas = ops.eleForce(elemento)
    print(f"Elemento {elemento}: {fuerzas}")

ops.wipe()
