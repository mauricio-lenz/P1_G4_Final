# P1L3 — Carga viva, sismo, superposicion y capacidad HA

## Objetivo

Construir los casos base para la interaccion posterior del modelo completo y comenzar la validacion de capacidad de hormigon armado.

El script principal reutiliza el JSON del edificio completo:

```text
P1L2/unity_visualizador/Assets/Resources/estructura_completo_unity.json
```

## Ejecucion

Desde la raiz del repo:

La forma mas facil para Windows es ejecutar este archivo que esta en la raiz del repositorio:

```text
EJECUTAR_SEMANA3.bat
```

Si el repositorio esta descargado en `Descargas`, se puede abrir con `Windows + R` pegando una ruta como esta:

```text
%USERPROFILE%\Downloads\Trabajo-MCOC\EJECUTAR_SEMANA3.bat
```

Si se descargo como ZIP desde GitHub, normalmente la carpeta se llama `Trabajo-MCOC-main`:

```text
%USERPROFILE%\Downloads\Trabajo-MCOC-main\EJECUTAR_SEMANA3.bat
```

Si esta en el Escritorio:

```text
%USERPROFILE%\Desktop\Trabajo-MCOC\EJECUTAR_SEMANA3.bat
```

Ese archivo abre PowerShell con `-NoExit`, crea `.venv`, instala `openseespy` y `matplotlib`, y abre el menu de Semana 3.
Al cerrar el menu, la consola queda abierta para poder leer resultados o errores.

Importante: `%USERPROFILE%` es para pegarlo en `Windows + R`. Si se escribe dentro de PowerShell, se debe usar `$env:USERPROFILE` o la ruta completa.

Tambien se puede ejecutar manualmente con PowerShell:

```powershell
& ".venv\Scripts\python.exe" "P1L3\semana3.py"
```

Para trabajar paso a paso solo la carga viva `Q` y el sismo pseudoestatico `EX/EY`:

```powershell
& ".venv\Scripts\python.exe" "P1L3\carga_viva_sismo.py" --sc-kg-m2 500
```

La forma mas simple es abrir el menu interactivo:

```powershell
& ".venv\Scripts\python.exe" "P1L3\carga_viva_sismo.py"
```

Tambien se puede abrir con doble click en:

```text
P1L3/abrir_menu.bat
```

El menu enumera que resultados se pueden pedir y avisa si necesita ID o no:

```text
1. Resumen global Q + sismo              (sin ID)
2. Area tributaria y Q de una viga       (con ID de viga)
3. Area y Q superficial de una losa      (con ID de losa)
4. Sismo EX/EY por piso                  (sin ID)
5. Superposicion R y verificacion        (sin ID, pide lambdas)
6. Capacidad HA Fiber Section            (sin ID)
7. Ejemplos de IDs disponibles           (sin ID)
8. Ruta del JSON completo de resultados  (sin ID)
```

La Parte C tambien se puede correr directamente con la combinacion por defecto:

```powershell
& ".venv\Scripts\python.exe" "P1L3\carga_viva_sismo.py" --sc-kg-m2 500 --superposicion
```

O cambiando los coeficientes de la combinacion:

```powershell
& ".venv\Scripts\python.exe" "P1L3\carga_viva_sismo.py" --sc-kg-m2 500 --superposicion --lambdaG 1.0 --lambdaQ 0.5 --lambdaEX 1.0 --lambdaEY 0.3
```

La Parte D se puede correr directamente con:

```powershell
& ".venv\Scripts\python.exe" "P1L3\carga_viva_sismo.py" --capacidad-ha
```

Al correr la Parte D tambien se exporta para Unity:

```text
P1L2/unity_visualizador/Assets/Resources/semana3_resultados_unity.json
```

En Unity:

```text
Proyecto correcto: P1L2/unity_visualizador
1 = diagrama axial
2 = diagrama de corte
3 = diagrama de momento
4 = primeros puntos de curva P-M HA
0 = ocultar diagramas
```

Para ubicar la carpeta correcta en Windows se puede ejecutar desde la raiz:

```text
ABRIR_UNITY_SEMANA3.bat
```

No abrir la carpeta vieja `edificio completo/unity_visualizador`, porque despues de reorganizar el repositorio el visualizador correcto quedo en `P1L2/unity_visualizador`.

Consulta puntual de una viga:

```powershell
& ".venv\Scripts\python.exe" "P1L3\carga_viva_sismo.py" --sc-kg-m2 500 --id B3002_V60/80
```

Consulta puntual de una losa:

```powershell
& ".venv\Scripts\python.exe" "P1L3\carga_viva_sismo.py" --sc-kg-m2 500 --id L1
```

Salidas:

```text
P1L3/resultados/resultados_semana3.json
P1L3/resultados/carga_viva_sismo.json
P1L3/resultados/fiber_COL70_70.png
P1L3/resultados/M_phi_COL70_70.png
P1L3/resultados/P_M_COL70_70.png
```

## Parte A - Carga Viva

Se usa la misma geometria tributaria de Semana 2, leyendo `liveLoad` y `areaTributaria` desde el JSON completo.

Verificacion obtenida:

```text
Area tributaria total = 4005.876 m2
Q transferida = 16809.851 kN
q_Q equivalente = 4.196 kN/m2
q_Q * A = 16809.851 kN
Error = 0.000000 kN
```

Nota: `q_Q` no es unico en todo el edificio porque hay perfiles distintos por nivel. Por eso se reporta un `q_Q equivalente` global y un rango de intensidades por viga.

