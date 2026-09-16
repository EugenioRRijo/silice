# PLAN_ASISTENTE.md — Asistente de presupuestos con IA, auditado (UC‑09)

Continuación de [PLAN_DESARROLLO.md](PLAN_DESARROLLO.md) (20 de 20 sesiones) y de
[PLAN_MULTIDOMINIO.md](PLAN_MULTIDOMINIO.md) (11 de 11). Aquellos planes dejaron un núcleo que
costea, audita y contrasta presupuestos de cuatro dominios con precios publicados y fechados. Este plan
agrega **una IA que arma el presupuesto a partir de las necesidades del usuario** sin que el núcleo
cambie y sin que la IA fije una sola cifra: la IA interpreta y elige; el núcleo calcula y audita.

**El diseño y sus decisiones viven en la spec**
[docs/superpowers/specs/2026-09-15-asistente-presupuestos-design.md](docs/superpowers/specs/2026-09-15-asistente-presupuestos-design.md)
(enfoque A, decisiones DA‑1 a DA‑3, herramientas, métricas propuestas). Este archivo es la **única
copia** de las fases, las compuertas y las sesiones; la spec no las repite y las sesiones no repiten
la spec: la enlazan.

**Cómo se audita.** `uv run python scripts/meta_asistente.py --hasta <fase>` evalúa las metas de
las fases alcanzadas (P, A0, A1, A2, A3) más las transversales (núcleo intacto desde `a-base` y
ruff). Una fase se cruza cuando su `--hasta` está en OK **y** su compuerta quedó registrada en la
bitácora (metodologia.md §2.2).

---

## 0. Situación de partida (2026‑09‑15)

| Pieza | Estado | Dónde |
|---|---|---|
| Catálogo, motor, presupuesto y auditoría R1–R7 | listos en los cuatro dominios | `core/`, [PLAN_MULTIDOMINIO.md](PLAN_MULTIDOMINIO.md) |
| Similitud semántica de partidas (UC‑03) | lista | `ml/normalization` |
| Contraste AACE clase 3 (UC‑07) | listo | `ml/prediction` |
| Referencia de precios MaPreX jul‑2026 por dominio | lista (37 / 18 / 13 / 43 filas) | `data/precios/maprex_2026-07/` |
| Presupuestos auditados para el conjunto dorado | 4 casos | fixtures de la spec §5.1 |
| Registros para un modelo propio (G2) | 5 / 40 / 4 / 9, todos < 50 | [docs/resultados_ml.md](docs/resultados_ml.md) |
| Integración continua | Linux + Windows, guardia del núcleo | `.github/workflows/ci.yml` |
| Interpretación de necesidades en lenguaje natural | **no existe** | este plan |

## 1. Principios (además de los de CLAUDE.md)

1. **La IA nunca fija precios ni cantidades sin regla.** Cada precio sale del catálogo o de MaPreX
   con su origen; cada cantidad, de una regla declarada (R1 la reevalúa) o del usuario.
2. **El informe se genera siempre**, también para un borrador de la IA (CLAUDE.md §2.7).
3. **Nada se persiste sin aceptación del usuario.** El asistente produce borradores.
4. **Ninguna corrida real contra la API sin aprobación.** Pruebas y CI usan un cliente falso; cada
   corrida real registra tokens y costo.
5. **Las salidas de la IA no entrenan a la IA.** Solo cuentan para G2 los registros validados por
   un humano o por una fuente real (compuerta GA‑datos).
6. **Sesiones de escritura con la misma DoD que las de código.** Un documento se cierra con su
   meta en OK, su fuente única declarada y su commit.

## 2. Compuertas y criterios de degradación

| Compuerta | Cuándo | Criterio de paso | Si no se cumple |
|---|---|---|---|
| **GA0** documentación | tras A0.3 | `--hasta A0` en OK y ERS, arquitectura y protocolo revisados por el tutor (incluido el cambio de RNF‑08) | se corrigen los documentos; si el tutor rechaza la excepción de red, el asistente con IA pasa a trabajo futuro declarado y solo sigue la Fase A1 |
| **GA1** herramientas | tras A1.2 | las herramientas reconstruyen los cuatro casos dorados desde necesidades estructuradas, ± 0,01, sin IA | se corrige la herramienta, nunca la referencia |
| **GA2** orquestación | tras A2.2 | suite verde sin red con cliente falso; guardas de precio y procedencia probadas; `core/` intacto | se rediseña la orquestación; nunca se relaja una guarda |
| **GA3** evaluación | tras A3.1 | los umbrales congelados en A0.3 se cumplen sobre el conjunto dorado | **degradación declarada**: el asistente queda como *sugeridor* con revisión obligatoria de cada renglón, y la brecha se reporta en el capítulo V |
| **GA‑datos** híbrido | en A3.2 y al cierre | recuento G2 con registros validados: ≥ 50 en un dominio abre razonamiento basado en casos; > 200, XGBoost | la limitación se declara con los conteos nuevos |

