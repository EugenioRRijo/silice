# Memoria de cálculo a mano: diferencia entre versiones, revaloración y costo de R16 (S3)

Oráculo de SL-E9 (`core/budget/comparacion.py`) y del costo de R16 (`ui/contraste.py`), spec S3
§13.1. Está hecha a mano, con aritmética exacta, **antes del código**, y no depende de ninguna
función del proyecto. Las pruebas comparan contra estas cifras, no contra la expresión de una
regla. Los datos son ficticios (NORMAS.md §1): números simples para contar a mano.

## 1. Diferencia entre dos versiones

Descomposición (el término cruzado queda en el precio):

    Δ total = q2·PU2 − q1·PU1 = (q2 − q1)·PU1  [Δ cantidad]  +  (PU2 − PU1)·q2  [Δ precio]

Una partida solo en la versión 2 (nueva) toma PU1 := PU2; una solo en la versión 1 (eliminada)
toma PU2 := PU1; así la partida entera es desvío por cantidad.

| Partida | v1: q × PU | v2: q × PU | Δ cantidad | Δ precio | Δ total | Estado |
|---|---|---|---|---|---|---|
| A | 10 × 50 = 500 | 12 × 50 = 600 | (12 − 10)·50 = 100 | 0 | 100 | cambiada |
| B | 5 × 20 = 100 | 5 × 22 = 110 | 0 | (22 − 20)·5 = 10 | 10 | cambiada |
| C | 2 × 100 = 200 | 3 × 110 = 330 | (3 − 2)·100 = 100 | (110 − 100)·3 = 30 | 130 | cambiada |
| D | 4 × 10 = 40 | — | (0 − 4)·10 = −40 | 0 | −40 | eliminada |
| E | — | 3 × 30 = 90 | 3·30 = 90 | 0 | 90 | nueva |

Totales: v1 = 500 + 100 + 200 + 40 = **840**; v2 = 600 + 110 + 330 + 90 = **1130**.
Σ Δ cantidad = 100 + 0 + 100 − 40 + 90 = **250**; Σ Δ precio = 0 + 10 + 30 + 0 + 0 = **40**;
Δ total = 250 + 40 = **290** = 1130 − 840. Orden por |Δ total| descendente: C (130), A (100),
E (90), D (40), B (10).

### 1b. La entrega paralela Q (protocolo del indicador de quien revisa, S3 §13.5 a)

Misma descomposición, otras cifras, para que la persona que revisa no vea dos veces la misma
entrega (`docs/protocolo_indicador_administrador.md` §2). Sus partidas llevan prima.

| Partida | v1: q × PU | v2: q × PU | Δ cantidad | Δ precio | Δ total | Estado |
|---|---|---|---|---|---|---|
| A' | 8 × 25 = 200 | 9 × 25 = 225 | (9 − 8)·25 = 25 | 0 | 25 | cambiada |
| B' | 6 × 15 = 90 | 6 × 16 = 96 | 0 | (16 − 15)·6 = 6 | 6 | cambiada |
| C' | 4 × 40 = 160 | 5 × 44 = 220 | (5 − 4)·40 = 40 | (44 − 40)·5 = 20 | 60 | cambiada |
| D' | 2 × 50 = 100 | — | (0 − 2)·50 = −100 | 0 | −100 | eliminada |
| E' | — | 4 × 12 = 48 | 4·12 = 48 | 0 | 48 | nueva |

Totales: v1 = 200 + 90 + 160 + 100 = **550**; v2 = 225 + 96 + 220 + 48 = **589**.
Σ Δ cantidad = 25 + 0 + 40 − 100 + 48 = **13**; Σ Δ precio = 0 + 6 + 20 + 0 + 0 = **26**;
Δ total = 13 + 26 = **39** = 589 − 550. Orden por |Δ total|: D' (100), C' (60), E' (48), A' (25),
B' (6).

## 2. Revaloración con la lista de quien revisa (MIN-001 del paquete de prueba)

Línea base del paquete: arena 1,00 × 14,00; compactadora 1 × 71,00 × 0,10 / 8 = 0,8875; mano de
obra (2 × 10,25 × (1 + 6,00) + 1,00 × 2) / 8 = 18,1875; PU = 41,839875; cantidad 20.

