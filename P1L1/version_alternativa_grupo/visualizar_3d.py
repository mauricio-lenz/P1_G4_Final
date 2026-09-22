import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as mpatches

# ============================================================
# GEOMETRIA DEL MODELO 3D
# ============================================================
Lx = 6.0
Ly = 5.0
H  = 3.5

# Nodos
nodos = {
    1: (0, 0, 0), 2: (Lx, 0, 0), 3: (Lx, Ly, 0), 4: (0, Ly, 0),
    5: (0, 0, H), 6: (Lx, 0, H), 7: (Lx, Ly, H), 8: (0, Ly, H)
}

# Elementos: (nodo_i, nodo_f, tipo)
elementos = [
    (1, 5, 'col'), (2, 6, 'col'), (3, 7, 'col'), (4, 8, 'col'),
    (5, 6, 'vigX'), (7, 8, 'vigX'), (6, 7, 'vigY'), (8, 5, 'vigY')
]

# ============================================================
# FIGURA 1: Vista 3D Isometrica
# ============================================================
fig = plt.figure(figsize=(14, 10))
ax = fig.add_subplot(111, projection='3d')

# Colores por tipo de elemento
colores = {'col': '#2196F3', 'vigX': '#F44336', 'vigY': '#FF9800'}

# Dibujar elementos
for ni, nf, tipo in elementos:
    x = [nodos[ni][0], nodos[nf][0]]
    y = [nodos[ni][1], nodos[nf][1]]
    z = [nodos[ni][2], nodos[nf][2]]
    ax.plot(x, y, z, color=colores[tipo], linewidth=4, solid_capstyle='round')

# Dibujar nodos
for nodo, (x, y, z) in nodos.items():
    if nodo <= 4:
        ax.scatter(x, y, z, color='navy', s=120, zorder=5, edgecolors='black', linewidth=1.5)
    else:
        ax.scatter(x, y, z, color='crimson', s=100, zorder=5, edgecolors='black', linewidth=1.5)

# Etiquetas de nodos
for nodo, (x, y, z) in nodos.items():
    offset_x = 0.15 if x < Lx else -0.3
    offset_y = 0.15 if y < Ly else -0.3
    offset_z = 0.2
    ax.text(x + offset_x, y + offset_y, z + offset_z, f'N{nodo}',
           fontsize=10, fontweight='bold', color='darkblue')

# Cargas distribuidas (flechas en las vigas superiores)
for ni, nf, tipo in elementos:
    if tipo.startswith('vig') and nodos[ni][2] == H:
        xi, yi, zi = nodos[ni]
        xf, yf, zf = nodos[nf]
        n_flechas = 5
        for i in range(1, n_flechas):
            t = i / n_flechas
            x = xi + t * (xf - xi)
            y = yi + t * (yf - yi)
            z = zi + 0.8
            ax.quiver(x, y, z, 0, 0, -0.6, color='green', arrow_length_ratio=0.3, linewidth=1.5)

# Simbolo de empotramiento en bases
for nodo in [1, 2, 3, 4]:
    x, y, z = nodos[nodo]
    for i in range(4):
        xi = x - 0.2 + i * 0.1
        ax.plot([xi, xi-0.08], [y, y], [z, z-0.25], 'k-', linewidth=1)
    ax.plot([x-0.25, x+0.25], [y, y], [z, z], 'k-', linewidth=2)

# Ejes de referencia en el origen
ax.quiver(0, 0, 0, 1.5, 0, 0, color='red', linewidth=2, arrow_length_ratio=0.15)
ax.text(1.7, 0, 0, 'X', fontsize=12, color='red', fontweight='bold')
ax.quiver(0, 0, 0, 0, 1.5, 0, color='green', linewidth=2, arrow_length_ratio=0.15)
ax.text(0, 1.7, 0, 'Y', fontsize=12, color='green', fontweight='bold')
ax.quiver(0, 0, 0, 0, 0, 1.5, color='blue', linewidth=2, arrow_length_ratio=0.15)
ax.text(0, 0, 1.7, 'Z', fontsize=12, color='blue', fontweight='bold')

