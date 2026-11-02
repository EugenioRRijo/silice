# Hoja 3e-3 y T11: cierre de paridad, suite completa y auditoría visual

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `520d401c` (Hoja completa, 3b a 3e fusionadas) · **Verificador:** subagente de cierre.
Sin push ni PR. `core/`, `ui/`, `asistente/` y `aplicacion/hoja.py` sin cambios (`git diff 520d401c..HEAD -- core ui asistente aplicacion/hoja.py` vacío);
`app.openapi() == docs/api.json` (comprobado). Datos: todo ficticio (OF-001 y TI-001 de las fixtures); `SILICE_DATOS` en carpetas temporales del scratchpad, nunca `data/`.

## 1. Commits de esta entrega

| SHA | Qué |
|---|---|
| `87548224` | `test(hoja)`: PE 1 763,39 y 62,50 % tras restaurar la 002 y tras cotizar sobre la 002; `con_anexos_de_cadena` llamado por `_crear` en las cuatro operaciones (rojo visto: 4 en rojo al quitar la llamada) |
| `755fa6db` | `test(front)`: un diálogo abierto en Precios o Trazabilidad cuyo panel se remonta por un cambio de `rev` no deja la página `[inert]` (rojo visto al quitar la limpieza de `useDialogoDeOperacion`: 2 en rojo) |
| `0ae3e1e9` | `fix(front)` H-1: la región con foco de las tablas anchas es la que desplaza (CSS + prueba de estilo) |
| `a412d589` | `fix(front)` H-2: retomar ofrece el borrador cuando el servidor dice el nombre y la cabecera el código (rojo visto: 2 pruebas) |
| `658fc4eb` | `test(integracion)`: dos fallos nuevos de la migración en la suite completa (`{partida:path}` en el recorrido de rutas; guardia de RF-100 con `api/rutas/hoja.py`) |

## 2. Tabla de paridad (diseño §9.2)

Criterio: la fila está cubierta si una prueba en la API/Vitest afirma el literal de la memoria o del diseño (no una lectura de la clásica) y otra, cuando aplica, la
compara con la clásica. `A` = `tests/unit/test_api_hoja*.py`, `P` = `tests/unit/test_aplicacion_hoja_paridad*.py`, `V` = `tests/unit/test_aplicacion_hoja_vista.py`,
`F` = `frontend-desktop/src/paginas/hoja/`.

