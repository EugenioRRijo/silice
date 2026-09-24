# AREN.IA — recorrido guiado de la interfaz: fases U0 y U1

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Goal:** Dar a la interfaz una puerta de entrada y un camino: pantalla de Inicio, caso abierto
compartido por todas las pantallas, estado vacío que siembra sin poder destruir, menú en dos
secciones con nombres de oficio y un paso siguiente pintado por el marco; y dejar escrito y medible
el requisito nuevo RNF‑10 con su caso de prueba con persona, CP‑07.

> **Enmienda del 2026‑09‑24 (apertura de C3).** La fase U1 se ejecuta como fase **C3** del cierre
> de la tesis, en la rama `inc/cierre-C3` (spec de cierre §5 y §6). La Tarea 6 se hizo en C1
> (`9f6b72b` y `10e3a10`), salvo su paso 7, que queda decidido por D7 = (b): la base del worktree
> `prototipo` se declara base sucia de un worktree retirado y no se ejecuta nada sobre ella. La
> compuerta de U1 es **GU1a**; CP‑07 sale de la Tarea 13 hacia la fase **Med (GU1b)**. Las menciones
> de «GU1» y de `inc/PLAN-ui` en la fase U0 (Tareas 1 a 5) son históricas; los criterios vigentes
> de U1 son los enmendados abajo. Plan de la fase:
> [2026-09-24-cierre-c3-interfaz-scripts.md](2026-09-24-cierre-c3-interfaz-scripts.md).

**Architecture:** El código de `ui/` no modifica `core/`. En la fase C3, `core/` cambia solo por dos
commits propios: el de INV‑080 en `core/budget/` y el de INV‑015 7a (tabla `descarte_version` y
`descartar_version`). `api/` y `ml/` cambian solo en los commits de INV‑080 e INV‑081 del plan de
C3; `adapters/` no cambia (enmienda del 2026‑09‑24). Cuatro piezas en `ui/`:
`ui/recorridos.py` (los tres recorridos como datos puros), `ui/caso.py` (el caso abierto y el
recorrido activo sobre claves propias de `st.session_state`, y el estado del caso leído con la API
pública de `Catalogo`), `ui/paginas/inicio.py` (solo pinta) y `ui/app.py`, que pasa a ser
enrutador **y marco común**: pinta título, caso abierto, posición en el recorrido y botón «Siguiente»
alrededor de `pagina.run()`. Las páginas no importan `ui.app` (no hay ciclo) y dejan de pedir la
ruta de la base.

**Tech Stack:** Python 3.13 · Streamlit 1.62.0 (`st.navigation` con secciones, `AppTest`) ·
SQLAlchemy 2 · pytest (`-W error --strict-markers`) · ruff · uv

**Spec:**
[docs/superpowers/specs/2026-09-23-ui-recorrido-guiado-design.md](../specs/2026-09-23-ui-recorrido-guiado-design.md)
— aprobada por Eugenio el 2026‑09‑23. Las secciones citadas abajo (§3.2, §6…) son de ese documento.

**Plan de sesiones:** [PLAN_UI.md](../../../PLAN_UI.md) — lo crea la Tarea 1 de este documento.

---

## Global Constraints

- **Dependencia dura (cumplida):** el PR #7 está auditado y fusionado en `main` (`6fbb977`), y U1
  sale de `main` tras la fusión de C2 (`58ee828`), en `inc/cierre-C3` (enmienda del 2026‑09‑24).
  La fase U0 (Tareas 1 a 5) solo tocó documentos y `pyproject.toml`.
- **`core/`:** el criterio es el de la Tarea 18, paso 3, del
  [plan de C3](2026-09-24-cierre-c3-interfaz-scripts.md): `core/` cambia exactamente en dos commits
  propios (INV‑080 en `core/budget/` e INV‑015 7a), cada uno solo con `core/` y sus pruebas, con
  expediente previo y la línea base intacta; ninguna fusión cambia `core/` por su cuenta y no se
  agrega ningún archivo bajo `ml/` ni `adapters/` (enmienda del 2026‑09‑24).
- `tests/fixtures/apu_linea_base.py` **no se edita**.
  `tests/integration/test_composicion_extremo_a_extremo.py` y
  `tests/integration/test_auditoria_7_de_7.py` solo cambian por INV‑052 (se mueven ayudas), sin
  tocar ninguna aserción. La línea base sigue en 1 586,61 USD y la auditoría en 7 de 7.
- `scripts/seed_demo.py` no se mueve ni se renombra (§4 regla 6).
- `ui/composicion.py` no importa `ui.caso`, `streamlit` ni `pandas` (§4 regla 5; meta P7).
- Ningún módulo de `ui/` construye objetos de Streamlit al importarse (§4 regla 3).
- La interfaz **nunca** construye la opción de reinicio de `seed_demo`: el literal `--reiniciar` no
  aparece en ningún archivo de `ui/`, **ni en docstrings ni en comentarios** (lo vigila una prueba
  que lee el texto fuente; en prosa se dice «el flag de reinicio»).
- Suite verde con `uv run pytest -W error --strict-markers`, sin `filterwarnings` ni marcadores
  nuevos; `uv run ruff check .` limpio; CI verde en `ubuntu-latest` y `windows-latest`.
- Ninguna prueba escribe en `data/apu.db`: toda base de prueba vive en `tmp_path`.
- Los dos decimales de presentación salen de `core.verification.informe.DECIMALES_PRESENTACION`.
- Commits: Conventional Commits en español **sin tildes en el asunto**, terminados con
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- Límite de línea de ruff: 100 caracteres (`pyproject.toml:36`). Si una firma o un
  `parametrize` de este plan lo excede, se parte en varias líneas sin cambiar su contenido.
- Textos de interfaz nuevos **sin tildes**, como el resto de `ui/app.py` y de los rótulos actuales
  («Catalogo», «Actualizacion»). La corrección ortográfica de la interfaz entera es de U3.
- **Compuerta por sección** (regla vigente del 2026‑09‑23): al cerrar U0 y al cerrar U1 se despachan
  en paralelo y en segundo plano los cuatro encargos de ingeniería de sistemas —ingeniero de
  requisitos (IEEE 830, ERS), arquitecto de software (vistas 4+1, `CLAUDE.md` §2/§5/§9), ingeniero
  de pruebas y calidad (IEEE 829, ISO/IEC 25010) y verificador de hechos (cada cita `archivo:línea`)—
  y no se pasa a la fase siguiente mientras quede un hallazgo bloqueante.

## Review Focus

1. **La página por defecto devuelve `url_path == ""`.** Verificado en Streamlit 1.62.0
   (`streamlit/navigation/page.py:414`: `return "" if self._default else self._url_path`). El
   pseudocódigo de §3.3 pasaría `""` al paso siguiente y el Inicio nunca se reconocería. Se espera
   que el Inicio se identifique como `inicio` → `ruta_actual("")` lo traduce; prueba en la Tarea 10.
2. **Una ruta con errata, un directorio o un archivo que no es SQLite como caso.** Se espera que el
   estado lo diga sin crear ningún archivo ni lanzar traza. Pruebas en la Tarea 8
   (`test_estado_de_una_ruta_inexistente_no_crea_el_archivo`, `..._directorio_...`,
   `..._archivo_que_no_es_sqlite_...`).
3. **Modo entrega con un recorrido activo que apunte a Investigación.** `st.switch_page` recibiría
   una página no registrada y reventaría. Se espera que ningún paso de ningún recorrido apunte fuera
   de Trabajo. Prueba en la Tarea 7 (`test_ningun_paso_sale_de_la_seccion_trabajo`).
4. **El caso abierto se olvida al navegar** (clave de widget descartada, §3.2 invariante 1). Se
   espera que el caso sobreviva. Prueba en la Tarea 9: la clave propia queda fijada tras pulsar
   «Abrir este caso» y ningún widget del Inicio usa esa clave.
5. **«Abrir este caso» con el campo vacío.** Se espera un mensaje y el caso anterior intacto, no un
   caso `Path("")` que apunte al directorio actual. Prueba en la Tarea 9
   (`test_abrir_un_caso_vacio_avisa_y_conserva_el_anterior`).
6. **La posición en el recorrido que pinta la barra lateral** (RF‑41 ampliado en GU0) no tenía
   prueba en la versión original del plan: la trazabilidad por paso de §8.1 lo detectó. Prueba en
   la Tarea 11.

---

## Mapa de archivos

| Archivo | Tarea | Responsabilidad |
|---|---|---|
| `PLAN_UI.md` | 1 | Sesiones U0–U3 y compuertas; enlaza este documento |
| `pyproject.toml`, `uv.lock` | 1 | `streamlit>=1.36` |
| `docs/ERS.md` | 2 | UC‑12, RF‑36…RF‑43, actor nuevo, RNF‑10, enmienda de la reserva de RF‑32 |
| `docs/calidad_iso25010.md`, `docs/plan_pruebas.md`, `docs/dossier_g0.md` | 3 | RNF‑10; bloque B del anexo A; cifras fechadas |
| `docs/guion_prueba_arenia.md` | 4 | CP‑07 |
| `docs/bitacora/2026-09-23-sprint-ui.md` | 5, 13 | Bitácora del sprint y de sus compuertas |
| `tests/conftest.py` | 6, 8 | Salvaguarda de `data/apu.db` (Tarea 6: hecha en C1); entorno limpio de `ARENIA_CASO` (Tarea 8) |
| `ui/recorridos.py` + `tests/unit/test_ui_recorridos.py` | 7 | Los tres recorridos, puros |
| `ui/caso.py` + `tests/unit/test_ui_caso.py` | 8 | Caso abierto, recorrido activo, estado del caso |
| `ui/paginas/inicio.py` + `tests/unit/test_ui_inicio.py` | 9 | Pantalla de Inicio y estado vacío |
| `ui/app.py` + `tests/unit/test_ui_app.py` + `tests/unit/test_ui_importable.py` | 10 | Secciones, orden, inicio por defecto, marco |
| `ui/paginas/*.py` (las nueve) + `ui/elaboracion.py` + `ui/resultado.py` + `ui/composicion.py` + `tests/unit/test_ui_componer.py` + `tests/unit/test_ui_app.py` + `tests/unit/test_arquitectura.py` | 11 | Las pantallas leen el caso abierto; título y caso de uso los pinta el marco; extracción de INV‑043 (11b y 11c) |
| `docs/manual_usuario.md`, `docs/guion_prueba_arenia.md` | 12 | Nombres nuevos del menú; Inicio en la preparación |
| — | 13 | Compuerta GU1a; CP‑07 en Med (GU1b) |

---

# Fase U0 — Documentar (se ejecuta ya, en `inc/PLAN-ui`)

### Task 1: PLAN_UI.md y el mínimo de Streamlit

**Files:**
- Create: `PLAN_UI.md`
- Modify: `pyproject.toml:17`, `uv.lock` (regenerado)

**Interfaces:**
- Consumes: nada.
- Produces: `PLAN_UI.md` con los identificadores de sesión U0.1, U0.2, U1.1…U1.6, U2, U3 que citan
  las tareas siguientes y la bitácora.

- [ ] **Step 1: Crear `PLAN_UI.md`** con este contenido exacto:

```markdown
# PLAN_UI — recorrido guiado de la interfaz

Continúa a [PLAN_PROTOTIPO.md](PLAN_PROTOTIPO.md), que cerró 12 de 12 metas, y **no** reemplaza a
[PLAN_ASISTENTE.md](PLAN_ASISTENTE.md): el asistente con IA (UC‑09) sigue siendo otro plan.

**Diseño que lo fundamenta:**
[docs/superpowers/specs/2026-09-23-ui-recorrido-guiado-design.md](docs/superpowers/specs/2026-09-23-ui-recorrido-guiado-design.md).
**Plan detallado (tarea por tarea):**
[docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md](docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md).

**Por qué existe.** La interfaz tiene nueve pantallas que funcionan y ninguna puerta de entrada.
Frase de origen (Eugenio, 2026‑09‑22): «no sé qué hacer y no hay un camino para llevar al usuario de
la mano». Este plan no agrega capacidades: agrega **orientación**.

**Dependencia dura.** U1 no empieza hasta que el PR #7 esté auditado y fusionado en `main`.

## Sesiones

| Sesión | Contenido | Cierre |
|---|---|---|
| U0.1 | ERS: UC‑12, RF‑36…RF‑43, actor «usuario nuevo / evaluador», RNF‑10, enmienda de la reserva de RF‑32 | ERS sin contradicción interna |
| U0.2 | RNF‑10 en calidad y plan de pruebas; bloque B del anexo A; CP‑07 redactado antes de ejecutarse; `streamlit>=1.36` | **GU0** |
| U1.1 | Reasentar sobre `main`; salvaguarda de aislamiento de `data/apu.db` | salvaguarda observada en rojo y en verde |
| U1.2 | `ui/recorridos.py` y `ui/caso.py` | pruebas puras verdes |
| U1.3 | Pantalla de Inicio con estado vacío sembrable | `AppTest` verde |
| U1.4 | `ui/app.py`: dos secciones, Inicio por defecto, marco común | `AppTest` verde |
| U1.5 | Las nueve pantallas leen el caso abierto; título y caso de uso los pinta el marco | ninguna pantalla pide la ruta |
| U1.6 | Manual y guion al día; compuerta automatizada; CP‑07 con dos personas | **GU1** |
| U2 | Asistente de cinco pasos. **Solo si CP‑07 resulta FALLA**; su alcance lo fijan los puntos de detención registrados | GU2 |
| U3 | Pulido de navegación y redacción. **Requiere decisión expresa de Eugenio** | — |

## Compuertas

- **GU0:** requisitos escritos; CP‑07 redactado antes de ejecutarse; documentos sin contradicción
  interna; aprobación de los cuatro encargos de revisión.
- **GU1:** línea base en 1 586,61 USD y 7 de 7; suite verde en Windows y Linux; salvaguarda de
  aislamiento activa; `git diff --stat main -- core/` vacío; aprobación de los cuatro encargos;
  **CP‑07 ejecutado y registrado** (PASA o FALLA: ambos cierran GU1; FALLA abre U2).
- **GU2:** ídem GU1, más `ui/paginas/componer.py` sin cambios salvo extracción de fragmentos.

Cada compuerta se anota en [docs/bitacora/2026-09-23-sprint-ui.md](docs/bitacora/2026-09-23-sprint-ui.md).
```

- [ ] **Step 2: Subir el mínimo de Streamlit.** En `pyproject.toml:17` cambiar
  `ui = ["streamlit>=1.35"]` por `ui = ["streamlit>=1.36"]`.

- [ ] **Step 3: Regenerar el lock y comprobar que solo cambió la restricción**

Run: `uv lock && git diff --stat uv.lock && git diff uv.lock | grep -n "streamlit"`
Expected: `uv.lock` cambia en pocas líneas y la única que menciona `streamlit` como requisito dice
`specifier = ">=1.36"`; la versión resuelta sigue siendo `1.62.0`. Si `uv lock` resolviera otras
versiones, **detenerse** y revertir con `git checkout uv.lock pyproject.toml`: el cambio no debe
arrastrar actualizaciones.

- [ ] **Step 4: Comprobar que el entorno sigue sincronizando**

Run: `uv sync --locked --extra ui --extra api --extra civil && uv run python -c "import streamlit; print(streamlit.__version__)"`
Expected: `1.62.0`.

- [ ] **Step 5: Commit**

```bash
git add PLAN_UI.md pyproject.toml uv.lock
git commit -m "docs(plan): plan del recorrido guiado y streamlit minimo 1.36" -m "st.navigation y su diccionario de secciones aparecieron en 1.36.0; la restriccion 1.35 admitia una instalacion que no arranca." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: La ERS — UC‑12, RF‑36 a RF‑43, RNF‑10 y la enmienda de la reserva

**Files:**
- Modify: `docs/ERS.md` (diez lugares: nota de cabecera `:13-18`; tabla §2.2 `:85-96`; sección
  UC‑12 tras UC‑11, antes de `### 2.3` `:352`; tabla de actores §2.3 `:354-359`; §3.1 `:382-383`;
  párrafo de numeración §3.2 `:392-398`; tabla de RF tras la fila RF‑35 `:435`; tabla de cobertura
  `:458-460`; tabla de RNF tras RNF‑09 `:474`; matriz §4 tras UC‑11 `:497` y su párrafo RNF `:499-502`)

**Interfaces:**
- Consumes: `PLAN_UI.md` (Tarea 1).
- Produces: los identificadores UC‑12, RF‑36…RF‑43 y RNF‑10 que citan las Tareas 3, 4 y 12, y los
  nombres de archivo de prueba que crea U1: `tests/unit/test_ui_recorridos.py`,
  `tests/unit/test_ui_caso.py`, `tests/unit/test_ui_inicio.py`, `tests/unit/test_ui_app.py`.

- [ ] **Step 1: Nota de cabecera.** Tras el bloque citado que termina en `:18` («…para no colisionar
  con esa reserva.»), agregar como nueva línea del mismo bloque de cita:

