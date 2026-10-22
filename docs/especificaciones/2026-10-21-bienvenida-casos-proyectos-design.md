# Bienvenida, carpetas de trabajo, proyectos, cómo se guarda y ayuda en lenguaje llano (React): diseño

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-adm-empresa` (árbol `.worktrees/s2madm`) · **Estado:** PROPUESTO. Lo juzga el árbitro
(`docs/planes/MANUAL_ARBITRO.md`, criterios B2, B3, B4, C1, C2, D1 y D2 aplicados al diseño). Sin su aprobación no hay código. Las
decisiones que no son de ingeniería están en §13 (D-1 a D-9), cada una con su recomendación.

**Origen del encargo.** Eugenio (2026-10-21, probando la interfaz React) pidió un flujo de bienvenida y una home de primera vez, y
dijo que no entendía qué es un «caso» frente a un «proyecto» ni cómo se guarda lo que hace. La retirada de Streamlit dejó una
**deuda bloqueante** (`docs/bitacora/2026-10-21-retiro-streamlit-cierre.md` §8, rama del retiro): una instalación nueva no puede
entrar, porque ninguna ruta ni pantalla de React llama a `preparar_primera_vez` ni a `reclamar_instalacion`. Este documento diseña seis
cosas que comparten pantalla y vocabulario: (A) el primer administrador, (B) crear, subir y estrenar «casos», (C) crear proyectos,
(D) explicar qué se guarda solo y qué es un borrador, (E) ayuda en lenguaje llano, y (F) accesibilidad.

**Alcance de este documento:** solo diseño. No se escribió código de producción ni se tocó ninguna prueba. No toca `core/`.

**Qué leí (enteros salvo donde se dice):** los dos manuales (`MANUAL_SUBAGENTES_MIGRACION.md`, `MANUAL_ARBITRO.md`); `frontend-desktop/DESIGN.md`
y `PRODUCT.md` (hasta «Operating Context»); `NORMAS.md` solo por referencia (el árbitro lo aplica; no lo releí entero); las dos
especificaciones modelo (`2026-10-19-hoja-react-design.md` §0, §3.1, §2.8 y §7; `2026-10-21-hoja-asistente-ia-design.md` §0 a §2 y §7 a
§11); el diseño del Inicio por áreas (`2026-10-18-silice-ui-inicio-panel-del-dia-design.md`, leído desde su commit `1c81a5ee`, porque el
archivo ya no está en el árbol) y su bitácora (`2026-10-19-T2-inicio-areas.md`); `seguridad/cuentas.py` y `seguridad/permisos.py`
enteros; `api/rutas/sesion.py`, `api/rutas/casos.py`, `api/rutas/proyectos.py`, `api/sesion_web.py`, `api/acceso.py`,
`api/caso_web.py`, `api/dependencias.py` (60-130), `api/proteccion.py` (45-180), `api/archivos.py`, `api/sin_cache.py`,
`api/sin_eco.py`; `api/rutas/presupuestos.py` 100-160 (`POST /proyectos`); `aplicacion/proyectos.py`, `aplicacion/entorno.py`,
`aplicacion/equipo.py`, `aplicacion/hoja_borradores.py` (cabecera); `operacion/config.py` entero, `operacion/base_datos.py` 125-525,
`operacion/lanzador.py` 255-330, `operacion/ordenes_100.py` (demostración y registro); `scripts/restablecer_administrador.py`;
`ui/acceso.py` y `ui/paginas/inicio.py` enteros y `ui/caso.py` 120-212 (cómo lo hacía Streamlit; `ui/` se borra en la rama del retiro:
se cita como **fuente de la regla**, no como código vivo); `docs/manual_usuario.md` 95-190 (§3.0 y §3.0 bis); `docs/manual_instalacion.md`
«Primer arranque» y «Casos»; `docs/ERS.md` (UC-12, RF-36 a RF-43, RF-60, RF-63, RF-81, RF-82, RF-84, RF-96, RNF-04, RNF-10 y los
máximos de numeración); en el front: `App.tsx`, `sesion/Entrar.tsx`, `sesion/useSesion.ts`, `shell/Shell.tsx`, `Selectores.tsx`,
`Cabecera.tsx`, `contexto.tsx`, `recorrido.ts`, `rutas.ts` (1-120 y las áreas), `MenuLateral.tsx` (1-60), `paginas/inicio/index.tsx`,
`api/cliente.ts`, `comun/EstadoVacio.tsx`, `comun/TamanoLetra.tsx`; y, de la rama `inc/ruta-s2-mig-retiro-streamlit` (cabeza
`a86532d2`), el estado de `operacion/lanzador.py` (ya lanza solo `uvicorn`, líneas 255-273), de `aplicacion/` y el parche de la deuda.
**No corrí ninguna prueba ni la aplicación**: lo que afirmo sale de la lectura, y cada afirmación que es deducción lo dice (§15).

**Convención de referencias:** `A:línea` = `ui/acceso.py`; `I:línea` = `ui/paginas/inicio.py` (los dos se borran en el retiro: son la regla,
no código vivo). Los demás son rutas del árbol `s2madm` en la base `4ad4c576`.

---

## 0. Resumen en catorce líneas

1. **Una instalación nueva hoy no entra, y el hueco es doble:** (a) nadie emite el código de instalación (`preparar_primera_vez` solo la
   llamaba la pantalla de Streamlit; el lanzador imprime el código «si el archivo ya existe», pero en el primer arranque aún no existe),
   y (b) nadie lo canjea (`reclamar_instalacion` no tiene ruta ni pantalla). Se cierran los dos (§3).
2. **Dos rutas nuevas y públicas, solo para el propio equipo:** `GET /v1/primer-arranque` (¿hay cuentas?, sin datos sensibles, `no-store`) y
   `POST /v1/primer-arranque/reclamo` (código + usuario + nombre + contraseña; mismo freno global y bloqueo de 5 fallos que el acceso, Origin
   obligatorio, 422 sin eco, mensajes fijos, el código no se registra ni se devuelve). Al canjear abre la sesión, como `POST /v1/sesion`.
3. **Hay un defecto real en `reclamar_instalacion`** que la clásica ocultaba: no toma el bloqueo de escritura antes de leer si el código sigue
   vivo (`_tomar_escritura` existe en el mismo archivo y lo usan `cambiar_roles` y `desactivar`). Dos reclamos simultáneos con logins
   distintos pueden crear **dos administradores con un solo código** (deducción por lectura, §1 H3). Se corrige con una línea y una prueba roja.
4. **Pantalla de bienvenida de primera vez** (en lugar de «Entrar» cuando no hay cuentas): qué es Sílice en tres líneas, dónde está el
   código (archivo y consola, escrito en llano), formulario con la política de contraseñas explicada, y qué pasa después. El mismo
   formulario sirve, con otro texto, al **código de restablecimiento** cuando ya hay cuentas (enlace «Perdí el acceso de administrador» en «Entrar»).
5. **Carpetas de trabajo (hoy «casos»):** se puede **crear**, **subir un `.db`** y **estrenar la demostración**, con las reglas de la
   clásica (sin `..`, rutas absolutas ni red) y más: la subida pasa por **cuarentena fuera de `casos/`**, se valida (firma, `integrity_check`,
   sin disparadores ni vistas, tablas de Sílice), se migra con respaldo y solo entonces aparece en la lista, con un renombrado atómico que nunca pisa nada.
6. **La demostración es una carpeta propia, `demostracion.db`,** que se construye en un proceso hijo (la API no puede importar `scripts/`, ARQ-5)
   y nunca escribe en la carpeta de trabajo de la persona. Diferencia deliberada con la clásica, que sembraba el caso abierto si estaba vacío (D-5).
7. **Crear proyecto:** `POST /v1/proyectos` (el `POST /proyectos` histórico no pone moneda ni responsable). Nombre único sin distinguir
   mayúsculas, moneda Bs/USD elegida (sin valor por defecto, UC-01 paso 1), tipo de obra opcional, responsable = la cuenta. El proyecto nuevo queda
   elegido y la hoja dice qué hacer: «sin versión guardada: describa el espacio o importe un plano y guarde la primera versión».
8. **Cómo se guarda, dicho una vez y en tres niveles:** *guardado en el archivo* (toda acción con botón que escribe confirma en el `.db` al
   instante), *borrador en memoria* (la hoja, hasta «Guardar versión») y *solo en pantalla*. **Hallazgo:** el borrador muere con la sesión: a los
   **30 minutos sin actividad** o a las **12 horas de antigüedad** (no a las 8 h del registro), además de al cambiar de carpeta, salir o reiniciar Sílice.
   La interfaz hoy cambia de caso **sin avisar** que descarta los borradores (§1 H12); se corrige con una confirmación.
9. **Vocabulario:** «Caso» no lo entiende un novato. «Espacio de trabajo» **choca** con «Espacio y metrajes» de la hoja. Se propone **«Carpeta de
   trabajo»** (palabra de Eugenio) en la interfaz, los manuales y las definiciones de la ERS; la API, el código y la base conservan `caso` (D-1).
10. **Ayuda sin tocar las 22 pantallas a mano dos veces:** un componente `AyudaDePagina` (una línea de «qué hace» bajo el único `h1`, texto
    en el registro `rutas.ts`), un botón «¿Qué es esto?» (Carbon `Toggletip`) junto a cada selector, una página «Ayuda y glosario» y un bloque
    «Primeros pasos» en el Inicio **derivado de los datos** (sin guardar nada en el navegador) que explica qué hacer primero según el rol.
11. **Primer usuario = administrador, y el administrador no arma.** La bienvenida lo dice y ofrece (D-2) marcar «usaré esta cuenta también
    para armar presupuestos»; si no, el Inicio le manda a crear la cuenta de quien arma.
12. **Accesibilidad:** pantallas completas y no capas para el flujo de entrada; diálogos Carbon con foco atrapado y devuelto; anuncios por
    región viva; 1366×768 y 1056 px con letra Normal, Grande y Muy grande sin desplazamiento horizontal; todo texto con tildes.
13. **Pruebas:** TDD con rojo visto; oráculos a mano de las constantes de `seguridad/cuentas.py` (5 fallos, 15 min, 20 fallos, 10 min, 10 a 128
    caracteres, 20 caracteres base32); seguridad específica (fuerza bruta del código, carrera de dos reclamos, traversal en nombres de
    carpeta, subida hostil); ninguna prueba abre la red ni usa libros reales.
14. **Once sub-rebanadas** (BCP-1 a BCP-11) con backend y frontend en paralelo contra un contrato fijo; nueve decisiones para Eugenio (D-1 a D-9).

### 0.1 Orden y estado de partida

- **Retiro de Streamlit** (rama `inc/ruta-s2-mig-retiro-streamlit`, otra sesión): su `operacion/lanzador.py` ya lanza solo `uvicorn` y su
  `ui/` está borrada. **Este diseño no puede construirse sobre `4ad4c576` tal cual:** `estado_caso`/`resumen_caso` vivían en `ui/caso.py`
  y el retiro **no los movió** (`git grep estado_caso` en esa rama solo encuentra un comentario), así que BCP-2 los reconstruye en
  `aplicacion/casos.py`. **BCP-1 y BCP-2 no empiezan hasta que la rama de trabajo contenga el retiro** (comprobable con
  `git merge-base --is-ancestor a86532d2 HEAD`). Los frentes (BCP-4 a BCP-7) sí pueden empezar contra el contrato de §9 con `fetch` simulado.
- **Autocompletado de campos** (otro agente: Componer, Hoja, Catálogo; memoria `feedback-campos-con-autocompletado-2026-10-21`): este diseño
  **no toca** `src/paginas/componer`, `hoja` ni `catalogo`, con dos excepciones mínimas y ordenadas al final: el texto del estado vacío
  de `hoja/index.tsx` (BCP-6) y la línea `<AyudaDePagina />` bajo el `h1` de cada página (BCP-8, la última sub-rebanada, cuando ese agente
  haya terminado). Ningún campo de este diseño pide un código o un dato técnico en texto libre que el autocompletado deba resolver.
- **Archivos compartidos** (solo el orquestador): `api/main.py`, `frontend-desktop/src/shell/rutas.ts` y su prueba,
  `tests/unit/test_api_acceso_por_ruta.py`, `tests/unit/test_arquitectura.py`, `CHANGELOG.md`, `docs/api.json`, `docs/ERS.md`, `package.json`.
  El texto exacto está en §14.

---

## 1. Hallazgos (verificados por lectura)

| # | Hallazgo | Evidencia | Consecuencia |
|---|---|---|---|
| H1 | **Nadie emite el código de instalación sin Streamlit.** `preparar_primera_vez` la llamaba solo la pantalla de acceso (`A:108`); el lanzador solo imprime el código si `codigo_instalacion.txt` ya existe, y esa comprobación corre **antes** de que alguien lo haya emitido | `cuentas.py:357-365`; `lanzador.py:286-289` (base) y `255-259` (rama del retiro); `git grep preparar_primera_vez` | el código se emite en el arranque (lanzador) y en el arranque de la API (gancho, §14), nunca al abrir una pantalla |
| H2 | `reclamar_instalacion` no tiene ruta ni pantalla en React; `/v1/sesion` solo autentica | `grep reclamar_instalacion` solo da `A:144` y pruebas | ruta y pantalla nuevas (§3) |
| H3 | **Carrera en el reclamo.** `reclamar_instalacion` lee `pendiente.usado` y `hay_usuarios` sin `_tomar_escritura`; pysqlite no abre transacción en un `SELECT`, y `pendiente.usado = ahora` se escribe sin condición. Dos hilos con logins distintos pasan ambos la comprobación y ambos crean un administrador. Con el mismo login, el segundo da `IntegrityError` (500) | `cuentas.py:393-427`; el remedio ya existe en `:145-158` y lo usan `cambiar_roles` (`:478`) y `desactivar` (`:509`) | deducción por lectura, **no probada**; BCP-1 abre con una prueba roja de carrera (S3) y añade `_tomar_escritura(session)` antes de leer |
| H4 | El orden de comprobaciones filtra el código: con el código válido y una contraseña débil, la ruta devuelve el mensaje de política; con un código inválido, `MENSAJE_CODIGO`. Un atacante distingue «código bueno» de «código malo» sin gastar el intento | `cuentas.py:393-406` (código primero, `validar_login`/`validar_contrasena` después) | la ruta valida la **forma** (usuario y contraseña) **antes** de tocar el código; así los dos casos devuelven el mismo mensaje de forma |
| H5 | El contador de intentos del código es **global** (`CLAVE_INTENTOS_CODIGO`): cinco fallos bloquean quince minutos el reclamo para todos, también para la persona legítima | `cuentas.py:55, 389-403` | aceptado (solo se canjea desde el propio equipo, §3.7); el mensaje dice «espere 15 minutos» y la prueba S1 fija el desbloqueo por reloj |
| H6 | El **restablecimiento** no distingue cuentas: si el login existe, `reclamar_instalacion` lo **reactiva y le agrega el rol administrador** aunque fuera `arma` o `revisa`, y cierra sus sesiones; si no existe, crea un administrador nuevo | `cuentas.py:416-420` | comportamiento heredado de S3 (quien corre el script tiene el equipo); se documenta y se pide a Eugenio decidir (D-6) |
| H7 | `scripts/restablecer_administrador.py` no está en el instalador ni en los manuales de usuario: en el producto instalado una persona no tiene cómo ejecutarlo | `grep` en `docs/manual_*.md` e `instalador/silice.iss` sin resultados; el instalador solo ofrece accesos «Sílice», «Detener Sílice» y «red local» | orden `python -m operacion restablecer-administrador` y acceso directo (D-7); la lógica pasa a `aplicacion/primer_arranque.py` (el script queda como envoltura) |
| H8 | Crear y subir casos existen en `operacion/base_datos.py` (`crear_caso`, `subir_caso`) pero **ninguna ruta los expone**; la lista de la cabecera es de solo elección | `base_datos.py:470-504`; `casos.py` solo tiene `GET` y `POST /actual` | rutas nuevas (§4) |
| H9 | `subir_caso` **escribe el archivo en `casos/` antes de validarlo** (`write_bytes` y luego `preparar_base`; si falla, `unlink`): en esa ventana otra sesión ve en su lista un archivo a medias, y un corte deja basura. Solo comprueba 16 bytes de firma | `base_datos.py:496-504` | la subida pasa por una carpeta de cuarentena fuera de `casos/` y se publica con renombrado atómico (§4.4) |
| H10 | `crear_caso` y `subir_caso` hacen «comprobar que no existe y crear» sin cerrojo; dos peticiones simultáneas con el mismo nombre pueden ambas pasar | `base_datos.py:475-479, 492-499` | cerrojo de proceso por la creación de casos (§4.2); la API corre en un solo proceso (`orden_uvicorn` sin `--workers`, vigilado por 3b-B26 de la Hoja) |
| H11 | **No hay límite propio de subida** más que los 20 MiB por petición de `LimiteDeCuerpo`; no hay tope de cuántas carpetas puede crear una cuenta | `proteccion.py:34, 120-175`; `base_datos.py` sin tope | se hereda el tope de 20 MiB (con 413 y mensaje fijo) y se agrega un tope de cantidad (D-4) |
| H12 | **Cambiar de caso descarta los borradores de la Hoja sin avisar.** `caso_web.fijar` llama a `hoja_borradores.olvidar(huella)`; `Shell.cambiarCaso` (`Shell.tsx:217`) no confirma nada | `caso_web.py:37-40`; `Shell.tsx:217-238` | confirmación con el número de borradores (`GET /v1/hoja/borradores`) antes de cambiar (§6.3) |
| H13 | **El borrador muere con la sesión, no a las 8 h.** `hoja_borradores.VIGENCIA` es 8 h sin uso, pero `sesion_vigente` llama a `caso_web.olvidar` al expirar la ficha, y la ficha expira a los **30 min de inactividad** o a las **12 h** de antigüedad aunque se esté usando | `sesiones.py:25-26, 98-101`; `sesion_web.py:83-85`; `caso_web.py:42-46` | el texto de «cómo se guarda» dice 30 minutos y 12 horas; el aviso de «Su sesión venció» dice que el borrador se perdió (§6.4) |
| H14 | `ui/paginas/inicio.py` dejaba **sembrar la demostración solo en el caso abierto vacío** y solo a quien tenía `EDITAR_HOJA` (`I:131`); el administrador no podía. `scripts/seed_demo.py` importa `scripts.seed`, que importa `tests.fixtures`, y `tests/unit/test_arquitectura.py:460-480` prohíbe que la API cargue `scripts`/`tests` aunque sea por otro paquete | `I:119-141`; `seed_demo.py:109`; `test_arquitectura.py:460, 494` | la demostración se construye en un **proceso hijo** y se publica como carpeta propia (§4.5) |
| H15 | `POST /proyectos` (`presupuestos.py:122-140`) no declara moneda ni responsable, pide `EDITAR_HOJA` y vive fuera de `/v1`. La función `aplicacion.proyectos.crear_proyecto_nuevo(ruta, …)` sí hace moneda, responsable y nombre sin distinguir mayúsculas, pero abre **su propio motor por ruta**, no la sesión de la petición | `presupuestos.py:122-140`; `proyectos.py:86-126` | `POST /v1/proyectos` sobre la `SesionDep` del caso de la ficha (RM-2) con una variante `crear_proyecto_en_sesion` (§5) |
| H16 | La cabecera mide 48 px y ya aloja los dos selectores, el tamaño de letra y «Salir»; no hay sitio para una línea de ayuda **bajo** los desplegables sin restar alto permanente a una pantalla de 768 px | `Cabecera.tsx`; `DESIGN.md` «Marco» | un `Toggletip` «¿Qué es esto?» junto a cada selector y una franja descriptiva solo mientras «Primeros pasos» esté pendiente (§7.2) |
| H17 | El Inicio por áreas ya existe (`paginas/inicio/index.tsx`: auditar un Excel, arenera, últimas auditorías) y **no menciona** carpeta de trabajo ni proyecto, salvo «Caso abierto: …» en una línea | `inicio/index.tsx` | «Primeros pasos» es un bloque **nuevo encima**; no se reordena ni se retira nada del Inicio |
| H18 | «Espacio» ya significa otra cosa: `Espacio y metrajes`, `esp_*`, «describa el espacio» (los ambientes del edificio) | `hoja-react-design.md` §2.5.1, §7.2 | descarta «Espacio de trabajo» como nombre (D-1) |
| H19 | Los respaldos manuales de la instalación existen (`POST /v1/admin/instalacion/respaldos` y descarga `.zip`) pero son del administrador; quien arma no tiene una forma de copiar su carpeta | `admin_instalacion.py:94` | el texto de «dónde queda y cómo se respalda» manda a Administración › Instalación (§6.5); una descarga por carpeta queda fuera (§11.1) |
| H20 | `Shell.tsx` pide `GET /v1/casos` solo al montar: una carpeta creada o subida por otra persona no aparece hasta recargar | `Shell.tsx:182` | el selector vuelve a pedir la lista al abrirse y tras cada creación (§4.6) |

---

## 2. Alcance y qué se reutiliza

| Pieza | Tratamiento | Bytes nuevos en archivos existentes |
|---|---|---|
| `seguridad/cuentas.py`: `emitir_codigo`, `preparar_primera_vez`, `reclamar_instalacion`, `hay_usuarios`, `FRENO`, `validar_*`, constantes | **tal cual**, salvo: `_tomar_escritura(session)` al inicio de `reclamar_instalacion` y el parámetro opcional `ademas_arma: bool = False` (D-2) | ~6 líneas (BCP-1) |
| `aplicacion/equipo.ip_es_local` | tal cual (criterio «propio equipo») | 0 |
| `api/sesion_web.py` (`poner_cookie`, `origen_propio`, `ahora`, `exigir_clave_o_sesion`, `csrf_de`), `api/sin_eco.py`, `api/sin_cache.py` | tal cual | 0 |
| `api/rutas/sesion.py`: cuerpo `SesionRespuesta` y `_cuerpo` | se **reutilizan** importándolos (el reclamo devuelve el mismo cuerpo que `POST /v1/sesion`) | 0 |
| `operacion/base_datos.py`: `resolver_caso`, `sanear_nombre`, `_validar_forma`, `preparar_base`, `leer_estado`, `listar_casos`, `CABECERA_SQLITE`, errores | tal cual, más la subclase `CasoYaExiste(RutaDeCasoRechazada)` | ~3 líneas |
| `operacion/respaldo.py` (`copiar_sqlite`, `abrir_solo_lectura`, `verificar_integridad`, `tablas_de`) | tal cual | 0 |
| `aplicacion/proyectos.py`: `crear_proyecto_nuevo`, `proyectos_del_caso` | `crear_proyecto_nuevo` pasa a envolver una función nueva `crear_proyecto_en_sesion` | ~25 líneas (BCP-3) |
| `core/budget` (`crear_proyecto`, `declarar_moneda`) | tal cual (`core/` intacto) | 0 |
| `api/rutas/casos.py`, `api/rutas/proyectos.py` | se **amplían** (rutas nuevas, las existentes no cambian) | BCP-2, BCP-3 |
| `operacion/lanzador.py` | una llamada a `asegurar_codigo` antes de imprimir el código | 4 líneas (BCP-1; el archivo lo cambia también el retiro: rebase) |
| `scripts/restablecer_administrador.py` | queda como envoltura de `aplicacion.primer_arranque.emitir_restablecimiento` | ~10 líneas |
| **Nuevo en `aplicacion/`** | `primer_arranque.py`, `casos.py`, `demostracion` no (va en `operacion/`) | — |
| **Nuevo en `operacion/`** | `demostracion.py` (proceso hijo) y la orden `restablecer-administrador` | — |
| **Nuevo en `api/`** | `rutas/primer_arranque.py`, `esquemas_bienvenida.py` | — |
| **Nuevo en el front** | `src/bienvenida/`, `src/shell/carpetas/`, `src/ayuda/`, `src/paginas/ayuda/`, bloque `PrimerosPasos` en `src/paginas/inicio/` | — |
| **No se toca** | `core/`, `asistente/`, `adapters/`, `paquete/` | 0 |

---

## 3. (A) El primer administrador

### 3.1 Emitir el código: dos lugares, una función

`aplicacion/primer_arranque.py` (RM-1, sin FastAPI):

- `asegurar_codigo(sesion, carpeta, ahora) -> bool`: envoltura de `cuentas.preparar_primera_vez`; idempotente (no hace nada si hay cuentas o ya
  hay un código vigente). Devuelve si emitió uno.
- `emitir_restablecimiento(sesion, carpeta, ahora) -> tuple[str, Path]`: lo que hoy hace `scripts/restablecer_administrador.restablecer`
  (se mueve aquí; el script y la orden `python -m operacion restablecer-administrador` lo llaman).
- `estado(sesion, carpeta) -> EstadoDeInstalacion`: `sin_cuentas = not cuentas.hay_usuarios(sesion)`, `archivo_presente = (carpeta /
  NOMBRE_ARCHIVO_CODIGO).is_file()`, `modo = "producto" if config.es_producto() else "desarrollo"`.

Quién la llama:

1. **El lanzador**, antes de leer el archivo para imprimirlo (`lanzador.py:255` en la rama del retiro). Es el único punto en que la consola
   muestra el código; sin esta llamada el primer arranque imprime nada (H1).
2. **El arranque de la API** (gancho `lifespan` en `api/main.py`, texto en §14), para el camino de desarrollo (`uvicorn api.main:app`) y para
   cuando el archivo se borró. Un fallo aquí se registra y **no** impide arrancar (la instalación sigue sirviendo el acceso normal).

El código **nunca** se emite desde una petición: ni `GET` ni `POST` escriben el archivo (un `GET` con efecto sería una trampa; la regla de
la clásica, emitir al pintar la pantalla, era posible porque Streamlit no distinguía).

### 3.2 `GET /v1/primer-arranque`

Pública (sin clave ni sesión), con `route_class=RutaSinCache` (`Cache-Control: no-store` también en los errores) y **solo para el propio
equipo**: `aplicacion.equipo.ip_es_local(request.client.host)`; desde otra IP, 403 con `equipo.MENSAJE_REMOTO`. (No se usa
`operacion_sensible_permitida`: esa función también se niega si hay «eventos de seguridad perdidos sin revisar», y el restablecimiento es
justamente la salida de ese caso.)

```
200 { "sin_cuentas": true|false,
      "archivo_presente": true|false,
      "modo": "producto"|"desarrollo",
      "politica": { "minimo": 10, "maximo": 128 } }
