# Retiro de Streamlit, F3: triaje de las funciones sin AppTest de los archivos AppTest

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-retiro-streamlit` · **Fase:** F3 de `docs/planes/PLAN_RETIRO_STREAMLIT.md` (§2.1, §4) · **Autor:** implementador F3.

## 1. Resumen

- Archivos revisados: **45** (los de `tests/unit` que usan `AppTest` o `streamlit`, sin `conftest.py`, `tests/fixtures/paginas_s3.py` ni `test_meta_sf.py`; coinciden con la lista de §2.1 del plan).
- Funciones `test_*` de esos archivos: **524**. Sin `AppTest`/`streamlit` (ni directo ni por ayudante, fixture o importacion de `ui.paginas.*` del mismo archivo): **126** (el plan estimaba 121; la diferencia es del metodo: aqui se cuentan tambien 11 funciones que no usan `AppTest` pero importan una pagina `ui.paginas.*`; sin ellas, 115).
- **MOVIDAS: 50 funciones (64 items)** a 9 archivos `tests/unit/test_aplicacion_*.py` (7 nuevos, 2 ampliados). **RETIRADAS con su modulo: 76 funciones (123 items)**. **Bloqueadas: 0** (ninguna depende de un modulo de `ui/` sin homologo en `aplicacion/` y a la vez prueba logica que sobreviva; las que quedaron sin homologo son de pantallas o modulos que el plan retira).
- Regla `movidos + retirados = items de origen sin AppTest`: **64 + 123 = 187** (50 + 76 = 126 funciones). Las funciones con AppTest (los otros 477 items de los 45 archivos) **no se tocan**: se borran en F4.
- Conteo real con `pytest --collect-only -q` de los 45 archivos: **antes 664 items, despues 600** (−64 = los 64 items movidos). Los 9 destinos suman **87** items, de los cuales 64 son los movidos (los otros 23 eran de `test_aplicacion_entorno.py` y `test_aplicacion_precios_empresa.py` antes). Suite completa del proyecto: no corrida (otros agentes tienen cambios en curso en `operacion/`, `instalador/`).

## 2. Criterio

1. Una funcion es «sin AppTest» si ni ella, ni los ayudantes de modulo o fixtures del mismo archivo que usa, mencionan `AppTest`, `streamlit`/`st`, `altair`, ni importan `tests.fixtures.paginas_s3`.
2. **MOVIDA** si el objeto probado vive en `aplicacion/` (directo o por un puente `ui.*` que solo reexporta). Solo cambia el origen del import. Cuatro grupos (15 funciones) requirieron una adaptacion minima, declarada en la columna de destino: `ui.cliente` (7, la IP se pasa directa a `aplicacion.equipo`), `ui.paginas.acerca` (6, la pagina solo envolvia `aplicacion.acerca.datos_acerca` con la ruta del caso), `ui.paginas.actualizacion` (1, delegaba en `aplicacion.actualizacion.detector_de_atipicos`) y `ui.app.modo_entrega_activo` (1, ya duplicado en `aplicacion.entorno`).
3. **RETIRADA** si prueba `ui/app`, `ui/barra`, `ui/libros`, `ui/existencias`, `ui/recorridos`, una pagina, el codigo fuente de `ui/` o la configuracion de Streamlit: el modulo desaparece en F4 y no tiene homologo en `aplicacion/`.
4. Los originales conservan las funciones retiradas y las de AppTest intactas; de los originales solo se quitaron las funciones ya movidas y verdes en el destino (mas los imports que quedaron sin uso, con `ruff --fix F401`).

## 3. Totales por archivo de origen

| Archivo origen | Items antes | Items sin AppTest | movidos | retirados | AppTest (intactos) | Items despues |
|---|---:|---:|---:|---:|---:|---:|
| `test_config_streamlit.py` | 6 | 6 | 0 | 6 | 0 | 6 |
| `test_ui_acceso.py` | 15 | 1 | 0 | 1 | 14 | 15 |
| `test_ui_acerca.py` | 8 | 6 | 6 | 0 | 2 | 2 |
| `test_ui_actualizacion_alta.py` | 11 | 1 | 1 | 0 | 10 | 10 |
| `test_ui_app.py` | 70 | 14 | 1 | 13 | 56 | 69 |
| `test_ui_barra.py` | 36 | 3 | 0 | 3 | 33 | 36 |
| `test_ui_barra_con_la_hoja.py` | 13 | 1 | 0 | 1 | 12 | 13 |
| `test_ui_cliente.py` | 25 | 19 | 12 | 7 | 6 | 13 |
| `test_ui_elaborar.py` | 13 | 5 | 5 | 0 | 8 | 8 |
| `test_ui_elaborar_plan_y_rendimiento.py` | 15 | 1 | 1 | 0 | 14 | 14 |
| `test_ui_existencias.py` | 16 | 9 | 0 | 9 | 7 | 16 |
| `test_ui_hoja.py` | 55 | 1 | 0 | 1 | 54 | 55 |
| `test_ui_hoja_trabajo.py` | 29 | 12 | 12 | 0 | 17 | 17 |
| `test_ui_informe_seguro.py` | 2 | 1 | 0 | 1 | 1 | 2 |
| `test_ui_instalacion.py` | 14 | 2 | 2 | 0 | 12 | 12 |
| `test_ui_libros.py` | 55 | 47 | 0 | 47 | 8 | 55 |
| `test_ui_marco.py` | 30 | 26 | 0 | 26 | 4 | 30 |
| `test_ui_precios_empresa.py` | 6 | 2 | 1 | 1 | 4 | 5 |
| `test_ui_roles.py` | 9 | 7 | 0 | 7 | 2 | 9 |
| `test_ui_tablero.py` | 33 | 23 | 23 | 0 | 10 | 10 |
| `test_ui_actualizacion.py` | 9 | 0 | 0 | 0 | 9 | 9 |
| `test_ui_administracion.py` | 16 | 0 | 0 | 0 | 16 | 16 |
| `test_ui_administracion_asistente.py` | 24 | 0 | 0 | 0 | 24 | 24 |
| `test_ui_componer.py` | 11 | 0 | 0 | 0 | 11 | 11 |
| `test_ui_componer_contraste.py` | 1 | 0 | 0 | 0 | 1 | 1 |
| `test_ui_componer_justificacion.py` | 5 | 0 | 0 | 0 | 5 | 5 |
| `test_ui_entregar.py` | 9 | 0 | 0 | 0 | 9 | 9 |
| `test_ui_escenarios.py` | 2 | 0 | 0 | 0 | 2 | 2 |
| `test_ui_hoja_asistente.py` | 20 | 0 | 0 | 0 | 20 | 20 |
| `test_ui_hoja_atipicos.py` | 5 | 0 | 0 | 0 | 5 | 5 |
| `test_ui_hoja_moneda.py` | 4 | 0 | 0 | 0 | 4 | 4 |
| `test_ui_hoja_planos.py` | 16 | 0 | 0 | 0 | 16 | 16 |
| `test_ui_hoja_primera_version.py` | 17 | 0 | 0 | 0 | 17 | 17 |
| `test_ui_hoja_responsable.py` | 4 | 0 | 0 | 0 | 4 | 4 |
| `test_ui_inicio.py` | 12 | 0 | 0 | 0 | 12 | 12 |
| `test_ui_pagina_control.py` | 16 | 0 | 0 | 0 | 16 | 16 |
| `test_ui_pagina_reajuste_valuaciones.py` | 2 | 0 | 0 | 0 | 2 | 2 |
| `test_ui_paginas_preparan_el_caso.py` | 2 | 0 | 0 | 0 | 2 | 2 |
| `test_ui_paginas_s1.py` | 3 | 0 | 0 | 0 | 3 | 3 |
| `test_ui_reajuste_pagina.py` | 4 | 0 | 0 | 0 | 4 | 4 |
| `test_ui_revisar.py` | 11 | 0 | 0 | 0 | 11 | 11 |
| `test_ui_similares.py` | 2 | 0 | 0 | 0 | 2 | 2 |
| `test_ui_similares_modulo.py` | 3 | 0 | 0 | 0 | 3 | 3 |
| `test_ui_similares_uc03.py` | 2 | 0 | 0 | 0 | 2 | 2 |
| `test_apptest_timeout_comun.py` | 3 | 0 | 0 | 0 | 3 | 3 |
| **Total** | **664** | **187** | **64** | **123** | **477** | **600** |

## 4. Tabla funcion por funcion

Items = casos de pytest (las parametrizadas cuentan una vez por caso).

| Archivo origen | Funcion | Items | Disposicion | Destino / motivo del retiro |
|---|---|---:|---|---|
| `test_config_streamlit.py` | `test_escucha_solo_en_el_bucle_local_y_sin_telemetria` | 1 | RETIRADA | `.streamlit/config.toml` y su suite de AppTest: configuracion de Streamlit, se retira con el modulo |
| `test_config_streamlit.py` | `test_cors_y_xsrf_explicitos` | 1 | RETIRADA | `.streamlit/config.toml` y su suite de AppTest: configuracion de Streamlit, se retira con el modulo |
| `test_config_streamlit.py` | `test_el_limite_de_subida_es_el_de_los_planos` | 1 | RETIRADA | `.streamlit/config.toml` y su suite de AppTest: configuracion de Streamlit, se retira con el modulo |
| `test_config_streamlit.py` | `test_los_detalles_de_error_no_llegan_al_navegador` | 1 | RETIRADA | `.streamlit/config.toml` y su suite de AppTest: configuracion de Streamlit, se retira con el modulo |
| `test_config_streamlit.py` | `test_streamlit_conoce_cada_opcion_del_archivo` | 1 | RETIRADA | `.streamlit/config.toml` y su suite de AppTest: configuracion de Streamlit, se retira con el modulo |
| `test_config_streamlit.py` | `test_la_suite_conserva_el_detalle_de_los_errores_de_apptest` | 1 | RETIRADA | `.streamlit/config.toml` y su suite de AppTest: configuracion de Streamlit, se retira con el modulo |
| `test_ui_acceso.py` | `test_la_fecha_inyectada_es_la_del_reloj_de_la_prueba` | 1 | RETIRADA | `ui.sesion.ahora` (reloj de la sesion Streamlit) |
| `test_ui_acerca.py` | `test_los_datos_traen_la_version_y_las_revisiones_de_las_dos_bases` | 1 | MOVIDA | `test_aplicacion_acerca.py` (con `config.ruta_caso_por_defecto()`) |
| `test_ui_acerca.py` | `test_una_base_que_no_existe_se_dice_sin_crearla` | 1 | MOVIDA | `test_aplicacion_acerca.py` (con `config.ruta_caso_por_defecto()`) |
| `test_ui_acerca.py` | `test_una_base_sin_alembic_version_lo_dice` | 1 | MOVIDA | `test_aplicacion_acerca.py` (con `config.ruta_caso_por_defecto()`) |
| `test_ui_acerca.py` | `test_una_base_ilegible_lo_dice_sin_excepcion` | 1 | MOVIDA | `test_aplicacion_acerca.py` (con `config.ruta_caso_por_defecto()`) |
| `test_ui_acerca.py` | `test_los_modulos_dicen_si_estan_instalados` | 1 | MOVIDA | `test_aplicacion_acerca.py` (con `config.ruta_caso_por_defecto()`) |
| `test_ui_acerca.py` | `test_un_modulo_que_no_existe_se_da_por_no_instalado` | 1 | MOVIDA | `test_aplicacion_acerca.py` (con `config.ruta_caso_por_defecto()`) |
| `test_ui_actualizacion_alta.py` | `test_el_detector_es_el_de_ml_y_sin_el_extra_no_hay` | 1 | MOVIDA | `test_aplicacion_actualizacion.py` (sobre `aplicacion.actualizacion.detector_de_atipicos`) |
| `test_ui_app.py` | `test_sin_modo_entrega_cuatro_secciones_en_el_orden_del_trabajo` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_modo_entrega_omite_investigacion_y_conserva_todo_trabajo` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_paginas_visibles_es_la_concatenacion_de_las_secciones` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_modo_entrega_solo_se_activa_con_el_valor_exacto_1` | 1 | MOVIDA | `test_aplicacion_entorno.py` (sobre `aplicacion.entorno`) |
| `test_ui_app.py` | `test_ningun_titulo_lleva_codigo_de_caso_de_uso` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_las_pantallas_con_caso_de_uso_lo_declaran` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_el_inicio_es_la_primera_pagina_y_la_unica_por_defecto` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_la_ruta_vacia_de_la_pagina_por_defecto_es_el_inicio` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_cada_pagina_tiene_una_ruta_url_propia` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_pagina_por_ruta` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_todo_paso_apunta_a_una_pagina_registrada` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_ningun_paso_sale_de_la_seccion_trabajo` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_app.py` | `test_el_extra_ui_exige_la_version_de_streamlit_con_navegacion_superior` | 1 | RETIRADA | extra `ui` de `pyproject.toml` (Streamlit) |
| `test_ui_app.py` | `test_son_veintiuna_pantallas_y_la_hoja_va_justo_despues_de_elaborar` | 1 | RETIRADA | `ui.app` / `ui.recorridos` (enrutador y menu Streamlit) |
| `test_ui_barra.py` | `test_importar_plano_se_detecta_por_el_paquete_de_planos_en_disco` | 1 | RETIRADA | `ui.barra` (barra superior Streamlit, clase (a) del plan) |
| `test_ui_barra.py` | `test_hay_importacion_de_planos_con_un_buscador_que_encuentra_o_no` | 1 | RETIRADA | `ui.barra` (barra superior Streamlit, clase (a) del plan) |
| `test_ui_barra.py` | `test_guardar_y_exportar_dependen_de_las_dos_funciones_de_ui_hoja` | 1 | RETIRADA | `ui.barra` (barra superior Streamlit, clase (a) del plan) |
| `test_ui_barra_con_la_hoja.py` | `test_la_hoja_real_expone_las_dos_funciones_y_la_deteccion_da_disponible` | 1 | RETIRADA | `ui.barra` + `ui.paginas.hoja` (Streamlit) |
| `test_ui_cliente.py` | `test_ip_del_cliente_sigue_el_ruling_de_streamlit` | 5 | RETIRADA | `ui.cliente.ip_del_cliente` lee `st.context.ip_address` (Streamlit puro) |
| `test_ui_cliente.py` | `test_con_la_red_encendida_solo_cuentan_el_bucle_y_la_ip_elegida` | 5 | MOVIDA | `test_aplicacion_equipo.py` (IP explicita en vez de `monkeypatch` de `ui.cliente.ip_del_cliente`) |
| `test_ui_cliente.py` | `test_con_la_red_apagada_la_ip_guardada_no_cuenta_como_propia` | 1 | MOVIDA | `test_aplicacion_equipo.py` (IP explicita en vez de `monkeypatch` de `ui.cliente.ip_del_cliente`) |
| `test_ui_cliente.py` | `test_si_no_se_puede_leer_la_ip_solo_es_local_con_la_red_apagada` | 1 | MOVIDA | `test_aplicacion_equipo.py` (IP explicita en vez de `monkeypatch` de `ui.cliente.ip_del_cliente`) |
| `test_ui_cliente.py` | `test_un_silice_toml_danado_se_lee_con_la_red_apagada` | 1 | MOVIDA | `test_aplicacion_equipo.py` (IP explicita en vez de `monkeypatch` de `ui.cliente.ip_del_cliente`) |
| `test_ui_cliente.py` | `test_una_operacion_sensible_se_rechaza_desde_una_ip_remota` | 1 | MOVIDA | `test_aplicacion_equipo.py` (IP explicita en vez de `monkeypatch` de `ui.cliente.ip_del_cliente`) |
| `test_ui_cliente.py` | `test_una_operacion_sensible_se_bloquea_con_eventos_sin_revisar` | 1 | MOVIDA | `test_aplicacion_equipo.py` (IP explicita en vez de `monkeypatch` de `ui.cliente.ip_del_cliente`) |
| `test_ui_cliente.py` | `test_remota_y_con_pendientes_manda_el_motivo_remoto` | 1 | MOVIDA | `test_aplicacion_equipo.py` (IP explicita en vez de `monkeypatch` de `ui.cliente.ip_del_cliente`) |
| `test_ui_cliente.py` | `test_administracion_exige_el_propio_equipo_antes_de_crear_una_clave_de_api` | 1 | RETIRADA | lee el codigo de `ui/paginas/administracion.py` (pagina retirada); la API usa `exigir_equipo_propio` |
| `test_ui_cliente.py` | `test_ningun_modulo_de_ui_ni_api_llama_a_es_local_de_seguridad_directamente` | 1 | MOVIDA | `tests/unit/test_aplicacion_equipo.py` como `test_ningun_modulo_de_api_ni_aplicacion_llama_a_es_local_de_seguridad_directamente` (misma logica AST; recorre `api` y `aplicacion` en vez de `ui` y `api`) |
| `test_ui_cliente.py` | `test_la_pantalla_de_acceso_de_s3_usa_el_aviso_de_s5` | 1 | RETIRADA | lee `ui/acceso.py` (pantalla retirada) |
| `test_ui_elaborar.py` | `test_aceptar_cambia_solo_el_item_pendiente` | 1 | MOVIDA | `test_aplicacion_elaboracion.py` |
| `test_ui_elaborar.py` | `test_aceptar_un_item_que_no_esta_es_un_error` | 1 | MOVIDA | `test_aplicacion_elaboracion.py` |
| `test_ui_elaborar.py` | `test_una_entrada_por_pendiente_en_su_orden_con_un_solo_normalizador` | 1 | MOVIDA | `test_aplicacion_elaboracion.py` |
| `test_ui_elaborar.py` | `test_sin_pendientes_no_hay_propuestas_ni_se_carga_nada` | 1 | MOVIDA | `test_aplicacion_elaboracion.py` |
| `test_ui_elaborar.py` | `test_una_falla_declarada_queda_en_la_entrada_del_pendiente` | 1 | MOVIDA | `test_aplicacion_elaboracion.py` |
| `test_ui_elaborar_plan_y_rendimiento.py` | `test_las_filas_del_plan_se_agrupan_por_periodo_y_una_a_medias_se_rechaza` | 1 | MOVIDA | `test_aplicacion_elaboracion.py` |
| `test_ui_existencias.py` | `test_tablero_para_pantalla_marca_el_estado` | 1 | RETIRADA | `ui.existencias` / `ui.app` (existencias: modulo retirado, sin homologo en aplicacion/) |
| `test_ui_existencias.py` | `test_cada_estado_se_rotula_con_icono_y_texto` | 1 | RETIRADA | `ui.existencias` / `ui.app` (existencias: modulo retirado, sin homologo en aplicacion/) |
| `test_ui_existencias.py` | `test_la_cantidad_escrita_acepta_coma_y_rechaza_lo_ambiguo` | 1 | RETIRADA | `ui.existencias` / `ui.app` (existencias: modulo retirado, sin homologo en aplicacion/) |
| `test_ui_existencias.py` | `test_importar_desde_pantalla_registra_y_manda_lo_dudoso_a_la_bandeja` | 1 | RETIRADA | `ui.existencias` / `ui.app` (existencias: modulo retirado, sin homologo en aplicacion/) |
| `test_ui_existencias.py` | `test_reimportar_el_mismo_reporte_no_duplica` | 1 | RETIRADA | `ui.existencias` / `ui.app` (existencias: modulo retirado, sin homologo en aplicacion/) |
| `test_ui_existencias.py` | `test_un_csv_tambien_se_importa` | 1 | RETIRADA | `ui.existencias` / `ui.app` (existencias: modulo retirado, sin homologo en aplicacion/) |
| `test_ui_existencias.py` | `test_sin_unidad_no_se_importa_nada_y_el_mensaje_es_el_del_lector` | 1 | RETIRADA | `ui.existencias` / `ui.app` (existencias: modulo retirado, sin homologo en aplicacion/) |
| `test_ui_existencias.py` | `test_un_xlsx_con_macros_renombrado_lo_rechaza_la_guardia` | 1 | RETIRADA | `ui.existencias` / `ui.app` (existencias: modulo retirado, sin homologo en aplicacion/) |
| `test_ui_existencias.py` | `test_navegacion_incluye_la_pagina_solo_para_quien_puede` | 1 | RETIRADA | `ui.existencias` / `ui.app` (existencias: modulo retirado, sin homologo en aplicacion/) |
| `test_ui_hoja.py` | `test_las_pestanas_son_las_nueve_de_la_spec_y_la_primera_es_espacio_y_metrajes` | 1 | RETIRADA | constante `PESTANAS` de `ui.paginas.hoja` (pagina Streamlit; React tiene las suyas) |
| `test_ui_hoja_trabajo.py` | `test_filtrar_partidas` | 9 | MOVIDA | `test_aplicacion_hoja_trabajo.py` |
| `test_ui_hoja_trabajo.py` | `test_filtrar_partidas_no_cambia_la_lista_de_entrada` | 1 | MOVIDA | `test_aplicacion_hoja_trabajo.py` |
| `test_ui_hoja_trabajo.py` | `test_el_cierre_de_ob_b_es_la_cascada_de_calcular_apu_a_mano` | 1 | MOVIDA | `test_aplicacion_hoja_trabajo.py` |
| `test_ui_hoja_trabajo.py` | `test_el_cierre_sigue_a_los_factores_y_cada_paso_suma_el_anterior` | 1 | MOVIDA | `test_aplicacion_hoja_trabajo.py` |
| `test_ui_informe_seguro.py` | `test_ninguna_pantalla_pinta_a_markdown_del_informe` | 1 | RETIRADA | barrido de `ui/` buscando `a_markdown(` (escape de Markdown de Streamlit) |
| `test_ui_instalacion.py` | `test_los_juegos_van_del_mas_nuevo_al_mas_viejo_y_saltan_los_ilegibles` | 1 | MOVIDA | `test_aplicacion_instalacion.py` |
| `test_ui_instalacion.py` | `test_el_zip_del_juego_trae_las_bases_y_la_ficha` | 1 | MOVIDA | `test_aplicacion_instalacion.py` |
| `test_ui_libros.py` | `test_totales_del_libro_limpio_coinciden_con_la_memoria_a_mano` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_totales_del_libro_con_h1_dan_la_diferencia_calculada_a_mano` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_totales_sin_dato_dicen_no_disponible_y_no_inventan_la_diferencia` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_diferencia_de_totales_en_la_frontera_del_centimo` | 3 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_totales_con_pdf_agregan_la_columna_de_lo_impreso` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_tabla_de_hallazgos_del_libro_limpio_es_r2_y_r7_en_info` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_tabla_de_hallazgos_con_h1_trae_f1_con_su_impacto_y_su_celda` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_opciones_de_filtro_ordenan_por_gravedad_y_dejan_lo_desconocido_al_final` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_filtrar_hallazgos_combina_los_tres_filtros_y_vacio_deja_pasar_todo` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_hoja_de_una_celda` | 7 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_marcas_por_hoja_del_libro_con_h1` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_marcas_expanden_rangos_por_filas_sin_repetir_codigos_y_con_tope` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_hay_tasas_y_filas_de_alertas_sin_tasa_dicen_no_contrastable` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_filas_de_alertas_con_tasa_formatean_tasa_bs_y_variacion` | 5 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_filas_de_trazabilidad` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_nombre_del_libro_devuelto` | 8 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_hojas_del_libro_limpio_en_su_orden` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_vista_calcada_resalta_lo_citado_y_declara_lo_que_queda_fuera` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_vista_calcada_escapa_el_texto_ajeno` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_abrir_libro_pasa_a_modo_ligero_justo_despues_del_tope` | 4 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_abrir_libro_mide_las_combinadas_sin_cargar_la_hoja` | 4 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_libros.py` | `test_abrir_libro_suma_el_area_de_las_combinadas` | 1 | RETIRADA | `ui.libros` (modulo retirado; la API usa `adapters.hoja_empresa.visual`) |
| `test_ui_marco.py` | `test_el_rol_arma_ve_lo_de_trabajo_y_no_ve_la_administracion` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_marco.py` | `test_el_rol_revisa_ve_la_lectura_y_nada_que_escriba` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_marco.py` | `test_el_administrador_no_ve_ninguna_pantalla_de_trabajo` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_marco.py` | `test_varios_roles_suman_sus_pantallas_sin_repetir` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_marco.py` | `test_sin_roles_solo_queda_lo_que_no_pide_accion` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_marco.py` | `test_toda_pantalla_menos_el_inicio_declara_la_accion_que_la_protege` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_marco.py` | `test_un_recorrido_omite_los_pasos_de_pantallas_que_el_rol_no_ve` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_marco.py` | `test_cada_render_exige_su_accion_en_la_primera_linea` | 19 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_precios_empresa.py` | `test_referencia_lista_de_empresa_y_hallazgos_de_la_memoria` | 1 | MOVIDA | `test_aplicacion_precios_empresa.py` |
| `test_ui_precios_empresa.py` | `test_la_pagina_no_importa_el_script_de_maprex_al_cargarse` | 1 | RETIRADA | importa `ui.paginas.precios_empresa` (pagina Streamlit) |
| `test_ui_roles.py` | `test_el_rol_arma_ve_el_trabajo_y_la_investigacion_pero_no_revisar_ni_administrar` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_roles.py` | `test_el_rol_revisa_solo_ve_el_inicio_la_lectura_y_la_revision` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_roles.py` | `test_el_administrador_solo_ve_el_inicio_los_precios_de_la_empresa_y_la_administracion` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_roles.py` | `test_arma_y_revisa_a_la_vez_ven_la_union_sin_administrar` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_roles.py` | `test_sin_roles_solo_se_ven_las_pantallas_sin_accion` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_roles.py` | `test_las_secciones_siguen_el_orden_de_s3_y_omiten_las_vacias` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_roles.py` | `test_ningun_recorrido_apunta_a_una_pantalla_que_el_rol_no_ve` | 1 | RETIRADA | `ui.app`/`ui.recorridos` (menu y roles del enrutador Streamlit) |
| `test_ui_tablero.py` | `test_el_desglose_de_ob_s2_es_el_de_la_memoria_y_suma_el_total` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_el_desglose_de_ti001_suma_el_total_literal_del_informe` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_un_presupuesto_de_total_cero_no_tiene_desglose_ni_pareto` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_el_pareto_con_resto_suma_el_total_y_cierra_en_cien` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_el_pareto_sin_resto_cuando_n_alcanza_a_todas_las_partidas` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_el_pareto_suma_los_renglones_de_una_misma_partida` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_sin_control_la_curva_es_el_plan_acumulado_del_presupuesto` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_con_control_la_curva_es_pv_ev_ac_y_salta_el_ac_que_falta` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_sin_indicadores_no_hay_tarjetas_de_control` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_las_tarjetas_de_control_de_ob_s2_al_corte` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_un_eac_disponible_no_lleva_el_motivo_del_eac_del_sistema` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_sin_ac_el_cpi_y_el_eac_dicen_el_motivo_del_ac` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_con_ac_cero_el_eac_dice_por_que_falta_el_cpi` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_sin_pv_el_spi_dice_su_motivo_y_el_avance_con_bac_cero_no_esta` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_sin_version_guardada_no_hay_tablero` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_el_tablero_sin_linea_base_trae_el_presupuesto_y_dice_por_que_no_hay_control` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_con_linea_base_y_sin_valuaciones_el_control_lo_dice` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_con_valuaciones_el_control_trae_los_indicadores_y_la_curva_pv_ev_ac` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_un_control_que_no_se_puede_calcular_da_su_motivo_y_no_rompe` | 3 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_el_comparativo_trae_las_versiones_y_omite_la_descartada` | 1 | MOVIDA | `test_aplicacion_tablero.py` |
| `test_ui_tablero.py` | `test_el_comparativo_de_una_decision_de_recuperacion_dice_su_motivo` | 1 | MOVIDA | `test_aplicacion_tablero.py` |

