# Bitácora — Sprint de planificación del asistente de presupuestos (UC‑09)

**Fecha:** 2026‑09‑15 · **Rama:** `inc/PLAN-asistente` (worktree `.claude/worktrees/plan-asistente`),
apilada sobre `inc/CI-integracion-continua` · **Base:** etiqueta `a-base` = `66fb52a` · **Spec:**
`docs/superpowers/specs/2026-09-15-asistente-presupuestos-design.md` · **Plan ejecutable:**
`docs/superpowers/plans/2026-09-15-plan-asistente.md` · **Plan de fases:** `PLAN_ASISTENTE.md`

## Objetivo

El usuario pidió una IA que **arme presupuestos según las necesidades del usuario**, auditados con
los datos del proyecto y con los parámetros de MaPreX. Pidió también **no priorizar la
implementación**: primero un plan de desarrollo en worktree, con metas que auditen la primera fase,
y sesiones de escritura y de desarrollo que sigan Scrum‑Cascada y DRY.

**Resultado:** `PLAN_ASISTENTE.md` define 12 sesiones en 5 fases con 5 compuertas, y la meta
`scripts/meta_asistente.py` las audita por fase. `--hasta P` da **4/4 OK**; la meta completa da
4/12, con M3–M10 en PENDIENTE y ninguna en FALLA, que es el estado correcto antes de A0. **No se
escribió código del asistente.**

## Decisiones

Las tres decisiones del usuario (tipo de IA, red y datos, alcance de las sesiones) están
registradas en la spec §1 (DA‑1 a DA‑3), junto con la elección del enfoque A frente a Managed
Agents y a una llamada única con salida estructurada (spec §2). Esta bitácora no las repite.

## Proceso

1. **Clasificación arquitectural**, anunciada al usuario: caso de uso nuevo, paquete nuevo,
   dependencia externa y cambio de RNF‑08.
2. **Tres preguntas, de a una.** Tipo de IA → híbrido con compuerta; red → extra opcional
   declarado; sesiones → técnicos más tesis.
3. **El skill `claude-api` se leyó antes de proponer.** De ahí salen el modelo, el Tool Runner, la
   comprobación de `stop_reason` y los fallbacks ante un rechazo que registra la spec §3.3, marcados
   para reverificar en A2. La búsqueda de otros proveedores de modelos dio falsos positivos:
   «cohere» aparece dentro de «CoherenciaDimensional». El repo no usa ninguno.
4. **Diseño aprobado tal cual**, después spec, plan ejecutable y TDD de la meta.

## TDD de la meta

1. **RED:** `ImportError: cannot import name 'meta_asistente'`. **GREEN:** 21 pruebas puras sobre
   texto sintético. Ruff marcó 3 líneas largas, corregidas antes del commit.
2. **Prueba negativa sobre el plan real.** Quitar la línea de commit de la sesión A2.2 dio FALLA
   («sesion A2.2: falta Commit»). Quitar «GA‑datos» siguió en OK, porque la compuerta seguía
   **nombrada** en un prompt con guion ASCII: el chequeo era blando.
3. **RED:** «una compuerta mencionada solo en un prompt no cuenta» (1 falló, 21 pasaron).
   **GREEN:** cada compuerta debe aparecer como fila `| **GAx** …` de la tabla de compuertas; 22
   pruebas. Repetida sobre el plan real, quitar la fila de GA‑datos da FALLA («falta la compuerta
   GA-datos en la tabla de compuertas») aunque la mención siga en el prompt.

## Qué se creó

