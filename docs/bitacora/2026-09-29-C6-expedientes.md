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

## C6.4 INV-076: importar el presupuesto tabular de un tercero para auditarlo

**Problema.** RF‑24, esencial (`docs/ERS.md:528`): «El sistema importará un presupuesto de un tercero
en formato tabular, conservando las unidades originales escritas por su autor, para poder
auditarlo»; UC‑05, pasos 1 y 2 (`docs/ERS.md:264-265`): «el auditor selecciona el presupuesto o
**importa el archivo del tercero**» y «el sistema construye el `Presupuesto` en memoria conservando
las unidades escritas por el autor». Ninguna capa lee ese archivo: la API y la interfaz auditan solo
lo que el propio sistema elabora (UC‑01), y lo único que ejercita UC‑05 sobre un presupuesto ajeno es
la fixture `presupuesto_con_siete_inconsistencias` (`tests/fixtures/presupuesto_auditado.py:137-139`),
que arma el `Presupuesto` en Python (inventario, INV‑076; `docs/plan_pruebas.md`, UC‑05 1 y 2).

**Diseño.** Un solo commit de `core/`, asunto
`feat(budget): importar el presupuesto tabular de un tercero para auditarlo`, con sus pruebas en
`tests/integration/test_importacion_tercero.py` y la fixture nueva
`tests/fixtures/presupuesto_tabular.py`.

*Formato: un solo XLSX* (el CSV no tiene hojas), con todo número leído como texto y convertido a
`Decimal` (CLAUDE.md §2.3), como `leer_lista_precios`. Hojas y columnas (fuente única: las
constantes de `core/budget/importacion.py`):

| Hoja | Columnas | Notas |
|---|---|---|
| `Datos` | `clave`, `valor` | claves obligatorias: `codigo`, `fecha` (ISO), `moneda`, `dominio`, `fcas`, `bono_alimentacion`, `administracion`, `utilidad` |
| `Presupuesto` | `codigo_partida`, `descripcion`, `unidad`, `cantidad`, `origen_id`, `regla`, `parametros`, `especificaciones` | `unidad` es la del autor y se guarda también en `especificaciones[CLAVE_UNIDAD_ORIGINAL]` (como `tests/fixtures/computo_auditado.py:36-48`), así que «mts» llega a R3; `parametros` y `especificaciones`, objetos JSON (los números de `parametros` como texto o número, siempre a `Decimal`); `origen_tipo` es `REGLA` si hay regla y `MANUAL` si no (R1 advierte la trazabilidad ausente, UC‑05 2b); sin `origen_id`, `<archivo>:Presupuesto:<fila>` |
| `APU` | `codigo_partida`, `descripcion`, `unidad`, `rendimiento` | una fila por partida, código único |
| `Insumos` | `codigo_partida`, `tipo`, `insumo`, `unidad`, `cantidad`, `precio`, `depreciacion`, `modalidad` | `tipo` con las grafías de UC‑02 (`_a_tipo` de `core/catalog/precios.py:239-250`); `unidad` solo materiales; `depreciacion` solo equipos; `modalidad` solo mano de obra, jornal por defecto (D9); `precio` es el sueldo en la mano de obra |
| `Curva` (opcional) | `periodo`, `monto`, `acumulado` | la del autor, tal cual; sin ella R2 y R7 no aplican (UC‑05 2a) |

*Código:*

