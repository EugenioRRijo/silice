# Inventario del cierre de la tesis

**Fuente única del backlog del cierre** ([spec, §4](../superpowers/specs/2026-09-23-plan-cierre-tesis-design.md)).
Inventario **vivo**: se agregan aquí los hallazgos que aparezcan después de C0 hasta la condición F3.

**Commit auditado:** `cc2243cd5a7efd3b20dc82fe586484a6ef01fea8` · **Fecha:** 2026‑09‑23 · **Estado:** borrador (C0)

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
(1 bloqueante, 36 importantes, 31 menores).

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
| INV-065 | docs-normativos-20 | docs (cruza: scripts) | Pérdida de datos / pruebas (aislamiento: `data/apu.db`) | bloqueante | `docs/guion_prueba_arenia.md:57,59-63`; CP‑07 figura como caso de prueba en `docs/plan_pruebas.md:214` | El camino principal del guion de CP‑07, un caso de prueba del plan, ejecuta `seed_demo.py --reiniciar` (`drop_all`, `scripts/seed_demo.py:479-480`) sobre `data/apu.db`, la base de trabajo; la base aparte queda como variante 2b. Una prueba que escribe en `data/apu.db` es bloqueante (spec §4) | Hacer de `--db data/prueba_arenia.db` el camino principal. Cara documental de INV‑050. Debe cerrarse antes de ejecutar CP‑07 en Med | C4 | abierto |
| INV-001 | core-01 | core | Invariantes de los contratos (§5) | importante | `core/contracts/apu.py:193`; `core/contracts/item_computo.py:54` (sin coerción en `:39-40`) | `Rendimiento` e `ItemComputo` comparan el enum con `is` sin convertir la entrada: con la cadena en vez del miembro se saltan sus invariantes (`Rendimiento` «medido» sin `referencia_ejecucion`; `ItemComputo` «regla» sin `regla`; comprobado). Ningún llamador actual pasa cadenas | Convertir en `__post_init__` con `TipoRendimiento(...)`, `OrigenTipo(...)` y `Dominio(...)`, como `LineaManoObra` (`apu.py:99`). **Cambia un contrato de `core/contracts/`: expediente en `docs/bitacora/` y aval del tutor** | C1 | abierto |
| INV-002 | core-02 | core | Decimal (principio 3) / contratos §5 | importante | `core/contracts/item_computo.py:42,57`; `core/contracts/apu.py:161-170`; `core/contracts/presupuesto.py:33-39`; `core/contracts/verificacion.py:28-38` | `ItemComputo.parametros`, los montos de `ResultadoAPU`, `PuntoCurva` y los campos numéricos de `Hallazgo` no exigen `Decimal` ni signo (se aceptan `1.5`, `-2.0`, `0.1`; comprobado). No se detectó uso real de `float` | Aplicar `_exigir_decimal`/`_no_negativo` (`apu.py:13-23`) a esos campos. **Cambia contratos de `core/contracts/`: expediente y aval del tutor.** Complementa a INV‑003 | C1 | abierto |
| INV-003 | core-03 | core | Informe siempre (principio 7) | importante | `core/verification/expresiones.py:125-138`; `core/verification/reglas.py:137`; promesa en `reglas.py:4-5` | Un valor no `Decimal` en `ItemComputo.parametros` lanza `TypeError` dentro de R1; sale de `auditar` y `elaborar` aborta sin presupuesto ni informe (comprobado) | Convertir `TypeError` en `ExpresionInvalida` en `_evaluar_binario` y `_evaluar_nodo`, para que R1 y R5 lo reporten como hallazgo | C1 | abierto |
| INV-004 | core-05 | core | DRY | importante | `core/catalog/precios.py:115-118` frente a `core/budget/actualizacion.py:306-308`; `precios.py:246` | La fórmula de variación de `modelo_datos.md` §6 está dos veces y difiere con precio anterior 0 (una devuelve 0, la otra lanza `DivisionByZero`; comprobado). El precio 0 es válido: `registrar_cambios` puede hacer fallar UC‑02 | Una sola función de variación con política declarada para base nula, importada por los dos módulos | C1 | abierto |
| INV-005 | core-06 | core | DRY | importante | `core/catalog/rendimientos.py:100-146` frente a `core/catalog/repositorio.py:241-258`; `rendimientos.py:136-143` frente a `core/catalog/mapeo.py:231-244` | El registro de un rendimiento está implementado dos veces, con errores (`LookupError`/`CatalogoIncompleto`) y retornos distintos, y `rendimientos.py` construye `models.Rendimiento` fuera de `mapeo.py` (ADR 12) | `rendimientos.registrar_rendimiento` construye el contrato y delega en `Catalogo.registrar_rendimiento` y `a_rendimiento`; una sola excepción | C1 | abierto |
| INV-006 | core-07 + adaptadores-ml-api-01 | core (cruza: adapters) | DRY | importante | `core/verification/expresiones.py:1-159`; `adapters/{civil,industrial,sistemas,telecom}/evaluador.py`; civil e industrial idénticos salvo el docstring | El evaluador de expresiones trazables existe en cinco copias (núcleo y cuatro adaptadores); civil e industrial son clones línea a línea | **C1:** un evaluador mínimo parametrizable (operadores permitidos como argumento) en `core.contracts`, único paquete que los adaptadores pueden importar; `core/verification/expresiones.py` lo usa. **Cambia `core/contracts/`: expediente y aval del tutor, o «aceptado por decisión de arquitectura registrada».** **C2 (subtarea):** migrar los cuatro adaptadores conservando los subconjuntos reducidos de sistemas y telecom. Documentación: INV‑058 | C1 (contrato) + C2 (adaptadores) | abierto |
| INV-007 | tests-10 | tests (cruza: docs) | Pruebas (marcadores) | importante | `tests/unit/test_costing.py:1-10,20`; `pyproject.toml:50-52` | El marcador `rojo_esperado` y el docstring «fallan con ImportError» siguen en siete pruebas que pasan desde I0.3 | Retirar `pytestmark`, actualizar el docstring (ninguna aserción cambia, CLAUDE.md §9), retirar el marcador de `pyproject.toml` y el «estado esperado» de CLAUDE.md §9 (esto último cierra también esa parte de INV‑055) | C1 | abierto |
| INV-008 | tests-11 | tests (cruza: api, adapters) | DRY (línea base) | importante | `tests/unit/test_costing_destajo.py:28-34`; `tests/integration/test_api.py:34,78-82,108,111,138,256,338-339`; `tests/unit/test_adapter_civil_ifc.py:18-19`; `tests/unit/test_generador_ifc.py:21-23`; `tests/integration/test_actualizacion_precios.py:207-208,308-309`; `test_persistencia.py:94`; `test_rendimientos.py:35,146,193`; `test_api_rendimientos.py:17,122` | Cifras y códigos de la línea base escritos como literales fuera de `tests/fixtures/apu_linea_base.py` (los cinco PU, `"1586.61"`, `"0.224"`, `"LB-0x-…"`, precios, rendimiento 80) | Importar de `apu_linea_base`; mover los PU exactos al fixture | C1 | abierto |
| INV-009 | tests-12 | tests (cruza: adapters) | DRY (entre pruebas) | importante | `tests/unit/test_escenarios.py:39-40` y `tests/integration/test_actualizacion_precios.py:52,57`; `test_tarifas_sistemas.py:31` y `test_presupuesto_sistemas.py:44`; `tests/fixtures/presupuesto_auditado.py:47` frente a `tests/unit/test_reglas_civil.py:31,112` | El mismo esperado en dos o tres archivos: incremento UC‑02 de 30,17025, PU de sistemas 110,992365 y factor de sección de la tubería de 4" (con dos precisiones distintas) | Un solo lugar por valor en `tests/fixtures/` (el factor derivado de `adapters.civil.reglas`) | C1 | abierto |
| INV-010 | tests-15 | tests | D (regla de dependencia) / trazabilidad | importante | `tests/unit/test_arquitectura.py:17,55-58` | `PAQUETES_FUERA_DEL_NUCLEO` omite `scripts` y `tests`: la regla «`core/` no importa de `scripts/`» no tiene prueba (hoy se cumple) | Añadir `"scripts"` y `"tests"` a la tupla (es la ampliación de la guardia que la spec §5 pone al inicio de C1) | C1 | abierto |
| INV-011 | docs-normativos-01 + tests-17 | tests (cruza: adapters, docs) | Trazabilidad | importante | `docs/ERS.md:465-466` (RF‑19, RF‑20), `:203-208` (UC‑04); `docs/plan_pruebas.md:146-147`; `tests/unit/test_reglas_civil.py:76-218`, `tests/unit/test_budget.py:79-222` (ninguna cambia el ancho ni suma diferenciales); `grep -r diferencial tests/` vacío | RF‑19 (sensibilidad al ancho) y RF‑20 (diferencial por partida) figuran «verde» citando pruebas que no existen; UC‑04 (pasos 1‑5, flujos 1a, 2a, 2b) no tiene ninguna prueba | Escribir las dos pruebas contra la función que realiza cada comportamiento y trazar cada paso de UC‑04; si RF‑20 no tiene implementación, declararlo sin cumplir. Mientras tanto, «sin prueba» en ERS §3.2/§4 y plan_pruebas §8 (subtarea documental, C4) | C1 (+ C4, documentos) | abierto |
| INV-012 | tests-18 | tests (cruza: core, docs) | Trazabilidad | importante | `docs/ERS.md:469` (RF‑23), `:234` (UC‑05 2a), `:238` (UC‑05 3a) frente a `tests/unit/test_verification.py:371-372,391-398,446-456,515-540` | RF‑23 y UC‑05 3a exigen INFO «regla no evaluable»; las pruebas fijan ERROR «no se puede evaluar». UC‑05 2a exige declarar R7 no aplicable sin plan; la prueba fija que R7 calla | Decidir cuál manda y alinear RF, regla y prueba en el mismo cambio | C1 | abierto |
| INV-013 | tests-19 | tests (cruza: core, docs) | Trazabilidad | importante | `docs/ERS.md:139` (UC‑01 3a) frente a `tests/unit/test_budget.py:95-107` | UC‑01 3a: un ítem sin partida queda pendiente, no suma y el informe lo declara; la prueba fija que `generar_presupuesto` lanza `ValueError` sin presupuesto ni informe | Alinear el UC o la implementación, y la prueba con el que quede. Toca `generar_presupuesto`, igual que INV‑037 | C1 | abierto |
| INV-014 | tests-20 | tests | Trazabilidad | importante | `docs/ERS.md:457-458` (RF‑11, RF‑12) frente a `tests/integration/test_actualizacion_precios.py:279-309`, `tests/integration/conftest.py:40-45` | Ninguna prueba compara las composiciones antes y después de UC‑02 (RF‑11) ni relee los cambios tras cerrar la sesión (RF‑12) | Comparar `Catalogo.composicion` de las cinco partidas antes y después; prueba con base en `tmp_path` que confirme, cierre el motor y relea los `CambioPrecio` | C1 | abierto |
| INV-015 | tests-21 | tests | Trazabilidad | importante | `docs/ERS.md:167` (UC‑02 2b), `:170` (UC‑02 7a); ausencia en `tests/` | Ninguna prueba ejercita el rechazo de una fila con unidad no equivalente ni la conservación del registro de cambios al descartar la versión nueva | Una prueba por flujo alternativo en `test_actualizacion_precios.py`; alimenta la matriz de INV‑033 | C1 | abierto |
| INV-016 | tests-07 | tests | Pruebas (aserciones triviales) | importante | `tests/integration/test_auditoria_arenaza.py:86,142` | La línea 86 compara dos presupuestos reconstruidos por separado y no detecta que `auditar` mute (RF‑23); la 142 afirma sobre una lista que la 141 ya afirmó vacía | Comparar el mismo objeto antes y después de `auditar`; borrar la 142 | C2 | abierto |
| INV-017 | tests-09 | tests (cruza: scripts) | Pruebas (aserción trivial) | importante | `tests/unit/test_resultados_ml.py:54-55,62` | `"5" in informe and "50" in informe` y `"reglas" in informe.lower()` se cumplen con cualquier fecha o importe: no verifican el conteo G2 ni la técnica (RF‑28) | Afirmar la fila exacta `"\| civil \| 5 \| reglas \|"` y la sección de limitación, como `test_resultados_ml_multidominio.py:76` | C2 | abierto |
| INV-018 | tests-14 | tests | DRY / pruebas | importante | `tests/unit/test_arquitectura.py:43-52`; `test_adapter_civil_ifc.py:61-73`; `test_adapter_telecom.py:145-179`; `test_adapter_industrial.py:68-81`; `test_adapter_sistemas.py:91-109` | La guarda «un adaptador solo importa `core.contracts`» está en cinco archivos con criterios distintos; la regla completa (sin importar otro adaptador, recursiva) solo rige para telecom | Una sola prueba parametrizada por paquete en `test_arquitectura.py` con la regla de telecom; borrar las copias | C2 | abierto |
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
| INV-037 | core-04 | core (cruza: api, ui, scripts) | Informe siempre (principio 7) | menor | `core/budget/presupuesto.py:39-64`; `core/budget/__init__.py:12-13,56`; llamadores: `api/rutas/presupuestos.py:85-96`, `ui/paginas/elaborar.py:227`, `scripts/seed_industrial.py:201` | `generar_presupuesto` es pública y devuelve un `Presupuesto` sin informe, contra «no existe forma de obtener el presupuesto sin su informe»; se usa como borrador antes de `elaborar` | Que `elaborar` acepte un generador de plan y volver privada `generar_presupuesto`, o documentarla como paso intermedio sin valor de entrega; llamadores en commits separados | C1 | abierto |
| INV-038 | core-08 + adaptadores-ml-api-02 | core (cruza: ml) | DRY | menor | `core/budget/excel.py:35,53-54`; `core/verification/texto.py:9-10,76-89`; `ml/prediction/reglas.py:186-193` | El redondeo de presentación (`quantize` a `DECIMALES_PRESENTACION` con `ROUND_HALF_UP`) está escrito tres veces: dos en el núcleo (aunque `texto.py` afirma «una sola copia») y una en `ml/`, que no puede importar `core.verification` | **C1:** un `redondear(valor, decimales)` único; si vive en `core/verification/texto.py` basta para el núcleo; para que `ml/` lo importe debe ir a `core.contracts`, lo que **cambia `core/contracts/`: expediente y aval del tutor**. **C2 (subtarea):** `ml/prediction/reglas.py` lo importa | C1 + C2 | abierto |
| INV-039 | core-09 | core | S | menor | `core/catalog/precios.py:3-20,41-44` | Un módulo lee CSV/XLSX, persiste la lista y registra el historial: tres razones de cambio nombradas en su propio docstring | Separar la lectura de archivos (p. ej. `core/catalog/lector_precios.py`) de la persistencia | C1 | abierto |
| INV-040 | core-10 | core (cruza: ui, api) | D (inversión estricta) | menor | `core/budget/actualizacion.py:25,87,275`; `core/budget/escenarios.py:30,108-128` | La API pública de `core.budget` devuelve `pandas.DataFrame`; no impide las pruebas | Devolver tuplas de dataclasses con `Decimal` y construir el `DataFrame` en `ui/` o `api/` | C1 | abierto |
| INV-041 | adaptadores-ml-api-03 | adapters | DRY | menor | `adapters/civil/tabular.py:30-43`; `adapters/industrial/adaptador.py:23-36`; `adapters/sistemas/adaptador.py:43-57`; `adapters/telecom/adaptador.py:25-38` | `_parsear_especificaciones` está duplicada en los cuatro adaptadores tabulares, sin la justificación arquitectónica del evaluador | Extraerla a un módulo compartido de `adapters/` (p. ej. `adapters/_texto.py`); no toca `core/` | C2 | abierto |
| INV-042 | tests-13 | tests | DRY (entre pruebas) | menor | `tests/integration/test_api.py:14-22,55-72`; `test_api_escenarios.py:29-37,43-57`; `test_api_rendimientos.py:21-29` | La fixture `cliente` está copiada tres veces y la carga útil de ítems dos | Moverlas a `tests/integration/conftest.py` | C2 | abierto |
| INV-043 | ui-01 | ui | S | menor | `ui/paginas/componer.py:29,32,55,111-193,639-665,682-834` | `componer.py` (872 líneas) pinta, calcula (`calcular_apu`), persiste (UC‑10/UC‑11) y reimplementa un recorte de UC‑01 (elaborar y exportar) | Separar la composición de la orquestación «cantidades → elaborar → exportar». Por spec §5, si se promueve, la hace **solo la Tarea 11 de U1** | C3 | abierto |
| INV-044 | ui-02 + scripts-05 | ui (cruza: scripts) | DRY | menor | `ui/paginas/{actualizacion.py:47, catalogo.py:24, componer.py:79, elaborar.py:38, escenarios.py:43, historico.py:25, similares.py:40, simulador.py:25}`; `scripts/seed.py:41`; `scripts/seed_demo.py:109,123`; `scripts/simular_lista.py:86-87`; `ui/app.py:18-23` | El literal `"data/apu.db"` como ruta por defecto está en ocho páginas y tres scripts, aunque `seed_demo.py` ya importa `scripts.seed` | **Previsto en U1** para `ui/` (Tareas 8 y 10: `RUTA_BASE_POR_DEFECTO` única en `ui/caso.py`). La parte de `scripts/` no está en U1: `seed_demo.py` y `simular_lista.py` importan `seed.RUTA_POR_DEFECTO` | C3 | abierto |
| INV-045 | ui-03 | ui | DRY / presentación | menor | `ui/paginas/componer.py:56-57,471-476,521-553,668-670,848`; contraste `ui/paginas/similares.py:130-176` | `componer.py` muestra `Decimal` sin `formatear_decimal` en el desglose en vivo, el mensaje de guardado y el bloque de partidas similares | Pasar esos valores por `formatear_decimal(valor, DECIMALES_PRESENTACION)` | C3 | abierto |
| INV-046 | ui-04 | ui | DRY | menor | `ui/composicion.py:68-81` frente a `ui/paginas/componer.py:752-762` | `_celda_de_cantidad` duplica literalmente `ui.composicion._texto`, y su docstring lo reconoce | Hacer pública `_texto` e importarla | C3 | abierto |
| INV-047 | scripts-01 | scripts | DRY / encapsulación | menor | `scripts/guardia_nucleo.py:25-31`; `scripts/verificar_omitidas.py:26`; `scripts/meta_{prototipo,datos,redaccion,i6,multidominio,asistente}.py` | Ocho módulos importan nombres con guion bajo de `scripts/meta_alpha.py`, que funciona como biblioteca interna sin interfaz declarada | Quitar el guion bajo a las funciones que cruzan módulos o extraerlas a `scripts/_comun.py` | C3 | abierto |
| INV-048 | scripts-02 | scripts | DRY (sembradores) | menor | `scripts/seed_telecom.py:451-463`; `scripts/seed_industrial.py:141-153`; `scripts/seed_sistemas.py:131-143`; contraste `scripts/seed_demo.py` | Los tres sembradores de dominio no copian los precios de la lista vigente como hace `seed_demo.py`; si dos dominios compartieran base, `lista_vigente` podría resolver contra otro dominio. Latente (spec de UI §9, trabajo futuro) | Extraer «crear lista copiando la vigente» a una función compartida y usarla en los tres | C3 | abierto |
| INV-049 | scripts-03 | scripts | DRY (redondeo de presentación) | menor | `scripts/seed_demo.py:544,546,549`; `scripts/seed_industrial.py:257,259`; `scripts/seed_sistemas.py:250,252`; `scripts/seed_telecom.py:572-573,577`; `scripts/simular_lista.py:59` | Los resúmenes CLI formatean con `:.2f` y `simular_lista.py` escribe `Decimal("0.01")`, en vez de usar `DECIMALES_PRESENTACION`/`formatear_decimal`, que `scripts/` ya puede importar | Sustituir por `formatear_decimal(valor, DECIMALES_PRESENTACION)` y la constante. Independiente de INV‑038 | C3 | abierto |
| INV-050 | scripts-04 | scripts | Gestión de datos / efectos destructivos | menor | `scripts/seed.py:41,118,125-126`; `scripts/seed_demo.py:58,123`; `scripts/seed_telecom.py:171,547-548`; `scripts/seed_industrial.py:91,231-232`; `scripts/seed_sistemas.py:92,221-222` | `--reiniciar` ejecuta `drop_all` de todo el esquema sin confirmación ni respaldo; en `seed.py` y `seed_demo.py` apunta por defecto a `data/apu.db`, la base de trabajo de la UI | Exigir confirmación (`--confirmar`) cuando `--reiniciar` va con la ruta por defecto, o negarse como `simular_corpus.py`. Cara documental: INV‑065 | C3 | abierto |
| INV-051 | scripts-06 | scripts | Coherencia documental | menor | `scripts/README.md:1-6`; `scripts/__init__.py:1` | El README de `scripts/` describe 2 de 24 scripts `.py` | Ampliar la tabla (agrupada por sesión o dominio) y el docstring del paquete | C3 | abierto |
| INV-052 | tests-16 | tests | DRY (ayudas compartidas) | menor | `tests/unit/test_ui_componer.py:64-69`; `tests/integration/test_composicion_extremo_a_extremo.py:54` | Dos módulos de prueba importan funciones privadas de otros módulos de prueba y acoplan `unit/` con `integration/` | Mover esas ayudas a `tests/fixtures/` | C3 | abierto |
| INV-053 | tests-23 | tests | Coherencia documental | menor | `tests/integration/test_seed_demo.py:82,99,117,141`; `tests/fixtures/presupuesto_auditado.py:211-213`; `tests/fixtures/presupuestos_arenaza.py:13-16`; `tests/unit/test_verification.py:460-461` | Docstrings obsoletos («Hoy falla», «se saltan mientras…», etc.) | Actualizarlos al comportamiento vigente | C4 | abierto |
| INV-054 | docs-normativos-09 | docs | Coherencia documental | menor | `docs/plan_pruebas.md:49-50`; `docs/dossier_g0.md:196`; `docs/manual_tecnico.md:246-248` frente a `docs/plan_pruebas.md:211`, `docs/calidad_iso25010.md:117-125` | RNF‑07 en Linux figura «pendiente» en tres lugares y «cumple» en dos | Retirar las menciones de pendiente; nota de vigencia en el dossier. Hermano de INV‑036 | C4 | abierto |
| INV-055 | docs-normativos-10 | docs | Coherencia documental (CLAUDE.md §6) | menor | `CLAUDE.md:173,174-176,179,181,238-239` | El árbol de §6 (fuente única de la estructura) no coincide con el repositorio; queda el estado esperado previo a I0.3 | Actualizar el árbol; el estado de §9 lo cierra INV‑007 | C4 | abierto |
| INV-056 | docs-normativos-11 | docs | Coherencia documental | menor | `README.md:31-33,64-71`; `docs/README.md:3-20`; `docs/manual_tecnico.md:191-206` | El README raíz, el índice de `docs/` y la tabla de scripts del manual técnico están desfasados e incompletos | Actualizar ambos índices y la tabla de scripts | C4 | abierto |
| INV-057 | docs-normativos-12 | docs | Coherencia documental | menor | `CLAUDE.md:137`; `docs/arquitectura.md:109-145` frente a `core/contracts/apu.py:69,94` | La tabla de contratos y el diagrama omiten `ModalidadManoObra` y `LineaManoObra.modalidad` (no reabre D9) | Añadirlos a los dos documentos | C4 | abierto |
| INV-058 | docs-normativos-13 | docs (cruza: core, adapters) | DRY | menor | `docs/arquitectura.md:930,944`; `docs/manual_tecnico.md:95-96` | La arquitectura declara dos copias del evaluador (hay cinco) y el manual enseña a crear otra por dominio | Alinear ADR 8, §6.1 y el manual con la corrección de INV‑006 | C4 | abierto |
| INV-059 | docs-normativos-14 | docs (cruza: ui, api) | SOLID‑O (declaración) | menor | `docs/manual_tecnico.md:137-139`; `ui/paginas/elaborar.py:46-48`; `api/rutas/computos.py:31-54`; `docs/arquitectura.md:770-854` | Los puntos de composición que enumeran dominios solo se declaran en el manual; el criterio O exige declararlos en la arquitectura | Declararlos en arquitectura §4 | C4 | abierto |
| INV-060 | docs-normativos-15 | docs | Datos ficticios (CLAUDE.md §1) | menor | `docs/ERS.md:453`; `docs/protocolo_precios.md:117`; `docs/dossier_g0.md:82-94` | Dos documentos llaman «real» al caso didáctico y el protocolo no recoge la verificación de D4 | «Caso didáctico» y enlace a D4 | C4 | abierto |
| INV-061 | docs-normativos-16 | docs | Coherencia documental | menor | `docs/modelo_datos.md:3,427-438` frente a `docs/README.md:9`, `docs/ERS.md:5` | El modelo de datos se declara «aprobado» con G0 pendiente, y su cobertura por UC omite UC‑10/11/12 | «Completo, pendiente de G0»; añadir UC‑10, UC‑11 y UC‑12 | C4 | abierto |
| INV-062 | docs-normativos-17 | docs | Coherencia documental | menor | `docs/metodologia.md:238`; `docs/calidad_iso25010.md:76`; `docs/plan_pruebas.md:44` frente a `PLAN_DESARROLLO.md:517-519`, `PLAN_CIERRE.md:31-32` | Las mediciones pendientes siguen asignadas a la Fase 6, ya cerrada | Reasignarlas a Med con enlace a PLAN_CIERRE | C4 | abierto |
| INV-063 | docs-normativos-18 | docs | Coherencia documental | menor | `docs/ERS.md:7` frente a `PLAN_DESARROLLO.md:79`; `docs/dossier_g0.md:4` frente a `:44-186` | «Al menos 23 RF» frente a «al menos 20 RF»; el dossier dice «ocho decisiones» y son nueve | Unificar citando el PLAN; «nueve decisiones» | C4 | abierto |
| INV-064 | docs-normativos-19 | docs | Coherencia documental | menor | `docs/linea_base.md:81,94-96` frente a `docs/dossier_g0.md:56` | Dos defectos distintos llevan el número 8, y queda un párrafo previo a I3.2 | Renumerar o nombrar el defecto de D2 sin ordinal; tiempo pasado | C4 | abierto |
| INV-066 | docs-normativos-21 | docs | Coherencia documental | menor | `PLAN_ASISTENTE.md:1-20` frente a la spec de cierre `:60` | PLAN_ASISTENTE no dice que quedó fuera del límite (trabajo futuro) | Nota de vigencia que enlace la spec §2 | C4 | abierto |
| INV-067 | docs-normativos-22 | docs | Coherencia documental | menor | `docs/calidad_iso25010.md:25-29,43` | El veredicto cita «tres RF no esenciales declarados arriba»; solo se declara RF‑16, que es esencial | Corregir la frase al actualizar las cifras (INV‑031) | C4 | abierto |
| INV-068 | docs-tesis-05 | docs | DRY / citación T8 | menor | `docs/tesis/referencias.md:521,534` | La nota de la entrada AACE 2020 aún justifica el sufijo «b», que dejó de hacer falta al corregir el año de la 56R‑08; no llega al texto de la tesis | Corregir la nota interna | Red | abierto |

