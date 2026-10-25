# Montar un presupuesto de punta a punta: plan de construcción

> **Para agentes:** SUB-SKILL OBLIGATORIA: superpowers:subagent-driven-development (implementador → árbitro por tarea, como
> mandan `docs/planes/MANUAL_SUBAGENTES_MIGRACION.md` y `docs/planes/MANUAL_ARBITRO.md`). Los pasos usan casillas (`- [ ]`).

**Meta:** que una persona haga una obra propia en Bs sin atajos: moneda explícita por carpeta, lista para armar, carpeta y
proyecto recordados, partidas agregadas a mano en la Hoja, ciclo de aprobación, estudio de mercado, y el control de obra con plan
por rendimientos, causas de retraso, procura con fechas, precio del corte declarado y APU arreglable en la versión.

**Arquitectura:** todo lo nuevo vive fuera de `core/`: lógica en `aplicacion/` (un módulo por pieza), tablas nuevas en módulos
`aplicacion/tablas_*.py` con su propio `MetaData` (precedente `paquete/modelo.py`), migraciones Alembic nuevas en
`migraciones/caso/` y `migraciones/instalacion/`, rutas nuevas en `api/rutas/`, páginas y componentes en `frontend-desktop/src/`.
El núcleo se usa tal cual: `copiar_precios`, `convertir_lista`, `tasa_aplicable`, `calcular_apu`, `evaluar`, `reproyectar`,
`PreciosDelCorte`, `GENESIS` y `EslabonVersion`.

**Tecnología:** Python 3 + SQLAlchemy 2 + Alembic + FastAPI (`uv run --active`); React 19 + TypeScript + `@carbon/react`
1.117.0 + Vitest/Testing Library; Playwright para Python (`uv run --active --with playwright`).

**Diseño:** `docs/especificaciones/2026-10-25-montar-presupuesto-design.md` (APROBADO; §10 y §11 mandan sobre §5). Diseños
citados: `2026-10-21-bienvenida-casos-proyectos-design.md` (BCP-5 §4.2-4.7, BCP-6 §5, pruebas F5-F11),
`2026-10-21-autocompletado-de-campos-design.md` (`CampoConBusqueda` §3, `GET /v1/buscar/partidas` §5.1-5.2 y §5.4),
`2026-10-25-barra-superior-design.md` (panel «Carpeta y proyecto», hueco `children` en `src/shell/PanelCarpetaProyecto.tsx:63`).
El ejecutor lee el diseño y este plan.

## Choques con el diseño (verificados en el código; propuesta en cada uno)

1. **Reproyección, alertas, valor ganado, plan y recuperación viven en `core/`, no en `aplicacion/` (§11).** `plan_secuencial`
   (`core/budget/curva.py:85`), `reproyectar` (`core/budget/valor_ganado.py:545`), `alertas` (`:764`), `opciones`
   (`core/budget/recuperacion.py:540`), `calcular_control` (`core/budget/control.py:193`). *Propuesta (sin bloqueo para el tutor):*
   el plan por rendimientos se calcula en `aplicacion/` y entra al núcleo como dato (`PeriodoPlan`), igual que hoy un plan editado a
   mano; la reproyección **ya es por partida** (`valor_ganado.py:623-650`: índice propio con evidencia, SPI global solo sin ella):
   el «adelantada, SPI 2,15» venía del plan de una partida por día, no de la fórmula. MP-7b agrega en `aplicacion/` el atraso en
   días y la causa por partida leyendo `Reproyeccion.partidas[*].fin`; las alertas del núcleo no se tocan.
2. **`revisa` con `cambiar_caso` le daría crear y subir carpetas** (`api/rutas/casos.py:238,250` usan `CAMBIAR_CASO`), no «solo
   lectura». *Propuesta:* revisa **no** gana `cambiar_caso`; `POST /v1/aprobaciones/abrir` (acción nueva `aprobar_version`) cambia
   la carpeta de esa sesión a la del envío. **Decisión para Eugenio** (ratificar).
3. **Revisa no puede leer la Hoja:** toda `/v1/hoja/*` exige `editar_hoja` (`api/rutas/hoja.py:207`). *Propuesta:* el detalle de
   lo que se aprueba sale de `GET /v1/aprobaciones/{id}` (sin abrir borrador) y se ve en una página nueva «Aprobar», solo lectura.
4. **La carpeta no tiene moneda en ninguna parte** (`aplicacion/casos.py:201` `EstadoCarpeta`, `api/rutas/casos.py`). Con D-MP1,
   `lista_para_armar` pierde el parámetro `moneda` de §5.1 y la moneda se guarda en una tabla nueva de la carpeta.
5. **No hay función que derive una lista con fecha nueva**; se arma con `copiar_precios` (`core/catalog/moneda.py:90`). La lista
   derivada no lleva `ListaPreciosOrigen`, así que es global y `lista_vigente` la elige (desempate por `id`, `repositorio.py:101`).
6. **MaPreX solo existe en Bs en la base** (`aplicacion/precios_empresa.py:73`, alcance `referencia`). En una carpeta en USD,
   «Crear desde MaPreX» convierte la referencia en Bs con `tasa_aplicable` (BCV, a lo sumo 7 días) y declara tasa y fecha.
7. **No hay IVA en el cálculo** (`ParametrosCosto`, `core/contracts/apu.py:143-158`): «precio con utilidad, sin IVA» es
   `ResultadoAPU.precio_unitario`; el piso «costo directo + administración» es `ResultadoAPU.con_administracion`.
8. **No hay cuadrillas en el APU** (`ComposicionAPU`, `apu.py:107`): «cuadrillas» es un divisor declarado al hacer el plan (1 por
   omisión), no un campo del APU.
9. **La explosión de insumos solo tiene sentido para materiales**: el material no se divide entre el rendimiento
   (`LineaMaterial`, `apu.py:26-31`); equipos y mano de obra no se compran. Procura = materiales.
10. **El plan propuesto en la primera versión cambia** (`aplicacion/hoja.py:1983-1984` usa `con_plan_secuencial`): las pruebas de
    la Hoja cuyo oráculo es «una partida por día» se rehacen a mano en la Tarea 21 (cambio de conducta declarado al árbitro, B4).
11. **Entregar propone la más nueva por `id`, no la vigente** (`api/rutas/entregas.py:127`); MP-4 la cambia por la última aprobada.
12. **Dos defectos de Control que MP-7 necesita corregir:** `/v1/control/calculo` pasa siempre la perspectiva `"costo"`
    (`api/rutas/control.py:102`) y `calcular_las_opciones` pierde `independientes` (`aplicacion/control.py:470-491`). Se corrigen
    en las Tareas 25 y 27, con su prueba.
13. **Las versiones ya son inmutables**: «una versión en aprobación no se edita» no requiere bloqueo; se cumple con la etiqueta, con
    «no se reenvía una devuelta» y con «hacer una versión nueva desde ella» (que es abrir su borrador, el flujo de hoy).
14. **Las aprobaciones viven en la carpeta y «Por aprobar» lista todas las carpetas:** dos bases, sin transacción común.
    *Propuesta:* la carpeta es la fuente de verdad; el índice en `instalacion.db` es un reflejo que se reescribe en cada envío y
    dictamen y se resincroniza para la carpeta abierta en cada `GET /v1/aprobaciones/pendientes`.
15. **No hay cadena de huellas fuera de `core/`**: el rastro de aprobaciones es una cadena nueva en `aplicacion/`, con
    `GENESIS` de `core/budget/cadena.py:64` y SHA-256 de JSON canónico.
16. **La Hoja en blanco nace en USD** (`hoja.Borrador.moneda` por omisión, `api/rutas/hoja.py:356`) y `crear_primera_version` exige
    `lista.moneda == moneda del proyecto` (`aplicacion/hoja.py:1973`): un proyecto en la otra moneda de la carpeta se valora con una
    lista convertida de alcance proyecto (`convertir_lista`, `core/catalog/moneda.py:133`) con la tasa del BCV.
17. **El guion del video** (`scratchpad/video/grabar.py`) usa los mismos dos atajos (`POST /v1/proyectos`, `POST /presupuestos`) y
    falló en su paso 21; se rehace sobre el recorrido de la Tarea 28.

## Restricciones globales

- `core/` intacto (`git diff <base>..HEAD -- core/` vacío). Árbol único `.worktrees/s2madm`, rama `inc/ruta-s2-mig-adm-empresa`;
  sin `git worktree add`, sin `.venv` ni `node_modules` nuevos, sin `npm install`, sin cambiar `package.json`; `uv run --active`.
- **Una moneda por carpeta** (D-MP1): `MONEDAS = ("Bs", "USD")` (`core/catalog/moneda.py:20`). Ningún precio cambia de moneda en
  silencio; toda conversión dice tasa, fecha y fuente (`TasaDeclarada`, `core/catalog/moneda.py:35`).
- Dinero y cantidades: `Decimal` en Python, **texto** en la API (decimal con punto), nunca `float`; el front no calcula ni redondea
  montos (formatea con `formatoEsVe`/`centesimasEsVe`). Lo que la persona **teclea** en las rutas nuevas llega como texto tal cual
  y lo interpreta `aplicacion/cifras.py::cifra_escrita` (coma decimal, punto de miles; 422 con `MENSAJE_CIFRA`).
- Tablas nuevas: un módulo `aplicacion/tablas_<pieza>.py` por pieza, con su `MetaData` propio, sin clave foránea a `core.models`
  (como `paquete/modelo.py`); montos con `DecimalExacto` (`core/models/tipos.py:14`), `sa.String(40)` en la migración; migración
  con `_faltan(...)` como `migraciones/caso/versions/caso_0009_s3_paquete.py:25`; escrituras de rastro solo por inserción.
- **Numeración de migraciones (fija, en este orden de integración):** caso `caso_0010_mp_carpeta` (T1), `caso_0011_mp_medicion`
  (T9), `caso_0012_mp_mercado` (T13), `caso_0013_mp_aprobacion` (T17), `caso_0014_mp_causas` (T22), `caso_0015_mp_procura` (T23),
  `caso_0016_mp_corte` (T25); instalación `ins_0004_mp_eleccion` (T5), `ins_0005_mp_indice_aprobacion` (T18). Si una tarea de número
  mayor termina antes, el orquestador ajusta su `down_revision` al integrar.
- **Archivos compartidos (solo el orquestador, con el texto exacto que entrega el implementador):** `api/main.py`,
  `frontend-desktop/src/shell/rutas.ts` y su prueba, `tests/unit/test_api_acceso_por_ruta.py` (`TABLA`, `ROLES`),
  `tests/unit/test_arquitectura.py`, `seguridad/permisos.py` y `tests/unit/test_permisos.py` (`MATRIZ`), las listas literales de
  acciones de sesión (`tests/unit/test_api_sesion_web.py:65-75`, `test_api_primer_arranque.py:83-105`,
  `test_api_sesion_contrasena.py:55-66`, `src/shell/Shell.test.tsx`, `src/App.test.tsx`, `src/paginas/inicio/Inicio.test.tsx`),
  `migraciones/metadatos.py`, `tests/unit/test_migraciones_metadatos.py`, los pinos de cabeza `ins_0003_auditoria_libro`
  (`tests/integration/test_migraciones.py:274,296`, `test_migracion_instalacion.py:41`, `test_migracion_produccion.py:49,88,91`,
  `test_migracion_auditoria_libro.py:72,139,142`, `test_preparar_base.py:251`, `test_respaldo.py:101`), `docs/api.json`
  (`scripts/exportar_openapi.py`), `CHANGELOG.md`, `docs/ERS.md`.
- Permisos (fila nueva en `seguridad/permisos.py`, la aplica el orquestador en la Tarea 18): `Accion.APROBAR_VERSION =
  "aprobar_version"` → `frozenset({_ARMA, _REVISA})`, declarada después de `REVISAR_PAQUETE`. Ninguna otra acción cambia.
- Datos ficticios en todo lo versionado («Contratista Demo, C.A.», `J-00000000-0`, la vivienda de 80 m² con OBRA-01..06);
  observaciones de mercado ficticias. Nunca libros, nombres ni precios reales de la empresa o de la competencia.
- Texto visible en español con tildes, lenguaje llano, sin jerga (UC-xx, RF-xx, MP-x, R1 a secas); «carpeta de trabajo» en la
  interfaz; fechas `dd/mm/aaaa` (`fechaEsVe`); Carbon g10, densidad `sm`, sin animación, sin morado, un h1 por página, 1366×768 y
  1056 px sin desplazamiento horizontal.
