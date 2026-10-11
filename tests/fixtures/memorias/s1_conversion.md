# Memoria S1: conversión y erosión (oráculo de RF‑66, spec S1 §9.1.1)
Precio ficticio P = 1 000 Bs del 01/07/2026; T0 = 633,3644 Bs/USD (MaPreX, verificada); evaluación al
01/10/2026 con T1 = 860,18 Bs/USD (BCV venta, fecha valor 01‑10‑2026, verificada). Decimal de 28 dígitos,
ROUND_HALF_EVEN.
| Cuenta | Valor exacto | Presentado |
|---|---|---|
| P/T0 | 1,578869920696521623255111907 USD | 1,58 USD |
| P/T1 | 1,162547373805482573414866656 USD | 1,16 USD |
| Erosión en USD = P/T0 − P/T1 | 0,416322546891039049840245251 | 0,42 USD |
| Erosión en Bs = P·T1/T0 − P | 358,112328384733969891582160 | 358,11 Bs |
| Porcentaje = 1 − T0/T1 | 0,2636838801181148131786370295 | 26,37 % |
| Contraste (NO es el de §5.3): 358,11 / 1 000 | — | 35,81 % |
Un precio en USD tiene erosión 0 en las dos monedas (declarado: no hay índice de inflación en USD).
