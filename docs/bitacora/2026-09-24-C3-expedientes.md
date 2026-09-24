# Expedientes de la fase C3 del cierre (núcleo)

**Fecha:** 2026‑09‑24 · **Rama:** `inc/cierre-C3-nucleo` (pista B de C3) · **Plan:**
[docs/superpowers/plans/2026-09-24-cierre-c3-interfaz-scripts.md](../superpowers/plans/2026-09-24-cierre-c3-interfaz-scripts.md)
· **Inventario:** [docs/auditoria/2026-09-inventario.md](../auditoria/2026-09-inventario.md) ·
**Spec:** [§5 y §10](../superpowers/specs/2026-09-23-plan-cierre-tesis-design.md).

La spec (§5, fila C3, enmendada en la Tarea 1 de C3) autoriza exactamente dos commits que tocan
`core/` en esta fase, cada uno con expediente previo en este archivo, commiteado antes de su código,
y con la línea base (1 586,61 USD y 7 de 7) intacta. Este archivo es de la pista B (plan de C3,
Global Constraints).

## C3.1 INV‑080: la recarga del informe conserva los ítems pendientes

**Problema y origen.** Están en el expediente C2.1 de la bitácora del cierre
([docs/bitacora/2026-09-23-cierre.md](2026-09-23-cierre.md), sección «Expediente C2.1»), que aquí
no se repite: el ítem pendiente no se persiste y la reauditoría de la recarga no lo conoce, así que
el informe recargado puede declarar CUMPLE un presupuesto emitido NO CUMPLE (RF‑02). Eugenio decidió
la opción (a) en GC2 y su alcance amplio en C3 (D4 = A, 2026‑09‑24).

**Diseño de la opción (a).** Un solo commit de `core/budget/`, asunto
`fix(budget): la recarga del informe conserva los items pendientes`, con sus pruebas en `tests/`:

- `guardar_presupuesto(..., pendientes: Sequence[ItemComputo] = ())` persiste cada pendiente como
  `models.ItemComputo` del presupuesto **sin renglón** (ninguna `partida_presupuestada` lo cita). El
  esquema no cambia: `item_computo.presupuesto_id` ya existe (`core/models/entidades.py:317`).
- `guardar_presupuesto` exige la correspondencia **en los dos sentidos**, con `ValueError`, por la
  clave `(codigo_partida, origen_id)` que define un solo ayudante (`_clave_pendiente`, en
  `core/budget/presupuesto.py`, el mismo que redacta los `origen_ids` del hallazgo):
  - un pendiente sin su hallazgo `CODIGO_PENDIENTE` en el informe: persistirlo haría que la recarga
    dijera **más** que el documento emitido;
  - un hallazgo `CODIGO_PENDIENTE` del informe sin su pendiente en `pendientes`: la recarga diría
    **menos**, y un documento emitido NO CUMPLE podría recargarse CUMPLE, que es el síntoma de
    C2.1. Con esta segunda guarda, olvidar `pendientes=` en un llamador nuevo falla al guardar en
    vez de perder el pendiente en silencio (ronda de corrección 1 de B1, dictámenes A1 y R‑1).
- `cargar_elaboracion(session, proyecto_nombre, codigo, catalogo) -> ResultadoElaboracion`, pública
  en `core.budget`:
  - `presupuesto` es la misma reconstrucción de `cargar_presupuesto`, que no cambia de firma ni de
    retorno (el contrato `Presupuesto` es estable, CLAUDE.md §5), sobre una sola búsqueda de la
    fila;
  - `pendientes`: los `item_computo` del presupuesto sin `partida_presupuestada`, ordenados por `id`
    (el orden en que se guardaron, que es el de `ResultadoElaboracion.pendientes`). Los lee un
    ayudante privado único, `_cargar_pendientes`, que comparte `actualizar_precios`;
  - `informe = _declarar_pendientes(auditar(presupuesto), pendientes)`. `_declarar_pendientes` se
    importa desde `core.budget.presupuesto` con un comentario que lo justifica, como hace el
    precedente `core/budget/actualizacion.py:32-40` con `_buscar` y `_parametros_de`: es la única
    definición del hallazgo `PENDIENTE` y duplicarla sería repetirla.
