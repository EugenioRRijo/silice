# Expedientes del núcleo de SF3 (SF3‑E0, SF‑E2, SF‑E3, SF‑E4, SF‑E6, SF‑E7, SF‑E8, SF‑E9)

**Contenido de este archivo:** SF3‑E0 (tablas aditivas), SF‑E2 (edición y versiones), SF‑E3 (punto de equilibrio),
SF‑E4 (Excel), SF‑E6 (instantánea), SF‑E7 (origen de precios), SF‑E8 (revalorar) y SF‑E9 (`siguiente_codigo`).
**Índice cruzado:** SF‑E1 (reglas externas en cada camino de auditoría) y SF‑E5 (R4 compara especificaciones
normalizadas) están en la bitácora principal, [2026-10-sf.md](2026-10-sf.md), sección «SF1».

**Fecha:** 2026‑10‑05 · **Rama:** `inc/sf3-nucleo` (apilada sobre `inc/sf2`) · **Plan:** [PLAN_SF.md](../../PLAN_SF.md),
fase SF3, tareas 3.1 a 3.5 · **Spec:** [2026-10-04-sprint-final-prototipo-design.md](../especificaciones/2026-10-04-sprint-final-prototipo-design.md)
§5.1 a §5.5, §8.4, §9.3 a §9.6, §11.2 y §12.3 · **Bitácora de la fase:** [2026-10-sf.md](2026-10-sf.md), «SF3».

Cada expediente sigue el método de C5 y C6
([2026-09-28-C5-expedientes.md](2026-09-28-C5-expedientes.md),
[2026-09-29-C6-expedientes.md](2026-09-29-C6-expedientes.md)): la regla que lo motiva, por qué es genérico
(ningún expediente nombra el agua, los datos ni la electricidad), la prueba que lo demuestra, el impacto y el
costo si es erróneo. La prueba en rojo de cada pieza se commitea **antes** que su implementación. Esta rama
solo toca `core/`, `tests/`, `docs/` y `scripts/analisis_ti001.py` (la guardia de la CI y la meta M9 fallan si
una rama que agrega archivos en `adapters/` toca `core/`); ningún contrato de `core/contracts/` cambia (NORMAS §5).

## SF3‑E0: tablas aditivas, no columnas (ruling común de esquema)

- **Regla que lo motiva:** el proyecto no tiene herramienta de migración y `create_all` no altera tablas
  existentes (hallazgo P2, [2026-09-20-P2-hallazgo-migraciones.md](2026-09-20-P2-hallazgo-migraciones.md);
  precedentes C3.2 y C6.1). Una columna nueva en una tabla existente haría fallar toda base anterior (clínica,
  TI‑001, importadas).
- **Por qué es genérico:** es una decisión de persistencia, no de dominio: todo lo que SF3 agrega son **tablas
  aditivas** que `crear_esquema` crea en una base anterior sin `ALTER TABLE` y sin tocar sus filas. Lo que el
  spec llama «columna» (`Presupuesto.version_origen`; tasa, fecha de la tasa y alcance de `ListaPrecios`;
  referencia de `PrecioInsumo`) se guarda en una tabla con la misma clave.
- **Prueba que lo demuestra:** `test_cotizacion_proyecto.py::test_una_base_sin_las_tablas_de_origen_abre_y_cotiza`
  y su equivalente de instantánea, `test_instantanea_composiciones.py::test_una_base_con_el_esquema_anterior_abre_y_gana_las_tablas`
  (una base anterior abre, recarga y gana las tablas sin perder filas).
- **Impacto:** `lista_vigente` filtra con una subconsulta y las bases existentes no tienen filas en las tablas
  nuevas, así que todas sus listas son globales; ninguna lectura anterior cambia.
- **Costo si es errónea:** si se prefieren columnas, se agrega un `ALTER TABLE … ADD COLUMN` por columna y se
  mueven las lecturas (cinco consultas).

---

## SF‑E6: instantánea de composiciones, rendimientos y plan por versión (tarea 3.1)

- **Regla que lo motiva:** spec §1.2, §5.2 (fila SF‑E6), §9.3 y DA‑SF‑7. `cargar_presupuesto` reconstruye cada
  APU desde la composición del catálogo y exige que el PU cuadre con el renglón
  (`core/budget/persistencia.py`, `_a_contrato_renglon`); el catálogo guarda **una** composición por partida y
  `reemplazar_composicion` la sustituye en el sitio. Resultado: editar un APU rompe la recarga (`ValueError`
  «no se reconstruye») de toda versión anterior que lo use. Sin SF‑E6 la hoja no puede editar un APU (RF‑53,
  RF‑54, spec §12.3).