---

## Fase A0 — Documentación (3 sesiones de escritura)

*Definition of Ready de la fase:* este plan en `main` o en su rama, `--hasta P` en OK.

### Sesión A0.1 — ERS: UC‑09 y excepción de red

**Lecturas.** [docs/ERS.md](docs/ERS.md) §2.2, §3.2, §3.3 y §4; spec §1, §4 y §5.

```
Agrega a la ERS el caso de uso UC-09 "Generar presupuesto asistido desde las necesidades del
usuario" con actores, precondiciones, flujo principal (spec §4) y flujos alternos (necesidad sin
partida, rechazo del modelo, extra ia no instalado). Numera sus requisitos desde RF-32: recibir
la necesidad, proponer partidas del catalogo, cantidades con regla o del usuario, borrador
auditado siempre, procedencia de cada renglon, aceptacion explicita. Reescribe la fila RNF-08 con
la excepcion declarada del extra `ia` (DA-2 de la spec). Actualiza la matriz de trazabilidad.
```

**Cierre.** M3 y M4 en OK; la matriz de trazabilidad cita UC‑09 con todos sus RF.
**Fuente única.** `docs/ERS.md` es la única definición de UC‑09 y de sus RF; spec, plan de pruebas y
tesis los citan por número.
**Commit.** `docs(ers): uc-09 asistente de presupuestos y excepcion de red declarada`

### Sesión A0.2 — Arquitectura del asistente

**Lecturas.** [docs/arquitectura.md](docs/arquitectura.md) §1–§6; spec §3.

```
Agrega la seccion del asistente a las vistas 4+1: logica (paquete asistente/ y sus herramientas),
proceso (secuencia de UC-09 hasta el borrador auditado), desarrollo (asistente/ al nivel de api/ y
ui/, extra ia, prueba de arquitectura) y fisica (que datos salen hacia la API y cuales nunca).
Registra en §6 la decision del enfoque A y, en la deuda declarada, el hallazgo de procedencia:
OrigenTipo no distingue una cantidad propuesta por la IA; la procedencia vive en asistente/.
```

**Cierre.** M5 en OK; la vista física lista explícitamente los datos que se envían y los que no.
**Fuente única.** `docs/arquitectura.md` para las fronteras del paquete; la decisión se registra
una sola vez en su §6.
**Commit.** `docs(arquitectura): vista del asistente y hallazgo de procedencia`

### Sesión A0.3 — Protocolo de evaluación congelado

**Lecturas.** spec §5; `tests/fixtures/` (los cuatro casos); [docs/resultados_ml.md](docs/resultados_ml.md).

```
Crea docs/evaluacion_asistente.md: los cuatro casos dorados (linea base, ARENAZA, MNT-001,
SIS-001) con la necesidad de cada uno redactada en lenguaje natural ANTES de ver una salida del
modelo; las metricas y sus umbrales (spec §5.2), ahora congelados; como se mide cada una; el costo
estimado por corrida y la regla de aprobacion del usuario. Las cifras de referencia no se copian:
se enlazan a sus fixtures.
```

**Cierre.** M6 en OK; `--hasta A0` en OK; compuerta GA0 solicitada al tutor y registrada en la
bitácora.
**Fuente única.** `docs/evaluacion_asistente.md` para necesidades y umbrales; las cifras de
referencia siguen en `tests/fixtures/`.
**Commit.** `docs(evaluacion): protocolo del asistente con casos dorados y umbrales`

---

## Fase A1 — Herramientas deterministas (2 sesiones de código)

*Definition of Ready:* GA0 cruzada.

### Sesión A1.1 — Herramientas de consulta

**Lecturas.** spec §3.1–§3.2; `core/catalog/repositorio.py`; `ml/normalization/normalizador.py`;
`data/precios/maprex_2026-07/README.md`.

```
TDD. Crea asistente/herramientas.py con buscar_partidas, consultar_composicion y
referencia_maprex: funciones puras sobre el catalogo y la referencia, sin IA y sin precios en lo
que devuelve buscar_partidas. Agrega "asistente" a PAQUETES_FUERA_DEL_NUCLEO en
tests/unit/test_arquitectura.py.
```