```

Sin nombres de usuario, sin rutas absolutas, sin el código ni su huella, sin número de cuentas. `politica` sale de `cuentas.MINIMO_CONTRASENA` y
`MAXIMO_CONTRASENA` (no se duplican en el front). `archivo_presente` solo sirve para decir «no encuentro el archivo» sin adivinar. Se pide al
montar `App` cuando no hay sesión; si responde 403 o falla, el front muestra «Entrar» (no inventa un estado).

### 3.3 `POST /v1/primer-arranque/reclamo`

```
{ "codigo": str ≤ 64, "usuario": str ≤ 120, "nombre": str ≤ 120, "contrasena": str ≤ 128, "tambien_arma": bool = false }
```

Orden fijo de comprobaciones (cada una antes de la siguiente; ninguna escribe hasta la última):

1. `Origin` **presente y propio** (`origen_propio`), si no 403 `MENSAJE_ORIGEN`. A diferencia de `POST /v1/sesion` (que tolera la ausencia de
   `Origin`), aquí **se exige**: crea una cuenta con el máximo rol y no hay ficha de la que sacar un token CSRF.
2. Propio equipo (`ip_es_local`): 403 `equipo.MENSAJE_REMOTO`.
3. Forma del cuerpo: Pydantic con `RutaSinEco`; 422 `{"detalle": <mensaje fijo>}` sin repetir lo enviado.
4. **Forma de usuario y contraseña** (H4): `cuentas.validar_login(usuario)` y `cuentas.validar_contrasena(contrasena, login)`; 422 con el mensaje de
   política. Se hace **antes** de mirar el código, para que un código bueno y uno malo respondan igual ante un dato mal formado.
5. `cuentas.reclamar_instalacion(sesion, codigo, usuario, nombre, contrasena, ahora, carpeta, ip=…, dormir=_no_dormir)` con el mismo patrón
   que `entrar`: `_Frenado` → 429 con `Retry-After` y evento `bloqueo`/«freno global»; `CuentaBloqueada` → 423 `MENSAJE_BLOQUEO`;
   `ErrorDeAcceso` (código inválido o ya usado, o no hay nada que reclamar) → 401 `MENSAJE_CODIGO` (**el mismo mensaje** con cuentas ya
   creadas y sin código de restablecimiento: no se revela si hay cuentas).
6. Éxito → `sesiones.abrir`, cookie (`poner_cookie`), cuerpo `SesionRespuesta` (el mismo de `POST /v1/sesion`), estado **201**. Si el navegador
   traía una ficha anterior se cierra y se olvida su caso (como `entrar`). `Cache-Control: no-store`.

Cambios en `seguridad/cuentas.py` (BCP-1, con prueba roja primero):

- `reclamar_instalacion` llama a `_tomar_escritura(session)` **después de la espera del freno y antes de `_intento`**: el segundo reclamo espera
  `busy_timeout` y encuentra `usado` fijado (H3).
- Parámetro `ademas_arma: bool = False`: con `True`, los roles de la cuenta nueva son `administrador,arma` (D-2). En un restablecimiento sobre una
  cuenta existente no cambia nada más que lo que ya hace.

**El código nunca se registra ni se devuelve:** no está en la respuesta (éxito ni error), ni en `evento_acceso` (el evento de fallo guarda
`login="(codigo)"`, `detalle="codigo"`), ni en el registro de la API (los 422 son sin eco y no hay `print`), ni en una cookie. La prueba S7 lo
busca en todo eso con la cadena literal del código de la prueba.

### 3.4 Qué pasa si ya hay cuentas (restablecimiento)

- El enlace «Perdí el acceso de administrador» (siempre visible en «Entrar») abre la **misma** pantalla de código con otro texto: «Un
  administrador con acceso al equipo ejecuta … y le da un código nuevo de 20 caracteres». Escribe el código, el usuario del administrador,
  su nombre y una contraseña nueva.
- Sin un código de restablecimiento pendiente, el servidor responde exactamente igual que con un código errado (401 `MENSAJE_CODIGO`).
- Con el código bueno: si el usuario **existe** se reactiva, se le agrega el rol administrador y se le cierran las sesiones; si **no existe** se crea (H6, D-6).
- El comando para generarlo: dev, `uv run python scripts/restablecer_administrador.py`; producto, `python -m operacion restablecer-administrador` desde
  el acceso directo propuesto en D-7. La pantalla dice las dos formas según `modo`.

### 3.5 La pantalla de bienvenida (primera vez)

Se muestra en lugar de «Entrar» cuando `GET /v1/primer-arranque` dice `sin_cuentas: true`. Es una **página** (`main.silice-entrada`, no un
diálogo), con un solo `h1` (`heading-04`) «Bienvenida a Sílice» y la cabecera mínima del marco (sin selectores).

Texto (con tildes; editable por el redactor tras revisarlo con una persona sin experiencia, §13 D-9):

```
h1  Bienvenida a Sílice
    Sílice le ayuda a calcular cuánto cuesta una obra, partida por partida, y a revisar presupuestos hechos en Excel.
    Todo se guarda en este equipo, en la carpeta de datos de Sílice. Nada sale de aquí sin que usted lo envíe.

