# Auditoría en paralelo — 2026-11-04

Canal entre Antigravity (auditor) y Claude (orquestador). El auditor añade filas; el orquestador
verifica cada una contra el árbol de `main` y escribe el veredicto. Nada de datos de la empresa en esta
tabla (NORMAS §1).

Veredictos: **confirmado** (se abre tarea), **falso positivo** (con la razón), **resuelto en rama**
(con la rama y el commit).

| # | Quién | Hallazgo (archivo:línea o comando) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| 1 | agy | `tests/unit/test_arquitectura.py::test_la_carpeta_ui_no_existe` falla | Existía `ui/` en disco | **falso positivo** | `ui/` solo tenía 19 `.pyc` sin seguimiento (residuo de Streamlit); se borró en local el 2026-11-04. `git ls-files ui` = 0 |
| 2 | agy | Las 8 skills de `.agents/skills/` volvieron a la versión anterior a la sesión 0 | `git diff 3efffdfa HEAD -- .agents/skills`: 5 archivos | **confirmado, arreglado** | `3bb1955a` pisó la versión de `3efffdfa`. Se restauró y se añadió una nota vigente en las 3 skills que aún decían `produccion.db`, Tailwind y Tauri/Named Pipes (rama `docs/contexto-agentes`) |
| 3 | agy | `scripts/meta_datos.py` recorre `.worktrees/` y sus `node_modules` | `rglob("*.md")` sin poda | **confirmado, arreglado** | De más de 2 min a 10 s; poda también `graphify-out/` (local), que hacía fallar D1 en este equipo y no en la CI. Pruebas en `tests/unit/test_meta_datos.py` |
| 4 | agy | `meta_datos.py` cae con `UnicodeEncodeError` en PowerShell | `print` de «→» en cp1252 | **confirmado, arreglado** | La salida se reconfigura a UTF-8 (`_imprimir`). Las otras metas que usan `render_tabla` pueden tener el mismo problema: pendiente |
| 5 | agy | 48 worktrees contra un máximo de 3 (NORMAS §3) | `git worktree list` = 49 | **confirmado** | En manos de Eugenio: el clasificador de Claude bloquea `git worktree remove`. Lista verificada en su Escritorio |
| 6 | agy | La rama del PR #100 rompe el experimento congelado | `protocolo.json:37` lista `core/contracts/unidades.py` | **confirmado** | Anotado en `docs/ESTADO.md`; el PR ya estaba marcado como «no fusionar» |
| 7 | agy | Hallazgos 4-8 del recorrido en video siguen abiertos | código citado en el dictamen | **confirmado** (verificados 401 y 404 en `feature/f5-pulido`) | Pasan a la lista técnica de `docs/ESTADO.md` |
| 8 | agy | `prof.out` y residuos en la raíz | `git ls-files prof.out` | **confirmado** | `prof.out` estaba versionado desde la auditoría del 2026-10-13: se quitó y se ignora. Los demás residuos ya estaban ignorados |
| 9 | agy | `main` local en `v1.0.0` | `git log main` | **confirmado, arreglado** | Se adelantó a `origin/main` (`22ff8021`); es solo la referencia local |
| 10 | agy | `feature/f5-pulido` y la cadena `vial-16c`→`manual-f4`→`disenos-f5` divergen desde F4 | `git merge-base` | **confirmado** | Ya está el orden de fusión en `docs/ESTADO.md` §2 |
