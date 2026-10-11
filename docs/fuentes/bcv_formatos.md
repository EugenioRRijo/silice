# Formatos de los archivos del BCV (S1-0, Tarea 3)

Lo que se verificó abriendo los archivos reales de `tests/fixtures/bcv/` (procedencia, huellas y
transcripción a mano en `tests/fixtures/bcv/FUENTE.md`). `adapters/bcv` lee estos formatos y nada más;
lo que no coincide va al informe de importación (S1 §7.1). Verificado el 2026-10-11.

## Tasa de referencia: `2_1_2<letra><AA>_smc.xls`

- **Letras del trimestre.** `a` = 1.er, `b` = 2.º, `c` = 3.º, `d` = 4.º. Se abrieron los cuatro archivos
  de 2026: `a26` tiene 58 hojas (de «02012026» a «31032026»), `b26` 58 (de «01042026» a «30062026»),
  `c26` 64 (de «01072026» a «30092026») y `d26` 7 (de «01102026» a «09102026», en curso).
- **Hojas.** Una por día hábil de **operación**; el nombre es esa fecha como `DDMMAAAA`, la más reciente
  primero. Los nombres no sirven de fecha del dato: la fecha valor está dentro.
- **Fecha valor.** En la fila 5, columna D: el texto `Fecha Valor: DD/MM/AAAA` (la fecha va en la
  **misma celda**, tras «:»). La celda de la columna B de esa fila dice `Fecha Operacion: DD/MM/AAAA`
  (sin tilde). La fecha valor es la del día hábil siguiente (hoja «30092026» vale el 01/10/2026; hoja
  «09102026» vale el 13/10/2026). Como la última hoja de un trimestre vale el día siguiente, la fecha
  valor puede caer hasta 7 días naturales después del fin del trimestre (SUPUESTO_DECLARADO de
  `tasa.py`; con este archivo, 1 día).
- **Fila USD.** El código `USD` está en la columna B de la fila 15 (las filas 11 a 14 son EUR, CNY, TRY y
  RUB), con «E.U.A.» en la C. Columnas D y E: cotización M.E./US$ (compra y venta; para el USD valen
  1.0 y 1.0). Columnas **F y G: Bs por moneda, compra (BID) y venta (ASK)**. Las dos últimas cifras
  de la fila son entonces las de Bs; el lector toma esas. Encabezados en las filas 8 y 9
  («(a) Cotización M.E./US$», «Bs./M.E.», «Compra (BID)», «Venta (ASK)»).
- **Precisión.** Las cifras de Bs vienen con 8 decimales (formato `#,##0.00000000`); el 01/10/2026 son
  858.02486175 y 860.1753. El literal 858,02 / 860,18 del plan es ese valor redondeado a dos
  decimales. El adaptador guarda el valor completo (con `repr`, sin `float` aguas abajo).

## INPC: `4_5_7.xls` (niveles) y por qué no `4_5_1.xls`

- `4_5_1.xls` publica **variaciones porcentuales** por grupos («Variaciones del Índice Nacional de
  Precios al Consumidor, Clasificado por Grupos», «(Porcentaje)»); la escalatoria necesita **niveles**,
  así que no sirve.
- `4_5_3.xls` trae niveles por grupos en 99 columnas (cuadro I.1, base Dic. 2007 = 100), con promedios;
  es válido pero ancho y con varias series. `4_5_7.xls` es el índice general solo, en una hoja
  y dos columnas. Se elige `4_5_7.xls`. `4_5_7_3.xls` es **byte a byte idéntico** a `4_5_7.xls`
  (comparado con `cmp`).
- **Hoja** única `Base Diciembre 2007`. Título «ÍNDICE NACIONAL DE PRECIOS AL CONSUMIDOR»,
  «Serie desde Diciembre 2007», «( BASE Diciembre 2007 = 100 )». Fuente al pie: «B.C.V. - I.N.E.».
- **Encabezados.** Fila 8: columna B `Indice`, columna C `Var%`. La columna A no tiene encabezado: es
  la del período. No existe una columna «Período» ni una de «Índice general»; la serie es la general.
- **Forma del período.** No es una fecha ni un texto «Ene-2026». El **año** va solo en una fila propia
  de la columna A (número `2024.0`, o texto `2023`, `2019 `, `2026(*)`; algunos con espacio al final) y
  debajo, los doce **nombres de mes** completos en español («Septiembre», «Diciembre»), del más
  reciente al más antiguo, con una fila en blanco entre años. Primer mes: Diciembre 2007 (valor 100.0);
  último: Septiembre 2026. En total 226 meses.
- **Provisional.** Los años 2026 y 2025 llevan `(*)` en su fila de año; los demás no. El archivo no trae
  una nota que explique el asterisco: se lo toma como «provisional» para **todos los meses de ese año**
  (SUPUESTO_DECLARADO; los antecedentes §6 lo describen así: 2026 provisional «(*)»).
- **Valores.** Números (`float` en `xlrd`, hasta 15 dígitos significativos: p. ej. 690967674312665.0
  en 2026-09); `Decimal(repr(x))`.
- **Base.** `Diciembre 2007 = 100`.
- **Lectura.** `FormatoMensual.disposicion = "anio_en_filas"` (nuevo en `formatos.json`, ver la tabla):
  el lector recorre la hoja, toma el año de cada fila de año y el mes de cada nombre, y ordena de
  más antiguo a más reciente antes de validar la continuidad.

## Índice de precios de insumos de la construcción

Página `https://www.bcv.org.ve/estadisticas/insumos-de-la-construccion`. Los archivos publicados son
`.xls` legibles (`indice_de_precios_de_insumos_de_la_construccion_segun_nivel.xls` y variantes
trimestral, anual y por productor/mayorista), con hojas `Con Impuesto` y `Sin Impuesto`, columnas
`AÑO`, `MES`, `Productor`, `Mayorista`, base 2007 = 100. **No sirve para 2026**: sus filas llegan hasta
2019 (la última, «Ene19/Dic18», mezcla variaciones y niveles). La Tarea 6 no tiene lector para él; la
serie de insumos entra por el CSV canónico (S1 §7.3; orden de caída de §10). No se archivó.

## Estado de Precios (paso 0.7 del spec)

La columna `Estado` de la pestaña Precios es **por insumo**: `ui/paginas/hoja.py` (línea 1236) la arma con
`p.estado` de `hoja.precios_de_version`, que devuelve una fila por insumo (`origen_de_precios`, ordenado
por código de insumo). Los `origen_ids` de los hallazgos R11 y R12 serán **códigos de partida**. Por eso
la Tarea 10 cruza por `insumo_id` interno y no por `origen_ids`. (Verificado leyendo el código; no se
abrió una versión de OF-001 en el navegador.)

## Formatos para `adapters/bcv/formatos.json`

| Clave | Valor (JSON) |
|---|---|
| `tasa.trimestre_por_letra` | `{"a": 1, "b": 2, "c": 3, "d": 4}` |
| `inpc.hoja` | `"Base Diciembre 2007"` |
| `inpc.etiqueta_periodo` | `""` |
| `inpc.etiqueta_valor` | `"Indice"` |
| `inpc.marca_provisional` | `"(*)"` |
| `inpc.base` | `"Diciembre 2007 = 100"` |
| `inpc.disposicion` | `"anio_en_filas"` |
