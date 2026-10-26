# Selector de obra, carpetas y «Nueva obra» (MOD-3b): decisiones de ingeniería (2026-10-26)

**Encargo:** Tarea MOD-3b de `docs/planes/PLAN_MODULOS.md` (absorbe T6 y T7 del plan de montar un presupuesto); diseño
APROBADO `docs/especificaciones/2026-10-25-modulos-design.md` (§7 y §12) y BCP-5/BCP-6 de
`2026-10-21-bienvenida-casos-proyectos-design.md`. Commits: `fb3f4ab4` (listas de acciones con `aprobar_version`),
`96b50e5a` (rojo) y el de la implementación. Las marcadas **por ratificar** las decide Eugenio.

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
- **Crear:** `POST /v1/casos` → abrir (con la confirmación) → `PUT /v1/carpeta/moneda`. Si la persona elige «Quedarme», la
  carpeta queda creada y sin abrir ni moneda («ábrala de la lista cuando quiera»).
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
