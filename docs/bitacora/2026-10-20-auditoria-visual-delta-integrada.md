# Auditoría visual del delta sobre la rama integrada 647c67e (solo lectura)

> **Fecha:** 2026-10-20 · **Quién:** auditor visual (subagente), por encargo del orquestador del bloque B ·
> **Qué se auditó:** `647c67e` (rama `inc/ruta-s2-mig-adm-empresa`, que integra las correcciones VB-2 a VB-23 y lo de la
> otra sesión), extraído con `git archive` a una carpeta propia del scratchpad (`scratchpad/delta/arbol`), con
> `frontend-desktop/dist` compilado allí (`npm run build`, sobre una unión de directorio al `node_modules` de `s2m4`,
> quitada al terminar). Sin ediciones de código ni de pruebas.
> **Cómo:** servidor FastAPI propio en `127.0.0.1:8537` (`uv run --active --no-sync`, con `SILICE_DATOS`,
> `SILICE_USUARIO` y `SILICE_RESPALDOS` en `scratchpad/delta/datos/inst` y
> `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` fijados antes de arrancar; `api` se importó de la copia
> extraída, comprobado con `api.__file__`) y Chrome headless de perfil propio por CDP (`127.0.0.1:9837`), manejado con
> los scripts Node de las auditorías anteriores (adaptados). Viewport 1366×768 y 1056×768 (más 1055 y 1000 para el
> menú plegable). Por página se midió lo mismo que en el informe anterior (`2026-10-19-auditoria-visual-bloque-b.md`):
> `scrollWidth` contra `clientWidth`, radios, sombras, degradados, familias, `h1`, rayas, jerga, palabras sin tilde,
> cifras y `title`, regiones vivas, campos sin etiqueta, almacenamiento, consola y peticiones a otros hosts.
> **Entorno de Python:** se usó el `.venv` ya existente de `s2m4` (no se creó ninguno) porque el común
> (`TESIS\.venv`) no trae el extra `ia` (`keyring`) y sin él no se puede probar la clave del Asistente; con
> `--no-sync` no se tocó ese entorno.
> **Datos:** 100 % ficticios en `scratchpad/delta/datos` (nunca `data/`): cuentas `admin`, `ana` (arma), `rita`
> (revisa) y `tomas` de `tests/fixtures/sesion_web.py`; empresa «Contratista Demo, C.A.» (J-00000000-0) con clave de
> firma ficticia y una segunda empresa ficticia («Constructora Ficticia Dos, C.A.», J-00000001-0) solo para su
> `.silice-clave`; caso `silice.db` con `scripts/seed`, `seed_demo` (DEMO-001) y `generar_obra_control`
> (OBRA-GENERADA); caso `reajuste.db` con `tests/fixtures/reajuste_s1`; caso aparte `precios.db` con la serie de
> atípicos (1, 2, 4 … 256, 257), para que no cambie la lista vigente de Elaborar (VB-25); tres libros construidos con
> `tests/fixtures/libros_empresa.py` (`limpio`, `sin_equipos`, `varios_hallazgos`); paquetes `.silice` generados por
> Entregar y uno «alterado» con un dígito cambiado en `presupuesto.json`. Ningún libro real.
> **Capturas:** `scratchpad/delta/capturas/<página>_<ancho>/` (220 PNG; barridos de todas las páginas en
> `barrido_<cuenta>_<ancho>/` con su `.txt` y `medidas.json`).

## Resultado global

