---
name: gestor-produccion-aridos
description: >-
  Bounded Context de Producción de Canteras y Áridos: costos horarios de maquinaria pesada
  (Caterpillar/USBR), balance de masa en trituración, conectores de báscula y derivación de $/m³.
---

# Skill: Gestor de Producción de Canteras y Áridos

Esta guía establece el modelado operativo para empresas de extracción de arena, grava, piedra picada y sub-bases granulares dentro de Sílice.

> [!IMPORTANT]
> **Orden de construcción (ruta, RT-7):** primero **existencias** (cuánto hay y cuánto queda de cada material: entradas de producción, despachos de báscula y ajustes por conteo). El costo horario de §1 se construye **solo** cuando sus fórmulas y constantes estén VERIFICADO en [`docs/planes/PLAN_FUENTES_DATOS_CANTERA.md`](../../../docs/planes/PLAN_FUENTES_DATOS_CANTERA.md). Toda cifra de esta guía es un **ejemplo construido** salvo que diga otra cosa.

---

## 1. El Costo Horario de Maquinaria Pesada (Caterpillar Performance Handbook)

El costo de cada metro cúbico de árido depende fundamentalmente del costo horario ($C_H$) de la flota pesada (retroexcavadoras, cargadores frontales, tractores de oruga y trituradoras móviles).

### Fórmulas Estándar:
$$C_H = C_{\text{posesión}} + C_{\text{operación}}$$

1. **Costo de Posesión ($/h)** — fórmula **A COTEJAR** (PLAN_FUENTES F-1, F-2):
   $$C_{\text{posesión}} = \frac{V_a - V_r}{V_u} + \frac{V_a \cdot (i + s + t)}{H_a}$$
   * $V_a$: Valor de compra; $V_r$: Valor de rescate; $V_u$: Vida útil en horas. Rescate y vida útil son **dato de la empresa** por equipo (PLAN_FUENTES C-4); no hay valor por defecto.
   * $i, s, t$: Tasas de interés bancario, seguros contra todo riesgo e impuestos; $H_a$: Horas trabajadas por año.
   * **Probable error a cotejar (F-2):** la bibliografía de equipos (Peurifoy et al.) aplica $i+s+t$ sobre la **inversión media anual**, no sobre $V_a$.
2. **Costo de Operación ($/h):**
   $$C_{\text{operación}} = (Q_{\text{diésel}} \times P_{\text{diésel}}) + C_{\text{lubricantes}} + C_{\text{desgaste}} + C_{\text{operador}}$$
   * **Desgaste Crítico:** Monitorea el recambio de mallas en zarandas vibratorias y muelas de trituradoras de mandíbula por hora de impacto en roca dura.

---

## 2. Balance de Masa y Derivación del Costo Unitario ($/m³ o $/ton)

Una tonelada de roca bruta (*Run-of-Mine* / ROM) ingresada a la tolva primaria se clasifica en la zaranda en distintas fracciones comerciales (arena, piedra picada 1/2", 3/4", 1", polvillo; tamaños A COTEJAR con ASTM C33 / COVENIN 277, PLAN_FUENTES C-7).

El costo operativo acumulado del turno de planta se reparte entre los coproductos (costos conjuntos, PLAN_FUENTES F-4): **por masa (t) por defecto**; por valor de venta solo con los precios de la empresa. No se usan coeficientes fijos de valor (los 1,15/1,00/0,85 de versiones anteriores no tenían fuente y se retiraron, C-3). El resultado es el **Costo Real de Producción** que alimenta la lista de precios de la empresa:
```text
Ejemplo construido (ficticio): Arena lavada en cantera = 18,50 $/m³; Piedra picada 3/4" = 16,20 $/m³
```

---

## 3. Conector de Báscula Camionera y Partes de Campo

1. **Importador de Báscula:** Mapea automáticamente hojas de cálculo generadas por básculas de salida (Toledo, Cardinal) extrayendo: *Ticket*, *Fecha*, *Placa*, *Material* y *Peso Neto*.
2. **Tarjetas Táctiles de Maquinaria:** Formularios de 3 datos para operadores en el frente de cantera:
   - *Horómetro inicial/final*
   - *Galones de diésel cargados*
   - *Incidencias / Paradas de mantenimiento*