## 4. Propuesta de triage para GC0

Propuesta del consolidador para que Eugenio la apruebe o la modifique en GC0 (spec §4, «Triage»).
Ninguna severidad se cambia aquí; los conteos ya reflejan la verificación de la Tarea 5 (§5).

### (a) Bloqueantes e importantes: entran

Un bloqueante: **INV‑065** (C4; se cierra antes de ejecutar CP‑07 en Med). Los 36 importantes entran,
por fase:

- **C1 (15):** INV‑001, INV‑002 (cambian contratos: expediente y aval), INV‑003, INV‑004, INV‑005,
  INV‑006 (contrato en C1; subtarea de migración en C2), INV‑007, INV‑008, INV‑009, INV‑010, INV‑011
  (subtarea documental en C4), INV‑012, INV‑013, INV‑014, INV‑015.
- **C2 (3):** INV‑016, INV‑017, INV‑018.
- **C3 (7):** INV‑019, INV‑020, INV‑021, INV‑022, INV‑023, INV‑024, INV‑025.
- **C4 (8):** INV‑026, INV‑027, INV‑028, INV‑029, INV‑030, INV‑031 (subtarea en Red), INV‑032, INV‑033.
- **Red (3):** INV‑034, INV‑035, INV‑036.

### (b) Menores que se propone promover (20)