```markdown
> **Extensión del sprint de UI (Sesión U0.1, compuerta GU0, [PLAN_UI.md](../PLAN_UI.md)):** se
> agregan UC‑12, los RF‑36 a RF‑43 —para un total de **42 RF**— y el requisito no funcional
> RNF‑10. **La reserva de UC‑09 queda reducida a RF‑32 solamente:** RF‑33 a RF‑35 ya los tomó
> UC‑10/UC‑11, de modo que la reserva de un rango contiguo estaba rota antes de este sprint. Los
> demás requisitos de UC‑09 continuarán desde el número libre más alto cuando se ejecute la Sesión
> A0.1 de [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md).
```

- [ ] **Step 2: Tabla §2.2.** Agregar tras la fila de UC‑11:

```markdown
| UC‑12 | Recorrer la aplicación guiado desde el Inicio | U0.1 (declarado), U1 |
```

- [ ] **Step 3: Sección UC‑12.** Insertar tras el bloque de UC‑11 (antes de `### 2.3`):

```markdown
#### UC‑12 — Recorrer la aplicación guiado desde el Inicio

- **Actor principal:** usuario nuevo / evaluador. **Actor secundario:** proyectista / estimador.
- **Precondiciones:** la aplicación está instalada y arrancada; el usuario no recibió explicación
  previa del sistema.
- **Flujo principal**
  1. El usuario abre la aplicación; el sistema muestra la pantalla de Inicio (RF‑36).
  2. El sistema muestra en la barra lateral, en solo lectura, el caso abierto y su estado (RF‑39).
  3. El usuario confirma el archivo del caso o abre otro; el sistema lo fija para toda la sesión y
     ninguna otra pantalla vuelve a pedirlo (RF‑38).
  4. El usuario elige uno de los tres recorridos declarados (RF‑37).
  5. En cada pantalla del recorrido, el sistema indica en qué paso está y ofrece el paso siguiente
     (RF‑41); el menú agrupa las pantallas por oficio y en el orden del trabajo (RF‑42).
  6. El usuario completa el último paso y obtiene el resultado del recorrido (por ejemplo, el
     presupuesto en Excel con su hoja de auditoría).
- **Flujos alternativos**
  - *1a. Modo entrega activo:* el menú omite la sección Investigación; ninguna pantalla de Trabajo
    queda inaccesible (RF‑43).
  - *3a. El caso no existe o no tiene partidas:* el sistema lo declara y ofrece cargar el caso de
    demostración; nunca ofrece reiniciar la base (RF‑40).
  - *3b. El archivo no se puede leer como base de datos:* el sistema lo informa con un mensaje, sin
    traza, y el usuario abre otro.
  - *5a. El usuario abre una pantalla que no pertenece al recorrido activo:* el sistema no muestra
    paso siguiente en ella (RF‑41).
- **Postcondiciones:** el usuario llegó al resultado del recorrido; la base solo cambió por las
  acciones que el propio usuario ejecutó (la siembra del paso 3a, guardar, elaborar).
```

- [ ] **Step 4: Tabla de actores §2.3.** Agregar la fila:

```markdown
| Usuario nuevo / evaluador | abre la aplicación por primera vez —tribunal, tutor o presupuestista recién llegado— y necesita orientarse sin formación previa | UC‑12 |
```

- [ ] **Step 5: §3.1.** Reemplazar la viñeta **Usuario** por:

```markdown
- **Usuario:** interfaz web local (Streamlit) con los once casos de uso declarados en este documento
  (UC‑01 a UC‑08 y UC‑10 a UC‑12; UC‑09 vacante, ver sección 2.2), con una pantalla de Inicio que
  lleva al usuario por recorridos guiados (UC‑12).
```

- [ ] **Step 6: Párrafo de numeración §3.2.** Reemplazar la frase que empieza en «**RF‑32 queda
  vacante**» y termina en «continúan en RF‑33.» por:

```markdown
**RF‑32 queda vacante**: [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md) (Sesión A0.1, aún no ejecutada)
lo reserva para UC‑09. Los RF de UC‑10 y UC‑11 (Sesión P0.1 de
[PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)) continuaron en RF‑33, y los de UC‑12 (Sesión U0.1 de
[PLAN_UI.md](../PLAN_UI.md)) en RF‑36. La reserva es **de RF‑32 solamente**: los demás requisitos
de UC‑09 tomarán el número libre más alto al ejecutarse A0.1.
```

- [ ] **Step 7: Tabla de RF.** Agregar tras la fila RF‑35:

```markdown
| RF‑36 | La interfaz abrirá en la pantalla de Inicio, cualquiera que sea el orden del resto del menú | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_app.py` — el Inicio es la página por defecto por identidad, no por posición, y la ruta vacía que Streamlit da a la página por defecto se traduce a `inicio` |
| RF‑37 | Los recorridos guiados se declararán una sola vez, en un módulo sin Streamlit ni base de datos, y el destino de cada paso será la ruta de una página registrada | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_recorridos.py` — integridad de enlaces: todo `paso.pagina` está en `{p.ruta_url for p in paginas_visibles(False)}` y en las visibles en modo entrega |
| RF‑38 | El archivo de la base se fijará una vez por sesión y todas las pantallas operarán sobre ese mismo caso; ninguna pantalla distinta del Inicio pedirá la ruta | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_caso.py` — resolución sesión → entorno → constante; `RUTA_BASE_POR_DEFECTO` definida una sola vez en `ui/`; `tests/unit/test_ui_app.py` — ninguna página salvo el Inicio pide la ruta |
| RF‑39 | El sistema mostrará en toda pantalla, en solo lectura, el caso abierto y su estado: existencia del archivo, número de partidas, número de insumos y si hay lista de precios vigente | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_caso.py` (estado sobre base inexistente, vacía, sembrada e ilegible) y `tests/unit/test_ui_app.py` (`AppTest`: el marco pinta el estado en cada una de las diez pantallas) |
| RF‑40 | Cuando el caso abierto no exista o no contenga partidas, el Inicio lo declarará y ofrecerá cargar el caso de demostración, sin exponer nunca la opción de reiniciar la base | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_inicio.py` (estado vacío, siembra, botón ausente con partidas) y `tests/unit/test_ui_caso.py` (el literal del flag de reinicio no aparece en ningún archivo de `ui/`) |
| RF‑41 | Cada pantalla del recorrido activo mostrará su paso siguiente, tomado de la declaración única de recorridos; una pantalla que no pertenezca a ningún recorrido no lo mostrará | Deseable | UC‑12 | U1 | pendiente: `tests/unit/test_ui_recorridos.py` (`paso_siguiente`) y `tests/unit/test_ui_app.py` (`AppTest`: botón «Siguiente» y su destino) |
| RF‑42 | El menú presentará cada pantalla con el nombre de su oficio, agrupada en dos secciones —Trabajo e Investigación— en el orden del trabajo real; el código del caso de uso permanecerá visible como subtítulo | Deseable | UC‑12 | U1 | pendiente: `tests/unit/test_ui_app.py` — secciones y orden sin Streamlit; ningún título lleva código de UC; `AppTest`: el subtítulo «Caso de uso …» en las cinco pantallas que tienen uno |
| RF‑43 | Con el modo entrega activo, ninguna pantalla de Trabajo quedará inaccesible | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_app.py` (la sección Trabajo es idéntica con y sin modo entrega) y `tests/unit/test_ui_recorridos.py` (ningún paso sale de Trabajo) |
```

- [ ] **Step 8: Tabla de cobertura.** Agregar la fila de UC‑12 antes de **Total**, y reemplazar la
  fila **Total**:

```markdown
| UC‑12 | RF‑36, RF‑37, RF‑38, RF‑39, RF‑40, RF‑41, RF‑42, RF‑43 | 8 (sin mínimo declarado; UC nuevo, Sesión U0.1) |
| **Total** | RF‑01 … RF‑31, RF‑33 … RF‑43 (RF‑32 vacante — reservado a UC‑09; RF‑03 traza a dos UC; RF‑33 y RF‑34 trazan a UC‑10 y UC‑11) | **42** |
```

- [ ] **Step 9: Tabla de RNF.** Agregar tras la fila de RNF‑09:

```markdown
| Usabilidad | RNF‑10 capacidad de aprendizaje de la interfaz: una persona que nunca vio la aplicación llega sola del Inicio a un presupuesto en Excel con su hoja de auditoría | caso con persona CP‑07 ([guion_prueba_arenia.md](guion_prueba_arenia.md)) y bloque B del anexo A de [dossier_g0.md](dossier_g0.md) | llega sin ayuda en ≤ 20 min, y el bloque B promedia ≥ 4,0 sin ningún ítem por debajo de 3; RNF‑04 es un requisito distinto y sigue pendiente |
```

- [ ] **Step 10: Matriz §4.** Agregar tras la fila de UC‑11:

```markdown
| UC‑12 | RF‑36, RF‑37, RF‑38, RF‑39, RF‑40, RF‑41, RF‑42, RF‑43 | pendientes: `tests/unit/test_ui_recorridos.py`, `tests/unit/test_ui_caso.py`, `tests/unit/test_ui_inicio.py`, `tests/unit/test_ui_app.py` (U1); CP‑07 para RNF‑10 | U0.1 (declarado), U1 ([PLAN_UI.md](../PLAN_UI.md)) | fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis); aporta la medición de usabilidad de [calidad_iso25010.md §4](calidad_iso25010.md) |
```

  Y en el párrafo «Correspondencia RNF → verificación», tras «RNF‑09 en la compuerta G1 (RF‑04).»,
  agregar: ` RNF‑10 con el caso con persona CP‑07, en la compuerta GU1 de [PLAN_UI.md](../PLAN_UI.md).`

- [ ] **Step 11: Comprobar que no queda ninguna cifra vieja del total**

Run: `grep -n "34 RF\|\*\*34\*\*\|diez casos de uso\|rango que arranca" docs/ERS.md`
Expected: solo la frase histórica de la nota de cabecera de P0.1 («para un total de **34 RF**»),
que describe esa sesión y se conserva; ninguna otra aparición.

- [ ] **Step 12: Commit**

```bash
git add docs/ERS.md
git commit -m "docs(ers): uc-12 recorrido guiado, rf-36 a rf-43 y rnf-10" -m "La reserva de UC-09 queda en RF-32 solamente: RF-33 a RF-35 ya los tomo el sprint del prototipo." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: RNF‑10 en calidad y en el plan de pruebas; bloque B del anexo A

**Files:**
- Modify: `docs/calidad_iso25010.md` (cabecera, §4 `:60-69`, fila «Usabilidad» de §9 `:129`)
- Modify: `docs/plan_pruebas.md` (§3 `:36-54`, §8 tras RF‑35 y su resumen `:158-160`, §9 `:173`)
- Modify: `docs/dossier_g0.md` (tras el anexo A, al final del archivo)

**Interfaces:**
- Consumes: RNF‑10, RF‑36…RF‑43 (Tarea 2).
- Produces: «bloque B» (ítems B1–B7) que cita CP‑07 en la Tarea 4.

- [ ] **Step 1: Fechar las cifras de `calidad_iso25010.md`.** Tras el título (línea 1) y su párrafo
  inicial, agregar:

```markdown
> **Nota de vigencia (2026‑09‑23).** Las cifras de pruebas de este documento son de su redacción
> (2026‑08‑31, 395 pruebas). [plan_pruebas.md §10](plan_pruebas.md) registra 479 (2026‑09‑14) y el
> cierre del sprint del prototipo, 673. Se actualizan todas juntas al cerrar la compuerta GU1 de
> [PLAN_UI.md](../PLAN_UI.md); hasta entonces, la fuente vigente del conteo es la última bitácora.
```

- [ ] **Step 2: §4 de calidad.** Cambiar el encabezado a `## 4. Usabilidad (RNF‑04 y RNF‑10)` y, tras
  el párrafo del veredicto de RNF‑04, agregar:

```markdown
**RNF‑10 — capacidad de aprendizaje de la interfaz** (sprint de UI, [PLAN_UI.md](../PLAN_UI.md)).
RNF‑04 pregunta por el **informe**; nada en él mide si la persona supo por dónde empezar, y siete de
sus ocho ítems no los puede contestar quien no llegó al informe. RNF‑10 mide ese tramo: una persona
que nunca vio la aplicación llega sola del Inicio a un presupuesto en Excel con su hoja de
auditoría. Instrumento: el caso con persona CP‑07 de [guion_prueba_arenia.md](guion_prueba_arenia.md)
y el **bloque B** del [anexo A del dossier](dossier_g0.md), con promedio propio que nunca se
mezcla con el del bloque A. Subcaracterísticas de ISO/IEC 25010 atacadas: reconocibilidad de la
adecuación, capacidad de aprendizaje y protección contra errores del usuario.

**Veredicto: pendiente de medición** (compuerta GU1). Con n = 1 por escenario, el resultado es un
dato, no una muestra, y así se cita.
```

- [ ] **Step 3: §9 de calidad.** Reemplazar la fila «Usabilidad» por:

```markdown
| Usabilidad | RNF‑04 Likert ≥ 4/5 sobre el informe; RNF‑10 CP‑07 sin ayuda en ≤ 20 min y bloque B ≥ 4,0 | RNF‑04: instrumento por aplicar (Fase 6); RNF‑10: CP‑07 por ejecutar (GU1) | pendiente |
```

- [ ] **Step 4: §3 de `plan_pruebas.md`.** En **A no probar**, tras la viñeta de RNF‑04, agregar:

```markdown
- **RNF‑10 (capacidad de aprendizaje de la interfaz):** no es automatizable; se mide con el caso con
  persona CP‑07 de [guion_prueba_arenia.md](guion_prueba_arenia.md) en la compuerta GU1 de
  [PLAN_UI.md](../PLAN_UI.md). Sus requisitos funcionales RF‑36 a RF‑43 **sí** tienen prueba
  automatizada (sección 8).
```

- [ ] **Step 5: §8 de `plan_pruebas.md`.** Agregar tras la fila RF‑35:

```markdown
| RF‑36 | `tests/unit/test_ui_app.py` (Inicio por defecto por identidad; ruta vacía → `inicio`) | — | pendiente (U1) |
| RF‑37 | `tests/unit/test_ui_recorridos.py` (integridad de enlaces con y sin modo entrega) | — | pendiente (U1) |
| RF‑38 | `tests/unit/test_ui_caso.py` (una sola ruta por defecto); `tests/unit/test_ui_app.py` (ninguna página salvo el Inicio pide la ruta) | — | pendiente (U1) |
| RF‑39 | `tests/unit/test_ui_caso.py`; `tests/unit/test_ui_app.py` (indicador en las diez pantallas) | — | pendiente (U1) |
| RF‑40 | `tests/unit/test_ui_inicio.py`; `tests/unit/test_ui_caso.py` (sin flag de reinicio en `ui/`) | — | pendiente (U1) |
| RF‑41 | `tests/unit/test_ui_recorridos.py`; `tests/unit/test_ui_app.py` (botón «Siguiente») | — | pendiente (U1) |
| RF‑42 | `tests/unit/test_ui_app.py` (secciones, orden, subtítulo de caso de uso) | — | pendiente (U1) |
| RF‑43 | `tests/unit/test_ui_app.py`; `tests/unit/test_ui_recorridos.py` | — | pendiente (U1) |
```

  Y reemplazar la primera frase del **Resumen** por: `**Resumen:** 33 de 34 RF anteriores al
  sprint de UI con prueba automatizada en verde; RF‑36 a RF‑43 declarados en U0 con su archivo de
  prueba nombrado y pendientes de U1.` (el resto del párrafo se conserva).

- [ ] **Step 6: §9 de `plan_pruebas.md`.** Agregar tras la fila de RNF‑09:

```markdown
| RNF‑10 aprendizaje de la interfaz | caso con persona CP‑07 ([guion_prueba_arenia.md](guion_prueba_arenia.md)), dos escenarios con personas distintas, bloque B del anexo A | pendiente (GU1) |
```

- [ ] **Step 7: Bloque B en `dossier_g0.md`.** Al final del archivo (tras el párrafo **Registro** del
  anexo A, que **no se toca**), agregar:

