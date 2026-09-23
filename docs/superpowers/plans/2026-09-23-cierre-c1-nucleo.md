# Cierre de la tesis, fase C1: núcleo, salvaguarda y guardia de arquitectura

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Goal:** Cerrar los hallazgos de la fase C1 del inventario aprobado en GC0: el bloqueante INV‑065 y los importantes INV‑001 a INV‑015 e INV‑069. Primero va la salvaguarda de `data/apu.db` y la guardia de arquitectura ampliada a `scripts/` y `tests/`. Los hallazgos que exigen cambiar `core/contracts/` no se tocan: se documentan con expediente y se elevan al tutor. Con todo eso se cruza la compuerta **GC1**.

**Architecture:** C1 corrige el núcleo sin tocar los contratos (`git diff --stat main -- core/contracts` vacío de principio a fin).

- **Fuera de `core/`.** La salvaguarda vive en `tests/conftest.py` y la guardia en `tests/unit/test_arquitectura.py`. El guion manual se corrige y queda vigilado por una prueba que lo lee como texto.
- **`core/verification/`.** El evaluador rechaza parámetros que no son `Decimal` (INV‑003). Una regla que no se puede evaluar pasa a informarse como INFO «regla no evaluable», y R7 se declara no aplicable cuando no hay plan (INV‑012).
- **`core/catalog/`.** Queda una sola fórmula de variación (INV‑004) y una sola puerta de registro de rendimientos (INV‑005).
- **`core/budget/`.**
  - `elaborar` pasa a ser el único punto del protocolo «presupuesto valorado → plan → curva → auditoría»: acepta `plan=plan_secuencial` (INV‑069).
  - Un ítem sin partida queda pendiente y el informe lo declara, sin tocar ningún contrato (INV‑013).
  - Módulo nuevo `diferencial.py` para RF‑20 (INV‑011).
  - `descartar_version` para UC‑02 7a (INV‑015).
- **Llamadores.** Los cinco llamadores del protocolo en `ui/`, `api/` y `scripts/` se migran en commits separados.
- **Pruebas.** Las fixtures ganan nombres, sin cambiar ningún valor de la línea base (INV‑008, INV‑009). Se agregan las pruebas que faltaban (INV‑011, INV‑014, INV‑015).
- **Contratos.** INV‑001, INV‑002 e INV‑006 se resuelven con expediente, aval pendiente del tutor y el estado «aceptado por decisión de arquitectura registrada».

**Tech Stack:** Python 3.13 · SQLAlchemy 2 · pytest (`-W error --strict-markers`) · ruff · uv · Streamlit 1.62 (`AppTest`) · FastAPI (`TestClient`) · Markdown

**Spec:** [docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md](../specs/2026-09-23-plan-cierre-tesis-design.md). Las secciones que manda este plan:

- §4: criterios, severidad, regla de los hallazgos que cruzan capas y estado *aceptado por decisión de arquitectura registrada*.
- §5: fila C1 y compuerta GC1.
- §6: organización, ramas sin apilar y ratificación.

**Plan de fases:** [PLAN_CIERRE.md](../../../PLAN_CIERRE.md). **Inventario:** [docs/auditoria/2026-09-inventario.md](../../auditoria/2026-09-inventario.md). **Bitácora:** `docs/bitacora/2026-09-23-cierre.md`.

**Rama y worktree:** `inc/cierre-C1` en `.claude/worktrees/cierre-C1`, creada desde `main` en `384a7fa`.

---

## Global Constraints

- **`Decimal` en todo lo monetario y dimensional, nunca `float`** (CLAUDE.md §2, principio 3). Los únicos `float` que escribe este plan son datos degradados dentro de pruebas que comprueban que el núcleo los rechaza (INV‑003).
- **El motor de costos es una función pura** (principio 4). `core/costing/` no se toca.
- **El informe de auditoría se genera siempre** (principio 7). Ningún cambio de este plan puede producir un presupuesto sin su informe.
- **Línea base en 1 586,61 USD y auditoría en 7 de 7, intactas.**
  - `tests/fixtures/apu_linea_base.py` solo gana nombres; ningún valor existente cambia.
  - `tests/integration/test_composicion_extremo_a_extremo.py` no se edita.
  - Toda tarea que toca `core/` termina corriendo la línea base y el 7 de 7.
- **Contratos congelados** (CLAUDE.md §5): `git diff --stat main -- core/contracts` vacío durante todo C1. Si un cambio de contrato parece necesario, se detiene la tarea y se escribe el expediente (CLAUDE.md §9).
- **Ningún commit mezcla `core/` con `adapters/` o `ml/`.** Al cerrar C1, `git diff --stat main -- adapters ml` debe estar vacío.
- **Los llamadores en `ui/`, `api/` y `scripts/` cambian en commits separados** de los de `core/` (spec §4, hallazgos que cruzan capas).
- **Ninguna prueba escribe en `data/apu.db`.** Toda base de prueba vive en `tmp_path` o en memoria; la salvaguarda de la Tarea 1 lo hace cumplir.
- **Suite y lint.**
  - Suite verde con `uv run pytest -W error --strict-markers`, sin `filterwarnings` ni marcadores nuevos.
  - `uv run ruff check .` limpio; límite de línea de 100 caracteres (`pyproject.toml:36`).
  - CI verde en `ubuntu-latest` y `windows-latest`.
- **Commits** en Conventional Commits, en español y **sin tildes en el asunto**. Terminan con `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- **Alcance congelado** (spec §2): solo correcciones que cierran un hallazgo y apuntan a un RF, RNF, contrato o documento existente. Toda duda se registra en la bitácora y la decide Eugenio en GC1.
- **Regla de reparto** (spec §2): desde C1, por cada sesión de código hay al menos una de redacción (fase Red). Se anota en la bitácora, fuera de este plan.
- **Convención de los textos.** Docstrings y comentarios siguen la del archivo que se edita: con tildes en `core/` y en `tests/fixtures/`; sin tildes donde el archivo no las usa (`ui/`, `scripts/seed_demo.py`, cuerpos de commit).
- **Push y PR solo con permiso expreso de Eugenio.**

## Review Focus

1. **El veredicto `cumple` cambia en dos casos.**
   - INV‑012: una regla inevaluable pasa de ERROR a INFO, así que un presupuesto que antes daba NO CUMPLE solo por eso ahora CUMPLE.
   - INV‑013: un ítem pendiente es un ERROR `PENDIENTE`.
   - Se espera que la línea base (1 586,61) y el 7 de 7 no se muevan, y que la demostración siga imprimiendo `Auditoria: 3 hallazgo(s), CUMPLE`. Se comprueba en las Tareas 8, 11 y 14.
2. **`elaborar(plan=...)` acepta una secuencia o una función.**
   - El discriminante es `callable(plan)`.
   - Los cinco llamadores migrados deben producir exactamente lo mismo que antes: total de la API, libro de Excel, salida de `seed_demo.py` y `docs/resultados_ml.md` sin diferencias (Tarea 11).
3. **La salvaguarda tiene un límite conocido.** Compara existencia y `mtime_ns` al abrir y al cerrar la sesión. Una prueba que *cree y borre* `data/apu.db` dentro de la misma sesión, cuando no existía, no se detecta. OneDrive podría tocar el `mtime` de una base existente y dar un falso positivo. El revisor de pruebas debe ponderar ambos casos (Tarea 1).
4. **`descartar_version` borra en cascada.**
   - Deben desaparecer los renglones, la curva, los hallazgos y los `item_computo` de la versión descartada.
   - Deben conservarse `CambioPrecio`, `IncidenciaCambio` y la lista nueva, con `PRAGMA foreign_keys=ON`.
   - La versión anterior debe seguir reconstruyéndose (Tarea 13).
5. **El factor exacto de la tubería (INV‑009) cambia el esperado de R5.** Pasa de 7,8856 a 7,88542… m³. R5 debe seguir marcando el hallazgo 6 del 7 de 7, `test_r5_no_reporta_nada_si_el_balance_se_cumple` debe seguir dentro de tolerancia y ninguna otra prueba puede fijar el valor viejo (Tarea 5).

---

## Mapa de archivos

| Archivo | Tarea | Responsabilidad |
|---|---|---|
| `PLAN_CIERRE.md`, este documento, `docs/bitacora/2026-09-23-cierre.md` | 0, 14 | Enlace al plan; sección C1 y compuerta GC1 de la bitácora |
| `tests/conftest.py` | 1 | Salvaguarda de sesión de `data/apu.db` |
| `tests/unit/test_arquitectura.py`, `tests/unit/test_meta_asistente.py` | 1 | INV‑010: la guardia cubre `scripts` y `tests` |
| `docs/auditoria/2026-09-inventario.md` | 1, 3, 11, 12, 13, 14 | Revisión H2; filas nuevas; estados |
| `docs/guion_prueba_arenia.md`, `tests/unit/test_guion_prueba_arenia.py` (nuevo) | 2 | INV‑065 |
| `docs/bitacora/2026-09-23-C1-expedientes.md` (nuevo), `docs/tesis/revisiones/2026-09-paquete-tutor.md` | 3 | Expedientes; INV‑001, 002 y 006 al tutor |
| `pyproject.toml`, `tests/unit/test_costing.py`, `CLAUDE.md` | 4 | INV‑007 |
| `tests/fixtures/actualizacion_uc02.py` (nuevo), `tests/fixtures/computo_civil.py` (nuevo), `tests/fixtures/tarifas_sistemas.py`, `tests/fixtures/presupuesto_auditado.py` y sus consumidores | 5 | INV‑009 |
| `tests/fixtures/apu_linea_base.py` y los consumidores citados por INV‑008 | 6 | INV‑008 |
| `core/verification/expresiones.py`, `tests/unit/test_verification.py`, `tests/unit/test_budget.py` | 7 | INV‑003 |
| `core/verification/reglas.py`, `tests/unit/test_verification.py` | 8 | INV‑012 |
| `core/catalog/precios.py`, `core/budget/actualizacion.py`, `tests/unit/test_variacion_precio.py` (nuevo), `tests/integration/test_actualizacion_precios.py` | 9 | INV‑004 |
| `core/catalog/rendimientos.py`, `core/catalog/repositorio.py`, `tests/integration/test_rendimientos.py` | 10 | INV‑005 |
| `core/budget/presupuesto.py`, `core/budget/__init__.py`, `tests/unit/test_budget.py`; `ui/paginas/elaborar.py`, `ui/paginas/componer.py`; `api/rutas/presupuestos.py`; `scripts/seed_demo.py`, `scripts/generar_resultados_ml.py` | 11 | INV‑013 + INV‑069 (núcleo, y tres commits de llamadores) |
| `core/budget/diferencial.py` (nuevo), `core/budget/__init__.py`, `tests/unit/test_budget.py`, `tests/unit/test_reglas_civil.py`, `tests/unit/test_recalculo_uc04.py` (nuevo) | 12 | INV‑011 |
| `core/budget/actualizacion.py`, `core/budget/__init__.py`, `tests/integration/test_actualizacion_precios.py` | 13 | INV‑014 + INV‑015 |
| — | 14 | Compuerta GC1 |

---

### Task 0: Punto de partida

**Files:**
- Create: `docs/superpowers/plans/2026-09-23-cierre-c1-nucleo.md` (este documento)
- Modify: `PLAN_CIERRE.md:11`, `docs/bitacora/2026-09-23-cierre.md` (sección nueva al final)

**Interfaces:**
- Consumes: `main` en `384a7fa`, con el inventario aprobado en GC0.
- Produces: el recuento de pruebas de partida (`N0`), que citan las Tareas 1 y 14.

- [ ] **Step 1: Comprobar rama y base**

Run: `git rev-parse --abbrev-ref HEAD && git merge-base --is-ancestor main HEAD && echo base-ok && git log --oneline -1 && ls data/*.db 2>/dev/null || echo "sin bases locales"`
Expected: `inc/cierre-C1`, luego `base-ok`, luego `384a7fa merge: cierre fase c0 inventario y paquete para el tutor (#10)` y `sin bases locales`. En este worktree `data/apu.db` **no existe**, y la Tarea 1, paso 5 depende de ese dato.

- [ ] **Step 2: Estado de partida en verde**

Run: `uv sync --locked --all-extras && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: verde y ruff limpio. Anotar el número de pruebas (`N0`); en C0 fueron 690.

- [ ] **Step 3: Enlazar el plan.** En `PLAN_CIERRE.md`, reemplazar la línea 11
  (`- C1, C2, C4, Med, U2/U3: se planifican al cruzar la compuerta anterior, con el inventario ya aprobado.`)
  por:

```markdown
- C1: [docs/superpowers/plans/2026-09-23-cierre-c1-nucleo.md](docs/superpowers/plans/2026-09-23-cierre-c1-nucleo.md)
- C2, C4, Med, U2/U3: se planifican al cruzar la compuerta anterior, con el inventario ya aprobado.
```

- [ ] **Step 4: Abrir la sección de C1 en la bitácora.** Agregar al final de `docs/bitacora/2026-09-23-cierre.md`:

```markdown
## Fase C1 — núcleo

**Rama:** `inc/cierre-C1` (worktree `.claude/worktrees/cierre-C1`) · **Commit de partida:** `384a7fa`
(merge del PR #10) · **Plan ejecutable:**
[docs/superpowers/plans/2026-09-23-cierre-c1-nucleo.md](../superpowers/plans/2026-09-23-cierre-c1-nucleo.md).

**Estado de partida:** `uv run pytest -W error --strict-markers -q` → N0 pruebas, 0 fallos, 0
omitidas; `ruff check .` limpio.
```

(Sustituir `N0` por el número del paso 2.)

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-09-23-cierre-c1-nucleo.md PLAN_CIERRE.md docs/bitacora/2026-09-23-cierre.md
git commit -m "docs(plan): plan detallado de la fase c1 del cierre" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 1: Salvaguarda de `data/apu.db`, guardia de arquitectura (INV‑010) y revisión H2

**Files:**
- Modify: `tests/conftest.py` (archivo completo abajo)
- Modify: `tests/unit/test_arquitectura.py:1-8,17` y prueba nueva al final
- Modify: `tests/unit/test_meta_asistente.py:190-191`
- Modify: `docs/auditoria/2026-09-inventario.md` (§1, fila «Universo excluido» de `ci.yml`/`pyproject.toml`; filas nuevas si la revisión H2 halla algo)

**Interfaces:**
- Consumes: nada.
- Produces:
  - La fixture de sesión autouse `_base_real_intacta` y la constante `RUTA_BASE_REAL` en `tests/conftest.py`, que todas las tareas siguientes dan por activas.
  - `PAQUETES_FUERA_DEL_NUCLEO = ("adapters", "ml", "ui", "api", "scripts", "tests")`.

- [ ] **Step 1: Escribir la salvaguarda.** Es el código de la Tarea 6, paso 3, del plan de UI, que la spec §5 trae a C1. Reemplazar `tests/conftest.py` completo por:

```python
"""Fixtures compartidas de la suite.

Los datos viven en tests/fixtures/apu_linea_base.py (única copia, principio DRY).
"""

from pathlib import Path

import pytest

from tests.fixtures import apu_linea_base as linea_base

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


@pytest.fixture(scope="session")
def parametros_linea_base():
    return linea_base.PARAMETROS_LINEA_BASE


@pytest.fixture(scope="session")
def apus_linea_base():
    return linea_base.APUS_LINEA_BASE


@pytest.fixture(scope="session")
def presupuesto_auditado():
    return linea_base.PRESUPUESTO_AUDITADO


@pytest.fixture(scope="session")
def curva_auditada():
    return linea_base.CURVA_AUDITADA
```

- [ ] **Step 2: Ver la salvaguarda en rojo con una prueba desechable.** Crear `tests/unit/test_zz_salvaguarda_desechable.py`:

```python
from tests.conftest import RUTA_BASE_REAL


def test_escribe_en_la_base_real():
    RUTA_BASE_REAL.parent.mkdir(parents=True, exist_ok=True)
    RUTA_BASE_REAL.touch()
```

Run: `uv run pytest tests/unit/test_zz_salvaguarda_desechable.py -q -p no:cacheprovider`
Expected: `1 passed, 1 error`, con el mensaje «la suite modifico … data/apu.db (antes (False, None), despues (True, …))».

- [ ] **Step 3: Deshacer el experimento.** `data/apu.db` no existía (Tarea 0, paso 1), así que se borran los dos archivos.

Run: `rm tests/unit/test_zz_salvaguarda_desechable.py data/apu.db && git status --short`
Expected: solo aparece `M tests/conftest.py`.

- [ ] **Step 4: La suite completa pasa con la salvaguarda**

Run: `uv run pytest -W error --strict-markers -q`
Expected: verde, `N0` pruebas. **Si falla por la salvaguarda**, es un hallazgo real: una prueba existente escribe en `data/apu.db`.
- Se identifica bisecando por archivo (`uv run pytest <archivo> -q -p no:cacheprovider`).
- Se corrige esa prueba para que use `tmp_path`.
- Se registra como fila nueva del inventario, bloqueante según spec §4.
- Nunca se relaja la salvaguarda.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py
git commit -m "test: salvaguarda que falla la sesion si una prueba toca data/apu.db" -m "Tarea 6, paso 3, del plan de UI, movida al inicio de C1 por la spec de cierre (seccion 5). Observada en rojo con una prueba desechable y en verde con la suite completa." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: INV‑010, comprobar primero quién depende del literal.**
  - `scripts/meta_asistente.py:230-239` (`evaluar_guardia_arquitectura`) extrae la tupla con `re.search(r"PAQUETES_FUERA_DEL_NUCLEO\s*=\s*\(([^)]*)\)", texto)` y solo pregunta si contiene `"asistente"`.
  - `tests/unit/test_meta_asistente.py:189-195` prueba esa función con **sus propios literales**, no con el archivo real.
  - Consecuencia: ampliar la tupla no cambia ningún veredicto. M7 sigue en PENDIENTE mientras no exista `asistente/`, y la tupla debe seguir en una sola línea y entre paréntesis para que la expresión regular la lea.

Run: `grep -rn "PAQUETES_FUERA_DEL_NUCLEO" scripts tests`
Expected: exactamente `scripts/meta_asistente.py:234`, `:236`, `:238`, `:239`, `tests/unit/test_arquitectura.py:17`, `:57` y `tests/unit/test_meta_asistente.py:190`, `:191`.

- [ ] **Step 7: Escribir la prueba que falla.** Agregar al final de `tests/unit/test_arquitectura.py`:

```python
def test_la_guardia_cubre_todo_paquete_de_primer_nivel_fuera_del_nucleo():
    """INV-010: la tupla vigilada no puede olvidar un paquete del repositorio.

    Todo directorio de primer nivel con `__init__.py`, salvo `core`, es un paquete que el nucleo no
    puede importar (CLAUDE.md §2; spec de cierre §4, criterio D: `core/` no importa de `adapters/`,
    `ml/`, `ui/`, `api/` ni `scripts/`). `tests` entra porque tambien es importable
    (`tests/__init__.py`). Un paquete nuevo (p. ej. `asistente`) hace fallar esta prueba hasta
    que se agrega a la tupla.
    """
    paquetes = {inicio.parent.name for inicio in RAIZ.glob("*/__init__.py")} - {"core"}
    assert paquetes == set(PAQUETES_FUERA_DEL_NUCLEO)
```

Run: `uv run pytest tests/unit/test_arquitectura.py -q -W error --strict-markers`
Expected: `1 failed`: `AssertionError`, con «Extra items in the left set: 'scripts' 'tests'».

- [ ] **Step 8: Ampliar la tupla y el docstring.** En `tests/unit/test_arquitectura.py`, la línea 17 pasa a:

```python
PAQUETES_FUERA_DEL_NUCLEO = ("adapters", "ml", "ui", "api", "scripts", "tests")
```

y la línea 4 del docstring pasa a:

```python
- core/ no importa adapters, ml, ui, api, scripts ni tests (ningún paquete de primer nivel);
```

En `tests/unit/test_meta_asistente.py`, las líneas 190-191 pasan a (el literal de la prueba refleja la tupla vigente; el veredicto no cambia):

```python
    actual = 'PAQUETES_FUERA_DEL_NUCLEO = ("adapters", "ml", "ui", "api", "scripts", "tests")'
    ampliada = 'PAQUETES_FUERA_DEL_NUCLEO = ("adapters", "ml", "ui", "api", "scripts", "tests", "asistente")'
```

Si la segunda línea supera los 100 caracteres, partirla con concatenación implícita entre paréntesis, sin cambiar su contenido.

Run: `uv run pytest tests/unit/test_arquitectura.py tests/unit/test_meta_asistente.py -q -W error --strict-markers && uv run python scripts/meta_asistente.py`
Expected: verde. `meta_asistente.py` reporta M7 en PENDIENTE, igual que antes.

- [ ] **Step 9: Commit**

```bash
git add tests/unit/test_arquitectura.py tests/unit/test_meta_asistente.py
git commit -m "test(arquitectura): la guardia del nucleo cubre scripts y tests" -m "Cierra INV-010. La prueba nueva exige que la tupla coincida con los paquetes de primer nivel, de modo que un paquete nuevo no quede fuera sin que la suite lo diga." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 10: Revisión H2 de GC0, solo lectura, de `.github/workflows/ci.yml` y `pyproject.toml` por la capa `tests`.** Leer los dos archivos completos y contestar, con cita `archivo:línea`:
  - (a) ¿La CI ejecuta la suite con `-W error` y `--strict-markers`? `ci.yml` pasa `-W error` y `pyproject.toml:49` pone `--strict-markers` en `addopts`.
  - (b) ¿Algún marcador o `filterwarnings` relaja la suite? El marcador `rojo_esperado` de `pyproject.toml:50-52` ya es INV‑007, así que no se duplica.
  - (c) ¿La salvaguarda de la Tarea 1 corre en CI? Es autouse en `tests/conftest.py` y la CI no pasa `--noconftest`.
  - (d) ¿Se prohíben las pruebas omitidas? `scripts/verificar_omitidas.py` sobre el JUnit.
  - (e) ¿La cobertura medida (`--cov=core --cov=ml --cov=api --cov=adapters`) excluye `ui` y `scripts`? Si algún documento normativo afirma cobertura de esas capas, es un hallazgo.
  - (f) ¿Los dos sistemas operativos corren la misma suite?
  - (g) ¿`testpaths`, `pythonpath` y `known-first-party` son coherentes con los paquetes de la guardia del paso 8?

  Cada hallazgo es una fila nueva al final de §3 del inventario, con el siguiente ID libre (`grep -o "INV-0[0-9]*" docs/auditoria/2026-09-inventario.md | sort -u | tail -1`) y este formato:
  `| INV-0NN | revisión C1 (capa tests, H2 de GC0) | tests | <principio de spec §4> | <severidad por spec §4> | <archivo:línea> | <hallazgo> | <corrección propuesta> | <fase por su capa> | abierto |`.
  Después, en §1, reemplazar la fila `| .github/workflows/ci.yml, pyproject.toml | 2 | **Pendientes de revisión en C1 …** |` por:

