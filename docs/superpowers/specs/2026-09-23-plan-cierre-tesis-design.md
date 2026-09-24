# Plan de cierre de la tesis: final, límite y corrección metodológica · diseño

**Fecha:** 2026‑09‑23 · **Rama:** `inc/PLAN-cierre` (worktree `.claude/worktrees/cierre`) · **Base:**
`inc/PLAN-ui` (`fe7a415`, PR #8 abierto), porque este plan se apoya en las reglas de metodología y en
`PLAN_UI.md` que ese PR agrega · **Plan que lo ejecuta:** `PLAN_CIERRE.md` — aún no escrito
**Decisiones de Eugenio que lo fundamentan (2026‑09‑23):** B y C condicionales como dice su spec;
inventario por auditoría de todo el repositorio; orden inventario → corrección → U1 → CP‑07 → B/C;
organización por capa; el final y el límite forman parte del plan y **son el límite del proyecto**.
**Revisado por los cuatro encargos** el 2026‑09‑23; la sección 10 deja constancia de qué cambió.

El proyecto tiene el software casi completo y el documento a dos de cinco capítulos. La auditoría del
PR #7 mostró que el código puede cruzar **tres compuertas** (GP0, GP1 y GP2,
`docs/bitacora/2026-09-16-sprint-prototipo.md`) con un requisito sin implementar —el paso 1 de
UC‑11—, que la ERS puede quedar desfasada un sprint entero y que casi toda la verificación la hace un
modelo revisando a otro. Este diseño no agrega capacidades: fija **dónde termina el proyecto**, qué
queda fuera, y cómo se corrige lo que ya existe con método y no por intuición.

**Nombres.** Para no chocar con las reglas R1–R7, las decisiones D1–D9, las metas M1–M12 ni el Sprint
R1 de capítulos, las fases de este plan se llaman **C0–C4** (corrección), **Med** (mediciones con
personas) y **Red** (redacción).

---

## 1. El final (endpoint)

El proyecto de tesis **termina** cuando se cumplen, todas a la vez, estas cinco condiciones de salida.
Cada una es comprobable por un tercero.

| # | Condición | Cómo se comprueba |
|---|---|---|
| F1 | Cada objetivo tiene su producto y cada indicador está medido | cada fila de la matriz de `docs/tesis/esqueleto_tesis.md` §2 —incluidas la fila transversal y OE7 si el tutor elige la variante A de D3— tiene su producto en el repositorio; **cada indicador 1–5** (`docs/metodologia.md` §8) tiene valor, fecha y fuente (corrida de CI o registro de medición) en el capítulo V y en `docs/tesis/plan_redaccion.md` §5; `docs/calidad_iso25010.md` §9 sin ningún veredicto *pendiente*, y todo veredicto *parcial* (hoy RNF‑09) declarado en el capítulo de limitaciones |
| F2 | El tutor académico designado validó lo que el proyecto decidió sin él | constancia en `docs/tesis/revisiones/` de: la compuerta G0 (validación **retroactiva**: `docs/metodologia.md` §2.2 la pedía antes de I0.3), **todas** las decisiones D1–D9 de `docs/dossier_g0.md` §3 y la elección AACE 18R‑97 frente a 56R‑08 (`docs/tesis/revisiones/R1-capitulo-2.md`) |
| F3 | El software queda congelado en la etiqueta **`v1.0-tesis`** | la etiqueta se pone sobre un commit de `main` cuya corrida de CI (Linux y Windows) está verde y se cita por su enlace —la CI no corre sobre etiquetas (`.github/workflows/ci.yml`)—; línea base 1 586,61 USD y 7 de 7; **cero** hallazgos bloqueantes o importantes abiertos en el inventario vivo (§4); la única excepción son los *aceptados por decisión de arquitectura registrada*, estado restringido por §4 a los hallazgos cuyo cierre exige cambiar un contrato y cuyo aval del tutor está pendiente o fue negado, cada uno declarado con su expediente en el capítulo de limitaciones; los menores, en ese mismo capítulo |
| F4 | El documento de tesis está completo | capítulos I–V, conclusiones e introducción según `docs/tesis/plan_redaccion.md`; por capítulo, **el acta** con la lista de cotejo de `docs/tesis/rubrica_tutor.md` sin ningún «no cumple» **y la constancia del tutor académico designado**, que la rúbrica no sustituye; toda cifra cita su corrida de CI o su medición |
| F5 | La trazabilidad cierra | `docs/plan_pruebas.md` §8 contiene la matriz por paso de **todos** los casos de uso (ampliando la §8.1 de UC‑12): cada paso y cada flujo alternativo cita su prueba o caso manual, en verde o registrado |

