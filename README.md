# MCOC P1_G4 — Edificio G35: OpenSees + Unity + AR

Modelo estructural de dos edificios de hormigón armado G35, con perfiles metálicos A36. El edificio 1 sale de los planos 2017_67 y el edificio 2 de los planos 2024_22. Están separados por una junta de dilatación.

El cálculo lo hace OpenSees desde Python. Unity sirve como pre y postprocesador, y sobre Unity corre una app de realidad aumentada para Android.

**Flujo:** planos DXF → modelo JSON (`Proyecto1/data`) → OpenSees (`Proyecto1/scripts`) → resultados JSON → viewer Unity y AR (`Proyecto1/edificio_G4`).

**Informes:** el final está en `reports/final.md` y los semanales en `reports/semana02` a `semana06.md`.

## Requisitos

| Componente | Versión probada |
|---|---|
| Windows | 10 / 11 (64 bits) |
| Python | **3.12.10**, en el PATH como `python` |
| OpenSeesPy | **3.8.0.0**. Todas las dependencias van con versión fija en `requirements.txt` |
| Unity | **6000.6.0f1**, con los módulos Android Build Support y Windows Build Support (IL2CPP) |
| Paquetes Unity | AR Foundation 6.6.2, Google ARCore XR Plugin 6.6.2 y XR Management 4.7.0. Unity los instala solo al abrir el proyecto |
| Teléfono (AR) | Android compatible con ARCore. Se probó con un Samsung Galaxy S24 |

```bat
python -m pip install -r requirements.txt
```

## Cómo usarlo

`Ejecutar.bat` abre un menú con todo lo de esta sección, e instala las dependencias si faltan. Los comandos equivalentes, desde la raíz del repo, son los siguientes.

**1. Analizar y generar resultados.** Corre G, Q, EX, EY y C1 a C3 en OpenSees, calcula la capacidad ACI 318 y escribe el JSON que lee Unity:

```bat
python -X utf8 Proyecto1\scripts\exportar_resultados_unity.py
```

- Los parámetros se leen de `Proyecto1/data/parametros_analisis.json`: Q, Q de cubierta, q_G, sismo NCh433 y rigidez fisurada.
- Las combinaciones se leen de `combinaciones.json` y las armaduras de `armaduras.json`. Los argumentos de consola tienen prioridad, por ejemplo `--q-kg-m2 300`, `--suelo D` o `--sc 0.2`; `--help` muestra todos.
- La salida es `Proyecto1/edificio_G4/Assets/Resources/estructura_p1l4_unity.json`. Incluye en `corrida` el comando, las versiones y el hash de cada entrada.
- Si una entrada no es válida, el script termina con código 2 y escribe `ERROR de validacion: …`.

**2. Reconstruir el modelo desde los planos.** Parte del respaldo `estructura_completo_unity.pre_planos.json`, aplica los 16 ajustes y vuelve a exportar:

```bat
python -X utf8 Proyecto1\scripts\ajustar_modelo_planos.py
```

Los ejes de grilla se leen de los DXF, que no están en el repo (carpeta `../Planos_1_dxf`):

```bat
python -X utf8 Proyecto1\scripts\generar_ejes_grilla.py
python -X utf8 Proyecto1\scripts\extraer_armaduras_planos.py
```

El segundo lee las elevaciones 300-310 (2017_67) y 300-305 (2024_22). Saca las barras de cada viga (cantidad, diámetro, capa, inicio y fin) y las mallas y barras de borde de cada muro, y las escribe en `Proyecto1/data/armaduras_planos.json`, que sí está en el repo. Las vigas y muros que no aparecen en ninguna elevación usan la armadura tipo de `armaduras.json`, que está marcada como supuesta.

**3. Ejecutar los tests y el QA.**

```bat
python -m pytest                  :: 50 tests, unos 40 s
python -m pytest -m "not lento"   :: sin las corridas completas del exportador, unos 10 s
python -X utf8 Proyecto1\scripts\qa_semana06.py          :: evidencia en Proyecto1/resultados/qa_semana06.json
python -X utf8 Proyecto1\scripts\sensibilidad_rigidez.py :: sección bruta vs fisurada
```

Lo que cubren los tests:

| Archivo | Verifica |
|---|---|
| `test_modelo.py` | Equilibrio, superposición, unidades, ejes locales, junta sin nodos compartidos, diafragmas |
| `test_cargas.py` | Conservación del área tributaria, Q por nivel, peso sísmico, C de la NCh433 calculado a mano |
| `test_capacidad.py` | Convergencia del M-φ, puntos ACI de la P-M de columna, Whitney vs fibras, flexión de viga a mano, P-M de diseño de muro a mano (malla y barras de borde) |
| `test_planos.py` | Barras de la viga E1_62 leídas de los planos y su φMn a mano, caras de apoyo, mapeo de las elevaciones, rótulos de malla y barras de borde en esquinas |
| `test_unity_json.py` | Integridad del JSON de Unity, que coincida con OpenSees y la trazabilidad de la corrida |
| `test_h4_reanalisis.py` | Validación de entradas y comparación del reanálisis de Unity con la corrida directa |
| `test_h5_armadura.py` | Que un cambio de armadura regenere la curva P-M y baje el DCR |

