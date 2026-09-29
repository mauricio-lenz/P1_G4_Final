# Semana 5 — Avance: laboratorio estructural interactivo v1

**Proyecto:** modelo estructural del Grupo 4 — edificio 1 (planos 2017_67) y edificio 2 (planos 2024_22), hormigón armado H-30, conectados por junta de dilatación.
**Herramientas:** OpenSeesPy (análisis), Python (pipeline), Unity 6000.6.0f1 (viewer `Proyecto1/edificio_G4`).
**Unidades:** kN, m, kN·m, rad.

Todas las cifras de este informe salen del pipeline reproducible de `Proyecto1/` con el modelo vigente (`Proyecto1/data/estructura_completo_unity.json`) y del JSON que lee Unity (`Proyecto1/edificio_G4/Assets/Resources/estructura_p1l4_unity.json`).

## 0. Estado del modelo

Esta semana el modelo se contrastó contra los planos DXF y se corrigieron los detalles que no calzaban (`Proyecto1/scripts/ajustar_modelo_planos.py`, reproducible desde el respaldo `estructura_completo_unity.pre_planos.json`). Los principales:

- El edificio 2 estaba **reflejado en Y** respecto del plano (eje 2 en y = 1.65 en vez de 0; núcleo del ascensor al sur en vez de al norte).
- Altura de piso real **3.96 m** en ambos edificios (niveles −3.96 / 0 / 3.96 / 7.92 / 11.88 / 15.84 m, z = 0 en el cielo 1° subterráneo) y **subterráneo del edificio 2** extendido hasta el radier.
- **Pilares metálicos P.M. 300×300×20** y **arriostres V.M. 300×300×5** (elevaciones 2017_67-800/801/802), con E = 200 GPa y propiedades del perfil cajón.
- Muros faltantes (subterráneo, piso 1, eje 1''), secciones V40/60 y V30/45 donde indica el plano, **losas en voladizo** y losas de la zona I'-J cargando a sus vigas.
- **45 vigas partidas** en nodos intermedios: varias vigas secundarias llegaban a mitad de otra sin nodo común y quedaban desconectadas.
- Extremos de vigas apoyados en muros sin pilar (ejes A' y D' del edificio 2) modelados como **columnas equivalentes de gravedad**.
- **Sismo por edificio y por piso con diafragma rígido** (`rigidDiaphragm`): antes toda la fuerza del piso se aplicaba en un solo nodo común a ambos edificios.
- La viga `E1_5` (quitada en una versión previa como modificación de prueba) se **restauró**; las modificaciones quedan como escenarios (sección 2).

| Dato | Valor |
|---|---:|
| Nodos | 589 |
| Elementos | 557 (398 vigas, 149 columnas, 10 arriostres) |
| Muros (visualización y demanda P-M) | 91 |
| Paneles de losa | 239 |
| Apoyos (empotrados) | 34 |
| Casos y combinaciones analizados | G, Q, EX, EY, C1, C2, C3 |
| Registros en el JSON de Unity | 4 123 desplazamientos · 3 899 fuerzas internas · 2 curvas P-M · 10 recorridos de carga móvil |
| Equilibrio G | aplicada 27 878.1 kN = reacción 27 878.1 kN |
| Equilibrio sísmico (por edificio) | edificio 1: 5 298.3 kN = reacción; edificio 2: 2 524.6 kN = reacción |

Combinaciones: `C1 = G + 0.5Q + 0.3EX + 0.2EY`, `C2 = G + 0.5Q + 0.3EX − 0.2EY`, `C3 = G + 0.5Q − 0.3EX + 0.2EY` (Q = 500 kg/m², coeficiente sísmico 0.20).

## 1. Funciones implementadas

Viewer Unity (escena `StructureViewerScene`, Play):

