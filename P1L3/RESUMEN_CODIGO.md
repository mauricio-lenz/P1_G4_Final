# Resumen del codigo - Semana 3

Este documento explica como esta organizado el codigo de la Semana 3 y donde mirar cada calculo importante.

## Archivo principal

El archivo principal es:

```text
P1L3/carga_viva_sismo.py
```

Se corre desde la raiz del repositorio con:

```powershell
.\.venv\Scripts\python.exe "P1L3\carga_viva_sismo.py"
```

Ese comando abre un menu interactivo con las partes A, B, C y D.

## Flujo general

El codigo lee el modelo completo desde:

```text
P1L2/unity_visualizador/Assets/Resources/estructura_completo_unity.json
```

Luego genera resultados en:

```text
P1L3/resultados/carga_viva_sismo.json
```

El flujo principal esta al final del archivo, en la funcion:

```python
main()
```

El menu interactivo esta en:

```python
interactive_menu()
```

## Parte A - Carga viva Q

La funcion principal es:

```python
transfer_live_load(data, q_q)
```

Calcula la carga viva sobre cada viga usando:

```text
Q_viga = q_Q * area_tributaria
```

Luego reparte esa carga a los dos nodos de la viga:

```text
Fz_nodeI = -Q_viga / 2
Fz_nodeJ = -Q_viga / 2
```

El signo negativo significa carga vertical hacia abajo.

La verificacion global es:

```text
sum(Q transferida) = q_Q * A_total
```

Campos importantes en el JSON:

```text
parte_A_carga_viva_Q.area_total_m2
parte_A_carga_viva_Q.Q_transferida_kN
parte_A_carga_viva_Q.q_Q_por_A_kN
parte_A_carga_viva_Q.error_conservacion_kN
parte_A_carga_viva_Q.vigas
parte_A_carga_viva_Q.cargas_nodales_Q
```

## Consultas por viga o losa

Las funciones son:

```python
query_beam(live_transfer, wanted_id)
query_slab(data, q_q, wanted_id)
query_item(data, live_transfer, q_q, wanted_id)
```

Para una viga, se puede buscar por ID numerico o por `elementTag`, por ejemplo:

```text
359
B3002_V60/80
```

Para una losa, se usa el ID de losa, por ejemplo:

```text
L1
D101
```

## Parte B - Sismo pseudoestatico EX/EY

La funcion principal es:

```python
build_seismic_cases(data, live_transfer, seismic_coeff)
```

Calcula el peso sismico por piso con:

```text
W_sismico = D + 0.5Q
```

Luego calcula la fuerza lateral por piso:

```text
F_piso = coef_sismo * W_sismico
```

Por defecto:

```text
coef_sismo = 0.20
```

El codigo agrupa cotas cercanas porque los dos edificios unidos tienen niveles levemente distintos. La tolerancia esta definida como:

```python
FLOOR_GROUP_TOL_M = 0.25
```

Eso evita que `z = 4.000 m` y `z = 4.120 m` aparezcan como pisos distintos.

Campos importantes en el JSON:

```text
parte_B_sismo_pseudoestatico.pisos
parte_B_sismo_pseudoestatico.carga_lateral_total_EX_kN
parte_B_sismo_pseudoestatico.carga_lateral_total_EY_kN
parte_B_sismo_pseudoestatico.corte_basal_EX_kN
parte_B_sismo_pseudoestatico.corte_basal_EY_kN
parte_B_sismo_pseudoestatico.cargas_nodales_EX
parte_B_sismo_pseudoestatico.cargas_nodales_EY
```

## Parte C - Superposicion

La funcion principal es:

```python
superposition_check(data, live_transfer, seismic, lambdas)
```

Construye la combinacion:

```text
R = lambda_G G + lambda_Q Q + lambda_EX EX + lambda_EY EY
```

Por defecto usa:

```text
lambda_G  = 1.0
lambda_Q  = 0.5
lambda_EX = 1.0
lambda_EY = 0.3
```

Primero corre cada caso separado en OpenSees:

```text
G
Q
EX
EY
```

Luego suma los resultados por superposicion y los compara contra una corrida explicita equivalente de OpenSees.

La funcion que arma el modelo OpenSees es:

```python
build_model(data)
```

La funcion que aplica cargas y analiza es:

```python
analyze_case(data, nodal_loads, control_node, element_id)
```

La linea donde OpenSees entrega fuerzas internas es:

```python
element_force = ops.eleForce(element_id)
```

Se verifica:

```text
desplazamiento del nodo de control
reacciones globales
fuerzas internas del elemento de control
```

Campos importantes en el JSON:

```text
parte_C_superposicion.lambdas
parte_C_superposicion.case_results
parte_C_superposicion.superposed_prediction
parte_C_superposicion.explicit_combination
parte_C_superposicion.errors
```