| ID | Fase | Por qué |
|---|---|---|
| INV‑050 | C3 | Riesgo de pérdida de datos: `--reiniciar` borra sin confirmar la base de trabajo por defecto; su cara documental, INV‑065, ya es bloqueante |
| INV‑044 | C3 | La parte de `ui/` ya está en U1; la de `scripts/` es una línea en `seed_demo.py`, que INV‑050 ya toca |
| INV‑049 | C3 | Barato; mismos cuatro sembradores que INV‑050 |
| INV‑045 | C3 | Barato; `componer.py` lo reescribe la Tarea 11 de U1 |
| INV‑046 | C3 | Barato; mismo archivo que INV‑045 |
| INV‑052 | C3 | Barato; `test_ui_componer.py` lo modifica la Tarea 11 de U1 |
| INV‑051 | C3 | Barato; es el mismo inventario de scripts que se escribe para INV‑055 e INV‑056 |
| INV‑041 | C2 | Barato; la migración de INV‑006 abre los cuatro adaptadores |
| INV‑042 | C2 | Barato; los archivos de la API ya se tocan en INV‑008 |
| INV‑053 | C4 | Barato; esos archivos se tocan en INV‑009, INV‑012 e INV‑020 |
| INV‑054 | C4 | Barato; `plan_pruebas.md` y `manual_tecnico.md` se tocan en INV‑027 e INV‑031; hermano de INV‑036 |
| INV‑055 | C4 | Barato; INV‑007 ya edita `CLAUDE.md` §9 |
| INV‑056 | C4 | Barato; INV‑032 ya edita `README.md` |
| INV‑057 | C4 | Barato; INV‑028 ya edita arquitectura §2.3 |
| INV‑058 | C4 | Barato; su contenido lo fija INV‑006 y arquitectura ya se regenera en INV‑029 |
| INV‑059 | C4 | Barato; arquitectura §4 se regenera en INV‑029 |
| INV‑060 | C4 | Barato; la ERS se edita en varias correcciones de C4, y el principio de datos ficticios tiene guardia en la CI (`meta_datos.py`) |
| INV‑062 | C4 | Barato; `calidad_iso25010.md` y `plan_pruebas.md` se tocan en INV‑031 |
| INV‑063 | C4 | Barato; ERS y dossier se tocan en INV‑031 e INV‑028 |
| INV‑067 | C4 | Barato; la propia corrección lo ata a la actualización de cifras de INV‑031 |

