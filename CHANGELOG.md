# Registro de cambios

Formato de [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) con secciones en español; versiones según
[SemVer](https://semver.org/lang/es/). Cada PR agrega una línea bajo «Sin publicar» (maestro §6.1, RV‑2); al
etiquetar, las líneas pasan a la sección de la versión. La historia anterior a la 0.5.0 está en `docs/bitacora/`.

## [Sin publicar]

### Corregido
- La prueba de humo del instalador exigía el caso por defecto (`casos\silice.db`) justo después de instalar, pero el diseño lo crea al primer arranque (spec S5 §5.4): ahora lo comprueba tras arrancar, y el instalador deja en su registro el código de `migrar` (`instalador/humo.ps1`, `instalador/silice.iss`). El workflow del instalador no había pasado nunca en la CI por esto.

### Agregado

- Interfaz: títulos unificados (un h1 `heading-04` por página, también cargando; h2 en `heading-compact-02`), marco de página común con párrafos a 70 ch, zona de soltar archivo de 96 px y marca «clásica» en las pestañas de Administración aún sin migrar; Catálogo e Histórico piden las rutas reales de la API (una prueba cruza todo literal de ruta del front con el OpenAPI); Tablero sin donas de índices, con formato es-VE único, el exacto en el tooltip y paleta sin morado; Control con etiquetas en español llano; tildes en Tablero y Control; el Libro rotula «Según Sílice» y lleva sus controles en el cuerpo; Inicio muestra el nombre del proyecto (V-6 a V-9, V-15, V-18 a V-24 de la auditoría visual).
- Seguridad: Índices del BCV y Precios de la empresa. Las rutas que escriben (confirmar índices, cargar la referencia MaPreX y crear listas de empresa) exigen la sesión de una cuenta con rol administrador de precios; la clave de API solo lee (403 en las de escritura) y el responsable de una importación es siempre la persona de la sesión. El lector de .xls rechaza libros con más de 50 hojas o 2 000 000 de celdas por hoja; el tope de archivo de Precios de la empresa pasa a 20 MiB (el real del servidor); los nombres reservados de Windows (CON, NUL, a:b) se sanean en todas las subidas; el informe de importación guardado se limita a 50 000 caracteres con el recuento de rechazos omitidos; los campos de texto de la lista de empresa tienen longitud máxima.
- Tablero y Control de obra aceptan el código que da `GET /v1/proyectos` además del nombre exacto (si un nombre es un número, gana el código); Control de obra dice en español cuando algo no está disponible y conserva el detalle de la API; Entregar presenta el total con dos decimales y separador de miles (valor exacto en el tooltip); Reajuste sin jerga interna. Catálogo, Histórico y Acerca de muestran el error de la API en vez de quedarse cargando; el Libro de la empresa tiene título, franja de indicadores completa y rótulo «Según Sílice»; Componer sin siglas internas.
- Migración del front, «Índices del BCV» (UC‑17): `GET /v1/indices/contexto`, `POST /v1/indices/leer` (informe previo, no escribe) y `POST /v1/indices/confirmar` (guarda todas las series o ninguna, con la huella del archivo); `ADMINISTRAR_PRECIOS`, sesión o clave de API; sin estado en el servidor; un `.xls` sin el extra `bcv` (xlrd) da un mensaje claro y no una traza; la lógica de `ui/indices.py` pasa a `aplicacion/indices.py` (RM‑1) y su página nueva.
- Migración del front, «Precios de la empresa» (UC‑17 4‑5): `GET /v1/precios-empresa`, `POST /v1/precios-empresa/referencia`, `POST /v1/precios-empresa/listas` (multipart; solo `.csv` o `.xlsx`, tope de 25 MiB, guardia de libros y 422 sin eco) y `GET /v1/precios-empresa/listas/{id}/hallazgos` (R11 y R12 con el impacto como texto), con `ADMINISTRAR_PRECIOS`; la lógica de `ui/precios_empresa.py` pasa a `aplicacion/precios_empresa.py` (RM‑1) y su página nueva. La búsqueda de variaciones atípicas (RF‑100) sigue solo en la página clásica.
- Se retira el Visor 3D del modelo (página Streamlit, `ui/visor3d.py`, three.js r128): quedan 20 páginas, 17 en modo entrega; el adaptador IFC sigue vivo (decisión de Eugenio, 2026-10-19; RNF‑08 pendiente de ratificar por el tutor).
- Migración del front, Administración (backend): `/v1/admin/empresa` (empresa y clave de firma: generar, descargar la pública y el respaldo cifrado, retirar y revocar), `/v1/admin/claves-api` (el secreto se muestra una vez) y `/v1/admin/instalacion` (red y API en lectura, respaldos, eventos de seguridad perdidos); solo con sesión de administrador (la clave de API no administra) y, lo sensible, solo desde el propio equipo; la lógica de «Instalación» pasa a `aplicacion/instalacion.py`.
- Interfaz nueva, ola 4b (sesión 2b): «Reajuste de precios» (UC‑18, RF‑71, RF‑72) por la API (`GET /v1/reajuste/contexto` y `/parciales`, `POST /v1/reajuste/calcular`, `/guardar`, `/excel`; `CONVERTIR_Y_REAJUSTAR`; sin estado en el servidor) y su página; la lógica de `ui/reajuste.py` pasó a `aplicacion/reajuste.py` (RM-1) y `HojaInvalida` a `aplicacion/errores.py` (`ui/hoja.py` solo la reimporta, misma clase).
- Interfaz nueva, ola 1: páginas «Catálogo de partidas e insumos» (con búsqueda sin tildes) y «Histórico de cambios de precio» (filtros por insumo y fechas, variación en por ciento sin pasar por float), sobre `GET /v1/partidas`, `/v1/insumos` y `/v1/cambios-precio`.
- Interfaz nueva, ola 1: página «Acerca de Sílice» sobre `GET /v1/acerca` (versión, revisiones de las dos bases, módulos; la carpeta de datos solo para quien administra o por clave de API).
- Interfaz nueva, ola 4 (S2-C), Control de obra (UC‑19, UC‑20): `/v1/control/*` (línea base y parámetros, valuaciones, anulación, costos, importación de XLSX con informe previo, cálculo del valor ganado con alertas y reproyección, opciones de recuperación y elección) con `CONTROL_DE_OBRA` y, para elegir, `DECIDIR_RECUPERACION`; el responsable sale de la sesión y el servidor no guarda estado entre el cálculo de las opciones y la elección. La página de cinco pestañas reutiliza `CurvaPlanAvance`.
- Interfaz nueva, ola 4 (S2-C), Tablero del proyecto (UC‑13): `GET /v1/tablero?proyecto=` (solo lectura, `leer_proyecto`) y la página con anillos de avance, curva plan/avance común (`CurvaPlanAvance`), desglose, Pareto y versiones sobre Carbon Charts, cada gráfico con su tabla de montos exactos. `control`, `tablero` y `estilo` pasan a `aplicacion/` con reexportación en `ui/` (RM‑1).
- Migración del front, ola 3 (S2-B), backend de «Componer una partida» (UC‑10, UC‑11): seis rutas `/v1/composicion/*` (`opciones`, `evaluar`, `partidas/{codigo}`, `referencia`, `similares`, `guardar`) con `EDITAR_HOJA`, montos como texto y los mensajes de la página clásica; la lógica (y `guardar_composicion`, antes en `ui/elaboracion.py`) vive en `aplicacion/composicion.py`, que `ui/` reexporta.
- Interfaz nueva, ola 4 (sesión 2b): la entrega del paquete auditado por la API (`GET /v1/entregas/versiones` y `/resumen`, `POST /v1/entregas`, descarga binaria del `.silice`; `ENTREGAR_PAQUETE`, y firmar solo desde el propio equipo, RM-4) y su página «Entregar paquete»; la lógica de `ui/entrega.py` pasó a `aplicacion/entrega.py` (RM-1) y `ui/entrega.py` la reexporta.
- Interfaz nueva, migración de páginas (sesión 2b): marco con menú por rol, caso y proyecto por sesión web, página de Inicio y «Partidas similares» (`POST /v1/similares`); la lógica de las páginas pasa a `aplicacion/` y `ui/` la reexporta.
- Sesión 2b, ola 2 (Actualizar precios, Elaborar un presupuesto y Escenarios en la interfaz nueva): rutas `POST /listas-precios/vista-previa`, `POST /presupuestos/revalorar`, `POST /presupuestos/{codigo}/descartar`, `POST /presupuestos/calcular` (más `/excel` y `/declarar-rendimiento`), `GET /presupuestos/{codigo}/escenarios/base` y `POST /presupuestos/{codigo}/escenarios/csv`; `GET /presupuestos` suma el campo aditivo `proyecto`; el informe de auditoría viaja como JSON (`api/esquemas_informe.py`); la lógica sin Streamlit pasa a `aplicacion/actualizacion.py` y `aplicacion/elaboracion.py` (con reexportación en `ui/`). Plan: `docs/planes/PLAN_MIGRACION_OLA_2.md`.
- Sesión 2b, ola 0a (backend del marco de la interfaz nueva): capa `aplicacion/` (RM-1); caso por sesión del navegador con `GET /v1/casos` y `POST /v1/casos/actual` (RM-2); `GET /v1/proyectos`; cambio de contraseña obligatorio desde la interfaz nueva (`POST /v1/sesion/contrasena`); `GET/POST /v1/sesion` informan `debe_cambiar_clave`, `acciones`, `modo_entrega` y `url_clasica` (la interfaz Streamlit, para las páginas aún no migradas); dependencia «solo desde el propio equipo» para la API (RM-4).
- Para integradores (RM-3): todas las rutas antiguas aceptan ahora la clave de API **o** la sesión del navegador con el rol de su página (tabla en `api/acceso.py`). Con `X-Silice-Clave` responden igual que antes; sin ella ni cookie, 401 con el mensaje de sesión y sin evento de «fallo de clave», como ya hacían las de `/v1/libros`.

### Cambiado

- Sesión 2 de la ruta (en curso): plan `docs/planes/PLAN_SESION_2_VISUAL.md`, producto y diseño de la interfaz nueva (`frontend-desktop/PRODUCT.md`, `DESIGN.md`) y enmienda 1.2.0 de la ERS (UC-26, RF-111 a RF-118, RNF-22 y RNF-23).

## [1.2.0] - 2026-10-18

### Agregado

- Sílice 1.2.0 (ruta, sesión 2; UC‑26, RF‑111 a RF‑118, RNF‑22 y RNF‑23): interfaz nueva y visor de solo lectura. `frontend-desktop/` (Vite, React 19, Carbon g10 y Univer, sin red externa) servida por la API en `/app` con CSP; `POST /v1/libros/replica` y `adapters/hoja_empresa/visual.py` (aspecto del libro con coordenadas de Excel); acceso del navegador por cuenta (`/v1/sesion` con cookie `HttpOnly`, anti‑CSRF y freno global con 429); campo aditivo `indicadores` en `/v1/libros/auditoria` (centésimas, sentido «exactitud», RS2‑12 y RS2‑13); el instalador lleva la interfaz compilada; trabajo `interfaz` en la CI.

### Cambiado

- Para integradores: las rutas `/v1/libros/*` aceptan ahora la clave de API **o** la sesión del navegador (RS2-5). Sin la cabecera `X-Silice-Clave` responden 401 con el mensaje de sesión (antes, el de la clave) y esa llamada ya no queda en el registro de accesos como fallo de clave; con una clave mala, todo sigue igual. RF‑98 ya no exige la clave en `/v1/sesion` ni en `/app` (enmienda 1.2.0 de la ERS).

## [1.1.0] - 2026-10-18

### Agregado

- RF-100: advertencia de variaciones de precio atípicas en la serie fechada (USD) de cada insumo, en la pestaña Precios de la hoja y en la lista de la empresa (`ml/anomaly/series.py`, `ui/atipicos.py`).
- RF-141 (R17): regla «Conexión de cada punto»: avisa de puntos de agua, drenaje o datos sin fuente y de tomacorrientes o iluminación sin circuito, en la hoja, al guardar, en el asistente y en la reauditoría (`adapters/espacio/conexion.py`).
- Reactivar la clave de IA de la empresa desde su respaldo cifrado, con rastro de cada intento fallido (Administración del asistente).
- Pruebas del experimento del asistente: comparador, métricas, mutaciones, corrida, congelado y `scripts/evaluar_asistente.py`.
- Ruta de construcción por sesiones, fichas de subagentes con modelo y esfuerzo, y plan de fuentes de la arenera (`docs/planes/`).

### Cambiado

- ERS, enmienda 1.1.0: pruebas obligatorias, RF-90 (b) diferido, RF-95 en parte (la corrida real del experimento sigue en pausa, sin gasto), E3 y E5 como límite del método, RF-141.
- Una prueba vigila que los archivos congelados del experimento no cambien (`tests/unit/test_experimento_congelado_vigente.py`).

### Corregido

- `main` en rojo desde la 1.0.0: se retiran los alias `ARENIA_CASO` y `ARENIA_MODO_ENTREGA`, que solo valían hasta la 0.6.0 (`ui/entorno.py`, manuales y `tests/conftest.py`).

## [1.0.0] - 2026-10-15

### Agregado

- S5 (cierre y lanzamiento 1.0.0, RF-97 a RF-99, RNF-19, RNF-20): instalador reproducible para Windows (`Silice-1.0.0.exe`), flujo `.github/workflows/instalador.yml`, medición de arranque RNF-19 (mediana 11.68 s <= 20.0 s), auditoría pip-audit limpia de vulnerabilidades y verificación con firma Ed25519 (`verificar_sumas.py` y `operacion.firma_sumas`).
- Ceremonia de la clave del proyecto (H1): clave pública Ed25519 versionada en `operacion/clave_proyecto.pub`, con su huella SHA-256 registrada en `docs/manual_instalacion.md`.

- `start.py`: arranque con un comando (`uv run start.py`), siembra los casos de demostración en `data/casos/` y abre la app en 127.0.0.1.
- S4‑3 (T14 a T16): panel «Asistente de IA» en la hoja (vista previa del envío, costo, aceptar, editar o rechazar, y la sesión marcada con la versión guardada), pestaña «Asistente de IA» en Administración (activación, tope de costo y clave solo desde el propio equipo), el anexo `anexos/ia.json` del paquete (ya armado por `ui/entrega.py`, verificado sin uso, costo ni clave) y los manuales y el caso CP‑12 del guion; sin pruebas nuevas por decisión de Eugenio; la compuerta GS4‑3 no se cruza todavía.
- Interfaz de trabajo (PLAN_SILICE_UI): pantalla «Tablero del proyecto» (tarjetas, control de obra, curva, desglose, Pareto, comparativo); línea de estado en la barra; pestaña APU en tres paneles; tema visual y Altair en extra `ui`.
- S3‑3 (T16, T17): pantalla «Entregar paquete» (UC‑22) con `ui/entrega.py` completo (anexos de S1, S2 y S4, cadena verificada, firma desde el propio equipo y SHA‑256 en el registro de accesos), página «Administración» (cuentas, empresa, clave de firma, empresas registradas, claves de API, accesos e «Instalación») y `scripts/restablecer_administrador.py`; el acceso sigue apagado por omisión.
- 1.0.0 · S5-3/S5-4 (RF-97, RF-98, RNF-19): `instalador/silice.iss` (por usuario, migración en `[Code]`, datos conservados), prueba de humo (`humo.ps1`, `navegador.py`, `proxy_testigo.py`, `verificar_bases.py`), `auditar.py` con `docs/pip-audit-aceptadas.toml`, flujo `.github/workflows/instalador.yml`, `scripts/medir_arranque.py` y manual de instalación; sin pruebas nuevas por decisión de Eugenio; sin compilar con Inno Setup.
- S3-4 (T19 a T21): `auditoria/` (reauditoría en memoria compartida por la vista y la API, R1-R12 y R15 con R12 a la fecha de emisión; R13-R14 apagadas hasta que S2 reconstruya su instantánea desde el anexo), `ui/revision.py`, la pantalla «Revisar un paquete» (UC-23, sección Revision) y `POST /v1/auditorias` con la clave de API de `api/proteccion.py`; sin pruebas nuevas por decisión de Eugenio.
- 1.0.0 · S5‑3 (RF‑97, RNF‑19, RNF‑20): `instalador/manifiesto.toml` (lista blanca de lo que viaja), `manifiesto.py` (cierre de importaciones de los sembradores y `simular_lista`, un solo `config.toml`), `operacion.programa` y la orden `verificar-programa`; `construir.py` (`--solo-carpeta` sin Inno Setup), `licencias.py` y `tamanos.py`.
- 1.0.0 · S5‑2 (RF‑98, RF‑99, T9, T10 y T12): la API exige clave en toda ruta menos `/salud` y filtra hosts y redes ajenas con tope de cuerpo; `operacion.eventos_perdidos` y `ui.cliente` (SEG‑12 y «solo este equipo»); pantallas «Acerca de» e «Instalación»; sin pruebas nuevas por decisión de Eugenio.
- 1.0.0 · S5‑2 (RF‑98, RF‑99): `operacion.version`, `registro` sin secretos, `silice.toml` y carpetas de usuario en `config`, `red` (IP explícita y reglas de cortafuegos), `lanzador` y las órdenes `arrancar`, `parar`, `demostracion`, `red-local` y `diagnostico-similitud`; la versión de la API sale de `pyproject.toml`; sin pruebas nuevas todavía.
- 1.0.0 · S5‑0: apertura (fases de la 1.0.0, enmiendas de ERS con UC‑24, RF‑97 a RF‑99 y RNF‑19, arquitectura, plan de pruebas y calidad) y `instalador/medir_capas.py`; la parte S5 de la meta queda diferida.
- S4‑1 (T5, T6): `asistente/` con las 13 herramientas sin campos de precio, el catálogo, las propuestas pendientes y la validación en cuatro capas; guardia de arquitectura propia.
- S3-5 (planos): DXF dañado con lectura de recuperación, requisitos IDS del IFC (`data/ids`), R15 de coherencia geométrica (también en la hoja) y R16 de contraste entre dos fuentes; sembrador de errores y medición de detección (100 % y 0 falsas alarmas sobre OF-001). Falta el costo de la diferencia (espera a SL-E9).
- S4‑2 (T7 a T12): interfaz de proveedor, proveedor guionado y tarifas con fecha; privacidad por lista blanca; registro `ia_*` con su revisión de Alembic y el anexo `ia.json`; orquestador reanudable; adaptadores de Claude y de Ollama con clientes falsos. La clave de IA (T13) queda diferida.
- S4‑1 (T4): origen «propuesta de IA» (`TipoOrigen.IA`) en el espacio, R8 advierte cada campo supuesto por la IA y la hoja muestra la procedencia `ia:` en el Estado.

- S2‑0 (0.7.0 en construcción): especificación de valuaciones, valor ganado, alertas y recuperación (UC‑19, UC‑20, RF‑72 a RF‑79, RNF‑15, R13 y R14 en la ERS); memoria a mano OB‑S2 con su XLSX y las fronteras de otros dominios; expedientes SL‑E4, SL‑E5 y SL‑E6; parte S2 de la meta (`scripts/meta_silice_s2.py`, `--version 0.7.0 --hasta S2-0`).
- S4.0: ERS (UC‑09, RF‑32, RF‑90 a RF‑95, RNF‑18), excepción a RNF‑08 y parte S4 de la meta (`scripts/meta_silice_s4.py`).

## [0.6.0] - 2026-10-12

### Agregado

- T0‑A1: el producto se llama Sílice; variables `SILICE_CASO` y `SILICE_MODO_ENTREGA` (alias `ARENIA_*` hasta la 0.6.0); `.streamlit/config.toml` en 127.0.0.1 sin telemetría; licencia propietaria (`LICENSE`).
- T0‑A2: dependencias de Sílice 0.6.0 a 1.0.0 (`alembic`, `argon2-cffi`, `cryptography`; extras `bcv`, `ifc`, `ia`, `anomalias`, `similitud`) con sus licencias en la bitácora.
- T0‑A3: guardia de red única de la suite y modelo de similitud descargado antes de pytest (`scripts/descargar_modelo.py`).
- T0‑A4: meta única `scripts/meta_silice.py --version X --hasta FASE` con el bloque de regresión literal.
- T0‑A5: enmienda propuesta a NORMAS §3 (worktrees, ramas cortas por fase, un carril de núcleo).
- Migraciones con Alembic en dos destinos (caso e instalación); revisión base `caso_0001_base_0_5_0` = esquema de la 0.5.0; `preparar_base` con respaldo previo, casos en la carpeta de datos y `python -m operacion` (RF‑96, RNF‑20; S5‑1).
- S1‑0: ERS con UC‑17, UC‑18, RF‑64 a RF‑71 y RNF‑14; modelo de datos §2.5; filas previstas en el plan de pruebas; parte S1 de la meta (`scripts/meta_silice_s1.py`).
- S1‑3 (interfaz): pantallas «Precios de la empresa» e «Índices del BCV» (UC‑17); la hoja ofrece la moneda del proyecto en Parámetros, conversión a la otra moneda, origen, erosión y R11/R12 en Precios y en la auditoría; la barra exige la moneda al crear un proyecto; `ui/texto_seguro.py` escapa el texto ajeno.
- S1‑4 (SL‑E3, núcleo): reajuste por fórmula escalatoria y por comprobación directa lado a lado (`core/budget/reajuste.py`), estudio guardado con las importaciones que cita y recalculable sin cambios (RNF‑14), parcial al corte; tablas aditivas con la revisión `caso_0004_s1_reajuste`.
- S1‑4 (interfaz): pantalla «Reajuste de precios» (UC‑18): cláusula, periodos y ejecutado con su fuente, escalatoria y comprobación lado a lado en las dos monedas, guardado del estudio (con reemplazo del parcial al corte) y Excel con las hojas Reajuste y Ejecutado; los errores nombran el campo como se ve en pantalla.
- S1‑5 (cierre): recorrido guiado «Moneda, precios de empresa y reajuste»; cuarta base de prueba (`s1.db`) con la clínica convertida a Bs, la lista de empresa y un estudio de reajuste; secciones 3.9 del manual de usuario y 13 del manual técnico.

### Corregido

- SEG‑3: el informe de auditoría ya no se interpreta como Markdown; el nombre de un insumo importado con `![x](http://…)` dentro de un hallazgo R11/R12 se ve como texto, en la hoja y en las pantallas de elaborar y componer (`ui.resultado.mostrar_informe`). Queda pendiente la pantalla de actualizar precios.
