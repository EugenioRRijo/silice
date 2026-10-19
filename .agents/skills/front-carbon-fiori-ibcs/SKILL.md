---
name: front-carbon-fiori-ibcs
description: >-
  Estándares de Frontend Desktop para Sílice: integración de diseño de alta densidad
  IBM Carbon, métricas analíticas SAP Fiori y semántica de variación de negocio IBCS
  sobre React 19, TypeScript, Tailwind CSS y lienzo Canvas Univer.
---

# Skill: Frontend Desktop Sílice (Carbon + Fiori + IBCS)

Esta guía define las especificaciones obligatorias para la interfaz de usuario de escritorio en Sílice (Tauri v2 + React 19 + TypeScript + Vite).

---

## 1. IBM Carbon Design System (Densidad y Severidad)

Las aplicaciones de presupuestos y obras manejan cientos de filas y columnas. Se adopta **IBM Carbon** para maximizar la cantidad de información visible sin fatiga visual:

### 1.1. Densidades de Tabla
* **Ultra-Compacta (`compact` - 24px):** Utilizada en el Visor Réplica de Excel (Univer Canvas Grid) y matrices de APU detalladas.
* **Estándar de Inspección (`short` - 32px):** Utilizada en tablas de hallazgos de auditoría y catálogos de partidas.
* **Espaciado Táctil (`tall` - 48px):** Reservada exclusivamente para las **Tarjetas de Maquinaria** y formularios rápidos de campo.

### 1.2. Paleta de Severidad y Estados de Auditoría
* 🟢 **Verificado / Cumple:** `Green-50` (`#24a148`) — Valor matemáticamente exacto y dentro del tabulador normativo.
* 🟡 **Advertencia Menor:** `Yellow-30` (`#f1c21b`) — Desviación de rendimiento leve o datos incompletos no bloqueantes.
* 🔴 **Error Crítico / Falla:** `Red-60` (`#da1e28`) — Fórmula alterada, omisión de celdas intermedias o violación de normativa.
* 🔵 **Informativo / Metadato:** `Blue-60` (`#0f62fe`) — Celdas con fórmulas externas no resueltas o notas de usuario.
* 🟣 **Precios y Rendimientos Atípicos (ML Outliers):** **`Purple-60` (`#8a3ffc`)**
  * **Regla estricta:** Todo insumo, precio unitario o rendimiento detectado como valor atípico por el modelo *Isolation Forest* de `ml/anomaly/` se resalta con **borde o halo morado Carbon** (`#8a3ffc`), acompañado del tooltip: *"[ML] Precio atípico detectado: puntuación de anomalía > 0.65"*.

---

## 2. SAP Fiori (Métricas Analíticas y Tarjetas KPI)

Para las cabeceras de presupuesto, resúmenes de auditoría y tableros de control de planta de áridos, cada indicador clave de desempeño (KPI Card) debe seguir el patrón de **SAP Fiori**:

### Estructura Mandatoria de Cada Indicador:
1. **Valor Actual (Actual Value):** Cifra real medida o presupuesto evaluado en tipografía grande (`text-2xl font-semibold`).
2. **Meta / Benchmark (Target):** Valor de referencia (Línea base, costo de cantera o tabulador oficial) en tipografía secundaria (`text-sm text-muted-foreground`).
3. **Desviación ($\Delta$ y $\Delta\%$):** Variación numérica y porcentual calculada:
   $$\Delta = \text{Valor Actual} - \text{Valor Meta}, \quad \Delta\% = \frac{\Delta}{\text{Valor Meta}} \times 100$$

```tsx
// Ejemplo de Tarjeta Fiori en React + Tailwind
export function IndicadorFiori({ titulo, actual, meta, unidad, esCosto }) {
  const delta = actual - meta;
  const deltaPct = (delta / meta) * 100;
  // IBCS: Si es costo, un incremento (+delta) es DESFAVORABLE (Rojo)
  const esFavorable = esCosto ? delta <= 0 : delta >= 0;

  return (
    <div className="p-4 border rounded-md bg-card shadow-sm">
      <span className="text-xs uppercase tracking-wider text-muted-foreground">{titulo}</span>
      <div className="flex items-baseline justify-between mt-1">
        <span className="text-2xl font-bold font-mono">{actual.toFixed(2)} {unidad}</span>
        <span className={`text-sm font-semibold font-mono px-2 py-0.5 rounded ${
          esFavorable ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
        }`}>
          {delta >= 0 ? '+' : ''}{deltaPct.toFixed(1)}%
        </span>
      </div>
      <div className="mt-2 text-xs text-muted-foreground flex justify-between">
        <span>Meta: {meta.toFixed(2)} {unidad}</span>
        <span>Dif: {delta >= 0 ? '+' : ''}{delta.toFixed(2)} {unidad}</span>
      </div>
    </div>
  );
}
```

---

## 3. IBCS (International Business Communication Standards)

En Sílice se aplica rigurosamente la regla semántica de color de **IBCS** para evitar interpretaciones erróneas en auditoría y control de costos:

### 3.1. Semántica Favorable / Desfavorable vs. Positivo / Negativo
> [!IMPORTANT]
> **NUNCA colorear en verde simplemente porque un número sea positivo (+), ni en rojo porque sea negativo (-).**
> El color debe expresar exclusivamente el **impacto económico sobre el presupuesto**:

| Métrica | Comportamiento | Signo Matemático | Semántica IBCS | Color IBCS |
|---|---|---|---|---|
| **Costo de Partida / Insumo** | El costo subió frente a la cantera/tabulador | $+$ Positivo | **Desfavorable** (Sobrecosto) | 🔴 **Rojo** (`#da1e28`) |
| **Costo de Partida / Insumo** | El costo bajó frente al tabulador | $-$ Negativo | **Favorable** (Ahorro) | 🟢 **Verde** (`#24a148`) |
| **Rendimiento de Cuadrilla** | Cuadrilla produce más m³/día | $+$ Positivo | **Favorable** (Mayor avance) | 🟢 **Verde** (`#24a148`) |
| **Tiempo de Ciclo de Camiones** | Camión tarda menos minutos en acarreo | $-$ Negativo | **Favorable** (Mayor eficiencia) | 🟢 **Verde** (`#24a148`) |
| **Producción de Arena en Zaranda** | Menor volumen al esperado | $-$ Negativo | **Desfavorable** (Pérdida en planta) | 🔴 **Rojo** (`#da1e28`) |

### 3.2. Representación Visual de Datos
* **Valores Reales / Actuales:** Barras o números con relleno **sólido** (`fill-current` oscuro).
* **Valores Presupuestados / Metas:** Barras o cajas con **contorno o achurado** (outline), diferenciando inmediatamente lo que ocurrió de lo que se planificó.
