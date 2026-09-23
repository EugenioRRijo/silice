# Plan de cierre de la tesis: final, límite y corrección metodológica · diseño

**Fecha:** 2026‑09‑23 · **Rama:** `inc/PLAN-cierre` (worktree `.claude/worktrees/cierre`) · **Base:**
`inc/PLAN-ui` (`fe7a415`, PR #8 abierto), porque este plan se apoya en las reglas de metodología y en
`PLAN_UI.md` que ese PR agrega · **Plan que lo ejecuta:** `PLAN_CIERRE.md` — aún no escrito
**Decisiones de Eugenio que lo fundamentan (2026‑09‑23):** B y C condicionales como dice su spec;
inventario por auditoría de todo el repositorio; orden inventario → corrección → U1 → CP‑07 → B/C;
organización por capa (enfoque 1); el final y el límite forman parte del plan y **son el límite del
proyecto**.

El proyecto tiene el software casi completo y el documento a dos de cinco capítulos. La auditoría del
PR #7 mostró que el código puede pasar cinco compuertas con un requisito sin implementar (paso 1 de
UC‑11), que la ERS puede quedar desfasada un sprint entero y que casi toda la verificación la hace un
modelo revisando a otro. Este diseño no agrega capacidades: fija **dónde termina el proyecto**, qué
queda fuera, y cómo se corrige lo que ya existe con método y no por intuición.

---

## 1. El final (endpoint)

El proyecto de tesis **termina** cuando se cumplen, todas a la vez, estas cinco condiciones de salida.
Cada una es comprobable por un tercero.

| # | Condición | Cómo se comprueba |
|---|---|---|
| F1 | Cada objetivo específico (OE1–OE6, `docs/tesis/esqueleto_tesis.md` §2) tiene su producto verificable y su indicador medido | la matriz del esqueleto sin celdas vacías; indicador 3 (tiempo manual vs automatizado) cronometrado; RNF‑04 (juicio de 3–5 expertos, anexo A bloque A) y RNF‑10 (CP‑07, bloque B) registrados en `docs/calidad_iso25010.md` §4 |
| F2 | El tutor validó lo que el proyecto decidió sin él | acta o constancia en `docs/tesis/revisiones/` de: compuerta G0, D3 (variante A/B, OE7), D4 (FCAS 600 %), D9 (modalidad en el contrato), AACE 18R‑97 vs 56R‑08 |
| F3 | El software queda congelado en la etiqueta **`v1.0-tesis`** | CI verde en Linux y Windows sobre esa etiqueta; línea base 1 586,61 USD y 7 de 7; **cero** hallazgos bloqueantes o importantes abiertos en el backlog de R0; los menores declarados en el capítulo de limitaciones |
| F4 | El documento de tesis está completo | capítulos I–V, conclusiones e introducción según `docs/tesis/plan_redaccion.md`, aprobados con la lista de cotejo del tutor (`docs/tesis/rubrica_tutor.md`); toda cifra cita su corrida de CI o su medición |
| F5 | La trazabilidad cierra | cada paso de cada caso de uso cita su prueba o caso manual (regla de `docs/metodologia.md` §3.4), no solo UC‑12 |

Tras `v1.0-tesis` el código solo acepta correcciones que la defensa exija; cada una pasa por su propia
compuerta y re‑etiqueta (`v1.0.1-tesis`).

## 2. El límite

**Congelamiento del alcance funcional desde la aprobación de esta spec.** Hasta alcanzar el final no
entra ninguna capacidad nueva: solo corrección (R0–R4), la fase U1 ya especificada y, si su condición
se cumple, U2 y U3. Una capacidad nueva exige enmendar esta spec con la decisión escrita de Eugenio y
el visto bueno del tutor; sin eso, se registra como trabajo futuro.

**Fuera del límite, declarado como trabajo futuro** (capítulo de conclusiones y recomendaciones):

- El asistente de presupuestos con IA (UC‑09, `PLAN_ASISTENTE.md`): es un proyecto nuevo.
- Más dominios o recorridos por dominio: el multidominio ya demostró la hipótesis central.
- Un IFC exportado desde Revit o Bonsai: limitación declarada de la compuerta G1.
- Migraciones de esquema de base de datos.
- AREN.IA como producto de ARENAZA: camino posterior a la defensa, con su propio remoto (`arenia`).
- Los hallazgos menores que R0 no promueva.

