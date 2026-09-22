# Resultados de verificacion - Benchmark 3D OpenSees

## Estado del analisis

- Resultado OpenSees: `0`
- `0` significa que el analisis termino sin error numerico.

## Comparacion con referencias

| Verificacion | OpenSees | Referencia/estimacion | Error relativo |
|---|---:|---:|---:|
| Suma de cargas verticales aplicadas [kN] | -180.000000 | -180.000000 | 0.000e+00 |
| Suma de reacciones verticales [kN] | 180.000000 | 180.000000 | 0.000e+00 |
| Desplazamiento Uz nodo 5 [m] | -5.208333333e-05 | -5.208333333e-05 | 2.602e-16 |
| Fuerza axial local elemento 1, extremo i [kN] | 45.000000 | 45.000000 | 1.579e-16 |
| Momento local My elemento 5, extremo i [kN*m] | -13.030943 | -22.500000 | 4.208e-01 |

## Notas de referencia

- La suma de cargas se calcula con `q_losa * Lx * Ly`.
- La reaccion vertical por base se estima por simetria: `q_losa * Lx * Ly / 4`.
- El desplazamiento vertical de referencia del nodo 5 se estima como acortamiento axial de la columna: `P*H/(A*E)`.
- El axial local del elemento 1 se compara con la reaccion vertical por simetria.
- El momento de extremo de la viga 5 se compara con una estimacion de viga empotrada-empotrada `wL^2/12`; no es identico porque el marco 3D tiene nudos flexibles y columnas deformables.

## Fuerzas locales usadas

Formato local 3D: `[P_i, Vy_i, Vz_i, T_i, My_i, Mz_i, P_j, Vy_j, Vz_j, T_j, My_j, Mz_j]`.

- Elemento 1: `[45.0, -4.693551, 6.105045, -0.0, -6.5052, -5.002067, -45.0, 4.693551, -6.105045, 0.0, -13.030943, -10.017296]`
- Elemento 5: `[6.105045, 0.0, 22.5, -0.0, -13.030943, 0.0, -6.105045, -0.0, 22.5, 0.0, 13.030943, 0.0]`
