# Diseño — Sprint R1: capítulos I (El problema) y II (Marco teórico)

**Fecha:** 2026‑09‑15 · **Estado:** aprobado en conversación («apruebo», con la aclaración de que
los datos de APU existentes son ficticios) · **Rama:** `inc/tesis-cap1-2` (worktree
`.claude/worktrees/redaccion-cap1-2`), apilada sobre `inc/PLAN-asistente` (PR #3); base: etiqueta
`r-base` · **Autoridad:** [CLAUDE.md](../../../CLAUDE.md), guion y convenciones en
[plan_redaccion.md](../../tesis/plan_redaccion.md), estructura y matriz en
[esqueleto_tesis.md](../../tesis/esqueleto_tesis.md), insumo institucional en
`docs/fuentes/Bases_Anteproyecto_BIM5D_APU.docx`

## 1. Contexto y alcance

El usuario pidió desarrollar los capítulos I y II «como tesistas y organizadores de tutores
universitarios»: redactarlos con el rigor de un trabajo de grado y organizarlos como los revisaría
un tutor. El plan de redacción recomendaba otro orden (IV → V → III → II → I); empezar por I y II
es decisión del usuario y se registra en la bitácora del sprint.

**Alcance:** borradores revisados de `docs/tesis/capitulos/01-el-problema.md` y
`02-marco-teorico.md`; lista única de referencias APA 7 con verificación por entrada; lista de
cotejo del tutor; actas de revisión; meta auditable con pruebas; corrección de la naturaleza de los
datos en la fuente única y en los documentos de los que dependen los capítulos.

**Fuera de alcance:** capítulos III a VI e introducción; aprobación del tutor real (se declara
pendiente; las actas la facilitan); formato final en procesador de texto; la limpieza de las
afirmaciones «real» en documentos que no alimentan a los capítulos I y II (§3).

## 2. Decisiones

| # | Decisión | Elección |
|---|---|---|
| DR‑1 | Naturaleza de los datos | **Todos los APU y presupuestos del repositorio son ejercicios académicos ficticios** (clínica y ARENAZA), con contenido y formato representativos de la práctica venezolana; `MNT-001` y `SIS-001` son casos construidos. Ningún valor es real. Los listados MaPreX jul‑2026 y el tabulador CIV se tratan como referencias publicadas aportadas por el usuario (supuesto confirmable). En los capítulos, todos los casos son **didácticos**; la validación con presupuestos reales es una limitación declarada |
| DR‑2 | Objetivos (D3) | **Dos variantes** en el capítulo I: A con OE7 (extensibilidad multidominio) y B sin OE7 (resultado complementario de OE3). El tutor elige en G0 sin reescribir |
| DR‑3 | Norma | **APA 7.ª edición**; ajustable si la institución exige otra variante |
| DR‑4 | Espacio de trabajo | Worktree apilado; primer commit `14d253b` = la sesión de redacción pausada (diff idéntico verificado); `main` quedó limpio |
| DR‑5 | Roles | El **tesista** redacta; el **tutor** revisa con la lista de cotejo y deja acta criterio por criterio; el tesista corrige y responde cada observación |

## 3. Hallazgo que condiciona la redacción

Las Bases (§2.2) dicen «se auditó un presupuesto real», y el repositorio contiene **92 afirmaciones
«real/reales» sobre APU, presupuestos o ARENAZA en 25 archivos**. Con DR‑1 son inexactas.

- **Fuente única:** `CLAUDE.md` §1 pasa a declarar la naturaleza de **todos** los datos (Sesión R1.0).
- **Se corrigen en este sprint** los documentos que alimentan a los capítulos I y II:
  `docs/tesis/plan_redaccion.md`, `docs/tesis/capitulos/README.md`, `docs/linea_base.md`,
  `data/telecom/fuentes/README.md` y `data/samples/README.md`.
- **Se registran como tarea propia** (toca código, texto regenerado y CI): ERS, `PLAN_DESARROLLO.md`,
  `PLAN_MULTIDOMINIO.md`, manuales, protocolo de precios, el texto que genera
  `scripts/generar_resultados_ml.py`, la spec del asistente y docstrings de pruebas y módulos.
- **Las bitácoras históricas no se reescriben:** registran lo que se sabía en su fecha; la errata va
  en la bitácora de este sprint.

**Consecuencia para el argumento del capítulo I.** El planteamiento ya no puede decir «se auditó un
presupuesto real y se hallaron siete errores». Se reformula en dos planos: (1) la **literatura**
documenta el problema en la práctica (peso del cómputo en el tiempo del estimador, errores de
transcripción, falta de trazabilidad), siempre con citas verificadas; (2) los **casos didácticos**
muestran el **mecanismo**: siete patologías de trazabilidad que el procedimiento tradicional
permite y que ninguna revisión del presupuesto final detecta. La prevalencia en obras reales queda
como pregunta abierta y limitación.

## 4. Artefactos

| Archivo | Papel | Fuente única de |
|---|---|---|
| `docs/tesis/capitulos/01-el-problema.md` | capítulo I | planteamiento, formulación, objetivos (A y B), justificación, delimitación |
| `docs/tesis/capitulos/02-marco-teorico.md` | capítulo II | antecedentes, bases teóricas y normativas, términos |
| `docs/tesis/referencias.md` | lista APA 7 | cada referencia y su estado: **verificada** (con DOI, URL o repositorio consultado y fecha) o **pendiente** (con lo que falta) |
| `docs/tesis/rubrica_tutor.md` | lista de cotejo | los criterios de revisión y su escala |
| `docs/tesis/revisiones/R1-capitulo-1.md`, `R1-capitulo-2.md` | actas | cada criterio con veredicto, observación del tutor y respuesta del tesista |
| `scripts/meta_redaccion.py` + `tests/unit/test_meta_redaccion.py` | meta del sprint | los chequeos automáticos de §6 |
| `docs/bitacora/2026-09-15-sprint-r1-capitulos.md` | bitácora | decisiones, errata de datos, desviación del orden, pendientes |

Los capítulos **citan** en autor‑año y no llevan lista de referencias propia (DRY): la lista vive
solo en `referencias.md`. Las cifras del proyecto salen de la tabla de cifras citables de
`plan_redaccion.md` §5.

## 5. Lista de cotejo del tutor (criterios)

| Grupo | Criterios |
|---|---|
| **Estructura y coherencia** | T1 las secciones del guion están completas · T2 la pregunta principal, las secundarias, los objetivos y las fases se corresponden uno a uno (observación metodológica de las Bases §3.2) · T3 cada objetivo inicia con verbo en infinitivo, es alcanzable y tiene producto verificable |
| **Rigor y evidencia** | T4 toda afirmación sobre la práctica se apoya en literatura citada · T5 los casos del repositorio se presentan como didácticos y su alcance se declara · T6 las cifras del proyecto coinciden con la tabla de cifras citables · T7 cada antecedente dice qué aporta a este trabajo |
| **Citación (APA 7)** | T8 formato autor‑año en el texto · T9 toda cita tiene referencia y toda referencia se cita · T10 ninguna referencia pendiente se cita sin marca |
| **Redacción** | T11 voz impersonal, sin primera persona · T12 terminología: BIM‑5D y sombra digital; «gemelo digital» solo en su delimitación · T13 párrafos con una idea central y transiciones explícitas |
| **Delimitación** | T14 lo que no comprende la investigación está declarado (gemelo digital, digitalización de planos, evaluación financiera, generalización estadística, validación con datos reales) |

Escala por criterio: **cumple** · **cumple con observaciones** · **no cumple**. Un capítulo se
aprueba en revisión cuando ningún criterio queda en «no cumple» y cada observación tiene respuesta.

## 6. Meta auditable (`scripts/meta_redaccion.py`)

Mismo patrón que `meta_asistente.py`: chequeos puros sobre texto con pruebas propias y **prueba
negativa sobre el documento real** (lección del sprint de planificación).

| Meta | Qué comprueba |
|---|---|
| R1 | el capítulo I existe con su tabla de estado y las cinco secciones del guion |
| R2 | los objetivos del capítulo I están en dos variantes y solo la A contiene OE7 |
| R3 | el capítulo II existe con antecedentes en tres ámbitos, bases teóricas, bases normativas y definición de términos |
| R4 | ningún capítulo usa primera persona |
| R5 | toda cita autor‑año de los capítulos tiene entrada en `referencias.md` |
| R6 | ninguna referencia pendiente se cita sin la marca de verificación pendiente |
| R7 | ningún capítulo presenta como reales los APU o presupuestos del repositorio |
| R8 | «gemelo digital» aparece solo en la delimitación conceptual del capítulo II y en lo que no comprende el capítulo I |
| R9 | la lista de cotejo existe con los criterios T1–T14 |
| R10 | el acta del capítulo I cubre T1–T14 con veredicto y ninguno en «no cumple» |
| R11 | el acta del capítulo II cubre T1–T14 con veredicto y ninguno en «no cumple» |
| R12 | `CLAUDE.md` §1 declara la naturaleza de todos los datos e incluye ARENAZA |

## 7. Sesiones (Scrum dentro de la fase de redacción)

| Sesión | Contenido | Cierre (DoD) | Commit |
|---|---|---|---|
| R1.0 | naturaleza de los datos en `CLAUDE.md` §1 y documentos dependientes; lista de cotejo; referencias base desde las Bases §12 (todas **pendientes** hasta verificarse); meta con TDD | R9 y R12 en OK; meta con pruebas verdes | `docs(tesis): preparacion del sprint r1 y naturaleza de los datos` |
| R1.1 | cap. I: planteamiento (contexto, evidencia en dos planos, naturaleza del problema) y formulación | R1 parcial; R4, R5, R7 en OK | `docs(tesis): capitulo i planteamiento y formulacion` |
| R1.2 | cap. I: objetivos A y B, justificación y alcance y delimitación | R1, R2 en OK | `docs(tesis): capitulo i objetivos justificacion y delimitacion` |
| R1.3 | revisión del tutor del cap. I y correcciones | R10 en OK | `docs(tesis): revision del tutor del capitulo i` |
| R1.4 | cap. II: antecedentes; **verificación de cada referencia** en su fuente | referencias citadas verificadas o marcadas; R5, R6 en OK | `docs(tesis): capitulo ii antecedentes con referencias verificadas` |
| R1.5 | cap. II: bases teóricas (ciclo del proyecto, BIM‑5D y LOD, sombra frente a gemelo, estructura del APU, ML con datos escasos, NLP para partidas) | R8 en OK | `docs(tesis): capitulo ii bases teoricas` |
| R1.6 | cap. II: bases normativas (COVENIN 2000, convención colectiva con D4 como nota, AACE 18R‑97) y definición de términos | R3 en OK | `docs(tesis): capitulo ii bases normativas y terminos` |
| R1.7 | revisión del tutor del cap. II, tablero de capítulos, bitácora y PR | R11 en OK; meta 12/12 | `docs(tesis): revision del capitulo ii y cierre del sprint r1` |

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Una referencia no se puede verificar | queda **pendiente** con lo que falta y se cita con marca; nunca se completa de memoria |
| Con datos ficticios, el planteamiento pierde fuerza | argumento en dos planos (§3): la literatura sostiene la prevalencia; los casos, el mecanismo |
| D3 y D4 siguen sin decisión del tutor | objetivos en dos variantes; FCAS como «parámetro del caso de estudio» |
| El tutor real no comparte un criterio de la lista | las actas registran cada observación con su respuesta y se ajustan sin reescribir |
| Cifras de fuentes comerciales en el estado del arte | se citan solo con su fuente primaria o no se citan (advertencia del propio estado del arte) |
