# Semana 1 - LAB: benchmark 3D OpenSees

## Objetivo

Construir y verificar un caso estructural 3D en OpenSeesPy. El modelo corresponde a un marco tridimensional de un vano en direccion X y un vano en direccion Y, con una losa descargada como carga lineal sobre las vigas perimetrales.

## Unidades

- Longitud: m
- Fuerza: kN
- Momento: kN*m
- Esfuerzo: kN/m2

## Geometria

- Vano en X: 6.0 m
- Vano en Y: 5.0 m
- Altura de piso: 3.2 m
- Nodos inferiores: 1, 2, 3, 4
- Nodos superiores: 5, 6, 7, 8
- Columnas: 1-5, 2-6, 3-7, 4-8
- Vigas superiores: 5-6, 6-7, 8-7, 5-8

## Material

Se considera acero ASTM A36 aproximado:

- Modulo de elasticidad: E = 200e6 kN/m2
- Coeficiente de Poisson: nu = 0.30
- Modulo de corte: G = E / [2(1 + nu)]

## Secciones

Columnas:

- Perfil tubular cuadrado 30 cm x 30 cm x 1.2 cm

Vigas:

- Seccion rectangular 25 cm x 40 cm

## Apoyos

Los apoyos se definen individualmente en el diccionario `supports` del script `benchmark_3d_opensees.py`. Por defecto, los cuatro nodos de base se consideran empotrados:

- Ux = 0
- Uy = 0
- Uz = 0
- Rx = 0
- Ry = 0
- Rz = 0

El orden usado en el codigo es `(Ux, Uy, Uz, Rx, Ry, Rz)`, donde `1` significa restringido y `0` significa libre.

## Cargas

La losa se modela como carga superficial uniforme:

- q_losa = 6.0 kN/m2

La losa se descarga de forma aproximada sobre las cuatro vigas perimetrales. Se reparte la carga para que la carga lineal total sea igual a `q_losa * Lx * Ly`.

- Vigas paralelas a X: w = q_losa * Ly / 4 = 7.5 kN/m
- Vigas paralelas a Y: w = q_losa * Lx / 4 = 9.0 kN/m
- Carga vertical total: 180 kN

## Verificacion

El script revisa:

- Resultado del analisis estatico lineal
- Desplazamientos nodales superiores
- Reacciones en bases
- Equilibrio global en X, Y y Z
- Fuerzas internas de cada elemento
- Comparacion con valores de referencia en `resultados_verificacion_3d.md`
- Comparacion externa propuesta en SAP2000 usando `sap2000_comparacion/README_SAP2000.md`

Para ejecutar:

```bat
python benchmark_3d_opensees.py
```

El script genera la figura:

- `benchmark_3d_modelo.png`
- `diagrama_3d_axial.png`
- `diagrama_3d_corte.png`
- `diagrama_3d_momento.png`

Tambien genera el archivo:

- `resultados_verificacion_3d.md`

## Archivos del entregable

- Modelo OpenSeesPy: `benchmark_3d_opensees.py`
- Script reproducible: `benchmark_3d_opensees.py`
- Extraccion de desplazamientos: impresa en consola y documentada en `resultados_verificacion_3d.md`
- Reacciones: impresas en consola y usadas para equilibrio global
- Fuerzas de elementos: impresas como `localForces`
- Visualizacion de geometria y ejes: `benchmark_3d_modelo.png`
- Diagramas de axial, corte y momento: `diagrama_3d_axial.png`, `diagrama_3d_corte.png`, `diagrama_3d_momento.png`
- Archivo de resultados de verificacion: `resultados_verificacion_3d.md`
- Guia de defensa individual: `DEFENSA_individual_3D.md`
- Guia comparacion SAP2000: `sap2000_comparacion/README_SAP2000.md`

## Visualizador Unity

Se agrego una base para visualizar la estructura en Unity:

- Datos exportados: `estructura_3d_unity.json`
- Scripts Unity: `../unity_visualizador/Assets/Scripts/`
- Instrucciones: `../unity_visualizador/README_Unity.md`

El visualizador permite tocar o hacer click sobre una barra para mostrar axial, corte local `Vz` y momento local `My` del elemento.
