# Semana 3 — Avance: casos base y curvas de interacción

**Proyecto:** modelo estructural UANDES, Edificio 1.  
**Unidades:** kN, m, kN·m, rad.

Los resultados numéricos de este informe provienen de `P1L2/Edificio 1 y 2/semana3/resultados/`. El visualizador y los resultados del edificio completo se mantienen en la carpeta `P1L3/`.

## 1. Casos base

Se construyeron cuatro casos lineales independientes sobre el mismo modelo OpenSees:

| Caso | Descripción | Aplicación |
|---|---|---|
| `G` | Carga permanente | Peso propio, losa y terminaciones según el modelo de Semana 2 |
| `Q` | Carga viva | Carga uniforme por viga usando áreas tributarias |
| `EX` | Sismo pseudoestático X | Fuerzas laterales en dirección X |
| `EY` | Sismo pseudoestático Y | Fuerzas laterales en dirección Y |

Los casos se ejecutan con `base_cases.py`, `part_a_live.py` y `part_b_seismic.py`. La respuesta de una combinación se obtiene sin modificar la geometría ni las propiedades entre corridas.

## 2. Carga viva

Se reutilizó la misma geometría tributaria de Semana 2. Para cada viga se lee el área tributaria y se aplica la carga lineal equivalente:

```text
w_Q = q_Q · A_tributaria / L_viga
```

La conservación se verificó comparando la carga aplicada a las vigas con `q_Q·A`:

| Magnitud | Resultado |
|---|---:|
| Área total tributaria | 2480.308 m² |
| Carga viva transferida | 10706.003 kN |
| Carga viva esperada `q_Q·A` | 10706.003 kN |
| Error absoluto | 3.64·10⁻¹² kN |
| Error relativo | 3.40·10⁻¹⁴ % |

Las intensidades usadas fueron 4.905 kN/m² en CIELO_1S a CIELO_3 y 1.962 kN/m² en CIELO_4. La conservación confirma que el reparto de áreas tributarias se reutiliza sin pérdida de carga.

## 3. Sismo pseudoestático

Se adoptó:

```text
W_i = D_i + 0.5 Q_i
F_i = C · W_i
C = 0.20
```

La fuerza se aplica en el centro de masa del diafragma de cada piso. Los pesos y fuerzas por piso son:

| Piso | `W_i` [kN] | `F_i` EX/EY [kN] | Centro de masa `(x,y,z)` [m] |
|---|---:|---:|---|
| CIELO_1S | 4306.733 | 861.347 | (18.234, 6.742, −4.01) |
| CIELO_1 | 4306.733 | 861.347 | (18.234, 6.742, −0.05) |
| CIELO_2 | 4306.733 | 861.347 | (18.234, 6.742, 3.91) |
| CIELO_3 | 4306.733 | 861.347 | (18.234, 6.742, 7.87) |
| CIELO_4 | 3284.796 | 656.959 | (18.234, 6.742, 11.83) |
| **Total** | — | **4102.346** | — |

### Resultados globales

| Magnitud | EX | EY |
|---|---:|---:|
| Fuerza lateral total | 4102.346 kN | 4102.346 kN |
| Corte basal por reacciones | 4102.346 kN | 4102.346 kN |
| Error de corte basal | 7.55·10⁻¹¹ kN | 5.00·10⁻¹¹ kN |
| Desplazamiento máximo de techo | 0.03502 m | 0.00571 m |
| Rotación máxima de diafragma `rz` | 1.7·10⁻⁵ rad | 1.28·10⁻⁴ rad |

El edificio es aproximadamente seis veces más rígido frente a `EY`, debido a la distribución de muros en esa dirección. La mayor rotación aparece en `EY`, consistente con la asimetría de rigidez respecto al centro de masa.

## 4. Superposición

Se evaluó la combinación:

```text
R = 1.0 G + 0.5 Q + 0.3 EX + 0.2 EY
```

Se comparó la suma ponderada de cuatro corridas independientes contra una corrida explícita de OpenSees con los cuatro patrones simultáneos:

| Respuesta comparada | Error máximo |
|---|---:|
| Desplazamientos | 7.15·10⁻¹⁶ m |
| Reacciones globales | 8.89·10⁻¹¹ kN |
| Reacciones por nodo | 4.59·10⁻¹¹ kN |
| Fuerzas internas | 1.59·10⁻⁸ kN |

