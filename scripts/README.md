# Scripts

Cada archivo `.py` de esta carpeta tiene su fila aquí, salvo `__init__.py`, que es el paquete y se
documenta en su propio docstring. Lo vigila `tests/unit/test_scripts_documentados.py` (INV‑051).
Se ejecutan desde la raíz del repositorio con `uv run python scripts/<nombre>.py`, salvo los que
piden algo más: `--with pymupdf` (`extraer_maprex.py`, `extraer_arenaza.py`) o el extra `civil`
(`generar_tanquilla_ifc.py`, `uv sync --extra civil`). El detalle de sus opciones está en el
docstring de cada uno.

## Siembra de bases SQLite

`--db <ruta>` elige otra base y `--reiniciar` borra el esquema antes de recrearlo. Sobre la ruta
por defecto, `--reiniciar` exige además `--confirmar` (INV‑050), también si esa ruta se
escribe con `--db`; con `--db` hacia otra ruta basta `--reiniciar`.

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `seed.py` | carga la línea base (`tests/fixtures/apu_linea_base.py`) en `data/apu.db` para reproducir el presupuesto completo; define `RUTA_POR_DEFECTO`, la ruta de trabajo que importan los demás | I0.4 · civil |
| `seed_demo.py` | en una sola orden: línea base, las tres partidas `DEMO-*` del caso didáctico de Sílice y el presupuesto `DEMO-001` guardado con su informe | P4.2 · prototipo |
| `seed_industrial.py` | catálogo de mantenimiento industrial en `data/apu_industrial.db` y su presupuesto `MNT-001` | M2.2 · industrial |
| `seed_sistemas.py` | catálogo de sistemas (puntos de función) en `data/apu_sistemas.db` y su presupuesto `SIS-001` | M3.2 · sistemas |
| `seed_telecom.py` | catálogo telecom (ARENAZA) en `data/apu_telecom.db` y la reproducción de sus dos presupuestos | M1.2 · telecom |
| `seed_of001.py` | la oficina OF‑001 con su espacio y la versión `001` en `data/prueba_sf.db`, la base propia de CP‑08 a CP‑11 del guion; se niega a escribir en `data/apu.db` y exige `--reiniciar` si el archivo existe | SF · integración |

## Datos derivados de las fuentes

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `extraer_maprex.py` | extrae de los tres listados MaPreX de julio de 2026 las referencias de precios por dominio en `data/precios/maprex_2026-07/` (necesita `--with pymupdf`) | M0.2 · todos |
| `lista_maprex_usd.py` | deriva, de las cuatro referencias MaPreX por dominio, la lista de precios en el formato canónico de UC‑02 (`tipo,insumo,unidad,precio`) | UC‑02 · todos |
| `lista_maprex_bs.py` | deriva la lista MaPreX en Bs (`precio`, `fecha`, `fuente`, `referencia`) copiando `precio_bs` tal cual, referencia de R11 (S1 §6.2) | S1 · todos |
| `extraer_arenaza.py` | genera y verifica contra los PDF los dos CSV de presupuestos ARENAZA en `data/telecom/fuentes/` (necesita `--with pymupdf`) | M1.1 · telecom |
| `derivar_listas_telecom.py` | deriva las dos listas de precios canónicas de UC‑02 del dominio telecom (ARENAZA y MaPreX) | M1.3 · telecom |
| `generar_tanquilla_ifc.py` | genera `data/samples/tanquilla.ifc`, el modelo IFC de muestra de la compuerta G1 (necesita el extra `civil`) | I3.1 · civil |
| `dibujar_of001_dxf.py` | dibuja `tests/fixtures/planos/of001.dxf` entidad por entidad con `ezdxf` desde las tablas de las memorias de cálculo de OF‑001 (nunca desde la hoja manual); necesita el extra `planos` | RF‑50 · SF5 |