h2  Paso 1: busque su código de instalación
    Sílice dejó un código de un solo uso para crear la primera cuenta. Está en dos sitios:
      • en la ventana negra que se abrió al iniciar Sílice (busque «Código de instalación»), y
      • en el archivo  codigo_instalacion.txt  dentro de la carpeta de datos de Sílice:
        %LOCALAPPDATA%\Silice\datos\codigo_instalacion.txt          (instalación normal; modo = producto)
        data\codigo_instalacion.txt, dentro de la carpeta del programa  (modo = desarrollo)
    Son 20 letras y números en grupos de cuatro, por ejemplo  XXXX-XXXX-XXXX-XXXX-XXXX. Cópielo y péguelo abajo.
    [si archivo_presente = false:] «No encuentro el archivo. Si ya lo borró, pida un código nuevo con
    «Perdí el acceso de administrador».»

h2  Paso 2: cree la cuenta del administrador
    Código de instalación        [__________________]   (sin eco; no se guarda)
    Su nombre                    [__________________]   (cómo aparecerá en lo que usted guarde)
    Usuario                      [__________________]   de 3 a 40 letras minúsculas, números, punto o guion
    Contraseña                   [__________________]   [mostrar]
    Repita la contraseña         [__________________]
    ☐ Usaré esta cuenta también para armar presupuestos        (ayuda: «Si usted trabaja solo, márquelo. Si no, luego cree otra cuenta con el rol «Arma».»)
    [Crear la cuenta y entrar]

    Cómo debe ser la contraseña (aparece siempre, no solo al fallar):
      • De 10 a 128 caracteres. Una frase larga es mejor que una palabra con símbolos.
      • No puede ser igual a su usuario ni una contraseña muy conocida (por ejemplo «password123»).
      • No hace falta mezclar mayúsculas, números o símbolos.
      • Sílice no puede recuperarla: si la olvida, se restablece con el equipo (vea «Perdí el acceso»).

h2  Qué pasa después
    Entrará con esa cuenta. Esta cuenta administra Sílice: crea las demás cuentas, la empresa y las copias de seguridad.
    Para armar presupuestos hace falta una cuenta con el rol «Arma». [si marcó la casilla: «Su cuenta ya puede hacerlo.»]
    El código se borra al usarse y no sirve otra vez.
```

Reglas de la pantalla:

- Dos campos de contraseña con comparación **en el cliente** (como `A:140`): «Las dos contraseñas no coinciden.» No se manda `repetida`.
- La política en llano sale de `politica` (10 y 128) y de los **mensajes de la API** (`MENSAJE_*` de `cuentas`), tal cual (DESIGN.md «Texto»: el `detalle` de la API).
  El cliente **no** lleva la lista de contraseñas comunes: solo la API decide; el cliente muestra el contador «N de 10 caracteres como mínimo».
- Atributos del navegador: código `autocomplete="off" spellcheck="false" autocapitalize="characters"`; usuario `autocomplete="username"`;
  contraseñas `autocomplete="new-password"`; el valor de contraseña y de código **no** va a `localStorage`, `sessionStorage` ni a la URL, y se
  borra del estado al terminar (éxito o error de 401/423). `PasswordInput` de Carbon con el botón de mostrar (accesible).
- Errores: el 401, 423 y 429 salen en un `InlineNotification` con `role="alert"` (el texto fijo de la API); el 429 muestra «Espere N segundos» con el `Retry-After`
  y deshabilita el botón ese tiempo; el 403 por equipo remoto muestra su texto. Ninguno borra lo escrito salvo el código.
- Éxito: `fijarCsrf(sesion.csrf)`, estado `activa` y el marco con el Inicio (que muestra «Primeros pasos», §7.6). No hay pantalla intermedia de «cuenta creada».

### 3.6 Entrar a una instalación con cuentas

`Entrar.tsx` gana, bajo el botón, un enlace de texto «Perdí el acceso de administrador» que lleva a `RecuperarAcceso` (misma forma que §3.5 con el
texto de §3.4, sin los pasos de bienvenida). No cambia el comportamiento del acceso ni sus mensajes.

### 3.7 Amenazas y mitigaciones

| Amenaza | Mitigación | Prueba |
|---|---|---|
| Fuerza bruta del código (100 bits) | 5 fallos → 423 por 15 min (contador global del código); freno global 20 fallos/10 min con espera 2^k s hasta 60 s; solo desde el equipo propio; 100 bits hacen inútil adivinarlo, el freno acota el ruido | S1, S2 |
| Reclamo desde la red local | 403 `MENSAJE_REMOTO`, aunque la red local esté encendida (solo bucle local o la IP del propio servidor, `operacion.red.es_cliente_local`) | S8 |
| Página web ajena que hace `POST` a `127.0.0.1` | `Origin` obligatorio y propio; sin `Origin` 403; el cuerpo exige el código, que la página no conoce | S8 |
| Carrera: dos administradores con un código | `_tomar_escritura` (H3) | S3 |
| El código en un registro, 422 o evento | sin eco, evento sin código, código no registrado; el lanzador lo imprime solo a la consola (`registro.registrar_secreto`) | S7 |
| Distinguir «hay cuentas» de «no hay» por la respuesta del reclamo | mismo 401 y mismo texto; `GET` solo para el equipo propio | S8, S4b |
| Distinguir código bueno de malo por el mensaje de forma | la forma se valida antes (H4) | S4b |
| Contraseña débil | `validar_contrasena` (misma política que cuentas) | S4 |
| Archivo del código legible por otro usuario de Windows | `%LOCALAPPDATA%` es por usuario; el código es de un solo uso; fuera de alcance endurecer ACL | (R-B5) |
| Denegación: un atacante local gasta los 5 intentos | aceptado; el mensaje explica la espera; `restablecer-administrador` emite otro código | (R-B4) |
| Reutilizar la cookie de otra persona en la bienvenida | el reclamo cierra la ficha previa del navegador y abre una nueva | B-reclamo-9 |

---

## 4. (B) Carpetas de trabajo (hoy «casos»)

### 4.1 Nombre

Ver D-1. En este documento el término de interfaz es **«carpeta de trabajo»** (recomendado) y el técnico, `caso`, se conserva en la API y el código.

### 4.2 Permisos, concurrencia y efecto sobre otras personas

| Acción | Quién (acción de `permisos.py`) | Base |
|---|---|---|
| Ver la lista y el resumen de la actual | cualquier cuenta con sesión | `GET /v1/casos` |
| Abrir otra carpeta | `CAMBIAR_CASO` (arma, administrador) | ya existe |
| **Crear** una carpeta | `CAMBIAR_CASO` | la clásica la ofrecía dentro del bloque cerrado por `puede_cambiar_de_caso` (`I:97, 110`) |
| **Subir** un `.db` | `CAMBIAR_CASO` | idem (`I:114`) |
| **Estrenar la demostración** | `EDITAR_HOJA` (solo arma) | `I:131` (D-3) |
| Crear un proyecto | `EDITAR_HOJA` | RF-63 / `POST /proyectos` |

Reglas de concurrencia (un solo proceso de API):

- **Cerrojo `threading.Lock` por toda creación de carpeta** (crear, subir y demostración) en `aplicacion/casos.py`: la comprobación de existencia, la
  publicación y la limpieza van dentro. Dos peticiones con el mismo nombre dan 201 y 409. Una creación larga (la demostración, hasta ~120 s) bloquea
  otras **creaciones**, nunca lecturas ni la Hoja de nadie.
- **Nunca se pisa un archivo:** la publicación usa `os.rename` (en Windows falla si el destino existe; en POSIX se complementa con una
  comprobación bajo cerrojo), no `os.replace`.
- **Otras personas con sesión no cambian de carpeta:** la elección vive por ficha (`caso_web._elegidos`), así que crear o subir no mueve a nadie.
  La carpeta nueva aparece en su lista cuando el selector vuelve a pedirla (H20). Subir **nunca** reemplaza una carpeta existente (409), de modo
  que no hay forma de cambiarle el archivo a alguien que lo tiene abierto.
- **Quien cambia de carpeta pierde sus propios borradores** (H12), nunca los de otra ficha.
- **No hay borrar ni renombrar** desde la interfaz (la clásica tampoco los tenía); se dice en la ayuda: «Para quitar una carpeta, el
  administrador la mueve fuera de la carpeta de datos con Sílice cerrado» (§11.1).
- Tope de cantidad: `MAXIMO_CARPETAS = 100` (supuesto, D-4); al llegar, 409 «Ya hay 100 carpetas de trabajo: retire alguna antes de crear otra.».

### 4.3 Crear

`POST /v1/casos` (cuerpo `{"nombre": str ≤ 200}`) → 201 `CasoRespuesta` (`nombre`, `ruta_relativa`). Con clave de API, 409 (`MENSAJE_CON_CLAVE`).

1. `_validar_forma(nombre.strip())` y `resolver_caso(sanear_nombre(nombre))` (las reglas de `base_datos.py`: sin UNC, absolutas, `..`, carpetas, `:`, ni
   nombres reservados de Windows; caracteres no permitidos pasan a `_`; 80 caracteres; extensión `.db`).
2. Bajo el cerrojo: existe → `CasoYaExiste` → 409 «Ya existe el caso X.db: ábralo de la lista o elija otro nombre.» (con el término nuevo, §13 D-1);
   si no, `preparar_base(ruta)` (crea el esquema en `head`).
3. La respuesta trae el nombre **final** (`Obra_1.db` si tecleó `Obra*1`); el diálogo lo muestra («Se creó con el nombre Obra_1.db») y luego llama a
   `POST /v1/casos/actual` para abrirla (dos llamadas: si la segunda falla, la carpeta existe y no está abierta, estado coherente).
4. `ErrorDeBase` al preparar → 503 con su mensaje; si el archivo quedó creado a medias, se elimina (solo lo que esta petición creó).

Errores (todos con `detalle`): 422 (forma o reservado, texto de `RutaDeCasoRechazada`), 409 (existe / tope), 503 (no se pudo preparar), 403 (sin permiso, CSRF u origen).

### 4.4 Subir un `.db`

`POST /v1/casos/subida`, `multipart/form-data`: `archivo` (obligatorio) y `nombre` (opcional; por omisión, el del archivo). → 201 `CasoSubido`
(`CasoRespuesta` + `aviso: str | null`, p. ej. «Se actualizó el archivo a la versión actual de Sílice; quedó un respaldo previo.»). Pipeline en
`aplicacion/casos.subir_seguro`, **todo o nada**:

1. Nombre: `sanear_nombre(nombre or archivo.filename)` (solo la última parte; `..\..\x.db` queda `x.db`); sin nombre utilizable → 422.
2. Tope: se lee el cuerpo en bloques hasta `TOPE_SUBIDA = 20 MiB` (el de `LimiteDeCuerpo`; el multipart añade unos cientos de bytes, así que el
   archivo útil es algo menor); pasar → 413 `{"detalle": "El archivo pasa de 20 MiB."}` y no queda nada en disco. El middleware ya corta antes de
   leer todo; el conteo propio cubre un `Content-Length` mentiroso.
3. Se escribe a `<datos>/cuarentena/<token_hex(16)>.sub` (**fuera de `casos/`**, creación exclusiva, sin extensión `.db`).
4. Firma: los 16 primeros bytes son `CABECERA_SQLITE`; si no, 422 «X no es una base de Sílice (SQLite): no se guardó.» (texto de `BaseIlegible`).
5. Inspección en **solo lectura** (`respaldo.abrir_solo_lectura`): `PRAGMA integrity_check` debe dar `ok`; en `sqlite_master` **ninguna** fila de tipo
   `trigger` o `view`, ninguna tabla virtual (`sql` que empiece por `CREATE VIRTUAL`); debe existir `alembic_version` con una revisión conocida **o** las
   tablas núcleo del caso (el conjunto de `core.models`, ver §15). Una tabla de más no se rechaza (puede ser de una versión anterior); sí se avisa en el
   registro, sin contenido. Fallo → 422 «El archivo no es una carpeta de trabajo de Sílice válida: no se guardó.» (texto fijo; el detalle técnico va al registro).
6. Revisión más nueva que este código → `BaseMasNueva` → 422 con `MENSAJE_MAS_NUEVA` (no se modifica nada).
7. `preparar_base` **sobre la copia de cuarentena** (respaldo previo y migración a `head`, RF-96; un fallo deja el original sin cambios).
8. Publicación: `respaldo.copiar_sqlite(cuarentena, casos/.subiendo-<token>.tmp)` (consolida WAL) y `os.rename` a `casos/<nombre>.db` bajo el cerrojo; si
   el destino existe → 409 «Ya hay una carpeta llamada X.db: cambie el nombre antes de subirla.». Sin extensión `.db`, `listar_casos` no ve el temporal.
9. `finally`: se borra la cuarentena y cualquier temporal. Al arrancar la API se purgan los de más de 1 hora.

Un archivo rechazado **no crea nada** en `casos/` ni deja nada en la cuarentena (S5, comparando el árbol de la carpeta de datos antes y después).

### 4.5 La demostración

`POST /v1/casos/demostracion` → 201 (la creó) o 200 (ya existía y tenía partidas), mismo cuerpo `CasoRespuesta`. `EDITAR_HOJA`.

- Nombre **fijo**: `demostracion.db` (ningún texto de la persona llega al proceso hijo).
- `operacion/demostracion.crear(carpeta)`: bajo el cerrojo, si `demostracion.db` existe y `estado` dice que tiene partidas, devuelve 200 sin tocar nada. Si no,
  ejecuta un **proceso hijo** `[sys.executable, "-E", "-s", "-B", "-X", "utf8", "-m", "operacion", "demostracion", "--salida", <ruta de cuarentena>]` con
  `timeout = 120 s` y sin shell (los mismos indicadores que el instalador, `silice.iss` `OpD`); `ordenes_100._demostracion` gana `--salida` (absoluta, armada por el
  servidor). El hijo importa `scripts.seed_demo` (esto es lo que la API no puede hacer, ARQ-5); la API no carga `scripts` ni `tests`.
- Terminado, se valida como una subida (pasos 5-6) y se publica con el paso 8. Fallo o `timeout` → 503 «No se pudo preparar la demostración. Pruebe de
  nuevo; si sigue, avise al administrador.» y se limpia lo que esta petición creó.
- La demostración es **ficticia** (`scripts/seed_demo.py`: «caso didáctico, no obra ejecutada»: la línea base de la clínica, tres partidas `DEMO-*` y el
  presupuesto `DEMO-001`) y la interfaz lo dice: «Datos de ejemplo inventados para aprender; no son una obra real».
- No borra ni modifica la carpeta que la persona tenía abierta (diferencia con `I:119-141`, D-5). El diálogo, tras crearla, ofrece «Abrirla ahora».

### 4.6 Resumen de la carpeta abierta y lista fresca

- `GET /v1/casos/actual` (nuevo, solo lectura, cualquier rol con sesión; con clave de API, el caso del proceso):

```
{ "nombre": "demo.db", "ruta_relativa": "casos/demo.db", "ubicacion": "En %LOCALAPPDATA%\\Silice\\datos\\casos\\demo.db",
  "partidas": 8, "insumos": 31, "lista_vigente": "MaPreX jul-2026" | null, "proyectos": 1, "proyectos_con_version": 1,
  "es_demostracion": false, "por_migrar": false, "error": null | "texto" }
