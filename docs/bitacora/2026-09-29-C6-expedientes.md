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

## C6.2 INV-090: dar de alta los insumos desconocidos de la lista de precios

**Problema.** UC‑02, flujo 2a (`docs/ERS.md:198-199`): «Insumos desconocidos en el archivo: el
sistema los lista y **ofrece darlos de alta o ignorarlos**; los ignorados no intervienen en el
recálculo». Hoy solo se listan: `crear_lista_desde_archivo` (`core/catalog/precios.py:276-324`) los
devuelve en `ResumenLista.desconocidos` (:94-105) y la página los anuncia como «no se crearon ni
intervienen en el recalculo» (`ui/paginas/actualizacion.py:299-303`); ni la página ni
`POST /listas-precios` (`api/rutas/listas.py:30-51`) ofrecen el alta (inventario, INV‑090;
`docs/plan_pruebas.md`, UC‑02 2a, parcial).

**Diseño.** Un solo commit de `core/`, asunto
`feat(catalog): dar de alta los insumos desconocidos de la lista de precios`, con sus pruebas en
`tests/integration/test_alta_desconocidos.py`:

- `core/catalog/precios.py`:
  - `insumos_desconocidos(session, ruta) -> tuple[PrecioLeido, ...]`: la vista previa de lo que se
    puede dar de alta, en el orden del archivo, **sin escribir nada**. Son las filas cuyo
    `(tipo, descripción)` normalizado no está en el catálogo con **ninguna** unidad. Una fila cuya
    descripción sí está en el catálogo pero con una unidad no equivalente es el flujo 2b («la fila
    se rechaza y se reporta», `docs/ERS.md:200-201`): sigue en `ResumenLista.desconocidos`, como hoy
    (`test_una_fila_con_unidad_no_equivalente_se_rechaza_y_las_demas_se_procesan`), pero no se
    ofrece para el alta, porque darla de alta crearía un homónimo con otra unidad del insumo que el
    flujo 2b rechaza.
  - `crear_lista_desde_archivo(..., dar_de_alta: Collection[PrecioLeido] = ())`: los elegidos se
    validan **antes** de crear la lista (`ValueError` si alguno no está en la vista previa de ese
    archivo, sin escribir nada); luego se crean, en el orden del archivo y uno por clave, con código
    nuevo del tipo (`MAT-NNN`, `EQU-NNN`, `MO-NNN`), y su precio entra **solo en la lista nueva**:
    la anterior es inmutable (docs/modelo_datos.md §2.2) y la nueva ya nace de copiarla (:286-288).
    Sin `dar_de_alta` el comportamiento es idéntico al de hoy.
  - `ResumenLista` (:94-105) gana, **al final** y con valor por defecto, `dados_de_alta:
    tuple[models.Insumo, ...] = ()`. `desconocidos` pasa a ser lo que **no** se dio de alta: los
    ignorados del flujo 2a y los rechazados del 2b («ignorados siguen en `desconocidos`»). Sin alta,
    `desconocidos` no cambia.
- `core/catalog/repositorio.py`: `Catalogo.dar_de_alta_insumo(tipo, descripcion, unidad) ->
  models.Insumo`, público, que reutiliza `_codigo_nuevo` (:404-413) y hace `flush`. `ValueError` con
  descripción vacía o si ya existe un insumo con el mismo `(tipo, descripción, unidad)`: el alta no
  es la vía para crear variantes (esas nacen en `_resolver_insumo`, :354-388). Construye el
  `models.Insumo` directamente, sin `a_modelo_insumo`: esa función traduce una `LineaCatalogo`, que
  exige precio, cantidad y depreciación que un insumo recién dado de alta no tiene, e inventarlos
  sería peor que declarar la excepción; el docstring del módulo (:8-11) la nombra junto a
  `models.PrecioInsumo`.
- `core/catalog/__init__.py`: exporta `insumos_desconocidos`.

**Alternativa descartada.** Dar de alta todos los desconocidos al cargar la lista. El flujo 2a pide
que el sistema **ofrezca** el alta o el ignorar: crear en silencio lo que un proveedor escribió mal
(«Cemento Portlan») llenaría el catálogo de insumos huérfanos. También se descartó identificar los
elegidos por descripción dentro del núcleo: dos filas del archivo pueden compartir descripción con
distinto tipo, y `PrecioLeido` (inmutable, con tipo, descripción, unidad y precio) ya es la clave
exacta que devuelve la vista previa; la API traduce las descripciones que recibe a esos
`PrecioLeido`.

**Por qué ningún contrato cambia.** `PrecioLeido`, `ResumenLista` y `Catalogo` son del catálogo,
no de `core/contracts/`; el campo nuevo de `ResumenLista` va al final con valor por defecto, así que
toda construcción existente sigue valiendo.

**Línea base.** Intacta: el alta solo ocurre si el llamador elige, un insumo recién creado no está
en ninguna composición y no tiene precio en la lista anterior, así que no entra en
`insumos_afectados` (:344-363, exige los dos precios) ni en ningún APU. `actualizar_precios` da
los mismos totales con y sin alta (prueba 4).

**Ronda 1 de revisión (arq N-1, qa N-QA-5, hechos 7, req 6), por `fixup` de este commit.**

- *Equipos y mano de obra sin unidad.* `Catalogo.dar_de_alta_insumo` guarda la unidad solo en los
  materiales; los equipos y la mano de obra se dan de alta con `unidad=None`, la convención de
  `lineas_de` (`core/catalog/mapeo.py:142-181`), para que `_resolver_insumo` los reutilice cuando un
  APU los componga. Sin eso, una fila de MaPreX `equipo,…,dia,…` daba un insumo que ningún APU
  alcanzaba y el primer APU creaba un homónimo. Límite que queda: la lista siguiente que traiga la
  misma fila con «dia» la rechaza como flujo 2b (unidad no equivalente), como ya les pasa hoy a
  todos los equipos del catálogo frente a MaPreX (riesgo «MaPreX casa pocos insumos», C6-plan §6).
