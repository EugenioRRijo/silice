# Memoria S2: la obra OB-S2 (oráculo de RF-72 a RF-79, spec S2 §7.1)

Escrita a mano **antes del código**, con cada paso intermedio; las pruebas comparan con esta memoria,
nunca con la salida de otra función del sistema. Todo es **ficticio y declarado** (NORMAS.md §1): la obra,
el inspector «Ing. Ficticio», las actas, los costos reales y el reajuste. Cuentas en `Decimal`, 28 dígitos,
`ROUND_HALF_EVEN`; se redondea solo al presentar.

## 1. Datos

Proyecto OB-S2, versión de contrato y línea base `OB-001`, perspectiva **costo**, moneda USD. Parámetros de
costo: FCAS 6,00, bono de alimentación 1,00, administración 0,15, utilidad 0,10 (PU = costo directo × 1,15 ×
1,10 = costo directo × 1,265). Calendario: inicio **lunes 2026-11-02**, períodos semanales de 5 días hábiles,
sin feriados: *D* = 20 días hábiles (4 semanas), término del plan base **viernes 2026-11-27**.

| Partida | Cantidad | Rend. *R* | Cuadrilla (obreros × sueldo) | Equipo (cant. × precio × dep.) | Material | Costo directo `u` |
|---|---|---|---|---|---|---|
| OB-A excavación (m3) | 100 | 10 m3/d | 4 × 3,00 = 12 | 1 × 120 × 0,10 = 12 | — | 10,00 |
| OB-B tubería (m) | 200 | 20 m/d | 2 × 2,50 = 5 | 1 × 30 × 0,10 = 3 | 3,00 | 5,00 |
| OB-C relleno (m3) | 100 | 10 m3/d | 4 × 2,50 = 10 | 1 × 60 × 0,10 = 6 | 12,00 | 20,00 |

`C_d` (costo diario de la cuadrilla y el equipo) = `S` × (1 + FCAS 6,00) + bono 1,00 × obreros + equipo:
A = 12 × 7 + 4 + 12 = **100**; B = 5 × 7 + 2 + 3 = **40**; C = 10 × 7 + 4 + 6 = **80**. Con `u = C_d / R + material`:
A = 100/10 = 10; B = 40/20 + 3 = 5; C = 80/10 + 12 = 20. `S`: A 12, B 5, C 10.

BAC = 100 × 10 + 200 × 5 + 100 × 20 = **4 000,00**; V = 4 000 × 1,265 = **5 060,00**; CV = 4 000; CF = CV × 0,15 =
**600,00**; PE base = CF × V / (V − CV) = 600 × 5 060 / 1 060 = **2 864,15** USD (56,60 %).

Plan de la línea base (fracción de cada partida por semana): A S1 0,5 · S2 0,5; B S2 0,5 · S3 0,5; C S3 0,5 · S4 0,5.
Precios del corte `u'` (el material de B pasa de 3,00 a 4,00 y el de C de 12,00 a 14,10): A 10,00; B 6,00; C 22,10.

## 2. Valuaciones y costos

V-01: 2026-11-02 a 11-06, fecha 11-09: A 40. V-02: 2026-11-09 a 11-13, fecha 11-16: A 50, B 60. Inspector «Ing. Ficticio».
Las dos **cuentan desde su registro** (RV-18, sin conformación). Costos reales: **1 280,00 USD**.
**Corte: viernes 2026-11-13** (día hábil 10, *c* = 2 períodos terminados).

## 3. Valor ganado al corte (§4.2)

| Resultado | Cuenta | Valor |
|---|---|---|
| PV | A 100 × 10 × 1 + B 200 × 5 × 0,5 + C 0 | **1 500,00** |
| EV | A 90 × 10 + B 60 × 5 | **1 200,00** |
| AC | costo real declarado | **1 280,00** |
| SV | 1 200 − 1 500 | **−300,00** |
| SPI | 1 200 / 1 500 | **0,8000** |
| CV | 1 200 − 1 280 | **−80,00** |
| CPI | 1 200 / 1 280 | **0,9375** |
| CPIc | (90 × 10 + 60 × 6) / 1 280 = 1 260 / 1 280 | **0,984375** |
| EAC (sistema) | 1 280 + (10 × 10 + 140 × 6 + 100 × 22,10) / 0,984375 = 1 280 + 3 150 / 0,984375 | **4 480,00** |
| EAC (índice) | 4 000 / 0,9375 | **4 266,67** |
| VAC | 4 000 − 4 480 | **−480,00** |
| Término (índice) | ⌈20 / 0,8⌉ = día hábil 25 | **2026-12-04** |