**Si el tutor rechaza una decisión (F2):** se abre un expediente en `docs/bitacora/` y la corrección
entra como hallazgo del inventario en la fase de su capa (D4 o D9 → C1). La línea base (`CLAUDE.md` §2,
principio 5, y §4) **solo cambia por decisión escrita del tutor**, con expediente previo.

Tras `v1.0-tesis` el código solo acepta correcciones que la defensa exija; cada una pasa por su propia
compuerta y re‑etiqueta (`v1.0.1-tesis`).

## 2. El límite

**Congelamiento del alcance funcional desde la aprobación de esta spec.** Hasta alcanzar el final no
entra ninguna capacidad nueva. La regla es operativa:

- **Corrección** es un cambio que cierra un hallazgo del inventario aprobado en GC0 y apunta a un RF,
  RNF, contrato o documento **que ya existe**.
- **Capacidad nueva** es todo lo que agregue un caso de uso, un RF, un RNF, una pantalla o una ruta de
  API que no estén en la ERS vigente al aprobar esta spec. La fase U1 ya especificada y, si su condición
  se cumple, U2 y U3 **no** son capacidad nueva: están en la ERS (UC‑12) y en `PLAN_UI.md`.
- **En duda**, se registra en la bitácora y decide Eugenio en la compuerta siguiente.
- Una capacidad nueva exige enmendar esta spec con la decisión escrita de Eugenio y el visto bueno del
  tutor; sin eso, se registra como trabajo futuro.

**Fuera del límite, declarado como trabajo futuro** (capítulo de conclusiones y recomendaciones):

- El asistente de presupuestos con IA (UC‑09, `PLAN_ASISTENTE.md`): es un proyecto nuevo.
- Más dominios o recorridos por dominio: el multidominio ya demostró la hipótesis central.
- Un IFC exportado desde Revit o Bonsai: limitación declarada de la compuerta G1 (RNF‑09 *parcial*).
- Migraciones de esquema de base de datos.
- AREN.IA como producto de ARENAZA: camino posterior a la defensa, con su propio remoto (`arenia`).
- Los hallazgos menores que el inventario no promueva.

**Regla de reparto** para que el documento deje de ir detrás del código: desde C1, **por cada sesión
de código hay al menos una de redacción** (fase Red).

## 3. Marco metodológico

Las cuatro disciplinas no compiten: cada una gobierna un nivel distinto.

| Disciplina | Gobierna | Cómo se aplica aquí |
|---|---|---|
| **Cascada** | el macro: fases en orden con compuertas | C0 → C1 → C2 → C3 → C4 → Med → (U2 \| U3) → congelamiento; Red en paralelo desde C1; ninguna compuerta se cruza sin su criterio y la ratificación de Eugenio |
| **Scrum** | el micro: cada fase es un sprint | backlog tomado del inventario; *Definition of Done* de `docs/metodologia.md` §3.4 (incluidas documentación y trazabilidad por paso); revisión = los cuatro encargos de ingeniería de sistemas; retrospectiva = bitácora; un PR por fase |
| **SOLID** | la estructura del código | criterio de auditoría en C0 y de corrección en C1–C3 (§4) |
| **DRY** | los hechos | cada hecho en su fuente única (`docs/metodologia.md` §5.1); toda duplicación es hallazgo |

## 4. Criterios de auditoría e inventario vivo

El inventario vive en `docs/auditoria/2026-09-inventario.md` y es **el backlog de todo el cierre**,
no una foto de C0: los hallazgos que aparezcan después (revisiones de fase, Med) se agregan ahí hasta
F3. Cada hallazgo lleva **capa** (`core`, `adapters`, `ml`, `api`, `ui`, `scripts`, `tests`, `docs`),
**principio**, **severidad**, evidencia `archivo:línea`, corrección propuesta, **fase destino** y
**estado** (abierto, cerrado, aceptado por decisión de arquitectura registrada, promovido o descartado
a limitaciones). Las decisiones ya elevadas al tutor (D1–D9 y las salvedades de `docs/dossier_g0.md`
§4) se referencian como **riesgo ya rastreado**, no como hallazgo nuevo, salvo que el inventario
encuentre algo que el dossier no capturó.

