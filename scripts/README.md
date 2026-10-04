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
| `seed_demo.py` | en una sola orden: línea base, las tres partidas `DEMO-*` del caso didáctico de AREN.IA y el presupuesto `DEMO-001` guardado con su informe | P4.2 · prototipo |
| `seed_industrial.py` | catálogo de mantenimiento industrial en `data/apu_industrial.db` y su presupuesto `MNT-001` | M2.2 · industrial |
| `seed_sistemas.py` | catálogo de sistemas (puntos de función) en `data/apu_sistemas.db` y su presupuesto `SIS-001` | M3.2 · sistemas |
| `seed_telecom.py` | catálogo telecom (ARENAZA) en `data/apu_telecom.db` y la reproducción de sus dos presupuestos | M1.2 · telecom |

## Datos derivados de las fuentes

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `extraer_maprex.py` | extrae de los tres listados MaPreX de julio de 2026 las referencias de precios por dominio en `data/precios/maprex_2026-07/` (necesita `--with pymupdf`) | M0.2 · todos |
| `lista_maprex_usd.py` | deriva, de las cuatro referencias MaPreX por dominio, la lista de precios en el formato canónico de UC‑02 (`tipo,insumo,unidad,precio`) | UC‑02 · todos |
| `extraer_arenaza.py` | genera y verifica contra los PDF los dos CSV de presupuestos ARENAZA en `data/telecom/fuentes/` (necesita `--with pymupdf`) | M1.1 · telecom |
| `derivar_listas_telecom.py` | deriva las dos listas de precios canónicas de UC‑02 del dominio telecom (ARENAZA y MaPreX) | M1.3 · telecom |
| `generar_tanquilla_ifc.py` | genera `data/samples/tanquilla.ifc`, el modelo IFC de muestra de la compuerta G1 (necesita el extra `civil`) | I3.1 · civil |

## Simulación y medición

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `simular_lista.py` | lista de precios determinista (por semilla) a partir de la vigente del catálogo, para pruebas de UC‑02 | UC‑02 |
| `simular_corpus.py` | corpus simulado y determinista de composiciones APU | P4.3 · prototipo |
| `generar_hoja_prueba.py` | generador determinista de puntos (`generar_items`) y composiciones simples para medir la hoja | RNF‑11 · SF0 |
| `prueba_data_editor.py` | app Streamlit descartable de la prueba corta de `st.data_editor` con 500 puntos (procedimiento en `medir_data_editor.md`) | spec SF §11.3 · SF0 |
| `medir_rnf03.py` | mide RNF‑03: el tiempo del recálculo masivo de UC‑02 con N partidas en SQLite local | RNF‑03 |
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

## Metas de sprint

Cada una audita las metas de su sprint (`OK`/`FALLA`/`PENDIENTE`); una fase se cruza con
`--hasta <fase>` donde el script lo admite (NORMAS.md §3).

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `meta_alpha.py` | corre la suite, ruff y el historial de git para reportar las 12 metas del sprint alpha | sprint alpha |
| `meta_i6.py` | las 12 metas del sprint I6 (Sesiones I6.2 e I6.3) | sprint I6 |
| `meta_multidominio.py` | las 12 metas del sprint multidominio (fases M0 a M4) | sprint multidominio |
| `meta_prototipo.py` | las 12 metas del prototipo AREN.IA, en seis fases (P0 a P5) | sprint prototipo |
| `meta_sf.py` | las 10 metas del sprint final, en seis fases (SF0 a SF5) | sprint final |
| `meta_asistente.py` | las 12 metas del plan del asistente de presupuestos (UC‑09) | plan del asistente |
| `meta_redaccion.py` | los 12 chequeos de la redacción de la tesis (R1 a R12) | sprint R1 |
| `meta_datos.py` | tres chequeos (D1 a D3): la documentación del repositorio no presenta sus datos como reales | limpieza de datos |
