# Sílice S5: producto e instalador (S5‑1 en la 0.6.0; el resto en la 1.0.0 «Sílice»)

| Campo | Valor |
|---|---|
| Estado | **propuesta corregida** tras la revisión por encargo del 2026‑10‑11 (requisitos, arquitectura, pruebas y calidad, verificador de hechos y **seguridad**; rulings RV‑1…RV‑26 del orquestador). Pendiente de la aprobación de Eugenio y de la revisión de usabilidad (maestro §6). Los rulings de §14 que no cierra un RV quedan «pendientes de ratificar por Eugenio» |
| Fecha | 2026‑10‑11 |
| Rama del spec | `inc/silice` (worktree `.worktrees/silice`) |
| Construcción | **ramas cortas por fase** desde el `main` del momento, con PR contra `main` y fusión al cruzar la compuerta de la fase (RV‑2): `inc/silice-s5-1`, `inc/silice-s5-2`, … Nunca una pila de ramas |
| Versión que entrega | **S5‑1** (Alembic, respaldo, `preparar_base`, casos en carpeta, `METADATA_ESPACIO`) es la **primera pieza de la 0.6.0** (RV‑1, RV‑3); **S5‑2** se adelanta como carril sin núcleo en lo que no depende de S3 (§13); **S5‑0** (documentos de la 1.0.0), **S5‑3**, **S5‑4** y **S5‑5** entregan la **1.0.0 «Sílice»**, después de 0.6.0 a 0.9.0 (maestro §5) |
| Se apoya en | [spec maestro](2026-10-11-silice-1.0.0-design.md) (S‑D3, S‑D6, §3, §4, §5, §10), [S1](2026-10-11-silice-s1-moneda-reajuste-design.md) y [S2](2026-10-11-silice-s2-presupuesto-vivo-design.md) (cada uno agrega su revisión de Alembic desde la 0.6.0), [S3](2026-10-11-silice-s3-auditor-paquete-design.md) (`instalacion.db`, cuentas, claves de API, código de instalación, pantalla de acceso, `seguridad/secretos.py`, SL‑E12; TLS diferido a S5), [S4](2026-10-11-silice-s4-asistente-ia-design.md) (extra `ia`, tablas `ia_*`), [spec SF](2026-10-04-sprint-final-prototipo-design.md) (formato), [PLAN_CIERRE.md](../../PLAN_CIERRE.md) (Med y `v1.0-tesis`) |
| Documentos que enmienda | [ERS](../ERS.md), [arquitectura](../arquitectura.md), [modelo de datos](../modelo_datos.md), [plan de pruebas](../plan_pruebas.md), [calidad](../calidad_iso25010.md), [manual de usuario](../manual_usuario.md), [manual técnico](../manual_tecnico.md) (§6 y §10.5), [README](../../README.md), `pyproject.toml`, `.gitignore`, `.github/workflows/` |
| Naturaleza de los datos | igual que [NORMAS.md §1](../../NORMAS.md): el caso de demostración que el instalador ofrece es construido y se declara como tal |

Este documento es la fuente única del diseño de S5, incluido el de Alembic aunque S5‑1 se construya en la 0.6.0
(RV‑3: S5 conserva la propiedad; el maestro y S1 citan el adelanto). El plan de sesiones (`PLAN_S5.md`) se escribe
después de aprobarlo y lo enlaza. **S5 no toca `core/` por diseño** (§5.1); el expediente que le queda (SL‑E11)
está reservado con su disparador. SL‑E12 pasó a S3 (RV‑7).

---

## 1. Qué se quiere y por qué

### 1.1 Lo que pide el maestro

Instalación local en el equipo de la empresa o en su red local, sin depender de internet (S‑D3); un instalador para
Windows con Python propio y dependencias incluidas, acceso directo que arranca y abre el navegador, y copia de
seguridad antes de cada actualización (S‑D6); migraciones con Alembic, red local y API apagadas por defecto, la API
con clave (maestro §3 y §4); versiones 0.6.0…1.0.0 con etiqueta y `CHANGELOG.md` (maestro §5); un límite de tamaño
del instalador básico con lo pesado en módulos opcionales (maestro §3, §8).

### 1.2 Lo que se encontró en el repositorio y en el equipo (2026‑10‑11, verificado)

- **Esquema sin migraciones.** `crear_esquema` es `Base.metadata.create_all` (`core/catalog/sesion.py:28‑35`):
  crea lo que falta y nunca altera una tabla. Ya costó un fallo en P2 (columna `modalidad`;
  [bitácora](../bitacora/2026-09-20-P2-hallazgo-migraciones.md)) y desde entonces rige la regla de tablas aditivas
  (manual técnico §10.5; ruling SF3‑E0). Hay **dos** `MetaData`: `core.models.Base.metadata` (25 tablas en
  `entidades.py`) y la privada `_metadata` de `adapters/espacio/persistencia.py:45` (tablas `esp_*`, creadas aparte
  por `crear_esquema_espacio`). Los specs ya prevén cambios de columnas en tablas publicadas entre la 0.6.0 y la
  0.9.0 (empresa de la lista de precios, ejecutado que cita valuaciones; ARQ‑H11): con solo
  `create_all`, una revisión base de la 0.9.0 daría `BaseNoAdoptable` con las bases de 0.6.0 y 0.7.0. Por eso
  Alembic entra con la 0.6.0 (RV‑3, §6).
- **Dos bases, no una.** S3 separa la **base de la instalación** (`instalacion.db`: cuentas, sesiones, claves de
  firma, empresa propia, empresas registradas, claves de API, `evento_acceso`; `Base` propia en
  `seguridad/modelo.py`) de la **base del caso** (presupuestos, espacio, `paq_*`, `ia_*`). S5 migra, respalda y
  adopta las dos (RV‑4, §6).
- **Nueve páginas, `ui/caso.py:128` y la API (`api/dependencias.py:22`) llaman a `crear_esquema` al abrir**;
  `estado_caso` (`ui/caso.py:128`) ejecuta DDL con solo mirar el estado.
- **Ruta libre del caso.** `ui/paginas/inicio.py:50` ofrece un `st.text_input` con la ruta del caso y
  `fijar_caso(texto)` la usa sin restricción. Con la red local encendida, cualquier usuario con sesión haría que el
  servidor abra o cree un SQLite en cualquier ruta, incluida una UNC (`\\equipo\x\a.db`), que en Windows entrega el
  hash NTLM del usuario (SEG‑5, ARQ‑H7). S5 lo cierra con la lista de casos (RV‑5, §6.6).
- **Rutas relativas al directorio de trabajo.** La base por defecto es `data/apu.db` (`ui/caso.py:37`,
  `api/dependencias.py:14`, `scripts/seed*.py`); el visor lee `data/samples/tanquilla.ifc`
  (`ui/paginas/visor.py:52`). La interfaz **importa al cargar el módulo** `scripts.seed_demo`
  (`ui/paginas/inicio.py:18`), `scripts.seed` (`ui/paginas/actualizacion.py:69`) y `scripts.simular_lista`
  (`ui/paginas/simulador.py:22`), y estos importan `tests.fixtures` (NORMAS §6 ya lo advierte). Un instalador que
  copie solo `core/ adapters/ ml/ ui/ api/` no arranca; uno que copie todo `tests/fixtures/` arrastraría los `.xls`
  del BCV, las grabaciones de S4, las bases de prueba y el catálogo de planos (ARQ‑H21).
- **Streamlit 1.62.0, probado aquí con un Python autónomo de `uv`:**
  - sin `server.address`, escucha en **todas las interfaces** (`0.0.0.0:8598` y `[::]:8598` en `netstat`) e imprime
    una «External URL» con la IP pública: el arranque actual (README, manual de usuario §2) ya expone la aplicación a
    la red. Con `--server.address 127.0.0.1` escucha solo en el bucle local y no imprime esa URL;
  - `browser.gatherUsageStats` vale `true` por defecto (`streamlit config show`): envía estadísticas de uso a
    Streamlit, lo que contradice RNF‑08;
  - `GET /_stcore/health` responde `200 ok` a los ~2 s con una app mínima; el servidor arranca sobre Uvicorn.
- **No hay `.streamlit/config.toml` versionado** (ni en `main` ni en `inc/silice`, verificado hoy): el camino de
  desarrollo y `INICIAR_PROTOTIPO.bat` arrancan con telemetría y en todas las interfaces. Arreglarlo **ya en `main`**
  con un `.streamlit/config.toml` (`server.address="127.0.0.1"`, `browser.gatherUsageStats=false`,
  `client.showErrorDetails="none"`, `server.maxUploadSize=20`) es un PR de cinco minutos que se recomienda antes
  de la 0.6.0, fuera de S5 (ARQ‑H18). S5 lo cita **como pendiente**; si al construir S5‑2 ya existe, lo cita como
  existente y lo toma como base del archivo oficial de `{app}\codigo` (§10.1).
- **El visor 3D descarga three.js de `cdnjs.cloudflare.com`** (`ui/paginas/visor.py:55`; excepción declarada en
  RNF‑08): sin internet, esa pantalla no funciona.