- **Por qué es genérico:** guardar «con qué líneas se valoró cada versión» no depende de ningún dominio ni
  especialidad: es la mitad que faltaba del versionado híbrido de `modelo_datos.md` §5 (se congelaba el
  resultado, no la composición). La instantánea guarda el `ComposicionAPU` del contrato tal cual, así que
  **el contrato no cambia**.
- **Diseño:** tres tablas aditivas en `core/models/entidades.py`.
  1. `ComposicionVersion` (`composicion_version`): una por (versión, código de partida): descripción, unidad y
     **rendimiento** (la instantánea de rendimientos es esta columna: el rendimiento vigente de la partida en
     esa versión).
  2. `LineaComposicionVersion` (`linea_composicion_version`): una por línea, en el orden canónico de
     `core.catalog.mapeo.lineas_de` (materiales, equipos, mano de obra): tipo, descripción, unidad, cantidad,
     precio (el que valoró la versión), depreciación, modalidad e `insumo_id` (anulable: de qué insumo del
     catálogo salió, para revalorar con otra lista).
  3. `PlanVersion` (`plan_version`): el reparto del plan de trabajo (período, etiqueta, partida, fracción).
     **Ampliación declarada del expediente:** la curva guardada (`PuntoCurva`) no conserva el reparto por
     partida, y RF‑56 («la versión resultante conserva el plan y la curva») y RF‑54 (restaurar) no se pueden
     cumplir sin él. Mismo patrón y misma justificación que la instantánea de composiciones.
  `core/budget/instantanea.py` (nuevo) contiene todo lo que lee o escribe esas tablas:
  `congelar(session, modelo, presupuesto, lista, plan)`, `composiciones_de_version`,
  `composiciones_de_presupuesto` (instantánea y, solo si falta, catálogo: lo que usan escenarios y la hoja),
  `composiciones_revaloradas` (UC‑02: líneas de la instantánea con los precios de la lista nueva),
  `plan_de_version`, `asegurar_instantanea` (UC‑15e) y `tiene_instantanea`.
  - `guardar_presupuesto` **siempre** congela (una por código de partida distinto, con el `apu` del renglón) y
    gana `plan=None` (sin él, se infiere de la curva solo si cada partida está en un único período: fracción 1;
    si no es inferible no se guarda plan y la versión queda «sin plan», como hoy).
  - La recarga (`_presupuesto_de`), la verificación de PU, `actualizar_precios` (composiciones e incidencias) y
    `composiciones_de_presupuesto` toman la composición **por código de partida**: de la instantánea si la
    versión la tiene, y del catálogo (con la lista y la fecha del presupuesto, como hoy) si no. El criterio es
    por partida y no por versión: una base anterior a SF‑E6 abre, y una instantánea parcial (UC‑15e) también.
  - `asegurar_instantanea(session, proyecto, codigo, catalogo)` crea desde el catálogo vigente la instantánea
    de las partidas que no la tienen **si el catálogo todavía reproduce su PU** (tolerancia
    `TOLERANCIA_RECONSTRUCCION`); las que no tienen composición, o cuyo PU ya no cuadra, se devuelven en
    `sin_composicion` (la hoja las deja en solo lectura, UC‑15e). Es idempotente. El registro de que se creó
    (UC‑15e: «y lo registra») lo escribe la tarea 3.2, que es la dueña de `RegistroCambio`.
  - Una base sin las tablas nuevas abre: `crear_esquema` las agrega vacías y todo cae al catálogo (FR‑5: la
    clínica y TI‑001 sembradas antes de SF3 no tienen instantánea y siguen cargando idénticas).
- **Prueba que lo demuestra** (`tests/integration/test_instantanea_composiciones.py`): **editar un APU en el
  catálogo no rompe la recarga de la versión anterior** (hoy da `ValueError`); lo mismo con un rendimiento
  nuevo; la revaloración UC‑02 usa las líneas congeladas (cuantía exacta calculada a mano); una versión sin
  instantánea sigue el camino del catálogo y **sí** denuncia un catálogo desligado; una base con el esquema
  anterior (sin las tablas nuevas) abre y se ensancha; `asegurar_instantanea` crea, es idempotente y reporta lo
  que no puede; la instantánea y el plan hacen ida y vuelta exactos (`Decimal` como cadena).
- **Impacto:** `guardar_presupuesto` agrega filas (tamaño: una por línea de APU de cada partida distinta, unas
  decenas por versión); la recarga lee esas filas en vez de armar el contrato desde `partida.composicion`. Los
  cinco APU de la línea base siguen en ±0,01, 7 de 7 intacto. Los llamadores de `ui/` y `api/` que arman
  composiciones con `catalogo.composiciones` para escenarios deben pasar a `composiciones_de_presupuesto`: es
  trabajo de la rama `inc/sf3` (esta no toca `ui/` ni `adapters/`).