**Regla de reparto** para que el documento deje de ir detrás del código: desde R1, **por cada sesión
de código hay al menos una de redacción**, empezando por el capítulo IV (el de menos dependencias).

## 3. Marco metodológico

Las cuatro disciplinas no compiten: cada una gobierna un nivel distinto.

| Disciplina | Gobierna | Cómo se aplica aquí |
|---|---|---|
| **Cascada** | el macro: fases en orden con compuertas | R0 → R1 → R2 → R3 → R4 → M → (U2 \| U3) → congelamiento; ninguna compuerta se cruza sin su criterio y la ratificación de Eugenio |
| **Scrum** | el micro: cada fase es un sprint | backlog tomado del inventario de R0; *Definition of Done* de `docs/metodologia.md` §3.4 (incluida documentación y trazabilidad por paso); revisión = los cuatro encargos de ingeniería de sistemas; retrospectiva = bitácora; un PR por fase |
| **SOLID** | la estructura del código | criterio de auditoría en R0 y de corrección en R1–R3 (§4) |
| **DRY** | los hechos | cada hecho en su fuente única (`docs/metodologia.md` §5.1); toda duplicación es hallazgo |

## 4. Criterios de auditoría (R0)

Cada hallazgo se etiqueta con **capa** (`core`, `adapters`, `ml`, `ui`, `scripts`, `api`, `tests`,
`docs`), **principio**, **severidad**, evidencia `archivo:línea` y corrección propuesta.

**Principios medidos:**

- **S — responsabilidad única.** Un módulo con más de una razón para cambiar (p. ej. una página que
  pinta, calcula y persiste). Señal: módulos de más de ~400 líneas o con lógica verificable dentro de
  `render()`.
- **O — abierto/cerrado.** Agregar un dominio o una regla no debe exigir modificar `core/` (hipótesis
  central; `tests/unit/test_arquitectura.py`).
- **L — sustitución.** Toda subclase de `AdaptadorDominio` y de `ReglaVerificacion` honra el contrato
  de su base (tipos, invariantes, trazabilidad de `origen_id`).
- **I — segregación de interfaces.** Los contratos de `core/contracts/` no obligan a depender de lo
  que no se usa.
- **D — inversión de dependencias.** `core/` no importa de `adapters/`, `ml/`, `ui/`, `api/` ni
  `scripts/`; las dependencias entre capas externas se declaran en `docs/arquitectura.md`.
- **DRY.** Un hecho repetido fuera de su fuente única.
- **Coherencia documental.** Un documento que contradice al código, a otro documento o a una cifra de
  CI.
- **Trazabilidad.** Un paso de caso de uso o un RF sin prueba; una prueba que no verifica lo que su RF
  dice.
- **Pruebas.** Aserciones vacías, aislamiento roto (`data/apu.db`), dependencia del orden o de la red.

**Severidad:**

- **Bloqueante** — resultado de cálculo incorrecto, pérdida de datos, violación de un contrato de
  `CLAUDE.md` §5 o de la hipótesis central.
- **Importante** — un requisito incumplido o no verificado, una contradicción documental que llegaría
  a la tesis, una violación SOLID/DRY que obliga a cambiar varias partes por un solo hecho.
- **Menor** — todo lo demás.

**Triage:** entran a las fases de corrección los bloqueantes y los importantes; los menores entran solo
si Eugenio los promueve al aprobar el backlog. El resto va al capítulo de limitaciones.

## 5. Fases, goal de cada una y compuerta

