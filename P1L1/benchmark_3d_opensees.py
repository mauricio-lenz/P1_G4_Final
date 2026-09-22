import matplotlib.pyplot as plt
import json
import math
import openseespy.opensees as ops
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# BENCHMARK 3D OPENSEES - SEMANA 1
# ============================================================
# Unidades:
# - Longitud: m
# - Fuerza: kN
# - Momento: kN*m
# - Esfuerzo: kN/m2


# -------------------------
# 1. Datos del problema
# -------------------------

Lx = 6.0       # vano en direccion X, m
Ly = 5.0       # vano en direccion Y, m
H = 3.2        # altura de piso, m

# Material: acero ASTM A36 aproximado
E = 200e6      # kN/m2
nu = 0.30
G = E / (2 * (1 + nu))

# Secciones propuestas
# Columnas: perfil tubular cuadrado 30x30x1.2 cm
b_col = 0.30
t_col = 0.012
A_col = b_col**2 - (b_col - 2 * t_col)**2
Iy_col = (b_col**4 - (b_col - 2 * t_col)**4) / 12
Iz_col = Iy_col
J_col = 2 * Iy_col

# Vigas: seccion rectangular 25x40 cm
b_viga = 0.25
h_viga = 0.40
A_viga = b_viga * h_viga
Iy_viga = h_viga * b_viga**3 / 12
Iz_viga = b_viga * h_viga**3 / 12
J_viga = Iy_viga + Iz_viga

# Losa como carga superficial equivalente
q_losa = 6.0   # kN/m2, peso propio + sobrecarga supuesta

# Descarga aproximada por ancho tributario hacia las cuatro vigas perimetrales.
# Se reparte la losa entre vigas X e Y para que la carga total sea q_losa*Lx*Ly.
w_vigas_x = q_losa * Ly / 4  # kN/m, vigas paralelas a X
w_vigas_y = q_losa * Lx / 4  # kN/m, vigas paralelas a Y


# -------------------------
# 2. Geometria
# -------------------------

nodes = {
    1: (0.0, 0.0, 0.0),
    2: (Lx, 0.0, 0.0),
    3: (Lx, Ly, 0.0),
    4: (0.0, Ly, 0.0),
    5: (0.0, 0.0, H),
    6: (Lx, 0.0, H),
    7: (Lx, Ly, H),
    8: (0.0, Ly, H),
}

columns = {
    1: (1, 5),
    2: (2, 6),
    3: (3, 7),
    4: (4, 8),
}

beams_x = {
    5: (5, 6),
    7: (8, 7),
}

beams_y = {
    6: (6, 7),
    8: (5, 8),
}

elements = {**columns, **beams_x, **beams_y}

# Apoyos por nodo: (Ux, Uy, Uz, Rx, Ry, Rz)
# 1 = restringido, 0 = libre
# Ejemplos:
# - Empotrado:       (1, 1, 1, 1, 1, 1)
# - Pasador 3D:      (1, 1, 1, 0, 0, 0)
# - Apoyo vertical:  (0, 0, 1, 0, 0, 0)
supports = {
    1: (1, 1, 1, 1, 1, 1),
    2: (1, 1, 1, 1, 1, 1),
    3: (1, 1, 1, 1, 1, 1),
    4: (1, 1, 1, 1, 1, 1),
}

# Cargas puntuales por nodo: (nodo, Fx, Fy, Fz, Mx, My, Mz)
# Importante: usar nodos libres/superiores, por ejemplo 5, 6, 7 u 8.
# Si aplicas una carga en un apoyo fijo, solo cambia la reaccion y no se nota en la deformada.
point_loads = [
    # Ejemplo: carga vertical de 20 kN hacia abajo en el nodo 7.
    # (7, 0.0, 0.0, -20.0, 0.0, 0.0, 0.0),
]


def support_type(fixity):
    if fixity == (1, 1, 1, 1, 1, 1):
        return "fixed"
    if fixity == (1, 1, 1, 0, 0, 0):
        return "pinned"
    if fixity == (0, 0, 1, 0, 0, 0):
        return "vertical"
    if fixity == (0, 1, 1, 0, 0, 0):
        return "roller_x"
    if fixity == (1, 0, 1, 0, 0, 0):
        return "roller_y"
    return "custom"


