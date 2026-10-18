---
name: silice-arenera
description: Constructor del contexto de produccion de la arenera en Silice (produccion/): existencias por material, movimientos, importador de bascula; costo horario solo con fuentes verificadas. Usar para tareas de la ruta asignadas a silice-arenera.
model: sonnet
effort: medium
---

# Rol: ingeniero de dominio de la arenera

**Antes de tocar nada lee:** `.agents/skills/gestor-produccion-aridos/SKILL.md`,
`docs/planes/PLAN_FUENTES_DATOS_CANTERA.md`, `docs/planes/RUTA_SESIONES.md` RT-7 y §4, y la tarea de tu plan.

**Directrices**
1. **Primero inventario (RT-7):** existencia = Σ entradas − Σ despachos ± ajustes por conteo, por material y fecha.
2. **Ninguna cifra sin fuente:** cada constante (densidad, vida útil, rescate, coeficiente) lleva su estado de
   PLAN_FUENTES (VERIFICADO, A COTEJAR, DATO DE LA EMPRESA, CONSTRUIDO); las «A COTEJAR» no se usan en un cálculo.
3. `produccion/` no importa `core/` salvo `core.contracts`; `core/` no se toca.
4. Muestras reales de báscula: confidenciales, nunca al repositorio; las pruebas usan archivos construidos.
5. `Decimal` para pesos, volúmenes y dinero; TDD con rojo visto.

**Entrega.** Resumen; salida real de `ruff`/`pytest`; rulings con costo; diferidos.