| Criterio (DESIGN.md / PRODUCT.md) | Resultado |
|---|---|
| Sin scroll horizontal a 1366 y a 1056 px | **Cumple** en las 21 páginas del menú con las tres cuentas (`scrollWidth` = `clientWidth`; 1351/1041 con barra vertical). Dentro de un contenedor: la tabla editable «Períodos» de Reajuste a 1056 (VD-11) y las pestañas de Administración a 1056 (VD-14). |
| Menú plegable | **Cumple**: fijo a 1056; a 1055 y 1000 el botón «Abrir el menú» abre la capa, el foco entra al menú y **Esc la cierra** devolviendo el foco al botón (VB-14 cerrado). |
| Esquinas rectas | **Cumple** salvo los `Tag` «instalado» de Acerca (16 px, VD-9) y el anillo de foco del navegador en tres controles (VD-4). |
| Sin sombras ni degradados | **Cumple**: solo los bordes internos de las pestañas, el anillo de Carbon y el halo de severidad del Libro; 0 degradados. |
| IBM Plex Sans (y Mono en códigos) | **Cumple**: únicas familias medidas; Mono en `RESUMEN!B13`, `L5`, `APU-01!F44` del Libro. |
| Un `h1` `heading-04` por página | **Cumple** en las 21 páginas y en «Entrar» (28 px, `cds--type-heading-04`); 0 encabezados dentro del menú (VB-15 cerrado). |
| Formato es-VE y exacto a un toque | **Cumple** en Elaborar, Historial, Tablero, Entregar, Revisar, Reajuste, Control (tablas) y Precios. Faltan: la nota de las opciones de recuperación (VD-1), el separador de miles de L9 (VB-8 parcial) y la fecha de Inicio (VD-3). |
| Montos tabulares | **Cumple** (`tabular-nums`, alineados a la derecha) en todas las tablas medidas. |
| Español con tildes, sin jerga | **Casi**: lo de VB-5, VB-11 y VB-17 está corregido; quedan VD-1 (códigos en mayúsculas en Control › Recuperación), los `title` con códigos (VD-5), «Dia 1» del Tablero (VD-8) y lo ya registrado como decisión del núcleo. |
| Sin rayas como adorno | **Cumple** (0 en todas). |
| El color nunca va solo / severidad con ícono | **Cumple**, también en las alertas de Control (VB-4 cerrado). |
| Morado solo para atípicos | **Cumple**: el ícono de «Advertencia» de ATIP-001 es `rgb(138, 63, 252)` con `title="0.390625"`; 0 elementos morados en el Tablero. |
| Cero errores de consola | **Cumple en lo que toca a la interfaz**: 0 excepciones de JavaScript y 0 403. Solo quedan los «Failed to load resource» que el navegador registra por respuestas 4xx que la interfaz maneja (VD-13). |
| Nada de red externa | **Cumple**: 0 peticiones a hosts distintos de `127.0.0.1` en todos los recorridos, incluido el Asistente de IA con clave registrada. |
| Ningún secreto en pantalla ni en el almacenamiento | **Cumple**: `localStorage` y `sessionStorage` vacíos en todas las páginas; cookie `silice_sesion` `HttpOnly` y `SameSite=Strict`; la clave de IA ficticia no aparece en el DOM tras registrarla (solo «…wxyz»); contraseñas `type=password` y vaciadas al enviar. |
| Teclado | **Cumple en lo esencial**: «Saltar al contenido» es el primer Tab tras cargar; foco visible de Carbon (2 px `#0f62fe` o anillo interno) en menú, pestañas, campos y botones; Shift+Tab recorre hacia atrás; sin trampas en las 21 páginas (45 Tab por página). Faltas: VD-2, VD-4 y VD-7. |
| Estados vacío, carga y error | **Cumple**: vacíos con instrucción («Todavía no hay empresas registradas», «No hay cambios de precio registrados con esos filtros»); carga con esqueleto (7 elementos con latencia de 1,5 s en Catálogo); 500 con `detalle` en Historial («No se pudo leer el historial / La base del caso está ocupada…») y conexión rechazada en Entregar («No se pudo hablar con el programa de Sílice…»). |
| Sesión expirada | **Cumple**: sin la cookie, al ir a Historial la API da 401 y aparece «Entrar» con «Su sesión venció. Entre de nuevo para seguir.», 0 filas; al recargar, solo «Entrar». |

## Estado de VB-2 a VB-23

