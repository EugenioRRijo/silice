---
name: front-carbon-fiori-ibcs
description: >-
  Estándares de Frontend Desktop para Sílice: IBM Carbon oficial (@carbon/react y
  @carbon/styles, sin Tailwind), métricas analíticas SAP Fiori y semántica de variación
  de negocio IBCS sobre React 19, TypeScript y el lienzo de Univer (@univerjs/presets).
---

# Skill: Frontend Desktop Sílice (Carbon + Fiori + IBCS)

> **Vigente al 2026-11-17.** La fuente única del aspecto es
> [frontend-desktop/DESIGN.md](../../../frontend-desktop/DESIGN.md) (y sus valores exactos,
> [src/estilos/tokens.scss](../../../frontend-desktop/src/estilos/tokens.scss)): si esta guía lo contradice, manda
> DESIGN.md. Sin Tailwind (RT-8). La interfaz la sirve el mismo Uvicorn de la API en `/app/` y la ventana de
> escritorio es `operacion/ventana.py` (pywebview); no hay Tauri. Estado del proyecto:
> [docs/ESTADO.md](../../../docs/ESTADO.md).

Esta guía resume las reglas de la interfaz de `frontend-desktop/` (React 19 + TypeScript + Vite) y enlaza el código que
ya las cumple. **Reutiliza ese código: no lo copies ni escribas otra versión** (la CI corre jscpd con umbral de 1 % y
knip).

**Comandos (AGENTS.md), en `frontend-desktop/`:** `npm run lint; npx vitest run --maxWorkers=3`; antes de entregar,
`npm run build`.

---

## 1. IBM Carbon Design System (Densidad y Severidad)

Las aplicaciones de presupuestos y obras manejan cientos de filas y columnas. Se adopta **IBM Carbon** (tema g10,
paquetes oficiales) para maximizar la información visible sin fatiga visual.

### 1.1. Densidades de Tabla
* **Ultra-Compacta (`compact` - 24px):** la hoja de Univer replica la altura de fila del libro.
* **Estándar de Inspección (`sm` - 32px):** tablas de hallazgos de auditoría y catálogos de partidas.
* **Espaciado Táctil (48px):** solo donde la especificación lo pide (controles de campo).

### 1.2. Severidad: cuatro niveles
La fuente es [src/severidad/severidad.ts](../../../frontend-desktop/src/severidad/severidad.ts) (`SEVERIDADES`,
`estiloDeSeveridad`, `normalizarSeveridad`); cada nivel trae su token, su ícono de Carbon y su texto:

| Nivel | Token | Color Carbon | Ícono |
|---|---|---|---|
| `CRITICO` | `--silice-sev-critico` | Red 60 | `ErrorFilled` |
| `ERROR` | `--silice-sev-error` | Orange 50 (naranja) | `WarningFilled` |
| `ADVERTENCIA` | `--silice-sev-advertencia` (ícono: `--silice-sev-advertencia-icono`) | Yellow 30 (ícono Yellow 50) | `WarningAltFilled` |
| `INFO` | `--silice-sev-info` | Blue 60 | `InformationFilled` |

* **Atípicos del detector:** `--silice-atipico` (Purple 60), exclusivo de lo que marca *Isolation Forest* en
  `ml/anomaly/detector.py` (`UMBRAL_ATIPICO = -0.05`, más negativo = más atípico; se abstiene con menos de
  `MINIMO_OBSERVACIONES = 8` y entonces no hay halo). El hallazgo es ADVERTENCIA, nunca ERROR.
* **Verificado:** `--silice-verificado` (Green 50).

### 1.3. Dos semánticas que no se mezclan
* **Halos de la hoja = severidad**, siempre con **ícono** y texto accesible: el color nunca va solo (WCAG 2.1 AA).
* **Rojo/verde IBCS = variación favorable/desfavorable**, solo en cifras de variación (tarjetas Fiori y gráficos),
  con los tokens `--silice-ibcs-favorable-texto`, `--silice-ibcs-desfavorable` y `--silice-ibcs-neutro`. Una celda con
  fórmula rota (severidad) y un precio caro (variación) no se pintan con el mismo significado.

