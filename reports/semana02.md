# Informe Semana 2 — Modelo Estructural por Gravedad (Edificio Completo P1L2)

> **Alcance:** todos los datos corresponden al **edificio completo** (unión de Edificio 1 + Edificio 2 conectados como una sola pieza), exportado en `P1L2/resultados/estructura_completo_unity.json` por `P1L2/scripts/unificar_edificios.py`. No son los valores de cada edificio por separado.
>
> **Unidades:** m, kN, kN·m. Niveles: CIELO_1S (Z≈0), CIELO_1 (Z=4), CIELO_2 (Z=8), CIELO_3 (Z=12), CIELO_4 (Z=16, nominal).

---

## 1. Trazabilidad desde planos

Cadena de trazabilidad de cada elemento del edificio completo:

`plano (eje de trabajo) → nodos (id + coordenadas) → elemento (id/tag) → sectionTag → elementTag`

| Plano / eje | Nodos (x, y, z) | Elemento (id · tag) | SectionTag (b×h m) | ElementTag |
|---|---|---|---|---|
| Planta CIELO_1 (Z=4), eje X=5, tramo Y 0→8.9 | 27 (5, 0, 4) — 28 (5, 8.9, 4) | 29 · viga | V60/80 (0.60×0.80) | `E1_29` |
| Planta CIELO_4 (Z=16), eje Y=0, tramo X −10→0 | 114 (0, 0, 16) — 111 (−10, 0, 16) | 165 · viga | V60/80 (0.60×0.80) | `E1_165` |
| Planta CIELO_4 (Z=16), eje X=0, tramo Y 0→8.9 | 114 (0, 0, 16) — 115 (0, 8.9, 16) | 167 · viga | V60/80 (0.60×0.80) | `E1_167` |
| Edificio 2, eje X=−41.475 (viga borde), Y −7.25→8.9 | 262 (−41.475, −7.25, 0.16) — 263 (−41.475, 8.9, 0.16) | 358 · viga | V40/80 (0.40×0.80) | `B3001_V40/80` |
| Edificio 2, eje Y=4.635, X −41.475→−33.975 | 276 (−41.475, 4.635, 0.16) — 277 (−33.975, 4.635, 0.16) | 369 · viga | V30/80 (0.30×0.80) | `B3012_V30/80` |
| Columna, eje X=−10 · Y=−7.25 · Z 0→4 | 1 (−10, −7.25, 0) — 19 (−10, −7.25, 4) | 229 · columna | COL70/70 (0.70×0.70) | `E1_229` |
| Muro ppal NEG, banda X=−6.7→−3.3, Y=−4.945, Z 0→4 | 173 (−6.7, −4.945, 0) — 172 (−3.3, −4.945, 0) | muro (panel equivalente) | t=0.20 × L=3.40 | panel `FOUNDATION→CIELO_1S` |

En OpenSees los muros se modelan como **vigas/columnas equivalentes** (tags base `500000+`); los nodos y elementos de esta tabla se leen directamente del JSON del edificio completo (`elements[].id`, `nodeI`, `nodeJ`, `sectionId`) y se pueden consultar con:

```bash
python P1L2\scripts\opensees_edificio_completo.py --id E1_29
python P1L2\scripts\opensees_edificio_completo.py --id B3001_V40/80
python P1L2\scripts\opensees_edificio_completo.py --id 229
```

## 2. Estadísticas

Conteo real del edificio completo (`estructura_completo_unity.json`):

| Componente | Cantidad | Observaciones |
|---|---|---|
| Nodos | **373** | (301 usados por elementos/apoyos + 72 auxiliares de losas/huecos) |
| Columnas | **129** | COL70/70 (0.70×0.70 m) |
| Vigas | **288** | V60/80: 273, V40/80: 5, V30/80: 10 |
| Elementos frame totales | 417 | 129 columnas + 288 vigas |
| Muros estructurales | **30** | 10 paneles t=0.20 (L=3.40) + 20 paneles t=0.25 (L=1.575) |
| Losas (paneles de diafragma) | **226** | CIELO_1S: 29 · CIELO_1: 45 · CIELO_2: 47 · CIELO_3: 48 · CIELO_4: 57 |
| Diafragmas rígidos | **5** | uno por nivel (maestros 1, 22, 53, 157, 159) |
| Apoyos | **30** | 18 del edificio 1 (Z=−4 y Z=0) + 12 del edificio 2 (Z≈0) |
| Pisos | **5** | CIELO_1S, CIELO_1, CIELO_2, CIELO_3, CIELO_4 |
| Procedencia | — | 317 elementos del edificio 1, 100 del edificio 2 |