def support_label(fixity):
    labels = {
        "fixed": "Emp.",
        "pinned": "Pas.",
        "vertical": "Vert.",
        "roller_x": "Rod. X",
        "roller_y": "Rod. Y",
        "custom": "Custom",
    }
    return labels[support_type(fixity)]


def support_style(fixity):
    tipo = support_type(fixity)

    if tipo == "fixed":
        return "s", "tab:orange", 150
    if tipo == "pinned":
        return "^", "tab:purple", 150
    if tipo in ["vertical", "roller_x", "roller_y"]:
        return "o", "tab:brown", 130

    return "D", "tab:gray", 130


def draw_supports_3d(ax, show_labels=True):
    for tag, fixity in supports.items():
        x, y, z = nodes[tag]
        marker, color, size = support_style(fixity)
        ax.scatter(x, y, z - 0.08, marker=marker, s=size, color=color)

        if show_labels:
            label = support_label(fixity)
            fixity_text = "".join(str(value) for value in fixity)
            ax.text(x + 0.12, y + 0.12, z - 0.28, f"{label}\n{fixity_text}", color=color, fontsize=8)


def elemento_vector_unitario(ni, nj):
    xi, yi, zi = nodes[ni]
    xj, yj, zj = nodes[nj]
    dx = xj - xi
    dy = yj - yi
    dz = zj - zi
    largo = math.sqrt(dx**2 + dy**2 + dz**2)
    return dx / largo, dy / largo, dz / largo, largo


def vector_diagrama(ni, nj):
    ux, uy, uz, largo = elemento_vector_unitario(ni, nj)

    if abs(uz) > 0.9:
        return 0.45, 0.0, 0.0

    return 0.0, 0.0, 0.45


def configurar_ejes_3d(ax, titulo):
    ax.set_title(titulo)
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Z [m]")
    ax.set_box_aspect((Lx, Ly, H))
    ax.set_xlim(-1.2, Lx + 1.2)
    ax.set_ylim(-1.2, Ly + 1.2)
    ax.set_zlim(-0.6, H + 1.4)


def build_model():
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    for tag, coord in nodes.items():
        ops.node(tag, *coord)

    # Apoyos configurables por nodo
    for tag, fixity in supports.items():
        ops.fix(tag, *fixity)

    # Transformaciones geometricas.
    # En vigas horizontales se usa vecxz vertical para que el eje local z quede vertical.
    ops.geomTransf("Linear", 1, 1, 0, 0)  # columnas verticales
    ops.geomTransf("Linear", 2, 0, 0, 1)  # vigas horizontales

    for ele, (ni, nj) in columns.items():
        ops.element("elasticBeamColumn", ele, ni, nj, A_col, E, G, J_col, Iy_col, Iz_col, 1)

    for ele, (ni, nj) in beams_x.items():
        ops.element("elasticBeamColumn", ele, ni, nj, A_viga, E, G, J_viga, Iy_viga, Iz_viga, 2)

    for ele, (ni, nj) in beams_y.items():
        ops.element("elasticBeamColumn", ele, ni, nj, A_viga, E, G, J_viga, Iy_viga, Iz_viga, 2)

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)

    for node_tag, fx, fy, fz, mx, my, mz in point_loads:
        ops.load(node_tag, fx, fy, fz, mx, my, mz)

    # Carga de losa descargada a las vigas. En este modelo el eje local z de las
    # vigas horizontales coincide con el eje global Z, por eso Wz es negativo.
    for ele in beams_x:
        ops.eleLoad("-ele", ele, "-type", "-beamUniform", 0.0, -w_vigas_x)

    for ele in beams_y:
        ops.eleLoad("-ele", ele, "-type", "-beamUniform", 0.0, -w_vigas_y)


def run_analysis():
    ops.system("BandGeneral")
    ops.numberer("Plain")
    ops.constraints("Plain")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")
    return ops.analyze(1)