- *Identidad normalizada.* La guardia de insumo existente compara con la identidad del catálogo
  (tipo, descripción con `normalizar_texto` y unidad con `normalizar_unidad`, sin unidad fuera de
  los materiales), no con el texto exacto: una llamada directa con otra grafía ya no crea un
  homónimo.
- *Filas repetidas.* Dos filas elegidas con la misma identidad dan **una** alta y las dos le fijan
  el precio en la lista nueva; si sus precios difieren, `ValueError` que nombra el archivo y las
  filas, antes de escribir nada. Dos filas con la misma descripción y distinta unidad de material
  siguen siendo dos identidades y dan dos altas (el catálogo ya admite homónimos de distinta
  unidad): caso de borde que la interfaz puede evitar.

**Pruebas previstas** (`tests/integration/test_alta_desconocidos.py`, base en memoria):

1. La vista previa lista el desconocido del flujo 2a, no el rechazado del 2b ni los casados, y no
   crea insumos ni listas.
2. Con el desconocido elegido, se crea `MAT-NNN` (siguiente número del tipo, calculado a mano desde
   la siembra) con su descripción y unidad, precio solo en la lista nueva, y queda en
   `dados_de_alta`, no en `desconocidos`.
3. El desconocido no elegido no se crea y sigue en `desconocidos`.
4. `actualizar_precios` da el mismo comparativo con y sin alta (dos bases).
5. Elegir un insumo casado o un rechazado del 2b: `ValueError`, sin lista nueva ni insumos.

La mordida prevista: fijar el precio del dado de alta también en la lista anterior, o aceptar un
elegido que no es desconocido.

**Para las pistas U, A y R.** La página llama a `insumos_desconocidos` al subir el archivo y pasa la
selección en `dar_de_alta`; si ningún precio cambió (flujo 3a) la página deshace la transacción y
con ella las altas, y debe decirlo. La API recibe descripciones: las traduce con
`insumos_desconocidos` (una descripción que no está en la vista previa es 422) y responde
`dados_de_alta` con `insumo.codigo` o `insumo.descripcion`. Para R, los rechazados del 2b son
`ResumenLista.desconocidos` menos la vista previa.

## C6.3 INV-086: crear el proyecto de los presupuestos

**Problema.** UC‑01, paso 1 (`docs/ERS.md:141`): «El proyectista crea el proyecto y selecciona la
fuente de cantidades y su dominio». Crear el proyecto no existe en ninguna capa: `POST /presupuestos`
exige un proyecto ya sembrado (`api/rutas/presupuestos.py:102-106`, `LookupError` si no existe) y el
único que crea filas de `proyecto` es la siembra (`scripts/seed.py:83-116`, y los sembradores de los
otros dominios). La matriz por paso lo marca parcial (`docs/plan_pruebas.md`, UC‑01 1; inventario,
INV‑086).

**Diseño.** Un solo commit de `core/`, asunto `feat(budget): crear el proyecto de los presupuestos`,
con sus pruebas en `tests/integration/test_proyectos.py`:

- `core/budget/persistencia.py`: `crear_proyecto(session, nombre, descripcion="", dominio="") ->
  models.Proyecto`, junto a `guardar_presupuesto` (:67-153), porque el proyecto es la cabecera del
  presupuesto que ese módulo persiste (`models.Proyecto`, `core/models/entidades.py:250-263`).
  Normaliza el nombre (`strip`); `ValueError` si queda vacío, si ya existe un proyecto con ese nombre
  (la columna es única, :256, y chocar en el `flush` daría un `IntegrityError` que la API no sabe
  traducir) o si `dominio` no es vacío ni un valor de `core.contracts.Dominio` (el dominio se guarda
  como texto, `str(Dominio.CIVIL)` como en la siembra, :91-95). Hace `flush`, no `commit`, como
  `guardar_presupuesto`.
- `core/budget/__init__.py`: exporta `crear_proyecto`.

**Alternativa descartada.** Crear el proyecto implícitamente en `POST /presupuestos` cuando no
existe. Cambiaría «Elaborar un presupuesto» y la ruta por donde pasan CP‑07 y el indicador 3, que
Med mide (spec §10, enmienda de C6), y un error de tipeo en el nombre crearía un proyecto nuevo en
silencio en vez de responder 404. También se descartó ponerla en `core/catalog`: el proyecto no es
catálogo (partidas, insumos, precios), es la cabecera del documento que persiste `core/budget`.

**Por qué ningún contrato cambia.** `core/contracts/` no tiene tipo de proyecto: es una entidad de
persistencia (`models.Proyecto`) y la función devuelve el modelo, como `guardar_presupuesto`.

**Línea base.** Intacta: la siembra sigue creando su proyecto por su cuenta y ninguna ruta de
elaboración cambia.

**Pruebas previstas** (`tests/integration/test_proyectos.py`, base en memoria):

1. Crear un proyecto nuevo: queda con su nombre (sin espacios sobrantes), descripción y dominio, y
   `guardar_presupuesto` guarda sobre él el presupuesto de la línea base.
2. Nombre repetido (el de la siembra) o vacío, y dominio desconocido: `ValueError`, sin fila nueva.

La mordida prevista: quitar la comprobación del nombre existente (la prueba 2 recibe un
`IntegrityError`).

**Para la pista A.** `POST /proyectos` llama a `crear_proyecto` y confirma; el duplicado y el
dominio desconocido son `ValueError` (422 por `api/main.py:47-50`).