```markdown
| `.github/workflows/ci.yml`, `pyproject.toml` | 2 | Revisados en C1 por la capa `tests` (Tarea 1, paso 10, del plan de C1); hallazgos: <IDs o «ninguno nuevo; el marcador `rojo_esperado` ya es INV‑007»> |
```

- [ ] **Step 11: Commit**

```bash
git add docs/auditoria/2026-09-inventario.md
git commit -m "docs(auditoria): revision de ci.yml y pyproject.toml por la capa tests" -m "Pendiente H2 de GC0." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: INV‑065, la preparación de CP‑01…CP‑06 sobre su propia base

**Files:**
- Create: `tests/unit/test_guion_prueba_arenia.py`
- Modify: `docs/guion_prueba_arenia.md:11`, `:42-44`, `:53-63`, `:75`, `:78`, `:101-102`, `:168`, `:176-179`, `:204-206`, `:242-243`, `:280-281`, `:328`, `:509`

**Interfaces:**
- Consumes: la salvaguarda (Tarea 1). La prueba protege el texto y la salvaguarda protege la suite.
- Produces: la corrección en cuatro partes de INV‑065, y una prueba que impide que la Tarea 12 de U1 (C3) vuelva a la ruta por defecto.

- [ ] **Step 1: Escribir la prueba que falla.** Crear `tests/unit/test_guion_prueba_arenia.py`:

```python
"""El guion manual no escribe en `data/apu.db` (INV‑065, bloqueante; spec de cierre §4).

Lee `docs/guion_prueba_arenia.md` como texto y comprueba tres cosas:

- toda orden de siembra lleva `--db` con una base propia;
- la preparación anota y comprueba la base de trabajo;
- la precondición de cada caso CP‑01…CP‑06 manda abrir la base de prueba en el campo
  **Archivo SQLite**, porque la aplicación vuelve a `data/apu.db` en cada recarga.

Cuando la Tarea 12 de U1 (fase C3) reescriba esas precondiciones podrá migrar la corrección a
`ARENIA_CASO`, que esta prueba también acepta, pero no volver en silencio a la ruta por defecto.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
GUION = RAIZ / "docs" / "guion_prueba_arenia.md"
BASE_DE_PRUEBA = "data/prueba_arenia.db"
BASE_DE_TRABAJO = "data/apu.db"
CASO_ABIERTO = "ARENIA_CASO"

#: Los encabezados de los casos usan el guion no separable U+2011 («### CP‑01 — …»).
_ENCABEZADO_DE_CASO = re.compile(r"^### CP\u2011(0[1-7]) ", re.MULTILINE)


def _texto() -> str:
    return GUION.read_text(encoding="utf-8")


def _seccion(texto: str, inicio: str, fin: str) -> str:
    desde = texto.index(inicio)
    return texto[desde : texto.index(fin, desde)]


def _casos() -> dict[str, str]:
    """Texto de cada caso, de su encabezado al del caso siguiente (CP‑07 cierra a CP‑06)."""
    texto = _texto()
    marcas = list(_ENCABEZADO_DE_CASO.finditer(texto))
    return {
        f"CP-{marca.group(1)}": texto[marca.start() : siguiente.start()]
        for marca, siguiente in zip(marcas, marcas[1:], strict=False)
    }


def test_toda_orden_de_siembra_lleva_su_propia_base():
    ordenes = [
        linea.strip()
        for linea in _texto().splitlines()
        if "uv run python scripts/seed_demo.py" in linea
    ]
    assert ordenes, "el guion debe sembrar con scripts/seed_demo.py"
    sin_base = [orden for orden in ordenes if "--db" not in orden]
    assert not sin_base, f"sin --db apuntan a {BASE_DE_TRABAJO}: {sin_base}"
    assert not [orden for orden in ordenes if f"--db {BASE_DE_TRABAJO}" in orden]


def test_la_preparacion_anota_y_comprueba_la_base_de_trabajo():
    texto = _texto()
    preparacion = _seccion(texto, "## 4. Entorno y preparación", "## 5.")
    registro = _seccion(texto, "## 8. Registro de la ejecución", "## 9.")
    assert "**Antes de empezar" in preparacion
    assert "**Al terminar la prueba.**" in preparacion
    assert f"`{BASE_DE_TRABAJO}` al empezar" in registro
    assert f"`{BASE_DE_TRABAJO}` sin cambios al terminar" in registro


@pytest.mark.parametrize("caso", ["CP-01", "CP-02", "CP-03", "CP-04", "CP-05", "CP-06"])
def test_la_precondicion_de_cada_caso_abre_la_base_de_prueba(caso):
    precondicion = _seccion(_casos()[caso], "**Precondición:**", "**Pasos**")
    assert BASE_DE_PRUEBA in precondicion or CASO_ABIERTO in precondicion, (
        f"{caso}: la precondicion no abre {BASE_DE_PRUEBA}; la aplicacion volveria a "
        f"{BASE_DE_TRABAJO} (INV-065)"
    )


def test_la_segunda_pestana_de_cp02_tambien_abre_la_base_de_prueba():
    """La pestaña nueva empieza en la ruta por defecto: el paso 6 de CP‑02 la corrige."""
    pasos = _seccion(_casos()["CP-02"], "**Pasos**", "**Resultado esperado**")
    assert BASE_DE_PRUEBA in pasos or CASO_ABIERTO in pasos
```

Run: `uv run pytest tests/unit/test_guion_prueba_arenia.py -q -W error --strict-markers`
Expected: `9 failed`. Fallan la siembra (línea 57 sin `--db`), la preparación, las seis precondiciones y la segunda pestaña.

- [ ] **Step 2: Parte (c), anotar antes de empezar.** Reemplazar el bloque citado `docs/guion_prueba_arenia.md:42-44` (desde `> **Atención: `--reiniciar` borra la base de datos**` hasta `(paso 2b).`) por:

```markdown
> **Esta prueba trabaja sobre su propia base, `data/prueba_arenia.db`, y nunca sobre
> `data/apu.db`**, la base de trabajo de la aplicación. La siembra con `--reiniciar` borra la base
> que se le indica antes de volver a sembrarla: por eso toda orden de este guion lleva
> `--db data/prueba_arenia.db`, y cada caso le recuerda escribir esa base en la barra lateral.

**Antes de empezar (protección de la base de trabajo).** Anote en la sección 8 si existe
`data/apu.db` y, si existe, su fecha y hora de modificación. En PowerShell:
`Get-Item data/apu.db | Select-Object LastWriteTime`; en bash: `ls -l --time-style=full-iso data/apu.db`.
Si no existe, anote «no existe».
```

- [ ] **Step 3: Parte (a), sembrar en la base propia.** Reemplazar el paso 2 completo (`:53-63`, desde `2. Siembre la base de prueba` hasta `cada vez que la página se recarga.`, variante 2b incluida) por el bloque siguiente. El párrafo **Comprobación de la preparación** (`:65-67`) queda igual.

````markdown
2. Siembre la base de prueba (línea base de la clínica, las tres partidas de demostración y el
   presupuesto de ejemplo `DEMO-001`) en su propio archivo:

   ```
   uv run python scripts/seed_demo.py --db data/prueba_arenia.db --reiniciar
   ```

   `--reiniciar` borra `data/prueba_arenia.db` antes de sembrarla, de modo que cada repetición
   empieza de la misma base. **No ejecute nunca la orden sin `--db`:** sin esa opción apunta a
   `data/apu.db`.
````

- [ ] **Step 4: Parte (b) en la apertura.** Tras la frase de `:75` (`Se abre el navegador. En el menú lateral, elija **Componer partida (UC-10 / UC-11)**.`), agregar dentro del mismo paso 3:

```markdown
   En la barra lateral, escriba `data/prueba_arenia.db` en el campo **Archivo SQLite** y pulse
   Enter. **El campo vuelve a `data/apu.db` cada vez que se recarga la página (F5) o se abre otra
   pestaña**: cada caso le indica cuándo escribirlo de nuevo.
```

- [ ] **Step 5: Parte (d), comprobar al terminar.** Tras el párrafo **Orden de ejecución** (`:77-78`), agregar:

```markdown

**Al terminar la prueba.** Repita la comprobación de «Antes de empezar» y anótela en la sección 8:
`data/apu.db` debe seguir igual que al empezar (o seguir sin existir). Si cambió, la ejecución es
**FALLA** aunque todos los casos hayan pasado: la prueba tocó la base de trabajo.
```

- [ ] **Step 6: Parte (b) en cada precondición.** Reemplazar cada precondición por el texto siguiente.

CP‑01 (`:101-102`):

```markdown
- **Precondición:** base recién sembrada (sección 4) y la página *Componer partida* abierta, con las
  tablas vacías y `data/prueba_arenia.db` escrita en el campo **Archivo SQLite** de la barra lateral.
```

CP‑02 (`:168`):

```markdown
- **Precondición:** CP‑01 terminado con PASA, en la misma pestaña y sin recargar la página: el campo
  **Archivo SQLite** sigue diciendo `data/prueba_arenia.db`.
```

CP‑02, paso 6 (`:176-179`):

```markdown
6. Abra una **segunda pestaña** del navegador con la misma dirección de la aplicación y, en ella,
   elija **Catalogo** en el menú lateral. En la barra lateral de esa pestaña escriba
   `data/prueba_arenia.db` en el campo **Archivo SQLite** y pulse Enter (la pestaña nueva empieza en
   `data/apu.db`). Observe la tabla **Partidas**. Cierre esa pestaña y vuelva a la primera.
```

CP‑03 (`:204-206`):

```markdown
- **Precondición:** CP‑02 terminado, en la misma pestaña: la partida `PRUEBA-01-TUB` en pantalla con
  rendimiento `120` y **Precio unitario** `19.99073793585000000000000000`, y el campo **Archivo
  SQLite** en `data/prueba_arenia.db`. Si el rendimiento no está en `120`, escríbalo.
```

CP‑04 (`:242-243`):

```markdown
- **Precondición:** base sembrada (la partida `DEMO-01-INST` trae dos observaciones de rendimiento:
  50 y 60 m por día). Recargue la página con **F5** para empezar con las tablas vacías y escriba de
  nuevo `data/prueba_arenia.db` en el campo **Archivo SQLite** (la recarga lo devolvió a
  `data/apu.db`).
```

CP‑05 (`:280-281`):

```markdown
- **Precondición:** base sembrada y CP‑04 terminado **sin guardar**. Recargue la página con **F5** y
  escriba de nuevo `data/prueba_arenia.db` en el campo **Archivo SQLite**. Excel o LibreOffice Calc
  para abrir el libro.
```

CP‑06 (`:328`):

```markdown
- **Precondición:** CP‑05 terminado, en la misma pestaña y con `data/prueba_arenia.db` en el campo
  **Archivo SQLite**.
```

- [ ] **Step 7: Registro y versión.** En la tabla de §8, tras la fila `| Comprobación de la preparación (sección 4, paso 2) | |` (`:509`), agregar:

```markdown
| `data/apu.db` al empezar (existe · fecha de modificación) | |
| `data/apu.db` sin cambios al terminar (sí/no) | |
```

En `:11`, la viñeta del identificador pasa a:

```markdown
- **Identificador:** GP‑ARENIA‑001, versión de la Sesión P4.2 (2026‑09‑21), corregida en la fase C1
  del cierre (INV‑065: la prueba trabaja sobre su propia base, nunca sobre `data/apu.db`).
```

- [ ] **Step 8: Verde, y ninguna referencia colgante a la variante 2b**

Run: `uv run pytest tests/unit/test_guion_prueba_arenia.py -q -W error --strict-markers && grep -n "2b" docs/guion_prueba_arenia.md`
Expected: `9 passed`. El `grep` no devuelve nada; si devuelve alguna línea, esa referencia a la variante eliminada se reescribe citando el paso 2.

- [ ] **Step 9: Commit**

```bash
git add docs/guion_prueba_arenia.md tests/unit/test_guion_prueba_arenia.py
git commit -m "docs(guion): cp-01 a cp-06 trabajan sobre su propia base" -m "Cierra INV-065 (bloqueante) con sus cuatro partes: siembra con --db data/prueba_arenia.db, precondicion de cada caso con el campo Archivo SQLite (y tras cada F5), y comprobacion de data/apu.db antes y despues. La prueba nueva impide que la Tarea 12 de U1 vuelva a la ruta por defecto." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Expedientes: INV‑001, INV‑002 e INV‑006 al tutor, y expedientes previos del núcleo

**Files:**
- Create: `docs/bitacora/2026-09-23-C1-expedientes.md`
- Modify: `docs/auditoria/2026-09-inventario.md` (columna «Estado» de las filas INV‑001, INV‑002 e INV‑006)
- Modify: `docs/tesis/revisiones/2026-09-paquete-tutor.md` (tres filas tras la fila `UC‑09/RF‑44` de «Puntos a decidir» y tres filas en «Modelo de constancia»)

**Interfaces:**
- Consumes: spec §4 (estado *aceptado por decisión de arquitectura registrada*, exclusivo de contratos sin aval) y §5 (C1: «cada uno con expediente previo en `docs/bitacora/`»).
- Produces:
  - Los expedientes A.1 a A.3 (contratos) y B.1 a B.8 (hallazgos de `core/` sin cambio de contrato), escritos **antes** del código de las Tareas 7 a 13.
  - Tres puntos nuevos en el paquete del tutor.

La tarea va aquí, y no al final, porque la respuesta del tutor es el camino crítico de F2 (spec §7).

- [ ] **Step 1: Ningún contrato cambió ni cambiará en C1**

Run: `git diff --stat main -- core/contracts`
Expected: vacío.

- [ ] **Step 2: Crear `docs/bitacora/2026-09-23-C1-expedientes.md`** con este contenido exacto:

````markdown
# Expedientes de la fase C1 del cierre (núcleo)

**Fecha:** 2026‑09‑23 · **Rama:** `inc/cierre-C1` · **Inventario:**
[docs/auditoria/2026-09-inventario.md](../auditoria/2026-09-inventario.md) · **Spec:**
[§4 y §5](../superpowers/specs/2026-09-23-plan-cierre-tesis-design.md) · **Paquete para el tutor:**
[docs/tesis/revisiones/2026-09-paquete-tutor.md](../tesis/revisiones/2026-09-paquete-tutor.md).

La spec (§5, fila C1) exige un expediente previo por cada hallazgo de `core/`, y (§4) que la
corrección que cambia un contrato de `core/contracts/` espere el aval del tutor. La sección A
reúne los tres hallazgos que cambian contratos: quedan **aceptados por decisión de arquitectura
registrada (pendiente del aval del tutor)**, el único caso en que ese estado es válido. Si el aval
llega antes de `v1.0-tesis`, el hallazgo vuelve a quedar abierto y se corrige; si se niega, se
declara en el capítulo de limitaciones con este expediente. La sección B reúne los hallazgos de
`core/` que C1 cierra sin tocar contratos; cada entrada se escribió antes de su código y enumera
la decisión que Eugenio ratifica en GC1.

## A. Hallazgos cuyo cierre exige cambiar un contrato

### A.1 INV-001: los enumerados de `Rendimiento` e `ItemComputo` no se convierten

**Problema.** `Rendimiento.__post_init__` (`core/contracts/apu.py:193`) e
`ItemComputo.__post_init__` (`core/contracts/item_computo.py:54`) comparan el enumerado con `is`
sin convertir la entrada. Con la cadena en lugar del miembro (`tipo="medido"`,
`origen_tipo="regla"`) se saltan sus invariantes: un rendimiento MEDIDO sin
`referencia_ejecucion` y un ítem REGLA sin `regla`. `dominio` tampoco se convierte. El contrato
vecino ya lo hace bien: `LineaManoObra` convierte `modalidad` (`core/contracts/apu.py:99`).

**Evidencia.** Reproducido en el registro de la Tarea 5 de C0 (inventario §5). Ningún llamador
actual de `adapters/`, `ml/`, `api/`, `ui/` ni `scripts/` pasa cadenas (dictamen R6): el riesgo es
latente, no hay dato corrompido.

**Cambio de contrato propuesto.**

```python
# core/contracts/apu.py, primera línea de Rendimiento.__post_init__:
object.__setattr__(self, "tipo", TipoRendimiento(self.tipo))

# core/contracts/item_computo.py, en ItemComputo.__post_init__, antes de la comprobación de REGLA:
object.__setattr__(self, "origen_tipo", OrigenTipo(self.origen_tipo))
object.__setattr__(self, "dominio", Dominio(self.dominio))
```

Es retrocompatible: un miembro del enumerado pasa sin cambio (`StrEnum(miembro) is miembro`) y una
cadena válida se convierte. Una cadena inválida ahora lanza `ValueError`, cuando antes pasaba sin
aviso. Se acompaña de cuatro casos en `tests/unit/test_contracts.py` (cadena válida convertida y
cadena que salta la invariante, para cada contrato).

| Alternativa | Por qué no |
|---|---|
| Validar en cada frontera (API, adaptadores, UI) | Repite la regla en cada capa (DRY) y deja al contrato sin proteger su propia invariante (CLAUDE.md §5) |
| `isinstance` estricto con `TypeError` | Más estricto que el precedente de `LineaManoObra`; rompe a un llamador que envíe texto de un JSON o CSV |
| No cambiar y declarar la limitación | Es el estado mientras no llegue el aval |

**Costo de hacerlo:** seis líneas en dos contratos «estables» (CLAUDE.md §5), más las pruebas. La
línea base no cambia porque sus datos usan miembros.

**Costo de no hacerlo:** un llamador futuro que construya contratos desde texto (la API recibe
JSON) podría crear un rendimiento MEDIDO sin ejecución, lo que rompe RF‑25, o un ítem REGLA sin
expresión, lo que rompe la trazabilidad de R1. Queda declarado en limitaciones.

**Paquete para el tutor:** punto `INV‑001`.

### A.2 INV-002: montos y parámetros de los contratos no exigen `Decimal` ni signo

**Problema.** No exigen `Decimal` ni signo:

- `ItemComputo.parametros` (`core/contracts/item_computo.py:42,57`);
- los seis montos de `ResultadoAPU` (`core/contracts/apu.py:161-170`);
- `PuntoCurva.monto` y `acumulado` (`core/contracts/presupuesto.py:33-39`);
- `Hallazgo.impacto`, `valor_observado` y `valor_esperado` (`core/contracts/verificacion.py:28-38`).

Aceptan `1.5`, `-2.0` y `0.1` (comprobado en C0).

**Evidencia.** No se detectó uso real de `float` (R6): falta la validación, no hay dato corrompido.
La consecuencia más grave, que un `float` en `parametros` abortara el informe, la cierra C1 **sin
contrato** en INV‑003: el evaluador rechaza lo que no es `Decimal` (expediente B.1).

**Cambio de contrato propuesto.**

```python
# ItemComputo.__post_init__, antes de congelar `parametros`:
for nombre, valor in self.parametros.items():
    if not isinstance(valor, Decimal):
        raise TypeError(f"parametros[{nombre!r}] debe ser Decimal, no {type(valor).__name__}")

# ResultadoAPU (nuevo __post_init__):
def __post_init__(self) -> None:
    for nombre in ("materiales", "equipos", "mano_obra", "costo_directo",
                   "con_administracion", "precio_unitario"):
        _no_negativo(nombre, getattr(self, nombre))

# PuntoCurva (nuevo __post_init__):
def __post_init__(self) -> None:
    _no_negativo("monto", self.monto)
    _no_negativo("acumulado", self.acumulado)

# Hallazgo.__post_init__: tipo sin signo, porque R5 y R7 producen negativos por diseño
# (core/verification/reglas.py:419, 431-444, 623-626):
for nombre in ("impacto", "valor_observado", "valor_esperado"):
    valor = getattr(self, nombre)
    if valor is not None:
        _exigir_decimal(nombre, valor)
```

`_exigir_decimal` y `_no_negativo` viven hoy en `core/contracts/apu.py:13-23`. Para que
`presupuesto.py`, `verificacion.py` e `item_computo.py` los usen sin importar privados de un
módulo hermano se propone moverlos a `core/contracts/_validacion.py`.

Antes de aplicar, dos comprobaciones. Primero, que `core/budget/curva.generar_curva` con
`cuantizar` no pueda dejar el último período en negativo: su monto es el total menos lo repartido,
y el redondeo hacia arriba de los anteriores podría excederlo. Segundo, que una prueba de R5 con
balance negativo siga produciendo el informe (prueba de aceptación del inventario).

| Alternativa | Por qué no |
|---|---|
| Validar solo en las fronteras (adaptadores, API) | Los contratos son la única forma que cruza paquetes; validar afuera repite la regla |
| `_no_negativo` también en `Hallazgo` | Rompe R5 y R7, que informan desviaciones negativas por diseño (dictamen R7 de GC0) |

**Costo de hacerlo:** cuatro contratos «estables» cambian, más el módulo de validación compartido
y las pruebas. Existe el riesgo del último período negativo, a comprobar antes.

**Costo de no hacerlo:** un `float` o un monto negativo pueden cruzar fronteras sin aviso (principio
3). El camino que más dañaba, la aritmética de R1 y R5, ya queda cerrado por INV‑003. Queda
declarado en limitaciones.

**Paquete para el tutor:** punto `INV‑002`.

### A.3 INV-006: el evaluador de expresiones en cinco copias

**Problema.** El evaluador aritmético de expresiones trazables existe cinco veces:
`core/verification/expresiones.py` (159 líneas) y `adapters/{civil,industrial,sistemas,telecom}/evaluador.py`
(74, 79, 60 y 66 líneas). Las copias civil e industrial son idénticas salvo el docstring. Es deuda
declarada: la ADR 8 y §6.1 de `docs/arquitectura.md:930,944` declaran dos copias, y las bitácoras de
I5 las otras tres. La propia ADR 8 prevé su cierre en `core.contracts.expresiones`.

**Evidencia.** Inventario §3, filas INV‑006 e INV‑058. Hay un costo nuevo y concreto: la corrección
de INV‑003 en C1 (rechazar lo que no es `Decimal`) solo llega a la copia del núcleo, y las cuatro de
los adaptadores siguen lanzando `TypeError` con un `float`.

**Cambio de contrato propuesto.** Un módulo nuevo `core/contracts/expresiones.py`, el único que los
adaptadores pueden importar (CLAUDE.md §2):

```python
OPERADORES_ARITMETICOS: frozenset[type[ast.operator]] = frozenset(
    {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow}
)

class ExpresionInvalida(ValueError): ...
class ParametroFaltante(KeyError): ...

def evaluar(
    expresion: str,
    valores: Mapping[str, Decimal],
    operadores: frozenset[type[ast.operator]] = OPERADORES_ARITMETICOS,
    unarios: bool = True,
) -> Decimal: ...
```

`core/verification/expresiones.py` conserva `codigos_de`, `sustituir_codigos` y `nombres_de`, y
delega `evaluar`. En la **subtarea de C2**, que depende del aval, los cuatro adaptadores importan
`core.contracts.expresiones.evaluar` con sus subconjuntos: sistemas `{Add, Mult}`, telecom
`{Add, Sub, Mult, Div}`, civil e industrial los cinco. El módulo nuevo agrega una fila a la tabla de
CLAUDE.md §5.

| Alternativa | Por qué no |
|---|---|
| Mantener las cinco copias con pruebas de equivalencia | Es el precio declarado hoy (ADR 8); cada corrección se aplica cinco veces |
| Módulo compartido dentro de `adapters/` | Rompe la autonomía de los adaptadores (dictamen R5 de GC0; `tests/unit/test_adapter_telecom.py:154-170`) |
| Que los adaptadores importen `core.verification` | Viola la regla «los adaptadores solo importan `core.contracts`» y la hipótesis central |

**Costo de hacerlo:** un contrato nuevo de unas 100 líneas. En C2 se migran cuatro adaptadores
(unas 280 líneas menos) conservando los subconjuntos reducidos. Tienen que seguir pasando
`test_arquitectura.py` y las pruebas de adaptadores.

**Costo de no hacerlo:** cinco copias declaradas en el capítulo de limitaciones; INV‑058 (C4)
documenta cinco y no dos; toda corrección del evaluador, como INV‑003, queda parcial.

**Paquete para el tutor:** punto `INV‑006`.

## B. Expedientes previos de los hallazgos de `core/` que no cambian contratos

### B.1 INV-003: un `float` en `parametros` aborta el informe

**Corrección.** `core/verification/expresiones._evaluar_nodo` rechaza con `ExpresionInvalida` todo
parámetro que no sea `Decimal`. R1 y R5 ya convierten esa excepción en hallazgo.

**Alternativa descartada.** Capturar `TypeError` en `_evaluar_binario`, que es la redacción literal
del inventario. No cubre la expresión de un solo nombre (`"longitud"`), donde el `TypeError` aparece
después, al comparar con la cantidad (`reglas.py:151`). Con la validación en el nodo, ese
`TypeError` es inalcanzable y no se agrega un `except` muerto.

**Línea base y 7 de 7:** no cambian; sus parámetros son `Decimal`.

**Ratificar:** la desviación de la redacción literal.

### B.2 INV-012: regla no evaluable, INFO y no ERROR; R7 no aplicable sin plan

**Corrección.** Manda la ERS: RF‑23 y UC‑05 3a piden INFO «regla no evaluable», y UC‑05 2a pide
declarar R7 no aplicable sin plan. R1 y R5 pasan de ERROR a INFO con el texto «regla no
evaluable», y R7 sin curva emite INFO «R7 no aplicable». Regla y prueba cambian en el mismo commit;
la ERS no cambia.

**Alternativa descartada.** Cambiar la ERS a ERROR. Sería modificar un requisito esencial para
ajustarlo al código.

**Efecto.** Un presupuesto que era NO CUMPLE *solo* por una regla inevaluable pasa a CUMPLE. El
presupuesto del 7 de 7 tiene curva y todas sus reglas son evaluables, así que no cambia; se
comprueba en la Tarea 8.

**Ratificar:** la severidad INFO y su efecto sobre `cumple`.

### B.3 INV-004: dos fórmulas de variación que difieren con base nula

**Corrección.** Una sola función, `core.catalog.precios.variacion_relativa`, que importan
`CambioDetectado.variacion` y `core/budget/actualizacion.py`. Política declarada: con precio
anterior 0 devuelve 0, y el registro conserva `precio_anterior = 0`, que distingue ese caso de «no
cambió».

**Alternativa descartada.** Devolver `None`. La columna `variacion` no es nula
(`docs/modelo_datos.md:147`) y cambiar el esquema es una migración, fuera del límite (spec §2).

**Ratificar:** la política de base nula.

### B.4 INV-005: dos registros de rendimiento

**Corrección.** `core.catalog.rendimientos.registrar_rendimiento` construye el contrato y delega en
`Catalogo.registrar_rendimiento` y en `a_rendimiento`. La excepción única ante una ejecución
inexistente es `LookupError`, con el mensaje que orienta al usuario.

**Alternativa descartada.** Unificar en `CatalogoIncompleto`. La API la traduce a 409
(`api/main.py:26-29`) y hoy responde 404 (`tests/integration/test_api_rendimientos.py:77`); una
ejecución que no existe es un recurso ausente, no un catálogo incompleto.

**Ratificar:** que la excepción única sea `LookupError`.

### B.5 INV-013: UC‑01 3a sin cambio de contrato

**Corrección, ruta sin contrato.** `elaborar` separa los ítems cuya partida no tiene composición: no
entran al presupuesto ni al total, van en `ResultadoElaboracion.pendientes` (el tipo es de
`core/budget/`, no un contrato) y el informe los declara con un `Hallazgo` del contrato vigente, de
código `PENDIENTE` y severidad ERROR. `Presupuesto` no cambia (`core/contracts/presupuesto.py:41-46`).
`generar_presupuesto` sigue exigiendo composición: es el paso intermedio (INV‑037, a limitaciones).

**Fuera de C1.** La propuesta de las tres partidas similares (UC‑03) es de `ui/`. La interfaz y la
API piden hoy las composiciones al catálogo, que lanza `KeyError` ante una partida desconocida, así
que 3a no se alcanza de punta a punta: se registra como hallazgo nuevo para C2 y C3.

**Ratificar:** el código `PENDIENTE` con severidad ERROR (un presupuesto incompleto no cumple).

### B.6 INV-069: el protocolo de elaboración en cuatro sitios

**Corrección.** `elaborar` acepta en `plan` una secuencia o una función del presupuesto valorado
(`plan=plan_secuencial`), y absorbe el borrador. Los llamadores migran en commits separados:
`ui/paginas/elaborar.py`, `ui/paginas/componer.py`, `api/rutas/presupuestos.py`,
`scripts/seed_demo.py` y un quinto sitio que el inventario no citaba,
`scripts/generar_resultados_ml.py:158-167`.

**Alternativa descartada.** Una función nueva `elaborar_con_plan_secuencial`: sería un segundo punto
de entrada para el mismo hecho.

**Ratificar:** que el punto único sea `elaborar` con `plan` invocable, y la inclusión del quinto
llamador.

### B.7 INV-011: RF‑20 sin implementación

**Hallazgo al planificar.** RF‑19 tiene capacidad (las reglas paramétricas de `adapters/civil/reglas.py`
se reevalúan) y solo le falta la prueba. RF‑20 **no tiene implementación**: `_comparar`
(`core/budget/actualizacion.py:267-303`) es privado, supone los mismos renglones y no da el
diferencial de cantidad.

**Corrección.** Módulo nuevo `core/budget/diferencial.py` (`diferencial_por_partida`), que
implementa el RF existente. Por la spec §2 es corrección, no capacidad nueva.

**Fuera de C1.** Los flujos alternativos 1a, 2a y 2b de UC‑04 viven en la capa de adaptadores (o no
existen). Se registran como hallazgo nuevo para C2 y C4.

**Ratificar:** implementar RF‑20 en C1.

### B.8 INV-015: UC‑02 7a

**Hallazgo al planificar.** «Descartar» hoy es no confirmar la transacción. Eso también deshace los
`CambioPrecio`, contra 7a («el registro de cambios se conserva»).

**Corrección.** `core.budget.descartar_version` borra la versión nueva (renglones, curva, hallazgos
y sus `item_computo`) y conserva la lista, `CambioPrecio` e `IncidenciaCambio`.

**Fuera de C1.** «Se marca como descartada» exige una columna nueva en `presupuesto`, es decir, una
migración, fuera del límite (spec §2). La interfaz no ofrece hoy descartar. Ambas cosas se
registran como hallazgo nuevo para C3 y C4.

**Ratificar:** borrar en vez de marcar.
````

- [ ] **Step 3: Estado en el inventario.** En `docs/auditoria/2026-09-inventario.md`, en las filas que empiezan con `| INV-001 |` y `| INV-002 |`, reemplazar la cola `| C1 | abierto |` por:

```markdown
| C1 | aceptado por decisión de arquitectura registrada (pendiente del aval del tutor; [expediente](../bitacora/2026-09-23-C1-expedientes.md), §A) |
```

En la fila `| INV-006 |`, reemplazar la cola `| C1 (contrato) + C2 (adaptadores) | abierto |` por:

```markdown
| C1 (contrato) + C2 (adaptadores) | aceptado por decisión de arquitectura registrada (pendiente del aval del tutor; [expediente](../bitacora/2026-09-23-C1-expedientes.md), §A.3); la subtarea de C2 queda aceptada con él mientras no haya aval |
```

- [ ] **Step 4: Paquete para el tutor.** En `docs/tesis/revisiones/2026-09-paquete-tutor.md`, agregar tras la fila `| **UC‑09/RF‑44** | … |` de «Puntos a decidir»:

```markdown
| **INV‑001** | ¿Avala que `Rendimiento` e `ItemComputo` conviertan en `__post_init__` sus campos enumerados (`TipoRendimiento`, `OrigenTipo`, `Dominio`), como ya hace `LineaManoObra` con `ModalidadManoObra`? | avalar el cambio de contrato · no avalarlo | avalar: es retrocompatible y cierra un salto latente de invariantes | [expediente A.1](../../bitacora/2026-09-23-C1-expedientes.md) | C1 (se corrige si el aval llega antes de `v1.0-tesis`) | queda **aceptado por decisión de arquitectura registrada** y se declara en el capítulo de limitaciones; no bloquea F3 |
| **INV‑002** | ¿Avala que los contratos exijan `Decimal` en `ItemComputo.parametros`, `ResultadoAPU`, `PuntoCurva` y los campos numéricos de `Hallazgo`, y no negativos en los montos de `ResultadoAPU` y `PuntoCurva`? | avalar el cambio de contrato · no avalarlo | avalar: el principio 3 queda protegido por el propio contrato | [expediente A.2](../../bitacora/2026-09-23-C1-expedientes.md) | C1 | queda **aceptado por decisión de arquitectura registrada**; el camino que abortaba el informe ya lo cierra INV‑003 sin contrato |
| **INV‑006** | ¿Avala un evaluador de expresiones único en `core.contracts.expresiones`, con los operadores permitidos como argumento, para eliminar las cinco copias (núcleo y cuatro adaptadores) que prevé la ADR 8? | avalar el contrato nuevo y la migración de los adaptadores en C2 · no avalarlo | avalar: cierra una deuda declarada y hace que una corrección del evaluador valga para todos los dominios | [expediente A.3](../../bitacora/2026-09-23-C1-expedientes.md) | C1 (contrato) y C2 (adaptadores) | queda **aceptado por decisión de arquitectura registrada** junto con su subtarea de C2; las cinco copias se declaran en limitaciones |
```

y en «Modelo de constancia», tras `| UC‑09 desde RF‑44 | | | |`:

```markdown
| INV‑001 (enumerados de los contratos) | | | |
| INV‑002 (`Decimal` y signo en los contratos) | | | |
| INV‑006 (evaluador único en `core.contracts`) | | | |
```

- [ ] **Step 5: Commit**

```bash
git add docs/bitacora/2026-09-23-C1-expedientes.md docs/auditoria/2026-09-inventario.md docs/tesis/revisiones/2026-09-paquete-tutor.md
git commit -m "docs(bitacora): expedientes de c1 y contratos pendientes del tutor" -m "INV-001, INV-002 e INV-006 quedan aceptados por decision de arquitectura registrada, pendientes del aval del tutor (spec seccion 4). Expedientes previos de los hallazgos de core sin cambio de contrato (spec seccion 5, fila C1)." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: INV‑007, retirar el marcador `rojo_esperado`

**Files:**
- Modify: `pyproject.toml:50-52`, `tests/unit/test_costing.py:1-10,20`, `CLAUDE.md:238-239`

**Interfaces:**
- Consumes: nada.
- Produces: una suite sin marcadores declarados. CLAUDE.md §9 queda sin el «estado esperado» previo a I0.3, lo que cierra también esa parte de INV‑055.

- [ ] **Step 1: Retirar el marcador de la configuración.** En `pyproject.toml`, borrar las líneas 50-52 (`markers = [` … `]`). `addopts = "-q --strict-markers"` queda igual.

- [ ] **Step 2: Rojo: `--strict-markers` rechaza el marcador huérfano**

Run: `uv run pytest tests/unit/test_costing.py -q`
Expected: `1 error`, con `'rojo_esperado' not found in `markers` configuration option`.

- [ ] **Step 3: Actualizar la prueba sin tocar ninguna aserción.** En `tests/unit/test_costing.py`, reemplazar el docstring de módulo (`:1-10`) por:

```python
"""Pruebas del motor de costos contra los cinco APU de la línea base (Sesiones I0.2 e I0.3).

