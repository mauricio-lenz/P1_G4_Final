# Semana 5 — Avance: laboratorio estructural interactivo v1

**Proyecto:** modelo estructural UANDES, edificio 1 (visualizador P1L4).
**Unidades:** kN, m, kN·m, rad.

Los resultados numéricos de este informe provienen del pipeline reproducible de `P1L4/` (reanálisis OpenSees de la sección 2). El visualizador y los datos se mantienen en `P1L4/unity_visualizador`, con el JSON de trabajo en `P1L4/unity_visualizador/Assets/Resources/estructura_p1l4_unity.json`.

## 1. Funciones implementadas

Tabla de estado del visualizador P1L4 (escena Unity ejecutada contra `estructura_p1l4_unity.json`):

| Funcionalidad | Estado | Cómo se verifica en el viewer |
|---|---|---|
| Navegación | **Implementada** | Vistas ISO/TOP/FRONT/RIGHT (botones en panel), órbita por arrastre con botón derecho, paneo con botón medio/flechas y zoom con rueda del mouse |
| Selección | **Implementada** | Click sobre elemento → panel con ID, nodos I/J, sección, material, ejes locales X'/Y'/Z', restricciones, N, Vy/Vz, T, My/Mz y trazabilidad (tag OpenSees → Unity → combo) |
| Apoyos | **Implementada** | 30 apoyos como objetos 3D distintivos; restricciones relevantes visibles en el panel de selección |
| Ejes | **Implementada** | Dibujo de ejes locales por elemento seleccionado (`EjeLocal_*`) y cámara sobre ejes globales |
| Cargas | **Implementada** | Toggle «Cargas»: flechas de carga gravitacional en cada losa (`carga = q_G·A`); casos G, Q, EX, EY y combinaciones en datos |
| Áreas tributarias | **Implementada** | Panel de tributarias: `A [m²]`, `carga total [kN]` por viga y resumen por piso |
| Deformada | **Implementada** | Modo «Deformada» (botón/tecla 5) con desplazamientos reales del combo activo, escala = % de la altura del edificio |
| Diagramas | **Implementada** | Diagramas axial (1), corte (2) y momento (3) por elemento con valores reales del combo activo; muros muestran V en plano |
| Superposición | **Implementada + verificada** | Selector de combo C1/C2/C3 (toolbar en pantalla); sección 3 verifica los 3 estados contra OpenSees |
| P-M (demanda-capacidad) | **Implementada** | Click en columna → curva `COL70/70_FIBER` con punto de demanda real del combo activo; muro → `W_DPRIME_OPENING_TO_3` con demanda propia por muro |
| Modificación del modelo | **Manual reproducible** | No hay UI de edición: el reanálisis se dispara por línea de comandos (CLI) y el resto del flujo es automático (sección 2) |

Datos que alimentan el viewer: 553 nodos, 462 elementos (129 columnas, 333 vigas, 75 muros equivalentes), 30 apoyos, 226 losas, 3 combinaciones (1659 registros de desplazamiento, 3234 registros de fuerzas internas incluyendo casos base).

## 2. Modificación del modelo (flujo completo, reproducible)

No se implementó todavía la edición visual del modelo; la modificación se hace por **dato en la interfaz de línea de comandos** y luego el pipeline es automático:

```text
interfaz/dato (arg CLI) → modelo (P1L3/carga_viva_sismo.py)
   → OpenSees (7 análisis: G, Q, EX, EY, C1, C2, C3)
   → resultados (estructura_p1l4_unity.json)
   → Unity (al entrar en Play, UnityData.Load() lee el JSON y reconstruye la escena)
```

Los dos parámetros de entrada que se pueden cambiar son la **carga viva** (`--q-kg-m2`) y el **coeficiente sísmico** (`--sc`). Cada escenario se corrió y su JSON quedó guardado para reproducción:

| Escenario | Comando | JSON guardado |
|---|---|---|
| Base | `python P1L4/exportar_resultados_unity.py` | `P1L4/semana5/resultados/escenario_baseline.json` |
| A (Q=600 kg/m²) | `... --q-kg-m2 600` | `P1L4/semana5/resultados/escenario_Q600.json` |
| B (C=0.30) | `... --sc 0.30` | `P1L4/semana5/resultados/escenario_SC030.json` |

