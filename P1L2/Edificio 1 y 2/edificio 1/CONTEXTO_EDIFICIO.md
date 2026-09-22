# Contexto del Edificio — Modelo Estructural 3D de Dos Pasillos

> **Propósito de este documento:** explicar *cómo* se genera el edificio y *cómo* está estructurado, con el nivel de detalle necesario para que otra IA (o ingeniero) pueda retomar el trabajo sin reconstruir todo el contexto desde cero. Es una descripción del modelo y sus reglas, no un tutorial de código.

---

## 1. Qué es

`modelo_pasillos.py` genera la **geometría estructural 3D** de un edificio formado por **dos pasillos paralelos** (vigas + columnas de hormigón), con añadidos: **subterráneo/sótano**, **extensión hacia X negativo**, **varios voladizos** y **muros estructurales**. Se exporta a **OpenSees/OpenSeesPy** (solo geometría, sin cargas), a **JSON** (coordenadas, elementos, muros, losas) y a **PNG + HTML interactivo** (Three.js) para visualización.

- Script principal: `modelo_pasillos/modelo_pasillos.py`
- Visualizador HTML: `modelo_pasillos/generar_html.py` (lee los JSON y produce `resultados/modelo_3d.html`)
- Salidas: carpeta `modelo_pasillos/resultados/` (`coordenadas_nodos.json`, `elementos.json`, `muros.json`, `losas.json`, PNGs, `modelo_3d.html`)
- Documentación de usuario: `modelo_pasillos/README.md` (parámetros, resumen, salidas)

---

## 2. Sistema de coordenadas

| Eje | Significado | Unidades |
|-----|-------------|----------|
| **X** | Longitudinal de los pasillos | metros en salida (cm en entrada) |
| **Y** | Transversal (ancho de los pasillos) | metros |
| **Z** | Vertical (altura / pisos) | metros |

- El código usa **cm** para los parámetros y convierte a **metros** al construir la geometría.
- **X positivo** hacia el eje central del edificio; la **extensión** va hacia **X negativo** (hasta X = −10 m).
- **Y=0** es el eje **compartido** entre los dos pasillos.

---

## 3. Parámetros globales (lo que hay que conocer)

| Parámetro | Valor | Nota |
|-----------|-------|------|
| `N_PISOS` | 4 | Pisos totales |
| `H_PISO` | 4.00 m | Altura de piso (`ALTURA_PISO_CM=400`) |
| `SEP_L` | 5.00 m | Separación longitudinal estándar entre vigas |
| `ESPACIOS_LONG` | 7 | Espacios longitudinales (→ 8 líneas de X) |
| `ANCHO_P1` | 8.90 m | Ancho del 1er pasillo (`Y_P1=+8.90`) |
| `SEP_T` | 7.25 m | Separación transversal del pasillo 2 (`Y_P2=−7.25`) |
| `D_EXT` | 4.12 m | Voladizo transversal original (`Y_EXT=−11.37`) |
| `EXT_X_CM` | 1000 | Extensión hacia X negativo (`X_NEG=−10.00`) |
| `SUBTERRANEO` | True | Sótano de Z=−4 a Z=0 |
| `MUROS_ESTRUCTURALES` | True | Muros de cortante verticales |
| `MURO_YPOS` | "AMBOS" | Genera muro negativo + positivo |
| `LOSA_ESPESOR_M` | 0.15 | Espesor de losa (referencia) |
| E | 23500 MPa | Módulo elástico hormigón |
| ν | 0.2 | Coeficiente de Poisson |
| Peso unitario de losa | 25.0 kN/m³ | Hormigón armado |
| Carga muerta adicional | 1.0 kN/m² | Terminaciones, tabiquería y cielo |
| Carga viva | 2.0 kN/m² | Parámetro configurable |
| Combinación última | 1.2D + 1.6L | Parámetros configurables |

### Ejes Y principales
- `Y_P1 = +8.90` — línea del **pasillo 1**
- `Y_COMP = 0.0` — línea **compartida / central**
- `Y_P2 = −7.25` — línea del **pasillo 2**
- `Y_EXT = −11.37` — línea del **voladizo transversal original**

