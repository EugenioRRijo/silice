# Inventario del cierre de la tesis

**Fuente única del backlog del cierre** ([spec, §4](../superpowers/specs/2026-09-23-plan-cierre-tesis-design.md)).
Inventario **vivo**: se agregan aquí los hallazgos que aparezcan después de C0 hasta la condición F3.

**Commit auditado:** `cc2243cd5a7efd3b20dc82fe586484a6ef01fea8` · **Fecha:** 2026‑09‑23 · **Estado:** aprobado en GC0 (2026‑09‑23)

## 1. Cobertura por capa

| Capa | Archivos en el repositorio (`git ls-files`) | Archivos revisados | Cobertura | Auditor |
|---|---|---|---|---|
| `core/` | 35 | 35 | 100 % | core ([parcial](parciales/core.md)) |
| `adapters/` + `ml/` + `api/` | 32 | 32 | 100 % | adaptadores-ml-api ([parcial](parciales/adaptadores-ml-api.md)) |
| `ui/` | 14 | 14 | 100 % | ui ([parcial](parciales/ui.md)) |
| `scripts/` | 26 | 26 | 100 % | scripts ([parcial](parciales/scripts.md)) |
| `tests/` | 70 | 70 | 100 % | tests ([parcial](parciales/tests.md)) |
| `docs` normativos (22 archivos: `CLAUDE.md`, `PLAN_*.md`, `README.md` y `docs/*.md` de primer nivel) | 22 | 22 | 100 % | docs-normativos ([parcial](parciales/docs-normativos.md)) |
| `docs/tesis/` | 10 | 10 | 100 % | docs-tesis ([parcial](parciales/docs-tesis.md)) |
| **Total** | **209** | **209** | **100 %** | siete auditores |

Nota: el encabezado del parcial de `scripts/` dice «25 de 25», pero su lista enumera los 26 archivos de
`git ls-files scripts/` (contrastada línea por línea): es un error de conteo del encabezado, no de
cobertura.

**Universo excluido** (126 archivos de `git ls-tree -r cc2243c`, declarados por la revisión de GC0):

| Ruta | Archivos | Motivo |
|---|---|---|
| `docs/bitacora/` | 50 | Registro histórico de sesiones: documenta decisiones pasadas, no afirma el estado vigente |
| `docs/superpowers/` | 19 | Specs y planes de trabajo; la spec de cierre es el criterio de esta auditoría |
| `docs/fuentes/` | 13 | Fuentes externas aportadas (normas, listados); no son producto del proyecto |
| `data/` | 37 | Datos de entrada y muestras; se auditan por las pruebas que los consumen |
| `docs/api.json` | 1 | Esquema OpenAPI generado por `scripts/exportar_openapi.py`; lo vigila `tests/unit/test_openapi.py` |
| `docs/auditoria/` | 1 | Este inventario (los parciales se crearon después del commit auditado) |
| `.github/workflows/ci.yml`, `pyproject.toml` | 2 | Revisados en C1 por la capa `tests` (Tarea 1, paso 10, del plan de C1); hallazgos: ninguno nuevo; el marcador `rojo_esperado` ya es INV‑007 |
| `.gitignore`, `.python-version`, `uv.lock` | 3 | Configuración del entorno sin lógica propia |

## 2. Riesgo ya rastreado (no se duplica como hallazgo)

Decisiones D1–D9 y salvedades de [docs/dossier_g0.md](../dossier_g0.md) §3 y §4, y AACE 18R‑97 frente a
56R‑08: se remite al [paquete para el tutor](../tesis/revisiones/2026-09-paquete-tutor.md).

## 3. Hallazgos

Estados: abierto · cerrado (commit) · aceptado por decisión de arquitectura registrada (solo contratos
sin aval del tutor, spec §4) · promovido (menor que Eugenio sube a corrección) · a limitaciones.

Los parciales sumaban 73 hallazgos (0 bloqueantes, 39 importantes, 34 menores). Tras fundir cinco
pares que describen el mismo hecho quedan **68** (0 bloqueantes, 36 importantes, 32 menores). La
columna «Origen» conserva los identificadores provisionales. Orden: severidad y, dentro de ella, fase
destino (C1 → C2 → C3 → C4 → Red). Ninguna severidad se cambió en la consolidación; la verificación
independiente (Tarea 5, §5) subió INV‑065 a bloqueante, sin falsos positivos: quedan **68**
(1 bloqueante, 36 importantes, 31 menores). Las correcciones de la
compuerta GC0 (§5, «Correcciones de GC0») agregan INV‑069 e INV‑070 y suben diez menores a importante:
quedan **70** (1 bloqueante, 48 importantes, 21 menores). Las filas conservan su posición; las nuevas
van al final y §5 indica dónde ordenarían.

**Criterio de la regla por defecto de pruebas.** La spec §4 hace importante «por defecto» todo
hallazgo de trazabilidad o de pruebas. Se aplica **por principio, no por capa**: es importante un
hallazgo de `tests/` que afecta lo que la suite verifica (aserción vacía o débil, aislamiento, valor
esperado duplicado que puede divergir, guardia incompleta; p. ej. INV‑009); es menor uno de `tests/`
que solo toca la organización del código de prueba sin cambiar lo que se verifica (fixture copiada,
ayuda importada de otro módulo, docstring; INV‑042, INV‑052, INV‑053).

**Fusiones:**

- INV‑006 = core‑07 + adaptadores‑ml‑api‑01 (el evaluador de expresiones en cinco copias).
- INV‑011 = docs‑normativos‑01 + tests‑17 (RF‑19 y RF‑20 citan pruebas que no existen).
- INV‑031 = docs‑normativos‑06 + docs‑tesis‑02 (cifras de la suite desfasadas y copiadas).
- INV‑038 = core‑08 + adaptadores‑ml‑api‑02 (el mismo redondeo `quantize(..., ROUND_HALF_UP)` sin
  implementación importable única).
- INV‑044 = ui‑02 + scripts‑05 (el literal `"data/apu.db"` como ruta por defecto).

**No fundidos, a propósito** (hechos distintos o severidades distintas, que fundir obligaría a
cambiar): scripts‑03 (los sembradores formatean con `:.2f` aunque ya pueden importar la fuente única:
otro mecanismo y otra corrección que INV‑038); docs‑normativos‑09 (menor) y docs‑tesis‑04
(importante), ambos sobre RNF‑07; docs‑normativos‑08 (la matriz por paso de UC‑01…UC‑11) y tests‑21
(pruebas que faltan de UC‑02), que alimentan esa matriz; docs‑normativos‑03 y tests‑22, que se tocan
solo en RF‑04; tests‑10 y docs‑normativos‑10, que se tocan solo en el «estado esperado» de
`CLAUDE.md` §9; docs‑normativos‑13, la cara documental de INV‑006; scripts‑04 y
docs‑normativos‑20, el mismo `--reiniciar` visto desde el código y desde el guion. Cada par se cruza
en la columna de corrección.