La corrida explícita convergió y el resultado se marcó como válido. Los errores son numéricos y están dentro de la tolerancia `1e-6` usada por el verificador.

## 5. Momento-curvatura

La sección representativa es la columna `COL70/70_FIBER`:

- Sección: 0.70 × 0.70 m.
- Hormigón: `Concrete01`, `f'c = 30 MPa`.
- Acero: `Steel01`, `fy = 420 MPa`, `Es = 200 GPa`.
- Armadura: 8 barras de diámetro 25 mm, `A_s = 3927 mm²`, cuantía 0.801 %.
- Discretización vigente: 20 × 20 fibras de hormigón, 400 fibras.

Para cada curvatura `φ` se busca la deformación axial que equilibra el axial objetivo y luego se integra el momento de las fibras:

```text
P = Σ σ_i A_i
M = Σ σ_i A_i y_i
```

Con `P = 0`, la curva alcanza aproximadamente `M = 654.4 kN·m`. Con `P = 0.2 Pn0 = 2499 kN`, alcanza `M = 1238.1 kN·m`.

La rigidez inicial se obtiene de la pendiente inicial `dM/dφ`; para `P = 2499 kN` los primeros puntos son aproximadamente `(φ,M)=(0.00024,144.3)` y `(0.00048,288.4)`, por lo que la pendiente secante inicial es cercana a `6.0·10⁵ kN·m²`.

El criterio de término de la curva vigente es `φ = 0.12 1/m` en el script de la sección de fibras. Para el modelo de capacidad HA del edificio completo se extendió la curva hasta `φ = 0.080 1/m`; la primera fluencia estimada es:

```text
ε_y = fy/Es = 0.00210
φ_y = ε_y/d' = 0.00420 1/m
M_y ≈ 425.9 kN·m
```

La discretización actual es 20×20. La sensibilidad se controló corriendo 10×10, 20×20 y 40×40 con los mismos materiales y tolerancias (`carga_viva_sismo.py`, opción 13; `resultados/part_d_sensibilidad.json`, `M_phi_sensibilidad.png`):

| Malla | Fibras | `Mmax` P=0 [kN·m] | `Mmax` P=2499 [kN·m] | `EI0` P=0 [kN·m²] |
|---|---:|---:|---:|---:|
| 10×10 | 108 | 657.78 | 1226.31 | 1.043·10⁵ |
| 20×20 | 408 | 651.85 | 1238.47 | 1.051·10⁵ |
| 40×40 | 1608 | 654.36 | 1238.08 | 1.054·10⁵ |

La malla vigente 20×20 difiere de la convergida 40×40 en −0.38 % en `Mmax` (P=0), +0.03 % en `Mmax` (P=2499) y −0.21 % en `EI0`; incluso la gruesa 10×10 queda dentro de ±1 %. Los máximos reportados arriba (654.4 y 1238.1 kN·m) son consistentes con la corrida convergida 40×40 (654.36 y 1238.08 kN·m), por lo que la discretización 20×20 se considera suficiente.

## 6. Curva P-M de columna

La envolvente se obtiene fijando varios niveles de compresión axial `P`, resolviendo la compatibilidad de deformaciones en la sección de fibras y guardando el máximo momento alcanzable para cada `P`.

Puntos representativos de `COL70/70_FIBER`:

| `P` [kN] | `P/Pn0` | `Mmax` [kN·m] |
|---:|---:|---:|
| 0.0 | 0.00 | 654.4 |
| 1249.5 | 0.10 | 987.7 |
| 2499.0 | 0.20 | 1238.1 |
| 3748.5 | 0.30 | 1409.5 |
| 5622.8 | 0.45 | 1525.0 |
| 7497.0 | 0.60 | 1502.4 |

La capacidad aumenta con compresión moderada por el mayor bloque comprimido y luego comienza a disminuir al acercarse a la compresión pura.

## 7. Curva P-M de muro

Los muros están implementados actualmente como **elementos equivalentes elásticos** (`wall_section_props`). La envolvente P-M de capacidad del muro se calculó con una **sección de fibra** independiente (`carga_viva_sismo.py`, opción 14; `resultados/part_e_wall.json`, `P_M_wall.png`), tomando el muro de mayor desarrollo del modelo:

- Sección `t × L` = 0.25 × 7.60 m, `A_g = 1.900 m²`.
- Hormigón `Concrete01` H-30, `f'c = 30 MPa`; acero `fy = 420 MPa`.
- Armadura: 76 barras φ12 (2 capas @ 200 mm), `A_s = 85.95 cm²`, cuantía 0.45 %.
- `P_n0 = 0.85 f'c A_g = 48450 kN`.

Con `P = 0` (flexión pura) la curva M-φ alcanza `M = 14452.5 kN·m` en `φ = 0.00756 1/m`. La envolvente para compresión creciente:

| `P/Pn0` | `P` [kN] | `Mmax` [kN·m] |
|---:|---:|---:|
| 0.00 | 0 | 14452.5 |
| 0.10 | 4845 | 27699.4 |
| 0.20 | 9690 | 38973.2 |
| 0.30 | 14535 | 47365.7 |
| 0.40 | 19380 | 52744.9 |
| 0.50 | 24225 | 55086.1 |
| 0.60 | 29070 | 54497.4 |
| 0.80 | 38760 | 45756.9 |
| 1.00 | 48450 | 26121.7 |

El máximo de la envolvente es `M = 55117 kN·m` en `P/Pn0 = 0.55`; para compresiones mayores la resistencia cae y el domo se cierra en compresión pura con `M = 0` en `P = 52060 kN` (`P/Pn0 = 1.075`). Se trata de la capacidad de la sección de fibra del muro; en el modelo OpenSees el muro se mantiene como elemento elástico equivalente, ya que la sección de fibra no participa todavía en el ensamblaje global.

## 8. Verificación de hormigón armado

Para la columna 70×70 se compararon puntos de la fibra con una estimación simplificada mediante bloque rectangular de compresión. El cálculo simplificado usa `f'c`, `A_g`, `A_s`, `fy`, equilibrio de fuerzas y brazo interno; la curva de fibras incorpora compatibilidad y la ley constitutiva completa.

| Punto | Fibra `P` [kN] | Fibra `M` [kN·m] | Referencia simplificada [kN·m] |
|---|---:|---:|---:|
| Flexión pura | 0 | 654.4 | 517.1 |
| Compresión moderada | 2499 | 1238.1 | aumenta respecto a flexión pura |
| Zona balanceada | 5623 | 1525.0 | 1452.5 en el cálculo nominal |
| Compresión pura | 12495 aprox. | 0 | `0.85 f'c A_g = 12495 kN` |

La diferencia entre fibra y cálculo simplificado es esperable: el bloque nominal usa una distribución idealizada, mientras que las fibras integran deformaciones y tensiones en toda la sección. La comparación no debe mezclar directamente los resultados H-25 del cálculo manual anterior con la corrida H-30 de fibras sin indicar el cambio de material.

## 9. Primera demanda-capacidad

Se eligió la columna `E1_284`, ubicada a `z = 2.0 m`. Para la combinación de demanda se usó:

```text
R = 1.0 G + 0.5 Q + 0.3 EX + 0.2 EY
```

La demanda extraída es:

```text
P_d = 343.26 kN
M_d = 760.49 kN·m
```

La capacidad de momento disponible reportada es `φM_n = 536.86 kN·m`. Por tanto:

| Indicador | Resultado |
|---|---:|
| Utilización axial | 0.044 |
| Utilización a flexión | 1.417 |
| Utilización total | 1.417 |
| Veredicto | **NO CUMPLE** |

El punto `(P_d,M_d)` queda por encima de la capacidad disponible en flexión. La verificación completa evaluó 89 columnas y encontró 17 que no cumplen; `E1_284` es la columna crítica reportada.

## 10. Edificio completo (P1L2 + edificio_2)

Los controles anteriores corresponden al modelo de `P1L2/Edificio 1 y 2`. Sobre el JSON del edificio completo (`estructura_completo_unity.json`) se corrió el mismo flujo con `carga_viva_sismo.py` (opciones 10–14). El modelo completo tiene 373 nodos, 417 elementos (129 columnas 70×70), 30 muros y 30 apoyos; la estructura se descompone en 113 componentes conectados, de los que solo el principal (169 nodos, 18 apoyos) pertenece a `edificio_1`.

### Caso G numérico

La carga permanente se aplicó solo sobre vigas de componentes apoyados (las vigas flotantes se excluyen porque no trasladan carga a los apoyos):