### Ejes X
- `X_LINEAS = [0, 5, 10, 15, 20, 25, 30, 35]` — líneas base (7 espacios).
- `X_EXTRA = 7.51` — columna/viga extra del pasillo 2 (añadida entre X=5 y X=10).
- `X_NEG = −10` — extremo de la extensión negativa.
- Voladizo X+: `X_PILAR_A=37.55`, `X_PILAR_B=40.00` (esta última es la punta).

---

## 4. Niveles en Z (piso / techo)

- Sótano: **Z = −4 a 0**
- Piso 1: **Z = 0 a 4**
- Piso 2: **Z = 4 a 8**
- Piso 3: **Z = 8 a 12**
- Piso 4 (azotea): **Z = 12 a 16**

Niveles de viga/losa: **Z = 0, 4, 8, 12, 16**. Losas en los 5 niveles (Z=0 es el techo del sótano).

---

## 5. Elementos estructurales y secciones

| Elemento | Sección | Notas |
|----------|---------|-------|
| Columnas | 70 × 70 cm | De un nivel al siguiente |
| Vigas longitudinales | 60 × 80 cm | Paralelas a X |
| Vigas transversales | 60 × 80 cm | Paralelas a Y |
| Viga voladizo piso 2 | 30 × 45 cm | Tramo especial `voladizo_yp2_p2` (X=10→20, Y=−9.71) |

- En OpenSees: secciones rectangulares con área, torsión (J) e inercias (Iy, Iz) calculadas por `propiedades_seccion`.
- GeomTransf: transformación 1 para columnas, 2 para vigas (el tag depende del tipo).

### Comportamiento de OpenSees (resumen)
- Se crean nodos, `node` (coord en m), `fix` (apoyos), secciones, elementos frame y patrones de carga gravitacional.
- **No hay cascarones/placas**: los **muros** y las **losas** NO se crean como elementos shell. 
   - Los **muros** se exportan a `muros.json`/HTML y en OpenSees se modelan como **vigas equivalentes** (una viga al tope + dos columnas de borde por banda) con la sección real del muro.
   - Las **losas** se modelan como **diafragmas rígidos por nivel** (`ops.rigidDiaphragm`): un nodo maestro por nivel y los nodos de ese nivel como esclavos (ux, uy, rz).
   - Las cargas de las losas se distribuyen como cargas nodales equivalentes en sus cuatro nodos esquina. Se crean patrones independientes **D**, **L** y **COMB** (`1.2D + 1.6L`).

### Apoyos / empotramientos
- **18 apoyos** fijos en total (`ops.fix`, 6 DOF):
  - **6** en la base Z=−4 del sótano (columnas X=−10 y X=0, en las 3 líneas Y).
  - **12** en la base Z=0 de planta baja (columnas X=10, 20, 30, 35, en las 3 líneas Y) — estas NO arrancan del sótano.
  - Se aplican automáticamente por criterio de coordenada.

---

## 6. Geometría y reglas de construcción (estructura general)

### 6.1 Pasillo 1
- De **Y=0 a Y=+8.90**, vigas transversales cada 5 m y longitudinales conectando columnas en la línea Y=+8.90 y Y=0.

### 6.2 Pasillo 2 (espejo) y modificación del eje central
- Reutiliza la línea compartida **Y=0**, con columnas en **Y=−7.25**, misma modulación X.
- **Columna eliminada** en **X=5.00** del pasillo 2 (2ª columna del lado nuevo).
- **Columna extra** en **X=7.51** (a 251 cm de X=5), entre X=5 y X=10.
- Viga transversal extra en **X=5.00** que conecta la línea compartida (Y=0) con un nodo intermedio a nivel de viga sobre la longitudinal del pasillo 2.

### 6.3 Columnas por piso — reglas centrales

Por **cada piso** se definen qué X de cada línea Y tienen columna. Las columnas llevan las **vigas** en la misma cuadrícula X (aunque algunas X no tengan columna, la viga puede estar).

- **Piso 1 (Z=0→4):** 3 líneas Y en **X = −10, 0, 10, 20, 30, 35**. Se eliminan X=5,15,25 (Y=±), X=7.51 (Y=−7.25) y las columnas del voladizo Y=−11.37 (X=0 y 7.51).
- **Piso 2 (Z=4→8):**
  - Y=0 y Y=+8.90: X = −10, 0, 10, 20, 30, 35 (se eliminan 5,15,25).
  - Y=−7.25: X = −10, 0, **7.51**, 10, 20, 30, 35 (conserva la extra 7.51; se eliminan 15,25).
  - El voladizo Y=−11.37 del piso 2 **no se modifica**.
