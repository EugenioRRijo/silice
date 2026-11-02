---
name: gestor-produccion-aridos
description: >-
  Bounded Context de Producción de Canteras y Áridos: costos horarios de maquinaria pesada
  (Caterpillar/USBR), balance de masa en trituración, conectores de báscula y derivación de $/m³.
---

# Skill: Gestor de Producción de Canteras y Áridos

Esta guía establece el modelado operativo para empresas de extracción de arena, grava, piedra picada y sub-bases granulares dentro de Sílice.

---

## 1. El Costo Horario de Maquinaria Pesada (Caterpillar Performance Handbook)

El costo de cada metro cúbico de árido depende fundamentalmente del costo horario ($C_H$) de la flota pesada (retroexcavadoras, cargadores frontales, tractores de oruga y trituradoras móviles).

### Fórmulas Estándar:
$$C_H = C_{\text{posesión}} + C_{\text{operación}}$$

1. **Costo de Posesión ($/h):**
   $$C_{\text{posesión}} = \frac{V_a - V_r}{V_u} + \frac{V_a \cdot (i + s + t)}{H_a}$$
   * $V_a$: Valor de compra; $V_r$: Valor de rescate (típicamente 20%); $V_u$: Vida útil en horas (ej. 10.000 h).
   * $i, s, t$: Tasas de interés bancario, seguros contra todo riesgo e impuestos; $H_a$: Horas trabajadas por año.
2. **Costo de Operación ($/h):**
   $$C_{\text{operación}} = (Q_{\text{diésel}} \times P_{\text{diésel}}) + C_{\text{lubricantes}} + C_{\text{desgaste}} + C_{\text{operador}}$$
   * **Desgaste Crítico:** Monitorea el recambio de mallas en zarandas vibratorias y muelas de trituradoras de mandíbula por hora de impacto en roca dura.

---

## 2. Balance de Masa y Derivación del Costo Unitario ($/m³ o $/ton)

Una tonelada de roca bruta (*Run-of-Mine* / ROM) ingresada a la tolva primaria se clasifica en la zaranda en distintas fracciones comerciales:
* **Arena Lavada (0-4 mm):** Coeficiente de valor 1.15
* **Piedra Picada 1/2" y 3/4":** Coeficiente de valor 1.00 (Base)
* **Piedra Picada 1" y Polvillo:** Coeficiente de valor 0.85

El costo operativo acumulado del turno de planta se reparte entre los metros cúbicos obtenidos, generando el **Costo Real de Producción** que alimenta directamente el catálogo de insumos de Sílice:
```text
Costo Unitario Arena Lavada en Cantera = $18.50 / m³
Costo Unitario Piedra Picada 3/4" = $16.20 / m³
```

---

## 3. Conector de Báscula Camionera y Partes de Campo

1. **Importador de Báscula:** Mapea automáticamente hojas de cálculo generadas por básculas de salida (Toledo, Cardinal) extrayendo: *Ticket*, *Fecha*, *Placa*, *Material* y *Peso Neto*.
2. **Tarjetas Táctiles de Maquinaria:** Formularios de 3 datos para operadores en el frente de cantera:
   - *Horómetro inicial/final*
   - *Galones de diésel cargados*
   - *Incidencias / Paradas de mantenimiento*
