# APU System

Sistema de generación y auditoría de Análisis de Precios Unitarios (APU) multidominio, asistido por
modelo BIM‑5D y aprendizaje automático. Trabajo de grado; caso de estudio: obra civil del sistema de
drenaje de una clínica (caso de ejemplo con contenido y formato reales de APU, no una obra ejecutada;
ver [docs/linea_base.md](docs/linea_base.md)).

La hipótesis central del trabajo es que **un núcleo de costeo y verificación puede permanecer intacto
mientras se agregan dominios (civil, telecom, industrial, sistemas) mediante adaptadores**. La prueba
empírica es `git diff --stat core/` vacío al terminar los adaptadores (Sesión I5); la mide la meta M9
de `scripts/meta_alpha.py` —commit a commit y, además, con el `git diff core/` del **rango completo**
de cada rama que incorpora un dominio— y la vigila `tests/unit/test_arquitectura.py`.

## Documentos rectores

| Documento | Para qué |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Constitución del proyecto: principios, cálculo, contratos, estructura, reglas, compuertas |
| [PLAN_DESARROLLO.md](PLAN_DESARROLLO.md) | Las 20 sesiones de trabajo, con prompt, criterio de cierre y commit |
| [docs/metodologia.md](docs/metodologia.md) | Metodología Scrum‑Cascada y principio DRY aplicados al proyecto |
| [docs/README.md](docs/README.md) | Índice de toda la documentación |

## Arranque rápido

```powershell
uv sync                                   # crea .venv e instala dependencias base + grupo dev (pytest, ruff)
uv run pytest                             # suite de pruebas
uv run ruff check .                       # estilo
uv run python scripts/seed.py             # carga la línea base en data/apu.db (idempotente; --reiniciar para recrear)
uv run python scripts/meta_alpha.py       # estado de las 12 metas del sprint alpha (OK/FALLA/PENDIENTE)
uv sync --extra ui                        # instala Streamlit
uv run streamlit run ui/app.py            # UI mínima: actualización masiva de precios (UC-02) e informe de auditoría
```

> OneDrive sincroniza todo lo que hay en esta carpeta, incluido `.venv/`. Para evitarlo, antes de
> `uv sync` defina `$env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\apu_system\.venv"` (o fíjelo
> como variable de usuario). `.venv` está en `.gitignore` en cualquier caso.

## Estado de la suite

Toda la suite está en verde (versión alpha 0.1, sprint del 2026‑08‑29). Qué vigila cada archivo:

| Archivo | Qué comprueba | Sesión |
|---|---|---|
| `tests/unit/test_contracts.py` | invariantes de los contratos (`Decimal`, unidades normalizadas, dataclasses inmutables) | 0 |
| `tests/unit/test_arquitectura.py` | `core/` no importa adaptadores, ML, UI ni API; los adaptadores solo importan `core.contracts` | 0 |
| `tests/unit/test_linea_base.py` | integridad del caso auditado (`tests/fixtures/apu_linea_base.py`) | 0 |
| `tests/unit/test_costing.py` | el motor reproduce los cinco APU de la línea base ± 0,01 | I0.3 |
| `tests/unit/test_meta_alpha.py` | las funciones puras de `scripts/meta_alpha.py` | alpha |
| `tests/unit/test_reglas_civil.py` | 0,224 m3 y 4,48 m2 por tanquilla; adaptador tabular | I3.2 |
| `tests/unit/test_verification.py` | evaluador, texto, directivas y las siete reglas sobre el presupuesto auditado | I4 |
| `tests/unit/test_adapter_{telecom,industrial,sistemas}.py` | cada adaptador devuelve `ItemComputo` trazables sin importar nada de `core` salvo `core.contracts` | I5 |
| `tests/unit/test_budget.py` | presupuesto 1 586,61; la curva cierra exactamente en el total; Excel de cuatro hojas | I0.5 |
| `tests/integration/test_persistencia.py` | SQLite reconstruye las cinco composiciones idénticas; precios a fecha; variantes de insumos | I0.4 |
| `tests/integration/test_auditoria_7_de_7.py` | **7 de 7** inconsistencias detectadas; el presupuesto corregido cumple | I4 |
| `tests/integration/test_civil_verificacion.py` | el balance del adaptador civil es resoluble por R5 | I3.2 (4b) |
| `tests/integration/test_presupuesto_linea_base.py` | seed → catálogo → `elaborar` → guardar → cargar reproduce el presupuesto | I0.5 |
| `tests/integration/test_actualizacion_precios.py` | UC‑02: nueva lista de precios, `CambioPrecio`, `IncidenciaCambio`, reconstrucción a fecha | I1 |

## Mapa del repositorio

```
core/        núcleo cerrado: contracts (estables), costing, models, catalog, budget, verification
adapters/    un paquete por dominio (civil tabular, telecom, industrial, sistemas); solo importan core.contracts
ml/          normalization, anomaly, prediction (pendientes de la compuerta G2)
ui/  api/    Streamlit (UC-02 mínimo) y FastAPI (Fase F)
tests/       unit, integration, fixtures (la línea base vive en tests/fixtures/apu_linea_base.py)
data/        linea_base (evidencia primaria), samples (CSV por dominio, PDF telecom, lista de precios de muestra)
docs/        metodología, ERS, modelo de datos, arquitectura, línea base, esqueleto de tesis, bitácora
scripts/     seed.py (línea base en SQLite), meta_alpha.py (las 12 metas del alpha)
```
