# Defensa individual - Benchmark 3D OpenSees

## 6 GDL por nodo

En un modelo 3D de marco cada nodo tiene 6 grados de libertad:

- `Ux`: desplazamiento en X global
- `Uy`: desplazamiento en Y global
- `Uz`: desplazamiento en Z global
- `Rx`: rotacion alrededor de X global
- `Ry`: rotacion alrededor de Y global
- `Rz`: rotacion alrededor de Z global

Por eso el modelo se define con:

```python
ops.model("basic", "-ndm", 3, "-ndf", 6)
```

## Que representa geomTransf

`geomTransf` define la transformacion geometrica del elemento entre coordenadas locales y globales. En un elemento viga-columna 3D, OpenSees necesita saber como orientar los ejes locales `x`, `y` y `z` del elemento dentro del sistema global.

En el modelo se usan dos transformaciones:

- Columnas verticales: `ops.geomTransf("Linear", 1, 1, 0, 0)`
- Vigas horizontales: `ops.geomTransf("Linear", 2, 0, 0, 1)`

## Diferencia local/global

El sistema global es unico para toda la estructura:

- X global: direccion del vano `Lx`
- Y global: direccion del vano `Ly`
- Z global: vertical

El sistema local depende de cada elemento:

- `x local`: va desde el nodo inicial al nodo final del elemento
- `y local` y `z local`: son los ejes principales de flexion de la seccion

Las cargas, desplazamientos y reacciones se pueden interpretar en global. Las fuerzas internas de elementos conviene revisarlas en local, porque ahi aparecen axial, cortes, torsion y momentos respecto a los ejes de la seccion.

## Que representan Iy e Iz

`Iy` e `Iz` son momentos de inercia de area de la seccion respecto a sus ejes locales principales.

- `Iy`: controla la rigidez a flexion alrededor del eje local `y`
- `Iz`: controla la rigidez a flexion alrededor del eje local `z`

En `elasticBeamColumn`, estos valores entran junto con `E` para formar las rigideces `E*Iy` y `E*Iz`.

## Que esta resolviendo OpenSees

OpenSees resuelve el equilibrio estructural:

```text
K * U = F
```

Donde:

- `K`: matriz de rigidez global ensamblada con todos los elementos
- `U`: desplazamientos y rotaciones nodales desconocidos
- `F`: vector de cargas nodales equivalentes

Despues de obtener `U`, calcula reacciones y fuerzas internas de los elementos.

## Por que terminar no significa estar correcto

Que OpenSees entregue `0` en `ops.analyze(1)` solo significa que el procedimiento numerico termino. No garantiza que el modelo fisico este bien.

Un modelo puede terminar y aun asi estar mal por:

- Cargas con signo incorrecto
- Unidades mezcladas
- Apoyos mal definidos
- Ejes locales mal orientados
- Secciones con `Iy` e `Iz` invertidos
- Descarga de losa duplicada o incompleta
- Resultados interpretados en global cuando se necesitaban locales

Por eso se hacen verificaciones de cargas, reacciones, desplazamientos y fuerzas internas.