**Principios propios del proyecto** (`CLAUDE.md` §2 y §5), los primeros que se miden:

- `Decimal` en todo lo monetario y dimensional, nunca `float` (principio 3) — **bloqueante** si se viola.
- El motor de costos es una función pura (principio 4) — **bloqueante** si se viola.
- El informe de auditoría se genera siempre (principio 7).
- Los contratos de `core/contracts/` son inmutables y validan sus invariantes en `__post_init__` (§5).

**SOLID, aplicado a este sistema:**

- **S — responsabilidad única.** Evidencia: un módulo que importa a la vez Streamlit y
  `sqlalchemy.orm`, o Streamlit y `core.costing`, o que tiene más de una razón de cambio nombrada (p. ej.
  pinta, calcula y persiste). El tamaño (~400 líneas) **solo sirve para elegir qué revisar**, nunca
  como evidencia. Los scripts de metas de sprint (`scripts/meta_*.py`) quedan fuera de este criterio.
- **O — abierto/cerrado, para los dominios.** Agregar un dominio no exige modificar `core/` (hipótesis
  central, `CLAUDE.md` §1). Las reglas de verificación viven en el núcleo por diseño (`CLAUDE.md` §7):
  para ellas se exige solo que una regla nueva no obligue a modificar las otras ni el motor. Los puntos
  de composición fuera de `core/` que enumeran dominios (p. ej. `ui/paginas/elaborar.py`, los
  sembradores) se **declaran** en `docs/arquitectura.md`; no son violación.
- **L — sustitución.** Toda subclase de `AdaptadorDominio` y de `ReglaVerificacion` honra el contrato de
  su base (tipos, invariantes, trazabilidad de `origen_id`).
- **I — segregación de interfaces.** Los contratos no obligan a depender de lo que no se usa.
- **D — regla de dependencia entre capas.** `core/` no importa de `adapters/`, `ml/`, `ui/`, `api/` ni
  `scripts/`; toda dependencia entre capas externas se declara en `docs/arquitectura.md`. La
  **inversión de dependencias** en sentido estricto (un módulo de `core/` que depende de una
  implementación concreta, p. ej. pandas o SQLAlchemy) se registra como hallazgo **menor**, salvo que
  impida probar el módulo.

**Otros principios:** DRY; coherencia documental (un documento que contradice al código, a otro
documento o a una cifra de CI); trazabilidad (un paso de caso de uso o un RF sin prueba, o una prueba
que no verifica lo que su RF dice); pruebas (aserciones vacías, aislamiento roto, dependencia del orden
o de la red).

**Severidad:**

- **Bloqueante** — resultado de cálculo incorrecto, pérdida de datos, violación de los principios 3 o 4,
  de un contrato de `CLAUDE.md` §5 o de la hipótesis central.
- **Importante** — un requisito incumplido o no verificado; una contradicción documental que llegaría a
  la tesis; una violación SOLID/DRY que obliga a cambiar varias partes por un solo hecho. **Por
  defecto**, todo hallazgo de trazabilidad o de pruebas es importante; una prueba que escribe en
  `data/apu.db` es bloqueante (pérdida de datos).
- **Menor** — todo lo demás.

**Hallazgos que cruzan capas** (p. ej. el evaluador de expresiones, hoy en cinco copias: el núcleo y
los cuatro adaptadores): se asignan a **la capa más baja que exige cambiar** y se parten en subtareas
por fase —el contrato en C1, la migración de los adaptadores en C2—, porque la guardia prohíbe mezclar
`core/` con `adapters/` o `ml/` en un commit. El PR de C1 puede ajustar a quienes llaman desde `ui/`,
`scripts/` o `api/`, en commits separados. Si la corrección exige cambiar un contrato de
`core/contracts/`, espera el aval del tutor; mientras tanto, el hallazgo puede quedar **aceptado por
decisión de arquitectura registrada** (con su expediente), estado que no bloquea F3. Ese estado es
**exclusivo** de los hallazgos cuyo cierre exige cambiar un contrato de `core/contracts/` y cuyo aval
del tutor está pendiente o fue negado; ningún otro hallazgo puede declararse aceptado. Si el tutor da el
aval antes de `v1.0-tesis`, el hallazgo vuelve a quedar abierto y se corrige.