| # | Estado | Medida o captura que lo prueba |
|---|---|---|
| VB-2 | **Cerrado** | Zona de soltar de **96 px** de alto: Inicio (ana y rita 96×1063 a 1366, 96×753 a 1056), Elaborar 96×445 (1366 y 1056), Revisar 96 (paquete y Excel, 1366 y 1056), Empresas registradas 96, Precios de la empresa 96 (1366 y 1056). |
| VB-3 | **Cerrado** | Columna «Número» con V-01 a V-04 (`control_1366/02_valuaciones.png`). |
| VB-4 | **Cerrado** | Severidad «Advertencia» con ícono (relleno `#f1c21b`) y «Sin evaluar» con ícono de información; descripción «retraso: SPI 0,9780» (`control_1366/04_alertas.png`). |
| VB-5 | **Cerrado en lo listado** | «EAC (índice BAC/CPI)», «Término por el índice (día hábil)», «Desvío de precio»; Reajuste con «Por partida», «Comprobación directa», «Ambos (escalatoria y comprobación)», componentes «Materiales / Equipos / Mano de obra», «Escriba «Serie del componente»: es obligatorio.» sin UC-18 y «El último período aún no cierra: … al 20/10/2026». Queda «(S1)» en la nota del desvío (decisión registrada) y la columna «Nota» de Recuperación (VD-1, no listada en VB-5). |
| VB-6 | **Cerrado** | «Total del presupuesto 1.166,91 USD» con «Valor exacto: 1166.913493900000000 USD»; tabla 0,90 / 242,64 / 217,41 con `title`; cómputo 0,896000 y 17,9200; plan «Día 1» a «Día 4»; «Resultado: No cumple» (1366 y 1056; `elaborar_1366/03_resultado.png`). |
| VB-7 | **Cerrado** | Detalle «Total del libro 4.876,56» y «Total según Sílice 5.055,52»; con Tab el Tooltip abre «Valor exacto: 4.876,56257» y Esc lo cierra (`historial_1366/03_tooltip_teclado_zoom.png`). El anillo de foco de ese botón es del navegador (VD-4). |
| VB-8 | **Parcial** | F1 ya en es-VE: «P.U. de 28,28375 … lo recalcula en 30,2121875 … mueve el total sin IVA en 154,28»; L6 «= 0,12 … (0,1) … -31,61 USD». Queda L9 con espacio como separador de miles: «suma 4 331,43 USD … es 4 203,93 USD», en el mismo detalle que «4.876,56» (`historial_1366/02_detalle_1.txt`). «curva de inversion» sigue sin tilde (núcleo, ya registrado). |
| VB-9 | **Cerrado** | Inicio sin ninguna respuesta ≥ 400 con admin, rita y ana; admin no ve «Audite un presupuesto» y lee «Quién audita los presupuestos…» (`marco_1366/inicio_admin.png`). Ver VD-10. |
| VB-10 | **Cerrado** | Tablas del resultado: 1078 px en un contenedor de 1078 a 1366 y 768 en 768 a 1056; cifras 15.300,00 / 16.000,00 / -700,00 y 18,00 / 18,82 / -0,82 (`reajuste_1366/05_resultado_completa.png`, `reajuste_1056/…`). |
| VB-11 | **Cerrado** | Componer «Comience por la cabecera (código y descripción) … o búsquelo … se calcula aquí automáticamente»; Precios «Fecha de evaluación», «Sin versión, el impacto…», «La referencia MaPreX en bolívares». |
| VB-12 | **Cerrado** | Enter en «Marcar como retirada»: el foco pasa a «Cancelar» dentro de `role=group` «Confirmar»; Enter en «Cancelar» lo devuelve a «Marcar como retirada» (`admin_1366/06_confirmar_retiro.png`). El mismo patrón falla en el Asistente (VD-2). |
| VB-13 | **Cerrado** | Tras «Calcular», el foco va al `h2` del resultado con `top` 56 px (cabecera fija hasta 48) a 1366 y 1056; con error, a la zona `role=alert` («Escriba «Fuente de la cláusula»: es obligatorio.») con `top` 688 dentro de 768. |
| VB-14 | **Cerrado** | A 1055 y 1000 px: Esc deja `aria-expanded=false` y el foco en «Abrir el menú». |
| VB-15 | **Cerrado** | 0 encabezados en el `nav`; `document.title` «Página · Sílice» en las 31 navegaciones medidas (Acerca: «Acerca de Sílice»); «Entrar» con `h1` de 28 px `heading-04` y título «Entrar · Sílice». |
| VB-16 | **Cerrado** | «6 advertencias» (Tablero y Entregar de OBRA-GENERADA), «3 advertencias» (DEMO-001); Precios «1 insumo no contrastable: 1 sin referencia MaPreX (Arena demo)», sin «()»; «Cumple» / «No cumple»; Revisar sin «CUMPLE». «INDICIO:» sigue en Reajuste (núcleo, decisión registrada). |
| VB-17 | **Cerrado** | Tabla del paquete alterado con «Precio unitario»; Excel de otro formato: «limpio.xlsx: falta la hoja 'Datos'»; la plantilla descargada de la propia pestaña da «Sin hallazgos.» (0 advertencias) y total 836,80 (`revisar_1366/03_excel_plantilla.png`). |
| VB-18 | **Cerrado en Administración** | 0 regiones `role=alert` vacías en sus pestañas; con la respuesta del Asistente interceptada (`falta_el_componente`) el aviso dice «Falta un componente opcional del asistente de IA en este equipo. Pídalo a quien instaló Sílice…» (`estados_1366/00_asistente_sin_componente.png`). Reajuste conserva 10 (deuda anotada); el resto de páginas en VD-6. |
| VB-19 | **Cerrado en lo listado** | Control en dd/mm/aaaa (valuaciones, «vigente desde 02/11/2026», «Corte 27/11/2026»), feriados «Feriados (fechas como 25/12/2026…)» y «31/02/2026» rechazado con el texto de la persona; Tablero «Versión GEN-001 del 02/11/2026»; Revisar «del 20/10/2026»; Historial e Histórico con `type=date`. Fuera de lo listado: Inicio en ISO (VD-3) y `title` de fechas en ISO (VD-5). |
| VB-20 | **Cerrado** | Selector de proyecto «OBRA-GENERADA» (sin id); Acerca «Al día (versión 3)» y «Al día (versión 9)». |
| VB-21 | **Cerrado** | «37,6 %», «39,1 %», «43,9 %», «56,60 %» en tablas y en las etiquetas SVG; `title` del total «Valor exacto: 95066.60006250 USD». |
| VB-22 | **Cerrado** | Tras revocar, «Marcar como retirada» y «Revocar» `disabled` con `aria-describedby` a «Esta clave ya está revocada: ningún paquete con ella verifica y no admite más cambios.» (`admin_1366/09_revocada.png`). |
| VB-23 | **Cerrado** | Campo `rgb(244, 244, 244)` sobre la capa `rgb(255, 255, 255)` (`barrido_admin_1056/administracion.png`). |
| VB-1 | Sigue igual (no se repite) | El paquete de DEMO-001 generado y firmado por Entregar da al revisarlo «No se pudo revisar el paquete / renglon 0.equipos: cifra fuera del patron estricto: '0.0833333333333333333333333333'» (422). El de OBRA-GENERADA sí se revisa. |

