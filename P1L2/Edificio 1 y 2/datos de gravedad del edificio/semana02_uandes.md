# UANDES - Analisis de Gravedad (Semana 2)

Analisis estructural por gravedad del **Edificio de Ingenieria UANDES de Santiago**
sobre la geometria real (`structural_geometry.json`). Modelo de superestructura en
portico: columnas + vigas + muros equivalentes + diafragmas rigidos. Escalera,
radier y fundaciones se conservan solo para visualizacion (no participan).

## Modelo

| Componente | Cantidad | Observaciones |
|---|---|---|
| Columnas | 40 | 70x70, empotradas en base |
| Vigas | 280 | union de bordes unicos de panel (V60/80, V40/80, V30/80; sin tramos solapados) |
| Muros equivalentes | 45 | elemento vertical `elasticBeamColumn`, seccion t x L |
| Apoyos (empotrados) | 17 | 8 columnas + 9 muros en base |
| Diafragmas rigidos | 5 | maestro fijado en plano, `rigidDiaphragm` |
| Losa analizada / piso | 496.06 m2 | 22 paneles por piso |

Materiales: H30 (E = 4700*sqrt(f'c)). Metros y kN.

## Cargas de diseno (Cuadro 1, g = 9.81)

- PP losa = e x 2500 kg/m3 = 0.15 x 2500 = **375 kg/m2** (3.68 kN/m2).
- Pisos CIELO 1°Sub.-3°: D = 375+260 = 635 kg/m2, L = 500 kg/m2.
  - Max(1.4D, 1.2D+1.6L) = Max(889, 1562) = **1562 kg/m2 = 15.32 kN/m2**.
- Cubierta (CIELO Piso 4°): D = 375+200 = 575 kg/m2, L = 200 kg/m2.
  - Max(1.4D, 1.2D+1.6L) = Max(805, 1010) = **1010 kg/m2 = 9.91 kN/m2**.

## Areas tributarias (metodo de losa por relacion de lados b/a)

La losa no se modela con elementos finitos; cada panel rectangular aporta su
superficie a las vigas perimetrales segun la relacion b/a (opcion a: rectangulo
envolvente del panel):

- **b/a < 2 -> en dos direcciones**: lado corto recibe un TRIANGULO (a^2/4),
  lado largo un TRAPECIO (a(2b-a)/4). Reparto a los 4 lados.
- **b/a > 2 -> en una direccion**: solo los lados largos, cada uno a*b/2.
  Los lados cortos no reciben carga.

Se garantizan vigas de reparto bajo **todos** los bordes de panel (creando los
nodos faltantes), de modo que cada panel queda apoyado en sus 4 lados. La malla
de vigas se arma como la **union de los bordes unicos de los paneles**: cada
borde compartido es UNA viga (sin duplicados ni solapamientos). La seccion de
cada borde es la de la viga de Santiago que lo cubre (misma linea, borde dentro
del tramo) o V30/80 (reparto) si no existe. Asi, el area tributaria de cada lado
se asigna completa a su unica viga de borde (p.ej. el trapecio del lado de L202
= 11.446 m2 va completo a su viga; el triangulo = 4.548 m2 a la viga del borde).

## Verificaciones

### 1 y 2. Conservacion de areas y carga por piso (error 0)

| Piso | Q_G (kN/m2) | A_losa (m2) | A_trib (m2) | carga (kN) | esperada (kN) | err_area | err_carga |
|---|---|---|---|---|---|---|---|
| CIELO_1S | 15.323 | 496.06 | 496.06 | 7601.26 | 7601.26 | 0.00000 | 0.00000 |
| CIELO_1 | 15.323 | 496.06 | 496.06 | 7601.26 | 7601.26 | 0.00000 | 0.00000 |
| CIELO_2 | 15.323 | 496.06 | 496.06 | 7601.26 | 7601.26 | 0.00000 | 0.00000 |
| CIELO_3 | 15.323 | 496.06 | 496.06 | 7601.26 | 7601.26 | 0.00000 | 0.00000 |
| CIELO_4 | 9.908 | 496.06 | 496.06 | 4915.03 | 4915.03 | 0.00000 | 0.00000 |

Conservacion exacta (error 0) sin factor de ajuste.

### 3. Carga total del edificio

Carga total = 4 x 7601.26 + 4915.03 = **35320.08 kN**.

### 4. Equilibrio global

| Reaccion | Valor (kN) | Carga (kN) | Error |
|---|---|---|---|
| Rz | 35320.077 | 35320.077 | 0.0000 |
| Rx | 0.0000 | - | - |
| Ry | -0.0000 | - | - |

Equilibrio de fuerzas verticales y horizontales verificado (error 0).

### 5. Compatibilidad de diafragma

| Piso | Esclavos | Delta vertical (m) |
|---|---|---|
| CIELO_1S | 44 | 1.75e-01 |
| CIELO_1 | 44 | 1.89e-01 |
| CIELO_2 | 44 | 1.88e-01 |
| CIELO_3 | 44 | 1.89e-01 |
| CIELO_4 | 44 | 1.30e-01 |

Asentamiento vertical coherente (orden decimetrico) con compatibilidad del plano.

### 6. Verificacion de deformacion

- **Elemento viga validado**: modelo aislado (voladizo V60/80, carga uniforme)
  da flecha FE = `w·L^4/(8·E·I)` con **ratio 1.00000** frente al valor cerrado
  (E H30 = 25.743 GPa, I = 0.0256 m4). Confirma E, inercias y aplicacion de carga.
- **Magnitud global**: el desplazamiento vertical nodal maximo del edificio es
  ~**0.19 m** (188.8 mm), consistente con los deltas de diafragma anteriores
  (~1.3 a 1.9e-1 m) para la estructura completa bajo 35,320 kN de gravedad
  (sin reduccion por agrietamiento).

## Archivos

- `structural_model.py`: ensamblaje y construccion del modelo (malla = union de
  bordes de panel, muros equivalentes, apoyos, diafragmas, nodos generados).
- `materials.py`: materiales (H30/H25) y cargas de diseno por nivel (Cuadro 1 +
  combinaciones ACI).
- `sections.py`: secciones G/E de vigas y muros.
- `tributary.py`: areas tributarias por losa (regla b/a, cono 45°).
- `gravity_analysis.py`: cargas q_G, analisis, verificaciones, export.
- `main_structural.py`: script de entrada (`python main_structural.py`).
- `outputs/resultados_gravedad.json`: resultados y verificaciones.
- `outputs/estructura_gravedad_unity.json`: export ampliado para Unity
  (diafragmas, muros, areas tributarias, ejes locales).
- `unity_visualizador/Assets/Resources/estructura_gravedad_unity.json`: copia
  para el viewer Unity.

## Ejecutar

```bat
.venv\Scripts\python.exe "P1L2\Edificio 1 y 2\main_structural.py"
```