**Triage:** entran a las fases de corrección los bloqueantes y los importantes; los menores, solo si
Eugenio los promueve al aprobar el inventario. El resto va al capítulo de limitaciones.

## 5. Fases, goal de cada una y compuerta

| Fase | Goal | Compuerta |
|---|---|---|
| **C0 — Inventario** | Inventario con evidencia por capa, principio y severidad, con una **tabla de cobertura por capa** (archivos revisados sobre totales). Solo lectura. **En paralelo:** el paquete para el tutor (F2) | **GC0:** cobertura completa de todas las capas; Eugenio aprueba el inventario y su triage |
| **C1 — Núcleo** | Primero, la salvaguarda de aislamiento de `data/apu.db` (Tarea 6, paso 3, del plan de UI, que solo toca `tests/`) y la ampliación de la guardia de `tests/unit/test_arquitectura.py` a `scripts/`. Después, los hallazgos de `core/`, cada uno con expediente previo en `docs/bitacora/`; ningún commit mezcla `core/` con `adapters/` o `ml/` | **GC1:** línea base 1 586,61 y 7 de 7; `tests/unit/test_arquitectura.py` verde; CI verde; contratos cambiados solo con aval del tutor; cuatro encargos aprueban |
| **C2 — Adaptadores, ML y API** | Los hallazgos de `adapters/`, `ml/` y `api/`, incluida la migración de los adaptadores de un contrato nuevo de C1 | **GC2:** `git diff --stat $(git merge-base main HEAD)..HEAD -- core/` vacío, anotado en la bitácora; CI verde; cuatro encargos |
| **C3 — Interfaz y scripts** | Se ejecuta como **U1** de `PLAN_UI.md` (Tareas 7–12 del plan detallado; la 6 pasó a C1 y la 13 se parte, ver abajo), ampliada con los hallazgos de `ui/` y `scripts/`. Si el inventario propone dividir `ui/paginas/componer.py` por el criterio S, esa extracción la hace **la Tarea 11 y nadie más**. C3 tiene **dos excepciones** a «`core/` sin cambios», cada una en un commit propio de `core/`, con expediente previo en `docs/bitacora/`, sin mezclar capas (sus llamadores de `api/` y `ui/` van en commits separados) y con la línea base (1 586,61 y 7 de 7) intacta: **INV‑080** (la recarga del informe pierde los pendientes), un commit de `core/budget/` derivado de un hallazgo posterior a C1; e **INV‑015 7a** (descartar la versión revalorada, `docs/ERS.md:170`), un commit con la tabla aditiva `descarte_version` en `core/models/`, `descartar_version` en `core/budget/actualizacion.py` (exportada en `core/budget/__init__.py`) y el docstring de `core/catalog/sesion.py`; el botón, en un commit de `ui/`. Enmiendas autorizadas por Eugenio el 2026‑09‑24 (§10) | **GC3 = GU1a** (ver enmienda), más, para esos dos commits, el expediente previo y la línea base intacta |
| **C4 — Documentación, trazabilidad e instrumentos** | ERS, plan de pruebas, calidad, manuales y arquitectura coherentes con el código; matriz por paso de **todos** los casos de uso (F5); cifras citadas a su corrida de CI; y, **antes de medir**, los protocolos de Med: el del indicador 3 (tarea de referencia, definición operacional de «manual», participantes que no sean el autor, n, orden y contrabalanceo, registro con commit probado) y el del juicio de expertos de RNF‑04 (n ≥ 3, perfil, versión del informe y commit), con enmienda de `docs/tesis/plan_redaccion.md` §5, que hoy deja el indicador 3 para la defensa | **GC4:** un **artefacto revisable por un tercero**: una lista de cotejo por documento (cada cifra con su corrida de CI) y la matriz por paso completa; el verificador de hechos es revisor, no criterio; cuatro encargos |
| **Med — Mediciones con personas** | CP‑07 (RNF‑10, dos escenarios), el indicador 3 y el juicio de expertos de RNF‑04, cada uno con su protocolo de C4; participantes y expertos sin relación personal con Eugenio, declarado en el registro; cada medición registra el commit probado | **GM = GU1b** para CP‑07, más: los tres registrados con n, perfil, fecha y commit; resultados incorporados a `calidad_iso25010.md` §4/§9, a la ERS y a `plan_redaccion.md` §5 sin contradicciones (la lista de cotejo de GC4). **Ningún criterio se relaja tras medir:** la revisión de umbrales que prevé el guion de CP‑07 aplica solo a ejecuciones futuras, nunca al escenario ya medido |
| **U2 — Enfoque B** | Solo si CP‑07 FALLA; alcance = puntos de detención registrados | GU2 de `PLAN_UI.md`, **más una nueva pasada de la lista de cotejo de GC4** sobre lo que U2 cambie |
| **U3 — Enfoque C** | Solo con decisión expresa de Eugenio | GU1a por defecto, salvo que esa decisión fije otra |
| **Congelamiento** | Etiqueta `v1.0-tesis` | **F3** |
| **Red — Redacción** (transversal desde C1) | Capítulos IV → V → III → conclusiones → introducción → **I (ajuste tras D3)**, con la regla de reparto de §2 | **F4** |

