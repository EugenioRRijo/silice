# Auditoría parcial — capa `tests`

Commit auditado: `cc2243cd5a7efd3b20dc82fe586484a6ef01fea8`. `git diff --stat cc2243cd HEAD -- tests/`
está vacío, así que los números de línea valen igual sobre el HEAD del worktree. Criterios: spec
`docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md` §4 (principios, severidades, regla por
defecto: todo hallazgo de trazabilidad o de pruebas es importante; una prueba que escribe en
`data/apu.db` es bloqueante). Las decisiones D1–D9 de `docs/dossier_g0.md` se toman como riesgo ya
rastreado y no se reportan.

Evidencia de ejecución (todas las bases fuera de `data/`):

- Suite completa desde la raíz del worktree, `-W error`: verde, sin omitidas; `data/apu.db` no existe
  antes ni después.
- Suite completa lanzada con el directorio de trabajo en un temporal (`APU_BASE` apuntando al
  temporal): **7 fallos** (`test_referencia_maprex.py` ×5, `test_fuentes_arenaza.py` ×2) por rutas
  relativas al cwd (tests-01); ningún `.db` creado en el temporal, así que ninguna prueba abre la ruta
  relativa `data/apu.db`.
- Cada uno de los archivos de prueba ejecutado de forma aislada (`pytest <archivo>`): verde. No hay
  dependencia del orden detectable entre archivos.

## 1. Archivos revisados (70 de 70 de `git ls-files tests/`)

```
tests/__init__.py
tests/conftest.py
tests/fixtures/__init__.py
tests/fixtures/apu_linea_base.py
tests/fixtures/computo_auditado.py
tests/fixtures/mantenimiento_industrial.py
tests/fixtures/presupuesto_auditado.py
tests/fixtures/presupuestos_arenaza.py
tests/fixtures/tarifas_sistemas.py
tests/integration/__init__.py
tests/integration/conftest.py
tests/integration/test_actualizacion_precios.py
tests/integration/test_api.py
tests/integration/test_api_escenarios.py
tests/integration/test_api_rendimientos.py
tests/integration/test_auditoria_7_de_7.py
tests/integration/test_auditoria_arenaza.py
tests/integration/test_civil_verificacion.py
tests/integration/test_composicion_extremo_a_extremo.py
tests/integration/test_composicion_r6.py
tests/integration/test_persistencia.py
tests/integration/test_presupuesto_arenaza.py
tests/integration/test_presupuesto_industrial.py
tests/integration/test_presupuesto_linea_base.py
tests/integration/test_presupuesto_sistemas.py
tests/integration/test_rendimientos.py
tests/integration/test_seed_demo.py
tests/unit/__init__.py
tests/unit/test_adapter_civil_ifc.py
tests/unit/test_adapter_industrial.py
tests/unit/test_adapter_sistemas.py
tests/unit/test_adapter_telecom.py
tests/unit/test_anomalias.py
tests/unit/test_arquitectura.py
tests/unit/test_budget.py
tests/unit/test_composicion.py
tests/unit/test_composicion_ia.py
tests/unit/test_contracts.py
tests/unit/test_costing.py
tests/unit/test_costing_destajo.py
tests/unit/test_escenarios.py
tests/unit/test_fuentes_arenaza.py
tests/unit/test_generador_ifc.py
tests/unit/test_guardia_nucleo.py
tests/unit/test_linea_base.py
tests/unit/test_lista_maprex_usd.py
tests/unit/test_listas_telecom.py
tests/unit/test_mantenimiento_industrial.py
tests/unit/test_meta_alpha.py
tests/unit/test_meta_asistente.py
tests/unit/test_meta_datos.py
tests/unit/test_meta_multidominio.py
tests/unit/test_meta_prototipo.py
tests/unit/test_meta_redaccion.py
tests/unit/test_normalizacion.py
tests/unit/test_openapi.py
tests/unit/test_prediccion.py
tests/unit/test_referencia_maprex.py
tests/unit/test_reglas_civil.py
tests/unit/test_resultados_ml.py
tests/unit/test_resultados_ml_multidominio.py
tests/unit/test_simulador.py
tests/unit/test_simular_corpus.py
tests/unit/test_tarifas_sistemas.py
tests/unit/test_ui_app.py
tests/unit/test_ui_componer.py
tests/unit/test_ui_importable.py
tests/unit/test_verificar_omitidas.py
tests/unit/test_verification.py
tests/unit/test_visor3d.py
```

## 2. Hallazgos