Rango de la geometría completa: X ∈ [−41.475, 40.00] m · Y ∈ [−17.97, 8.90] m · Z ∈ [0, 16] m.

## 3. Carga superficial

Parámetros de la losa y cargas de diseño del edificio completo:

| Parámetro | Valor | Nota |
|---|---|---|
| Espesor de losa | 0.15 m | `ESPESOR_LOSA = 0.15` |
| Peso unitario | 25.0 kN/m³ | hormigón armado (modelo) / 2500 kg/m³ (análisis) |
| Peso propio losa | 3.75 kN/m² | 0.15 × 25.0 (3.68 kN/m² con 2500 kg/m³) |
| Carga de terminaciones | 1.0 kN/m² | tabiquería + cielo (pisos 1S–3: 260 kg/m², cubierta: 200 kg/m² en análisis) |
| Carga viva | 2.0 kN/m² | 500 kg/m² (pisos) / 200 kg/m² (cubierta) en el análisis ACI |
| **q_G (diseño, gobierna 1.2D+1.6L)** | **15.323 kN/m²** (CIELO_1S–3) · **9.908 kN/m²** (CIELO_4) | `materials.Q_G_BY_LEVEL` |
| Referencia q_G del JSON completo | 6.227 kN/m² | componente D de referencia usada por el viewer |

Modelo de reparto: las losas no son shells; cada panel transfiere su carga superficial (D, L y COMB = 1.2D+1.6L) a los nodos de sus 4 esquinas y a las vigas perimetrales por el método de **áreas tributarias b/a**.

## 4. Áreas tributarias (ejemplos)

Esquema del método (losa según relación de lados b/a): para `b/a < 2` el lado corto recibe un **triángulo** a²/4 y el lado largo un **trapecio** a(2b−a)/4; para `b/a ≥ 2` solo los lados largos reciben a·b/2. Cada polígono se asigna completo a la viga de borde que lo cubre.

| Viga (elementTag · piso) | Polígono tributario (lados/sourceEdges) | A (m²) | L (m) | Nodos | q_COMB efectiva (kN/m²) | Carga total U=1.2D+1.6L (kN) | Distribución aplicada |
|---|---|---|---|---|---|---|---|
| `E1_29` · CIELO_1 | 2 triángulos (16.00 + 16.00) | 32.00 | 8.9 | 27–28 | 15.318 | 490.18 | w = −55.1 kN/m (uniforme) |
| `E1_165` · CIELO_4 | 2 trapecios (24.70 + 23.11) | 47.81 | 10.0 | 114–111 | 9.906 | 473.51 | w = −47.4 kN/m (uniforme) |
| `E1_167` · CIELO_4 | trapecio (19.80) + triángulo (16.00) | 35.80 | 8.9 | 114–115 | 9.905 | 354.61 | w = −39.8 kN/m (uniforme) |
| `B3001_V40/80` · e2 | borde de losa (con prorrateo por largo cubierto) | 8.96 | 16.15 | 262–263 | 15.319 | 137.29 | w = −8.50 kN/m (uniformLoad) |

Las tensiones superficiales efectivas (15.32 y 9.91 kN/m²) coinciden con q_G de diseño por nivel, lo que confirma que las áreas tributarias alimentan el mismo cuadro de cargas de la sección 3.

## 5. Conservación

Tolerancias adoptadas (`materials.py`): **TOL_AREA = 0.02 m²** y **TOL_CONSERVACION = 0.05 kN**.

### 5a. Conservación de carga de losa → fuerzas nodales (edificio completo)

La carga superficial de cada panel se transfiere a sus 4 nodos esquina; la suma de las fuerzas nodales consolida exactamente el producto q·A:

| Patrón | q (kN/m²) | A_losa (m²) | q·A esperada (kN) | Σ fuerzas nodales (kN) | Error (kN) |
|---|---|---|---|---|---|
| D | 4.75 | 3315.95 | 15750.774 | 15750.774 | 0.000 |
| L | 2.00 | 3315.95 | 6631.905 | 6631.905 | 0.000 |
| COMB (1.2D+1.6L) | 8.90 | 3315.95 | 29511.976 | 29511.976 | 0.000 |

