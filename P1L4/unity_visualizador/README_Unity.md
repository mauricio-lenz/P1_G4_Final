# P1L4 — Visualizador Unity Estructural (Enriquecido)

Visualizador Unity de la estructura 3D con resultados de análisis estático lineal OpenSeesPy, combinaciones de carga NCh433, diagramas de interacción P-M, deformada y panel de información completo por elemento.

## Funcionalidades principales

- **Estructura 3D**: 553 nodos, 129 columnas, 333 vigas, 75 muros equivalentes, diafragmas/losas, apoyos empotrados.
- **Selector de combinaciones de carga**: C1 = G+0.5Q+0.3EX+0.2EY, C2 = G+0.5Q+0.3EX-0.2EY, C3 = G+0.5Q-0.3EX+0.2EY (NCh433).
- **Diagrams OpenSees** (tecla 0–3): Axial, Corte, Momento — con fuerzas internas reales del combo activo.
- **Tabla compacta de valores**: al seleccionar un elemento y activar axial/corte/momento, muestra I, centro, J y maximo absoluto del diagrama.
- **Deformada** (tecla 5): desplazamientos escalados ×120 del combo activo.
- **Panel de información por elemento** (click izquierdo): sección, material, restricciones, ejes locales, fuerzas interpoladas, trazabilidad OpenSees→Unity→resultados.
- **Diagrama P-M interactivo** (click izquierdo en columna/muro): curva de capacidad HA con punto de demanda (N, M) del elemento en el combo activo.

## Arquitectura

```
P1L4/
├── exportar_resultados_unity.py   ← Generador del JSON enriquecido (requiere venv con openseespy)
├── unity_visualizador/
│   ├── Assets/
│   │   ├── Resources/
│   │   │   ├── estructura_completo_unity.json   ← JSON base (P1L2)
│   │   │   └── estructura_p1l4_unity.json       ← JSON enriquecido (generado por el exportador)
│   │   └── Scripts/
│   │       ├── StructureData.cs       ← Modelo de datos C# (deserializa el JSON enriquecido)
│   │       ├── StructureViewer.cs     ← Constructor de la escena + selector de combinaciones
│   │       ├── ElementSelectable.cs   ← Comportamiento de selección + info completa
│   │       ├── ElementPicker.cs       ← Raycast click + panel de info + trigger P-M
│   │       ├── DiagramController.cs   ← Diagramas de fuerza + deformada
│   │       ├── PMPanel.cs             ← Panel de diagrama P-M interactivo (nuevo)
│   │       ├── UnityData.cs           ← Datos estáticos compartidos entre scripts
│   │       ├── InfoSelectable.cs      ← Info para diafragmas/losas
│   │       ├── OrbitCamera.cs         ← Cámara orbital (click derecho rotar, rueda zoom)
│   │       └── Editor/
│   │           └── MCOCSetup.cs       ← Setup automático de la escena
│   ├── Packages/                      ← Unity Package Manager
│   ├── ProjectSettings/               ← Configuración del proyecto Unity
│   └── README_Unity.md                ← Este archivo
```

## 1. Generar datos (Python)

Requiere el venv del proyecto con `openseespy` instalado:

```bat
.venv\Scripts\python.exe -X utf8 P1L4\exportar_resultados_unity.py
```

Opciones:
- `--q-kg-m2 500` — carga viva Q en kg/m² (default 500 → 4.903 kN/m²)
- `--sc 0.20` — coeficiente sismico (default 0.20)

El exportador:
1. Carga `estructura_completo_unity.json` (P1L2).
2. Corre análisis estático lineal con OpenSeesPy para 3 combinaciones (C1, C2, C3).
3. Extrae desplazamientos (553 nodos x 3 combos) y fuerzas internas (462 elementos x 3 combos, 12 componentes x 2 extremos).
4. Genera curvas P-M: COL70/70_FIBER (5 puntos) y W_DPRIME_OPENING_TO_3 (24 puntos envolvente).
5. Genera demandas P-M por muro y por combinacion activa.
6. Guarda `estructura_p1l4_unity.json` (~1.3 MB) en `P1L4/unity_visualizador/Assets/Resources/`.