| ID | Origen | Capa | Principio | Severidad | Evidencia | Hallazgo | Corrección propuesta | Fase destino | Estado |
|---|---|---|---|---|---|---|---|---|---|
| INV-065 | docs-normativos-20 | docs (cruza: scripts) | Pérdida de datos / pruebas (aislamiento: `data/apu.db`) | bloqueante | `docs/guion_prueba_arenia.md:55-60,77-78,125,157`; `scripts/seed_demo.py:123,479-480`; contraste CP‑07: `docs/guion_prueba_arenia.md:374-390` (base exclusiva, «nunca `data/apu.db`», `:377`) | La **preparación común de CP‑01…CP‑06** del guion ejecuta `seed_demo.py --reiniciar` (`drop_all`) sobre la ruta por defecto `data/apu.db`, la base de trabajo, y esos casos escriben después `PRUEBA-01-TUB` en la misma base; la base aparte queda como variante 2b. CP‑07 no está afectado: usa su propia base. Una prueba que escribe en `data/apu.db` es bloqueante (spec §4) | Corrección de `docs/guion_prueba_arenia.md` en C1, junto a la salvaguarda, con cuatro partes: (a) la línea 57 siembra con `--db data/prueba_arenia.db`; (b) la precondición de **cada** caso CP‑01…CP‑06 manda escribir `data/prueba_arenia.db` en el campo **Archivo SQLite** de cada página y de nuevo tras cada F5, porque la aplicación vuelve a `data/apu.db` por defecto (`:60-63`, `:101-102`; el paso 10 de CP‑01 guarda `PRUEBA-01-TUB`, `:157`); (c) antes de empezar, anotar si `data/apu.db` existe y su fecha de modificación; (d) al terminar, comprobar que `data/apu.db` no cambió. Es el mismo patrón que ya usa CP‑07 (`:377`, `:481`). **Nota:** la Tarea 12 de U1 (C3) reescribe esa preparación y esas precondiciones: debe conservar esta corrección o migrarla a `ARENIA_CASO`, y nunca volver a la ruta por defecto. Cara documental de INV‑050. **Condición de cierre:** antes de cualquier ejecución del guion, incluida la que Eugenio hace al ratificar GC1–GC3 | C1 | abierto |
| INV-001 | core-01 | core | Invariantes de los contratos (§5) | importante | `core/contracts/apu.py:193`; `core/contracts/item_computo.py:54` (sin coerción en `:39-40`) | `Rendimiento` e `ItemComputo` comparan el enum con `is` sin convertir la entrada: con la cadena en vez del miembro se saltan sus invariantes (`Rendimiento` «medido» sin `referencia_ejecucion`; `ItemComputo` «regla» sin `regla`; comprobado). Ningún llamador actual pasa cadenas (importante y no bloqueante: matiz en §5, R6) | Convertir en `__post_init__` con `TipoRendimiento(...)`, `OrigenTipo(...)` y `Dominio(...)`, como `LineaManoObra` (`apu.py:99`). **Cambia un contrato de `core/contracts/`: expediente en `docs/bitacora/` y aval del tutor** | C1 | aceptado por decisión de arquitectura registrada (pendiente del aval del tutor; [expediente](../bitacora/2026-09-23-C1-expedientes.md), §A) |
| INV-002 | core-02 | core | Decimal (principio 3) / contratos §5 | importante | `core/contracts/item_computo.py:42,57`; `core/contracts/apu.py:161-170`; `core/contracts/presupuesto.py:33-39`; `core/contracts/verificacion.py:28-38` | `ItemComputo.parametros`, los montos de `ResultadoAPU`, `PuntoCurva` y los campos numéricos de `Hallazgo` no exigen `Decimal` ni signo (se aceptan `1.5`, `-2.0`, `0.1`; comprobado). No se detectó uso real de `float`: falta la validación, no hay dato corrompido (importante y no bloqueante: matiz en §5, R6) | `_exigir_decimal` (`apu.py:13-23`) a todos esos campos; `_no_negativo` **solo** a los montos de `ResultadoAPU` y a `monto`/`acumulado` de `PuntoCurva`, **no** a `Hallazgo.impacto`, `valor_observado` ni `valor_esperado`, que R5 y R7 producen negativos por diseño (`core/verification/reglas.py:419,431-444,623-626`). Prueba de aceptación: R5 con balance negativo sigue produciendo el informe. **Cambia contratos de `core/contracts/`: expediente y aval del tutor.** Complementa a INV‑003 | C1 | aceptado por decisión de arquitectura registrada (pendiente del aval del tutor; [expediente](../bitacora/2026-09-23-C1-expedientes.md), §A) |
| INV-003 | core-03 | core | Informe siempre (principio 7) | importante | `core/verification/expresiones.py:125-138`; `core/verification/reglas.py:137`; promesa en `reglas.py:4-5` | Un valor no `Decimal` en `ItemComputo.parametros` lanza `TypeError` dentro de R1; sale de `auditar` y `elaborar` aborta sin presupuesto ni informe (comprobado) | Convertir `TypeError` en `ExpresionInvalida` en `_evaluar_binario` y `_evaluar_nodo`, para que R1 y R5 lo reporten como hallazgo | C1 | abierto |
| INV-004 | core-05 | core | DRY | importante | `core/catalog/precios.py:115-118` frente a `core/budget/actualizacion.py:306-308`; `precios.py:246` | La fórmula de variación de `modelo_datos.md` §6 está dos veces y difiere con precio anterior 0 (una devuelve 0, la otra lanza `DivisionByZero`; comprobado). El precio 0 es válido: `registrar_cambios` puede hacer fallar UC‑02. El camino que devuelve 0 (`_variacion`, base = PU anterior nulo) solo llena `IncidenciaCambio.variacion`, que ninguna pantalla, ruta de la API, informe ni script lee: no llega a un resultado publicado (R6, §5) | Una sola función de variación con política declarada para base nula, importada por los dos módulos | C1 | abierto |
| INV-005 | core-06 | core | DRY | importante | `core/catalog/rendimientos.py:100-146` frente a `core/catalog/repositorio.py:241-258`; `rendimientos.py:136-143` frente a `core/catalog/mapeo.py:231-244` | El registro de un rendimiento está implementado dos veces, con errores (`LookupError`/`CatalogoIncompleto`) y retornos distintos, y `rendimientos.py` construye `models.Rendimiento` fuera de `mapeo.py` (ADR 12) | `rendimientos.registrar_rendimiento` construye el contrato y delega en `Catalogo.registrar_rendimiento` y `a_rendimiento`; una sola excepción | C1 | abierto |
| INV-006 | core-07 + adaptadores-ml-api-01 | core (cruza: adapters) | DRY | importante | `core/verification/expresiones.py:1-159`; `adapters/{civil,industrial,sistemas,telecom}/evaluador.py`; civil e industrial idénticos salvo el docstring | El evaluador de expresiones trazables existe en cinco copias (núcleo y cuatro adaptadores); civil e industrial son clones línea a línea. Es **deuda declarada**: ADR 8 y arquitectura §6.1 (`docs/arquitectura.md:930,944`) declaran la del núcleo y la civil, y las bitácoras de I5 las otras tres (`docs/bitacora/2026-08-29-I5-industrial.md:31`, `…-I5-sistemas.md:30`, `…-I5-telecom.md:31`); la propia ADR prevé su cierre en `core.contracts.expresiones` | **C1:** un evaluador mínimo parametrizable (operadores permitidos como argumento) en `core.contracts`, único paquete que los adaptadores pueden importar; `core/verification/expresiones.py` lo usa. **Cambia `core/contracts/`: expediente y aval del tutor, o «aceptado por decisión de arquitectura registrada».** **C2 (subtarea, depende del aval):** migrar los cuatro adaptadores conservando los subconjuntos reducidos de sistemas y telecom. Si el aval no llega, la subtarea queda aceptada junto con el hallazgo padre. Documentación: INV‑058 | C1 (contrato) + C2 (adaptadores) | aceptado por decisión de arquitectura registrada (pendiente del aval del tutor; [expediente](../bitacora/2026-09-23-C1-expedientes.md), §A.3); la subtarea de C2 queda aceptada con él mientras no haya aval |
| INV-007 | tests-10 | tests (cruza: docs) | Pruebas (marcadores) | importante | `tests/unit/test_costing.py:1-10,20`; `pyproject.toml:50-52` | El marcador `rojo_esperado` y el docstring «fallan con ImportError» siguen en siete pruebas que pasan desde I0.3 | Retirar `pytestmark`, actualizar el docstring (ninguna aserción cambia, CLAUDE.md §9), retirar el marcador de `pyproject.toml` y el «estado esperado» de CLAUDE.md §9 (esto último cierra también esa parte de INV‑055) | C1 | abierto |
| INV-008 | tests-11 | tests (cruza: api, adapters) | DRY (línea base) | importante | `tests/unit/test_costing_destajo.py:28-34`; `tests/integration/test_api.py:34,78-82,108,111,138,256,338-339`; `tests/unit/test_adapter_civil_ifc.py:18-19`; `tests/unit/test_generador_ifc.py:21-23`; `tests/integration/test_actualizacion_precios.py:207-208,308-309`; `test_persistencia.py:94`; `test_rendimientos.py:35,146,193`; `test_api_rendimientos.py:17,122` | Cifras y códigos de la línea base escritos como literales fuera de `tests/fixtures/apu_linea_base.py` (los cinco PU, `"1586.61"`, `"0.224"`, `"LB-0x-…"`, precios, rendimiento 80) | Importar de `apu_linea_base`; mover los PU exactos al fixture | C1 | abierto |
| INV-009 | tests-12 | tests (cruza: adapters) | DRY (entre pruebas) | importante | `tests/unit/test_escenarios.py:39-40` y `tests/integration/test_actualizacion_precios.py:52,57`; `test_tarifas_sistemas.py:31` y `test_presupuesto_sistemas.py:44`; `tests/fixtures/presupuesto_auditado.py:47` frente a `tests/unit/test_reglas_civil.py:31,112` | El mismo esperado en dos o tres archivos: incremento UC‑02 de 30,17025, PU de sistemas 110,992365 y factor de sección de la tubería de 4" (con dos precisiones distintas) | Un solo lugar por valor en `tests/fixtures/` (el factor derivado de `adapters.civil.reglas`) | C1 | abierto |
| INV-010 | tests-15 | tests | D (regla de dependencia) / trazabilidad | importante | `tests/unit/test_arquitectura.py:17,55-58` | `PAQUETES_FUERA_DEL_NUCLEO` omite `scripts` y `tests`: la regla «`core/` no importa de `scripts/`» no tiene prueba (hoy se cumple) | Añadir `"scripts"` y `"tests"` a la tupla (es la ampliación de la guardia que la spec §5 pone al inicio de C1) | C1 | abierto |
| INV-011 | docs-normativos-01 + tests-17 | tests (cruza: adapters, docs) | Trazabilidad | importante | `docs/ERS.md:465-466` (RF‑19, RF‑20), `:203-208` (UC‑04); `docs/plan_pruebas.md:146-147`; `tests/unit/test_reglas_civil.py:76-218`, `tests/unit/test_budget.py:79-222` (ninguna cambia el ancho ni suma diferenciales); `grep -r diferencial tests/` vacío | RF‑19 (sensibilidad al ancho) y RF‑20 (diferencial por partida) figuran «verde» citando pruebas que no existen; UC‑04 (pasos 1‑5, flujos 1a, 2a, 2b) no tiene ninguna prueba | Escribir las dos pruebas contra la función que realiza cada comportamiento y trazar cada paso de UC‑04; si RF‑20 no tiene implementación, declararlo sin cumplir. Mientras tanto, «sin prueba» en ERS §3.2/§4 y plan_pruebas §8 (subtarea documental, C4) | C1 (+ C4, documentos) | abierto |
| INV-012 | tests-18 | tests (cruza: core, docs) | Trazabilidad | importante | `docs/ERS.md:469` (RF‑23), `:234` (UC‑05 2a), `:238` (UC‑05 3a) frente a `tests/unit/test_verification.py:371-372,391-398,446-456,515-540` | RF‑23 y UC‑05 3a exigen INFO «regla no evaluable»; las pruebas fijan ERROR «no se puede evaluar». UC‑05 2a exige declarar R7 no aplicable sin plan; la prueba fija que R7 calla | Decidir cuál manda y alinear RF, regla y prueba en el mismo cambio | C1 | abierto |
| INV-013 | tests-19 | tests (cruza: core, docs) | Trazabilidad | importante | `docs/ERS.md:139` (UC‑01 3a) frente a `tests/unit/test_budget.py:95-107` | UC‑01 3a: un ítem sin partida queda pendiente, no suma y el informe lo declara; la prueba fija que `generar_presupuesto` lanza `ValueError` sin presupuesto ni informe | Alinear el UC o la implementación, y la prueba con el que quede. Toca `generar_presupuesto`, igual que INV‑037 e INV‑069. `Presupuesto` no tiene lugar para partidas pendientes (`core/contracts/presupuesto.py:41-46`): declarar una ruta **sin** cambio de contrato (pendientes en `InformeAuditoria` o en `ResultadoElaboracion`) o, si hace falta el contrato, **expediente en `docs/bitacora/` y aval del tutor** | C1 | abierto |
| INV-014 | tests-20 | tests | Trazabilidad | importante | `docs/ERS.md:457-458` (RF‑11, RF‑12) frente a `tests/integration/test_actualizacion_precios.py:279-309`, `tests/integration/conftest.py:40-45` | Ninguna prueba compara las composiciones antes y después de UC‑02 (RF‑11) ni relee los cambios tras cerrar la sesión (RF‑12) | Comparar `Catalogo.composicion` de las cinco partidas antes y después; prueba con base en `tmp_path` que confirme, cierre el motor y relea los `CambioPrecio` | C1 | abierto |
| INV-015 | tests-21 | tests | Trazabilidad | importante | `docs/ERS.md:167` (UC‑02 2b), `:170` (UC‑02 7a); ausencia en `tests/` | Ninguna prueba ejercita el rechazo de una fila con unidad no equivalente ni la conservación del registro de cambios al descartar la versión nueva | Una prueba por flujo alternativo en `test_actualizacion_precios.py`; alimenta la matriz de INV‑033 | C1 | abierto |
| INV-016 | tests-07 | tests | Pruebas (aserciones triviales) | importante | `tests/integration/test_auditoria_arenaza.py:86,142` | La línea 86 compara dos presupuestos reconstruidos por separado y no detecta que `auditar` mute (RF‑23); la 142 afirma sobre una lista que la 141 ya afirmó vacía | Comparar el mismo objeto antes y después de `auditar`; borrar la 142 | C2 | abierto |
| INV-017 | tests-09 | tests (cruza: scripts) | Pruebas (aserción trivial) | importante | `tests/unit/test_resultados_ml.py:54-55,62` | `"5" in informe and "50" in informe` y `"reglas" in informe.lower()` se cumplen con cualquier fecha o importe: no verifican el conteo G2 ni la técnica (RF‑28) | Afirmar la fila exacta `"\| civil \| 5 \| reglas \|"` y la sección de limitación, como `test_resultados_ml_multidominio.py:76` | C2 | abierto |
| INV-018 | tests-14 | tests | DRY / pruebas | importante | `tests/unit/test_arquitectura.py:43-52`; `test_adapter_civil_ifc.py:61-73`; `test_adapter_telecom.py:145-179`; `test_adapter_industrial.py:68-81`; `test_adapter_sistemas.py:91-109` | La guarda «un adaptador solo importa `core.contracts`» está en cinco archivos con criterios distintos; la regla completa (sin importar otro adaptador, recursiva) solo rige para telecom | Una sola prueba parametrizada por paquete en `test_arquitectura.py` con la regla de telecom (biblioteca estándar + `core.contracts` + el propio paquete, sin otro adaptador) **más los terceros permitidos por adaptador**, declarados en la parametrización (civil: `ifcopenshell`); borrar las copias | C2 | abierto |
| INV-019 | tests-01 | tests | Pruebas (aislamiento: cwd) | importante | `tests/unit/test_referencia_maprex.py:6`; `tests/unit/test_fuentes_arenaza.py:14` | Rutas relativas al cwd: 7 casos fallan si pytest se lanza fuera de la raíz (reproducido) | Anclar en `Path(__file__).resolve().parents[2]`, como `test_adapter_telecom.py:23` | C3 | abierto |
| INV-020 | tests-02 | tests | Pruebas (aislamiento: reloj) | importante | `tests/integration/test_seed_demo.py:91,109` | La valoración se comprueba en `date.today()`: depende del reloj (antes del 2026‑04‑28 falla; hasta `FECHA_DEMO` no ejercita la lista de la demostración) | Fijar la fecha: `seed_demo.FECHA_DEMO` o una fecha fija declarada | C3 | abierto |
| INV-021 | tests-03 | tests | Pruebas (estado compartido) | importante | `tests/unit/test_visor3d.py:65-68` frente a `tests/unit/test_composicion_ia.py:397-417`; síntoma en `test_ui_componer.py:21-30` | `_SinIfcopenshell` restaura `sys.modules` pero no los atributos del paquete padre; el arreglo solo está en la copia de `test_composicion_ia.py` | Un solo gestor de contexto «sin extra» con la resincronización en `tests/fixtures/` o `conftest.py` | C3 | abierto |
| INV-022 | tests-04 | tests | Pruebas (aislamiento: `data/apu.db`) | importante | `tests/unit/test_ui_app.py:80-85`; guarda correcta en `test_ui_componer.py:107-111` | El arranque real de la app solo desvía la ruta de `ui.paginas.actualizacion`, la página por defecto de hoy; cuando el Inicio pase a serlo (RF‑36) la prueba abrirá `data/apu.db` sin fallar | Desviar la fuente única (RF‑38) y afirmar tras `at.run()` que el temporal existe y `data/apu.db` no se creó. **Nota:** la Tarea 10 de U1 reescribe este archivo con desvío por `ui.caso`; la afirmación final se añade ahí. La salvaguarda de sesión de C1 detecta la escritura, no la desviación ausente | C3 | abierto |
| INV-023 | tests-05 | tests (cruza: docs) | Pruebas (aserción vacía) | importante | `tests/unit/test_ui_importable.py:4-17`; citada en `docs/plan_pruebas.md` §8 (RF‑16, RF‑31) | La prueba no tiene aserciones: promete «sin efectos» y no comprueba ninguno | Afirmar la ausencia de efectos (cwd temporal, ningún archivo creado) o renombrarla como humo de importación y dejar de citarla como evidencia. **Nota:** la Tarea 10 de U1 reescribe el archivo, pero su versión tampoco afirma efectos | C3 | abierto |
| INV-024 | tests-06 | tests | Pruebas (aserciones triviales) | importante | `tests/unit/test_visor3d.py:83-85`; `tests/unit/test_composicion_ia.py:430-431` | `importlib.import_module(...) is not None` no puede fallar | Comprobación con fase roja (el módulo expone `render`; `ifcopenshell`/`ml` no quedó en `sys.modules`) | C3 | abierto |
| INV-025 | tests-08 | tests | Pruebas (aserción débil) | importante | `tests/unit/test_simulador.py:19` | `in (["Cemento Portland"], [])` acepta la lista vacía: pasa aunque el filtro `solo` no produzca variación | Con semilla fija, afirmar exactamente `["Cemento Portland"]` y que Arena conserva su precio | C3 | abierto |
| INV-026 | tests-22 | tests (cruza: docs) | Trazabilidad | importante | `docs/ERS.md:449-450` (RF‑03, RF‑04), `:470` (RF‑24); `docs/plan_pruebas.md:150`; `tests/unit/test_verification.py:263-270`; `tests/unit/test_adapter_civil_ifc.py:12-20` | La matriz cita pruebas que no verifican lo afirmado: `test_linea_base.py` no construye `ItemComputo`; la unidad «mts» se afirma en `test_verification.py`, no en `test_auditoria_7_de_7.py`; RF‑04 figura «pendiente» y `test_adapter_civil_ifc.py` lo cubre | Corregir la columna de criterio en ERS §3.2 y la fila de `plan_pruebas.md` §8. La parte de RF‑04 se corrige junto con INV‑028 | C4 | abierto |
| INV-027 | docs-normativos-02 | docs | Coherencia documental | importante | `docs/ERS.md:462,548,554`; `docs/plan_pruebas.md:144,170-173`; `docs/calidad_iso25010.md:27-29,150`; `docs/manual_tecnico.md:246` | RF‑16 tiene dos estados contradictorios dentro de la ERS y entre la ERS y el plan de pruebas | Fijar un único estado de RF‑16 y propagarlo (no reabre D5) | C4 | abierto |
| INV-028 | docs-normativos-03 | docs (cruza: adapters) | Coherencia documental | importante | `docs/ERS.md:408,450,531,545`; `docs/arquitectura.md:98,619,864,872-905,881` frente a `adapters/civil/ifc.py:49`, `data/samples/tanquilla.ifc`, `tests/unit/test_adapter_civil_ifc.py`, `docs/plan_pruebas.md:51-54,135,213`, `docs/calidad_iso25010.md:139-144` | ERS y arquitectura dan la extracción IFC y `tanquilla.ifc` por pendientes y G1 abierta; existen el adaptador, la muestra y su prueba, y plan de pruebas y calidad dan G1 cruzada con salvedad | Pasar ERS §2.5, RF‑04, RNF‑09, la matriz UC‑01 y arquitectura §1, §2.3 (añadir `AdaptadorCivilIFC`) y §5 a «G1 cruzada con salvedad» | C4 | abierto |
| INV-029 | docs-normativos-04 | docs | Coherencia documental | importante | `docs/arquitectura.md:46-82,96-105,718,832,836,837` frente a `ml/normalization/normalizador.py:68`, `ml/anomaly/detector.py:83,103`, `ml/prediction/reglas.py:94,152` | Las vistas de casos de uso y de desarrollo describen un sistema anterior a I1 (sin UC‑10/11/12, estados viejos) y nombran funciones que no existen, aunque el documento dice copiar las firmas del código | Regenerar §1, §3.2 y §4 contra el código actual | C4 | abierto |
| INV-030 | docs-normativos-05 | docs (cruza: ui) | Coherencia documental | importante | `docs/ERS.md:421-423`; `docs/manual_usuario.md:91-105,143,151`; `docs/calidad_iso25010.md:30-32` | La ERS promete en la interfaz once casos de uso que la interfaz no ofrece (UC‑04, UC‑06, UC‑07 van por API o script); calidad lo da por cumplido | Declarar en ERS §3.1 qué capa realiza cada UC y retirar la afirmación de calidad; ninguna pantalla nueva (spec §2) | C4 | abierto |
| INV-031 | docs-normativos-06 + docs-tesis-02 | docs | Coherencia documental / DRY de cifras | importante | `docs/plan_pruebas.md:32` (13 endpoints; hay 18), `:128`, `:216-246`; `docs/calidad_iso25010.md:47,67,120,151`; `docs/dossier_g0.md:32`; `README.md:42`; `docs/tesis/plan_redaccion.md:96,151,195` («395 pruebas», «núcleo 98,05 %») | Las cifras de suite, cobertura y API se contradicen entre documentos y están desfasadas (395, 392, 479, 490; hoy hay 562 funciones `test_`), incluida la tabla de cifras citables del plan de redacción, fuente de los capítulos | **C4:** medir sobre una corrida de CI, registrarla solo en plan_pruebas §10 y enlazarla (metodologia §6). **Red (subtarea):** la fila «Suite y cobertura» de `plan_redaccion.md` §5 y sus dos menciones narrativas enlazan esa cifra | C4 + Red | abierto |
| INV-032 | docs-normativos-07 | docs | DRY | importante | `docs/ERS.md:447-488,543-556`; `docs/plan_pruebas.md:130-168`; `README.md:44-59`; `docs/metodologia.md:164-175` | La correspondencia RF → prueba → estado está copiada en cuatro lugares y ya diverge (INV‑027, INV‑028) | Declarar en metodologia §5.1 a plan_pruebas §8 como fuente única; la ERS conserva el criterio sin estado y enlaza; el README enlaza | C4 | abierto |
| INV-033 | docs-normativos-08 | docs | Trazabilidad | importante | `docs/plan_pruebas.md:181-199` (matriz por paso solo de UC‑12); `docs/metodologia.md:123-126`; `docs/ERS.md:136-145,210-215` | UC‑01 a UC‑11 no tienen matriz por paso: sus pasos y flujos alternativos no citan prueba ni caso manual | Ampliar plan_pruebas §8 a todos los UC (condición F5) y registrar cada paso sin prueba; la alimentan INV‑011, INV‑013 e INV‑015 | C4 | abierto |
| INV-034 | docs-tesis-01 | docs | Coherencia documental | importante | `docs/tesis/plan_redaccion.md:111,131` frente a `docs/ERS.md:20,421-422,517,532` | El guion del capítulo IV cita el conteo de G0 (8 UC, 31 RF, 9 RNF, ocho pantallas); la ERS vigente tiene 42 RF, 10 RNF, once UC y diez pantallas | Actualizar las dos líneas a la ERS vigente o poner una nota de vigencia como la de `calidad_iso25010.md` | Red | abierto |
| INV-035 | docs-tesis-03 | docs | Coherencia documental / DRY | importante | `docs/tesis/plan_redaccion.md:150` frente a `docs/calidad_iso25010.md:148-157` | El guion del capítulo V reproduce de memoria «5 cumplen, 1 pendiente, 2 parciales»; la fuente única dice 6/1/1 | Citar `calidad_iso25010.md` §9 en vez de reproducir el conteo | Red | abierto |
| INV-036 | docs-tesis-04 | docs | Coherencia documental | importante | `docs/tesis/plan_redaccion.md:158-159` frente a `docs/plan_pruebas.md:211`, `docs/calidad_iso25010.md:155` | El guion de conclusiones manda declarar RNF‑07 como limitación pendiente (ya cumple por CI) y omite RNF‑09 (parcial) y RNF‑10 (pendiente) | Quitar RNF‑07 y añadir RNF‑09 y RNF‑10 con su fuente. Hermano de INV‑054 (RNF‑07 en los documentos normativos) | Red | abierto |
| INV-037 | core-04 | core (cruza: api, ui, scripts) | Informe siempre (principio 7) | menor | `core/budget/presupuesto.py:39-64`; `core/budget/__init__.py:12-13,56`; llamadores: `api/rutas/presupuestos.py:85-96`, `ui/paginas/elaborar.py:227`, `scripts/seed_industrial.py:201` | `generar_presupuesto` es pública y devuelve un `Presupuesto` sin informe, contra «no existe forma de obtener el presupuesto sin su informe»; se usa como borrador antes de `elaborar` | Que `elaborar` acepte un generador de plan y volver privada `generar_presupuesto`, o documentarla como paso intermedio sin valor de entrega; llamadores en commits separados. Se corrige junto con INV‑069 (el protocolo repetido); menor correcto frente a RF‑02, porque `elaborar` sí audita siempre | C1 | a limitaciones |
| INV-038 | core-08 + adaptadores-ml-api-02 | core (cruza: ml) | DRY | menor | `core/budget/excel.py:35,53-54`; `core/verification/texto.py:9-10,76-89`; `ml/prediction/reglas.py:186-193` | El redondeo de presentación (`quantize` a `DECIMALES_PRESENTACION` con `ROUND_HALF_UP`) está escrito tres veces: dos en el núcleo (aunque `texto.py` afirma «una sola copia») y una en `ml/`, que no puede importar `core.verification`. El cuarto `quantize` del núcleo (`core/budget/curva.py:114`) es el redondeo del plan de trabajo, no de presentación: caso distinto, fuera de este hallazgo | **C1:** un `redondear(valor, decimales)` único; si vive en `core/verification/texto.py` basta para el núcleo; para que `ml/` lo importe debe ir a `core.contracts`, lo que **cambia `core/contracts/`: expediente y aval del tutor**. **C2 (subtarea):** `ml/prediction/reglas.py` lo importa | C1 + C2 | a limitaciones |
| INV-039 | core-09 | core | S | menor | `core/catalog/precios.py:3-20,41-44` | Un módulo lee CSV/XLSX, persiste la lista y registra el historial: tres razones de cambio nombradas en su propio docstring | Separar la lectura de archivos (p. ej. `core/catalog/lector_precios.py`) de la persistencia | C1 | a limitaciones |
| INV-040 | core-10 | core (cruza: ui, api) | D (inversión estricta) | menor | `core/budget/actualizacion.py:25,87,275`; `core/budget/escenarios.py:30,108-128` | La API pública de `core.budget` devuelve `pandas.DataFrame`; no impide las pruebas | Devolver tuplas de dataclasses con `Decimal` y construir el `DataFrame` en `ui/` o `api/` | C1 | a limitaciones |
| INV-041 | adaptadores-ml-api-03 | adapters | DRY | menor | `adapters/civil/tabular.py:30-43`; `adapters/industrial/adaptador.py:23-36`; `adapters/sistemas/adaptador.py:43-57`; `adapters/telecom/adaptador.py:25-38` | `_parsear_especificaciones` está duplicada en los cuatro adaptadores tabulares, sin la justificación arquitectónica del evaluador | **No se extrae:** la duplicación es el precio declarado de la autonomía de los adaptadores (bitácoras de I5; `tests/unit/test_adapter_telecom.py:154-170` prohíbe importar otro adaptador), así que va a limitaciones (R5), o por la vía de contrato de INV‑006 si el tutor la avala. Alternativa descartada: un módulo compartido dentro de `adapters/` (p. ej. `adapters/_texto.py`), que no toca `core/` pero rompería esa autonomía | C2 | a limitaciones |
| INV-042 | tests-13 | tests | DRY (entre pruebas) | menor | `tests/integration/test_api.py:14-22,55-72`; `test_api_escenarios.py:29-37,43-57`; `test_api_rendimientos.py:21-29` | La fixture `cliente` está copiada tres veces y la carga útil de ítems dos | Moverlas a `tests/integration/conftest.py` | C2 | promovido |
| INV-043 | ui-01 | ui | S | importante | `ui/paginas/componer.py:29,32,55,111-193,639-665,682-834` | `componer.py` (871 líneas) pinta, calcula (`calcular_apu`), persiste (UC‑10/UC‑11) y reimplementa un recorte de UC‑01 (elaborar y exportar). Esa orquestación repetida es INV‑069: un cambio del protocolo obliga a cambiar también esta página, así que la violación S obliga a cambiar varias partes por un solo hecho (spec §4, importante; §5, R2). La arquitectura afirma lo contrario (INV‑070) | Separar la composición de la orquestación «cantidades → elaborar → exportar». Por spec §5 la hace **solo la Tarea 11 de U1**, que hoy no reescribe `componer.py` (solo la ruta de `:109` y el título): **el primer commit de C3 enmienda la Tarea 11** para incluir la extracción y refresca sus anclas de línea | C3 | abierto |
| INV-044 | ui-02 + scripts-05 | ui (cruza: scripts) | DRY | menor | `ui/paginas/{actualizacion.py:47, catalogo.py:24, componer.py:79, elaborar.py:38, escenarios.py:43, historico.py:25, similares.py:40, simulador.py:25}`; `scripts/seed.py:41`; `scripts/seed_demo.py:109,123`; `scripts/simular_lista.py:86-87`; `ui/app.py:18-23` | El literal `"data/apu.db"` como ruta por defecto está en ocho páginas y tres scripts, aunque `seed_demo.py` ya importa `scripts.seed` | **Previsto en U1** para `ui/`: la Tarea 8 crea la definición única en `ui/caso.py` y la **Tarea 11** retira las ocho copias de las páginas. La parte de `scripts/` no está en U1: `seed_demo.py` y `simular_lista.py` importan `seed.RUTA_POR_DEFECTO` | C3 | promovido |
| INV-045 | ui-03 | ui | DRY / presentación | menor | `ui/paginas/componer.py:56-57,471-476,521-553,668-670,848`; contraste `ui/paginas/similares.py:130-176` | `componer.py` muestra `Decimal` sin `formatear_decimal` en el desglose en vivo, el mensaje de guardado y el bloque de partidas similares | Pasar esos valores por `formatear_decimal(valor, DECIMALES_PRESENTACION)`. Se hace **después** de la Tarea 11 de U1, en un commit aparte (la Tarea 11 no reescribe esas líneas) | C3 | promovido |
| INV-046 | ui-04 | ui | DRY | menor | `ui/composicion.py:68-81` frente a `ui/paginas/componer.py:752-762` | `_celda_de_cantidad` duplica literalmente `ui.composicion._texto`, y su docstring lo reconoce | Hacer pública `_texto` e importarla, **después** de la Tarea 11 de U1 | C3 | promovido |
| INV-047 | scripts-01 | scripts | DRY / encapsulación | menor | `scripts/guardia_nucleo.py:25-31`; `scripts/verificar_omitidas.py:26`; `scripts/meta_{prototipo,datos,redaccion,i6,multidominio,asistente}.py` | Ocho módulos importan nombres con guion bajo de `scripts/meta_alpha.py`, que funciona como biblioteca interna sin interfaz declarada | Quitar el guion bajo a las funciones que cruzan módulos o extraerlas a `scripts/_comun.py` | C3 | a limitaciones |
| INV-048 | scripts-02 | scripts | DRY (sembradores) | menor | `scripts/seed_telecom.py:451-463`; `scripts/seed_industrial.py:141-153`; `scripts/seed_sistemas.py:131-143`; contraste `scripts/seed_demo.py` | Los tres sembradores de dominio no copian los precios de la lista vigente como hace `seed_demo.py`; si dos dominios compartieran base, `lista_vigente` podría resolver contra otro dominio. Latente (spec de UI §9, trabajo futuro) | Extraer «crear lista copiando la vigente» a una función compartida y usarla en los tres | C3 | a limitaciones |
| INV-049 | scripts-03 | scripts | DRY (redondeo de presentación) | menor | `scripts/seed_demo.py:544,546,549`; `scripts/seed_industrial.py:257,259`; `scripts/seed_sistemas.py:250,252`; `scripts/seed_telecom.py:572-573,577`; `scripts/simular_lista.py:59` | Los resúmenes CLI formatean con `:.2f` y `simular_lista.py` escribe `Decimal("0.01")`, en vez de usar `DECIMALES_PRESENTACION`/`formatear_decimal`, que `scripts/` ya puede importar | Sustituir por `formatear_decimal(valor, DECIMALES_PRESENTACION)` y la constante. Independiente de INV‑038 | C3 | promovido |
| INV-050 | scripts-04 | scripts | Gestión de datos / efectos destructivos | menor | `scripts/seed.py:41,118,125-126`; `scripts/seed_demo.py:58,123`; `scripts/seed_telecom.py:171,547-548`; `scripts/seed_industrial.py:91,231-232`; `scripts/seed_sistemas.py:92,221-222` | `--reiniciar` ejecuta `drop_all` de todo el esquema sin confirmación ni respaldo; en `seed.py` y `seed_demo.py` apunta por defecto a `data/apu.db`, la base de trabajo de la UI | Exigir confirmación (`--confirmar`) cuando `--reiniciar` va con la ruta por defecto, o negarse como `simular_corpus.py`. Cara documental: INV‑065 | C3 | promovido |
| INV-051 | scripts-06 | scripts | Coherencia documental | menor | `scripts/README.md:1-6`; `scripts/__init__.py:1` | El README de `scripts/` describe 2 de 24 scripts `.py` | Ampliar la tabla (agrupada por sesión o dominio) y el docstring del paquete | C3 | promovido |
| INV-052 | tests-16 | tests | DRY (ayudas compartidas) | menor | `tests/unit/test_ui_componer.py:64-69`; `tests/integration/test_composicion_extremo_a_extremo.py:54` | Dos módulos de prueba importan funciones privadas de otros módulos de prueba y acoplan `unit/` con `integration/` | Mover esas ayudas a `tests/fixtures/` | C3 | promovido |
| INV-053 | tests-23 | tests | Coherencia documental | menor | `tests/integration/test_seed_demo.py:82,99,117,141`; `tests/fixtures/presupuesto_auditado.py:211-213`; `tests/fixtures/presupuestos_arenaza.py:13-16`; `tests/unit/test_verification.py:460-461` | Docstrings obsoletos («Hoy falla», «se saltan mientras…», etc.) | Actualizarlos al comportamiento vigente | C4 | promovido |
| INV-054 | docs-normativos-09 | docs | Coherencia documental | importante | `docs/plan_pruebas.md:49-50`; `docs/dossier_g0.md:196`; `docs/manual_tecnico.md:246-248` frente a `docs/plan_pruebas.md:211`, `docs/calidad_iso25010.md:117-125` | RNF‑07 en Linux figura «pendiente» en tres lugares y «cumple» en dos | Retirar las menciones de pendiente; nota de vigencia en el dossier. Hermano de INV‑036 | C4 | abierto |
| INV-055 | docs-normativos-10 | docs | Coherencia documental (CLAUDE.md §6) | menor | `CLAUDE.md:173,174-176,179,181,238-239` | El árbol de §6 (fuente única de la estructura) no coincide con el repositorio; queda el estado esperado previo a I0.3 | Actualizar el árbol; el estado de §9 lo cierra INV‑007 | C4 | promovido |
| INV-056 | docs-normativos-11 | docs | Coherencia documental | menor | `README.md:31-33,64-71`; `docs/README.md:3-20`; `docs/manual_tecnico.md:191-206` | El README raíz, el índice de `docs/` y la tabla de scripts del manual técnico están desfasados e incompletos | Actualizar ambos índices y la tabla de scripts | C4 | promovido |
| INV-057 | docs-normativos-12 | docs | Coherencia documental | importante | `CLAUDE.md:137`; `docs/arquitectura.md:109-145` frente a `core/contracts/apu.py:69,94` | La tabla de contratos y el diagrama omiten `ModalidadManoObra` y `LineaManoObra.modalidad` (no reabre D9) | Añadirlos a los dos documentos | C4 | abierto |
| INV-058 | docs-normativos-13 | docs (cruza: core, adapters) | DRY | importante | `docs/arquitectura.md:930,944`; `docs/manual_tecnico.md:95-96` | La arquitectura (ADR 8 y §6.1, material del capítulo IV) declara dos copias del evaluador y hay cinco; las otras tres solo las declaran las bitácoras de I5. El manual enseña a crear otra por dominio | Alinear ADR 8, §6.1 y el manual con la corrección de INV‑006 | C4 | abierto |
| INV-059 | docs-normativos-14 | docs (cruza: ui, api) | SOLID‑O (declaración) | menor | `docs/manual_tecnico.md:137-139`; `ui/paginas/elaborar.py:46-48`; `api/rutas/computos.py:31-54`; `docs/arquitectura.md:770-854` | Los puntos de composición que enumeran dominios solo se declaran en el manual; el criterio O exige declararlos en la arquitectura | Declararlos en arquitectura §4 | C4 | promovido |
| INV-060 | docs-normativos-15 | docs | Datos ficticios (CLAUDE.md §1) | importante | `docs/ERS.md:453`; `docs/protocolo_precios.md:117`; `docs/dossier_g0.md:82-94` | Dos documentos llaman «real» al caso didáctico y el protocolo no recoge la verificación de D4 | «Caso didáctico» y enlace a D4 | C4 | abierto |
| INV-061 | docs-normativos-16 | docs | Coherencia documental | importante | `docs/modelo_datos.md:3,427-438` frente a `docs/README.md:9`, `docs/ERS.md:5` | El modelo de datos se declara «aprobado» con G0 pendiente, y su cobertura por UC omite UC‑10/11/12 | «Completo, pendiente de G0»; añadir UC‑10, UC‑11 y UC‑12 | C4 | abierto |
| INV-062 | docs-normativos-17 | docs | Coherencia documental | importante | `docs/metodologia.md:238`; `docs/calidad_iso25010.md:76`; `docs/plan_pruebas.md:44` frente a `PLAN_DESARROLLO.md:517-519`, `PLAN_CIERRE.md:31-32` | Las mediciones pendientes siguen asignadas a la Fase 6, ya cerrada | Reasignarlas a Med con enlace a PLAN_CIERRE | C4 | abierto |
| INV-063 | docs-normativos-18 | docs | Coherencia documental | importante | `docs/ERS.md:7` frente a `PLAN_DESARROLLO.md:79`; `docs/dossier_g0.md:4` frente a `:44-186` | «Al menos 23 RF» frente a «al menos 20 RF»; el dossier dice «ocho decisiones» y son nueve | Unificar citando el PLAN; «nueve decisiones» | C4 | abierto |
| INV-064 | docs-normativos-19 | docs | Coherencia documental | importante | `docs/linea_base.md:81,94-96` frente a `docs/dossier_g0.md:56` | Dos defectos distintos llevan el número 8, y queda un párrafo previo a I3.2 | Renumerar o nombrar el defecto de D2 sin ordinal; tiempo pasado | C4 | abierto |
| INV-066 | docs-normativos-21 | docs | Coherencia documental | menor | `PLAN_ASISTENTE.md:1-20` frente a la spec de cierre `:60` | PLAN_ASISTENTE no dice que quedó fuera del límite (trabajo futuro) | Nota de vigencia que enlace la spec §2 | C4 | a limitaciones |
| INV-067 | docs-normativos-22 | docs | Coherencia documental | importante | `docs/calidad_iso25010.md:25-29,43` | El veredicto cita «tres RF no esenciales declarados arriba»; solo se declara RF‑16, que es esencial | Corregir la frase al actualizar las cifras (INV‑031) | C4 | abierto |
| INV-068 | docs-tesis-05 | docs | DRY / citación T8 | menor | `docs/tesis/referencias.md:521,534` | La nota de la entrada AACE 2020 aún justifica el sufijo «b», que dejó de hacer falta al corregir el año de la 56R‑08; no llega al texto de la tesis | Corregir la nota interna | Red | a limitaciones |
| INV-069 | revisión GC0 (arquitectura, A3) | core (cruza: ui, api, scripts) | DRY | importante | `ui/paginas/elaborar.py:218-268`; `ui/paginas/componer.py:791-835`; `api/rutas/presupuestos.py:85-96`; `scripts/seed_demo.py:345-360` (los sembradores de dominio, p. ej. `scripts/seed_industrial.py:201`, llaman solo al primer paso) | El protocolo de elaboración `generar_presupuesto` → `elaborar(..., plan=plan_secuencial(borrador))` (→ `exportar_excel` en las dos páginas) está escrito en cuatro sitios fuera de `core/budget`. Un cambio del protocolo (p. ej. el de INV‑013 o el de INV‑037) obliga a cambiar los cuatro | Un punto de entrada único en `core/budget` que encapsule borrador, plan secuencial y elaboración (con el informe siempre dentro), coordinado con INV‑013 e INV‑037; los llamadores de `ui/`, `api/` y `scripts/` se migran en commits separados | C1 | abierto |
| INV-070 | revisión GC0 (arquitectura, A4) | docs (cruza: ui) | Coherencia documental | importante | `docs/arquitectura.md:638-639` frente a `ui/paginas/componer.py:29,32,55,639-665,791-835` | La arquitectura afirma que `componer.py` «solo pinta», sin lógica de negocio propia; la página calcula, persiste y orquesta la elaboración (INV‑043, INV‑069). La vista de desarrollo llega al capítulo IV | Reescribir el párrafo cuando se cierren INV‑043 e INV‑069, describiendo el reparto que quede | C4 | abierto |
| INV-071 | planificación de C1 (Tarea 11) | core (cruza: ui) | Requisito (UC‑01) | importante | `core/budget/curva.py:85-90` (`plan_secuencial`), `:117-140` (`_validar`); `data/samples/civil/tanquillas_y_zanja.csv` (dos ítems `LB-01-EXC`: tanquilla y zanja) | `plan_secuencial` crea un período por **renglón** con fracción 1; con dos renglones del mismo código la fracción suma 2 y `generar_curva` lanza `PlanInvalido`. Elaborar la muestra civil tabular desde la interfaz falla (reproducido en C1) | `plan_secuencial` agrupa por código: un período por código distinto, en orden de primera aparición. Se corrige en `core/` | C1 si Eugenio lo ratifica en GC1; si no, fase siguiente | abierto |
| INV-072 | planificación de C1 (Tarea 11; expediente B.5) | ui (cruza: api) | Trazabilidad (UC‑01 3a) | importante | `ui/paginas/elaborar.py:225-226`, `ui/paginas/componer.py:798-800`, `api/rutas/presupuestos.py:79-81` frente a `core/catalog/repositorio.py:73-78,128-134` | El núcleo ya deja pendiente un ítem sin partida (INV‑013), pero la interfaz y la API piden antes las composiciones al catálogo, que lanza `KeyError` ante una partida desconocida: 3a no se alcanza de punta a punta, y la propuesta de tres partidas similares (UC‑03) no existe en ese flujo | Pedir composiciones solo de las partidas existentes y mostrar `ResultadoElaboracion.pendientes` con sus propuestas; persistir o re‑derivar los ítems pendientes al guardar/cargar (hoy el hallazgo PENDIENTE guardado apunta a un origen_id sin línea guardada); en commits de `ui/` y `api/` | C2 (api) + C3 (ui) | abierto |