- **Piso 3 (Z=8→12):** 3 líneas Y en **X = −10, 0, 10, 20, 30, 35**. Se eliminan 5,15,25 (Y=±) y 15,25 (Y=−7.25); la X=7.51 y la X=5 de ese lado ya se eliminan por otras reglas del piso 3 (`PISO3_ELIMINAR_BARRAS_P2=True`).
- **Piso 4 (Z=12→16):** 3 líneas Y en **X = −10, 0, 10, 20, 30, 35**, más los **voladizos conservados**: X+ (X=37.55 y 40) y Y− (`voladizo_yp2_frame`, X=10 y 20, Y=−11.37). Se eliminan 5,15,25 (Y=±) y 7.51,15,25 (Y=−7.25).

### 6.4 Extensión hacia X negativo
- 10 m desde X=0 a X=−10 sobre las **3 líneas Y**.
- **3 columnas en X=−10** (una por línea Y), conectadas: longitudinales (0→−10) y transversales de cierre en X=−10 y X=0.

### 6.5 Subterráneo (Z=−4 a Z=0)
- Replica bajo el suelo la **parte de X negativo**:
  - Bajan hasta Z=−4 las columnas de las **3 líneas Y** en **X=−10** y (con `SUBTERRANEO_COLS_X0=True`) también las de **X=0**.
  - En el techo (Z=0) se replican las vigas de la extensión negativa (3 longitudinales + transversales de cierre). No hay vigas en Z=−4.

---

## 7. Voladizos

### 7.1 Voladizo X+ (pisos 3 y 4)
- En el extremo X+ (más allá del último pilar X=35):
  - Avanza **255 cm** y coloca **pilares de 4 m** (Z=8→12) en las 3 líneas en **X=37.55**.
  - Avanza **otros 245 cm** y coloca **otros pilares** en las 3 líneas en **X=40.00**.
  - Unido por vigas longitudinales (35→37.55→40) y transversales en X=37.55 y X=40, a nivel superior (Z=12) e inferior (Z=8).
  - Parámetros: `VOLADIZO_XP_PISOS=[3,4]`.

### 7.2 Voladizo Y− original (X=0→7.51 → Y=−11.37)
- Vigas en voladizo de **412 cm (4.12 m)** hacia Y− apoyadas en las columnas X=0 y X=7.51 del pasillo 2.
- Cada uno sostenido por una **columna nueva** en (0,−11.37) y (7.51,−11.37), conectadas por una viga longitudinal en la punta.
- En pisos 1 y 2 (Z=4 y 8). (Se excluye del piso 4.)

### 7.3 Marco Y− X=10→20 (`voladizo_yp2_frame`, pisos 3 y 4)
- Marco rectangular que sale **412 cm** hacia Y− (Y=−7.25 → −11.37) entre **X=10 y X=20**.
- **2 columnas** en las esquinas exteriores (10,−11.37) y (20,−11.37), de Z=8 a Z=16.
- Cerrrado con vigas en Z=8, 12 y 16 (el nivel compartido Z=12 no se duplica): una longitudinal en el borde exterior y dos transversales (X=10 y X=20).

### 7.4 Voladizo Y− del pasillo 2 (X=0→2.2 → Y=−9.86, piso 3)
- Marco en voladizo (sin pilares de apoyo) que sale **261 cm** hacia Y− (hasta Y=−9.86) con **ancho 220 cm** hacia X+ (X=0→2.20), en el 3er piso (Z=8→12).
- En X=2.20, solo a nivel de techo (Z=12), una viga hacia adentro une la línea del pasillo (Y=−7.25) con la línea central (Y=0).
- En el nivel inferior (Z=8) se eliminan el borde exterior longitudinal (Y=−9.86) y la transversal en X=2.20 (`VOLADIZO_YP2_ELIMINAR_INFERIOR=True`).

### 7.5 Voladizo Y− X=10→20 a Y=−9.71 (piso 2)
- Tramo con viga longitudinal de sección **30×45 cm** en Y=−9.71 (X=10→20), subdividida en X=15, a nivel Z=8 (`VOLADIZO_YP2_P2=True`, `_PISOS=[2]`).