- Archivo nuevo `core/budget/importacion.py`:
  - `leer_presupuesto_tabular(ruta) -> PresupuestoImportado`, **pura** (no toca la base): construye
    los `ItemComputo`, las `ComposicionAPU` y los `ParametrosCosto`, arma el presupuesto con
    `generar_presupuesto` (`core/budget/presupuesto.py:62-88`, que exige composición para todo ítem)
    y le pone la curva del autor con `con_curva` (`core/budget/curva.py:77-82`). Devuelve
    `PresupuestoImportado` (presupuesto, parámetros, composiciones y dominio), un dataclass del
    módulo, no un contrato. Todo error de forma es `ValueError` con archivo, hoja y, si aplica, fila:
    hoja o columna ausente, clave de `Datos` ausente, número o fecha ilegibles, partida repetida en
    `APU`, insumo de una partida sin APU, y un ítem del presupuesto sin APU («ítem sin APU»: un
    presupuesto ajeno no tiene pendientes que proponer, el tercero entregó un documento incompleto).
  - `importar_presupuesto(session, ruta, proyecto) -> ResultadoElaboracion`: lee; audita siempre
    (`auditar`, principio 7); comprueba **antes de escribir** que ningún `codigo_partida` del
    archivo exista ya en el catálogo (si existe, `ValueError`: el APU del tercero no puede
    sustituir ni mezclarse con el del catálogo, y el caso necesita códigos propios) y que el
    proyecto no tenga ya un presupuesto con ese código; crea `ListaPrecios(nombre="Importada:
    <archivo>", origen=<archivo>, fecha_vigencia=<fecha del presupuesto>)` copiando los precios de
    la lista vigente a esa fecha si la hay, para que siga valorando el catálogo completo, como
    `crear_lista_desde_archivo` (`core/catalog/precios.py:286-288`); carga cada APU con
    `Catalogo.cargar_composicion(..., condiciones="importado de <archivo> (presupuesto de un
    tercero, UC-05)")` (`core/catalog/repositorio.py:138-183`: reutiliza los insumos homónimos con
    el mismo precio y crea variantes si difiere) y guarda con `guardar_presupuesto`
    (`core/budget/persistencia.py`), con el informe, la curva y los hallazgos. No confirma. Así la
    postcondición de UC‑05 («informe persistido y asociado al presupuesto») se cumple, y
    `cargar_elaboracion` recarga el mismo informe porque el catálogo reconstruye los APU del
    tercero con la lista importada.
- `core/catalog/precios.py`: `_leer_tabla(ruta, hoja=None)` y `_leer_tabla_excel(ruta, hoja=None)`
  (:167-210; hoy solo la hoja activa, :198) leen la hoja por su nombre; una hoja ausente es
  `ValueError` con archivo y hoja. Sin `hoja`, idénticas. Es la única lectura de XLSX sin `float`
  del sistema (docstring de :1-13) y la importación la reutiliza en vez de repetirla.
- `core/budget/__init__.py`: exporta `PresupuestoImportado`, `importar_presupuesto` y
  `leer_presupuesto_tabular`.

**Alternativas descartadas.** (a) *Auditar sin persistir.* Cumpliría los pasos 1 a 5, pero no la
postcondición de UC‑05 ni el paso 6 por las rutas que ya existen (`GET /presupuestos/{codigo}/informe`
y `…/excel` leen lo guardado). (b) *Persistir sin cargar los APU* (renglones sin partida del
catálogo): `models.PartidaPresupuestada.partida_id` es obligatorio y `cargar_presupuesto`
reconstruye cada renglón desde el catálogo; cambiarlo es cambiar el versionado híbrido
(docs/modelo_datos.md §5). (c) *Reutilizar la partida del catálogo si el código existe*: mezclaría
el APU del tercero con el propio y la reconstrucción denunciaría la diferencia; se rechaza (ruling
C6‑4). (d) *CSV con varias tablas* o varios archivos: el XLSX de hojas es el formato que ya usa el
sistema (`exportar_excel`) y un solo archivo es lo que el auditor recibe. (e) *Leer con
`pandas.read_excel`*: pasa los números por `float` (docstring de `core/catalog/precios.py:1-13`).

**Por qué ningún contrato cambia.** La importación produce `ItemComputo`, `ComposicionAPU`,
`ParametrosCosto` y `Presupuesto` tal como están, con la unidad original en
`especificaciones[CLAVE_UNIDAD_ORIGINAL]`, la convención que ya usan la fixture y la persistencia
(`_a_modelo_item`). `PresupuestoImportado` y `ResultadoElaboracion` son de `core/budget`.

**Línea base.** Intacta: el motor, las reglas y la siembra no cambian, y
`tests/fixtures/apu_linea_base.py` no se edita. La fixture tabular **deriva** de
`presupuesto_con_siete_inconsistencias()` sin repetir un dato, cambiando solo el prefijo de los
códigos de partida (`LB-` por `TER-`, también dentro de los `origen_id` y del balance de R5), porque
la base de prueba ya tiene sembradas las `LB-*` y la importación rechaza un código existente
(riesgo de C6‑plan §6). Efecto declarado en el catálogo: la lista «Importada» pasa a ser la vigente
a su fecha (tiene la misma fecha y mayor `id`), pero copia todos los precios de la anterior, así que
todo APU del catálogo se reconstruye igual; las partidas del tercero quedan en el catálogo y
aparecerán entre las similares de UC‑03.

