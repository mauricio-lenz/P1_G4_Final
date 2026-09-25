# Semana 5 — Avance: laboratorio estructural interactivo v1

**Proyecto:** modelo estructural UANDES, edificio 1 (visualizador P1L4).
**Unidades:** kN, m, kN·m, rad.

Los resultados numéricos de este informe provienen del pipeline reproducible de `Proyecto1/` (reanálisis OpenSees). El visualizador y los datos se mantienen en `Proyecto1/edificio_G4`, con el JSON de trabajo en `Proyecto1/edificio_G4/Assets/Resources/estructura_p1l4_unity.json`. El punto único de entrada para modificar el modelo es `Proyecto1/scripts/modificar_modelo.py`.

> Estado entregado: el modelo se entrega con la **Modificación A aplicada** (se quitó la viga `E1_5`, pasando de 462 a 461 elementos). Cada modificación se documenta completa y reproducible en la sección 2, con `--restore` para volver al estado base.

## 1. Funciones implementadas

Tabla de estado del visualizador (escena Unity ejecutada contra `estructura_p1l4_unity.json`):

| Funcionalidad | Estado | Cómo se verifica en el viewer |
|---|---|---|
| Navegación | **Implementada** | Vistas ISO/TOP/FRONT/RIGHT (botones en panel), órbita por arrastre con botón derecho, paneo con botón medio/flechas y zoom con rueda del mouse |
| Selección | **Implementada** | Click sobre elemento → panel con ID, nodos I/J, sección, material, ejes locales X'/Y'/Z', restricciones, N, Vy/Vz, T, My/Mz y trazabilidad (tag OpenSees → Unity → combo) |
| Apoyos | **Implementada** | 30 apoyos como objetos 3D distintivos; restricciones relevantes visibles en el panel de selección |
| Ejes | **Implementada** | Dibujo de ejes locales por elemento seleccionado (`EjeLocal_*`) y cámara sobre ejes globales |
| Cargas | **Implementada** | Toggle «Cargas»: flechas de carga gravitacional en cada losa (`carga = q_G·A`); casos G, Q, EX, EY y combinaciones en datos |
| Áreas tributarias | **Implementada** | Panel de tributarias: `A [m²]`, `carga total [kN]` por viga y resumen por piso; al quitar una viga la tributaria se reparte entre vecinas (/4) y el panel refleja el nuevo mapa |
| Deformada | **Implementada** | Modo «Deformada» (botón/tecla 5) con desplazamientos reales del combo activo, escala = % de la altura del edificio |
| Diagramas | **Implementada** | Diagramas axial (1), corte (2) y momento (3) por elemento con valores reales del combo activo; muros muestran V en plano |
| Superposición | **Implementada + verificada** | Selector de combo C1/C2/C3 (toolbar en pantalla); sección 3 verifica los 3 estados contra OpenSees |
| P-M (demanda-capacidad) | **Implementada** | Click en columna → curva `COL70/70_FIBER` con punto de demanda real del combo activo; muro → curva propia con demanda por muro |
| Modificación del modelo | **Implementada (CLI reproducible)** | No hay aún UI de edición visual: la modificación se declara en `modificar_modelo.py` y el pipeline dato → modelo → OpenSees → resultados → Unity corre en un solo comando (sección 2) |

Datos que alimentan el viewer en el estado entregado: **553 nodos, 461 elementos** (129 columnas, 332 vigas), 30 apoyos, 226 lozas, 3 combinaciones (3871 registros de desplazamiento y 3227 registros de fuerzas internas incluyendo casos base G/Q/EX/EY).

## 2. Modificación del modelo (flujo completo, reproducible)

La edición del modelo no necesita tocar la escena de Unity ni reescribir el JSON a mano. El flujo es:

```text
interfaz/dato (una línea en aplicar_ediciones() de modificar_modelo.py)
   → modelo (JSON base en Proyecto1/data/estructura_completo_unity.json, con backup .bak automático)
   → OpenSees (7 análisis: G, Q, EX, EY, C1, C2, C3)
   → resultados (Proyecto1/edificio_G4/Assets/Resources/estructura_p1l4_unity.json)
   → Unity (al entrar en Play, UnityData.Load() lee el JSON y reconstruye la escena)
```

Operaciones disponibles en la edición: `quitar_elemento` (por tag, tipo o piso), `quitar_loza`, `cambiar_seccion`, `mover_nodo`, `cambiar_apoyo`, `quitar_apoyo`. Tras editar, se ejecuta:

```text
python Proyecto1/scripts/modificar_modelo.py      # aplica la edición, guarda backup y re-exporta
python Proyecto1/scripts/modificar_modelo.py --restore   # vuelve al estado base desde el .bak
```

### Modificación A — quitar la viga E1_5 (V60/80, segundo nivel)

Edit: `quitar_elemento(data, tag="E1_5")`. Lo que se verificó en la corrida real:

```text
Modelo: 553 nodos | 462 elementos (vigas=333, columnas=129) | 30 apoyos | 226 lozas
Quitando elemento E1_5 (id=5, viga, V60/80)
Repartida tributaria (/4): [4, 6, 32, 33]        ← el área que tributaba E1_5 se reparte entre 4 vecinas
Modelo: 553 nodos | 461 elementos (vigas=332, columnas=129) | 30 apoyos | 226 lozas
```

Reanálisis OpenSees completo (G/Q/EX/EY/C1/C2/C3) con 461 elementos → `fuerzas_elem = 3227` registros (= 461 × 7). El checksum de desplazamientos del JSON cambia con la modificación (evidencia numérica de que el modelo entregado difiere del base):

| Escenario | Elementos | Checksum desplazamientos |
|---|---:|---:|
| Base | 462 | `29822526.450491115` |
| **Entregado (Mod A)** | **461** | **`29967285.813745894`** |

### Modificación B — cambiar sección de E1_10: V60/80 → V30/45

Edit: `cambiar_seccion(data, tag="E1_10", seccion="V30/45")`. Verificado en la corrida real:

```text
Seccion E1_10: 0.6x0.8 -> 0.3x0.45
```

El reanálisis cambia las fuerzas internas del propio elemento. Comparando C1 (G+0.5Q+0.3EX+0.2EY) en `E1_10` antes/después:

| Componente (C1, extremo J) | Base (V60/80) | E1_10→V30/45 | Δ |
|---|---:|---:|---:|
| Momento Mz_J [kN·m] | 682.029 | 247.758 | **−63.7 %** |
| Axial N_J [kN] | −487.024 | −450.477 | −7.5 % |
| Corte Vy_J [kN] | −101.881 | −22.811 | −77.6 % |

Esto confirma que `cambiar_seccion` no solo renombra la sección: modifica la rigidez del elemento en `modificar_modelo.py`, el modelo reanaliza en OpenSees y las fuerzas en el JSON de Unity (y por lo tanto los diagramas del viewer) reflejan el nuevo estado.

### Restauración y determinismo

```text
python Proyecto1/scripts/modificar_modelo.py --restore   # restaura data/estructura_completo_unity.json desde .bak
```

El reanálisis es determinista: el mismo comando sobre el mismo JSON base reproduce los mismos resultados (superposición de la sección 3 se re-verificó después de cada modificación y siguió en `10⁻¹⁴`).

## 3. Superposición interactiva — 3 estados verificados contra resultados numéricos

El viewer muestra 3 estados combinados (`C1/C2/C3`). Se verificó que **la suma ponderada de los casos base (G, Q, EX, EY) reproduce exactamente la corrida directa de cada combinación** guardada en el JSON, usando los coeficientes NCh433.

`Proyecto1/scripts/verificar_superposicion.py` compara las 12 componentes de fuerza por extremo de todos los elementos (461 en el estado entregado — para el base son 462):

| Estado | Coeficientes | Error absoluto máx. [kN o kN·m] | Error relativo global |
|---|---|---|---:|
| C1 | G+0.5Q+0.3EX+0.2EY | 4.798·10⁻¹¹ | 1.80·10⁻¹⁴ |
| C2 | G+0.5Q+0.3EX−0.2EY | 4.798·10⁻¹¹ | 1.83·10⁻¹⁴ |
| C3 | G+0.5Q−0.3EX+0.2EY | 5.807·10⁻¹¹ | 2.18·10⁻¹⁴ |

El error máximo es de orden `10⁻¹¹` kN (precisión de máquina), muy por debajo de la tolerancia `1e-6`. Los tres estados que muestra Unity son numéricamente idénticos a la corrida directa de OpenSees. Adicionalmente, la curva P-M de columna `COL70/70_FIBER` (H-30) usa esos mismos valores como punto de demanda: `Po = 14044.198 kN`, 5 puntos — constante en base y en ambas modificaciones, como corresponde a la sección de fibra.

