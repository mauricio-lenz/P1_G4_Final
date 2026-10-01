# Proyecto1 — Visualizador Unity con resultados OpenSees y P-M interactivo (autocontenido)

Proyecto final MCOC (Semana 5) que implementa el visualizador 3D mejorado en
Unity con OpenSees como backend. **Esta carpeta es autocontenida**: scripts,
datos, resultados y proyecto Unity están todos dentro de `Proyecto1/`, sin
dependencias a directorios externos (`P1L1`, `P1L2`, `P1L3` ya no se usan —
fueron movidos/borrados de la raíz).

## Qué incluye

| Componente | Ubicación | Descripción |
|---|---|---|
| Scripts de pipeline | `scripts/` | Modelo y cargas, exportador a Unity, ajustes según planos, verificación de superposición, indicadores, modificación del modelo, quitar elemento, carga móvil, carga en elemento, Excel |
| Datos base (OpenSees) | `data/` | `estructura_completo_unity.json` (modelo vigente), `estructura_completo_unity.pre_planos.json` (respaldo base de `ajustar_modelo_planos.py`), `part_e_wall.json` (curva P-M muro) |
| Resultados Unity | `data/semana3_resultados_unity.json` | Curva P-M de columna (COL70/70_FIBER) + demandas por combo |
| Proyecto Unity viewer | `edificio_G4/` | Visualizador 3D en Unity; JSON en `Assets/Resources/` |
| Resultados exportados | `resultados/` | `esfuerzos_por_elemento.xlsx` (esfuerzos por elemento a Excel) |
| Informes / entregables | `../reports/semana06.md` (vigente, AR), `../reports/semana05.md`, `ENTREGA_SEMANA4_CHECKLIST.md` | Informes de las semanas 6 y 5 + rúbrica de la semana 4 |

## Funcionalidades (tabla de estado)

| # | Función | Estado |
|---|---|---|
| 1 | Mostrar estructura 3D completa (edificio 1 + 2, G35 + perfiles A36) | Implementada |
| 2 | Selección de elemento (columna/viga/muro): ID, nodos, sección, material, eje local, restricciones | Implementada |
| 3 | Apoyos visibles (34 apoyos, objetos 3D) | Implementada |
| 4 | Toggle cargas (D, L, combinaciones; flechas por losa) | Implementada |
| 5 | Toggle deformada (escala relativa a altura) | Implementada |
| 6 | Diagramas axial/corte/momento por elemento | Implementada |
| 7 | Curva P-M de columna + muro (demanda vs capacidad) | Implementada |
| 8 | Superposición (verificar: C1/C2/C3 vs OpenSees) | Verificada numéricamente (error 1e-11) |
| 9 | Sidequest carga móvil | Implementada (P editable, 5 pisos × 2 edificios, conservación ΣRz = P) |
| 10 | Modificación del modelo desde Unity (quitar elemento + reanálisis) | Implementada |
| 11 | Carga puntual/distribuida en un elemento elegido | Implementada |
| 12 | Autocontenido (scripts+datos+Unity en una carpeta) | Implementada en Proyecto1/ |

## Ejecutar (desde la raíz del repo)

```bat
cd Proyecto1
python -X utf8 scripts\ajustar_modelo_planos.py      & rem reconstruye el modelo segun los planos y re-exporta
python -X utf8 scripts\exportar_resultados_unity.py  & rem solo re-exporta a Unity
```

Regenera:
- `Proyecto1/data/semana3_resultados_unity.json` (curva P-M columna G35).
- `Proyecto1/edificio_G4/Assets/Resources/estructura_p1l4_unity.json`
  (JSON enriquecido para el viewer Unity).

Exportar esfuerzos a Excel:

```bat
python -X utf8 scripts\exportar_excel_esfuerzos.py
```

Genera `Proyecto1/resultados/esfuerzos_por_elemento.xlsx`.

Verificar superposición (OpenSees ↔ combinaciones C1/C2/C3):

```bat
python -X utf8 scripts\verificar_superposicion.py
```

Abrir Unity (visualizador):

```text
Proyecto1/edificio_G4   (escena StructureViewerScene; carga estructura_p1l4_unity.json al correr)
```

## Notas de autocontención

- Todos los scripts importan solo desde `Proyecto1/scripts/` (peer) y `Proyecto1/data/` (JSON); no hay referencias a `P1L1/P1L2/P1L3`.
- Los `requirements.txt` de la semana incluyen `openseespy` + `openpyxl`.
- El proyecto Unity del viewer se mantiene en `edificio_G4/` (carpeta completa con `Assets/Resources/estructura_p1l4_unity.json` listo).
