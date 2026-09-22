# SEMANA 3 — Casos de carga base, sismo pseudoestático, superposición y capacidad de sección (fibras)

**Proyecto MCOC — Edificio de Ingeniería UANDES (Edificio 1)**

Unidades de trabajo: **kN y metros**. Modelo en OpenSees (`openseespy` 3.8.0.0, Python 3.12).

---

## 0. Objetivo

Construir y verificar los casos de carga base sobre el modelo estructural del
Edificio 1 (Semana 2):

- **Parte A**: carga viva `Q` (sobrecarga de uso) con conservación exacta.
- **Parte B**: sismo pseudoestático `EX` y `EY` (20 % g), verificación de corte
  basal, sentido de la deformada y torsión de piso.
- **Parte C**: superposición lineal
  `R = λG·G + λQ·Q + λEX·EX + λEY·EY` contra la corrida explícita simultánea.
- **Parte D**: sección de fibras de la columna 70×70 cm (H-30), curva
  momento–curvatura `M–φ` y primeros puntos de la interacción `P–M`.

Todo el código y los resultados quedan en la carpeta `semana3/`.

---

## 1. Contexto del modelo

Modelo de Semana 2 (gravedad) ya resuelto y conservado exactamente:

| Nivel | Z [m] | Área losa [m²] |
|---|---|---|
| FOUNDATION | −4.16 | — (apoyos) |
| CIELO_1S | −4.01 | 496.06 |
| CIELO_1 | −0.05 | 496.06 |
| CIELO_2 | 3.91 | 496.06 |
| CIELO_3 | 7.87 | 496.06 |
| CIELO_4 | 11.83 | 496.06 |

Cargas por nivel (Cuadro 1 del enunciado, g = 9.81 m/s²):

| Nivel | Muerta `D` [kN/m²] | Viva `Q` [kN/m²] |
|---|---|---|
| CIELO_1S … CIELO_3 | 6.2294 | 4.905 |
| CIELO_4 (cubierta) | 5.6408 | 1.962 |

Sismo pseudoestático según NCh433/SEG, formato fuerza en centro de masa:

```
F_i = C · W_i ,   W_i = (D_i + 0,5·Q_i)·A_piso ,   C = 20 % g
```

---

## 2. Parte A — Carga viva `Q`

Se aplica `Q` como carga uniforme sobre las vigas (áreas tributarias por el
método b/a de Semana 2, ahora generalizado a área pura para poder aplicar `D`
o `Q`). Verificación por **conservación**:

```
Q_transferida = Σ w·largo = q_Q · A_losa
```

Resultado (error ~ 1e-12):

| Nivel | q_Q [kN/m²] | A [m²] | Q transferida [kN] |
|---|---|---|---|
| CIELO_1S…3 | 4.905 | 496.06 | 2433.183 |
| CIELO_4 | 1.962 | 496.06 | 973.273 |
| **Total** | — | 2480.31 | **10706.003** |

`Q_esperada = 4.905·2480.31 = 10706.003 kN` → **conservación exacta**.

Script: `part_a_live.py` → `resultados/part_a_carga_viva.json`

---

## 3. Parte B — Sismo pseudoestático `EX` / `EY`

Masa (peso) sísmica por piso y fuerza lateral:

| Nivel | W = D+0.5·Q [kN] | F [kN] |
|---|---|---|
| CIELO_1S…3 | 4306.73 | 861.347 |
| CIELO_4 | 3284.80 | 656.959 |
| **Σ** | — | **4102.346** |

Fuerzas aplicadas en el nodo maestro (diafragma rígido, centro de masa =
centroide geométrico) en la dirección del sismo.

**Verificaciones:**

| Verificación | EX | EY |
|---|---|---|
| Carga lateral total | 4102.346 kN | 4102.346 kN |
| Corte basal (Σ reacciones) | 4102.346 kN | 4102.346 kN |
| Error | 7.5e-11 kN | 5.0e-11 kN |
| Deformada orientada + | ✓ | ✓ |
| Desplazamiento tope CIELO_4 | 0.0350 m | 0.0057 m |
| Torsión piso máx (rz) | 1.7e-5 rad | 1.3e-4 rad |

Observaciones:
- El edificio es **mucho más rígido en Y** (más muros en esa dirección), por
  eso el desplazamiento por `EY` es ≈ 6 veces menor que por `EX`.
