# Plan de construcción de Sílice 1.0.0 (el resto de S5)

> **Para quien ejecute (agentes):** SUB-SKILL REQUERIDA: `superpowers:subagent-driven-development`
> (un subagente por tarea con su ficha de rol `C:\Users\euger\.claude\agents\sf-*.md` y un revisor
> fresco por tarea). Los pasos usan casillas `- [ ]`. Cada tarea lleva su prueba primero, con el
> rojo observado (NORMAS §5). Las tareas marcadas **[HUMANO]** tienen un paso que ningún agente
> puede hacer: el agente prepara todo, se detiene y lo dice.

**Objetivo:** entregar la 1.0.0 «Sílice». Una persona sin permisos de administrador y sin internet
instala Sílice con un asistente de Windows, abre el acceso directo y entra al navegador; después
instala la versión siguiente y sus dos bases (instalación y casos) se respaldan, se migran y
recargan con el mismo informe. La red local y la API nacen apagadas. Cada instalador sale con un
`SHA256SUMS` firmado con la clave Ed25519 del proyecto, auditado con `pip-audit` y probado en un
runner de Windows con cortafuegos de salida y navegador sin interfaz. La versión se mide (RNF-19,
RNF-20), se documenta (manual de instalación) y se cierra con `v1.0.0-rc.N`, `v1.0.0` y
`v1.0-tesis`.

**Alcance:** todo S5 menos S5-1, que ya está en el plan de la 0.6.0 (`PLAN_SILICE_060.md`,
sección B): S5-0 (documentos y mediciones), S5-2 (operación, red local, API con clave, versión),
S5-3 (instalador), S5-4 (CI) y S5-5 (cierre). No toca `core/` (spec S5 §5.1; SL-E11 queda vacante).

**Arquitectura:** cinco fases con ramas cortas desde `origin/main`.
- **S5-0:** enmiendas de la ERS y compañía, `FASES["1.0.0"]` y `scripts/meta_silice_s5b.py`,
  medición del Python autónomo y de las capas, y la clave del proyecto con la firma de
  `SHA256SUMS`.
- **S5-2:** `operacion/` crece (`version`, `registro`, `config` con `silice.toml`, `red`,
  `lanzador`, `eventos_perdidos`, `ordenes_100`); `api/proteccion.py`; en `ui/`, three.js local,
  imports diferidos, «Acerca de», pestaña «Instalación» y `ui/cliente.py`.
- **S5-3:** `instalador/` (`manifiesto.toml`, `manifiesto.py`, `construir.py`, `licencias.py`,
  `silice.iss`) y `operacion/programa.py`.
- **S5-4:** `instalador/humo.ps1`, `navegador.py`, `proxy_testigo.py`, `verificar_bases.py`,
  `auditar.py`, `tamanos.py` y `.github/workflows/instalador.yml`.
- **S5-5:** meta completa, manuales, mediciones de RNF-19 y RNF-20, `publicar.py`, rc, Med y
  etiquetas.

**Tecnología:** Python 3.13 (3.13.13 en el instalador), `uv` 0.11.9, Inno Setup 6.7.x,
PowerShell 7 (`pwsh`) en el runner `windows-2025`, `cryptography` (Ed25519), `pip-audit`,
Playwright con Edge (solo en la CI), Streamlit 1.62, FastAPI y Uvicorn, `tomllib`.

**Specs:** maestro `docs/especificaciones/2026-10-11-silice-1.0.0-design.md` (§3, §4.7, §5, §6,
§10; P9 licencia propietaria, ya en `LICENSE`) y S5
`docs/especificaciones/2026-10-11-silice-s5-producto-instalador-design.md` (UC-24, RF-96…99,
RNF-19/20, §6.5, §7, §8, §9, §10, §11, §12, §13, §14, §16). El plan cita los specs por sección y
no los repite; quien ejecuta lee el plan y el spec. Precedente de formato: `PLAN_SILICE_060.md`.

---

## Lo que exige acción humana o dinero (leer antes de empezar)

Cada punto dice quién, el valor por defecto si Eugenio no decide y dónde aparece. Ningún secreto
entra a la CI sin una orden escrita de Eugenio; este plan no la da.

- **H1. La clave Ed25519 del proyecto.** La genera **Eugenio**, nunca un agente: la privada no va
  en el repositorio, ni en OneDrive, ni en la CI, y su contraseña se guarda en dos lugares.
  Aparece en T3 (paso 7) y T20.
- **H2. Certificado de firma de código** (costo anual). Decide Eugenio. Por defecto no se compra:
  SmartScreen avisa y `SHA256SUMS` va firmado (RS5-10). Aparece en T19 (manual).
- **H3. Un segundo equipo o máquina virtual para la prueba en limpio** (pregunta 9). Windows 11
  Home no trae Sandbox ni Hyper-V. Por defecto: una cuenta estándar nueva en el mismo equipo más
  el runner de la CI; el riesgo del redistribuible de Visual C++ queda abierto y declarado.
  Aparece en T20 (paso 8). Si Eugenio lo quiere cubierto, es un equipo prestado o una máquina
  virtual en la nube (costo por decidir).
- **H4. Quién publica el release y firma `SHA256SUMS`** (pregunta 6). Por defecto, el controlador
  a mano; la CI no escribe en el repositorio ni tiene la clave. Aparece en T20.
- **H5. Instalar Inno Setup 6.7.x** en el equipo de desarrollo (hoy no está en el `PATH`):
  `winget install --id JRSoftware.InnoSetup -e`. Sin costo. Aparece en T15 (paso 4).
- **H6. Instalar a mano en una cuenta estándar y sin internet; Med con las dos personas.**
  Procedimiento en la bitácora. Aparece en T20.
- **H7. Minutos de Windows de la CI** (en un repositorio privado cobran el doble que Linux). Por
  defecto: filtros por ruta y el completo solo con etiqueta o a mano. Aparece en T17.
- **H8. Ratificar RS5-3** (instalación por usuario), **RS5-9** (modo entrega) y **RS5-13**
  (`v1.0-tesis`). Rigen los valores por defecto del spec mientras tanto.
- **H9. Redistribuir los PDF de MaPreX** (pregunta 12). Por defecto no viajan. Aparece en T13.
- **H10. Si `ifctester` entra al instalador** (GPLv3 de `bcf-client`; lo resuelve S3-0). Por
  defecto queda fuera (extra `ifc`). Aparece en T13.

## Cómo se ejecuta

- Una tarea a la vez, cada una con su rol (`sf-ingeniero-*`) y un revisor fresco. Rojo observado,
  commit de la prueba, implementación, verde, commit (maestro §6.3; comprobación C3 de la meta).
  C3 mira el primer commit de cada archivo: la implementación de un par `ParTDD` es siempre un
  archivo **nuevo** de la tarea.
- `unset VIRTUAL_ENV; uv sync --all-extras` antes de pytest. `uv run pytest -q -W error`.
  `uv run ruff check <archivos tocados>` (nunca `ruff format .` en todo el repositorio). Antes de
  cada PR: `uv run python scripts/guardia_nucleo.py --base origin/main`.
- Nunca `pkill`, `taskkill` ni matar procesos ajenos desde un comando de este plan. Las pruebas que
  arrancan Sílice paran lo que arrancaron, con `operacion parar` o por el identificador que
  guardaron.
- Nadie toca `data/apu.db`, `data/casos/` ni `data/instalacion.db` reales; toda prueba usa
  `tmp_path` o la carpeta de datos temporal de `tests/conftest.py`.
- Cada commit termina con la línea de atribución vigente de la sesión:
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` (el plan de la 0.6.0 usa la de su
  fecha; ver «Discrepancias»).
- Los comandos `git` y `gh` con `rama:ruta` se ejecutan en Git Bash con `MSYS_NO_PATHCONV=1`.
- Cada PR agrega **una línea** a `CHANGELOG.md` bajo `## [Sin publicar]` (maestro §6.1, RV-2),
  con sus RF y, si las hay, sus revisiones de Alembic.

## Supuestos (interfaces de la 0.6.0 a la 0.9.0 que este plan consume)

Todo esto está escrito en otros planes y **todavía no existe en `main`** (hoy `main` está en
`b85ddf5`: T0 parcial). Cada supuesto tiene una prueba que lo fija o un paso «cotejar»; si al
ejecutar la firma real difiere, se ajusta el consumidor de este plan (no el productor) y se anota
en `docs/bitacora/2026-10-silice-100.md`.

De la 0.6.0 (secciones A, B y C del plan `PLAN_SILICE_060.md`):
- **A1.** `operacion.config`: `carpeta_datos(entorno=None)`, `carpeta_casos`, `ruta_instalacion`,
  `carpeta_respaldos`, `ruta_caso_por_defecto`, `RAIZ`, `DATOS_DESARROLLO`, `_valor`, `_ruta`;
  ninguna crea carpetas. Lo consume T5.
- **A2.** `operacion.base_datos`: `preparar_base(ruta, destino=Destino.CASO, *, entorno=None)`,
  `Destino`, `revision_head`, `leer_estado` (con `.existe`, `.tablas`, `.revision`),
  `listar_casos`, `resolver_caso`, `migrar_todo`, `respaldar_todo`, `restaurar_juego`,
  `adoptar_base`, `ErrorDeBase`. Lo consumen T7, T8, T10 y T12.
- **A3.** `operacion.respaldo.restaurar(...)` escribe `eventos_perdidos_<fecha>.json` con
  `{"juego", "fecha", "revisado": false, "eventos": [...]}`; la ficha lleva
  `bases[].{archivo, destino, sha256, revision_origen}`, `motivo` y `ultimo_evento_acceso`. Lo
  consume T10.
- **A4.** `operacion/__main__.py` con `_ORDENES: dict[str, Callable]`, los subparsers `ordenes` y
  `main(argv)`; órdenes `casos`, `revision`, `migrar`, `respaldar`, `restaurar`, `adoptar`.
  Lo consumen T3 y T8.
- **A5.** `tests/fixtures/bases_prueba.py`: `carpeta_version`, `ficha`, `nombres`, `copiar_base`,
  `diferencias_con_ficha(ruta, esperado)`; bases `tests/fixtures/bases/v0_5_0` … `v0_9_0` con su
  `ficha.json`. Lo consume T16.
- **A6.** `scripts/meta_silice.py`: `FASES`, `Parte`, `ParTDD`, `CifraDeTiempo`, `Comprobacion`,
  `Contexto`, `partes()` (descubre `scripts/meta_silice_<parte>.py`); `scripts/meta_alpha.Estado`.
  Lo consumen T1 y T18.
- **A7.** `tests/conftest.py`: `_guardia_de_red` (sesión, autouse), `_datos_de_silice_temporales`
  (autouse, fija `SILICE_DATOS`), `_instalacion_real_intacta`; `pytest_plugins = ["pytester"]`.
  Lo consumen T5 y T9.
- **A8.** `ui.entorno`: `VARIABLE_CASO = "SILICE_CASO"`, `VARIABLE_MODO_ENTREGA =
  "SILICE_MODO_ENTREGA"`, `leer_variable(entorno, nombre)`; `ui.caso.ruta_caso()`. Lo consume T7.
- **A9.** `CHANGELOG.md` con `## [Sin publicar]` y una sección por versión; la bitácora
  `docs/bitacora/2026-10-silice-060.md`; versiones 0.6.0 a 0.9.0 etiquetadas, cada una con su base
  de prueba. Lo consumen T1, T18 y T20.
- **A10.** `api/dependencias.py` abre el caso con `preparar_base` y lee `APU_BASE` como URL
  `sqlite:///…`. Lo consume T7.

De la 0.8.0 (S3) y la 0.9.0 (S4):
- **A11.** `seguridad.secretos.cifrar(secreto: bytes, contrasena: str, *, asociado: bytes) ->
  bytes` y `descifrar(sobre: bytes, contrasena: str, *, asociado: bytes) -> bytes` (Argon2id +
  AES-GCM; lanza `InvalidTag` si falla). Lo consume T3.
- **A12.** `seguridad.modelo.Base.metadata` con las tablas `usuario(id, login, activo, roles)`,
  `clave_empresa(id, huella, estado)`, `empresa_registrada(id, huella, estado)`,
  `clave_api(id, nombre, revocada)`, `evento_acceso(id, …)` y `codigo_instalacion`. Lo consume T10
  (una prueba compara los nombres contra el modelo real).
- **A13.** `api.seguridad.exigir_clave_api(request: Request) -> None`, cabecera
  `X-Silice-Clave: <identificador>.<secreto>`, lanza `HTTPException(401)`;
  `seguridad.claves_api.crear_clave(sesion, *, nombre, creada_por) -> (identificador, secreto)`;
  la ruta `/v1/auditorias`. Lo consume T9 (solo `tests/fixtures/claves_api.py` conoce la forma).
- **A14.** `seguridad.red.es_local(ip: str) -> bool` (solo bucle local); S3 escribe
  `datos/codigo_instalacion.txt` al crear `instalacion.db`. Lo consumen T6, T7 y T10.
- **A15.** `ui/paginas/administracion.py` arma sus pestañas desde la constante
  `PESTANAS: tuple[tuple[str, Callable[[], None]], ...]`. Lo consume T12.
- **A16.** `st.context.ip_address` existe en Streamlit 1.62 (S3-0 lo confirma); si no, `ui.cliente`
  trata al cliente como remoto salvo con la red apagada. Lo consume T10.
- **A17.** `asistente/` y el extra `ia` (`anthropic`, `ollama`, `keyring`); el modo nube nace
  apagado; `tests/fixtures/bases/v0_9_0`. Lo consumen T13 y T16.
- **A18.** `scripts/descargar_modelo.py`; `ml.normalization.MODELO_POR_DEFECTO`. Lo consume T14.
- **A19.** `.gitignore` ya ignora `*.db`, `data/casos/`, `data/respaldos/`, `data/instalacion.db`,
  `codigo_instalacion.txt` y `paquetes/`. Lo consume T5.
- **A20.** `ui.texto_seguro.texto_seguro(texto: str) -> str` (S3). Lo consume T12.

## Rulings del orquestador sobre este plan (2026-10-11)

Todos tienen un valor por defecto; los que dependen de Eugenio llevan **[Eugenio]**.

- **RP10-1:** una rama corta por entrega, desde `origin/main` del momento, un PR por rama,
  fusión con `gh pr merge <n> --merge`. Nada se apila. GS5-0, GS5-2, GS5-3 y GS5-4 se cruzan al
  fusionar la última rama de su fase; GS5 (1.0.0) al etiquetar.
- **RP10-2 [Eugenio]:** sin certificado de firma de código; SmartScreen avisa y el manual lo
  explica (RS5-10, H2). Cambiarlo no toca este plan salvo un paso nuevo en `construir.py`.
- **RP10-3 [Eugenio]:** el par Ed25519 del proyecto lo genera Eugenio con
  `python -m operacion generar-clave-proyecto` fuera del repositorio y de OneDrive; el repositorio
  solo guarda la pública (`operacion/clave_proyecto.pub`). La CI publica `SHA256SUMS` sin firmar
  y el controlador firma en su equipo (H1, H4).
- **RP10-4:** `ifctester` queda fuera del instalador mientras S3-0 no resuelva la GPLv3 de
  `bcf-client` (extra `ifc`, no `civil`; el spec S5 §7.2 decía «`civil` con `ifctester`»). El
  manifiesto lo apaga con `ifc = false`; encenderlo es un ruling y un cambio de una línea (H10).
- **RP10-5:** three.js (r128, MIT, 603 445 bytes, SHA-256
  `9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2`, verificado el 2026-10-11 en
  cdnjs) va **incrustado** en el HTML del visor, no servido por una ruta estática. Así no hace
  falta `server.enableStaticServing` ni otra opción fuera de §10.1.
- **RP10-6:** 1 MB = 1 000 000 de bytes para RNF-19 (límites 150 MB y 650 MB). Es la lectura que
  da menos margen.
- **RP10-7:** las banderas de Python del lanzador y de los accesos directos son
  `-E -s -B -X utf8` (el spec §5.4 dice `-E -s -B`): `-E` ignora `PYTHONUTF8`, y sin UTF-8 una
  ruta con `ñ` rompe la salida de consola.
- **RP10-8:** `operacion.red.es_cliente_local(ip, direccion)` manda sobre `seguridad.red.es_local`:
  con la red local encendida, el navegador del propio servidor llega por la IP elegida y es
  local. Los sitios de llamada de S3 pasan a `ui.cliente` (T10).
- **RP10-9:** el `SHA256SUMS` del release es **uno solo**, armado por el controlador con
  `instalador/publicar.py` a partir de los artefactos de ambos perfiles. La CI solo deja
  `SHA256SUMS-<perfil>`.
- **RP10-10:** quien instala por primera vez no tiene Sílice para comprobar la firma: el release
  incluye `verificar_sumas.py` (biblioteca estándar + `cryptography`) y el manual indica
  `uv run --with cryptography verificar_sumas.py … --publica <hex>`. Es un límite declarado.
- **RP10-11:** `instalador.yml` usa solo `contents: read` y ningún `secrets.*`; sus artefactos
  son `instalador-<perfil>`, `tamanos-<perfil>`, `pip-audit-<perfil>` y `humo-<perfil>`.
- **RP10-12:** la meta de la 1.0.0 se evalúa dos veces: la CI hasta `S5-4` (sin lo que exige la
  máquina de Eugenio) y el controlador en local hasta `S5-5` en la compuerta GS5.
- **RP10-13:** si hay cambios de código después de una `v1.0.0-rc.N` medida, sale otra rc y se
  decide en la bitácora si se vuelve a medir (spec §9.3). `v1.0.0` es la rc medida con solo la
  versión, el candado, el CHANGELOG y los documentos cambiados.
- **RP10-14:** el disparo por etiqueta de `instalador.yml` se estrena con `v1.0.0-rc.1`: una
  etiqueta de prueba tendría que coincidir con `pyproject.toml`. GS5-4 se cruza con un PR verde y
  un `workflow_dispatch` verde con los dos perfiles.

## Orden y ramas

| Orden | Rama | Tareas | Condición |
|---|---|---|---|
| 1 | `inc/100-s5-0-docs` | T1–T2 (GS5-0) | 0.9.0 etiquetada y fusionada |
| 2 | `inc/100-clave-proyecto` | T3 | T1 fusionada |
| 3 | `inc/100-s5-2-operacion` | T4–T6 | T1 fusionada |
| 4 | `inc/100-s5-2-lanzador` | T7–T8 | T4–T6 fusionadas |
| 4′ | `inc/100-s5-2-api` (paralela) | T9 | T4 fusionada |
| 5 | `inc/100-s5-2-ui` | T10–T12 (GS5-2) | T6, T8 y T9 fusionadas |
| 6 | `inc/100-s5-3-manifiesto` | T13 | GS5-2 cruzada |
| 7 | `inc/100-s5-3-instalador` | T14–T15 (GS5-3) | T3 y T13 fusionadas |
| 8 | `inc/100-s5-4-humo` | T16 | GS5-3 cruzada |
| 9 | `inc/100-s5-4-flujo` | T17 (GS5-4) | T16 fusionada |
| 10 | `inc/100-s5-5-meta` | T18 | GS5-4 cruzada |
| 11 | `inc/100-s5-5-manuales` | T19 | T18 fusionada |
| 12 | `inc/100-s5-5-cierre` | T20 → rc, `v1.0.0`, `v1.0-tesis` | todo fusionado |

Ninguna rama toca `core/` ni `core/contracts/`; todas pasan `scripts/guardia_nucleo.py`. T3 y T14
usan `operacion/firma_sumas.py` y `seguridad.secretos`, que ya existen desde la 0.8.0.

## Mapa de tareas

- **T1** `FASES["1.0.0"]`, `meta_silice_s5b.py` (S5-0) y las enmiendas de ERS, arquitectura, plan
  de pruebas y calidad. Rol: sf-ingeniero-pruebas.
- **T2** `instalador/medir_capas.py` y la medición del Python 3.13 autónomo y de las capas.
  sf-ingeniero-pruebas.
- **T3** `operacion/firma_sumas.py`, `instalador/verificar_sumas.py` y la ceremonia de la clave
  **[HUMANO]**. sf-ingeniero-adaptadores.
- **T4** `operacion.version`, `operacion.registro`, `scripts/verificar_version.py` y la versión de
  la API. sf-ingeniero-adaptadores.
- **T5** `operacion.config`: producto, `silice.toml` y rutas de usuario. sf-ingeniero-adaptadores.
- **T6** `operacion.red`: interfaces, reglas `netsh`, cliente local, túneles y UNC.
  sf-ingeniero-adaptadores.
- **T7** `operacion.lanzador`: opciones fijas, arrancar, parar y una sola instancia.
  sf-ingeniero-adaptadores.
- **T8** `operacion.ordenes_100`: la CLI de la 1.0.0 y la guardia de `restaurar`.
  sf-ingeniero-adaptadores.
- **T9** `api/proteccion.py` y `api/main.py`: clave en todo, hosts, redes privadas y `/salud`.
  sf-ingeniero-adaptadores.
- **T10** `operacion.eventos_perdidos` y `ui/cliente.py` (SEG-12 completo). sf-ingeniero-interfaz.
- **T11** three.js local, imports diferidos de `scripts.*` y mensaje de la similitud.
  sf-ingeniero-interfaz.
- **T12** «Acerca de», pestaña «Instalación» y aviso «sin cifrar». sf-ingeniero-interfaz.
- **T13** `instalador/manifiesto.toml`, `manifiesto.py`, `operacion/programa.py` y
  `test_manifiesto`. sf-ingeniero-adaptadores.
- **T14** `instalador/construir.py`, `licencias.py` y `tamanos.py`. sf-ingeniero-adaptadores.
- **T15** `instalador/silice.iss`, su prueba estática y la compilación local **[HUMANO: Inno]**.
  sf-ingeniero-adaptadores.
- **T16** `humo.ps1`, `navegador.py`, `proxy_testigo.py` y `verificar_bases.py`.
  sf-ingeniero-pruebas.
- **T17** `instalador.yml`, `auditar.py` y su prueba. sf-ingeniero-pruebas.
- **T18** La parte S5 completa de la meta y el paso de la CI. sf-ingeniero-pruebas.
- **T19** Manuales, README, calidad, trazabilidad y `scripts/medir_arranque.py`.
  sf-ingeniero-pruebas.
- **T20** `publicar.py`, la candidata, Med, `v1.0.0` y `v1.0-tesis` **[HUMANO]**.
  sf-lider-de-fase.

Dentro de una rama las tareas van en el orden de la numeración; cada una consume firmas de las
anteriores (ver su «Interfaces»).

## Restricciones globales

- `core/` y `core/contracts/` no se tocan: `git diff origin/main --stat -- core/` vacío en cada
  rama.
- `operacion` no importa `streamlit`, `ui` ni `api`; `ui` y `api` importan de `operacion` todo
  **menos** `operacion.lanzador`, `operacion.ordenes_100` y `operacion.__main__` (la regla de
  la 0.6.0 se amplía en T10; spec S5 §5.2).
- Bloque de regresión literal intacto: `git diff v0.5.0..HEAD` vacío sobre `ARCHIVOS_REGRESION`.
- Ninguna prueba abre una conexión que no sea a `127.0.0.1` o `::1` (guardia de red). Las pruebas
  de red no ejecutan `netsh` ni PowerShell reales: reciben un ejecutor.
- Licencia propietaria (P9): `LICENSE` se muestra en el asistente; las de terceros van en
  `LICENCIAS\`.
- Los documentos anteriores al 2026-10-11 son historia y no se editan; los vivos (ERS, manuales,
  README, calidad, plan de pruebas) sí, con las enmiendas de este plan.

---

## S5-0 · Documentos y mediciones de la 1.0.0

### Tarea 1: apertura de la 1.0.0: fases, parte S5 de la meta y enmiendas de documentos

**Rama:** `inc/100-s5-0-docs` (sale de `origin/main` con la 0.9.0 etiquetada; PR a `main`; RV-2)
**Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `scripts/meta_silice_s5b.py`, `docs/bitacora/2026-10-silice-100.md`,
  `tests/unit/test_meta_silice_s5b.py`, `tests/unit/test_documentos_s5_100.py`
- Modificar: `scripts/meta_silice.py` (`FASES`, al final del diccionario);
  `tests/unit/test_meta_silice.py` (una prueba); `.github/workflows/ci.yml` (paso «Meta de
  Silice»); `docs/ERS.md`, `docs/arquitectura.md`, `docs/plan_pruebas.md`,
  `docs/calidad_iso25010.md`; `CHANGELOG.md` (una línea)

**Interfaces:**
- Consume: `scripts.meta_silice` (A6): `FASES`, `Parte`, `ParTDD`, `Comprobacion`, `Contexto`,
  `partes()`, `validar_partes`, `fases_hasta`; `scripts.meta_sf._patron_definicion`;
  `scripts.meta_alpha.Estado`.
- Produce: `FASES["1.0.0"] = ("S5-0", "S5-2", "S5-3", "S5-4", "S5-5")`; `scripts.meta_silice_s5b`:
  `REQUISITOS_S5_0 = ("UC-24", "RF-97", "RF-98", "RF-99", "RNF-19")`, `FRASES_RNF08`,
  `evaluar_ers_final(ers: str | None, calidad: str | None) -> tuple[Estado, str]`, `PARES_S5B`,
  `PARTE` (la T18 la completa). Las enmiendas de la ERS, la arquitectura, el plan de pruebas y la
  calidad que enumera S5-0.1 y S5-0.4.

- [ ] **Paso 1: Escribir la prueba que falla**

Agregar a `tests/unit/test_meta_silice.py`:
```python
def test_la_1_0_0_acumula_todas_las_versiones_y_termina_en_s5_5() -> None:
    fases = fases_hasta("1.0.0", "S5-5")
    assert fases[-5:] == ("S5-0", "S5-2", "S5-3", "S5-4", "S5-5")
    assert "S5-1" in fases and "S1-5" in fases  # lo de la 0.6.0 se evalúa también
    assert fases_hasta("1.0.0", "S5-0")[-1] == "S5-0"
    with pytest.raises(ValueError, match="fase desconocida"):
        fases_hasta("1.0.0", "S5-1")  # S5-1 es de la 0.6.0, no de la 1.0.0
```

`tests/unit/test_meta_silice_s5b.py`:
```python
"""Parte S5 de la 1.0.0 en la meta única (plan 1.0.0, tarea 1)."""

from __future__ import annotations

from pathlib import Path

from scripts import meta_silice_s5b as m
from scripts.meta_alpha import Estado
from scripts.meta_silice import FASES, partes, validar_partes

RAIZ = Path(__file__).resolve().parents[2]
ERS_OK = (
    "| Seguridad | RNF-08 ejecución local con dos excepciones declaradas: (1) el modelo, que el "
    "instalador completo trae incluido; (2) el asistente en modo nube. La excepción de three.js "
    "se retira | medición | meta |\n"
)
CALIDAD_OK = "## 6. Portabilidad (RNF-07 y RNF-19)\n"


def test_la_parte_se_descubre_y_solo_usa_fases_de_la_1_0_0() -> None:
    todas = partes()
    assert m.PARTE in todas
    validar_partes(todas)
    usadas = {c.fase for c in m.PARTE.comprobaciones} | set(m.PARTE.requisitos)
    assert usadas <= set(FASES["1.0.0"])


def test_los_requisitos_de_la_1_0_0_se_exigen_en_s5_0() -> None:
    assert m.PARTE.requisitos == {"S5-0": ("UC-24", "RF-97", "RF-98", "RF-99", "RNF-19")}


def test_s5_m1_acepta_la_redaccion_final_de_rnf_08_y_rnf_19_en_calidad() -> None:
    assert m.evaluar_ers_final(ERS_OK, CALIDAD_OK)[0] is Estado.OK


def test_s5_m1_falla_si_falta_una_excepcion_o_rnf_19() -> None:
    estado, detalle = m.evaluar_ers_final(ERS_OK.replace("modo nube", "la nube"), CALIDAD_OK)
    assert estado is Estado.FALLA and "modo nube" in detalle
    estado, detalle = m.evaluar_ers_final(ERS_OK, "## 6. Portabilidad (RNF-07)\n")
    assert estado is Estado.FALLA and "RNF-19" in detalle


def test_s5_m1_sin_documentos_es_pendiente() -> None:
    assert m.evaluar_ers_final(None, CALIDAD_OK)[0] is Estado.PENDIENTE
    assert m.evaluar_ers_final(ERS_OK, None)[0] is Estado.PENDIENTE


def test_s5_m1_acepta_el_guion_no_separable_de_los_documentos() -> None:
    assert m.evaluar_ers_final(ERS_OK, CALIDAD_OK.replace("RNF-19", "RNF‑19"))[0] is Estado.OK


def test_los_pares_tdd_incluyen_los_de_s5_0_sobre_archivos_nuevos() -> None:
    assert "S5-0" in {p.fase for p in m.PARES_S5B}
    assert ("tests/unit/test_meta_silice_s5b.py", "scripts/meta_silice_s5b.py") in {
        (p.prueba, p.implementacion) for p in m.PARES_S5B
    }


def test_la_ers_y_la_calidad_reales_pasan_s5_m1() -> None:
    ers = (RAIZ / "docs" / "ERS.md").read_text(encoding="utf-8")
    calidad = (RAIZ / "docs" / "calidad_iso25010.md").read_text(encoding="utf-8")
    estado, detalle = m.evaluar_ers_final(ers, calidad)
    assert estado is Estado.OK, detalle
```

`tests/unit/test_documentos_s5_100.py`:
```python
"""Enmiendas de la 1.0.0 en los documentos vivos (S5-0.1; spec S5 §4, §10.3 y §13)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.meta_sf import _patron_definicion

RAIZ = Path(__file__).resolve().parents[2]


def _leer(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8").replace("‑", "-")


@pytest.mark.parametrize(
    ("prefijo", "numero"), [("UC", 24), ("RF", 97), ("RF", 98), ("RF", 99), ("RNF", 19)]
)
def test_la_ers_define_los_numeros_de_la_1_0_0(prefijo: str, numero: int) -> None:
    assert re.search(_patron_definicion(prefijo, numero), _leer("docs/ERS.md"), re.MULTILINE)


def test_uc_24_trae_sus_flujos_alternativos_y_postcondiciones() -> None:
    uc = _leer("docs/ERS.md").split("#### UC-24", 1)[1].split("\n### ", 1)[0]
    for marca in ("Flujo principal", "Flujos alternativos", "Postcondiciones", "3f.", "7b.", "8a."):
        assert marca in uc, marca


def test_rnf_08_queda_con_la_redaccion_final() -> None:
    fila = next(
        linea
        for linea in _leer("docs/ERS.md").splitlines()
        if re.match(r"^\|[^|]*\|\s*RNF-08", linea)
    )
    for frase in ("dos excepciones declaradas", "modo nube", "three.js", "instalador completo"):
        assert frase in fila, frase


def test_rnf_07_aclara_el_camino_del_instalador() -> None:
    fila = next(
        linea
        for linea in _leer("docs/ERS.md").splitlines()
        if re.match(r"^\|[^|]*\|\s*RNF-07", linea)
    )
    assert "instalador" in fila and "uv sync" in fila


def test_la_ers_anota_la_enmienda_de_la_1_0_0() -> None:
    assert "Enmienda de Sílice 1.0.0" in _leer("docs/ERS.md")


def test_la_arquitectura_describe_el_producto_el_instalador_y_la_operacion() -> None:
    arquitectura = _leer("docs/arquitectura.md")
    assert "Enmienda de Sílice 1.0.0 (S5)" in arquitectura
    for pieza in (
        "operacion/",
        "instalador/",
        "%LOCALAPPDATA%\\Silice",
        "api/proteccion.py",
        "ui/cliente.py",
    ):
        assert pieza in arquitectura, pieza


def test_el_plan_de_pruebas_traza_rf_97_a_rf_99_y_rnf_19() -> None:
    plan = _leer("docs/plan_pruebas.md")
    seccion = plan.split("### 8.3", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
    for requisito in ("RF-97", "RF-98", "RF-99", "RNF-19", "RNF-20"):
        assert f"**{requisito}" in seccion, requisito
    assert re.search(r"\| RNF-19 [^|\n]*\|", plan.split("## 9.", 1)[1]), (
        "falta la fila de RNF-19 en §9"
    )


def test_la_calidad_declara_rnf_19_en_portabilidad() -> None:
    portabilidad = _leer("docs/calidad_iso25010.md").split("## 6.", 1)[1].split("## 7.", 1)[0]
    assert "RNF-19" in portabilidad and "instalador" in portabilidad


def test_la_bitacora_de_la_1_0_0_existe_con_los_rulings() -> None:
    bitacora = _leer("docs/bitacora/2026-10-silice-100.md")
    for ruling in ("RP10-1", "RP10-4", "RP10-9", "RP10-13"):
        assert ruling in bitacora, ruling
    assert "S5-0" in bitacora


def test_el_changelog_anota_la_apertura() -> None:
    assert "S5-0" in _leer("CHANGELOG.md").split("## [Sin publicar]", 1)[1].split("\n## [", 1)[0]
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `unset VIRTUAL_ENV; uv sync --all-extras; uv run pytest tests/unit/test_meta_silice.py
tests/unit/test_meta_silice_s5b.py tests/unit/test_documentos_s5_100.py -v -W error`
Esperado: FAIL con `ValueError: version desconocida: '1.0.0'`, `ImportError: cannot import name
'meta_silice_s5b' from 'scripts'` y `AssertionError` en la ERS (UC‑24, RF‑97…99, RNF‑19).
```bash
git add tests/unit/test_meta_silice.py tests/unit/test_meta_silice_s5b.py \
  tests/unit/test_documentos_s5_100.py
git commit -m "test(scripts): fases de la 1.0.0, meta S5 y enmiendas de documentos (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`scripts/meta_silice.py`, al final del diccionario `FASES` (después de la entrada de la 0.9.0):
```python
    "1.0.0": ("S5-0", "S5-2", "S5-3", "S5-4", "S5-5"),
```
`scripts/meta_silice_s5b.py`:
```python
"""Parte S5 de la 1.0.0 de la meta única (spec S5 §12 y §13; plan 1.0.0, tareas 1 y 18).

`scripts/meta_silice.py` la descubre por su nombre. Con `--version 1.0.0 --hasta S5-0` exige que la
ERS defina UC-24, RF-97 a RF-99 y RNF-19 (por presencia), que RNF-08 tenga su redacción final
(S5-M1) y que la prueba de cada pieza de S5-0 sea anterior a su código. La Tarea 18 le agrega las
comprobaciones de S5-2 a S5-5 (versión, flujo, tamaños, arranque, pip-audit, clave y etiquetas).
S5-1 (RF-96, RNF-20) es de la 0.6.0 y vive en `scripts/meta_silice_s5.py`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_silice import Comprobacion, Contexto, ParTDD, Parte  # noqa: E402

REQUISITOS_S5_0 = ("UC-24", "RF-97", "RF-98", "RF-99", "RNF-19")
#: La redacción final de RNF-08 (spec S5 §10.3, RV-23): las dos excepciones y lo que se retira.
FRASES_RNF08 = ("dos excepciones declaradas", "modo nube", "three.js", "instalador completo")
RUTA_ERS = RAIZ / "docs" / "ERS.md"
RUTA_CALIDAD = RAIZ / "docs" / "calidad_iso25010.md"

PARES_S5B: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_meta_silice_s5b.py", "scripts/meta_silice_s5b.py", "S5-0"),
    ParTDD("tests/unit/test_documentos_s5_100.py", "docs/bitacora/2026-10-silice-100.md", "S5-0"),
)


def _normal(texto: str) -> str:
    return texto.replace("‑", "-")


def evaluar_ers_final(ers: str | None, calidad: str | None) -> tuple[Estado, str]:
    """S5-M1: RNF-08 con su redacción final en la ERS y RNF-19 en la evaluación de calidad."""
    if ers is None or calidad is None:
        return Estado.PENDIENTE, "faltan docs/ERS.md o docs/calidad_iso25010.md"
    fila = next(
        (linea for linea in _normal(ers).splitlines() if re.match(r"^\|[^|]*\|\s*RNF-08", linea)),
        "",
    )
    faltan = [frase for frase in FRASES_RNF08 if frase not in fila]
    if "RNF-19" not in _normal(calidad):
        faltan.append("RNF-19 en docs/calidad_iso25010.md")
    if faltan:
        return Estado.FALLA, "falta: " + ", ".join(faltan)
    return Estado.OK, "RNF-08 con su redacción final y RNF-19 en la evaluación de calidad"


def _leer(ruta: Path) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else None


def _s5_m1(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_ers_final(_leer(RUTA_ERS), _leer(RUTA_CALIDAD))


PARTE = Parte(
    nombre="S5 resto (1.0.0)",
    requisitos={"S5-0": REQUISITOS_S5_0},
    pares_tdd=PARES_S5B,
    comprobaciones=(
        Comprobacion(
            "S5-M1", "ERS final: RNF-08 con dos excepciones y RNF-19 en calidad", "S5-0", _s5_m1
        ),
    ),
)
```
`.github/workflows/ci.yml`, paso «Meta de Silice»: `--version 1.0.0 --hasta S5-0`.
`CHANGELOG.md`, bajo `## [Sin publicar]`, una línea:
```markdown
- 1.0.0 · S5‑0: apertura (fases, parte S5 de la meta, enmiendas de ERS, arquitectura y calidad).
```

Enmiendas de los documentos, con un script de una sola vez (**no se versiona**; se guarda en el
directorio temporal de la sesión y se corre desde la raíz del repositorio). Los textos de UC‑24 y de
RF‑97 a RF‑99 salen **literales** del spec S5 (§4.1 y §4.2) y el de RNF‑08, de §10.3:
```python
"""Aplica las enmiendas de la 1.0.0 a los documentos (una vez). Falla si un ancla no está."""

import re
from pathlib import Path

SPEC = Path("docs/especificaciones/2026-10-11-silice-s5-producto-instalador-design.md").read_text(
    "utf-8"
)
ERS = Path("docs/ERS.md")
ers = ERS.read_text("utf-8")


def una_vez(texto: str, ancla: str, nuevo: str, *, antes: bool = True) -> str:
    assert texto.count(ancla) == 1, f"ancla ausente o repetida: {ancla!r}"
    return texto.replace(ancla, nuevo + ancla if antes else ancla + nuevo, 1)


# UC-24 (literal del spec §4.1) antes de «2.3 Características de los usuarios»
inicio = SPEC.index("#### UC‑24")
uc = SPEC[inicio : SPEC.index("UC existentes que se enmiendan", inicio)].rstrip() + "\n\n"
nota_uc = (
    "> **Enmienda a UC‑12 y UC‑21 (Sílice 1.0.0):** los recorridos de UC‑12 parten del acceso "
    "directo, no de la terminal; el primer administrador de UC‑21 se crea con el código de "
    "instalación que el arranque deja en la carpeta de datos (spec S5 §4.1 y §8.1).\n\n"
)
ers = una_vez(ers, "### 2.3 Características de los usuarios", uc + nota_uc)

# RF-97 a RF-99 (literal del spec §4.2) después de la fila de RF-96
filas = [linea for linea in SPEC.splitlines() if re.match(r"^\| RF‑9[789] \|", linea)]
assert len(filas) == 3


def fila_ers(linea: str) -> str:
    rf, req, uc_, pri, fase, criterio = (c.strip() for c in linea.strip().strip("|").split("|"))
    pri = pri.replace("E (básico); D (completo)", "Esencial (básico); Deseable (completo)")
    pri = {"E": "Esencial", "D": "Deseable"}.get(pri, pri)
    return f"| {rf} | {req} | {pri} | {uc_} | {fase} (1.0.0) | {criterio} |"


linea96 = next(linea for linea in ers.splitlines() if linea.startswith("| RF‑96 |"))
ers = una_vez(
    ers, linea96 + "\n", "\n".join(fila_ers(linea) for linea in filas) + "\n", antes=False
)

# RNF-19, antes de la fila de RNF-20
rnf19 = (
    "| Portabilidad | RNF‑19 Instalabilidad: artefactos comprimidos (los `.exe`) del instalador "
    "básico ≤ 150 MB y del completo ≤ 650 MB (1 MB = 10⁶ bytes); instalado, el básico ≤ 900 MB. Se "
    "instala sin internet y sin administrador en Windows 10 22H2 y 11 x64, en una ruta con espacios"
    " y caracteres no ASCII. Del acceso directo a la salud 200: ≤ 60 s en la CI y ≤ 20 s en el "
    "equipo de desarrollo. Actualizar conserva el 100 % de los datos de las dos bases | tamaño de "
    "los artefactos de la CI (falla si se pasa); prueba de humo; arranque medido (mediana de cinco,"
    " con fecha y los cinco valores en plan_pruebas §10); instalación en una cuenta estándar, a "
    "mano | cumplir los tres límites |\n"
)
ers = una_vez(
    ers,
    next(linea for linea in ers.splitlines() if linea.startswith("| Mantenibilidad | RNF‑20")),
    rnf19,
)

# RNF-08 (redacción final, spec §10.3) y RNF-07 (aclaración)
bloque = SPEC[SPEC.index("> RNF‑08 ejecución local") :].split("\n\n", 1)[0]
texto08 = " ".join(linea.removeprefix("> ").strip() for linea in bloque.splitlines())
requisito, _, medicion = texto08.partition(" Medición: ")
linea08 = next(linea for linea in ers.splitlines() if re.match(r"^\|[^|]*\|\s*RNF‑08", linea))
celdas = [c.strip() for c in linea08.strip().strip("|").split("|")]
assert len(celdas) == 4, celdas
ers = ers.replace(linea08, f"| {celdas[0]} | {requisito} | Medición: {medicion} | {celdas[3]} |", 1)
linea07 = next(linea for linea in ers.splitlines() if re.match(r"^\|[^|]*\|\s*RNF‑07", linea))
celdas = [c.strip() for c in linea07.strip().strip("|").split("|")]
extra = (
    " Desde la 1.0.0 el camino de usuario es el instalador de Windows (RF‑97); `uv sync` sigue "
    "siendo el camino de desarrollo y el de Linux."
)
ers = ers.replace(linea07, f"| {celdas[0]} | {celdas[1]}{extra} | {celdas[2]} | {celdas[3]} |", 1)

# Nota de enmienda al principio
nota = (
    "> **Enmienda de Sílice 1.0.0 (S5‑0; spec S5 §4 y §10.3):** se agregan UC‑24, RF‑97 a RF‑99 y "
    "RNF‑19; RNF‑07 aclara que el instalador de Windows es el camino de usuario; RNF‑08 queda con "
    "su redacción final (dos excepciones declaradas y three.js incrustado). RF‑96 y RNF‑20 llegaron"
    " con la 0.6.0. Los conteos los calcula la meta (maestro §6.1).\n\n"
)
ers = una_vez(ers, "## 1. Introducción", nota)
ERS.write_text(ers, "utf-8")

# Arquitectura, al final
ARQ = Path("docs/arquitectura.md")
ARQ.write_text(
    ARQ.read_text("utf-8").rstrip()
    + """

## Enmienda de Sílice 1.0.0 (S5): producto, instalador y operación

Fuente: [spec S5](especificaciones/2026-10-11-silice-s5-producto-instalador-design.md) §5 a §11.
S5 no toca `core/` (NORMAS §2): lo que agrega vive fuera del núcleo y el núcleo no lo importa.

### Vista lógica y de desarrollo

- `operacion/` (sin Streamlit): `config` (carpetas de datos y `silice.toml`), `base_datos` y
  `respaldo` (0.6.0), `version`, `registro` (sin secretos), `red` (IP explícita, cortafuegos,
  «el propio equipo»), `lanzador` (arrancar y parar), `eventos_perdidos` (SEG‑12), `programa`
  (el manifiesto), `firma_sumas` (Ed25519 de `SHA256SUMS`) y `ordenes_100` con `__main__` (la CLI).
  Importa `core.catalog`, `migraciones`, SQLAlchemy y la biblioteca estándar. `ui` y `api`
  importan de él todo menos `lanzador`, `ordenes_100` y `__main__`.
- `api/proteccion.py`: clave en toda ruta menos `/salud`, hosts permitidos, filtro de redes
  privadas y documentación apagada en el producto. `ui/cliente.py`: «solo desde este equipo», la
  IP del cliente y el aviso «sin cifrar». `ui/paginas/acerca.py` e `instalacion.py`.
- `instalador/` (no viaja ni lo importa el producto): `manifiesto.toml` y `manifiesto.py` (lista
  blanca), `construir.py`, `silice.iss`, `humo.ps1`, `navegador.py`, `proxy_testigo.py`,
  `verificar_bases.py`, `auditar.py`, `tamanos.py`, `publicar.py` y `licencias.py`.

### Vista física

- `%LOCALAPPDATA%\\Programs\\Silice` (`{app}`: `python\\`, `modulos\\similitud\\`, `codigo\\`,
  `manifiesto.json`, `LICENCIAS\\`) se reemplaza entero al actualizar.
- `%LOCALAPPDATA%\\Silice` guarda `config\\silice.toml`, `datos\\` (`instalacion.db`, `casos\\`,
  `codigo_instalacion.txt`, `paquetes\\`), `respaldos\\`, `registros\\` y
  `estado\\servidor.json`; el desinstalador no lo toca. Límite declarado: `{app}` lo puede
  escribir cualquier proceso del usuario (instalación sin administrador, RS5‑3).

### Vista de procesos

`python.exe -E -s -B -X utf8 -m operacion arrancar`: una sola instancia (`servidor.json` y la
salud), `silice.toml`, `preparar_base` de la instalación y del caso, dirección (`127.0.0.1` o la IP
elegida si sigue existiendo), Streamlit (y Uvicorn si la API está activa) como hijos con las
opciones fijas de §10.1, espera de la salud (≤ 60 s) y navegador. Cerrar la ventana o `parar`
lo detiene todo.
Actualizar es ejecutar el instalador nuevo: detiene Sílice, borra `python\\`, `modulos\\` y
`codigo\\`, copia, y `operacion migrar` respalda y migra las dos bases con un solo juego.

### Decisiones

DA‑S5‑1 a DA‑S5‑8 del spec S5 §5.5 (dependencias preinstaladas en capas, sin entorno virtual,
instalación por usuario, un solo camino de migración, consola minimizada como servidor, red local en
IP explícita). Rulings de este plan: `docs/bitacora/2026-10-silice-100.md`.
""",
    "utf-8",
)

# Plan de pruebas: §8.3 antes de «9.»; fila de RNF-19 al final de la tabla de §9
PLAN = Path("docs/plan_pruebas.md")
plan = PLAN.read_text("utf-8")
seccion = (
    "### 8.3 Filas de Sílice 1.0.0 (S5): RF‑97 a RF‑99 y RNF‑19\n\n"
    "Fuente: [spec S5 §12](especificaciones/2026-10-11-silice-s5-producto-instalador-design.md). "
    "El commit de cada prueba va antes que el de su implementación, con el rojo observado. La meta "
    "(S5‑TRAZ) comprueba que cada prueba citada existe.\n\n"
    + Path("seccion_8_3.md").read_text("utf-8")
    + "\n"
)
plan = una_vez(plan, "## 9. Trazabilidad RNF", seccion)
lineas = plan.split("\n")
indice10 = next(i for i, linea in enumerate(lineas) if linea.startswith("## 10."))
ultima = max(i for i in range(indice10) if lineas[i].startswith("|"))
lineas.insert(ultima + 1, Path("fila_rnf19.md").read_text("utf-8").rstrip("\n"))
PLAN.write_text("\n".join(lineas), "utf-8")

# Calidad: RNF-19 en §6 (se completa con la medición en la Tarea 19)
CAL = Path("docs/calidad_iso25010.md")
cal = CAL.read_text("utf-8")
cal = cal.replace("## 6. Portabilidad (RNF‑07)", "## 6. Portabilidad (RNF‑07 y RNF‑19)", 1)
cal = una_vez(
    cal,
    "**Veredicto: cumple** (las dos plataformas declaradas, con evidencia automatizada en cada "
    "cambio).",
    "**RNF‑19 (1.0.0).** El camino de usuario pasa a ser el instalador de Windows: sin "
    "administrador ni internet, con Python propio, ≤ 150 MB el básico y ≤ 650 MB el completo, "
    "arranque a la salud 200 en ≤ 60 s en la CI y ≤ 20 s en el equipo de desarrollo, y "
    "actualización que conserva el 100 % de las dos bases. La evidencia la dan el flujo "
    "`instalador.yml` (tamaño y prueba de humo en cada versión) y la medición de [plan_pruebas.md "
    "§10](plan_pruebas.md); hasta que esa medición exista, este punto está **por medir**.\n\n",
)
CAL.write_text(cal, "utf-8")
```
El script lee dos fragmentos que se escriben junto a él: `seccion_8_3.md` (la lista) y
`fila_rnf19.md` (la fila de §9). Son:

`seccion_8_3.md`:
```markdown
- **RF‑97** (instalador). Por construir. (a)–(f) las cubre la prueba de humo `instalador/humo.ps1`
  en la CI; el resto:
  `tests/unit/test_manifiesto.py::test_el_cierre_de_importaciones_de_la_siembra_esta_completo`,
  `tests/unit/test_manifiesto.py::test_ui_y_api_se_importan_solo_con_el_arbol_del_manifiesto`,
  `tests/unit/test_manifiesto.py::test_un_unico_config_toml_y_es_el_oficial`,
  `tests/unit/test_manifiesto.py::test_nunca_viajan_fixtures_bcv_bases_ni_db`,
  `tests/unit/test_iss.py::test_el_iss_instala_por_usuario_y_con_el_appid_fijo`,
  `tests/unit/test_iss.py::test_el_iss_no_toca_la_carpeta_de_datos_ni_descarga_nada`,
  `tests/unit/test_construir.py::test_el_manifiesto_json_cubre_codigo_y_python`,
  `tests/unit/test_ui_similares_modulo.py::test_en_el_producto_nombra_el_modulo`.
- **RF‑98** (operación segura). Por construir. «0 conexiones salientes»: prueba de humo.
  `tests/unit/test_ajustes.py::test_los_valores_por_defecto_apagan_la_red_y_la_api`,
  `tests/unit/test_ajustes.py::test_un_archivo_danado_da_defectos_y_nunca_red_encendida`,
  `tests/unit/test_lanzador.py::test_ninguna_configuracion_produce_0_0_0_0`,
  `tests/unit/test_lanzador.py::test_las_opciones_fijas_van_en_la_orden_de_streamlit`,
  `tests/unit/test_lanzador.py::test_la_ip_elegida_se_usa_solo_si_sigue_existiendo`,
  `tests/integration/test_arranque_real.py::test_arranca_en_el_bucle_local_y_se_detiene`,
  `tests/unit/test_red.py::test_ordenes_netsh_exactas`,
  `tests/unit/test_red.py::test_es_cliente_local`,
  `tests/integration/test_api_clave.py::test_cada_ruta_menos_salud_da_401_sin_clave`,
  `tests/integration/test_api_clave.py::test_ip_publica_simulada_recibe_403`,
  `tests/integration/test_api_clave.py::test_un_host_ajeno_recibe_400`,
  `tests/unit/test_ui_cliente.py::test_una_operacion_sensible_se_rechaza_desde_una_ip_remota`,
  `tests/unit/test_ui_cliente.py::test_el_cliente_remoto_ve_el_aviso_sin_cifrar`,
  `tests/unit/test_registro.py::test_secretos_sembrados_no_llegan_al_archivo`,
  `tests/integration/test_restaurar_eventos.py::test_restaurar_lista_lo_perdido_y_bloquea`.
- **RF‑99** (versión). Por construir. `scripts/meta_silice_s5b.py` (S5‑M5):
  `tests/unit/test_version.py::test_la_version_de_la_api_es_la_de_pyproject`,
  `tests/unit/test_verificar_version.py::test_etiqueta_que_coincide`,
  `tests/unit/test_ui_acerca.py::test_la_pantalla_muestra_todo_sin_excepciones`.
- **RNF‑19** (instalabilidad). Por medir. Instalación en cuenta estándar a mano y prueba de humo:
  `tests/unit/test_tamanos.py::test_el_limite_es_exacto`,
  `tests/unit/test_medir_arranque.py::test_resumen_calcula_la_mediana_de_cinco`.
- **RNF‑20** (mantenibilidad, desde la 0.6.0). Cumple por la prueba de deriva de cada destino:
  `tests/integration/test_migraciones.py::test_head_en_vacio_es_igual_a_create_all`,
  `tests/integration/test_migraciones.py::test_la_autogeneracion_contra_head_no_propone_cambios`,
  `tests/integration/test_migraciones.py::test_cada_revision_baja_y_vuelve_a_subir`.
- **Firma de `SHA256SUMS`** (spec S5 §10.4). Por construir.
  `tests/unit/test_firma_sumas.py::test_la_firma_se_verifica_con_una_biblioteca_independiente`,
  `tests/unit/test_firma_sumas.py::test_la_firma_lleva_separacion_de_dominio`,
  `tests/unit/test_firma_sumas.py::test_sumas_con_crlf_no_verifican`,
  `tests/unit/test_firma_sumas.py::test_la_privada_se_guarda_cifrada_y_exige_la_contrasena`,
  `tests/unit/test_publicar.py::test_el_sha256sums_reunido_se_firma_y_verifica`.
```
`fila_rnf19.md`:
```markdown
| RNF‑19 | `tests/unit/test_tamanos.py::test_el_limite_es_exacto` y humo | por medir |
```
Correr el script, revisar el diff y borrar los tres archivos temporales. La bitácora
`docs/bitacora/2026-10-silice-100.md` se crea con los rulings del plan:
```markdown
# Bitácora de la 1.0.0 de Sílice

Plan: `PLAN_SILICE_100.md`. Specs: maestro y S5 del 2026‑10‑11. Una sección por tarea y por
compuerta.

## S5‑0 · T1 Apertura de la 1.0.0

- `FASES["1.0.0"] = (S5‑0, S5‑2, S5‑3, S5‑4, S5‑5)` y `scripts/meta_silice_s5b.py`.
- Enmiendas: ERS (UC‑24, RF‑97 a RF‑99, RNF‑19, RNF‑07, RNF‑08 final), arquitectura §8, plan de
  pruebas §8.3 y §9, calidad §6.

## Rulings del plan (2026‑10‑11)

| # | Ruling |
|---|---|
| RP10‑1 | una rama corta por entrega, un PR por rama, fusión con merge commit; nada se apila |
| RP10‑2 | sin certificado de firma de código; SmartScreen avisa (a ratificar por Eugenio) |
| RP10‑3 | la clave Ed25519 la genera Eugenio fuera del repositorio; el controlador firma a mano |
| RP10‑4 | `ifctester` fuera del instalador hasta que S3‑0 resuelva la GPLv3 de `bcf-client` |
| RP10‑5 | three.js r128 incrustado en el HTML del visor (SHA‑256 fijado) |
| RP10‑6 | 1 MB = 10⁶ bytes para los límites de RNF‑19 |
| RP10‑7 | banderas de Python `-E -s -B -X utf8` |
| RP10‑8 | `operacion.red.es_cliente_local` manda sobre `seguridad.red.es_local` |
| RP10‑9 | un solo `SHA256SUMS` por release, armado por el controlador |
| RP10‑10 | primera instalación: `verificar_sumas.py` con `uv run --with cryptography` |
| RP10‑11 | `instalador.yml` sin secretos y con `contents: read` |
| RP10‑12 | la meta se evalúa en la CI hasta S5‑4 y en local hasta S5‑5 |
| RP10‑13 | entre la rc medida y `v1.0.0` solo cambian versión, candado, CHANGELOG y documentos |
| RP10‑14 | el disparo por etiqueta del flujo se estrena con `v1.0.0-rc.1` |
```

- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_meta_silice.py tests/unit/test_meta_silice_s5b.py
tests/unit/test_documentos_s5_100.py tests/unit/test_meta_datos.py -v -W error && uv run python
scripts/meta_datos.py`
y `uv run ruff check scripts/meta_silice_s5b.py tests/unit/test_meta_silice_s5b.py
tests/unit/test_documentos_s5_100.py`.
Luego `uv run python scripts/meta_silice.py --version 1.0.0 --hasta S5-0 --junit
reporte-pruebas.xml`
(con el JUnit de la suite): C1 con los cinco números, C3 con los dos pares de esta tarea y `S5-M1`
en OK.

- [ ] **Paso 5: Commit**
```bash
git add scripts/meta_silice.py scripts/meta_silice_s5b.py .github/workflows/ci.yml docs CHANGELOG.md
git commit -m "docs(ers): apertura de la 1.0.0 con UC-24, RF-97 a RF-99 y RNF-19" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Tarea 2: medir el Python 3.13 autónomo y las capas (S5-0.3) con `instalador/medir_capas.py`

**Rama:** `inc/100-s5-0-docs`   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `instalador/__init__.py`, `instalador/medir_capas.py`;
  `docs/bitacora/2026-10-silice-100-capas.json`
- Modificar: `docs/bitacora/2026-10-silice-100.md` (tabla de §1.3 completada);
  `tests/unit/test_arquitectura.py:18` (`PAQUETES_FUERA_DEL_NUCLEO` suma `"instalador"`: la
  guardia exige que todo paquete nuevo de primer nivel conste allí); `pyproject.toml`
  (`known-first-party` suma `"instalador"`)
- Prueba: `tests/unit/test_medir_capas.py`

**Interfaces:**
- Consume: `uv` (0.11.9), internet y ~4 GB libres solo al correr la medición real.
- Produce, en `instalador.medir_capas`: `REQUISITO` (regex), `normalizar(nombre) -> str`,
  `paquetes_de(requisitos: str) -> dict[str, str]`, `capas_nuevas(exportaciones: Mapping[str, str])
  -> dict[str, set[str]]`, `tamano_de_dist_info(sitio: Path, dist_info: Path) -> int`,
  `estimar_xz(archivos: Iterable[Path]) -> int`, `decidir_recorte(python_mb, capas_mb,
  codigo_mb=7.0,
  limite=150.0) -> list[str]`, `tabla_markdown(datos) -> str`, `main(argv)`. `construir.py` (T14)
  importa de aquí `REQUISITO`, `normalizar` y `paquetes_de`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_medir_capas.py`:
```python
"""Medición del Python autónomo y de las capas (spec S5 §1.3 y S5-0.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from instalador import medir_capas as mc

BASE = "alfa==1.0\nBeta_Uno==2.0 ; sys_platform == 'win32'\n"
UI = BASE + "streamlit==1.62.0\nnumpy==2.3.0\n"
CIVIL = UI + "ifcopenshell==0.8.1\nshapely==2.1.0\n"
ANOMALIAS = CIVIL + "scikit-learn==1.7.0\nnumpy==2.3.0\n"


def test_normalizar_une_guiones_guiones_bajos_y_puntos() -> None:
    assert mc.normalizar("Beta_Uno") == mc.normalizar("beta-uno") == "beta-uno"
    assert mc.normalizar("Zope.Interface") == "zope-interface"


def test_paquetes_de_lee_nombre_y_version_y_salta_lo_demas() -> None:
    assert mc.paquetes_de(
        "# x\n-e .\nalfa==1.0\n    # via y\nBeta_Uno==2.0 ; python_version > '3'\n"
    ) == {
        "alfa": "1.0",
        "beta-uno": "2.0",
    }


def test_cada_capa_trae_solo_lo_que_las_anteriores_no_tenian() -> None:
    capas = mc.capas_nuevas({"base": BASE, "ui": UI, "civil": CIVIL, "anomalias": ANOMALIAS})
    assert capas["base"] == {"alfa", "beta-uno"}
    assert capas["ui"] == {"streamlit", "numpy"}
    assert capas["civil"] == {"ifcopenshell", "shapely"}
    assert capas["anomalias"] == {"scikit-learn"}  # numpy ya estaba en «ui»


def test_el_tamano_de_un_paquete_se_suma_desde_su_record(tmp_path: Path) -> None:
    sitio = tmp_path / "site-packages"
    (sitio / "alfa").mkdir(parents=True)
    (sitio / "alfa" / "__init__.py").write_bytes(b"x" * 100)
    (sitio / "alfa" / "datos.bin").write_bytes(b"y" * 300)
    info = sitio / "alfa-1.0.dist-info"
    info.mkdir()
    (info / "RECORD").write_text(
        "alfa/__init__.py,sha256=abc,100\nalfa/datos.bin,sha256=def,300\n"
        "alfa-1.0.dist-info/RECORD,,\n../../Scripts/alfa.exe,,\n",
        encoding="utf-8",
    )
    (info / "METADATA").write_text("Name: alfa\n", encoding="utf-8")
    assert mc.tamano_de_dist_info(sitio, info) == 400  # ni RECORD ni lo que sale de site-packages


def test_estimar_xz_comprime_lo_repetitivo_y_no_inventa_bytes(tmp_path: Path) -> None:
    repetitivo = tmp_path / "a.txt"
    repetitivo.write_bytes(b"silice " * 20000)
    aleatorio = tmp_path / "b.bin"
    aleatorio.write_bytes(__import__("os").urandom(20000))
    solo_repetitivo = mc.estimar_xz([repetitivo])
    assert 0 < solo_repetitivo < repetitivo.stat().st_size // 20
    assert mc.estimar_xz([aleatorio]) > aleatorio.stat().st_size * 0.9
    assert mc.estimar_xz([]) > 0  # el contenedor vacío también ocupa algo


@pytest.mark.parametrize(
    ("python_mb", "capas", "esperado"),
    [
        (20.0, {"basica": 65, "bcv": 1, "civil": 16, "anomalias": 26, "ia": 12}, []),  # 147
        (
            20.0,
            {"basica": 80, "bcv": 1, "civil": 16, "anomalias": 26, "ia": 12},
            ["civil"],
        ),  # 162-16
        (
            20.0,
            {"basica": 95, "bcv": 1, "civil": 16, "anomalias": 26, "ia": 12},
            ["civil", "anomalias"],  # 177-16-26
        ),
    ],
)
def test_el_recorte_sigue_el_orden_del_spec_primero_civil_y_luego_anomalias(
    python_mb: float, capas: dict[str, float], esperado: list[str]
) -> None:
    assert mc.decidir_recorte(python_mb, capas) == esperado


def test_si_ni_recortando_cabe_se_dice() -> None:
    capas = {"basica": 150, "bcv": 1, "civil": 16, "anomalias": 26, "ia": 12}
    with pytest.raises(ValueError, match="150"):
        mc.decidir_recorte(20.0, capas)


def test_la_tabla_para_la_bitacora_trae_cada_capa_y_el_total() -> None:
    datos = {
        "python": {"instalado_mb": 70.0, "comprimido_mb": 15.0},
        "capas": {
            "basica": {"paquetes": 120, "instalado_mb": 348.0, "comprimido_mb": 62.0},
            "civil": {"paquetes": 3, "instalado_mb": 87.0, "comprimido_mb": 16.0},
        },
        "recorte": [],
    }
    tabla = mc.tabla_markdown(datos)
    assert (
        "| Python autónomo |" in tabla and "| basica | 120 |" in tabla and "| civil | 3 |" in tabla
    )
    assert "Total comprimido (estimado xz -9): 93,0 MB" in tabla and "Recorte: ninguno" in tabla
```

- [ ] **Paso 2: Correrla y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_medir_capas.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'instalador'`.
```bash
git add tests/unit/test_medir_capas.py
git commit -m "test(instalador): medicion de capas y decision de recorte (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`instalador/__init__.py` (T3 y T13 también escriben ahí):
```python
"""Herramientas de construcción del instalador de Windows (spec S5 §7). Nada de aquí viaja en el
producto ni se importa desde el código del producto (`tests/unit/test_manifiesto.py`)."""
```
`instalador/medir_capas.py`:
```python
"""Mide el Python autónomo y cada capa del instalador (spec S5 §1.3 y S5-0.3).

    uv run python instalador/medir_capas.py --tabla

Instala en una copia desechable del Python 3.13 de `uv` todo lo que el instalador completo llevaría
(capa por capa, desde `uv.lock`), suma el tamaño de cada paquete desde su `RECORD` y estima lo que
daría LZMA2 con `tar | xz -9`. Deja `docs/bitacora/2026-10-silice-100-capas.json` y, con `--tabla`,
el cuadro de §1.3 en Markdown. Necesita internet y unos 4 GB libres; no toca el repositorio.
"""

from __future__ import annotations

import argparse
import csv
import json
import lzma
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REQUISITO = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._\-]*)==([^\s;]+)")
MB = 1_000_000
LIMITE_BASICO_MB = 150.0
FIJAS = ("basica", "bcv", "civil", "anomalias", "ia")
ORDEN_DE_RECORTE = ("civil", "anomalias")
#: capa -> extras acumulados (el spec §7.2: «base + ui + api + planos + informes», luego cada extra)
CAPAS: dict[str, list[str]] = {
    "base": [],
    "basica": ["ui", "api", "planos", "informes"],
    "bcv": ["ui", "api", "planos", "informes", "bcv"],
    "civil": ["ui", "api", "planos", "informes", "bcv", "civil"],
    "anomalias": ["ui", "api", "planos", "informes", "bcv", "civil", "anomalias"],
    "ia": ["ui", "api", "planos", "informes", "bcv", "civil", "anomalias", "ia"],
    "similitud": [
        "ui",
        "api",
        "planos",
        "informes",
        "bcv",
        "civil",
        "anomalias",
        "ia",
        "similitud",
    ],
}


def normalizar(nombre: str) -> str:
    return re.sub(r"[-_.]+", "-", nombre).lower()


def paquetes_de(requisitos: str) -> dict[str, str]:
    encontrados = {}
    for linea in requisitos.splitlines():
        coincidencia = REQUISITO.match(linea.strip())
        if coincidencia:
            encontrados[normalizar(coincidencia.group(1))] = coincidencia.group(2)
    return encontrados


def capas_nuevas(exportaciones: Mapping[str, str]) -> dict[str, set[str]]:
    """Por capa (en el orden del diccionario), los paquetes que las anteriores no traían."""
    vistos: set[str] = set()
    capas = {}
    for capa, requisitos in exportaciones.items():
        nombres = set(paquetes_de(requisitos))
        capas[capa] = nombres - vistos
        vistos |= nombres
    return capas


def _archivos_de(sitio: Path, dist_info: Path) -> list[Path]:
    registro = dist_info / "RECORD"
    if not registro.is_file():
        return []
    archivos = []
    with registro.open(encoding="utf-8", newline="") as flujo:
        for fila in csv.reader(flujo):
            if not fila or fila[0].startswith(".."):
                continue
            ruta = sitio / fila[0]
            if ruta.is_file() and ruta.name != "RECORD":
                archivos.append(ruta)
    return archivos


def tamano_de_dist_info(sitio: Path, dist_info: Path) -> int:
    return sum(p.stat().st_size for p in _archivos_de(sitio, dist_info))


class _ContadorXz:
    def __init__(self) -> None:
        self._compresor = lzma.LZMACompressor(format=lzma.FORMAT_XZ, preset=9)
        self.total = 0

    def write(self, datos: bytes) -> int:
        self.total += len(self._compresor.compress(datos))
        return len(datos)

    def cerrar(self) -> int:
        self.total += len(self._compresor.flush())
        return self.total


def estimar_xz(archivos: Iterable[Path]) -> int:
    """Bytes que daría `tar | xz -9` de esos archivos (la estimación del spec §1.3)."""
    contador = _ContadorXz()
    with tarfile.open(fileobj=contador, mode="w|") as tar:  # type: ignore[arg-type]
        for archivo in archivos:
            tar.add(archivo, arcname=archivo.name, recursive=False)
    return contador.cerrar()


def decidir_recorte(
    python_mb: float,
    capas_mb: Mapping[str, float],
    codigo_mb: float = 7.0,
    limite: float = LIMITE_BASICO_MB,
) -> list[str]:
    """Qué capas pasarían a opcionales para que el básico quepa: primero `civil`, luego
    `anomalias` (spec S5 §7.2). `ValueError` si ni así cabe."""
    total = python_mb + codigo_mb + sum(capas_mb[c] for c in FIJAS)
    recortes: list[str] = []
    for capa in ORDEN_DE_RECORTE:
        if total <= limite:
            break
        total -= capas_mb[capa]
        recortes.append(capa)
    if total > limite:
        raise ValueError(
            f"ni recortando {', '.join(ORDEN_DE_RECORTE)} cabe en {limite:.0f} MB ({total:.1f})"
        )
    return recortes


def tabla_markdown(datos: Mapping) -> str:
    coma = lambda v: f"{v:.1f}".replace(".", ",")  # noqa: E731
    filas = [
        "| Capa | Paquetes | Instalado (MB) | Comprimido, xz ‑9 (MB) |",
        "|---|---|---|---|",
        f"| Python autónomo | — | {coma(datos['python']['instalado_mb'])} "
        f"| {coma(datos['python']['comprimido_mb'])} |",
    ]
    total = datos["python"]["comprimido_mb"]
    for capa, d in datos["capas"].items():
        filas.append(
            f"| {capa} | {d['paquetes']} | {coma(d['instalado_mb'])} | {coma(d['comprimido_mb'])} |"
        )
        total += d["comprimido_mb"]
    recorte = ", ".join(datos["recorte"]) or "ninguno"
    filas += ["", f"Total comprimido (estimado xz -9): {coma(total)} MB. Recorte: {recorte}."]
    return "\n".join(filas)


def _correr(orden: Sequence[str]) -> str:
    return subprocess.run(list(orden), capture_output=True, text=True, check=True, cwd=RAIZ).stdout


def medir(version_python: str) -> dict:
    with tempfile.TemporaryDirectory() as carpeta:
        base = Path(carpeta)
        _correr(["uv", "python", "install", version_python, "--install-dir", str(base / "py")])
        origen = next((base / "py").glob(f"cpython-{version_python}-*"))
        copia = base / "python"
        shutil.copytree(origen, copia)
        exe = copia / "python.exe" if sys.platform == "win32" else copia / "bin" / "python3"
        python_archivos = [p for p in copia.rglob("*") if p.is_file()]
        resultado: dict = {
            "python": {
                "version": version_python,
                "instalado_mb": sum(p.stat().st_size for p in python_archivos) / MB,
                "comprimido_mb": estimar_xz(python_archivos) / MB,
            },
            "capas": {},
        }
        exportaciones = {}
        for capa, extras in CAPAS.items():
            pares = [x for e in extras for x in ("--extra", e)]
            exportaciones[capa] = _correr(
                ["uv", "export", "--frozen", "--no-dev", "--no-emit-project", "--no-hashes", *pares]
            )
        completa = base / "req-completa.txt"
        completa.write_text(exportaciones["similitud"], encoding="utf-8")
        _correr(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(exe),
                "--break-system-packages",
                "--no-deps",
                "-r",
                str(completa),
            ]
        )
        sitio = next(copia.rglob("site-packages"))
        por_capa = capas_nuevas(exportaciones)
        for capa, nombres in por_capa.items():
            archivos: list[Path] = []
            for info in sitio.glob("*.dist-info"):
                if normalizar(info.name.rsplit("-", 1)[0]) in nombres:
                    archivos += _archivos_de(sitio, info)
            resultado["capas"][capa] = {
                "paquetes": len(nombres),
                "instalado_mb": sum(p.stat().st_size for p in archivos) / MB,
                "comprimido_mb": estimar_xz(archivos) / MB,
            }
    mb = {c: d["comprimido_mb"] for c, d in resultado["capas"].items()}
    mb["basica"] += mb["base"]  # la «básica» del spec es la base más ui, api, planos e informes
    resultado["recorte"] = decidir_recorte(resultado["python"]["comprimido_mb"], mb)
    return resultado


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--python", default="3.13.13")
    analizador.add_argument(
        "--salida", type=Path, default=RAIZ / "docs/bitacora/2026-10-silice-100-capas.json"
    )
    analizador.add_argument("--tabla", action="store_true")
    argumentos = analizador.parse_args(argv)
    datos = medir(argumentos.python)
    argumentos.salida.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(tabla_markdown(datos) if argumentos.tabla else json.dumps(datos, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
(`decidir_recorte` usa `capas_mb["basica"]` ya sumada con la base, de ahí `mb["basica"] +=
mb["base"]`;
si ni recortando cabe, `medir` falla con el mensaje y se decide con Eugenio, no en silencio.)

- [ ] **Paso 4: Correrla y ver el verde; medir de verdad [con internet]**
Run: `uv run pytest tests/unit/test_medir_capas.py -v -W error` y `uv run ruff check instalador
tests/unit/test_medir_capas.py`.

Medición real (una vez; ~20-40 min y ~4 GB; no es una prueba y no corre en la CI):
`uv run python instalador/medir_capas.py --tabla`. La tabla impresa se pega en
`docs/bitacora/2026-10-silice-100.md` bajo «S5‑0.3: tamaños medidos» y completa la fila «a medir en
S5‑0.3» del §1.3 del spec; si `recorte` no está vacío, **se registra un ruling `RP10-15`** (qué capa
pasa a opcional) y se avisa a Eugenio antes de seguir (el manifiesto y el `.iss` cambian). Si
`decidir_recorte` lanza `ValueError`, la tarea se detiene: ni `civil` ni `anomalias` alcanzan y hay
que decidir otro recorte con Eugenio.

- [ ] **Paso 5: Commit y PR (cierra `inc/100-s5-0-docs`, GS5-0)**
```bash
git add instalador/__init__.py instalador/medir_capas.py docs/bitacora \
  tests/unit/test_arquitectura.py pyproject.toml
git commit -m "feat(instalador): medir el Python autonomo y las capas, y decidir el recorte" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-0-docs
gh pr create --base main --head inc/100-s5-0-docs \
  --title "S5-0: documentos de la 1.0.0 y medicion de capas" --body-file -
```

### Compuerta GS5-0

- [ ] CI verde en Linux y Windows; 0 omitidas; `-W error`; ruff solo sobre lo tocado.
- [ ] `uv run python scripts/meta_silice.py --version 1.0.0 --hasta S5-0 --junit
  reporte-pruebas.xml`
  en OK; salida literal en la bitácora; el paso de la CI ya dice `--hasta S5-0`.
- [ ] ERS, arquitectura, plan de pruebas y calidad enmendados (T1) y **revisados por el encargo de
  requisitos y el verificador de hechos**; los números citados salen del spec, no de memoria.
- [ ] Tabla de §1.3 completada con la medición (T2) y, si hubo recorte, el ruling `RP10-15`
  anotado y avisado a Eugenio.
- [ ] Núcleo intacto (`git diff origin/main --stat -- core/` vacío) y regresión literal intacta.
- [ ] **S5‑0 queda completa solo cuando la Tarea 3 (otra rama) se fusiona** con la clave pública
  versionada por Eugenio: la meta de S5‑0 incluirá entonces sus pares de prueba y código.
- [ ] Pendiente de Eugenio, con su valor por defecto anotado: RS5‑3, RS5‑9, RS5‑13 y las preguntas
  2, 4, 5, 6, 9 y 10 del spec (H2, H3, H4, H8).

---

### Tarea 3: `operacion.firma_sumas`, `verificar_sumas.py` y la clave del proyecto **[HUMANO: H1]**

**Rama:** `inc/100-clave-proyecto` (sale de `origin/main` con T1 fusionada)
**Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `operacion/firma_sumas.py`, `operacion/ordenes_100.py`, `instalador/verificar_sumas.py`;
  `operacion/clave_proyecto.pub` (**solo la pública, y solo la hace Eugenio**)
- Modificar: `operacion/__main__.py` (registrar las órdenes de la 1.0.0, 3 líneas)
- Prueba: `tests/unit/test_firma_sumas.py`, `tests/unit/test_ordenes_clave.py`,
  `tests/unit/test_verificar_sumas_independiente.py`

**Interfaces:**
- Consume: `cryptography` (Ed25519); `seguridad.secretos.cifrar/descifrar` (A11: Argon2id +
  AES‑GCM, `InvalidTag` si falla).
- Produce, en `operacion.firma_sumas`: `DOMINIO = b"silice-sumas-v1\0"`, `RUTA_PUBLICA`,
  `generar_par() -> Ed25519PrivateKey`, `bytes_publicos(privada) -> bytes`,
  `huella(publica: bytes) -> str` (SHA‑256 en hex), `huella_agrupada(publica) -> str`,
  `formatear_sumas(entradas: Mapping[str, str]) -> bytes`, `parsear_sumas(datos: bytes) -> dict[str,
  str]`,
  `firmar(sumas: bytes, privada) -> bytes`, `verificar(sumas, firma, publica) -> bool`,
  `verificar_instalador(exe: Path, sumas: bytes, firma: bytes, publica: bytes) -> tuple[bool, str]`,
  `guardar_privada(privada, contrasena, ruta)`, `cargar_privada(ruta, contrasena)`,
  `leer_publica(ruta=RUTA_PUBLICA) -> bytes`. Órdenes: `generar-clave-proyecto --salida`,
  `firmar-sumas <sumas> --clave`, `verificar-instalador <exe> <sumas> <firma> [--publica HEX]`,
  `huella-clave-proyecto`. `ordenes_100.registrar(ordenes, tabla)`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_firma_sumas.py`:
```python
"""Firma Ed25519 de SHA256SUMS con la clave del proyecto (spec S5 §10.4; RV-16)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from operacion import firma_sumas as fs

CONTRASENA = "una contraseña larga y única 2026"


@pytest.fixture
def par():
    privada = fs.generar_par()
    return privada, fs.bytes_publicos(privada)


def test_la_firma_se_verifica_con_una_biblioteca_independiente(par) -> None:
    privada, publica = par
    sumas = fs.formatear_sumas({"Silice-1.0.0.exe": "ab" * 32})
    firma = fs.firmar(sumas, privada)
    assert len(firma) == 64
    # el oráculo no pasa por nuestro `verificar`: la propia biblioteca, con el prefijo a mano
    Ed25519PublicKey.from_public_bytes(publica).verify(firma, b"silice-sumas-v1\0" + sumas)


def test_la_firma_lleva_separacion_de_dominio(par) -> None:
    privada, publica = par
    sumas = fs.formatear_sumas({"Silice-1.0.0.exe": "ab" * 32})
    sin_prefijo = privada.sign(sumas)
    de_paquete = privada.sign(
        b"silice-paquete-v1\0" + sumas
    )  # el dominio del paquete auditado (S3)
    assert fs.verificar(sumas, sin_prefijo, publica) is False
    assert fs.verificar(sumas, de_paquete, publica) is False
    with pytest.raises(InvalidSignature):
        Ed25519PublicKey.from_public_bytes(publica).verify(
            sin_prefijo, b"silice-sumas-v1\0" + sumas
        )


def test_un_byte_cambiado_la_clave_equivocada_y_las_firmas_mal_formadas_no_verifican(par) -> None:
    privada, publica = par
    sumas = fs.formatear_sumas({"a.exe": "cd" * 32})
    firma = fs.firmar(sumas, privada)
    assert fs.verificar(sumas, firma, publica) is True
    assert fs.verificar(sumas[:-1] + b"X", firma, publica) is False
    assert fs.verificar(sumas, firma, fs.bytes_publicos(fs.generar_par())) is False
    for rota in (b"", firma[:63], firma + b"\0", b"x" * 64):
        assert fs.verificar(sumas, rota, publica) is False
    assert fs.verificar(sumas, firma, b"corta") is False  # una pública que no mide 32 bytes


def test_sumas_con_crlf_no_verifican(par) -> None:
    privada, publica = par
    sumas = fs.formatear_sumas({"a.exe": "cd" * 32, "b.exe": "ef" * 32})
    firma = fs.firmar(sumas, privada)
    assert fs.verificar(sumas.replace(b"\n", b"\r\n"), firma, publica) is False
    assert fs.verificar(b"\xef\xbb\xbf" + sumas, firma, publica) is False  # ni con BOM


def test_formatear_y_parsear_sumas_son_inversas_y_ordenan_por_nombre() -> None:
    entradas = {"z.exe": "11" * 32, "a.json": "22" * 32}
    crudo = fs.formatear_sumas(entradas)
    assert crudo == f"{'22' * 32}  a.json\n{'11' * 32}  z.exe\n".encode()
    assert fs.parsear_sumas(crudo) == entradas


def test_parsear_sumas_acepta_el_modo_binario_y_rechaza_lo_raro() -> None:
    ok = f"{'aa' * 32} *Silice.exe\n".encode()
    assert fs.parsear_sumas(ok) == {"Silice.exe": "aa" * 32}
    for malo in (
        b"no es una suma\n",
        f"{'AA' * 32}  mayusculas.exe\n".encode(),
        f"{'aa' * 32}  ../fuera.exe\n".encode(),
        f"{'aa' * 32}  a\\b.exe\n".encode(),
        f"{'aa' * 32}  a.exe\n{'bb' * 32}  a.exe\n".encode(),
        f"{'aa' * 32}  a.exe\r\n".encode(),
        f"{'aa' * 31}  corta.exe\n".encode(),
    ):
        with pytest.raises(ValueError):
            fs.parsear_sumas(malo)


def test_verificar_instalador_dice_la_causa(tmp_path: Path, par) -> None:
    privada, publica = par
    exe = tmp_path / "Silice-1.0.0.exe"
    exe.write_bytes(b"instalador")
    sumas = fs.formatear_sumas({exe.name: hashlib.sha256(b"instalador").hexdigest()})
    firma = fs.firmar(sumas, privada)
    ok, mensaje = fs.verificar_instalador(exe, sumas, firma, publica)
    assert ok is True and "VERIFICADO" in mensaje and fs.huella(publica) in mensaje

    exe.write_bytes(b"alterado")
    ok, mensaje = fs.verificar_instalador(exe, sumas, firma, publica)
    assert ok is False and "huella" in mensaje

    exe.write_bytes(b"instalador")
    otro = tmp_path / "Silice-9.9.9.exe"
    otro.write_bytes(b"x")
    assert "no figura" in fs.verificar_instalador(otro, sumas, firma, publica)[1]
    ok, mensaje = fs.verificar_instalador(exe, sumas, b"\0" * 64, publica)
    assert ok is False and "firma" in mensaje and "no instale" in mensaje
    ok, mensaje = fs.verificar_instalador(exe, b"basura", firma, publica)
    assert ok is False


def test_la_privada_se_guarda_cifrada_y_exige_la_contrasena(tmp_path: Path, par) -> None:
    privada, publica = par
    ruta = tmp_path / "clave_proyecto.enc"
    fs.guardar_privada(privada, CONTRASENA, ruta)
    crudo = ruta.read_bytes()
    semilla = privada.private_bytes_raw()
    assert semilla not in crudo and semilla.hex().encode() not in crudo
    datos = json.loads(crudo)
    assert datos["formato"] == "silice-clave-proyecto" and datos["publica"] == publica.hex()
    asimetrica = fs.cargar_privada(ruta, CONTRASENA)
    assert fs.bytes_publicos(asimetrica) == publica
    with pytest.raises(InvalidTag):
        fs.cargar_privada(ruta, "otra contraseña distinta 2026")


def test_una_contrasena_corta_se_rechaza(tmp_path: Path, par) -> None:
    with pytest.raises(ValueError, match="12"):
        fs.guardar_privada(par[0], "corta", tmp_path / "k.enc")


def test_la_clave_cifrada_no_se_puede_mover_a_otra_publica(tmp_path: Path, par) -> None:
    """El dato asociado liga el sobre a su clave pública: cambiar la pública a mano falla."""
    privada, _ = par
    ruta = tmp_path / "k.enc"
    fs.guardar_privada(privada, CONTRASENA, ruta)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["publica"] = fs.bytes_publicos(fs.generar_par()).hex()
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(InvalidTag):
        fs.cargar_privada(ruta, CONTRASENA)


def test_la_huella_es_el_sha256_de_la_clave_publica(par) -> None:
    _, publica = par
    assert fs.huella(publica) == hashlib.sha256(publica).hexdigest()
    agrupada = fs.huella_agrupada(publica)
    assert agrupada.replace(" ", "") == fs.huella(publica) and agrupada.count(" ") == 7


def test_leer_publica_acepta_hex_con_salto_de_linea_y_rechaza_lo_demas(tmp_path: Path, par) -> None:
    _, publica = par
    ruta = tmp_path / "clave_proyecto.pub"
    ruta.write_text(publica.hex() + "\n", encoding="utf-8")
    assert fs.leer_publica(ruta) == publica
    ruta.write_text("zz", encoding="utf-8")
    with pytest.raises(ValueError, match="clave pública"):
        fs.leer_publica(ruta)
    with pytest.raises(FileNotFoundError):
        fs.leer_publica(tmp_path / "no.pub")
```

`tests/unit/test_ordenes_clave.py`:
```python
"""Las órdenes de la clave del proyecto (spec S5 §10.4)."""

from __future__ import annotations

import getpass
import hashlib

import pytest

from operacion import __main__ as cli
from operacion import config
from operacion import firma_sumas as fs

CONTRASENA = "una contraseña larga y única 2026"


@pytest.fixture
def contrasena(monkeypatch):
    monkeypatch.setattr(getpass, "getpass", lambda texto="": CONTRASENA)


def test_generar_clave_proyecto_escribe_la_cifrada_y_la_publica(
    tmp_path, contrasena, capsys
) -> None:
    carpeta = tmp_path / "fuera" / ".silice-clave"
    assert cli.main(["generar-clave-proyecto", "--salida", str(carpeta)]) == 0
    publica = fs.leer_publica(carpeta / "clave_proyecto.pub")
    assert (
        fs.bytes_publicos(fs.cargar_privada(carpeta / "clave_proyecto.enc", CONTRASENA)) == publica
    )
    salida = capsys.readouterr().out
    assert (
        publica.hex() in salida
        and fs.huella(publica) in salida
        and "operacion/clave_proyecto.pub" in salida
    )


@pytest.mark.parametrize(("donde", "palabra"), [("repo", "repositorio"), ("onedrive", "OneDrive")])
def test_generar_rechaza_el_repositorio_y_onedrive(
    tmp_path, contrasena, capsys, donde, palabra
) -> None:
    malo = (
        config.RAIZ / "secretos_de_prueba"
        if donde == "repo"
        else tmp_path / "OneDrive - Personal" / "claves"
    )
    assert cli.main(["generar-clave-proyecto", "--salida", str(malo)]) == 1
    assert palabra in capsys.readouterr().err and not malo.exists()


def test_generar_no_pisa_una_clave_existente(tmp_path, contrasena) -> None:
    carpeta = tmp_path / "k"
    assert cli.main(["generar-clave-proyecto", "--salida", str(carpeta)]) == 0
    antes = (carpeta / "clave_proyecto.enc").read_bytes()
    assert cli.main(["generar-clave-proyecto", "--salida", str(carpeta)]) == 1
    assert (carpeta / "clave_proyecto.enc").read_bytes() == antes


def test_firmar_sumas_escribe_la_firma_y_la_comprueba_contra_la_publica_del_programa(
    tmp_path, contrasena, monkeypatch
) -> None:
    carpeta = tmp_path / "k"
    assert cli.main(["generar-clave-proyecto", "--salida", str(carpeta)]) == 0
    monkeypatch.setattr(fs, "RUTA_PUBLICA", carpeta / "clave_proyecto.pub")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(fs.formatear_sumas({"a.exe": "ab" * 32}))
    assert cli.main(["firmar-sumas", str(sumas), "--clave", str(carpeta)]) == 0
    firma = (tmp_path / "SHA256SUMS.ed25519").read_bytes()
    assert fs.verificar(sumas.read_bytes(), firma, fs.leer_publica(carpeta / "clave_proyecto.pub"))


def test_firmar_con_una_clave_que_no_es_la_del_programa_se_rechaza(
    tmp_path, contrasena, monkeypatch, capsys
) -> None:
    ajena, propia = tmp_path / "ajena", tmp_path / "propia"
    cli.main(["generar-clave-proyecto", "--salida", str(ajena)])
    cli.main(["generar-clave-proyecto", "--salida", str(propia)])
    monkeypatch.setattr(fs, "RUTA_PUBLICA", propia / "clave_proyecto.pub")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(fs.formatear_sumas({"a.exe": "ab" * 32}))
    assert cli.main(["firmar-sumas", str(sumas), "--clave", str(ajena)]) == 1
    assert not (tmp_path / "SHA256SUMS.ed25519").exists()
    assert "clave del proyecto" in capsys.readouterr().err


def test_firmar_con_la_contrasena_equivocada_no_deja_traza(tmp_path, monkeypatch, capsys) -> None:
    carpeta = tmp_path / "k"
    monkeypatch.setattr(getpass, "getpass", lambda texto="": CONTRASENA)
    cli.main(["generar-clave-proyecto", "--salida", str(carpeta)])
    monkeypatch.setattr(getpass, "getpass", lambda texto="": "otra contraseña distinta 2026")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(b"")
    assert cli.main(["firmar-sumas", str(sumas), "--clave", str(carpeta)]) == 1
    error = capsys.readouterr().err
    assert "contraseña" in error.lower() and "Traceback" not in error


def test_verificar_instalador_acepta_y_rechaza(tmp_path, contrasena, capsys) -> None:
    carpeta = tmp_path / "k"
    cli.main(["generar-clave-proyecto", "--salida", str(carpeta)])
    privada = fs.cargar_privada(carpeta / "clave_proyecto.enc", CONTRASENA)
    exe = tmp_path / "Silice-1.0.0.exe"
    exe.write_bytes(b"instalador")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(fs.formatear_sumas({exe.name: hashlib.sha256(b"instalador").hexdigest()}))
    (tmp_path / "SHA256SUMS.ed25519").write_bytes(fs.firmar(sumas.read_bytes(), privada))
    publica = fs.bytes_publicos(privada).hex()
    argumentos = [
        "verificar-instalador",
        str(exe),
        str(sumas),
        str(tmp_path / "SHA256SUMS.ed25519"),
        "--publica",
        publica,
    ]
    assert cli.main(argumentos) == 0 and "VERIFICADO" in capsys.readouterr().out
    exe.write_bytes(b"alterado")
    assert cli.main(argumentos) == 1 and "huella" in capsys.readouterr().err


def test_verificar_instalador_sin_clave_en_el_programa_lo_dice(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(fs, "RUTA_PUBLICA", tmp_path / "no_esta.pub")
    archivo = tmp_path / "x"
    archivo.write_bytes(b"x")
    assert cli.main(["verificar-instalador", str(archivo), str(archivo), str(archivo)]) == 1
    assert "clave del proyecto" in capsys.readouterr().err


def test_huella_clave_proyecto_imprime_el_sha256(tmp_path, monkeypatch, capsys) -> None:
    privada = fs.generar_par()
    ruta = tmp_path / "clave_proyecto.pub"
    ruta.write_text(fs.bytes_publicos(privada).hex() + "\n", encoding="utf-8")
    monkeypatch.setattr(fs, "RUTA_PUBLICA", ruta)
    assert cli.main(["huella-clave-proyecto"]) == 0
    assert fs.huella(fs.bytes_publicos(privada)) in capsys.readouterr().out
```
`tests/unit/test_verificar_sumas_independiente.py`:
```python
"""`instalador/verificar_sumas.py`: quien instala por primera vez no tiene Sílice (RP10-10)."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from operacion import firma_sumas as fs

SCRIPT = Path(__file__).resolve().parents[2] / "instalador" / "verificar_sumas.py"


def _preparar(tmp_path: Path):
    privada = fs.generar_par()
    exe = tmp_path / "Silice-1.0.0.exe"
    exe.write_bytes(b"instalador")
    sumas = tmp_path / "SHA256SUMS"
    sumas.write_bytes(fs.formatear_sumas({exe.name: hashlib.sha256(b"instalador").hexdigest()}))
    firma = tmp_path / "SHA256SUMS.ed25519"
    firma.write_bytes(fs.firmar(sumas.read_bytes(), privada))
    return exe, sumas, firma, fs.bytes_publicos(privada).hex()


def _correr(*argumentos: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *argumentos],
        capture_output=True,
        text=True,
        check=False,
    )


def test_el_script_independiente_verifica_con_la_clave_pasada_por_argumento(tmp_path: Path) -> None:
    exe, sumas, firma, publica = _preparar(tmp_path)
    resultado = _correr(str(exe), str(sumas), str(firma), "--publica", publica)
    assert resultado.returncode == 0 and "VERIFICADO" in resultado.stdout
    assert (
        hashlib.sha256(bytes.fromhex(publica)).hexdigest() in resultado.stdout
    )  # la huella a comparar


def test_el_script_independiente_rechaza_un_instalador_alterado_o_una_clave_ajena(
    tmp_path: Path,
) -> None:
    exe, sumas, firma, publica = _preparar(tmp_path)
    exe.write_bytes(b"alterado")
    assert _correr(str(exe), str(sumas), str(firma), "--publica", publica).returncode == 1
    exe.write_bytes(b"instalador")
    ajena = fs.bytes_publicos(fs.generar_par()).hex()
    resultado = _correr(str(exe), str(sumas), str(firma), "--publica", ajena)
    assert resultado.returncode == 1 and "NO INSTALE" in resultado.stderr


def test_el_script_independiente_no_importa_nada_de_silice() -> None:
    texto = SCRIPT.read_text(encoding="utf-8")
    assert "operacion" not in texto.replace("silice-sumas-v1", "")
    assert "import cryptography" in texto or "from cryptography" in texto
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_firma_sumas.py tests/unit/test_ordenes_clave.py
tests/unit/test_verificar_sumas_independiente.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'firma_sumas' from 'operacion'`.
```bash
git add tests/unit/test_firma_sumas.py tests/unit/test_ordenes_clave.py \
  tests/unit/test_verificar_sumas_independiente.py
git commit -m "test(operacion): firma de SHA256SUMS, ordenes de la clave y verificador (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/firma_sumas.py`:
```python
"""Firma Ed25519 de `SHA256SUMS` con la clave del proyecto (spec S5 §10.4; RV-16).

El instalador no lleva firma de código (RS5-10): lleva `SHA256SUMS` (huella de cada archivo del
release) y `SHA256SUMS.ed25519`, la firma de esos bytes exactos con la clave del proyecto, con
separación de dominio (`b"silice-sumas-v1\\0"`, como `silice-paquete-v1\\0` en S3: una firma de un
tipo no vale como la de otro). La privada vive cifrada (Argon2id + AES-GCM, `seguridad.secretos`)
fuera del repositorio y de la CI; el repositorio solo tiene la pública (`clave_proyecto.pub`).
No se programa criptografía propia: todo es `cryptography`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from operacion import config

DOMINIO = b"silice-sumas-v1\0"
ASOCIADO = b"silice-clave-proyecto-v1"
FORMATO_CLAVE = "silice-clave-proyecto"
MIN_CONTRASENA = 12
RUTA_PUBLICA = config.RAIZ / "operacion" / "clave_proyecto.pub"
_LINEA = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")


def generar_par() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def bytes_publicos(privada: Ed25519PrivateKey) -> bytes:
    return privada.public_key().public_bytes_raw()


def huella(publica: bytes) -> str:
    return hashlib.sha256(publica).hexdigest()


def huella_agrupada(publica: bytes) -> str:
    h = huella(publica)
    return " ".join(h[i : i + 8] for i in range(0, 64, 8))


def formatear_sumas(entradas: Mapping[str, str]) -> bytes:
    """Líneas `<sha256>  <nombre>` (formato de `sha256sum`), ordenadas por nombre, solo LF."""
    return "".join(f"{entradas[n]}  {n}\n" for n in sorted(entradas)).encode("utf-8")


def parsear_sumas(datos: bytes) -> dict[str, str]:
    if b"\r" in datos:
        raise ValueError(
            "SHA256SUMS tiene saltos de línea de Windows (CRLF): no es el archivo firmado"
        )
    entradas: dict[str, str] = {}
    for numero, linea in enumerate(datos.decode("utf-8").splitlines(), start=1):
        if not linea:
            continue
        coincidencia = _LINEA.match(linea)
        if coincidencia is None:
            raise ValueError(f"SHA256SUMS, línea {numero}: no tiene la forma «<sha256>  <nombre>»")
        huella_, nombre = coincidencia.groups()
        if "/" in nombre or "\\" in nombre or nombre in {".", ".."}:
            raise ValueError(f"SHA256SUMS, línea {numero}: nombre sospechoso {nombre!r}")
        if nombre in entradas:
            raise ValueError(f"SHA256SUMS, línea {numero}: {nombre!r} repetido")
        entradas[nombre] = huella_
    return entradas


def firmar(sumas: bytes, privada: Ed25519PrivateKey) -> bytes:
    return privada.sign(DOMINIO + sumas)


def verificar(sumas: bytes, firma: bytes, publica: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(publica).verify(firma, DOMINIO + sumas)
    except (InvalidSignature, ValueError):
        return False
    return True


def verificar_instalador(exe: Path, sumas: bytes, firma: bytes, publica: bytes) -> tuple[bool, str]:
    """Firma de `SHA256SUMS` y huella del instalador, con la causa de cada fallo."""
    if not verificar(sumas, firma, publica):
        return (
            False,
            "La firma de SHA256SUMS no es válida con la clave del proyecto: no instale este "
            "archivo.",
        )
    try:
        entradas = parsear_sumas(sumas)
    except ValueError as error:
        return False, f"SHA256SUMS no tiene el formato esperado: {error}"
    if exe.name not in entradas:
        return False, f"{exe.name} no figura en SHA256SUMS: no instale este archivo."
    if hashlib.sha256(exe.read_bytes()).hexdigest() != entradas[exe.name]:
        return (
            False,
            f"La huella de {exe.name} no coincide con SHA256SUMS: el archivo cambió. "
            "No lo instale.",
        )
    return True, (
        f"VERIFICADO: {exe.name} coincide con SHA256SUMS firmado por la clave del proyecto "
        f"(huella de la clave {huella(publica)})."
    )


def guardar_privada(privada: Ed25519PrivateKey, contrasena: str, ruta: Path) -> None:
    from seguridad import secretos

    if len(contrasena) < MIN_CONTRASENA:
        raise ValueError(
            f"la contraseña de la clave debe tener al menos {MIN_CONTRASENA} caracteres"
        )
    publica = bytes_publicos(privada).hex()
    sobre = secretos.cifrar(
        privada.private_bytes_raw(), contrasena, asociado=ASOCIADO + publica.encode()
    )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(
            {
                "formato": FORMATO_CLAVE,
                "version": 1,
                "publica": publica,
                "sobre": base64.b64encode(sobre).decode("ascii"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def cargar_privada(ruta: Path, contrasena: str) -> Ed25519PrivateKey:
    from seguridad import secretos

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if datos.get("formato") != FORMATO_CLAVE:
        raise ValueError(f"{ruta.name} no es una clave del proyecto de Sílice")
    semilla = secretos.descifrar(
        base64.b64decode(datos["sobre"]), contrasena, asociado=ASOCIADO + datos["publica"].encode()
    )
    return Ed25519PrivateKey.from_private_bytes(semilla)


def leer_publica(ruta: Path | None = None) -> bytes:
    destino = ruta if ruta is not None else RUTA_PUBLICA
    texto = destino.read_text(encoding="utf-8").strip()
    try:
        publica = bytes.fromhex(texto)
    except ValueError:
        raise ValueError(f"{destino.name} no es una clave pública en hexadecimal") from None
    if len(publica) != 32:
        raise ValueError(
            f"{destino.name}: una clave pública Ed25519 mide 32 bytes, no {len(publica)}"
        )
    return publica
```

`operacion/ordenes_100.py` (nuevo; T7/T8 agregan sus órdenes a `registrar`):
```python
"""Órdenes de la 1.0.0 de `python -m operacion` (spec S5 §5.4, §6.5, §8.2 y §10.4)."""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Callable
from pathlib import Path

from cryptography.exceptions import InvalidTag

from operacion import config, firma_sumas


def _generar_clave(argumentos: argparse.Namespace) -> int:
    salida = Path(argumentos.salida).resolve()
    if salida.is_relative_to(config.RAIZ.resolve()):
        print("La clave privada no puede vivir dentro del repositorio.", file=sys.stderr)
        return 1
    if "onedrive" in str(salida).lower():
        print(
            "La clave privada no puede vivir en una carpeta de OneDrive (se sincroniza).",
            file=sys.stderr,
        )
        return 1
    if (salida / "clave_proyecto.enc").exists():
        print(f"Ya hay una clave en {salida}: no se pisa.", file=sys.stderr)
        return 1
    contrasena = getpass.getpass("Contraseña de la clave del proyecto (mínimo 12 caracteres): ")
    if contrasena != getpass.getpass("Repítala: "):
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 1
    privada = firma_sumas.generar_par()
    try:
        firma_sumas.guardar_privada(privada, contrasena, salida / "clave_proyecto.enc")
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    publica = firma_sumas.bytes_publicos(privada)
    (salida / "clave_proyecto.pub").write_text(publica.hex() + "\n", encoding="utf-8")
    print(f"Clave pública: {publica.hex()}")
    print(f"Huella SHA-256: {firma_sumas.huella(publica)}")
    print(
        f"Copie {salida / 'clave_proyecto.pub'} a operacion/clave_proyecto.pub y versione SOLO ese "
        f"archivo. Guarde {salida / 'clave_proyecto.enc'} y su contraseña en dos lugares fuera del "
        "repositorio."
    )
    return 0


def _firmar_sumas(argumentos: argparse.Namespace) -> int:
    sumas = Path(argumentos.sumas)
    clave = Path(argumentos.clave)
    clave = clave / "clave_proyecto.enc" if clave.is_dir() else clave
    try:
        privada = firma_sumas.cargar_privada(
            clave, getpass.getpass("Contraseña de la clave del proyecto: ")
        )
    except InvalidTag:
        print("Contraseña incorrecta (o la clave no es la que dice ser).", file=sys.stderr)
        return 1
    try:
        publica_del_programa = firma_sumas.leer_publica()
    except (FileNotFoundError, ValueError) as error:
        print(f"No hay clave del proyecto en este programa: {error}", file=sys.stderr)
        return 1
    if firma_sumas.bytes_publicos(privada) != publica_del_programa:
        print(
            "Esa clave no es la clave del proyecto (operacion/clave_proyecto.pub): no se firma "
            "nada.",
            file=sys.stderr,
        )
        return 1
    datos = sumas.read_bytes()
    firma = firma_sumas.firmar(datos, privada)
    assert firma_sumas.verificar(datos, firma, publica_del_programa)
    destino = sumas.with_name(sumas.name + ".ed25519")
    destino.write_bytes(firma)
    print(f"Firmado: {destino}")
    return 0


def _verificar_instalador(argumentos: argparse.Namespace) -> int:
    try:
        publica = (
            bytes.fromhex(argumentos.publica) if argumentos.publica else firma_sumas.leer_publica()
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"No hay clave del proyecto para comprobar: {error}", file=sys.stderr)
        return 1
    ok, mensaje = firma_sumas.verificar_instalador(
        Path(argumentos.exe),
        Path(argumentos.sumas).read_bytes(),
        Path(argumentos.firma).read_bytes(),
        publica,
    )
    print(mensaje, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


def _huella(_argumentos: argparse.Namespace) -> int:
    publica = firma_sumas.leer_publica()
    print(firma_sumas.huella(publica))
    print(firma_sumas.huella_agrupada(publica))
    return 0


def registrar(
    ordenes: argparse._SubParsersAction, tabla: dict[str, Callable[[argparse.Namespace], int]]
) -> None:
    """Agrega al `python -m operacion` las órdenes de la 1.0.0 (cada tarea agrega las suyas)."""
    generar = ordenes.add_parser(
        "generar-clave-proyecto", help="genera el par Ed25519 del proyecto"
    )
    generar.add_argument(
        "--salida", required=True, help="carpeta FUERA del repositorio y de OneDrive"
    )
    firmar = ordenes.add_parser("firmar-sumas", help="firma SHA256SUMS con la clave del proyecto")
    firmar.add_argument("sumas")
    firmar.add_argument("--clave", required=True, help="clave_proyecto.enc o su carpeta")
    verificar = ordenes.add_parser("verificar-instalador", help="huella y firma de un instalador")
    for nombre in ("exe", "sumas", "firma"):
        verificar.add_argument(nombre)
    verificar.add_argument(
        "--publica", help="clave pública en hexadecimal (por defecto, la del programa)"
    )
    ordenes.add_parser(
        "huella-clave-proyecto", help="huella SHA-256 de la clave pública del proyecto"
    )
    tabla.update(
        {
            "generar-clave-proyecto": _generar_clave,
            "firmar-sumas": _firmar_sumas,
            "verificar-instalador": _verificar_instalador,
            "huella-clave-proyecto": _huella,
        }
    )
```
`operacion/__main__.py`, en `main`, antes de `argumentos = analizador.parse_args(argv)`:
```python
    from operacion import ordenes_100

    ordenes_100.registrar(ordenes, _ORDENES)
```
(La Tarea 8 **agrega** a `ordenes_100.py` y no repite estas tres líneas de `__main__`.)

`instalador/verificar_sumas.py` (biblioteca estándar + `cryptography`; se entrega con el release):
```python
"""Comprueba un instalador de Sílice sin tener Sílice (spec S5 §10.4; RP10-10).

    uv run --with cryptography verificar_sumas.py Silice-1.0.0.exe SHA256SUMS SHA256SUMS.ed25519 \\
        --publica <clave pública del proyecto, 64 caracteres hexadecimales>

Comprueba (1) la firma Ed25519 de SHA256SUMS con la clave pública que usted pasa y (2) la huella
SHA-256 del instalador contra SHA256SUMS. Imprime la huella de la clave usada: debe ser la del
manual de instalación y la de la tesis. Sale con 1 si algo no cuadra.
"""

import argparse
import hashlib
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DOMINIO = b"silice-sumas-v1\0"


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("exe", type=Path)
    analizador.add_argument("sumas", type=Path)
    analizador.add_argument("firma", type=Path)
    analizador.add_argument("--publica", required=True, help="clave pública en hexadecimal")
    argumentos = analizador.parse_args()
    publica = bytes.fromhex(argumentos.publica)
    datos = argumentos.sumas.read_bytes()
    print(f"Huella de la clave usada: {hashlib.sha256(publica).hexdigest()}")
    try:
        Ed25519PublicKey.from_public_bytes(publica).verify(
            argumentos.firma.read_bytes(), DOMINIO + datos
        )
    except (InvalidSignature, ValueError):
        print("FIRMA NO VÁLIDA: NO INSTALE este archivo.", file=sys.stderr)
        return 1
    esperada = None
    for linea in datos.decode("utf-8").splitlines():
        huella, _, nombre = linea.partition(" ")
        if nombre.lstrip(" *") == argumentos.exe.name:
            esperada = huella
    if esperada is None:
        print(f"{argumentos.exe.name} no figura en SHA256SUMS: NO INSTALE.", file=sys.stderr)
        return 1
    if hashlib.sha256(argumentos.exe.read_bytes()).hexdigest() != esperada:
        print("La huella del instalador NO coincide con SHA256SUMS: NO INSTALE.", file=sys.stderr)
        return 1
    print(f"VERIFICADO: {argumentos.exe.name} coincide con SHA256SUMS firmado por esa clave.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_firma_sumas.py tests/unit/test_ordenes_clave.py
tests/unit/test_verificar_sumas_independiente.py tests/integration/test_operacion_cli.py -v -W
error`
y `uv run ruff check operacion/firma_sumas.py operacion/ordenes_100.py instalador/verificar_sumas.py
tests/unit/test_firma_sumas.py tests/unit/test_ordenes_clave.py`.

- [ ] **Paso 5: Commit**
```bash
git add operacion/firma_sumas.py operacion/ordenes_100.py operacion/__main__.py \
  instalador/verificar_sumas.py
git commit -m "feat(operacion): firma Ed25519 de SHA256SUMS con separacion de dominio" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 6: Revisión del encargo de seguridad antes de la ceremonia**
El revisor fresco comprueba, leyendo `operacion/firma_sumas.py`: que no hay criptografía propia
(solo
`cryptography` y `seguridad.secretos`); que `verificar` nunca lanza con una entrada mal formada; que
`parsear_sumas` rechaza rutas; que la privada nunca se escribe sin cifrar ni se imprime; y que
ninguna prueba contiene una clave real.

- [ ] **Paso 7: La ceremonia de la clave [HUMANO: H1]** (Eugenio, en su equipo, sin ningún agente)

> **Un agente se detiene aquí y le dice a Eugenio que le toca.** Ningún agente genera, toca, lee ni
> copia la clave privada ni su contraseña, y la CI jamás la recibe.

```powershell
# 1. Fuera del repositorio y de OneDrive (la orden se niega si la ruta es una de esas dos)
uv run python -m operacion generar-clave-proyecto --salida "$env:USERPROFILE\.silice-clave"
# pide una contraseña de 12 caracteres o más, dos veces; imprime la pública y su huella
# 2. Guardar clave_proyecto.enc y la contraseña en DOS lugares fuera del equipo (memoria USB y
#    gestor de contraseñas). Perder la contraseña es perder la clave: habría que generar otra.
# 3. Versionar SOLO la pública
Copy-Item "$env:USERPROFILE\.silice-clave\clave_proyecto.pub" operacion\clave_proyecto.pub
uv run python -m operacion huella-clave-proyecto      # debe imprimir la misma huella
git add operacion/clave_proyecto.pub
git commit -m "feat(operacion): clave publica Ed25519 del proyecto"
```
La huella (64 hexadecimales) se anota en la bitácora, se pega en `docs/manual_instalacion.md`
(Tarea 19) y se cita en la tesis. La rama no se fusiona hasta que exista
`operacion/clave_proyecto.pub` (lo comprueba la fila `S5-CLAVE` de la meta en GS5).

- [ ] **Paso 8: PR**
```bash
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-clave-proyecto
gh pr create --base main --head inc/100-clave-proyecto \
  --title "S5-0: firma de SHA256SUMS y clave publica del proyecto" --body-file -
```

---

## S5-2 · Operación (RF-98, RF-99)

### Tarea 4: `operacion.version`, `operacion.registro` y la versión de la API

**Rama:** `inc/100-s5-2-operacion` (sale de `origin/main`; PR a `main`; RV-2)   **Rol:**
sf-ingeniero-adaptadores
**Archivos:**
- Crear: `operacion/version.py`, `operacion/registro.py`, `scripts/verificar_version.py`
- Modificar: `api/main.py:5` (importación) y `api/main.py:18` (`version="0.1.0"` fijo)
- Prueba: `tests/unit/test_version.py`, `tests/unit/test_registro.py`,
  `tests/unit/test_verificar_version.py`

**Interfaces:**
- Consume: `operacion.config.RAIZ` (A1); `packaging.version.Version` solo en las pruebas y en el
  script.
- Produce:
  - `operacion.version`: `ruta_pyproject() -> Path`, `version() -> str` (PEP 440, tal como está en
    `pyproject.toml`), `a_semver(pep440: str) -> str`, `a_pep440(semver: str) -> str`,
    `etiqueta(pep440: str | None = None) -> str` (`"v1.0.0-rc.1"`),
    `siguiente_parche(semver: str) -> str` (`"1.0.0-rc.1"` → `"1.0.1"`).
  - `operacion.registro`: `NOMBRE_LOGGER = "silice"`, `MARCA = "[omitido]"`,
    `limpiar(texto: str, perfil: str | None = None) -> str`,
    `registrar_secreto(valor: str) -> None`, `olvidar_secretos() -> None`,
    `FormatoSeguro(logging.Formatter)`,
    `configurar(carpeta: Path, nivel: str = "INFO", *, max_bytes: int = 1_000_000, copias: int = 5)
    -> logging.Logger`,
    `copiar_salida(flujo: Iterable[str], logger: logging.Logger, nivel: int = logging.ERROR,
    origen: str = "") -> int`.
  - `scripts.verificar_version`: `comparar(etiqueta: str, pep440: str) -> tuple[bool, str]`,
    `main(argv: list[str] | None = None) -> int`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_version.py`:
```python
"""Una sola fuente de la versión (RF-99; spec S5 §9.2)."""

from __future__ import annotations

import tomllib

import pytest
from packaging.version import Version

from api.main import app
from operacion import version as v


def test_la_version_sale_de_pyproject() -> None:
    with v.ruta_pyproject().open("rb") as archivo:
        esperada = tomllib.load(archivo)["project"]["version"]
    assert v.version() == esperada


def test_la_version_de_la_api_es_la_de_pyproject() -> None:
    assert app.version == v.version()


@pytest.mark.parametrize(
    ("pep", "semver"),
    [
        ("1.0.0", "1.0.0"),
        ("1.0.0rc1", "1.0.0-rc.1"),
        ("1.0.0rc12", "1.0.0-rc.12"),
        ("0.9.0a2", "0.9.0-alpha.2"),
        ("0.9.0b3", "0.9.0-beta.3"),
    ],
)
def test_conversion_de_ida_y_vuelta_y_packaging_la_normaliza(pep: str, semver: str) -> None:
    assert v.a_semver(pep) == semver
    assert v.a_pep440(semver) == pep
    # S5 §9.2: que 1.0.0-rc.1 normalice a 1.0.0rc1 se confirma aquí, con la biblioteca de la CI.
    assert str(Version(semver)) == pep


def test_la_etiqueta_lleva_v_y_semver() -> None:
    assert v.etiqueta("1.0.0rc1") == "v1.0.0-rc.1"
    assert v.etiqueta("1.0.0") == "v1.0.0"


@pytest.mark.parametrize("texto", ["1.0", "1.0.0.1", "v1.0.0", "1.0.0-rc1", "1.0.0rc", "uno"])
def test_una_version_que_no_es_pep440_ni_semver_se_rechaza(texto: str) -> None:
    with pytest.raises(ValueError, match="versión"):
        v.a_semver(texto)
    with pytest.raises(ValueError, match="versión"):
        v.a_pep440(texto)


def test_siguiente_parche_es_mayor_que_la_candidata_y_que_la_final() -> None:
    assert v.siguiente_parche("1.0.0") == "1.0.1"
    assert v.siguiente_parche("1.0.0-rc.1") == "1.0.1"
    assert Version("1.0.1") > Version("1.0.0-rc.1")
```

`tests/unit/test_verificar_version.py`:
```python
"""La etiqueta de git coincide con pyproject, normalizada (RF-99; spec S5 §9.2)."""

from __future__ import annotations

import pytest

from scripts import verificar_version as vv


@pytest.mark.parametrize(
    ("etiqueta", "pep"),
    [("v1.0.0", "1.0.0"), ("v1.0.0-rc.1", "1.0.0rc1"), ("v0.6.0", "0.6.0")],
)
def test_etiqueta_que_coincide(etiqueta: str, pep: str) -> None:
    assert vv.comparar(etiqueta, pep)[0] is True


@pytest.mark.parametrize(
    ("etiqueta", "pep", "razon"),
    [
        ("1.0.0", "1.0.0", "empezar con «v»"),
        ("v1.0.0", "1.0.1", "no coincide"),
        ("v1.0.0-rc.2", "1.0.0rc1", "no coincide"),
        ("v1.0", "1.0.0", "SemVer"),
        ("v1.0.0rc1", "1.0.0rc1", "SemVer"),
    ],
)
def test_etiqueta_que_no_coincide(etiqueta: str, pep: str, razon: str) -> None:
    coincide, mensaje = vv.comparar(etiqueta, pep)
    assert coincide is False and razon in mensaje


def test_main_devuelve_0_o_1(capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    monkeypatch.setattr(vv, "version_del_proyecto", lambda: "1.0.0rc1")
    assert vv.main(["--etiqueta", "v1.0.0-rc.1"]) == 0
    assert vv.main(["--etiqueta", "v1.0.0"]) == 1
    assert "no coincide" in capsys.readouterr().err


def test_imprimir_la_version_semver_y_la_de_parche(capsys, monkeypatch) -> None:
    monkeypatch.setattr(vv, "version_del_proyecto", lambda: "1.0.0rc1")
    assert vv.main(["--imprimir", "semver"]) == 0
    assert capsys.readouterr().out.strip() == "1.0.0-rc.1"
    assert vv.main(["--imprimir", "parche"]) == 0
    assert capsys.readouterr().out.strip() == "1.0.1"
```

`tests/unit/test_registro.py`:
```python
"""Registro de errores sin secretos (RF-98; spec S5 §8.4)."""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from operacion import registro

#: Cada valor sembrado y el fragmento que no puede llegar al archivo.
SEMBRADOS = {
    "clave de IA": ("sk-ant-api03-ZXCVBNM1234567890", "sk-ant-api03"),
    "bearer": ("Bearer eyJhbGciOiJIUzI1NiJ9.cuerpo.firma", "eyJhbGci"),
    "cabecera de la API": ("X-Silice-Clave: AB12CD34.s3cretoDeClaveDeApi", "s3cretoDeClave"),
    "contraseña": ("contraseña=Tr0ub4dor&3xyz", "Tr0ub4dor"),
    "PEM": (
        "-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIA\n-----END PRIVATE KEY-----",
        "MC4CAQAw",
    ),
    "consulta": ("GET http://127.0.0.1:8501/x?token=abc123def", "abc123def"),
}


@pytest.fixture
def registro_en(tmp_path: Path) -> Iterator[tuple[logging.Logger, Path]]:
    logger = registro.configurar(tmp_path / "registros")
    yield logger, tmp_path / "registros" / "silice.log"
    for manejador in list(logger.handlers):
        logger.removeHandler(manejador)
        manejador.close()
    registro.olvidar_secretos()


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


@pytest.mark.parametrize("nombre", SEMBRADOS)
def test_secretos_sembrados_no_llegan_al_archivo(registro_en, nombre: str) -> None:
    logger, archivo = registro_en
    valor, fragmento = SEMBRADOS[nombre]
    logger.error("algo falló con %s", valor)
    texto = _texto(archivo)
    assert fragmento not in texto
    assert registro.MARCA in texto


def test_una_excepcion_guarda_tipo_mensaje_y_lineas_sin_valores(registro_en) -> None:
    logger, archivo = registro_en
    try:
        raise ValueError("fallo con clave=sk-ant-api03-ZZZ y secreto=hunter2xyz")
    except ValueError:
        logger.exception("no se pudo")
    texto = _texto(archivo)
    assert "ValueError" in texto and ".py:" in texto
    assert "sk-ant-api03" not in texto and "hunter2xyz" not in texto
    assert "raise ValueError" not in texto  # ni el texto de la línea de código


def test_el_perfil_del_usuario_se_reescribe() -> None:
    perfil = r"C:\Users\euger"
    assert registro.limpiar(r"abrió C:\Users\euger\x.db", perfil) == r"abrió %USERPROFILE%\x.db"
    assert registro.limpiar("abrió c:/users/euger/x.db", perfil) == "abrió %USERPROFILE%/x.db"


def test_el_codigo_de_instalacion_conocido_no_llega_al_archivo(registro_en) -> None:
    logger, archivo = registro_en
    registro.registrar_secreto("K7QFM9XRA2PTW4HNC8DV")
    logger.info("el código es K7QFM9XRA2PTW4HNC8DV, úselo una vez")
    assert "K7QFM9XRA2PTW4HNC8DV" not in _texto(archivo)


def test_la_salida_de_un_hijo_pasa_por_el_mismo_filtro(registro_en) -> None:
    logger, archivo = registro_en
    programa = (
        "import sys\n"
        "for l in ('Bearer ABC.def.ghi', '-----BEGIN PRIVATE KEY-----', 'MC4CAQAwBQYDK2Vw',"
        " '-----END PRIVATE KEY-----', 'listo'):\n"
        "    print(l, file=sys.stderr)\n"
    )
    hijo = subprocess.run(
        [sys.executable, "-c", programa], capture_output=True, text=True, check=True
    )
    contadas = registro.copiar_salida(hijo.stderr.splitlines(keepends=True), logger, origen="hijo")
    texto = _texto(archivo)
    assert contadas == 5 and "listo" in texto
    assert "ABC.def" not in texto and "MC4CAQAw" not in texto


def test_el_archivo_rota_y_conserva_cinco_copias(tmp_path: Path) -> None:
    logger = registro.configurar(tmp_path, max_bytes=2000, copias=5)
    try:
        for i in range(400):
            logger.error("línea %03d %s", i, "x" * 80)
    finally:
        for manejador in list(logger.handlers):
            logger.removeHandler(manejador)
            manejador.close()
    nombres = sorted(p.name for p in tmp_path.iterdir())
    assert nombres == ["silice.log"] + [f"silice.log.{n}" for n in range(1, 6)]


def test_un_nivel_desconocido_se_rechaza(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nivel"):
        registro.configurar(tmp_path, "RUIDO")
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit de las pruebas**
Run: `unset VIRTUAL_ENV; uv sync --all-extras; uv run pytest tests/unit/test_version.py
tests/unit/test_verificar_version.py tests/unit/test_registro.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'operacion.version'` (y `.registro`,
`scripts.verificar_version`).
```bash
git add tests/unit/test_version.py tests/unit/test_verificar_version.py tests/unit/test_registro.py
git commit -m "test(operacion): version unica y registro sin secretos (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/version.py`:
```python
"""La versión de Sílice sale de un solo sitio: `pyproject.toml` (RF-99; spec S5 §9.2).

`pyproject.toml` guarda la versión en PEP 440 (`1.0.0rc1`); la etiqueta de git y el instalador usan
SemVer (`v1.0.0-rc.1`, `1.0.0-rc.1`). Las conversiones son exactas y reversibles; `packaging`
normaliza `1.0.0-rc.1` a `1.0.0rc1` y la prueba lo confirma.
"""

from __future__ import annotations

import re
import tomllib
from functools import lru_cache
from pathlib import Path

from operacion import config

_PEP = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$")
_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?$")
_A_SEMVER = {"a": "alpha", "b": "beta", "rc": "rc"}
_A_PEP = {nombre: letra for letra, nombre in _A_SEMVER.items()}


def ruta_pyproject() -> Path:
    return config.RAIZ / "pyproject.toml"


@lru_cache(maxsize=1)
def version() -> str:
    """La versión de `pyproject.toml`, en PEP 440."""
    with ruta_pyproject().open("rb") as archivo:
        return str(tomllib.load(archivo)["project"]["version"])


def _rechazar(texto: str) -> ValueError:
    return ValueError(f"«{texto}» no es una versión válida (X.Y.Z, con a, b o rc opcional)")


def a_semver(pep440: str) -> str:
    coincidencia = _PEP.match(pep440)
    if coincidencia is None:
        raise _rechazar(pep440)
    mayor, menor, parche, fase, numero = coincidencia.groups()
    base = f"{mayor}.{menor}.{parche}"
    return base if fase is None else f"{base}-{_A_SEMVER[fase]}.{numero}"


def a_pep440(semver: str) -> str:
    coincidencia = _SEMVER.match(semver)
    if coincidencia is None:
        raise _rechazar(semver)
    mayor, menor, parche, fase, numero = coincidencia.groups()
    base = f"{mayor}.{menor}.{parche}"
    return base if fase is None else f"{base}{_A_PEP[fase]}{numero}"


def etiqueta(pep440: str | None = None) -> str:
    return "v" + a_semver(pep440 if pep440 is not None else version())


def siguiente_parche(semver: str) -> str:
    """`1.0.0-rc.1` → `1.0.1`: mayor que la candidata y que la final (prueba de actualización)."""
    coincidencia = _SEMVER.match(semver)
    if coincidencia is None:
        raise _rechazar(semver)
    mayor, menor, parche = (int(grupo) for grupo in coincidencia.groups()[:3])
    return f"{mayor}.{menor}.{parche + 1}"
```

`operacion/registro.py`:
```python
"""Registro de errores sin datos sensibles (RF-98; spec S5 §8.4).

`registros/silice.log`, rotativo (1 MB × 5), con el formato `fecha nivel módulo mensaje`. Nunca se
escriben contraseñas, códigos de instalación, claves de API o de IA, bloques PEM, cuerpos de
petición ni cadenas de consulta; la carpeta del usuario se reescribe como `%USERPROFILE%`. Las
trazas guardan el tipo, el mensaje (también filtrado) y `archivo:línea`, nunca el texto de la
línea ni los valores de las variables. El lanzador pasa por el mismo filtro la salida de Streamlit
y de Uvicorn (`copiar_salida`).
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import re
import traceback
from collections.abc import Iterable
from pathlib import Path

NOMBRE_LOGGER = "silice"
MARCA = "[omitido]"

_PATRONES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"-----BEGIN [A-Z0-9 ]+-----.*?(?:-----END [A-Z0-9 ]+-----|\Z)", re.DOTALL), MARCA),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]+"), MARCA),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=\-]+"), "Bearer " + MARCA),
    (re.compile(r"(?i)(x-silice-clave\s*[:=]\s*)\S+"), r"\1" + MARCA),
    (
        re.compile(
            r"(?i)\b(contrase[nñ]a|password|passwd|clave|secreto|token"
            r"|codigo(?:_de)?_instalaci[oó]n)(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|\S+)"
        ),
        r"\1\2" + MARCA,
    ),
    (re.compile(r"(https?://[^\s?\"']+)\?[^\s\"'<>]+"), r"\1?" + MARCA),
)
_SECRETOS_CONOCIDOS: set[str] = set()


def registrar_secreto(valor: str) -> None:
    """Un valor concreto (el código de instalación) que no debe aparecer jamás en el archivo."""
    if len(valor) >= 8:
        _SECRETOS_CONOCIDOS.add(valor)


def olvidar_secretos() -> None:
    _SECRETOS_CONOCIDOS.clear()


def _perfil() -> str:
    return os.environ.get("USERPROFILE") or str(Path.home())


def limpiar(texto: str, perfil: str | None = None) -> str:
    for valor in _SECRETOS_CONOCIDOS:
        texto = texto.replace(valor, MARCA)
    for patron, sustituto in _PATRONES:
        texto = patron.sub(sustituto, texto)
    base = _perfil() if perfil is None else perfil
    if base:
        for variante in {base, base.replace("\\", "/")}:
            texto = re.sub(re.escape(variante), lambda _: "%USERPROFILE%", texto, flags=re.I)
    return texto


class FormatoSeguro(logging.Formatter):
    """`fecha nivel módulo mensaje`, con el mensaje y la excepción pasados por `limpiar`."""

    def __init__(self) -> None:
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        texto = (
            f"{self.formatTime(record, self.datefmt)} {record.levelname} {record.name} "
            f"{limpiar(record.getMessage())}"
        )
        if record.exc_info and record.exc_info[1] is not None:
            tipo, valor, cola = record.exc_info
            lineas = [f"{tipo.__name__}: {limpiar(str(valor))}"]
            for marco in traceback.extract_tb(cola):
                lineas.append(f"  en {limpiar(marco.filename)}:{marco.lineno} ({marco.name})")
            texto += "\n" + "\n".join(lineas)
        return texto


def configurar(
    carpeta: Path, nivel: str = "INFO", *, max_bytes: int = 1_000_000, copias: int = 5
) -> logging.Logger:
    if nivel.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise ValueError(f"nivel de registro desconocido: {nivel!r}")
    carpeta.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(NOMBRE_LOGGER)
    for manejador in list(logger.handlers):
        logger.removeHandler(manejador)
        manejador.close()
    manejador = logging.handlers.RotatingFileHandler(
        carpeta / "silice.log", maxBytes=max_bytes, backupCount=copias, encoding="utf-8"
    )
    manejador.setFormatter(FormatoSeguro())
    logger.addHandler(manejador)
    logger.setLevel(nivel.upper())
    logger.propagate = False
    return logger


def copiar_salida(
    flujo: Iterable[str], logger: logging.Logger, nivel: int = logging.ERROR, origen: str = ""
) -> int:
    """Pasa por el filtro cada línea de la salida de un proceso hijo. Un bloque PEM repartido en
    varias líneas se descarta entero. Devuelve cuántas líneas leyó."""
    leidas = 0
    dentro_de_pem = False
    for linea in flujo:
        leidas += 1
        texto = linea.rstrip("\r\n")
        if dentro_de_pem:
            dentro_de_pem = "-----END" not in texto
            continue
        if "-----BEGIN" in texto and "-----END" not in texto:
            dentro_de_pem = True
            texto = texto[: texto.index("-----BEGIN")] + "-----BEGIN " + MARCA
        if texto.strip():
            logger.log(nivel, "%s %s", origen, texto)
    return leidas
```

`scripts/verificar_version.py`:
```python
"""Comprueba que la etiqueta de git coincide con `pyproject.toml` (RF-99; spec S5 §9.2).

    uv run python scripts/verificar_version.py --etiqueta v1.0.0-rc.1

La etiqueta es SemVer con `v`; `pyproject.toml` guarda PEP 440; se comparan normalizadas con
`packaging.version`. Código de salida 0 si coinciden, 1 si no.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from packaging.version import InvalidVersion, Version

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion.version import a_semver, siguiente_parche, version  # noqa: E402

_SEMVER_CON_V = re.compile(r"^v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?$")


def version_del_proyecto() -> str:
    return version()


def comparar(etiqueta: str, pep440: str) -> tuple[bool, str]:
    if not etiqueta.startswith("v"):
        return False, f"la etiqueta «{etiqueta}» debe empezar con «v»"
    if _SEMVER_CON_V.match(etiqueta) is None:
        return False, f"la etiqueta «{etiqueta}» no es SemVer (vX.Y.Z o vX.Y.Z-rc.N)"
    try:
        igual = Version(etiqueta[1:]) == Version(pep440)
    except InvalidVersion as error:
        return False, f"versión inválida: {error}"
    if not igual:
        return False, f"la etiqueta {etiqueta} no coincide con pyproject.toml ({pep440})"
    return True, f"{etiqueta} coincide con pyproject.toml ({pep440})"


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    grupo = analizador.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--etiqueta", help="vX.Y.Z[-rc.N]: comprobar contra pyproject.toml")
    grupo.add_argument("--imprimir", choices=["semver", "parche"], help="imprimir la versión")
    argumentos = analizador.parse_args(argv)
    if argumentos.imprimir:
        semver = a_semver(version_del_proyecto())
        print(semver if argumentos.imprimir == "semver" else siguiente_parche(semver))
        return 0
    coincide, mensaje = comparar(argumentos.etiqueta, version_del_proyecto())
    print(mensaje, file=sys.stdout if coincide else sys.stderr)
    return 0 if coincide else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

`api/main.py`: agregar `from operacion.version import version` a las importaciones y cambiar la
línea 18 por
`app = FastAPI(title="Sílice", version=version(), description=DESCRIPCION)`. (La tarea 9 vuelve a
tocar esta línea para agregar `**opciones_documentacion()`.)

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite)
Run: `uv run pytest tests/unit/test_version.py tests/unit/test_verificar_version.py
tests/unit/test_registro.py tests/unit/test_arquitectura_s5.py -v -W error`
y luego `uv run pytest -q -W error` (`docs/api.json` no cambia: el `version` del OpenAPI sí;
correr `uv run python scripts/exportar_openapi.py` y revisar que el único cambio sea
`info.version`).
`uv run ruff check operacion scripts/verificar_version.py tests/unit/test_version.py
tests/unit/test_registro.py tests/unit/test_verificar_version.py api/main.py`.

- [ ] **Paso 5: Commit**
```bash
git add operacion/version.py operacion/registro.py scripts/verificar_version.py api/main.py \
  docs/api.json
git commit -m "feat(operacion): version unica de pyproject y registro sin secretos" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Tarea 5: `operacion.config`: producto, rutas de usuario y `silice.toml`

**Rama:** `inc/100-s5-2-operacion`   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Modificar: `operacion/config.py` (las funciones `carpeta_datos` y `carpeta_respaldos`, y las
  constantes nuevas al final); `tests/conftest.py` (fixture `_datos_de_silice_temporales`);
  `.gitignore` (al final)
- Prueba: `tests/unit/test_ajustes.py`; `tests/unit/test_operacion_config.py` (se agregan cuatro)

**Interfaces:**
- Consume: de A1 (0.6.0) `config._valor`, `config._ruta`, `config.RAIZ`, `config.DATOS_DESARROLLO`.
- Produce, en `operacion.config`:
  - `VARIABLE_USUARIO = "SILICE_USUARIO"`, `NIVELES_DE_REGISTRO = ("DEBUG", "INFO", "WARNING",
    "ERROR")`,
    `es_producto(raiz: Path | None = None) -> bool`, `carpeta_usuario(entorno=None) -> Path`,
    `ruta_ajustes(entorno=None) -> Path`, `carpeta_registros(entorno=None) -> Path`,
    `ruta_estado(entorno=None) -> Path`, `ruta_codigo_instalacion(entorno=None) -> Path`.
  - `Ajustes` (dataclass inmutable): `puerto=8501`, `red_local=False`, `direccion=""`,
    `api_activa=False`, `puerto_api=8000`, `mostrar_investigacion=False`, `nivel_registro="INFO"`,
    `avisos: tuple[str, ...] = ()`.
  - `cargar_ajustes(ruta: Path) -> Ajustes`, `guardar_ajustes(ruta: Path, ajustes: Ajustes) ->
    None`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_ajustes.py`:
```python
"""`silice.toml`: valores por defecto y archivo dañado (RF-98; spec S5 §8.1)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from operacion.config import Ajustes, cargar_ajustes, guardar_ajustes


def _escribir(ruta: Path, texto: str) -> Path:
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def test_los_valores_por_defecto_apagan_la_red_y_la_api(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(tmp_path / "no_existe.toml")
    assert ajustes == Ajustes()
    assert (ajustes.red_local, ajustes.api_activa, ajustes.mostrar_investigacion) == (False,) * 3
    assert (ajustes.puerto, ajustes.puerto_api, ajustes.nivel_registro) == (8501, 8000, "INFO")


def test_guardar_y_volver_a_leer_da_lo_mismo(tmp_path: Path) -> None:
    ruta = tmp_path / "config" / "silice.toml"
    esperados = Ajustes(
        puerto=8600,
        red_local=True,
        direccion="192.168.1.20",
        api_activa=True,
        puerto_api=8010,
        mostrar_investigacion=True,
        nivel_registro="WARNING",
    )
    guardar_ajustes(ruta, esperados)
    assert cargar_ajustes(ruta) == esperados


@pytest.mark.parametrize(
    "texto",
    [
        "[servidor\npuerto = 8501",
        "\x00\x01 no es toml",
        'puerto = "sin tabla" ===',
        "[servidor]\nred_local = ",
    ],
)
def test_un_archivo_danado_da_defectos_y_nunca_red_encendida(tmp_path: Path, texto: str) -> None:
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", texto))
    assert ajustes.red_local is False and ajustes.api_activa is False
    assert ajustes.direccion == "" and len(ajustes.avisos) == 1
    assert "valores por defecto" in ajustes.avisos[0]


def test_un_archivo_que_no_es_utf8_tambien_es_danado(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    ruta.write_bytes(b"[servidor]\nred_local = true\n\xff\xfe")
    ajustes = cargar_ajustes(ruta)
    assert ajustes.red_local is False and ajustes.avisos


@pytest.mark.parametrize("direccion", ["", "0.0.0.0", "::", "8.8.8.8", "no-es-ip", "224.0.0.1"])
def test_red_local_con_direccion_invalida_se_apaga_y_avisa(tmp_path: Path, direccion: str) -> None:
    ruta = _escribir(
        tmp_path / "silice.toml", f'[servidor]\nred_local = true\ndireccion = "{direccion}"\n'
    )
    ajustes = cargar_ajustes(ruta)
    assert ajustes.red_local is False and ajustes.direccion == ""
    assert any("dirección" in aviso for aviso in ajustes.avisos)


@pytest.mark.parametrize("direccion", ["192.168.1.20", "10.0.0.5", "172.16.4.9"])
def test_red_local_con_ip_privada_se_acepta(tmp_path: Path, direccion: str) -> None:
    ruta = _escribir(
        tmp_path / "silice.toml", f'[servidor]\nred_local = true\ndireccion = "{direccion}"\n'
    )
    ajustes = cargar_ajustes(ruta)
    assert ajustes.red_local is True and ajustes.direccion == direccion and ajustes.avisos == ()


@pytest.mark.parametrize("puerto", ["80", "70000", '"8501"', "true", "-1", "8501.5"])
def test_un_puerto_invalido_vuelve_al_defecto_y_avisa(tmp_path: Path, puerto: str) -> None:
    ajustes = cargar_ajustes(
        _escribir(tmp_path / "silice.toml", f"[servidor]\npuerto = {puerto}\n")
    )
    assert ajustes.puerto == 8501 and any("puerto" in aviso for aviso in ajustes.avisos)


def test_los_dos_puertos_iguales_se_corrigen(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path / "silice.toml", "[servidor]\npuerto = 8600\n[api]\npuerto = 8600\n")
    ajustes = cargar_ajustes(ruta)
    assert ajustes.puerto == 8600 and ajustes.puerto_api == 8000 and ajustes.avisos


def test_un_nivel_desconocido_vuelve_a_info(tmp_path: Path) -> None:
    ajustes = cargar_ajustes(_escribir(tmp_path / "silice.toml", '[registro]\nnivel = "ruido"\n'))
    assert ajustes.nivel_registro == "INFO" and ajustes.avisos


def test_las_claves_con_tipo_equivocado_no_encienden_nada(tmp_path: Path) -> None:
    ruta = _escribir(
        tmp_path / "silice.toml",
        '[servidor]\nred_local = "true"\n[api]\nactiva = 1\n'
        '[interfaz]\nmostrar_investigacion = "si"\n',
    )
    ajustes = cargar_ajustes(ruta)
    assert (ajustes.red_local, ajustes.api_activa, ajustes.mostrar_investigacion) == (False,) * 3
    assert len(ajustes.avisos) == 3


def test_guardar_no_deja_un_archivo_a_medias(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    guardar_ajustes(ruta, replace(Ajustes(), puerto=8700))
    assert [p.name for p in tmp_path.iterdir()] == ["silice.toml"]
```
Agregar a `tests/unit/test_operacion_config.py`:
```python
def test_en_desarrollo_el_usuario_es_data_y_no_es_producto() -> None:
    assert config.es_producto() is False
    assert config.carpeta_usuario({}) == config.DATOS_DESARROLLO


def test_hay_producto_si_el_manifiesto_esta_junto_al_codigo(tmp_path: Path) -> None:
    (tmp_path / "codigo").mkdir()
    assert config.es_producto(tmp_path / "codigo") is False
    (tmp_path / "manifiesto.json").write_text("{}", encoding="utf-8")
    assert config.es_producto(tmp_path / "codigo") is True


def test_en_el_producto_todo_vive_en_localappdata_silice(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: True)
    entorno = {"LOCALAPPDATA": str(tmp_path / "Local")}
    usuario = (tmp_path / "Local" / "Silice").resolve()
    assert config.carpeta_usuario(entorno) == usuario
    assert config.carpeta_datos(entorno) == usuario / "datos"
    assert config.carpeta_casos(entorno) == usuario / "datos" / "casos"
    assert config.ruta_instalacion(entorno) == usuario / "datos" / "instalacion.db"
    assert config.carpeta_respaldos(entorno) == usuario / "respaldos"
    assert config.ruta_ajustes(entorno) == usuario / "config" / "silice.toml"
    assert config.carpeta_registros(entorno) == usuario / "registros"
    assert config.ruta_estado(entorno) == usuario / "estado" / "servidor.json"
    assert config.ruta_codigo_instalacion(entorno) == usuario / "datos" / "codigo_instalacion.txt"
    assert not usuario.exists()


def test_silice_usuario_manda_sobre_localappdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: True)
    entorno = {config.VARIABLE_USUARIO: str(tmp_path / "u"), "LOCALAPPDATA": str(tmp_path / "L")}
    assert config.carpeta_usuario(entorno) == (tmp_path / "u").resolve()
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_ajustes.py tests/unit/test_operacion_config.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'Ajustes' from 'operacion.config'` y
`AttributeError: module 'operacion.config' has no attribute 'es_producto'`.
```bash
git add tests/unit/test_ajustes.py tests/unit/test_operacion_config.py
git commit -m "test(operacion): silice.toml, modo producto y carpetas de usuario (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/config.py`: reemplazar `carpeta_datos` y `carpeta_respaldos` por
```python
def carpeta_datos(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_DATOS`; si no, `<usuario>/datos` en el producto y `data/` en desarrollo."""
    valor = _valor(VARIABLE_DATOS, entorno)
    if valor:
        return _ruta(valor)
    return carpeta_usuario(entorno) / "datos" if es_producto() else DATOS_DESARROLLO


def carpeta_respaldos(entorno: Mapping[str, str] | None = None) -> Path:
    """`SILICE_RESPALDOS`; si no, `<usuario>/respaldos` en el producto y `<datos>/respaldos`."""
    valor = _valor(VARIABLE_RESPALDOS, entorno)
    if valor:
        return _ruta(valor)
    if es_producto():
        return carpeta_usuario(entorno) / CARPETA_RESPALDOS
    return carpeta_datos(entorno) / CARPETA_RESPALDOS
```
y agregar al final del archivo (con `import ipaddress`, `import tomllib`, `from dataclasses import
dataclass, replace` arriba):
```python
VARIABLE_USUARIO = "SILICE_USUARIO"
NIVELES_DE_REGISTRO = ("DEBUG", "INFO", "WARNING", "ERROR")
PUERTO_STREAMLIT = 8501
PUERTO_API = 8000


def es_producto(raiz: Path | None = None) -> bool:
    """El instalador deja `manifiesto.json` junto a `codigo/`: eso distingue el producto de un
    árbol de desarrollo (spec S5 §5.3)."""
    return ((raiz or RAIZ).parent / "manifiesto.json").is_file()


def carpeta_usuario(entorno: Mapping[str, str] | None = None) -> Path:
    """Donde viven `config/`, `registros/` y `estado/`: `SILICE_USUARIO`; en el producto
    `%LOCALAPPDATA%\\Silice`; en desarrollo, `data/`."""
    valor = _valor(VARIABLE_USUARIO, entorno)
    if valor:
        return _ruta(valor)
    if es_producto():
        local = _valor("LOCALAPPDATA", entorno) or str(Path.home() / "AppData" / "Local")
        return _ruta(local) / "Silice"
    return DATOS_DESARROLLO


def ruta_ajustes(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_usuario(entorno) / "config" / "silice.toml"


def carpeta_registros(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_usuario(entorno) / "registros"


def ruta_estado(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_usuario(entorno) / "estado" / "servidor.json"


def ruta_codigo_instalacion(entorno: Mapping[str, str] | None = None) -> Path:
    return carpeta_datos(entorno) / "codigo_instalacion.txt"


@dataclass(frozen=True, slots=True)
class Ajustes:
    """El contenido de `silice.toml` ya validado (spec S5 §8.1). Todo lo dudoso cae al valor
    por defecto, que tiene la red local y la API apagadas."""

    puerto: int = PUERTO_STREAMLIT
    red_local: bool = False
    direccion: str = ""
    api_activa: bool = False
    puerto_api: int = PUERTO_API
    mostrar_investigacion: bool = False
    nivel_registro: str = "INFO"
    avisos: tuple[str, ...] = ()


def _direccion_valida(texto: str) -> bool:
    try:
        ip = ipaddress.ip_address(texto)
    except ValueError:
        return False
    return ip.version == 4 and ip.is_private and not (ip.is_unspecified or ip.is_multicast)


def _puerto(valor: object, defecto: int, nombre: str, avisos: list[str]) -> int:
    if isinstance(valor, int) and not isinstance(valor, bool) and 1024 <= valor <= 65535:
        return valor
    if valor is not None:
        avisos.append(f"El puerto de {nombre} no es válido ({valor!r}); se usa {defecto}.")
    return defecto


def _booleano(valor: object, nombre: str, avisos: list[str]) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is not None:
        avisos.append(f"«{nombre}» debe ser true o false ({valor!r}); se usa false.")
    return False


def _tabla(datos: dict, nombre: str) -> dict:
    tabla = datos.get(nombre, {})
    return tabla if isinstance(tabla, dict) else {}


def cargar_ajustes(ruta: Path) -> Ajustes:
    """Lee `silice.toml`. Falta → valores por defecto. Dañado → valores por defecto y un aviso:
    nunca la red encendida."""
    if not ruta.exists():
        return Ajustes()
    try:
        datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        return Ajustes(
            avisos=(
                f"No se pudo leer {ruta.name} ({type(error).__name__}); se usan los valores por "
                "defecto: red local apagada y API apagada.",
            )
        )
    avisos: list[str] = []
    servidor, api = _tabla(datos, "servidor"), _tabla(datos, "api")
    interfaz, reg = _tabla(datos, "interfaz"), _tabla(datos, "registro")
    puerto = _puerto(servidor.get("puerto"), PUERTO_STREAMLIT, "la interfaz", avisos)
    puerto_api = _puerto(api.get("puerto"), PUERTO_API, "la API", avisos)
    if puerto_api == puerto:
        avisos.append("La interfaz y la API no pueden usar el mismo puerto; la API vuelve a 8000.")
        puerto_api = PUERTO_API
    red_local = _booleano(servidor.get("red_local"), "red_local", avisos)
    direccion = servidor.get("direccion", "")
    if red_local and not (isinstance(direccion, str) and _direccion_valida(direccion)):
        avisos.append(
            f"La dirección de la red local ({direccion!r}) no es una IP privada IPv4; la red local "
            "queda apagada."
        )
        red_local, direccion = False, ""
    nivel = str(reg.get("nivel", "INFO")).upper()
    if nivel not in NIVELES_DE_REGISTRO:
        avisos.append(f"El nivel de registro {nivel!r} no existe; se usa INFO.")
        nivel = "INFO"
    return Ajustes(
        puerto=puerto,
        red_local=red_local,
        direccion=direccion if red_local else "",
        api_activa=_booleano(api.get("activa"), "api.activa", avisos),
        puerto_api=puerto_api,
        mostrar_investigacion=_booleano(
            interfaz.get("mostrar_investigacion"), "mostrar_investigacion", avisos
        ),
        nivel_registro=nivel,
        avisos=tuple(avisos),
    )


def guardar_ajustes(ruta: Path, ajustes: Ajustes) -> None:
    """Escribe `silice.toml` completo y con comentarios, de golpe (archivo temporal + reemplazo)."""
    texto = (
        "[servidor]\n"
        f"puerto = {ajustes.puerto}\n"
        f"red_local = {str(ajustes.red_local).lower()}        # true: escucha en la IP de abajo\n"
        f'direccion = "{ajustes.direccion}"         # IP de la interfaz elegida; nunca 0.0.0.0\n'
        "[api]\n"
        f"activa = {str(ajustes.api_activa).lower()}\n"
        f"puerto = {ajustes.puerto_api}\n"
        "[interfaz]\n"
        f"mostrar_investigacion = {str(ajustes.mostrar_investigacion).lower()}"
        "   # false = modo entrega (RS5-9)\n"
        "[registro]\n"
        f'nivel = "{ajustes.nivel_registro}"\n'
    )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(texto, encoding="utf-8", newline="\n")
    temporal.replace(ruta)
```
(`replace` de `dataclasses` no se usa en el módulo; omitir esa importación.)

`tests/conftest.py`, la fixture `_datos_de_silice_temporales` (de la 0.6.0) pasa a:
```python
@pytest.fixture(autouse=True)
def _datos_de_silice_temporales(monkeypatch, tmp_path_factory):
    """Toda prueba trabaja con carpetas temporales: nada llega a `data/casos/`, `data/respaldos/`,
    `data/instalacion.db`, `data/config/`, `data/registros/` ni `data/estado/` (spec S5 §12)."""
    carpeta = tmp_path_factory.mktemp("silice_datos")
    monkeypatch.setenv("SILICE_DATOS", str(carpeta))
    monkeypatch.setenv("SILICE_USUARIO", str(carpeta))
    monkeypatch.delenv("SILICE_INSTALACION", raising=False)
    monkeypatch.delenv("SILICE_RESPALDOS", raising=False)
```
`.gitignore`, al final:
```gitignore
# Configuración, registros y estado del servidor de desarrollo (S5-2)
data/config/
data/registros/
data/estado/
```

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_ajustes.py tests/unit/test_operacion_config.py
tests/unit/test_arquitectura_s5.py -v -W error`
y `uv run pytest -q -W error`. `uv run ruff check operacion/config.py tests/unit/test_ajustes.py
tests/conftest.py`.

- [ ] **Paso 5: Commit**
```bash
git add operacion/config.py tests/conftest.py .gitignore
git commit -m "feat(operacion): modo producto, carpetas de usuario y silice.toml validado" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Tarea 6: `operacion.red`: interfaces, reglas de cortafuegos, cliente local, túneles y UNC

**Rama:** `inc/100-s5-2-operacion`   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `operacion/red.py`
- Prueba: `tests/unit/test_red.py`

**Interfaces:**
- Consume: `operacion.config` (T5): `Ajustes`, `cargar_ajustes`, `guardar_ajustes`.
- Produce, en `operacion.red`:
  - `Interfaz(nombre: str, ip: str)` (dataclass inmutable, ordenable por `nombre`).
  - `AVISO_SIN_CIFRAR`, `AVISO_ACCESO` (textos de spec S5 §8.2).
  - `interfaces_privadas(ejecutor: Callable[[str], str] = _powershell) -> list[Interfaz]`,
    `ips_del_equipo() -> list[str]`.
  - `es_cliente_local(ip_cliente: str | None, direccion: str = "") -> bool`.
  - `ordenes_activar(programa: Path, ip: str, puertos: Sequence[int]) -> list[list[str]]`,
    `ordenes_desactivar() -> list[list[str]]`.
  - `ResultadoRed(ok: bool, mensaje: str)`, `activar(ip, *, programa, puertos, ruta_ajustes,
    interfaces, ejecutor=_ejecutar, es_admin=es_administrador) -> ResultadoRed`,
    `desactivar(*, ruta_ajustes, ejecutor=_ejecutar, es_admin=es_administrador) -> ResultadoRed`.
  - `es_administrador() -> bool`, `relanzar_elevado(argumentos: Sequence[str]) -> bool`.
  - `procesos_en_ejecucion() -> list[str]`, `tuneles_en_ejecucion(listar=procesos_en_ejecucion)
    -> list[str]`, `es_ruta_unc(ruta: str) -> bool`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_red.py`:
```python
"""Red local, cortafuegos y cliente local (RF-98; spec S5 §8.2). Nada ejecuta netsh de verdad."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from operacion import config, red
from operacion.red import Interfaz

JSON = (
    '[{"InterfaceAlias":"Ethernet","IPAddress":"192.168.1.20"},'
    '{"InterfaceAlias":"Loopback Pseudo-Interface 1","IPAddress":"127.0.0.1"},'
    '{"InterfaceAlias":"Wi-Fi","IPAddress":"169.254.3.4"},'
    '{"InterfaceAlias":"VPN publica","IPAddress":"8.8.8.8"},'
    '{"InterfaceAlias":"Docker","IPAddress":"172.20.0.1"}]'
)
PYTHON = Path(r"C:\Prueba Sílice\Programa ñ\python\python.exe")


def test_interfaces_privadas_filtra_publicas_loopback_y_link_local() -> None:
    assert red.interfaces_privadas(lambda _: JSON) == [
        Interfaz("Docker", "172.20.0.1"),
        Interfaz("Ethernet", "192.168.1.20"),
    ]


def test_una_sola_interfaz_llega_como_objeto() -> None:
    uno = '{"InterfaceAlias":"Ethernet","IPAddress":"10.0.0.7"}'
    assert red.interfaces_privadas(lambda _: uno) == [Interfaz("Ethernet", "10.0.0.7")]


def test_si_powershell_falla_se_usa_el_nombre_del_equipo(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(_: str) -> str:
        raise OSError("sin powershell")

    monkeypatch.setattr(
        red.socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("10.0.0.7", 0)), (2, 1, 6, "", ("127.0.1.1", 0))],
    )
    assert [i.ip for i in red.interfaces_privadas(falla)] == ["10.0.0.7"]


def test_ordenes_netsh_exactas() -> None:
    ordenes = red.ordenes_activar(PYTHON, "192.168.1.20", [8501, 8000, 8501])
    assert ordenes == [
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name=Silice red local TCP {p}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={p}",
            "localip=192.168.1.20",
            "remoteip=localsubnet",
            "profile=private",
            f"program={PYTHON}",
            "enable=yes",
        ]
        for p in (8000, 8501)
    ]


def test_ninguna_orden_abre_a_todas_las_interfaces_ni_a_todos_los_perfiles() -> None:
    for orden in red.ordenes_activar(PYTHON, "10.0.0.5", [8501]):
        plano = " ".join(orden)
        assert "0.0.0.0" not in plano and "localip=any" not in plano
        assert "profile=private" in plano and "remoteip=localsubnet" in plano


def test_desactivar_borra_por_nombre_con_comodin() -> None:
    (orden,) = red.ordenes_desactivar()
    assert orden[0] == "powershell.exe" and "Silice red local*" in orden[-1]
    assert "Remove-NetFirewallRule" in orden[-1]


@pytest.mark.parametrize(
    ("ip", "direccion", "esperado"),
    [
        ("127.0.0.1", "", True),
        ("127.5.5.5", "", True),
        ("::1", "", True),
        ("::ffff:127.0.0.1", "", True),
        ("192.168.1.20", "192.168.1.20", True),
        ("192.168.1.21", "192.168.1.20", False),
        ("192.168.1.20", "", False),
        ("8.8.8.8", "8.8.8.8", False),
        ("::ffff:8.8.8.8", "", False),
        (None, "192.168.1.20", False),
        ("", "", False),
        ("no-es-una-ip", "no-es-una-ip", False),
    ],
)
def test_es_cliente_local(ip, direccion: str, esperado: bool) -> None:
    assert red.es_cliente_local(ip, direccion) is esperado


@pytest.mark.parametrize("ip", ["127.0.0.1", "::1", "192.168.1.5", "8.8.8.8", "10.0.0.1"])
def test_coincide_con_la_regla_de_s3_para_el_bucle_local(ip: str) -> None:
    from seguridad.red import es_local

    assert red.es_cliente_local(ip, "") == es_local(ip)


def test_tuneles_conocidos_en_ejecucion() -> None:
    listar = lambda: ["python.exe", "cloudflared.exe", "NGROK.EXE", "chrome.exe"]  # noqa: E731
    assert red.tuneles_en_ejecucion(listar) == ["cloudflared", "ngrok"]
    assert red.tuneles_en_ejecucion(lambda: ["python.exe"]) == []


@pytest.mark.parametrize(
    ("ruta", "unc"),
    [
        (r"\\equipo\x\a.db", True),
        ("//servidor/x", True),
        (r"\\?\UNC\servidor\x", True),
        (r"C:\Users\x", False),
        (r"\\?\C:\x", False),
        ("relativa/x", False),
    ],
)
def test_es_ruta_unc(ruta: str, unc: bool) -> None:
    assert red.es_ruta_unc(ruta) is unc


def _ejecutor(codigos: list[int], gastadas: list[list[str]]):
    def ejecutar(orden: list[str]) -> subprocess.CompletedProcess[str]:
        gastadas.append(orden)
        return subprocess.CompletedProcess(orden, codigos.pop(0), stdout="", stderr="fallo netsh")

    return ejecutar


def test_activar_sin_permisos_no_cambia_nada(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    gastadas: list[list[str]] = []
    resultado = red.activar(
        "192.168.1.20",
        programa=PYTHON,
        puertos=[8501],
        ruta_ajustes=ruta,
        interfaces=[Interfaz("Ethernet", "192.168.1.20")],
        ejecutor=_ejecutor([], gastadas),
        es_admin=lambda: False,
    )
    assert resultado.ok is False and "administrador" in resultado.mensaje
    assert gastadas == [] and not ruta.exists()


def test_activar_con_una_ip_que_no_es_del_equipo_se_rechaza(tmp_path: Path) -> None:
    resultado = red.activar(
        "10.9.9.9",
        programa=PYTHON,
        puertos=[8501],
        ruta_ajustes=tmp_path / "s.toml",
        interfaces=[Interfaz("Ethernet", "192.168.1.20")],
        ejecutor=_ejecutor([], []),
        es_admin=lambda: True,
    )
    assert resultado.ok is False and "10.9.9.9" in resultado.mensaje


def test_activar_guarda_la_ip_y_avisa_sin_cifrar(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    gastadas: list[list[str]] = []
    resultado = red.activar(
        "192.168.1.20",
        programa=PYTHON,
        puertos=[8501, 8000],
        ruta_ajustes=ruta,
        interfaces=[Interfaz("Ethernet", "192.168.1.20")],
        ejecutor=_ejecutor([0, 0], gastadas),
        es_admin=lambda: True,
    )
    ajustes = config.cargar_ajustes(ruta)
    assert resultado.ok and ajustes.red_local and ajustes.direccion == "192.168.1.20"
    assert red.AVISO_SIN_CIFRAR in resultado.mensaje and len(gastadas) == 2


def test_si_una_regla_falla_se_deshace_todo_y_los_ajustes_quedan_igual(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    gastadas: list[list[str]] = []
    resultado = red.activar(
        "192.168.1.20",
        programa=PYTHON,
        puertos=[8501, 8000],
        ruta_ajustes=ruta,
        interfaces=[Interfaz("Ethernet", "192.168.1.20")],
        ejecutor=_ejecutor([0, 1, 0], gastadas),
        es_admin=lambda: True,
    )
    assert resultado.ok is False and "fallo netsh" in resultado.mensaje
    assert gastadas[-1][0] == "powershell.exe"  # se borraron las reglas creadas
    assert config.cargar_ajustes(ruta).red_local is False


def test_desactivar_borra_las_reglas_y_apaga_la_red(tmp_path: Path) -> None:
    ruta = tmp_path / "silice.toml"
    config.guardar_ajustes(ruta, config.Ajustes(red_local=True, direccion="192.168.1.20"))
    resultado = red.desactivar(
        ruta_ajustes=ruta, ejecutor=_ejecutor([0], []), es_admin=lambda: True
    )
    ajustes = config.cargar_ajustes(ruta)
    assert resultado.ok and ajustes.red_local is False and ajustes.direccion == ""
```

- [ ] **Paso 2: Correrla y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_red.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'operacion.red'`.
```bash
git add tests/unit/test_red.py
git commit -m "test(operacion): interfaces, reglas netsh y cliente local (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/red.py`:
```python
"""Red local de Sílice: interfaces, cortafuegos y quién es «el propio equipo» (RF-98; spec S5 §8.2).

Apagada por defecto. Al activarla, Streamlit y Uvicorn escuchan en la IP **explícita** de la
interfaz elegida (nunca en todas) y el cortafuegos de Windows solo deja entrar a esa IP, a la
subred local y al perfil Privado. Sin TLS: el aviso lo dice. Solo IPv4 en la 1.0.0.
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from operacion import config

AVISO_SIN_CIFRAR = (
    "Sílice quedará visible para los equipos de esta red. Las contraseñas viajan sin cifrar "
    "(sin TLS): úselo solo en una red de confianza."
)
AVISO_ACCESO = "Esta conexión no está cifrada. Use Sílice solo en una red de confianza."
PREFIJO_REGLA = "Silice red local"
TUNELES_CONOCIDOS = ("cloudflared", "ngrok", "frpc")
_CONSULTA = (
    "Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias,IPAddress "
    "| ConvertTo-Json -Compress"
)


@dataclass(frozen=True, slots=True, order=True)
class Interfaz:
    nombre: str
    ip: str


def _powershell(comando: str) -> str:
    resultado = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", comando],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    return resultado.stdout


def _es_privada(texto: str) -> bool:
    try:
        ip = ipaddress.ip_address(texto)
    except ValueError:
        return False
    return ip.version == 4 and ip.is_private and not (ip.is_loopback or ip.is_link_local)


def ips_del_equipo() -> list[str]:
    """Todas las IPv4 que el equipo tiene hoy (para saber si la IP guardada sigue existiendo)."""
    try:
        bruto = _powershell(_CONSULTA)
        crudo = json.loads(bruto) if bruto.strip() else []
        crudo = [crudo] if isinstance(crudo, dict) else crudo
        ips = [str(fila["IPAddress"]) for fila in crudo]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        ips = []
    if not ips:
        ips = _ips_por_nombre_de_equipo()
    return sorted({*ips, "127.0.0.1"})


def _ips_por_nombre_de_equipo() -> list[str]:
    try:
        filas = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    return sorted({str(fila[4][0]) for fila in filas})


def interfaces_privadas(ejecutor: Callable[[str], str] = _powershell) -> list[Interfaz]:
    """Las interfaces IPv4 con dirección privada (sin bucle local ni enlace local), por nombre."""
    try:
        bruto = ejecutor(_CONSULTA)
        crudo = json.loads(bruto) if bruto.strip() else []
        crudo = [crudo] if isinstance(crudo, dict) else crudo
        halladas = [Interfaz(str(f["InterfaceAlias"]), str(f["IPAddress"])) for f in crudo]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        halladas = [Interfaz("(sin nombre)", ip) for ip in _ips_por_nombre_de_equipo()]
    return sorted(i for i in halladas if _es_privada(i.ip))


def _ip(texto: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    if not texto:
        return None
    try:
        ip = ipaddress.ip_address(texto)
    except ValueError:
        return None
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def es_cliente_local(ip_cliente: str | None, direccion: str = "") -> bool:
    """«Es el propio equipo»: bucle local o la IP de la interfaz elegida, que solo tiene el
    servidor (RV-15). Una IP ilegible o ausente se trata como remota."""
    ip = _ip(ip_cliente)
    if ip is None:
        return False
    if ip.is_loopback:
        return True
    propia = _ip(direccion)
    return propia is not None and propia.is_private and not propia.is_unspecified and ip == propia


def _nombre_regla(puerto: int) -> str:
    return f"{PREFIJO_REGLA} TCP {puerto}"


def ordenes_activar(programa: Path, ip: str, puertos: Sequence[int]) -> list[list[str]]:
    return [
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={_nombre_regla(p)}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={p}",
            f"localip={ip}",
            "remoteip=localsubnet",
            "profile=private",
            f"program={programa}",
            "enable=yes",
        ]
        for p in sorted(set(puertos))
    ]


def ordenes_desactivar() -> list[list[str]]:
    comando = (
        f"Get-NetFirewallRule -DisplayName '{PREFIJO_REGLA}*' -ErrorAction SilentlyContinue "
        "| Remove-NetFirewallRule"
    )
    return [["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", comando]]


def es_administrador() -> bool:
    if os.name != "nt":
        return os.geteuid() == 0  # type: ignore[attr-defined]
    import ctypes

    return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]


def relanzar_elevado(argumentos: Sequence[str]) -> bool:
    """Pide a Windows (UAC) abrir `python -m operacion <argumentos>` con permisos de
    administrador en una ventana nueva. `True` si el usuario aceptó."""
    import ctypes

    parametros = subprocess.list2cmdline(
        ["-E", "-s", "-B", "-X", "utf8", "-m", "operacion", *argumentos]
    )
    codigo = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
        None, "runas", sys.executable, parametros, str(config.RAIZ), 1
    )
    return int(codigo) > 32


def _ejecutar(orden: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        orden,
        capture_output=True,
        text=True,
        encoding="oem" if os.name == "nt" else "utf-8",
        errors="replace",
        check=False,
    )


@dataclass(frozen=True, slots=True)
class ResultadoRed:
    ok: bool
    mensaje: str


_SIN_PERMISOS = (
    "Cambiar la red local necesita permisos de administrador de Windows. No se cambió nada: use "
    "el acceso «Sílice: red local (administrador)» y acepte el aviso."
)


def activar(
    ip: str,
    *,
    programa: Path,
    puertos: Sequence[int],
    ruta_ajustes: Path,
    interfaces: Sequence[Interfaz],
    ejecutor: Callable[[list[str]], subprocess.CompletedProcess[str]] = _ejecutar,
    es_admin: Callable[[], bool] = es_administrador,
) -> ResultadoRed:
    if ip not in {i.ip for i in interfaces}:
        return ResultadoRed(
            False, f"La IP {ip} no pertenece a ninguna interfaz privada del equipo."
        )
    if not es_admin():
        return ResultadoRed(False, _SIN_PERMISOS)
    for orden in ordenes_activar(programa, ip, puertos):
        resultado = ejecutor(orden)
        if resultado.returncode != 0:
            for deshacer in ordenes_desactivar():
                ejecutor(deshacer)
            detalle = (resultado.stderr or resultado.stdout or "").strip()
            return ResultadoRed(
                False, f"El cortafuegos rechazó la regla ({detalle}). No se activó."
            )
    actuales = config.cargar_ajustes(ruta_ajustes)
    config.guardar_ajustes(ruta_ajustes, replace(actuales, red_local=True, direccion=ip, avisos=()))
    return ResultadoRed(
        True,
        f"{AVISO_SIN_CIFRAR} Reinicie Sílice. Los otros equipos abren "
        f"http://{ip}:{actuales.puerto}. "
        "La red debe estar marcada como Privada en Windows.",
    )


def desactivar(
    *,
    ruta_ajustes: Path,
    ejecutor: Callable[[list[str]], subprocess.CompletedProcess[str]] = _ejecutar,
    es_admin: Callable[[], bool] = es_administrador,
) -> ResultadoRed:
    if not es_admin():
        return ResultadoRed(False, _SIN_PERMISOS)
    for orden in ordenes_desactivar():
        ejecutor(orden)
    actuales = config.cargar_ajustes(ruta_ajustes)
    config.guardar_ajustes(
        ruta_ajustes, replace(actuales, red_local=False, direccion="", avisos=())
    )
    return ResultadoRed(True, "Red local apagada: Sílice escucha solo en este equipo. Reinícielo.")


def procesos_en_ejecucion() -> list[str]:
    orden = ["tasklist", "/FO", "CSV", "/NH"] if os.name == "nt" else ["ps", "-e", "-o", "comm="]
    try:
        salida = subprocess.run(
            orden, capture_output=True, text=True, errors="replace", check=False
        )
    except OSError:
        return []
    if os.name != "nt":
        return [Path(linea.strip()).name for linea in salida.stdout.splitlines() if linea.strip()]
    return [linea.split('","')[0].strip('"') for linea in salida.stdout.splitlines() if linea]


def tuneles_en_ejecucion(
    listar: Callable[[], list[str]] = procesos_en_ejecucion,
) -> list[str]:
    """Los túneles locales conocidos que están corriendo: anulan el filtro de IP (spec S5 §8.2)."""
    nombres = {Path(p).stem.lower() for p in listar()}
    return [t for t in TUNELES_CONOCIDOS if t in nombres]


def es_ruta_unc(ruta: str) -> bool:
    texto = ruta.replace("/", "\\")
    if texto.startswith("\\\\?\\"):
        return texto[4:].upper().startswith("UNC\\")
    return texto.startswith("\\\\")
```

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_red.py tests/unit/test_arquitectura_s5.py -v -W error` y
`uv run ruff check operacion/red.py tests/unit/test_red.py`.

- [ ] **Paso 5: Commit y PR (cierra `inc/100-s5-2-operacion`)**
```bash
git add operacion/red.py
git commit -m "feat(operacion): red local con IP explicita, reglas netsh y cliente local" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-2-operacion
gh pr create --base main --head inc/100-s5-2-operacion \
  --title "S5-2: version, registro, silice.toml y red" --body-file -
```

---

### Tarea 7: `operacion.lanzador`: opciones fijas, arrancar, parar y una sola instancia

**Rama:** `inc/100-s5-2-lanzador` (sale de `origin/main` con T4–T6 fusionadas)   **Rol:**
sf-ingeniero-adaptadores
**Archivos:**
- Crear: `operacion/lanzador.py`
- Prueba: `tests/unit/test_lanzador.py`, `tests/integration/test_arranque_real.py`

**Interfaces:**
- Consume: `operacion.config` (T5), `operacion.red` (T6), `operacion.registro` (T4),
  `operacion.base_datos.preparar_base`, `Destino`, `ErrorDeBase` (A2).
- Produce, en `operacion.lanzador`:
  - `LOOPBACK = "127.0.0.1"`, `BANDERAS_PYTHON = ("-E", "-s", "-B", "-X", "utf8")`,
    `OPCIONES_FIJAS: tuple[tuple[str, str], ...]`.
  - `elegir_direccion(ajustes: Ajustes, ips_locales: Iterable[str]) -> tuple[str, tuple[str, ...]]`.
  - `opciones_streamlit(direccion: str, puerto: int) -> list[str]`,
    `orden_streamlit(python: Path, direccion: str, puerto: int) -> list[str]`,
    `orden_uvicorn(python: Path, direccion: str, puerto: int) -> list[str]`.
  - `entorno_hijos(ajustes, direccion, entorno=None, *, base=None) -> dict[str, str]`,
    `variables_de_similitud(raiz: Path | None = None) -> dict[str, str]`.
  - `EstadoServidor(pids, direccion, puerto, puerto_api, inicio)`, `leer_estado(entorno=None)`,
    `escribir_estado(estado, entorno=None)`, `borrar_estado(entorno=None)`.
  - `hay_instancia(entorno=None, *, sonda=...) -> bool`,
    `arrancar(entorno=None, *, sin_navegador=False, lanzar=..., sonda=..., abrir=..., ips=...,
    tuneles=..., puerto_libre=..., dormir=..., reloj=..., salida=print) -> int`,
    `parar(entorno=None, *, sonda=..., matar=..., dormir=..., reloj=..., salida=print) -> int`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_lanzador.py`:
```python
"""Arranque y parada (RF-98; spec S5 §5.4, §8.1 y §10.1). Ningún proceso real."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from operacion import config, lanzador, registro
from operacion.config import Ajustes

PYTHON = Path("python.exe")
PRIVADA = "192.168.1.20"


@pytest.mark.parametrize(
    "ajustes",
    [
        Ajustes(),
        Ajustes(red_local=True, direccion="0.0.0.0"),
        Ajustes(red_local=True, direccion="::"),
        Ajustes(red_local=True, direccion=""),
        Ajustes(red_local=True, direccion=PRIVADA),
        Ajustes(red_local=True, direccion="10.9.9.9", api_activa=True),
        Ajustes(api_activa=True),
    ],
)
@pytest.mark.parametrize("ips", [[], ["127.0.0.1"], [PRIVADA, "127.0.0.1"], ["0.0.0.0"]])
def test_ninguna_configuracion_produce_0_0_0_0(ajustes: Ajustes, ips: list[str]) -> None:
    direccion, _ = lanzador.elegir_direccion(ajustes, ips)
    ordenes = [
        lanzador.orden_streamlit(PYTHON, direccion, ajustes.puerto),
        lanzador.orden_uvicorn(PYTHON, direccion, ajustes.puerto_api),
    ]
    for orden in ordenes:
        assert "0.0.0.0" not in " ".join(orden) and "::" not in orden
    assert direccion in {"127.0.0.1", PRIVADA}


def test_la_ip_elegida_se_usa_solo_si_sigue_existiendo() -> None:
    ajustes = Ajustes(red_local=True, direccion=PRIVADA)
    assert lanzador.elegir_direccion(ajustes, [PRIVADA, "127.0.0.1"]) == (PRIVADA, ())
    direccion, avisos = lanzador.elegir_direccion(ajustes, ["10.0.0.4", "127.0.0.1"])
    assert direccion == "127.0.0.1" and PRIVADA in avisos[0] and "127.0.0.1" in avisos[0]


def test_con_la_red_apagada_es_siempre_el_bucle_local() -> None:
    assert lanzador.elegir_direccion(Ajustes(), [PRIVADA]) == ("127.0.0.1", ())


def test_las_opciones_fijas_van_en_la_orden_de_streamlit() -> None:
    orden = lanzador.orden_streamlit(PYTHON, PRIVADA, 8600)
    assert orden[:10] == [
        "python.exe",
        "-E",
        "-s",
        "-B",
        "-X",
        "utf8",
        "-m",
        "streamlit",
        "run",
        "ui/app.py",
    ]
    pares = dict(zip(orden[10::2], orden[11::2], strict=True))
    assert pares == {
        "--server.address": PRIVADA,
        "--browser.serverAddress": PRIVADA,
        "--server.port": "8600",
        "--browser.serverPort": "8600",
        "--server.headless": "true",
        "--server.fileWatcherType": "none",
        "--server.runOnSave": "false",
        "--browser.gatherUsageStats": "false",
        "--client.showErrorDetails": "none",
        "--client.toolbarMode": "minimal",
        "--server.maxUploadSize": "20",
        "--global.developmentMode": "false",
        "--server.enableCORS": "true",
        "--server.enableXsrfProtection": "true",
    }


def test_uvicorn_escucha_en_la_misma_direccion_y_sin_registro_de_accesos() -> None:
    orden = lanzador.orden_uvicorn(PYTHON, PRIVADA, 8010)
    assert orden[6:9] == ["-m", "uvicorn", "api.main:app"]
    assert orden[orden.index("--host") + 1] == PRIVADA
    assert orden[orden.index("--port") + 1] == "8010"
    assert "--no-access-log" in orden


def test_el_entorno_de_los_hijos(tmp_path: Path) -> None:
    base = {
        "PATH": "x",
        "STREAMLIT_SERVER_ADDRESS": "0.0.0.0",
        "PYTHONPATH": "z",
        "VIRTUAL_ENV": "v",
    }
    entorno = {config.VARIABLE_DATOS: str(tmp_path / "d"), config.VARIABLE_USUARIO: str(tmp_path)}
    env = lanzador.entorno_hijos(Ajustes(), "127.0.0.1", entorno, base=base)
    caso = (tmp_path / "d" / "casos" / "silice.db").resolve()
    assert env["SILICE_CASO"] == str(caso)
    assert env["APU_BASE"] == f"sqlite:///{caso.as_posix()}"
    assert env["SILICE_DATOS"] == str((tmp_path / "d").resolve())
    assert env["SILICE_INSTALACION"] == str((tmp_path / "d" / "instalacion.db").resolve())
    assert env["SILICE_DIRECCION"] == "127.0.0.1" and env["SILICE_MODO_ENTREGA"] == "1"
    assert env["HF_HUB_OFFLINE"] == "1" and env["TRANSFORMERS_OFFLINE"] == "1"
    assert env["PATH"] == "x"
    assert not any(k.startswith(("STREAMLIT_", "PYTHON")) or k == "VIRTUAL_ENV" for k in env)
    abierto = lanzador.entorno_hijos(
        Ajustes(mostrar_investigacion=True), "127.0.0.1", entorno, base=base
    )
    assert "SILICE_MODO_ENTREGA" not in abierto


@dataclass
class Hijo:
    pid: int
    stdout: list[str] = field(default_factory=lambda: ["listo\n"])
    vivo: bool = True
    terminado: bool = False

    def poll(self) -> int | None:
        return None if self.vivo else 0

    def terminate(self) -> None:
        self.terminado, self.vivo = True, False

    def kill(self) -> None:
        self.terminate()

    def wait(self, timeout: float | None = None) -> int:
        return 0


class Escenario:
    """Los efectos de `arrancar` sustituidos: se anota qué se llamó y con qué."""

    def __init__(self, salud: list[bool] | None = None, vivir_ciclos: int = 1) -> None:
        self.lanzados: list[list[str]] = []
        self.hijos: list[Hijo] = []
        self.abiertas: list[str] = []
        self.salida: list[str] = []
        self.salud = list(salud if salud is not None else [True])
        self.ciclos = vivir_ciclos

    def lanzar(self, orden, entorno, cwd):
        self.lanzados.append(list(orden))
        hijo = Hijo(pid=5000 + len(self.hijos))
        self.hijos.append(hijo)
        return hijo

    def sonda(self, url: str) -> bool:
        return self.salud.pop(0) if len(self.salud) > 1 else self.salud[0]

    def dormir(self, _s: float) -> None:
        self.ciclos -= 1
        if self.ciclos <= 0:
            for hijo in self.hijos:
                hijo.vivo = False

    def correr(self, entorno=None, **extra) -> int:
        return lanzador.arrancar(
            entorno,
            lanzar=self.lanzar,
            sonda=self.sonda,
            abrir=self.abiertas.append,
            ips=lambda: ["127.0.0.1", PRIVADA],
            tuneles=extra.pop("tuneles", lambda: []),
            puerto_libre=extra.pop("puerto_libre", lambda d, p: True),
            dormir=self.dormir,
            reloj=iter(range(0, 1000, 1)).__next__,
            salida=self.salida.append,
            **extra,
        )


@pytest.fixture
def entorno(tmp_path: Path) -> dict[str, str]:
    return {config.VARIABLE_DATOS: str(tmp_path / "datos"), config.VARIABLE_USUARIO: str(tmp_path)}


def test_arrancar_prepara_las_bases_lanza_streamlit_y_abre_el_navegador(entorno) -> None:
    escenario = Escenario(salud=[True])
    assert escenario.correr(entorno) == 0
    assert (
        config.ruta_instalacion(entorno).exists() and config.ruta_caso_por_defecto(entorno).exists()
    )
    assert len(escenario.lanzados) == 1 and "streamlit" in escenario.lanzados[0]
    assert escenario.abiertas == ["http://127.0.0.1:8501"]
    assert config.ruta_ajustes(entorno).exists()  # se creó con los valores por defecto
    assert lanzador.leer_estado(entorno) is None  # al salir se limpia


def test_sin_navegador_no_abre_nada(entorno) -> None:
    escenario = Escenario()
    assert escenario.correr(entorno, sin_navegador=True) == 0 and escenario.abiertas == []


def test_con_la_api_activa_lanza_uvicorn_en_la_misma_direccion(entorno) -> None:
    config.guardar_ajustes(config.ruta_ajustes(entorno), Ajustes(api_activa=True))
    escenario = Escenario()
    assert escenario.correr(entorno) == 0
    assert len(escenario.lanzados) == 2 and "uvicorn" in escenario.lanzados[1]


def test_una_sola_instancia_abre_el_navegador_y_no_lanza_otra(entorno) -> None:
    lanzador.escribir_estado(
        lanzador.EstadoServidor((1, 2), "127.0.0.1", 8501, None, "ayer"), entorno
    )
    escenario = Escenario(salud=[True])
    assert escenario.correr(entorno) == 0
    assert escenario.lanzados == [] and escenario.abiertas == ["http://127.0.0.1:8501"]


def test_un_estado_huerfano_se_borra_y_se_arranca(entorno) -> None:
    lanzador.escribir_estado(
        lanzador.EstadoServidor((1, 2), "127.0.0.1", 8501, None, "ayer"), entorno
    )
    escenario = Escenario(salud=[False, True])
    assert escenario.correr(entorno) == 0 and len(escenario.lanzados) == 1


def test_puerto_ocupado_da_mensaje_con_el_puerto_y_no_lanza(entorno) -> None:
    escenario = Escenario()
    assert escenario.correr(entorno, puerto_libre=lambda d, p: False) == 1
    assert escenario.lanzados == []
    assert "8501" in " ".join(escenario.salida) and "silice.toml" in " ".join(escenario.salida)


def test_si_no_responde_en_el_plazo_se_detiene_todo(entorno) -> None:
    escenario = Escenario(salud=[False], vivir_ciclos=10_000)
    assert escenario.correr(entorno) == 1
    assert all(h.terminado for h in escenario.hijos) and lanzador.leer_estado(entorno) is None
    assert "60" in " ".join(escenario.salida)


def test_una_base_que_no_se_puede_preparar_detiene_el_arranque(entorno) -> None:
    config.ruta_instalacion(entorno).parent.mkdir(parents=True)
    config.ruta_instalacion(entorno).write_bytes(b"esto no es sqlite" * 100)
    escenario = Escenario()
    assert escenario.correr(entorno) == 1 and escenario.lanzados == []
    assert escenario.salida, "debe explicar qué pasó"


def test_un_tunel_en_ejecucion_se_avisa_y_se_arranca(entorno) -> None:
    escenario = Escenario()
    assert escenario.correr(entorno, tuneles=lambda: ["cloudflared"]) == 0
    assert "cloudflared" in " ".join(escenario.salida)


def test_el_codigo_de_instalacion_se_muestra_y_no_llega_al_registro(entorno) -> None:
    codigo = config.ruta_codigo_instalacion(entorno)
    codigo.parent.mkdir(parents=True, exist_ok=True)
    codigo.write_text("K7QFM9XRA2PTW4HNC8DV\n", encoding="utf-8")
    escenario = Escenario()
    try:
        assert escenario.correr(entorno) == 0
        assert any("K7QFM9XRA2PTW4HNC8DV" in linea for linea in escenario.salida)
        logging.getLogger(registro.NOMBRE_LOGGER).error("código K7QFM9XRA2PTW4HNC8DV")
        texto = (config.carpeta_registros(entorno) / "silice.log").read_text(encoding="utf-8")
        assert "K7QFM9XRA2PTW4HNC8DV" not in texto
    finally:
        registro.olvidar_secretos()
        for manejador in list(logging.getLogger(registro.NOMBRE_LOGGER).handlers):
            manejador.close()


def test_parar_no_mata_nada_si_la_salud_no_responde(entorno) -> None:
    """PID reutilizado: un estado viejo no autoriza a matar un proceso ajeno."""
    lanzador.escribir_estado(
        lanzador.EstadoServidor((4242, 4243), "127.0.0.1", 8501, None, "x"), entorno
    )
    muertos: list[int] = []
    salida: list[str] = []
    codigo = lanzador.parar(
        entorno, sonda=lambda url: False, matar=muertos.append, salida=salida.append
    )
    assert codigo == 0 and muertos == [] and lanzador.leer_estado(entorno) is None


def test_parar_mata_los_hijos_antes_que_el_lanzador(entorno) -> None:
    lanzador.escribir_estado(
        lanzador.EstadoServidor((100, 200, 300), "127.0.0.1", 8501, None, "x"), entorno
    )
    respuestas = iter([True, True, False])
    muertos: list[int] = []
    codigo = lanzador.parar(
        entorno,
        sonda=lambda url: next(respuestas),
        matar=muertos.append,
        dormir=lambda s: None,
        salida=lambda t: None,
    )
    assert codigo == 0 and muertos == [300, 200, 100] and lanzador.leer_estado(entorno) is None


def test_sin_estado_parar_no_hace_nada(entorno) -> None:
    salida: list[str] = []
    assert lanzador.parar(entorno, salida=salida.append) == 0 and "no está en marcha" in salida[0]


def test_un_estado_ilegible_cuenta_como_ausente(entorno) -> None:
    ruta = config.ruta_estado(entorno)
    ruta.parent.mkdir(parents=True)
    ruta.write_text("{no es json", encoding="utf-8")
    assert (
        lanzador.leer_estado(entorno) is None
        and lanzador.hay_instancia(entorno, sonda=lambda u: True) is False
    )
```

`tests/integration/test_arranque_real.py`:
```python
"""Arranque real de Streamlit con las opciones del spec (confirma §10.1 y la salud de §11.2)."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from operacion import config
from operacion.config import Ajustes

RAIZ = Path(__file__).resolve().parents[2]
BANDERAS = ["-E", "-s", "-B", "-X", "utf8", "-m", "operacion"]


def _puerto_libre() -> int:
    with socket.socket() as zocalo:
        zocalo.bind(("127.0.0.1", 0))
        return int(zocalo.getsockname()[1])


def _salud(puerto: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/_stcore/health", timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


def test_arranca_en_el_bucle_local_y_se_detiene() -> None:
    puerto = _puerto_libre()
    config.guardar_ajustes(
        config.ruta_ajustes(), Ajustes(puerto=puerto, mostrar_investigacion=True)
    )
    entorno = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "STREAMLIT_"))}
    servidor = subprocess.Popen(
        [sys.executable, *BANDERAS, "arrancar", "--sin-navegador"],
        cwd=RAIZ,
        env=entorno,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        limite = time.monotonic() + 120
        while time.monotonic() < limite and not _salud(puerto) and servidor.poll() is None:
            time.sleep(1)
        assert _salud(puerto), "Streamlit no respondió: ¿rechazó alguna opción de la orden?"
        estado = config.ruta_estado().read_text(encoding="utf-8")
        assert '"direccion": "127.0.0.1"' in estado
    finally:
        parada = subprocess.run(
            [sys.executable, *BANDERAS, "parar"], cwd=RAIZ, env=entorno, check=False, timeout=60
        )
        try:
            servidor.wait(timeout=30)
        except subprocess.TimeoutExpired:
            servidor.terminate()  # solo el hijo que este mismo test lanzó
    assert parada.returncode == 0 and not _salud(puerto)
    assert not config.ruta_estado().exists()
```
(Esta prueba confirma que Streamlit 1.62 acepta cada opción de §10.1 por línea de órdenes y,
con ellas, escucha solo en `127.0.0.1`. **Contingencia:** si Streamlit rechaza
`--global.developmentMode`, quitar ese par de `OPCIONES_FIJAS`, dejar `developmentMode = false`
solo en `instalador/streamlit_config.toml` (T13) y quitarlo del diccionario de
`test_las_opciones_fijas_van_en_la_orden_de_streamlit`.)

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_lanzador.py tests/integration/test_arranque_real.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'lanzador' from 'operacion'`.
```bash
git add tests/unit/test_lanzador.py tests/integration/test_arranque_real.py
git commit -m "test(operacion): lanzador con opciones fijas, una instancia y parada segura (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/lanzador.py`:
```python
"""Arranque y parada de Sílice (RF-98; spec S5 §5.4, §8.1 y §10.1).

`python -m operacion arrancar` prepara las bases, elige la dirección (siempre el bucle local salvo
la IP explícita de la red local), lanza Streamlit (y Uvicorn si la API está activa) como procesos
hijos, espera la salud y abre el navegador. Cerrar la ventana detiene todo; `parar` lo hace desde
otro proceso. Nunca importa Streamlit ni FastAPI: solo los lanza.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from operacion import base_datos, config, red, registro

LOOPBACK = "127.0.0.1"
BANDERAS_PYTHON = ("-E", "-s", "-B", "-X", "utf8")
PLAZO_SALUD_S = 60
DIRECCIONES_PROHIBIDAS = frozenset({"", "0.0.0.0", "::"})
OPCIONES_FIJAS: tuple[tuple[str, str], ...] = (
    ("server.headless", "true"),
    ("server.fileWatcherType", "none"),
    ("server.runOnSave", "false"),
    ("browser.gatherUsageStats", "false"),
    ("client.showErrorDetails", "none"),
    ("client.toolbarMode", "minimal"),
    ("server.maxUploadSize", "20"),
    ("global.developmentMode", "false"),
    ("server.enableCORS", "true"),
    ("server.enableXsrfProtection", "true"),
)


def elegir_direccion(
    ajustes: config.Ajustes, ips_locales: Iterable[str]
) -> tuple[str, tuple[str, ...]]:
    """`127.0.0.1`, o la IP guardada si la red local está encendida y esa IP sigue existiendo."""
    if not ajustes.red_local or ajustes.direccion in DIRECCIONES_PROHIBIDAS:
        return LOOPBACK, ()
    if ajustes.direccion in set(ips_locales):
        return ajustes.direccion, ()
    return LOOPBACK, (
        f"La IP {ajustes.direccion} de la red local ya no existe en este equipo (la red cambió): "
        f"Sílice arranca solo en {LOOPBACK}. Vuelva a activar la red local para elegir otra IP.",
    )


def opciones_streamlit(direccion: str, puerto: int) -> list[str]:
    pares = [
        ("server.address", direccion),
        ("browser.serverAddress", direccion),
        ("server.port", str(puerto)),
        ("browser.serverPort", str(puerto)),
        *OPCIONES_FIJAS,
    ]
    return [parte for clave, valor in pares for parte in (f"--{clave}", valor)]


def orden_streamlit(python: Path, direccion: str, puerto: int) -> list[str]:
    return [
        str(python),
        *BANDERAS_PYTHON,
        "-m",
        "streamlit",
        "run",
        "ui/app.py",
        *opciones_streamlit(direccion, puerto),
    ]


def orden_uvicorn(python: Path, direccion: str, puerto: int) -> list[str]:
    return [
        str(python),
        *BANDERAS_PYTHON,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        direccion,
        "--port",
        str(puerto),
        "--no-access-log",
    ]


def variables_de_similitud(raiz: Path | None = None) -> dict[str, str]:
    """El módulo de similitud (si está instalado) trae su caché del modelo: sin red, nunca."""
    modelo = (raiz or config.RAIZ).parent / "modulos" / "similitud" / "hf"
    variables = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    if modelo.is_dir():
        variables["HF_HOME"] = str(modelo)
    return variables


def entorno_hijos(
    ajustes: config.Ajustes,
    direccion: str,
    entorno: Mapping[str, str] | None = None,
    *,
    base: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """El entorno de Streamlit y Uvicorn: ninguna escritura cae en la carpeta del programa y nada
    del entorno del usuario (`PYTHON*`, `STREAMLIT_*`, `VIRTUAL_ENV`) cambia su comportamiento."""
    origen = os.environ if base is None else base
    env = {
        k: v
        for k, v in origen.items()
        if not k.upper().startswith(("STREAMLIT_", "PYTHON")) and k.upper() != "VIRTUAL_ENV"
    }
    caso = config.ruta_caso_por_defecto(entorno)
    env.update(
        {
            "SILICE_DATOS": str(config.carpeta_datos(entorno)),
            "SILICE_INSTALACION": str(config.ruta_instalacion(entorno)),
            "SILICE_RESPALDOS": str(config.carpeta_respaldos(entorno)),
            "SILICE_USUARIO": str(config.carpeta_usuario(entorno)),
            "SILICE_CASO": str(caso),
            "APU_BASE": f"sqlite:///{caso.as_posix()}",
            "SILICE_DIRECCION": direccion,
            "SILICE_PRODUCTO": "1" if config.es_producto() else "0",
            **variables_de_similitud(),
        }
    )
    env.pop("SILICE_MODO_ENTREGA", None)
    if not ajustes.mostrar_investigacion:
        env["SILICE_MODO_ENTREGA"] = "1"
    return env


@dataclass(frozen=True, slots=True)
class EstadoServidor:
    pids: tuple[int, ...]
    direccion: str
    puerto: int
    puerto_api: int | None
    inicio: str


def leer_estado(entorno: Mapping[str, str] | None = None) -> EstadoServidor | None:
    try:
        datos = json.loads(config.ruta_estado(entorno).read_text(encoding="utf-8"))
        return EstadoServidor(
            tuple(int(p) for p in datos["pids"]),
            str(datos["direccion"]),
            int(datos["puerto"]),
            None if datos.get("puerto_api") is None else int(datos["puerto_api"]),
            str(datos["inicio"]),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None


def escribir_estado(estado: EstadoServidor, entorno: Mapping[str, str] | None = None) -> None:
    ruta = config.ruta_estado(entorno)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(asdict(estado), indent=2), encoding="utf-8")


def borrar_estado(entorno: Mapping[str, str] | None = None) -> None:
    config.ruta_estado(entorno).unlink(missing_ok=True)


def _url(direccion: str, puerto: int) -> str:
    return f"http://{direccion}:{puerto}"


def _sonda(url: str) -> bool:
    try:
        with urllib.request.urlopen(url + "/_stcore/health", timeout=2) as respuesta:  # noqa: S310
            return bool(respuesta.status == 200)
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _puerto_libre(direccion: str, puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as zocalo:
        try:
            zocalo.bind((direccion, puerto))
        except OSError:
            return False
    return True


def _lanzar(orden: list[str], entorno: dict[str, str], cwd: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(  # noqa: S603
        orden,
        cwd=cwd,
        env=entorno,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _matar(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def hay_instancia(
    entorno: Mapping[str, str] | None = None, *, sonda: Callable[[str], bool] = _sonda
) -> bool:
    estado = leer_estado(entorno)
    return estado is not None and sonda(_url(estado.direccion, estado.puerto))


def _terminar(procesos: Iterable[Any]) -> None:
    for proceso in procesos:
        if proceso.poll() is None:
            proceso.terminate()
    for proceso in procesos:
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()


def arrancar(
    entorno: Mapping[str, str] | None = None,
    *,
    sin_navegador: bool = False,
    lanzar: Callable[..., Any] = _lanzar,
    sonda: Callable[[str], bool] = _sonda,
    abrir: Callable[[str], Any] = webbrowser.open,
    ips: Callable[[], list[str]] = red.ips_del_equipo,
    tuneles: Callable[[], list[str]] = red.tuneles_en_ejecucion,
    puerto_libre: Callable[[str, int], bool] = _puerto_libre,
    dormir: Callable[[float], None] = time.sleep,
    reloj: Callable[[], float] = time.monotonic,
    salida: Callable[[str], Any] = print,
) -> int:
    estado = leer_estado(entorno)
    if estado is not None:
        url = _url(estado.direccion, estado.puerto)
        if sonda(url):
            salida(f"Sílice ya está en marcha: {url}")
            if not sin_navegador:
                abrir(url)
            return 0
        borrar_estado(entorno)  # un registro viejo de una instancia que ya no existe
    ruta_ajustes = config.ruta_ajustes(entorno)
    if not ruta_ajustes.exists():
        config.guardar_ajustes(ruta_ajustes, config.Ajustes())
    ajustes = config.cargar_ajustes(ruta_ajustes)
    logger = registro.configurar(config.carpeta_registros(entorno), ajustes.nivel_registro)
    avisos = list(ajustes.avisos)
    if red.es_ruta_unc(str(config.carpeta_datos(entorno))):
        avisos.append("La carpeta de datos está en una ruta de red (UNC): SQLite no es fiable ahí.")
    if encontrados := tuneles():
        avisos.append(
            f"Hay un túnel en ejecución ({', '.join(encontrados)}): anula el filtro de IP y la "
            "regla «solo desde este equipo». Ciérrelo o publique Sílice por su cuenta y riesgo."
        )
    try:
        base_datos.preparar_base(
            config.ruta_instalacion(entorno), base_datos.Destino.INSTALACION, entorno=entorno
        )
        base_datos.preparar_base(config.ruta_caso_por_defecto(entorno), entorno=entorno)
    except base_datos.ErrorDeBase as error:
        logger.error("no se pudieron preparar las bases: %s", error)
        salida(f"Sílice no arrancó: {error}")
        return 1
    codigo = config.ruta_codigo_instalacion(entorno)
    if codigo.is_file():
        texto = codigo.read_text(encoding="utf-8").strip()
        registro.registrar_secreto(texto)  # a la consola, nunca al registro
        salida(f"Código de instalación (un solo uso, para crear el primer administrador): {texto}")
    direccion, de_direccion = elegir_direccion(ajustes, ips())
    avisos.extend(de_direccion)
    for aviso in avisos:
        logger.warning("%s", aviso)
        salida(f"AVISO: {aviso}")
    puertos = [("la interfaz", ajustes.puerto)]
    if ajustes.api_activa:
        puertos.append(("la API", ajustes.puerto_api))
    for nombre, puerto in puertos:
        if not puerto_libre(direccion, puerto):
            salida(
                f"El puerto {puerto} de {nombre} lo usa otro programa. Cierre ese programa "
                f"o cambie el puerto en {ruta_ajustes}."
            )
            return 1
    python = Path(sys.executable)
    env = entorno_hijos(ajustes, direccion, entorno)
    ordenes = [("streamlit", orden_streamlit(python, direccion, ajustes.puerto))]
    if ajustes.api_activa:
        ordenes.append(("api", orden_uvicorn(python, direccion, ajustes.puerto_api)))
    procesos = []
    for nombre, orden in ordenes:
        proceso = lanzar(orden, env, config.RAIZ)
        procesos.append(proceso)
        threading.Thread(
            target=registro.copiar_salida,
            args=(proceso.stdout, logger, logging.INFO, nombre),
            daemon=True,
        ).start()
    escribir_estado(
        EstadoServidor(
            (os.getpid(), *(p.pid for p in procesos)),
            direccion,
            ajustes.puerto,
            ajustes.puerto_api if ajustes.api_activa else None,
            datetime.now().isoformat(timespec="seconds"),
        ),
        entorno,
    )
    url = _url(direccion, ajustes.puerto)
    try:
        limite = reloj() + PLAZO_SALUD_S
        while not sonda(url):
            if reloj() >= limite or any(p.poll() is not None for p in procesos):
                logger.error("Streamlit no respondió en %s s", PLAZO_SALUD_S)
                salida(
                    f"Sílice no respondió en {PLAZO_SALUD_S} s. Mire el registro en "
                    f"{config.carpeta_registros(entorno)}."
                )
                return 1
            dormir(0.5)
        salida(f"Sílice está en marcha: {url}")
        salida("Para detener Sílice, cierre esta ventana.")
        if not sin_navegador:
            abrir(url)
        while all(p.poll() is None for p in procesos):
            dormir(1)
        logger.error("un proceso de Sílice terminó solo")
        salida("Un proceso de Sílice terminó. Mire el registro y vuelva a abrir Sílice.")
    except KeyboardInterrupt:
        salida("Sílice se detuvo.")
    finally:
        _terminar(procesos)
        borrar_estado(entorno)
    return 0


def parar(
    entorno: Mapping[str, str] | None = None,
    *,
    sonda: Callable[[str], bool] = _sonda,
    matar: Callable[[int], Any] = _matar,
    dormir: Callable[[float], None] = time.sleep,
    salida: Callable[[str], Any] = print,
) -> int:
    """Detiene la instancia de `servidor.json`. Solo mata procesos si la instancia **responde**:
    un registro viejo, con PID que otro programa pudo reutilizar, no autoriza a matar nada."""
    estado = leer_estado(entorno)
    if estado is None:
        salida("Sílice no está en marcha.")
        return 0
    url = _url(estado.direccion, estado.puerto)
    if not sonda(url):
        borrar_estado(entorno)
        salida("Sílice no estaba en marcha (se limpió un registro viejo).")
        return 0
    propio = os.getpid()
    for pid in reversed(estado.pids):  # primero los hijos, el lanzador al final
        if pid != propio:
            matar(pid)
    for _ in range(20):
        if not sonda(url):
            break
        dormir(0.5)
    borrar_estado(entorno)
    salida("Sílice se detuvo.")
    return 0
```

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_lanzador.py tests/integration/test_arranque_real.py
tests/unit/test_arquitectura_s5.py -v -W error`
(la real tarda 10-60 s). `uv run ruff check operacion/lanzador.py tests/unit/test_lanzador.py
tests/integration/test_arranque_real.py`
(ruff exige partir las dos líneas de `salida(...)` que superan 100 columnas).

- [ ] **Paso 5: Commit**
```bash
git add operacion/lanzador.py
git commit -m "feat(operacion): lanzador con IP explicita, opciones fijas y parada segura" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Tarea 8: `operacion.ordenes_100`: la CLI de la 1.0.0 y la guardia de `restaurar`

**Rama:** `inc/100-s5-2-lanzador`   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `operacion/ordenes_100.py`
- Modificar: `operacion/__main__.py` (solo `_restaurar`; el registro de `ordenes_100` en `main`
  ya lo puso la Tarea 3)
- Prueba: `tests/unit/test_ordenes_100.py`

**Interfaces:**
- Consume: `operacion.lanzador` (T7), `operacion.red` (T6), `operacion.config` (T5),
  `operacion.base_datos.resolver_caso`/`preparar_base` (A2), `operacion.firma_sumas` y
  `operacion.programa` (T3, T13: se importan dentro del manejador, ver abajo).
- Produce: `ordenes_100.registrar(ordenes, tabla) -> None`; las órdenes `arrancar`, `parar`,
  `demostracion`, `red-local {activar,desactivar,estado}` y `diagnostico-similitud`; las de la
  clave y `verificar-instalador`, que T3 ya dejó registradas, quedan intactas.

> **Nota de orden.** T3 creó `operacion/ordenes_100.py` con `registrar()` y las órdenes de la
> clave. Esta tarea **agrega** a ese archivo y a esa función; no la reescribe.
> `verificar-programa` se agrega en T13 (cuando existe `operacion.programa`).

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_ordenes_100.py`:
```python
"""Órdenes de `python -m operacion` de la 1.0.0 (spec S5 §5.4, §6.5, §8.2)."""

from __future__ import annotations

import pytest

from operacion import __main__ as cli
from operacion import base_datos, config, lanzador, red


def test_arrancar_y_parar_llaman_al_lanzador(monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas: list[tuple] = []
    monkeypatch.setattr(lanzador, "arrancar", lambda **k: llamadas.append(("arrancar", k)) or 3)
    monkeypatch.setattr(lanzador, "parar", lambda **k: llamadas.append(("parar", k)) or 4)
    assert cli.main(["arrancar", "--sin-navegador"]) == 3
    assert cli.main(["parar"]) == 4
    assert llamadas == [("arrancar", {"sin_navegador": True}), ("parar", {})]


def test_restaurar_exige_silice_detenido(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path) -> None:
    monkeypatch.setattr(lanzador, "hay_instancia", lambda *a, **k: True)
    monkeypatch.setattr(
        base_datos, "restaurar_juego", lambda *a, **k: pytest.fail("no debe restaurar")
    )
    assert cli.main(["restaurar", str(tmp_path)]) == 1
    assert "deténgalo" in capsys.readouterr().err


def test_la_demostracion_prepara_el_caso_y_lo_siembra(monkeypatch, tmp_path) -> None:
    llamadas: list[list[str]] = []
    import scripts.seed_demo as seed_demo

    monkeypatch.setattr(seed_demo, "main", lambda argv: llamadas.append(list(argv)) or 0)
    assert cli.main(["demostracion"]) == 0
    destino = config.carpeta_casos() / "demostracion.db"
    assert destino.exists() and llamadas == [["--db", str(destino)]]


def test_red_local_estado_describe_la_configuracion(capsys) -> None:
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="10.0.0.5")
    )
    assert cli.main(["red-local", "estado"]) == 0
    texto = capsys.readouterr().out
    assert "encendida" in texto and "10.0.0.5" in texto and "8501" in texto


def test_red_local_activar_con_ip_pide_confirmacion_y_activa(monkeypatch, capsys) -> None:
    visto: dict = {}
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [red.Interfaz("Ethernet", "10.0.0.5")])
    monkeypatch.setattr(red, "es_administrador", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "s")
    monkeypatch.setattr(
        red,
        "activar",
        lambda ip, **k: visto.update(ip=ip, **k) or red.ResultadoRed(True, "listo"),
    )
    assert cli.main(["red-local", "activar", "--ip", "10.0.0.5"]) == 0
    assert visto["ip"] == "10.0.0.5" and visto["puertos"] == [8501]
    assert red.AVISO_SIN_CIFRAR in capsys.readouterr().out


def test_red_local_activar_si_no_se_confirma_no_cambia_nada(monkeypatch) -> None:
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [red.Interfaz("Ethernet", "10.0.0.5")])
    monkeypatch.setattr(red, "es_administrador", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(red, "activar", lambda *a, **k: pytest.fail("no debe activar"))
    assert cli.main(["red-local", "activar", "--ip", "10.0.0.5"]) == 1


def test_red_local_activar_sin_permisos_relanza_elevado(monkeypatch) -> None:
    pedidos: list[list[str]] = []
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [red.Interfaz("Ethernet", "10.0.0.5")])
    monkeypatch.setattr(red, "es_administrador", lambda: False)
    monkeypatch.setattr(red, "relanzar_elevado", lambda args: pedidos.append(list(args)) or True)
    assert cli.main(["red-local", "activar"]) == 0
    assert pedidos == [["red-local", "activar", "--elevado"]]


def test_red_local_activar_sin_interfaces_privadas_lo_dice(monkeypatch, capsys) -> None:
    monkeypatch.setattr(red, "interfaces_privadas", lambda: [])
    assert cli.main(["red-local", "activar", "--si"]) == 1
    assert "ninguna interfaz" in capsys.readouterr().err


def test_el_diagnostico_de_similitud_usa_el_proponedor_sin_red(monkeypatch, capsys) -> None:
    import ml.normalization as normalizacion

    monkeypatch.setattr(lanzador, "variables_de_similitud", lambda raiz=None: {})

    class Propuesta:
        falla = None

    monkeypatch.setattr(normalizacion, "proponedor", lambda partidas: lambda texto: Propuesta())
    assert cli.main(["diagnostico-similitud"]) == 0
    assert "sin red" in capsys.readouterr().out


def test_el_diagnostico_de_similitud_falla_si_el_modelo_no_esta(monkeypatch, capsys) -> None:
    import ml.normalization as normalizacion

    monkeypatch.setattr(lanzador, "variables_de_similitud", lambda raiz=None: {})

    class Propuesta:
        falla = "ImportError: no hay sentence_transformers"

    monkeypatch.setattr(normalizacion, "proponedor", lambda partidas: lambda texto: Propuesta())
    assert cli.main(["diagnostico-similitud"]) == 1
    assert "ImportError" in capsys.readouterr().err
```

- [ ] **Paso 2: Correrla y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_ordenes_100.py -v -W error`
Esperado: FAIL con `SystemExit: 2` (`invalid choice: 'arrancar'`) en el primer caso.
```bash
git add tests/unit/test_ordenes_100.py
git commit -m "test(operacion): ordenes arrancar, parar, red-local y diagnostico (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/ordenes_100.py`, agregar las importaciones y estos manejadores (debajo de los de la clave
que dejó T3), y las líneas nuevas al final de `registrar`:
```python
import json
import os
from pathlib import Path

from operacion import base_datos, config, lanzador, red


def _arrancar(argumentos: argparse.Namespace) -> int:
    return lanzador.arrancar(sin_navegador=argumentos.sin_navegador)


def _parar(_argumentos: argparse.Namespace) -> int:
    return lanzador.parar()


def _demostracion(_argumentos: argparse.Namespace) -> int:
    ruta = base_datos.resolver_caso("demostracion")
    base_datos.preparar_base(ruta)
    from scripts.seed_demo import main as sembrar  # diferido: scripts/ viaja solo por el manifiesto

    return int(sembrar(["--db", str(ruta)]))


def _estado_red() -> int:
    ajustes = config.cargar_ajustes(config.ruta_ajustes())
    if ajustes.red_local:
        print(f"Red local: encendida en http://{ajustes.direccion}:{ajustes.puerto}")
    else:
        print(f"Red local: apagada (solo http://127.0.0.1:{ajustes.puerto})")
    print(f"API: {'activa' if ajustes.api_activa else 'apagada'} (puerto {ajustes.puerto_api})")
    return 0


def _elegir_interfaz(interfaces: list[red.Interfaz], ip: str | None) -> red.Interfaz | None:
    if ip is not None:
        return next((i for i in interfaces if i.ip == ip), red.Interfaz("(indicada)", ip))
    for numero, interfaz in enumerate(interfaces, start=1):
        print(f"  {numero}. {interfaz.nombre}  {interfaz.ip}")
    respuesta = input("Número de la interfaz de su red de confianza: ").strip()
    if respuesta.isdigit() and 1 <= int(respuesta) <= len(interfaces):
        return interfaces[int(respuesta) - 1]
    return None


def _red_local(argumentos: argparse.Namespace) -> int:
    ruta = config.ruta_ajustes()
    if argumentos.accion == "estado":
        return _estado_red()
    if argumentos.accion == "desactivar":
        resultado = red.desactivar(ruta_ajustes=ruta)
        print(resultado.mensaje, file=sys.stdout if resultado.ok else sys.stderr)
        return 0 if resultado.ok else 1
    interfaces = red.interfaces_privadas()
    if not interfaces:
        print("Este equipo no tiene ninguna interfaz con dirección privada.", file=sys.stderr)
        return 1
    if not red.es_administrador() and not argumentos.elevado:
        extra = ["--ip", argumentos.ip] if argumentos.ip else []
        return 0 if red.relanzar_elevado(["red-local", "activar", "--elevado", *extra]) else 1
    elegida = _elegir_interfaz(interfaces, argumentos.ip)
    if elegida is None:
        print("No se eligió ninguna interfaz.", file=sys.stderr)
        return 1
    print(red.AVISO_SIN_CIFRAR)
    if (
        not argumentos.si
        and input("¿Activar la red local en esa IP? (s/n): ").strip().lower() != "s"
    ):
        return 1
    ajustes = config.cargar_ajustes(ruta)
    puertos = [ajustes.puerto] + ([ajustes.puerto_api] if ajustes.api_activa else [])
    resultado = red.activar(
        elegida.ip,
        programa=Path(sys.executable),
        puertos=puertos,
        ruta_ajustes=ruta,
        interfaces=interfaces,
    )
    print(resultado.mensaje, file=sys.stdout if resultado.ok else sys.stderr)
    if argumentos.elevado:
        input("Pulse Entrar para cerrar esta ventana.")
    return 0 if resultado.ok else 1


def _diagnostico_similitud(_argumentos: argparse.Namespace) -> int:
    os.environ.update(lanzador.variables_de_similitud())
    import ml.normalization as normalizacion

    propuesta = normalizacion.proponedor({"EXC-1": "Excavación manual de zanja"})("excavar zanja")
    if propuesta.falla is not None:
        print(f"La función de similitud no está disponible: {propuesta.falla}", file=sys.stderr)
        return 1
    print("Similitud de partidas: el modelo cargó sin red.")
    return 0
```
y, dentro de `registrar`, antes del `tabla.update(...)`:
```python
    arrancar = ordenes.add_parser("arrancar", help="prepara las bases y abre Sílice")
    arrancar.add_argument("--sin-navegador", action="store_true")
    ordenes.add_parser("parar", help="detiene la instancia en marcha")
    ordenes.add_parser("demostracion", help="crea el caso de demostración (datos construidos)")
    local = ordenes.add_parser("red-local", help="activa, apaga o describe la red local")
    acciones = local.add_subparsers(dest="accion", required=True)
    activar = acciones.add_parser("activar", help="elegir una interfaz y abrir el cortafuegos")
    activar.add_argument("--ip")
    activar.add_argument("--si", action="store_true", help="no pedir confirmación")
    activar.add_argument("--elevado", action="store_true", help=argparse.SUPPRESS)
    acciones.add_parser("desactivar")
    acciones.add_parser("estado")
    ordenes.add_parser("diagnostico-similitud", help="carga el modelo de similitud sin red")
    tabla.update(
        {
            "arrancar": _arrancar, "parar": _parar, "demostracion": _demostracion,
            "red-local": _red_local, "diagnostico-similitud": _diagnostico_similitud,
        }
    )
```
(La orden `eventos` la agrega la Tarea 10, junto con el módulo que usa.)

`operacion/__main__.py`: `_restaurar` empieza por
```python
    from operacion import lanzador

    if lanzador.hay_instancia():
        print("Sílice está en marcha: deténgalo con «Detener Sílice» antes de restaurar.",
              file=sys.stderr)
        return 1
```

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_ordenes_100.py tests/integration/test_operacion_cli.py
tests/unit/test_lanzador.py -v -W error`
(`test_operacion_cli.py` es de la 0.6.0 y no se edita). `uv run ruff check operacion
tests/unit/test_ordenes_100.py`.

- [ ] **Paso 5: Commit y PR (cierra `inc/100-s5-2-lanzador`)**
```bash
git add operacion/ordenes_100.py operacion/__main__.py
git commit -m "feat(operacion): ordenes arrancar, parar, red-local y guardia de restaurar" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-2-lanzador
gh pr create --base main --head inc/100-s5-2-lanzador \
  --title "S5-2: lanzador y CLI de la 1.0.0" --body-file -
```

---
### Tarea 9: `api/proteccion.py` y `api/main.py`: clave en toda ruta, hosts y redes privadas

**Rama:** `inc/100-s5-2-api` (sale de `origin/main` con T4 fusionada; paralela a la del lanzador)
**Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `api/proteccion.py`, `tests/fixtures/claves_api.py`
- Modificar: `tests/conftest.py` (`pytest_plugins` suma `"tests.fixtures.claves_api"`);
  `api/main.py` (importaciones, creación de `app`, los `include_router`, `/salud` y la llamada
  final a `proteger`); `docs/api.json` (se regenera); los `TestClient(app)` de
  `tests/integration/test_api*.py` y de las pruebas de S3 que llaman a la API
- Prueba: `tests/integration/test_api_clave.py`, `tests/unit/test_api_proteccion.py`

**Interfaces:**
- Consume: `api.seguridad.exigir_clave_api` (A13), `operacion.version.version` (T4),
  `seguridad.claves_api.crear_clave` (solo en `tests/fixtures/claves_api.py`).
- Produce, en `api.proteccion`: `VARIABLE_DIRECCION = "SILICE_DIRECCION"`,
  `VARIABLE_PRODUCTO = "SILICE_PRODUCTO"`, `en_producto(entorno=None) -> bool`,
  `opciones_documentacion(entorno=None) -> dict[str, None]`,
  `anfitriones_permitidos(direccion: str | None) -> list[str]`,
  `ip_permitida(host: str | None) -> bool`, `SoloRedesPrivadas` (middleware ASGI),
  `proteger(app: FastAPI, entorno=None) -> None`. Rutas nuevas: `GET /salud` → `{"estado": "ok"}`.
  En `tests.fixtures.claves_api`: fixtures `clave_api` (texto `<identificador>.<secreto>`) y
  `cliente_api` (`TestClient` que llega desde `127.0.0.1` y manda la clave).

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/fixtures/claves_api.py` (el **único** sitio que conoce la forma de `seguridad.claves_api`;
si S3-4 la dejó distinta, se ajusta aquí y se anota en la bitácora):
```python
"""Adaptador de las pruebas a S3: una clave de API real en la `instalacion.db` temporal (A13)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from core.catalog import crear_motor
from operacion import config
from operacion.base_datos import Destino, preparar_base

CABECERA = "X-Silice-Clave"
ANFITRION = "http://127.0.0.1:8000"


@pytest.fixture
def clave_api() -> str:
    from seguridad import claves_api

    ruta = config.ruta_instalacion()
    preparar_base(ruta, Destino.INSTALACION)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with Session(motor) as sesion:
            identificador, secreto = claves_api.crear_clave(
                sesion, nombre="prueba de S5", creada_por=None
            )
            sesion.commit()
    finally:
        motor.dispose()
    return f"{identificador}.{secreto}"


@pytest.fixture
def cliente_api(clave_api: str) -> TestClient:
    return TestClient(
        app, base_url=ANFITRION, client=("127.0.0.1", 50000), headers={CABECERA: clave_api}
    )
```

`tests/integration/test_api_clave.py`:
```python
"""La API exige clave en toda ruta menos `/salud` y se defiende de hosts y redes ajenas
(RF-98; spec S5 §8.3). Recorre `app.routes`: una ruta nueva sin clave rompe la prueba."""

from __future__ import annotations

import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.main import app
from tests.fixtures.claves_api import ANFITRION, CABECERA

PROTEGIDAS = [
    (ruta, metodo)
    for ruta in app.routes
    if isinstance(ruta, APIRoute) and ruta.path != "/salud"
    for metodo in sorted(ruta.methods - {"HEAD", "OPTIONS"})
]


def _cliente(ip: str = "127.0.0.1", base: str = ANFITRION) -> TestClient:
    return TestClient(app, base_url=base, client=(ip, 50000), raise_server_exceptions=False)


def _ruta_concreta(ruta: APIRoute) -> str:
    return re.sub(r"\{[^}]+\}", "x", ruta.path)


def test_hay_rutas_que_proteger_y_estan_las_de_s3() -> None:
    assert len(PROTEGIDAS) >= 10
    assert any(ruta.path == "/v1/auditorias" for ruta, _ in PROTEGIDAS)


@pytest.mark.parametrize(
    ("ruta", "metodo"), PROTEGIDAS, ids=[f"{m} {r.path}" for r, m in PROTEGIDAS]
)
def test_cada_ruta_menos_salud_da_401_sin_clave(ruta: APIRoute, metodo: str) -> None:
    respuesta = _cliente().request(metodo, _ruta_concreta(ruta), json={})
    assert respuesta.status_code == 401, respuesta.text
    assert "detalle" in respuesta.json()


@pytest.mark.parametrize("clave", ["", "AB12CD34.no-es-la-clave", "sin-punto", "x" * 5000])
def test_una_clave_falsa_tampoco_pasa(clave: str) -> None:
    ruta, metodo = next((r, m) for r, m in PROTEGIDAS if m == "GET" and "{" not in r.path)
    respuesta = _cliente().request(metodo, ruta.path, headers={CABECERA: clave})
    assert respuesta.status_code == 401


def test_con_clave_valida_la_ruta_responde_sin_401_ni_403(cliente_api: TestClient) -> None:
    ruta, _ = next((r, m) for r, m in PROTEGIDAS if m == "GET" and "{" not in r.path)
    assert cliente_api.get(ruta.path).status_code not in (401, 403)


def test_salud_responde_sin_clave_y_sin_version() -> None:
    respuesta = _cliente().get("/salud")
    assert respuesta.status_code == 200 and respuesta.json() == {"estado": "ok"}


def test_ip_publica_simulada_recibe_403(clave_api: str) -> None:
    cliente = TestClient(
        app, base_url=ANFITRION, client=("8.8.8.8", 50000), headers={CABECERA: clave_api}
    )
    for ruta in ("/salud", "/v1/auditorias"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 403 and "detalle" in respuesta.json()


def test_una_ip_privada_simulada_pasa_el_filtro() -> None:
    assert _cliente(ip="192.168.1.30").get("/salud").status_code == 200


def test_un_host_ajeno_recibe_400() -> None:
    respuesta = _cliente(base="http://atacante.ejemplo").get("/salud")
    assert respuesta.status_code == 400


def test_la_documentacion_no_se_publica_en_el_producto(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import FastAPI

    from api.proteccion import opciones_documentacion

    producto = FastAPI(**opciones_documentacion({"SILICE_PRODUCTO": "1"}))
    cliente = TestClient(producto)
    assert (
        cliente.get("/docs").status_code == 404 and cliente.get("/openapi.json").status_code == 404
    )
    assert TestClient(FastAPI(**opciones_documentacion({}))).get("/docs").status_code == 200
```

`tests/unit/test_api_proteccion.py`:
```python
"""Piezas puras de la protección de la API (spec S5 §8.3)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.trustedhost import TrustedHostMiddleware

from api import proteccion


@pytest.mark.parametrize(
    ("host", "esperado"),
    [
        ("127.0.0.1", True),
        ("::1", True),
        ("10.0.0.5", True),
        ("192.168.1.30", True),
        ("172.16.0.9", True),
        ("fe80::1", True),
        ("8.8.8.8", False),
        ("::ffff:8.8.8.8", False),
        ("::ffff:192.168.1.30", True),
        ("2001:4860:4860::8888", False),
        ("testclient", False),
        ("", False),
        (None, False),
    ],
)
def test_ip_permitida(host: str | None, esperado: bool) -> None:
    assert proteccion.ip_permitida(host) is esperado


def test_los_anfitriones_son_el_bucle_local_y_la_ip_elegida() -> None:
    assert proteccion.anfitriones_permitidos(None) == ["127.0.0.1", "localhost"]
    assert proteccion.anfitriones_permitidos("192.168.1.20") == [
        "127.0.0.1",
        "localhost",
        "192.168.1.20",
    ]
    for rara in ("0.0.0.0", "::", "no-es-ip", "8.8.8.8"):
        assert proteccion.anfitriones_permitidos(rara) == ["127.0.0.1", "localhost"]


def test_en_producto_lo_dice_la_variable() -> None:
    assert proteccion.en_producto({"SILICE_PRODUCTO": "1"}) is True
    assert proteccion.en_producto({"SILICE_PRODUCTO": "0"}) is False
    assert proteccion.en_producto({}) is False


def test_proteger_reemplaza_el_filtro_de_hosts_de_s3_por_el_suyo() -> None:
    app = FastAPI()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])

    @app.get("/x")
    def _x() -> dict[str, str]:
        return {"ok": "si"}

    proteccion.proteger(app, {"SILICE_DIRECCION": "192.168.1.20"})
    asignados = [m for m in app.user_middleware if m.cls is TrustedHostMiddleware]
    assert len(asignados) == 1
    cliente = TestClient(app, base_url="http://192.168.1.20:8000", client=("192.168.1.30", 1))
    assert cliente.get("/x").status_code == 200
    ajeno = TestClient(app, base_url="http://otro.ejemplo", client=("192.168.1.30", 1))
    assert ajeno.get("/x").status_code == 400
```

Además, en `tests/unit/test_arquitectura_s5.py` (la regla de `api` importando solo públicos ya se
amplía en T10; aquí no cambia).

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/integration/test_api_clave.py tests/unit/test_api_proteccion.py -v -W
error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'api.proteccion'`.
```bash
git add tests/fixtures/claves_api.py tests/integration/test_api_clave.py \
  tests/unit/test_api_proteccion.py
git commit -m "test(api): clave en toda ruta, hosts ajenos y redes publicas (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`api/proteccion.py`:
```python
"""Protección de la API en el producto (RF-98; spec S5 §8.3).

Tres capas, ninguna sustituye a la otra: (1) la clave de acceso en cada ruta (**el control**),
(2) `TrustedHostMiddleware` contra el *DNS rebinding* (un `Host` ajeno da 400) y (3) un filtro que
responde 403 a quien no llega desde el bucle local ni desde una red privada (defensa adicional al
cortafuegos: un túnel o proxy local anula esta capa y la regla «solo desde este equipo»).
"""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

VARIABLE_DIRECCION = "SILICE_DIRECCION"
VARIABLE_PRODUCTO = "SILICE_PRODUCTO"
ANFITRIONES_BASE = ("127.0.0.1", "localhost")


def en_producto(entorno: Mapping[str, str] | None = None) -> bool:
    return (os.environ if entorno is None else entorno).get(VARIABLE_PRODUCTO) == "1"


def opciones_documentacion(entorno: Mapping[str, str] | None = None) -> dict[str, None]:
    """En el producto no se publican `/docs`, `/redoc` ni `/openapi.json` (el esquema sigue
    exportado en `docs/api.json`)."""
    if en_producto(entorno):
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


def anfitriones_permitidos(direccion: str | None) -> list[str]:
    hosts = list(ANFITRIONES_BASE)
    try:
        ip = ipaddress.ip_address(direccion or "")
    except ValueError:
        return hosts
    if ip.version == 4 and ip.is_private and not ip.is_unspecified and str(ip) not in hosts:
        hosts.append(str(ip))
    return hosts


def ip_permitida(host: str | None) -> bool:
    try:
        ip = ipaddress.ip_address(host or "")
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback or ip.is_private


class SoloRedesPrivadas:
    """Middleware ASGI: 403 (o cierre del websocket) a quien no es de bucle local ni privada."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            cliente = scope.get("client")
            if not ip_permitida(cliente[0] if cliente else None):
                if scope["type"] == "http":
                    respuesta = JSONResponse(
                        {"detalle": "Acceso denegado: Sílice solo atiende a la red local."},
                        status_code=403,
                    )
                    await respuesta(scope, receive, send)
                else:
                    await send({"type": "websocket.close", "code": 1008})
                return
        await self.app(scope, receive, send)


def proteger(app: FastAPI, entorno: Mapping[str, str] | None = None) -> None:
    """Instala el filtro de redes y el de hosts. Si S3 ya había puesto un `TrustedHostMiddleware`
    con su lista, se reemplaza por el de la IP elegida (uno solo)."""
    fuente = os.environ if entorno is None else entorno
    app.user_middleware = [m for m in app.user_middleware if m.cls is not TrustedHostMiddleware]
    app.add_middleware(SoloRedesPrivadas)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=anfitriones_permitidos(fuente.get(VARIABLE_DIRECCION))
    )
```

`api/main.py` (queda así; **conservar** los `include_router` que S3 agregó, que ya llevan su
dependencia de clave):
```python
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api.proteccion import opciones_documentacion, proteger
from api.rutas import catalogo, computos, listas, presupuestos, rendimientos
from api.seguridad import exigir_clave_api
from core.catalog import CatalogoIncompleto
from operacion.version import version

# DESCRIPCION: sin cambios.

app = FastAPI(
    title="Sílice", version=version(), description=DESCRIPCION, **opciones_documentacion()
)
CON_CLAVE = [Depends(exigir_clave_api)]  # RF-98: clave en todas las rutas salvo /salud
app.include_router(catalogo.router, dependencies=CON_CLAVE)
app.include_router(listas.router, dependencies=CON_CLAVE)
app.include_router(computos.router, dependencies=CON_CLAVE)
app.include_router(presupuestos.router, dependencies=CON_CLAVE)
app.include_router(rendimientos.router, dependencies=CON_CLAVE)
# (aquí siguen los routers de S3, p. ej. auditorias, con su propia dependencia de clave)


@app.get("/salud")
def salud() -> dict[str, str]:
    """Sin clave y sin versión: solo dice que el servidor responde (spec S5 §8.3)."""
    return {"estado": "ok"}


# (los manejadores de excepción, sin cambios)

proteger(app)  # al final: ya están todas las rutas y los filtros envuelven a la aplicación
```
`tests/conftest.py`: `pytest_plugins = ["pytester", "tests.fixtures.claves_api"]` (así las
fixtures `clave_api` y `cliente_api` llegan a todas las pruebas sin importarlas, que ruff
marcaría como redefinidas). `tests/integration/test_api*.py` y las pruebas de S3 que hoy hacen
`TestClient(app)`: `rg -n "TestClient\(" tests` y cambiar a la fixture `cliente_api`; las que
prueban el 401 sin clave usan un `TestClient` propio. Luego
`uv run python scripts/exportar_openapi.py` (el esquema gana `/salud` y la versión) y se
versiona `docs/api.json`.

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite)
Run: `uv run pytest tests/integration tests/unit/test_api_proteccion.py -v -W error` y luego
`uv run pytest -q -W error`; `git diff --exit-code -- docs/api.json` tras regenerar.
`uv run ruff check api tests/fixtures/claves_api.py tests/integration/test_api_clave.py
tests/unit/test_api_proteccion.py`.

- [ ] **Paso 5: Commit y PR**
```bash
git add api/proteccion.py api/main.py docs/api.json tests/fixtures/claves_api.py tests/integration \
  tests/unit/test_api_proteccion.py
git commit -m "feat(api): clave en toda ruta, hosts, redes privadas y /salud" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-2-api
gh pr create --base main --head inc/100-s5-2-api --title "S5-2: proteccion de la API" --body-file -
```

---

### Tarea 10: `operacion.eventos_perdidos` y `ui/cliente.py` (SEG-12 y «solo este equipo»)

**Rama:** `inc/100-s5-2-ui` (sale de `origin/main` con T6, T8 y T9 fusionadas)
**Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `operacion/eventos_perdidos.py`, `ui/cliente.py`, `tests/fixtures/eventos_seguridad.py`
- Modificar: `operacion/respaldo.py` (función `restaurar`: agregar `diferencias` al JSON);
  `operacion/ordenes_100.py` (orden `eventos`); `tests/unit/test_arquitectura_s5.py` (regla de
  `PUBLICOS_DE_OPERACION`); los sitios de S3 que llaman a `seguridad.red.es_local`
  (`rg -n "es_local" ui api`)
- Prueba: `tests/unit/test_eventos_perdidos.py`, `tests/integration/test_restaurar_eventos.py`,
  `tests/unit/test_ui_cliente.py`, `tests/unit/test_ordenes_eventos.py`

**Interfaces:**
- Consume: `operacion.base_datos.respaldar_todo`, `restaurar_juego`, `Restauracion.eventos_perdidos`
  (A2, A3); `operacion.red.es_cliente_local`, `AVISO_ACCESO` (T6); `operacion.config` (T5);
  `seguridad.modelo.Base` solo en una prueba (A12).
- Produce:
  - `operacion.eventos_perdidos`: `TABLAS_VIGILADAS: dict[str, ReglaTabla]`,
    `ReglaTabla(clave, etiqueta, estado: tuple[str, ...])`,
    `diferencias(actual: Path, copia: Path) -> list[dict]`,
    `pendientes(entorno=None) -> list[Path]`, `resumen(archivo: Path) -> dict`,
    `marcar_revisado(archivo: Path, *, por: str | None = None) -> None`,
    `bloqueadas(entorno=None) -> bool`.
  - `ui.cliente`: `MENSAJE_REMOTO`, `MENSAJE_PENDIENTE`, `ip_del_cliente() -> str | None`,
    `cliente_es_local() -> bool`, `operacion_sensible_permitida() -> tuple[bool, str]`,
    `pintar_aviso_sin_cifrar() -> bool`.
  - Orden `eventos {pendientes, revisar <archivo>}`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/fixtures/eventos_seguridad.py` (instalaciones mínimas, solo con las columnas que la
prueba necesita; no dependen de las migraciones de S3):
```python
"""Dos estados de una `instalacion.db` para probar lo que se pierde al restaurar (SEG-12)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

ESQUEMA = """
CREATE TABLE usuario (id INTEGER PRIMARY KEY, login TEXT, activo INTEGER, roles TEXT,
                      huella_clave TEXT);
CREATE TABLE clave_empresa (id INTEGER PRIMARY KEY, huella TEXT, estado TEXT, privada_cifrada BLOB);
CREATE TABLE empresa_registrada (id INTEGER PRIMARY KEY, huella TEXT, estado TEXT);
CREATE TABLE clave_api (id INTEGER PRIMARY KEY, nombre TEXT, revocada INTEGER, huella_secreto TEXT);
CREATE TABLE evento_acceso (id INTEGER PRIMARY KEY, tipo TEXT);
"""


def base(ruta: Path, filas: dict[str, list[tuple]]) -> Path:
    conexion = sqlite3.connect(ruta)
    conexion.executescript(ESQUEMA)
    columnas = {
        "usuario": "id, login, activo, roles, huella_clave",
        "clave_empresa": "id, huella, estado, privada_cifrada",
        "empresa_registrada": "id, huella, estado",
        "clave_api": "id, nombre, revocada, huella_secreto",
        "evento_acceso": "id, tipo",
    }
    for tabla, registros in filas.items():
        marcas = ", ".join("?" * len(registros[0]))
        conexion.executemany(
            f"INSERT INTO {tabla} ({columnas[tabla]}) VALUES ({marcas})", registros
        )
    conexion.commit()
    conexion.close()
    return ruta


COPIA = {
    "usuario": [(1, "ana", 1, "arma", "ARGON-A"), (2, "beto", 1, "arma,revisa", "ARGON-B")],
    "clave_empresa": [(1, "AAAA", "activa", b"cifrada")],
    "empresa_registrada": [(1, "BBBB", "activa")],
    "clave_api": [(1, "plugin", 0, "SHA-1")],
    "evento_acceso": [(1, "entrada")],
}
ACTUAL = {
    "usuario": [
        (1, "ana", 0, "arma", "ARGON-A"),
        (2, "beto", 1, "revisa", "ARGON-B"),
        (3, "carla", 1, "arma", "ARGON-C"),
    ],
    "clave_empresa": [(1, "AAAA", "revocada", None)],
    "empresa_registrada": [(1, "BBBB", "revocada")],
    "clave_api": [(1, "plugin", 1, "SHA-1"), (2, "nuevo", 0, "SHA-2")],
    "evento_acceso": [(1, "entrada"), (2, "revocacion")],
}
```

`tests/unit/test_eventos_perdidos.py`:
```python
"""Revisión obligatoria de los eventos de seguridad perdidos al restaurar (SEG-12; spec S5 §6.5)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from operacion import config, eventos_perdidos
from tests.fixtures.eventos_seguridad import ACTUAL, COPIA
from tests.fixtures.eventos_seguridad import base as _base


def test_el_conjunto_exacto_de_diferencias_sembradas(tmp_path: Path) -> None:
    actual, copia = _base(tmp_path / "actual.db", ACTUAL), _base(tmp_path / "copia.db", COPIA)
    hallado = {
        (d["tipo"], d["tabla"], d["id"]) for d in eventos_perdidos.diferencias(actual, copia)
    }
    assert hallado == {
        ("cuenta_reactivada", "usuario", 1),
        ("roles_distintos", "usuario", 2),
        ("registro_posterior_perdido", "usuario", 3),
        ("clave_revivida", "clave_empresa", 1),
        ("clave_revivida", "empresa_registrada", 1),
        ("clave_api_revivida", "clave_api", 1),
        ("registro_posterior_perdido", "clave_api", 2),
    }


def test_las_diferencias_no_llevan_secretos(tmp_path: Path) -> None:
    actual, copia = _base(tmp_path / "actual.db", ACTUAL), _base(tmp_path / "copia.db", COPIA)
    texto = json.dumps(eventos_perdidos.diferencias(actual, copia), ensure_ascii=False)
    for secreto in ("ARGON-", "SHA-", "cifrada"):
        assert secreto not in texto
    assert "ana" in texto and "AAAA" in texto  # lo que identifica, sí


def test_sin_diferencias_no_hay_nada_que_revisar(tmp_path: Path) -> None:
    uno, otro = _base(tmp_path / "a.db", COPIA), _base(tmp_path / "b.db", COPIA)
    assert eventos_perdidos.diferencias(uno, otro) == []


def test_una_instalacion_sin_esas_tablas_no_falla(tmp_path: Path) -> None:
    vacia = tmp_path / "vacia.db"
    sqlite3.connect(vacia).close()
    con_datos = _base(tmp_path / "c.db", COPIA)
    assert eventos_perdidos.diferencias(vacia, con_datos) == []
    assert eventos_perdidos.diferencias(con_datos, vacia) == []
    assert eventos_perdidos.diferencias(tmp_path / "no_existe.db", con_datos) == []


def test_las_tablas_vigiladas_existen_en_el_modelo_de_s3() -> None:
    from seguridad.modelo import Base

    for tabla, regla in eventos_perdidos.TABLAS_VIGILADAS.items():
        columnas = {c.name for c in Base.metadata.tables[tabla].columns}
        assert {regla.clave, regla.etiqueta, *regla.estado} <= columnas, tabla


def _pendiente(nombre: str, contenido: str) -> Path:
    ruta = config.carpeta_datos() / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def test_un_archivo_sin_revisar_bloquea_las_operaciones_sensibles() -> None:
    assert eventos_perdidos.bloqueadas() is False
    archivo = _pendiente(
        "eventos_perdidos_20261011-100000.json", '{"revisado": false, "eventos": []}'
    )
    assert eventos_perdidos.pendientes() == [archivo] and eventos_perdidos.bloqueadas() is True
    eventos_perdidos.marcar_revisado(archivo, por="ana")
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert datos["revisado"] is True and datos["revisado_por"] == "ana" and datos["revisado_en"]
    assert eventos_perdidos.bloqueadas() is False


@pytest.mark.parametrize("contenido", ["{no es json", "[]", '{"eventos": []}', ""])
def test_un_archivo_ilegible_o_sin_marca_cuenta_como_pendiente(contenido: str) -> None:
    _pendiente("eventos_perdidos_20261011-110000.json", contenido)
    assert eventos_perdidos.bloqueadas() is True


def test_el_resumen_cuenta_eventos_y_diferencias() -> None:
    archivo = _pendiente(
        "eventos_perdidos_20261011-120000.json",
        json.dumps({"revisado": False, "eventos": [{"id": 2}], "diferencias": [{"tipo": "x"}]}),
    )
    assert eventos_perdidos.resumen(archivo) == {
        "archivo": archivo.name,
        "revisado": False,
        "eventos": 1,
        "diferencias": 1,
        "juego": None,
    }
```

`tests/integration/test_restaurar_eventos.py`:
```python
"""Restaurar un juego con `instalacion.db` deja el listado exacto y bloquea (RF-96 f; spec §6.5)."""

from __future__ import annotations

import json
import sqlite3

from operacion import base_datos, config, eventos_perdidos
from tests.fixtures.eventos_seguridad import ACTUAL, COPIA
from tests.fixtures.eventos_seguridad import base as _base


def _reemplazar(ruta, filas) -> None:
    ruta.unlink()
    _base(ruta, filas)


def test_restaurar_lista_lo_perdido_y_bloquea() -> None:
    instalacion = config.ruta_instalacion()
    instalacion.parent.mkdir(parents=True, exist_ok=True)
    _base(instalacion, COPIA)
    juego = base_datos.respaldar_todo()
    _reemplazar(instalacion, ACTUAL)  # la instalación siguió: revocó, desactivó y registró

    resultado = base_datos.restaurar_juego(juego)

    datos = json.loads(resultado.eventos_perdidos.read_text(encoding="utf-8"))
    assert datos["revisado"] is False
    assert [e["tipo"] for e in datos["eventos"]] == [
        "revocacion"
    ]  # el evento 2, posterior al juego
    assert {d["tipo"] for d in datos["diferencias"]} == {
        "cuenta_reactivada",
        "roles_distintos",
        "registro_posterior_perdido",
        "clave_revivida",
        "clave_api_revivida",
    }
    with sqlite3.connect(instalacion) as conexion:  # y la base quedó como estaba en el juego
        assert conexion.execute("SELECT COUNT(*) FROM usuario").fetchone() == (2,)
    assert eventos_perdidos.bloqueadas() is True
    eventos_perdidos.marcar_revisado(resultado.eventos_perdidos, por="admin")
    assert eventos_perdidos.bloqueadas() is False


def test_restaurar_solo_un_caso_no_toca_la_seguridad_ni_pide_revision() -> None:
    caso = base_datos.preparar_base(config.ruta_caso_por_defecto()).ruta
    juego = base_datos.respaldar_todo()
    resultado = base_datos.restaurar_juego(juego, solo_caso=caso.stem)
    assert resultado.eventos_perdidos is None and eventos_perdidos.bloqueadas() is False
```

`tests/unit/test_ordenes_eventos.py`:
```python
"""La orden `eventos` de `python -m operacion` (spec S5 §6.5)."""

from __future__ import annotations

import json

from operacion import __main__ as cli
from operacion import config


def test_los_eventos_pendientes_se_listan_y_se_revisan(capsys) -> None:
    archivo = config.carpeta_datos() / "eventos_perdidos_20261011-120000.json"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(json.dumps({"revisado": False, "eventos": []}), encoding="utf-8")
    assert cli.main(["eventos", "pendientes"]) == 0
    assert archivo.name in capsys.readouterr().out
    assert cli.main(["eventos", "revisar", str(archivo)]) == 0
    assert json.loads(archivo.read_text(encoding="utf-8"))["revisado"] is True
    assert cli.main(["eventos", "pendientes"]) == 0
    assert archivo.name not in capsys.readouterr().out
```

`tests/unit/test_ui_cliente.py`:
```python
"""«Solo desde el propio equipo» y el aviso «sin cifrar» (RF-98; spec S5 §8.2)."""

from __future__ import annotations

import ast

import pytest
from streamlit.testing.v1 import AppTest

from operacion import config, red
from tests.fixtures.arquitectura import archivos, ruta
from ui import cliente


@pytest.fixture
def con_red_local():
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="192.168.1.20")
    )


@pytest.mark.parametrize(
    ("ip", "esperado"),
    [("127.0.0.1", True), ("192.168.1.20", True), ("192.168.1.30", False), ("8.8.8.8", False)],
)
def test_con_la_red_encendida_solo_cuentan_el_bucle_y_la_ip_elegida(
    monkeypatch, con_red_local, ip: str, esperado: bool
) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: ip)
    assert cliente.cliente_es_local() is esperado


def test_si_no_se_puede_leer_la_ip_solo_es_local_con_la_red_apagada(monkeypatch) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: None)
    assert cliente.cliente_es_local() is True  # red apagada: solo el propio equipo puede llegar
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="192.168.1.20")
    )
    assert cliente.cliente_es_local() is False


def test_una_operacion_sensible_se_rechaza_desde_una_ip_remota(monkeypatch, con_red_local) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: "192.168.1.30")
    permitida, motivo = cliente.operacion_sensible_permitida()
    assert permitida is False and motivo == cliente.MENSAJE_REMOTO


def test_una_operacion_sensible_se_bloquea_con_eventos_sin_revisar(monkeypatch) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: "127.0.0.1")
    assert cliente.operacion_sensible_permitida() == (True, "")
    pendiente = config.carpeta_datos() / "eventos_perdidos_20261011-090000.json"
    pendiente.parent.mkdir(parents=True, exist_ok=True)
    pendiente.write_text('{"revisado": false}', encoding="utf-8")
    assert cliente.operacion_sensible_permitida() == (False, cliente.MENSAJE_PENDIENTE)


def _aviso() -> None:
    from ui import cliente as c

    c.pintar_aviso_sin_cifrar()


@pytest.mark.parametrize(("ip", "visible"), [("192.168.1.30", True), ("127.0.0.1", False)])
def test_el_cliente_remoto_ve_el_aviso_sin_cifrar(monkeypatch, con_red_local, ip, visible) -> None:
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: ip)
    texto = [e.value for e in AppTest.from_function(_aviso).run().warning]
    assert (red.AVISO_ACCESO in texto) is visible


def test_ningun_modulo_de_ui_ni_api_llama_a_es_local_de_seguridad_directamente() -> None:
    infractores = []
    for paquete in ("ui", "api"):
        for archivo in archivos(paquete):
            for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
                usa_import = isinstance(nodo, ast.ImportFrom) and nodo.module == "seguridad.red"
                usa_llamada = (
                    isinstance(nodo, ast.Call)
                    and isinstance(nodo.func, (ast.Name, ast.Attribute))
                    and ast.unparse(nodo.func)
                    in {"es_local", "red.es_local", "seguridad.red.es_local"}
                )
                if usa_import or usa_llamada:
                    infractores.append(f"{ruta(archivo)}:{nodo.lineno}")
    assert infractores == []


def test_la_pantalla_de_acceso_de_s3_usa_el_aviso_de_s5() -> None:
    from tests.fixtures.arquitectura import RAIZ

    assert "pintar_aviso_sin_cifrar" in (RAIZ / "ui" / "acceso.py").read_text(encoding="utf-8")
```
`tests/unit/test_arquitectura_s5.py`: reemplazar `PUBLICOS_DE_OPERACION` y su prueba por
```python
#: Lo único de `operacion` que `ui` y `api` NO pueden importar: arrancar y la CLI (spec S5 §5.2).
PRIVADOS_DE_OPERACION = ("operacion.lanzador", "operacion.ordenes_100", "operacion.__main__")


def test_ui_y_api_no_importan_el_lanzador_ni_la_cli() -> None:
    infractores = sorted(
        f"{ruta(archivo)}: {modulo}"
        for paquete in ("ui", "api")
        for archivo in archivos(paquete)
        for modulo in importaciones(archivo)
        if any(modulo == p or modulo.startswith(p + ".") for p in PRIVADOS_DE_OPERACION)
    )
    assert infractores == []
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_eventos_perdidos.py tests/integration/test_restaurar_eventos.py
tests/unit/test_ordenes_eventos.py tests/unit/test_ui_cliente.py tests/unit/test_arquitectura_s5.py
-v -W error`
Esperado: FAIL con `ImportError: cannot import name 'eventos_perdidos' from 'operacion'` y
`ModuleNotFoundError: No module named 'ui.cliente'`.
```bash
git add tests/fixtures/eventos_seguridad.py tests/unit/test_eventos_perdidos.py \
  tests/integration/test_restaurar_eventos.py tests/unit/test_ordenes_eventos.py \
  tests/unit/test_ui_cliente.py tests/unit/test_arquitectura_s5.py
git commit -m "test(operacion): eventos perdidos completos, bloqueo y cliente local (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`operacion/eventos_perdidos.py`:
```python
"""Qué se pierde al restaurar la base de la instalación y cómo se obliga a revisarlo (SEG-12).

Restaurar `instalacion.db` puede revivir claves de firma o de API revocadas, cuentas desactivadas,
roles retirados y revocaciones ajenas. `diferencias` compara la instalación **actual** con la
copia que se va a restaurar y lista solo lo que identifica (login, huella, nombre), nunca una
huella de contraseña ni un secreto. El archivo `eventos_perdidos_<fecha>.json` queda fuera de la
base y mientras tenga `revisado: false` (o no se pueda leer) las operaciones sensibles se bloquean.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from operacion import config


@dataclass(frozen=True, slots=True)
class ReglaTabla:
    clave: str
    etiqueta: str
    estado: tuple[str, ...]


TABLAS_VIGILADAS: dict[str, ReglaTabla] = {
    "usuario": ReglaTabla("id", "login", ("activo", "roles")),
    "clave_empresa": ReglaTabla("id", "huella", ("estado",)),
    "empresa_registrada": ReglaTabla("id", "huella", ("estado",)),
    "clave_api": ReglaTabla("id", "nombre", ("revocada",)),
}
_REVOCADAS = ("retirada", "revocada")


def _filas(ruta: Path, tabla: str, regla: ReglaTabla) -> dict[Any, dict[str, Any]] | None:
    if not ruta.is_file():
        return None
    columnas = [regla.clave, regla.etiqueta, *regla.estado]
    with closing(sqlite3.connect(f"{ruta.resolve().as_uri()}?mode=ro", uri=True)) as conexion:
        existe = conexion.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
        ).fetchone()
        if existe is None:
            return None
        consulta = f"SELECT {', '.join(columnas)} FROM {tabla}"  # nombres fijos, no del usuario
        return {
            fila[0]: dict(zip(columnas, fila, strict=True)) for fila in conexion.execute(consulta)
        }


def _diferencia(
    tipo: str, tabla: str, regla: ReglaTabla, antes: Mapping, despues: Mapping | None
) -> dict:
    return {
        "tipo": tipo,
        "tabla": tabla,
        "id": antes[regla.clave],
        "etiqueta": antes[regla.etiqueta],
        "actual": {c: antes[c] for c in regla.estado},
        "al_restaurar": None if despues is None else {c: despues[c] for c in regla.estado},
    }


def _tipo(tabla: str, actual: Mapping, copia: Mapping) -> list[str]:
    if tabla == "usuario":
        tipos = []
        if not actual["activo"] and copia["activo"]:
            tipos.append("cuenta_reactivada")
        if actual["roles"] != copia["roles"]:
            tipos.append("roles_distintos")
        return tipos
    if tabla == "clave_api":
        return ["clave_api_revivida"] if actual["revocada"] and not copia["revocada"] else []
    revivida = actual["estado"] in _REVOCADAS and copia["estado"] == "activa"
    return ["clave_revivida"] if revivida else []


def diferencias(actual: Path, copia: Path) -> list[dict[str, Any]]:
    """Lo que la restauración de `copia` sobre `actual` deshace en silencio. Una tabla que falta
    en cualquiera de las dos (instalación de la 0.6.0, vacía) no es una diferencia."""
    resultado: list[dict[str, Any]] = []
    for tabla, regla in TABLAS_VIGILADAS.items():
        ahora, antes = _filas(actual, tabla, regla), _filas(copia, tabla, regla)
        if ahora is None or antes is None:
            continue
        for clave, fila in ahora.items():
            otra = antes.get(clave)
            if otra is None:
                resultado.append(
                    _diferencia("registro_posterior_perdido", tabla, regla, fila, None)
                )
                continue
            resultado.extend(
                _diferencia(t, tabla, regla, fila, otra) for t in _tipo(tabla, fila, otra)
            )
    return resultado


def _leer(archivo: Path) -> dict[str, Any] | None:
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def pendientes(entorno: Mapping[str, str] | None = None) -> list[Path]:
    """Los archivos sin revisar. Uno ilegible o sin la marca `revisado: true` cuenta como
    pendiente: ante la duda, se bloquea."""
    carpeta = config.carpeta_datos(entorno)
    if not carpeta.is_dir():
        return []
    return [
        archivo
        for archivo in sorted(carpeta.glob("eventos_perdidos_*.json"))
        if (_leer(archivo) or {}).get("revisado") is not True
    ]


def bloqueadas(entorno: Mapping[str, str] | None = None) -> bool:
    return bool(pendientes(entorno))


def resumen(archivo: Path) -> dict[str, Any]:
    datos = _leer(archivo) or {}
    return {
        "archivo": archivo.name,
        "revisado": datos.get("revisado") is True,
        "eventos": len(datos.get("eventos", [])),
        "diferencias": len(datos.get("diferencias", [])),
        "juego": datos.get("juego"),
    }


def marcar_revisado(archivo: Path, *, por: str | None = None) -> None:
    datos = _leer(archivo) or {}
    datos.update(
        revisado=True, revisado_por=por, revisado_en=datetime.now().isoformat(timespec="seconds")
    )
    temporal = archivo.with_name(archivo.name + ".tmp")
    temporal.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    temporal.replace(archivo)
```
`operacion/respaldo.py`, función `restaurar`: donde arma el JSON de `perdidos`, agregar la clave
`"diferencias"` (importando `eventos_perdidos` dentro de la función, para no crear un ciclo):
```python
        from operacion import eventos_perdidos as perdidos_mod

        copia_instalacion = next(
            juego / base["archivo"] for base in elegidas if base["destino"] == "instalacion"
        )
        # ... dentro del dict que se escribe:
                "diferencias": perdidos_mod.diferencias(ruta_instalacion, copia_instalacion),
```
`operacion/ordenes_100.py`: agregar
```python
def _eventos(argumentos: argparse.Namespace) -> int:
    from operacion import eventos_perdidos

    if argumentos.accion == "pendientes":
        for archivo in eventos_perdidos.pendientes():
            print(archivo.name)
        return 0
    eventos_perdidos.marcar_revisado(Path(argumentos.archivo), por="administrador")
    print(f"Revisado: {argumentos.archivo}")
    return 0
```
y en `registrar`:
```python
    eventos = ordenes.add_parser("eventos", help="eventos de seguridad perdidos tras restaurar")
    sub = eventos.add_subparsers(dest="accion", required=True)
    sub.add_parser("pendientes")
    sub.add_parser("revisar").add_argument("archivo")
    tabla["eventos"] = _eventos
```

`ui/cliente.py`:
```python
"""Quién llega a Sílice: «el propio equipo» y las operaciones sensibles (RF-98; spec S5 §8.2).

Firmar, generar o exportar la clave de firma, registrar la clave de IA, crear claves de API y
cambiar la carpeta de datos se permiten solo desde el propio equipo y mientras no haya eventos de
seguridad perdidos sin revisar (SEG-12). Sin TLS, la pantalla de acceso avisa al cliente remoto.
"""

from __future__ import annotations

import streamlit as st

from operacion import config, eventos_perdidos, red

MENSAJE_REMOTO = (
    "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red."
)
MENSAJE_PENDIENTE = (
    "Se restauró un respaldo y hay eventos de seguridad perdidos sin revisar. El administrador "
    "debe revisarlos (pestaña Instalación) antes de esta operación."
)


def ip_del_cliente() -> str | None:
    """La IP del navegador (`st.context.ip_address`, A16); `None` si Streamlit no la da."""
    try:
        return st.context.ip_address
    except (AttributeError, RuntimeError):
        return None


def cliente_es_local() -> bool:
    ajustes = config.cargar_ajustes(config.ruta_ajustes())
    ip = ip_del_cliente()
    if ip is None:
        # Sin la IP, solo es seguro suponer «local» si la red está apagada: nadie más puede llegar.
        return not ajustes.red_local
    return red.es_cliente_local(ip, ajustes.direccion if ajustes.red_local else "")


def operacion_sensible_permitida() -> tuple[bool, str]:
    if not cliente_es_local():
        return False, MENSAJE_REMOTO
    if eventos_perdidos.bloqueadas():
        return False, MENSAJE_PENDIENTE
    return True, ""


def pintar_aviso_sin_cifrar() -> bool:
    """Para la pantalla de acceso: avisa al cliente remoto que la conexión no está cifrada."""
    if cliente_es_local():
        return False
    st.warning(red.AVISO_ACCESO)
    return True
```
Sitios de S3: `rg -n "es_local" ui api` y, en cada uno, reemplazar la pareja
`if not es_local(ip): … ` por
```python
permitida, motivo = cliente.operacion_sensible_permitida()
if not permitida:
    st.error(motivo)
    return
```
(`from ui import cliente`); en `ui/acceso.py`, reemplazar el aviso propio por
`cliente.pintar_aviso_sin_cifrar()`. Las pruebas de S3 que parchaban `seguridad.red.es_local` pasan
a
parchar `ui.cliente.ip_del_cliente` (no están en el bloque de regresión).

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite)
Run: `uv run pytest tests/unit/test_eventos_perdidos.py tests/integration/test_restaurar_eventos.py
tests/unit/test_ordenes_eventos.py tests/unit/test_ui_cliente.py tests/unit/test_arquitectura_s5.py
tests/integration/test_respaldo.py -v -W error`
y `uv run pytest -q -W error`. `uv run ruff check operacion ui/cliente.py
tests/unit/test_eventos_perdidos.py tests/unit/test_ui_cliente.py`.

- [ ] **Paso 5: Commit**
```bash
git add operacion/eventos_perdidos.py operacion/respaldo.py operacion/ordenes_100.py \
  ui/cliente.py ui/ \
  tests/
git commit -m "feat(operacion): eventos perdidos, bloqueo hasta la revision y cliente local" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
(`git add ui/ tests/` solo porque los sitios de S3 tocados están repartidos; revisar `git status`
antes: nada de `data/` ni archivos ajenos.)

---

### Tarea 11: three.js local, imports diferidos de `scripts.*` y el mensaje de la similitud

**Rama:** `inc/100-s5-2-ui`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/estaticos/three.min.js`, `ui/estaticos/LICENSE-three.txt`; `.gitattributes` (una línea)
- Modificar: `ui/paginas/visor.py` (constantes `VERSION_THREE_JS`/`URL_THREE_JS`, `_html_visor` y
  `_PLANTILLA_HTML`); `ui/paginas/inicio.py:18` y `:75`; `ui/paginas/actualizacion.py:69` y sus
  usos (`:151`, `_sembrar`); `ui/paginas/simulador.py:22` y su uso (`:78`);
  `ui/paginas/similares.py` (`_MENSAJE_SIN_EXTRA_ML`)
- Prueba: `tests/unit/test_ui_sin_cdn.py`, `tests/unit/test_arquitectura_s5.py`,
  `tests/unit/test_ui_similares_modulo.py`; se actualizan las pruebas que citen `URL_THREE_JS`,
  `cdnjs` o parchen `inicio.sembrar_demostracion`, `actualizacion.sembrar`, `simulador.simular`

**Interfaces:**
- Consume: `operacion.config.es_producto` (T5).
- Produce: `ui.paginas.visor.RUTA_THREE_JS: Path`, `SHA256_THREE_JS: str`, `TAMANO_THREE_JS: int`;
  `_html_visor(mallas)` sin ninguna referencia externa; las páginas ya no importan `scripts.*` ni
  `tests.fixtures` al cargarse (RV-25).

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_ui_sin_cdn.py`:
```python
"""El visor 3D no pide nada fuera del equipo (RNF-08; spec S5 §10.2; RP10-5)."""

from __future__ import annotations

import hashlib
import re

from ui.paginas import visor

MALLA = {"global_id": "g1", "vertices": [0, 0, 0, 1, 0, 0, 0, 1, 0], "caras": [0, 1, 2]}


def test_el_archivo_de_three_es_el_r128_verificado() -> None:
    contenido = visor.RUTA_THREE_JS.read_bytes()
    assert len(contenido) == visor.TAMANO_THREE_JS == 603_445
    assert hashlib.sha256(contenido).hexdigest() == visor.SHA256_THREE_JS
    assert visor.SHA256_THREE_JS == (
        "9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2"
    )
    assert b"SPDX-License-Identifier: MIT" in contenido[:300]


def test_la_licencia_de_three_acompana_al_archivo() -> None:
    texto = (visor.RUTA_THREE_JS.parent / "LICENSE-three.txt").read_text(encoding="utf-8")
    assert "MIT" in texto and "three.js authors" in texto


def test_el_html_incrusta_three_y_no_menciona_hosts_externos() -> None:
    html = visor._html_visor([MALLA])
    assert "cdnjs" not in html and "<script src=" not in html
    hosts = set(re.findall(r"https?://([A-Za-z0-9.-]+)", html))
    assert hosts <= {
        "www.w3.org"
    }  # el espacio de nombres XHTML dentro de three.js, no una petición


def test_el_script_incrustado_no_se_cierra_antes_de_tiempo() -> None:
    html = visor._html_visor([MALLA])
    assert html.count("</script") == 2  # los dos <script> de la plantilla, ninguno dentro de three
    assert "THREE.WebGLRenderer" in html and '"g1"' in html


def test_el_html_conserva_la_altura_y_los_datos() -> None:
    html = visor._html_visor([MALLA])
    assert f"height:{visor.ALTURA_VISOR}px" in html and "__DATOS__" not in html
    assert "__THREE__" not in html and "__ALTURA__" not in html
```
En `tests/unit/test_arquitectura_s5.py`, agregar:
```python
import ast


def _importaciones_al_cargar(archivo, raices: set[str]) -> list[str]:
    """Importaciones del nivel superior del módulo (también dentro de `try`), no las de `if
    TYPE_CHECKING` ni las de dentro de una función."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    pendientes = list(arbol.body)
    halladas = []
    while pendientes:
        nodo = pendientes.pop()
        if isinstance(nodo, ast.Try):
            pendientes.extend(nodo.body + nodo.orelse + nodo.finalbody)
        elif isinstance(nodo, ast.Import):
            halladas += [a.name for a in nodo.names if a.name.split(".")[0] in raices]
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            if nodo.level == 0 and nodo.module.split(".")[0] in raices:
                halladas.append(nodo.module)
    return sorted(halladas)


@pytest.mark.parametrize("archivo", archivos("ui"), ids=ruta)
def test_ningun_modulo_de_ui_importa_scripts_ni_fixtures_al_cargar(archivo) -> None:
    assert _importaciones_al_cargar(archivo, {"scripts", "tests"}) == []
```
`tests/unit/test_ui_similares_modulo.py`:
```python
"""Sin el módulo de similitud, la pantalla dice cuál módulo falta (RF-97 g; spec S5 §4.2)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from operacion import config
from ui.paginas import similares


def _pagina() -> None:
    from ui.paginas import similares as pagina

    pagina.render()


def _correr(monkeypatch: pytest.MonkeyPatch, producto: bool) -> str:
    monkeypatch.setattr(config, "es_producto", lambda raiz=None: producto)
    monkeypatch.setattr(
        similares,
        "sugerir_partidas_similares",
        lambda partidas, descripcion: SimpleNamespace(
            falla="ImportError: No module named 'sentence_transformers'", similares=()
        ),
    )
    at = AppTest.from_function(_pagina).run()
    at.text_input[0].set_value("excavacion de zanja").run()
    assert not at.exception
    return at.error[0].value


def test_en_el_producto_nombra_el_modulo(monkeypatch) -> None:
    mensaje = _correr(monkeypatch, producto=True)
    assert "módulo de similitud de partidas" in mensaje and "instalador completo" in mensaje


def test_en_desarrollo_nombra_el_extra(monkeypatch) -> None:
    mensaje = _correr(monkeypatch, producto=False)
    assert "uv sync --extra similitud" in mensaje
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_ui_sin_cdn.py tests/unit/test_arquitectura_s5.py
tests/unit/test_ui_similares_modulo.py -v -W error`
Esperado: FAIL con `AttributeError: module 'ui.paginas.visor' has no attribute 'RUTA_THREE_JS'`, con
`assert [...] == []` en `inicio`, `actualizacion` y `simulador`, y con `AssertionError` en el
mensaje.
```bash
git add tests/unit/test_ui_sin_cdn.py tests/unit/test_arquitectura_s5.py \
  tests/unit/test_ui_similares_modulo.py
git commit -m "test(ui): sin CDN, sin scripts al cargar y mensaje del modulo de similitud (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

three.js (una vez; la descarga la hace quien implementa, con internet, y la prueba fija su huella):
```bash
mkdir -p ui/estaticos
curl -sSL -o ui/estaticos/three.min.js \
  https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js
sha256sum ui/estaticos/three.min.js
# 9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2
echo "ui/estaticos/three.min.js binary" >> .gitattributes   # que autocrlf no cambie los bytes
```
`ui/estaticos/LICENSE-three.txt`:
```text
three.js r128, distribuido sin cambios desde cdnjs.cloudflare.com.

The MIT License

Copyright © 2010-2021 three.js authors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```
`ui/paginas/visor.py`: las dos constantes de la CDN (`VERSION_THREE_JS`, `URL_THREE_JS`, líneas
50-53) pasan a
```python
RUTA_THREE_JS = Path(__file__).resolve().parents[1] / "estaticos" / "three.min.js"
VERSION_THREE_JS = "r128"
TAMANO_THREE_JS = 603_445
SHA256_THREE_JS = "9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2"
```
`_html_visor` y la primera línea de script de la plantilla:
```python
def _html_visor(mallas_encontradas: list[dict]) -> str:
    """Incrusta el visor three.js con las mallas ya teseladas. three.js va dentro del HTML (RP10-5):
    el visor no pide nada fuera del equipo (RNF-08)."""
    return (
        _PLANTILLA_HTML.replace("__DATOS__", json.dumps(mallas_encontradas))
        .replace("__ALTURA__", str(ALTURA_VISOR))
        .replace("__THREE__", RUTA_THREE_JS.read_text(encoding="utf-8"))
    )
```
y en `_PLANTILLA_HTML`, la línea `<script src="__URL_THREE__"></script>` pasa a
`<script>__THREE__</script>`.
El docstring del módulo cambia «se carga desde cdnjs» por «va incrustado desde `ui/estaticos/`».
(`from pathlib import Path` ya está importado.)

Imports diferidos (RV-25), cada uno a la acción que lo usa:
- `ui/paginas/inicio.py`: quitar la línea 18 y, en `_estado`, antes de la llamada de la línea 75:
  `from scripts.seed_demo import main as sembrar_demostracion  # diferido: viaja por el manifiesto`.
- `ui/paginas/actualizacion.py`: quitar la línea 69; en `_barra_lateral`, antes de
  `st.text_input("Proyecto", ...)`:
  `from scripts.seed import NOMBRE_PROYECTO`; en `_sembrar`: `from scripts.seed import sembrar`.
- `ui/paginas/simulador.py`: quitar la línea 22; en `_generar`, antes de la llamada de la línea 78:
  `from scripts.simular_lista import simular`.
- Las pruebas que parchaban `inicio.sembrar_demostracion`, `actualizacion.sembrar` o
  `simulador.simular` (`rg -n "sembrar_demostracion|actualizacion.sembrar|simulador.simular" tests`)
  pasan a parchar `scripts.seed_demo.main`, `scripts.seed.sembrar` y
  `scripts.simular_lista.simular`.

`ui/paginas/similares.py`: reemplazar `_MENSAJE_SIN_EXTRA_ML` por
```python
from operacion import config

_MENSAJE_SIN_EXTRA_ML = (
    "Las propuestas de partidas similares necesitan el extra 'similitud' (sentence-transformers): "
    "instala con 'uv sync --extra similitud' y vuelve a intentar."
)
_MENSAJE_SIN_MODULO = (
    "El módulo de similitud de partidas no está instalado en este equipo. Ejecute el instalador "
    "completo (Silice-<versión>-completo.exe) para agregarlo; sus datos se conservan."
)


def _mensaje_sin_modulo() -> str:
    return _MENSAJE_SIN_MODULO if config.es_producto() else _MENSAJE_SIN_EXTRA_ML
```
y en `render`, `st.error(_MENSAJE_SIN_EXTRA_ML)` → `st.error(_mensaje_sin_modulo())`. Ajustar
`tests/unit/test_ui_similares.py` si cita el texto viejo («extra 'ml'»).

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite)
Run: `uv run pytest tests/unit/test_ui_sin_cdn.py tests/unit/test_arquitectura_s5.py
tests/unit/test_ui_similares_modulo.py tests/unit/test_ui_similares.py
tests/unit/test_ui_importable.py tests/unit/test_visor3d.py tests/unit/test_ui_inicio.py -v -W
error`
y `uv run pytest -q -W error`. `uv run ruff check ui tests/unit/test_ui_sin_cdn.py
tests/unit/test_ui_similares_modulo.py`.

- [ ] **Paso 5: Commit**
```bash
git add ui/estaticos ui/paginas .gitattributes tests/
git commit -m "feat(ui): three.js incrustado, imports diferidos y mensaje de la similitud" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Tarea 12: «Acerca de», pestaña «Instalación» y aviso en la pantalla de acceso

**Rama:** `inc/100-s5-2-ui`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/paginas/acerca.py`, `ui/paginas/instalacion.py`
- Modificar: `ui/app.py` (importación y `PAGINAS`); `ui/paginas/administracion.py` (`PESTANAS`);
  conteos de pantallas en las pruebas de `ui/app.py`
- Prueba: `tests/unit/test_ui_acerca.py`, `tests/unit/test_ui_instalacion.py`

**Interfaces:**
- Consume: `operacion.version` (T4), `operacion.base_datos` (`leer_estado`, `revision_head`,
  `Destino`,
  `respaldar_todo`), `operacion.config` (T5), `operacion.eventos_perdidos` (T10), `ui.cliente`
  (T10), `ui.caso.ruta_caso`, `ui.texto_seguro.texto_seguro` (S3), `ui/paginas/administracion.py`
  (A15).
- Produce: `ui.paginas.acerca.datos_acerca(entorno=None) -> DatosAcerca`, `render()`;
  `ui.paginas.instalacion.juegos_de_respaldo(entorno=None) -> list[JuegoResumen]`,
  `zip_del_juego(carpeta: Path) -> bytes`, `render_pestana()`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_ui_acerca.py`:
```python
"""«Acerca de»: versión, las dos revisiones, carpeta de datos y módulos (RF-99; spec S5 §5.2)."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from operacion import config
from operacion.base_datos import Destino, preparar_base, revision_head
from operacion.version import a_semver, version
from ui.paginas import acerca


def _pagina() -> None:
    from ui.paginas import acerca as pagina

    pagina.render()


def test_los_datos_traen_la_version_y_las_revisiones_de_las_dos_bases() -> None:
    preparar_base(config.ruta_instalacion(), Destino.INSTALACION)
    preparar_base(config.ruta_caso_por_defecto())
    datos = acerca.datos_acerca()
    assert datos.version == version() and datos.semver == a_semver(version())
    assert datos.revision_caso == revision_head(Destino.CASO) == datos.head_caso
    assert datos.revision_instalacion == datos.head_instalacion
    assert datos.carpeta_datos == str(config.carpeta_datos())


def test_una_base_que_no_existe_se_dice_sin_crearla() -> None:
    datos = acerca.datos_acerca()
    assert datos.revision_instalacion == "sin base" and not config.ruta_instalacion().exists()


def test_los_modulos_dicen_si_estan_instalados() -> None:
    datos = acerca.datos_acerca(modulo_instalado=lambda nombre: nombre == "xlrd")
    assert dict(datos.modulos)["Datos del BCV"] is True
    assert dict(datos.modulos)["Similitud de partidas"] is False


def test_la_pantalla_muestra_todo_sin_excepciones() -> None:
    preparar_base(config.ruta_instalacion(), Destino.INSTALACION)
    preparar_base(config.ruta_caso_por_defecto())
    datos = acerca.datos_acerca()
    at = AppTest.from_function(_pagina).run()
    assert not at.exception
    texto = " ".join(m.value for m in at.markdown)
    assert a_semver(version()) in texto and datos.revision_caso in texto
    assert datos.revision_instalacion in texto
    assert str(config.carpeta_datos()) in texto and "Similitud de partidas" in texto
```

`tests/unit/test_ui_instalacion.py`:
```python
"""Pestaña «Instalación»: red y API, respaldos y revisión de eventos perdidos (RF-98; spec §5.2)."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from operacion import config, eventos_perdidos
from operacion.base_datos import Destino, preparar_base
from ui import cliente
from ui.paginas import instalacion


def _pestana() -> None:
    from ui.paginas import instalacion as pestana

    pestana.render_pestana()


@pytest.fixture
def bases() -> None:
    preparar_base(config.ruta_instalacion(), Destino.INSTALACION)
    preparar_base(config.ruta_caso_por_defecto())


def _texto(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


def test_muestra_el_estado_de_la_red_y_de_la_api(bases) -> None:
    config.guardar_ajustes(
        config.ruta_ajustes(),
        config.Ajustes(red_local=True, direccion="192.168.1.20", api_activa=True),
    )
    texto = _texto(AppTest.from_function(_pestana).run())
    assert "http://192.168.1.20:8501" in texto and "API: activa" in texto
    assert "Sílice: red local (administrador)" in texto  # cómo cambiarla: no desde el navegador


def test_con_la_red_apagada_lo_dice(bases) -> None:
    texto = _texto(AppTest.from_function(_pestana).run())
    assert "Red local: apagada" in texto and "API: apagada" in texto


def test_crear_un_respaldo_lo_agrega_a_la_lista(bases) -> None:
    assert instalacion.juegos_de_respaldo() == []
    at = AppTest.from_function(_pestana).run()
    at.button(key="crear_respaldo").click().run()
    assert not at.exception
    (juego,) = instalacion.juegos_de_respaldo()
    assert juego.motivo == "manual" and juego.bases >= 2
    assert juego.nombre in _texto(at)


def test_el_zip_del_juego_trae_las_bases_y_la_ficha(bases) -> None:
    from operacion.base_datos import respaldar_todo

    carpeta = respaldar_todo()
    with zipfile.ZipFile(io.BytesIO(instalacion.zip_del_juego(carpeta))) as zip_:
        nombres = set(zip_.namelist())
    assert "ficha.json" in nombres and "instalacion.db" in nombres


def test_descargar_un_respaldo_exige_ser_el_propio_equipo(bases, monkeypatch) -> None:
    from operacion.base_datos import respaldar_todo

    respaldar_todo()
    config.guardar_ajustes(
        config.ruta_ajustes(), config.Ajustes(red_local=True, direccion="192.168.1.20")
    )
    monkeypatch.setattr(cliente, "ip_del_cliente", lambda: "192.168.1.30")
    at = AppTest.from_function(_pestana).run()
    assert [e.value for e in at.error] == [cliente.MENSAJE_REMOTO]


def test_los_eventos_pendientes_se_ven_y_se_marcan_revisados(bases) -> None:
    archivo = config.carpeta_datos() / "eventos_perdidos_20261011-120000.json"
    archivo.write_text(
        json.dumps(
            {
                "juego": "x",
                "revisado": False,
                "eventos": [{"id": 9, "tipo": "revocacion"}],
                "diferencias": [
                    {
                        "tipo": "clave_revivida",
                        "tabla": "clave_empresa",
                        "id": 1,
                        "etiqueta": "AAAA",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    at = AppTest.from_function(_pestana).run()
    assert "clave_revivida" in _texto(at) and "bloqueadas" in _texto(at)
    at.checkbox(key=f"confirmar_{archivo.name}").check().run()
    at.button(key=f"revisar_{archivo.name}").click().run()
    assert eventos_perdidos.bloqueadas() is False
    assert json.loads(archivo.read_text(encoding="utf-8"))["revisado"] is True


def test_un_nombre_con_marcado_no_se_interpreta(bases) -> None:
    archivo = config.carpeta_datos() / "eventos_perdidos_20261011-130000.json"
    archivo.write_text(
        json.dumps(
            {
                "revisado": False,
                "diferencias": [
                    {
                        "tipo": "cuenta_reactivada",
                        "tabla": "usuario",
                        "id": 1,
                        "etiqueta": "<img src=x onerror=alert(1)>",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    at = AppTest.from_function(_pestana).run()
    assert not at.exception
    assert all("<img" not in m.value for m in at.markdown)  # pasó por texto_seguro


def test_administracion_registra_la_pestana() -> None:
    fuente = (
        Path(__file__).resolve().parents[2] / "ui" / "paginas" / "administracion.py"
    ).read_text(encoding="utf-8")
    assert "Instalación" in fuente and "instalacion.render_pestana" in fuente
```
- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_ui_acerca.py tests/unit/test_ui_instalacion.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'acerca' from 'ui.paginas'`.
```bash
git add tests/unit/test_ui_acerca.py tests/unit/test_ui_instalacion.py
git commit -m "test(ui): acerca de y pestana Instalacion (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`ui/paginas/acerca.py`:
```python
"""Pantalla «Acerca de»: versión, revisiones de los dos esquemas, carpeta de datos y módulos
instalados (RF-99; spec S5 §5.2). Solo lee: no crea ni migra nada."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from dataclasses import dataclass

import streamlit as st

from operacion import config
from operacion.base_datos import Destino, leer_estado, revision_head
from operacion.version import a_semver, version
from ui.caso import ruta_caso

MODULOS: tuple[tuple[str, str], ...] = (
    ("Similitud de partidas", "sentence_transformers"),
    ("Anomalías de precios", "sklearn"),
    ("Planos IFC", "ifcopenshell"),
    ("Planos DXF", "ezdxf"),
    ("Informes PDF", "reportlab"),
    ("Datos del BCV", "xlrd"),
    ("Asistente de IA", "anthropic"),
)


@dataclass(frozen=True, slots=True)
class DatosAcerca:
    version: str
    semver: str
    revision_instalacion: str
    head_instalacion: str
    revision_caso: str
    head_caso: str
    carpeta_datos: str
    modulos: tuple[tuple[str, bool], ...]


def _instalado(nombre: str) -> bool:
    try:
        return importlib.util.find_spec(nombre) is not None
    except (ImportError, ValueError):
        return False


def _revision(ruta, destino: Destino) -> tuple[str, str]:
    head = revision_head(destino) or "sin revisiones"
    estado = leer_estado(ruta)
    if not estado.existe:
        return "sin base", head
    return (estado.revision or "sin alembic_version"), head


def datos_acerca(
    entorno=None, *, modulo_instalado: Callable[[str], bool] = _instalado
) -> DatosAcerca:
    ins, head_ins = _revision(config.ruta_instalacion(entorno), Destino.INSTALACION)
    caso, head_caso = _revision(ruta_caso(), Destino.CASO)
    return DatosAcerca(
        version=version(),
        semver=a_semver(version()),
        revision_instalacion=ins,
        head_instalacion=head_ins,
        revision_caso=caso,
        head_caso=head_caso,
        carpeta_datos=str(config.carpeta_datos(entorno)),
        modulos=tuple((nombre, modulo_instalado(paquete)) for nombre, paquete in MODULOS),
    )


def render() -> None:
    datos = datos_acerca()
    st.markdown(f"**Sílice {datos.semver}** (versión de `pyproject.toml`: {datos.version})")
    st.markdown(
        f"- Base de la instalación: `{datos.revision_instalacion}` "
        f"(la última es `{datos.head_instalacion}`)\n"
        f"- Base del caso abierto: `{datos.revision_caso}` "
        f"(la última es `{datos.head_caso}`)\n"
        f"- Carpeta de datos: `{datos.carpeta_datos}`"
    )
    st.subheader("Módulos")
    for nombre, instalado in datos.modulos:
        st.markdown(f"- {nombre}: {'instalado' if instalado else 'no instalado'}")
    st.caption("Sílice es software propietario; las licencias de terceros están en LICENCIAS.")
```
(Partir las líneas largas del f-string para ruff.)

`ui/paginas/instalacion.py`:
```python
"""Pestaña «Instalación» de Administración: red local y API, respaldos y eventos de seguridad
perdidos (RF-98; spec S5 §5.2 y §6.5). Los cambios de red no se hacen desde el navegador."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from operacion import base_datos, config, eventos_perdidos
from ui import cliente
from ui.texto_seguro import texto_seguro


@dataclass(frozen=True, slots=True)
class JuegoResumen:
    nombre: str
    motivo: str
    bases: int
    carpeta: Path


def juegos_de_respaldo(entorno=None) -> list[JuegoResumen]:
    carpeta = config.carpeta_respaldos(entorno)
    if not carpeta.is_dir():
        return []
    juegos = []
    for ruta in sorted(carpeta.iterdir(), reverse=True):
        try:
            ficha = json.loads((ruta / "ficha.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        juegos.append(
            JuegoResumen(
                ruta.name, str(ficha.get("motivo", "?")), len(ficha.get("bases", [])), ruta
            )
        )
    return juegos


def zip_del_juego(carpeta: Path) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zip_:
        for archivo in sorted(p for p in carpeta.rglob("*") if p.is_file()):
            zip_.write(archivo, archivo.relative_to(carpeta).as_posix())
    return memoria.getvalue()


def _red_y_api() -> None:
    ajustes = config.cargar_ajustes(config.ruta_ajustes())
    if ajustes.red_local:
        st.markdown(f"Red local: encendida en http://{ajustes.direccion}:{ajustes.puerto}")
    else:
        st.markdown(f"Red local: apagada (solo http://127.0.0.1:{ajustes.puerto})")
    st.markdown(
        f"API: {'activa' if ajustes.api_activa else 'apagada'} (puerto {ajustes.puerto_api})"
    )
    st.caption(
        "Para cambiar la red local use, en el equipo servidor, el acceso «Sílice: red local "
        "(administrador)». La API se activa en silice.toml y entra en vigor al reiniciar."
    )


def _respaldos() -> None:
    st.subheader("Respaldos")
    if st.button("Crear respaldo ahora", key="crear_respaldo"):
        st.success(f"Respaldo creado: {base_datos.respaldar_todo().name}")
    juegos = juegos_de_respaldo()
    for juego in juegos:
        st.markdown(f"- {juego.nombre} ({juego.motivo}, {juego.bases} bases)")
    if not juegos:
        st.caption("Todavía no hay respaldos.")
        return
    permitida, motivo = cliente.operacion_sensible_permitida()
    if not permitida:
        st.error(motivo)
        return
    elegido = st.selectbox("Descargar", [j.nombre for j in juegos], key="juego_elegido")
    st.warning(
        "El respaldo trae huellas de contraseñas y la clave de firma cifrada: guárdelo bien."
    )
    if st.button("Preparar descarga", key="preparar_descarga"):
        carpeta = next(j.carpeta for j in juegos if j.nombre == elegido)
        st.download_button("Descargar el juego (.zip)", zip_del_juego(carpeta), f"{elegido}.zip")


def _eventos() -> None:
    pendientes = eventos_perdidos.pendientes()
    if not pendientes:
        return
    st.error(
        "Las operaciones sensibles están bloqueadas: se restauró un respaldo y hay eventos de "
        "seguridad perdidos sin revisar."
    )
    for archivo in pendientes:
        datos = json.loads(archivo.read_text(encoding="utf-8")) if archivo.is_file() else {}
        with st.expander(archivo.name, expanded=True):
            for dif in datos.get("diferencias", []):
                st.markdown(
                    f"- {texto_seguro(str(dif.get('tipo')))}: "
                    f"{texto_seguro(str(dif.get('tabla')))} "
                    f"{texto_seguro(str(dif.get('etiqueta')))}"
                )
            st.markdown(
                f"Eventos de acceso posteriores al respaldo: {len(datos.get('eventos', []))}"
            )
            st.caption("Vuelva a aplicar lo que corresponda (revocar, desactivar) y luego marque.")
            confirmado = st.checkbox("Ya revisé esto", key=f"confirmar_{archivo.name}")
            if st.button(
                "Marcar como revisado", key=f"revisar_{archivo.name}", disabled=not confirmado
            ):
                eventos_perdidos.marcar_revisado(archivo, por="administrador")
                st.rerun()


def render_pestana() -> None:
    _red_y_api()
    _respaldos()
    _eventos()
```
(`st.checkbox`/`st.button` con `disabled`: en AppTest el botón no se pulsa si el checkbox no está
marcado; la prueba marca primero.)

`ui/app.py`: importar `acerca` (primero en la lista alfabética de `from ui.paginas import (...)`) y
agregar a `PAGINAS`, al final de la sección Trabajo:
`DefinicionPagina(acerca.render, "Acerca de Sílice", SECCION_TRABAJO),`.
`ui/paginas/administracion.py`: `from ui.paginas import instalacion` y, en `PESTANAS`, la tupla
`("Instalación", instalacion.render_pestana)`.
Correr `uv run pytest tests/unit -k "app or recorrido or pagina or administracion" -W error` y
ajustar
los conteos de pantallas que la lista nueva mueva (no están en el bloque de regresión).

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite)
Run: `uv run pytest tests/unit/test_ui_acerca.py tests/unit/test_ui_instalacion.py
tests/unit/test_ui_importable.py tests/unit/test_arquitectura_s5.py -v -W error`
y `uv run pytest -q -W error`. `uv run ruff check ui tests/unit/test_ui_acerca.py
tests/unit/test_ui_instalacion.py`.

- [ ] **Paso 5: Commit y PR (cierra `inc/100-s5-2-ui` y GS5-2)**
```bash
git add ui/paginas/acerca.py ui/paginas/instalacion.py ui/app.py ui/paginas/administracion.py tests/
git commit -m "feat(ui): acerca de, pestana Instalacion y aviso sin cifrar en el acceso" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-2-ui
gh pr create --base main --head inc/100-s5-2-ui \
  --title "S5-2: eventos perdidos, cliente local, three.js local y acerca de" --body-file -
```

### Compuerta GS5-2

- [ ] CI verde en Linux y Windows; `scripts/verificar_omitidas.py` en 0; `-W error`.
- [ ] RF-98 y RF-99 en verde: `uv run pytest -W error tests/unit/test_ajustes.py
  tests/unit/test_red.py tests/unit/test_lanzador.py tests/integration/test_arranque_real.py
  tests/unit/test_ordenes_100.py tests/integration/test_api_clave.py
  tests/unit/test_api_proteccion.py tests/unit/test_registro.py tests/unit/test_version.py
  tests/unit/test_eventos_perdidos.py tests/integration/test_restaurar_eventos.py
  tests/unit/test_ui_cliente.py tests/unit/test_ui_sin_cdn.py tests/unit/test_ui_acerca.py
  tests/unit/test_ui_instalacion.py tests/unit/test_arquitectura_s5.py`.
- [ ] `git diff origin/main --stat -- core/` vacío en cada rama; guardia del núcleo con salida 0.
- [ ] Bloque de regresión literal intacto (C5 de la meta).
- [ ] Bitácora `docs/bitacora/2026-10-silice-100.md`: compuerta GS5-2 anotada, con la salida de
  `uv run python scripts/meta_silice.py --version 1.0.0 --hasta S5-2 --junit reporte-pruebas.xml`.
- [ ] Encargos (maestro §6.4): requisitos, arquitectura, pruebas y calidad, verificador de hechos y,
  por ser S5, **seguridad** (API, red local, registro, eventos perdidos) y usabilidad (pestaña
  Instalación), aprobados.

---
## S5-3 · Instalador (RF-97, RNF-19, RNF-20)

### Tarea 13: manifiesto del instalador, cierre de importaciones y `operacion.programa`

**Rama:** `inc/100-s5-3-manifiesto` (sale de `origin/main` con GS5-2 cruzada)
**Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `instalador/manifiesto.toml`, `instalador/streamlit_config.toml`,
  `instalador/manifiesto.py`, `operacion/programa.py`
- Modificar: `operacion/ordenes_100.py` (orden `verificar-programa`)
- Prueba: `tests/unit/test_manifiesto.py`, `tests/unit/test_programa.py`

**Interfaces:**
- Consume: `tests.fixtures.arquitectura` (B1); `operacion.config` (T5).
- Produce:
  - `instalador.manifiesto`: `Manifiesto` (dataclass inmutable: `python`, `extras_basica`, `ifc`,
    `extras_similitud`, `paquetes`, `archivos`, `cierre_desde`, `datos_incluir`,
    `datos_excluir_sufijos`), `ManifiestoInvalido(ValueError)`, `cargar(ruta=RUTA_MANIFIESTO)`,
    `cierre_de_importaciones(raiz: Path, modulos: Sequence[str]) -> set[Path]`,
    `archivos_de_codigo(raiz: Path, m: Manifiesto) -> list[Path]`,
    `armar_arbol(raiz: Path, destino: Path, m: Manifiesto) -> list[Path]`,
    `RUTA_CONFIG_OFICIAL`.
  - `operacion.programa`: `NOMBRE = "manifiesto.json"`, `entrada(raiz_app, relativa) -> dict`,
    `escribir(raiz_app: Path, relativas: Iterable[str | Path], version: str) -> Path`,
    `leer(raiz_app: Path) -> dict`, `verificar(raiz_app: Path) -> list[str]`.
  - Orden `verificar-programa` (0 si `{app}` coincide con `manifiesto.json`, 1 si no).

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_manifiesto.py`:
```python
"""Lo que viaja en el instalador es exactamente lo del manifiesto (RF-97 h; spec S5 §7.1 y §12)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from instalador import manifiesto as mf

RAIZ = Path(__file__).resolve().parents[2]
PROHIBIDOS = ("tests/fixtures/bcv/", "tests/fixtures/bases/", "docs/", ".venv/", ".worktrees/")


def _entorno_limpio() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}


@pytest.fixture(scope="module")
def arbol(tmp_path_factory) -> Path:
    destino = tmp_path_factory.mktemp("producto") / "codigo"
    mf.armar_arbol(RAIZ, destino, mf.cargar())
    return destino


def test_el_manifiesto_declara_lo_que_decide_el_spec() -> None:
    m = mf.cargar()
    assert m.python == "3.13.13"
    assert "xgboost" not in m.extras_basica and "ml" not in m.extras_basica
    assert {"ui", "api", "planos", "informes", "bcv", "civil", "anomalias", "ia"} <= set(
        m.extras_basica
    )
    assert m.ifc is False  # RP10-4: bcf-client es GPLv3 hasta que S3-0 resuelva
    assert m.extras_similitud == ("similitud",)
    assert {"core", "adapters", "ml", "ui", "api", "operacion", "migraciones"} <= set(m.paquetes)
    assert "pyproject.toml" in m.archivos and "LICENSE" in m.archivos


def _repo_chico(raiz: Path) -> Path:
    archivos = {
        "scripts/__init__.py": "",
        "scripts/seed.py": "from tests.fixtures import base\nfrom . import hermano\n"
        "def f():\n    from scripts.diferido import g\n    return g\n",
        "scripts/hermano.py": "import json\n",
        "scripts/diferido.py": "def g(): ...\n",
        "scripts/inutil.py": "import tests.fixtures.otro\n",
        "tests/__init__.py": "",
        "tests/fixtures/__init__.py": "",
        "tests/fixtures/base.py": "import json\n",
        "tests/fixtures/otro.py": "",
    }
    for relativa, texto in archivos.items():
        ruta = raiz / relativa
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8")
    return raiz


def test_el_cierre_sigue_importaciones_absolutas_relativas_y_diferidas(tmp_path: Path) -> None:
    cierre = mf.cierre_de_importaciones(_repo_chico(tmp_path), ["scripts.seed"])
    assert {p.as_posix() for p in cierre} == {
        "scripts/__init__.py",
        "scripts/seed.py",
        "scripts/hermano.py",
        "scripts/diferido.py",
        "tests/__init__.py",
        "tests/fixtures/__init__.py",
        "tests/fixtures/base.py",
    }


def test_el_cierre_de_importaciones_de_la_siembra_esta_completo() -> None:
    m = mf.cargar()
    cierre = {p.as_posix() for p in mf.cierre_de_importaciones(RAIZ, m.cierre_desde)}
    assert {"scripts/seed.py", "scripts/seed_demo.py", "scripts/simular_lista.py"} <= cierre
    assert "tests/fixtures/apu_linea_base.py" in cierre  # scripts.seed lo importa (NORMAS §6)
    assert not [p for p in cierre if p.startswith(PROHIBIDOS) or p.endswith((".xls", ".xlsx"))]
    assert all(
        p.startswith(("scripts/", "tests/")) or p.split("/")[0] in m.paquetes for p in cierre
    )


def test_nunca_viajan_fixtures_bcv_bases_ni_db(arbol: Path) -> None:
    viajan = {p.relative_to(arbol).as_posix() for p in arbol.rglob("*") if p.is_file()}
    assert not [p for p in viajan if p.startswith(PROHIBIDOS)]
    assert not [p for p in viajan if p.endswith((".db", ".xls", ".xlsx", ".pyc"))]
    assert not [p for p in viajan if p.startswith("data/") and p.endswith(".pdf")]
    assert not [
        p
        for p in viajan
        if p.startswith("tests/")
        and not p.startswith("tests/fixtures/")
        and p not in {"tests/__init__.py"}
    ]


def test_un_unico_config_toml_y_es_el_oficial(arbol: Path) -> None:
    assert [p.relative_to(arbol).as_posix() for p in arbol.rglob("config.toml")] == [
        ".streamlit/config.toml"
    ]
    assert (
        arbol / ".streamlit" / "config.toml"
    ).read_bytes() == mf.RUTA_CONFIG_OFICIAL.read_bytes()


def test_la_configuracion_oficial_incluye_la_del_repositorio_y_las_opciones_fijas() -> None:
    oficial = tomllib.loads(mf.RUTA_CONFIG_OFICIAL.read_text(encoding="utf-8"))
    desarrollo = tomllib.loads((RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    for seccion, claves in desarrollo.items():
        for clave, valor in claves.items():
            assert oficial[seccion][clave] == valor, f"{seccion}.{clave}"
    assert oficial["server"]["address"] == "127.0.0.1" and oficial["server"]["headless"] is True
    assert (
        oficial["server"]["fileWatcherType"] == "none" and oficial["server"]["runOnSave"] is False
    )
    assert (
        oficial["client"]["toolbarMode"] == "minimal"
        and oficial["global"]["developmentMode"] is False
    )


def test_ui_y_api_se_importan_solo_con_el_arbol_del_manifiesto(arbol: Path) -> None:
    modulos = [
        "ui.app",
        "api.main",
        "operacion.__main__",
        "migraciones.comun",
        "scripts.seed",
        "scripts.seed_demo",
        "scripts.simular_lista",
    ]
    programa = (
        "import importlib, json\n"
        f"print(json.dumps({{n: importlib.import_module(n).__file__ for n in {modulos!r}}}))\n"
    )
    hijo = subprocess.run(
        [sys.executable, "-E", "-s", "-B", "-c", programa],
        cwd=arbol,
        env=_entorno_limpio(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert hijo.returncode == 0, hijo.stderr[-2000:]
    rutas = json.loads(hijo.stdout.splitlines()[-1])
    fuera = {
        n: r for n, r in rutas.items() if not Path(r).resolve().is_relative_to(arbol.resolve())
    }
    assert fuera == {}, (
        fuera
    )  # nada se importó del repositorio: todo salió del árbol del manifiesto


def test_la_demostracion_se_siembra_con_el_arbol_del_manifiesto(
    arbol: Path, tmp_path: Path
) -> None:
    destino = tmp_path / "demo.db"
    programa = (
        f"from scripts.seed_demo import main\nraise SystemExit(main(['--db', {str(destino)!r}]))\n"
    )
    hijo = subprocess.run(
        [sys.executable, "-E", "-s", "-B", "-c", programa],
        cwd=arbol,
        env=_entorno_limpio(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert hijo.returncode == 0, hijo.stderr[-2000:]
    assert destino.stat().st_size > 0


def test_un_paquete_declarado_que_no_existe_falla(tmp_path: Path) -> None:
    m = mf.cargar()
    roto = replace(m, paquetes=(*m.paquetes, "no_existe"))
    with pytest.raises(mf.ManifiestoInvalido, match="no_existe"):
        mf.archivos_de_codigo(RAIZ, roto)


def test_un_dato_prohibido_hace_fallar_el_armado() -> None:
    m = mf.cargar()
    roto = replace(m, datos_incluir=(*m.datos_incluir, "docs"))
    with pytest.raises(mf.ManifiestoInvalido, match="docs/"):
        mf.archivos_de_codigo(RAIZ, roto)


def test_nadie_fuera_de_tests_importa_instalador() -> None:
    from tests.fixtures.arquitectura import archivos, importaciones, ruta

    infractores = sorted(
        ruta(a)
        for paquete in ("core", "adapters", "ml", "ui", "api", "operacion", "migraciones")
        for a in archivos(paquete)
        if any(m == "instalador" or m.startswith("instalador.") for m in importaciones(a))
    )
    assert infractores == []
```
(`instalador/` no viaja: por eso la lista de módulos del hijo no lo incluye.)

`tests/unit/test_programa.py`:
```python
"""manifiesto.json del programa instalado y `verificar-programa` (spec S5 §10.4 y §11.2)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from operacion import __main__ as cli
from operacion import config, programa


@pytest.fixture
def app(tmp_path: Path) -> Path:
    (tmp_path / "codigo" / "ui").mkdir(parents=True)
    (tmp_path / "python").mkdir()
    (tmp_path / "codigo" / "ui" / "app.py").write_text("print('hola')\n", encoding="utf-8")
    (tmp_path / "codigo" / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "python" / "python.exe").write_bytes(b"MZ fake")
    programa.escribir(
        tmp_path, ["codigo/ui/app.py", "codigo/pyproject.toml", "python/python.exe"], "1.0.0"
    )
    return tmp_path


def test_el_manifiesto_lista_cada_archivo_con_ruta_tamano_y_huella(app: Path) -> None:
    datos = json.loads((app / "manifiesto.json").read_text(encoding="utf-8"))
    assert datos["formato"] == "silice-manifiesto" and datos["version"] == "1.0.0"
    por_ruta = {a["ruta"]: a for a in datos["archivos"]}
    assert list(por_ruta) == sorted(por_ruta)
    contenido = (app / "codigo" / "ui" / "app.py").read_bytes()
    assert por_ruta["codigo/ui/app.py"] == {
        "ruta": "codigo/ui/app.py",
        "tamano": len(contenido),
        "sha256": hashlib.sha256(contenido).hexdigest(),
    }


def test_un_programa_intacto_no_tiene_diferencias(app: Path) -> None:
    assert programa.verificar(app) == []


def test_verificar_detecta_distinto_falta_y_sobra(app: Path) -> None:
    (app / "codigo" / "ui" / "app.py").write_text("print('otro')\n", encoding="utf-8")
    (app / "python" / "python.exe").unlink()
    (app / "codigo" / "extra.py").write_text("x = 1\n", encoding="utf-8")
    assert programa.verificar(app) == [
        "distinto codigo/ui/app.py",
        "falta python/python.exe",
        "sobra codigo/extra.py",
    ]


def test_sin_manifiesto_no_es_una_instalacion(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        programa.verificar(tmp_path)


def test_la_orden_verificar_programa(app: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(config, "RAIZ", app / "codigo")
    assert cli.main(["verificar-programa"]) == 0 and "coincide" in capsys.readouterr().out
    (app / "codigo" / "pyproject.toml").write_text("alterado", encoding="utf-8")
    assert cli.main(["verificar-programa"]) == 1
    assert "distinto codigo/pyproject.toml" in capsys.readouterr().err


def test_la_orden_verificar_programa_en_desarrollo_lo_dice(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(config, "RAIZ", tmp_path / "codigo")
    assert cli.main(["verificar-programa"]) == 1
    assert "no es una instalación" in capsys.readouterr().err
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_manifiesto.py tests/unit/test_programa.py -v -W error`
Esperado: FAIL con `ModuleNotFoundError: No module named 'instalador'` y `... 'operacion.programa'`.
```bash
git add tests/unit/test_manifiesto.py tests/unit/test_programa.py
git commit -m "test(instalador): manifiesto, cierre de importaciones y verificar-programa (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

(`instalador/__init__.py` ya lo creó la Tarea 2.)

`instalador/manifiesto.toml`:
```toml
# Lo que viaja en el instalador (spec S5 §7.1 y §7.2). Lista blanca: lo que no está aquí no viaja.

[python]
# CPython autónomo de python-build-standalone que instala `uv` (3.13.13 en uv 0.11.9, 2026-10-11).
version = "3.13.13"

[capas]
# Extras de pyproject.toml de la capa básica. `xgboost` y `ml` nunca (ningún código los importa).
basica = ["ui", "api", "planos", "informes", "bcv", "civil", "anomalias", "ia"]
# `ifctester` (extra `ifc`) arrastra `bcf-client`, GPLv3, incompatible con la licencia propietaria
# (RP10-4). Pasa a true solo con un ruling que cite la resolución de S3-0.
ifc = false
# Capa opcional del instalador completo: paquetes + modelo, en `modulos\similitud`.
similitud = ["similitud"]

[codigo]
paquetes = [
  "core", "adapters", "ml", "ui", "api", "operacion", "migraciones",
  "seguridad", "paquete", "asistente",
]
archivos = ["pyproject.toml", "LICENSE"]
# De scripts/ y tests/fixtures/ viaja solo el cierre de importaciones de estos módulos (RV-25).
cierre_desde = [
  "scripts.seed", "scripts.seed_demo", "scripts.seed_industrial", "scripts.seed_of001",
  "scripts.seed_sistemas", "scripts.seed_telecom", "scripts.simular_lista",
]

[datos]
# Lista blanca de data/. Los PDF de MaPreX no viajan mientras su redistribución no esté aclarada
# (pregunta 12); los .xls del BCV tampoco (P6): cada empresa descarga los suyos.
incluir = [
  "data/samples", "data/civil", "data/industrial", "data/precios/maprex_2026-07/*.csv",
]
excluir_sufijos = [".pdf", ".db", ".xls", ".xlsx"]
```

`instalador/streamlit_config.toml`:
```toml
# Configuración oficial de Streamlit de {app}\codigo (spec S5 §10.1). Es el ÚNICO config.toml que
# puede haber dentro de codigo\ (tests/unit/test_manifiesto.py). Contiene todo lo de
# .streamlit/config.toml del repositorio y las opciones fijas de la segunda capa.

[global]
developmentMode = false

[server]
address = "127.0.0.1"
headless = true
fileWatcherType = "none"
runOnSave = false
enableCORS = true
enableXsrfProtection = true
# MB; el mismo límite que los planos (RNF-12)
maxUploadSize = 20

[browser]
serverAddress = "127.0.0.1"
gatherUsageStats = false

[client]
showErrorDetails = "none"
toolbarMode = "minimal"
```

`instalador/manifiesto.py`:
```python
"""Qué archivos viajan en el instalador y cómo se arma el árbol `{app}\\codigo` (spec S5 §7.1).

Lista blanca (`manifiesto.toml`): los paquetes del producto completos, de `scripts/` y
`tests/fixtures/` solo el cierre de importaciones de los sembradores y del simulador (calculado
leyendo el árbol sintáctico), la lista blanca de `data/`, `pyproject.toml` y `LICENSE`, más el
`config.toml` oficial. Todo lo demás (`.venv`, `*.db`, `docs/`, los `.xls` del BCV, las bases de
prueba) está prohibido y, si algo lo trae, el armado falla en vez de copiarlo.
"""

from __future__ import annotations

import ast
import shutil
import tomllib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_MANIFIESTO = Path(__file__).with_name("manifiesto.toml")
RUTA_CONFIG_OFICIAL = Path(__file__).with_name("streamlit_config.toml")
RAICES_PROPIAS = frozenset(
    {
        "core",
        "adapters",
        "ml",
        "ui",
        "api",
        "operacion",
        "migraciones",
        "seguridad",
        "paquete",
        "asistente",
        "scripts",
        "tests",
    }
)
DIRECTORIOS_EXCLUIDOS = frozenset(
    {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".venv", "node_modules"}
)
SUFIJOS_EXCLUIDOS = frozenset(
    {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".db-journal", ".db-wal", ".db-shm"}
)
PROHIBIDOS = (
    "tests/fixtures/bcv/",
    "tests/fixtures/bases/",
    "docs/",
    ".venv/",
    ".worktrees/",
    "data/apu.db",
    "data/casos/",
    "data/respaldos/",
)


class ManifiestoInvalido(ValueError):  # noqa: N818
    pass


@dataclass(frozen=True, slots=True)
class Manifiesto:
    python: str
    extras_basica: tuple[str, ...]
    ifc: bool
    extras_similitud: tuple[str, ...]
    paquetes: tuple[str, ...]
    archivos: tuple[str, ...]
    cierre_desde: tuple[str, ...]
    datos_incluir: tuple[str, ...]
    datos_excluir_sufijos: tuple[str, ...]


def cargar(ruta: Path = RUTA_MANIFIESTO) -> Manifiesto:
    datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    try:
        ifc = datos["capas"]["ifc"]
        if not isinstance(ifc, bool):
            raise ManifiestoInvalido("capas.ifc debe ser true o false")
        return Manifiesto(
            python=str(datos["python"]["version"]),
            extras_basica=tuple(datos["capas"]["basica"]),
            ifc=ifc,
            extras_similitud=tuple(datos["capas"]["similitud"]),
            paquetes=tuple(datos["codigo"]["paquetes"]),
            archivos=tuple(datos["codigo"]["archivos"]),
            cierre_desde=tuple(datos["codigo"]["cierre_desde"]),
            datos_incluir=tuple(datos["datos"]["incluir"]),
            datos_excluir_sufijos=tuple(datos["datos"]["excluir_sufijos"]),
        )
    except KeyError as error:
        raise ManifiestoInvalido(f"{ruta.name}: falta la clave {error}") from error


def _modulo_a_archivo(raiz: Path, modulo: str) -> Path | None:
    base = raiz.joinpath(*modulo.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def _importados(raiz: Path, archivo: Path) -> set[str]:
    """Módulos propios que `archivo` importa, en cualquier parte (también dentro de funciones)."""
    paquete = ".".join(archivo.relative_to(raiz).parent.parts)
    encontrados: set[str] = set()
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            encontrados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            base = nodo.module or ""
            if nodo.level:
                partes = paquete.split(".") if paquete else []
                partes = partes[: len(partes) - (nodo.level - 1)]
                base = ".".join([*partes, *([nodo.module] if nodo.module else [])])
            encontrados.add(base)
            encontrados.update(f"{base}.{alias.name}" for alias in nodo.names)
    return {m for m in encontrados if m and m.split(".")[0] in RAICES_PROPIAS}


def cierre_de_importaciones(raiz: Path, modulos: Sequence[str]) -> set[Path]:
    """Los archivos de los módulos de partida y de todo lo propio que importan, con los
    `__init__.py` de sus paquetes. Rutas relativas a `raiz`."""
    vistos: set[Path] = set()
    pendientes = list(modulos)
    while pendientes:
        modulo = pendientes.pop()
        archivo = _modulo_a_archivo(raiz, modulo)
        if archivo is None:
            continue
        partes = modulo.split(".")
        for n in range(1, len(partes)):
            inicio = raiz.joinpath(*partes[:n], "__init__.py")
            if inicio.is_file() and inicio not in vistos:
                vistos.add(inicio)
                pendientes.extend(_importados(raiz, inicio))
        if archivo not in vistos:
            vistos.add(archivo)
            pendientes.extend(_importados(raiz, archivo))
    return {a.relative_to(raiz) for a in vistos}


def _recorrer(carpeta: Path, raiz: Path) -> Iterator[Path]:
    for ruta in sorted(carpeta.rglob("*")):
        if not ruta.is_file():
            continue
        relativa = ruta.relative_to(raiz)
        if DIRECTORIOS_EXCLUIDOS & set(relativa.parts) or ruta.suffix in SUFIJOS_EXCLUIDOS:
            continue
        yield relativa


def _datos(raiz: Path, m: Manifiesto) -> set[Path]:
    salida: set[Path] = set()
    for patron in m.datos_incluir:
        if any(c in patron for c in "*?["):
            coincidencias = [p for p in raiz.glob(patron) if p.is_file()]
        elif (raiz / patron).is_dir():
            coincidencias = [p for p in (raiz / patron).rglob("*") if p.is_file()]
        elif (raiz / patron).is_file():
            coincidencias = [raiz / patron]
        else:
            raise ManifiestoInvalido(f"el dato declarado no existe: {patron}")
        for ruta in coincidencias:
            if ruta.suffix.lower() not in m.datos_excluir_sufijos:
                salida.add(ruta.relative_to(raiz))
    return salida


def archivos_de_codigo(raiz: Path, m: Manifiesto) -> list[Path]:
    """Los archivos que viajan, relativos a `raiz`, ordenados. Falla si falta algo declarado o si
    algo prohibido se cuela."""
    salida: set[Path] = set()
    for paquete in m.paquetes:
        carpeta = raiz / paquete
        if not carpeta.is_dir():
            raise ManifiestoInvalido(f"el paquete declarado no existe: {paquete}")
        salida.update(_recorrer(carpeta, raiz))
    salida.update(cierre_de_importaciones(raiz, m.cierre_desde))
    for archivo in m.archivos:
        if not (raiz / archivo).is_file():
            raise ManifiestoInvalido(f"el archivo declarado no existe: {archivo}")
        salida.add(Path(archivo))
    salida.update(_datos(raiz, m))
    prohibidos = sorted(
        p.as_posix()
        for p in salida
        if p.as_posix().startswith(PROHIBIDOS) or p.suffix in SUFIJOS_EXCLUIDOS
    )
    if prohibidos:
        raise ManifiestoInvalido("archivos prohibidos en el instalador: " + ", ".join(prohibidos))
    return sorted(salida)


def armar_arbol(raiz: Path, destino: Path, m: Manifiesto) -> list[Path]:
    """Copia los archivos del manifiesto a `destino` (= `{app}\\codigo`) y deja el `config.toml`
    oficial como único `.streamlit/config.toml`. Devuelve las rutas relativas copiadas."""
    archivos = archivos_de_codigo(raiz, m)
    for relativa in archivos:
        origen, copia = raiz / relativa, destino / relativa
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, copia)
    oficial = destino / ".streamlit" / "config.toml"
    oficial.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUTA_CONFIG_OFICIAL, oficial)
    return [*archivos, Path(".streamlit/config.toml")]
```

`operacion/programa.py`:
```python
"""El programa instalado contra su `manifiesto.json` (spec S5 §7.1, §10.4 y §11.2).

El instalador deja `{app}\\manifiesto.json` con ruta, tamaño y SHA-256 de cada archivo de
`codigo\\` y del `python.exe`. `verificar` dice qué cambió desde la instalación; en el
repositorio de desarrollo no hay manifiesto y no tiene sentido.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

NOMBRE = "manifiesto.json"
FORMATO = "silice-manifiesto"


def _sha256(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def entrada(raiz_app: Path, relativa: str) -> dict[str, object]:
    ruta = raiz_app / relativa
    return {"ruta": relativa, "tamano": ruta.stat().st_size, "sha256": _sha256(ruta)}


def escribir(raiz_app: Path, relativas: Iterable[str | Path], version: str) -> Path:
    rutas = sorted({Path(r).as_posix() for r in relativas})
    datos = {
        "formato": FORMATO,
        "version": version,
        "archivos": [entrada(raiz_app, r) for r in rutas],
    }
    destino = raiz_app / NOMBRE
    destino.write_text(json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return destino


def leer(raiz_app: Path) -> dict:
    datos = json.loads((raiz_app / NOMBRE).read_text(encoding="utf-8"))
    if datos.get("formato") != FORMATO:
        raise ValueError(f"{NOMBRE} no es un manifiesto de Sílice")
    return datos


def verificar(raiz_app: Path) -> list[str]:
    """Diferencias: `distinto X`, `falta X` y `sobra X` (solo bajo `codigo/`)."""
    esperado = {a["ruta"]: a for a in leer(raiz_app)["archivos"]}
    diferencias = []
    for ruta, datos in esperado.items():
        archivo = raiz_app / ruta
        if not archivo.is_file():
            diferencias.append(f"falta {ruta}")
        elif archivo.stat().st_size != datos["tamano"] or _sha256(archivo) != datos["sha256"]:
            diferencias.append(f"distinto {ruta}")
    codigo = raiz_app / "codigo"
    if codigo.is_dir():
        presentes = {p.relative_to(raiz_app).as_posix() for p in codigo.rglob("*") if p.is_file()}
        diferencias.extend(f"sobra {ruta}" for ruta in sorted(presentes - set(esperado)))
    return sorted(diferencias, key=lambda d: (d.split(" ", 1)[0] != "distinto", d))
```
(El orden de `verificar` es: primero `distinto`, luego `falta`, luego `sobra`, cada grupo ordenado;
es el que fija `test_verificar_detecta_distinto_falta_y_sobra`: `falta` < `sobra` alfabéticamente.)

`operacion/ordenes_100.py`: agregar el manejador y su parser:
```python
def _verificar_programa(_argumentos: argparse.Namespace) -> int:
    from operacion import programa

    try:
        diferencias = programa.verificar(config.RAIZ.parent)
    except FileNotFoundError:
        print("Esto no es una instalación de Sílice (falta manifiesto.json).", file=sys.stderr)
        return 1
    if diferencias:
        print("\n".join(diferencias), file=sys.stderr)
        return 1
    print("El programa coincide con su manifiesto.")
    return 0
```
en `registrar`: `ordenes.add_parser("verificar-programa", help="compara {app} con manifiesto.json")`
y
`tabla["verificar-programa"] = _verificar_programa`.

`tests/unit/test_arquitectura.py:18`: sumar `"instalador"` a `PAQUETES_FUERA_DEL_NUCLEO`;
`pyproject.toml`:
sumar `"instalador"` a `known-first-party`; `tests/unit/test_arquitectura_s5.py` no cambia (la regla
de que nadie importa `instalador` vive en `test_manifiesto.py`).

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_manifiesto.py tests/unit/test_programa.py
tests/unit/test_arquitectura.py -v -W error`.
Si `test_la_demostracion_se_siembra…` falla por un dato que el sembrador lee de `data/`, se agrega
**ese** archivo (no la carpeta) a `datos_incluir` y se anota en la bitácora; si
`test_el_cierre…` o `test_nunca_viajan…` encuentran algo de `tests/fixtures/bcv/`, el sembrador
importa lo que no debe: se corrige el sembrador, no la prohibición.
`uv run ruff check instalador operacion/programa.py tests/unit/test_manifiesto.py
tests/unit/test_programa.py`.

- [ ] **Paso 5: Commit y PR (cierra `inc/100-s5-3-manifiesto`)**
```bash
git add instalador operacion/programa.py operacion/ordenes_100.py
git commit -m "feat(instalador): manifiesto en lista blanca y verificar-programa" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-3-manifiesto
gh pr create --base main --head inc/100-s5-3-manifiesto \
  --title "S5-3: manifiesto del instalador" --body-file -
```

---

### Tarea 14: `instalador/construir.py`, `licencias.py` y `tamanos.py`

**Rama:** `inc/100-s5-3-instalador` (sale de `origin/main` con T3 y T13 fusionadas)
**Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `instalador/construir.py`, `instalador/licencias.py`, `instalador/tamanos.py`
- Modificar: `.gitignore` (`build/`, `publicacion/`, `humo-salida/`)
- Prueba: `tests/unit/test_construir.py`, `tests/unit/test_licencias.py`,
  `tests/unit/test_tamanos.py`

**Interfaces:**
- Consume: `instalador.manifiesto` (T13), `operacion.programa` (T13), `operacion.firma_sumas`
  (`formatear_sumas`, T3), `operacion.version` (T4), `ml.normalization.MODELO_POR_DEFECTO` (A18).
- Produce, en `instalador.construir`:
  - `Rutas(raiz=RAIZ)` con `build`, `py`, `app`, `salida`;
  - `paquetes_de(requisitos: str) -> dict[str, str]`, `solo_los_nuevos(basica: str, completa: str)
    -> str`,
    `extras_de(m: Manifiesto, similitud: bool) -> list[str]`,
    `exportar(extras, salida, ejecutar)`, `instalar_python(version, rutas, ejecutar) -> Path`,
    `instalar_capa(python, requisitos, ejecutar)`,
    `instalar_similitud(python, requisitos, destino, ejecutar)`, `escribir_pth(app)`,
    `descargar_modelo(python, app, ejecutar)`, `licencias(python, app, ejecutar)`,
    `copiar_codigo(m, destino)`, `compilar(python, codigo, ejecutar)`,
    `escribir_manifiesto_json(app, version)`, `asegurar_bom(origen, destino) -> Path`,
    `buscar_iscc(entorno=None, existe=...) -> Path`,
    `comando_iscc(iscc, iss, version, perfil, rutas) -> list[str]`,
    `nombre_instalador(version, perfil) -> str`, `escribir_sumas(carpeta, perfil, extras) -> Path`,
    `construir(perfil, *, version=None, solo_iss=False, rutas=None, ejecutar=...) -> list[Path]`,
    `main(argv)`.
  - `instalador.licencias`: `main(argv)` (se corre con el Python **construido**, solo biblioteca
    estándar).
  - `instalador.tamanos`: `MB = 1_000_000`, `LIMITES = {"basico": 150 * MB, "completo": 650 * MB}`,
    `evaluar(perfil, bytes_) -> tuple[bool, str]`, `medir(carpeta, version, perfil) -> dict`,
    `main(argv)`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_tamanos.py`:
```python
"""Tamaño de los instaladores contra RNF-19 (spec S5 §4.3 y §7.2; RP10-6: 1 MB = 10^6 bytes)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from instalador import tamanos


@pytest.mark.parametrize(
    ("perfil", "bytes_", "ok"),
    [
        ("basico", 150_000_000, True),
        ("basico", 150_000_001, False),
        ("completo", 650_000_000, True),
        ("completo", 650_000_001, False),
        ("basico", 0, False),
    ],
)
def test_el_limite_es_exacto(perfil: str, bytes_: int, ok: bool) -> None:
    assert tamanos.evaluar(perfil, bytes_)[0] is ok


def test_un_perfil_desconocido_se_rechaza() -> None:
    with pytest.raises(ValueError, match="perfil"):
        tamanos.evaluar("gigante", 1)


def test_medir_lee_el_exe_de_la_version_y_deja_el_json(tmp_path: Path) -> None:
    (tmp_path / "Silice-1.0.0-rc.1.exe").write_bytes(b"x" * 1234)
    (tmp_path / "Silice-1.0.0-rc.1-completo.exe").write_bytes(b"y" * 99)
    basico = tamanos.medir(tmp_path, "1.0.0-rc.1", "basico")
    completo = tamanos.medir(tmp_path, "1.0.0-rc.1", "completo")
    assert basico["bytes"] == 1234 and completo["bytes"] == 99 and basico["limite"] == 150_000_000


def test_main_escribe_el_json_y_sale_con_1_si_se_pasa(tmp_path: Path) -> None:
    (tmp_path / "Silice-1.0.0.exe").write_bytes(b"x" * 10)
    salida = tmp_path / "tamanos-basico.json"
    assert (
        tamanos.main(
            [
                "--perfil",
                "basico",
                "--carpeta",
                str(tmp_path),
                "--version",
                "1.0.0",
                "--salida",
                str(salida),
            ]
        )
        == 0
    )
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["ok"] is True and datos["perfil"] == "basico" and datos["version"] == "1.0.0"
    (tmp_path / "Silice-1.0.0.exe").write_bytes(b"x" * 150_000_001)
    assert (
        tamanos.main(
            [
                "--perfil",
                "basico",
                "--carpeta",
                str(tmp_path),
                "--version",
                "1.0.0",
                "--salida",
                str(salida),
            ]
        )
        == 1
    )
    assert json.loads(salida.read_text(encoding="utf-8"))["ok"] is False


def test_sin_el_exe_es_un_error_claro(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Silice-9.9.9.exe"):
        tamanos.medir(tmp_path, "9.9.9", "basico")
```

`tests/unit/test_licencias.py`:
```python
"""LICENCIAS\\: la de Python y la de cada paquete incluido (spec S5 §7.1 paso 5; P9)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "instalador" / "licencias.py"


def _dist(
    sitio: Path, nombre: str, version: str, licencia: str | None, archivo: str | None
) -> None:
    info = sitio / f"{nombre}-{version}.dist-info"
    (info / "licenses").mkdir(parents=True)
    meta = f"Metadata-Version: 2.1\nName: {nombre}\nVersion: {version}\n"
    if licencia:
        meta += f"License-Expression: {licencia}\n"
    (info / "METADATA").write_text(meta, encoding="utf-8")
    registro = ["METADATA,,"]
    if archivo:
        (info / "licenses" / archivo).write_text(
            f"Texto de la licencia de {nombre}\n", encoding="utf-8"
        )
        registro.append(f"{nombre}-{version}.dist-info/licenses/{archivo},,")
    (info / "RECORD").write_text("\n".join(registro) + "\n", encoding="utf-8")


def _correr(sitio: Path, salida: Path, python_licencia: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-S",
            str(SCRIPT),
            "--salida",
            str(salida),
            "--solo-ruta",
            str(sitio),
            "--python-licencia",
            str(python_licencia),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_copia_la_licencia_de_cada_paquete_y_la_de_python(tmp_path: Path) -> None:
    sitio, salida = tmp_path / "sitio", tmp_path / "LICENCIAS"
    sitio.mkdir()
    _dist(sitio, "alfa", "1.0", "MIT", "LICENSE")
    _dist(sitio, "beta", "2.0", "Apache-2.0", "LICENSE.txt")
    psf = tmp_path / "LICENSE.txt"
    psf.write_text("PSF", encoding="utf-8")
    resultado = _correr(sitio, salida, psf)
    assert resultado.returncode == 0, resultado.stderr
    assert (salida / "Python" / "LICENSE.txt").read_text(encoding="utf-8") == "PSF"
    assert "Texto de la licencia de alfa" in (salida / "alfa-1.0" / "LICENSE").read_text(
        encoding="utf-8"
    )
    indice = (salida / "INDICE.md").read_text(encoding="utf-8")
    assert "| alfa | 1.0 | MIT |" in indice and "| beta | 2.0 | Apache-2.0 |" in indice


def test_un_paquete_sin_licencia_ni_texto_hace_fallar(tmp_path: Path) -> None:
    sitio = tmp_path / "sitio"
    sitio.mkdir()
    _dist(sitio, "huerfano", "0.1", None, None)
    psf = tmp_path / "LICENSE.txt"
    psf.write_text("PSF", encoding="utf-8")
    resultado = _correr(sitio, tmp_path / "L", psf)
    assert resultado.returncode == 1 and "huerfano" in resultado.stderr


def test_sin_la_licencia_de_python_falla(tmp_path: Path) -> None:
    sitio = tmp_path / "sitio"
    sitio.mkdir()
    _dist(sitio, "alfa", "1.0", "MIT", "LICENSE")
    resultado = _correr(sitio, tmp_path / "L", tmp_path / "no_existe.txt")
    assert resultado.returncode == 1 and "Python" in resultado.stderr
```

`tests/unit/test_construir.py`:
```python
"""Construcción del instalador: órdenes de uv, capas, BOM y encadenado (spec S5 §7.1; RNF-20)."""

from __future__ import annotations

import hashlib
import json
import ntpath
from dataclasses import replace
from pathlib import Path

import pytest

from instalador import construir as c
from instalador.manifiesto import cargar

BASICA = "alfa==1.0 ; sys_platform == 'win32'\nBeta_Uno==2.0\n# via x\n-e .\ngamma==3.0.post1\n"
COMPLETA = (
    BASICA + "sentence-transformers==5.0.0\ntorch==2.9.0 ; sys_platform == 'win32'\nbeta-uno==2.0\n"
)


def test_paquetes_de_normaliza_nombres_y_salta_comentarios() -> None:
    assert c.paquetes_de(BASICA) == {"alfa": "1.0", "beta-uno": "2.0", "gamma": "3.0.post1"}


def test_solo_los_nuevos_quita_lo_que_la_basica_ya_trae() -> None:
    nuevos = c.solo_los_nuevos(BASICA, COMPLETA)
    assert nuevos.splitlines() == [
        "sentence-transformers==5.0.0",
        "torch==2.9.0 ; sys_platform == 'win32'",
    ]


def test_los_extras_del_completo_suman_similitud_y_el_ifc_solo_si_el_manifiesto_lo_pide() -> None:
    m = cargar()
    assert "similitud" not in c.extras_de(m, similitud=False)
    assert c.extras_de(m, similitud=True)[-1] == "similitud"
    assert "ifc" not in c.extras_de(m, similitud=False)
    con_ifc = replace(m, ifc=True)
    assert "ifc" in c.extras_de(con_ifc, similitud=False)


class Grabador:
    def __init__(self) -> None:
        self.ordenes: list[list[str]] = []

    def __call__(self, orden, entorno=None, cwd=None) -> None:
        self.ordenes.append([str(p) for p in orden])
        if list(orden[:2]) == ["uv", "export"]:
            destino = Path(orden[orden.index("--output-file") + 1])
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(COMPLETA if "similitud" in orden else BASICA, encoding="utf-8")
        if orden[:3] == ["uv", "python", "install"]:
            destino = Path(orden[orden.index("--install-dir") + 1])
            exe = destino / f"cpython-{orden[3]}-windows-x86_64-none" / "python.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"MZ")


def test_las_ordenes_de_uv_son_las_del_spec(tmp_path: Path) -> None:
    rutas, ejecutar = c.Rutas(tmp_path), Grabador()
    python = c.instalar_python("3.13.13", rutas, ejecutar)
    assert python == rutas.app / "python" / "python.exe" and python.is_file()
    assert ejecutar.ordenes[0] == [
        "uv",
        "python",
        "install",
        "3.13.13",
        "--install-dir",
        str(rutas.py),
    ]
    c.exportar(["ui", "api"], tmp_path / "req.txt", ejecutar)
    assert ejecutar.ordenes[1] == [
        "uv",
        "export",
        "--frozen",
        "--no-dev",
        "--no-emit-project",
        "--no-hashes",
        "--extra",
        "ui",
        "--extra",
        "api",
        "--output-file",
        str(tmp_path / "req.txt"),
    ]
    c.instalar_capa(python, tmp_path / "req.txt", ejecutar)
    assert ejecutar.ordenes[2] == [
        "uv",
        "pip",
        "install",
        "--python",
        str(python),
        "--break-system-packages",
        "--compile-bytecode",
        "--no-deps",
        "-r",
        str(tmp_path / "req.txt"),
    ]
    c.instalar_similitud(python, tmp_path / "nuevos.txt", tmp_path / "paq", ejecutar)
    assert ejecutar.ordenes[3] == [
        "uv",
        "pip",
        "install",
        "--python",
        str(python),
        "--target",
        str(tmp_path / "paq"),
        "--no-deps",
        "--compile-bytecode",
        "-r",
        str(tmp_path / "nuevos.txt"),
    ]


def test_sin_python_exe_la_construccion_falla_con_mensaje(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="uv no dejó"):
        c.instalar_python("3.13.13", c.Rutas(tmp_path), lambda *a, **k: None)


def test_el_pth_apunta_a_modulos_similitud_desde_site_packages(tmp_path: Path) -> None:
    c.escribir_pth(tmp_path)
    linea = (tmp_path / "silice_similitud.pth").read_text(encoding="utf-8").strip()
    # lo que hace `site.addpackage` en Windows: une la línea a la carpeta del .pth y normaliza
    sitio = r"C:\Prueba\python\Lib\site-packages"
    assert ntpath.normpath(ntpath.join(sitio, linea)) == r"C:\Prueba\modulos\similitud\paquetes"


def test_el_iss_se_compila_desde_una_copia_con_bom_utf8(tmp_path: Path) -> None:
    origen = tmp_path / "silice.iss"
    origen.write_bytes("; Sílice\n[Setup]\n".encode())
    copia = c.asegurar_bom(origen, tmp_path / "build" / "silice.iss")
    datos = copia.read_bytes()
    assert datos.startswith(b"\xef\xbb\xbf") and datos[3:].decode("utf-8") == "; Sílice\n[Setup]\n"
    origen.write_bytes(b"\xef\xbb\xbf; ya trae BOM\n")
    assert c.asegurar_bom(origen, tmp_path / "otra.iss").read_bytes().count(b"\xef\xbb\xbf") == 1


def test_buscar_iscc_prueba_las_ubicaciones_conocidas(tmp_path: Path) -> None:
    pf = tmp_path / "pf86"
    exe = pf / "Inno Setup 6" / "ISCC.exe"
    entorno = {"ProgramFiles(x86)": str(pf), "PATH": ""}
    assert c.buscar_iscc(entorno, existe=lambda p: Path(p) == exe) == exe
    with pytest.raises(FileNotFoundError, match="Inno Setup"):
        c.buscar_iscc(entorno, existe=lambda p: False)


def test_el_comando_de_iscc_lleva_version_perfil_y_carpetas(tmp_path: Path) -> None:
    rutas = c.Rutas(tmp_path)
    iss = rutas.build / "silice.iss"
    comando = c.comando_iscc(Path("ISCC.exe"), iss, "1.0.0-rc.1", "completo", rutas)
    assert comando[0] == "ISCC.exe" and comando[-1].endswith("silice.iss")
    assert "/DVersion=1.0.0-rc.1" in comando and "/DCompleto" in comando
    assert "/DCompleto" not in c.comando_iscc(Path("ISCC.exe"), iss, "1.0.0", "basico", rutas)
    assert f"/DOrg={rutas.app}" in comando and f"/DSalida={rutas.salida}" in comando
    assert f"/DRaiz={tmp_path}" in comando


def test_el_nombre_del_instalador() -> None:
    assert c.nombre_instalador("1.0.0", "basico") == "Silice-1.0.0.exe"
    assert c.nombre_instalador("1.0.0-rc.1", "completo") == "Silice-1.0.0-rc.1-completo.exe"


def test_las_sumas_son_sha256sum_con_saltos_de_linea_lf(tmp_path: Path) -> None:
    (tmp_path / "Silice-1.0.0.exe").write_bytes(b"instalador")
    (tmp_path / "manifiesto.json").write_bytes(b"{}")
    sumas = c.escribir_sumas(tmp_path, "basico", ["Silice-1.0.0.exe", "manifiesto.json"])
    crudo = sumas.read_bytes()
    assert sumas.name == "SHA256SUMS-basico" and b"\r" not in crudo
    assert crudo.decode().splitlines() == [
        f"{hashlib.sha256(b'instalador').hexdigest()}  Silice-1.0.0.exe",
        f"{hashlib.sha256(b'{}').hexdigest()}  manifiesto.json",
    ]


def test_el_manifiesto_json_cubre_codigo_y_python(tmp_path: Path) -> None:
    (tmp_path / "codigo" / "ui").mkdir(parents=True)
    (tmp_path / "python").mkdir()
    (tmp_path / "codigo" / "ui" / "app.py").write_text("x", encoding="utf-8")
    (tmp_path / "python" / "python.exe").write_bytes(b"MZ")
    (tmp_path / "python" / "otro.dll").write_bytes(b"dll")
    destino = c.escribir_manifiesto_json(tmp_path, "1.0.0")
    rutas = [a["ruta"] for a in json.loads(destino.read_text(encoding="utf-8"))["archivos"]]
    assert rutas == ["codigo/ui/app.py", "python/python.exe"]


def _sin_efectos(monkeypatch, pasos: list[str], tmp_path: Path) -> None:
    """Sustituye los pasos que tocan el disco real o a Inno Setup; anota cuáles se llaman."""
    for nombre in (
        "copiar_codigo",
        "compilar",
        "licencias",
        "escribir_manifiesto_json",
        "descargar_modelo",
        "escribir_pth",
    ):
        monkeypatch.setattr(c, nombre, lambda *a, _n=nombre, **k: pasos.append(_n))
    monkeypatch.setattr(c, "asegurar_bom", lambda o, d: pasos.append("bom") or d)
    monkeypatch.setattr(c, "buscar_iscc", lambda *a, **k: Path("ISCC.exe"))
    monkeypatch.setattr(c, "escribir_sumas", lambda *a, **k: pasos.append("sumas") or tmp_path)


def test_construir_encadena_los_pasos_en_el_orden_del_spec(tmp_path: Path, monkeypatch) -> None:
    pasos: list[str] = []
    _sin_efectos(monkeypatch, pasos, tmp_path)
    ejecutar = Grabador()
    rutas = c.Rutas(tmp_path)
    rutas.salida.mkdir(parents=True)
    c.construir("completo", version="1.0.0", rutas=rutas, ejecutar=ejecutar)
    verbos = [" ".join(o[:3]) for o in ejecutar.ordenes]
    assert (
        verbos.index("uv python install")
        < verbos.index("uv export --frozen")
        < verbos.index("uv pip install")
    )
    assert any(o[0] == "ISCC.exe" for o in ejecutar.ordenes)
    assert pasos == [
        "escribir_pth",
        "descargar_modelo",
        "copiar_codigo",
        "compilar",
        "licencias",
        "escribir_manifiesto_json",
        "bom",
        "sumas",
    ]


def test_el_basico_no_trae_la_capa_de_similitud(tmp_path: Path, monkeypatch) -> None:
    pasos: list[str] = []
    _sin_efectos(monkeypatch, pasos, tmp_path)
    ejecutar = Grabador()
    rutas = c.Rutas(tmp_path)
    rutas.salida.mkdir(parents=True)
    c.construir("basico", version="1.0.0", rutas=rutas, ejecutar=ejecutar)
    assert "escribir_pth" not in pasos and "descargar_modelo" not in pasos
    assert not any("--target" in orden for orden in ejecutar.ordenes)
    assert not any(orden[0] == "ISCC.exe" and "/DCompleto" in orden for orden in ejecutar.ordenes)
    assert any(orden[0] == "ISCC.exe" for orden in ejecutar.ordenes)
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_tamanos.py tests/unit/test_licencias.py
tests/unit/test_construir.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'tamanos' from 'instalador'` (y `construir`).
```bash
git add tests/unit/test_tamanos.py tests/unit/test_licencias.py tests/unit/test_construir.py
git commit -m "test(instalador): construir, licencias y tamanos del instalador (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`instalador/tamanos.py`:
```python
"""Tamaño de los instaladores contra RNF-19 (spec S5 §4.3 y §11.2). 1 MB = 1 000 000 de bytes
(RP10-6): es la lectura con menos margen."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

MB = 1_000_000
LIMITES = {"basico": 150 * MB, "completo": 650 * MB}


def evaluar(perfil: str, bytes_: int) -> tuple[bool, str]:
    if perfil not in LIMITES:
        raise ValueError(f"perfil desconocido: {perfil!r}; válidos: {', '.join(LIMITES)}")
    limite = LIMITES[perfil]
    ok = 0 < bytes_ <= limite
    return ok, f"{perfil}: {bytes_ / MB:.1f} MB de {limite / MB:.0f} MB " + (
        "(cumple)" if ok else "(NO cumple)"
    )


def _nombre(version: str, perfil: str) -> str:
    return f"Silice-{version}{'-completo' if perfil == 'completo' else ''}.exe"


def _commit() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    resultado = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return resultado.stdout.strip() or "desconocido"


def medir(carpeta: Path, version: str, perfil: str) -> dict:
    exe = carpeta / _nombre(version, perfil)
    if not exe.is_file():
        raise FileNotFoundError(f"no existe {exe.name} en {carpeta}")
    bytes_ = exe.stat().st_size
    ok, mensaje = evaluar(perfil, bytes_)
    return {
        "perfil": perfil,
        "version": version,
        "archivo": exe.name,
        "bytes": bytes_,
        "limite": LIMITES[perfil],
        "ok": ok,
        "mensaje": mensaje,
        "commit": _commit(),
    }


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--perfil", required=True, choices=list(LIMITES))
    analizador.add_argument("--carpeta", required=True, type=Path)
    analizador.add_argument("--version", required=True)
    analizador.add_argument("--salida", type=Path)
    argumentos = analizador.parse_args(argv)
    datos = medir(argumentos.carpeta, argumentos.version, argumentos.perfil)
    if argumentos.salida:
        argumentos.salida.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    print(datos["mensaje"])
    return 0 if datos["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

`instalador/licencias.py` (se ejecuta con el Python **construido**; solo biblioteca estándar):
```python
"""Reúne las licencias de Python y de cada paquete instalado en `LICENCIAS\\` (spec S5 §7.1 paso 5).

    python instalador/licencias.py --salida build/app/LICENCIAS [--solo-ruta CARPETA]

Sale con 1 si un paquete no declara licencia y no trae ningún texto de licencia, o si falta la de
Python: esos casos se resuelven a mano con un ruling, no se omiten.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from importlib import metadata
from pathlib import Path

PATRON = re.compile(r"(?i)^(licen[cs]e|copying|notice|authors)([-_. ].*)?$")


def _declarada(meta) -> str:
    expresion = meta.get("License-Expression") or meta.get("License") or ""
    if not expresion or expresion.upper() == "UNKNOWN":
        clases = [
            c.split("::")[-1].strip() for c in meta.get_all("Classifier", []) if "License ::" in c
        ]
        expresion = "; ".join(clases)
    return " ".join(expresion.split("\n")[0].split())[:90]


def _textos(dist) -> list[Path]:
    halladas = []
    for archivo in dist.files or []:
        if PATRON.match(archivo.name) and (
            "licenses" in archivo.parts
            or len(archivo.parts) <= 2
            or archivo.parts[0].endswith(".dist-info")
        ):
            ruta = Path(str(dist.locate_file(archivo)))
            if ruta.is_file():
                halladas.append(ruta)
    return halladas


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--salida", required=True, type=Path)
    analizador.add_argument("--solo-ruta", action="append", type=Path, help="buscar solo aquí")
    analizador.add_argument(
        "--python-licencia", type=Path, default=Path(sys.base_prefix) / "LICENSE.txt"
    )
    argumentos = analizador.parse_args(argv)
    problemas: list[str] = []
    argumentos.salida.mkdir(parents=True, exist_ok=True)
    if argumentos.python_licencia.is_file():
        (argumentos.salida / "Python").mkdir(exist_ok=True)
        shutil.copyfile(argumentos.python_licencia, argumentos.salida / "Python" / "LICENSE.txt")
    else:
        problemas.append(f"falta la licencia de Python en {argumentos.python_licencia}")
    ruta = [str(p) for p in argumentos.solo_ruta] if argumentos.solo_ruta else None
    filas = []
    for dist in sorted(metadata.distributions(path=ruta), key=lambda d: d.metadata["Name"].lower()):
        nombre, version = dist.metadata["Name"], dist.version
        declarada, textos = _declarada(dist.metadata), _textos(dist)
        if not declarada and not textos:
            problemas.append(f"{nombre} {version}: sin licencia declarada ni texto de licencia")
        carpeta = argumentos.salida / f"{nombre}-{version}"
        for numero, texto in enumerate(textos):
            carpeta.mkdir(exist_ok=True)
            destino = carpeta / texto.name
            shutil.copyfile(
                texto, destino if not destino.exists() else carpeta / f"{numero}-{texto.name}"
            )
        filas.append(f"| {nombre} | {version} | {declarada or 'ver texto'} |")
    (argumentos.salida / "INDICE.md").write_text(
        "# Licencias de terceros\n\n| Paquete | Versión | Licencia |\n|---|---|---|\n"
        + "\n".join(filas)
        + "\n\nPython: carpeta `Python\\`. Sílice: `LICENSE` (propietaria).\n",
        encoding="utf-8",
    )
    for problema in problemas:
        print(problema, file=sys.stderr)
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`instalador/construir.py`:
```python
"""Construye el instalador de Sílice (spec S5 §7.1; RF-97, RNF-20). Solo en Windows.

    uv run python instalador/construir.py --perfil basico|completo
    uv run python instalador/construir.py --perfil basico --solo-iss --version 1.0.1
    uv run python instalador/construir.py --perfil basico --solo-sumas \\
        --extra pip-audit-basico.json

Parte solo de `uv.lock` (`--frozen`): instalar no ejecuta un resolvedor. El resultado queda en
`build/salida/`: `Silice-<versión>[-completo].exe`, `manifiesto.json` y `SHA256SUMS-<perfil>`.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from instalador import manifiesto as mf  # noqa: E402
from instalador.medir_capas import REQUISITO as _REQUISITO  # noqa: E402
from instalador.medir_capas import normalizar as _normal  # noqa: E402
from instalador.medir_capas import paquetes_de  # noqa: E402,F401  (lo usan las pruebas)
from operacion import firma_sumas, programa  # noqa: E402
from operacion.version import a_semver  # noqa: E402
from operacion.version import version as version_del_proyecto  # noqa: E402

Ejecutar = Callable[..., None]


@dataclass(frozen=True)
class Rutas:
    raiz: Path = RAIZ

    @property
    def build(self) -> Path:
        return self.raiz / "build"

    @property
    def py(self) -> Path:
        return self.build / "py"

    @property
    def app(self) -> Path:
        return self.build / "app"

    @property
    def salida(self) -> Path:
        return self.build / "salida"


def _ejecutar(
    orden: Sequence[str], entorno: Mapping[str, str] | None = None, cwd: Path | None = None
) -> None:
    subprocess.run([str(p) for p in orden], env=entorno, cwd=cwd, check=True)


def solo_los_nuevos(basica: str, completa: str) -> str:
    """Las líneas de `completa` cuyo paquete la capa básica no trae (diferencia de conjuntos)."""
    ya = set(paquetes_de(basica))
    nuevas = []
    for linea in completa.splitlines():
        coincidencia = _REQUISITO.match(linea.strip())
        if coincidencia and _normal(coincidencia.group(1)) not in ya:
            nuevas.append(linea.strip())
            ya.add(_normal(coincidencia.group(1)))
    return "\n".join(nuevas) + ("\n" if nuevas else "")


def extras_de(m: mf.Manifiesto, similitud: bool) -> list[str]:
    extras = [*m.extras_basica, *(["ifc"] if m.ifc else [])]
    return [*extras, *m.extras_similitud] if similitud else extras


def exportar(extras: Sequence[str], salida: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    pares = [parte for extra in extras for parte in ("--extra", extra)]
    ejecutar(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-hashes",
            *pares,
            "--output-file",
            str(salida),
        ]
    )


def instalar_python(version: str, rutas: Rutas, ejecutar: Ejecutar = _ejecutar) -> Path:
    ejecutar(["uv", "python", "install", version, "--install-dir", str(rutas.py)])
    candidatos = sorted(rutas.py.glob(f"cpython-{version}-*/python.exe"))
    if not candidatos:
        raise FileNotFoundError(f"uv no dejó un python.exe de {version} en {rutas.py}")
    destino = rutas.app / "python"
    shutil.copytree(candidatos[0].parent, destino)
    return destino / "python.exe"


def instalar_capa(python: Path, requisitos: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    ejecutar(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--break-system-packages",
            "--compile-bytecode",
            "--no-deps",
            "-r",
            str(requisitos),
        ]
    )


def instalar_similitud(
    python: Path, requisitos: Path, destino: Path, ejecutar: Ejecutar = _ejecutar
) -> None:
    ejecutar(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--target",
            str(destino),
            "--no-deps",
            "--compile-bytecode",
            "-r",
            str(requisitos),
        ]
    )


def escribir_pth(app: Path) -> None:
    """`site` une cada línea de un .pth a su carpeta (`python\\Lib\\site-packages`): tres `..`
    llegan a `{app}`. El Inno lo instala solo con el componente de similitud."""
    (app / "silice_similitud.pth").write_text(
        "..\\..\\..\\modulos\\similitud\\paquetes\n", encoding="utf-8"
    )


def descargar_modelo(python: Path, app: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    from ml.normalization import MODELO_POR_DEFECTO

    similitud = app / "modulos" / "similitud"
    entorno = {
        **os.environ,
        "HF_HOME": str(similitud / "hf"),
        "PYTHONPATH": str(similitud / "paquetes"),
    }
    entorno.pop("HF_HUB_OFFLINE", None)
    ejecutar(
        [
            str(python),
            "-c",
            "from sentence_transformers import SentenceTransformer as S; "
            f"S({MODELO_POR_DEFECTO!r})",
        ],
        entorno,
    )


def licencias(python: Path, app: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    paquetes = app / "modulos" / "similitud" / "paquetes"
    entorno = {**os.environ, **({"PYTHONPATH": str(paquetes)} if paquetes.is_dir() else {})}
    ejecutar(
        [
            str(python),
            str(RAIZ / "instalador" / "licencias.py"),
            "--salida",
            str(app / "LICENCIAS"),
        ],
        entorno,
    )
    shutil.copyfile(RAIZ / "LICENSE", app / "LICENCIAS" / "Silice-LICENSE.txt")


def copiar_codigo(m: mf.Manifiesto, destino: Path) -> None:
    mf.armar_arbol(RAIZ, destino, m)


def compilar(python: Path, codigo: Path, ejecutar: Ejecutar = _ejecutar) -> None:
    ejecutar([str(python), "-m", "compileall", "-q", "-j", "0", str(codigo)])


def escribir_manifiesto_json(app: Path, version: str) -> Path:
    relativas = [p.relative_to(app) for p in (app / "codigo").rglob("*") if p.is_file()]
    return programa.escribir(app, [*relativas, Path("python/python.exe")], version)


def asegurar_bom(origen: Path, destino: Path) -> Path:
    """Inno Setup lee un .iss UTF-8 solo si trae BOM; sin él, rompe «Sílice»."""
    datos = origen.read_bytes()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos if datos.startswith(b"\xef\xbb\xbf") else b"\xef\xbb\xbf" + datos)
    return destino


def buscar_iscc(
    entorno: Mapping[str, str] | None = None, existe: Callable[[Path], bool] = Path.is_file
) -> Path:
    env = os.environ if entorno is None else entorno
    candidatas = [Path(p) / "ISCC.exe" for p in env.get("PATH", "").split(os.pathsep) if p]
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        if env.get(variable):
            base = Path(env[variable]) / ("Programs" if variable == "LOCALAPPDATA" else "")
            candidatas += [base / "Inno Setup 6" / "ISCC.exe", base / "Inno Setup 7" / "ISCC.exe"]
    for candidata in candidatas:
        if existe(candidata):
            return candidata
    raise FileNotFoundError(
        "No se encontró ISCC.exe de Inno Setup. Instálelo con "
        "`winget install --id JRSoftware.InnoSetup -e` y vuelva a intentar."
    )


def nombre_instalador(version: str, perfil: str) -> str:
    return f"Silice-{version}{'-completo' if perfil == 'completo' else ''}.exe"


def comando_iscc(iscc: Path, iss: Path, version: str, perfil: str, rutas: Rutas) -> list[str]:
    # El perfil completo se marca con un símbolo sin valor (`#ifdef Completo`): ISPP no tiene que
    # adivinar si «completo» es una cadena.
    return [
        str(iscc),
        f"/DVersion={version}",
        *(["/DCompleto"] if perfil == "completo" else []),
        f"/DOrg={rutas.app}",
        f"/DSalida={rutas.salida}",
        f"/DRaiz={rutas.raiz}",
        str(iss),
    ]


def escribir_sumas(carpeta: Path, perfil: str, nombres: Sequence[str]) -> Path:
    entradas = {n: hashlib.sha256((carpeta / n).read_bytes()).hexdigest() for n in nombres}
    destino = carpeta / f"SHA256SUMS-{perfil}"
    destino.write_bytes(firma_sumas.formatear_sumas(entradas))
    return destino


def construir(
    perfil: str,
    *,
    version: str | None = None,
    solo_iss: bool = False,
    rutas: Rutas | None = None,
    ejecutar: Ejecutar = _ejecutar,
) -> list[Path]:
    rutas = rutas or Rutas()
    m = mf.cargar()
    semver = version or a_semver(version_del_proyecto())
    rutas.salida.mkdir(parents=True, exist_ok=True)
    if not solo_iss:
        shutil.rmtree(rutas.app, ignore_errors=True)
        python = instalar_python(m.python, rutas, ejecutar)
        basica = rutas.build / "req-basica.txt"
        exportar(extras_de(m, similitud=False), basica, ejecutar)
        instalar_capa(python, basica, ejecutar)
        if perfil == "completo":
            completa, nuevos = rutas.build / "req-completa.txt", rutas.build / "req-similitud.txt"
            exportar(extras_de(m, similitud=True), completa, ejecutar)
            nuevos.write_text(
                solo_los_nuevos(basica.read_text("utf-8"), completa.read_text("utf-8")), "utf-8"
            )
            instalar_similitud(
                python, nuevos, rutas.app / "modulos" / "similitud" / "paquetes", ejecutar
            )
            escribir_pth(rutas.app)
            descargar_modelo(python, rutas.app, ejecutar)
        copiar_codigo(m, rutas.app / "codigo")
        compilar(python, rutas.app / "codigo", ejecutar)
        licencias(python, rutas.app, ejecutar)
        escribir_manifiesto_json(rutas.app, semver)
    iss = asegurar_bom(RAIZ / "instalador" / "silice.iss", rutas.build / "silice.iss")
    ejecutar(comando_iscc(buscar_iscc(), iss, semver, perfil, rutas), None, RAIZ)
    if (rutas.app / "manifiesto.json").is_file():
        shutil.copyfile(rutas.app / "manifiesto.json", rutas.salida / "manifiesto.json")
    sumas = escribir_sumas(
        rutas.salida, perfil, [nombre_instalador(semver, perfil), "manifiesto.json"]
    )
    return [rutas.salida / nombre_instalador(semver, perfil), sumas]


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--perfil", required=True, choices=["basico", "completo"])
    analizador.add_argument("--version", help="SemVer; por defecto la de pyproject.toml")
    analizador.add_argument(
        "--solo-iss", action="store_true", help="recompila sin reconstruir el árbol"
    )
    analizador.add_argument(
        "--solo-sumas", action="store_true", help="regenera SHA256SUMS-<perfil>"
    )
    analizador.add_argument(
        "--extra", action="append", default=[], help="archivo más para las sumas"
    )
    argumentos = analizador.parse_args(argv)
    rutas = Rutas()
    semver = argumentos.version or a_semver(version_del_proyecto())
    if argumentos.solo_sumas:
        nombres = [
            nombre_instalador(semver, argumentos.perfil),
            "manifiesto.json",
            *argumentos.extra,
        ]
        print(escribir_sumas(rutas.salida, argumentos.perfil, nombres))
        return 0
    for salida in construir(
        argumentos.perfil, version=argumentos.version, solo_iss=argumentos.solo_iss
    ):
        print(salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
Notas: (1) `firma_sumas.formatear_sumas(entradas: Mapping[str, str]) -> bytes` es de T3
(líneas `<hex>  <nombre>\n`, ordenadas por nombre, solo LF). (2) El orden de `pasos` que fija
`test_construir_encadena…` es el de este `construir`. (3) Las líneas largas que ruff marque
(`E501`) se parten; no se agrega excepción.

- [ ] **Paso 4: Correrlas y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_tamanos.py tests/unit/test_licencias.py
tests/unit/test_construir.py tests/unit/test_manifiesto.py -v -W error`
y `uv run ruff check instalador tests/unit/test_construir.py tests/unit/test_licencias.py
tests/unit/test_tamanos.py`.
`.gitignore`, al final:
```gitignore
# Construcción del instalador, publicación y salidas de la prueba de humo (S5-3, S5-4)
build/
publicacion/
humo-salida/
```

- [ ] **Paso 5: Commit**
```bash
git add instalador/construir.py instalador/licencias.py instalador/tamanos.py .gitignore
git commit -m "feat(instalador): construir.py con Python autonomo y capas desde uv.lock" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Tarea 15: `instalador/silice.iss`, su prueba estática y la compilación local **[HUMANO]**

**Rama:** `inc/100-s5-3-instalador`   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `instalador/silice.iss`
- Prueba: `tests/unit/test_iss.py`

**Interfaces:**
- Consume: `construir.asegurar_bom`, `construir.comando_iscc` (T14); `operacion.version` (T4).
- Produce: `Silice-<versión>[-completo].exe` con `AppId` fijo, componentes `programa`,
  `demostracion`
  y (solo en el completo) `similitud`; accesos «Sílice», «Detener Sílice» y «Sílice: red local
  (administrador)»; migración con aviso si falla; desinstalador que conserva los datos.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_iss.py`:
```python
"""Comprobaciones estáticas de silice.iss (spec S5 §7.3). La compilación real la hace la CI."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ISS = RAIZ / "instalador" / "silice.iss"
GUID = "D3E5A9C1-6B24-4F0A-8E7D-2C41B96A5F30"  # fijo para siempre: lo usa la actualización
PARAMETROS = "-E -s -B -X utf8 -m operacion"


def _texto() -> str:
    """El .iss con sus atajos `#define` sustituidos, como lo ve Inno Setup."""
    texto = ISS.read_text(encoding="utf-8")
    atajos = dict(re.findall(r'^#define (\w+) "(.*)"$', texto, re.M))
    for nombre, valor in atajos.items():
        texto = texto.replace("{#" + nombre + "}", valor.replace('""', '"'))
    return texto


def _secciones() -> dict[str, list[str]]:
    secciones: dict[str, list[str]] = {}
    actual = ""
    for linea in _texto().splitlines():
        if re.match(r"^\[[A-Za-z]+\]$", linea.strip()):
            actual = linea.strip()[1:-1]
            secciones[actual] = []
        elif actual and linea.strip() and not linea.strip().startswith(";"):
            secciones[actual].append(linea.strip())
    return secciones


def test_ninguna_linea_pasa_de_100_columnas() -> None:
    largas = [
        n
        for n, linea in enumerate(ISS.read_text(encoding="utf-8").splitlines(), 1)
        if len(linea) > 100
    ]
    assert largas == []


def test_el_iss_instala_por_usuario_y_con_el_appid_fijo() -> None:
    texto = _texto()
    assert "PrivilegesRequired=lowest" in texto
    assert f"AppId={{{{{GUID}}}" in texto  # {{ escapa la llave: el AppId real es {GUID}
    assert f"{{{GUID}}}_is1" in texto  # clave de desinstalación de donde se lee la versión previa
    assert "DefaultDirName={autopf}\\Silice" in texto
    assert "MinVersion=10.0.19045" in texto and "ArchitecturesAllowed=x64compatible" in texto
    assert "Compression=lzma2/ultra64" in texto and "SolidCompression=yes" in texto
    assert "LicenseFile=" in texto and "LICENSE" in texto


def test_el_iss_no_toca_la_carpeta_de_datos_ni_descarga_nada() -> None:
    secciones = _secciones()
    for nombre in ("Files", "InstallDelete", "UninstallDelete", "Dirs"):
        for linea in secciones.get(nombre, []):
            assert "localappdata" not in linea.lower() and "\\datos" not in linea.lower(), linea
            assert "respaldos" not in linea.lower(), linea
    texto = _texto()
    assert "DownloadTemporaryFile" not in texto and "CreateDownloadPage" not in texto
    assert not re.search(r"https?://", "\n".join(sum(secciones.values(), [])))


def test_install_delete_borra_el_programa_pero_no_los_datos() -> None:
    borradas = " ".join(_secciones()["InstallDelete"])
    for carpeta in ("{app}\\python", "{app}\\modulos", "{app}\\codigo", "{app}\\LICENCIAS"):
        assert carpeta in borradas


def test_los_accesos_directos_usan_las_banderas_de_aislamiento() -> None:
    iconos = _secciones()["Icons"]
    nombres = " ".join(iconos)
    for nombre in ("Sílice", "Detener Sílice", "Sílice: red local (administrador)"):
        assert f'Name: "{{autoprograms}}\\{nombre}"' in nombres
    for linea in iconos:
        assert "Filename: {app}\\python\\python.exe" in linea
        assert "WorkingDir: {app}\\codigo" in linea
        assert f'Parameters: "{PARAMETROS} ' in linea


def test_la_migracion_corre_despues_de_copiar_y_antes_de_ofrecer_abrir() -> None:
    texto = _texto()
    assert "ssPostInstall" in texto and f"{PARAMETROS} migrar" in texto
    ejecuciones = _secciones()["Run"]
    assert not any("migrar" in linea for linea in ejecuciones)  # la migración se hace en [Code]
    assert "postinstall" in ejecuciones[-1] and "skipifsilent" in ejecuciones[-1]
    assert any(
        "demostracion" in linea and "Components: demostracion" in linea for linea in ejecuciones
    )


def test_se_detiene_silice_antes_de_copiar_y_al_desinstalar() -> None:
    texto = _texto()
    assert "function PrepareToInstall" in texto and f"{PARAMETROS} parar" in texto
    desinstalar = " ".join(_secciones()["UninstallRun"])
    assert f"{PARAMETROS} parar" in desinstalar and "RunOnceId" in desinstalar


def test_bajar_de_version_pide_confirmacion_y_en_silencio_se_niega() -> None:
    texto = _texto()
    assert "function ClaveDeVersion" in texto and "function InitializeSetup" in texto
    assert "IDNO" in texto  # la respuesta por defecto de SuppressibleMsgBox es «no»


def test_el_perfil_completo_agrega_el_componente_de_similitud() -> None:
    texto = _texto()
    assert "#ifdef Completo" in texto and "similitud" in texto
    componentes = " ".join(_secciones()["Components"])
    assert "programa" in componentes and "demostracion" in componentes
    assert "OutputBaseFilename=Silice-{#Version}{#Sufijo}" in texto


def test_el_idioma_es_espanol_y_el_archivo_es_utf8() -> None:
    assert 'MessagesFile: "compiler:Languages\\Spanish.isl"' in _texto()
    assert "Sílice" in _texto()  # el nombre visible lleva tilde: por eso construir.py agrega el BOM


def test_el_mensaje_de_desinstalacion_dice_donde_quedan_los_datos() -> None:
    texto = _texto()
    assert "usDone" in texto and "Sus datos quedan en" in texto and "{localappdata}" in texto


@pytest.mark.parametrize("variable", ["Version", "Org", "Raiz"])
def test_faltar_una_definicion_obligatoria_es_un_error_de_compilacion(variable: str) -> None:
    assert f"#ifndef {variable}" in _texto() and "#error" in _texto()
```

- [ ] **Paso 2: Correrla y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_iss.py -v -W error`
Esperado: FAIL con `FileNotFoundError: ... instalador\silice.iss`.
```bash
git add tests/unit/test_iss.py
git commit -m "test(instalador): comprobaciones estaticas de silice.iss (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`instalador/silice.iss` (UTF-8; `construir.py` lo compila desde una copia con BOM):
```ini
; Sílice: instalador de Windows (spec S5 §7.3; RF-97). No se compila a mano: lo hace
; construir.py con ISCC.exe /DVersion=<SemVer> [/DCompleto] /DOrg=<build\app>
;   /DRaiz=<repositorio> /DSalida=<build\salida> silice.iss
#ifndef Version
  #error Falta /DVersion=<versión SemVer del pyproject>
#endif
#ifndef Org
  #error Falta /DOrg=<carpeta build\app>
#endif
#ifndef Raiz
  #error Falta /DRaiz=<carpeta del repositorio>
#endif
#ifndef Salida
  #define Salida Raiz + "\build\salida"
#endif
#ifdef Completo
  #define Sufijo "-completo"
#else
  #define Sufijo ""
#endif
; Atajos: las secciones de Inno no admiten líneas partidas y deben caber en 100 columnas.
#define Op "-E -s -B -X utf8 -m operacion"
#define OpA "-E -s -B -X utf8 -m operacion arrancar"
#define OpP "-E -s -B -X utf8 -m operacion parar"
#define OpR "-E -s -B -X utf8 -m operacion red-local activar"
#define OpD "-E -s -B -X utf8 -m operacion demostracion"
#define Ej "Filename: {app}\python\python.exe; WorkingDir: {app}\codigo;"
#define Rec "recursesubdirs createallsubdirs ignoreversion"
#define Mod "{app}\modulos\similitud"
#define Sp "{app}\python\Lib\site-packages"

[Setup]
; El AppId no cambia jamás: la actualización reconoce así la instalación anterior.
AppId={{D3E5A9C1-6B24-4F0A-8E7D-2C41B96A5F30}
AppName=Sílice
AppVersion={#Version}
AppPublisher=Eugenio Rijo
DefaultDirName={autopf}\Silice
DefaultGroupName=Sílice
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
MinVersion=10.0.19045
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
LicenseFile={#Raiz}\LICENSE
OutputDir={#Salida}
OutputBaseFilename=Silice-{#Version}{#Sufijo}
UninstallDisplayIcon={app}\python\python.exe
SetupLogging=yes
UsePreviousAppDir=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Types]
Name: "est"; Description: "Instalación estándar"
Name: "per"; Description: "Instalación personalizada"; Flags: iscustom

[Components]
Name: "programa"; Description: "Sílice"; Types: est per; Flags: fixed
Name: "demostracion"; Description: "Caso de demostración (datos ficticios)"; Types: est per
#ifdef Completo
Name: "similitud"; Description: "Similitud de partidas (módulo opcional, ~1 GB)"; Types: est per
#endif

[Tasks]
Name: "escritorio"; Description: "Acceso directo en el escritorio"; Flags: unchecked

[Files]
Source: "{#Org}\python\*"; DestDir: "{app}\python"; Components: programa; Flags: {#Rec}
Source: "{#Org}\codigo\*"; DestDir: "{app}\codigo"; Components: programa; Flags: {#Rec}
Source: "{#Org}\LICENCIAS\*"; DestDir: "{app}\LICENCIAS"; Components: programa; Flags: {#Rec}
Source: "{#Org}\manifiesto.json"; DestDir: "{app}"; Components: programa; Flags: ignoreversion
#ifdef Completo
Source: "{#Org}\modulos\similitud\*"; DestDir: "{#Mod}"; Components: similitud; Flags: {#Rec}
Source: "{#Org}\silice_similitud.pth"; DestDir: "{#Sp}"; Components: similitud; Flags: ignoreversion
#endif

[InstallDelete]
; Al actualizar no deben quedar paquetes de la versión anterior. Los datos viven fuera de {app}.
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\modulos"
Type: filesandordirs; Name: "{app}\codigo"
Type: filesandordirs; Name: "{app}\LICENCIAS"

[Icons]
Name: "{autoprograms}\Sílice"; {#Ej} Parameters: "{#OpA}"; Flags: runminimized
Name: "{autoprograms}\Detener Sílice"; {#Ej} Parameters: "{#OpP}"; Flags: runminimized
Name: "{autoprograms}\Sílice: red local (administrador)"; {#Ej} Parameters: "{#OpR}"
Name: "{autodesktop}\Sílice"; {#Ej} Parameters: "{#OpA}"; Flags: runminimized; Tasks: escritorio

[Run]
{#Ej} Parameters: "{#OpD}"; Components: demostracion; Flags: runhidden
{#Ej} Parameters: "{#OpA}"; Description: "Abrir Sílice"; Flags: postinstall nowait skipifsilent

[UninstallRun]
{#Ej} Parameters: "{#OpP}"; Flags: runhidden; RunOnceId: "DetenerSilice"

[UninstallDelete]
; Solo el programa; nunca la carpeta de datos.
Type: filesandordirs; Name: "{app}\codigo"
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\modulos"

[Code]
const
  ClaveDesinstalador =
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
    '{D3E5A9C1-6B24-4F0A-8E7D-2C41B96A5F30}_is1';

function TomarNumero(var S: String): Integer;
var
  I: Integer;
  N: String;
begin
  I := 1;
  while (I <= Length(S)) and (S[I] >= '0') and (S[I] <= '9') do
    I := I + 1;
  N := Copy(S, 1, I - 1);
  S := Copy(S, I, Length(S));
  if (Length(S) > 0) and (S[1] = '.') then
    S := Copy(S, 2, Length(S));
  Result := StrToIntDef(N, 0);
end;

{ X.Y.Z[-rc.N] como un número comparable; la versión final vale más que cualquier candidata. }
function ClaveDeVersion(Texto: String): Int64;
var
  X, Y, Z, N, I: Integer;
begin
  X := TomarNumero(Texto);
  Y := TomarNumero(Texto);
  Z := TomarNumero(Texto);
  N := 999;
  if (Length(Texto) > 0) and (Texto[1] = '-') then
  begin
    I := Pos('.', Texto);
    if I > 0 then
      N := StrToIntDef(Copy(Texto, I + 1, Length(Texto)), 0)
    else
      N := 0;
  end;
  Result := (((Int64(X) * 1000 + Y) * 1000 + Z) * 1000) + N;
end;

function VersionInstalada(): String;
var
  V: String;
begin
  Result := '';
  if RegQueryStringValue(HKCU, ClaveDesinstalador, 'DisplayVersion', V) then
    Result := V
  else if RegQueryStringValue(HKLM, ClaveDesinstalador, 'DisplayVersion', V) then
    Result := V;
end;

function InitializeSetup(): Boolean;
var
  Previa: String;
begin
  Result := True;
  Previa := VersionInstalada();
  if (Previa <> '') and (ClaveDeVersion(Previa) > ClaveDeVersion('{#Version}')) then
    Result := SuppressibleMsgBox(
      'Ya hay instalada una versión más nueva de Sílice (' + Previa + '). Instalar la ' +
      '{#Version} es bajar de versión y puede dejar sus datos sin abrir. ¿Continuar?',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Codigo: Integer;
  Python: String;
begin
  Result := '';
  Python := ExpandConstant('{app}\python\python.exe');
  if FileExists(Python) then
    Exec(Python, '{#Op} parar', ExpandConstant('{app}\codigo'),
      SW_HIDE, ewWaitUntilTerminated, Codigo);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Codigo: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if (not Exec(ExpandConstant('{app}\python\python.exe'), '{#Op} migrar',
        ExpandConstant('{app}\codigo'), SW_HIDE, ewWaitUntilTerminated, Codigo))
       or (Codigo <> 0) then
      SuppressibleMsgBox(
        'Sílice se instaló, pero no pudo actualizar sus bases de datos. Sus datos no se ' +
        'tocaron y hay un respaldo previo. Abra Sílice: le dirá qué hacer (manual de ' +
        'instalación, «base no adoptable» o «versión más nueva»).',
        mbError, MB_OK, IDOK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usDone then
    SuppressibleMsgBox(
      'Sus datos quedan en ' + ExpandConstant('{localappdata}') + '\Silice. ' +
      'Bórrelos a mano si ya no los necesita.', mbInformation, MB_OK, IDOK);
end;
```
(Las secciones de Inno no admiten líneas partidas: los atajos `#define` (`Op`, `Ej`, `Rec`…) las
mantienen en 100 columnas y las pruebas leen el texto ya con los atajos sustituidos.
`UninstallDelete` solo nombra carpetas del programa, nunca la de datos; la línea
`LicenseFile={#Raiz}\LICENSE` muestra la licencia propietaria (P9).)

- [ ] **Paso 4: Correrla y ver el verde; compilar de verdad [HUMANO: H5]**
Run: `uv run pytest tests/unit/test_iss.py -v -W error` y `uv run ruff check
tests/unit/test_iss.py`.

Compilación y prueba a mano en el equipo de desarrollo (criterio de GS5-3; lo hace Eugenio o el
controlador, sentado al equipo, con internet para `uv`):
```powershell
winget install --id JRSoftware.InnoSetup -e          # H5: una vez; confirma ISCC.exe
uv run python instalador/construir.py --perfil basico
Get-FileHash build\salida\Silice-*.exe -Algorithm SHA256
# Instalar en una ruta con espacios y ñ, sin administrador, y usar el acceso directo:
.\build\salida\Silice-*.exe /DIR="C:\Prueba Sílice\Programa ñ"
```
Si ISPP rechaza `/DVersion=1.0.0-rc.1` (lo trata como expresión y no como texto), pasar el valor
entre comillas (`/DVersion="1.0.0-rc.1"`) en `comando_iscc` y en su prueba; es lo único del
`.iss` que solo la primera compilación real puede confirmar.

Comprobar a mano: el asistente muestra la licencia y el español; el acceso «Sílice» abre el
navegador en `http://127.0.0.1:8501` y la consola dice «Para detener Sílice, cierre esta ventana»;
`python -m operacion verificar-programa` (con el Python de `{app}`) dice «coincide»; «Detener
Sílice» lo para; reinstalar encima conserva `%LOCALAPPDATA%\Silice`; desinstalar deja ese
directorio y borra `{app}`. Los resultados (huella, tamaño real con LZMA2, tiempos) se anotan en
`docs/bitacora/2026-10-silice-100.md` y el tamaño real completa §1.3 (S5-3.4) y decide el recorte
de `instalador/medir_capas.py` si el básico pasa de 150 MB.

- [ ] **Paso 5: Commit y PR (cierra `inc/100-s5-3-instalador` y GS5-3)**
```bash
git add instalador/silice.iss
git commit -m "feat(instalador): silice.iss por usuario, con migracion y datos conservados" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-3-instalador
gh pr create --base main --head inc/100-s5-3-instalador \
  --title "S5-3: construir.py y silice.iss" --body-file -
```

### Compuerta GS5-3

- [ ] CI verde en Linux y Windows, 0 omitidas, `-W error`.
- [ ] `uv run pytest -W error tests/unit/test_manifiesto.py tests/unit/test_programa.py
  tests/unit/test_construir.py tests/unit/test_licencias.py tests/unit/test_tamanos.py
  tests/unit/test_iss.py` en verde.
- [ ] **A mano, en el equipo de desarrollo (H5):** se compila el básico, se instala en
  `C:\Prueba Sílice\Programa ñ`, arranca, se actualiza, se desinstala y los datos quedan (Paso 4 de
  la Tarea 15); resultados en la bitácora con fecha.
- [ ] §1.3 del spec completada con las cifras de T2 y con el tamaño real del instalador; si el
  básico pasa de 150 MB, el recorte del spec §7.2 (primero `civil`, luego `anomalias`) está decidido
  en un ruling `RP10-n` en la bitácora.
- [ ] Núcleo intacto; regresión literal intacta.
- [ ] Encargos (maestro §6.4): requisitos, arquitectura, pruebas y calidad, verificador de hechos y
  seguridad (manifiesto, rutas con espacios, desinstalación).

---

## S5-4 · Integración continua (RF-97, RF-98, RNF-19)

### Tarea 16: `humo.ps1`, `navegador.py`, `proxy_testigo.py` y `verificar_bases.py`

**Rama:** `inc/100-s5-4-humo` (sale de `origin/main` con GS5-3 cruzada)
**Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `instalador/humo.ps1`, `instalador/navegador.py`, `instalador/proxy_testigo.py`,
  `instalador/verificar_bases.py`
- Prueba: `tests/unit/test_humo_piezas.py`

**Interfaces:**
- Consume: `tests.fixtures.bases_prueba` (`ficha`, `diferencias_con_ficha`, `copiar_base`; A5),
  `operacion.base_datos` (`leer_estado`, `revision_head`, `Destino`), `operacion.lanzador` y
  `operacion.ordenes_100` (órdenes `arrancar --sin-navegador`, `parar`, `migrar`, `red-local`,
  `verificar-programa`, `diagnostico-similitud`).
- Produce:
  - `instalador/humo.ps1 -Instalador <exe> -Actualizacion <exe> -Version <SemVer> [-Perfil
    basico|completo] [-Salida humo-salida]`: sale con 0 si todo cumple (RF-97 a–h, RF-98).
  - `instalador.navegador`: `externos(urls: Iterable[str]) -> list[str]`, `main(argv) -> int`.
  - `instalador.proxy_testigo`: `crear_servidor(puerto: int, registro: Path) ->
    ThreadingHTTPServer`,
    `main(argv)`.
  - `instalador.verificar_bases`: `verificar(casos: Path, pares: Sequence[Par]) -> list[str]`,
    `Par(version, base, archivo)`, `main(argv)`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_humo_piezas.py`:
```python
"""Piezas de la prueba de humo que sí se pueden probar sin Windows ni instalador (spec S5 §11.2)."""

from __future__ import annotations

import http.client
import re
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

import pytest

from instalador import navegador, proxy_testigo, verificar_bases
from operacion.base_datos import preparar_base
from tests.fixtures import bases_prueba as bp

RAIZ = Path(__file__).resolve().parents[2]
HUMO = RAIZ / "instalador" / "humo.ps1"


def test_externos_ignora_el_bucle_local_y_los_esquemas_que_no_son_red() -> None:
    urls = [
        "http://127.0.0.1:8501/",
        "ws://127.0.0.1:8501/_stcore/stream",
        "http://localhost:8501/x",
        "data:image/png;base64,AAAA",
        "blob:http://127.0.0.1:8501/abc",
        "about:srcdoc",
        "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
        "https://browser.events.data.microsoft.com/x",
        "wss://otro.ejemplo/socket",
    ]
    assert navegador.externos(urls) == [
        "browser.events.data.microsoft.com",
        "cdnjs.cloudflare.com",
        "otro.ejemplo",
    ]
    assert navegador.externos([]) == []


@pytest.fixture
def testigo(tmp_path: Path):
    registro = tmp_path / "proxy.log"
    servidor = proxy_testigo.crear_servidor(0, registro)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield servidor.server_address[1], registro
    servidor.shutdown()
    servidor.server_close()


def test_el_proxy_testigo_anota_cada_peticion_y_no_deja_pasar_ninguna(testigo) -> None:
    puerto, registro = testigo
    conexion = http.client.HTTPConnection("127.0.0.1", puerto, timeout=5)
    conexion.request("GET", "http://ejemplo.invalid/x")
    assert conexion.getresponse().status == 502
    conexion = http.client.HTTPConnection("127.0.0.1", puerto, timeout=5)
    conexion.request("CONNECT", "ejemplo.invalid:443")
    assert conexion.getresponse().status == 502
    assert registro.read_text(encoding="utf-8").splitlines() == [
        "GET http://ejemplo.invalid/x",
        "CONNECT ejemplo.invalid:443",
    ]


def test_sin_peticiones_el_registro_no_existe_o_esta_vacio(testigo) -> None:
    _, registro = testigo
    assert not registro.exists() or registro.read_text(encoding="utf-8") == ""


def _caso(tmp_path: Path, version: str, nombre: str, archivo: str) -> Path:
    destino = tmp_path / archivo
    bp.copiar_base(version, nombre, destino)
    preparar_base(destino)
    return destino


def test_una_base_migrada_cuadra_con_la_ficha_de_su_version(tmp_path: Path) -> None:
    _caso(tmp_path, "0.5.0", "demo.db", "v050_demo.db")
    pares = [verificar_bases.Par("0.5.0", "demo.db", "v050_demo.db")]
    assert verificar_bases.verificar(tmp_path, pares) == []


def test_una_base_alterada_o_sin_migrar_se_reporta(tmp_path: Path) -> None:
    ruta = _caso(tmp_path, "0.5.0", "demo.db", "v050_demo.db")
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("DELETE FROM alembic_version")
        conexion.commit()
    pares = [
        verificar_bases.Par("0.5.0", "demo.db", "v050_demo.db"),
        verificar_bases.Par("0.5.0", "of001.db", "no_esta.db"),
    ]
    problemas = verificar_bases.verificar(tmp_path, pares)
    assert any("v050_demo.db" in p and "head" in p for p in problemas)
    assert any("no_esta.db" in p and "no existe" in p for p in problemas)


def test_el_argumento_par_se_lee_version_base_archivo() -> None:
    assert verificar_bases.leer_par("0.9.0:demo.db=v090_demo.db") == verificar_bases.Par(
        "0.9.0", "demo.db", "v090_demo.db"
    )
    with pytest.raises(ValueError, match="VERSION:BASE=ARCHIVO"):
        verificar_bases.leer_par("sin-formato")


def test_humo_cubre_cada_comprobacion_del_spec() -> None:
    texto = HUMO.read_text(encoding="utf-8")
    for pieza in (
        "New-NetFirewallRule",
        "-Direction Outbound",
        "-Action Block",
        "LogBlocked",  # cortafuegos
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/CURRENTUSER",
        "/DIR=",
        "Get-NetTCPConnection -State Listen",
        "'0.0.0.0'",
        "'::'",  # escucha
        "_stcore/health",
        "navegador.py",
        "proxy_testigo.py",
        "HTTP_PROXY",
        "NO_PROXY",
        "verificar-programa",
        "verificar_bases.py",
        "red-local",
        "unins000.exe",
        "$env:SILICE_DATOS",
        "$env:SILICE_USUARIO",
        "tiempos.json",
    ):
        assert pieza in texto, pieza
    assert "Invoke-Expression" not in texto and not re.search(r"\biex\b", texto)
    assert "$ErrorActionPreference = 'Stop'" in texto
    assert "C:\\Prueba Sílice" in texto and "Programa ñ" in texto


def test_humo_no_pide_nada_a_internet_desde_el_programa() -> None:
    texto = HUMO.read_text(encoding="utf-8")
    # la única red que usa el script es 127.0.0.1 y la IP local; `uv run --with playwright` es del
    # runner, no de Sílice, y el cortafuegos bloquea solo el python.exe de {app}
    assert "$Url = 'http://127.0.0.1:8501'" in texto
    assert "https://" not in texto
```

- [ ] **Paso 2: Correrla y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_humo_piezas.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'navegador' from 'instalador'`.
```bash
git add tests/unit/test_humo_piezas.py
git commit -m "test(instalador): piezas de la prueba de humo (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`instalador/proxy_testigo.py`:
```python
"""Proxy testigo de la prueba de humo (spec S5 §11.2 paso 1): anota toda petición que le llega y
no deja pasar ninguna. Con `HTTP_PROXY` apuntando aquí, lo que Sílice pida respetando proxies queda
en el registro; se espera **cero** líneas."""

from __future__ import annotations

import argparse
import http.server
from pathlib import Path


def crear_manejador(registro: Path) -> type[http.server.BaseHTTPRequestHandler]:
    class Testigo(http.server.BaseHTTPRequestHandler):
        def _responder(self) -> None:
            with registro.open("a", encoding="utf-8") as archivo:
                archivo.write(f"{self.command} {self.path}\n")
            self.send_error(502, "proxy testigo: sin salida")

        # los nombres do_<MÉTODO> los fija http.server
        do_GET = do_POST = do_PUT = _responder  # noqa: N815
        do_DELETE = do_HEAD = do_OPTIONS = do_PATCH = _responder  # noqa: N815
        do_CONNECT = _responder  # noqa: N815

        def log_message(self, *argumentos) -> None:  # silencio: el registro es el archivo
            return

    return Testigo


def crear_servidor(puerto: int, registro: Path) -> http.server.ThreadingHTTPServer:
    return http.server.ThreadingHTTPServer(("127.0.0.1", puerto), crear_manejador(registro))


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--puerto", type=int, required=True)
    analizador.add_argument("--registro", type=Path, required=True)
    argumentos = analizador.parse_args(argv)
    crear_servidor(argumentos.puerto, argumentos.registro).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`instalador/navegador.py`:
```python
"""Navegador sin interfaz de la prueba de humo (spec S5 §11.2 paso 5; solo en la CI).

Carga páginas de Sílice con Edge sin interfaz (Playwright) y anota **toda** petición y todo
websocket: la lista de anfitriones fuera de 127.0.0.1 debe quedar vacía (telemetría de Streamlit y
three.js son del navegador y el proxy no los ve). Sale con 1 si hay alguno.

    uv run --no-project --with playwright python instalador/navegador.py \\
        --url http://127.0.0.1:8501 --salida humo-salida/peticiones.json
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

LOCALES = {"127.0.0.1", "localhost", "::1"}
ESQUEMAS_DE_RED = {"http", "https", "ws", "wss", "ftp"}


def externos(urls: Iterable[str]) -> list[str]:
    anfitriones = set()
    for url in urls:
        analizada = urlparse(url)
        if analizada.scheme in ESQUEMAS_DE_RED and analizada.hostname not in LOCALES:
            anfitriones.add(analizada.hostname or url)
    return sorted(anfitriones)


def recorrer(url: str, paginas: list[str]) -> list[str]:
    from playwright.sync_api import sync_playwright

    vistas: list[str] = []
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="msedge", headless=True)
        try:
            pagina = navegador.new_context().new_page()
            pagina.on("request", lambda peticion: vistas.append(peticion.url))
            pagina.on("websocket", lambda ws: vistas.append(ws.url))
            for ruta in paginas:
                pagina.goto(f"{url}/{ruta}", wait_until="networkidle", timeout=60_000)
                pagina.wait_for_timeout(1500)
        finally:
            navegador.close()
    return vistas


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--url", required=True)
    analizador.add_argument("--paginas", nargs="+", default=["", "visor", "similares"])
    analizador.add_argument("--salida", type=Path, required=True)
    argumentos = analizador.parse_args(argv)
    vistas = recorrer(argumentos.url.rstrip("/"), argumentos.paginas)
    fuera = externos(vistas)
    argumentos.salida.write_text(
        json.dumps({"peticiones": len(vistas), "externos": fuera, "urls": vistas}, indent=2),
        encoding="utf-8",
    )
    print(f"{len(vistas)} peticiones; anfitriones fuera del equipo: {fuera or 'ninguno'}")
    return 1 if fuera else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`instalador/verificar_bases.py`:
```python
"""Compara las bases migradas por el programa instalado con la ficha de su versión (RF-96 a,
RF-97 e; spec S5 §11.2 paso 9).

    uv run python instalador/verificar_bases.py --casos <carpeta> \\
        --par 0.5.0:demo.db=v050_demo.db --par 0.9.0:demo.db=v090_demo.db

Cada `--par` es `VERSION:BASE=ARCHIVO`: el archivo de la carpeta de casos y la base de
`tests/fixtures/bases/` de la que salió. Debe estar en `head` y dar las filas por tabla, el total
literal y la huella del informe de su ficha.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion.base_datos import Destino, leer_estado, revision_head  # noqa: E402
from tests.fixtures import bases_prueba as bp  # noqa: E402


@dataclass(frozen=True, slots=True)
class Par:
    version: str
    base: str
    archivo: str


def leer_par(texto: str) -> Par:
    try:
        version, resto = texto.split(":", 1)
        base, archivo = resto.split("=", 1)
    except ValueError:
        raise ValueError(f"«{texto}» no tiene la forma VERSION:BASE=ARCHIVO") from None
    return Par(version, base, archivo)


def verificar(casos: Path, pares: Sequence[Par]) -> list[str]:
    problemas: list[str] = []
    for par in pares:
        ruta = casos / par.archivo
        if not ruta.is_file():
            problemas.append(f"{par.archivo}: no existe en {casos}")
            continue
        estado = leer_estado(ruta)
        head = revision_head(Destino.CASO)
        if estado.revision != head:
            problemas.append(f"{par.archivo}: está en {estado.revision}, no en head ({head})")
        with closing(sqlite3.connect(ruta)) as conexion:
            integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
        if integridad != "ok":
            problemas.append(f"{par.archivo}: integrity_check dice {integridad}")
        esperado = bp.ficha(par.version)["bases"][par.base]
        problemas.extend(f"{par.archivo}: {d}" for d in bp.diferencias_con_ficha(ruta, esperado))
    return problemas


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--casos", type=Path, required=True)
    analizador.add_argument("--par", action="append", type=leer_par, required=True)
    argumentos = analizador.parse_args(argv)
    problemas = verificar(argumentos.casos, argumentos.par)
    print(json.dumps({"problemas": problemas}, ensure_ascii=False, indent=2))
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`instalador/humo.ps1` (UTF-8 con BOM; PowerShell 7):
```powershell
<#
.SYNOPSIS
  Prueba de humo del instalador de Sílice (spec S5 §11.2; RF-97, RF-98, RNF-19).
.DESCRIPTION
  Corre en el runner de Windows (administrador) con el asistente de IA apagado. Bloquea la
  salida del python.exe de {app}, instala en una ruta con espacios y acentos, arranca, mide,
  actualiza con una base de la 0.5.0 sin migrar, prueba la red local y desinstala.
  Sale con 1 si algo falla.
.PARAMETER Instalador     Silice-<versión>[-completo].exe
.PARAMETER Actualizacion  El mismo build con la versión de parche +1 (construir.py --solo-iss)
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Instalador,
    [Parameter(Mandatory)][string]$Actualizacion,
    [Parameter(Mandatory)][string]$Version,
    [ValidateSet('basico', 'completo')][string]$Perfil = 'basico',
    [string]$Salida = 'humo-salida',
    [string]$Raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Base = 'C:\Prueba Sílice'
$Programa = Join-Path $Base 'Programa ñ'
$Usuario = Join-Path $Base 'Usuario ñ'
$Datos = Join-Path $Usuario 'datos'
$Respaldos = Join-Path $Usuario 'respaldos'
$Codigo = Join-Path $Programa 'codigo'
$Python = Join-Path $Programa 'python\python.exe'
$Banderas = @('-E', '-s', '-B', '-X', 'utf8', '-m', 'operacion')
$PuertoProxy = 8899
$Url = 'http://127.0.0.1:8501'
$ReglaSalida = 'Silice humo: bloquear salida'
$Fallos = [System.Collections.Generic.List[string]]::new()
New-Item -ItemType Directory -Force -Path $Salida | Out-Null
$Salida = (Resolve-Path $Salida).Path
$env:SILICE_USUARIO = $Usuario
$env:SILICE_DATOS = $Datos
$env:SILICE_RESPALDOS = $Respaldos

function Afirmar([bool]$Condicion, [string]$Mensaje) {
    if ($Condicion) { Write-Host "ok: $Mensaje"; return }
    $Fallos.Add($Mensaje)
    Write-Host "FALLA: $Mensaje" -ForegroundColor Red
}
function Paso([string]$Texto) { Write-Host "`n== $Texto" -ForegroundColor Cyan }
function Contar($Objetos) { return @($Objetos | Where-Object { $null -ne $_ }).Count }
function Nombre([string]$Prefijo) {
    return Join-Path $Salida ($Prefijo + '-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
}

function Operacion([string[]]$Argumentos) {
    $registro = Nombre 'op'
    $proceso = Start-Process -FilePath $Python -ArgumentList ($Banderas + $Argumentos) `
        -WorkingDirectory $Codigo -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput "$registro.out" -RedirectStandardError "$registro.err"
    return $proceso.ExitCode
}

function EsperarSalud([string]$Direccion, [int]$Limite = 60) {
    $reloj = [Diagnostics.Stopwatch]::StartNew()
    while ($reloj.Elapsed.TotalSeconds -lt $Limite) {
        try {
            $r = Invoke-WebRequest -Uri "$Direccion/_stcore/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { return [math]::Round($reloj.Elapsed.TotalSeconds, 2) }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    return $null
}

function Hijos([int]$Raiz) {
    $todos = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId
    $cola = [System.Collections.Generic.Queue[int]]::new()
    $vistos = [System.Collections.Generic.List[int]]::new()
    $cola.Enqueue($Raiz)
    while ($cola.Count -gt 0) {
        $actual = $cola.Dequeue()
        $vistos.Add($actual)
        $todos | Where-Object { $_.ParentProcessId -eq $actual } |
            ForEach-Object { $cola.Enqueue([int]$_.ProcessId) }
    }
    return $vistos.ToArray()
}
function Escuchas([int]$Raiz) {
    $pids = Hijos $Raiz
    return @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $pids -contains $_.OwningProcess })
}
function Escucha($Lista, [string]$Direccion, [int]$Puerto) {
    return Contar ($Lista | Where-Object {
        $_.LocalAddress -eq $Direccion -and $_.LocalPort -eq $Puerto })
}
function EnTodas($Lista) {
    return Contar ($Lista | Where-Object { $_.LocalAddress -in @('0.0.0.0', '::') })
}

function ArbolDe([string]$Carpeta) {
    Get-ChildItem -LiteralPath $Carpeta -Recurse -File -Force | Sort-Object FullName |
        ForEach-Object { '{0}|{1}' -f $_.FullName.Substring($Carpeta.Length), $_.Length }
}

function AEntero([string]$Ip) {
    $b = [System.Net.IPAddress]::Parse($Ip).GetAddressBytes()
    return ([uint32]$b[0] -shl 24) + ([uint32]$b[1] -shl 16) +
        ([uint32]$b[2] -shl 8) + [uint32]$b[3]
}
function ADecimal([uint32]$N) {
    $p = (($N -shr 24) -band 255), (($N -shr 16) -band 255), (($N -shr 8) -band 255), ($N -band 255)
    return $p -join '.'
}
function RangosSin([string]$Ip) {
    # Todo IPv4 salvo 127.0.0.0/8 y la IP propia: conectarse a la propia IP no es salir del equipo.
    $n = AEntero $Ip
    return @('0.0.0.0-126.255.255.255', ('128.0.0.0-' + (ADecimal ($n - 1))),
        ((ADecimal ($n + 1)) + '-255.255.255.255'))
}

function IniciarSilice {
    $env:HTTP_PROXY = "http://127.0.0.1:$PuertoProxy"
    $env:HTTPS_PROXY = $env:HTTP_PROXY
    $env:NO_PROXY = '127.0.0.1,localhost'
    try {
        $registro = Nombre 'arrancar'
        return Start-Process -FilePath $Python -PassThru -WindowStyle Hidden `
            -ArgumentList ($Banderas + @('arrancar', '--sin-navegador')) `
            -WorkingDirectory $Codigo `
            -RedirectStandardOutput "$registro.out" -RedirectStandardError "$registro.err"
    } finally {
        Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:NO_PROXY -ErrorAction SilentlyContinue
    }
}

function InstalarSilencioso([string]$Exe, [string]$Registro) {
    $argumentos = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER',
        "/DIR=`"$Programa`"", "/LOG=`"$Registro`"")
    if ($Perfil -eq 'completo') {
        $argumentos += '/COMPONENTS="programa,demostracion,similitud"'
    }
    return (Start-Process -FilePath $Exe -ArgumentList $argumentos -Wait -PassThru).ExitCode
}

function DescartesDe([string]$Registro, [string[]]$Pids) {
    if (-not (Test-Path $Registro)) { return @() }
    $lineas = Get-Content $Registro
    $cabecera = $lineas | Where-Object { $_ -like '#Fields:*' } | Select-Object -Last 1
    $campos = ($cabecera -replace '^#Fields:\s*', '') -split '\s+'
    if ($campos -notcontains 'pid') { return @() }
    $filas = foreach ($linea in ($lineas | Where-Object { $_ -and $_ -notlike '#*' })) {
        $valores = $linea -split ' '
        $fila = @{}
        for ($i = 0; $i -lt [math]::Min($campos.Count, $valores.Count); $i++) {
            $fila[$campos[$i]] = $valores[$i]
        }
        [pscustomobject]$fila
    }
    return @($filas | Where-Object {
        $_.action -eq 'DROP' -and $Pids -contains $_.pid -and $_.'dst-ip' -notmatch '^(127\.|::1)'
    })
}

$Muestreo = {
    param($programa, $archivo)
    while ($true) {
        $pids = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($programa) } |
            ForEach-Object { $_.ProcessId })
        if ($pids.Count) {
            $pids | ForEach-Object { "pid $_" } | Add-Content -Path "$archivo.pids"
            Get-NetTCPConnection -ErrorAction SilentlyContinue |
                Where-Object { $pids -contains $_.OwningProcess -and $_.State -ne 'Listen' } |
                ForEach-Object {
                    $local = "$($_.LocalAddress):$($_.LocalPort)"
                    $remoto = "$($_.RemoteAddress):$($_.RemotePort)"
                    "$($_.OwningProcess) $($_.State) $local $remoto"
                } | Add-Content -Path $archivo
        }
        Start-Sleep -Seconds 1
    }
}

$servidor = $null; $proxy = $null; $trabajo = $null; $ip = $null
try {
    Paso '1. Cortafuegos de salida y proxy testigo'
    New-NetFirewallRule -DisplayName $ReglaSalida -Direction Outbound -Action Block `
        -Program $Python -Profile Any | Out-Null
    $registroFw = Join-Path $Salida 'pfirewall.log'
    Set-NetFirewallProfile -Profile Domain, Private, Public -LogBlocked True `
        -LogFileName $registroFw -LogMaxSizeKilobytes 16384
    $proxy = Start-Process -FilePath python -PassThru -WindowStyle Hidden -ArgumentList @(
        (Join-Path $Raiz 'instalador\proxy_testigo.py'), '--puerto', $PuertoProxy,
        '--registro', (Join-Path $Salida 'proxy.log'))

    Paso '2. Instalación silenciosa en una ruta con espacios y acentos'
    $codigo = InstalarSilencioso $Instalador (Join-Path $Salida 'instalacion.log')
    Afirmar ($codigo -eq 0) "el instalador terminó con 0 (fue $codigo)"
    Afirmar (Test-Path $Python) 'python.exe quedó en la ruta con espacios y ñ'
    $bases = (Test-Path (Join-Path $Datos 'instalacion.db')) -and
        (Test-Path (Join-Path $Datos 'casos\silice.db'))
    Afirmar $bases 'las dos bases nacieron en la carpeta de datos'

    Paso '3. Inventario y manifiesto'
    Afirmar ((Operacion @('verificar-programa')) -eq 0) '{app}\codigo coincide con manifiesto.json'
    $configs = @(Get-ChildItem -LiteralPath $Codigo -Recurse -Filter 'config.toml' -File)
    $unico = $configs.Count -eq 1 -and $configs[0].FullName.EndsWith('.streamlit\config.toml')
    Afirmar $unico 'hay un único .streamlit\config.toml'
    $ajustes = Join-Path $Usuario 'config'
    New-Item -ItemType Directory -Force -Path $ajustes | Out-Null
    Set-Content -Path (Join-Path $ajustes 'silice.toml') -Encoding utf8 `
        -Value "[servidor]`npuerto = 8501`n[interfaz]`nmostrar_investigacion = true`n"
    $antes = ArbolDe $Programa

    Paso '4. Arranque, salud y puertos'
    $trabajo = Start-Job -ScriptBlock $Muestreo `
        -ArgumentList $Programa, (Join-Path $Salida 'conexiones.log')
    $servidor = IniciarSilice
    $segundos = EsperarSalud $Url 60
    Afirmar ($null -ne $segundos) "la salud respondió 200 en <= 60 s (fueron $segundos s)"
    @{ salud_s = $segundos; perfil = $Perfil; version = $Version } | ConvertTo-Json |
        Set-Content (Join-Path $Salida 'tiempos.json')
    $escuchas = Escuchas $servidor.Id
    Afirmar ((Escucha $escuchas '127.0.0.1' 8501) -ge 1) 'el 8501 escucha en 127.0.0.1'
    Afirmar ((EnTodas $escuchas) -eq 0) 'nada de Sílice escucha en 0.0.0.0 ni en ::'
    $api = Contar ($escuchas | Where-Object { $_.LocalPort -eq 8000 })
    Afirmar ($api -eq 0) 'el 8000 (API) no escucha'

    Paso '5. Navegador sin interfaz'
    $navegador = Join-Path $Raiz 'instalador\navegador.py'
    & uv run --no-project --with playwright python $navegador --url $Url `
        --salida (Join-Path $Salida 'peticiones.json')
    Afirmar ($LASTEXITCODE -eq 0) 'el navegador no pidió nada fuera de 127.0.0.1 (ni telemetría)'
    if ($Perfil -eq 'completo') {
        $modelo = Operacion @('diagnostico-similitud')
        Afirmar ($modelo -eq 0) 'el modelo de similitud carga sin red'
    }

    Paso '6. Parada, puerto libre e inventario sin cambios'
    Afirmar ((Operacion @('parar')) -eq 0) 'operacion parar terminó con 0'
    Start-Sleep -Seconds 2
    Afirmar ($null -eq (EsperarSalud $Url 3)) 'el puerto quedó libre'
    $despues = ArbolDe $Programa
    Afirmar (-not (Compare-Object $antes $despues)) 'nada se escribió en la carpeta del programa'
    $peticiones = Get-Content (Join-Path $Salida 'proxy.log') -ErrorAction SilentlyContinue
    Afirmar ((Contar $peticiones) -eq 0) 'el proxy testigo anotó 0 peticiones'

    Paso '7. Actualización con Sílice en marcha y bases viejas sin migrar'
    $casos = Join-Path $Datos 'casos'
    New-Item -ItemType Directory -Force -Path $casos | Out-Null
    $bases = Join-Path $Raiz 'tests\fixtures\bases'
    Copy-Item (Join-Path $bases 'v0_5_0\demo.db') (Join-Path $casos 'v050_demo.db')
    Copy-Item (Join-Path $bases 'v0_9_0\demo.db') (Join-Path $casos 'v090_demo.db')
    $servidor = IniciarSilice
    Afirmar ($null -ne (EsperarSalud $Url 60)) 'Sílice arrancó antes de actualizar'
    $codigo = InstalarSilencioso $Actualizacion (Join-Path $Salida 'actualizacion.log')
    Afirmar ($codigo -eq 0) "la actualización terminó con 0 (fue $codigo)"
    Afirmar ($null -eq (EsperarSalud $Url 3)) 'el instalador detuvo Sílice antes de copiar'
    $juegos = @(Get-ChildItem -LiteralPath $Respaldos -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName 'ficha.json') })
    Afirmar ($juegos.Count -ge 1) 'existe un juego de respaldo con su ficha'
    & uv run python (Join-Path $Raiz 'instalador\verificar_bases.py') --casos $casos `
        --par '0.5.0:demo.db=v050_demo.db' --par '0.9.0:demo.db=v090_demo.db'
    Afirmar ($LASTEXITCODE -eq 0) 'las dos bases están en head y cuadran con su ficha'

    Paso '8. Red local en la IP de la interfaz'
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)' } |
        Select-Object -First 1).IPAddress
    Afirmar ($null -ne $ip) 'el runner tiene una interfaz con dirección privada'
    if ($ip) {
        Set-NetFirewallRule -DisplayName $ReglaSalida -RemoteAddress (RangosSin $ip)
        Afirmar ((Operacion @('red-local', 'activar', '--ip', $ip, '--si')) -eq 0) "activar en $ip"
        $filtros = Get-NetFirewallRule -DisplayName 'Silice red local*' |
            Get-NetFirewallApplicationFilter
        $conPrograma = Contar ($filtros | Where-Object { $_.Program -eq $Python })
        Afirmar ($conPrograma -ge 1) 'la regla apunta al python.exe de la ruta con espacios y ñ'
        $servidor = IniciarSilice
        Afirmar ($null -ne (EsperarSalud "http://${ip}:8501" 60)) 'la salud responde por esa IP'
        $escuchas = Escuchas $servidor.Id
        Afirmar ((Escucha $escuchas $ip 8501) -ge 1) 'escucha solo en esa IP'
        Afirmar ((EnTodas $escuchas) -eq 0) 'nunca en 0.0.0.0'
        Afirmar ($null -eq (EsperarSalud $Url 3)) 'ya no responde en 127.0.0.1'
        Operacion @('parar') | Out-Null
        Afirmar ((Operacion @('red-local', 'desactivar')) -eq 0) 'red-local desactivar'
        $quedan = Get-NetFirewallRule -DisplayName 'Silice red local*' -ErrorAction SilentlyContinue
        Afirmar ((Contar $quedan) -eq 0) 'las reglas del cortafuegos se borraron'
    }

    Paso '9. Ninguna conexión saliente en toda la corrida'
    Stop-Job $trabajo -ErrorAction SilentlyContinue
    $conexiones = Get-Content (Join-Path $Salida 'conexiones.log') -ErrorAction SilentlyContinue
    $propias = if ($ip) { '|' + [regex]::Escape($ip) } else { '' }
    $locales = '^(127\.0\.0\.1|::1|0\.0\.0\.0|::|\[::\]' + $propias + '):'
    $ajenas = @($conexiones | Where-Object { $_ -and ($_ -split ' ')[3] -notmatch $locales })
    Afirmar ($ajenas.Count -eq 0) "el muestreo no vio conexiones ajenas ($($ajenas.Count))"
    $vistos = Get-Content (Join-Path $Salida 'conexiones.log.pids') -ErrorAction SilentlyContinue |
        ForEach-Object { ($_ -split ' ')[1] } | Sort-Object -Unique
    $descartes = DescartesDe $registroFw $vistos
    Afirmar ((Contar $descartes) -eq 0) 'el cortafuegos no descartó nada de Sílice hacia fuera'

    Paso '10. Desinstalación: el programa se va y los datos quedan'
    $desinstalador = Join-Path $Programa 'unins000.exe'
    Start-Process -FilePath $desinstalador -Wait `
        -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'
    $limite = (Get-Date).AddSeconds(60)
    while ((Test-Path $Programa) -and (Get-Date) -lt $limite) { Start-Sleep -Seconds 2 }
    Afirmar (-not (Test-Path $Programa)) '{app} ya no existe'
    $quedan = (Test-Path (Join-Path $Datos 'instalacion.db')) -and (Test-Path $casos) -and
        (Test-Path $Respaldos)
    Afirmar $quedan 'la carpeta de datos y sus respaldos siguen ahí'
}
finally {
    if ($trabajo) { Stop-Job $trabajo -ErrorAction SilentlyContinue }
    if ($trabajo) { Remove-Job $trabajo -Force -ErrorAction SilentlyContinue }
    if ($proxy) { Stop-Process -Id $proxy.Id -Force -ErrorAction SilentlyContinue }
    Remove-NetFirewallRule -DisplayName $ReglaSalida -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName 'Silice red local*' -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue
}
Write-Host "`nFallos: $($Fallos.Count)"
$Fallos | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
exit ([int]($Fallos.Count -gt 0))
```
Notas de implementación: (1) los pasos del spec se agrupan por el orden real (parar antes de
copiar las bases viejas, actualizar con el servidor arriba, muestreo hasta el final); (2)
`Stop-Process` aquí solo termina el proxy que **este script** lanzó, nunca un proceso ajeno; (3) si
`navegador.py` no puede usarse (Edge o Playwright), el script falla en vez de omitirse: el sustituto
del spec (escanear HTML y JS) es un ruling explícito y se anota en la bitácora; (4) el script se
guarda como UTF-8 con BOM (PowerShell 5.1 lo exige para `ñ`; `pwsh` 7 no).

- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/unit/test_humo_piezas.py -v -W error`;
`uv run ruff check instalador tests/unit/test_humo_piezas.py`.
Sintaxis de PowerShell (donde haya `pwsh`): `pwsh -NoProfile -Command "$e=$null;
[System.Management.Automation.Language.Parser]::ParseFile('instalador/humo.ps1',[ref]$null,[ref]$e);
if ($e) { $e; exit 1 }"` (la CI lo repite en T17).

- [ ] **Paso 5: Commit y PR (cierra `inc/100-s5-4-humo`)**
```bash
git add instalador/humo.ps1 instalador/navegador.py instalador/proxy_testigo.py \
  instalador/verificar_bases.py
git commit -m "feat(instalador): prueba de humo con cortafuegos de salida y navegador" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-4-humo
gh pr create --base main --head inc/100-s5-4-humo --title "S5-4: prueba de humo" --body-file -
```

---
### Tarea 17: `instalador.yml`, `instalador/auditar.py` (pip-audit esencial) y su prueba

**Rama:** `inc/100-s5-4-flujo` (sale de `origin/main` con T16 fusionada)   **Rol:**
sf-ingeniero-pruebas
**Archivos:**
- Crear: `.github/workflows/instalador.yml`, `instalador/auditar.py`,
  `docs/pip-audit-aceptadas.toml`
- Modificar: `.github/workflows/ci.yml` (paso «Meta de Silice»: `--version 1.0.0 --hasta S5-4`)
- Prueba: `tests/unit/test_auditar.py`, `tests/unit/test_ci_instalador.py`

**Interfaces:**
- Consume: `instalador/construir.py`, `tamanos.py`, `humo.ps1`, `verificar_bases.py` (T14, T16),
  `scripts/verificar_version.py` (T4).
- Produce: en `instalador.auditar`: `PIP_AUDIT = "2.9.0"`, `fusionar(resultados) -> dict`,
  `vulnerabilidades(resultado) -> list[dict]`, `cargar_aceptadas(ruta) -> dict[str, Aceptada]`,
  `evaluar(resultado, aceptadas, hoy) -> Veredicto(abiertas, aceptadas, vencidas, no_auditadas)`,
  `auditar_capa(requisitos, ejecutar=...) -> dict`, `main(argv)`. El flujo publica por perfil los
  artefactos `instalador-<perfil>`, `tamanos-<perfil>`, `pip-audit-<perfil>` y `humo-<perfil>`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_auditar.py`:
```python
"""pip-audit esencial con rulings que vencen (SEG-14; spec S5 §10.2)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from instalador import auditar

LIMPIA = {"dependencies": [{"name": "alfa", "version": "1.0", "vulns": []}], "fixes": []}
CON_VULN = {
    "dependencies": [
        {"name": "alfa", "version": "1.0", "vulns": []},
        {
            "name": "beta",
            "version": "2.0",
            "vulns": [
                {
                    "id": "PYSEC-2026-1",
                    "fix_versions": ["2.1"],
                    "aliases": ["CVE-2026-0001"],
                    "description": "x",
                }
            ],
        },
        {"name": "gamma", "version": "3.0", "skip_reason": "Dependency not found on PyPI"},
    ],
    "fixes": [],
}
HOY = date(2026, 10, 11)


def test_vulnerabilidades_lista_paquete_version_id_y_alias() -> None:
    (v,) = auditar.vulnerabilidades(CON_VULN)
    assert (v["paquete"], v["version"], v["id"]) == ("beta", "2.0", "PYSEC-2026-1")
    assert v["alias"] == ["CVE-2026-0001"] and v["arreglo"] == ["2.1"]


def test_una_capa_limpia_no_tiene_nada_abierto() -> None:
    veredicto = auditar.evaluar(LIMPIA, {}, HOY)
    assert veredicto.abiertas == [] and veredicto.no_auditadas == []


def test_una_vulnerabilidad_sin_ruling_queda_abierta() -> None:
    veredicto = auditar.evaluar(CON_VULN, {}, HOY)
    assert [v["id"] for v in veredicto.abiertas] == ["PYSEC-2026-1"]
    assert veredicto.no_auditadas == ["gamma 3.0: Dependency not found on PyPI"]


def test_un_ruling_vigente_la_acepta_por_id_o_por_alias(tmp_path: Path) -> None:
    ruta = tmp_path / "aceptadas.toml"
    ruta.write_text(
        '[[aceptada]]\nid = "CVE-2026-0001"\nruling = "RP10-20"\nhasta = 2026-12-31\n'
        'razon = "no se llama a la función afectada"\n',
        encoding="utf-8",
    )
    veredicto = auditar.evaluar(CON_VULN, auditar.cargar_aceptadas(ruta), HOY)
    assert veredicto.abiertas == [] and [v["id"] for v in veredicto.aceptadas] == ["PYSEC-2026-1"]


def test_un_ruling_vencido_vuelve_a_abrir_la_vulnerabilidad(tmp_path: Path) -> None:
    ruta = tmp_path / "aceptadas.toml"
    ruta.write_text(
        '[[aceptada]]\nid = "PYSEC-2026-1"\nruling = "RP10-20"\nhasta = 2026-10-10\nrazon = "x"\n',
        encoding="utf-8",
    )
    veredicto = auditar.evaluar(CON_VULN, auditar.cargar_aceptadas(ruta), HOY)
    assert [v["id"] for v in veredicto.abiertas] == ["PYSEC-2026-1"]
    assert [v["id"] for v in veredicto.vencidas] == ["PYSEC-2026-1"]


@pytest.mark.parametrize("falta", ["id", "ruling", "hasta", "razon"])
def test_una_excepcion_sin_ruling_o_sin_fecha_es_invalida(tmp_path: Path, falta: str) -> None:
    campos = {"id": '"X-1"', "ruling": '"RP10-20"', "hasta": "2026-12-31", "razon": '"porque"'}
    del campos[falta]
    ruta = tmp_path / "aceptadas.toml"
    ruta.write_text(
        "[[aceptada]]\n" + "\n".join(f"{k} = {v}" for k, v in campos.items()), encoding="utf-8"
    )
    with pytest.raises(ValueError, match=falta):
        auditar.cargar_aceptadas(ruta)


def test_el_archivo_de_aceptadas_del_repositorio_es_valido_y_empieza_vacio() -> None:
    assert auditar.cargar_aceptadas(auditar.RUTA_ACEPTADAS) == {}


def test_fusionar_une_capas_sin_duplicar_paquetes() -> None:
    otra = {
        "dependencies": [
            {"name": "alfa", "version": "1.0", "vulns": []},
            {"name": "delta", "version": "4.0", "vulns": []},
        ],
        "fixes": [],
    }
    nombres = [d["name"] for d in auditar.fusionar([LIMPIA, otra])["dependencies"]]
    assert sorted(nombres) == ["alfa", "delta"]


def test_main_escribe_el_json_y_sale_con_1_si_hay_algo_abierto(tmp_path: Path) -> None:
    requisitos = tmp_path / "req.txt"
    requisitos.write_text("beta==2.0\n", encoding="utf-8")
    salida = tmp_path / "pip-audit.json"

    def ejecutar(orden, **k):
        destino = Path(orden[orden.index("--output") + 1])
        destino.write_text(json.dumps(CON_VULN), encoding="utf-8")
        return 1  # pip-audit sale con 1 si encontró vulnerabilidades, pero escribe el JSON

    codigo = auditar.main(
        ["--capa", f"basica={requisitos}", "--salida", str(salida)], ejecutar=ejecutar
    )
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert codigo == 1 and datos["pip_audit"] == auditar.PIP_AUDIT
    assert [v["id"] for v in datos["abiertas"]] == ["PYSEC-2026-1"] and "fecha" in datos
    assert datos["capas"] == ["basica"]


def test_la_orden_de_pip_audit_no_resuelve_ni_instala_nada(tmp_path: Path) -> None:
    visto: list[list[str]] = []

    def ejecutar(orden, **k):
        visto.append(list(orden))
        Path(orden[orden.index("--output") + 1]).write_text(json.dumps(LIMPIA), encoding="utf-8")
        return 0

    auditar.auditar_capa(tmp_path / "req.txt", ejecutar=ejecutar)
    orden = visto[0]
    assert orden[:5] == ["uv", "tool", "run", "--from", f"pip-audit=={auditar.PIP_AUDIT}"]
    assert "--no-deps" in orden and "--disable-pip" in orden and "json" in orden
```

`tests/unit/test_ci_instalador.py`:
```python
"""El flujo del instalador: Windows fijo, sin secretos, con el orden del spec (§11.2)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
RUTA = RAIZ / ".github" / "workflows" / "instalador.yml"
TEXTO = RUTA.read_text(encoding="utf-8")
DOC = yaml.safe_load(TEXTO)
CI = yaml.safe_load((RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))


def _pasos(trabajo: str) -> list[dict]:
    return DOC["jobs"][trabajo]["steps"]


def _indice(trabajo: str, huella: str) -> int:
    for i, paso in enumerate(_pasos(trabajo)):
        if huella in str(paso.get("run", "")) + str(paso.get("uses", "")) + str(
            paso.get("name", "")
        ):
            return i
    raise AssertionError(f"ningún paso de {trabajo} contiene {huella!r}")


def test_corre_en_windows_2025_fijo_con_permisos_de_solo_lectura() -> None:
    assert DOC["jobs"]["construir"]["runs-on"] == "windows-2025"
    assert DOC["permissions"] == {"contents": "read"}
    assert "windows-latest" not in TEXTO


def test_no_usa_secretos_ni_permisos_de_escritura() -> None:
    assert "secrets." not in TEXTO and "contents: write" not in TEXTO
    assert "id-token" not in TEXTO and "pull-requests: write" not in TEXTO


def test_se_dispara_con_etiquetas_a_mano_y_con_las_rutas_del_instalador() -> None:
    disparos = DOC.get("on") or DOC[True]
    assert disparos["push"]["tags"] == ["v*"] and "workflow_dispatch" in disparos
    rutas = set(disparos["pull_request"]["paths"])
    assert {"instalador/**", "operacion/**", "migraciones/**", "pyproject.toml", "uv.lock"} <= rutas


def test_las_acciones_y_uv_estan_fijadas_a_version_exacta() -> None:
    for uso in re.findall(r"uses:\s*(\S+)", TEXTO):
        assert re.search(r"@v\d+(\.\d+\.\d+)?$", uso), uso
    versiones = {
        paso["with"]["version"]
        for flujo in (DOC, CI)
        for trabajo in flujo["jobs"].values()
        for paso in trabajo["steps"]
        if str(paso.get("uses", "")).startswith("astral-sh/setup-uv")
    }
    assert versiones == {"0.11.9"}  # la misma de ci.yml


def test_el_completo_solo_va_con_etiqueta_o_a_mano() -> None:
    plan = DOC["jobs"]["plan"]["steps"][0]["run"]
    assert 'push) perfiles=\'["basico","completo"]\'' in plan
    assert "*) perfiles='[\"basico\"]'" in plan  # los PR: solo el básico


def test_la_etiqueta_debe_coincidir_con_pyproject_antes_de_gastar_windows() -> None:
    version = DOC["jobs"]["version"]
    assert "startsWith(github.ref, 'refs/tags/v')" in version["if"]
    assert any("verificar_version.py" in str(p.get("run", "")) for p in version["steps"])
    assert "version" in DOC["jobs"]["construir"]["needs"]


def test_el_orden_es_construir_tamano_auditar_humo() -> None:
    orden = [
        _indice("construir", "instalador/construir.py --perfil"),
        _indice("construir", "instalador/tamanos.py"),
        _indice("construir", "instalador/auditar.py"),
        _indice("construir", "--solo-sumas"),
        _indice("construir", "./instalador/humo.ps1"),
    ]
    assert orden == sorted(orden) and len(set(orden)) == 5


def test_el_instalador_de_actualizacion_se_compila_con_el_parche_siguiente() -> None:
    assert "--solo-iss --version" in "\n".join(str(p.get("run", "")) for p in _pasos("construir"))
    assert "--imprimir parche" in TEXTO


def test_los_artefactos_se_suben_aunque_falle_el_humo() -> None:
    subidas = [p for p in _pasos("construir") if "upload-artifact" in str(p.get("uses", ""))]
    nombres = " ".join(str(p["with"]["name"]) for p in subidas)
    for esperado in ("instalador-", "tamanos-", "pip-audit-", "humo-"):
        assert esperado in nombres, esperado
    assert all(p.get("if") == "always()" for p in subidas if "humo-" in str(p["with"]["name"]))


def test_el_instalador_de_parche_no_se_publica() -> None:
    subida = next(
        p for p in _pasos("construir") if "instalador-" in str(p.get("with", {}).get("name", ""))
    )
    ruta = str(subida["with"]["path"])
    assert "manifiesto.json" in ruta and "SHA256SUMS-" in ruta
    assert "VERSION_PARCHE" not in ruta


def test_la_sintaxis_de_humo_se_comprueba_antes_de_correrlo() -> None:
    assert _indice("construir", "Parser]::ParseFile") < _indice(
        "construir", "./instalador/humo.ps1"
    )


def test_ci_corre_la_meta_de_la_1_0_0_hasta_s5_4() -> None:
    meta = next(
        p
        for t in CI["jobs"].values()
        for p in t["steps"]
        if "scripts/meta_silice.py" in str(p.get("run", ""))
    )
    assert "--version 1.0.0 --hasta S5-4" in " ".join(str(meta["run"]).split())


@pytest.mark.parametrize("nombre", ["plan", "version", "construir"])
def test_cada_trabajo_tiene_nombre_y_plazo(nombre: str) -> None:
    assert DOC["jobs"][nombre].get("name")
    if nombre == "construir":
        assert DOC["jobs"][nombre]["timeout-minutes"] <= 120
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_auditar.py tests/unit/test_ci_instalador.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'auditar' from 'instalador'` y
`FileNotFoundError: ... instalador.yml`.
```bash
git add tests/unit/test_auditar.py tests/unit/test_ci_instalador.py
git commit -m "test(ci): pip-audit con rulings que vencen y flujo del instalador (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`docs/pip-audit-aceptadas.toml`:
```toml
# Vulnerabilidades conocidas que la 1.0.0 acepta, cada una con su ruling y su vencimiento (SEG-14).
# Sin entrada aquí, una vulnerabilidad hace fallar el flujo del instalador (spec S5 §10.2).
#
# [[aceptada]]
# id = "PYSEC-0000-00000"        # el id de pip-audit o cualquiera de sus alias (CVE-…, GHSA-…)
# ruling = "RP10-20"             # el ruling de la bitácora que la acepta
# hasta = 2026-12-31             # fecha de vencimiento: después vuelve a ser un fallo
# razon = "no se llama a la función afectada"
```

`instalador/auditar.py`:
```python
"""`pip-audit` esencial sobre las dependencias exportadas de cada capa (SEG-14; spec S5 §10.2).

    uv run python instalador/auditar.py --capa basica=build/req-basica.txt \\
        --capa similitud=build/req-completa.txt --salida pip-audit-basico.json

Audita el candado, no el equipo: lee los `requirements` que escribió `uv export` (versiones fijas,
sin resolver ni instalar nada). Una vulnerabilidad sin ruling vigente en
`docs/pip-audit-aceptadas.toml` hace salir con 1. El JSON queda adjunto a cada versión.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PIP_AUDIT = "2.9.0"
RAIZ = Path(__file__).resolve().parents[1]
RUTA_ACEPTADAS = RAIZ / "docs" / "pip-audit-aceptadas.toml"
CAMPOS = ("id", "ruling", "hasta", "razon")


@dataclass(frozen=True, slots=True)
class Aceptada:
    id: str
    ruling: str
    hasta: date
    razon: str


@dataclass(frozen=True, slots=True)
class Veredicto:
    abiertas: list[dict]
    aceptadas: list[dict]
    vencidas: list[dict]
    no_auditadas: list[str]


def cargar_aceptadas(ruta: Path = RUTA_ACEPTADAS) -> dict[str, Aceptada]:
    datos = tomllib.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else {}
    aceptadas = {}
    for entrada in datos.get("aceptada", []):
        for campo in CAMPOS:
            if campo not in entrada:
                raise ValueError(f"{ruta.name}: una excepción no tiene «{campo}»")
        aceptadas[entrada["id"]] = Aceptada(
            entrada["id"], entrada["ruling"], entrada["hasta"], entrada["razon"]
        )
    return aceptadas


def vulnerabilidades(resultado: Mapping) -> list[dict]:
    halladas = []
    for dependencia in resultado.get("dependencies", []):
        for vuln in dependencia.get("vulns", []):
            halladas.append(
                {
                    "paquete": dependencia["name"],
                    "version": dependencia["version"],
                    "id": vuln["id"],
                    "alias": list(vuln.get("aliases", [])),
                    "arreglo": list(vuln.get("fix_versions", [])),
                }
            )
    return halladas


def fusionar(resultados: Sequence[Mapping]) -> dict:
    unidas: dict[tuple[str, str], dict] = {}
    for resultado in resultados:
        for dependencia in resultado.get("dependencies", []):
            unidas.setdefault((dependencia["name"], dependencia.get("version", "")), dependencia)
    return {"dependencies": list(unidas.values()), "fixes": []}


def evaluar(resultado: Mapping, aceptadas: Mapping[str, Aceptada], hoy: date) -> Veredicto:
    abiertas, aceptadas_usadas, vencidas = [], [], []
    for vuln in vulnerabilidades(resultado):
        ruling = next((aceptadas[i] for i in (vuln["id"], *vuln["alias"]) if i in aceptadas), None)
        if ruling is None:
            abiertas.append(vuln)
        elif ruling.hasta < hoy:
            abiertas.append(vuln)
            vencidas.append(vuln)
        else:
            aceptadas_usadas.append({**vuln, "ruling": ruling.ruling})
    no_auditadas = [
        f"{d['name']} {d.get('version', '?')}: {d['skip_reason']}"
        for d in resultado.get("dependencies", [])
        if "skip_reason" in d
    ]
    return Veredicto(abiertas, aceptadas_usadas, vencidas, no_auditadas)


def _ejecutar(orden: Sequence[str], **_: object) -> int:
    return subprocess.run(list(orden), check=False).returncode


def auditar_capa(requisitos: Path, ejecutar: Callable[..., int] = _ejecutar) -> dict:
    with tempfile.TemporaryDirectory() as carpeta:
        salida = Path(carpeta) / "pip-audit.json"
        ejecutar(
            [
                "uv",
                "tool",
                "run",
                "--from",
                f"pip-audit=={PIP_AUDIT}",
                "pip-audit",
                "-r",
                str(requisitos),
                "--no-deps",
                "--disable-pip",
                "--format",
                "json",
                "--progress-spinner",
                "off",
                "--output",
                str(salida),
            ]
        )
        # pip-audit sale con 1 si encontró vulnerabilidades pero escribe el JSON igual; sin JSON
        # la auditoría no ocurrió y eso es un fallo, no un «limpio».
        if not salida.is_file():
            raise RuntimeError(f"pip-audit no produjo resultado para {requisitos}")
        return json.loads(salida.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None, ejecutar: Callable[..., int] = _ejecutar) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--capa", action="append", required=True, help="NOMBRE=archivo.txt")
    analizador.add_argument("--salida", type=Path, required=True)
    argumentos = analizador.parse_args(argv)
    nombres, resultados = [], []
    for capa in argumentos.capa:
        nombre, _, archivo = capa.partition("=")
        nombres.append(nombre)
        resultados.append(auditar_capa(Path(archivo), ejecutar))
    unido = fusionar(resultados)
    veredicto = evaluar(unido, cargar_aceptadas(), date.today())
    argumentos.salida.write_text(
        json.dumps(
            {
                "pip_audit": PIP_AUDIT,
                "fecha": date.today().isoformat(),
                "capas": nombres,
                "abiertas": veredicto.abiertas,
                "aceptadas": veredicto.aceptadas,
                "vencidas": veredicto.vencidas,
                "no_auditadas": veredicto.no_auditadas,
                "dependencias": len(unido["dependencies"]),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"{len(unido['dependencies'])} dependencias; abiertas: {len(veredicto.abiertas)}")
    return 1 if veredicto.abiertas else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`.github/workflows/instalador.yml`:
```yaml
# Instalador de Windows (spec S5 §11.2; RF-97, RF-98, RNF-19). Sin secretos y sin permisos de
# escritura: publicar el release y firmar SHA256SUMS lo hace el controlador a mano
# (RP10-3, RP10-11).
name: Instalador

on:
  push:
    tags: ["v*"]
  workflow_dispatch:
    inputs:
      perfiles:
        description: "Qué instaladores construir"
        type: choice
        options: [basico, completo, ambos]
        default: basico
  pull_request:
    paths:
      - "instalador/**"
      - "operacion/**"
      - "migraciones/**"
      - "pyproject.toml"
      - "uv.lock"
      - ".github/workflows/instalador.yml"

concurrency:
  group: instalador-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  plan:
    name: plan (perfiles)
    runs-on: ubuntu-latest
    outputs:
      perfiles: ${{ steps.elegir.outputs.perfiles }}
    steps:
      - id: elegir
        shell: bash
        env:
          EVENTO: ${{ github.event_name }}
          ELEGIDO: ${{ github.event.inputs.perfiles }}
        run: |
          case "$EVENTO" in
            push) perfiles='["basico","completo"]' ;;
            workflow_dispatch)
              case "$ELEGIDO" in
                completo) perfiles='["completo"]' ;;
                ambos) perfiles='["basico","completo"]' ;;
                *) perfiles='["basico"]' ;;
              esac ;;
            *) perfiles='["basico"]' ;;
          esac
          echo "perfiles=$perfiles" >> "$GITHUB_OUTPUT"

  version:
    name: la etiqueta coincide con pyproject
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10.1.0
        with:
          version: "0.11.9"
          enable-cache: true
      - run: uv sync --locked --only-group dev
      - name: Etiqueta = pyproject (PEP 440 normalizado)
        env:
          ETIQUETA: ${{ github.ref_name }}
        run: uv run --no-sync python scripts/verificar_version.py --etiqueta "$ETIQUETA"

  construir:
    name: construir y probar (${{ matrix.perfil }})
    needs: [plan, version]
    # `version` se omite si no es una etiqueta: `always()` deja correr a `construir` en ese caso.
    if: ${{ always() && needs.plan.result == 'success' && needs.version.result != 'failure' }}
    runs-on: windows-2025
    timeout-minutes: 120
    strategy:
      fail-fast: false
      matrix:
        perfil: ${{ fromJSON(needs.plan.outputs.perfiles) }}
    defaults:
      run:
        shell: pwsh
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - uses: astral-sh/setup-uv@v10.1.0
        with:
          version: "0.11.9"
          enable-cache: true

      - name: Inno Setup
        run: |
          $pf = ${env:ProgramFiles(x86)}
          $iscc = Join-Path $pf 'Inno Setup 6\ISCC.exe'
          if (-not (Get-Command ISCC.exe -ErrorAction SilentlyContinue) -and
              -not (Test-Path $iscc)) {
            choco install innosetup --version 6.7.1 --no-progress -y
          }
          Get-ChildItem -Path $pf, $env:ProgramFiles -Filter ISCC.exe -Recurse -Depth 2 `
            -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName

      - name: Entorno (las capas del instalador básico, para construir y verificar bases)
        run: >-
          uv sync --locked --extra ui --extra api --extra planos --extra civil
          --extra informes --extra bcv --extra anomalias --extra ia

      - name: Versiones
        run: |
          $v = uv run --no-sync python scripts/verificar_version.py --imprimir semver
          $p = uv run --no-sync python scripts/verificar_version.py --imprimir parche
          $s = if ('${{ matrix.perfil }}' -eq 'completo') { '-completo' } else { '' }
          "VERSION=$v" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
          "VERSION_PARCHE=$p" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
          "SUFIJO=$s" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8

      - name: Construir el instalador
        run: uv run --no-sync python instalador/construir.py --perfil ${{ matrix.perfil }}

      - name: Instalador de actualización (mismo programa, versión de parche +1; solo la prueba)
        run: >-
          uv run --no-sync python instalador/construir.py --perfil ${{ matrix.perfil }}
          --solo-iss --version $env:VERSION_PARCHE

      - name: Tamaño contra RNF-19 (falla si se pasa)
        run: >-
          uv run --no-sync python instalador/tamanos.py --perfil ${{ matrix.perfil }}
          --carpeta build/salida --version $env:VERSION
          --salida build/salida/tamanos-${{ matrix.perfil }}.json

      - name: pip-audit de cada capa (falla ante una vulnerabilidad sin ruling)
        run: |
          $capas = @('--capa', 'basica=build/req-basica.txt')
          if ('${{ matrix.perfil }}' -eq 'completo') {
            $capas += @('--capa', 'completa=build/req-completa.txt')
          }
          $salida = 'build/salida/pip-audit-${{ matrix.perfil }}.json'
          uv run --no-sync python instalador/auditar.py @capas --salida $salida

      - name: SHA256SUMS del instalador (sin firmar; la firma la pone el controlador)
        run: >-
          uv run --no-sync python instalador/construir.py --perfil ${{ matrix.perfil }}
          --solo-sumas --version $env:VERSION --extra pip-audit-${{ matrix.perfil }}.json

      - name: Sintaxis de humo.ps1
        run: |
          $errores = $null
          $humo = "$PWD/instalador/humo.ps1"
          [System.Management.Automation.Language.Parser]::ParseFile($humo, [ref]$null,
            [ref]$errores) | Out-Null
          if ($errores) { $errores | ForEach-Object { Write-Error $_ }; exit 1 }

      - name: Prueba de humo (asistente de IA apagado)
        run: |
          $exe = "build/salida/Silice-$env:VERSION$env:SUFIJO.exe"
          $parche = "build/salida/Silice-$env:VERSION_PARCHE$env:SUFIJO.exe"
          ./instalador/humo.ps1 -Instalador $exe -Actualizacion $parche -Version $env:VERSION `
            -Perfil ${{ matrix.perfil }} -Salida humo-salida

      - name: Subir el instalador y sus sumas
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: instalador-${{ matrix.perfil }}
          path: |
            build/salida/Silice-${{ env.VERSION }}${{ env.SUFIJO }}.exe
            build/salida/manifiesto.json
            build/salida/SHA256SUMS-${{ matrix.perfil }}
            build/salida/pip-audit-${{ matrix.perfil }}.json
          if-no-files-found: warn

      - name: Subir el tamaño
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: tamanos-${{ matrix.perfil }}
          path: build/salida/tamanos-${{ matrix.perfil }}.json
          if-no-files-found: warn

      - name: Subir el resultado de pip-audit
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pip-audit-${{ matrix.perfil }}
          path: build/salida/pip-audit-${{ matrix.perfil }}.json
          if-no-files-found: warn

      - name: Subir los registros de la prueba de humo
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: humo-${{ matrix.perfil }}
          path: humo-salida
          if-no-files-found: warn
```
Notas: (1) `Silice-$VERSION_PARCHE` solo se usa dentro del job; el instalador de parche **no** se
sube. (2) Las rutas de la CI de Windows con `pwsh` usan `/` y `$PWD` porque el paso corre en el
directorio del repositorio. (3)
`tests/unit/test_ci_instalador.py::test_el_orden_es_construir_tamano_auditar_humo`
busca las huellas `instalador/construir.py --perfil`, `instalador/tamanos.py`,
`instalador/auditar.py`,
`--solo-sumas` e `instalador/humo.ps1` en los pasos `run`, en ese orden.

`ci.yml`: el paso «Meta de Silice» pasa a `--version 1.0.0 --hasta S5-4 --junit reporte-pruebas.xml`
(el flujo solo sube el `--hasta` al cruzar cada compuerta; GS5-4 es esta).

- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_auditar.py tests/unit/test_ci_instalador.py
tests/unit/test_ci_silice.py -v -W error`
y `uv run ruff check instalador/auditar.py tests/unit/test_auditar.py
tests/unit/test_ci_instalador.py`.

Primera corrida real (cuesta minutos de Windows, H7): `gh workflow run instalador.yml --ref
inc/100-s5-4-flujo -f perfiles=ambos`; seguirla con `gh run watch`. Lo que sale de esa primera
corrida y se ajusta aquí, sin cambiar el diseño: la ruta de `ISCC.exe` en el runner; el valor
`/DVersion` (ver Tarea 15, paso 4); que `pip-audit` lea el formato de `uv export` (spec §10.2: «se
confirma en S5-4»); que `winget`/`choco` no hagan falta; el tamaño real de los dos instaladores,
que se anota en la bitácora y en §1.3.

- [ ] **Paso 5: Commit y PR (cierra GS5-4)**
```bash
git add .github/workflows/instalador.yml .github/workflows/ci.yml instalador/auditar.py \
  docs/pip-audit-aceptadas.toml
git commit -m "feat(ci): flujo del instalador con tamano, pip-audit y prueba de humo en Windows" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-4-flujo
gh pr create --base main --head inc/100-s5-4-flujo \
  --title "S5-4: flujo del instalador" --body-file -
```

### Compuerta GS5-4

- [ ] CI de Linux y Windows verde (`ci.yml`), con `--version 1.0.0 --hasta S5-4` en OK.
- [ ] `instalador.yml` verde en el PR (perfil básico) y en `workflow_dispatch` con `perfiles=ambos`:
  construir, tamaño (básico ≤ 150 MB, completo ≤ 650 MB), `pip-audit` sin vulnerabilidades abiertas
  y prueba de humo completa (RF-97 a–h, RF-98 con 0 conexiones salientes), con los artefactos
  `humo-*` descargados y leídos por una persona (`peticiones.json`, `proxy.log` vacío,
  `conexiones.log`). **El disparo por etiqueta se prueba por primera vez con `v1.0.0-rc.1`**
  (RP10-14):
  una etiqueta de prueba tendría que coincidir con `pyproject.toml` y no es posible sin cambiar la
  versión.
- [ ] Tamaños reales y minutos de Windows consumidos anotados en la bitácora (H7).
- [ ] Núcleo intacto; regresión literal intacta; 0 omitidas.
- [ ] Encargos (maestro §6.4): requisitos, arquitectura, pruebas y calidad, verificador de hechos y
  seguridad (que la CI no escriba ni tenga secretos; qué prueba la prueba de humo y qué no).

---

## S5-5 · Cierre (RNF-19, RNF-20, UC-24, GS5)

### Tarea 18: la parte S5 completa de la meta (`meta_silice_s5b.py`)

**Rama:** `inc/100-s5-5-meta` (sale de `origin/main` con GS5-4 cruzada)   **Rol:**
sf-ingeniero-pruebas
**Archivos:**
- Modificar: `scripts/meta_silice_s5b.py` (lo creó la Tarea 1); `scripts/README.md` (fila);
  `.gitignore` (`scripts/_salida_arranque.json`)
- Prueba: `tests/unit/test_meta_silice_s5b.py` (se amplía)

**Interfaces:**
- Consume: `scripts.meta_silice` (A6: `Comprobacion`, `Contexto`, `CifraDeTiempo`, `ParTDD`,
  `Parte`),
  `instalador.tamanos.evaluar` (T14), `instalador.auditar` (T17), `operacion.version` (T4).
- Produce, en `scripts.meta_silice_s5b`: `PARES_S5B` completo (una entrada por tarea 1 a 17),
  `CIFRAS`, y las comprobaciones `S5-M1`, `S5-M5a` (fase S5-2), `S5-M5`, `S5-M6`, `S5-M7`, `S5-M9`,
  `S5-M10`, `S5-CLAVE`, `S5-TRAZ` y `S5-ETIQUETAS` (fase S5-5), cada una con su evaluador puro:
  `evaluar_version(...)`, `evaluar_flujo(...)`, `evaluar_tamanos(...)`, `evaluar_arranque(...)`,
  `evaluar_pip_audit(...)`, `evaluar_clave(...)`, `evaluar_trazabilidad(...)`,
  `evaluar_etiquetas(...)`.

- [ ] **Paso 1: Escribir la prueba que falla** (se agrega al final de
`tests/unit/test_meta_silice_s5b.py`, que ya importa `m` y `Estado`)
```python
CHANGELOG = "## [Sin publicar]\n\n## [1.0.0-rc.1] - 2026-10-30\n\n- algo\n"


def test_s5_m5a_la_api_y_operacion_dan_la_version_de_pyproject() -> None:
    assert m.evaluar_version("1.0.0rc1", "1.0.0rc1", "1.0.0rc1", None, "1.0.0-rc.1")[0] is Estado.OK
    estado, detalle = m.evaluar_version("1.0.0rc1", "0.1.0", "1.0.0rc1", None, "1.0.0-rc.1")
    assert estado is Estado.FALLA and "API" in detalle


def test_s5_m5_exige_la_seccion_del_changelog_con_fecha() -> None:
    assert (
        m.evaluar_version("1.0.0rc1", "1.0.0rc1", "1.0.0rc1", CHANGELOG, "1.0.0-rc.1")[0]
        is Estado.OK
    )
    estado, detalle = m.evaluar_version(
        "1.0.0rc1", "1.0.0rc1", "1.0.0rc1", "## [Sin publicar]\n", "1.0.0-rc.1"
    )
    assert estado is Estado.FALLA and "CHANGELOG" in detalle
    sin_fecha = "## [1.0.0-rc.1]\n"
    assert (
        m.evaluar_version("1.0.0rc1", "1.0.0rc1", "1.0.0rc1", sin_fecha, "1.0.0-rc.1")[0]
        is Estado.FALLA
    )


EJECUCIONES = [
    {
        "databaseId": 3,
        "headSha": "bbb",
        "conclusion": "failure",
        "status": "completed",
        "event": "push",
    },
    {
        "databaseId": 2,
        "headSha": "aaa",
        "conclusion": "success",
        "status": "completed",
        "event": "push",
    },
]


def test_s5_m6_exige_un_flujo_verde_sin_cambios_del_instalador_despues() -> None:
    sin_cambios, con_cambios = (lambda sha: False), (lambda sha: True)
    es_ancestro = lambda sha: sha in {"aaa", "bbb"}  # noqa: E731
    assert m.evaluar_flujo(EJECUCIONES[1:], sin_cambios, es_ancestro)[0] is Estado.OK
    assert m.evaluar_flujo(EJECUCIONES[1:], con_cambios, es_ancestro)[0] is Estado.FALLA
    assert m.evaluar_flujo(EJECUCIONES[:1], sin_cambios, es_ancestro)[0] is Estado.FALLA
    assert m.evaluar_flujo(None, sin_cambios, es_ancestro)[0] is Estado.PENDIENTE
    assert m.evaluar_flujo([], sin_cambios, es_ancestro)[0] is Estado.PENDIENTE


def _tam(perfil: str, bytes_: int) -> dict:
    return {"perfil": perfil, "bytes": bytes_, "ok": True}


def test_s5_m7_exige_los_dos_perfiles_dentro_del_limite() -> None:
    ok = {"basico": _tam("basico", 120_000_000), "completo": _tam("completo", 600_000_000)}
    assert m.evaluar_tamanos(ok)[0] is Estado.OK
    pasado = {**ok, "basico": _tam("basico", 150_000_001)}
    assert m.evaluar_tamanos(pasado)[0] is Estado.FALLA
    assert m.evaluar_tamanos({"basico": ok["basico"]})[0] is Estado.PENDIENTE
    assert m.evaluar_tamanos(None)[0] is Estado.PENDIENTE


PLAN = "### Medición de arranque (RNF‑19)\n2026-10-30: 11,20; 11,40; 11,10; 11,30; 11,50 s\n"
ARRANQUE = {"mediana_s": 11.3, "valores_s": [11.2, 11.4, 11.1, 11.3, 11.5], "fecha": "2026-10-30"}


def test_s5_m9_la_medicion_dejo_su_cifra_y_esta_en_el_plan_de_pruebas() -> None:
    assert m.evaluar_arranque(ARRANQUE, PLAN)[0] is Estado.OK
    assert m.evaluar_arranque(None, PLAN)[0] is Estado.PENDIENTE
    assert m.evaluar_arranque({**ARRANQUE, "valores_s": [11.2]}, PLAN)[0] is Estado.FALLA
    assert m.evaluar_arranque({**ARRANQUE, "mediana_s": 25.0}, PLAN)[0] is Estado.FALLA
    assert m.evaluar_arranque(ARRANQUE, "sin la tabla")[0] is Estado.PENDIENTE


def test_s5_m10_pip_audit_sin_nada_abierto_en_los_dos_perfiles() -> None:
    limpio = {"abiertas": [], "vencidas": []}
    assert m.evaluar_pip_audit({"basico": limpio, "completo": limpio})[0] is Estado.OK
    sucio = {"abiertas": [{"id": "PYSEC-1", "paquete": "x"}], "vencidas": []}
    estado, detalle = m.evaluar_pip_audit({"basico": limpio, "completo": sucio})
    assert estado is Estado.FALLA and "PYSEC-1" in detalle
    assert m.evaluar_pip_audit(None)[0] is Estado.PENDIENTE


def test_s5_clave_la_publica_esta_versionada_y_su_huella_en_el_manual() -> None:
    publica = "ab" * 32
    import hashlib

    huella = hashlib.sha256(bytes.fromhex(publica)).hexdigest()
    manual = "Huella: " + " ".join(huella[i : i + 8] for i in range(0, 64, 8))
    assert m.evaluar_clave(publica, manual)[0] is Estado.OK
    assert m.evaluar_clave(None, manual)[0] is Estado.FALLA
    assert m.evaluar_clave("zz", manual)[0] is Estado.FALLA
    assert m.evaluar_clave(publica, "sin huella")[0] is Estado.FALLA


def test_s5_etiquetas_v1_0_tesis_apunta_al_commit_de_una_etiqueta_semver() -> None:
    etiquetas = {"v1.0.0": "c1", "v1.0.0-rc.1": "c0", "v1.0-tesis": "c1"}
    assert m.evaluar_etiquetas(etiquetas)[0] is Estado.OK
    assert m.evaluar_etiquetas({**etiquetas, "v1.0-tesis": "c9"})[0] is Estado.FALLA
    assert m.evaluar_etiquetas({"v1.0.0": "c1"})[0] is Estado.PENDIENTE


def test_s5_traz_cada_prueba_citada_en_el_plan_existe() -> None:
    plan = "| RF‑97 | `tests/unit/test_x.py::test_a` y `tests/unit/test_y.py` | verde |"
    existe = lambda archivo, prueba: (
        (archivo, prueba)
        in {  # noqa: E731
            ("tests/unit/test_x.py", "test_a"),
            ("tests/unit/test_y.py", None),
        }
    )
    assert m.evaluar_trazabilidad(plan, existe)[0] is Estado.OK
    assert m.evaluar_trazabilidad(plan, lambda a, p: False)[0] is Estado.FALLA


def test_las_fases_de_cada_comprobacion_son_las_del_spec() -> None:
    fases = {c.codigo: c.fase for c in m.PARTE.comprobaciones}
    assert fases["S5-M1"] == "S5-0" and fases["S5-M5a"] == "S5-2"
    for codigo in (
        "S5-M5",
        "S5-M6",
        "S5-M7",
        "S5-M9",
        "S5-M10",
        "S5-CLAVE",
        "S5-TRAZ",
        "S5-ETIQUETAS",
    ):
        assert fases[codigo] == "S5-5", codigo
    assert {c.fase for c in m.CIFRAS} == {"S5-5"}


def test_hay_un_par_de_prueba_e_implementacion_por_cada_tarea() -> None:
    implementaciones = {p.implementacion for p in m.PARES_S5B}
    for esperado in (
        "scripts/meta_silice_s5b.py",
        "operacion/firma_sumas.py",
        "operacion/version.py",
        "operacion/registro.py",
        "operacion/lanzador.py",
        "operacion/red.py",
        "api/proteccion.py",
        "operacion/eventos_perdidos.py",
        "ui/cliente.py",
        "instalador/manifiesto.py",
        "instalador/construir.py",
        "instalador/silice.iss",
        "instalador/humo.ps1",
        "instalador/auditar.py",
        ".github/workflows/instalador.yml",
        "instalador/publicar.py",
        "operacion/ordenes_100.py",
        "instalador/verificar_sumas.py",
        "instalador/tamanos.py",
        "scripts/verificar_version.py",
    ):
        assert esperado in implementaciones, esperado
    assert all(p.fase in {"S5-0", "S5-2", "S5-3", "S5-4", "S5-5"} for p in m.PARES_S5B)
```

- [ ] **Paso 2: Correrla y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_meta_silice_s5b.py -v -W error`
Esperado: FAIL con `AttributeError: module 'scripts.meta_silice_s5b' has no attribute
'evaluar_version'`.
```bash
git add tests/unit/test_meta_silice_s5b.py
git commit -m "test(scripts): comprobaciones S5-M5 a M10, clave, trazabilidad y etiquetas (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima** — `scripts/meta_silice_s5b.py` (se **extiende** el archivo
de la Tarea 1; se conservan `REQUISITOS_S5_0`, `FRASES_RNF08`, `evaluar_ers_final` y `_s5_m1`;
`re`, `sys` y `Path` ya están importados allí y `CifraDeTiempo` se suma a la importación de
`scripts.meta_silice`; las demás importaciones de abajo se agregan al bloque de importaciones):
```python
import hashlib
import json
import subprocess
import tempfile
from collections.abc import Callable, Mapping

from instalador.tamanos import evaluar as evaluar_tamano  # noqa: E402
from scripts.meta_silice import CifraDeTiempo  # noqa: E402

LIMITE_ARRANQUE_S = 20.0
RUTA_CLAVE = RAIZ / "operacion" / "clave_proyecto.pub"
RUTA_MANUAL = RAIZ / "docs" / "manual_instalacion.md"
RUTA_PLAN = RAIZ / "docs" / "plan_pruebas.md"
RUTAS_DEL_INSTALADOR = (
    "instalador",
    "operacion",
    "migraciones",
    "pyproject.toml",
    "uv.lock",
    ".github/workflows/instalador.yml",
)

PARES_S5B: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_meta_silice_s5b.py", "scripts/meta_silice_s5b.py", "S5-0"),
    ParTDD("tests/unit/test_documentos_s5_100.py", "docs/bitacora/2026-10-silice-100.md", "S5-0"),
    ParTDD("tests/unit/test_medir_capas.py", "instalador/medir_capas.py", "S5-0"),
    ParTDD("tests/unit/test_firma_sumas.py", "operacion/firma_sumas.py", "S5-0"),
    ParTDD("tests/unit/test_ordenes_clave.py", "operacion/ordenes_100.py", "S5-0"),
    ParTDD(
        "tests/unit/test_verificar_sumas_independiente.py", "instalador/verificar_sumas.py", "S5-0"
    ),
    ParTDD("tests/unit/test_version.py", "operacion/version.py", "S5-2"),
    ParTDD("tests/unit/test_registro.py", "operacion/registro.py", "S5-2"),
    ParTDD("tests/unit/test_verificar_version.py", "scripts/verificar_version.py", "S5-2"),
    ParTDD("tests/unit/test_red.py", "operacion/red.py", "S5-2"),
    ParTDD("tests/unit/test_lanzador.py", "operacion/lanzador.py", "S5-2"),
    ParTDD("tests/integration/test_api_clave.py", "api/proteccion.py", "S5-2"),
    ParTDD("tests/unit/test_eventos_perdidos.py", "operacion/eventos_perdidos.py", "S5-2"),
    ParTDD("tests/unit/test_ui_cliente.py", "ui/cliente.py", "S5-2"),
    ParTDD("tests/unit/test_ui_sin_cdn.py", "ui/estaticos/three.min.js", "S5-2"),
    ParTDD("tests/unit/test_ui_acerca.py", "ui/paginas/acerca.py", "S5-2"),
    ParTDD("tests/unit/test_ui_instalacion.py", "ui/paginas/instalacion.py", "S5-2"),
    ParTDD("tests/unit/test_manifiesto.py", "instalador/manifiesto.py", "S5-3"),
    ParTDD("tests/unit/test_programa.py", "operacion/programa.py", "S5-3"),
    ParTDD("tests/unit/test_construir.py", "instalador/construir.py", "S5-3"),
    ParTDD("tests/unit/test_tamanos.py", "instalador/tamanos.py", "S5-3"),
    ParTDD("tests/unit/test_licencias.py", "instalador/licencias.py", "S5-3"),
    ParTDD("tests/unit/test_iss.py", "instalador/silice.iss", "S5-3"),
    ParTDD("tests/unit/test_humo_piezas.py", "instalador/humo.ps1", "S5-4"),
    ParTDD("tests/unit/test_auditar.py", "instalador/auditar.py", "S5-4"),
    ParTDD("tests/unit/test_ci_instalador.py", ".github/workflows/instalador.yml", "S5-4"),
    ParTDD("tests/unit/test_publicar.py", "instalador/publicar.py", "S5-5"),
    ParTDD("tests/unit/test_medir_arranque.py", "scripts/medir_arranque.py", "S5-5"),
    ParTDD("tests/unit/test_manuales_s5.py", "docs/manual_instalacion.md", "S5-5"),
)
CIFRAS: tuple[CifraDeTiempo, ...] = (
    CifraDeTiempo(
        "RNF-19",
        "scripts/_salida_arranque.json",
        "mediana_s",
        "uv run python scripts/medir_arranque.py",
        "S5-5",
    ),
)


def _normal(texto: str) -> str:
    return texto.replace("\u2011", "-")


def evaluar_version(
    pyproject: str, api: str, operacion: str, changelog: str | None, semver: str
) -> tuple[Estado, str]:
    """S5-M5/M5a: una sola versión (pyproject = API = `operacion.version`) y, si se pide el
    CHANGELOG, su sección `## [semver] - AAAA-MM-DD`."""
    if api != pyproject:
        return Estado.FALLA, f"la API dice {api} y pyproject.toml {pyproject}"
    if operacion != pyproject:
        return Estado.FALLA, f"operacion.version dice {operacion} y pyproject.toml {pyproject}"
    if changelog is None:
        return Estado.OK, f"versión única: {pyproject}"
    if not re.search(
        rf"^## \[{re.escape(semver)}\] - \d{{4}}-\d{{2}}-\d{{2}}\s*$", changelog, re.M
    ):
        return Estado.FALLA, f"el CHANGELOG no tiene «## [{semver}] - AAAA-MM-DD»"
    return Estado.OK, f"versión única {pyproject} y sección {semver} del CHANGELOG"


def evaluar_flujo(
    ejecuciones: list[dict] | None,
    toca_despues: Callable[[str], bool],
    es_ancestro: Callable[[str], bool],
) -> tuple[Estado, str]:
    """S5-M6: hay un flujo del instalador verde sobre un commit que es ancestro de HEAD y nada
    del instalador cambió después."""
    if not ejecuciones:
        return Estado.PENDIENTE, "sin corridas de instalador.yml (¿`gh` autenticado?)"
    verdes = [
        e
        for e in ejecuciones
        if e.get("conclusion") == "success"
        and e.get("status") == "completed"
        and es_ancestro(e["headSha"])
    ]
    if not verdes:
        return Estado.FALLA, "ninguna corrida verde de instalador.yml sobre un ancestro de HEAD"
    if all(toca_despues(e["headSha"]) for e in verdes):
        return Estado.FALLA, "el instalador cambió después de su última corrida verde"
    return Estado.OK, "último flujo del instalador verde y vigente"


def evaluar_tamanos(artefactos: Mapping[str, Mapping] | None) -> tuple[Estado, str]:
    if not artefactos or not {"basico", "completo"} <= set(artefactos):
        return Estado.PENDIENTE, "faltan los tamaños de los dos perfiles (artefactos tamanos-*)"
    fuera = []
    for perfil in ("basico", "completo"):
        ok, mensaje = evaluar_tamano(perfil, int(artefactos[perfil]["bytes"]))
        if not ok:
            fuera.append(mensaje)
    if fuera:
        return Estado.FALLA, "; ".join(fuera)
    return Estado.OK, "; ".join(
        evaluar_tamano(p, int(artefactos[p]["bytes"]))[1] for p in artefactos
    )


def evaluar_arranque(datos: Mapping | None, plan_pruebas: str | None) -> tuple[Estado, str]:
    """S5-M9: la medición de RNF-19 dejó su cifra: cinco valores, mediana <= 20 s y la tabla en
    plan_pruebas §10 con fecha y los cinco valores."""
    if not datos or plan_pruebas is None:
        return (
            Estado.PENDIENTE,
            "sin scripts/_salida_arranque.json: corra scripts/medir_arranque.py",
        )
    valores = datos.get("valores_s", [])
    if len(valores) != 5 or not all(isinstance(v, (int, float)) for v in valores):
        return Estado.FALLA, f"se esperaban cinco valores y hay {valores!r}"
    if float(datos.get("mediana_s", 1e9)) > LIMITE_ARRANQUE_S:
        return Estado.FALLA, f"la mediana {datos['mediana_s']} s pasa de {LIMITE_ARRANQUE_S} s"
    texto = _normal(plan_pruebas)
    escritos = [f"{v:.2f}".replace(".", ",") for v in valores]
    if str(datos.get("fecha")) not in texto or not all(e in texto for e in escritos):
        return (
            Estado.PENDIENTE,
            "plan_pruebas §10 no trae la fecha y los cinco valores de la medición",
        )
    return (
        Estado.OK,
        f"arranque: mediana {datos['mediana_s']} s de cinco (<= {LIMITE_ARRANQUE_S} s)",
    )


def evaluar_pip_audit(archivos: Mapping[str, Mapping] | None) -> tuple[Estado, str]:
    if not archivos or not {"basico", "completo"} <= set(archivos):
        return Estado.PENDIENTE, "faltan los pip-audit de los dos perfiles"
    abiertas = [
        f"{perfil}: {v.get('paquete')} {v.get('id')}"
        for perfil, datos in archivos.items()
        for v in datos.get("abiertas", [])
    ]
    if abiertas:
        return Estado.FALLA, "vulnerabilidades abiertas: " + "; ".join(abiertas)
    return Estado.OK, "pip-audit sin vulnerabilidades abiertas en los dos perfiles"


def evaluar_clave(publica: str | None, manual: str | None) -> tuple[Estado, str]:
    """S5-CLAVE: `operacion/clave_proyecto.pub` está versionada (32 bytes en hex) y su huella
    SHA-256 aparece en el manual de instalación."""
    if publica is None:
        return Estado.FALLA, "falta operacion/clave_proyecto.pub (la ceremonia de la clave, T3)"
    try:
        crudo = bytes.fromhex(publica.strip())
    except ValueError:
        return Estado.FALLA, "clave_proyecto.pub no es hexadecimal"
    if len(crudo) != 32:
        return Estado.FALLA, f"clave_proyecto.pub mide {len(crudo)} bytes y debe medir 32"
    huella = hashlib.sha256(crudo).hexdigest()
    if manual is None or huella not in "".join(_normal(manual).split()):
        return Estado.FALLA, "el manual de instalación no trae la huella de la clave del proyecto"
    return Estado.OK, f"clave del proyecto versionada; huella {huella[:16]}… en el manual"


def evaluar_etiquetas(etiquetas: Mapping[str, str]) -> tuple[Estado, str]:
    """`v1.0-tesis` apunta al commit de una etiqueta `v1.0.x` (RS5-13), nunca a uno sin ella."""
    if "v1.0-tesis" not in etiquetas:
        return Estado.PENDIENTE, "todavía no existe v1.0-tesis"
    destino = etiquetas["v1.0-tesis"]
    semver = [t for t, c in etiquetas.items() if re.fullmatch(r"v1\.0\.\d+", t) and c == destino]
    if not semver:
        return Estado.FALLA, "v1.0-tesis no apunta al commit de ninguna etiqueta v1.0.x"
    return Estado.OK, f"v1.0-tesis = {semver[0]}"


def evaluar_trazabilidad(
    plan_pruebas: str | None, existe: Callable[[str, str | None], bool]
) -> tuple[Estado, str]:
    """Cada `archivo::prueba` (o archivo) citado en plan_pruebas §8.3 existe."""
    if plan_pruebas is None:
        return Estado.PENDIENTE, "falta docs/plan_pruebas.md"
    seccion = _normal(plan_pruebas).split("### 8.3", 1)[-1].split("\n### ", 1)[0]
    citas = re.findall(r"`(tests/[\w/.]+\.py)(?:::(\w+))?`", seccion)
    if not citas:
        return Estado.FALLA, "plan_pruebas §8.3 no cita ninguna prueba"
    faltan = [f"{a}::{p}" if p else a for a, p in citas if not existe(a, p or None)]
    if faltan:
        return Estado.FALLA, "citadas y no encontradas: " + ", ".join(sorted(set(faltan)))
    return Estado.OK, f"{len(citas)} pruebas citadas en §8.3 y todas existen"


def _gh(*argumentos: str) -> str | None:
    try:
        r = subprocess.run(
            ["gh", *argumentos], capture_output=True, text=True, check=False, cwd=RAIZ
        )
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


def _git(*argumentos: str) -> str | None:
    r = subprocess.run(["git", *argumentos], capture_output=True, text=True, check=False, cwd=RAIZ)
    return r.stdout.strip() if r.returncode == 0 else None


def _ejecuciones() -> list[dict] | None:
    salida = _gh(
        "run",
        "list",
        "--workflow",
        "instalador.yml",
        "--limit",
        "40",
        "--json",
        "conclusion,headSha,status,databaseId,event",
    )
    return json.loads(salida) if salida else None


def _artefacto(ejecucion: int, nombre: str) -> dict | None:
    with tempfile.TemporaryDirectory() as carpeta:
        if _gh("run", "download", str(ejecucion), "-n", nombre, "-D", carpeta) is None:
            return None
        archivos = list(Path(carpeta).rglob("*.json"))
        return json.loads(archivos[0].read_text(encoding="utf-8")) if archivos else None


def _artefactos_de_perfiles(prefijo: str) -> dict[str, dict] | None:
    """Los artefactos `<prefijo>-basico` y `<prefijo>-completo` de la corrida verde más reciente
    que tenga los dos (las de un PR solo traen el básico)."""
    for e in _ejecuciones() or []:
        if e.get("conclusion") == "success" and e.get("status") == "completed":
            datos = {
                p: _artefacto(int(e["databaseId"]), f"{prefijo}-{p}")
                for p in ("basico", "completo")
            }
            if all(datos.values()):
                return datos
    return None


def _leer(ruta) -> str | None:
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else None


def _m5a(_ctx: Contexto) -> tuple[Estado, str]:
    from api.main import app
    from operacion.version import a_semver, version

    return evaluar_version(version(), app.version, version(), None, a_semver(version()))


def _m5(_ctx: Contexto) -> tuple[Estado, str]:
    from api.main import app
    from operacion.version import a_semver, version

    return evaluar_version(
        version(), app.version, version(), _leer(RAIZ / "CHANGELOG.md"), a_semver(version())
    )


def _m6(_ctx: Contexto) -> tuple[Estado, str]:
    def toca_despues(sha: str) -> bool:
        return bool(_git("log", "--format=%H", f"{sha}..HEAD", "--", *RUTAS_DEL_INSTALADOR))

    def es_ancestro(sha: str) -> bool:
        return (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=RAIZ, check=False
            ).returncode
            == 0
        )

    return evaluar_flujo(_ejecuciones(), toca_despues, es_ancestro)


def _m7(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_tamanos(_artefactos_de_perfiles("tamanos"))


def _m9(_ctx: Contexto) -> tuple[Estado, str]:
    ruta = RAIZ / "scripts" / "_salida_arranque.json"
    datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else None
    return evaluar_arranque(datos, _leer(RUTA_PLAN))


def _m10(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_pip_audit(_artefactos_de_perfiles("pip-audit"))


def _clave(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_clave(_leer(RUTA_CLAVE), _leer(RUTA_MANUAL))


def _etiquetas(_ctx: Contexto) -> tuple[Estado, str]:
    salida = (
        _git(
            "for-each-ref",
            "--format=%(refname:short) %(*objectname) %(objectname)",
            "refs/tags/v1.0*",
        )
        or ""
    )
    etiquetas = {}
    for linea in salida.splitlines():
        partes = linea.split()
        if partes:
            etiquetas[partes[0]] = partes[1] if len(partes) == 3 else partes[-1]
    return evaluar_etiquetas(etiquetas)


def _traz(_ctx: Contexto) -> tuple[Estado, str]:
    def existe(archivo: str, prueba: str | None) -> bool:
        texto = _leer(RAIZ / archivo)
        return texto is not None and (prueba is None or f"def {prueba}(" in texto)

    return evaluar_trazabilidad(_leer(RUTA_PLAN), existe)


PARTE = Parte(
    nombre="S5 resto (1.0.0)",
    requisitos={"S5-0": REQUISITOS_S5_0},
    pares_tdd=PARES_S5B,
    cifras=CIFRAS,
    comprobaciones=(
        Comprobacion(
            "S5-M1", "ERS final: RNF-08 con dos excepciones y RNF-19 en calidad", "S5-0", _s5_m1
        ),
        Comprobacion("S5-M5a", "Versión única: pyproject = API = operacion.version", "S5-2", _m5a),
        Comprobacion("S5-M5", "Versión única y sección del CHANGELOG", "S5-5", _m5),
        Comprobacion("S5-M6", "Último flujo del instalador verde y vigente", "S5-5", _m6),
        Comprobacion(
            "S5-M7", "Instaladores <= 150 MB (básico) y <= 650 MB (completo)", "S5-5", _m7
        ),
        Comprobacion("S5-M9", "La medición de arranque de RNF-19 dejó su cifra", "S5-5", _m9),
        Comprobacion("S5-M10", "pip-audit sin vulnerabilidades abiertas", "S5-5", _m10),
        Comprobacion(
            "S5-CLAVE", "Clave pública del proyecto y su huella en el manual", "S5-5", _clave
        ),
        Comprobacion("S5-TRAZ", "Cada prueba de plan_pruebas §8.3 existe", "S5-5", _traz),
        Comprobacion("S5-ETIQUETAS", "v1.0-tesis = v1.0.x", "S5-5", _etiquetas),
    ),
)
```
(Las importaciones de `Estado`, `Comprobacion`, `Contexto`, `ParTDD`, `Parte`, `RAIZ` y las
constantes `REQUISITOS_S5_0` y `_s5_m1` ya están en el archivo de la Tarea 1; las de arriba se
agregan al bloque de importaciones y ruff las ordena. `PARTE` reemplaza a la de la Tarea 1.
**S5-M2** (núcleo intacto) no es acumulable y queda en `guardia_nucleo.py` y en cada compuerta;
**S5-M8** es C5 de la meta.)

`.gitignore`: `scripts/_salida_arranque.json`. `scripts/README.md`: fila
`| meta_silice_s5b.py | parte S5 de la 1.0.0: ERS final, versión única, flujo del instalador,
tamaños, arranque, pip-audit, clave y etiquetas | 1.0.0 |`.

- [ ] **Paso 4: Correrla y ver el verde**
Run: `uv run pytest tests/unit/test_meta_silice_s5b.py tests/unit/test_meta_silice.py -v -W error` y
`uv run ruff check scripts/meta_silice_s5b.py tests/unit/test_meta_silice_s5b.py`. Luego, con la
suite entera: `uv run python scripts/meta_silice.py --version 1.0.0 --hasta S5-4 --junit
reporte-pruebas.xml`
→ todas las filas en OK (C3 con los `PARES_S5B` de S5-0 a S5-4). Las de S5-5 quedan para la
compuerta GS5 (locales).

- [ ] **Paso 5: Commit y PR**
```bash
git add scripts/meta_silice_s5b.py scripts/README.md .gitignore
git commit -m "feat(scripts): parte S5 completa de la meta (version, flujo, tamanos, clave)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-5-meta
gh pr create --base main --head inc/100-s5-5-meta \
  --title "S5-5: meta completa de la parte S5" --body-file -
```

---

### Tarea 19: manuales, README, calidad, trazabilidad y `scripts/medir_arranque.py`

**Rama:** `inc/100-s5-5-manuales` (sale de `origin/main` con T18 fusionada)   **Rol:**
sf-ingeniero-pruebas
**Archivos:**
- Crear: `docs/manual_instalacion.md`, `scripts/medir_arranque.py`
- Modificar: `docs/manual_usuario.md` (§1 y §2), `docs/manual_tecnico.md` (secciones nuevas al
  final), `README.md` (Arranque rápido), `docs/calidad_iso25010.md` (§6 y §9),
  `docs/plan_pruebas.md`
  (§8.3 final), `docs/README.md` (índice), `CHANGELOG.md` (líneas de S5)
- Prueba: `tests/unit/test_manuales_s5.py`, `tests/unit/test_medir_arranque.py`,
  `tests/unit/test_trazabilidad_s5.py`

**Interfaces:**
- Consume: `operacion/clave_proyecto.pub` y la orden `huella-clave-proyecto` (T3);
  `operacion.lanzador`
  (T7); `operacion.config` (T5).
- Produce: `scripts.medir_arranque`: `resumen(valores) -> dict`, `tabla_markdown(datos) -> str`,
  `una_vez(python, cwd, puerto, datos, *, ejecutar...) -> float`, `main(argv)`; deja
  `scripts/_salida_arranque.json` (`mediana_s`, `valores_s`, `fecha`, `equipo`, `python`,
  `instalado`).

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_medir_arranque.py`:
```python
"""RNF-19: arranque del acceso directo a la salud 200, mediana de cinco (spec S5 §4.3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import medir_arranque as ma


def test_resumen_calcula_la_mediana_de_cinco() -> None:
    datos = ma.resumen([11.2, 11.4, 11.1, 11.3, 11.5])
    assert datos["mediana_s"] == 11.3 and datos["valores_s"] == [11.2, 11.4, 11.1, 11.3, 11.5]
    assert ma.resumen([5.123, 1.0, 9.999, 3.0, 2.0])["mediana_s"] == 3.0


@pytest.mark.parametrize("cantidad", [0, 1, 4, 6])
def test_resumen_exige_exactamente_cinco_valores(cantidad: int) -> None:
    with pytest.raises(ValueError, match="cinco"):
        ma.resumen([1.0] * cantidad)


def test_la_tabla_para_plan_de_pruebas_trae_fecha_y_los_cinco_valores() -> None:
    datos = {
        **ma.resumen([11.2, 11.4, 11.1, 11.3, 11.5]),
        "fecha": "2026-10-30",
        "equipo": "Windows-11",
    }
    tabla = ma.tabla_markdown(datos).replace("\u2011", "-")
    assert "### Medición de arranque (RNF-19)" in tabla and "2026-10-30" in tabla
    for esperado in ("11,20", "11,40", "11,10", "11,30", "11,50", "mediana 11,30 s"):
        assert esperado in tabla


def test_main_mide_una_corrida_de_calentamiento_y_cinco_y_deja_el_json(
    tmp_path: Path, monkeypatch
) -> None:
    tiempos = iter(
        [30.0, 11.2, 11.4, 11.1, 11.3, 11.5]
    )  # el primero es el calentamiento: se descarta
    monkeypatch.setattr(ma, "una_vez", lambda *a, **k: next(tiempos))
    salida = tmp_path / "arranque.json"
    assert ma.main(["--salida", str(salida)]) == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["valores_s"] == [11.2, 11.4, 11.1, 11.3, 11.5] and datos["mediana_s"] == 11.3
    assert {"fecha", "equipo", "python", "instalado"} <= set(datos)


def test_main_sale_con_1_si_la_mediana_pasa_de_20_s(tmp_path: Path, monkeypatch) -> None:
    tiempos = iter([30.0, 25.0, 26.0, 27.0, 28.0, 29.0])
    monkeypatch.setattr(ma, "una_vez", lambda *a, **k: next(tiempos))
    assert ma.main(["--salida", str(tmp_path / "a.json")]) == 1
```

`tests/unit/test_manuales_s5.py`:
```python
"""Los manuales dicen lo que S5 promete (spec S5 §10.5; RF-97, RF-98)."""

from __future__ import annotations

import hashlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _leer(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8").replace("\u2011", "-")


SECCIONES = (
    "Requisitos",
    "Comprobar la huella y la firma",
    "Instalar",
    "Primer arranque",
    "Casos",
    "Red local",
    "API y claves",
    "Actualizar",
    "Respaldos",
    "Restaurar",
    "Desinstalar",
    "SmartScreen",
    "Problemas frecuentes",
)


def test_el_manual_de_instalacion_tiene_las_secciones_del_spec() -> None:
    manual = _leer("docs/manual_instalacion.md")
    for seccion in SECCIONES:
        assert f"## {seccion}" in manual or f"### {seccion}" in manual, seccion


def test_el_manual_dice_lo_que_el_spec_manda_decir() -> None:
    manual = _leer("docs/manual_instalacion.md")
    minusculas = manual.lower()
    for frase in (
        "red de confianza",
        "WPA2",
        "cloudflared",
        "ngrok",
        "sin cifrar",
        "keyring",
        "no viaja en los respaldos",
        "%LOCALAPPDATA%\\Silice",
        "Windows protegió su PC",
        "SHA256SUMS",
        "SHA256SUMS.ed25519",
        "verificar_sumas.py",
        "operacion verificar-instalador",
        "base no adoptable",
        "versión más nueva",
        "puerto ocupado",
        "IP de la red local",
    ):
        assert frase.lower() in minusculas, frase


def test_el_manual_trae_la_huella_de_la_clave_publica_del_proyecto() -> None:
    publica = bytes.fromhex(
        (RAIZ / "operacion" / "clave_proyecto.pub").read_text(encoding="utf-8").strip()
    )
    huella = hashlib.sha256(publica).hexdigest()
    assert huella in "".join(_leer("docs/manual_instalacion.md").split())


def test_el_manual_de_usuario_empieza_por_el_instalador() -> None:
    manual = _leer("docs/manual_usuario.md")
    seccion1 = manual.split("## 2.", 1)[0]
    assert "Silice-" in seccion1 and "manual_instalacion.md" in seccion1
    assert "uv sync" not in seccion1  # el camino de desarrollo pasó al manual técnico


def test_el_manual_tecnico_explica_construir_la_cli_y_publicar() -> None:
    manual = _leer("docs/manual_tecnico.md")
    for titulo in ("Construir el instalador", "La orden `operacion`", "Publicar una versión"):
        assert titulo in manual, titulo
    for dato in (
        "instalador/construir.py",
        "SHA256SUMS",
        "firmar-sumas",
        "v1.0-tesis",
        "CHANGELOG.md",
    ):
        assert dato in manual, dato


def test_el_readme_tiene_los_dos_caminos_y_la_direccion_explicita() -> None:
    readme = _leer("README.md")
    assert "Silice-" in readme and "uv sync" in readme and "--server.address 127.0.0.1" in readme


def test_calidad_declara_rnf_19_y_la_ers_el_camino_del_instalador() -> None:
    assert "RNF-19" in _leer("docs/calidad_iso25010.md")
    assert (
        "cdnjs" not in _leer("docs/calidad_iso25010.md").split("## 7.", 1)[1].split("## 8.", 1)[0]
    )


def test_el_indice_de_docs_enlaza_el_manual_de_instalacion() -> None:
    assert "manual_instalacion.md" in _leer("docs/README.md")
```

`tests/unit/test_trazabilidad_s5.py`:
```python
"""Cada prueba que plan_pruebas §8.3 cita para RF-97 a RF-99 y RNF-19 existe (S5-TRAZ)."""

from __future__ import annotations

import re
from pathlib import Path

from scripts import meta_silice_s5b as meta
from scripts.meta_alpha import Estado

RAIZ = Path(__file__).resolve().parents[2]


def test_la_trazabilidad_de_la_1_0_0_cita_pruebas_que_existen() -> None:
    estado, detalle = meta._traz(None)
    assert estado is Estado.OK, detalle


def test_cada_requisito_de_la_1_0_0_tiene_al_menos_una_prueba_citada() -> None:
    texto = (RAIZ / "docs" / "plan_pruebas.md").read_text(encoding="utf-8").replace("\u2011", "-")
    seccion = texto.split("### 8.3", 1)[1].split("\n### ", 1)[0]
    viñetas = re.split(r"\n(?=- \*\*)", seccion)
    for requisito in ("RF-97", "RF-98", "RF-99", "RNF-19", "RNF-20"):
        texto_del_requisito = next(
            v for v in viñetas if v.lstrip("- ").startswith(f"**{requisito}")
        )
        assert "`tests/" in texto_del_requisito or "humo.ps1" in texto_del_requisito, requisito
```

- [ ] **Paso 2: Correrlas y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_medir_arranque.py tests/unit/test_manuales_s5.py
tests/unit/test_trazabilidad_s5.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'medir_arranque' from 'scripts'` y
`FileNotFoundError: docs/manual_instalacion.md`.
```bash
git add tests/unit/test_medir_arranque.py tests/unit/test_manuales_s5.py \
  tests/unit/test_trazabilidad_s5.py
git commit -m "test(docs): manuales de S5, trazabilidad y medicion de arranque (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`scripts/medir_arranque.py`:
```python
"""Mide RNF-19: del acceso directo a la salud 200 (spec S5 §4.3). Mediana de cinco, como RNF-11.

    uv run python scripts/medir_arranque.py [--python <python.exe de un Sílice instalado>]

Una corrida de calentamiento (crea las bases; se descarta) y cinco medidas de
`python -m operacion arrancar --sin-navegador` hasta que `/_stcore/health` responde 200. Usa una
carpeta de datos temporal y un puerto libre: no toca ningún dato real. Deja
`scripts/_salida_arranque.json` y, con `--tabla`, imprime el bloque para plan_pruebas §10.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion import config  # noqa: E402

LIMITE_S = 20.0
BANDERAS = ["-E", "-s", "-B", "-X", "utf8", "-m", "operacion"]


def resumen(valores: Sequence[float]) -> dict:
    if len(valores) != 5:
        raise ValueError(f"se miden exactamente cinco valores, no {len(valores)}")
    redondeados = [round(float(v), 2) for v in valores]
    return {"mediana_s": round(statistics.median(redondeados), 2), "valores_s": redondeados}


def tabla_markdown(datos: dict) -> str:
    coma = lambda v: f"{v:.2f}".replace(".", ",")  # noqa: E731
    valores = "; ".join(coma(v) for v in datos["valores_s"])
    return (
        "### Medición de arranque (RNF‑19)\n\n"
        f"{datos['fecha']}, {datos['equipo']}: {valores} s; mediana {coma(datos['mediana_s'])} s "
        f"frente al umbral de {int(LIMITE_S)} s en el equipo de desarrollo.\n"
    )


def _puerto_libre() -> int:
    with socket.socket() as zocalo:
        zocalo.bind(("127.0.0.1", 0))
        return int(zocalo.getsockname()[1])


def _salud(puerto: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/_stcore/health", timeout=1) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def una_vez(python: Path, cwd: Path, puerto: int, entorno: dict[str, str]) -> float:
    inicio = time.monotonic()
    servidor = subprocess.Popen(
        [str(python), *BANDERAS, "arrancar", "--sin-navegador"],
        cwd=cwd,
        env=entorno,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        while time.monotonic() - inicio < 120:
            if _salud(puerto):
                return time.monotonic() - inicio
            if servidor.poll() is not None:
                raise RuntimeError("Sílice terminó antes de responder la salud")
            time.sleep(0.1)
        raise TimeoutError("la salud no respondió en 120 s")
    finally:
        subprocess.run(
            [str(python), *BANDERAS, "parar"], cwd=cwd, env=entorno, check=False, timeout=60
        )
        try:
            servidor.wait(timeout=30)
        except subprocess.TimeoutExpired:
            servidor.terminate()  # solo el hijo que este mismo script lanzó


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--python", type=Path, default=Path(sys.executable))
    analizador.add_argument("--cwd", type=Path, default=RAIZ)
    analizador.add_argument(
        "--salida", type=Path, default=RAIZ / "scripts" / "_salida_arranque.json"
    )
    analizador.add_argument(
        "--tabla", action="store_true", help="imprime el bloque de plan_pruebas"
    )
    argumentos = analizador.parse_args(argv)
    with tempfile.TemporaryDirectory() as carpeta:
        puerto = _puerto_libre()
        entorno = {
            "SILICE_DATOS": carpeta,
            "SILICE_USUARIO": carpeta,
            **{
                k: v
                for k, v in os.environ.items()
                if not k.upper().startswith(("PYTHON", "SILICE_"))
            },
        }
        config.guardar_ajustes(
            Path(carpeta) / "config" / "silice.toml", config.Ajustes(puerto=puerto)
        )
        una_vez(argumentos.python, argumentos.cwd, puerto, entorno)  # calentamiento: crea las bases
        valores = [una_vez(argumentos.python, argumentos.cwd, puerto, entorno) for _ in range(5)]
    datos = {
        **resumen(valores),
        "fecha": date.today().isoformat(),
        "equipo": platform.platform(),
        "python": platform.python_version(),
        "instalado": config.es_producto(argumentos.cwd / "codigo")
        or config.es_producto(argumentos.cwd),
    }
    argumentos.salida.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    print(tabla_markdown(datos) if argumentos.tabla else json.dumps(datos))
    return 0 if datos["mediana_s"] <= LIMITE_S else 1


if __name__ == "__main__":
    raise SystemExit(main())
```
(`una_vez` se llama con cuatro argumentos; la prueba la sustituye por una función con `*a, **k`.)

`docs/manual_instalacion.md` (nuevo; la huella de la clave la imprime
`uv run python -m operacion huella-clave-proyecto` y se pega donde dice «Huella de la clave»):
```markdown
# Manual de instalación de Sílice

Para quien instala y administra Sílice en un equipo de la empresa. No hace falta saber programar.
La operación diaria está en el [manual de usuario](manual_usuario.md); cómo se construye el
instalador, en el [manual técnico](manual_tecnico.md).

## Requisitos

- Windows 10 22H2 u 11, de 64 bits. **No hace falta ser administrador** ni tener internet.
- Espacio libre: unos 700 MB para el instalador básico y unos 1,8 GB para el completo (con la
  similitud de partidas).
- Una cuenta de Windows por persona: cada cuenta tiene su propia copia del programa y sus propios
  datos.

## Comprobar la huella y la firma

Nunca ejecute un instalador que le llegó por correo, WhatsApp o memoria USB sin comprobarlo.
Junto al instalador vienen tres archivos: `SHA256SUMS`, `SHA256SUMS.ed25519` y `verificar_sumas.py`.

1. **Huella del archivo.** En PowerShell: `Get-FileHash .\Silice-1.0.0.exe -Algorithm SHA256`. El
   resultado debe ser el que aparece en `SHA256SUMS` para ese archivo.
2. **Firma de `SHA256SUMS`.** La firma demuestra que `SHA256SUMS` lo emitió el proyecto. Con `uv`
   instalado: `uv run --with cryptography verificar_sumas.py Silice-1.0.0.exe SHA256SUMS
   SHA256SUMS.ed25519 --publica <clave pública>`. Debe decir **VERIFICADO**.
3. **Huella de la clave.** El script imprime la huella SHA-256 de la clave pública que usó; debe ser
   exactamente esta (también está en la tesis):

   Huella de la clave: `<se pega aquí la salida de huella-clave-proyecto>`

   Si no coincide, **no instale** y avise a quien le entregó el instalador.

Si ya tiene Sílice instalado, el mismo control se hace sin `uv`:
`python -m operacion verificar-instalador Silice-1.0.1.exe SHA256SUMS SHA256SUMS.ed25519`.
Nunca abra `SHA256SUMS` con un editor y lo guarde: cualquier cambio (incluso los saltos de línea)
invalida la firma.

## Instalar

1. Haga doble clic en `Silice-<versión>.exe` (o en `Silice-<versión>-completo.exe` si necesita la
   similitud de partidas).
2. Windows puede mostrar «Windows protegió su PC» (ver SmartScreen más abajo).
3. Elija los componentes: el programa (obligatorio), el caso de demostración (datos construidos,
   ficticios) y, en el completo, la similitud de partidas.
4. Termine el asistente. Se crean los accesos «Sílice» y «Detener Sílice» en el menú Inicio.

El programa queda en `%LOCALAPPDATA%\Programs\Silice` y sus datos en `%LOCALAPPDATA%\Silice`. Si
alguien usa otra carpeta de datos por una razón especial, la variable es `SILICE_DATOS`.

## Primer arranque

Haga doble clic en «Sílice». Se abre una ventana minimizada (es el servidor: **ciérrela para
detener Sílice**) y el navegador entra a `http://127.0.0.1:8501`.

Como todavía no hay usuarios, Sílice deja un **código de instalación de un solo uso** en la
ventana del servidor y en `%LOCALAPPDATA%\Silice\datos\codigo_instalacion.txt`. Úselo en la pantalla
de acceso para crear el primer administrador. El código nunca se guarda en el registro.

## Casos

Los casos viven en `%LOCALAPPDATA%\Silice\datos\casos\`. En **Inicio** se elige uno de la lista, se
crea uno nuevo o se sube un archivo `.db`. No se pueden abrir archivos de otras carpetas ni de
carpetas de red: se copian primero. El caso de demostración trae datos construidos para aprender.

## Red local

Por defecto Sílice **solo atiende a este equipo**. Para que otros equipos de la oficina entren:

1. Use, en el equipo servidor, el acceso «Sílice: red local (administrador)» y acepte el aviso de
   Windows. Elija la interfaz de su red de confianza.
2. Reinicie Sílice. Los demás equipos abren `http://<IP del servidor>:8501`.
3. Para apagarla: `python -m operacion red-local desactivar` desde el mismo acceso.

**Red de confianza** es la red propia de la oficina, con WPA2 o WPA3 o cableada, y equipos
conocidos. **No** lo es la Wi‑Fi de la obra, una red pública ni la conexión compartida de un
teléfono. En Windows, la red debe estar marcada como **Privada**.

Sílice **no cifra** la conexión en la red local: las contraseñas viajan sin cifrar. La pantalla de
acceso lo avisa a quien entra desde otro equipo. Firmar, tocar las claves y crear claves de API
solo se puede desde el propio servidor.

**Nunca** use un túnel (`cloudflared`, `ngrok`, un proxy inverso) para publicar Sílice en internet:
anula las protecciones por IP y expone el sistema. Si Sílice detecta uno en ejecución, lo avisa al
arrancar. Si la IP del servidor cambia (DHCP), Sílice arranca solo en `127.0.0.1` y lo dice;
conviene reservar la IP en el enrutador.

## API y claves

La API está apagada. Para usarla (por ejemplo, desde un plugin) el administrador pone
`activa = true` en `%LOCALAPPDATA%\Silice\config\silice.toml`, reinicia y crea una clave en
Administración, desde el propio servidor; se muestra **una sola vez**. Toda ruta pide la clave
(cabecera `X-Silice-Clave`) salvo `/salud`.

## Actualizar

Ejecute el instalador de la versión nueva (después de comprobarlo). Sílice se detiene, se reemplaza
el programa, se respaldan las bases y se migran. Sus datos y sus presupuestos quedan. Si la
versión nueva no puede migrar una base, la base **no se toca** y el arranque explica qué hacer.

## Respaldos

Antes de cada migración Sílice guarda un juego de respaldo (la instalación y los casos juntos, con
una ficha) en `%LOCALAPPDATA%\Silice\respaldos\`; se conservan los cinco últimos. En
Administración → Instalación se puede crear uno a mano y descargarlo. **Un respaldo contiene todo**:
huellas de contraseñas, la clave de firma cifrada y huellas de claves de API. Guárdelo como guarda
las llaves. La clave de IA de la empresa se guarda con el almacén de claves de Windows (`keyring`)
y **no viaja en los respaldos**: en otro equipo hay que registrarla de nuevo.

## Restaurar

Con Sílice detenido: `python -m operacion restaurar <carpeta del juego>`. Restaurar la instalación
puede **deshacer en silencio** revocaciones, cuentas desactivadas y cambios de roles. Por eso
Sílice escribe `eventos_perdidos_<fecha>.json` y **bloquea las operaciones sensibles** hasta que el
administrador revise la lista (Administración → Instalación) y la marque como revisada.

## Desinstalar

«Configuración → Aplicaciones → Sílice → Desinstalar». Se borra el programa; **los datos y los
respaldos quedan** en `%LOCALAPPDATA%\Silice`. Bórrelos a mano si ya no los necesita.

## SmartScreen

Este instalador no lleva firma de código (cuesta una suscripción anual). Windows puede mostrar
**«Windows protegió su PC»**: pulse «Más información» y «Ejecutar de todas formas» **solo después**
de comprobar la huella y la firma como se explicó arriba.

## Problemas frecuentes

- **Puerto ocupado:** otro programa usa el 8501. Cierre ese programa o cambie `puerto` en
  `silice.toml`.
- **Base no adoptable:** una base muy antigua (anterior a la 0.4) no se puede migrar sola. Sílice
  no la toca; vuelva a sembrar el caso o pida ayuda con el juego de respaldo.
- **Esta base es de una versión más nueva:** instale esa versión o restaure el respaldo previo.
- **La IP de la red local ya no existe:** Sílice arrancó solo en este equipo. Vuelva a activar la
  red local y elija la IP nueva.
- **No abre el navegador:** abra `http://127.0.0.1:8501` a mano.
```

`docs/manual_usuario.md`, §1 pasa a:
```markdown
## 1. Instalación

La forma normal de instalar Sílice es el instalador de Windows (`Silice-<versión>.exe`, o
`Silice-<versión>-completo.exe` con la similitud de partidas): no necesita permisos de
administrador ni internet. Compruebe su huella y su firma antes de ejecutarlo; todos los pasos, la
red local, los respaldos y los problemas frecuentes están en el
[manual de instalación](manual_instalacion.md).

Después de instalar, el acceso «Sílice» del menú Inicio abre la aplicación en el navegador. Para
detenerla, cierre la ventana minimizada «Sílice» o use «Detener Sílice».

> La instalación para desarrollo pasó al [manual
  técnico](manual_tecnico.md#2-entorno-de-desarrollo).
```
(El contenido del §1 anterior —requisitos con `uv sync`— se traslada sin cambios al §2 del manual
técnico bajo el título «Instalación para desarrollo». El §2 del manual de usuario empieza con una
línea: «Con el instalador no hace falta sembrar nada a mano; Inicio ofrece el caso de
demostración.»)

`docs/manual_tecnico.md`, al final, tres secciones nuevas:
```markdown
## 12. Construir el instalador

`uv run python instalador/construir.py --perfil basico|completo` (solo Windows, con Inno Setup 6):
instala el Python autónomo de `uv`, exporta las capas desde `uv.lock` (`--frozen`, nunca resuelve),
copia el código según `instalador/manifiesto.toml` (lista blanca), compila, reúne las licencias y
llama a `ISCC.exe` con `instalador/silice.iss` (UTF‑8 con BOM, lo agrega `construir.py`). El
resultado
queda en `build/salida/` con `manifiesto.json` y `SHA256SUMS-<perfil>`. Lo que no está en el
manifiesto
no viaja; `tests/unit/test_manifiesto.py` lo comprueba. La CI lo repite en `instalador.yml` y corre
la
prueba de humo (`instalador/humo.ps1`).

## 13. La orden `operacion`

`python -m operacion <orden>`: `arrancar`, `parar`, `migrar`, `respaldar`, `restaurar`, `adoptar`,
`casos`, `revision`, `demostracion`, `red-local {activar,desactivar,estado}`, `eventos
{pendientes,revisar}`, `verificar-programa`, `verificar-instalador`, `generar-clave-proyecto`,
`firmar-sumas`, `huella-clave-proyecto` y `diagnostico-similitud`. Los accesos directos del
instalador llaman a `arrancar` y `parar` con `-E -s -B -X utf8`.

## 14. Publicar una versión

1. `CHANGELOG.md`: las líneas de `[Sin publicar]` pasan a `## [x.y.z] - AAAA-MM-DD`.
2. `pyproject.toml`: la versión en PEP 440 (`1.0.0rc1`); `uv lock`.
3. `uv run python scripts/meta_silice.py --version <x.y.z> --hasta <última fase> --junit
   reporte-pruebas.xml` en OK.
4. PR, CI verde, fusión con merge commit y etiqueta anotada `vX.Y.Z[-rc.N]` en `main`
   (`scripts/verificar_version.py` la compara con `pyproject.toml`).
5. Bajar los artefactos del flujo (`gh run download`), `instalador/publicar.py reunir …` arma el
   `SHA256SUMS` único y el controlador lo firma en su equipo con `firmar-sumas` (la clave privada no
   está en el repositorio ni en la CI).
6. `v1.0-tesis` es un alias anotado que apunta al commit de `v1.0.0` (o de un `v1.0.x`).
```

`README.md`, «Arranque rápido» pasa a dos caminos (usuario y desarrollo) y el comando de Streamlit
lleva `--server.address 127.0.0.1`:
```markdown
## Arranque rápido

**Para usar Sílice:** instale `Silice-<versión>.exe` (sin administrador, sin internet) después de
comprobar su huella y su firma ([manual de instalación](docs/manual_instalacion.md)) y abra
«Sílice» desde el menú Inicio.

**Para desarrollar:**

```powershell
uv sync --all-extras                      # crea .venv con las dependencias, el grupo dev y los
extras
uv run python scripts/descargar_modelo.py # una vez: modelo de similitud (la suite corre sin red)
uv run pytest -W error                    # suite de pruebas (advertencia = error)
uv run ruff check .                       # estilo
uv run python -m operacion migrar         # prepara las bases en data/ (casos e instalación)
uv run python -m streamlit run ui/app.py --server.address 127.0.0.1   # la interfaz
uv run uvicorn api.main:app --host 127.0.0.1   # la API (apagada en el producto; pide clave)
```
```
`docs/calidad_iso25010.md`: §6 agrega, antes del veredicto, el párrafo de RNF‑19 (instalador de
Windows sin administrador ni internet, tamaño, arranque, prueba de humo en cada versión, instalación
en cuenta estándar a mano) y su veredicto pasa a «cumple (con la medición de plan_pruebas §10)»; §7
reemplaza el párrafo de las «dos llamadas de red» por la redacción final de RNF‑08 (spec S5 §10.3:
three.js incrustado, modelo incluido en el completo, único tráfico saliente declarado: el asistente
en modo nube) y la fila «Seguridad» del resumen deja de citar three.js; la fila «Portabilidad» cita
RNF‑07 y RNF‑19. `docs/README.md`: una línea para `manual_instalacion.md`.

`docs/plan_pruebas.md`: la tabla de §8.3 (Tarea 1) pasa de «por escribir» a los estados reales, y se
agrega, al final de §10, el bloque que imprime `uv run python scripts/medir_arranque.py --tabla`.

- [ ] **Paso 4: Correrlas y ver el verde; medir [HUMANO en parte]**
Run: `uv run pytest tests/unit/test_medir_arranque.py tests/unit/test_manuales_s5.py
tests/unit/test_trazabilidad_s5.py tests/unit/test_meta_datos.py -v -W error`
(`test_meta_datos` y `uv run python scripts/meta_datos.py` vigilan que ningún documento presente
como real un dato construido) y `uv run ruff check scripts/medir_arranque.py tests/unit`.

Medición de RNF‑20 (cero deriva, desde la 0.6.0):
`uv run pytest tests/integration/test_migraciones.py -v -W error` (la CI lo corre en Linux y Windows
en cada PR) y `uv run python -m operacion revision`; se anota en `docs/plan_pruebas.md` §10 la
`head` de cada destino y cuántas revisiones lleva cada uno
(`git ls-files 'migraciones/*/versions/*.py'`), con la fecha y el commit.

Medición de RNF‑19 en el equipo de desarrollo (cinco valores y su mediana, ≤ 20 s):
`uv run python scripts/medir_arranque.py --tabla`; el bloque impreso se pega al final de
`docs/plan_pruebas.md` §10. Con el instalador ya instalado, se repite con
`--python "%LOCALAPPDATA%\Programs\Silice\python\python.exe" --cwd
"%LOCALAPPDATA%\Programs\Silice\codigo"`.
La huella de la clave: `uv run python -m operacion huella-clave-proyecto`, pegada en el manual.

- [ ] **Paso 5: Commit y PR**
```bash
git add docs scripts/medir_arranque.py README.md CHANGELOG.md tests/unit/test_manuales_s5.py
git commit -m "docs(manuales): manual de instalacion, RNF-19 y medicion de arranque" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
uv run python scripts/guardia_nucleo.py --base origin/main
git push -u origin inc/100-s5-5-manuales
gh pr create --base main --head inc/100-s5-5-manuales \
  --title "S5-5: manuales y medicion de arranque" --body-file -
```

---

### Tarea 20: `instalador/publicar.py`, la candidata, Med, `v1.0.0` y `v1.0-tesis` **[HUMANO]**

**Rama:** `inc/100-s5-5-cierre` (sale de `origin/main` con T18 y T19 fusionadas)
**Rol:** sf-lider-de-fase (con Eugenio)
**Archivos:**
- Crear: `instalador/publicar.py`
- Modificar: `pyproject.toml` (versión), `uv.lock`, `CHANGELOG.md`,
  `docs/bitacora/2026-10-silice-100.md`,
  `docs/plan_pruebas.md` (§10, resultados), `.github/workflows/ci.yml` (`--hasta S5-5` no: el CI
  se queda en S5-4; GS5 se evalúa en local, RP10-12)
- Prueba: `tests/unit/test_publicar.py`

**Interfaces:**
- Consume: `operacion.firma_sumas` (`formatear_sumas`, `parsear_sumas`, `verificar`; T3),
  `instalador.tamanos`, `operacion.version` (T4).
- Produce, en `instalador.publicar`: `reunir(carpetas: Sequence[Path], salida: Path) -> Path`
  (el `SHA256SUMS` único, solo LF), `comprobar_contra_ci(carpetas, sumas) -> list[str]`,
  `cambios_permitidos(archivos: Iterable[str]) -> list[str]` (lo que no puede cambiar entre una rc
  y `v1.0.0`), `main(argv)` con las órdenes `reunir`, `comprobar` y `cambios`.

- [ ] **Paso 1: Escribir la prueba que falla**

`tests/unit/test_publicar.py`:
```python
"""Reunir, comprobar y firmar el SHA256SUMS único del release (RP10-9; spec S5 §10.4)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from instalador import publicar
from operacion import firma_sumas


def _carpeta(base: Path, perfil: str, contenido: bytes, sufijo: str) -> Path:
    carpeta = base / perfil
    carpeta.mkdir()
    exe = carpeta / f"Silice-1.0.0{sufijo}.exe"
    exe.write_bytes(contenido)
    (carpeta / "manifiesto.json").write_bytes(b'{"formato": "silice-manifiesto"}')
    (carpeta / f"pip-audit-{perfil}.json").write_bytes(b"{}")
    sumas = carpeta / f"SHA256SUMS-{perfil}"
    entradas = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in carpeta.iterdir()}
    sumas.write_bytes(firma_sumas.formatear_sumas(entradas))
    return carpeta


@pytest.fixture
def carpetas(tmp_path: Path) -> list[Path]:
    return [
        _carpeta(tmp_path, "basico", b"basico" * 100, ""),
        _carpeta(tmp_path, "completo", b"completo" * 100, "-completo"),
    ]


def test_reunir_arma_un_solo_sha256sums_ordenado_y_solo_con_lf(carpetas, tmp_path: Path) -> None:
    salida = tmp_path / "release"
    sumas = publicar.reunir(carpetas, salida)
    crudo = sumas.read_bytes()
    assert sumas == salida / "SHA256SUMS" and b"\r" not in crudo and crudo.endswith(b"\n")
    lineas = crudo.decode().splitlines()
    nombres = [linea.split("  ", 1)[1] for linea in lineas]
    assert nombres == sorted(nombres)
    assert "Silice-1.0.0.exe" in nombres and "Silice-1.0.0-completo.exe" in nombres
    assert "pip-audit-basico.json" in nombres and "pip-audit-completo.json" in nombres
    assert nombres.count("manifiesto.json") == 1  # el mismo para los dos perfiles
    assert (salida / "Silice-1.0.0.exe").exists()  # los archivos se copian junto a las sumas


def test_dos_manifiestos_distintos_son_un_error(carpetas, tmp_path: Path) -> None:
    (carpetas[1] / "manifiesto.json").write_bytes(b"otro")
    with pytest.raises(ValueError, match="manifiesto.json"):
        publicar.reunir(carpetas, tmp_path / "release")


def test_comprobar_contra_ci_detecta_un_archivo_cambiado_en_el_camino(
    carpetas, tmp_path: Path
) -> None:
    assert publicar.comprobar_contra_ci(carpetas) == []
    (carpetas[0] / "Silice-1.0.0.exe").write_bytes(b"alterado")
    problemas = publicar.comprobar_contra_ci(carpetas)
    assert problemas and "Silice-1.0.0.exe" in problemas[0]


def test_el_sha256sums_reunido_se_firma_y_verifica(carpetas, tmp_path: Path) -> None:
    sumas = publicar.reunir(carpetas, tmp_path / "release")
    privada = Ed25519PrivateKey.generate()
    publica = firma_sumas.bytes_publicos(privada)
    firma = firma_sumas.firmar(sumas.read_bytes(), privada)
    exe = tmp_path / "release" / "Silice-1.0.0.exe"
    assert firma_sumas.verificar_instalador(exe, sumas.read_bytes(), firma, publica)[0] is True


def test_un_sha256sums_guardado_con_crlf_ya_no_verifica(carpetas, tmp_path: Path) -> None:
    sumas = publicar.reunir(carpetas, tmp_path / "release")
    privada = Ed25519PrivateKey.generate()
    publica = firma_sumas.bytes_publicos(privada)
    firma = firma_sumas.firmar(sumas.read_bytes(), privada)
    con_crlf = sumas.read_bytes().replace(b"\n", b"\r\n")
    exe = tmp_path / "release" / "Silice-1.0.0.exe"
    assert firma_sumas.verificar_instalador(exe, con_crlf, firma, publica)[0] is False


@pytest.mark.parametrize(
    ("archivos", "ofensores"),
    [
        (["pyproject.toml", "uv.lock", "CHANGELOG.md", "docs/plan_pruebas.md", "README.md"], []),
        (["docs/bitacora/2026-10-silice-100.md"], []),
        (["core/budget/persistencia.py"], ["core/budget/persistencia.py"]),
        (["ui/app.py", "pyproject.toml"], ["ui/app.py"]),
        (["instalador/silice.iss"], ["instalador/silice.iss"]),
    ],
)
def test_entre_la_rc_y_v1_0_0_solo_cambian_version_changelog_y_documentos(
    archivos, ofensores
) -> None:
    assert publicar.cambios_permitidos(archivos) == ofensores
```

- [ ] **Paso 2: Correrla y ver el rojo; commit**
Run: `uv run pytest tests/unit/test_publicar.py -v -W error`
Esperado: FAIL con `ImportError: cannot import name 'publicar' from 'instalador'`.
```bash
git add tests/unit/test_publicar.py
git commit -m "test(instalador): reunir sumas, firma de punta a punta y cambios rc-final (rojo)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 3: Implementación mínima**

`instalador/publicar.py`:
```python
"""Arma el release: un solo `SHA256SUMS` de ambos perfiles, listo para firmar (RP10-9).

    uv run python instalador/publicar.py reunir publicacion/basico publicacion/completo \\
        --salida publicacion/release
    uv run python instalador/publicar.py comprobar publicacion/basico publicacion/completo
    git diff --name-only v1.0.0-rc.1..HEAD | uv run python instalador/publicar.py cambios

`reunir` copia los artefactos de cada perfil (bajados con `gh run download`) a una carpeta, verifica
que el `manifiesto.json` sea el mismo y escribe `SHA256SUMS` (sha256sum, dos espacios, solo LF).
La firma la pone el controlador en su equipo: `python -m operacion firmar-sumas`.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion import firma_sumas  # noqa: E402

#: Lo único que puede cambiar entre `v1.0.0-rc.N` y `v1.0.0` (spec S5 §9.3, RP10-13).
PERMITIDOS = ("pyproject.toml", "uv.lock", "CHANGELOG.md", "README.md")
PREFIJOS_PERMITIDOS = ("docs/",)


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def cambios_permitidos(archivos: Iterable[str]) -> list[str]:
    """Los archivos cambiados que NO deberían haber cambiado entre la candidata y la final."""
    return sorted(
        a
        for a in (x.strip().replace("\\", "/") for x in archivos)
        if a
        if a not in PERMITIDOS and not a.startswith(PREFIJOS_PERMITIDOS)
    )


def reunir(carpetas: Sequence[Path], salida: Path) -> Path:
    salida.mkdir(parents=True, exist_ok=True)
    entradas: dict[str, str] = {}
    for carpeta in carpetas:
        for archivo in sorted(carpeta.iterdir()):
            if not archivo.is_file() or archivo.name.startswith("SHA256SUMS"):
                continue
            huella = _sha256(archivo)
            if archivo.name in entradas and entradas[archivo.name] != huella:
                raise ValueError(f"{archivo.name} es distinto en dos perfiles; no puede haber dos")
            entradas[archivo.name] = huella
            shutil.copyfile(archivo, salida / archivo.name)
    sumas = salida / "SHA256SUMS"
    sumas.write_bytes(firma_sumas.formatear_sumas(entradas))
    return sumas


def comprobar_contra_ci(carpetas: Sequence[Path]) -> list[str]:
    """Cada archivo bajado coincide con el `SHA256SUMS-<perfil>` que dejó la CI."""
    problemas = []
    for carpeta in carpetas:
        for sumas in carpeta.glob("SHA256SUMS-*"):
            for nombre, huella in firma_sumas.parsear_sumas(sumas.read_bytes()).items():
                archivo = carpeta / nombre
                if not archivo.is_file():
                    problemas.append(f"{carpeta.name}: falta {nombre}")
                elif _sha256(archivo) != huella:
                    problemas.append(f"{carpeta.name}: {nombre} no coincide con lo que dejó la CI")
    return problemas


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ordenes = analizador.add_subparsers(dest="orden", required=True)
    for nombre in ("reunir", "comprobar"):
        sub = ordenes.add_parser(nombre)
        sub.add_argument("carpetas", nargs="+", type=Path)
        if nombre == "reunir":
            sub.add_argument("--salida", type=Path, required=True)
    ordenes.add_parser("cambios")
    argumentos = analizador.parse_args(argv)
    if argumentos.orden == "cambios":
        ofensores = cambios_permitidos(sys.stdin.read().splitlines())
        print("\n".join(ofensores) or "solo cambian la versión, el CHANGELOG y los documentos")
        return 1 if ofensores else 0
    problemas = comprobar_contra_ci(argumentos.carpetas)
    if problemas:
        print("\n".join(problemas), file=sys.stderr)
        return 1
    if argumentos.orden == "reunir":
        print(reunir(argumentos.carpetas, argumentos.salida))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
(`firma_sumas.parsear_sumas(bytes) -> dict[str, str]`, `bytes_publicos(privada) -> bytes` y
`verificar_instalador(exe, sumas, firma, publica) -> tuple[bool, str]` son de T3.)

- [ ] **Paso 4: Correrla y ver el verde**
Run: `uv run pytest tests/unit/test_publicar.py -v -W error` y `uv run ruff check
instalador/publicar.py tests/unit/test_publicar.py`.

- [ ] **Paso 5: Commit** (ya con la prueba antes del código)
```bash
git add instalador/publicar.py
git commit -m "feat(instalador): publicar.py: SHA256SUMS unico y vigilancia de cambios" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Paso 6: La candidata `v1.0.0-rc.1`** (la hace el controlador; ninguna orden publica nada sin
  su visto bueno)

1. En la rama `inc/100-s5-5-cierre`: `pyproject.toml` → `version = "1.0.0rc1"`; `uv lock`
   (el candado guarda la versión del proyecto); en `CHANGELOG.md` las líneas de `[Sin publicar]`
   pasan a `## [1.0.0-rc.1] - AAAA-MM-DD`, con una sección por RF (RF‑97 a RF‑99), RNF‑19 y RNF‑20;
   `uv run python scripts/verificar_version.py --etiqueta v1.0.0-rc.1` → 0.
2. Suite completa, CI verde en Linux y Windows, y la meta **en local** (RP10-12):
   ```bash
   uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml
   uv run python scripts/medir_rnf11.py
   uv run python scripts/meta_silice.py --version 1.0.0 --hasta S5-5 --junit reporte-pruebas.xml
   ```
   Las filas `S5-M6`, `S5-M7` y `S5-M10` necesitan `gh` autenticado y un flujo verde del commit;
   `S5-M9`, la medición de arranque; `S5-CLAVE`, la clave y su huella en el manual;
   `S5-ETIQUETAS` queda en PENDIENTE hasta el último paso.
3. PR, fusión con `gh pr merge <n> --merge`, y la etiqueta (anotada, en `main`, en orden):
   ```bash
   git fetch origin && git checkout origin/main
   git tag -a v1.0.0-rc.1 -m "Silice 1.0.0-rc.1: candidata para Med"
   git push origin v1.0.0-rc.1      # dispara instalador.yml con los dos perfiles
   ```
4. Cuando el flujo esté verde: `gh run download <id> -n instalador-basico -D publicacion/basico`,
   igual con `instalador-completo` en `publicacion/completo`;
   `uv run python instalador/publicar.py comprobar publicacion/basico publicacion/completo` y
   `uv run python instalador/publicar.py reunir publicacion/basico publicacion/completo --salida
   publicacion/release`.

- [ ] **Paso 7: Firma y publicación [HUMANO: H1, H4]** (Eugenio, en su equipo; nunca un agente)
```powershell
uv run python -m operacion firmar-sumas publicacion\release\SHA256SUMS `
    --clave "$env:USERPROFILE\.silice-clave\clave_proyecto.enc"
# pide la contraseña de la clave; escribe publicacion\release\SHA256SUMS.ed25519
$r = 'publicacion\release'
uv run python -m operacion verificar-instalador $r\Silice-1.0.0-rc.1.exe `
    $r\SHA256SUMS $r\SHA256SUMS.ed25519
Copy-Item instalador\verificar_sumas.py publicacion\release\
gh release create v1.0.0-rc.1 --draft --prerelease --title "Sílice 1.0.0-rc.1" `
    (Get-ChildItem $r -File).FullName
```
El *release* queda en **borrador** hasta que Eugenio lo publique. El repositorio es privado: la
entrega a las empresas es el contenido de `publicacion\release\` por el canal que elija (USB,
correo), siempre con los tres archivos de verificación.

- [ ] **Paso 8: Prueba en limpio y Med [HUMANO: H3, H6]**
  1. **Cuenta estándar sin internet (RNF‑19):** en Windows 11 Home se crea una cuenta **estándar**
     nueva (Configuración → Cuentas → Otros usuarios), se desconecta la red, se instala
     `Silice-1.0.0-rc.1.exe` con esa cuenta, se abre «Sílice», se crea el primer administrador con
     el código y se actualiza instalando de nuevo. El procedimiento y su resultado van a la
     bitácora.
  2. **Equipo limpio (H3):** si Eugenio dispone de un segundo equipo o una máquina virtual (Windows
     11 Home no trae Sandbox ni Hyper‑V), se repite allí; es lo único que atrapa un redistribuible
     de Visual C++ ausente (spec §15). Si no hay, queda declarado como riesgo abierto en la
     bitácora y en la tesis.
  3. **Med** con las dos personas (CP‑07, indicador 3, RNF‑04, RNF‑13; PLAN_CIERRE.md): se mide
     sobre el instalador de la rc, no sobre el árbol de desarrollo. Si el tutor pide cambios de
     código, sale `v1.0.0-rc.2` (RP10-13) y se decide en la bitácora si se vuelve a medir.

- [ ] **Paso 9: `v1.0.0` y `v1.0-tesis`** (solo si no hubo cambios de código después de la rc)
```bash
# en una rama nueva desde origin/main: pyproject 1.0.0, uv lock, CHANGELOG [1.0.0] con su
# fecha y los resultados de Med
git diff --name-only v1.0.0-rc.1..HEAD | uv run python instalador/publicar.py cambios
# sale con 0 si solo cambian versión, candado, CHANGELOG y documentos
uv run python scripts/verificar_version.py --etiqueta v1.0.0
# PR, CI verde, fusión con merge commit; luego, sobre ese main:
git tag -a v1.0.0 -m "Silice 1.0.0: la candidata medida, sin cambios de codigo"
git tag -a v1.0-tesis v1.0.0^{} -m "Congelamiento de la tesis (F3): igual a v1.0.0"
git push origin v1.0.0 v1.0-tesis
```
Se vuelve a correr el flujo con la etiqueta `v1.0.0` (rebuild con la versión final), se repite el
Paso 6.4 y el Paso 7 para el release final (con la huella y la firma nuevas) y se repite a mano la
instalación rápida del Paso 8.1 con el instalador final.

### Compuerta GS5 = 1.0.0

- [ ] **CI verde** en Linux y Windows en el commit de `v1.0.0`, y `instalador.yml` verde en la
  etiqueta `v1.0.0` (los dos perfiles), con `pip-audit-*.json` sin vulnerabilidades abiertas.
- [ ] **Meta en OK**, en local: `uv run python scripts/meta_silice.py --version 1.0.0 --hasta S5-5
  --junit reporte-pruebas.xml`, **sin ninguna fila en PENDIENTE** (S5‑M6 en OK, sin excepción:
  maestro §6.3), incluidas `S5-CLAVE`, `S5-TRAZ` y `S5-ETIQUETAS`. Su salida literal va a la
  bitácora.
- [ ] **Regresión literal** (C5) y `core/contracts/` (C4) intactos: `git diff v0.5.0..HEAD` vacío
  sobre `ARCHIVOS_REGRESION`; `git diff origin/main --stat -- core/` vacío en cada rama de S5.
- [ ] **RNF‑19:** tamaños ≤ 150 MB / ≤ 650 MB en los artefactos de la CI; arranque ≤ 20 s con su
  cifra en plan_pruebas §10; instalación en cuenta estándar y sin internet hecha y anotada; el
  resultado del equipo limpio (o su declaración de riesgo) anotado.
- [ ] **RNF‑20:** `tests/integration/test_migraciones.py` en verde en Linux y Windows desde la
  0.6.0 hasta la 1.0.0; las bases de prueba de 0.5.0 a 0.9.0 con su ficha.
- [ ] **Clave del proyecto:** `operacion/clave_proyecto.pub` versionada; su huella en el manual de
  instalación y en la tesis; el release final lleva `SHA256SUMS` firmado y `verificar-instalador`
  lo acepta.
- [ ] **Etiquetas:** `v1.0.0-rc.1` … `v1.0.0` anotadas en `main`, en orden; `v1.0-tesis` apunta al
  commit de `v1.0.0` (`S5-ETIQUETAS`).
- [ ] **Encargos** (maestro §6.4), todos aprobados: requisitos, arquitectura, pruebas y calidad,
  verificador de hechos, **usabilidad** (manual de instalación probado por alguien que no lo
  escribió, instalador, pestaña Instalación) y **seguridad** (clave y firma, API, red local,
  registro, respaldos y restauración, tabla de amenazas de §10.4 con su estado real).
- [ ] **Pendientes de Eugenio** anotados con su valor por defecto: RS5‑3, RS5‑9, RS5‑13, pregunta 12
  (PDF de MaPreX), certificado de firma de código (H2) y el segundo equipo (H3).
- [ ] **Bitácora** `docs/bitacora/2026-10-silice-100.md` con cada compuerta, las cifras reales de
  tamaño y tiempo, los rulings `RP10-n` nuevos y los hallazgos.

## Foco de revisión

Condiciones que el spec implica y que ninguna prueba ejercitaba antes de este plan; cada una tiene
su prueba en la tarea dueña.

1. **Rutas con espacios y caracteres no ASCII** en lo que más se rompe: la regla del cortafuegos
   (`program=`), el `.iss` (UTF‑8 con BOM, o «Sílice» sale corrupto) y los parámetros del
   instalador. → Tarea 6: `test_ordenes_netsh_exactas` (con `C:\Prueba Sílice\Programa ñ`);
   Tarea 14: `test_el_iss_se_compila_desde_una_copia_con_bom_utf8`; Tarea 16: el paso 8 de
   `humo.ps1` crea la regla con la ruta real y comprueba el programa de la regla; Tarea 15:
   paso 4 a mano.
2. **Actualizar con Sílice en marcha:** el instalador debe detenerlo sin matar nada ajeno y los
   archivos bloqueados no deben dejar una mezcla de versiones. → Tarea 15:
   `test_se_detiene_silice_antes_de_copiar_y_al_desinstalar`; Tarea 7:
   `test_parar_mata_los_hijos_antes_que_el_lanzador`; Tarea 16: el paso 7 de
   `humo.ps1` actualiza con el servidor arriba.
3. **La IP de la red local cambió (DHCP):** arrancar en `127.0.0.1` con aviso, nunca en
   `0.0.0.0`. → Tarea 7: `test_la_ip_elegida_se_usa_solo_si_sigue_existiendo`,
   `test_ninguna_configuracion_produce_0_0_0_0`; Tarea 5:
   `test_red_local_con_direccion_invalida_se_apaga_y_avisa`.
4. **Un `servidor.json` viejo con un PID reutilizado por otro programa:** `parar` no mata nada si
   la salud no responde. → Tarea 7: `test_parar_no_mata_nada_si_la_salud_no_responde`.
5. **`SHA256SUMS` alterado sin querer** (otro fin de línea, editor que guarda con BOM): la firma
   falla aunque nadie haya cambiado un instalador, y el manual lo avisa. → Tarea 3:
   `test_sumas_con_crlf_no_verifican`; Tarea 20:
   `test_un_sha256sums_guardado_con_crlf_ya_no_verifica`;
   Tarea 19: el manual dice que no se abre ni se guarda.

## Discrepancias encontradas

1. **`civil` con `ifctester` (spec S5 §7.2) vs el extra `ifc` (RV-24, `pyproject.toml`).** El spec
   S5 mete `ifctester` en `civil`; el PR de dependencias lo dejó en un extra propio porque
   `bcf-client` es GPLv3. Se sigue el código: `ifc = false` en el manifiesto (RP10-4, H10).
2. **`[Run]` con `operacion migrar` (spec §7.3) vs `CurStepChanged(ssPostInstall)`.** `[Run]` no
   expone el código de salida: una migración fallida (7a) pasaría callada. Se migra desde `[Code]`,
   que sí lo lee y avisa; el efecto para quien instala es el mismo.
3. **three.js «servido» (spec §10.2) vs incrustado (RP10-5).** Servirlo pide `enableStaticServing`,
   una opción fuera de §10.1; incrustarlo no cambia ninguna opción y deja la misma garantía.
4. **`es_cliente_local` en `operacion.red` (spec S5) vs `es_local` en `seguridad.red` (S3 §5.6).**
   Dos funciones para lo mismo, con una diferencia que importa (la IP elegida). Gana la de S5
   (RP10-8) y una prueba impide que `ui` o `api` llamen a la de S3.
5. **Texto del aviso «sin cifrar»:** S3 §5.6 y S5 §8.2 lo redactan distinto. Vale el de S5
   (`red.AVISO_ACCESO`); la pantalla de acceso de S3 lo muestra con `ui.cliente`.
6. **Banderas de Python:** el spec dice `-E -s -B`; el plan agrega `-X utf8` (RP10-7).
7. **`/DPerfil=…` vs `/DCompleto`:** ISPP no garantiza cómo interpreta una cadena de la línea de
   órdenes; un símbolo sin valor (`#ifdef Completo`) no deja dudas. El `/DVersion` sigue siendo un
   valor y es lo único que solo la primera compilación real confirma (T15 paso 4).
8. **«`v1.0.0` es la rc medida, sin cambios de código» (spec §9.3):** cambia `pyproject.toml`
   (`1.0.0rc1` → `1.0.0`), así que el instalador final se reconstruye. Se acepta que cambien solo
   la versión, `uv.lock`, el CHANGELOG y los documentos; `publicar.py cambios` lo comprueba
   (RP10-13).
9. **«Flujo verde en una etiqueta de prueba» (spec §13, GS5-4):** una etiqueta debe coincidir con
   `pyproject.toml`, así que una de prueba exigiría subir la versión. Se sustituye por
   `workflow_dispatch`
   con `perfiles=ambos` y el disparo por etiqueta se estrena con `v1.0.0-rc.1` (RP10-14).
10. **`operacion/rutas.py` (spec §5.2):** el plan de la 0.6.0 puso las carpetas en `config.py`;
    `silice.toml` y las rutas de usuario se agregan ahí (sección B, discrepancia 2).
11. **`ARENIA_MODO_ENTREGA` (spec §8.1):** desde T0 es `SILICE_MODO_ENTREGA` (A1).
12. **Los 12 pasos de §11.2:** `humo.ps1` los agrupa porque el orden real manda (parar antes de
    copiar las bases viejas, la actualización con el servidor arriba, el muestreo hasta el final);
    todas las comprobaciones están.
13. **Atribución de commits:** el plan de la 0.6.0 usa `Claude Opus 5.5`; este usa la línea vigente
    de la sesión (`Claude Sonnet 5.5`).
14. **Inno Setup:** el spec cita 6.7.1 en el runner y 7.0.2 como última; el plan fija la rama 6 y
    `choco install innosetup --version 6.7.1` si falta.
15. **`{userpf}` = `%LOCALAPPDATA%\Programs` (spec §5.3, «se confirma en la prueba de humo»):** la
    prueba de humo instala con `/DIR`, así que no lo confirma; se confirma a mano en T15 paso 4
    (la carpeta que propone el asistente) y en la instalación en cuenta estándar de T20.
16. **«Salvo los manuales» (spec §7.1):** el manifiesto no incluye `docs/`; los manuales viajan como
    documentos del release, no dentro del programa.
17. **Primera instalación y firma:** quien instala por primera vez no tiene Sílice para correr
    `verificar-instalador`; se le da `verificar_sumas.py` y `uv run --with cryptography` (RP10-10).
    Es un límite declarado, no una solución completa.
18. **`st.context.ip_address`:** el spec lo deja «a confirmar»; si Streamlit 1.62 no lo da,
    `ui.cliente` trata la operación como local solo con la red apagada (A16).
19. **Cifras del spec que dependen de S5-0.3** (Python 3.13 autónomo, dependencias de S1/S3/S4):
    se miden en la Tarea 2 y completan §1.3; el recorte de §7.2 se decide ahí.
20. **`uv.lock` y la versión del proyecto:** subir `pyproject.toml` a `1.0.0rc1` exige regenerar
    `uv.lock` (CI usa `--locked`); el spec no lo menciona.