**Ronda 1 de revisión (req 2, arq N-2 y N-7, qa N-QA-1), por `fixup` de este commit y del de
código.**

- *Monedas.* `importar_presupuesto` rechaza, sin escribir, el archivo cuya moneda difiere de la de
  la lista vigente a su fecha: la lista «Importada» copia esos precios y no mezcla monedas.
- *Presupuesto vacío.* Una hoja `Presupuesto` sin renglones es `ValueError` con archivo y hoja: un
  archivo sin cantidades ya no se importa ni sale CUMPLE.
- *Limitación declarada: la lista «Importada» pasa a ser la vigente.* Tiene la fecha del
  presupuesto del tercero y mayor `id`, así que `Catalogo.lista_vigente` la devuelve a esa fecha y
  después. Los importes no cambian (copia exacta de la anterior, y cada presupuesto se reconstruye
  con su propia lista), pero la procedencia sí (principio 6):
  - el marco de toda pantalla (`ui/caso.py:101`) y `api/rutas/catalogo.py:35` muestran como lista
    vigente la del tercero;
  - un presupuesto propio elaborado después por `POST /presupuestos`
    (`api/rutas/presupuestos.py:151`) o por «Elaborar» queda ligado a esa lista;
  - «Componer una partida» fija los precios de sus insumos nuevos y variantes en ella
    (`ui/elaboracion.py:210-219`);
  - toda lista cargada después (`crear_lista_desde_archivo`, `seed_demo`) la copia, variantes del
    tercero incluidas, y una lista de fecha posterior creada **antes** de la importación no tiene
    los insumos del tercero (revalorar el presupuesto importado contra ella daría
    `CatalogoIncompleto`);
  - las partidas `TER-*` entran en `catalogo.partidas(dominio)`: inflan el recuento que decide la
    técnica de la compuerta G2 en la ayuda 4 de «Componer» (`ui/paginas/componer.py:629`),
    aparecen en «Elaborar» y entre las similares de UC-03;
  - las variantes de insumo del tercero alimentan el histórico de `CambioPrecio` que usa el
    detector de atípicos.
  Excluir las listas importadas de `lista_vigente` exige una marca en el esquema y tocar
  `repositorio.py`, fuera de los archivos que la enmienda permite a este commit: queda para un
  sprint posterior, y la decisión, para Eugenio y el tutor (GC6).

**Pruebas previstas** (`tests/integration/test_importacion_tercero.py`, base en memoria y archivos
en `tmp_path`):

1. La lectura reproduce, código por código, los ítems (unidad del autor incluida), los APU y la
   curva de la fixture, y el total exacto de la línea base.
2. La importación audita 7 de 7 (oráculo: `INCONSISTENCIAS` de la línea base, con el prefijo
   cambiado), y el hallazgo de R3 cita «mts», la unidad del autor (criterio de RF‑24).
3. Guardar y recargar con `cargar_elaboracion` da el mismo informe y el mismo total.
4. Un código de partida que ya está en el catálogo (el archivo con `LB-`): `ValueError`, sin lista,
   partida ni presupuesto nuevos.
5. Hoja ausente, columna ausente e ítem sin APU: `ValueError` con archivo, hoja y fila.
6. Sin la hoja `Curva`: R2 y R7 se declaran no aplicables y las demás reglas se ejecutan.
7. Un ítem sin regla: `MANUAL` y la advertencia de trazabilidad ausente de R1.

La mordida prevista: normalizar la unidad del autor antes de guardarla en `especificaciones`
(R3 dejaría de citar «mts»), o no copiar la lista vigente (la línea base sembrada dejaría de
reconstruirse con la lista importada).

**Para la pista A.** `POST /presupuestos/importar` (multipart: `archivo` y `proyecto` como `Form`)
escribe el archivo en un `TemporaryDirectory` con su nombre, busca el `models.Proyecto` por nombre
(`LookupError` si no está, 404), llama a `importar_presupuesto`, confirma y responde 201 con
`PresupuestoCreadoRespuesta`, `pendientes=[]`; la ruta va antes de las que llevan `{codigo}`.

## C6.5 INV-099: los precios atípicos de la lista nueva entran al informe