| Fila | Estado | Prueba(s) |
|---|---|---|
| P1 total 2 703,86 | cubierta | `A/test_api_hoja.py::test_r2_abre_of001_v001_con_el_total_de_la_memoria`; `P/test_aplicacion_hoja_paridad.py::test_abrir_of001_da_el_total_de_la_memoria_en_las_dos`; `F/Hoja.test.tsx` |
| P2 3 · 4,345 · 8,250 | cubierta | `A/test_api_hoja.py::test_r5_of001_da_las_cantidades_derivadas_de_la_memoria`; `P/test_aplicacion_hoja_paridad_espacio.py::test_las_tablas_de_of001_reconstruyen_el_espacio_de_la_memoria`; `F/Vistas.test.tsx` |
| P3 PE 1 530,49 · 56,60 % · «Dia 23» | cubierta | `A/test_api_hoja.py::test_r9_of001_da_el_equilibrio_de_la_memoria`; `P/test_aplicacion_hoja_paridad.py::test_elaborar_ti001_da_el_punto_de_equilibrio_de_la_memoria_en_las_dos`; `F/Vistas3b3.test.tsx` |
| P4 frases de PE (4 casos límite) | cubierta | `V/test_aplicacion_hoja_vista.py::test_los_cuatro_casos_limite_del_equilibrio_dicen_su_frase`; `F/Vistas3b3.test.tsx` (3b-F9) |
| P5 Estado por fila | cubierta | `A/test_api_hoja.py::test_r5_el_estado_de_cada_fila_lleva_severidad_y_texto_de_la_clasica`; `P/…paridad.py::test_el_estado_de_filas_de_of001_es_igual_en_las_dos` y `::test_el_estado_de_filas_marca_ok_en_una_fila_que_ningun_hallazgo_toca` |
| P6 TI-001 sin espacio, sin crear filas | cubierta | `A/test_api_hoja.py::test_r2_sobre_ti001_no_tiene_espacio_y_no_escribe_versiones_ni_filas_esp`; `P/…paridad.py::test_abrir_ti001_no_tiene_espacio_y_es_igual_en_las_dos` |
| P7 proyecto sin versiones | cubierta | `A/test_api_hoja.py::test_r2_de_un_proyecto_sin_versiones_abre_un_borrador_en_blanco` |
| P8 historial 001/002/003 | cubierta | `A/test_api_hoja.py::test_r1_con_tres_versiones_da_el_historial_de_la_aceptacion_sf`; `A/test_api_hoja_versiones.py::test_restaurar_la_001_crea_la_003_copia_de_la_001_y_la_deja_vigente` |
| P9 Precios: 21 columnas, estado, erosión | cubierta | `A/test_api_hoja.py::test_r12_of001_trae_las_21_columnas_en_el_orden_de_la_clasica`, `::test_r12_un_precio_en_usd_tiene_erosion_cero_y_la_de_indice_no_viene`, `::test_paridad_r12_los_precios_son_los_de_la_clasica` (fecha fija); literal de `s1_conversion.md` (0,4163… USD, 358,1123… Bs, 26,3683 %) en `V/…::test_la_erosion_de_la_memoria_s1_se_ve_en_dos_decimales_y_exacta` (capa de aplicación; la ruta solo la mapea) |
| P10 Trazabilidad de la 002 | cubierta | `A/test_api_hoja.py::test_r14_la_version_002_trae_exactamente_el_registro_de_la_celda_editada`, `::test_r14_de_las_tres_versiones_trae_el_historial_completo` |
| P11 Auditoría con R17 | cubierta | `A/test_api_hoja.py::test_r11_of001_es_el_informe_de_la_clasica_y_evalua_r17`, `::test_r11_un_punto_de_agua_sin_fuente_da_el_hallazgo_r17_advertencia`, `::test_paridad_r11_…` |
| P12 cascada de la partida | cubierta | `A/test_api_hoja.py::test_r7_con_partida_da_la_cascada_a_mano_de_af_llave`; `P/test_aplicacion_hoja_paridad_apu.py::test_la_llave_de_oficina_cuesta_10_433785_y_su_precio_unitario_13_198738025` |
| P13 administración 0,20 → 2 821,42 · PE 1 763,39 · 62,50 % · `cambios == 1` | cubierta; **ampliada en esta entrega** | `A/test_api_hoja_edicion_secciones.py::test_e3_administracion_020_da_los_literales_de_p13`; `A/test_api_hoja_guardado.py::test_guardar_con_fuente_crea_la_002_con_su_registro_exacto_y_los_literales_de_la_memoria`; `A/test_api_hoja.py::test_r9_de_la_version_002_con_administracion_020_da_las_cifras_de_p13`; nuevas: `A/test_api_hoja_versiones.py::test_restaurar_la_002_deja_el_punto_de_equilibrio_de_p13_en_la_003` y `::test_cotizar_sobre_la_002_sube_el_punto_pero_el_porcentaje_sigue_en_62_50` |
| P14 parámetro inválido | cubierta | `A/test_api_hoja_edicion_secciones.py::test_e3_un_parametro_invalido_es_422_con_el_texto_de_la_clasica_y_conserva_los_previos`; `P/…paridad_secciones.py::test_un_parametro_invalido_dice_el_campo_y_el_texto_de_la_clasica` |
| P15 AF-LLAVE 3 → 5 (+26,3975) | cubierta | `A/test_api_hoja_edicion_secciones.py::test_e2_la_llave_de_3_a_5_suma_26_39748_marca_r8_y_registra_el_cambio` |
| P16 cantidad negativa | cubierta | `A/test_api_hoja_edicion_secciones.py::test_e2_una_cantidad_negativa_dice_la_fila_de_la_tabla_completa_aunque_se_mande_una_sola` |
| P17 alto `2,5` | cubierta | `A/test_api_hoja_edicion.py::test_e1_el_alto_con_coma_es_422_con_el_texto_de_la_clasica_y_el_borrador_no_cambia` |
| P18 fila en blanco · id duplicado | cubierta | `A/test_api_hoja_edicion.py::test_e1_una_fila_en_blanco_no_es_un_error_ni_cambia_nada`, `::test_e1_un_id_duplicado_y_una_referencia_rota_dan_el_mensaje_del_modelo` |
| P19 plan que no suma 1 | cubierta | `A/test_api_hoja_edicion_secciones.py::test_e4_un_plan_que_no_suma_1_es_422_con_el_texto_de_la_clasica_y_el_plan_no_cambia` |
| P20 plan secuencial | cubierta | `A/test_api_hoja_edicion_secciones.py::test_e5_el_plan_secuencial_de_of001_tiene_30_periodos_y_la_curva_cierra_en_el_total` |
| P21 cambiar insumo | cubierta | `A/test_api_hoja_apu_retomar.py::test_e7_el_pegamento_en_lugar_de_la_llave_conserva_la_cantidad_y_sube_101_7860745`, `::test_e7_el_tecnico_en_lugar_del_plomero_cambia_el_sueldo_y_no_la_cantidad` |
| P22 partida nueva del catálogo / pendiente | cubierta | `A/test_api_hoja_edicion.py::test_e1_la_partida_que_la_version_no_tenia_toma_su_apu_del_catalogo_de_la_version`, `::test_e1_una_partida_sin_apu_en_el_catalogo_queda_pendiente_y_no_suma` |
| P23 cambiar de versión con cambios | cubierta | `A/test_api_hoja_apu_retomar.py::test_e11_cambiar_de_version_no_descarta_nada_p23`; `F/Retomar.test.tsx` (3c-F9) |
| P24 bloqueos con cambios pendientes (P:1946, 2081, 2201) | cubierta | `F/Versiones.test.tsx` describe «3d-F5» (Precios, Parámetros, Trazabilidad) |
| P25 guardar sin fuente | cubierta | `A/test_api_hoja_guardado.py::test_guardar_sin_fuente_es_422_con_el_texto_de_la_clasica_y_no_escribe_nada` |
| P26 guardar con fuente | cubierta | `A/test_api_hoja_guardado.py::test_guardar_con_fuente_crea_la_002_…` ; `P/…paridad_guardado.py::test_guardar_la_administracion_en_20_da_la_002_con_el_total_de_la_memoria` |
| P27 cadena íntegra tras guardar | cubierta | `A/test_api_hoja_guardado.py::test_la_cadena_queda_integra_tras_guardar_por_la_api` |
| P28 guardado que falla | cubierta | `A/test_api_hoja_guardado.py::test_si_la_copia_del_espacio_falla_no_queda_nada_y_se_puede_reintentar`; `P/…paridad_guardado.py::test_si_la_copia_del_espacio_falla_las_dos_deshacen_todo` |
| P29 solo lectura | cubierta | `A/test_api_hoja_guardado.py::test_una_version_en_solo_lectura_no_se_guarda_y_dice_por_que` |
| P30 primera versión | cubierta | `A/test_api_hoja_guardado.py::test_la_primera_version_de_un_proyecto_nuevo_es_la_001_con_la_memoria` |
| P31 restaurar la 001 | cubierta | `A/test_api_hoja_versiones.py::test_restaurar_la_001_crea_la_003_copia_de_la_001_y_la_deja_vigente` |
| P32 cotizar / retirar | cubierta | `A/test_api_hoja_versiones.py::test_cotizar_crea_la_version_nueva_con_ese_insumo_y_conserva_el_plan`, `::test_retirar_la_cotizacion_vuelve_al_precio_de_la_lista_base` |
| P33 convertir (÷ o × tasa; sin tasa) | cubierta | `A/test_api_hoja_conversion_cadena.py::test_convertir_a_bs_crea_la_002_con_la_tasa_de_venta_y_el_total_de_la_memoria_por_la_tasa`, `::test_sin_ninguna_tasa_no_se_convierte_nada_y_lo_dice` |
| P34 responsable = la sesión | cubierta | `A/test_api_hoja_guardado.py::test_el_responsable_es_la_sesion_y_el_cuerpo_no_puede_decir_otro_p34`; `A/test_api_hoja_versiones.py::test_el_responsable_es_la_sesion_y_el_cuerpo_no_puede_decir_otro_p34` |
| P35 permisos por rol | cubierta | `A/test_api_hoja_versiones.py::test_quien_no_arma_no_puede_usar_ninguna_de_las_cuatro`, `::test_la_clave_de_api_no_escribe_versiones`; `A/test_api_hoja_guardado.py::test_rita_que_revisa_y_tomas_con_clave_temporal_no_pueden_guardar`, `::test_la_clave_de_api_no_guarda` |
| P36 Excel: 9 hojas + extras, total evaluado ±0,005 | cubierta | `A/test_api_hoja_exportar.py::test_b1_el_libro_de_of001_tiene_las_nueve_hojas_y_el_total_del_sistema`, `::test_paridad_el_libro_es_celda_por_celda_el_de_la_clasica`; comprobado además con Chromium real (§4: `hoja_003.xlsx`, 9 hojas + 5 `Esp …`) |
| P37 plano de OF-001: alturas, circuitos, fusión | cubierta | `A/test_api_hoja_plano.py::test_p5_sobre_un_borrador_en_blanco_da_el_total_y_las_cantidades_de_la_memoria` (2 703,86 ±0,01; cantidades ±0,001), `::test_p3_las_seis_alturas_de_la_memoria_se_cargan_y_rev_no_sube`, `::test_p4_declarar_los_dos_circuitos_y_ya_no_hay_aviso`; `P/…paridad_planos.py::test_fusionar_da_el_mismo_borrador_y_el_resumen_cuenta_una_vez` |
| P38 rechazado, detenido, extensión ajena | cubierta | `A/test_api_hoja_plano.py::test_p1_un_archivo_corrupto_es_rechazada_con_200_y_no_se_fusiona`, `::test_p1_un_dxf_sin_unidad_se_detiene_y_p2_con_metros_reanuda`, `::test_p1_otra_extension_es_422_antes_de_escribir_nada`; `F/ImportarPlano.test.tsx` («Solo se aceptan archivos .dxf o .ifc.») |
| P39 interfaz: 1366×768, teclado, un `h1`, foco visible | cubierta por Vitest **y** por la auditoría visual de esta entrega | `F/Hoja.test.tsx` (un `h1`), `F/Vistas.test.tsx` (un `h1`), `F/estilosEdicion.test.ts`; medición con Chromium real en §4 |