## 5. Mutantes (sobre copia fuera del repo)

Tres funciones movidas elegidas al azar (`random.seed(20261021)` sobre las 49). Cada mutante es una **copia de `aplicacion/`** en el scratchpad; el corredor la importa antes que el repo (`sys.path.insert` + `import aplicacion`, con `assert` de que `aplicacion.__file__` esta en la copia) y ejecuta solo la prueba movida. Control = misma copia sin mutar (verde).

| Prueba movida | Mutante | Control sin mutar | Con mutante |
|---|---|---|---|
| `test_aplicacion_equipo.py::test_un_silice_toml_danado_se_lee_con_la_red_apagada` | `ip_es_local`: `return not ajustes.red_local` pasa a `return ajustes.red_local` | 1 passed | **1 failed** (detectado) |
| `test_aplicacion_elaboracion.py::test_sin_pendientes_no_hay_propuestas_ni_se_carga_nada` | `propuestas_de_pendientes`: `return ()` pasa a `return (None,)` en la rama sin pendientes | 1 passed | **1 failed** (detectado) |
| `test_aplicacion_equipo.py::test_remota_y_con_pendientes_manda_el_motivo_remoto` | `operacion_sensible_permitida`: se invierte el orden (eventos pendientes antes que IP remota) | 1 passed | **1 failed** (detectado) |

