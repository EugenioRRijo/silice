# Cierre de la tesis, fase C0 — inventario del repositorio y paquete para el tutor

> **Para trabajadores agénticos:** SUB-SKILL REQUERIDA: usa superpowers:subagent-driven-development
> (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos
> usan casillas (`- [ ]`) para seguimiento.

**Goal:** Producir el inventario vivo de hallazgos de todo el repositorio —capa, principio, severidad,
evidencia verificada, fase destino— con su tabla de cobertura y su propuesta de triage, y el paquete
de decisiones para el tutor académico designado; cruzar la compuerta **GC0**.

**Architecture:** C0 es de solo lectura sobre el código: no modifica `core/`, `adapters/`, `ml/`,
`api/`, `ui/`, `scripts/` ni `tests/`. Siete auditores por capa trabajan en paralelo sobre el mismo
commit y escriben cada uno un archivo parcial; un consolidador los une, deduplica los hallazgos que
cruzan capas y asigna identificadores; un verificador independiente confirma la evidencia de cada
bloqueante e importante; los cuatro encargos revisan el inventario; Eugenio lo aprueba en GC0.

**Tech Stack:** Markdown · git · `uv run pytest`/`ruff` solo como verificación de que nada cambió.

**Spec:** [docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md](../specs/2026-09-23-plan-cierre-tesis-design.md)
— §4 (criterios, severidad, estados, hallazgos que cruzan capas, triage) es **la** referencia de los
auditores; §5 fila C0 y GC0.

**Plan de fases:** [PLAN_CIERRE.md](../../../PLAN_CIERRE.md).

---

## Global Constraints

- **Solo lectura del código.** `git diff --stat main -- core adapters ml api ui scripts tests` vacío al
  cerrar C0. Los únicos archivos que C0 crea o cambia están en `docs/auditoria/`,
  `docs/tesis/revisiones/` y `docs/bitacora/`.
- **Todos los auditores trabajan sobre el mismo commit**, anotado en el inventario (`git rev-parse HEAD`
  al empezar la Tarea 3). Toda evidencia es `archivo:línea` sobre ese commit.
- **Criterios únicos:** spec §4. Ningún auditor inventa principios ni severidades fuera de ella.
- **Fuera del alcance del inventario, declarado:** `docs/fuentes/` (textos normativos de terceros),
  `docs/superpowers/` (specs y planes históricos, salvo la spec y los planes vigentes de UI y de cierre),
  `docs/bitacora/` (registros fechados: no se «corrigen»), `data/` (datos; se auditan solo los scripts
  que los generan) y `uv.lock`.
- **Las decisiones D1–D9 y las salvedades del dossier** (`docs/dossier_g0.md` §3 y §4) son riesgo ya
  rastreado: se citan, no se duplican como hallazgo (spec §4).
- Un hallazgo sin evidencia verificable no entra al inventario.
- Documentos y commits en español; commits Conventional Commits sin tildes en el asunto, con el trailer
  `Co-Authored-By` del modelo que los escribe.
- Un auditor no despacha subagentes, no hace commit y no hace push; el controlador hace los commits.

## Review Focus

1. **Falsos positivos.** Un auditor que marca como violación algo que es diseño declarado (las reglas en
   el núcleo, `CLAUDE.md` §7; los puntos de composición que enumeran dominios; los scripts de metas).
   La Tarea 5 verifica cada bloqueante e importante contra el código y la spec §4.
2. **Doble conteo.** El mismo hecho reportado por dos auditores (p. ej. el evaluador de expresiones,
   visto desde `core/` y desde `adapters/`). La Tarea 4 los funde en un solo hallazgo, asignado a la
   capa más baja.
3. **Cobertura aparente.** Un auditor que dice haber revisado una capa sin listar sus archivos. La tabla
   de cobertura se calcula contra `git ls-files`, no contra lo que el auditor declara.
4. **Severidad inflada o desinflada.** La Tarea 5 re‑clasifica según las reglas de la spec §4 y deja
   constancia de cada cambio.
5. **Decisiones del tutor como hallazgos.** D1–D9 no se re‑etiquetan.

---

## Mapa de archivos

| Archivo | Tarea | Responsabilidad |
|---|---|---|
| `docs/bitacora/2026-09-23-cierre.md` | 1, 6 | Bitácora del cierre y de GC0 |
| `docs/auditoria/2026-09-inventario.md` | 1, 4, 5 | El inventario vivo (fuente única del backlog del cierre) |
| `docs/auditoria/parciales/<grupo>.md` | 3 | Salida cruda de cada auditor; se conserva como evidencia |
| `docs/tesis/revisiones/2026-09-paquete-tutor.md` | 2 | Las decisiones que esperan al tutor académico designado |

---

### Task 0: Precondiciones (decisión de Eugenio)

- [ ] **Step 1:** Eugenio fusiona el PR #8 (`inc/PLAN-ui`) **con merge commit** y después el PR de
  `inc/PLAN-cierre` (spec, `PLAN_CIERRE.md` y este plan). El agente no fusiona sin su orden.
- [ ] **Step 2:** Crear el worktree de la fase desde `main` actualizado:

Run: `git -C <raíz> fetch origin && git -C <raíz> worktree add .claude/worktrees/cierre-C0 -b inc/cierre-C0 origin/main`
Expected: el worktree existe; `git log --oneline -1` es el merge del PR de `inc/PLAN-cierre`;
`ls PLAN_CIERRE.md docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md` existen.

- [ ] **Step 3:** Estado de partida verde, con todos los extras:

Run: `uv sync --locked --all-extras && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: verde. Anotar el recuento y el commit en la bitácora (Tarea 1).

---

### Task 1: Esqueleto del inventario y bitácora

**Files:** Create `docs/auditoria/2026-09-inventario.md`, `docs/bitacora/2026-09-23-cierre.md`

- [ ] **Step 1: Crear el inventario con esta estructura exacta:**

```markdown
# Inventario del cierre de la tesis

**Fuente única del backlog del cierre** ([spec, §4](../superpowers/specs/2026-09-23-plan-cierre-tesis-design.md)).
Inventario **vivo**: se agregan aquí los hallazgos que aparezcan después de C0 hasta la condición F3.

**Commit auditado:** `<sha>` · **Fecha:** <fecha> · **Estado:** borrador (C0) | aprobado en GC0 (<fecha>)

## 1. Cobertura por capa

| Capa | Archivos en el repositorio (`git ls-files`) | Archivos revisados | Cobertura | Auditor |
|---|---|---|---|---|

## 2. Riesgo ya rastreado (no se duplica como hallazgo)

Decisiones D1–D9 y salvedades de [docs/dossier_g0.md](../dossier_g0.md) §3 y §4, y AACE 18R‑97 frente a
56R‑08: se remite al [paquete para el tutor](../tesis/revisiones/2026-09-paquete-tutor.md).

## 3. Hallazgos

Estados: abierto · cerrado (commit) · aceptado por decisión de arquitectura registrada (solo contratos
sin aval del tutor, spec §4) · promovido (menor que Eugenio sube a corrección) · a limitaciones.

| ID | Capa | Principio | Severidad | Evidencia | Hallazgo | Corrección propuesta | Fase destino | Estado |
|---|---|---|---|---|---|---|---|---|

## 4. Propuesta de triage para GC0

## 5. Registro de cambios de severidad (Tarea 5)
```

- [ ] **Step 2: Crear la bitácora** con: fecha, rama, commit de partida, recuento de pruebas y corrida de
  CI de `main` (`gh run list --branch main --limit 1`), enlaces a la spec, `PLAN_CIERRE.md` y este plan,
  y una sección «Decisiones pendientes de ratificación» con la tabla de la metodología (decisión,
  motivo, costo si es errónea, ratificada por Eugenio).

- [ ] **Step 3: Commit**

```bash
git add docs/auditoria/2026-09-inventario.md docs/bitacora/2026-09-23-cierre.md
git commit -m "docs(auditoria): esqueleto del inventario vivo y bitacora del cierre" -m "Co-Authored-By: <modelo> <noreply@anthropic.com>"
```

---

### Task 2: Paquete para el tutor académico designado

**Files:** Create `docs/tesis/revisiones/2026-09-paquete-tutor.md`

- [ ] **Step 1: Redactar el paquete.** DRY: **no copia** el contenido de cada decisión; lo enlaza. Para
  cada punto, una fila con: identificador, pregunta concreta al tutor en una línea, opciones, la
  recomendación del proyecto si la hay, el lugar donde está desarrollada, qué fase del cierre depende
  de la respuesta y qué pasa si la rechaza (spec §1, párrafo de rechazo). Puntos:
  - **G0** (validación retroactiva: `docs/metodologia.md` §2.2 la pedía antes de I0.3; qué aprueba:
    `docs/dossier_g0.md` §1).
  - **D1 a D9**, uno por fila, desde `docs/dossier_g0.md` §3 (lee cada una para escribir su pregunta).
  - **AACE 18R‑97 frente a 56R‑08**, desde `docs/tesis/revisiones/R1-capitulo-2.md`.
  - **T2 y T3 del acta del capítulo I**, si siguen abiertos (léelo en `docs/tesis/revisiones/R1-capitulo-1.md`).
  - **Numeración de UC‑09 desde RF‑44** (`docs/ERS.md`, nota de la Sesión U0.1).

  Al final, un **modelo de constancia** que el tutor pueda firmar por punto (aprobado / aprobado con
  cambios / rechazado, observaciones, fecha), porque F2 exige constancia en `docs/tesis/revisiones/`.

- [ ] **Step 2: Verificar** que cada enlace resuelve y que cada decisión citada existe con ese número:
  `grep -n "^### D[1-9]" docs/dossier_g0.md`.

- [ ] **Step 3: Commit**

```bash
git add docs/tesis/revisiones/2026-09-paquete-tutor.md
git commit -m "docs(tesis): paquete de decisiones para el tutor academico designado" -m "Co-Authored-By: <modelo> <noreply@anthropic.com>"
```

---

### Task 3: Auditoría por capa — siete auditores en paralelo

**Files:** Create `docs/auditoria/parciales/{core,adaptadores-ml-api,ui,scripts,tests,docs-normativos,docs-tesis}.md`
(uno por auditor; los escribe el auditor, los commitea el controlador).

**Grupos** (cada uno con su lista exacta de archivos: `git ls-files <rutas>`):

| Grupo | Rutas | Modelo sugerido |
|---|---|---|
| `core` | `core/` | el más capaz |
| `adaptadores-ml-api` | `adapters/`, `ml/`, `api/` | estándar |
| `ui` | `ui/` | estándar |
| `scripts` | `scripts/` (los `meta_*.py` fuera del criterio S) | estándar |
| `tests` | `tests/` | el más capaz |
| `docs-normativos` | `docs/*.md` salvo `docs/tesis/`, `docs/bitacora/`, `docs/superpowers/`, `docs/fuentes/`; más `CLAUDE.md`, `README.md`, `PLAN_*.md` | el más capaz |
| `docs-tesis` | `docs/tesis/` | estándar |

- [ ] **Step 1: Fijar el commit auditado** (`git rev-parse HEAD`) y escribirlo en el inventario.

- [ ] **Step 2: Despachar los siete auditores en paralelo y en segundo plano**, en un solo mensaje, con
  este encargo común (sustituyendo `<grupo>`, `<rutas>` y `<commit>`):

```text
Encargo: AUDITOR DE LA CAPA <grupo> del repositorio de una tesis de ingeniería de sistemas (español).
Worktree: <ruta absoluta del worktree de C0>, commit <commit>. SOLO LECTURA del código: no edites nada
fuera de docs/auditoria/parciales/<grupo>.md, no hagas commit, no hagas push, no despaches subagentes.

Lee primero la spec docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md §4: sus principios,
severidades y reglas son los ÚNICOS que usas. Lee CLAUDE.md (§1, §2, §5, §7) y docs/metodologia.md §5.1
(fuentes únicas de verdad). Las decisiones D1–D9 de docs/dossier_g0.md son riesgo ya rastreado: no las
reportes como hallazgo.

Revisa TODOS los archivos de: git ls-files <rutas>. Para cada hallazgo, una fila:
| ID provisional (<grupo>-NN) | capa | principio | severidad | evidencia archivo:línea (sobre <commit>) | hallazgo en una frase | corrección propuesta | fase destino (C1 núcleo · C2 adapters/ml/api · C3 ui/scripts · C4 docs) |
Reglas: solo hallazgos con evidencia que puedas citar; si un hecho cruza capas, repórtalo igual y
marca «cruza: <otras capas>»; no infles la severidad (en duda, la menor); no reportes diseño declarado
como violación (reglas en el núcleo, puntos de composición declarados, scripts de metas).

Escribe docs/auditoria/parciales/<grupo>.md con: (1) la lista de archivos revisados, uno por línea;
(2) la tabla de hallazgos; (3) «Sin hallazgos» explícito por principio cuando no encontraste nada.
Responde en menos de 15 líneas: cuántos archivos revisaste de cuántos y cuántos hallazgos por severidad.
```

- [ ] **Step 3: Al recibir cada respuesta**, comprobar que su archivo parcial existe y que la lista de
  archivos revisados coincide con `git ls-files <rutas>` (`comm -3`). Si faltan archivos, reanudar al
  mismo auditor con la lista faltante.

- [ ] **Step 4: Commit de los parciales**

```bash
git add docs/auditoria/parciales/
git commit -m "docs(auditoria): informes parciales de los siete auditores por capa" -m "Co-Authored-By: <modelo> <noreply@anthropic.com>"
```

---

### Task 4: Consolidación del inventario

**Files:** Modify `docs/auditoria/2026-09-inventario.md`

- [ ] **Step 1: Cobertura.** Llenar la tabla §1 con `git ls-files <rutas> | wc -l` por capa y las listas
  de archivos revisados de cada parcial. Cobertura exigida: **100 % por capa** (GC0).
- [ ] **Step 2: Fundir.** Pasar todas las filas de los parciales a §3; fundir las que describen el mismo
  hecho (una sola fila, asignada a la **capa más baja que exige cambiar**, spec §4, con las subtareas por
  fase si cruza capas); asignar identificadores definitivos `INV-001…`, ordenados por severidad y luego
  por fase destino; estado inicial «abierto». Conservar en cada fila el ID provisional de origen.
- [ ] **Step 3: Propuesta de triage (§4 del inventario).** Tres listas: (a) bloqueantes e importantes →
  entran, por fase; (b) menores que el consolidador **propone** promover, con una línea de por qué;
  (c) el resto → limitaciones. Un conteo por fase y severidad.
- [ ] **Step 4: Commit**

```bash
git add docs/auditoria/2026-09-inventario.md
git commit -m "docs(auditoria): inventario consolidado con cobertura y propuesta de triage" -m "Co-Authored-By: <modelo> <noreply@anthropic.com>"
```

---

### Task 5: Verificación independiente de la evidencia

**Files:** Modify `docs/auditoria/2026-09-inventario.md` (§3 y §5)

- [ ] **Step 1:** Un verificador **distinto** de los auditores abre la evidencia de **cada** hallazgo
  bloqueante e importante y de una muestra de uno de cada cinco menores, y dictamina por fila:
  confirmado · severidad corregida (a cuál y por qué, según la regla de la spec §4) · falso positivo
  (por qué: diseño declarado, D1–D9, evidencia que no dice eso). Si la muestra de menores tiene más de
  un falso positivo, se verifican todos los menores.
- [ ] **Step 2:** Aplicar sus dictámenes: los falsos positivos salen de §3 y quedan listados en §5 con
  su motivo; los cambios de severidad se aplican y se registran en §5.
- [ ] **Step 3: Commit**

```bash
git add docs/auditoria/2026-09-inventario.md
git commit -m "docs(auditoria): evidencia verificada y severidades corregidas" -m "Co-Authored-By: <modelo> <noreply@anthropic.com>"
```

---

### Task 6: Compuerta GC0

**Files:** Modify `docs/bitacora/2026-09-23-cierre.md`, `docs/auditoria/2026-09-inventario.md`

- [ ] **Step 1: Nada cambió en el código**

Run: `git diff --stat main -- core adapters ml api ui scripts tests && uv run pytest -W error --strict-markers -q && uv run ruff check .`
Expected: el `diff` no imprime nada; suite y ruff verdes.

- [ ] **Step 2: Los cuatro encargos** (requisitos, arquitectura, pruebas y calidad, verificación de
  hechos), en paralelo y en segundo plano, revisan el inventario y el paquete del tutor: cobertura
  real, criterios de la spec §4 bien aplicados, severidades, falsos positivos restantes, hallazgos que
  falten en capas que conocen. VEREDICTO y hallazgos con severidad. Corregir y repasar hasta que los
  cuatro aprueben.
- [ ] **Step 3: Presentar a Eugenio** el resumen del inventario (conteo por fase y severidad), la
  propuesta de triage y las decisiones pendientes de ratificación. **Eugenio decide** qué menores
  promueve y ratifica; el agente no cierra GC0 sin su respuesta.
- [ ] **Step 4: Registrar** su decisión en el inventario (estado «aprobado en GC0», menores promovidos) y
  en la bitácora (`**GC0: cruzada el <fecha>.**`, ratificaciones).
- [ ] **Step 5: Commit, push y PR** (el push y el PR con permiso de Eugenio):

```bash
git add docs/auditoria/2026-09-inventario.md docs/bitacora/2026-09-23-cierre.md
git commit -m "docs(bitacora): compuerta gc0 del cierre" -m "Co-Authored-By: <modelo> <noreply@anthropic.com>"
git push -u origin inc/cierre-C0
gh pr create --base main --title "Cierre de la tesis, fase C0: inventario y paquete para el tutor"
```

  Tras la fusión, la etiqueta `gc0` sobre el merge y el plan detallado de C1 se escribe con el
  inventario aprobado.
