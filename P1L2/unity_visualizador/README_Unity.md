# Visualizador Unity - Estructura 3D

Este visualizador permite cargar la estructura 3D exportada desde OpenSeesPy y tocar/clickear una barra para ver:

- Axial `N`
- Corte local `Vz`
- Momento local `My`

Los apoyos se dibujan automaticamente segun el diccionario `supports` de `benchmark_3d_opensees.py`: empotrado, pasador, apoyo vertical, rodillo en X, rodillo en Y o personalizado.

## 1. Generar datos desde Python

Desde la raiz del repositorio:

```bat
.venv\Scripts\python semana_actual_benchmark_3d\benchmark_3d_opensees.py
```

Esto genera:

```text
semana_actual_benchmark_3d\estructura_3d_unity.json
```

Si cambias cargas en `benchmark_3d_opensees.py`, debes guardar el archivo y volver a correr este comando para que Unity reciba los datos nuevos.

## 2. Crear proyecto Unity

1. Abrir Unity Hub.
2. Crear un proyecto `3D Core`.
3. Copiar la carpeta `unity_visualizador/Assets/Scripts` dentro de `Assets/Scripts` del proyecto Unity.
4. Copiar `semana_actual_benchmark_3d/estructura_3d_unity.json` dentro de `Assets/Resources` o directamente dentro de `Assets`.

## 3. Configurar escena

1. Crear un objeto vacio llamado `StructureViewer`.
2. Agregarle el componente `StructureViewer`.
3. Arrastrar `estructura_3d_unity.json` al campo `Structure Json`.
4. Crear tres materiales y asignarlos a `Beam Material`, `Column Material` y `Support Material`.
5. Agregar el componente `ElementPicker` a la camara principal.
6. Opcional: agregar `OrbitCamera` a la camara principal para rotar con click derecho y hacer zoom con la rueda.
7. Presionar Play.

## 4. Uso

Al hacer click o tocar una barra, aparece un cuadro con los resultados interpolados en esa posicion del elemento.

Teclas para diagramas:

- `0`: ocultar diagramas.
- `1`: mostrar axial `N`.
- `2`: mostrar corte `Vz`.
- `3`: mostrar momento `My` en vigas.

Formato usado:

- `N`: fuerza axial local del elemento.
- `Vz`: corte local vertical usado para la carga de losa.
- `My`: momento local asociado a la flexion vertical de las vigas.

El diagrama de momento del visualizador Unity se muestra parabolico en las vigas y normalizado para que sea legible en 3D. Los diagramas completos generados con Python estan en `semana_actual_benchmark_3d`.

## Nota

El visualizador muestra una interpolacion lineal entre valores de extremo. Es suficiente para una demostracion interactiva del laboratorio, pero no reemplaza los diagramas completos calculados en OpenSeesPy.
