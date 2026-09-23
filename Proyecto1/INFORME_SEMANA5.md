# INFORME SEMANA 5 — Entrega Final Consolidada (P1_G4_Final)

**Grupo 4 — Estructuras de Concreto Reforzado / MCOC**
**Carpeta de entrega final autocontenida: `Proyecto1/`**

> Este informe resume el estado final del proyecto tras la consolidación de las
> 4 entregas semanales. Solo se conserva la última versión en `Proyecto1`
> (unificada), y el repositorio queda autocontenido: **scripts + data + Unity**.

---

## 1. Funciones del proyecto e indicadores (estado actualizado)

La tabla de estado de funciones se mantiene viva en:
- `Proyecto1/README.md` (tabla maestra de funciones/estado)
- `reports/semana05.md` (histórico semanal)

| Componente | Archivo / carpeta | Estado |
|---|---|---|
| Modelo estructural completo (JSON base) | `Proyecto1/data/estructura_completo_unity.json` | OK |
| Carga viva + carga sísmica | `Proyecto1/scripts/carga_viva_sismo.py` | OK |
| Exportación resultados Unity (C1/C2/C3) | `Proyecto1/scripts/exportar_resultados_unity.py` | OK |
| Excel de esfuerzos por elemento | `Proyecto1/scripts/exportar_excel_esfuerzos.py` | OK |
| Verificación de superposición | `Proyecto1/scripts/verificar_superposicion.py` | OK |
| Extracción de indicadores (desplazamientos) | `Proyecto1/scripts/extraer_indicadores.py` | OK |
| Arriostres en voladizos (diagonales Unity) | `Proyecto1/scripts/anadir_arriostres_unity.py` | OK |
| Visualizador Unity (edificio_G4) | `Proyecto1/edificio_G4/` | OK, compila limpio |

**Todas las dependencias quedaron dentro de `Proyecto1/`:** los 6 scripts viven en
`Proyecto1/scripts/` y todos los JSON (base y resultados Unity) en
`Proyecto1/data/`. Ya no se referencia ninguna carpeta P1L*/P1L2 externa.

---

## 2. Modificaciones completas sobre el modelo (este ciclo)

Se realizaron **2 modificaciones completas**, cada una con el flujo
interfaz/dato → modelo → OpenSees → resultados → Unity. Ambas quedan
**reproducibles con un solo comando** porque los scripts ya son autocontenidos.

### Modificación A — Arriostres diagonales en los voladizos (secciones P1L4)

| Etapa | Detalle |
|---|---|
| Interfaz/dato | Se definen 4 parejas de extremos de arriostres (sección 30×45) en `anadir_arriostres_unity.py` |
| Modelo | Se insertan elementos diagonales entre el marco interior y el borde de losa volada |
| OpenSees | Curvas P-M y rigidez regeneradas con `carga_viva_sismo.py` |
| Resultados | `exportar_resultados_unity.py` regenera `estructura_p1l4_unity.json` |
| Unity | Unity recarga el JSON desde `Assets/Resources/` (sin recompilar scripts) |

**Reproducir (autocontenido, 4 comandos):**
```bash
python Proyecto1/scripts/carga_viva_sismo.py --sc-kg-m2 500
python Proyecto1/scripts/anadir_arriostres_unity.py
python Proyecto1/scripts/exportar_resultados_unity.py
python Proyecto1/scripts/exportar_excel_esfuerzos.py
```

Verificado: `edificio_G4` compila en Unity con 0 errores de C#.

### Modificación B — Regeneración de curvas P-M de columna (fC=H-30)

`exportar_resultados_unity.py` recomputa en runtime la curva P-M de la columna
COL70/70 con fibra (comportamiento H-30) y escribe `semana3_resultados_unity.json`
en `Proyecto1/data/`, evitando la inconsistencia histórica con la curva guardada
(fc=25 MPa). `part_e_wall.json` (curva P-M del muro) vive ahora en `Proyecto1/data/`.

---

## 3. Verificación de superposición (interactiva, 3 estados superpuestos)

Script: `Proyecto1/scripts/verificar_superposicion.py`

Al ejecutarse sobre `estructura_p1l4_unity.json` devuelve las **3 posiciones de
reposo** del edificio bajo los 3 estados de carga, que se comparan contra los
numéricos de OpenSees:

| Estado (caso) | Peso | Verificación |
|---|---|---|
| **C1** (G+Q+EX) | 0.76 | superposición OK: desplazamiento máx ≤ tolerancia |
| **C2** (G+Q+EY) | 0.88 | superposición OK |
| **C3** (G+Q+EX+0.3EY) | 0.94 | superposición OK |

Los 3 casos cumplen el criterio de superposición vs el análisis numérico
(OpenSees). La salida interactiva imprime por caso los desplazamientos en los
nodos críticos y el veredicto PASS/FAIL por gap/penetración.

---

## 4. Sidequest: carga móvil (NO implementada en esta entrega)

La carga móvil **no fue implementada** (búsqueda en `.py`/`.cs` con 0 resultados).
Queda documentada como **pendiente** por su impacto en los indicadores y en Unity:

- **Regla física/estructural:** aplicar la carga móvil por fajas de influencia de
  cada viga (equivalentes a franjas tributarias de 1.0 m), combinada en
  posiciones extremas para maximizar M y V (solo *semana tras semana* — definible).
- **Panel Unity:** slider "posición de la carga móvil" que mueve la carga a lo
  largo del claro y actualiza el diagrama de momentos en tiempo real.
- **Reparto:** proporcional a la posición de la carga multiplicada por el factor
  de impacto dinámico (si se modela vehículo con `p1l5`).
- **Conservación:** la suma de reacciones = peso de la carga móvil, repartida por
  equilibrio de cada tramo (verificación automática por nodo).
- **Respuesta visual:** resaltar viga bajo carga y actualizar esfuerzos en el
  `PM/DiagramController`.

**Estado:** pendiente — se documenta para planificación de P1L5.

---

## 5. UX estructural (evaluación del visualizador Unity)

`edificio_G4` (Unity) responde las 6 preguntas de UX estructural:

| Pregunta | Respuesta en la escena |
|---|---|
| **¿Dónde está cada elemento?** | `ElementPicker.cs` permite seleccionar columna/viga/muro y resaltarlo |
| **¿Está apoyado?** | Se muestran los **nodos de apoyo fijo** (base) e indicadores de restricción |
| **¿Qué lo carga/he carga a él?** | Clones por elemento con metadatos (sección, material, cargas puntuales/distribuidas) |
| **¿Cómo se deforma?** | Opciones de visualización por magnitudes (rotaciones `p1l4`), escala de deformada |
| **¿Qué fuerzas hay?** | Diagramas de esfuerzos por elemento (N, Vy, Vz, T, My, Mz) clipables |
| **¿Capacidad?** | Curvas P-M (interacción) por elemento, comparando demanda vs capacidad |

Esta sección detalla la comunicación entre el modelo OpenSees y el Unity:
`exportar_resultados_unity.py` serializa geometría, fuerzas y curvas P-M en
`estructura_p1l4_unity.json`, y los scripts en `Assets/Scripts/` las renderizan.

---
**Estado del repo:** `P1_G4_Final` con `Proyecto1/` autocontenido; entregas
semana 1-3 (P1L1/P1L2/P1L3) y marcos 2D previos ya no se conservan en el repo
final (se consolidaron en `Proyecto1/`).
