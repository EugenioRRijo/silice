# Cierre de la tesis, fase C2: adaptadores, ML y API

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Goal:** Cerrar los hallazgos de la fase C2 del inventario aprobado en GC0: los importantes INV‑016, INV‑017, INV‑018, INV‑072 (su parte de `api/`) e INV‑073 (su parte de `adapters/`), y el menor promovido INV‑042. `core/` no se toca en ningún momento. Si una corrección exige tocar `core/`, se detiene y se documenta en la bitácora, sin parche (CLAUDE.md §9). INV‑006 (subtarea de C2), INV‑038 (subtarea de C2) e INV‑041 no llevan código: conservan su estado. Con todo eso se cruza la compuerta **GC2**.

**Architecture:** C2 corrige las capas externas sin tocar el núcleo. `git diff --stat $(git merge-base main HEAD)..HEAD -- core/` queda vacío de principio a fin.

- **`tests/`.** Tres pruebas dejan de ser triviales o duplicadas:
  - INV‑016: RF‑23 se comprueba sobre el mismo objeto antes y después de auditar.
  - INV‑017: se afirma la fila exacta de la compuerta G2 y la limitación declarada.
  - INV‑018: una sola guardia de importaciones por adaptador en `test_arquitectura.py`.
- **INV‑042.** La fixture `cliente` y la carga útil de ítems pasan a `tests/integration/conftest.py`.
- **`api/`.** `POST /presupuestos` alcanza el flujo 3a de UC‑01 (INV‑072). Solo pide composiciones de las partidas que existen. El ítem sin partida queda pendiente, no suma al total y el informe lo declara. La respuesta 201 lo lista con las tres partidas más similares (UC‑03). No se crea ninguna ruta: el esquema de la respuesta gana un campo y `docs/api.json` se regenera.
- **Lo que exige `core/`.** El informe recargado pierde el hallazgo `PENDIENTE` y los ítems pendientes no se persisten. Eso solo se cierra en `core/budget/`, así que se registra como hallazgo nuevo con expediente y **no se parchea**.
- **`adapters/`.** Un módulo nuevo, `adapters/civil/recalculo.py`, realiza los flujos 1a, 2a y 2b de UC‑04 (INV‑073). Solo importa `core.contracts` y su propio paquete. Está sujeto a la decisión previa 1.
- **`ml/`.** Ningún hallazgo de C2 exige código en `ml/`: la única subtarea de esa capa (INV‑038) está en limitaciones.

**Tech Stack:** Python 3.13 · FastAPI (`TestClient`) · pytest (`-W error --strict-markers`) · ruff · uv · ifcopenshell (extra `civil`) · sentence-transformers (extra `ml`) · Markdown

**Spec:** [docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md](../specs/2026-09-23-plan-cierre-tesis-design.md). Las secciones que mandan este plan:

- §2: el límite (corrección frente a capacidad nueva).
- §4: criterios, severidad, regla de los hallazgos que cruzan capas y estado *aceptado por decisión de arquitectura registrada*.
- §5: fila C2 y compuerta GC2.
- §6: organización, ramas sin apilar y ratificación.

**Plan de fases:** [PLAN_CIERRE.md](../../../PLAN_CIERRE.md). **Inventario:** [docs/auditoria/2026-09-inventario.md](../../auditoria/2026-09-inventario.md). **Expedientes de C1:** [docs/bitacora/2026-09-23-C1-expedientes.md](../../bitacora/2026-09-23-C1-expedientes.md). **Bitácora:** `docs/bitacora/2026-09-23-cierre.md`.