- `actualizar_precios` arrastra los pendientes del base (D4 = A): carga el base con
  `cargar_presupuesto` y sus pendientes con `_cargar_pendientes` (sin reauditarlo), aplica
  `exigir_composiciones` solo sobre los ítems **valorados**, vuelve a elaborar los valorados más los
  pendientes (así `elaborar` los declara en el informe nuevo) y guarda la versión nueva con
  `pendientes`. El comparativo (`_comparar`, `zip(strict=True)`) sigue recorriendo solo las partidas
  valoradas de las dos versiones, que son las mismas y en el mismo orden.
- **Al revalorar, un pendiente sigue pendiente aunque la lista nueva ya tenga su partida** (D4 = A):
  las composiciones se piden solo para las partidas valoradas del base, así que revalorar no valora
  pendientes. Valorarlos es volver a elaborar (UC‑01), no revalorar (UC‑02).

**Límite declarado: datos anteriores.** Los presupuestos guardados antes de este cambio no tienen
pendientes persistidos: su recarga no los inventa y su informe recargado sigue siendo el de
`auditar`. Pero sus hallazgos `PENDIENTE` sí quedaron guardados con el documento emitido, así que
en esas bases `GET /presupuestos/{codigo}/informe` puede todavía decir CUMPLE sobre un documento
emitido NO CUMPLE: es una **no conformidad residual con RF‑02**, limitada a bases locales creadas
antes del commit (la CI y las pruebas siembran bases nuevas). Queda en el docstring de
`cargar_elaboracion` y en el dictamen C3‑3.

**Límite del oráculo de las pruebas.** Las entradas de las pruebas (la línea base auditada más
`XX-99-NUE`) ya son NO CUMPLE sin el pendiente, por los siete hallazgos de la línea base: las
pruebas fijan que el hallazgo `PENDIENTE` se recarga (conjunto de hallazgos igual al emitido y al
persistido), pero no reproducen el síntoma exacto de C2.1, un documento que **solo** por el
pendiente pasa de CUMPLE a NO CUMPLE.

**Alcance de D4 = A.** Recarga y revaloración, **no** escenarios. Los escenarios son INV‑083
(Hecho 11 del plan): su parte de `ui/` va en la Tarea 11, paso 8 (pista A), con
`cargar_elaboracion` y sin tocar `core/`; el informe del propio escenario (`generar_escenario`) y la
ruta de la API quedan en el dictamen C3‑12, con fase C4.

**Llamadores, en commits aparte.** `api/rutas/presupuestos.py`: `crear_presupuesto` pasa
`pendientes=resultado.pendientes` y `_cargar` usa `cargar_elaboracion` (lo usan `/informe` y
`/excel`), en el commit `fix(api): el informe recargado declara los pendientes`. En `ui/` ningún
módulo llama a `guardar_presupuesto` ni a `cargar_elaboracion` (Hecho 11); `ui/paginas/escenarios.py`
es INV‑083.

**Línea base.** Intacta: `tests/fixtures/apu_linea_base.py` no se edita y el conjunto de la línea
base sigue en `27 0 0 0`. Un presupuesto sin pendientes se guarda y se recarga exactamente como
antes: el parámetro nuevo vale `()` por defecto y la recarga sin pendientes devuelve
`auditar(cargar_presupuesto(...))`. Ningún llamador actual guarda un informe con `PENDIENTE` sin
`pendientes`: los sembradores y scripts (`scripts/seed_demo.py`, `scripts/generar_resultados_ml.py`,
`scripts/medir_rnf03.py`) elaboran solo partidas del catálogo, y la API pasa `pendientes`; el
recuento completo lo confirma.

**Ratificar en GC3:** la guarda en dos sentidos (`ValueError`), el pendiente que sigue pendiente al
revalorar y el límite de los datos anteriores al cambio.

## Nota de la Tarea 10b (INV‑081, api): rojo declarado de la reescritura de `test_api.py`

No es una excepción de `core/`: se anota aquí porque el plan (Tarea 10b, QA‑17) pide dejar en el
expediente la lista real del rojo. Con los dobles ya parchados en `ml.normalization.normalizador` y
la API todavía con `_proponedor`, corrido sin red (`HF_HUB_OFFLINE=1`,
`-k "propuestas or pendiente"`):

- **Fallan** (ocho casos): `test_un_item_sin_partida_queda_pendiente_por_http`;
  `test_sin_el_modelo_el_pendiente_queda_sin_propuestas[sin-modelo]`, `[identificador-invalido]` y
  `[pesos-corruptos]`; `test_si_similares_falla_el_pendiente_queda_sin_propuestas[import]`, `[os]`,
  `[valor]` y `[ejecucion]`.
