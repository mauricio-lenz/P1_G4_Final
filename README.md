# Proyecto MCOC

Codigos en Python para analisis estructural 2D y 3D.

## Estructura

- `semana_pasada_marco_2d/`: trabajo anterior del marco 2D, con reacciones, axial, corte, momento, deformada y diagramas.
- `semana_actual_benchmark_3d/`: entregable actual del benchmark 3D OpenSeesPy con informe, verificacion, defensa e imagen del modelo.
- `semana_actual_benchmark_3d/sap2000_comparacion/`: guia para comparar el benchmark 3D con SAP2000.
- `P1L2/Edificio 1 y 2/`: proyecto de los edificios 1 y 2; contiene el modelo del edificio 1 (pasillos), el modelo estructural base y los archivos de unificación.
- `edificio_2/`: edificio 2 con `modelo_python/` (areas tributarias, cargas D/L, combinaciones) y su `unity_visualizador/` propio.
- `requirements.txt`: dependencias de Python.

## Ejecutar

Marco 2D de la semana pasada:

```bat
python semana_pasada_marco_2d\analisis_marco.py
```

Si `python` no funciona en Windows:

```bat
py semana_pasada_marco_2d\analisis_marco.py
```

Benchmark 3D de esta semana:

```bat
python semana_actual_benchmark_3d\benchmark_3d_opensees.py
```

El benchmark 3D genera `semana_actual_benchmark_3d\benchmark_3d_modelo.png`, `semana_actual_benchmark_3d\resultados_verificacion_3d.md` y muestra desplazamientos, reacciones, equilibrio global y fuerzas internas.

Edificio 2:

```bat
python "edificio_2\modelo_python\main.py"
```

Unity del edificio 2:

```text
edificio_2/unity_visualizador
```

Edificio 1 (analisis de gravedad):

```bat
py "P1L2\Edificio 1 y 2\edificio 1\analisis_gravedad.py"
```

Unity del edificio 1 (genera/Abre `P1L2/Edificio 1 y 2/edificio 1/unity_visualizador`):

```text
P1L2/Edificio 1 y 2/edificio 1/unity_visualizador
```

## Pipeline unificado (P1L4)

Genera el JSON del visualizador Unity con esfuerzos por elemento (con `tag` de OpenSees), combinaciones C1/C2/C3 y curvas P-M H-30:

```bat
python -X utf8 P1L4\exportar_resultados_unity.py
```

Salida: `P1L4/unity_visualizador/Assets/Resources/estructura_p1l4_unity.json` (claves ordenadas) y `P1L2/unity_visualizador/Assets/Resources/semana3_resultados_unity.json`.

Exportar fuerzas internas por elemento a Excel (hoja por caso/combinacion mas resumen de muros):

```bat
python -X utf8 P1L4\exportar_excel_esfuerzos.py
```

Salida: `P1L4/resultados/esfuerzos_por_elemento.xlsx`. Requiere `openpyxl` (ya incluido en `requirements.txt`).

Unity del visualizador unificado:

```text
P1L4/unity_visualizador
```

## Limitaciones conocidas

- El edificio 2 solo se incluye en la geometria unificada (nodulos de `estructura_completo_unity.json`); su analisis estructural fisico no esta modelado en la etapa P1L4, por lo que los resultados de esfuerzos, desplazamientos y muros corresponden al edificio 1.
- Los muros se representan como muros equivalentes (seccion banda H-30) con demandas estimadas por reparto sismico proporcional a `t*L`; el momento vuelvo/corte fuera de plano se desprecia.
- Modulos de elasticidad secantes: el modelo usa valores de material por etapa (p. ej. `E_CONCRETE = 25 GPa`) como simplificacion documentada; las curvas P-M usan H-30 (`fc = 30 MPa`, `fy = 420 MPa`).

## Entrega Canvas

- Repositorio: `https://github.com/mauricio-lenz/P1_G4_Final`
- Informe Markdown: `semana_actual_benchmark_3d/LAB_semana1_benchmark_3D.md`
- Archivo de verificacion: `semana_actual_benchmark_3d/resultados_verificacion_3d.md`
- Guia de defensa: `semana_actual_benchmark_3d/DEFENSA_individual_3D.md`

## Instalar dependencias

```bat
pip install -r requirements.txt
```
