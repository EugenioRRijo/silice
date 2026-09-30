# Muestra industrial: `activos_planta.csv`

Entrada del adaptador industrial (`adapters/industrial/adaptador.py`, Sesión I5): un registro de
activos de una planta industrial con su frecuencia de intervención de mantenimiento. Diez activos
realistas (bombas, tableros eléctricos, compresores, transformadores, una válvula y un motor), todos
con `id_activo` prefijado `IN-`.

## Columnas

`id_activo,descripcion,codigo_partida,unidad,frecuencia_anual,horizonte_anios,especificaciones`

- `id_activo`: identificador único del activo en el registro de planta (`IN-001`…). Es el
  `origen_id` del `ItemComputo` (trazabilidad, NORMAS.md §5).
- `descripcion`: nombre del activo tal como aparece en el inventario de mantenimiento.
- `codigo_partida`: código de la partida de mantenimiento asociada al activo (prefijo `MNT-`); es
  la partida que un futuro APU de mantenimiento costearía (ver Hallazgos en la bitácora de esta
  sesión).
- `unidad`: unidad de la cantidad de obra. Todas las filas de esta muestra usan `intervencion`
  (`core.contracts.unidades.normalizar_unidad` no tiene alias para ella: pasa sin traducir, como
  toda unidad no tabulada).
- `frecuencia_anual`: número de intervenciones de mantenimiento programadas por año.
- `horizonte_anios`: años del horizonte de planificación sobre el que se proyecta la frecuencia.
- `especificaciones`: pares `clave=valor` separados por `;` (por ejemplo
  `potencia=15 HP;marca=Grundfos`), trazables hacia la regla R4 igual que en el adaptador civil.

## Regla de cómputo

Cada fila produce un único `ItemComputo` con `origen_tipo=REGLA` y `regla="frecuencia_anual *
horizonte_anios"`: la cantidad de obra es el número total de intervenciones de mantenimiento
esperadas en el horizonte de planificación. Por ejemplo, `IN-001` (frecuencia 4, horizonte 5 años)
produce una cantidad de 20 intervenciones.

## Supuesto declarado

Esta muestra fija un horizonte de planificación de 5 años para la mayoría de los activos (3 años
para `IN-010`, el transformador de emergencia, con un ciclo de reemplazo más corto) porque el brief
de la sesión no fija un horizonte único; es un supuesto de esta muestra, no un valor tomado de una
fuente auditada como la línea base civil.