| Archivo | Contenido |
|---|---|
| `docs/superpowers/specs/2026-09-15-asistente-presupuestos-design.md` | Decisiones, enfoques, arquitectura, flujo de UC‑09, conjunto dorado, métricas propuestas, compuertas, meta y riesgos |
| `docs/superpowers/plans/2026-09-15-plan-asistente.md` | Las tres tareas de este sprint |
| `PLAN_ASISTENTE.md` | **Única copia** de fases, compuertas y sesiones. Cada sesión lleva Lecturas, prompt, **Cierre.** (DoD con la meta que pasa a OK), **Fuente única.** (DRY) y **Commit.** |
| `scripts/meta_asistente.py` | 12 metas (P, A0–A3 y dos transversales). Chequeos de contenido puros sobre texto; `--hasta <fase>`; M8 y M9 por `_evaluar` de `meta_alpha`; M11 y M12 importados de `meta_multidominio` |
| `tests/unit/test_meta_asistente.py` | 22 pruebas, sin disco, git, ruff ni pytest |
| etiqueta `a-base` | Punto de partida de la meta de núcleo intacto |

## Auditoría

`uv run python scripts/meta_asistente.py --hasta P` (salida 0):

```
M1  (P) PLAN_ASISTENTE.md con fases, compuertas y sesiones completas  OK  5 fases, 5 compuertas y 12 sesiones con cierre, fuente unica y commit
M2  (P) Spec de diseno del asistente                                  OK
M11 Nucleo intacto: git diff <base> --stat -- core/ vacio             OK
M12 ruff check . limpio                                               OK
RESULTADO: 4/4 metas OK
```

Meta completa (salida 1, esperada): M1, M2, M11 y M12 en OK. M3–M10 en PENDIENTE, cada una con
su evidencia: «la ERS todavia no declara UC-09», «falta docs/evaluacion_asistente.md»,
«PAQUETES_FUERA_DEL_NUCLEO todavia no incluye asistente», «falta
tests/integration/test_asistente_casos_dorados.py», etc. Ninguna en FALLA.

## Hallazgos

1. **`OrigenTipo` no registra que una cantidad la propuso la IA.** Alcanza para la cantidad (REGLA o
   MANUAL) sin tocar el contrato, pero la procedencia de la IA tiene que vivir en `asistente/`. Se
   declara como deuda en la sesión A0.2.
2. **Cualquier función con modelo de lenguaje contradice RNF‑08** tal como está escrito («no invoca
   servicios externos»). La decisión DA‑2 lo acota a un extra opcional, y la compuerta GA0 lo lleva
   al tutor con una degradación prevista si lo rechaza.
3. **Hoy el lado «entrenado» del híbrido no es viable** (G2: 5 / 40 / 4 / 9). El plan lo convierte
   en la compuerta GA‑datos, con una regla explícita: los borradores de la IA no cuentan como datos,
   para no entrenar un modelo con su propia salida.
4. **Una meta de contenido puede ser blanda aunque tenga pruebas.** Las pruebas sintéticas pasaban y
   aun así la mención suelta de una compuerta la daba por declarada. Lección para las metas
   siguientes: cada chequeo necesita también **una prueba negativa sobre el documento real**.
5. **Error de registro:** el commit `01e8f50` dice «pruebas propias (23)»; eran 21 (22 tras el
   endurecimiento). No se reescribió la historia; lo corrige el commit del endurecimiento y esta
   bitácora.

## Pendientes

- **Del tutor (GA0):** revisar UC‑09, el cambio de RNF‑08, la vista del asistente y el protocolo de
  evaluación cuando A0 esté escrita.
- **Del usuario:**
  - fusionar en orden los PR #1 (sprint multidominio), #2 (CI) y #3 (este plan);
  - aprobar el presupuesto de corridas reales antes de A3;
  - commitear la sesión de redacción pausada, requisito de A4.3.
- **En archivos vedados:** mencionar `asistente/` y `PLAN_ASISTENTE.md` en `CLAUDE.md` (§1 y §6) y
  en `README.md`.
- **Siguiente sesión:** A0.1 (ERS). Su *Definition of Ready* se cumple con este plan en su rama y
  `--hasta P` en OK.

## Estado final

- Suite completa antes del endurecimiento: **511 passed in 74,61 s** con `-W error`. Después del
  endurecimiento: las 50 pruebas de las tres metas en verde. La CI del PR corre la suite completa
  sobre el commit final.
- `uv run ruff check .`: limpio.
- `git diff a-base --stat -- core/`: **vacío**.
- `scripts/meta_asistente.py --hasta P`: **4/4 OK**.