**NO cubierta:** ninguna. Lo que no tenía prueba y se agregó: la 003 restaurada de la 002 y la cotización sobre la 002 con el PE y el 62,50 % (P13 tras S2/S3),
la llamada a `con_anexos_de_cadena` desde `_crear` y el diálogo abierto que se remonta por `rev`. Cobertura por capas en P9: la ruta de Precios no tiene un literal de
erosión en Bs (solo ceros en USD y la paridad con la clásica a fecha fija); el literal de la memoria S1 está en la capa de aplicación.
Las diferencias deliberadas DV-1 a DV-13 no cuentan como fallo (diseño §9.3).

## 3. T11, suite completa

Entorno: `uv run --active` (venv común de `TESIS`, **sin** los extras `planos`, `pdf` ni `anthropic`) y, para lo que esos extras necesitan, `python -m pytest` del `.venv` de
`.worktrees\s2m4` (solo lectura, trae `ezdxf`, `xlrd`, `anthropic` y el extra `pdf`). Siempre `-W error -p no:cacheprovider`, `SILICE_DATOS` temporal.

| Corrida | Resultado |
|---|---|
| `tests/unit` sin `test_ui_*` (301 archivos), venv común | 6 457 pasaron, 124 fallaron, 22 errores de recolección (3 026 s) |
| los 19 archivos que fallaron, más `test_aceptacion_sf`, `test_clave_ia_nunca_aparece` y `test_api_libros`, venv de `s2m4` | 572 pasaron, 2 fallaron |
| `tests/integration` (venv común) | 1 589 pasaron, 9 fallaron, 17 errores (1 196 s) |
| `tests/integration/test_api_clave.py` tras el arreglo `658fc4eb` | 182 pasaron |
| `tests/integration/test_atipicos.py::test_solo_las_dos_pantallas…` tras el arreglo | pasa |
| `test_ui_*` (54 archivos, AppTest), en 5 tandas paralelas | 858 pasaron, 1 falló y 1 error de recolección; los dos archivos (`test_ui_libros.py`, `test_ui_hoja_planos.py`) pasan con el venv de `s2m4` (71 verdes) |
| `vitest` completo por mitades (115 archivos) | primera pasada: 765 + 1 007 = 1 772, con 2 fallos por carga (`PlanoEnHoja` «Fusionar… ocupadoPorEdicion» y `Retomar` «lee el borrador vivo») que pasan aislados; pasada final con mis 5 pruebas nuevas y la máquina libre: **765 + 1 012 = 1 777 verdes, 0 fallos** |
| `npm run lint` | limpio (`eslint .` y `tsc -b --noEmit`) |
| `npm run build` | verde; `npm run dist`: 162 archivos, 14 032 527 bytes (límite 15 000 000), sin URLs externas |
| `ruff check .` | limpio; `ruff format --check`: los tres archivos que toqué están formateados (41 archivos ajenos ya lo estaban sin formatear) |
| `app.openapi() == docs/api.json` | verdadero |