```markdown
### Bloque B. Recorrido de la interfaz (RNF‑10)

Agregado en la Sesión U0.2 de [PLAN_UI.md](../PLAN_UI.md). El cuestionario de arriba es el
**bloque A**: se conserva intacto y sigue siendo el instrumento de RNF‑04. El bloque B lo contesta
la persona que ejecutó el caso CP‑07 de [guion_prueba_arenia.md](guion_prueba_arenia.md), al
terminar y sin el observador mirando. **Su promedio es propio y nunca se promedia con el del
bloque A.** Misma escala: 1 = totalmente en desacuerdo · 3 = neutral · 5 = totalmente de acuerdo.

| # | Afirmación | Vigila | 1–5 |
|---|---|---|---|
| B1 | Al abrir la aplicación entendí para qué sirve y por dónde empezar | D‑1, D‑4 | |
| B2 | Los nombres del menú me dijeron qué hace cada pantalla sin abrirlas | D‑4 | |
| B3 | En todo momento supe sobre qué archivo de datos estaba trabajando | D‑2 | |
| B4 | Cuando no había datos, la aplicación me dijo qué pasaba y cómo salir | D‑3 | |
| B5 | Al terminar una pantalla supe cuál era el paso siguiente | D‑5 | |
| B6 | El orden de las pantallas se parece al orden en que se hace el trabajo | D‑6 | |
| B7 | Volvería a recorrer esto solo, sin que nadie me acompañara | global | |

Los códigos D‑1 a D‑6 son los defectos de orientación de la
[spec del recorrido guiado, §1](superpowers/specs/2026-09-23-ui-recorrido-guiado-design.md).
B4 solo se contesta en el escenario B de CP‑07 (base vacía); en el escenario A se anota «no aplica»
y el promedio se calcula sobre seis ítems.

Campo abierto: *¿en qué momento no supo qué hacer, y qué le habría ayudado?*

**Registro:** además de los ítems, **tiempo total** (min) y **número de preguntas al observador**;
promedio del bloque B, n, fecha, commit probado y escenario. El resultado se incorpora a
[calidad_iso25010.md §4](calidad_iso25010.md) como medición de RNF‑10.
```

- [ ] **Step 8: Commit**

```bash
git add docs/calidad_iso25010.md docs/plan_pruebas.md docs/dossier_g0.md
git commit -m "docs(calidad): rnf-10 con su instrumento, bloque b del anexo a" -m "RNF-04 queda intacto y pendiente; el bloque B tiene promedio propio y nunca se mezcla con el A." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: CP‑07 en el guion manual, redactado antes de ejecutarse

**Files:**
- Modify: `docs/guion_prueba_arenia.md` (§1 alcance `:9-16`, §6 tras CP‑06 `:348`, §7 `:350-359`)

**Interfaces:**
- Consumes: bloque B (Tarea 3); RF‑36…RF‑43, RNF‑10, UC‑12 (Tarea 2); variable de entorno
  `ARENIA_CASO` y rótulos de la interfaz que fija U1: menú «Inicio», botones «Abrir este caso»,
  «Cargar el caso de demostracion», «Siguiente: …», barra lateral «Caso abierto» (Tareas 8–10).
- Produces: CP‑07, que ejecuta la Tarea 13.

- [ ] **Step 1: §1.** Al final del alcance, agregar: `CP‑07 (sprint de UI, [PLAN_UI.md](../PLAN_UI.md))
  es de otra naturaleza: no lo ejecuta quien anota, sino una persona que nunca vio la aplicación,
  y mide RNF‑10.`

- [ ] **Step 2: §6.** Tras el bloque de CP‑06 (antes de `## 7.`), insertar:

```markdown
### CP‑07 — Una persona nueva llega sola del Inicio al Excel auditado

- **Objetivo:** medir si una persona que nunca vio la aplicación, sin explicación previa y sin que
  nadie la guíe, llega desde el Inicio hasta un presupuesto en Excel con su hoja de auditoría.
- **Trazabilidad:** UC‑12; RF‑36 a RF‑43; **RNF‑10**; compuerta GU1 de [PLAN_UI.md](../PLAN_UI.md).
- **Naturaleza:** caso con persona. Hay dos papeles: el **participante**, que usa la aplicación, y
  el **observador**, que prepara, lee la consigna, cronometra y anota. El observador no es
  participante.
- **Participantes:** dos personas distintas, una por escenario. Ninguna vio antes la aplicación ni
  sus documentos. Se anota su perfil, no su nombre: profesión, años de experiencia con
  presupuestos de obra, si ha usado aplicaciones web de datos.
- **Escenarios:**
  - **A — base sembrada:** mide el recorrido.
  - **B — base vacía:** mide además el estado vacío y la siembra desde la interfaz.

**Preparación (el observador, antes de que llegue el participante)**

1. Base **exclusiva** de la prueba, nunca `data/apu.db`. Escenario A:
   `uv run python scripts/seed_demo.py --db data/cp07/escenario_a.db`.
   Escenario B: compruebe que `data/cp07/escenario_b.db` **no** existe (bórrelo si quedó de una
   corrida anterior). Los `*.db` están ignorados por git.
2. Arranque la aplicación apuntando a esa base. En bash:
   `ARENIA_CASO=data/cp07/escenario_a.db uv run python -m streamlit run ui/app.py`;
   en PowerShell: `$env:ARENIA_CASO = "data/cp07/escenario_a.db"; uv run python -m streamlit run ui/app.py`
   (en el escenario B, `escenario_b.db`).
3. Compruebe que el navegador abrió en **Inicio** y que la barra lateral, bajo **Caso abierto**,
   nombra la base del escenario. Cierre toda otra pestaña.
4. Vacíe la carpeta de descargas del navegador, o anote su contenido para distinguir después el
   archivo nuevo.
5. Tenga a mano el cronómetro, esta hoja de registro y el bloque B del anexo A de
   [dossier_g0.md](dossier_g0.md), impreso.

**Consigna literal** — se lee tal cual, una sola vez, sin agregar nada:

> «Esta aplicación sirve para armar y auditar presupuestos de obra. Le pido que, sin ayuda,
> obtenga un presupuesto en Excel que incluya su auditoría y que, al terminar, me diga cuántos
> hallazgos tiene esa auditoría. Puede pensar en voz alta. Yo solo voy a observar y a tomar notas.»

**Guion del observador**

1. Ponga en marcha el cronómetro al terminar de leer la consigna.
2. **No conteste preguntas sobre la aplicación.** Respuesta fija a cualquier pregunta: «Haga lo que
   haría si yo no estuviera». Anote cada pregunta con su minuto: cuentan para el registro.
3. Anote cada **punto de detención**: 30 s o más sin una acción nueva, o una frase del tipo «no sé
   qué hacer». Registre minuto, pantalla y lo que dijo la persona. Son la entrada de U2 si el caso
   resulta FALLA.
4. **Qué cuenta como ayuda:** cualquier indicación sobre qué pulsar, adónde ir o qué significa un
   término, y cualquier gesto que confirme o niegue que va bien. Repetir la consigna literal **no**
   cuenta como ayuda.
5. **Oferta única de ayuda:** si pasan 3 minutos sin avanzar —sin cambiar de pantalla ni producir
   un resultado nuevo—, diga una sola vez: «¿Quiere que le ayude?». Si acepta, la sesión queda
   **asistida** y el veredicto ya es FALLA; se continúa hasta una condición de parada para registrar
   el resto. Si no acepta, no se vuelve a ofrecer.

**Condiciones de parada** (la primera que ocurra)

1. El participante alcanza el estado final (éxito).
2. Se cumplen **20 minutos**.
3. Pasan **5 minutos sin ninguna acción nueva** (abandono).
4. El participante declara que se rinde.
5. La aplicación muestra una traza de error o deja de responder: se registra como defecto con la
   pantalla y el texto visible.

**Estado final observable**

- En la carpeta de descargas existe `presupuesto_<codigo>.xlsx`; el observador lo abre al terminar
  y comprueba sus **cuatro hojas**, en este orden: *Presupuesto*, *APU*, *Curva* y *Auditoria*.
- El participante dice un número de hallazgos y ese número coincide con el que muestra el informe
  de auditoría en pantalla.
- Solo en el escenario B: la barra lateral, bajo **Caso abierto**, informa más de cero partidas.

**Al terminar:** el participante contesta a solas el **bloque B** del anexo A (en el escenario A,
B4 se marca «no aplica»). El observador no mira mientras lo contesta.

**Criterio de aceptación, declarado antes de ejecutar.** Un escenario **PASA** si y solo si: se
alcanzó el estado final **sin ayuda**; **dentro de los 20 minutos**; y el promedio del bloque B es
**≥ 4,0 sin ningún ítem por debajo de 3**. **FALLA** en cualquier otro caso, sin negociar. **CP‑07
PASA si y solo si pasan los dos escenarios.** Una FALLA no cancela el sprint: es el dato de la
tesis y la entrada de la fase U2, cuyo alcance lo fijan los puntos de detención.

Los umbrales de 20, 5 y 3 minutos **son decisiones de este caso, no medidas**: se declaran para que
el veredicto no dependa del criterio del observador, y se revisan con evidencia tras la primera
ejecución, dejando constancia en [docs/bitacora/](bitacora/).

**Hoja de registro** (una por escenario)

| Campo | Escenario A | Escenario B |
|---|---|---|
| Perfil del participante (sin nombre) | | |
| Fecha y hora de inicio | | |
| Commit probado (`git log -1 --oneline`) | | |
| Sistema operativo y navegador | | |
| Tiempo total (min) | | |
| Número de preguntas al observador | | |
| Oferta de ayuda: minuto · ¿aceptada? | | |
| Puntos de detención (minuto · pantalla · qué dijo) | | |
| Condición de parada (1–5) | | |
| Archivo obtenido y sus hojas | | |
| Hallazgos que dijo · hallazgos del informe | | |
| Partidas al terminar (solo B) | — | |
| Bloque B: B1 · B2 · B3 · B4 · B5 · B6 · B7 · promedio | | |
| Campo abierto | | |
| Veredicto del escenario | | |

**Veredicto de CP‑07:** ____ (PASA solo si ambos escenarios PASAN)
```

- [ ] **Step 3: §7.** Agregar a la tabla de trazabilidad:

```markdown
| CP‑07 | UC‑12 | RF‑36 a RF‑43 | RNF‑10; bloque B del anexo A de [dossier_g0.md](dossier_g0.md); compuerta GU1 |
```

- [ ] **Step 4: Commit**

```bash
git add docs/guion_prueba_arenia.md
git commit -m "docs(pruebas): cp-07 caso con persona para rnf-10, antes de ejecutarlo" -m "Consigna literal, guion del observador, cinco paradas, tope de 20 minutos y criterio declarado antes de medir." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Compuerta GU0

**Files:**
- Create: `docs/bitacora/2026-09-23-sprint-ui.md`

**Interfaces:**
- Consumes: Tareas 1 a 4.
- Produces: el veredicto de GU0, que habilita U1 (junto con la fusión del PR #7).

- [ ] **Step 1: Suite y lint siguen verdes** (U0 no toca código, pero sí `uv.lock`)

Run: `uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: todo verde; el número de pruebas es el mismo que antes de la Tarea 1.

- [ ] **Step 2: Despachar los cuatro encargos en paralelo y en segundo plano** (una llamada `Agent`
  por encargo, las cuatro en el mismo mensaje), todos sobre el mismo artefacto: `git diff
  bac1b48..HEAD` en `.claude/worktrees/ui` más la spec. Cada prompt incluye: el encargo y su norma
  (requisitos → IEEE 830 y la plantilla de `docs/ERS.md:391-392`; arquitectura → vistas 4+1 y
  `CLAUDE.md` §2/§5/§9; pruebas y calidad → IEEE 829, ISO/IEC 25010 y que CP‑07 sea ejecutable por
  un tercero sin preguntar nada; verificación factual → abrir cada cita `archivo:línea` y cada cifra
  y confirmarla), la instrucción de devolver **VEREDICTO** (aprueba / aprueba con correcciones /
  rechaza) y hallazgos con severidad (bloqueante / importante / menor), evidencia y corrección
  concreta, y la prohibición de editar archivos.

- [ ] **Step 3: Corregir cada hallazgo bloqueante** en un commit `docs(...)` propio por documento y
  volver a pasar **solo** el encargo que lo levantó. Repetir hasta que los cuatro aprueben.

- [ ] **Step 4: Crear la bitácora** `docs/bitacora/2026-09-23-sprint-ui.md` con: origen del sprint
  (la frase de Eugenio), enlace a la spec y a `PLAN_UI.md`, la tabla de veredictos de los cuatro
  encargos con el número de rondas, los hallazgos bloqueantes y su corrección, y la línea
  `**GU0: cruzada el <fecha>.** U1 espera la fusión del PR #7.`

- [ ] **Step 5: Commit**

```bash
git add docs/bitacora/2026-09-23-sprint-ui.md
git commit -m "docs(bitacora): compuerta gu0 del sprint de ui" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

# Fase U1 — Enfoque A (solo tras la fusión del PR #7)

### Task 6: Reasentar la rama y activar la salvaguarda de aislamiento (hecha en C1: 9f6b72b, 10e3a10; paso 7 decidido en C3: D7 = (b))

**Files:**
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: `main` con el PR #7 fusionado.
- Produces: fixture de sesión `_base_real_intacta` (autouse) y la constante `RUTA_BASE_REAL` en
  `tests/conftest.py`, que las Tareas 8 a 11 dan por activas.

- [x] **Step 1: Comprobar la integración con `main`.** La rama ya se integró con `main` por merge
  (`216acca`, 2026‑09‑23): el rebase chocaba commit a commit con las correcciones de la auditoría
  del PR #7 en ERS y plan de pruebas, y un merge los resolvió en una sola pasada. Comprobar:
  `git log --oneline -1 main` está contenido en la rama (`git merge-base --is-ancestor main HEAD`).

- [x] **Step 2: Estado de partida en verde**

Run: `uv sync --locked --all-extras && uv run pytest -W error --strict-markers -q`
Expected: verde; anotar el número de pruebas en la bitácora.

- [x] **Step 3: Escribir la salvaguarda.** Agregar a `tests/conftest.py`, tras los imports
  existentes (agregar `from pathlib import Path`):

```python
#: La base de trabajo del repositorio. Ninguna prueba puede crearla, borrarla ni escribir en ella:
#: el sprint del prototipo dejo `UI-01-TUB` dentro por una prueba de interfaz mal desviada
#: (hallazgo 5 de su bitacora de cierre), y una convencion escrita en docstrings no lo impidio.
RUTA_BASE_REAL = Path(__file__).resolve().parents[1] / "data" / "apu.db"


def _huella(ruta: Path) -> tuple[bool, int | None]:
    """Existencia y `mtime` en nanosegundos: cualquier escritura de SQLite cambia el segundo."""
    if not ruta.exists():
        return (False, None)
    return (True, ruta.stat().st_mtime_ns)


@pytest.fixture(scope="session", autouse=True)
def _base_real_intacta():
    """Falla la sesion entera si alguna prueba creo, borro o modifico `data/apu.db`."""
    antes = _huella(RUTA_BASE_REAL)
    yield
    despues = _huella(RUTA_BASE_REAL)
    if despues != antes:
        pytest.fail(
            f"la suite modifico {RUTA_BASE_REAL} (antes {antes}, despues {despues}): alguna prueba "
            "no desvio su base a tmp_path",
            pytrace=False,
        )
```

- [x] **Step 4: Ver la salvaguarda en rojo.** Crear un archivo desechable
  `tests/unit/test_zz_salvaguarda_desechable.py`:

```python
from tests.conftest import RUTA_BASE_REAL


def test_escribe_en_la_base_real():
    RUTA_BASE_REAL.parent.mkdir(parents=True, exist_ok=True)
    RUTA_BASE_REAL.touch()
```

Run: `uv run pytest tests/unit/test_zz_salvaguarda_desechable.py -q -p no:cacheprovider`
Expected: `1 passed, 1 error` con el mensaje «la suite modifico … data/apu.db».

- [x] **Step 5: Deshacer el experimento**

Run: `rm tests/unit/test_zz_salvaguarda_desechable.py` y, **solo si antes del paso 4
`data/apu.db` no existía en este worktree**, `rm data/apu.db`. Si existía, el `touch` cambió su
`mtime` pero no su contenido: no se borra.

- [x] **Step 6: La suite completa pasa con la salvaguarda**

Run: `uv run pytest -W error --strict-markers -q`
Expected: verde, mismo número de pruebas que en el paso 2. **Si falla por la salvaguarda**, es un
hallazgo real (una prueba existente escribe en `data/apu.db`): se identifica con
`uv run pytest -q -p no:randomly --setup-show` por bisección de archivos, se corrige esa prueba
para usar `tmp_path` y se anota en la bitácora. Nunca se relaja la salvaguarda.

- [x] **Step 7: Decidir `UI-01-TUB`.** La partida quedó en `.claude/worktrees/prototipo/data/apu.db`
  (archivo ignorado por git). Preguntar a Eugenio con `AskUserQuestion` entre: (a) regenerar esa
  base con `uv run python scripts/seed_demo.py --db .claude/worktrees/prototipo/data/apu.db
  --reiniciar` ejecutado **desde la raíz del repositorio**, o (b) dejarla y declararla en la
  bitácora como base sucia de un worktree retirado. No borrar nada sin su respuesta. Anotar la
  decisión en la bitácora.
  **Decidido en C3 (D7 = (b), Eugenio, 2026‑09‑24):** base sucia de un worktree retirado; no se
  ejecuta nada sobre ella (ni siembra, ni reinicio, ni borrado). Registrado en la sección «Fase C3»
  de `docs/bitacora/2026-09-23-cierre.md`.

- [x] **Step 8: Commit**

```bash
git add tests/conftest.py
git commit -m "test: salvaguarda que falla la sesion si una prueba toca data/apu.db" -m "Exigible antes de la primera prueba de U1 (spec de UI, seccion 6): centralizar la ruta del caso quita la costura que hoy desvia la base de cada pagina." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `ui/recorridos.py` — los tres recorridos como datos

