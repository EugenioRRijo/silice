# Expedientes de la fase C6 del cierre (núcleo)

**Fecha:** 2026‑09‑29 · **Rama:** `inc/cierre-C6-N` (pista N de C6, desde `c47b57e`) · **Plan:**
`C6-plan.md` del directorio de control de C6 (§2 y §6) · **Inventario:**
[docs/auditoria/2026-09-inventario.md](../auditoria/2026-09-inventario.md) · **Spec:**
[§5, fila C6, y §10, enmienda del 2026‑09‑29](../superpowers/specs/2026-09-23-plan-cierre-tesis-design.md)
· **Bitácora de la fase:** [2026-09-23-cierre.md, «Fase C6»](2026-09-23-cierre.md).

La enmienda de C6 autoriza exactamente cinco commits que tocan `core/`, uno por hallazgo (INV‑093,
INV‑090, INV‑086, INV‑076 e INV‑099), cada uno con su expediente previo en este archivo, commiteado
antes de su código, sin mezclar capas (los llamadores de `api/` y `ui/` van en commits de otras
pistas), sin cambiar ningún contrato de `core/contracts/` y con la línea base (1 586,61 USD y 7 de 7)
intacta. Si un expediente concluyera que hace falta un contrato, la fase se detiene (CLAUDE.md §5).
El método es el de los expedientes C3 y C5
([2026-09-24-C3-expedientes.md](2026-09-24-C3-expedientes.md),
[2026-09-28-C5-expedientes.md](2026-09-28-C5-expedientes.md)). Las citas archivo:línea son de
`c47b57e`.

## C6.1 INV-093: justificar la advertencia de rendimiento en una tabla aditiva

**Problema.** UC‑06, flujo 4a (`docs/ERS.md:303`): «El proyectista acepta la advertencia: se
registra su justificación junto al APU». El sistema advierte (RF‑27,
`core/catalog/rendimientos.py:149-164`, `advertencia_rendimiento`), pero ni el registro de
rendimientos (`api/esquemas.py:328-335`, `RendimientoPeticion` sin campo de justificación) ni la
composición (`ui/paginas/componer.py:278-308`) tienen dónde guardarla: la tabla `rendimiento`
(`core/models/entidades.py:138-160`) no tiene columna para ella. La matriz por paso lo marca
«no implementado» (`docs/plan_pruebas.md`, UC‑06 4a; inventario, INV‑093).

**Diseño.** Un solo commit de `core/`, asunto
`feat(models): tabla aditiva para justificar la advertencia de rendimiento`, con sus pruebas en
`tests/integration/test_justificacion_rendimiento.py`:

- `core/models/entidades.py`, tras `Rendimiento` (:138-160): la entidad
  `JustificacionRendimiento`, `__tablename__ = "justificacion_rendimiento"`, con
  `rendimiento_id` clave primaria y foránea a `rendimiento.id` con `ondelete="CASCADE"` (un
  rendimiento tiene a lo sumo una justificación, y borrar el rendimiento, o la partida que lo
  arrastra con su `delete-orphan` de :76-80, no queda bloqueado por ella con
  `PRAGMA foreign_keys=ON`), `texto` (`Text`), `advertencia` (`Text`, el texto de RF‑27 que se
  aceptó, para que la justificación se lea sin reconstruir la dispersión de ese momento) y `fecha`
  (`Date`). La relación se declara solo del lado nuevo, sin `back_populates`: `Rendimiento` no gana
  atributos y ninguna consulta existente cambia. Mismo patrón que `DescarteVersion` (:303-319,
  expediente C3.2). Se exporta en `core/models/__init__.py`; el docstring del módulo pasa a
  «diecisiete entidades».
- `core/catalog/sesion.py:30-32`: `crear_esquema` ya es `Base.metadata.create_all(motor)`, que
  crea solo las tablas que faltan (`checkfirst`). Solo su docstring pasa a «diecisiete tablas». Sin
  `ALTER TABLE` y sin tocar las demás tablas.