- **Versión:** `pyproject.toml` dice `0.1.0`, `api/main.py:18` fija `version="0.1.0"` a mano y existe la etiqueta
  anotada `v0.5.0` (8610053, PR #29), cuyo mensaje dice «el versionado se alinea en S5». No hay `CHANGELOG.md`.
  `.python-version` dice `3.13`, la de la CI.
- **Extras:** `xgboost` está en el extra `ml`, pero ningún código del producto lo importa (solo el nombre de una
  técnica en `ml/prediction/reglas.py:62`). La pantalla de actualización usa `scikit-learn` (atípicos,
  `ui/paginas/actualizacion.py:387‑393`); la similitud usa `sentence-transformers` y descarga el modelo
  `paraphrase-multilingual-MiniLM-L12-v2` la primera vez (RNF‑08).
- **Precedente sin versionar** en el checkout principal: `INICIAR_PROTOTIPO.bat` (descarga `uv` de internet si falta,
  sin fijar versión y con `-ExecutionPolicy Bypass`; `uv sync --all-extras`, siembra la demostración y arranca sin
  `server.address`), `scripts/crear_paquete_portable.ps1` (empaqueta todo `data/`, incluidos los PDF de MaPreX),
  `requirements.txt` (redundante con `uv.lock`, sin huellas) y `COMPARTIR_ONLINE.bat`, que abre un **túnel público**
  de Cloudflare sin autenticación y descarga `cloudflared` «latest» sin comprobar su huella: eso es un servidor en
  internet, fuera de la 1.0.0 (maestro §1) y contrario a §4. S5 no los toca; los sustituye (§14, RS5‑12). Su riesgo
  actual quedó registrado en la revisión de seguridad del 2026‑10‑11 (H1–H3).
- **Inno Setup:** última 7.0.2 (rama 6: 6.7.3); `windows-2022` y `windows-2025` de GitHub Actions traen
  **InnoSetup 6.7.1** (README de `actions/runner-images`, consultado hoy); el español viene incluido.

### 1.3 Mediciones de tamaño (2026‑10‑11)

Tamaño instalado por paquete sumado desde los `RECORD` del entorno `.worktrees/sf5/.venv` (CPython 3.13, ruedas de
Windows, `uv.lock` vigente); conjuntos por extra con `uv export --frozen --no-dev --extra <x>`; incremento sobre el
básico. «Comprimido» es `tar | xz -9` de esos archivos, **estimación** de lo que dará LZMA2 de Inno Setup (el
número real se mide en S5‑3.4).

| Capa | Paquetes clave | Instalado | Comprimido (xz ‑9) |
|---|---|---|---|
| Python autónomo (python-build-standalone 3.12.13; la 3.13 se mide en S5‑0.3) | — | 68 MB | 15 MB |
| Código y datos del repositorio (`core adapters ml ui api scripts tests/fixtures data`; cota superior: el manifiesto de §7.1 copia menos) | — | ~11 MB | 7 MB |
| Básico: base + `ui` + `api` + `planos` + `informes` | pandas, numpy, streamlit, pyarrow (86), pydeck (47), matplotlib, ezdxf | 348 MB | 62 MB |
| `civil` | ifcopenshell (81), shapely | +87 MB | 16 MB |
| Anomalías (`scikit-learn`, `scipy`, `joblib`, `threadpoolctl`) | | +136 MB | 26 MB |
| `xgboost` | | +58 MB | no va al instalador |
| Similitud: `sentence-transformers` y su cierre (torch 466, transformers, tokenizers…) | | +589 MB | 88 MB |
| Modelo `paraphrase-multilingual-MiniLM-L12-v2` (`model.safetensors` 449 MB) | | 458 MB | 408 MB |
| Dependencias de S1 (`bcv`: `xlrd`, < 1 MB), S3 (`argon2-cffi`, `cryptography`; `ifctester` va en `civil`), S4 (`anthropic`, cliente de Ollama, `keyring`) y `alembic` | | **a medir en S5‑0.3** | **a medir en S5‑0.3** |

Con esas cifras: **instalador básico ≈ 126 MB** más S1/S3/S4 (Python, código, básico, civil y anomalías), unos
650 MB instalado; el módulo de **similitud ≈ 496 MB** comprimido y ≈ 1,05 GB instalado; el **completo ≈ 622 MB**
comprimido sin S3/S4. Los paquetes CUDA de la rama Linux del candado no se instalan en Windows.

### 1.4 Criterio de éxito de S5

En un Windows 10 u 11 limpio, **sin internet y sin permisos de administrador**, una persona instala Sílice con el
asistente, hace doble clic en el acceso directo, el navegador se abre en la aplicación y crea el primer administrador
(S3). Después instala la versión siguiente: **sus dos bases** (instalación y casos) se respaldan juntas, se migran y
sus presupuestos recargan con el mismo informe. Al desinstalar, sus datos quedan. Con el asistente de IA apagado,
nada de esto abre una conexión fuera del equipo. La CI lo comprueba en cada versión (§11).

---

## 2. Relación con S1–S4, el plan de cierre y Med

- **Alembic desde la 0.6.0 (RV‑3).** S5‑1 es la primera pieza de la 0.6.0: revisión base del caso = **esquema de la
  0.5.0**; desde ahí **cada S agrega su revisión** (S1 la suya en la 0.6.0, S2 en la 0.7.0, S3 en la 0.8.0, también la
  primera de la base de la instalación, y S4 en la 0.9.0). La prueba de deriva (RNF‑20) está activa desde S1. Nadie
  marca bases con `stamp`: hay un solo camino de migración (DA‑S5‑4; S1 §5.2 se alinea, REQ‑18).
- **Base de prueba por versión (RV‑3, PRU‑H15).** Cada versión genera su base de prueba **en su compuerta de
  cierre**, con el código de su etiqueta, y una ficha escrita con ese mismo código (total literal, huella del
  informe, filas por tabla). RF‑96 compara contra esa ficha, nunca contra un recálculo con el código nuevo. La de la
  0.5.0 la genera S5‑1 desde `v0.5.0`.
- **S3** deja a S5: el paso del código de instalación (S3 §5.5), extender la clave de la API a las rutas antiguas
  (S3 §10) y decidir TLS en la red local (RS3‑8). S5 responde en §8. S3 recibe de S5 el expediente SL‑E12
  (`busy_timeout`, WAL, `BEGIN IMMEDIATE`; RV‑7) y la función `operacion.red.es_cliente_local` para la pantalla de
  acceso (§8.2).
- **S4** pone el extra `ia`; S5 lo incluye en el instalador básico (§7.2). La prueba de humo corre con el asistente
  apagado (RV‑23).
- **Orden e integración (RV‑1, RV‑2).** 0.6.0 = S5‑1 + S1; 0.7.0 = S2; 0.8.0 = S3; 0.9.0 = S4; 1.0.0 = resto de S5.
  `main` es la única rama de integración; las etiquetas se ponen en orden numérico en `main`. S5‑2 puede adelantarse
  como carril sin núcleo (§13).
- **Med y `v1.0-tesis`.** Las mediciones con las dos personas (maestro §5 y §7; indicador 3, RNF‑04, CP‑07, RNF‑13)
  se hacen sobre el **instalador `v1.0.0-rc.N`**, en un equipo preparado con él. `v1.0-tesis` (F3 de PLAN_CIERRE)
  apunta siempre a un commit que ya tiene una etiqueta `v1.0.x` (§9.3).

---

## 3. Alcance

**Incluye:** Alembic en dos destinos (instalación y caso) con revisión base de la 0.5.0, adopción de bases de la
0.5.0, respaldo automático de las dos bases en un mismo juego y restauración con revisión de los eventos de seguridad
perdidos (§6); abrir casos solo desde la carpeta de casos (§6.6); instalador de Windows con Inno Setup, Python
autónomo, dependencias sin internet, componentes opcionales, acceso directo, actualización y desinstalación que
conserva los datos (§7); arranque y parada, configuración, red local en la IP explícita de una interfaz y API apagadas
por defecto, clave en toda la API, registro sin secretos (§8); versionado, `CHANGELOG.md` y etiquetas (§9);
endurecimiento, tabla de amenazas propia y manuales, incluido un manual de instalación nuevo (§10); construcción,
firma de `SHA256SUMS`, auditoría de dependencias y prueba de humo del instalador en la CI (§11).

**No incluye:** instalador para Linux o macOS (en Linux sigue el camino de desarrollo con `uv sync`, RNF‑07);
Windows ARM64; TLS en la red local (RS5‑8); un servidor en internet o túneles públicos (2.x); firma de código del
instalador (RS5‑10); actualización automática por internet; base de datos en una carpeta compartida de red; IPv6
en la red local.

---

## 4. Requisitos (enmienda a la ERS, IEEE 830)

**Numeración** (maestro §9): UC‑24; RF‑96 a RF‑99; RNF‑19 y RNF‑20; expediente SL‑E11. Se usan todos los números
de requisito; **SL‑E11 queda reservado y vacante** mientras no se cumpla su disparador (§5.1). SL‑E12 pasó a S3
con su expediente genérico (RV‑7).

### 4.1 Caso de uso

#### UC‑24 — Instalar, actualizar y operar Sílice en un equipo

- **Actor principal:** administrador de la instalación (S3). **Secundarios:** quien arma y quien revisa, que solo
  usan el acceso directo o el navegador.
- **Precondiciones:** Windows 10 22H2 u 11, x64; una cuenta de usuario (no hace falta que sea administradora); el
  instalador con su `SHA256SUMS` y la firma de este (§10.4).
- **Flujo principal**
  1. El administrador comprueba la huella del instalador contra `SHA256SUMS` y la firma de `SHA256SUMS` con la clave
     del proyecto (§10.4), ejecuta el asistente y elige los componentes (§7.2).
  2. El asistente copia el programa en `{app}` sin internet, crea los accesos directos y ejecuta
     `operacion migrar`: crea (o respalda y migra) `instalacion.db` y cada caso de `datos\casos\` (§6).
  3. El administrador abre «Sílice»: el lanzador prepara las bases, arranca en `127.0.0.1` y abre el navegador.
     Como no hay usuarios, deja el código de instalación en la carpeta de datos y en la consola.
  4. El administrador crea el primer administrador con ese código (UC‑21 de S3) y entra.
  5. Quien arma (o el administrador) elige un caso de la **lista** de `datos\casos\` o sube uno; si el caso no está
     en `head`, se migra con respaldo previo (§6.4 y §6.6).
  6. Opcional: el administrador activa la red local desde el equipo servidor, eligiendo la interfaz (§8.2), y la
     API (§8.3).
  7. Para actualizar, ejecuta el instalador de la versión siguiente: detiene Sílice, reemplaza el programa,
     respalda y migra las dos bases.
  8. Para parar, cierra la ventana de Sílice o usa «Detener Sílice».
- **Flujos alternativos**
  - *1a. La huella o la firma no coinciden:* no se instala; el manual dice a quién avisar.
  - *2a. Espacio en disco insuficiente:* el asistente lo dice antes de copiar.
  - *2b. Ya hay un Sílice en marcha:* el asistente lo detiene (`PrepareToInstall`) antes de copiar.
  - *3a. Ya hay un Sílice en marcha:* el acceso directo abre el navegador y no arranca otro.
  - *3b. El puerto está ocupado por otro programa:* mensaje con el puerto y cómo cambiarlo.
  - *3c. Base de la 0.5.0 con columnas que no cuadran (anterior a P2 o alterada a mano), no adoptable:* no se toca y
    se explica.
  - *3d. Base de una versión más nueva que el programa (bajó de versión):* no arranca y ofrece restaurar el respaldo
    previo.
  - *3e. La IP de la red local elegida ya no existe (la red cambió):* arranca solo en `127.0.0.1` y lo avisa.
  - *3f. Hay un túnel local conocido en ejecución (`cloudflared`, `ngrok`):* arranca y avisa que el túnel anula el
    filtro de IP y la regla de «solo desde este equipo» (§10.4).
  - *5a. Ruta UNC, absoluta o con `..`:* se rechaza sin crear ningún archivo.
  - *5b. Función de similitud sin su módulo:* la pantalla dice cuál módulo falta (RF‑97 g).
  - *6a. Activar la red local sin poder elevar permisos:* queda apagada y se explica.
  - *7a. Una migración falla:* las bases se restauran del juego de respaldo, Sílice no arranca y explica qué hacer.
  - *7b. Restaurar un juego de respaldo que trae `instalacion.db`:* Sílice lista los eventos de seguridad perdidos y
    exige que el administrador los revise antes de las operaciones sensibles (§6.5).
  - *8a. Desinstalar:* los datos quedan y el asistente dice dónde.
- **Postcondiciones:** programa en `{app}`; datos en `%LOCALAPPDATA%\Silice` con `instalacion.db` y los casos en
  `head` y un juego de respaldo por cada migración; red local y API en el estado configurado (apagadas por defecto);
  ninguna conexión saliente salvo el asistente en modo nube activado por el administrador; tras desinstalar, los
  datos y los respaldos siguen ahí.

UC existentes que se enmiendan: **UC‑12** (los recorridos parten del acceso directo, no de la terminal) y **UC‑21**
de S3 (el primer administrador se crea con el código que el arranque deja en la carpeta de datos, §8.1).

### 4.2 Requisitos funcionales

Prioridad: E = esencial, D = deseable. Fases de §13.

| RF | Requisito | UC | Pri. | Fase | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑96 | **Migraciones con respaldo y vuelta atrás, en dos bases.** El esquema se versiona con Alembic en dos destinos, cada uno con su `alembic_version` y su lista `METADATAS` explícita (§6.1): la **instalación** (`seguridad`) y el **caso** (`core.models`, `METADATA_ESPACIO`, `paquete`, `asistente`). La revisión base del caso es el esquema de la 0.5.0 y cada cambio posterior trae su revisión, desde la 0.6.0. Antes de aplicar cualquier revisión pendiente se respaldan **juntas** la instalación y los casos que se migran, en un juego con una sola ficha; si la migración falla, se restauran solas. Las bases de la 0.5.0 se adoptan (§6.4). Un caso se abre solo con `preparar_base` y desde `datos\casos\` (§6.6) | UC‑24 | E | S5‑1 (0.6.0) | (a) una base vacía, una base de la 0.5.0 sin `alembic_version` y la base de prueba de cada versión 0.6.0…0.9.0 (generada en su compuerta con el código de su etiqueta) llegan a `head`, y sus presupuestos recargan con el total literal, la huella del informe y las filas por tabla **de su ficha**; lo mismo para `instalacion.db` desde la 0.8.0; (b) cada base del juego de respaldo pasa `PRAGMA integrity_check` y su huella está en la ficha; (c) con un fallo inyectado en una revisión, la huella SHA‑256 de cada base tras el intento es igual a la de antes; (d) una base con revisión desconocida o no adoptable no se modifica (huella igual) y el mensaje dice qué hacer; (e) una ruta UNC, absoluta o con `..` se rechaza sin crear archivo, y `estado_caso` no emite DDL; (f) restaurar un juego con `instalacion.db` lista los eventos de seguridad perdidos y deja pendiente la revisión del administrador |
| RF‑97 | **Instalador para Windows.** Un `Silice-<versión>.exe` (básico) y un `Silice-<versión>-completo.exe` (con el módulo de similitud) instalan sin internet ni permisos de administrador: Python autónomo, dependencias y código según el manifiesto; crean el acceso directo «Sílice» que arranca y abre el navegador y «Detener Sílice»; la actualización detiene Sílice, reemplaza el programa y migra con respaldo; la desinstalación borra el programa y **conserva los datos** | UC‑24 | E (básico); D (completo) | S5‑3 | prueba de humo de §11.2: (a) instalación silenciosa en una ruta con espacios y acentos; (b) salud `200` ≤ 60 s; (c) solo `127.0.0.1` escuchando y nada en `0.0.0.0` ni en `::`; (d) nada escrito en la carpeta del programa (inventario igual antes y después); (e) actualización con un juego de respaldo y las dos bases en `head`; (f) desinstalación sin carpeta de programa y con la carpeta de datos intacta; (g) sin el módulo de similitud, la pantalla de similares lo dice con su nombre; (h) `{app}\codigo` contiene exactamente lo del manifiesto: ni `tests/fixtures/` completo ni otro `.streamlit/config.toml` que el oficial |
| RF‑98 | **Operación segura por defecto.** Arranque y parada con una sola instancia; red local **apagada**, activable solo desde el equipo servidor con elevación, escuchando en la **IP explícita** de la interfaz elegida (nunca `0.0.0.0`) con regla de cortafuegos limitada a esa IP, a la subred local y al perfil Privado; API **apagada**, en la misma dirección, con clave en **todas** sus rutas salvo `/salud`, `TrustedHostMiddleware` y filtro de redes privadas (defensa adicional; el control es la clave); las operaciones sensibles solo desde el propio equipo y el aviso «sin cifrar» en la pantalla de acceso para clientes remotos (§8.2); registro de errores rotativo **sin secretos**; **ninguna conexión saliente salvo el asistente en modo nube activado por el administrador** (excepción de RNF‑08) | UC‑24 | E | S5‑2 | pruebas de §12: configuración por defecto; ninguna configuración produce `0.0.0.0` en la orden de Streamlit ni de Uvicorn; con la API activa, `401` sin clave en cada ruta del esquema, `403` desde una IP pública simulada y `400` con un `Host` ajeno; una operación sensible pedida desde una IP remota se rechaza; un registro con secretos sembrados no contiene ninguno; prueba de humo **con el asistente apagado**: **0** conexiones salientes desde el arranque hasta la parada (cortafuegos de salida, muestreo de conexiones, proxy testigo y navegador sin interfaz, §11.2) |
| RF‑99 | **Versión y registro de cambios.** Una sola fuente de la versión (`pyproject.toml`); la API, la pantalla «Acerca de» y el instalador la leen de ahí; «Acerca de» muestra además las revisiones de los dos esquemas, la carpeta de datos y los módulos instalados; `CHANGELOG.md` con una sección por versión; una etiqueta anotada por versión | UC‑24 | E | S5‑0, S5‑2, S5‑4 | `scripts/meta_silice.py --version <x>` (RV‑17): versión de `pyproject` = la de la API = la del instalador; sección del `CHANGELOG` para la versión en curso con fecha; en un *push* de etiqueta, la etiqueta (`v` + SemVer) coincide con `pyproject` normalizado (PEP 440) o la CI falla |

### 4.3 Requisitos no funcionales (ISO/IEC 25010)

Se usan los nombres de la edición de 2011, como [calidad_iso25010.md](../calidad_iso25010.md); en la edición de 2023
«portabilidad» se llama «flexibilidad» (a confirmar en S5‑0 contra la norma antes de citarlo en la tesis).

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑19 | **Portabilidad** (instalabilidad, adaptabilidad, reemplazabilidad) | Artefactos **comprimidos** (los `.exe`): básico **≤ 150 MB** y completo **≤ 650 MB** (estimado ≈ 622 MB sin S3/S4, §1.3). Instalado: básico ≤ 900 MB; el completo instalado no tiene límite propio (≈ 1,7 GB estimado). Se instala sin internet y sin administrador, en Windows 10 22H2 y 11 x64, en una ruta con espacios y caracteres no ASCII. Del acceso directo a la salud `200`: ≤ 60 s en la CI y ≤ 20 s en el equipo de desarrollo. Actualizar conserva el 100 % de los datos de las dos bases (filas por tabla y huella de los informes de la ficha) | tamaño de los artefactos de la CI (falla si se pasa); prueba de humo de §11.2; tiempo de arranque medido en el equipo de desarrollo (mediana de cinco, como RNF‑11) y anotado en plan_pruebas §10 con fecha y los cinco valores: la meta comprueba que la medición **dejó su cifra** (sin cifra es FALLA, PRU‑H21); la instalación en una cuenta estándar sin administrador, a mano en S5‑5 (la CI corre como administrador) |
| RNF‑20 | **Mantenibilidad** (modificabilidad, capacidad de prueba) | Cero deriva de esquema **en cada destino**: una base llevada a `head` por las migraciones es igual a la creada con `create_all` de sus `METADATAS`, y la autogeneración de Alembic contra ella no propone cambios; toda `MetaData` con tablas está registrada en la lista de su destino; cada revisión baja y vuelve a subir; el instalador se construye solo desde `uv.lock` (`--frozen`) con un manifiesto de archivos y huellas. Activa desde la 0.6.0 (RV‑3) | `tests/integration/test_migraciones.py` en Linux y Windows en cada PR (la búsqueda de `MetaData` recorre `core`, `adapters`, `seguridad`, `paquete`, `asistente` y `ui`); `scripts/meta_silice.py`; el manifiesto se publica con el instalador |

---

## 5. Arquitectura (vistas 4+1)

### 5.1 Principio que se conserva

NORMAS §2: núcleo cerrado. **S5 no modifica `core/`.** `crear_esquema` se queda como está (lo usan las pruebas en
memoria y el camino de desarrollo); la operación del producto vive fuera del núcleo y solo importa
`core.catalog`/`core.models`. El expediente reservado se abre **solo** si se cumple su disparador:

| Expediente | Disparador | Cambio que pediría |
|---|---|---|
| SL‑E11 | una revisión necesita borrar o cambiar una restricción **sin nombre** de `core/models` y el `naming_convention` por revisión de `batch_alter_table` no alcanza | convención de nombres en `Base.metadata` (cambia los nombres de restricciones nuevas; no los existentes) |

Si no se dispara, queda **vacante** y así se declara al cerrar S5. SL‑E12 (`busy_timeout`, diario WAL y
`BEGIN IMMEDIATE` en las transacciones que crean versión) es de S3 desde la revisión (RV‑7); S5 lo da por hecho en la
red local y en la prueba de humo.

### 5.2 Vista lógica y de desarrollo

| Pieza | Qué hace | Importa | Toca `core/` |
|---|---|---|---|
| `migraciones/` (nuevo; S5‑1): `caso/` (`env.py`, `script.py.mako`, `versions/caso_0001_base_0_5_0.py`) e `instalacion/` (`env.py`, `script.py.mako`, `versions/`, sin revisiones hasta S3‑1); `comun.py` (ayudante `crear_o_verificar`) | dos entornos de Alembic sin `alembic.ini` (configuración programática), cada uno con su `alembic_version` en su propia base y su lista explícita: `METADATAS_CASO` = `core.models.Base.metadata`, `METADATA_ESPACIO`, y las de `paquete` (S3) y `asistente` (S4) cuando existan; `METADATAS_INSTALACION` = la de `seguridad.modelo` (S3) | `core.models`, `adapters.espacio.persistencia`, `seguridad`, `paquete`, `asistente` (solo sus modelos) | no |
| `operacion/` (nuevo, sin Streamlit): `rutas.py`, `config.py`, `base_datos.py`, `respaldo.py`, `lanzador.py`, `red.py`, `registro.py`, `version.py`, `__main__.py` | carpetas de datos; configuración; `preparar_base` (instalación y caso), lista de casos y validación de rutas (§6.6); respaldar y restaurar el juego; arrancar y parar; red local (interfaces, reglas, `es_cliente_local`); registro; versión; CLI `python -m operacion …` | `core.catalog`, `migraciones`, biblioteca estándar | no |
| `api/seguridad.py` (nuevo) y `api/main.py` | clave en todas las rutas (cabecera que fija S3‑0), `TrustedHostMiddleware`, filtro de redes privadas, documentación interactiva apagada en el producto, versión desde `operacion.version` (hoy fija en `api/main.py:18`) | `operacion.config`, `operacion.version` | no |
| `api/dependencias.py` | abre el caso que fijó el lanzador (ya en `head`); si no está en `head`, responde `503` con mensaje en vez de crear tablas | `operacion.base_datos` | no |
| `ui/caso.py` y `ui/paginas/inicio.py` | el caso se elige de la lista de `datos\casos\` (o se sube); el `st.text_input` de la ruta desaparece; `estado_caso` solo lee (sin `crear_esquema`); abrir pasa por `preparar_base` | `operacion.base_datos` | no |
| `ui/paginas/{inicio,actualizacion,simulador}.py` | las importaciones de `scripts.*` pasan **dentro de la acción** que las usa (sembrar, simular), no al cargar el módulo (RV‑25) | — | no |
| `ui/paginas/acerca.py` (nueva) y la pestaña **Instalación** de `ui/paginas/administracion.py` (S3; RV‑22) | versión, revisiones de los dos esquemas, carpeta de datos, módulos; estado de red local y API, respaldos (crear, listar, descargar), revisión de eventos perdidos tras una restauración | `operacion` (nunca `operacion.lanzador`) | no |
| `ui/paginas/visor.py` | three.js servido desde el paquete (`ui/estaticos/`), no desde la CDN | — | no |
| `adapters/espacio/persistencia.py` | exporta `METADATA_ESPACIO` (hoy `_metadata` privada) | — | no |
| `instalador/` (nuevo): `silice.iss`, `construir.py`, `manifiesto.toml`, `streamlit_config.toml`, `humo.ps1`, `navegador.py`, `licencias/` | construir el instalador y probarlo | — (no se importa desde el código) | no |
| `pyproject.toml` | `alembic` como dependencia base; `bcv` (`xlrd`) entra al básico (RV‑24); `ifctester` en `civil` (o un extra `ifc` nuevo), con importación diferida en `adapters/espacio/planos/ids.py`; extras `anomalias` (`scikit-learn`) y `similitud` (`sentence-transformers`); `ml` = `anomalias` + `similitud` + `xgboost` para la CI y la investigación. Los cambios de dependencias van en el PR temprano «dependencias Sílice» (RV‑2) | — | — |

`tests/unit/test_arquitectura.py` (o el archivo propio de S5, RV‑2) gana: `core` no importa `operacion` ni
`migraciones`; `operacion` no importa `streamlit`, `ui` ni `api`; `ui` y `api` solo importan `operacion.config`,
`operacion.version`, `operacion.respaldo` y `operacion.base_datos` (RV‑5); `migraciones` no importa `ui` ni `api`;
ningún módulo de `ui/` importa `scripts.*` en el nivel superior (búsqueda en el árbol sintáctico);
`PAQUETES_FUERA_DEL_NUCLEO` suma `operacion` y `migraciones` (si lleva `__init__`) (RV‑22). `known-first-party` de
ruff suma los dos paquetes.

### 5.3 Vista física: dónde vive cada cosa

```
%LOCALAPPDATA%\Programs\Silice\        {app}: programa (se reemplaza entero al actualizar)
  python\                              CPython autónomo + capa básica en Lib\site-packages
  modulos\similitud\                   paquetes de similitud + modelo (solo con el componente)
  codigo\                              core adapters ml ui api operacion migraciones seguridad paquete asistente
                                       + scripts y tests\fixtures solo en lo que fija el manifiesto (§7.1), data (lista blanca),
                                       pyproject.toml, .streamlit\config.toml (el oficial, único)
  manifiesto.json  LICENCIAS\  unins000.exe
%LOCALAPPDATA%\Silice\                 datos del usuario: el desinstalador NO los toca
  config\silice.toml                   red local (y su IP), API, puertos, nivel del registro
  datos\instalacion.db                 base de la instalación (seguridad: cuentas, sesiones, claves, empresa, evento_acceso)
  datos\casos\silice.db                caso por defecto
  datos\casos\demostracion.db          caso construido de demostración (solo si se pide)
  datos\casos\<nombre>.db              otros casos, creados o subidos desde Inicio
  datos\codigo_instalacion.txt         código de un solo uso de S3 (se borra al usarlo)
  datos\paquetes\                      paquetes auditados recibidos y emitidos (S3)
  respaldos\<AAAAMMDD-HHMMSS>_<motivo>\ juego: instalacion.db + casos\*.db + ficha.json
  registros\silice.log (+ .1 … .5)     registro rotativo
  estado\servidor.json                 PID, dirección, puertos y hora de arranque de la instancia viva
```

- `{app}` es `{autopf}\Silice`, que en modo sin administrador Inno resuelve a `{userpf}` (verificado en la ayuda de
  Inno Setup); que `{userpf}` sea `%LOCALAPPDATA%\Programs` se confirma en la prueba de humo.
- **Límite declarado (SEG‑16):** `%LOCALAPPDATA%\Programs` lo puede escribir **cualquier proceso del usuario**, sin
  elevación; un programa malicioso con los permisos del usuario puede cambiar el código de Sílice o su `python.exe`,
  y la regla de entrada del cortafuegos de la red local autoriza a ese `python.exe` modificable. Es el costo de
  instalar sin administrador (RS5‑3); queda en la tabla de amenazas (§10.4).
- Los datos van en `{localappdata}` (igual en ambos modos de Inno), **fuera** de la carpeta del programa: OneDrive no
  sincroniza `%LOCALAPPDATA%` y el desinstalador solo borra lo que instaló. `SILICE_DATOS` cambia la carpeta (pruebas
  y casos especiales). Los nombres de carpeta van sin tilde (`Silice`); el nombre visible es «Sílice».
- **En desarrollo** (RV‑4): `SILICE_DATOS` vale por defecto `data/`, con la misma disposición (`data/instalacion.db`,
  `data/casos/`, `data/codigo_instalacion.txt`, `data/paquetes/`); `.gitignore` suma `instalacion.db`,
  `codigo_instalacion.txt`, `paquetes/` y `casos/` (ARQ‑H9). Las variables `ARENIA_CASO` y `APU_BASE` siguen
  existiendo para las pruebas y el camino de desarrollo.
- El directorio de trabajo del servidor es `{app}\codigo` (las rutas relativas de `data/samples` y `data/precios`
  siguen valiendo). El lanzador fija `SILICE_INSTALACION` hacia `datos\instalacion.db` y `ARENIA_CASO` y `APU_BASE`
  hacia `datos\casos\silice.db`: ninguna escritura cae en la carpeta del programa (lo comprueba la prueba de humo).
- `keyring` (S4) guarda la clave de IA de la empresa por usuario de Windows: **no viaja en los respaldos** y hay que
  registrarla de nuevo en otro equipo (RV‑24; se declara en el manual).

### 5.4 Vista de procesos

**Arranque** (`python.exe -E -s -B -m operacion arrancar`, desde el acceso directo):

1. Si `estado\servidor.json` existe y `/_stcore/health` responde, abre el navegador y termina (3a).
2. Lee `config\silice.toml` (lo crea con los valores por defecto si falta) y configura el registro. Si la carpeta de
   datos es una ruta UNC, avisa; si encuentra un túnel local conocido en ejecución, avisa (3f).
3. `preparar_base` sobre `instalacion.db` y el caso por defecto: si hay revisiones pendientes, respalda el juego y
   migra (§6); si falla, restaura y se detiene con mensaje. Si no hay usuarios (S3), genera el código de instalación
   y lo muestra en la consola.
4. Elige la dirección: `127.0.0.1`, o la IP de la interfaz guardada si `red_local = true` y esa IP sigue existiendo
   en el equipo (si no, `127.0.0.1` y aviso, 3e). Lanza Streamlit como proceso hijo con las opciones de §10.1 y, si
   `api.activa`, Uvicorn con `api.main:app` en la misma dirección; escribe `servidor.json`.
5. Espera la salud `200` (hasta 60 s), abre `http://<dirección>:<puerto>` con `webbrowser` y queda en primer plano.

**Parada:** cerrar la ventana de Sílice (minimizada, «Para detener Sílice, cierre esta ventana») o el acceso
«Detener Sílice» (`operacion parar`: termina los procesos de `servidor.json` y borra el archivo). Las banderas `-E`
(ignora `PYTHON*` del entorno), `-s` (sin `site-packages` del usuario) y `-B` (sin `.pyc` nuevos) aíslan el Python
autónomo de cualquier otro Python del equipo.

**Abrir otro caso** (Inicio): la lista viene de `operacion.base_datos.listar_casos`; al elegir, `preparar_base` valida
la ruta y, si el caso no está en `head`, lo migra con respaldo previo del juego (§6.6).

**Actualización:** el instalador detiene Sílice (`operacion parar`, desde `PrepareToInstall`), borra `{app}\python`,
`{app}\modulos` y `{app}\codigo` (`[InstallDelete]`, para que no queden paquetes de la versión anterior), copia la
nueva versión y ejecuta `operacion migrar`, que lleva a `head` la instalación y **todos** los casos de
`datos\casos\` con un solo juego de respaldo. El arranque vuelve a comprobar las revisiones: la migración tiene un
solo camino de código y es idempotente.

### 5.5 Decisiones de diseño

| # | Decisión | Alternativa descartada | Por qué |
|---|---|---|---|
| DA‑S5‑1 | Dependencias **preinstaladas al construir**, en capas (básica dentro del Python autónomo; similitud en `modulos\similitud` añadida con un `.pth`) | carpeta de ruedas e instalación con `uv` durante el asistente | instalar no ejecuta un resolvedor en el equipo del cliente; lo que se probó en la CI es lo que se instala |
| DA‑S5‑2 | Paquetes en el Python autónomo, sin entorno virtual | `uv venv --relocatable` | un entorno virtual guarda la ruta de su intérprete; el Python autónomo movido de carpeta sigue funcionando (probado hoy con Streamlit 1.62.0) |
| DA‑S5‑3 | Instalación **por usuario** (`PrivilegesRequired=lowest`) | por equipo en `Program Files` | instala sin administrador; el administrador solo hace falta para la regla de cortafuegos de la red local. Costo declarado en §5.3 |
| DA‑S5‑4 | Un solo camino de migración: siempre `upgrade head`, con una revisión base **idempotente** que crea las tablas que faltan y verifica las existentes; las revisiones que solo crean tablas usan el mismo ayudante | `create_all` + `stamp head` para bases nuevas (receta del libro de cocina de Alembic) | la base nueva, la adoptada y la actualizada pasan por el mismo código y las mismas pruebas; nadie usa `stamp` |
| DA‑S5‑5 | Ventana de consola minimizada como «servidor» | ícono en la bandeja o servicio de Windows | cerrar la ventana detiene todo, sin procesos huérfanos; es lo que Eugenio ya usó con el `.bat` |
| DA‑S5‑6 | Vuelta atrás = restaurar el respaldo; `downgrade()` existe y se prueba en la CI, pero no se ofrece al usuario | bajar de revisión desde la interfaz | restaurar es exacto; un `downgrade` puede perder datos de columnas nuevas |
| DA‑S5‑7 | **Dos destinos de migración** (instalación y caso), cada uno con su entorno, su `alembic_version` y su lista `METADATAS`; un solo juego de respaldo para los dos (RV‑4) | un solo entorno con todas las `MetaData` | las cuentas y claves no pueden terminar en la base de un caso; un caso se copia o se envía sin arrastrar la seguridad de la instalación |
| DA‑S5‑8 | Red local en la **IP explícita** de la interfaz elegida al activar (RV‑15) | `0.0.0.0` | no escucha en VPN ni en adaptadores públicos y evita que Streamlit consulte su IP pública |

---

## 6. Migraciones con Alembic (RF‑96, RNF‑20)

### 6.1 Punto de partida

**Caso.** La revisión `caso_0001_base_0_5_0` contiene el esquema **de la 0.5.0** (las 25 tablas de `core/models` y
las `esp_*`), generado una vez con la autogeneración de Alembic contra una base vacía creada con el código de
`v0.5.0`, **revisado a mano y congelado**: no se deriva de los modelos en cada corrida. Se escribe idempotente con
`migraciones/comun.py:crear_o_verificar`: para cada tabla, si no existe la crea; si existe, compara columnas (nombre,
tipo, nulabilidad) e índices con su definición y, ante una diferencia, lanza `BaseNoAdoptable` con la lista. Desde
ahí **cada S agrega su revisión** (`caso_0002_…` de S1 en la 0.6.0, etc.); las que solo crean tablas usan el mismo
ayudante, lo que cubre las bases de desarrollo creadas con `create_all`. Las que alteran columnas usan
`batch_alter_table`.

**Instalación.** El entorno `migraciones/instalacion/` nace en S5‑1 con `METADATAS_INSTALACION = []` y sin
revisiones; S3‑1 escribe su primera revisión (`ins_0001_seguridad`) con las tablas de `seguridad/modelo.py`.

**Ambos.** `render_as_batch=True` en cada `env.py` (SQLite casi no tiene `ALTER`; Alembic usa «mover y copiar» y
solo en SQLite). `target_metadata` = la lista de su destino (Alembic admite una lista de `MetaData`). Cada base
tiene su propia tabla `alembic_version`. Versión de Alembic: la vigente al construir (la documentación consultada hoy
es la 1.20.0), fijada en `uv.lock` por el PR «dependencias Sílice».

### 6.2 Convivencia con `crear_esquema`

- **Producto:** el lanzador ejecuta `preparar_base` **antes** de arrancar la interfaz y la API, y la interfaz lo
  vuelve a ejecutar al abrir **cualquier** caso. Cuando las páginas llaman a `crear_esquema`, la base ya está en
  `head` y `create_all` no hace nada. `estado_caso` deja de llamarlo (solo lee).
- **Desarrollo y pruebas:** `crear_esquema` sigue igual (bases en memoria). `scripts/seed*.py` llaman a
  `preparar_base` cuando la URL es un archivo.
- **Red de seguridad:** si alguien agrega una tabla al modelo sin revisión, `create_all` la crearía «por el costado»
  en las bases existentes. Lo atrapan dos pruebas de RNF‑20 en cada destino: la autogeneración contra una base en
  `head` debe venir vacía, y `crear_esquema` + `crear_esquema_espacio` (y los equivalentes de `seguridad`, `paquete`
  y `asistente`) sobre una base en `head` no deben cambiar nada (instantánea del esquema igual antes y después).

### 6.3 Respaldo automático: un juego, una ficha

Antes de aplicar **cualquier** revisión pendiente (también la base, en una adopción):

1. copia con la API de respaldo de `sqlite3` (`Connection.backup`, segura con la base abierta) de `instalacion.db`
   (si existe) y de cada caso que se va a migrar a `respaldos\<AAAAMMDD-HHMMSS>_<motivo>\` (`instalacion.db`,
   `casos\<nombre>.db`); `instalacion.db` va siempre en el juego, aunque no se migre, para que la pareja restaurada
   sea coherente;
2. `PRAGMA integrity_check` sobre cada copia, que debe dar `ok`;
3. `ficha.json` con versión de Sílice, motivo y, **por base**: revisión de origen y de destino, filas por tabla y
   SHA‑256 de la copia; además el último `evento_acceso` de la instalación (id y fecha) para calcular lo perdido al
   restaurar (§6.5).

Sin juego verificado no se migra. Se conservan los juegos de las **cinco** últimas migraciones y todos los
manuales; nunca se borra el más reciente. Los respaldos contienen todo (huellas de contraseñas, la clave privada de
firma cifrada con Argon2id y AES‑GCM según RV‑13, huellas de las claves de API): viven en la carpeta protegida del
usuario y el manual advierte al copiarlos. La clave de IA que guarda `keyring` no está en ellos (§5.3).

### 6.4 Adopción de bases anteriores y casos límite

| Base encontrada | Qué hace `preparar_base` |
|---|---|
| no existe o está vacía | `upgrade head` (la base se crea por las revisiones) |
| sin `alembic_version`, con el esquema de la 0.5.0 (bases de la 0.5.0 y de desarrollo creadas con `create_all`) | respaldo del juego → `upgrade head`: la base idempotente crea las tablas que falten y verifica el resto → revisiones siguientes (idempotentes si solo crean tablas) |
| sin `alembic_version`, con columnas que no cuadran (p. ej. sin `modalidad`, anterior a P2) | `BaseNoAdoptable`: se restaura el juego (huella igual) y el mensaje lista las diferencias y remite al manual (volver a sembrar o pedir ayuda) |
| con revisión anterior a `head` (bases de 0.6.0 a 0.9.0 y posteriores) | respaldo del juego → `upgrade head` |
| con revisión desconocida (de un Sílice más nuevo) | no se toca; «Esta base es de una versión más nueva de Sílice. Instale esa versión o restaure el respaldo previo» (3d) |
| migración que falla a medias | se restaura el juego; `registros\silice.log` guarda el error; el arranque se detiene (7a) |
| caso abierto desde Inicio que no está en `head` | se migra con respaldo previo del juego; si no es adoptable o es de una versión más nueva, se rechaza con mensaje y se queda en el caso anterior |

### 6.5 Restauración y CLI

`python -m operacion respaldar | restaurar <juego> [--solo-caso <nombre>] | migrar | revision | casos`. Restaurar
exige Sílice detenido, guarda antes las bases actuales como juego `antes_de_restaurar_<fecha>`, rechaza un respaldo de
revisión desconocida y, si es de una revisión anterior, la migración ocurre en el siguiente arranque (con su propio
juego). `--solo-caso` restaura un caso sin tocar la instalación.

**Restaurar la instalación deshace la seguridad en silencio si nadie mira** (SEG‑12): revive claves de firma o de
API revocadas, cuentas desactivadas, roles retirados y revocaciones ajenas registradas. Por eso, cuando el juego trae
`instalacion.db`:

1. antes de restaurar, `operacion` compara la instalación actual con la del juego y escribe
   `datos\eventos_perdidos_<fecha>.json` (fuera de la base): los `evento_acceso` posteriores al último de la ficha y
   las diferencias de cuentas (desactivadas, roles), claves de firma y de API (revocadas, retiradas) y revocaciones
   ajenas registradas;
2. la consola y la pantalla de acceso del administrador muestran la lista; mientras el administrador no la marque
   como revisada (aplicando de nuevo lo que corresponda: revocar, desactivar), quedan bloqueadas las operaciones
   sensibles de §8.2 y la pestaña Instalación lo indica.

### 6.6 Abrir un caso (RV‑5)

- Un caso se abre **solo** con `operacion.base_datos.preparar_base` (la guardia lo permite en `ui` y `api`).
- Los casos se eligen de una **lista** de `datos\casos\` (`listar_casos`) o se **suben** (archivo `.db` que se copia
  a `casos\` con un nombre saneado y pasa por `preparar_base`). El `st.text_input` libre de Inicio desaparece.
- Toda ruta pasa por `Path.resolve()` + `is_relative_to(datos\casos)`; se rechazan las rutas UNC, las absolutas y las
  que contienen `..`, antes de tocar el disco.
- `estado_caso` no emite DDL. Una base que no está en `head` se rechaza con mensaje o se migra con respaldo previo
  (§6.4).
- «Cambiar de caso»: solo *arma* y administrador (S3 §5.1). Cambiar la carpeta de datos: solo administrador y desde el
  propio equipo (§8.2).
- Esto entra con S5‑1 en la 0.6.0.

---

## 7. Instalador para Windows (RF‑97, RNF‑19)

### 7.1 Construcción (`instalador/construir.py`, en Windows)

1. `uv python install <3.13.x fijada> --install-dir build\py` (distribución de python-build-standalone que usa `uv`)
   y copia a `build\app\python`. La distribución viene marcada `EXTERNALLY-MANAGED` por `uv` (verificado), así que
   la instalación de paquetes usa `--break-system-packages` **solo al construir**; la marca se conserva para que nadie
   use `pip` sobre ella después.
2. `uv export --frozen --no-dev --no-emit-project --no-hashes` con los extras de cada capa (§7.2) y
   `uv pip install --python build\app\python\python.exe --break-system-packages --compile-bytecode -r <capa>`; la capa
   de similitud se instala con `--target build\app\modulos\similitud\paquetes` y **solo** los paquetes que la básica no
   trae (diferencia de conjuntos, como en §1.3), más `silice_similitud.pth` (va en el componente).
3. Copia el código según `instalador/manifiesto.toml` (lista blanca): los paquetes del producto; de `scripts/` y
   `tests/fixtures/`, **solo el cierre de importaciones** de `scripts.seed*` y `scripts.simular_lista`, calculado al
   construir y comprobado por `test_manifiesto`; **nunca** todo `tests/fixtures/` (ni los `.xls` del BCV, ni las
   grabaciones de S4, ni las bases de prueba, ni el catálogo de planos); de `data/`, solo lo que el producto lee (los
   PDF de `data/precios` no viajan mientras su redistribución no esté aclarada); `pyproject.toml`; y
   `instalador/streamlit_config.toml` como `codigo\.streamlit\config.toml`, el único `config.toml` permitido. Nunca
   `.venv`, `*.db` ni `docs/` salvo los manuales. Luego `python -m compileall` y `manifiesto.json` (ruta, tamaño,
   SHA‑256 de cada archivo). Mover los datos de demostración a un paquete `demo/` queda como mejora posterior (RV‑25).
4. Para el completo: modelo descargado una vez al construir en `modulos\similitud\hf` (`HF_HOME`); en tiempo de
   ejecución, `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1` (que cargue sin red se confirma en la prueba de humo del
   completo).
5. `LICENCIAS\`: la de Python (PSF) y la de cada paquete incluido, generadas desde los metadatos instalados.
6. `ISCC.exe /DVersion=<pyproject> /DPerfil=basico|completo instalador\silice.iss`.
7. `SHA256SUMS` de los artefactos y de `manifiesto.json` (§10.4).

### 7.2 Componentes y tamaños

| Componente | Contenido | Artefacto | Tamaño (estimado §1.3) |
|---|---|---|---|
| Programa (fijo) | Python, básica (base, `ui`, `api`, `planos`, `informes`, `bcv`), `civil` (con `ifctester`), `anomalias`, extra `ia` de S4, dependencias de S3, código | ambos | ≈ 126 MB + S1/S3/S4 (a medir en S5‑0.3) |
| Caso de demostración (casilla, marcada) | ofrecer «abrir el caso de demostración» en Inicio | ambos | despreciable |
| Similitud de partidas (casilla) | paquetes de similitud y el modelo | solo el completo | ≈ 496 MB |

`xgboost` no se incluye (ningún código del producto lo importa). `bcv` (`xlrd`, < 1 MB) va en el básico porque sin
él UC‑17 falla en el producto (ARQ‑H14). Si el básico pasa de 150 MB, el orden para recortar es: `civil` (con
`ifctester`) a componente opcional (16 MB), luego `anomalias` (26 MB); la decisión se registra como ruling. El límite
de 4 200 000 000 bytes a partir del cual Inno exige `DiskSpanning` queda lejos.

### 7.3 Directivas principales de `silice.iss`

`AppId` fijo para siempre (lo usa la actualización); `AppVersion={#Version}`; `PrivilegesRequired=lowest`;
`DefaultDirName={autopf}\Silice`; `Compression=lzma2/ultra64` y `SolidCompression=yes`; idiomas: español (traducción
oficial incluida); `[Types]`/`[Components]` de §7.2; `[InstallDelete]` de §5.4; `[Icons]` en `{autoprograms}` y,
opcional, el escritorio: «Sílice» (`{app}\python\python.exe`, `Parameters: -E -s -B -m operacion arrancar`,
`WorkingDir: {app}\codigo`, `Flags: runminimized`), «Detener Sílice» y «Sílice: red local (administrador)»;
`[Run]` post‑instalación `operacion migrar` y, opcional, «Abrir Sílice ahora»; `[Code]`: detener en
`PrepareToInstall` y avisar si se instala una versión **menor** que la instalada. Sin `[UninstallDelete]` sobre la
carpeta de datos. Ningún paso descarga nada.

### 7.4 Desinstalación y actualización

Desinstalar quita `{app}` y los accesos; la página final dice «Sus datos quedan en %LOCALAPPDATA%\Silice. Bórrela a
mano si ya no los necesita». Actualizar = ejecutar el instalador nuevo sobre el anterior (mismo `AppId`): §5.4 y §6.
Pasar del básico al completo = ejecutar el completo. El manual pide comprobar la huella y la firma antes de ejecutar
cualquier instalador recibido por correo, WhatsApp o USB (§10.4).

---

## 8. Operación (RF‑98)

### 8.1 Configuración y primer arranque

`config\silice.toml` (valores por defecto):

```toml
[servidor]
puerto = 8501
red_local = false        # true: escucha en la IP de la interfaz elegida (§8.2)
direccion = ""           # IP de esa interfaz, la fija «red-local activar»; nunca 0.0.0.0
[api]
activa = false
puerto = 8000
[interfaz]
mostrar_investigacion = false   # false = modo entrega (ARENIA_MODO_ENTREGA=1), RS5-9
[registro]
nivel = "INFO"
```

Las claves de la API viven en `instalacion.db` (S3: SHA‑256, se muestran una vez), no en este archivo. El código de
instalación de S3 se escribe en `datos\codigo_instalacion.txt` y en la consola del servidor; como la red local está
apagada en el primer arranque, solo alguien sentado al equipo puede crear el primer administrador. Un
`silice.toml` dañado da un mensaje y los valores por defecto: nunca la red encendida.

### 8.2 Red local

- **Apagada:** Streamlit con `server.address=127.0.0.1` y `browser.serverAddress=127.0.0.1`; la API, si está activa,
  también en `127.0.0.1`.
- **Activar** solo desde el equipo servidor, con el acceso «Sílice: red local (administrador)» o
  `python -m operacion red-local activar`, que pide elevación (UAC), lista las interfaces IPv4 con dirección privada
  y pide **elegir una**; guarda su IP en `direccion` y crea reglas de entrada para el `python.exe` de `{app}` y los
  puertos configurados con `netsh advfirewall firewall add rule … dir=in action=allow protocol=TCP
  localip=<direccion> remoteip=localsubnet profile=private`; pone `red_local = true` y avisa: «Sílice quedará
  visible para los equipos de esta red. Las contraseñas viajan sin cifrar (sin TLS): úselo solo en una red de
  confianza». Al reiniciar, Streamlit y Uvicorn escuchan en **esa IP** (nunca `0.0.0.0`), con
  `browser.serverAddress` fijado a ella, y la consola y la pestaña Instalación muestran `http://<direccion>:<puerto>`.
  Sin elevación (6a) no cambia nada.
- **Red de confianza** (definición que usan el aviso y el manual): la red propia de la oficina, con WPA2 o WPA3 (o
  cableada) y equipos conocidos; **no** la Wi‑Fi de la obra, una red pública ni un punto de acceso compartido desde
  un teléfono.
- **Desactivar** borra las reglas y vuelve a `127.0.0.1`. La pestaña Instalación muestra el estado, no lo cambia
  (cambiarlo desde un navegador remoto pediría elevación en el servidor).
- **Solo desde el propio equipo** (RV‑15): firmar, generar o exportar la clave de firma de la empresa, registrar la
  clave de IA de la empresa, crear claves de API y cambiar la carpeta de datos se permiten solo si
  `operacion.red.es_cliente_local(ip)` es verdadero: IP de bucle local o la IP de la interfaz elegida (que solo
  tiene el servidor). La IP del cliente sale de `st.context.ip_address` (API de Streamlit **a confirmar** en S5‑2);
  si no se puede leer, la operación se trata como remota.
- **Aviso «sin cifrar» en la pantalla de acceso** (S3, `ui/acceso`) cuando el cliente es remoto: «Esta conexión no
  está cifrada. Use Sílice solo en una red de confianza». S5 da la función y el texto; S3 los muestra.
- **El filtro de IP no es un control.** Un túnel o proxy local (`cloudflared`, `ngrok`, un proxy inverso) hace que todo
  llegue como `127.0.0.1` y anula tanto el filtro de redes privadas de la API como la regla de «solo desde este
  equipo». El control es la contraseña de la cuenta y la clave de la API; el arranque avisa si ve un túnel conocido
  (3f) y el manual lo prohíbe.
- Solo IPv4 en la 1.0.0. Que Streamlit, con la dirección fijada, no consulte su IP pública (la «External URL» de
  §1.2) se confirma con la prueba de humo (§11.2).

### 8.3 API

Apagada por defecto. Al activarla (pestaña Instalación, rol administrador, efecto al reiniciar) escucha en la misma
dirección que Streamlit (§8.2). Todas las rutas exigen la cabecera de clave de S3 (S5 la **extiende a las rutas
antiguas**: sin clave, `401` con `{"detalle": ...}`), salvo `GET /salud` (`{"estado": "ok"}`, sin versión);
`TrustedHostMiddleware` admite solo `127.0.0.1`, `localhost` y la IP elegida (contra DNS rebinding; un `Host` ajeno da
`400`); un middleware responde `403` a clientes que no son de bucle local ni de redes privadas (`ipaddress`:
`is_loopback` o `is_private`), defensa adicional al cortafuegos y **no** control (§8.2); `docs_url` y `openapi_url`
apagados en el producto (el esquema sigue exportado en `docs/api.json`); registro de accesos de Uvicorn apagado.
Crear claves de API: solo desde el propio equipo.

### 8.4 Registro de errores sin datos sensibles

`registros\silice.log`, rotativo (1 MB × 5), formato `fecha nivel módulo mensaje`. El lanzador recoge la salida de
error de Streamlit y de Uvicorn y la pasa por el mismo filtro. **Nunca** se registran: contraseñas, códigos de
instalación, claves de API o de IA (patrones `sk-ant-`, la cabecera de clave, `Bearer`), bloques PEM, cuerpos de
petición ni cadenas de consulta; la carpeta del usuario se reescribe como `%USERPROFILE%`. Las trazas guardan tipo,
mensaje y líneas de código, no valores de variables. En el navegador, `client.showErrorDetails="none"`.

---

## 9. Versionado, `CHANGELOG.md` y etiquetas (RF‑99)

### 9.1 Versionado semántico del producto

La «API pública» de Sílice, para decidir el número, es: el formato del paquete auditado (S3), las rutas de la API, la
CLI `operacion` y la capacidad de migrar la base sola. **Mayor:** un paquete o una ruta deja de ser compatible, o una
base no se migra sola. **Menor:** funciones nuevas; puede traer revisiones de Alembic. **Parche:** correcciones sin
revisión de esquema ni cambio de formato. Candidatas: `1.0.0-rc.N`.

### 9.2 Una sola fuente

`pyproject.toml` (`version`, PEP 440: `1.0.0rc1`); `operacion.version` la lee con `tomllib` del `pyproject.toml`
instalado; la usan `api/main.py` (hoy `version="0.1.0"` fijo en la línea 18), «Acerca de» y `construir.py`
(`/DVersion`). La etiqueta es SemVer con `v` (`v1.0.0-rc.1`); la CI compara ambas normalizadas con
`packaging.version` (que `1.0.0-rc.1` normalice a `1.0.0rc1` se confirma en S5‑0).

### 9.3 Etiquetas y relación con `v1.0-tesis`

- `v0.5.0` existe. `v0.6.0` … `v0.9.0`: anotadas, sobre el commit de fusión en `main` tras la compuerta de cada
  versión, puestas por el controlador en orden numérico (RV‑1). `v1.0.0-rc.N`: el instalador que se lleva a Med.
  `v1.0.0`: la rc medida, sin cambios de código (solo documentos de resultados); si hay cambios de código después de
  medir, se declaran y se decide en la bitácora si se vuelve a medir.
- **`v1.0-tesis`** (F3 de PLAN_CIERRE) es un alias anotado que apunta **al mismo commit que `v1.0.0`** o, si la
  tesis necesita correcciones, al de un `v1.0.x`; nunca a un commit sin etiqueta SemVer. La tesis cita la versión
  SemVer («Sílice 1.0.0»), la huella del instalador y la huella de la clave pública del proyecto (§10.4).

### 9.4 `CHANGELOG.md`

Formato de *Keep a Changelog* con secciones en español (Agregado, Cambiado, Obsoleto, Eliminado, Corregido,
Seguridad) y una sección `## [x.y.z] - AAAA-MM-DD` por versión, más `## [Sin publicar]`, donde cada PR agrega **una
línea** (RV‑2); al etiquetar, el controlador mueve esas líneas a la sección de la versión. Entrada retroactiva para
0.5.0 (desde el mensaje de la etiqueta y la bitácora del SF) y una línea de historia para lo anterior que enlaza
`docs/bitacora/`. Cada entrada nombra sus RF y, si las hay, sus revisiones de Alembic. El `CHANGELOG.md` nace con
S5‑1 en la 0.6.0.

---

## 10. Endurecimiento, amenazas y manuales

### 10.1 Opciones fijas del servidor

El lanzador pasa a Streamlit por línea de órdenes (que tengan precedencia sobre un `config.toml` global del usuario
se confirma con una prueba en S5‑2): `server.headless=true`, `server.address` y `browser.serverAddress` según §8.2
(nunca `0.0.0.0`), `server.port` y `browser.serverPort`, `browser.gatherUsageStats=false`,
`server.fileWatcherType=none`, `server.runOnSave=false`, `client.showErrorDetails=none`,
`client.toolbarMode=minimal`, `server.maxUploadSize=20` (MB, coherente con el límite de planos de RNF‑12),
`global.developmentMode=false`, y **explícitos** `server.enableCORS=true` y `server.enableXsrfProtection=true`.

Segunda capa: `{app}\codigo\.streamlit\config.toml` con los mismos valores fijos (sale de
`instalador/streamlit_config.toml`, que parte del `.streamlit/config.toml` de desarrollo de §1.2 si ya está en
`main`). Es el **único** `config.toml` dentro de `{app}\codigo`: `test_manifiesto` falla si aparece otro.

### 10.2 Otras medidas

three.js empaquetado (licencia MIT) y servido localmente: se retira la excepción de RNF‑08 por la CDN; similitud
sin descargas (`HF_HUB_OFFLINE`); la base nunca en una carpeta de red (SQLite sobre SMB no es fiable): el arranque
avisa si la carpeta de datos es una ruta UNC y los casos rechazan rutas UNC (§6.6); **`pip-audit` esencial** (SEG‑14)
sobre las dependencias exportadas de cada capa en el flujo del instalador, con su resultado (`pip-audit.json`)
adjunto a cada versión: una vulnerabilidad conocida sin ruling que la acepte hace fallar el flujo (que lea el formato
de `uv export` se confirma en S5‑4); el instalador **sin firma de código** en la 1.0.0 (RS5‑10): SmartScreen avisará
«Windows protegió su PC» y el manual lo explica junto con la comprobación de §10.4.

### 10.3 Redacción consolidada de RNF‑08 (S5‑0, RV‑23)

S3‑0 enmienda RNF‑08 una vez (credenciales locales sin servicios externos) y S4 agrega el asistente en modo nube.
S5‑0 escribe la redacción **final** de la ERS, con la numeración de excepciones cerrada:

> RNF‑08 ejecución local: el sistema funciona sin conexión a internet; sus únicas credenciales son las cuentas
> locales de la instalación (S3), que no dependen de ningún servicio externo; los datos residen en archivos SQLite
> del equipo servidor (la base de la instalación y las de los casos). Medición: credenciales versionadas, 0;
> conexiones fuera del equipo durante la operación, 0, con **dos excepciones declaradas**: (1) en el camino de
> desarrollo, la descarga inicial del modelo de `sentence-transformers` (I2), que se cachea localmente (el
> instalador completo lo trae incluido y corre con `HF_HUB_OFFLINE=1`); (2) el asistente de IA en **modo nube**,
> apagado por defecto, que solo activa el administrador de la instalación al registrar la clave de IA de la empresa
> y que envía al proveedor solo lo de la lista blanca de S4. La excepción de three.js se retira: se sirve desde el
> propio sistema.

### 10.4 Modelo de amenazas de la operación (RV‑16)

Tabla propia de S5 (la del paquete auditado es la de S3). «Residual» es lo que se acepta y se declara.

| Amenaza (actor) | Escenario | Control | Residual |
|---|---|---|---|
| Instalador cambiado (tercero en el canal de descarga) | un `.exe` alterado ejecuta código en el equipo de la empresa | `SHA256SUMS` de los artefactos y de `manifiesto.json`, **firmado con la clave Ed25519 del proyecto** (`SHA256SUMS.ed25519`; separación de dominio `b"silice-sumas-v1\0"`, como RV‑16); la huella de la clave pública se publica en el manual de instalación y en la tesis; el manual explica cómo comprobar huella y firma antes de instalar | quien no comprueba; sin firma de código, SmartScreen avisa igual (RS5‑10) |
| Actualización por WhatsApp o USB (colega, intermediario) | un instalador «nuevo» llega por un canal informal | `python -m operacion verificar-instalador <exe> <SHA256SUMS> <firma>` desde el Sílice ya instalado, con la clave pública del proyecto incluida en el programa; el manual: nunca ejecutar uno que no pase | quien lo ejecuta sin verificar |
| Restaurar un respaldo viejo (administrador apurado o empleado deshonesto) | revive claves revocadas, cuentas desactivadas, roles retirados y revocaciones ajenas | lista de eventos de seguridad perdidos y revisión obligatoria del administrador antes de las operaciones sensibles (§6.5, SEG‑12) | el administrador que marca «revisado» sin leer |
| Atacante en la red local | escucha (sin TLS), DNS rebinding, websockets entre sitios, prueba masiva de contraseñas | red apagada por defecto; IP explícita y regla limitada a la subred y al perfil Privado; «red de confianza» (§8.2); `TrustedHostMiddleware`; CORS y XSRF explícitos; freno de intentos de S3; operaciones sensibles solo desde el propio equipo; aviso «sin cifrar» en la pantalla de acceso | contraseñas y datos viajan en claro en la red de la oficina (RS5‑8) |
| Túnel o proxy local (`cloudflared`, `ngrok`, un servicio olvidado) | todo llega como `127.0.0.1`: se anulan el filtro de IP y la regla «solo desde este equipo»; Sílice queda publicado en internet | el control es la clave y la contraseña, no la IP; aviso al arrancar si hay un túnel conocido (3f); el manual lo prohíbe; `COMPARTIR_ONLINE.bat` no se incorpora (RS5‑12) | un túnel desconocido o configurado por el usuario |
| Proceso malicioso del usuario | cambia el código o el `python.exe` de `{app}` (escribible sin elevación) y aprovecha la regla del cortafuegos | instalación por usuario declarada (§5.3); `manifiesto.json` firmado vía `SHA256SUMS` permite comprobar `{app}` (`operacion verificar-programa`, D) | un programa con los permisos del usuario ya controla su cuenta: fuera del modelo |
| Ruta de caso arbitraria (usuario con sesión) | crear o abrir un SQLite en cualquier ruta; ruta UNC que entrega el hash NTLM | lista de `datos\casos\`, rechazo de UNC, absolutas y `..` (§6.6) | ninguno conocido |
| Respaldo copiado fuera del equipo | trae huellas de contraseñas, la clave de firma cifrada y huellas de claves de API | Argon2id + AES‑GCM de la clave (RV‑13); el manual advierte; `keyring` no viaja | ataque sin conexión a contraseñas débiles (lista de comunes rechazadas, S3) |
| Fuga por registros | secretos en `silice.log` o en la salida de los hijos | filtro de §8.4 con prueba de secretos sembrados | un patrón nuevo no previsto |
| Dependencia vulnerable | una biblioteca del instalador con vulnerabilidad conocida | `pip-audit` esencial con resultado adjunto a cada versión (§10.2) | vulnerabilidades no publicadas |
| Conexiones salientes no declaradas | telemetría de Streamlit, CDN, descarga de modelos | `gatherUsageStats=false`, `browser.serverAddress` fijo, three.js local, `HF_HUB_OFFLINE`; prueba de humo con cortafuegos de salida y navegador sin interfaz (§11.2) | el asistente en modo nube, declarado (§10.3) |

**Clave del proyecto.** Par Ed25519 generado por el controlador con la maquinaria de `seguridad` de S3; la privada
vive cifrada (RV‑13) fuera del repositorio y de la CI. La CI publica `SHA256SUMS` sin firmar; el controlador lo
firma en su equipo (`python -m operacion firmar-sumas`) y publica la firma junto al *release* (pregunta 6). Si la
privada se pierde o se expone, se genera otra, se publica la huella nueva en el manual y la tesis lo declara.

### 10.5 Manuales

| Documento | Cambio |
|---|---|
| `docs/manual_instalacion.md` (**nuevo**) | requisitos; comprobar huella y firma (y la huella de la clave del proyecto); instalar (básico y completo); primer arranque y primer administrador; casos (lista, subir, demostración); red local, «red de confianza», túneles prohibidos; API y claves; actualizar; respaldos, restaurar y la revisión de eventos perdidos; `keyring` no viaja en los respaldos; desinstalar; SmartScreen; problemas frecuentes (puerto ocupado, base no adoptable, versión más nueva, IP de la red local cambiada) |
| `docs/manual_usuario.md` | §1–§2: el camino del instalador primero; el de desarrollo pasa al manual técnico |
| `docs/manual_tecnico.md` | §6 y §10.5 se reescriben en la 0.6.0 (hay migraciones: los dos destinos, cómo crear una revisión, la prueba de deriva, la base de prueba y su ficha en cada compuerta); en la 1.0.0, secciones nuevas: construir el instalador, la CLI `operacion`, cómo publicar una versión (CHANGELOG, `pyproject`, etiqueta, firma de `SHA256SUMS`) |
| `README.md` | «Arranque rápido» con dos caminos: instalador (usuario) y `uv sync` (desarrollo); el comando de Streamlit lleva `--server.address 127.0.0.1` |
| `docs/calidad_iso25010.md`, ERS | RNF‑19, RNF‑20; RNF‑07 se aclara (sigue el camino `uv sync`, ahora junto al instalador); RNF‑08 con la redacción final de §10.3 |

---

## 11. Integración continua

### 11.1 En `ci.yml` (cada PR, Linux y Windows)

Desde la 0.6.0, las pruebas de `operacion` y `migraciones` corren dentro de la suite existente (§12). `calidad` suma
`scripts/meta_silice.py --version <versión en curso>` (RV‑17), que reúne las comprobaciones comunes y las de S5 (§13).
La suite corre bajo la guardia de red única de `tests/conftest.py` (solo `127.0.0.1` y `::1`) con
`HF_HUB_OFFLINE=1`; el modelo de similitud se descarga en un paso anterior, con caché.

### 11.2 Flujo nuevo `.github/workflows/instalador.yml` (Windows)

- **Cuándo:** etiquetas `v*`, `workflow_dispatch` y PR que tocan `instalador/`, `operacion/`, `migraciones/`,
  `pyproject.toml` o `uv.lock`. El completo, solo con etiqueta o a mano (≈ 600 MB de artefacto; minutos de Windows de
  un repositorio privado).
- **construir:** `runs-on: windows-2025` (fija, no `latest`); `setup-uv` con la versión exacta de `ci.yml`; Inno Setup
  6.7.x del runner (si falta, `choco install innosetup --version <fija>`; la ruta de `ISCC.exe` se confirma en la
  primera corrida); `construir.py`; tamaño del artefacto contra RNF‑19 (falla si se pasa); `pip-audit` de cada capa
  (falla ante una vulnerabilidad sin ruling); publica instalador, `manifiesto.json`, `SHA256SUMS` y `pip-audit.json`.
- **humo** (`instalador/humo.ps1`), en el mismo runner (que es administrador), **con el asistente de IA apagado**:
  1. **cortafuegos de salida:** regla que **bloquea** las conexiones salientes del `python.exe` de `{app}` y registro
     de paquetes descartados activado (`Set-NetFirewallProfile -LogBlocked True`); el tráfico de bucle local no se
     filtra. Además arranca un **proxy testigo** local que anota toda petición y fija `HTTP_PROXY`/`HTTPS_PROXY`
     hacia él, con `NO_PROXY=127.0.0.1,localhost` (ve lo que respeta proxies; el cortafuegos ve el resto);
  2. instala con `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /DIR="C:\Prueba Sílice\Programa ñ" /LOG=…`
     y `SILICE_DATOS` en otra ruta con espacios;
  3. inventario de archivos de `{app}`; comprueba que `{app}\codigo` coincide con el manifiesto y que no hay otro
     `.streamlit\config.toml`;
  4. `operacion arrancar --sin-navegador` en segundo plano; espera `GET /_stcore/health` = `200` (≤ 60 s);
     comprueba con `Get-NetTCPConnection -State Listen` que el puerto escucha **solo** en `127.0.0.1`, que **nada**
     de los procesos de Sílice escucha en `0.0.0.0` ni en `::` y que el 8000 no escucha;
  5. abre la página principal (HTTP 200) y, con un **navegador sin interfaz** (Playwright con Edge, solo en la CI,
     `instalador/navegador.py`), carga Inicio y el visor y anota toda petición: la lista de anfitriones fuera de
     `127.0.0.1` debe quedar vacía (telemetría y three.js son del navegador y el proxy no los ve; ARQ‑H19). Si el
     navegador sin interfaz no se puede usar, se escanean el HTML y el JS servidos buscando direcciones externas;
  6. durante toda la corrida, muestreo cada segundo de `Get-NetTCPConnection -OwningProcess <pids de Sílice>`:
     ninguna dirección remota fuera de `127.0.0.1`/`::1`;
  7. crea casos con la base de prueba de la 0.5.0 (adopción) y con la de la 0.9.0, cada una con su ficha;
  8. `operacion parar`; el puerto queda libre; el inventario de `{app}` no cambió; el proxy anotó **0** peticiones; el
     registro de descartes del cortafuegos no tiene líneas con destino fuera del bucle local;
  9. **actualización:** instala el mismo build con versión de parche +1 (`/DVersion`): existe un juego de respaldo
     con su ficha, las dos bases tienen `alembic_version` = `head` y los presupuestos recargan con el total literal,
     la huella del informe y las filas por tabla de su ficha;
  10. **red local:** activa la red local con la IP de la interfaz del runner: escucha solo en esa IP (nunca en
      `0.0.0.0`), la salud responde por ella y desactivar borra las reglas;
  11. desinstala con `unins000.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`: `{app}` ya no existe; la carpeta de
      datos y sus respaldos siguen ahí;
  12. sube los registros como artefacto aunque falle.
- **Completo:** además, la página de similares carga el modelo sin red (salud de la función, proxy en 0 y
  cortafuegos sin descartes).
- Permisos `contents: read`; la publicación del *release* y la firma de `SHA256SUMS` las hace el controlador a mano
  (pregunta 6; §10.4).

---

## 12. Pruebas (IEEE 829)

Pruebas antes que implementación: un commit con la prueba en rojo observada y otro con la implementación por pieza
(rol de líder de fase; la meta comprueba que el commit de la prueba es anterior). Cero omitidas; ninguna toca
`data/apu.db` real (siempre `tmp_path` o `SILICE_DATOS`); todas bajo la guardia de red de `tests/conftest.py`.

| RF / RNF | Prueba |
|---|---|
| RF‑96 | `tests/integration/test_migraciones.py`: base vacía a `head` en los dos destinos; la base de prueba de la 0.5.0 (sin `alembic_version`, adopción) y la de cada versión 0.6.0…0.9.0 a `head`, **cada una generada en la compuerta de su versión con el código de su etiqueta** y versionada en `tests/fixtures/bases/` con su `ficha.json` (total literal, huella del informe, filas por tabla, escritos con ese código): la prueba compara contra la ficha, nunca contra un recálculo (PRU‑H15); `instalacion.db` desde la de la 0.8.0; juego de respaldo con `integrity_check` y huellas de cada base; fallo inyectado en una revisión de prueba → huellas iguales a las previas; base sin `modalidad` → `BaseNoAdoptable` sin tocarla; revisión desconocida → no arranca; restaurar crea `antes_de_restaurar_*`; retención de cinco juegos; restaurar un juego con `instalacion.db` → `eventos_perdidos_*.json` con el conjunto exacto de eventos sembrados (un evento posterior, una clave revocada, una cuenta desactivada) y operaciones sensibles bloqueadas hasta la revisión |
| RF‑96 (casos) | `tests/unit/test_casos.py`: lista de `casos\`; rechazo de `\\equipo\x\a.db`, `C:\x.db`, `../x.db` y `casos\..\x.db` sin crear archivo; subir un `.db` lo copia con nombre saneado; `estado_caso` sin DDL (instantánea del esquema y conteo de sentencias); caso fuera de `head` → migrado con juego previo o rechazado con mensaje; solo *arma* y administrador cambian de caso |
| RNF‑20 | en cada destino: `upgrade head` en vacío ≡ `create_all` de su `METADATAS` (tablas, columnas, tipos, nulabilidad, índices, únicas, foráneas, `CHECK`); autogeneración contra `head` sin cambios; `crear_esquema` (y los equivalentes de `espacio`, `seguridad`, `paquete`, `asistente`) sobre `head` sin DDL; toda `MetaData` con tablas está en la lista de su destino (se recorren los módulos de `core`, `adapters`, `seguridad`, `paquete`, `asistente` y `ui` buscando instancias); `downgrade`/`upgrade` de cada revisión. Activa desde la 0.6.0 |
| RF‑97 | prueba de humo de §11.2; `tests/unit/test_manifiesto.py`: importar `ui.app` y `api.main` en un subproceso cuyo `sys.path` es **solo** el árbol que arma el manifiesto (sin el repositorio); el cierre de importaciones de `scripts.seed*` y `simular_lista` está completo y no incluye nada más de `tests/fixtures/`; un único `.streamlit/config.toml`; prueba de arquitectura: ningún módulo de `ui/` importa `scripts.*` en el nivel superior |
| RF‑98 | `tests/unit/test_operacion_config.py` (valores por defecto: red y API apagadas; archivo dañado → mensaje y valores por defecto, nunca red encendida); `test_lanzador.py` (opciones de §10.1 en la orden, incluidas `browser.serverAddress`, `server.enableCORS=true` y `server.enableXsrfProtection=true`; para toda configuración, ni Streamlit ni Uvicorn reciben `0.0.0.0`; IP guardada que ya no existe → `127.0.0.1` y aviso; una sola instancia; puerto ocupado → mensaje); `test_red.py` (las órdenes `netsh` exactas con `localip`, sin ejecutarlas; `es_cliente_local` con bucle local, la IP elegida, otra IP privada e IP ilegible); `tests/integration/test_api_clave.py` (cada ruta de `app.routes` salvo `/salud` da `401` sin clave; `403` con un cliente `8.8.8.8` simulado; `400` con `Host: atacante.ejemplo`; crear una clave de API desde una IP remota se rechaza; `docs` apagado en modo producto); `test_registro.py` (secretos sembrados en mensajes, excepciones y salida de un hijo: ninguno en el archivo; rotación); `AppTest` de la pantalla de acceso con cliente remoto: muestra el aviso «sin cifrar» |
| RF‑99 | `scripts/meta_silice.py` (S5‑M5); `test_version.py`: API = `pyproject` |
| RNF‑19 | tamaño en la CI; arranque en el equipo de desarrollo (mediana de cinco) anotado en plan_pruebas §10, y la meta comprueba que la cifra está (S5‑M9); instalación a mano en una cuenta **estándar** y en un equipo sin internet (S5‑5, procedimiento en la bitácora) |
| Interfaz | `AppTest` de «Acerca de» (versión, las dos revisiones) y de la pestaña Instalación (estado de red y API, respaldos, revisión pendiente tras restaurar); RF‑43 (modo entrega) intacto |

**Regresión en cada compuerta (no se editan; RV‑17):** cinco APU a ± 0,01; 7 de 7; R4 de 3/4 pulg y
`test_r4_marca_3_4_pulg_y_no_marca_pvc`; TI‑001 total, PU y punto de equilibrio 28 586,76 USD en el Día 6; las dos
huellas de RNF‑04; cuatro hojas de `exportar_excel`. S5 no toca `core/` ni `exportar_excel`; la meta comprueba
`git diff v0.5.0..HEAD` vacío sobre los archivos de esas pruebas. Si un cambio de S5 moviera alguna, se registra un
ruling de reanclaje; nunca se edita la prueba.

---

## 13. Tareas y fases

Cada fase es una rama corta desde el `main` del momento con su PR contra `main`, que se fusiona al cruzar su compuerta
(RV‑2). S5‑1 abre la 0.6.0; S5‑2 es un carril sin núcleo que puede adelantarse; S5‑0 (documentos de la 1.0.0),
S5‑3, S5‑4 y S5‑5 son de la 1.0.0.

| Fase | Versión | Contenido | Criterio de cierre | Compuerta |
|---|---|---|---|---|
| **S5‑1** migraciones y casos | **0.6.0**, primera pieza | enmienda de la ERS para RF‑96 y RNF‑20; `alembic` en el PR «dependencias Sílice»; `migraciones/caso` con `caso_0001_base_0_5_0` y `migraciones/instalacion` vacío; `operacion.rutas`, `base_datos` (`preparar_base`, `listar_casos`, validación de rutas), `respaldo` (juego y ficha; restauración); `METADATA_ESPACIO`; lista de casos en Inicio, `estado_caso` sin DDL, `api/dependencias.py`; seeds con `preparar_base`; base de prueba de la 0.5.0 y su ficha, generadas desde `v0.5.0`; `.gitignore`; `CHANGELOG.md` con `[Sin publicar]`; manual técnico §6 y §10.5 | §12 RF‑96 (con lo que exista en la 0.6.0) y RNF‑20 en verde en Linux y Windows | GS5‑1 |
| Base de prueba de cada versión | 0.6.0 … 0.9.0 | en la compuerta de cierre de cada versión: su base de prueba en `tests/fixtures/bases/` y su ficha, escritas con el código de esa etiqueta; la revisión de Alembic de cada S | la prueba de RF‑96 la lleva a `head` y compara con la ficha | compuerta de cada versión |
| **S5‑2** operación | carril sin núcleo; lo que depende de S3 después de la 0.8.0 | sin S3: `operacion.config`, `lanzador` (IP explícita, opciones de §10.1), `registro`, `version`, «Acerca de», three.js local, extras `anomalias`/`similitud`, README con `--server.address`; con S3: `operacion.red` (`es_cliente_local`, interfaces, reglas), `api/seguridad.py`, pestaña Instalación, aviso de la pantalla de acceso, revisión de eventos perdidos al restaurar | §12 RF‑98 y RF‑99 en verde | GS5‑2 |
| **S5‑0** documentos de la 1.0.0 | 1.0.0 | 0.1 enmiendas a la ERS (UC‑24, RF‑97…99, RNF‑19, RNF‑07 y la redacción final de RNF‑08 de §10.3), arquitectura y plan de pruebas §8–§10; 0.2 entrada retroactiva del `CHANGELOG.md` y regla de versión; 0.3 **medir** el Python 3.13 autónomo y las dependencias de S1/S3/S4 (completa §1.3 y fija el recorte si el básico pasa de 150 MB); 0.4 comprobaciones de S5 en `scripts/meta_silice.py`; 0.5 confirmar ISO/IEC 25010:2023 y PEP 440 de §9.2; 0.6 clave del proyecto y su huella | documentos aprobados; comprobaciones de la meta escritas | GS5‑0 |
| **S5‑3** instalador | 1.0.0 | `instalador/` (§7), manifiesto con el cierre de importaciones, `config.toml` oficial; 3.4 **medir** los artefactos reales con ISCC y anotar en §1.3 y plan_pruebas §10 | se instala, arranca, actualiza y desinstala a mano en el equipo de desarrollo | GS5‑3 |
| **S5‑4** CI | 1.0.0 | `instalador.yml` con construir, `pip-audit` y humo (cortafuegos de salida, navegador sin interfaz, red local); tamaño y versión en la CI | flujo verde en un PR y en una etiqueta de prueba | GS5‑4 |
| **S5‑5** cierre | 1.0.0 | manuales (§10.5); prueba a mano en cuenta estándar y sin red; `SHA256SUMS` firmado; `v1.0.0-rc.1` para Med; revisión por encargo con seguridad y usabilidad | maestro §6: meta en OK (incluida S5‑M6, sin PENDIENTE), CI verde Linux y Windows, encargos aprobados | **GS5 = 1.0.0** |

**Meta** (`scripts/meta_silice.py --version <x> --hasta <fase>`, RV‑17). Comprobaciones comunes de la meta única:
presencia de los números de la ERS de esa versión (no conteos absolutos); cero omitidas; commit de la prueba anterior
al de la implementación; `git diff` vacío en `core/contracts/`; `git diff v0.5.0..HEAD` vacío sobre los archivos de
las pruebas de regresión; guardia de red activa; las pruebas de tiempo dejaron su cifra. Comprobaciones de S5:
**S5‑M1** RF‑96…99, RNF‑19/20 y UC‑24 presentes en la ERS (RF‑96 y RNF‑20 desde la 0.6.0); **S5‑M2** `core/` intacto
en el rango de cada rama de S5; **S5‑M3** pruebas de migraciones, casos y deriva en verde, y una base de prueba con
ficha por cada versión etiquetada; **S5‑M4** pruebas de operación en verde; **S5‑M5** versión única y sección del
CHANGELOG; **S5‑M6** último flujo del instalador verde (en la 1.0.0 debe estar en **OK**, sin excepción; antes de la
1.0.0 no aplica); **S5‑M7** tamaño del básico ≤ 150 MB y del completo ≤ 650 MB según el último artefacto; **S5‑M8**
regresión literal (bloque de §12); **S5‑M9** la medición de arranque de RNF‑19 dejó su cifra; **S5‑M10**
`pip-audit.json` adjunto a la última versión sin vulnerabilidades abiertas. Con `--version 0.6.0 --hasta S5‑1` solo
corren las comunes, S5‑M1 (su parte), S5‑M2, S5‑M3 y S5‑M8.

---

## 14. Rulings

| # | Ruling | Estado | Costo si es erróneo |
|---|---|---|---|
| RS5‑1 | Alembic entra con la **0.6.0** (S5‑1 primera pieza), revisión base del caso = esquema de la 0.5.0; cada S agrega su revisión; cada versión genera su base de prueba y ficha en su compuerta | **cerrado por RV‑3** | ninguno conocido; reemplaza la propuesta de esperar a la 0.9.0, que daba `BaseNoAdoptable` con las bases de 0.6.0 y 0.7.0 |
| RS5‑2 | S5 no toca `core/`; SL‑E11 solo con su disparador; SL‑E12 pasa a S3 | **cerrado por RV‑7** (SL‑E12) | si SL‑E11 se dispara, un expediente más y el aval del tutor |
| RS5‑3 | Instalación por usuario, sin administrador (DA‑S5‑3), con el límite de §5.3 declarado | a ratificar por Eugenio (maestro §10) | en un equipo con varias cuentas de Windows cada una tiene su copia y sus datos; instalar por equipo exige otra carpeta de datos (`{commonappdata}`) y permisos |
| RS5‑4 | Dependencias preinstaladas en capas al construir, sin entorno virtual (DA‑S5‑1, DA‑S5‑2) | a ratificar | si la capa `.pth` choca con la básica, el completo pasa a ser un Python con todo instalado (instalador más grande, una sola capa) |
| RS5‑5 | Límites: básico ≤ 150 MB y completo ≤ 650 MB (comprimidos), básico instalado ≤ 900 MB; `xgboost` fuera; `bcv` dentro; `ifctester` en `civil` | `bcv`/`ifctester` **cerrados por RV‑24**; los límites, a ratificar | si S3/S4 pesan más de lo estimado, `civil` y luego `anomalias` pasan a componentes opcionales |
| RS5‑6 | Un solo camino de migración (`upgrade head`) con base idempotente, sin `stamp` (DA‑S5‑4) | a ratificar | crear una base nueva tarda algo más que `create_all` + `stamp` |
| RS5‑7 | Vuelta atrás = restaurar el respaldo; sin `downgrade` para el usuario (DA‑S5‑6) | a ratificar | bajar de versión exige restaurar y perder lo hecho después del respaldo |
| RS5‑8 | Sin TLS en la red local en la 1.0.0 (responde RS3‑8), **con las condiciones de RV‑15**: red apagada por defecto, IP explícita, regla limitada a la subred y al perfil Privado, operaciones sensibles solo desde el propio equipo, aviso en la pantalla de acceso, «red de confianza» definida | **cerrado por RV‑15** | las contraseñas viajan sin cifrar en la red de la oficina; TLS (proxy inverso local) queda para 1.x |
| RS5‑9 | El producto arranca en **modo entrega** (Investigación oculta) salvo que la configuración diga lo contrario | a ratificar por Eugenio (maestro §10) | quien quiera escenarios, similares, simulador o visor debe activarlo en `silice.toml` |
| RS5‑10 | Instalador sin firma de código; `SHA256SUMS` **firmado con Ed25519 del proyecto** y huella de la clave publicada en el manual y la tesis | la firma de `SHA256SUMS`, **cerrada por RV‑16**; comprar un certificado, a decidir por Eugenio (maestro §10) | SmartScreen avisa; un certificado de firma tiene costo anual |
| RS5‑11 | La red local se activa solo desde el equipo servidor con elevación, no desde el navegador | a ratificar | menos cómodo para un administrador remoto |
| RS5‑12 | Los `.bat`, el paquete portable y `requirements.txt` sin versionar no se incorporan; `COMPARTIR_ONLINE.bat` (túnel público) queda fuera de la 1.0.0 | a decidir por Eugenio (maestro §10) | si Eugenio necesita mostrar el sistema por internet antes de 2.x, se hace fuera del producto, sin datos reales y en un equipo desechable |
| RS5‑13 | `v1.0-tesis` apunta al commit de `v1.0.0` (o de un `v1.0.x`), nunca a uno sin etiqueta SemVer; Med se mide con `v1.0.0-rc.N` | a ratificar por Eugenio (maestro §10) | si el tutor exige congelar antes del instalador, `v1.0-tesis` iría a una 0.9.x y la tesis lo declara |
| RS5‑14 | El servidor es una ventana de consola minimizada (DA‑S5‑5) | a ratificar | una ventana más en la barra de tareas; un ícono en la bandeja sería más pulido |
| RS5‑15 | Dos bases y dos destinos de migración (`instalacion.db` y `casos\*.db`), respaldadas juntas en un juego con una ficha (DA‑S5‑7) | **cerrado por RV‑4** | ninguno conocido |
| RS5‑16 | Los casos se abren solo desde `datos\casos\` vía `preparar_base`; sin rutas libres | **cerrado por RV‑5** | quien guardaba casos en otra carpeta debe subirlos |
| RS5‑17 | Restaurar un juego con `instalacion.db` exige revisar los eventos de seguridad perdidos | **cerrado por RV‑16** | un paso más tras cada restauración |

---

## 15. Riesgos

| Riesgo | Mitigación |
|---|---|
| Ruedas que necesitan el redistribuible de Visual C++ (`msvcp140.dll`, típico de `torch`) y un Windows limpio no lo trae; el runner sí, y la prueba de humo no lo vería | prueba a mano en un equipo sin herramientas de desarrollo (S5‑5); si falla, se incluyen las DLL del redistribuible junto al Python (Microsoft permite redistribuirlas con la aplicación; a confirmar la licencia vigente) |
| La CI corre como administrador: no prueba la instalación sin permisos | prueba a mano en una cuenta estándar (Windows 11 Home permite crearla) |
| Antivirus o SmartScreen bloquean un instalador sin firma | `SHA256SUMS` firmado, manual; firma de código en 1.x si hace falta (RS5‑10) |
| El tamaño real con LZMA2 difiere de la estimación con xz | medido en S5‑3.4; recorte de RS5‑5 |
| Streamlit cambia opciones o ruta de salud; quedan paquetes viejos en `{app}`; una ruta no ASCII rompe algo | versión fijada en `uv.lock` y prueba de humo; `[InstallDelete]` (§5.4); espacios y `ñ` en la prueba |
| Concurrencia de SQLite con varios usuarios en la red local | un solo proceso servidor; SL‑E12 de S3 (`busy_timeout`, WAL, `BEGIN IMMEDIATE`) |
| Una versión intermedia no deja su base de prueba en su compuerta | S5‑M3 la exige por cada versión etiquetada; reconstruirla después desde la etiqueta es posible pero se declara |
| Un túnel local (p. ej. un servicio `cloudflared` de otro proyecto) publica Sílice en internet | aviso al arrancar (3f), manual, tabla de amenazas (§10.4); el control es la clave |
| La IP de la red local cambia (DHCP) | arranque en `127.0.0.1` con aviso (3e); el manual recomienda reservar la IP en el enrutador |
| Minutos de Windows de la CI en un repositorio privado | filtros por ruta; completo solo con etiqueta o a mano |
| Una conexión saliente por sockets directos | cortafuegos de salida con registro y muestreo de conexiones en la prueba de humo; navegador sin interfaz para lo del navegador (§11.2) |

---

## 16. Preguntas abiertas

**Cerradas por los rulings de la revisión (2026‑10‑11):**

- **1.** ~~¿Alembic con la revisión base de la 0.9.0 o adelantado a la 0.6.0?~~ Cerrada por **RV‑3**: se adelanta a la
  0.6.0, con base en el esquema de la 0.5.0.
- **3.** ~~¿Red local sin TLS en la 1.0.0?~~ Cerrada por **RV‑15**: sí, con las condiciones de §8.2 (RS5‑8).
- **11.** ~~¿Cómo se tratan la base de la instalación y las demás bases de caso?~~ Cerrada por **RV‑4** y **RV‑5**.

**Para Eugenio (se responden en el maestro §10):**

- **2.** ¿Instalación solo por usuario (RS5‑3), o también por equipo para oficinas con varias cuentas de Windows?
- **4.** ¿Modo entrega por defecto en el producto (RS5‑9)?
- **5.** ¿Se compra un certificado de firma de código o se acepta el aviso de SmartScreen con `SHA256SUMS` firmado (RS5‑10)?
- **6.** ¿Quién publica el *release* y firma `SHA256SUMS` (el controlador a mano, por defecto, o la CI con permiso de
  escritura y la clave en un secreto)?
- **7.** ¿Qué licencia lleva Sílice? (**maestro §10, P9**). El repositorio no tiene archivo `LICENSE` y un instalador que se
  entrega a empresas debe mostrar una (el asistente de Inno puede presentarla). Bloquea publicar el instalador.
- **8.** ¿Qué se hace con los `.bat`, el paquete portable y `requirements.txt` sin versionar (RS5‑12)?
- **9.** ¿Hay un segundo equipo o máquina virtual para la prueba a mano en limpio? Windows 11 Home no trae Sandbox ni
  Hyper‑V.
- **10.** ¿Se confirma que `v1.0-tesis` sea el mismo commit que `v1.0.0` y que Med se mida con el instalador rc (RS5‑13)?
- **12.** ¿Se pueden redistribuir en el instalador los PDF de MaPreX de `data/precios`? Mientras no se aclare, no viajan
  (§7.1).

---

## 17. Fuentes y verificación

**Verificado el 2026‑10‑11:** ayuda de Inno Setup (`PrivilegesRequired`, constantes, parámetros silenciosos de
instalación y desinstalación, `DiskSpanning`, `[Icons]`, español oficial) y sus versiones; README de
`actions/runner-images` (Windows 2022/2025); `uv 0.11.9 --help` y la distribución que instala (con
`EXTERNALLY-MANAGED`); Alembic 1.20.0 (lista de `MetaData`, modo *batch*, `create_all` + `stamp`,
`Config.attributes`); `netsh advfirewall`; Streamlit 1.62.0 en este equipo (§1.2); tamaños de §1.3; en el
repositorio: `api/main.py:18`, `ui/paginas/inicio.py:18` y `:50`, `ui/paginas/actualizacion.py:69`,
`ui/paginas/simulador.py:22`, `ui/caso.py:128`, y que no hay `.streamlit/config.toml` versionado. **A confirmar:**
lo marcado así en el texto (entre otros, `st.context.ip_address`, la precedencia de las opciones de línea de
órdenes, que `pip-audit` lea el formato de `uv export`, que Streamlit con la dirección fijada no consulte su IP
pública), y los tamaños de S5‑0.3 y S5‑3.4. Revisión por encargo: informes de requisitos, arquitectura, pruebas,
hechos y seguridad del 2026‑10‑11 y rulings RV‑1…RV‑26.