Se escribieron antes que el motor (CLAUDE.md §2, principio 5): la línea base verificada existía
antes que `core.costing`, y el motor se escribió para pasarlas sin modificarlas. Están en verde
desde la Sesión I0.3 y siguen sin modificarse para ponerlas en verde (CLAUDE.md §9).

Contrato del motor:
    calcular_apu(composicion: ComposicionAPU, parametros: ParametrosCosto) -> ResultadoAPU
"""
```

y borrar la línea 20 (`pytestmark = pytest.mark.rojo_esperado`) y la línea en blanco que la sigue. `import pytest` se queda: `:34` lo usa en `parametrize`.

- [ ] **Step 4: Verde, sin rastro del marcador en código ni configuración**

Run: `uv run pytest tests/unit/test_costing.py -q -W error --strict-markers && grep -rn "rojo_esperado" --include=*.py --include=*.toml core adapters ml api ui scripts tests pyproject.toml`
Expected: `7 passed`, y el `grep` no devuelve nada.

- [ ] **Step 5: Commit de pruebas y configuración**

```bash
git add pyproject.toml tests/unit/test_costing.py
git commit -m "test(costing): retira el marcador rojo_esperado" -m "Cierra INV-007 en codigo: las siete pruebas pasan desde I0.3; ninguna asercion cambia (CLAUDE.md seccion 9)." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: CLAUDE.md §9.** Reemplazar las líneas 238-239 (`- Estado esperado de la suite hasta I0.3: … Es correcto y deliberado.`) por:

```markdown
- Estado esperado de la suite: todo verde con `uv run pytest -W error --strict-markers`. Desde la
  Sesión I0.3 ninguna prueba está roja a propósito; el marcador `rojo_esperado` se retiró en C1 del
  cierre (INV‑007).
```

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): la suite esperada es toda verde desde i0.3" -m "Cierra la parte de INV-007 (y de INV-055) sobre el estado esperado de CLAUDE.md seccion 9." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: INV‑009, un solo lugar por valor esperado compartido

**Files:**
- Create: `tests/fixtures/actualizacion_uc02.py`, `tests/fixtures/computo_civil.py`
- Modify: `tests/unit/test_escenarios.py:38-40`
- Modify: `tests/integration/test_actualizacion_precios.py:48-59`
- Modify: `tests/fixtures/tarifas_sistemas.py` (tras `:67`)
- Modify: `tests/unit/test_tarifas_sistemas.py:31,86,122`
- Modify: `tests/integration/test_presupuesto_sistemas.py:44,92`
- Modify: `tests/fixtures/presupuesto_auditado.py:45-47`
- Modify: `tests/unit/test_reglas_civil.py:27-42,112`
- Modify: `tests/integration/test_civil_verificacion.py:32-40`

**Interfaces:**
- Produces:
  - `tests.fixtures.actualizacion_uc02`: `CEMENTO`, `ARENA`, `PRECIOS_NUEVOS`, `VARIACIONES`, `INCREMENTO_PU_CONCRETO`, `INCREMENTO_TOTAL`.
  - `tests.fixtures.computo_civil`: `CODIGOS`, `SOBREANCHO`, `ESPESOR_FONDO`, `DIAMETRO_TUBERIA_M`, `DESPERDICIO_TUBERIA`, `FACTOR_VOLUMEN_TUBERIA` (`Decimal`).
  - `tests.fixtures.tarifas_sistemas.PRECIO_UNITARIO_PF_ESPERADO`.
- Las Tareas 6, 12 y 13 consumen estos nombres.

- [ ] **Step 1: Consumidores primero (rojo).**

En `tests/unit/test_escenarios.py`, reemplazar `:38-40` por:

```python
# Escenario de precios del caso UC‑02: solo cemento y arena suben, solo el concreto los usa.
from tests.fixtures.actualizacion_uc02 import INCREMENTO_PU_CONCRETO  # noqa: E402
from tests.fixtures.actualizacion_uc02 import PRECIOS_NUEVOS as PRECIOS_UC02  # noqa: E402
```

Mejor todavía: mover esas dos importaciones al bloque de imports (tras `from tests.fixtures import apu_linea_base as linea_base`, `:33`) sin `noqa` y dejar en `:38` solo el comentario.

En `tests/integration/test_actualizacion_precios.py`:
- Borrar `:48-59`: el comentario, `CEMENTO`, `ARENA`, `PRECIOS_NUEVOS`, `VARIACIONES`, los dos comentarios, `INCREMENTO_PU_CONCRETO` e `INCREMENTO_TOTAL`.
- Conservar `VARIACION_PU_CONCRETO_PCT` (`:60-61`).
- Agregar al bloque de imports:

```python
from tests.fixtures.actualizacion_uc02 import (
    ARENA,
    CEMENTO,
    INCREMENTO_PU_CONCRETO,
    INCREMENTO_TOTAL,
    PRECIOS_NUEVOS,
    VARIACIONES,
)
```

En `tests/unit/test_tarifas_sistemas.py`, borrar `:31` y reemplazar `PRECIO_UNITARIO_ESPERADO` por `sis.PRECIO_UNITARIO_PF_ESPERADO` en `:86` y `:122`. En `tests/integration/test_presupuesto_sistemas.py`, borrar `:44` y reemplazar `PRECIO_UNITARIO_PF` por `sis.PRECIO_UNITARIO_PF_ESPERADO` en `:92`.

En `tests/fixtures/presupuesto_auditado.py`, borrar `:45-47` (el comentario y `FACTOR_VOLUMEN_TUBERIA = "0.0081"`) y agregar al bloque de imports:

```python
from tests.fixtures.computo_civil import FACTOR_VOLUMEN_TUBERIA
```

En `tests/unit/test_reglas_civil.py`:
- Borrar `:27-42` (supuestos y `CODIGOS`).
- Agregar al bloque de imports:

```python
from tests.fixtures.computo_civil import (
    CODIGOS,
    DESPERDICIO_TUBERIA,
    DIAMETRO_TUBERIA_M,
    ESPESOR_FONDO,
    SOBREANCHO,
)
from tests.fixtures.presupuesto_auditado import BALANCE_RELLENO
```

- En `:112` (ahora más arriba), reemplazar `balance="{LB-01-EXC} - {LB-04-CON} - {LB-02-TUB} * 0.008107338624",` por `balance=BALANCE_RELLENO,`.

En `tests/integration/test_civil_verificacion.py`, borrar `:32-40` (comentario y `CODIGOS`) y agregar al bloque de imports `from tests.fixtures.computo_civil import CODIGOS`.

Run: `uv run pytest tests/unit/test_escenarios.py tests/integration/test_actualizacion_precios.py tests/unit/test_tarifas_sistemas.py tests/integration/test_presupuesto_sistemas.py tests/unit/test_reglas_civil.py tests/integration/test_civil_verificacion.py -q`
Expected:
- Errores de colección `ModuleNotFoundError: No module named 'tests.fixtures.actualizacion_uc02'` y `'tests.fixtures.computo_civil'`.
- `AttributeError: module 'tests.fixtures.tarifas_sistemas' has no attribute 'PRECIO_UNITARIO_PF_ESPERADO'` en las pruebas de sistemas.

- [ ] **Step 2: Crear `tests/fixtures/actualizacion_uc02.py`**

```python
"""UC‑02 sobre la línea base con la muestra `data/samples/precios/lista_2026-06-01.csv`.

