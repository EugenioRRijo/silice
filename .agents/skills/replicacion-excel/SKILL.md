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

### Protocolo de Extracción en Backend:
```python
import openpyxl


def extraer_libro_dual(ruta_archivo: Path):
    # Pasada 1: Lee las fórmulas exactas escritas por el autor
    wb_formulas = openpyxl.load_workbook(ruta_archivo, data_only=False)
    # Pasada 2: Lee el valor numérico calculado y guardado en la caché de Excel
    wb_valores = openpyxl.load_workbook(ruta_archivo, data_only=True)

    for hoja in wb_formulas.sheetnames:
        sheet_f = wb_formulas[hoja]
        sheet_v = wb_valores[hoja]

        for fila in range(1, sheet_f.max_row + 1):
            for col in range(1, sheet_f.max_column + 1):
                val_formula = sheet_f.cell(row=fila, column=col).value
                val_calculado = sheet_v.cell(row=fila, column=col).value

                # Detección de "celda quemada": si es columna de total y no tiene fórmula
                es_total = col == 6  # Ejemplo: Columna Total
                if es_total and isinstance(val_formula, (int, float)):
                    registrar_hallazgo_celda_quemada(hoja, fila, col, val_formula)
```

---

## 2. Renderizado en Lienzo Univer (`<canvas>`)

* **No usar DOM masivo (`<table>` o `<div>`):** Renderizar 30.000 celdas mediante nodos HTML satura la memoria y congela la UI.
* **Integración con Univer:**
  * Se utiliza `@univerjs/core` y `@univerjs/sheets`.
  * Toda la cuadrícula se dibuja sobre un único `<canvas>` con aceleración WebGL/2D.
  * Los halos de severidad (verde, amarillo, rojo, morado) y popovers de auditoría se proyectan en una capa flotante sincronizada con las coordenadas del viewport.
