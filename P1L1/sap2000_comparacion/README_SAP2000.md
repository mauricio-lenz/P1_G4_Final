# Comparacion SAP2000 - Benchmark 3D

Esta guia permite armar en SAP2000 el mismo marco 3D usado en `benchmark_3d_opensees.py` para comparar desplazamientos, reacciones y fuerzas internas.

## 1. Unidades

Antes de crear el modelo, usar:

```text
kN, m, C
```

## 2. Geometria

Crear un modelo 3D con 8 joints y 8 frame objects.

Coordenadas en `sap_joints.csv`.

Resumen:

- Vano X: 6.0 m
- Vano Y: 5.0 m
- Altura: 3.2 m
- Columnas: elementos 1 a 4
- Vigas superiores: elementos 5 a 8

## 3. Material

Crear un material elastico llamado `A36_OPENSEES`:

```text
E = 200000000 kN/m2
nu = 0.30
G = 76923076.923 kN/m2
```

## 4. Secciones

Para que SAP2000 sea comparable con OpenSeesPy, lo mas directo es crear secciones con propiedades modificadas usando `General Frame Section`.

### Columna COL_TUB_30x30x1p2

```text
A  = 0.013824 m2
I22 = 1.914348e-04 m4
I33 = 1.914348e-04 m4
J  = 3.828695e-04 m4
```

### Viga VIGA_RECT_25x40

```text
A  = 0.100000 m2
I22 = 5.208333e-04 m4
I33 = 1.333333e-03 m4
J  = 1.854167e-03 m4
```

Nota: SAP2000 usa ejes locales `2` y `3`. En OpenSeesPy se imprimen como `Iy` e `Iz`. Para comparar, mantener las mismas propiedades numericas.

## 5. Apoyos

Asignar restricciones en nodos 1, 2, 3 y 4 segun `sap_restraints.csv`.

Por defecto son empotrados:

```text
U1 U2 U3 R1 R2 R3 = Yes Yes Yes Yes Yes Yes
```

## 6. Cargas

Crear un load pattern llamado:

```text
LOSA
```

Tipo recomendado:

```text
Dead
```

Self Weight Multiplier:

```text
0
```

Aplicar cargas distribuidas verticales globales hacia abajo sobre vigas:

- Vigas X, elementos 5 y 7: `7.5 kN/m`
- Vigas Y, elementos 6 y 8: `9.0 kN/m`

Ver tabla `sap_frame_loads.csv`.

En SAP2000 usar:

```text
Assign > Frame Loads > Distributed
Load Pattern: LOSA
Coordinate System: Global
Direction: Z
Load: -7.5 o -9.0 kN/m
```

## 7. Caso de analisis

Usar analisis lineal estatico para el load pattern `LOSA`.

## 8. Resultados a comparar

Comparar con `../resultados_verificacion_3d.md`.

Valores esperados principales:

```text
Suma cargas verticales = -180.000 kN
Suma reacciones verticales = 180.000 kN
Uz nodo 5 = -5.208333e-05 m
Axial local elemento 1 = 45.000 kN
Momento local My elemento 5 extremo i = -13.031 kN*m
```

## 9. Donde ver resultados en SAP2000

Desplazamiento nodo 5:

```text
Display > Show Tables > Analysis Results > Joint Output > Displacements
```

Reacciones:

```text
Display > Show Tables > Analysis Results > Joint Output > Reactions
```

Fuerzas internas:

```text
Display > Show Tables > Analysis Results > Element Output > Frame Output > Frame Forces
```

Diagramas:

```text
Display > Show Forces/Stresses > Frames/Cables/Tendons
```

Elegir:

- Axial Force
- Shear 2-2 o Shear 3-3
- Moment 2-2 o Moment 3-3

La direccion exacta depende de los ejes locales del frame en SAP2000. Revisar con:

```text
Display > Show Misc Assigns > Frame/Cable/Tendon > Local Axes
```