# Leyenda
legend_elements = [
    mpatches.Patch(color='#2196F3', label='Columnas'),
    mpatches.Patch(color='#F44336', label='Vigas en X'),
    mpatches.Patch(color='#FF9800', label='Vigas en Y'),
    plt.Line2D([0], [0], color='green', linewidth=2, label='Cargas (losa)'),
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

# Etiquetas
ax.set_xlabel('X [m]', fontsize=11, labelpad=10)
ax.set_ylabel('Y [m]', fontsize=11, labelpad=10)
ax.set_zlabel('Z [m]', fontsize=11, labelpad=10)
ax.set_title('Benchmark 3D: Marco Portal 1x1 Vano\ncon Losa sobre Vigas',
            fontsize=14, fontweight='bold', pad=20)

# Dimensiones de la planta
ax.text(Lx/2, -0.8, -0.5, f'Lx = {Lx} m', ha='center', fontsize=10, color='gray')
ax.text(-0.8, Ly/2, -0.5, f'Ly = {Ly} m', ha='center', fontsize=10, color='gray', rotation=45)
ax.text(-0.8, -0.8, H/2, f'H = {H} m', ha='center', fontsize=10, color='gray', rotation=90)

# Configuracion de la vista
ax.view_init(elev=25, azim=-55)
ax.set_xlim(-1, Lx+1)
ax.set_ylim(-1, Ly+1)
ax.set_zlim(-1, H+1.5)

plt.tight_layout()
fig.savefig('imagenes/benchmark_3d_vista.png', dpi=150, bbox_inches='tight')
plt.close(fig)

# ============================================================
# FIGURA 2: Vista en planta (Z = H)
# ============================================================
fig2, ax2 = plt.subplots(1, 1, figsize=(8, 7))

# Dibujar elementos en planta
for ni, nf, tipo in elementos:
    if nodos[ni][2] == H:  # Solo nivel superior
        x = [nodos[ni][0], nodos[nf][0]]
        y = [nodos[ni][1], nodos[nf][1]]
        ax2.plot(x, y, color=colores[tipo], linewidth=4, solid_capstyle='round')

# Nodos
for nodo in [5, 6, 7, 8]:
    x, y, z = nodos[nodo]
    ax2.scatter(x, y, color='crimson', s=150, zorder=5, edgecolors='black', linewidth=1.5)
    ax2.text(x, y+0.2, f'N{nodo}', ha='center', fontsize=11, fontweight='bold', color='darkblue')

# Cargas (flechas verdes)
for nodo in [5, 6, 7, 8]:
    x, y, z = nodos[nodo]
    ax2.annotate('', xy=(x, y), xytext=(x, y+0.6),
                arrowprops=dict(arrowstyle='->', color='green', lw=2))
    ax2.text(x, y+0.75, '54 kN', ha='center', fontsize=9, color='green', fontweight='bold')

# Dimensiones
ax2.annotate('', xy=(0, -0.5), xytext=(Lx, -0.5),
            arrowprops=dict(arrowstyle='<->', color='gray', lw=1.2))
ax2.text(Lx/2, -0.7, f'Lx = {Lx} m', ha='center', fontsize=10, color='gray')

ax2.annotate('', xy=(-0.5, 0), xytext=(-0.5, Ly),
            arrowprops=dict(arrowstyle='<->', color='gray', lw=1.2))
ax2.text(-0.7, Ly/2, f'Ly = {Ly} m', ha='center', fontsize=10, color='gray', rotation=90)

# Leyenda
legend_elements = [
    mpatches.Patch(color='#F44336', label='Vigas en X'),
    mpatches.Patch(color='#FF9800', label='Vigas en Y'),
]
ax2.legend(handles=legend_elements, loc='upper right', fontsize=10)

ax2.set_xlim(-1.2, Lx+1.2)
ax2.set_ylim(-1.2, Ly+1.5)
ax2.set_aspect('equal')
ax2.set_xlabel('X [m]', fontsize=11)
ax2.set_ylabel('Y [m]', fontsize=11)
ax2.set_title('Planta del Nivel Superior (Z = 3.5 m)', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
fig2.savefig('imagenes/benchmark_3d_planta.png', dpi=150, bbox_inches='tight')
plt.close(fig2)

print("Imagenes 3D generadas:")
print("  - imagenes/benchmark_3d_vista.png (vista isometrica)")
print("  - imagenes/benchmark_3d_planta.png (vista en planta)")
