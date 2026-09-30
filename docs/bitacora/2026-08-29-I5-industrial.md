# Bitácora — Sesión I5 (adaptador industrial)

**Fecha:** 2026‑08‑29 · **Rama:** `inc/I5-industrial` · **Compuertas cruzadas:** ninguna (I5 no
depende de G1/G2; es paralela a los adaptadores telecom y sistemas de la misma sesión)

## Objetivo

Implementar `AdaptadorIndustrial`, que lee un registro de activos de planta (bombas, tableros,
compresores, transformadores, válvulas, motores…) con su frecuencia de intervención de
mantenimiento y devuelve `ItemComputo` trazables, sin tocar `core/`. Es una de las tres piezas de la
prueba empírica de la hipótesis central del proyecto (`git diff --stat core/` vacío tras agregar un
dominio nuevo, NORMAS.md §1).

## Qué se hizo

| Archivo | Contenido |
|---|---|
| `adapters/industrial/evaluador.py` | `evaluar_regla(expresion, parametros) -> Decimal`: evalúa un AST restringido (`BinOp` +‑‑*‑/‑**, `UnaryOp` USub, `Name`, `Constant` numérico); cualquier otro nodo → `ValueError`; nombre no declarado → `KeyError`. Implementación propia e independiente de `adapters/civil/evaluador.py` (no se importa entre dominios) |
| `adapters/industrial/adaptador.py` | `AdaptadorIndustrial(AdaptadorDominio)`, `dominio = Dominio.INDUSTRIAL`; `REGLA_INTERVENCIONES = "frecuencia_anual * horizonte_anios"`; lee el CSV con `csv.DictReader`, arma un `ItemComputo` por fila con `origen_tipo=REGLA`, `origen_id=id_activo` |
| `adapters/industrial/__init__.py` | Reexporta `AdaptadorIndustrial` (`__all__`) |
| `data/samples/industrial/activos_planta.csv` | 10 activos (2 bombas, 2 tableros, 2 compresores, 2 transformadores, 1 válvula, 1 motor), todos con `id_activo` prefijado `IN-` y `codigo_partida` prefijado `MNT-` |
| `data/samples/industrial/README.md` | Describe columnas, la regla de cómputo y el supuesto del horizonte de planificación |
| `tests/unit/test_adapter_industrial.py` | 4 pruebas con los nombres exactos del brief |

Commit: `feat(industrial): adaptador de registro de activos`.

## Decisiones

| Decisión | Motivo |
|---|---|
| Evaluador propio en `adapters/industrial/evaluador.py`, no importado de `adapters/civil/evaluador.py` | cada adaptador es independiente (NORMAS.md §2); aunque el subconjunto aritmético permitido coincide hoy con el de civil, importar entre paquetes de `adapters/` acoplaría dos dominios que no deben conocerse entre sí |
| `codigo_partida` distinto de `id_activo` (`MNT-BOM-CEN` vs. `IN-001`) | el brief pide activos con códigos `IN-`; `id_activo` es el identificador del activo físico en el inventario (y el `origen_id` trazable), mientras `codigo_partida` es la partida de mantenimiento que un futuro APU costearía — son dos conceptos distintos aunque en esta muestra compartan el mismo activo 1:1 |
| `unidad` de la muestra es `intervencion` para todas las filas, sin alias en `core.contracts.unidades` | es la unidad natural de una intervención de mantenimiento; `normalizar_unidad` la deja pasar sin traducir porque no está en la tabla de alias, tal como el contrato prevé para unidades no tabuladas |
| Horizonte de planificación de 5 años para la mayoría de los activos, 3 años para el transformador de emergencia (`IN-010`) | el brief no fija un horizonte único; variar uno de los diez activos evita que la muestra parezca una constante disfrazada y ejercita la regla con más de un valor de `horizonte_anios` |
| `test_no_importa_nada_de_core_salvo_contracts` reimplementa localmente el mismo chequeo AST de `tests/unit/test_arquitectura.py`, en vez de reutilizarlo | el brief pide ese nombre de prueba exacto dentro de `test_adapter_industrial.py`; `test_arquitectura.py` ya vigila lo mismo a nivel de todo `adapters/`, así que esta prueba es redundante por diseño (cinturón y tirantes), no una superposición accidental |

## Hallazgos

Ninguna insuficiencia de contrato. `core.contracts.item_computo.ItemComputo` y
`core.contracts.adaptador.AdaptadorDominio` cubren exactamente lo que este adaptador necesita: un
`origen_id` real por activo, `origen_tipo=REGLA` con `regla` y `parametros` para la trazabilidad
(R1), y `especificaciones` para los atributos comparables (R4, aunque esta sesión no construye
todavía un APU de mantenimiento que los consuma).

**Qué haría falta para un APU de mantenimiento** (más allá del alcance de esta sesión): la unidad
"intervencion" no tiene un rendimiento natural en el sentido de `core.contracts.apu.Rendimiento`
("partidas de obra por día"), porque una intervención de mantenimiento no es una partida de
construcción que se ejecuta en un tajo con cuadrilla — es un evento periódico con su propio costo
(repuestos, horas de técnico, parada de planta). El motor de costeo (`core.costing.calcular_apu`)
no cambiaría (sigue siendo materiales + equipos + mano de obra sobre un `rendimiento`), pero el
*origen* de ese rendimiento para una partida de mantenimiento sería distinto al de una partida
civil: en vez de "unidades de partida por día" derivadas de una cuadrilla, sería "1 intervención"
por evento, con la frecuencia y el horizonte de esta muestra determinando cuántas veces se repite
esa partida en el presupuesto — no cuántas partidas caben en un día. Esto no exige tocar
`core/contracts/apu.py`: `ParametrosCosto` y `ComposicionAPU` ya son agnósticos al significado de
`rendimiento`; es una decisión de cómo el llamador arma la `ComposicionAPU` para una partida de
mantenimiento, no del contrato en sí.

## Impedimentos

Ninguno. Las 4 pruebas de `tests/unit/test_adapter_industrial.py` pasan; la suite completa del
worktree queda en 137 pruebas verdes; `ruff check .` y `ruff format --check .` limpios, sin
advertencias en la salida de pytest. `git diff --stat be70863 -- core/` vacío.
