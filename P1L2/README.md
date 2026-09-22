# P1L2 — Edificio de Ingeniería UANDES unificado

Escena Unity que une el **edificio 1** y el **edificio 2** (ambos modelos del mismo
edificio de Ingeniería UANDES) en una sola pieza continua, como un único edificio.

## Conexión

- **Edificio 2 a la izquierda**: se traslada con `OFFSET_X = -41.524` para que su
  cara X+ (frontal, donde están sus ascensores, X ≈ 28.8–31.5) quede pegada a la
  cara X− del edificio 1 (X = −10, opuesta al voladizo X+ donde están los ascensores).
- **Cara de contacto**: `X = -10`. Ambos comparten esa línea (36 nodos en contacto),
  con los núcleos de ascensores contiguos, dando la sensación de un solo edificio.
- **Y**: sin desplazamiento (`OFFSET_Y = 0`), alineados.
- **Z**: `OFFSET_Z = 0.05` para alinear por **piso 1** (el CIELO_1 del edificio 2,
  Z = −0.05, pasa a Z = 0, igual que el edificio 1).

## Rangos finales

- **X**: [−41.524, 40.0]
- **Y**: [−11.37, 16.15]
- Nodos: 373 · Elementos: 417 · Losas: 226 · Muros: 30 · Apoyos: 30

## Generación

El JSON unificado se produce con `scripts/unificar_edificios.py`, que:

1. Carga el JSON del edificio 1 (`estructura_edificio1_unity.json`, formato altas
   con `walls`/`slabs` reales) y del edificio 2 (`estructura_edificio_ingenieria_unity.json`,
   formato `rigidDiaphragms`).
2. Traslada el edificio 2 (offsets X/Y/Z) y remapea los IDs de sus nodos.
3. Convierte los `rigidDiaphragms` del edificio 2 a `slabs` (formato del edificio 1).
4. Fusiona `nodes`, `elements`, `walls`, `supports`, `slabs`, `pointLoads`,
   `tributaryList`.
5. Exporta el resultado a `resultados/estructura_completo_unity.json` y lo copia a
   `unity_visualizador/Assets/Resources/estructura_completo_unity.json`.

## Cómo abrir en Unity

1. Abrir el proyecto `P1L2/unity_visualizador/` con Unity 6000.5.10f1.
2. Abrir la escena `Assets/Scenes/StructureViewerScene.unity` (apunta al JSON
   unificado vía su GUID).
3. Pulsar **Play**. El edificio completo (edificios 1 y 2 conectados) se visualiza.

Unidades: kN y metros.
