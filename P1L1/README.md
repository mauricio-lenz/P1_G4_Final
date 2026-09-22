# Semana Actual - Benchmark 3D OpenSeesPy

Entregable del laboratorio de benchmark 3D.

## Contenido principal

- `benchmark_3d_opensees.py`: modelo OpenSeesPy reproducible.
- `LAB_semana1_benchmark_3D.md`: informe Markdown del caso.
- `resultados_verificacion_3d.md`: comparacion con referencias y verificaciones obligatorias.
- `benchmark_3d_modelo.png`: visualizacion simple de geometria, losa y ejes.
- `diagrama_3d_axial.png`: diagrama simple de fuerza axial local.
- `diagrama_3d_corte.png`: diagrama simple de corte local `Vz`.
- `diagrama_3d_momento.png`: diagrama simple de momento local `My`.
- `estructura_3d_unity.json`: datos exportados para el visualizador Unity.
- `DEFENSA_individual_3D.md`: guia para la defensa individual.
- `sap2000_comparacion/`: guia y tablas para replicar el modelo en SAP2000.

## Version alternativa

- `version_alternativa_grupo/`: material adicional del benchmark 3D que ya estaba en el repositorio.

## Ejecutar

Desde la raiz del repositorio:

```bat
python semana_actual_benchmark_3d\benchmark_3d_opensees.py
```

## Cambiar apoyos

En `benchmark_3d_opensees.py`, buscar `supports`:

```python
supports = {
    1: (1, 1, 1, 1, 1, 1),
    2: (1, 1, 1, 1, 1, 1),
    3: (1, 1, 1, 1, 1, 1),
    4: (1, 1, 1, 1, 1, 1),
}
```

Cada fila corresponde a un nodo de apoyo y el orden es `(Ux, Uy, Uz, Rx, Ry, Rz)`.

- `1` significa restringido.
- `0` significa libre.

Ejemplo de pasador en el nodo 2:

```python
2: (1, 1, 1, 0, 0, 0),
```