- **Alternativas descartadas:** `vigente_desde`/`vigente_hasta` en `ComposicionAPU` (modelo_datos §5: cada
  consulta del catálogo cambia y los APU anteriores quedan sin fecha); guardar el JSON del `ComposicionAPU` en
  una columna de texto (no consultable por insumo, que es lo que necesitan las incidencias de UC‑02).
- **Costo si es erróneo:** si el tutor rechaza la tabla de líneas, la hoja no puede editar un APU (queda de
  solo lectura) y la recarga vuelve a depender del catálogo; el resto de SF3 no cambia.
- **Implementación y rojo observado (2026‑10‑05):** `core/budget/instantanea.py` (nuevo), `core/models/entidades.py`
  (tres tablas), `core/budget/persistencia.py` (`guardar_presupuesto` congela y gana `plan`, `version_origen` y
  `motivo`; la recarga toma la composición por código de partida) y `core/budget/actualizacion.py` (composiciones
  revaloradas e incidencias desde la instantánea). Prueba: `tests/integration/test_instantanea_composiciones.py`
  (18). Rojo: `ModuleNotFoundError: No module named 'core.budget.instantanea'` en el commit `67e6777`;
  implementación `d28c352`. `escenarios.py` no cambia: `generar_escenario` recibe las composiciones del llamador,
  que ahora las obtiene con `composiciones_de_presupuesto`. Cobertura de `importacion.py` (UC‑05): las versiones
  importadas congelan su instantánea al guardar.
- **Estado:** espera visto bueno del tutor.

## SF‑E2: edición, versiones, `RegistroCambio` y restaurar (tarea 3.2)

- **Regla que lo motiva:** RF‑52 a RF‑54 y spec §9.3. Hoy solo UC‑02 deja registro de un cambio
  (`CambioPrecio`); el esquema no guarda de qué versión salió otra (limitación C3.2 de `descartar_version`);
  no hay forma de restaurar una versión; y «guardar dos veces» sin cambios crearía una versión vacía (FR‑4,
  segunda parte, que SF‑E1 dejó a este expediente).
- **Por qué es genérico:** versionar una edición y registrar quién cambió qué, con qué respaldo y cuándo es
  propio de **cualquier** presupuesto guardado (clínica, TI‑001, importado de UC‑05), con o sin hoja de
  metrajes (UC‑15). `core` no conoce `esp_*`: la función de guardado acepta un gancho `Callable[[Session,
  models.Presupuesto], None]` que la hoja usa para copiar sus filas en la **misma** `Session`.
- **Diseño:**
  1. Entidades aditivas: `RegistroCambio` (`registro_cambio`: proyecto, versión de origen, versión
     resultante, objeto, clave de fila, campo, valor anterior, valor nuevo, fuente del cambio, responsable,
     fecha y hora; valores como texto) y `VersionOrigen` (`version_origen`: versión, versión de la que salió,
     motivo). `guardar_presupuesto` gana `version_origen=None, motivo=""`; **toda** versión nueva la pasa:
     edición, restauración, cotización y `actualizar_precios` (UC‑02).
  2. `core/budget/edicion.py`: `guardar_edicion(...)` (versión nueva desde una elaboración editada con sus
     `CambioEditado`), `restaurar_version(...)`, `version_vigente(...)` (mayor `id` no descartada),
     `siguiente_codigo(...)`, `registros_de_version(...)` y `tabla_trazabilidad(...)`.
  3. **Guardar exige fuente y responsable** (`ValueError`, antes de tocar la base) y **no crea versión ni
     registros vacíos**: si, tras descartar los cambios cuyo valor anterior y nuevo coinciden, no queda
     ninguno, devuelve `None` (FR‑4). Un `RegistroCambio` por celda que cambió; todos en la misma transacción
     que la versión.
  4. **Restaurar la versión N** crea una versión nueva, copia exacta de N (renglones, ítems, pendientes,
     curva, plan, instantánea, hallazgos incluidos los externos), con `version_origen = N` y un
     `RegistroCambio` (objeto `version`, campo `restauracion`). No usa `descartar_version`; nada se borra.
  5. `asegurar_instantanea` (de 3.1) registra su creación con un `RegistroCambio` (objeto `apu`, campo
     `instantanea`, fuente y responsable del sistema).
  6. No confirma la transacción (como `guardar_presupuesto`): confirma quien llama, y si el gancho falla quien
     llama hace `rollback`: una sola `Session`, una sola transacción.