---

## 2. SAP Fiori (Métricas Analíticas y Tarjetas KPI)

Cada indicador clave sigue el patrón de **SAP Fiori**: valor actual, meta o referencia, y desviación
($\Delta = \text{Actual} - \text{Meta}$, $\Delta\% = \Delta / \text{Meta} \times 100$). Los montos y las
variaciones **los calcula la API** (`Decimal` como texto); la interfaz no recalcula dinero, solo formatea.

Código que ya lo hace (úsalo):
* [src/indicadores/IndicadorFiori.tsx](../../../frontend-desktop/src/indicadores/IndicadorFiori.tsx): la tarjeta
  (valor, meta, Δ y Δ %, flecha e ícono con texto accesible). Su franja: `FranjaIndicadores.tsx`.
* [src/indicadores/ibcs.ts](../../../frontend-desktop/src/indicadores/ibcs.ts): `semanticaIbcs(delta, sentido)`
  decide favorable, desfavorable o neutro leyendo el signo del texto, sin `Number()`.
* [src/indicadores/formatoEsVe.ts](../../../frontend-desktop/src/indicadores/formatoEsVe.ts): coma decimal y punto
  de miles (`formatoEsVe`, `formatoMontoEsVe`, `cantidadEsVe`, `fechaEsVe`). Ninguna cifra se muestra sin pasar por
  aquí.
* [src/estilos/tokens.scss](../../../frontend-desktop/src/estilos/tokens.scss): los colores; nada de hexadecimales
  sueltos en un componente.

---

## 3. IBCS (International Business Communication Standards)

En Sílice se aplica rigurosamente la regla semántica de color de **IBCS** para evitar interpretaciones erróneas en auditoría y control de costos:

### 3.1. Semántica Favorable / Desfavorable vs. Positivo / Negativo
> [!IMPORTANT]
> **NUNCA colorear en verde simplemente porque un número sea positivo (+), ni en rojo porque sea negativo (-).**
> El color debe expresar exclusivamente el **impacto económico sobre el presupuesto**:

| Métrica | Comportamiento | Signo Matemático | Semántica IBCS | Color IBCS |
|---|---|---|---|---|
| **Costo de Partida / Insumo** | El costo subió frente a la cantera/tabulador | $+$ Positivo | **Desfavorable** (Sobrecosto) | 🔴 **Rojo** (`--silice-ibcs-desfavorable`) |
| **Costo de Partida / Insumo** | El costo bajó frente al tabulador | $-$ Negativo | **Favorable** (Ahorro) | 🟢 **Verde** (`--silice-ibcs-favorable-texto`) |
| **Rendimiento de Cuadrilla** | Cuadrilla produce más m³/día | $+$ Positivo | **Favorable** (Mayor avance) | 🟢 **Verde** (`--silice-ibcs-favorable-texto`) |
| **Tiempo de Ciclo de Camiones** | Camión tarda menos minutos en acarreo | $-$ Negativo | **Favorable** (Mayor eficiencia) | 🟢 **Verde** (`--silice-ibcs-favorable-texto`) |
| **Producción de Arena en Zaranda** | Menor volumen al esperado | $-$ Negativo | **Desfavorable** (Pérdida en planta) | 🔴 **Rojo** (`--silice-ibcs-desfavorable`) |

### 3.2. Representación Visual de Datos
* **Valores Reales / Actuales (AC):** Barras o números con relleno **sólido**.
* **Valores Presupuestados / Plan (PL):** Barras o cajas con **contorno** (outline).
* **Pronósticos / Reproyecciones (FC):** relleno **achurado** (por ejemplo, la reproyección del valor ganado). Plan y pronóstico no comparten notación.
