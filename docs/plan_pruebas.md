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
| RF‑21 | `tests/unit/test_verification.py`, una o más pruebas por regla: `::test_r1_encofrado_y_concreto_con_impacto`, `::test_r2_brecha_11_11`, `::test_r3_reporta_unidad_original_mts`, `::test_r4_marca_3_4_pulg_y_no_marca_pvc`, `::test_r5_relleno_vs_balance`, `::test_r6_vehiculo_0_03_vs_1_00`, `::test_r7_dia_a_dia`; sin errores cuando el presupuesto cumple: `tests/integration/test_auditoria_7_de_7.py::test_el_presupuesto_corregido_no_tiene_errores` | verde |
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

**Resumen:** de los 42 RF, **39 en verde**, **2 parciales** (RF‑16 y RF‑24, los dos esenciales: la
persistencia de la referencia de RF‑16 espera la decisión D5 del tutor y la importación de RF‑24 es
INV‑076, abierto) y **1 no implementado** (RF‑20, deseable, en limitaciones). Ningún RF esencial queda
sin ninguna prueba.

Las demás pruebas de la suite no demuestran un RF concreto: guardias de arquitectura y de la base de
trabajo, metas de sprint, scripts, referencias de precios, dominios del sprint multidominio, API
(OpenAPI y errores HTTP) y visor 3D. Su recuento es el de la sección 10.

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
