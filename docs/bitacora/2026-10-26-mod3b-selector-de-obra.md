# Selector de obra, carpetas y «Nueva obra» (MOD-3b): decisiones de ingeniería (2026-10-26)

**Encargo:** Tarea MOD-3b de `docs/planes/PLAN_MODULOS.md` (absorbe T6 y T7 del plan de montar un presupuesto); diseño
APROBADO `docs/especificaciones/2026-10-25-modulos-design.md` (§7 y §12) y BCP-5/BCP-6 de
`2026-10-21-bienvenida-casos-proyectos-design.md`. Commits: `fb3f4ab4` (listas de acciones con `aprobar_version`),
`96b50e5a` (rojo), `95b575d7` (implementación) y la ronda 2 del árbitro (§5). Las marcadas **por ratificar** las
decide Eugenio.

## 1. «Volver a la carpeta de la empresa» pregunta como «Cambiar carpeta…»

`DELETE /v1/casos/actual` llama a `caso_web.olvidar`, que descarta los borradores vivos de la Hoja de la sesión (hallazgo
del árbitro de MOD-3a). Por eso la marca «Demostración» no vuelve directo: pasa por `confirmarSalida("carpeta", extras)`
igual que abrir otra carpeta, con los mismos extras («Hoja de {obra}» por cada borrador de `GET /v1/hoja/borradores` con
`cambios > 0`). Las dos salen de un único `cambiar` en `src/shell/carpetas/useCarpetaDeTrabajo.ts`: no hay dos caminos.

Para nombrar el borrador, `proyecto` del borrador se busca por código o por nombre en la lista de obras (el servidor
puede mandar cualquiera de los dos, como ya dice `logicaRetomar.ts`); si no está, se dice tal cual. Un 403 o un fallo de
esa lectura cuentan como cero borradores (no se puede saber); un 401 cierra la sesión.

## 2. Interfaz ampliada respecto del plan (sin quitar nada)

- `SelectorObra` gana `puedeVerObras?` (por omisión, `obras !== null`): distingue «la cuenta no ve obras» (el
  administrador, o un 403 de `GET /v1/proyectos`) de «la lista aún no llega» (el botón dice «Obra: cargando…» si había una
  obra recordada). Exporta `ID_BOTON_OBRA`: los diálogos le devuelven el foco al cerrarse.
- `GestionCarpetas` gana `puedeDeclararMoneda?`, `alAbierta?` (de dónde se abrió: lista, creada, subida, demostración) y
  `nivelDeTitulo?` (3 en el diálogo, cuyo título es el h2; 2 en Administración). `alAbrir` puede devolver
  `Promise<boolean>`: el del armazón resuelve `false` si la persona eligió «Quedarme».
- `Aplicacion` gana, además de `elegirObra` y `abrirNuevaObra`, `abrirCarpeta` (opcional, como `modulo`): Administración ›
  Carpetas de trabajo abre por el armazón (misma confirmación, mismo aviso, la página se vuelve a montar).
- `src/shell/carpetas/MarcoDeDialogo.tsx`: el marco común de los dos diálogos propios (carpetas y «Nueva obra»), con
  `useAtraparFoco`, Esc y el foco devuelto al cerrarse; por debajo de «Cambios sin guardar» (z 8500 contra 9000).
- `src/comun/logicaBusqueda.ts` exporta `TIPO_DE_OBRA` (antes privado) para que «Nueva obra» no repita los rótulos.
- La búsqueda de obras usa `coincide` de `src/paginas/catalogo/filtro.ts` (sin tildes ni mayúsculas, cada palabra).

## 3. Comportamientos que el plan no fijaba

- **Abrir desde la lista o la demostración cierra el diálogo; crear y subir no.** Crear se queda para mostrar el nombre
  final saneado («Se creó la carpeta de trabajo «Obra_1» y ya trabaja con ella.», F5); subir, para el aviso de la migración
  y «Abrir ahora».
- **Crear:** confirmación → `POST /v1/casos` → `POST /v1/casos/actual` → `PUT /v1/carpeta/moneda` (corregido en la
  ronda 2, §5: antes la carpeta se creaba antes de preguntar).
- **El administrador no declara la moneda** (**por ratificar**): `PUT /v1/carpeta/moneda` exige `editar_hoja` y el
  administrador no la tiene (los permisos no cambian en este plan). En Administración › Carpetas de trabajo crear no pide
  la moneda y dice «La moneda de trabajo la declara una cuenta que arma presupuestos.». Hoy ninguna pantalla la declara
  después; alternativas: dar `editar_hoja`-para-moneda al administrador (cambio de permisos) o pedir la moneda de la carpeta
  en «Nueva obra» cuando falte.
- **Sin la demostración (F7):** la pestaña no aparece (el plan de MOD-3b lo pide así para el administrador) y una línea
  dice por qué: «La carpeta de demostración la abre una cuenta que arma presupuestos.».
- **Demostración, 201 y 200 la abren** directamente (F7), sin el paso intermedio «Abrirla ahora» de BCP-5 §4.5.
- **«Nueva obra», nombre vacío:** lo valida la API (el plan pide «el mensaje de la API en línea»). Ese texto viene de
  `aplicacion/proyectos.py` y dice «proyecto»: la guardia de vocabulario mira los textos propios del diálogo, no el `detalle`
  de la API (**para el backend**: «Escriba un nombre para la obra…» y «Ya existe una obra llamada…»).