**Files:**
- Create: `ui/recorridos.py`
- Test: `tests/unit/test_ui_recorridos.py`

**Interfaces:**
- Consumes: las rutas URL de las páginas, que son el nombre de su módulo (`DefinicionPagina.ruta_url`
  en `ui/app.py`): `inicio`, `catalogo`, `componer`, `elaborar`, `actualizacion`, `historico`,
  `escenarios`, `similares`, `simulador`, `visor`.
- Produces:
  - `RUTA_INICIO: str = "inicio"`
  - `Paso(titulo: str, pagina: str, que_hacer: str, senal_de_exito: str)` — frozen, slots
  - `Recorrido(nombre: str, proposito: str, pasos: tuple[Paso, ...])` — frozen, slots; método
    `posicion(ruta: str) -> int | None` (base 1)
  - `RECORRIDOS: tuple[Recorrido, ...]` — tres, en este orden: `NOMBRE_DEMOSTRACION`,
    `NOMBRE_PRESUPUESTO`, `NOMBRE_PRECIOS`
  - `recorrido_por_nombre(nombre: str | None) -> Recorrido | None`
  - `paso_siguiente(recorrido: Recorrido | None, ruta: str) -> Paso | None`

- [ ] **Step 1: Escribir las pruebas puras (sin la integridad de enlaces, que necesita `ui.app`
  nuevo y va en la Tarea 10)**

```python
"""Los recorridos guiados de la interfaz (sprint de UI, RF-37 y RF-41): datos puros, sin Streamlit."""

from __future__ import annotations

import dataclasses

import pytest

from ui.recorridos import (
    NOMBRE_DEMOSTRACION,
    NOMBRE_PRECIOS,
    NOMBRE_PRESUPUESTO,
    RECORRIDOS,
    RUTA_INICIO,
    Paso,
    Recorrido,
    paso_siguiente,
    recorrido_por_nombre,
)

PASO = Paso("Ver el catalogo", "catalogo", "Revise las partidas.", "Ve la tabla de partidas.")
OTRO = Paso("Componer", "componer", "Componga la partida.", "La partida queda guardada.")


def test_hay_tres_recorridos_en_el_orden_declarado() -> None:
    assert tuple(r.nombre for r in RECORRIDOS) == (
        NOMBRE_DEMOSTRACION,
        NOMBRE_PRESUPUESTO,
        NOMBRE_PRECIOS,
    )


def test_los_recorridos_son_inmutables() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        RECORRIDOS[0].nombre = "otro"  # type: ignore[misc]


def test_ningun_recorrido_pasa_por_el_inicio_ni_repite_pagina() -> None:
    for recorrido in RECORRIDOS:
        paginas = [paso.pagina for paso in recorrido.pasos]
        assert RUTA_INICIO not in paginas, recorrido.nombre
        assert len(set(paginas)) == len(paginas), recorrido.nombre


def test_ningun_texto_de_paso_queda_vacio() -> None:
    for recorrido in RECORRIDOS:
        assert recorrido.proposito.strip()
        for paso in recorrido.pasos:
            assert paso.titulo.strip() and paso.que_hacer.strip() and paso.senal_de_exito.strip()


def test_un_recorrido_sin_pasos_se_rechaza() -> None:
    with pytest.raises(ValueError, match="al menos un paso"):
        Recorrido("vacio", "nada", ())


def test_un_recorrido_que_repite_pagina_se_rechaza() -> None:
    with pytest.raises(ValueError, match="dos veces"):
        Recorrido("doble", "x", (PASO, PASO))


def test_un_recorrido_que_pasa_por_el_inicio_se_rechaza() -> None:
    en_inicio = dataclasses.replace(PASO, pagina=RUTA_INICIO)
    with pytest.raises(ValueError, match="Inicio"):
        Recorrido("inicio", "x", (en_inicio,))


def test_posicion_es_de_base_uno_y_none_fuera_del_recorrido() -> None:
    recorrido = Recorrido("r", "x", (PASO, OTRO))
    assert recorrido.posicion("catalogo") == 1
    assert recorrido.posicion("componer") == 2
    assert recorrido.posicion("visor") is None


def test_paso_siguiente_desde_el_inicio_es_el_primero() -> None:
    recorrido = Recorrido("r", "x", (PASO, OTRO))
    assert paso_siguiente(recorrido, RUTA_INICIO) == PASO


def test_paso_siguiente_avanza_y_se_detiene_en_el_ultimo() -> None:
    recorrido = Recorrido("r", "x", (PASO, OTRO))
    assert paso_siguiente(recorrido, "catalogo") == OTRO
    assert paso_siguiente(recorrido, "componer") is None


def test_una_pantalla_fuera_del_recorrido_no_tiene_paso_siguiente() -> None:
    recorrido = Recorrido("r", "x", (PASO, OTRO))
    assert paso_siguiente(recorrido, "visor") is None


def test_sin_recorrido_activo_no_hay_paso_siguiente() -> None:
    assert paso_siguiente(None, RUTA_INICIO) is None
    assert paso_siguiente(None, "catalogo") is None


def test_recorrido_por_nombre() -> None:
    assert recorrido_por_nombre(NOMBRE_PRECIOS) is RECORRIDOS[2]
    assert recorrido_por_nombre(None) is None
    assert recorrido_por_nombre("no existe") is None
```

- [ ] **Step 2: Ver el rojo**

Run: `uv run pytest tests/unit/test_ui_recorridos.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ui.recorridos'`.

- [ ] **Step 3: Implementar `ui/recorridos.py`**

```python
"""Los recorridos guiados de la interfaz (sprint de UI, RF-37 y RF-41).

Un recorrido es una secuencia de pasos con un proposito. Se declara aqui **una sola vez** y de esta
declaracion salen sus cuatro consumidores: la pantalla de Inicio que los ofrece, el marco de
`ui/app.py` que pinta en que paso esta el usuario y su boton «Siguiente», y el guion de prueba
manual CP-07 (`docs/guion_prueba_arenia.md`). Escribir el camino en cada pantalla seria repetirlo
cuatro veces (principio DRY, CLAUDE.md §2).

Sin Streamlit y sin base de datos: se prueba como funcion pura. La integridad de enlaces —que cada
`Paso.pagina` sea la ruta URL de una pagina registrada en `ui.app.PAGINAS`, y de una pagina de la
seccion Trabajo para que el modo entrega no la esconda— la vigila `tests/unit/test_ui_app.py`: este
modulo no importa `ui.app`, que si importa Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Ruta URL de la pantalla de Inicio (el nombre de su modulo, `ui/paginas/inicio.py`). El Inicio no
#: es un paso de ningun recorrido: es de donde salen todos.
RUTA_INICIO = "inicio"

NOMBRE_DEMOSTRACION = "Ver la demostracion auditada"
NOMBRE_PRESUPUESTO = "Armar un presupuesto"
NOMBRE_PRECIOS = "Actualizar precios"


@dataclass(frozen=True, slots=True)
class Paso:
    """Un paso: la pantalla donde ocurre, que hacer en ella y como se sabe que termino."""

    titulo: str
    pagina: str  # ruta URL de una pagina registrada en ui.app.PAGINAS
    que_hacer: str
    senal_de_exito: str


@dataclass(frozen=True, slots=True)
class Recorrido:
    """Una secuencia de pasos con un proposito, que no pasa dos veces por la misma pantalla."""

    nombre: str
    proposito: str
    pasos: tuple[Paso, ...]

    def __post_init__(self) -> None:
        if not self.pasos:
            raise ValueError(f"el recorrido {self.nombre!r} debe tener al menos un paso")
        paginas = [paso.pagina for paso in self.pasos]
        if RUTA_INICIO in paginas:
            raise ValueError(
                f"el recorrido {self.nombre!r} no puede tener un paso en el Inicio: sale de el"
            )
        if len(set(paginas)) != len(paginas):
            raise ValueError(
                f"el recorrido {self.nombre!r} pasa dos veces por la misma pantalla: el paso "
                "siguiente seria ambiguo"
            )

    def posicion(self, ruta: str) -> int | None:
        """Numero del paso (desde 1) que ocurre en la pantalla `ruta`; `None` si no es del recorrido."""
        for numero, paso in enumerate(self.pasos, start=1):
            if paso.pagina == ruta:
                return numero
        return None


RECORRIDOS: tuple[Recorrido, ...] = (
    Recorrido(
        NOMBRE_DEMOSTRACION,
        "Para un primer contacto: recorre el caso de demostracion ya cargado hasta el informe de "
        "auditoria y el presupuesto en Excel.",
        (
            Paso(
                "Ver el catalogo del caso",
                "catalogo",
                "Revise las partidas DEMO-01-INST, DEMO-02-VALV y DEMO-03-PRUEBA y los precios "
                "vigentes de sus insumos.",
                "La tabla de partidas muestra las tres partidas DEMO.",
            ),
            Paso(
                "Elaborar, auditar y exportar",
                "componer",
                "Baje a «Cantidades de obra», agregue una fila por partida con su cantidad y su "
                "origen, pulse «Elaborar y auditar» y despues «Exportar a Excel».",
                "Se descarga presupuesto_<codigo>.xlsx y el informe de auditoria dice cuantos "
                "hallazgos tiene.",
            ),
        ),
    ),
    Recorrido(
        NOMBRE_PRESUPUESTO,
        "Para quien presupuesta: compone las partidas que falten y elabora su propio "
        "presupuesto auditado desde un computo.",
        (
            Paso(
                "Ver que partidas hay",
                "catalogo",
                "Compruebe que partidas e insumos ya existen en el caso abierto.",
                "Sabe que partidas tendra que componer.",
            ),
            Paso(
                "Componer las partidas que falten",
                "componer",
                "Declare la cabecera, las tres tablas de insumos y el rendimiento con sus "
                "condiciones; pulse «Guardar composicion».",
                "La partida guardada aparece en el catalogo con su precio unitario.",
            ),
            Paso(
                "Elaborar el presupuesto",
                "elaborar",
                "Elija el dominio, cargue su computo en CSV, pulse «Extraer computo» y despues "
                "«Elaborar presupuesto»; descargue el Excel.",
                "Se descarga el libro con su hoja de auditoria.",
            ),
        ),
    ),
    Recorrido(
        NOMBRE_PRECIOS,
        "Para quien mantiene el catalogo: carga una lista de precios nueva, revalora un "
        "presupuesto guardado y revisa el comparativo.",
        (
            Paso(
                "Ver los precios vigentes",
                "catalogo",
                "Revise los insumos y su precio vigente antes de cambiarlos.",
                "Sabe que precios va a reemplazar.",
            ),
            Paso(
                "Cargar la lista y revalorar",
                "actualizacion",
                "Cargue la lista nueva (CSV o XLSX con columnas tipo, insumo, unidad y precio) y "
                "pulse «Revalorar presupuesto».",
                "Aparecen el comparativo por partida y la auditoria de la version nueva.",
            ),
        ),
    ),
)


def recorrido_por_nombre(nombre: str | None) -> Recorrido | None:
    """El recorrido de ese nombre; `None` si no hay nombre o no corresponde a ninguno."""
    for recorrido in RECORRIDOS:
        if recorrido.nombre == nombre:
            return recorrido
    return None


def paso_siguiente(recorrido: Recorrido | None, ruta: str) -> Paso | None:
    """El paso que sigue a la pantalla `ruta` dentro de `recorrido`.

    Desde el Inicio, el primero. Desde el ultimo paso, o desde una pantalla que no es del
    recorrido, ninguno (RF-41): una pantalla ajena al recorrido no ofrece paso siguiente.
    """
    if recorrido is None:
        return None
    if ruta == RUTA_INICIO:
        return recorrido.pasos[0]
    posicion = recorrido.posicion(ruta)
    if posicion is None or posicion == len(recorrido.pasos):
        return None
    return recorrido.pasos[posicion]
```

- [ ] **Step 4: Ver el verde**

Run: `uv run pytest tests/unit/test_ui_recorridos.py -q -W error && uv run ruff check ui/recorridos.py tests/unit/test_ui_recorridos.py`
Expected: 13 passed; ruff limpio.

- [ ] **Step 5: Commit**

```bash
git add ui/recorridos.py tests/unit/test_ui_recorridos.py
git commit -m "feat(ui): los tres recorridos guiados como datos puros" -m "RF-37 y RF-41: una sola declaracion de la que salen el Inicio, el marco y el guion CP-07." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: `ui/caso.py` — el caso abierto, el recorrido activo y el estado del caso

**Files:**
- Create: `ui/caso.py`
- Test: `tests/unit/test_ui_caso.py`
- Modify: `tests/conftest.py` (fixture que limpia `ARENIA_CASO`)

**Interfaces:**
- Consumes: `core.catalog` (`Catalogo`, `CatalogoIncompleto`, `abrir_sesion`, `crear_esquema`,
  `crear_motor`); `scripts.seed.sembrar(sesion)` solo en las pruebas.
- Produces:
  - `RUTA_BASE_POR_DEFECTO = "data/apu.db"` — **la única definición en `ui/`**, parchable
  - `VARIABLE_RUTA_CASO = "ARENIA_CASO"`, `CLAVE_CASO = "arenia_caso_ruta"`,
    `CLAVE_RECORRIDO = "arenia_recorrido_activo"` — claves propias, nunca de widget
  - `resolver_ruta(guardada: str | None, entorno: Mapping[str, str], por_defecto: str) -> Path` — pura
  - `ruta_caso() -> Path`; `fijar_caso(ruta: Path | str) -> None` (`ValueError` si vacía)
  - `recorrido_activo() -> str | None`; `fijar_recorrido(nombre: str | None) -> None`
  - `EstadoCaso(ruta: Path, existe: bool, partidas: int = 0, insumos: int = 0,
    lista_vigente: str | None = None, error: str | None = None)` con propiedad `vacio: bool`
  - `estado_caso(ruta: Path) -> EstadoCaso`
  - `resumen_caso(estado: EstadoCaso) -> str`
  - `argv_siembra(ruta: Path) -> list[str]`

- [ ] **Step 1: Escribir las pruebas**

```python
"""El caso abierto de la interfaz (sprint de UI, RF-38, RF-39 y RF-40).

Toda base de este archivo vive en `tmp_path`; la salvaguarda de `tests/conftest.py` falla la
sesion si alguna toca `data/apu.db`.
"""

from __future__ import annotations

from pathlib import Path

from core.catalog import abrir_sesion, crear_esquema, crear_motor
from scripts.seed import sembrar
from tests.fixtures.apu_linea_base import APUS_LINEA_BASE
from ui.caso import (
    RUTA_BASE_POR_DEFECTO,
    VARIABLE_RUTA_CASO,
    EstadoCaso,
    argv_siembra,
    estado_caso,
    resolver_ruta,
    resumen_caso,
)

RAIZ = Path(__file__).resolve().parents[2]


def _base_sembrada(ruta: Path) -> Path:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta


# --- resolucion de la ruta (RF-38) ------------------------------------------------------------


def test_la_ruta_guardada_en_la_sesion_manda() -> None:
    entorno = {VARIABLE_RUTA_CASO: "entorno.db"}
    assert resolver_ruta("sesion.db", entorno, "defecto.db") == Path("sesion.db")


def test_sin_ruta_en_la_sesion_manda_la_variable_de_entorno() -> None:
    entorno = {VARIABLE_RUTA_CASO: "entorno.db"}
    assert resolver_ruta(None, entorno, "defecto.db") == Path("entorno.db")


def test_una_variable_de_entorno_vacia_no_cuenta() -> None:
    assert resolver_ruta(None, {VARIABLE_RUTA_CASO: "  "}, "defecto.db") == Path("defecto.db")


def test_sin_sesion_ni_entorno_queda_la_ruta_por_defecto() -> None:
    assert resolver_ruta(None, {}, RUTA_BASE_POR_DEFECTO) == Path("data/apu.db")


# --- estado del caso (RF-39) ------------------------------------------------------------------


def test_estado_de_una_ruta_inexistente_no_crea_el_archivo(tmp_path: Path) -> None:
    ruta = tmp_path / "con_errata" / "apu.db"
    estado = estado_caso(ruta)
    assert estado == EstadoCaso(ruta=ruta, existe=False)
    assert estado.vacio
    assert not ruta.exists()
    assert not ruta.parent.exists()


def test_estado_de_una_base_vacia(tmp_path: Path) -> None:
    ruta = tmp_path / "vacia.db"
    ruta.touch()
    estado = estado_caso(ruta)
    assert (estado.existe, estado.partidas, estado.insumos, estado.lista_vigente) == (
        True,
        0,
        0,
        None,
    )
    assert estado.error is None
    assert estado.vacio