```

  Equivale a `ui.caso.estado_caso` (que el retiro borra): conexión de **solo lectura**, sin DDL, nunca crea el archivo (RV-5). `ubicacion` es texto en llano con
  la variable literal `%LOCALAPPDATA%` en producto y la ruta relativa a la carpeta del programa en desarrollo: **ninguna ruta absoluta** (como `GET /v1/casos`).
- El selector «Carpeta de trabajo» vuelve a pedir `GET /v1/casos` al abrirse (foco o clic) y tras cada creación (H20).
- Al **cambiar** de carpeta, si la ficha tiene borradores con cambios (`GET /v1/hoja/borradores` con `cambios > 0`), el front muestra un diálogo de
  confirmación: «Tiene N borrador(es) de la hoja con cambios sin guardar. Si cambia de carpeta se descartan. ¿Cambiar de todos modos?» [Quedarme] [Cambiar y descartar]. Sin borradores o sin
  cambios, cambia directo como hoy. El mismo aviso se repite en «Salir» (§6.3).

### 4.7 Lo que el diálogo «Carpetas de trabajo» ofrece

Un botón «Carpetas…» al lado del selector abre un `ComposedModal` de Carbon con tres pestañas (`Tabs`): **Crear**, **Subir un archivo** y **Demostración**.
Cada una tiene su explicación en una línea («Una carpeta de trabajo guarda su catálogo, sus precios y sus proyectos en un solo archivo») y su botón. Sin
`CAMBIAR_CASO` el botón no aparece (el selector queda como hoy, deshabilitado). Sin `EDITAR_HOJA`, la pestaña Demostración dice por qué no está disponible.

---

## 5. (C) Proyectos

### 5.1 Ruta

`POST /v1/proyectos` en `api/rutas/proyectos.py`, `EDITAR_HOJA` (clave de API o sesión; CSRF y Origin por la dependencia), `RutaSinEco`:

```
{ "nombre": str ≤ 120, "moneda": "Bs"|"USD"|null, "dominio": ""|"civil"|"telecom"|"industrial"|"sistemas", "descripcion": str ≤ 500 = "" }
→ 201 { codigo, nombre, version_vigente: null, version_codigo: null, actualizado: null }   (la forma de un elemento de GET /v1/proyectos)
```

- `aplicacion.proyectos.crear_proyecto_en_sesion(sesion, nombre, moneda, dominio, descripcion, responsable)`: normaliza el nombre
  (`" ".join(nombre.split())`), rechaza vacío, compara **sin distinguir mayúsculas** en Python (`casefold`, como `proyectos.py:109-112`), llama a `core.budget.crear_proyecto` y,
  si hay moneda, `declarar_moneda(..., responsable=<cuenta>)`, y confirma en una sola transacción (todo o nada; si `declarar_moneda` falla, no queda el proyecto).
  `crear_proyecto_nuevo(ruta, …)` pasa a abrir su motor y delegar en ella (la lógica no se duplica).
- `moneda` es **obligatoria desde la interfaz** (UC-01 paso 1: «sin valor por defecto en la interfaz») pero la API acepta `null` (las integraciones y `POST /proyectos`
  siguen igual); el front manda siempre una.
- Responsable: la cuenta de la sesión (`activa.usuario`, `Nombre <login>`, RF-82), nunca `RESPONSABLE_DE_LA_INTERFAZ`; con clave de API, `USUARIO_API`.
- Un `IntegrityError` por la restricción única (dos peticiones a la vez) se traduce al mismo 409.

Mensajes (la clásica, con tildes; DV-BCP-3): vacío → 422 «Escriba un nombre para el proyecto: no puede quedar vacío.»; repetido →
409 «Ya existe un proyecto llamado «X»: elija otro nombre o abra ese.»; moneda fuera de Bs/USD → 422 con el texto del núcleo; tipo de obra desconocido → 422 con el texto del núcleo.

### 5.2 Interfaz

- Un botón «Nuevo proyecto» junto al selector Proyecto (solo con `editar_hoja`) abre un diálogo: Nombre, Moneda (`Select`, sin opción preelegida: «Elija…»),
  Tipo de obra (opcional, con «Sin especificar»). Las ayudas dicen: «Moneda: en la que se calcularán los precios de este proyecto. Se puede convertir después, con tasa, desde la hoja».
- Al crear: `recargarProyectos()` y el Shell **elige el proyecto nuevo** (guarda el código en una referencia `proyectoPorElegir` y lo asigna cuando llega la lista, para no depender del orden).
- **Sin versión guardada** (`version_vigente: null`): el selector rotula «Torre B (sin versión guardada)»; la Hoja, en lugar de «Elija un proyecto» o de una tabla vacía, muestra un
  `EstadoVacio`: «Este proyecto aún no tiene versión guardada. Describa el espacio (ambientes y puntos) o importe un plano, y guarde la primera versión con «Guardar primera versión…»».
  (El botón y el flujo ya existen: `hoja/index.tsx:73`.) El Tablero y las demás pantallas que necesitan versión dicen lo mismo con un enlace a la Hoja.
- Si el proyecto es nuevo y la persona abre la Hoja, el panel de ayuda «Primeros pasos» (§7.6) marca el paso 3 como el siguiente.

---

## 6. (D) Cómo se guarda: qué se guarda solo, qué es un borrador

### 6.1 Tres niveles, tres palabras

| Palabra en pantalla | Qué es | Cuándo se guarda | Qué pasa si cierra Sílice |
|---|---|---|---|
| **Guardado** | lo que una acción con botón escribió en el archivo `.db` de la carpeta de trabajo (crear proyecto, guardar una partida, cargar precios, registrar una cotización, **guardar versión**…). Cada una confirma su transacción (todo o nada) y queda al instante | al pulsar el botón de esa acción; no hay «guardado automático» de otra cosa | no se pierde |
| **Borrador** | los cambios de la **Hoja del proyecto** que aún no son una versión: viven en la memoria de Sílice, no en el archivo | solo al pulsar **Guardar versión**; hasta entonces son provisionales | **se pierde** (ver §6.2) |
| **Solo en pantalla** | filtros, pestañas abiertas, texto a medio escribir en un cuadro | nunca | se pierde |

Frase fija del glosario: «Lo que Sílice guarda va al archivo de su carpeta de trabajo en el momento de pulsar el botón. Lo único que se queda provisional es el borrador de la hoja, hasta
que usted guarde una versión.»

### 6.2 Cuándo se pierde un borrador (todos los caminos, H13)

El borrador vive en el servidor, ligado a la ficha de sesión (`hoja_borradores`; hoja-react-design §3.1). Se descarta:

1. al **cambiar de carpeta de trabajo** (`caso_web.fijar`); 2. al **Salir**; 3. a los **30 minutos sin actividad** o a las **12 horas** desde que entró (aunque esté trabajando), porque la ficha vence y
`caso_web.olvidar` lo arrastra; 4. a las **8 horas sin tocarlo** (`VIGENCIA`); 5. al **reiniciar Sílice** (memoria del proceso); 6. por exceso de borradores (4 por ficha, 64 en total o 256 MiB: el menos usado).
**No** se pierde al recargar la página (F5), ni al cambiar de proyecto en la cabecera (se retoma desde la Hoja), ni al navegar a otra pantalla.

### 6.3 Avisos de salida

| Situación | Aviso | Dónde |
|---|---|---|
| Cerrar la pestaña o recargar con cambios sin guardar | `beforeunload` (ya existe en `hoja/index.tsx:402`) | Hoja |
| Cambiar de carpeta de trabajo con borradores con cambios | diálogo de confirmación con el número (§4.6) | Shell |
| «Salir» con borradores con cambios | el mismo diálogo: «Si sale, se descartan. Guarde una versión primero.» | Cabecera/Shell |
| Cambiar de proyecto en la cabecera con borrador | **sin diálogo**; nota en el selector («Su borrador de «Torre B» sigue abierto en la Hoja») y la Hoja ya ofrece «Retomar» | Selectores/Hoja |
| La sesión venció | aviso en «Entrar»: «Su sesión venció por inactividad. Los cambios de la hoja que no guardó se perdieron.» (hoy: «Su sesión venció. Entre de nuevo para seguir.») | `App.tsx` |
| Indicador permanente | región `role="region" aria-label="Estado del borrador"` ya existente en la Hoja («3 cambios sin guardar»); se agrega la frase «Provisional hasta que guarde una versión» | Hoja |

No se promete un aviso «le quedan 5 minutos» porque `GET /v1/sesion` no informa el tiempo restante; ese contador es una mejora posible (D-8).

### 6.4 Dónde queda el archivo y cómo se respalda

- En la barra «Carpeta de trabajo» (Inicio, Primeros pasos y el diálogo): «Su carpeta «demo.db» está en: %LOCALAPPDATA%\Silice\datos\casos\demo.db» (`ubicacion` de §4.6; ninguna ruta absoluta).
- **Copia de seguridad**: el administrador la crea y descarga desde Administración › Instalación (Respaldos); Sílice además respalda **antes de migrar** una carpeta.
  Quien arma ve: «Para una copia de seguridad, pídale al administrador que cree un respaldo (Administración › Instalación). No copie el archivo mientras Sílice está abierto.»
  Copiar a mano el `.db` con Sílice **detenido** es válido; con Sílice en marcha el archivo puede tener cambios en archivos auxiliares `-wal`/`-shm` (SQLite modo WAL; `data/casos/` los muestra).
- Mover a otro equipo: copiar el `.db` y usar «Subir un archivo» allí.

---

## 7. (E) Ayuda en lenguaje llano

### 7.1 Vocabulario y regla de consistencia

Una palabra por idea, la misma en pantalla, manuales, ERS y mensajes de la API que lee la persona:

| Idea | Palabra en pantalla | Se evita |
|---|---|---|
| El archivo que guarda catálogo, precios y proyectos | **carpeta de trabajo** (D-1) | caso, base de datos, archivo `.db` (salvo al subir: «archivo .db»), espacio de trabajo |
| Una obra dentro de la carpeta | **proyecto** | obra, caso (dos significados), presupuesto (otra cosa) |
| Receta de costo de una partida | **análisis de precios unitarios (APU)**; abreviado **APU** desde la segunda mención | análisis, receta (solo en la explicación) |
| Un trabajo medible con su precio | **partida** | rubro, ítem (salvo en tablas ya existentes) |
| Foto guardada de un proyecto | **versión** | revisión, snapshot |
| Cambios aún no guardados de la hoja | **borrador** | sesión de edición |
| Excel de presupuesto que ya tiene | **libro** | planilla, archivo |
| Algo que no cuadra | **hallazgo** | error (reservado a la gravedad) |

Los términos técnicos (`caso`, `APU`, `UC-xx`) no aparecen en pantalla sin su explicación (DESIGN.md/D1: sin jerga interna). **Regla de consistencia:** toda cadena visible nueva usa esta tabla;
una prueba estática (`F-vocab`) busca en `src/**/*.tsx` (excluidas pruebas y `docs/`) los literales prohibidos como texto visible (`>Caso<`, `"Caso"` en `labelText`, «este caso») y falla.

### 7.2 Ayuda junto a los selectores (H16)

- Junto a **Carpeta de trabajo** y **Proyecto** va un botón-icono «?» (Carbon `Toggletip`, `aria-label` «¿Qué es la carpeta de trabajo?» / «¿Qué es el proyecto?»), abre con clic, Intro o Espacio y
  se cierra con Esc devolviendo el foco. Texto de cada uno:
  - Carpeta de trabajo: «La carpeta donde Sílice guarda su catálogo, sus precios y sus proyectos. Está en un solo archivo de este equipo. Puede tener varias, por ejemplo una por empresa o una de práctica».
  - Proyecto: «La obra con la que trabaja ahora. Cada proyecto guarda sus versiones. Elija uno o cree uno nuevo».
- **Franja descriptiva** (32 px, `body-compact-01`, bajo la cabecera, dentro de `main`): «Carpeta de trabajo: su catálogo, precios y obras. Proyecto: la obra con la que trabaja ahora.» Aparece **solo mientras «Primeros pasos» tenga algo pendiente**
  (derivado de los datos, §7.6); luego desaparece y queda el «?». Con letra Grande y Muy grande baja de línea (alto mínimo, no fijo).
- Los selectores se llaman en pantalla «Carpeta de trabajo» y «Proyecto» (D-1).

### 7.3 «Qué hace esta pantalla» (una línea bajo el `h1` de cada página)

Componente `AyudaDePagina` (`src/ayuda/AyudaDePagina.tsx`): un `<p class="cds--type-body-compact-01" id="…">` bajo el único `h1`, con el texto del campo `queHace` de la página en
`rutas.ts`, más el enlace «Ver el glosario». Va dentro de la página (no en el Shell) para respetar el orden de lectura y el foco: el Shell manda el foco al `h1` al navegar (VD-7); la
línea queda justo después. Cada página lo monta con una línea (`<AyudaDePagina />`, sin props: lee su ruta); una **prueba estática** (`F-ayuda-cobertura`) comprueba que todo `index.tsx` migrado lo importa y
que todo `PaginaDef` tiene `queHace` no vacío, para que una pantalla nueva no salga sin ayuda. Textos (propuesta; se validan con una persona sin experiencia, D-9):

| Pantalla (`id`) | Qué hace (una línea) |
|---|---|
| Inicio (`inicio`) | Su punto de partida: qué hacer primero, auditar un Excel que ya tiene y retomar lo último que hizo. |
| Tablero del proyecto (`tablero`) | Resume un proyecto: su versión vigente, el total y lo que encontró la auditoría. |
| Catálogo de partidas e insumos (`catalogo`) | Lista las partidas y los insumos de su carpeta de trabajo con el precio vigente. Aquí solo se consulta. |
| Componer una partida (`componer`) | Arma la receta de costo de **una** partida (materiales, equipos y mano de obra) y calcula su precio unitario. |
| Elaborar un presupuesto (`elaborar`) | Arma un presupuesto con **muchas** partidas y sus cantidades, a partir de una fuente de datos, y lo audita. |
| Hoja del proyecto (`hoja`) | Describa el espacio de un proyecto, ajuste partidas, precios y parámetros, y guarde versiones. |
| Actualizar precios (`actualizacion`) | Carga una lista de precios nueva y vuelve a calcular un presupuesto ya guardado. |
| Histórico de cambios de precio (`historico`) | Muestra cada cambio de precio que Sílice registró, con filtros. |
| Precios de la empresa (`precios_empresa`) | La lista de precios propia de la empresa, que el administrador mantiene. |
| Índices del BCV (`indices`) | Registra los índices del Banco Central de Venezuela que se usan para reajustar precios. |
| Reajuste de precios (`reajuste`) | Calcula cuánto cambia el precio de un contrato con la fórmula de reajuste y los índices. |
| Control de obra (`control`) | Compara lo presupuestado con lo que cuesta la obra real: línea base, valuaciones y costos. |
| Acerca de Sílice (`acerca`) | La versión del programa, su licencia y el estado de esta instalación. |
| Entregar paquete (`entregar`) | Prepara el paquete firmado de un proyecto para entregarlo a otra persona. |
| Existencias de la arenera (`existencias`) | Cuánto hay de cada material en la arenera y los movimientos de entrada y salida. |
| Revisar un paquete (`revisar`) | Abre un paquete recibido, lo vuelve a auditar y deja el dictamen. |
| Libro de la empresa (`libros`) | Audita un Excel de presupuesto que **ya tiene**: recalcula cada partida y marca lo que no cuadra. |
| Historial de auditorías (`historial`) | Las auditorías de libros que ya hizo, con su resumen y sus hallazgos. |
| Escenarios de sensibilidad (`escenarios`) | Prueba qué pasaría con el total si cambian precios o rendimientos, sin alterar el presupuesto. |
| Partidas similares (`similares`) | Busca partidas parecidas a una descripción para reutilizar su desglose. |
| Simulador de listas (`simulador`) | Genera listas de precios de prueba para practicar. |
| Administración (`administracion`) | Cuentas, empresa, claves, copias de seguridad y red de esta instalación. |
| Ayuda y glosario (`ayuda`, nueva) | Qué significa cada palabra de Sílice y cómo se guarda lo que usted hace. |

### 7.4 Glosario accesible (página `ayuda`, ruta `#/ayuda`, sin permiso)

