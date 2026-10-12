# Registro de cambios

Formato de [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) con secciones en español; versiones según
[SemVer](https://semver.org/lang/es/). Cada PR agrega una línea bajo «Sin publicar» (maestro §6.1, RV‑2); al
etiquetar, las líneas pasan a la sección de la versión. La historia anterior a la 0.5.0 está en `docs/bitacora/`.

## [Sin publicar]

### Agregado

- T0‑A1: el producto se llama Sílice; variables `SILICE_CASO` y `SILICE_MODO_ENTREGA` (alias `ARENIA_*` hasta la 0.6.0); `.streamlit/config.toml` en 127.0.0.1 sin telemetría; licencia propietaria (`LICENSE`).
- T0‑A2: dependencias de Sílice 0.6.0 a 1.0.0 (`alembic`, `argon2-cffi`, `cryptography`; extras `bcv`, `ifc`, `ia`, `anomalias`, `similitud`) con sus licencias en la bitácora.
- T0‑A3: guardia de red única de la suite y modelo de similitud descargado antes de pytest (`scripts/descargar_modelo.py`).
- T0‑A4: meta única `scripts/meta_silice.py --version X --hasta FASE` con el bloque de regresión literal.
- T0‑A5: enmienda propuesta a NORMAS §3 (worktrees, ramas cortas por fase, un carril de núcleo).
- Migraciones con Alembic en dos destinos (caso e instalación); revisión base `caso_0001_base_0_5_0` = esquema de la 0.5.0; `preparar_base` con respaldo previo, casos en la carpeta de datos y `python -m operacion` (RF‑96, RNF‑20; S5‑1).
- S1‑0: ERS con UC‑17, UC‑18, RF‑64 a RF‑71 y RNF‑14; modelo de datos §2.5; filas previstas en el plan de pruebas; parte S1 de la meta (`scripts/meta_silice_s1.py`).
- S1‑4 (SL‑E3, núcleo): reajuste por fórmula escalatoria y por comprobación directa lado a lado (`core/budget/reajuste.py`), estudio guardado con las importaciones que cita y recalculable sin cambios (RNF‑14), parcial al corte; tablas aditivas con la revisión `caso_0004_s1_reajuste`.