### 7.6 Eliminación de voladizos en el piso 3 (`ELIMINAR_VOLADIZOS_PISO3=True`)
- Del piso 3 (Z=8→12) se retiran **solo las columnas** y las vigas del nivel inferior Z=8 de dos voladizos: el **X+** y el **marco Y−** (X=10→20). Así ambos viven **solo a partir del piso 4** (columnas Z=12→16, vigas en Z=12 y 16). No se toca el módulo X=0 (`voladizo_yp2`).

---

## 8. Muros estructurales

Muros de cortante **verticales de altura completa (Z=−4 a Z=16)** que conectan los dos pasillos a la altura de la línea central modificada.

- **`MURO_YPOS = "AMBOS"`** → genera **dos** muros (negativo + positivo).
- **Muro principal (`muro_ppal`)**: plano X-Z:
  - NEG: en **Y=−4.945**, de **X=−6.7 a −3.3**, espesor 0.20 m, 5 paneles de 4.0 m.
  - POS: espejo en **Y=+5.00**, mismas dimensiones en X, espesor 0.20 m.
- **Muros extremos (`muro_ext`)**: planos Y-Z en X=−3.3 y X=−6.7, espesor 0.25 m:
  - NEG: de Y=−4.945 a −3.37 (ancho transversal 1.575 m), 10 paneles.
  - POS: de Y=+5.00 a +3.425 (apuntando hacia Y=0 sin llegar), 10 paneles.
- Total con `"AMBOS"`: **30 paneles** (10 `muro_ppal` + 20 `muro_ext`).
- Los paneles se guardan en `muros.json` y se visualizan como superficies translúcidas en el HTML (casilla "Muros estructurales").
- **En OpenSees** no hay cascarones → se modelan como **vigas equivalentes** (banda superior + columnas de borde) con sección real; tags en base `500000+`.

### Huella en planta de los muros (importante para las losas)
`_huellas_muro()` devuelve rectángulos en planta:
- Muro principal NEG/POS: banda X=−6.7→−3.3 en Y=±(ppal).
- Muro extremo NEG: X=−6.7→−3.3 × Y=−4.945→−3.37.
- Muro extremo POS: X=−6.7→−3.3 × Y=+5.00→+3.425.

---

## 9. Losas de piso (`LOSAS=True`)

### 9.1 Cobertura general
- Se generan losas (diafragmas) en **cada nivel de viga (Z=0, 4, 8, 12, 16)** (Z=0 = techo del sótano).
- Rellenan cada **bahía de la cuadrícula de vigas** entre los **3 ejes Y** (P1, COMP, P2) y los vanos transversales.
- La cuadrícula se **subdivide en todas las líneas de viga** (aunque no haya columna: X=5,15,25, y la extra X=7.51 donde exista).
- Cada bahía = 4 nodos esquina + nivel + espesor (0.15 m).
- **Voladizos**: también reciben losa las superficies de los voladizos (X+, Y− original, marco Y− X=10→20, voladizo Y− pasillo 2, y el tramo Y=−9.71).

### 9.2 Huecos en la zona X negativa (huella de los muros)
Regla importante: en la bahía **X=−10→0**, la losa tiene un **hueco (abertura interior)** coincidente con el **rectángulo envolvente de cada muro estructural**, que va del **subterráneo (Z=0) al piso 3 (Z=12)**. En **Z=16 (piso 4)** la losa es completa. El resto de la bahía (a ambos lados en X y fuera del rectángulo en Y) conserva la losa.

- **Hueco NEG (vano COMP→P2):** rectángulo **X=−6.7→−3.3 × Y=−4.95→0** (la huella del muro NEG llega **hasta Y=0**). La losa queda en Y=−7.25→−4.95 de esa franja X y fuera de la franja X en ambos lados.
- **Hueco POS (vano P1→COMP):** rectángulo **X=−6.7→−3.3 × Y=3.425→5.0**. La losa queda en Y=0→3.425 y Y=5.0→8.9 de esa franja X y fuera de la franja X en ambos lados.

Detalle técnico de implementación:
- La función `celdas_fuera_hueco(...)` subdivide la bahía X negativa en los **bordes del hueco** (X=−6.7, −3.3 y las Y del rectángulo) y emite solo las celdas **fuera** del rectángulo.
- Se crean **nodos auxiliares** en los bordes del hueco cuando no existen (bordes que no coinciden con columnas/vigas). Estos se fusionan en la lista de nodos antes de descartar nodos sin elementos.
- `construir_losas` devuelve `(losas, nodos_aux)`; `main` los añade a `lista_nodos` antes de `filtrar_nodos_vivos`.
- Con `MURO_YPOS="AMBOS"` el total es **101 paneles** de losa.