### Separación del desvío de control (§4.3)

Precio ΔP = Σ qe·(u − u') = 90 × (10 − 10) + 60 × (5 − 6) = **−60,00**. Consumo ΔC = Σ qe·u' − AC = 1 260 − 1 280 =
**−20,00**. CV = −60 − 20 = **−80,00** (la identidad es exacta). Al término: VAC_precio = −Σ q·(u' − u) = −(0 + 200 × 1 + 100 × 2,10) =
**−410,00**; VAC_consumo = −480 − (−410) = **−70,00**.

## 4. Reproyección al ritmo real (§4.4)

Índices por partida: A = 900 / 1 000 = **0,9**; B = 300 / 500 = **0,6**; C no tiene evidencia propia (PV = 0): el SPI global
**0,8**. Ritmo `r = s / n` con *n* = 2 períodos por partida: A 0,45; B 0,30; C 0,40. Pendiente: A 0,1; B 0,7; C 1.

**Plan reproyectado:** S1 A 0,4 · S2 A 0,5, B 0,3 · S3 A 0,1, B 0,3, C 0,4 · S4 B 0,3, C 0,4 · S5 B 0,1, C 0,2.

Fines (días hábiles): A (3 − 1) × 5 + (0,1 / 0,45) × 5 = **11,11**; B 4 × 5 + (0,1 / 0,3) × 5 = **21,67**; C 4 × 5 + (0,2 / 0,4) × 5 =
**22,5**. Término por el plan: ⌈22,5⌉ = día hábil 23 = **2026-12-02** (3 días hábiles tarde).

## 5. Lo ejecutado que S2 entrega a S1 (RF-72)

Cláusula ficticia: periodicidad mensual, mecanismo `comprobacion`. V-01 (*hasta* 11-06) y V-02 (*hasta* 11-13) caen en noviembre de 2026:
**A 90 y B 60**, C 0; la cantidad reajustable es la misma (ningún acumulado supera lo presupuestado). Con la valuación sembrada V-S
(B 150 más) B entrega cantidad 210 y reajustable 200, con aviso, y R13 da ERROR.

## 6. Reajuste reconocido (RV-12; §4.7)

Escenario **con reajuste**: un estudio de S1 guardado al corte (fecha de cálculo 2026-11-13), período noviembre, «parcial al corte» porque
noviembre no cierra (S1-R21), comprobación directa contra la versión revalorada: PU del contrato = `u` × 1,265: A 12,65; B 6,325. PU
comprobado = `u'` × 1,265: A 12,65; B 7,59. `Σ q_reajustable · (PU comprobado − PU contrato)` = 90 × 0,00 + 60 × 1,265 = **75,90**.
V' = 5 060,00 + 75,90 = **5 135,90**. La comprobación de toda la obra (410 × 1,265) **no** entra: incluye obra no ejecutada.
Escenario **sin reajuste**: ningún estudio guardado, V' = V = 5 060,00.

## 7. Alertas (iguales en los dos escenarios)

AL-1 ERROR (SPI 0,80 < 0,90); AL-2 ADVERTENCIA (CPI 0,9375 ≥ 0,90); AL-3 ERROR (3 días = 15 % de *D* > 10 %); AL-4 ERROR (el PE' de la
reproyección no se alcanza, con y sin el reajuste); AL-5 INFO (|ΔP| = 60 = 5 % de 1 200, frontera exacta).

## 8. Opciones de recuperación (§4.6)

`T*` = día 20; CF/D = 600 / 20 = 30 por día; `CV'` = 4 480 + ΔCD; `PE' = CF'·V' / (V' − CV')`.

| Opción | Detalle | Término | ΔCD | `CV'` | `CF'` | PE' sin reajuste (V' = 5 060,00) | PE' con reajuste (V' = 5 135,90) |
|---|---|---|---|---|---|---|---|
| Aceptar el retraso | — | día 23, 2026-12-02 | 0,00 | 4 480,00 | 690,00 | 6 019,66: no se alcanza | 5 402,91: no se alcanza |
| Más cuadrillas | B y C con *k* = 2, `E` = 1,8 | día 17, 2026-11-24 | 120,00 | 4 600,00 | 510,00 | 5 610,00: no se alcanza | **4 887,68 (95,17 %), se alcanza en S4** |
| Horas extra | `h` = 2 en B y C; B llega (19,72), C no (20,42) | día 21, 2026-11-30 | 115,3125 | 4 595,3125 | 630,00 | 6 860,09: no se alcanza | 5 985,37: no se alcanza |
| Partidas en paralelo | ninguna sin empezar con inicio > S3 | — | — | — | — | no aplica | no aplica |

