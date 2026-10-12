# Memoria de cálculo a mano: variaciones atípicas en series de precios sembradas (RF-100, S3-6)

Oráculo de `ml/anomaly/series.py` y `ui/atipicos.py` (spec S3 §3.2 y §13.2). Hecha a mano antes
del código; no depende de ninguna función del proyecto. **No valida la tasa real de detección
ni de falsas alarmas** (los datos son ficticios, NORMAS.md §1): solo fija qué punto es atípico
en series construidas para que lo sea. La tesis lo presenta como apoyo a quien revisa.

El detector es el de I6.1 y no se ajusta: `SEMILLA` = 42, `UMBRAL_ATIPICO` = −0,05,
`MINIMO_OBSERVACIONES` = 8 variaciones. Una variación es `(p2 − p1) / p1`.

## 1. Serie de 10 precios con un atípico (9 variaciones)

Precios en USD, uno por mes (2026-01 a 2026-10): 1, 2, 4, 8, 16, 32, 64, 128, 256, **257**.

| Variación | Cálculo | Valor |
|---|---|---|
| v0 a v7 | (2 − 1) / 1 = 1, (4 − 2) / 2 = 1, …, (256 − 128) / 128 | **1** (ocho veces) |
| v8 (2026-09 → 2026-10) | (257 − 256) / 256 | **0,00390625** |

Ocho variaciones iguales a 1 y una de 0,00390625: el atípico es **v8**, el único. Conjunto
esperado de hallazgos: `{v8}`, ADVERTENCIA, con valor 0,00390625 (0,39 %).

## 2. Serie de 10 precios sin atípico

Precios: 1, 2, 4, 8, 16, 32, 64, 128, 256, **512**. Las nueve variaciones valen 1 (todas
iguales): nada se aparta del resto. Conjunto esperado: **vacío**.

## 3. Serie corta: abstención

Precios: 1, 2, 4, 8, 16, 32, 64, 128 (8 precios, **7** variaciones, menos de 8). El detector se
abstiene aunque se le añada un punto raro: conjunto esperado **vacío** y `se_abstuvo` verdadero.

## 4. Conversión a USD con la tasa de cada precio (RF-65)

Dos precios en bolívares de fechas distintas, con la tasa (Bs por USD) de cada fecha:

| Fecha | Precio | Tasa | En USD |
|---|---|---|---|
| 2026-08-03 | 720 Bs | 36 | 720 / 36 = **20** |
| 2026-09-07 | 1 100 Bs | 44 | 1 100 / 44 = **25** |

Variación en USD = (25 − 20) / 20 = **0,25**. En bolívares habría sido (1 100 − 720) / 720 =
0,52777…: la diferencia es la erosión de la moneda, que no es un cambio del precio del insumo.
Un precio en Bs **sin tasa** no se convierte ni se inventa: se omite y se nombra (`sin_tasa`).

## 5. Ordenamiento y emparejamiento

Los puntos se ordenan por fecha y, a igual fecha, por el nombre de su lista; las variaciones
son entre consecutivos. Un precio anterior igual a 0 no genera variación (no se divide por 0).
Las listas de **proyecto** (las que nacen de una cotización) no entran en la serie.
