# Scripts

Cada archivo `.py` de esta carpeta tiene su fila aquí, salvo `__init__.py`, que es el paquete y se
documenta en su propio docstring. Lo vigila `tests/unit/test_scripts_documentados.py` (INV‑051).
Todos se ejecutan desde la raíz del repositorio con `uv run python scripts/<nombre>.py`; el detalle
de sus opciones está en el docstring de cada uno.

## Siembra de bases SQLite

`--db <ruta>` elige otra base y `--reiniciar` borra el esquema antes de recrearlo. Sobre la ruta
por defecto, `--reiniciar` exige además `--confirmar` (INV‑050).

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
| `extraer_arenaza.py` | genera y verifica contra los PDF los dos CSV de presupuestos ARENAZA en `data/telecom/fuentes/` | M1.1 · telecom |
| `derivar_listas_telecom.py` | deriva las dos listas de precios canónicas de UC‑02 del dominio telecom (ARENAZA y MaPreX) | M1.3 · telecom |
| `generar_tanquilla_ifc.py` | genera `data/samples/tanquilla.ifc`, el modelo IFC de muestra de la compuerta G1 | I3.1 · civil |

## Simulación y medición

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `simular_lista.py` | lista de precios determinista (por semilla) a partir de la vigente del catálogo, para pruebas de UC‑02 | UC‑02 |
| `simular_corpus.py` | corpus simulado y determinista de composiciones APU | P4.3 · prototipo |
| `medir_rnf03.py` | mide RNF‑03: el tiempo del recálculo masivo de UC‑02 con N partidas en SQLite local | RNF‑03 |

## Artefactos reproducibles

La CI los regenera y los compara con `git diff --exit-code`.

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `exportar_openapi.py` | exporta el esquema OpenAPI de la aplicación FastAPI a `docs/api.json` | F.1 · api |
| `generar_resultados_ml.py` | genera `docs/resultados_ml.md`: compuerta G2 y métricas del módulo predictivo (RF‑28) | I6 · ml |

## Guardias de la CI

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `guardia_nucleo.py` | la hipótesis central sobre `<base>..HEAD`: falla si un commit toca `core/` junto a `adapters/` o `ml/`, o si una rama fusionada que incorpora un dominio cambia `core/` | CI |
| `verificar_omitidas.py` | falla si el JUnit de pytest trae alguna prueba omitida | CI |

## Metas de sprint

Cada una audita las metas de su sprint (`OK`/`FALLA`/`PENDIENTE`); una fase se cruza con
`--hasta <fase>` donde el script lo admite (CLAUDE.md §3).

| Script | Qué hace | Sesión o dominio |
|---|---|---|
| `meta_alpha.py` | corre la suite, ruff y el historial de git para reportar las 12 metas del sprint alpha | sprint alpha |
| `meta_i6.py` | las 12 metas del sprint I6 (Sesiones I6.2 e I6.3) | sprint I6 |
| `meta_multidominio.py` | las 12 metas del sprint multidominio (fases M0 a M4) | sprint multidominio |
| `meta_prototipo.py` | las 12 metas del prototipo AREN.IA, en seis fases (P0 a P5) | sprint prototipo |
| `meta_asistente.py` | las 12 metas del plan del asistente de presupuestos (UC‑09) | plan del asistente |
| `meta_redaccion.py` | los 12 chequeos de la redacción de la tesis (R1 a R12) | sprint R1 |
| `meta_datos.py` | tres chequeos (D1 a D3): la documentación del repositorio no presenta sus datos como reales | limpieza de datos |