Única copia (INV‑009) de lo que esa muestra cambia y de su efecto, calculado a mano. La usan la
prueba de integración de UC‑02, la de escenarios de UC‑08 y la de la API.
"""

from __future__ import annotations

from decimal import Decimal

from tests.fixtures import apu_linea_base as linea_base

CEMENTO = "Cemento Portland"
ARENA = "Arena lavada"

#: Lo que sube la muestra, y la fracción de variación de docs/modelo_datos.md §6:
#: (nuevo − anterior) / anterior.
PRECIOS_NUEVOS = {CEMENTO: Decimal("18"), ARENA: Decimal("33")}
VARIACIONES = {CEMENTO: Decimal("0.2"), ARENA: Decimal("0.1")}

#: 7,5 sacos × (18 − 15) + 0,45 m3 × (33 − 30) = 23,85 USD de material por m3 de concreto; el
#: incremento atraviesa administración y utilidad en cascada: 23,85 × 1,15 × 1,10 = 30,17025.
INCREMENTO_PU_CONCRETO = Decimal("30.17025")

_CANTIDAD_CONCRETO = next(
    linea.cantidad
    for linea in linea_base.PRESUPUESTO_AUDITADO
    if linea.codigo_partida == linea_base.APU_CONCRETO.codigo_partida
)
#: El cómputo auditado lleva 1,66 m3 de concreto: 1,66 × 30,17025 = 50,082615.
INCREMENTO_TOTAL = INCREMENTO_PU_CONCRETO * _CANTIDAD_CONCRETO
```

- [ ] **Step 3: Crear `tests/fixtures/computo_civil.py`**

```python
"""La muestra civil paramétrica (`data/samples/civil/`): códigos, supuestos y factor de la tubería.

Única copia (INV‑009) de lo que comparten las pruebas del adaptador civil:

- Los códigos de partida son los de la línea base, porque el adaptador no decide códigos: los
  recibe el llamador.
- Los cuatro supuestos están declarados en `data/samples/civil/README.md`. La memoria auditada no
  fija margen de excavación, espesor de fondo, diámetro en metros ni desperdicio de tubería.
- El factor de sección de la tubería no se transcribe: se evalúa con la misma expresión que declara
  el adaptador (`adapters.civil.reglas.REGLA_VOLUMEN_TUBERIA`).