Nota honesta: el primer mutante que se probo para la segunda funcion fue quitar la guarda `if not pendientes: return ()`; **sobrevivio**, porque `ml.normalization.propuestas_para` repite la misma guarda (equivalente a efectos de conducta, no un hueco de la prueba). Se sustituyo por el mutante de la tabla, que si cambia el comportamiento de la rama que la prueba cubre.

## 5b. Mutante de la guardia de `es_local` (copia fuera del repo)

Copia de `api/`, `aplicacion/` y `tests/fixtures/arquitectura.py` en el scratchpad, con la prueba extraida a `tests/unit/test_arq.py`. Control sin mutar: `1 passed`. Mutante: `from seguridad.red import es_local` insertado como primera linea de `api/__init__.py` de la copia: `AssertionError: assert ['api/__init__.py:1'] == []` (detectado).

## 6. Verificacion

- `pytest -W error -p no:cacheprovider -o addopts=""` de los 9 destinos y los 10 originales tocados: **149 passed + 96 passed**, y **3 failed** que no son de esta fase: `tests/unit/test_ui_instalacion.py::test_muestra_el_estado_de_la_red_y_de_la_api` y `::test_con_la_red_apagada_lo_dice` (dos pruebas AppTest, que no se tocaron) fallan por el texto de la pagina: esperan `API: apagada (puerto 8000)` y reciben `API: activa (puerto 8501)`, consecuencia del commit F2 `cd158d0a` (un solo proceso uvicorn, la API siempre activa en el puerto unico). La primera pasada citaba el kwarg `api_activa` como causa: era el mismo defecto visto desde otra prueba de ese archivo, no la causa raiz. Se borran en F4 de todos modos. Los 9 destinos y el resto de originales, en verde.
- `ruff check` y `ruff format --check` de todos los archivos tocados: limpios (tras un `ruff format` de `test_ui_tablero.py`, commit aparte).
- Commits (uno por grupo): `bbfc0627` (tablero), `64261f98` (elaboracion), `2ec0e6c4` (hoja trabajo), `f8c2dedf` (equipo), `f7a555bb` (instalacion), `a52bf57c` (acerca), `2bca7813` (actualizacion y entorno), `4b889d9c` (precios de empresa), `af9a4343` (guardia de `es_local`: ver 5b), mas el de formato de `test_ui_tablero.py`.