- `core/catalog/rendimientos.py`: `justificar_rendimiento(session, codigo_partida, texto,
  advertencia, fecha) -> models.JustificacionRendimiento`. Liga la justificación al **último**
  rendimiento registrado de la partida (el de mayor `id`: el que acaba de registrar
  `registrar_rendimiento` o `reemplazar_composicion` en la misma transacción). Rechaza con
  `ValueError` el texto o la advertencia vacíos (una justificación sin advertencia no justifica
  nada) y un rendimiento ya justificado; con `KeyError` (un `LookupError`, como
  `Catalogo.rendimientos`) la partida inexistente, y con `LookupError` la partida sin rendimientos.
  Hace `flush`, no `commit`: la confirmación es de la capa que representa la decisión del usuario,
  como el resto del módulo (docstring de :16-17). Se exporta en `core/catalog/__init__.py`.

**Alternativa descartada.** Una columna `justificacion` en `rendimiento`. Toda consulta del modelo
`Rendimiento` (`Catalogo.rendimientos`, `_rendimiento_estimado`, la dispersión) seleccionaría la
columna nueva, y en una base creada antes de C6 fallaría con `no such column` hasta una migración
con `ALTER TABLE`, que la spec §2 deja fuera del límite. La tabla aditiva solo la consulta el
código nuevo; una base vieja la gana con `crear_esquema` y conserva sus filas. Tampoco se guarda en
`condiciones` (`core/models/entidades.py:155`): mezclaría la condición de obra con el juicio del proyectista, y
`_registrar_rendimiento_si_cambia` (`core/catalog/repositorio.py:321-352`) compara condiciones
para decidir si registra un rendimiento nuevo.

**Por qué ningún contrato cambia.** `core.contracts.apu.Rendimiento` no gana campo: la
justificación es un dato de persistencia sobre un rendimiento ya registrado, no una entrada del
motor ni algo que cruce a `adapters/` o `ml/`. La función devuelve un modelo, como
`registrar_ejecucion` (:71-96), para que la capa que llama siga en la sesión.

**Línea base.** Intacta: el motor no lee la tabla nueva, `tests/fixtures/apu_linea_base.py` no se
edita y la siembra no cambia; el conjunto de la línea base sigue en `27 0 0 0`.

**Pruebas previstas** (`tests/integration/test_justificacion_rendimiento.py`, base en memoria o en
`tmp_path`):

1. Registrar un rendimiento que se aparta del observado y justificarlo: la fila queda ligada a ese
   rendimiento (el último), con el texto, la advertencia y la fecha; los rendimientos anteriores
   quedan sin justificación.
2. Texto vacío o en blanco, advertencia vacía y una segunda justificación del mismo rendimiento:
   `ValueError`, sin fila nueva.
3. Partida sin rendimientos: `LookupError`; partida inexistente: `KeyError`.
4. Una base creada con las dieciséis tablas anteriores, sembrada y confirmada, gana
   `justificacion_rendimiento` con `crear_esquema`, conserva sus filas y admite justificar.
5. `CASCADE`: borrar el rendimiento justificado borra su justificación con `PRAGMA foreign_keys=ON`.

La mordida prevista: ligar al primer rendimiento en vez del último, o quitar el rechazo de la
segunda justificación.

**Para las pistas A y U.** `justificar_rendimiento` se llama después de registrar (API:
`registrar_rendimiento`; «Componer»: `reemplazar_composicion` o `cargar_composicion`) y antes del
`commit`, solo si hubo advertencia y el usuario escribió una justificación. Si la edición de
«Componer» no registra rendimiento nuevo (`_registrar_rendimiento_si_cambia` no cambió nada), el
último rendimiento puede estar ya justificado y la función lanza `ValueError`: la interfaz debe
tratarlo como aviso, no como fallo del guardado.
