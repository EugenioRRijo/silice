# Cierre de la tesis, fase C3: interfaz y scripts

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Archivo propuesto:** `docs/superpowers/plans/2026-09-24-cierre-c3-interfaz-scripts.md`. Entra en el primer commit de `inc/cierre-C3` junto con la enmienda del plan de UI (Tarea 1).

**Goal:** ejecutar U1 del plan de UI (sus Tareas 7 a 12) como fase C3 del cierre y cerrar los hallazgos de C3 del inventario:

- **Importantes:** INV‑019 a INV‑025, INV‑043 (solo dentro de la Tarea 11 de UI), INV‑072 (su parte de `ui/`), INV‑075, INV‑080 (un commit de `core/budget/`, D4 = A), INV‑083 (nuevo: los escenarios de un base con pendientes, solo en `ui/`; Hecho 11) y la subtarea 7a de INV‑015 (un commit de `core/` propio, D1 = A).
- **Menores promovidos:** INV‑044, INV‑045, INV‑046, INV‑049, INV‑050, INV‑051, INV‑052 e INV‑081.
- **INV‑076:** C3 no escribe su código (D2). Se registra «en duda» (spec §2), con diseño propio fuera de C3, y cruza GC3 **abierto**.

Con todo eso se cruza la compuerta **GC3 = GU1a**.

**Architecture:**

- **`ui/` es la capa principal.** Cuatro piezas nuevas del plan de UI: `ui/recorridos.py`, `ui/caso.py`, `ui/paginas/inicio.py` y el marco en `ui/app.py`. Con INV‑043 (11b + 11c, D5 = A) se suman `ui/elaboracion.py`, sin Streamlit ni `pandas`, que orquesta contra `core.budget` y `core.catalog` y es **el único módulo de `ui/` sin página que escribe en la base** (A‑2), y `ui/resultado.py`, un fragmento de Streamlit sin `sqlalchemy.orm` ni `core.costing`. `ui/composicion.py` sigue siendo puro: solo gana `desglose` (`calcular_apu`, también puro). Así `componer.py` deja de orquestar «cantidades → elaborar → exportar», de calcular y de persistir.
- **`core/` cambia exactamente dos veces**, cada una en un commit propio que solo toca `core/` (y sus pruebas en `tests/`), con expediente previo y la línea base intacta:
  - el de INV‑080 en `core/budget/` (Tarea 11), con sus llamadores de `api/` en commits separados;
  - el de INV‑015 7a (Tarea 12): la tabla `descarte_version`, `descartar_version(...)` en `core/budget/actualizacion.py` y el docstring de `core/catalog/sesion.py`. El botón va en un commit de `ui/` aparte.
- **`ml/` solo modifica archivos existentes.** INV‑081 agrega `FALLAS_DE_LA_PROPUESTA`, `Propuesta`, `proponedor` y `propuestas_para` dentro de `ml/normalization/normalizador.py`, que ya existe. **Ningún archivo nuevo** bajo `ml/` ni `adapters/` (Review Focus 1).
- **`scripts/`:** INV‑044, INV‑049, INV‑050, INV‑051 e INV‑075.
- **`tests/`:** INV‑019 a INV‑025 e INV‑052.

**Tech Stack:** Python 3.13 (`.python-version`) · Streamlit 1.62.0 (`st.navigation`, `AppTest`) · SQLAlchemy 2 · FastAPI (`TestClient`) · sentence-transformers (extra `ml`) · pytest (`-W error --strict-markers`) · ruff · uv

**Spec:** [docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md](../specs/2026-09-23-plan-cierre-tesis-design.md). Mandan:
- §2, el límite;
- §4, los criterios y la regla de las capas cruzadas;
- §5, la fila C3 con las dos excepciones de `core/` (INV‑080 e INV‑015 7a; la segunda la agrega la Tarea 1) y la enmienda GU1a/GU1b;
- §6, la organización y la ratificación;
- §10, la enmienda del 2026‑09‑24 y la de apertura de C3 (Tarea 1).

**Plan que ejecuta:** [docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md](2026-09-23-ui-recorrido-guiado-u0-u1.md), Tareas 7 a 12, enmendado en la Tarea 1.

**Otros documentos:** plan de fases [PLAN_CIERRE.md](../../../PLAN_CIERRE.md) · inventario [docs/auditoria/2026-09-inventario.md](../../auditoria/2026-09-inventario.md) · bitácora `docs/bitacora/2026-09-23-cierre.md` · expedientes de C3 en `docs/bitacora/2026-09-24-C3-expedientes.md` (nuevo, lo crea la Tarea 11).

**Rama y worktree:** `inc/cierre-C3` en `.claude/worktrees/cierre-C3`, creada desde `main` = `58ee828`, el merge del PR #13 de C2 (etiqueta `gc2`). Con D3 se abren tres sub‑worktrees transitorios (sección «Orquestación por roles»).

---

## Hechos verificados al planificar (sobre `dd5a13a`; revisados el 2026‑09‑24 sobre `main` = `58ee828`)

Contradicen o precisan el encargo; mandan sobre el resto del plan. `git diff --stat dd5a13a 58ee828 -- core/ ui/ api/ ml/ scripts/ tests/` sale vacío: entre la planificación y la apertura de C3 solo cambiaron documentos, así que las anclas de código siguen vigentes. **Aviso (GC3):** las anclas de los Hechos 3, 5, 8, 11 y 12, las de la tabla «Anclas del plan de UI» y `docs/manual_tecnico.md:350` (Mapa de archivos) son las de `58ee828`, y C3 las desplazó o consumió: no se citan desde `HEAD`; siguen vigentes en `HEAD` los Hechos 4, 6 y 7 y `core/budget/escenarios.py:71-111` (Hecho 11).

1. **Resuelto: `inc/tesis-cap4` está en `main`.**
   - Es el PR #12, merge `5630f5b` del 2026‑09‑24; `git merge-base --is-ancestor inc/tesis-cap4 main` da éxito sobre `58ee828`.
   - `main` tiene INV‑074 a INV‑078 y `docs/tesis/capitulos/04-desarrollo.md`. INV‑075 **no** está bloqueado.
   - Las funciones puras R4–R8 de `scripts/meta_redaccion.py`, aplicadas a ese capítulo IV y al `referencias.md` de `main`, dan las cinco OK. Extenderlas no rompe hoy la meta 12/12.