Además, Σ(COMB) = 1.2·ΣD + 1.6·ΣL = 29511.98 kN (exacto). **Error 0 dentro de la tolerancia.**

### 5b. Conservación de áreas tributarias por piso

Por construcción del método, cada panel reparte su superficie completa (ΣA_trib = ΣA_losa analizada, sin factor de ajuste):

| Piso | A_trib = A_losa (m²) | Err área (m²) | Estado |
|---|---|---|---|
| CIELO_1S | 139.33 | 0.000 | OK |
| CIELO_1 | 735.52 | 0.000 | OK |
| CIELO_2 | 760.12 | 0.000 | OK |
| CIELO_3 | 832.27 | 0.000 | OK |
| CIELO_4 | 848.70 | 0.000 | OK |

Nota: el archivo del edificio completo contiene también paneles de visualización (radier/escalera/voladizos sin viga); la superficie total de los 226 paneles es 5729.41 m², mientras que la superficie analizada por el camino tributario es la de la tabla.

## 6. Apoyos y restricciones

- **30 apoyos**, **todos empotrados (6 GDL fijos)**: `ux=uy=uz=rx=ry=rz=1` (`type: fixed`).
- Son los únicos tipos usados (no hay pasadores ni rodillos en el edificio completo).
- Ubicación (por nivel):
  - **Z = −4 (sótano)**: nodos 164–169 (X=−10 y X=0, en las 3 líneas Y) — edificio 1.
  - **Z = 0**: nodos 7–18 (X=10, 20, 30, 35, en las 3 líneas Y) — edificio 1 (columnas que no arrancan del sótano).
  - **Z ≈ 0.01 (baja)**: nodos 242–253 (X=−37.73…−9.95, incl. Y=−17.97/−13.67 del edificio 2).
- Representación gráfica: el viewer Unity dibuja cada apoyo como un **símbolo de empotramiento** (cubo naranja) con su etiqueta `N{id}\nEmpotrado` (ver sección 8).

## 7. Diafragmas: cinemática y verificación numérica

Los diafragmas se modelan con el comando `rigidDiaphragm` de OpenSees: en cada nivel un **nodo maestro** fija el movimiento horizontal del plano y los nodos esclavos se mueven como cuerpo rígido.

**Cinemática:** para un esclavo E con vector relativo r = (x_E − x_M, y_E − y_M) al maestro M, el movimiento horizontal queda:

```
u_E = u_M − θ·(y_E − y_M)
v_E = v_M + θ·(x_E − x_M)
w_E   libre (vertical no restringida por el diafragma)
```

(3 GDL por nivel: traslaciones u_M, v_M y giro de piso θ.)

**Verificación numérica (del JSON del edificio completo):**

| Nivel | Maestro | Esclavos | Esclavos válidos | Rango X (m) | Rango Y (m) |
|---|---|---|---|---|---|
| CIELO_1S | 1 | 17 | 17/17 | −10.00…0.00 | −7.25…8.90 |
| CIELO_1 | 22 | 42 | 42/42 | −10.00…35.00 | −11.37…8.90 |
| CIELO_2 | 53 | 45 | 45/45 | −10.00…35.00 | −11.37…8.90 |
| CIELO_3 | 157 | 49 | 49/49 | −10.00…40.00 | −11.37…8.90 |
| CIELO_4 | 159 | 34 | 34/34 | −10.00…40.00 | −11.37…8.90 |

Todos los esclavos existen como nodos y están **co-planares** a su nivel; la verificación de compatibilidad del análisis (del informe que genera la exportación) arroja asentamientos verticales coherentes con un plano rígido (Δ vertical del orden de 0.13–0.19 m, sin agrietamiento).

## 8. Viewer Unity

Controlador `StructureViewer.cs` + `ElementPicker` + `DiagramController` (escena `StructureViewerScene`), cargando `Assets/Resources/estructura_completo_unity.json`:

- **Capas:** toggles de visibilidad — *Columnas, Vigas, Muros equiv., Apoyos, Diafragmas, Nodos, IDs, Ejes locales*.
- **Selección:** click sobre una barra → popup con resultados interpolados (axial N, corte local Vz, momento My). Teclas `0/1/2/3` ocultan/muestran los diagramas.
- **IDs:** botones *Mostrar nodos* y *Mostrar IDs* etiquetan nodos (cian) y elementos (blanco) con su `id`.
- **Ejes:** ejes globales X (rojo), Y (verde), Z (azul) y ejes locales de cada elemento (magenta).
- **Apoyos:** símbolos de empotramiento con etiqueta `N{id} Empotrado` en sus 30 posiciones.
- **Áreas tributarias:** panel GUI que lista por piso el área total (m²) y la carga total (kN), y cada losa muestra en su info área, q_G y carga gravitacional estimada.

