# Modelo de datos

> Estado: **completo, pendiente de revisión del tutor (compuerta G0,
> [docs/metodologia.md §2.2](metodologia.md#22-compuertas))**. Redactado en la Sesión 0.2 y
> contrastado con `core/models/entidades.py` en la fase C4 del cierre (2026‑09‑28); en la fase C6
> (2026‑09‑29) gana la tabla aditiva `justificacion_rendimiento` (INV‑093). Materializa en
> persistencia los contratos de interfaz de [NORMAS.md §5](../NORMAS.md) sin ampliarlos ni
> contradecirlos. Los modelos SQLAlchemy de
> `core/models/` (Sesión I0.4) se escriben a partir de este documento y no lo preceden: si el código
> necesita una columna que aquí no está, primero se corrige el documento.

## 1. Requisitos del modelo

| Requisito | Origen | Consecuencia de diseño |
|---|---|---|
| Reconstruir cualquier presupuesto a la fecha en que se elaboró | UC‑02, RNF‑02 | los precios se versionan: `ListaPrecios` con vigencia y `CambioPrecio` como historial; el presupuesto referencia la lista con la que se valoró |
| Distinguir rendimiento estimado de rendimiento medido | UC‑06 | `Rendimiento.tipo` ∈ {estimado, medido}; un rendimiento medido referencia obligatoriamente una `Ejecucion` (restricción `CHECK` en la tabla, no solo en Python) |
| `Decimal` para todo lo monetario y dimensional | NORMAS.md §2 | tipo propio `DecimalExacto` (§7); nunca `Float`, y tampoco `Numeric` sobre SQLite |
| Toda cantidad es trazable a su origen | NORMAS.md §2 | `ItemComputo` persistido con `origen_id`, `origen_tipo`, `regla`, `parametros` |
| El núcleo no conoce dominios concretos | NORMAS.md §5 | `Partida.dominio` es un dato, no una rama de código; ninguna tabla **de `core/models`** es específica de un dominio. Las tablas `esp_*` del sprint final (§2.4) son del adaptador `adapters/espacio`, no del núcleo, y por eso no contradicen este requisito (spec SF §5.4) |
| El histórico de cambios alimenta el módulo predictivo | I1, I6.3 | `CambioPrecio` guarda insumo, precio anterior, precio nuevo, fecha; `IncidenciaCambio` guarda el efecto por partida |
| El informe de auditoría se persiste, no solo se imprime | NORMAS.md §2, UC‑05 | `Hallazgo` cuelga del presupuesto auditado y conserva los `origen_id` involucrados |

## 2. Entidades

Diecisiete entidades. Los atributos de cada una se detallan en §2.1 – §2.3, con su tipo lógico y el papel
de la clave (**PK** primaria, **FK** foránea, **UK** única); `DecimalExacto` (§7.1) se abrevia
`Decimal` en esas tablas.

| Entidad | Propósito | Contrato de `core.contracts` que materializa |
|---|---|---|
| `Proyecto` | agrupa presupuestos y ejecuciones de una misma obra | — |
| `Presupuesto` | versión valorada de un proyecto en una fecha, con su lista de precios | `Presupuesto` |
| `PartidaPresupuestada` | renglón del presupuesto: cantidad × precio unitario | `PartidaPresupuestada` |
| `PuntoCurva` | período del plan de trabajo con monto y acumulado | `PuntoCurva` |
| `ItemComputo` | cantidad de obra persistida con su procedencia | `ItemComputo` |
| `Partida` | código, descripción, unidad, dominio | `ComposicionAPU` (cabecera) |
| `Insumo` | material, equipo o mano de obra del catálogo | `LineaMaterial` / `LineaEquipo` / `LineaManoObra` (catálogo) |
| `ComposicionAPU` | relación partida–insumo con cantidad y factor de depreciación | `ComposicionAPU` (líneas) |
| `Rendimiento` | valor, tipo, condiciones, fecha, referencia a ejecución | `Rendimiento` |
| `JustificacionRendimiento` | justificación con que el proyectista acepta la advertencia de RF‑27 sobre un rendimiento (UC‑06, flujo 4a) | — |
| `Ejecucion` | obra ejecutada de la que se mide un rendimiento | `Rendimiento.referencia_ejecucion` |
| `ListaPrecios` | conjunto de precios con fecha de vigencia y moneda | — |
| `PrecioInsumo` | precio de un insumo en una lista | precio de `LineaMaterial` / `LineaEquipo` / sueldo de `LineaManoObra` |
| `CambioPrecio` | historial: qué insumo cambió, cuánto y entre qué listas | — |
| `IncidenciaCambio` | efecto de un cambio de precio sobre el precio unitario de una partida | — |
| `DescarteVersion` | marca de la versión revalorada que el usuario descartó (UC‑02, flujo 7a) | — |
| `Hallazgo` | resultado persistido de una regla sobre un presupuesto, o la declaración de un ítem pendiente (UC‑01, flujo 3a) | `Hallazgo` |

### 2.1 Catálogo

**`Partida`** — la cabecera de un APU. El código es la identidad de negocio; la clave primaria es
subrogada para que un cambio de nomenclatura (paso de `LB-` a COVENIN 2000) no propague claves.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | subrogada, autoincremental |
| `codigo` | str(40) | UK | no | `LB-01-EXC` mientras no exista el código normativo |
| `codigo_covenin` | str(40) | — | sí | código COVENIN 2000 cuando se asigne |
| `descripcion` | str(300) | — | no | indexada: búsqueda de UC‑03 |
| `unidad` | str(20) | — | no | normalizada con `normalizar_unidad` |
| `dominio` | str(20) | — | no | valor de `Dominio`; dato, nunca rama de código |

**`Insumo`** — material, equipo o mano de obra. **No lleva precio**: el precio depende del par
(insumo, lista) y vive en `PrecioInsumo` (§4.1).

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `codigo` | str(20) | UK | no | generado: `MAT-001`, `EQU-001`, `MO-001`; sufijo de variante `EQU-007-B` (§6) |
| `tipo` | str(10) | — | no | ∈ {`material`, `equipo`, `mano_obra`} |
| `descripcion` | str(300) | — | no | |
| `unidad` | str(20) | — | sí | solo los materiales la tienen; equipos y mano de obra no la declaran en el contrato |

Índice `ix_insumo_tipo_descripcion (tipo, descripcion)`: es la búsqueda que hace `cargar_composicion`
antes de decidir si reutiliza un insumo o crea una variante.

**`ComposicionAPU`** — una línea del desglose. Su identidad natural es (partida, insumo, orden).

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `partida_id` | int | FK → `Partida.id` | no | |
| `insumo_id` | int | FK → `Insumo.id` | no | |
| `cantidad` | Decimal | — | no | ≥ 0 |
| `depreciacion` | Decimal | — | sí | solo equipos; (0, 1]. Varía entre APU para el mismo insumo (hallazgo 7) |
| `modalidad` | str(10) | — | sí | solo mano de obra; ∈ {jornal, destajo}; NULL se lee como jornal |
| `orden` | int | — | no | preserva el orden del PDF; sin él las tuplas del contrato no se reconstruyen iguales |

**`Rendimiento`** — unidades de partida por día, con su procedencia.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `partida_id` | int | FK → `Partida.id` | no | |
| `valor` | Decimal | — | no | > 0 |
| `tipo` | str(10) | — | no | ∈ {`estimado`, `medido`} |
| `fecha` | date | — | no | fecha de declaración o de medición |
| `condiciones` | str(300) | — | no | cadena vacía si no se declaran |
| `ejecucion_id` | int | FK → `Ejecucion.id` | sí | obligatorio si `tipo = 'medido'` |

`CheckConstraint ck_rendimiento_medido_exige_ejecucion`:
`tipo <> 'medido' OR ejecucion_id IS NOT NULL`. La misma invariante que valida
`contracts.Rendimiento.__post_init__`, escrita también en el esquema para que ningún camino de
carga (script, importación masiva, SQL directo) pueda saltársela.

**`JustificacionRendimiento`** — la justificación con que el proyectista acepta la advertencia de
RF‑27 (UC‑06, flujo 4a; `docs/ERS.md`, UC‑06 4a). Se liga al rendimiento que registró el guardado o
la petición que trajo la advertencia (`core.catalog.justificar_rendimiento`, que toma el último
rendimiento de la partida, el de mayor `id`), no a la composición.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `rendimiento_id` | int | PK, FK → `Rendimiento.id` | no | `ondelete="CASCADE"`: borrar el rendimiento (o su partida) borra su justificación |
| `texto` | texto | — | no | la justificación; no vacía (lo valida `justificar_rendimiento`) |
| `advertencia` | texto | — | no | el texto de la advertencia aceptada, para leerla sin reconstruir la dispersión de ese momento |
| `fecha` | date | — | no | fecha del registro |

Como la clave primaria es la foránea, un rendimiento tiene a lo sumo una justificación (una
segunda da `ValueError`). La relación se declara solo del lado nuevo (`JustificacionRendimiento.rendimiento`,
sin `back_populates`), así que `Rendimiento` y sus consultas no cambian. La tabla es **aditiva**,
como `DescarteVersion` (§2.2): `crear_esquema` (`create_all`) la agrega a una base anterior a C6 sin
`ALTER TABLE` y sin tocar las demás tablas ni sus filas (expediente C6.1 de
`docs/bitacora/2026-09-29-C6-expedientes.md`). Ninguna ruta ni pantalla la lee después de
registrarla.

**`Ejecucion`** — obra ejecutada de la que se mide un rendimiento.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `referencia` | str(60) | UK | no | lo que el contrato guarda en `Rendimiento.referencia_ejecucion` |
| `proyecto_id` | int | FK → `Proyecto.id` | sí | una ejecución puede ser de un proyecto ajeno al catálogo |
| `fecha_inicio` | date | — | no | |
| `fecha_fin` | date | — | sí | nula mientras la obra está en curso |
| `descripcion` | str(300) | — | no | |

### 2.2 Precios y su historial

**`ListaPrecios`** — el conjunto de precios vigente desde una fecha. **Inmutable una vez que un
presupuesto la referencia** (§5).

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `nombre` | str(120) | — | no | `Linea base 28/04/2026` |
| `moneda` | str(10) | — | no | `USD` |
| `fecha_vigencia` | date | — | no | indexada: `lista_vigente(fecha)` busca el máximo ≤ fecha |
| `origen` | str(200) | — | no | procedencia documental: `APUS_CLINICA.pdf`, boletín, cotización |

Desde C6 (INV‑076), importar el presupuesto de un tercero (UC‑05) crea la lista «Importada:
<archivo>», con `origen` = el nombre del archivo, la moneda del presupuesto y `fecha_vigencia` = su
fecha, que **copia los precios de la lista vigente a esa fecha** (si la hay) y valora los APU del
tercero. Como `lista_vigente` toma la de mayor `fecha_vigencia` y, a igual fecha, la de mayor `id`,
la importada pasa a ser la **vigente desde su fecha** para todo el caso: la heredan lo que se
elabore o componga después y la próxima lista que se cargue. Los importes no cambian, porque la
copia es exacta; la procedencia sí (limitación declarada en la ERS, postcondición de UC‑05).

**`PrecioInsumo`** — el precio de un insumo en una lista. Para la mano de obra, el jornal diario.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `lista_id` | int | FK → `ListaPrecios.id` | no | |
| `insumo_id` | int | FK → `Insumo.id` | no | |
| `precio` | Decimal | — | no | ≥ 0 |

`UniqueConstraint uq_precio_insumo_lista_insumo (lista_id, insumo_id)`: un insumo tiene a lo sumo un
precio por lista. El índice que crea esa restricción es el que sirve la consulta de UC‑02 (§7.2).

**`CambioPrecio`** — el historial. Una fila por insumo que cambió entre dos listas.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `lista_anterior_id` | int | FK → `ListaPrecios.id` | no | |
| `lista_nueva_id` | int | FK → `ListaPrecios.id` | no | indexada (UC‑02) |
| `insumo_id` | int | FK → `Insumo.id` | no | |
| `precio_anterior` | Decimal | — | no | |
| `precio_nuevo` | Decimal | — | no | |
| `variacion` | Decimal | — | no | fracción: (nuevo − anterior) / anterior. Derivada y almacenada (§4.2) |
| `fecha` | date | — | no | fecha del cambio |

**`IncidenciaCambio`** — qué le hizo ese cambio al precio unitario de cada partida que usa el insumo.
Es lo que UC‑02 muestra al usuario: «el cemento subió 20 % y el vaciado de concreto sube 7,4 %».

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `cambio_id` | int | FK → `CambioPrecio.id` | no | |
| `partida_id` | int | FK → `Partida.id` | no | |
| `precio_unitario_anterior` | Decimal | — | no | PU con la lista anterior |
| `precio_unitario_nuevo` | Decimal | — | no | PU con la lista nueva |
| `variacion` | Decimal | — | no | fracción de variación del PU |

**`DescarteVersion`** — la versión revalorada que el usuario descartó (UC‑02, flujo 7a;
`docs/ERS.md:184`). Es una **marca, no un borrado**: la versión sigue guardada y cargándose como
documento, y el historial que la produjo (`CambioPrecio`, `IncidenciaCambio`) se conserva porque
alimenta el histórico del módulo predictivo.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `presupuesto_id` | int | PK, FK → `Presupuesto.id` | no | `ondelete="CASCADE"`: borrar el presupuesto borra su marca |
| `fecha` | date | — | no | fecha del descarte |

Regla de 7a (`core.budget.descartar_version`): solo se descarta el último presupuesto guardado del
proyecto (el de mayor `id`), si el proyecto tiene al menos otro anterior, y una sola vez; el primero
del proyecto nunca. Como la clave primaria es la foránea, una versión tiene a lo sumo una marca.
Límite (expediente C3.2; **cerrado en SF‑E2**, §2.4: toda versión nueva guarda su `version_origen`
y la versión vigente pasa a ser la de mayor `id` no descartada): hoy el esquema no guarda de qué
presupuesto salió una versión, así que la función no distingue una versión revalorada de un segundo presupuesto elaborado aparte en el mismo
proyecto; por eso la interfaz solo ofrece el botón «Descartar version» para la versión que acaba de
guardar `actualizar_precios` en esa ejecución. La tabla es **aditiva**: `crear_esquema`
(`create_all`) la agrega a una base existente sin tocar las demás tablas, así que no es una
migración de esquema.

### 2.3 Proyecto, presupuesto y auditoría

**`Proyecto`**

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `nombre` | str(200) | UK | no | `Drenaje de la clínica`; la unicidad es lo que hace idempotente a `seed.py` |
| `descripcion` | str(500) | — | no | |
| `dominio` | str(20) | — | no | valor de `Dominio` |

**`Presupuesto`** — una versión valorada. Congela los cuatro parámetros de costo y referencia la lista.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `codigo` | str(40) | — | no | `001`; único dentro del proyecto |
| `proyecto_id` | int | FK → `Proyecto.id` | no | |
| `fecha` | date | — | no | |
| `moneda` | str(10) | — | no | |
| `lista_precios_id` | int | FK → `ListaPrecios.id` | no | la lista con la que se valoró |
| `fcas` | Decimal | — | no | instantánea de `ParametrosCosto.fcas` |
| `bono_alimentacion` | Decimal | — | no | instantánea de `ParametrosCosto.bono_alimentacion` |
| `administracion` | Decimal | — | no | instantánea de `ParametrosCosto.administracion` |
| `utilidad` | Decimal | — | no | instantánea de `ParametrosCosto.utilidad` |

`UniqueConstraint uq_presupuesto_proyecto_codigo (proyecto_id, codigo)`.

**`PartidaPresupuestada`** — el renglón, con la instantánea completa del `ResultadoAPU`.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `presupuesto_id` | int | FK → `Presupuesto.id` | no | |
| `partida_id` | int | FK → `Partida.id` | no | |
| `item_computo_id` | int | FK → `ItemComputo.id` | no | la cantidad y su trazabilidad |
| `orden` | int | — | no | orden de presentación |
| `cantidad` | Decimal | — | no | copia de `ItemComputo.cantidad` en el momento de valorar |
| `materiales` | Decimal | — | no | instantánea de `ResultadoAPU.materiales` |
| `equipos` | Decimal | — | no | instantánea de `ResultadoAPU.equipos` |
| `mano_obra` | Decimal | — | no | instantánea de `ResultadoAPU.mano_obra` |
| `costo_directo` | Decimal | — | no | instantánea de `ResultadoAPU.costo_directo` |
| `con_administracion` | Decimal | — | no | instantánea de `ResultadoAPU.con_administracion` |
| `precio_unitario` | Decimal | — | no | instantánea de `ResultadoAPU.precio_unitario` |
| `total` | Decimal | — | no | cantidad × precio_unitario, sin redondear |

**`PuntoCurva`**

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `presupuesto_id` | int | FK → `Presupuesto.id` | no | |
| `orden` | int | — | no | posición en el plan de trabajo |
| `periodo` | str(120) | — | no | `Día 1 Excavación` |
| `monto` | Decimal | — | no | gasto del período |
| `acumulado` | Decimal | — | no | derivada y almacenada (§4.2); la regla R2 la audita |

**`ItemComputo`** — la cantidad de obra con su procedencia. Conserva **dos** unidades.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `presupuesto_id` | int | FK → `Presupuesto.id` | sí | nulo mientras el cómputo no se ha presupuestado. Un ítem del presupuesto que ningún renglón cita es un **pendiente** de UC‑01 3a: se guarda así para que la recarga vuelva a declararlo (`core.budget.cargar_elaboracion`, INV‑080) |
| `codigo_partida` | str(40) | — | no | código de negocio, no FK: un cómputo puede citar una partida aún no catalogada (lo detecta la auditoría) |
| `descripcion` | str(300) | — | no | la que escribió el proyectista |
| `unidad_original` | str(20) | — | no | tal cual se escribió: `mts` |
| `unidad` | str(20) | — | no | normalizada: `m`. La regla R3 compara esta con la del APU y reporta la original |
| `cantidad` | Decimal | — | no | ≥ 0 |
| `origen_id` | str(120) | — | no | GlobalId IFC, fila de la tabla, clave del CSV… |
| `origen_tipo` | str(20) | — | no | valor de `OrigenTipo` |
| `dominio` | str(20) | — | no | valor de `Dominio` |
| `regla` | str(300) | — | sí | obligatoria si `origen_tipo = 'regla'` |
| `parametros` | texto JSON | — | no | `{"a": "0.80", "h": "0.80"}`; los `Decimal` se serializan como cadena (§7.1) |
| `especificaciones` | texto JSON | — | no | `{"diametro": "4 pulg", "material": "PVC"}` |

**`Hallazgo`** — el informe de auditoría persistido.

| Atributo | Tipo | Clave | Nulo | Notas |
|---|---|---|---|---|
| `id` | int | PK | no | |
| `presupuesto_id` | int | FK → `Presupuesto.id` | no | |
| `regla` | str(10) | — | no | `R1`…`R7`, o `PENDIENTE` (`core.budget.CODIGO_PENDIENTE`) para un ítem sin partida en el catálogo (UC‑01 3a), o `ATIPICO` (`core.budget.CODIGO_ATIPICO`, desde C6) para un precio atípico de la lista nueva en el informe de una versión revalorada (UC‑07 5) |
| `severidad` | int | — | no | valor de `Severidad` (IntEnum) |
| `descripcion` | str(500) | — | no | |
| `impacto` | Decimal | — | sí | monto o cantidad afectada |
| `origen_ids` | texto JSON | — | no | lista de identificadores que resuelve `InformeAuditoria.partida_de`: `origen_id` en R1, R3, R4, R5 y R7; **códigos de partida** en R6 y en `ATIPICO` (las partidas del presupuesto que usan el insumo; convención de C6, no `origen_id` de ítems), y el par `(codigo_partida, origen_id)` en `PENDIENTE` (`core.budget.presupuesto._clave_pendiente`); `[]` si la regla no señala cantidades. Desde C5 (INV‑095) la partida de un hallazgo de R1, R3, R4, R5 o R7 la declara la regla al emitirlo (`InformeAuditoria.partida_por_hallazgo`), no se deduce de su primer origen: un `origen_id` compartido por varias partidas ya no se atribuye a la primera. Esa atribución **no se persiste** (la tabla no cambia): la recarga (`cargar_elaboracion`) reaudita y la vuelve a calcular ([arquitectura §6.1](arquitectura.md#61-deuda-arquitectónica-declarada)) |
| `valor_observado` | Decimal | — | sí | |
| `valor_esperado` | Decimal | — | sí | |

Lo que el informe ganó en C5 no tiene columna ni tabla, a propósito (sin migración de esquema): las
**reglas evaluadas** (`InformeAuditoria.reglas_evaluadas`, INV‑092, UC‑05 5a) y la partida que
declaró cada regla (`partida_por_hallazgo`, INV‑095). El informe recargado las enumera y las
atribuye porque la recarga reaudita con `REGLAS`; la tabla guarda solo los hallazgos, que no
cambiaron de forma. Un presupuesto sin hallazgos no deja ninguna fila `Hallazgo`: que se
verificaron las siete reglas lo dice el informe al recargarlo, no la base.

Los `ATIPICO` de C6 (INV‑099) sí se guardan como filas de `Hallazgo`, sin columna nueva: la
reauditoría no los puede recalcular (el detector no está en el núcleo), así que `cargar_elaboracion`
los lee de la tabla y los vuelve a declarar.

### 2.4 Enmienda del sprint final (SF): núcleo implementado en SF3 (`inc/sf3-nucleo`)

Fuente: [spec SF](especificaciones/2026-10-04-sprint-final-prototipo-design.md) §5.2, §6.2, §9.3 y
§9.6; expedientes SF‑E2, SF‑E6 y SF‑E7 en [2026-10-sf-expedientes.md](bitacora/2026-10-sf-expedientes.md).
Las §2.1 a §2.3 siguen describiendo las diecisiete entidades originales; esta sección describe las
**ocho tablas aditivas** que SF3 agrega a `core/models` (veinticinco en total). Todas son aditivas
(ruling SF3‑E0): `crear_esquema` las crea en una base anterior sin `ALTER TABLE` y sin tocar sus
filas, y ninguna columna se agrega a una tabla existente. Lo que el spec llama «columna» (la versión
de origen, la tasa y el alcance de una lista, la referencia de un precio) vive en una tabla con la
misma clave. Una base anterior abre: las tablas nuevas están vacías y todo cae al camino de siempre
(catálogo, lista global, versión sin origen). Los nombres de columna son los de `entidades.py`.

**Instantánea por versión (SF‑E6).** Una por (versión, partida); `ondelete="CASCADE"` desde `Presupuesto`.

| Entidad (tabla) | Atributos | Notas |
|---|---|---|
| `ComposicionVersion` (`composicion_version`) | `id`, `presupuesto_id`, `codigo_partida`, `descripcion`, `unidad`, `rendimiento` | única por (`presupuesto_id`, `codigo_partida`). `rendimiento` es la **instantánea de rendimientos**: el vigente de la partida en esa versión |
| `LineaComposicionVersion` (`linea_composicion_version`) | `id`, `composicion_id`, `orden`, `tipo`, `insumo_id` (anulable), `descripcion`, `unidad`, `cantidad`, `precio`, `depreciacion`, `modalidad` | orden canónico de `core.catalog.mapeo.lineas_de` (materiales, equipos, mano de obra); `precio` es el que valoró la versión; `insumo_id` permite revalorar con otra lista |
| `PlanVersion` (`plan_version`) | `id`, `presupuesto_id`, `periodo`, `etiqueta`, `orden`, `codigo_partida` (anulable), `fraccion` | el reparto del plan por partida (la curva guardada no lo conserva): ampliación declarada del expediente SF‑E6 |

`core.budget.guardar_presupuesto` congela siempre la instantánea. La recarga, la verificación del PU,
la revaloración por UC‑02 y `composiciones_de_presupuesto` (escenarios, hoja) toman la composición
**por código de partida** de la instantánea y, solo si falta, del catálogo con la lista y la fecha del
presupuesto (versiones anteriores a SF‑E6; instantánea parcial de UC‑15e). `asegurar_instantanea`
congela desde el catálogo vigente las partidas que no la tienen, solo si el catálogo todavía
reproduce su PU.

**Versiones y registro (SF‑E2).**

| Entidad (tabla) | Atributos | Notas |
|---|---|---|
| `VersionOrigen` (`version_origen`) | `presupuesto_id` (PK), `origen_id` (anulable), `motivo` | de qué versión salió otra; `motivo` ∈ `edicion`, `restauracion`, `cotizacion`, `revaloracion` (`models.MOTIVOS_VERSION`). La guarda **toda** versión nueva que no se elabora de cero. Cierra la limitación C3.2 de `DescarteVersion` (§2.2): la **versión vigente** es la de mayor `id` no descartada (`core.budget.version_vigente`) |
| `RegistroCambio` (`registro_cambio`) | `id`, `proyecto_id`, `version_origen_id`, `version_resultante_id`, `objeto`, `clave`, `campo`, `valor_anterior`, `valor_nuevo`, `fuente`, `responsable`, `fecha_hora` | una fila por celda cambiada; valores como texto; `objeto` ∈ `metraje`, `apu`, `cantidad`, `precio`, `plan`, `parametro`, `version`. **Fuente del cambio y responsable obligatorios** |

**Restaurar** la versión N crea una versión nueva copia de N (renglones, ítems, pendientes, curva,
plan, instantánea, hallazgos), con `VersionOrigen` (motivo `restauracion`, origen N) y su
`RegistroCambio`; nada se borra (RF‑54).

**Origen de precios y cotizaciones (SF‑E7).**

| Entidad (tabla) | Atributos | Notas |
|---|---|---|
| `ListaPreciosOrigen` (`lista_precios_origen`) | `lista_id` (PK), `tasa`, `fecha_tasa`, `alcance`, `proyecto_id`, `lista_base_id` | una lista sin fila es **global**. Una lista de alcance `proyecto` nace de una cotización (copia de `lista_base_id`) y la versión la referencia explícitamente (DA‑SF‑9); `Catalogo.lista_vigente` la excluye |
| `ReferenciaPrecio` (`referencia_precio`) | `precio_id` (PK), `referencia` | la referencia de un `PrecioInsumo` en su lista (el Ref de MaPreX) |
| `Cotizacion` (`cotizacion`) | `id`, `lista_id`, `insumo_id`, `precio`, `precio_base`, `proveedor`, `numero`, `fecha` | cotizaciones **activas** de una lista de proyecto; única por (lista, insumo) |

Al revalorar por UC‑02 una versión con lista de proyecto, `actualizar_precios` crea una lista de
proyecto nueva (copia de la lista base nueva con las cotizaciones activas repuestas): la cotización
prevalece hasta `retirar_cotizacion`, que también deja su `RegistroCambio`. El historial `CambioPrecio`
compara siempre listas base.

**Tablas `esp_*` del adaptador `adapters/espacio`** (DA‑SF‑2). Las crea `crear_esquema_espacio()`, no
`crear_esquema`. Todas llevan la **clave de versión** (id del presupuesto) **sin clave foránea**,
porque el adaptador no importa `core.models`; el borrado de proyecto lo hace `adapters.espacio.borrar_proyecto(...)`, que invoca `ui.hoja` (la API no borra proyectos). Mientras no se invoque, pueden quedar filas `esp_*` huérfanas: deuda explícita de SF. Las versiones
que no crea la hoja (restaurar, cotizar, revalorar) no copian filas `esp_*`: su espacio es el de su
`version_origen`, subiendo por la cadena hasta la primera con filas propias (spec §5.3).

| Tabla | Columnas |
|---|---|
| `esp_ambientes` | id, nombre, x0, y0, largo, ancho, alto, origen de medida |
| `esp_fuentes` | id, especialidad, tipo (acometida o montante de agua, colector de drenaje, rack, tablero), ambiente, x, y, z, origen |
| `esp_circuitos` | id, tablero, número, conductores (fase, neutro, tierra), calibre, puntos máximos, orden de la cadena |
| `esp_puntos` | id, especialidad, tipo (agua fría, drenaje, datos, tomacorriente, iluminación), ambiente, superficie (pared, techo, piso), x, y, z, fuente, circuito, especificaciones (diámetro, calibre, categoría), origen |
| `esp_recorridos` | id, punto o circuito, propuesto o declarado, vértices declarados |
| `esp_tramos` | recorrido, orden, superficie (pared, techo, plafón, piso, bandeja), empotrado o expuesto, vértices, pendiente (drenaje), longitud calculada |
| `esp_segmentos` (derivada) | resultado de la unión de tramos (spec §6.5), con sobrescritura opcional de diámetro y de empotrado |
| `esp_origenes` | id, tipo (plano, DXF, IFC, levantamiento en sitio, supuesto), referencia obligatoria por tipo, fecha, responsable |

Coordenadas en metros, eje z hacia arriba desde el piso terminado; tolerancia geométrica 0,001 m. Los
valores dimensionales se guardan con `DecimalExacto` (§7.1), como el resto del esquema. El origen de la
medida es de la **fila** (de dónde sale el dato); la fuente del cambio es del `RegistroCambio` (por
qué se cambió): se piden por separado. El espacio no se serializa dentro de `ItemComputo.parametros`
(`Mapping[str, Decimal]`, no admite texto) ni en `especificaciones` (R4 haría ruido): R8 a R10 reciben
la instantánea del espacio de la versión (DA‑SF‑8).

### 2.5 Enmienda de Sílice 0.6.0 (S1): moneda, origen de precios, lista de empresa e índices del BCV

Fuente: [spec S1 §5.2](especificaciones/2026-10-11-silice-s1-moneda-reajuste-design.md). Todas las tablas son aditivas (ruling SF3‑E0: tablas, no columnas); entran con revisiones de Alembic propias (`caso_0002` a `caso_0004`) y no alteran ninguna tabla existente. La **empresa va como texto** (`empresa_nombre`, `empresa_rif`), sin clave foránea a `instalacion.db` hasta S3 (RV‑6, ruling RV‑6 ratificado por Eugenio el 2026‑10‑11). Las tablas de las secciones 1 a 4 de este modelo no cambian. Las pruebas de estas tablas aún no existen: se escriben en cada fase de núcleo.

| Tabla | Columnas | Expediente |
|---|---|---|
| `serie_indice` | `id`, `codigo` (único), `nombre`, `organismo`, `unidad`, `periodicidad` (diaria, mensual, trimestral, anual), `base` (texto tal como lo trae el archivo) | SL‑E1 |
| `importacion_indice` | `id`, `serie_id`, `archivo`, `huella` (SHA‑256), `fuente` (dirección declarada), `fecha_descarga`, `fecha_importacion`, `responsable`, `filas_leidas`, `filas_rechazadas`, `informe` (texto) | SL‑E1 |
| `valor_indice` | `id`, `serie_id`, `importacion_id`, `fecha` (fecha valor o primer día del período), `valor`, `provisional` | SL‑E1; única por (`serie_id`, `fecha`, `importacion_id`) |
| `moneda_proyecto` | `id`, `proyecto_id`, `moneda`, `desde` (fecha y hora), `version_id`, `responsable`, `fuente` | SL‑E1; historial: la vigente es la última; sin filas, la de su versión vigente |
| `precio_origen` | `precio_id` (PK → `precio_insumo`), `moneda_original`, `precio_original`, `fecha_precio`, `tasa`, `fecha_tasa`, `fuente_tasa` (id de importación o texto), `fuente` | SL‑E1 |
| `lista_empresa` | `lista_id` (PK), `empresa_nombre`, `empresa_rif` (texto, instantánea sin clave foránea a `instalacion.db`; RV‑6, ratificada por Eugenio el 2026‑10‑11, P1), `lista_base_id`, `lista_referencia_id` (MaPreX), `plazo_vigencia_dias`, `rango_inferior`, `rango_superior` | SL‑E2 |
| `clausula_reajuste`, `componente_clausula` | §8.1 | SL‑E3 |
| `estudio_reajuste`, `periodo_reajuste`, `ejecutado_periodo` | §8.5 | SL‑E3 |

**Migraciones (RV‑1, RV‑3).** La 0.6.0 **empieza** con S5‑1 adelantado: Alembic con su revisión base = esquema
de la 0.5.0, respaldo, `operacion.base_datos.preparar_base` y casos en `datos\casos\`. S5 conserva la propiedad
del spec de Alembic; S1 solo agrega **su** revisión con las tablas de esta sección (todas aditivas, sin
`ALTER TABLE` sobre tablas existentes). Las bases anteriores (clínica, TI‑001, importadas, de la 0.5.0) entran
por la **revisión base** de Alembic y suben a `head` con la revisión de S1 al abrirse por `preparar_base`; S1
no usa `stamp`. La prueba de deriva (RNF‑20, de S5) está activa desde S1: una base llevada a `head` es igual a
la creada desde los metadatos. Como Alembic ya está, un cambio posterior de columnas (p. ej. la cita a la
valuación que agrega S2 en `ejecutado_periodo`, §8.6) es una revisión más, no una tabla rehecha.

### 2.6 Tablas del asistente `ia_*` (S4)

Fuente: [spec S4](especificaciones/2026-10-11-silice-s4-asistente-ia-design.md) §5.5. Tablas **aditivas** de la
base del **caso**, propias del paquete `asistente/` (como las `esp_*` del adaptador del espacio): no cuentan entre
las entidades de `core/models` y **no tienen clave foránea a `core/models`**. Las crea una revisión propia de
Alembic (tarea 9 de `PLAN_SILICE_090.md`) y `asistente` figura en la lista `METADATAS` del caso.

| Tabla | Columnas |
|---|---|
| `ia_sesiones` | identificador, proyecto, versión de partida, versión guardada (si se guardó), proveedor, modelo pedido, pedido, topes (turnos, llamadas, costo), inicio, fin, motivo de fin |
| `ia_turnos` | sesión, orden, modelo que respondió, fin del turno, uso de fichas, costo estimado, texto del modelo |
| `ia_llamadas` | turno, orden, herramienta, argumentos en JSON con claves ordenadas, resultado de la validación, motivo |
| `ia_propuestas` | sesión, identificador, tipo, estado (pendiente, aceptada, editada, rechazada), quién y cuándo decidió |

La clave de IA de la empresa nunca se guarda aquí (RNF‑18 c).

## 3. Diagrama entidad‑relación

```mermaid
erDiagram
    PROYECTO {
        int id PK
        string nombre UK
        string descripcion
        string dominio
    }
    PRESUPUESTO {
        int id PK
        int proyecto_id FK
        int lista_precios_id FK
        string codigo
        date fecha
        string moneda
        decimal fcas
        decimal bono_alimentacion
        decimal administracion
        decimal utilidad
    }
    PARTIDA_PRESUPUESTADA {
        int id PK
        int presupuesto_id FK
        int partida_id FK
        int item_computo_id FK
        int orden
        decimal cantidad
        decimal materiales
        decimal equipos
        decimal mano_obra
        decimal costo_directo
        decimal con_administracion
        decimal precio_unitario
        decimal total
    }
    PUNTO_CURVA {
        int id PK
        int presupuesto_id FK
        int orden
        string periodo
        decimal monto
        decimal acumulado
    }
    ITEM_COMPUTO {
        int id PK
        int presupuesto_id FK
        string codigo_partida
        string descripcion
        string unidad_original
        string unidad
        decimal cantidad
        string origen_id
        string origen_tipo
        string dominio
        string regla
        string parametros
        string especificaciones
    }
    PARTIDA {
        int id PK
        string codigo UK
        string codigo_covenin
        string descripcion
        string unidad
        string dominio
    }
    INSUMO {
        int id PK
        string codigo UK
        string tipo
        string descripcion
        string unidad
    }
    COMPOSICION_APU {
        int id PK
        int partida_id FK
        int insumo_id FK
        decimal cantidad
        decimal depreciacion
        string modalidad
        int orden
    }
    RENDIMIENTO {
        int id PK
        int partida_id FK
        int ejecucion_id FK
        decimal valor
        string tipo
        date fecha
        string condiciones
    }
    JUSTIFICACION_RENDIMIENTO {
        int rendimiento_id PK, FK
        string texto
        string advertencia
        date fecha
    }
    EJECUCION {
        int id PK
        int proyecto_id FK
        string referencia UK
        date fecha_inicio
        date fecha_fin
        string descripcion
    }
    LISTA_PRECIOS {
        int id PK
        string nombre
        string moneda
        date fecha_vigencia
        string origen
    }
    PRECIO_INSUMO {
        int id PK
        int lista_id FK
        int insumo_id FK
        decimal precio
    }
    CAMBIO_PRECIO {
        int id PK
        int lista_anterior_id FK
        int lista_nueva_id FK
        int insumo_id FK
        decimal precio_anterior
        decimal precio_nuevo
        decimal variacion
        date fecha
    }
    INCIDENCIA_CAMBIO {
        int id PK
        int cambio_id FK
        int partida_id FK
        decimal precio_unitario_anterior
        decimal precio_unitario_nuevo
        decimal variacion
    }
    DESCARTE_VERSION {
        int presupuesto_id PK, FK
        date fecha
    }
    HALLAZGO {
        int id PK
        int presupuesto_id FK
        string regla
        int severidad
        string descripcion
        decimal impacto
        string origen_ids
        decimal valor_observado
        decimal valor_esperado
    }

    PROYECTO ||--o{ PRESUPUESTO : tiene
    PROYECTO ||--o{ EJECUCION : ejecuta
    PRESUPUESTO }o--|| LISTA_PRECIOS : "se valora con"
    PRESUPUESTO ||--o{ PARTIDA_PRESUPUESTADA : contiene
    PRESUPUESTO ||--o{ PUNTO_CURVA : planifica
    PRESUPUESTO ||--o{ HALLAZGO : audita
    PRESUPUESTO ||--o{ ITEM_COMPUTO : computa
    PRESUPUESTO ||--o| DESCARTE_VERSION : "se descarta en"
    ITEM_COMPUTO ||--o| PARTIDA_PRESUPUESTADA : "se valora en"
    PARTIDA ||--o{ PARTIDA_PRESUPUESTADA : "se presupuesta en"
    PARTIDA ||--o{ COMPOSICION_APU : "se desglosa en"
    PARTIDA ||--o{ RENDIMIENTO : "rinde segun"
    RENDIMIENTO ||--o| JUSTIFICACION_RENDIMIENTO : "se justifica en"
    PARTIDA ||--o{ INCIDENCIA_CAMBIO : "se encarece en"
    INSUMO ||--o{ COMPOSICION_APU : participa
    INSUMO ||--o{ PRECIO_INSUMO : "cotiza en"
    INSUMO ||--o{ CAMBIO_PRECIO : afecta
    LISTA_PRECIOS ||--o{ PRECIO_INSUMO : agrupa
    LISTA_PRECIOS ||--o{ CAMBIO_PRECIO : registra
    CAMBIO_PRECIO ||--o{ INCIDENCIA_CAMBIO : repercute
    EJECUCION ||--o{ RENDIMIENTO : mide
```

Cardinalidades en palabras:

- Un proyecto tiene cero o más presupuestos; un presupuesto pertenece a exactamente un proyecto.
- Un presupuesto se valora con exactamente una lista de precios; una lista puede valorar muchos.
- Un presupuesto contiene cero o más renglones, cero o más puntos de curva y cero o más hallazgos.
- Un renglón presupuestado corresponde a exactamente un `ItemComputo` y a exactamente una `Partida`;
  un `ItemComputo` del presupuesto sin renglón es un ítem pendiente (UC‑01 3a). El «a lo sumo un
  renglón por ítem» (`ITEM_COMPUTO ||--o| PARTIDA_PRESUPUESTADA`) es regla de negocio, **no la impone
  el esquema**: `partida_presupuestada.item_computo_id` no lleva `UNIQUE`
  (`core/models/entidades.py:373`). La garantiza la persistencia: `guardar_presupuesto` crea un
  `ItemComputo` nuevo por cada renglón y uno por cada pendiente, sin reutilizar ninguno
  (`core/budget/persistencia.py:156-165`).
- Una partida se desglosa en una o más líneas de composición; cada línea referencia un insumo.
- Un insumo cotiza a lo sumo una vez por lista (`UNIQUE (lista_id, insumo_id)`).
- Una partida tiene cero o más rendimientos; un rendimiento medido pertenece a una ejecución.
- Un rendimiento tiene a lo sumo una justificación (`JustificacionRendimiento`, UC‑06 4a).
- Un cambio de precio repercute en cero o más partidas (`IncidenciaCambio`).
- Un presupuesto tiene a lo sumo una marca de descarte (`DescarteVersion`, UC‑02 7a).

Cobertura de los once casos de uso (UC‑09 está vacante):

| UC | Entidades que lo sostienen |
|---|---|
| UC‑01 Elaborar presupuesto | `Proyecto` (paso 1, `POST /proyectos` desde C6), `ItemComputo` (los pendientes, sin renglón), `Partida`, `ComposicionAPU`, `Rendimiento`, `ListaPrecios`, `PrecioInsumo`, `Presupuesto`, `PartidaPresupuestada`, `PuntoCurva`, `Hallazgo` (el `PENDIENTE` de 3a) |
| UC‑02 Actualizar precios | `ListaPrecios`, `PrecioInsumo`, `CambioPrecio`, `IncidenciaCambio`, `DescarteVersion` (flujo 7a), `Insumo` (los dados de alta del flujo 2a, C6) |
| UC‑03 Reutilizar partidas | `Partida.descripcion` (índice), `ComposicionAPU`, `Insumo` |
| UC‑04 Recalcular alcance | `ItemComputo.regla`, `ItemComputo.parametros` |
| UC‑05 Auditar | `Hallazgo`, `ItemComputo.origen_id`, `PartidaPresupuestada`, `PuntoCurva`; al importar el archivo de un tercero (C6), además `Partida`, `Insumo`, `ComposicionAPU`, `Rendimiento` (los APU del tercero) y la `ListaPrecios` «Importada» con sus `PrecioInsumo` |
| UC‑06 Rendimientos reales | `Rendimiento`, `Ejecucion`, `JustificacionRendimiento` (flujo 4a, C6) |
| UC‑07 Precio de mercado | `PartidaPresupuestada.precio_unitario`, `PrecioInsumo`, `CambioPrecio`, `Hallazgo` (el `ATIPICO` de la versión revalorada, paso 5, C6) |
| UC‑08 Sensibilidad | parámetros congelados en `Presupuesto` + `ComposicionAPU`; el escenario no se persiste |
| UC‑10 Componer una partida | `Partida`, `Insumo` (y sus variantes, §6), `ComposicionAPU` (con `modalidad`), `PrecioInsumo` de la lista vigente, `Rendimiento` estimado con sus `condiciones` |
| UC‑11 Editar una partida compuesta | `ComposicionAPU` (las líneas se reemplazan), `Rendimiento` (si cambió, se agrega uno nuevo y el anterior queda en el histórico de la partida) |
| UC‑12 Recorrer la aplicación guiado | ninguna propia: el estado del caso abierto cuenta `Partida` e `Insumo` y lee la `ListaPrecios` vigente |

## 4. Normalización

### 4.1 Justificación de la tercera forma normal

El esquema está en 3FN. Se comprueba entidad por entidad sobre las dependencias funcionales reales:

- **1FN.** Ningún atributo es multivaluado ni repetitivo. Donde el contrato tiene una colección
  (`ComposicionAPU.materiales`, `Presupuesto.partidas`, `Presupuesto.curva`) el modelo tiene una tabla
  hija con clave foránea. Las dos únicas columnas con estructura interna son
  `ItemComputo.parametros`/`especificaciones` y `Hallazgo.origen_ids`: se justifican en §4.3.
- **2FN.** Toda tabla tiene clave primaria subrogada de un solo atributo, de modo que no existen
  dependencias parciales. Las claves naturales que sí son compuestas se declaran como
  `UniqueConstraint` (`(lista_id, insumo_id)`, `(proyecto_id, codigo)`) y todos los atributos no clave
  de esas tablas dependen del par completo: `PrecioInsumo.precio` no depende solo del insumo ni solo
  de la lista.
- **3FN.** No hay dependencias transitivas. Los tres casos que las habrían producido se resolvieron
  extrayendo tablas:
  1. *El precio no es atributo del insumo.* `precio` depende de (insumo, lista de precios), no del
     insumo. Ponerlo en `Insumo` habría creado `Insumo.id → Insumo.precio_vigente → fecha` y habría
     hecho imposible reconstruir un presupuesto pasado. De ahí `PrecioInsumo`.
  2. *La cantidad y la depreciación no son atributos del insumo ni de la partida.* Dependen del par
     (partida, insumo): la línea base demuestra que el mismo vehículo de transporte lleva 1,00 en
     cuatro APU y 0,03 en el quinto (hallazgo 7). De ahí `ComposicionAPU`.
  3. *El rendimiento no es atributo de la partida.* Una partida acumula varios rendimientos a lo
     largo del tiempo y con distinta procedencia (estimado / medido). De ahí `Rendimiento`, y de ahí
     que `Ejecucion` sea entidad propia en vez de una cadena repetida en cada fila.
- **Moneda.** `Presupuesto.moneda` y `ListaPrecios.moneda` coexisten a propósito: la moneda de la
  lista es la de sus precios y la del presupuesto es la de presentación. No es transitividad, son dos
  hechos distintos; que hoy coincidan (USD) es circunstancial.

### 4.2 Desnormalizaciones deliberadas

Cuatro, todas del mismo tipo: **valores derivados que se almacenan porque su recálculo futuro no
tiene por qué dar el mismo número que dio el día en que se emitió el documento.**

| Dónde | Qué se duplica | Por qué |
|---|---|---|
| `PartidaPresupuestada.materiales … precio_unitario, total` | el `ResultadoAPU` completo del renglón | **la desnormalización principal.** Es la instantánea del versionado híbrido (§5): el presupuesto emitido es un documento con valor contractual y debe poder mostrarse tal como se firmó, aunque después cambien la composición, el rendimiento o la lista. Sin ella, «reconstruir» sería «recalcular», y un cambio de catálogo alteraría retroactivamente presupuestos ya entregados |
| `Presupuesto.fcas, bono_alimentacion, administracion, utilidad` | los cuatro `ParametrosCosto` | los valores por defecto del contrato pueden cambiar (una reforma de prestaciones); el presupuesto conserva los que se le aplicaron |
| `PuntoCurva.acumulado` | suma de los montos anteriores | la regla R2 audita el acumulado **tal como lo escribió el proyectista**. Si se calculara al vuelo, el sistema nunca podría detectar el hallazgo 3 (curva que cierra en 99,30 %), que es precisamente lo que debe detectar |
| `CambioPrecio.variacion`, `IncidenciaCambio.variacion` | (nuevo − anterior) / anterior | se congela con la aritmética `Decimal` del momento del cambio y sirve de columna de ordenación y filtrado en UC‑02 sin expresión calculada |

`PartidaPresupuestada.cantidad` es un quinto caso menor: copia de `ItemComputo.cantidad` por la misma
razón (el cómputo puede corregirse después; el renglón emitido no cambia).

Las cuatro se declaran aquí para que ninguna se tome por descuido: fuera de esta lista, ningún valor
derivado se almacena.

### 4.3 Columnas JSON‑texto

`ItemComputo.parametros`, `ItemComputo.especificaciones` y `Hallazgo.origen_ids` guardan un objeto o
una lista serializados como texto JSON. Es una excepción consciente a la 1FN estricta:

- son **diccionarios abiertos** cuyas claves las decide cada adaptador (`a`, `h`, `e` en civil;
  `longitud_enlace` en telecom). Normalizarlos exigiría una tabla llave‑valor genérica, que en la
  práctica es peor: no aporta integridad referencial (las claves no están en ningún catálogo) y
  multiplica las lecturas;
- nunca se consultan por su contenido: se leen enteros para reevaluar la regla (R1) o comparar
  especificaciones (R4). No hay ninguna consulta de la forma «cantidades con `diametro = 4 pulg`»;
- los valores `Decimal` de `parametros` se serializan como **cadena** (`{"a": "0.80"}`), no como
  número JSON, para que la ida y vuelta sea exacta (§7.1).

Si en el futuro apareciera una consulta por contenido, el reemplazo natural es `JSONB` en PostgreSQL
con índice GIN, sin cambiar el resto del esquema.

## 5. Estrategia de versionado

**Híbrida: el presupuesto referencia su lista de precios y además congela el resultado valorado.**

1. `ListaPrecios` es **inmutable una vez que un presupuesto la referencia**. Actualizar precios no es
   editar una lista: es crear una lista nueva con `fecha_vigencia` posterior y registrar en
   `CambioPrecio` las diferencias insumo por insumo.
2. `Presupuesto.lista_precios_id` deja constancia de con qué precios se valoró, y los cuatro
   parámetros de costo quedan copiados en la propia fila.
3. `PartidaPresupuestada` congela el `ResultadoAPU` de cada renglón. Es la parte «documento» del
   modelo: lo que se firmó.
4. **Reconstruir a fecha = valorar con la lista vigente a esa fecha.**
   `Catalogo.lista_vigente(fecha)` devuelve la lista de mayor `fecha_vigencia ≤ fecha`, y
   `Catalogo.composicion(codigo, fecha)` arma la `ComposicionAPU` con los precios de esa lista y con
   el rendimiento **estimado** más reciente cuya `fecha ≤ fecha`. Ese es el mecanismo que sostiene
   UC‑02: comparar el mismo APU valorado con dos listas distintas.
5. **Descartar una versión no la borra.** La versión revalorada que el usuario descarta (UC‑02,
   flujo 7a) recibe una marca en `DescarteVersion` (§2.2): sigue guardada, sigue reconstruyéndose
   como cualquier otra y su historial (`CambioPrecio`, `IncidenciaCambio`) se conserva.

Las dos vías responden preguntas distintas y por eso conviven:

| Pregunta | Se responde con |
|---|---|
| ¿Qué decía el presupuesto que emitimos el 28/04/2026? | la instantánea de `PartidaPresupuestada` |
| ¿Cuánto costaría hoy ese mismo APU? | `Catalogo.composicion(codigo)` con la lista vigente |
| ¿Cuánto subió y por culpa de qué insumo? | `CambioPrecio` + `IncidenciaCambio` |

Consecuencia operativa: **`seed.py` y `cargar_composicion` nunca modifican una lista ya usada**; si un
precio difiere del que ya tiene un insumo en esa lista, se crea una variante de insumo (§6), no se
sobreescribe el precio.

Lo que este esquema **no** versiona todavía, y se declara como limitación: las líneas de
`ComposicionAPU` no tienen vigencia temporal. Cambiar el desglose de una partida (añadir un insumo,
cambiar una cantidad) altera el APU reconstruible a fechas pasadas.

**Corrección (SF0, 2026‑10‑04; spec SF §1.2).** Una versión anterior de este párrafo afirmaba que
esto «no afecta a los presupuestos emitidos», porque estarían congelados en `PartidaPresupuestada`.
La recarga demuestra lo contrario: `cargar_presupuesto` reconstruye cada APU desde la composición
del catálogo y exige que el precio unitario cuadre con la instantánea del renglón
(`core/budget/persistencia.py:403-425`), de modo que editar un APU rompe la recarga de cualquier
presupuesto anterior que lo use. Lo congelado es el resultado valorado, no la composición que lo
produjo. La extensión se hace en el sprint final (SF‑E6, §2.4) con una **instantánea de la
composición y del rendimiento por versión**, no con `vigente_desde`/`vigente_hasta`: cada versión
guarda las líneas con que se valoró y toda recarga las toma de ahí (solo las versiones anteriores a
SF‑E6 o importadas por UC‑05 usan el catálogo).

## 6. Insumos homónimos con precio distinto (hallazgo de datos de la Sesión I0.4)

La línea base contiene **cuatro pares de insumos con la misma descripción y precios distintos** en la
misma fecha:

| Insumo | Precio A | Dónde | Precio B | Dónde |
|---|---|---|---|---|
| Agua (m3) | 12,00 | vaciado de concreto | 2,00 | relleno compactado |
| Pala | 15,00 | excavación | 10,00 | vaciado de concreto |
| Cinta métrica | 15,00 | tubería | 160,00 | encofrado |
| Nivel de mano | 10,00 | encofrado | 40,00 | vaciado de concreto |

Con `UNIQUE (lista_id, insumo_id)` los dos precios no caben en la misma lista, y el modelo tiene
razón: **un insumo no puede costar dos cosas distintas el mismo día.** Se trata de un octavo defecto
del presupuesto auditado, del mismo tipo que el hallazgo 7 (depreciación no uniforme), y no de una
carencia del esquema.

Política de carga adoptada en `Catalogo.cargar_composicion`, para no alterar la línea base ni ocultar
el defecto:

1. buscar el insumo por (`tipo`, `descripcion`, `unidad`);
2. si existe y su precio en esa lista **coincide**, reutilizarlo;
3. si existe y su precio **difiere**, crear una **variante**: mismo `tipo`, misma `descripcion`, misma
   `unidad`, código con sufijo (`EQU-007-B`, `EQU-007-C`…), y devolverla en `ResumenCarga.variantes`.

Así los cinco APU se reconstruyen **idénticos** al fixture (que es la evidencia primaria y no se
toca), y a la vez queda una lista explícita de los insumos que el presupuesto original contradice.

Esto es candidato a una **regla R8, «precio uniforme del insumo»**: dos líneas de composición que
citan la misma descripción de insumo con precios distintos en la misma fecha son un hallazgo de
severidad ADVERTENCIA. Se decide con el tutor en la Sesión I4, igual que R7.

## 7. Tipos y decisiones de implementación

### 7.1 `DecimalExacto`: el tipo monetario y dimensional

NORMAS.md §2 exige `Decimal` en todo número monetario y dimensional, sin `float` en ningún punto del
camino. Sobre SQLite eso descarta las dos opciones evidentes:

- `Float` está prohibido por el principio;
- `Numeric` **no** resuelve el problema en SQLite: el motor no tiene tipo decimal nativo, SQLAlchemy
  almacena el valor como `REAL` y lo reconvierte a `Decimal` **pasando por `float`**, lo que emite un
  `SAWarning` en cada consulta y, sobre todo, admite pérdida de precisión.

Decisión: un `TypeDecorator` propio en `core/models/tipos.py`.

```python
class DecimalExacto(TypeDecorator):
    impl = String(40)
    cache_ok = True
    # bind:   Decimal -> str(valor)
    # result: str     -> Decimal(valor)
```

El valor viaja como **texto**, que conserva exactamente los dígitos y la escala del `Decimal`
original (`Decimal("0.415")` vuelve como `Decimal("0.415")`, no como `0.41499999…`). Consecuencias
aceptadas:

- las comparaciones y ordenaciones en SQL son lexicográficas, no numéricas. Ninguna consulta del
  sistema ordena ni filtra por un importe (se filtra por fecha, código, tipo y claves foráneas), así
  que el costo es nulo hoy y está declarado por si deja de serlo;
- la suite corre **sin advertencias**, que es el criterio de aceptación de la Sesión I0.4.

Portabilidad: en PostgreSQL se sustituye por `Numeric(18, 6)`, que sí es decimal exacto en el motor,
sin tocar los modelos más allá del alias del tipo. El mismo criterio de serialización como cadena se
aplica a los `Decimal` dentro de las columnas JSON‑texto (§4.3).

### 7.2 Índices

| Índice | Tabla | Columnas | Para qué |
|---|---|---|---|
| `uq_precio_insumo_lista_insumo` | `PrecioInsumo` | (`lista_id`, `insumo_id`) | **UC‑02**: precio de un insumo en una lista y unicidad del par. Sirve además de índice de cobertura para recorrer una lista completa |
| `ix_cambio_precio_lista_nueva` | `CambioPrecio` | (`lista_nueva_id`) | **UC‑02**: «qué insumos cambiaron al pasar a esta lista», la consulta que abre el informe de actualización |
| `ix_partida_descripcion` | `Partida` | (`descripcion`) | **UC‑03**: búsqueda y reutilización de partidas anteriores por descripción; también es el candidato de recall del normalizador semántico de I2 |
| `ix_insumo_tipo_descripcion` | `Insumo` | (`tipo`, `descripcion`) | resolución de insumos en `cargar_composicion` y detección de homónimos (§6) |
| `ix_lista_precios_fecha_vigencia` | `ListaPrecios` | (`fecha_vigencia`) | `lista_vigente(fecha)`: máximo `fecha_vigencia ≤ fecha` |
| `ix_rendimiento_partida_tipo_fecha` | `Rendimiento` | (`partida_id`, `tipo`, `fecha`) | rendimiento estimado más reciente a una fecha (§5) y separación estimado/medido de UC‑06 |
| `ix_composicion_partida_orden` | `ComposicionAPU` | (`partida_id`, `orden`) | reconstrucción del desglose en el orden del documento original |

Los índices de las claves foráneas restantes (`presupuesto_id` en `PartidaPresupuestada`,
`PuntoCurva`, `ItemComputo` y `Hallazgo`) los crea SQLite implícitamente al resolver las restricciones;
se añadirán explícitamente si el perfilado de I1 los reclama.

## 8. Decisiones ya tomadas

- Los códigos de partida de la línea base usan el prefijo `LB-` hasta que se cargue el catálogo COVENIN
  2000; `Partida` admite un `codigo_covenin` y conserva el código de origen en `codigo`.
- `ComposicionAPU` guarda la cantidad **y** el factor de depreciación por línea, porque la línea base
  demuestra que el factor varía entre APU para el mismo insumo (hallazgo 7). La regla R6 necesita ese dato.
- La unidad se persiste normalizada con `core.contracts.unidades.normalizar_unidad`, pero se conserva la
  unidad original escrita por el usuario en `ItemComputo.unidad_original` para que la regla R3 pueda
  reportarla.
- Los nombres de las entidades son los del diagrama ER aunque siete de ellos coincidan con nombres de
  `core.contracts` (`Presupuesto`, `PartidaPresupuestada`, `PuntoCurva`, `ItemComputo`,
  `ComposicionAPU`, `Rendimiento`, `Hallazgo`). El código los usa **siempre cualificados**
  (`from core import models` → `models.Presupuesto`). La frontera modelo↔contrato se cruza en dos
  lugares y solo en dos: `core/catalog/mapeo.py` para el catálogo (partidas, insumos, composiciones,
  rendimientos) y `core/budget/persistencia.py` para el presupuesto emitido (renglones, curva,
  hallazgos, ítems de cómputo). Hallazgo de la Sesión 0.3: la formulación anterior ("único lugar")
  quedó desactualizada al implementar I0.5.
- Las enumeraciones (`dominio`, `tipo` de insumo, `tipo` de rendimiento, `origen_tipo`) se persisten
  como **texto** con el valor del `StrEnum`, y `severidad` como **entero** con el valor del `IntEnum`.
  No se usa `sqlalchemy.Enum`: el tipo nativo obligaría a una migración de esquema cada vez que se
  añade un dominio, y el sistema está diseñado para admitir dominios nuevos sin tocar el núcleo.
