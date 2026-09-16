# Plan del asistente de presupuestos (sprint de planificación) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar auditable la planificación del asistente de presupuestos con IA (UC‑09): una meta
por fases con pruebas propias y un `PLAN_ASISTENTE.md` cuyas sesiones cumplen la plantilla
Scrum‑Cascada‑DRY, con `--hasta P` en verde.

**Architecture:** `scripts/meta_asistente.py` sigue el patrón de `meta_multidominio.py`, pero cada
chequeo de contenido es una función pura sobre texto (probada sin disco) y `--hasta <fase>`
selecciona las metas de las fases alcanzadas. `PLAN_ASISTENTE.md` es la única copia del detalle de
fases, compuertas y sesiones.

**Tech Stack:** Python 3.13, pytest, ruff; `scripts/meta_alpha.py` y `scripts/meta_multidominio.py` (reutilizados).

**Spec:** `docs/superpowers/specs/2026-09-15-asistente-presupuestos-design.md`

## Global Constraints

- Sin código del asistente: esta sesión solo planifica (spec §1).
- `core/` intacto: `git diff a-base --stat -- core/` vacío.
- Vedados: `CLAUDE.md`, `README.md`, `docs/README.md`, `docs/linea_base.md`, `docs/tesis/**`.
- Sin cambios de dependencias.
- Código, docstrings y commits en español; identificadores y asuntos sin tildes; salidas de consola en ASCII.
- Cada tarea cierra con `uv run pytest -W error` verde y `uv run ruff check .` limpio.
- Worktree `.claude/worktrees/plan-asistente`, rama `inc/PLAN-asistente`; el PR #3 apunta a `inc/CI-integracion-continua`.

---

### Task 1: Meta auditada por fases (`scripts/meta_asistente.py`)

**Files:**
- Create: `scripts/meta_asistente.py`
- Test: `tests/unit/test_meta_asistente.py`

**Interfaces:**
- Consumes: `Estado`, `Fila`, `Meta`, `_evaluar(base, umbral, con_cobertura=..., metas=...)`, `_filas_a_json` y `render_tabla` de `scripts/meta_alpha.py`; `evaluar_m11_nucleo_intacto(base)` y `evaluar_m12_ruff()` de `scripts/meta_multidominio.py`.
- Produces: `FASES`, `FASE_DE`, `metas_hasta(fase) -> list[str]` y las funciones puras `evaluar_plan`, `evaluar_spec`, `evaluar_uc09`, `evaluar_rnf08`, `evaluar_arquitectura`, `evaluar_protocolo`, `evaluar_guardia_arquitectura` y `evaluar_resultados`, todas `-> tuple[Estado, str]`. También la CLI `--hasta {P,A0,A1,A2,A3} --json --base`. La Task 2 depende de lo que exige `evaluar_plan`: encabezados `## Fase A0`…`## Fase A4`, las compuertas GA0–GA3 y GA‑datos, y por sesión `### Sesión <id>` con `**Cierre.**`, `**Fuente única.**` y `**Commit.**`.

