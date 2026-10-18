---
name: replicacion-excel
description: >-
  Motor de Réplica Visual de Hojas de Cálculo: extracción dual de fórmulas con openpyxl,
  detección de celdas quemadas, mapeo de coordenadas visuales y renderizado en Canvas con Univer.
---

# Skill: Réplica Visual de Hojas de Cálculo (Excel / Univer)

Esta guía establece el protocolo para transformar presupuestos en formato `.xlsx`/`.xlsm` en réplicas interactivas auditables sobre la interfaz desktop.

---

## 1. El Algoritmo de Extracción Dual (Fórmulas vs. Valores)

En auditoría forense de obras civiles, una práctica común de fraude o descuido es escribir un número fijo en la celda del monto total en lugar de aplicar la multiplicación $\text{Cantidad} \times \text{Precio Unitario}$ o una suma de partidas.

### Protocolo de Extracción en Backend (ya construido: no se escribe otro parser)

> [!IMPORTANT]
> La extracción dual **ya existe** en `adapters/hoja_empresa/lector.py` (ruta RT-6): el libro pasa primero por
> `adapters/hoja_empresa/guardia.py` (tamaño, bombas zip), se abre en **solo lectura** dos veces (fórmulas y valores
> guardados con `data_only=True`), cada dato se busca **por rótulo, nunca por fila o columna fija** (los APU de la
> empresa tienen más de diez formas) y todo número es `Decimal(str(v))`. Las reglas L1–L9
> (`adapters/hoja_empresa/reglas.py`) comparan lo que el libro *dice* con lo que *calcula*, y cada hallazgo apunta a
> `HOJA!CELDA`. Una «celda quemada» (un número donde la plantilla espera una fórmula) es una de esas reglas, no un
> `col == 6` fijo.

Lo único nuevo para la réplica es el **aspecto** (`adapters/hoja_empresa/visual.py`): relleno, fuente, bordes,
alineación, formato numérico, combinadas, anchos y altos. En solo lectura openpyxl no da combinadas ni dimensiones,
así que `visual.py` hace una **tercera apertura en modo normal** (~7 s por libro, costo declarado en RT-6), siempre
después de la guardia y sin escribir nunca sobre el original.

---

## 2. Renderizado en Lienzo Univer (`<canvas>`)

* **No usar DOM masivo (`<table>` o `<div>`):** Renderizar 30.000 celdas mediante nodos HTML satura la memoria y congela la UI.
* **Integración con Univer:**
  * Se utiliza `@univerjs/core` y `@univerjs/sheets`.
  * Toda la cuadrícula se dibuja sobre un único `<canvas>` con aceleración WebGL/2D.
  * Los halos de severidad (verde, amarillo, rojo, morado) y popovers de auditoría se proyectan en una capa flotante sincronizada con las coordenadas del viewport.