- TDD con rojo visto; prueba e implementación en commits separados (`test(...)… (rojo)` y luego `feat(...)`); asunto sin tildes;
  `git commit <rutas> -m ...` solo con las rutas propias; trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` (o el
  modelo del implementador). Pruebas Python con `-q -W error -p no:cacheprovider`; front con `npx vitest run <ruta>`,
  `npm run lint`, `npm run build`. Sin push ni PR.

## Foco de revisión

Lo que una persona real encontrará primero; cada línea tiene su prueba en la tarea dueña:

1. **Moneda:** carpeta en Bs cuya lista vigente está en USD (o proyecto en USD dentro de una carpeta en Bs) → Componer no guarda y
   lo dice; la Hoja valora con una lista convertida que declara tasa y fecha, o se niega si no hay tasa del BCV de los últimos 7 días
   (Tareas 1, 3 y 9).
2. **Pérdida de datos al cambiar de carpeta:** con un borrador con cambios en la Hoja o un APU a medio componer, cambiar de carpeta
   (o abrir un envío de otra carpeta desde «Por aprobar») pide confirmación; la carpeta recordada que ya no existe abre la de
   omisión con aviso, sin error (Tareas 5, 6 y 19).
3. **Dictamen que no vuelve:** Ana ve «Devuelta» con las notas en su Inicio y en la Hoja tras salir, entrar y reiniciar la API; dos
   dictámenes a la vez sobre el mismo envío → el segundo recibe 409 y no queda rastro doble (Tareas 17, 18 y 19).
4. **Plan irreal:** partida sin composición o con cantidad 0, duración de medio día y partidas en paralelo → el plan sigue siendo
   válido (cada partida suma exactamente 1) y lo dice; con la vivienda y el concreto atrasado Sílice dice «atrasada», no
   «adelantada» (Tareas 21 y 22).
5. **Compra tardía no avisada:** el cemento sin pedir a 2 días hábiles de su fecha límite avisa; pasada la fecha, error; recibido
   después de que se necesitaba, alerta de compra tardía y la causa se sugiere en la valuación; un feriado declarado corre las
   fechas (Tarea 23).

---

## Orden y paralelismo

| Ola | Tareas (‖ = a la vez) | Archivos propios que no se cruzan |
|---|---|---|
| A | T1 ‖ T5 ‖ T10 | T1 `aplicacion/listas_para_armar.py`; T5 `aplicacion/eleccion.py`, `api/rutas/sesion.py`, `api/rutas/casos.py`; T10 `aplicacion/busqueda.py`, `src/comun/CampoConBusqueda*` |
| B | T2 ‖ T3 ‖ T6 ‖ T8 ‖ T13 ‖ T17 | T2 `api/rutas/carpeta.py`; T3 `aplicacion/composicion.py`, `api/rutas/composicion.py`; T6 `src/shell/carpetas/**`, `Shell.tsx`, `Selectores.tsx`; T8 `aplicacion/hoja.py`, `aplicacion/hoja_partidas.py`; T13 `aplicacion/mercado.py`; T17 `aplicacion/aprobaciones.py` |
| C | T4 ‖ T7 ‖ T9 ‖ T14 | T4 `src/paginas/componer/**`, `src/shell/ListaDeLaCarpeta*`; T7 `src/shell/proyectos/**`, `Shell.tsx`; T9 `aplicacion/hoja_{vista,edicion,guardado}.py`, `api/rutas/hoja.py`, `api/esquemas_hoja.py`; T14 `api/rutas/mercado.py` |
| D | T11 ‖ T12 ‖ T15 ‖ T18 | T11 `src/paginas/hoja/{index,PestanaPresupuesto,AgregarPartida*}`; T12 `aplicacion/elaboracion.py`, `api/rutas/hoja_llevar.py`, `src/paginas/elaborar/**`; T15 `src/paginas/mercado/**`; T18 `api/rutas/aprobaciones.py`, `aplicacion/indice_aprobaciones.py` |
| E | T16 ‖ T19 ‖ T21 | T16 `src/paginas/hoja/ObjetivoDeMercado*`; T19 `src/paginas/hoja/AprobacionDeVersion*`, `src/paginas/inicio/**`; T21 `aplicacion/plan_rendimientos.py`, `src/paginas/hoja/PestanaPlan.tsx` |
| F | T20 ‖ T22 ‖ T23 | T20 `src/paginas/aprobar/**`, `src/paginas/entregar/**`, `control/PestanaLineaBase.tsx`, `hoja/PestanaTrazabilidad.tsx`; T22 `aplicacion/causas.py`, `control/{PestanaValuaciones,PestanasDeResultados,logica}`; T23 `aplicacion/procura.py`, `api/rutas/procura.py` |
| G | T24 ‖ T26 | T24 `control/PestanaProcura*`, `control/index.tsx`; T26 `aplicacion/hoja_lineas_apu.py`, `hoja/PestanaApu.tsx` |
| H | T25 | `aplicacion/precios_declarados.py`, `aplicacion/control.py`, `api/rutas/control.py`, `control/PestanasDeResultados.tsx` |
| I | T27 | `aplicacion/control.py`, `api/rutas/control.py`, `control/PestanasDeResultados.tsx` |
| J | T28 → T29 | `scripts/recorrido_obra.py`, video, manual |

Dependencias: T2←T1; T3←T1; T4←T2,T3,T6; T6←T2 (moneda al crear); T7←T5,T6; T9←T1,T8; T11←T9,T10; T12←T9; T14←T13; T15←T14;
T16←T11,T14; T18←T5,T17; T19←T18,T11; T20←T19; T21←T9; T22←T21; T23←T21,T13; T24←T22,T23; T25←T22,T23,T14; T26←T21;
T27←T25,T26; T28←todas; T29←T28. El montaje de `ListaDeLaCarpeta` en el hueco `children` del panel (`Shell.tsx`) lo hace el
orquestador al cerrar la ola C.

---

## MP-1 · Moneda explícita y lista para armar

### Tarea 1: Moneda de la carpeta y lista para armar

**Archivos:**
- Crear: `aplicacion/tablas_carpeta.py`, `aplicacion/listas_para_armar.py`, `migraciones/caso/versions/caso_0010_mp_carpeta.py`
- Prueba: `tests/unit/test_listas_para_armar.py`
- Compartidos (orquestador): `migraciones/metadatos.py` (`METADATA_CARPETA` en `METADATAS_CASO`), su prueba, `CHANGELOG.md`

**Interfaces:**
- Tabla `mp_carpeta` (una sola fila, `id=1`): `moneda String(10)`, `declarada_por String(200)`, `declarada_el DateTime`.
- Produce, en `aplicacion/listas_para_armar.py`:
  ```python
  class SinListaParaArmar(ValueError): ...          # el mensaje es el que ve la persona
  @dataclass(frozen=True) class ListaParaArmar: lista_id: int; nombre: str; moneda: str; fecha: date; origen: str
  def moneda_de_la_carpeta(sesion: Session) -> str | None
  def declarar_moneda_de_la_carpeta(sesion: Session, moneda: str, *, responsable: str, ahora: datetime) -> None
  def lista_para_armar(sesion: Session, fecha: date) -> models.ListaPrecios
  def lista_de_hoy(sesion: Session, fecha: date, *, nueva_si_usada: bool) -> models.ListaPrecios
  def lista_para_el_proyecto(sesion: Session, proyecto: str, fecha: date, *, responsable: str) -> models.ListaPrecios
  def crear_lista_para_armar(sesion: Session, *, desde: Literal["maprex", "convertir"], fecha: date, responsable: str) -> models.ListaPrecios
  def describir(sesion: Session, fecha: date) -> ListaParaArmar | None
  ```
  `moneda_de_la_carpeta`: la declarada; si no hay, la de `Catalogo.lista_vigente(fecha)`; si no hay lista, `None`.
  `lista_para_armar`: la vigente; `SinListaParaArmar` si no hay ninguna («Esta carpeta de trabajo no tiene lista de precios para
  armar. Créela a partir de MaPreX o convirtiendo la que tiene.») o si su moneda difiere de la carpeta («La lista vigente
  «{nombre}» está en {m1} y la carpeta trabaja en {m2}: conviértala antes de armar.»).
  `lista_de_hoy`: la de `lista_para_armar` si su `fecha_vigencia == fecha` y (con `nueva_si_usada`) ninguna versión la usa; si no,
  una lista nueva global de esa moneda y fecha con `copiar_precios(sesion, base, nueva, None)`, `origen = f"derivada de «{base}»"`,
  nombre `f"{raiz} al {fecha:%d/%m/%Y}"` (raíz = el nombre de la base sin un sufijo final ` al dd/mm/aaaa` ni ` (n)`), y `" (2)"`,
  `" (3)"`… si ese nombre ya existe.
  `lista_para_el_proyecto`: `lista_para_armar` si la moneda del proyecto (`moneda_del_proyecto`, `core/budget/moneda.py:37`) es la
  de la carpeta; si no, la convertida de alcance proyecto de ese día (`convertir_lista` con `TasaDeclarada.de_importacion(
  tasa_aplicable(sesion, fecha))`), reutilizada si ya existe para esa base y fecha; `TasaNoDisponible` → `SinListaParaArmar`
  («No hay tasa del BCV de los últimos 7 días: cárguela en Índices y vuelva a intentar.»).
  `crear_lista_para_armar("maprex")`: si no hay referencia, `cargar_referencia_maprex(sesion)`; copia
  `lista_de_referencia(sesion)` a una global en la moneda de la carpeta, convirtiendo con la tasa del BCV si la carpeta es USD.
  `("convertir")`: copia la vigente (otra moneda) a la de la carpeta con la tasa del BCV. Ambas fechadas `fecha`.

- [ ] **Paso 1: pruebas en rojo** (`tests/unit/test_listas_para_armar.py`, base en memoria con `crear_esquema` + `METADATA_CARPETA`,
  datos ficticios):
  - sin declarar y sin listas → `moneda_de_la_carpeta(s) is None`; con una lista vigente en Bs → `"Bs"`; declarada `"USD"` con lista
    vigente en Bs → `"USD"`;
  - `lista_para_armar` sin listas levanta `SinListaParaArmar` con el texto exacto de arriba; carpeta USD con vigente «Base» en Bs →
    `"La lista vigente «Base» está en Bs y la carpeta trabaja en USD: conviértala antes de armar."`;
  - `lista_de_hoy(s, date(2026,10,25), nueva_si_usada=False)` con la vigente «MaPreX julio 2026 en Bs» del 01/07/2026 → lista nueva
    «MaPreX julio 2026 en Bs al 25/10/2026», moneda Bs, mismos precios (3 insumos ficticios, comparados uno a uno), y es la que
    devuelve `Catalogo.lista_vigente(date(2026,10,25))`; llamada otra vez → la misma (mismo `id`);
  - con una versión guardada que usa «… al 25/10/2026», `nueva_si_usada=True` → «MaPreX julio 2026 en Bs al 25/10/2026 (2)»; otra
    vez con otra versión encima → «… (3)»;
  - `crear_lista_para_armar(desde="maprex")` en carpeta USD con tasa BCV 40,00 del 24/10/2026: un insumo de 400 Bs queda en 10 USD
    y su `PrecioOrigen` dice tasa 40 y fecha 24/10/2026; sin tasa de los últimos 7 días → `SinListaParaArmar` con el texto de la tasa;
  - **foco 1:** proyecto en USD en carpeta Bs: `lista_para_el_proyecto` devuelve una lista en USD de alcance `proyecto` con la tasa
    declarada; dos llamadas el mismo día → mismo `id`.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_listas_para_armar.py -q -W error -p no:cacheprovider` → FALLA (módulo
  inexistente).
- [ ] **Paso 3:** implementar `tablas_carpeta.py` (`METADATA_CARPETA`, `crear_esquema_carpeta(engine)`), la migración
  `caso_0010_mp_carpeta` (`down_revision = "caso_0009_s3_paquete"`) y el módulo.
- [ ] **Paso 4:** misma orden → PASA; `uv run --active pytest tests/integration/test_migraciones.py -q -W error` con el texto
  compartido aplicado localmente por el orquestador → PASA.
- [ ] **Paso 5:** commits `test(armar): moneda de la carpeta y lista para armar (rojo)` y `feat(armar): moneda de la carpeta y
  lista para armar`.

### Tarea 2: Rutas de la carpeta

**Archivos:**
- Crear: `api/rutas/carpeta.py`
- Prueba: `tests/unit/test_api_carpeta.py`
- Compartidos: `api/main.py` (`app.include_router(carpeta.router)`), `TABLA` de acceso, `docs/api.json`, `CHANGELOG.md`

**Interfaces:**
- Consume: Tarea 1.
- Produce (`prefix="/v1/carpeta"`, `RutaSinEco`):
  - `GET ""` (`CUALQUIER_ROL`) → `{moneda: str|null, declarada: bool, lista: {nombre, moneda, fecha, origen}|null, aviso: str|null}`
    (`aviso` = el mensaje de `SinListaParaArmar`, si lo hay).
  - `PUT /moneda` (`EDITAR`) cuerpo `{moneda: "Bs"|"USD"}` → 200 con la misma forma; 409 «La carpeta de trabajo ya trabaja en
    {m}: para trabajar en {otra}, cree otra carpeta.» si ya hay moneda declarada distinta o una lista vigente en otra moneda.
  - `POST /lista-para-armar` (`EDITAR`) cuerpo `{desde: "maprex"|"convertir"}` → 201 con la misma forma; 409 con el mensaje de
    `SinListaParaArmar`.

- [ ] **Paso 1: pruebas en rojo** con `con_cuenta`/`protegida` (`tests/fixtures/sesion_web.py`): `GET` en carpeta vacía →
  `{"moneda": null, "declarada": false, "lista": null, "aviso": "Esta carpeta de trabajo no tiene lista…"}`; ana `PUT` Bs → 200 y
  `GET` dice `"Bs"`, `declarada: true`; `PUT` USD después → 409 con el texto exacto; `POST {desde:"maprex"}` → 201 y
  `lista.nombre == "MaPreX julio 2026 en Bs al <hoy dd/mm/aaaa>"`; rita `PUT` → 403 `MENSAJE_PERMISO`; sin CSRF → 403; un 422 no
  repite lo enviado.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_carpeta.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar; montaje y filas de `TABLA` en el informe para el orquestador.
- [ ] **Paso 4:** misma orden + `tests/unit/test_api_acceso_por_ruta.py` → PASA.
- [ ] **Paso 5:** commits `test(api): rutas de la carpeta (rojo)` / `feat(api): moneda y lista para armar de la carpeta`.

### Tarea 3: Componer guarda en la lista de hoy y avisa las variantes

**Archivos:**
- Modificar: `aplicacion/composicion.py:889-903` (`guardar_composicion`: la lista sale de `lista_de_hoy(..., nueva_si_usada=False)`,
  no de `catalogo.lista_vigente`), `api/rutas/composicion.py` (ruta nueva y 409)
- Prueba: `tests/unit/test_composicion_lista_de_hoy.py`, `tests/unit/test_api_composicion_prever.py`
- Compartidos: `TABLA` de acceso, `docs/api.json`

**Interfaces:**
- Produce: `def prever_guardado(sesion: Session, codigo: str, ..., *, fecha: date, condiciones: str) -> Prevision` (mismos
  parámetros que `guardar_desde_tablas`, `aplicacion/composicion.py:1239`), que corre el guardado dentro de
  `sesion.begin_nested()` y lo deshace; `@dataclass Prevision: lista: ListaParaArmar; lista_nueva: bool; variantes:
  list[AvisoVariante]`; `AvisoVariante(descripcion: str, unidad: str, precio_en_lista: Decimal, precio_tecleado: Decimal,
  codigo_variante: str)` leído de `ResumenCarga.variantes`.
- `POST /v1/composicion/prever` (`EDITAR`), cuerpo `PeticionGuardar` → `{lista:{nombre,moneda,fecha}, lista_nueva: bool,
  variantes:[{descripcion, unidad, precio_en_lista, precio_tecleado, codigo_variante}]}`. `POST /guardar` y `/prever` responden
  409 con el mensaje de `SinListaParaArmar`.

- [ ] **Paso 1: pruebas en rojo:**
  - vigente del 01/07/2026 en Bs, guardar con `fecha=2026-10-25` un APU con un insumo nuevo a «18,00» → el precio queda en la lista
    «… al 25/10/2026», **no** en la del 01/07 (O-13); la del 01/07 no cambia (mismo número de precios);
  - `prever_guardado` con «Cemento gris» que ya está a 18 Bs y tecleado a 20 → una `AvisoVariante("Cemento gris", "saco", 18, 20,
    "MAT-001-B")` (código ficticio de la siembra) y, después, el catálogo no tiene `MAT-001-B` (se deshizo) ni la lista nueva;
  - **foco 1:** carpeta en USD con vigente en Bs → `/guardar` 409 con «La lista vigente … está en Bs y la carpeta trabaja en USD…» y
    nada escrito; `/prever` igual.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_composicion_lista_de_hoy.py tests/unit/test_api_composicion_prever.py -q
  -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar; correr también `tests/unit/test_api_composicion*.py tests/integration/test_composicion*.py`.
- [ ] **Paso 4:** todo lo anterior → PASA.
- [ ] **Paso 5:** commits `test(componer): lista de hoy y variantes previstas (rojo)` / `feat(componer): guarda en la lista de hoy
  y avisa las variantes`.

### Tarea 4: Componer y el panel dicen la moneda (front)

**Archivos:**
- Modificar: `frontend-desktop/src/paginas/componer/index.tsx`, `cliente.ts` (sustituye `GET /v1/casos/actual` por
  `GET /v1/carpeta`), el aviso `AvisoSinLista`
- Crear: `frontend-desktop/src/shell/ListaDeLaCarpeta.tsx` (+ `.test.tsx`)
- Prueba: `frontend-desktop/src/paginas/componer/Moneda.test.tsx`

**Interfaces:**
- Consume: Tareas 2 y 3; `useFormularioSucio` (Tarea 6): Componer llama `useFormularioSucio("componer", hayDatos)` con
  `hayDatos` = algún campo de la cabecera o alguna fila escrita sin guardar. Produce:
  `export function ListaDeLaCarpeta(props: { alExpirar: () => void }): JSX.Element` — texto
  «Moneda de trabajo: Bs · Lista para armar: {nombre}, al {dd/mm/aaaa}» o el `aviso`; lo monta el orquestador en `children`.
- Componer acepta `?codigo=X&volver=hoja`: precarga el código y, tras guardar, ofrece «Volver a la Hoja» (lo usa la Tarea 11).

- [ ] **Paso 1: pruebas en rojo** (`fetch` simulado):
  - Componer muestra «Precios en Bs» sobre las tablas y el precio unitario como «2.074,44 Bs»; no hay selector de moneda;
  - con `aviso` de la carpeta, Componer muestra el aviso con dos botones «Crear la lista a partir de MaPreX» y «Convertir la lista
    que tiene» (este solo si `lista` existe en otra moneda); pulsar el primero hace `POST /v1/carpeta/lista-para-armar
    {desde:"maprex"}` y luego habilita Guardar;
  - **foco 1:** Guardar llama primero `/prever`; con `variantes` no vacías abre un diálogo «“Cemento gris” ya está a 18,00 Bs; con
    20,00 Bs se creará una variante solo para este APU.» con «Guardar así» / «Volver»; «Volver» no llama `/guardar`;
  - `ListaDeLaCarpeta`: el texto exacto de arriba con una lista del 25/10/2026; con `moneda: null` dice «Carpeta sin moneda
    declarada»;
  - ninguna cadena visible contiene «caso»;
  - **foco 2:** con una fila escrita, `formulariosSucios()` contiene `"componer"`; tras guardar o vaciar, ya no;
  - con `#/componer?codigo=OBRA-07&volver=hoja` el código llega precargado y, guardado, aparece «Volver a la Hoja».
- [ ] **Paso 2:** `npx vitest run src/paginas/componer src/shell/ListaDeLaCarpeta.test.tsx` → FALLA.
- [ ] **Paso 3:** implementar; montos tal cual llegan, con `formatoEsVe`.
- [ ] **Paso 4:** misma orden, `npm run lint`, `npm run build` → PASA.
- [ ] **Paso 5:** commits `test(front): componer en la moneda de la carpeta (rojo)` / `feat(front): componer y panel con la moneda
  de la carpeta`.

## MP-2 · Crear el proyecto y recordar la elección

### Tarea 5: Recordar carpeta y proyecto por cuenta (backend)

**Archivos:**
- Crear: `aplicacion/tablas_eleccion.py`, `aplicacion/eleccion.py`, `migraciones/instalacion/versions/ins_0004_mp_eleccion.py`
- Modificar: `api/rutas/casos.py:118-144` (`elegir_caso` guarda la elección), `api/rutas/sesion.py` (`GET /v1/sesion` restaura y
  devuelve `eleccion`; ruta nueva `PUT /v1/sesion/proyecto`)
- Prueba: `tests/unit/test_api_eleccion.py`
- Compartidos: `METADATAS_INSTALACION`, pinos de cabeza de instalación (→ `ins_0004_mp_eleccion`), `TABLA`, `docs/api.json`

**Interfaces:**
- Tabla `mp_eleccion` (instalación): `usuario_id Integer PK`, `caso String(255)`, `proyecto String(120) null`, `fecha DateTime`.
- `def recordar_caso(sesion_ins: Session, usuario_id: int, caso: str, ahora: datetime) -> None` (borra el proyecto);
  `def recordar_proyecto(sesion_ins, usuario_id: int, proyecto: str | None, ahora) -> None`;
  `def eleccion_de(sesion_ins, usuario_id: int) -> Eleccion | None` con `Eleccion(caso: str, proyecto: str | None)`.
- `GET /v1/sesion`: si `caso_web.elegido(huella)` es `None` y hay elección cuyo caso está en `listar_casos()`, hace
  `caso_web.fijar`; responde además `eleccion: {caso, proyecto, aviso}`; si el caso recordado ya no existe, `caso` es el de
  omisión y `aviso` = «La carpeta de trabajo «{x}» ya no existe; se abrió la de siempre.»; si el proyecto ya no existe, `proyecto`
  es `null`.
- `PUT /v1/sesion/proyecto` (sesión con cualquier rol) cuerpo `{proyecto: str|null}` → 204.

- [ ] **Paso 1: pruebas en rojo:**
  - ana elige `s1.db` (`POST /v1/casos/actual`) y el proyecto «Torre B» (`PUT`), sale, entra → `GET /v1/sesion` trae
    `eleccion.caso == "s1.db"` y `proyecto == "Torre B"`, y `GET /v1/casos` dice `actual == "s1.db"` sin volver a elegir;
  - **reinicio de la API:** `caso_web.olvidar_todo()` + `dependencias.cerrar_motores()` con la misma ficha → `GET /v1/sesion`
    restaura `s1.db`;
  - **foco 2:** se borra `s1.db` entre sesiones → `eleccion.caso` es el de omisión y `aviso` el texto exacto; ningún 500;
  - elegir otra carpeta borra el proyecto recordado; rita y admin también recuerdan (todas las cuentas);
  - `PUT /v1/sesion/proyecto` sin CSRF → 403.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_eleccion.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar (escritura en instalación con `sesion_instalacion_api()`, una transacción por petición).
- [ ] **Paso 4:** misma orden + `tests/unit/test_api_casos.py tests/unit/test_api_sesion_web.py` → PASA.
- [ ] **Paso 5:** commits `test(api): recordar carpeta y proyecto por cuenta (rojo)` / `feat(api): recordar carpeta y proyecto
  por cuenta`.

### Tarea 6: Carpetas de trabajo en el panel (BCP-5) con su moneda y la confirmación

**Archivos:**
- Crear: `frontend-desktop/src/shell/carpetas/` (diálogo «Carpetas…» con Crear / Subir un archivo / Demostración, como BCP-5 §4.7;
  `ConfirmarCambio.tsx`), `frontend-desktop/src/shell/sucio.ts`
- Modificar: `frontend-desktop/src/shell/Shell.tsx` (`cambiarCaso` :213-234 pasa por la confirmación), `Selectores.tsx`
- Prueba: `frontend-desktop/src/shell/carpetas/Carpetas.test.tsx`, `src/shell/sucio.test.ts`

**Interfaces:**
- `sucio.ts`: `export function useFormularioSucio(id: string, sucio: boolean): void`, `export function formulariosSucios():
  string[]` (almacén externo como `recorrido.ts`; se limpia al desmontar).
- Crear carpeta: campo **Moneda de trabajo** (`Select` sin preselección, «Elija…», obligatorio); secuencia `POST /v1/casos` →
  `POST /v1/casos/actual` → `PUT /v1/carpeta/moneda`.
- Confirmación: borradores con cambios (`GET /v1/hoja/borradores`, `cambios>0`, BCP-5 §4.6) **o** `formulariosSucios()` no
  vacío → diálogo «Tiene cambios sin guardar en {lista}. Si cambia de carpeta se perderán.» con «Quedarme» / «Cambiar y descartar».

- [ ] **Paso 1: pruebas en rojo:** F5 a F9 del diseño BCP (§10.4, líneas 721-725) tal como están escritas, más: crear sin moneda →
  «Elija la moneda de trabajo de la carpeta.» y no llama a la API; crear con Bs → las tres llamadas en ese orden con `{moneda:"Bs"}`;
  **foco 2:** con `useFormularioSucio("componer", true)` montado, elegir otra carpeta abre el diálogo y «Quedarme» no llama
  `POST /v1/casos/actual`.
- [ ] **Paso 2:** `npx vitest run src/shell` → FALLA.
- [ ] **Paso 3:** implementar (diálogo propio, sin `Modal` de Carbon, como manda BCP-5 §4.7). Componer se registra en la
  Tarea 4 y Estudio de mercado en la 15.
- [ ] **Paso 4:** `npx vitest run src/shell`, `npm run lint`, `npm run build` → PASA.
- [ ] **Paso 5:** commits `test(front): carpetas con moneda y confirmacion (rojo)` / `feat(front): carpetas de trabajo en el panel`.

### Tarea 7: Nuevo proyecto (BCP-6) y restaurar la elección

**Archivos:**
- Crear: `frontend-desktop/src/shell/proyectos/` (diálogo «Nuevo proyecto», BCP-6 §5.2)
- Modificar: `Shell.tsx` (estado inicial de carpeta y proyecto desde `sesion.eleccion`; `PUT /v1/sesion/proyecto` al elegir;
  aviso de `eleccion.aviso`), `Selectores.tsx` («(sin versión guardada)»), una línea de `src/paginas/hoja/index.tsx` (estado vacío)
- Prueba: `src/shell/proyectos/NuevoProyecto.test.tsx`, ajustar `src/shell/Shell.test.tsx`

**Interfaces:** el diálogo propone por omisión la moneda de la carpeta (`GET /v1/carpeta`); si se elige la otra, dice «Este proyecto
se valorará convirtiendo los precios de la carpeta con la tasa del BCV del día.».

- [ ] **Paso 1: pruebas en rojo:** F10 y F11 del diseño BCP; la moneda propuesta es la de la carpeta y elegir la otra muestra el
  texto exacto; al recargar con `eleccion = {caso:"s1.db", proyecto:"Torre B"}` el panel dice «s1 · Torre B» sin elegir nada;
  elegir un proyecto llama `PUT /v1/sesion/proyecto {proyecto:"Torre B"}`; con `eleccion.aviso` se ve el aviso una vez.
- [ ] **Paso 2:** `npx vitest run src/shell` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** `npx vitest run`, `npm run lint`, `npm run build` → PASA.
- [ ] **Paso 5:** commits `test(front): nuevo proyecto y eleccion recordada (rojo)` / `feat(front): nuevo proyecto y eleccion
  recordada`.

## MP-3 · Presupuesto por partidas en la Hoja

### Tarea 8: Partidas a mano en el borrador (lógica)

**Archivos:**
- Crear: `aplicacion/hoja_partidas.py`
- Modificar: `aplicacion/hoja.py` (`Borrador` :334-361 gana `notas: Mapping[str, str] = field(default_factory=dict)`;
  `_cambios_de_cantidades` :1386 registra altas y bajas)
- Prueba: `tests/unit/test_hoja_partidas.py`

**Interfaces:**
```python
class CalculoInvalido(ValueError): ...
@dataclass(frozen=True) class PartidaElegida: codigo: str; descripcion: str; unidad: str; dominio: Dominio
def traducir_calculo(texto: str) -> str
def cantidad_y_regla(cantidad: str, calculo: str) -> tuple[Decimal, str | None]
def agregar_partida(borrador: Borrador, partida: PartidaElegida, *, cantidad: str, calculo: str, nota: str) -> tuple[Borrador, str]
def quitar_partida(borrador: Borrador, clave: str) -> Borrador
def texto_llano(descripcion: str) -> str
```
- `traducir_calculo`: admite cifras con la regla de `cifra_escrita`, `+ - * / ( )`, espacios y `×`/`x` como `*`; cada cifra se
  reescribe con punto decimal y sin miles. Otro carácter → `CalculoInvalido("El cálculo solo admite números y los signos + − × /
  y paréntesis.")`; una cifra mal escrita → `CalculoInvalido(MENSAJE_CIFRA)`.
- `cantidad_y_regla`: sin cálculo → `(cifra_escrita(cantidad), None)`; con cálculo, `v = evaluar(traducido, {})`; cantidad vacía →
  `v` cuantizado a 0,0001 (`ROUND_HALF_UP`, sin ceros a la derecha); escrita y `|v − c| > 0,001` (la tolerancia de R1,
  `core/verification/reglas.py:161`) → `CalculoInvalido(f"El cálculo da {texto_de_cifra(v)} y la cantidad es
  {texto_de_cifra(c)}: corrija uno de los dos.")`; la regla devuelta es el cálculo traducido.
- `agregar_partida`: agrega a `items_base` un `ItemComputo` `MANUAL` con `origen_id = f"a-mano:{n}"` (n = siguiente entero libre
  entre los `a-mano:` del borrador), `regla` y `parametros={}`; la nota va a `notas[clave]`; devuelve la clave
  (`f"{codigo}|a-mano:{n}"`).
- `quitar_partida`: solo claves de `items_base` (`HojaInvalida("Esa fila sale del espacio: cámbiela en «Espacio y metrajes».")`
  si sale del espacio); quita también su cantidad escrita y su nota.
- Cambios: un alta es `CambioEditado("cantidad", clave, "alta", "", <cantidad>)`; una baja `CambioEditado("cantidad", clave, "baja",
  <cantidad>, "")` (sin objeto nuevo en `OBJETOS`); nunca a la vez un cambio de cantidad para esa clave.
- `texto_llano`: si la descripción es la de R1 manual («la cantidad de X (Q U) es manual y no declara la regla…»,
  `reglas.py:175-187`) → «La cantidad de X (Q U) se escribió a mano sin cálculo: escriba cómo se obtuvo si quiere que Sílice la
  pueda verificar.»; si no, igual.

- [ ] **Paso 1: pruebas en rojo:** `traducir_calculo("2,5*4") == "2.5*4"`, `("6*3-2") == "6*3-2"`, `("1.234,5*2") == "1234.5*2"`,
  `("6 × 3") == "6*3"`; `"2.5*4"` y `"6*a"` levantan con sus textos; `cantidad_y_regla("", "6*3-2") == (Decimal("16"), "6*3-2")`;
  `cantidad_y_regla("", "10/3") == (Decimal("3.3333"), "10/3")`; `("15", "6*3-2")` levanta «El cálculo da 16 y la cantidad es 15:
  corrija uno de los dos.»; `("210", "")` → `(Decimal("210"), None)`; agregar OBRA-04 con «210» a un borrador vacío (fixture
  `tests/fixtures/hoja_borrador.py`) → clave `"OBRA-04|a-mano:1"` y `cambios_entre(base, nuevo) == [CambioEditado("cantidad",
  "OBRA-04|a-mano:1", "alta", "", "210")]`; agregarla dos veces → claves `…a-mano:1` y `…a-mano:2`; quitar la primera → baja con
  `"210"`; con el cálculo `"6*35"` el informe de `elaborar_borrador` **no** trae hallazgo de R1 para OBRA-04, y sin cálculo trae la
  advertencia cuyo `texto_llano` es el texto exacto de arriba.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_hoja_partidas.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden + `tests/unit/test_hoja*.py tests/unit/test_aplicacion_hoja*.py` → PASA.
- [ ] **Paso 5:** commits `test(hoja): partidas a mano con su calculo (rojo)` / `feat(hoja): agregar y quitar partidas del borrador`.

### Tarea 9: Rutas de la Hoja: agregar, quitar, notas y borrador en la moneda del proyecto

**Archivos:**
- Crear: `aplicacion/tablas_medicion.py`, `migraciones/caso/versions/caso_0011_mp_medicion.py`
- Modificar: `aplicacion/hoja_edicion.py` (`agregar`, `quitar`), `aplicacion/hoja_guardado.py:106` (guarda las notas con el código
  nuevo), `aplicacion/hoja.py` (`abrir_version` :1679 carga las notas), `aplicacion/hoja_vista.py` (`FilaDePresupuesto` :340 gana
  `nota`, `calculo`, `quitable`; `ResumenHoja` :69 gana `moneda` y `espacio_vacio`; `informe_de_auditoria` :745 aplica
  `texto_llano`), `api/rutas/hoja.py` (rutas nuevas; `:356` borrador en blanco con la moneda del proyecto y `lista_para_el_proyecto`),
  `api/esquemas_hoja.py`
- Prueba: `tests/unit/test_api_hoja_partidas.py`
- Compartidos: `METADATAS_CASO`, `TABLA`, `docs/api.json`

**Interfaces:**
- Tabla `mp_nota_medicion`: `id`, `proyecto_id Integer`, `version String(40)`, `clave String(200)`, `nota String(500)`.
- `def agregar(sesion, huella, id, rev, *, codigo: str, cantidad: str, calculo: str, nota: str) -> tuple[BorradorVivo, str]` y
  `def quitar(sesion, huella, id, rev, clave: str) -> BorradorVivo` (por `_cambiar`, `hoja_edicion.py:114`; la composición la
  completa `completar_composiciones` con `lista_para_el_proyecto`).
- `POST /v1/hoja/borradores/{id}/partidas` cuerpo `{rev, codigo, cantidad: "", calculo: "", nota: ""}` → 200 `{rev, resumen,
  clave}`; 404 «La partida «X» no está en el catálogo: compóngala primero en Componer.» (sin repetir otra cosa); 422 cifra/cálculo;
  409 `rev`. `POST /v1/hoja/borradores/{id}/partidas/quitar` cuerpo `{rev, clave}` → 200 `{rev, resumen}`. Acción `editar_hoja`.

- [ ] **Paso 1: pruebas en rojo** (patrón `tests/unit/test_api_hoja_edicion.py`, plantilla de carpeta en Bs con OBRA-04 en el
  catálogo):
  - proyecto nuevo en Bs sin versiones: `POST /borradores {proyecto}` → `resumen.moneda == "Bs"`, `espacio_vacio == true` (O-7);
  - agregar OBRA-04 con `cantidad:"210"`, `nota:"6 m × 35 m de muro"` → `vistas/presupuesto` trae la fila con cantidad `"210"`,
    `nota` y `quitable: true`; `cambios` dice 1; guardar la primera versión «VIV-001» → al abrir VIV-001 la nota sigue ahí;
  - `cantidad:"2.5"` → 422 con `MENSAJE_CIFRA`; `calculo:"6*3-2", cantidad:"15"` → 422 con el texto de la Tarea 8;
  - quitar una fila del espacio → 422 con el texto exacto; quitar la agregada → `cambios` vuelve a 0;
  - `vistas/auditoria` muestra el texto llano para una partida sin cálculo;
  - **foco 1:** proyecto en USD en carpeta Bs con tasa del BCV → la primera versión se guarda en USD y su lista es de alcance
    proyecto con la tasa; sin tasa de los últimos 7 días → 409 con el texto de la tasa y nada guardado.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_hoja_partidas.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden + `tests/unit/test_api_hoja*.py tests/unit/test_aplicacion_hoja*.py` → PASA.
- [ ] **Paso 5:** commits `test(api): agregar y quitar partidas en la hoja (rojo)` / `feat(api): agregar y quitar partidas en la
  hoja`.

### Tarea 10: Búsqueda de partidas y `CampoConBusqueda` (C-1)

**Archivos:**
- Crear: `aplicacion/busqueda.py`, `api/rutas/busqueda.py`, `frontend-desktop/src/comun/CampoConBusqueda.tsx`,
  `frontend-desktop/src/comun/logicaBusqueda.ts`
- Prueba: `tests/unit/test_busqueda_aplicacion.py`, `tests/unit/test_api_busqueda.py`, `src/comun/CampoConBusqueda.test.tsx`,
  `src/comun/logicaBusqueda.test.ts`
- Compartidos: `api/main.py`, `TABLA`, `docs/api.json`

**Interfaces:** exactamente el contrato del diseño de autocompletado: `GET /v1/buscar/partidas` (§5.1 reglas comunes, §5.2 orden por
relevancia, §5.4 forma de respuesta; acción `LEER_PROYECTO`); `def buscar_partidas(catalogo: Catalogo, q: str, dominio: Dominio |
None, limite: int) -> tuple[list[PartidaHallada], bool]`; el componente con las propiedades de §3.2 (modo `buscar` y `valorPropio`;
el modo local no hace falta aquí), comportamiento §3.3, «no lo encuentro» §3.5 y accesibilidad §3.6. Las demás rutas de `/v1/buscar`
quedan para el plan de autocompletado.

- [ ] **Paso 1: pruebas en rojo:** las filas de §8.1 que tocan `/partidas` (rango 0-4 con los ejemplos del diseño; `q` de 1 letra →
  200 vacío; `limite=8` con `hay_mas`; 422 sin eco; admin 403); el componente: pausa de 300 ms, flechas y Enter eligen, Esc
  cierra, la región `role="status"` solo con foco y siempre con texto, «Crear una partida nueva con el código «X»» al final.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_busqueda_aplicacion.py tests/unit/test_api_busqueda.py -q -W error` y
  `npx vitest run src/comun/CampoConBusqueda.test.tsx src/comun/logicaBusqueda.test.ts` → FALLAN.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** mismas órdenes, `npm run lint`, `npm run build` → PASAN.
- [ ] **Paso 5:** commits `test(busqueda): partidas del catalogo y campo con busqueda (rojo)` / `feat(busqueda): partidas del
  catalogo y campo con busqueda`.

### Tarea 11: La Hoja agrega y quita partidas y abre en Presupuesto

**Archivos:**
- Crear: `frontend-desktop/src/paginas/hoja/AgregarPartida.tsx` (+ `.test.tsx`)
- Modificar: `frontend-desktop/src/paginas/hoja/index.tsx:379` (pestaña inicial), `PestanaPresupuesto.tsx` (botón «Agregar
  partida», columna «Cómo se midió», «Quitar» con confirmación), `logica.ts` (`pestanaInicial`)
- Prueba: `src/paginas/hoja/AgregarPartida.test.tsx`, `src/paginas/hoja/logica.test.ts`

**Interfaces:** `export function pestanaInicial(resumen: { espacio_vacio: boolean }): number` → índice de «Presupuesto» (2) si
`espacio_vacio`, si no 0. «Agregar partida» abre un diálogo con `CampoConBusqueda` (Tarea 10), «Cantidad», «Cálculo (opcional)»
con ayuda «Por ejemplo 6*3-2 o 2,5*4», «Nota de medición (opcional)»; escribir el cálculo rellena la cantidad con su resultado al
salir del campo (`POST` de la Tarea 9 lo confirma); `valorPropio` = «Componer una partida nueva con el código «X»» que navega a
`/componer?codigo=X&volver=hoja`.

- [ ] **Paso 1: pruebas en rojo:** `pestanaInicial({espacio_vacio:true}) === 2`; la Hoja de un proyecto sin espacio abre con
  «Presupuesto» seleccionada; buscar «bloq», elegir OBRA-04, cantidad «210» → `POST …/partidas` con
  `{codigo:"OBRA-04", cantidad:"210", calculo:"", nota:""}` y la fila aparece; el 422 del cálculo se muestra junto al campo
  «Cálculo»; «Quitar» pide confirmación «¿Quitar OBRA-04 del presupuesto? Lo puede descartar antes de guardar.» y solo entonces
  llama `…/partidas/quitar`; el total dice «Bs»; la fila de espacio no tiene «Quitar».
- [ ] **Paso 2:** `npx vitest run src/paginas/hoja` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden, `npm run lint`, `npm run build` → PASA.
- [ ] **Paso 5:** commits `test(front): agregar y quitar partidas en la hoja (rojo)` / `feat(front): agregar y quitar partidas en
  la hoja`.

### Tarea 12: Elaborar lleva sus ítems a la Hoja

**Archivos:**
- Crear: `api/rutas/hoja_llevar.py`
- Modificar: `aplicacion/elaboracion.py:97` (`elaborar_desde_catalogo` gana `lista: models.ListaPrecios | None = None`;
  `api/rutas/presupuestos.py:735` le pasa `lista_para_el_proyecto`), `frontend-desktop/src/paginas/elaborar/index.tsx`
- Prueba: `tests/unit/test_api_hoja_llevar.py`, `src/paginas/elaborar/Llevar.test.tsx`
- Compartidos: `api/main.py`, `TABLA`, `docs/api.json`

**Interfaces:** `POST /v1/hoja/llevar` (`editar_hoja`) cuerpo `{proyecto, partidas: [{codigo, cantidad, calculo: ""}]}` → 200
`{borrador_id}`: usa el borrador vivo de esa ficha y proyecto o abre uno sobre la versión vigente (o en blanco), y agrega cada ítem
con `agregar` de la Tarea 9, todo o nada; no guarda versión. El front muestra «Llevar a la Hoja del proyecto» (solo con proyecto
elegido) y navega a `/hoja`.

- [ ] **Paso 1: pruebas en rojo:** llevar 2 ítems → el borrador tiene 2 altas y ninguna versión nueva; un código inexistente → 404
  y el borrador sin cambios (todo o nada); sin proyecto el botón no aparece; tras llevar se navega a `/hoja`.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_hoja_llevar.py -q -W error` y `npx vitest run src/paginas/elaborar`
  → FALLAN.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** mismas órdenes + `tests/integration/test_api_ola2_elaborar.py` → PASAN.
- [ ] **Paso 5:** commits `test(elaborar): llevar a la hoja del proyecto (rojo)` / `feat(elaborar): llevar a la hoja del proyecto`.

## MP-5 · Estudio de mercado

### Tarea 13: Observaciones, estadísticas, piso y propuesta (lógica)

**Archivos:**
- Crear: `aplicacion/tablas_mercado.py`, `aplicacion/mercado.py`, `migraciones/caso/versions/caso_0012_mp_mercado.py`
- Prueba: `tests/unit/test_mercado.py`, `tests/fixtures/mercado_ficticio.py`

**Interfaces:**
- Tablas: `mp_observacion` (`id`, `lado` `"compra"|"cobro"`, `codigo String(40)` del insumo o la partida, `fuente_tipo`
  `"proveedor"|"competidor"|"cotizacion"|"maprex"|"compra"`, `fuente String(200)`, `fecha Date`, `moneda String(10)`, `precio`,
  `nota String(500)`, `responsable`, `fecha_hora`, `anulada_por Integer null`); `mp_precio_objetivo` (`id`, `codigo_partida`,
  `precio`, `moneda`, `observaciones String(400)` (ids en JSON), `responsable`, `fecha_hora`; vale el último por partida).
- ```python
  @dataclass(frozen=True) class Estadisticas: moneda: str; n: int; minimo: Decimal|None; q1: Decimal|None; mediana: Decimal|None; promedio: Decimal|None; maximo: Decimal|None; ids: tuple[int, ...]; otras_monedas: int
  @dataclass(frozen=True) class Propuesta: precio: Decimal|None; razon: str; piso: Decimal|None
  def registrar_observacion(sesion, *, lado: str, codigo: str, fuente_tipo: str, fuente: str, fecha: date, precio: str, nota: str, responsable: str, ahora: datetime) -> int
  def estadisticas(sesion, *, lado: str, codigo: str, hoy: date, dias: int = 90) -> Estadisticas
  def piso_de_cobro(sesion, catalogo: Catalogo, codigo_partida: str, *, proyecto: str | None, fecha: date) -> tuple[Decimal, Decimal]  # (piso, precio_unitario)
  def propuesta(lado: str, est: Estadisticas, piso: Decimal | None) -> Propuesta
  def margen(objetivo: Decimal, precio_unitario: Decimal) -> Decimal   # porcentaje, 1 decimal HALF_UP
  ```
- Cuartiles: interpolación lineal tipo 7 (la de `CUARTIL.INC` de Excel: posición `(n−1)·p` sobre los ordenados). Mostrado: todo
  cuantizado a 0,01 `ROUND_HALF_UP`; las comparaciones con el piso, exactas. Ventana: `fecha >= hoy − dias`. La moneda es la de la
  carpeta; las de otra moneda solo se cuentan en `otras_monedas`. `precio` se lee con `cifra_escrita`; moneda = la de la carpeta.
- Piso: `calcular_apu(catalogo.composicion(codigo, fecha, lista_para_armar(...)), parametros)` → `con_administracion`; parámetros de
  la versión vigente del proyecto abierto (`_parametros_de_version`, `aplicacion/hoja.py:1624`) o `ParametrosCosto()`.
- Propuesta de compra: mediana, razón «Mediana de {n} observaciones; la más barata vista: {mínimo}.». De cobro: `q1` si `q1 >= piso`
  («Primer cuartil del mercado, por encima de su costo.»); si no, `piso` («La competencia cobra menos que su costo: se propone su
  costo.»); sin observaciones: `precio=None`, «Sin observaciones en los últimos {dias} días.».

- [ ] **Paso 1: pruebas en rojo** (`hoy = 2026-10-25`, datos ficticios en `tests/fixtures/mercado_ficticio.py`):
  - [100, 120, 130, 150, 200] Bs → n 5, mínimo 100, q1 120, mediana 130, promedio 140, máximo 200; compra → 130;
  - [10, 20] → q1 12,50, mediana 15; [50] → todo 50; [] → n 0, todo `None`, razón del texto exacto;
  - observación del 2026-07-27 entra y la del 2026-07-26 no (90 días); una en USD no entra y `otras_monedas == 1`;
  - cobro con piso 125 → 125 y la razón de «cobra menos que su costo»; con piso 110 → 120; **piso mayor que todo el mercado**
    (piso 250) → 250;
  - piso de un APU de costo directo 1.000,00 con parámetros por omisión → `(1150.00, 1265.00)`;
  - `margen(Decimal("1980.00"), Decimal("2074.44")) == Decimal("-4.6")`;
  - `precio="2.5"` → `CifraInvalida`.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_mercado.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden → PASA.
- [ ] **Paso 5:** commits `test(mercado): estadisticas, piso y propuesta (rojo)` / `feat(mercado): estadisticas, piso y propuesta`.

### Tarea 14: Rutas del estudio de mercado y «Usar este precio»

**Archivos:**
- Crear: `api/rutas/mercado.py`
- Modificar: `aplicacion/mercado.py` (`usar_precio_de_compra`, `usar_precio_de_cobro`, `apus_afectados`)
- Prueba: `tests/unit/test_api_mercado.py`
- Compartidos: `api/main.py`, `TABLA`, `docs/api.json`

**Interfaces:**
- `def apus_afectados(sesion, catalogo: Catalogo, codigo_insumo: str, fecha: date) -> list[str]` (partidas del catálogo cuya
  composición vigente usa ese insumo, ordenadas).
- `def usar_precio_de_compra(sesion, codigo_insumo: str, precio: str, *, observacion_id: int | None, fecha: date, responsable: str,
  ahora: datetime) -> models.ListaPrecios` — `lista_de_hoy(..., nueva_si_usada=True)`, cambia el `PrecioInsumo` del insumo en esa
  lista y su `PrecioOrigen.fuente` = «Estudio de mercado: observación n.º {id}».
- `def usar_precio_de_cobro(sesion, codigo_partida: str, precio: str, *, observaciones: Sequence[int], responsable, ahora) -> None`.
- Rutas (`prefix="/v1/mercado"`, `editar_hoja`): `GET /{lado}/{codigo}?dias=90` → `{estadisticas, propuesta, piso, precio_unitario,
  observaciones:[…]}`; `POST /observaciones` → 201 `{id}`; `POST /observaciones/{id}/anular` → 200; `GET /compra/{codigo}/afectados`
  → `{apus:[…]}`; `POST /compra/{codigo}/usar` `{precio, observacion_id}` → 200 `{lista}`; `POST /cobro/{codigo}/usar`
  `{precio, observaciones}` → 200; `GET /objetivos?partidas=A,B` → `{objetivos:[{codigo, precio, moneda}]}`.

- [ ] **Paso 1: pruebas en rojo:** registrar 3 observaciones y leer las estadísticas de la Tarea 13 por la API (montos como texto);
  `afectados` del cemento ficticio → `["OBRA-02", "OBRA-04"]`; `usar` 20,00 → la lista de hoy tiene 20 y la del 01/07 sigue con 18;
  con una versión guardada sobre la lista de hoy → se crea «… (2)» y la versión no cambia de total; `cobro/usar` y luego
  `objetivos?partidas=OBRA-04` → `"1980.00"`; rita → 403; una observación anulada sale de las estadísticas.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_mercado.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden → PASA.
- [ ] **Paso 5:** commits `test(api): estudio de mercado (rojo)` / `feat(api): estudio de mercado`.

### Tarea 15: Página «Estudio de mercado»

**Archivos:**
- Crear: `frontend-desktop/src/paginas/mercado/` (`index.tsx`, `logica.ts`, `mercado.scss`, pruebas)
- Compartidos: `rutas.ts` — página `{id:"mercado", titulo:"Estudio de mercado", enUnaLinea:"Compare precios del mercado y
  elija los suyos", seccion:"Trabajo", accion:"editar_hoja"}` en el área **Crear**, después de «Catálogo» (**decisión para
  Eugenio**: el diseño lo deja al constructor).

**Interfaces:** pestañas «Lo que compramos» / «Lo que cobramos»; buscador del insumo o partida; tabla de observaciones; franja de
estadísticas (n, mínimo, primer cuartil, mediana, promedio, máximo, cada una con «de {n} observaciones»); en cobro, «Su costo
(piso)» y «Precio con utilidad»; la propuesta con su razón; campo de precio prellenado con la propuesta; «Usar este precio» (en
compra, antes muestra «Cambiará el precio en {apus}» y pide confirmar); `useFormularioSucio("mercado", …)`.

- [ ] **Paso 1: pruebas en rojo:** con las respuestas de la Tarea 14 simuladas: las seis cifras en es-VE («140,00»); la razón de
  cobro debajo del piso; «Usar este precio» en compra muestra «Cambiará el precio en OBRA-02 y OBRA-04» y solo tras «Confirmar»
  llama `…/usar`; el precio se envía tal como se escribió («1.980,00»); un 422 se muestra en el campo; sin `Number()` sobre montos
  (prueba de fuente como `sinJergaInterna.test.ts`).
- [ ] **Paso 2:** `npx vitest run src/paginas/mercado` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden, `npm run lint`, `npm run build` → PASA.
- [ ] **Paso 5:** commits `test(front): estudio de mercado (rojo)` / `feat(front): estudio de mercado`.

### Tarea 16: Objetivo de mercado en la Hoja

**Archivos:**
- Crear: `frontend-desktop/src/paginas/hoja/ObjetivoDeMercado.tsx` (+ `.test.tsx`)
- Modificar: `PestanaPresupuesto.tsx` (columna nueva); `api/rutas/mercado.py`: `GET /v1/mercado/objetivos` acepta
  `pu=OBRA-04:2074.44,…` (los PU que la Hoja ya tiene, como texto) y devuelve también `margen` calculado con `margen()` de la
  Tarea 13 (el front no calcula)
- Prueba: `src/paginas/hoja/ObjetivoDeMercado.test.tsx`, una prueba más en `tests/unit/test_api_mercado.py`

- [ ] **Paso 1: pruebas en rojo:** la fila de OBRA-04 con PU 2.074,44 y objetivo 1.980,00 muestra «APU 2.074,44 · objetivo de
  mercado 1.980,00 · margen −4,6 %»; sin objetivo, la columna queda vacía; el margen negativo no usa solo el color (lleva el signo).
- [ ] **Paso 2:** `npx vitest run src/paginas/hoja/ObjetivoDeMercado.test.tsx` y la prueba de API ampliada → FALLAN.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** mismas órdenes → PASAN.
- [ ] **Paso 5:** commits `test(front): objetivo de mercado en la hoja (rojo)` / `feat(front): objetivo de mercado en la hoja`.

## MP-4 · Ciclo de aprobación

### Tarea 17: Envíos, dictámenes y rastro encadenado (lógica)

**Archivos:**
- Crear: `aplicacion/tablas_aprobacion.py`, `aplicacion/aprobaciones.py`, `migraciones/caso/versions/caso_0013_mp_aprobacion.py`
- Prueba: `tests/unit/test_aprobaciones.py`

**Interfaces:**
- Tabla `mp_aprobacion_evento` (solo inserción): `id`, `proyecto_id`, `tipo` `"envio"|"retiro"|"dictamen"`, `version String(40)`,
  `huella_version String(64)` (`EslabonVersion.huella_eslabon` de esa versión), `resultado String(30) null`
  (`"aprobada"|"aprobada_con_observaciones"|"devuelta"`), `notas String(2000)`, `usuario String(200)`, `fecha_hora`,
  `armo Boolean`, `cierre_de Integer null UNIQUE` (id del envío que cierra un retiro o dictamen), `anterior String(64)`,
  `huella String(64)`; `UNIQUE(proyecto_id, anterior)`.
- `huella` = SHA-256 de `json.dumps({anterior, tipo, proyecto_id, version, huella_version, resultado, notas, usuario,
  fecha_hora: isoformat, armo, cierre_de}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`; el primero
  encadena a `GENESIS`.
- ```python
  ESTADOS = ("guardada", "en_aprobacion", "retirada", "aprobada", "aprobada_con_observaciones", "devuelta")
  class AprobacionInvalida(ValueError): ...      # 409/422 con su mensaje
  def enviar(sesion, proyecto: str, version: str, *, nota: str, usuario: str, ahora: datetime) -> Envio   # Envio(id, retirada: str | None)
  def dictaminar(sesion, envio_id: int, *, resultado: str, notas: str, usuario: str, ahora: datetime) -> int
  def estados(sesion, proyecto: str) -> dict[str, EstadoDeVersion]   # EstadoDeVersion(estado, por, el, notas, armo)
  def historial(sesion, proyecto: str) -> list[EventoAprobacion]
  def verificar_rastro(sesion, proyecto: str) -> RastroVerificado     # (integro: bool, mensaje: str)
  def fases(sesion, proyecto: str) -> str                             # "VIV-001 devuelta → VIV-002 aprobada"
  def ultima_aprobada(sesion, proyecto: str) -> str | None
  ```
- Reglas: un solo envío pendiente por proyecto (enviar otra versión inserta un `retiro` de la pendiente y `Envio.retirada` la nombra);
  «La versión X ya está en aprobación.», «La versión X ya está aprobada.», «La versión X fue devuelta: corríjala en una versión
  nueva y envíe esa.»; notas obligatorias para `devuelta` y `aprobada_con_observaciones` («Escriba las notas: son obligatorias para
  devolver o aprobar con observaciones.»); `armo` = el usuario que dictamina es el de `EslabonVersion.usuario` de esa versión;
  dictaminar un envío ya cerrado → «Este envío ya tiene dictamen o fue retirado.».
- `verificar_rastro` recalcula cada huella y su encadenamiento y compara `huella_version` con el eslabón actual; mensajes «Rastro de
  aprobaciones íntegro.» / «El rastro de aprobaciones se rompió en el evento n.º {id}.».

- [ ] **Paso 1: pruebas en rojo** (proyecto ficticio con VIV-001 y VIV-002 guardadas, rastro con usuarios «Ana <ana>» y
  «Rita <rita>»):
  - enviar VIV-001 → `estados()["VIV-001"].estado == "en_aprobacion"`; enviar VIV-002 → VIV-001 `retirada` y `Envio.retirada ==
    "VIV-001"`;
  - devolver sin notas → `AprobacionInvalida` con el texto exacto; con notas → `devuelta`; reenviar VIV-001 devuelta → texto exacto;
  - **foco 3:** dos dictámenes sobre el mismo envío (segunda llamada tras la primera, y dos sesiones que leen el mismo `anterior`
    antes de escribir) → el segundo levanta «Este envío ya tiene dictamen o fue retirado.» y solo hay un evento `dictamen`;
  - Ana aprueba su propia VIV-002 → `armo is True` y `estados()["VIV-002"].armo is True`;
  - `fases` tras devolver VIV-001 y aprobar VIV-002 → `"VIV-001 devuelta → VIV-002 aprobada"`; `ultima_aprobada == "VIV-002"`;
  - alterar a mano `notas` de un evento en la base → `verificar_rastro` dice «…se rompió en el evento n.º {id}.».
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_aprobaciones.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar (insertar con el `anterior` leído en la misma transacción; `IntegrityError` → `AprobacionInvalida`).
- [ ] **Paso 4:** misma orden → PASA.
- [ ] **Paso 5:** commits `test(aprobacion): envios, dictamenes y rastro (rojo)` / `feat(aprobacion): envios, dictamenes y rastro`.

### Tarea 18: Rutas de aprobación, índice de la instalación y permiso

**Archivos:**
- Crear: `api/rutas/aprobaciones.py`, `aplicacion/indice_aprobaciones.py`, `aplicacion/tablas_indice_aprobacion.py`,
  `migraciones/instalacion/versions/ins_0005_mp_indice_aprobacion.py`
- Prueba: `tests/unit/test_api_aprobaciones.py`
- Compartidos: `seguridad/permisos.py` (`APROBAR_VERSION`), `MATRIZ`, listas literales de acciones, `ROLES`/`TABLA`,
  `METADATAS_INSTALACION`, pinos (→ `ins_0005_mp_indice_aprobacion`), `api/main.py`, `docs/api.json`

**Interfaces:**
- Tabla `mp_indice_aprobacion` (instalación): `id`, `caso String(255)`, `envio_id Integer`, `proyecto String(120)`,
  `version String(40)`, `total String(40)`, `moneda`, `estado`, `enviado_por`, `enviado_el`, `dictamen_por null`,
  `dictamen_el null`, `notas String(2000)`; `UNIQUE(caso, envio_id)`.
- `def reflejar(sesion_ins, caso: str, sesion_caso) -> None` (reescribe las filas de ese caso desde la carpeta);
  `def pendientes(sesion_ins) -> list[FilaIndice]`; `def de_quien(sesion_ins, usuario: str, limite: int = 20) -> list[FilaIndice]`.
- Rutas (`prefix="/v1/aprobaciones"`):
  - `POST ""` (`editar_hoja`) `{proyecto, version, nota}` → 201 `{id, estado, retirada}`.
  - `GET ""?proyecto=` (`editar_hoja`) → `{rastro:{integro, mensaje}, fases, versiones:{codigo: {estado, por, el, notas, armo}},
    eventos:[…]}`.
  - `GET /pendientes` (`aprobar_version`) → filas del índice con `estado="en_aprobacion"`, de todas las carpetas.
  - `GET /mias` (`editar_hoja`) → las 20 últimas filas del índice enviadas por la cuenta.
  - `POST /abrir` (`aprobar_version`) `{caso, envio_id}` → 200 `{caso}`: valida el caso (`resolver_caso`) y el envío, hace
    `caso_web.fijar` y `recordar_caso` (Tarea 5); 404 «No se encontró ese envío.».
  - `GET /{envio_id}` (`aprobar_version`) → `{proyecto, version, moneda, total, partidas:[{codigo, descripcion, unidad, cantidad,
    precio_unitario, total}], hallazgos:{error, advertencia, info, lista:[…]}, rastro, envio:{por, el, nota}, armo}` leído con
    `abrir_version`/`elaborar_borrador` sin registrar borrador.
  - `POST /{envio_id}/dictamen` (`aprobar_version`, solo sesión: con clave de API 403) `{resultado, notas}` → 201.
  - Todas: 409/422 con el mensaje de `AprobacionInvalida`; cada escritura refleja el índice después de confirmar la carpeta.

- [ ] **Paso 1: pruebas en rojo:** ana envía VIV-001; rita `GET /pendientes` la ve con `caso`; rita `POST /abrir` y después `GET
  /{id}` trae 6 partidas y el total como texto; rita devuelve con notas → ana `GET /mias` ve `estado: "devuelta"` y las notas;
  **foco 3:** tras `olvidar_todo()` + `cerrar_motores()` ana sigue viendo la devolución en `/mias` y en `GET ""?proyecto=`; dos
  `POST /dictamen` sobre el mismo envío → 201 y 409; admin → 403 en `/pendientes`; rita → 403 en `POST ""`; borrar a mano la fila del
  índice y pedir `/pendientes` con la carpeta abierta la repone; ana aprueba la suya → `armo: true`.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_aprobaciones.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden + `tests/unit/test_permisos.py tests/unit/test_api_acceso_por_ruta.py` (con lo compartido aplicado)
  → PASA.
- [ ] **Paso 5:** commits `test(api): ciclo de aprobacion (rojo)` / `feat(api): ciclo de aprobacion`.

### Tarea 19: Enviar desde la Hoja y el dictamen de vuelta en el Inicio

**Archivos:**
- Crear: `frontend-desktop/src/paginas/hoja/AprobacionDeVersion.tsx` (+ prueba), `src/paginas/inicio/Aprobaciones.tsx` (+ prueba)
- Modificar: `src/paginas/hoja/index.tsx` (monta la etiqueta y los botones junto a la versión), `src/paginas/inicio/index.tsx`

**Interfaces:** etiqueta «Guardada» / «En aprobación» / «Aprobada · Rita · 25/10/2026» / «Aprobada con observaciones · …» /
«Devuelta · …» (más «aprobada por quien la armó» si `armo`); «Enviar a aprobación…» (versión guardada, sin envío abierto ni
aprobada) con nota opcional; si fue devuelta, las notas y «Hacer una versión nueva a partir de esta» (abre el borrador de esa versión
en «Presupuesto» con el aviso «Corrija y guarde: será una versión nueva.»). Inicio: «Por aprobar» (con `aprobar_version`) y «Mis
versiones en aprobación» (con `editar_hoja`), cada fila con proyecto, versión, total, quién, cuándo.

- [ ] **Paso 1: pruebas en rojo:** las cinco etiquetas exactas; enviar llama `POST /v1/aprobaciones` y la etiqueta pasa a «En
  aprobación»; con `retirada` se avisa «Se retiró VIV-001 de la aprobación.»; **foco 3:** ana con `/mias` devuelta ve las notas en el
  Inicio; **foco 2:** «Abrir» en «Por aprobar» de otra carpeta con un borrador con cambios pide la confirmación de la Tarea 6 antes de
  `POST /abrir`; rita no ve «Mis versiones en aprobación»; abrir VIV-001 «En aprobación», cambiar una cantidad y guardar crea
  VIV-002 y VIV-001 sigue «En aprobación» (la versión enviada no se edita).
- [ ] **Paso 2:** `npx vitest run src/paginas/hoja src/paginas/inicio` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden, `npm run lint`, `npm run build` → PASA.
- [ ] **Paso 5:** commits `test(front): enviar a aprobacion y dictamen de vuelta (rojo)` / `feat(front): enviar a aprobacion y
  dictamen de vuelta`.

### Tarea 20: Página «Aprobar», y la aprobada manda en Entregar, Control y Trazabilidad

**Archivos:**
- Crear: `frontend-desktop/src/paginas/aprobar/` (`index.tsx` con `?envio=`; tabla de partidas, hallazgos con `InformeAuditoria`,
  panel «Dictamen»)
- Modificar: `src/paginas/entregar/index.tsx:124-127` (por omisión la última aprobada; aviso si no lo está),
  `api/rutas/entregas.py:123-128` (cada versión con `aprobacion: estado|null`), `src/paginas/control/PestanaLineaBase.tsx`
  (propone la aprobada), `src/paginas/hoja/PestanaTrazabilidad.tsx` (fases y rastro)
- Prueba: `src/paginas/aprobar/Aprobar.test.tsx`, ajustes en `Entregar.test.tsx`, `Control.test.tsx`, pruebas de Trazabilidad;
  `tests/unit/test_api_entregas.py`
- Compartidos: `rutas.ts` — `{id:"aprobar", titulo:"Aprobar una versión", enUnaLinea:"Revise y dé su dictamen sobre una versión",
  accion:"aprobar_version"}` en el área **Auditar**

- [ ] **Paso 1: pruebas en rojo:** «Devuelta» y «Aprobada con observaciones» sin notas no se envían y dicen el texto de la Tarea 17;
  el panel no tiene campos de edición de la versión (solo lectura); si `armo`, el panel dice «Usted armó esta versión: el dictamen
  quedará rotulado así.»; Entregar con VIV-001 devuelta y VIV-002 aprobada elige VIV-002; elegir VIV-001 muestra «Esta versión no está
  aprobada.»; Control propone VIV-002 como línea base; Trazabilidad muestra «VIV-001 devuelta → VIV-002 aprobada» y «Rastro de
  aprobaciones íntegro.»; `GET /v1/entregas/versiones` trae `aprobacion`.
- [ ] **Paso 2:** `npx vitest run src/paginas/aprobar src/paginas/entregar src/paginas/control src/paginas/hoja` y
  `uv run --active pytest tests/unit/test_api_entregas.py -q -W error` → FALLAN.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** mismas órdenes, `npm run lint`, `npm run build` → PASAN.
- [ ] **Paso 5:** commits `test(front): aprobar y la aprobada manda (rojo)` / `feat(front): aprobar y la aprobada manda`.

## MP-7 · Retrasos y crisis

### Tarea 21: Plan desde los rendimientos

**Archivos:**
- Crear: `aplicacion/plan_rendimientos.py`, `tests/fixtures/obra_vivienda.py` (los 6 APU ficticios OBRA-01..06 con sus
  rendimientos 4,5 / 6 / 250 / 12 / 18 / 60 y cantidades 18 / 12 / 950 / 210 / 420 / 420)
- Modificar: `aplicacion/hoja.py:1983-1984` (`crear_primera_version` propone `plan_por_rendimientos`), `aplicacion/hoja_edicion.py`
  (`plan_desde_rendimientos`), `api/rutas/hoja.py` (`POST /v1/hoja/borradores/{id}/plan/rendimientos`),
  `frontend-desktop/src/paginas/hoja/PestanaPlan.tsx` (botón «Plan desde los rendimientos» con cuadrillas por partida, marca «en
  paralelo con la anterior» y «Días hábiles / Semanas»)
- Prueba: `tests/unit/test_plan_rendimientos.py`, `src/paginas/hoja/PlanRendimientos.test.tsx`

**Interfaces:**
```python
@dataclass(frozen=True) class Duracion: codigo: str; dias: Decimal; aviso: str
def duraciones(items: Sequence[ItemComputo], composiciones: Mapping[str, ComposicionAPU], cuadrillas: Mapping[str, int]) -> list[Duracion]
def plan_por_rendimientos(duraciones: Sequence[Duracion], *, paralelas: Collection[str] = (), unidad: Literal["dia", "semana"] = "dia") -> list[PeriodoPlan]
def paralelas_del_plan(plan: Sequence[PeriodoPlan]) -> frozenset[str]
```
- Duración = cantidad ÷ rendimiento ÷ cuadrillas, hacia arriba al medio día; sin composición o rendimiento → 1 día y aviso «{código}
  no tiene rendimiento: se le asignó 1 día.»; cantidad 0 → 0 días y la partida no entra al plan (aviso «{código} tiene cantidad 0.»).
- Encadenado en el orden del presupuesto; una partida en `paralelas` empieza donde empezó la anterior; la siguiente no paralela
  empieza en el mayor fin alcanzado. Fracción de un período = días de la partida dentro del período ÷ duración, cuantizada a
  0,000001 `ROUND_HALF_UP`; el último período de la partida absorbe el residuo para sumar exactamente 1. Etiquetas
  `FORMATO_PERIODO` (`core/budget/curva.py:30`) en días; «Semana {n}» con 5 días hábiles por período.
- `paralelas_del_plan`: partidas cuyo primer período activo coincide con el de una anterior (lo usa la Tarea 27).
- Ruta: cuerpo `{rev, cuadrillas: {codigo: "1"}, paralelas: [codigo], unidad: "dia"|"semana"}` → `EdicionPlanRespuesta` + `avisos`.

- [ ] **Paso 1: pruebas en rojo** (con `obra_vivienda`): duraciones `[4, 2, 4, 17.5, 23.5, 7]`; plan secuencial de 58 períodos
  «Dia 1»…«Dia 58»; OBRA-01 con 0,25 en Dia 1-4; OBRA-05 con 0,021277 en Dia 28, 0,042553 en Dia 29 y 0,042557 en Dia 51, y su suma
  exactamente 1; con OBRA-03 en paralelo → 56 períodos y OBRA-03 empieza en Dia 5; OBRA-04 con 2 cuadrillas → 8,75 → 9 días;
  **foco 4:** una partida sin composición → 1 día y el aviso exacto, otra con cantidad 0 → fuera del plan y el plan pasa
  `plan_desde_filas` (cada partida suma 1); en semanas, OBRA-01 (4 días) cae entera en «Semana 1» con 1; `crear_primera_version` sin
  plan guarda el de rendimientos (58 períodos). Front: el botón envía `{cuadrillas, paralelas, unidad}` y muestra los avisos.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_plan_rendimientos.py -q -W error -p no:cacheprovider` y
  `npx vitest run src/paginas/hoja/PlanRendimientos.test.tsx` → FALLAN.
- [ ] **Paso 3:** implementar; correr `tests/unit/test_hoja*.py tests/unit/test_aplicacion_hoja*.py tests/unit/test_api_hoja*.py
  tests/integration/test_hoja*.py` y rehacer **a mano** los oráculos que suponían una partida por día en la primera versión (choque
  10), listándolos en el informe.
- [ ] **Paso 4:** todas las órdenes anteriores, `npm run lint`, `npm run build` → PASAN.
- [ ] **Paso 5:** commits `test(plan): plan desde los rendimientos (rojo)` / `feat(plan): plan desde los rendimientos`.

### Tarea 22: Causas de retraso y atraso por partida

**Archivos:**
- Crear: `aplicacion/tablas_causas.py`, `aplicacion/causas.py`, `migraciones/caso/versions/caso_0014_mp_causas.py`
- Modificar: `aplicacion/control.py:307` (`registrar_y_controlar` guarda las causas en la misma transacción), `api/rutas/control.py`
  (`LineaDeValuacion` gana `causa`; `CalculoRespuesta` gana `atrasos`), `frontend-desktop/src/paginas/control/PestanaValuaciones.tsx`
  (selector de causa por línea), `PestanasDeResultados.tsx` (tabla «Atraso por partida» en «Alertas y reproyección»), `logica.ts`
- Prueba: `tests/unit/test_causas.py`, `tests/unit/test_api_control_causas.py`, `src/paginas/control/Causas.test.tsx`

**Interfaces:**
- `CAUSAS = {"compra_tardia": "Compra tardía", "precio": "Precio", "clima": "Lluvia o clima", "cambio_cliente": "Cambio del cliente",
  "falta_personal": "Falta de personal", "falla_equipo": "Falla de equipo", "otra": "Otra"}`.
- Tabla `mp_causa_retraso`: `id`, `valuacion_id`, `codigo_partida`, `causa`, `fecha_hora` (solo inserción; la de una valuación
  anulada no cuenta).
- `@dataclass(frozen=True) class Atraso: codigo: str; dias: int; causa: str | None; texto: str`;
  `def atrasos(sesion, resultado: ResultadoControl) -> list[Atraso]`: por partida con `fin`, `dias = ceil(fin − fin_plan)` con
  `fin_plan` = último período con fracción > 0 × `dias_por_periodo`; solo `dias > 0`; causa = la última declarada para esa partida;
  texto «{código} atrasada {n} días: {causa}» («1 día» en singular; «sin causa declarada» si no hay).

- [ ] **Paso 1: pruebas en rojo:** obra de dos partidas con el plan de la Tarea 21 (A: 10 m³ a 2 m³/día = 5 días, días hábiles,
  inicio 2026-11-02), corte al día 5 con A ejecutada en 5 m³ y causa `compra_tardia` → SPI 0,5, `Atraso("A", 5, "compra_tardia",
  "A atrasada 5 días: Compra tardía")` (`fin` = 10 calculado a mano con `valor_ganado.py:623-697`); **foco 4:** con la vivienda y el
  concreto (OBRA-02) al 50 % al fin de su plan, los indicadores dicen SPI < 1 y la tabla nombra OBRA-02; una causa de una valuación
  anulada no aparece; la API acepta `causa` nula y rechaza una desconocida con 422 sin eco; el front envía `causa` por línea y pinta el
  texto de cada atraso.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_causas.py tests/unit/test_api_control_causas.py -q -W error` y
  `npx vitest run src/paginas/control` → FALLAN.
- [ ] **Paso 3:** implementar; `tests/unit/test_api_control.py tests/integration/test_control.py` siguen verdes.
- [ ] **Paso 4:** todas las órdenes, `npm run lint`, `npm run build` → PASAN.
- [ ] **Paso 5:** commits `test(control): causas y atraso por partida (rojo)` / `feat(control): causas y atraso por partida`.

### Tarea 23: Procura con fechas, compras y alertas (backend)

**Archivos:**
- Crear: `aplicacion/tablas_procura.py`, `aplicacion/procura.py`, `api/rutas/procura.py`,
  `migraciones/caso/versions/caso_0015_mp_procura.py`
- Prueba: `tests/unit/test_procura.py`, `tests/unit/test_api_procura.py`
- Compartidos: `api/main.py`, `TABLA` (acción `control_de_obra`), `docs/api.json`

**Interfaces:**
- Tablas: `mp_plazo_entrega` (`proyecto_id`, `descripcion_insumo`, `unidad`, `dias Integer`; PK compuesta); `mp_compra` (`id`,
  `proyecto_id`, `descripcion_insumo`, `unidad`, `evento` `"pedida"|"recibida"`, `fecha`, `cantidad null`, `precio null`, `moneda
  null`, `responsable`, `fecha_hora`; solo inserción).
- ```python
  @dataclass(frozen=True) class NecesidadDeInsumo: descripcion: str; unidad: str; cantidad: Decimal; partidas: tuple[str, ...]; se_necesita: date | None; pedir_a_mas_tardar: date | None; plazo: int; pedida: date | None; recibida: date | None
  @dataclass(frozen=True) class AlertaDeCompra: severidad: str; texto: str
  def explosion(sesion, proyecto: str, version: str) -> list[NecesidadDeInsumo]
  def alertas_de_compra(necesidades: Sequence[NecesidadDeInsumo], corte: date, feriados: Collection[date]) -> list[AlertaDeCompra]
  def causa_sugerida(sesion, proyecto: str, codigo_partida: str, hasta: date) -> str | None
  def registrar_compra(sesion, proyecto: str, *, descripcion: str, unidad: str, evento: str, fecha: date, cantidad: str = "", precio: str = "", responsable: str, ahora: datetime) -> None
  ```
- Explosión: solo materiales de `linea_composicion_version` de la versión de la línea base, Σ cantidad de la partida × cantidad de
  la línea, agrupado por (descripción, unidad). `se_necesita` = fecha del primer período activo de la primera partida que lo usa
  (`dia_habil(inicio, n, feriados)`, `core/budget/calendario.py:42`, con el calendario de la línea base); `pedir_a_mas_tardar` =
  `se_necesita` menos `plazo` días hábiles (3 por omisión). Sin línea base: fechas `None` y la ruta lo dice («Declare la línea base
  para calcular las fechas de compra.»).
- Alertas: sin pedir y `corte` entre `pedir_a_mas_tardar − 2` y `pedir_a_mas_tardar − 1` días hábiles → `AVISO` «Pida {insumo} antes
  del {dd/mm/aaaa}.»; sin pedir y `corte >= pedir_a_mas_tardar` → `ERROR` «{insumo} no está pedido y debía pedirse el {dd/mm/aaaa}.»;
  recibida después de `se_necesita` → `ERROR` «Compra tardía: {insumo} llegó el {…} y se necesitaba el {…}.».
- La recepción con precio registra también una observación de mercado (`lado="compra"`, `fuente_tipo="compra"`, Tarea 13).
- Rutas (`prefix="/v1/procura"`, `control_de_obra`): `GET ?proyecto=&corte=` → `{necesidades, alertas, aviso}`;
  `POST /compras`; `PUT /plazos` `{descripcion, unidad, dias}`.

- [ ] **Paso 1: pruebas en rojo** (vivienda con línea base desde el lunes 2026-11-02, días hábiles): el cemento de OBRA-02
  (sacos por m³ ficticios de la fixture × 12 m³) da la cantidad calculada a mano; `se_necesita` = 2026-11-06 (OBRA-02 empieza el día 5);
  `pedir_a_mas_tardar` = 2026-11-03; **foco 5:** corte 2026-11-02 sin pedir → AVISO con «antes del 03/11/2026»; corte 2026-11-03 →
  ERROR; pedida el 2026-11-02 → sin alerta; recibida el 2026-11-09 → «Compra tardía: …» y `causa_sugerida(…, "OBRA-02", …) ==
  "compra_tardia"`; con feriado el 2026-11-04 `se_necesita` pasa al 2026-11-09 y `pedir_a_mas_tardar` al 2026-11-03; equipos y mano de
  obra no aparecen; la recepción con precio «20,00» crea una observación de compra.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_procura.py tests/unit/test_api_procura.py -q -W error` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden → PASA.
- [ ] **Paso 5:** commits `test(procura): necesidades, compras y alertas (rojo)` / `feat(procura): necesidades, compras y alertas`.

### Tarea 24: Pestaña «Procura» en Control de obra

**Archivos:**
- Crear: `frontend-desktop/src/paginas/control/PestanaProcura.tsx` (+ `.test.tsx`)
- Modificar: `control/logica.ts:257` (`PESTANAS` gana «Procura» después de «Valuaciones»), `control/index.tsx`,
  `PestanaValuaciones.tsx` (prellena la causa con `causa_sugerida`)

- [ ] **Paso 1: pruebas en rojo:** tabla de necesidades (insumo, cantidad, partidas, se necesita, pedir a más tardar, pedida,
  recibida) con fechas `dd/mm/aaaa`; alertas con severidad por texto e ícono (no solo color); «Pedida hoy» y «Recibida…» (fecha,
  cantidad, precio en es-VE) llaman `POST /v1/procura/compras`; el plazo editable llama `PUT /plazos`; en Valuaciones, OBRA-02 llega con
  «Compra tardía» elegida si la API la sugiere.
- [ ] **Paso 2:** `npx vitest run src/paginas/control` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden, `npm run lint`, `npm run build` → PASA.
- [ ] **Paso 5:** commits `test(front): procura en control de obra (rojo)` / `feat(front): procura en control de obra`.

### Tarea 25: Precio nuevo como precio del corte

**Archivos:**
- Crear: `aplicacion/precios_declarados.py`, `aplicacion/tablas_corte.py`, `migraciones/caso/versions/caso_0016_mp_corte.py`
- Modificar: `aplicacion/control.py:407-449` (`METODO_DECLARADOS = "Precios declarados de insumos"`; `precios_del_corte` lo
  atiende), `api/rutas/control.py:93-102` (método nuevo; **la perspectiva sale de la línea base**, no `"costo"` fijo),
  `api/rutas/mercado.py` y `api/rutas/procura.py` (casilla «Declararlo precio del corte»), `control/PestanasDeResultados.tsx`
  (`BarraDeCorte` con el método nuevo), `paginas/mercado/index.tsx`, `control/PestanaProcura.tsx`
- Prueba: `tests/unit/test_precios_declarados.py`, `tests/unit/test_api_control_declarados.py`, pruebas de front tocadas

**Interfaces:**
- Tabla `mp_precio_corte`: `id`, `proyecto_id`, `descripcion_insumo`, `unidad`, `precio`, `moneda`, `fecha`, `fuente String(300)`,
  `responsable`, `fecha_hora` (solo inserción).
- `def declarar_precio_del_corte(sesion, proyecto: str, *, descripcion: str, unidad: str, precio: Decimal, fecha: date, fuente: str,
  responsable: str, ahora: datetime) -> None`;
  `def precios_declarados(sesion, proyecto: str, catalogo: Catalogo, corte: date, perspectiva: str) -> PreciosDelCorte | None`:
  por partida de la línea base, su composición congelada con los precios de los materiales sustituidos por el último declarado con
  `fecha <= corte` (mismas descripción y unidad), `calcular_apu` con los parámetros de esa versión → `costo_directo` (perspectiva
  costo) o `precio_unitario`; `PreciosDelCorte("declarados", "Precios declarados al {dd/mm/aaaa}: {n} insumos", unitarios)`;
  sin precios declarados → `None`.

- [ ] **Paso 1: pruebas en rojo:** fixture de Control `tests/fixtures/control_ob_s2.py` + un material declarado de 18 a 20: el
  unitario de la partida que lo usa sube en (20 − 18) × cantidad del material (calculado a mano) y las demás no cambian; con
  `metodo=declarados` el cálculo ya **no** dice «sin precios del corte» y la separación trae desvío de precio > 0; un declarado con
  fecha posterior al corte no cuenta; con línea base de perspectiva «precio» la ruta usa `precio_unitario` (antes usaba costo:
  prueba del defecto); desde Estudio de mercado y desde la recepción de una compra la casilla declara el precio.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_precios_declarados.py tests/unit/test_api_control_declarados.py -q -W
  error` y `npx vitest run src/paginas/control src/paginas/mercado` → FALLAN.
- [ ] **Paso 3:** implementar; `tests/unit/test_api_control.py` sigue verde.
- [ ] **Paso 4:** todas las órdenes, `npm run lint`, `npm run build` → PASAN.
- [ ] **Paso 5:** commits `test(control): precio declarado del corte (rojo)` / `feat(control): precio declarado del corte`.

### Tarea 26: Agregar y quitar líneas del APU de la versión

**Archivos:**
- Crear: `aplicacion/hoja_lineas_apu.py`
- Modificar: `aplicacion/hoja.py:1309-1336` (`_cambios_de_apu` registra `CambioEditado("apu", f"{partida}|{tipo}|{n}", "alta"|"baja",
  …)` en lugar de perder las líneas con `zip(strict=False)`), `aplicacion/hoja.py:944-948` (el mensaje «use Componer» ya no aplica a
  esta ruta), `aplicacion/hoja_edicion.py`, `api/rutas/hoja.py` (rutas nuevas), `frontend-desktop/src/paginas/hoja/PestanaApu.tsx`
  («Agregar línea» con `CampoConBusqueda` en modo `buscar` sobre la ruta existente
  `GET /v1/hoja/borradores/{id}/insumos?tipo=&texto=&limite=`, más `valorPropio` «Insumo nuevo «X»» que pide unidad y precio;
  «Quitar» por línea), `aplicacion/control.py` y
  `control/PestanasDeResultados.tsx` («Antes y después» de la partida cambiada)
- Prueba: `tests/unit/test_hoja_lineas_apu.py`, `tests/unit/test_api_hoja_lineas_apu.py`, `src/paginas/hoja/LineasApu.test.tsx`

**Interfaces:**
- `def agregar_linea(composicion: ComposicionAPU, tipo: str, *, descripcion: str, unidad: str, cantidad: Decimal, precio: Decimal,
  depreciacion: Decimal | None = None, modalidad: str | None = None) -> ComposicionAPU`;
  `def quitar_linea(composicion: ComposicionAPU, tipo: str, indice: int) -> ComposicionAPU` (no deja un APU sin líneas:
  «Un APU necesita al menos una línea.»).
- `POST /v1/hoja/borradores/{id}/apu/{partida:path}/lineas` `{rev, tipo, insumo: codigo|"" , descripcion, unidad, cantidad, precio}`
  (insumo del catálogo con su precio de la lista de la versión, o uno nuevo con su precio tecleado) y `POST …/lineas/quitar`
  `{rev, tipo, indice}` → `EdicionApuRespuesta`.
- `def antes_y_despues(sesion, proyecto: str, catalogo: Catalogo, version_nueva: str) -> list[dict[str, str]]`: por partida cuya
  composición cambió respecto de la línea base: costo unitario, duración (Tarea 21), y el efecto en término y punto de equilibrio
  (`equilibrio_proyectado`, núcleo, sin tocarlo).

- [ ] **Paso 1: pruebas en rojo:** agregar «Concreto premezclado» (m³, 1,05, 95,00) a OBRA-02 → el costo directo sube en 99,75 por
  m³ (a mano) y `cambios` trae `CambioEditado("apu", "OBRA-02|material|5", "alta", "", "Concreto premezclado")`; guardar crea la
  versión nueva con la línea en `linea_composicion_version` (`insumo_id` nulo si es nuevo); quitar la última línea de un APU de una
  línea → 422 con el texto; el 422 de cifra; Control muestra «Antes y después» de OBRA-02 con costo y duración; front: agregar y quitar
  líneas llaman sus rutas y el borrador cuenta los cambios.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_hoja_lineas_apu.py tests/unit/test_api_hoja_lineas_apu.py -q -W error` y
  `npx vitest run src/paginas/hoja src/paginas/control` → FALLAN.
- [ ] **Paso 3:** implementar; `tests/unit/test_api_hoja_apu_retomar.py tests/unit/test_aplicacion_hoja_apu.py` siguen verdes
  (el mensaje viejo de `_cantidades_de_tabla` se conserva para la edición de cantidades).
- [ ] **Paso 4:** todas las órdenes, `npm run lint`, `npm run build` → PASAN.
- [ ] **Paso 5:** commits `test(hoja): lineas del apu de la version (rojo)` / `feat(hoja): agregar y quitar lineas del apu de la
  version`.

### Tarea 27: Recuperación con el plan real

**Archivos:**
- Modificar: `aplicacion/control.py:470-491` (`calcular_las_opciones` pasa `independientes` a `contexto_de_recuperacion`; por
  omisión `paralelas_del_plan` del plan de la línea base), `api/rutas/control.py` (`PeticionOpciones` gana `independientes:
  list[str]`), `control/PestanasDeResultados.tsx` (`Recuperacion` prellena las independientes y deja cambiarlas)
- Prueba: `tests/unit/test_api_control_recuperacion_plan.py`, ajuste en `src/paginas/control/Control.test.tsx`

- [ ] **Paso 1: pruebas en rojo:** con la vivienda (plan con OBRA-03 en paralelo) y el atraso de la Tarea 22, la opción «paralelo»
  existe y nombra OBRA-03; sin paralelas declaradas la opción dice que no hay partidas independientes (texto del núcleo); la
  petición con `independientes:["OBRA-05"]` llega al contexto (prueba del defecto: antes se perdía); las cuatro opciones usan el
  término del plan por rendimientos (58 días), no el de una partida por día.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_control_recuperacion_plan.py -q -W error` y
  `npx vitest run src/paginas/control` → FALLAN.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** mismas órdenes + `tests/unit/test_api_control.py tests/unit/test_recuperacion.py` → PASAN.
- [ ] **Paso 5:** commits `test(control): recuperacion con el plan real (rojo)` / `feat(control): recuperacion con el plan real`.

## MP-6 · La obra sin atajos

### Tarea 28: Recorrido versionado de la vivienda en Bs

**Archivos:**
- Crear: `scripts/recorrido_obra.py`, `tests/unit/test_recorrido_obra_sin_atajos.py`, `docs/bitacora/2026-10-2x-recorrido-obra.md`
- Fuente: los pasos de `C:\Users\euger\AppData\Local\Temp\claude\c--Users-euger-OneDrive-Escritorio-TESIS\298dcfa1-29b1-4c95-862b-61cb68185a76\scratchpad\obra_vivo\pasos\*.py`
  (se descartan `atajo_*.py`; los demás se reescriben contra la interfaz nueva) y `obra_vivo/partidas.json` vía
  `tests/fixtures/obra_vivienda.py`

**Interfaces:** reutiliza de `scripts/recorrido_ux_playwright.py` `sembrar_datos`, `congelar_interfaz`, `ServidorCongelado`,
`lanzar_navegador`, `entrar`, `puerto_libre`; `uv run --active --with playwright python -u scripts/recorrido_obra.py --salida <dir>
[--visible] [--lento-ms 40]`; escribe `<dir>/resultado.json` (`[{paso, cuenta, ok, detalle, captura}]`) y una captura por paso; sale
con código 1 si un paso falla. La única siembra es la de `sembrar_datos` (cuentas); todo lo demás por la interfaz.

- [ ] **Paso 1: prueba en rojo** `test_recorrido_obra_sin_atajos.py`: el archivo existe; su fuente no contiene `fetch(`,
  `page.request`, `APIRequestContext`, `requests.`, `httpx`, `sqlite3`, `create_engine` ni un literal que empiece por `"/v1/"` o
  `"/presupuestos"`; declara los pasos en este orden exacto: `admin_clave_firma`, `ana_carpeta_bs`, `ana_lista_maprex`,
  `ana_mercado_3_insumos_1_partida`, `ana_componer_6_apu`, `ana_nuevo_proyecto_bs`, `ana_agregar_6_partidas`, `ana_plan_rendimientos`,
  `ana_guardar_viv001`, `ana_enviar_viv001`, `rita_devuelve_con_notas`, `ana_ve_devuelta`, `ana_corrige_viv002`, `ana_enviar_viv002`,
  `rita_aprueba`, `ana_entrega_aprobada`, `ana_linea_base`, `ana_procura_cemento_tarde`, `ana_valuacion_concreto_atrasado`,
  `ana_precio_cemento_al_corte`, `ana_apu_premezclado_viv003`, `ana_recuperacion`.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_recorrido_obra_sin_atajos.py -q -W error` → FALLA.
- [ ] **Paso 3:** escribir el recorrido. Comprobaciones por paso (visibles en pantalla): PU de cada APU igual a `PU_ESPERADO` de
  `scratchpad/video/grabar.py` en es-VE («2.074,44 Bs»; en la bitácora, OBRA-04 recalculado a mano); total de VIV-001 igual a la suma
  de sus filas y a menos de 10,15 Bs de 1.238.375,28 Bs (redondeo de los PU a céntimos, Σ cantidades 2.030); VIV-002 = VIV-001 +
  31.116,60 Bs (bloques 210 → 225); «Devuelta» con las notas en el Inicio de Ana; «Aprobada · Rita» en la Hoja; Entregar propone
  VIV-002; la línea base propone VIV-002; Procura avisa el cemento; Alertas dice «OBRA-02 atrasada … : Compra tardía» y la franja no
  dice «adelantada»; el valor ganado separa desvío de precio; VIV-003 trae la línea «Concreto premezclado»; Recuperación lista cuatro
  opciones.
- [ ] **Paso 4:** correr el recorrido completo → `resultado.json` con los 22 pasos `ok: true`; correr también
  `scripts/recorrido_ux_playwright.py` (visual) y `--funcional` → sin regresiones frente a sus bitácoras.
- [ ] **Paso 5:** commits `test(recorrido): la obra sin atajos (rojo)` / `feat(recorrido): la vivienda de 80 m2 en Bs sin atajos`;
  bitácora con las cifras y la hora de cada paso.

### Tarea 29: Video, manual y cierre

**Archivos:**
- Modificar fuera del repositorio: `C:\Users\euger\AppData\Local\Temp\claude\c--Users-euger-OneDrive-Escritorio-TESIS\298dcfa1-29b1-4c95-862b-61cb68185a76\scratchpad\video\grabar.py`
  (lo deja el agente de video: debe llamar a los pasos de `scripts/recorrido_obra.py` con `--visible --lento-ms 40` y sus rótulos, sin
  sus dos atajos)
- Crear: `docs/manual_nuevo/montar-un-presupuesto.md` (capítulo del manual; lo coordina el orquestador con quien lleva
  `docs/manual_nuevo/`)
- Compartidos: `CHANGELOG.md`, `docs/ERS.md` (RF de moneda por carpeta, aprobación, mercado, procura)

- [ ] **Paso 1:** grabar → `scratchpad/video/silice_obra_ficticia.webm` y `resultado.json` del recorrido con 22 pasos `ok`; si un paso
  falla, se trata como defecto de la tarea dueña (TDD y árbitro), no se graba alrededor.
- [ ] **Paso 2:** el manual cuenta el flujo de la obra con capturas del recorrido (sin datos reales) y las decisiones de §9-§10.
- [ ] **Paso 3:** cierre: `uv run --active pytest -q -W error -p no:cacheprovider` (suite completa: es cierre de fase),
  `npx vitest run`, `npm run lint`, `npm run build`, `ruff check` de lo tocado, `git diff <base>..HEAD -- core/` vacío.
- [ ] **Paso 4:** revisor de diseño sobre las capturas del recorrido; bitácora y memoria al día.
- [ ] **Paso 5:** commit `docs(manual): montar un presupuesto de punta a punta`. Sin push ni PR.

## Cierre

Árbitro por tarea (criterios A1-F1 de `MANUAL_ARBITRO.md`); el orquestador aplica los compartidos de cada informe en el orden de la
tabla de olas y corre `tests/unit/test_api_acceso_por_ruta.py`, `tests/unit/test_permisos.py`, `tests/integration/test_migraciones.py`
y `tests/unit/test_front_rutas_api.py` tras cada integración.

## Decisiones para Eugenio (ratificar al leer; el plan las toma así mientras tanto)

1. Revisa no gana `cambiar_caso`: llega a la carpeta de lo que debe aprobar con «Abrir» desde «Por aprobar» (choque 2).
2. «Estudio de mercado» va en el área Crear, después de «Catálogo»; «Aprobar una versión», en Auditar.
3. Cuartiles como `CUARTIL.INC` de Excel; la propuesta de cobro es el primer cuartil si es **igual o mayor** que el piso.
4. El plan propuesto al guardar la primera versión pasa a ser el de rendimientos (choque 10).
5. En una carpeta en USD, «Crear desde MaPreX» convierte la referencia en Bs con la tasa del BCV (choque 6).
6. Aviso de compra: 2 días hábiles antes de la fecha límite de pedido; plazo de entrega 3 días hábiles por omisión.
7. «Quien la armó» es quien guardó la versión (el usuario de su eslabón), no quien la envió.
8. El administrador no aprueba versiones (`aprobar_version` solo para arma y revisa, como dice §10).