"""

from __future__ import annotations

from decimal import Decimal

from adapters.civil.evaluador import evaluar_regla
from adapters.civil.reglas import REGLA_VOLUMEN_TUBERIA
from tests.fixtures import apu_linea_base as linea_base

CODIGOS = {
    "concreto": linea_base.APU_CONCRETO.codigo_partida,
    "encofrado": linea_base.APU_ENCOFRADO.codigo_partida,
    "excavacion": linea_base.APU_EXCAVACION.codigo_partida,
    "tuberia": linea_base.APU_TUBERIA.codigo_partida,
    "relleno": linea_base.APU_RELLENO.codigo_partida,
}

SOBREANCHO = Decimal("0.10")
ESPESOR_FONDO = Decimal("0.10")
DIAMETRO_TUBERIA_M = Decimal("0.1016")  # 4 pulg, coherente con DIAMETRO_TUBERIA_PROYECTO
DESPERDICIO_TUBERIA = Decimal("0.05")

#: Volumen de un metro de tubería de 4 pulg (m3/m): 0,7854 × 0,1016² = 0,008107338624, evaluado
#: con la expresión del adaptador. Antes, la fixture del presupuesto auditado lo escribía truncado
#: a 0,0081 y la prueba del adaptador, completo: dos precisiones del mismo dato.
FACTOR_VOLUMEN_TUBERIA = evaluar_regla(
    REGLA_VOLUMEN_TUBERIA, {"longitud": Decimal("1"), "diametro": DIAMETRO_TUBERIA_M}
)
```

- [ ] **Step 4: El precio unitario de sistemas en su fixture.** En `tests/fixtures/tarifas_sistemas.py`, tras `PARAMETROS_SISTEMAS` (`:67`), agregar:

```python
#: Precio unitario de un punto de función **calculado a mano** con la fórmula de CLAUDE.md §4 antes
#: de correr el motor (README de `data/sistemas/fuentes/`). Es un resultado esperado, no un precio
#: de entrada: única copia para las pruebas de M3.1 y M3.2 (INV‑009).
PRECIO_UNITARIO_PF_ESPERADO = Decimal("110.992365")
```

- [ ] **Step 5: Verde, con el 7 de 7 intacto pese al factor exacto**

Run: `uv run pytest tests/unit/test_escenarios.py tests/integration/test_actualizacion_precios.py tests/unit/test_tarifas_sistemas.py tests/integration/test_presupuesto_sistemas.py tests/unit/test_reglas_civil.py tests/integration/test_civil_verificacion.py tests/unit/test_verification.py tests/integration/test_auditoria_7_de_7.py tests/unit/test_costing.py -q -W error --strict-markers && grep -rn "0\.0081\b\|110\.992365\|30\.17025" tests`
Expected:
- Verde. El esperado de R5 pasa de 7,8856 a 7,885423873…, y `test_r5_no_reporta_nada_si_el_balance_se_cumple` (`7.8856`) sigue dentro del 5 %.
- El `grep` solo encuentra las definiciones de las fixtures, los docstrings y comentarios que explican el cálculo, y `TOTAL_ESPERADO` (`16093.892925`) de `test_presupuesto_sistemas.py`.

- [ ] **Step 6: Suite completa y lint**

Run: `uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: verde y limpio, con el mismo número de pruebas que antes de la tarea.

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures tests/unit/test_escenarios.py tests/integration/test_actualizacion_precios.py tests/unit/test_tarifas_sistemas.py tests/integration/test_presupuesto_sistemas.py tests/unit/test_reglas_civil.py tests/integration/test_civil_verificacion.py
git commit -m "test: una sola copia de los esperados compartidos" -m "Cierra INV-009: incremento de UC-02, precio unitario del punto de funcion y factor de seccion de la tuberia, este ultimo derivado de adapters.civil.reglas. La linea base y el 7 de 7 no cambian." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: INV‑008, los literales de la línea base vuelven a su fixture

**Files:**
- Modify: `tests/fixtures/apu_linea_base.py` (tras `:174`, tras `:183`, tras `:292`; docstring `:7-8`)
- Modify: `tests/unit/test_costing_destajo.py:23-34,131`
- Modify: `tests/integration/test_api.py:34,77-90,108,111,138,140,256,338-339`
- Modify: `tests/unit/test_adapter_civil_ifc.py:18-19`, `tests/unit/test_generador_ifc.py:15,21,23`
- Modify: `tests/integration/test_actualizacion_precios.py:207-208,308-309`
- Modify: `tests/integration/test_persistencia.py:85,94`
- Modify: `tests/integration/test_rendimientos.py:35,146,193`, `tests/integration/test_api_rendimientos.py:17,122`
- Modify: `tests/unit/test_linea_base.py` (prueba nueva)

**Interfaces:**
- Consumes: `tests.fixtures.actualizacion_uc02.INCREMENTO_TOTAL` y `tests.fixtures.computo_civil.CODIGOS` (Tarea 5).
- Produces: `apu_linea_base.CODIGOS_LINEA_BASE`, `PRECIO_UNITARIO_EXACTO`, `TOTAL_EXACTO_LINEA_BASE` y `precio_de_insumo(descripcion) -> Decimal`. Ningún valor existente cambia.
- Alcance: las líneas que cita INV‑008, más `test_api.py:140`, `test_generador_ifc.py:15` y `test_persistencia.py:85`, que son el mismo hecho en la misma aserción. El resto de literales de `test_persistencia.py` queda fuera y se anota en la bitácora como observación.

- [ ] **Step 1: Consumidores primero (rojo).** Aplicar los reemplazos siguientes.

`tests/unit/test_costing_destajo.py`: borrar `:23-34` (comentario y diccionario) y cambiar `:131` por:

```python
        esperado = lb.PRECIO_UNITARIO_EXACTO[apu.codigo_partida]
```

`tests/integration/test_api.py`, en el bloque de imports:

```python
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import INCREMENTO_TOTAL
from tests.fixtures.computo_civil import CODIGOS as CODIGOS_CIVIL
```

Reemplazos en `test_api.py`:
- `:34` → `    assert set(linea_base.CODIGOS_LINEA_BASE) <= codigos`
- `:77-83`: borrar el diccionario `codigos` y cambiar en `:90` `data={"codigos": json.dumps(codigos)},` por `data={"codigos": json.dumps(CODIGOS_CIVIL)},`
- `:108` → `    assert r.json()["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)  # texto exacto`
- `:111`:

```python
    assert detalle["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)
    assert len(detalle["partidas"]) == len(linea_base.PRESUPUESTO_AUDITADO)
```

- `:138`:

```python
    assert cuerpo["total_nuevo"] == formatear_decimal(
        linea_base.TOTAL_EXACTO_LINEA_BASE + INCREMENTO_TOTAL, DECIMALES_PRESENTACION
    )
```

- `:140` → `    assert filas[linea_base.APU_CONCRETO.codigo_partida]["variacion_pct"] != "0"`
- `:256` → `    assert detalle.status_code == 200`, seguido de `    assert detalle.json()["total"] == str(linea_base.TOTAL_PRESUPUESTO_AUDITADO)`
- `:338-339`:

```python
    concreto = linea_base.APU_CONCRETO.codigo_partida
    assert items[0]["cantidad"] == str(linea_base.CANTIDAD_POR_TANQUILLA_MEMORIA[concreto])
    assert items[0]["codigo_partida"] == concreto
```

`tests/unit/test_adapter_civil_ifc.py`: agregar `from tests.fixtures import apu_linea_base as linea_base` y reemplazar `:18-19` por:

```python
    concreto = linea_base.APU_CONCRETO.codigo_partida
    # (0.8^2 - 0.6^2) * 0.8: la memoria de calculo de la linea base, por tanquilla
    assert item.cantidad == linea_base.CANTIDAD_POR_TANQUILLA_MEMORIA[concreto]
    assert item.unidad == "m3" and item.codigo_partida == concreto
```

`tests/unit/test_generador_ifc.py`: agregar `from tests.fixtures import apu_linea_base as linea_base` y reemplazar `:15`, `:21` y `:23` por:

```python
    geometria = linea_base.GEOMETRIA_TANQUILLA
    generar(ruta, a=geometria["a"], h=geometria["h"], e=geometria["e"])
```

```python
    concreto = linea_base.APU_CONCRETO.codigo_partida
    assert apu["COVENIN_Codigo"] == concreto and apu["Unidad"] == "m3"
```

```python
    assert Decimal(str(qto["VolumenConcreto"])) == (
        linea_base.CANTIDAD_POR_TANQUILLA_MEMORIA[concreto]
    )
```

`tests/integration/test_actualizacion_precios.py`, `:207-208`:

```python
    assert precios["Piedra picada"] == linea_base.precio_de_insumo("Piedra picada")
    assert precios["Retroexcavadora"] == linea_base.precio_de_insumo("Retroexcavadora")
```

y `:308-309`:

```python
    assert por_insumo[CEMENTO].precio_anterior == linea_base.precio_de_insumo(CEMENTO)
    assert por_insumo[ARENA].precio_anterior == linea_base.precio_de_insumo(ARENA)
```

`tests/integration/test_persistencia.py`:
- `:85` → `        composicion = catalogo.composicion(linea_base.APU_CONCRETO.codigo_partida, fecha=fecha)`
- `:94` → `    assert cemento(date(2026, 5, 1)) == linea_base.precio_de_insumo("Cemento Portland")`

`tests/integration/test_rendimientos.py`: agregar `from tests.fixtures import apu_linea_base as linea_base` y hacer estos reemplazos:
- `:35` → `EXCAVACION = linea_base.APU_EXCAVACION.codigo_partida  # sembrada con su rendimiento estimado`
- tras `:36`, agregar `SEMBRADO = linea_base.APU_EXCAVACION.rendimiento`
- `:146` → `    assert dispersion.media == (SEMBRADO + Decimal("75") + Decimal("82") + Decimal("90")) / 4`
- `:193` → `    assert propuesta.rendimiento.valor == SEMBRADO`

`tests/integration/test_api_rendimientos.py`: agregar `from decimal import Decimal` y `from tests.fixtures import apu_linea_base as linea_base`, y hacer estos reemplazos:
- `:17` → `EXCAVACION = linea_base.APU_EXCAVACION.codigo_partida`
- tras `:17`, agregar `SEMBRADO = linea_base.APU_EXCAVACION.rendimiento`
- `:122` → `    assert dispersion["media"] == str((SEMBRADO + Decimal("75") + Decimal("85")) / 3)`

Agregar a `tests/unit/test_linea_base.py`:

```python
def test_el_total_exacto_redondeado_es_el_del_pdf():
    """`TOTAL_EXACTO_LINEA_BASE` es el total del motor; a dos decimales, el 1 586,61 auditado."""
    from core.verification.informe import DECIMALES_PRESENTACION
    from core.verification.texto import formatear_decimal

    total = formatear_decimal(lb.TOTAL_EXACTO_LINEA_BASE, DECIMALES_PRESENTACION)
    assert total == str(lb.TOTAL_PRESUPUESTO_AUDITADO)


def test_precio_de_insumo_lee_la_transcripcion_del_pdf():
    concreto = {linea.descripcion: linea.precio for linea in lb.APU_CONCRETO.materiales}
    assert lb.precio_de_insumo("Cemento Portland") == concreto["Cemento Portland"]
    with pytest.raises(KeyError, match="Cemento blanco"):
        lb.precio_de_insumo("Cemento blanco")
```

Run: `uv run pytest tests/unit/test_costing_destajo.py tests/integration/test_api.py tests/unit/test_adapter_civil_ifc.py tests/unit/test_generador_ifc.py tests/integration/test_actualizacion_precios.py tests/integration/test_persistencia.py tests/integration/test_rendimientos.py tests/integration/test_api_rendimientos.py tests/unit/test_linea_base.py -q`
Expected: fallos por `AttributeError: module 'tests.fixtures.apu_linea_base' has no attribute 'PRECIO_UNITARIO_EXACTO'` (y `CODIGOS_LINEA_BASE`, `TOTAL_EXACTO_LINEA_BASE`, `precio_de_insumo`).

- [ ] **Step 2: Agregar los nombres a la fixture sin cambiar ningún valor.** En `tests/fixtures/apu_linea_base.py`, tras `APUS_LINEA_BASE = (…)` (`:174`):

```python
CODIGOS_LINEA_BASE = tuple(apu.codigo_partida for apu in APUS_LINEA_BASE)


def precio_de_insumo(descripcion: str) -> Decimal:
    """Precio con que la línea base transcribe un material o equipo, buscado por su descripción.

    Devuelve el de la primera línea que lo nombra, en el orden de `APUS_LINEA_BASE`. No sirve para
    los homónimos con precio distinto (`Pala`, `Agua`…; docs/modelo_datos.md §6): ahí el precio
    depende del APU y se lee de la línea concreta.
    """
    for apu in APUS_LINEA_BASE:
        for linea in (*apu.materiales, *apu.equipos):
            if linea.descripcion == descripcion:
                return linea.precio
    raise KeyError(f"la linea base no transcribe ningun insumo {descripcion!r}")
```

Tras `PRECIO_UNITARIO_ESPERADO = {…}` (`:177-183`):

```python
# El mismo precio unitario con el `Decimal` exacto que produce el motor (comprobado contra
# `calcular_apu`): lo usan las pruebas que caracterizan que el motor no cambió ni un decimal y que
# comparan por igualdad, no con la tolerancia de ± 0,01 de la fuente externa. Antes vivía en
# `tests/unit/test_costing_destajo.py` (INV‑008).
PRECIO_UNITARIO_EXACTO = {
    "LB-01-EXC": Decimal("8.600418750"),
    "LB-02-TUB": Decimal("10.1933700"),
    "LB-03-ENC": Decimal("33.237875000"),
    "LB-04-CON": Decimal("242.63965000"),
    "LB-05-REL": Decimal("52.57656250"),
}
```

Tras `TOTAL_PRESUPUESTO_AUDITADO = Decimal("1586.61")` (`:292`):

```python
# Total del presupuesto 001 con los precios unitarios exactos del motor: el que calculan
# `generar_presupuesto` y la API antes de redondear. A dos decimales es el 1 586,61 del PDF.
TOTAL_EXACTO_LINEA_BASE = sum(
    (
        linea.cantidad * PRECIO_UNITARIO_EXACTO[linea.codigo_partida]
        for linea in PRESUPUESTO_AUDITADO
    ),
    Decimal(0),
)
```

En el docstring (`:7-8`), la frase de consumidores pasa a:

```python
Consumidores: toda la suite (las pruebas importan los nombres de este módulo en vez de repetir
cifras o códigos, INV‑008), scripts/seed.py (Sesión I0.4) y las fixtures derivadas de tests/fixtures/.
```

- [ ] **Step 3: Verde, con la línea base intacta**

Run: `uv run pytest tests/unit/test_costing_destajo.py tests/integration/test_api.py tests/unit/test_adapter_civil_ifc.py tests/unit/test_generador_ifc.py tests/integration/test_actualizacion_precios.py tests/integration/test_persistencia.py tests/integration/test_rendimientos.py tests/integration/test_api_rendimientos.py tests/unit/test_linea_base.py tests/unit/test_costing.py tests/integration/test_auditoria_7_de_7.py -q -W error --strict-markers && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: todo verde. La suite completa suma dos pruebas nuevas.

- [ ] **Step 4: Commit**

```bash
git add tests
git commit -m "test: los literales de la linea base vuelven a su fixture" -m "Cierra INV-008: codigos, 1586.61, 0.224, precios y rendimiento 80 se importan de tests/fixtures/apu_linea_base.py; los PU exactos se mudan alli. Ningun valor cambia." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: INV‑003, un `float` en los parámetros no aborta el informe

**Files:**
- Modify: `core/verification/expresiones.py:52-58,111-114`
- Test: `tests/unit/test_verification.py` (tras `:540`); `tests/unit/test_budget.py` (prueba nueva)

**Interfaces:**
- Consumes: expediente B.1.
- Produces: `evaluar` lanza `ExpresionInvalida("el parametro 'x' no es Decimal sino float")` ante un valor que no es `Decimal`.

- [ ] **Step 1: Pruebas que fallan.** En `tests/unit/test_verification.py`, agregar `from tests.fixtures.computo_auditado import origen_de` al bloque de imports y, tras `:540`:

```python
@pytest.mark.parametrize("regla", ["longitud * 2", "longitud"])
def test_r1_reporta_un_parametro_que_no_es_decimal_en_vez_de_reventar_auditar(presupuesto, regla):
    """Principio 7 (INV‑003): un `float` en `ItemComputo.parametros` no saca a `auditar` con
    `TypeError`. Con la expresión compuesta fallaba la aritmética; con el nombre solo, la
    comparación posterior contra la cantidad `Decimal`. En ambos casos R1 lo informa y sigue.
    """
    roto = _con_item(
        presupuesto,
        linea_base.APU_EXCAVACION.codigo_partida,
        regla=regla,
        parametros={"longitud": 1.5},
    )
    informe = auditar(roto)
    origen = origen_de(linea_base.APU_EXCAVACION.codigo_partida)
    hallazgos = [h for h in informe.hallazgos if h.regla == "R1" and h.origen_ids == (origen,)]
    assert len(hallazgos) == 1
    assert "'longitud'" in hallazgos[0].descripcion
    assert "float" in hallazgos[0].descripcion


def test_r5_reporta_un_parametro_que_no_es_decimal_en_vez_de_reventar_auditar(presupuesto):
    roto = _con_item(
        presupuesto,
        linea_base.APU_RELLENO.codigo_partida,
        especificaciones={
            directivas.CLAVE_BALANCE: f"{{{linea_base.APU_EXCAVACION.codigo_partida}}} - holgura"
        },
        parametros={"holgura": 0.5},
    )
    informe = auditar(roto)
    hallazgos = [h for h in informe.hallazgos if h.regla == "R5"]
    assert len(hallazgos) == 1
    assert "'holgura'" in hallazgos[0].descripcion
```

En `tests/unit/test_budget.py`, agregar `from dataclasses import replace` al bloque de imports y, tras `test_elaborar_siempre_devuelve_informe`:

```python
def test_elaborar_con_un_parametro_no_decimal_emite_presupuesto_e_informe():
    """Principio 7 (INV‑003): datos degradados dan hallazgos, nunca un presupuesto sin informe."""
    excavacion = linea_base.APU_EXCAVACION.codigo_partida
    items = tuple(
        replace(item, regla="longitud * 2", parametros={"longitud": 1.5})
        if item.codigo_partida == excavacion
        else item
        for item in items_auditados()
    )

    resultado = elaborar(
        items,
        composiciones_linea_base(),
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=linea_base.CODIGO_PRESUPUESTO,
        fecha=linea_base.FECHA_LINEA_BASE,
    )

    assert abs(resultado.presupuesto.total - linea_base.TOTAL_PRESUPUESTO_AUDITADO) <= TOLERANCIA
    assert any("'longitud'" in h.descripcion for h in resultado.informe.por_regla()["R1"])
```

Run: `uv run pytest tests/unit/test_verification.py tests/unit/test_budget.py -q -W error --strict-markers -k "no_es_decimal or no_decimal"`
Expected: `4 failed`, con `TypeError: unsupported operand type(s) for *: 'float' and 'decimal.Decimal'` (expresión compuesta, R5 y `elaborar`) y `TypeError: unsupported operand type(s) for -: 'decimal.Decimal' and 'float'` (nombre solo).

- [ ] **Step 2: Implementación mínima.** En `core/verification/expresiones.py`, reemplazar la rama `ast.Name` de `_evaluar_nodo` (`:111-114`) por:

```python
    if isinstance(nodo, ast.Name):
        if nodo.id not in valores:
            raise ParametroFaltante(nodo.id)
        valor = valores[nodo.id]
        if not isinstance(valor, Decimal):
            # Un `float` en los parámetros haría fallar la aritmética (o la comparación posterior
            # de R1) con `TypeError`, fuera del alcance de las reglas: el informe no se emitiría
            # (principio 7 de CLAUDE.md §2). Aquí se convierte en un dato inválido reportable.
            raise ExpresionInvalida(
                f"el parametro {nodo.id!r} no es Decimal sino {type(valor).__name__}"
            )
        return valor
```

y el docstring de `evaluar` (`:53-57`) pasa a:

```python
    """Evalúa `expresion` con `valores` y devuelve un `Decimal` exacto.

    Lanza `ExpresionInvalida` ante cualquier construcción no aritmética o si un parámetro usado no
    es `Decimal`, y `ParametroFaltante` si la expresión usa un nombre que no está en `valores`.
    """
```

- [ ] **Step 3: Verde, con la línea base y el 7 de 7 intactos**

Run: `uv run pytest tests/unit/test_verification.py tests/unit/test_budget.py tests/unit/test_costing.py tests/integration/test_auditoria_7_de_7.py -q -W error --strict-markers && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: todo verde.

- [ ] **Step 4: Commit**

```bash
git add core/verification/expresiones.py tests/unit/test_verification.py tests/unit/test_budget.py
git commit -m "fix(verificacion): un parametro que no es decimal se reporta y no aborta el informe" -m "Cierra INV-003 (principio 7). La validacion en el nodo de nombre cubre tambien la expresion de un solo nombre; ver expediente B.1." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: INV‑012, regla no evaluable como INFO y R7 no aplicable sin plan

**Files:**
- Modify: `core/verification/reglas.py:1-17,47-58,137-149,183-193,449-456,555-557`
- Test: `tests/unit/test_verification.py:258-260,371-372,391-398,435-471,515-540`

**Interfaces:**
- Consumes: expediente B.2; RF‑23, UC‑05 2a y 3a (`docs/ERS.md:234,238,469`), sin cambios en la ERS.
- Produces:
  - `core.verification.reglas.REGLA_NO_EVALUABLE = "regla no evaluable"` y `NO_APLICABLE = "no aplicable"`.
  - R1 y R5 emiten INFO al no poder evaluar; R2 y R7 sin curva emiten INFO «no aplicable».

- [ ] **Step 1: ¿Mueve la línea base o el 7 de 7?** Primero, por lectura:
  - `test_auditoria_7_de_7.py:23-39` cuenta solo hallazgos de severidad ≥ ERROR.
  - El presupuesto de las siete inconsistencias trae `CURVA_AUDITADA`, así que R7 no entra en la rama «sin curva».
  - Todas sus reglas son evaluables, así que ninguna pasa por la rama inevaluable.
  - Conclusión: no debe moverse. Se fija la referencia corriendo antes:

Run: `uv run pytest tests/integration/test_auditoria_7_de_7.py tests/unit/test_costing.py tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61 -q -W error`
Expected: verde, y anotar el resultado.

- [ ] **Step 2: Pruebas que fallan.** En `tests/unit/test_verification.py`, agregar `from core.verification.reglas import NO_APLICABLE, REGLA_NO_EVALUABLE` al bloque de imports y el ayudante tras `_errores` (`:59-60`):

```python
def _no_evaluables(hallazgos):
    return [hallazgo for hallazgo in hallazgos if REGLA_NO_EVALUABLE in hallazgo.descripcion]
```

Reemplazar `test_r2_informa_cuando_no_hay_curva` (`:258-260`) por:

```python
def test_r2_informa_cuando_no_hay_curva(presupuesto):
    hallazgos = CierreCurvaInversion().evaluar(replace(presupuesto, curva=()))
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]
    assert NO_APLICABLE in hallazgos[0].descripcion
```

Reemplazar `test_r7_no_reporta_nada_si_el_presupuesto_no_declara_curva` (`:371-372`) por:

```python
def test_r7_se_declara_no_aplicable_si_el_presupuesto_no_declara_curva(presupuesto):
    """UC‑05, flujo 2a: sin plan de trabajo R7 se declara no aplicable en el informe (INV‑012)."""
    hallazgos = ConciliacionPresupuestoPlan().evaluar(replace(presupuesto, curva=()))
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]
    assert NO_APLICABLE in hallazgos[0].descripcion
```

Reemplazar las aserciones de las seis pruebas de datos degradados:
- `test_r1_reporta_la_regla_que_no_puede_evaluar` (`:397-398`):

```python
    hallazgos = _no_evaluables(TrazabilidadGeometrica().evaluar(roto))
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]  # RF‑23, UC‑05 3a
    assert "no se puede evaluar" in hallazgos[0].descripcion
```

- `test_r5_reporta_una_referencia_de_balance_no_resuelta` (`:441-443`):

```python
    hallazgos = _no_evaluables(BalanceVolumetrico().evaluar(roto))
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]
    assert "referencia no resuelta" in hallazgos[0].descripcion
```

- `test_r5_reporta_un_balance_que_no_puede_evaluar` (`:454-456`) y `test_r5_reporta_un_balance_sin_llaves_en_vez_de_lanzar` (`:469-471`), cada una:

```python
    hallazgos = _no_evaluables(BalanceVolumetrico().evaluar(roto))
    assert [h.severidad for h in hallazgos] == [Severidad.INFO]
    assert "no se puede evaluar" in hallazgos[0].descripcion
```

- `test_r1_reporta_una_regla_que_desborda_en_vez_de_reventar_auditar` (`:526`) y `test_r5_reporta_un_balance_que_desborda_en_vez_de_reventar_auditar` (`:539`): `assert hallazgos[0].severidad is Severidad.ERROR` pasa a `assert hallazgos[0].severidad is Severidad.INFO`.

Run: `uv run pytest tests/unit/test_verification.py -q -W error --strict-markers`
Expected: primero `ImportError: cannot import name 'NO_APLICABLE' from 'core.verification.reglas'` (error de colección).

- [ ] **Step 3: Implementación.** En `core/verification/reglas.py`, el párrafo del docstring (`:3-5`) pasa a:

```python
Cada regla es una clase `ReglaVerificacion` que recibe un `Presupuesto` y devuelve una lista de
`Hallazgo`. Ninguna lanza excepciones por datos: un balance inevaluable o una referencia rota son
hallazgos INFO «regla no evaluable» (RF‑23, UC‑05 flujo 3a), y R2 y R7 sin plan de trabajo se
declaran «no aplicables» (UC‑05 flujo 2a). Ninguno interrumpe a las demás reglas.
```

`__all__` suma `"NO_APLICABLE"` y `"REGLA_NO_EVALUABLE"`, y tras `_CERO = Decimal(0)` (`:58`) se agrega:

```python
#: Prefijo de un hallazgo INFO de una regla que no pudo evaluarse (RF‑23, UC‑05 flujo 3a).
REGLA_NO_EVALUABLE = "regla no evaluable"
#: Con qué se declaran R2 y R7 cuando el presupuesto no trae plan de trabajo (UC‑05 flujo 2a).
NO_APLICABLE = "no aplicable"
```

R1, rama `except` (`:137-149`):

```python
        except (ExpresionInvalida, ParametroFaltante) as error:
            return [
                Hallazgo(
                    regla=self.codigo,
                    severidad=Severidad.INFO,
                    descripcion=(
                        f"{REGLA_NO_EVALUABLE}: la regla declarada por {item.codigo_partida} "
                        f"({item.regla!r}) no se puede evaluar: {error}"
                    ),
                    origen_ids=(item.origen_id,),
                    valor_observado=item.cantidad,
                )
            ]
```

R2, descripción sin curva (`:189-191`):

```python
                    descripcion=(
                        f"R2 {NO_APLICABLE}: el presupuesto no declara curva de inversion, "
                        "no hay cierre que verificar"
                    ),
```

R5, `_inevaluable` (`:449-456`):

```python
    def _inevaluable(self, item: ItemComputo, ids: tuple[str, ...], detalle: str) -> Hallazgo:
        """RF‑23: un balance que no se puede evaluar se informa como INFO y las demás siguen."""
        return Hallazgo(
            regla=self.codigo,
            severidad=Severidad.INFO,
            descripcion=f"{REGLA_NO_EVALUABLE}: {item.codigo_partida}: {detalle}",
            origen_ids=ids,
            valor_observado=item.cantidad,
        )
```

R7, sin curva (`:556-557`):

```python
        if not presupuesto.curva:
            return [
                Hallazgo(
                    regla=self.codigo,
                    severidad=Severidad.INFO,
                    descripcion=(
                        f"R7 {NO_APLICABLE}: el presupuesto no declara plan de trabajo, no hay "
                        "montos que conciliar con sus partidas"
                    ),
                )
            ]
```

- [ ] **Step 4: Verde**

Run: `uv run pytest tests/unit/test_verification.py -q -W error --strict-markers`
Expected: verde.

- [ ] **Step 5: La línea base y el 7 de 7 no se movieron; los dominios siguen cumpliendo**

Run: `uv run pytest tests/integration/test_auditoria_7_de_7.py tests/unit/test_costing.py tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61 tests/integration/test_presupuesto_industrial.py tests/integration/test_presupuesto_sistemas.py tests/integration/test_civil_verificacion.py tests/integration/test_seed_demo.py -q -W error --strict-markers && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: todo verde, y el mismo resultado del 7 de 7 que en el paso 1.

- [ ] **Step 6: Commit**

```bash
git add core/verification/reglas.py tests/unit/test_verification.py
git commit -m "fix(verificacion): regla no evaluable como info y r7 no aplicable sin plan" -m "Cierra INV-012: regla y prueba se alinean con RF-23 y UC-05 2a y 3a, que no cambian. La linea base y el 7 de 7 no se mueven; ver expediente B.2." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: INV‑004, una sola fórmula de variación

**Files:**
- Modify: `core/catalog/precios.py:51-61` (`__all__`) y antes de `:107` (función nueva); `:115-118`
- Modify: `core/budget/actualizacion.py:43,211,306-308`
- Test: `tests/unit/test_variacion_precio.py` (nuevo); `tests/integration/test_actualizacion_precios.py` (prueba nueva)

**Interfaces:**
- Consumes: expediente B.3.
- Produces: `core.catalog.precios.variacion_relativa(anterior: Decimal, nuevo: Decimal) -> Decimal`. `core.budget.actualizacion._variacion` desaparece.

- [ ] **Step 1: Pruebas que fallan.** Crear `tests/unit/test_variacion_precio.py`:

```python
"""Una sola fórmula de variación (INV‑004): docs/modelo_datos.md §6, (nuevo − anterior) / anterior."""

from __future__ import annotations

from decimal import Decimal

from core.budget import actualizacion
from core.catalog.precios import CambioDetectado, variacion_relativa
from core.models import Insumo


def test_la_variacion_es_la_de_modelo_datos():
    assert variacion_relativa(Decimal("15"), Decimal("18")) == Decimal("0.2")


def test_con_base_nula_la_variacion_es_cero_por_politica_declarada():
    assert variacion_relativa(Decimal("0"), Decimal("18")) == Decimal("0")


def test_el_cambio_detectado_usa_la_misma_funcion():
    cambio = CambioDetectado(
        insumo=Insumo(), precio_anterior=Decimal("0"), precio_nuevo=Decimal("18")
    )
    assert cambio.variacion == Decimal("0")


def test_actualizacion_no_define_su_propia_formula():
    assert not hasattr(actualizacion, "_variacion")
    assert actualizacion.variacion_relativa is variacion_relativa
```

Agregar a `tests/integration/test_actualizacion_precios.py` (sección «Lectura del archivo y creación de la lista»), con `registrar_cambios` sumado al import de `core.catalog`:

```python
def test_un_precio_anterior_nulo_no_hace_fallar_el_registro_de_cambios(sesion, tmp_path):
    """INV‑004: un precio 0 es válido (`leer_lista_precios` acepta no negativos), así que la
    variación con base nula no puede lanzar `DivisionByZero` en medio de UC‑02."""
    donado = tmp_path / "cemento_donado.csv"
    donado.write_text(f"tipo,insumo,unidad,precio\nmaterial,{CEMENTO},saco,0\n", encoding="utf-8")
    intermedia = crear_lista_desde_archivo(
        sesion,
        donado,
        nombre="Lista con cemento donado",
        moneda=linea_base.MONEDA,
        fecha_vigencia=date(2026, 5, 15),
    ).lista
    nueva = crear_lista_desde_archivo(
        sesion, MUESTRA, nombre=NOMBRE_LISTA_NUEVA, moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
    ).lista

    cambios = {cambio.insumo.descripcion: cambio for cambio in registrar_cambios(sesion, intermedia, nueva)}

    assert cambios[CEMENTO].precio_anterior == Decimal("0")
    assert cambios[CEMENTO].variacion == Decimal("0")
    assert cambios[ARENA].variacion == VARIACIONES[ARENA]
```

Partir en varias líneas lo que supere los 100 caracteres.

Run: `uv run pytest tests/unit/test_variacion_precio.py tests/integration/test_actualizacion_precios.py -q -W error --strict-markers`
Expected: `ImportError: cannot import name 'variacion_relativa'` en el módulo unitario, y `decimal.DivisionByZero` en la prueba de integración.

- [ ] **Step 2: Implementación.** En `core/catalog/precios.py`, antes de `class CambioDetectado` (`:107`):

```python
_CERO = Decimal(0)


def variacion_relativa(anterior: Decimal, nuevo: Decimal) -> Decimal:
    """Fracción (nuevo − anterior) / anterior: la fórmula de docs/modelo_datos.md §6.

    Única definición del sistema (INV‑004): la usan `CambioDetectado.variacion` y la incidencia por
    partida de `core.budget.actualizacion`.

    **Base nula.** Con `anterior == 0` la variación relativa no está definida. Política declarada:
    devuelve 0, y el registro conserva `precio_anterior = 0`, que es lo que distingue ese caso de
    un precio que no cambió. Un precio 0 es válido (`leer_lista_precios` acepta cualquier no
    negativo), así que la fórmula no puede lanzar `DivisionByZero` en medio de UC‑02.
    """
    return (nuevo - anterior) / anterior if anterior else _CERO
```

`CambioDetectado.variacion` (`:115-118`):

```python
    @property
    def variacion(self) -> Decimal:
        """Fracción (nuevo − anterior) / anterior, con la política de base nula declarada."""
        return variacion_relativa(self.precio_anterior, self.precio_nuevo)
```

`__all__` suma `"variacion_relativa"` al final.

En `core/budget/actualizacion.py`:
- `:43` pasa a `from core.catalog.precios import registrar_cambios, variacion_relativa`.
- `:211` pasa a `            variacion=variacion_relativa(`.
- Borrar `_variacion` (`:306-308`) y la línea en blanco que la precede.

- [ ] **Step 3: Verde**

Run: `uv run pytest tests/unit/test_variacion_precio.py tests/integration/test_actualizacion_precios.py tests/integration/test_api.py -q -W error --strict-markers && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: todo verde.

- [ ] **Step 4: Commit**

```bash
git add core/catalog/precios.py core/budget/actualizacion.py tests/unit/test_variacion_precio.py tests/integration/test_actualizacion_precios.py
git commit -m "fix(catalogo): una sola formula de variacion con base nula declarada" -m "Cierra INV-004: CambioDetectado y la incidencia por partida importan variacion_relativa; con precio anterior 0 devuelve 0 en vez de lanzar DivisionByZero. Ver expediente B.3." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: INV‑005, una sola puerta de registro de rendimientos

**Files:**
- Modify: `core/catalog/repositorio.py:251-254`
- Modify: `core/catalog/rendimientos.py:1-18,100-146`
- Test: `tests/integration/test_rendimientos.py` (dos pruebas nuevas)

**Interfaces:**
- Consumes: expediente B.4.
- Produces: `rendimientos.registrar_rendimiento` delega en `Catalogo.registrar_rendimiento`. Ante una ejecución inexistente, los dos lanzan `LookupError` exacto, con el mensaje «registre la obra antes de medir sobre ella».

- [ ] **Step 1: Pruebas que fallan.** En `tests/integration/test_rendimientos.py`, cambiar el import `from core.contracts.apu import TipoRendimiento` por `from core.contracts.apu import Rendimiento, TipoRendimiento` y agregar:

```python
def test_el_registro_del_modulo_delega_en_el_del_catalogo(sesion, monkeypatch):
    """INV‑005: una sola implementación del registro, la de `Catalogo`."""
    llamadas = []
    original = Catalogo.registrar_rendimiento

    def espia(self, rendimiento):
        llamadas.append(rendimiento)
        return original(self, rendimiento)

    monkeypatch.setattr(Catalogo, "registrar_rendimiento", espia)
    registrado = registrar_rendimiento(
        sesion, EXCAVACION, valor=Decimal("75"), tipo=TipoRendimiento.ESTIMADO, fecha=FECHA
    )

    assert llamadas == [registrado]


def test_una_ejecucion_inexistente_se_rechaza_igual_por_las_dos_puertas(sesion):
    contrato = Rendimiento(
        codigo_partida=EXCAVACION,
        valor=Decimal("70"),
        tipo=TipoRendimiento.MEDIDO,
        fecha=FECHA,
        referencia_ejecucion="OBRA-FANTASMA",
    )
    with pytest.raises(LookupError, match="registre la obra") as desde_catalogo:
        Catalogo(sesion).registrar_rendimiento(contrato)
    with pytest.raises(LookupError, match="registre la obra") as desde_modulo:
        registrar_rendimiento(
            sesion,
            EXCAVACION,
            valor=Decimal("70"),
            tipo=TipoRendimiento.MEDIDO,
            fecha=FECHA,
            referencia_ejecucion="OBRA-FANTASMA",
        )
    assert type(desde_catalogo.value) is LookupError
    assert type(desde_modulo.value) is LookupError
```

Run: `uv run pytest tests/integration/test_rendimientos.py -q -W error --strict-markers -k "delega or dos_puertas"`
Expected: `2 failed`. La primera falla por `assert [] == [Rendimiento(...)]`. La segunda, porque `Catalogo` lanza `CatalogoIncompleto` sin «registre la obra» (`Regex pattern did not match`).

- [ ] **Step 2: Implementación.** En `core/catalog/repositorio.py:251-254`:

```python
            if ejecucion is None:
                # `LookupError` y no `CatalogoIncompleto`: la ejecución es un recurso que no existe
                # (404 en la API), no un precio o rendimiento que falte para reconstruir un APU.
                raise LookupError(
                    f"no hay ninguna ejecución con referencia {rendimiento.referencia_ejecucion!r}: "
                    "registre la obra antes de medir sobre ella"
                )
```

En `core/catalog/rendimientos.py`, el cuerpo de `registrar_rendimiento` (`:109-146`) pasa a:

```python
    """Registra un rendimiento y devuelve el `Rendimiento` del contrato ya persistido.

    El contrato se construye primero: sus invariantes (valor > 0, MEDIDO exige referencia)
    rechazan la petición antes de tocar la base. El registro lo hace `Catalogo.registrar_rendimiento`,
    la única implementación (INV‑005), que lanza `LookupError` si la partida no existe o la
    referencia no corresponde a ninguna ejecución registrada.
    """
    contrato = Rendimiento(
        codigo_partida=codigo_partida,
        valor=valor,
        tipo=tipo,
        fecha=fecha,
        condiciones=condiciones,
        referencia_ejecucion=referencia_ejecucion,
    )
    return a_rendimiento(Catalogo(session).registrar_rendimiento(contrato))
```

En el docstring del módulo (`:5-9`), la frase «este módulo la aplica en la frontera construyendo el contrato **antes** de tocar la base, y además exige que la referencia apunte a una ejecución que exista» pasa a: «este módulo construye el contrato **antes** de tocar la base y delega el registro en `Catalogo.registrar_rendimiento`, que exige que la referencia apunte a una ejecución que exista». `select` y `models` siguen en uso (`registrar_ejecucion`).

- [ ] **Step 3: Verde, con la API respondiendo 404 como antes**

Run: `uv run pytest tests/integration/test_rendimientos.py tests/integration/test_api_rendimientos.py tests/integration/test_persistencia.py -q -W error --strict-markers && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: todo verde. En particular, `test_medido_sin_referencia_es_422_y_con_referencia_real_queda_trazado` sigue viendo `404`.

- [ ] **Step 4: Commit**

```bash
git add core/catalog/repositorio.py core/catalog/rendimientos.py tests/integration/test_rendimientos.py
git commit -m "refactor(catalogo): una sola puerta para registrar rendimientos" -m "Cierra INV-005: el modulo construye el contrato y delega en Catalogo.registrar_rendimiento; excepcion unica LookupError (404 en la API). Ver expediente B.4." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: INV‑013 + INV‑069, `elaborar` como punto único, con ítems pendientes (UC‑01 3a)

INV‑069 e INV‑013 tocan la misma función: se corrigen juntos en el núcleo y después se migran los llamadores.

**Files:**
- Modify: `core/budget/presupuesto.py` (archivo completo abajo), `core/budget/__init__.py:5-13,37,39-59`
- Test: `tests/unit/test_budget.py:22-35,95-107` y tres pruebas nuevas
- Callers, en commits separados:
  - `ui/paginas/elaborar.py:31,227-248`
  - `ui/paginas/componer.py:34-40,766,799-822`
  - `api/rutas/presupuestos.py:39-50,85-96`
  - `scripts/seed_demo.py:83-89,172-173,344-361`
  - `scripts/generar_resultados_ml.py:47-53,158-167`
- Modify: `docs/auditoria/2026-09-inventario.md` (filas nuevas)

**Interfaces:**
- Consumes: expedientes B.5 y B.6. `ConciliacionPresupuestoPlan` sin curva ya informa «no aplicable» (Tarea 8).
- Produces:
  - `elaborar(..., plan: Sequence[PeriodoPlan] | GeneradorPlan | None = None) -> ResultadoElaboracion`.
  - `ResultadoElaboracion.pendientes: tuple[ItemComputo, ...]`, `CODIGO_PENDIENTE = "PENDIENTE"` y `GeneradorPlan = Callable[[Presupuesto], Sequence[PeriodoPlan]]`, exportados desde `core.budget`.

- [ ] **Step 1: ¿Mueve la línea base o el 7 de 7?** Por lectura:
  - El 7 de 7 audita `presupuesto_con_siete_inconsistencias()` sin pasar por `elaborar`.
  - `test_presupuesto_reproduce_1586_61` usa `generar_presupuesto`, que no cambia.
  - Con todas las composiciones presentes, `elaborar` no genera pendientes y su resultado es idéntico al de hoy.
  - Conclusión: no debe moverse. Lo confirma el paso 5.

- [ ] **Step 2: Pruebas que fallan.** En `tests/unit/test_budget.py`, el import de `core.budget` pasa a:

```python
from core.budget import (
    CODIGO_PENDIENTE,
    con_curva,
    elaborar,
    exportar_excel,
    generar_curva,
    generar_presupuesto,
    plan_secuencial,
)
```

agregar `from core.contracts.verificacion import Severidad`, y dar docstring a `test_codigo_sin_composicion_lanza_valueerror` (`:95`):

```python
def test_codigo_sin_composicion_lanza_valueerror():
    """`generar_presupuesto` es el paso intermedio: exige composición para todo ítem. El flujo 3a
    de UC‑01 (ítem pendiente) lo implementa `elaborar`: ver la prueba siguiente."""
```

Agregar tras ella:

```python
def test_un_item_sin_partida_queda_pendiente_y_el_informe_lo_declara():
    """UC‑01, flujo 3a (INV‑013): no suma al total, no entra al plan, el informe lo declara."""
    composiciones = composiciones_linea_base()
    huerfano = linea_base.APU_RELLENO.codigo_partida
    del composiciones[huerfano]
    completo = _presupuesto()
    total_huerfano = sum(
        (p.total for p in completo.partidas if p.item.codigo_partida == huerfano), Decimal(0)
    )

    resultado = elaborar(
        items_auditados(),
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=linea_base.CODIGO_PRESUPUESTO,
        fecha=linea_base.FECHA_LINEA_BASE,
        plan=plan_secuencial,
    )

    assert [item.codigo_partida for item in resultado.pendientes] == [huerfano]
    assert huerfano not in {p.item.codigo_partida for p in resultado.presupuesto.partidas}
    assert resultado.presupuesto.total == completo.total - total_huerfano
    assert resultado.presupuesto.total_curva == resultado.presupuesto.total
    (declarado,) = resultado.informe.por_regla()[CODIGO_PENDIENTE]
    assert declarado.severidad is Severidad.ERROR
    assert resultado.informe.partida_de(declarado) == huerfano
    assert not resultado.informe.cumple


def test_sin_ninguna_partida_valorable_el_informe_se_emite_igual():
    resultado = elaborar(
        items_auditados(),
        {},
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=linea_base.CODIGO_PRESUPUESTO,
        fecha=linea_base.FECHA_LINEA_BASE,
        plan=plan_secuencial,
    )

    assert resultado.presupuesto.partidas == ()
    assert resultado.presupuesto.total == Decimal(0)
    assert len(resultado.pendientes) == len(linea_base.PRESUPUESTO_AUDITADO)
    assert len(resultado.informe.por_regla()[CODIGO_PENDIENTE]) == len(
        linea_base.PRESUPUESTO_AUDITADO
    )


def test_elaborar_acepta_el_plan_como_funcion_del_presupuesto_valorado():
    """INV‑069: el protocolo borrador → `plan_secuencial` → `elaborar` vive en `elaborar`."""
    argumentos = dict(
        codigo=linea_base.CODIGO_PRESUPUESTO,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
    )
    con_funcion = elaborar(
        items_auditados(),
        composiciones_linea_base(),
        linea_base.PARAMETROS_LINEA_BASE,
        plan=plan_secuencial,
        **argumentos,
    )
    con_lista = elaborar(
        items_auditados(),
        composiciones_linea_base(),
        linea_base.PARAMETROS_LINEA_BASE,
        plan=plan_secuencial(_presupuesto()),
        **argumentos,
    )

    assert con_funcion.presupuesto == con_lista.presupuesto
    assert con_funcion.informe.hallazgos == con_lista.informe.hallazgos
    assert con_funcion.presupuesto.total_curva == con_funcion.presupuesto.total
    assert con_funcion.pendientes == ()
```

Run: `uv run pytest tests/unit/test_budget.py -q -W error --strict-markers`
Expected: error de colección `ImportError: cannot import name 'CODIGO_PENDIENTE' from 'core.budget'`.

- [ ] **Step 3: Implementación.** Reemplazar `core/budget/presupuesto.py` completo por:

```python
"""Armado del presupuesto: de las cantidades de obra al precio de cada renglón.

