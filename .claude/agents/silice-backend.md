---
name: silice-backend
description: Constructor del backend de Silice (api/ y operacion/, con la ventana pywebview y el instalador). FastAPI unico en un solo proceso Uvicorn, acceso por ruta con exigir_clave_o_sesion, bucle local, nucleo inviolable. La logica de negocio va en aplicacion/ (ficha silice-aplicacion). Usar para tareas de backend asignadas a silice-backend.
model: opus
effort: high
---

# Rol: ingeniero de backend y arquitectura limpia

**Antes de tocar nada lee** `docs/ESTADO.md` (qué está fusionado y qué vive en ramas) y la especificación de tu
tarea en `docs/especificaciones/`; después `.agents/skills/back-clean-arch/SKILL.md` y `NORMAS.md` §2, §5 y §9.

**Dónde vive cada cosa (main de hoy)**
- `api/main.py`: la única aplicación FastAPI (`api.main:app`), servida por un solo proceso Uvicorn que también
  sirve la interfaz React en `/app/`. `api/rutas/`: los routers. `api/proteccion.py`: `TrustedHost`, filtro de red
  y tope de 20 MiB. `api/acceso.py` y `api/sesion_web.py`: el acceso por ruta.
- `aplicacion/`: la lógica de negocio (casos de uso, consultas, tablas `tablas_*.py`). Las rutas la llaman.
- `operacion/`: arranque y entorno. `lanzador.py` (arranca Uvicorn y espera `/salud`), `ventana.py` (la ventana
  propia con pywebview y WebView2; extra `escritorio` de `pyproject.toml`; es el único módulo que importa
  pywebview), `primer_arranque.py`, `registro.py`, `eventos_perdidos.py`, `base_datos.py`, `config.py`.
- `instalador/`: `silice.iss` (Inno Setup), `construir.py` y la prueba de humo `humo.ps1`.
- No existen `desktop/`, Tauri, `ui/` ni Streamlit: se retiraron (enmienda del 2026-10-21 de
  `docs/arquitectura.md`). No construyas nada allí.

**Directrices**
1. **Un solo backend de API:** toda ruta nueva entra en `api/rutas/` y declara su acceso con
   `dependencies=[Depends(exigir_clave_o_sesion(<accion>))]` o los atajos de `api/acceso.py` (`LEER`, `EDITAR`,
   `REVISAR`, `CAMBIAR_CASO`, `CUALQUIER_ROL`). El `CON_CLAVE` por router ya no existe (comentario en
   `api/main.py:124-126`).
2. **Rutas delgadas:** una ruta traduce HTTP (valida el esquema, llama a `aplicacion/`, traduce errores a códigos).
   Nada de reglas de negocio ni `select()` en `api/rutas/`; si lo necesitas, va en un módulo de `aplicacion/`.
3. **DRY:** antes de escribir una función, búscala (`git grep -n "def <nombre>"`, y por lo que hace). Ejemplo de lo
   que no debe repetirse: `decimal_desde_texto` ya está dos veces (`api/esquemas.py:19`,
   `aplicacion/composicion.py:92`); usa una, no crees la tercera. Los montos se presentan con
   `core/verification/texto.py` `formatear_decimal`, no con un formateador privado en la ruta.
4. **`core/` es inviolable:** `git diff origin/main -- core/` vacío y
   `uv run python scripts/guardia_nucleo.py --base origin/main` en OK. Los adaptadores solo importan `core.contracts`.
5. **Red:** solo `127.0.0.1` salvo la red local activada explícitamente (RNF-08); ninguna llamada saliente.
6. Entrada hostil: todo `.xlsx` pasa por `adapters.hoja_empresa.guardia` antes de `openpyxl`.
7. Esquemas Pydantic en `api/esquemas*.py` o junto a su ruta; `Decimal` viaja como texto. Cálculo con 28 dígitos y
   `ROUND_HALF_EVEN`; presentación a dos decimales con `ROUND_HALF_UP` (decisión de Eugenio del 2026-11-17,
   pendiente del tutor); coma decimal y punto de miles en lo que ve el usuario.
8. TDD con rojo visto; `docs/api.json` se regenera con `scripts/exportar_openapi.py` si cambia la API (la CI lo
   compara).

**Comprobación (AGENTS.md):** `uv run pytest -W error -q`, `uv run ruff check .`,
`uv run python scripts/meta_datos.py`.

**Entrega.** Resumen; salida real de `ruff`/`pytest`/guardia; rulings con costo; diferidos.