Indicadores por combo del estado entregado (`Proyecto1/scripts/extraer_indicadores.py`):

| Indicador | C1 | C2 | C3 |
|---|---:|---:|---:|
| Desplazamiento horizontal máx. [m] (nodo 361) | 0.036036 | 0.036036 | 0.036036 |
| Muro 1 — P [kN] | 442.62 | 442.62 | 442.62 |
| Muro 1 — M [kN·m] | 600.82 | 600.82 | 600.82 |
| Muro 1 — V en plano [kN] | 37.55 | 37.55 | 37.55 |

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
| ¿Qué fuerzas tiene? | Diagramas axial/corte/momento con valores rotulados del combo activo; muro con V en plano real | **Sí.** Valores en el elemento y en el panel; se recomienda añadir valores máximos globales por piso |
| ¿Cuánta capacidad tiene? | Curva P-M (columna y muro) con punto de demanda del combo activo y rótulo C1/C2/C3 | **Sí.** La lectura visual de holgura/falla es directa; la capacidad es de la sección de fibra, no del ensamblaje global (documentado) |

Conclusión QA/UX: el viewer contesta las 6 preguntas con datos reales de OpenSees. Los 3 puntos débiles detectados (candidatos a la siguiente iteración) son: búsqueda por ID, capa global de apoyos y máximos por piso.

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

**Pipeline de modificación-reanálisis unificado (`modificar_modelo.py`) + fuerzas de muro V en plano y flechas de carga**
- El agente unificó en `modificar_modelo.py` la edición del modelo (quitar elemento, cambiar sección, mover nodo, apoyos, lozas), el backup automático `.bak` y la re-exportación a Unity en un solo comando; el reparto de área tributaria al eliminar una viga se implementó en `repartir_area_eliminada()` (dividió la tributaria de `E1_5` entre los nodos 4, 6, 32 y 33).
- El exportador calcula la demanda aproximada de muro `V_kN` por reparto del corte basal (`V_i = (V_EX·|λEX| + V_EY·|λEY|)·(t·L)/Σ(t·L)`), extiende `DemandRecord` con `V_kN` y dibuja flechas de carga por losa `q_G·A` con el toggle «Cargas».

**Verificación**
- Ambos flujos de la sección 2 se corrieron de punta a punta: reanálisis OpenSees local, cambios de elemento/sección verificados en el resumen del script y fuerzas internas comparadas antes/después (E1_10: Mz_J 682.0→247.8 kN·m).
- `verificar_superposicion.py` corrió sobre el JSON final de cada estado y confirmó la superposición en `10⁻¹¹`/`10⁻¹⁴` (sección 3).
- Al abrir en el editor Unity al estado base, el log (`Proyecto1/edificio_G4/Logs/Editor.log`) registró «Estructura lista: 537 elementos interactivos, 3 combinaciones» sin errores `CS`/NullReference; la re-serialización de la escena (menú MCOC → Crear Visualizador) resolvió el problema de scripts «missing» de Unity 6 en Play Mode.

## Archivos de reproducción

- `Proyecto1/scripts/modificar_modelo.py` — punto único de edición del modelo + reanálisis (flags `--restore`, `--ejemplo`, `--dry-run`).
- `Proyecto1/scripts/exportar_resultados_unity.py` — pipeline dato → modelo → OpenSees → JSON Unity.
- `Proyecto1/scripts/verificar_superposicion.py` — verificación numérica de C1/C2/C3 vs casos base.
- `Proyecto1/scripts/extraer_indicadores.py` — extracción reproducible de indicadores por escenario.
- `Proyecto1/Data_validacion/` — respaldos de escenarios verificados de semanas previas.
- `Proyecto1/edificio_G4/` — proyecto y escena del viewer.
- `Proyecto1/edificio_G4/Assets/Resources/estructura_p1l4_unity.json` — JSON vigente (estado entregado: Mod A aplicada, 461 elementos).
- `Proyecto1/data/estructura_completo_unity.json` (+ `.bak`) — modelo base y backup de restauración.
- `Proyecto1/edificio_G4/Assets/Scripts/` — `StructureViewer.cs` (cargas), `ElementSelectable.cs`, `DiagramController.cs`, `StructureData.cs`, `UnityData.cs`, `PMPanel.cs`; `Scripts/Editor/MCOCSetup.cs` (menú `MCOC/Crear Visualizador`).