| ID | Capa | Principio | Severidad | Evidencia (archivo:línea) | Hallazgo | Corrección propuesta | Fase |
|---|---|---|---|---|---|---|---|
| tests-01 | tests | pruebas (aislamiento: directorio de trabajo) | importante | `tests/unit/test_referencia_maprex.py:6`; `tests/unit/test_fuentes_arenaza.py:14` | Las dos pruebas abren los CSV con rutas relativas al cwd (`Path("data/...")`), y 7 casos fallan si pytest se lanza fuera de la raíz (reproducido); el resto de la suite ancla en `Path(__file__).resolve().parents[2]`. | Anclar `CARPETA` en `Path(__file__).resolve().parents[2]`, como `test_adapter_telecom.py:23`. | C3 |
| tests-02 | tests | pruebas (aislamiento: reloj) | importante | `tests/integration/test_seed_demo.py:91`, `:109` | La valoración se comprueba en `date.today()`: el resultado depende del reloj de la máquina (antes del 2026‑04‑28 no hay lista vigente y la prueba falla; entre esa fecha y `FECHA_DEMO` no ejercita la lista de la demostración). | Fijar la fecha: `seed_demo.FECHA_DEMO` (y, si se quiere el «hoy», una fecha fija posterior declarada en la prueba). | C3 |
| tests-03 | tests | pruebas (estado compartido entre pruebas) | importante | `tests/unit/test_visor3d.py:65-68` frente a `tests/unit/test_composicion_ia.py:397-417`; síntoma descrito en `tests/unit/test_ui_componer.py:21-30` | `_SinIfcopenshell` restaura `sys.modules` pero no los atributos del paquete padre (`ui.paginas.visor`, `ui.visor3d`, `adapters.civil.ifc`, `ifcopenshell.util`…); el arreglo que resincroniza esos atributos se aplicó solo a la copia de `test_composicion_ia.py`. Deja el mismo agujero que obligó a `test_ui_componer.py` a parchar por objeto y no por ruta. | Un solo gestor de contexto «sin extra» en `tests/fixtures/` (o `conftest.py`), con la resincronización, usado por los dos archivos. | C3 |
| tests-04 | tests | pruebas (aislamiento: `data/apu.db`) | importante | `tests/unit/test_ui_app.py:80-85` | El arranque real de la app (`AppTest.from_file`) solo desvía `RUTA_BASE_POR_DEFECTO` de `ui.paginas.actualizacion`, porque hoy es la página por defecto; nada lo afirma. Cuando cambie la página por defecto (RF‑36 hace del Inicio la página por defecto en U1) la prueba abrirá `data/apu.db` relativa al cwd sin fallar. `test_ui_componer.py:107-111` sí tiene la guarda. | Desviar la ruta de todas las páginas (o la fuente única que exige RF‑38) y afirmar tras `at.run()` que el temporal existe y `data/apu.db` no se creó. | C3 |
| tests-05 | tests | pruebas (aserción vacía) | importante | `tests/unit/test_ui_importable.py:4-17`; citado como evidencia en `docs/plan_pruebas.md` §8 (RF‑16, RF‑31) | La prueba no tiene ninguna aserción: su nombre promete «sin efectos» y no comprueba ninguno (ni que no se cree una base, ni que no se llame a Streamlit). | Afirmar la ausencia de efectos (p. ej. cwd temporal y ningún archivo creado) o renombrarla como humo de importación y dejar de citarla como evidencia de RF. | C3 (cruza: docs) |
| tests-06 | tests | pruebas (aserciones triviales) | importante | `tests/unit/test_visor3d.py:83-85`; `tests/unit/test_composicion_ia.py:430-431` | `importlib.import_module(...) is not None` no puede fallar; lo que se verifica de verdad (que no se lance `ImportError`) queda implícito. | Sustituir por una comprobación con fase roja (p. ej. que el módulo expone `render` y que `ifcopenshell`/`ml` no quedó en `sys.modules`). | C3 |
| tests-07 | tests | pruebas (aserciones triviales) | importante | `tests/integration/test_auditoria_arenaza.py:86`, `:142` | La línea 86 compara el total de dos presupuestos reconstruidos por separado, así que no puede detectar que `auditar` mute el presupuesto (RF‑23); la 142 es un `all(...)` sobre una lista que la línea 141 ya afirmó vacía. | Comparar el mismo objeto antes y después de `auditar` (copia previa por igualdad de dataclass) y borrar la 142. | C2 |
| tests-08 | tests | pruebas (aserción débil) | importante | `tests/unit/test_simulador.py:19` | `... in (["Cemento Portland"], [])` acepta la lista vacía: la prueba pasa aunque el filtro `solo` no produzca ninguna variación. | Con semilla fija, afirmar exactamente `["Cemento Portland"]` (y que Arena queda en su precio). | C3 |
| tests-09 | tests | pruebas (aserción trivial) | importante | `tests/unit/test_resultados_ml.py:54-55`, `:62` | `"5" in informe and "50" in informe` y `"reglas" in informe.lower()` se cumplen con cualquier fecha o importe: no verifican ni el conteo G2 ni la técnica (RF‑28). La prueba hermana sí fija la fila (`test_resultados_ml_multidominio.py:76`). | Afirmar la fila exacta `"| civil | 5 | reglas |"` y la sección de limitación. | C2 (cruza: scripts) |
| tests-10 | tests | pruebas (marcadores) | importante | `tests/unit/test_costing.py:1-10`, `:20`; `pyproject.toml:50-52` | El marcador `rojo_esperado` («pruebas que deben fallar hasta que exista la implementación») y el docstring («fallan con ImportError») siguen aplicados a siete pruebas que pasan desde I0.3; es el único uso del marcador. | Retirar `pytestmark` y actualizar el docstring (no cambia ninguna aserción, así que respeta CLAUDE.md §9); retirar el marcador de `pyproject.toml` y el «estado esperado» de CLAUDE.md §9. | C1 (cruza: docs) |
| tests-11 | tests | DRY (línea base copiada) | importante | `tests/unit/test_costing_destajo.py:28-34`; `tests/integration/test_api.py:34`, `:78-82`, `:108`, `:111`, `:138`, `:256`, `:338-339`; `tests/unit/test_adapter_civil_ifc.py:18-19`; `tests/unit/test_generador_ifc.py:21-23`; `tests/integration/test_actualizacion_precios.py:207-208`, `:308-309`; `tests/integration/test_persistencia.py:94`; `tests/integration/test_rendimientos.py:35`, `:146`, `:193`; `tests/integration/test_api_rendimientos.py:17`, `:122` | Cifras y códigos de la línea base escritos como literales fuera de `tests/fixtures/apu_linea_base.py` (metodología §5.1): los cinco PU exactos, `"1586.61"`, `"0.224"`, `"LB-0x-…"`, precios 15/30/35/200 y el rendimiento 80. Corregir un dato del fixture obliga a editar hasta ocho archivos más. | Importar de `apu_linea_base` (`TOTAL_PRESUPUESTO_AUDITADO`, `APU_*.codigo_partida`, `CANTIDAD_POR_TANQUILLA_MEMORIA`, precios de `APU_CONCRETO`, `APU_EXCAVACION.rendimiento`); mover los PU exactos al fixture. | C1 (cruza: api, adapters) |
| tests-12 | tests | DRY (duplicación entre archivos de prueba) | importante | `tests/unit/test_escenarios.py:39-40` y `tests/integration/test_actualizacion_precios.py:52`, `:57` (y sus derivados `test_api_escenarios.py:95`, `test_api.py:138`); `tests/unit/test_tarifas_sistemas.py:31` y `tests/integration/test_presupuesto_sistemas.py:44`; `tests/fixtures/presupuesto_auditado.py:47` (`"0.0081"`) frente a `tests/unit/test_reglas_civil.py:31`, `:112` (`0.1016`, `0.008107338624`) | El mismo valor esperado se declara en dos o tres archivos: el incremento UC‑02 de 30,17025 y sus precios, el PU de sistemas de 110,992365 y el factor de sección de la tubería de 4" (este último con dos precisiones distintas). | Un solo lugar por valor en `tests/fixtures/` (el factor de tubería, derivado de `adapters.civil.reglas`), importado por las pruebas. | C1 (cruza: adapters) |
| tests-13 | tests | DRY (duplicación entre archivos de prueba) | menor | `tests/integration/test_api.py:14-22`, `tests/integration/test_api_escenarios.py:29-37`, `tests/integration/test_api_rendimientos.py:21-29` (fixture `cliente`); `tests/integration/test_api.py:55-72` y `tests/integration/test_api_escenarios.py:43-57` (carga útil de ítems) | La fixture `cliente` está copiada tres veces y el armado de la carga útil de ítems dos. | Moverlos a `tests/integration/conftest.py`. | C2 |
| tests-14 | tests | DRY / pruebas (una regla, cinco implementaciones) | importante | `tests/unit/test_arquitectura.py:43-52`; `tests/unit/test_adapter_civil_ifc.py:61-73`; `tests/unit/test_adapter_telecom.py:145-179`; `tests/unit/test_adapter_industrial.py:68-81`; `tests/unit/test_adapter_sistemas.py:91-109` | La guarda «un adaptador solo importa `core.contracts`» se reimplementa en cinco archivos con criterios distintos: solo telecom rechaza importar otro adaptador (`adapters.civil…`), industrial usa `glob` no recursivo, sistemas una lista fija de tres archivos y civil solo mira `ifc.py`. La regla completa no rige para civil, industrial ni sistemas. | Una sola prueba parametrizada por paquete en `test_arquitectura.py`, con la regla de telecom (stdlib + `core.contracts` + el propio paquete), y borrar las copias. | C2 |
| tests-15 | tests | D (regla de dependencia) / trazabilidad | importante | `tests/unit/test_arquitectura.py:17`, `:55-58` | `PAQUETES_FUERA_DEL_NUCLEO` omite `scripts` (y `tests`): la regla de la spec §4‑D «`core/` no importa de … `scripts/`» no tiene prueba. Hoy se cumple (`grep` sobre `core/`), pero nada lo vigila. | Añadir `"scripts"` y `"tests"` a la tupla. | C1 |
| tests-16 | tests | DRY (ubicación de ayudas compartidas) | menor | `tests/unit/test_ui_componer.py:64-69`; `tests/integration/test_composicion_extremo_a_extremo.py:54` | Dos módulos de prueba importan funciones privadas (`_filas_*`, `_texto`, `_detectadas`) de otros módulos de prueba; un cambio en uno rompe al otro y acopla `unit/` a `integration/`. | Mover esas ayudas a `tests/fixtures/`. | C3 |
| tests-17 | tests | trazabilidad (RF y pasos de UC sin prueba) | importante | `docs/ERS.md:465-466` (RF‑19, RF‑20), `docs/ERS.md:203-208` (UC‑04 pasos 1‑5), `docs/plan_pruebas.md:146-147`; ausencia en `tests/unit/test_reglas_civil.py` y `tests/unit/test_budget.py` | RF‑19 («cambiar el ancho altera solo lo derivado de esa dimensión») y RF‑20 («la suma de los diferenciales por partida iguala la diferencia de totales») citan pruebas que no existen; `plan_pruebas.md` los da en verde. UC‑04 (pasos 1‑5 y flujos 1a, 2a, 2b) no tiene ninguna prueba. | Escribir las dos pruebas (o bajar RF‑19/RF‑20 a pendiente en ERS y plan de pruebas) y trazar cada paso de UC‑04. | C1 (cruza: adapters, docs) |
| tests-18 | tests | trazabilidad (prueba que afirma lo contrario del RF) | importante | `docs/ERS.md:469` (RF‑23), `:234` (UC‑05 2a), `:238` (UC‑05 3a) frente a `tests/unit/test_verification.py:391-398`, `:446-456`, `:515-540` y `:371-372` | RF‑23 y UC‑05 3a exigen que una regla no evaluable se reporte como INFO «regla no evaluable»; las pruebas fijan ERROR «no se puede evaluar». UC‑05 2a exige que R7 se declare no aplicable sin plan; la prueba fija que R7 calla (`[]`). | Decidir cuál manda y alinear RF, regla y prueba en el mismo cambio. | C1 (cruza: core, docs) |
| tests-19 | tests | trazabilidad (paso de UC contradicho por la prueba) | importante | `docs/ERS.md:139` (UC‑01 3a) frente a `tests/unit/test_budget.py:95-107` | UC‑01 3a: un ítem sin partida queda pendiente, no suma al total y el informe lo declara; la prueba fija que `generar_presupuesto` lanza `ValueError` y no emite presupuesto ni informe. | Alinear el UC o la implementación, y la prueba con el que quede. | C1 (cruza: core, docs) |
| tests-20 | tests | trazabilidad (criterio de aceptación no verificado) | importante | `docs/ERS.md:457-458` (RF‑11, RF‑12) frente a `tests/integration/test_actualizacion_precios.py:279-309` y `tests/integration/conftest.py:40-45` | RF‑11 exige «las composiciones quedan idénticas» y RF‑12 «recuperable tras cerrar la sesión»; ninguna prueba compara las composiciones del catálogo antes y después de UC‑02, y todas consultan los cambios en la misma sesión abierta, sin cerrarla ni reabrirla. | Comparar `Catalogo.composicion` de las cinco partidas antes y después de `actualizar_precios`; añadir una prueba con base en `tmp_path` que confirme, cierre el motor y relea los `CambioPrecio`. | C1 |
| tests-21 | tests | trazabilidad (pasos de UC sin prueba) | importante | `docs/ERS.md:167` (UC‑02 2b), `:170` (UC‑02 7a); ausencia en `tests/` | Ninguna prueba ejercita el rechazo de una fila con unidad no equivalente a la del catálogo, ni que al descartar la versión nueva se conserve el registro de cambios. | Una prueba por flujo alternativo en `test_actualizacion_precios.py`. | C1 |
| tests-22 | tests | trazabilidad (la matriz cita pruebas que no verifican lo afirmado) | importante | `docs/ERS.md:449-450` (RF‑03, RF‑04 citan `test_linea_base.py`), `:470` (RF‑24 cita `test_auditoria_7_de_7.py`); `docs/plan_pruebas.md:150` | `tests/unit/test_linea_base.py` no construye ningún `ItemComputo`; la unidad «mts» que llega intacta a R3 se afirma en `tests/unit/test_verification.py:263-270`, no en `test_auditoria_7_de_7.py`; RF‑04 da la extracción IFC por «pendiente» y `tests/unit/test_adapter_civil_ifc.py:12-20` la cubre. | Corregir la columna de criterio de aceptación en ERS §3.2 y la fila de `plan_pruebas.md` §8. | C4 (cruza: docs) |
| tests-23 | tests | coherencia documental (docstrings obsoletos) | menor | `tests/integration/test_seed_demo.py:82`, `:99`, `:117`, `:141`; `tests/fixtures/presupuesto_auditado.py:211-213`; `tests/fixtures/presupuestos_arenaza.py:13-16`; `tests/unit/test_verification.py:460-461` | Los docstrings dicen «Hoy falla», «se saltan mientras…», «comparando la suma de `total`, no cada campo» y «como el que hoy escribe `adapters/civil/tabular.py`», y las cuatro cosas dejaron de ser ciertas (la suite pasa, no hay `skip`, `test_fuentes_arenaza.py:63-70` compara campo a campo, y `test_civil_verificacion.py` documenta el arreglo del adaptador). | Actualizar los docstrings al comportamiento vigente. | C4 |