| Función | Estado | Cómo se usa / verifica en el viewer |
|---|---|---|
| Navegación | **Implementada** | Vistas ISO / TOP / FRONT / RIGHT, órbita con botón derecho, paneo, zoom con rueda; filtro por piso |
| Selección | **Implementada** | Click sobre elemento → panel con ID/tag, nodos I/J, sección, material, ejes locales, restricciones, N, V, T, M del combo activo y trazabilidad OpenSees → Unity |
| Apoyos | **Implementada** | 34 apoyos empotrados dibujados como objetos 3D; restricciones en el panel de selección |
| Ejes | **Implementada** | Ejes globales y ejes locales X'/Y'/Z' por elemento seleccionado |
| Cargas | **Implementada** | Capa de cargas por losa (q·A); casos G, Q, EX, EY y combos en la barra superior |
| Áreas tributarias | **Implementada** | Panel de tributarias por viga (A [m²], carga [kN]) y resumen por piso |
| Deformada | **Implementada** | Modo Deformada del combo activo, escala automática por edificio (5 % de la altura) |
| Diagramas | **Implementada** | Axial, corte y momento por elemento con valores del combo activo |
| Superposición | **Implementada + verificada** | Combos C1/C2/C3 en la barra superior y sliders λ_G, λ_Q, λ_EX, λ_EY de superposición en vivo (sección 3) |
| P-M | **Implementada** | Click en columna H-30 → curva `COL70/70_FIBER` con punto de demanda; muro → curva propia; coloreo por utilización |
| Modificación del modelo | **Implementada (desde Unity y por script)** | Panel **Quitar elemento**: reanálisis OpenSees en segundo plano sin salir de Unity; `modificar_modelo.py` para cambios persistentes (sección 2) |
| Carga en elemento (extra) | **Implementada** | Carga puntual o distribuida (tramo x1–x2) en −Z, X o Y sobre el elemento elegido por id/tag |
| Carga móvil (sidequest) | **Implementada** | Sección 4 |

## 2. Modificación del modelo — dos modificaciones completas

Flujo **interfaz/dato → modelo → OpenSees → resultados → Unity**. Hay dos vías, ambas reproducibles:

```text
Vía 1 (interactiva, desde Unity)                Vía 2 (persistente, por script)
panel "Quitar elemento" (id/tag o click)        edición en aplicar_ediciones() de modificar_modelo.py
  → quitar_elemento.py marca "removed"            → escribe data/estructura_completo_unity.json (+ backup .bak)
  → OpenSees: G, Q, EX, EY, C1, C2, C3            → exportar_resultados_unity.py: 7 análisis OpenSees
  → JSON de resultados (temporal)                 → Assets/Resources/estructura_p1l4_unity.json
  → Unity reemplaza resultados en memoria         → Unity lo carga al dar Play
```

En la vía 1 el elemento quitado deja de aportar rigidez, pero su carga tributaria se mantiene en sus nodos (la losa sigue ahí), por lo que el peso y la masa sísmica se conservan. El panel informa equilibrio, convergencia, los elementos con mayor aumento de esfuerzo y la **deformada original vs modificada** (naranjo/verde, misma escala). "Restaurar modelo original" vuelve al estado base; no se modifica ningún archivo.

### Modificación A — quitar la viga `E1_5` (V60/80, cielo 1, eje 1, x = 20 → 25 m)

Vía 1. En Unity: *QUITAR ELEMENTO* → `E1_5` → **Quitar y analizar**. Equivalente por consola:

```text
python -X utf8 Proyecto1/scripts/quitar_elemento.py --elements E1_5 --out resultado.json
OK quitados=['E1_5'] | G aplicada=-27878.1 kN, reaccion=27878.1 kN, perdida=0.0 kN | 7 casos ok=True
```

| Resultado (C1) | Original | Sin `E1_5` |
|---|---:|---:|
| `E1_6` (tramo x = 25 → 30, queda en voladizo) — \|M\|máx [kN·m] | 364.9 | **841.3** |
| `E1_13` — \|M\|máx [kN·m] | 431.8 | 552.1 |
| `E1_33` (viga x = 25 que llega al nodo libre) — \|M\|máx [kN·m] | 71.5 | 128.1 |
| Nodo 43 (x = 25, y = 8.9, cielo 1) — u_z por G [mm] | −1.75 | **−9.14** |