def draw_model():
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")

    for ele, (ni, nj) in elements.items():
        xi, yi, zi = nodes[ni]
        xj, yj, zj = nodes[nj]
        color = "black" if ele in columns else "tab:blue"
        ax.plot([xi, xj], [yi, yj], [zi, zj], color=color, linewidth=3)
        ax.text((xi + xj) / 2, (yi + yj) / 2, (zi + zj) / 2, f"E{ele}", fontsize=8)

    for tag, (x, y, z) in nodes.items():
        ax.scatter(x, y, z, color="black", s=20)
        ax.text(x, y, z + 0.08, f"N{tag}", fontsize=8)

    draw_supports_3d(ax)

    # Losa representada como plano semitransparente
    xs = [0, Lx, Lx, 0, 0]
    ys = [0, 0, Ly, Ly, 0]
    zs = [H, H, H, H, H]
    ax.plot(xs, ys, zs, color="tab:green", linewidth=1.5)
    ax.text(Lx / 2, Ly / 2, H + 0.15, f"Losa q = {q_losa:.1f} kN/m2", color="tab:green")

    # Cargas puntuales configuradas
    for node_tag, fx, fy, fz, mx, my, mz in point_loads:
        x, y, z = nodes[node_tag]
        if abs(fz) > 0:
            dz = -0.8 if fz < 0 else 0.8
            z0 = z - dz
            ax.quiver(x, y, z0, 0.0, 0.0, dz, color="tab:red", arrow_length_ratio=0.25, linewidth=2)
            ax.text(x + 0.15, y + 0.15, z0, f"Pz = {fz:.1f} kN", color="tab:red")

    # Ejes globales
    ax.quiver(-0.8, -0.8, 0.0, 0.7, 0.0, 0.0, color="red", arrow_length_ratio=0.2)
    ax.quiver(-0.8, -0.8, 0.0, 0.0, 0.7, 0.0, color="green", arrow_length_ratio=0.2)
    ax.quiver(-0.8, -0.8, 0.0, 0.0, 0.0, 0.7, color="blue", arrow_length_ratio=0.2)
    ax.text(0.0, -0.8, 0.0, "X global", color="red")
    ax.text(-0.8, 0.0, 0.0, "Y global", color="green")
    ax.text(-0.8, -0.8, 0.8, "Z global", color="blue")

    # Ejes locales representativos del elemento 5. x local va de N5 a N6.
    ax.quiver(0.5, 0.15, H + 0.15, 0.7, 0.0, 0.0, color="darkred", arrow_length_ratio=0.2)
    ax.quiver(0.5, 0.15, H + 0.15, 0.0, 0.7, 0.0, color="darkgreen", arrow_length_ratio=0.2)
    ax.quiver(0.5, 0.15, H + 0.15, 0.0, 0.0, 0.7, color="darkblue", arrow_length_ratio=0.2)
    ax.text(1.25, 0.15, H + 0.15, "x local E5", color="darkred", fontsize=8)
    ax.text(0.5, 0.9, H + 0.15, "y local E5", color="darkgreen", fontsize=8)
    ax.text(0.5, 0.15, H + 0.9, "z local E5", color="darkblue", fontsize=8)

    configurar_ejes_3d(ax, "Benchmark 3D OpenSees - geometria, apoyos, losa y ejes")
    plt.tight_layout()
    plt.savefig(BASE_DIR / "benchmark_3d_modelo.png", dpi=200)
    plt.show()


def obtener_fuerzas_locales():
    return {ele: ops.eleResponse(ele, "localForces") for ele in sorted(elements)}


def valores_diagrama(ele, fuerzas, tipo):
    f = fuerzas[ele]

    if tipo == "axial":
        return f[0], -f[6], "Diagrama axial local P", "diagrama_3d_axial.png", "P [kN]"

    if tipo == "corte":
        return f[2], f[8], "Diagrama de corte local Vz", "diagrama_3d_corte.png", "Vz [kN]"

    return f[4], f[10], "Diagrama de momento local My", "diagrama_3d_momento.png", "My [kN*m]"