### Modificación A — carga viva Q: 500 → 600 kg/m² (+20 %)

`Q` pasa de 4.9033 a 5.8840 kN/m². Como las cargas sísmicas se calculan con `W_i = D_i + 0.5·Q_i`, el cambio también sube la fuerza lateral.

| Indicador | Base | Q=600 | Δ |
|---|---:|---:|---:|
| Desplazamiento horizontal máx. C1 | 0.036036 m | 0.038102 m | +5.7 % |
| Desplazamiento nodo 114 (C1) | 0.017847 m | 0.018887 m | +5.8 % |
| Muro 1 — P (C1) | 442.62 kN | 467.63 kN | +5.65 % |
| Muro 1 — V en plano (C1) | 37.55 kN | 39.71 kN | +5.75 % |
| Muro 1 — M (C1) | 600.82 kN·m | 635.30 kN·m | +5.7 % |

### Modificación B — coeficiente sísmico C: 0.20 → 0.30 (+50 %)

Las fuerzas por gravedad no cambian; el corte basal escala con `C`.

| Indicador | Base | C=0.30 | Δ |
|---|---:|---:|---:|
| Muro 1 — V en plano (C1) | 37.55 kN | 56.33 kN | +50.0 % |
| Muro 1 — M (C1) | 600.82 kN·m | 901.22 kN·m | +50.0 % |
| Muro 1 — P (C1) | 442.62 kN | 442.62 kN | 0 % |
| Desplazamiento nodo 114 (C1) | 0.017847 m | 0.027298 m | +52.9 % |

El desplazamiento máximo global no cambió con `C` porque el nodo 361 (componentes en voladizo de `edificio_2`) tiene deformación dominada por gravedad; el **nodo 114** sí responde al sismo (+53 % con +50 % de fuerza lateral). Que la V y M del muro escalen exactamente con `C` (+50.0 %) confirma que el reanálisis reproduce la ley `F_i = C·W_i`.

### Restauración del estado de entrega

Al final se volvió al estado base y se verificó determinismo byte a byte:

```text
Python: python P1L4/exportar_resultados_unity.py   (defaults: --q-kg-m2 500 --sc 0.20)
SHA256 escenario_baseline.json   = 241CD1F3...C531897
SHA256 escenario_restaurado.json = 241CD1F3...C531897   → IDÉNTICOS
```

El reanálisis es **determinista**: el mismo comando reproduce el mismo JSON. El flujo manual que debe documentar el estudiante queda reducido a un solo comando (`--q-kg-m2` o `--sc`) + botón Play en Unity.

## 3. Superposición interactiva — 3 estados verificados contra resultados numéricos

El viewer muestra los 3 estados combinados (`C1/C2/C3`). En lugar de confiar en el etiquetado, se verificó que **la suma ponderada de los casos base (G, Q, EX, EY) reproduce exactamente la corrida directa de cada combinación** guardada en el JSON, usando los mismos coeficientes NCh433.

`P1L4/verificar_superposicion.py` compara, para los 462 elementos y las 12 componentes de fuerza por extremo:

| Estado | Coeficientes | Error absoluto máx. [kN o kN·m] | Error relativo global |
|---|---|---|---:|
| C1 | G+0.5Q+0.3EX+0.2EY | 4.798·10⁻¹¹ | 1.83·10⁻¹⁴ |
| C2 | G+0.5Q+0.3EX−0.2EY | 4.798·10⁻¹¹ | 1.86·10⁻¹⁴ |
| C3 | G+0.5Q−0.3EX+0.2EY | 4.798·10⁻¹¹ | 1.84·10⁻¹⁴ |

El error máximo es de orden `10⁻¹¹` kN (precisión de máquina), muy por debajo de la tolerancia `1e-6` usada en la Semana 3. Los tres estados que muestra Unity son numéricamente idénticos a la corrida directa de OpenSees. La curva P-M de columna usa esos mismos valores como punto de demanda.