- **Prueba que lo demuestra** (`tests/integration/test_edicion_versiones.py`): sin fuente o sin responsable se
  rechaza y no deja filas; **guardar dos veces sin cambios no crea versión ni registros**; un cambio crea
  versión con `version_origen` y un registro por celda con todos sus campos; cambiar y volver al valor
  anterior es sin cambios; la versión anterior recarga idéntica; el gancho corre en la misma sesión (un fallo
  del gancho tras `rollback` no deja versión ni registros); restaurar crea una versión igual a N, N sigue
  existiendo, la restaurada es la vigente; `version_origen` en edición, restauración, cotización y UC‑02;
  `version_vigente` ignora las descartadas.
- **Impacto:** `guardar_presupuesto` y `actualizar_precios` ganan parámetros opcionales (compatibles hacia
  atrás); nada cambia en las versiones ya guardadas (sin `VersionOrigen`, su origen es «ninguno»).
  `descartar_version` conserva su regla; su limitación C3.2 queda cerrada porque ahora hay con qué
  distinguir una revaloración (`motivo = revaloracion`) de un presupuesto aparte.
- **Costo si es erróneo:** una tabla de registro con otro nombre de columna: se renombra con una migración
  aditiva (los valores son texto); si el tutor rechaza el expediente, la hoja no guarda ediciones y se declara.
- **Implementación y rojo observado (2026‑10‑05):** `core/budget/edicion.py` (nuevo) y las entidades
  `VersionOrigen` y `RegistroCambio`. `asegurar_instantanea` registra su creación (UC‑15e). Prueba:
  `tests/integration/test_edicion_versiones.py` (23 casos, con su fixture compartido
  `tests/fixtures/versiones.py`) y `test_trazabilidad_exportable.py` (3). Rojo: `ModuleNotFoundError: No module
  named 'core.budget.edicion'` en `8fb57c0`; implementación `a3ca877`; la tabla de trazabilidad, `56a1856` y
  `350bb91`.
- **Estado:** espera visto bueno del tutor.

## SF‑E3: punto de equilibrio (tarea 3.3)

- **Regla que lo motiva:** RF‑58, RS‑4 y spec §9.4. El punto de equilibrio solo existe en un script del caso
  (`scripts/analisis_ti001.py`); la hoja y el Excel lo necesitan sobre **cualquier** presupuesto.
- **Por qué es genérico:** CV = Σ cantidad × costo directo; CF = CV × administración; V = total; m = (V − CV) /
  V; PE = CF / m: solo usa el presupuesto y `ParametrosCosto.administracion`. Función pura con `Decimal`, sin
  base de datos, como el motor (NORMAS §2.4).
- **Diseño:** `core/budget/equilibrio.py`: `punto_equilibrio(presupuesto, parametros) -> PuntoEquilibrio`
  (dataclass inmutable con `estado` — `calculado`, `no_aplicable`, `no_existe`, `no_se_alcanza` —, `V`, `CV`,
  `CF`, `utilidad`, `margen`, `punto`, `porcentaje`, `periodo`, `fraccion_periodo` y `mensaje`). Los casos
  límite son resultados, no excepciones: V = 0 → no aplicable; m ≤ 0 → «no existe punto de equilibrio»; PE >
  V → «no se alcanza dentro del contrato» (con el PE calculado y sin ubicación); sin curva → PE sin ubicación.
  La ubicación es el primer período cuyo acumulado alcanza el PE y la fracción de ese período
  (`(PE − acumulado anterior) / monto`, cero si el monto es cero). `scripts/analisis_ti001.py` importa la
  función (DRY). El script **ya no contiene los literales** (28 586,76 USD, 56,60 %, Día 6): quedan en la
  bitácora del caso y en `tests/unit/test_caso_ti001.py`, que los comparan sin editarse.
- **Prueba que lo demuestra** (`tests/unit/test_equilibrio.py`): el oráculo es el **literal de la bitácora**
  de TI‑001 (`2026-09-30-caso-ti001.md`: 28 586,76 USD = 56,60 % del contrato, Día 6), no el script; un caso
  calculado a mano de dos partidas; cada caso límite con su estado y su mensaje; sin curva; tipos `Decimal`.
- **Impacto:** módulo nuevo; el script cambia solo su cuerpo (`test_punto_de_equilibrio` de TI‑001 sigue
  igual). El total y los PU de TI‑001 no cambian.
- **Costo si es erróneo:** cambiar una función pura y sus pruebas (RS‑4).
- **Implementación y rojo observado (2026‑10‑05):** `core/budget/equilibrio.py` (nuevo) y
  `scripts/analisis_ti001.py`, cuya `punto_equilibrio` adapta el resultado al diccionario de siempre y remite los
  literales a la bitácora y a `test_caso_ti001.py` (`test_punto_de_equilibrio` sin editar). Prueba:
  `tests/unit/test_equilibrio.py` (14, con el literal de la bitácora de TI‑001 y el caso de dos partidas a mano:
  PE = 585 = 50 % de 1 170, período 1 a 0,9). Rojo: `ModuleNotFoundError: No module named
  'core.budget.equilibrio'` en `2b85ffa`; implementación `2b68ab2`.
