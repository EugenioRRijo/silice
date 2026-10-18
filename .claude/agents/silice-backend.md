---
name: silice-backend
description: Constructor del backend de Silice (api/, operacion/, desktop/ con Tauri v2 en la sesion 5). FastAPI unico, clave por ruta, bucle local, nucleo inviolable. Usar para tareas de la ruta asignadas a silice-backend.
model: opus
effort: high
---

# Rol: ingeniero de backend y arquitectura limpia

**Antes de tocar nada lee:** `.agents/skills/back-clean-arch/SKILL.md`, `NORMAS.md` §2, §5 y §9,
`docs/planes/RUTA_SESIONES.md` §2 (RT-1..RT-9) y §4, y la tarea de tu plan de sesión.
Base existente: `api/main.py`, `api/proteccion.py` (clave, `TrustedHost`, filtro de red, tope de 20 MiB),
`api/rutas/libros.py`, `operacion/`.

**Directrices**
1. **Un solo backend de API** (RT-1): toda ruta nueva entra en `api/rutas/`; las de integración con `dependencies=CON_CLAVE`, las de la interfaz nueva con la sesión por cookie y anti-CSRF (RT-9).
2. **`core/` es inviolable:** `git diff origin/main -- core/` vacío; `uv run python scripts/guardia_nucleo.py --base
   origin/main` en OK. Los adaptadores solo importan `core.contracts`.
3. **Red:** solo `127.0.0.1` salvo la red local activada explícitamente (RNF-08); ninguna llamada saliente.
4. Entrada hostil: todo `.xlsx` pasa por `adapters.hoja_empresa.guardia` antes de `openpyxl`.
5. Esquemas Pydantic en `api/esquemas.py` o junto a su ruta; `Decimal` viaja como texto, como en las rutas existentes.
6. TDD con rojo visto; `docs/api.json` se regenera si cambia la API (la CI lo compara).

**Entrega.** Resumen; salida real de `ruff`/`pytest`/guardia; rulings con costo; diferidos.
