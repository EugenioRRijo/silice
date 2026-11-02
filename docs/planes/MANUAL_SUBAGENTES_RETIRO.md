# Manual de los subagentes del retiro de Streamlit

Plan: `docs/planes/PLAN_RETIRO_STREAMLIT.md` (léelo: tu fase está en §4). Reglas del árbitro: `docs/planes/MANUAL_ARBITRO.md`. Normas: `NORMAS.md`.
Tu fase te la da el orquestador; no hagas otra. Todo en el worktree `C:\Users\euger\OneDrive\Escritorio\TESIS\.worktrees\s2m4`, rama
`inc/ruta-s2-mig-retiro-streamlit`. Hay otros agentes trabajando a la vez en la misma carpeta de trabajo: **solo tus rutas**.

## Entorno (no negociable)
- Sin worktrees, venv ni node_modules nuevos (TESIS pesa ~20 GB). Usa el venv común:
  `$env:VIRTUAL_ENV='C:\Users\euger\OneDrive\Escritorio\TESIS\.venv'; uv run --active --no-sync pytest …` (ya trae ezdxf, shapely, pdfplumber, anthropic, ollama, keyring, xlrd, streamlit).
- Antes de importar el proyecto: `SILICE_DATOS` apuntando a una carpeta temporal tuya (nunca escribir en `data/`) y `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring`.
- `pytest -W error -p no:cacheprovider -o addopts=""`; una suite grande en tandas (mitades si se cuelga). ruff check y ruff format --check de lo que toques.
- Datos reales nunca al repo; casos ficticios.

## Git
- `git commit <rutas>` con las rutas explícitas (nunca `add -A`, `commit -a`, `--amend`, `checkout`, `reset`, `stash`, `clean`, `restore`).
  Otro agente puede tener cambios sin commitear en otras rutas: no los toques.
- Asunto en español **sin tildes**; última línea `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Commits pequeños. Sin push ni PR.
- TDD: la prueba o guardia nueva va en un commit propio y la ves **en rojo** (pega la salida) antes de implementar. Los mutantes se hacen sobre una **copia** fuera del repo.

## Prohibido
`frontend-desktop/`, `api/`, `core/` (otro agente), `asistente/experimento/protocolo.json` y `congelado.json` (solo F11), la lógica del auditor
(solo imports en F7), `CHANGELOG.md`, `NORMAS.md`, `pyproject.toml`, `uv.lock`, `docs/api.json` (los toca el orquestador).
Propón su texto en el informe.

## Informe final
SHAs (rojo y verde), salida real de cada comando (pytest con conteo, ruff), conteos antes/después, qué NO hiciste y por qué, hallazgos fuera de tu fase,
texto propuesto para CHANGELOG y archivos compartidos. No digas «hecho» de lo que no corriste.

## Decisiones de Eugenio (2026-10-21, vigentes)
Un solo proceso Uvicorn y un puerto sirviendo API y front estático (`[api] activa` se ignora por compatibilidad); el asistente de IA de la Hoja queda sin
interfaz (deuda registrada, no se construye); retiro definitivo de Streamlit **y del Visor 3D** (RNF-08); sin subir versión ni etiquetar; `docs/api.json`
pierde `url_clasica`. **No toques `aplicacion/entrega.py` ni `aplicacion/hoja_*.py`** (otra sesión los edita y se rebasará encima).