## 4. Propuesta de triage para GC0

Aprobada por Eugenio tal cual el 2026‑09‑23.

Propuesta del consolidador para que Eugenio la apruebe o la modifique en GC0 (spec §4, «Triage»).
Los conteos reflejan la verificación de la Tarea 5 y las correcciones de GC0 (§5); cuadran con §3
(recontados con un script sobre la tabla).

### (a) Bloqueantes e importantes: entran

Un bloqueante: **INV‑065** (C1, junto a la salvaguarda; se cierra antes de cualquier ejecución del
guion). Los 48 importantes entran, por fase:

- **C1 (16):** INV‑001, INV‑002 (cambian contratos: expediente y aval), INV‑003, INV‑004, INV‑005,
  INV‑006 (contrato en C1; subtarea de migración en C2, que depende del aval), INV‑007, INV‑008,
  INV‑009, INV‑010, INV‑011 (subtarea documental en C4), INV‑012, INV‑013 (si exige contrato:
  expediente y aval), INV‑014, INV‑015, INV‑069 (llamadores de `ui/`, `api/` y `scripts/` en commits
  separados).
- **C2 (3):** INV‑016, INV‑017, INV‑018.
- **C3 (8):** INV‑019, INV‑020, INV‑021, INV‑022, INV‑023, INV‑024, INV‑025, INV‑043 (exige enmendar
  la Tarea 11 de U1 en el primer commit de C3).
