# Proyecto MCOC — Grupo 4 (entrega final autocontenida)

Modelo estructural de dos edificios de hormigón armado H-30 (edificio 1: planos
2017_67; edificio 2: planos 2024_22; separados por junta de dilatación):
análisis OpenSees/Python + viewer Unity **en una sola carpeta autocontenida
(`Proyecto1/`)**. Informe vigente de la semana 5: [`reports/semana05.md`](reports/semana05.md).

## Estructura

```text
Proyecto1/
├─ scripts/
│  ├─ carga_viva_sismo.py            # modelo OpenSees, cargas, sismo con diafragma rigido
│  ├─ exportar_resultados_unity.py   # 7 analisis (G,Q,EX,EY,C1-C3) -> JSON de Unity
│  ├─ ajustar_modelo_planos.py       # ajustes del modelo segun los planos DXF (reproducible)
│  ├─ verificar_superposicion.py     # verificacion numerica de C1/C2/C3
│  ├─ extraer_indicadores.py         # indicadores por combo
│  ├─ modificar_modelo.py            # modificaciones persistentes del modelo (--restore)
│  ├─ quitar_elemento.py             # reanalisis al quitar elementos (lo usa Unity)
│  ├─ carga_movil.py                 # casos unitarios de la carga movil (sidequest)
│  ├─ carga_elemento.py              # casos unitarios de carga puntual/distribuida en un elemento
│  └─ exportar_excel_esfuerzos.py    # esfuerzos por elemento -> .xlsx
├─ data/
│  ├─ estructura_completo_unity.json            # modelo vigente
│  ├─ estructura_completo_unity.pre_planos.json # respaldo base de ajustar_modelo_planos.py
│  ├─ part_e_wall.json                          # curva P-M del muro
│  └─ semana3_resultados_unity.json             # curva P-M de la columna
├─ edificio_G4/                      # proyecto Unity (escena StructureViewerScene)
│  └─ Assets/Resources/estructura_p1l4_unity.json
└─ resultados/                       # esfuerzos_por_elemento.xlsx
reports/                             # informes semanales (semana02, 03, 05)
```

## Modelo vigente

```text
Nodos: 589 · Elementos: 557 (398 vigas, 149 columnas, 10 arriostres) · Muros: 91
Apoyos: 34 · Paneles de losa: 239 · Niveles: -3.96 / 0 / 3.96 / 7.92 / 11.88 / 15.84 m
Casos: G, Q, EX, EY · Combinaciones: C1, C2, C3
Equilibrio G: 27 878.1 kN aplicados = 27 878.1 kN de reaccion
```

Combinaciones: `C1 = G+0.5Q+0.3EX+0.2EY`, `C2 = G+0.5Q+0.3EX−0.2EY`,
`C3 = G+0.5Q−0.3EX+0.2EY` (Q = 500 kg/m², coeficiente sísmico 0.20). La
superposición se verifica contra la corrida directa de OpenSees con error ~1e-11.

## Viewer Unity

Abrir `Proyecto1/edificio_G4` con Unity 6000.6.0f1 (o `Abrir_Unity.bat`), escena
`StructureViewerScene`, **Play**. Además de navegación, selección, apoyos, ejes,
cargas, tributarias, deformada, diagramas, superposición en vivo y P-M, la
columna izquierda tiene tres paneles:

| Panel | Qué hace |
|---|---|
| Carga móvil | Carga P (editable) que recorre el eje 2 del piso/edificio elegido; exacta y continua |
| Carga en elemento | Carga puntual o distribuida (−Z, X, Y) sobre el elemento elegido por id/tag |
| Quitar elemento | Reanálisis OpenSees sin los elementos indicados; compara con el modelo original |

Carga en elemento y quitar elemento ejecutan Python en segundo plano (requieren
`python` con openseespy en el PATH; solo editor o PC).

## Ejecutar

```bat
python -X utf8 Proyecto1\scripts\ajustar_modelo_planos.py     & rem reconstruye el modelo y re-exporta a Unity
python -X utf8 Proyecto1\scripts\exportar_resultados_unity.py & rem solo re-exporta a Unity
python -X utf8 Proyecto1\scripts\verificar_superposicion.py   & rem verifica C1/C2/C3
python -X utf8 Proyecto1\scripts\exportar_excel_esfuerzos.py  & rem Excel de esfuerzos (requiere openpyxl)
```

## Limitaciones conocidas

- Los muros no están en el análisis OpenSees: se usan para visualización y para
  una demanda P-M estimada (corte de piso repartido por orientación y t·L). Los
  muros que sostienen extremos de vigas sin pilar (ejes A' y D' del edificio 2)
  se modelan como columnas equivalentes de gravedad.
- Los factores de las combinaciones (0.3EX / 0.2EY) están pendientes de revisión
  frente a la norma.
- Pilares metálicos y muros equivalentes no tienen curva P-M propia.

## Dependencias

```text
pip install -r requirements.txt   (openseespy, numpy, openpyxl)
```