### (c) El resto: a limitaciones (11)

INV‑037 (C1; el cambio de `elaborar` cruza tres capas, aunque INV‑013 toca la misma función),
INV‑038 (C1+C2; exige un cambio de contrato para cubrir `ml/`), INV‑039, INV‑040, INV‑043 (si Eugenio
lo promueve, la hace la Tarea 11 de U1, spec §5), INV‑047, INV‑048 (latente; ya declarado trabajo
futuro en la spec de UI §9), INV‑061, INV‑064, INV‑066, INV‑068.

### (d) Conteo por fase y severidad

Cada hallazgo se cuenta en su fase principal (la primera de la columna «Fase destino»); las subtareas
en otra fase se anotan en (a).

| Fase | Bloqueante | Importante | Menor | Total | Menores promovidos | Menores a limitaciones |
|---|---|---|---|---|---|---|
| C1 | 0 | 15 | 4 | 19 | 0 | 4 |
| C2 | 0 | 3 | 2 | 5 | 2 | 0 |
| C3 | 0 | 7 | 10 | 17 | 7 | 3 |
| C4 | 1 | 8 | 14 | 23 | 11 | 3 |
| Red | 0 | 3 | 1 | 4 | 0 | 1 |
| **Total** | **1** | **36** | **31** | **68** | **20** | **11** |

Si se aprueba la propuesta, entran 57 hallazgos (1 bloqueante, 36 importantes y 20 menores
promovidos) y 11 van al capítulo de limitaciones.

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
  mismo caso como hallazgo.
- INV‑022 (importante): hoy la prueba no escribe en `data/apu.db`: el defecto es que falta la
  afirmación que lo garantiza. Por eso no es bloqueante; queda en el valor por defecto de pruebas.
- INV‑032 (importante): la tabla de `README.md:44-59` enumera archivo → qué comprueba, sin RF ni
  estado. El hallazgo se sostiene con las dos copias de la ERS (`:447-488`, `:543-556`) y
  `plan_pruebas.md` §8, que ya divergen (INV‑027).
- INV‑027, INV‑028, INV‑036 e INV‑054 (este último fuera de la muestra) tocan D5, la salvedad G1 y la
  salvedad RNF‑07 del dossier. No las duplican: registran contradicciones entre documentos que el
  dossier no capturó (spec §4).