**Problema.** UC‑07, paso 5 (`docs/ERS.md:317-318`): «El sistema marca como atípicos los precios que
se apartan del histórico **y los incorpora al informe de auditoría**». `ml.anomaly.precios_atipicos`
(`ml/anomaly/detector.py:83-100`) los marca y los muestra la ayuda 2 de «Componer una partida»
(`ui/composicion.py:650-670`) y `docs/resultados_ml.md`, pero ningún informe de auditoría los lleva:
`InformeAuditoria.a_markdown` (`core/verification/informe.py:123-170`) no los conoce y la
revaloración (`core/budget/actualizacion.py:112-179`) no los busca (inventario, INV‑099;
`docs/plan_pruebas.md`, UC‑07 5, parcial). La nota de arquitectura de GC4 en esa fila fija la
restricción: `core/` no importa `ml/`.

**Diseño.** Un solo commit de `core/`, asunto
`feat(budget): los precios atipicos de la lista nueva entran al informe`, con sus pruebas en
`tests/integration/test_atipicos_en_informe.py`. Los atípicos entran donde nacen los precios nuevos:
en el informe de la versión revalorada de UC‑02, que es el informe del presupuesto valorado con esa
lista.

- `core/budget/presupuesto.py`, junto a `CODIGO_PENDIENTE` y `_declarar_pendientes` (:43-46,
  :127-170):
  - `CODIGO_ATIPICO = "ATIPICO"` (cabe en `models.Hallazgo.regla`, `String(10)`,
    `core/models/entidades.py:390`).
  - `MarcaAtipica`, un `typing.Protocol` con `id: str`, `valor: Decimal` y `puntaje: float` (de solo
    lectura). `ml.anomaly.PrecioAtipico` (`ml/anomaly/detector.py:66-72`) lo cumple
    estructuralmente, sin que `core/` lo importe.
  - `DetectorAtipicos = Callable[[Mapping[str, Decimal]], Sequence[MarcaAtipica]]`: la forma de
    `precios_atipicos`, que recibe el histórico `{id del cambio: variación}`.
  - `_declarar_atipicos(informe, hallazgos)`: el mismo informe con los hallazgos `ATIPICO`
    agregados por `dataclasses.replace` (como `_declarar_pendientes` desde C5.2, así se conservan
    las reglas evaluadas y la atribución de cada regla), y la partida de cada uno en
    `partida_por_hallazgo`: la única partida que cita, o `None` si cita varias (el informe no elige
    una por su cuenta, como en INV‑095). Es la única definición de esa atribución: la usan la
    revaloración y la recarga.
- `core/budget/actualizacion.py`: `actualizar_precios(..., detectar_atipicos: DetectorAtipicos |
  None = None)` (:112-179). `registrar_cambios` (:177) pasa a ir **antes** de `guardar_presupuesto`
  (:167-175), porque los hallazgos se persisten al guardar; es idempotente y solo hace `flush`
  (`core/catalog/precios.py:366-401`), así que repetir UC‑02 con el mismo par de listas sigue sin
  duplicar filas. Con detector: el histórico es `{str(c.id): c.variacion for c in
  cambios_precio(session)}` (todo el historial persistido, incluidos los cambios de esta lista);
  de sus marcas se toman solo las de los cambios de **esta** lista; cada una da un
  `Hallazgo(regla="ATIPICO", severidad=ADVERTENCIA, descripcion="el precio de <insumo> paso de A a
  B (+x %): se aparta del historico de variaciones de precio (detector de atipicos, puntaje p;
  RF-29)", origen_ids=<códigos de las partidas del presupuesto que usan el insumo>,
  valor_observado=<variación>)`, con las partidas de `_partidas_por_insumo` (:276-300); un cambio
  que no toca ninguna partida del presupuesto no da hallazgo (no es un hallazgo **de este**
  presupuesto). El informe se declara con `_declarar_atipicos` y se guarda con esos hallazgos.
  Sin detector (`None`, el valor por defecto) el informe es el de hoy: ninguna llamada cambia.
- `core/budget/persistencia.py`: `cargar_elaboracion` (:188-209) vuelve a declarar los `ATIPICO`
  guardados del presupuesto (filas de `models.Hallazgo` con `regla == CODIGO_ATIPICO`), como ya hace
  con los pendientes: la reauditoría no puede recalcularlos (el detector no está en `core/` y el
  histórico habrá crecido), así que el informe recargado repite los del documento emitido. La
  conversión fila → `Hallazgo` vive aquí, el único módulo que cruza la frontera modelo↔contrato del
  presupuesto.
