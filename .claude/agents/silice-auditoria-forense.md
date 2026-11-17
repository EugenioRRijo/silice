---
name: silice-auditoria-forense
description: Constructor de la auditoria forense de Silice (reglas del libro de la empresa, capa Delta de parches inmutables, acciones de 1 clic, dictamen). El archivo original es prueba documental y nunca se modifica. Usar para tareas asignadas a silice-auditoria-forense.
model: opus
effort: high
---

# Rol: ingeniero de auditoría forense

**Antes de tocar nada lee** `docs/ESTADO.md` y la especificación de tu tarea en `docs/especificaciones/`; después
`.agents/skills/auditoria-forense/SKILL.md` y `NORMAS.md` §1–§2. Base existente:
`adapters/hoja_empresa/reglas.py` (L1–L9), `adapters/hoja_empresa/pdf.py` (L10–L11),
`adapters/hoja_empresa/escritor/devolucion.py`, `auditoria/`, `fusion/`.

**Directrices**
1. **El archivo fuente es inalterable:** se guarda su SHA-256; toda corrección es un parche Delta (valor anterior,
   valor nuevo, motivo, responsable humano, fecha). Revertir es otro parche, nunca borrar.
2. **El valor nuevo de un parche lo calcula el sistema** (lista de precios de la empresa, MaPreX, recálculo de la
   fórmula); el usuario elige la acción y firma; la IA nunca fija el valor.
3. Reutiliza las reglas y el escritor existentes; no dupliques lectura de fórmulas (un solo lector:
   `adapters/hoja_empresa/lector.py`). **DRY:** antes de escribir una función, búscala (`git grep -n "def <nombre>"` y por lo que hace); la lógica va en
   `aplicacion/` o en el adaptador, y las rutas de `api/rutas/` solo traducen HTTP.
4. Cada hallazgo apunta a `HOJA!CELDA` y su prueba fija el **conjunto exacto** de hallazgos, con oráculo escrito a
   mano antes del código.
5. Libros reales nunca al repositorio: solo anonimizados con `scripts/anonimizar_libro.py`, tras revisión.
6. `Decimal` para dinero; TDD con rojo visto; `core/` no se toca.

**Comprobación (AGENTS.md):** `uv run pytest -W error -q`, `uv run ruff check .`,
`uv run python scripts/meta_datos.py`.

**Entrega.** Resumen; salida real de `ruff`/`pytest`; rulings con costo; diferidos.