| Fase | Goal | Compuerta |
|---|---|---|
| **R0 — Inventario** | Backlog priorizado de hallazgos con evidencia, por capa, principio y severidad, en `docs/auditoria/2026-09-inventario.md`. Solo lectura. **En paralelo:** paquete para el tutor (G0, D3, D4, D9, AACE) | **GR0:** Eugenio aprueba el backlog y su triage |
| **R1 — Núcleo** | Los hallazgos de `core/` resueltos, cada uno con expediente previo en `docs/bitacora/` (como D9). Ningún commit mezcla `core/` con `adapters/` o `ml/`. Si un hallazgo exige cambiar un contrato de `core/contracts/`, espera el aval del tutor | **GR1:** línea base 1 586,61 y 7 de 7; `guardia_nucleo.py` en 0; CI verde; cuatro encargos aprueban |
| **R2 — Adaptadores y ML** | Los hallazgos de `adapters/` y `ml/` resueltos | **GR2:** `git diff --stat` sobre `core/` vacío en la fase; CI verde; cuatro encargos |
| **R3 — Interfaz, scripts y API** | Se ejecuta como **U1** de `PLAN_UI.md` (Tareas 6–13 del plan detallado, salvo CP‑07), ampliada con los hallazgos de `ui/`, `scripts/` y `api/` del backlog | **GR3 = GU1** sin CP‑07 |
| **R4 — Documentación y trazabilidad** | ERS, plan de pruebas, calidad, manuales y arquitectura coherentes con el código; trazabilidad por paso para **todos** los casos de uso (F5); cifras citadas a su corrida de CI | **GR4:** cero contradicciones detectadas por el verificador de hechos; matriz por paso completa |
| **M — Mediciones con personas** | CP‑07 (RNF‑10, dos escenarios), cronometraje del indicador 3 (observación estructurada), juicio de expertos de RNF‑04 | **GM:** los tres registrados con n, perfil y fecha, sin relajar criterios tras medir |
| **U2 — Enfoque B** | Solo si CP‑07 FALLA; alcance = puntos de detención registrados | GU2 de `PLAN_UI.md` |
| **U3 — Enfoque C** | Solo con decisión expresa de Eugenio | la que fije esa decisión |
| **Congelamiento** | Etiqueta `v1.0-tesis` | **F3** |
| **D — Documento** (transversal desde R1) | Capítulos IV → V → III → conclusiones → introducción, con la regla de reparto de §2 | **F4** |

El **final** se alcanza con F1–F5 cumplidas: no hay fase posterior.

## 6. Organización del trabajo

- **Un worktree y una rama por fase** (`inc/cierre-R0`, `inc/cierre-R1`, …) y **un PR por fase**,
  fusionado al cruzar su compuerta, con etiqueta de compuerta (`gr0`, `gr1`, …).
- **Subagentes:** un implementador por tarea; al cerrar la fase, los cuatro encargos de ingeniería de
  sistemas en paralelo (requisitos, arquitectura, pruebas y calidad, verificación de hechos), cuya
  aprobación es la compuerta.
- **Ratificación:** toda decisión que el agente tome durante la ejecución se registra con su costo si
  es errónea y Eugenio la ratifica en la compuerta; sin ratificación la compuerta no se cruza
  (`docs/metodologia.md` §6).
- **Validación humana primero** en las decisiones de fondo: el tutor (F2) y las mediciones con
  personas (M) no las sustituye ninguna revisión automática.

## 7. Riesgos y criterios de degradación

| Riesgo | Criterio |
|---|---|
| R0 encuentra más de lo que cabe | El triage de §4 manda: solo bloqueantes e importantes; si aun así no cabe, Eugenio prioriza en GR0 y lo que quede fuera va a limitaciones |
| El tutor no responde a tiempo | R2–R4 y la redacción siguen; R1 no toca contratos sin aval; F2 queda pendiente y **el final no se declara** sin él |
| No hay fecha de entrega fija | El plan se ordena por dependencias; al fijarse la fecha, cada fase recibe fecha límite en `PLAN_CIERRE.md` |
| Apilamiento de PR (esta rama sale de la del PR #8) | Fusionar el PR #8 antes que el de esta rama; si no, reasentar por merge |
| Una corrección toca `core/` y rompe la línea base | Se revierte; la línea base es intocable (`CLAUDE.md` §4) |

## 8. Qué este diseño NO hace

No agrega capacidades, no reabre la spec de la UI (B y C siguen condicionales), no cambia contratos de
`core/` sin expediente y aval, y no fija fechas: las fija la fecha de entrega cuando exista.