- **Estado:** espera visto bueno del tutor.

## SF‑E4: Excel de la hoja y M‑1/M‑2 (tarea 3.4)

- **Regla que lo motiva:** RF‑59, RNF‑12 y hallazgos M‑1 y M‑2 de TI‑001 (spec §8.3 y §9.5). `exportar_excel`
  escribe textos del usuario sin escapar (un texto que empieza por `=` se guarda como fórmula) y el TOTAL
  redondeado no cuadra con la suma de las filas redondeadas.
- **Por qué es genérico:** cualquier presupuesto se exporta; el escape y el tratamiento del redondeo no dependen
  de una especialidad. Las hojas que `core` no conoce (Espacio y metrajes, origen de precios) llegan como
  `TablaExportable`, un tipo genérico (título, columnas, filas) definido en `core.budget.excel`.
- **Diseño:** `exportar_hoja(presupuesto, informe, ruta, parametros, *, equilibrio, trazabilidad,
  hojas_extra)`: una hoja por pestaña (APU, Presupuesto, Plan y curva, Punto de equilibrio, Parámetros,
  Auditoría y Trazabilidad, más las extras en su lugar), cantidades y precios **sin redondear** con formato de
  presentación a dos decimales, y totales como **fórmulas** (`=E2*F2`, `SUM`, `ROUND`; nombres en inglés).
  M‑2 según RS‑8: el total exacto es el contractual y una nota al pie declara la diferencia de redondeo de
  presentación. **M‑1** en las dos exportaciones: toda celda de texto cuyo primer carácter sea `=`, `+`, `-`,
  `@`, tabulador o retorno de carro se escribe como texto (tipo cadena y `quotePrefix`), y un número negativo
  sigue siendo número. `exportar_excel` **conserva sus cuatro hojas y su estructura**
  (`test_exportar_excel_escribe_cuatro_hojas` intacto); si el escape de M‑1 moviera alguna de las dos huellas
  de RNF‑04, no se edita la prueba: se registra un ruling de reanclaje.
- **Prueba que lo demuestra** (`tests/unit/test_excel_hoja.py`, `tests/unit/test_excel_m1.py`): un evaluador
  de fórmulas (paquete `formulas`, grupo `dev`) calcula cada total del libro y se compara con el `Decimal` del
  sistema con tolerancia ±0,005 por celda; la línea base sigue sumando 1 586,61; cada prefijo de M‑1 en las dos
  exportaciones y el negativo legítimo; las dos huellas de RNF‑04 y las cuatro hojas sin tocar.
- **Impacto:** función nueva y un ayudante de escape en las dos exportaciones; ninguna hoja de
  `exportar_excel` cambia de forma. Dependencia nueva solo de pruebas.
- **Costo si es erróneo:** si se prefiere el total como suma de filas redondeadas, hay que enmendar RF‑08 y el
  principio 3 de NORMAS con expediente (RS‑8).