`generar_presupuesto` cose las tres piezas del núcleo sin conocer ningún dominio: recibe los
`ItemComputo` que produjo un adaptador, las composiciones del catálogo y los parámetros de costo, y
llama al motor puro `core.costing.calcular_apu` una vez por renglón. Es un paso intermedio: exige
composición para todo ítem.

`elaborar` es el flujo completo de la Sesión I0.5: presupuesto, curva y **auditoría siempre**, sin
que el usuario la pida (principio 7 de CLAUDE.md §2). Por eso devuelve `ResultadoElaboracion`, que
lleva el informe junto al presupuesto: no hay forma de obtener uno sin el otro. Es también el único
lugar del protocolo «presupuesto valorado → plan de trabajo → curva → auditoría» (INV‑069): quien
necesita el plan secuencial pasa `plan=plan_secuencial`, sin armar un borrador propio.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from core.budget.curva import PeriodoPlan, con_curva, generar_curva
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.item_computo import ItemComputo
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto
from core.contracts.verificacion import Hallazgo, Severidad
from core.costing import calcular_apu
from core.verification import auditar
from core.verification.informe import InformeAuditoria
from core.verification.texto import formatear_decimal

__all__ = [
    "CODIGO_PENDIENTE",
    "GeneradorPlan",
    "ResultadoElaboracion",
    "elaborar",
    "generar_presupuesto",
]

MONEDA_POR_DEFECTO = "USD"

#: Código con que el informe declara un ítem sin partida en el catálogo (UC‑01, flujo 3a). No es una
#: de las siete reglas de CLAUDE.md §7: lo emite la elaboración, que es quien sabe qué ítems no pudo
#: valorar, y viaja en el mismo informe para que nadie reciba el presupuesto sin esa declaración.
CODIGO_PENDIENTE = "PENDIENTE"

#: Un plan de trabajo que se calcula sobre el presupuesto ya valorado (p. ej. `plan_secuencial`).
GeneradorPlan = Callable[[Presupuesto], Sequence[PeriodoPlan]]


@dataclass(frozen=True, slots=True)
class ResultadoElaboracion:
    """Lo que produce una elaboración: el presupuesto, el informe que siempre lo acompaña y los
    ítems que quedaron pendientes por no tener partida en el catálogo (UC‑01, flujo 3a)."""

    presupuesto: Presupuesto
    informe: InformeAuditoria
    pendientes: tuple[ItemComputo, ...] = ()


def generar_presupuesto(
    items: Sequence[ItemComputo],
    composiciones: Mapping[str, ComposicionAPU],
    parametros: ParametrosCosto,
    codigo: str,
    fecha: date,
    moneda: str = MONEDA_POR_DEFECTO,
) -> Presupuesto:
    """Un `PartidaPresupuestada` por ítem, en el orden recibido, con su precio recién calculado.

    Lanza `ValueError` con la lista de códigos si alguna cantidad no tiene composición de APU: un
    presupuesto incompleto es un presupuesto sin precio, no un presupuesto con ceros.
    """
    faltantes = _codigos_sin_composicion(items, composiciones)
    if faltantes:
        raise ValueError("no hay composicion de APU para las partidas: " + ", ".join(faltantes))

    partidas = tuple(
        PartidaPresupuestada(
            item=item,
            apu=composiciones[item.codigo_partida],
            resultado=calcular_apu(composiciones[item.codigo_partida], parametros),
        )
        for item in items
    )
    return Presupuesto(codigo=codigo, fecha=fecha, moneda=moneda, partidas=partidas)


def elaborar(
    items: Sequence[ItemComputo],
    composiciones: Mapping[str, ComposicionAPU],
    parametros: ParametrosCosto,
    codigo: str,
    fecha: date,
    moneda: str = MONEDA_POR_DEFECTO,
    plan: Sequence[PeriodoPlan] | GeneradorPlan | None = None,
) -> ResultadoElaboracion:
    """Genera el presupuesto, le añade la curva si hay plan y lo audita siempre.

    `plan` es el plan de trabajo ya escrito o una función que lo calcula sobre el presupuesto
    valorado. `plan=plan_secuencial` es el protocolo de la interfaz, la API y los sembradores, que
    antes cada uno escribía con un borrador propio (INV‑069). Sin `plan` el presupuesto no lleva
    curva y las reglas R2 y R7 lo declaran no aplicable.

    Un ítem cuya partida no tiene composición en `composiciones` queda **pendiente** (UC‑01, flujo
    3a): no entra al presupuesto, no suma al total ni al plan, y el informe lo declara con un
    hallazgo `CODIGO_PENDIENTE` de severidad ERROR. `ResultadoElaboracion.pendientes` los devuelve
    para que quien llama proponga partidas similares (UC‑03). Un plan ya escrito que reparta una
    partida pendiente lanza `PlanInvalido`, como cualquier código desconocido.
    """
    valorables = [item for item in items if item.codigo_partida in composiciones]
    pendientes = tuple(item for item in items if item.codigo_partida not in composiciones)
    presupuesto = generar_presupuesto(valorables, composiciones, parametros, codigo, fecha, moneda)
    reparto = plan(presupuesto) if callable(plan) else plan
    if reparto is not None:
        presupuesto = con_curva(presupuesto, generar_curva(presupuesto, reparto))
    informe = _declarar_pendientes(auditar(presupuesto), pendientes)
    return ResultadoElaboracion(presupuesto=presupuesto, informe=informe, pendientes=pendientes)


def _declarar_pendientes(
    informe: InformeAuditoria, pendientes: Sequence[ItemComputo]
) -> InformeAuditoria:
    """El mismo informe con un hallazgo ERROR por ítem pendiente, atribuido a su partida.

    ERROR y no ADVERTENCIA: un presupuesto al que le falta una partida no cumple, aunque la
    verificación no bloquee su emisión (UC‑01, flujo 7a).
    """
    if not pendientes:
        return informe
    declarados = tuple(
        Hallazgo(
            regla=CODIGO_PENDIENTE,
            severidad=Severidad.ERROR,
            descripcion=(
                f"el item {item.origen_id} ({formatear_decimal(item.cantidad)} {item.unidad}) "
                f"cita la partida {item.codigo_partida}, que no tiene composicion de APU: queda "
                "pendiente y no suma al total"
            ),
            origen_ids=(item.origen_id,),
            valor_observado=item.cantidad,
        )
        for item in pendientes
    )
    return InformeAuditoria(
        codigo_presupuesto=informe.codigo_presupuesto,
        hallazgos=informe.hallazgos + declarados,
        partida_por_origen={
            **{item.origen_id: item.codigo_partida for item in pendientes},
            **informe.partida_por_origen,
        },
    )


def _codigos_sin_composicion(
    items: Sequence[ItemComputo], composiciones: Mapping[str, ComposicionAPU]
) -> list[str]:
    faltantes: list[str] = []
    for item in items:
        if item.codigo_partida not in composiciones and item.codigo_partida not in faltantes:
            faltantes.append(item.codigo_partida)
    return faltantes
```

En `core/budget/__init__.py`:
- La línea 37 pasa a:

```python
from core.budget.presupuesto import (
    CODIGO_PENDIENTE,
    GeneradorPlan,
    ResultadoElaboracion,
    elaborar,
    generar_presupuesto,
)
```

- `__all__` suma `"CODIGO_PENDIENTE"` y `"GeneradorPlan"`.
- En el docstring (`:9`), el ejemplo pasa a `    resultado = elaborar(items, composiciones, parametros, codigo="001", fecha=hoy, plan=plan_secuencial)`.

- [ ] **Step 4: Verde**

Run: `uv run pytest tests/unit/test_budget.py -q -W error --strict-markers`
Expected: verde.

- [ ] **Step 5: Línea base, 7 de 7 y suite; ningún llamador cambió todavía**

Run: `uv run pytest tests/unit/test_costing.py tests/integration/test_auditoria_7_de_7.py tests/integration/test_composicion_extremo_a_extremo.py -q -W error --strict-markers && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: todo verde.

- [ ] **Step 6: Commit del núcleo, solo `core/` y `tests/`**

```bash
git add core/budget/presupuesto.py core/budget/__init__.py tests/unit/test_budget.py
git commit -m "fix(budget): elaborar es el punto unico del protocolo y deja pendientes los items sin partida" -m "Cierra en el nucleo INV-069 (plan como funcion del presupuesto valorado) e INV-013 por la ruta sin contrato: pendientes en ResultadoElaboracion y un hallazgo PENDIENTE en el informe. Ver expedientes B.5 y B.6." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 7: Llamadores de `ui/`.** En `ui/paginas/elaborar.py:31`, el import pasa a `from core.budget import elaborar, exportar_excel, plan_secuencial`. El bloque `:225-251` (desde `codigos_unicos = …` hasta `return`) pasa a:

```python
            codigos_unicos = list(dict.fromkeys(item.codigo_partida for item in items))
            composiciones = catalogo.composiciones(codigos_unicos, fecha=parametros["fecha"])
            resultado = elaborar(
                items,
                composiciones,
                ParametrosCosto(),
                codigo=str(parametros["codigo"]),
                fecha=parametros["fecha"],
                moneda=str(parametros["moneda"]),
                plan=plan_secuencial,
            )
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # `LookupError` (`CatalogoIncompleto`) si falta la composicion de alguna partida del
        # computo (por ejemplo, un dominio sin catalogo cargado); `ValueError` (`PlanInvalido`) del
        # plan de trabajo; `ArithmeticError`/`SQLAlchemyError` por simetria con el mismo criterio
        # de `ui/paginas/actualizacion.py`.
        st.session_state[CLAVE_RESULTADO] = None
        st.error(str(error))
        return
```

En `ui/paginas/componer.py`:
- Borrar `generar_presupuesto,` del import (`:38`); `plan_secuencial` se queda.
- El docstring de `:766` pasa a `    """Boton de elaboracion (paso 2): `elaborar(..., plan=plan_secuencial)`.`
- El bloque `:801-822` pasa a:

```python
        composiciones = catalogo.composiciones(codigos_unicos, fecha=fecha_presupuesto)
        resultado = elaborar(
            items,
            composiciones,
            ParametrosCosto(),
            codigo=codigo_presupuesto,
            fecha=fecha_presupuesto,
            moneda=moneda,
            plan=plan_secuencial,
        )
    except (LookupError, ValueError, ArithmeticError, SQLAlchemyError) as error:
        # `LookupError` (`CatalogoIncompleto`) si no hay lista de precios vigente a esa fecha;
        # `ValueError` (`PlanInvalido`) del plan de trabajo; `ArithmeticError` y
        # `SQLAlchemyError` por el mismo criterio que `ui/paginas/elaborar.py`.
```

Run: `uv run pytest tests/unit/test_ui_componer.py tests/unit/test_ui_app.py tests/unit/test_ui_importable.py -q -W error --strict-markers && uv run ruff check ui`
Expected: verde.

```bash
git add ui/paginas/elaborar.py ui/paginas/componer.py
git commit -m "refactor(ui): las paginas elaboran con plan=plan_secuencial" -m "Llamadores de INV-069 en ui/, en commit separado del nucleo (spec de cierre, seccion 4)." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 8: Llamador de `api/`.** En `api/rutas/presupuestos.py`, borrar `generar_presupuesto,` del import (`:47`) y reemplazar `:85-96` por:

```python
    resultado = elaborar(
        items,
        composiciones,
        parametros,
        peticion.codigo,
        peticion.fecha,
        peticion.moneda,
        plan=plan_secuencial,
    )
```

Run: `uv run pytest tests/integration/test_api.py tests/integration/test_api_escenarios.py tests/unit/test_openapi.py -q -W error --strict-markers && uv run ruff check api`
Expected: verde, con el total de la API todavía en `1586.61`.

```bash
git add api/rutas/presupuestos.py
git commit -m "refactor(api): crear presupuesto elabora con plan=plan_secuencial" -m "Llamador de INV-069 en api/, en commit separado." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 9: Llamadores de `scripts/`.** En `scripts/seed_demo.py`:
- Borrar `generar_presupuesto,` del import (`:86`).
- El docstring `:172-173` pasa a:

```python
    `composiciones` y `items` viajan emparejados por `codigo_partida`: `elaborar` los consume
    directo (encurva y audita siempre), sin transformacion.
```

- El cuerpo de `elaborar_caso_demo` (`:344-361`) pasa a:

```python
    composiciones_por_codigo = {apu.codigo_partida: apu for apu in caso.composiciones}
    return elaborar(
        caso.items,
        composiciones_por_codigo,
        caso.parametros,
        codigo=caso.codigo_presupuesto,
        fecha=caso.fecha,
        moneda=caso.moneda,
        plan=plan_secuencial,
    )
```

En `scripts/generar_resultados_ml.py`, borrar `generar_presupuesto,` del import (`:50`) y reemplazar `:158-167` por:

```python
    resultado = elaborar(
        items,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        plan=plan_secuencial,
        **argumentos,
    )
```

Run: `uv run pytest tests/integration/test_seed_demo.py tests/unit/test_resultados_ml.py -q -W error --strict-markers && uv run ruff check scripts && TMP_C1=$(mktemp -d) && uv run python scripts/seed_demo.py --db "$TMP_C1/demo.db" | grep -E "Partida: 8|Total: 4131.10 USD|Auditoria: 3 hallazgo\(s\), CUMPLE" && rm -rf "$TMP_C1" && uv run python scripts/generar_resultados_ml.py && git diff --exit-code -- docs/resultados_ml.md`
Expected: verde. Aparecen las tres líneas de la demostración, y `docs/resultados_ml.md` queda sin diferencias (salida 0).

```bash
git add scripts/seed_demo.py scripts/generar_resultados_ml.py
git commit -m "refactor(scripts): la demostracion y los resultados de ml elaboran con plan=plan_secuencial" -m "Llamadores de INV-069 en scripts/, en commit separado; generar_resultados_ml.py era un quinto sitio del protocolo que el inventario no citaba." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 10: Ningún sitio fuera de `core/budget` escribe el protocolo**

Run: `grep -rn "plan_secuencial(borrador)\|borrador = generar_presupuesto" --include=*.py ui api scripts`
Expected: vacío. Las pruebas y fixtures que lo conservan son evidencia de equivalencia y no se tocan.

- [ ] **Step 11: Registrar en el inventario lo que esta tarea hizo visible.** Agregar al final de §3, cada una con el siguiente ID libre, estas dos filas.

La primera: antes de registrarla, reproducirla.

Run: `uv run python -B -c "from pathlib import Path; from adapters.civil.tabular import AdaptadorCivilTabular; from core.budget import elaborar, plan_secuencial; from tests.fixtures import apu_linea_base as lb; from tests.fixtures.computo_auditado import composiciones_linea_base; from tests.fixtures.computo_civil import CODIGOS; items = AdaptadorCivilTabular(codigos=CODIGOS).extraer(Path('data/samples/civil/tanquillas_y_zanja.csv')); elaborar(items, composiciones_linea_base(), lb.PARAMETROS_LINEA_BASE, codigo='X', fecha=lb.FECHA_LINEA_BASE, plan=plan_secuencial)"`
Expected: `PlanInvalido: las fracciones del plan de trabajo deben sumar exactamente 1 por partida: LB-01-EXC suma 2`. Si no se reproduce, la fila no se agrega y se anota en la bitácora.

```markdown
| INV-0NN | planificación de C1 (Tarea 11) | core (cruza: ui) | Requisito (UC‑01) | importante | `core/budget/curva.py:85-90` (`plan_secuencial`), `:117-140` (`_validar`); `data/samples/civil/tanquillas_y_zanja.csv` (dos ítems `LB-01-EXC`: tanquilla y zanja) | `plan_secuencial` crea un período por **renglón** con fracción 1; con dos renglones del mismo código la fracción suma 2 y `generar_curva` lanza `PlanInvalido`. Elaborar la muestra civil tabular desde la interfaz falla (reproducido en C1) | `plan_secuencial` agrupa por código: un período por código distinto, en orden de primera aparición. Se corrige en `core/` | C1 si Eugenio lo ratifica en GC1; si no, fase siguiente | abierto |
| INV-0NN | planificación de C1 (Tarea 11; expediente B.5) | ui (cruza: api) | Trazabilidad (UC‑01 3a) | importante | `ui/paginas/elaborar.py:225-226`, `ui/paginas/componer.py:799-801`, `api/rutas/presupuestos.py:80-82` frente a `core/catalog/repositorio.py:73-78,128-134` | El núcleo ya deja pendiente un ítem sin partida (INV‑013), pero la interfaz y la API piden antes las composiciones al catálogo, que lanza `KeyError` ante una partida desconocida: 3a no se alcanza de punta a punta, y la propuesta de tres partidas similares (UC‑03) no existe en ese flujo | Pedir composiciones solo de las partidas existentes y mostrar `ResultadoElaboracion.pendientes` con sus propuestas; en commits de `ui/` y `api/` | C2 (api) + C3 (ui) | abierto |
```

```bash
git add docs/auditoria/2026-09-inventario.md
git commit -m "docs(auditoria): hallazgos visibles al unificar el protocolo de elaboracion" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: INV‑011, RF‑19 con prueba, RF‑20 implementado y UC‑04 trazado

**Files:**
- Create: `core/budget/diferencial.py`, `tests/unit/test_recalculo_uc04.py`
- Modify: `core/budget/__init__.py`
- Test: `tests/unit/test_reglas_civil.py` (prueba nueva de RF‑19), `tests/unit/test_budget.py` (dos pruebas de RF‑20)
- Modify: `docs/auditoria/2026-09-inventario.md` (fila nueva)

**Interfaces:**
- Consumes: expediente B.7; `tests.fixtures.computo_civil` (Tarea 5); `elaborar(plan=plan_secuencial)` (Tarea 11).
- Produces: `core.budget.DiferencialPartida` y `core.budget.diferencial_por_partida(anterior: Presupuesto, recalculado: Presupuesto) -> tuple[DiferencialPartida, ...]`.

**¿Existe la capacidad?**
- RF‑19: **sí**. `adapters/civil/reglas.computar_tanquillas` reevalúa sus expresiones con los parámetros nuevos (`:41-108`). Solo falta la prueba, que se escribe y se comprueba que muerde.
- RF‑20: **no**. `_comparar` (`core/budget/actualizacion.py:267-303`) es privado, supone los mismos renglones (`zip(..., strict=True)`) y no da el diferencial de cantidad. Se implementa por el RF existente; spec §2: es corrección.

- [ ] **Step 1: RF‑19, la prueba de su criterio.** En `tests/unit/test_reglas_civil.py`, sumar `REGLA_CONCRETO_TANQUILLA`, `REGLA_ENCOFRADO_TANQUILLA` y `REGLA_EXCAVACION_TANQUILLA` al import de `adapters.civil.reglas` y agregar:

```python
def test_cambiar_el_ancho_altera_solo_las_cantidades_que_dependen_de_el():
    """RF‑19 (UC‑04, pasos 1 y 2; INV‑011): cambiar el ancho de la tanquilla altera las cantidades
    derivadas de esa dimensión y ninguna otra, y cada ítem nuevo trae la expresión y los
    parámetros que lo produjeron."""
    geometria = linea_base.GEOMETRIA_TANQUILLA
    ancho_nuevo = geometria["a"] + Decimal("0.20")
    antes = [*_computar_una_tanquilla(n=linea_base.N_TANQUILLAS), *_computar_la_zanja()]
    despues = [
        *computar_tanquillas(
            origen_id="T-01",
            codigos=CODIGOS,
            a=ancho_nuevo,
            h=geometria["h"],
            e=geometria["e"],
            n=linea_base.N_TANQUILLAS,
            sobreancho=SOBREANCHO,
            espesor_fondo=ESPESOR_FONDO,
        ),
        *_computar_la_zanja(),
    ]

    cambiadas = {
        nuevo.regla
        for viejo, nuevo in zip(antes, despues, strict=True)
        if viejo.cantidad != nuevo.cantidad
    }

    assert cambiadas == {
        REGLA_CONCRETO_TANQUILLA,
        REGLA_ENCOFRADO_TANQUILLA,
        REGLA_EXCAVACION_TANQUILLA,
    }
    for item in despues:
        assert evaluar_regla(item.regla, item.parametros) == item.cantidad
        if item.regla in cambiadas:
            assert item.parametros["a"] == ancho_nuevo
```

Run: `uv run pytest tests/unit/test_reglas_civil.py -q -W error --strict-markers -k ancho`
Expected: `1 passed`, porque la capacidad existe. **Comprobar que muerde:** cambiar temporalmente `a=ancho_nuevo` por `a=geometria["a"]` en `despues` y volver a correr. Debe fallar con `assert set() == {…}`. Restaurar la línea.

- [ ] **Step 2: RF‑20, pruebas que fallan.** En `tests/unit/test_budget.py`, sumar `diferencial_por_partida` al import de `core.budget` y agregar:

```python
def test_la_suma_de_los_diferenciales_por_partida_iguala_la_diferencia_de_totales():
    """RF‑20 (UC‑04, paso 5; INV‑011): cantidad, precio unitario y total por partida."""
    anterior = _presupuesto()
    concreto = linea_base.APU_CONCRETO.codigo_partida
    duplicado = tuple(
        replace(item, cantidad=item.cantidad * 2) if item.codigo_partida == concreto else item
        for item in items_auditados()
    )
    recalculado = generar_presupuesto(
        duplicado,
        composiciones_linea_base(),
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=f"{linea_base.CODIGO_PRESUPUESTO}-R",
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
    )

    filas = diferencial_por_partida(anterior, recalculado)

    assert [fila.codigo_partida for fila in filas] == [
        linea.codigo_partida for linea in linea_base.PRESUPUESTO_AUDITADO
    ]
    assert sum((fila.diferencia_total for fila in filas), Decimal(0)) == (
        recalculado.total - anterior.total
    )
    (fila_concreto,) = [fila for fila in filas if fila.codigo_partida == concreto]
    assert fila_concreto.diferencia_cantidad == fila_concreto.cantidad_anterior
    assert fila_concreto.diferencia_precio_unitario == Decimal(0)
    assert fila_concreto.diferencia_total == fila_concreto.total_anterior
    assert all(fila.diferencia_total == 0 for fila in filas if fila.codigo_partida != concreto)


def test_una_partida_que_desaparece_entra_al_diferencial_con_cero_y_sin_precio():
    anterior = _presupuesto()
    relleno = linea_base.APU_RELLENO.codigo_partida
    sin_relleno = generar_presupuesto(
        tuple(item for item in items_auditados() if item.codigo_partida != relleno),
        composiciones_linea_base(),
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=f"{linea_base.CODIGO_PRESUPUESTO}-R",
        fecha=linea_base.FECHA_LINEA_BASE,
    )

    (fila,) = [
        fila
        for fila in diferencial_por_partida(anterior, sin_relleno)
        if fila.codigo_partida == relleno
    ]

    assert fila.cantidad_nueva == Decimal(0)
    assert fila.total_nuevo == Decimal(0)
    assert fila.precio_unitario_nuevo is None
    assert fila.diferencia_precio_unitario is None
    assert fila.diferencia_total == -fila.total_anterior
```

Run: `uv run pytest tests/unit/test_budget.py -q -W error --strict-markers`
Expected: error de colección `ImportError: cannot import name 'diferencial_por_partida' from 'core.budget'`.

- [ ] **Step 3: Implementación.** Crear `core/budget/diferencial.py`:

```python
"""RF‑20 (UC‑04, paso 5): el diferencial entre una versión del presupuesto y su recálculo.