### 9.3 En OpenSees
- Losas = **diafragmas rígidos por piso**: `ops.rigidDiaphragm` con un **nodo maestro** por nivel y los nodos de ese nivel como esclavos (ux, uy, rz). **5 niveles** de losa.

---

## 10. Flujo de ejecución del script

1. `build(...)` / `construir_modelo()` construye nodos, columnas y vigas (registro en `lista_nodos`, `elems`).
2. Se construyen los muros → `muros`.
3. `construir_losas(lista_nodos, elems, muros)` → `(losas, nodos_aux)`; se fusionan los `nodos_aux` en `lista_nodos`.
4. `filtrar_nodos_vivos(lista_nodos, elems, muros, losas)` descarta nodos sin elementos y **reindexa** nodos/elementos/muros/losas (con remapeo de ids de esquina de losas).
5. `construir_opensees(...)` crea el modelo OpenSees (nodos, apoyos, secciones, elementos frame, diafragmas rígidos).
6. `aplicar_cargas(...)` crea los patrones D, L y COMB y distribuye las cargas de las losas.
7. `imprimir_resumen`, `exportar_tablas` (JSON), `graficar_3d`, `graficar_vista_superior`, `graficar_vista_longitudinal`, `imprimir_tablas`.

Salida final: coordenadas, elementos, muros, losas y cargas en `resultados/`.

---

## 11. Conteos actuales (referencia, 4 pisos, `MURO_YPOS="AMBOS"`)

| Concepto | Cantidad |
|----------|----------|
| Nodos | 241 (incluye auxiliares de bordes de hueco) |
| Columnas | 89 |
| Vigas longitudinales | 126 |
| Vigas transversales | 101 |
| Total barras (vigas+col) | 317 |
| Paneles de muro | 30 (10 `muro_ppal` + 20 `muro_ext`) |
| Paneles de losa | 101 |
| Carga muerta superficial D | 4.75 kN/m² (3.75 de peso propio + 1.00 adicional) |
| Carga viva superficial L | 2.00 kN/m² |
| Combinación de carga | 1.2D + 1.6L = 8.90 kN/m² equivalente |
| Diafragmas rígidos | 5 niveles |
| Apoyos empotrados | 18 |

---

## 12. Cómo visualizar (paso a paso)

```bash
# 1) Generar geometría, JSON y PNGs + modelo OpenSees
python modelo_pasillos.py

# 2) Generar el visor HTML interactivo (Three.js)
python generar_html.py

# 3) Abrir en el navegador
start resultados/modelo_3d.html
```

Salidas generadas en `modelo_pasillos/resultados/`:
- `coordenadas_nodos.json`, `elementos.json`, `muros.json`, `losas.json`, `cargas.json`
- `modelo_3d.png`, `vista_superior.png`, `vista_longitudinal.png`
- `modelo_3d.html` (visor 3D con casillas para columnas/vigas/muros/losas)

---

## 13. Notas para quien retome el trabajo

- **No hay cascarones en OpenSees** en este build: muros y losas van modelados como *frame* (muros) y *diafragma rígido* (losas). Si se quisieran shells reales, habría que añadirlos.
- El script crea los patrones de carga OpenSees `D` (tag 1), `L` (tag 2) y `COMB` (tag 3). Las cargas se aplican hacia −Z a los nodos de las losas, repartiendo cada panel en sus cuatro esquinas. No se ejecuta todavía un análisis estructural; los patrones quedan definidos para el análisis posterior.
- La geometría plana se **replica verticalmente** por piso; las reglas por piso (columnas excluidas) se aplican dentro de `construir_modelo`.
- Los **huecos de losa** están ligados a la huella de los muros (`_huellas_muro`) y solo existen en Z=0→12 de la bahía X=−10→0.
- Si cambias `MURO_YPOS` o `MUROS_ESTRUCTURALES`, cambiarán las huellas y por tanto los huecos de losa de la zona X negativa. Revisa `_huellas_muro`, `celdas_fuera_hueco` y los parámetros `MURO_*`.
- Los ids de los elementos equivalentes de muro usan base `500000+` para no chocar con columnas/vigas normales.
