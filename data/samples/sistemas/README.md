# Muestra sistemas: `alcance_funcional.csv`

Entrada de `AdaptadorSistemas` (`adapters/sistemas/adaptador.py`, Sesión I5): el alcance funcional
de un sistema de software ficticio pero realista — un módulo de presupuestos, catálogo de insumos y
verificación, coherente con el propio sistema que describe este repositorio —, expresado como una
tabla de casos de uso. Nueve casos de uso (`SI-01` … `SI-09`) en tres módulos (`Presupuestos`,
`Catalogo`, `Verificacion`).

## Columnas

`id,modulo,caso_de_uso,codigo_partida,entradas,salidas,consultas,archivos,interfaces,especificaciones`

- `id`: identificador del caso de uso, prefijo `SI-`. Es el `origen_id` del `ItemComputo` (regla de
  trazabilidad total, NORMAS.md §2.6).
- `modulo`, `caso_de_uso`: agrupación funcional y nombre del caso de uso; se combinan en la
  `descripcion` del `ItemComputo` (`"<modulo>: <caso_de_uso>"`).
- `codigo_partida`: código de la partida asociada a ese caso de uso. A diferencia del adaptador
  civil tabular, aquí cada fila declara su propio código: no hay un mapeo externo `codigos`.
- `entradas`, `salidas`, `consultas`, `archivos`, `interfaces`: conteo de transacciones o archivos
  de cada tipo IFPUG que participan en el caso de uso (ver tabla de pesos abajo).
- `especificaciones`: pares `clave=valor` separados por `;` (aquí, `actor=<rol que dispara el caso
  de uso>`), mismo formato que `adapters/civil/tabular.py`.

## Puntos de función no ajustados (PFNA) y pesos IFPUG

`AdaptadorSistemas` calcula, para cada caso de uso, los puntos de función no ajustados con los pesos
medios de complejidad de IFPUG (International Function Point Users Group):

| Tipo de función                                        | Sigla | Peso medio | Columna del CSV |
|----------------------------------------------------------|-------|-----------:|------------------|
| Entrada externa (External Input)                          | EI    |          4 | `entradas`       |
| Salida externa (External Output)                           | EO    |          5 | `salidas`        |
| Consulta externa (External Inquiry)                        | EQ    |          4 | `consultas`      |
| Archivo lógico interno (Internal Logical File)             | ILF   |         10 | `archivos`       |
| Archivo de interfaz externa (External Interface File)      | EIF   |          7 | `interfaces`     |

La regla trazable es `REGLA_PUNTOS_FUNCION` (`adapters/sistemas/adaptador.py`):

```
4*entradas + 5*salidas + 4*consultas + 10*archivos + 7*interfaces
```

Cada `ItemComputo` guarda esta expresión en `regla` y las cinco cantidades en `parametros`, de modo
que `evaluar_regla(item.regla, item.parametros) == item.cantidad` (regla R1 de verificación,
trazabilidad geométrica) para cada fila. La unidad de cada item es `"pf"` (punto de función): no
está en la tabla de alias de `core.contracts.unidades` (esa tabla solo cubre unidades físicas de
obra), así que `normalizar_unidad("pf")` la conserva tal cual, sin traducirla. Se documenta como
hallazgo en `docs/bitacora/2026-08-29-I5-sistemas.md`.

## Filas

| id | módulo | caso de uso | PFNA |
|---|---|---|---:|
| SI-01 | Presupuestos | Crear presupuesto a partir de partidas | 27 |
| SI-02 | Presupuestos | Editar partida presupuestada | 19 |
| SI-03 | Presupuestos | Cerrar la curva de inversión del presupuesto | 18 |
| SI-04 | Catalogo | Registrar insumo en el catálogo | 14 |
| SI-05 | Catalogo | Actualizar precio de insumo | 20 |
| SI-06 | Catalogo | Consultar historial de precios de un insumo | 4 |
| SI-07 | Verificacion | Generar el informe de auditoría del presupuesto | 27 |
| SI-08 | Verificacion | Exportar el presupuesto auditado a Excel | 12 |
| SI-09 | Verificacion | Consultar los indicadores de las siete reglas de verificación | 4 |

## Supuesto declarado

Esta muestra es sintética (no proviene de un sistema en producción ni de una entrevista de alcance
real): los conteos de entradas, salidas, consultas, archivos e interfaces por caso de uso son
estimaciones razonables de un analista, no una medición formal contra un modelo de casos de uso
documentado. Sirve para probar el adaptador y la fórmula de PFNA, no como línea base auditada (a
diferencia de `data/linea_base/APUS_CLINICA.pdf`, que sí lo es para el dominio civil).