Lectura estructural: al quitar `E1_5`, el nodo x = 25 pierde uno de sus dos apoyos en el eje 1 y `E1_6` pasa a trabajar como voladizo desde el pilar de x = 30; su momento se duplica y el nodo libre baja 9.1 mm. La carga total sigue equilibrada y todos los casos convergen (no hay mecanismo).

### Modificación B — cambiar la sección de `E1_10`: V60/80 → V30/45 (cielo 1, eje 2, x = 7.51 → 10 m)

Vía 2. En `aplicar_ediciones()` de `modificar_modelo.py` se activa la línea `cambiar_seccion(data, tag="E1_10", seccion="V30/45")` y se ejecuta:

```text
python -X utf8 Proyecto1/scripts/modificar_modelo.py            # aplica, guarda backup .bak y re-exporta a Unity
python -X utf8 Proyecto1/scripts/modificar_modelo.py --restore  # vuelve al modelo base
```

| Resultado en `E1_10` (C1, extremo J) | V60/80 | V30/45 | Δ |
|---|---:|---:|---:|
| Momento M_J [kN·m] | 592.46 | 227.63 | −61.6 % |
| Corte V_J [kN] | 239.03 | 157.51 | −34.1 % |
| u_z nodo J (33) [mm] | −0.79 | −0.76 | — |

Lectura estructural: la viga menos rígida atrae menos momento (redistribución hacia los elementos vecinos). El cambio no es solo de nombre: `width_m`/`height_m` alimentan la rigidez del elemento en OpenSees.

Ambas modificaciones quedan documentadas como escenarios en `modificar_modelo.py` (comentadas); el modelo base es el de los planos.

## 3. Superposición interactiva — tres estados verificados

Cada combinación se calcula de dos maneras: (a) corrida directa de OpenSees con las cargas combinadas y (b) suma de los casos base con sus factores. Como el modelo es lineal deben coincidir. `Proyecto1/scripts/verificar_superposicion.py` compara las 12 componentes de fuerza de los 557 elementos:

| Estado | Combinación | Error absoluto máx. [kN o kN·m] | Error relativo |
|---|---|---:|---:|
| C1 | G + 0.5Q + 0.3EX + 0.2EY | 5.7·10⁻¹² | 2.1·10⁻¹⁵ |
| C2 | G + 0.5Q + 0.3EX − 0.2EY | 1.6·10⁻¹¹ | 6.3·10⁻¹⁵ |
| C3 | G + 0.5Q − 0.3EX + 0.2EY | 4.9·10⁻¹² | 1.8·10⁻¹⁵ |

Ejemplo puntual (momento en el extremo J de `E1_5`):

| Estado | Corrida directa [kN·m] | Σ λ·caso base [kN·m] | Diferencia |
|---|---:|---:|---:|
| C1 | −291.9463 | −291.9463 | 2·10⁻¹³ |
| C2 | −276.8392 | −276.8392 | 5·10⁻¹³ |
| C3 | −282.9125 | −282.9125 | 1·10⁻¹³ |

Los tres estados son distintos entre sí (el sentido del sismo cambia la respuesta), como se ve en los indicadores (`extraer_indicadores.py`):

| Indicador | C1 | C2 | C3 |
|---|---:|---:|---:|
| Desplazamiento horizontal máx. [mm] | 9.46 (nodo 360) | 11.81 (nodo 359) | 11.12 (nodo 359) |
| Muro 1 — V en plano [kN] | 180.1 | 180.1 | −180.1 |
| Muro 1 — M [kN·m] | 2 882.3 | 2 882.3 | −2 882.3 |

En el viewer la superposición es **interactiva**: el panel "Superposición en vivo" tiene sliders λ_G, λ_Q, λ_EX, λ_EY; al fijarlos en (1, 0.5, 0.3, 0.2), (1, 0.5, 0.3, −0.2) o (1, 0.5, −0.3, 0.2) el combo sintético SUP reproduce C1, C2 y C3 (diagramas, deformada y punto P-M).

## 4. Sidequest: carga móvil — implementada