- **La obra nueva entra a la lista al momento** (sin esperar la recarga) y queda elegida con `PUT /v1/sesion/proyecto`.
- **Administración vuelve a «Carpetas de trabajo»** tras abrir una carpeta desde ahí (la página se vuelve a montar): una
  marca en memoria solo para el montaje siguiente.
- **La marca «Demostración» no esconde su texto** con letra grande ni por debajo de 1366 px (es corta y es lo que dice en
  qué carpeta se está); el selector de obra sí, como la cuenta (queda el ícono y el nombre accesible).
- La lista de carpetas siempre trae la abierta, aunque `GET /v1/casos` no la liste (D1 del recorrido funcional), marcada
  «Abierta» con `aria-current`; la de la empresa dice «Carpeta de la empresa» y la de demostración «Datos inventados».
- Volver a la carpeta de la empresa cuando no está en la lista y la abierta no es la demostración no tiene botón (solo la
  marca de la demostración lo ofrece). **Por ratificar** si hace falta en la lista.

## 4. Lo que queda para MOD-5 (navegador)

- 1366×768 y 1056 px con las tres letras: el panel de la obra (22 rem), el diálogo de carpetas (44 rem, cuerpo con
  desplazamiento propio) y la marca «Demostración» junto al selector, sin desplazamiento horizontal.
- Esc dentro de «Buscar obra» (el `Search` de Carbon borra con Esc) y el foco al cerrar cada diálogo.
- Los estados vacíos de Hoja, Tablero y Control aún dicen «Elija un proyecto» y «Este proyecto aún no tiene versiones»
  (`paginas/hoja/logica.ts`, fuera de esta tarea): conviene pasarlos a «obra».
- `PlanoEnHoja.test.tsx` («Fusionar» no se puede pulsar…) falla a veces cuando corre junto a `src/shell` (pausa de 400 ms
  bajo carga); solo, pasa. No es de esta tarea.

## 5. Ronda 2 del árbitro

- **MAYOR, crear antes de preguntar.** «Crear y abrir» hacía `POST /v1/casos` y la confirmación llegaba después, dentro de
  abrir: con «Quedarme» la carpeta quedaba creada sin la moneda elegida (y luego tomaba Bs en silencio al crear la lista de
  MaPreX, contra D-MP1); y si fallaba `PUT /v1/carpeta/moneda` tras abrirla, el formulario decía «No se pudo crear la
  carpeta de trabajo» mientras el armazón avisaba «Ahora trabaja con…», y reintentar daba 409 «ya existe». **Arreglo:**
  `abrir(nombre, preparar?)` de `useCarpetaDeTrabajo` corre `preparar` (el `POST /v1/casos`) dentro del mismo `cambiar`,
  después de `confirmarSalida("carpeta", extras)` y antes de `POST /v1/casos/actual`: «Quedarme» no crea nada y el orden de
  las tres llamadas no cambia. Si falla el `PUT`, `Crear` dice «La carpeta «X» se creó y ya trabaja con ella, pero no se
  pudo declarar su moneda: {detalle}» con «Declarar la moneda», que repite solo el `PUT`. Si la carpeta se crea y no se
  puede abrir, dice que se creó y que se abra de la lista (nunca «No se pudo crear»).
- **Menor, subida.** Cada elección vacía antes la anterior (captura de `change` y `drop` alrededor de `SubidaArchivo`):
  un archivo que no es .db ya no deja el .db de antes con «Subir» habilitado. Un archivo de más de 20 MiB se rechaza en el
  navegador con el mismo texto de la API («El archivo pasa de 20 MiB.», el 413) y no se sube entero. La API sigue siendo
  la última palabra (su tope incluye el sobre del multipart).
- **Menor, búsqueda de obras.** Se vacía al cerrar el panel de cualquier forma (se ajusta en el render al pasar a
  cerrado). El `Search` de Carbon se quedaba con Esc (borra y detiene la propagación): ahora Esc en la búsqueda cierra el
  panel de una vez y el foco vuelve al botón.
- **Deuda del backend que llega tal cual a los diálogos** (los errores van con el `detalle` de la API): `api/rutas/casos.py:81`
  `MENSAJE_NO_ESTA` («El caso «X» no está en la carpeta de casos: elija uno de la lista.») al abrir una carpeta que ya no
  está, y `aplicacion/proyectos.py:89,135,149` («Escriba un nombre para el proyecto…», «Ya existe un proyecto
  llamado…») en «Nueva obra». La guardia de vocabulario mira los textos propios, no esos.
- `elegirObra`, `abrirNuevaObra` y `abrirCarpeta` quedaron **opcionales** en `src/shell/contexto.tsx` (el plan las da como
  parte de `Aplicacion`): el Shell siempre las da; así las pruebas de cada página no tienen que inventarlas, como `modulo`.
- **F11** conserva el título «Este proyecto aún no tiene versiones» (`SIN_VERSIONES` de `paginas/hoja/logica.ts`) y «Elija
  un proyecto · Use el selector de la cabecera» de la Hoja sin obra: el plan permite una sola línea de
  `paginas/hoja/index.tsx`, que se usó para la descripción de BCP-6 §5.2.