Cuando cambia un parámetro dimensional (RF‑19), el presupuesto se vuelve a elaborar y el usuario
necesita ver qué cambió **por partida**: cantidad, precio unitario y total. Este módulo compara dos
`Presupuesto` ya elaborados; no recalcula nada, así que es una función pura sobre contratos.

La comparación es por **código de partida**, no por renglón. Un cambio de alcance puede partir o
fundir renglones (dos tanquillas que pasan a ser tres, una zanja que se divide), y el código es lo
único estable entre las dos versiones. Varios renglones del mismo código se suman; comparten precio
unitario porque comparten APU. Una partida que solo existe en una de las dos versiones aparece con
cantidad y total cero del otro lado, y sin precio unitario.

Devuelve dataclasses con `Decimal`, no un `DataFrame`: la presentación decide el formato (INV‑040).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto

__all__ = ["DiferencialPartida", "diferencial_por_partida"]

CERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class DiferencialPartida:
    """Una partida en las dos versiones. `None` en un precio unitario: la partida no estaba."""

    codigo_partida: str
    cantidad_anterior: Decimal
    cantidad_nueva: Decimal
    precio_unitario_anterior: Decimal | None
    precio_unitario_nuevo: Decimal | None
    total_anterior: Decimal
    total_nuevo: Decimal

    @property
    def diferencia_cantidad(self) -> Decimal:
        return self.cantidad_nueva - self.cantidad_anterior

    @property
    def diferencia_precio_unitario(self) -> Decimal | None:
        """Sin precio en alguna de las dos versiones no hay diferencia que calcular."""
        if self.precio_unitario_anterior is None or self.precio_unitario_nuevo is None:
            return None
        return self.precio_unitario_nuevo - self.precio_unitario_anterior

    @property
    def diferencia_total(self) -> Decimal:
        return self.total_nuevo - self.total_anterior


def diferencial_por_partida(
    anterior: Presupuesto, recalculado: Presupuesto
) -> tuple[DiferencialPartida, ...]:
    """Una fila por código de partida, en el orden en que aparece por primera vez (primero los de
    `anterior`, después los nuevos de `recalculado`).

    La suma de `diferencia_total` de todas las filas es exactamente
    `recalculado.total - anterior.total`: los dos lados suman los mismos `Decimal` sin redondear.
    """
    antes = _por_codigo(anterior.partidas)
    despues = _por_codigo(recalculado.partidas)
    return tuple(
        _fila(codigo, antes.get(codigo), despues.get(codigo))
        for codigo in dict.fromkeys([*antes, *despues])
    )


#: Lo que una versión dice de una partida: cantidad total, precio unitario y total.
_Resumen = tuple[Decimal, Decimal, Decimal]


def _por_codigo(partidas: Sequence[PartidaPresupuestada]) -> dict[str, _Resumen]:
    resumen: dict[str, _Resumen] = {}
    for partida in partidas:
        codigo = partida.item.codigo_partida
        cantidad, precio, total = resumen.get(
            codigo, (CERO, partida.resultado.precio_unitario, CERO)
        )
        resumen[codigo] = (cantidad + partida.item.cantidad, precio, total + partida.total)
    return resumen


def _fila(codigo: str, antes: _Resumen | None, despues: _Resumen | None) -> DiferencialPartida:
    cantidad_anterior, pu_anterior, total_anterior = antes or (CERO, None, CERO)
    cantidad_nueva, pu_nuevo, total_nuevo = despues or (CERO, None, CERO)
    return DiferencialPartida(
        codigo_partida=codigo,
        cantidad_anterior=cantidad_anterior,
        cantidad_nueva=cantidad_nueva,
        precio_unitario_anterior=pu_anterior,
        precio_unitario_nuevo=pu_nuevo,
        total_anterior=total_anterior,
        total_nuevo=total_nuevo,
    )
```

En `core/budget/__init__.py`, agregar `from core.budget.diferencial import DiferencialPartida, diferencial_por_partida` (tras el import de `curva`) y sumar `"DiferencialPartida"` y `"diferencial_por_partida"` a `__all__`.

Run: `uv run pytest tests/unit/test_budget.py -q -W error --strict-markers`
Expected: verde.

- [ ] **Step 4: UC‑04, pasos 1 a 5 de punta a punta.** Crear `tests/unit/test_recalculo_uc04.py`:

```python
"""UC‑04 de punta a punta (RF‑19 y RF‑20; INV‑011): cambiar el ancho de las tanquillas y recalcular.

Los ítems vienen de las reglas paramétricas del adaptador civil con los supuestos de la muestra
(`tests/fixtures/computo_civil.py`); los precios, de la línea base. Se usan tanquillas y tubería,
no la excavación de la zanja, para que ningún código de partida se repita (ver el hallazgo de
`plan_secuencial` registrado en la Tarea 11 del plan de C1).
"""

from __future__ import annotations

from decimal import Decimal

from adapters.civil.reglas import computar_tanquillas, computar_zanja
from core.budget import diferencial_por_partida, elaborar, plan_secuencial
from core.contracts import Severidad
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import composiciones_linea_base
from tests.fixtures.computo_civil import (
    CODIGOS,
    DESPERDICIO_TUBERIA,
    DIAMETRO_TUBERIA_M,
    ESPESOR_FONDO,
    SOBREANCHO,
)

GEOMETRIA = linea_base.GEOMETRIA_TANQUILLA
ANCHO_NUEVO = GEOMETRIA["a"] + Decimal("0.20")


def _items(ancho: Decimal):
    concreto, encofrado, excavacion = computar_tanquillas(
        origen_id="T-01",
        codigos=CODIGOS,
        a=ancho,
        h=GEOMETRIA["h"],
        e=GEOMETRIA["e"],
        n=linea_base.N_TANQUILLAS,
        sobreancho=SOBREANCHO,
        espesor_fondo=ESPESOR_FONDO,
    )
    _excavacion_zanja, tuberia = computar_zanja(
        origen_id="Z-01",
        codigos=CODIGOS,
        longitud=linea_base.LONGITUD_TUBERIA_M,
        ancho=linea_base.ZANJA["ancho"],
        profundidad=linea_base.ZANJA["profundidad"],
        diametro=DIAMETRO_TUBERIA_M,
        desperdicio=DESPERDICIO_TUBERIA,
    )
    return [concreto, encofrado, excavacion, tuberia]


def _elaborar(ancho: Decimal, codigo: str):
    return elaborar(
        _items(ancho),
        composiciones_linea_base(),
        linea_base.PARAMETROS_LINEA_BASE,
        codigo=codigo,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        plan=plan_secuencial,
    )


def test_uc04_recalcula_precios_curva_y_auditoria_y_presenta_el_diferencial():
    anterior = _elaborar(GEOMETRIA["a"], "UC04-1")
    nuevo = _elaborar(ANCHO_NUEVO, "UC04-2")

    filas = diferencial_por_partida(anterior.presupuesto, nuevo.presupuesto)

    # Paso 3: se recalculan las partidas afectadas y ninguna otra.
    assert {fila.codigo_partida for fila in filas if fila.diferencia_total != 0} == {
        CODIGOS["concreto"],
        CODIGOS["encofrado"],
        CODIGOS["excavacion"],
    }
    assert all(fila.diferencia_precio_unitario == 0 for fila in filas)  # mismo APU
    # Paso 4: curva regenerada que cierra en el total nuevo, y verificación ejecutada otra vez.
    assert nuevo.presupuesto.total_curva == nuevo.presupuesto.total
    assert nuevo.informe.codigo_presupuesto == "UC04-2"
    assert not [
        h for h in nuevo.informe.hallazgos if h.regla == "R1" and h.severidad >= Severidad.ERROR
    ]
    # Paso 5: el diferencial por partida suma la diferencia de totales.
    assert sum((fila.diferencia_total for fila in filas), Decimal(0)) == (
        nuevo.presupuesto.total - anterior.presupuesto.total
    )
    assert nuevo.pendientes == ()
```

Run: `uv run pytest tests/unit/test_recalculo_uc04.py -q -W error --strict-markers`
Expected: `1 passed`. **Comprobar que muerde:** reemplazar temporalmente `_elaborar(ANCHO_NUEVO, "UC04-2")` por `_elaborar(GEOMETRIA["a"], "UC04-2")`; debe fallar la primera aserción con `set() == {…}`. Restaurar.

- [ ] **Step 5: Línea base, 7 de 7, suite y lint**

Run: `uv run pytest tests/unit/test_costing.py tests/integration/test_auditoria_7_de_7.py -q -W error --strict-markers && uv run pytest -W error --strict-markers -q && uv run ruff check . && git diff --stat main -- adapters ml`
Expected: verde, limpio y diff vacío.

- [ ] **Step 6: Commits.** Primero las pruebas de RF‑19 y UC‑04 (solo `tests/`), después RF‑20 (`core/` y su prueba).

```bash
git add tests/unit/test_reglas_civil.py tests/unit/test_recalculo_uc04.py
git commit -m "test: rf-19 y los pasos de uc-04 con prueba propia" -m "Parte de INV-011: la prueba de RF-19 es la de su criterio en la ERS (cambiar el ancho altera solo lo que depende de el); la de UC-04 traza los pasos 1 a 5." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
git add core/budget/diferencial.py core/budget/__init__.py tests/unit/test_budget.py
git commit -m "fix(budget): diferencial por partida entre una version y su recalculo" -m "Parte de INV-011: RF-20 no tenia implementacion; se implementa el RF existente (spec de cierre, seccion 2). Ver expediente B.7." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 7: Registrar los flujos de UC‑04 que C1 no cierra.** Agregar al final de §3 del inventario (siguiente ID libre):

```markdown
| INV-0NN | planificación de C1 (Tarea 12; expediente B.7) | adapters (cruza: core, docs) | Trazabilidad (UC‑04) | importante | `docs/ERS.md:211-215` (flujos 1a, 2a, 2b) frente a `adapters/civil/reglas.py:41-198`, `core/contracts/item_computo.py:52-53` | Los flujos alternativos de UC‑04 no tienen implementación: nada informa que un parámetro no participa en ninguna regla (1a); nada empareja por GlobalId al reimportar un IFC (2a); una cantidad negativa se rechaza con `ValueError` del contrato, en vez de conservar la anterior y emitir un hallazgo de R5 (2b) | Implementar 1a y 2b en la capa de adaptadores, sin cambiar `core/`, y 2a con `diferencial_por_partida` por `origen_id`; o declararlos sin cumplir en la ERS §3.2 y en plan_pruebas §8 | C2 (adaptadores) + C4 (documentos) | abierto |
```

```bash
git add docs/auditoria/2026-09-inventario.md
git commit -m "docs(auditoria): flujos alternativos de uc-04 pendientes para c2 y c4" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: INV‑014 e INV‑015, RF‑11, RF‑12, UC‑02 2b y 7a con prueba propia

**Files:**
- Test: `tests/integration/test_actualizacion_precios.py` (cuatro pruebas nuevas)
- Modify: `core/budget/actualizacion.py:46` (`__all__`) y función nueva tras `actualizar_precios`; `core/budget/__init__.py:20`
- Modify: `docs/auditoria/2026-09-inventario.md` (fila nueva)

**Interfaces:**
- Consumes: expediente B.8; `elaborar(plan=plan_secuencial)` (Tarea 11); `tests.fixtures.actualizacion_uc02` (Tarea 5); `apu_linea_base.precio_de_insumo` (Tarea 6).
- Produces: `core.budget.descartar_version(session, proyecto_nombre: str, codigo_nuevo: str) -> None`.

**¿Existe la capacidad?**
- RF‑11, RF‑12 y UC‑02 2b: **sí**. RF‑11: `actualizar_precios` nunca edita composiciones. RF‑12: el registro se persiste. 2b: `crear_lista_desde_archivo` compara por unidad normalizada y devuelve la fila en `desconocidos`. Se escriben las pruebas y se comprueba que muerden.
- UC‑02 7a: **no**. Descartar sin confirmar también deshace `CambioPrecio`. Se implementa.

- [ ] **Step 1: Pruebas de las capacidades existentes.** En `tests/integration/test_actualizacion_precios.py`, sumar al import `from core.catalog import Catalogo, abrir_sesion, crear_esquema, crear_lista_desde_archivo, crear_motor, leer_lista_precios` y agregar en la sección «Actualización del presupuesto»:

```python
def _estructura(composicion):
    """Lo que UC‑02 no puede tocar: rendimiento, líneas, cantidades, depreciaciones y modalidades."""
    return (
        composicion.rendimiento,
        tuple((linea.descripcion, linea.unidad, linea.cantidad) for linea in composicion.materiales),
        tuple(
            (linea.descripcion, linea.cantidad, linea.depreciacion) for linea in composicion.equipos
        ),
        tuple(
            (linea.descripcion, linea.cantidad, linea.modalidad) for linea in composicion.mano_obra
        ),
    )


def test_uc02_no_edita_ninguna_composicion(sesion, presupuesto_001, lista_nueva):
    """RF‑11 (INV‑014): las composiciones quedan idénticas; solo cambia la lista que las valora."""
    catalogo = Catalogo(sesion)
    antes = {
        codigo: catalogo.composicion(codigo, fecha=linea_base.FECHA_LINEA_BASE)
        for codigo in CODIGOS
    }
    lineas_antes = len(sesion.scalars(select(models.ComposicionAPU)).all())

    actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        lista_nueva.lista,
        CODIGO_NUEVO,
        plan=plan_secuencial(presupuesto_001.presupuesto),
    )

    assert len(sesion.scalars(select(models.ComposicionAPU)).all()) == lineas_antes
    for codigo in CODIGOS:
        despues = catalogo.composicion(codigo, fecha=linea_base.FECHA_LINEA_BASE)
        assert despues == antes[codigo], codigo
        con_lista_nueva = catalogo.composicion(codigo, fecha=FECHA_NUEVA)
        assert _estructura(con_lista_nueva) == _estructura(antes[codigo]), codigo