El **final** se alcanza con F1–F5 cumplidas: no hay fase posterior.

**Enmienda a `PLAN_UI.md`, a su spec y a su plan detallado.** Esta spec **enmienda** la compuerta GU1:
se parte en **GU1a** (U1 completa sin CP‑07: línea base, suite verde en ambos sistemas, salvaguarda,
`core/` sin cambios salvo los dos commits que autoriza la fila C3: INV‑080 e INV‑015 7a (§10, enmiendas del
2026‑09‑24), cuatro encargos) y **GU1b** (CP‑07 ejecutado y registrado, en Med). También mueve
la Tarea 6, paso 3 (la salvaguarda) a C1, y la restricción global del plan detallado sobre `api/` deja
de aplicar a C2. **El primer commit de `inc/cierre-C3`, antes de la Tarea 7,** ajusta `PLAN_UI.md` y el
plan detallado: Tareas 6 y 13 (la salvaguarda ya existe desde C1, CP‑07 sale de la Tarea 13 a Med), la
rama `inc/cierre-C3`, la compuerta GU1a y la restricción global sobre `api/`. C4 actualiza solo los
documentos derivados: la ERS (correspondencia RNF‑10 → GU1b) y `docs/calidad_iso25010.md` §4/§9. Fuera
de eso, la spec de la UI no se reabre: B y C siguen condicionales.

## 6. Organización del trabajo

- **Ramas sin apilar.** Antes de abrir la rama de C0 se fusiona el PR #8 **con merge commit** (no
  squash) y después el PR de esta spec (`inc/PLAN-cierre`). Cada fase abre su rama **desde `main`**
  (`inc/cierre-C0`, `inc/cierre-C1`, …) después de fusionar la anterior; nunca apilada. U1 vive solo en
  `inc/cierre-C3`: el plan detallado se ajusta en el primer commit de esa rama (§5, enmienda).
- **Un PR por fase**, fusionado al cruzar su compuerta, con etiqueta de compuerta (`gc0`, `gc1`, …).
- **Subagentes:** un implementador por tarea; al cerrar la fase, los cuatro encargos de ingeniería de
  sistemas en paralelo (requisitos, arquitectura, pruebas y calidad, verificación de hechos).
- **Ratificación humana en cada compuerta:** Eugenio revisa el resumen de cambios de la fase y ratifica
  las decisiones que el agente haya tomado, cada una con su costo si es errónea (`docs/metodologia.md`
  §6); sin ratificación la compuerta no se cruza. En las fases de código, además, ejecuta la aplicación
  una vez sobre el cambio principal antes de ratificar.
- **Validación humana primero** en las decisiones de fondo: el tutor (F2) y las mediciones con personas
  (Med) no las sustituye ninguna revisión automática.

## 7. Riesgos y criterios de degradación

| Riesgo | Criterio |
|---|---|
| C0 encuentra más de lo que cabe | El triage de §4 manda: solo bloqueantes e importantes; si aun así no cabe, Eugenio prioriza en GC0 y lo que quede fuera va a limitaciones |
| El tutor no responde a tiempo | C2–C4 y Red siguen; C1 no toca contratos sin aval (los hallazgos afectados quedan *aceptados por decisión de arquitectura registrada*); F2 queda pendiente y **el final no se declara** sin él |
| No hay fecha de entrega fija | El plan se ordena por dependencias; al fijarse la fecha, cada fase recibe fecha límite en `PLAN_CIERRE.md` |
| Los revisores comparten puntos ciegos | Ratificación humana en cada compuerta (§6) y validación del tutor y de personas en lo de fondo |
| Una corrección toca `core/` y rompe la línea base | Se revierte; la línea base no cambia salvo decisión escrita del tutor (§1) |

