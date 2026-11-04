# AGENTS.md — entrada para agentes de IA (Antigravity, Codex, Claude y otros)

Este repositorio es **Sílice**, el sistema de APU del trabajo de grado de Eugenio. Tiene meses de
historia y muchos documentos que describen **fases ya cerradas**. Antes de opinar sobre el estado del
proyecto, lee en este orden:

1. **[docs/ESTADO.md](docs/ESTADO.md)**: qué está fusionado, qué vive en ramas, qué falta y qué espera
   una decisión de Eugenio. Es la única fuente del estado actual. Si otro documento lo contradice,
   manda `ESTADO.md`.
2. **[NORMAS.md](NORMAS.md)**: la constitución (principios, cálculo, contratos, reglas, compuertas).
3. **[README.md](README.md)** y **[docs/README.md](docs/README.md)**: arranque e índice de la documentación.

## Qué está vigente y qué es historia

| Vigente (describe el programa de hoy) | Histórico (solo para saber *por qué* algo es así) |
|---|---|
| [docs/ESTADO.md](docs/ESTADO.md), [NORMAS.md](NORMAS.md), [README.md](README.md), [CHANGELOG.md](CHANGELOG.md) | Todos los `PLAN_*.md` de la raíz (ver abajo) |
| [docs/ERS.md](docs/ERS.md), [docs/arquitectura.md](docs/arquitectura.md), [docs/modelo_datos.md](docs/modelo_datos.md): **léelos con sus enmiendas** (la de 2026-10-21 retiró Streamlit) | [docs/planes/](docs/planes/): planes de fases cerradas; el estado de cada uno lo dice `ESTADO.md` |
| [docs/especificaciones/](docs/especificaciones/): diseños aprobados, cada uno con su fecha | [docs/bitacora/](docs/bitacora/): registro fechado; dice lo que se sabía *ese día* |
| [.agents/skills/](.agents/skills/): guías por área (núcleo, front, base de datos, pruebas) | `.worktrees/` y `.claude/worktrees/`: copias de ramas viejas; **no son el programa actual** |

Planes de la raíz, **todos cerrados**: PLAN_DESARROLLO.md, PLAN_MULTIDOMINIO.md, PLAN_PROTOTIPO.md,
PLAN_UI.md, PLAN_ASISTENTE.md, PLAN_CIERRE.md, PLAN_SF.md, PLAN_SILICE_060.md, PLAN_SILICE_070.md,
PLAN_SILICE_080.md, PLAN_SILICE_090.md, PLAN_SILICE_100.md, PLAN_SILICE_150.md, PLAN_SILICE_UI.md.
No se mueven porque los scripts de metas (`scripts/meta_*.py`) y algunas pruebas los leen por nombre.

## Hechos que un documento viejo puede contradecir

- **Streamlit ya no existe.** La interfaz es React (`frontend-desktop/`) servida por un solo proceso
  Uvicorn (`api.main:app`). La lógica que vivía en `ui/` está en `aplicacion/`. Una carpeta `ui/` en
  disco con solo `__pycache__` es residuo local, no un defecto del repositorio.
- **`main` es el programa completo** desde el 2026-11-02 (PR #98). El trabajo nuevo vive en ramas
  `feature/*` con su PR; Eugenio fusiona en GitHub.
- **Coma decimal y punto de miles** en toda entrada y salida numérica.

## Reglas que no se negocian

- **Datos reales nunca al repositorio.** Los libros de la empresa, lo anonimizado y lo derivado viven
  solo en el equipo (NORMAS §1). Los `.docx` y `.pdf` sueltos de la raíz son documentos de trabajo de
  Eugenio: no se copian, no se citan en commits ni se suben. Las pruebas usan casos construidos.
- **`core/` no cambia** sin expediente y aval del tutor (`scripts/guardia_nucleo.py` lo vigila en la CI).
- **TDD:** prueba en rojo antes del código; suite completa al cerrar una fase.

## Cómo comprobar algo antes de reportarlo

```powershell
uv run pytest -W error -q                 # suite de Python
uv run ruff check .                       # estilo
uv run python scripts/meta_datos.py       # naturaleza de los datos (D1-D4)
cd frontend-desktop; npm run lint; npx vitest run --maxWorkers=3
```

Un hallazgo vale cuando cita `archivo:línea` del árbol actual (no de un worktree) y, si es una prueba
que falla, la salida literal.

## Si trabajas en paralelo con otro agente

Anota cada hallazgo en `docs/bitacora/auditoria-agy-AAAA-MM-DD.md` con el formato de
[docs/bitacora/auditoria-agy-2026-11-04.md](docs/bitacora/auditoria-agy-2026-11-04.md). El otro agente
lo verifica contra el código y escribe su veredicto en la misma fila. No edites código que otro agente
tenga abierto en ese momento.