- **Implementación y rojo observado (2026‑10‑05):** `core/budget/excel.py` (`exportar_hoja`, `TablaExportable`,
  escape de M‑1 en `_agregar`, usado por las dos exportaciones) y `pyproject.toml`/`uv.lock` (`formulas` en
  `dev`). Prueba: `tests/unit/test_excel_hoja.py` y `test_excel_m1.py` (33 con las parametrizadas: 19 y 14). Las fórmulas
  evaluadas de la línea base, de TI‑001 (50 503,27) y de un caso sintético con destajo, equipo y parámetros
  propios coinciden con el `Decimal` del sistema a ±0,005 en cada celda con fórmula (PU y total de cada
  renglón, resumen de cada APU, acumulado y porcentaje de la curva, V, CV, CF y PE). Rojo: el commit `a2801ea`
  precede al código; `core/budget/excel.py` de ese commit no define `TablaExportable` ni `exportar_hoja` (no se
  ejecutó la corrida roja antes del commit: el `ImportError` se verificó con `git show`). Implementación `028d622`.
  **Rojo reproducido a posteriori (2026‑10‑05, revisión de pruebas):** en una copia desechable (`git worktree
  add --detach` de `HEAD`, retirada después) se neutralizó `_asegurar_texto` de `core/budget/excel.py` (el
  escape de M‑1, `if False and …`) y se corrió `tests/unit/test_excel_m1.py`: **13 de 13 fallan** (los seis
  prefijos en `exportar_excel`, los seis en `exportar_hoja` y el negativo legítimo, p. ej. `('f', '=1+1') !=
  ('s', '=1+1')`). Con el escape pasan, más los 12 directos añadidos después.
  **Relajación de las pruebas M‑1 tras el commit rojo (`a2801ea` → `028d622`), justificada:** (1) el filtro
  `"cmd" in c.value or endswith("col")` existe porque `exportar_hoja` escribe fórmulas vivas propias del
  sistema, que empiezan por `=` y son correctas; sin él las contaría como celdas de usuario sin escapar. No
  debilita nada: la comprobación de que ninguna `<f>` contiene la carga útil (`_formulas_con_carga`) se
  conserva. (2) Con tabulador y retorno de carro la hoja del plan no entra en lo esperado porque la etiqueta del
  periodo llega recortada de espacios iniciales: no hay prefijo que escapar ahí. Medido el 2026‑10‑05:
  Presupuesto, APU, Auditoría y la tabla genérica **sí** llevan el prefijo y quedan como texto con
  `quotePrefix`, así que `_hojas_esperadas` ahora exige todas menos la del plan (antes exigía solo APU y
  Auditoría). (3) Añadidas pruebas directas de `_agregar`, `_poner` y `TablaExportable` con cada uno de los seis
  prefijos, que no dependen de lo que se recorte.
  **Huellas:** `test_huellas_rnf04.py` (las dos) y las cuatro hojas pasan sin editarse: el escape solo toca
  celdas con prefijo peligroso y la fixture de las siete inconsistencias no tiene ninguna, así que **no hay
  ruling de reanclaje**.
- **Estado:** espera visto bueno del tutor.

## Correcciones de la revisión de SF3 (2026‑10‑05)

Cuatro encargos aprobaron el núcleo con correcciones; cada una con su prueba en rojo (`90c152c`) antes del código.

- **SF3‑R7, insumo heredado (SF‑E2/SF‑E6).** `restaurar_version` y `guardar_edicion` re‑resolvían el
  `insumo_id` de cada línea por tipo, descripción y precio, con lo que una restauración podía cambiar el insumo
  de una línea (o ligar una línea de precio manual a un insumo de la lista). Ahora `congelar(..., origen=)`
  copia el `insumo_id` de la instantánea de origen (`_insumos_heredados`). **Regla del precio editado a mano:**
  una línea en la misma posición, con el mismo tipo y descripción, hereda el insumo **si conserva su precio**;
  si el precio cambió es un precio manual y queda **sin `insumo_id`** (UC‑02 no la revalora con la lista); si
  la estructura de líneas de la partida cambió (otro número de líneas, otra descripción), se cae al
  re‑resolutor de siempre. Cotización y UC‑02 no heredan (su precio nuevo viene de otra lista y deben
  re‑resolver). *Genérico:* nada depende de un dominio. *Pruebas:* `test_edicion_versiones.py`
  (`…copia_el_insumo_id…`, `…hereda_el_insumo_de_todas_las_lineas`, `…precio_editado_a_mano_pierde_su_insumo…`).
  *Impacto:* solo versiones nuevas; las existentes no se tocan. *Costo si es errónea:* una línea de precio manual
  sin insumo no se revalora con UC‑02 (es lo deseado); si se prefiere ligarla, se cambia una condición.
- **SF3‑R8, títulos de hoja.** `_validar_titulos` comparaba con `_HOJAS_PROPIAS` sin pasar a minúsculas:
  «presupuesto» pasaba y openpyxl lo renombraba a «presupuesto1». Ahora se compara en minúsculas (siete casos
  nuevos en `test_excel_hoja.py`).
- **SF3‑R9, ciclo instantánea ↔ persistencia.** `_buscar` y `_parametros_de` pasan a `core/budget/_modelo.py`
  (que `persistencia` reimporta, así que nada cambia para quien los importaba de ahí) y `instantanea` ya no
  importa `persistencia` dentro de sus funciones. `_sesion_de` da un `ValueError` claro si la fila no tiene
  sesión (antes `AttributeError` sobre `None`).
- **Pruebas añadidas por la revisión (sin cambio de código):** M‑1 directo con los seis prefijos; PE de TI‑001
  evaluado por `formulas` contra 28 586,76 y 56,60 %; RF‑57 (FCAS 6,00 → 5,00 con PU a mano en los cinco APU);
  RF‑62 con un hallazgo R8 sembrado al restaurar, cotizar y retirar; delta del total editado a mano (1,5 × 15 ×
  1,15 × 1,10 × cantidad de concreto); restaurar inexistente, descartada y sin instantánea (con una lista nueva
  en el catálogo da la línea base; con la lista de la versión editada se rechaza sin dejar filas).