- **C4 (18):** INV‑026, INV‑027, INV‑028, INV‑029, INV‑030, INV‑031 (subtarea en Red), INV‑032,
  INV‑033, INV‑054, INV‑057, INV‑058, INV‑060, INV‑061, INV‑062, INV‑063, INV‑064, INV‑067, INV‑070.
- **Red (3):** INV‑034, INV‑035, INV‑036.

### (b) Menores que se propone promover (12)

| ID | Fase | Por qué |
|---|---|---|
| INV‑050 | C3 | Riesgo de pérdida de datos: `--reiniciar` borra sin confirmar la base de trabajo por defecto; su cara documental, INV‑065, ya es bloqueante |
| INV‑044 | C3 | La parte de `ui/` ya está en U1 (Tareas 8 y 11); la de `scripts/` es una línea en `seed_demo.py`, que INV‑050 ya toca |
| INV‑049 | C3 | Barato; mismos cuatro sembradores que INV‑050 |
| INV‑045 | C3 | Barato; mismo archivo que INV‑043, que ya entra en C3; se hace después de la Tarea 11 |
| INV‑046 | C3 | Barato; mismo archivo que INV‑043 e INV‑045; después de la Tarea 11 |
| INV‑052 | C3 | Barato; `test_ui_componer.py` lo tocan la Tarea 11 (solo el desvío de la ruta) e INV‑043 |
| INV‑051 | C3 | Barato; es el mismo inventario de scripts que se escribe para INV‑055 e INV‑056 |
| INV‑042 | C2 | Barato; los archivos de la API ya se tocan en INV‑008 |
| INV‑053 | C4 | Barato; esos archivos se tocan en INV‑009, INV‑012 e INV‑020 |
| INV‑055 | C4 | Barato; INV‑007 ya edita `CLAUDE.md` §9 |
| INV‑056 | C4 | Barato; INV‑032 ya edita `README.md` |
| INV‑059 | C4 | Barato; arquitectura §4 se regenera en INV‑029 |