def draw_diagram_3d(tipo):
    fuerzas = obtener_fuerzas_locales()
    datos = {ele: valores_diagrama(ele, fuerzas, tipo) for ele in elements}
    max_valor = max(max(abs(vi), abs(vj)) for vi, vj, titulo, archivo, etiqueta in datos.values())
    escala = 0.75 / max_valor if max_valor > 0 else 1.0
    titulo = next(iter(datos.values()))[2]
    archivo = next(iter(datos.values()))[3]
    etiqueta = next(iter(datos.values()))[4]

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")

    for ele, (ni, nj) in elements.items():
        xi, yi, zi = nodes[ni]
        xj, yj, zj = nodes[nj]
        ax.plot([xi, xj], [yi, yj], [zi, zj], color="0.35", linewidth=2)

        vi, vj, _, _, _ = datos[ele]
        vx, vy, vz = vector_diagrama(ni, nj)
        di = vi * escala
        dj = vj * escala

        xdi = xi + vx * di
        ydi = yi + vy * di
        zdi = zi + vz * di
        xdj = xj + vx * dj
        ydj = yj + vy * dj
        zdj = zj + vz * dj

        ax.plot([xdi, xdj], [ydi, ydj], [zdi, zdj], color="tab:red", linewidth=2)
        ax.plot([xi, xdi], [yi, ydi], [zi, zdi], color="tab:red", linewidth=1)
        ax.plot([xj, xdj], [yj, ydj], [zj, zdj], color="tab:red", linewidth=1)
        ax.text(xdi, ydi, zdi, f"{vi:.1f}", color="tab:red", fontsize=7)
        ax.text(xdj, ydj, zdj, f"{vj:.1f}", color="tab:red", fontsize=7)

    draw_supports_3d(ax, show_labels=False)

    configurar_ejes_3d(ax, f"{titulo} ({etiqueta})")
    plt.tight_layout()
    plt.savefig(BASE_DIR / archivo, dpi=200)
    plt.show()


def obtener_resultados_verificacion(resultado):
    ops.reactions()

    carga_puntual_z = sum(fz for node_tag, fx, fy, fz, mx, my, mz in point_loads)
    carga_lineal_total = -2 * w_vigas_x * Lx - 2 * w_vigas_y * Ly + carga_puntual_z
    carga_losa_total = -q_losa * Lx * Ly + carga_puntual_z
    reaccion_z_total = sum(ops.nodeReaction(tag, 3) for tag in [1, 2, 3, 4])
    reaccion_z_nodo_1 = ops.nodeReaction(1, 3)
    uz_nodo_5 = ops.nodeDisp(5, 3)
    fuerzas_locales_e1 = ops.eleResponse(1, "localForces")
    fuerzas_locales_e5 = ops.eleResponse(5, "localForces")

    # Referencias por estimacion manual/simetria del caso simetrico.
    carga_ref = -q_losa * Lx * Ly + carga_puntual_z
    reaccion_z_ref = -carga_ref
    reaccion_base_ref = reaccion_z_ref / 4
    uz_ref = -reaccion_base_ref * H / (A_col * E)
    axial_e1_ref = reaccion_base_ref
    momento_e5_ref_estimado = -w_vigas_x * Lx**2 / 12

    return {
        "resultado": resultado,
        "carga_lineal_total": carga_lineal_total,
        "carga_losa_total": carga_losa_total,
        "carga_puntual_z": carga_puntual_z,
        "carga_ref": carga_ref,
        "reaccion_z_total": reaccion_z_total,
        "reaccion_z_ref": reaccion_z_ref,
        "reaccion_z_nodo_1": reaccion_z_nodo_1,
        "reaccion_base_ref": reaccion_base_ref,
        "uz_nodo_5": uz_nodo_5,
        "uz_ref": uz_ref,
        "axial_e1": fuerzas_locales_e1[0],
        "axial_e1_ref": axial_e1_ref,
        "momento_e5_my_i": fuerzas_locales_e5[4],
        "momento_e5_ref_estimado": momento_e5_ref_estimado,
        "fuerzas_locales_e1": fuerzas_locales_e1,
        "fuerzas_locales_e5": fuerzas_locales_e5,
    }


def error_relativo(valor, referencia):
    if abs(referencia) < 1e-12:
        return abs(valor - referencia)
    return abs((valor - referencia) / referencia)