def test_estado_de_una_base_sembrada(tmp_path: Path) -> None:
    estado = estado_caso(_base_sembrada(tmp_path / "sembrada.db"))
    assert estado.existe and estado.error is None
    assert estado.partidas == len(APUS_LINEA_BASE)
    assert estado.insumos > 0
    assert estado.lista_vigente
    assert not estado.vacio


def test_estado_de_un_directorio_es_un_error_sin_traza(tmp_path: Path) -> None:
    estado = estado_caso(tmp_path)
    assert estado.existe
    assert estado.error
    assert not estado.vacio


def test_estado_de_un_archivo_que_no_es_sqlite_es_un_error_sin_traza(tmp_path: Path) -> None:
    ruta = tmp_path / "notas.db"
    ruta.write_text("esto no es una base de datos\n" * 20, encoding="utf-8")
    estado = estado_caso(ruta)
    assert estado.error
    assert ruta.read_text(encoding="utf-8").startswith("esto no es")


def test_resumen_de_cada_estado(tmp_path: Path) -> None:
    ruta = tmp_path / "x.db"
    assert resumen_caso(EstadoCaso(ruta, existe=False)) == "El archivo no existe todavia."
    assert (
        resumen_caso(EstadoCaso(ruta, existe=True, error="file is not a database"))
        == "No se pudo leer: file is not a database"
    )
    assert (
        resumen_caso(EstadoCaso(ruta, True, partidas=5, insumos=12, lista_vigente="Lista A"))
        == "5 partidas · 12 insumos · lista vigente: Lista A"
    )
    assert (
        resumen_caso(EstadoCaso(ruta, True, partidas=0, insumos=0))
        == "0 partidas · 0 insumos · lista vigente: ninguna"
    )


# --- la siembra no puede destruir (RF-40) -----------------------------------------------------


def test_la_siembra_apunta_al_caso_y_no_reinicia(tmp_path: Path) -> None:
    ruta = tmp_path / "caso.db"
    argv = argv_siembra(ruta)
    assert argv == ["--db", str(ruta)]
    assert "--reiniciar" not in argv


def test_ningun_archivo_de_ui_contiene_el_flag_de_reinicio() -> None:
    con_flag = [
        archivo.relative_to(RAIZ).as_posix()
        for archivo in sorted((RAIZ / "ui").rglob("*.py"))
        if "--reiniciar" in archivo.read_text(encoding="utf-8")
    ]
    assert con_flag == []
```

- [ ] **Step 2: Ver el rojo**

Run: `uv run pytest tests/unit/test_ui_caso.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ui.caso'`.

- [ ] **Step 3: Implementar `ui/caso.py`**

```python
"""El caso abierto de la sesion y el recorrido activo (sprint de UI, RF-38 a RF-40).

El archivo de la base se fija una vez por sesion y todas las pantallas operan sobre el: ninguna,
salvo el Inicio, vuelve a pedir la ruta. Antes de este modulo cada pantalla tenia su caja de texto
y su propia copia de `RUTA_BASE_POR_DEFECTO` (ocho copias); esta es la unica.

Tres invariantes (spec de UI, §3.2):

1. **Claves propias de `st.session_state`, nunca de widget.** Streamlit descarta las entradas de los
   widgets que no se vuelven a montar: si el caso abierto viviera en la clave de la caja de texto
   del Inicio, se olvidaria al navegar a otra pantalla. Por eso `CLAVE_CASO` y `CLAVE_RECORRIDO` no
   son la `key` de ningun widget.
2. **Respaldo declarado.** Se puede entrar por URL a cualquier pantalla sin pasar por el Inicio. Sin
   caso fijado, manda la variable de entorno `ARENIA_CASO` (el guion CP-07 la usa) y, si no esta,
   `RUTA_BASE_POR_DEFECTO`. `ruta_caso()` lee esa constante **al llamarse**, no al definirse: las
   pruebas la parchan en el objeto modulo de `sys.modules`.
3. **El motor de SQLAlchemy no va a la sesion.** Cada pantalla lo crea y lo cierra con
   `motor.dispose()`: en Windows no se puede borrar un archivo con un motor abierto.

`estado_caso` comprueba si el archivo existe **antes** de crear el esquema: `crear_esquema` sobre
una ruta con una errata crearia una base vacia en silencio. La siembra desde la interfaz nunca
construye el flag de reinicio de `scripts/seed_demo.py`, que borra la base entera.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_esquema, crear_motor

RUTA_BASE_POR_DEFECTO = "data/apu.db"
VARIABLE_RUTA_CASO = "ARENIA_CASO"
CLAVE_CASO = "arenia_caso_ruta"
CLAVE_RECORRIDO = "arenia_recorrido_activo"


def resolver_ruta(guardada: str | None, entorno: Mapping[str, str], por_defecto: str) -> Path:
    """La ruta del caso: la fijada en la sesion; si no, la del entorno; si no, la por defecto."""
    if guardada:
        return Path(guardada)
    del_entorno = entorno.get(VARIABLE_RUTA_CASO, "").strip()
    return Path(del_entorno or por_defecto)


def ruta_caso() -> Path:
    """La ruta del caso abierto en esta sesion."""
    return resolver_ruta(st.session_state.get(CLAVE_CASO), os.environ, RUTA_BASE_POR_DEFECTO)


def fijar_caso(ruta: Path | str) -> None:
    """Fija el caso abierto para toda la sesion. `ValueError` si la ruta queda vacia."""
    texto = str(ruta).strip()
    if not texto:
        raise ValueError("Escriba la ruta del archivo del caso: no puede quedar vacia.")
    st.session_state[CLAVE_CASO] = texto


def recorrido_activo() -> str | None:
    """El nombre del recorrido elegido en el Inicio, o `None` si no se eligio ninguno."""
    return st.session_state.get(CLAVE_RECORRIDO)


def fijar_recorrido(nombre: str | None) -> None:
    """Fija (o, con `None`, suelta) el recorrido activo de la sesion."""
    st.session_state[CLAVE_RECORRIDO] = nombre


@dataclass(frozen=True, slots=True)
class EstadoCaso:
    """Lo que el marco muestra del caso abierto (RF-39)."""

    ruta: Path
    existe: bool
    partidas: int = 0
    insumos: int = 0
    lista_vigente: str | None = None
    error: str | None = None

    @property
    def vacio(self) -> bool:
        """Legible y sin partidas: incluye el archivo que todavia no existe (RF-40)."""
        return self.error is None and self.partidas == 0


def estado_caso(ruta: Path) -> EstadoCaso:
    """El estado del caso en `ruta`, sin crear el archivo si no existe."""
    if not ruta.exists():
        return EstadoCaso(ruta=ruta, existe=False)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            try:
                lista: str | None = catalogo.lista_vigente().nombre
            except CatalogoIncompleto:
                lista = None
            return EstadoCaso(
                ruta=ruta,
                existe=True,
                partidas=len(catalogo.partidas()),
                insumos=len(catalogo.insumos()),
                lista_vigente=lista,
            )
    except SQLAlchemyError as error:
        # `orig` (el mensaje de SQLite, sin la sentencia SQL) solo existe en `DBAPIError`.
        return EstadoCaso(ruta=ruta, existe=True, error=str(getattr(error, "orig", None) or error))
    finally:
        motor.dispose()


def resumen_caso(estado: EstadoCaso) -> str:
    """Una linea con el estado del caso, para la barra lateral."""
    if estado.error is not None:
        return f"No se pudo leer: {estado.error}"
    if not estado.existe:
        return "El archivo no existe todavia."
    return (
        f"{estado.partidas} partidas · {estado.insumos} insumos · "
        f"lista vigente: {estado.lista_vigente or 'ninguna'}"
    )


def argv_siembra(ruta: Path) -> list[str]:
    """Argumentos de `scripts.seed_demo.main` para sembrar el caso: nunca el flag de reinicio."""
    return ["--db", str(ruta)]
```

  La prueba de que `RUTA_BASE_POR_DEFECTO` se define una sola vez en `ui/` **no** va en esta tarea:
  las nueve pantallas conservan su copia hasta la Tarea 11, que la agrega.

- [ ] **Step 4: Entorno limpio en toda la suite.** Agregar a `tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def _sin_caso_del_entorno(monkeypatch):
    """Una `ARENIA_CASO` exportada en la terminal de quien corre la suite no debe desviar pruebas."""
    monkeypatch.delenv("ARENIA_CASO", raising=False)
```

  (El literal repite `ui.caso.VARIABLE_RUTA_CASO` a propósito: importar `ui.caso` desde
  `conftest.py` metería Streamlit en el arranque de toda la suite. `test_ui_caso.py` ya fija el
  valor de la constante con `resolver_ruta`.)

- [ ] **Step 5: Ver el verde**

Run: `uv run pytest tests/unit/test_ui_caso.py -q -W error && uv run ruff check ui/caso.py tests/unit/test_ui_caso.py tests/conftest.py`
Expected: 12 passed; ruff limpio.

- [ ] **Step 6: Commit**

```bash
git add ui/caso.py tests/unit/test_ui_caso.py tests/conftest.py
git commit -m "feat(ui): caso abierto unico por sesion y su estado" -m "RF-38 a RF-40: una sola RUTA_BASE_POR_DEFECTO, claves propias de session_state, estado leido sin crear el archivo." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: La pantalla de Inicio y su estado vacío

**Files:**
- Create: `ui/paginas/inicio.py`
- Test: `tests/unit/test_ui_inicio.py`

**Interfaces:**
- Consumes: `ui.caso` (Tarea 8), `ui.recorridos` (Tarea 7), `scripts.seed_demo.main(argv) -> int`.
- Produces: `ui.paginas.inicio.render() -> None` y los rótulos `ROTULO_ARCHIVO =
  "Archivo del caso (SQLite)"`, `ROTULO_ABRIR = "Abrir este caso"`, `ROTULO_SEMBRAR =
  "Cargar el caso de demostracion"`, `ROTULO_RECORRIDO = "Que quiere hacer?"`, que usan CP‑07
  (Tarea 4) y la Tarea 12.

- [ ] **Step 1: Escribir las pruebas `AppTest`**

```python
"""La pantalla de Inicio (sprint de UI, RF-36 a RF-40), con `AppTest`.

Arnes heredado de `tests/unit/test_ui_componer.py`: la base se desvia parchando el **objeto
modulo** `sys.modules["ui.caso"]` (no una ruta de texto) y se comprueba antes de pulsar nada que
la desviacion surtio efecto. La salvaguarda de `tests/conftest.py` falla la sesion si algo llega a
`data/apu.db`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import ElementList

from ui.caso import CLAVE_CASO, CLAVE_RECORRIDO, estado_caso
from ui.paginas.inicio import ROTULO_ABRIR, ROTULO_ARCHIVO, ROTULO_RECORRIDO, ROTULO_SEMBRAR
from ui.recorridos import NOMBRE_PRECIOS, RECORRIDOS

SCRIPT = "from ui.paginas.inicio import render\nrender()\n"

#: La siembra completa (linea base + demostracion + presupuesto auditado) supera holgadamente los
#: 60 s del arnes de la pantalla de componer en una maquina lenta de CI.
TIEMPO_SIEMBRA = 300


def _por_rotulo(elementos: ElementList, rotulo: str):
    for elemento in elementos:
        if elemento.label == rotulo:
            return elemento
    raise AssertionError(f"ningun elemento {rotulo!r}: {[e.label for e in elementos]}")


def _inicio(monkeypatch, base: Path, *, tiempo: int = 60) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT, default_timeout=tiempo)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert _por_rotulo(at.text_input, ROTULO_ARCHIVO).value == str(base), (
        "la desviacion de ui.caso.RUTA_BASE_POR_DEFECTO no surtio efecto"
    )
    return at


def test_el_inicio_ofrece_los_tres_recorridos(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    radio = _por_rotulo(at.radio, ROTULO_RECORRIDO)
    assert list(radio.options) == [r.nombre for r in RECORRIDOS]
    assert radio.value is None


def test_elegir_un_recorrido_lo_fija_en_la_clave_propia(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    _por_rotulo(at.radio, ROTULO_RECORRIDO).set_value(NOMBRE_PRECIOS).run()
    assert at.session_state[CLAVE_RECORRIDO] == NOMBRE_PRECIOS


def test_una_base_inexistente_muestra_el_estado_vacio_sin_crearla(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "nueva.db"
    at = _inicio(monkeypatch, base)
    assert any("no tiene partidas" in info.value for info in at.info)
    assert _por_rotulo(at.button, ROTULO_SEMBRAR)
    assert not base.exists()


def test_una_base_existente_sin_partidas_ofrece_sembrar(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "vacia.db"
    base.touch()
    at = _inicio(monkeypatch, base)
    assert any("no tiene partidas" in info.value for info in at.info)
    assert _por_rotulo(at.button, ROTULO_SEMBRAR)


def test_la_siembra_deja_la_base_utilizable(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "nueva.db"
    at = _inicio(monkeypatch, base, tiempo=TIEMPO_SIEMBRA)
    _por_rotulo(at.button, ROTULO_SEMBRAR).click().run()
    assert not at.exception, [e.value for e in at.exception]
    estado = estado_caso(base)
    assert estado.partidas > 0 and estado.lista_vigente
    assert ROTULO_SEMBRAR not in [boton.label for boton in at.button]


def test_con_partidas_no_se_ofrece_sembrar(monkeypatch, tmp_path: Path) -> None:
    from core.catalog import abrir_sesion, crear_esquema, crear_motor
    from scripts.seed import sembrar

    base = tmp_path / "sembrada.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    at = _inicio(monkeypatch, base)
    assert ROTULO_SEMBRAR not in [boton.label for boton in at.button]


def test_abrir_otro_caso_lo_fija_en_la_clave_propia(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    otra = tmp_path / "otra.db"
    _por_rotulo(at.text_input, ROTULO_ARCHIVO).set_value(str(otra))
    _por_rotulo(at.button, ROTULO_ABRIR).click().run()
    assert at.session_state[CLAVE_CASO] == str(otra)
    assert CLAVE_CASO not in {widget.key for widget in at.text_input}


def test_abrir_un_caso_vacio_avisa_y_conserva_el_anterior(monkeypatch, tmp_path: Path) -> None:
    at = _inicio(monkeypatch, tmp_path / "caso.db")
    _por_rotulo(at.text_input, ROTULO_ARCHIVO).set_value("   ")
    _por_rotulo(at.button, ROTULO_ABRIR).click().run()
    assert any("no puede quedar vacia" in error.value for error in at.error)
    assert CLAVE_CASO not in at.session_state


def test_un_archivo_ilegible_se_informa_sin_ofrecer_sembrar(monkeypatch, tmp_path: Path) -> None:
    base = tmp_path / "notas.db"
    base.write_text("esto no es una base de datos\n" * 20, encoding="utf-8")
    at = _inicio(monkeypatch, base)
    assert any("No se pudo leer" in error.value for error in at.error)
    assert ROTULO_SEMBRAR not in [boton.label for boton in at.button]
```

- [ ] **Step 2: Ver el rojo**

Run: `uv run pytest tests/unit/test_ui_inicio.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ui.paginas.inicio'`.

- [ ] **Step 3: Implementar `ui/paginas/inicio.py`**

```python
"""Pantalla de Inicio (sprint de UI, UC-12; RF-36 a RF-40).

La puerta de entrada: que caso esta abierto, que hacer si esta vacio y que recorridos hay. Solo
pinta; lo que decide vive en `ui/caso.py` y `ui/recorridos.py`. El titulo, el estado del caso en
la barra lateral y el boton «Siguiente» los pinta el marco de `ui/app.py`.

El estado vacio ofrece cargar el caso de demostracion con `scripts.seed_demo.main`, siempre sin el
flag de reinicio, y solo cuando el caso no tiene partidas: no puede sembrar encima de trabajo
existente ni borrar nada.
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from scripts.seed_demo import main as sembrar_demostracion
from ui.caso import (
    EstadoCaso,
    argv_siembra,
    estado_caso,
    fijar_caso,
    fijar_recorrido,
    recorrido_activo,
    resumen_caso,
    ruta_caso,
)
from ui.recorridos import RECORRIDOS, recorrido_por_nombre

ROTULO_ARCHIVO = "Archivo del caso (SQLite)"
ROTULO_ABRIR = "Abrir este caso"
ROTULO_SEMBRAR = "Cargar el caso de demostracion"
ROTULO_RECORRIDO = "Que quiere hacer?"


def render() -> None:
    """El caso abierto, su estado vacio si lo tiene y los tres recorridos."""
    st.caption(
        "Esta aplicacion arma, costea y audita analisis de precios unitarios. Elija el caso con "
        "que va a trabajar y lo que quiere hacer: cada pantalla le indicara el paso siguiente."
    )
    _elegir_caso()
    _estado(estado_caso(ruta_caso()))
    _elegir_recorrido()