### 3.1 Clasificación de fallos

| Fallo | Clase | Evidencia |
|---|---|---|
| 7 en `tests/integration/test_api_libros.py` (`Esta instalación no puede leer PDF: falta el componente pdf`) | preexistente conocido | pasan con el `.venv` de `s2m4` (trae el extra) |
| 50 en `test_hoja_empresa_pdf.py`, 6 en `test_dependencias_silice.py`, 6 en `test_asistente_instalacion.py`, 3 en `test_licencia_ifc.py`, 2 en `test_hoja_rotulos.py`, 1 en `test_extras_perezosos.py`, 1 en `test_asistente_claude.py`, `test_deteccion_planos.py` | entorno (extras ausentes del venv común) | los 19 archivos pasan con el venv de `s2m4` salvo los dos de abajo |
| 45 en `test_api_hoja_plano.py`, 1 en `test_aplicacion_hoja_plano.py`, 15 en `test_aplicacion_hoja_paridad_planos.py`, 22 errores de recolección y 16 en `test_aceptacion_sf.py`, `test_clave_ia_nunca_aparece.py` | entorno (`ModuleNotFoundError: ezdxf` / `anthropic`; la decisión de proyecto es no instalar los extras) | pasan con el venv de `s2m4` |
| `test_experimento_congelado_vigente.py::test_los_archivos_del_auditor_siguen_como_se_congelaron` | preexistente conocido (decisión pendiente del congelado) | falla en ambos venv |
| `test_sin_omisiones.py::test_ninguna_prueba_se_omite_por_su_cuenta` | **NUEVO respecto de la lista, pero no de la Hoja**: `tests/unit/test_api_control.py:538` tiene un `pytest.skip("ninguna opcion aplica al corte de la memoria")` | `git blame`: `d78ae316` (2026-10-18, rama de Control, no está en `main`). No se tocó (otro encargo y pide una decisión: convertir el `skip` en un caso que siempre aplique) |
| `test_api_clave.py::test_el_recorrido_ve_todas_las_rutas_del_esquema` | **NUEVO, de la migración, arreglado** (`658fc4eb`) | las dos rutas `/v1/hoja/borradores/{id}/apu/{partida:path}` (PUT) y `…/insumo` (POST) salen en el OpenAPI como `{partida}`; el recorrido comparaba la ruta con el convertidor |
| `test_atipicos.py::test_solo_las_dos_pantallas_de_precios_y_su_ruta_importan_la_busqueda_de_rf_100` | **NUEVO, de la migración, arreglado** (`658fc4eb`) | `api/rutas/hoja.py` (R13) y `api/esquemas_atipicos.py` importan la búsqueda; se agregaron a los permitidos |
| 3 de BCV real `.xls` por `xlrd` | no aparecieron en esta corrida | — |
| Vitest: `Retomar`, `PlanoEnHoja`, `HojaExcel` | flaky por carga conocido | pasan aislados (35 y 5 verdes) |