def escribir_archivo_verificacion(datos):
    lineas = [
        "# Resultados de verificacion - Benchmark 3D OpenSees",
        "",
        "## Estado del analisis",
        "",
        f"- Resultado OpenSees: `{datos['resultado']}`",
        "- `0` significa que el analisis termino sin error numerico.",
        "",
        "## Comparacion con referencias",
        "",
        "| Verificacion | OpenSees | Referencia/estimacion | Error relativo |",
        "|---|---:|---:|---:|",
        f"| Suma de cargas verticales aplicadas [kN] | {datos['carga_lineal_total']:.6f} | {datos['carga_ref']:.6f} | {error_relativo(datos['carga_lineal_total'], datos['carga_ref']):.3e} |",
        f"| Suma de reacciones verticales [kN] | {datos['reaccion_z_total']:.6f} | {datos['reaccion_z_ref']:.6f} | {error_relativo(datos['reaccion_z_total'], datos['reaccion_z_ref']):.3e} |",
        f"| Desplazamiento Uz nodo 5 [m] | {datos['uz_nodo_5']:.9e} | {datos['uz_ref']:.9e} | {error_relativo(datos['uz_nodo_5'], datos['uz_ref']):.3e} |",
        f"| Fuerza axial local elemento 1, extremo i [kN] | {datos['axial_e1']:.6f} | {datos['axial_e1_ref']:.6f} | {error_relativo(datos['axial_e1'], datos['axial_e1_ref']):.3e} |",
        f"| Momento local My elemento 5, extremo i [kN*m] | {datos['momento_e5_my_i']:.6f} | {datos['momento_e5_ref_estimado']:.6f} | {error_relativo(datos['momento_e5_my_i'], datos['momento_e5_ref_estimado']):.3e} |",
        "",
        "## Notas de referencia",
        "",
        "- La suma de cargas se calcula con `q_losa * Lx * Ly`.",
        "- La reaccion vertical por base se estima por simetria: `q_losa * Lx * Ly / 4`.",
        "- El desplazamiento vertical de referencia del nodo 5 se estima como acortamiento axial de la columna: `P*H/(A*E)`.",
        "- El axial local del elemento 1 se compara con la reaccion vertical por simetria.",
        "- El momento de extremo de la viga 5 se compara con una estimacion de viga empotrada-empotrada `wL^2/12`; no es identico porque el marco 3D tiene nudos flexibles y columnas deformables.",
        "",
        "## Fuerzas locales usadas",
        "",
        "Formato local 3D: `[P_i, Vy_i, Vz_i, T_i, My_i, Mz_i, P_j, Vy_j, Vz_j, T_j, My_j, Mz_j]`.",
        "",
        f"- Elemento 1: `{[round(v, 6) for v in datos['fuerzas_locales_e1']]}`",
        f"- Elemento 5: `{[round(v, 6) for v in datos['fuerzas_locales_e5']]}`",
        "",
    ]

    with open(BASE_DIR / "resultados_verificacion_3d.md", "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas))


def exportar_datos_unity():
    datos = {
        "units": "m, kN, kN*m",
        "nodes": [],
        "elements": [],
        "pointLoads": [],
        "supports": [],
    }

    for tag, (x, y, z) in nodes.items():
        datos["nodes"].append({"id": tag, "x": x, "y": y, "z": z})

    for tag, fixity in supports.items():
        datos["supports"].append({
            "node": tag,
            "type": support_type(fixity),
            "ux": fixity[0],
            "uy": fixity[1],
            "uz": fixity[2],
            "rx": fixity[3],
            "ry": fixity[4],
            "rz": fixity[5],
        })

    for node_tag, fx, fy, fz, mx, my, mz in point_loads:
        datos["pointLoads"].append({
            "node": node_tag,
            "fx": fx,
            "fy": fy,
            "fz": fz,
            "mx": mx,
            "my": my,
            "mz": mz,
        })

    for ele, (ni, nj) in sorted(elements.items()):
        fuerzas = ops.eleResponse(ele, "localForces")
        tipo = "columna" if ele in columns else "viga"
        if ele in beams_x:
            carga_distribuida = -w_vigas_x
        elif ele in beams_y:
            carga_distribuida = -w_vigas_y
        else:
            carga_distribuida = 0.0

        datos["elements"].append({
            "id": ele,
            "type": tipo,
            "nodeI": ni,
            "nodeJ": nj,
            "uniformLoad": carga_distribuida,
            "axialI": fuerzas[0],
            "axialJ": -fuerzas[6],
            "shearI": fuerzas[2],
            "shearJ": fuerzas[8],
            "momentI": fuerzas[4],
            "momentJ": fuerzas[10],
        })

    with open(BASE_DIR / "estructura_3d_unity.json", "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2)


def print_results(resultado):
    datos = obtener_resultados_verificacion(resultado)

    print("\n================ BENCHMARK 3D OPENSEES ================")
    print(f"Resultado del analisis: {resultado}")
    print("0 significa que el analisis corrio correctamente")

    print("\n--- Geometria ---")
    print(f"Vano X = {Lx:.2f} m")
    print(f"Vano Y = {Ly:.2f} m")
    print(f"Altura = {H:.2f} m")

    print("\n--- Material ---")
    print(f"E = {E:.3e} kN/m2")
    print(f"G = {G:.3e} kN/m2")

    print("\n--- Secciones ---")
    print(f"Columnas: A = {A_col:.6f} m2, Iy = {Iy_col:.6e} m4, Iz = {Iz_col:.6e} m4, J = {J_col:.6e} m4")
    print(f"Vigas:    A = {A_viga:.6f} m2, Iy = {Iy_viga:.6e} m4, Iz = {Iz_viga:.6e} m4, J = {J_viga:.6e} m4")

    print("\n--- Cargas de losa descargadas a vigas ---")
    print(f"q_losa = {q_losa:.2f} kN/m2")
    print(f"Vigas paralelas a X: w = {w_vigas_x:.2f} kN/m")
    print(f"Vigas paralelas a Y: w = {w_vigas_y:.2f} kN/m")
    print(f"Carga lineal total aplicada = {-2 * w_vigas_x * Lx - 2 * w_vigas_y * Ly:.3f} kN")
    for node_tag, fx, fy, fz, mx, my, mz in point_loads:
        print(f"Carga puntual nodo {node_tag}: Fx={fx:.3f}, Fy={fy:.3f}, Fz={fz:.3f} kN")

    print("\n--- Desplazamientos nodales superiores ---")
    for tag in [5, 6, 7, 8]:
        ux = ops.nodeDisp(tag, 1)
        uy = ops.nodeDisp(tag, 2)
        uz = ops.nodeDisp(tag, 3)
        rx = ops.nodeDisp(tag, 4)
        ry = ops.nodeDisp(tag, 5)
        rz = ops.nodeDisp(tag, 6)
        print(f"Nodo {tag}: Ux={ux:.6e} m, Uy={uy:.6e} m, Uz={uz:.6e} m, Rx={rx:.6e}, Ry={ry:.6e}, Rz={rz:.6e}")

    print("\n--- Reacciones en bases ---")
    total_rx = total_ry = total_rz = 0.0
    for tag in [1, 2, 3, 4]:
        rx = ops.nodeReaction(tag, 1)
        ry = ops.nodeReaction(tag, 2)
        rz = ops.nodeReaction(tag, 3)
        mx = ops.nodeReaction(tag, 4)
        my = ops.nodeReaction(tag, 5)
        mz = ops.nodeReaction(tag, 6)
        total_rx += rx
        total_ry += ry
        total_rz += rz
        print(f"Nodo {tag}: Rx={rx:.3f} kN, Ry={ry:.3f} kN, Rz={rz:.3f} kN, Mx={mx:.3f}, My={my:.3f}, Mz={mz:.3f}")

    print("\n--- Chequeo de equilibrio global ---")
    print(f"Suma reacciones X = {total_rx:.3f} kN")
    print(f"Suma reacciones Y = {total_ry:.3f} kN")
    print(f"Suma reacciones Z = {total_rz:.3f} kN")
    print(f"Carga vertical total = {-q_losa * Lx * Ly + sum(fz for node_tag, fx, fy, fz, mx, my, mz in point_loads):.3f} kN")

    print("\n--- Fuerzas internas por elemento ---")
    print("Formato local 3D: [P_i, Vy_i, Vz_i, T_i, My_i, Mz_i, P_j, Vy_j, Vz_j, T_j, My_j, Mz_j]")
    for ele in sorted(elements):
        valores = ops.eleResponse(ele, "localForces")
        valores_txt = ", ".join(f"{v:.3f}" for v in valores)
        print(f"Elemento {ele}: [{valores_txt}]")

    escribir_archivo_verificacion(datos)
    print("\nArchivo generado: resultados_verificacion_3d.md")


if __name__ == "__main__":
    build_model()
    resultado = run_analysis()
    draw_model()
    draw_diagram_3d("axial")
    draw_diagram_3d("corte")
    draw_diagram_3d("momento")
    exportar_datos_unity()
    print_results(resultado)
    ops.wipe()