- La **torsión de piso** (rz del diafragma) es mayor en `EY`, por la asimetría
  relativa de la distribución de muros respecto a esa dirección.

Script: `part_b_seismic.py` → `resultados/part_b_sismo.json`

---

## 4. Parte C — Superposición lineal

Combinación estudiada (factores arbitrarios de un combo lineal elástico):

```
R = 1.0·G + 0.5·Q + 0.3·EX + 0.2·EY
```

Se compara:
1. la **suma de los resultados** de 4 corridas independientes
   (`run_case` por caso), ponderada por cada λ, y
2. una **corrida explícita** con los 4 patrones actuando a la vez sobre el
   mismo modelo.

Criterio: máximo error absoluto entre ambas en desplazamientos, reacciones y
fuerzas internas.

| Campo | Máximo error | Umbral |
|---|---|---|
| Desplazamientos | 7.1e-16 m | 1e-6 |
| Reacciones (suma) | 8.9e-11 kN | 1e-6 |
| Reacciones (por nodo) | 4.6e-11 kN | 1e-6 |
| Fuerzas internas | 1.6e-8 kN | 1e-6 |

**SUPERPOSICIÓN LINEAL VÁLIDA: ✓** (errores a precisión de máquina).

*Nota de implementación:* `run_case` ya escala la carga por su λ, por lo que
la combinación solo suma los resultados; una doble multiplicación por λ
habría producido un falso error (detectado y corregido durante el desarrollo).

Script: `part_c_superposicion.py` → `resultados/part_c_superposicion.json`

---

## 5. Parte D — Sección de fibras de la columna 70×70

Sección `70 cm × 70 cm`, concreto **H-30** (f'c = 30 MPa) y
**8 φ 25** (A630-420H, fy = 420 MPa, Es = 200 GPa; cuantía ≈ 0.80 %).

En OpenSees se define la sección `section Fiber` (concrete `Concrete01`,
acero `Steel01`). La curva `M–φ` y los puntos `P–M` se obtienen por
**integración de fibras** (compatibilidad de deformaciones): para cada
curvatura κ se busca la deformación ε₀ que equilibra la carga axial `P`
(bisección) y se integra el momento respecto al centroide.

**Curva M–φ (P = 0, flexión pura):**
- M_max ≈ **654 kN·m**
- 501 puntos de 0 a 0.12 1/m (acero con endurecimiento).

**Curva M–φ con P = 0.2·Pn₀ ≈ 2499 kN:** M_max ≈ **1238 kN·m**.

**Primeros puntos de interacción P–M** (Pn₀ = 0.85·f'c·Ag = 12495 kN):

| P [kN] | P/Pn₀ | M_max [kN·m] |
|---|---:|---:|
| 0 | 0.00 | 654 |
| 1250 | 0.10 | 988 |
| 2499 | 0.20 | 1238 |
| 3748 | 0.30 | 1410 |
| 5623 | 0.45 | 1525 |
| 7497 | 0.60 | 1502 |

**Interpretación:** la resistencia a flexión de la columna crece con niveles
moderados de compresión axial (hasta el punto balanceado, ≈ 0.4–0.45·Pn₀) y
luego cae hacia la compresión pura (forma clásica del diagrama de interacción
P–M de columnas de hormigón armado).

Script: `part_d_fiber.py` → `resultados/part_d_fiber.json`

---

## 6. Cómo ejecutar

```powershell
# desde P1L2/Edificio 1 y 2 (entorno base de anaconda, Python 3.12)
py -3.12 semana3\part_a_live.py
py -3.12 semana3\part_b_seismic.py
py -3.12 semana3\part_c_superposicion.py
py -3.12 semana3\part_d_fiber.py
```

Los resultados quedan en `semana3/resultados/*.json`.

---

## 7. Archivos

| Archivo | Contenido |
|---|---|
| `semana3/base_cases.py` | Construcción y corridas G/Q/EX/EY reutilizables |
| `semana3/part_a_live.py` | Parte A |
| `semana3/part_b_seismic.py` | Parte B |
| `semana3/part_c_superposicion.py` | Parte C |
| `semana3/part_d_fiber.py` | Parte D |
| `semana3/resultados/` | JSONs de salida |

Materiales/geometría: `materials.py`, `structural_model.py`, `tributary.py`,
`sections.py` (Semana 2, sin cambios).