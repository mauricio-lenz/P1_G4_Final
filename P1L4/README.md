# P1L4 — Visualizador Unity con resultados OpenSees y P-M interactivo

Etapa del proyecto MCOC que implementa el visualizador 3D mejorado en Unity con:

- Resultados de análisis estático lineal (desplazamientos y fuerzas internas por combinación de carga).
- Selector de combinaciones NCh433 (C1, C2, C3).
- Diagramas de fuerza (axial, corte, momento) con datos reales de OpenSees.
- Modo deformada con desplazamientos escalados.
- Panel de información completo por elemento (sección, material, restricciones, fuerzas, trazabilidad).
- Diagrama P-M interactivo de capacidad HA para columnas y muros (punto de demanda por combo).

## Estructura

- `exportar_resultados_unity.py` — Exportador Python que genera el JSON enriquecido desde OpenSeesPy (requiere venv con `openseespy`).
- `unity_visualizador/` — Proyecto Unity completo, autocontenido. Ver `unity_visualizador/README_Unity.md` para instrucciones de uso.

## Generar datos

```bat
.venv\Scripts\python.exe -X utf8 P1L4\exportar_resultados_unity.py
```

## Abrir en Unity

Copiar `unity_visualizador/` como proyecto Unity, crear escena, y usar el menú **MCOC → Crear Visualizador**.
