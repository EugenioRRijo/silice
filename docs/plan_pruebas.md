# Plan de pruebas y registro de ejecución (IEEE 829) — Sesión F.2

Plan de pruebas del sistema de generación y auditoría de APU multidominio, según la estructura de
IEEE 829 y con la trazabilidad que exige [metodologia.md §7](metodologia.md#7-trazabilidad): cada
caso de prueba cita su RF; los enunciados de los RF viven **una sola vez** en
[ERS.md §3.2](ERS.md#32-requisitos-funcionales) y aquí no se repiten (CLAUDE.md §2, DRY).

## 1. Identificador y alcance

- **Identificador:** PP‑APU‑001, versión de la Sesión F.2 (2026‑08‑31), actualizada en la fase C4
  del cierre (2026‑09‑28): cifras de la corrida de CI de §10 y matriz por paso de todos los casos
  de uso (§8.1).
- **Alcance:** todo el software del repositorio (`core/`, `adapters/`, `ml/`, `api/`, `ui/`,
  `scripts/`) contra los RF‑01…RF‑43 (RF‑32 vacante) y RNF‑01…RNF‑10 de la ERS.
- **Referencias:** [CLAUDE.md](../CLAUDE.md) (constitución), [ERS.md](ERS.md) (IEEE 830),
  [metodologia.md](metodologia.md) (indicadores y trazabilidad),
  [linea_base.md](linea_base.md) (caso auditado), bitácoras en [bitacora/](bitacora/).

## 2. Elementos de prueba

Versión probada: la de la corrida de CI registrada en §10, commit `308eca5` (cierre de la fase C3),
idéntico en contenido a `main` en `ceb6b8e`. Elementos:

| Paquete | Contenido | Nivel de prueba |
|---|---|---|
| `core/contracts` | contratos estables (§5 de CLAUDE.md) | unitario (invariantes) |
| `core/costing` | motor de costos (función pura) | unitario contra la línea base |
| `core/models`, `core/catalog` | persistencia SQLite y catálogo | unitario + integración |
| `core/budget` | presupuesto, curva, exportación, UC‑02 | unitario + integración |
| `core/verification` | reglas R1–R7 e informe | unitario + integración (7 de 7) |
| `adapters/{civil,telecom,industrial,sistemas}` | extracción de cantidades | unitario + arquitectura |
| `ml/{normalization,anomaly,prediction}` | RF‑15/17, RF‑27/29, RF‑28 | unitario |
| `api/` | 18 operaciones FastAPI (`docs/api.json`) + OpenAPI | integración (TestClient) |
| `ui/` | Streamlit multipágina y visor 3D | unitario con `streamlit.testing.v1.AppTest` + humo (importación) |
| `scripts/` | seed, simulador, generadores, metas | unitario + ejecución directa |

## 3. Características a probar y a no probar

**A probar:** los 42 RF de la ERS (matriz de la sección 8) y los RNF verificables por software o
por medición (RNF‑01, 02, 03, 05, 06, 07, 08; sección 9).

**A no probar en esta sesión, con causa:**

- **RNF‑04 (usabilidad del informe):** requiere juicio de expertos con escala Likert; no es
  automatizable. Se mide en la fase Med de [PLAN_CIERRE.md](../PLAN_CIERRE.md), con el protocolo que
  C4 deja escrito antes de medir (la Fase 6 del plan de desarrollo ya cerró; INV‑062).
- **RNF‑10 (capacidad de aprendizaje de la interfaz):** no es automatizable; se mide con el caso con
  persona CP‑07 de [guion_prueba_arenia.md](guion_prueba_arenia.md) en la compuerta GU1b (fase Med)
  de [PLAN_UI.md](../PLAN_UI.md). Sus requisitos funcionales RF‑36 a RF‑43 **sí** tienen prueba
  automatizada, en verde (sección 8, U1).
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
4. **Arquitectura como prueba.** `test_arquitectura.py` (sus casos parametrizados crecen solos con
   cada módulo que nace: el cierre de UC‑08 añadió el suyo sin tocar la prueba) falla si un
   adaptador importa de `core` algo distinto de `core.contracts`: la hipótesis central se vigila en
   cada corrida.
5. **Advertencias como errores.** La suite corre con `-W error`: cualquier advertencia de
   dependencia o de código propio rompe la corrida.
6. **Determinismo.** Todo lo estocástico fija semilla (Isolation Forest y simulador con
   semilla 42); las pruebas de caracterización añadidas en F1‑fixes se verificaron por mutación
   (se comprobó que fallan ante el defecto que documentan).
7. **Metas de sprint automatizadas.** `scripts/meta_alpha.py` y `scripts/meta_i6.py` evalúan las
   metas de cierre (12/12 en el sprint I6) leyendo la corrida de pytest, la cobertura y el estado
   del repositorio; ellos mismos tienen pruebas (`test_meta_alpha.py` y las de cada meta).

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

**Entorno de la ejecución registrada (§10):** los runners de GitHub `ubuntu-latest` (Python
3.13.13) y `windows-latest` (Python 3.13.15), con `uv sync --locked --all-extras`, SQLite y el modelo
de `sentence-transformers` restaurado de la caché de la CI. Comandos locales equivalentes:

```
uv sync --locked --all-extras
uv run pytest -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml --cov=core --cov=ml --cov=api --cov=adapters --cov-report=term
uv run python scripts/verificar_omitidas.py reporte-pruebas.xml
uv run coverage report --include="core/*" --fail-under=80
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

**Fuente única** (INV‑032): esta tabla es el único lugar donde cada RF se traza a las pruebas que lo
demuestran y a su estado. El enunciado y el criterio de aceptación viven en la fila homónima de
[ERS.md §3.2](ERS.md#32-requisitos-funcionales), sin estado; el README y la metodología enlazan aquí.
Cada prueba se cita como `archivo::función` (o `archivo::Clase::función`); `::función` a secas
pertenece al último archivo nombrado en la misma celda. Todas existen en el commit probado de la
sección 10 (`uv run pytest --collect-only -q` las lista) y pasan en esa corrida.

Estados: **verde** (una prueba automatizada lo demuestra y pasa en la corrida de §10); **parcial**
(una parte del criterio tiene prueba y otra no existe; la celda dice cuál); **no implementado** (el
requisito no tiene código y está declarado en limitaciones).

| RF | Prueba(s) que lo demuestran | Estado |
|---|---|---|
| RF‑01 | `tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base` (5 APU ± 0,01), `::test_los_materiales_no_se_dividen_entre_el_rendimiento`, `::test_administracion_y_utilidad_se_aplican_en_cascada` | verde |
| RF‑02 | `tests/integration/test_auditoria_7_de_7.py::test_detecta_las_siete_inconsistencias`; `tests/unit/test_budget.py::test_elaborar_siempre_devuelve_informe`; `tests/integration/test_presupuesto_linea_base.py::test_guardar_persiste_renglones_curva_y_hallazgos`; la recarga declara los pendientes del documento emitido (C3, INV‑080): `tests/integration/test_recarga_con_pendientes.py::test_la_recarga_devuelve_el_informe_emitido_con_sus_pendientes` y, por HTTP, `tests/integration/test_api.py::test_el_informe_recargado_declara_el_pendiente`, `::test_el_excel_recargado_declara_el_pendiente_en_la_auditoria` | verde; residuo en bases guardadas antes de `04ca90d` (dictamen C3‑3, [manual técnico](manual_tecnico.md)) |
| RF‑03 | `tests/unit/test_contracts.py::TestItemComputo::test_origen_obligatorio`, `::TestItemComputo::test_regla_obligatoria_si_origen_es_regla`, `::TestItemComputo::test_regla_con_parametros_queda_congelada`; `tests/unit/test_reglas_civil.py::test_los_items_son_trazables`; `tests/integration/test_auditoria_7_de_7.py::test_todo_hallazgo_de_partida_referencia_un_origen_trazable` | verde |
| RF‑04 | `tests/unit/test_arquitectura.py::test_un_adaptador_solo_importa_contratos_su_paquete_y_sus_terceros`, `::test_toda_carpeta_de_adapters_tiene_su_regla`; `tests/unit/test_adapter_civil_ifc.py::test_g1_lo_extraido_coincide_con_el_calculo_manual` (`origen_id` = GlobalId); `tests/unit/test_adapter_telecom.py::test_origen_id_es_la_clave_de_fila` | verde, con la salvedad de G1 (§3) |
| RF‑05 | `tests/integration/test_persistencia.py::test_composicion_reconstruye_cada_apu_identico`, `::test_seed_carga_cinco_partidas_y_una_lista` | verde |
| RF‑06 | `tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61`, `::test_cada_renglon_reproduce_el_total_auditado`; `tests/integration/test_presupuesto_linea_base.py::test_elaborar_desde_el_catalogo_reproduce_1586_61`, `::test_los_renglones_referencian_la_partida_del_catalogo` | verde |
| RF‑07 | `tests/unit/test_budget.py::test_curva_cierra_exactamente_en_el_total`, `::test_curva_con_fracciones_arbitrarias_cierra`; `tests/integration/test_composicion_extremo_a_extremo.py::test_la_curva_del_caso_de_demostracion_cierra_en_el_total` | verde |
| RF‑08 | `tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas`; `tests/unit/test_elaboracion.py::test_el_libro_se_abre_y_tiene_la_hoja_de_auditoria` | verde |
| RF‑09 | `tests/unit/test_arquitectura.py` (todo el archivo); `tests/unit/test_adapter_telecom.py::test_extrae_nodos_y_enlaces_de_la_muestra`; `tests/unit/test_adapter_industrial.py::test_extrae_los_activos_de_la_muestra`; `tests/unit/test_adapter_sistemas.py::test_extrae_los_casos_de_uso_de_la_muestra`; `git diff --stat core/` vacío tras I5 y la guardia `scripts/guardia_nucleo.py` en cada corrida de CI | verde (indicador 4) |
| RF‑10 | `tests/integration/test_actualizacion_precios.py::test_leer_lista_precios_devuelve_decimales_exactos`, `::test_leer_lista_precios_xlsx_lee_decimales_exactos`, `::test_leer_lista_precios_rechaza_lo_que_no_es_un_numero_no_negativo`, `::test_actualizar_precios_solo_revalora_el_concreto`, `::test_una_fila_con_unidad_no_equivalente_se_rechaza_y_las_demas_se_procesan` | verde |
| RF‑11 | `tests/integration/test_actualizacion_precios.py::test_uc02_no_edita_ninguna_composicion`, `::test_actualizar_precios_solo_revalora_el_concreto` | verde |
| RF‑12 | `tests/integration/test_actualizacion_precios.py::test_registra_un_cambio_de_precio_por_insumo_afectado`, `::test_registra_la_incidencia_de_cada_cambio_en_el_concreto`, `::test_los_cambios_de_precio_se_releen_tras_cerrar_la_sesion` | verde |
| RF‑13 | `tests/integration/test_actualizacion_precios.py::test_el_comparativo_suma_los_totales`, `::test_el_comparativo_detalla_la_partida_que_cambio` | verde |
| RF‑14 | `tests/integration/test_persistencia.py::test_precios_se_reconstruyen_a_fecha`; `tests/integration/test_actualizacion_precios.py::test_el_presupuesto_anterior_sigue_reconstruyendose_a_su_fecha` | verde |
| RF‑15 | `tests/unit/test_normalizacion.py::test_propuestas_ordenadas_por_puntaje_y_sobre_el_umbral`, `::test_cuantos_acota_el_numero_de_propuestas` | verde |
| RF‑16 | la precarga (desglose, rendimiento, partida de origen y puntaje) la pinta `ui/paginas/similares.py` y solo tiene la prueba de humo `tests/unit/test_ui_importable.py::test_las_paginas_se_importan_sin_efectos`; la persistencia de la partida nueva con esa referencia no existe (decisión D5 del tutor, pendiente) | parcial (INV‑027: estado único) |
| RF‑17 | `tests/unit/test_normalizacion.py::test_acepta_al_menos_80_por_ciento_del_presupuesto_conocido` | verde |
| RF‑18 | `tests/unit/test_reglas_civil.py::test_concreto_por_tanquilla_es_0_224`, `::test_encofrado_por_tanquilla_es_4_48`, `::test_los_items_son_trazables` | verde |
| RF‑19 | `tests/unit/test_reglas_civil.py::test_cambiar_el_ancho_altera_solo_las_cantidades_que_dependen_de_el`; `tests/unit/test_recalculo_uc04.py::test_uc04_recalcula_precios_curva_y_auditoria_al_cambiar_el_ancho`; flujos 1a, 2a y 2b de UC‑04 en §8.1 | verde |
| RF‑20 | — (ninguna prueba: el requisito no tiene implementación; INV‑011) | no implementado; declarado en limitaciones |
| RF‑21 | `tests/unit/test_verification.py`, una o más pruebas por regla: `::test_r1_encofrado_y_concreto_con_impacto`, `::test_r2_brecha_11_11`, `::test_r3_reporta_unidad_original_mts`, `::test_r4_marca_3_4_pulg_y_no_marca_pvc`, `::test_r5_relleno_vs_balance`, `::test_r6_vehiculo_0_03_vs_1_00`, `::test_r7_dia_a_dia`; lista vacía cuando cumple: R5 y R7, `::test_r5_no_reporta_nada_si_el_balance_se_cumple`, `::test_r7_concilia_una_curva_con_corchetes`; R1 y R3, `tests/integration/test_presupuesto_sistemas.py::test_la_auditoria_no_reporta_errores_r1_acepta_ifpug_y_r3_acepta_pf`; R1, `tests/integration/test_presupuesto_industrial.py::test_la_auditoria_no_reporta_errores_y_r1_acepta_la_regla_de_intervenciones`, `tests/integration/test_auditoria_arenaza.py::test_el_presupuesto_1_no_tiene_el_hallazgo_80_90`; R6, `tests/integration/test_composicion_r6.py::test_mismo_factor_de_la_referencia_r6_no_emite_hallazgo`; R2 y R4, ninguna (`tests/unit/test_verification.py::test_r2_no_reporta_acumulados_rotos_en_una_curva_bien_sumada` solo afirma que no hay ERROR); para el conjunto, solo la ausencia de ERROR y CRITICO: `tests/integration/test_auditoria_7_de_7.py::test_el_presupuesto_corregido_no_tiene_errores`; ninguna prueba audita un presupuesto con cero hallazgos (§8.1, UC‑05 5a) | parcial: la lista vacía no tiene prueba en R2 ni en R4 |
| RF‑22 | `tests/integration/test_auditoria_7_de_7.py::test_detecta_las_siete_inconsistencias`: **7 de 7**, uno por regla | verde (indicador 1) |
| RF‑23 | `tests/unit/test_verification.py::test_el_informe_ordena_los_hallazgos_por_severidad_descendente`, `::test_r1_reporta_la_regla_que_no_puede_evaluar`, `::test_r5_reporta_un_balance_que_no_puede_evaluar` (INFO sin abortar); presupuesto idéntico antes y después: `tests/integration/test_auditoria_arenaza.py::test_la_auditoria_corre_sobre_el_presupuesto_telecom_completo` | verde |
| RF‑24 | la unidad «mts» del autor llega intacta a R3 sobre un `Presupuesto` construido en memoria: `tests/unit/test_verification.py::test_r3_reporta_unidad_original_mts`; la importación de un archivo tabular de un tercero no existe (INV‑076, abierto) | parcial |
| RF‑25 | `tests/unit/test_contracts.py::TestRendimiento::test_medido_exige_referencia`; `tests/integration/test_rendimientos.py::test_registrar_medido_sin_referencia_se_rechaza`, `::test_registrar_medido_traza_la_ejecucion`, `::test_referencia_de_ejecucion_inexistente_se_rechaza`; `tests/integration/test_api_rendimientos.py::test_medido_sin_referencia_es_422_y_con_referencia_real_queda_trazado` | verde |
| RF‑26 | `tests/integration/test_rendimientos.py::test_dispersion_exacta_y_con_tipos_contados`, `::test_propuesta_prefiere_el_medido_mas_reciente`, `::test_propuesta_sin_medidos_cae_al_estimado_mas_reciente`; `tests/integration/test_api_rendimientos.py::test_get_trae_historico_dispersion_y_propuesta` | verde |
| RF‑27 | `tests/unit/test_anomalias.py::test_rendimiento_desviado_es_atipico_pero_el_veredicto_no_prohibe`, `::test_rendimiento_coherente_con_lo_observado_no_es_atipico`, `::test_historico_insuficiente_no_da_veredicto`; `tests/integration/test_rendimientos.py::test_advertencia_cuando_el_valor_se_aparta_del_rango_observado`; `tests/integration/test_api_rendimientos.py::test_advertencia_fuera_del_rango_observado_sin_impedir_el_registro` | verde |
| RF‑28 | `tests/unit/test_prediccion.py::test_tecnica_para_es_la_tabla_de_la_compuerta_g2`, `::test_metricas_exactas_mape_rmse_r2`, `::test_prediccion_por_reglas_con_rango_de_sensibilidad`; `tests/unit/test_resultados_ml.py::test_el_informe_declara_conteo_tecnica_y_metricas`; la CI regenera [resultados_ml.md](resultados_ml.md) sin diferencias (§7) | verde (G2: reglas; indicador 5) |
| RF‑29 | `tests/unit/test_prediccion.py::test_contraste_aace_fuera_del_rango_es_hallazgo_advertencia`, `::test_contraste_aace_dentro_del_rango_no_produce_hallazgo`; `tests/unit/test_anomalias.py::test_la_variacion_extrema_es_atipica_y_tiene_el_peor_puntaje`, `::test_los_atipicos_salen_ordenados_del_mas_anomalo_al_menos` | verde |
| RF‑30 | `tests/unit/test_escenarios.py::test_escenario_de_parametros_recalcula_cada_partida_contra_el_motor`, `::test_escenario_de_precios_sube_solo_las_partidas_afectadas`, `::test_el_presupuesto_base_y_las_composiciones_quedan_intactos`; `tests/integration/test_api_escenarios.py::test_los_escenarios_no_persisten_ninguna_version`, `::test_parametro_fuera_de_rango_se_rechaza_por_el_contrato` | verde |
| RF‑31 | `tests/unit/test_escenarios.py::test_tabla_comparativa_una_fila_por_escenario_con_total_y_variacion`, `::test_tabla_comparativa_es_exportable`, `::test_comparativo_por_partida_del_escenario`; `tests/integration/test_api_escenarios.py::test_base_mas_una_entrada_por_escenario_con_detalle`; la página «Escenarios de sensibilidad»: `tests/unit/test_ui_escenarios.py::test_el_escenario_de_un_base_con_pendientes_los_declara` | verde |
| RF‑33 | `tests/integration/test_persistencia.py::test_cargar_composicion_sin_condiciones_lanza_valueerror`, `::test_reemplazar_composicion_exige_condiciones_no_vacias` (los dos caminos del catálogo); `tests/unit/test_ui_componer.py::test_sin_condiciones_el_boton_de_guardar_esta_deshabilitado`, `::test_sin_rendimiento_guardar_no_persiste_nada` | verde |
| RF‑34 | `tests/unit/test_costing_destajo.py` (todo el archivo); `tests/unit/test_composicion.py::test_una_fila_de_mano_de_obra_sin_modalidad_es_jornal`, `::test_una_modalidad_desconocida_se_rechaza_nombrando_la_fila`; `tests/integration/test_persistencia.py::test_la_modalidad_a_destajo_sobrevive_el_viaje_por_el_catalogo`; `tests/integration/test_composicion_extremo_a_extremo.py::test_el_caso_de_demostracion_mezcla_jornal_y_destajo_en_una_partida`; `tests/unit/test_ui_componer.py::test_teclear_el_codigo_de_una_partida_guardada_precarga_sus_tres_tablas`; `tests/unit/test_budget.py::test_hoja_apu_muestra_la_modalidad_de_mano_de_obra` | verde |
| RF‑35 | `tests/unit/test_composicion.py::test_buscar_referencia_encuentra_la_fila_esperada_con_ref_y_precio_decimal` y las otras cuatro pruebas `test_buscar_referencia_*` del mismo archivo (la referencia MaPreX sugiere); `::test_el_precio_sugerido_por_la_referencia_es_editable_y_el_calculo_lo_refleja` | verde |
| RF‑36 | `tests/unit/test_ui_app.py::test_la_aplicacion_arranca_en_el_inicio`, `::test_la_ruta_vacia_de_la_pagina_por_defecto_es_el_inicio`, `::test_el_inicio_es_la_primera_pagina_y_la_unica_por_defecto` | verde |
| RF‑37 | `tests/unit/test_ui_recorridos.py::test_hay_tres_recorridos_en_el_orden_declarado`; `tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas[ui/recorridos.py]` (sin Streamlit ni base de datos); `tests/unit/test_ui_app.py::test_todo_paso_apunta_a_una_pagina_registrada` | verde |
| RF‑38 | `tests/unit/test_ui_caso.py::test_la_ruta_guardada_en_la_sesion_manda`, `::test_sin_ruta_en_la_sesion_manda_la_variable_de_entorno`, `::test_sin_sesion_ni_entorno_queda_la_ruta_por_defecto`, `::test_la_ruta_por_defecto_se_define_una_sola_vez_en_ui`; `tests/unit/test_ui_app.py::test_ninguna_pantalla_distinta_del_inicio_pide_la_ruta` | verde |
| RF‑39 | `tests/unit/test_ui_caso.py::test_resumen_de_cada_estado`, `::test_estado_de_un_archivo_que_no_es_sqlite_es_un_error_sin_traza`; `tests/unit/test_ui_app.py::test_cada_pantalla_muestra_el_caso_abierto_y_su_titulo` | verde |
| RF‑40 | `tests/unit/test_ui_inicio.py::test_una_base_inexistente_muestra_el_estado_vacio_sin_crearla`, `::test_la_siembra_deja_la_base_utilizable`, `::test_con_partidas_no_se_ofrece_sembrar`; `tests/unit/test_ui_caso.py::test_ningun_archivo_de_ui_contiene_el_flag_de_reinicio` | verde |
| RF‑41 | `tests/unit/test_ui_recorridos.py::test_paso_siguiente_avanza_y_se_detiene_en_el_ultimo`, `::test_posicion_es_de_base_uno_y_none_fuera_del_recorrido`; `tests/unit/test_ui_app.py::test_el_boton_siguiente_lleva_al_paso_que_sigue`, `::test_una_pantalla_fuera_del_recorrido_no_muestra_siguiente` | verde |
| RF‑42 | `tests/unit/test_ui_app.py::test_sin_modo_entrega_dos_secciones_en_el_orden_del_trabajo`, `::test_ningun_titulo_lleva_codigo_de_caso_de_uso`, `::test_las_cinco_pantallas_con_caso_de_uso_lo_declaran` | verde |
| RF‑43 | `tests/unit/test_ui_app.py::test_modo_entrega_omite_investigacion_y_conserva_todo_trabajo`, `::test_ningun_paso_sale_de_la_seccion_trabajo` | verde |

**Resumen:** de los 42 RF, **38 en verde**, **3 parciales** (RF‑16, RF‑21 y RF‑24, los tres
esenciales: la persistencia de la referencia de RF‑16 espera la decisión D5 del tutor, la lista vacía
de RF‑21 no tiene prueba en R2 ni en R4 y la importación de RF‑24 es INV‑076, abierto) y
**1 no implementado** (RF‑20, deseable, en limitaciones). Ningún RF esencial queda sin ninguna prueba,
pero RF‑16 solo tiene la de humo, que no ejercita la precarga.

Las demás pruebas de la suite no demuestran un RF concreto: guardias de arquitectura y de la base de
trabajo, metas de sprint, scripts, referencias de precios, dominios del sprint multidominio, API
(OpenAPI y errores HTTP) y visor 3D. Su recuento es el de la sección 10.

### 8.1 Trazabilidad por paso de todos los casos de uso

Regla (metodología §3.4): cada paso numerado y cada flujo alternativo de un caso de uso cita la
prueba o el caso manual que lo demuestra; un paso sin fila es un requisito sin verificar. La regla
nace de la auditoría del PR #7: el paso 1 de UC‑11 estaba escrito y nunca se implementó, y ninguna
prueba lo reclamaba. Desde C4 la matriz cubre los once casos de uso de la
[ERS §2.2](ERS.md#22-funciones-del-producto-casos-de-uso), con sus flujos alternativos (INV‑033,
condición F5 del final del proyecto). La capa que realiza cada caso de uso está en
[ERS §3.1](ERS.md#31-interfaces-externas).

Mismas convenciones de cita que la sección 8. Estados de un paso: **verde** (una prueba automatizada
lo demuestra y pasa en la corrida de §10); **manual** (solo lo demuestra un caso del
[guion](guion_prueba_arenia.md), cuya ejecución no está registrada todavía: su §8 está en blanco);
**parcial** (la celda dice qué parte tiene prueba y qué parte no); **sin prueba** (el comportamiento
existe, pero ninguna prueba ni caso manual lo demuestra); **no implementado** (el paso, tal como está
escrito, no existe en ninguna capa). Donde una prueba automatizada existe, el caso manual que también
lo recorre se cita entre paréntesis como apoyo.

#### UC‑01 — Elaborar presupuesto nuevo desde una fuente de cantidades

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 crea el proyecto y selecciona fuente y dominio | RF‑04 | la fuente y el dominio: `tests/integration/test_api.py::test_computo_civil_desde_la_muestra`, `::test_computo_civil_desde_un_modelo_ifc` (`POST /computos/{dominio}`); el proyecto no se crea: la API exige uno ya sembrado y la interfaz no lo pide | parcial: crear el proyecto no está implementado |
| 2 extrae los `ItemComputo` con su origen | RF‑03, RF‑04 | `tests/unit/test_reglas_civil.py::test_adaptador_tabular_extrae_la_muestra`; `tests/unit/test_adapter_civil_ifc.py::test_g1_lo_extraido_coincide_con_el_calculo_manual`; `tests/unit/test_adapter_telecom.py::test_extrae_nodos_y_enlaces_de_la_muestra`; `tests/unit/test_adapter_industrial.py::test_extrae_los_activos_de_la_muestra`; `tests/unit/test_adapter_sistemas.py::test_extrae_los_casos_de_uso_de_la_muestra` | verde |
| 3 asocia cada ítem a su partida y recupera composición y rendimiento | RF‑05, RF‑06 | `tests/integration/test_persistencia.py::test_composicion_reconstruye_cada_apu_identico`; `tests/integration/test_presupuesto_linea_base.py::test_los_renglones_referencian_la_partida_del_catalogo` | verde |
| 4 el motor calcula cada `ResultadoAPU` | RF‑01 | `tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base` | verde |
| 5 arma el `Presupuesto` con totales | RF‑06 | `tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61`, `::test_cada_renglon_reproduce_el_total_auditado`; `tests/integration/test_presupuesto_linea_base.py::test_elaborar_desde_el_catalogo_reproduce_1586_61`; `tests/integration/test_api.py::test_elaborar_presupuesto_por_http_reproduce_el_total_auditado` | verde |
| 6 el proyectista distribuye en períodos; la curva cierra en el total | RF‑07 | la curva cierra: `tests/unit/test_budget.py::test_curva_cierra_exactamente_en_el_total`, `::test_curva_con_fracciones_arbitrarias_cierra`, `::test_elaborar_acepta_el_plan_como_funcion_del_presupuesto_valorado`; la distribución no la hace el proyectista: la interfaz y la API usan siempre `plan_secuencial` (una partida por día) | parcial: distribuir los períodos no está implementado en la interfaz ni en la API; el núcleo acepta cualquier plan |
| 7 verifica y emite el informe sin que se pida | RF‑02 | `tests/unit/test_budget.py::test_elaborar_siempre_devuelve_informe`; `tests/unit/test_ui_elaborar.py::test_el_item_sin_partida_queda_pendiente_con_sus_propuestas` (el informe en la pantalla) (CP‑06) | verde |
| 8 exporta presupuesto y curva a XLSX | RF‑08 | `tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas`; `tests/unit/test_elaboracion.py::test_el_libro_se_abre_y_tiene_la_hoja_de_auditoria`; `tests/unit/test_ui_componer.py::test_de_componer_a_excel_desde_la_pantalla` (CP‑05) | verde |
| 2a fuente ilegible o de otro dominio | RF‑04 | fuentes malformadas en dos adaptadores: `tests/unit/test_adapter_telecom.py::test_longitud_vacia_falla_con_fila_y_columna` (un CSV de telecom con una longitud vacía falla nombrando la fila y la columna); `tests/unit/test_reglas_civil.py::test_adaptador_tabular_exige_una_zanja_para_el_balance_de_relleno`, `::test_adaptador_tabular_rechaza_dos_zanjas_de_diametros_distintos` (el CSV civil sin zanja, o con dos diámetros, se rechaza); `tests/unit/test_adapter_civil_ifc.py::test_dos_cantidades_del_mismo_tipo_ifc_son_ambiguas` (un IFC ambiguo falla con el GlobalId, no un IFC corrupto). Sin prueba: un IFC corrupto o ilegible, una fuente de otro dominio, un archivo malformado de industrial o de sistemas, la respuesta de `POST /computos/{dominio}` a una fuente ilegible (`ValueError` → 422, `api/main.py`) y el mensaje de la página «Elaborar un presupuesto» (`st.error`) | parcial |
| 3a ítem sin partida: pendiente, propuestas y reelaboración (orden de C3‑10) | RF‑02, RF‑15 | `tests/unit/test_budget.py::test_un_item_sin_partida_queda_pendiente_y_el_informe_lo_declara`; `tests/unit/test_ui_elaborar.py::test_el_item_sin_partida_queda_pendiente_con_sus_propuestas`, `::test_aceptar_una_propuesta_vuelve_a_elaborar_sin_pendientes`, `::test_aceptar_cambia_solo_el_item_pendiente`, `::test_sin_el_extra_el_pendiente_se_declara_sin_propuestas`; `tests/integration/test_api.py::test_un_item_sin_partida_queda_pendiente_por_http`, `::test_si_todos_los_items_quedan_pendientes_el_presupuesto_sale_vacio_y_no_cumple` | verde |
| 3b partida sin rendimiento vigente: propone el del histórico | RF‑26 | ninguna: la elaboración exige un rendimiento estimado vigente y, si falta, se detiene con `CatalogoIncompleto` (`core/catalog/repositorio.py`, `_rendimiento_estimado`); la propuesta del histórico con su dispersión existe en UC‑06 (paso 3), no en la elaboración | no implementado |
| 6a sin plan de trabajo: sin curva, R2 no aplicable | RF‑07 | `tests/unit/test_budget.py::test_elaborar_siempre_devuelve_informe` (sin plan, `curva == ()`); `tests/unit/test_verification.py::test_r2_informa_cuando_no_hay_curva`, `::test_r7_se_declara_no_aplicable_si_el_presupuesto_no_declara_curva` | verde en el núcleo; la interfaz y la API siempre pasan un plan, así que por ellas el flujo no ocurre |
| 7a hallazgos `CRITICO`: se emite igual, con ellos al frente | RF‑23 | `tests/unit/test_verification.py::test_r2_brecha_11_11` (un `CRITICO`), `::test_el_informe_ordena_los_hallazgos_por_severidad_descendente` | verde |

#### UC‑02 — Actualizar masivamente los precios de un presupuesto existente

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 carga el archivo con su vigencia y su moneda | RF‑10 | `tests/integration/test_actualizacion_precios.py::test_leer_lista_precios_devuelve_decimales_exactos`, `::test_leer_lista_precios_xlsx_lee_decimales_exactos`, `::test_crear_lista_copia_los_precios_anteriores_y_sobrescribe_los_del_archivo`, `::test_el_presupuesto_nuevo_queda_persistido_con_su_lista` | verde |
| 2 valida columnas, tipos y unidades; todo importe a `Decimal` | RF‑10 | `tests/integration/test_actualizacion_precios.py::test_leer_lista_precios_rechaza_lo_que_no_es_un_numero_no_negativo`, `::test_leer_lista_precios_devuelve_decimales_exactos` | verde |
| 3 identifica los insumos que cambian y sus partidas | RF‑10 | `tests/integration/test_actualizacion_precios.py::test_actualizar_precios_solo_revalora_el_concreto`; `tests/integration/test_api.py::test_actualizacion_por_http_solo_revalora_el_concreto` | verde |
| 4 recalcula y produce una versión nueva sin editar composiciones | RF‑11 | `tests/integration/test_actualizacion_precios.py::test_uc02_no_edita_ninguna_composicion`, `::test_uc02_exige_composicion_para_todo_renglon_antes_de_guardar` | verde |
| 5 un registro de cambio por insumo, con su incidencia | RF‑12 | `tests/integration/test_actualizacion_precios.py::test_registra_un_cambio_de_precio_por_insumo_afectado`, `::test_registra_la_incidencia_de_cada_cambio_en_el_concreto`, `::test_repetir_uc02_con_el_mismo_par_de_listas_no_duplica_el_historial` | verde |
| 6 informe comparativo por partida y total | RF‑13 | `tests/integration/test_actualizacion_precios.py::test_el_comparativo_suma_los_totales`, `::test_el_comparativo_detalla_la_partida_que_cambio` | verde |
| 7 acepta o descarta la versión nueva | RF‑11 | `tests/unit/test_ui_actualizacion.py::test_revalorar_con_cambios_ofrece_descartar_la_version_guardada` (la versión se guarda y el botón de descartar aparece) | verde |
| 2a insumos desconocidos: se listan y se ofrecen dar de alta o ignorar | RF‑10 | `tests/integration/test_actualizacion_precios.py::test_crear_lista_reporta_los_insumos_desconocidos_sin_crearlos`; `tests/integration/test_api.py::test_cargar_lista_de_precios_reporta_desconocidos_vacios` | parcial: se listan y se ignoran; darlos de alta no se ofrece |
| 2b unidad no equivalente: la fila se rechaza y las demás siguen | RF‑10 | `tests/integration/test_actualizacion_precios.py::test_una_fila_con_unidad_no_equivalente_se_rechaza_y_las_demas_se_procesan` | verde |
| 3a ningún precio cambió: no hay versión nueva | RF‑11 | `tests/unit/test_ui_actualizacion.py::test_revalorar_sin_cambios_no_guarda_ni_ofrece_descartar`; `tests/integration/test_api.py::test_actualizacion_sin_cambios_de_precio_responde_409_sin_persistir` | verde |
| 4a el base tiene ítems pendientes (UC‑01 3a) | RF‑02 | `tests/integration/test_recarga_con_pendientes.py::test_revalorar_arrastra_los_pendientes_del_base` | verde |
| 7a descarta la versión: se marca y el historial se conserva | RF‑12 | `tests/integration/test_actualizacion_precios.py::test_descartar_la_version_nueva_la_marca_y_conserva_el_historial`, `::test_con_tres_versiones_solo_se_descarta_la_ultima`, `::test_el_presupuesto_base_nunca_se_descarta`, `::test_una_version_no_se_descarta_dos_veces`; `tests/unit/test_ui_actualizacion.py::test_descartar_version_marca_la_version_y_conserva_el_historial`, `::test_descartar_marca_la_base_donde_se_guardo_aunque_se_cambie_de_caso` | verde |

#### UC‑03 — Reutilizar partidas y desgloses de proyectos anteriores

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 escribe la descripción en texto libre | RF‑15 | `tests/unit/test_normalizacion.py::test_descripcion_identica_es_la_primera_propuesta_con_puntaje_cercano_a_uno` | verde en `ml/`; la página «Partidas similares» solo tiene pruebas de degradación (`tests/unit/test_ui_similares.py::test_sin_el_extra_la_pagina_lo_dice`) |
| 2 devuelve las tres más similares con su puntaje | RF‑15 | `tests/unit/test_normalizacion.py::test_propuestas_ordenadas_por_puntaje_y_sobre_el_umbral`, `::test_cuantos_acota_el_numero_de_propuestas`; `tests/integration/test_api.py::test_la_propuesta_real_reconoce_la_partida_de_la_misma_descripcion` | verde |
| 3 el proyectista selecciona una | RF‑16 | en UC‑01 3a: `tests/unit/test_ui_elaborar.py::test_aceptar_una_propuesta_vuelve_a_elaborar_sin_pendientes`; en la página «Partidas similares» la selección es desplegar la propuesta, sin prueba | parcial |
| 4 precarga composición y rendimiento con origen y puntaje | RF‑16 | la página los muestra; solo `tests/unit/test_ui_importable.py::test_las_paginas_se_importan_sin_efectos` (humo) | sin prueba (RF‑16 parcial) |
| 5 ajusta y el sistema recalcula | RF‑16 | la página «Partidas similares» es de solo lectura; el ajuste y el recálculo en vivo ocurren en «Componer una partida» (UC‑10, paso 6) | no implementado en UC‑03 |
| 2a ningún candidato supera el umbral | RF‑15 | `tests/unit/test_normalizacion.py::test_nada_supera_el_umbral_no_propone_nada` | verde |
| 2b catálogo vacío | RF‑15 | `tests/unit/test_normalizacion.py::test_catalogo_vacio_no_propone_sin_error` | verde |
| 4a el desglose usa insumos sin precio vigente | RF‑16 | ninguna: la página muestra el aviso de `CatalogoIncompleto` sin prueba | sin prueba |

#### UC‑04 — Recalcular ante cambio de alcance o dimensiones

UC‑04 no tiene pantalla ni ruta: lo realiza `adapters/civil/recalculo.py` (ERS §3.1).

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 modifica un parámetro dimensional o un conteo | RF‑19 | `tests/unit/test_recalculo_civil.py::test_recalcular_equivale_a_extraer_la_fuente_editada`; `tests/unit/test_reglas_civil.py::test_cambiar_el_ancho_altera_solo_las_cantidades_que_dependen_de_el` | verde |
| 2 reevalúa las reglas y produce `ItemComputo` con su expresión | RF‑18, RF‑19 | `tests/unit/test_recalculo_civil.py::test_recalcular_equivale_a_extraer_la_fuente_editada`; `tests/unit/test_reglas_civil.py::test_los_items_son_trazables` | verde |
| 3 recalcula las partidas y el total | RF‑19 | `tests/unit/test_recalculo_uc04.py::test_uc04_recalcula_precios_curva_y_auditoria_al_cambiar_el_ancho` | verde |
| 4 regenera la curva y la verificación | RF‑19 | `tests/unit/test_recalculo_uc04.py::test_uc04_recalcula_precios_curva_y_auditoria_al_cambiar_el_ancho` | verde |
| 5 muestra el diferencial por partida | RF‑20 | — | no implementado (RF‑20, limitaciones) |
| 1a el parámetro no participa en ninguna regla | RF‑19 | `tests/unit/test_recalculo_civil.py::test_1a_un_parametro_sin_regla_no_recalcula_y_se_informa`, `::test_1a_un_cambio_dirigido_al_relleno_se_rechaza` | verde |
| 2a la fuente es IFC: reimportar y emparejar por GlobalId | RF‑04, RF‑19 | `tests/unit/test_adapter_civil_ifc.py::test_uc04_2a_un_objeto_ifc_no_se_recalcula_por_reglas`, `::test_uc04_2a_reimportar_empareja_por_global_id`; `tests/unit/test_recalculo_civil.py::test_emparejar_rechaza_claves_repetidas_en_cualquiera_de_las_versiones` | verde |
| 2b cantidad negativa o nula: rechazo atómico del objeto; R5 si es el relleno | RF‑19 | `tests/unit/test_recalculo_civil.py::test_2b_una_cantidad_nula_se_rechaza_y_conserva_la_anterior`, `::test_2b_el_rechazo_es_atomico_por_objeto`, `::test_2b_un_relleno_negativo_se_rechaza_y_r5_lo_declara` | verde |

#### UC‑05 — Auditar un presupuesto elaborado por un tercero

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 selecciona el presupuesto o importa el archivo del tercero | RF‑24 | seleccionar uno propio: `tests/integration/test_api.py::test_el_informe_recargado_declara_el_pendiente` (`GET /presupuestos/{codigo}/informe`); importar el archivo de un tercero: ninguna (INV‑076) | parcial: la importación no está implementada |
| 2 construye el `Presupuesto` conservando las unidades del autor | RF‑24 | `tests/unit/test_verification.py::test_r3_reporta_unidad_original_mts`, sobre el presupuesto de prueba construido en memoria (`tests/fixtures/presupuesto_auditado.py`); por la vía de las cantidades tecleadas en «Componer una partida» el ítem toma la unidad de la partida, así que R3 no se dispara por esa vía (dictamen C3‑47) | parcial: sin archivo de un tercero |
| 3 ejecuta R1–R7 | RF‑21, RF‑22 | `tests/integration/test_auditoria_7_de_7.py::test_detecta_las_siete_inconsistencias` | verde |
| 4 cada hallazgo con severidad, descripción, impacto y `origen_id` | RF‑21 | `tests/integration/test_auditoria_7_de_7.py::test_todo_hallazgo_de_partida_referencia_un_origen_trazable`; `tests/unit/test_verification.py::test_r1_encofrado_y_concreto_con_impacto`; `tests/unit/test_contracts.py::TestVerificacion::test_hallazgo_exige_regla_y_descripcion` | verde |
| 5 ordena por severidad y emite el informe | RF‑23 | `tests/unit/test_verification.py::test_el_informe_ordena_los_hallazgos_por_severidad_descendente`, `::test_informe_markdown_contiene_resumen_y_partidas` (CP‑06) | verde |
| 6 exporta el informe | RF‑02 | `tests/unit/test_elaboracion.py::test_el_libro_se_abre_y_tiene_la_hoja_de_auditoria`; `tests/integration/test_api.py::test_el_excel_recargado_declara_el_pendiente_en_la_auditoria` | verde |
| 2a sin plan de trabajo: R2 y R7 no aplicables | RF‑23 | `tests/unit/test_verification.py::test_r2_informa_cuando_no_hay_curva`, `::test_r7_se_declara_no_aplicable_si_el_presupuesto_no_declara_curva` | verde |
| 2b cantidades sin regla: R1 declara la trazabilidad ausente | RF‑03, RF‑21 | `tests/unit/test_verification.py::test_r1_advierte_de_las_cantidades_manuales_sin_regla`; sin origen no hay ítem: `tests/unit/test_contracts.py::TestItemComputo::test_origen_obligatorio` | verde |
| 3a una regla no evaluable: INFO y la ejecución continúa | RF‑23 | `tests/unit/test_verification.py::test_r1_reporta_la_regla_que_no_puede_evaluar`, `::test_r5_reporta_un_balance_que_no_puede_evaluar`, `::test_r4_informa_de_una_especificacion_que_no_puede_contrastar` | verde |
| 5a sin hallazgos: el informe se emite igual y declara las siete reglas evaluadas | RF‑02, RF‑21 | ninguna prueba audita un presupuesto con cero hallazgos (es también la parte sin prueba de RF‑21), y el informe (`InformeAuditoria.a_markdown`) no enumera las reglas evaluadas | sin prueba; la enumeración de las siete reglas, no implementada |

#### UC‑06 — Registrar y consultar rendimientos reales de obra ejecutada

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 registra el rendimiento observado con su referencia | RF‑25 | `tests/integration/test_api_rendimientos.py::test_medido_sin_referencia_es_422_y_con_referencia_real_queda_trazado`, `::test_ejecucion_se_registra_se_lista_y_no_se_duplica` | verde |
| 2 lo persiste como MEDIDO exigiendo la referencia | RF‑25 | `tests/integration/test_rendimientos.py::test_registrar_medido_traza_la_ejecucion`; `tests/unit/test_contracts.py::TestRendimiento::test_medido_exige_referencia` | verde |
| 3 propone el rendimiento del histórico con su dispersión | RF‑26 | `tests/integration/test_rendimientos.py::test_dispersion_exacta_y_con_tipos_contados`, `::test_propuesta_prefiere_el_medido_mas_reciente`; `tests/integration/test_api_rendimientos.py::test_get_trae_historico_dispersion_y_propuesta` (CP‑02 y CP‑04, paso 1, en «Componer una partida») | verde |
| 4 advierte sin impedir el registro | RF‑27 | `tests/integration/test_api_rendimientos.py::test_advertencia_fuera_del_rango_observado_sin_impedir_el_registro`, `::test_dentro_del_rango_observado_no_hay_advertencia`; `tests/integration/test_rendimientos.py::test_advertencia_cuando_el_valor_se_aparta_del_rango_observado` (CP‑04) | verde |
| 5 nunca mezcla estimados con medidos | RF‑26 | `tests/integration/test_rendimientos.py::test_dispersion_exacta_y_con_tipos_contados`, `::test_propuesta_sin_medidos_cae_al_estimado_mas_reciente`; `tests/integration/test_persistencia.py::test_reemplazar_composicion_tras_un_medido_no_deja_el_estimado_obsoleto` | verde |
| 1a falta la referencia a la ejecución | RF‑25 | `tests/integration/test_rendimientos.py::test_registrar_medido_sin_referencia_se_rechaza`, `::test_referencia_de_ejecucion_inexistente_se_rechaza`, `::test_referencia_de_ejecucion_vacia_se_rechaza_por_las_dos_puertas` | verde |
| 3a sin histórico: propone el estimado del catálogo, rotulado | RF‑26 | `tests/integration/test_rendimientos.py::test_propuesta_sin_medidos_cae_al_estimado_mas_reciente`, `::test_dispersion_de_partida_sin_rendimientos_es_none` | verde |
| 4a acepta la advertencia: su justificación queda junto al APU | RF‑27 | ninguna: ni el registro (`RendimientoPeticion`) ni la composición tienen un campo de justificación | no implementado |

#### UC‑07 — Contrastar el precio construido con el precio de mercado

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 selecciona una partida o un presupuesto | RF‑28 | una partida, al componerla: `tests/unit/test_composicion_ia.py::test_contrastar_precio_con_reglas_ofrece_el_marco_aace_cuando_hay_hallazgo` (CP‑02, paso 2); los presupuestos de todos los dominios, por `scripts/generar_resultados_ml.py`: `tests/unit/test_resultados_ml.py::test_el_informe_tabula_las_predicciones_con_su_rango` | verde; elegir un presupuesto concreto no tiene pantalla ni ruta |
| 2 determina la técnica por el conteo | RF‑28 | `tests/unit/test_prediccion.py::test_tecnica_para_es_la_tabla_de_la_compuerta_g2`; `tests/unit/test_resultados_ml.py::test_el_informe_declara_conteo_tecnica_y_metricas` | verde |
| 3 estima y reporta MAPE, RMSE y R² | RF‑28 | `tests/unit/test_prediccion.py::test_metricas_exactas_mape_rmse_r2`, `::test_prediccion_por_reglas_con_rango_de_sensibilidad` | verde |
| 4 contrasta y expresa la desviación en porcentaje | RF‑29 | `tests/unit/test_prediccion.py::test_contraste_aace_fuera_del_rango_es_hallazgo_advertencia`, `::test_contraste_aace_presenta_a_dos_decimales_con_redondeo_hacia_arriba` | verde |
| 5 marca los atípicos y los incorpora al informe de auditoría | RF‑29 | se marcan: `tests/unit/test_anomalias.py::test_los_atipicos_salen_ordenados_del_mas_anomalo_al_menos`; se tabulan en `docs/resultados_ml.md`; ninguna capa los agrega al informe de auditoría del presupuesto | parcial: la incorporación al informe no está implementada |
| 2a menos de 50 registros: reglas con sensibilidad, como limitación | RF‑28 | `tests/unit/test_prediccion.py::test_tecnica_para_es_la_tabla_de_la_compuerta_g2`, `::test_prediccion_por_reglas_con_rango_de_sensibilidad`; `tests/unit/test_resultados_ml.py::test_con_un_dominio_en_el_umbral_el_informe_no_afirma_que_todos_estan_por_debajo` | verde |
| 3a partida sin análogas: no se estima y se informa | RF‑28 | para una partida nueva la ayuda 4 de «Componer una partida» no estima: `_contraste_aace` retorna sin nada si la partida no existe (`ui/paginas/componer.py`, docstring de `contrastar_precio_con_reglas` en `ui/composicion.py`), pero no informa que el contraste no es posible, y ninguna prueba lo fija. Otra condición, vecina: con un histórico de variaciones del dominio vacío, la predicción por reglas es el precio base sin rango (`tests/unit/test_prediccion.py::test_sin_historico_de_variaciones_la_prediccion_es_el_precio_base`) | parcial: no se estima, pero no se informa y no hay prueba |
| 4a desviación fuera de la clase 3 de AACE: ADVERTENCIA | RF‑29 | `tests/unit/test_prediccion.py::test_contraste_aace_fuera_del_rango_es_hallazgo_advertencia`; `tests/unit/test_composicion_ia.py::test_contrastar_precio_con_reglas_ofrece_el_marco_aace_cuando_hay_hallazgo` | verde |

#### UC‑08 — Generar escenarios de sensibilidad

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 define el escenario (parámetros o precios) | RF‑30 | `tests/unit/test_escenarios.py::test_escenario_de_parametros_recalcula_cada_partida_contra_el_motor`, `::test_escenario_de_precios_sube_solo_las_partidas_afectadas` | verde |
| 2 recalcula sin alterar el base | RF‑30 | `tests/unit/test_escenarios.py::test_el_presupuesto_base_y_las_composiciones_quedan_intactos`; `tests/integration/test_api_escenarios.py::test_los_escenarios_no_persisten_ninguna_version` | verde |
| 3 total y variación, por partida y en conjunto | RF‑31 | `tests/unit/test_escenarios.py::test_comparativo_por_partida_del_escenario`; `tests/integration/test_api_escenarios.py::test_base_mas_una_entrada_por_escenario_con_detalle` | verde |
| 4 compara varios escenarios y exporta la tabla | RF‑31 | `tests/unit/test_escenarios.py::test_tabla_comparativa_una_fila_por_escenario_con_total_y_variacion`, `::test_tabla_comparativa_es_exportable` | verde |
| 1a parámetro fuera de rango: no se crea | RF‑30 | `tests/integration/test_api_escenarios.py::test_parametro_fuera_de_rango_se_rechaza_por_el_contrato`; `tests/unit/test_contracts.py::TestParametrosCosto::test_negativo` | verde |
| 2a cambia precios de insumos: mecanismo de UC‑02 sin persistir la lista | RF‑30 | `tests/unit/test_escenarios.py::test_escenario_de_precios_sube_solo_las_partidas_afectadas`; `tests/integration/test_api_escenarios.py::test_los_escenarios_no_persisten_ninguna_version` | verde |
| 4a promueve un escenario a presupuesto | RF‑30 | ninguna: promover no existe como acción; por diseño es UC‑02 con la lista del escenario (decisión D6 del dossier, pendiente del tutor) | no implementado |
| base con ítems pendientes (UC‑01 3a; INV‑083) (no es un flujo de la ERS) | RF‑30 | la página los declara: `tests/unit/test_ui_escenarios.py::test_el_escenario_de_un_base_con_pendientes_los_declara`; la API, sin prueba en esta rama; el informe del propio escenario no los lista (dictamen C4‑3, a limitaciones) | parcial |

#### UC‑10 — Componer una partida

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 declara código, descripción y unidad | RF‑33 | `tests/unit/test_elaboracion.py::test_una_partida_nueva_se_persiste_y_se_relee`; `tests/unit/test_composicion.py::test_la_unidad_con_alias_se_normaliza` (CP‑01, paso 6) | verde |
| 2 tabla de materiales | RF‑01 | `tests/unit/test_composicion.py::test_una_tabla_valida_produce_la_composicion_esperada`, `::test_una_fila_de_materiales_con_datos_pero_sin_descripcion_se_rechaza` | verde |
| 3 tabla de equipos con su depreciación | RF‑01 | `tests/unit/test_composicion.py::test_una_tabla_valida_produce_la_composicion_esperada`, `::test_una_depreciacion_fuera_de_rango_nombra_la_tabla_equipos` | verde |
| 4 tabla de mano de obra con su modalidad | RF‑34 | `tests/unit/test_composicion.py::test_una_fila_de_mano_de_obra_sin_modalidad_es_jornal`, `::test_una_modalidad_desconocida_se_rechaza_nombrando_la_fila`; `tests/unit/test_costing_destajo.py::test_la_composicion_mixta_suma_los_dos_bloques` (CP‑03) | verde |
| 5 declara el rendimiento con sus condiciones | RF‑33 | `tests/unit/test_composicion.py::test_un_rendimiento_cero_o_negativo_se_rechaza`; `tests/unit/test_ui_componer.py::test_sin_condiciones_el_boton_de_guardar_esta_deshabilitado` | verde |
| 6 calcula y muestra el desglose en vivo, sin guardar | RF‑01 | `tests/unit/test_ui_componer.py::test_el_desglose_en_vivo_muestra_el_precio_unitario`, `::test_el_desglose_en_vivo_presenta_dos_decimales`; `tests/unit/test_composicion.py::test_desglose_de_la_tuberia_da_el_precio_de_la_linea_base` (CP‑01, paso 8) | verde |
| 7 guarda la composición | RF‑33 | `tests/unit/test_ui_componer.py::test_de_componer_a_excel_desde_la_pantalla`; `tests/unit/test_elaboracion.py::test_una_partida_nueva_se_persiste_y_se_relee` (CP‑01, paso 10) | verde |
| 8 la persiste con su rendimiento y sus condiciones | RF‑33 | `tests/integration/test_persistencia.py::test_cargar_composicion_registra_las_condiciones_declaradas`; `tests/integration/test_composicion_extremo_a_extremo.py::test_el_caso_de_demostracion_sobrevive_al_camino_de_la_pantalla` | verde |
| 2a/3a/4a fila vacía: se descarta | RF‑33 | `tests/unit/test_composicion.py::test_las_filas_vacias_se_descartan`, `::test_una_fila_con_nan_en_todas_las_celdas_se_descarta_como_vacia`, `::test_una_fila_con_none_en_todas_las_celdas_se_descarta_como_vacia` | verde |
| 2b/3b/4b buscador de la referencia de mercado; precio editable | RF‑35 | `tests/unit/test_composicion.py::test_buscar_referencia_encuentra_la_fila_esperada_con_ref_y_precio_decimal`, `::test_buscar_referencia_factor_depreciacion_solo_lleno_en_equipos`, `::test_el_precio_sugerido_por_la_referencia_es_editable_y_el_calculo_lo_refleja` (CP‑01, pasos 1 a 4) | verde |
| 5a sin rendimiento o sin condiciones: no se persiste | RF‑33 | `tests/unit/test_ui_componer.py::test_sin_condiciones_el_boton_de_guardar_esta_deshabilitado`, `::test_sin_rendimiento_guardar_no_persiste_nada`; `tests/integration/test_persistencia.py::test_cargar_composicion_sin_condiciones_lanza_valueerror` | verde |
| 7a la partida ya tiene composición: se edita (UC‑11) | RF‑33 | `tests/integration/test_persistencia.py::test_cargar_composicion_dos_veces_lanza_valueerror`; `tests/unit/test_ui_componer.py::test_guardar_dos_veces_edita_la_partida` (CP‑02, paso 6) | verde |

#### UC‑11 — Editar una partida compuesta

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 abre la partida: tablas y rendimiento precargados | RF‑34 | `tests/unit/test_ui_componer.py::test_teclear_el_codigo_de_una_partida_guardada_precarga_sus_tres_tablas` (CP‑04, paso 1) | verde |
| 2 modifica insumos, cantidades, precios o modalidad | RF‑34 | `tests/unit/test_ui_componer.py::test_editar_una_cantidad_y_guardar_reemplaza_la_composicion` | verde |
| 3 declara un rendimiento nuevo con sus condiciones | RF‑33 | `tests/integration/test_persistencia.py::test_reemplazar_composicion_propaga_las_condiciones_al_rendimiento`; `tests/unit/test_ui_componer.py::test_guardar_dos_veces_edita_la_partida` | verde |
| 4 recalcula en vivo sobre la composición modificada | RF‑01 | CP‑02 paso 2 y CP‑03 (sobre la partida editada); la prueba automatizada del desglose, `tests/unit/test_ui_componer.py::test_el_desglose_en_vivo_muestra_el_precio_unitario`, es de UC‑10, sobre una composición nueva | manual |
| 5 guarda | RF‑33 | `tests/unit/test_ui_componer.py::test_editar_una_cantidad_y_guardar_reemplaza_la_composicion`, `::test_guardar_dos_veces_edita_la_partida` (CP‑02, paso 3). La rama con éxito de `ui.elaboracion.guardar_composicion` sobre una partida existente no tiene prueba unitaria propia en `tests/unit/test_elaboracion.py`: la cubre la pantalla (QA‑A5 de C3) | verde por la pantalla; sin unitaria propia |
| 6 reemplaza la composición y conserva el rendimiento anterior | RF‑33 | `tests/integration/test_persistencia.py::test_reemplazar_composicion_permite_corregir_una_partida`, `::test_reemplazar_conserva_el_rendimiento_anterior_en_el_historico`, `::test_reemplazar_composicion_agrega_rendimiento_solo_si_cambian_condiciones`, `::test_reemplazar_composicion_sin_cambios_no_agrega_rendimiento` | verde |
| 3a sin rendimiento nuevo con condiciones: no se guarda | RF‑33 | `tests/integration/test_persistencia.py::test_reemplazar_composicion_exige_condiciones_no_vacias`; `tests/unit/test_ui_componer.py::test_sin_condiciones_el_boton_de_guardar_esta_deshabilitado` | verde |
| 6a la partida no existe: se rechaza el reemplazo | RF‑33 | `tests/integration/test_persistencia.py::test_reemplazar_una_partida_inexistente_lanza_lookuperror` | verde |

#### UC‑12 — Recorrer la aplicación guiado desde el Inicio

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 abre en Inicio | RF‑36 | `tests/unit/test_ui_app.py::test_la_aplicacion_arranca_en_el_inicio`, `::test_la_ruta_vacia_de_la_pagina_por_defecto_es_el_inicio` | verde |
| 2 caso abierto en la barra lateral | RF‑39 | `tests/unit/test_ui_app.py::test_cada_pantalla_muestra_el_caso_abierto_y_su_titulo`; `tests/unit/test_ui_caso.py::test_resumen_de_cada_estado` | verde |
| 3 fija el caso para la sesión | RF‑38 | `tests/unit/test_ui_inicio.py::test_abrir_otro_caso_lo_fija_en_la_clave_propia`; `tests/unit/test_ui_app.py::test_ninguna_pantalla_distinta_del_inicio_pide_la_ruta` | verde |
| 4 elige un recorrido | RF‑37 | `tests/unit/test_ui_inicio.py::test_el_inicio_ofrece_los_tres_recorridos`, `::test_elegir_un_recorrido_lo_fija_en_la_clave_propia` | verde |
| 5 posición y paso siguiente; menú por oficio | RF‑41, RF‑42 | `tests/unit/test_ui_app.py::test_la_barra_lateral_indica_el_paso_del_recorrido`, `::test_el_boton_siguiente_lleva_al_paso_que_sigue`, `::test_desde_el_inicio_el_siguiente_es_el_primer_paso`, `::test_sin_modo_entrega_dos_secciones_en_el_orden_del_trabajo` | verde |
| 6 obtiene el resultado del recorrido | RNF‑10 | CP‑07 (`docs/guion_prueba_arenia.md`) | manual (CP‑07; se mide en Med, GU1b) |
| 1a modo entrega | RF‑43 | `tests/unit/test_ui_app.py::test_modo_entrega_omite_investigacion_y_conserva_todo_trabajo`, `::test_la_aplicacion_arranca_en_modo_entrega`, `::test_ningun_paso_sale_de_la_seccion_trabajo` | verde |
| 3a caso vacío: siembra sin reinicio | RF‑40 | `tests/unit/test_ui_inicio.py::test_una_base_inexistente_muestra_el_estado_vacio_sin_crearla`, `::test_la_siembra_deja_la_base_utilizable`, `::test_con_partidas_no_se_ofrece_sembrar`, `::test_una_base_existente_sin_partidas_ofrece_sembrar`; `tests/unit/test_ui_caso.py::test_ningun_archivo_de_ui_contiene_el_flag_de_reinicio`, `::test_estado_de_una_base_vacia` | verde |
| 3b archivo ilegible | RF‑39 | `tests/unit/test_ui_inicio.py::test_un_archivo_ilegible_se_informa_sin_ofrecer_sembrar`; `tests/unit/test_ui_caso.py::test_estado_de_un_archivo_que_no_es_sqlite_es_un_error_sin_traza` | verde |
| 5a pantalla fuera del recorrido | RF‑41 | `tests/unit/test_ui_app.py::test_una_pantalla_fuera_del_recorrido_no_muestra_siguiente` | verde |

#### Resumen de la matriz por paso

Recuento de las filas de esta sección por el estado con que empieza su última celda (una fila
«verde en el núcleo…» cuenta como verde; su celda dice qué capa no lo ejerce). No cuenta la fila
rotulada «(no es un flujo de la ERS)» de UC‑08, que traza INV‑083 (1 fila). Los pasos
parciales, sin prueba o no implementados son hallazgos de esta matriz y quedan para decisión en
la compuerta GC4: C4 es documentación y no los resuelve.

| UC | Pasos y flujos | Verde | Manual | Parcial | Sin prueba | No implementado |
|---|---|---|---|---|---|---|
| UC‑01 | 13 | 9 | 0 | 3 | 0 | 1 |
| UC‑02 | 12 | 11 | 0 | 1 | 0 | 0 |
| UC‑03 | 8 | 4 | 0 | 1 | 2 | 1 |
| UC‑04 | 8 | 7 | 0 | 0 | 0 | 1 |
| UC‑05 | 10 | 7 | 0 | 2 | 1 | 0 |
| UC‑06 | 8 | 7 | 0 | 0 | 0 | 1 |
| UC‑07 | 8 | 6 | 0 | 2 | 0 | 0 |
| UC‑08 | 7 | 6 | 0 | 0 | 0 | 1 |
| UC‑10 | 12 | 12 | 0 | 0 | 0 | 0 |
| UC‑11 | 8 | 7 | 1 | 0 | 0 | 0 |
| UC‑12 | 10 | 9 | 1 | 0 | 0 | 0 |
| **Total** | **104** | **85** | **2** | **9** | **3** | **5** |

## 9. Trazabilidad RNF → verificación

| RNF | Cómo se verificó | Resultado |
|---|---|---|
| RNF‑01 exactitud | línea base reproducida exacta (RF‑01, RF‑06): desviación 0,00 % ≪ clase 3 AACE | cumple |
| RNF‑02 reproducibilidad | `test_precios_se_reconstruyen_a_fecha`: reconstrucción idéntica, 100 % | cumple |
| RNF‑03 desempeño | `scripts/medir_rnf03.py` (2026‑08‑31): UC‑02 con **100 partidas y 41 insumos revalorados en 1,17 s** (umbral 5 s) | cumple |
| RNF‑04 usabilidad | juicio de expertos Likert ≥ 4/5, con el protocolo de C4, en la fase Med de [PLAN_CIERRE.md](../PLAN_CIERRE.md) | pendiente (Med) |
| RNF‑05 núcleo cerrado | `git diff --stat core/` vacío tras I5 y tras cada adaptador; `test_arquitectura.py` verde | cumple |
| RNF‑06 cobertura | cobertura de `core/` en la corrida de §10 (meta ≥ 80 %, que la CI exige con `--fail-under=80`) | cumple |
| RNF‑07 portabilidad | `uv sync --locked --all-extras` sin pasos manuales y la suite completa en verde en Linux y en Windows en la corrida de §10 ([36427904452](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36427904452)) | cumple |
| RNF‑08 seguridad | inspección: 0 credenciales versionadas, 0 llamadas de red en operación salvo las dos excepciones que declara la ERS: la descarga inicial del modelo (cacheada) y three.js desde `cdnjs.cloudflare.com` en el Visor 3D (INV‑077) | cumple, con las dos excepciones declaradas |
| RNF‑09 compatibilidad IFC | G1 con salvedad: exacto contra modelo programático; faltan exports de ≥ 2 modeladores | parcial |
| RNF‑10 aprendizaje de la interfaz | caso con persona CP‑07 ([guion_prueba_arenia.md](guion_prueba_arenia.md)), dos escenarios con personas distintas, bloque B del anexo A | pendiente (GU1b, fase Med) |

## 10. Registro de la ejecución (CI, 2026‑09‑28)

**Fuente única de las cifras de la suite y de la cobertura** (INV‑031; la CI es la fuente de verdad
de las cifras, [metodologia.md §6](metodologia.md#6-gestión-de-configuración)): la corrida
[36427904452](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36427904452)
del PR #14, sobre el commit `308eca5` (cierre de C3), idéntico en contenido a `main` en `ceb6b8e`.
La CI prueba la fusión de ese commit con la base del PR (`91b938a` en el registro del trabajo). Los
demás documentos enlazan esta sección y no copian sus cifras.

```
calidad (ruff + guardia del nucleo)  ruff: All checks passed!   guardia del nucleo: OK
pruebas (ubuntu-latest)   926 passed in 96.75s   Python 3.13.13   verificar omitidas: 0 omitidas
pruebas (windows-latest)  926 passed in 173.39s  Python 3.13.15   verificar omitidas: 0 omitidas
```

Distribución de la suite: **926 casos** recogidos, 721 en `tests/unit/` y 205 en
`tests/integration/`, 0 fallos y 0 omitidos, en las dos plataformas. El reparto por carpeta se lee
con `uv run pytest --collect-only -q` sobre el mismo commit.

Cobertura, del trabajo `pruebas (ubuntu-latest)` de esa corrida (`coverage.py` cuenta
**sentencias**, no líneas; la CI publica el porcentaje entero y el exacto se calcula de sus columnas
`Stmts` y `Miss`):

| Paquete | Sentencias cubiertas | Cobertura publicada | Exacta |
|---|---|---|---|
| `core/` | 1 811 / 1 841 | **98 %** | 98,37 % |
| `ml/` | 173 / 174 | — | 99,43 % |
| `api/` | 466 / 492 | — | 94,72 % |
| `adapters/` | 474 / 521 | — | 90,98 % |
| **Total medido** | 2 924 / 3 028 | **97 %** | 96,57 % |

La CI publica el porcentaje de `core/` en el paso «Cobertura de core/ ≥ 80 %»
(`coverage report --include="core/*" --fail-under=80`) y el total en la tabla de la suite; los de
`ml/`, `api/` y `adapters/` son la suma de sus filas en esa misma tabla. `ui/` y `scripts/` no se
miden.

Registros anteriores, que esta sección sustituye: 385 casos en F.2 y 392 y 395 tras el cierre de
UC‑08 (los tres del 2026‑08‑31, locales), 479 en la Sesión M4.1 del sprint multidominio
(2026‑09‑14, local, con `core/` al 98,10 %) y 926 en esta corrida. La evaluación de
calidad sobre estos resultados está en [calidad_iso25010.md](calidad_iso25010.md).
