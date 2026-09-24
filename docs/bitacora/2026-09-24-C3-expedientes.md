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
- `guardar_presupuesto` lanza `ValueError` si un pendiente no tiene su hallazgo `PENDIENTE` en el
  informe (regla `CODIGO_PENDIENTE` con el código de la partida y el `origen_id` del ítem en
  `origen_ids`): persistir un pendiente que el documento emitido no declara sería guardar una
  recarga que dice más que el documento.
- `cargar_elaboracion(session, proyecto_nombre, codigo, catalogo) -> ResultadoElaboracion`, pública
  en `core.budget`:
  - `presupuesto` sale de `cargar_presupuesto`, que no cambia de firma ni de retorno (el contrato
    `Presupuesto` es estable, CLAUDE.md §5);
  - `pendientes`: los `item_computo` del presupuesto sin `partida_presupuestada`, ordenados por `id`
    (el orden en que se guardaron, que es el de `ResultadoElaboracion.pendientes`);
  - `informe = _declarar_pendientes(auditar(presupuesto), pendientes)`. `_declarar_pendientes` se
    importa desde `core.budget.presupuesto` con un comentario que lo justifica, como hace el
    precedente `core/budget/actualizacion.py:32-40` con `_buscar` y `_parametros_de`: es la única
    definición del hallazgo `PENDIENTE` y duplicarla sería repetirla.
- `actualizar_precios` arrastra los pendientes del base (D4 = A): carga el base con
  `cargar_elaboracion`, aplica `exigir_composiciones` solo sobre los ítems **valorados**, vuelve a
  elaborar los valorados más los pendientes (así `elaborar` los declara en el informe nuevo) y guarda
  la versión nueva con `pendientes`. El comparativo (`_comparar`, `zip(strict=True)`) sigue
  recorriendo solo las partidas valoradas de las dos versiones, que son las mismas y en el mismo
  orden.

**Límite declarado.** Los presupuestos guardados antes de este cambio no tienen pendientes
persistidos: su recarga no los inventa y su informe recargado sigue siendo el de `auditar`. Queda en
el docstring de `cargar_elaboracion` y en el dictamen C3‑3.

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
`auditar(cargar_presupuesto(...))`.

**Ratificar en GC3:** el `ValueError` ante un pendiente no declarado y el límite de los datos
anteriores al cambio.

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