Lista de definición (`<dl>`), orden alfabético, un `h2` por letra no (un solo `h1`, `h2` por grupo «Palabras de Sílice» y «Cómo se guarda»). Cada término con `id` para enlazarlo. Definiciones (propuesta):

- **APU (análisis de precios unitarios):** la receta de costo de una partida: qué materiales, equipos y horas de mano de obra hacen falta por cada unidad (un metro, un metro cuadrado…) y cuánto cuesta cada uno.
- **Borrador:** los cambios de la hoja que todavía no guardó como versión. Viven en la memoria de Sílice: si sale, la sesión vence o cambia de carpeta, se pierden.
- **Carpeta de trabajo:** el archivo donde Sílice guarda su catálogo, sus precios y sus proyectos. Puede tener varias.
- **Hallazgo:** algo que la auditoría encontró y conviene revisar (una cuenta que no cuadra, un precio muy distinto del habitual…). Tiene gravedad: crítico, error, advertencia o información.
- **Insumo:** un material, un equipo o un tipo de mano de obra con su precio.
- **Libro:** un archivo de Excel con un presupuesto, normalmente hecho fuera de Sílice.
- **Lista de precios:** los precios de los insumos desde una fecha; Sílice usa la vigente.
- **Partida:** un trabajo que se puede medir y cobrar (por ejemplo, «Tubería de PVC de 6 pulgadas», por metro), con su APU y su precio unitario.
- **Presupuesto:** muchas partidas con sus cantidades. El total es la suma de cantidad × precio unitario de cada una, más los costos indirectos.
- **Proyecto:** la obra con la que trabaja. Guarda sus versiones.
- **Versión:** una foto guardada de un proyecto en un momento dado, con quién la guardó y por qué. Las versiones no se borran: se guarda una nueva.
- **Guardado / Borrador / Solo en pantalla:** §6.1.

### 7.5 «¿Qué es esto?» contextual

Un componente `Termino` (`<Termino id="partida">partida</Termino>`) pinta la palabra con subrayado punteado y un `Toggletip` con la definición de §7.4 y el enlace «Ver en el glosario». Se usa
**solo la primera vez** que una palabra de la tabla aparece en una línea de ayuda (§7.3), el estado vacío de una pantalla o «Primeros pasos»; no se siembra por toda la interfaz. Es un botón
(teclado, `aria-expanded`, Esc cierra), no un `title`; el contenido es texto del registro `glosario.ts` (una fuente, la misma que la página).

### 7.6 Home de primera vez: «Primeros pasos»

Un bloque nuevo **encima** de «Audite un presupuesto» en el Inicio (no reordena el resto, H17), con `h2` «Primeros pasos» y una lista numerada. Se **deriva de los datos** (función pura
`pasosDeInicio(resumen, acciones, roles)` en `src/paginas/inicio/primerosPasos.ts`, con prueba): no guarda nada en el navegador (RT-9) y desaparece cuando todo está hecho (queda un enlace «Ver los primeros
pasos» en el glosario). Fuentes: `GET /v1/casos/actual` (§4.6) y `sesion.acciones`.

| Rol | Pasos | Se marca hecho cuando |
|---|---|---|
| Administrador sin `arma` | 1. «Cree la cuenta de quien arma presupuestos» → Administración › Cuentas. 2. «Revise la copia de seguridad» → Administración › Instalación. | hay más de una cuenta (el resumen de cuentas lo da `GET /v1/cuentas`, que ya lee `administrar_cuentas`) |
| Arma | 1. «Elija o cree su carpeta de trabajo» → botón **Carpetas…** (con «Abrir la demostración» si la carpeta está vacía). 2. «Cree un proyecto» → **Nuevo proyecto**. 3. «Describa el espacio y guarde la primera versión» → Hoja. 4. «Revise el total y la auditoría» → Tablero. | 1: `partidas > 0`. 2: `proyectos > 0`. 3: `proyectos_con_version > 0`. 4: sin marca (siempre opcional) |
| Revisa | 1. «Audite un libro de la empresa» → Libro de la empresa. 2. «Revise un paquete recibido» → Revisar un paquete. | sin marca |
| Cuentas con varios roles | la unión, sin repetir | — |

Cada paso dice, en una línea, **para qué** sirve, y tiene un enlace o botón que lo hace. Debajo, dos botones: «Abrir la demostración» (si puede, §4.5) y **«Empezar el recorrido guiado»**.

**Recorrido guiado nuevo, `RECORRIDO_PRIMER_PRESUPUESTO`** en `src/shell/recorrido.ts` (misma estructura que `RECORRIDO_AUDITAR`): «Armar su primer presupuesto». Tres pasos, uno por pantalla:
1. `inicio`: «Elija su carpeta y cree su proyecto», «Sabrá que terminó cuando el proyecto aparezca elegido en la cabecera».
2. `hoja`: «Describa el espacio y guarde la primera versión», «Sabrá que terminó cuando la hoja diga «Versión 001 guardada»» (el texto exacto lo fija la Hoja; se confirma al construir).
3. `tablero`: «Revise el total y la auditoría», «Sabrá que terminó cuando haya leído el total y los hallazgos».
El paso siguiente se enlaza solo si la pantalla existe, está migrada y la cuenta puede abrirla (regla ya usada por el Inicio). El recorrido se inicia solo con el botón (decisión 10 de la bitácora T2).

---

## 8. (F) Accesibilidad, letra grande y pantallas

- **Bienvenida y Recuperar acceso: páginas, no capas.** Un `h1`, `main`, etiquetas visibles, errores con `aria-invalid` + `aria-describedby`, un resumen de errores con `role="alert"` que recibe el foco al enviar con fallos
  (la primera vez; después solo anuncia). La política de contraseña es texto, no un tooltip, y se enlaza al campo con `aria-describedby`.
- **Diálogos (Carpetas…, Nuevo proyecto, confirmaciones):** `ComposedModal`/`Modal` de Carbon: foco atrapado, Esc cierra, el foco vuelve al botón que lo abrió, `aria-labelledby` al título; no se abren solos al cargar.
  La subida usa `SubidaArchivo` (ya accesible; teclado, `extensiones=[".db"]`) y un `status` que dice el nombre y el tamaño en MiB con la coma decimal de `formatoEsVe`.
- **Regiones vivas:** un `role="status"` siempre montado por pantalla/diálogo que anuncia «Creando…», «Carpeta creada: Obra_1.db», «Subiendo… 4,2 MiB» y los errores; el cuerpo de error además va en el `InlineNotification`.
- **Letra Normal/Grande/Muy grande (`--silice-escala-letra` 1, 1,25, 1,5):** todo en `rem`; formularios en una columna que pasa de dos a una por debajo de 1056 px con `grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr))`;
  `min-inline-size: 0` y `overflow-wrap: anywhere` en nombres de carpeta/proyecto largos; `Toggletip` con ancho `max-inline-size: min(24rem, 90vw)`; la franja de §7.2 sin alto fijo. Prueba de estilos como `estilosPlano.test.ts` (F-estilos).
- **1366×768 y 1056 px:** `scrollWidth <= clientWidth` en la bienvenida, el diálogo de carpetas, el de proyecto, el Inicio con «Primeros pasos» y el glosario, con las tres letras (auditoría visual BCP-10).
- **Teclado y lector:** orden de tabulación = orden visual; el botón «Carpetas…» y «Nuevo proyecto» están en la cabecera tras su selector; `Toggletip` alcanzable; ningún atajo propio. Nombres accesibles distintos
  («Nuevo proyecto» ≠ «Nueva carpeta de trabajo»). Color nunca solo: los pasos hechos llevan ícono `Checkmark` y la palabra «Hecho».
- **Español con tildes** en todo literal; los mensajes de `seguridad/cuentas.py` ya las llevan. Los de la clásica sin tilde (`vacio`) se reproducen con tilde (DV-BCP-3).
- **Sin animación decorativa** (DESIGN.md); solo las transiciones de componentes Carbon.

---

## 9. Contrato de API

Reglas comunes: respuestas con `Cache-Control: no-store` (`RutaSinCache`); 422 sin eco (`RutaSinEco`) con mensaje fijo por ruta; ningún `float`; sin rutas absolutas ni SQL en los errores;
CSRF/Origin por `exigir_clave_o_sesion` salvo en las dos públicas (donde se exige `Origin` a mano).

| Id | Método y ruta | Acceso | Éxito | Errores |
|---|---|---|---|---|
| P0 | `GET /v1/primer-arranque` | pública, solo propio equipo | 200 `{sin_cuentas, archivo_presente, modo, politica}` | 403 equipo remoto |
| P1 | `POST /v1/primer-arranque/reclamo` | pública, solo propio equipo, `Origin` obligatorio | 201 `SesionRespuesta` + cookie | 401 código no válido o ya usado; 403 origen/equipo; 422 forma (mensaje fijo o política); 423 bloqueo 15 min; 429 `Retry-After`; 503 base |
| C0 | `GET /v1/casos/actual` | cualquier rol con sesión / clave | 200 resumen (§4.6) | 401/403; 503 |
| C1 | `POST /v1/casos` `{nombre}` | `CAMBIAR_CASO` | 201 `CasoRespuesta` | 403; 409 existe / tope / clave de API; 422 forma; 503 |
| C2 | `POST /v1/casos/subida` multipart | `CAMBIAR_CASO` | 201 `CasoSubido` | 403; 409 existe / clave de API; 413; 422 no es de Sílice / más nueva / sin nombre; 503 |
| C3 | `POST /v1/casos/demostracion` | `EDITAR_HOJA` | 201 / 200 `CasoRespuesta` | 403; 409 clave de API; 503 hijo falló o plazo |
| J1 | `POST /v1/proyectos` | `EDITAR_HOJA` | 201 `ProyectoDelCasoRespuesta` | 403; 409 repetido; 422 vacío / moneda / tipo de obra; 503 |

`GET /v1/casos` y `POST /v1/casos/actual` no cambian. `POST /proyectos` (histórico) no cambia. En `docs/api.json` las rutas P0/P1/C0 a C3/J1 aparecen tras `scripts/exportar_openapi.py` (orquestador).

Mensajes fijos nuevos (todos con tildes; los de `cuentas` tal cual):

