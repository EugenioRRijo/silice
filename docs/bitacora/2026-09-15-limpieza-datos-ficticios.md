# Bitácora — Sesión de limpieza (afirmaciones de datos «reales»)

**Fecha:** 2026‑09‑15 · **Rama:** `inc/limpieza-datos-ficticios` (worktree
`.claude/worktrees/limpieza-datos`) · **Base:** `inc/tesis-cap1-2` (`d6fc6e9`, PR #4) ·
**Origen:** pendiente registrado en la
[bitácora del Sprint R1](2026-09-15-sprint-r1-capitulos.md) y en la
[spec del sprint](../superpowers/specs/2026-09-15-sprint-r1-capitulos-design.md) §3.

## Objetivo

`CLAUDE.md` §1 declara que **todos** los APU y presupuestos del repositorio son ejercicios
académicos ficticios. Los capítulos I y II ya lo respetan, pero el resto del repositorio seguía
llamándolos reales: un jurado que leyera la tesis y después el repositorio encontraría la
contradicción. Esta sesión la cierra y deja una meta que impide que vuelva.

## Qué se corrigió

69 sustituciones en 29 archivos, en tres categorías:

| Categoría | Ejemplo antes → después | Archivos |
|---|---|---|
| Presupuestos de ARENAZA presentados como reales | «los dos presupuestos **reales** de ARENAZA» → «didácticos»; «segunda línea base **real**» → «didáctica» | fixture y pruebas de ARENAZA, `data/samples/telecom/README.md`, `PLAN_MULTIDOMINIO.md` |
| La línea base de la clínica como caso real | «los cinco APU **reales**» → «los cinco APU de la línea base»; «en el presupuesto **real** auditado» → «en el presupuesto auditado» | `tests/fixtures/apu_linea_base.py`, `test_costing.py`, `test_budget.py`, `PLAN_DESARROLLO.md`, `docs/dossier_g0.md`, `docs/plan_pruebas.md`, `docs/calidad_iso25010.md`, `docs/metodologia.md`, `README.md` |
| «Precios reales» donde corresponde «publicados» | «precios **reales** y fechados» → «publicados y fechados»; «tarifas **reales**» → «publicadas» | `PLAN_MULTIDOMINIO.md`, `PLAN_ASISTENTE.md`, `docs/README.md`, `docs/manual_usuario.md`, `docs/protocolo_precios.md`, `data/sistemas/fuentes/README.md` |

La tercera categoría es la que más se prestaba a confusión: MaPreX jul‑2026 y el tabulador del CIV
**sí** son referencias publicadas y reales; lo ficticio son los APU y presupuestos que se costean
con ellas. Antes ambas cosas se nombraban igual.

## Qué no se tocó, y por qué

- **Vocabulario del dominio:** `origen_id` real, el tipo `REAL` de SQLite, los «rendimientos reales
  de obra ejecutada» de UC‑06, el parámetro `reales` de las métricas (valores observados frente a
  estimados) y las frases que ya declaran que algo **no** es real.
- **Datos reales futuros:** las corridas reales contra la API del asistente y los «APU reales que el
  usuario suministre» de la compuerta GA‑datos. `CLAUDE.md` §1 los contempla.
- **Registros fechados:** bitácoras y specs o planes de sprints ya ejecutados registran lo que se
  sabía en su fecha. Tampoco se reescribieron los **mensajes de commit citados** dentro de
  `PLAN_MULTIDOMINIO.md`: son historia ocurrida. En su lugar, cada documento histórico lleva su
  nota de errata (`PLAN_DESARROLLO.md` y `PLAN_MULTIDOMINIO.md` en esta sesión;
  `data/telecom/fuentes/README.md` ya la tenía).

## Meta de datos (`scripts/meta_datos.py`)

Tres chequeos, con 14 pruebas en `tests/unit/test_meta_datos.py`:

| Meta | Qué comprueba |
|---|---|
| D1 | Ningún documento vigilado presenta los datos del repositorio como reales |
| D2 | `CLAUDE.md` sigue declarando la naturaleza de todos los datos, ARENAZA incluido |
| D3 | Los tres documentos históricos conservan su nota de errata |

Decisiones de diseño:

- **Separada de `meta_redaccion.py`.** Su meta R7 solo mira los capítulos, y la contradicción
  estaba fuera de ellos. Además la regla debe ser distinta: en un capítulo, «obra ejecutada»
  delata una afirmación sobre los datos; en la documentación es vocabulario de UC‑06. Aquí se
  vigila la pareja «presupuesto / APU / caso / datos / línea base» con «real».
- **No vigila** `docs/bitacora/` ni `docs/superpowers/` (registros fechados) ni `docs/tesis/`
  (ya lo hace R7, con su regla más estricta).
- **Corre sin dependencias** (solo biblioteca estándar), por lo que se enganchó al job `calidad`
  de la CI, que instala únicamente el grupo de desarrollo.

## Defecto de la meta, hallado con la prueba negativa sobre documentos reales

La lección del Sprint R1 volvió a pagar. Sobre el repositorio ya limpio, la meta **falló**, y no
por suciedad pendiente: daba dos falsos positivos.

1. Los mensajes de commit citados entre comillas invertidas en `PLAN_MULTIDOMINIO.md`.
2. Las propias notas de errata, que citan entre comillas angulares la redacción antigua
   («presupuestos reales») justamente para declararla corregida.

En ambos casos el texto está **citado, no afirmado**. Se corrigió con dos pruebas que primero
fallaron: la afirmación se busca fuera de lo citado, y la marca que la desmiente se busca en toda
la oración. De paso, el corte de oraciones dejó de partir en cualquier punto — «M1.1‑M4.2» y
«(2026‑09‑15).**» quedaban en trozos distintos de la marca que los exonera — y ahora corta solo
donde el punto va seguido de espacio.

## Informe generado y ancho de línea

`docs/resultados_ml.md` se genera: se corrigieron los textos de `scripts/generar_resultados_ml.py`
y se regeneró. Antes de tocar nada se comprobó que el informe en disco coincidía con la salida del
generador, así que el diff resultante es íntegramente de esta sesión: cuatro frases («catálogos
poblados», «histórico observado», «lista de precios publicada» y la cabecera «PU observado»). La CI
sigue comprobando que sea reproducible.

Los textos nuevos son más largos que los que sustituyeron y dispararon 12 avisos `E501`. Se
reajustaron partiendo cadenas y reflujando docstrings, sin cambiar ni una palabra de lo impreso.

## Estado al cierre

- **Suite:** 558 pruebas en verde con `-W error`. Eran 544; las 14 nuevas son las de la meta de
  datos.
- **`ruff check .`:** limpio.
- **Metas:** `scripts/meta_datos.py` 3/3 y `scripts/meta_redaccion.py` 12/12.
- **Núcleo:** `git diff --stat r-base -- core/` vacío. Esta sesión no tocó `core/`.
- **Informe:** `docs/resultados_ml.md` regenerado; el diff se limita a las cuatro frases
  corregidas, y la CI comprueba en cada PR que el generador lo reproduzca.

## Pendientes (no son de esta sesión)

1. Completar las 14 referencias pendientes de la tesis.
2. Capítulo III (marco metodológico), donde va la justificación de la clase 3 de AACE.
3. Decisiones del tutor académico: D3, D4, la elección entre AACE 18R‑97 y 56R‑08, y T2/T3 del
   acta del capítulo I.