- `core/budget/__init__.py`: exporta `CODIGO_ATIPICO`, `DetectorAtipicos` y `MarcaAtipica`.
- No cambian: `InformeAuditoria`, `core/verification`, `a_markdown` (pinta el `ATIPICO` en su
  tabla como pinta el `PENDIENTE`), `core/budget/excel.py` (su hoja *Auditoria* recorre
  `informe.hallazgos`); la sección «Reglas evaluadas» no cuenta `ATIPICO`, porque no es una de las
  siete reglas (`cuenta_por_regla_evaluada`, `core/verification/informe.py:98-107`). El
  puntaje (`float`) solo aparece en el texto; la variación queda en `valor_observado` como `Decimal`.

**Alternativas descartadas.** (a) *Importar `ml.anomaly` desde `core/budget`*: rompe la frontera que
vigila `tests/unit/test_arquitectura.py` y haría del extra `ml` una dependencia del núcleo. (b)
*Una sección de atípicos en `a_markdown`* o un campo nuevo en `InformeAuditoria`: toca
`core/verification`, que la enmienda no abre, y cambiaría la huella del informe de RNF‑04 para todo
presupuesto; como hallazgos `ATIPICO` solo aparecen donde hay detector y cambios marcados. (c)
*Atípicos en la elaboración (UC‑01)*: el presupuesto nuevo no trae precios nuevos que juzgar contra
el histórico de variaciones, y «Elaborar» es lo que Med mide (spec §10). (d) *Severidad ERROR*: un
precio atípico es una alerta para revisar, no un incumplimiento; con ADVERTENCIA el veredicto
CUMPLE/NO CUMPLE no cambia por un juicio estadístico.

**Por qué ningún contrato cambia.** `Hallazgo.regla` es texto libre (`core/contracts/verificacion.py:
21-38`): `ATIPICO` es un código más, como `PENDIENTE` (C3). `MarcaAtipica` y `DetectorAtipicos`
son tipos de `core/budget`, no de `core/contracts/`.

**Línea base.** Intacta: con `detectar_atipicos=None` la revaloración produce el mismo presupuesto,
el mismo informe y el mismo historial que hoy, y la elaboración de la línea base no pasa por aquí.
El informe de RNF‑04 (elaboración del protocolo) no cambia de huella.

**Pruebas previstas** (`tests/integration/test_atipicos_en_informe.py`, base en memoria):

1. Con un detector falso que marca las variaciones mayores de 0,15 de una lista que sube el cemento
   (15 → 18, +20 %, solo en el concreto) y el ayudante (3 → 4, en las cinco partidas): dos
   `ATIPICO` de severidad ADVERTENCIA; el del cemento cita solo el concreto y se atribuye a él; el
   del ayudante cita las cinco partidas (oráculo: la línea base) y no se atribuye a ninguna; ambos
   quedan guardados y `cargar_elaboracion` los vuelve a declarar; el veredicto no cambia y la
   sección «Reglas evaluadas» no los cuenta.
2. Sin detector: el informe de la versión nueva es la auditoría de su presupuesto
   (`auditar(nuevo.presupuesto)`, otra ruta de código), sin `ATIPICO`.
3. Una marca de un cambio ajeno a esta lista, y la de un cambio de un insumo que ninguna partida
   usa: sin hallazgo.
4. Repetir la revaloración con el mismo par de listas no duplica el historial (idempotencia de
   UC‑02 con el nuevo orden).
5. Con `ml.anomaly.precios_atipicos` real (extra `ml`, que la CI instala; `importorskip` como las
   demás pruebas del extra) y un histórico de diez variaciones pequeñas: el cemento (+20 %) sale
   `ATIPICO` en el informe.

La mordida prevista: no filtrar las marcas por los cambios de esta lista, o atribuir el hallazgo
de varias partidas a la primera.

**Para las pistas A y U.** `POST /presupuestos/{codigo}/actualizacion` y la página «Actualizar
precios» pasan `detectar_atipicos=ml.anomaly.precios_atipicos` con import perezoso (como
`ui/composicion.py:609-612` y `api/rutas/rendimientos.py:160-166`); sin el extra `ml`, `None`. El
informe ya los trae: la página y `GET /presupuestos/{codigo}/informe` los muestran sin cambio.