## Simulación y medición

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `simular_lista.py` | lista de precios determinista (por semilla) a partir de la vigente del catálogo, para pruebas de UC‑02 | UC‑02 |
| `simular_corpus.py` | corpus simulado y determinista de composiciones APU | P4.3 · prototipo |
| `generar_hoja_prueba.py` | generador determinista de puntos (`generar_items`) y composiciones simples para medir la hoja | RNF‑11 · SF0 |
| `prueba_data_editor.py` | app Streamlit descartable de la prueba corta de `st.data_editor` con 500 puntos (procedimiento en `medir_data_editor.md`) | spec SF §11.3 · SF0 |
| `medir_data_editor.md` | procedimiento escrito de la prueba corta de `st.data_editor` con 500 puntos (qué se mide, cómo y con qué umbrales); lo ejecuta una persona en el navegador con `prueba_data_editor.py`, porque `AppTest` no escribe en el editor | spec SF §11.3 · SF0 |
| `medir_rnf11.py` | mide RNF‑11: la hoja del proyecto con 500 puntos del generador, en `ui.hoja` sin Streamlit, desde aplicar una edición hasta tener presupuesto, informe y punto de equilibrio sin persistir (una corrida de calentamiento y la mediana de cinco); **solo registra** la cifra en `scripts/_salida_rnf11.json`, de donde la lee la meta S9 | RNF‑11 · SF3 |
| `medir_rnf03.py` | mide RNF‑03: el tiempo del recálculo masivo de UC‑02 con N partidas en SQLite local | RNF‑03 |
| `generar_obra_control.py` | obra determinista de control (partidas, plan, línea base y valuaciones por período) para medir RNF‑15 (500 partidas, 52 períodos, 26 valuaciones) | RNF‑15 · Sílice 0.7.0 |
| `probar_precios_maprex.py` | prueba los casos didácticos con precios de referencia publicados (MaPreX de julio de 2026 y tabulador CIV): cobertura del listado MaPreX en USD, revaloración del presupuesto 001 civil y de TC‑001/TC‑002, comprobación de MNT‑001 y SIS‑001; siempre en un directorio temporal, sin `--db` (con el extra `ml`, que instala `uv sync --all-extras`, marca los precios atípicos; sin él corre igual y lo declara) | C6 · todos |

## Artefactos reproducibles

La CI los regenera y los compara con `git diff --exit-code`.

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `exportar_openapi.py` | exporta el esquema OpenAPI de la aplicación FastAPI a `docs/api.json` | F.1 · api |
| `generar_resultados_ml.py` | genera `docs/resultados_ml.md`: compuerta G2 y métricas del módulo predictivo (RF‑28) | I6.3 y M4.1 · ml |

## Caso TI-001 e informes en PDF

Caso construido de redes de computación (laptops HP, cableado Cat 6, canalización EMT y servidor en
rack), con datos en `tests/fixtures/caso_ti001.py` y cantidades en
`data/samples/telecom/topologia_ti001.csv`. Los dos generadores de PDF necesitan el extra `informes`
(`uv run --extra informes python scripts/<nombre>.py --salida <ruta>.pdf`).

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `analisis_ti001.py` | recálculo independiente del PU, pruebas de control con errores sembrados, sensibilidad y punto de equilibrio del caso; sin argumentos imprime el resumen | caso TI-001 · telecom |
| `informe_ti001.py` | PDF del caso: APU, presupuesto, plan, curva, punto de equilibrio, auditoría del presupuesto y del programa (extra `informes`) | caso TI-001 · telecom |
| `auditoria_ti001.py` | datos de la auditoría técnica del programa del 30/09/2026 que muestra la sección 2 del informe (instantánea fechada) | caso TI-001 · todos |
| `glosario_presupuestos.py` | PDF con el glosario de siglas, las fuentes de cada dato y la guía para presupuestar una red (extra `informes`) | caso TI-001 · telecom |

## Guardias de la CI

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `guardia_nucleo.py` | la hipótesis central sobre `<base>..HEAD`: falla si un commit toca `core/` junto a `adapters/` o `ml/`, o si una rama fusionada que incorpora un dominio cambia `core/` | CI |
| `verificar_omitidas.py` | falla si el JUnit de pytest trae alguna prueba omitida | CI |
| `dividir_suite.py` | reparte los archivos `tests/**/test_*.py` en tramos balanceados (voraz «mayor primero», pesos de `pesos_suite.json` o tamaño) para los runners paralelos | CI |
| `unir_junit.py` | une los JUnit de los tramos en uno por sistema operativo, exige que lleguen todos y escribe los pesos medidos por archivo | CI |
| `descargar_modelo.py` | descarga una vez el modelo de similitud a la caché de Hugging Face; la suite corre sin red (`HF_HUB_OFFLINE=1`) y la CI lo corre antes de pytest | CI · RV‑17 |

## Metas de sprint

