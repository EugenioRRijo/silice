# Plan de pruebas y registro de ejecución (IEEE 829) — Sesión F.2

Plan de pruebas del sistema de generación y auditoría de APU multidominio, según la estructura de
IEEE 829 y con la trazabilidad que exige [metodologia.md §7](metodologia.md#7-trazabilidad): cada
caso de prueba cita su RF; los enunciados de los RF viven **una sola vez** en
[ERS.md §3.2](ERS.md#32-requisitos-funcionales) y aquí no se repiten (CLAUDE.md §2, DRY).

## 1. Identificador y alcance

- **Identificador:** PP‑APU‑001, versión de la Sesión F.2 (2026‑08‑31).
- **Alcance:** todo el software del repositorio (`core/`, `adapters/`, `ml/`, `api/`, `ui/`,
  `scripts/`) contra los RF‑01…RF‑43 (RF‑32 vacante) y RNF‑01…RNF‑10 de la ERS.
- **Referencias:** [CLAUDE.md](../CLAUDE.md) (constitución), [ERS.md](ERS.md) (IEEE 830),
  [metodologia.md](metodologia.md) (indicadores y trazabilidad),
  [linea_base.md](linea_base.md) (caso auditado), bitácoras en [bitacora/](bitacora/).

## 2. Elementos de prueba

Versión probada: rama `main` en el commit `02f961a` (cierre del sprint I6) más el cierre de
UC‑08 (`inc/UC08-escenarios`, 2026‑08‑31), que motivó la segunda corrida registrada en §10.
Elementos:

| Paquete | Contenido | Nivel de prueba |
|---|---|---|
| `core/contracts` | contratos estables (§5 de CLAUDE.md) | unitario (invariantes) |
| `core/costing` | motor de costos (función pura) | unitario contra la línea base |
| `core/models`, `core/catalog` | persistencia SQLite y catálogo | unitario + integración |
| `core/budget` | presupuesto, curva, exportación, UC‑02 | unitario + integración |
| `core/verification` | reglas R1–R7 e informe | unitario + integración (7 de 7) |
| `adapters/{civil,telecom,industrial,sistemas}` | extracción de cantidades | unitario + arquitectura |
| `ml/{normalization,anomaly,prediction}` | RF‑15/17, RF‑27/29, RF‑28 | unitario |
| `api/` | 13 endpoints FastAPI + OpenAPI | integración (TestClient) |
| `ui/` | Streamlit multipágina y visor 3D | humo (importación y generación) |
| `scripts/` | seed, simulador, generadores, metas | unitario + ejecución directa |

## 3. Características a probar y a no probar

**A probar:** los 42 RF de la ERS (matriz de la sección 8) y los RNF verificables por software o
por medición (RNF‑01, 02, 03, 05, 06, 08; sección 9).

**A no probar en esta sesión, con causa:**

- **RNF‑04 (usabilidad del informe):** requiere juicio de expertos con escala Likert; el
  instrumento se aplica con el tutor (Fase 6). No es automatizable.
- **RNF‑10 (capacidad de aprendizaje de la interfaz):** no es automatizable; se mide con el caso con
  persona CP‑07 de [guion_prueba_arenia.md](guion_prueba_arenia.md) en la compuerta GU1b (fase Med)
  de [PLAN_UI.md](../PLAN_UI.md). Sus requisitos funcionales RF‑36 a RF‑43 **sí** tienen prueba
  automatizada, en verde (sección 8, U1).
- **RNF‑07 en Linux:** la instalación con `uv sync` está verificada solo en Windows 11; la
  corrida en Linux queda declarada como pendiente.
- **RNF‑09 (IFC de ≥ 2 modeladores):** la compuerta G1 se cruzó con salvedad — el adaptador civil
  reproduce exacto el cálculo manual, pero contra `data/samples/tanquilla.ifc` generado
  programáticamente, no contra un export BIM real (bitácora
  [2026‑08‑31‑F1](bitacora/2026-08-31-F1-api-3d.md)).
(RF‑30 y RF‑31 figuraban aquí en la primera versión de este plan: UC‑08 había quedado fuera del
alcance de F.1. La brecha se cerró el mismo día — `core/budget/escenarios.py` con
`tests/unit/test_escenarios.py`, TDD con RED observado — y sus filas están ahora en §8.)

## 4. Enfoque

1. **Pruebas antes que implementación en el núcleo** (CLAUDE.md §2.5): la línea base verificada
   (`tests/fixtures/apu_linea_base.py`, única copia) existe desde antes que el motor;
   `test_costing.py` no se modificó para ponerse en verde.
2. **Dos niveles.** `tests/unit/` prueba cada pieza aislada (contratos, motor, reglas,
   adaptadores, ml); `tests/integration/` prueba flujos completos sobre SQLite real (sembrar →
   elaborar → auditar → actualizar precios → reconstruir a fecha).
3. **Exactitud decimal.** Los importes se comparan como `Decimal` exactos; la única tolerancia
   admitida es ± 0,01 sobre el precio unitario de los cinco APU de la línea base (CLAUDE.md §4).
4. **Arquitectura como prueba.** `test_arquitectura.py` (65 casos, uno más por cada módulo que
   nace: el cierre de UC‑08 añadió el suyo solo) falla si un adaptador importa
   de `core` algo distinto de `core.contracts`: la hipótesis central se vigila en cada corrida.
5. **Advertencias como errores.** La suite corre con `-W error`: cualquier advertencia de
   dependencia o de código propio rompe la corrida.
6. **Determinismo.** Todo lo estocástico fija semilla (Isolation Forest y simulador con
   semilla 42); las pruebas de caracterización añadidas en F1‑fixes se verificaron por mutación
   (se comprobó que fallan ante el defecto que documentan).
7. **Metas de sprint automatizadas.** `scripts/meta_alpha.py` y `scripts/meta_i6.py` evalúan las
   metas de cierre (12/12 en el sprint I6) leyendo la corrida de pytest, la cobertura y el estado
   del repositorio; ellos mismos tienen pruebas (`test_meta_alpha.py`, 26 casos).

## 5. Criterios de aprobación y de fallo

- La suite completa en verde con `-W error`; ninguna prueba omitida.
- Los cinco precios unitarios de la línea base dentro de ± 0,01 (RF‑01).
- El presupuesto de prueba con las siete inconsistencias produce **7 de 7** hallazgos, uno por
  regla (RF‑22, indicador 1 de la tesis).
- `total_curva == total` sin tolerancia (RF‑07).
- Cobertura de `core/` ≥ 80 % (RNF‑06).
- `uv run ruff check .` sin observaciones.

## 6. Criterios de suspensión y reanudación

Si una prueba del núcleo se pone en rojo, la regla de CLAUDE.md §9 aplica: no se parchea la
prueba; se corrige la implementación o, si el contrato resulta insuficiente, se documenta el
hallazgo en `docs/bitacora/` y se detiene la sesión. Estado esperado histórico: hasta I0.3 la
suite estuvo deliberadamente roja en `test_costing.py` (marcador `rojo_esperado`).

## 7. Entregables y entorno

**Entregables:** este plan, [calidad_iso25010.md](calidad_iso25010.md), la bitácora de la sesión,
el reporte de cobertura (sección 10) y `scripts/medir_rnf03.py` (evidencia reproducible del
RNF‑03). Desde la Sesión P4.2, además, el [guion de prueba manual de AREN.IA](guion_prueba_arenia.md)
(casos CP‑01 a CP‑06 de la pantalla de componer, para quien pruebe sin programar).

**Entorno de la ejecución registrada:** equipo de desarrollo con Windows 11 Home (10.0.26200),
Python 3.13.2, `uv` con extras `ui`, `api`, `civil` y `ml`, SQLite local, modelo de
`sentence-transformers` en caché local (sin red durante la corrida). Comandos:

```
uv sync --extra ui --extra api --extra civil --extra ml
uv run pytest -W error --cov=core --cov=adapters --cov=ml --cov=api
uv run ruff check .
uv run python scripts/medir_rnf03.py
```

**Integración continua** (desde 2026‑09‑15, `.github/workflows/ci.yml`): cada PR y cada push a
`main` ejecutan en runners de GitHub el job `calidad` (ruff y `scripts/guardia_nucleo.py`, que
aplica la regla de la hipótesis central al rango del cambio) y el job `pruebas` en Linux y
Windows (todos los extras, `pytest -W error` y `scripts/verificar_omitidas.py`, que exige 0
omitidas). En Linux, además, se exige la cobertura de `core/` ≥ 80 % y que `docs/api.json` y
`docs/resultados_ml.md` se regeneren sin diferencias. Cada paso tiene su comando local
equivalente en [manual_tecnico.md](manual_tecnico.md) §2.

## 8. Especificación de casos: trazabilidad RF → prueba

Una fila por RF; el enunciado y el criterio de aceptación están en la fila homónima de
[ERS.md §3.2](ERS.md#32-requisitos-funcionales). «Casos» cuenta las funciones de prueba del
archivo en la corrida registrada (total de la suite: 392).

| RF | Prueba(s) que lo demuestran | Casos | Resultado |
|---|---|---|---|
| RF‑01 | `tests/unit/test_costing.py` (5 APU ± 0,01, errores vigilados: materiales sin dividir por rendimiento, cascada admin→utilidad) | 7 | verde |
| RF‑02 | `tests/integration/test_auditoria_7_de_7.py`; `elaborar` audita siempre (`tests/integration/test_presupuesto_linea_base.py`) | 4 + 9 | verde |
| RF‑03 | `tests/unit/test_contracts.py` (`TestItemComputo`: sin `origen_id` se rechaza; REGLA sin expresión se rechaza); `tests/unit/test_linea_base.py` | 8 + 14 | verde |
| RF‑04 | `tests/unit/test_arquitectura.py`; `tests/unit/test_adapter_civil_ifc.py` (`origen_id` = GlobalId) | 65 + 3 | verde, con la salvedad G1 (§3) |
| RF‑05 | `tests/integration/test_persistencia.py` (los 5 APU recuperados dan los mismos PU que el fixture) | 14 | verde |
| RF‑06 | `tests/unit/test_budget.py`; `tests/integration/test_presupuesto_linea_base.py` | 12 + 9 | verde |
| RF‑07 | ídem RF‑06: `total_curva == total` exacto | — | verde |
| RF‑08 | `tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas` | 1 | verde |
| RF‑09 | `test_arquitectura.py` + `test_adapter_telecom.py`, `test_adapter_industrial.py`, `test_adapter_sistemas.py` + `git diff --stat core/` vacío tras I5 | 65 + 7 + 4 + 4 | verde (indicador 4) |
| RF‑10 – RF‑13 | `tests/integration/test_actualizacion_precios.py` (lista de muestra: cambios exactos, composiciones intactas, un registro por insumo, variaciones que cuadran) | 20 | verde |
| RF‑14 | `tests/integration/test_persistencia.py::test_precios_se_reconstruyen_a_fecha` + `test_actualizacion_precios.py` | — | verde |
| RF‑15 | `tests/unit/test_normalizacion.py::test_propuestas_ordenadas_por_puntaje_y_sobre_el_umbral` | 6 | verde |
| RF‑16 | precarga cubierta en `ui/paginas/similares.py` (humo: `test_ui_importable.py`); **persistencia pendiente** del flujo de creación de partidas (hallazgo I2, para G0) | 1 | parcial |
| RF‑17 | `tests/unit/test_normalizacion.py::test_acepta_al_menos_80_por_ciento_del_presupuesto_conocido` (5/5 reconocidas) | — | verde |
| RF‑18, RF‑19 | `tests/unit/test_reglas_civil.py` (0,224 m3 y 4,48 m2 con a=0,80, h=0,80, e=0,10; sensibilidad al ancho) | 12 | verde |
| RF‑20 | — (ninguna prueba: el requisito no tiene implementación; INV‑011) | — | no implementado; declarado en limitaciones |
| RF‑21, RF‑23 | `tests/unit/test_verification.py` (una clase de pruebas por regla; presupuesto intacto; regla sin datos → INFO) | 71 | verde |
| RF‑22 | `tests/integration/test_auditoria_7_de_7.py`: **7 de 7**, uno por regla | 4 | verde (indicador 1) |
| RF‑24 | `test_auditoria_7_de_7.py`: la unidad «mts» del tercero llega intacta a R3 | — | verde |
| RF‑25 | `tests/unit/test_contracts.py` (`TestRendimiento`); `tests/integration/test_rendimientos.py`; `tests/integration/test_api_rendimientos.py` | 2 + 13 + 7 | verde |
| RF‑26 | `test_rendimientos.py` + `test_api_rendimientos.py` (dispersión con n, media, mínimo, máximo; prefiere el medido más reciente) | — | verde |
| RF‑27 | `tests/unit/test_anomalias.py` (`evaluar_rendimiento`); `test_api_rendimientos.py` (201 con `advertencia`, el registro persiste) | 8 | verde |
| RF‑28 | `tests/unit/test_prediccion.py`; `tests/unit/test_resultados_ml.py`; [resultados_ml.md](resultados_ml.md) con MAPE, RMSE, R² | 8 + 2 | verde (G2: reglas; indicador 5) |
| RF‑29 | `test_anomalias.py` (`precios_atipicos`); `test_prediccion.py` (desviación % y hallazgo fuera del rango AACE clase 3) | — | verde |
| RF‑30 | `tests/unit/test_escenarios.py` (parámetros verificados contra el motor; base y composiciones intactos); `tests/integration/test_api_escenarios.py` (`POST /presupuestos/{codigo}/escenarios`: nada se persiste, 422 ante parámetro fuera de rango) | 6 + 3 | verde |
| RF‑31 | `tests/unit/test_escenarios.py` (tabla base + una fila por escenario, exportada a CSV; detalle por partida); la página «Escenarios (UC‑08)» cubierta por humo en `test_ui_importable.py` | — | verde |
| RF‑33 | `tests/integration/test_persistencia.py` (`test_cargar_composicion_sin_condiciones_lanza_valueerror`, `test_reemplazar_composicion_exige_condiciones_no_vacias`: los dos caminos del catálogo); `tests/unit/test_ui_componer.py` (P4.1: el botón «Guardar composicion» nace deshabilitado sin condiciones y se habilita al declararlas; con condiciones pero sin rendimiento, el botón guarda habilitado pero no persiste nada) | 27 + 5 | verde |
| RF‑34 | `tests/unit/test_composicion.py` (`composicion_desde_tablas` acepta y valida la modalidad por fila); `tests/integration/test_persistencia.py::test_la_modalidad_a_destajo_sobrevive_el_viaje_por_el_catalogo`; `tests/integration/test_composicion_extremo_a_extremo.py::test_el_caso_de_demostracion_mezcla_jornal_y_destajo_en_una_partida` (jornal y destajo en una misma partida, por el camino de la pantalla) | 24 + 27 + 14 | verde |
| RF‑35 | `tests/unit/test_composicion.py` (`test_buscar_referencia_*`, 5 pruebas: la referencia MaPreX sugiere; `test_el_precio_sugerido_por_la_referencia_es_editable_y_el_calculo_lo_refleja`, 1 prueba: el precio de la fila sigue siendo un campo editable, nunca de solo lectura, y `core.costing.calcular_apu` refleja el precio editado, no el sugerido) | 34 | verde |
| RF‑36 | `tests/unit/test_ui_app.py` (Inicio por defecto por identidad; ruta vacía → `inicio`) | 21 | verde |
| RF‑37 | `tests/unit/test_ui_recorridos.py` (la declaración única, sin Streamlit); `tests/unit/test_ui_app.py` (integridad de enlaces con y sin modo entrega) | 13 + 21 | verde |
| RF‑38 | `tests/unit/test_ui_caso.py` (una sola ruta por defecto); `tests/unit/test_ui_app.py` (ninguna página salvo el Inicio pide la ruta) | 13 + 21 | verde |
| RF‑39 | `tests/unit/test_ui_caso.py`; `tests/unit/test_ui_app.py` (indicador en las diez pantallas) | 13 + 21 | verde |
| RF‑40 | `tests/unit/test_ui_inicio.py`; `tests/unit/test_ui_caso.py` (sin flag de reinicio en `ui/`) | 9 + 13 | verde |
| RF‑41 | `tests/unit/test_ui_recorridos.py` (`paso_siguiente` y `Recorrido.posicion`); `tests/unit/test_ui_app.py` (botón «Siguiente») | 13 + 21 | verde |
| RF‑42 | `tests/unit/test_ui_app.py` (secciones, orden, subtítulo de caso de uso) | 21 | verde |
| RF‑43 | `tests/unit/test_ui_app.py` (la sección Trabajo intacta en modo entrega; ningún paso sale de Trabajo) | 21 | verde |

**Resumen:** 33 de 34 RF anteriores al
sprint de UI con prueba automatizada en verde; RF‑36 a RF‑43, declarados en U0, en verde desde U1
(fase C3 del cierre). En esas ocho filas, «Casos» cuenta las funciones `def test_` de cada archivo;
`test_ui_app.py` suma 38 casos al contar sus parámetros. RF‑16 parcial (su parte de UI está
cubierta, su persistencia espera un flujo que no existe — hallazgo registrado). **Los RF esenciales
anteriores al sprint de UI y RF‑36 a RF‑43 tienen prueba en verde.**

Cobertura adicional no exigida por RF: `test_generador_ifc.py` (1), `test_visor3d.py` (4),
`test_openapi.py` (2), `test_simulador.py` (2), `test_api.py` (14), `test_civil_verificacion.py`
(3) y `test_meta_alpha.py` (26).

### 8.1 Trazabilidad por paso de UC‑12

Regla (metodología §3.4): cada paso numerado y cada flujo alternativo de un caso de uso cita la
prueba o el caso manual que lo demuestra; un paso sin fila es un requisito sin verificar. La regla
nace de la auditoría del PR #7: el paso 1 de UC‑11 estaba escrito y nunca se implementó, y ninguna
prueba lo reclamaba.

| Paso de UC‑12 | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 abre en Inicio | RF‑36 | `tests/unit/test_ui_app.py::test_la_aplicacion_arranca_en_el_inicio`, `::test_la_ruta_vacia_de_la_pagina_por_defecto_es_el_inicio` | verde |
| 2 caso abierto en la barra lateral | RF‑39 | `tests/unit/test_ui_app.py::test_cada_pantalla_muestra_el_caso_abierto_y_su_titulo`; `tests/unit/test_ui_caso.py::test_resumen_de_cada_estado` | verde |
| 3 fija el caso para la sesión | RF‑38 | `tests/unit/test_ui_inicio.py::test_abrir_otro_caso_lo_fija_en_la_clave_propia`; `tests/unit/test_ui_app.py::test_ninguna_pantalla_distinta_del_inicio_pide_la_ruta` | verde |
| 4 elige un recorrido | RF‑37 | `tests/unit/test_ui_inicio.py::test_el_inicio_ofrece_los_tres_recorridos`, `::test_elegir_un_recorrido_lo_fija_en_la_clave_propia` | verde |
| 5 posición y paso siguiente; menú por oficio | RF‑41, RF‑42 | `tests/unit/test_ui_app.py::test_la_barra_lateral_indica_el_paso_del_recorrido`, `::test_el_boton_siguiente_lleva_al_paso_que_sigue`, `::test_desde_el_inicio_el_siguiente_es_el_primer_paso`, `::test_sin_modo_entrega_dos_secciones_en_el_orden_del_trabajo` | verde |
| 6 obtiene el resultado del recorrido | RNF‑10 | CP‑07 (`docs/guion_prueba_arenia.md`) | ejecutable; se mide en Med (GU1b) |
| 1a modo entrega | RF‑43 | `tests/unit/test_ui_app.py::test_modo_entrega_omite_investigacion_y_conserva_todo_trabajo`, `::test_la_aplicacion_arranca_en_modo_entrega`, `::test_ningun_paso_sale_de_la_seccion_trabajo` | verde |
| 3a caso vacío: siembra sin reinicio | RF‑40 | `tests/unit/test_ui_inicio.py::test_una_base_inexistente_muestra_el_estado_vacio_sin_crearla`, `::test_la_siembra_deja_la_base_utilizable`, `::test_con_partidas_no_se_ofrece_sembrar`, `::test_una_base_existente_sin_partidas_ofrece_sembrar`; `tests/unit/test_ui_caso.py::test_ningun_archivo_de_ui_contiene_el_flag_de_reinicio`, `::test_estado_de_una_base_vacia` | verde |
| 3b archivo ilegible | RF‑39 | `tests/unit/test_ui_inicio.py::test_un_archivo_ilegible_se_informa_sin_ofrecer_sembrar`; `tests/unit/test_ui_caso.py::test_estado_de_un_archivo_que_no_es_sqlite_es_un_error_sin_traza` | verde |
| 5a pantalla fuera del recorrido | RF‑41 | `tests/unit/test_ui_app.py::test_una_pantalla_fuera_del_recorrido_no_muestra_siguiente` | verde |

## 9. Trazabilidad RNF → verificación

| RNF | Cómo se verificó | Resultado |
|---|---|---|
| RNF‑01 exactitud | línea base reproducida exacta (RF‑01, RF‑06): desviación 0,00 % ≪ clase 3 AACE | cumple |
| RNF‑02 reproducibilidad | `test_precios_se_reconstruyen_a_fecha`: reconstrucción idéntica, 100 % | cumple |
| RNF‑03 desempeño | `scripts/medir_rnf03.py` (2026‑08‑31): UC‑02 con **100 partidas y 41 insumos revalorados en 1,17 s** (umbral 5 s) | cumple |
| RNF‑04 usabilidad | juicio de expertos Likert ≥ 4/5: instrumento por aplicar con el tutor | pendiente |
| RNF‑05 núcleo cerrado | `git diff --stat core/` vacío tras I5 y tras cada adaptador; `test_arquitectura.py` verde | cumple |
| RNF‑06 cobertura | `core/` 98,10 % (meta ≥ 80 %); detalle en §10 | cumple |
| RNF‑07 portabilidad | `uv sync --locked` sin pasos manuales; suite completa en verde en Windows 11 (local) y en Linux y Windows por CI ([run 34969162933](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/34969162933), 2026‑09‑15) | cumple |
| RNF‑08 seguridad | inspección: 0 credenciales versionadas, 0 llamadas de red en operación (excepción declarada: descarga inicial del modelo, cacheada) | cumple |
| RNF‑09 compatibilidad IFC | G1 con salvedad: exacto contra modelo programático; faltan exports de ≥ 2 modeladores | parcial |
| RNF‑10 aprendizaje de la interfaz | caso con persona CP‑07 ([guion_prueba_arenia.md](guion_prueba_arenia.md)), dos escenarios con personas distintas, bloque B del anexo A | pendiente (GU1b, fase Med) |

## 10. Registro de la ejecución (2026‑09‑14)

```
479 passed in 109.47s          (pytest -W error, plataforma win32, Python 3.13.2)
ruff check .                   sin observaciones
git diff m-base --stat -- core/   vacío
```

Corrida de la Sesión M4.1 del sprint multidominio (rama `worktree-sprint-multidominio`). Desde el
registro anterior la suite creció en 84 casos, los de las sesiones M0.1–M4.1: referencia MaPreX
estructurada, catálogo, presupuesto y auditoría de telecom (ARENAZA), industrial (mantenimiento) y
sistemas (puntos de función), la meta del sprint y la sección multidominio de
[resultados_ml.md](resultados_ml.md). Todo ese crecimiento ocurrió sin tocar `core/`. Registros
anteriores, todos del 2026‑08‑31: 385 en F.2 (`core/` 97,99 %), 392 tras el cierre de UC‑08 en el
núcleo y 395 tras cablear UC‑08 en la API y la UI.

Cobertura de líneas por paquete (pytest‑cov sobre la corrida completa):

| Paquete | Líneas cubiertas | Cobertura |
|---|---|---|
| `core/` | 1 707 / 1 740 | **98,10 %** |
| `ml/` | 141 / 142 | 99,30 % |
| `api/` | 452 / 478 | 94,56 % |
| `adapters/` | 372 / 419 | 88,78 % |
| **Total medido** | 2 672 / 2 779 | **96,15 %** |

`core/` tiene las mismas 1 740 líneas que el 2026‑08‑31; la línea adicional cubierta la ejercen las
pruebas de integración de los dominios nuevos. Las dos líneas nuevas de `ml/` son la cuantización
de presentación de `contrastar_aace` (M4.1).

Distribución de la suite: 345 casos unitarios y 134 de integración, 0 fallos, 0 omitidos.
La evaluación de calidad sobre estos resultados está en [calidad_iso25010.md](calidad_iso25010.md).
