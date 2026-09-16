# Línea base: el presupuesto auditado

Caso de estudio: obra civil del sistema de drenaje de una clínica. Presupuesto 001 del 28/04/2026,
elaborado por el procedimiento tradicional (croquis → cómputo en hoja de cálculo → APU → presupuesto
→ plan de trabajo). Es simultáneamente la **línea base de comparación** (indicador 2) y la **evidencia
empírica del problema** (indicador 1: siete inconsistencias que el sistema debe detectar).

> **Naturaleza del caso.** Este presupuesto es un **ejercicio académico ficticio**: reproduce el
> contenido y el formato de un APU venezolano, pero no corresponde a una obra ejecutada ni sus
> valores son reales. Es la línea base normativa de las pruebas y un caso **didáctico** en la tesis.
> La naturaleza de todos los datos del repositorio se declara una sola vez en
> [CLAUDE.md §1](../CLAUDE.md#1-qué-es-este-proyecto).

| Versión | Dónde |
|---|---|
| Evidencia primaria | [`data/linea_base/APUS_CLINICA.pdf`](../data/linea_base/APUS_CLINICA.pdf) |
| Versión ejecutable (única copia de los datos) | [`tests/fixtures/apu_linea_base.py`](../tests/fixtures/apu_linea_base.py) |
| Fórmula y resumen de los cinco APU | [CLAUDE.md §4](../CLAUDE.md#4-especificación-del-cálculo-y-línea-base) |
| Pruebas de integridad de esta transcripción | [`tests/unit/test_linea_base.py`](../tests/unit/test_linea_base.py) |

## 1. Alcance físico

24 m lineales de tubería PVC de 4" en cuatro tramos (8,00 + 3,00 + 8,00 + 5,00 m) y cuatro
tanquillas de inspección de 0,80 × 0,80 × 0,80 m con paredes de 0,10 m. Cinco partidas:
excavación, tubería, encofrado, vaciado de concreto y relleno.

## 2. Memoria de cálculo declarada

| Partida | Memoria | Valor usado en el cómputo |
|---|---|---|
| Excavación | zanja 24 × 0,40 × 0,80 = 7,68 m3; fosos 4 × 0,515 = 2,06 m3 | 9,74 m3 |
| Tubería | 8 + 3 + 8 + 5 = 24 m, rotulada **3/4"** | 24 "mts" |
| Encofrado | 4 × 0,60 × 0,80 = 1,92 + 4 × 0,80 × 0,80 = 2,56 → **4,48 m2** por tanquilla | 4 × **5,92** = 23,68 "m3" |
| Concreto | 0,28 m2 × 0,80 m = **0,224 m3** por tanquilla | 4 × **0,415** = 1,66 m3 |
| Relleno | sin memoria | 1,30 m3 |

## 3. Presupuesto emitido

| N.º | Partida | Unidad del cómputo | Cantidad | PU (USD) | Total (USD) |
|---|---|---|---|---|---|
| 1 | Excavación | m3 | 9,74 | 8,60 | 83,77 |
| 2 | Tubería de 4" | mts | 24,00 | 10,19 | 244,64 |
| 3 | Encofrado | m3 | 23,68 | 33,24 | 787,07 |
| 4 | Vaciado de concreto | m3 | 1,66 | 242,64 | 402,78 |
| 5 | Relleno | m3 | 1,30 | 52,58 | 68,35 |
| | **Total** | | | | **1 586,61** |

Los totales de línea se calcularon con el precio unitario sin redondear (p. ej. 24 × 10,1934 = 244,64),
lo que confirma que el motor debe trabajar sin redondeos intermedios.

## 4. Plan de trabajo y curva de inversión emitidos

| Período | Gasto planificado | Acumulado | % |
|---|---|---|---|
| Día 1 Excavación | 82,98 | 82,98 | 5,23 |
| Día 2 Tubería | 244,56 | 327,54 | 20,64 |
| Día 3 Encofrado inicio | 389,77 | 717,31 | 45,21 |
| Día 4 Encofrado cierre | 389,78 | 1 107,09 | 69,78 |
| Día 5 Vaciado de concreto | 401,21 | 1 508,30 | 95,06 |
| Día 6 Relleno | 67,20 | 1 575,50 | **99,30** |

## 5. Las siete inconsistencias

| N.º | Hallazgo | Observado | Esperado | Impacto | Regla que lo detecta |
|---|---|---|---|---|---|
| 1 | Encofrado | 5,92 m2/tanquilla (23,68 total) | 4,48 m2/tanquilla (17,92 total) | sobreestimación del 32 %; origen de 5,92 no justificado | R1 Trazabilidad geométrica |
| 2 | Concreto | 0,415 m3/tanquilla (1,66 total) | 0,224 m3/tanquilla (0,896 total) | sobreestimación del 85 % en la partida más cara (242,64 USD/m3) | R1 Trazabilidad geométrica |
| 3 | Curva S | cierra en 1 575,50 (99,30 %) | 1 586,61 (100 %) | 11,11 USD sin conciliar | R2 Cierre de curva |
| 4 | Unidades | cómputo en "mts" | APU en "Pieza" | incompatibilidad dimensional | R3 Coherencia dimensional |
| 5 | Diámetro | 3/4" en la memoria | 4" en proyecto y APU | error de transcripción sin validación cruzada | R4 Correspondencia de especificaciones |
| 6 | Relleno | 1,30 m3 | excavación − concreto − tubería ≈ 8,6 m3 | balance volumétrico incoherente | R5 Balance volumétrico |
| 7 | Depreciación | vehículo con 0,03 en tubería y 1,00 en el resto | un factor por insumo, con criterio declarado | regla de imputación no reproducible | R6 Criterio de depreciación |

### Hallazgos adicionales (Sprint 0)

Al transcribir el PDF aparecieron dos inconsistencias más, no listadas en las Bases del anteproyecto.
No se cuentan en el indicador 1, pero las reglas las cubren:

| N.º | Hallazgo | Observado | Esperado | Regla |
|---|---|---|---|---|
| 8 | Unidad del encofrado | cómputo y presupuesto en "m3" | APU en "m2" | R3 |
| 9 | Plan de trabajo vs presupuesto | 82,98 · 779,55 · 401,21 · 67,20 por partida | 83,77 · 787,07 · 402,78 · 68,35 | R7 Conciliación presupuesto‑plan |

El hallazgo 9 explica el 3: cada monto diario es menor que el de su partida, y la suma de esas
diferencias es la brecha de 11,11 USD.

## 6. Otras observaciones del documento fuente

- El APU de tubería asigna un "Maestro Electricista" a una partida de plomería. No afecta al cálculo;
  es un dato para el módulo de normalización semántica (I2).
- El análisis financiero de la clínica (páginas 9 y 10 del PDF) rotula como "ingreso mensual" un
  ingreso diario y declara costo de insumos nulo. Está fuera del alcance, pero ilustra la misma
  patología: ausencia de verificación automática entre magnitudes relacionadas.
- El cómputo corregido completo (excavación con sobreancho y espesor de fondo, zanja con pendiente
  del 3 %, tubería con 5 % de desperdicio) se produce con las reglas paramétricas de la Sesión I3.2;
  hasta entonces solo están corregidos encofrado y concreto.