### (c) El resto: a limitaciones (9)

INV‑037 (C1; se corrige de hecho si se cierra INV‑069, que ya entra), INV‑038 (C1+C2; exige un
cambio de contrato para cubrir `ml/`), INV‑039, INV‑040, INV‑041 (C2; precio declarado de la
autonomía de los adaptadores, o vía de contrato de INV‑006 si el tutor la avala, R5), INV‑047,
INV‑048 (latente; ya declarado trabajo futuro en la spec de UI §9), INV‑066, INV‑068. INV‑037 puede seguir abierto después de cerrar INV‑069, porque INV‑069 no exige volver privada `generar_presupuesto`.

### (d) Conteo por fase y severidad

Cada hallazgo se cuenta en su fase principal (la primera de la columna «Fase destino»); las subtareas
en otra fase se anotan en (a).

| Fase | Bloqueante | Importante | Menor | Total | Menores promovidos | Menores a limitaciones |
|---|---|---|---|---|---|---|
| C1 | 1 | 16 | 4 | 21 | 0 | 4 |
| C2 | 0 | 3 | 2 | 5 | 1 | 1 |
| C3 | 0 | 8 | 9 | 17 | 7 | 2 |
| C4 | 0 | 18 | 5 | 23 | 4 | 1 |
| Red | 0 | 3 | 1 | 4 | 0 | 1 |
| **Total** | **1** | **48** | **21** | **70** | **12** | **9** |

