# Memoria S1: precios de empresa, R11 y R12 (oráculo de RF‑68, spec S1 §6.3 y §9.2)
Empresa ficticia «Constructora Ejemplo, C.A.», RIF J‑00000000‑0 (texto, RV‑6). Lista en Bs del 20/09/2026,
base y referencia = MaPreX julio 2026 en Bs (`lista_maprex_bs.csv`, tasa 633,3644 al 01/07/2026).
Precios propios en `tests/fixtures/precios_empresa_s1.csv`. **Fecha de evaluación fija: 2026-10-01**
(tasa venta 860,18, fecha valor 01‑10‑2026, BCV verificada). Rango −20 % / +30 %, plazo 30 días.
Versión ficticia en Bs: partida S1‑EMP‑01 con un material de cantidad 1 por cada insumo de la tabla,
cantidad de obra 10, administración 0,15, utilidad 0,10 (FCAS y bono 0): todo Δ de precio de un insumo
mueve el total en Δ · 1,15 · 1,10 · 10 = Δ · **12,65**.
Los precios en Bs declaran la tasa MaPreX para que el desvío sea exactamente p/p_ref − 1 (PRU‑H11).
| # | Insumo (MaPreX) | Ref | p_ref Bs | Precio en la lista (Bs) | Fecha | Condición |
|---|---|---|---|---|---|---|
| 1 | CEMENTO GRIS PORTLAND SACO 42.5 KG/93,7 LB | CEM019 | 12 080,00 | 13 288,00 (+10 %) | 2026‑09‑20 | dentro y vigente |
| 2 | CODO PVC 90 GRADOS A.N. D=4" | PLO035 | 4 530,00 | 3 624,00 = 0,8000·p_ref | 2026‑09‑20 | −20,00 % pasa |
| 3 | UNION PVC A.B. 4" | PLO560 | 5 285,00 | 4 227,4715 = 0,7999·p_ref | 2026‑09‑20 | −20,01 % |
| 4 | PIEDRA PICADA PARA CONCRETO | AGR081 | 37 750,00 | 49 075,00 = 1,3000·p_ref | 2026‑09‑20 | +30,00 % pasa |
| 5 | ARENA LAVADA | MZ0027 | 37 750,00 | 49 078,775 = 1,3001·p_ref | 2026‑09‑20 | +30,01 % |
| 6 | AGUA SUMINISTRADA EN CAMION CISTERNA O TANQUE | AGR003 | 7 550,00 | 7 550,00 | 2026‑09‑01 | 30 días pasa |
| 7 | CLAVO DE ACERO LISO L=2 1/2" | ACE076 | 302,00 | 302,00 | 2026‑08‑31 | 31 días |
| 8 | PEGAMENTO PARA PVC 1/4 GL TANGIT O SIM | MT539 | 21 895,00 | 30,00 USD × 700 = 21 000,00 | 2026‑09‑25 | tasa sin fecha |
| 9 | TUBO PVC A.N. D=4" / 110 MM E = 2,2 MM NORMA | PLOA38 | 8 822,17 | 12,00 USD × 735,00 = 8 820,00 | 2026‑09‑26 | tasa sin fuente |
| 10 | LIJA DE AGUA N 100 (alta) | — | — | 150,00 | 2026‑09‑20 | sin referencia |
| 11 | MATERIAL GRANULAR INTEGRAL (heredado de la base) | BAS006 | 4 530,00 | 4 530,00 | 2026‑07‑09 | 84 días |
Desvíos de 8 y 9 (pasan): (21 000·633,3644)/(21 895·700) − 1 = −13,22 %; (8 820·633,3644)/(8 822,17·735) − 1 = −13,85 %.
Erosión en Bs por unidad (T1/T0 = 860,18/633,3644): clavo 302·0,358112328… = 108,1499231721896589072578124;
granular 4 530·0,358112328… = 1 622,248847582844883608867186. Precio original en USD: erosión 0 (declarada).
**Conjunto exacto de hallazgos a 2026‑10‑01 (versión):**
| Regla | Severidad | Insumo | Observado | Δ por unidad | Impacto en la versión (Bs) |
|---|---|---|---|---|---|
| R11 | ADVERTENCIA | UNION PVC A.B. 4" | −20,01 % | 1 057,53 | 13 377,74 |
| R11 | ADVERTENCIA | ARENA LAVADA | +30,01 % | 11 328,78 | 143 309,00 |
| R11 | INFO | 1 no contrastable (LIJA DE AGUA N 100, sin referencia) | 1 | — | — |
| R12 | ADVERTENCIA | CLAVO DE ACERO LISO L=2 1/2" | 31 días | 108,15 | 1 368,10 |
| R12 | ADVERTENCIA | MATERIAL GRANULAR INTEGRAL | 84 días | 1 622,25 | 20 521,45 |
| R12 | ERROR | PEGAMENTO PARA PVC 1/4 GL TANGIT O SIM | tasa 700 sin fecha | — | — |
| R12 | ADVERTENCIA | TUBO PVC A.N. D=4" … | tasa 735,00 sin fuente | 0,00 | 0,00 |
Reevaluada a 2026‑10‑06: se agrega R12 ADVERTENCIA del AGUA (35 días); las filas guardadas no cambian.