**4. Abrir el viewer.**

- **Editor:** abrir `Proyecto1/edificio_G4` con Unity 6000.6.0f1 (o `Abrir_Unity.bat`, que usa `-force-d3d11`), cargar la escena `Assets/Scenes/StructureViewerScene` y presionar Play.
- **Ejecutable de Windows:** `Proyecto1/edificio_G4/Builds/Windows/P1G4_Viewer.exe`, que viene en la release. Para regenerar las capturas de la demo: `P1G4_Viewer.exe -autoshot <carpeta> -demo`.
- **Pestañas:**
  - VISTA: capas de ejes, diafragmas, cargas, apoyos y tributarias.
  - RESULTADOS: diagramas, deformada, superposición y utilización.
  - CARGAS: carga móvil y carga en un elemento.
  - MODIFICAR: armadura, sección y quitar elemento.
  - ANÁLISIS: parámetros, sismo y combinaciones, más *Reanalizar*, que llama a Python y OpenSees.

**5. Compilar para el teléfono.** Desde los menús del editor de Unity:

| Menú | Salida |
|---|---|
| `MCOC/Build Android (APK)` | `Builds/Android/P1G4_Viewer.apk` |
| `MCOC/AR/Build Android AR (APK)` | `Builds/Android/P1G4_AR.apk` |
| `MCOC/Build Windows (viewer)` | `Builds/Windows/P1G4_Viewer.exe` |

También se puede compilar por consola, con Unity cerrado:

```bat
Unity.exe -batchmode -quit -force-d3d11 -projectPath Proyecto1\edificio_G4 -executeMethod BuildAndroid.BuildAR
```

Para instalar en el teléfono: `adb install -r P1G4_AR.apk`.

**AR:**
1. Imprimir `Proyecto1/ar/marcador_E1_243_imprimir.pdf` al 100 %. El cuadrado debe medir 20 cm.
2. Pegarlo en la cara +X de la columna **E1_243** (eje F-3, sala del voladizo), con el centro a 1,20 m del piso.
3. Los modos son 1:1 sobre la columna, maqueta 1:100 y sobre el plano.

Si se cambia el marcador: `python -X utf8 Proyecto1\scripts\generar_marcador_ar.py`, luego el menú `MCOC/AR/Actualizar marcador` y volver a compilar el APK.

## Modelo vigente

```text
Nodos 722 · elementos 1023 (398 vigas, 129 columnas, 10 arriostres, 91 muros como columna ancha, 395 brazos rígidos)
Apoyos 78 · paneles de losa 239 · niveles −3.96 / 0 / 3.96 / 7.92 / 11.88 / 15.84 m (z = 0 en cielo 1S)
G = 75 701 kN · Q = 25 886 kN (500 kg/m² en pisos, 200 kg/m² en cubierta)
Sismo NCh433 estático (zona 3, suelo C, R = 7, I = 1, P = D + 0.25Q): corte basal EX 9 174 kN · EY 6 640 kN
Rigidez fisurada ACI 318-19: vigas 0.35 Ig, columnas 0.70 Ig, muros 0.35 Ig
Armadura: 319 vigas y 81 muros con las barras de los planos; 79 vigas, 10 muros y las columnas con armadura tipo supuesta
Capacidad ACI 318-19: vigas DCR ≤ 0.87 (sección por sección, en la cara de los apoyos); columnas DCR ≤ 0.83; muros C ≤ 0.82
```

Las limitaciones están en `reports/final.md`, sección 19.

## Estructura

```text
Proyecto1/
├─ scripts/        carga_viva_sismo.py (núcleo OpenSees), exportar_resultados_unity.py, ajustar_modelo_planos.py,
│                  capacidad_ha.py (ACI 318), validacion_entradas.py, qa_semana06.py, generar_ejes_grilla.py,
│                  extraer_armaduras_planos.py, generar_marcador_ar.py, quitar_elemento.py, carga_movil.py, ...
├─ data/           modelo, parámetros, combinaciones, armaduras (tipo y de los planos), ejes de grilla
├─ edificio_G4/    proyecto Unity (viewer + AR); resultados en Assets/Resources/
├─ ar/             marcador AR para imprimir
└─ resultados/     evidencia del QA, sensibilidad y Excel de esfuerzos
tests/             suite pytest
reports/           informes (final.md y semanales)
```
