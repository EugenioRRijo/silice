# Registro de cambios

Formato de [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) con secciones en español; versiones según
[SemVer](https://semver.org/lang/es/). Cada PR agrega una línea bajo «Sin publicar» (maestro §6.1, RV‑2); al
etiquetar, las líneas pasan a la sección de la versión. La historia anterior a la 0.5.0 está en `docs/bitacora/`.

## [Sin publicar]

### Agregado

- Sílice 1.2.0 (ruta, sesión 2; UC‑26, RF‑111 a RF‑118, RNF‑22 y RNF‑23): interfaz nueva y visor de solo lectura. `frontend-desktop/` (Vite, React 19, Carbon g10 y Univer, sin red externa) servida por la API en `/app` con CSP; `POST /v1/libros/replica` y `adapters/hoja_empresa/visual.py` (aspecto del libro con coordenadas de Excel); acceso del navegador por cuenta (`/v1/sesion` con cookie `HttpOnly`, anti‑CSRF y freno global con 429); campo aditivo `indicadores` en `/v1/libros/auditoria` (centésimas, sentido «exactitud», RS2‑12 y RS2‑13); el instalador lleva la interfaz compilada; trabajo `interfaz` en la CI.
- Migración del front, ola 3 (S2-B), backend de «Componer una partida» (UC‑10, UC‑11): seis rutas `/v1/composicion/*` (`opciones`, `evaluar`, `partidas/{codigo}`, `referencia`, `similares`, `guardar`) con `EDITAR_HOJA`, montos como texto y los mensajes de la página clásica; la lógica (y `guardar_composicion`, antes en `ui/elaboracion.py`) vive en `aplicacion/composicion.py`, que `ui/` reexporta.
- Interfaz nueva, migración de páginas (sesión 2b): marco con menú por rol, caso y proyecto por sesión web, página de Inicio y «Partidas similares» (`POST /v1/similares`); la lógica de las páginas pasa a `aplicacion/` y `ui/` la reexporta.
- Sílice 1.2.0 (ruta, sesión 2; UC‑26, RF‑111 a RF‑118, RNF‑22 y RNF‑23): interfaz nueva y visor de solo lectura. `frontend-desktop/` (Vite, React 19, Carbon g10 y Univer, sin red externa) servida por la API en `/app` con CSP; `POST /v1/libros/replica` y `adapters/hoja_empresa/visual.py` (aspecto del libro con coordenadas de Excel); acceso del navegador por cuenta (`/v1/sesion` con cookie `HttpOnly`, anti‑CSRF y freno global con 429); campo aditivo `indicadores` en `/v1/libros/auditoria` (centésimas, sentido «exactitud», RS2‑12 y RS2‑13); el instalador lleva la interfaz compilada; trabajo `interfaz` en la CI.
- Sesión 2b, ola 0a (backend del marco de la interfaz nueva): capa `aplicacion/` (RM-1); caso por sesión del navegador con `GET /v1/casos` y `POST /v1/casos/actual` (RM-2); `GET /v1/proyectos`; cambio de contraseña obligatorio desde la interfaz nueva (`POST /v1/sesion/contrasena`); `GET/POST /v1/sesion` informan `debe_cambiar_clave`, `acciones`, `modo_entrega` y `url_clasica` (la interfaz Streamlit, para las páginas aún no migradas); dependencia «solo desde el propio equipo» para la API (RM-4).
- Para integradores (RM-3): todas las rutas antiguas aceptan ahora la clave de API **o** la sesión del navegador con el rol de su página (tabla en `api/acceso.py`). Con `X-Silice-Clave` responden igual que antes; sin ella ni cookie, 401 con el mensaje de sesión y sin evento de «fallo de clave», como ya hacían las de `/v1/libros`.

### Cambiado

- Para integradores: las rutas `/v1/libros/*` aceptan ahora la clave de API **o** la sesión del navegador (RS2-5). Sin la cabecera `X-Silice-Clave` responden 401 con el mensaje de sesión (antes, el de la clave) y esa llamada ya no queda en el registro de accesos como fallo de clave; con una clave mala, todo sigue igual. RF‑98 ya no exige la clave en `/v1/sesion` ni en `/app` (enmienda 1.2.0 de la ERS).
- Para integradores: las rutas `/v1/libros/*` aceptan ahora la clave de API **o** la sesión del navegador (RS2-5). Sin la cabecera `X-Silice-Clave` responden 401 con el mensaje de sesión (antes, el de la clave) y esa llamada ya no queda en el registro de accesos como fallo de clave; con una clave mala, todo sigue igual.
- Sesión 2b, ola 0a (backend del marco de la interfaz nueva): capa `aplicacion/` (RM-1); caso por sesión del navegador con `GET /v1/casos` y `POST /v1/casos/actual` (RM-2); `GET /v1/proyectos`; cambio de contraseña obligatorio desde la interfaz nueva (`POST /v1/sesion/contrasena`); `GET/POST /v1/sesion` informan `debe_cambiar_clave`, `acciones`, `modo_entrega` y `url_clasica` (la interfaz Streamlit, para las páginas aún no migradas); dependencia «solo desde el propio equipo» para la API (RM-4).
- Para integradores (RM-3): todas las rutas antiguas aceptan ahora la clave de API **o** la sesión del navegador con el rol de su página (tabla en `api/acceso.py`). Con `X-Silice-Clave` responden igual que antes; sin ella ni cookie, 401 con el mensaje de sesión y sin evento de «fallo de clave», como ya hacían las de `/v1/libros`.
- Sesión 2 de la ruta (en curso): plan `docs/planes/PLAN_SESION_2_VISUAL.md`, producto y diseño de la interfaz nueva (`frontend-desktop/PRODUCT.md`, `DESIGN.md`) y enmienda 1.2.0 de la ERS (UC-26, RF-111 a RF-118, RNF-22 y RNF-23).

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