- **Pasan ya en rojo**, como prevé el plan (no cuentan como rojo; su cambio lo cubre la mordida):
  `test_sin_el_extra_ml_el_pendiente_queda_sin_propuestas` y
  `test_si_todos_los_items_quedan_pendientes_el_presupuesto_sale_vacio_y_no_cumple`.
- Además, las dos pruebas de INV‑080 del paso 2 de la Tarea 11
  (`test_el_informe_recargado_declara_el_pendiente` y
  `test_el_excel_recargado_declara_el_pendiente_en_la_auditoria`), que también sustituían
  `sys.modules["ml.normalization"]` por `None`, pasan a parchar `_cargar_modelo` con `_sin_extra`,
  para no cargar el modelo real; pasan antes y después del cambio de la API.

Mordida del commit de la API (`_pendientes` con `propuestas=[]` sin llamar a `propuestas_para`):
fallan el cableado, los siete casos de `caplog` y `test_la_propuesta_real_reconoce_la_partida_de_la_misma_descripcion`.

## C3.2 INV‑015 7a: descartar la versión revalorada conserva el historial

**Problema y origen.** Están en el expediente B.8 de C1
([docs/bitacora/2026-09-23-C1-expedientes.md](2026-09-23-C1-expedientes.md), «B.8 INV-015»), que
aquí no se repite: «descartar» hoy es no confirmar la transacción, que también deshace los
`CambioPrecio`, contra UC‑02 7a («se marca como descartada, pero el registro de cambios se
conserva», `docs/ERS.md:170`). Eugenio decidió la segunda excepción de `core/` en C3 (D1 = A,
2026‑09‑24).

**Diseño.** Un solo commit de `core/`, asunto
`feat(budget): descartar la version revalorada conserva el historial`, que toca **solo** los cinco
archivos autorizados (`core/models/entidades.py`, `core/models/__init__.py`,
`core/catalog/sesion.py`, `core/budget/actualizacion.py`, `core/budget/__init__.py`) más sus pruebas
en `tests/integration/test_actualizacion_precios.py` y `tests/integration/test_persistencia.py`:

- **Tabla `descarte_version`** (`models.DescarteVersion`): `presupuesto_id` es clave primaria **y**
  foránea a `presupuesto.id` con `ondelete="CASCADE"`, así que es única por presupuesto y no bloquea
  el borrado de un presupuesto con `PRAGMA foreign_keys=ON` (`core/catalog/sesion.py:51`, A‑11); y
  `fecha`. Es **aditiva**: `crear_esquema` (`create_all`) la agrega a una base existente sin tocar
  las otras quince tablas, así que no es una migración de esquema (spec §2). Dictamen C3‑1.
  El docstring de `core/models/entidades.py:1` y el de `crear_esquema` (`core/catalog/sesion.py:31`)
  pasan de «quince» a «dieciséis».
- **`descartar_version(session, proyecto_nombre, codigo_presupuesto, fecha)`** en
  `core/budget/actualizacion.py`, exportada en `core.budget`:
  - «Última versión» es el presupuesto de mayor `id` del proyecto, siempre que haya al menos otro
    anterior. El presupuesto base nunca se descarta (`ValueError`), ni una versión que no sea la
    última, ni una ya descartada (`ValueError`).
  - La versión descartada **sigue guardada y cargándose como documento**: la marca no borra nada.
    Los `CambioPrecio` y las `IncidenciaCambio` que la produjeron se conservan (`docs/ERS.md:170`).
  - No confirma la transacción: la confirma el llamador (la página de actualización, en el commit de
    `ui/` de la pista A), como con `actualizar_precios`.
- **Fuera de este commit:** el botón «Descartar version» (`ui/paginas/actualizacion.py`, pista A) y
  los documentos derivados (`docs/modelo_datos.md`, `docs/arquitectura.md`), en commits aparte.

**Línea base.** Intacta: `tests/fixtures/apu_linea_base.py` no se edita y el conjunto de la línea
base sigue en `27 0 0 0`. Ninguna prueba de persistencia previa cambia: el diff de
`test_persistencia.py` y `test_actualizacion_precios.py` solo agrega líneas.

**Ratificar en GC3:** la tabla aditiva (dictamen C3‑1) y la regla de «última versión».