Cuentas. Más cuadrillas: `E(2)` = 1 + 0,8 = 1,8; B: q_rest 140 × 40 × (2 − 1,8) / (20 × 1,8) = 31,11; C: 100 × 80 × 0,2 / (10 × 1,8) = 88,89; ΔCD = 120,00. Plan:
S3 B 0,54, C 0,72; S4 B 0,16, C 0,28 (B termina en 16,48 y C en 16,94 → día 17). Horas extra: `m` = 1 + (2/8) × 0,8 = 1,2; OT = (2/8) × 1,5 × S × 7:
B 13,125; C 26,25; ΔCD_B = 140 × (40 + 13,125 − 40 × 1,2) / (20 × 1,2) = 29,8958; ΔCD_C = 100 × (80 + 26,25 − 96) / (10 × 1,2) = 85,4167; total 115,3125. Con reajuste:
`V' − CV'` = 5 135,90 − 4 600,00 = 535,90 y PE' = 510 × 5 135,90 / 535,90 = 4 887,68 (95,17 % de V'); en la curva de `OB-002` el acumulado llega a 82 % en S3 y a 100 % en S4: se
ubica en **S4**. Horas extra: 540,5875 y 630 × 5 135,90 / 540,5875 = 5 985,37. Sin reajuste: 460,00 y 510 × 5 060 / 460 = 5 610,00; 464,6875 y 630 × 5 060 / 464,6875 = 6 860,09.
**Comprobación cruzada:** PE' ≤ V' equivale a V' ≥ CV' + CF', así que cada opción necesita un reajuste reconocido de al menos CV' + CF' − V: aceptar **110,00**; más cuadrillas **50,00**; horas extra
**165,3125**. Con 75,90 solo «más cuadrillas» lo supera; sin reajuste, ninguna.

## 9. Decisión «más cuadrillas»

Versión **`OB-002`** con motivo `recuperacion` y el plan S1 A 0,4 · S2 A 0,5, B 0,3 · S3 A 0,1, B 0,54, C 0,72 · S4 B 0,16, C 0,28. Un `RegistroCambio` (objeto `plan`) por cada
(período, partida) que cambió respecto del plan de la versión de origen: (S1, A) 0,5 → 0,4; (S2, B) 0,5 → 0,3; (S3, A) 0 → 0,1; (S3, B) 0,5 → 0,54; (S3, C) 0,5 → 0,72; (S4, B) 0 → 0,16; (S4, C) 0,5 →
0,28 (**siete**). R2 y R7 sin hallazgos; la línea base sigue en `OB-001`; el SPI al mismo corte sigue en 0,80.

## 10. Valuación sembrada V-S (para R13 y R14)

Número `V-03`, 2026-11-12 a 11-20, fecha 11-19, **sin inspector**; líneas: B 150 (acumulado 210 > 200), D 5 (no presupuestada), C 10 con fecha de medición 11-23. El corte de la prueba es 2026-11-20.
Conjunto **exacto** de seis hallazgos: R13 ERROR B (impacto **50,00** = 10 × 5,00); R13 ERROR D; R14 ERROR sin inspector; R14 ERROR fecha anterior a *hasta*; R14 ERROR solape con V-02; R14 ERROR medición
fuera del período.