Excluido por diseño declarado: la dependencia de `tests/unit/test_normalizacion.py:46-53` de la descarga
inicial del modelo de similitud es la excepción declarada de RNF‑08 (`docs/plan_pruebas.md` §9), así que
no se reporta.

## 3. Principios sin hallazgos

- **Principio 3 (`Decimal`, nunca `float`)**: sin hallazgos. Los `float` que aparecen en las pruebas
  son entradas deliberadas para comprobar que la frontera los rechaza o los convierte a `Decimal`
  (`test_contracts.py:84-86`, `test_actualizacion_precios.py:150-171`).
- **Principio 4 (motor de costos puro)**: sin hallazgos.
- **Principio 7 (el informe de auditoría se genera siempre)**: sin hallazgos. Lo vigilan
  `test_budget.py:174-195` y `test_api.py:96-113`.
- **Contratos de `CLAUDE.md` §5 (inmutables, invariantes en `__post_init__`)**: sin hallazgos.
  Ninguna prueba muta un contrato, y `test_contracts.py` cubre las invariantes.
- **S, O, L, I**: sin hallazgos (no aplican a la capa de pruebas más allá de lo reportado como DRY).
- **Pruebas que escriben en `data/apu.db` (bloqueante)**: sin hallazgos. Todas las bases van a memoria
  (`tests/integration/conftest.py:18-37`) o a `tmp_path`, y ninguna corrida creó `data/apu.db`, ni
  lanzada desde la raíz ni desde un cwd temporal. El riesgo latente queda como tests-04.
- **Dependencia del orden de ejecución**: sin hallazgos. Cada archivo pasa aislado y la suite pasa
  completa. El estado compartido en `sys.modules` queda como tests-03.
- **Dependencia de la red**: sin hallazgos aparte de la excepción declarada de RNF‑08.
- **`filterwarnings`**: sin hallazgos. Ninguna prueba silencia advertencias; la CI corre con
  `-W error`, y el único ajuste (`HF_HUB_DISABLE_SYMLINKS_WARNING`, `test_normalizacion.py:22-26`)
  está justificado en el propio archivo.