- [ ] **Step 1: Write the failing test** — `tests/unit/test_meta_asistente.py`: pruebas puras con texto sintético para `metas_hasta` (P, A0, fase desconocida), `evaluar_plan` (completo, sesión sin commit, sin GA‑datos, ausente), `evaluar_spec`, `evaluar_uc09` (sin UC‑09, con tres RF mezclando guion ASCII y `‑`, con dos RF), `evaluar_rnf08` (sin excepción, con extra `ia`, sin fila), `evaluar_arquitectura`, `evaluar_protocolo` (completo, falta un caso, ausente), `evaluar_guardia_arquitectura` (tupla actual, con `asistente`, sin constante) y `evaluar_resultados` (ausente, completo, sin tabla). Código completo en el archivo de prueba del commit de esta tarea.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -W error -p no:cacheprovider tests/unit/test_meta_asistente.py`
Expected: FAIL con `ImportError: cannot import name 'meta_asistente'`

- [ ] **Step 3: Write minimal implementation** — `scripts/meta_asistente.py` con las funciones de Interfaces. Reglas de cada evaluador:
  - `evaluar_plan`: PENDIENTE si no hay texto; FALLA si falta una fase, una compuerta, no hay sesiones o a una sesión le falta alguno de los tres elementos, citando la sesión; si no, OK.
  - `evaluar_spec(existe)`: OK o PENDIENTE.
  - `evaluar_uc09`: PENDIENTE si no hay texto o no existe el encabezado `#### UC‑09`; FALLA si menos de tres filas `| RF‑nn |` citan UC‑09; si no, OK.
  - `evaluar_rnf08`: FALLA si no hay fila RNF‑08; PENDIENTE si no menciona el extra `ia`; si no, OK.
  - `evaluar_arquitectura`: OK si hay un encabezado que nombre al asistente; si no, PENDIENTE.
  - `evaluar_protocolo`: PENDIENTE si no hay texto; FALLA si falta un caso dorado (línea base, ARENAZA, MNT‑001, SIS‑001) o la palabra «umbral»; si no, OK.
  - `evaluar_guardia_arquitectura`: FALLA si no hay texto o no aparece `PAQUETES_FUERA_DEL_NUCLEO`; PENDIENTE si `"asistente"` no está en la tupla; si no, OK.
  - `evaluar_resultados`: PENDIENTE si no hay texto; FALLA sin tabla o sin «G2»; si no, OK.
  - Los guiones aceptan ASCII `-` y el no separable `‑` (U+2011), como escriben los documentos del proyecto.
  - Las metas M8 y M9 corren por `_evaluar` con `Meta(tipo="pruebas")`, solo si están seleccionadas.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -W error -p no:cacheprovider tests/unit/test_meta_asistente.py tests/unit/test_meta_alpha.py tests/unit/test_meta_multidominio.py`
Expected: PASS

- [ ] **Step 5: Ensayo de la CLI** — `uv run python scripts/meta_asistente.py --hasta P` (esperado: M1 PENDIENTE porque el plan aún no existe, M2 OK, M11 OK, M12 OK; salida 1).

- [ ] **Step 6: Commit**

```bash
git add scripts/meta_asistente.py tests/unit/test_meta_asistente.py
git commit -m "feat(scripts): meta del plan del asistente auditada por fases"
```

---

### Task 2: `PLAN_ASISTENTE.md`

**Files:**
- Create: `PLAN_ASISTENTE.md`

**Interfaces:**
- Consumes: la estructura que exige `evaluar_plan` (Task 1); spec §3–§9.
- Produces: la única copia de fases, compuertas y sesiones; M1 en OK.

- [ ] **Step 1: Escribir el plan** con las secciones: Situación de partida (enlaza la spec, no la copia); Principios; Compuertas (GA0–GA3 y GA‑datos, con criterio y degradación); Fases A0–A4 con sus sesiones A0.1–A0.3, A1.1–A1.2, A2.1–A2.2, A3.1–A3.2 y A4.1–A4.3; Resumen del recorrido; Cómo se audita cada fase (`--hasta`). Cada sesión lleva **Lecturas**, un bloque de prompt, **Cierre.** (DoD con la meta que pasa a OK), **Fuente única.** (DRY) y **Commit.**
- [ ] **Step 2: Auditar** — `uv run python scripts/meta_asistente.py --hasta P` → 4/4 OK, salida 0; y la meta completa, con M3–M10 en PENDIENTE y ninguna en FALLA.
- [ ] **Step 3: Commit** — `git add PLAN_ASISTENTE.md && git commit -m "docs(plan): plan del asistente de presupuestos con fases auditadas"`

---

### Task 3: Cierre del sprint de planificación

**Files:**
- Create: `docs/bitacora/2026-09-15-PLAN-asistente.md`

- [ ] **Step 1: Bitácora** con decisiones DA‑1…DA‑3, hallazgo de procedencia en `OrigenTipo`, TDD de la meta, salida de `--hasta P` y de la meta completa, pendientes (GA0 con el tutor, sesión de redacción del usuario para A4.3, vedados).
- [ ] **Step 2: Suite + ruff + núcleo intacto**, commit `docs(bitacora): sprint de planificacion del asistente`, push y PR #3 contra `inc/CI-integracion-continua`; observar la CI hasta el verde.