def test_los_cambios_de_precio_se_releen_tras_cerrar_la_sesion(tmp_path):
    """RF‑12 (INV‑014): un registro por insumo, recuperable desde otra sesión y otro motor."""
    url = f"sqlite:///{(tmp_path / 'uc02.db').as_posix()}"
    motor = crear_motor(url)
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            catalogo = Catalogo(sesion)
            resultado = elaborar(
                items_auditados(),
                catalogo.composiciones(CODIGOS, fecha=linea_base.FECHA_LINEA_BASE),
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
            sesion.commit()
            nueva = crear_lista_desde_archivo(
                sesion,
                MUESTRA,
                nombre=NOMBRE_LISTA_NUEVA,
                moneda=linea_base.MONEDA,
                fecha_vigencia=FECHA_NUEVA,
            )
            actualizar_precios(
                sesion,
                NOMBRE_PROYECTO,
                linea_base.CODIGO_PRESUPUESTO,
                nueva.lista,
                CODIGO_NUEVO,
                plan=plan_secuencial(resultado.presupuesto),
            )
            sesion.commit()
    finally:
        motor.dispose()

    motor = crear_motor(url)
    try:
        with abrir_sesion(motor) as sesion:
            cambios = {
                cambio.insumo.descripcion: cambio
                for cambio in sesion.scalars(select(models.CambioPrecio))
            }
            assert set(cambios) == set(PRECIOS_NUEVOS)
            for descripcion, cambio in cambios.items():
                assert cambio.precio_anterior == linea_base.precio_de_insumo(descripcion)
                assert cambio.precio_nuevo == PRECIOS_NUEVOS[descripcion]
                assert cambio.variacion == VARIACIONES[descripcion]
                assert cambio.fecha == FECHA_NUEVA
                assert {i.partida.codigo for i in cambio.incidencias} == {CONCRETO}
    finally:
        motor.dispose()


def test_una_fila_con_unidad_no_equivalente_se_rechaza_y_las_demas_se_procesan(
    sesion, presupuesto_001, tmp_path
):
    """UC‑02, flujo 2b (INV‑015): la fila se rechaza y se reporta en `desconocidos`, el insumo
    conserva su precio anterior, y la fila con una grafía equivalente (m³ ≡ m3) se procesa."""
    archivo = tmp_path / "unidades.csv"
    archivo.write_text(
        f"tipo,insumo,unidad,precio\nmaterial,{CEMENTO},m3,99\nmaterial,{ARENA},m³,33\n",
        encoding="utf-8",
    )

    resumen = crear_lista_desde_archivo(
        sesion,
        archivo,
        nombre=NOMBRE_LISTA_NUEVA,
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
    )

    assert [(p.descripcion, p.unidad) for p in resumen.desconocidos] == [(CEMENTO, "m3")]
    precios = {precio.insumo.descripcion: precio.precio for precio in resumen.lista.precios}
    assert precios[CEMENTO] == linea_base.precio_de_insumo(CEMENTO)
    assert precios[ARENA] == PRECIOS_NUEVOS[ARENA]
```

Sumar `elaborar` y `guardar_presupuesto` al import de `core.budget` si faltan.

Run: `uv run pytest tests/integration/test_actualizacion_precios.py -q -W error --strict-markers -k "no_edita or releen or no_equivalente"`
Expected: `3 passed`. **Comprobar que cada una muerde**, restaurando después de cada cambio:
- (RF‑11) Agregar temporalmente tras `actualizar_precios(...)`:

```python
    linea = sesion.scalars(select(models.ComposicionAPU)).first()
    linea.cantidad += 1
    sesion.flush()
```

  Debe fallar la comparación.
- (RF‑12) Comentar el segundo `sesion.commit()`. Debe fallar con `set() == {…}`.
- (2b) Cambiar `m3,99` por `saco,99`. Debe fallar la aserción de `desconocidos`.

```bash
git add tests/integration/test_actualizacion_precios.py
git commit -m "test(budget): rf-11, rf-12 y uc-02 2b con prueba propia" -m "Parte de INV-014 e INV-015: las capacidades existian; las pruebas se observaron mordiendo con una alteracion temporal." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 2: UC‑02 7a, prueba que falla.** Sumar `descartar_version` al import de `core.budget` y agregar:

```python
def test_descartar_la_version_nueva_conserva_el_registro_de_cambios(
    sesion, presupuesto_001, actualizacion
):
    """UC‑02, flujo 7a (INV‑015): la versión nueva desaparece; los `CambioPrecio`, sus
    `IncidenciaCambio` y la lista nueva se conservan porque alimentan el histórico de I6."""
    incidencias = len(sesion.scalars(select(models.IncidenciaCambio)).all())

    descartar_version(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO)
    sesion.commit()

    with pytest.raises(KeyError, match=CODIGO_NUEVO):
        cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, Catalogo(sesion))
    assert len(sesion.scalars(select(models.CambioPrecio)).all()) == len(PRECIOS_NUEVOS)
    assert len(sesion.scalars(select(models.IncidenciaCambio)).all()) == incidencias
    huerfanos = sesion.scalars(
        select(models.ItemComputo).where(models.ItemComputo.presupuesto_id.is_(None))
    ).all()
    assert huerfanos == []
    anterior = cargar_presupuesto(
        sesion, NOMBRE_PROYECTO, linea_base.CODIGO_PRESUPUESTO, Catalogo(sesion)
    )
    assert anterior == presupuesto_001.presupuesto
```

Run: `uv run pytest tests/integration/test_actualizacion_precios.py -q -W error --strict-markers`
Expected: error de colección `ImportError: cannot import name 'descartar_version' from 'core.budget'`.

- [ ] **Step 3: Implementación.** En `core/budget/actualizacion.py`, `__all__` (`:46`) pasa a `["COLUMNAS_COMPARATIVO", "Comparativo", "actualizar_precios", "descartar_version"]`. Tras `actualizar_precios` (`:160`) se agrega:

```python
def descartar_version(session: Session, proyecto_nombre: str, codigo_nuevo: str) -> None:
    """UC‑02, flujo 7a: el usuario descarta la versión nueva y el registro de cambios se conserva.

    Borra de la sesión el presupuesto `codigo_nuevo`: sus renglones, su curva y sus hallazgos caen
    por cascada, y sus `ItemComputo` se borran aquí para no dejar filas huérfanas. Quedan intactos
    la lista nueva, sus `CambioPrecio` y sus `IncidenciaCambio`, que alimentan el histórico del
    módulo predictivo. «Marcarla como descartada» exigiría una columna nueva (una migración, fuera
    del límite del cierre): se borra (expediente B.8 de C1).

    No confirma la transacción, como `actualizar_precios`: la confirma la capa que representa la
    decisión del usuario. `KeyError` si esa versión no existe.
    """
    modelo = _buscar(session, proyecto_nombre, codigo_nuevo)
    items = list(modelo.items_computo)
    session.delete(modelo)
    for item in items:
        session.delete(item)
    session.flush()
```

En `core/budget/__init__.py:20`:

```python
from core.budget.actualizacion import (
    COLUMNAS_COMPARATIVO,
    Comparativo,
    actualizar_precios,
    descartar_version,
)
```

y `__all__` suma `"descartar_version"`.

- [ ] **Step 4: Verde, línea base, suite y lint**

Run: `uv run pytest tests/integration/test_actualizacion_precios.py tests/integration/test_api.py -q -W error --strict-markers && uv run pytest tests/unit/test_costing.py tests/integration/test_auditoria_7_de_7.py -q -W error && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: todo verde. Si SQLite rechaza el borrado por una clave foránea, el orden de borrado del *unit of work* no alcanzó. En ese caso, borrar primero los renglones (`for partida in list(modelo.partidas): session.delete(partida)`) y hacer `flush` antes de los ítems, sin tocar el esquema.

- [ ] **Step 5: Commit**

```bash
git add core/budget/actualizacion.py core/budget/__init__.py tests/integration/test_actualizacion_precios.py
git commit -m "fix(budget): descartar la version nueva de uc-02 conserva el registro de cambios" -m "Cierra INV-015 (7a) junto a las pruebas del commit anterior. Descartar sin confirmar deshacia tambien los CambioPrecio; ver expediente B.8." -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Registrar lo que C1 no cierra de 7a.** Agregar al final de §3 del inventario (siguiente ID libre):

```markdown
| INV-0NN | planificación de C1 (Tarea 13; expediente B.8) | ui (cruza: api, docs) | Trazabilidad (UC‑02 7a) | importante | `ui/paginas/actualizacion.py:207-223` (confirma siempre que hay cambios); `docs/ERS.md:170` («se marca como descartada») | La interfaz no ofrece descartar la versión nueva, y la ERS promete una marca que el modelo no tiene: la columna exigiría una migración, fuera del límite (spec §2). `core.budget.descartar_version` ya conserva el historial | Botón «Descartar versión» en la página de actualización que llame a `descartar_version` y confirme (C3); en la ERS, 7a dice «se elimina la versión nueva; el registro de cambios se conserva» (C4) | C3 (ui) + C4 (ERS) | abierto |
```

```bash
git add docs/auditoria/2026-09-inventario.md
git commit -m "docs(auditoria): la interfaz de uc-02 7a queda para c3 y la ers para c4" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: Compuerta GC1

**Files:**
- Modify: `docs/auditoria/2026-09-inventario.md` (estados)
- Modify: `docs/bitacora/2026-09-23-cierre.md` (sección GC1)

**Interfaces:**
- Consumes: Tareas 0 a 13.
- Produces: el veredicto de GC1 y, con permiso de Eugenio, el PR de C1 con la etiqueta `gc1`.

- [ ] **Step 1: Línea base y 7 de 7**

Run: `uv run pytest tests/unit/test_costing.py tests/unit/test_costing_destajo.py::test_la_linea_base_no_se_mueve tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61 tests/integration/test_auditoria_7_de_7.py tests/integration/test_composicion_extremo_a_extremo.py -q -W error --strict-markers`
Expected: verde: 1 586,61 USD y 7 de 7, afirmados contra `tests/fixtures/apu_linea_base.py`.

- [ ] **Step 2: Guardia de arquitectura**

Run: `uv run pytest tests/unit/test_arquitectura.py -q -W error --strict-markers`
Expected: verde, incluida `test_la_guardia_cubre_todo_paquete_de_primer_nivel_fuera_del_nucleo`.

- [ ] **Step 3: Contratos, capas y guardia del núcleo**

Run:

```bash
git diff --stat main -- core/contracts
git diff --stat main -- adapters ml
uv run python scripts/guardia_nucleo.py --base main
for c in $(git rev-list main..HEAD); do f=$(git show --name-only --format= "$c"); if echo "$f" | grep -q '^core/' && echo "$f" | grep -qE '^(adapters|ml|ui|api|scripts)/'; then echo "MEZCLA $c"; fi; done
```

Expected: los dos diff vacíos, la guardia con código 0 y ninguna línea `MEZCLA`.

- [ ] **Step 4: Suite completa, lint y salvaguarda activa**

Run: `uv run pytest -W error --strict-markers -q && uv run ruff check . && grep -n "_base_real_intacta" tests/conftest.py`
Expected: verde, limpio, y la fixture presente. Anotar el número de pruebas (`N1`) frente a `N0`.

- [ ] **Step 5: Estados del inventario.** Con `git log --format="%h %s" main..HEAD`, reemplazar la columna «Estado» de estas filas:
  - `cerrado (<hash>)`, con el commit que cierra cada una: INV‑065 (Tarea 2), INV‑010 (Tarea 1, paso 9), INV‑007 (Tarea 4, pasos 5 y 7: citar los dos), INV‑009 (Tarea 5), INV‑008 (Tarea 6), INV‑003 (Tarea 7), INV‑012 (Tarea 8), INV‑004 (Tarea 9), INV‑005 (Tarea 10), INV‑013 e INV‑069 (Tarea 11, commit del núcleo y los tres de llamadores), INV‑014 (Tarea 13, paso 1) e INV‑015 (Tarea 13, pasos 1 y 5).
  - INV‑011: `abierto: la parte de C1 cerrada en <hash RF‑19/UC‑04> y <hash RF‑20>; queda la subtarea documental de C4 (ERS §3.2 y plan_pruebas §8)`.
  - INV‑001, INV‑002 e INV‑006 conservan el estado de la Tarea 3.

  En el párrafo de conteos de §3 (`:48-56`), agregar al final: «La fase C1 agrega INV‑0NN a INV‑0MM (Tareas 1, 11, 12 y 13 del plan de C1) y cierra los hallazgos de su fase según esta columna.»

- [ ] **Step 6: Bitácora.** Agregar a la sección «Fase C1 — núcleo» de `docs/bitacora/2026-09-23-cierre.md`:
  - (a) La tabla de hallazgos de C1: ID → estado → commit.
  - (b) Los hallazgos nuevos (IDs y fase).
  - (c) Pruebas: `N0` → `N1`.
  - (d) La tabla de dictámenes siguiente.
  - (e) Los veredictos de los cuatro encargos (paso 7).
  - (f) La ejecución de la aplicación por Eugenio (paso 8).
  - (g) Las sesiones de redacción (fase Red) hechas durante C1, por la regla de reparto de la spec §2.
  - (h) La línea `**GC1: cruzada el AAAA‑MM‑DD.**`, con la fecha real.

```markdown
### Decisiones de C1 pendientes de ratificación

| # | Decisión | Motivo | Costo si es errónea | Ratificada por Eugenio |
|---|---|---|---|---|
| C1‑1 | INV‑012: una regla inevaluable es INFO «regla no evaluable», no ERROR; R2 y R7 sin plan se declaran «no aplicables» | Manda la ERS (RF‑23, UC‑05 2a y 3a); la prueba estaba alineada con el código y no con el requisito | Un presupuesto que era NO CUMPLE solo por una regla rota pasa a CUMPLE; revertir es cambiar tres severidades | |
| C1‑2 | INV‑013: el ítem sin partida queda pendiente, con un hallazgo `PENDIENTE` de severidad ERROR; `generar_presupuesto` sigue lanzando `ValueError` | Ruta sin contrato del inventario; un presupuesto incompleto no cumple | Si el tutor prefiere ADVERTENCIA, se cambia una severidad | |
| C1‑3 | INV‑069: el punto único es `elaborar(plan=función)`, no una función nueva; se migró también `scripts/generar_resultados_ml.py` | Un solo punto de entrada para un solo hecho; el quinto sitio repetía el protocolo | Ninguno en el resultado: las salidas son idénticas (Tarea 11, paso 9) | |
| C1‑4 | INV‑004: con precio anterior 0, la variación es 0 | La columna no admite nulo y cambiar el esquema es una migración | Un análisis de variaciones puede leer 0 donde no hay variación definida; `precio_anterior = 0` lo delata | |
| C1‑5 | INV‑005: la excepción única es `LookupError` y no `CatalogoIncompleto` | La API conserva el 404 de un recurso inexistente | Ninguno funcional | |
| C1‑6 | INV‑003: la validación va en el nodo de nombre y no en `_evaluar_binario` | Cubre también la expresión de un solo nombre; evita un `except` muerto | Ninguno | |
| C1‑7 | INV‑011: RF‑20 se implementa en `core/budget/diferencial.py` como corrección; los flujos 1a, 2a y 2b de UC‑04 pasan a C2 y C4 | RF‑20 existe en la ERS (spec §2); los flujos son de la capa de adaptadores | Si se juzga capacidad nueva, se revierte un commit y RF‑20 se declara sin cumplir | |
| C1‑8 | INV‑015: descartar borra la versión nueva en vez de marcarla | La marca exige una migración (spec §2) | La ERS dice «marca» hasta C4 | |
| C1‑9 | INV‑001, INV‑002 e INV‑006: aceptados por decisión de arquitectura registrada, pendientes del aval | Cambian contratos (spec §4); expedientes A.1 a A.3 | Si el tutor avala, se reabren y se corrigen antes de `v1.0-tesis` | |
| C1‑10 | INV‑008 se limita a las líneas citadas, más tres líneas de la misma aserción; INV‑009 hace exacto el factor de la tubería (7,8856 → 7,88542… m³ esperados en R5) | Alcance del inventario; un dato con dos precisiones | Quedan literales de la línea base en `test_persistencia.py` fuera del alcance | |
| C1‑11 | La tarea de expedientes va tercera y no al final | La respuesta del tutor es el camino crítico de F2 | Ninguno | |
| C1‑12 | Los hallazgos nuevos de C1 (`plan_secuencial` con códigos repetidos, UC‑01 3a en la interfaz y la API, flujos de UC‑04, UC‑02 7a en la interfaz) quedan abiertos en su fase; el de `plan_secuencial` se corrige en C1 solo si Eugenio lo decide aquí | Alcance de C1 fijado en GC0 | Si se decide corregirlo ahora, es una tarea más en `core/budget/curva.py` | |
```

- [ ] **Step 7: Los cuatro encargos, en paralelo y en segundo plano.** Una llamada `Agent` por encargo, las cuatro en el mismo mensaje, todas sobre `git diff main..HEAD` más la spec, el inventario y los expedientes. Cada prompt incluye:
  - El encargo y su norma:
    - requisitos: IEEE 830 y la ERS, con cada RF y UC tocado;
    - arquitectura: vistas 4+1 y `CLAUDE.md` §2, §5 y §9, verificando además la regla de capas del paso 3 y que ningún contrato cambió;
    - pruebas y calidad: IEEE 829 e ISO/IEC 25010, verificando los cinco puntos de **Review Focus** y que cada prueba nueva se observó en rojo o mordiendo;
    - verificación de hechos: abrir cada cita `archivo:línea` de los expedientes, del inventario y de la bitácora y confirmarla.
  - La instrucción de devolver **VEREDICTO** (aprueba / aprueba con correcciones / rechaza) y hallazgos con severidad, evidencia y corrección concreta.
  - La prohibición de editar archivos.

  Cada hallazgo bloqueante se corrige en un commit propio y se vuelve a pasar **solo** el encargo que lo levantó, hasta que los cuatro aprueben. Los hallazgos nuevos que no se corrijan en C1 van al inventario vivo.

- [ ] **Step 8: Eugenio ejecuta la aplicación y ratifica** (spec §6).
  - El guion ya está corregido (Tarea 2; condición de cierre de INV‑065).
  - Eugenio sigue `docs/guion_prueba_arenia.md` §4 con `data/prueba_arenia.db`, ejecuta CP‑05 y CP‑06 (el cambio principal: la elaboración con `plan=plan_secuencial` y el informe siempre presente) y comprueba al terminar que `data/apu.db` no cambió.
  - Después ratifica cada fila de la tabla del paso 6. Sin ratificación, la compuerta no se cruza.

- [ ] **Step 9: Commit**

```bash
git add docs/auditoria/2026-09-inventario.md docs/bitacora/2026-09-23-cierre.md
git commit -m "docs(bitacora): compuerta gc1 del cierre" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 10: Push y PR, solo con permiso expreso de Eugenio.**

Run: `git push -u origin inc/cierre-C1`, seguido de:

```bash
gh pr create --base main --title "Cierre de la tesis: fase C1 (nucleo)" --label gc1 --body "$(cat <<'EOF'
Fase C1 del plan de cierre: salvaguarda de data/apu.db, guardia de arquitectura sobre scripts y tests, INV-065 y los importantes de core sin cambio de contrato. INV-001, INV-002 e INV-006 quedan aceptados por decision de arquitectura registrada, pendientes del aval del tutor (expedientes en docs/bitacora/2026-09-23-C1-expedientes.md). Compuerta GC1 en docs/bitacora/2026-09-23-cierre.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Si la etiqueta `gc1` no existe, se crea con `gh label create gc1` (también con permiso).

Expected: `gh pr checks` muestra `ubuntu-latest` y `windows-latest` en verde. La fusión es con merge commit y la decide Eugenio (spec §6).

---

## Autorrevisión del plan

**Cobertura de los hallazgos de C1:**

| Hallazgo | Tarea | Cierre en C1 |
|---|---|---|
| INV‑065 (bloqueante) | 2 | completo, con sus cuatro partes y una prueba de texto |
| INV‑001 | 3 | aceptado (contrato), expediente A.1 |
| INV‑002 | 3 | aceptado (contrato), expediente A.2; su efecto sobre el informe lo cierra INV‑003 |
| INV‑003 | 7 | completo |
| INV‑004 | 9 | completo |
| INV‑005 | 10 | completo |
| INV‑006 | 3 | aceptado (contrato + subtarea C2), expediente A.3 |
| INV‑007 | 4 | completo |
| INV‑008 | 6 | completo en las líneas citadas |
| INV‑009 | 5 | completo |
| INV‑010 | 1 | completo |
| INV‑011 | 12 | RF‑19 con prueba, RF‑20 implementado, pasos 1‑5 de UC‑04 trazados; queda la subtarea de C4 |
| INV‑012 | 8 | completo |
| INV‑013 | 11 | completo en el núcleo por la ruta sin contrato |
| INV‑014 | 13 | completo |
| INV‑015 | 13 | completo en el núcleo (2b con prueba, 7a implementado) |
| INV‑069 | 11 | completo: núcleo más cinco llamadores en tres commits separados |
| Pendiente H2 de GC0 | 1, paso 10 | revisión de solo lectura |

**Lo que no se pudo planificar en concreto, y por qué:**

- **Hallazgos de la revisión H2 (Tarea 1, paso 10).** No se conocen hasta leer los archivos con el criterio de la capa `tests`. El plan da la lista de preguntas y el formato de fila, no el texto de filas que aún no existen.
- **Flujos 1a, 2a y 2b de UC‑04.** No tienen implementación y su lugar natural es `adapters/`, que C1 no puede tocar junto con `core/`. Se registran para C2 y C4 (Tarea 12, paso 7).
- **UC‑02 7a en la interfaz, y la «marca» de descartada.** La primera es de `ui/` (C3). La segunda exige una migración de esquema, fuera del límite de la spec §2 (Tarea 13, paso 6).
- **UC‑01 3a de punta a punta.** La interfaz y la API piden composiciones al catálogo, que lanza `KeyError` antes de llegar a `elaborar`, y la propuesta de tres partidas similares (UC‑03) es de `ui/` (Tarea 11, paso 11).
- **`plan_secuencial` con códigos repetidos.** Es un defecto de `core/` descubierto al planificar, no un hallazgo aprobado en GC0. Se reproduce y se registra (Tarea 11, paso 11), pero su corrección no se planifica: la decide Eugenio en GC1 (dictamen C1‑12).
- **Recuentos exactos de pruebas.** No se fijan: el plan manda anotar `N0` y `N1` y compararlos, en lugar de inventar cifras.

### Archivos críticos para la implementación

- `C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C1\core\budget\presupuesto.py`
- `C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C1\core\verification\reglas.py`
- `C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C1\core\verification\expresiones.py`
- `C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C1\tests\conftest.py`
- `C:\Users\euger\OneDrive\Escritorio\TESIS\.claude\worktrees\cierre-C1\docs\guion_prueba_arenia.md`