### Tabla RF → núcleo / hoja

| RF | Qué se prueba en el **núcleo** (esta rama) | Qué queda para la **hoja** (`inc/sf3`) |
|---|---|---|
| RF‑52 editar la hoja | `guardar_edicion`: versión nueva, origen, un registro por celda | borrador, derivación y cálculo en `ui/hoja.py` |
| RF‑53 instantánea (APU) | instantánea por versión y herencia del `insumo_id`; la de `esp_*` NO es del núcleo | instantánea de `esp_*` (tablas del adaptador, vía el gancho) |
| RF‑55 plan | el plan se guarda con la versión y se conserva al editar, restaurar y cotizar | edición del plan en la pantalla |
| RF‑56 precios | cotizar y retirar, origen de precios, tabla exportable | pestaña Precios (UI) |
| RF‑57 parámetros | el parámetro editado se guarda, se registra y la recarga calcula con él (PU a mano) | `guardar_edicion` **no recalcula**: la hoja elabora con los parámetros y pasa el resultado |
| RF‑62 hallazgos externos | R8 sobrevive a recargar, restaurar y cotizar | R8 a R10 los emite el adaptador del espacio |

**Riesgo residual de S4.** La meta S4 compara los hashes de `core/` contra el fin de SF2: vigila `core/` hasta
SF2, no los cambios de SF3. Estos se vigilan por **este archivo**: cada cambio de `core/` de SF3 (SF3‑E0, SF‑E2,
E3, E4, E6, E7 y las correcciones R7 a R9) tiene su expediente, y quien agregue un cambio de `core/` sin
expediente debe agregarlo aquí en el mismo commit. Nada lo exige mecánicamente; costo si ocurre: un cambio de
`core/` sin argumento de genericidad llega al tutor sin expediente.

---

## SF‑E7: origen de precios y cotizaciones por proyecto (tarea 3.5)

- **Regla que lo motiva:** RF‑56, DA‑SF‑9 y spec §9.6. `ListaPrecios` guarda nombre, moneda, vigencia y origen,
  sin tasa ni fecha de la tasa; `PrecioInsumo` no guarda referencia; y no hay forma de registrar una
  cotización de un proyecto sin cambiar la lista global (que cambiaría todos los proyectos).
- **Por qué es genérico:** de dónde sale un precio y cotizar un insumo para una obra son propios de cualquier
  presupuesto valorado, de cualquier dominio.
- **Diseño:** tablas aditivas `ListaPreciosOrigen` (tasa, fecha de la tasa, alcance global o de proyecto,
  proyecto y lista base), `ReferenciaPrecio` (la referencia, p. ej. el Ref de MaPreX, de un `PrecioInsumo`) y
  `Cotizacion` (insumo, precio, precio base, proveedor, número y fecha, ligadas a la lista del proyecto).
  - `Catalogo.lista_vigente` **excluye** las listas de alcance de proyecto.
  - `core/budget/cotizacion.py`: `cotizar_insumo(...)` crea la lista del proyecto (copia de la lista actual de
    la versión con ese insumo cambiado), la que la versión resultante referencia explícitamente, y guarda una
    versión nueva con la composición de la instantánea revalorada, con **el plan y la curva de la versión
    conservados**, `version_origen` y un `RegistroCambio` (objeto `precio`, campo `cotizacion`);
    `retirar_cotizacion(...)` hace lo mismo sin ella.
  - `actualizar_precios` (UC‑02) sobre una versión con lista de proyecto: crea una **lista nueva del
    proyecto** copiando la lista base nueva y reponiendo sobre ella las cotizaciones activas; la cotización
    **prevalece** hasta que se retire. El historial `CambioPrecio` compara siempre listas **base**.
  - `core/catalog/origen.py`: `origen_de_precios(...)` (lista, referencia, fecha, moneda, tasa con su fecha,
    cotización) para la pestaña Precios y su `TablaExportable`; ayudantes `registrar_origen_lista` y
    `fijar_referencia`.
- **Prueba que lo demuestra** (`tests/integration/test_cotizacion_proyecto.py`): la cotización cambia **solo**
  ese insumo en **ese** proyecto (otro proyecto sobre la misma lista queda igual); la versión resultante
  conserva plan y curva (R2 cierra); `lista_vigente` no devuelve la lista del proyecto; una carga global
  posterior por UC‑02 **no pisa** la cotización, y retirarla la quita con su registro; origen visible por
  insumo; una base anterior abre.
- **Impacto:** compatible hacia atrás; `lista_vigente` filtra con una subconsulta (las bases existentes no
  tienen filas en `lista_precios_origen`, así que todas sus listas son globales).