def _elegir_caso() -> None:
    st.subheader("1. El caso con que va a trabajar")
    texto = st.text_input(ROTULO_ARCHIVO, value=str(ruta_caso()))
    if st.button(ROTULO_ABRIR):
        try:
            fijar_caso(texto)
        except ValueError as error:
            st.error(str(error))
        else:
            st.rerun()


def _estado(estado: EstadoCaso) -> None:
    if estado.error is not None:
        st.error(f"{resumen_caso(estado)}. Revise la ruta o abra otro archivo.")
        return
    if not estado.vacio:
        st.success(f"Caso listo: {resumen_caso(estado)}.")
        return
    st.info(
        f"El caso {estado.ruta} no existe todavia o no tiene partidas. Puede cargar el caso de "
        "demostracion —la linea base de la clinica y una linea de agua potable didactica, con su "
        "presupuesto auditado— o abrir otro archivo arriba."
    )
    if st.button(ROTULO_SEMBRAR, type="primary"):
        with st.spinner("Cargando la linea base, la demostracion y su presupuesto auditado..."):
            try:
                sembrar_demostracion(argv_siembra(estado.ruta))
            except (LookupError, ValueError, ArithmeticError, OSError, SQLAlchemyError) as error:
                st.error(f"No se pudo cargar el caso de demostracion: {error}")
                return
        st.rerun()


def _elegir_recorrido() -> None:
    st.subheader("2. Que quiere hacer")
    nombres = [recorrido.nombre for recorrido in RECORRIDOS]
    activo = recorrido_activo()
    eleccion = st.radio(
        ROTULO_RECORRIDO,
        nombres,
        index=nombres.index(activo) if activo in nombres else None,
        captions=[recorrido.proposito for recorrido in RECORRIDOS],
    )
    if eleccion is not None and eleccion != activo:
        fijar_recorrido(eleccion)
        st.rerun()
    recorrido = recorrido_por_nombre(eleccion)
    if recorrido is None:
        return
    for numero, paso in enumerate(recorrido.pasos, start=1):
        st.markdown(f"**{numero}. {paso.titulo}.** {paso.que_hacer}")
    st.caption("Pulse «Siguiente» al pie de la pagina para ir al primer paso.")
```

- [ ] **Step 4: Ver el verde**

Run: `uv run pytest tests/unit/test_ui_inicio.py -q -W error && uv run ruff check ui/paginas/inicio.py tests/unit/test_ui_inicio.py`
Expected: 9 passed; ruff limpio. Si `test_la_siembra_deja_la_base_utilizable` agota el tiempo en
Windows, medir con `--durations=5` y subir `TIEMPO_SIEMBRA`; **no** sustituir la siembra por un doble:
lo que se prueba es que la siembra real deja la base utilizable.

- [ ] **Step 5: Commit**

```bash
git add ui/paginas/inicio.py tests/unit/test_ui_inicio.py
git commit -m "feat(ui): pantalla de inicio con estado vacio sembrable" -m "RF-36 a RF-40: el caso se abre una vez, la base vacia se declara y se siembra sin reinicio posible, y se ofrecen los tres recorridos." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: `ui/app.py` — dos secciones, el Inicio por defecto y el marco común

**Files:**
- Modify: `ui/app.py` (todo el módulo salvo `modo_entrega_activo`)
- Modify (reescritura declarada, §6): `tests/unit/test_ui_app.py`
- Modify: `tests/unit/test_ui_importable.py`

**Interfaces:**
- Consumes: `ui.caso` (Tarea 8), `ui.recorridos` (Tarea 7), `ui.paginas.inicio` (Tarea 9).
- Produces:
  - `SECCION_TRABAJO = "Trabajo"`, `SECCION_INVESTIGACION = "Investigacion"`
  - `DefinicionPagina(render, titulo: str, seccion: str, caso_uso: str | None = None)` con
    `ruta_url` (sin cambios)
  - `PAGINA_INICIO: DefinicionPagina`; `PAGINAS: tuple[DefinicionPagina, ...]` (diez)
  - `paginas_visibles(modo_entrega: bool) -> tuple[DefinicionPagina, ...]`
  - `secciones_visibles(modo_entrega: bool) -> dict[str, tuple[DefinicionPagina, ...]]`
  - `pagina_por_ruta(ruta: str) -> DefinicionPagina` (`KeyError` si no existe)
  - `ruta_actual(url_path: str) -> str`
  - `marco(definicion: DefinicionPagina, pintar: Callable[[], None], ir_a: Callable[[str], None]) -> None`
  - `ROTULO_SIGUIENTE = "Siguiente: {}"`, `CLAVE_BOTON_SIGUIENTE = "marco_siguiente"`

  **En esta tarea las nueve pantallas antiguas siguen pintando su propio título y pidiendo su ruta**
  (eso cambia en la Tarea 11). El marco ya pinta título y subtítulo, así que durante esta tarea
  esas pantallas mostrarán el título dos veces: es el estado intermedio esperado y no se prueba.

> **Enmienda de C3 (2026‑09‑24): INV‑022, INV‑023 y P8.** Esta tarea se ejecuta como la Tarea 5 del
> [plan de C3](2026-09-24-cierre-c3-interfaz-scripts.md), que manda donde difiera:
> - **Anclas vigentes** (sobre `58ee828`): `ui/app.py:1-135`, con `modo_entrega_activo` en
>   `:104-112`; `tests/unit/test_ui_app.py` tiene hoy 7 funciones (`:44`, `:49`, `:54`, `:60`,
>   `:88`, `:94`, `:99`) y `_aplicacion` en `:80-85`.
> - **Paso 1 + INV‑022:** en la reescritura de `test_ui_app.py`, `_aplicacion` afirma tras
>   `at.run()` que la desviación surtió efecto (la leyenda lateral muestra el temporal) y que la
>   huella de `data/apu.db` no cambió.
> - **Paso 2 + INV‑023 + P8:** `test_ui_importable.py` importa los módulos en un proceso limpio con
>   la ayuda única `tests/fixtures/subproceso.py::importar_en_limpio` (A‑13), afirma que no se crean
>   archivos ni se llama a Streamlit sin runtime, y **conserva el literal `ui.paginas.componer`**
>   que busca la meta P8 (`scripts/meta_prototipo.py:216-223`).
> - **Paso 3 + debilidad de INV‑023 en las dos direcciones:** con una mutación temporal en
>   `ui/paginas/historico.py`, la prueba vieja pasa y la nueva falla; se restaura.
> - **Paso 7:** el cuerpo del commit agrega `Cierra INV-022 e INV-023; conserva el literal de la
>   meta P8.`
> - **Paso 8 (nuevo):** `uv run python scripts/meta_prototipo.py` da 12/12.

- [ ] **Step 1: Reescribir `tests/unit/test_ui_app.py`** (sustituye el archivo entero; la
  afirmación de rutas únicas nacida de `a478cfc` se conserva en
  `test_cada_pagina_tiene_una_ruta_url_propia`):

```python
"""Pruebas del enrutador y marco comun de `ui/app.py` (sprint de UI; antes, Sesion P5.1).

Reescritas a proposito en el sprint de UI (spec, §6): el menu paso de nueve pantallas en orden
alfabetico a diez en dos secciones con nombres de oficio, y el Inicio es la pagina por defecto.
Cambian porque cambio el comportamiento **especificado**, no porque fallaran. Sobrevive intacta la
afirmacion de que todas las rutas URL son unicas: nacio de un fallo real (`a478cfc`).

Secciones, orden, filtro del modo entrega e integridad de enlaces son funciones puras sobre
`DefinicionPagina`, que no es de Streamlit. El marco se prueba con `AppTest` desviando la base a un
temporal por el objeto modulo `sys.modules["ui.caso"]`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.app import (
    PAGINA_INICIO,
    PAGINAS,
    SECCION_INVESTIGACION,
    SECCION_TRABAJO,
    VARIABLE_MODO_ENTREGA,
    modo_entrega_activo,
    pagina_por_ruta,
    paginas_visibles,
    ruta_actual,
    secciones_visibles,
)
from ui.paginas.inicio import ROTULO_RECORRIDO
from ui.recorridos import RECORRIDOS, RUTA_INICIO

TITULOS_TRABAJO = (
    "Inicio",
    "Catalogo de partidas e insumos",
    "Componer una partida",
    "Elaborar un presupuesto",
    "Actualizar precios",
    "Historico de cambios de precio",
)

TITULOS_INVESTIGACION = (
    "Escenarios de sensibilidad",
    "Partidas similares",
    "Simulador de listas",
    "Visor 3D del modelo",
)

CASOS_DE_USO = {
    "actualizacion": "UC-02",
    "componer": "UC-10 / UC-11",
    "elaborar": "UC-01",
    "escenarios": "UC-08",
    "similares": "UC-03",
}


def _titulos(paginas) -> tuple[str, ...]:
    return tuple(pagina.titulo for pagina in paginas)


# --- secciones y orden (RF-42, RF-43) ---------------------------------------------------------


def test_sin_modo_entrega_dos_secciones_en_el_orden_del_trabajo() -> None:
    secciones = secciones_visibles(False)
    assert tuple(secciones) == (SECCION_TRABAJO, SECCION_INVESTIGACION)
    assert _titulos(secciones[SECCION_TRABAJO]) == TITULOS_TRABAJO
    assert _titulos(secciones[SECCION_INVESTIGACION]) == TITULOS_INVESTIGACION


def test_modo_entrega_omite_investigacion_y_conserva_todo_trabajo() -> None:
    secciones = secciones_visibles(True)
    assert tuple(secciones) == (SECCION_TRABAJO,)
    assert secciones[SECCION_TRABAJO] == secciones_visibles(False)[SECCION_TRABAJO]


def test_paginas_visibles_es_la_concatenacion_de_las_secciones() -> None:
    for modo in (False, True):
        concatenadas = tuple(p for grupo in secciones_visibles(modo).values() for p in grupo)
        assert paginas_visibles(modo) == concatenadas


def test_modo_entrega_solo_se_activa_con_el_valor_exacto_1() -> None:
    assert modo_entrega_activo({VARIABLE_MODO_ENTREGA: "1"}) is True
    assert modo_entrega_activo({}) is False
    assert modo_entrega_activo({VARIABLE_MODO_ENTREGA: "0"}) is False
    assert modo_entrega_activo({VARIABLE_MODO_ENTREGA: "si"}) is False


def test_ningun_titulo_lleva_codigo_de_caso_de_uso() -> None:
    assert [p.titulo for p in PAGINAS if "UC-" in p.titulo or "UC‑" in p.titulo] == []


def test_las_cinco_pantallas_con_caso_de_uso_lo_declaran() -> None:
    declarados = {p.ruta_url: p.caso_uso for p in PAGINAS if p.caso_uso is not None}
    assert declarados == CASOS_DE_USO


# --- Inicio por defecto (RF-36) ---------------------------------------------------------------


def test_el_inicio_es_la_primera_pagina_y_la_unica_por_defecto() -> None:
    assert PAGINAS[0] is PAGINA_INICIO
    assert PAGINA_INICIO.ruta_url == RUTA_INICIO
    assert sum(1 for p in PAGINAS if p is PAGINA_INICIO) == 1


def test_la_ruta_vacia_de_la_pagina_por_defecto_es_el_inicio() -> None:
    # Streamlit 1.62 devuelve url_path == "" para la pagina marcada default=True
    # (streamlit/navigation/page.py:414).
    assert ruta_actual("") == RUTA_INICIO
    assert ruta_actual("componer") == "componer"


def test_cada_pagina_tiene_una_ruta_url_propia() -> None:
    rutas = [pagina.ruta_url for pagina in paginas_visibles(False)]
    assert len(set(rutas)) == len(rutas) == len(TITULOS_TRABAJO) + len(TITULOS_INVESTIGACION)
    assert "componer" in rutas


def test_pagina_por_ruta() -> None:
    assert pagina_por_ruta("componer").titulo == "Componer una partida"


# --- integridad de enlaces de los recorridos (RF-37, RF-43) -----------------------------------


def test_todo_paso_apunta_a_una_pagina_registrada() -> None:
    registradas = {p.ruta_url for p in paginas_visibles(False)}
    for recorrido in RECORRIDOS:
        for paso in recorrido.pasos:
            assert paso.pagina in registradas, (recorrido.nombre, paso.pagina)


def test_ningun_paso_sale_de_la_seccion_trabajo() -> None:
    en_modo_entrega = {p.ruta_url for p in paginas_visibles(True)}
    for recorrido in RECORRIDOS:
        for paso in recorrido.pasos:
            assert paso.pagina in en_modo_entrega, (recorrido.nombre, paso.pagina)


# --- la aplicacion completa arranca en el Inicio ----------------------------------------------

RUTA_APP = Path(__file__).resolve().parents[2] / "ui" / "app.py"


def _aplicacion(monkeypatch, tmp_path: Path) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "app.db"))
    at = AppTest.from_file(str(RUTA_APP), default_timeout=60)
    at.run()
    return at


def test_la_aplicacion_arranca_en_el_inicio(monkeypatch, tmp_path: Path) -> None:
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    assert at.title[0].value == "Inicio"
    assert any(radio.label == ROTULO_RECORRIDO for radio in at.radio)


def test_la_aplicacion_arranca_en_modo_entrega(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(VARIABLE_MODO_ENTREGA, "1")
    at = _aplicacion(monkeypatch, tmp_path)
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    assert at.title[0].value == "Inicio"
```

- [ ] **Step 2: Ampliar `tests/unit/test_ui_importable.py`** (sustituye el archivo entero):

```python
"""Todo modulo de `ui/` se importa sin construir objetos de Streamlit (spec de UI, §4 regla 3).

La lista ya no se escribe a mano: las paginas salen de `ui.app.PAGINAS`, de modo que una pagina
nueva queda cubierta sin tocar este archivo. Los modulos que no son pagina se nombran aparte.
"""

import importlib

from ui.app import PAGINAS

MODULOS_SIN_PAGINA = ("ui.app", "ui.caso", "ui.recorridos", "ui.composicion")


def test_las_paginas_se_importan_sin_efectos():
    modulos = (*MODULOS_SIN_PAGINA, *(pagina.render.__module__ for pagina in PAGINAS))
    assert len(modulos) == len(MODULOS_SIN_PAGINA) + 10
    for mod in modulos:
        importlib.import_module(mod)
```

- [ ] **Step 3: Ver el rojo**

Run: `uv run pytest tests/unit/test_ui_app.py tests/unit/test_ui_importable.py -q`
Expected: FAIL — `ImportError: cannot import name 'PAGINA_INICIO' from 'ui.app'`.

- [ ] **Step 4: Reescribir `ui/app.py`.** Sustituir el docstring y todo lo que sigue a
  `modo_entrega_activo` por lo de abajo; `modo_entrega_activo`, `TITULO_APP`,
  `VARIABLE_MODO_ENTREGA` y `VALOR_MODO_ENTREGA` se conservan tal cual. El docstring nuevo
  **elimina** el párrafo que justificaba repetir `RUTA_BASE_POR_DEFECTO` en cada página (y con él
  la afirmación falsa sobre `scripts/simular_lista.py`, que no define ninguna constante: usa el
  literal como `default=` de argparse, `scripts/simular_lista.py:86-87`).

