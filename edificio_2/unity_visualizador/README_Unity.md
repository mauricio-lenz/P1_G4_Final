# Unity - Edificio 2

Proyecto Unity para inspeccionar el modelo estructural del edificio 2.

## Abrir Proyecto

En Unity Hub seleccionar esta carpeta:

```text
edificio_ingenieria_uandes/project/edificio 2/unity_visualizador
```

## Generar Datos

Desde la raiz del repositorio:

```bat
python "edificio_ingenieria_uandes\project\edificio 2\main.py"
```

Esto actualiza:

```text
Assets/Resources/estructura_edificio_ingenieria_unity.json
```

## Crear Visualizador

En Unity:

```text
MCOC > Crear Visualizador
Play
```

## Inspeccion

Al hacer click sobre vigas, columnas, apoyos o diafragmas se muestra informacion del elemento.

Para vigas y columnas:

- `elementTag`;
- seccion;
- material;
- axial;
- corte;
- momento;
- cargas tributarias cuando corresponda.

Para diafragmas:

- identificador;
- nivel;
- perfil de carga;
- area del panel.

## Diagramas

Teclas:

```text
0 = apagar diagramas
1 = axial
2 = corte
3 = momento
```

Los diagramas de vigas usan la carga tributaria distribuida equivalente `qU = (1.2D + 1.6L) / L`. Las columnas muestran axial gravitacional acumulado aproximado.