- **Costo si es erróneo:** una lista global por vigencia cambiaría todos los proyectos (DA‑SF‑9); si el tutor
  rechaza el expediente, la cotización se difiere y la pestaña Precios solo muestra el origen.
- **Implementación y rojo observado (2026‑10‑05):** `core/catalog/origen.py` (nuevo: tasa, referencia, listas de
  proyecto, `origen_de_precios`), `core/budget/cotizacion.py` (nuevo: `cotizar_insumo`, `retirar_cotizacion`),
  `core/catalog/repositorio.py` (`lista_vigente` excluye las listas de proyecto) y `actualizar_precios` (repone las
  cotizaciones activas sobre la lista base nueva). Prueba: `tests/integration/test_cotizacion_proyecto.py` (19).
  Rojo: `ModuleNotFoundError: No module named 'core.budget.cotizacion'` en `8fc8799`; implementación `5ee15f0`.
- **Estado:** espera visto bueno del tutor.

---

## SF‑E8: revalorar guarda el reparto por partida que recibe (hallazgo de la hoja de SF3)

- **Regla que lo motiva:** RF‑54/RF‑56 y SF‑E6: toda versión conserva su plan por partida. `actualizar_precios`
  elaboraba con `plan=` pero llamaba a `guardar_presupuesto` sin él, que lo infería de la curva; con una partida
  repartida en varios períodos el plan no es inferible y la versión revalorada quedaba **sin `PlanVersion`**.
- **Por qué es genérico:** revalorar (UC‑02) y guardar un plan son propios de cualquier presupuesto valorado; no
  interviene ninguna especialidad.
- **Cambio:** `actualizar_precios` pasa a `guardar_presupuesto` el mismo reparto con el que elaboró: el plan ya
  escrito, o el que calcula el `GeneradorPlan` (se captura al ejecutarlo, sin calcularlo dos veces). Sin `plan=`
  nada cambia: **ruling SF3‑R4 se mantiene** (UC‑02 no conserva el plan por defecto; la pantalla pasa
  `plan_de_version(...)`).
- **Prueba que lo demuestra** (`tests/integration/test_sf3_defectos_nucleo.py`): origen con reparto 40/60 por
  partida (literal escrito a mano); revalorar con `plan=plan_de_version(origen)` → la nueva versión recarga con
  el mismo reparto exacto y la misma curva (dos períodos, primer monto = 40 % del total ±0,01, acumulado final =
  total); plan como función se guarda igual al del origen; sin `plan=` la versión queda sin plan (R4).
- **Impacto:** compatible hacia atrás (solo añade filas de `PlanVersion` cuando antes se perdían); las líneas base
  no se mueven.
- **Costo si es erróneo:** una versión revalorada con un plan que el llamador pasó mal; se corrige pasando el
  correcto. Si se revierte, vuelve a perderse el reparto.
- **Implementación y rojo observado (2026‑10‑05):** rojo `plan_de_version(...)` devolvía `None` para la versión
  `002` y siete casos de `siguiente_codigo` fallaban (SF‑E9); implementación en el commit siguiente.
- **Estado:** espera visto bueno del tutor.

## SF‑E9: `siguiente_codigo` reconoce prefijo y número (hallazgo de la hoja de SF3)

- **Regla que lo motiva:** la convención de códigos de versión (`001`, `TI-001`). `siguiente_codigo` solo veía
  códigos solo‑dígitos: en un proyecto con `TI-001` devolvía `001`, que choca con la convención (y con una
  versión existente si ya hubiera `001`).
- **Por qué es genérico:** cualquier proyecto puede nombrar sus versiones con prefijo (caso TI‑001, importados).
- **Cambio:** cada código se lee como prefijo libre + número final (`^(.*?)(\d+)$`). El prefijo es el de la última
  versión guardada; el número, el mayor de ese prefijo más uno, con el ancho del mayor (mínimo 3); se salta
  cualquier código existente. Sin código reconocible: `001`.
- **Prueba que lo demuestra:** `TI-001`→`TI-002`; `001`→`002`; `001,002`→`003`; huecos (`TI-001,TI-003`→`TI-004`);
  mezcla (`001,TI-001`→`TI-002`, `TI-001,002`→`003`); sin número (`PRE`)→`001`; ancho (`TI-0999`→`TI-1000`);
  proyecto sin versiones→`001`; nunca un código existente.
- **Impacto:** los proyectos con códigos solo numéricos dan lo mismo que antes.
- **Costo si es erróneo:** un código con otro prefijo del esperado; el usuario lo puede cambiar. Ruling: con
  mezcla de prefijos manda la última versión guardada.
- **Estado:** espera visto bueno del tutor.
