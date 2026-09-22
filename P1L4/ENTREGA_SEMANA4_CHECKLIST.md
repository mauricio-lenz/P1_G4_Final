# Semana 4 - Checklist De Entrega Unity

## Objetivo

Unity funciona como postprocesador estructural conectado a resultados OpenSees ya exportados en:

```text
P1L4/unity_visualizador/Assets/Resources/estructura_p1l4_unity.json
```

## Datos Verificados

```text
Nodos: 553
Elementos: 462
Columnas: 129
Vigas: 333
Muros equivalentes: 75
Apoyos: 30
Losas/slabs: 226
Combinaciones: C1, C2, C3
Registros de desplazamiento: 1659
Registros de fuerzas internas: 1386
Curvas P-M: COL70/70_FIBER y W_DPRIME_OPENING_TO_3
Muros con demanda P-M: 75/75
```

## Seleccion De Elementos

Al seleccionar columnas, vigas o muros se muestra:

```text
ID
nodos
seccion
material
ejes locales X', Y', Z'
condiciones/restricciones relevantes
N
Vy/Vz
T
My/Mz
trazabilidad OpenSees/JSON -> Unity -> resultados -> seccion/capacidad
```

## Visualizaciones

Unity incluye:

```text
deformada: tecla/boton 5
diagrama axial: tecla/boton 1
diagrama corte: tecla/boton 2
diagrama momento: tecla/boton 3
areas tributarias: panel de informacion y resumen tributario
cargas: D, L, combinaciones y cargas distribuidas en vigas
apoyos: objetos visibles y restricciones en panel de seleccion
```

## Demanda-Capacidad

Para columnas:

```text
curva P-M: COL70/70_FIBER
punto de demanda: desde fuerzas internas OpenSees del combo activo
combo activo identificado: C1/C2/C3 con expresion completa
```

Para muros:

```text
curva P-M: W_DPRIME_OPENING_TO_3
punto de demanda: propio de cada muro y combo activo
combo activo identificado: C1/C2/C3 con expresion completa
```

Combinaciones disponibles:

```text
C1: G+0.5Q+0.3EX+0.2EY
C2: G+0.5Q+0.3EX-0.2EY
C3: G+0.5Q-0.3EX+0.2EY
```

## Como Ejecutar

Regenerar datos:

```powershell
cd "C:\Users\segui\OneDrive\Desktop\proyecto MCOC"
.\.venv\Scripts\python.exe -X utf8 P1L4\exportar_resultados_unity.py
```

Abrir Unity:

```text
C:\Users\segui\OneDrive\Desktop\proyecto MCOC\P1L4\unity_visualizador
```