Si se aprueba la propuesta, entran 61 hallazgos (1 bloqueante, 48 importantes y 12 menores
promovidos) y 9 van al capítulo de limitaciones.

## 5. Registro de cambios de severidad (Tarea 5)

Verificador independiente (no fue auditor ni consolidador), sobre la evidencia del commit
`cc2243c` (`git show cc2243c:<ruta>`; el código de `HEAD` es idéntico en `core`, `adapters`, `ml`,
`api`, `ui`, `scripts` y `tests`). Las afirmaciones «comprobado» de INV‑001, INV‑002 e INV‑003 se
reprodujeron en un intérprete sin tocar ninguna base.

**Filas verificadas: 44.** Los 36 importantes (no había bloqueantes) y 8 menores: la muestra de uno de
cada cinco en orden (INV‑041, INV‑046, INV‑051, INV‑056, INV‑061, INV‑066) más INV‑050 e INV‑065
(reinicio destructivo y `data/apu.db`). La muestra no tuvo ningún falso positivo, así que no fue
necesario verificar el resto de los menores.

**Dictámenes:** 43 confirmados · 1 severidad corregida · 0 falsos positivos.

| ID | Antes | Después | Motivo (spec §4) |
|---|---|---|---|
| INV‑065 | menor | **bloqueante** | «Una prueba que escribe en `data/apu.db` es bloqueante (pérdida de datos)». CP‑07 es un caso de prueba del plan (`docs/plan_pruebas.md:214`, RNF‑10), y el camino principal de su guion (`docs/guion_prueba_arenia.md:57`) ejecuta `seed_demo.py --reiniciar`, que hace `drop_all` (`scripts/seed_demo.py:479-480`) sobre la ruta por defecto `data/apu.db` (`:123`), la base de trabajo de la UI. Seguir el guion al pie de la letra borra esa base |

