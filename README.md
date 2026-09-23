# Proyecto MCOC — Grupo 4 (entrega final autocontenida)

Modelo estructural de un edificio de hormigón armado (H-30): análisis
OpenSees/Python + viewer Unity **en una sola carpeta autocontenida
(`Proyecto1/`)**. No requiere ningún directorio externo.

## Estructura (entrega final)

```text
Proyecto1/
├─ scripts/                          # 6 scripts Python (todo autocontenido)
│  ├─ carga_viva_sismo.py            # cargas vivas + sísmicas (OpenSees)
│  ├─ exportar_resultados_unity.py   # JSON enriquecido -> Unity (pipeline P1L4)
│  ├─ exportar_excel_esfuerzos.py    # esfuerzos por elemento -> .xlsx
│  ├─ extraer_indicadores.py         # indicadores por escenario (despl., muros)
│  ├─ anadir_arriostres_unity.py     # arriostres diagonales en voladizos (Unity)
│  └─ verificar_superposicion.py     # verificación numérica de superposición C1/C2/C3
├─ data/                             # JSON base + resultados Unity (autocontenido)
│  ├─ estructura_completo_unity.json
│  ├─ part_e_wall.json
│  └─ semana3_resultados_unity.json
├─ edificio_G4/                      # Proyecto Unity (visualizador P1L4)
│  └─ Assets/Resources/estructura_p1l4_unity.json
├─ resultados/                       # esfuerzos_por_elemento.xlsx
├─ INFORME_SEMANA5.md                # → informe completo de esta entrega
└─ README.md                         # este archivo
```

## Nota: todas las rutas son relativas a `Proyecto1/scripts` y `Proyecto1/data`

Los scripts fueron consolidados para que el repo sea **autocontenido**: ya no
dependen de las carpetas viejas (`P1L2`, `P1L3`, `semana_pasada_marco_2d`,
`edificio_2`) que fueron **eliminadas** del repositorio en esta entrega.

## Checklist de la entrega (Semana 4/5)

Estado: **todas las funciones de la tabla están implementadas** (ver detalle
en `Proyecto1/INFORME_SEMANA5.md`):

| Pregunta UX estructural | Cómo la responde el viewer |
|---|---|
| ¿Dónde está cada elemento? | Selección por clic → panel ID, nodos, sección, material, ejes locales, trazabilidad OpenSees/Unity |
| ¿Está apoyado? | Apoyos visuales + restricciones en panel de selección |
| ¿Qué lo carga / a quién carga? | Cargas D/L/combinaciones, áreas tributarias por losa y resumen por piso |
| ¿Cómo se deforma? | Modo deformada (real, escala relativa a la altura del edificio) |
| ¿Qué fuerzas tiene? | Diagramas axial/corte/momento por elemento con valores del combo activo |
| ¿Cuánta capacidad tiene? | Curvas P-M (columna `COL70/70_FIBER`, muro `W_DPRIME_*`) con punto de demanda real |

### Datos verificados

```text
Nodos: 553 · Elementos: 462 · Columnas: 129 · Vigas: 333 · Muros: 75
Apoyos: 30 · Losas: 226 · Combinaciones: C1, C2, C3
Registros de desplazamiento: 1659 · Fuerzas internas: 1386 · Curvas P-M: 2
Muros con demanda P-M: 75/75
```

## Modificaciones completas (2) — reproducibles con un solo comando

Cada modificación sigue el flujo completo interfaz/dato → modelo → OpenSees →
resultados → Unity y queda **reproducible** porque los scripts son autocontenidos:

| Mod | Qué cambia | Comando (reproducción) |
|---|---|---|
| **A** | Carga viva Q: 500 → 600 kg/m² (+20 %) | `python -X utf8 Proyecto1\scripts\exportar_resultados_unity.py --q-kg-m2 600` |
| **B** | Coeficiente sísmico C: 0.20 → 0.30 (+50 %) | `python -X utf8 Proyecto1\scripts\exportar_resultados_unity.py --sc 0.30` |

Resultados (verificados contra OpenSees):

- **Mod A (Q=600):** desplazamiento máx C1 `0.0360 → 0.0381 m` (+5.7 %); muro 1 — P `442.6 → 467.6 kN` (+5.6 %), V `37.6 → 39.7 kN` (+5.7 %).
- **Mod B (C=0.30):** muro 1 — V `37.55 → 56.33 kN` y M `600.8 → 901.2 kN·m` (+50.0 %, escala exacta con `C`); desplazamiento nodo 114 +52.9 %. Solo las fuerzas sísmicas cambian (P por gravedad se conserva).
- **Restauración determinista:** el mismo comando reproduce byte a byte el estado base (SHA256 idéntico).

## Superposición (verificada numéricamente, 3 estados)

El viewer muestra 3 estados (C1/C2/C3) que **se verificaron contra la corrida
directa** de OpenSees con `verificar_superposicion.py` (exactitud máquina,
error `~1e-11`):

```text
C1: G+0.5Q+0.3EX+0.2EY   C2: G+0.5Q+0.3EX−0.2EY   C3: G+0.5Q−0.3EX+0.2EY
```

## Sidequest: carga móvil

**No implementada en esta entrega** (documentada como pendiente en
`Proyecto1/INFORME_SEMANA5.md` §4). Regla física propuesta: carga concentrada
`P` recorriendo cada viga entre nodos i-j (`s ∈ [0,L]`), reanálisis OpenSees por
posición, reparto por equilibrio y verificación de conservación `ΣR_z = P`.

## Ejecutar

Regenerar el JSON enriquecido para Unity (mismo comando usado en la
verificación de superposición):

```bat
python -X utf8 Proyecto1\scripts\exportar_resultados_unity.py
```

Exportar esfuerzos a Excel (caso y combinación por elemento):

```bat
python -X utf8 Proyecto1\scripts\exportar_excel_esfuerzos.py
```

Salida: `Proyecto1/resultados/esfuerzos_por_elemento.xlsx` (requiere `openpyxl`).

Abrir el viewer en Unity:

```text
Proyecto1/edificio_G4   (escena StructureViewerScene; carga estructura_p1l4_unity.json)
```

Verificar superposición (7 análisis G/Q/EX/EY + C1/C2/C3 vs OpenSees):

```bat
python -X utf8 Proyecto1\scripts\verificar_superposicion.py
```

## Limitaciones conocidas

- El edificio 2 está solo en la geometría unificada del JSON; el análisis
  estructural físico (esfuerzos, muros, desplazamientos) corresponde al edificio 1.
- Muros = muros equivalentes (H-30, banda); demanda P-M con reparto sísmico
  proporcional a `t·L`; fuera de plano despreciado.
- `E` secante por material (p. ej. 25 GPa) documentado; curvas P-M H-30.

## Dependencias

```text
pip install -r requirements.txt   (openseespy, numpy, openpyxl)
```
