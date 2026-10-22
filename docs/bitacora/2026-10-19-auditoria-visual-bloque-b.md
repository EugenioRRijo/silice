# Auditoría visual del bloque B a 1366×768 y 1056 px (solo lectura)

> **Fecha:** 2026-10-19 · **Quién:** auditor visual (subagente), por encargo del orquestador del bloque B ·
> **Qué se auditó:** `inc/ruta-s2-mig-final-b` en `7fce6ca`, con `frontend-desktop/dist` recompilado (`npm run build`;
> el `dist` anterior era de las 17:10 y había fuentes más nuevas). Sin ediciones de código ni de pruebas.
> **Cómo:** servidor FastAPI propio en `127.0.0.1:8131` (`SILICE_DATOS`, `SILICE_USUARIO` y `SILICE_RESPALDOS` en una
> carpeta temporal del scratchpad) y Chrome headless de perfil propio por CDP (`127.0.0.1:9461`), manejado con un script
> Node 22 (WebSocket global). Viewport 1366×768 y 1056×768 (más 1055 para el menú plegable). Por página se midió:
> `scrollWidth` contra `clientWidth`, radios, sombras, degradados, familias tipográficas, `h1`/`h2`, rayas (—), jerga
> (expresión regular de códigos internos y `snake_case`), palabras frecuentes sin tilde, cifras (formato,
> `tabular-nums`, `title`), roles y regiones vivas, campos sin etiqueta, `localStorage`/`sessionStorage`, errores de
> consola (solo los posteriores al inicio de cada script) y toda petición a un host distinto de `127.0.0.1`.
> **Datos:** 100 % ficticios en la carpeta temporal (nunca `data/`): cuentas `admin`, `ana` (arma), `rita` (revisa) y
> `tomas` de `tests/fixtures/sesion_web.py`; empresa «Contratista Demo, C.A.» (J-00000000-0) con clave de firma generada
> ahí; una segunda empresa ficticia («Constructora Ficticia Dos, C.A.», J-00000001-0) en otra instalación temporal solo
> para exportar su `.silice-clave`; caso `silice.db` con `scripts/seed`, `seed_demo` (DEMO-001) y
> `generar_obra_control` (OBRA-GENERADA); caso `reajuste.db` con `tests/fixtures/reajuste_s1`; serie de precios con un
> atípico (memoria `atipicos_s3.md`: 1, 2, 4 … 256, 257); tres libros construidos con `tests/fixtures/libros_empresa.py`
> (`limpio`, `sin_equipos`, `varios_hallazgos`). Ningún libro real, nada de `docs/auditoria/*.xlsx` ni de
> `data/confidencial/`.
> **Capturas:** `scratchpad/auditoria_b/capturas/<página>_<ancho>/` (≈ 150 PNG con su `.txt` y `.json` de medidas).

## Resultado global