## Parte B - Sismo Pseudoestatico

Se generan dos casos independientes:

```text
EX: fuerza lateral en X
EY: fuerza lateral en Y
```

Supuesto de masa:

```text
W_piso = D_piso + 0.5 L_piso
F_sismo_piso = 0.20 * W_piso
```

Resultado global:

```text
Corte basal EX = 6560.582 kN
Corte basal EY = 6560.582 kN
```

El JSON de resultados guarda por piso:

```text
D_piso
L_piso
masa equivalente
centro de masa estimado
nodo de aplicacion
torsion estimada respecto del CM
```

## Parte C - Superposicion

Casos base:

```text
G
Q
EX
EY
```

Combinacion arbitraria usada:

```text
R = 1.0 G + 0.5 Q + 1.0 EX + 0.3 EY
```

Se compara contra una corrida explicita equivalente en OpenSees.

Verificacion obtenida con `SC = 500 kg/m2`:

```text
desplazamiento max |OpenSees explicito - superposicion| = 1.401e-11 m
reaccion max       |OpenSees explicito - superposicion| = 3.633e-10 kN
fuerza interna max |OpenSees explicito - superposicion| = 2.871e-12
```

Errores de verificacion obtenidos son numericos de orden maquina:

```text
desplazamiento: ~1e-12 m
reaccion: ~1e-10 kN
fuerza interna: ~1e-12 kN
```

Esto confirma que el modelo lineal cumple superposicion para los casos construidos.

## Parte D - Capacidad HA

Se construye una seccion `Fiber` de columna:

```text
COL70/70_FIBER (H-25)
b = 0.70 m
h = 0.70 m
fc' = 25 MPa
fy = 420 MPa
400 fibras de hormigon
3 barras inferiores + 2 centrales + 3 superiores
Diametro de barra = 25 mm
```

La armadura se modifica al inicio de `carga_viva_sismo.py`:

```python
BAR_DIAMETER_MM = 25.0
REBAR_BARS_INFERIOR = 3
REBAR_BARS_CENTRO = 2
REBAR_BARS_SUPERIOR = 3
CONCRETE_FIBERS_X = 20
CONCRETE_FIBERS_Y = 20
```

Ademas se declara una `ops.section("Fiber", ...)` en OpenSees con:

```text
Concrete01
Steel01
patch rect 20x20
layer straight usando la cantidad de barras configurada por fila
```

Graficos generados:

```text
fiber_COL70_70.png: discretizacion de fibras y barras
M_phi_COL70_70.png: curva momento-curvatura aproximada
P_M_COL70_70.png: primeros puntos de interaccion P-M
```

Resultados principales obtenidos:

```text
Seccion: COL70/70_FIBER
b x h = 0.70 x 0.70 m
b x h = 700 x 700 mm
Hormigon: Concrete01, fc' = 25 MPa (H-25)
Acero: Steel01, fy = 420 MPa, Es = 200000 MPa
Fibras de hormigon = 400 (20 x 20)
Refuerzo = 8 barras de diametro 25 mm (3 inferior, 2 centro, 3 superior)
Area por barra = 0.000491 m2
Area por barra = 490.9 mm2
Ast = 0.003927 m2
Ast = 3927.0 mm2
Ag = 490000 mm2
Cuantia = 0.801 %
Po aproximado = 11978.388 kN
```

Puntos P-M reportados (metodo manual simplificado, f'c = 25 MPa):

```text
A) Compresion pura: Pn = 11978.388 kN, Mn = 0.000 kN*m
B) Balance: Pn = 5020.930 kN, Mn = 1270.813 kN*m
C) Ultima falla ductil: Pn = 2825.149 kN, Mn = 1130.504 kN*m
D) Flexion pura: Pn = 0.000 kN, Mn = 513.175 kN*m
E) Traccion pura: Pn = -1649.336 kN, Mn = 0.000 kN*m
P =  8426.519 kN, M = 1375.427 kN*m
P = 14044.198 kN, M =  33.296 kN*m
```

Puntos P-M simplificados (metodo nominal, bloque de tensiones):

```text
A) Compresion pura:      Pn = 14044.198 kN, Mn =    0.000 kN*m, phi = 0.65
B) Balance:              Pn =  6007.143 kN, Mn = 1452.523 kN*m, phi = 0.65
C) Ultima falla ductil:  Pn =  3441.532 kN, Mn = 1282.384 kN*m, phi = 0.90
D) Flexion pura:         Pn =     0.000 kN, Mn =  517.113 kN*m, phi = 0.90
E) Traccion pura:        Pn = -1649.336 kN, Mn =    0.000 kN*m, phi = 0.90
```

La curva M-phi se extendio hasta `phi = 0.080 1/m`. La primera fluencia del acero aparece aproximadamente en:

```text
eps_y = fy / Es = 0.002100
phi_y = 0.004200 1/m
M_y = 425.871 kN*m
```

Interpretacion inicial:

```text
Al aumentar la compresion axial P, aumenta inicialmente la capacidad a momento por mayor bloque comprimido. Al acercarse a Po, la capacidad a momento tiende a bajar hacia cero.
```

## Nota De Modelo

Para estabilizar corridas lineales en OpenSees, el script fija nodos auxiliares aislados y ancla componentes desconectadas sin apoyo. Esos nodos provienen principalmente de paneles de losa/diafragma visuales del JSON completo y no modifican la transferencia tributaria usada para G/Q.
