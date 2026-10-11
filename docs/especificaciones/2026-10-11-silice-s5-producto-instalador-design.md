# Sílice S5: producto e instalador (1.0.0 «Sílice»)

| Campo | Valor |
|---|---|
| Estado | **propuesta**, pendiente de la aprobación de Eugenio y de la revisión por encargo (requisitos, arquitectura, pruebas y calidad, verificador de hechos, usabilidad y **seguridad**, maestro §6). Los rulings de §14 quedan «pendientes de ratificar por Eugenio» |
| Fecha | 2026‑10‑11 |
| Rama del spec | `inc/silice` (worktree `.worktrees/silice`); construcción en `inc/silice-s5` (maestro §6) |
| Versión que entrega | **1.0.0 «Sílice»**, después de 0.6.0 a 0.9.0 (maestro §5) |
| Se apoya en | [spec maestro](2026-10-11-silice-1.0.0-design.md) (S‑D3, S‑D6, §3, §4, §5), [S1](2026-10-11-silice-s1-moneda-reajuste-design.md) y [S2](2026-10-11-silice-s2-presupuesto-vivo-design.md) (tablas aditivas hasta S5), [S3](2026-10-11-silice-s3-auditor-paquete-design.md) (cuentas, claves de API, código de instalación, TLS diferido a S5), [S4](2026-10-11-silice-s4-asistente-ia-design.md) (extra `ia`), [spec SF](2026-10-04-sprint-final-prototipo-design.md) (formato), [PLAN_CIERRE.md](../../PLAN_CIERRE.md) (Med y `v1.0-tesis`) |
| Documentos que enmienda | [ERS](../ERS.md), [arquitectura](../arquitectura.md), [modelo de datos](../modelo_datos.md), [plan de pruebas](../plan_pruebas.md), [calidad](../calidad_iso25010.md), [manual de usuario](../manual_usuario.md), [manual técnico](../manual_tecnico.md) (§6 y §10.5), [README](../../README.md), `pyproject.toml`, `.github/workflows/` |
| Naturaleza de los datos | igual que [NORMAS.md §1](../../NORMAS.md): el caso de demostración que el instalador ofrece es construido y se declara como tal |

Este documento es la fuente única del diseño de S5. El plan de sesiones (`PLAN_S5.md`) se escribe después de
aprobarlo y lo enlaza. **S5 no toca `core/` por diseño** (§5.1); los expedientes asignados quedan reservados con su
disparador.

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
  por `crear_esquema_espacio`). S1 a S4 agregan tablas aditivas y delegan en S5 la revisión base de Alembic.
- **Nueve páginas, `ui/caso.py:128` y la API (`api/dependencias.py:22`) llaman a `crear_esquema` al abrir**.
- **Rutas relativas al directorio de trabajo.** La base por defecto es `data/apu.db` (`ui/caso.py:37`,
  `api/dependencias.py:14`, `scripts/seed*.py`); el visor lee `data/samples/tanquilla.ifc`
  (`ui/paginas/visor.py:52`). La interfaz **importa en tiempo de ejecución** `scripts.seed`, `scripts.seed_demo` y
  `scripts.simular_lista`, y estos importan `tests.fixtures` (NORMAS §6 ya lo advierte). Un instalador que copie solo
  `core/ adapters/ ml/ ui/ api/` no arranca.
- **Streamlit 1.62.0, probado aquí con un Python autónomo de `uv`:**
  - sin `server.address`, escucha en **todas las interfaces** (`0.0.0.0:8598` y `[::]:8598` en `netstat`) e imprime
    una «External URL» con la IP pública: el arranque actual (README, manual de usuario §2) ya expone la aplicación a
    la red. Con `--server.address 127.0.0.1` escucha solo en el bucle local y no imprime esa URL;
  - `browser.gatherUsageStats` vale `true` por defecto (`streamlit config show`): envía estadísticas de uso a
    Streamlit, lo que contradice RNF‑08;
  - `GET /_stcore/health` responde `200 ok` a los ~2 s con una app mínima; el servidor arranca sobre Uvicorn.
- **El visor 3D descarga three.js de `cdnjs.cloudflare.com`** (`ui/paginas/visor.py:55`; excepción declarada en
  RNF‑08): sin internet, esa pantalla no funciona.
