# Plan de pruebas y registro de ejecución (IEEE 829) — Sesión F.2

Plan de pruebas del sistema de generación y auditoría de APU multidominio, según la estructura de
IEEE 829 y con la trazabilidad que exige [metodologia.md §7](metodologia.md#7-trazabilidad): cada
caso de prueba cita su RF; los enunciados de los RF viven **una sola vez** en
[ERS.md §3.2](ERS.md#32-requisitos-funcionales) y aquí no se repiten (NORMAS.md §2, DRY).

## 1. Identificador y alcance

- **Identificador:** PP‑APU‑001, versión de la Sesión F.2 (2026‑08‑31), actualizada en la fase C4
  del cierre (2026‑09‑28): cifras de la corrida de CI de §10 y matriz por paso de todos los casos
  de uso (§8.1); y en la fase C5 (2026‑09‑28): las matrices de §8 y §8.1 al código que corrige los
  hallazgos de C5 (las cifras de §10 las sustituyó la corrida de la compuerta GC5, 2026‑09‑29); y
  en la fase C6 (2026‑09‑29): las matrices de §8 y §8.1 al código de C6 y las cifras de la corrida de
  la CI de la compuerta GC6 (2026‑09‑29) en §10.
- **Alcance:** todo el software del repositorio (`core/`, `adapters/`, `ml/`, `api/`, `ui/`,
  `scripts/`) contra los RF‑01…RF‑43 (RF‑32 vacante) y RNF‑01…RNF‑10 de la ERS.
- **Referencias:** [NORMAS.md](../NORMAS.md) (constitución), [ERS.md](ERS.md) (IEEE 830),
  [metodologia.md](metodologia.md) (indicadores y trazabilidad),
  [linea_base.md](linea_base.md) (caso auditado), bitácoras en [bitacora/](bitacora/).

## 2. Elementos de prueba

Versión probada: la corrida de la CI de §10, sobre `6eb8b84` (compuerta GC6 del cierre, PR #17),
fusionado a prueba con `main` en `c47b57e`; el código de C6 es el de `5b33e5f` con el lote del
encargo de QA de GC6 (`eb06e96`), y los commits posteriores solo tocan documentos. Elementos:

| Paquete | Contenido | Nivel de prueba |
|---|---|---|
| `core/contracts` | contratos estables (§5 de NORMAS.md) | unitario (invariantes) |
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

1. **Pruebas antes que implementación en el núcleo** (NORMAS.md §2.5): la línea base verificada
   (`tests/fixtures/apu_linea_base.py`, única copia) existe desde antes que el motor;
   `test_costing.py` no se modificó para ponerse en verde.
2. **Dos niveles.** `tests/unit/` prueba cada pieza aislada (contratos, motor, reglas,
   adaptadores, ml); `tests/integration/` prueba flujos completos sobre SQLite real (sembrar →
   elaborar → auditar → actualizar precios → reconstruir a fecha).
3. **Exactitud decimal.** Los importes se comparan como `Decimal` exactos; la única tolerancia
   admitida es ± 0,01 sobre el precio unitario de los cinco APU de la línea base (NORMAS.md §4).
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

Si una prueba del núcleo se pone en rojo, la regla de NORMAS.md §9 aplica: no se parchea la
prueba; se corrige la implementación o, si el contrato resulta insuficiente, se documenta el
hallazgo en `docs/bitacora/` y se detiene la sesión. Estado esperado histórico: hasta I0.3 la
suite estuvo deliberadamente roja en `test_costing.py` (marcador `rojo_esperado`).

## 7. Entregables y entorno

**Entregables:** este plan, [calidad_iso25010.md](calidad_iso25010.md), la bitácora de la sesión,
el reporte de cobertura (sección 10) y `scripts/medir_rnf03.py` (evidencia reproducible del
RNF‑03). Desde la Sesión P4.2, además, el [guion de prueba manual de AREN.IA](guion_prueba_arenia.md)
(casos CP‑01 a CP‑06 de la pantalla de componer, para quien pruebe sin programar).

**Entorno de la última corrida de la CI (§10):** los runners de GitHub `ubuntu-latest` (Python
3.13.13, uv 0.11.9) y `windows-latest` (Python 3.13.15), con `uv sync --locked --all-extras`, SQLite y el modelo
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
`tests/integration/test_api_escenarios.py::test_los_escenarios_de_un_base_con_pendientes_los_declaran`,
citada en la fila RF‑30 y en la tabla de UC‑08, entró en la fase C4 (INV‑083), después de `308eca5`,
y por eso quedaba fuera de la corrida anterior de la sección 10; la de la compuerta GC4, que la
sustituyó, ya la incluye. Lo mismo vale para las pruebas que entraron en la fase C5 (INV‑087,
INV‑088, INV‑089, INV‑091, INV‑092, INV‑094, INV‑095 e INV‑096), citadas en esta sección y en §8.1:
existían en `f629f94` (`uv run pytest --collect-only -q`, 1 037 casos) y pasaban en local, pero
quedaban fuera de la corrida de `e7a0569`; la de la compuerta GC5, que sustituyó a esa en §10, ya
las incluye. Y para las de la fase C6 (INV‑076, INV‑086, INV‑090, INV‑093 e INV‑099): existen en
`e6c84c1` (`uv run pytest --collect-only -q`, 1 167 casos) y pasan en la corrida local de la
compuerta GC6, y la corrida de la CI de §10 (`6eb8b84`, GC6), que sustituyó a la de GC5, ya las
incluye.

Estados: **verde** (una prueba automatizada lo demuestra y pasa en la corrida de §10); **parcial**
(una parte del criterio tiene prueba y otra no existe; la celda dice cuál); **no implementado** (el
requisito no tiene código y está declarado en limitaciones).

| RF | Prueba(s) que lo demuestran | Estado |
|---|---|---|
| RF‑01 | `tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base` (5 APU ± 0,01), `::test_los_materiales_no_se_dividen_entre_el_rendimiento`, `::test_administracion_y_utilidad_se_aplican_en_cascada` | verde |
| RF‑02 | `tests/integration/test_auditoria_7_de_7.py::test_detecta_las_siete_inconsistencias`; `tests/unit/test_budget.py::test_elaborar_siempre_devuelve_informe`; `tests/integration/test_presupuesto_linea_base.py::test_guardar_persiste_renglones_curva_y_hallazgos`; la recarga declara los pendientes del documento emitido (C3, INV‑080): `tests/integration/test_recarga_con_pendientes.py::test_la_recarga_devuelve_el_informe_emitido_con_sus_pendientes` y, por HTTP, `tests/integration/test_api.py::test_el_informe_recargado_declara_el_pendiente`, `::test_el_excel_recargado_declara_el_pendiente_en_la_auditoria`; la recarga declara también los `ATIPICO` de una versión revalorada (C6, INV‑099): `tests/integration/test_atipicos_en_informe.py::test_los_atipicos_entran_al_informe_se_guardan_y_se_recargan`; el informe importado se recarga igual (INV‑076): `tests/integration/test_importacion_tercero.py::test_guardar_y_recargar_da_el_mismo_informe` | verde; residuo en bases guardadas antes de `04ca90d` (dictamen C3‑3, [manual técnico](manual_tecnico.md)) |
| RF‑03 | `tests/unit/test_contracts.py::TestItemComputo::test_origen_obligatorio`, `::TestItemComputo::test_regla_obligatoria_si_origen_es_regla`, `::TestItemComputo::test_regla_con_parametros_queda_congelada`; `tests/unit/test_reglas_civil.py::test_los_items_son_trazables`; `tests/integration/test_auditoria_7_de_7.py::test_todo_hallazgo_de_partida_referencia_un_origen_trazable` | verde |
| RF‑04 | `tests/unit/test_arquitectura.py::test_un_adaptador_solo_importa_contratos_su_paquete_y_sus_terceros`, `::test_toda_carpeta_de_adapters_tiene_su_regla`; `tests/unit/test_adapter_civil_ifc.py::test_g1_lo_extraido_coincide_con_el_calculo_manual` (`origen_id` = GlobalId); `tests/unit/test_adapter_telecom.py::test_origen_id_es_la_clave_de_fila` | verde, con la salvedad de G1 (§3) |
| RF‑05 | `tests/integration/test_persistencia.py::test_composicion_reconstruye_cada_apu_identico`, `::test_seed_carga_cinco_partidas_y_una_lista` | verde |
| RF‑06 | `tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61`, `::test_cada_renglon_reproduce_el_total_auditado`; `tests/integration/test_presupuesto_linea_base.py::test_elaborar_desde_el_catalogo_reproduce_1586_61`, `::test_los_renglones_referencian_la_partida_del_catalogo` | verde |
| RF‑07 | `tests/unit/test_budget.py::test_curva_cierra_exactamente_en_el_total`, `::test_curva_con_fracciones_arbitrarias_cierra`; `tests/integration/test_composicion_extremo_a_extremo.py::test_la_curva_del_caso_de_demostracion_cierra_en_el_total`; con el plan del proyectista (UC‑01 6, INV‑087): `tests/integration/test_api_plan_y_rendimiento.py::test_el_plan_del_proyectista_reparte_los_periodos_por_http`, `tests/unit/test_ui_elaborar_plan_y_rendimiento.py::test_el_plan_del_proyectista_reparte_los_periodos` | verde |
| RF‑08 | `tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas`; `tests/unit/test_elaboracion.py::test_el_libro_se_abre_y_tiene_la_hoja_de_auditoria` | verde |
| RF‑09 | `tests/unit/test_arquitectura.py` (todo el archivo); `tests/unit/test_adapter_telecom.py::test_extrae_nodos_y_enlaces_de_la_muestra`; `tests/unit/test_adapter_industrial.py::test_extrae_los_activos_de_la_muestra`; `tests/unit/test_adapter_sistemas.py::test_extrae_los_casos_de_uso_de_la_muestra`; `git diff --stat core/` vacío tras I5 y la guardia `scripts/guardia_nucleo.py` en cada corrida de CI | verde (indicador 4) |
| RF‑10 | `tests/integration/test_actualizacion_precios.py::test_leer_lista_precios_devuelve_decimales_exactos`, `::test_leer_lista_precios_xlsx_lee_decimales_exactos`, `::test_leer_lista_precios_rechaza_lo_que_no_es_un_numero_no_negativo`, `::test_actualizar_precios_solo_revalora_el_concreto`, `::test_una_fila_con_unidad_no_equivalente_se_rechaza_y_las_demas_se_procesan` | verde |
| RF‑11 | `tests/integration/test_actualizacion_precios.py::test_uc02_no_edita_ninguna_composicion`, `::test_actualizar_precios_solo_revalora_el_concreto` | verde |
| RF‑12 | `tests/integration/test_actualizacion_precios.py::test_registra_un_cambio_de_precio_por_insumo_afectado`, `::test_registra_la_incidencia_de_cada_cambio_en_el_concreto`, `::test_los_cambios_de_precio_se_releen_tras_cerrar_la_sesion` | verde |
| RF‑13 | `tests/integration/test_actualizacion_precios.py::test_el_comparativo_suma_los_totales`, `::test_el_comparativo_detalla_la_partida_que_cambio` | verde |
| RF‑14 | `tests/integration/test_persistencia.py::test_precios_se_reconstruyen_a_fecha`; `tests/integration/test_actualizacion_precios.py::test_el_presupuesto_anterior_sigue_reconstruyendose_a_su_fecha` | verde |
| RF‑15 | `tests/unit/test_normalizacion.py::test_propuestas_ordenadas_por_puntaje_y_sobre_el_umbral`, `::test_cuantos_acota_el_numero_de_propuestas` | verde |
| RF‑16 | la precarga (desglose, rendimiento, partida de origen y puntaje) de `ui/paginas/similares.py`: `tests/unit/test_ui_similares_uc03.py::test_desplegar_una_propuesta_precarga_su_desglose_rendimiento_origen_y_puntaje`, `::test_un_insumo_sin_precio_vigente_senala_el_desglose_incompleto` (INV‑091, C5); la persistencia de la partida nueva con esa referencia no existe (decisión D5 del tutor, pendiente) | parcial (INV‑027: estado único): la persistencia de la referencia no existe |
| RF‑17 | `tests/unit/test_normalizacion.py::test_acepta_al_menos_80_por_ciento_del_presupuesto_conocido` | verde |
| RF‑18 | `tests/unit/test_reglas_civil.py::test_concreto_por_tanquilla_es_0_224`, `::test_encofrado_por_tanquilla_es_4_48`, `::test_los_items_son_trazables` | verde |
| RF‑19 | `tests/unit/test_reglas_civil.py::test_cambiar_el_ancho_altera_solo_las_cantidades_que_dependen_de_el`; `tests/unit/test_recalculo_uc04.py::test_uc04_recalcula_precios_curva_y_auditoria_al_cambiar_el_ancho`; flujos 1a, 2a y 2b de UC‑04 en §8.1 | verde |
| RF‑20 | — (ninguna prueba: el requisito no tiene implementación; INV‑011) | no implementado; declarado en limitaciones |
| RF‑21 | `tests/unit/test_verification.py`, una o más pruebas por regla: `::test_r1_encofrado_y_concreto_con_impacto`, `::test_r2_brecha_11_11`, `::test_r3_reporta_unidad_original_mts`, `::test_r4_marca_3_4_pulg_y_no_marca_pvc`, `::test_r5_relleno_vs_balance`, `::test_r6_vehiculo_0_03_vs_1_00`, `::test_r7_dia_a_dia`; lista vacía cuando cumple: R5 y R7, `::test_r5_no_reporta_nada_si_el_balance_se_cumple`, `::test_r7_concilia_una_curva_con_corchetes`; R1 y R3, `tests/integration/test_presupuesto_sistemas.py::test_la_auditoria_no_reporta_errores_r1_acepta_ifpug_y_r3_acepta_pf`; R1, `tests/integration/test_presupuesto_industrial.py::test_la_auditoria_no_reporta_errores_y_r1_acepta_la_regla_de_intervenciones`, `tests/integration/test_auditoria_arenaza.py::test_el_presupuesto_1_no_tiene_el_hallazgo_80_90`; R6, `tests/integration/test_composicion_r6.py::test_mismo_factor_de_la_referencia_r6_no_emite_hallazgo`; R2 y R4 (INV‑092, C5), `tests/unit/test_verification.py::test_r2_devuelve_lista_vacia_si_la_curva_cierra`, `::test_r4_devuelve_lista_vacia_si_el_apu_reconoce_las_especificaciones`; las siete a la vez, sobre un presupuesto con cero hallazgos (§8.1, UC‑05 5a): `::test_un_presupuesto_sin_hallazgos_emite_el_informe_con_las_siete_reglas`; sin ERROR ni CRITICO en el presupuesto corregido: `tests/integration/test_auditoria_7_de_7.py::test_el_presupuesto_corregido_no_tiene_errores` | verde (INV‑092, C5) |
| RF‑22 | `tests/integration/test_auditoria_7_de_7.py::test_detecta_las_siete_inconsistencias`: **7 de 7**, uno por regla | verde (indicador 1) |
| RF‑23 | `tests/unit/test_verification.py::test_el_informe_ordena_los_hallazgos_por_severidad_descendente`, `::test_r1_reporta_la_regla_que_no_puede_evaluar`, `::test_r5_reporta_un_balance_que_no_puede_evaluar` (INFO sin abortar); presupuesto idéntico antes y después: `tests/integration/test_auditoria_arenaza.py::test_la_auditoria_corre_sobre_el_presupuesto_telecom_completo` | verde |
| RF‑24 | la unidad «mts» del autor del archivo importado llega intacta a R3 (INV‑076, C6): `tests/integration/test_importacion_tercero.py::test_la_importacion_audita_siete_de_siete_con_la_unidad_del_autor`, `::test_la_lectura_reproduce_partidas_unidades_apu_y_curva`; por `POST /presupuestos/importar` y `GET …/informe`: `tests/integration/test_api_c6.py::test_importar_audita_siete_de_siete_y_persiste_informe_y_libro`; sobre un `Presupuesto` construido en memoria: `tests/unit/test_verification.py::test_r3_reporta_unidad_original_mts` | verde (C6) |
| RF‑25 | `tests/unit/test_contracts.py::TestRendimiento::test_medido_exige_referencia`; `tests/integration/test_rendimientos.py::test_registrar_medido_sin_referencia_se_rechaza`, `::test_registrar_medido_traza_la_ejecucion`, `::test_referencia_de_ejecucion_inexistente_se_rechaza`; `tests/integration/test_api_rendimientos.py::test_medido_sin_referencia_es_422_y_con_referencia_real_queda_trazado` | verde |
| RF‑26 | `tests/integration/test_rendimientos.py::test_dispersion_exacta_y_con_tipos_contados`, `::test_propuesta_prefiere_el_medido_mas_reciente`, `::test_propuesta_sin_medidos_cae_al_estimado_mas_reciente`; `tests/integration/test_api_rendimientos.py::test_get_trae_historico_dispersion_y_propuesta`; la misma propuesta al elaborar (UC‑01 3b, INV‑088): `tests/integration/test_api_plan_y_rendimiento.py::test_sin_rendimiento_vigente_responde_409_con_la_propuesta_y_no_guarda`, `tests/unit/test_ui_elaborar_plan_y_rendimiento.py::test_sin_rendimiento_vigente_se_propone_el_del_historico_con_su_dispersion` | verde |
| RF‑27 | `tests/unit/test_anomalias.py::test_rendimiento_desviado_es_atipico_pero_el_veredicto_no_prohibe`, `::test_rendimiento_coherente_con_lo_observado_no_es_atipico`, `::test_historico_insuficiente_no_da_veredicto`; `tests/integration/test_rendimientos.py::test_advertencia_cuando_el_valor_se_aparta_del_rango_observado`; `tests/integration/test_api_rendimientos.py::test_advertencia_fuera_del_rango_observado_sin_impedir_el_registro` | verde |
| RF‑28 | `tests/unit/test_prediccion.py::test_tecnica_para_es_la_tabla_de_la_compuerta_g2`, `::test_metricas_exactas_mape_rmse_r2`, `::test_prediccion_por_reglas_con_rango_de_sensibilidad`; `tests/unit/test_resultados_ml.py::test_el_informe_declara_conteo_tecnica_y_metricas`; la CI regenera [resultados_ml.md](resultados_ml.md) sin diferencias (§7) | verde (G2: reglas; indicador 5) |
| RF‑29 | `tests/unit/test_prediccion.py::test_contraste_aace_fuera_del_rango_es_hallazgo_advertencia`, `::test_contraste_aace_dentro_del_rango_no_produce_hallazgo`; `tests/unit/test_anomalias.py::test_la_variacion_extrema_es_atipica_y_tiene_el_peor_puntaje`, `::test_los_atipicos_salen_ordenados_del_mas_anomalo_al_menos`; los atípicos de la lista nueva entran al informe de la versión revalorada (UC‑07 5, C6): `tests/integration/test_atipicos_en_informe.py::test_con_el_detector_real_el_cemento_sale_atipico` | verde |
| RF‑30 | `tests/unit/test_escenarios.py::test_escenario_de_parametros_recalcula_cada_partida_contra_el_motor`, `::test_escenario_de_precios_sube_solo_las_partidas_afectadas`, `::test_el_presupuesto_base_y_las_composiciones_quedan_intactos`; `tests/integration/test_api_escenarios.py::test_los_escenarios_no_persisten_ninguna_version`, `::test_parametro_fuera_de_rango_se_rechaza_por_el_contrato`; con un base que tiene ítems pendientes, la respuesta los declara en `pendientes_base` y ningún escenario los suma (INV‑083): `::test_los_escenarios_de_un_base_con_pendientes_los_declaran` | verde |
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

**Resumen:** de los 42 RF, **40 en verde**, **1 parcial** (RF‑16, esencial: la persistencia de la
referencia espera la decisión D5 del tutor) y **1 no implementado** (RF‑20, deseable, en
limitaciones). Ningún RF esencial queda sin ninguna prueba. Desde C5, RF‑21 está completo (la lista
vacía de R2 y R4 y el presupuesto sin hallazgos tienen prueba, INV‑092) y la precarga de RF‑16 tiene
prueba de pantalla (INV‑091); lo que le falta a RF‑16 es solo la persistencia. Desde C6, RF‑24 está
en verde: la importación del archivo de un tercero existe (INV‑076).

**RF en verde con pasos que el sistema no realiza.** Desde C6 queda uno: RF‑30, al que la matriz
traza UC‑08 4a (promover un escenario a presupuesto), que no existe como acción por la decisión D6
del dossier, pendiente del tutor; este párrafo no lo nombraba antes de C6. UC‑01 2a, parcial,
traza a RF‑04, pero el paso sí se realiza: lo que le falta es la prueba del mensaje de la
pantalla. La lista tuvo a RF‑07 y
RF‑26 hasta C5, en que el proyectista pasó a distribuir los períodos (UC‑01 6, INV‑087) y la
elaboración a proponer el rendimiento del histórico (UC‑01 3b, INV‑088), y a RF‑27 y RF‑29 hasta
C6, en que la justificación de la advertencia se registra (UC‑06 4a, INV‑093) y los atípicos entran
al informe de la versión revalorada (UC‑07 5, INV‑099, con el alcance vigente de la
[ERS §2.2](ERS.md#22-funciones-del-producto-casos-de-uso)).

Las demás pruebas de la suite no demuestran un RF concreto: guardias de arquitectura y de la base de
trabajo, metas de sprint, scripts, referencias de precios, dominios del sprint multidominio, API
(OpenAPI y errores HTTP) y visor 3D. Su recuento es el de la sección 10.

### 8.0 Filas del sprint final (SF): RF‑44 a RF‑63

Fuente: [spec SF §11.2](especificaciones/2026-10-04-sprint-final-prototipo-design.md) y
[§4.2](especificaciones/2026-10-04-sprint-final-prototipo-design.md) (criterios de aceptación). Las
filas se abrieron en SF0 sin pruebas; tras la revisión final cada una cita las pruebas reales
(`archivo::función`, verificadas con `grep`) y su estado es **verde** o **parcial** (la celda dice qué
parte no tiene prueba). El **commit de la prueba iba antes que el de la implementación, con el rojo
observado** (NORMAS principio 5; spec §11.2). Estas filas **no entran en el resumen de §8** (que cuenta
los 42 RF vigentes) ni en el recuento de §10. Las pruebas se comparan con las **memorias de cálculo a
mano** (`tests/fixtures/memorias/bano_of001.md`, antes de SF1; `of001.md`, antes de SF2), no con la
expresión de R1, que sería circular.

| RF | Prueba(s) que lo demuestran | Estado |
|---|---|---|
| RF‑44 | referencia obligatoria por tipo de origen: `tests/unit/test_espacio_origen.py::test_cada_tipo_con_su_referencia_completa_es_valido`, `tests/unit/test_espacio_origen.py::test_falta_un_dato_de_la_referencia_el_origen_se_acepta_y_queda_incompleto`; negativo, la fila se acepta y R8 la marca ERROR: `tests/unit/test_espacio_reglas.py::test_r8_fila_sin_origen_de_medida_es_error`, `tests/unit/test_espacio_reglas.py::test_r8_origen_sin_su_referencia_obligatoria_es_error`, `tests/integration/test_espacio_reglas.py::test_fila_sin_origen_de_medida_de_la_hoja_a_la_recarga_extremo_a_extremo`; en la hoja: `tests/unit/test_hoja.py::test_una_fila_con_origen_vacio_pasa_al_borrador_y_el_estado_la_marca_error` | parcial: no editable en la hoja (circuitos, sobrescrituras de segmento y orden de la cadena solo se declaran al importar un plano o por la API); limitación vigente |
| RF‑45 | `tests/unit/test_espacio_geometria.py::test_recorrido_propuesto_de_cada_punto_del_oraculo`, `tests/unit/test_espacio_geometria.py::test_tramos_de_prefiere_el_declarado_y_si_no_propone`, `tests/unit/test_espacio_geometria.py::test_punto_sin_fuente_no_tiene_recorrido`; longitudes del baño de OF‑001 = memoria: `tests/unit/test_espacio_geometria.py::test_claves_y_longitudes_de_los_seis_segmentos`; `tests/unit/test_memoria_bano_of001.py` | verde |
| RF‑46 | `tests/unit/test_espacio_geometria.py::test_solape_total_une_dos_recorridos_identicos`, `tests/unit/test_espacio_geometria.py::test_solape_parcial_parte_el_segmento_mas_largo`, `tests/unit/test_espacio_geometria.py::test_tres_solapes_parciales_colineales`, `tests/unit/test_espacio_geometria.py::test_la_tuberia_compartida_no_se_cuenta_dos_veces`, `tests/unit/test_hoja_borrador.py::test_fr3_dos_recorridos_con_un_tramo_parcial_colineal_no_cuentan_la_tuberia_dos_veces` | parcial: no editable en la hoja (circuitos, sobrescrituras de segmento y orden de la cadena solo se declaran al importar un plano o por la API); limitación vigente |
| RF‑47 | `tests/unit/test_espacio_agua.py::test_agua_fria_del_bano_iguala_la_memoria`, `tests/unit/test_espacio_agua.py::test_drenaje_del_bano_iguala_la_memoria`, `tests/unit/test_espacio_agua.py::test_cantidades_decimal_exactas`; `tests/unit/test_memoria_bano_drenaje_of001.py` | verde |
| RF‑48 | `tests/unit/test_espacio_datos.py::test_datos_de_of001_igualan_la_memoria`, `tests/unit/test_espacio_datos.py::test_cantidades_decimal_exactas`, `tests/unit/test_espacio_datos.py::test_longitud_del_enlace_es_recorrido_mas_holguras`; `tests/unit/test_memoria_of001.py` | verde |
| RF‑49 | `tests/unit/test_espacio_electricidad.py::test_electricidad_de_of001_iguala_la_memoria`, `tests/unit/test_espacio_circuitos.py::test_sin_orden_lo_propone_el_vecino_mas_cercano`, `tests/unit/test_espacio_circuitos.py::test_el_orden_declarado_manda`, `tests/unit/test_espacio_circuitos.py::test_la_cadena_de_cada_circuito_iguala_la_memoria` | parcial: no editable en la hoja (circuitos, sobrescrituras de segmento y orden de la cadena solo se declaran al importar un plano o por la API); limitación vigente |
| RF‑50 | `tests/unit/test_planos_dxf_of001.py` (`tests/unit/test_planos_dxf_of001.py::test_el_dxf_da_las_mismas_cantidades_derivadas_que_la_hoja_manual`, `tests/unit/test_planos_dxf_of001.py::test_reimportar_un_dxf_al_que_le_falta_una_entidad_la_marca`, `tests/unit/test_planos_dxf_of001.py::test_la_altura_de_los_seis_ambientes_queda_pendiente_y_r8_la_marca`); sin `$INSUNITS` se detiene y lo fuera de convención va al informe (`tests/unit/test_planos_dxf.py`); tope de 20 MB y de entidades: `tests/unit/test_planos_dxf.py::test_el_tope_por_defecto_es_una_constante_con_nombre`, `tests/unit/test_planos_dxf.py::test_un_dxf_con_mas_entidades_que_el_tope_se_rechaza_sin_traza`; flujo en la hoja: `tests/unit/test_hoja_planos.py`, `tests/unit/test_ui_hoja_planos.py`; aceptación: `tests/integration/test_aceptacion_sf.py::test_las_cantidades_por_el_plano_son_las_de_la_hoja_manual_a_una_milesima` | verde |
| RF‑51 | `tests/unit/test_planos_ifc.py` (`tests/unit/test_planos_ifc.py::test_los_ambientes_salen_de_los_espacios_con_su_caja_y_su_altura`, `tests/unit/test_planos_ifc.py::test_lo_que_el_ifc_no_declara_queda_pendiente_y_no_se_adivina`, `tests/unit/test_planos_ifc.py::test_el_drenaje_de_un_aparato_sanitario_no_se_infiere`, `tests/unit/test_planos_ifc.py::test_reimportar_el_ifc_editado_actualiza_agrega_y_marca_lo_que_desaparecio`, `tests/unit/test_planos_ifc.py::test_un_archivo_malformado_se_rechaza_con_mensaje_y_sin_traza`); informe: `tests/unit/test_planos_informe.py`; la salvedad de RNF‑09 (IFC programático) se hereda | verde, con alcance acotado: el IFC no trae fuentes ni circuitos y no infiere drenaje (RS‑19) |
| RF‑52 | `tests/integration/test_hoja_versiones.py::test_abrir_la_version_de_la_hoja_recarga_su_espacio_y_el_total_de_la_memoria`, `tests/unit/test_hoja_borrador.py::test_escribir_una_cantidad_cambia_el_total_en_delta_por_el_pu`, `tests/unit/test_ui_hoja.py::test_cambiar_el_fcas_recalcula_y_deja_cambios_sin_guardar`, `tests/unit/test_ui_hoja.py::test_la_pantalla_abre_la_version_vigente_del_proyecto_elegido` | verde |
| RF‑53 | `tests/integration/test_edicion_versiones.py::test_guardar_sin_fuente_o_sin_responsable_se_rechaza_y_no_deja_filas`, `tests/integration/test_edicion_versiones.py::test_la_version_anterior_sigue_cargando_identica`, `tests/integration/test_hoja_versiones.py::test_guardar_sin_fuente_o_sin_responsable_se_rechaza_y_no_deja_filas`, `tests/unit/test_ui_hoja.py::test_guardar_exige_fuente_y_responsable_y_luego_crea_la_version`, `tests/integration/test_instantanea_composiciones.py::test_guardar_congela_las_composiciones_tal_como_se_escribieron` | verde, con alcance acotado: una fuente y un responsable por guardado, no por celda (H‑2) |
| RF‑54 | `tests/integration/test_edicion_versiones.py::test_restaurar_crea_una_version_copia_de_n_y_n_sigue_existiendo`, `tests/integration/test_edicion_versiones.py::test_restaurar_exige_fuente_y_responsable`, `tests/integration/test_hoja_versiones.py::test_restaurar_crea_una_copia_nueva_vigente_y_hereda_el_espacio`, `tests/unit/test_ui_hoja.py::test_restaurar_desde_trazabilidad_crea_una_copia_y_la_deja_vigente` | verde |
| RF‑55 | `tests/unit/test_hoja.py::test_el_estado_marca_solo_la_fila_sembrada`, `tests/unit/test_hoja.py::test_el_estado_agrupa_las_advertencias_de_una_fila_en_un_solo_texto`, `tests/unit/test_ui_hoja.py::test_el_estado_va_fuera_de_los_editores` | verde |
| RF‑56 | `tests/integration/test_cotizacion_proyecto.py::test_la_cotizacion_cambia_solo_ese_insumo_y_solo_en_ese_proyecto`, `tests/integration/test_cotizacion_proyecto.py::test_la_version_resultante_conserva_el_plan_y_la_curva`, `tests/integration/test_cotizacion_proyecto.py::test_una_carga_global_posterior_por_uc02_no_pisa_la_cotizacion`, `tests/integration/test_cotizacion_proyecto.py::test_el_origen_de_cada_precio_muestra_lista_referencia_fecha_moneda_tasa_y_cotizacion`, `tests/integration/test_cotizacion_proyecto.py::test_una_cotizacion_incompleta_o_sin_efecto_se_rechaza_sin_dejar_filas`, `tests/unit/test_ui_hoja.py::test_cotizar_desde_la_pestana_precios_crea_la_version_y_conserva_el_plan`, `tests/unit/test_ui_hoja.py::test_una_cotizacion_sin_proveedor_se_rechaza_con_mensaje_y_no_guarda` | verde |
| RF‑57 | `tests/unit/test_hoja_borrador.py::test_cambiar_el_fcas_recalcula_todos_los_apu_de_la_version`, `tests/integration/test_edicion_versiones.py::test_editar_el_fcas_se_guarda_se_registra_y_la_version_recarga_con_los_pu_a_mano`, `tests/integration/test_hoja_versiones.py::test_el_fcas_de_ti001_recalcula_y_queda_en_el_registro` | verde |
| RF‑58 | `tests/unit/test_equilibrio.py::test_ti001_da_los_literales_de_la_bitacora_del_caso`, `tests/unit/test_equilibrio.py::test_margen_cero_o_negativo_no_tiene_punto_de_equilibrio`, `tests/unit/test_equilibrio.py::test_pe_mayor_que_las_ventas_no_se_alcanza_dentro_del_contrato`, `tests/unit/test_equilibrio.py::test_sin_curva_hay_pe_sin_ubicacion`, `tests/integration/test_hoja_versiones.py::test_abrir_ti001_da_el_total_y_el_punto_de_equilibrio_del_caso`, `tests/unit/test_ui_hoja.py::test_ti001_abre_con_su_plan_y_su_punto_de_equilibrio` | verde |
| RF‑59 | `tests/unit/test_excel_hoja.py::test_cada_formula_de_la_linea_base_coincide_con_el_sistema`, `tests/unit/test_excel_hoja.py::test_cada_formula_de_ti001_coincide_con_el_sistema`, `tests/unit/test_excel_hoja.py::test_cada_formula_con_destajo_equipo_y_parametros_propios_coincide`, `tests/integration/test_hoja_versiones.py::test_el_excel_de_la_hoja_se_reabre_y_sus_formulas_dan_el_total_del_sistema`, `tests/integration/test_aceptacion_sf.py::test_el_excel_evaluado_coincide_con_el_sistema_a_cinco_milesimas` | verde |
| RF‑60 | `tests/unit/test_ui_app.py::test_la_aplicacion_declara_la_navegacion_arriba_con_los_dos_grupos`, `tests/unit/test_ui_app.py::test_modo_entrega_declara_solo_el_grupo_trabajo_en_la_navegacion_superior`, `tests/unit/test_ui_app.py::test_el_boton_de_la_barra_lleva_a_la_pantalla_con_ir_a`, `tests/unit/test_ui_app.py::test_el_modo_entrega_mantiene_importar_plano_y_guardar_y_oculta_investigacion`, `tests/unit/test_ui_barra.py`, `tests/unit/test_ui_barra_con_la_hoja.py` | verde |
| RF‑61 | `tests/unit/test_espacio_r10.py::test_el_enlace_de_90_00_pasa_y_el_de_90_01_falla`, `tests/unit/test_espacio_r10.py::test_el_maximo_de_puntos_pasa_y_uno_mas_falla`, `tests/unit/test_espacio_r10.py::test_la_pendiente_minima_pasa_y_una_menos_falla`, `tests/unit/test_espacio_r10.py::test_con_fuente_verificada_las_tres_condiciones_son_error`, `tests/unit/test_espacio_r10.py::test_of001_con_cada_condicion_sembrada_da_exactamente_ese_hallazgo`; R9 por condición: `tests/unit/test_espacio_reglas.py::test_r9_recorrido_un_milimetro_mas_corto_es_error`, `tests/unit/test_espacio_reglas.py::test_r9_fuente_en_el_borde_mas_tolerancia_no_es_error`; severidad de R8: `tests/unit/test_espacio_reglas.py::test_r8_supuesto_en_cada_tipo_de_fila_es_advertencia`, `tests/unit/test_espacio_reglas.py::test_r8_fila_sin_origen_de_medida_es_error`; conjunto exacto: `tests/unit/test_espacio_reglas.py::test_of001_bano_limpio_conjunto_exacto_de_hallazgos` | verde, con alcance acotado: R10 no propone pendiente y sus tres límites son supuestos que bajan a ADVERTENCIA (RS‑11) |
| RF‑62 | `tests/integration/test_espacio_reglas.py::test_el_informe_del_bano_incluye_r8_y_sobrevive_a_la_recarga`, `tests/integration/test_edicion_versiones.py::test_restaurar_conserva_el_hallazgo_externo_y_el_informe_recargado_es_identico`, `tests/integration/test_cotizacion_proyecto.py::test_cotizar_y_retirar_conservan_el_hallazgo_externo_y_el_informe_recargado_es_identico`, `tests/integration/test_reglas_externas.py::test_la_recarga_devuelve_el_informe_emitido`, `tests/integration/test_reglas_externas.py::test_revalorar_arrastra_los_externos_y_no_los_atipicos_viejos`, `tests/integration/test_reglas_externas.py::test_importar_con_reglas_extra_recarga_el_mismo_informe` | verde |
| RF‑63 | `tests/unit/test_ui_proyectos.py::test_nombre_vacio_se_rechaza_con_mensaje`, `tests/unit/test_ui_proyectos.py::test_nombre_repetido_se_rechaza_aunque_cambien_espacios_o_mayusculas`, `tests/unit/test_ui_barra.py::test_proyecto_nuevo_con_nombre_vacio_se_rechaza_con_mensaje`, `tests/unit/test_ui_barra.py::test_proyecto_nuevo_con_nombre_repetido_se_rechaza_con_mensaje` | verde |
| A‑2 (hallazgo) | caso directo (3/4" en memoria, 4" en el APU, `docs/linea_base.md`) y los cuatro pares de la bitácora de TI‑001: `tests/unit/test_r4_especificaciones_normalizadas.py::test_caso_directo_la_descripcion_del_item_no_confirma_su_especificacion`, `tests/unit/test_r4_especificaciones_normalizadas.py::test_r4_marca_el_valor_declarado_contenido_en_el_del_apu`, `tests/unit/test_r4_especificaciones_normalizadas.py::test_r4_marca_el_par_en_el_sentido_inverso`; regresión: `tests/unit/test_verification.py::test_r4_marca_3_4_pulg_y_no_marca_pvc` | verde |
| Arquitectura | importaciones de `adapters.espacio`, `ui.hoja` y `ui.barra` en `test_arquitectura.py`: `tests/unit/test_arquitectura.py::test_un_adaptador_solo_importa_contratos_su_paquete_y_sus_terceros`, `tests/unit/test_arquitectura.py::test_ui_respeta_sus_importaciones_prohibidas`, `tests/unit/test_arquitectura.py::test_solo_ui_app_importa_la_barra_de_herramientas` | verde |

**Regresión en cada compuerta del SF:** los cinco APU de la línea base a ± 0,01; 7 de 7 y
`test_r4_marca_3_4_pulg_y_no_marca_pvc` sin modificarse; total de TI‑001 (50 503,27 USD); las dos
huellas de RNF‑04 (informe y contenido del `.xlsx`); las cuatro hojas de `exportar_excel`. **OF‑001
limpio** no da «cero hallazgos»: da el conjunto exacto esperado (regla, severidad y fila), porque las
constantes declaradas como supuesto producen ADVERTENCIAS de R8 y R10.

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
| 1 crea el proyecto y selecciona fuente y dominio | RF‑04 | la fuente y el dominio: `tests/integration/test_api.py::test_computo_civil_desde_la_muestra`, `::test_computo_civil_desde_un_modelo_ifc` (`POST /computos/{dominio}`); crear el proyecto (INV‑086, C6), en el núcleo: `tests/integration/test_proyectos.py::test_crear_el_proyecto_y_guardar_sobre_el`, `::test_dominio_opcional`, `::test_nombre_repetido_o_vacio_o_dominio_desconocido`; por `POST /proyectos`, y luego elaborar sobre él: `tests/integration/test_api_c6.py::test_crear_proyecto_y_elaborar_sobre_el`, `::test_crear_proyecto_sin_dominio_ni_descripcion`, `::test_un_proyecto_invalido_es_422_sin_crear_nada`, `::test_el_proyecto_y_el_presupuesto_importado_quedan_confirmados` | verde (C6); la interfaz no crea proyectos: solo la API |
| 2 extrae los `ItemComputo` con su origen | RF‑03, RF‑04 | `tests/unit/test_reglas_civil.py::test_adaptador_tabular_extrae_la_muestra`; `tests/unit/test_adapter_civil_ifc.py::test_g1_lo_extraido_coincide_con_el_calculo_manual`; `tests/unit/test_adapter_telecom.py::test_extrae_nodos_y_enlaces_de_la_muestra`; `tests/unit/test_adapter_industrial.py::test_extrae_los_activos_de_la_muestra`; `tests/unit/test_adapter_sistemas.py::test_extrae_los_casos_de_uso_de_la_muestra` | verde |
| 3 asocia cada ítem a su partida y recupera composición y rendimiento | RF‑05, RF‑06 | `tests/integration/test_persistencia.py::test_composicion_reconstruye_cada_apu_identico`; `tests/integration/test_presupuesto_linea_base.py::test_los_renglones_referencian_la_partida_del_catalogo` | verde |
| 4 el motor calcula cada `ResultadoAPU` | RF‑01 | `tests/unit/test_costing.py::test_precio_unitario_reproduce_la_linea_base` | verde |
| 5 arma el `Presupuesto` con totales | RF‑06 | `tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61`, `::test_cada_renglon_reproduce_el_total_auditado`; `tests/integration/test_presupuesto_linea_base.py::test_elaborar_desde_el_catalogo_reproduce_1586_61`; `tests/integration/test_api.py::test_elaborar_presupuesto_por_http_reproduce_el_total_auditado` | verde |
| 6 el proyectista distribuye en períodos; la curva cierra en el total | RF‑07 | la curva cierra: `tests/unit/test_budget.py::test_curva_cierra_exactamente_en_el_total`, `::test_curva_con_fracciones_arbitrarias_cierra`, `::test_elaborar_acepta_el_plan_como_funcion_del_presupuesto_valorado`; el proyectista distribuye (INV‑087, C5), en la tabla «Plan de trabajo» de la pantalla: `tests/unit/test_ui_elaborar_plan_y_rendimiento.py::test_el_plan_del_proyectista_reparte_los_periodos`, `::test_por_defecto_el_plan_es_una_partida_por_dia`, `::test_un_plan_que_no_reparte_toda_partida_se_rechaza_y_conserva_el_presupuesto`, `::test_una_fila_del_plan_malformada_se_rechaza_en_la_pagina`, `::test_las_filas_del_plan_se_agrupan_por_periodo_y_una_a_medias_se_rechaza`, `::test_volver_a_elaborar_avisa_que_el_plan_vuelve_al_secuencial`; y en el campo `plan` de `POST /presupuestos`: `tests/integration/test_api_plan_y_rendimiento.py::test_el_plan_del_proyectista_reparte_los_periodos_por_http`, `::test_sin_plan_la_curva_es_una_partida_por_dia`, `::test_un_plan_que_no_reparte_toda_partida_responde_422_sin_guardar`, `::test_una_fraccion_que_no_es_decimal_responde_422` | verde; sin plan del proyectista, `plan_secuencial` (una partida por día) sigue siendo el valor por defecto |
| 7 verifica y emite el informe sin que se pida | RF‑02 | `tests/unit/test_budget.py::test_elaborar_siempre_devuelve_informe`; `tests/unit/test_ui_elaborar.py::test_el_item_sin_partida_queda_pendiente_con_sus_propuestas` (el informe en la pantalla) (CP‑06) | verde |
| 8 exporta presupuesto y curva a XLSX | RF‑08 | `tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas`; `tests/unit/test_elaboracion.py::test_el_libro_se_abre_y_tiene_la_hoja_de_auditoria`; `tests/unit/test_ui_componer.py::test_de_componer_a_excel_desde_la_pantalla` (CP‑05) | verde |
| 2a fuente ilegible o de otro dominio | RF‑04 | fuentes malformadas en dos adaptadores: `tests/unit/test_adapter_telecom.py::test_longitud_vacia_falla_con_fila_y_columna` (un CSV de telecom con una longitud vacía falla nombrando la fila y la columna); `tests/unit/test_reglas_civil.py::test_adaptador_tabular_exige_una_zanja_para_el_balance_de_relleno`, `::test_adaptador_tabular_rechaza_dos_zanjas_de_diametros_distintos` (el CSV civil sin zanja, o con dos diámetros, se rechaza); `tests/unit/test_adapter_civil_ifc.py::test_dos_cantidades_del_mismo_tipo_ifc_son_ambiguas` (un IFC ambiguo falla con el GlobalId). Desde C5 (INV‑089), en los cuatro adaptadores, cada rechazo con el nombre del archivo (sin su ruta) y la fila o el elemento: `tests/unit/test_fuentes_ilegibles.py::test_un_ifc_que_no_es_step_se_rechaza_nombrando_el_archivo`, `::test_un_step_que_ifcopenshell_no_abre_se_rechaza_con_archivo_y_motivo`, `::test_rechazar_estos_ifc_no_deja_excepciones_no_atrapables`, `::test_un_elemento_ifc_que_falla_nombra_el_archivo_y_no_su_ruta`, `::test_industrial_una_frecuencia_mal_formada_falla_con_archivo_fila_y_columna`, `::test_sistemas_un_conteo_mal_formado_falla_con_archivo_fila_y_columna`, `::test_civil_una_medida_vacia_falla_con_archivo_fila_y_columna`, `::test_civil_una_fila_corta_falla_con_archivo_y_fila`, `::test_telecom_una_celda_mal_formada_nombra_archivo_fila_y_columna`, `::test_telecom_una_fila_corta_se_identifica_por_su_linea_y_no_por_none`, `::test_la_muestra_de_otro_dominio_se_rechaza_nombrando_archivo_y_dominio`, `::test_un_archivo_binario_se_rechaza_nombrando_el_archivo`; la respuesta 422 de `POST /computos/{dominio}`: `tests/integration/test_api_fuentes_ilegibles.py::test_un_ifc_corrupto_responde_422_con_el_archivo`, `::test_un_step_de_esquema_no_soportado_responde_422_sin_la_ruta_del_servidor`, `::test_una_celda_industrial_mal_formada_responde_422_con_archivo_y_fila`, `::test_la_muestra_de_telecom_en_sistemas_responde_422_y_no_404`, `::test_la_muestra_de_telecom_en_civil_responde_422_sin_la_ruta_del_servidor`, `::test_un_binario_en_telecom_responde_422_con_el_archivo`. Sin prueba: el mensaje de la página «Elaborar un presupuesto» (`ui/paginas/elaborar.py::_extraer`, que pinta con `st.error` el mismo `ValueError`). Límite declarado: un `.ifc` con cabecera STEP válida y cuerpo truncado o con basura lo abre `ifcopenshell` sin error y da un cómputo vacío (o con los elementos que alcanzó a leer), sin rechazo (docstring de `adapters/civil/ifc.py::_abrir_modelo`; INV‑103) | parcial: el mensaje de la pantalla no tiene prueba, y un IFC con cabecera válida y cuerpo dañado no se rechaza (INV‑103, limitaciones) |
| 3a ítem sin partida: pendiente, propuestas y reelaboración (orden de C3‑10) | RF‑02, RF‑15 | `tests/unit/test_budget.py::test_un_item_sin_partida_queda_pendiente_y_el_informe_lo_declara`; `tests/unit/test_ui_elaborar.py::test_el_item_sin_partida_queda_pendiente_con_sus_propuestas`, `::test_aceptar_una_propuesta_vuelve_a_elaborar_sin_pendientes`, `::test_aceptar_cambia_solo_el_item_pendiente`, `::test_sin_el_extra_el_pendiente_se_declara_sin_propuestas`; `tests/integration/test_api.py::test_un_item_sin_partida_queda_pendiente_por_http`, `::test_si_todos_los_items_quedan_pendientes_el_presupuesto_sale_vacio_y_no_cumple` | verde |
| 3b partida sin rendimiento vigente: propone el del histórico | RF‑26 | desde C5 (INV‑088), en el bloque «Rendimientos por declarar» de la pantalla: `tests/unit/test_ui_elaborar_plan_y_rendimiento.py::test_sin_rendimiento_vigente_se_propone_el_del_historico_con_su_dispersion`, `::test_sin_declarar_el_tipo_no_se_registra_nada`, `::test_declarado_medido_no_se_usa_tal_cual_y_no_se_registra`, `::test_declarado_estimado_se_registra_y_se_vuelve_a_elaborar`, `::test_con_dos_partidas_el_tipo_de_la_segunda_no_se_presume`, `::test_sin_ningun_historico_no_hay_propuesta_y_se_remite_a_componer`; lo que no es 3b sigue con su mensaje: `::test_sin_lista_vigente_se_muestra_su_error_y_no_se_ofrece_3b`, `::test_un_insumo_sin_precio_muestra_su_error_y_no_se_ofrece_3b`; por HTTP, el 409 con la propuesta y el reenvío: `tests/integration/test_api_plan_y_rendimiento.py::test_sin_rendimiento_vigente_responde_409_con_la_propuesta_y_no_guarda`, `::test_declarado_el_estimado_propuesto_la_elaboracion_reproduce_la_linea_base`, `::test_sin_ningun_historico_la_propuesta_es_null`, `::test_sin_lista_vigente_el_409_no_propone_rendimientos_y_no_guarda`, `::test_un_insumo_sin_precio_responde_el_409_de_siempre` | verde, con el alcance vigente de la [ERS §2.2](ERS.md#22-funciones-del-producto-casos-de-uso) (UC‑01 3b): declarado «medido», el rendimiento no se registra ni desbloquea la elaboración, y la propuesta sale de todo el histórico, sin atarla a la fecha del presupuesto |
| 6a sin plan de trabajo: sin curva, R2 no aplicable | RF‑07 | `tests/unit/test_budget.py::test_elaborar_siempre_devuelve_informe` (sin plan, `curva == ()`); `tests/unit/test_verification.py::test_r2_informa_cuando_no_hay_curva`, `::test_r7_se_declara_no_aplicable_si_el_presupuesto_no_declara_curva` | verde en el núcleo; la interfaz y la API siempre pasan un plan (sin el del proyectista, `plan_secuencial`; un `plan` vacío en `POST /presupuestos` responde 422: `tests/integration/test_api_plan_y_rendimiento.py::test_un_plan_vacio_responde_422_sin_guardar`), así que por ellas el flujo no ocurre |
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
| 2a insumos desconocidos: se listan y se ofrecen dar de alta o ignorar | RF‑10 | se listan y se ignoran: `tests/integration/test_actualizacion_precios.py::test_crear_lista_reporta_los_insumos_desconocidos_sin_crearlos`; `tests/integration/test_api.py::test_cargar_lista_de_precios_reporta_desconocidos_vacios`; el alta por selección (INV‑090, C6), en el núcleo: `tests/integration/test_alta_desconocidos.py::test_la_vista_previa_lista_los_desconocidos_sin_crear_nada`, `::test_el_elegido_se_da_de_alta_con_precio_solo_en_la_lista_nueva`, `::test_sin_eleccion_nada_se_da_de_alta`, `::test_revalorar_con_alta_da_el_incremento_calculado_sin_ella`, `::test_elegir_un_casado_o_un_rechazado_se_rechaza_sin_escribir`, `::test_equipo_y_mano_de_obra_se_dan_de_alta_sin_unidad_y_un_apu_los_reutiliza`, `::test_un_desconocido_repetido_se_da_de_alta_una_sola_vez`, `::test_un_desconocido_repetido_con_precios_distintos_se_rechaza`, `::test_la_guardia_del_alta_usa_la_identidad_del_catalogo`; en «Actualizar precios»: `tests/unit/test_ui_actualizacion_alta.py::test_al_subir_la_lista_ofrece_dar_de_alta_solo_los_desconocidos_del_flujo_2a`, `::test_revalorar_sin_elegir_ignora_los_desconocidos_y_rechaza_los_de_otra_unidad`, `::test_revalorar_con_el_elegido_lo_da_de_alta_con_precio_solo_en_la_lista_nueva`, `::test_filas_repetidas_con_precios_distintos_son_un_error_sin_escribir`, `::test_un_archivo_mal_formado_no_ofrece_nada_y_el_error_sale_al_revalorar`, `::test_con_un_caso_inexistente_la_vista_previa_no_crea_la_base`; por `POST /listas-precios` (campo `dar_de_alta`): `tests/integration/test_api_c6.py::test_dar_de_alta_crea_solo_el_elegido_y_separa_ignorados_de_rechazados`, `::test_sin_dar_de_alta_nada_se_crea_y_los_desconocidos_se_reportan_aparte`, `::test_un_alta_invalida_es_422_sin_escribir_nada`, `::test_elegir_una_grafia_da_de_alta_la_identidad_con_el_precio_de_sus_filas`, `::test_un_xlsx_ilegible_al_cargar_la_lista_es_422_sin_escribir_nada` | verde (C6); por la API no hay vista previa, y dos homónimos de material con distinta unidad se pueden dar de alta juntos (límites declarados en la ERS, UC‑02 2a) |
| 2b unidad no equivalente: la fila se rechaza y las demás siguen | RF‑10 | `tests/integration/test_actualizacion_precios.py::test_una_fila_con_unidad_no_equivalente_se_rechaza_y_las_demas_se_procesan`; desde C6 se reporta aparte de los ignorados de 2a y no se ofrece para el alta: `tests/unit/test_ui_actualizacion_alta.py::test_revalorar_sin_elegir_ignora_los_desconocidos_y_rechaza_los_de_otra_unidad`; `tests/integration/test_api_c6.py::test_dar_de_alta_crea_solo_el_elegido_y_separa_ignorados_de_rechazados`; `tests/integration/test_alta_desconocidos.py::test_elegir_un_casado_o_un_rechazado_se_rechaza_sin_escribir` | verde |
| 3a ningún precio cambió: no hay versión nueva | RF‑11 | `tests/unit/test_ui_actualizacion.py::test_revalorar_sin_cambios_no_guarda_ni_ofrece_descartar`; `tests/integration/test_api.py::test_actualizacion_sin_cambios_de_precio_responde_409_sin_persistir`; desde C6, en la pantalla las altas elegidas tampoco se guardan: `tests/unit/test_ui_actualizacion_alta.py::test_sin_cambios_de_precio_las_altas_tampoco_se_guardan` | verde |
| 4a el base tiene ítems pendientes (UC‑01 3a) | RF‑02 | `tests/integration/test_recarga_con_pendientes.py::test_revalorar_arrastra_los_pendientes_del_base` | verde |
| 7a descarta la versión: se marca y el historial se conserva | RF‑12 | `tests/integration/test_actualizacion_precios.py::test_descartar_la_version_nueva_la_marca_y_conserva_el_historial`, `::test_con_tres_versiones_solo_se_descarta_la_ultima`, `::test_el_presupuesto_base_nunca_se_descarta`, `::test_una_version_no_se_descarta_dos_veces`; `tests/unit/test_ui_actualizacion.py::test_descartar_version_marca_la_version_y_conserva_el_historial`, `::test_descartar_marca_la_base_donde_se_guardo_aunque_se_cambie_de_caso` | verde |

#### UC‑03 — Reutilizar partidas y desgloses de proyectos anteriores

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 escribe la descripción en texto libre | RF‑15 | `tests/unit/test_normalizacion.py::test_descripcion_identica_es_la_primera_propuesta_con_puntaje_cercano_a_uno`; en la página «Partidas similares», con un doble del modelo que comprueba que recibe la descripción tecleada y el catálogo (INV‑091, C5): `tests/unit/test_ui_similares_uc03.py::test_desplegar_una_propuesta_precarga_su_desglose_rendimiento_origen_y_puntaje`; la degradación sin el extra: `tests/unit/test_ui_similares.py::test_sin_el_extra_la_pagina_lo_dice` | verde; ninguna prueba de pantalla recorre la página con el modelo real en el camino de éxito (el ranking real lo prueban `ml/` y la API, paso 2) |
| 2 devuelve las tres más similares con su puntaje | RF‑15 | `tests/unit/test_normalizacion.py::test_propuestas_ordenadas_por_puntaje_y_sobre_el_umbral`, `::test_cuantos_acota_el_numero_de_propuestas`; `tests/integration/test_api.py::test_la_propuesta_real_reconoce_la_partida_de_la_misma_descripcion` | verde |
| 3 el proyectista selecciona una | RF‑16 | en UC‑01 3a: `tests/unit/test_ui_elaborar.py::test_aceptar_una_propuesta_vuelve_a_elaborar_sin_pendientes`; en la página «Partidas similares» la selección es desplegar la propuesta, que no tiene estado en el servidor: `tests/unit/test_ui_similares_uc03.py::test_desplegar_una_propuesta_precarga_su_desglose_rendimiento_origen_y_puntaje` comprueba que cada propuesta seleccionable trae su contenido (INV‑091, C5) | verde, con nota: `AppTest` pinta el contenido de todo desplegable, así que la prueba no ejerce la interacción de desplegar (P‑5 de la pista P de C5) |
| 4 precarga composición y rendimiento con origen y puntaje | RF‑16 | `tests/unit/test_ui_similares_uc03.py::test_desplegar_una_propuesta_precarga_su_desglose_rendimiento_origen_y_puntaje` (título, pie con la partida de origen y el puntaje, unidad y rendimiento, y las tablas del desglose; oráculo: la línea base) (INV‑091, C5) | verde; la persistencia de la referencia es la parte parcial de RF‑16 (§8) |
| 5 ajusta y el sistema recalcula | RF‑16 | la página «Partidas similares» es de solo lectura; el ajuste y el recálculo en vivo ocurren en «Componer una partida» (UC‑10, paso 6) | no implementado en UC‑03 |
| 2a ningún candidato supera el umbral | RF‑15 | `tests/unit/test_normalizacion.py::test_nada_supera_el_umbral_no_propone_nada` | verde |
| 2b catálogo vacío | RF‑15 | `tests/unit/test_normalizacion.py::test_catalogo_vacio_no_propone_sin_error` | verde |
| 4a el desglose usa insumos sin precio vigente | RF‑16 | `tests/unit/test_ui_similares_uc03.py::test_un_insumo_sin_precio_vigente_senala_el_desglose_incompleto` (sin el precio del cemento, la propuesta del concreto avisa nombrando el insumo y la partida y no muestra tablas; la de la excavación sí las muestra) (INV‑091, C5) | verde |

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
| 1 selecciona el presupuesto o importa el archivo del tercero | RF‑24 | seleccionar uno propio: `tests/integration/test_api.py::test_el_informe_recargado_declara_el_pendiente` (`GET /presupuestos/{codigo}/informe`); importar el archivo de un tercero (INV‑076, C6), en el núcleo: `tests/integration/test_importacion_tercero.py::test_la_importacion_audita_siete_de_siete_con_la_unidad_del_autor`, `::test_guardar_y_recargar_da_el_mismo_informe`, `::test_un_codigo_que_ya_esta_en_el_catalogo_se_rechaza_sin_escribir`, `::test_un_presupuesto_repetido_en_el_proyecto_se_rechaza_sin_escribir`, `::test_una_moneda_distinta_de_la_lista_vigente_se_rechaza_sin_escribir`, `::test_sin_lista_vigente_la_importada_lleva_solo_los_precios_del_tercero`, `::test_un_archivo_mal_formado_se_rechaza_con_archivo_hoja_y_fila`, `::test_un_archivo_que_no_es_un_libro_se_rechaza`, `::test_el_formato_es_el_del_plan`; por `POST /presupuestos/importar`: `tests/integration/test_api_c6.py::test_importar_audita_siete_de_siete_y_persiste_informe_y_libro`, `::test_importar_sobre_un_proyecto_inexistente_es_404`, `::test_un_archivo_que_no_se_puede_importar_es_422_sin_escribir_nada`, `::test_si_la_importacion_falla_despues_de_escribir_la_ruta_no_deja_nada`, `::test_importar_dos_veces_el_mismo_codigo_es_422`, `::test_importar_un_archivo_que_no_es_xlsx_es_422`, `::test_importar_se_declara_antes_de_las_rutas_con_codigo`, `::test_el_proyecto_y_el_presupuesto_importado_quedan_confirmados` | verde (C6); la importación es solo por la API, sin pantalla (ruling C6‑3) |
| 2 construye el `Presupuesto` conservando las unidades del autor | RF‑24 | `tests/unit/test_verification.py::test_r3_reporta_unidad_original_mts`, sobre el presupuesto de prueba construido en memoria (`tests/fixtures/presupuesto_auditado.py`); desde el archivo de un tercero (INV‑076, C6): `tests/integration/test_importacion_tercero.py::test_la_lectura_reproduce_partidas_unidades_apu_y_curva` («mts» en `especificaciones[CLAVE_UNIDAD_ORIGINAL]` y el total exacto de la línea base), `::test_la_importacion_audita_siete_de_siete_con_la_unidad_del_autor` (R3 cita «mts»), `::test_una_linea_a_destajo_se_importa_y_se_valora_a_destajo`; por HTTP, `tests/integration/test_api_c6.py::test_importar_audita_siete_de_siete_y_persiste_informe_y_libro`. Por la vía de las cantidades tecleadas en «Componer una partida» el ítem toma la unidad de la partida, así que R3 no se dispara por esa vía (dictamen C3‑47) | verde (C6); el presupuesto importado se valora con el motor sobre los APU del archivo, no con los precios unitarios del autor (ERS, UC‑05 2) |
| 3 ejecuta R1–R7 | RF‑21, RF‑22 | `tests/integration/test_auditoria_7_de_7.py::test_detecta_las_siete_inconsistencias`; el informe declara las reglas que corrió, con su cuenta (INV‑092, C5): `tests/unit/test_verification.py::test_el_informe_enumera_las_reglas_evaluadas_con_su_cuenta_de_hallazgos`, `::test_el_informe_enumera_solo_las_reglas_que_corrieron` | verde |
| 4 cada hallazgo con severidad, descripción, impacto y `origen_id` | RF‑21 | `tests/integration/test_auditoria_7_de_7.py::test_todo_hallazgo_de_partida_referencia_un_origen_trazable`; `tests/unit/test_verification.py::test_r1_encofrado_y_concreto_con_impacto`; `tests/unit/test_contracts.py::TestVerificacion::test_hallazgo_exige_regla_y_descripcion`; la columna *Partida* del informe, que declara la regla que emite el hallazgo (INV‑095, C5): `tests/unit/test_verification.py::test_el_informe_atribuye_la_muestra_civil_a_la_partida_de_cada_hallazgo`, `::test_el_hallazgo_de_un_objeto_con_dos_partidas_va_a_la_partida_que_lo_produjo`, `::test_una_regla_que_no_declara_su_partida_no_se_atribuye_a_un_origen_compartido`, `::test_un_hallazgo_declarado_para_dos_partidas_no_se_atribuye_a_ninguna`, `::test_r4_sobre_un_objeto_compartido_se_atribuye_a_la_partida_de_la_especificacion`, `::test_r5_sobre_un_origen_compartido_se_atribuye_a_la_partida_del_balance`, `::test_r7_atribuye_la_conciliacion_y_la_partida_sin_periodo_de_un_objeto_compartido`, `::test_r7_atribuye_la_conciliacion_de_varias_partidas_a_la_primera_del_presupuesto` | verde |
| 5 ordena por severidad y emite el informe | RF‑23 | `tests/unit/test_verification.py::test_el_informe_ordena_los_hallazgos_por_severidad_descendente`, `::test_informe_markdown_contiene_resumen_y_partidas` (CP‑06) | verde |
| 6 exporta el informe | RF‑02 | `tests/unit/test_elaboracion.py::test_el_libro_se_abre_y_tiene_la_hoja_de_auditoria`; `tests/integration/test_api.py::test_el_excel_recargado_declara_el_pendiente_en_la_auditoria`; la hoja *Auditoria* enumera las reglas evaluadas en las columnas G a I (INV‑092, C5): `tests/unit/test_budget.py::test_la_hoja_de_auditoria_enumera_las_reglas_evaluadas` | verde |
| 2a sin plan de trabajo: R2 y R7 no aplicables | RF‑23 | `tests/unit/test_verification.py::test_r2_informa_cuando_no_hay_curva`, `::test_r7_se_declara_no_aplicable_si_el_presupuesto_no_declara_curva`; un archivo de un tercero sin la hoja `Curva` (C6): `tests/integration/test_importacion_tercero.py::test_sin_curva_r2_y_r7_no_aplican_y_las_demas_reglas_si` | verde |
| 2b cantidades sin regla: R1 declara la trazabilidad ausente | RF‑03, RF‑21 | `tests/unit/test_verification.py::test_r1_advierte_de_las_cantidades_manuales_sin_regla`; sin origen no hay ítem: `tests/unit/test_contracts.py::TestItemComputo::test_origen_obligatorio`; en un archivo de un tercero (C6), el renglón sin regla es `MANUAL` y R1 lo advierte, y el que no trae `origen_id` recibe `<archivo>:Presupuesto:<fila>`: `tests/integration/test_importacion_tercero.py::test_un_item_sin_regla_es_manual_y_r1_lo_advierte`, `::test_sin_origen_id_el_origen_es_archivo_hoja_y_fila` | verde |
| 3a una regla no evaluable: INFO y la ejecución continúa | RF‑23 | `tests/unit/test_verification.py::test_r1_reporta_la_regla_que_no_puede_evaluar`, `::test_r5_reporta_un_balance_que_no_puede_evaluar`, `::test_r4_informa_de_una_especificacion_que_no_puede_contrastar` | verde |
| 5a sin hallazgos: el informe se emite igual y declara las siete reglas evaluadas | RF‑02, RF‑21 | desde C5 (INV‑092), en pantalla (`InformeAuditoria.a_markdown`: la sección «Reglas evaluadas» con las siete en 0 y «Sin hallazgos.»): `tests/unit/test_verification.py::test_un_presupuesto_sin_hallazgos_emite_el_informe_con_las_siete_reglas`; en la hoja *Auditoria* del Excel (columna A solo con el encabezado y las siete reglas en 0 en G a I): `::test_la_hoja_de_auditoria_sin_hallazgos_enumera_las_siete_reglas_en_cero`; la enumeración sobrevive a los pendientes y a la recarga: `tests/unit/test_budget.py::test_la_elaboracion_con_pendientes_conserva_las_reglas_evaluadas_y_la_atribucion`, `tests/integration/test_recarga_con_pendientes.py::test_la_recarga_con_pendientes_enumera_las_reglas_evaluadas` | verde |

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
| 4a acepta la advertencia: su justificación queda junto al APU | RF‑27 | la tabla y su registro (INV‑093, C6), en el núcleo: `tests/integration/test_justificacion_rendimiento.py::test_la_justificacion_queda_ligada_al_ultimo_rendimiento`, `::test_texto_o_advertencia_vacios_se_rechazan`, `::test_un_rendimiento_ya_justificado_se_rechaza`, `::test_partida_sin_rendimientos_o_inexistente`, `::test_una_base_anterior_gana_la_tabla_y_conserva_sus_filas`, `::test_borrar_el_rendimiento_borra_su_justificacion`; en «Componer una partida»: `tests/unit/test_ui_componer_justificacion.py::test_con_advertencia_la_justificacion_se_liga_al_rendimiento_que_registra_el_guardado`, `::test_sin_advertencia_no_hay_campo_ni_justificacion`, `::test_con_advertencia_y_sin_texto_guarda_sin_justificacion`, `::test_si_el_guardado_no_registra_rendimiento_no_justifica_el_ultimo_y_avisa`, `::test_el_aviso_de_ml_no_hace_aparecer_el_campo_de_justificacion`; por `POST /partidas/{codigo}/rendimientos` (campo `justificacion`): `tests/integration/test_api_c6.py::test_la_justificacion_con_advertencia_queda_ligada_al_rendimiento_registrado`, `::test_cada_peticion_justifica_su_propio_rendimiento`, `::test_la_justificacion_sin_advertencia_se_ignora_y_el_registro_se_hace`, `::test_una_justificacion_en_blanco_es_422_sin_registrar_nada`, `::test_sin_justificacion_la_respuesta_la_trae_nula` | verde (C6), ligada al rendimiento que registra el guardado o la petición, no a la composición (ERS, UC‑06 4a); ninguna ruta ni pantalla la lee después |

#### UC‑07 — Contrastar el precio construido con el precio de mercado

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| 1 selecciona una partida o un presupuesto | RF‑28 | una partida, al componerla: `tests/unit/test_composicion_ia.py::test_contrastar_precio_con_reglas_ofrece_el_marco_aace_cuando_hay_hallazgo` (CP‑02, paso 2); los presupuestos de todos los dominios, por `scripts/generar_resultados_ml.py`: `tests/unit/test_resultados_ml.py::test_el_informe_tabula_las_predicciones_con_su_rango` | verde; elegir un presupuesto concreto no tiene pantalla ni ruta |
| 2 determina la técnica por el conteo | RF‑28 | `tests/unit/test_prediccion.py::test_tecnica_para_es_la_tabla_de_la_compuerta_g2`; `tests/unit/test_resultados_ml.py::test_el_informe_declara_conteo_tecnica_y_metricas` | verde |
| 3 estima y reporta MAPE, RMSE y R² | RF‑28 | `tests/unit/test_prediccion.py::test_metricas_exactas_mape_rmse_r2`, `::test_prediccion_por_reglas_con_rango_de_sensibilidad` | verde |
| 4 contrasta y expresa la desviación en porcentaje | RF‑29 | `tests/unit/test_prediccion.py::test_contraste_aace_fuera_del_rango_es_hallazgo_advertencia`, `::test_contraste_aace_presenta_a_dos_decimales_con_redondeo_hacia_arriba` | verde |
| 5 marca los atípicos y los incorpora al informe de auditoría | RF‑29 | se marcan: `tests/unit/test_anomalias.py::test_los_atipicos_salen_ordenados_del_mas_anomalo_al_menos`; se tabulan en `docs/resultados_ml.md`; entran al informe de la versión revalorada (INV‑099, C6), en el núcleo: `tests/integration/test_atipicos_en_informe.py::test_los_atipicos_entran_al_informe_se_guardan_y_se_recargan`, `::test_sin_detector_el_informe_es_la_auditoria_del_presupuesto`, `::test_las_marcas_ajenas_a_la_lista_o_al_presupuesto_no_dan_hallazgo`, `::test_repetir_la_revaloracion_no_duplica_el_historial`, `::test_con_el_detector_real_el_cemento_sale_atipico`; en «Actualizar precios»: `tests/unit/test_ui_actualizacion_alta.py::test_el_informe_revalorado_muestra_los_precios_atipicos`, `::test_sin_detector_el_informe_no_trae_atipicos`, `::test_el_detector_es_el_de_ml_y_sin_el_extra_no_hay`, `::test_sin_sklearn_no_hay_detector_y_la_revaloracion_no_se_aborta`; por `POST /presupuestos/{codigo}/actualizacion` y `GET …/informe`: `tests/integration/test_api_c6.py::test_la_revaloracion_trae_los_atipicos_de_ml_al_informe`, `::test_sin_sklearn_la_revaloracion_con_historico_suficiente_sigue_sin_atipicos` | verde, con el alcance vigente de la [ERS §2.2](ERS.md#22-funciones-del-producto-casos-de-uso) (UC‑07 5): solo en el informe de la versión revalorada; sin el extra `ml` o con menos de 8 variaciones no se marca ninguno y el informe no lo dice |
| 2a menos de 50 registros: reglas con sensibilidad, como limitación | RF‑28 | `tests/unit/test_prediccion.py::test_tecnica_para_es_la_tabla_de_la_compuerta_g2`, `::test_prediccion_por_reglas_con_rango_de_sensibilidad`; `tests/unit/test_resultados_ml.py::test_con_un_dominio_en_el_umbral_el_informe_no_afirma_que_todos_estan_por_debajo` | verde |
| 3a partida sin análogas: no se estima y se informa | RF‑28 | desde C5 (INV‑094), para una partida nueva la ayuda 4 de «Componer una partida» no estima y la pantalla informa que el contraste no es posible (`ui/paginas/componer.py::_contraste_aace`); una partida guardada no lleva el aviso: `tests/unit/test_ui_componer_contraste.py::test_una_partida_nueva_informa_que_el_contraste_no_es_posible`. El sistema detecta 3a como «partida sin PU anterior» (la estimación por reglas parte de él), no busca análogas (U‑8 de la revisión de la pista U de C5). Otra condición, vecina: con un histórico de variaciones del dominio vacío, la predicción por reglas es el precio base sin rango (`tests/unit/test_prediccion.py::test_sin_historico_de_variaciones_la_prediccion_es_el_precio_base`) | verde |
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
| base con ítems pendientes (UC‑01 3a; INV‑083) (no es un flujo de la ERS) | RF‑30 | la página los declara: `tests/unit/test_ui_escenarios.py::test_el_escenario_de_un_base_con_pendientes_los_declara`; la API, en `pendientes_base`: `tests/integration/test_api_escenarios.py::test_los_escenarios_de_un_base_con_pendientes_los_declaran`; el informe del propio escenario no los lista (dictamen C4‑3, a limitaciones) | parcial |

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
| 2 modifica insumos, cantidades, precios o modalidad | RF‑34 | la cantidad, por la pantalla: `tests/unit/test_ui_componer.py::test_editar_una_cantidad_y_guardar_reemplaza_la_composicion`; la cantidad, el precio y la modalidad sobre la partida existente `DEMO-01-INST` (INV‑091, C5): `::test_editar_cantidad_precio_y_modalidad_recalcula_el_desglose_en_vivo`; agregar o quitar insumos recorren las mismas tablas de UC‑10 (pasos 2 a 4, RF‑34), probadas sobre una partida nueva | verde; agregar o quitar un insumo, por el camino de UC‑10 |
| 3 declara un rendimiento nuevo con sus condiciones | RF‑33 | `tests/integration/test_persistencia.py::test_reemplazar_composicion_propaga_las_condiciones_al_rendimiento`; `tests/unit/test_ui_componer.py::test_guardar_dos_veces_edita_la_partida` | verde |
| 4 recalcula en vivo sobre la composición modificada | RF‑01 | `tests/unit/test_ui_componer.py::test_editar_cantidad_precio_y_modalidad_recalcula_el_desglose_en_vivo` (tras cada una de tres ediciones sucesivas, las métricas son las de la composición del catálogo editada con `dataclasses.replace` y costeada por el motor; el rubro editado y el precio unitario se mueven; nada se guarda) (INV‑091, C5) (CP‑02 paso 2 y CP‑03) | verde |
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

#### UC‑13 a UC‑16 — casos de uso del sprint final

Fuente: [spec SF §4.1](especificaciones/2026-10-04-sprint-final-prototipo-design.md); los UC se
escriben completos en la ERS en SF0 y esta tabla sigue sus flujos alternos. Las filas
se abrieron como «planeado (SFn)» y ya citan sus pruebas con el estado de §8.1 (misma regla que §8.0:
no entran en el «Resumen de la matriz por paso», que sigue siendo el de los once casos de uso de C4).
Un paso sin prueba ni caso manual es un requisito sin verificar (regla de §8.1).

| Paso | RF | Prueba o caso | Estado |
|---|---|---|---|
| UC‑13 1 el proyectista levanta ambientes, fuentes, puntos y recorridos en la hoja | RF‑44, RF‑45 | `tests/unit/test_hoja.py::test_las_filas_del_editor_reconstruyen_el_mismo_espacio`, `tests/unit/test_hoja.py::test_los_vertices_declarados_se_editan_como_tramos`, `tests/unit/test_ui_hoja.py::test_el_bano_sembrado_muestra_cantidades_derivadas_y_el_informe`; manual: CP‑08 del guion | parcial: no editable en la hoja (circuitos, sobrescrituras de segmento y orden de la cadena solo se declaran al importar un plano o por la API) |
| UC‑13 2 el sistema une segmentos, cuenta accesorios y deriva los `ItemComputo` | RF‑46, RF‑47, RF‑48, RF‑49 | `tests/unit/test_espacio_agua.py::test_agua_fria_del_bano_iguala_la_memoria`, `tests/unit/test_espacio_datos.py::test_datos_de_of001_igualan_la_memoria`, `tests/unit/test_espacio_electricidad.py::test_electricidad_de_of001_iguala_la_memoria`, `tests/unit/test_hoja.py::test_los_items_del_borrador_son_los_de_la_memoria`, `tests/integration/test_aceptacion_sf.py::test_la_hoja_manual_de_of001_da_el_total_de_la_memoria` | verde |
| UC‑13 3 elabora y audita con las siete reglas más R8 a R10 | RF‑61, RF‑62 | `tests/unit/test_hoja.py::test_el_presupuesto_del_bano_es_el_de_la_memoria_y_cumple_las_siete_reglas`, `tests/unit/test_hoja.py::test_las_reglas_del_espacio_se_pasan_a_elaborar_con_la_instantanea`, `tests/integration/test_hoja_versiones.py::test_el_conjunto_exacto_de_hallazgos_de_la_hoja_abierta_es_el_de_of001`, `tests/integration/test_espacio_reglas.py::test_el_informe_del_bano_incluye_r8_y_sobrevive_a_la_recarga` | verde |
| UC‑13a fila sin origen de medida: se acepta en la versión y R8 la marca ERROR | RF‑44, RF‑61 | `tests/unit/test_espacio_reglas.py::test_r8_fila_sin_origen_de_medida_es_error`, `tests/integration/test_espacio_reglas.py::test_fila_sin_origen_de_medida_de_la_hoja_a_la_recarga_extremo_a_extremo`, `tests/unit/test_hoja.py::test_una_fila_con_origen_vacio_pasa_al_borrador_y_el_estado_la_marca_error` | verde |
| UC‑13b punto fuera de su ambiente: R9 | RF‑61 | `tests/unit/test_espacio_reglas.py::test_r9_fuente_fuera_de_su_ambiente`, `tests/unit/test_espacio_reglas.py::test_r9_fuente_en_el_borde_mas_tolerancia_no_es_error` | verde |
| UC‑14 1 elige un plano (DXF o IFC) | RF‑50, RF‑51 | `tests/unit/test_hoja_planos.py::test_leer_el_dxf_de_of001_devuelve_la_importacion_con_su_informe`, `tests/unit/test_hoja_planos.py::test_el_formato_se_deduce_de_la_extension_sin_distinguir_mayusculas`, `tests/unit/test_ui_hoja_planos.py::test_importar_plano_de_la_barra_lleva_a_espacio_y_metrajes_y_abre_el_flujo`; IFC: `tests/unit/test_planos_ifc.py::test_los_ambientes_salen_de_los_espacios_con_su_caja_y_su_altura` | verde |
| UC‑14 2 el sistema vuelca filas a la hoja con un informe de importación (nunca directo al presupuesto, DA‑SF‑6) | RF‑50, RF‑51 | `tests/unit/test_planos_dxf_of001.py::test_la_importacion_da_las_filas_de_la_memoria`, `tests/unit/test_hoja_planos.py::test_fusionar_no_cambia_el_borrador_original_ni_toca_lo_que_no_es_del_espacio`, `tests/unit/test_ui_hoja_planos.py::test_fusionar_pasa_las_filas_al_borrador_sin_saltar_la_hoja` (nunca directo al presupuesto); el informe: `tests/unit/test_planos_informe.py` | verde |
| UC‑14a DXF sin `$INSUNITS`: se detiene y pide la unidad | RF‑50 | `tests/unit/test_hoja_planos.py::test_leer_un_dxf_sin_unidad_se_detiene_y_pide_la_unidad_y_se_reanuda_con_ella`, `tests/unit/test_ui_hoja_planos.py::test_la_importacion_detenida_pide_la_unidad_y_se_reanuda_con_ella` | verde |
| UC‑14b entidades fuera de convención: van al informe, no a la hoja | RF‑50 | `tests/unit/test_planos_dxf_of001.py::test_nada_del_dxf_queda_sin_reconocer`; lo fuera de convención va al informe en `tests/unit/test_planos_dxf.py`; IFC: `tests/unit/test_planos_ifc.py::test_lo_que_no_se_reconoce_va_al_informe_agrupado_por_clase` | verde |
| UC‑14c reimportar el mismo plano: empareja por *handle* o `GlobalId`, actualiza, agrega y marca las que desaparecieron | RF‑50, RF‑51 | `tests/unit/test_planos_informe.py::test_reimportar_el_mismo_plano_no_cambia_nada`, `tests/unit/test_planos_informe.py::test_reimportar_marca_la_fila_desaparecida_y_no_la_borra`, `tests/unit/test_planos_ifc.py::test_reimportar_el_ifc_editado_actualiza_agrega_y_marca_lo_que_desaparecio`, `tests/unit/test_hoja_planos.py::test_reimportar_el_mismo_plano_no_duplica_filas` | verde |
| UC‑14d archivo malformado o mayor de 20 MB: rechazo con mensaje, sin *traceback* | RNF‑12 | `tests/unit/test_planos_ifc.py::test_un_archivo_malformado_se_rechaza_con_mensaje_y_sin_traza`, `tests/unit/test_planos_ifc.py::test_un_archivo_de_mas_de_20_mb_se_rechaza`, `tests/unit/test_hoja_planos.py::test_leer_un_archivo_roto_no_lanza_y_dice_que_no_se_pudo_leer`; DXF: `tests/unit/test_planos_dxf.py` (20 MB y tope de entidades) | verde |
| UC‑15 1 edita celdas de entrada en el borrador; recalcula y audita sin persistir | RF‑52, RF‑55 | `tests/unit/test_hoja_borrador.py::test_escribir_una_cantidad_cambia_el_total_en_delta_por_el_pu`, `tests/unit/test_ui_hoja.py::test_cambiar_el_fcas_recalcula_y_deja_cambios_sin_guardar`, `tests/unit/test_ui_hoja.py::test_el_estado_va_fuera_de_los_editores` | verde |
| UC‑15 2 guarda: versión nueva con informe, instantáneas y un `RegistroCambio` por celda | RF‑53, RF‑57 | `tests/integration/test_hoja_versiones.py::test_guardar_crea_la_version_002_con_su_registro_y_el_espacio_de_la_edicion`, `tests/integration/test_edicion_versiones.py::test_un_registro_por_celda_cambiada`, `tests/integration/test_edicion_versiones.py::test_editar_el_fcas_se_guarda_se_registra_y_la_version_recarga_con_los_pu_a_mano` | verde |
| UC‑15 3 cotiza un insumo; exporta la hoja a Excel | RF‑56, RF‑59 | `tests/integration/test_cotizacion_proyecto.py::test_la_cotizacion_cambia_solo_ese_insumo_y_solo_en_ese_proyecto`, `tests/unit/test_excel_hoja.py::test_cada_formula_de_la_linea_base_coincide_con_el_sistema`, `tests/integration/test_hoja_versiones.py::test_el_excel_de_la_hoja_se_reabre_y_sus_formulas_dan_el_total_del_sistema` | verde |
| UC‑15a guardar sin fuente o responsable: se rechaza | RF‑53 | `tests/integration/test_edicion_versiones.py::test_guardar_sin_fuente_o_sin_responsable_se_rechaza_y_no_deja_filas`, `tests/unit/test_ui_hoja.py::test_guardar_exige_fuente_y_responsable_y_luego_crea_la_version`, `tests/integration/test_aceptacion_sf.py::test_guardar_sin_fuente_se_rechazo_con_el_motivo_y_no_creo_version` | verde |
| UC‑15b plan con una partida que no suma 1: se rechaza (como UC‑01 paso 6) | RF‑52 | `tests/unit/test_hoja_borrador.py::test_el_plan_se_lee_de_filas_y_cada_partida_debe_sumar_uno` | verde |
| UC‑15c salir con ediciones sin guardar: aviso | RF‑52 | `tests/unit/test_ui_hoja.py::test_cambiar_de_version_con_cambios_pide_confirmar_y_no_los_descarta_solo` (AppTest del aviso) | parcial: aviso en pantalla automatizado; el cierre del navegador queda manual (diferido) |
| UC‑15d restaurar una versión anterior | RF‑54 | `tests/integration/test_edicion_versiones.py::test_restaurar_crea_una_version_copia_de_n_y_n_sigue_existiendo`, `tests/integration/test_aceptacion_sf.py::test_restaurar_la_001_crea_la_003_igual_a_ella_y_no_borra_nada` | verde |
| UC‑15e versión sin instantánea (anterior a SF‑E6 o importada por UC‑05): la hoja la crea desde el catálogo vigente y lo registra; partida sin composición en el catálogo: APU en solo lectura | RF‑53 | `tests/integration/test_hoja_versiones.py::test_abrir_la_clinica_no_tiene_espacio_y_da_el_total_de_la_linea_base`, `tests/integration/test_hoja_versiones.py::test_abrir_una_version_sin_instantanea_la_crea_y_deja_el_registro`, `tests/integration/test_hoja_versiones.py::test_ti001_sin_instantanea_se_abre_con_su_plan_inferido`, `tests/integration/test_instantanea_composiciones.py::test_asegurar_instantanea_deja_en_solo_lectura_la_partida_que_el_catalogo_ya_no_reproduce` | verde |
| UC‑16 1 calcula el punto de equilibrio y lo ubica en la curva | RF‑58 | `tests/unit/test_equilibrio.py::test_ti001_da_los_literales_de_la_bitacora_del_caso`, `tests/integration/test_hoja_versiones.py::test_abrir_ti001_da_el_total_y_el_punto_de_equilibrio_del_caso`, `tests/integration/test_aceptacion_sf.py::test_el_punto_de_equilibrio_es_el_de_la_aritmetica_de_la_version` | verde |
| UC‑16a sin plan: PE sin ubicación en la curva | RF‑58 | `tests/unit/test_equilibrio.py::test_sin_curva_hay_pe_sin_ubicacion`, `tests/unit/test_hoja_borrador.py::test_sin_plan_el_punto_de_equilibrio_no_tiene_ubicacion` | verde |
| UC‑16b margen ≤ 0: no existe PE | RF‑58 | `tests/unit/test_equilibrio.py::test_margen_cero_o_negativo_no_tiene_punto_de_equilibrio`, `tests/unit/test_hoja_borrador.py::test_un_margen_no_positivo_es_no_existe_con_su_texto` | verde |
| UC‑16c PE > V: no se alcanza | RF‑58 | `tests/unit/test_equilibrio.py::test_pe_mayor_que_las_ventas_no_se_alcanza_dentro_del_contrato`, `tests/unit/test_equilibrio.py::test_pe_igual_a_las_ventas_si_se_alcanza_en_el_ultimo_periodo` | verde |

#### Resumen de la matriz por paso

Recuento de las filas de esta sección por el estado con que empieza su última celda (una fila
«verde en el núcleo…» cuenta como verde; su celda dice qué capa no lo ejerce). No cuenta la fila
rotulada «(no es un flujo de la ERS)» de UC‑08, que traza INV‑083 (1 fila). Los pasos
parciales, sin prueba o no implementados son hallazgos de esta matriz; la compuerta GC4 los
repartió entre la fase C5, que corrigió los suyos, y las limitaciones.

| UC | Pasos y flujos | Verde | Manual | Parcial | Sin prueba | No implementado |
|---|---|---|---|---|---|---|
| UC‑01 | 13 | 12 | 0 | 1 | 0 | 0 |
| UC‑02 | 12 | 12 | 0 | 0 | 0 | 0 |
| UC‑03 | 8 | 7 | 0 | 0 | 0 | 1 |
| UC‑04 | 8 | 7 | 0 | 0 | 0 | 1 |
| UC‑05 | 10 | 10 | 0 | 0 | 0 | 0 |
| UC‑06 | 8 | 8 | 0 | 0 | 0 | 0 |
| UC‑07 | 8 | 8 | 0 | 0 | 0 | 0 |
| UC‑08 | 7 | 6 | 0 | 0 | 0 | 1 |
| UC‑10 | 12 | 12 | 0 | 0 | 0 | 0 |
| UC‑11 | 8 | 8 | 0 | 0 | 0 | 0 |
| UC‑12 | 10 | 9 | 1 | 0 | 0 | 0 |
| **Total** | **104** | **99** | **1** | **1** | **0** | **3** |

En C5 pasan a verde ocho filas: UC‑01 6 y 3b, UC‑03 3, 4 y 4a, UC‑05 5a, UC‑07 3a y UC‑11 4.
Otras seis ganan pruebas sin cambiar de estado: UC‑01 2a (sigue parcial: le falta la prueba del
mensaje en la pantalla), UC‑03 1, UC‑05 3, 4 y 6 y UC‑11 2. En GC4 el total era 85 verdes,
2 manuales, 9 parciales, 2 sin prueba y 6 no implementados.

En C6 pasan a verde seis filas más: UC‑01 1, UC‑02 2a, UC‑05 1 y 2, UC‑06 4a y UC‑07 5 (esta, con
su alcance vigente). Otras cuatro ganan pruebas sin cambiar de estado, todas en verde: UC‑02 2b y
3a y UC‑05 2a y 2b. En GC5 el total era 93 verdes, 1 manual, 6
parciales, 0 sin prueba y 4 no implementados. El único parcial que queda es UC‑01 2a (el mensaje de
la pantalla no tiene prueba e INV‑103 está en limitaciones); los tres no implementados son UC‑03 5,
UC‑04 5 (RF‑20) y UC‑08 4a (decisión D6).

## 9. Trazabilidad RNF → verificación

| RNF | Cómo se verificó | Resultado |
|---|---|---|
| RNF‑01 exactitud | línea base reproducida exacta (RF‑01, RF‑06): desviación 0,00 % ≪ clase 3 AACE | cumple |
| RNF‑02 reproducibilidad | `test_precios_se_reconstruyen_a_fecha`: reconstrucción idéntica, 100 % | cumple |
| RNF‑03 desempeño | `scripts/medir_rnf03.py` (2026‑08‑31): UC‑02 con **100 partidas y 41 insumos revalorados en 1,17 s** (umbral 5 s) | cumple |
| RNF‑04 usabilidad | juicio de expertos Likert ≥ 4/5, con el protocolo de C4, en la fase Med de [PLAN_CIERRE.md](../PLAN_CIERRE.md) | pendiente (Med) |
| RNF‑05 núcleo cerrado | `git diff --stat core/` vacío tras I5 y tras cada adaptador; `test_arquitectura.py` verde | cumple |
| RNF‑06 cobertura | cobertura de `core/` en la corrida de §10 (meta ≥ 80 %, que la CI exige con `--fail-under=80`) | cumple |
| RNF‑07 portabilidad | `uv sync --locked --all-extras` sin pasos manuales y la suite completa en verde en Linux y en Windows en la corrida de §10 ([36520879630](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36520879630)) | cumple |
| RNF‑08 seguridad | inspección: 0 credenciales versionadas, 0 llamadas de red en operación salvo las dos excepciones que declara la ERS: la descarga inicial del modelo (cacheada) y three.js desde `cdnjs.cloudflare.com` en el Visor 3D (INV‑077) | cumple, con las dos excepciones declaradas |
| RNF‑09 compatibilidad IFC | G1 con salvedad: exacto contra modelo programático; faltan exports de ≥ 2 modeladores | parcial |
| RNF‑10 aprendizaje de la interfaz | caso con persona CP‑07 ([guion_prueba_arenia.md](guion_prueba_arenia.md)), dos escenarios con personas distintas, bloque B del anexo A | pendiente (GU1b, fase Med) |
| RNF‑11 desempeño de la hoja | `scripts/medir_rnf11.py` con el generador determinista de 500 puntos (SF0): desde aplicar una edición hasta tener presupuesto, informe y PE, sin persistir, en `ui.hoja` sin Streamlit; mediana de cinco corridas tras una de calentamiento ≤ 2 s. Veredicto en el equipo de desarrollo (como RNF‑03); la CI registra la cifra en Linux y Windows sin romper la corrida | **cumple en el equipo de desarrollo**: mediana 0,125 s (2026‑10‑05, §10 «Medición de RNF‑11»); la CI solo registra |
| RNF‑12 seguridad de exportes y subidas | una prueba por cada prefijo de fórmula (`=`, `+`, `-`, `@`, tabulador, retorno de carro; un negativo sigue siendo número) y por cada ruta peligrosa (`..\`, `../`, absoluta, nombres reservados de Windows); DXF/IFC de más de 20 MB o malformados se rechazan con mensaje: `tests/unit/test_excel_m1.py::test_exportar_excel_escribe_como_texto_cada_prefijo_peligroso`, `tests/unit/test_excel_m1.py::test_exportar_hoja_escribe_como_texto_cada_prefijo_peligroso`, `tests/unit/test_excel_m1.py::test_un_numero_negativo_legitimo_sigue_siendo_numero_y_un_texto_negativo_sigue_siendo_texto`, `tests/integration/test_hoja_versiones.py::test_un_texto_con_prefijo_de_formula_no_se_exporta_como_formula`, `tests/unit/test_ui_subidas.py::test_nombre_seguro_deja_un_solo_componente_limpio`, `tests/unit/test_ui_subidas.py::test_nombres_reservados_de_windows_se_renombran_y_los_demas_no`, `tests/unit/test_ui_subidas.py::test_guardar_nunca_deja_archivos_fuera_de_la_carpeta`, `tests/unit/test_planos_ifc.py::test_un_archivo_de_mas_de_20_mb_se_rechaza`, `tests/unit/test_planos_ifc.py::test_un_ifc_con_mas_elementos_que_el_tope_se_rechaza_sin_traza`, `tests/unit/test_planos_dxf.py::test_un_dxf_con_mas_entidades_que_el_tope_se_rechaza_sin_traza` | **cumple** (automatizado, SF3–SF5) |
| RNF‑13 usabilidad de la hoja | CP‑08 a CP‑11 del [guion](guion_prueba_arenia.md), con el mismo número y perfil de participantes que CP‑07 pero personas distintas: cada caso sin ayuda en ≤ 15 min por todos, bloque B ≥ 4,0 y ningún ítem < 3; veredicto por caso. Consigna, paradas y criterio se fijan antes de medir | pendiente de la fase de mediciones (guion CP‑08…11 listo; ninguna persona lo ha ejecutado) |

## 10. Registro de la ejecución (CI de la compuerta GC6, 2026‑09‑29)

**Fuente única de las cifras de la suite y de la cobertura** (INV‑031; la CI es la fuente de verdad
de las cifras, [metodologia.md §6](metodologia.md#6-gestión-de-configuración)). Esta sección registra
la corrida de la CI de la compuerta GC6 (PR #17) y, aparte, la corrida local que la precedió. Los
demás documentos enlazan esta sección y no copian sus cifras.

### Última corrida de la CI (GC6, 2026‑09‑29)

La corrida
[36656292394](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36656292394)
del PR #17, sobre el commit `6eb8b84` (compuerta GC6 del cierre). La CI prueba la fusión de ese
commit con la base del PR, `main` en `c47b57e` (el commit de la fusión de GC5).

```
calidad (ruff + guardia del nucleo)  ruff: All checks passed!   guardia del nucleo: PENDIENTE (exit 0)   meta de datos: 3/3 OK
pruebas (ubuntu-latest)   1191 passed in 159.23s  Python 3.13.13  uv 0.11.9   verificar omitidas: 0 omitidas
pruebas (windows-latest)  1191 passed in 287.17s  Python 3.13.15   verificar omitidas: 0 omitidas
```

La guardia del núcleo de la CI (`scripts/guardia_nucleo.py`) responde `PENDIENTE: sin commits que
toquen adapters/ o ml/ desde la base` y sale con código 0: el rango de C6 no toca adaptadores ni `ml/`,
así que no hay rama de adaptador que evaluar. La comprobación de C6 sobre `core/` es la de
`guardia_gc6.sh` (cinco commits autorizados, marcas 0) de la corrida local y de la compuerta GC6 de la
bitácora, no la de la CI.

Distribución de la suite: **1 191 casos**, 0 fallos y 0 omitidos en las dos plataformas. El reparto por
carpeta, 841 en `tests/unit/` y 350 en `tests/integration/`, es el de la recolección local de la
compuerta (la CI no lo imprime). C6 sumó 146 sobre los 1 045 de la CI de GC5.

Cobertura, del trabajo `pruebas (ubuntu-latest)` de esa corrida de la CI (`coverage.py` cuenta
**sentencias**, no líneas; la CI publica el porcentaje entero y el exacto se calcula de sus columnas
`Stmts` y `Miss`):

| Paquete | Sentencias cubiertas | Cobertura publicada | Exacta |
|---|---|---|---|
| `core/` | 2 210 / 2 233 | **99 %** | 98,97 % |
| `ml/` | 173 / 174 | — | 99,43 % |
| `api/` | 599 / 616 | — | 97,24 % |
| `adapters/` | 565 / 609 | — | 92,78 % |
| **Total medido** | 3 547 / 3 632 | **98 %** | 97,66 % |

La CI publica el porcentaje de `core/` en el paso «Cobertura de core >= 80 % (RNF-06)»
(`coverage report --include="core/*" --fail-under=80`, umbral 80 %, superado) y el total en la tabla de
la suite; los de `ml/`, `api/` y `adapters/` son la suma de sus filas en esa misma tabla. `ui/` y
`scripts/` no se miden. El paso «Artefactos reproducibles» regeneró `docs/api.json` y
`docs/resultados_ml.md` sin diferencias.

### Corrida local previa a la CI (compuerta GC6)

Sobre `eb06e96`, el código de C6 con el lote del encargo de QA de GC6, con
`uv run --all-extras pytest -W error --strict-markers -q -p no:cacheprovider --junitxml=<ruta fuera
del árbol>`, en Windows, y las cifras leídas del JUnit:

```
suite completa         1191 tests   0 fallos   0 errores   0 omitidas   357 s   Python 3.13.2
verificar omitidas: 0 omitidas      ruff check .: All checks passed!
metas: meta_prototipo 12/12, meta_redaccion 12/12, meta_datos 3/3
línea base (test_costing, 7 de 7, extremo a extremo, 1 586,61): 27 0 0 0
guardia del núcleo (guardia_gc6.sh 5): 5 commits de core/ con los asuntos autorizados, marcas: 0
```

La CI coincide con ella en el total (1 191) y sustituye sus cifras de cobertura, que la local no medía.

Registros anteriores, que esta sección sustituye: 385 casos en F.2 y 392 y 395 tras el cierre de
UC‑08 (los tres del 2026‑08‑31, locales), 479 en la Sesión M4.1 del sprint multidominio
(2026‑09‑14, local, con `core/` al 98,10 %), 926 en la corrida
[36427904452](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36427904452)
del cierre de C3 (2026‑09‑28, PR #14, commit `308eca5`), 945 en la corrida
[36489551508](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36489551508)
de la compuerta GC4 (2026‑09‑28, PR #15, commit `e7a0569`, con `core/` al 98,37 %), 1 045 en la
corrida de la CI de GC5 (`core/` al 98,53 %) y 1 191 en la corrida local y en la de la CI de GC6. La evaluación de
calidad sobre estos resultados está en [calidad_iso25010.md](calidad_iso25010.md).

### Medición de RNF‑11 (SF3, 2026‑10‑05)

`uv run python scripts/medir_rnf11.py` en el equipo de desarrollo (Windows 11, AMD64 de 16 núcleos,
Python 3.13.2): hoja de **500 puntos** del generador determinista (semilla 0), cada corrida aplica una
edición (cantidad escrita a mano) y llama a `ui.hoja.elaborar_borrador` (valora, ajusta el plan,
audita con R1 a R10, punto de equilibrio y Estado) sin persistir. Una corrida de calentamiento y cinco
medidas: **0,125; 0,135; 0,125; 0,121 y 0,126 s; mediana 0,125 s** frente al umbral de 2 s (cumple, con
un margen de 16 veces). **Alcance de la cifra:** el generador usa 8 partidas sintéticas (un material,
un equipo y una cuadrilla cada una) y ningún espacio: mide el costo de valorar y auditar 500 renglones,
no la derivación espacial (`adapters.espacio`, que la spec de SF2 midió aparte: 500 puntos en un
circuito, derivar 0,431 s). La CI ejecuta el script en Linux y Windows y **solo registra** la cifra (el
paso no rompe la corrida); la meta S9 de `scripts/meta_sf.py` lee `scripts/_salida_rnf11.json`.