| Magnitud | Resultado |
|---|---:|
| G total aplicado | 23193.079 kN |
| ΣRz | 23193.079 kN |
| Error de conservación | 1.38·10⁻¹⁰ kN |
| Apoyos | 30 |

Los aportes por piso más grandes son de `edificio_1` (z=0.0→384, 4.0→3987.8, 12.0→3916.2, 16.0→5211.8 kN). En el componente principal la respuesta es pequeña (uz máx 3.3 mm, momento máx 151.5 kN·m). El resto de componentes de `edificio_2` son torres "una columna + pasillos en voladizo" de 31.5 m; sus extremos (uz 45.9 m, M 56083 kN·m) son un artefacto del modelo exportado y no representan la estructura real.

### Tablas sísmicas EX/EY por piso

Aplicando las fuerzas pseudoestáticas solo sobre la estructura soportada:

| Dirección | F total [kN] | Corte basal [kN] | Error [kN] | Desp. promedio máx [m] |
|---|---|---:|---:|---:|
| EX | 3668.660 | 3668.660 | 4.59·10⁻¹⁰ | 0.013076 |
| EY | 3668.660 | 3668.660 | 3.21·10⁻¹⁰ | 0.014008 |

Los desplazamientos promedio crecen monótonamente con la altura (EX: 0.0005 → 0.0131 m de CIELO_1S a CIELO_4). Las `u_max` nodales de la tabla EY (hasta 0.057 m) vuelven a reflejar los voladizos de `edificio_2`.

### Superposición con 3 combinaciones (NCh433)

La superposición lineal se verificó con `C1 = G + 0.5Q + 0.3EX + 0.2EY`, `C2 = G + 0.5Q + 0.3EX − 0.2EY` y `C3 = G + 0.5Q − 0.3EX + 0.2EY`:

| Margen | C1 | C2 | C3 |
|---|---:|---:|---:|
| Desplazamientos [m] | 1.40·10⁻¹¹ | 1.40·10⁻¹¹ | 1.40·10⁻¹¹ |
| Reacciones [kN] | 3.64·10⁻¹⁰ | 3.65·10⁻¹⁰ | 3.63·10⁻¹⁰ |
| Fuerzas internas | 5.9·10⁻¹³ | 1.2·10⁻¹² | 9.0·10⁻¹³ |

La superposición es válida en las tres combinaciones (error global 3.65·10⁻¹⁰, tolerancia 1e-6).

## 11. Uso de IA

Durante el desarrollo, el agente propuso inicialmente representar los huecos de losa como un recorte rectangular fijo. El grupo revisó la propuesta contra la geometría real de los muros y detectó que el recorte no coincidía con sus huellas en planta.

La convención corregida fue generar los huecos a partir del rectángulo envolvente de cada muro, subdividir las celdas en los bordes del hueco y agregar nodos auxiliares antes de eliminar nodos sin elementos. Esta revisión evitó contar losas fuera de su posición arquitectónica y dejó explícita la trazabilidad entre muros, paneles y nodos.

## Archivos de reproducción

- `P1L2/Edificio 1 y 2/semana3/base_cases.py`
- `P1L2/Edificio 1 y 2/semana3/part_a_live.py`
- `P1L2/Edificio 1 y 2/semana3/part_b_seismic.py`
- `P1L2/Edificio 1 y 2/semana3/part_c_superposicion.py`
- `P1L2/Edificio 1 y 2/semana3/part_d_fiber.py`
- `P1L2/Edificio 1 y 2/semana3/resultados/part_a_carga_viva.json`
- `P1L2/Edificio 1 y 2/semana3/resultados/part_b_sismo.json`
- `P1L2/Edificio 1 y 2/semana3/resultados/part_c_superposicion.json`
- `P1L2/Edificio 1 y 2/semana3/resultados/part_d_fiber.json`
- `P1L3/carga_viva_sismo.py` (edificio completo, opciones 10–14)
- `P1L3/resultados/carga_viva_sismo.json`
- `P1L3/resultados/part_g_gravity.json`
- `P1L3/resultados/part_b_sismo_tablas.json`
- `P1L3/resultados/part_d_sensibilidad.json`
- `P1L3/resultados/part_e_wall.json`
- `P1L3/resultados/M_phi_sensibilidad.png`
- `P1L3/resultados/P_M_wall.png`
- `P1L3/resultados/M_phi_COL70_70.png`
- `P1L3/resultados/P_M_COL70_70.png`