### 3.2 `test_ui_*` (AppTest de Streamlit)

Corridos aparte, en cinco tandas paralelas (en una sola corrida serial tardaban más de 4 horas): 254 + 169 + 68 + 170 + 197 = 858 pasaron. Fallaron `test_ui_libros.py::test_un_pdf_simple_sin_excel_se_revisa_con_l10`
(falta el extra `pdf` del venv común: conocido) y `test_ui_hoja_planos.py` (error de recolección por `ezdxf`); con el venv de `s2m4` los dos archivos dan 71 verdes. Ninguna prueba agotó
los 3 s de AppTest en esta corrida.

## 4. Auditoría visual de la Hoja (Chromium real)

**Entorno:** Chromium 151 de `ms-playwright` (ya instalado; no hay Playwright como librería, así que se manejó por el protocolo DevTools con Node 22, sin instalar nada),
perfil propio en el scratchpad, API con `uvicorn` en `127.0.0.1:8000` sobre un caso ficticio (OF-001 con tres versiones: 001, 002 con administración 0,20 y 003 con la
cotización de EQU-001), cuenta `ana`. Cierre de ambos procesos por su PID. Anchos de 1366 y 1056 px, alto 768. Capturas en el scratchpad (`visual\fotos`).

**Medido a 1366 y a 1056 px, en las nueve pestañas:** `scrollWidth == clientWidth` en todas (sin desplazamiento horizontal de la página), cero elementos desbordados fuera
de un desplazador, un solo `h1` («Hoja del proyecto»), cero controles sin nombre, ningún solape de controles propios (el único «solape» a 1056 es el botón de
desplazamiento de las pestañas de Carbon sobre el borde de la lista, por diseño). Los tres paneles del APU se apilan a 1056. Foco: 40 paradas de Tab seguidas con anillo
visible (`outline: solid 2px`), las flechas recorren las nueve pestañas, la columna fija de «Puntos» no oculta el elemento enfocado (15 pasos con Mayús+Tab a ambos
anchos: izquierda del campo ≥ 432 px, derecha de la columna fija 416 px).

