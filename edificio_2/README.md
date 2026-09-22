# Edificio 2 - Modelo Estructural UANDES

Esta carpeta contiene el modelo trabajado para el edificio 2.

## Contenido

- `modelo_python/geometry_data.py`: geometria parametrica, ejes, niveles, vigas, columnas, muros, diafragmas, apoyos y cargas tributarias.
- `modelo_python/geometry.py`: clases de datos del modelo.
- `modelo_python/build_opensees.py`: crea nodos OpenSees y apoyos empotrados de fundacion.
- `modelo_python/checks.py`: verificaciones geometricas y conservacion de areas/cargas tributarias.
- `modelo_python/export_unity.py`: exporta el modelo a Unity.
- `modelo_python/viewer_2d.py`: viewer 2D HTML.
- `modelo_python/viewer_3d.py`: viewer 3D HTML.
- `modelo_python/main.py`: regenera JSON, viewers y archivo Unity.
- `modelo_python/structural_geometry.json`: salida completa del modelo.
- `modelo_python/outputs/`: viewers HTML generados.
- `unity_visualizador/`: proyecto Unity del edificio 2.

## Criterio Actual

- No se modelan zapatas ni vigas de fundacion.
- La planta de fundacion se considera empotrada.
- No se modelan losas con elementos finitos.
- Los paños se representan como diafragmas rigidos.
- Las cargas gravitacionales se transfieren a vigas mediante areas tributarias explicitas.
- El material estructural es hormigon armado.

## Ejecutar Modelo Python

Desde la raiz del repositorio:

```bat
.venv\Scripts\python.exe "edificio_2\modelo_python\main.py"
```

Si no usas `.venv`:

```bat
python "edificio_2\modelo_python\main.py"
```

## Abrir Viewer HTML

Despues de ejecutar `main.py`:

```text
edificio_2/modelo_python/outputs/structural_3d.html
```

## Abrir Unity

En Unity Hub seleccionar esta carpeta:

```text
edificio_2/unity_visualizador
```

Luego en Unity:

```text
MCOC > Crear Visualizador
Play
```

## Inspeccion En Unity

Al hacer click sobre una viga o columna se muestra:

- `elementTag`;
- seccion;
- material;
- area tributaria;
- cargas `D`, `L`, `U = 1.4D`, `U = 1.2D + 1.6L`;
- carga distribuida equivalente `qU`;
- axial, corte y momento aproximados.

Controles de diagramas:

```text
1 = axial
2 = corte
3 = momento
0 = apagar diagramas
```

## Verificaciones Generadas

El modelo reporta por nivel:

- area total de diafragmas cargados;
- suma de areas tributarias;
- error de conservacion de area;
- carga muerta total `D`;
- sobrecarga total `L`;
- error de conservacion de carga.