## 7. Hallazgos fuera de la fase

1. **Guardia de arquitectura (resuelta en la ronda 1).** `test_ningun_modulo_de_ui_ni_api_llama_a_es_local_de_seguridad_directamente` ya no se pierde: su mitad `api/` se movio a `test_aplicacion_equipo.py` (commit `af9a4343`), recorriendo `api` y `aplicacion`. Mutante en 5b.
2. **Visibilidad por rol del menu.** `test_ui_marco.py` y `test_ui_roles.py` (15 funciones) probaban que cada rol ve solo sus pantallas (`ui.app.paginas_visibles`). Ese criterio vivia en el enrutador Streamlit; en la API y en React la cobertura equivalente es de otros archivos (no medida aqui). Conviene que el arbitro confirme que `frontend-desktop` o `api/` tienen su propia prueba de roles antes de F4.
3. **`ui.app.modo_entrega_activo`** solo estaba cubierto con valores `"0"` y `"si"` por la prueba de paridad circular; se movio a `test_aplicacion_entorno.py`, donde ahora esta asertado contra literales (F6 podra borrar la paridad sin perder cobertura).
4. **`aplicacion/equipo.py` no tenia prueba directa** (solo a traves de `ui.cliente`); ahora tiene `test_aplicacion_equipo.py`.
5. Quedan en los originales constantes y ayudantes huerfanos (p. ej. `_MODULOS_RELACIONADOS_CON_ML` en `test_ui_actualizacion_alta.py`); se van con el archivo en F4.

