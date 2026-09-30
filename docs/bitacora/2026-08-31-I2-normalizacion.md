# Bitácora — Sesión I2: memoria y normalización semántica (UC‑03)

**Fecha:** 2026‑08‑31 · **Rama:** `inc/I2-normalizacion` (fusionada a `main` con `--no-ff`) ·
**Base:** `0749279` (limpieza post‑F.1) · **Sesión del PLAN:** I2 (Fase 2), pendiente desde el
sprint alpha; se ejecuta ahora por indicación del usuario («haz la limpieza y continúa con la
siguiente sesión»).

## Qué se hizo

- **`ml/normalization/`** (`normalizador.py`): `NormalizadorPartidas` vectoriza el catálogo con
  `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`, el modelo que fija el PLAN;
  embeddings normalizados, similitud del coseno como producto punto) y `similares()` devuelve a lo
  sumo tres `PartidaSimilar` ordenadas por puntaje descendente, ninguna bajo `UMBRAL_POR_DEFECTO`
  (RF‑15). Catálogo vacío o nada sobre el umbral → lista vacía (flujos 2b y 2a del UC‑03). Sin
  datos etiquetados ni entrenamiento, como exige el PLAN.
- **`ui/paginas/similares.py`** + registro en `ui/app.py` (séptima pantalla): descripción en texto
  libre → propuestas con puntaje; cada propuesta precarga su desglose y su rendimiento
  (`Catalogo.composicion`) mostrando el código de origen y el puntaje (RF‑16, parte de precarga).
  Import perezoso de `ml.normalization` (mismo criterio que el visor con el extra `civil`);
  `CatalogoIncompleto` por propuesta → advertencia, no traza (flujo 4a).
- **`tests/unit/test_normalizacion.py`** (6 pruebas, TDD con RED observado por `ImportError`):
  RF‑15, puntaje ≈ 1 con descripción idéntica, **aceptación RF‑17** (≥ 80 % de la línea base
  parafraseada reconocida en el primer puesto — 5/5 en la corrida de cierre), flujos 2a/2b y el
  parámetro `cuantos`. Catálogo de prueba: las cinco partidas de la única copia de la línea base
  (`tests/fixtures/apu_linea_base.py`, DRY).
- ERS actualizado: filas RF‑15/16/17 y matriz UC‑03 pasan de «prueba pendiente» a sus pruebas.

## Decisiones

| Decisión | Motivo |
|---|---|
| `ml/` recibe el catálogo como pares (código, descripción) planos; la página de la UI es la capa de composición que consulta `core.catalog` | `ml/` solo puede importar `core.contracts` (NORMAS.md §2, `test_arquitectura.py`); este módulo no necesita ni eso — sin base de datos, sin sesión |
| El puntaje de similitud es `float`, no `Decimal` | Es una similitud adimensional en [−1, 1], no una cantidad de obra ni un monto: la regla `Decimal` de NORMAS.md §2.3 alcanza «cantidades, precios, factores y rendimientos», y los vectores del modelo son `float32` de origen. Se presenta redondeado solo en la UI |
| `UMBRAL_POR_DEFECTO = 0.5` | Umbral declarado que exige RF‑15, calibrado con la aceptación RF‑17: las cinco paráfrasis puntúan cómodamente por encima y la consulta fuera de dominio («auditoría contable…») queda por debajo |
| Modelo cacheado por proceso (`lru_cache`) | Cargarlo cuesta segundos y cientos de MB de RAM; la UI de Streamlit re‑ejecuta la página en cada interacción |
| `HF_HUB_DISABLE_SYMLINKS_WARNING=1` en las pruebas | En Windows sin modo desarrollador, la primera descarga del modelo emite un `UserWarning` documentado de `huggingface_hub` (caché sin symlinks); rompería el DoD de cero advertencias (`-W error`) en un entorno limpio. Es la variable oficial de la librería, no un filtro genérico |
| Las pruebas se saltan si el modelo no puede cargarse (`OSError` → `pytest.skip`) | Precondición del UC‑03 en el ERS: «el modelo de similitud está disponible localmente». Mismo patrón que `pytest.importorskip("ifcopenshell")` con el extra `civil`. El sprint corrió con el modelo descargado y las seis pruebas pasando |

## Hallazgos

1. **La persistencia de RF‑16 no puede cumplirse todavía.** «Al aceptar una propuesta… conservando
   la referencia a la partida de origen y el puntaje» presupone un flujo de **creación de
   partidas** que ningún UC implementado ofrece (el catálogo nace de `scripts/seed.py`) y
   `models.Partida` no tiene columnas de origen/puntaje (docs/modelo_datos.md no las contempla).
   No se parchea el modelo de datos desde una sesión de `ml/`: la precarga queda cubierta en la UI
   y la persistencia se decide cuando exista ese flujo (candidato: administración del catálogo,
   Fase 6 o decisión del tutor en G0). El ERS lo deja anotado en RF‑16.
2. **El extra `ml` pesa** (torch CPU + transformers, del orden de GB) y la primera construcción
   descarga ~470 MB de modelo a la caché de Hugging Face. Documentado aquí para el capítulo de
   requisitos de despliegue; el entorno del sprint queda `uv sync --extra ui --extra api
   --extra civil --extra ml`.

## Estado al cierre

```
uv run pytest -q -W error            -> 343 passed (337 + 6 de normalizacion), 0 advertencias
uv run ruff check . / format --check -> limpios
uv run python scripts/meta_alpha.py  -> 12/12 metas OK
git diff --stat core/ (en la rama)   -> vacio: la sesion no toco el nucleo
```

## Próximos pasos

1. G0 (tutor) — ahora incluye el hallazgo 1 de esta bitácora (persistencia de RF‑16).
2. G1 contra un IFC exportado por una herramienta BIM real.
3. Sesiones I6.1/I6.2/I6.3 con el cruce formal de G2 (conteo informal 2026‑08‑31: todos los
   dominios ≪ 50 registros → sistema de reglas con análisis de sensibilidad como técnica
   probable de `ml/prediction/`).