| Texto | Dónde |
|---|---|
| «Revise el usuario, el nombre y la contraseña: …» (el de política de `cuentas`) | P1, 422 |
| `cuentas.MENSAJE_CODIGO`, `MENSAJE_BLOQUEO`, `MENSAJE_FRENO` (de `api.rutas.sesion`), `equipo.MENSAJE_REMOTO`, `MENSAJE_ORIGEN` | P1 |
| «El archivo pasa de 20 MiB.» | C2, 413 (el del middleware dice «…excede el máximo de 20 MiB.»; el front muestra el suyo) |
| «El archivo no es una carpeta de trabajo de Sílice válida: no se guardó.» | C2, C3, 422 |
| «Ya hay 100 carpetas de trabajo: retire alguna antes de crear otra.» | C1, C2, C3, 409 |
| «No se pudo preparar la demostración. Pruebe de nuevo; si sigue, avise al administrador.» | C3, 503 |

---

## 10. Pruebas por capa y criterios de aceptación

### 10.1 Principios

TDD con rojo visto; oráculos a mano desde `seguridad/cuentas.py` (constantes), la ERS, los manuales y la clásica, nunca del código bajo prueba; `-W error`, cero omitidas; **ninguna prueba abre la red ni usa libros o
nombres reales**; datos ficticios («Contratista Demo, C.A.», `ana`, `rita`, `admin` de `tests/fixtures/sesion_web.py`). La suite completa no se corre en sub-rebanadas.

### 10.2 Backend (ids BCP-B*)

| Id | Qué prueba | Oráculo |
|---|---|---|
| B1 | `asegurar_codigo`: base vacía → emite y crea `codigo_instalacion.txt`; segunda llamada no hace nada; con cuentas no emite; con un código vigente no emite otro | a mano: 1 fila `CodigoInstalacion`, archivo de 24 caracteres (`XXXX-…` 5 grupos de 4) + `\n` |
| B2 | `GET /v1/primer-arranque`: claves exactas del JSON; `no-store`; sin cuentas → `sin_cuentas=true`; tras crear una → `false`; IP remota (`cliente(app, ip="192.168.1.50")`) → 403 `MENSAJE_REMOTO`; no contiene ruta absoluta ni el código | conjunto literal de claves |
| B3 | reclamo feliz: 201, cookie `silice_sesion`, cuerpo = forma de `SesionRespuesta`, roles `["administrador"]`, `acciones` de la matriz, el archivo del código se borró, la huella quedó `usado`, `evento_acceso` tipo `alta` | matriz de `permisos.PERMISOS` escrita a mano |
| B4 | `tambien_arma=true` → roles `["arma","administrador"]` (orden de `Rol`: arma, revisa, administrador) y acciones de ambos; con restablecimiento no cambia a otras cuentas | literal |
| B5 | contraseña de 9 caracteres → 422 con el texto de política exacto («La contraseña debe tener al menos 10 caracteres.»); de 129 → «admite hasta 128»; igual al usuario; «password123» → «demasiado común»; usuario `AB` → «3 a 40 caracteres»; **y con código inválido + contraseña débil el mensaje es el de política, igual que con código válido** (H4) | textos de `cuentas.py` copiados a mano |
| B6 | código mal escrito (minúsculas, sin guiones, con espacios) se acepta; código con un carácter cambiado → 401 `MENSAJE_CODIGO`; código ya usado → 401 igual; con cuentas y sin restablecimiento → 401 igual | `_huella_codigo` normaliza: construcción a mano |
| B7 | cuerpo inválido (contraseña de 500 caracteres, falta de campo, tipo erróneo): 422 `{"detalle": <fijo>}` que **no contiene** la contraseña ni el código enviados | búsqueda de la cadena |
| B8 | `Origin` ajeno → 403; **sin `Origin` → 403** (a diferencia de `POST /v1/sesion`); `Host` no permitido → lo corta `TrustedHostMiddleware` | `MENSAJE_ORIGEN` |
| B9 | tras el reclamo, `GET /v1/sesion` con la cookie → 200; una cookie previa del navegador se cerró (`sesion.cerrada`); `caso_web.elegido` de la ficha anterior olvidado | consulta a `sesion` |
| B10 | `restablecer`: con cuentas y código de restablecimiento, login existente `ana` (arma) → queda con `arma,administrador`, activa, sin `debe_cambiar_clave`, sesiones cerradas; login nuevo → administrador; el código de «primera vez» con cuentas → 401 | documenta H6; D-6 |
| B11 | `crear_caso` por la ruta: 201, el archivo existe en `casos/`, es SQLite en `head`; el nombre final es el saneado; repetido (incluido `X.DB` frente a `x.db`) → 409; tope de 100 → 409 | `leer_estado` literal; `alembic_version` = `head` |
| B12 | permisos de cada ruta nueva por rol y sin sesión, sin CSRF, con clave de API (§10.3) | matriz S6 |
| B13 | `subida` feliz con una base mínima generada por `preparar_base` en cuarentena: 201; aparece en `GET /v1/casos`; cuarentena vacía; `Content-Length` correcto | árbol de carpetas antes/después |
| B14 | `subida` de una base 0.5.0 sin `alembic_version` (fixture ya existente en `tests/fixtures/bases`): 201, `aviso` no nulo, existe un juego en `respaldos/`, la base queda en `head`, sus presupuestos recargan con el total literal de su ficha | ficha del fixture |
| B15 | `subida` rechazada **no deja rastro**: texto, cabecera falsa, SQLite de otra aplicación (tabla `moz_places`), con `TRIGGER`, con `VIEW`, con tabla virtual, `integrity_check` roto (bytes del medio alterados), `alembic_version='zzz'`, de 20 MiB + 1 byte: cada caso devuelve su estado (422/413) y el **árbol completo** de `<datos>` es idéntico (nombres, tamaños) | `os.walk` antes y después |
| B16 | demostración: con el hijo sustituido por un doble que escribe una base mínima (no se ejecuta `scripts` en la prueba de la API); 201 y luego 200 (idempotente); hijo que falla o excede plazo → 503, sin `demostracion.db` ni temporales; `ana` 201, `admin` 403, `rita` 403 | `subprocess` simulado; conteo de archivos |
| B17 | demostración **real** (marcada de integración, una sola vez): la base resultante tiene el proyecto `DEMO` y el presupuesto `DEMO-001` y `estado.partidas == 8` (5 `LB-*` + 3 `DEMO-*`, `seed_demo.py`) | docstring de `seed_demo.py`; confirmar al construir (§15) |
| B18 | `GET /v1/casos/actual`: base vacía → `partidas=0`; con la demostración → conteos; no crea el archivo; no emite DDL (conexión de solo lectura); sin ruta absoluta en `ubicacion` | conteos a mano |
| B19 | `POST /v1/proyectos`: 201 con la forma de un elemento de la lista; moneda `Bs` queda en `moneda_proyecto` con `responsable = "Ana Pérez <ana>"`; vacío («   ») 422 con el texto; «Torre B» y «  torre   b » → 409 con «Torre B» en el mensaje; moneda «EUR» 422; dominio «x» 422; dos peticiones simultáneas con el mismo nombre → 201 y 409 | textos de `proyectos.py` con tildes (DV-BCP-3) |
| B20 | `POST /v1/proyectos` crea en el caso de la **ficha** (no en el del proceso): con `ana` en otra carpeta, el proyecto aparece solo allí | dos bases de prueba |
| B21 | arquitectura: `api/` no importa `scripts`, `ui`, `tests`; `aplicacion/primer_arranque.py` y `casos.py` no importan `api`, `streamlit`, `scripts`; importar la API no carga `scripts` ni `tests` (la prueba existente `test_importar_la_api_no_carga_scripts_tests_ni_ui` sigue verde) | guardias existentes |
| B22 | `core/` intacto (`git diff -- core/` vacío) | `git diff` |
| B23 | `lifespan`: al arrancar sin cuentas se emite el código; un fallo al emitir no impide arrancar (se registra) | a mano |

### 10.3 Seguridad (ids S*)

| Id | Qué prueba | Oráculo |
|---|---|---|
| **S1** | **Fuerza bruta del código.** Cinco `POST` con códigos errados → los cinco 401 (el quinto bloquea); el sexto, **con el código correcto**, da 423 `MENSAJE_BLOQUEO` y **no crea cuenta**; con el reloj avanzado 15 min (`ahora` inyectado) el código correcto funciona; 4 fallos no bloquean | `FALLOS_PARA_BLOQUEAR = 5`, `BLOQUEO = 15 min`: literales de la prueba |
| **S2** | **Freno global.** 20 fallos de login con 20 usuarios inexistentes distintos (cada uno con su contador) y luego un reclamo → 429, `Retry-After: 2`, cuerpo `MENSAJE_FRENO`, y **no se calculó ningún hash** (el contador de verificaciones no sube); el 22.º fallo → `Retry-After: 4` | `FRENO_FALLOS = 20`, espera `2**exceso`: 2 con exceso 1, 4 con exceso 2 |
| **S3** | **Carrera de dos reclamos.** Dos hilos con barrera, mismo código y logins distintos (`uno`, `dos`): exactamente un 201 y un 401; `SELECT count(*) FROM usuario` = 1; una sola fila `usado` fijada. **Debe fallar antes del arreglo** (rojo visto, H3). Variante con el mismo login: no hay 500 | conteos SQL a mano |
| **S4** | **Política de contraseña** completa (B5). **S4b:** el mensaje de forma no distingue código bueno de malo | igualdad de respuestas |
| **S5** | **Traversal y nombres hostiles, en crear y subir.** Lista literal: `..\x`, `../x`, `a/b`, `a\b`, `C:\x`, `\\srv\share\x`, `//srv/x`, `con`, `NUL.db`, `COM1`, `x:y`, `x.db::$DATA`, `   `, `....`, `.`, `x.`, un nombre de 500 caracteres, `Ñandú`, `x<y>`, `%2e%2e/x`: el resultado de cada uno es 201 con nombre saneado **dentro** de `casos/`, o 422; el árbol fuera de `casos/` es idéntico; nunca existe un archivo cuyo `resolve()` salga de `casos/`; el nombre del archivo subido (`filename` del multipart) con `..\..\evil.db` crea solo `casos/evil.db` | `Path.resolve().is_relative_to` sobre el árbol; lista literal |
| **S6** | **Subida hostil** (B15) más: dos subidas simultáneas del mismo nombre → 201 y 409; cuerpo multipart sin parte `archivo` → 422; parte `archivo` repetida → 422; `Content-Length` mentiroso (declara 10, envía 21 MiB) → 413 sin escribir; cuarentena con basura de más de 1 h se purga al arrancar | hilos con barrera; árbol |
| **S7** | **Secretos:** el código, la contraseña y la ficha **no** aparecen en: ningún cuerpo (éxito, 401, 422, 423, 429), `docs/api.json`, `evento_acceso`, `caplog` a nivel DEBUG, `localStorage` simulado del front, la URL; el 422 no repite el campo | búsqueda de las cadenas literales de la prueba |
| **S8** | **Acceso a las rutas:** `GET` y `POST` de P0/P1 desde IP remota → 403; sin `Origin` → 403; matriz de roles de C0-C3 y J1: sin sesión 401; `rita` (revisa): C1 403, C2 403, C3 403, J1 403; `ana` (arma): C1 201, C2 201, C3 201, J1 201; `admin`: C1 201, C2 201, C3 **403**, J1 **403**; contraseña temporal pendiente → 403 `MENSAJE_CAMBIAR_CLAVE`; sin `X-Silice-CSRF` en los `POST` → 403; clave de API → C1, C2, C3 409 y J1 201 | `permisos.PERMISOS` a mano; `tests/fixtures/sesion_web.py` |
| **S9** | **Todo o nada y limpieza:** un fallo en `preparar_base` (inyectado) tras crear → el archivo se elimina; un fallo en `os.rename` → no queda temporal; un fallo del hijo → no queda cuarentena | árbol |

### 10.4 Frontend (ids BCP-F*)

| Id | Qué prueba |
|---|---|
| F1 | `App`: sin sesión pide `GET /v1/primer-arranque`; `sin_cuentas=true` → Bienvenida; `false` o 403/500 → Entrar (un fallo del estado nunca pinta `alert`); «Perdí el acceso…» abre Recuperar y vuelve |
| F2 | Bienvenida: campos y etiquetas; contador «N de 10»; las dos contraseñas distintas → «Las dos contraseñas no coinciden.» sin llamar a la API; la política de §3.5 está siempre presente; `autocomplete` correctos |
| F3 | Reclamo: manda `{codigo, usuario, nombre, contrasena, tambien_arma}` (nunca `repetida`); 401/423/422 muestran el `detalle` tal cual; 429 deshabilita el botón `Retry-After` s y lo anuncia; el código se borra del estado tras un error; éxito → `fijarCsrf` y marco |
| F4 | Ni el código ni la contraseña quedan en `localStorage`, `sessionStorage`, `document.title`, la URL ni el DOM tras el envío (`value` limpio) |
| F5 | Diálogo «Carpetas…»: solo con `cambiar_caso`; pestañas por teclado; Crear → `POST /v1/casos` y luego `POST /actual`; muestra el nombre final saneado; 409 «ya existe» en línea; foco devuelto al cerrar |
| F6 | Subir: solo `.db`; muestra nombre y MiB; 413, 422 y 409 con su texto; progreso anunciado; un archivo rechazado no cambia la lista |
| F7 | Demostración: visible solo con `editar_hoja` (si no, explica por qué); 201 y 200 abren la carpeta; el aviso «Datos inventados» |
| F8 | Cambiar de carpeta con borradores (`GET /v1/hoja/borradores` con `cambios>0`): diálogo con N, «Quedarme» no cambia, «Cambiar y descartar» llama `POST /actual`; sin borradores cambia directo; «Salir» igual |
| F9 | El selector vuelve a pedir `GET /v1/casos` al abrirse y tras crear; carpeta nueva visible |
| F10 | Nuevo proyecto: solo con `editar_hoja`; moneda sin valor por defecto; vacío y repetido muestran los mensajes; éxito → recarga la lista y **elige** el proyecto nuevo |
| F11 | Proyecto sin versión: rótulo «(sin versión guardada)» y estado vacío de la Hoja con el texto de §5.2 |
| F12 | «Primeros pasos»: `pasosDeInicio` (prueba pura) para cada rol y estado: carpeta vacía; con proyecto sin versión; con versión; administrador sin y con otra cuenta; sin datos (la API falló) → el bloque no se pinta ni pinta `alert` |
| F13 | `AyudaDePagina`: todo `PaginaDef` tiene `queHace`; todo `index.tsx` migrado lo monta bajo el único `h1`; el texto sale del registro |
| F14 | Glosario: cada término de §7.4 con `id`; `Termino` abre y cierra con teclado, Esc devuelve el foco; sin `title` como único portador |
| F15 | Toggletips de los selectores con su `aria-label`; la franja de §7.2 solo con pasos pendientes |
| F16 | Estilos (como `estilosPlano.test.ts`): sin `px` en tamaños de texto, `min-inline-size: 0`, `overflow-wrap: anywhere`, `auto-fit/minmax(min(100%, …))`, franja sin alto fijo |
| F17 | `F-vocab`: ningún literal visible usa «Caso»/«caso» donde corresponde «carpeta de trabajo» (lista de excepciones: identificadores y rutas) |
| F18 | Montos/`Number()`: ninguno de los archivos nuevos usa `Number(`, `parseFloat` ni `toFixed` salvo `Number(Retry-After)` del cliente existente (la interfaz no calcula) |
| F19 | Regresión: `Shell.test.tsx`, `Selectores.test.tsx`, `Cabecera.test.tsx`, `Inicio.test.tsx`, `App.test.tsx`, `Entrar.test.tsx` siguen verdes con los selectores nuevos y las dos peticiones nuevas del Shell (`/v1/casos/actual`, `/v1/hoja/borradores`) simuladas con un ayudante común `respuestasDeBienvenida` |