**Confirmados con matiz, sin cambio de severidad:**

- INV‑050 (menor): el reinicio es una opción explícita, que su ayuda describe como destructiva
  («borra el esquema»), y que los sembradores escriban en `data/apu.db` por defecto es diseño
  declarado (`README.md:29`, `CLAUDE.md` §6). Ninguna prueba automatizada ni la CI invoca un
  sembrador sin `--db` (`git grep` sobre `tests/` y `.github/`). El riesgo se materializa por el
  guion, que ya es bloqueante (INV‑065).
- INV‑006 (importante): la copia del núcleo y la del adaptador civil son un precio declarado
  (`docs/arquitectura.md:930`, ADR 8). Las otras tres copias no lo son, y la spec §4 nombra este
  mismo caso como hallazgo. *Nota de GC0:* la afirmación «las otras tres copias no lo son» queda
  sustituida por INV‑006 corregido: las tres están declaradas en las bitácoras de I5 (A5, R8).
- INV‑022 (importante): hoy la prueba no escribe en `data/apu.db`: el defecto es que falta la
  afirmación que lo garantiza. Por eso no es bloqueante; queda en el valor por defecto de pruebas.
- INV‑032 (importante): la tabla de `README.md:44-59` enumera archivo → qué comprueba, sin RF ni
  estado. El hallazgo se sostiene con las dos copias de la ERS (`:447-488`, `:543-556`) y
  `plan_pruebas.md` §8, que ya divergen (INV‑027).
- INV‑027, INV‑028, INV‑036 e INV‑054 (este último fuera de la muestra) tocan D5, la salvedad G1 y la
  salvedad RNF‑07 del dossier. No las duplican: registran contradicciones entre documentos que el
  dossier no capturó (spec §4).

### Correcciones de la compuerta GC0 (ronda 1)

Los cuatro encargos de GC0 (requisitos, arquitectura, pruebas y calidad, verificación de hechos)
aprobaron con correcciones; el controlador las resolvió en los dictámenes R1–R9, que mandan donde
difieren de una revisión. Las filas conservan su ID y su posición en §3; las que suben de severidad
ordenarían entre los importantes de su fase.

**Hallazgos nuevos**

| ID | Origen | Severidad | Fase | Motivo | Dónde ordenaría |
|---|---|---|---|---|---|
| INV‑069 | revisión de arquitectura A3; R1 | importante | C1 | DRY: el protocolo `generar_presupuesto` → `elaborar(plan=plan_secuencial(...))` está en cuatro sitios fuera de `core/budget`, y un solo cambio del protocolo obliga a cambiar los cuatro (spec §4, importante). Evidencia verificada: `ui/paginas/elaborar.py:227-242`, `ui/paginas/componer.py:802-817`, `api/rutas/presupuestos.py:85-95`, `scripts/seed_demo.py:345-360` | Último de los importantes de C1, tras INV‑015 |
| INV‑070 | revisión de arquitectura A4; R2 | importante | C4 | Contradicción documental que llega a la tesis: `docs/arquitectura.md:638-639` dice que `componer.py` «solo pinta» y la página calcula, persiste y orquesta | Último de los importantes de C4, tras INV‑067 |

**Cambios de severidad**

| ID | Antes | Después | Dictamen | Motivo (spec §4) |
|---|---|---|---|---|
| INV‑043 | menor | importante | R2 | Cumple los tres criterios de evidencia S y la orquestación que duplica (INV‑069) obliga a cambiar varias partes por un solo hecho. Entra a C3; exige enmendar la Tarea 11 de U1 en el primer commit de C3 |
| INV‑061 | menor | importante | R4 | Contradicción que llega a la tesis: `modelo_datos.md` se declara «aprobado» con G0 pendiente y su diagrama ER va al capítulo IV (`docs/tesis/plan_redaccion.md:29`) |
| INV‑064 | menor | importante | R4 | Contradicción que llega a la tesis: dos defectos distintos con el número 8 en `linea_base.md` (fuente del caso de estudio, citada ocho veces en el plan de redacción) y en el dossier |
| INV‑054 | menor | importante | R9 | Contradicción que llega a la tesis: RNF‑07 «pendiente» en plan de pruebas, dossier (fuente de las limitaciones, `plan_redaccion.md:158`) y manual técnico (anexo), y «cumple» en calidad |
| INV‑057 | menor | importante | R9 | Contradicción que llega a la tesis: el diagrama de contratos de arquitectura (material del capítulo IV, `plan_redaccion.md:29`) omite la modalidad a destajo ya implementada |
| INV‑058 | menor | importante | R9 | Contradicción que llega a la tesis: ADR 8 y §6.1 de arquitectura declaran dos copias del evaluador y hay cinco |
| INV‑060 | menor | importante | R9 | Contradicción que llega a la tesis: la ERS (anexo, `plan_redaccion.md:31-32`) llama «real» al caso didáctico, contra `CLAUDE.md` §1 |
| INV‑062 | menor | importante | R9 | Contradicción que llega a la tesis: metodología, calidad y plan de pruebas (fuentes de los capítulos III y V) asignan mediciones pendientes a la Fase 6, ya cerrada |
| INV‑063 | menor | importante | R9 | Contradicción que llega a la tesis: el encabezado de la ERS (anexo) y el dossier (fuente de limitaciones y anexo A) contradicen sus propios conteos |
| INV‑067 | menor | importante | R9 | Contradicción que llega a la tesis: el veredicto de `calidad_iso25010.md` (fuente del capítulo V) cita tres RF que el texto no declara |

