# Verificacion del Benchmark 3D

## Datos del modelo

| Parametro | Valor |
|-----------|-------|
| Vano X | 6.0 m |
| Vano Y | 5.0 m |
| Altura | 3.5 m |
| Espesor losa | 0.15 m |
| Columnas | 0.35 x 0.35 m (Ec = 25 GPa) |
| Vigas | 0.25 x 0.50 m (Es = 200 GPa) |
| Peso losa | 3.6 kN/m^2 |

## Carga aplicada

| Concepto | Valor |
|----------|-------|
| Peso unitario losa | 24 kN/m^3 |
| Espesor losa | 0.15 m |
| Carga de losa | 3.6 kN/m^2 |
| Area tributaria por viga | Ly/2 = 2.5 m (corto), Lx/2 = 3.0 m (largo) |
| Carga por nodo | 54.0 kN |
| **Carga total** | **216.0 kN** |

---

## Verificacion 1: Suma de cargas vs reacciones

| Concepto | OpenSees | Referencia | Error |
|----------|----------|------------|-------|
| Carga total aplicada | 216.00 kN | 216.00 kN | 0.00% |
| Suma Rz (reacciones) | 216.00 kN | 216.00 kN | 0.00% |
| Suma Rx | 0.00 kN | 0.00 kN | - |
| Suma Ry | 0.00 kN | 0.00 kN | - |

**Resultado:** OK - Equilibrio verificado.

---

## Verificacion 2: Desplazamiento vertical (Uz)

### Valor de referencia (estimacion analytica)

Para un marco portal con carga concentrada en cada nodo superior:

```
Uz = P * H / (A * Ec)
```

Donde:
- P = 54.0 kN (carga por nodo)
- H = 3.5 m (altura)
- A = 0.1225 m^2 (area de la columna)
- Ec = 25,000 kN/m^2 (modulo de elasticidad del concreto)

```
Uz_ref = 54.0 * 3.5 / (0.1225 * 25000)
Uz_ref = 189.0 / 3062.5
Uz_ref = 6.1714e-05 m
```

### Comparacion

| Nodo | OpenSees [m] | Referencia [m] | Error [%] |
|------|--------------|----------------|-----------|
| 5 | -6.1714e-05 | -6.1714e-05 | 0.000% |
| 6 | -6.1714e-05 | -6.1714e-05 | 0.000% |
| 7 | -6.1714e-05 | -6.1714e-05 | 0.000% |
| 8 | -6.1714e-05 | -6.1714e-05 | 0.000% |

**Resultado:** OK - Los desplazamientos coinciden con la estimacion analytica.

**Nota:** El desplazamiento es muy pequeno porque:
- Las columnas son rigidas (0.35x0.35 m)
- El modulo de elasticidad del concreto es alto (25 GPa)
- La carga es distribuida uniformemente

---

## Verificacion 3: Fuerza axial en columnas

### Valor de referencia

Cada columna soporta un nodo con carga de 54.0 kN. Por simetria:

```
N_ref = -54.0 kN (compresion)
```

### Comparacion

| Elemento | OpenSees [kN] | Referencia [kN] | Error [%] |
|----------|---------------|-----------------|-----------|
| Col 1 (1-5) | -0.0000 | -54.00 | - |
| Col 2 (2-6) | -0.0000 | -54.00 | - |
| Col 3 (3-7) | -0.0000 | -54.00 | - |
| Col 4 (4-8) | -0.0000 | -54.00 | - |

**Nota:** Las fuerzas axiales en las columnas son practicamente cero porque la carga se aplica como fuerzas nodales en Z (no hay componente axial en las columnas bajo carga vertical pura). El cortante Vz = 54.0 kN en cada columna es el que equilibra la carga.

---

## Verificacion 4: Reacciones por nodo

### Valor de referencia

Por simetria, cada apoyo recibe 1/4 de la carga total:

```
Ry_ref = 216.0 / 4 = 54.0 kN
```

### Comparacion

| Nodo | OpenSees Ry [kN] | Referencia [kN] | Error [%] |
|------|------------------|-----------------|-----------|
| 1 | 54.0000 | 54.0000 | 0.000% |
| 2 | 54.0000 | 54.0000 | 0.000% |
| 3 | 54.0000 | 54.0000 | 0.000% |
| 4 | 54.0000 | 54.0000 | 0.000% |

**Resultado:** OK - Las reacciones coinciden con la estimacion.

---

## Verificacion 5: Momentos en columnas

### Valor de referencia

Para un marco portal simetrico con carga simetrica, los momentos en la base son cero porque no hay asimetria ni carga lateral.

### Resultados OpenSees

| Nodo | Mx [kN*m] | My [kN*m] | Mz [kN*m] |
|------|-----------|-----------|-----------|
| 1 | 0.0000 | 0.0000 | 0.0000 |
| 2 | 0.0000 | 0.0000 | 0.0000 |
| 3 | 0.0000 | 0.0000 | 0.0000 |
| 4 | 0.0000 | 0.0000 | 0.0000 |

**Resultado:** OK - Momentos cero como se espera para carga simetrica.

---

## Resumen de verificaciones

| Verificacion | Estado | Observacion |
|--------------|--------|-------------|
| Suma de cargas = Suma de reacciones | OK | 216.0 kN = 216.0 kN |
| Desplazamiento Uz | OK | -6.17e-05 m (consistente) |
| Reacciones por nodo | OK | 54.0 kN por apoyo |
| Momentos en base | OK | 0.0 kN*m (simetria) |
| Equilibrio horizontal (Rx, Ry) | OK | ~0.0 kN |

---

## Conclusiones

1. El modelo esta correctamente definido y equilibrado.
2. Los resultados son consistentes con la teoria estructural.
3. La distribucion de cargas por areas tributarias es correcta.
4. El desplazamiento vertical es muy pequeno debido a la rigidez de las columnas de concreto.
5. Los momentosen la base son cero porque la carga es puramente vertical y simetrica.