```python
"""Interfaz Streamlit multipagina del sistema APU: enrutador y marco comun (sprint de UI).

Dos papeles. **Enrutador:** `st.navigation` sobre las diez pantallas de `ui/paginas/`, agrupadas en
dos secciones —Trabajo e Investigacion— en el orden del trabajo real, con el Inicio como pagina por
defecto (RF-36, RF-42). **Marco comun:** alrededor de cada pantalla, `marco()` pinta el titulo y el
caso de uso que implementa, el caso abierto y su estado en la barra lateral (RF-39), en que paso del
recorrido activo esta el usuario y, al pie, el boton «Siguiente» (RF-41). Streamlit describe asi el
archivo de entrada de `st.navigation`: «acts like a router or frame of common elements around each
of your pages».

El paso siguiente lo pinta el marco, no las paginas: `st.switch_page` necesita el objeto `Page` de
destino, que solo existe dentro de `main()`, y una pagina que importara `ui.app` para obtenerlo
crearia un ciclo. El grafo queda `ui.app -> ui.paginas.* -> ui.caso -> core.catalog`, aciclico.

Cada pagina expone `def render() -> None` sin efectos al importarse. Este modulo tampoco construye
objetos de Streamlit al importarse: `st.Page` y `st.navigation` solo dentro de `main()`, que corre
cuando la app se ejecuta de verdad (`if __name__ == "__main__"`); lo comprueba
`tests/unit/test_ui_importable.py`. `st.set_page_config` se llama una unica vez aqui.

La pagina por defecto tiene `url_path == ""` en Streamlit (no la ruta que se le declaro): por eso
`ruta_actual()` traduce la ruta vacia al Inicio antes de buscar su definicion.

Modo entrega (Sesion P5.1, prototipo AREN.IA). Con `ARENIA_MODO_ENTREGA=1` (exactamente `"1"`) el
menu **omite** la seccion Investigacion —escenarios, similares, simulador y visor 3D—; la seccion
Trabajo queda completa (RF-43). Las secciones no se pueden colapsar en la barra lateral de
Streamlit (solo con `position="top"`), por eso se omite en vez de plegarse.

Uso (con `python -m`: `streamlit run` a secas pone en `sys.path` la carpeta `ui/` y no la raiz
del repositorio, y entonces `import ui` falla; `python -m` agrega el directorio actual)::

    uv sync --extra ui --extra api --extra civil
    uv run python -m streamlit run ui/app.py

Otro caso que `data/apu.db`, y modo entrega, en bash::

    ARENIA_CASO=data/otro.db ARENIA_MODO_ENTREGA=1 uv run python -m streamlit run ui/app.py

y en PowerShell::

    $env:ARENIA_CASO = "data/otro.db"; $env:ARENIA_MODO_ENTREGA = "1"; uv run python -m streamlit run ui/app.py
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import streamlit as st

from ui.caso import estado_caso, recorrido_activo, resumen_caso, ruta_caso
from ui.paginas import (
    actualizacion,
    catalogo,
    componer,
    elaborar,
    escenarios,
    historico,
    inicio,
    similares,
    simulador,
    visor,
)
from ui.recorridos import RUTA_INICIO, Recorrido, paso_siguiente, recorrido_por_nombre

TITULO_APP = "Sistema APU"
VARIABLE_MODO_ENTREGA = "ARENIA_MODO_ENTREGA"
VALOR_MODO_ENTREGA = "1"
SECCION_TRABAJO = "Trabajo"
SECCION_INVESTIGACION = "Investigacion"
ROTULO_SIGUIENTE = "Siguiente: {}"
CLAVE_BOTON_SIGUIENTE = "marco_siguiente"


@dataclass(frozen=True, slots=True)
class DefinicionPagina:
    """Una pantalla del enrutador, sin Streamlit: de ella nace un `st.Page` dentro de `main()`."""

    render: Callable[[], None]
    titulo: str
    seccion: str
    caso_uso: str | None = None  # codigo de la ERS; el marco lo pinta como subtitulo (RF-42)

    @property
    def ruta_url(self) -> str:
        """Ruta URL de la pagina: el nombre de su modulo (`ui.paginas.componer` -> `componer`).

        Sin ella Streamlit la infiere del nombre de la funcion, y como todas se llaman `render`
        `st.navigation` rechaza la aplicacion entera por rutas repetidas.
        """
        return self.render.__module__.rsplit(".", 1)[-1]


PAGINA_INICIO = DefinicionPagina(inicio.render, "Inicio", SECCION_TRABAJO)

PAGINAS: tuple[DefinicionPagina, ...] = (
    PAGINA_INICIO,
    DefinicionPagina(catalogo.render, "Catalogo de partidas e insumos", SECCION_TRABAJO),
    DefinicionPagina(componer.render, "Componer una partida", SECCION_TRABAJO, "UC-10 / UC-11"),
    DefinicionPagina(elaborar.render, "Elaborar un presupuesto", SECCION_TRABAJO, "UC-01"),
    DefinicionPagina(actualizacion.render, "Actualizar precios", SECCION_TRABAJO, "UC-02"),
    DefinicionPagina(historico.render, "Historico de cambios de precio", SECCION_TRABAJO),
    DefinicionPagina(
        escenarios.render, "Escenarios de sensibilidad", SECCION_INVESTIGACION, "UC-08"
    ),
    DefinicionPagina(similares.render, "Partidas similares", SECCION_INVESTIGACION, "UC-03"),
    DefinicionPagina(simulador.render, "Simulador de listas", SECCION_INVESTIGACION),
    DefinicionPagina(visor.render, "Visor 3D del modelo", SECCION_INVESTIGACION),
)


def modo_entrega_activo(entorno: Mapping[str, str] | None = None) -> bool:
    """Indica si el modo entrega esta encendido: la variable vale exactamente `"1"`.

    `entorno` permite probar la funcion sin tocar `os.environ`; si es `None` se lee el entorno
    del proceso.
    """
    if entorno is None:
        entorno = os.environ
    return entorno.get(VARIABLE_MODO_ENTREGA) == VALOR_MODO_ENTREGA


def paginas_visibles(modo_entrega: bool) -> tuple[DefinicionPagina, ...]:
    """Las pantallas que se muestran: las diez, o sin la seccion Investigacion en modo entrega."""
    if not modo_entrega:
        return PAGINAS
    return tuple(pagina for pagina in PAGINAS if pagina.seccion != SECCION_INVESTIGACION)


def secciones_visibles(modo_entrega: bool) -> dict[str, tuple[DefinicionPagina, ...]]:
    """Las pantallas visibles agrupadas por seccion; el `dict` conserva el orden de `PAGINAS`."""
    secciones: dict[str, tuple[DefinicionPagina, ...]] = {}
    for pagina in paginas_visibles(modo_entrega):
        secciones[pagina.seccion] = (*secciones.get(pagina.seccion, ()), pagina)
    return secciones


def pagina_por_ruta(ruta: str) -> DefinicionPagina:
    """La definicion de la pantalla con esa ruta URL. `KeyError` si no hay ninguna."""
    for pagina in PAGINAS:
        if pagina.ruta_url == ruta:
            return pagina
    raise KeyError(f"no hay ninguna pantalla con la ruta {ruta!r}")


def ruta_actual(url_path: str) -> str:
    """La ruta de la pantalla actual: Streamlit da `""` a la pagina por defecto, que es el Inicio."""
    return url_path or RUTA_INICIO


def marco(
    definicion: DefinicionPagina, pintar: Callable[[], None], ir_a: Callable[[str], None]
) -> None:
    """Los elementos comunes alrededor de una pantalla.

    `pintar` pinta la pantalla (`Page.run` en la aplicacion, `render` en las pruebas); `ir_a` lleva
    a la pantalla de una ruta (`st.switch_page` en la aplicacion, un registrador en las pruebas).
    """
    st.title(definicion.titulo)
    if definicion.caso_uso is not None:
        st.caption(f"Caso de uso {definicion.caso_uso}")
    _pintar_caso_abierto()
    recorrido = recorrido_por_nombre(recorrido_activo())
    _pintar_posicion(recorrido, definicion.ruta_url)
    pintar()
    paso = paso_siguiente(recorrido, definicion.ruta_url)
    if paso is not None and st.button(
        ROTULO_SIGUIENTE.format(paso.titulo), type="primary", key=CLAVE_BOTON_SIGUIENTE
    ):
        ir_a(paso.pagina)


def _pintar_caso_abierto() -> None:
    estado = estado_caso(ruta_caso())
    with st.sidebar:
        st.subheader("Caso abierto")
        st.caption(str(estado.ruta))
        st.caption(resumen_caso(estado))


def _pintar_posicion(recorrido: Recorrido | None, ruta: str) -> None:
    if recorrido is None:
        return
    with st.sidebar:
        st.subheader(f"Recorrido: {recorrido.nombre}")
        if ruta == RUTA_INICIO:
            st.caption("Pulse «Siguiente» al pie de la pagina para empezar.")
            return
        posicion = recorrido.posicion(ruta)
        if posicion is None:
            st.caption("Esta pantalla no es parte del recorrido; vuelva al Inicio para retomarlo.")
            return
        paso = recorrido.pasos[posicion - 1]
        st.caption(f"Paso {posicion} de {len(recorrido.pasos)}: {paso.titulo}")
        st.markdown(paso.que_hacer)
        st.caption(f"Sabra que termino cuando: {paso.senal_de_exito}")


def main() -> None:
    """Punto de entrada de `streamlit run ui/app.py`: configura, enruta y enmarca la pantalla."""
    st.set_page_config(page_title=TITULO_APP, layout="wide")
    modo_entrega = modo_entrega_activo()
    paginas = {
        definicion.ruta_url: st.Page(
            definicion.render,
            title=definicion.titulo,
            url_path=definicion.ruta_url,
            default=definicion is PAGINA_INICIO,
        )
        for definicion in paginas_visibles(modo_entrega)
    }
    secciones = {
        seccion: [paginas[definicion.ruta_url] for definicion in definiciones]
        for seccion, definiciones in secciones_visibles(modo_entrega).items()
    }
    actual = st.navigation(secciones)
    marco(
        pagina_por_ruta(ruta_actual(actual.url_path)),
        actual.run,
        lambda ruta: st.switch_page(paginas[ruta]),
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Ver el verde**

Run: `uv run pytest tests/unit/test_ui_app.py tests/unit/test_ui_importable.py tests/unit/test_visor3d.py tests/unit/test_composicion_ia.py -q -W error`
Expected: todo verde. `test_visor3d.py` y `test_composicion_ia.py` reimportan `ui.app`
bloqueando `ml`/`ifcopenshell`; **no** agregar `ui.caso` ni `ui.recorridos` a sus listas de
módulos a reimportar: si se reimportaran, las páginas quedarían atadas a una copia de `ui.caso`
distinta de la que parchan las pruebas.

- [ ] **Step 6: Suite completa** (las páginas antiguas aún piden su ruta: la Tarea 11 lo cambia)

Run: `uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: verde. Si algo escribe en `data/apu.db`, la salvaguarda lo detiene: corregir la prueba.

- [ ] **Step 7: Commit**

```bash
git add ui/app.py tests/unit/test_ui_app.py tests/unit/test_ui_importable.py
git commit -m "feat(ui): menu en dos secciones con inicio por defecto y marco comun" -m "RF-36, RF-39, RF-41 a RF-43. El marco pinta titulo, caso de uso, caso abierto, posicion y boton Siguiente alrededor de Page.run; la ruta vacia de la pagina por defecto se traduce al Inicio." -m "test_ui_app.py se reescribe a proposito (spec de UI, seccion 6); sobrevive la afirmacion de rutas unicas." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Las nueve pantallas leen el caso abierto; el marco pinta su título

**Files:**
- Modify: `ui/paginas/actualizacion.py`, `catalogo.py`, `componer.py`, `elaborar.py`,
  `escenarios.py`, `historico.py`, `similares.py`, `simulador.py`, `visor.py`
- Modify: `tests/unit/test_ui_componer.py:21-30` (docstring, hecho 2), `:90-115` (`_pantalla`;
  parche `:100-101`, mensaje `:106-110`); anclas vigentes sobre `58ee828` (enmienda de C3)
- Modify: `tests/unit/test_ui_app.py` (agrega las pruebas del marco por pantalla)

**Interfaces:**
- Consumes: `ui.caso.ruta_caso() -> Path` (Tarea 8); `ui.app.marco`, `pagina_por_ruta`,
  `CLAVE_BOTON_SIGUIENTE`, `ROTULO_SIGUIENTE` (Tarea 10).
- Produces: ninguna página de `ui/paginas/` salvo `inicio.py` define `RUTA_BASE_POR_DEFECTO`,
  `TITULO` ni llama a `st.title`.

- [ ] **Step 1: Escribir las pruebas del marco por pantalla** — agregar al final de
  `tests/unit/test_ui_app.py` (y `import pytest` junto a los imports; y del bloque de imports de
  `ui.app` agregar `CLAVE_BOTON_SIGUIENTE`, `ROTULO_SIGUIENTE`; de `ui.caso`, `CLAVE_RECORRIDO`,
  `estado_caso`, `resumen_caso`; de `ui.recorridos`, `NOMBRE_DEMOSTRACION`):

```python
# --- el marco alrededor de cada pantalla (RF-38, RF-39, RF-41, RF-42) --------------------------
#
# `AppTest` no puede navegar entre paginas definidas por callable (spec de UI, §6): cada pantalla se
# pinta por separado dentro de `marco()`, con el caso fijado en un temporal y un `ir_a` que solo
# registra el destino en la sesion.

SCRIPT_MARCO = """
import streamlit as st
from ui.app import marco, pagina_por_ruta
definicion = pagina_por_ruta({ruta!r})
marco(definicion, definicion.render, lambda destino: st.session_state.__setitem__("destino", destino))
"""


@pytest.fixture(scope="module")
def base_sembrada(tmp_path_factory) -> Path:
    from core.catalog import abrir_sesion, crear_esquema, crear_motor
    from scripts.seed import sembrar

    base = tmp_path_factory.mktemp("marco") / "caso.db"
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return base


def _marco(monkeypatch, base: Path, ruta: str, estado: dict[str, object] | None = None) -> AppTest:
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    at = AppTest.from_string(SCRIPT_MARCO.format(ruta=ruta), default_timeout=120)
    for clave, valor in (estado or {}).items():
        at.session_state[clave] = valor
    at.run()
    assert not at.exception, [excepcion.value for excepcion in at.exception]
    return at


@pytest.mark.parametrize("ruta", [pagina.ruta_url for pagina in PAGINAS])
def test_cada_pantalla_muestra_el_caso_abierto_y_su_titulo(monkeypatch, base_sembrada, ruta) -> None:
    at = _marco(monkeypatch, base_sembrada, ruta)
    leyendas = [leyenda.value for leyenda in at.sidebar.caption]
    assert str(base_sembrada) in leyendas
    assert resumen_caso(estado_caso(base_sembrada)) in leyendas
    definicion = pagina_por_ruta(ruta)
    assert [titulo.value for titulo in at.title] == [definicion.titulo]
    if definicion.caso_uso is not None:
        assert f"Caso de uso {definicion.caso_uso}" in [c.value for c in at.main.caption]


@pytest.mark.parametrize("ruta", [pagina.ruta_url for pagina in PAGINAS if pagina.ruta_url != "inicio"])
def test_ninguna_pantalla_distinta_del_inicio_pide_la_ruta(monkeypatch, base_sembrada, ruta) -> None:
    at = _marco(monkeypatch, base_sembrada, ruta)
    rotulos = [campo.label for campo in at.text_input]
    assert not any("SQLite" in rotulo for rotulo in rotulos), rotulos