Cada una audita las metas de su sprint (`OK`/`FALLA`/`PENDIENTE`); una fase se cruza con
`--hasta <fase>` donde el script lo admite (NORMAS.md §3).

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `meta_alpha.py` | corre la suite, ruff y el historial de git para reportar las 12 metas del sprint alpha | sprint alpha |
| `meta_i6.py` | las 12 metas del sprint I6 (Sesiones I6.2 e I6.3) | sprint I6 |
| `meta_multidominio.py` | las 12 metas del sprint multidominio (fases M0 a M4) | sprint multidominio |
| `meta_prototipo.py` | las 12 metas del prototipo AREN.IA (hoy Sílice), en seis fases (P0 a P5) | sprint prototipo |
| `meta_sf.py` | las 10 metas del sprint final, en seis fases (SF0 a SF5) | sprint final |
| `meta_asistente.py` | las 12 metas del plan del asistente de presupuestos (UC‑09) | plan del asistente |
| `meta_redaccion.py` | los 12 chequeos de la redacción de la tesis (R1 a R12) | sprint R1 |
| `meta_datos.py` | tres chequeos (D1 a D3): la documentación del repositorio no presenta sus datos como reales | limpieza de datos |
| `meta_silice.py` | meta única de Sílice: siete comprobaciones comunes (ERS por presencia, cero omitidas, prueba antes que código, contratos y regresión intactos desde v0.5.0, cifras de tiempo, guardia de red) más las de cada parte en `meta_silice_<parte>.py` | 0.6.0 a 1.0.0 |
| `meta_silice_s1.py` | parte S1 de la meta única: once requisitos de S1 por presencia en la ERS, prueba antes que código de SL‑E1 a SL‑E3 y del adaptador BCV, memorias a mano (S1‑MEM), `FUENTE.md` del BCV (S1‑FUENTE) y base de prueba 0.6.0 con su ficha (S1‑BASE‑060) | 0.6.0 |
| `meta_silice_s5.py` | parte S5 de la meta única: RF‑96 y RNF‑20, prueba antes que código de S5‑1 y base de prueba de v0.5.0 con su ficha (S5‑M3) | 0.6.0 |
| `meta_silice_s2.py` | parte S2 de la meta única (0.7.0): los diez requisitos de S2 por presencia en la ERS, memoria OB‑S2 (S2‑MEM), reglas R13 y R14 en la ERS (S2‑REGLAS), expedientes SL‑E4 a SL‑E6 (S2‑EXPEDIENTES), memorias de S1 intactas desde v0.6.0 (S2‑REG‑S1) y base de prueba 0.7.0 con su ficha (S2‑BASE‑070) | 0.7.0 |
| `meta_silice_s3.py` | parte S3 de la meta: UC‑21 a UC‑23, RF‑80 a RF‑89 y RF‑100, protocolos con huella, OF‑001 limpio (S3‑M1 a S3‑M5) | 0.8.0 |
| `huellas_protocolos_s3.py` | escribe `docs/protocolos_s3.json`: el SHA‑256 de los dos protocolos de S3 y su lista | 0.8.0 |
| `meta_silice_s4.py` | parte S4 de la meta única: UC‑09, RF‑32, RF‑90 a RF‑95 y RNF‑18 por presencia en la ERS, RNF‑08 con la excepción del asistente, banco de tareas con su huella, guardia de arquitectura y núcleo intacto del asistente, y congelado y resultados del experimento | 0.9.0 |
| `escribir_banco_asistente.py` | escribe las 16 fichas del banco de tareas del asistente (memoria de cálculo a mano) en `tests/fixtures/asistente/tareas`; no se vuelve a correr tras el congelado | 0.9.0 |
| `explorar_ia.py` | prueba exploratoria de S4.0: `keyring` y el modelo local de Ollama (`keyring` \| `ollama --modelo <nombre>`); no llama a ninguna API de pago | 0.9.0 |
| `_experimento.py` | lo común de los scripts del experimento del asistente: contexto (banco, composiciones, catálogo) y proveedor real con la clave del almacén de credenciales; no se ejecuta solo | 0.9.0 |
| `prueba_real_asistente.py` | prueba manual del asistente con la API real: **gasta dinero** y exige `--acepto-costo`, que autoriza una persona; solo tareas de desarrollo; no la corre la CI ni el plan | 0.9.0 |

## Bases de prueba y migraciones (Sílice, desde la 0.6.0)

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `generar_base_prueba.py` | genera, **con el código de una etiqueta**, las bases de prueba `demo.db`, `of001.db` y `ti001.db` de esa versión y su `ficha.json` (filas por tabla, total literal y huella del informe) en `tests/fixtures/bases/v<X_Y_Z>/`; se niega a reescribirlas | S5‑1 · RV‑3 |
| `congelar_esquema.py` | escribe una revisión base de Alembic con el DDL literal (`sqlite_master`) de una base de prueba, en orden de creación; se niega a pisar una revisión existente (la revisión base queda congelada) | S5‑1 · RF‑96 |
| `generar_ids_silice.py` | escribe (o con `--comprobar`, verifica) `data/ids/silice_instalaciones.ids`, los requisitos IDS del IFC (necesita el extra `ifc`) | S3-5 · RF-89 |
| `sembrar_errores_planos.py` | siembra errores conocidos en el DXF de OF-001 y en el IFC de oficina (catálogo de S3) | S3-5 · RF-89 |
| `medir_deteccion_planos.py` | mide la tasa de detección y las falsas alarmas de la auditoría de planos sobre esos errores | S3-5 · RF-89 |