## 7b. Decisiones para Eugenio

Estas funciones se retiran con su modulo, pero **no se comprobo que React tenga homologo**; el retiro de su cobertura es una decision de producto, no de este triaje:

1. **`ui.libros`: 22 funciones** de `test_ui_libros.py` (hallazgos resaltados en la vista calcada del libro, filtros y orden de la tabla de hallazgos, totales, marcas por hoja, tope de celdas combinadas). La API usa `adapters.hoja_empresa.visual`, pero no se verifico que React reproduzca el resaltado de hallazgos ni los filtros/orden de la tabla.
2. **Recorridos de Streamlit** (`ui.recorridos`; probados en `test_ui_app`, `test_ui_marco`, `test_ui_roles`): demostracion, presupuesto, precios y paquete. En React solo existe el recorrido «Auditar un libro de la empresa» (`shell/recorrido.ts`); los otros cuatro no tienen homologo comprobado. Si deben sobrevivir, hay que construirlos y probarlos antes de F4.

Decision pedida: aceptar la perdida de esas coberturas o abrir tarea para que React las tenga.

## 8. Propuesta de linea para `CHANGELOG.md` (la anota el orquestador)

`- Retiro de Streamlit, F3: 50 funciones (64 items) de pruebas de logica que vivian dentro de archivos AppTest pasan a tests/unit/test_aplicacion_{tablero,elaboracion,hoja_trabajo,equipo,instalacion,acerca,actualizacion,entorno,precios_empresa}.py; 76 funciones (123 items) se retiran con su modulo.`