**Cierre.** M7 en OK; pruebas unitarias de las tres herramientas en verde; `core/` intacto.
**Fuente única.** `asistente/herramientas.py`; la referencia MaPreX se lee del CSV, nunca se
transcribe.
**Commit.** `feat(asistente): herramientas de consulta del catalogo y maprex`

### Sesión A1.2 — Armado y auditoría de borradores

**Lecturas.** `core/budget/presupuesto.py` (`elaborar`); `ml/prediction/reglas.py`
(`contrastar_aace`); `docs/evaluacion_asistente.md`.

```
TDD. Agrega proponer_items (ItemComputo con REGLA o MANUAL), elaborar_borrador (core.budget.elaborar,
informe siempre) y contrastar. Escribe tests/integration/test_asistente_casos_dorados.py: desde la
necesidad ESTRUCTURADA de cada caso dorado (sin IA), las herramientas reconstruyen su presupuesto
con +/- 0,01 y el informe no tiene ERROR ni CRITICO.
```

**Cierre.** M8 en OK (GA1); `--hasta A1` en OK.
**Fuente única.** los casos dorados importan sus fixtures; las necesidades estructuradas viven en
un solo módulo de prueba.
**Commit.** `feat(asistente): armado y auditoria de borradores con casos dorados`

---

## Fase A2 — Orquestación con Claude (2 sesiones de código)

*Definition of Ready:* GA1 cruzada.

### Sesión A2.1 — Cliente y bucle de herramientas

**Lecturas.** el skill `claude-api` completo para Python (obligatorio: ninguna firma del SDK se
escribe de memoria); spec §3.3.

```
Agrega el extra ia (SDK anthropic) a pyproject.toml y uv.lock. Crea asistente/orquestador.py con el
Tool Runner sobre las herramientas de A1 (strict), modelo claude-opus-5 con pensamiento adaptativo,
comprobacion de stop_reason y fallbacks del lado del servidor ante un rechazo. Las pruebas usan un
cliente falso: ninguna prueba abre red ni necesita clave.
```

**Cierre.** M9 en OK (`tests/unit/test_asistente_orquestacion.py`); CI verde en Linux y Windows con
el extra instalado.
**Fuente única.** `asistente/orquestador.py` para el modelo y sus parámetros; ningún otro módulo
nombra el modelo.
**Commit.** `feat(asistente): orquestacion con claude y cliente falso`

### Sesión A2.2 — Guardas de precio y de procedencia

**Lecturas.** spec §1 y §9; `asistente/orquestador.py`.

```
TDD. Guardas: (1) todo precio del borrador proviene de una herramienta con origen; un precio sin
origen se rechaza; (2) cada renglon registra su procedencia (pedido, herramientas, version del
modelo); (3) una necesidad sin partida se informa, no se inventa. Pruebas negativas con el cliente
falso devolviendo precios inventados y partidas inexistentes.
```

**Cierre.** `--hasta A2` en OK; las tres pruebas negativas en verde (GA2).
**Fuente única.** las guardas viven en un solo módulo del asistente; UI y API las heredan.
**Commit.** `feat(asistente): guardas de precio y de procedencia`

---

## Fase A3 — Evaluación (2 sesiones)

*Definition of Ready:* GA2 cruzada; presupuesto de la corrida aprobado por el usuario.

### Sesión A3.1 — Corrida sobre el conjunto dorado

**Lecturas.** `docs/evaluacion_asistente.md`; el skill `claude-api` (caché de prompt y costo).

```
Crea scripts/evaluar_asistente.py: corre las cuatro necesidades en lenguaje natural contra la API
real (con aprobacion previa del usuario), mide cada metrica contra su umbral congelado, registra
tokens y costo, y genera docs/resultados_asistente.md con la tabla de metricas.
```

**Cierre.** `docs/resultados_asistente.md` generado por el script; veredicto de GA3 (cruzada o
degradación declarada) en la bitácora.
**Fuente única.** `docs/resultados_asistente.md` es generado, nunca editado a mano.
**Commit.** `feat(asistente): evaluacion sobre los casos dorados`

### Sesión A3.2 — Recuento GA‑datos

**Lecturas.** `scripts/generar_resultados_ml.py`; `ml/prediction/reglas.py` (`tecnica_para`).