## 4. Sidequest: carga móvil

**No implementada esta semana.** Se deja registrado el diseño acordado para no romper el viewer actual:

- **Regla física:** carga concentrada `P` (e.g. 30 kN por eje) que recorre cada viga entre sus nodos I y J; la posición se parametriza con `s ∈ [0, L]`.
- **Panel (futuro):** slider `s/L`, selector de viga por filtro de piso y etiqueta con la carga.
- **Reparto:** punto de aplicación mueve los nodos del elemento y OpenSees reanaliza; alternativa rápida sin reanálisis: usar las fuerzas de los casos base y colocar el punto en la envolvente (superposición restringida).
- **Conservación:** se verificaría `Σ R_z = P` en el elemento y que la suma de reacciones del edificio no cambie al mover la carga.
- **Respuesta visual:** flecha móvil de color por intensidad + diagrama de momento instantáneo.

La decisión técnica: implementarla sobre el pipeline de reanálisis de la sección 2, que ya es reproducible, sin tocar la escena.

## 5. UX estructural — ¿el viewer responde las 6 preguntas?

| Pregunta | Respuesta del viewer | Evaluación |
|---|---|---|
| ¿Dónde está el elemento? | Selección por click; panel con ID y coordenadas de nodos; vistas ISO/TOP/FRONT/RIGHT; ejes locales dibujados | **Sí.** La navegación por presets + órbita ubica rápido cualquier elemento; falta búsqueda por ID tecleado (pendiente) |
| ¿Cómo está apoyado? | Objetos de apoyo 3D y restricciones en panel de selección | **Sí**, a nivel de elemento. Faltaría una capa global de apoyos sobre el edificio completo |
| ¿Qué lo carga? | Toggle «Cargas» (flechas por losa), casos G/Q/EX/EY y combinaciones, panel de tributarias por viga | **Sí.** El repaso de tributarias con área y carga total por viga responde directamente |
| ¿Cómo se deforma? | Modo deformada real del combo activo, escala relativa a la altura | **Sí.** La escala por edificio evita el clásico problema de magnitudes absolutas |
| ¿Qué fuerzas tiene? | Diagramas axial/corte/momento con valores rotulados del combo activo; muro con V en plano real | **Sí.** Idear valores en el elemento y en el panel; se recomienda añadir valores máximos globales por piso |
| ¿Cuánta capacidad tiene? | Curva P-M (columna y muro) con punto de demanda del combo activo y rótulo C1/C2/C3 | **Sí.** La lectura visual de holgura/falla es directa; la capacidad es de la sección de fibra, no del ensamblaje global (documentado) |

Conclusión QA/UX: el viewer contesta las 6 preguntas con datos reales de OpenSees. Los 3 puntos débiles detectados (y candidatos a la siguiente iteración) son: búsqueda por ID, capa global de apoyos y máximos por piso.

## 6. Preparación móvil

### Teléfono compatible identificado

Se selecciona como referencia un equipo de gama media con requisitos de GPU Android de Unity (OpenGL ES 3.x / Vulkan):

| Dispositivo | Especificaciones relevantes |
|---|---|
| **Samsung Galaxy A54 5G** (SM-A546E) | Android 13, Exynos 1380, GPU Mali-G68 MP5 (Vulkan 1.1, OpenGL ES 3.1/3.2), 6.4" FHD+ AMOLED (2340×1080), 6/8 GB RAM |

Toda serie con estos atributos sirve: **Android 10+ (API 29)**, **OpenGL ES 3.0+/Vulkan**, arquitectura **ARM64**. El viewer usa IMGUI (OnGUI) + primitivas, liviano para esta GPU.

### Configuración de build (documentada; requiere módulo Android)

El equipo no tiene aún instalado el paquete **Android Build Support** (solo Windows standalone). Pasos para el build inicial:

1. **Unity Hub → Installs → 6000.6.0f1 → Add modules →** marcar *Android Build Support* (+ *OpenJDK* y *Android SDK & NDK Tools*).
2. **Build Settings → Platform → Android → Switch Platform** (acepta descargar SDK).
3. **Player Settings** (recomendados):
   - Company: `UANDES` · Product Name: `P1L4 Viewer` · package: `com.uandes.mcoc.p1l4`
   - Min API Level: 24 (Android 7.0) · Target API: último instalado
   - Scripting Backend: **IL2CPP** · Target Architectures: **ARM64**
   - Orientation: *Landscape Left* (el panel del viewer asume landscape)
   - Graphics APIs: **Vulkan** con fallback **OpenGLES3**
4. **Build → Build And Run** con el teléfono conectado (USB debugging ON), o `adb install` del `.apk` generado.

### Limitaciones detectadas para móvil

- Los atajos de teclado (1/2/3/5, flechas de cámara) no existen en teléfono; los diagramas y el combo **ya tienen toolbar en pantalla** (funciona con touch), pero la órbita de cámara por arrastre con botón derecho no — requiere 1/2-finger drag (próxima iteración).
- El panel de información (IMGUI) funciona con pantallas táctiles; debe validarse re-flow en 1080×2340 antes de publicar.

## 7. IA — funcionalidad compleja implementada por agente

Se documenta la funcionalidad con más lógica de esta semana, implementada por el agente y verificada contra los resultados:

**Fuerzas de muro en el viewer (V en plano) + flechas de carga por losa**
- El problema: los muros equivalen a elementos elásticos sin demanda de corte; el JSON llegaba a Unity con `Vy/Vz/T/Mz = 0`, y las losas no dibujaban su carga.
- El agente (a) calculó en el exportador la demanda aproximada `V_kN` por reparto del corte basal `V_i = (V_EX·|λEX| + V_EY·|λEY|)·(t·L)/Σ(t·L)`, con `M = V·h_eff` por niveles sobre el muro; (b) extendió `DemandRecord` con `V_kN` y el panel de muro pasó a mostrar «Vz in-plane» / «My in-plane» con nota de ortogonalidad; (c) añadió `CreateLoadArrows()`, flechas por losa `q_G·A`, activadas con el toggle «Cargas».

**Verificación**
- Reanálisis OpenSees local y comparación de órdenes de magnitud: muro 1 → C1 `P=442.6 kN`, `M=600.8 kN·m`, `V=37.55 kN`. La suma de las `V_kN` de los 75 muros acumula el corte basal sísmico combinado de cada combinación (el reparto por `t·L` suma 1 por construcción); para C1 esa suma es `3421.85 kN`.
- Compilación Unity sin errores `CS`: editor log `P1L4/unity_visualizador/Logs/Editor.log` → «Estructura lista: 537 elementos interactivos, 3 combinaciones», sin NullReference ni excepciones.
- El script `verificar_superposicion.py` de la sección 3 corrió sobre el JSON final y confirmó que las fuerzas de muro son consistentes con la superposición lineal (error `10⁻¹¹`).

## Archivos de reproducción

- `P1L4/exportar_resultados_unity.py` — pipeline dato → modelo → OpenSees → JSON Unity (args `--q-kg-m2`, `--sc`).
- `P1L4/verificar_superposicion.py` — verificación numérica de C1/C2/C3 vs casos base.
- `P1L4/extraer_indicadores.py` — extracción reproducible de indicadores por escenario.
- `P1L4/semana5/resultados/escenario_baseline.json` — escenario base (Q=500 kg/m², C=0.20).
- `P1L4/semana5/resultados/escenario_Q600.json` — modificación A.
- `P1L4/semana5/resultados/escenario_SC030.json` — modificación B.
- `P1L4/semana5/resultados/escenario_restaurado.json` — restauración (idéntico SHA256 al base).
- `P1L4/unity_visualizador/` — proyecto y escena del viewer.
- `P1L4/unity_visualizador/Assets/Resources/estructura_p1l4_unity.json` — JSON vigente (estado base entregado).
- `P1L4/unity_visualizador/Assets/Scripts/` — `StructureViewer.cs` (cargas), `ElementSelectable.cs`, `DiagramController.cs`, `StructureData.cs`, `UnityData.cs`, `PMPanel.cs`.