def test_la_barra_lateral_indica_el_paso_del_recorrido(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "catalogo", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    leyendas = [leyenda.value for leyenda in at.sidebar.caption]
    assert "Paso 1 de 2: Ver el catalogo del caso" in leyendas


def test_el_boton_siguiente_lleva_al_paso_que_sigue(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "catalogo", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    boton = at.button(key=CLAVE_BOTON_SIGUIENTE)
    assert boton.label == ROTULO_SIGUIENTE.format("Elaborar, auditar y exportar")
    boton.click().run()
    assert at.session_state["destino"] == "componer"


def test_desde_el_inicio_el_siguiente_es_el_primer_paso(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "inicio", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    at.button(key=CLAVE_BOTON_SIGUIENTE).click().run()
    assert at.session_state["destino"] == "catalogo"


def test_en_el_ultimo_paso_no_hay_siguiente(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "componer", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    assert CLAVE_BOTON_SIGUIENTE not in {boton.key for boton in at.button}


def test_una_pantalla_fuera_del_recorrido_no_muestra_siguiente(monkeypatch, base_sembrada) -> None:
    at = _marco(monkeypatch, base_sembrada, "historico", {CLAVE_RECORRIDO: NOMBRE_DEMOSTRACION})
    assert CLAVE_BOTON_SIGUIENTE not in {boton.key for boton in at.button}
```

  Y agregar al final de `tests/unit/test_ui_caso.py` (con `import re` en sus imports) la prueba
  que en la Tarea 8 todavía no podía pasar:

```python
def test_la_ruta_por_defecto_se_define_una_sola_vez_en_ui() -> None:
    definiciones = [
        archivo.relative_to(RAIZ).as_posix()
        for archivo in sorted((RAIZ / "ui").rglob("*.py"))
        if re.search(r"^RUTA_BASE_POR_DEFECTO\s*=", archivo.read_text(encoding="utf-8"), re.M)
    ]
    assert definiciones == ["ui/caso.py"]
```

- [ ] **Step 2: Ver el rojo, sin tocar la base real**

Run: `uv run pytest tests/unit/test_ui_caso.py tests/unit/test_ui_app.py -q -k "una_sola_vez or (muestra_el_caso and visor)"`
Expected: 2 failed — la ruta por defecto aparece en nueve archivos, y el visor pinta dos títulos.
**No** correr todavía las pruebas del marco sobre las demás pantallas: con su ruta antigua,
`catalogo`, `componer` y el resto crearían `data/apu.db` (la salvaguarda lo detectaría, pero el
archivo ya habría quedado escrito). El visor es la única pantalla que no abre la base.

- [ ] **Step 3: Migrar las nueve pantallas.** En cada una: importar `from ui.caso import ruta_caso`;
  borrar la constante `RUTA_BASE_POR_DEFECTO`, la constante `TITULO` y la línea `st.title(TITULO)`
  (el marco los pinta); sustituir la obtención de la ruta como se indica. Las pantallas cuyo
  subtítulo mencionaba el código del caso de uso **dentro del texto** (p. ej. el de `componer.py`,
  «…reemplaza su composicion vigente (UC-11)…») lo conservan: es prosa, no título.

  | Página | Antes | Después |
  |---|---|---|
  | `catalogo.py:32` | `ruta = Path(st.sidebar.text_input("Archivo SQLite", value=RUTA_BASE_POR_DEFECTO))` | `ruta = ruta_caso()` |
  | `componer.py:120` | ídem | `ruta = ruta_caso()` |
  | `escenarios.py:57` | ídem | `ruta = ruta_caso()` |
  | `historico.py:37` | ídem | `ruta = ruta_caso()` |
  | `similares.py:69` | ídem | `ruta = ruta_caso()` |
  | `actualizacion.py:107-108` | `st.header("Base de datos")` + `ruta = st.text_input("Archivo SQLite", value=RUTA_BASE_POR_DEFECTO)` | `st.header("Base de datos")` + `ruta = ruta_caso()`; el botón «Sembrar la linea base» se conserva y siembra en `ruta` |
  | `actualizacion.py:123` dict | `"ruta": Path(ruta),` | `"ruta": ruta,` |
  | `elaborar.py:98-99` | `st.header("Base de datos")` + `ruta = st.text_input(...)` | borrar ambas líneas; en el dict (`:110`), `"ruta": ruta_caso(),` |
  | `simulador.py:50-51` | `st.header("Base de datos")` + `ruta = st.text_input(...)` | borrar ambas líneas; en el dict (`:59`), `"ruta": ruta_caso(),` |
  | `visor.py` | no pide ruta | solo borrar `TITULO` y `st.title(TITULO)` |

  Tras migrar, quitar `from pathlib import Path` de las páginas donde quede sin uso (ruff lo
  señalará con `F401`).

- [ ] **Step 4: Migrar el arnés de `tests/unit/test_ui_componer.py`.** En `_pantalla` (`:90-115`),
  sustituir:

```python
    pagina = importlib.import_module("ui.paginas.componer")
    monkeypatch.setattr(pagina, "RUTA_BASE_POR_DEFECTO", str(base))
    monkeypatch.setattr(pagina, "sugerir_partidas_similares", lambda *_: [])
```

  por:

```python
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    pagina = importlib.import_module("ui.paginas.componer")
    monkeypatch.setattr(pagina, "sugerir_partidas_similares", lambda *_: [])
```

  y el mensaje del `assert base.exists()` por: `f"la redireccion de ui.caso.RUTA_BASE_POR_DEFECTO
  no surtio efecto: {base} no existe tras el primer run (la pantalla habria creado el esquema
  ahi)"`. En el docstring del módulo, hecho verificado 2, cambiar «parchando el **objeto módulo**
  que devuelve `importlib.import_module("ui.paginas.componer")`» por «parchando el **objeto
  módulo** que devuelve `importlib.import_module("ui.caso")`, donde vive la única
  `RUTA_BASE_POR_DEFECTO` desde el sprint de UI» y `monkeypatch.setattr(pagina,
  "RUTA_BASE_POR_DEFECTO", str(base))` por `monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO",
  str(base))`; el resto del razonamiento sobre la copia huérfana se conserva (sigue aplicando a
  `sugerir_partidas_similares`).

- [ ] **Step 5: Ver el verde de todo lo de interfaz**

Run: `uv run pytest tests/unit/test_ui_app.py tests/unit/test_ui_componer.py tests/unit/test_ui_caso.py tests/unit/test_ui_inicio.py tests/unit/test_ui_importable.py -q -W error --durations=10`
Expected: todo verde. `test_la_ruta_por_defecto_se_define_una_sola_vez_en_ui` ahora sí vigila las
nueve páginas.

- [ ] **Step 6: Regresión intocable y suite completa**

Run: `git diff --stat main -- tests/integration/test_composicion_extremo_a_extremo.py tests/fixtures/apu_linea_base.py adapters/ && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: el `git diff --stat` no imprime nada; suite y ruff verdes. **Enmienda de C3:** `core/`,
`ml/` y `api/` ya no se exigen vacíos aquí; su criterio es el de la Tarea 18, paso 3, del
[plan de C3](2026-09-24-cierre-c3-interfaz-scripts.md) (dos commits de `core/`, INV‑080 e INV‑015
7a), y `tests/fixtures/` gana ayudas nuevas (`subproceso.py` y las de INV‑052).

- [ ] **Step 7: Commit**

```bash
git add ui/paginas/ tests/unit/test_ui_componer.py tests/unit/test_ui_app.py
git commit -m "refactor(ui): las pantallas leen el caso abierto y el marco pinta su titulo" -m "RF-38 y RF-42: ocho copias de RUTA_BASE_POR_DEFECTO pasan a una en ui/caso.py; ninguna pantalla salvo el Inicio pide la ruta; el codigo del caso de uso baja a subtitulo." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

> **Enmienda de C3 (2026‑09‑24): pasos 8 a 12, la extracción de INV‑043 (11b y 11c, D5 = A).**
> Si el inventario propone dividir `ui/paginas/componer.py` por el criterio S, **esa extracción la
> hace la Tarea 11 y nadie más** (spec de cierre §5, fila C3). Los pasos 8 a 12 se ejecutan tal
> como los escribe la Tarea 6 del [plan de C3](2026-09-24-cierre-c3-interfaz-scripts.md) (parte b),
> que manda en firmas, mordidas y commits. Es una refactorización **sin cambio de comportamiento**:
> las 9 pruebas de `tests/unit/test_ui_componer.py` siguen verdes y solo cambia el arnés del paso 4.

- [ ] **Step 8: Prueba de arquitectura en rojo.** `test_ui_respeta_sus_importaciones_prohibidas`,
  una sola prueba parametrizada en `tests/unit/test_arquitectura.py` (A‑9); falla en
  `ui/paginas/componer.py` citando `core.budget`. La entrada de `ui/composicion.py` se observa con
  una mutación en las dos direcciones (P7 no la ve; esta prueba sí).
- [ ] **Step 9: Extraer (11b).** `ui/elaboracion.py` (sin Streamlit, `pandas` ni `ui.caso`:
  `items_desde_filas`, `elaborar_desde_catalogo`, `libro_excel`) y `ui/resultado.py` (el fragmento
  `mostrar_elaboracion`, sin `sqlalchemy.orm` ni `core.costing`); pruebas puras en
  `tests/unit/test_elaboracion.py`, cada función con su mordida. Commit
  `refactor(ui): la elaboracion sale de la pagina de componer`.
- [ ] **Step 10: 11c.** `ui/composicion.py` gana `desglose` (puro) y `ui/elaboracion.py` gana
  `Guardado` y `guardar_composicion` (la persistencia, sin `commit`); `componer.py` deja de
  importar `core.costing`, `core.budget` y `sqlalchemy.orm` en tiempo de ejecución.
- [ ] **Step 11: Verde y regresión**, con el recuento, `scripts/meta_prototipo.py` (P7 sigue OK) y
  las líneas de `componer.py` antes (862) y después.
- [ ] **Step 12: Commit de 11c**, separado del de 11b:
  `refactor(ui): calculo y guardado de la composicion fuera de la pagina`, que cierra INV‑043.

---

### Task 12: Manual y guion con los nombres nuevos

**Files:**
- Modify: `docs/manual_usuario.md` (tabla de pantallas `:97-105` y menciones de títulos antiguos:
  `:44`, `:174`, `:260`, `:290`)
- Modify: `docs/guion_prueba_arenia.md` (`:3`, preparación §4 `:38-110`, precondiciones de
  CP‑01…CP‑06; CP‑07 `:394-533`); anclas vigentes sobre `58ee828` (enmienda de C3)
- Modify: `tests/unit/test_guion_prueba_arenia.py` (`test_cp07_se_declara_no_ejecutable_hasta_u1`,
  paso 5b, enmienda de C3)
- Modify: `docs/ERS.md` (columna de criterio de RF‑36…RF‑43: `pendiente` → `cumplido`)
- Modify: `docs/plan_pruebas.md` (§8, filas RF‑36…RF‑43: casos y resultado)

**Interfaces:**
- Consumes: títulos de `ui.app.PAGINAS` y rótulos de `ui.paginas.inicio` (Tareas 9–11).
- Produces: documentos coherentes con la interfaz que prueba CP‑07.

- [ ] **Step 1: Listar las menciones a los títulos antiguos**

Run: `grep -n "Componer partida\|Actualizacion de precios\|Elaborar presupuesto (UC\|Escenarios (UC\|Partidas similares (UC\|Archivo SQLite\|Visor 3D\b" docs/manual_usuario.md docs/guion_prueba_arenia.md`

- [ ] **Step 2: Sustituir cada mención** por el título nuevo (tabla de la Tarea 10: «Componer una
  partida», «Actualizar precios», «Elaborar un presupuesto», «Escenarios de sensibilidad»,
  «Partidas similares», «Catalogo de partidas e insumos», «Visor 3D del modelo»). Donde el manual
  o el guion digan que se teclea la ruta de la base en la barra lateral de una pantalla, sustituir
  por: «el caso se abre una vez en **Inicio** (campo *Archivo del caso (SQLite)* y botón *Abrir
  este caso*); la barra lateral lo muestra bajo **Caso abierto**». En el manual, agregar a la
  tabla de pantallas la fila de **Inicio** y una nota: «Con `ARENIA_CASO=<ruta>` la aplicación
  abre ese caso sin pasar por el Inicio.» Las specs de sprints anteriores **no** se tocan: son
  históricas.

- [ ] **Step 3: Poner al día la trazabilidad.** Con la corrida de la Tarea 11, paso 6, contar las
  funciones de prueba de cada archivo nuevo
  (`uv run pytest tests/unit/test_ui_recorridos.py tests/unit/test_ui_caso.py tests/unit/test_ui_inicio.py tests/unit/test_ui_app.py -q --co | tail -1`
  y uno por uno) y en `docs/ERS.md` cambiar el prefijo «pendiente:» de RF‑36…RF‑43 por
  «cumplido (U1):»; en `docs/plan_pruebas.md` §8 llenar «Casos» y poner «verde».

- [ ] **Step 4: Recorrer la tabla de `docs/plan_pruebas.md` §8.1 y comprobar con
  `grep -n "def <nombre>" tests/` que cada prueba citada existe; pasar cada fila a "verde" o, si
  falta, detenerse: un paso de UC‑12 sin prueba es un hallazgo, no una fila por corregir.**

- [ ] **Step 5: Comprobar**

Run: `grep -n "Componer partida (UC\|Archivo SQLite" docs/manual_usuario.md docs/guion_prueba_arenia.md; uv run pytest tests/unit/test_meta_prototipo.py tests/unit/test_meta_datos.py -q`
Expected: el `grep` no imprime nada; las metas siguen verdes.

- [ ] **Step 5b (enmienda de C3): reescribir a propósito
  `test_cp07_se_declara_no_ejecutable_hasta_u1`** (`tests/unit/test_guion_prueba_arenia.py:115-121`),
  que hoy fija que CP‑07 «no es ejecutable hasta U1». Con U1 hecha, la prueba afirma que CP‑07
  **ya** es ejecutable y que su medición con personas es de Med (GU1b). El guion **conserva la
  corrección de INV‑065**: la prueba manual trabaja sobre su propia base y nunca vuelve a
  `data/apu.db`. La prueba entra en el commit del paso 6.

- [ ] **Step 6: Commit**

```bash
git add docs/manual_usuario.md docs/guion_prueba_arenia.md docs/ERS.md docs/plan_pruebas.md tests/unit/test_guion_prueba_arenia.py
git commit -m "docs(manual): nombres de oficio, inicio y caso abierto; rf-36 a rf-43 cumplidos" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: Compuerta GU1a

> **Enmienda de C3 (2026‑09‑24).** GU1 se parte (spec de cierre §5): esta tarea cierra **GU1a** (U1
> completa sin CP‑07) como parte de la compuerta **GC3 = GU1a**, cuyo procedimiento completo es la
> Tarea 18 del [plan de C3](2026-09-24-cierre-c3-interfaz-scripts.md). CP‑07 con personas (pasos 6
> y 7 originales) sale de aquí hacia la fase **Med**, compuerta **GU1b**.

**Files:**
- Modify: `docs/bitacora/2026-09-23-sprint-ui.md`
- Modify: `docs/guion_prueba_arenia.md` (hoja de registro de CP‑07, al ejecutarlo) — en Med (GU1b)
- Modify: `docs/calidad_iso25010.md` (§4 y §9 con la medición; cifras de pruebas al día) — en Med (GU1b)

**Interfaces:**
- Consumes: todo U1.
- Produces: veredicto de GU1a. El de CP‑07 (y, si FALLA, la lista de puntos de detención que fija
  el alcance de U2) lo produce Med (GU1b).

- [ ] **Step 1: Línea base y auditoría**

Run: `uv run pytest tests/unit/test_costing.py tests/integration/test_auditoria_7_de_7.py tests/integration/test_composicion_extremo_a_extremo.py -q -W error`
Expected: verde (1 586,61 USD y 7 de 7, afirmados contra `tests/fixtures/apu_linea_base.py`).

- [ ] **Step 2: Núcleo cerrado, guardia y suite completa**

Run: el criterio de `core/` de la Tarea 18, paso 3, del plan de C3 (`guardia_gc3.sh 2`, que incluye
`scripts/guardia_nucleo.py` en la rama y contra una fusión de prueba en `main`), después
`uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: exactamente dos commits tocan `core/` (INV‑080 e INV‑015 7a), cada uno solo con `core/` y
sus pruebas; ninguna marca; guardia con código 0; suite y ruff verdes. Anotar el número de pruebas.

- [ ] **Step 3: CI en ambos sistemas.** Empujar la rama **solo con permiso de Eugenio**
  (`git push -u origin inc/cierre-C3`) y abrir el PR con `gh pr create` hacia `main`; esperar el
  workflow y comprobar `ubuntu-latest` y `windows-latest` en verde con `gh pr checks`.

- [ ] **Step 4: La aplicación en un navegador de verdad** (pendiente heredado de la bitácora del
  prototipo, `:190-191`). Con `ARENIA_CASO=data/cp07/humo.db` (inexistente) arrancar la aplicación
  y comprobar a mano: abre en Inicio; el estado vacío aparece; «Cargar el caso de demostracion»
  siembra y el aviso desaparece; al elegir «Ver la demostracion auditada», «Siguiente» lleva al
  catálogo y luego a componer; la barra lateral muestra el caso en cada pantalla. Repetir con
  `ARENIA_MODO_ENTREGA=1`: solo la sección Trabajo, completa. Anotar en la bitácora.

- [ ] **Step 5: Revisión de los cuatro encargos** sobre `git diff main..HEAD`, como en la Tarea 5,
  paso 2, con el arquitecto verificando además las reglas 1–6 de §4 de la spec y el ingeniero de
  pruebas la cobertura de los cinco puntos de **Review Focus**. Corregir bloqueantes y repasar
  hasta que aprueben.

- [ ] **Step 6: CP‑07 con dos personas — pasa a Med (GU1b), enmienda de C3; no se ejecuta en
  C3.** Lo ejecuta Eugenio como observador, siguiendo al pie de la letra `docs/guion_prueba_arenia.md` CP‑07, un escenario por persona. Llenar la hoja de
  registro; calcular el veredicto con el criterio declarado; **no** modificar el criterio después
  de medir.

- [ ] **Step 7: Registrar.** **Enmienda de C3:** en C3 solo se registra en la bitácora la línea
  `**GU1a: cruzada el <fecha>.**` (con los resultados de los pasos 1 a 5); lo que sigue sobre
  CP‑07 lo hace Med (GU1b). En Med: en `docs/calidad_iso25010.md` §4 reemplazar «Veredicto:
  pendiente de medición» de RNF‑10 por el resultado (n, perfiles, tiempos, promedios del bloque B, veredicto) y
  actualizar su fila de §9 y la nota de vigencia con el conteo de pruebas del paso 2. En la
  bitácora: resultados del paso 6 y la línea `**GU1b: cruzada el <fecha>. CP‑07: PASA|FALLA.**`
  Si FALLA: copiar los puntos de detención a una sección «Alcance de U2» y **no** empezar U2 sin
  que Eugenio lo confirme.

- [ ] **Step 8: Commit.** **Enmienda de C3:** en C3, GU1a se registra en los commits de la Tarea 18
  del plan de C3 (`docs(bitacora): compuerta gc3 del cierre, pendiente de ci`); el commit de abajo,
  con el resultado de CP‑07, es de Med (GU1b).

```bash
git add docs/bitacora/2026-09-23-sprint-ui.md docs/guion_prueba_arenia.md docs/calidad_iso25010.md
git commit -m "docs(bitacora): compuerta gu1b y resultado de cp-07" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

## Fases U2 y U3

No se detallan aquí a propósito. **U2** solo existe si CP‑07 resulta FALLA, y su alcance lo fijan
los puntos de detención registrados en Med (GU1b; antes, Tarea 13): escribir sus tareas hoy sería inventarlas. Se
planifica en un documento propio con la skill `superpowers:writing-plans` al cerrar GU1b (Med). **U3**
requiere decisión expresa de Eugenio.
