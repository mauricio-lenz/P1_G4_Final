# Guía maestra de la demo — Unity, AR y defensa

**Grupo 4 · P1_G4** · Matías Campos · Iván González · Mauricio Lenz
**Demo:** miércoles 7 de octubre de 2026 · modelo vigente del commit `ca0dca8`

Esta guía es para preparar y hacer la demo, y para responder la defensa individual. El profesor puede preguntarle a **cualquiera** por **cualquier** parte, así que los tres deben leerla completa, no solo su parte del guion.

Se usa así:

- **Sección 1:** lo que hay que revisar antes de entrar.
- **Secciones 2 a 6:** qué calcula cada parte del sistema y cómo. Es la base para responder.
- **Sección 7:** el guion de la demo, ítem por ítem, con los clics y las cifras esperadas.
- **Sección 8:** qué hacer si algo falla.
- **Sección 9:** preguntas probables con su respuesta corta.
- **Sección 10:** las cifras clave en una sola tabla.

---

## 1. Antes de la demo (checklist)

**El día anterior o en la mañana:**

- ☐ Notebook con el repo al día: `git pull`. El último commit debe ser `ca0dca8` o posterior.
- ☐ `python -m pytest -m "not lento"` en verde. Confirma que Python, OpenSeesPy y los datos están bien.
- ☐ Abrir `Proyecto1\edificio_G4\Builds\Windows\P1G4_Viewer.exe` y **ensayar cada función que llama a Python**: *Reanalizar* con Q = 300 (unos 11 s), *Quitar* E1_243 (unos 15 s) y *Carga en elemento*. Si alguna falla, ver la sección 8.
- ☐ Teléfono S24 cargado, con las apps **P1_G4 AR** y **P1_G4 Viewer** instaladas (ya están).
- ☐ Marcador impreso al 100 %: el cuadrado debe medir **20,0 cm** con regla. Llevar cinta para pegarlo.
- ☐ Probar la AR en la sala del voladizo: el marcador va en la cara +X de **E1_243** (hacia la sala), con el centro a **1,20 m** del piso.
- ☐ Tener abiertos el PDF del informe y esta guía, por si preguntan algo puntual.

**En la sala, 5 minutos antes:**

- ☐ Pegar el marcador y probar el anclaje en modo 1:1.
- ☐ Abrir el viewer en el notebook, en vista ISO, combinación C1 y *Sin diagrama*.
- ☐ Cerrar otros programas: el reanálisis usa CPU.

---

## 2. El flujo completo (lo que cualquiera debe saber explicar)

```text
planos DXF → datos JSON → OpenSees (Python) → resultados JSON → Unity (viewer) → AR (teléfono)
```

| Etapa | Qué pasa | Archivo o script |
|---|---|---|
| **Planos** | Plantas y elevaciones DXF de 2017_67 (edificio 1) y 2024_22 (edificio 2) | `Planos_1_dxf/` (fuera del repo) |
| **Datos** | Modelo con 16 ajustes contrastados con los planos; 40 ejes de grilla; armadura de 319 vigas y 81 muros leída de las elevaciones | `ajustar_modelo_planos.py`, `generar_ejes_grilla.py`, `extraer_armaduras_planos.py` → `Proyecto1/data/*.json` |
| **OpenSees** | Modelo 3D, cargas G y Q por área tributaria, sismo NCh433 (modal, centro de masa, torsión accidental), casos G, Q, EX, EY y combinaciones C1 a C3; capacidad ACI 318-19 y DCR | `carga_viva_sismo.py` (núcleo), `capacidad_ha.py`, `exportar_resultados_unity.py` |
| **Resultados** | Un solo JSON con nodos, elementos, desplazamientos, fuerzas por caso y combinación, curvas P-M, capacidad y trazabilidad | `Assets/Resources/estructura_p1l4_unity.json` |
| **Unity** | Muestra, interpola y combina esos resultados; para cambiar el modelo, vuelve a llamar a Python | proyecto `Proyecto1/edificio_G4` |
| **AR** | Lee **el mismo JSON** y lo dibuja anclado al marcador de E1_243 | `P1G4_AR.apk` |

