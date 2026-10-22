# Sílice

Sistema de generación y auditoría de Análisis de Precios Unitarios (APU) multidominio, asistido por
modelo BIM‑5D y aprendizaje automático. Nombre del producto desde la versión 0.6.0; el prototipo de
septiembre de 2026 se llamó AREN.IA (hoy Sílice). Trabajo de grado; caso de estudio: obra civil del
sistema de drenaje de una clínica (ejercicio académico ficticio con el contenido y el formato de un APU
venezolano, no una obra ejecutada; ver [docs/linea_base.md](docs/linea_base.md)).

La hipótesis central del trabajo es que **un núcleo de costeo y verificación puede permanecer intacto
mientras se agregan dominios (civil, telecom, industrial, sistemas) mediante adaptadores**. La prueba
empírica es `git diff --stat core/` vacío al terminar los adaptadores (Sesión I5); la mide la meta M9
de `scripts/meta_alpha.py` —commit a commit y, además, con el `git diff core/` del **rango completo**
de cada rama que incorpora un dominio—, la vigila `tests/unit/test_arquitectura.py` y, en cada PR,
`scripts/guardia_nucleo.py` en la integración continua.

## Documentos rectores

| Documento | Para qué |
|---|---|
| [NORMAS.md](NORMAS.md) | Constitución del proyecto: principios, cálculo, contratos, estructura, reglas, compuertas |
| [PLAN_DESARROLLO.md](PLAN_DESARROLLO.md) | Las 20 sesiones de trabajo, con prompt, criterio de cierre y commit (completo) |
| [PLAN_CIERRE.md](PLAN_CIERRE.md) | El final de la tesis: fases de corrección C0–C4, mediciones con personas (Med) y redacción, con sus compuertas |
| [docs/metodologia.md](docs/metodologia.md) | Metodología Scrum‑Cascada y principio DRY aplicados al proyecto |
| [docs/README.md](docs/README.md) | Índice de toda la documentación, con los planes de cada sprint |

## Arranque rápido

**Para usar Sílice:** instale `Silice-<versión>.exe` (sin administrador, sin internet) después de
comprobar su huella y su firma ([manual de instalación](docs/manual_instalacion.md)) y abra
«Sílice» desde el menú Inicio.

**Para desarrollar:**

```powershell
uv sync --all-extras                      # crea .venv con las dependencias, el grupo dev y los extras (api, civil, ifc, planos, ml, anomalias, similitud, informes, bcv, ia)
uv run python scripts/descargar_modelo.py      # una vez: modelo de similitud (la suite corre sin red)
uv run pytest -W error                    # suite de pruebas (advertencia = error)
uv run ruff check .                       # estilo
uv run python -m operacion adoptar data/apu.db --nombre silice   # una vez, si trae una base de la 0.5.0: la copia a data/casos/silice.db y la migra (el original no se toca)
uv run python scripts/seed_demo.py --db data/casos/silice.db     # o, sin base anterior: el caso de demostración en el caso por defecto
uv run start.py                            # EL COMANDO: siembra los casos de demostración la primera vez y abre la app en 127.0.0.1
uv run uvicorn api.main:app --host 127.0.0.1            # solo la API y la interfaz, sin sembrar (documentación interactiva en http://127.0.0.1:8000/docs)
```

Un solo proceso (Uvicorn, `api.main:app`) sirve la API y la interfaz de React en `/app/`, por el
puerto de `[servidor]` de `silice.toml` (8501 por omisión con `start.py`), y escucha solo en
127.0.0.1. La interfaz está en `frontend-desktop/` y se compila con `npm run build` (la carpeta
`dist/` es lo que sirve Uvicorn). Streamlit ya no forma parte del producto.

> **Pendiente:** una instalación nueva (sin cuentas) aún no puede crear su primer administrador desde la pantalla; el flujo de «primera vez» de React no está construido (véase el [manual de instalación](docs/manual_instalacion.md#primer-arranque)).

La operación completa está en el [manual de usuario](docs/manual_usuario.md); cómo mantener y
extender el sistema, en el [manual técnico](docs/manual_tecnico.md).

> OneDrive sincroniza todo lo que hay en esta carpeta, incluido `.venv/`. Para evitarlo, antes de
> `uv sync` defina `$env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\apu_system\.venv"` (o fíjelo
> como variable de usuario). `.venv` está en `.gitignore` en cualquier caso.

## Estado de la suite

La suite corre en verde con `-W error` y 0 omitidas en Linux y Windows en cada PR
(`.github/workflows/ci.yml`). Este README no repite cifras ni estados (DRY,
[docs/metodologia.md §5.1](docs/metodologia.md#5-dry)):

- qué RF demuestra cada archivo de prueba y en qué estado está:
  [docs/plan_pruebas.md §8](docs/plan_pruebas.md);
- el número de pruebas y la cobertura, con la corrida de CI que los mide:
  [docs/plan_pruebas.md §10](docs/plan_pruebas.md);
- la evaluación de calidad sobre esos resultados: [docs/calidad_iso25010.md](docs/calidad_iso25010.md).

## Mapa del repositorio

```
core/        núcleo cerrado: contracts (estables), costing, models, catalog, budget, verification
adapters/    un paquete por dominio (civil IFC y tabular, telecom, industrial, sistemas); solo importan core.contracts
ml/          normalization, anomaly, prediction (técnica de reglas por la compuerta G2)
aplicacion/  lógica de la aplicación sin interfaz (hoja, composición, control, entrega...), la que usan la API y el asistente
api/         FastAPI; esquema OpenAPI exportado a docs/api.json; sirve la interfaz de React en /app/
frontend-desktop/  la interfaz: React + TypeScript (Vite), compilada a dist/
tests/       unit, integration, fixtures (la línea base vive en tests/fixtures/apu_linea_base.py)
data/        linea_base (evidencia primaria), samples (fuentes por dominio), precios (MaPreX jul‑2026), fuentes por dominio
docs/        ERS, plan de pruebas, calidad, manuales, arquitectura, modelo de datos, protocolos, tesis, bitácoras
scripts/     siembra, datos derivados, medición, guardias de la CI y metas de sprint (índice en scripts/README.md)
```
