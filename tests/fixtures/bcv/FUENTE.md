# Fuente de los archivos del BCV (S1-0, Tarea 3)

Archivos reales descargados de bcv.org.ve el 2026-10-11 con `curl.exe -L` y versionados aquí (repo
privado, P6 ratificada). No van en el instalador. Todo lo de esta ficha se transcribió **a mano**
abriendo los archivos con `xlrd` en una sesión aparte (no con `adapters/bcv`); no se escribió ningún
valor que no estuviera en el archivo. Las pruebas de `adapters/bcv` (Tarea 6) leen las tablas de
transcripción de aquí y las comparan con lo que lee el adaptador. Valores con punto decimal.

## Tasa

| Campo | Valor |
|---|---|
| Archivo | 2_1_2c26_smc.xls |
| Dirección | https://www.bcv.org.ve/sites/default/files/EstadisticasGeneral/2_1_2c26_smc.xls |
| Página | https://www.bcv.org.ve/estadisticas/tipo-cambio-de-referencia-smc |
| Fecha de descarga | 2026-10-11 |
| SHA-256 | f58240f09239882d0cb3b40d8e675abbbfb8208cfb3a6566731046ee9e7480fb |
| Hojas (N) | 64 |

Letra `c` = 3.er trimestre de 2026 (verificado: las 64 hojas van de «01072026» a «30092026»). Las
letras `a`, `b`, `d` (`2_1_2a26`, `2_1_2b26`, `2_1_2d26`) se abrieron también y dan 1T, 2T y 4T
(el `d26` trae 7 hojas, de «01102026» a «09102026», trimestre en curso).

El nombre de cada hoja es la **fecha de operación** (DDMMAAAA); la **fecha valor** está dentro de la
hoja («Fecha Valor: DD/MM/AAAA») y es el día hábil siguiente. La hoja «30092026» vale el 2026-10-01.
Las columnas de la fila USD son: cotización M.E./US$ compra y venta (ambas 1.0) y después Bs por
moneda, compra y venta. El archivo guarda **8 decimales** (formato de celda `#,##0.00000000`); la
tabla copia el valor guardado.

### Transcripción

| Hoja | Posición | Fecha valor | Compra | Venta |
|---|---|---|---|---|
| 30092026 | primera | 2026-10-01 | 858.02486175 | 860.1753 |
| 17082026 | medio | 2026-08-18 | 771.37921875 | 773.3125 |
| 01072026 | última | 2026-07-02 | 638.10364275 | 639.7029 |

La hoja «del medio» es la n.º 32 de 64, contando desde la primera del archivo (que es la más
reciente).

## Literal verificado

El 2026-10-01 el BCV publica 858,02 (compra) y 860,18 (venta) Bs por USD, esto es, los valores
guardados de la hoja «30092026» redondeados a dos decimales (858.02486175 y 860.1753). Es el literal
que usan las memorias y los ejemplos del plan.

| Fecha valor | Compra | Venta |
|---|---|---|
| 2026-10-01 | 858.02 | 860.18 |

## INPC

| Campo | Valor |
|---|---|
| Archivo | 4_5_7.xls |
| Dirección | https://www.bcv.org.ve/sites/default/files/precios_consumidor/4_5_7.xls |
| Página | https://www.bcv.org.ve/estadisticas/consumidor |
| Fecha de descarga | 2026-10-11 |
| SHA-256 | 715a48725efe6efa2ec8db501da2479b142c3628161eaafc81998b9805027510 |
| Hojas (N) | 1 |

Hoja «Base Diciembre 2007»: «ÍNDICE NACIONAL DE PRECIOS AL CONSUMIDOR, serie desde Diciembre 2007,
base Diciembre 2007 = 100», columnas Indice y Var%, fuente «B.C.V. - I.N.E.». Va del mes 2007-12 al
2026-09 (226 meses), los más recientes primero, con el año en una fila propia sobre sus meses. Los
años 2026 y 2025 llevan «(*)» en esa fila: se toman como provisionales **todos** sus meses (el
archivo no trae nota que defina el asterisco; ver `docs/fuentes/bcv_formatos.md`).

### Transcripción

| Mes | Posición | Valor | Provisional |
|---|---|---|---|
| 2007-12 | primero | 100.0 | no |
| 2017-06 | medio | 17537.8 | no |
| 2020-12 | otro | 327767509170.0 | no |
| 2025-01 | otro | 40521840708458.305 | sí |
| 2025-12 | otro | 212393273459827.03 | sí |
| 2026-01 | otro | 281565112063483.0 | sí |
| 2026-09 | último | 690967674312665.0 | sí |