La lista del revisor trae la arena a 16,00 y el obrero a 12,25; la compactadora **no está** en su
lista: es «no contrastable», conserva 71,00 y no suma al desvío.

- Materiales 1,00 × 16,00 = 16,00. Mano de obra (2 × 12,25 × 7 + 1,00 × 2) / 8 = 173,5 / 8 =
  21,6875. Costo directo 16,00 + 0,8875 + 21,6875 = 38,575.
- Con administración 38,575 × 1,15 = 44,36125; PU = 44,36125 × 1,10 = **48,797375**.
- Δ total = (48,797375 − 41,839875) × 20 = 6,9575 × 20 = **139,15**, todo por precio (Δ cantidad 0).

Con la arena a 15,00 (referencia por «Ref» de precio en vez de por código):
materiales 15,00 → costo directo 15,00 + 0,8875 + 21,6875 = 37,575; × 1,15 = 43,21125; PU =
**47,532375**; Δ total = (47,532375 − 41,839875) × 20 = 5,6925 × 20 = **113,85**.

## 3. Costo de R16 sobre OF-001 (solo la especialidad de datos)

Referencia = OF-001 de `of001.md` (7 puntos de datos, rack `RK1`). Cantidades de la memoria de
OF-001 §3: cajas, *face plates*, *jacks* y certificaciones 7 cada una (sin desperdicio, D-17);
cable UTP cat 6 = 74,900 + 7 × (2,0 + 0,5) = 92,400 × 1,10 = **101,640 m**; canalización EMT
1/2" = DS1 + DS2 + DS3 = 3 + 3 + 2,2 = **8,2 m**; EMT 3/4" = DS4 a DS17 = **23,2 m**.

Precios de la memoria (supuestos de prueba): caja 5,00; *face plate* 3,00; *jack* 4,00;
certificación 12,00; UTP cat 6 1,20 /m; EMT 3/4" 6,00 /m; EMT 1/2" 4,50 /m.

**Escenario A: el plano no trae `PB3` (faltante en el plano).** Sin `PB3` (recorrido 12,2 m):
cajas = *face plates* = *jacks* = certificaciones = 6; cable = (74,900 − 12,2 + 6 × 2,5) × 1,10 =
(62,7 + 15,0) × 1,10 = **85,470 m**; EMT 3/4" sin DS16 (0,5) ni DS17 (2,2) = 23,2 − 2,7 =
**20,5 m**; EMT 1/2" igual (8,2 m).

| Partida | Plano − referencia | × precio | Δ |
|---|---|---|---|
| caja, *face plate*, *jack*, certificación | −1 cada una | 5,00 + 3,00 + 4,00 + 12,00 = 24,00 | −24,000 |
| UTP cat 6 | 85,470 − 101,640 = −16,170 m | 1,20 | −19,404 |
| EMT 3/4" | 20,5 − 23,2 = −2,7 m | 6,00 | −16,200 |
| EMT 1/2" | 0 | 4,50 | 0 |
| **Total** | | | **−59,604** |

R16 da un único faltante (`PB3`, solo en la referencia) y 32 emparejadas.

**Escenario B: `PB3` está 0,40 m más allá (y = 5,9 en vez de 5,5): desplazado.** 0,40 m queda
entre 0,10 y 1,00 m: desplazado. Los 7 puntos siguen, así que las cuatro piezas no cambian. El
recorrido de `PB3` crece 0,40 m (el tendido en y a z = 2,5): cable = 101,640 + 0,40 × 1,10 =
**102,080 m**; DS16 pasa de 0,5 a 0,9 m y DS17 conserva 2,2: EMT 3/4" = **23,6 m**.
Δ = 0,44 × 1,20 + 0,40 × 6,00 = 0,528 + 2,400 = **+2,928**.

**Escenario C: sobrante.** Es A con las fuentes cambiadas (la referencia sin `PB3` y el plano
con él): un sobrante en el plano y **+59,604**.

## 4. Reauditoría con anexos

El anexo `espacio` de OF-001 en un paquete reauditado da exactamente 33 ADVERTENCIAS de R8 (las
de las constantes supuestas de `of001.md`) y ninguna de R9, R10 ni R15. La importación del DXF de
OF-001 da 8 (6 «altura pendiente» y 2 supuestos de circuito): son dos literales distintos
porque no leen lo mismo (RP8-5).
