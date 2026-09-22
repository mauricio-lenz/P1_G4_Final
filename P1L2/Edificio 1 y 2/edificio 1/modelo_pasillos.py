"""
Modelo Estructural 3D - Dos Pasillos (Vigas + Columnas) - Varios Pisos
======================================================================
Genera la geometria tridimensional de dos pasillos paralelos formados
exclusivamente por vigas y columnas, en MULTIPLES PISOS, lista para
implementarse en OpenSees/OpenSeesPy.

Sistema de coordenadas (todo en METROS en la salida / OpenSees):
  - X : direccion longitudinal de los pasillos
  - Y : direccion transversal
  - Z : direccion vertical

Dimensiones base (dadas en cm, convertidas a metros):
  - 890  cm = 8.90 m  -> ancho del 1er pasillo
  - 725  cm = 7.25 m  -> distancia transversal entre el lado compartido
                         y el lado nuevo del 2do pasillo
  - 500  cm = 5.00 m  -> separacion longitudinal estandar
  - 7            -> numero de espacios longitudinales (8 lineas)

Modificacion especial en el 2do pasillo:
  - Se ELIMINA la 2da columna del lado nuevo (X = 5.00 m).
  - Se AGREGA una columna EXTRA a 251 cm (2.51 m) desde esa linea, o sea
    en X = 7.51 m, entre la 2da y 3ra columna originales (X = 5 y X = 10).
  - Se mantiene una viga transversal en X = 5 mediante un nodo intermedio.

Extensiones:
  - Voladizo de 412 cm hacia Y negativa (Y = -11.37) en X = 0 y X = 7.51.
  - Extension de 1000 cm hacia X negativa (X = -10) en las 3 lineas Y.

Pisos:
  - El modelo se genera en N_PISOS pisos; cada piso tiene su nivel de
    vigas y las columnas van de un nivel al siguiente.

Este script genera la geometria (nodos + elementos frame), aplica cargas
verticales separadas y genera sus visualizaciones.
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import openseespy.opensees as ops

# ============================================================
# CONFIGURACION PARAMETRICA (entradas en cm -> salidas en m)
# ============================================================
ANCHO_PASILLO1_CM = 890.0       # ancho transversal del 1er pasillo (cm)
SEP_TRANSVERSAL_CM = 725.0      # distancia transversal del 2do pasillo (cm)
SEP_LONGITUDINAL_CM = 500.0     # separacion longitudinal estandar (cm)
ESPACIOS_LONG = 7               # numero de espacios longitudinales
ALTURA_PISO_CM = 400.0          # altura de cada piso (cm)
N_PISOS = 4                     # numero de pisos

# Piso 4 (Z=12 a Z=16): SOLO sube los 2 pasillos, el voladizo en el eje X
# (voladizo_xpos) y el tramo/extension hacia X negativo (extension_x). Se
# excluyen del piso 4 solamente los voladizos Y- (Y=-11.37). Los planos
# excluidos en el piso 4:
PISO4_SOLO_PASILLOS = True
PISO4_EXCLUIR_PLANOS = {"voladizo", "extension"}

# En el piso 4 (nivel Z=16), las vigas transversales del pasillo 2 (transv_p2)
# deben quedar en X=-10, 0, 5, 10, 15, 20, 25, 30, 35, 37.55 y 40: se elimina
# entonces la transv_p2 en X=7.51 pero se CONSERVA la columna de X=7.51.
PISO4_ELIMINAR_TRANSV_P2_7_51 = True

# Modificacion especial del 2do pasillo
MOD_ELIMINAR_INDEX = 1          # indice (0-based) de la columna a eliminar (1 = 2da)
D_ESPECIAL_CM = 251.0           # distancia de la columna extra desde la eliminada

# Extension exterior del 2do pasillo (vigas en voladizo de 412 cm)
D_EXT_CM = 412.0                # longitud de la viga de voladizo (cm)

# Voladizo presente en todos los pisos EXCEPTO el piso indicado (1-based).
# None = presente en todos los pisos. Ej. [3] elimina el voladizo en el 3er piso.
VOLADIZO_ELIMINAR_PISOS = [3]

# Voladizo en X positivo (hacia afuera, mas alla de X mayor) en ciertos pisos.
#  Desde el ultimo pilar (X_MAX) se avanza:
#   1) XD_XP_CM (255 cm) -> se colocan PILARES de 1 piso en AMBOS pasillos (Y+ y Y-)
#   2) otros XD_XP_CM2 (245 cm) desde esos pilares -> se colocan OTROS PILARES
#      en ambos pasillos
#  Todo se une con vigas (longitudinales y transversales) a nivel de viga.
VOLADIZO_XP_PISOS = [3, 4]
XD_XP_CM = 255.0                # avance al 1er par de pilares (cm)
XD_XP_CM2 = 245.0               # avance al 2do par de pilares (cm)

# Voladizo del piso 3 sobre el pasillo 2 en el pilar X=0 (Y negativa).
#  Modulo rectangular que sale del pilar (0, Y_P2):
#    - hacia Y negativo una profundidad VD_YP2_PROF_CM (261 cm)
#    - con ancho VD_YP2_ANCHO_CM (220 cm) desde X=0 hacia X positivo
#  Se apoya en los pilares de esquina (Z=piso en el 3er piso) y se cierra
#  con vigas superior e inferior que se unen a la viga del pasillo 2.
VOLADIZO_YP2_PISOS = [3]
VD_YP2_PROF_CM = 261.0          # profundidad hacia Y negativa (cm)
VD_YP2_ANCHO_CM = 220.0         # ancho en X desde X=0 hacia X+ (cm)
# En el nivel inferior (Z=8) del voladizo_yp2 se eliminan el borde exterior
# longitudinal (Y=-9.86, X=0->2.20) y la transversal en X=2.20 (Y=-7.25->-9.86).
VOLADIZO_YP2_ELIMINAR_INFERIOR = True

# Voladizo Y- del pasillo 2 entre X=10 y X=20 (pisos 3 y 4).
#  Marco rectangular apoyado sobre pasillo 2, saliendo 412 cm hacia Y negativa
#  (hasta Y=-11.37), con 2 columnas en las esquinas exteriores y vigas
#  que cierran el marco en cada nivel de viga del piso cubierto. En el piso 4
#  las columnas suben de Z=12 a Z=16 (sin duplicar las vigas de Z=12).
VOLADIZO_YP2_FRAME_PISOS = [3, 4]    # pisos 3 (Z=8 a Z=12) y 4 (Z=12 a Z=16)
VD_YP2_FRAME_X1 = 10.0            # X inicial
VD_YP2_FRAME_X2 = 20.0            # X final

# Extension hacia X negativo (1000 cm)
EXT_X_CM = 1000.0               # largo de la extension hacia X negativo (cm)

# Subterraneo: replica la parte de X negativo (extension_x) un nivel bajo el
# suelo, de Z=0 a Z=-H_SUB (Z negativo). Baja las columnas de las 3 lineas en
# X=-10 (y, si SUBTERRANEO_COLS_X0, tambien las de X=0) hasta Z=-4 y replica
# en el techo (Z=0) las vigas de la extension: longitudinales (0,y)->(X_NEG,y)
# y transversales en X_NEG. No se tocan los pisos de arriba.
SUBTERRANEO = True
SUBTERRANEO_ALTURA_CM = 400.0        # altura del subterraneo (cm)
SUBTERRANEO_COLS_X0 = True           # bajar tambien las columnas de X=0

# Muros estructurales de hormigon armado, presentes de Z=-4 (suelo del sotano)
# hasta Z=16 (azotea), en el tramo de X negativo. Posicion en Y segun MURO_YPOS:
#   - Muro principal (muro_ppal): plano X-Z en Y=_alias_ppal_y, de X=-6.7 a -3.3,
#     espesor 20 cm.
#   - Dos muros extremos (muro_ext): planos Y-Z en X=-3.3 y X=-6.7, de
#     Y=_alias_ext_y1 a Y=_alias_ext_y2, espesor 25 cm.
# Nota: este OpenSeesPy no soporta cascarones, por lo que la geometria del muro
# se exporta (muros.json / HTML) y en OpenSees se modela con vigas equivalentes.
MUROS_ESTRUCTURALES = True
# Posicion del muro en Y (transversal):
#   "NEG"  -> lado negativo: muro principal en Y=-4.945, extremos Y=-4.945 a -3.37
#   "POS"  -> lado positivo (espejo, mismas dimensiones): muro principal en Y=+5.00,
#             extremos de Y=+5.00 a Y=+3.425 (ancho transversal 1.575 m, apuntando
#             hacia Y=0 sin llegar)
#   "AMBOS"-> genera los DOS muros a la vez (negativo + positivo)
MURO_YPOS = "AMBOS"
MURO_PPAL_Y_M = -4.945        # Y del muro principal (plano X-Z)
MURO_PPAL_X1_M = -6.7         # X inicial del muro principal
MURO_PPAL_X2_M = -3.3         # X final del muro principal
MURO_PPAL_T_CM = 20.0         # espesor muro principal (cm)
MURO_EXT_Y_INF_M = -4.945     # Y inferior de los muros extremos (arrancan del principal)
MURO_EXT_Y_SUP_M = -3.37      # Y superior de los muros extremos
MURO_EXT_T_CM = 25.0          # espesor muros extremos (cm)
MURO_Z_INF = -4.0             # cota inferior (suelo del sotano)
MURO_Z_SUP = 16.0             # cota superior (azotea)

# Lista de configuraciones de muro a generar (cada una: ppal_y, ext_y1, ext_y2)
_ancho_ext = MURO_EXT_Y_SUP_M - MURO_EXT_Y_INF_M   # 1.575 m (ancho transversal)
_MURO_NEG = dict(ppal_y=MURO_PPAL_Y_M, ext_y=[MURO_EXT_Y_INF_M, MURO_EXT_Y_SUP_M])
_MURO_POS = dict(ppal_y=5.0, ext_y=[5.0, 5.0 - _ancho_ext])   # 5.0 a 3.425
if MURO_YPOS == "NEG":
    _MURO_CONFIGS = [_MURO_NEG]
elif MURO_YPOS == "POS":
    _MURO_CONFIGS = [_MURO_POS]
else:                                     # "AMBOS" (y cualquier otro valor)
    _MURO_CONFIGS = [_MURO_NEG, _MURO_POS]

# ============================================================
# LOSAS DE PISO (diafragmas y cargas gravitacionales)
#   Se generan en los niveles de viga (Z en Z_VIGAS) y en el techo
#   del subterraneo (Z=0), rellenando cada bahia de la cuadricula de
#   vigas entre los 3 ejes Y principales (P1, COMP, P2). Se subdivide
#   la cuadricula en TODAS las lineas de viga (aunque no haya columna,
#   e.g. X=5,15,25, o la columna extra X=7.51 donde exista).
#   Las bahias se subdividen para representar los huecos interiores de los
#   muros estructurales en la extension X negativa.
LOSAS = True
LOSA_ESPESOR_M = 0.15        # espesor de losa (m) - referencia
# Losas en los niveles de vigas (Z=H,2H,...) y en el techo del sotano (Z=0)

# Cargas gravitacionales de losas (kN/m2).
# La carga muerta incluye el peso propio de la losa y una carga permanente
# adicional (terminaciones, tabiqueria y cielo). La carga viva es independiente.
PESO_UNITARIO_LOSA = 25.0             # kN/m3, hormigon armado
CARGA_MUERTA_ADICIONAL = 1.0          # kN/m2
CARGA_VIVA = 2.0                       # kN/m2
FACTOR_COMB_D = 1.2                   # combinacion ultima: 1.2D + 1.6L
FACTOR_COMB_L = 1.6

# Eliminacion en el 3er piso (Z=12), pasillo 2 (Y=P2): se retiran la 3ra columna
# (contando la de X negativo como 1ra) y la viga transversal que va hacia el
# pasillo 1 en esa columna. Las columnas de la linea del pasillo 2 son:
#   X negativo(1ra), X=0(2da), X_EXTRA=7.51(3ra), ...
# y la viga transversal asociada es la transv_p2 (Y=P2 -> Y_COMP) en ese X.
PISO3_ELIMINAR_BARRAS_P2 = True
ELIM_P2_COL_X_M = 7.51           # 7.51 m: 3ra columna del pasillo 2 a eliminar
ELIM_P2_VIGA_TRANS_Y_P2 = True    # eliminar la transv_p2 hacia el pasillo 1 en ese X


# Secciones transversales (cm) y material (MPa)
SEC_COL_B = 70.0                # base columna (cm)
SEC_COL_H = 70.0                # altura columna (cm)
SEC_VIG_B = 60.0                # base viga (cm)
SEC_VIG_H = 80.0                # altura viga (cm)
SEC_VIG_VOL_P2_B = 30.0         # base viga exterior voladizo piso 2 (cm)
SEC_VIG_VOL_P2_H = 45.0         # altura viga exterior voladizo piso 2 (cm)
MODULO_E_MPA = 23500.0          # modulo de elasticidad (MPa)
POISSON = 0.2                   # coeficiente de Poisson

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# DERIVACION DE COORDENADAS (metros)
# ============================================================
ANCHO_P1 = ANCHO_PASILLO1_CM / 100.0      # 8.90 m
SEP_T = SEP_TRANSVERSAL_CM / 100.0        # 7.25 m
SEP_L = SEP_LONGITUDINAL_CM / 100.0       # 5.00 m
H_PISO = ALTURA_PISO_CM / 100.0           # 4.00 m
D_ESP = D_ESPECIAL_CM / 100.0             # 2.51 m
D_EXT = D_EXT_CM / 100.0                  # 4.12 m
EXT_X = EXT_X_CM / 100.0                  # 10.00 m

# Secciones en metros + propiedades seccionales (orientacion: b=>Y, h=>Z)
b_col, h_col = SEC_COL_B / 100.0, SEC_COL_H / 100.0     # 0.70 x 0.70
b_vig, h_vig = SEC_VIG_B / 100.0, SEC_VIG_H / 100.0     # 0.60 x 0.80
b_vig_vp2, h_vig_vp2 = SEC_VIG_VOL_P2_B / 100.0, SEC_VIG_VOL_P2_H / 100.0  # 0.30 x 0.45
EC = MODULO_E_MPA                   # en kN/m2 queda 23500 * 1000 -> ver nota
G_COL = EC / (2 * (1 + POISSON))
G_VIG = EC / (2 * (1 + POISSON))

# Posiciones longitudinales de las lineas estructurales
X_LINEAS = [i * SEP_L for i in range(ESPACIOS_LONG + 1)]  # 0,5,...,35
N_LINEAS = len(X_LINEAS)  # 8

# Columna eliminada y columna extra del 2do pasillo
X_ELIMINADA = X_LINEAS[MOD_ELIMINAR_INDEX]   # 5.00 m
X_EXTRA = X_ELIMINADA + D_ESP                 # 7.51 m

# Posiciones transversales
Y_P1 = ANCHO_P1        # +8.90 m  (lado 1er pasillo)
Y_COMP = 0.0           # compartida
Y_P2 = -SEP_T          # -7.25 m  (lado nuevo 2do pasillo)
Y_EXT = Y_P2 - D_EXT   # -11.37 m (voladizo)

# X de extension negativa
X_NEG = -EXT_X         # -10.00 m

# Posiciones X por fila (puntos de VIGA, incluyen nodos intermedios)
X_P1 = list(X_LINEAS)
X_COMP = sorted(set(X_LINEAS) | {X_EXTRA})
X_P2_NODOS = sorted(set(X_LINEAS) | {X_EXTRA})
X_P2_COLS = sorted((set(X_LINEAS) - {X_ELIMINADA}) | {X_EXTRA})  # columnas pasillo 2
X_EXT_COLS = sorted({X_LINEAS[0], X_EXTRA})   # voladizo: X=0 y X=7.51

# Voladizo X+ : posiciones de los pares de pilares (metros)
X_EDGE_XP = X_LINEAS[-1]                                   # 35.00 m (ultimo pilar)
XD_XP = XD_XP_CM / 100.0                                   # 2.55 m
XD_XP2 = XD_XP_CM2 / 100.0                                 # 2.45 m
X_PILAR_A = X_EDGE_XP + XD_XP                              # 37.55 m (1er par de pilares)
X_PILAR_B = X_PILAR_A + XD_XP2                             # 38.00 m (2do par de pilares)
X_TIP_COMP = X_PILAR_A                                     # compartida acompaña al 1er par

# Eliminacion de los voladizos del piso 3 (solo columnas y vigas de abajo).
#  Se retiran del piso 3 las COLUMNAS (Z=8 a Z=12) y las VIGAS del nivel
#  inferior (Z=8) de los voladizos:
#    - voladizo_xpos       (X+ : pilares en X=37.55 y X=40)
#    - voladizo_yp2_frame  (Y- : X=10 a X=20, columnas en Y=-11.37)
#  El piso 4 (Z=12 a Z=16) de esos voladizos se conserva intacto: se dejan
#  las columnas Z=12->16 y las vigas de los niveles Z=12 y Z=16.
ELIMINAR_VOLADIZOS_PISO3 = True

# Voladizo Y- del pasillo 2 en el pilar X=0 (metros)
VD_X0 = X_LINEAS[0]                                        # 0.00 m (pilar de arranque)
VD_X2 = VD_X0 + VD_YP2_ANCHO_CM / 100.0                    # 2.20 m (ancho)
VD_Y0 = Y_P2                                               # -7.25 m (linea pasillo 2)
VD_YFAR = VD_Y0 - VD_YP2_PROF_CM / 100.0                   # -9.86 m (borde exterior)

# Voladizo del piso 2 (Z=8) en el lado Y negativo del pasillo 2: 3 vigas
# transversales que salen hacia Y negativa (VD_YP2_P2_PROF_CM, 246 cm) en
# X=10, 15 y 20, desde la linea del pasillo 2 (Y=-7.25) hasta
# Y_P2 - 2.46 = -9.71 m. Por fuera se unen con una viga longitudinal en
# Y=-9.71 (de X=10 a X=20) que usa UNA SECCION DISTINTA (30x45 cm).
VOLADIZO_YP2_P2 = True
VOLADIZO_YP2_P2_PISOS = [2]          # piso 2 (nivel de viga Z=8)
VD_YP2_P2_PROF_CM = 246.0            # 246 cm hacia Y negativa
VD_YP2_P2_XS = [10.0, 15.0, 20.0]    # X de las 3 vigas hacia afuera

# ============================================================
# GEOMETRIA PLANA: lineas y ligaduras que se repiten por piso
# ============================================================
def construir_geometria_plana():
    """
    Define la topologia (nodos vs vigas) de la estructura en 2D (un nivel).
    Devuelve:
      - puntos_col  : lista de (x,y) donde EXISTE columna (base/uso)
      - segmentos   : lista de dicts {tipo, plano, a, b} donde a=lista y fila, etc.
      - puntos_viga : conjunto de (x,y) que tienen nodo a nivel de viga
    """
    puntos_col = set()
    puntos_viga = set()
    segmentos = []          # {tipo, plano, p1, p2} con p=(x,y)

    def add_viga(tipo, plano, p1, p2):
        segmentos.append({"tipo": tipo, "plano": plano, "p1": p1, "p2": p2})
        puntos_viga.add(p1)
        puntos_viga.add(p2)

    # ---- Columnas (base) ----
    for x in X_P1:
        puntos_col.add((x, Y_P1))
    for x in X_LINEAS:
        puntos_col.add((x, Y_COMP))
    for x in X_P2_COLS:
        puntos_col.add((x, Y_P2))
    for x in X_EXT_COLS:          # voladizo
        puntos_col.add((x, Y_EXT))
    for y in (Y_P1, Y_COMP, Y_P2):  # extension x negativa
        puntos_col.add((X_NEG, y))

    # Puntos de viga (incluye nodos intermedios sin columna)
    for x in X_P1:
        puntos_viga.add((x, Y_P1))
    for x in X_COMP:
        puntos_viga.add((x, Y_COMP))
    for x in X_P2_NODOS:
        puntos_viga.add((x, Y_P2))
    for x in X_EXT_COLS:
        puntos_viga.add((x, Y_EXT))
    for y in (Y_P1, Y_COMP, Y_P2):
        puntos_viga.add((X_NEG, y))

    # ---- Vigas longitudinales (paralelas a X) ----
    for i in range(len(X_P1) - 1):
        add_viga("viga_longitudinal", "pasillo_1",
                 (X_P1[i], Y_P1), (X_P1[i + 1], Y_P1))
    for i in range(len(X_COMP) - 1):
        add_viga("viga_longitudinal", "compartida",
                 (X_COMP[i], Y_COMP), (X_COMP[i + 1], Y_COMP))
    for i in range(len(X_P2_NODOS) - 1):
        add_viga("viga_longitudinal", "pasillo_2",
                 (X_P2_NODOS[i], Y_P2), (X_P2_NODOS[i + 1], Y_P2))
    # Voladizo: viga longitudinal entre X=0 y X=7.51 en Y_EXT
    for i in range(len(X_EXT_COLS) - 1):
        add_viga("viga_longitudinal", "extension",
                 (X_EXT_COLS[i], Y_EXT), (X_EXT_COLS[i + 1], Y_EXT))
    # Extension X negativa: (0,y) -> (X_NEG,y)
    for y in (Y_P1, Y_COMP, Y_P2):
        add_viga("viga_longitudinal", "extension_x", (0.0, y), (X_NEG, y))

    # ---- Vigas transversales (paralelas a Y) ----
    for x in X_P1:
        add_viga("viga_transversal", "transv_p1", (x, Y_COMP), (x, Y_P1))
    for x in X_P2_NODOS:
        add_viga("viga_transversal", "transv_p2", (x, Y_P2), (x, Y_COMP))
    for x in X_EXT_COLS:
        add_viga("viga_transversal", "voladizo", (x, Y_P2), (x, Y_EXT))
    # Extension X negativa: transversales en X_NEG entre las 3 lineas
    for i in range(len([Y_P1, Y_COMP, Y_P2]) - 1):
        add_viga("viga_transversal", "extension_x",
                 (X_NEG, [Y_P1, Y_COMP, Y_P2][i]),
                 (X_NEG, [Y_P1, Y_COMP, Y_P2][i + 1]))

    return puntos_col, puntos_viga, segmentos


# ============================================================
# 1. CONSTRUCCION DE NODOS Y ELEMENTOS (multi-piso)
# ============================================================
def construir_modelo():
    """
    Genera nodos y elementos para N_PISOS pisos.
    Cad citas de viga: Z = H_PISO, 2*H_PISO, ... (nivel de vigas por piso).
    Columnas: de Z_i a Z_{i+1} en cada punto de columna.
    Vigas: en cada nivel de viga, todos los segmentos de la geometria plana.
    """
    puntos_col, puntos_viga, segmentos = construir_geometria_plana()

    # Piso 1 (Z=0 a Z=4): en las 3 lineas las columnas deben quedar solo en
    # X = -10, 0, 10, 20, 30, 35. Se eliminan X=5,15,25 en Y=8.90 y Y=0, y
    # X=7.51,15,25 en Y=-7.25. Tambien se eliminan las del voladizo en
    # Y=-11.37 (columnas en X=0 y X=7.51 de ese nivel).
    piso1_cols_eliminar = {
        (5.0, Y_P1), (15.0, Y_P1), (25.0, Y_P1),
        (5.0, 0.0),  (15.0, 0.0),  (25.0, 0.0),
        (ELIM_P2_COL_X_M, Y_P2), (15.0, Y_P2), (25.0, Y_P2),
        (0.0, Y_EXT), (ELIM_P2_COL_X_M, Y_EXT),
    }

    # Piso 2 (Z=4 a Z=8): en Y=0 y el lado Y positivo (Y=+8.90) las columnas
    # deben quedar solo en X=-10, 0, 10, 20, 30, 35 (se eliminan X=5,15,25);
    # en el lado Y negativo (Y=-7.25) deben quedar en X=-10, 0, 7.51, 10, 20,
    # 30, 35 (se eliminan X=15,25, conservando la extra X=7.51). El voladizo
    # Y=-11.37 del piso 2 NO se modifica.
    piso2_cols_eliminar = {
        (5.0, Y_P1), (15.0, Y_P1), (25.0, Y_P1),
        (5.0, 0.0),  (15.0, 0.0),  (25.0, 0.0),
        (15.0, Y_P2), (25.0, Y_P2),
    }

    # Piso 3 (Z=8 a Z=12): las columnas deben quedar en las MISMAS X en las 3
    # lineas de Y (Y=+8.90, Y=0 y Y=-7.25): X=-10, 0, 10, 20, 30, 35. Se eliminan
    # X=5,15,25 en Y=8.90 y Y=0, y X=15,25 en Y=-7.25 (la X=7.51 del pasillo 2 ya
    # se elimina por PISO3_ELIMINAR_BARRAS_P2 y la X=5 no existe en el pasillo 2).
    piso3_cols_eliminar = {
        (5.0, Y_P1), (15.0, Y_P1), (25.0, Y_P1),
        (5.0, 0.0),  (15.0, 0.0),  (25.0, 0.0),
        (15.0, Y_P2), (25.0, Y_P2),
    }

    # Piso 4 (Z=12 a Z=16): las columnas de las 3 lineas principales (Y=+8.90,
    # Y=0, Y=-7.25) quedan en X=-10, 0, 10, 20, 30, 35, CONSERVANDO las columnas
    # del voladizo X+ (X=37.55 y X=40) y las del voladizo Y- (Y=-11.37, X=10 y 20).
    # Se eliminan X=5,15,25 en Y=8.90 y Y=0, y X=7.51,15,25 en Y=-7.25.
    piso4_cols_eliminar = {
        (5.0, Y_P1), (15.0, Y_P1), (25.0, Y_P1),
        (5.0, 0.0),  (15.0, 0.0),  (25.0, 0.0),
        (ELIM_P2_COL_X_M, Y_P2), (15.0, Y_P2), (25.0, Y_P2),
    }

    # Cotas verticales (niveles)
    Z_NIVELES = [i * H_PISO for i in range(N_PISOS + 1)]   # 0, 4, 8, 12, 16
    Z_VIGAS = Z_NIVELES[1:]                                # 4, 8, 12, 16

    nodos = {}
    nid = 0

    def add_nodo(x, y, z):
        nonlocal nid
        clave = (x, y, round(z, 9))
        if clave in nodos:            # idempotente: nodos compartidos entre pisos
            return nodos[clave]
        nid += 1
        nodos[clave] = nid
        return nid

    # Base (Z=0) en cada punto de columna
    for (x, y) in sorted(puntos_col):
        add_nodo(x, y, 0.0)
    # Nivel de vigas en cada punto de viga, en cada piso
    for z in Z_VIGAS:
        for (x, y) in sorted(puntos_viga):
            add_nodo(x, y, z)

    elems = []
    eid = 0

    def add(tipo, ni, nj, plano):
        nonlocal eid
        eid += 1
        elems.append({"id": eid, "tipo": tipo, "nodo_i": ni, "nodo_j": nj,
                      "plano": plano})

    def nid_xy(x, y, z):
        return nodos[(x, y, round(z, 9))]

    # Voladizo: coordenadas Y de los puntos de columna/viga del voladizo
    VOLADIZO_PLANOS = {"voladizo", "extension"}   # vigas del voladizo
    VOLADIZO_Y = Y_EXT                            # lineas Y del voladizo

    def es_voladizo_col(x, y):
        return abs(y - Y_EXT) < 1e-9

    def es_voladizo_viga(s):
        return s["plano"] in VOLADIZO_PLANOS

    # --- COLUMNAS: entre niveles consecutivos, en cada punto de columna ---
    def es_elim_p2(x, y, piso):
        """Columna a eliminar en el pasillo 2 (Y negativa) en el piso 3."""
        return (PISO3_ELIMINAR_BARRAS_P2 and piso == 3
                and abs(x - ELIM_P2_COL_X_M) < 1e-9 and abs(y - Y_P2) < 1e-9)

    def es_elim_viga_p2(s, piso):
        """Viga transversal hacia el pasillo 1 (transv_p2) en la columna a eliminar."""
        if not (PISO3_ELIMINAR_BARRAS_P2 and piso == 3
                and s["tipo"] == "viga_transversal" and s["plano"] == "transv_p2"):
            return False
        return (abs(min(s["p1"][0], s["p2"][0]) - ELIM_P2_COL_X_M) < 1e-9
                and abs(max(s["p1"][0], s["p2"][0]) - ELIM_P2_COL_X_M) < 1e-9)

    def excluir_p4(x, y):
        """En el piso 4 se excluyen solo las columnas del voladizo Y- (Y=-11.37);
        el voladizo X+ y la extension X negativa SI suben."""
        return (PISO4_SOLO_PASILLOS and es_voladizo_col(x, y))

    def excluir_p4_plano(s):
        """En el piso 4 se excluyen los planos de voladizo y extension."""
        return PISO4_SOLO_PASILLOS and s["plano"] in PISO4_EXCLUIR_PLANOS

    def es_elim_viga_transv_p2_p4(s, piso):
        """En el piso 4 se elimina la viga transversal del pasillo 2 (transv_p2)
        en X=7.51, pero se conserva la columna de X=7.51."""
        return (PISO4_ELIMINAR_TRANSV_P2_7_51 and piso == 4
                and s["tipo"] == "viga_transversal" and s["plano"] == "transv_p2"
                and abs(min(s["p1"][0], s["p2"][0]) - ELIM_P2_COL_X_M) < 1e-9
                and abs(max(s["p1"][0], s["p2"][0]) - ELIM_P2_COL_X_M) < 1e-9)

    def es_elim_col_p1(x, y, piso):
        """Piso 1: columnas excluidas (deben quedar solo en X=-10,0,10,20,30,35)."""
        if piso != 1:
            return False
        return any(abs(x - ex) < 1e-9 and abs(y - ey) < 1e-9
                   for ex, ey in piso1_cols_eliminar)

    def es_elim_col_p2(x, y, piso):
        """Piso 2: en Y=0 y Y=+8.90 las columnas quedan en X=-10,0,10,20,30,35
        (se eliminan X=5,15,25); en Y=-7.25 quedan en X=-10,0,7.51,10,20,30,35
        (se eliminan X=15,25, conservando la extra X=7.51). El voladizo Y=-11.37
        del piso 2 no se modifica."""
        if piso != 2:
            return False
        return any(abs(x - ex) < 1e-9 and abs(y - ey) < 1e-9
                   for ex, ey in piso2_cols_eliminar)

    def es_elim_col_p3(x, y, piso):
        """Piso 3: las columnas quedan en las MISMAS X en las 3 lineas de Y
        (Y=+8.90, Y=0, Y=-7.25): X=-10,0,10,20,30,35."""
        if piso != 3:
            return False
        return any(abs(x - ex) < 1e-9 and abs(y - ey) < 1e-9
                   for ex, ey in piso3_cols_eliminar)

    def es_elim_col_p4(x, y, piso):
        """Piso 4: las columnas de las 3 lineas principales (Y=+8.90, Y=0,
        Y=-7.25) quedan en X=-10,0,10,20,30,35 CONSERVANDO el voladizo X+
        (X=37.55 y X=40) y el voladizo Y- (Y=-11.37, X=10 y 20)."""
        if piso != 4:
            return False
        return any(abs(x - ex) < 1e-9 and abs(y - ey) < 1e-9
                   for ex, ey in piso4_cols_eliminar)

    for (x, y) in sorted(puntos_col):
        for i in range(N_PISOS):
            piso = i + 1
            if es_voladizo_col(x, y):
                if piso in VOLADIZO_ELIMINAR_PISOS:
                    continue
            if piso == 4 and excluir_p4(x, y):
                continue
            if es_elim_col_p1(x, y, piso):
                continue
            if es_elim_col_p2(x, y, piso):
                continue
            if es_elim_col_p3(x, y, piso):
                continue
            if es_elim_col_p4(x, y, piso):
                continue
            if es_elim_p2(x, y, piso):
                continue
            add("columna", nid_xy(x, y, Z_NIVELES[i]),
                nid_xy(x, y, Z_NIVELES[i + 1]), "vertical")

    # --- VIGAS: en cada nivel de viga, todos los segmentos ---
    for z in Z_VIGAS:
        piso = Z_VIGAS.index(z) + 1
        for s in segmentos:
            if es_voladizo_viga(s) and piso in VOLADIZO_ELIMINAR_PISOS:
                continue
            if piso == 4 and excluir_p4_plano(s):
                continue
            if es_elim_viga_transv_p2_p4(s, piso):
                continue
            if es_elim_viga_p2(s, piso):
                continue
            add(s["tipo"], nid_xy(*s["p1"], z), nid_xy(*s["p2"], z), s["plano"])

    # --- VOLADIZO X+ (solo en ciertos pisos):
    #     desde X_MAX, 2 pares de PILARES en ambos pasillos + vigas. ---
    lineas_xpos = (Y_P1, Y_COMP, Y_P2)
    #   Pilares (nodos + columnas) en cada piso indicado
    for piso in VOLADIZO_XP_PISOS:
        z = Z_VIGAS[piso - 1]                       # nivel de viga superior del piso
        z_base = Z_NIVELES[piso - 1]                # nivel de piso (base de columnas)
        # Pilares A (X_PILAR_A) en X_MAX + 255 cm, en las 3 lineas
        for y in lineas_xpos:
            add_nodo(X_PILAR_A, y, z_base)          # base del pilar (nivel de piso)
            add_nodo(X_PILAR_A, y, z)               # cabeza del pilar (nivel de viga)
        # Pilares B (X_PILAR_B) en A + 245 cm, en las 3 lineas
        for y in lineas_xpos:
            add_nodo(X_PILAR_B, y, z_base)
            add_nodo(X_PILAR_B, y, z)
        # Columnas de 1 piso (z_base -> z) en los 6 nuevos pilares (3 lineas x 2 X)
        if ELIMINAR_VOLADIZOS_PISO3 and piso == 3:
            continue     # piso 3: se eliminan las columnas de Z=8 a Z=12
        for xp in (X_PILAR_A, X_PILAR_B):
            for y in lineas_xpos:
                add("columna", nid_xy(xp, y, z_base), nid_xy(xp, y, z), "vertical")
    #   Vigas en los niveles unicos (evita duplicar el nivel compartido Z=12)
    niveles_xpos = set()
    for piso in VOLADIZO_XP_PISOS:
        niveles_xpos.add(Z_VIGAS[piso - 1])
        niveles_xpos.add(Z_NIVELES[piso - 1])
    if ELIMINAR_VOLADIZOS_PISO3:
        # quitar el nivel inferior (Z=8) que pertenece solo al piso 3
        niveles_xpos.discard(Z_NIVELES[min(VOLADIZO_XP_PISOS) - 1])
    for zp in sorted(niveles_xpos):
        #   Longitudinales por linea (pasillos + eje central)
        for y in lineas_xpos:
            xids = [X_EDGE_XP, X_PILAR_A, X_PILAR_B]
            for xa, xb in zip(xids[:-1], xids[1:]):
                add("viga_longitudinal", nid_xy(xa, y, zp), nid_xy(xb, y, zp),
                    "voladizo_xpos")
        #   Transversales uniendo los pasillos (via compartida) en cada X
        for xp in (X_PILAR_A, X_PILAR_B):
            add("viga_transversal", nid_xy(xp, Y_P1, zp),
                nid_xy(xp, Y_COMP, zp), "voladizo_xpos")
            add("viga_transversal", nid_xy(xp, Y_COMP, zp),
                nid_xy(xp, Y_P2, zp), "voladizo_xpos")

    # --- VOLADIZO Y- PISO 3 en el pilar X=0 del pasillo 2 (modulo 261x220) ---
    #     Cantilever (sin pilares de apoyo) + viga de union hacia adentro en X=2.20
    for piso in VOLADIZO_YP2_PISOS:
        z = Z_VIGAS[piso - 1]
        z_base = Z_NIVELES[piso - 1]
        # Puntos del marco (planta): (X, Y)
        c_root  = (VD_X0, VD_Y0)     # (0,  -7.25)  pilar existente (arranque)
        c_x2    = (VD_X2, VD_Y0)     # (2.20,-7.25) extremo sobre la linea pasillo 2
        c_yfar0 = (VD_X0, VD_YFAR)   # (0,  -9.86)  punta libre (lado X=0)
        c_yfar2 = (VD_X2, VD_YFAR)   # (2.20,-9.86) punta libre (lado X=2.20)
        c_int   = (VD_X2, Y_COMP)    # (2.20, 0.00) sobre la linea central (union)

        # Nodos de viga (superior e inferior) en los puntos del voladizo
        for (x, y) in (c_x2, c_yfar0, c_yfar2, c_int):
            add_nodo(x, y, z_base)
            add_nodo(x, y, z)

        # Marco en voladizo (aristas cerradas), a nivel superior e inferior
        for zp in (z, z_base):
            add("viga_longitudinal", nid_xy(c_root[0], c_root[1], zp),
                nid_xy(c_x2[0], c_x2[1], zp), "voladizo_yp2")      # borde pasillo
            if not (VOLADIZO_YP2_ELIMINAR_INFERIOR and zp == z_base):
                add("viga_longitudinal", nid_xy(c_yfar0[0], c_yfar0[1], zp),
                    nid_xy(c_yfar2[0], c_yfar2[1], zp), "voladizo_yp2")  # borde exterior
                add("viga_transversal", nid_xy(c_x2[0], c_x2[1], zp),
                    nid_xy(c_yfar2[0], c_yfar2[1], zp), "voladizo_yp2")  # lado X=2.20
            add("viga_transversal", nid_xy(c_root[0], c_root[1], zp),
                nid_xy(c_yfar0[0], c_yfar0[1], zp), "voladizo_yp2")  # lado X=0
        # Viga de union hacia adentro SOLO a nivel de techo (z): X=2.20 pasillo 2 -> central
        add("viga_transversal", nid_xy(c_x2[0], c_x2[1], z),
            nid_xy(c_int[0], c_int[1], z), "voladizo_yp2")

    # --- VOLADIZO Y- entre X=10 y X=20 (salida 412 cm, marco con 2 columnas) ---
    #     El marco sale del pasillo 2 (Y=-7.25) hacia Y negativo (hasta Y=-11.37),
    #     con 2 columnas en las esquinas exteriores (X=10 y X=20) y cerrado con
    #     vigas (longitudinal exterior + 2 transversales) en los niveles de viga
    #     del piso (o pisos) indicado en VOLADIZO_YP2_FRAME_PISOS.
    # Columnas de 1 piso (z_base -> z) en las 2 esquinas exteriores (X=10, X=20)
    for piso in VOLADIZO_YP2_FRAME_PISOS:
        z = Z_VIGAS[piso - 1]
        z_base = Z_NIVELES[piso - 1]
        for x in (VD_YP2_FRAME_X1, VD_YP2_FRAME_X2):   # nodos del borde exterior
            add_nodo(x, Y_EXT, z_base)
            add_nodo(x, Y_EXT, z)
        if ELIMINAR_VOLADIZOS_PISO3 and piso == 3:
            continue     # piso 3: se elimina la columna de Z=8 a Z=12
        for x in (VD_YP2_FRAME_X1, VD_YP2_FRAME_X2):   # columnas en las esquinas exteriores
            add("columna", nid_xy(x, Y_EXT, z_base),
                nid_xy(x, Y_EXT, z), "vertical")
    #   Vigas en los niveles unicos (evita duplicar el nivel compartido Z=12)
    niveles_frame = set()
    for piso in VOLADIZO_YP2_FRAME_PISOS:
        niveles_frame.add(Z_VIGAS[piso - 1])
        niveles_frame.add(Z_NIVELES[piso - 1])
    if ELIMINAR_VOLADIZOS_PISO3:
        # quitar el nivel inferior (Z=8) que pertenece solo al piso 3
        niveles_frame.discard(Z_NIVELES[min(VOLADIZO_YP2_FRAME_PISOS) - 1])
    for zp in sorted(niveles_frame):
        add("viga_longitudinal", nid_xy(VD_YP2_FRAME_X1, Y_EXT, zp),
            nid_xy(VD_YP2_FRAME_X2, Y_EXT, zp), "voladizo_yp2_frame")
        add("viga_transversal", nid_xy(VD_YP2_FRAME_X1, Y_P2, zp),
            nid_xy(VD_YP2_FRAME_X1, Y_EXT, zp), "voladizo_yp2_frame")
        add("viga_transversal", nid_xy(VD_YP2_FRAME_X2, Y_P2, zp),
            nid_xy(VD_YP2_FRAME_X2, Y_EXT, zp), "voladizo_yp2_frame")
    # --- VOLADIZO PISO 2 (Z=8): 3 vigas hacia Y negativo en pasillo 2 + viga ext ---
    #     Desde la linea del pasillo 2 (Y=-7.25) salen 3 vigas transversales de
    #     VD_YP2_P2_PROF_CM (246 cm) en X=10, 15, 20, hasta Y_P2-2.46=-9.71, unidas
    #     por fuera por una viga longitudinal (X=10->20) de seccion DISTINTA
    #     (30x45 cm): tipo "viga_long_voladizo_p2".
    if VOLADIZO_YP2_P2:
        for piso in VOLADIZO_YP2_P2_PISOS:
            z = Z_VIGAS[piso - 1]                       # nivel de viga del piso
            y_ext = Y_P2 - VD_YP2_P2_PROF_CM / 100.0    # -9.71 m (extremo exterior)
            x_ext_min = min(VD_YP2_P2_XS)
            x_ext_max = max(VD_YP2_P2_XS)
            # Nodos extremos en cada X saliente
            for xx in VD_YP2_P2_XS:
                add_nodo(xx, y_ext, z)
            # 3 vigas transversales (seccion estandar): passillio 2 (Y_P2) -> y_ext
            for xx in VD_YP2_P2_XS:
                add("viga_transversal", nid_xy(xx, Y_P2, z),
                    nid_xy(xx, y_ext, z), "voladizo_yp2_p2")
            # Viga exterior longitudinal (seccion 30x45): tipo propio
            add("viga_long_voladizo_p2", nid_xy(x_ext_min, y_ext, z),
                nid_xy(x_ext_max, y_ext, z), "voladizo_yp2_p2")
    # --- SUBTERRANEO: replica de la parte de X negativo en Z negativo ---
    #     Baja hasta Z=-H_SUB las columnas de X=-10 (y X=0 si SUBTERRANEO_COLS_X0)
    #     en las 3 lineas Y, y replica a nivel de techo (Z=0) las vigas de la
    #     extension X negativa (longitudinales 0->X_NEG y transversales en X_NEG).
    if SUBTERRANEO:
        h_sub = SUBTERRANEO_ALTURA_CM / 100.0
        z_sub = -h_sub                        # suelo del subterraneo (Z negativo)
        xs_sub = [X_NEG]
        if SUBTERRANEO_COLS_X0:
            xs_sub.append(0.0)
        # Nodos de arranque (suelo del subterraneo) en las 3 lineas
        for x in xs_sub:
            for y in (Y_P1, Y_COMP, Y_P2):
                add_nodo(x, y, z_sub)
        # Columnas descendentes: de Z=-4 a Z=0 (los pisos de arriba siguen con
        # sus columnas Z=0->4 intactas; los nodos Z=0 ya existen)
        for x in xs_sub:
            for y in (Y_P1, Y_COMP, Y_P2):
                add("columna", nid_xy(x, y, z_sub), nid_xy(x, y, 0.0), "vertical")
        # Techo del subterraneo (Z=0): replica las vigas de la extension X negativa
        for y in (Y_P1, Y_COMP, Y_P2):
            add("viga_longitudinal", nid_xy(0.0, y, 0.0),
                nid_xy(X_NEG, y, 0.0), "extension_x")
        for y0, y1 in ((Y_P1, Y_COMP), (Y_COMP, Y_P2)):
            add("viga_transversal", nid_xy(X_NEG, y0, 0.0),
                nid_xy(X_NEG, y1, 0.0), "extension_x")
        if SUBTERRANEO_COLS_X0:
            # Cierre por la linea X=0 del subterraneo
            for y0, y1 in ((Y_P1, Y_COMP), (Y_COMP, Y_P2)):
                add("viga_transversal", nid_xy(0.0, y0, 0.0),
                    nid_xy(0.0, y1, 0.0), "extension_x")
    # --- MUROS ESTRUCTURALES (cascaron) ---
    #     Cada muro es un plano vertical dividido en bandas de piso; cada banda
    #     es un elemento cascaron (ShellMITC4) de 4 nodos esquina.
    muros = []
    if MUROS_ESTRUCTURALES:
        t_p = MURO_PPAL_T_CM / 100.0
        t_e = MURO_EXT_T_CM / 100.0
        # bandas en Z entre MURO_Z_INF y MURO_Z_SUP
        bandas = []
        z0 = MURO_Z_INF
        while z0 < MURO_Z_SUP - 1e-9:
            z1 = min(z0 + H_PISO, MURO_Z_SUP)
            bandas.append((z0, z1))
            z0 = z1
        # D2: muro principal (plano X-Z en Y=MURO_PPAL_Y_M)
        def _banda(pts, z_a, z_c):
            """Crea/recupera los 4 nodos esquina esquina de un rectangulo vertical
            definido por sus 2 puntos en planta (x,y) y las cotas z_a, z_c.
            Devuelve los ids [n00, n10, n11, n01] (orden de ShellMITC4)."""
            (x0, y0), (x1, y1) = pts
            return [
                add_nodo(x0, y0, z_a),  # 00
                add_nodo(x1, y1, z_a),  # 10
                add_nodo(x1, y1, z_c),  # 11
                add_nodo(x0, y0, z_c),  # 01
            ]
        # Configuraciones de muro: una por lado (NEG y/o POS segun _MURO_CONFIGS)
        #   Muro principal (X=-6.7 a -3.3, plano X-Z en cfg['ppal_y']), espesor 0.20
        #   Muros extremos (X=-3.3 y X=-6.7, plano Y-Z de ext_y[0] a ext_y[1]), espesor 0.25
        for cfg in _MURO_CONFIGS:
            ppal_y = cfg["ppal_y"]
            ext_y1, ext_y2 = cfg["ext_y"]
            for za, zc in bandas:
                n4 = _banda([(MURO_PPAL_X1_M, ppal_y),
                             (MURO_PPAL_X2_M, ppal_y)], za, zc)
                muros.append({"plano": "muro_ppal", "nodos": n4, "t": t_p})
            for x_ext in (MURO_PPAL_X2_M, MURO_PPAL_X1_M):
                for za, zc in bandas:
                    n4 = _banda([(x_ext, ext_y1), (x_ext, ext_y2)], za, zc)
                    muros.append({"plano": "muro_ext", "nodos": n4, "t": t_e})
    return nodos, elems, Z_NIVELES, Z_VIGAS, muros


def filtrar_nodos_vivos(nodos, elems, muros=None, losas=None):
    """
    Descarta los nodos que no participan en ningun elemento (nodos 'muertos').
    Reindexa los ids de elementos en consecuencia. Si se pasan `muros`
    (elementos cascaron de 4 nodos), sus nodos tambien se conservan, y si se
    pasan `losas` (diafragmas de 4 nodos) se reindexan sus esquinas.
    """
    muros = muros or []
    losas = losas or []
    nodos_muro = set(n for m in muros for n in m["nodos"])
    nodos_losa = set(n for l in losas for n in l["nodos"])
    vivos = {}
    mapa = {}
    for nid, x, y, z in nodos:
        if (any((e["nodo_i"] == nid) or (e["nodo_j"] == nid) for e in elems)
                or nid in nodos_muro or nid in nodos_losa):
            nuevo = len(vivos) + 1
            vivos[(x, y, z)] = nuevo
            mapa[nid] = nuevo
    # reasignar ids en nodos
    nuevos_nodos = [(mapa[nid], x, y, z)
                    for nid, x, y, z in nodos
                    if nid in mapa]
    nuevos_nodos.sort(key=lambda t: t[0])
    nuevos_elems = []
    for e in elems:
        e2 = dict(e)
        e2["nodo_i"] = mapa[e["nodo_i"]]
        e2["nodo_j"] = mapa[e["nodo_j"]]
        nuevos_elems.append(e2)
    nuevos_muros = []
    for m in muros:
        m2 = dict(m)
        m2["nodos"] = [mapa[n] for n in m["nodos"]]
        nuevos_muros.append(m2)
    nuevas_losas = []
    for l in losas:
        l2 = dict(l)
        l2["nodos"] = [mapa[n] for n in l["nodos"]]
        nuevas_losas.append(l2)
    return nuevos_nodos, nuevos_elems, nuevos_muros, nuevas_losas


# Lista de nodos como (id, x, y, z) ordenada, para visualizacion
def nodos_a_lista(nodos):
    return [(nid, x, y, z) for (x, y, z), nid in sorted(nodos.items(),
            key=lambda kv: kv[1])]


# ============================================================
# LOSAS DE PISO (diafragmas por bahia)
# ============================================================
def _huellas_muro():
    """Huellas en planta (x0, x1, y sup, y inf) de los muros estructurales
    configurados. Son rectangulos cerrados por encierro conservador."""
    huellas = []
    for cfg in _MURO_CONFIGS:
        ppal_y = cfg["ppal_y"]
        ext_y1, ext_y2 = cfg["ext_y"]
        # muro principal: plano X-Z en Y=ppal_y, ancho = espesor -> banda fina
        x0, x1 = MURO_PPAL_X1_M, MURO_PPAL_X2_M
        huellas.append((x0, x1, ppal_y, ppal_y))
        # muros extremos: plano Y-Z desde ext_y1 a ext_y2 (banda en X)
        huellas.append((x0, x1, min(ext_y1, ext_y2), max(ext_y1, ext_y2)))
    return huellas


def _rect_intersect(r1, r2):
    """True si las cajas 2D alineadas r1 y r2 se intersectan (expansión epsilon)."""
    e = 1e-9
    (a0x, a1x, a0y, a1y), (b0x, b1x, b0y, b1y) = r1, r2
    return not (a1x <= b0x + e or b1x <= a0x + e or a1y <= b0y + e or b1y <= a0y + e)


def construir_losas(lista_nodos, elems, muros=None):
    """Genera las losas de piso por bahia.
    Params: lista_nodos -> [(id, x, y, z)], elems -> vigas, muros -> muros.
    Devuelve (losas, nodos_aux): lista de losa y lista de nodos auxiliares
    [(id, x, y, z)] creados para los bordes de los huecos.
    Losa: {"plano":"losa","nivel":z,"nodos":[4 nodos],
           "x0","x1","y0","y1","detalle"}.
    Cada bahia es el rectangulo entre dos cortes consecutivos de la
    cuadricula de vigas longitudinales a ese nivel.

    En la zona X negativa (-10..0) se abren HUECOS (se recorta la losa):
      - Lado Y negativo (COMP->P2): hueco de Y=0 a Y=-4.945 (hasta el muro).
      - Lado Y positivo (P1->COMP): hueco de Y=2.75 a Y=5 (ancho 225 cm).
    Los huecos existen de Z=0 a Z=12 (subterraneo -> piso 3). En Z=16
    (piso 4) la zona X negativa vuelve a tener losa completa."""
    if not LOSAS:
        return [], []
    coord = {nid: (x, y, z) for nid, x, y, z in lista_nodos}
    huellas = _huellas_muro() if (MUROS_ESTRUCTURALES or muros) else []

    # nodos auxiliares para los bordes de hueco (por coordenada de X y Y)
    aux = {}
    _id_aux = [200000]
    def nodo_aux(x, y, z):
        key = (round(x, 4), round(y, 4), round(z, 4))
        if key not in aux:
            _id_aux[0] += 1
            nodo_id = _id_aux[0]
            aux[key] = nodo_id
            coord[nodo_id] = (x, y, z)
        return aux[key]

    # vigas longitudinales (definen la cuadricula de pórticos por eje Y)
    longs = [el for el in elems if el["tipo"] in ("viga_longitudinal",
                                                  "viga_long_voladizo_p2")]

    def xlines(y, z):
        xs = set()
        for el in longs:
            a, b = coord[el["nodo_i"]], coord[el["nodo_j"]]
            if abs(a[1] - b[1]) < 1e-6 and abs(a[1] - y) < 1e-6:
                if abs(a[2] - z) < 1e-6 or abs(b[2] - z) < 1e-6:
                    xs.add(round(a[0], 4)); xs.add(round(b[0], 4))
        return sorted(xs)

    vanos = (("P1-COMP", Y_P1, Y_COMP), ("COMP-P2", Y_COMP, Y_P2))
    niveles_losa = sorted(set([0.0] + [i * H_PISO for i in range(1, N_PISOS + 1)]))

    def emitir(y0, y1, xs, z, detalle):
        """Crea una losa por cada tramo entre cortes consecutivos de `xs`,
        para el vano transversal (y0,y1) a nivel z (si existen las 4 esquinas)."""
        out = []
        xs = sorted(set(round(x, 4) for x in xs))
        for i in range(len(xs) - 1):
            xa, xb = xs[i], xs[i + 1]
            esquinas = [(xa, y0, z), (xb, y0, z), (xb, y1, z), (xa, y1, z)]
            n_esq = []
            for (ex, ey, ez) in esquinas:
                id_ = next((n for n in coord
                            if abs(coord[n][0] - ex) < 1e-6
                            and abs(coord[n][1] - ey) < 1e-6
                            and abs(coord[n][2] - ez) < 1e-6), None)
                n_esq.append(id_)
            if any(v is None for v in n_esq):
                continue
            out.append({"plano": "losa", "nivel": z, "nodos": n_esq,
                        "x0": xa, "x1": xb, "y0": min(y0, y1),
                        "y1": max(y0, y1), "detalle": detalle,
                        "t": LOSA_ESPESOR_M})
        return out

    def emitir_bandas(y0, y1, xs, z, detalle):
        """Idem emitir pero localizando las esquinas por coordenadas (permite
        usar nodos ausentes si es preciso crearlos como auxiliares via coord)."""
        out = []
        xs = sorted(set(round(x, 4) for x in xs))
        for i in range(len(xs) - 1):
            xa, xb = xs[i], xs[i + 1]
            esquinas = [(xa, y0, z), (xb, y0, z), (xb, y1, z), (xa, y1, z)]
            n_esq = []
            for (ex, ey, ez) in esquinas:
                id_ = next((n for n in coord
                            if abs(coord[n][0] - ex) < 1e-6
                            and abs(coord[n][1] - ey) < 1e-6
                            and abs(coord[n][2] - ez) < 1e-6), None)
                if id_ is None:
                    id_ = nodo_aux(ex, ey, ez)
                n_esq.append(id_)
            if any(v is None for v in n_esq):
                continue
            out.append({"plano": "losa", "nivel": z, "nodos": n_esq,
                        "x0": xa, "x1": xb, "y0": min(y0, y1),
                        "y1": max(y0, y1), "detalle": detalle,
                        "t": LOSA_ESPESOR_M})
        return out

    def celdas_fuera_hueco(y0, y1, xs, z, hx0, hx1, hy0, hy1):
        """Emite las celdas de la losa de una bahia transversal (y0,y1) sobre
        la subdivision en X `xs`, subdividiendo en los bordes del rectangulo del
        hueco (hx0,hx1)x(hy0,hy1) y omitiendo las celdas que caen dentro.
        Usa nodos auxiliares para los bordes del hueco."""
        out = []
        # subdivide X incluyendo los bordes del hueco dentro del vano X
        xborde = list(xs)
        for hx in (hx0, hx1):
            if min(xborde) - 1e-6 < hx < max(xborde) + 1e-6 and \
               not any(abs(v - hx) < 1e-6 for v in xborde):
                xborde.append(hx)
        # subdivide Y incluyendo los bordes del hueco dentro del vano Y
        yborde = [y0, y1]
        for hy in (hy0, hy1):
            if min(yborde) - 1e-6 < hy < max(yborde) + 1e-6 and \
               not any(abs(v - hy) < 1e-6 for v in yborde):
                yborde.append(hy)
        xborde = sorted(set(round(v, 4) for v in xborde))
        yborde = sorted(set(round(v, 4) for v in yborde))
        for i in range(len(xborde) - 1):
            xa, xb = xborde[i], xborde[i + 1]
            if xb <= hx0 + 1e-6 or xa >= hx1 - 1e-6:
                # tramo entero fuera del hueco en X
                out.extend(emitir_bandas(y0, y1, [xa, xb], z, "losas"))
            else:
                for j in range(len(yborde) - 1):
                    ya, yb = yborde[j], yborde[j + 1]
                    # celda fuera del hueco si no esta dentro del rect x hy
                    if xb <= hx0 + 1e-6 or xa >= hx1 - 1e-6 or \
                       ya >= hy1 - 1e-6 or yb <= hy0 + 1e-6:
                        out.extend(emitir_bandas(ya, yb, [xa, xb], z, "losas"))
        return out

    losas = []
    # --- Plano principal (dos pasillos): 3 lineas Y, vanos X de -10 a 35 ---
    for z in niveles_losa:
        for _name, y0, y1 in vanos:
            g0, g1 = set(xlines(y0, z)), set(xlines(y1, z))
            grid = sorted(g0 & g1)
            grid = [x for x in grid if x <= 35.001]
            for i in range(len(grid) - 1):
                xa, xb = grid[i], grid[i + 1]
                caja = (xa, xb, min(y0, y1), max(y0, y1))
                es_zona_muro = any(_rect_intersect(caja, h) for h in huellas)
                # Bahias en la zona X negativa (-10..0): la losa lleva un HUECO
                # en la huella (envelope) del muro estructural de ese lado, desde
                # el subterraneo (Z=0) hasta el piso 3 (Z=12). En Z=16 (piso 4)
                # la bahía X negativa va completa. El hueco es un rectangulo
                # interior: en su porte la losa se subdivide y se omiten las
                # celdas que caen dentro del rectangulo.
                if abs(xa - X_NEG) < 1e-6 and abs(xb) < 1e-6:
                    if abs(z - 16.0) < 1e-9:
                        losas.extend(emitir(y0, y1, [xa, xb], z, "losas"))
                    elif abs(y0 - Y_P1) < 1e-6:   # lado positivo (P1-COMP)
                        # rectangulo del hueco positivo (envelope muro POS)
                        hx0, hx1 = MURO_PPAL_X1_M, MURO_PPAL_X2_M   # -6.7..-3.3
                        hy0, hy1 = 3.425, 5.0
                        losas.extend(celdas_fuera_hueco(
                            y0, y1, [xa, 0.0], z, hx0, hx1, hy0, hy1))
                    else:                          # lado negativo (COMP-P2)
                        # rectangulo del hueco negativo (envelope muro NEG),
                        # que llega hasta Y=0
                        hx0, hx1 = MURO_PPAL_X1_M, MURO_PPAL_X2_M   # -6.7..-3.3
                        hy0, hy1 = -4.945, 0.0
                        losas.extend(celdas_fuera_hueco(
                            y0, y1, [xa, 0.0], z, hx0, hx1, hy0, hy1))
                elif es_zona_muro:
                    losas.extend(emitir(y0, y1, [xa, xb], z, "zona_muro"))
                else:
                    losas.extend(emitir(y0, y1, [xa, xb], z, "losas"))

    # --- Voladizos: losas sobre las superficies planas de cada voladizo ---
    # Cada definicion lista: y sup, y inf, cortes de X (subdivision), niveles y
    # el X minimo del vano. Son rectangulos horizontales cerrados por vigas.
    voladizos = [
        # Voladizo X+ (piso X 35->40 en las 3 lineas Y), subdividido en X=37.55
        dict(y0=Y_P1, y1=Y_P2, xs=[35.0, 37.55, 40.0], zs=[12.0, 16.0]),
        # Voladizo Y- original (X 0->7.51, sale a Y=-11.37)
        dict(y0=Y_P2, y1=Y_EXT, xs=[0.0, 7.51], zs=[4.0, 8.0]),
        # Marco Y- X=10->20 (sale a Y=-11.37)
        dict(y0=Y_P2, y1=Y_EXT, xs=[10.0, 20.0], zs=[12.0, 16.0]),
        # Voladizo Y- pasillo 2 (X=0->2.2, salta a Y=-9.86) - marco del piso 3
        dict(y0=Y_P2, y1=-9.86, xs=[0.0, 2.2], zs=[12.0]),
        # Voladizo Y- pasillo 2, tramo X=10->20 a Y=-9.71, subdividido en X=15
        dict(y0=Y_P2, y1=-9.71, xs=[10.0, 15.0, 20.0], zs=[8.0]),
    ]
    for v in voladizos:
        for z in v["zs"]:
            losas.extend(emitir(v["y0"], v["y1"], v["xs"], z, "losas"))

    nodos_aux = [(nid, coord[nid][0], coord[nid][1], coord[nid][2])
                 for nid in sorted({v for v in aux.values()})]
    return losas, nodos_aux


# ============================================================
# 2. INTEGRACION CON OPENSEES (solo geometria, no carga)
# ============================================================
def propiedades_seccion(b, h, E, G):
    """Area, J, Iy, Iz de una seccion rectangular b(x) x h, con inercias
    relativas al eje local: Iy alrededor Y (strong en h), Iz alrededor Z."""
    A = b * h
    J = b**3 * h / 3.0 + b * h**3 / 3.0      # torsion rectangular de St-Venant
    Iy = h * b**3 / 12.0                     # flexion en el plano YZ (eje Y)
    Iz = b * h**3 / 12.0                     # flexion en el plano YZ? (eje Z)
    return A, J, Iy, Iz


def construir_opensees(lista_nodos, elems, muros=None, losas=None):
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    # Nota: E/G en MPa se usan con unidades m -> kN/m2 = 1000 * MPa
    E = EC * 1000.0
    Gc = G_COL * 1000.0
    Gv = G_VIG * 1000.0

    A_col, J_col, Iy_col, Iz_col = propiedades_seccion(b_col, h_col, E, Gc)
    A_vig, J_vig, Iy_vig, Iz_vig = propiedades_seccion(b_vig, h_vig, E, Gv)
    A_vig2, J_vig2, Iy_vig2, Iz_vig2 = propiedades_seccion(b_vig_vp2, h_vig_vp2, E, Gv)

    ops.geomTransf("Linear", 1, 1, 0, 0)   # columnas
    ops.geomTransf("Linear", 2, 0, 0, 1)   # vigas

    for nid, x, y, z in lista_nodos:
        ops.node(nid, x, y, z)
    for e in elems:
        if e["tipo"] == "columna":
            transf, A, J, Iy, Iz = 1, A_col, J_col, Iy_col, Iz_col
        elif e["tipo"] == "viga_long_voladizo_p2":
            transf, A, J, Iy, Iz = 2, A_vig2, J_vig2, Iy_vig2, Iz_vig2
        else:
            transf, A, J, Iy, Iz = 2, A_vig, J_vig, Iy_vig, Iz_vig
        Gi = Gc if e["tipo"] == "columna" else Gv
        ops.element("elasticBeamColumn", e["id"], e["nodo_i"], e["nodo_j"],
                    A, E, Gi, J, Iy, Iz, transf)

    # Muros estructurales: este OpenSeesPy no soporta cascarones, por lo que se
    # modelan como VIGAS EQUIVALENTES (frame) a lo largo del plano del muro.
    # Cada muro (una banda = un rectangulo vertical 00/10/11/01) se representa
    # con: una viga horizontal en el tope (01-11), y sus dos bordes verticales
    # (00-01 y 10-11) como columnas de borde. La viga y las columnas usan la
    # seccion real del muro: espesor x longitud en planta.
    muros = muros or []
    if muros:
        coord2 = {nid: (x, y, z) for nid, x, y, z in lista_nodos}
        eqids = 500000
        eqn = 0
        for m in muros:
            t = m.get("t", 0.20)
            nids = m["nodos"]                      # [00,10,11,01]
            p0, p10, p11, p01 = (coord2[x] for x in nids)
            # longitud del muro en planta (distancia 00-10, ya sea en X o en Y)
            L = max(abs(p10[0] - p0[0]), abs(p10[1] - p0[1]))
            # seccion equivalente del muro: espesor x longitud en planta
            b_eq = min(t, L)
            h_eq = max(t, L)
            A, J, Iy, Iz = propiedades_seccion(b_eq, h_eq, E, Gv)
            eqn += 1
            # viga horizontal al tope (01-11)
            ops.element("elasticBeamColumn", eqids + eqn,
                        nids[3], nids[2], A, E, Gv, J, Iy, Iz, 2)
            eqn += 1
            # columnas de borde verticales (00-01 y 10-11)
            ops.element("elasticBeamColumn", eqids + eqn,
                        nids[0], nids[3], A, E, Gc, J, Iy, Iz, 1)
            eqn += 1
            ops.element("elasticBeamColumn", eqids + eqn,
                        nids[1], nids[2], A, E, Gc, J, Iy, Iz, 1)

    # ------------------------------------------------------------------
    # APOYOS EMPOTRADOS en las columnas mas bajas sin apoyo.
    #   - Subterraneo: base en Z=-4 (nodos de las columnas del sotano
    #     en X=-10 y X=0, en las 3 lineas Y principales).
    #   - Planta baja: base en Z=0 de las columnas del 1er piso que NO
    #     arrancan del sotano (X=10, 20, 30, 35, en las 3 lineas Y).
    # Se fijan los 6 grados de libertad (empotramiento completo).
    ys_apoyo = (Y_P1, Y_COMP, Y_P2)
    xs_sub = (X_NEG, X_LINEAS[0])            # X=-10 y X=0 (sotano)
    xs_pb = (X_LINEAS[2], X_LINEAS[4], X_LINEAS[6], X_LINEAS[7])  # 10,20,30,35
    z_sub = -SUBTERRANEO_ALTURA_CM / 100.0   # suelo del subterraneo (Z=-4)
    n_apoyos = 0
    for nid, x, y, z in lista_nodos:
        if (abs(z - z_sub) < 1e-9 and any(abs(y - yy) < 1e-9 for yy in ys_apoyo)
                and any(abs(x - xx) < 1e-9 for xx in xs_sub)):
            ops.fix(nid, 1, 1, 1, 1, 1, 1)
            n_apoyos += 1
        elif (abs(z) < 1e-9 and any(abs(y - yy) < 1e-9 for yy in ys_apoyo)
                and any(abs(x - xx) < 1e-9 for xx in xs_pb)):
            ops.fix(nid, 1, 1, 1, 1, 1, 1)
            n_apoyos += 1
    if n_apoyos:
        print(f"  Apoyos empotrados aplicados a {n_apoyos} nodos base.")

    # ------------------------------------------------------------------
    # LOSAS DE PISO como DIARRAGMAS RIGIDOS por nivel.
    #   Cada nivel con losa se restringe con un diafragma rigido en el plano
    #   X-Y (constriñe ux, uy y rz de los nodos del nivel al nodo maestro).
    #   El nodo maestro es uno de los nodos del propio nivel.
    losas = losas or []
    if losas:
        coord3 = {nid: (x, y, z) for nid, x, y, z in lista_nodos}
        nivel_a_nodos = {}
        for l in losas:
            nivel_a_nodos.setdefault(l["nivel"], []).extend(l["nodos"])
        for z in sorted(nivel_a_nodos):
            nodos_nivel = sorted(set(nivel_a_nodos[z]))
            # nodo maestro: el de menor Y (linea P2) y menor X del nivel
            maestro = min(nodos_nivel,
                          key=lambda n: (coord3[n][1], coord3[n][0]))
            esclavos = [n for n in nodos_nivel if n != maestro]
            for n in esclavos:
                ops.rigidDiaphragm(3, maestro, n)
        print(f"  Diafragmas rigidos en {len(nivel_a_nodos)} niveles de losa.")


def aplicar_cargas(lista_nodos, losas):
    """Aplica cargas de losas como cargas nodales equivalentes.

    Cada panel distribuye su carga vertical uniformemente entre sus cuatro
    nodos esquina. Se crean patrones independientes para D, L y 1.2D+1.6L.
    Devuelve un resumen serializable para exportarlo a cargas.json.
    """
    if not losas:
        return {"patrones": {}, "paneles": 0, "mensaje": "Sin losas"}

    coord = {nid: (x, y, z) for nid, x, y, z in lista_nodos}
    q_losa = PESO_UNITARIO_LOSA * LOSA_ESPESOR_M
    q_dead = q_losa + CARGA_MUERTA_ADICIONAL
    q_live = CARGA_VIVA
    q_combo = FACTOR_COMB_D * q_dead + FACTOR_COMB_L * q_live
    acumuladas = {"D": {}, "L": {}, "COMB": {}}
    area_total = 0.0

    for losa in losas:
        nids = losa["nodos"]
        pts = [coord[n] for n in nids]
        area = abs(sum(pts[i][0] * pts[(i + 1) % 4][1]
                       - pts[(i + 1) % 4][0] * pts[i][1]
                       for i in range(4))) / 2.0
        area_total += area
        for nombre, q in (("D", q_dead), ("L", q_live), ("COMB", q_combo)):
            carga_nodal = q * area / 4.0
            for nid in nids:
                acumuladas[nombre][nid] = acumuladas[nombre].get(nid, 0.0) + carga_nodal

    patrones = (("D", 1, q_dead), ("L", 2, q_live), ("COMB", 3, q_combo))
    for nombre, pattern_tag, _q in patrones:
        ops.timeSeries("Linear", pattern_tag)
        ops.pattern("Plain", pattern_tag, pattern_tag)
        for nid, fuerza in acumuladas[nombre].items():
            ops.load(nid, 0.0, 0.0, -fuerza, 0.0, 0.0, 0.0)

    return {
        "unidades": {"carga_superficial": "kN/m2", "fuerza_nodal": "kN"},
        "supuestos": {
            "peso_unitario_losa_kN_m3": PESO_UNITARIO_LOSA,
            "espesor_losa_m": LOSA_ESPESOR_M,
            "carga_muerta_adicional_kN_m2": CARGA_MUERTA_ADICIONAL,
            "carga_viva_kN_m2": CARGA_VIVA,
        },
        "paneles": len(losas),
        "area_total_losas_m2": area_total,
        "patrones": {
            "D": {"tag": 1, "descripcion": "Carga muerta", "q_kN_m2": q_dead,
                  "factor": 1.0, "fuerzas_nodales_kN": acumuladas["D"]},
            "L": {"tag": 2, "descripcion": "Carga viva", "q_kN_m2": q_live,
                  "factor": 1.0, "fuerzas_nodales_kN": acumuladas["L"]},
            "COMB": {"tag": 3, "descripcion": "1.2D + 1.6L", "q_equivalente_kN_m2": q_combo,
                     "factores": {"D": FACTOR_COMB_D, "L": FACTOR_COMB_L},
                     "fuerzas_nodales_kN": acumuladas["COMB"]},
        },
    }


# ============================================================
# 3. VERIFICACION GEOMETRICA
# ============================================================
def verificar_geometria():
    print("=" * 70)
    print("VERIFICACION GEOMETRICA")
    print("=" * 70)
    checks = [
        ("890 cm = ancho 1er pasillo (8.90 m)", ANCHO_P1, 8.90),
        ("725 cm = separacion transversal (7.25 m)", SEP_T, 7.25),
        ("500 cm = separacion longitudinal (5.00 m)", SEP_L, 5.00),
        ("7 espacios longitudinales (8 lineas)", N_LINEAS - 1, ESPACIOS_LONG),
        ("Columna eliminada 2da (X=5.00 m)", X_ELIMINADA, 5.00),
        ("Columna extra a 251 cm de X=5 (X=7.51 m)", X_EXTRA, 7.51),
        ("Viga voladizo 412 cm (4.12 m)", D_EXT, 4.12),
        ("Extension en Y=-11.37 m", Y_EXT, -11.37),
        ("Extension X negativo 1000 cm (10 m)", EXT_X, 10.00),
        ("Extremo X de extension (X=-10 m)", X_NEG, -10.00),
        ("Altura por piso (4.00 m)", H_PISO, 4.00),
        ("Numero de pisos", N_PISOS, N_PISOS),
    ]
    ok = True
    for nombre, valor, esperado in checks:
        p = abs(valor - esperado) < 1e-9
        ok = ok or (nombre == "Numero de pisos" and valor == esperado)
        ok = ok if nombre != "Numero de pisos" else (p)
        print(f"  {'[OK]' if p else '[ERROR]'} {nombre}: {valor:.2f} m")

    # Duplicados de columnas
    puntos_col, _, _ = construir_geometria_plana()
    if len(puntos_col) == len(list(puntos_col)):
        print("  [OK] Sin columnas duplicadas")
    else:
        print("  [ERROR] Puntos de columna duplicados")
        ok = False
    return ok


# ============================================================
# 4. VISUALIZACION
# ============================================================
def graficar_3d(lista_nodos, elems, muros=None, losas=None):
    fig = plt.figure(figsize=(15, 10))
    ax = fig.add_subplot(111, projection='3d')
    coord = {nid: (x, y, z) for nid, x, y, z in lista_nodos}

    estilo = {'columna': ('green', 2.6), 'viga_longitudinal': ('blue', 1.8),
              'viga_transversal': ('orange', 1.8),
              'viga_long_voladizo_p2': ('cyan', 2.0)}
    for e in elems:
        p1, p2 = coord[e["nodo_i"]], coord[e["nodo_j"]]
        color, lw = estilo.get(e["tipo"], ('purple', 1.8))
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                color=color, linewidth=lw)

    # Resaltar vigas del voladizo y extension X
    for e in elems:
        if e["plano"] in ("voladizo", "extension", "extension_x", "voladizo_xpos", "voladizo_yp2", "voladizo_yp2_p2"):
            p1, p2 = coord[e["nodo_i"]], coord[e["nodo_j"]]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                    color='purple', linewidth=2.2, zorder=4)

    # Muros estructurales (superficies cascaron)
    if muros:
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        verts = [[coord[n] for n in m["nodos"]] for m in muros]
        col = muros[0]["plano"]
        colores = {"muro_ppal": (0.65, 0.75, 0.9, 0.55), "muro_ext": (0.9, 0.65, 0.75, 0.55)}
        poly = Poly3DCollection(verts, facecolors=[colores.get(m["plano"], (0.7, 0.7, 0.7, 0.5)) for m in muros],
                                edgecolors='darkslateblue', linewidths=0.6)
        ax.add_collection3d(poly)

    # Losas de piso (superficies horizontales del diafragma de cada bahia)
    if losas:
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        lverts = [[coord[n] for n in l["nodos"]] for l in losas]
        lfcs = []
        for l in losas:
            if l.get("detalle") == "zona_muro":
                lfcs.append((0.95, 0.85, 0.6, 0.35))   # zona de muro (pendiente)
            else:
                lfcs.append((0.55, 0.8, 0.7, 0.35))    # losa comun
        poly = Poly3DCollection(lverts, facecolors=lfcs,
                                edgecolors='teal', linewidths=0.4, alpha=0.35)
        ax.add_collection3d(poly)

    # Nodos
    for nid, x, y, z in lista_nodos:
        if z > 0:
            ax.scatter(x, y, z, c='0.4', s=10, zorder=4)

    ax.set_xlabel('X (m) - longitudinal')
    ax.set_ylabel('Y (m) - transversal')
    ax.set_zlabel('Z (m) - vertical')
    ax.set_title(f'Modelo 3D: {N_PISOS} pasillos de {N_PISOS} piso(s)', fontsize=13)

    xs = [c[0] for c in coord.values()]
    ys = [c[1] for c in coord.values()]
    zs = [c[2] for c in coord.values()]
    m = 1.5
    ax.set_xlim(min(xs) - m, max(xs) + m)
    ax.set_ylim(min(ys) - m, max(ys) + m)
    ax.set_zlim(-0.5, max(zs) + 1)
    dx = (max(xs) - min(xs)) + 2 * m
    dy = (max(ys) - min(ys)) + 2 * m
    dz = (max(zs) - min(zs)) + 2
    ax.set_box_aspect((dx, dy, dz))
    ax.view_init(elev=22, azim=-55)

    plt.tight_layout()
    p = os.path.join(OUT_DIR, "modelo_3d.png")
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Guardado: modelo_3d.png")
    return p


def graficar_vista_superior(lista_nodos, _elems):
    fig, ax = plt.subplots(figsize=(14, 8))
    coord = {nid: (x, y, z) for nid, x, y, z in lista_nodos}
    zmax = max(c[2] for c in coord.values())
    for e in _elems:
        if e["tipo"] == "columna":
            continue
        p1, p2 = coord[e["nodo_i"]], coord[e["nodo_j"]]
        if abs(p1[2] - zmax) < 1e-6 and abs(p2[2] - zmax) < 1e-6:
            es_ext = e["plano"] in ("voladizo", "extension", "extension_x", "voladizo_xpos", "voladizo_yp2", "voladizo_yp2_p2")
            color = 'purple' if es_ext else (
                'blue' if e["tipo"] == "viga_longitudinal" else 'orange')
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, linewidth=1.5)
    for nid, x, y, z in lista_nodos:
        if z > 0 and abs(z - zmax) < 1e-6:
            ax.scatter(x, y, c='k', s=14)

    # Cotas
    ax.annotate('', xy=(38, 0), xytext=(38, Y_P1),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax.text(38.4, Y_P1 / 2, '890 cm', color='green', fontsize=11)
    ax.annotate('', xy=(38, Y_P2), xytext=(38, 0),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax.text(38.4, Y_P2 / 2, '725 cm', color='green', fontsize=11)
    ax.annotate('', xy=(X_NEG, -3.6), xytext=(0, -3.6),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax.text(X_NEG / 2, -3.9, '1000 cm', color='green', fontsize=10, ha='center')

    ax.set_xlabel('X (m) - longitudinal')
    ax.set_ylabel('Y (m) - transversal')
    ax.set_title('Vista Superior (planta nivel superior)', fontsize=14)
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()
    p = os.path.join(OUT_DIR, "vista_superior.png")
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Guardado: vista_superior.png")
    return p


def graficar_vista_longitudinal(lista_nodos, elems):
    fig, ax = plt.subplots(figsize=(14, 6))
    coord = {nid: (x, y, z) for nid, x, y, z in lista_nodos}
    for e in elems:
        p1, p2 = coord[e["nodo_i"]], coord[e["nodo_j"]]
        if p1[1] == p2[1] == Y_P2:   # fila pasillo 2
            ax.plot([p1[0], p2[0]], [p1[2], p2[2]], color='0.4', linewidth=2)
    ax.annotate('', xy=(0, -1.2), xytext=(SEP_L, -1.2),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax.text(SEP_L / 2, -1.4, '500 cm', color='green', fontsize=11, ha='center')
    ax.set_xlabel('X (m) - longitudinal')
    ax.set_ylabel('Z (m) - vertical')
    ax.set_title('Vista Longitudinal (XZ) pasillo 2 - ' + str(N_PISOS) + ' pisos', fontsize=13)
    x_all = [c[0] for c in coord.values()]
    ax.set_xlim(min(x_all) - 2, max(x_all) + 2)
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()
    p = os.path.join(OUT_DIR, "vista_longitudinal.png")
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Guardado: vista_longitudinal.png")
    return p


# ============================================================
# 5. TABLAS (nodos y elementos)
# ============================================================
def exportar_tablas(lista_nodos, elems, muros=None, losas=None, cargas=None):
    coords = {nid: [x, y, z] for nid, x, y, z in lista_nodos}
    with open(os.path.join(OUT_DIR, "coordenadas_nodos.json"), "w",
              encoding="utf-8") as f:
        json.dump(coords, f, indent=2, ensure_ascii=False)
    elem_simple = []
    for e in elems:
        elem_simple.append({"tipo": e["tipo"], "plano": e["plano"],
                            "nodo_i": e["nodo_i"], "nodo_j": e["nodo_j"]})
    with open(os.path.join(OUT_DIR, "elementos.json"), "w",
              encoding="utf-8") as f:
        json.dump(elem_simple, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT_DIR, "muros.json"), "w",
              encoding="utf-8") as f:
        json.dump(muros or [], f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT_DIR, "losas.json"), "w",
              encoding="utf-8") as f:
        json.dump(losas or [], f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT_DIR, "cargas.json"), "w",
              encoding="utf-8") as f:
        json.dump(cargas or {}, f, indent=2, ensure_ascii=False)


def imprimir_resumen(lista_nodos, elems, Z_NIVELES, muros=None, losas=None):
    print("\n" + "=" * 70)
    print("RESUMEN DEL MODELO")
    print("=" * 70)
    n_col = sum(1 for e in elems if e["tipo"] == "columna")
    n_vl = sum(1 for e in elems if e["tipo"] == "viga_longitudinal")
    n_vt = sum(1 for e in elems if e["tipo"] == "viga_transversal")
    n_los = len(losas or [])
    n_los_muro = sum(1 for l in (losas or []) if l.get("detalle") == "zona_muro")
    print(f"  Pisos:                     {N_PISOS}")
    print(f"  Niveles de viga (Z):       {', '.join(f'{z:.0f}' for z in Z_NIVELES[1:])} m")
    print(f"  Nodos:                     {len(lista_nodos)}")
    print(f"  Columnas:                  {n_col}")
    print(f"  Vigas longitudinales:      {n_vl}")
    print(f"  Vigas transversales:       {n_vt}")
    print(f"  Total elementos:           {len(elems)}")
    if losas:
        print(f"  Paneles de losa:           {n_los}  "
              f"({n_los_muro} en zona de muro, forma pendiente)")
    print(f"  Seccion columnas:          {b_col:.2f} x {h_col:.2f} m")
    print(f"  Seccion vigas:             {b_vig:.2f} x {h_vig:.2f} m")
    print(f"  E = {EC:.0f} MPa,  nu = {POISSON}")
    print(f"  Columna eliminada:         X = {X_ELIMINADA:.2f} m (2da pasillo 2)")
    print(f"  Columna extra:             X = {X_EXTRA:.2f} m (251 cm)")
    print(f"  Extension voladizo:        vigas de {D_EXT*100:.0f} cm (Y={Y_EXT:.2f} m)")
    print(f"  Extension X negativo:      {EXT_X*100:.0f} cm (3 columnas en X={X_NEG:.0f})")
    print(f"\n  Apoyos empotrados:         suelo sotano (Z=-4) y planta baja (Z=0)")
    print(f"  Cargas:                    D={PESO_UNITARIO_LOSA * LOSA_ESPESOR_M + CARGA_MUERTA_ADICIONAL:.2f}, "
          f"L={CARGA_VIVA:.2f} kN/m2; COMB={FACTOR_COMB_D:.1f}D+{FACTOR_COMB_L:.1f}L")
    print(f"\n  Tablas guardadas en {OUT_DIR}")


def imprimir_tablas(lista_nodos, elems):
    print("\n" + "=" * 70)
    print("COORDENADAS DE NODOS (id, x, y, z) - en metros")
    print("=" * 70)
    for nid, x, y, z in lista_nodos:
        print(f"  N{nid:<4d}: ({x:>7.2f}, {y:>7.2f}, {z:>5.2f})")
    print("\n" + "=" * 70)
    print("CONECTIVIDAD DE ELEMENTOS (id, tipo, nodo_i -> nodo_j)")
    print("=" * 70)
    for e in elems:
        print(f"  E{e['id']:<4d} {e['tipo']:<18s} {e['plano']:<12s} "
              f"{e['nodo_i']} -> {e['nodo_j']}")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 70)
    print("MODELO ESTRUCTURAL 3D: DOS PASILLOS (VIGAS + COLUMNAS)")
    print("=" * 70)
    print(f"  Pasillo 1 (ancho): {ANCHO_P1:.2f} m")
    print(f"  Pasillo 2 (ancho): {SEP_T:.2f} m")
    print(f"  Separacion long.:  {SEP_L:.2f} m")
    print(f"  Espacios long.:    {ESPACIOS_LONG}")
    print(f"  Altura por piso:   {H_PISO:.2f} m")
    print(f"  Pisos:             {N_PISOS}")
    print(f"  Mod.: eliminar X={X_ELIMINADA:.2f}, extra X={X_EXTRA:.2f}")
    print(f"  Ext. X negativo:   {EXT_X:.2f} m")

    if not verificar_geometria():
        print("\n[ERROR] La verificacion geometrica fallo.")
        return

    nodos, elems, Z_NIVELES, Z_VIGAS, muros = construir_modelo()
    lista_nodos = nodos_a_lista(nodos)

    # Losas de piso: se calculan sobre la geometria completa (ids originales)
    # y luego sus esquinas se reindexan junto con los elementos vivos.
    losas, nodos_aux = construir_losas(lista_nodos, elems, muros)
    # Fusiona los nodos auxiliares (bordes de hueco de losa) a la geometria.
    if nodos_aux:
        lista_nodos = lista_nodos + nodos_aux

    # Descarta nodos sin elementos (e.g. voladizo eliminado en el 3er piso)
    lista_nodos, elems, muros, losas = filtrar_nodos_vivos(
        lista_nodos, elems, muros, losas)

    construir_opensees(lista_nodos, elems, muros, losas)
    cargas = aplicar_cargas(lista_nodos, losas)
    print(f"\n  Modelo cargado en OpenSees con cargas D, L y COMB.")

    imprimir_resumen(lista_nodos, elems, Z_NIVELES, muros, losas)
    exportar_tablas(lista_nodos, elems, muros, losas, cargas)

    print("\nGenerando visualizaciones...")
    graficar_3d(lista_nodos, elems, muros, losas)
    graficar_vista_superior(lista_nodos, elems)
    graficar_vista_longitudinal(lista_nodos, elems)

    imprimir_tablas(lista_nodos, elems)

    print("\n" + "=" * 70)
    print("FIN")
    print("=" * 70)


if __name__ == "__main__":
    main()