**Regla física.** Carga puntual vertical P (por defecto 50 kN, editable) que recorre el eje 2 del piso y edificio elegidos (5 pisos × 2 edificios = 10 recorridos; 10 m a 50 m). En la viga que la contiene (nodos A→B, largo L, a = s − s_A, b = L − a) la carga se reemplaza por sus fuerzas de empotramiento perfecto:

```text
F_A = P b² (3a + b) / L³        M_A = +P a b² / L²
F_B = P a² (a + 3b) / L³        M_B = −P a² b / L²
```

**Reparto.** El modelo es lineal: `carga_movil.py` precalcula con OpenSees la respuesta a cargas unitarias (F_z y momento) en cada nodo del recorrido, y Unity combina esos casos con los coeficientes anteriores. El movimiento es **continuo** y **exacto** para cualquier s y cualquier P (P es un factor de escala), sin volver a correr el análisis.

**Panel** (columna izquierda, "CARGA MÓVIL"): selector de edificio y piso, campo P [kN] con −/+, slider de posición s, animación ida y vuelta con velocidad regulable, y lecturas de viga cargada, a, b, F_A, F_B y momentos de empotramiento.

**Conservación.** El panel muestra en vivo F_A + F_B y la suma de reacciones verticales de los apoyos frente a P ("OK: Suma Rz = P"). Validación contra un análisis directo de OpenSees con la viga partida en el punto de carga (3 posiciones por recorrido, 30 en total): ΣR_z = 50.000000 kN en todos y error máximo de desplazamiento < 10⁻¹⁶ m.

**Respuesta visual.** Flecha roja con la etiqueta "P = … kN" sobre el punto de carga, recorrido resaltado en naranjo, diagrama de momento con el quiebre bajo la carga y deformada actualizados en vivo.

## 5. UX estructural — ¿el viewer contesta las 6 preguntas?

| Pregunta | Qué ofrece el viewer | Evaluación |
|---|---|---|
| ¿Dónde está el elemento? | Selección por click, panel con ID/tag y coordenadas de nodos, vistas preset, filtro por piso, búsqueda por id/tag en los paneles de carga y quitar elemento | **Sí.** La búsqueda por tag ubica cualquier elemento; falta centrar la cámara en el elemento buscado |
| ¿Cómo está apoyado? | Apoyos 3D, restricciones en el panel, columnas y muros por piso | **Sí**, a nivel de elemento. Una vista "camino de carga" hasta el apoyo sería el siguiente paso |
| ¿Qué lo carga? | Capa de cargas, casos G/Q/EX/EY, panel de tributarias, carga en elemento y carga móvil | **Sí.** Se puede agregar una carga y ver su efecto aislado con conservación de reacciones |
| ¿Cómo se deforma? | Deformada por combo con escala por edificio; comparación original vs modificada con escala fija opcional | **Sí.** La comparación hace visible el efecto local de quitar un elemento |
| ¿Qué fuerzas tiene? | Diagramas axial/corte/momento, valores en el panel, ranking de elementos que más aumentan al quitar uno | **Sí.** El diagrama de corte no dibuja el salto bajo una carga puntual (el de momento sí) |
| ¿Cuánta capacidad tiene? | Curva P-M con punto de demanda del combo activo; coloreo por utilización | **Parcial.** Curvas P-M para columnas H-30 y muro de referencia; pilares metálicos y muros equivalentes no tienen curva propia |

Puntos débiles detectados: centrar la cámara en el elemento buscado, salto del corte bajo cargas puntuales y curvas de capacidad para las secciones metálicas.

## 6. Preparación móvil

**Teléfono de referencia:** Samsung Galaxy A54 5G (Android 13, Exynos 1380, GPU Mali-G68 MP5 con Vulkan 1.1 / OpenGL ES 3.2, pantalla 2340×1080). Requisitos mínimos equivalentes: Android 10+ (API 29), OpenGL ES 3.0+/Vulkan, ARM64.