**Idea central para la defensa:** OpenSees calcula y Unity muestra. El teléfono nunca corre OpenSees. Cuando se modifica algo en Unity, no se recalcula en Unity: se le pide a Python que haga un análisis nuevo.

---

## 3. Qué calcula Unity y qué calcula Python

Es la pregunta más probable sobre Unity. Hay que saber trazar el límite con precisión.

| Lo calcula **Python / OpenSees** (en el PC) | Lo calcula **Unity** (en vivo, en C#) |
|---|---|
| Geometría, apoyos, rigidez fisurada y diafragmas | Interpolación de los esfuerzos a lo largo de cada barra: N, V y M entre los extremos de OpenSees, más el efecto de la carga repartida del tramo |
| Áreas tributarias y cargas G y Q | Superposición en vivo: SUP = λG·G + λQ·Q + λEX·EX + λEY·EY, con los esfuerzos y desplazamientos de los casos base |
| Sismo NCh433: modal, T*, C, Q0, A_k, centro de masa y torsión accidental | Deformada y flecha de cada barra: Hermite con los desplazamientos y giros de OpenSees en sus nodos, más la flecha de la carga repartida del tramo, q·x²(L−x)²/(24EI); se dibuja con escala automática (5 % de la altura del edificio) |
| Análisis lineal de cada caso y combinación | Punto de demanda P-M: N al centro de la barra y |M| resultante máximo en I, ½ y J, del caso activo |
| Curvas P-M de diseño (ACI 318-19) de columnas y muros, y sección de fibras | Color por utilización (lee el DCR que calculó Python) |
| Capacidad y DCR de cada viga, columna y muro | Carga móvil: combina casos unitarios precalculados con las fuerzas de empotramiento de la viga cargada |
| Validación de entradas | Carga en un elemento: combina 12 casos unitarios del elemento, calculados por OpenSees al elegirlo |

**Por qué la superposición en vivo es válida:** el análisis es lineal (elementos elásticos, pequeñas deformaciones), así que cualquier combinación de casos es la suma ponderada de los casos base. Lo verificamos: C1 a C3 resueltas directamente en OpenSees son iguales a Σ λ · caso base, con un error de 2,4·10⁻⁹.

**Límite de la superposición en vivo:** recombina esfuerzos, deformada y punto P-M, pero no recalcula el DCR. El color de utilización muestra el DCR de las combinaciones C1 a C3 calculadas por Python.

---

## 4. La interfaz

### 4.1 Barra superior

| Control | Qué hace |
|---|---|
| **Caso:** G · Q · EX · EY · C1 · C2 · C3 | Elige el caso base o la combinación activa. Todo lo que se dibuja usa ese caso. Al pasar el mouse sobre una combinación se ve su fórmula |
| **Resultado:** Sin diagrama · Axial N · Corte V · Momento M · Deformada | Elige qué se dibuja (atajos: teclas 0 a 4) |
| **Buscar** | Escribir un id o tag (E1_243, E1_72, MURO-013) y Enter: selecciona el elemento y centra la cámara |
| **ISO · TOP · FRONT · RIGHT** | Vistas fijas de cámara |
| Línea de estado | Mensajes de cada acción y, con SUP activa, la combinación en uso |

**Cámara:**

- **Clic:** seleccionar.
- **Clic derecho y arrastrar:** orbitar.
- **Rueda:** zoom.
- **Flechas:** mover.
- **Teclas + y −:** cambiar la escala del diagrama.

### 4.2 Panel del elemento seleccionado

Al hacer clic en una barra se abre el panel de la derecha:

| Bloque | Qué muestra |
|---|---|
| Identificación | id de Unity, elementTag de OpenSees, nodos I y J, piso, edificio |
| Sección y material | sección, G35 o A36, f'c, f_y |
| Restricciones | si sus nodos tienen apoyo |
| Ejes locales | x', y', z' en coordenadas globales |
| Fuerzas en el punto clicado | N, V, T y M interpolados en x/L, del caso activo |
| Esfuerzos en los extremos | los 12 valores de OpenSees en ejes locales |
| **Desplazamientos** | ux, uy, uz y \|u\| en mm de los nodos I y J (OpenSees) y, en vigas, la **flecha respecto de sus apoyos**: valor, posición y L/δ, del caso activo |
| Cargas tributarias | área tributaria y carga de losa (vigas) |
| Demanda-capacidad | P y M del punto de demanda y curva P-M (columnas y muros) |
| Armadura y capacidad | fuente de la armadura (planos o tipo), barras, φM_n, φV_n, DCR y combinación gobernante, con su variante de torsión accidental, por ejemplo "C1 (−TX −TY)" |
| Trazabilidad | de qué JSON y de qué elemento de OpenSees salen los datos |

En columnas y muros se abre además el **diagrama P-M**: la curva de diseño, el punto de demanda del caso activo y C = M/φM_n.

---

## 5. Pestaña por pestaña

### 5.1 VISTA

| Control | Qué muestra | Cómo se calcula / qué decir |
|---|---|---|
| **Capas:** columnas, vigas, muros, apoyos, losas, nodos, IDs, ejes locales | Cada familia de elementos | Geometría del JSON del modelo (722 nodos, 1 023 elementos) |
| **Apoyos** | Los 78 empotramientos | En la cota de fundación; el suelo no se modela |
| **Ejes** | 40 ejes de grilla con sus burbujas | Leídos de las plantas DXF y llevados al sistema del modelo |
| **Diafragmas** | Un diafragma por edificio y piso, con su nodo maestro y su centro de masa | Diafragma rígido; el sismo de cada piso se aplica en el centro de masa |
| **Cargas** | G y Q repartidas en las vigas, EX o EY en cada diafragma, según el caso activo | La línea bajo las capas resume las cargas del caso |
| **Piso** | Filtra un piso | — |
| **Áreas tributarias por piso** | Área y carga de losa por piso y edificio | Polígonos tributarios de cada panel de losa; total 6 136,8 m², igual al área de losa |

### 5.2 RESULTADOS

| Control | Qué muestra | Cómo se calcula / qué decir |
|---|---|---|
| **Plano de flexión:** Auto · xz · xy | Qué momento se dibuja (My o Mz) | Ejes locales de cada barra; *Auto* elige el plano principal |
| **Vigas / Columnas y arriostres** | Filtra qué barras llevan diagrama | — |
| **Escala** (×0,1 a ×10) | Tamaño del diagrama | Escala común a todo el modelo: el tamaño compara barras entre sí |
| **Etiquetas** | Valores máximos o del elemento seleccionado | — |
| **Animar la deformada** | Animación de la deformada | — |
| **Convención** | Azul: M+ (tracciona abajo), N tracción, V+. Naranjo: M−, N compresión, V− | El momento se dibuja del lado traccionado |
| **Colorear por utilización** | Verde C ≤ 0,7 · amarillo C ≈ 1 · rojo C > 1 | Usa el DCR de Python para la combinación activa. Con C1 a C3 todo queda verde o amarillo |
| **Superposición en vivo** | Sliders λG, λQ, λEX, λEY (−3 a 4), botones *λ = 1* y *Solo G* | SUP = Σ λ · caso base, al instante y sin reanalizar (sección 3) |

**Truco para la demo:** con la superposición activa y λ = (1; 0,5; 0,3; 0,2), SUP reproduce exactamente C1. Es la forma más clara de mostrar que la superposición funciona.

### 5.3 CARGAS (no reanaliza el modelo completo)

| Función | Qué hace | Cómo se calcula |
|---|---|---|
| **Carga móvil** | Una carga P (50 kN por defecto, editable) recorre el eje 2 del piso y edificio elegidos; se puede animar | El exportador precalcula con OpenSees la respuesta a cargas unitarias en cada nodo del recorrido. Unity reemplaza P por sus fuerzas de empotramiento en la viga que la contiene (F_A = P·b²(3a+b)/L³, M_A = P·a·b²/L², …) y combina. El panel muestra Σ R_z = P |
| **Carga en un elemento** | Carga puntual o repartida en un tramo x1–x2, en −Z, X o Y, sobre el elemento elegido | Al elegir el elemento, `carga_elemento.py` corre en OpenSees sus 12 casos unitarios; después Unity combina en vivo cualquier magnitud y posición. Es exacto porque el modelo es lineal |

### 5.4 MODIFICAR

| Función | Qué hace | Qué pasa por dentro |
|---|---|---|
| **Armadura (ACI 318)** | Cambiar las barras de la viga o columna seleccionada (*Aplicar al elemento*) o de toda su sección (*Aplicar a la sección*); luego *Reanalizar ahora* | Se escribe un archivo de cambios de armadura y se reanaliza. Python regenera la curva P-M y el DCR (Honors H5). Si la viga tenía armadura de los planos, el panel avisa que el cambio la reemplaza |
| **Cambiar sección** | Nueva b × h para una viga o columna; *Agregar cambio* y reanalizar en ANÁLISIS | Cambia la rigidez en OpenSees (no solo el nombre) y el peso propio |
| **Quitar elemento** | Uno o varios elementos por tag o clic; *Quitar y analizar* | `quitar_elemento.py` reanaliza G, Q, EX, EY y C1 a C3 sin esos elementos. Su losa sigue cargando a los vecinos y se descuenta su peso propio. Unity reemplaza los resultados **en memoria**: diagramas, deformada y P-M. *Comparar deformada* muestra la original en naranjo, y *Restaurar modelo original* vuelve atrás. No modifica archivos |

### 5.5 ANÁLISIS

| Bloque | Qué hace |
|---|---|
| **Modelo** | Conteos del modelo cargado |
| **Parámetros de carga** | q_G (6,227 kN/m²), Q de pisos (500 kg/m²) y Q de cubierta (200 kg/m²) |
| **Sismo** | Método NCh433 o C fijo; zona, suelo, R, I y fracción de Q en P |
| **Rigidez** | Factores de inercia por tipo; botones *ACI fisurada* (0,35 / 0,70 / 0,35) y *Sección bruta* |
| **Combinaciones** | Editar λ, agregar o quitar combinaciones |
| **Cambios de sección y armadura** | Lista de lo pendiente desde MODIFICAR |
| **Reanalizar el modelo completo** | Corre Python y OpenSees con todo lo anterior (sección 6.1) |
| **Verificación del análisis cargado** | G aplicada = Σ R_z, Q aplicada = Σ R_z, corte basal, T*, C y Q0 de cada edificio, DCR máximos y |u| máximo de cada caso |
| **Escenario sin guardar** | *Guardar como modelo vigente* o *Descartar* |

---

## 6. Las funciones que llaman a OpenSees

### 6.1 Reanalizar (Honors H4)

1. Se editan los parámetros en ANÁLISIS y, si se quiere, secciones y armaduras en MODIFICAR.
2. Unity valida rangos básicos. Si algo está fuera de rango, lo dice y no lanza nada.
3. Escribe en la carpeta temporal `combos_unity.json`, `mods_unity.json` y, si hay cambios de armadura, `armaduras_unity.json`.
4. Lanza `python -X utf8 exportar_resultados_unity.py` con los argumentos: `--q-kg-m2`, `--q-cubierta-kg-m2`, sismo, `--qG`, `--combos`, `--mods`, `--fisurada` y `--armaduras`. La salida va a `--out escenario_unity.json`.
5. Python valida todo con `validacion_entradas.py`. Si hay un error, termina con **código 2** y "ERROR de validación: …", que Unity muestra tal cual, y no se calcula nada.
6. Si todo está bien, OpenSees resuelve todo de nuevo. Es el mismo programa que genera el modelo vigente: tarda unos **11 s** y el botón muestra los segundos.
7. Unity carga el resultado como **escenario sin guardar**. *Descartar* vuelve al modelo vigente. *Guardar como modelo vigente* lo copia a `Assets/Resources` y escribe `data/combinaciones.json` y `data/parametros_analisis.json`, así que la consola da después el mismo resultado.

**Cómo sabemos que el reanálisis está bien** (tests de `test_h4_reanalisis.py`):

- con los argumentos de Unity da lo mismo que OpenSees directo;
- con Q = 300 kg/m², la reacción de Q coincide con el cálculo directo;
- las 7 entradas inválidas se rechazan.

### 6.2 Quitar elemento

Ver la sección 5.4. Para la demo usamos **E1_243**, la columna del marcador y de la sala, en el piso 2. Resultados esperados:

| Resultado | Original | Sin E1_243 |
|---|---|---|
| Descenso del nodo que sostenía, con G | 1,2 mm | **22,4 mm** |
| Momento máximo de la viga E1_84, con C1 | 186 kN·m | **833 kN·m** |
| G aplicada = Σ R_z | 75 700,9 kN | 75 652,4 kN (sale su peso propio, 48,5 kN) |

**Qué decir:** "Al quitar la columna, el nodo que sostenía queda colgado de las vigas: baja 20 mm más y los momentos de las vigas vecinas se multiplican. El equilibrio se mantiene sin pérdida de carga: la losa sigue cargando a los vecinos."

**Ojo:** en este modo cambian los esfuerzos, pero el color de utilización sigue mostrando el DCR del modelo original.

### 6.3 Carga en un elemento

Elegir, por ejemplo, la viga E1_72, la de borde del voladizo, y aplicar una carga puntual de 100 kN al centro, en −Z. El diagrama de momento muestra el quiebre bajo la carga y el de corte, el salto.

### 6.4 Si el profesor pide cambiar la armadura o la sección de un elemento

**Cambiar la armadura** (vigas y columnas de hormigón):

1. Seleccionar el elemento: clic, o escribir su tag en *Buscar* y Enter (por ejemplo E1_291).
2. Pestaña **MODIFICAR** → bloque **ARMADURA (ACI 318)**. Arriba dice si usa la armadura tipo o las barras de los planos, y muestra su capacidad y DCR actuales.
3. Escribir la armadura nueva:
    - **columna:** *Barras* (por ejemplo `12f25`) y *Estribos* (`EDf12a10`);
    - **viga:** *Inferior*, *Superior*, *Suple apoyo*, *Estribos apoyo* y *Estribos tramo*.

    La notación es `4f22` o `4φ22`, `2f22+2f25`; los estribos, `Ef10a10` (2 ramas) o `EDf10a10` (4 ramas). Solo se envían los campos que cambian.
4. **Aplicar al elemento** (solo ese) o **Aplicar a la sección** (todos los de esa sección con armadura tipo). Aparece en *Pendientes*.
5. **Reanalizar ahora**. El botón cuenta los segundos (unos 11 s).
6. Seleccionar de nuevo el elemento: el panel muestra la armadura nueva, φM_n o φP_max y el DCR nuevo. En una columna, el diagrama P-M muestra la curva regenerada (por ejemplo `COL70/70_12f25`).
7. En **ANÁLISIS**: **Descartar** para volver, o **Guardar como modelo vigente** solo si se quiere conservar, porque sobrescribe los archivos del proyecto.

Cifra esperada: E1_291 de 8φ25 a 12φ25 → DCR de 0,83 a 0,61 (φM_n de 575 a 784 kN·m).

**Cambiar la sección** (vigas y columnas de hormigón):

1. Seleccionar el elemento.
2. **MODIFICAR** → **CAMBIAR SECCIÓN**: elegir una sección del desplegable o escribir *b* y *h* en metros (entre 0,10 y 3,00 m).
3. **Agregar cambio**. Aparece en la lista, por ejemplo "E1_62: V60/80 → V60/60".
4. **Reanalizar** (en ANÁLISIS → *Reanalizar el modelo completo*, o *Reanalizar ahora* en MODIFICAR). Se puede combinar con un cambio de armadura en el mismo reanálisis.
5. Ver el resultado:
    - cambian la rigidez y el peso propio, así que los esfuerzos se redistribuyen;
    - la capacidad se recalcula con las dimensiones nuevas y la misma armadura: la de los planos o, si la sección nueva no tiene armadura tipo, la de su sección original. El panel lo indica con una nota.
6. **Descartar** o **Guardar como modelo vigente**.

Cifras esperadas:
- E1_62 de V60/80 a V60/60 → φM_n⁺ de 1 358 a 913 kN·m (12φ25 con d = 479 mm) y DCR de 0,40 a 0,46.
- E1_72 de V60/80 a V60/100 → DCR de 0,29 a 0,31: la viga es más resistente, pero también más pesada y más rígida, así que atrae más carga.

**Lo que no se edita desde Unity:** la armadura de los muros y las secciones de los muros, pilares metálicos y arriostres. Si se escribe una armadura con mala notación o una dimensión fuera de rango, aparece "ERROR de validación" y no se analiza.

---

## 7. Guion de la demo

Son unos 15 minutos para los 14 ítems de la demo base, más 3 minutos de Honors. La columna "Quién" es una sugerencia: conviene que cada uno presente su parte, pero todos deben poder hacer cualquier ítem.

| # | Ítem del enunciado | Quién | Qué hacer en Unity | Qué decir y qué cifra mostrar |
|---|---|---|---|---|
| 1 | Geometría | Matías | ISO, *Mostrar todo*; girar | Dos edificios separados por junta en x = −10 m; 722 nodos y 1 023 elementos; muros como columna ancha |
| 2 | Apoyos y restricciones | Matías | VISTA → *Apoyos*; clic en una columna de la base → bloque Restricciones | 78 empotramientos en la cota de fundación |
| 3 | Ejes | Matías | VISTA → *Ejes*; vista TOP | 40 ejes leídos de las plantas DXF, principales y secundarios |
| 4 | Diafragmas | Matías | VISTA → *Diafragmas* | Diafragma rígido por edificio y piso; nodo maestro; centro de masa con pesos reales |
| 5 | Áreas tributarias | Matías | VISTA → *Losas* y el listado por piso; clic en una viga → Cargas tributarias | Total 6 136,8 m², igual al área de losa (se conserva) |
| 6 | Cargas G, Q, EX, EY | Matías | VISTA → *Cargas*; caso G, después Q, EX y EY | G = 75 701 kN; Q = 25 886 kN; corte basal EX 9 174 kN y EY 6 640 kN (NCh433) |
| 7 | Deformada | Iván | Caso C1 → *Deformada*; *Animar*; clic en **E1_72** → bloque *Desplazamientos* | Escala automática al 5 % de la altura; \|u\| máximo arriba. En el panel, los mm de cada nodo y la flecha de la viga respecto de sus apoyos |
| 8 | Diagramas | Iván | *Momento M*; buscar **E1_72** | Momento del lado traccionado; panel con los valores de OpenSees en los extremos |
| 9 | Superposición con sliders | Iván | RESULTADOS → *Activar superposición*; λ = (1; 0,5; 0,3; 0,2) | SUP = C1, sin reanalizar; válido porque el análisis es lineal (error 2,4·10⁻⁹) |
| 10 | Curva P-M de columna | Mauricio | Buscar **E1_291** (clic) | Curva de diseño ACI 318-19 de la COL70/70; DCR 0,83, la más exigida |
| 11 | Curva P-M de muro | Mauricio | Buscar **MURO-013** | Curva propia con su malla y las barras de borde del plano (ρ ≈ 2 %) |
| 12 | Punto de demanda | Mauricio | En el panel P-M, cambiar entre C1, C2 y C3 | El punto (P, M) se mueve; C = M/φM_n(P). Colorear por utilización: ningún elemento sobre 1 |
| 13 | Modificación de dos parámetros | Iván y Mauricio | **(a)** ANÁLISIS: Q = 300 → *Reanalizar*. **(b)** MODIFICAR: armadura de E1_291 a 12φ25 → *Reanalizar ahora*. **(c, opcional)** Quitar E1_243 | (a) Q pasa de 25 886 a 16 653 kN y el corte basal EX de 9 174 a 8 914 kN. (b) DCR de E1_291 de 0,83 a 0,61. (c) Sección 6.2 |
| 14 | AR básica | Iván | Teléfono: app **P1_G4 AR** → marcador de E1_243 → modo 1:1 → C1 → tocar **E1_243** o el acceso directo **E1_72** | El modelo queda anclado a la columna real; el panel muestra N, V, M, el desplazamiento y la P-M del mismo JSON que el viewer |
| H4 | Reanálisis en vivo | Matías | Mostrar una entrada inválida: Q = −5 → *Reanalizar* | Unity muestra "ERROR de validación" y no calcula nada; después Q válido → reanálisis de 11 s |
| H5 | Regeneración de la P-M | Mauricio | La del ítem 13b, abriendo la P-M antes y después | La curva crece con más acero y el DCR baja |

**Después de la demo:** en ANÁLISIS → *Descartar* el escenario, para volver al modelo vigente.

---

## 8. Plan B

| Si falla… | Hacer |
|---|---|
| *Reanalizar* no responde o da error | Mirar el mensaje en ANÁLISIS. Si dice que no encuentra Python, abrir una consola y correr `python -X utf8 Proyecto1\scripts\exportar_resultados_unity.py --q-kg-m2 300 --out prueba.json`, mostrando el resultado en la consola. Explicar que es el mismo programa que llama Unity |
| El viewer de Windows se cae al abrir | Abrir el proyecto con `Abrir_Unity.bat` (usa Direct3D 11) y dar Play en `StructureViewerScene` |
| La AR no ancla | Acercarse a 30 a 50 cm con buena luz y sin reflejos sobre el marcador; *RE-ANCLAR*. Si sigue fallando, usar el modo **MAQUETA 1:100** con el marcador sobre una mesa |
| La AR se desplaza al mover el teléfono | *RE-ANCLAR* cerca de la zona que se quiere mostrar (el error crece unos 1,75 cm por metro y por grado) |
| El teléfono no tiene batería o no tiene la app | Mostrar la figura 11 del informe y explicar la cadena con la sección 16 |
| Se pide algo que no está en la demo | Responder con la sección 9 y el informe |

---

## 9. Preguntas probables (defensa individual)

### 9.1 Flujo y modelo

- **¿Cómo pasan los planos al modelo?** Los scripts leen los DXF: ejes, muros, columnas, vigas y armadura de las elevaciones. Los 16 ajustes del modelo se contrastaron con las plantas y elevaciones, y cada uno quedó en `ajustar_modelo_planos.py`, reproducible.
- **¿Por qué los muros son columnas anchas?** Para representar su rigidez en el plano con elementos de barra. Cada paño es una columna en su eje con la sección t × L, unida al marco por brazos rígidos en cada piso.
- **¿Qué es el diafragma rígido?** La losa no se deforma en su plano, así que todos los nodos de un piso se mueven como un cuerpo rígido respecto del nodo maestro. Hay uno por edificio y piso, porque la junta separa los edificios.
- **¿Por qué rigidez fisurada?** Porque con sismo el hormigón se fisura. ACI 318-19 §6.6.3.1.1: vigas 0,35 I_g, columnas 0,70 I_g, muros 0,35 I_g. Con sección bruta los desplazamientos son cerca de 20 % menores.

### 9.2 Cargas y sismo

- **¿Cómo se reparte la losa?** Cada panel se reparte entre las vigas y muros que lo apoyan con su polígono tributario. La suma de las áreas tributarias es igual al área de losa (6 136,8 m²).
- **¿Cómo se calcula el sismo?** NCh433 estático: C = 2,75·S·A0/(g·R)·(T'/T*)ⁿ, acotado entre Cmin y Cmax, con T* del modal de cada edificio. Q0 = C·I·P con P = D + 0,25Q, repartido en altura con A_k.
- **¿Por qué C es distinto en cada edificio?** Porque cada uno tiene su propio T*. El edificio 1 en X queda en Cmax (0,147) y el edificio 2 en Cmin (0,07).
- **¿Por qué los modos del edificio 2 son diagonales?** Es casi igual de flexible en X que en Y (3,3 y 3,5 mm con 100 kN por piso), y sus muros rígidos están junto a la junta, a unos 15 m del centro de masa. La torsión acopla las dos direcciones. No cambia el diseño porque C queda en Cmin.
- **¿Dónde se aplica el sismo?** En el centro de masa de cada piso, calculado con los pesos D + 0,25Q, más la torsión accidental de la NCh433 (±0,10·b·Z/H).
- **¿Cumplen las derivas?** Sí. Deriva máxima en el centro de masa: 1,63 ‰, con límite de 2 ‰. Exceso máximo de un punto sobre el centro de masa: 0,60 ‰, con límite de 1 ‰.

### 9.3 Capacidad

- **¿Cómo se obtiene la curva P-M?** Por compatibilidad de deformaciones: bloque de Whitney, φ entre 0,65 y 0,90 según ε_t, y tope 0,80·φ·P0. La comparamos con una sección de fibras, y coinciden con 2 % de diferencia en flexión pura.
- **¿De dónde sale la armadura?** Para 319 vigas y 81 muros, de las elevaciones de los planos, barra por barra. Para las columnas es una armadura supuesta de 8φ25, porque los planos no traen cuadro de pilares; está bajo el mínimo ACI, así que es conservadora.
- **¿Qué es el DCR?** Demanda / capacidad. En vigas se verifica sección por sección en la cara de los apoyos; en columnas y muros, M/φM_n(P).
- **¿Cumple el edificio?** Con las combinaciones del curso, sí: DCR máximo de 0,87 en vigas, 0,83 en columnas y 0,82 en muros. Con las combinaciones de diseño de la NCh3171, no. Lo mostramos como sensibilidad: el modelo es un laboratorio, no una verificación de diseño del edificio real.

### 9.4 Unity y AR

- **¿Unity calcula algo?** Interpola, combina y escala, pero no analiza (sección 3). Todo lo estructural sale de OpenSees.
- **¿Cómo funciona la AR?** ARCore detecta el marcador y crea un anchor en su pose. Cada nodo pasa al mundo AR con p_AR = T_anchor · s · M · (p − p_ref). La precisión es de unos 5 cm a 1 m del marcador.
- **¿Dónde veo cuánto se deforma un elemento?** En el panel del elemento, bloque *Desplazamientos*: los nodos I y J en mm y, en vigas, la flecha respecto de sus apoyos con L/δ. Por ejemplo, E1_72 con G: 1,85 mm (L/4 060). Coincide con OpenSees partiendo la viga en su punto medio (`test_flecha_de_viga_como_en_unity`). El \|u\| máximo de todo el modelo aparece arriba al elegir *Deformada*.
- **¿Por qué el punto P-M del panel no da exactamente el mismo C que el DCR?** El punto del panel usa los esfuerzos de la combinación tal cual. El DCR incluye además la torsión accidental en su variante más desfavorable, que aparece al lado del DCR, por ejemplo "C1 (−TX −TY)".

### 9.5 El error que cada uno detectó (sección 21 del informe)

| Integrante | Error | Explicación en una frase | Evidencia |
|---|---|---|---|
| **Matías** | El sismo se aplicaba en el centroide de los nodos y no en el centro de masa | En el edificio 1 la diferencia era de 5 m (10 % de la planta); se corrigió con los pesos reales y se agregó la torsión accidental | `test_sismo_en_centro_de_masa` |
| **Mauricio** | El panel de áreas tributarias mostraba 3 180 m² en vez de 6 137 m² | Sumaba solo las vigas del edificio 1; ahora agrupa por edificio y piso | `test_panel_areas_tributarias` |
| **Iván** | Vigas con DCR de 9,99 en el mapa de utilización | El momento se verificaba dentro de la columna; la ACI permite verificar en la cara del apoyo | `test_caras_de_apoyo_E1_62` |

---

## 10. Cifras clave

| Dato | Valor |
|---|---|
| Nodos · elementos · apoyos | 722 · 1 023 · 78 |
| Área tributaria | 6 136,8 m² |
| G · Q | 75 700,9 kN · 25 885,9 kN |
| Corte basal NCh433 EX · EY | 9 174,5 kN · 6 639,8 kN |
| T* edificio 1 (X · Y) · edificio 2 | 0,422 s · 0,684 s · 0,856 s |
| C edificio 1 (X · Y) · edificio 2 | 0,147 (Cmax) · 0,092 · 0,070 (Cmin) |
| Deriva máxima en el centro de masa | 1,63 ‰ (límite 2 ‰) |
| Superposición: error máximo | 2,4·10⁻⁹ |
| DCR máximo con C1 a C3: vigas · columnas · muros | 0,87 · 0,83 · 0,82 |
| Armadura de los planos | 319 vigas · 81 muros |
| Reanálisis completo | unos 11 s |
| Tests | 55, todos en verde |
| AR: registro medido (marcador impreso a 0,39 m) | 10,6 mm · 2,6° · ruido 2,4 mm |