2. **Resuelto: C2 está fusionado en `main`** (`58ee828`, PR #13, etiqueta `gc2`), sin conflicto pendiente. El inventario de `main` integra las dos series: `grep -c "^| INV-0\(7[4-9]\|8[0-2]\) " docs/auditoria/2026-09-inventario.md` da `9`, y el inventario tiene 82 filas, INV‑001 a INV‑082.
3. **Resuelto: `main` no tiene ningún `print(` en `api/rutas/presupuestos.py`.** `git show main:api/rutas/presupuestos.py | grep -n "_registro.warning\|print("` da solo `372` y `383`, las dos con `_registro.warning(`. La mutación que se vio en el worktree de C2 no llegó a `main`.
4. **7a de INV‑015 exigía `core/` más allá de la excepción de INV‑080** (resuelto por D1 = A).
   - El expediente B.8 (`docs/bitacora/2026-09-23-C1-expedientes.md:321-338`) y la fila INV‑015 exigen «una función del núcleo» para 7a.
   - La enmienda del 2026‑09‑24 declaraba a INV‑080 «la única excepción a `core/` sin cambios» en C3.
   - `models.Presupuesto` no tiene columna de estado (`core/models/entidades.py:266-300`). «Se marca como descartada» (`docs/ERS.md:170`) exige un dato persistido nuevo: la tabla `descarte_version` de la Tarea 12. La Tarea 1 enmienda §5 y §10 para la segunda excepción.
5. **INV‑076 no cabe en C3** (D2: no se escribe su código aquí):
   - la importación de un presupuesto de tercero pide un analizador que construya `Presupuesto`, con APU y plan;
   - pide una ruta o un control nuevos, que spec §2 llama capacidad nueva si no están en la ERS;
   - la postcondición de UC‑05 («informe persistido») choca con `guardar_presupuesto`, que exige que cada partida exista en el catálogo (`core/budget/persistencia.py:71`).
6. **La guardia del núcleo mira las ramas fusionadas.** `scripts/meta_alpha.py:449-481` (`_ramas_adaptador`) marca FALLA si una fusión de la línea principal **agrega** un archivo bajo `adapters/` o `ml/` y el rango cambia `core/`. C3 cambia `core/`, así que **ningún commit de C3 puede agregar un archivo bajo `ml/` ni `adapters/`**. La CI corre esa guardia (`.github/workflows/ci.yml:55-71`).
7. **La meta P8 del prototipo depende de un literal.** P8 (`scripts/meta_prototipo.py:216-224`)
   busca el literal `'ui.paginas.componer'` en `tests/unit/test_ui_importable.py`. La reescritura de
   la Tarea 10 del plan de UI lo borra, y P8 pasaría de OK a PENDIENTE (la meta, de 12/12 a 11/12;
   hoy 12/12, comprobado).
8. **`tests/unit/test_guion_prueba_arenia.py:115-121` fija que CP‑07 «no es ejecutable hasta U1».** La Tarea 12 de UI debe reescribirla a propósito.
9. **El paso 7 de la Tarea 6 de UI (qué hacer con `UI-01-TUB` en `.claude/worktrees/prototipo/data/apu.db`) no constaba decidido** en ninguna bitácora de C1. Resuelto por D7 = (b): base sucia de un worktree retirado; no se ejecuta nada sobre ella.
10. **INV‑052 exige editar archivos protegidos:** `tests/integration/test_composicion_extremo_a_extremo.py`, que el plan de UI declara intocable, y `tests/integration/test_auditoria_7_de_7.py`, del conjunto de la línea base. Solo se mueven ayudas, sin tocar aserciones. La Tarea 1 enmienda la restricción.
11. **Ningún módulo de `ui/` llama a `guardar_presupuesto` ni a `cargar_elaboracion`; `ui/paginas/escenarios.py` sí llama a `cargar_presupuesto`** (`:31` lo importa, `:93` lo llama), solo para UC‑08. La API hace lo mismo en `api/rutas/presupuestos.py:260`. `generar_escenario` (`core/budget/escenarios.py:71-111`) reelabora solo los renglones valorados, así que un escenario sobre un base con pendientes no los declara: es la pérdida de INV‑080 por la ruta de UC‑08, y D4 = A (recarga y `actualizar_precios`) no la cubre. Se registra como **INV‑083** (Tarea 1, paso 7).
    - **Decisión, leído el código:** `cargar_presupuesto` devuelve el contrato `Presupuesto`, que no tiene pendientes y es estable (CLAUDE.md §5). Pero `cargar_elaboracion`, pública en `core.budget` desde el commit de INV‑080, devuelve `ResultadoElaboracion` con `pendientes`. Basta con que `ui/paginas/escenarios.py` la use y muestre los pendientes del base: INV‑083 se corrige en C3 **dentro de `ui/`**, en la Tarea 11, paso 8 (pista A, tras fusionar B), con su rojo y su mutación, y **sin un tercer commit de `core/`**.
    - Queda fuera: que el informe del propio escenario (`Escenario.informe`) lleve el hallazgo `PENDIENTE` exigiría cambiar `generar_escenario` (tercer commit de `core/`), y la ruta de la API necesitaría un campo nuevo en `EscenariosRespuesta`. Las dos cosas van al dictamen C3‑12 con fase C4, y las decide Eugenio en GC3.
    - INV‑080 llega a la interfaz, además, por `actualizar_precios` (página de actualización), porque D4 = A hace que esa función conserve los pendientes; ahí no hay commit de `ui/`.
12. **El `RuntimeError` de pesos corruptos rompe la página de similares.** `ui/paginas/similares.py:80-88` atrapa solo `OSError`: con `RuntimeError` la página muestra una traza. `ui/composicion.py:618-623` atrapa `Exception`. Es la divergencia observable de INV‑081.

## Decisiones tomadas (Eugenio, 2026‑09‑24)

Vinculantes. La Tarea 0, paso 5, las copia en el ledger de la pista A y la Tarea 1, paso 7, en la bitácora. Cada una se ratifica con su costo en GC3 (dictámenes de la Tarea 18, paso 6).

1. **D1 = (A): segunda excepción de `core/` para INV‑015 7a, en un commit propio** (Tarea 12).
   - `core/models/entidades.py`: tabla nueva `descarte_version` (`presupuesto_id` único, `fecha`). La crea `crear_esquema` (`create_all`) en las bases existentes sin alterar las demás tablas: no es migración. `core/models/__init__.py` la exporta.
   - `core/catalog/sesion.py:31` y el docstring de `core/models/entidades.py:1`: «quince» pasa a «dieciséis».
   - `core/budget/actualizacion.py`: `descartar_version(...)`, exportada en `core/budget/__init__.py`.
   - El botón «Descartar version» de la página de actualización va en un commit de `ui/` aparte.
   - La Tarea 1 enmienda la fila C3 de la spec §5 y §10 para las **dos** excepciones. Los lugares de la excepción son la spec, `PLAN_UI.md` y la guardia de la Tarea 18, paso 3.
   - La compuerta GC3 = GU1a espera **exactamente dos** commits que tocan `core/` (INV‑080 e INV‑015 7a), cada uno solo con `core/` y sus pruebas, y la línea base intacta.
   - Costo si es errónea: el núcleo se reabre una segunda vez y queda una tabla de más; se revierte el commit de 7a y el de `ui/`, y 7a vuelve a abierto.
2. **D2 = recomendada: C3 no escribe código de INV‑076** (RF‑24, UC‑05).
   - RF‑24 existe, así que por la primera viñeta de §2 es corrección; pero la ruta `POST /presupuestos/importar` y la pantalla que propone la fila no están en la ERS: por la segunda viñeta, capacidad nueva. Queda **en duda**.
   - Diseño propio (superpowers:brainstorming) del formato tabular, la capa del analizador y la persistencia, **fuera de C3**. INV‑076 cruza GC3 **abierto**. La Tarea 1, paso 7, lo registra en el inventario.
   - Costo si es errónea: RF‑24 (Esencial) sigue sin implementar al cruzar GC3; F3 no se alcanza sin cerrarlo o sin la enmienda de §2 con visto bueno del tutor.
3. **D3 = (sí): tres sub‑worktrees transitorios.**
   - CLAUDE.md §3 admite solo el checkout principal y el worktree del sprint; Eugenio pidió acelerar y autoriza la excepción **solo para C3**.
   - Salen de `inc/cierre-C3` tras el tercer commit de la Tarea 1 (paso 8, la ayuda de subproceso) y vuelven a ella con `--no-ff` antes de la Tarea 18. No hay PR propio: la fusión es local. Cada uno se borra al fusionar.
   - Costo si es errónea: conflictos de fusión locales; se resuelven en `inc/cierre-C3` antes de la Tarea 18.
4. **D4 = (A): INV‑080 amplio.** El commit de `core/budget/` hace que la recarga (`cargar_elaboracion`) **y** `actualizar_precios` conserven los pendientes del presupuesto. Costo si es errónea: `actualizar_precios` cambia de comportamiento con pendientes; lo cubre la prueba 4 de la Tarea 11.
5. **D5 = (A): 11b + 11c.** 11b saca la orquestación «cantidades → elaborar → exportar» a `ui/elaboracion.py`. 11c saca también el cálculo (`calcular_apu`, a `ui/composicion.desglose`, que es puro) y la persistencia (`cargar_composicion` y `reemplazar_composicion`, a `ui/elaboracion.guardar_composicion`: `ui/composicion.py` no escribe en la base, A‑2), para que `componer.py` no importe `core.costing`, `core.budget` ni `sqlalchemy.orm` en tiempo de ejecución (evidencia S, spec §4). Costo si es errónea: una extracción más amplia que la corrección literal de la fila; la protegen las 9 pruebas de `test_ui_componer.py`.
6. **D6 = recomendada: selector de propuestas y botón «Aplicar y volver a elaborar».** Por cada ítem pendiente. Realiza «si no se acepta ninguna…» de UC‑01 3a (`docs/ERS.md:139-140`) en la página existente (Tarea 7). Costo si es errónea: un control más en la página de elaborar, dentro del flujo que la ERS ya describe.
7. **D7 = (b): `UI-01-TUB`.** La base `.claude/worktrees/prototipo/data/apu.db` se declara **base sucia de un worktree retirado**, y **no se ejecuta nada sobre ella**: ni siembra, ni `--reiniciar`, ni borrado. Costo si es errónea: esa base conserva la partida de prueba; no afecta a `main` ni a la CI.

---

## Global Constraints

- **`core/` cambia exactamente en los dos commits que autoriza §5** (enmendada por la Tarea 1), cada uno con expediente previo en `docs/bitacora/2026-09-24-C3-expedientes.md`, commiteado antes, y con la línea base (1 586,61 USD y 7 de 7) intacta:
  - `fix(budget): la recarga del informe conserva los items pendientes` (INV‑080, Tarea 11): solo `core/budget/*` más sus pruebas en `tests/`.
  - `feat(budget): descartar la version revalorada conserva el historial` (INV‑015 7a, Tarea 12): solo `core/models/entidades.py`, `core/models/__init__.py`, `core/catalog/sesion.py`, `core/budget/actualizacion.py` y `core/budget/__init__.py`, más sus pruebas en `tests/`.
  - Cualquier otra necesidad de `core/` **detiene la tarea**: va a expediente y a una fila nueva del inventario, sin parche (CLAUDE.md §9).
- **Ningún commit mezcla `core/` con otra capa** salvo `tests/`, ni `core/` con `adapters/` o `ml/`. Los llamadores de `api/` y `ui/` van en commits aparte.
- **Ningún archivo nuevo bajo `ml/` ni `adapters/`.** `git diff --name-only --diff-filter=A $(git merge-base main HEAD)..HEAD -- adapters ml` debe salir vacío (Hecho 6). Se comprueba después de cada fusión de un sub‑worktree y en la Tarea 18, con `scripts/guardia_nucleo.py` también contra una fusión de prueba en `main` (el guion `guardia_gc3.sh`, sección «Orquestación por roles»): en `inc/cierre-C3` la guardia no ve un archivo agregado desde una subrama sin `core/`, y la CI del PR sí (QA‑3).
- **`adapters/` no cambia.** `api/` y `ml/` solo cambian en los commits de las Tareas 10 y 11. La restricción global del plan de UI sobre `api/` ya no aplica (spec §5).
- **Línea base y fixtures:**
  - `tests/fixtures/apu_linea_base.py` no se edita.
  - `tests/integration/test_composicion_extremo_a_extremo.py` y `tests/integration/test_auditoria_7_de_7.py` solo cambian por INV‑052: se mueven ayudas y **ninguna aserción cambia**. Se verifica con `git diff -U0` en la Tarea 8.
- **Ninguna prueba escribe en `data/apu.db`.** La salvaguarda de sesión (`tests/conftest.py:53`, `_base_real_intacta`) lo hace cumplir, y `tests/unit/test_salvaguarda.py` la vigila con 4 pruebas. Toda base vive en `tmp_path`. Si la salvaguarda salta, se bisecta por archivo y se corrige la prueba. Nunca se relaja.
- **Ninguna prueba del plan puede alcanzar una base de `data/`** (QA‑9). La salvaguarda solo **detecta**, y solo sobre `data/apu.db`; no vigila `data/apu_industrial.db`, `data/apu_sistemas.db` ni `data/apu_telecom.db`. Por eso toda prueba que llame al `main()` de un script con `--reiniciar` o con la ruta por defecto hace, **antes** de llamarlo, `monkeypatch.chdir(tmp_path)` y afirma que `Path(modulo.RUTA_POR_DEFECTO).resolve()` queda dentro de `tmp_path.resolve()`. Si esa aserción falla, la prueba se detiene antes de cualquier `drop_all`.
- **Ninguna prueba nueva importa de otro módulo `test_*.py`** (A‑6, regla de INV‑052 desde la Tarea 1). Lo compartido va a `tests/fixtures/`. Vale para las cuatro pistas: la prueba de arquitectura de la Tarea 8 recorre todo `tests/` y pondría la rama en rojo al fusionar.
- **`Decimal` en todo lo monetario y dimensional** (principio 3). Única excepción declarada: el puntaje `float` de UC‑03 (`ml/normalization/normalizador.py:13-15`).
- **Reglas de interfaz del plan de UI, vigentes:**
  - `ui/composicion.py` no importa `ui.caso`, `streamlit` ni `pandas`, ni escribe en la base. `ui/elaboracion.py` no importa `ui.caso`, `streamlit` ni `pandas`. `ui/resultado.py` no importa `sqlalchemy.orm` ni `core.costing`. Las tres reglas, y la de `componer.py`, las hace cumplir **una** prueba parametrizada de `tests/unit/test_arquitectura.py` (`test_ui_respeta_sus_importaciones_prohibidas`, Tarea 6, paso 8), que reutiliza `_imports_de_ejecucion` (A‑9).
  - Ningún módulo de `ui/` construye objetos de Streamlit al importarse.
  - El literal del flag de reinicio no aparece en ningún archivo de `ui/`.
  - Los textos nuevos de la interfaz van sin tildes.
- **TDD con fase roja observada por comportamiento.** Un `ImportError` solo no basta. Cuando la función es nueva, se acompaña de una **mordida** tras el verde: una mutación temporal que la prueba detecta, y que se restaura. Cuando la capacidad ya existe y solo se endurece la prueba, la mutación se observa en las dos direcciones: la aserción vieja pasa con el defecto y la nueva falla.
- **Oráculos independientes:** otra ruta de código, la fixture de la línea base o aritmética escrita a mano y documentada. Nunca la misma función que se prueba.
- **Recuento con `--junitxml`** («el recuento»):

```bash
uv run pytest -W error --strict-markers -q -p no:cacheprovider --junitxml=reporte-pruebas.xml; uv run python scripts/verificar_omitidas.py reporte-pruebas.xml; uv run python -c "import xml.etree.ElementTree as E; r=E.parse('reporte-pruebas.xml').getroot(); s=r if r.tag=='testsuite' else r.find('testsuite'); print(s.get('tests'), s.get('failures'), s.get('errors'), s.get('skipped'))"
```

  Imprime `N 0 0 0` y `verificar omitidas: 0 omitidas`.
- **Artefactos reproducibles.** `docs/api.json` se regenera (`scripts/exportar_openapi.py`) si cambia un esquema o un docstring de ruta. La CI lo compara con `git diff --exit-code`.
- **Metas de sprint, sin regresión:** `scripts/meta_prototipo.py` 12/12, `scripts/meta_redaccion.py` 12/12 y `scripts/meta_datos.py` OK, antes y después.
- **Suite y lint:** `uv run pytest -W error --strict-markers` verde, sin `filterwarnings` ni marcadores nuevos. `uv run ruff check .` limpio, con línea de 100 caracteres. CI verde en `ubuntu-latest` y `windows-latest`, sin omitidas.
- **Commits:** Conventional Commits en español sin tildes en el asunto, terminados con `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- **IDs nuevos del inventario:** INV‑083 lo abre la Tarea 1, paso 7 (A‑1); los que aparezcan durante la fase, desde INV‑084.
- **Bitácora e inventario tienen un solo dueño**, el controlador de la pista A:
  - Las pistas B, C y D escriben en su ledger (`.superpowers/sdd/2026-09-24-cierre-c3/<pista>.md`, sin versionar), y el controlador consolida en la Tarea 18.
  - Excepción: `docs/bitacora/2026-09-24-C3-expedientes.md` es de la pista B.
- **Regla de reparto** (spec §2): por cada sesión de código, al menos una de redacción. Se anota en la Tarea 18 (g).
- **Alcance congelado.** Toda duda se registra y la decide Eugenio en GC3.
- **Push y PR solo con permiso expreso de Eugenio.**

## Review Focus

1. **Las dos excepciones de `core/` son exactas y no disparan la guardia de ramas.**
   - Exactamente dos commits tocan `core/`: el de INV‑080 (solo `core/budget/*`) y el de INV‑015 7a (solo los cinco archivos de la Tarea 12), ninguno con otra capa salvo `tests/`. La línea base sigue en `27 0 0 0`, el mismo conjunto que GC1 y GC2.
   - La tabla `descarte_version` es aditiva: `crear_esquema` la agrega a una base existente sin tocar las otras quince, y ninguna prueba de persistencia previa cambia (el diff de `test_persistencia.py` y `test_actualizacion_precios.py` solo agrega líneas, salvo las dos líneas de import de `test_persistencia.py` que ruff amplió con `inspect` y `crear_esquema`: Tarea 18, paso 3, QA‑20). Su clave foránea lleva `ondelete="CASCADE"` (A‑11).
   - Ninguna fusión cambia `core/` por su cuenta: `git diff-tree --cc` de cada fusión sobre `core/` sale vacío (A‑7, QA‑2).
   - Ningún archivo agregado bajo `ml/` ni `adapters/` en toda la rama, ni en los sub‑worktrees. Si se agregara, la fusión en `main` haría fallar `guardia_nucleo.py` en la CI (Hecho 6). Se comprueba después de cada fusión y en la Tarea 18, también contra una fusión de prueba en `main` (QA‑3).
   - El ayudante de INV‑081 va **dentro** de `ml/normalization/normalizador.py`.
2. **La página por defecto devuelve `url_path == ""`** (Review Focus 1 del plan de UI). `ruta_actual("")` la traduce a `inicio`.
3. **INV‑043 conserva el comportamiento.**
   - Las 9 pruebas de `tests/unit/test_ui_componer.py` siguen verdes. Solo cambia el arnés de la Tarea 11, paso 4.
   - Los rótulos y las claves de `st.session_state` (`componer_resultado_elaboracion`, `componer_libro_excel`, `componer_cantidades`…) no cambian.
   - Una prueba de arquitectura nueva fija qué importa `componer.py` en tiempo de ejecución.
4. **INV‑080, recarga fiel al documento emitido.**
   - El informe recargado tiene los mismos hallazgos que el emitido: regla, severidad y `origen_ids`.
   - El oráculo es doble: los hallazgos de `elaborar` en memoria y los **persistidos** del documento emitido (`modelo.hallazgos`, como en `tests/integration/test_presupuesto_linea_base.py:95-107`).
   - Los presupuestos guardados **antes** del cambio no tienen pendientes persistidos: la recarga no los inventa. Queda declarado en el docstring y en el dictamen C3‑3.
   - `actualizar_precios` arrastra los pendientes (D4 = A).
   - El comparativo (`_comparar`, `zip(strict=True)`) solo recorre las partidas valoradas: lo afirma la prueba 4 de la Tarea 11, sin `ValueError`.
   - INV‑083: la página de escenarios declara los pendientes del base (Tarea 11, paso 8), sin tercer commit de `core/`.
5. **INV‑081 cambia el comportamiento en tres lugares.**
   - La ayuda 1 de componer deja de tragarse `Exception`: solo las cuatro fallas declaradas se tratan como «sin propuestas», y un `KeyError` se propaga (prueba en rojo de C3‑4).
   - La página de similares muestra `st.error` ante `RuntimeError`, sin traza.
   - Los avisos de la API pasan al registrador de `ml.normalization.normalizador`: las pruebas `caplog` de `tests/integration/test_api.py:426-534` se reescriben a propósito, y los dobles de `:365`, `:406`, `:441`, `:517` y `:547` también (QA‑4).
   - Un solo normalizador por llamada, y el emparejamiento de pendientes con propuestas en un solo lugar (`ml.normalization.propuestas_para`), que comparten la API y `ui/` (A‑4).
6. **Regresiones de metas y guion.**
   - P8 sigue OK: el literal `ui.paginas.componer` se conserva.
   - `test_cp07_se_declara_no_ejecutable_hasta_u1` se reescribe declarando que CP‑07 **ya** es ejecutable y que su medición es de Med (GU1b).
   - `test_toda_orden_de_siembra_lleva_su_propia_base` sigue verde.
7. **INV‑050 cambia la CLI.**
   - `--reiniciar` sobre la ruta por defecto se niega sin `--confirmar`: código 2, mensaje en `stderr` y la base intacta.
   - La preparación del guion usa `--db data/prueba_arenia.db --reiniciar` (`docs/guion_prueba_arenia.md:79`), que no es la ruta por defecto: no cambia.
8. **INV‑022.** El arranque real de la aplicación desvía la base por `ui.caso`, y la prueba lo **afirma**: la leyenda lateral muestra el temporal y la huella de `data/apu.db` no cambia. El Inicio no crea el archivo (`estado_caso` no crea), así que la prueba no espera que el temporal exista.
9. **Fusiones de sub‑worktrees** (D3). Cada una va con `--no-ff`. Después de cada fusión, el recuento y el guion `guardia_gc3.sh` con el número de commits de `core/` esperados en ese momento: `git diff-tree --cc` de la fusión sobre `core/` vacío, `--diff-filter=A` sobre `ml/` y `adapters/` vacío, y `guardia_nucleo.py` en código 0 tanto en `inc/cierre-C3` como contra una fusión de prueba en `main` (QA‑2, QA‑3, A‑7).
10. **UC‑02 7a (INV‑015) fiel a la ERS.** Descartar **marca** la versión y conserva `CambioPrecio` e `IncidenciaCambio` (`docs/ERS.md:170`); nunca descarta el base, una versión que no sea la última ni una ya descartada; el botón solo aparece tras guardar una versión en esta ejecución.
11. **D7.** Ningún comando de la fase toca `.claude/worktrees/prototipo/data/apu.db`.

---

## Mapa de archivos

| Archivo | Tarea | Responsabilidad |
|---|---|---|
| `docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md`, `PLAN_UI.md`, spec de cierre (fila C3 de §5 `:155`, `:167` y §10), `PLAN_CIERRE.md:10-11`, este documento | 1 | Enmienda (primer commit) |
| `docs/bitacora/2026-09-23-cierre.md`, `docs/auditoria/2026-09-inventario.md` (fila INV‑076 y fila nueva INV‑083) | 1, 18 | Sección «Fase C3», registro de D2 y de INV‑083, y compuerta |
| `tests/fixtures/subproceso.py` (nuevo) | 1 | `importar_en_limpio`, la ayuda única para importar en un subproceso limpio (A‑13); tercer commit, antes de abrir los sub‑worktrees |
| `ui/recorridos.py`, `tests/unit/test_ui_recorridos.py` | 2 | Tarea 7 de UI |
| `ui/caso.py`, `tests/unit/test_ui_caso.py`, `tests/conftest.py` | 3 | Tarea 8 de UI |
| `ui/paginas/inicio.py`, `tests/unit/test_ui_inicio.py` | 4 | Tarea 9 de UI |
| `ui/app.py`, `tests/unit/test_ui_app.py`, `tests/unit/test_ui_importable.py` | 5 | Tarea 10 de UI, INV‑022, INV‑023 y P8 |
| `ui/paginas/*.py` (9), `ui/elaboracion.py` (nuevo), `ui/resultado.py` (nuevo), `ui/composicion.py`, `tests/unit/test_ui_componer.py`, `tests/unit/test_ui_app.py`, `tests/unit/test_ui_caso.py`, `tests/unit/test_arquitectura.py`, `tests/unit/test_composicion.py`, `tests/unit/test_elaboracion.py` (nuevo) | 6 | Tarea 11 de UI, INV‑044 (ui) e INV‑043 |
| `ui/elaboracion.py`, `ui/resultado.py`, `ui/paginas/elaborar.py`, `ui/paginas/componer.py` (firma nueva del fragmento), `tests/unit/test_ui_elaborar.py` (nuevo) | 7 | INV‑072 (ui) |
| `ui/paginas/componer.py`, `ui/composicion.py`, `ui/elaboracion.py`, `tests/fixtures/filas_composicion.py` (nuevo), `tests/fixtures/auditoria.py` (nuevo), `tests/unit/test_ui_componer.py`, `tests/integration/test_composicion_extremo_a_extremo.py`, `tests/integration/test_auditoria_7_de_7.py`, `tests/unit/test_arquitectura.py` | 8 | INV‑045, INV‑046 e INV‑052 |
| `docs/manual_usuario.md`, `docs/guion_prueba_arenia.md`, `docs/ERS.md`, `docs/plan_pruebas.md`, `tests/unit/test_guion_prueba_arenia.py` | 9 | Tarea 12 de UI |
| `ml/normalization/normalizador.py`, `ml/normalization/__init__.py`, `tests/unit/test_normalizacion.py` (10a, B) · `api/rutas/presupuestos.py`, `tests/integration/test_api.py` (10b, B) · `ui/composicion.py`, `ui/elaboracion.py`, `ui/paginas/componer.py`, `ui/paginas/similares.py`, `tests/unit/test_composicion_ia.py`, `tests/unit/test_ui_similares.py` (nuevo) (10c, A, **tras fusionar B y C**) | 10 | INV‑081 (tres commits). `test_composicion_ia.py` es de la pista C (Tarea 14) hasta su fusión; 10c lo edita después (A‑4) |
| `docs/bitacora/2026-09-24-C3-expedientes.md` (nuevo) · `core/budget/{persistencia,presupuesto,actualizacion,__init__}.py`, `tests/integration/test_recarga_con_pendientes.py` (nuevo) · `api/rutas/presupuestos.py`, `tests/integration/test_api.py`, `docs/api.json` (pista B) · `ui/paginas/escenarios.py`, `tests/unit/test_ui_escenarios.py` (nuevo) (paso 8, pista A, tras fusionar B) | 11 | INV‑080 e INV‑083 |
| `docs/bitacora/2026-09-24-C3-expedientes.md` (§C3.2) · `core/models/entidades.py`, `core/models/__init__.py`, `core/catalog/sesion.py`, `core/budget/actualizacion.py`, `core/budget/__init__.py`, `tests/integration/test_actualizacion_precios.py`, `tests/integration/test_persistencia.py` · `ui/paginas/actualizacion.py`, `tests/unit/test_ui_actualizacion.py` (nuevo) · `docs/modelo_datos.md`, `docs/arquitectura.md` | 12 | INV‑015 7a (D1 = A): expediente, commit de `core/`, commit de `ui/` y commit de documentos |
| `tests/unit/test_referencia_maprex.py`, `tests/unit/test_fuentes_arenaza.py`, `tests/integration/test_seed_demo.py`, `tests/unit/test_simulador.py` | 13 | INV‑019, INV‑020 e INV‑025 |
| `tests/fixtures/sin_extra.py` (nuevo), `tests/unit/test_visor3d.py`, `tests/unit/test_composicion_ia.py`, `tests/unit/test_extras_perezosos.py` (nuevo) | 14 | INV‑021 e INV‑024 |
| `scripts/seed.py`, `seed_demo.py`, `seed_industrial.py`, `seed_sistemas.py`, `seed_telecom.py`, `simular_lista.py`, `scripts/README.md`, `scripts/__init__.py`, `README.md:29-30`, `docs/manual_tecnico.md:225,350`, `tests/unit/test_reinicio_seguro.py` (nuevo), `tests/unit/test_scripts_documentados.py` (nuevo), `tests/unit/test_scripts_ruta_unica.py` (nuevo), `tests/unit/test_scripts_resumen.py` (nuevo) | 15 | INV‑044 (scripts), INV‑049, INV‑050 e INV‑051 |
| `scripts/meta_redaccion.py`, `tests/unit/test_meta_redaccion.py` | 16 | INV‑075 |
| `docs/auditoria/2026-09-inventario.md`, `docs/bitacora/2026-09-23-cierre.md`, `docs/bitacora/2026-09-23-sprint-ui.md` | 18 | Estados y compuerta GC3 = GU1a |

### Anclas del plan de UI, refrescadas contra `dd5a13a` (vigentes en `58ee828`)

C1 cambió `ui/` (`bdf7859`, INV‑069: `elaborar.py` y `componer.py`); C2 no la tocó. `main` no toca
`ui/` después de `f1dda36`, y entre `dd5a13a` y `58ee828` no cambió ningún archivo de código. La
Tarea 0, paso 2, las vuelve a comprobar.

| Plan de UI | Ancla vieja | Ancla vigente |
|---|---|---|
| T11 `catalogo.py` | `:32` | `:32` (constantes `:23-24`, `st.title` `:29`) |
| T11 `componer.py` | `:109` | **`:120`** (constantes `:77-78`, `st.title` `:112`) |
| T11 `escenarios.py` | `:57` | `:57` (`:42-43`, `:51`) |
| T11 `historico.py` | `:37` | `:37` (`:24-25`, `:31`) |
| T11 `similares.py` | `:69` | `:69` (`:39-40`, `:58`) |
| T11 `actualizacion.py` | `:107-108` | `:107-108` (`:46-47`, `:82`; diccionario `"ruta": Path(ruta)` `:123`) |
| T11 `elaborar.py` | `:98-99` | `:98-99` (`:37-38`, `:54`; diccionario `:110`) |
| T11 `simulador.py` | `:50-51` | `:50-51` (`:24-25`, `:32`) |
| T11 `visor.py` | — | `TITULO` `:49`, `st.title` `:76` |
| T11 `test_ui_componer.py` | `:14-30`, `:92-112` | docstring, hecho 2: **`:21-30`**; `_pantalla`: **`:91-113`** (parche `:100-101`, mensaje `:107-111`) |
| T10 `ui/app.py` | todo salvo `modo_entrega_activo` | vigente (`:1-135`; `modo_entrega_activo` `:104-112`) |
| T10 `test_ui_app.py` | reescritura | vigente: hoy 7 funciones (`:44`, `:49`, `:54`, `:60`, `:88`, `:94`, `:99`); `_aplicacion` `:80-85` (INV‑022) |
| T12 `manual_usuario.md` | `:99` | **tabla `:97-105`**; `:44`, `:174`, `:260`, `:290` |
| T12 `guion_prueba_arenia.md` | `:3`, `:73` | `:3`; preparación §4 **`:38-110`**; CP‑07 `:394-533`; «Archivo SQLite» en `:98`, `:133`, `:200`, `:211`, `:277`, `:316`, `:365` |
| INV‑043 | `componer.py:29,32,55,111-193,639-665,682-834` | `:29`, `:32`, `:54` (`calcular_apu`), `:110-192`, `:638-670` (`_guardar`), `:673-862` (orquestación UC‑01) |
| INV‑045 | `componer.py:56-57,471-476,521-553,668-670,848` | `:55-56` (importaciones), `:470-475`, `:514-558`, `:667-670`, `:848` |
| INV‑046 | `componer.py:752-762` | `:751-761` (`_celda_de_cantidad`); `ui/composicion.py:68-81` (`_texto`) |
| INV‑072 | `elaborar.py:225-226`; `componer.py:798-800` | `elaborar.py:225-226`; `componer.py:798-800` |
| INV‑081 | `api:352-391`; `ui/composicion.py:618-623`; `similares.py:80-88` | vigentes |

### ¿Corrección o capacidad nueva? (spec §2)

| Hallazgo | Apunta a | Veredicto |
|---|---|---|
| Tareas 7 a 12 de UI | UC‑12, RF‑36 a RF‑43 y RNF‑10 (ERS vigente) | no es capacidad nueva: U1 está en la ERS y en `PLAN_UI.md` (§2, tercera viñeta) |
| INV‑019 a INV‑025, INV‑052 | pruebas de RF existentes | corrección, en `tests/` |
| INV‑043, INV‑044, INV‑045, INV‑046 | criterios S y DRY (§4) | corrección; `ui/elaboracion.py` y `ui/resultado.py` son extracciones, no pantallas |
| INV‑072 (ui) | UC‑01 3a (`docs/ERS.md:139-140`), en la página existente | corrección; el selector de aceptación de D6 también (lo pide el mismo flujo) |
| INV‑080 | RF‑02 («al producir o cargar») | corrección, con la primera excepción de `core/` autorizada (§5 y §10) |
| INV‑083 | RF‑02 y UC‑08 (el informe siempre declara lo que falta), en la página existente | corrección en `ui/`, con `cargar_elaboracion` del commit de INV‑080; el informe del propio escenario y la ruta de la API, a C4 (dictamen C3‑12) |
| INV‑081 | DRY de UC‑03 | corrección, en tres capas y en commits separados |
| INV‑049, INV‑051 | DRY y documentación | corrección |
| INV‑050 | pérdida de datos (cara de código de INV‑065) | corrección: `--confirmar` es una opción de CLI, no un UC, RF, RNF, pantalla ni ruta |
| INV‑075 | trazabilidad de la rúbrica (metas R4–R8) | corrección, en `scripts/` |
| INV‑015 7a | UC‑02 7a (`docs/ERS.md:170`) | corrección por su fuente, con la segunda excepción de `core/` (D1 = A; la Tarea 1 enmienda §5 y §10). La tabla `descarte_version` es aditiva, no una migración de esquema (§2): se anota como dictamen C3‑1 |
| INV‑076 | RF‑24 (existe), con ruta y pantalla nuevas | **en duda**: C3 no escribe su código (D2); diseño propio fuera de C3 |

---

## Orquestación por roles

**Roles de implementación** (un subagente por tarea; spec §6):

| Rol | Alcance |
|---|---|
| Controlador | Tareas 0, 1 y 18; dueño de la bitácora, del inventario y de las fusiones |
| Implementador de interfaz | `ui/` y sus pruebas `AppTest` |
| Implementador de núcleo | `core/budget/`, y en la Tarea 12 `core/models/` y el docstring de `core/catalog/sesion.py` |
| Implementador de API | `api/` y `docs/api.json` |
| Implementador de ML | `ml/normalization/` |
| Implementador de pruebas | `tests/` sin código de producción |
| Implementador de scripts | `scripts/` |
| Redactor técnico | documentos normativos y expedientes |

**Los cuatro encargos** (norma de cada uno: Tarea 18, paso 7): requisitos (IEEE 830), arquitectura (vistas 4+1 y CLAUDE.md §2/§5/§9), pruebas y calidad (IEEE 829 e ISO/IEC 25010) y verificación de hechos (cada `archivo:línea` y cada cifra). En cada tarea revisa al menos un encargo, el que la cierra. Al final de la fase revisan los cuatro en paralelo.

| Tarea | Implementador | Encargo que la cierra | Pista |
|---|---|---|---|
| 0 Punto de partida | Controlador | verificación de hechos | A |
| 1 Enmienda (primer commit) | Redactor técnico | requisitos + verificación de hechos | A |
| 2 Tarea 7 de UI | Interfaz | pruebas y calidad | A |
| 3 Tarea 8 de UI | Interfaz | pruebas y calidad (aislamiento) | A |
| 4 Tarea 9 de UI | Interfaz | requisitos (RF‑40) + pruebas | A |
| 5 Tarea 10 de UI + INV‑022/023 | Interfaz | arquitectura + pruebas | A |
| 6 Tarea 11 de UI + INV‑043/044 | Interfaz | arquitectura (S, DRY) + pruebas | A |
| 7 INV‑072 (ui) | Interfaz | requisitos (UC‑01 3a) + pruebas | A |
| 8 INV‑045/046/052 | Interfaz y pruebas | pruebas y calidad | A |
| 9 Tarea 12 de UI | Redactor técnico | requisitos + verificación de hechos | A |
| 10a INV‑081 (ml) | ML | arquitectura (regla de `ml/`, sin archivo nuevo) | B |
| 10b INV‑081 (api) | API | pruebas | B |
| 10c INV‑081 (ui) | Interfaz | pruebas | A (tras 6, 7 y las fusiones de B y C) |
| 11 INV‑080 (expediente, core, api) e INV‑083 (ui, paso 8) | Redactor técnico → núcleo → API → interfaz | arquitectura + requisitos (RF‑02, UC‑08) + pruebas | B (pasos 1 a 7) y A (paso 8, tras la fusión de B) |
| 12 INV‑015 7a (D1 = A) | Redactor técnico → núcleo → interfaz → redactor técnico | requisitos (fidelidad a la ERS) + arquitectura | B (expediente y núcleo) y A (ui y documentos, tras 6 y la fusión de B) |
| 13 INV‑019/020/025 | Pruebas | pruebas y calidad | C |
| 14 INV‑021/024 | Pruebas | pruebas y calidad | C |
| 15 INV‑044 (scripts), INV‑049, INV‑050, INV‑051 | Scripts | arquitectura (DRY) + pruebas | D |
| 16 INV‑075 | Scripts | pruebas + verificación de hechos | D |
| 17 INV‑076 (D2: sin código) | Controlador (solo registro) | requisitos (§2) | A |
| 18 Compuerta GC3 = GU1a | Controlador | los cuatro, en paralelo | A |

**Pistas en paralelo (D3 ratificada).** Cada una sale de `inc/cierre-C3` tras el tercer commit de la Tarea 1 (paso 8) y no comparte archivos con las demás mientras está viva:

- **A:** `inc/cierre-C3` en `.claude/worktrees/cierre-C3`. Tareas 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9, más 11 (paso 8, INV‑083), 12 (ui y documentos), 10c y 17. Toca `ui/`, `tests/unit/test_ui_*`, `tests/unit/test_elaboracion.py`, `tests/unit/test_composicion.py`, `tests/conftest.py`, los documentos normativos, la bitácora y el inventario; y `tests/unit/test_composicion_ia.py` **solo** en 10c, después de fusionar C.
- **B:** `inc/cierre-C3-nucleo` en `.claude/worktrees/cierre-C3-nucleo`. Tareas 11 (pasos 1 a 7) → 10a → 10b → 12 (expediente y núcleo). Es la única que toca `core/`, `api/`, `ml/`, `tests/integration/test_api.py`, `tests/integration/test_actualizacion_precios.py`, `tests/integration/test_persistencia.py`, `tests/unit/test_normalizacion.py` y `docs/api.json`. Concentrar ahí todos los cambios de `api/rutas/presupuestos.py` (INV‑080 e INV‑081) y de `core/budget/actualizacion.py` (INV‑080 e INV‑015 7a) evita conflictos.
- **C:** `inc/cierre-C3-pruebas` en `.claude/worktrees/cierre-C3-pruebas`. Tareas 13 y 14. Solo toca `tests/`, en archivos que ninguna otra pista edita mientras C está viva (`test_composicion_ia.py` pasa a A cuando C se fusiona).
- **D:** `inc/cierre-C3-scripts` en `.claude/worktrees/cierre-C3-scripts`. Tareas 15 y 16. Solo toca `scripts/`, `README.md`, `docs/manual_tecnico.md` y archivos de prueba **nuevos** con nombre fijado (`test_reinicio_seguro.py`, `test_scripts_documentados.py`, `test_scripts_ruta_unica.py`, `test_scripts_resumen.py`), además de `tests/unit/test_meta_redaccion.py`. La Tarea 20 de UI (`test_seed_demo.py`) queda en C, y D no lo toca; tampoco `test_arquitectura.py`, que es de A (A‑5).

**Guion de la guardia (`guardia_gc3.sh`).** El controlador lo guarda, sin versionar, en `.superpowers/sdd/2026-09-24-cierre-c3/guardia_gc3.sh` y lo corre con `bash`. El argumento es el número de commits de `core/` que se esperan en ese momento: `0` antes de fusionar B y `2` después (y en la Tarea 18). Termina con `exit 1` ante cualquier marca, así que el veredicto no depende de leer la salida (QA‑2):

```bash
#!/usr/bin/env bash
# Guardia de C3: las dos excepciones de core/ exactas, ninguna fusion que cambie core/ por su
# cuenta y ningun archivo nuevo bajo ml/ ni adapters/, en la rama y contra main (Tarea 18, paso 3).
set -u
ESPERADOS=${1:-2}
ASUNTO_080="fix(budget): la recarga del informe conserva los items pendientes"
ASUNTO_7A="feat(budget): descartar la version revalorada conserva el historial"
PERMITIDOS_7A='^core/(models/entidades\.py|models/__init__\.py|catalog/sesion\.py|budget/actualizacion\.py|budget/__init__\.py)$'
B=$(git merge-base main HEAD)
CABEZA=$(git rev-parse HEAD)
marcas=0
toca_core=0
marca() { echo "$1"; marcas=$((marcas + 1)); }

echo "== commits sin fusion que tocan core/"
git log --no-merges --format="%h %s" "$B..HEAD" -- core/
git diff --stat "$B..HEAD" -- core/
[ -z "$(git diff --name-only "$B..HEAD" -- tests/fixtures/apu_linea_base.py)" ] \
  || marca "LINEA-BASE-EDITADA"

for c in $(git rev-list --no-merges "$B..HEAD"); do
  f=$(git show --name-only --format= "$c" | grep .)
  echo "$f" | grep -q '^core/' || continue
  s=$(git log -1 --format=%s "$c")
  echo "TOCA-CORE $c $s"
  toca_core=$((toca_core + 1))
  echo "$f" | grep -v '^core/\|^tests/' | grep -q . && marca "MEZCLA $c"
  case "$s" in
    "$ASUNTO_080")
      fuera=$(echo "$f" | grep '^core/' | grep -v '^core/budget/')
      [ -z "$fuera" ] || marca "FUERA-DE-080 $c $fuera";;
    "$ASUNTO_7A")
      fuera=$(echo "$f" | grep '^core/' | grep -Ev "$PERMITIDOS_7A")
      [ -z "$fuera" ] || marca "FUERA-DE-7A $c $fuera";;
    *) marca "NO-AUTORIZADO $c";;
  esac
done
[ "$toca_core" -eq "$ESPERADOS" ] \
  || marca "TOCA-CORE=$toca_core, se esperaban exactamente $ESPERADOS"
if [ "$ESPERADOS" -eq 2 ]; then
  n080=$(git log --no-merges --format=%s "$B..HEAD" -- core/ | grep -cxF "$ASUNTO_080")
  n7a=$(git log --no-merges --format=%s "$B..HEAD" -- core/ | grep -cxF "$ASUNTO_7A")
  [ "$n080" -eq 1 ] && [ "$n7a" -eq 1 ] || marca "ASUNTOS 080=$n080 7A=$n7a"
fi

# A-7 y QA-2: una fusion que resuelve un conflicto editando core/ no la ve el bucle anterior.
for m in $(git rev-list --merges "$B..HEAD"); do
  for a in $(git diff-tree --cc --name-only --format= "$m" -- core/); do
    marca "FUSION-TOCA-CORE $m $a"
  done
done

# Hecho 6 y QA-3: ningun archivo agregado bajo ml/ ni adapters/.
agregados=$(git diff --name-only --diff-filter=A "$B..HEAD" -- adapters ml)
[ -z "$agregados" ] || marca "AGREGADO-EN-ML-O-ADAPTERS $agregados"

# La guardia en la rama...
uv run --no-sync python scripts/guardia_nucleo.py --base main || marca "GUARDIA-EN-LA-RAMA"
# ...y contra main, como la evalua la CI del PR (QA-3): fusion de prueba en un worktree temporal
# fuera del repositorio, que se borra al terminar. El script se ejecuta desde ese worktree, asi
# que su RAIZ (y su git) es la fusion de prueba.
T=$(mktemp -d)
# RQ-3: limpiar tambien si se interrumpe (Ctrl-C o cuelgue) entre add y remove; si $T aun no es
# un worktree, el remove falla en silencio y se borra el directorio vacio.
trap 'git worktree remove --force "$T" 2>/dev/null || rm -rf "$T"; git worktree prune' EXIT
git worktree add --quiet --detach "$T" main
if git -C "$T" merge --no-ff --no-edit --quiet "$CABEZA"; then
  uv run --no-sync python "$T/scripts/guardia_nucleo.py" --base main \
    || marca "GUARDIA-CONTRA-MAIN"
else
  git -C "$T" merge --abort
  marca "FUSION-DE-PRUEBA-CON-MAIN-EN-CONFLICTO"
fi
git worktree remove --force "$T"

echo "marcas: $marcas"
[ "$marcas" -eq 0 ] || exit 1
```

**Protocolo de fusión.** Lo aplica el controlador en `cierre-C3`:

1. `git merge --no-ff inc/cierre-C3-<pista> -m "merge: pista <x> de c3"`.
2. Comprobar la fusión recién hecha antes de seguir:
   - `git diff-tree --cc --name-only --format= HEAD -- core/` sale vacío: la fusión no cambió `core/` por su cuenta (A‑7);
   - `git diff --name-only --diff-filter=A $(git merge-base main HEAD)..HEAD -- adapters ml` sale vacío (QA‑3);
   - el recuento, `N 0 0 0`;
   - `bash .superpowers/sdd/2026-09-24-cierre-c3/guardia_gc3.sh <n>`, con `<n>` = `2` si B ya está fusionada y `0` si no, en código 0. Incluye `guardia_nucleo.py` en la rama y contra una fusión de prueba en `main`.
   - Si algo falla, la fusión se deshace con `git reset --hard ORIG_HEAD` (solo local, sin push) y se corrige en la subrama.
3. Borrar el worktree y la rama local: `git worktree remove`, luego `git branch -d`.

El orden obligado: B se fusiona **antes** de 11 (paso 8), 12 (ui y documentos) y 10c; C también antes de 10c, porque 10c edita `tests/unit/test_composicion_ia.py`, que la Tarea 14 cambia (A‑4). D se fusiona cuando termina. Todas antes de la Tarea 18.

---

### Task 0: Punto de partida

**Files:** ninguno (el primer commit de la rama debe ser la enmienda, spec §5).

**Interfaces:**
- Consumes: `main` = `58ee828`, con C2 fusionada (PR #13, etiqueta `gc2`), y las decisiones tomadas D1 a D7.
- Produces: `N0` y el ledger de la pista A con las decisiones, que la Tarea 1 copia en la bitácora.

- [ ] **Step 1: Rama, base y estado**

Run: `git rev-parse --abbrev-ref HEAD && git merge-base --is-ancestor main HEAD && echo base-ok && git log --oneline -4 main && git status --short && (ls data/*.db 2>/dev/null || echo "sin bases locales") && git worktree list && git merge-base --is-ancestor inc/tesis-cap4 main && echo cap4-en-main && git tag --points-at 58ee828`

Expected:
- `inc/cierre-C3`, `base-ok` y `cap4-en-main`.
- En el log, `58ee828 merge: cierre c2 adaptadores ml y api (#13)` en la cabeza de `main`, y `gc2`
  como etiqueta de `58ee828`.
- `git status --short` sin más que este plan sin versionar (`?? docs/superpowers/plans/2026-09-24-cierre-c3-interfaz-scripts.md`).
- Anotar si `data/apu.db` existe y su fecha de modificación.
- Anotar los worktrees vivos; al planificar son cuatro (el checkout principal, `cierre-C3`, `prototipo` y `ui`). **No se borra ninguno**: lo decide Eugenio. Sobre `prototipo` no se ejecuta nada (D7).

- [ ] **Step 2: Hechos resueltos, comprobados sobre `main`**

Run:

```bash
grep -c "^| INV-0\(7[4-9]\|8[0-2]\) " docs/auditoria/2026-09-inventario.md
grep -c "^| INV-" docs/auditoria/2026-09-inventario.md
git show main:api/rutas/presupuestos.py | grep -n "_registro.warning\|print("
git diff --stat dd5a13a main -- core/ ui/ api/ ml/ scripts/ tests/
```

Expected:
- `9` y `82`: las series INV‑074 a INV‑078 e INV‑079 a INV‑082 conviven (Hecho 2).
- `372:` y `383:`, las dos con `_registro.warning(`, y ningún `print(` (Hecho 3).
- El `diff --stat`, vacío: las anclas de la tabla «Anclas del plan de UI» siguen vigentes. Si no sale vacío, se vuelven a comprobar una por una.

- [ ] **Step 3: Estado de partida en verde**

Run: `uv sync --locked --all-extras`, «el recuento» y `uv run ruff check .`.

Expected: `750 0 0 0` (N de GC2, bitácora (c) de C2; cap4 no tocó código) y `0 omitidas`. Si no es 750, se detiene y se registra la diferencia.

- [ ] **Step 4: Metas de referencia**

Run: `uv run python scripts/meta_prototipo.py; uv run python scripts/meta_redaccion.py; uv run python scripts/meta_datos.py`

Expected: 12/12, 12/12 y OK. Anotarlo.

- [ ] **Step 5: Decisiones.** Copiar en el ledger de la pista A (`.superpowers/sdd/2026-09-24-cierre-c3/A.md`) las decisiones D1 a D7 de la sección «Decisiones tomadas», con su fecha (2026‑09‑24) y su costo. No se vuelven a preguntar.

---

### Task 1: Enmienda del plan de UI y apertura de C3 (primer commit de la rama)

**Files:**
- Modify: `docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md`
- Modify: `PLAN_UI.md`
- Modify: `docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md` (fila C3 de §5 `:155`, `:167` y §10)
- Modify: `PLAN_CIERRE.md:10-11`
- Create: este documento
- Modify: `docs/bitacora/2026-09-23-cierre.md` y `docs/auditoria/2026-09-inventario.md` (fila INV‑076 y fila nueva INV‑083), en el segundo commit
- Create: `tests/fixtures/subproceso.py`, en el tercer commit (A‑13)

**Interfaces:**
- Consumes: las decisiones tomadas D1 a D7.
- Produces: el texto enmendado que ejecutan las Tareas 2 a 9, las dos excepciones de `core/` escritas en la spec y el criterio exacto de `core/` de la Tarea 18, paso 3.

- [ ] **Step 1: Enmendar el plan de UI**, cada punto en su lugar:
  - (a) **Nota de enmienda** tras el **Goal**. U1 se ejecuta como fase C3 del cierre, en `inc/cierre-C3`. La Tarea 6 se hizo en C1 (`9f6b72b` y `10e3a10`), salvo su paso 7, que queda decidido por D7 = (b): la base del worktree `prototipo` se declara base sucia de un worktree retirado y no se ejecuta nada sobre ella. La compuerta es **GU1a**. CP‑07 sale de la Tarea 13 hacia **Med (GU1b)**. Enlace a este plan.
  - (b) **Architecture** (`:12`). «Nada toca `core/`, `adapters/`, `ml/` ni `api/`» pasa a: el código de `ui/` no modifica `core/`; en la fase C3, `core/` cambia solo por dos commits propios, el de INV‑080 en `core/budget/` y el de INV‑015 7a (tabla `descarte_version` y `descartar_version`); `api/` y `ml/` solo en los commits de INV‑080 e INV‑081 del plan de C3; `adapters/` no cambia.
  - (c) **Global Constraints.**
    - `:33-35`: la dependencia dura quedó cumplida (PR #7 fusionado; U1 sale de `main` tras C2, `58ee828`).
    - `:36`: se sustituye por el criterio de `core/` de la Tarea 18, paso 3 de este plan.
    - `:37-38`: `test_composicion_extremo_a_extremo.py` y `test_auditoria_7_de_7.py` solo cambian por INV‑052, sin tocar aserciones.
    - Tech Stack: Python 3.13.
  - (d) **Mapa de archivos.** La fila 6 pasa a «hecha en C1». La fila 11 suma `ui/elaboracion.py`, `ui/resultado.py`, `ui/composicion.py` y `tests/unit/test_arquitectura.py`. La fila 13 pasa a «Compuerta GU1a; CP‑07 en Med».
  - (e) **Tarea 6.** Encabezado `(hecha en C1: 9f6b72b, 10e3a10; paso 7 decidido en C3: D7 = (b))` y casillas marcadas, incluida la 7, con la nota «base sucia de un worktree retirado; no se ejecuta nada sobre ella».
  - (f) **Tarea 10.** Sumar los pasos de INV‑022, INV‑023 y P8 (Tarea 5 de este plan) y refrescar anclas.
  - (g) **Tarea 11.** La tabla del paso 3 con las anclas vigentes y el paso 4 con `:91-113`. Pasos
    nuevos 8 a 12: la extracción de INV‑043 (11b y 11c, D5 = A), que remiten a la Tarea 6 de este
    plan. La frase de GC0: «esa extracción la hace la Tarea 11 y nadie más».
  - (h) **Tarea 12.** Anclas: manual `:97-105`; guion `:38-110` y `:394-533`. Paso nuevo: reescribir a propósito `test_cp07_se_declara_no_ejecutable_hasta_u1`, y conservar la corrección de INV‑065 (nunca volver a `data/apu.db`).
  - (i) **Tarea 13** pasa a «Compuerta GU1a».
    - El paso 2 remite al criterio de `core/` de la Tarea 18, paso 3 (dos commits).
    - El paso 3 empuja `inc/cierre-C3`.
    - Los pasos 6 y 7 (CP‑07) pasan a Med (GU1b) con nota.
    - El paso 7 registra solo `**GU1a: cruzada…**`.
  - (j) **«Fases U2 y U3».** «al cerrar GU1» pasa a «al cerrar GU1b (Med)».
- [ ] **Step 2: `PLAN_UI.md`.**
  - `:18`: dependencia cumplida.
  - Tabla de sesiones: U1.1 «hecha en C1 (salvaguarda); integración con `main` en C3»; U1.6 «Manual y guion; compuerta GU1a (C3); CP‑07 en Med (GU1b)».
  - `:58-61` (**el `git diff --stat main -- core/` vacío de `:59`**): GU1 se parte en:
    - **GU1a:** línea base; suite verde en ambos sistemas; salvaguarda activa; `core/` cambia **solo** por los dos commits que autoriza la fila C3 de la spec de cierre (§5): el de INV‑080 y el de INV‑015 7a, verificados como en la Tarea 18, paso 3 del plan de C3; cuatro encargos.
    - **GU1b:** CP‑07 ejecutado y registrado, en Med.
  - GU2: «ídem GU1a y GU1b».
- [ ] **Step 3: Spec de cierre.**
  - **Fila C3 de §5 (`:155`).** «C3 corrige además **INV‑080** … Es la única excepción a «`core/` sin cambios» en C3; enmienda autorizada por Eugenio el 2026‑09‑24 (§10)» pasa a nombrar **dos** excepciones, cada una en un commit propio de `core/`, con expediente previo, sin mezclar capas (sus llamadores de `api/` y `ui/` en commits separados) y con la línea base intacta:
    - INV‑080 (la recarga del informe pierde los pendientes), un commit de `core/budget/`;
    - INV‑015 7a (descartar la versión revalorada, `docs/ERS.md:170`), un commit con la tabla aditiva `descarte_version` en `core/models/`, `descartar_version` en `core/budget/actualizacion.py` y el docstring de `core/catalog/sesion.py`; el botón, en un commit de `ui/`.
    - La columna de compuerta pasa a «**GC3 = GU1a** (ver enmienda), más, para esos dos commits, el expediente previo y la línea base intacta».
  - **`:167`** (el texto está en `:167`, no en `:166`; A‑10). El paréntesis de GU1a «`core/` sin cambios» pasa a «`core/` sin cambios salvo los dos commits que autoriza la fila C3: INV‑080 e INV‑015 7a (§10, enmiendas del 2026‑09‑24)».
  - **Al final de §10**, un párrafo: «**Enmienda del 2026‑09‑24 (apertura de C3).** Eugenio decidió (D1 = A) que la subtarea 7a de INV‑015 (expediente B.8 de `docs/bitacora/2026-09-23-C1-expedientes.md`) se corrige en C3 con un segundo commit de `core/`: la tabla `descarte_version`, que `crear_esquema` agrega sin alterar las demás (no es migración de esquema, §2), y `descartar_version` en `core/budget/actualizacion.py`, con el botón en un commit de `ui/` aparte. Condiciones: las mismas que INV‑080. Motivo: 7a exige un dato persistido nuevo («se marca como descartada») y la fila INV‑015 es importante, así que no puede ir a limitaciones. Coherencia: GU1a recoge las dos excepciones en su criterio, en `PLAN_UI.md` y en la verificación de la compuerta».
- [ ] **Step 4: `PLAN_CIERRE.md:10-11`.** Enlazar este plan como plan de C3, junto al de UI enmendado.
- [ ] **Step 5: Comprobar**

Run:

```bash
grep -n "inc/PLAN-ui\|GU1\b\|git diff --stat main -- core/ adapters/ ml/ api/" docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md PLAN_UI.md
grep -n "única excepción\|unica excepcion" docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md PLAN_UI.md docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md
grep -c "INV‑015 7a\|INV-015 7a" docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md PLAN_UI.md
```

Expected:
- El primero: solo menciones históricas de U0 (Tareas 1 a 5) o notas de enmienda. Ningún criterio vigente con «GU1» a secas ni con el diff vacío sobre `core/`.
- El segundo: vacío. Ningún texto vigente llama «única» a la excepción de INV‑080.
- El tercero: al menos `3` en la spec (fila C3, `:167` y §10) y al menos `1` en `PLAN_UI.md`.

- [ ] **Step 6: Commit 1** (primero de la rama)

```bash
git add docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md PLAN_UI.md docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md PLAN_CIERRE.md docs/superpowers/plans/2026-09-24-cierre-c3-interfaz-scripts.md
git commit -m "docs(plan): enmienda del plan de ui para c3 y plan detallado de la fase" -m "Tarea 6 hecha en C1 y su paso 7 decidido (D7 = b); CP-07 pasa a Med (GU1b); rama inc/cierre-C3; compuerta GU1a con dos excepciones de core: INV-080 en core/budget e INV-015 7a (D1 = A), enmendadas en la fila C3 y en la seccion 10 de la spec de cierre; restriccion sobre api/ retirada; anclas refrescadas; la Tarea 11 absorbe INV-043." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 7: Abrir la sección de C3 en la bitácora y registrar D2 en el inventario.**
  - Agregar `## Fase C3 — interfaz y scripts` al final de `docs/bitacora/2026-09-23-cierre.md`, con:
    - rama, commit de partida (`58ee828`) y enlace al plan;
    - `N0`, las metas y si `data/apu.db` existe;
    - las decisiones D1 a D7 de Eugenio (2026‑09‑24), con su costo;
    - los Hechos 1 a 12, con los tres resueltos y su evidencia;
    - los tres sub‑worktrees (D3), con rama y ruta;
    - la regla de reparto.
  - En `docs/auditoria/2026-09-inventario.md`, la columna de estado de INV‑076 pasa de `abierto` a: `abierto — en duda (spec §2): RF‑24 existe, pero la ruta y la pantalla propuestas no están en la ERS; por decisión de Eugenio (D2, 2026‑09‑24) C3 no escribe su código; diseño propio (superpowers:brainstorming) fuera de C3; cruza GC3 abierto`. Las demás columnas no cambian.
  - En el mismo archivo, una fila nueva **INV‑083** después de INV‑082 (Hecho 11, A‑1), con las diez columnas:
    - Origen: `revisión del plan de C3 (arquitectura, A‑1)`; Capa: `ui/core (cruza: api)`; Principio: `Informe siempre (principio 7) / trazabilidad (UC‑01 3a)`; Severidad: `importante`.
    - Evidencia: `ui/paginas/escenarios.py:31,93`; `api/rutas/presupuestos.py:260`; `core/budget/escenarios.py:71-111` (`generar_escenario` reelabora solo los renglones valorados).
    - Hallazgo: `los escenarios de un presupuesto con pendientes no los declaran: la pérdida de INV‑080 por la ruta de UC‑08, que D4 = A (recarga y revaloración) no cubre`.
    - Corrección propuesta: `la página de escenarios carga el base con cargar_elaboracion (commit de INV‑080) y declara sus pendientes; sin tercer commit de core/. El informe del propio escenario y la ruta de la API quedan para C4 (dictamen C3‑12)`.
    - Fase destino: `C3 (ui); C4 (informe del escenario y API)`; Estado: `abierto`.
  - Después, el commit:

```bash
git add docs/bitacora/2026-09-23-cierre.md docs/auditoria/2026-09-inventario.md
git commit -m "docs(bitacora): abre la seccion de c3 del cierre" -m "Decisiones D1 a D7 de Eugenio (2026-09-24); hechos resueltos con evidencia; INV-076 en duda y fuera de C3 (D2); INV-083 nuevo, los escenarios con pendientes (A-1)." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 8: La ayuda única de subproceso (A‑13), antes de abrir las pistas.** INV‑023 (Tarea 5, pista A) e INV‑024 (Tarea 14, pista C) importan módulos en un proceso limpio. Para que no haya dos arneses, la ayuda entra aquí, en un commit propio que heredan las cuatro pistas. `tests/fixtures/subproceso.py`:

```python
"""Importar modulos en un proceso Python limpio (INV-023 e INV-024): una sola ayuda para las
pruebas que comprueban que importar no tiene efectos ni arrastra extras."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

#: Importa cada modulo de argv y escribe en stdout, uno por linea, los de `sys.modules` al final.
_CODIGO = (
    "import importlib, sys\n"
    "for nombre in sys.argv[1:]:\n"
    "    importlib.import_module(nombre)\n"
    "print('\\n'.join(sorted(sys.modules)))\n"
)


def importar_en_limpio(modulos: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Importa `modulos` en un proceso nuevo con `cwd` como directorio de trabajo y la raiz del
    repositorio en `PYTHONPATH`. No lanza si el proceso falla: el llamador afirma `returncode`."""
    return subprocess.run(
        [sys.executable, "-c", _CODIGO, *modulos],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(RAIZ)},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def modulos_cargados(salida: subprocess.CompletedProcess[str]) -> set[str]:
    """Los nombres de `sys.modules` que el proceso limpio dejo cargados."""
    return set(salida.stdout.split())
```

  Sin prueba propia: la ejercen la Tarea 5 (con su mutación en dos direcciones) y la Tarea 14. `uv run ruff check tests/fixtures/subproceso.py` limpio. Commit:

```bash
git add tests/fixtures/subproceso.py
git commit -m "test: ayuda unica para importar modulos en un proceso limpio" -m "La comparten INV-023 (pista A) e INV-024 (pista C); entra antes de abrir los sub-worktrees (A-13)." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 9: Crear los tres sub‑worktrees (D3)** desde el commit del paso 8:

```bash
git worktree add .claude/worktrees/cierre-C3-nucleo -b inc/cierre-C3-nucleo
git worktree add .claude/worktrees/cierre-C3-pruebas -b inc/cierre-C3-pruebas
git worktree add .claude/worktrees/cierre-C3-scripts -b inc/cierre-C3-scripts
git worktree list
```

Expected: los tres en la lista, sobre el hash del commit del paso 8.

- [ ] **Step 10: Guardar el guion `guardia_gc3.sh`** (sección «Orquestación por roles») en `.superpowers/sdd/2026-09-24-cierre-c3/`, sin versionar, y correrlo con `0`: debe terminar en código 0 (todavía no hay commits de `core/`).

---

### Task 2: Tarea 7 del plan de UI, `ui/recorridos.py`

Se ejecuta **tal cual** (pasos 1 a 5 del plan de UI, `:728-1035`): código, pruebas, rojo esperado (`ModuleNotFoundError`, que ahí sí basta porque el módulo es datos puros) y commit.

Agregado: tras el verde, una **mordida**. En `paso_siguiente`, cambiar `return recorrido.pasos[posicion]` por `return recorrido.pasos[posicion - 1]`. Debe fallar `test_paso_siguiente_avanza_y_se_detiene_en_el_ultimo`; luego se restaura.

Expected: 13 passed.

### Task 3: Tarea 8 del plan de UI, `ui/caso.py`

Tal cual (`:1039-1377`). `tests/conftest.py` ya tiene la salvaguarda. `_sin_caso_del_entorno` se agrega **después** de `_base_real_intacta`, sin tocarla.

Mordidas, cada una restaurada después:
- En `estado_caso`, quitar la guarda `if not ruta.exists()`. Debe fallar `test_estado_de_una_ruta_inexistente_no_crea_el_archivo`.
- `argv_siembra` con el flag de reinicio agregado (QA‑6: sus dos pruebas son de esta tarea, `test_ui_caso.py`, `:1194-1207` del plan de UI). Deben fallar `test_la_siembra_apunta_al_caso_y_no_reinicia` y `test_ningun_archivo_de_ui_contiene_el_flag_de_reinicio`, porque el literal queda en `ui/caso.py`.

Expected: 12 passed.

### Task 4: Tarea 9 del plan de UI, la pantalla de Inicio

Tal cual (`:1382-1646`). Mordida en `ui/paginas/inicio.py`, la que muerde las pruebas de esta tarea (QA‑6): quitar la salida temprana `if not estado.vacio:` (el Inicio ofrece sembrar aunque el caso tenga partidas). Debe fallar `test_con_partidas_no_se_ofrece_sembrar`. Luego se restaura.

Expected: 9 passed.

### Task 5: Tarea 10 del plan de UI, más INV‑022, INV‑023 y P8

**Files:** los de la Tarea 10 del plan de UI.

**¿Existe la capacidad?**
- INV‑022: la desviación existe, pero nada afirma que surtió efecto (`test_ui_app.py:80-85`).
- INV‑023: `test_ui_importable.py` no tiene aserciones.

- [ ] **Step 1: Pasos 1 y 2 del plan de UI**, con estas diferencias.
  - En la reescritura de `test_ui_app.py`, `_aplicacion` afirma tras `at.run()` (INV‑022):

```python
from tests.conftest import RUTA_BASE_REAL, huella

def _aplicacion(monkeypatch, tmp_path: Path) -> AppTest:
    caso = importlib.import_module("ui.caso")
    temporal = tmp_path / "app.db"
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(temporal))
    antes = huella(RUTA_BASE_REAL)
    at = AppTest.from_file(str(RUTA_APP), default_timeout=60)
    at.run()
    # INV-022: la desviacion surtio efecto (el marco muestra el temporal) y la base real no cambio.
    assert str(temporal) in [leyenda.value for leyenda in at.sidebar.caption]
    assert huella(RUTA_BASE_REAL) == antes
    return at
```

  - `test_ui_importable.py` conserva el literal de P8 y afirma la ausencia de efectos (INV‑023). El subproceso es la ayuda única `tests/fixtures/subproceso.py::importar_en_limpio` de la Tarea 1, paso 8 (A‑13), y se repone el conteo del plan de UI (QA‑11): diez páginas más los módulos sin página, que la Tarea 6 amplía con `ui.elaboracion` y `ui.resultado` sin tocar el `+ 10`:

```python
from tests.fixtures.subproceso import importar_en_limpio

MODULOS_SIN_PAGINA = ("ui.app", "ui.caso", "ui.recorridos", "ui.composicion")

def test_las_paginas_se_importan_sin_efectos(tmp_path):
    """Importar cada modulo de ui/ en un proceso limpio, con cwd temporal: no crea archivos ni
    llama a Streamlit fuera de `main()` (spec de UI, §4 regla 3)."""
    modulos = (*MODULOS_SIN_PAGINA, *(p.render.__module__ for p in PAGINAS))
    assert len(modulos) == len(MODULOS_SIN_PAGINA) + 10  # las diez paginas del marco
    assert "ui.paginas.componer" in modulos  # meta P8 del prototipo (scripts/meta_prototipo.py)
    salida = importar_en_limpio(modulos, cwd=tmp_path)
    assert salida.returncode == 0, salida.stderr
    assert list(tmp_path.iterdir()) == []
    assert "ScriptRunContext" not in salida.stderr  # Streamlit llamado sin runtime
```

- [ ] **Step 2: Rojo del plan de UI** (`ImportError` de `PAGINA_INICIO`), **más la debilidad de INV‑023 en las dos direcciones.**
  - Antes de reescribir, agregar **temporalmente** al final de `ui/paginas/historico.py` `import streamlit as _st; _st.title("efecto")  # MUTACION`.
  - La prueba vieja pasa.
  - Con la nueva escrita, falla por `ScriptRunContext`. Si Streamlit 1.62 no lo escribe en modo *bare*, la marca se sustituye por `Path("efecto.txt").touch()` y falla `iterdir`. Anotar cuál de las dos se observó.
  - Restaurar.
- [ ] **Step 3: Implementar (paso 4 del plan de UI), verde (pasos 5 y 6) y commit (paso 7).** El cuerpo del commit agrega: `Cierra INV-022 e INV-023; conserva el literal de la meta P8.`
- [ ] **Step 4: Meta P8.** `uv run python scripts/meta_prototipo.py` da 12/12.

### Task 6: Tarea 11 del plan de UI, más INV‑044 (ui) e INV‑043

**Files:** los de la Tarea 11 de UI, más:
- Create: `ui/elaboracion.py`, `ui/resultado.py`, `tests/unit/test_elaboracion.py`
- Modify: `ui/composicion.py` (11c, D5 = A: solo gana `desglose`, que es puro; ver paso 10)
- Modify: `tests/unit/test_arquitectura.py`, `tests/unit/test_composicion.py`

**Interfaces** (las fija esta tarea; las Tareas 7, 10c y 11, paso 8, las consumen sin cambiarlas salvo donde se dice):
- `ui/elaboracion.py` (sin Streamlit, sin `pandas`, sin `ui.caso`; orquesta contra `core.budget` y `core.catalog`; **el único módulo de `ui/` sin página que escribe en la base**, A‑2):
  - `items_desde_filas(filas: Sequence[Mapping[str, object]], partidas_por_codigo: Mapping[str, str]) -> tuple[list[ItemComputo], list[str]]`
  - `elaborar_desde_catalogo(catalogo: Catalogo, items: Sequence[ItemComputo], codigo: str, fecha: date, moneda: str) -> ResultadoElaboracion`
  - `libro_excel(resultado: ResultadoElaboracion) -> tuple[bytes, str]`
  - `Guardado` (dataclass congelada: `resultado: ResultadoAPU | None`, `motivo: str | None`, exactamente uno de los dos) y `guardar_composicion(catalogo: Catalogo, composicion: ComposicionAPU, dominio: Dominio, fecha: date, condiciones: str) -> Guardado` (paso 10).
- `ui/composicion.py` (puro): gana `desglose(composicion: ComposicionAPU) -> ResultadoAPU` (paso 10). Su docstring de módulo pasa a decir que depende de `core.costing` (función pura) y que no escribe en la base.
- `ui/resultado.py` (Streamlit; sin `sqlalchemy.orm` ni `core.costing`): `mostrar_elaboracion(resultado: ResultadoElaboracion, libro: bytes, nombre_libro: str, *, prefijo: str) -> None` en esta tarea. La Tarea 7 le agrega el parámetro `propuestas` y el retorno (su bloque Interfaces).

**Parte a (pasos 1 a 7 del plan de UI, anclas vigentes).** Migra las nueve pantallas y retira las ocho `RUTA_BASE_POR_DEFECTO` de las páginas (INV‑044, parte de `ui/`). Commit `refactor(ui): las pantallas leen el caso abierto y el marco pinta su titulo`.

**Parte b (11b y 11c, D5 = A; INV‑043: la orquestación, el cálculo y la persistencia salen de `componer.py`).** Es una refactorización **sin cambio de comportamiento**. La prueba de arquitectura va primero.

- [ ] **Step 8: Prueba de arquitectura, en rojo por la estructura actual.** En `tests/unit/test_arquitectura.py` (ya importa `ast`, `pytest` y define `RAIZ`), **una** prueba parametrizada por módulo que hace cumplir las reglas de importación de `ui/` (A‑9). Las entradas de `ui/elaboracion.py` y `ui/resultado.py` se agregan en el paso 9, cuando existen; la de `componer.py` crece en el paso 10:

```python
#: Lo que cada modulo de ui/ no importa en tiempo de ejecucion (fuera de `if TYPE_CHECKING:`).
#: Reglas de interfaz del plan de C3 (Global Constraints) e INV-043 para la pagina de componer.
PROHIBIDOS_EN_UI: dict[str, tuple[str, ...]] = {
    "ui/paginas/componer.py": ("core.budget", "tempfile"),
    # RA-2: "no escribe en la base" vigilado tambien por core.catalog, core.budget y sqlalchemy.
    "ui/composicion.py": (
        "streamlit", "pandas", "ui.caso", "sqlalchemy", "core.catalog", "core.budget",
    ),
}


def _imports_de_ejecucion(ruta: Path) -> set[str]:
    """Modulos importados fuera de `if TYPE_CHECKING:` (AST), tambien los perezosos."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    solo_tipado = {
        id(nodo)
        for bloque in ast.walk(arbol)
        if isinstance(bloque, ast.If)
        and ast.unparse(bloque.test) in {"TYPE_CHECKING", "typing.TYPE_CHECKING"}
        for sentencia in bloque.body
        for nodo in ast.walk(sentencia)
    }
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if id(nodo) in solo_tipado:
            continue
        if isinstance(nodo, ast.Import):
            importados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            importados.add(nodo.module)
    return importados


@pytest.mark.parametrize("modulo", sorted(PROHIBIDOS_EN_UI))
def test_ui_respeta_sus_importaciones_prohibidas(modulo):
    """INV-043 (criterio S, spec de cierre §4) y reglas de interfaz de C3: cada modulo de ui/
    importa solo lo que su responsabilidad pide."""
    importados = _imports_de_ejecucion(RAIZ / modulo)
    prohibidos = {
        nombre
        for nombre in importados
        for prefijo in PROHIBIDOS_EN_UI[modulo]
        if nombre == prefijo or nombre.startswith(prefijo + ".")
    }
    assert not prohibidos, f"{modulo} importa {sorted(prohibidos)}"
```

  Run: `uv run pytest tests/unit/test_arquitectura.py -k importaciones_prohibidas -q`
  Expected: FAIL en `ui/paginas/componer.py`, citando `core.budget` (hoy `componer.py:34-39`); PASS en `ui/composicion.py`.
  - La entrada de `ui/composicion.py` endurece una regla que ya existe (P7 solo mira `streamlit`): mutación en las dos direcciones. Agregar temporalmente `import pandas  # MUTACION` a `ui/composicion.py`: `uv run python scripts/meta_prototipo.py` sigue en 12/12 (P7 no lo ve) y esta prueba falla. Restaurar.

- [ ] **Step 9: Extraer (11b).**
  - `ui/elaboracion.py`, con las firmas del bloque Interfaces:
    - `items_desde_filas`: las filas de cantidades pasan a ítems más avisos. Mueve la lógica de `componer.py:723-748` y `_celda_de_cantidad` tal cual; INV‑046 viene después.
    - `elaborar_desde_catalogo`: `catalogo.composiciones` de los códigos únicos y `elaborar(..., plan=plan_secuencial)`. Mismo comportamiento que `componer.py:798-809` y `elaborar.py:225-235`: hoy **todavía** pide todas las composiciones. Lo cambia la Tarea 7.
    - `libro_excel`: `exportar_excel` en un directorio temporal.
  - `ui/resultado.py`: `mostrar_elaboracion(resultado, libro, nombre_libro, *, prefijo)` con el cuerpo de `componer.py:828-862` (total, severidades, descarga e informe). `prefijo` es el de las claves de widget de la página que lo llama (`"componer"` o `"elaborar"`), para que las claves no cambien.
  - `componer.py` y `elaborar.py` los usan. Las claves de `st.session_state` y los rótulos no cambian.
  - `PROHIBIDOS_EN_UI` suma `"ui/elaboracion.py": ("streamlit", "pandas", "ui.caso")` y `"ui/resultado.py": ("sqlalchemy.orm", "core.costing")`.
  - `MODULOS_SIN_PAGINA` de `test_ui_importable.py` suma `ui.elaboracion` y `ui.resultado` (el `+ 10` de la Tarea 5 no cambia).
  - Pruebas puras nuevas en `tests/unit/test_elaboracion.py` (base en `tmp_path` sembrada con `scripts.seed.sembrar`; oráculos de la fixture de la línea base). Su rojo es `ImportError`, así que cada función lleva su **mordida** tras el verde (QA‑8), restaurada después:
    - `items_desde_filas`: las filas de `items_auditados()` dan esos mismos ítems (`==`) y ningún aviso; una fila con la cantidad vacía da un aviso que cita su fila. Mordida: no emitir el aviso de la celda vacía; falla la segunda.
    - `elaborar_desde_catalogo`: con `items_auditados()` y la fecha de la línea base, el total es `TOTAL_EXACTO_LINEA_BASE` (oráculo: la fixture). Mordida: omitir el primer código de la lista de composiciones que se piden; falla por el total.
    - `libro_excel`: el libro se abre con `openpyxl` desde los bytes y tiene la hoja de auditoría; el nombre termina en `.xlsx`. Mordida: devolver `b""`; falla la apertura.
  - Mordidas de la regla de importación: agregar `import streamlit  # MUTACION` a `ui/elaboracion.py`, y `from core.costing import calcular_apu  # MUTACION` a `ui/resultado.py`. Cada una hace fallar su parámetro de `test_ui_respeta_sus_importaciones_prohibidas`. Restaurar.
  - Verde del paso 8 en `componer.py` y commit `refactor(ui): la elaboracion sale de la pagina de componer`, que cierra la parte 11b de INV‑043.
- [ ] **Step 10: 11c (D5 = A).**
  - La entrada de `componer.py` en `PROHIBIDOS_EN_UI` pasa a `("core.budget", "core.costing", "sqlalchemy.orm", "tempfile")`. Rojo: el parámetro de `componer.py` cita `core.costing` y `sqlalchemy.orm`.
  - `ui/composicion.py` gana `desglose(composicion) -> ResultadoAPU` (`calcular_apu` con `ParametrosCosto()`), que es puro. Su docstring de módulo dice ahora que depende de `core.costing` y que no escribe en la base.
  - `ui/elaboracion.py` gana `Guardado` y `guardar_composicion(catalogo, composicion, dominio, fecha, condiciones) -> Guardado`, con la lógica de `componer.py:653-666`: `motivo_para_no_reemplazar` antes de escribir con `cargar_composicion` o `reemplazar_composicion`. **Sin `commit`**: lo decide la página. La persistencia **no** va a `ui/composicion.py` (A‑2).
  - `componer.py` confirma con `sesion.commit()` solo si hubo resultado.
  - El tipo `Session` pasa a `if TYPE_CHECKING:`.
  - Pruebas:
    - En `tests/unit/test_composicion.py`, `desglose(APU_TUBERIA)`: precio unitario redondeado igual a `PRECIO_UNITARIO_ESPERADO["LB-02-TUB"]` (10,19) y costo directo 8,058 (CLAUDE.md §4). Mordida: `ParametrosCosto(utilidad=Decimal(0))` dentro de `desglose`; falla.
    - En `tests/unit/test_elaboracion.py`, `guardar_composicion`: el motivo ante una cabecera distinta, sin escribir nada; y la persistencia en `tmp_path`, confirmada por la prueba y releída con un motor propio. Mordida: saltarse `motivo_para_no_reemplazar`; falla «motivo ante una cabecera distinta» (QA‑8).
- [ ] **Step 11: Verde y regresión.**

Run: `uv run pytest tests/unit/test_ui_componer.py tests/unit/test_ui_app.py tests/unit/test_ui_importable.py tests/unit/test_composicion.py tests/unit/test_elaboracion.py tests/unit/test_arquitectura.py -q -W error --strict-markers`, después el recuento, `uv run python scripts/meta_prototipo.py` (P7 sigue OK) y `wc -l ui/paginas/componer.py`.

Expected:
- Verde.
- Las 9 pruebas de `test_ui_componer.py` sin cambios, salvo el arnés de la parte a.
- Anotar las líneas de `componer.py` antes (862) y después.

- [ ] **Step 12: Commit de 11c**, separado del de 11b (paso 9): `refactor(ui): calculo y guardado de la composicion fuera de la pagina`, que cierra INV‑043.

### Task 7: INV‑072 en `ui/`: el ítem sin partida queda pendiente, con sus propuestas

**Files:**
- Modify: `ui/elaboracion.py`, `ui/resultado.py`, `ui/paginas/elaborar.py`, `ui/paginas/componer.py` (solo la llamada al fragmento, con la firma nueva)
- Create: `tests/unit/test_ui_elaborar.py`

**Interfaces** (fijas desde aquí; 10c cambia el **cuerpo** de `propuestas_de_pendientes`, no su firma ni su tipo de retorno; A‑3 y A‑4):
- `ui/elaboracion.py`:
  - `PendienteConPropuestas` (dataclass congelada): `item: ItemComputo`, `similares: tuple[PartidaSimilar, ...]`, `falla: str | None = None`. `PartidaSimilar` se importa bajo `if TYPE_CHECKING:`.
  - `propuestas_de_pendientes(partidas: Mapping[str, str], pendientes: Sequence[ItemComputo]) -> tuple[PendienteConPropuestas, ...]`: una entrada por pendiente, en su orden; sin pendientes devuelve `()` sin cargar nada. **Cuerpo provisional en esta tarea:** llama a `composicion.sugerir_partidas_similares` (resuelta como atributo del módulo `ui.composicion`) una vez por pendiente, con el criterio de error de hoy. Construye un índice por pendiente: queda declarado aquí y lo corrige 10c, que pasa el cuerpo a `ml.normalization.propuestas_para` (un solo normalizador por llamada y el emparejamiento que comparte la API).
  - `aceptar_propuesta(items: Sequence[ItemComputo], pendiente: ItemComputo, codigo_elegido: str) -> list[ItemComputo]`.
- `ui/resultado.py`: `mostrar_elaboracion(resultado: ResultadoElaboracion, libro: bytes, nombre_libro: str, *, prefijo: str, propuestas: Sequence[PendienteConPropuestas] = ()) -> tuple[ItemComputo, str] | None`.
  - `PendienteConPropuestas` se importa de `ui.elaboracion` bajo `if TYPE_CHECKING:` (con `from __future__ import annotations`), como `PartidaSimilar`: el fragmento no arrastra `core.budget` ni `core.catalog` al importarse (RA‑1).
  - Pinta el bloque «Pendientes» siempre que `resultado.pendientes` no esté vacío: origen, código y descripción de cada uno, y sus propuestas (código, descripción y puntaje con dos decimales) o su `falla` como `st.caption`.
  - Solo para los pendientes que traen `similares` pinta el selector y el botón, con claves `f"{prefijo}_propuesta_{indice}"` y `f"{prefijo}_aplicar_{indice}"` (el índice evita claves repetidas si dos pendientes comparten origen).
  - Devuelve `(pendiente, codigo_elegido)` si se pulsó «Aplicar y volver a elaborar», o `None`. No conoce ninguna clave de `st.session_state` de ninguna página.
- `ui/paginas/elaborar.py`: importa `from ui import elaboracion` y llama `elaboracion.propuestas_de_pendientes(...)` y `elaboracion.aceptar_propuesta(...)` como atributos del módulo, para que la prueba los parche donde se resuelven (QA‑7). Calcula las propuestas **una vez por elaboración** y las guarda junto al resultado en `st.session_state`. Si el fragmento devuelve una elección, guarda `aceptar_propuesta(...)` en `CLAVE_ITEMS`, vuelve a elaborar con `elaborar_desde_catalogo` y recalcula las propuestas.
- `ui/paginas/componer.py`: llama al fragmento con `prefijo="componer"` y sin `propuestas`. Sin propuestas no hay selector: componer muestra los pendientes, si los hay, pero no ofrece aplicar (lo cubre `test_sin_propuestas_el_fragmento_no_ofrece_selector`, paso 3).

**¿Existe la capacidad?** En el núcleo, sí: `elaborar` deja pendientes (INV‑013). En la API, también (C2). La interfaz pide composiciones de todos los códigos y el catálogo lanza `KeyError` (`core/catalog/repositorio.py:128-134`).

- [ ] **Step 1: Rojo por comportamiento.** `test_ui_elaborar.py` (`AppTest`):
  - Base sembrada en `tmp_path` con `scripts.seed.sembrar` y desviada por `ui.caso`.
  - `st.session_state["elaborar_items"]` con los ítems de la línea base (`tests.fixtures.computo_auditado.items_auditados()`) más un `ItemComputo` de código `XX-99-NUE`, origen `T-99`, unidad `pieza` y cantidad `Decimal("2")`.
  - El doble de las propuestas se parcha **donde la página lo resuelve en tiempo de llamada**: `monkeypatch.setattr("ui.elaboracion.propuestas_de_pendientes", _propuestas_fijas, raising=False)`. `raising=False` porque la función todavía no existe; así el rojo no es un `AttributeError` al preparar la prueba sino el `st.error` de la página (QA‑7). `_propuestas_fijas(partidas, pendientes)` importa `PendienteConPropuestas` **dentro** de su cuerpo y devuelve, para cada pendiente, dos `PartidaSimilar` fijas: la primera `LB-02-TUB` (la usa la prueba de D6) y la segunda `LB-01-EXC`.
  - Pulsar «Elaborar presupuesto».
  - Aserciones:
    - `not at.error`;
    - el total mostrado es `formatear_decimal(TOTAL_EXACTO_LINEA_BASE, DECIMALES_PRESENTACION)`: los ítems válidos son la línea base, así que el oráculo es la fixture, independiente del núcleo (QA‑18);
    - y coincide con `formatear_decimal(elaborar(items_validos, composiciones_linea_base(), PARAMETROS_LINEA_BASE, ..., plan=plan_secuencial).presupuesto.total, DECIMALES_PRESENTACION)`, el oráculo por el núcleo directo, sin la página;
    - el texto del pendiente cita `T-99` y `XX-99-NUE`;
    - las dos propuestas aparecen;
    - el informe en markdown contiene `PENDIENTE`.

  Expected: FAIL, porque aparece `st.error` con el `KeyError` del catálogo (la página nunca llega a pedir propuestas).

- [ ] **Step 2: Implementar**, con las firmas del bloque Interfaces.
  - `elaborar_desde_catalogo` pide solo los códigos que existen: `{p.codigo for p in catalogo.partidas()}`, el mismo criterio que `api/rutas/presupuestos.py:95-101`.
  - `mostrar_elaboracion` gana `propuestas`, el bloque «Pendientes» y el retorno.
  - D6: la sustitución es pura y vive en `ui/elaboracion.py`; la página solo la invoca y reelabora:

```python
def aceptar_propuesta(
    items: Sequence[ItemComputo], pendiente: ItemComputo, codigo_elegido: str
) -> list[ItemComputo]:
    """UC-01 3a (D6): el item `pendiente` pasa a la partida propuesta que el usuario acepto. Los
    demas items no cambian; si `pendiente` no esta entre `items`, ValueError."""
    if pendiente not in items:
        raise ValueError(f"el item {pendiente.origen_id!r} no esta entre los items a elaborar")
    return [
        dataclasses.replace(item, codigo_partida=codigo_elegido) if item == pendiente else item
        for item in items
    ]
```

  - En `ui/resultado.py`, dentro del bloque «Pendientes», por cada `indice, propuesta` con `propuesta.similares`: `st.selectbox("Propuesta para " + propuesta.item.origen_id, [s.codigo for s in propuesta.similares], key=f"{prefijo}_propuesta_{indice}")` y `st.button("Aplicar y volver a elaborar", key=f"{prefijo}_aplicar_{indice}")`. Si se pulsa, el fragmento devuelve `(propuesta.item, elegido)`.
  - `componer.py` pasa a la firma nueva (`prefijo="componer"`, sin `propuestas`).
- [ ] **Step 3: Verde, mordidas y pruebas de D6.**
  - Mordida: restaurar temporalmente la petición de todos los códigos. El paso 1 falla; luego se restaura.
  - Prueba pura de `aceptar_propuesta` en `tests/unit/test_ui_elaborar.py`: cambia solo el ítem pendiente, deja los demás idénticos (`==`) y da `ValueError` con un ítem que no está. Mordida: reemplazar el código de **todos** los ítems; falla «deja los demás idénticos».
  - Prueba pura de `propuestas_de_pendientes` (cuerpo provisional): con `ui.composicion.sugerir_partidas_similares` parchado por un doble que registra sus llamadas, dos pendientes dan dos entradas en su orden, cada una con las propuestas de su descripción; sin pendientes, `()` y el doble no se llama. Mordida: devolver las entradas en orden inverso; falla. 10c reescribe esta prueba, declarado ahí.
  - Prueba `AppTest.from_function` del fragmento, `test_sin_propuestas_el_fragmento_no_ofrece_selector`: un `ResultadoElaboracion` con un pendiente y `propuestas=()` pinta el pendiente, sin `selectbox` ni botón «Aplicar y volver a elaborar»; con una entrada con `similares`, un `selectbox`. Es la regresión de `componer.py` (A‑3). Mordida: pintar el selector aunque no haya `similares`; falla la primera mitad.
  - Prueba `AppTest` de D6: sobre el estado del paso 1, elegir `LB-02-TUB` para `T-99` y pulsar «Aplicar y volver a elaborar». Aserciones: ningún pendiente; el total mostrado es `formatear_decimal(elaborar(aceptar_propuesta(items, pendiente_t99, "LB-02-TUB"), composiciones_linea_base(), PARAMETROS_LINEA_BASE, ..., plan=plan_secuencial).presupuesto.total, DECIMALES_PRESENTACION)`, el oráculo por el núcleo directo; y ese total supera al del paso 1 en `cantidad de T-99 × PRECIO_UNITARIO_EXACTO["LB-02-TUB"]` (10,1933700 USD por pieza, aritmética de la fixture), con la tolerancia `Decimal(1).scaleb(-DECIMALES_PRESENTACION)` de los dos redondeos de presentación, definida en el propio archivo (no se importa de `test_ui_componer.py`: INV‑052). El ítem `XX-99-NUE` se declara en `pieza`, la unidad de `LB-02-TUB`, para que R3 no agregue un hallazgo ajeno a la prueba.
  - Mordida de D6: que la página no guarde en `CLAVE_ITEMS` la lista devuelta por `aceptar_propuesta`. La prueba `AppTest` de D6 falla (el pendiente sigue); luego se restaura.
- [ ] **Step 4: Commit** `fix(ui): uc-01 3a en la interfaz deja pendiente el item sin partida y propone similares`, que cierra la parte de C3 de INV‑072.

### Task 8: INV‑045, INV‑046 e INV‑052 (después de la Tarea 11)

- [ ] **INV‑045.**
  - Prueba `AppTest` en `test_ui_componer.py`: con las tablas de `APU_TUBERIA`, las métricas del desglose valen `8.06` de costo directo y `10.19` de precio unitario. El oráculo es CLAUDE.md §4 (costo directo 8,058; PU 10,19) y `PRECIO_UNITARIO_ESPERADO`.
  - Rojo: hoy se muestra `str(Decimal)`.
  - Luego `formatear_decimal` en el desglose, el mensaje de guardado y el bloque de similares.
  - Commit `fix(ui): componer presenta los decimales con la fuente unica`.
- [ ] **INV‑046.**
  - `ui/composicion._texto` pasa a ser pública con el nombre `texto_de_celda`, y `ui/elaboracion.py` la importa.
  - Prueba de arquitectura: «ningún módulo de `ui/` define `_celda_de_cantidad`». Hoy falla; luego pasa.
  - Commit `refactor(ui): una sola lectura de celdas de tabla`.
- [ ] **INV‑052.**
  - Prueba en `test_arquitectura.py`: `test_ningun_modulo_de_prueba_importa_de_otro_modulo_de_prueba`. Recorre `tests/**/test_*.py` por AST: solo se admite `from tests.fixtures…` y `from tests.conftest…`. Rojo con las dos importaciones: `test_ui_componer.py:64` y `test_composicion_extremo_a_extremo.py:54`.
  - Mover `_texto`, `_filas_materiales`, `_filas_equipos` y `_filas_mano_obra` a `tests/fixtures/filas_composicion.py`, y `_detectadas` a `tests/fixtures/auditoria.py`, con nombres públicos.
  - Comprobar con `git diff -U0 -- tests/integration/test_composicion_extremo_a_extremo.py tests/integration/test_auditoria_7_de_7.py | grep '^[-+].*assert'`, que debe salir **vacío**.
  - Línea base: `27 0 0 0`.
  - Commit `test: las ayudas compartidas de las pruebas pasan a fixtures`.

### Task 9: Tarea 12 del plan de UI, manual y guion

Tal cual (`:2337-2383`), con las anclas vigentes. Más:

- `test_cp07_se_declara_no_ejecutable_hasta_u1` se reescribe como `test_cp07_es_ejecutable_y_se_mide_en_med`: afirma «se ejecuta en la fase Med (GU1b)» y retira «no es ejecutable hasta U1» (QA‑10).
  - Conserva la aserción de INV‑065 que hoy hace `test_guion_prueba_arenia.py:121`: la preparación de CP‑07 nombra la `copia desechable de la sección 4` o `ARENIA_CASO` con una base que no es la por defecto.
  - Rojo declarado: la prueba nueva se escribe **antes** que el guion y falla, porque el guion todavía dice «no es ejecutable hasta U1». Tras editar el guion, pasa. Se anota la salida del rojo.
- El guion de CP‑01 a CP‑06 sustituye «campo **Archivo SQLite**» por el caso abierto con `ARENIA_CASO=data/prueba_arenia.db`: `CASO_ABIERTO` ya lo admite la prueba (`:101-112`). **Nunca** la ruta por defecto (INV‑065).
- En el paso 3 del plan de UI, RF‑36 a RF‑43 pasan a «cumplido (U1)». UC‑01 3a en la interfaz (`test_ui_elaborar.py`) se anota para la matriz de C4 (INV‑033).
- Commit del plan de UI.

### Task 10: INV‑081, una sola propuesta de similares (tres commits, tres capas)

**Interfaces** (las fija 10a; 10b y 10c las consumen sin cambiarlas; A‑4):
- `ml/normalization/normalizador.py`, exportadas en `ml/normalization/__init__.py`:
  - `FALLAS_DE_LA_PROPUESTA: tuple[type[Exception], ...]`
  - `Propuesta` (dataclass congelada): `similares: tuple[PartidaSimilar, ...]`, `falla: str | None = None`
  - `proponedor(partidas: Mapping[str, str]) -> Callable[[str], Propuesta]`: construye **un** normalizador y lo reutiliza en cada consulta.
  - `propuestas_para(partidas: Mapping[str, str], pendientes: Sequence[P]) -> tuple[tuple[P, Propuesta], ...]` (mismo orden de argumentos que `propuestas_de_pendientes` de `ui/`), con `P` acotado a `TieneDescripcion` (un `Protocol` con `descripcion: str`, para que `ml/` no dependa de `ItemComputo`). Es **el único emparejamiento** de pendientes con propuestas: un solo `proponedor` por llamada, ninguno si no hay pendientes. Lo usan `api/rutas/presupuestos.py::_pendientes` (10b) y `ui/elaboracion.py::propuestas_de_pendientes` (10c).
- `ui/composicion.py`: `sugerir_partidas_similares(partidas: Mapping[str, str], descripcion: str, cargar_normalizacion: Callable[[], ModuleType] = _importar_normalizacion) -> Propuesta` (antes devolvía `list[PartidaSimilar]`). Conserva la costura `cargar_normalizacion`. `Propuesta` se importa bajo `if TYPE_CHECKING:`.
- `ui/elaboracion.py::propuestas_de_pendientes`: misma firma y mismo retorno que en la Tarea 7; solo cambia su cuerpo.

- [ ] **10a (ml, pista B).** En `ml/normalization/normalizador.py`, que ya existe (**ningún archivo nuevo**):

```python
FALLAS_DE_LA_PROPUESTA: tuple[type[Exception], ...] = (ImportError, OSError, ValueError, RuntimeError)
_registro = logging.getLogger(__name__)


class TieneDescripcion(Protocol):
    """Lo unico que `propuestas_para` necesita de un pendiente (un `ItemComputo`, en la practica)."""

    @property
    def descripcion(self) -> str: ...


@dataclass(frozen=True, slots=True)
class Propuesta:
    similares: tuple[PartidaSimilar, ...]
    falla: str | None = None  # "Tipo: mensaje" si el modelo no pudo proponer


def proponedor(partidas: Mapping[str, str]) -> Callable[[str], Propuesta]:
    """El criterio unico de UC-03 (INV-081): construye el normalizador una vez; ante una de
    FALLAS_DE_LA_PROPUESTA, al construir o al consultar, devuelve Propuesta vacia con su falla y
    lo registra con logging.warning. Cualquier otra excepcion se propaga."""


def propuestas_para[P: TieneDescripcion](
    partidas: Mapping[str, str], pendientes: Sequence[P]
) -> tuple[tuple[P, Propuesta], ...]:
    """UC-01 3a con UC-03: cada pendiente con la propuesta para su descripcion, en su orden. Un
    solo `proponedor` por llamada, y ninguno sin pendientes (cargar el modelo cuesta segundos y
    la primera vez puede descargarlo). Es el unico emparejamiento: la API y ui/ lo comparten."""
```

  - Exportar `FALLAS_DE_LA_PROPUESTA`, `Propuesta`, `proponedor`, `propuestas_para` y `TieneDescripcion` en `__init__` y en `__all__`.
  - Pruebas en `test_normalizacion.py`. El extra ausente, el modelo ausente y los pesos corruptos se simulan con `monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", …)` que lanza cada falla (el `NormalizadorPartidas` real la propaga desde su `__init__`); la falla al consultar, con un `NormalizadorPartidas` doble en el submódulo cuyo `similares` lanza:
    - por cada una de las cuatro fallas, al construir y al consultar: `Propuesta((), "OSError: …")` y un aviso en `caplog` del registrador `ml.normalization.normalizador` que nombra el tipo;
    - `KeyError` se propaga;
    - `propuestas_para` con dos pendientes construye el normalizador **una** vez (doble que cuenta construcciones) y devuelve los dos pares en su orden; sin pendientes, ninguna construcción.
  - Rojo: `ImportError`. Mordidas tras el verde, restauradas después:
    - quitar `RuntimeError` de la tupla: falla la prueba de ese parámetro;
    - construir un `proponedor` por pendiente dentro de `propuestas_para`: falla la prueba de «una construcción».
  - La guardia de `ml/` (`test_ml_solo_importa_core_contracts_del_nucleo`, `tests/unit/test_arquitectura.py:56`; A‑8) queda verde.
  - Commit `refactor(ml): criterio unico de fallas para proponer partidas similares`.
- [ ] **10b (api, pista B, después de la Tarea 11).**
  - `_pendientes` usa `propuestas_para(descripciones, pendientes)`. Se borran `_proponedor` y la tupla local `api/rutas/presupuestos.py:72`. `propuestas_para` se importa al principio del módulo: `ml.normalization` ya no arrastra el extra (`normalizador.py:49-53`).
  - **Reescritura declarada de las pruebas de `tests/integration/test_api.py`** (QA‑4). Hoy sustituyen `sys.modules["ml.normalization"]` por un `SimpleNamespace(NormalizadorPartidas=...)` o por `None`. Con `propuestas_para`, la API importa un nombre que ese doble no tiene, y `proponedor` resuelve `NormalizadorPartidas` en su propio módulo, saltándose el doble. Cada una pasa a parchar el submódulo:
    - `:365` (dentro de `test_un_item_sin_partida_queda_pendiente_por_http`, el cableado): `monkeypatch.setattr("ml.normalization.normalizador.NormalizadorPartidas", _NormalizadorDoble)`, con el mismo doble y las mismas aserciones.
    - `:406` (`test_sin_el_extra_ml_el_pendiente_queda_sin_propuestas`): `monkeypatch.setattr("ml.normalization.normalizador._cargar_modelo", _sin_extra)`, donde `_sin_extra` lanza `ImportError("simulado: sin sentence-transformers")`, que es como falla de verdad el extra ausente.
    - `:441` (`test_sin_el_modelo_el_pendiente_queda_sin_propuestas`): el mismo `_NormalizadorSinModelo`, parchado en el submódulo; el `caplog` pasa a `logger="ml.normalization.normalizador"` y el filtro `a.name ==` también.
    - `:517` (`test_si_similares_falla_el_pendiente_queda_sin_propuestas`): el mismo `_NormalizadorQueFallaAlProponer`, parchado en el submódulo; el `caplog`, igual que el anterior.
    - `:547` (`test_si_todos_los_items_quedan_pendientes…`): `_cargar_modelo` parchado con `_sin_extra`, en vez de `sys.modules[...] = None`.
  - Rojo declarado de la reescritura (QA‑17): con las pruebas ya reescritas y la API todavía sin cambiar, el rojo corre **sin red** para que la API vieja no descargue el modelo real de Hugging Face (RQ‑2): en PowerShell, `$env:HF_HUB_OFFLINE = "1"; uv run pytest tests/integration/test_api.py -k "propuestas or pendiente" -q; Remove-Item Env:HF_HUB_OFFLINE`. El doble del submódulo no llega al `_proponedor` viejo, que toma la `NormalizadorPartidas` real que reexporta el paquete, y los avisos siguen saliendo del registrador `api.rutas.presupuestos`. **Deben fallar** las de cableado y `caplog`: `:365` (`test_un_item_sin_partida_queda_pendiente_por_http`), `:441` (`test_sin_el_modelo_el_pendiente_queda_sin_propuestas`) y `:517` (`test_si_similares_falla_el_pendiente_queda_sin_propuestas`). **Pasan ya en rojo** `:406` y `:547`, las de `_cargar_modelo` parchado: la API vieja atrapa el `ImportError` y el pendiente queda sin propuestas igual; no es un rojo y no se cuenta como tal (su cambio lo cubre la mordida). Anotar la lista real en el expediente. Después se cambia la API y pasan las cinco.
  - Mordida: que `_pendientes` arme la respuesta sin llamar a `propuestas_para`, con `propuestas=[]`. Falla la aserción de propuestas de `test_un_item_sin_partida_queda_pendiente_por_http`; se restaura. El «un solo normalizador por llamada» lo prueba 10a sobre `propuestas_para`.
  - `docs/api.json` se regenera, y debe quedar sin cambios.
  - Commit `refactor(api): la propuesta de similares usa el criterio unico de ml`.
- [ ] **10c (ui, pista A, tras la Tarea 7 y las fusiones de B y C).** Va después de C porque edita `tests/unit/test_composicion_ia.py`, que la Tarea 14 cambia (A‑4).
  - **Rojo de C3‑4, por comportamiento** (QA‑4), en `tests/unit/test_composicion_ia.py`, escrito antes de tocar `ui/`: `test_sugerir_partidas_similares_propaga_lo_que_no_es_una_falla_declarada`, con `_cargar_modelo` parchado para lanzar `KeyError` y `pytest.raises(KeyError)`. Hoy falla, porque `ui/composicion.py:618-623` atrapa `Exception` y devuelve `[]`.
  - **Rojo de la página de similares, por comportamiento:** `tests/unit/test_ui_similares.py` (`AppTest`), con base sembrada en `tmp_path` y desviada por `ui.caso`, `_cargar_modelo` parchado para lanzar `RuntimeError` y una descripción tecleada. Espera `st.error` y ninguna excepción. **Hoy hay traza**, porque `similares.py:80-88` atrapa solo `OSError`.
  - Implementar, con las firmas del bloque Interfaces:
    - `sugerir_partidas_similares`: `normalizacion = cargar_normalizacion()`. Sin descripción o sin catálogo devuelve `normalizacion.Propuesta(())` sin llamar a `proponedor`; si no, `normalizacion.proponedor(partidas)(descripcion)`. El paquete `ml` es del repositorio y su `normalization` no importa el extra, así que `cargar_normalizacion()` no falla por falta del extra: esa falla llega desde `_cargar_modelo`, dentro de `proponedor`.
    - `componer.py::_sugerencias_similares` usa `propuesta.similares`.
    - `ui/paginas/similares.py` usa `sugerir_partidas_similares`, un solo normalizador por consulta. Si `propuesta.falla` empieza por `ImportError`, muestra `_MENSAJE_SIN_EXTRA_ML`; con otra falla, `st.error(f"El modelo de similitud no esta disponible: {propuesta.falla}")`. Se retira su `_cargar_normalizacion` y su propia construcción de `NormalizadorPartidas`.
    - `ui/elaboracion.py::propuestas_de_pendientes` pasa a `propuestas_para` (import perezoso de `ml.normalization` dentro de la función): `tuple(PendienteConPropuestas(item, p.similares, p.falla) for item, p in propuestas_para(partidas, pendientes))`. Es un solo normalizador por elaboración, y el mismo emparejamiento que la API.
  - **Reescritura declarada de `tests/unit/test_composicion_ia.py`** (QA‑4): los dobles de `:54-99` y `:330` usan la costura `cargar_normalizacion` con un módulo que tiene `NormalizadorPartidas`, y 10c cambia lo que la costura debe ofrecer.
    - `_modulo_normalizacion(resultado)` devuelve `SimpleNamespace(Propuesta=Propuesta, proponedor=…)`, cuyo `proponedor(partidas)` afirma un catálogo no vacío y devuelve `lambda descripcion: Propuesta(tuple(resultado))`.
    - `:67`: `propuesta.similares == tuple(resultado)` y `propuesta.falla is None`.
    - `:80` (la ayuda lanza): costura por defecto y `_cargar_modelo` parchado con `_que_falla`. Da `Propuesta` vacía cuya `falla` empieza por `"RuntimeError"`.
    - `:87` (sin el extra): `_cargar_modelo` parchado con `_que_falla_por_extra_ausente`. La `falla` empieza por `"ImportError"`.
    - `:94` (sin descripción): un módulo doble cuyo `proponedor` lanza `AssertionError`. Da `Propuesta(())`, así que nunca se llamó.
    - `:330`: la llamada a `sugerir_partidas_similares` usa la costura por defecto con `_cargar_modelo` parchado con `_que_falla`.
    - La prueba de `propuestas_de_pendientes` de la Tarea 7 (`test_ui_elaborar.py`) se reescribe igual. Parcha `ml.normalization.normalizador.NormalizadorPartidas` con un doble que cuenta construcciones: con dos pendientes, **una** construcción y dos entradas en orden; sin pendientes, ninguna. Mordida: una construcción por pendiente; falla.
  - Verde: `uv run pytest tests/unit/test_composicion_ia.py tests/unit/test_ui_similares.py tests/unit/test_ui_elaborar.py tests/unit/test_ui_componer.py -q -W error --strict-markers` y el recuento.
  - Mordida de la página: volver a atrapar solo `OSError` en `similares.py`. La prueba `AppTest` falla; se restaura.
  - Commit `refactor(ui): la propuesta de similares usa el criterio unico de ml`.

### Task 11: INV‑080, la recarga del informe conserva los pendientes (pista B), e INV‑083 (pista A)

**Interfaces:**
- Produce (commit de `core/budget/`): `guardar_presupuesto(..., pendientes: Sequence[ItemComputo] = ())` y `cargar_elaboracion(session, proyecto_nombre: str, codigo: str, catalogo: Catalogo) -> ResultadoElaboracion`, exportada en `core.budget`. `cargar_presupuesto` no cambia de firma ni de retorno: el contrato `Presupuesto` es estable (CLAUDE.md §5).
- Consume (paso 8, pista A): `cargar_elaboracion` en `ui/paginas/escenarios.py` (INV‑083).

- [ ] **Step 1: Expediente previo.** Crear `docs/bitacora/2026-09-24-C3-expedientes.md` §C3.1. Remite al expediente C2.1 sin repetirlo y fija el diseño de la opción (a):
  - `guardar_presupuesto(..., pendientes: Sequence[ItemComputo] = ())` persiste cada pendiente como `models.ItemComputo` del presupuesto **sin renglón**. El esquema no cambia: `item_computo.presupuesto_id` ya existe, `core/models/entidades.py:317`.
  - `ValueError` si un pendiente no tiene su hallazgo `PENDIENTE` en el informe.
  - `cargar_elaboracion(session, proyecto, codigo, catalogo) -> ResultadoElaboracion`:
    - `presupuesto` sale de `cargar_presupuesto`;
    - `pendientes`: los `item_computo` del presupuesto sin `partida_presupuestada`, ordenados por `id`;
    - `informe = _declarar_pendientes(auditar(presupuesto), pendientes)`. Se importa desde `core.budget.presupuesto` con un comentario, como hace el precedente `actualizacion.py:32-40`.
  - `actualizar_precios` arrastra los pendientes del base (D4 = A): `exigir_composiciones` solo sobre los valorados, y guarda con `pendientes`.
  - Límite declarado: los presupuestos guardados antes del cambio no tienen pendientes persistidos.
  - Alcance de D4 = A: recarga y revaloración, **no** escenarios. Los escenarios son INV‑083 (Hecho 11): su parte de `ui/` va en el paso 8, sin tocar `core/`; el informe del propio escenario y la ruta de la API quedan en el dictamen C3‑12.
  - La línea base, intacta.

  Commit `docs(bitacora): expediente previo de inv-080 para c3`.
- [ ] **Step 2: Rojo por comportamiento, a nivel de sistema.** En `tests/integration/test_api.py`, dos pruebas sobre `POST /presupuestos` con la línea base más `XX-99-NUE`:
  - después, `GET /presupuestos/{codigo}/informe` contiene `PENDIENTE`;
  - y `GET /presupuestos/{codigo}/excel` lleva la hoja de auditoría con `PENDIENTE`: el libro se abre con `openpyxl` desde los bytes de la respuesta (QA‑16).
  - Expected: las dos FAIL, porque las dos rutas recargan con `_cargar` (`api/rutas/presupuestos.py:186,195`) y el informe recargado no lo declara.
  - **No se agregan al índice**: entran en el commit del paso 5.
- [ ] **Step 3: Pruebas del núcleo.** En `tests/integration/test_recarga_con_pendientes.py` (base en `tmp_path`, motor cerrado y reabierto; las fixtures, en el propio archivo o en `tests/fixtures/`, nunca importadas de otro `test_*.py`: Global Constraints):
  1. **Ida y vuelta.** Los hallazgos recargados, como conjunto de `(regla, severidad, origen_ids)`, son iguales a los de `elaborar` en memoria, que es el oráculo por la otra ruta, **y** a los persistidos del documento emitido (`modelo.hallazgos`, con la lectura de `tests/integration/test_presupuesto_linea_base.py:95-107`), que es lo que el Review Focus 4 llama «el emitido» (QA‑16). `pendientes` iguales. No cumple.
  2. **Sin pendientes.** `cargar_elaboracion` coincide con `auditar(cargar_presupuesto(...))`, y el total es el de la fixture de la línea base.
  3. **Pendiente no declarado.** Da `ValueError`.
  4. **Revalorar (D4 = A).** `actualizar_precios` sobre un base con un pendiente: termina sin `ValueError`, la versión nueva declara `PENDIENTE`, y las filas del comparativo (`Comparativo.tabla`) son exactamente las partidas **valoradas** del base, en su orden: `_comparar` (`zip(strict=True)`) no recorre el pendiente (QA‑16, Review Focus 4).
  5. **Datos anteriores.** Guardado sin `pendientes`: la recarga no inventa ninguno.

  Rojo: `ImportError` de `cargar_elaboracion`, acompañado del rojo del paso 2.
- [ ] **Step 4: Implementar en `core/budget/`** (`persistencia.py`, `actualizacion.py` por D4 = A, `__init__.py`).

  Verde del paso 3, más tres mordidas:
  - `cargar_elaboracion` devuelve `auditar(presupuesto)` a secas: la prueba 1 falla.
  - `guardar_presupuesto` no persiste los pendientes: la prueba 1 falla por `pendientes` vacíos.
  - `actualizar_precios` guarda la versión nueva sin `pendientes`: la prueba 4 falla.

  Después, la línea base `27 0 0 0` y el recuento. **El recuento sale `N 2 0 0`, no `N 0 0 0`** (QA‑5): las dos pruebas del paso 2 siguen en el árbol, sin commit, en rojo hasta el paso 5. Se anotan sus dos nombres, y no se acepta ningún otro fallo. (Otra opción equivalente: el recuento con `--deselect` de esas dos, que debe dar `N 0 0 0`.)

```bash
git add core/budget/ tests/integration/test_recarga_con_pendientes.py
git commit -m "fix(budget): la recarga del informe conserva los items pendientes" -m "Cierra la parte de core de INV-080 (expediente C3.1, previo; C2.1): guardar_presupuesto persiste los pendientes como items sin renglon, sin cambiar el esquema; cargar_elaboracion reaudita y los vuelve a declarar. actualizar_precios arrastra los pendientes del base (D4 = A). Linea base 1586.61 y 7 de 7 intactas. Primera de las dos excepciones de core/ en C3 (spec de cierre, seccion 5)." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

  Comprobar con `git show --stat HEAD` que el commit solo tiene `core/budget/*` y `tests/*`, y que `tests/integration/test_api.py` **no** está.
- [ ] **Step 5: Llamadores de `api/`, en commit aparte.**
  - `crear_presupuesto` pasa `pendientes=resultado.pendientes`.
  - `_cargar` usa `cargar_elaboracion`, así que lo usan `/informe` y `/excel`.
  - Las dos pruebas del paso 2 quedan en verde.
  - Mordida: `_cargar` vuelve a `auditar(cargar_presupuesto(...))`; fallan las dos; se restaura.
  - Regenerar `docs/api.json`.
  - El recuento: **`N 0 0 0`**.
  - Commit `fix(api): el informe recargado declara los pendientes`, con las dos pruebas del paso 2.
- [ ] **Step 6: (sin contenido propio).** La prueba del Excel entró en el paso 2 y su commit es el del paso 5 (QA‑16).
- [ ] **Step 7: Llamadores de `ui/`, en la pista B.** `grep -rn "guardar_presupuesto\|cargar_elaboracion" ui/` debe salir vacío (A‑1): en la pista B no hay commit de `ui/`. `ui/paginas/escenarios.py` sí llama a `cargar_presupuesto` (Hecho 11): eso lo corrige el paso 8, en la pista A. Se anota en el ledger para la bitácora.
- [ ] **Step 8: INV‑083 en `ui/` (pista A, después de fusionar B).** El escenario de un base con pendientes los declara en la página. Sin `core/`: usa `cargar_elaboracion`, que ya existe tras la fusión de B.
  - **Rojo por comportamiento.** `tests/unit/test_ui_escenarios.py` (`AppTest`, nuevo):
    - Base en `tmp_path`, desviada por `ui.caso`. Se prepara por el núcleo directo, como en la Tarea 12, paso 6: `sembrar`; `elaborar` de `items_auditados()` más el ítem `XX-99-NUE` de origen `T-99`; `guardar_presupuesto(..., pendientes=resultado.pendientes)`; `commit`.
    - La página se abre con ese presupuesto elegido y se genera un escenario con los parámetros por defecto.
    - Aserciones: `not at.exception`; un aviso (`at.warning`) que cita `T-99` y `XX-99-NUE` y dice que el escenario no los incluye; el total del escenario mostrado es el del base (`formatear_decimal(TOTAL_EXACTO_LINEA_BASE, DECIMALES_PRESENTACION)`, oráculo de la fixture: mismos parámetros).
    - Expected: FAIL, porque hoy la página carga con `cargar_presupuesto` (`escenarios.py:93`) y no dice nada de los pendientes.
  - **Implementar** en `ui/paginas/escenarios.py`: cargar el base con `cargar_elaboracion(...)`. `base = elaboracion.presupuesto` sigue alimentando `generar_escenario` y las tablas sin cambios. Si `elaboracion.pendientes` no está vacío, `st.warning` con cada origen y código, y la frase «los escenarios solo recalculan los renglones valorados; estos items no suman al total del base ni de ningun escenario (UC-01 3a)». El import de `cargar_presupuesto` sale de la página.
  - Mordida: ignorar `elaboracion.pendientes`. La prueba falla; se restaura.
  - Regresión: `uv run pytest tests/unit/test_ui_escenarios.py tests/integration/test_api_escenarios.py tests/unit/test_escenarios.py -q -W error --strict-markers` y el recuento.
  - Commit `fix(ui): los escenarios declaran los pendientes del presupuesto base`, que cierra la parte de C3 de INV‑083 (su resto, en el dictamen C3‑12).

### Task 12: INV‑015 7a, descartar la versión (D1 = A; pistas B y A)

**Files:**
- Modify: `docs/bitacora/2026-09-24-C3-expedientes.md` (§C3.2, pista B)
- Modify: `core/models/entidades.py`, `core/models/__init__.py`, `core/catalog/sesion.py:31`, `core/budget/actualizacion.py`, `core/budget/__init__.py` (pista B)
- Modify: `tests/integration/test_actualizacion_precios.py`, `tests/integration/test_persistencia.py` (pista B)
- Modify: `ui/paginas/actualizacion.py`; Create: `tests/unit/test_ui_actualizacion.py` (pista A, tras la Tarea 6 y la fusión de B)
- Modify: `docs/modelo_datos.md` (`:22` y §2.2), `docs/arquitectura.md:275,417,427` (pista A)

**Interfaces:**
- Consumes: `actualizar_precios` de la Tarea 11 (pendientes arrastrados, D4 = A); `_buscar` de `core/budget/persistencia.py:203`; `ruta_caso()` de `ui/caso.py` a través del diccionario de `_barra_lateral` migrado en la Tarea 6.
- Produces: `models.DescarteVersion` y `descartar_version(session, proyecto_nombre, codigo_presupuesto, fecha) -> models.DescarteVersion`, exportada en `core.budget`.

**¿Existe la capacidad?** No. «Descartar» hoy es no confirmar la transacción, que también deshace los `CambioPrecio` (expediente B.8), y la interfaz confirma la versión en cuanto cambia un insumo (`ui/paginas/actualizacion.py:207-223`). No hay dato que marque una versión como descartada.

- [ ] **Step 1: Expediente previo C3.2** en `docs/bitacora/2026-09-24-C3-expedientes.md`. Remite a B.8 sin repetirlo y fija:
  - La tabla `descarte_version` (`presupuesto_id` clave primaria y foránea a `presupuesto.id` con `ondelete="CASCADE"`, así que única y sin bloquear el borrado de un presupuesto con `PRAGMA foreign_keys=ON`, `core/catalog/sesion.py:51`, A‑11; `fecha`) es aditiva: `crear_esquema` (`create_all`) la agrega a las bases existentes sin tocar las otras quince, así que no es una migración (spec §2). Dictamen C3‑1.
  - «Última versión»: el presupuesto de mayor `id` del proyecto, siempre que haya al menos otro anterior. El base nunca se descarta, ni una versión dos veces.
  - La versión descartada sigue guardada y cargándose como documento. Los `CambioPrecio` y las `IncidenciaCambio` se conservan (`docs/ERS.md:170`).
  - No confirma la transacción: la confirma la página, como con `actualizar_precios`.
  - La línea base, intacta; el commit solo toca los cinco archivos de `core/` de esta tarea y sus pruebas.

  Commit:

```bash
git add docs/bitacora/2026-09-24-C3-expedientes.md
git commit -m "docs(bitacora): expediente previo de inv-015 7a para c3" -m "Segunda excepcion de core/ en C3 (D1 = A): tabla aditiva descarte_version y descartar_version; el historial de cambios se conserva (ERS, UC-02 7a)." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 2: Pruebas del núcleo, en rojo.** Al final de `tests/integration/test_actualizacion_precios.py`, con sus fixtures `sesion`, `presupuesto_001` y `actualizacion`; `descartar_version` se suma al `from core.budget import (...)` del archivo:

```python
# ---------------------------------------------------------------------------------------------
# UC-02, flujo 7a: descartar la version nueva (INV-015, expediente C3.2)
# ---------------------------------------------------------------------------------------------


def _contar(sesion, entidad) -> int:
    return len(sesion.scalars(select(entidad)).all())


def test_descartar_la_version_nueva_la_marca_y_conserva_el_historial(sesion, actualizacion):
    """`docs/ERS.md:170`: se marca como descartada y el registro de cambios se conserva."""
    nuevo, _ = actualizacion
    sesion.commit()
    incidencias = _contar(sesion, models.IncidenciaCambio)

    marca = descartar_version(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, FECHA_NUEVA)
    sesion.commit()

    assert marca.presupuesto.codigo == CODIGO_NUEVO
    assert marca.fecha == FECHA_NUEVA
    assert _contar(sesion, models.DescarteVersion) == 1
    # Oraculo: la muestra cambia exactamente dos insumos (tests/fixtures/actualizacion_uc02.py).
    assert _contar(sesion, models.CambioPrecio) == len(PRECIOS_NUEVOS) == 2
    assert _contar(sesion, models.IncidenciaCambio) == incidencias
    # La version descartada sigue siendo un documento que se carga.
    recargado = cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, Catalogo(sesion))
    assert recargado.total == nuevo.presupuesto.total


def test_el_presupuesto_base_nunca_se_descarta(sesion, actualizacion):
    sesion.commit()
    with pytest.raises(ValueError, match="ultima version"):
        descartar_version(sesion, NOMBRE_PROYECTO, linea_base.CODIGO_PRESUPUESTO, FECHA_NUEVA)


def test_sin_version_revalorada_no_hay_nada_que_descartar(sesion, presupuesto_001):
    sesion.commit()
    with pytest.raises(ValueError, match="ultima version"):
        descartar_version(sesion, NOMBRE_PROYECTO, linea_base.CODIGO_PRESUPUESTO, FECHA_NUEVA)


def test_una_version_no_se_descarta_dos_veces(sesion, actualizacion):
    sesion.commit()
    descartar_version(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, FECHA_NUEVA)
    with pytest.raises(ValueError, match="ya esta descartada"):
        descartar_version(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, FECHA_NUEVA)
```

  Y en `tests/integration/test_persistencia.py` (usa `crear_motor` y `abrir_sesion`, ya importados; suma `from sqlalchemy import inspect` y `from core.catalog import crear_esquema`):

```python
def test_crear_esquema_agrega_descarte_version_a_una_base_existente(tmp_path):
    """Expediente C3.2: la tabla es aditiva; una base creada sin ella la recibe sin perder datos."""
    motor = crear_motor(f"sqlite:///{(tmp_path / 'anterior.db').as_posix()}")
    try:
        anteriores = [t for t in models.Base.metadata.sorted_tables if t.name != "descarte_version"]
        models.Base.metadata.create_all(motor, tables=anteriores)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()  # QA-1: `sembrar` solo hace flush y `abrir_sesion` revierte al cerrar
            partidas = _contar(sesion, models.Partida)

        crear_esquema(motor)

        assert "descarte_version" in inspect(motor).get_table_names()
        with abrir_sesion(motor) as sesion:
            assert _contar(sesion, models.Partida) == partidas == len(linea_base.APUS_LINEA_BASE)
        # A-11: borrar un presupuesto no queda bloqueado por su marca (PRAGMA foreign_keys=ON).
        (clave,) = inspect(motor).get_foreign_keys("descarte_version")
        assert clave["options"].get("ondelete") == "CASCADE"
    finally:
        motor.dispose()
```

  `_contar` ya existe en `tests/integration/test_persistencia.py:35` (`func.count`): la prueba nueva **reusa** ese ayudante y **no** define otra copia, que lo sombrearía en silencio sin que ruff lo marque (RQ‑1). Tampoco se importa de `test_actualizacion_precios.py` (Global Constraints, INV‑052).

  Run: `uv run pytest tests/integration/test_actualizacion_precios.py tests/integration/test_persistencia.py -q -k "descart" -W error --strict-markers`
  Expected: FAIL. `ImportError` de `descartar_version` en el primer archivo y, en el segundo, la aserción `"descarte_version" in inspect(motor).get_table_names()`: es el rojo por comportamiento, porque hoy `crear_esquema` no crea esa tabla. Antes de esa aserción, la de las partidas **no** falla: el `commit` tras `sembrar` las deja confirmadas (sin él, la segunda sesión contaría 0 y la prueba nunca pasaría a verde, QA‑1).

- [ ] **Step 3: Implementar en `core/`.**
  - `core/models/entidades.py`, después de `Presupuesto`, y el docstring del módulo (`:1`) pasa de «Las quince entidades» a «Las dieciséis entidades»:

```python
class DescarteVersion(Base):
    """UC‑02, flujo 7a: la versión revalorada que el usuario descartó.

    Es una marca, no un borrado: la versión sigue guardada y cargándose como documento, y el
    historial de cambios que la produjo (`CambioPrecio`, `IncidenciaCambio`) se conserva porque
    alimenta el histórico del módulo predictivo (`docs/ERS.md:170`). Tabla aditiva: `crear_esquema`
    la agrega a una base existente sin tocar las demás (expediente C3.2).
    """

    __tablename__ = "descarte_version"

    presupuesto_id: Mapped[int] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="CASCADE"), primary_key=True
    )
    fecha: Mapped[date] = mapped_column(Date)

    presupuesto: Mapped[Presupuesto] = relationship()
```

  - `core/models/__init__.py`: `DescarteVersion` en el `from core.models.entidades import (...)` y en `__all__`, en orden alfabético.
  - `core/catalog/sesion.py:31`: `"""Crea las dieciséis tablas y sus índices si aún no existen."""`.
  - `core/budget/actualizacion.py`: `from datetime import date` en los imports, `"descartar_version"` en `__all__` y, después de `actualizar_precios`:

```python
def descartar_version(
    session: Session, proyecto_nombre: str, codigo_presupuesto: str, fecha: date
) -> models.DescarteVersion:
    """UC‑02, flujo 7a: marca como descartada la última versión revalorada del proyecto.

    La versión sigue guardada y cargándose como documento, y el historial de cambios que la
    produjo (`CambioPrecio`, `IncidenciaCambio`) se conserva (`docs/ERS.md:170`). Solo se descarta
    la última versión (la de mayor `id`) de un proyecto que tenga al menos otra anterior —el
    presupuesto base nunca— y una sola vez; en otro caso, `ValueError`. No confirma la
    transacción: como `actualizar_precios`, la confirma el llamador.
    """
    modelo = _buscar(session, proyecto_nombre, codigo_presupuesto)
    versiones = session.scalars(
        select(models.Presupuesto.id)
        .where(models.Presupuesto.proyecto_id == modelo.proyecto_id)
        .order_by(models.Presupuesto.id)
    ).all()
    if len(versiones) < 2 or modelo.id != versiones[-1]:
        raise ValueError(
            f"solo se descarta la ultima version revalorada del proyecto {proyecto_nombre!r}, "
            f"y {codigo_presupuesto!r} no lo es"
        )
    if session.get(models.DescarteVersion, modelo.id) is not None:
        raise ValueError(f"la version {codigo_presupuesto!r} ya esta descartada")
    marca = models.DescarteVersion(presupuesto_id=modelo.id, fecha=fecha)
    session.add(marca)
    session.flush()
    return marca
```

  - `core/budget/__init__.py`: `descartar_version` en el `from core.budget.actualizacion import (...)` y en `__all__`, en orden alfabético.

- [ ] **Step 4: Verde, mordidas y línea base.**
  - Run: el comando del paso 2. Expected: PASS (5 pruebas).
  - La aserción de `ondelete` es estructural: la cubre la mordida 3.
  - Mordida 1: quitar `len(versiones) < 2 or`. Debe fallar `test_sin_version_revalorada_no_hay_nada_que_descartar`; se restaura.
  - Mordida 2: sustituir la marca por `session.execute(delete(models.CambioPrecio))` antes de agregarla. Debe fallar `test_descartar_la_version_nueva_la_marca_y_conserva_el_historial`; se restaura.
  - Mordida 3: quitar `ondelete="CASCADE"`. Debe fallar `test_crear_esquema_agrega_descarte_version_a_una_base_existente`; se restaura.
  - Línea base `27 0 0 0` y el recuento.

- [ ] **Step 5: Commit de núcleo** (segunda excepción de `core/`):

```bash
git add core/models/entidades.py core/models/__init__.py core/catalog/sesion.py core/budget/actualizacion.py core/budget/__init__.py tests/integration/test_actualizacion_precios.py tests/integration/test_persistencia.py
git commit -m "feat(budget): descartar la version revalorada conserva el historial" -m "Cierra la parte de core de INV-015 7a (expediente C3.2, previo; B.8): tabla aditiva descarte_version, que crear_esquema agrega sin tocar las demas; descartar_version marca la ultima version, nunca el base ni dos veces, y conserva CambioPrecio e IncidenciaCambio. Linea base 1586.61 y 7 de 7 intactas. Segunda de las dos excepciones de core/ en C3 (spec de cierre, seccion 5; D1 = A)." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
git show --stat HEAD
```

  Expected: solo los cinco archivos de `core/` nombrados y los dos de `tests/integration/`.

- [ ] **Step 6: Botón de `ui/`, en rojo** (pista A, después de la Tarea 6 y de fusionar B). `tests/unit/test_ui_actualizacion.py`:

```python
"""UC-02 7a en la interfaz (INV-015): el boton marca la version y conserva el historial."""

from __future__ import annotations

import importlib
from datetime import date
from pathlib import Path

from pandas import DataFrame
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from core import models
from core.budget import actualizar_precios, elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import (
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
)
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.conftest import RUTA_BASE_REAL, huella
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import PRECIOS_NUEVOS
from tests.fixtures.computo_auditado import items_auditados

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"
SCRIPT = "from ui.paginas.actualizacion import render\nrender()\n"
CODIGO_NUEVO = "002"


def _base_con_version_nueva(ruta: Path) -> None:
    """001 guardado y 002 revalorado con la muestra, ambos confirmados, por el nucleo directo."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            catalogo = Catalogo(sesion)
            codigos = [apu.codigo_partida for apu in linea_base.APUS_LINEA_BASE]
            resultado = elaborar(
                items_auditados(),
                catalogo.composiciones(codigos, fecha=linea_base.FECHA_LINEA_BASE),
                linea_base.PARAMETROS_LINEA_BASE,
                codigo=linea_base.CODIGO_PRESUPUESTO,
                fecha=linea_base.FECHA_LINEA_BASE,
                moneda=linea_base.MONEDA,
                plan=plan_secuencial,
            )
            guardar_presupuesto(
                sesion,
                resultado.presupuesto,
                resultado.informe,
                proyecto=proyecto,
                lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
                parametros=linea_base.PARAMETROS_LINEA_BASE,
            )
            lista = crear_lista_desde_archivo(
                sesion,
                MUESTRA,
                nombre="Lista 01/06/2026",
                moneda=linea_base.MONEDA,
                fecha_vigencia=date(2026, 6, 1),
                origen=MUESTRA.name,
            )
            actualizar_precios(
                sesion, NOMBRE_PROYECTO, linea_base.CODIGO_PRESUPUESTO, lista.lista, CODIGO_NUEVO
            )
            sesion.commit()
    finally:
        motor.dispose()


def _contar(ruta: Path, entidad) -> int:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return len(sesion.scalars(select(entidad)).all())
    finally:
        motor.dispose()


def test_descartar_version_marca_la_version_y_conserva_el_historial(monkeypatch, tmp_path):
    base = tmp_path / "caso.db"
    _base_con_version_nueva(base)
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(base))
    pagina = importlib.import_module("ui.paginas.actualizacion")
    antes = huella(RUTA_BASE_REAL)

    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.session_state[pagina.CLAVE_RESULTADO] = pagina.Presentacion(
        tabla=DataFrame(),
        resumen="",
        informe="",
        desconocidos=(),
        libro=b"",
        nombre_libro="presupuesto_002.xlsx",
        proyecto=NOMBRE_PROYECTO,
        version_guardada=CODIGO_NUEVO,
    )
    at.run()
    boton = next(b for b in at.button if b.label == "Descartar version")
    boton.click().run()

    assert not at.exception
    assert _contar(base, models.DescarteVersion) == 1
    assert _contar(base, models.CambioPrecio) == len(PRECIOS_NUEVOS)
    assert huella(RUTA_BASE_REAL) == antes


def test_sin_version_guardada_no_hay_boton_de_descartar(monkeypatch, tmp_path):
    caso = importlib.import_module("ui.caso")
    monkeypatch.setattr(caso, "RUTA_BASE_POR_DEFECTO", str(tmp_path / "vacio.db"))
    pagina = importlib.import_module("ui.paginas.actualizacion")

    at = AppTest.from_string(SCRIPT, default_timeout=60)
    at.session_state[pagina.CLAVE_RESULTADO] = pagina.Presentacion(
        tabla=DataFrame(),
        resumen="",
        informe="",
        desconocidos=(),
        libro=b"",
        nombre_libro="presupuesto_002.xlsx",
        proyecto=NOMBRE_PROYECTO,
        version_guardada=None,
    )
    at.run()

    assert not at.exception
    assert "Descartar version" not in [b.label for b in at.button]
```

  Run: `uv run pytest tests/unit/test_ui_actualizacion.py -q -W error --strict-markers`
  Expected: FAIL. El rojo es **estructural**: `TypeError` al construir `Presentacion`, que no acepta `proyecto` ni `version_guardada` (QA‑19). El comportamiento lo cubre la mordida del paso 8 (sin `commit`, la marca no queda), que es la que prueba que el botón de verdad marca la versión.

- [ ] **Step 7: Implementar en `ui/paginas/actualizacion.py`.**
  - `Presentacion` gana `proyecto: str` y `version_guardada: str | None`, el código de la versión confirmada en esta ejecución.
  - En `_actualizar`, la `Presentacion` se construye **después** de decidir: `version_guardada=str(parametros["codigo_nuevo"])` solo en la rama que llama a `sesion.commit()`; `None` en la rama de UC‑02 3a.
  - `render` pasa la ruta del caso: `_mostrar(st.session_state.get(CLAVE_RESULTADO), parametros["ruta"])`.
  - Constante y función nuevas, y el bloque al final de `_mostrar`:

```python
CLAVE_DESCARTADA = "actualizacion_version_descartada"


def _descartar(ruta: Path, presentacion: Presentacion) -> None:
    """UC-02 7a: marca la version nueva como descartada; su historial de cambios se conserva."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            descartar_version(
                sesion, presentacion.proyecto, presentacion.version_guardada, date.today()
            )
            sesion.commit()
        st.session_state[CLAVE_DESCARTADA] = presentacion.version_guardada
    except (LookupError, ValueError, SQLAlchemyError) as error:
        st.error(str(error))
    finally:
        motor.dispose()
```

```python
    if presentacion.version_guardada is not None:
        if st.session_state.get(CLAVE_DESCARTADA) == presentacion.version_guardada:
            st.info(
                f"Version {presentacion.version_guardada} descartada: sigue guardada como "
                "documento y su historial de cambios se conserva (UC-02, flujo 7a)."
            )
        elif st.button("Descartar version"):
            _descartar(ruta, presentacion)
```

  - `descartar_version` se suma al `from core.budget import ...` de la página. `_mostrar` recibe `ruta: Path` como segundo parámetro.

- [ ] **Step 8: Verde, mordida y commit de `ui/`.**
  - Run: el comando del paso 6. Expected: PASS (2 pruebas).
  - Mordida: quitar `sesion.commit()` de `_descartar`. Debe fallar la primera prueba (`DescarteVersion` = 0); se restaura.
  - Commit:

```bash
git add ui/paginas/actualizacion.py tests/unit/test_ui_actualizacion.py
git commit -m "feat(ui): boton descartar version en la actualizacion de precios" -m "Cierra INV-015 7a en la interfaz: tras confirmar una version en esta ejecucion, el boton la marca con descartar_version y el historial de cambios se conserva (ERS, UC-02 7a)." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 9: Documentos derivados** (redactor técnico, pista A).
  - `docs/modelo_datos.md` §2.2: la entidad `DescarteVersion` (clave, fecha, relación con `Presupuesto`, regla de 7a) y su caja en el diagrama de §3.
  - `docs/modelo_datos.md:22` («Quince entidades», con mayúscula; A‑10) y `docs/arquitectura.md:275`, `:417` y `:427`: «quince» pasa a «dieciséis».
  - `docs/tesis/capitulos/04-desarrollo.md:195` («quince entidades») y `:983` (4.6, «corrección de la interfaz») **no** se tocan en C3: se anotan en el ledger para Red y la matriz de C4.
  - Comprobar: `grep -rniw --include=*.py "quince" core/` y `grep -niw "quince" docs/arquitectura.md docs/modelo_datos.md` salen vacíos. `-i` ve la mayúscula de `modelo_datos.md:22` (A‑10) e `--include=*.py` deja fuera los `.pyc` de `__pycache__` (QA‑13).
  - Commit `docs(modelo): la entidad descarte_version de uc-02 7a`.

### Task 13: INV‑019, INV‑020 e INV‑025 (pista C)

- **INV‑019.**
  - Rojo por comportamiento: `cd tests && uv run pytest unit/test_referencia_maprex.py unit/test_fuentes_arenaza.py -q -p no:cacheprovider` falla (7 casos).
  - Luego se ancla en `Path(__file__).resolve().parents[2]` (`test_referencia_maprex.py:6`, `test_fuentes_arenaza.py:14`).
  - El mismo comando, en verde.
  - Commit `test: las rutas de referencia no dependen del directorio de trabajo`.
- **INV‑020.**
  - Rojo: parchar **temporalmente** `date` del módulo con una subclase cuyo `today()` da `2026-01-01`. `test_seed_demo.py:91` y `:109` fallan.
  - Luego se fija la fecha en `seed_demo.FECHA_DEMO` y la mutación deja de afectar.
  - Commit `test(seed): la valoracion de la demostracion no depende del reloj`.
- **INV‑025.**
  - Mutación en dos direcciones: `simular` devuelve los precios sin variar. La aserción vieja pasa y la nueva falla.
  - La nueva: con `semilla=1`, exactamente `["Cemento Portland"]` y `Arena lavada == Decimal("30.00")`.
  - Commit `test(simulador): el filtro solo varia el insumo pedido`.

### Task 14: INV‑021 e INV‑024 (pista C)

- **INV‑021.**
  - Prueba nueva en `test_visor3d.py`: tras `with _SinIfcopenshell(...)`, `getattr(sys.modules["ui.paginas"], "visor") is sys.modules["ui.paginas.visor"]`. Hoy falla, porque la copia del visor no sincroniza el atributo del paquete.
  - Luego un solo gestor, `tests/fixtures/sin_extra.py::SinExtra(monkeypatch, bloqueados, relacionados)`, con la sincronización de `test_composicion_ia.py:397-417`. Lo usan los dos archivos.
  - Commit `test: un solo gestor sin extra con los atributos de paquete sincronizados`.
- **INV‑024.**
  - Las aserciones `is not None` (`test_visor3d.py:83-85` y `test_composicion_ia.py:430-431`) se sustituyen por `callable(modulo.render)`.
  - Prueba nueva en su propio archivo, `tests/unit/test_extras_perezosos.py` (pista C). Usa la ayuda única `tests/fixtures/subproceso.py` de la Tarea 1, paso 8 (A‑13), sin otro arnés de subproceso:

```python
"""INV-024: importar la interfaz no carga los extras `civil` ni `ml` (se cargan al usarlos)."""

import importlib.util

import pytest

from tests.fixtures.subproceso import importar_en_limpio, modulos_cargados

EXTRAS = ("ifcopenshell", "sentence_transformers")


@pytest.mark.parametrize("extra", EXTRAS)
def test_importar_la_aplicacion_no_carga_el_extra(extra, tmp_path):
    # QA-12: sin el extra instalado la prueba saldria verde en vacio; primero se exige que exista.
    assert importlib.util.find_spec(extra) is not None, f"{extra} no esta instalado"
    salida = importar_en_limpio(["ui.app"], cwd=tmp_path)
    assert salida.returncode == 0, salida.stderr
    assert extra not in modulos_cargados(salida)
```

  - Mordida en las dos direcciones: `try: import ifcopenshell  # noqa` más `except ImportError: pass` al principio de `ui/visor3d.py`. La prueba vieja (`is not None`) pasa y la nueva falla en el parámetro `ifcopenshell`. Luego se restaura.
  - La CI instala todos los extras (`uv sync --locked --all-extras`, `.github/workflows/ci.yml:100`), así que la aserción de `find_spec` no deja la prueba en vacío en `ubuntu-latest` ni en `windows-latest`.
  - Commit `test: la importacion perezosa de los extras se comprueba de verdad`.

### Task 15: `scripts/` (pista D)

**Files:** los del Mapa, todos de la pista D. Las pruebas nuevas van en **archivos nuevos con nombre fijado**, fuera de `tests/unit/test_arquitectura.py` (pista A) y de `tests/integration/test_seed_demo.py` (pista C) (A‑5, QA‑15):
- `tests/unit/test_scripts_ruta_unica.py` (INV‑044)
- `tests/unit/test_scripts_resumen.py` (INV‑049)
- `tests/unit/test_reinicio_seguro.py` (INV‑050)
- `tests/unit/test_scripts_documentados.py` (INV‑051)

**Interfaces:**
- `scripts/seed.py::motivo_para_no_reiniciar(ruta: str, reiniciar: bool, confirmar: bool, por_defecto: str) -> str | None` (INV‑050).
- En `seed_demo.py`, `seed_industrial.py`, `seed_sistemas.py` y `seed_telecom.py`: `resumen(resultado: ResultadoElaboracion, moneda: str) -> str`, el texto que hoy imprime cada `main` (INV‑049). Es la costura que permite inyectar un total. Si un sembrador imprime además datos de su caso, se pasan como argumentos con nombre y se declara en el commit.

- **INV‑044 (scripts).**
  - Rojo: `test_la_ruta_de_trabajo_se_define_una_vez_en_scripts`, en `tests/unit/test_scripts_ruta_unica.py`, con regex sobre asignaciones y `default=` con `"data/apu.db"`. Hoy la encuentra en `seed_demo.py:122` y `simular_lista.py:86`.
  - Luego ambos importan `scripts.seed.RUTA_POR_DEFECTO`.
  - Dictamen C3‑6: `ui/caso.py` conserva su propia definición, parchable en las pruebas.
  - Commit `refactor(scripts): la ruta de trabajo se define una vez`.
- **INV‑049.**
  - Rojo, en `tests/unit/test_scripts_resumen.py`, parametrizado por los cuatro sembradores. Construye un `ResultadoElaboracion` con `core.budget.elaborar` sobre una composición mínima: un material de precio `Decimal("2.125")`, cantidad 1, rendimiento 1, sin equipos ni mano de obra, y `ParametrosCosto(administracion=Decimal(0), utilidad=Decimal(0))`.
    - Aritmética a mano: el total es exactamente 2,125. `:.2f` redondea al par y da `2.12`; `formatear_decimal` (`ROUND_HALF_UP`) da `2.13`.
    - Afirma que `"2.13"` está en `modulo.resumen(resultado, "USD")` y que `"2.12"` no está.
    - El rojo es `AttributeError` (la función se extrae), así que la mordida se hace tras el verde: devolver el total con `:.2f` en uno de los cuatro. Falla su parámetro; luego se restaura.
  - Luego `resumen` usa `formatear_decimal(valor, DECIMALES_PRESENTACION)` en los tramos que hoy tienen `:.2f`: `seed_demo.py:535-540`, `seed_industrial.py:257-259`, `seed_sistemas.py:250-252` y `seed_telecom.py:572-577`. Cada `main` imprime `resumen(...)`.
  - En `simular_lista.py:59`, el paso sale de `DECIMALES_PRESENTACION`.
  - Commit `fix(scripts): los resumenes de los sembradores redondean con la fuente unica`.
- **INV‑050.**
  - `scripts/seed.py::motivo_para_no_reiniciar(...)`, más `--confirmar` en los cinco `main` (`seed`, `seed_demo`, `seed_industrial`, `seed_sistemas`, `seed_telecom`).
  - Rojo en `tests/unit/test_reinicio_seguro.py`, parametrizado por módulo. **Hoy ese `main` hace `drop_all` sobre `RUTA_POR_DEFECTO`, que es relativa (`"data/apu.db"`, `"data/apu_industrial.db"`…), así que el rojo ejecuta código destructivo.** Por eso cada caso, **antes** de llamar a `main` (QA‑9, Global Constraints):
    1. `monkeypatch.chdir(tmp_path)`;
    2. `monkeypatch.setattr(modulo, "RUTA_POR_DEFECTO", str(tmp_path / "data" / nombre))`, con un centinela en esa ruta que es una **base SQLite sembrada** (`crear_esquema` más `scripts.seed.sembrar` y `commit`), no un archivo arbitrario: así el rojo de hoy es una base vaciada por `drop_all`, y no una excepción «file is not a database» (RQ‑4). La huella se toma tras sembrar;
    3. `assert Path(modulo.RUTA_POR_DEFECTO).resolve().is_relative_to(tmp_path.resolve())`. Si falla, la prueba se detiene sin haber llamado a `main`.

    Después, `main(["--reiniciar"])` debe devolver 2, escribir el motivo en `stderr` y dejar intacta la huella del centinela. Hoy hace `drop_all` sobre el centinela, que está en `tmp_path`.
  - Con `--confirmar` procede. Esa rama solo se prueba en `seed` y `seed_demo`, por tiempo, con las mismas tres precauciones.
  - Mordida tras el verde: `motivo_para_no_reiniciar` devuelve siempre `None`. Fallan los cinco parámetros; se restaura.
  - La preparación del guion (`docs/guion_prueba_arenia.md:79`, `--db data/prueba_arenia.db --reiniciar`) no cambia.
  - Documentos de la CLI que recomiendan `--reiniciar` sobre la ruta por defecto (A‑12): `README.md:29-30` y `docs/manual_tecnico.md:225` y `:350` pasan a decir que sobre la ruta por defecto hace falta `--confirmar`, y que con `--db <ruta>` basta `--reiniciar`.
  - Commits `fix(scripts): reiniciar la base por defecto exige confirmar` (código y prueba) y `docs(scripts): reiniciar la base por defecto exige confirmar` (`README.md` y `docs/manual_tecnico.md`).
- **INV‑051.**
  - Criterio declarado (QA‑14): cada `scripts/*.py` **salvo `scripts/__init__.py`** aparece en `scripts/README.md`. `__init__.py` es el paquete, y lo documenta su propio docstring. Hoy hay 25 archivos `.py`, y faltan 22 de los 24 que cuenta el criterio.
  - Rojo: `tests/unit/test_scripts_documentados.py` con ese criterio; cita los 22.
  - Luego la tabla, agrupada por sesión o dominio, y el docstring de `scripts/__init__.py`.
  - Mordida: quitar una fila de la tabla; falla citando ese archivo; se restaura.
  - Commit `docs(scripts): cada script tiene su fila en el readme`.

### Task 16: INV‑075, las metas R4–R8 leen todo capítulo presente (pista D)

- [ ] **Rojo por comportamiento.**
  - En `test_meta_redaccion.py` se parchan `RUTA_CAPITULO_1`, `RUTA_CAPITULO_2` y `CARPETA_CAPITULOS` (con `raising=False`) hacia `tmp_path`.
  - Los capítulos 01 y 02 cumplen; el `04-desarrollo.md` dice «hemos implementado».
  - `_evaluar_metas()` debe dar R4 FALLA citando «capitulo IV». Hoy da OK, porque ignora el capítulo 04 (`meta_redaccion.py:465-470`).
  - Lo mismo, parametrizado, para R5 (cita sin referencia), R6, R7 y R8.
- [ ] **Implementar.**
  - `CARPETA_CAPITULOS` y `capitulos_presentes(carpeta) -> dict[str, str]`: archivos `NN-*.md`, con el número pasado a romano y `README.md` excluido.
  - R1–R3 no cambian.
  - Docstring del módulo: «R4–R8 sobre todo capítulo presente».
- [ ] **Real.** `uv run python scripts/meta_redaccion.py` sigue 12/12: el capítulo IV de `main` pasa R4–R8, comprobado al planificar. Si falla, es un hallazgo de Red y **no** se parchea en `scripts/`.
- [ ] **Commit** `fix(scripts): las metas de redaccion revisan todo capitulo presente`.

### Task 17: INV‑076, registro sin código (D2)

C3 no escribe código de INV‑076. La Tarea 1, paso 7, ya dejó la fila «en duda (spec §2)» con la decisión D2. Esta tarea solo comprueba, antes de la Tarea 18, que nada de la rama la implementa a medias:

- [ ] Run: `git diff --name-only $(git merge-base main HEAD)..HEAD | grep -i "importar\|tercero"` y `grep -rn "presupuestos/importar" api/ ui/`.
  Expected: ambos vacíos.
- [ ] Anotar en el ledger de la pista A, para el dictamen C3‑2, que el diseño propio (superpowers:brainstorming: formato tabular del tercero, capa del analizador y persistencia de partidas ajenas) queda fuera de C3, y que INV‑076 cruza GC3 **abierto**.

### Task 18: Compuerta GC3 = GU1a

- [ ] **Step 1: Línea base.** El conjunto de GC1 y GC2 (`test_costing.py`, `test_costing_destajo.py::test_la_linea_base_no_se_mueve`, `test_budget.py::test_presupuesto_reproduce_1586_61`, `test_auditoria_7_de_7.py`, `test_composicion_extremo_a_extremo.py`) con `--junitxml` debe dar `27 0 0 0`.
- [ ] **Step 2: Guardia de arquitectura.** `test_arquitectura.py` en verde, incluidas las pruebas nuevas de las Tareas 6 y 8.
- [ ] **Step 3: Las dos excepciones de `core/`, exactas.** Con las cuatro pistas ya fusionadas:

```bash
bash .superpowers/sdd/2026-09-24-cierre-c3/guardia_gc3.sh 2; echo "codigo: $?"
B=$(git merge-base main HEAD)
PREVIAS="tests/integration/test_persistencia.py tests/integration/test_actualizacion_precios.py"
diff <(git diff -U0 "$B..HEAD" -- $PREVIAS | grep '^-[^-]') - <<'FIN' && echo "qa20: ok"
-from sqlalchemy import func, select
-from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_motor
FIN
git diff -U0 "$B..HEAD" -- $PREVIAS | grep -cxF -e '+from sqlalchemy import func, inspect, select' -e '+from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_esquema, crear_motor'
```

  El guion es el de la sección «Orquestación por roles», completo. Comprueba:
  - los commits sin fusión que tocan `core/`, cada uno con su asunto y su lista de archivos autorizada;
  - que ningún commit mezcle `core/` con otra capa salvo `tests/`;
  - que ninguna fusión cambie `core/` por su cuenta (`git diff-tree --cc`, A‑7 y QA‑2);
  - que no haya archivos agregados bajo `ml/` ni `adapters/`;
  - `guardia_nucleo.py` en la rama y contra una fusión de prueba en `main` (QA‑3).

  Termina con `exit 1` ante cualquier marca, así que el veredicto no depende de leer la salida.

  Expected:
  - `codigo: 0`, y en la salida exactamente dos `TOCA-CORE`: `fix(budget): la recarga del informe conserva los items pendientes` (INV‑080) y `feat(budget): descartar la version revalorada conserva el historial` (INV‑015 7a). Ninguna otra marca (`MEZCLA`, `FUERA-DE-080`, `FUERA-DE-7A`, `NO-AUTORIZADO`, `ASUNTOS`, `FUSION-TOCA-CORE`, `AGREGADO-EN-ML-O-ADAPTERS`, `GUARDIA-EN-LA-RAMA`, `GUARDIA-CONTRA-MAIN`, `FUSION-DE-PRUEBA-CON-MAIN-EN-CONFLICTO`, `LINEA-BASE-EDITADA`) y `marcas: 0`.
  - En el `--stat` de `core/` que imprime el guion, solo `core/budget/*`, `core/models/entidades.py`, `core/models/__init__.py` y `core/catalog/sesion.py`.
  - `qa20: ok` y el conteo final en `2` (QA‑20): el diff de las dos pruebas de persistencia
    previas solo agrega líneas, salvo **exactamente** estas dos, que cambian por un superconjunto
    de nombres. Al agregar las pruebas de INV‑015 7a, ruff (I001) **amplió** dos líneas de import
    existentes de `test_persistencia.py`: `from sqlalchemy import func, select` ganó `inspect` y
    `from core.catalog import …` ganó `crear_esquema`. Cualquier otra línea quitada, incluido un
    import redirigido, hace fallar el `diff`. Ninguna aserción cambia (revisión de B3, R‑2, y de
    A5, M‑2).
  - **Cualquier otra salida: GC3 no se cruza.**
- [ ] **Step 4: Suite y artefactos.**
  - El recuento: `N1 0 0 0`.
  - ruff limpio.
  - `test_salvaguarda.py`: `4 passed`.
  - `exportar_openapi.py` y `git diff --exit-code -- docs/api.json`.
  - `generar_resultados_ml.py` y `git diff --exit-code -- docs/resultados_ml.md`.
  - Metas: prototipo 12/12, redacción 12/12 y datos OK.
  - Anotar `N1` frente a `N0 = 750`, por tarea.
- [ ] **Step 5: Inventario.**
  - `cerrado (<hash>)`, con el hash del último commit de cada hallazgo: INV‑019, INV‑020, INV‑021, INV‑022, INV‑023, INV‑024, INV‑025, INV‑043, INV‑044, INV‑045, INV‑046, INV‑049, INV‑050, INV‑051, INV‑052, INV‑075, INV‑080 e INV‑081.
  - INV‑072: `cerrado (C2: ddd82b5, a02cb57; C3: <hash>)`.
  - INV‑015: `cerrado (C1: 0d9a310 para 2b; C3: <hash del commit de núcleo>, <hash del commit de ui> para 7a)`.
  - INV‑076: conserva, sin cambios, el estado que le dio la Tarea 1, paso 7 (D2).
  - INV‑047 e INV‑048 conservan «a limitaciones».
  - INV‑083 (fila abierta en la Tarea 1, paso 7): `abierto — C3 cerrado en ui/ (<hash del commit de la Tarea 11, paso 8>); resto (informe del escenario y ruta de la API) en C4, dictamen C3‑12`.
  - Las filas nuevas que aparezcan en la fase, desde INV‑084.
  - Recontar §4 (d) con un script ad hoc.
  - Anotar en INV‑070 (C4) el reparto de `componer.py` tras INV‑043.
- [ ] **Step 6: Bitácora.**
  - (a) Los hallazgos con estado y commit.
  - (b) Los hallazgos nuevos.
  - (c) `N0` y `N1`.
  - (d) Los dictámenes C3‑1 a C3‑n. Como mínimo:
    - C3‑1: la forma de 7a y la segunda excepción de `core/` (D1 = A; tabla aditiva, no migración);
    - C3‑2: INV‑076 fuera de C3, con diseño propio (D2);
    - C3‑3: los datos anteriores a INV‑080 sin pendientes persistidos;
    - C3‑4: la ayuda 1 deja de tragarse `Exception` (INV‑081);
    - C3‑5: `--confirmar` (INV‑050);
    - C3‑6: dos definiciones de la ruta de trabajo, una por capa (INV‑044);
    - C3‑7: los sub‑worktrees (D3);
    - C3‑8: `actualizar_precios` arrastra los pendientes (D4 = A);
    - C3‑9: 11c saca también el cálculo y la persistencia de `componer.py` (D5 = A);
    - C3‑10: el selector de propuestas en Elaborar (D6);
    - C3‑11: la base del worktree `prototipo`, declarada sucia y sin tocar (D7 = b);
    - C3‑12: INV‑083 se corrige en C3 solo en `ui/`. Que el informe del propio escenario lleve `PENDIENTE` exigiría un tercer commit de `core/` (`generar_escenario`), y la ruta de la API, un campo nuevo en `EscenariosRespuesta`: los dos van a C4 y los decide Eugenio (A‑1). Alcance de D4 = A: recarga y revaloración, no escenarios;
    - C3‑13: la Tarea 7 dejó `propuestas_de_pendientes` con un cuerpo provisional (un índice por pendiente), y 10c lo sustituyó por `propuestas_para` (A‑4). Anotar si 10c llegó antes de la Tarea 18.

    Cada uno con su costo si es erróneo.
  - (e) Los encargos.
  - (f) La ejecución de la aplicación.
  - (g) La redacción.
  - (h) La salida del paso 3.
  - La línea `**GC3 = GU1a: pendiente de CI.**`, y un enlace en `docs/bitacora/2026-09-23-sprint-ui.md`.
- [ ] **Step 7: Los cuatro encargos, en paralelo y en segundo plano**, sobre `git diff $(git merge-base main HEAD)..HEAD`, la spec, el inventario, los expedientes y este plan.
  - **Requisitos:** UC‑12 y RF‑36 a RF‑43, UC‑01 3a, RF‑02, UC‑02 7a, UC‑08 (INV‑083) y RF‑24. Que nada sea capacidad nueva.
  - **Arquitectura:** el paso 3 (las dos excepciones de `core/`), la regla de `ml/`, la extracción de INV‑043 (con `ui/composicion.py` puro y la persistencia en `ui/elaboracion.py`), las firmas del fragmento `ui/resultado.py` y de `propuestas_para`, y el ciclo `ui.app` → páginas.
  - **Pruebas y calidad:** los once puntos de Review Focus, los rojos observados y los oráculos.
  - **Verificación de hechos:** cada `archivo:línea` de este plan, del plan de UI enmendado, de los expedientes y de la bitácora.

  Cada uno devuelve **VEREDICTO** y hallazgos con severidad, sin editar. Los bloqueantes se corrigen en commits propios y se repasa solo el encargo que los levantó.
- [ ] **Step 8: Eugenio ejecuta y ratifica** (spec §6; paso 4 de la Tarea 13 de UI). Nunca contra `data/apu.db`.
  - En PowerShell: `$env:ARENIA_CASO = "$env:TEMP\humo_c3.db"; uv run python -m streamlit run ui/app.py`.
  - Comprobar:
    - abre en Inicio;
    - el estado vacío y la siembra funcionan;
    - «Siguiente» recorre catálogo → componer;
    - la barra lateral muestra el caso en cada pantalla;
    - en Elaborar, un ítem `XX-99-NUE` queda pendiente con sus propuestas, y «Aplicar y volver a elaborar» lo resuelve;
    - en Actualizar precios, tras revalorar con `data/samples/precios/lista_2026-06-01.csv`, «Descartar version» marca la versión y el aviso lo confirma;
    - con `ARENIA_MODO_ENTREGA=1`, la sección Trabajo está completa.
  - Después, en la API, `POST` y luego `GET /presupuestos/{codigo}/informe` declaran `PENDIENTE` (con `APU_BASE` en `$env:TEMP`, como en C2).
  - INV‑083: con `APU_BASE` apuntando al mismo `humo_c3.db`, el presupuesto con pendiente que guardó ese `POST` aparece en Escenarios, y la página muestra el aviso de sus pendientes al generar un escenario.
  - Al final: `data/apu.db` sin cambios, y nada ejecutado sobre `.claude/worktrees/prototipo/data/apu.db` (D7).
  - Ratificar los dictámenes.
- [ ] **Step 9: Commit** `docs(bitacora): compuerta gc3 del cierre, pendiente de ci`.
- [ ] **Step 10: Push y PR con permiso.** `gh pr create --base main --label gc3`. El cuerpo termina con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Después, `gh pr checks --watch`: calidad, `ubuntu-latest` y `windows-latest`.
- [ ] **Step 11: Declarar GC3 = GU1a cruzada solo con la CI en verde.** Con el hash que probó la CI y el número del PR. Commit `docs(bitacora): gc3 cruzada con la ci en verde`. La fusión, con merge commit, la decide Eugenio.

---

## Autorrevisión del plan

**Cobertura de los hallazgos de C3** (toda fila cuya «Fase destino» empieza por C3 o nombra una subtarea de C3):

| Hallazgo | Tarea | Cierre en C3 |
|---|---|---|
| INV‑015 7a (subtarea) | 12 | completo (D1 = A): expediente, segundo commit de `core/`, commit de `ui/` y documentos derivados |
| INV‑019, INV‑020, INV‑025 | 13 | completos, con rojo por comportamiento o mutación en dos direcciones |
| INV‑021, INV‑024 | 14 | completos |
| INV‑022, INV‑023 | 5 | completos, dentro de la Tarea 10 de UI |
| INV‑043 | 6 (11b y 11c) | completo solo dentro de la Tarea 11, como exige §5 |
| INV‑044 | 6 (ui) y 15 (scripts) | completo; una definición por capa (C3‑6) |
| INV‑045, INV‑046, INV‑052 | 8 | completos, después de la Tarea 11 |
| INV‑049, INV‑050, INV‑051 | 15 | completos |
| INV‑072 (ui) | 7 | completo, con el selector y «Aplicar y volver a elaborar» (D6) |
| INV‑075 | 16 | completo; no está bloqueado (Hecho 1) |
| INV‑076 | 1 (registro) y 17 (comprobación) | **sin código** (D2): en duda, diseño propio fuera de C3; cruza GC3 abierto |
| INV‑080 | 11 | completo (D4 = A): expediente, un commit de `core/budget/` y `api/` (recarga, informe y Excel) |
| INV‑083 | 1 (registro) y 11, paso 8 | parte de `ui/` en C3, sin tercer commit de `core/`; el informe del escenario y la API, a C4 (C3‑12) |
| INV‑081 | 10a, 10b y 10c | completo en tres capas, sin archivo nuevo en `ml/` |
| INV‑047, INV‑048 | — | siguen a limitaciones (GC0) |
| Tareas 7 a 12 de UI | 2 a 9 | enmendadas por la Tarea 1; CP‑07 va a Med (GU1b) |

**Grafo de dependencias:**

```
T0 → T1 (3 commits) ─┬─ A: T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 ───────────────────────────┐
                     │        └─(6 + fusión de B)→ T11.8 (INV‑083), T12 (ui, docs)             ┤
                     │        └─(7 + fusiones de B y C)→ T10c                                  ┤
                     ├─ B: T11 (exp → core → api) → T10a → T10b → T12 (exp → core) ───────────┤ fusión antes de T11.8, T12 (ui) y T10c
                     ├─ C: T13 ∥ T14 ─────────────────────────────────────────────────────────┤ fusión antes de T10c
                     └─ D: T15 → T16 ─────────────────────────────────────────────────────────┴→ T17 → T18
```

- T3 no depende de T2: podrían correr en paralelo, pero comparten worktree y los commits van en serie.
- T7 depende de T6 (`ui/elaboracion.py`) y de T3 (el desvío por `ui.caso`).
- T10b va después de T11, paso 5: el mismo archivo de la API.
- T12 (núcleo) va después de T11: los dos commits de `core/` tocan `core/budget/actualizacion.py` y `core/budget/__init__.py`, y la prueba de 7a usa el `actualizar_precios` que arrastra pendientes (D4 = A).
- T12 (ui) depende de T6 (la página ya lee `ruta_caso()`) y de la fusión de B (`descartar_version`).
- T11, paso 8 (INV‑083) depende de T6 (la página de escenarios migrada) y de la fusión de B (`cargar_elaboracion`).
- T10c depende de T7 (`propuestas_de_pendientes` y su prueba), de la fusión de B (`propuestas_para`) y de la de C (`tests/unit/test_composicion_ia.py`, que edita la Tarea 14; A‑4).
- T5 y T14 comparten la ayuda `tests/fixtures/subproceso.py`, que entra en la Tarea 1, paso 8, antes de abrir las pistas (A‑13).
- T17 solo comprueba y registra; va justo antes de T18.

**Lo que no se pudo planificar en concreto, y por qué:**

- **INV‑076.** El formato tabular del tercero (cómputo con regla y parámetros, APU y curva), la capa del analizador y la persistencia de partidas ajenas exigen diseño propio y, probablemente, otra enmienda de §5 y capacidad nueva por la ruta o la pantalla (Hecho 5). Por D2 se diseña fuera de C3 (superpowers:brainstorming); C3 solo lo registra.
- **El límite exacto de 11c.** Qué ayudas de `componer.py` que leen la sesión (`_rendimiento`, `_advertencias_precios`, `_contraste_aace`) quedan en la página. Lo fija el implementador bajo la prueba de arquitectura del paso 8. Si una ayuda obliga a importar `sqlalchemy.orm` en tiempo de ejecución, se registra y no se fuerza.
- **Si Streamlit 1.62 escribe «ScriptRunContext» en modo *bare*** (Tarea 5): el paso 2 lo comprueba y trae la alternativa.
- **Los recuentos exactos por tarea.** Se leen con `--junitxml`. Solo `N0 = 750` es esperado.
- **Borrar los worktrees de fases cerradas** (CLAUDE.md §3). Lo decide Eugenio: el plan solo los cuenta. Los tres sub‑worktrees de D3 sí se borran al fusionar.

---

## Trazabilidad de la revisión

Dictámenes sobre la versión sin commit de este plan: arquitectura (`.superpowers/sdd/c3/revision-plan-arq.md`, A‑1 a A‑13) y pruebas y calidad (`.superpowers/sdd/c3/revision-plan-qa.md`, QA‑1 a QA‑20). Todos se atendieron en esta edición; ninguno quedó como dictamen pendiente. Las re-revisiones (`.superpowers/sdd/c3/rerevision-plan-arq.md` y `rerevision-plan-qa.md`) aprobaron el plan con seis observaciones menores, también aplicadas: RA‑1 y RA‑2 (arquitectura) y RQ‑1 a RQ‑4 (pruebas y calidad).

| ID | Severidad | Dónde quedó atendido |
|---|---|---|
| A‑1 | importante | Hecho 11 reescrito, con la decisión leída del código. INV‑083 abierto en la Tarea 1, paso 7. Tarea 11: paso 7, grep `guardar_presupuesto\|cargar_elaboracion`; paso 8, INV‑083 en `ui/` con su rojo y su mutación y sin tercer commit de `core/`. Dictamen C3‑12 (resto a C4). Goal, tabla §2, Review Focus 4, Mapa y Autorrevisión |
| A‑2 | importante | Architecture, D5, Global Constraints (reglas de interfaz) y Tarea 6, bloque Interfaces y paso 10: `Guardado` y `guardar_composicion` en `ui/elaboracion.py`; `ui/composicion.py` solo gana `desglose`, puro, con el docstring actualizado |
| A‑3 | importante | Tarea 6, Interfaces (`prefijo`), y Tarea 7, Interfaces: `mostrar_elaboracion(..., *, prefijo, propuestas=()) -> tuple[ItemComputo, str] \| None`. Componer va sin selector; lo cubre `test_sin_propuestas_el_fragmento_no_ofrece_selector` |
| A‑4 | importante | Tarea 10, Interfaces: `proponedor` y `propuestas_para`, el único emparejamiento, un normalizador por llamada. `sugerir_partidas_similares -> Propuesta`. 10b y 10c usan `propuestas_para`. 10c va tras las fusiones de B y C. `test_composicion_ia.py` asignado a 10c en el Mapa. Doble de la Tarea 7 estable (`propuestas_de_pendientes`) |
| A‑5 | importante | Tarea 15, Files y cada hallazgo: `test_scripts_ruta_unica.py` y `test_scripts_resumen.py`, nuevos, de la pista D. Mapa y pista D |
| A‑6 | menor | Global Constraints: ninguna prueba nueva importa de otro `test_*.py` desde la Tarea 1. Tareas 11, paso 3, y 12, paso 2 (`_contar` del propio archivo; en `test_persistencia.py`, el existente: RQ‑1) |
| A‑7 | menor | Guion `guardia_gc3.sh` (`git diff-tree --cc` de cada fusión sobre `core/`). Protocolo de fusión, paso 2. Review Focus 1 y 9. Tarea 18, paso 3 |
| A‑8 | menor | Tarea 10a: `test_ml_solo_importa_core_contracts_del_nucleo` (`tests/unit/test_arquitectura.py:56`) |
| A‑9 | menor | Tarea 6, paso 8: `test_ui_respeta_sus_importaciones_prohibidas`, parametrizada con `PROHIBIDOS_EN_UI` (componer, composicion, elaboracion, resultado), reutilizando `_imports_de_ejecucion`. Mordidas en los pasos 8 y 9 |
| A‑10 | menor | Tarea 1, pasos 3 y 5, y Mapa: `:167`. Tarea 12, paso 9: `docs/modelo_datos.md:22` y `grep -niw` |
| A‑11 | menor | Tarea 12: `ForeignKey("presupuesto.id", ondelete="CASCADE")` en el mismo commit de `core/`, en el expediente C3.2, con la aserción en `test_persistencia.py` y la mordida 3. Review Focus 1 |
| A‑12 | menor | Tarea 15, INV‑050: `README.md:29-30` y `docs/manual_tecnico.md:225` y `:350`, commit `docs(scripts)`. Mapa y pista D |
| A‑13 | menor | Tarea 1, paso 8: `tests/fixtures/subproceso.py` (`importar_en_limpio`, `modulos_cargados`), antes de abrir las pistas. La usan la Tarea 5 (INV‑023) y la Tarea 14 (INV‑024, archivo propio `test_extras_perezosos.py`) |
| QA‑1 | bloqueante | Tarea 12, paso 2: `sesion.commit()` tras `sembrar(sesion)`, y la explicación en el Expected |
| QA‑2 | importante | Guion `guardia_gc3.sh`: `FUSION-TOCA-CORE` con `git diff-tree --cc`, contador de marcas y `exit 1`. Tarea 18, paso 3 |
| QA‑3 | importante | Protocolo de fusión, paso 2 (`--diff-filter=A` y guion). Guion: `guardia_nucleo.py` contra una fusión de prueba en `main`. Global Constraints y Review Focus 1 y 9 |
| QA‑4 | importante | Tarea 10b: reescritura de `test_api.py:365,406,441,517,547`. Tarea 10c: reescritura de `test_composicion_ia.py:54-99,330` y prueba en rojo de C3‑4 (`KeyError` se propaga). Review Focus 5 |
| QA‑5 | importante | Tarea 11, paso 4: recuento `N 2 0 0` con los dos fallos nombrados (o `--deselect`). Paso 5: `N 0 0 0` |
| QA‑6 | importante | Tarea 3: mordida de `argv_siembra`. Tarea 4: mordida en `ui/paginas/inicio.py` contra `test_con_partidas_no_se_ofrece_sembrar` |
| QA‑7 | importante | Tarea 7, Interfaces y paso 1: el doble se parcha en `ui.elaboracion.propuestas_de_pendientes`, donde la página lo resuelve, con `raising=False` |
| QA‑8 | importante | Tarea 6, pasos 9 y 10: una mordida por función nueva (`items_desde_filas`, `elaborar_desde_catalogo`, `libro_excel`, `desglose`, `guardar_composicion`). Tarea 7: mordidas de `aceptar_propuesta`, `propuestas_de_pendientes` y del fragmento |
| QA‑9 | importante | Global Constraints y Tarea 15, INV‑050: `monkeypatch.chdir(tmp_path)` y la aserción de la ruta antes de cualquier `main()` |
| QA‑10 | menor | Tarea 9: se conserva la aserción de INV‑065 y se declara el rojo de CP‑07 |
| QA‑11 | menor | Tarea 5: `assert len(modulos) == len(MODULOS_SIN_PAGINA) + 10` repuesto; la Tarea 6 no toca el `+ 10` |
| QA‑12 | menor | Tarea 14, INV‑024: `importlib.util.find_spec(extra) is not None` primero |
| QA‑13 | menor | Tarea 12, paso 9: `grep --include=*.py` |
| QA‑14 | menor | Tarea 15, INV‑051: criterio sin `__init__.py`, 22 de 24 faltan (25 archivos) |
| QA‑15 | menor | Tarea 15: archivos con nombre fijado e interfaz `resumen(resultado, moneda) -> str` para inyectar el total 2,125 |
| QA‑16 | menor | Tarea 11, paso 3: oráculo de los hallazgos persistidos (prueba 1) y comparativo solo sobre las valoradas (prueba 4). Paso 2: la prueba del Excel, en rojo y en el commit del paso 5. Review Focus 4 |
| QA‑17 | menor | Tarea 10b: rojo declarado de la reescritura `caplog` antes de cambiar la API |
| QA‑18 | menor | Tarea 7, paso 1: total igual a `formatear_decimal(TOTAL_EXACTO_LINEA_BASE, DECIMALES_PRESENTACION)` |
| QA‑19 | menor | Tarea 12, paso 6: el rojo es estructural (`TypeError`) y lo cubre la mordida del paso 8 |
| QA‑20 | menor | Tarea 18, paso 3: las líneas quitadas del `git diff -U0 …` sobre `test_persistencia.py` y `test_actualizacion_precios.py` son exactamente las dos de import que ruff (I001) amplió con `inspect` y `crear_esquema`, cada una con su línea nueva (revisión de B3, R‑2, y de A5, M‑2) |
| RA‑1 | menor | Tarea 7, Interfaces: `ui/resultado.py` importa `PendienteConPropuestas` bajo `if TYPE_CHECKING:` (re-revisión de arquitectura, R‑1) |
| RA‑2 | menor | Tarea 6, paso 8: `PROHIBIDOS_EN_UI["ui/composicion.py"]` suma `sqlalchemy`, `core.catalog` y `core.budget`; sigue en verde hoy (R‑2) |
| RQ‑1 | menor | Tarea 12, paso 2: la prueba nueva reusa `_contar` de `tests/integration/test_persistencia.py:35`, sin redefinirlo (re-revisión de pruebas, R‑1) |
| RQ‑2 | menor | Tarea 10b: el rojo corre con `HF_HUB_OFFLINE=1`; deben fallar `:365`, `:441` y `:517`, y `:406` y `:547` pasan ya con la API vieja (R‑2) |
| RQ‑3 | menor | Guion `guardia_gc3.sh`: `trap` en `EXIT` tras `mktemp -d` que quita el worktree temporal, o borra el directorio si aún no lo es, y hace `git worktree prune` (R‑3) |
| RQ‑4 | menor | Tarea 15, INV‑050: el centinela es una base SQLite sembrada, con la huella tomada tras sembrar (R‑4) |