### 10.5 Auditoría visual (BCP-10)

`scripts/auditoria_visual_bienvenida.py` (solo lectura del repositorio; navegador con perfil propio en el scratchpad; servidor en `127.0.0.1` y cierre por PID; **base de datos y carpeta de datos temporales**, instalación vacía): 1366×768 y 1056 px, letra Normal, Grande y Muy grande,
`scrollWidth <= clientWidth` en: Bienvenida (con y sin `archivo_presente`), Recuperar, Entrar, Inicio con «Primeros pasos» para cada rol, diálogo de Carpetas (tres pestañas), diálogo de Proyecto, estado vacío de la Hoja, Glosario. Solo teclado; foco visible;
un `h1` por pantalla. Además, **la prueba de extremo a extremo con una base vacía** (lo que el retiro dejó como deuda): arrancar sin cuentas → código en el archivo → bienvenida → reclamo → Inicio → crear carpeta → crear proyecto →
Hoja «sin versión».

### 10.6 Criterios de aceptación (P-n)

(No son los P de la Hoja ni los del asistente.)

| Id | Criterio | Oráculo | Sub-rebanada |
|---|---|---|---|
| P-1 | Una instalación sin cuentas emite el código al arrancar (lanzador y API) y es idempotente | B1, B23 | BCP-1 |
| P-2 | `GET /v1/primer-arranque` dice solo `sin_cuentas`, `archivo_presente`, `modo` y `politica`, `no-store`, solo desde el propio equipo | B2, S8 | BCP-1 |
| P-3 | El reclamo crea el primer administrador, abre la sesión, borra el archivo y no devuelve ni registra el código | B3, S7 | BCP-1 |
| P-4 | Cinco códigos errados bloquean 15 min incluso al código correcto; el freno global responde 429 con `Retry-After` | S1, S2 | BCP-1 |
| P-5 | **Dos reclamos simultáneos no crean dos administradores** | S3 | BCP-1 |
| P-6 | Un código bueno y uno malo con datos mal formados responden igual | B5, S4b | BCP-1 |
| P-7 | El código de restablecimiento funciona con cuentas creadas y se explica; sin él, la respuesta no revela si hay cuentas | B6, B10 | BCP-1 |
| P-8 | Crear una carpeta usa las reglas de nombre de la clásica y nunca sale de `casos/` | B11, S5 | BCP-2 |
| P-9 | Una subida válida se valida, se respalda, se migra y aparece completa; una rechazada no deja ni un byte en `<datos>` | B13, B14, B15, S6 | BCP-2 |
| P-10 | La demostración es una carpeta propia, idempotente, creada fuera del proceso de la API y sin tocar la carpeta abierta | B16, B17 | BCP-2 |
| P-11 | Permisos de cada ruta por rol, CSRF, Origin y clave de API | S8, B12 | BCP-2, BCP-3 |
| P-12 | `GET /v1/casos/actual` resume la carpeta en solo lectura y sin rutas absolutas | B18 | BCP-2 |
| P-13 | Crear un proyecto: nombre único sin distinguir mayúsculas, moneda elegida, responsable humano, en el caso de la ficha | B19, B20 | BCP-3 |
| P-14 | La bienvenida es una página accesible con la política explicada y sin guardar secretos en el navegador | F1 a F4 | BCP-4 |
| P-15 | Crear, subir y abrir la demostración desde un diálogo accesible; cambiar de carpeta avisa de los borradores | F5 a F9 | BCP-5 |
| P-16 | Crear un proyecto lo elige y la Hoja dice qué hacer sin versión | F10, F11 | BCP-6 |
| P-17 | «Primeros pasos» sale de los datos, por rol, y no guarda nada | F12 | BCP-7 |
| P-18 | Cada pantalla tiene su línea de «qué hace», el glosario y los «?» | F13 a F15 | BCP-8 |
| P-19 | La interfaz usa una sola palabra por idea | F17 | BCP-9 |
| P-20 | 1366×768 y 1056 px, tres letras, sin desplazamiento horizontal, solo teclado; extremo a extremo con base vacía | §10.5 | BCP-10 |
| P-21 | `git diff <base>..HEAD -- core` vacío; guardias de arquitectura verdes | B21, B22 | todas |
| P-22 | Ninguna prueba abre la red | revisión | todas |

---

## 11. Sub-rebanadas, dependencias y paralelismo

| Sub-rebanada | Hace | Archivos suyos | Depende de | Pruebas |
|---|---|---|---|---|
| **BCP-1** backend: primer arranque | `aplicacion/primer_arranque.py`, `api/rutas/primer_arranque.py` (+ esquemas), `cuentas._tomar_escritura` y `ademas_arma`, `operacion` orden `restablecer-administrador`, gancho del lanzador, `scripts/restablecer_administrador.py` como envoltura. **Abre con S3 en rojo** | `aplicacion/primer_arranque.py`, `api/rutas/primer_arranque.py`, `api/esquemas_bienvenida.py`, `seguridad/cuentas.py` (2 puntos), `operacion/lanzador.py` (4 líneas), `operacion/ordenes_100.py`, `scripts/restablecer_administrador.py`, `tests/unit/test_aplicacion_primer_arranque.py`, `tests/unit/test_api_primer_arranque*.py`, `docs/bitacora/2026-10-2x-bcp1-*` | **el retiro de Streamlit fusionado** y este diseño aprobado | B1 a B10, B21 a B23, S1 a S4, S7, S8; P-1 a P-7 |
| **BCP-2** backend: carpetas | `aplicacion/casos.py` (estado de solo lectura, crear, subir seguro, cerrojo, tope, purga de cuarentena), `operacion/demostracion.py` y `--salida`, `CasoYaExiste`, rutas C0 a C3 | `aplicacion/casos.py`, `operacion/demostracion.py`, `operacion/base_datos.py` (subclase), `operacion/ordenes_100.py` (`--salida`), `api/rutas/casos.py`, `tests/unit/test_aplicacion_casos.py`, `tests/unit/test_api_casos_*.py` | el retiro fusionado (necesita reconstruir `estado_caso`) | B11 a B18, S5, S6, S8, S9; P-8 a P-12 |
| **BCP-3** backend: proyectos | `crear_proyecto_en_sesion`, `POST /v1/proyectos` | `aplicacion/proyectos.py`, `api/rutas/proyectos.py`, `tests/unit/test_api_proyectos_crear.py` | independiente (puede ir en paralelo con BCP-1/2; mismo archivo `api/rutas/casos.py` no) | B19, B20; P-13 |
| **BCP-4** front: bienvenida y recuperar | `src/bienvenida/` (`Bienvenida`, `RecuperarAcceso`, `usePrimerArranque`), cambios en `App.tsx`, `useSesion.ts` y `Entrar.tsx` (enlace) | `frontend-desktop/src/bienvenida/**`, `src/App.tsx`, `src/sesion/*`, sus pruebas | solo el contrato de §9 (P0, P1) con `fetch` simulado: **puede empezar antes del retiro** | F1 a F4, F16 (parte); P-14 |
| **BCP-5** front: carpetas de trabajo | `src/shell/carpetas/` (diálogo con tres pestañas, confirmación de borradores), cambios en `Shell.tsx` y `Selectores.tsx` | `src/shell/carpetas/**`, `Shell.tsx`, `Selectores.tsx` y sus pruebas | contrato C0 a C3 y `GET /v1/hoja/borradores` (existe) | F5 a F9, F19; P-15 |
| **BCP-6** front: proyectos | diálogo «Nuevo proyecto», elegir el nuevo, rótulo «(sin versión guardada)», estado vacío de la Hoja | `src/shell/proyectos/**`, `Selectores.tsx`, **una línea de `src/paginas/hoja/index.tsx`** | contrato J1; BCP-5 (mismo `Selectores.tsx`: en orden) | F10, F11; P-16 |
| **BCP-7** front: primeros pasos y recorrido | `primerosPasos.ts`, bloque en `inicio/index.tsx`, `RECORRIDO_PRIMER_PRESUPUESTO` en `recorrido.ts` | `src/paginas/inicio/**`, `src/shell/recorrido.ts` y su prueba | BCP-5, BCP-6 y C0 | F12; P-17 |
| **BCP-8** front: ayuda | `src/ayuda/` (`AyudaDePagina`, `Termino`, `glosario.ts`), página `ayuda`, `queHace` en `rutas.ts` (**compartido**), Toggletips y franja, la línea `<AyudaDePagina />` en cada página | `src/ayuda/**`, `src/paginas/ayuda/**`, los `index.tsx` de las pantallas (una línea cada uno) | **el agente del autocompletado terminó** (comparte `componer`, `hoja`, `catalogo`); `rutas.ts` lo aplica el orquestador | F13 a F16; P-18 |
| **BCP-9** renombrado | «Caso» → término de D-1 en cadenas visibles, manuales y definiciones de la ERS; prueba `F-vocab` | `src/**` (cadenas), `docs/manual_usuario.md`, `docs/manual_instalacion.md`, **ERS (orquestador)** | **D-1 decidida** y BCP-8 | F17; P-19 |
| **BCP-10** integración y auditoría visual | `scripts/auditoria_visual_bienvenida.py`; extremo a extremo con base vacía; bitácora | `scripts/auditoria_visual_bienvenida.py`, `docs/bitacora/**` | BCP-1 a BCP-9 | §10.5; P-20 |
| **BCP-11** documentos | ERS (RF nuevos), manuales de usuario e instalación (quitar el «Estado provisional»), `DESIGN.md` («Texto»: vocabulario), `CHANGELOG.md` | los listados | todas | — |

**Orden y paralelismo**

```
(retiro fusionado) ──▶ BCP-1 ──▶ BCP-2 ──▶┐
                         BCP-3 ───────────┤
BCP-4 ─────────────────────────────────────┤
BCP-5 ──▶ BCP-6 ──▶ BCP-7 ─────────────────┼─▶ BCP-8 ─▶ BCP-9 (tras D-1) ─▶ BCP-10 ─▶ BCP-11
```

- **Backend y frontend en paralelo:** BCP-4 a BCP-7 trabajan contra el contrato de §9 con `fetch` simulado y **no prueban** que el front y el servidor coincidan: lo prueba BCP-10 (primera integración real). Si BCP-1 a BCP-3
  desvían el contrato lo anotan en `docs/bitacora/…-bcp-contrato-rutas.md` y avisan.
- BCP-1 → BCP-2 es secuencial (BCP-2 hereda el cerrojo y la cuarentena de BCP-1 solo en `<datos>`); BCP-3 es independiente. BCP-5 → BCP-6 → BCP-7 comparten `Selectores.tsx`/`Shell.tsx`/`inicio`: en orden. BCP-8 y BCP-9
  son las únicas que tocan pantallas ajenas y van **al final**.
- Cada sub-rebanada pasa implementador → árbitro antes de empezar la siguiente que dependa de ella. Un solo árbol; cada agente toca solo sus carpetas; los archivos compartidos los aplica el orquestador (§14).

### 11.1 Lo que este diseño no incluye

Borrar o renombrar carpetas de trabajo desde la interfaz; descargar una copia de la carpeta abierta (solo el respaldo del administrador); importar una carpeta desde otra de la misma instalación; cambiar la contraseña
desde la bienvenida (ya existe `POST /v1/sesion/contrasena`); contador regresivo de la sesión (D-8); tutorial en vídeo; traducción a otro idioma; el instalador (sí propone un acceso directo, D-7).

---

## 12. Riesgos

| # | Riesgo | Efecto | Mitigación | Estado |
|---|---|---|---|---|
| R-B1 | **Orden de fusión:** construir BCP-1/2 antes del retiro | `lanzador.py` y `ordenes_100.py` en conflicto; `estado_caso` desaparecido | `git merge-base --is-ancestor`; BCP-4 a BCP-7 pueden empezar | mitigado |
| R-B2 | H3 es una **deducción**: si `pysqlite`/SQLAlchemy toman el bloqueo antes de lo que creo, la carrera no existe | el arreglo sobraría (inocuo) | S3 se escribe primero y se mira: si no falla, se documenta y el arreglo queda como defensa | abierto hasta ver S3 |
| R-B3 | El proceso hijo de la demostración no existe en un producto sin `scripts/` | la demostración no se puede estrenar | `OpD` del instalador ya lo corre; el 503 dice qué hacer; prueba de producto en BCP-10 | declarado |
| R-B4 | Denegación local: gastar los 5 intentos del código | el administrador legítimo espera 15 min | aceptado; `restablecer-administrador` | declarado |
| R-B5 | El archivo del código lo lee otro proceso del mismo usuario de Windows | fuga de un código de un solo uso | es de un solo uso y caduca al canjearse; endurecer ACL fuera de alcance | declarado |
| R-B6 | Una subida de 20 MiB tarda: el cerrojo de creación bloquea otras creaciones | espera | `integrity_check` sobre 20 MiB es del orden de segundos; solo bloquea creaciones, no lecturas | por medir (BCP-10) |
| R-B7 | La validación de tablas núcleo rechaza una carpeta antigua legítima | el usuario no puede subir su archivo | condición «`alembic_version` conocida **o** tablas núcleo»; tablas extra no se rechazan; B14 cubre la 0.5.0 | por medir |
| R-B8 | `Toggletip` y `ComposedModal` de Carbon no se usan hoy en el repositorio | comportamiento de foco/jsdom distinto | F5/F14 prueban foco y Esc con Testing Library; si el componente no cumple, se usa un botón con `aria-expanded` propio | abierto |
| R-B9 | Cambiar el nombre «caso» deja textos mixtos | confusión | `F-vocab`, BCP-9 al final y un solo vocabulario (§7.1) | mitigado |
| R-B10 | El borrador muere con la sesión de 30 min | trabajo perdido | texto claro y aviso al vencer; mejora D-8 | declarado |
| R-B11 | Mensajes de la clásica sin tilde reaparecen | inconsistencia | DV-BCP-3; pruebas con la cadena con tilde | mitigado |
| R-B12 | Dos agentes tocan `Shell.tsx`/`Selectores.tsx`/`rutas.ts` | conflicto de fusión | orden de BCP-5→7; `rutas.ts` solo el orquestador; commits con `git commit <ruta>` | mitigado |
| R-B13 | El texto de ayuda sigue sin entenderse | RNF-10 no se cumple | D-9: validar con una persona sin experiencia (CP-07) antes de dar la sub-rebanada por cerrada | abierto |
| R-B14 | Un administrador reclama el restablecimiento sobre una cuenta `revisa` y la hace administradora | elevación por quien tiene el equipo | D-6; el script exige el equipo | declarado |