**Build móvil inicial: generado.** `Proyecto1/edificio_G4/Builds/Android/P1G4_Viewer.apk` (22 MB; 0 errores). Se reproduce con el menú **MCOC → Build Android (APK)** o por consola:

```text
Unity.exe -batchmode -quit -projectPath Proyecto1/edificio_G4 -buildTarget Android -executeMethod BuildAndroid.Build
```

`Assets/Scripts/Editor/BuildAndroid.cs` fija la configuración: paquete `cl.uandes.mcoc.p1g4`, IL2CPP, ARM64, Android 10+ (API 29), Vulkan con respaldo OpenGLES3, solo orientación horizontal. Módulo *Android Build Support* (+ OpenJDK, SDK & NDK) instalado en Unity 6000.6.0f1.

**Adaptaciones para el teléfono:**
- controles táctiles de cámara: 1 dedo orbita, pellizco hace zoom, 2 dedos desplazan;
- selección con un toque corto sin arrastre;
- interfaz escalada a una pantalla virtual de ~720 px de alto, para que los paneles sean legibles en alta densidad;
- los toques sobre los paneles no mueven la cámara ni seleccionan.

En el teléfono funcionan navegación, selección, combos, diagramas, deformada, superposición en vivo, P-M y carga móvil, porque usan datos precalculados en el JSON. Carga en elemento y quitar elemento requieren Python/OpenSees y se ocultan en el celular.

**Pendiente:** validar la experiencia en el equipo físico (legibilidad de los paneles en 2340×1080 y sensibilidad de los gestos).

## 7. IA — funcionalidad compleja implementada por el agente

**Revisión del modelo contra los planos DXF.** El agente (Claude Code) extrajo ejes, cotas, muros, pilares y vigas de las plantas y elevaciones DXF (ezdxf), los transformó a coordenadas del modelo y generó superposiciones plano-modelo por piso. Así detectó el reflejo en Y del edificio 2, los muros faltantes, los pilares metálicos y arriostres, las vigas desconectadas y el sismo aplicado en un solo nodo por piso. Cada corrección quedó en `ajustar_modelo_planos.py`, reproducible desde el respaldo.

**Carga móvil, carga en elemento y quitar elemento.** Implementados con la misma idea: casos unitarios o reanálisis en OpenSees más combinación en Unity.

**Verificación.**
- **Equilibrio:** cierra en G y en EX/EY de cada edificio (sección 0).
- **Superposición:** error del orden de 10⁻¹¹ (sección 3).
- **Carga móvil:** 30 comparaciones contra análisis directo con error < 10⁻¹⁶ m (sección 4).
- **Carga en elemento:** validada en vigas, columnas, pilares metálicos y arriostres en −Z, X e Y.
- **Supervisión del grupo:** el grupo revisó las superposiciones plano-modelo y el viewer en Unity antes de aceptar cada cambio.

## Archivos de reproducción

| Archivo | Rol |
|---|---|
| `Proyecto1/scripts/ajustar_modelo_planos.py` | Ajustes del modelo según planos (desde `data/estructura_completo_unity.pre_planos.json`) |
| `Proyecto1/scripts/carga_viva_sismo.py` | Modelo OpenSees, cargas, sismo con diafragma rígido |
| `Proyecto1/scripts/exportar_resultados_unity.py` | 7 análisis + JSON de Unity (incluye carga móvil) |
| `Proyecto1/scripts/verificar_superposicion.py` | Verificación C1/C2/C3 contra casos base |
| `Proyecto1/scripts/extraer_indicadores.py` | Indicadores por combo |
| `Proyecto1/scripts/modificar_modelo.py` | Modificaciones persistentes del modelo (`--restore`) |
| `Proyecto1/scripts/quitar_elemento.py` | Reanálisis al quitar elementos (lo usa Unity) |
| `Proyecto1/scripts/carga_movil.py` · `carga_elemento.py` | Casos unitarios de carga móvil y de carga en elemento |
| `Proyecto1/edificio_G4/` | Proyecto Unity; paneles `MovingLoadPanel.cs`, `ElementLoadPanel.cs`, `ElementRemovalPanel.cs` |