**Diálogos** (guardar, restaurar, cotizar, retirar, convertir), a ambos anchos: nombre accesible, foco inicial dentro, 14 Tab sin salir, el resto de la página `inert`,
Esc cierra, devuelve el foco al botón que lo abrió y quita todo `inert`, sin desbordes. **Importar plano** (DXF de OF-001 por la ruta real): informe 33 / 0 / 9 / 6 como
en las pruebas, 6 alturas, 2 circuitos y fusión («Se fusionó «of001.dxf» … 6 ambientes, 6 fuentes y 21 puntos»), sin desborde a ninguno de los dos anchos. **Excel:**
el botón descarga `hoja_003.xlsx` con las 9 hojas y las 5 `Esp …`.

### Hallazgos

| Id | Severidad | Hallazgo | Estado |
|---|---|---|---|
| H-1 | MAYOR (accesibilidad) | En Precios, «Ambientes», «Fuentes», «Puntos» y «Cantidades derivadas» la región con `tabindex="0"` y nombre «…: desplazar horizontalmente» **no era el desplazador**: lo era `.silice-tabla` (de `TablaDensa`) o el contenedor de Carbon. Con el foco en la región de Precios, ArrowRight ×6 dejaba `scrollLeft` en 0 (la tabla mide 1 097 px en 1 031; en las otras tres la región medía 1 031 con el contenido en 1 310 a 1 326, y en «Puntos» había dos desplazadores anidados, 1 412 y 1 916) | **Arreglado** en `0ae3e1e9` (`hoja.scss`: dentro de `.silice-hoja__desplazable`, `.silice-tabla` y `.cds--data-table-content` con `overflow-x: visible`) con prueba de estilo; verificado en el navegador: Precios `scrollLeft` 66 (el máximo), «Plan» 240 |
| H-2 | MAYOR (lógica, funcional) | «Retomar borrador» **nunca aparecía con datos reales**: E10 devuelve `proyecto` = nombre del proyecto («OF-001: oficina con baño…») y la página lo comparaba con el código de la cabecera. Tras recargar con cambios, abrir la hoja daba el 409 «retómelo o reemplácelo» sin botón alguno | **Arreglado** en `a412d589` (acepta código o nombre; el rótulo dice el nombre). Rojo visto: `logicaRetomar.test.ts` y `Retomar.test.tsx`. Las pruebas anteriores usaban código = nombre y no podían verlo |
| H-3 | MENOR | Un `role="alert"` vacío por cada `TextInput` de Carbon editable: 296 en Espacio, 900 en Plan y curva, 30 en Presupuesto, 10 en APU, 4 en Parámetros. No se anuncian (están vacíos), pero son 900 regiones vivas en el DOM | Registrado (viene de Carbon; se arregla con otro componente de celda o con `invalid={false}` y sin `invalidText`) |
| H-4 | MENOR | El diálogo «Registrar una cotización» mide 692 px a 768 de alto y desplaza por dentro: al abrirlo, «Cancelar» y «Cotizar» quedan bajo el borde del diálogo (alcanzables con Tab o desplazando) | Registrado. Sugerencia: pie fijo (sticky) o menos separación vertical entre campos |
| H-5 | MENOR (heredado de `src/comun`) | Tras «Descargar Excel» el foco queda en el `h1`/cuerpo, no en el botón (ya anotado en 3e) | Registrado |
| H-6 | INFO | La pestaña Espacio mide 52 340 a 54 998 px de alto (cinco tablas de 6 a 33 filas, 296 campos) | Conocido (3c-1, T11); no es un desborde horizontal |
| H-7 | INFO | A 1056 px la lista de pestañas se desplaza (botón › de Carbon); es el comportamiento del componente y las flechas llegan a las nueve | Sin acción |

No verificado: arrastrar y soltar con el ratón en la zona de archivos (el archivo se entregó al `<input type="file">` por el protocolo), el teclado dentro de esa zona,
lectores de pantalla, modo oscuro, Firefox/Edge, y la medición de memoria del lector de planos (§ riesgos de `2026-10-20-hoja-3e-avance.md`).

## 5. Pendientes que siguen siendo de Eugenio

El `skip` de `test_api_control.py:538` (el árbitro de `test_sin_omisiones` lo vigila), la decisión del congelado (`test_experimento_congelado_vigente`), los extras `planos` y
`pdf` en el venv común si se quiere que la suite completa corra sin el `.venv` de `s2m4`, los 14 riesgos de `2026-10-20-hoja-3e-avance.md` (tope de tiempo del lector de
planos, barrido de `silice_planos_*`) y el retiro de Streamlit.