```
Recuenta G2 por dominio solo con registros validados por humano o fuente real y agrega el recuento
a docs/resultados_asistente.md (regenerado). Si un dominio cruza 50, abre la sub-fase de casos
para ese dominio en este plan; si no, declara la limitacion con los conteos nuevos.
```

**Cierre.** M10 en OK; `--hasta A3` en OK; GA‑datos registrada en la bitácora.
**Fuente única.** los conteos G2 siguen saliendo de `tecnica_para`; `resultados_asistente.md`
enlaza `resultados_ml.md` en vez de copiar su tabla.
**Commit.** `docs(asistente): veredicto ga3 y recuento de datos`

---

## Fase A4 — Integración y cierre (3 sesiones)

*Definition of Ready:* GA3 registrada (cruzada o degradada).

### Sesión A4.1 — Página y ruta de UC‑09

**Lecturas.** `ui/paginas/escenarios.py` y `api/rutas/` (precedente de UC‑08); `docs/manual_tecnico.md` §9.

```
Agrega la pagina "Presupuesto asistido (UC-09)" y la ruta POST /asistente/borradores: ambas llaman
al orquestador (la UI no consume la API por HTTP, decision de F.1), muestran el borrador, el
informe y la procedencia, y persisten solo tras aceptacion. Regenera docs/api.json.
```

**Cierre.** pruebas de la ruta y de la página en verde; el paso de reproducibles de CI en verde con
el nuevo `api.json`.
**Fuente única.** la lógica sigue en `asistente/`; página y ruta solo componen y presentan.
**Commit.** `feat(asistente): pagina y ruta de presupuesto asistido`

### Sesión A4.2 — Manuales, pruebas y calidad

**Lecturas.** `docs/manual_usuario.md`, `docs/manual_tecnico.md`, `docs/plan_pruebas.md` §8–§10,
`docs/calidad_iso25010.md` §7.

```
Manual de usuario: como pedir un borrador y leer su procedencia. Manual tecnico: el extra ia y las
guardas. Plan de pruebas: UC-09 y sus RF en la matriz RF -> prueba. ISO/IEC 25010: seguridad con la
excepcion de RNF-08. Bitacora final del plan con las cinco compuertas.
```

**Cierre.** la matriz RF → prueba cubre todos los RF de UC‑09; `scripts/meta_asistente.py` completo
en OK.
**Fuente única.** los documentos enlazan la ERS y los resultados; no copian cifras.
**Commit.** `docs: cierre del plan del asistente`

### Sesión A4.3 — Redacción de la tesis

*Definition of Ready propia:* el usuario commiteó su sesión de redacción pausada
(`docs/tesis/**`, hoy vedado).

**Lecturas.** `docs/tesis/plan_redaccion.md`; `docs/resultados_asistente.md`; bitácoras de A0–A4.

```
Redacta en el capitulo IV la seccion del asistente (arquitectura, guardas y por que la IA no fija
precios) y en el capitulo V sus resultados (metricas contra umbrales, veredicto GA3, recuento
GA-datos como limitacion o avance). Agrega las cifras nuevas a la tabla de cifras citables de
plan_redaccion con su comando de regeneracion.
```

**Cierre.** el tablero de `docs/tesis/capitulos/README.md` refleja las dos secciones; toda cifra
citada está en la tabla de cifras citables.
**Fuente única.** cada cifra vive en `resultados_asistente.md` y se cita desde la tabla de cifras
citables, nunca se reescribe a mano en el capítulo.
**Commit.** `docs(tesis): asistente de presupuestos en capitulos iv y v`

---

## Resumen del recorrido

| Fase | Sesiones | Tipo | Producto | Compuerta | Meta |
|---|---|---|---|---|---|
| A0 Documentación | 3 | escritura | ERS, arquitectura, protocolo congelado | GA0 | `--hasta A0` |
| A1 Herramientas | 2 | código | herramientas deterministas y casos dorados sin IA | GA1 | `--hasta A1` |
| A2 Orquestación | 2 | código | Claude con cliente falso y guardas | GA2 | `--hasta A2` |
| A3 Evaluación | 2 | código + escritura | resultados medidos y recuento de datos | GA3, GA‑datos | `--hasta A3` |
| A4 Integración y cierre | 3 | código + escritura | UI, API, manuales, calidad y tesis | — | meta completa |

Total: **12 sesiones**. Cada fase se ejecuta en su propio worktree con su rama `inc/A<n>-…`, y cada
sesión cierra con la *Definition of Done* de [metodologia.md](docs/metodologia.md) §3.4 más la
fuente única declarada.