## Parte D - Capacidad HA Fiber Section

La funcion principal es:

```python
fiber_section_capacity()
```

La seccion estudiada es una columna:

```text
COL70/70_FIBER
b = 700 mm
h = 700 mm
```

El refuerzo usado es:

```text
3 barras inferiores + 2 barras centrales + 3 barras superiores
8 barras totales de diametro 25 mm
As por barra = 490.9 mm2
Ast total = 3927.0 mm2
```

La configuracion se cambia al inicio de `carga_viva_sismo.py`:

```python
BAR_DIAMETER_MM = 25.0
REBAR_BARS_INFERIOR = 3
REBAR_BARS_CENTRO = 2
REBAR_BARS_SUPERIOR = 3
CONCRETE_FIBERS_X = 20
CONCRETE_FIBERS_Y = 20
```

Si quieres, por ejemplo, 4 barras abajo, 2 al centro y 4 arriba, solo cambias:

```python
REBAR_BARS_INFERIOR = 4
REBAR_BARS_CENTRO = 2
REBAR_BARS_SUPERIOR = 4
```

El codigo reparte automaticamente las barras de cada fila entre ambos bordes laterales de la columna. Ya no hay que editar coordenadas manualmente.

La discretizacion de fibras se crea en:

```python
make_column_fibers()
```

Se usan:

```text
20 x 20 = 400 fibras de hormigon
8 fibras de acero, una por barra
```

Cada fibra de hormigon representa un pedazo de la seccion. Como la columna mide `700 mm x 700 mm`, cada fibra de hormigon mide aproximadamente:

```text
35 mm x 35 mm
```

La respuesta de la seccion se calcula en:

```python
section_response(section, eps0, phi)
```

Para cada fibra calcula:

```text
deformacion
tension
fuerza
momento
```

Luego suma todas las fibras para obtener:

```text
P total
M total
```

## Curva momento-curvatura M-phi

La curva M-phi se calcula dentro de:

```python
fiber_section_capacity()
```

El rango de curvatura actual es:

```text
phi = 0.00010 a 0.08000 1/m
```

El codigo detecta la primera fluencia del acero usando:

```text
eps_y = fy / Es
```

Con los valores actuales:

```text
eps_y = 0.002100
phi_y = 0.004200 1/m
M_y = 425.871 kN*m
```

El grafico se genera en:

```python
plot_capacity(capacity)
```

Archivo generado:

```text
P1L3/resultados/M_phi_COL70_70.png
```

## Diagrama de interaccion P-M

Los puntos P-M se calculan con el metodo manual simplificado en:

```python
simplified_pm_points(section, po_kN)
```

Los cinco estados usados son:

```text
A) Compresion pura
B) Balance
C) Ultima falla ductil
D) Flexion pura
E) Traccion pura
```

Los puntos actuales son:

```text
A) Compresion pura:      Pn = 11978.388 kN, Mn =    0.000 kN*m, phi = 0.65
B) Balance:              Pn =  5020.930 kN, Mn = 1270.813 kN*m, phi = 0.65
C) Ultima falla ductil:  Pn =  2825.149 kN, Mn = 1130.504 kN*m, phi = 0.90
D) Flexion pura:         Pn =     0.000 kN, Mn =  513.175 kN*m, phi = 0.90
E) Traccion pura:        Pn = -1649.336 kN, Mn =    0.000 kN*m, phi = 0.90
```

El grafico se genera en:

```text
P1L3/resultados/P_M_COL70_70.png
```

## Unity

El proyecto Unity correcto es:

```text
P1L2/unity_visualizador
```

Los scripts importantes son:

```text
P1L2/unity_visualizador/Assets/Scripts/DiagramController.cs
P1L2/unity_visualizador/Assets/Scripts/ElementPicker.cs
P1L2/unity_visualizador/Assets/Scripts/ElementSelectable.cs
```

Los diagramas axial, corte y momento se muestran en:

```text
DiagramController.cs
```

La funcion clave es:

```csharp
GetValue(ElementData data, DiagramMode mode, float t, float length)
```

Usa estos campos del JSON:

```text
axialI, axialJ
shearI, shearJ
momentI, momentJ
uniformLoad
```

El archivo que Unity usa para la curva P-M de Semana 3 es:

```text
P1L2/unity_visualizador/Assets/Resources/semana3_resultados_unity.json
```

En Unity:

```text
1 = diagrama axial
2 = diagrama de corte
3 = diagrama de momento
4 = curva P-M HA
0 = ocultar diagramas
```

## Resultados principales

Los resultados principales quedan en:

```text
P1L3/resultados
```

Archivos relevantes:

```text
carga_viva_sismo.json
fiber_COL70_70.png
M_phi_COL70_70.png
P_M_COL70_70.png
```