## 9. Modificación del modelo (desde datos)

Ejemplo implementable sin reanálisis automático desde Unity: **cambiar la sección de una viga** en el JSON del edificio completo.

Viga `E1_165` (actual: V60/80, 0.60×0.80 m). Para cambiar a **V40/80** (0.40×0.80 m):

```json
{
  "id": 165,
  "nodeI": 114, "nodeJ": 111,
  "sectionId": "V40/80",
  "width_m": 0.40,
  "height_m": 0.80
}
```

Cambios equivalentes sobre datos:
- **Sección:** editar `sectionId`/`width_m`/`height_m` (o la tabla `SECTIONS` de `unificar_edificios.py`).
- **Apoyo:** nodo 7 `(10,−7.25,0)` de empotrado a pasador → `"ux":1,"uy":1,"uz":1,"rx":0,"ry":0,"rz":0`.
- **Polígono tributario:** ajustar `source_edges[].tributary_area_m2` (o la regla b/a en `P1L2/Edificio 1 y 2/tributary.py`) y la carga se recalcula con q·A.

Para regenerar: `python P1L2\scripts\unificar_edificios.py` (re-exporta `estructura_completo_unity.json` y copia al viewer). El modelo OpenSees se reconstruye con `python P1L2\scripts\opensees_edificio_completo.py`.

## 10. Uso de IA (corrección de un error generado por el agente)

**Caso: definición de los huecos de losa en la zona X negativa.**

- **Error generado por el agente:** propuso los huecos como un recorte de banda completa de losa (`X=−10→−5`) o como rectángulos fijos que no coincidían con la posición real de los muros estructurales, generando un recuento de losas inconsistente con la arquitectura.
- **Corrección:** el hueco debe coincidir con la **huella en planta (rectángulo envolvente) de cada muro estructural**:
  - Hueco NEG: X = −6.7→−3.3, Y = −4.95→0 (lado COMP→P2), solo en niveles CIELO_1S a CIELO_3 (Z=0…12).
  - Hueco POS: X = −6.7→−3.3, Y = 3.425→5.0 (lado P1→COMP), mismos niveles.
  - En CIELO_4 (Z=16) la losa es completa (los muros no generan hueco en la cubierta).
- **Implementación:** función `celdas_fuera_hueco()` que subdivide la bahía en los bordes del hueco y emite sólo las celdas fuera del rectángulo, con **nodos auxiliares** en los bordes (fusionados a la lista de nodos antes de descartar nodos sin elementos). Resultado verificado: **101 paneles de losa y 241 nodos** consistentes con los 30 paneles de muro.
- URL fuente del modelo: `P1L2/Edificio 1 y 2/edificio 1/modelo_pasillos.py` (`construir_losas`, `celdas_fuera_hueco`, `_huellas_muro`).

---

## Fuentes y reproducción

| Archivo | Rol |
|---|---|
| `P1L2/resultados/estructura_completo_unity.json` | Modelo del edificio completo (nodos, elementos, muros, losas, apoyos, diafragmas, áreas tributarias) |
| `P1L2/scripts/unificar_edificios.py` | Unión Edificio 1 + Edificio 2 y export del JSON completo |
| `P1L2/scripts/opensees_edificio_completo.py` | Construcción del modelo OpenSees y consulta por ID |
| `P1L2/Edificio 1 y 2/materials.py` | Materiales y cargas superficiales (q_G por nivel) |
| `P1L2/Edificio 1 y 2/tributary.py` | Método de áreas tributarias b/a |
| `P1L2/Edificio 1 y 2/edificio 1/resultados/cargas.json` | Cargas D/L/COMB por losas → fuerzas nodales (conservación 5a) |
| `P1L2/unity_visualizador/` | Viewer Unity (capas, selección, IDs, ejes, apoyos, áreas tributarias) |

Reproducción: `python P1L2\scripts\unificar_edificios.py` → `python P1L2\scripts\opensees_edificio_completo.py`.