# Sprint R1 (capítulos I y II) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Borradores revisados de los capítulos I y II, con referencias APA 7 verificadas o marcadas,
lista de cotejo y actas del tutor, y una meta de 12 chequeos en OK.

**Architecture:** Los capítulos citan en autor‑año y la lista de referencias vive una sola vez en
`docs/tesis/referencias.md`. La meta `scripts/meta_redaccion.py` sigue el patrón de
`meta_asistente.py`: chequeos puros sobre texto con pruebas sintéticas **y** pruebas negativas
sobre los documentos reales.

**Tech Stack:** Markdown, Python 3.13, pytest, ruff; WebSearch/WebFetch para verificar referencias.

**Spec:** `docs/superpowers/specs/2026-09-15-sprint-r1-capitulos-design.md` (decisiones DR‑1…DR‑5,
criterios T1–T14 y sesiones).

## Global Constraints

- **DR‑1:** ningún APU ni presupuesto del repositorio se presenta como real; todos son didácticos o construidos.
- **APA 7.ª edición;** ninguna referencia se completa de memoria; lo no verificado queda «pendiente».
- **Voz impersonal;** BIM‑5D y sombra digital; «gemelo digital» solo en su delimitación.
- **Cifras del proyecto:** solo las de `plan_redaccion.md` §5.
- **Sin cambios de código** fuera de `scripts/meta_redaccion.py` y su prueba.
- **Cierre de cada sesión:** `uv run pytest -W error` verde, `uv run ruff check .` limpio y la meta de la sesión en OK.

---

### Task 1 (R1.0): Preparación

**Files:**
- Modify: `CLAUDE.md` (§1: naturaleza de los datos), `docs/tesis/plan_redaccion.md` (guion del cap. I y §IV‑5), `docs/tesis/capitulos/README.md`, `docs/linea_base.md`, `data/telecom/fuentes/README.md`, `data/samples/README.md`
- Create: `docs/tesis/rubrica_tutor.md` (hecho), `docs/tesis/referencias.md` (hecho), `scripts/meta_redaccion.py`, `tests/unit/test_meta_redaccion.py`

**Interfaces (meta):** funciones puras `-> tuple[Estado, str]`, un chequeo por meta:
- `evaluar_capitulo_1(texto)`: tabla `Capítulo | Estado | Última revisión` y encabezados `##` de planteamiento, formulación, objetivos, justificación, y alcance y delimitación (sin distinguir tildes).
- `evaluar_objetivos(texto)`: bajo objetivos, `### Variante A` y `### Variante B`; OE7 dentro de A y ausente de B.
- `evaluar_capitulo_2(texto)`: antecedentes con ámbito internacional, latinoamericano y nacional; bases teóricas; bases normativas; definición de términos.
- `evaluar_primera_persona(textos)`: sin «nosotros/as», «nuestro/a(s)», «hemos» ni verbos en -amos/-emos/-imos de la lista declarada; cita el capítulo y la línea.
- `evaluar_citas(textos, referencias)`: extrae citas narrativas «Apellido [et al.|y Apellido] (año|s.f.)» y parentéticas «(Apellido…, año)»; cada (primer apellido, año) debe existir en los encabezados `###` de `referencias.md`.
- `evaluar_pendientes(textos, referencias)`: toda cita de una referencia en estado «pendiente» va seguida, en la misma línea, de «[verificación pendiente]».
- `evaluar_datos_reales(textos)`: toda oración con «real(es)» o «ejecutad…» cerca de presupuesto, APU, obra, caso o datos contiene también un marcador de negación o limitación («no», «sin», «limitación», «futur», «pendiente», «ficticio», «didáctic», «ilustrativ»).
- `evaluar_gemelo_digital(texto_c1, texto_c2)`: «gemelo digital» solo bajo encabezados que contengan «gemelo», «sombra», «no comprende» o «definición de términos».
- `evaluar_rubrica(texto)`: filas `| **T1** |` … `| **T14** |`.
- `evaluar_acta(texto)`: filas `| T1 |` … `| T14 |` con veredicto en {cumple, cumple con observaciones, no cumple}; FALLA si falta un criterio o alguno está en «no cumple».
- `evaluar_naturaleza_datos(texto_claude)`: `CLAUDE.md` tiene «Naturaleza de los datos», menciona ARENAZA y declara los datos ficticios.
- CLI: `--json`. Un documento ausente da PENDIENTE; un documento presente que no cumple da FALLA.

- [x] **Step 1:** Corregir la naturaleza de los datos en los seis documentos (spec §3).
- [x] **Step 2 (RED):** `tests/unit/test_meta_redaccion.py`, con casos positivos y negativos sintéticos por función. Correr: `ImportError`.
- [x] **Step 3 (GREEN):** `scripts/meta_redaccion.py`; pruebas en verde; ruff limpio.
- [x] **Step 4:** Pruebas negativas sobre documentos reales: `evaluar_naturaleza_datos` sobre el `CLAUDE.md` anterior a la corrección (`git show r-base:CLAUDE.md`) debe dar FALLA, y `evaluar_rubrica` sobre la rúbrica sin T14 también.
- [ ] **Step 5:** Meta → R9 y R12 en OK, las demás en PENDIENTE. Commit `docs(tesis): preparacion del sprint r1 y naturaleza de los datos`.

### Tasks 2–8 (R1.1–R1.7)

Una tarea por sesión de la spec §7, con su contenido, cierre y commit. Cada sesión de redacción:
(1) lee la fuente indicada en `plan_redaccion.md` §3 y las Bases; (2) redacta con los criterios
T1–T14 a la vista; (3) corre la meta; (4) hace la prueba negativa de la meta que la sesión pone en
OK sobre el capítulo real (quitar una sección, agregar una primera persona, citar sin referencia);
(5) cierra la sesión con su commit. Las sesiones de revisión (R1.3, R1.7) aplican la lista de cotejo
en un acta con evidencia textual por criterio, y el tesista corrige antes de cerrar el acta.