## Hallazgos nuevos

| # | Gravedad | Página | Hallazgo (evidencia) | Arreglo sugerido |
|---|---|---|---|---|
| VD-1 | **Importante** | Control de obra › Recuperación | La tabla «Opciones de recuperación» muestra en la columna «Nota» los códigos crudos **SUPUESTO_DECLARADO**, **DATO_DEL_CONTRATO** y **FUENTE_VERIFICADA**, «eta de cuadrillas» y cifras con punto («0.80», «0.50»), en las cuatro opciones. Medido: jerga `["SUPUESTO_DECLARADO","DATO_DEL_CONTRATO","FUENTE_VERIFICADA"]`; captura `control_1366/11_opciones.png`. Causa: `PestanasDeResultados.tsx:281` arma las columnas con `columnasDe(COLUMNAS_OPCIONES, …)` sin formateador para «Nota», mientras que `textoLlano` ya traduce esos códigos en Línea base y Alertas. No es regresión del delta: la pestaña no se recorrió en la pasada anterior. | Pasar «Nota» por `textoLlano` (y el es-VE de cifras solo en la ranura de la cifra, como `descripcionEsVe`); «eta» como «eficiencia»; prueba con la respuesta real de la API de opciones. |
| VD-2 | Pulido | Administración › Asistente de IA | «Olvidar la clave» abre su confirmación y **el foco cae a `body`** (medido tras Enter); el primer Tab lleva a «Sí, olvidar la clave», el botón destructivo; con Enter en «Cancelar» el foco vuelve a `body`. Es el defecto de VB-12, corregido en Empresas registradas pero no aquí. Captura `admin_1366/24_olvido_teclado.png`. | El mismo patrón que Empresas registradas: foco a «Cancelar» al abrir y de vuelta a «Olvidar la clave» al cancelar. |
| VD-3 | Pulido | Inicio › Últimas auditorías guardadas | La columna «Fecha» sale en ISO: «2026-10-20 14:39», mientras Historial muestra la misma auditoría como «20/10/2026 14:39». Medido en el texto de Inicio con rita y ana (`marco_1366/inicio_ana.png`). | El formateador de fecha y hora de Historial. |
| VD-4 | Pulido | Historial (detalle), Control, curvas | El botón del exacto que añadió VB-7 (`.silice-historial__monto-valor`) muestra el anillo de foco **del navegador**: `outline: auto 1px rgb(16, 16, 16)`, con esquinas redondeadas, no el de Carbon (2 px `#0f62fe`). Lo mismo los `<summary>` «Declarar una línea base» (Control) y «Ver los montos por período» (`CurvaPlanAvance`). Captura `historial_1366/03_tooltip_teclado_zoom.png`. | `:focus-visible { outline: 2px solid $focus; outline-offset: 2px }` en esos tres controles, o reusar el disparador del indicador del Libro (deuda ya anotada para el Tooltip). |
| VD-5 | Pulido | Control, Precios de la empresa | El `title` que da el exacto también se pone en rótulos y fechas, y al pasar el ratón muestra el valor interno: Parámetros «Umbral de SPI para error» → `spi_error`, «Supuesto declarado» → `SUPUESTO_DECLARADO`, «Qué es» → «… (AL-1)»; Alertas «Retraso (SPI)» → `AL-1`, umbral → «0.9000 (SUPUESTO_DECLARADO)»; atípicos «01/09/2026» → «2026-09-01». Medido con la lista de `[title]` de cada tabla. | Dejar el `title` solo en las cifras; en rótulos, códigos y fechas, ninguno o el texto llano. |
| VD-6 | Pulido | Componer, Escenarios, Actualizar precios, Elaborar, Histórico, Simulador, Precios, Índices, Historial, Libro, Existencias, Similares | Regiones `role=alert` vacías fuera de Administración: son los `cds--text-input__counter-alert` de cada `TextInput` de Carbon. Medido: Componer 9, Precios 5, Escenarios 5, Actualizar 4, Elaborar 3, Histórico 3, Simulador 3, Índices 2, Historial 2, Libro, Existencias y Similares 1 (Reajuste, 10, ya está anotado como deuda). | `CampoTexto` de `comun/` (el arreglo de VB-18) en esas páginas. |
| VD-7 | Pulido | Marco (recorrido), Inicio | El foco se pierde cuando la acción quita o reemplaza el control: «Terminar recorrido» con Enter deja el foco en `body` (el panel desaparece); «Auditar por mi cuenta» con Enter lleva al Libro con el foco en `body` (el siguiente Tab cae en el primer indicador, así que no hay trampa). | Llevar el foco al `h1` de la página nueva, o al primer enlace del menú al terminar el recorrido. |
| VD-8 | Pulido | Tablero (DEMO-001) | «Punto de equilibrio … se alcanza en **Dia 1** [DEMO-01-INST]» sin tilde, mientras el eje de la curva de la misma página dice «Día 1 [DEMO-01…». Relacionado con la decisión registrada («Dia» es convención del núcleo, `core/budget/curva.py:30`). Medido en `tablero_1366/demo.txt`. | Mostrar el rótulo del período con el mismo arreglo que ya usa el eje, o decidir junto con la decisión de Elaborar. |
| VD-9 | Pulido | Acerca de Sílice | Cada módulo lleva un `Tag` de Carbon verde «instalado» con `border-radius: 16px` (píldora, fondo `rgb(167, 240, 186)`): rompe «esquinas rectas» y «verde por ser positivo» de DESIGN.md. No cambió en el delta (la pasada anterior lo pasó por alto). | Texto llano («Instalado» / «No instalado») o `Tag` de radio 0 y color neutro. |
| VD-10 | Pulido | Inicio (rita, admin) | Tras VB-9 las secciones que la cuenta no puede usar se muestran vacías en vez de ocultarse: rita ve «Arenera: lo que requiere atención / Sin datos de la arenera para su cuenta»; admin, «Últimas auditorías guardadas / Sin historial de auditorías para su cuenta». | Omitir la sección cuando falta la acción (`operar_arenera`, `leer_proyecto`). |
| VD-11 | Pulido | Reajuste de precios › 2. Períodos | A 1056 px la tabla editable «Períodos» mide 770 px dentro de un contenedor de 736 (34 px de scroll horizontal interno). Las tablas del resultado sí caben (VB-10). | Ancho mínimo menor en las columnas de fecha o la papelera fuera de la tabla. |
| VD-12 | Informativo | Revisar un paquete (alterado) | En la fila «Precio unitario» la columna «Diferencia» dice 103,22, que es el efecto en el total, no la diferencia del P.U. (35,5971 − 35,0911 = 0,5060). Captura `revisar_1366/01_alterado.png`. | Rótulo «Efecto en el total», o la diferencia del campo y el efecto en otra columna. |
| VD-13 | Informativo | Entrar, Reajuste, Administración, Revisar | Los únicos mensajes de consola son «Failed to load resource» de respuestas 4xx que la interfaz maneja: 401 de `/v1/sesion` al abrir «Entrar», 422 de `/v1/reajuste/calcular` con datos inválidos, 400 de la huella equivocada y del tope 0, 422 del paquete DEMO-001 y del Excel de otro formato. 0 excepciones. | Ninguno (lo registra el navegador), o validar en el front antes de enviar. |
| VD-14 | Informativo | Administración a 1056 px | Las 7 pestañas no caben: «Instalación» y parte de «Accesos» quedan tras la flecha de desplazamiento de Carbon (`barrido_admin_1056/administracion.png`). Sin scroll de página. | Ninguno, o rótulos más cortos. |

## Qué se comprobó y cómo

- **Barrido de todas las páginas del menú** con las tres cuentas a 1366 y a 1056 (ana 17 páginas, rita 8, admin 6):
  captura, texto y `medidas.json` por página (`barrido_<cuenta>_<ancho>/`). La Hoja del proyecto no se auditó (solo
  aparece como «En la interfaz clásica»).
- **Historial** con 4 auditorías guardadas (3 del recorrido y 1 del Libro): lista, filtros `type=date`, los tres
  detalles (foco al `h2` del detalle), Tooltip del exacto por teclado y Esc, 1366 y 1056.
- **Recorrido «Auditar un libro»** (ana): Inicio → «Auditar con recorrido guiado» → Libro («Paso 2 de 3») → «Compruebe
  que quedó guardada» → Historial («Paso 3 de 3») → «Terminar recorrido» (con clic y con Enter).
- **Revisar un paquete** (rita): bueno (OBRA-GENERADA: «No verificado … Se audita igual», con «Guardar dictamen»),
  alterado («Alterado: presupuesto.json cambió después de firmarse», tabla «Precio unitario», **sin** formulario de
  dictamen), DEMO-001 (VB-1); pestaña «Presupuesto en Excel» por teclado (flecha y Enter), plantilla descargada (0
  hallazgos) y libro de otro formato; 1366 y 1056.
- **Entregar** (ana): DEMO-001 y OBRA-GENERADA generados y firmados con la clave ficticia («Paquete listo y firmado»,
  SHA-256), contraseña vaciada, «Descargar el paquete» a la carpeta temporal (`Page.setDownloadBehavior`).
- **Empresas registradas** (admin): leer `.silice-clave` sin guardar (0 registradas tras leer), huella equivocada
  («la huella corta son 20 caracteres…»), registrar, retirar y revocar con confirmación (foco medido), revocar sin
  motivo («Escriba el motivo…»), estado de la clave revocada.
- **Asistente de IA** (admin, almacén nulo): estado, configuración (tope 0 rechazado, 2,50 guardado), registrar una
  clave ficticia con contraseña de respaldo («Clave de IA registrada (…wxyz)», la clave no está en el DOM), olvidar con
  confirmación (foco medido), aviso del componente ausente con la respuesta interceptada. 0 peticiones fuera de
  `127.0.0.1`.
- **Inicio por áreas**: menú de 5 áreas (Inicio, Auditar, Crear, Producción, Más) más «Herramientas principales»
  según la cuenta; «Más» plegable con `aria-expanded`.
- **Precios de la empresa** (admin, caso `precios.db`): «Buscar variaciones atípicas de precio» → ATIP-001, 0,39 %
  con `title="0.390625"`, 01/09/2026 → 01/10/2026, «Advertencia» con ícono `rgb(138, 63, 252)`; 1366 y 1056.
- **Control de obra** (OBRA-GENERADA): las cinco pestañas a 1366 y 1056, feriados con fecha imposible, «Calcular
  opciones» de recuperación.
- **Reajuste** (caso `reajuste.db`, «Contrato S1»): los dos pasos con selectores de fecha, resultado (oráculos de
  `test_ui_reajuste`), dos errores de validación, foco tras calcular y tras el error, 1366 y 1056.
- **Elaborar con resultado** (ana): `data/samples/civil/tanquillas_y_zanja.csv` de la copia extraída (ejemplo
  versionado, solo leído), LB-01..LB-04, 1366 y 1056.
- **Teclado**: 45 Tab y 3 Shift+Tab por página en las 21 páginas, con el modo de foco de cada parada; «Saltar al
  contenido»; menú en capa a 1055 y 1000 con Esc; navegación por el menú con Enter.
- **Estados**: carga (latencia emulada), 500 con `detalle`, conexión rechazada, sesión expirada sin recargar y con
  recarga.

## Qué NO se pudo comprobar y por qué

- **Lector de pantalla real** (NVDA o Narrador): solo inspección de roles y regiones en el DOM.
- **Calendario nativo de los campos de fecha abierto**: en headless no se despliega; se comprobó `type=date`, el valor
  y el anillo de foco al entrar con Tab.
- **Paquete verificado (aviso verde)**: no se generó un paquete firmado por la segunda empresa ficticia; solo se
  vieron «No verificado» y «Alterado».
- **Guardar el dictamen y guardar el estudio de reajuste**: se vio el formulario, no se envió.
- **Rechazo de la clave de la propia empresa como ajena**: con una empresa ya registrada, el primer campo de archivo
  del panel era el del aviso de revocación y el intento quedó en «Solo se aceptan archivos .silice-revocacion»; no se
  repitió.
- **Asistente con el almacén de credenciales real de Windows**: a propósito no (almacén nulo); el aviso del componente
  ausente se vio interceptando la respuesta, porque el entorno usado sí trae el extra `ia`.
- **Entregar con generación a 1056 px**: a ese ancho solo se capturó el estado inicial del barrido.
- **Existencias, Índices del BCV, Escenarios, Partidas similares, Simulador, Actualizar precios y Catálogo**: solo el
  barrido de medidas y el recorrido de teclado, sin sus flujos.

## Limpieza

Servidor (PID 36532) y Chrome (PID 27760) cerrados por su PID con `taskkill /PID … /T /F`; puertos 8537 y 9837
libres. La unión `scratchpad/delta/arbol/frontend-desktop/node_modules` se quitó con `rmdir` sin seguirla; el
`node_modules` de `s2m4` sigue con sus 301 entradas. Datos, libros, paquetes, claves y capturas quedan solo en
`scratchpad/delta`; nada en `data/` (sin archivos modificados en las últimas horas) ni en el repositorio salvo este
informe.
