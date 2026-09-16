# Resultados del modulo predictivo (Sesion I6.3, RF-28; recuento multidominio M4.1)

Generado por `scripts/generar_resultados_ml.py` sobre bases en memoria sembradas con los
catalogos de los cuatro dominios; reproducible con
`uv run python scripts/generar_resultados_ml.py`.

## Compuerta G2: conteo de registros y tecnica (CLAUDE.md §8.1)

| Dominio | Registros de APU | Tecnica que dicta la tabla |
|---|---|---|
| civil | 5 | reglas |
| industrial | 4 | reglas |
| sistemas | 9 | reglas |
| telecom | 40 | reglas |

Todos los dominios estan por debajo de los 50 registros: la tecnica de
`ml/prediction/` es el **sistema de reglas con analisis de sensibilidad**, y se declara
como **limitacion** del trabajo, no como logro: no hay datos suficientes para entrenar
ni validar un modelo de aprendizaje (la tabla de degradacion existe exactamente para
este caso). La compuerta G2 queda cruzada con esta evidencia; tras el sprint
multidominio la limitacion esta demostrada con catalogos poblados en los cuatro dominios,
no con ausencia de datos (compuerta GM4, PLAN_MULTIDOMINIO §2).

## Regla declarada

PU estimado = PU base x (1 + media de las variaciones del historico de cambios de
precio). Sensibilidad: el rango recorre la variacion minima y la maxima observadas.
La regla no conoce la composicion del APU: el motor de costos (`core.costing`) es la
verdad de terreno contra la que se mide.

## Metricas (RF-28) — dominio civil, caso UC-02 de la linea base

| Metrica | Valor |
|---|---|
| MAPE | 12.46 % |
| RMSE | 5.10 USD |
| R2 | 0.9974 |

## Predicciones sobre el caso UC-02 de la linea base

| Partida | PU base | PU estimado | Rango de sensibilidad |
|---|---|---|---|
| LB-01-EXC | 8.60 | 9.89 | [9.46, 10.32] |
| LB-02-TUB | 10.19 | 11.72 | [11.21, 12.23] |
| LB-03-ENC | 33.24 | 38.22 | [36.56, 39.89] |
| LB-04-CON | 242.64 | 279.04 | [266.90, 291.17] |
| LB-05-REL | 52.58 | 60.46 | [57.83, 63.09] |

## Contraste AACE clase 3 (RF-29) — dominio civil

Ningun precio construido se desvia del estimado fuera del rango declarado (-20 % / +30 %): sin hallazgos.

## Metricas por dominio (Sesion M4.1)

Solo se evalua donde hay un historico observado de `CambioPrecio` entre dos listas de precios
fechadas; donde no lo hay se declara, no se fabrica.

| Dominio | Historico | Partidas | Cambios de precio | MAPE | RMSE | R2 | AACE |
|---|---|---|---|---|---|---|---|
| industrial | sin historico de variaciones: una sola lista de precios publicada (M2.2 / M3.2) | — | — | no evaluable | — | — | — |
| sistemas | sin historico de variaciones: una sola lista de precios publicada (M2.2 / M3.2) | — | — | no evaluable | — | — | — |
| telecom | Precios ARENAZA (2026-05-18) -> Precios MaPreX 2026-07 (2026-07-09) | 40 | 5 | 27.83 % | 28.16 USD | 0.8866 | 38 hallazgo(s) |

### telecom: partidas cuyo PU cambio con la lista nueva (8 de 40)

| Partida | PU base | PU observado (lista nueva) | PU estimado | Rango de sensibilidad |
|---|---|---|---|---|
| TC-P1-03 | 3.33 | 2.62 | 4.18 | [2.62, 8.01] |
| TC-P1-10 | 5.05 | 6.79 | 6.35 | [3.98, 12.16] |
| TC-P1-11 | 3.96 | 9.54 | 4.98 | [3.12, 9.54] |
| TC-P1-13 | 2.00 | 1.91 | 2.51 | [1.58, 4.82] |
| TC-P2-05 | 3.33 | 2.62 | 4.18 | [2.62, 8.01] |
| TC-P2-23 | 5.05 | 6.79 | 6.35 | [3.98, 12.16] |
| TC-P2-24 | 3.96 | 9.54 | 4.98 | [3.12, 9.54] |
| TC-P2-25 | 2.00 | 1.91 | 2.51 | [1.58, 4.82] |

Las otras 32 partidas conservan su PU con la lista nueva, pero la regla
(que no conoce la composicion) les aplica igualmente la variacion media del
historico: las metricas de arriba son sobre las 40 partidas y
muestran exactamente esa limitacion.

Contraste AACE clase 3 (RF-29) — telecom:

38 hallazgo(s) de severidad ADVERTENCIA:

- el precio construido de TC-P1-01 (82.68) se desvia -20.44 % del estimado (103.92), fuera del rango de la clase 3 de AACE (-20 % / +30 %)
- el precio construido de TC-P1-02 (157.99) se desvia -20.44 % del estimado (198.59), fuera del rango de la clase 3 de AACE (-20 % / +30 %)
- el precio construido de TC-P1-03 (2.62) se desvia -37.25 % del estimado (4.18), fuera del rango de la clase 3 de AACE (-20 % / +30 %)
- el precio construido de TC-P1-04 (5.00) se desvia -20.44 % del estimado (6.28), fuera del rango de la clase 3 de AACE (-20 % / +30 %)
- el precio construido de TC-P1-05 (2.00) se desvia -20.44 % del estimado (2.51), fuera del rango de la clase 3 de AACE (-20 % / +30 %)
- … y 33 mas.