---

## 13. Decisiones abiertas (recomendación conservadora y reversible)

| Id | Decisión | Quién | Recomendación | Si se elige otra cosa |
|---|---|---|---|---|
| **D-1** | **Nombre de «caso» en la interfaz.** Opciones: (a) «Caso» (hoy); (b) «Espacio de trabajo» (la sugerencia): choca con «Espacio y metrajes»/«describa el espacio» de la Hoja; (c) **«Carpeta de trabajo»** (tus palabras): contiene varios proyectos, se entiende «dónde está lo mío»; flojea en «subir una carpeta» (es un archivo `.db`, y el diálogo lo dice); (d) «Archivo de trabajo»: concreto para subir/copiar, pero no sugiere que contiene varias obras | Eugenio | **(c) «Carpeta de trabajo»** en pantalla, manuales y definiciones de la ERS; la API, el código, la base y las pruebas siguen con `caso`. Costo medido: ≈21 archivos y 47 líneas del front, 45 líneas del manual de usuario, ≈57 de la ERS (hay 9 de «caso de uso» que no cambian) | (a): solo se añade la ayuda y no hay BCP-9; (b) o (d): mismo trabajo con otra palabra |
| **D-2** | ¿Ofrecer en la bienvenida «Usaré esta cuenta también para armar presupuestos»? (la primera cuenta es solo administrador y el administrador no arma, `permisos.py`) | Eugenio | **Sí, desmarcada**, con su explicación; una instalación de una sola persona la marca. Cambio: parámetro `ademas_arma` en `reclamar_instalacion` | no: el Inicio manda al administrador a crear otra cuenta con rol «Arma» antes de poder usar la Hoja |
| **D-3** | Permisos: crear y subir = `CAMBIAR_CASO` (arma y administrador, como la clásica); demostración = `EDITAR_HOJA` (solo arma, como la clásica). Consecuencia: el administrador sin rol «arma» crea y sube carpetas pero **no** puede estrenar la demostración ni crear proyectos | Eugenio | paridad con la clásica | dejar la demostración también al administrador (acción `CAMBIAR_CASO`), o restringir crear/subir a quien arma |
| **D-4** | Topes y plazos supuestos: subida 20 MiB (el global de la API); `MAXIMO_CARPETAS = 100`; cuarentena de 1 h; plazo de la demostración 120 s; nombre ≤ 80 caracteres | Eugenio | adoptarlos como supuestos y medir en BCP-10 | cambiar constantes en `aplicacion/casos.py` |
| **D-5** | La demostración es **una carpeta propia** (`demostracion.db`, nombre fijo, ficticia), no se siembra la carpeta abierta | Eugenio | sí (no puede dañar datos reales; el proceso hijo se aísla de ARQ-5) | sembrar la carpeta abierta cuando esté vacía exige mover `seed_demo` y `seed` a un paquete que la API pueda importar, y sacar `tests.fixtures` de `scripts/seed.py` |
| **D-6** | El código de **restablecimiento** reactiva y promueve a administrador a **cualquier** login existente (aunque fuera `arma` o `revisa`) y crea un administrador nuevo si no existe (H6) | Eugenio / tutor (es comportamiento de S3) | mantenerlo y documentarlo: quien corre el script ya tiene el equipo; restringirlo cambia `seguridad/cuentas.py` y sus pruebas | restringir a cuentas que ya eran administradoras: rechazo con mensaje fijo si el login existe y no lo es |
| **D-7** | Acceso directo «Sílice: recuperar acceso de administrador» en el menú Inicio de Windows y la orden `python -m operacion restablecer-administrador` (H7); si no, el producto no tiene forma de ejecutar el script | Eugenio | sí (una línea en `instalador/silice.iss`, un `[Icons]` más) | solo documentar la orden en el manual de instalación |
| **D-8** | Aviso «le quedan 5 minutos» antes de que venza la sesión (y con ella el borrador): exige que `GET /v1/sesion` informe el tiempo restante | Eugenio | **diferir**; por ahora, el texto de §6.2 y el aviso al vencer | adelantarlo: un campo `vence_en_s` en `SesionRespuesta` y un temporizador accesible en el front |
| **D-9** | Los textos de ayuda (§3.5, §7.2 a §7.6) los valida una **persona sin experiencia** (la prueba CP-07 de RNF-10) antes de cerrar BCP-4 y BCP-8 | Eugenio | sí: una persona real, 20 minutos con el guion de `guion_prueba_arenia.md`; el redactor ajusta | cerrar con la revisión del árbitro y dejar RNF-10 pendiente |

Decisiones de ingeniería ya tomadas: el código se emite en el arranque (nunca desde una petición); la forma se valida antes del código; `Origin` obligatorio en el reclamo; solo el propio equipo; cuarentena y renombrado atómico en
las subidas; proceso hijo para la demostración; cerrojo por creación; `POST /v1/proyectos` sobre la sesión de la ficha; «Primeros pasos» derivado de datos y sin almacenamiento del navegador; la línea de ayuda dentro de cada página y no en el Shell.

### 13.1 Diferencias deliberadas con Streamlit

| # | Diferencia | Motivo |
|---|---|---|
| DV-BCP-1 | El código se emite al arrancar, no al pintar la pantalla de acceso | una petición `GET` no debe escribir; el lanzador debe tener el archivo antes de imprimirlo (H1) |
| DV-BCP-2 | El reclamo valida usuario y contraseña **antes** del código, y exige `Origin` | H4; es una ruta pública que crea el máximo rol |
| DV-BCP-3 | Los mensajes de la clásica sin tilde («vacio») salen con tilde | regla de DESIGN.md/D1 |
| DV-BCP-4 | La subida pasa por cuarentena, `integrity_check` y rechazo de disparadores/vistas | H9 |
| DV-BCP-5 | La demostración es una carpeta propia, no la siembra del caso abierto vacío | D-5 |
| DV-BCP-6 | Crear y abrir son dos pasos de API; subir acepta un nombre distinto del archivo | el 409 por nombre repetido de la clásica obligaba a renombrar fuera |
| DV-BCP-7 | Cambiar de carpeta confirma si hay borradores | H12 |
| DV-BCP-8 | La moneda del proyecto se elige en un diálogo y el responsable es la cuenta | UC-01 paso 1 y RF-82 |
| DV-BCP-9 | El reclamo abre la sesión y entra al marco sin pantalla intermedia (Streamlit hacía `_iniciar` y `st.rerun`) | misma conducta |

---

## 14. Texto exacto para los archivos compartidos (lo aplica el orquestador)

**`api/main.py`**

```python
from api.rutas import primer_arranque
...
app.include_router(primer_arranque.router)   # P0 y P1 (públicas, solo propio equipo)
```
y, junto a `app = FastAPI(`, un `lifespan` (hoy no existe: `grep lifespan api/main.py` sin resultados):
```python
@asynccontextmanager
async def _arranque(_: FastAPI):
    try:
        with sesion_de_instalacion() as sesion:
            primer_arranque.asegurar_codigo(sesion, config.carpeta_datos(), datetime.now())
        casos_aplicacion.purgar_cuarentena()
    except Exception:  # no impide servir; el acceso normal sigue
        logging.getLogger("silice.api").exception("no se pudo preparar el primer arranque")
    yield
```
(`app = FastAPI(..., lifespan=_arranque)`; si el gancho de apagado del asistente de la Hoja ya añade un `lifespan`, se componen en uno.) Las rutas C0 a C3 y J1 viven en `casos.router` y `proyectos.router`, ya incluidos.

**`tests/unit/test_api_acceso_por_ruta.py`** (tabla escrita a mano; filas nuevas)

| Ruta | Sin clave ni sesión | Con sesión `arma` | `revisa` | `administrador` |
|---|---|---|---|---|
| `GET /v1/primer-arranque` | 200 (solo propio equipo) | 200 | 200 | 200 |
| `POST /v1/primer-arranque/reclamo` | 401/422 según cuerpo (pública, solo propio equipo, `Origin` obligatorio) | igual | igual | igual |
| `GET /v1/casos/actual` | 401 | 200 | 200 | 200 |
| `POST /v1/casos` | 401 | 201 | 403 | 201 |
| `POST /v1/casos/subida` | 401 | 201 | 403 | 201 |
| `POST /v1/casos/demostracion` | 401 | 201/200 | 403 | 403 |
| `POST /v1/proyectos` | 401 | 201 | 403 | 403 |

**`tests/unit/test_arquitectura.py`:** ningún cambio de reglas; `aplicacion/primer_arranque.py` y `aplicacion/casos.py` quedan bajo las guardias existentes (no importan `api`, `streamlit`, `scripts`, `tests`). Si la guardia enumera módulos de `aplicacion/`, añadir esos dos.

**`frontend-desktop/src/shell/rutas.ts` y su prueba**

- `PaginaDef` gana `queHace: string` (obligatorio); cada página lleva el texto de §7.3.
- Nueva entrada (al final de «Trabajo», sin acción): `{ id: "ayuda", titulo: "Ayuda y glosario", seccion: "Trabajo", accion: null, queHace: "…", cargar: () => import("../paginas/ayuda") }`.
  Con ella, los conteos de `rutas.test.ts` pasan de 22 a 23 páginas y de 19 a 20 en modo entrega (recalcular, como se hizo con `historial`).
- `AREAS`: `ayuda` va en el grupo «Más» (`paginas: [..., "acerca", "ayuda"]`) y, además, un enlace «Ayuda y glosario» al pie del menú lateral.

**`docs/ERS.md`** (la numeración la asigna el orquestador contra el máximo vigente: RF-155, UC-30, RNF-28; los números de abajo son provisionales)

> **Enmienda de Sílice (bienvenida, carpetas de trabajo y ayuda):** se agregan RF-156 a RF-162 y RNF-29; se enmiendan UC-12, UC-21 y RF-63.
> - **RF-156** (UC-21): una instalación sin cuentas emite un código de instalación de un solo uso al arrancar, y la interfaz permite canjearlo, solo desde el propio equipo, para crear el primer administrador, con el mismo freno y bloqueo que el acceso; el código no se registra ni se devuelve. *Criterio:* cinco intentos errados bloquean quince minutos; dos canjes simultáneos crean una sola cuenta.
> - **RF-157** (UC-12): la interfaz permite crear una carpeta de trabajo con un nombre que no salga de la carpeta de casos. **RF-158:** permite subir un archivo `.db`, que se valida, se respalda, se migra y solo entonces aparece; un archivo rechazado no deja rastro.
> - **RF-159** (UC-12): la interfaz ofrece una carpeta de demostración ficticia que no altera ninguna carpeta existente.
> - **RF-160** (UC-01): crear un proyecto desde la interfaz elige la moneda, firma con la cuenta y queda elegido; un proyecto sin versión dice qué hacer.
> - **RF-161** (UC-15): la interfaz explica qué se guarda al instante y qué es un borrador, avisa al descartarlo (cambio de carpeta, salida) y declara cuándo se pierde.
> - **RF-162** (UC-12): cada pantalla dice en una línea qué hace; hay un glosario accesible; el Inicio de una instalación o carpeta nueva muestra los primeros pasos según el rol.
> - **RNF-29** (usabilidad): la ayuda se entiende sin formación previa (se mide con RNF-10).
> - **Terminología:** donde la ERS dice «caso» (la base de datos de trabajo) la interfaz y los manuales dicen «carpeta de trabajo» (D-1); «caso de uso» no cambia.

**`CHANGELOG.md`** (una línea por sub-rebanada, al cerrar): «Bienvenida de primera vez, carpetas de trabajo (crear, subir, demostración), proyectos nuevos, explicación de cómo se guarda y ayuda en lenguaje llano.»

**`docs/api.json`:** regenerar con `scripts/exportar_openapi.py` al cerrar BCP-1, BCP-2 y BCP-3.

**`package.json`:** sin cambios (Carbon ya incluye `Toggletip`, `ComposedModal` y `PasswordInput`).

---

## 15. Lo que no pude determinar

1. **H3 es lectura, no ejecución.** No corrí la carrera; la prueba S3 abre BCP-1 para verlo en rojo.
2. **El conjunto de «tablas núcleo» del caso** (B15, §4.4 paso 5): sale de `core.models` y `migraciones`; no abrí `migraciones/` para listarlo. La regla exacta (alembic conocida **o** tablas núcleo) se fija leyéndolo al construir BCP-2.
3. **El recuento de la demostración** (B17: 8 partidas) sale del docstring de `scripts/seed_demo.py` (5 `LB-*` y 3 `DEMO-*`); confirmarlo ejecutando `seed_demo` en la sub-rebanada.
4. **Qué mueve el retiro a `aplicacion/`:** vi `aplicacion/` y `operacion/` de la rama del retiro, pero no su `api/` ni su `frontend-desktop/`; si el retiro ya añadió algo parecido a `GET /v1/casos/actual` o a un estado de instalación, BCP-1/2 lo reutilizan. La cabeza que leí es `a86532d2`.
5. **Mensaje del 413 del middleware y el límite efectivo del archivo** (el multipart añade bytes): se fija midiendo en B15.
6. **`Toggletip`/`ComposedModal` de Carbon** no se usan aún en el repositorio; su comportamiento de foco con jsdom está por verificar (R-B8).
7. **Si `Hoja` ya muestra «Versión 001 guardada»** como texto fijo (paso 2 del recorrido nuevo): lo fija la Hoja; el texto del recorrido se ajusta al construir.
8. **La orden `restablecer-administrador`** y su acceso directo no existen; no comprobé si `instalador/silice.iss` admite otro `[Icons]` sin cambiar el manifiesto de huellas (`instalador/manifiesto.toml`).
9. **Los números de RF/RNF** de §14 son provisionales; la ERS vigente llega hasta RF-155, UC-30 y RNF-28.
10. **No leí `NORMAS.md` entero ni `docs/metodologia.md`:** los criterios del árbitro se aplicaron por el manual.
