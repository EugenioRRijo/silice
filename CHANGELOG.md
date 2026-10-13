# Registro de cambios

Formato de [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) con secciones en español; versiones según
[SemVer](https://semver.org/lang/es/). Cada PR agrega una línea bajo «Sin publicar» (maestro §6.1, RV‑2); al
etiquetar, las líneas pasan a la sección de la versión. La historia anterior a la 0.5.0 está en `docs/bitacora/`.

## [Sin publicar]

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