## 2. Abrir en Unity

1. Copiar la carpeta `P1L4/unity_visualizador` completa (o usar el `Assets/` como tu Unity project si ya tienes uno).
2. Abrir Unity Hub → Open → seleccionar `P1L4/unity_visualizador`.
3. Dejar que Unity regenere `Library/` (excluido del gitignore).
4. Crear una escena vacía.
5. Ir al menú **MCOC → Crear Visualizador** (o confiar en la creación automática del editor script).

El `MCOCSetup.cs` (editor-only) crea automáticamente: StructureViewer, Camera + ElementPicker + OrbitCamera, Light, y guarda la escena.

## 3. Uso

### Combinaciones de carga

Usa el toolbar en la parte superior izquierda para seleccionar entre C1, C2, C3. El diagrama de fuerzas y la deformada se actualizan según la combinación seleccionada.

### Diagramas de fuerzas (teclas)

- `0` — Ocultar diagramas
- `1` — Axial N (rojo)
- `2` — Corte Vy (naranja)
- `3` — Momento My (magenta)
- `5` — Deformada (verde, ×120)

Las fuerzas provienen de los 12 componentes de `eleForce` de OpenSees (coordenadas locales). Para vigas, se suma el efecto de carga distribuida (qL²/8 parabólico).
Al seleccionar una viga, columna o muro, aparece una tabla compacta con los valores del diagrama activo: extremos I/J, centro y maximo absoluto. Para momento/corte se muestran tambien componentes locales My/Mz o Vy/Vz segun corresponda.

### Panel de información (click)

Al hacer click en cualquier columna, viga o muro:
- ID Unity y OpenSees (elementTag)
- Nodos extremos, piso, edificio
- Sección y material (fc', fy, barras, As, rho)
- Restricciones en cada extremo (empotrado/pasador/etc.)
- Ejes locales X' Y' Z'
- Fuerzas/demanda: N, Vy, Vz, T, My, Mz segun corresponda
- Trazabilidad: OpenSees tag → Unity obj → combo activo → sección/capacidad

### Diagrama P-M interactivo

Al hacer click en una **columna** o **muro** (con curva disponible):
- Se abre un panel con la curva P-M de capacidad.
- Punto de demanda del combo activo, rotulado con C1/C2/C3 y expresion completa.
- Demandas estimadas por muro; al seleccionar otro muro cambia el punto de demanda.
- Para columnas, el punto de demanda (N, M) proviene de las fuerzas internas reales del combo activo.
- Se muestra información de material, barras y porcentaje de acero.

Columnas disponibles con P-M: todas las 129 columnas (COL70/70 → curva COL70/70_FIBER).
Muros disponibles con P-M: los 75 muros equivalentes (curva W_DPRIME_OPENING_TO_3 representativa).

### Controles de cámara

- Click izquierdo + arrastrar: rotar
- Click derecho + arrastrar: pan (desplazar)
- Rueda del mouse: zoom
- Botones toggles en panel superior: Columnas, Vigas, Muros, Apoyos, Diafragmas, Nodos, IDs, Ejes locales

## Notas técnicas

- Las fuerzas internas están en **coordenadas locales** del elemento: [N, Vy, Vz, T, My, Mz] × 2 extremos.
- El mapping de ejes globales → Unity es: X→x, Y→z, Z→y (el eje vertical del edificio es Z global, Y de Unity).
- Los muros equivalentes son visualizaciones de las paredes de la estructura real (grosor 0.2–0.25 m). La curva P-M es representativa.
- El edificio completo integra edificio 1 + edificio 2, incluyendo los muros equivalentes del edificio 2.