| Criterio (DESIGN.md / PRODUCT.md) | Resultado |
|---|---|
| Sin scroll horizontal a 1366 y a 1056 px | **Cumple** en todas las páginas medidas (`scrollWidth` = `clientWidth`, 1351 con barra vertical). Ver VB-10: la tabla de Reajuste se desborda dentro de su contenedor. |
| Menú plegable | **Cumple** el marco: fijo a 1056 px (botón oculto) y plegable a 1055 (botón «Abrir el menú», `aria-expanded`, se cierra al elegir un enlace o con clic fuera). Esc no lo cierra (VB-14). |
| Esquinas rectas | **Cumple**. Solo `checkbox` de Carbon Charts (2 px) y el círculo del `RadioButton` (50 %). |
| Sin sombras ni degradados | **Cumple**. Las sombras medidas son los bordes internos de las pestañas y el anillo de foco de Carbon; 0 degradados. |
| IBM Plex Sans (y Mono en códigos) | **Cumple**: únicas familias medidas. |
| Un `h1` `heading-04` por página | **Cumple** en las 20 páginas medidas (28 px). Excepción: la pantalla de entrada usa `heading-03` (VB-15). Los rótulos de área del menú son `h2` de 12 px (VB-15). |
| Formato es-VE y exacto a un toque | **Parcial.** Cumple en Libro (tooltip «En el libro: 4.203,93325 / Según Sílice: 4.358,2082500»), Revisar (`title="Valor exacto: 95066.60006250"`), Entregar, Reajuste y Control (`title` con el valor). No cumple en Elaborar (VB-6), Historial (VB-7), prosa de hallazgos (VB-8) y porcentajes del Tablero (VB-21). |
| Montos tabulares | **Cumple** (`tabular-nums`) en todas las tablas y franjas medidas. |
| Español con tildes, sin jerga | **No cumple** en Control, Reajuste, Componer, Precios, Elaborar y textos del núcleo (VB-5, VB-6, VB-8, VB-11, VB-16, VB-17). |
| Sin rayas como adorno | **Cumple** (0 en todas). |
| El color nunca va solo / severidad con ícono | **Parcial.** Cumple en Libro, Historial, Revisar, Elaborar y Precios; no en las alertas de Control (VB-4). |
| Morado solo para atípicos | **Cumple.** El ícono de «Advertencia» del atípico se pinta `rgb(138, 63, 252)` (#8a3ffc, `--silice-atipico`); 0 elementos morados en el Tablero. |
| Rojo/verde IBCS solo en variaciones | **Cumple** (Libro: Δ en rojo con triángulo y texto). |
| Cero errores de consola | **No cumple** del todo: 403 de recursos que la cuenta no puede leer (VB-9). Ninguna excepción de JavaScript. |
| Nada de red externa | **Cumple**: 0 peticiones a hosts distintos de `127.0.0.1` en todos los recorridos (incluida la pestaña del Asistente de IA). |
| Ningún secreto en pantalla ni en el almacenamiento | **Cumple**: `localStorage` y `sessionStorage` vacíos en todas las páginas; cookie `silice_sesion` `HttpOnly` y `SameSite=Strict`; la contraseña de la clave de firma es `type=password` y el campo se vacía al generar. |
| Teclado | **Cumple en lo esencial**: «Saltar al contenido» es el primer Tab y lleva el foco a `main`; orden lógico cabecera → menú → contenido; foco visible en todo lo medido (contorno 2 px `#0f62fe`, o borde 2 px en el nombre «Sílice», o anillo interno en botones); el diálogo de Cuentas atrapa el Tab, Esc lo cierra y devuelve el foco; las pestañas se recorren con flechas. Faltas en VB-12, VB-13 y VB-14. |
| Estados vacío, carga y error | **Cumple**: «Buscando variaciones atípicas…», «Elija un proyecto», «Todavía no hay auditorías guardadas»; con la API interceptada (500 con `detalle`, conexión rechazada) aparece el `AvisoError` con el `detalle` tal cual o «No se pudo hablar con el programa de Sílice». |
| Sesión expirada | **Cumple**: sin la cookie, al navegar dentro de la app la API da 401 y aparece «Entrar» con «Su sesión venció. Entre de nuevo para seguir.», 0 filas de datos; al recargar, solo la pantalla de entrada. |

## Hallazgos nuevos

| # | Gravedad | Página | Hallazgo (evidencia) | Arreglo sugerido |
|---|---|---|---|---|
| VB-1 | **Bloqueante** | Entregar → Revisar un paquete | El paquete de **DEMO-001** que Entregar genera y firma **no se puede revisar**: `POST /v1/revision/paquete` contesta 422 `renglon 0.equipos: cifra fuera del patron estricto: '0.0833333333333333333333333333'` (confirmado también con `curl` directo a la API). La pantalla muestra ese texto crudo, sin tildes. El de OBRA-GENERADA sí se revisa. Capturas `entregar_1366/03_generado.png`, `revisar_1366/01_bueno.png` (primera pasada). | Que la emisión serialice con el mismo patrón estricto que exige el lector (cuantizar en el documento canónico) o que Entregar valide el paquete con el lector de Revisar antes de firmarlo; prueba de ida y vuelta Entregar → Revisar con la siembra `seed_demo`. Mensaje en español llano. |
| VB-2 | **Importante** | Inicio, Elaborar, Revisar, Administración (Empresas registradas), Precios | La zona de soltar archivo mide **36 px** de alto, no 96 (medido: `.cds--file__drop-container` h=36 en Inicio y en Empresas registradas). Causa en el CSS compilado: el mismo botón lleva `cds--file__drop-container` y `cds--file-browse-btn`; la regla posterior `.silice-subida .cds--file-browse-btn{block-size:100%}` anula `block-size:6rem` y el 100 % de una rejilla sin alto es `auto`. Reabre V-7. | Fijar el alto en una sola regla (`.silice-subida .cds--file__drop-container.cds--file-browse-btn { block-size: 6rem }`) o quitar el `block-size:100%`; prueba que mida el alto renderizado. |
| VB-3 | **Importante** | Control de obra › Valuaciones | La columna **«Número» sale vacía** en las 4 valuaciones. La API manda la clave `Numero` (`V-01`…`V-04`) y el front busca `Número` (`frontend-desktop/src/paginas/control/logica.ts:145`, `COLUMNAS_VALUACIONES`). Regresión del arreglo de tildes. Captura `control_1366/02_valuaciones.png`. | Usar la clave de la API (`Numero`) y el rótulo con tilde (la tabla `164: Numero: "Número"` ya existe); prueba con la respuesta real de la API. |
| VB-4 | **Importante** | Control de obra › Alertas | La severidad de las alertas es texto en mayúsculas («ADVERTENCIA», «sin evaluar») **sin ícono**, fuera del componente de severidad; la descripción usa punto decimal («SPI 0.9780») junto a la columna con coma («0,9780»). Captura `control_1366/04_alertas.png`. | Pintar la severidad con el componente común (ícono + «Advertencia»); formatear la cifra de la descripción en es-VE. |
| VB-5 | **Importante** | Control de obra, Reajuste de precios | Tildes y jerga interna que siguen a la vista: Valor ganado «EAC (indice BAC/CPI)», «Termino por el indice (dia habil)», «Desvio de precio», «(S1)», «(S1-R2)»; Valuaciones «solo anularla la saca del calculo (S2-R14)», «Agregar linea»; Parámetros «si». Reajuste: «El ultimo periodo aun no cierra: el estudio se guardara … (S1-R21)», «Escriba «Serie del componente»: es obligatorio (UC-18).», «La clausula no es valida: mecanismo_pagadero solo con 'ambos' …», opciones de los desplegables «comprobacion», «por_partida», componente «mano_obra». V-17 y V-22 siguen parciales por esto. | Traducir los códigos a frases, acentuar y mostrar rótulos para los valores de los desplegables (el valor interno puede seguir igual). |
| VB-6 | **Importante** | Elaborar un presupuesto | Cifras sin formato es-VE ni exacto: «Total del presupuesto **1166.91 USD**», tabla «242.64», «217.41», cómputo «0.896000», «17.9200»; plan «Dia 1»; «Resultado: NO CUMPLE». Captura `elaborar_1366/03_resultado_completa.png`. | El formateador es-VE de Entregar/Tablero con el exacto en `title`; cantidades con sus decimales propios; «Día»; «No cumple». |
| VB-7 | **Importante** | Historial de auditorías › detalle | «Total del libro **4.876,56257**» y «Total según Sílice **5.055,521570000**»: ni en centésimas ni con el exacto a un toque (DESIGN.md, RS2-12); el Libro de la empresa muestra lo mismo como 4.876,56 con tooltip. Captura `historial_1366/02_detalle_completa.png`. | Mismo indicador que el Libro: centésimas y exacto en el tooltip. |
| VB-8 | **Importante** | Libro de la empresa, Historial (textos de hallazgos del núcleo) | Formatos mezclados en la misma frase: F1 «guarda un P.U. de **28.28375** y … lo recalcula en **30.2121875** … mueve el total sin IVA en **154.28**» junto a L9 «suma **4 331,43 USD**». En es-VE «154.28» se lee ciento cincuenta y cuatro mil. Además «motor de Silice», «curva de inversion», «esta definido», «depreciacion», «amortizacion» (Elaborar). | Formatear las cifras de los mensajes de reglas con el mismo criterio (o devolver las cifras aparte y formatearlas en el front); revisar tildes de los mensajes del núcleo. |
| VB-9 | **Importante** | Inicio (admin y rita) | Con `admin`, Inicio ofrece «Audite un presupuesto»; al soltar el libro y pulsar «Auditar por mi cuenta» se llega a **«Sin permiso»** (captura `inicio_1366/admin_audita.png`). Inicio pide además `/v1/proyectos` y `/v1/auditorias-libro` con `admin` y `/v1/produccion/existencias` con `rita`, que contestan **403** y quedan como errores de consola. | Mostrar el bloque de auditoría y pedir cada recurso solo si la cuenta tiene la acción (`leer_proyecto`, `operar_arenera`); para el administrador, un texto que diga quién audita. |
| VB-10 | **Importante** | Reajuste de precios › resultado | La tabla «Escalatoria y comprobación» (12 columnas) mide 1751 px a 1366 y 1479 px dentro de 768 visibles a 1056: media tabla queda tras el scroll interno, y la columna «Marcas» con texto largo comprime las filas a ≈ 200 px (captura `reajuste_1366/05_resultado_completa.png`). Las cifras sí cumplen (15.300,00 / 16.000,00 / −0,82, los oráculos de `test_ui_reajuste`). | Sacar «Marcas» de la tabla (avisos ya debajo) o mostrarlas como nota por fila; agrupar «(otra moneda)» en una segunda tabla. |
| VB-11 | **Importante** | Componer, Precios de la empresa | Sin tildes en la interfaz: Componer «Comience por la cabecera (codigo y descripcion) … o busquelo … el desglose se calcula aqui automaticamente»; Precios «Fecha de evaluacion», «Sin version, el impacto …», «MaPreX en bolivares». | Acentuar (`paginas/componer`, `paginas/precios_empresa/index.tsx:323`). |
| VB-12 | Pulido | Administración › Empresas registradas | La confirmación en línea de «Marcar como retirada» / «Revocar» reemplaza el botón y **el foco cae a `body`** (medido tras Enter: `{"tag":"body"}`); el lector de pantalla no anuncia la pregunta. El diálogo de Cuentas sí lo hace bien. | Llevar el foco al grupo de confirmación (o a «Cancelar») y devolverlo al botón al cancelar. |
| VB-13 | Pulido | Reajuste de precios | Tras «Calcular», el error (`role=alert`) aparece bajo el pliegue (y ≈ 760 a 1366×768) y el foco queda en `body`; el resultado tampoco recibe el foco. | Llevar el foco al aviso o al `h2` del resultado. |
| VB-14 | Pulido | Marco (menú a < 1056 px) | Con el menú abierto como capa, **Esc no lo cierra** (medido `aria-expanded=true` tras Esc). | Cerrar con Esc y devolver el foco al botón. |
| VB-15 | Pulido | Marco, Entrar | Los rótulos de área del menú son `h2` de 12 px y aparecen antes del `h1` de la página; `document.title` es siempre «Sílice» (no cambia por página); la pantalla «Entrar» usa `h1` `heading-03` (20 px). | Rótulos del menú sin nivel de encabezado (o `aria-hidden` en el nivel); título del documento «Página · Sílice»; `heading-04` en Entrar. |
| VB-16 | Pulido | Entregar, Tablero, Precios, Revisar | Concordancia y forma: «3 advertencia» (Entregar), «6 advertencia» (Tablero), «1 insumos no contrastables … 0 sin tasa a su fecha ()» (paréntesis vacíos), «CUMPLE» / «NO CUMPLE» en mayúsculas, «INDICIO:». | Plural según la cantidad; omitir la lista vacía; mayúscula inicial. |
| VB-17 | Pulido | Revisar un paquete | La tabla de precios que no coinciden muestra el campo crudo «precio_unitario»; en «Presupuesto en Excel», el error dice «**externo.xlsx**: falta la hoja 'Datos'» aunque el archivo subido era `limpio.xlsx`; la plantilla oficial descargada da 3 advertencias al auditarla (R1, R7 «Dia 1»). | Rótulo «Precio unitario»; nombrar el archivo recibido; una plantilla que pase su propia auditoría. |
| VB-18 | Pulido | Administración › Asistente de IA; Administración, Reajuste | El aviso pide al administrador «Instálelo con «uv sync --extra ia»» (comando de desarrollador); hay 4 a 8 regiones `role=alert` vacías en la página (Administración y Reajuste). | Texto para el usuario («falta un componente opcional; pídalo a quien instaló Sílice»); montar la región viva solo con contenido. |
| VB-19 | Pulido | Control, Tablero, Revisar, Historial, Histórico | Fechas en ISO («vigente desde 2026-11-02», «2026-11-02 a 2026-11-06», «Versión GEN-001 del 2026-10-19») junto a dd/mm/aaaa en Historial y Libro; los filtros «Desde (AAAA-MM-DD)» de Historial e Histórico son texto, no selector de fecha. | Formato de fecha único es-VE; `type="date"` en los filtros. |
| VB-20 | Pulido | Cabecera, Acerca de | El selector de proyecto muestra el id: «3 · OBRA-GENERADA»; Acerca muestra los nombres de migración «ins_0003_auditoria_libro», «caso_0009_s3_paquete». | Solo el nombre del proyecto; «Base al día» o el número de versión de la base. |
| VB-21 | Pulido | Tablero | Porcentajes de la composición y del Pareto con punto: «37.6 %», «39.1%», «43.9 %»; el `title` del total es «95066.60 USD», no el exacto (95066.60006250, que sí da Revisar). V-19 queda parcial. | Formateador es-VE también en porcentajes y etiquetas del gráfico; exacto en el `title`. |
| VB-22 | Pulido | Empresas registradas | Con la clave ya revocada siguen ofrecidos «Marcar como retirada» y «Revocar» sobre ella. | Deshabilitar o explicar cuando el estado es «revocada». |
| VB-23 | Pulido | Administración | Los campos de texto son blancos sobre la capa blanca de la pestaña: solo la línea inferior marca el campo (captura `inicio_1366/administracion.png`). | Usar el token de campo de la capa (`$field-02`) dentro de la capa blanca. |
| VB-24 | Informativo | Catálogo, Entregar, Elaborar | Los datos sembrados no llevan tildes («caso de demostracion (linea de agua potable, didactico)», «Instalacion de tuberia», «Excavacion»): son datos de ejemplo, no rótulos. | Corregir las semillas cuando se toquen. |
| VB-25 | Informativo | Elaborar | Elaborar valora con la lista más reciente del caso: tras sembrar la serie de atípicos (listas de un solo insumo), a 1056 px contestó 409 «el insumo MAT-009 (Cemento Portland) no tiene precio en la lista 'Serie demo 10'». El `AvisoError` lo dijo bien; es efecto de los datos de prueba. | Ninguno, o decir qué lista se usa. |
| VB-26 | Informativo | Marco | El menú lateral no se recorre con flechas (solo Tab, como el SideNav de Carbon). | Ninguno. |

## Estado de los hallazgos anteriores (V-1 a V-25)

| # | Estado | Evidencia en esta pasada |
|---|---|---|
| V-1 | **Cerrado** | Catálogo carga (14 partidas, 77 insumos); el `AvisoError` con el `detalle` se vio en Historial, Inicio y Entregar con la API interceptada. |
| V-2 | **Cerrado** | Acerca con `h1` `heading-04` y «Versión: 1.2.0». Queda la jerga de VB-20. |
| V-3 | **Cerrado** | Libro con `h1`. |
| V-4 | **Cerrado** | «Últimas auditorías guardadas» y el Historial muestran las 3 auditorías ficticias. |
| V-5 | **Cerrado** | Componer sin UC/RF ni raya. Quedan tildes (VB-11). |
| V-6 | Cerrado (a la vista) | Los párrafos de Inicio, Elaborar, Historial y Reajuste cortan a ≈ 560-580 px. No se midió en `ch`. |
| V-7 | **Abierto** (como VB-2) | La zona sigue en 36 px. |
| V-8 | **Cerrado** | Un `h1` `heading-04` en las 20 páginas medidas. |
| V-9 | **Cerrado** | Empresas registradas y Asistente de IA ya migradas y funcionando. |
| V-10 | Informativo | Igual (1351 con barra vertical). |
| V-11 | **Cerrado** | Tablero y Control cargan OBRA-GENERADA. |
| V-12 | **Cerrado** | Sin `no_disponible` en Control. |
| V-13 | **Cerrado** | Entregar «4.131,10 USD» con exacto. |
| V-14 | **Cerrado** | Indicadores del Libro sin recorte, a 1366 y a 1056. |
| V-15 | **Cerrado** | «Según Sílice» en lugar de «Meta»; tooltip con libro y Sílice. |
| V-16 | Abierto (decisión de Eugenio o del tutor) | Libro 3,54 % menor que Sílice sigue en rojo con ▼. |
| V-17 | **Parcial** | Ya hay dos pasos (pestañas) y selector de fecha; queda la jerga y las tildes (VB-5). |
| V-18 | **Cerrado** | Catálogo e Histórico sin 404. |
| V-19 | **Parcial** | Montos del Tablero en es-VE y ejes «10.000»; porcentajes con punto y `title` sin el exacto (VB-21). |
| V-20 | **Parcial** | Tablero acentuado; Control conserva textos sin tilde (VB-5). |
| V-21 | **Cerrado** | SPI y CPI como cifras; 0 elementos morados en el Tablero. |
| V-22 | **Parcial** | Parámetros con nombres en español; quedan «ADVERTENCIA» sin ícono (VB-4) y tildes (VB-5). |
| V-23 | **Cerrado** | «Proyecto: OBRA-GENERADA» en Inicio. |
| V-24 | **Cerrado** | Fecha de devolución y «Cambiar libro» bajo el título del Libro. |
| V-25 | Informativo | Igual. |

## Qué se comprobó y cómo

- **Elaborar con resultado** (ana): dominio civil, `data/samples/civil/tanquillas_y_zanja.csv` (ejemplo versionado y
  ficticio, solo leído), partidas LB-01..LB-04; cómputo, presupuesto (1166.91 USD), plan de trabajo e informe con 2
  hallazgos. A 1056 px se capturó el estado de error (VB-25).
- **Reajuste con resultado** (ana, caso `reajuste.db`): cláusula ficticia S1 (mecanismo «ambos», estructura declarada,
  series FIC-MAT/EQU/MO), período 01/02/2027-28/02/2027, ejecutado 1000 de S1-R01; resultado 15.300,00 / 16.000,00 y
  −0,82 en la otra moneda (los oráculos de `tests/unit/test_ui_reajuste.py`). Selectores de fecha `type=date` en
  los dos pasos; los errores de validación se vieron con su texto (VB-5).
- **Entregar** (ana): paquete firmado con la clave ficticia para DEMO-001 y para OBRA-GENERADA, «Paquete listo y
  firmado», SHA-256 y descarga a la carpeta temporal (`Page.setDownloadBehavior`).
- **Historial**: 3 auditorías guardadas con el recorrido «Auditar un libro» (Inicio → Libro → Historial), detalle
  abierto; filtros y foco al abrir el detalle (el foco va al `h2` del detalle).
- **Revisar un paquete** (rita): bueno (OBRA-GENERADA: «No verificado … Se audita igual», con formulario de dictamen),
  alterado (`presupuesto.json` con un dígito cambiado: «Alterado: presupuesto.json cambió después de firmarse», tabla
  de precios que no coinciden, **sin formulario de dictamen** y «no admite dictamen»), DEMO-001 rechazado (VB-1);
  pestaña «Presupuesto en Excel» con la plantilla descargada de la propia app y con un libro de otro formato.
- **Administración** (admin): Empresas registradas — leer `.silice-clave` sin guardar (0 registradas tras leer),
  huella equivocada (mensaje de 20 caracteres), registrar con la huella buena, retirar y revocar con confirmación, y
  rechazo de la clave de la propia empresa. Asistente de IA — estado, configuración guardada con el asistente apagado
  (tope 2,50) y rechazo del tope 0; sin ninguna llamada de red externa.
- **Inicio y menú por áreas**: con ana se ven Inicio, Auditar, Crear, Producción y Más (más «Herramientas
  principales»); con admin, Inicio, Producción y Más. Recorrido guiado de 3 pasos: el panel del menú marca el paso
  («Paso 2 de 3», «Paso 3 de 3») y ofrece «Terminar recorrido».
- **Control de obra** (OBRA-GENERADA): Línea base, Valuaciones, Valor ganado y Alertas; cifras es-VE con `title`.
- **Precios de la empresa**: «Buscar variaciones atípicas de precio» sobre la lista sembrada: 1 variación ATIP-001,
  0,39 %, 01/09/2026 → 01/10/2026, «Advertencia» con ícono morado #8a3ffc.
- **Teclado**: Tab y Shift+Tab desde la carga, «Saltar al contenido», Enter en enlaces del menú, botón «Más»
  (Enter pliega y despliega con `aria-expanded`), flechas en pestañas (Revisar, Administración), diálogo de Cuentas
  («Desactivar a tomas»: foco al abrir, Tab cíclico, Esc y retorno del foco; no se confirmó), confirmación en línea de
  Empresas registradas, menú como capa a 1055 px.
- **Lector de pantalla (inspección)**: `lang="es"`, un `header`, un `nav` «Menú principal», un `main` (`#contenido`),
  `aria-current="page"` en el menú, 0 campos sin etiqueta en todas las páginas, avisos con `role=alert`/`status`,
  diálogo `role=alertdialog` con `aria-modal`, `aria-labelledby` y `aria-describedby`.
- **Estados**: vacío, carga y error (Fetch del CDP: 500 con `detalle` en `/v1/auditorias-libro`, conexión rechazada en
  `/v1/entregas/versiones`), sesión expirada borrando la cookie (con y sin recarga).
- **1056 px**: recorridos repetidos (Inicio, Libro con auditoría, Historial con detalle, Elaborar, Entregar,
  Reajuste con resultado, Control con sus pestañas, Tablero, Revisar bueno/alterado/Excel, Precios con atípicos,
  Administración) sin scroll horizontal de página.

## Qué NO se pudo comprobar y por qué

- **Clave del Asistente de IA (registrar, clave enmascarada, olvidar con confirmación)**: el extra `ia` (`keyring`) no
  está instalado en el `.venv` compartido y la regla prohíbe instalar; la pestaña muestra «Falta el componente…» y no
  ofrece esos controles. Además, con `keyring` instalado, registrar escribiría en el Administrador de credenciales de
  Windows de Eugenio (servicio `silice-ia`): habría que forzar un almacén nulo (`PYTHON_KEYRING_BACKEND`) antes de
  probarlo.
- **Paquete verificado (banner verde)**: la clave de la propia empresa no se registra como ajena (es correcto), y no
  se generó un paquete firmado por la segunda empresa ficticia; solo se vio «No verificado» y «Alterado».
- **Guardar el dictamen y guardar el estudio de reajuste**: se vio el formulario, no se envió.
- **Lector de pantalla real** (NVDA/Narrador): solo inspección del DOM y de los roles.
- **Selector de fecha nativo abierto**: en headless no se abre el calendario; se comprobó `type=date` y el valor.
- **Diálogo «Olvidar la clave»**: depende del extra `ia` (ver arriba).
- **Elaborar con resultado a 1056 px**: la siembra de atípicos cambió la lista vigente y Elaborar dio 409; se capturó
  ese estado de error en su lugar (VB-25). El resultado sí se capturó a 1366.

## Limpieza

Servidor (PID 12036) y Chrome (PID 14840, con su árbol) cerrados por su PID con `taskkill /PID … /T`; puertos 8131 y
9461 libres. Los datos, libros, paquetes, claves y capturas quedan solo en la carpeta temporal del scratchpad; nada en
`data/` (sin archivos modificados en las últimas horas) ni en el repositorio salvo este informe.