**Cambio de fase sin cambio de severidad.** INV‑065 (bloqueante) pasa de C4 a C1 y se reescribe según
la revisión de pruebas y calidad (R3): lo afectado es la preparación común de CP‑01…CP‑06
(`docs/guion_prueba_arenia.md:55-60,77-78`), no CP‑07, que usa una base exclusiva (`:374-390`). Se
corrige junto a la salvaguarda de C1, y su condición de cierre es que ocurra antes de cualquier
ejecución del guion. Se descarta la propuesta A6 (C3), porque C1 llega antes.

**Matices de severidad, sin cambio (R6)**

- INV‑001 e INV‑002 siguen importantes y no son bloqueantes, aunque tocan contratos de `CLAUDE.md` §5.
  Lo que falta es la validación; ningún llamador de `adapters/`, `ml/`, `api/`, `ui/` ni `scripts/`
  pasa cadenas en vez de miembros del enum, y no hay uso real de `float`. El riesgo es latente y no
  hay datos corrompidos.
- INV‑004 sigue importante. Se verificó el camino que devuelve 0: `_variacion`
  (`core/budget/actualizacion.py:306-308`) solo llena `IncidenciaCambio.variacion` (`:205-217`), y
  ninguna pantalla, ruta de la API, informe ni script lee ese campo (`grep` de `IncidenciaCambio` y
  `.variacion` en `core/`, `ui/`, `api/`, `scripts/` y `ml/`). Los lectores publicados usan
  `CambioPrecio.variacion` (`ui/paginas/historico.py:85`, `api/rutas/listas.py:71`), que viene de
  `core/catalog/precios.py:115-118`, y esa función lanza error con base nula en vez de publicar un
  valor. No llega a un resultado publicado, así que no sube a bloqueante.

**Otras correcciones sin cambio de severidad**

- R7 (A1): la corrección de INV‑002 queda acotada. `_no_negativo` se aplica solo a los montos de
  `ResultadoAPU` y `PuntoCurva`, y no a los campos de `Hallazgo`, porque R5 y R7 producen negativos por
  diseño. Se añade una prueba de R5 con balance negativo.
- R5: INV‑041 sale de los promovidos y va a limitaciones, porque extraer la función contradice la
  autonomía declarada de los adaptadores. INV‑018 se reformula: la parametrización declara los
  terceros permitidos por cada adaptador (civil: `ifcopenshell`).
- R1: INV‑037 sigue menor (correcto frente a RF‑02) y se enlaza con INV‑069.
- R8/A5: INV‑006 se reformula como deuda declarada, cuyo cierre prevé la ADR 8. La subtarea de C2
  depende del aval; si el aval no llega, queda aceptada junto con el hallazgo padre.
- R8/A7: INV‑044 pasa a citar la Tarea 11 (no la 10) como la que retira las copias. INV‑045 e INV‑046
  se hacen después de la Tarea 11, que no reescribe `componer.py`. Se corrigen las justificaciones de
  INV‑045 e INV‑052 en §4 (b). Promover INV‑043 exige enmendar la Tarea 11.
- R8/A8: INV‑013 declara la ruta sin contrato, o bien expediente y aval.
- R8/A9: INV‑038 deja fuera `core/budget/curva.py:114`, que es el redondeo del plan y no el de
  presentación. INV‑002 justifica su severidad (primer matiz de R6).
- R8/H2: en §1 se declara el universo excluido. `.github/workflows/ci.yml` y `pyproject.toml` quedan
  pendientes de revisión en C1 por la capa `tests`.
- R8/H5: en §3 se declara el criterio de la regla por defecto de pruebas.
- R8/hechos: INV‑043 cita 871 líneas, no 872.

**Pasada de R9 por los 31 menores.** Cada menor se contrastó solo con los tres criterios que suben de
nivel: (1) pérdida de datos o escritura en `data/apu.db`, (2) requisito incumplido, (3) contradicción
que llega a la tesis. Para (3) se tomó como material de la tesis lo que `docs/tesis/plan_redaccion.md`
cita o manda anexar: `CLAUDE.md` §1, §4 y §8.1, `linea_base.md`, `metodologia.md`,
`calidad_iso25010.md`, `plan_pruebas.md`, `dossier_g0.md`, los diagramas de `arquitectura.md` y
`modelo_datos.md`, y la ERS y los manuales como anexos (`plan_redaccion.md:29-32`).

| ID | (1) | (2) | (3) | Resultado |
|---|---|---|---|---|
| INV‑037 | no | no: RF‑02 se cumple, `elaborar` audita siempre | no | menor |
| INV‑038 | no | no | no | menor |
| INV‑039 | no | no | no | menor |
| INV‑040 | no | no | no | menor |
| INV‑041 | no | no | no | menor (a limitaciones, R5) |
| INV‑042 | no | no | no | menor |
| INV‑043 | no | no | no | por R9, menor; sube a importante por R2 (S + DRY) |
| INV‑044 | no: es un literal, no escribe | no: RF‑38 está pendiente y previsto en U1, no incumplido | no | menor |
| INV‑045 | no | no: RF‑08 rige solo el XLSX | no | menor |
| INV‑046 | no | no | no | menor |
| INV‑047 | no | no | no | menor |
| INV‑048 | no: latente, no observado | no | no | menor |
| INV‑049 | no | no | no | menor |
| INV‑050 | latente: opción explícita documentada como destructiva; se materializa por el guion (INV‑065, bloqueante), como ya ponderó la Tarea 5 | no | no | menor (promovido) |
| INV‑051 | no | no | no: `scripts/README.md` no es material de la tesis | menor |
| INV‑052 | no | no | no | menor |
| INV‑053 | no | no | no | menor |
| INV‑054 | no | no | **sí** | **importante** |
| INV‑055 | no | no | no: el plan de redacción cita `CLAUDE.md` §1, §4 y §8.1, no el árbol de §6 | menor |
| INV‑056 | no | no | no: incompleto, no contradictorio | menor |
| INV‑057 | no | no | **sí** | **importante** |
| INV‑058 | no | no | **sí** | **importante** |
| INV‑059 | no | no | no: es una declaración que falta; el manual sí la hace y ningún documento la contradice | menor |
| INV‑060 | no | no | **sí** | **importante** |
| INV‑061 | no | no | sí | importante (R4) |
| INV‑062 | no | no | **sí** | **importante** |
| INV‑063 | no | no | **sí** | **importante** |
| INV‑064 | no | no | sí | importante (R4) |
| INV‑066 | no | no | no | menor |
| INV‑067 | no | no | **sí** | **importante** |
| INV‑068 | no | no | no: nota interna de `referencias.md`, el texto de la tesis cita bien | menor |

Resultado: siete menores suben por R9 (INV‑054, 057, 058, 060, 062, 063, 067), dos por R4 (INV‑061,
064) y uno por R2 (INV‑043). Quedan 21 menores.

### Correcciones de la compuerta GC0 (ronda 2)

Ninguna severidad cambia en esta ronda.

- INV‑065: la corrección deja de ser «un cambio documental de una línea». La corrección de C1 del guion
  tiene cuatro partes: (a) sembrar con `--db data/prueba_arenia.db`; (b) escribir esa base en el campo
  **Archivo SQLite** en la precondición de cada caso CP‑01…CP‑06 y tras cada F5; (c) anotar antes si
  existe `data/apu.db` y su fecha; (d) comprobar al final que no cambió. Motivo: sembrar en otra base no
  basta, porque la aplicación vuelve a `data/apu.db` por defecto y CP‑01 guarda `PRUEBA-01-TUB`
  (`docs/guion_prueba_arenia.md:60-63,101-102,157`). Se añade la nota: la Tarea 12 de U1 debe
  conservar la corrección o migrarla a `ARENIA_CASO`.
- §4 (c): se declara que INV‑037 puede seguir abierto después de cerrar INV‑069.
- INV‑041: la corrección propuesta empieza por el motivo de no extraer la función (autonomía declarada,
  R5); el módulo compartido queda como alternativa descartada.
- Registro de la Tarea 5: se anota que «las otras tres copias no lo son» queda sustituido por INV‑006
  corregido (A5, R8).
- R9, INV‑056: el motivo pasa a «incompleto, no contradictorio».
