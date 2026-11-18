---
name: replicacion-excel
description: >-
  Motor de Réplica Visual de Hojas de Cálculo: un solo lector de dos pasadas
  (adapters/hoja_empresa/lector.py) tras la guardia, reglas L1-L9 sobre lo leído, aspecto de
  celdas en visual.py y renderizado en Canvas con Univer (@univerjs/presets).
---

# Skill: Réplica Visual de Hojas de Cálculo (Excel / Univer)

> **Vigente al 2026-11-17.** El código ya existe: esta guía enlaza los módulos en vez de dar ejemplos. Un segundo
> parser de Excel está prohibido (RT-6). Estado del proyecto: [docs/ESTADO.md](../../../docs/ESTADO.md).

Esta guía establece el protocolo para transformar presupuestos en formato `.xlsx` en réplicas interactivas auditables
sobre la interfaz.

---

## 1. Entrada, lectura dual y reglas (backend)

En auditoría forense de obras civiles, una práctica común de fraude o descuido es escribir un número fijo en la celda
del monto total en lugar de aplicar la multiplicación $\text{Cantidad} \times \text{Precio Unitario}$ o una suma de
partidas. Sílice lo detecta comparando lo que el libro **dice** (sus fórmulas) con lo que **calcula** (sus valores
guardados). El camino es siempre el mismo y no se duplica:

1. **Guardia:** [adapters/hoja_empresa/guardia.py](../../../adapters/hoja_empresa/guardia.py), `verificar_archivo`.
   Todo libro que viene de fuera pasa por aquí antes de openpyxl (macros renombradas, ZIP malformado, bombas de
   descompresión, áreas desmedidas); si no, `ArchivoRechazado`.
2. **Lector (el único):** [adapters/hoja_empresa/lector.py](../../../adapters/hoja_empresa/lector.py), `leer_libro`.
   Dos lecturas del mismo archivo (fórmulas y `data_only`), por rótulo y nunca por fila fija, todo dato con su
   `Celda`, números con `Decimal(str(v))` (nunca `float`), y topes por hoja y por libro (`filas_acotadas`).
3. **Reglas L1-L9:** [adapters/hoja_empresa/reglas.py](../../../adapters/hoja_empresa/reglas.py),
   `reglas_del_libro` y la tabla `REGLAS_LIBRO` (por ejemplo, L3 «Valor guardado ≠ fórmula»). Qué caso cubre cada
   regla lo dice el docstring del módulo; antes de proponer una regla nueva, confirma que ninguna de las nueve lo
   cubre. Cada hallazgo apunta a `HOJA!CELDA`.
4. **Aspecto:** [adapters/hoja_empresa/visual.py](../../../adapters/hoja_empresa/visual.py), `replicar_libro`
   (relleno, fuente, bordes, alineación, formato numérico, combinadas, anchos, altos, ocultas, paneles fijos). Si hace
   falta un atributo visual más, se añade aquí, no en un lector nuevo.

Antes de escribir una función en este paquete, búscala (`git grep -n "def <nombre>" adapters/hoja_empresa`).

---

## 2. Renderizado en Lienzo Univer (`<canvas>`)

* **No usar DOM masivo (`<table>` o `<div>`):** Renderizar 30.000 celdas mediante nodos HTML satura la memoria y
  congela la UI.
* **Integración con Univer:** se usa `@univerjs/presets` (y `@univerjs/preset-sheets-core`), con versiones exactas
  en `frontend-desktop/package.json`; no `@univerjs/sheets` suelto y nunca `@univerjs-pro`.
  * El paso de `LibroVisual` al modelo de Univer está en `frontend-desktop/src/replica/aUniver.ts`; la conversión de
    coordenadas base 1 (Excel) a base 0 (Univer), en un solo lugar: `frontend-desktop/src/replica/coordenadas.ts`.
  * El montaje del lienzo está en `frontend-desktop/src/visor/adaptadorUniver.ts`.
  * Los halos de severidad (cuatro niveles de `src/severidad/severidad.ts`, y morado para atípicos) y los popovers de
    auditoría se proyectan en una capa flotante sincronizada con las coordenadas del viewport.