**Rama y worktree:** `inc/cierre-C2` en `.claude/worktrees/cierre-C2`, creada desde `main` en `f1dda36` (merge del PR #11, C1 ya fusionada).

### Decisiones que Eugenio toma antes de ejecutar

Mandan sobre el resto del plan. La Tarea 0, paso 4, anota la respuesta. Sin respuesta, se ejecuta la opción recomendada **solo** en las Tareas 1 a 5, y la Tarea 6 espera.

1. **INV‑073: implementar o declarar los flujos 1a, 2a y 2b de UC‑04.** La corrección aprobada en GC0 admite las dos vías.
   - **Recomendada: (A) implementar** en `adapters/civil/recalculo.py` (Tarea 6). Los tres flujos están en la ERS (`docs/ERS.md:211-215`), así que es corrección y no capacidad nueva (spec §2). No toca `core/`. El hallazgo de R5 del flujo 2b lo emite el núcleo existente al auditar.
   - Costo de (A): unas 150 líneas en `adapters/` sin llamador en `ui/` ni en `api/`. UC‑04 no tiene pantalla ni ruta, y los pasos 1 a 4 ya se aceptaron en C1 como composición de biblioteca (`tests/unit/test_recalculo_uc04.py`). Es el mismo argumento de «sin llamador» con que C1 no implementó RF‑20 (dictamen C1‑7). Aquí pesa menos: no agrega un comparador al núcleo.
   - **(B) Declarar** los tres flujos «sin cumplir» en la ERS §3.2 y en plan_pruebas §8. Es documental: la hace C4. En C2 la Tarea 6 se reduce a anotar la decisión en la fila de INV‑073.
   - Una **ruta de API o una pantalla** para UC‑04 sería capacidad nueva (spec §2): no entra por ninguna de las dos vías.
2. **INV‑072 en la API: forma de la respuesta.**
   - **Recomendada:** `POST /presupuestos` responde 201 y agrega a `PresupuestoCreadoRespuesta` un campo `pendientes`. Cada ítem lleva sus propuestas (código, descripción, puntaje).
   - «Aceptar una propuesta» es volver a enviar el ítem con el código elegido. Así no hace falta ruta nueva.
   - Sin el extra `ml`, o sin el modelo en la caché local, las propuestas quedan vacías y el ítem sigue pendiente.
   - Un campo nuevo en la respuesta de una ruta existente, para realizar un flujo que ya está en la ERS, es corrección. Se registra de todos modos como punto «en duda» (spec §2) en el dictamen C2‑2.

---

## Global Constraints

- **`core/` no cambia** (spec §5, GC2; CLAUDE.md §1 y §9). `git diff --stat $(git merge-base main HEAD)..HEAD -- core/` debe estar vacío durante toda la fase.
  - Si una corrección parece exigir `core/`, **se detiene la tarea**: el hallazgo se escribe en la bitácora con expediente y como fila nueva del inventario, y no se parchea. La Tarea 5 lo hace con la recarga del informe.
  - Esto incluye cambios «temporales» de mutación: ninguno toca `core/`.
- **Los adaptadores solo importan `core.contracts`** (CLAUDE.md §2 y §5), su propio paquete y los terceros declarados. La guardia unificada de la Tarea 3 lo hace cumplir.
- **Ningún commit mezcla `core/` con `adapters/` o `ml/`.** Como `core/` no se toca, basta con que `scripts/guardia_nucleo.py --base main` salga con código 0.
- **INV‑006: la subtarea de C2 no se planifica.** La migración de los cuatro evaluadores de los adaptadores depende del aval del tutor, que no ha llegado. Queda *aceptada por decisión de arquitectura registrada* junto con el hallazgo padre (expediente A.3). Si el aval llega antes de `v1.0-tesis`, se reabre en una fase posterior.
- **`Decimal` en todo lo monetario y dimensional** (principio 3). La excepción declarada es el puntaje de similitud de UC‑03, que es adimensional y `float` de origen (`ml/normalization/normalizador.py:13-15`).
- **Línea base en 1 586,61 USD y auditoría en 7 de 7, intactas.** `tests/fixtures/apu_linea_base.py` no se edita.
- **Ninguna prueba escribe en `data/apu.db`.** La salvaguarda de sesión de C1 (`tests/conftest.py:53`) lo hace cumplir. Toda base de prueba vive en memoria o en `tmp_path`. Si la salvaguarda falla, se bisecta por archivo y se corrige la prueba. Nunca se relaja la salvaguarda ni se toca la base a mano.
- **Recuento de pruebas con `--junitxml`**, porque en este entorno pytest no imprime la línea de resumen. «El recuento» es:

```bash
uv run pytest -W error --strict-markers -q -p no:cacheprovider --junitxml=reporte-pruebas.xml; uv run python scripts/verificar_omitidas.py reporte-pruebas.xml; uv run python -c "import xml.etree.ElementTree as E; r=E.parse('reporte-pruebas.xml').getroot(); s=r if r.tag=='testsuite' else r.find('testsuite'); print(s.get('tests'), s.get('failures'), s.get('errors'), s.get('skipped'))"
```

  Imprime `N 0 0 0` y `verificar omitidas: 0 omitidas`. `reporte-pruebas.xml` está en `.gitignore`.
- **TDD con fase roja observada que ejerza comportamiento**, no solo un `ImportError`. Cuando la capacidad ya existe y la prueba solo se endurece, la fase roja es una **mutación temporal observada**: primero se ve que la aserción vieja la deja pasar, después que la nueva la muerde, y al final se restaura. Ninguna mutación toca `core/`.
- **Oráculos independientes.** El esperado sale de otra ruta de código o de aritmética escrita a mano y documentada. Nunca de la misma función que se prueba.
- **`docs/api.json` se regenera** con `uv run python scripts/exportar_openapi.py` cada vez que cambia un esquema de la API. La CI lo compara con `git diff --exit-code` (`.github/workflows/ci.yml`, paso «Artefactos reproducibles»).
- **La restricción global del plan de UI sobre `api/` no aplica a C2** (spec §5, enmienda).
- **Suite y lint.**
  - Suite verde con `uv run pytest -W error --strict-markers`, sin `filterwarnings` ni marcadores nuevos.
  - `uv run ruff check .` limpio, con línea de 100 caracteres.
  - CI verde en `ubuntu-latest` y `windows-latest`, sin pruebas omitidas.
- **Commits** en Conventional Commits, en español y sin tildes en el asunto. Terminan con `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- **Alcance congelado** (spec §2): solo correcciones que cierran un hallazgo y apuntan a un RF, RNF, contrato o documento existente. Toda duda se registra en la bitácora y la decide Eugenio en GC2.
- **Regla de reparto** (spec §2): por cada sesión de código, al menos una de redacción. Se anota en la bitácora (Tarea 0, paso 4, y Tarea 7, paso 6 (g)).
- **Convención de los textos.** Docstrings y comentarios siguen la del archivo que se edita.
  - **Con tildes:** `api/rutas/presupuestos.py`, los docstrings de clase de `api/esquemas.py`, `adapters/civil/*` salvo `ifc.py`, `tests/integration/conftest.py`, `tests/integration/test_auditoria_arenaza.py`, `tests/unit/test_recalculo_uc04.py` y los archivos nuevos de este plan.
  - **Sin tildes:** `adapters/civil/ifc.py`, `tests/integration/test_api.py`, `tests/unit/test_resultados_ml.py`, las pruebas de INV‑010 en `test_arquitectura.py`, los mensajes de error de los adaptadores y los cuerpos de commit.
- **Push y PR solo con permiso expreso de Eugenio.**

## Review Focus

1. **`POST /presupuestos` cambia de comportamiento (INV‑072).**
   - Un ítem con partida desconocida respondía 404, porque el `KeyError` de `Catalogo.partida` llegaba a `api/main.py:41-44`. Ahora responde 201, con el ítem en `pendientes` y un hallazgo `PENDIENTE` más en el conteo.
   - Ninguna prueba vigente dependía del 404 (se buscó en `tests/integration/test_api*.py`).
   - El esquema solo **agrega** un campo, así que ningún cliente se rompe. `docs/api.json` cambia solo en esquemas, no en rutas (`tests/unit/test_openapi.py` compara las rutas).
   - La recarga (`GET /presupuestos/{codigo}/informe`) **sigue sin declarar los pendientes**: es INV‑075 y exige `core/`. El revisor de requisitos debe confirmar que UC‑01 3a queda cubierto al elaborar y registrado como abierto al recargar.
2. **Las propuestas cargan el modelo de similitud en la ruta**, solo cuando hay pendientes.
   - Sin el extra `ml` o sin el modelo, la ruta degrada a propuestas vacías (`except (ImportError, OSError)`), con el mismo criterio que `api/rutas/rendimientos.py:156-162`.
   - La API ya dependía de `ml/` (`ml.anomaly`); la declaración de esa dependencia en la arquitectura es de C4 (INV‑059).
   - El revisor de arquitectura pondera la latencia y el `except`.
3. **Recálculo de UC‑04 (INV‑073, opción A).**
   - El relleno, que se deriva de totales, se recalcula sumando excavación y concreto y **escalando el volumen de tubería en proporción a la tubería**. Es válido porque el adaptador tabular admite un solo diámetro por balance (`adapters/civil/tabular.py:53-60`).
   - `diametro` se rechaza con `ValueError`: entra al cómputo solo por la fuente.
   - El flujo 2b rechaza también la cantidad **nula**, como dice la ERS.
   - El hallazgo de R5 no lo fabrica el adaptador: sale del núcleo al auditar, porque el relleno conservado deja de cuadrar con su directiva `_balance`.
   - El oráculo del flujo principal es `AdaptadorCivilTabular.extraer` sobre la fuente editada, otra ruta de código.
4. **La guardia unificada (INV‑018) cambia qué pruebas existen.**
   - Desaparecen cinco pruebas de los archivos de adaptador y los casos por archivo de `adapters/` de `test_fuera_del_nucleo_solo_se_importa_core_contracts`, que queda solo para `ml/`.
   - Aparecen una prueba por adaptador, la prueba de la regla y la de cobertura.
   - El recuento baja o sube según eso: se anota con `--junitxml`, sin inventarlo.
   - El revisor de pruebas verifica que la regla nueva es **al menos** tan estricta como la de telecom para los cuatro paquetes.
5. **Las mutaciones de INV‑016 e INV‑017 deben observarse en las dos direcciones:** la aserción vieja pasa con el defecto inyectado y la nueva falla con él.

---

## Mapa de archivos

| Archivo | Tarea | Responsabilidad |
|---|---|---|
| `PLAN_CIERRE.md`, este documento, `docs/bitacora/2026-09-23-cierre.md` | 0, 5, 7 | Enlace al plan; sección «Fase C2», expediente C2.1 y compuerta GC2 |
| `tests/integration/test_auditoria_arenaza.py` | 1 | INV‑016 |
| `tests/unit/test_resultados_ml.py`, `docs/auditoria/2026-09-inventario.md` | 2 | INV‑017; fila nueva INV‑074 (latente, `scripts/`) |
| `tests/unit/test_arquitectura.py`, `tests/unit/test_adapter_{civil_ifc,telecom,industrial,sistemas}.py`, `adapters/civil/ifc.py:16-19` (docstring) | 3 | INV‑018 |
| `tests/integration/conftest.py`, `tests/integration/test_api.py`, `test_api_escenarios.py`, `test_api_rendimientos.py` | 4 | INV‑042 |
| `api/esquemas.py`, `api/rutas/presupuestos.py`, `docs/api.json`, `tests/integration/test_api.py`; `docs/auditoria/2026-09-inventario.md`, `docs/bitacora/2026-09-23-cierre.md` | 5 | INV‑072 (api); fila nueva INV‑075 y expediente C2.1 (exige `core/`) |
| `adapters/civil/recalculo.py` (nuevo), `tests/unit/test_recalculo_civil.py` (nuevo), `tests/unit/test_adapter_civil_ifc.py` | 6 | INV‑073 (adaptadores), según la decisión previa 1 |
| `docs/auditoria/2026-09-inventario.md`, `docs/bitacora/2026-09-23-cierre.md` | 7 | Estados, incluidos INV‑006, INV‑038 e INV‑041 sin código; compuerta GC2 |

### Anclas verificadas contra `f1dda36`

Las anclas del inventario se escribieron sobre `cc2243c` y C1 movió algunas líneas de `tests/`. Estado actual:

| Hallazgo | Ancla del inventario | Estado en `f1dda36` |
|---|---|---|
| INV‑016 | `test_auditoria_arenaza.py:86,142` | vigente |
| INV‑017 | `test_resultados_ml.py:54-55,62`; contraste `test_resultados_ml_multidominio.py:76` | vigente |
| INV‑018 | `test_arquitectura.py:43-52`; `test_adapter_industrial.py:68-81`; `test_adapter_sistemas.py:91-109` | vigente |
| INV‑018 | `test_adapter_civil_ifc.py:61-73` | **desplazada:** hoy `:64-76` |
| INV‑018 | `test_adapter_telecom.py:145-179` | **incompleta:** hoy `:145-194` (incluye `test_la_validacion_de_imports_rechaza_otros_paquetes`, `:182-194`) |
| INV‑042 | `test_api.py:14-22`, `:55-72` | **desplazada:** hoy `:19-27` (`cliente`) y `:60-77` (`_items_payload`) |
| INV‑042 | `test_api_escenarios.py:29-37,43-57` | vigente |
| INV‑042 | `test_api_rendimientos.py:21-29` | **desplazada:** hoy `:26-33` |
| INV‑072 | `api/rutas/presupuestos.py:79-81`; `core/catalog/repositorio.py:73-78,128-134`; `ui/paginas/elaborar.py:225-226`; `ui/paginas/componer.py:798-800` | vigente |
| INV‑073 | `docs/ERS.md:211-215`; `adapters/civil/reglas.py:41-198`; `core/contracts/item_computo.py:52-53` | vigente |
| INV‑038 | `ml/prediction/reglas.py:186-193` | vigente |
| INV‑041 | `adapters/civil/tabular.py:30-43`, `industrial/adaptador.py:23-36`, `sistemas/adaptador.py:43-57`, `telecom/adaptador.py:25-38` | vigente |

La Tarea 7, paso 5, anota las anclas desplazadas en las filas correspondientes al cerrarlas.

### ¿Corrección o capacidad nueva? (spec §2)

| Hallazgo | Apunta a | Veredicto |
|---|---|---|
| INV‑016 | RF‑23 (existe) | corrección (solo `tests/`) |
| INV‑017 | RF‑28 y CLAUDE.md §8.1 (existen) | corrección (solo `tests/`) |
| INV‑018 | RF‑04, RF‑09 y CLAUDE.md §2 (existen) | corrección (solo `tests/` y un docstring) |
| INV‑042 | organización de pruebas | corrección (menor promovido) |
| INV‑072 (api) | UC‑01, flujo 3a (existe), en la ruta existente `POST /presupuestos` | corrección. El campo nuevo de la respuesta queda en duda y lo ratifica Eugenio (C2‑2). **No** se agrega ninguna ruta de UC‑03 a la API |
| INV‑073 (adapters) | UC‑04, flujos 1a, 2a y 2b (existen en `docs/ERS.md:211-215`) | corrección por la vía A. Una ruta o una pantalla de UC‑04 sería **capacidad nueva**: no se implementa y se registra como trabajo futuro si Eugenio la quisiera |
| INV‑006 (subtarea C2) | contrato nuevo `core.contracts.expresiones` | exige contrato y aval: **aceptado**, sin código |
| INV‑038 (subtarea C2) | contrato en `core.contracts` | a limitaciones, sin código |
| INV‑041 | autonomía declarada de los adaptadores | a limitaciones, sin código |

---

### Task 0: Punto de partida

**Files:**
- Ya en la rama: `docs/superpowers/plans/2026-09-23-cierre-c2-adaptadores-ml-api.md` (este documento, en el commit `docs(plan): plan detallado de la fase c2 del cierre`)
- Modify: `PLAN_CIERRE.md:12`, `docs/bitacora/2026-09-23-cierre.md` (sección nueva al final)

**Interfaces:**
- Consumes: `main` en `f1dda36` con C1 fusionada, más el commit del plan.
- Produces: el recuento de partida (`N0`), que citan las Tareas 1 a 7.

- [ ] **Step 1: Comprobar rama, base y estado de la base de trabajo**

Run: `git rev-parse --abbrev-ref HEAD && git merge-base --is-ancestor main HEAD && echo base-ok && git log --oneline -3 && git status --short && (ls data/*.db 2>/dev/null || echo "sin bases locales") && git worktree list`

Expected:
- `inc/cierre-C2`, luego `base-ok`.
- Los commits, del más reciente al más antiguo: `docs(plan): plan detallado de la fase c2 del cierre` y `f1dda36 merge: cierre fase c1 nucleo salvaguarda y guardia (#11)`.
- `git status --short` vacío.
- La lista de bases locales, o `sin bases locales`.
- La lista de worktrees. Al planificar había ocho vivos: principal, `cierre`, `cierre-C0`, `cierre-C1`, `cierre-C2`, `prototipo`, `tesis-cap4` y `ui`. CLAUDE.md §3 («Worktrees») dice que solo coexisten el principal y el del sprint vigente. Se anota en la bitácora (paso 4). **No se borra ninguno**: lo decide Eugenio.

- [ ] **Step 2: Estado de partida en verde**

Run: `uv sync --locked --all-extras`, después «el recuento» (Global Constraints) y `uv run ruff check .`.

Expected: `735 0 0 0`, `verificar omitidas: 0 omitidas` y `All checks passed!`. Anotar `N0` (según la bitácora, (h) de C1, es 735). Si no es 735, se detiene la tarea y se registra la diferencia antes de seguir.

- [ ] **Step 3: Enlazar el plan.** En `PLAN_CIERRE.md`, reemplazar la línea 12 (`- C2, C4, Med, U2/U3: se planifican al cruzar la compuerta anterior, con el inventario ya aprobado.`) por:

```markdown
- C2: [docs/superpowers/plans/2026-09-23-cierre-c2-adaptadores-ml-api.md](docs/superpowers/plans/2026-09-23-cierre-c2-adaptadores-ml-api.md)
- C4, Med, U2/U3: se planifican al cruzar la compuerta anterior, con el inventario ya aprobado.
```

- [ ] **Step 4: Abrir la sección de C2 en la bitácora.** Agregar al final de `docs/bitacora/2026-09-23-cierre.md`:

```markdown
## Fase C2 — adaptadores, ML y API

**Rama:** `inc/cierre-C2` (worktree `.claude/worktrees/cierre-C2`) · **Commit de partida:** `f1dda36`
(merge del PR #11) · **Plan ejecutable:**
[docs/superpowers/plans/2026-09-23-cierre-c2-adaptadores-ml-api.md](../superpowers/plans/2026-09-23-cierre-c2-adaptadores-ml-api.md).

**Estado de partida:** el recuento (`--junitxml`) da N0 pruebas, 0 fallos, 0 errores y 0 omitidas;
`ruff check .` limpio. `data/apu.db` al empezar: EXISTE_O_NO.

**Decisiones de Eugenio antes de ejecutar:** (1) INV‑073: DECISION_1; (2) INV‑072, forma de la
respuesta: DECISION_2.

**Observaciones de partida.**

- Regla de reparto (spec §2): la compensación ratificada en GC1 (redactar el capítulo IV antes de
  abrir C2) no consta. El worktree `tesis-cap4` está en `f1dda36`, sin commits propios.
- Hay WORKTREES worktrees vivos frente a los dos que admite CLAUDE.md §3. Borrarlos lo decide
  Eugenio.
```

Sustituir:
- `N0` por el número del paso 2.
- `EXISTE_O_NO` por «existe» o «no existe», según el paso 1.
- `DECISION_1` por «A, implementar en `adapters/civil/recalculo.py`» o «B, declarar sin cumplir (C4)».
- `DECISION_2` por la opción ratificada.
- `WORKTREES` por el número del paso 1.

Actualizar la observación del capítulo IV si ya tiene commits.

- [ ] **Step 5: Commit**

```bash
git add PLAN_CIERRE.md docs/bitacora/2026-09-23-cierre.md
git commit -m "docs(plan): enlaza el plan de c2 y abre su seccion en la bitacora" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 1: INV‑016, RF‑23 sobre el mismo presupuesto antes y después de auditar

**Files:**
- Modify: `tests/integration/test_auditoria_arenaza.py:77-86` (prueba parametrizada), `:126-142` (docstring y borrar `:142`)

**Interfaces:**
- Consumes: nada.
- Produces: ninguna interfaz. Solo cambia `tests/`.

**¿Existe la capacidad?** Sí: `auditar` no muta el presupuesto. Lo que falla es la prueba.
- `:86` compara el total de dos presupuestos reconstruidos por separado, así que no detectaría una mutación del objeto auditado.
- `:142` afirma sobre una lista que `:141` ya afirmó vacía.

- [ ] **Step 1: Observar la debilidad (la aserción vieja deja pasar la mutación).** En `test_la_auditoria_corre_sobre_el_presupuesto_telecom_completo`, sustituir **temporalmente** `    informe = auditar(presupuesto)` (`:81`) por:

```python
    informe = auditar(presupuesto)
    from datetime import date  # MUTACION TEMPORAL: simula un auditar que altera su entrada

    object.__setattr__(presupuesto, "fecha", date(2000, 1, 1))
```

Run: `uv run pytest tests/integration/test_auditoria_arenaza.py -q -W error --strict-markers -k completo -p no:cacheprovider`
Expected: `2 passed`. La aserción vieja no ve la mutación, porque el total no cambia. **No restaurar todavía.**

- [ ] **Step 2: Escribir la aserción que muerde (rojo).** Reemplazar las líneas `:79-86` de la prueba (dejando dentro la mutación del paso 1) por:

```python
    presupuesto = presupuesto_arenaza(sesion_telecom, numero)
    antes = repr(presupuesto)

    informe = auditar(presupuesto)
    from datetime import date  # MUTACION TEMPORAL: simula un auditar que altera su entrada

    object.__setattr__(presupuesto, "fecha", date(2000, 1, 1))

    assert isinstance(informe, InformeAuditoria)
    assert informe.codigo_presupuesto == presupuesto.codigo
    # El informe no altera el presupuesto auditado (RF‑23; INV‑016): el mismo objeto, campo por
    # campo, antes y después de auditar. `repr` recorre los contratos anidados, incluidos los
    # `MappingProxyType` de parámetros y especificaciones, que `copy.deepcopy` no puede copiar.
    assert repr(presupuesto) == antes
```

Run: el mismo comando del paso 1.
Expected: `2 failed`, con `AssertionError` en `assert repr(presupuesto) == antes` y la fecha `2000` en el diff.

- [ ] **Step 3: Quitar la mutación (verde).** Borrar las tres líneas marcadas `MUTACION TEMPORAL` y la línea en blanco que las sigue.

Run: el mismo comando.
Expected: `2 passed`.

- [ ] **Step 4: Borrar la aserción vacía (`:142`) y ajustar el docstring.** En `test_r5_no_reporta_error_sin_balance_declarado`:
  - Borrar `    assert all(h.severidad not in (Severidad.ERROR, Severidad.CRITICO) for h in hallazgos_r5)`.
  - En el docstring, la última oración (`Lo que importa para RF‑23 y se fija aquí es la garantía de fondo: nunca ERROR ni CRITICO por falta de datos.`) pasa a: `Lo que importa para RF‑23 es la garantía de fondo, nunca ERROR ni CRITICO por falta de datos, y la lista vacía ya la fija (INV‑016).`
  - Si `Severidad` queda sin uso, `ruff` lo marca. Sigue en uso en `:102`.

Run: `uv run pytest tests/integration/test_auditoria_arenaza.py -q -W error --strict-markers -p no:cacheprovider && uv run ruff check tests/integration/test_auditoria_arenaza.py`
Expected: verde y limpio.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_auditoria_arenaza.py
git commit -m "test(auditoria): rf-23 compara el mismo presupuesto antes y despues de auditar" -m "Cierra INV-016: la prueba comparaba dos reconstrucciones por separado y no veia una mutacion del objeto auditado (observado con una mutacion temporal de la fecha, que la asercion vieja dejaba pasar). Se borra la asercion sobre una lista ya afirmada vacia." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: INV‑017, la fila exacta de la compuerta G2 y la limitación declarada

**Files:**
- Modify: `tests/unit/test_resultados_ml.py:48-62`
- Modify: `docs/auditoria/2026-09-inventario.md` (fila nueva INV‑074)

**Interfaces:**
- Consumes: nada.
- Produces: ninguna interfaz. `scripts/` y `ml/` no cambian.

**¿Existe la capacidad?** Sí. `generar_informe` (`scripts/generar_resultados_ml.py:294-361`) escribe la fila `| civil | 5 | reglas |`. La prueba solo busca `"5"`, `"50"` y `"reglas"` sueltos.

- [ ] **Step 1: Observar la debilidad.** En `_informe()` (`:23`), cambiar **temporalmente** `"civil": 5` por `"civil": 51`. Con 51 registros la tabla de CLAUDE.md §8.1 dicta «casos», no «reglas».

Run: `uv run pytest tests/unit/test_resultados_ml.py -q -W error --strict-markers -p no:cacheprovider`
Expected: `2 passed`. `"5"` aparece dentro de `51`, `"50"` en el párrafo y `"reglas"` en las otras filas. **No restaurar todavía.**

- [ ] **Step 2: Endurecer las aserciones (rojo).** Reemplazar el cuerpo de `test_el_informe_declara_conteo_tecnica_y_metricas` (`:49-62`) por:

```python
    informe = _informe()

    # Compuerta G2 (INV-017): la fila exacta de cada dominio con su conteo y la tecnica que dicta
    # la tabla de CLAUDE.md §8.1 (menos de 50 registros: reglas). Oraculo escrito a mano desde esa
    # tabla, no con `tecnica_para`: una fila con otro conteo u otra tecnica no pasa.
    assert "| civil | 5 | reglas |" in informe
    for dominio in ("industrial", "sistemas", "telecom"):
        assert f"| {dominio} | 0 | reglas |" in informe

    # RF-28: las tres metricas obligatorias, presentes y con nombre.
    for metrica in ("MAPE", "RMSE", "R2"):
        assert metrica in informe

    # La tecnica de reglas se declara como limitacion, no como logro (CLAUDE.md §8.1): la frase
    # exacta, no la palabra suelta, que tambien aparece en otros parrafos del informe.
    assert "como **limitacion** del trabajo, no como logro" in informe
```

Run: el mismo comando.
Expected: `1 failed, 1 passed`. Falla `assert "| civil | 5 | reglas |" in informe`.

- [ ] **Step 3: La limitación también muerde.** Restaurar `"civil": 5`. En `scripts/generar_resultados_ml.py:324`, cambiar **temporalmente** `"como **limitacion** del trabajo, no como logro: ...` por `"como **logro** del trabajo, no como limitacion: ...`.

Run: el mismo comando.
Expected: `1 failed`, en la aserción de la limitación. La aserción vieja (`"limitacion" in informe.lower()`) habría pasado por las otras menciones (`:327`). **Restaurar `scripts/generar_resultados_ml.py`.**

Run: `uv run pytest tests/unit/test_resultados_ml.py tests/unit/test_resultados_ml_multidominio.py -q -W error --strict-markers -p no:cacheprovider && git status --short`
Expected: verde, y `git status` solo muestra `M tests/unit/test_resultados_ml.py`.

- [ ] **Step 4: Commit de la prueba**

```bash
git add tests/unit/test_resultados_ml.py
git commit -m "test(ml): el informe g2 afirma la fila exacta y la limitacion declarada" -m "Cierra INV-017: '5' y '50' sueltos pasaban con 51 registros (tecnica casos); ahora se afirma la fila | civil | 5 | reglas | y la frase de la limitacion, con oraculo escrito desde CLAUDE.md 8.1. Mutaciones observadas y restauradas." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 5: Registrar el hallazgo latente visto al planificar.**
  - El párrafo de la compuerta G2 (`scripts/generar_resultados_ml.py:322-328`) afirma «Todos los dominios estan por debajo de los 50 registros» **sin consultar `conteos`**. Con un dominio sobre el umbral, la tabla diría «casos» y el párrafo seguiría diciendo lo contrario.
  - Hoy es cierto: el conteo mayor es 40 (`docs/resultados_ml.md:13`).
  - Es de `scripts/` (C3) y menor: se registra sin corregir.

  Agregar al final de §3 del inventario (siguiente ID libre; al planificar, INV‑074):

```markdown
| INV-074 | planificación de C2 (Tarea 2) | scripts (cruza: docs) | Coherencia documental (resultados de ML) | menor | `scripts/generar_resultados_ml.py:318-328`; `docs/resultados_ml.md:15` | `generar_informe` escribe «Todos los dominios estan por debajo de los {UMBRAL_CASOS} registros» y declara la técnica de reglas como limitación sin consultar `conteos`: con un dominio sobre el umbral la tabla diría «casos» y el párrafo seguiría afirmando lo contrario. Latente: hoy el conteo mayor es 40 | Derivar el párrafo de `max(conteos.values())` (o exigir la condición antes de escribirlo) | C3 si Eugenio lo promueve en GC2; si no, a limitaciones | abierto |
```

```bash
git add docs/auditoria/2026-09-inventario.md
git commit -m "docs(auditoria): parrafo g2 de resultados_ml sin derivar de los conteos" -m "Hallazgo menor y latente registrado al planificar INV-017; su destino lo decide Eugenio en GC2." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: INV‑018, una sola guardia de importaciones por adaptador

**Files:**
- Modify: `tests/unit/test_arquitectura.py` (docstring `:1-8`; `:43-52`; pruebas nuevas al final)
- Modify: `tests/unit/test_adapter_civil_ifc.py:64-76` (borrar), `tests/unit/test_adapter_telecom.py:12-13,25,145-194` (borrar), `tests/unit/test_adapter_industrial.py:8,20,68-81` (borrar), `tests/unit/test_adapter_sistemas.py:12,24-28,91-109` (borrar)
- Modify: `adapters/civil/ifc.py:16-19` (docstring que cita la prueba borrada)

**Interfaces:**
- Consumes: `RAIZ`, `_archivos`, `_ruta` e `_imports` de `test_arquitectura.py`.
- Produces:
  - `TERCEROS_POR_ADAPTADOR: dict[str, frozenset[str]]` y `_import_permitido(adaptador, modulo)` en `tests/unit/test_arquitectura.py`.
  - La Tarea 6 da por hecho que `adapters/civil/recalculo.py` queda bajo esta regla.

- [ ] **Step 1: Escribir la regla unificada con civil sin terceros (rojo de comportamiento).** En `tests/unit/test_arquitectura.py`, después de `PAQUETES_FUERA_DEL_NUCLEO` (`:17`), agregar:

```python
#: Terceros que cada adaptador puede importar, ademas de la biblioteca estandar, `core.contracts` y
#: su propio paquete (INV-018: una sola guardia con la regla que antes solo regia para telecom).
#: Un adaptador nuevo necesita su fila: lo exige `test_toda_carpeta_de_adapters_tiene_su_regla`.
TERCEROS_POR_ADAPTADOR: dict[str, frozenset[str]] = {
    "civil": frozenset(),
    "industrial": frozenset(),
    "sistemas": frozenset(),
    "telecom": frozenset(),
}
_BIBLIOTECA_ESTANDAR = frozenset(sys.stdlib_module_names) | {"__future__"}
```

Y al final del archivo:

```python
def _import_permitido(adaptador: str, modulo: str) -> bool:
    """True si un archivo de `adapters/<adaptador>/` puede importar `modulo`.

    Compara el paquete completo y no solo la raiz: `adapters.civil.evaluador` tiene la misma raiz
    `adapters` que el propio paquete de telecom y no por eso le esta permitido (hallazgo Important 1
    de la ronda 1 de revision de I5, que antes solo vigilaba la copia de telecom).
    """
    raiz = modulo.split(".")[0]
    if raiz == "core":
        return modulo == "core.contracts" or modulo.startswith("core.contracts.")
    if raiz == "adapters":
        propio = f"adapters.{adaptador}"
        return modulo == propio or modulo.startswith(propio + ".")
    return raiz in _BIBLIOTECA_ESTANDAR or raiz in TERCEROS_POR_ADAPTADOR[adaptador]


@pytest.mark.parametrize("adaptador", sorted(TERCEROS_POR_ADAPTADOR))
def test_un_adaptador_solo_importa_contratos_su_paquete_y_sus_terceros(adaptador):
    """INV-018: CLAUDE.md §2 y §5 para cada adaptador, con importaciones anidadas incluidas."""
    prohibidos = [
        f"{_ruta(archivo)}: {modulo}"
        for archivo in _archivos(f"adapters/{adaptador}")
        for modulo in _imports(archivo)
        if not _import_permitido(adaptador, modulo)
    ]
    assert not prohibidos, (
        f"adapters/{adaptador} importa {prohibidos}; solo se permite la biblioteca estandar, "
        "core.contracts, su propio paquete y los terceros de TERCEROS_POR_ADAPTADOR"
    )


def test_la_regla_de_un_adaptador_rechaza_otro_adaptador_y_el_resto_del_nucleo():
    assert not _import_permitido("telecom", "adapters.civil.evaluador")
    assert not _import_permitido("telecom", "adapters.civil")
    assert not _import_permitido("telecom", "adapters.telecomunicaciones")  # prefijo, no paquete
    assert not _import_permitido("telecom", "core.costing")
    assert not _import_permitido("telecom", "core")
    assert not _import_permitido("telecom", "ifcopenshell")  # el tercero de civil no es de telecom
    assert _import_permitido("telecom", "core.contracts.item_computo")
    assert _import_permitido("telecom", "adapters.telecom.adaptador")
    assert _import_permitido("telecom", "decimal")
    assert _import_permitido("telecom", "__future__")


def test_toda_carpeta_de_adapters_tiene_su_regla():
    """Un adaptador nuevo no puede quedar fuera de la guardia; el `__init__` raiz no importa nada."""
    paquetes = {inicio.parent.name for inicio in (RAIZ / "adapters").glob("*/__init__.py")}
    assert paquetes == set(TERCEROS_POR_ADAPTADOR)
    assert not list(_imports(RAIZ / "adapters" / "__init__.py"))
```

Run: `uv run pytest tests/unit/test_arquitectura.py -q -W error --strict-markers -p no:cacheprovider`
Expected: `1 failed`: `test_un_adaptador_solo_importa_contratos_su_paquete_y_sus_terceros[civil]`, que lista `adapters/civil/ifc.py: ifcopenshell` y `adapters/civil/ifc.py: ifcopenshell.util.element`. Es un rojo sobre el código real: la regla muerde en cuanto un tercero no está declarado.

- [ ] **Step 2: Declarar el tercero de civil (verde).** `"civil": frozenset(),` pasa a `"civil": frozenset({"ifcopenshell"}),`.

Run: el mismo comando.
Expected: verde.

- [ ] **Step 3: La regla nueva ve lo que las copias viejas no veían.** Agregar **temporalmente**, como primera línea después de `from __future__ import annotations` en `adapters/industrial/adaptador.py`, `import adapters.civil.evaluador  # noqa: F401  MUTACION TEMPORAL`.

Run: `uv run pytest tests/unit/test_adapter_industrial.py tests/unit/test_arquitectura.py -q -W error --strict-markers -p no:cacheprovider -k "importa"`
Expected:
- `test_adapter_industrial.py::test_no_importa_nada_de_core_salvo_contracts` **pasa**: la copia vieja solo vigilaba `core`.
- `test_un_adaptador_solo_importa_contratos_su_paquete_y_sus_terceros[industrial]` **falla**.

**Restaurar `adapters/industrial/adaptador.py`** y comprobar con `git status --short` que no aparece.

- [ ] **Step 4: Borrar las cuatro copias y reducir la vieja a `ml/`.**
  - `tests/unit/test_adapter_civil_ifc.py`: borrar `test_solo_importa_core_contracts` (`:64-76`).
  - `tests/unit/test_adapter_telecom.py`: borrar `_imports_de`, `_import_permitido`, `test_no_importa_nada_de_core_salvo_contracts` y `test_la_validacion_de_imports_rechaza_otros_paquetes` (`:145-194`), la constante `PAQUETE_TELECOM` (`:25`) y los `import ast` e `import sys` (`:12-13`).
  - `tests/unit/test_adapter_industrial.py`: borrar `test_no_importa_nada_de_core_salvo_contracts` (`:68-81`), `RUTA_PAQUETE` (`:20`) e `import ast` (`:8`).
  - `tests/unit/test_adapter_sistemas.py`: borrar `test_no_importa_nada_de_core_salvo_contracts` (`:91-109`), `ARCHIVOS_ADAPTADOR` (`:24-28`) e `import ast` (`:12`).
  - `tests/unit/test_arquitectura.py`:
    - La parametrización de `:43-45` pasa a `@pytest.mark.parametrize("archivo", _archivos("ml"), ids=_ruta)`. La regla por adaptador ya cubre `adapters/`, así que dejar ambas sería la duplicación que el hallazgo denuncia.
    - En el docstring, la línea 3 pasa a: `- adapters/ importa solo la biblioteca estándar, core.contracts, su propio paquete y los terceros declarados; ml/ importa de core solo core.contracts;`.
  - `adapters/civil/ifc.py:16-19`: el docstring pasa a:

```python
Regla del nucleo cerrado (CLAUDE.md §5): solo se importa `core.contracts`; ifcopenshell (tercero
declarado para civil) y la biblioteca estandar estan libres. `tests/unit/test_arquitectura.py`
(`TERCEROS_POR_ADAPTADOR`) lo vigila con un analisis AST del paquete.
```

Run:
- `uv run ruff check tests adapters && grep -rn "test_solo_importa_core_contracts\|test_no_importa_nada_de_core_salvo_contracts\|_import_permitido" --include=*.py --include=*.md . | grep -v "docs/bitacora\|docs/superpowers"`
- después, «el recuento».

Expected:
- ruff limpio.
- El `grep` solo muestra `tests/unit/test_arquitectura.py`, con `_import_permitido`.
- Suite verde, 0 omitidas. Anotar el recuento (`N3`); cambia respecto de `N0` porque la regla por archivo de `adapters/` se reemplaza por la regla por paquete.
- `scripts/meta_alpha.py:109-111` sigue encontrando los tres archivos de adaptador, que no se borran.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_arquitectura.py tests/unit/test_adapter_civil_ifc.py tests/unit/test_adapter_telecom.py tests/unit/test_adapter_industrial.py tests/unit/test_adapter_sistemas.py adapters/civil/ifc.py
git commit -m "test(arquitectura): una sola guardia de importaciones por adaptador" -m "Cierra INV-018: la regla de telecom (biblioteca estandar, core.contracts, su propio paquete y ningun otro adaptador) rige ahora para los cuatro, con los terceros declarados por adaptador (civil: ifcopenshell). Rojo observado con civil sin terceros; una importacion cruzada temporal paso la copia vieja de industrial y fallo la nueva. Se borran las cuatro copias; la regla generica queda para ml." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: INV‑042, una sola fixture de cliente y de ítems para la API

**Files:**
- Modify: `tests/integration/conftest.py` (dos fixtures nuevas al final)
- Modify: `tests/integration/test_api.py:9,19-27,60-77` y cada uso de `_items_payload()` (`:102`, `:123`, `:156`, `:184`, `:212`, `:231`, `:278`)
- Modify: `tests/integration/test_api_escenarios.py:18,29-37,40-57`
- Modify: `tests/integration/test_api_rendimientos.py:26-33`

**Interfaces:**
- Consumes: `sesion` de `tests/integration/conftest.py`; `tests.fixtures.computo_auditado.items_auditados`.
- Produces: las fixtures `cliente` e `items_payload` (una lista nueva por prueba), que usa la Tarea 5.

**Refactorización sin cambio de comportamiento:** no hay fase roja. La evidencia es que el recuento y los resultados son idénticos antes y después, y que queda una sola definición de cada cosa.

- [ ] **Step 1: Agregar las fixtures.** Al final de `tests/integration/conftest.py`:

```python
@pytest.fixture
def cliente(sesion):
    """Cliente HTTP de la API sobre la sesión en memoria (INV‑042: una sola copia).

    Importa FastAPI dentro de la fixture: el extra `api` solo hace falta en las pruebas que la
    piden, no en todo el paquete de integración.
    """
    from fastapi.testclient import TestClient

    from api.dependencias import sesion_api
    from api.main import app

    app.dependency_overrides[sesion_api] = lambda: sesion
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def items_payload():
    """Los ítems del presupuesto auditado como cuerpo JSON de `POST /presupuestos`, con los montos
    como texto. Una lista nueva por prueba: quien la altera no contamina a las demás."""
    from tests.fixtures.computo_auditado import items_auditados

    return [
        {
            "codigo_partida": item.codigo_partida,
            "descripcion": item.descripcion,
            "unidad": item.unidad,
            "cantidad": str(item.cantidad),
            "origen_id": item.origen_id,
            "origen_tipo": item.origen_tipo.value,
            "dominio": item.dominio.value,
            "regla": item.regla,
            "parametros": {clave: str(valor) for clave, valor in item.parametros.items()},
            "especificaciones": dict(item.especificaciones),
        }
        for item in items_auditados()
    ]
```

- [ ] **Step 2: Borrar las copias.**
  - `test_api.py`:
    - Borrar la fixture `cliente` (`:19-27`) y `_items_payload` (`:60-77`).
    - Cada prueba que llamaba `_items_payload()` recibe `items_payload` como parámetro y lo usa en su lugar.
    - `test_cantidad_decimal_malformada_responde_422_no_500` pasa de `items = _items_payload()` a `items = items_payload`.
    - Borrar `from fastapi.testclient import TestClient` (`:9`) si queda sin uso.
  - `test_api_escenarios.py`:
    - Borrar la fixture `cliente` (`:29-37`).
    - `presupuesto_001(cliente)` pasa a `presupuesto_001(cliente, items_payload)` y usa `items_payload` en lugar de la lista armada en `:43-57`.
    - Borrar el import de `TestClient` si queda sin uso. `items_auditados` sigue en uso en `:97`.
  - `test_api_rendimientos.py`:
    - Borrar la fixture `cliente` (`:26-33`).
    - Conservar `from fastapi.testclient import TestClient`, que anota `_registrar`.
    - La línea 8 del docstring pasa a: `El fixture \`cliente\` vive en \`tests/integration/conftest.py\` (INV-042): la base en memoria sembrada`.

Run: `uv run ruff check tests/integration && grep -rn "def cliente\|def _items_payload\|def items_payload" tests`, después «el recuento».

Expected:
- ruff limpio.
- `grep` muestra solo `tests/integration/conftest.py` (dos líneas).
- El recuento da **`N3 0 0 0`**, el mismo número de la Tarea 3.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/conftest.py tests/integration/test_api.py tests/integration/test_api_escenarios.py tests/integration/test_api_rendimientos.py
git commit -m "test(api): una sola fixture de cliente y de items para las pruebas de la api" -m "Cierra INV-042 (menor promovido): la fixture cliente estaba copiada tres veces y la carga util de items dos. Refactorizacion sin cambio de comportamiento: mismo recuento antes y despues." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: INV‑072 (api), UC‑01 3a por HTTP; la recarga del informe queda registrada porque exige `core/`

**Files:**
- Modify: `api/esquemas.py:131-136` (`PresupuestoCreadoRespuesta`) y dos esquemas nuevos antes
- Modify: `api/rutas/presupuestos.py:1-7` (docstring), `:9-56` (imports), `:67-107` (`crear_presupuesto`), ayudantes nuevos después de `_a_item_computo` (`:282-297`)
- Modify: `docs/api.json` (regenerado)
- Test: `tests/integration/test_api.py` (tres pruebas nuevas)
- Modify: `docs/auditoria/2026-09-inventario.md` (fila nueva INV‑075), `docs/bitacora/2026-09-23-cierre.md` (expediente C2.1)

**Interfaces:**
- Consumes: `core.budget.elaborar` y `ResultadoElaboracion.pendientes` (`core/budget/presupuesto.py:91-124`, sin cambios); `Catalogo.partidas` (`core/catalog/repositorio.py:66-71`); `ml.normalization.NormalizadorPartidas` (`ml/normalization/normalizador.py:67-119`); las fixtures `cliente` e `items_payload` (Tarea 4).
- Produces: `PresupuestoCreadoRespuesta.pendientes: list[ItemPendienteRespuesta]`, `ItemPendienteRespuesta` y `PropuestaPartidaRespuesta` en `api/esquemas.py`.

**¿Existe la capacidad?** En el núcleo, sí: `elaborar` deja pendiente el ítem cuya partida no tiene composición (INV‑013, C1). En la API, no. `crear_presupuesto` pide composiciones de **todos** los códigos (`:79-81`), `Catalogo.partida` lanza `KeyError` (`repositorio.py:73-78`) y `api/main.py:41-44` lo convierte en 404.

**Lo que esta tarea no cierra, porque exige `core/`.** La recarga pierde los pendientes:
- `_cargar` (`api/rutas/presupuestos.py:378-385`) reaudita con `auditar`, que no conoce los pendientes: los agrega `elaborar` (`core/budget/presupuesto.py:123,127`).
- `guardar_presupuesto` persiste el hallazgo `PENDIENTE` (`core/budget/persistencia.py:101-112`), pero no el ítem pendiente (`:85-89` solo recorre `presupuesto.partidas`).

Reconstruir el informe con los hallazgos guardados, o persistir los pendientes, es trabajo de la frontera de persistencia del presupuesto: el docstring de `core/budget/persistencia.py:11-13` la declara única. Hacerlo desde `api/` duplicaría `_declarar_pendientes`. **Se detiene aquí y se documenta** (paso 6), según CLAUDE.md §9.

- [ ] **Step 1: Pruebas que fallan.** En `tests/integration/test_api.py`, agregar `import sys` y `from types import SimpleNamespace` a los imports y `from sqlalchemy import select` si no está. Después, al final:

```python
CODIGO_SIN_PARTIDA = "XX-99-NUE"


def _item_sin_partida(descripcion):
    """Un item cuya partida no existe en el catalogo (UC-01, flujo 3a)."""
    return {
        "codigo_partida": CODIGO_SIN_PARTIDA,
        "descripcion": descripcion,
        "unidad": "m3",
        "cantidad": "2.5",
        "origen_id": "PEND-01",
        "origen_tipo": "manual",
        "dominio": "civil",
    }


def _cuerpo(codigo, items):
    return {
        "codigo": codigo,
        "fecha": "2026-04-28",
        "moneda": "USD",
        "proyecto": "Drenaje de la clínica",
        "items": items,
    }


def test_un_item_sin_partida_queda_pendiente_por_http(cliente, sesion, items_payload, monkeypatch):
    """UC-01, flujo 3a, por HTTP (INV-072): el item sin partida no aborta la elaboracion. Queda
    pendiente, no suma al total, el informe lo declara (y se persiste) y la respuesta lo lista con
    las partidas similares que propone UC-03. El normalizador es un doble: esta prueba verifica el
    cableado, no la similitud (esa la cubre la prueba con el modelo real, mas abajo).
    """
    from core import models

    recibidas = {}
    propuesta = SimpleNamespace(codigo="LB-01-EXC", descripcion="Excavacion", puntaje=0.91)

    class _NormalizadorDoble:
        def __init__(self, partidas):
            recibidas.update(partidas)

        def similares(self, descripcion):
            return [propuesta]

    monkeypatch.setitem(
        sys.modules, "ml.normalization", SimpleNamespace(NormalizadorPartidas=_NormalizadorDoble)
    )

    base = cliente.post("/presupuestos", json=_cuerpo("API-BASE", items_payload))
    r = cliente.post(
        "/presupuestos",
        json=_cuerpo("API-3A", [*items_payload, _item_sin_partida("Excavacion de un foso nuevo")]),
    )

    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)  # no suma al total
    assert cuerpo["hallazgos"] == base.json()["hallazgos"] + 1  # el informe lo declara
    assert base.json()["pendientes"] == []
    (pendiente,) = cuerpo["pendientes"]
    assert pendiente["codigo_partida"] == CODIGO_SIN_PARTIDA
    assert pendiente["origen_id"] == "PEND-01" and pendiente["cantidad"] == "2.5"
    assert pendiente["propuestas"] == [
        {"codigo": "LB-01-EXC", "descripcion": "Excavacion", "puntaje": 0.91}
    ]
    assert set(linea_base.CODIGOS_LINEA_BASE) <= set(recibidas)  # propone sobre el catalogo
    # Postcondicion de UC-01: el informe persistido lleva la declaracion del pendiente.
    guardado = sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == "API-3A")
    ).one()
    assert [h.regla for h in guardado.hallazgos if h.regla == "PENDIENTE"] == ["PENDIENTE"]


def test_sin_el_extra_ml_el_pendiente_queda_sin_propuestas(cliente, items_payload, monkeypatch):
    """La propuesta es una ayuda, no una condicion: sin `ml` el item sigue pendiente."""
    monkeypatch.setitem(sys.modules, "ml.normalization", None)  # import -> ImportError

    r = cliente.post(
        "/presupuestos",
        json=_cuerpo("API-3A-SIN-ML", [*items_payload, _item_sin_partida("Foso nuevo")]),
    )

    assert r.status_code == 201
    assert r.json()["pendientes"][0]["propuestas"] == []


def test_la_propuesta_real_reconoce_la_partida_de_la_misma_descripcion(
    cliente, items_payload, monkeypatch
):
    """Con el modelo de similitud real (RF-15): una descripcion identica a la de una partida del
    catalogo la pone primera. Oraculo independiente del modelo: textos iguales, coseno 1."""
    pytest.importorskip("sentence_transformers")
    monkeypatch.setenv("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from ml.normalization import NormalizadorPartidas

    try:
        NormalizadorPartidas({})
    except OSError as error:  # mismo criterio que tests/unit/test_normalizacion.py
        pytest.skip(f"el modelo de similitud no esta disponible localmente: {error}")

    codigo = linea_base.APU_EXCAVACION.codigo_partida
    excavacion = next(p for p in cliente.get("/partidas").json() if p["codigo"] == codigo)

    r = cliente.post(
        "/presupuestos",
        json=_cuerpo("API-3A-REAL", [*items_payload, _item_sin_partida(excavacion["descripcion"])]),
    )

    propuestas = r.json()["pendientes"][0]["propuestas"]
    assert 1 <= len(propuestas) <= 3
    assert propuestas[0]["codigo"] == codigo
    puntajes = [p["puntaje"] for p in propuestas]
    assert puntajes == sorted(puntajes, reverse=True)
```

Partir en varias líneas lo que supere los 100 caracteres.

Run: `uv run pytest tests/integration/test_api.py -q -W error --strict-markers -p no:cacheprovider -k "pendiente or propuesta"`
Expected: `3 failed`, las tres con `assert 404 == 201` (o `KeyError: 'pendientes'` en la del modelo real). Es el comportamiento que denuncia INV‑072: la partida desconocida aborta la elaboración con 404.

- [ ] **Step 2: Esquemas.** En `api/esquemas.py`, antes de `class PresupuestoCreadoRespuesta` (`:131`), agregar:

```python
class PropuestaPartidaRespuesta(BaseModel):
    """Una partida del catálogo parecida a la de un ítem pendiente (UC‑03, RF‑15).

    El puntaje es una similitud adimensional del coseno, no un monto: viaja como número
    (`ml/normalization/normalizador.py`, la excepción declarada a la regla `Decimal`).
    """

    codigo: str
    descripcion: str
    puntaje: float


class ItemPendienteRespuesta(BaseModel):
    """Un ítem sin partida en el catálogo (UC‑01, flujo 3a): no suma al total y el informe lo
    declara. Para aceptar una propuesta se vuelve a enviar el ítem con ese código. `propuestas`
    queda vacía sin el extra `ml` o sin el modelo de similitud en la caché local."""

    codigo_partida: str
    descripcion: str
    unidad: str
    cantidad: str
    origen_id: str
    propuestas: list[PropuestaPartidaRespuesta]
```

`PresupuestoCreadoRespuesta` pasa a:

```python
class PresupuestoCreadoRespuesta(BaseModel):
    """Lo que confirma la elaboración: el total (dos decimales), cuántos hallazgos audita y los
    ítems que quedaron pendientes por no tener partida en el catálogo (UC‑01, flujo 3a)."""

    codigo: str
    total: str
    hallazgos: int
    pendientes: list[ItemPendienteRespuesta] = Field(default_factory=list)
```

(`Field` ya se importa en el archivo, porque lo usa `EscenarioPeticion`.)

- [ ] **Step 3: La ruta.** En `api/rutas/presupuestos.py`:
  - Imports: agregar `from collections.abc import Callable, Sequence`, y `ItemPendienteRespuesta` y `PropuestaPartidaRespuesta` al import de `api.esquemas`.
  - El docstring del módulo (`:3-4`) pasa a: `UC-01 (\`POST /presupuestos\`, a partir de \`ItemComputo\` ya extraídos; un ítem sin partida queda pendiente y se lista con sus partidas similares, flujo 3a), UC-05 (el informe de`. El resto del docstring no cambia.
  - En `crear_presupuesto`, el docstring pasa a `"""Elabora el presupuesto (UC-01), lo audita siempre (UC-05) y lo guarda; los ítems sin partida quedan pendientes (flujo 3a)."""`, partido en dos líneas si supera los 100 caracteres.
  - Las líneas `:78-81` pasan a:

```python
    catalogo = Catalogo(sesion)
    # UC-01, flujo 3a (INV-072): solo se piden composiciones de las partidas que existen; las
    # demás las deja pendientes `elaborar`, en vez de abortar con el KeyError del catálogo (404).
    catalogadas = {partida.codigo for partida in catalogo.partidas()}
    composiciones = catalogo.composiciones(
        dict.fromkeys(item.codigo_partida for item in items if item.codigo_partida in catalogadas),
        fecha=peticion.fecha,
    )
```

  - El `return` (`:103-107`) pasa a:

```python
    return PresupuestoCreadoRespuesta(
        codigo=resultado.presupuesto.codigo,
        total=formatear_decimal(resultado.presupuesto.total, DECIMALES_PRESENTACION),
        hallazgos=len(resultado.informe.hallazgos),
        pendientes=_pendientes(catalogo, resultado.pendientes),
    )
```

  - Después de `_a_item_computo` (`:282-297`):

```python
def _pendientes(
    catalogo: Catalogo, pendientes: Sequence[ItemComputo]
) -> list[ItemPendienteRespuesta]:
    """UC-01, flujo 3a: cada ítem sin partida con las partidas más similares del catálogo (UC-03).

    La cantidad viaja exacta (como en `ItemComputoRespuesta`), no redondeada: quien acepta una
    propuesta vuelve a enviar este mismo ítem con el código elegido.
    """
    if not pendientes:
        return []
    proponer = _proponedor(catalogo)
    return [
        ItemPendienteRespuesta(
            codigo_partida=item.codigo_partida,
            descripcion=item.descripcion,
            unidad=item.unidad,
            cantidad=str(item.cantidad),
            origen_id=item.origen_id,
            propuestas=[
                PropuestaPartidaRespuesta(
                    codigo=similar.codigo, descripcion=similar.descripcion, puntaje=similar.puntaje
                )
                for similar in proponer(item.descripcion)
            ],
        )
        for item in pendientes
    ]


def _proponedor(catalogo: Catalogo) -> Callable[[str], Sequence]:
    """`similares` del normalizador de UC-03 sobre el catálogo, o una propuesta vacía.

    La propuesta es una ayuda, no una condición: sin el extra `ml`, o sin el modelo de similitud en
    la caché local (precondición de UC-03, `docs/ERS.md`), el ítem queda pendiente y el informe lo
    declara igual. Mismo criterio que `rutas/rendimientos._veredicto_bosque` ante la falta del
    extra. Solo se construye si hay pendientes: cargar el modelo cuesta segundos.
    """
    try:
        from ml.normalization import NormalizadorPartidas

        normalizador = NormalizadorPartidas(
            {partida.codigo: partida.descripcion for partida in catalogo.partidas()}
        )
    except (ImportError, OSError):
        return lambda _descripcion: []
    return normalizador.similares
```

- [ ] **Step 4: Verde y artefacto regenerado**

Run: `uv run pytest tests/integration/test_api.py tests/integration/test_api_escenarios.py tests/integration/test_api_rendimientos.py tests/unit/test_openapi.py -q -W error --strict-markers -p no:cacheprovider && uv run python scripts/exportar_openapi.py && git diff --stat -- docs/api.json && uv run ruff check api tests`

Expected:
- Verde.
- `docs/api.json` cambia solo en `components/schemas`: aparecen `PropuestaPartidaRespuesta` e `ItemPendienteRespuesta`, y `pendientes` en `PresupuestoCreadoRespuesta`. Ninguna ruta cambia.
- ruff limpio.

**Comprobar que muerde:** en `_proponedor`, cambiar temporalmente `return normalizador.similares` por `return lambda _descripcion: []`. Deben fallar la prueba del doble y la del modelo real. Restaurar.

Después, «el recuento» (anotar `N5 = N3 + 3`) y `uv run pytest tests/unit/test_costing.py tests/integration/test_auditoria_7_de_7.py -q -W error -p no:cacheprovider`, que debe quedar verde.

- [ ] **Step 5: Commit del código**

```bash
git add api/esquemas.py api/rutas/presupuestos.py docs/api.json tests/integration/test_api.py
git commit -m "fix(api): uc-01 3a por http deja pendiente el item sin partida y propone similares" -m "Parte de C2 de INV-072: POST /presupuestos pedia composiciones de todos los codigos y respondia 404 ante una partida desconocida. Ahora solo pide las que existen; elaborar deja el item pendiente, el informe lo declara y la respuesta 201 lo lista con las propuestas de UC-03 (vacias sin el extra ml). Sin rutas nuevas; docs/api.json regenerado. La recarga del informe exige core y se registra aparte." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Registrar lo que exige `core/` (CLAUDE.md §9), sin parchear.** Agregar a la sección «Fase C2» de `docs/bitacora/2026-09-23-cierre.md`:

```markdown
### Expediente C2.1: la recarga del informe pierde los pendientes (INV‑075)

**Problema.** Tras elaborar con un ítem sin partida, el informe guardado lleva el hallazgo
`PENDIENTE` (`core/budget/persistencia.py:101-112`), pero:

- el ítem pendiente no se persiste, porque `:85-89` solo recorre `presupuesto.partidas`;
- la recarga reaudita con `auditar` (`api/rutas/presupuestos.py:378-385`), que no conoce los
  pendientes: los agrega `elaborar` (`core/budget/presupuesto.py:123,127`).

`GET /presupuestos/{codigo}/informe` declara entonces CUMPLE un presupuesto que se emitió NO CUMPLE.
RF‑02 pide el informe «al producir o cargar».

**Por qué no se corrige en C2.** La única frontera de persistencia del presupuesto es
`core/budget/persistencia.py` (su docstring, `:11-13`). Reconstruir el informe desde `api/`
duplicaría `_declarar_pendientes`. GC2 exige `core/` sin cambios, y GU1a (C3) también.

**Opciones para Eugenio en GC2.**

- (a) Una función de `core/budget/` que cargue el presupuesto con su informe completo, con los
  pendientes persistidos o con los hallazgos guardados, más sus llamadores de `api/` y `ui/` en
  commits separados. Exige una fase que pueda tocar `core/`, es decir, una enmienda de la spec §5.
- (b) Declararlo en limitaciones.

**Costo de no hacerlo:** el informe recargado subdeclara un presupuesto incompleto. El elaborado sí
lo declara.
```

Y al final de §3 del inventario (siguiente ID libre; al planificar, INV‑075):

```markdown
| INV-075 | planificación de C2 (Tarea 5; expediente C2.1 de la bitácora) | core (cruza: api, ui) | Informe siempre (principio 7) / trazabilidad (UC‑01 3a) | importante | `api/rutas/presupuestos.py:378-385`; `core/budget/presupuesto.py:123,127`; `core/budget/persistencia.py:85-89,101-112,119-144` | El informe recargado se reaudita con `auditar`, que no conoce los pendientes, y los ítems pendientes no se persisten: el presupuesto que se emitió NO CUMPLE por un ítem sin partida se recarga CUMPLE (RF‑02: el informe «al producir o cargar») | Una función de `core/budget/` que cargue el presupuesto con su informe completo, con llamadores de `api/` y `ui/` en commits separados; o declararlo en limitaciones | a decidir por Eugenio en GC2 (exige `core/`, cerrado en C2 y en C3) | abierto |
```

```bash
git add docs/bitacora/2026-09-23-cierre.md docs/auditoria/2026-09-inventario.md
git commit -m "docs(bitacora): la recarga del informe pierde los pendientes y exige core" -m "Expediente C2.1 e INV-075: se detiene la correccion en la frontera de core/ (CLAUDE.md seccion 9); su destino lo decide Eugenio en GC2." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: INV‑073 (adaptadores), flujos 1a, 2a y 2b de UC‑04

**Condición:** solo si la decisión previa 1 es **A**. Con **B**, esta tarea se reduce al paso 7 con el texto de la variante B.

**Files:**
- Create: `adapters/civil/recalculo.py`
- Create: `tests/unit/test_recalculo_civil.py`
- Test: `tests/unit/test_adapter_civil_ifc.py` (dos pruebas nuevas, flujo 2a)
- Modify: `docs/auditoria/2026-09-inventario.md` (paso 7)

**Interfaces:**
- Consumes:
  - `adapters.civil.evaluador.evaluar_regla`, la copia civil. Es una de las cinco de INV‑006, aceptada mientras no haya aval; si el aval llega, la migración incluye este módulo.
  - `adapters.civil.reglas.REGLA_RELLENO`, `AdaptadorCivilTabular` (solo en pruebas) y `AdaptadorCivilIFC`.
  - `core.budget.elaborar` (solo en pruebas).
- Produces, en `adapters.civil.recalculo`:
  - `recalcular(anteriores, cambios, codigos) -> Recalculo`;
  - `emparejar(anteriores, nuevos) -> Emparejamiento`;
  - `Recalculo(items, sin_regla, rechazados)`, `Emparejamiento(pares, solo_anteriores, solo_nuevos)` y `PARAMETROS_SOLO_EN_LA_FUENTE`.

**¿Existe la capacidad?** Los pasos 1 a 4 existen por composición (`tests/unit/test_recalculo_uc04.py`, C1). Los flujos alternativos, no:
- 1a: nada informa que un parámetro no participa.
- 2a: nada empareja por GlobalId.
- 2b: una cantidad negativa se rechaza con el `ValueError` del contrato (`core/contracts/item_computo.py:52-53`), que aborta todo.

`core/` no cambia. El hallazgo de R5 del flujo 2b lo emite `BalanceVolumetrico` (`core/verification/reglas.py:393-491`) al auditar, porque el relleno conservado ya no cuadra con su `_balance`.

**Oráculos (escritos a mano, en el docstring de la prueba):**
- **Flujo principal.** `AdaptadorCivilTabular.extraer` sobre la fuente con la fila editada, que es otra ruta de código.
- **Flujo 2b**, con la muestra `data/samples/civil/tanquillas_y_zanja.csv`:
  - relleno anterior = 3,6 + 7,68 − 0,896 − 25,2 × 0,008107338624 = **10,1796950666752** m3;
  - con Z‑01 de 500 × 0,001 × 0,001: excavación 3,6 + 0,0005, tubería 525 m y balance 3,6005 − 0,896 − 525 × 0,008107338624 = **−1,5518527776** m3.

- [ ] **Step 1: Pruebas.** Crear `tests/unit/test_recalculo_civil.py`:

```python
"""UC‑04 sobre el cómputo civil (INV‑073): el recálculo por reglas y sus flujos 1a y 2b.

El oráculo del flujo principal no pasa por `recalcular`: el mismo adaptador tabular extrae la
fuente con la fila ya editada, como la editaría el proyectista. El del flujo 2b es aritmética
escrita a mano sobre la muestra (`data/samples/civil/tanquillas_y_zanja.csv`; supuestos en
`tests/fixtures/computo_civil.py`):

- relleno anterior = 3,6 + 7,68 − 0,896 − 25,2 × 0,008107338624 = 10,1796950666752 m3;
- con la zanja Z‑01 de 500 m × 0,001 m × 0,001 m: excavación 3,6 + 0,0005, tubería 525 m, y el
  balance da 3,6005 − 0,896 − 525 × 0,008107338624 = −1,5518527776 m3, que el recálculo rechaza.

El flujo 2a (modelo IFC) vive en `tests/unit/test_adapter_civil_ifc.py`, que exige el extra civil.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.civil.recalculo import emparejar, recalcular
from adapters.civil.tabular import AdaptadorCivilTabular
from core.budget import elaborar, plan_secuencial
from core.contracts.verificacion import Severidad
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import composiciones_linea_base
from tests.fixtures.computo_civil import CODIGOS

MUESTRA = (
    Path(__file__).resolve().parents[2] / "data" / "samples" / "civil" / "tanquillas_y_zanja.csv"
)
RELLENO_ANTERIOR = Decimal("10.1796950666752")
BALANCE_CON_ZANJA_MINIMA = Decimal("-1.5518527776")
ZANJA_MINIMA = {
    "longitud": Decimal("500"),
    "ancho": Decimal("0.001"),
    "profundidad": Decimal("0.001"),
}


def _anteriores():
    return AdaptadorCivilTabular(CODIGOS).extraer(MUESTRA)


def _fuente_con(tmp_path: Path, fila_id: str, valores: dict[str, Decimal]) -> Path:
    """La muestra con los valores de una fila cambiados: la fuente que editaría el proyectista."""
    with MUESTRA.open(newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        campos = lector.fieldnames
        filas = [
            {**fila, **{clave: str(valor) for clave, valor in valores.items()}}
            if fila["id"] == fila_id
            else fila
            for fila in lector
        ]
    ruta = tmp_path / "fuente_editada.csv"
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


@pytest.mark.parametrize(
    ("fila_id", "valores"),
    [
        ("T-01", {"a": Decimal("1.00")}),  # la tanquilla: concreto, encofrado y excavación
        ("Z-01", {"longitud": Decimal("30.00")}),  # la zanja: el volumen de tubería se reescala
    ],
)
def test_recalcular_equivale_a_extraer_la_fuente_editada(tmp_path, fila_id, valores):
    """UC‑04, pasos 1 y 2 (RF‑19): las reglas afectadas se reevalúan, el relleno se rebalancea, y
    el resultado es exactamente lo que da extraer la fuente con la fila ya editada."""
    recalculo = recalcular(_anteriores(), {fila_id: valores}, CODIGOS)

    esperado = AdaptadorCivilTabular(CODIGOS).extraer(_fuente_con(tmp_path, fila_id, valores))
    assert recalculo.items == tuple(esperado)
    assert recalculo.sin_regla == () and recalculo.rechazados == ()


def test_1a_un_parametro_sin_regla_no_recalcula_y_se_informa():
    anteriores = _anteriores()

    recalculo = recalcular(anteriores, {"T-01": {"material": Decimal("1")}}, CODIGOS)

    assert recalculo.items == tuple(anteriores)
    assert recalculo.sin_regla == ("T-01:material",)
    assert recalculo.rechazados == ()


def test_el_diametro_solo_cambia_volviendo_a_extraer_la_fuente():
    """`diametro` participa en el balance del relleno por un factor fijado al extraer; ningún
    ítem lo lleva, así que no es un flujo 1a: se exige volver a extraer la fuente."""
    with pytest.raises(ValueError, match="vuelva a extraerla"):
        recalcular(_anteriores(), {"Z-01": {"diametro": Decimal("0.2032")}}, CODIGOS)


def test_2b_una_cantidad_nula_se_rechaza_y_conserva_la_anterior():
    anteriores = _anteriores()
    de_la_tanquilla = tuple(item for item in anteriores if item.origen_id == "T-01")

    recalculo = recalcular(anteriores, {"T-01": {"n": Decimal("0")}}, CODIGOS)

    assert recalculo.items == tuple(anteriores)
    assert recalculo.rechazados == de_la_tanquilla


def test_2b_un_relleno_negativo_se_rechaza_y_r5_lo_declara():
    anteriores = _anteriores()
    (relleno,) = [item for item in anteriores if item.codigo_partida == CODIGOS["relleno"]]
    assert relleno.cantidad == RELLENO_ANTERIOR  # el oráculo a mano coincide con la muestra

    recalculo = recalcular(anteriores, {"Z-01": ZANJA_MINIMA}, CODIGOS)

    assert recalculo.rechazados == (relleno,)
    assert relleno in recalculo.items
    resultado = elaborar(
        recalculo.items,
        composiciones_linea_base(),
        linea_base.PARAMETROS_LINEA_BASE,
        codigo="UC04-2B",
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
    )
    (hallazgo,) = [h for h in resultado.informe.hallazgos if h.regla == "R5"]
    assert hallazgo.severidad == Severidad.ERROR
    assert hallazgo.valor_observado == RELLENO_ANTERIOR
    assert hallazgo.valor_esperado == BALANCE_CON_ZANJA_MINIMA
    assert resultado.informe.partida_de(hallazgo) == CODIGOS["relleno"]
    assert not [h for h in resultado.informe.hallazgos if h.regla == "R1"]  # trazas intactas


def test_emparejar_rechaza_claves_repetidas():
    anteriores = _anteriores()
    with pytest.raises(ValueError, match="ambiguo"):
        emparejar([*anteriores, *anteriores], anteriores)
```

En `tests/unit/test_adapter_civil_ifc.py` agregar `from decimal import Decimal` y `from tests.fixtures.computo_civil import CODIGOS` a los imports, y al final:

```python
def test_uc04_2a_un_objeto_ifc_no_se_recalcula_por_reglas():
    """UC-04, flujo 2a: la fuente es un modelo, no reglas; se exige reimportarlo."""
    from adapters.civil.ifc import AdaptadorCivilIFC
    from adapters.civil.recalculo import recalcular

    items = AdaptadorCivilIFC().extraer(MUESTRA)

    with pytest.raises(ValueError, match="reimporte el modelo"):
        recalcular(items, {items[0].origen_id: {"a": Decimal("1.00")}}, CODIGOS)


def test_uc04_2a_reimportar_empareja_por_global_id(tmp_path):
    """UC-04, flujo 2a: al reimportar, la correspondencia de las partidas se conserva por GlobalId.
    Un modelo generado de nuevo tiene otro GlobalId: no es el mismo objeto y no se empareja."""
    import ifcopenshell

    from adapters.civil.ifc import AdaptadorCivilIFC
    from adapters.civil.recalculo import emparejar
    from scripts.generar_tanquilla_ifc import generar

    version_1 = tmp_path / "v1.ifc"
    generar(version_1)
    modelo = ifcopenshell.open(str(version_1))
    (volumen,) = modelo.by_type("IfcQuantityVolume")
    volumen.VolumeValue = 0.3
    version_2 = tmp_path / "v2.ifc"
    modelo.write(str(version_2))
    otro = tmp_path / "otro.ifc"
    generar(otro)

    adaptador = AdaptadorCivilIFC()
    anteriores = adaptador.extraer(version_1)
    nuevos = adaptador.extraer(version_2)
    ajenos = adaptador.extraer(otro)

    emparejamiento = emparejar(anteriores, nuevos)
    ((anterior, nuevo),) = emparejamiento.pares
    concreto = linea_base.APU_CONCRETO.codigo_partida
    assert anterior.origen_id == nuevo.origen_id
    assert anterior.cantidad == linea_base.CANTIDAD_POR_TANQUILLA_MEMORIA[concreto]
    assert nuevo.cantidad == Decimal("0.3")
    assert emparejamiento.solo_anteriores == () and emparejamiento.solo_nuevos == ()

    sin_par = emparejar(anteriores, ajenos)
    assert sin_par.pares == ()
    assert sin_par.solo_anteriores == tuple(anteriores)
    assert sin_par.solo_nuevos == tuple(ajenos)
```

- [ ] **Step 2: Primera versión, solo el flujo principal (rojo de comportamiento en los alternativos).** Crear `adapters/civil/recalculo.py` con el código del paso 3, pero **sin** las líneas marcadas `# UC‑04, flujo 1a`, `# UC‑04, flujo 2a`, `# UC‑04, flujo 2b` y `# fuente`. En cada bloque marcado se omite la condición y su cuerpo:
  - en `_separar`, sin el 1a todos los nombres van a `efectivos`;
  - en `_reevaluar`, sin el 2b no hay `return None`;
  - en `_rebalancear_relleno`, sin el 2b no se conserva el relleno.

Run: `uv run pytest tests/unit/test_recalculo_civil.py tests/unit/test_adapter_civil_ifc.py -q -W error --strict-markers -p no:cacheprovider`

Expected:
- Pasan las dos variantes de `test_recalcular_equivale_a_extraer_la_fuente_editada`, `test_emparejar_rechaza_claves_repetidas` y `test_uc04_2a_reimportar_empareja_por_global_id`.
- **Fallan**, cada una por comportamiento:
  - `test_1a_…`: `assert () == ('T-01:material',)`.
  - `test_el_diametro_…`: `DID NOT RAISE`.
  - `test_2b_una_cantidad_nula_…`: la tupla de ítems difiere, porque se aceptan ceros.
  - `test_2b_un_relleno_negativo_…`: `ValueError: cantidad no puede ser negativa`. Es el defecto exacto de INV‑073: el contrato aborta el recálculo.
  - `test_uc04_2a_un_objeto_ifc_…`: `DID NOT RAISE`.
- **Comprobar que el flujo principal muerde:** en `_reevaluar`, cambiar temporalmente `evaluar_regla(item.regla, parametros)` por `evaluar_regla(item.regla, item.parametros)`. Debe fallar `test_recalcular_equivale_…`. Restaurar.
- **Comprobar que `emparejar` muerde:** cambiar temporalmente `_clave` para que devuelva `(item.codigo_partida,)`. Debe fallar `test_uc04_2a_reimportar_…` en `sin_par.pares == ()`. Restaurar.

- [ ] **Step 3: Versión completa (verde).** `adapters/civil/recalculo.py`:

```python
"""Recálculo del cómputo civil ante un cambio de dimensiones (UC‑04; INV‑073).

Pasos 1 a 3 de UC‑04 del lado del cómputo: el proyectista cambia un parámetro de un objeto
paramétrico (el ancho de la tanquilla `T-01`, la longitud de la zanja `Z-01`) y el sistema vuelve a
evaluar **las reglas que lo usan**, con la expresión y los parámetros que cada `ItemComputo` ya
lleva (RF‑18, RF‑19). Los flujos alternativos de `docs/ERS.md` (UC‑04):

- 1a. Un parámetro que no participa en ninguna regla de su objeto no produce recálculo: se informa
  en `Recalculo.sin_regla` y los ítems no cambian.
- 2a. Un objeto que viene de un modelo IFC no tiene reglas que reevaluar: `recalcular` lo rechaza y
  pide reimportar el modelo (UC‑01, paso 2); `emparejar` conserva la correspondencia de las
  partidas por `origen_id`, que es el GlobalId.
- 2b. Una regla que da una cantidad negativa o nula no la impone: el ítem conserva su valor
  anterior y queda en `Recalculo.rechazados`. El hallazgo de R5 lo emite el núcleo al auditar,
  porque el relleno conservado deja de cuadrar con su directiva de balance.

El paso 5 (RF‑20, el diferencial) no está implementado: se declaró en limitaciones en C1.

Este módulo no toca `core/` (CLAUDE.md §2 y §9): importa solo `core.contracts` y su propio paquete,
y evalúa con la copia civil del evaluador (una de las cinco de INV‑006, aceptada mientras no haya
aval del tutor).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from adapters.civil.evaluador import evaluar_regla
from adapters.civil.reglas import REGLA_RELLENO
from core.contracts import ItemComputo, OrigenTipo

__all__ = [
    "PARAMETROS_SOLO_EN_LA_FUENTE",
    "Emparejamiento",
    "Recalculo",
    "emparejar",
    "recalcular",
]

#: Parámetros de la fuente que ningún ítem lleva. `diametro` entra al cómputo solo por el factor de
#: sección que el adaptador tabular fija en la directiva de balance del relleno
#: (`REGLA_VOLUMEN_TUBERIA`): cambiarlo exige volver a extraer la fuente (UC‑01, paso 2).
PARAMETROS_SOLO_EN_LA_FUENTE = frozenset({"diametro"})

_CERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class Recalculo:
    """La versión recalculada del cómputo y lo que el recálculo informa (UC‑04).

    `sin_regla` lista `"origen:parametro"` de cada cambio que no participa en ninguna regla (1a).
    `rechazados` son los ítems anteriores que se conservaron porque su regla dio una cantidad
    negativa o nula (2b); ya están también en `items`.
    """

    items: tuple[ItemComputo, ...]
    sin_regla: tuple[str, ...] = ()
    rechazados: tuple[ItemComputo, ...] = ()


@dataclass(frozen=True, slots=True)
class Emparejamiento:
    """Ítems de dos extracciones del mismo modelo, emparejados por `(origen_id, codigo_partida)`."""

    pares: tuple[tuple[ItemComputo, ItemComputo], ...]
    solo_anteriores: tuple[ItemComputo, ...]
    solo_nuevos: tuple[ItemComputo, ...]


def recalcular(
    anteriores: Sequence[ItemComputo],
    cambios: Mapping[str, Mapping[str, Decimal]],
    codigos: Mapping[str, str],
) -> Recalculo:
    """Reevalúa las reglas que usan los parámetros cambiados, objeto por objeto.

    :param anteriores: el cómputo vigente, tal como lo devolvió el adaptador.
    :param cambios: por objeto (`origen_id`), los parámetros nuevos, en `Decimal`.
    :param codigos: el mismo mapeo que recibe `AdaptadorCivilTabular`; si trae `relleno`, el
        relleno se recalcula con los totales nuevos.
    """
    efectivos, sin_regla = _separar(anteriores, cambios)
    if not efectivos:
        return Recalculo(items=tuple(anteriores), sin_regla=sin_regla)

    items: list[ItemComputo] = []
    rechazados: list[ItemComputo] = []
    for item in anteriores:
        propios = {
            nombre: valor
            for nombre, valor in efectivos.get(item.origen_id, {}).items()
            if nombre in item.parametros
        }
        nuevo = _reevaluar(item, propios) if propios and item.regla else item
        if nuevo is None:  # UC‑04, flujo 2b
            rechazados.append(item)  # UC‑04, flujo 2b
            nuevo = item  # UC‑04, flujo 2b
        items.append(nuevo)

    if "relleno" in codigos:
        items, del_relleno = _rebalancear_relleno(anteriores, items, codigos)
        rechazados.extend(del_relleno)
    return Recalculo(items=tuple(items), sin_regla=sin_regla, rechazados=tuple(rechazados))


def emparejar(anteriores: Sequence[ItemComputo], nuevos: Sequence[ItemComputo]) -> Emparejamiento:
    """UC‑04, flujo 2a: empareja la extracción anterior con la del modelo reimportado.

    La clave es `(origen_id, codigo_partida)`: en IFC el `origen_id` es el GlobalId del elemento, y
    el código distingue las partidas que un mismo objeto produce. Una clave repetida haría ambiguo
    el emparejamiento: se rechaza.
    """
    indice_nuevos = _indice(nuevos, "nueva")
    _indice(anteriores, "anterior")
    pares = tuple(
        (anterior, indice_nuevos[_clave(anterior)])
        for anterior in anteriores
        if _clave(anterior) in indice_nuevos
    )
    emparejadas = {_clave(anterior) for anterior, _ in pares}
    return Emparejamiento(
        pares=pares,
        solo_anteriores=tuple(a for a in anteriores if _clave(a) not in emparejadas),
        solo_nuevos=tuple(n for n in nuevos if _clave(n) not in emparejadas),
    )


def _separar(
    anteriores: Sequence[ItemComputo], cambios: Mapping[str, Mapping[str, Decimal]]
) -> tuple[dict[str, dict[str, Decimal]], tuple[str, ...]]:
    """Los cambios que tocan alguna regla de su objeto, y los que no (flujo 1a)."""
    efectivos: dict[str, dict[str, Decimal]] = {}
    sin_regla: list[str] = []
    for origen_id, parametros in cambios.items():
        del_objeto = [item for item in anteriores if item.origen_id == origen_id]
        if not del_objeto:
            raise ValueError(f"ningun item del computo tiene el origen {origen_id!r}")
        if any(item.origen_tipo is OrigenTipo.IFC for item in del_objeto):  # UC‑04, flujo 2a
            raise ValueError(  # UC‑04, flujo 2a
                f"el objeto {origen_id!r} viene de un modelo IFC, no de reglas: reimporte el "
                "modelo (UC-01, paso 2) y empareje las partidas con `emparejar` (UC-04, 2a)"
            )  # UC‑04, flujo 2a
        participan = {nombre for item in del_objeto if item.regla for nombre in item.parametros}
        for nombre, valor in parametros.items():
            if nombre in PARAMETROS_SOLO_EN_LA_FUENTE:  # fuente
                raise ValueError(  # fuente
                    f"{nombre!r} no lo lleva ningun item: entra al computo por la fuente; "
                    "vuelva a extraerla (UC-01, paso 2)"
                )  # fuente
            if nombre not in participan:  # UC‑04, flujo 1a
                sin_regla.append(f"{origen_id}:{nombre}")  # UC‑04, flujo 1a
                continue  # UC‑04, flujo 1a
            efectivos.setdefault(origen_id, {})[nombre] = valor
    return efectivos, tuple(sin_regla)


def _reevaluar(item: ItemComputo, cambios: Mapping[str, Decimal]) -> ItemComputo | None:
    """El ítem con su regla reevaluada, o `None` si la cantidad no es positiva (flujo 2b)."""
    parametros = {**item.parametros, **cambios}
    cantidad = evaluar_regla(item.regla, parametros)
    if cantidad <= _CERO:  # UC‑04, flujo 2b
        return None  # UC‑04, flujo 2b
    return replace(item, cantidad=cantidad, parametros=parametros)


def _rebalancear_relleno(
    anteriores: Sequence[ItemComputo], items: list[ItemComputo], codigos: Mapping[str, str]
) -> tuple[list[ItemComputo], list[ItemComputo]]:
    """El relleno, que se deriva de totales y no de un objeto, recalculado con los ítems nuevos.

    La excavación y el concreto se vuelven a sumar. El volumen de tubería se escala con la longitud
    de tubería: el adaptador tabular admite un solo diámetro por balance (límite declarado en
    `AdaptadorCivilTabular`), así que ese volumen es proporcional a la tubería. Un relleno que queda
    negativo o nulo se rechaza como cualquier otra cantidad (flujo 2b).
    """
    tuberia_antes = _suma(anteriores, codigos["tuberia"])
    tuberia_despues = _suma(items, codigos["tuberia"])
    resultado: list[ItemComputo] = []
    rechazados: list[ItemComputo] = []
    for item in items:
        if item.codigo_partida != codigos["relleno"] or item.regla != REGLA_RELLENO:
            resultado.append(item)
            continue
        volumen = item.parametros["volumen_tuberia"]
        parametros = {
            "excavacion": _suma(items, codigos["excavacion"]),
            "concreto": _suma(items, codigos["concreto"]),
            "volumen_tuberia": (
                volumen * tuberia_despues / tuberia_antes if tuberia_antes else volumen
            ),
        }
        if parametros == dict(item.parametros):
            resultado.append(item)
            continue
        cantidad = evaluar_regla(REGLA_RELLENO, parametros)
        if cantidad <= _CERO:  # UC‑04, flujo 2b
            rechazados.append(item)  # UC‑04, flujo 2b
            resultado.append(item)  # UC‑04, flujo 2b
            continue  # UC‑04, flujo 2b
        resultado.append(replace(item, cantidad=cantidad, parametros=parametros))
    return resultado, rechazados


def _suma(items: Sequence[ItemComputo], codigo: str) -> Decimal:
    return sum((item.cantidad for item in items if item.codigo_partida == codigo), _CERO)


def _clave(item: ItemComputo) -> tuple[str, str]:
    return (item.origen_id, item.codigo_partida)


def _indice(items: Sequence[ItemComputo], version: str) -> dict[tuple[str, str], ItemComputo]:
    indice: dict[tuple[str, str], ItemComputo] = {}
    for item in items:
        clave = _clave(item)
        if clave in indice:
            raise ValueError(
                f"la version {version} repite el origen {clave[0]!r} para la partida "
                f"{clave[1]!r}: el emparejamiento seria ambiguo"
            )
        indice[clave] = item
    return indice
```

Las marcas `# UC‑04, flujo …` y `# fuente` se quedan: documentan qué línea realiza qué flujo. En el paso 2 solo sirvieron para quitar esas líneas.

Run: `uv run pytest tests/unit/test_recalculo_civil.py tests/unit/test_adapter_civil_ifc.py tests/unit/test_recalculo_uc04.py tests/unit/test_reglas_civil.py tests/unit/test_arquitectura.py -q -W error --strict-markers -p no:cacheprovider && uv run ruff check adapters tests`
Expected:
- Verde, con `test_arquitectura.py` cubriendo `adapters/civil/recalculo.py`: solo importa la biblioteca estándar, `core.contracts` y `adapters.civil`.
- ruff limpio. Si una línea supera los 100 caracteres, se parte sin cambiar su contenido.

Después, «el recuento» (anotar `N6`), y `uv run pytest tests/unit/test_costing.py tests/integration/test_auditoria_7_de_7.py -q -W error -p no:cacheprovider` en verde, y `git diff --stat $(git merge-base main HEAD)..HEAD -- core/` vacío.

- [ ] **Step 4: Commit**

```bash
git add adapters/civil/recalculo.py tests/unit/test_recalculo_civil.py tests/unit/test_adapter_civil_ifc.py
git commit -m "fix(civil): flujos 1a, 2a y 2b de uc-04 en el adaptador civil" -m "Parte de C2 de INV-073 (decision previa 1, opcion A): recalcular reevalua las reglas que usan el parametro cambiado y rebalancea el relleno; informa lo que no participa en ninguna regla (1a), exige reimportar un objeto IFC y empareja por GlobalId (2a), y conserva la cantidad anterior ante una regla negativa o nula (2b), con el hallazgo de R5 emitido por el nucleo existente al auditar. Oraculos: la extraccion de la fuente editada y aritmetica a mano. core/ sin cambios." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 5: Comprobar que ninguna prueba vieja fija el comportamiento anterior.**

Run: `grep -rn "cantidad no puede ser negativa" tests adapters`
Expected: solo las pruebas de contrato (`tests/unit/test_contracts.py`), que el recálculo no afecta, porque el contrato sigue rechazando negativos.

- [ ] **Step 6: Anotar el alcance que no se implementa.** A la sección «Fase C2» de la bitácora:

```markdown
**UC‑04 fuera del límite (spec §2).** `recalcular` y `emparejar` no tienen llamador en `ui/` ni en
`api/`: UC‑04 no tiene pantalla ni ruta, y agregarlas sería capacidad nueva. Se registra como
trabajo futuro. La ERS §3.1, que promete UC‑04 en la interfaz, es INV‑030 (C4).
```

- [ ] **Step 7: Estado de INV‑073.** En la fila de INV‑073 del inventario, la columna «Estado» pasa a:
  - **Variante A:** `abierto: la parte de C2 (adaptadores) cerrada en <hash del paso 4>; queda la subtarea documental de C4 (ERS §3.2 y plan_pruebas §8 trazan 1a, 2a y 2b a sus pruebas)`.
  - **Variante B:** `abierto: por decisión de Eugenio (<fecha>) los flujos 1a, 2a y 2b no se implementan; C4 los declara sin cumplir en la ERS §3.2 y en plan_pruebas §8`.

```bash
git add docs/bitacora/2026-09-23-cierre.md docs/auditoria/2026-09-inventario.md
git commit -m "docs(auditoria): estado de inv-073 tras c2" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Compuerta GC2

**Files:**
- Modify: `docs/auditoria/2026-09-inventario.md` (estados, anclas desplazadas y §4 (d))
- Modify: `docs/bitacora/2026-09-23-cierre.md` (sección GC2)

**Interfaces:**
- Consumes: Tareas 0 a 6.
- Produces: el veredicto de GC2 y, con permiso de Eugenio, el PR de C2 con la etiqueta `gc2`.

- [ ] **Step 1: Línea base y 7 de 7**

Run: `uv run pytest tests/unit/test_costing.py tests/unit/test_costing_destajo.py::test_la_linea_base_no_se_mueve tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61 tests/integration/test_auditoria_7_de_7.py tests/integration/test_composicion_extremo_a_extremo.py -q -W error --strict-markers -p no:cacheprovider --junitxml=reporte-pruebas.xml`, y leer el recuento del XML con el mismo `python -c` de Global Constraints.
Expected: `27 0 0 0`, el mismo conjunto que en GC1: 1 586,61 USD y 7 de 7.

- [ ] **Step 2: Guardia de arquitectura**

Run: `uv run pytest tests/unit/test_arquitectura.py -q -W error --strict-markers -p no:cacheprovider`
Expected: verde, incluidas `test_un_adaptador_solo_importa_contratos_su_paquete_y_sus_terceros[civil|industrial|sistemas|telecom]`, `test_toda_carpeta_de_adapters_tiene_su_regla` y `test_la_guardia_cubre_todo_paquete_de_primer_nivel_fuera_del_nucleo`.

- [ ] **Step 3: `core/` intacto (criterio de la spec §5) y guardia del núcleo**

Run:

```bash
git diff --stat $(git merge-base main HEAD)..HEAD -- core/
uv run python scripts/guardia_nucleo.py --base main
for c in $(git rev-list main..HEAD); do f=$(git show --name-only --format= "$c"); if echo "$f" | grep -q '^core/'; then echo "TOCA-CORE $c"; fi; done
```

Expected:
- El primer comando no imprime nada.
- La guardia sale con código 0 e imprime `guardia del nucleo: OK: N commits evaluados; 0 ramas de adaptador con git diff core/ vacio`. Ya no dice PENDIENTE: C2 sí tiene commits en `adapters/`.
- Ninguna línea `TOCA-CORE`.
- **Si algo de esto falla, GC2 no se cruza.** Se revierte el commit que toca `core/` y su hallazgo va a expediente.

- [ ] **Step 4: Suite completa, lint, salvaguarda y artefactos**

Run: «el recuento», y después:

```bash
uv run ruff check .
uv run pytest tests/unit/test_salvaguarda.py -q -W error --strict-markers -p no:cacheprovider
uv run python scripts/exportar_openapi.py && git diff --exit-code -- docs/api.json && echo api-ok
uv run python scripts/generar_resultados_ml.py && git diff --exit-code -- docs/resultados_ml.md && echo ml-ok
```

Expected:
- `N1 0 0 0` con `verificar omitidas: 0 omitidas`.
- ruff limpio.
- `3 passed` en la salvaguarda.
- `api-ok` y `ml-ok`: los dos artefactos que la CI regenera no cambian.
- Anotar `N1` frente a `N0 = 735`, con el desglose por tarea (`N3`, `N5` y `N6`).

- [ ] **Step 5: Estados del inventario.** Con `git log --format="%h %s" main..HEAD`, reemplazar la columna «Estado»:
  - `cerrado (<hash>)` para INV‑016 (Tarea 1), INV‑017 (Tarea 2, paso 4), INV‑018 (Tarea 3) e INV‑042 (Tarea 4).
  - INV‑072: `abierto: la parte de C2 (api) cerrada en <hash de la Tarea 5, paso 5>; quedan la subtarea de C3 (ui) y la recarga del informe, que exige core/ (INV‑075)`.
  - INV‑073: el de la Tarea 6, paso 7.
  - INV‑006: conserva su estado. Se agrega al final: `; en C2 no hubo código: la subtarea de C2 sigue aceptada con el hallazgo padre (sin aval del tutor al cerrar C2)`.
  - INV‑038 e INV‑041: conservan «a limitaciones»; no hay código en C2.
  - INV‑074 e INV‑075: el destino que decida Eugenio en el paso 8.
  - En la columna «Evidencia» de INV‑018 e INV‑042, anotar las anclas desplazadas de la tabla «Anclas verificadas» (p. ej. `test_adapter_civil_ifc.py:61-73 (hoy :64-76)`).
  - En §4 (d), recontar con un script ad hoc sobre la tabla, como en C0 y C1, agregando INV‑074 e INV‑075 a su fase principal una vez decidida. Al final de §4 agregar: «La fase C2 agrega INV‑074 e INV‑075 (Tareas 2 y 5 del plan de C2) y cierra los hallazgos de su fase según la columna «Estado»».

- [ ] **Step 6: Bitácora.** Agregar a la sección «Fase C2» de `docs/bitacora/2026-09-23-cierre.md`:
  - (a) La tabla de hallazgos de C2: ID → estado → commit. Incluye INV‑006, INV‑038 e INV‑041, «sin código en C2».
  - (b) Los hallazgos nuevos (INV‑074, INV‑075) con su fase.
  - (c) Pruebas: `N0 = 735` → `N1`, leídas con `--junitxml`.
  - (d) La tabla de dictámenes de abajo.
  - (e) Los veredictos de los cuatro encargos (paso 7).
  - (f) La ejecución de la aplicación por Eugenio (paso 8).
  - (g) Las sesiones de redacción (fase Red) hechas durante C2 y el estado de la compensación del capítulo IV.
  - (h) La salida del paso 3, con **el `git diff --stat $(git merge-base main HEAD)..HEAD -- core/` vacío anotado** (spec §5), y la línea `**GC2: pendiente de CI.** Criterios locales cumplidos y dictámenes ratificados el AAAA‑MM‑DD; falta la CI verde en ubuntu-latest y windows-latest (paso 11).`, con la fecha real. GC2 **no** se declara cruzada en este commit.

```markdown
### Decisiones de C2 pendientes de ratificación

| # | Decisión | Motivo | Costo si es errónea | Ratificada por Eugenio |
|---|---|---|---|---|
| C2‑1 | INV‑073 por la vía A (o B): `adapters/civil/recalculo.py` realiza 1a, 2a y 2b sin llamador en `ui/` ni `api/` | Flujos de la ERS (corrección, spec §2); UC‑04 ya es composición de biblioteca desde C1 | ~150 líneas sin llamador; con B, tres flujos declarados sin cumplir | (antes de ejecutar) |
| C2‑2 | INV‑072: `POST /presupuestos` responde 201 con `pendientes` y sus propuestas; aceptar es reenviar el ítem; sin rutas nuevas | Realiza UC‑01 3a en la ruta existente; el campo nuevo es aditivo | Un cliente que dependía del 404 cambia de comportamiento (ninguna prueba lo hacía) | (antes de ejecutar) |
| C2‑3 | La recarga del informe (INV‑075) no se corrige: exige `core/`; expediente C2.1 | CLAUDE.md §9 y GC2 | El informe recargado subdeclara un presupuesto con pendientes hasta que se decida (a) o (b) | |
| C2‑4 | Sin el extra `ml` o sin el modelo, las propuestas quedan vacías (`ImportError`, `OSError`) | La propuesta es una ayuda; mismo criterio que `ml.anomaly` en la API | Un fallo de red se ve como «sin propuestas» y no como error | |
| C2‑5 | INV‑018: la regla de telecom rige para los cuatro adaptadores, con terceros declarados (civil: `ifcopenshell`); la guardia genérica queda para `ml/` | Una sola fuente de la regla; ningún criterio más débil | Un tercero nuevo exige editar `TERCEROS_POR_ADAPTADOR` | |
| C2‑6 | INV‑073: 2b rechaza también la cantidad nula; `diametro` exige volver a extraer; el volumen de tubería del relleno se escala por proporción | Texto de la ERS; el diámetro solo vive en la fuente; un solo diámetro por balance | Un cambio de diámetro no se puede recalcular sin reextraer | |
| C2‑7 | INV‑074 (latente, `scripts/`): a limitaciones salvo que se promueva a C3 | Menor; hoy la afirmación es cierta | El informe podría contradecirse si un dominio supera 50 registros | |
| C2‑8 | INV‑075: (a) fase que toque `core/`, con enmienda de la spec §5, o (b) limitaciones | Exige `core/`, cerrado en C2 y C3 | (a) reabre el núcleo; (b) deja RF‑02 parcial al recargar | |
| C2‑9 | Sin código en C2 para INV‑006 (subtarea), INV‑038 (subtarea) e INV‑041 | Exigen contrato con aval pendiente, o están en limitaciones por GC0 | Si el tutor avala INV‑006, la migración de los cuatro evaluadores (y de `recalculo.py`) se reabre antes de `v1.0-tesis` | |
```

(C2‑1 y C2‑2 llevan en la última columna la decisión anotada en la Tarea 0, paso 4.)

- [ ] **Step 7: Los cuatro encargos, en paralelo y en segundo plano.** Una llamada `Agent` por encargo, las cuatro en el mismo mensaje, todas sobre `git diff $(git merge-base main HEAD)..HEAD` más la spec, el inventario, el expediente C2.1 y este plan. Cada prompt incluye:
  - El encargo y su norma:
    - **Requisitos:** IEEE 830 y la ERS, con UC‑01 3a, UC‑04 1a/2a/2b, RF‑02, RF‑04, RF‑09, RF‑23 y RF‑28. Confirma que ningún cambio es capacidad nueva (spec §2).
    - **Arquitectura:** vistas 4+1 y CLAUDE.md §2, §5 y §9. Verifica el paso 3, la regla de importaciones de `adapters/civil/recalculo.py` y que la dependencia `api → ml` no se amplió más allá de `ml.normalization`.
    - **Pruebas y calidad:** IEEE 829 e ISO/IEC 25010. Verifica los cinco puntos de **Review Focus**, que cada prueba nueva se observó en rojo por comportamiento o mordiendo, que los oráculos son independientes y que el recuento se leyó con `--junitxml`.
    - **Verificación de hechos:** abre cada cita `archivo:línea` de este plan, del expediente C2.1, del inventario y de la bitácora, y la confirma. Incluye la aritmética de los oráculos de la Tarea 6.
  - La instrucción de devolver **VEREDICTO** (aprueba / aprueba con correcciones / rechaza) y hallazgos con severidad, evidencia y corrección concreta.
  - La prohibición de editar archivos.

  Cada hallazgo bloqueante se corrige en un commit propio y se vuelve a pasar **solo** el encargo que lo levantó, hasta que los cuatro aprueben. Los hallazgos nuevos que no se corrijan en C2 van al inventario vivo. Si uno exige `core/`, va a expediente, no a parche.

- [ ] **Step 8: Eugenio ejecuta la aplicación y ratifica** (spec §6). El cambio principal es la API. **Nunca contra `data/apu.db`**: la API abre esa ruta por defecto (`api/dependencias.py:14`).

```bash
uv run python scripts/seed.py --db data/prueba_c2.db
APU_BASE="sqlite:///data/prueba_c2.db" uv run uvicorn api.main:app
```

  - En `http://127.0.0.1:8000/docs`, enviar `POST /presupuestos` con los ítems de la línea base más uno de código `XX-99-NUE`. Debe responder 201 con el ítem en `pendientes` y hasta tres propuestas.
  - Abrir `GET /presupuestos/{codigo}/informe` y comprobar lo que registra INV‑075: el informe recargado no declara el pendiente.
  - Para INV‑073 (variante A), ejecutar `uv run pytest tests/unit/test_recalculo_civil.py -q -p no:cacheprovider`.
  - Al terminar, comprobar que `data/apu.db` no cambió (existencia y fecha anotadas en la Tarea 0).
  - Después, ratificar cada fila de la tabla del paso 6 y decidir C2‑7 y C2‑8. Sin ratificación, la compuerta no se cruza.

- [ ] **Step 9: Commit (GC2 pendiente de CI)**

```bash
git add docs/auditoria/2026-09-inventario.md docs/bitacora/2026-09-23-cierre.md
git commit -m "docs(bitacora): compuerta gc2 del cierre, pendiente de ci" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 10: Push y PR, solo con permiso expreso de Eugenio.**

Run: `git push -u origin inc/cierre-C2`, seguido de:

```bash
gh pr create --base main --title "Cierre de la tesis: fase C2 (adaptadores, ML y API)" --label gc2 --body "$(cat <<'EOF'
Fase C2 del plan de cierre: INV-016, INV-017, INV-018 e INV-042 (pruebas), INV-072 en la API (UC-01 3a por HTTP) e INV-073 en el adaptador civil (flujos 1a, 2a y 2b de UC-04). core/ sin cambios: git diff --stat de la base de fusion a HEAD sobre core/ vacio. La recarga del informe con pendientes exige core y queda registrada (INV-075, expediente C2.1). INV-006 (subtarea de C2) sigue aceptada sin aval del tutor. Compuerta GC2 en docs/bitacora/2026-09-23-cierre.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Si la etiqueta `gc2` no existe, se crea con `gh label create gc2`, también con permiso.

Run después: `gh pr checks --watch`
Expected: `calidad`, `ubuntu-latest` y `windows-latest` en verde. Si alguno falla, GC2 sigue pendiente: se corrige en un commit propio, se empuja con el mismo permiso y se repite este paso.

- [ ] **Step 11: Declarar GC2 cruzada, solo con la CI en verde.** En la sección «Fase C2» de la bitácora, reemplazar la línea `**GC2: pendiente de CI.** …` por:

```markdown
**GC2: cruzada el AAAA‑MM‑DD.** CI verde en calidad, `ubuntu-latest` y `windows-latest` sobre el
commit HASH_CI (PR #NUMERO_PR); `git diff --stat $(git merge-base main HEAD)..HEAD -- core/` vacío;
criterios locales y dictámenes ratificados según las secciones anteriores.
```

(Sustituir la fecha real, el hash corto que probó la CI y el número del PR.)

```bash
git add docs/bitacora/2026-09-23-cierre.md
git commit -m "docs(bitacora): gc2 cruzada con la ci en verde" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
git push
```

El `push` va con el permiso del paso 10. La fusión es con merge commit y la decide Eugenio (spec §6).

---

## Autorrevisión del plan

**Cobertura de los hallazgos de C2** (toda fila cuya «Fase destino» empieza por C2 o nombra una subtarea de C2, más el menor promovido):

| Hallazgo | Tarea | Cierre en C2 |
|---|---|---|
| INV‑016 (importante) | 1 | completo, con mutación observada en las dos direcciones |
| INV‑017 (importante) | 2 | completo; deja registrado el latente INV‑074 |
| INV‑018 (importante) | 3 | completo: una regla, terceros declarados, prueba de cobertura; anclas desplazadas anotadas |
| INV‑042 (menor promovido) | 4 | completo; recuento idéntico antes y después |
| INV‑072 (importante; C2 api + C3 ui) | 5 | parte de `api/` completa. Quedan la de C3 (`ui/`) y la recarga del informe, que exige `core/` (INV‑075) |
| INV‑073 (importante; C2 adapters + C4 docs) | 6 | con la decisión A, parte de C2 completa y documentos para C4; con B, sin código y documentos para C4 |
| INV‑006 (subtarea de C2) | 7, paso 5 | **sin código**: aceptada con el padre; el aval del tutor no llegó |
| INV‑038 (subtarea de C2) | 7, paso 5 | sin código: a limitaciones (exige contrato) |
| INV‑041 | 7, paso 5 | sin código: a limitaciones (autonomía declarada, dictamen R5 de GC0) |
| Flujos 1a, 2a y 2b de UC‑04 registrados por C1 para C2 | 6 | son INV‑073 |

**Lo que no se pudo planificar en concreto, y por qué:**

- **La migración de los cuatro evaluadores (subtarea de C2 de INV‑006).** Depende del aval del tutor sobre `core.contracts.expresiones` (expediente A.3), que no se ha dado. Por spec §4 queda *aceptada por decisión de arquitectura registrada* con su padre. `adapters/civil/recalculo.py` agrega un consumidor de la copia civil. Si el aval llega, entra en esa migración.
- **La recarga del informe con pendientes (INV‑075).** Exige `core/budget/` y GC2 prohíbe tocar `core/`. Se documenta con expediente (C2.1) y se deja a Eugenio en GC2. Su corrección no se planifica porque no hay fase que pueda tocar `core/` sin enmendar la spec §5.
- **La parte de `ui/` de INV‑072.** Es de C3. C3 heredará el mismo límite de INV‑075, porque GU1a también exige `core/` sin cambios.
- **La documentación de INV‑073 (ERS §3.2 y plan_pruebas §8).** Es de C4.
- **Una ruta de API o una pantalla para UC‑04, y una ruta de UC‑03 en la API.** Serían capacidad nueva (spec §2): no se planifican y quedan como trabajo futuro si Eugenio las quisiera.
- **La corrección de INV‑074.** Es de `scripts/` (C3) y menor: se registra y la decide Eugenio.
- **Los recuentos exactos tras cada tarea.** No se fijan, salvo `N0 = 735` y que la Tarea 4 no cambia el número. El plan manda leerlos con `--junitxml` y anotarlos.
- **La compensación de la regla de reparto (capítulo IV antes de C2).** No consta al abrir C2. La redacción no es parte de este plan: se registra en la bitácora (Tarea 0, paso 4; Tarea 7, paso 6 (g)).

### Critical Files for Implementation

- C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C2\api\rutas\presupuestos.py
- C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C2\adapters\civil\reglas.py (lo consume el nuevo `adapters/civil/recalculo.py`)
- C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C2\tests\unit\test_arquitectura.py
- C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C2\tests\integration\conftest.py
- C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C2\docs\auditoria\2026-09-inventario.md