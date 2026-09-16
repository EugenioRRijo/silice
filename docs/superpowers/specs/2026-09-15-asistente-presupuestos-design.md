# Diseño — Asistente de presupuestos con IA, auditado (UC‑09)

**Fecha:** 2026‑09‑15 · **Estado:** aprobado en conversación («aprobado tal cual»; enfoque A) ·
**Rama:** `inc/PLAN-asistente`, apilada sobre `inc/CI-integracion-continua` (PR #2); base del
plan: etiqueta `a-base` (`66fb52a`) · **Autoridad:** [CLAUDE.md](../../../CLAUDE.md),
[docs/metodologia.md](../../metodologia.md), [docs/ERS.md](../../ERS.md) · **Plan de fases y
sesiones:** [PLAN_ASISTENTE.md](../../../PLAN_ASISTENTE.md) (única copia del detalle de cada
sesión; esta spec no lo repite)

## 1. Contexto y alcance

El usuario pide que **una IA arme presupuestos según las necesidades del usuario**, auditados con
los datos del proyecto (la línea base, los presupuestos ARENAZA, `MNT-001`, `SIS-001`) y con los
parámetros de la referencia MaPreX. Pidió también que no se priorice su implementación: primero
un plan de desarrollo en worktree, con metas que auditen la **primera fase**, y sesiones de
escritura y de desarrollo que sigan la metodología Scrum‑Cascada y DRY
([metodologia.md](../../metodologia.md)).

**Decisiones del usuario (2026‑09‑15):**

| # | Decisión | Elección |
|---|---|---|
| DA‑1 | Tipo de IA | **Híbrido con compuerta.** Ahora, un asistente con Claude que traduce necesidades a partidas del catálogo y cantidades con regla declarada; el modelo entrenado con datos propios entra cuando un dominio cruce G2 |
| DA‑2 | Red y datos (RNF‑08) | **Extra opcional declarado.** El asistente vive en el extra `ia`, apagado por defecto; sin él, el sistema sigue sin red. RNF‑08 se reescribe con la excepción declarada |
| DA‑3 | Sesiones del plan | **Técnicos + tesis.** Cada fase lleva sus sesiones de escritura (ERS, arquitectura, manuales) y, al cierre, las secciones de los capítulos IV y V |

**Dato que condiciona el diseño:** la compuerta G2 midió 5 (civil), 40 (telecom), 4 (industrial)
y 9 (sistemas) registros de APU ([resultados_ml.md](../../resultados_ml.md)), todos por debajo de
50. Hoy no existe base para entrenar un modelo propio; el híbrido lo reconoce en vez de ocultarlo.

**Alcance de esta sesión:** solo planificación. `PLAN_ASISTENTE.md`, esta spec, el plan
ejecutable, la meta `scripts/meta_asistente.py` con pruebas propias y la bitácora. **No se escribe
código del asistente.**

**Fuera de alcance del plan completo:** que la IA fije precios (nunca: los precios salen del
catálogo y de MaPreX con su origen); agentes alojados por Anthropic (enfoque B, §2); entrenar con
presupuestos generados por la propia IA (§5.3).

## 2. Enfoques considerados

| Enfoque | Veredicto |
|---|---|
| **A. Capa de composición con herramientas deterministas.** Claude (SDK `anthropic`, Tool Runner) solo elige partidas del catálogo y cantidades con regla declarada; costeo, auditoría y contraste los hace el núcleo existente | **Elegido.** Cada cifra conserva su origen, el informe R1–R7 se genera siempre y la IA queda acotada a lo que sabe hacer: interpretar texto y elegir |
| B. Managed Agents (Anthropic aloja el agente y su espacio de trabajo) | Descartado: el catálogo vive en SQLite local; habría que subir datos a un servicio externo y RNF‑08 empeoraría |
| C. Una sola llamada con salida estructurada que devuelve el presupuesto completo | Descartado: el modelo inventaría precios y cantidades sin trazabilidad; ninguna regla R1–R7 podría reevaluarlos |

## 3. Arquitectura

### 3.1 Paquete y fronteras

- **`asistente/`**, paquete de primer nivel del mismo rango que `api/` y `ui/`: capa de
  composición. Puede importar `core` (catálogo, presupuesto, verificación), `ml` (similitud,
  predicción) y `adapters` si hiciera falta; **`core` nunca lo importa**. Se añade a
  `PAQUETES_FUERA_DEL_NUCLEO` en `tests/unit/test_arquitectura.py` (Fase A1).
- **Extra `ia`** en `pyproject.toml` con el SDK oficial `anthropic` (Python). Sin el extra, las
  pruebas del asistente se omiten con `importorskip` como las de `ml` — y el paso «sin pruebas
  omitidas» de CI obliga a instalarlo allí (`uv sync --all-extras`).
- **`core/` no cambia.** Si una sesión cree necesitarlo, se detiene y escribe el hallazgo
  (CLAUDE.md §9). Meta M11 lo vigila desde `a-base`.

### 3.2 Herramientas (todas deterministas, todas sobre código existente)

| Herramienta | Envuelve | Devuelve al modelo |
|---|---|---|
| `buscar_partidas(texto, dominio)` | `Catalogo.partidas` + `ml.normalization.NormalizadorPartidas.similares` | códigos, descripciones, unidades y puntaje (nunca precios) |
| `consultar_composicion(codigo)` | `Catalogo.composicion` | insumos y rendimiento de la partida, sin montos |
| `referencia_maprex(insumo, dominio)` | `data/precios/maprex_2026-07/referencia_<dominio>.csv` | precio USD, `ref_maprex`, `fecha_vigencia` y `archivo` |
| `proponer_items(partidas)` | construcción de `ItemComputo` | ítems con `origen_tipo = REGLA` (expresión y parámetros que R1 reevalúa) o `MANUAL` (cantidad dictada por el usuario, `origen_id` = referencia a su pedido) |
| `elaborar_borrador(items)` | `core.budget.elaborar` | presupuesto costeado con `Decimal` + `InformeAuditoria` (siempre) |
| `contrastar(presupuesto)` | `ml.prediction.contrastar_aace` + referencia MaPreX | hallazgos ADVERTENCIA fuera de la clase 3 de AACE |

**Procedencia de la IA.** `OrigenTipo` (contrato congelado) tiene IFC, REGLA, TABULAR, CSV y
MANUAL: alcanza para registrar la cantidad sin tocar el contrato, pero no dice que la **propuso**
la IA. Esa procedencia (pedido, herramientas llamadas, versión del modelo) vive en un registro del
paquete `asistente/`, no en `core/`. Se declara como hallazgo de contrato en la Fase A0.

### 3.3 El modelo (hechos del skill `claude-api`, a reverificar en la Fase A2)

- Modelo por defecto `claude-opus-5`, pensamiento adaptativo; SDK Python oficial y **Tool Runner**
  (`client.beta.messages.tool_runner` con funciones `@beta_tool`), herramientas con `strict: true`.
- Comprobar `stop_reason` antes de leer el contenido; con `claude-opus-5` se incluyen por defecto
  los **fallbacks del lado del servidor** ante un rechazo (se declara al usuario).
- Caché de prompt para el contexto estable (instrucciones y lista de herramientas).
- Regla del skill: **ninguna firma del SDK se escribe de memoria**; la sesión A2 relee la
  documentación del skill antes de programar.
- Datos enviados a la API: el pedido del usuario y las partidas candidatas que devuelven las
  herramientas. **Nunca** los PDF de terceros (MaPreX, ARENAZA, fuentes del anteproyecto).

## 4. Flujo de UC‑09 — Generar presupuesto asistido desde las necesidades del usuario

1. El usuario describe su necesidad en texto (dominio, alcance, dimensiones que conozca).
2. El asistente busca partidas candidatas y consulta sus composiciones (herramientas §3.2).
3. Propone ítems con cantidad trazable: por regla declarada o dictada por el usuario.
4. `elaborar_borrador` costea con el motor puro y audita con R1–R7; `contrastar` compara con MaPreX.
5. El usuario recibe el **borrador**, el informe y la procedencia de cada renglón; acepta, corrige
   o descarta. Nada se persiste sin su aceptación.
6. Flujo alterno: si una necesidad no tiene partida en el catálogo, el asistente lo **dice** (no
   inventa una partida); el caso queda como pendiente del flujo de creación de partidas (RF‑16).

## 5. Auditoría con los datos del proyecto

### 5.1 Conjunto dorado

Los cuatro presupuestos auditados del repositorio, cada uno con su necesidad redactada en lenguaje
natural (redacción congelada en la Fase A0.3, antes de ver una sola salida del modelo):

| Caso | Dominio | Referencia (única copia) |
|---|---|---|
| Drenaje de la clínica, línea base corregida | civil | `tests/fixtures/apu_linea_base.py` |
| ARENAZA 1 y 2 | telecom | `tests/fixtures/presupuestos_arenaza.py` |
| `MNT-001` mantenimiento | industrial | `tests/fixtures/mantenimiento_industrial.py` |
| `SIS-001` puntos de función | sistemas | `tests/fixtures/tarifas_sistemas.py` |

### 5.2 Métricas y umbrales (propuesta; se congelan en la Fase A0.3)

| Métrica | Umbral propuesto | Por qué |
|---|---|---|
| Precios sin origen trazable | **0** (invariante; una guarda la hace imposible) | la IA nunca fija precios |
| Hallazgos ERROR o CRITICO en el borrador | **0** | el borrador pasa la misma auditoría que cualquier presupuesto |
| Partidas de la referencia presentes en el borrador (exhaustividad) | ≥ 80 % | criterio de reconocimiento ya usado en RF‑17 |
| Total del borrador contra la referencia | dentro de la clase 3 de AACE (−20 % / +30 %) | mismo rango de RF‑29 |

Las pruebas y la CI usan un **cliente falso** (sin red, sin clave). Las corridas reales contra la
API cuestan dinero: cada una requiere aprobación del usuario y registra tokens y costo medido.

### 5.3 Compuerta GA‑datos (el lado «entrenado» del híbrido)

Se recuenta G2 al cerrar la Fase A3 y al cierre del plan con `ml.prediction.tecnica_para`. Solo
cuentan **registros validados por un humano o por una fuente real** (presupuestos del autor, APU
reales que el usuario suministre, listas fechadas): los borradores generados por la IA no cuentan,
aunque se acepten, para no entrenar un modelo con su propia salida. Con ≥ 50 registros en un
dominio se abre una sub‑fase de razonamiento basado en casos para ese dominio; > 200, XGBoost
(CLAUDE.md §8.1). Por debajo, la limitación se declara con los conteos nuevos.

## 6. Fases, compuertas y sesiones (Cascada)

| Fase | Producto verificable | Compuerta de salida | Si no se cumple |
|---|---|---|---|
| **P** Planificación (esta sesión) | `PLAN_ASISTENTE.md`, esta spec, meta con pruebas | — (la meta `--hasta P` en verde) | — |
| **A0** Documentación | ERS (UC‑09, RF‑32…, RNF‑08 reescrito), arquitectura (vista del asistente), protocolo de evaluación congelado | **GA0**: documentos revisados por el tutor | se corrigen los documentos; no se programa |
| **A1** Herramientas sin IA | `asistente/herramientas.py`, guardia de arquitectura ampliada | **GA1**: las herramientas reconstruyen los cuatro casos dorados desde necesidades estructuradas (± 0,01) | se corrige la herramienta, nunca la referencia |
| **A2** Orquestación con Claude | cliente, Tool Runner, guardas de procedencia y de precios, manejo de rechazos | **GA2**: suite verde sin red con cliente falso; `core/` intacto | se rediseña la orquestación |
| **A3** Evaluación | `docs/resultados_asistente.md` con las métricas del §5.2 y el recuento GA‑datos | **GA3**: umbrales cumplidos | **degradación declarada**: el asistente queda como *sugeridor* con revisión obligatoria de cada renglón |
| **A4** Integración y cierre | página UI y ruta API, manuales, secciones de la tesis | — | — |

El detalle de cada sesión (lecturas, prompt, cierre, fuente única, commit) vive **solo** en
[PLAN_ASISTENTE.md](../../../PLAN_ASISTENTE.md).

## 7. Meta auditada (`scripts/meta_asistente.py`)

Se escribe **antes** de las sesiones, como `meta_multidominio.py`, con dos mejoras aprendidas:
cada chequeo de contenido es una función **pura sobre texto** con pruebas propias (la meta M8 del
sprint multidominio contaba mal y no tenía pruebas), y la opción **`--hasta <fase>`** evalúa solo
las metas de las fases ya alcanzadas, para que la primera fase se audite sin que las posteriores la
tiñan de PENDIENTE.

| Meta | Fase | Qué comprueba |
|---|---|---|
| M1 | P | `PLAN_ASISTENTE.md` tiene las fases A0–A4, las compuertas GA0–GA3 y GA‑datos, y **cada sesión** tiene «Cierre», «Fuente única» y «Commit» |
| M2 | P | esta spec existe |
| M3 | A0 | la ERS declara UC‑09 y al menos tres RF que lo citan |
| M4 | A0 | la fila RNF‑08 de la ERS declara la excepción del extra `ia` |
| M5 | A0 | `docs/arquitectura.md` tiene una sección del asistente |
| M6 | A0 | `docs/evaluacion_asistente.md` nombra los cuatro casos dorados y declara umbrales |
| M7 | A1 | `tests/unit/test_arquitectura.py` vigila `asistente` |
| M8 | A1 | `tests/integration/test_asistente_casos_dorados.py` en verde (GA1) |
| M9 | A2 | `tests/unit/test_asistente_orquestacion.py` en verde sin red (GA2) |
| M10 | A3 | `docs/resultados_asistente.md` con tabla de métricas y recuento G2 (GA3, GA‑datos) |
| M11 | todas | `git diff a-base --stat -- core/` vacío (reutiliza `meta_multidominio.evaluar_m11_nucleo_intacto`) |
| M12 | todas | `ruff check .` limpio (reutiliza `meta_multidominio.evaluar_m12_ruff`) |

Al cierre de esta sesión: `--hasta P` → 4/4 OK (M1, M2, M11, M12); la meta completa muestra
M3–M10 en PENDIENTE, que es lo correcto.

## 8. Cómo se aplica la metodología a cada sesión

- **Cascada:** las fases A0→A4 van en orden; ninguna sesión adelanta trabajo de una fase cuya
  compuerta no se cruzó (metodologia.md §4). La meta `--hasta` es la evidencia de cada cruce.
- **Scrum:** cada fase es un sprint con su worktree; cada sesión es un ítem del sprint backlog con
  *Definition of Ready* (compuerta anterior cruzada, insumos presentes) y *Definition of Done*
  (criterio de cierre con evidencia, suite y ruff verdes, `core/` intacto, commit convencional,
  bitácora). Las sesiones de escritura cumplen la misma DoD que las de código: su evidencia es la
  meta de contenido y la revisión del diff.
- **DRY:** cada sesión declara su **fuente única** (dónde vive el hecho nuevo y quién lo importa o
  enlaza). Esta spec enlaza el plan en vez de copiarlo; la meta importa los chequeos de `core/` y
  ruff en vez de reescribirlos; el conjunto dorado importa los fixtures existentes.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| El tutor no aprueba el cambio de RNF‑08 (GA0) | el asistente queda fuera del alcance evaluado y se declara como trabajo futuro; A1 (herramientas sin IA) sigue siendo útil para UC‑01 |
| La IA propone partidas o cantidades erróneas | toda cifra pasa por el motor y por R1–R7; el borrador exige aceptación; la métrica de exhaustividad lo mide |
| La IA intenta fijar un precio | la guarda de A2 rechaza cualquier precio que no venga de una herramienta con origen; invariante probada |
| Costo de las corridas reales | cliente falso en pruebas y CI; corridas reales solo con aprobación y costo registrado |
| Contaminar el lado «entrenado» con salidas de la propia IA | regla de GA‑datos (§5.3): solo cuentan registros validados por humano o fuente real |
| Deriva de la API de Claude entre hoy y la Fase A2 | la sesión A2 relee el skill y la documentación oficial antes de escribir una firma |

## 10. Mecánica y restricciones

- **Worktree y ramas:** worktree `.claude/worktrees/plan-asistente`, rama `inc/PLAN-asistente`
  (apilada sobre el PR #2), PR #3. Cada fase posterior abre su propio worktree (`inc/A0-…`, …).
- **Vedados** (cambios sin commitear del usuario en el checkout principal): `CLAUDE.md`,
  `README.md`, `docs/README.md`, `docs/linea_base.md`, `docs/tesis/**`. Las sesiones de redacción
  de la tesis de la Fase A4 dependen de que el usuario commitee su sesión de redacción pausada.
- **Commits:** Conventional Commits en español, asunto sin tildes; uno por componente.
- **Sin cambios de dependencias en esta sesión:** el extra `ia` se agrega en la Fase A2.