- **Versión:** `pyproject.toml` dice `0.1.0`, `api/main.py:20` fija `version="0.1.0"` a mano y existe la etiqueta
  anotada `v0.5.0` (8610053, PR #29), cuyo mensaje dice «el versionado se alinea en S5». No hay `CHANGELOG.md`.
  `.python-version` dice `3.13`, la de la CI.
- **Extras:** `xgboost` está en el extra `ml`, pero ningún código del producto lo importa (solo el nombre de una
  técnica en `ml/prediction/reglas.py:62`). La pantalla de actualización usa `scikit-learn` (atípicos,
  `ui/paginas/actualizacion.py:387‑393`); la similitud usa `sentence-transformers` y descarga el modelo
  `paraphrase-multilingual-MiniLM-L12-v2` la primera vez (RNF‑08).
- **Precedente sin versionar** en el checkout principal: `INICIAR_PROTOTIPO.bat` (descarga `uv` de internet si falta,
  `uv sync --all-extras`, siembra la demostración y arranca sin `server.address`),
  `scripts/crear_paquete_portable.ps1`, `requirements.txt` (redundante con `uv.lock`) y `COMPARTIR_ONLINE.bat`, que
  abre un **túnel público** de Cloudflare: eso es un servidor en internet, fuera de la 1.0.0 (maestro §1) y contrario
  a §4. S5 no los toca; los sustituye (§14, RS5‑12).
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
| Código y datos del repositorio (`core adapters ml ui api scripts tests/fixtures data`) | — | ~11 MB | 7 MB |
| Básico: base + `ui` + `api` + `planos` + `informes` | pandas, numpy, streamlit, pyarrow (86), pydeck (47), matplotlib, ezdxf | 348 MB | 62 MB |
| `civil` | ifcopenshell (81), shapely | +87 MB | 16 MB |
| Anomalías (`scikit-learn`, `scipy`, `joblib`, `threadpoolctl`) | | +136 MB | 26 MB |
| `xgboost` | | +58 MB | no va al instalador |
| Similitud: `sentence-transformers` y su cierre (torch 466, transformers, tokenizers…) | | +589 MB | 88 MB |
| Modelo `paraphrase-multilingual-MiniLM-L12-v2` (`model.safetensors` 449 MB) | | 458 MB | 408 MB |
| Dependencias de S3 (`argon2-cffi`, `cryptography`, IDS) y S4 (`anthropic`, cliente de Ollama, `keyring`) | | **a medir en S5‑0.3** | **a medir en S5‑0.3** |

Con esas cifras: **instalador básico ≈ 126 MB** más S3/S4 (Python, código, básico, civil y anomalías), unos 650 MB
instalado; el módulo de **similitud ≈ 496 MB** comprimido y ≈ 1,05 GB instalado. Los paquetes CUDA de la rama Linux
del candado no se instalan en Windows.

### 1.4 Criterio de éxito de S5

En un Windows 10 u 11 limpio, **sin internet y sin permisos de administrador**, una persona instala Sílice con el
asistente, hace doble clic en el acceso directo, el navegador se abre en la aplicación y crea el primer administrador
(S3). Después instala la versión siguiente: su base se respalda, se migra y sus presupuestos recargan con el mismo
informe. Al desinstalar, sus datos quedan. Nada de esto abre una conexión fuera del equipo. La CI lo comprueba en cada
versión (§11).

---

## 2. Relación con S1–S4, el plan de cierre y Med

- **S1 a S4** siguen la regla de tablas aditivas con `crear_esquema` (S1 §5.2, S2 §6.1, S3 §7.4). S5 escribe la
  **revisión base de Alembic con el esquema de la 0.9.0** y adopta las bases de 0.5.0 a 0.9.0 (§6.4). Desde la
  1.0.0, todo cambio de esquema trae su revisión.
- **S3** deja a S5: el paso del código de instalación (S3 §5.5), extender la clave de la API a las rutas antiguas
  (S3 §10) y decidir TLS en la red local (RS3‑8). S5 responde en §8.
- **S4** pone el extra `ia`; S5 lo incluye en el instalador básico (§7.2).
- **Med y `v1.0-tesis`.** Las mediciones con las dos personas (maestro §5 y §7; indicador 3, RNF‑04, CP‑07, RNF‑13)
  se hacen sobre el **instalador `v1.0.0-rc.N`**, en un equipo preparado con él. `v1.0-tesis` (F3 de PLAN_CIERRE)
  apunta siempre a un commit que ya tiene una etiqueta `v1.0.x` (§9.3).

---

## 3. Alcance

**Incluye:** Alembic con revisión base, adopción de bases anteriores, respaldo automático y restauración (§6);
instalador de Windows con Inno Setup, Python autónomo, dependencias sin internet, componentes opcionales, acceso
directo, actualización y desinstalación que conserva los datos (§7); arranque y parada, configuración, red local y API
apagadas por defecto, clave en toda la API, registro sin secretos (§8); versionado, `CHANGELOG.md` y etiquetas (§9);
endurecimiento y manuales, incluido un manual de instalación nuevo (§10); construcción y prueba de humo del instalador
en la CI (§11).

**No incluye:** instalador para Linux o macOS (en Linux sigue el camino de desarrollo con `uv sync`, RNF‑07);
Windows ARM64; TLS en la red local (RS5‑8); un servidor en internet o túneles públicos (2.x); firma de código del
instalador (RS5‑10); actualización automática por internet; base de datos en una carpeta compartida de red.

---

## 4. Requisitos (enmienda a la ERS, IEEE 830)

**Numeración** (maestro §9): UC‑24; RF‑96 a RF‑99; RNF‑19 y RNF‑20; expedientes SL‑E11 y SL‑E12. Se usan todos los
números de requisito; **SL‑E11 y SL‑E12 quedan reservados y vacantes** mientras no se cumpla su disparador (§5.1).

### 4.1 Caso de uso

| UC | Nombre | Actor | Precondición | Flujos alternos conocidos |
|---|---|---|---|---|
| UC‑24 | Instalar, actualizar y operar Sílice en un equipo | **administrador de la instalación** (S3); quien arma y quien revisa solo usan el acceso directo o el navegador | Windows 10 22H2 u 11, x64; cuenta de usuario (no hace falta que sea administradora) | 24a espacio en disco insuficiente: el asistente lo dice antes de copiar; 24b actualización con una migración que falla: la base se restaura del respaldo, Sílice no arranca y explica qué hacer; 24c el puerto está ocupado por otro programa: mensaje con el puerto y cómo cambiarlo; 24d base de otra versión no adoptable (anterior a 0.5.0 o alterada a mano): no se toca y se explica; 24e base de una versión más nueva que el programa (bajó de versión): no arranca, ofrece restaurar el respaldo previo; 24f activar la red local sin poder elevar permisos: queda apagada y se explica; 24g función de similitud sin su módulo: la pantalla dice cuál módulo falta (RF‑97 g); 24h ya hay un Sílice en marcha: el acceso directo abre el navegador y no arranca otro; 24i desinstalar: los datos quedan y el asistente dice dónde |

UC existentes que se enmiendan: **UC‑12** (los recorridos parten del acceso directo, no de la terminal) y **UC‑21**
de S3 (el primer administrador se crea con el código que el arranque deja en la carpeta de datos, §8.1).

### 4.2 Requisitos funcionales

Prioridad: E = esencial, D = deseable. Fases de §13.

| RF | Requisito | UC | Pri. | Fase | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑96 | **Migraciones con respaldo y vuelta atrás.** El esquema se versiona con Alembic: una revisión base con el esquema de la 0.9.0 y una revisión por cada cambio posterior. Antes de aplicar cualquier revisión pendiente se respalda la base; si la migración falla, la base se restaura sola. Las bases de 0.5.0 a 0.9.0 se adoptan (§6) | UC‑24 | E | S5‑1 | (a) una base vacía y una base de cada versión 0.5.0…0.9.0 (fixtures) llegan a `head`, y sus presupuestos recargan con el mismo total e informe; (b) existe un respaldo que pasa `PRAGMA integrity_check` y cuya huella está en su ficha; (c) con un fallo inyectado en una revisión, la huella SHA‑256 de la base tras el intento es igual a la de antes; (d) una base con revisión desconocida o no adoptable no se modifica (huella igual) y el mensaje dice qué hacer |
| RF‑97 | **Instalador para Windows.** Un `Silice-<versión>.exe` (básico) y un `Silice-<versión>-completo.exe` (con el módulo de similitud) instalan sin internet ni permisos de administrador: Python autónomo, dependencias y código; crean el acceso directo «Sílice» que arranca y abre el navegador y «Detener Sílice»; la actualización detiene Sílice, reemplaza el programa y migra con respaldo; la desinstalación borra el programa y **conserva los datos** | UC‑24 | E (básico); D (completo) | S5‑3 | prueba de humo de §11.2: instalación silenciosa en una ruta con espacios y acentos, salud `200` ≤ 60 s, solo `127.0.0.1` escuchando, nada escrito en la carpeta del programa, actualización con respaldo y revisión `head`, desinstalación sin carpeta de programa y con la carpeta de datos intacta; (g) sin el módulo de similitud, la pantalla de similares lo dice con su nombre |
| RF‑98 | **Operación segura por defecto.** Arranque y parada con una sola instancia; red local **apagada** y activable solo desde el equipo servidor con elevación y regla de cortafuegos limitada a la subred local y al perfil Privado; API **apagada**, con clave en **todas** sus rutas salvo `/salud` y que rechaza clientes fuera de redes privadas; registro de errores rotativo **sin secretos**; ninguna conexión saliente en la operación | UC‑24 | E | S5‑2 | pruebas de §12: configuración por defecto; con la API activa, `401` sin clave en cada ruta del esquema y `403` desde una IP pública simulada; un registro con secretos sembrados no contiene ninguno; prueba de humo con un proxy testigo: **0** peticiones salientes desde el arranque hasta la parada (§11.2) |
| RF‑99 | **Versión y registro de cambios.** Una sola fuente de la versión (`pyproject.toml`); la API, la pantalla «Acerca de» y el instalador la leen de ahí; «Acerca de» muestra además la revisión del esquema, la carpeta de datos y los módulos instalados; `CHANGELOG.md` con una sección por versión; una etiqueta anotada por versión | UC‑24 | E | S5‑0, S5‑4 | `meta_s5.py`: versión de `pyproject` = la de la API = la del instalador; sección del `CHANGELOG` para la versión en curso con fecha; en un *push* de etiqueta, la etiqueta (`v` + SemVer) coincide con `pyproject` normalizado (PEP 440) o la CI falla |

### 4.3 Requisitos no funcionales (ISO/IEC 25010)

Se usan los nombres de la edición de 2011, como [calidad_iso25010.md](../calidad_iso25010.md); en la edición de 2023
«portabilidad» se llama «flexibilidad» (a confirmar en S5‑0 contra la norma antes de citarlo en la tesis).

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑19 | **Portabilidad** (instalabilidad, adaptabilidad, reemplazabilidad) | Instalador básico **≤ 150 MB**; básico instalado ≤ 900 MB; completo ≤ 650 MB. Se instala sin internet y sin administrador, en Windows 10 22H2 y 11 x64, en una ruta con espacios y caracteres no ASCII. Del acceso directo a la salud `200`: ≤ 60 s en la CI y ≤ 20 s en el equipo de desarrollo. Actualizar conserva el 100 % de los datos (filas por tabla y huella de los informes de la fixture) | tamaño de los artefactos de la CI (falla si se pasa); prueba de humo de §11.2; tiempo de arranque medido en el equipo de desarrollo (mediana de cinco, como RNF‑11) y anotado en plan_pruebas §10; la instalación en una cuenta estándar sin administrador, a mano en S5‑5 (la CI corre como administrador) |
| RNF‑20 | **Mantenibilidad** (modificabilidad, capacidad de prueba) | Cero deriva de esquema: una base llevada a `head` por las migraciones es igual a la creada con `create_all` de todos los `MetaData`, y la autogeneración de Alembic contra ella no propone cambios; toda `MetaData` con tablas está registrada en las migraciones; cada revisión baja y vuelve a subir; el instalador se construye solo desde `uv.lock` (`--frozen`) con un manifiesto de archivos y huellas | `tests/integration/test_migraciones.py` en Linux y Windows en cada PR; `meta_s5.py`; el manifiesto se publica con el instalador |

---

## 5. Arquitectura (vistas 4+1)

### 5.1 Principio que se conserva

NORMAS §2: núcleo cerrado. **S5 no modifica `core/`.** `crear_esquema` se queda como está (lo usan las pruebas en
memoria y el camino de desarrollo); la operación del producto vive fuera del núcleo y solo importa
`core.catalog`/`core.models`. Los expedientes reservados se abren **solo** si se cumple su disparador:

| Expediente | Disparador | Cambio que pediría |
|---|---|---|
| SL‑E11 | una revisión necesita borrar o cambiar una restricción **sin nombre** de `core/models` y el `naming_convention` por revisión de `batch_alter_table` no alcanza | convención de nombres en `Base.metadata` (cambia los nombres de restricciones nuevas; no los existentes) |
| SL‑E12 | la prueba de varios usuarios en la red local (S3 §13.4) o la de humo dan `database is locked` | `PRAGMA busy_timeout` y diario WAL en `crear_motor` |

Si ninguno se dispara, ambos quedan **vacantes** y así se declara al cerrar S5.

### 5.2 Vista lógica y de desarrollo

| Pieza | Qué hace | Importa | Toca `core/` |
|---|---|---|---|
| `migraciones/` (nuevo): `env.py`, `script.py.mako`, `versions/0001_base_0_9_0.py` | entorno de Alembic sin `alembic.ini` (configuración programática); `METADATAS` = lista de todas las `MetaData` | `core.models`, `adapters.espacio.persistencia` (y las de S3/S4) | no |
| `operacion/` (nuevo, sin Streamlit): `rutas.py`, `config.py`, `base_datos.py`, `respaldo.py`, `lanzador.py`, `red.py`, `registro.py`, `version.py`, `__main__.py` | carpetas de datos, configuración, preparar y migrar la base, respaldar y restaurar, arrancar y parar, red local, registro, versión; CLI `python -m operacion …` | `core.catalog`, `migraciones`, biblioteca estándar | no |
| `api/seguridad.py` (nuevo) y `api/main.py` | clave en todas las rutas (cabecera que fija S3‑0), filtro de redes privadas, documentación interactiva apagada en el producto, versión desde `operacion.version` | `operacion.config`, `operacion.version` | no |
| `ui/paginas/acerca.py` (nueva) y la pestaña **Instalación** de Administración (S3) | versión, revisión, carpeta de datos, módulos; estado de red local y API, respaldos (crear, listar, descargar) | `operacion` (nunca `operacion.lanzador`) | no |
| `ui/paginas/visor.py` | three.js servido desde el paquete (`ui/estaticos/`), no desde la CDN | — | no |
| `adapters/espacio/persistencia.py` | exporta `METADATA_ESPACIO` (hoy `_metadata` privada) | — | no |
| `instalador/` (nuevo): `silice.iss`, `construir.py`, `manifiesto.toml`, `humo.ps1`, `licencias/` | construir el instalador y probarlo | — (no se importa desde el código) | no |
| `pyproject.toml` | `alembic` como dependencia base; extras `anomalias` (`scikit-learn`) y `similitud` (`sentence-transformers`); `ml` = `anomalias` + `similitud` + `xgboost` para la CI y la investigación | — | — |

`tests/unit/test_arquitectura.py` gana: `core` no importa `operacion` ni `migraciones`; `operacion` no importa
`streamlit`, `ui` ni `api`; `ui` y `api` solo importan `operacion.config`, `operacion.version` y
`operacion.respaldo`; `migraciones` no importa `ui` ni `api`. `known-first-party` de ruff suma los dos paquetes.

### 5.3 Vista física: dónde vive cada cosa

```
%LOCALAPPDATA%\Programs\Silice\        {app}: programa (se reemplaza entero al actualizar)
  python\                              CPython autónomo + capa básica en Lib\site-packages
  modulos\similitud\                   paquetes de similitud + modelo (solo con el componente)
  codigo\                              core adapters ml ui api operacion migraciones scripts tests\fixtures data pyproject.toml
  manifiesto.json  LICENCIAS\  unins000.exe
%LOCALAPPDATA%\Silice\                 datos del usuario: el desinstalador NO los toca
  config\silice.toml                   red local, API, puertos, nivel del registro
  datos\silice.db                      la base de la instalación
  datos\demostracion.db                caso construido de demostración (solo si se pide)
  datos\codigo_instalacion.txt         código de un solo uso de S3 (se borra al usarlo)
  respaldos\                           silice_<AAAAMMDD-HHMMSS>_<rev-origen>_a_<rev-destino>.db + .json
  registros\silice.log (+ .1 … .5)     registro rotativo
  estado\servidor.json                 PID, puertos y hora de arranque de la instancia viva
```

- `{app}` es `{autopf}\Silice`, que en modo sin administrador Inno resuelve a `{userpf}` (verificado en la ayuda de
  Inno Setup); que `{userpf}` sea `%LOCALAPPDATA%\Programs` se confirma en la prueba de humo.
- Los datos van en `{localappdata}` (igual en ambos modos de Inno), **fuera** de la carpeta del programa: OneDrive no
  sincroniza `%LOCALAPPDATA%` y el desinstalador solo borra lo que instaló. `SILICE_DATOS` cambia la carpeta (pruebas
  y casos especiales). Los nombres de carpeta van sin tilde (`Silice`); el nombre visible es «Sílice».
- El directorio de trabajo del servidor es `{app}\codigo` (las rutas relativas de `data/samples` y `data/precios`
  siguen valiendo) y el lanzador fija `ARENIA_CASO` y `APU_BASE` hacia `datos\silice.db`: ninguna escritura cae en
  la carpeta del programa (lo comprueba la prueba de humo).

### 5.4 Vista de procesos

**Arranque** (`python.exe -E -s -B -m operacion arrancar`, desde el acceso directo):

1. Si `estado\servidor.json` existe y `/_stcore/health` responde, abre el navegador y termina (24h).
2. Lee `config\silice.toml` (lo crea con los valores por defecto si falta) y configura el registro.
3. `preparar_base`: si hay revisiones pendientes, respalda y migra (§6); si falla, restaura y se detiene con mensaje.
   Si no hay usuarios (S3), genera el código de instalación y lo muestra en la consola.
4. Lanza Streamlit como proceso hijo con las opciones de §10.1 y, si `api.activa`, Uvicorn con `api.main:app`;
   escribe `servidor.json`.
5. Espera la salud `200` (hasta 60 s), abre `http://127.0.0.1:<puerto>` con `webbrowser` y queda en primer plano.

**Parada:** cerrar la ventana de Sílice (minimizada, «Para detener Sílice, cierre esta ventana») o el acceso
«Detener Sílice» (`operacion parar`: termina los procesos de `servidor.json` y borra el archivo). Las banderas `-E`
(ignora `PYTHON*` del entorno), `-s` (sin `site-packages` del usuario) y `-B` (sin `.pyc` nuevos) aíslan el Python
autónomo de cualquier otro Python del equipo.

**Actualización:** el instalador detiene Sílice (`operacion parar`, desde `PrepareToInstall`), borra `{app}\python`,
`{app}\modulos` y `{app}\codigo` (`[InstallDelete]`, para que no queden paquetes de la versión anterior), copia la
nueva versión y ejecuta `operacion migrar`. El arranque vuelve a comprobar la revisión: la migración tiene un solo
camino de código y es idempotente.

### 5.5 Decisiones de diseño

| # | Decisión | Alternativa descartada | Por qué |
|---|---|---|---|
| DA‑S5‑1 | Dependencias **preinstaladas al construir**, en capas (básica dentro del Python autónomo; similitud en `modulos\similitud` añadida con un `.pth`) | carpeta de ruedas e instalación con `uv` durante el asistente | instalar no ejecuta un resolvedor en el equipo del cliente; lo que se probó en la CI es lo que se instala |
| DA‑S5‑2 | Paquetes en el Python autónomo, sin entorno virtual | `uv venv --relocatable` | un entorno virtual guarda la ruta de su intérprete; el Python autónomo movido de carpeta sigue funcionando (probado hoy con Streamlit 1.62.0) |
| DA‑S5‑3 | Instalación **por usuario** (`PrivilegesRequired=lowest`) | por equipo en `Program Files` | instala sin administrador; el administrador solo hace falta para la regla de cortafuegos de la red local |
| DA‑S5‑4 | Un solo camino de migración: siempre `upgrade head`, con una revisión base **idempotente** que crea las tablas que faltan y verifica las existentes | `create_all` + `stamp head` para bases nuevas (receta del libro de cocina de Alembic) | la base nueva, la adoptada y la actualizada pasan por el mismo código y las mismas pruebas |
| DA‑S5‑5 | Ventana de consola minimizada como «servidor» | ícono en la bandeja o servicio de Windows | cerrar la ventana detiene todo, sin procesos huérfanos; es lo que Eugenio ya usó con el `.bat` |
| DA‑S5‑6 | Vuelta atrás = restaurar el respaldo; `downgrade()` existe y se prueba en la CI, pero no se ofrece al usuario | bajar de revisión desde la interfaz | restaurar es exacto; un `downgrade` puede perder datos de columnas nuevas |

---

## 6. Migraciones con Alembic (RF‑96, RNF‑20)

### 6.1 Punto de partida

La revisión `0001_base_0_9_0` contiene el esquema **de la 0.9.0** (todas las tablas de `core/models`, `esp_*` y las
aditivas de S1–S4), generado una vez con la autogeneración de Alembic contra una base vacía, **revisado a mano y
congelado**: no se deriva de los modelos en cada corrida. Se escribe idempotente: para cada tabla, si no existe la
crea; si existe, compara columnas (nombre, tipo, nulabilidad) e índices con su definición y, ante una diferencia,
lanza `BaseNoAdoptable` con la lista. `render_as_batch=True` en `env.py` (SQLite casi no tiene `ALTER`; Alembic usa
«mover y copiar» y solo en SQLite). `target_metadata = METADATAS` (Alembic admite una lista de `MetaData`). Versión de
Alembic: la vigente al construir (la documentación consultada hoy es la 1.20.0), fijada en `uv.lock`.

### 6.2 Convivencia con `crear_esquema`

- **Producto:** el lanzador ejecuta `preparar_base` **antes** de arrancar la interfaz y la API. Cuando las páginas
  llaman a `crear_esquema`, la base ya está en `head` y `create_all` no hace nada.
- **Desarrollo y pruebas:** `crear_esquema` sigue igual (bases en memoria). `scripts/seed*.py` llaman a
  `preparar_base` cuando la URL es un archivo.
- **Red de seguridad:** si alguien agrega una tabla al modelo sin revisión, `create_all` la crearía «por el costado»
  en las bases existentes. Lo atrapan dos pruebas de RNF‑20: la autogeneración contra una base en `head` debe venir
  vacía, y `crear_esquema` + `crear_esquema_espacio` sobre una base en `head` no deben cambiar nada (instantánea del
  esquema igual antes y después).

### 6.3 Respaldo automático

Antes de aplicar **cualquier** revisión pendiente (también la base, en una adopción):

1. copia con la API de respaldo de `sqlite3` (`Connection.backup`, segura con la base abierta) a
   `respaldos\silice_<fecha>_<rev-origen>_a_<rev-destino>.db`;
2. `PRAGMA integrity_check` sobre la copia, que debe dar `ok`;
3. ficha `.json` con versión de Sílice, revisiones, filas por tabla y SHA‑256 de la copia.

Sin respaldo verificado no se migra. Se conservan los respaldos de las **cinco** últimas migraciones y todos los
manuales; nunca se borra el más reciente. Los respaldos contienen todo (huellas de contraseñas, la clave privada
cifrada de S3): viven en la carpeta protegida del usuario y el manual advierte al copiarlos.

### 6.4 Adopción de bases anteriores y casos límite

| Base encontrada | Qué hace `preparar_base` |
|---|---|
| no existe o está vacía | `upgrade head` (la base se crea por las revisiones) |
| sin `alembic_version`, con tablas de 0.5.0–0.9.0 | respaldo → `upgrade head`: la base idempotente crea las tablas aditivas que falten y verifica el resto → revisiones siguientes |
| sin `alembic_version`, con columnas que no cuadran (p. ej. sin `modalidad`, anterior a P2) | `BaseNoAdoptable`: se restaura el respaldo (huella igual) y el mensaje lista las diferencias y remite al manual (volver a sembrar o pedir ayuda) |
| con revisión anterior a `head` | respaldo → `upgrade head` |
| con revisión desconocida (de un Sílice más nuevo) | no se toca; «Esta base es de una versión más nueva de Sílice. Instale esa versión o restaure el respaldo previo» (24e) |
| migración que falla a medias | se restaura el respaldo; `registros\silice.log` guarda el error; el arranque se detiene (24b) |

### 6.5 Restauración y CLI

`python -m operacion respaldar | restaurar <archivo> | migrar | revision`. Restaurar exige Sílice detenido, guarda
antes la base actual como `antes_de_restaurar_<fecha>.db`, rechaza un respaldo de revisión desconocida y, si es de
una revisión anterior, la migración ocurre en el siguiente arranque (con su propio respaldo).

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
3. Copia el código según `instalador/manifiesto.toml` (lista blanca: los paquetes, `scripts/seed*.py`,
   `scripts/simular_lista.py`, `tests/fixtures/`, `data/`, `pyproject.toml`; nunca `.venv`, `*.db`, `docs/` salvo los
   manuales), `python -m compileall` y escribe `manifiesto.json` (ruta, tamaño, SHA‑256 de cada archivo).
4. Para el completo: modelo descargado una vez al construir en `modulos\similitud\hf` (`HF_HOME`); en tiempo de
   ejecución, `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1` (que cargue sin red se confirma en la prueba de humo del
   completo).
5. `LICENCIAS\`: la de Python (PSF) y la de cada paquete incluido, generadas desde los metadatos instalados.
6. `ISCC.exe /DVersion=<pyproject> /DPerfil=basico|completo instalador\silice.iss`.

### 7.2 Componentes y tamaños

| Componente | Contenido | Artefacto | Tamaño (estimado §1.3) |
|---|---|---|---|
| Programa (fijo) | Python, básica (base, `ui`, `api`, `planos`, `informes`), `civil`, `anomalias`, extra `ia` de S4, dependencias de S3, código | ambos | ≈ 126 MB + S3/S4 (a medir en S5‑0.3) |
| Caso de demostración (casilla, marcada) | ofrecer «abrir el caso de demostración» en Inicio | ambos | despreciable |
| Similitud de partidas (casilla) | paquetes de similitud y el modelo | solo el completo | ≈ 496 MB |

`xgboost` no se incluye (ningún código del producto lo importa). Si el básico pasa de 150 MB, el orden para recortar
es: `civil` a componente opcional (16 MB), luego `anomalias` (26 MB); la decisión se registra como ruling. El límite
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
Pasar del básico al completo = ejecutar el completo.

---

## 8. Operación (RF‑98)

### 8.1 Configuración y primer arranque

`config\silice.toml` (valores por defecto):

```toml
[servidor]
puerto = 8501
red_local = false        # true: escucha en la red local (§8.2)
[api]
activa = false
puerto = 8000
[interfaz]
mostrar_investigacion = false   # false = modo entrega (ARENIA_MODO_ENTREGA=1), RS5-9
[registro]
nivel = "INFO"
```

Las claves de la API viven en la base (S3: SHA‑256, se muestran una vez), no en este archivo. El código de
instalación de S3 se escribe en `datos\codigo_instalacion.txt` y en la consola del servidor; como la red local está
apagada en el primer arranque, solo alguien sentado al equipo puede crear el primer administrador.

### 8.2 Red local

- **Apagada:** Streamlit con `server.address=127.0.0.1`; la API, si está activa, también en `127.0.0.1`.
- **Activar** solo desde el equipo servidor, con el acceso «Sílice: red local (administrador)» o
  `python -m operacion red-local activar`, que pide elevación (UAC) y crea reglas de entrada para el
  `python.exe` de `{app}` y los puertos configurados con `netsh advfirewall firewall add rule … dir=in action=allow
  protocol=TCP remoteip=localsubnet profile=private`; pone `red_local = true` y avisa: «Sílice quedará visible para
  los equipos de esta red. Las contraseñas viajan sin cifrar (sin TLS): úselo solo en la red de su oficina». Al
  reiniciar, Streamlit escucha en `0.0.0.0` y la consola y la pestaña Instalación muestran la dirección
  `http://<ip-local>:<puerto>`. Sin elevación (24f) no cambia nada.
- **Desactivar** borra las reglas y vuelve a `127.0.0.1`. La pestaña Instalación muestra el estado, no lo cambia
  (cambiarlo desde un navegador remoto pediría elevación en el servidor).
- Solo IPv4 en la 1.0.0. Que Streamlit con `0.0.0.0` no consulte su IP pública (la «External URL» de §1.2) se confirma
  con el proxy testigo de la prueba de humo (a confirmar).

### 8.3 API

Apagada por defecto. Al activarla (pestaña Instalación, rol administrador, efecto al reiniciar): todas las rutas
exigen la cabecera de clave de S3 (S5 la **extiende a las rutas antiguas**: sin clave, `401` con
`{"detalle": ...}`), salvo `GET /salud` (`{"estado": "ok"}`, sin versión); un middleware responde `403` a clientes
que no son de bucle local ni de redes privadas (`ipaddress`: `is_loopback` o `is_private`), defensa adicional al
cortafuegos; `docs_url` y `openapi_url` apagados en el producto (el esquema sigue exportado en `docs/api.json`);
registro de accesos de Uvicorn apagado.

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
instalado; la usan `api/main.py`, «Acerca de» y `construir.py` (`/DVersion`). La etiqueta es SemVer con `v`
(`v1.0.0-rc.1`); la CI compara ambas normalizadas con `packaging.version` (que `1.0.0-rc.1` normalice a `1.0.0rc1`
se confirma en S5‑0).

### 9.3 Etiquetas y relación con `v1.0-tesis`

- `v0.5.0` existe. `v0.6.0` … `v0.9.0`: anotadas, sobre el commit de fusión en `main` tras la compuerta de cada
  versión, puestas por el controlador. `v1.0.0-rc.N`: el instalador que se lleva a Med. `v1.0.0`: la rc medida, sin
  cambios de código (solo documentos de resultados); si hay cambios de código después de medir, se declaran y se
  decide en la bitácora si se vuelve a medir.
- **`v1.0-tesis`** (F3 de PLAN_CIERRE) es un alias anotado que apunta **al mismo commit que `v1.0.0`** o, si la
  tesis necesita correcciones, al de un `v1.0.x`; nunca a un commit sin etiqueta SemVer. La tesis cita la versión
  SemVer («Sílice 1.0.0») y la huella del instalador.

### 9.4 `CHANGELOG.md`

Formato de *Keep a Changelog* con secciones en español (Agregado, Cambiado, Obsoleto, Eliminado, Corregido,
Seguridad) y una sección `## [x.y.z] - AAAA-MM-DD` por versión, más `## [Sin publicar]`. Entrada retroactiva para
0.5.0 (desde el mensaje de la etiqueta y la bitácora del SF) y una línea de historia para lo anterior que enlaza
`docs/bitacora/`. Cada entrada nombra sus RF y, si las hay, sus revisiones de Alembic.

---

## 10. Endurecimiento y manuales

### 10.1 Opciones fijas del servidor

El lanzador pasa a Streamlit por línea de órdenes (que tengan precedencia sobre un `config.toml` global del usuario
se confirma en S5‑2): `server.headless=true`, `server.address` según §8.2, `server.port`,
`browser.gatherUsageStats=false`, `server.fileWatcherType=none`, `server.runOnSave=false`,
`client.showErrorDetails=none`, `client.toolbarMode=minimal`, `server.maxUploadSize=20` (MB, coherente con el límite
de planos de RNF‑12), `global.developmentMode=false`; `server.enableXsrfProtection` queda en su valor por defecto
(`true`).

### 10.2 Otras medidas

three.js empaquetado (licencia MIT) y servido localmente: se retira la excepción de RNF‑08 por la CDN; similitud
sin descargas (`HF_HUB_OFFLINE`); la base nunca en una carpeta de red (SQLite sobre SMB no es fiable): el arranque
avisa si la carpeta de datos es una ruta UNC; `pip-audit` sobre las dependencias exportadas en el flujo del
instalador (deseable; a confirmar que lee el formato de `uv export`); el instalador **sin firma de código** en la
1.0.0 (RS5‑10): SmartScreen avisará «Windows protegió su PC» y el manual lo explica junto con la huella SHA‑256 que
se publica.

### 10.3 Manuales

| Documento | Cambio |
|---|---|
| `docs/manual_instalacion.md` (**nuevo**) | requisitos; instalar (básico y completo); primer arranque y primer administrador; red local; API y claves; actualizar; respaldos y restaurar; desinstalar; SmartScreen; problemas frecuentes (puerto ocupado, base no adoptable, versión más nueva) |
| `docs/manual_usuario.md` | §1–§2: el camino del instalador primero; el de desarrollo pasa al manual técnico |
| `docs/manual_tecnico.md` | §6 y §10.5 se reescriben (hay migraciones: cómo crear una revisión, la prueba de deriva); secciones nuevas: construir el instalador, la CLI `operacion`, cómo publicar una versión (CHANGELOG, `pyproject`, etiqueta) |
| `README.md` | «Arranque rápido» con dos caminos: instalador (usuario) y `uv sync` (desarrollo); el comando de Streamlit lleva `--server.address 127.0.0.1` |
| `docs/calidad_iso25010.md`, ERS | RNF‑19, RNF‑20; RNF‑07 se aclara (sigue el camino `uv sync`, ahora junto al instalador); RNF‑08 pierde la excepción de three.js |

---

## 11. Integración continua

### 11.1 En `ci.yml` (cada PR, Linux y Windows)

Las pruebas de `operacion` y `migraciones` corren dentro de la suite existente (§12). `calidad` suma
`scripts/meta_s5.py`.

### 11.2 Flujo nuevo `.github/workflows/instalador.yml` (Windows)

- **Cuándo:** etiquetas `v*`, `workflow_dispatch` y PR que tocan `instalador/`, `operacion/`, `migraciones/`,
  `pyproject.toml` o `uv.lock`. El completo, solo con etiqueta o a mano (≈ 500 MB de artefacto; minutos de Windows de
  un repositorio privado).
- **construir:** `runs-on: windows-2025` (fija, no `latest`); `setup-uv` con la versión exacta de `ci.yml`; Inno Setup
  6.7.x del runner (si falta, `choco install innosetup --version <fija>`; la ruta de `ISCC.exe` se confirma en la
  primera corrida); `construir.py`; tamaño del artefacto contra RNF‑19 (falla si se pasa); publica instalador,
  `manifiesto.json` y `SHA256SUMS`.
- **humo** (`instalador/humo.ps1`), en el mismo runner:
  1. arranca un **proxy testigo** local que anota toda petición y fija `HTTP_PROXY`/`HTTPS_PROXY` hacia él, con
     `NO_PROXY=127.0.0.1,localhost` (detecta lo que respeta proxies; un socket directo no se detecta: límite
     declarado);
  2. instala con `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /DIR="C:\Prueba Sílice\Programa ñ" /LOG=…`
     y `SILICE_DATOS` en otra ruta con espacios;
  3. inventario de archivos de `{app}`;
  4. `operacion arrancar --sin-navegador` en segundo plano; espera `GET /_stcore/health` = `200` (≤ 60 s);
     comprueba con `Get-NetTCPConnection` que el puerto escucha **solo** en `127.0.0.1` y que el 8000 no escucha;
  5. abre la página principal (HTTP 200) y crea una base con la fixture de 0.9.0 en una segunda corrida;
  6. `operacion parar`; el puerto queda libre; el inventario de `{app}` no cambió; el proxy anotó **0** peticiones;
  7. **actualización:** instala el mismo build con versión de parche +1 (`/DVersion`) sobre la base de 0.9.0: existe
     un respaldo con su ficha, `alembic_version` = `head` y los presupuestos recargan con el mismo informe;
  8. desinstala con `unins000.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`: `{app}` ya no existe; la carpeta de
     datos y sus respaldos siguen ahí;
  9. sube los registros como artefacto aunque falle.
- **Completo:** además, la página de similares carga el modelo sin red (salud de la función y proxy en 0).
- Permisos `contents: read`; la publicación del *release* la hace el controlador a mano (pregunta 6).

---

## 12. Pruebas (IEEE 829)

Pruebas antes que implementación: un commit con la prueba en rojo observada y otro con la implementación por pieza
(rol de líder de fase). Cero omitidas; ninguna toca `data/apu.db` real (siempre `tmp_path` o `SILICE_DATOS`).

| RF / RNF | Prueba |
|---|---|
| RF‑96 | `tests/integration/test_migraciones.py`: base vacía a `head`; una fixture por versión 0.5.0…0.9.0 (bases construidas con el código de esa etiqueta y versionadas en `tests/fixtures/bases/`) a `head`, con filas por tabla y recarga del presupuesto de la fixture (total e informe iguales); respaldo con `integrity_check` y huella; fallo inyectado en una revisión de prueba → huella igual a la previa; base sin `modalidad` → `BaseNoAdoptable` sin tocarla; revisión desconocida → no arranca; restaurar crea `antes_de_restaurar_*`; retención de cinco |
| RNF‑20 | `upgrade head` en vacío ≡ `create_all` de `METADATAS` (tablas, columnas, tipos, nulabilidad, índices, únicas, foráneas, `CHECK`); autogeneración contra `head` sin cambios; `crear_esquema` sobre `head` sin DDL; toda `MetaData` con tablas en `METADATAS` (se recorren los módulos de `core`, `adapters`, `asistente` y `ui` buscando instancias); `downgrade`/`upgrade` de cada revisión |
| RF‑97 | prueba de humo de §11.2; `tests/unit/test_manifiesto.py`: importar `ui.app` y `api.main` en un subproceso cuyo `sys.path` es **solo** el árbol que arma el manifiesto (sin el repositorio) |
| RF‑98 | `tests/unit/test_operacion_config.py` (valores por defecto: red y API apagadas; archivo dañado → mensaje y valores por defecto, nunca red encendida); `test_lanzador.py` (opciones de §10.1 en la orden; una sola instancia; puerto ocupado → mensaje); `test_red.py` (las órdenes `netsh` exactas, sin ejecutarlas); `tests/integration/test_api_clave.py` (cada ruta de `app.routes` salvo `/salud` da `401` sin clave; `403` con un cliente `8.8.8.8` simulado; `docs` apagado en modo producto); `test_registro.py` (secretos sembrados en mensajes, excepciones y salida de un hijo: ninguno en el archivo; rotación) |
| RF‑99 | `meta_s5.py` (S5‑M5); `test_version.py`: API = `pyproject` |
| RNF‑19 | tamaño en la CI; arranque en el equipo de desarrollo (mediana de cinco); instalación a mano en una cuenta **estándar** y en un equipo sin internet (S5‑5, procedimiento en la bitácora) |
| Interfaz | `AppTest` de «Acerca de» y de la pestaña Instalación (estado de red y API, respaldos); RF‑43 (modo entrega) intacto |
| Regresión | línea base, 7 de 7, TI‑001, las dos huellas de RNF‑04 y las cuatro hojas: sin cambios (S5 no toca `core/` ni `exportar_excel`) |

---

## 13. Tareas y fases

| Fase | Contenido | Criterio de cierre | Compuerta |
|---|---|---|---|
| **S5‑0** documentos | 0.1 enmiendas a ERS (UC‑24, RF‑96…99, RNF‑19/20, RNF‑07/08), arquitectura y plan de pruebas §8–§10; 0.2 `CHANGELOG.md` retroactivo y regla de versión; 0.3 **medir** el Python 3.13 autónomo y las dependencias de S3/S4 (completa §1.3 y fija el recorte si el básico pasa de 150 MB); 0.4 `scripts/meta_s5.py`; 0.5 confirmar ISO/IEC 25010:2023 y PEP 440 de §9.2 | documentos aprobados; metas existen en PENDIENTE | GS5‑0 |
| **S5‑1** migraciones | `alembic` en `pyproject`; `migraciones/` con `0001_base_0_9_0`; `operacion.base_datos`, `respaldo`; fixtures de bases 0.5.0–0.9.0; seeds con `preparar_base`; `METADATA_ESPACIO` | §12 RF‑96 y RNF‑20 en verde en Linux y Windows | GS5‑1 |
| **S5‑2** operación | `operacion.config`, `lanzador`, `red`, `registro`, `version`; `api/seguridad.py`; «Acerca de» y pestaña Instalación; three.js local; extras `anomalias`/`similitud`; README con `--server.address` | §12 RF‑98 y RF‑99 en verde | GS5‑2 |
| **S5‑3** instalador | `instalador/` (§7); 3.4 **medir** los artefactos reales con ISCC y anotar en §1.3 y plan_pruebas §10 | se instala, arranca, actualiza y desinstala a mano en el equipo de desarrollo | GS5‑3 |
| **S5‑4** CI | `instalador.yml` con construir y humo; tamaño y versión en la CI | flujo verde en un PR y en una etiqueta de prueba | GS5‑4 |
| **S5‑5** cierre | manuales (§10.3); prueba a mano en cuenta estándar y sin red; `v1.0.0-rc.1` para Med; revisión por encargo con seguridad y usabilidad | maestro §6: meta en OK, CI verde Linux y Windows, encargos aprobados | **GS5 = 1.0.0** |

Metas de `scripts/meta_s5.py`: **S5‑M1** requisitos en la ERS; **S5‑M2** `core/` intacto en el rango de la rama;
**S5‑M3** pruebas de migraciones y deriva en verde; **S5‑M4** pruebas de operación en verde; **S5‑M5** versión única
y sección del CHANGELOG; **S5‑M6** último flujo del instalador verde (PENDIENTE sin red; no es FALLA); **S5‑M7**
tamaño del básico ≤ 150 MB según el último artefacto; **S5‑M8** regresión.

---

## 14. Rulings para ratificar (pendientes de ratificar por Eugenio)

| # | Ruling | Costo si es erróneo |
|---|---|---|
| RS5‑1 | La revisión base de Alembic es el esquema de la **0.9.0**; hasta entonces rigen las tablas aditivas (coherente con S1 y S2) | S1–S4 no pueden cambiar columnas; si alguno lo necesita, Alembic se adelanta a esa versión y la base pasa a ser la anterior |
| RS5‑2 | S5 no toca `core/`; SL‑E11 y SL‑E12 solo con su disparador | si se disparan, dos expedientes más y el aval del tutor |
| RS5‑3 | Instalación por usuario, sin administrador (DA‑S5‑3) | en un equipo con varias cuentas de Windows cada una tiene su copia y sus datos; instalar por equipo exige otra carpeta de datos (`{commonappdata}`) y permisos |
| RS5‑4 | Dependencias preinstaladas en capas al construir, sin entorno virtual (DA‑S5‑1, DA‑S5‑2) | si la capa `.pth` choca con la básica, el completo pasa a ser un Python con todo instalado (instalador más grande, una sola capa) |
| RS5‑5 | Límites: básico ≤ 150 MB, básico instalado ≤ 900 MB, completo ≤ 650 MB; `xgboost` fuera | si S3/S4 pesan más de lo estimado, `civil` y luego `anomalias` pasan a componentes opcionales |
| RS5‑6 | Un solo camino de migración (`upgrade head`) con base idempotente (DA‑S5‑4) | crear una base nueva tarda algo más que `create_all` + `stamp` |
| RS5‑7 | Vuelta atrás = restaurar el respaldo; sin `downgrade` para el usuario (DA‑S5‑6) | bajar de versión exige restaurar y perder lo hecho después del respaldo |
| RS5‑8 | Sin TLS en la red local en la 1.0.0 (responde RS3‑8): red apagada por defecto, regla limitada a la subred y al perfil Privado, aviso | las contraseñas viajan sin cifrar en la red de la oficina; TLS (proxy inverso local) queda para 1.x |
| RS5‑9 | El producto arranca en **modo entrega** (Investigación oculta) salvo que la configuración diga lo contrario | quien quiera escenarios, similares, simulador o visor debe activarlo en `silice.toml` |
| RS5‑10 | Instalador sin firma de código; se publica la huella SHA‑256 | SmartScreen avisa; un certificado de firma tiene costo anual |
| RS5‑11 | La red local se activa solo desde el equipo servidor con elevación, no desde el navegador | menos cómodo para un administrador remoto |
| RS5‑12 | Los `.bat`, el paquete portable y `requirements.txt` sin versionar no se incorporan; `COMPARTIR_ONLINE.bat` (túnel público) queda fuera de la 1.0.0 | si Eugenio necesita mostrar el sistema por internet antes de 2.x, se hace fuera del producto y sin datos reales |
| RS5‑13 | `v1.0-tesis` apunta al commit de `v1.0.0` (o de un `v1.0.x`), nunca a uno sin etiqueta SemVer; Med se mide con `v1.0.0-rc.N` | si el tutor exige congelar antes del instalador, `v1.0-tesis` iría a una 0.9.x y la tesis lo declara |
| RS5‑14 | El servidor es una ventana de consola minimizada (DA‑S5‑5) | una ventana más en la barra de tareas; un ícono en la bandeja sería más pulido |

---

## 15. Riesgos

| Riesgo | Mitigación |
|---|---|
| Ruedas que necesitan el redistribuible de Visual C++ (`msvcp140.dll`, típico de `torch`) y un Windows limpio no lo trae; el runner sí, y la prueba de humo no lo vería | prueba a mano en un equipo sin herramientas de desarrollo (S5‑5); si falla, se incluyen las DLL del redistribuible junto al Python (Microsoft permite redistribuirlas con la aplicación; a confirmar la licencia vigente) |
| La CI corre como administrador: no prueba la instalación sin permisos | prueba a mano en una cuenta estándar (Windows 11 Home permite crearla) |
| Antivirus o SmartScreen bloquean un instalador sin firma | huella publicada, manual; firma en 1.x si hace falta (RS5‑10) |
| El tamaño real con LZMA2 difiere de la estimación con xz | medido en S5‑3.4; recorte de RS5‑5 |
| Streamlit cambia opciones o ruta de salud; quedan paquetes viejos en `{app}`; una ruta no ASCII rompe algo | versión fijada en `uv.lock` y prueba de humo; `[InstallDelete]` (§5.4); espacios y `ñ` en la prueba |
| Concurrencia de SQLite con varios usuarios en la red local | un solo proceso servidor; SL‑E12 si aparece `database is locked` |
| Minutos de Windows de la CI en un repositorio privado | filtros por ruta; completo solo con etiqueta o a mano |
| Una conexión saliente por sockets directos que el proxy testigo no ve | `gatherUsageStats=false`, `HF_HUB_OFFLINE`, three.js local; revisión del encargo de seguridad; límite declarado |

---

## 16. Preguntas abiertas para Eugenio

1. ¿Se ratifica que Alembic entre con la revisión base de la **0.9.0** (RS5‑1), o se adelanta a la 0.6.0 para que
   S1–S4 puedan cambiar columnas?
2. ¿Instalación solo por usuario (RS5‑3), o también por equipo para oficinas con varias cuentas de Windows?
3. ¿Se acepta la red local **sin TLS** en la 1.0.0 (RS5‑8, responde RS3‑8)?
4. ¿Modo entrega por defecto en el producto (RS5‑9)?
5. ¿Se compra un certificado de firma de código o se acepta el aviso de SmartScreen (RS5‑10)?
6. ¿Quién publica el *release* con los instaladores (el controlador a mano o la CI con permiso de escritura)?
7. ¿Qué licencia lleva Sílice? El repositorio no tiene archivo `LICENSE` y un instalador que se entrega a empresas
   debe mostrar una (el asistente de Inno puede presentarla).
8. ¿Qué se hace con los `.bat`, el paquete portable y `requirements.txt` sin versionar (RS5‑12)?
9. ¿Hay un segundo equipo o máquina virtual para la prueba a mano en limpio? Windows 11 Home no trae Sandbox ni Hyper‑V.
10. ¿Se confirma que `v1.0-tesis` sea el mismo commit que `v1.0.0` y que Med se mida con el instalador rc (RS5‑13)?

---

## 17. Fuentes y verificación

**Verificado el 2026‑10‑11:** ayuda de Inno Setup (`PrivilegesRequired`, constantes, parámetros silenciosos de
instalación y desinstalación, `DiskSpanning`, `[Icons]`, español oficial) y sus versiones; README de
`actions/runner-images` (Windows 2022/2025); `uv 0.11.9 --help` y la distribución que instala (con
`EXTERNALLY-MANAGED`); Alembic 1.20.0 (lista de `MetaData`, modo *batch*, `create_all` + `stamp`,
`Config.attributes`); `netsh advfirewall`; Streamlit 1.62.0 en este equipo (§1.2); tamaños de §1.3. **A confirmar:**
lo marcado así en el texto, y los tamaños de S5‑0.3 y S5‑3.4.