## 8. Qué este diseño NO hace

No agrega capacidades; no reabre la spec de la UI más allá de la enmienda de GU1 declarada en §5 (B y C
siguen condicionales); no cambia contratos de `core/` sin expediente y aval; y no fija fechas: las fija
la fecha de entrega cuando exista.

## 9. Calibración del inventario

El sondeo del arquitecto (2026‑09‑23) confirma que C0 tiene materia: el evaluador de expresiones en
cinco copias (`core/verification/expresiones.py` y `adapters/{civil,industrial,sistemas,telecom}/evaluador.py`);
`ui/paginas/componer.py`, que pinta, calcula, persiste y elabora; la dependencia en dos sentidos entre
`ui` y `scripts`; `scripts/guardia_nucleo.py`, que importa funciones privadas de un script de metas de
sprint; y el redondeo de presentación escrito a mano en `ml/` y `scripts/`. No se encontró `float` en
los cálculos de `core/`.

## 10. Qué cambió en la revisión del 2026‑09‑23

Los cuatro encargos aprobaron con correcciones, sin bloqueantes; 17 hallazgos importantes aplicados:
GU1 se enmienda de forma declarada (GU1a/GU1b); F1 exige indicadores 1–5 con fuente, todos los RNF
cerrados u OE7 si D3 = A; F2 cubre D1–D9, G0 retroactiva y el caso de rechazo; «tutor académico
designado» en F2 y F4; protocolos del indicador 3 y de RNF‑04 antes de medir; GC4 con artefacto
revisable; GM incorpora resultados sin contradicciones y sin relajar criterios; límite operativo;
criterio O limitado a dominios; S con evidencia y no por tamaño; principios propios del proyecto;
reglas para hallazgos que cruzan capas y estado *aceptado por decisión de arquitectura registrada*;
`api/` pasa a C2 y la extracción de `componer.py` queda solo en la Tarea 11; ramas sin apilar; y la
cifra corregida de compuertas (tres, no cinco). Menores aplicados: CI sobre commit de `main` para F3;
inventario vivo; cobertura por capa en GC0; comando explícito en GC2; nombres C/Med/Red; capítulo I
tras D3; mapeo de severidad por defecto; decisiones del dossier como riesgo rastreado.

**Enmienda del 2026‑09‑24 (compuerta GC2).** Eugenio decidió que INV‑080 (la recarga del informe
pierde los pendientes; expediente C2.1 de `docs/bitacora/2026-09-23-cierre.md`) se corrige en **C3**
con **un commit de `core/budget/`**, aunque C3 no toca `core/` por lo demás [nota de la apertura de
C3: salvo la segunda excepción, enmienda siguiente]. Condiciones: expediente previo, commit propio
sin mezclar capas, llamadores de `api/` y `ui/` en commits separados, y la línea base intacta. La
fila C3 de §5 lo recoge. Motivo: la única frontera de persistencia del presupuesto es
`core/budget/persistencia.py`, y declararlo en limitaciones dejaba RF‑02 parcial al recargar.

**Enmienda del 2026‑09‑24 (apertura de C3).** Eugenio decidió (D1 = A) que la subtarea 7a de INV‑015
(expediente B.8 de `docs/bitacora/2026-09-23-C1-expedientes.md`) se corrige en C3 con un segundo
commit de `core/`: la tabla `descarte_version`, que `crear_esquema` agrega sin alterar las demás (no
es migración de esquema, §2), y `descartar_version` en `core/budget/actualizacion.py` (exportada en
`core/budget/__init__.py`), con el botón en un commit de `ui/` aparte. Condiciones: las mismas que
INV‑080. Motivo: 7a exige un dato persistido nuevo («se marca como descartada») y la fila INV‑015 es
importante, así que no puede ir a limitaciones. Coherencia: GU1a recoge las dos excepciones (INV‑080
e INV‑015 7a) en su criterio, en `PLAN_UI.md` y en la verificación de la compuerta.
