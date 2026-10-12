# Lista congelada de diferencias sembradas (protocolo del indicador de quien revisa)

Versión 1, escrita en S3-0 con las cifras de `tests/fixtures/memorias/diferencias_s3.md` §1 y §1b,
hechas a mano. Su SHA-256 está en `protocolos_s3.json` y no cambia después de escrito. Los Excel y
los `.silice` de las dos entregas se generan en la fase Med a partir de estas tablas; generarlos no
cambia la lista.

## Entrega P (total anterior 840, total nuevo 1130, diferencia +290)

| Partida | Tipo de diferencia | Δ cantidad | Δ precio | Δ total |
|---|---|---|---|---|
| A | cantidad (10 → 12 a 50) | +100 | 0 | +100 |
| B | precio (20 → 22, cantidad 5) | 0 | +10 | +10 |
| C | cantidad y precio (2 → 3; 100 → 110) | +100 | +30 | +130 |
| D | partida eliminada (4 a 10) | −40 | 0 | −40 |
| E | partida nueva (3 a 30) | +90 | 0 | +90 |

## Entrega Q (total anterior 550, total nuevo 589, diferencia +39)

| Partida | Tipo de diferencia | Δ cantidad | Δ precio | Δ total |
|---|---|---|---|---|
| A' | cantidad (8 → 9 a 25) | +25 | 0 | +25 |
| B' | precio (15 → 16, cantidad 6) | 0 | +6 | +6 |
| C' | cantidad y precio (4 → 5; 40 → 44) | +40 | +20 | +60 |
| D' | partida eliminada (2 a 50) | −100 | 0 | −100 |
| E' | partida nueva (4 a 12) | +48 | 0 | +48 |

**Qué cuenta como «encontrada»:** la persona nombra la partida y dice que cambió su cantidad,
su precio, que se eliminó o que es nueva; el monto no tiene que ser exacto para contarla, pero se
anota para la medición de la vista Revisar (que sí debe darlo exacto). **Qué es falsa alarma:**
nombrar una partida que no está en su tabla o un cambio que no ocurrió.
