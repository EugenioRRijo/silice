# Oráculo del libro mínimo (Sílice 1.2.0, Task 2.6)

Tabla **hecha a mano** de cómo se ve `libro_minimo.xlsx` en Excel y de dónde cae cada celda en el contrato
neutro de la réplica visual (RS2-1) y en la instantánea de Univer. De esta tabla sale `libro_minimo.json`; el
JSON no sale de `visual.py`. Lo leen `tests/unit/test_replica_oraculo.py`, `tests/integration/test_api_replica_oraculo.py`
y, en la tarea 2.4, `frontend-desktop/src/replica/aUniver.test.ts`.

## Cómo se dedujo

La fuente de cada valor es el **contenido del archivo** (`xl/worksheets/sheetN.xml`, `xl/styles.xml`,
`xl/workbook.xml`, abiertos con `zipfile`, no con el código bajo prueba) leído con las reglas de ECMA-376, y el
código de `libro_minimo.py`, que dice qué se quiso poner. Reglas usadas:

- **Coordenadas.** `ref` es la referencia A1 sin `$`. `fila` y `columna` son de Excel (base 1; A = 1, Z = 26,
  AA = 27). `fila0` y `columna0` (base 0) son las posiciones en `cellData[fila0][columna0]` de Univer y se
  obtienen restando 1. Ejemplo: `F12` → fila 12, columna 6 (A=1, B=2, C=3, D=4, E=5, F=6) → `cellData[11][5]`.
  `AA3` → fila 3, columna 27 → `cellData[2][26]`.
- **Mostrado.** El contrato lleva el **valor guardado** como texto, no el texto formateado: un número es un
  decimal en texto (`1234.5`, no `1,234.50`; el formato viaja en `formato_numero`), una fecha es ISO (`<v>46313</v>`
  con formato de fecha es el 18/10/2026: el 1 de enero de 2026 es el serial 46023 y el 18 de octubre es el día 291
  del año, 46023 + 290 = 46313), un booleano es `TRUE`/`FALSE` (`t="b"`, `<v>1</v>`) y una celda con fórmula
  muestra su valor guardado (`F12`: `<f>F11*2</f><v>200</v>` → `200`).
- **Anchos.** El archivo guarda `width` según ECMA-376 §18.3.1.13:
  `Truncate((caracteres × 7 + 5) / 7 × 256) / 256`. Para un número entero `w` de caracteres eso es
  `w + 182/256 = w + 0.7109375` (Truncate(256 w + 182.857…) = 256 w + 182). Por eso 24 → `24.7109375`,
  14 → `14.7109375`, 20 → `20.7109375`, 12 → `12.7109375`, 15 → `15.7109375`, 10 → `10.7109375`; se verificó
  leyendo el atributo `width` de `<col>` en el XML. Un `<col min="2" max="3">` vale para las columnas 2 y 3.
  Una columna sin `<col>` (E, G…) usa el ancho por omisión de Excel y no se escribe.
- **Altos.** `ht` del `<row>` en puntos (`21.75`, `30`); el alto por omisión (15) no se escribe. Un número entero
  se escribe sin ceros sobrantes (`"30"`, no `"30.0"`).
- **Ocultas.** `<col hidden="1">` (columna 3 de `PLAN DE PAGOS`) y `<row hidden="1">` (fila 5) van en
  `ocultas_columnas` / `ocultas_filas`, y **conservan sus celdas y su ancho**: ocultar no renumera nada, así que `D3`
  sigue siendo columna 4 y `A5` fila 5. La hoja `AUX` (`state="hidden"`) es `visible: false` y sigue en su sitio
  en el orden del libro.
- **Combinada.** `<mergeCell ref="A1:D1"/>`. En Excel una combinada se dibuja con el relleno, la fuente y la
  alineación de su celda superior izquierda; las celdas que cubre (`B1`, `C1`, `D1`; el archivo las guarda con el
  estilo del origen, `s="4"`) **no tienen aspecto propio** y no se piden en `celdas`. Decisión de este oráculo,
  ver «Regla de las celdas cubiertas» abajo. La combinada cruza la columna oculta C y no cambia nada.
- **Paneles fijos.** `<pane xSplit="1" ySplit="2" topLeftCell="B3" state="frozen"/>` → `fijas: "B3"` (la primera
  celda que **no** queda congelada: una columna y dos filas fijas).
- **Hoja con espacio.** `PLAN DE PAGOS` viaja tal cual, sin comillas ni escape; las comillas simples de `'PLAN DE
  PAGOS'!F12` solo existen dentro de las fórmulas.
- **Celdas listadas.** Las que tienen valor, fórmula o un estilo distinto del por omisión (xf 0), ordenadas por
  fila y, dentro de la fila, por columna. Las celdas vacías con el estilo por omisión no se listan.
- **Estilos.** `estilos` es una lista sin repetidos, en el orden de la **primera aparición** recorriendo las hojas
  en su orden y las celdas por fila y columna. El estilo por omisión del libro (Calibri 11, color de texto del
  tema, sin relleno ni bordes, formato General) cuenta como un estilo más cuando una celda con valor lo usa
  (aquí el índice 1).
- **Colores.** Los rellenos y colores de fuente son `rgb` explícitos (`FF1F3864` → `#1F3864`). El único color de
  tema es el de la fuente por omisión (`<color theme="1"/>`): el índice de tema 1 es `dk1`, el color de texto, y es
  negro en todo tema de Office → `#000000`.
- **Bordes.** `thin` en los cuatro lados de `encabezado` (`<left/><right/><top/><bottom style="thin">`); el orden
  del contrato es arriba, derecha, abajo, izquierda. El color del borde no viaja.

### Regla de las celdas cubiertas (a ratificar)

La lectura literal del contrato («celdas con valor o estilo distinto del por omisión») incluiría `B1`, `C1` y `D1`,
porque el archivo les guarda `s="4"`. Este oráculo **no las lista**: lo que se ve en Excel en `A1:D1` lo dicta
solo `A1`, así que listarlas duplicaría el estilo sin cambiar el dibujo ni lo que Univer necesita (`mergeData`
más la celda origen). Si el orquestador decide lo contrario, hay que añadir tres filas a la tabla y al JSON y
corregir `visual.py`.

## Hojas

| Hoja | visible | filas | columnas | anchos | altos | ocultas_filas | ocultas_columnas | combinadas | fijas | Deducción |
|---|---|---|---|---|---|---|---|---|---|---|
| `"PORTADA"` | `true` | `4` | `2` | `{"1": "24.7109375", "2": "14.7109375", "3": "14.7109375"}` | `{"1": "21.75"}` | `[]` | `[]` | `[]` | `null` | Celdas hasta B4 (`dimension A1:B4`). `<col 1>` 24 → 24.7109375; `<col min=2 max=3>` 14 → 14.7109375 para B y para C. Fila 1 con `ht="21.75"`. Sin ocultas, combinadas ni paneles. |
| `"PLAN DE PAGOS"` | `true` | `12` | `27` | `{"1": "20.7109375", "2": "12.7109375", "3": "12.7109375", "4": "15.7109375", "6": "10.7109375"}` | `{"1": "30"}` | `[5]` | `[3]` | `["A1:D1"]` | `"B3"` | Celdas hasta la fila 12 (`F12`) y la columna AA = 27. Anchos de A, B, C (oculta, conserva el 12), D y F; E no tiene `<col>`. Fila 1 de 30 pt; fila 5 oculta sin alto propio. |
| `"AUX"` | `false` | `1` | `1` | `{}` | `{}` | `[]` | `[]` | `[]` | `null` | `state="hidden"` en `workbook.xml`; una celda (`A1`). |

## Estilos

Orden de primera aparición: `PORTADA!A1`, `PORTADA!A2`, `PORTADA!B2`, `PORTADA!B3`, `PLAN DE PAGOS!A1`,
`PLAN DE PAGOS!A2`, `PLAN DE PAGOS!AA3` (los demás repiten uno de estos). `bordes` es
`[arriba, derecha, abajo, izquierda]`.

| Estilo | relleno | fuente | tamano | negrita | cursiva | subrayado | color | alineacion_h | alineacion_v | ajustar_texto | formato_numero | bordes | En palabras |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `0` | `null` | `"Calibri"` | `"14"` | `true` | `false` | `false` | `"#000000"` | `null` | `null` | `false` | `"General"` | `[null, null, null, null]` | `xf 1`: Calibri 14 en negrita, color de texto del tema, sin relleno. Título de `PORTADA`. |
| `1` | `null` | `"Calibri"` | `"11"` | `false` | `false` | `false` | `"#000000"` | `null` | `null` | `false` | `"General"` | `[null, null, null, null]` | `xf 0`: el estilo por omisión (Calibri 11, texto del tema). |
| `2` | `null` | `"Calibri"` | `"11"` | `false` | `false` | `false` | `"#000000"` | `null` | `null` | `false` | `"#,##0.00"` | `[null, null, null, null]` | `xf 2`: por omisión con formato `#,##0.00` (numFmt 164). |
| `3` | `null` | `"Calibri"` | `"11"` | `false` | `false` | `false` | `"#000000"` | `null` | `null` | `false` | `"dd/mm/yyyy"` | `[null, null, null, null]` | `xf 3`: por omisión con formato de fecha `dd/mm/yyyy` (numFmt 165). |
| `4` | `"#D9E1F2"` | `"Arial"` | `"12"` | `true` | `false` | `false` | `"#1F3864"` | `"center"` | `"center"` | `true` | `"General"` | `[null, null, null, null]` | `xf 4`: Arial 12 en negrita azul oscuro `#1F3864` sobre relleno sólido `#D9E1F2`, centrado horizontal y vertical, texto ajustado. |
| `5` | `null` | `"Calibri"` | `"11"` | `true` | `false` | `false` | `"#000000"` | `null` | `null` | `false` | `"General"` | `["thin", "thin", "thin", "thin"]` | `xf 5`: negrita con borde fino en los cuatro lados. |
| `6` | `null` | `"Calibri"` | `"11"` | `false` | `true` | `true` | `"#C00000"` | `"right"` | `"top"` | `false` | `"General"` | `[null, null, null, null]` | `xf 6`: cursiva, subrayado simple, rojo `#C00000`, alineado a la derecha y arriba. |

## Celdas

`mostrado` y `formula` son literales JSON (la cadena vacía sería `""`; ninguna celda de este libro lo es).

| Celda | hoja | ref | fila | columna | fila0 | columna0 | mostrado | formula | estilo | Deducción |
|---|---|---|---|---|---|---|---|---|---|---|
| PORTADA!A1 | `"PORTADA"` | `"A1"` | `1` | `1` | `0` | `0` | `"Obra ficticia"` | `null` | `0` | Texto compartido 0; `s="1"` = estilo 0. |
| PORTADA!A2 | `"PORTADA"` | `"A2"` | `2` | `1` | `1` | `0` | `"Monto contratado"` | `null` | `1` | Texto sin `s`: xf 0, el por omisión. |
| PORTADA!B2 | `"PORTADA"` | `"B2"` | `2` | `2` | `1` | `1` | `"1234.5"` | `null` | `2` | `<v>1234.5</v>`; `s="2"`: `#,##0.00`. El texto en pantalla sería `1,234.50`; el contrato lleva `1234.5`. |
| PORTADA!A3 | `"PORTADA"` | `"A3"` | `3` | `1` | `2` | `0` | `"Fecha de corte"` | `null` | `1` | Texto, estilo por omisión. |
| PORTADA!B3 | `"PORTADA"` | `"B3"` | `3` | `2` | `2` | `1` | `"2026-10-18"` | `null` | `3` | Serial 46313 con formato de fecha = 18/10/2026 → ISO sin hora. |
| PORTADA!A4 | `"PORTADA"` | `"A4"` | `4` | `1` | `3` | `0` | `"Vigente"` | `null` | `1` | Texto, estilo por omisión. |
| PORTADA!B4 | `"PORTADA"` | `"B4"` | `4` | `2` | `3` | `1` | `"TRUE"` | `null` | `1` | `t="b"`, `<v>1</v>` → `TRUE`; estilo por omisión. |
| PLAN DE PAGOS!A1 | `"PLAN DE PAGOS"` | `"A1"` | `1` | `1` | `0` | `0` | `"Plan de pagos ficticio"` | `null` | `4` | Origen de la combinada `A1:D1`; `s="4"`. `B1`, `C1`, `D1` no se listan (celdas cubiertas). |
| PLAN DE PAGOS!A2 | `"PLAN DE PAGOS"` | `"A2"` | `2` | `1` | `1` | `0` | `"Hito"` | `null` | `5` | Encabezado, `s="5"`. |
| PLAN DE PAGOS!B2 | `"PLAN DE PAGOS"` | `"B2"` | `2` | `2` | `1` | `1` | `"Monto"` | `null` | `5` | Encabezado, `s="5"`. |
| PLAN DE PAGOS!D2 | `"PLAN DE PAGOS"` | `"D2"` | `2` | `4` | `1` | `3` | `"Fecha"` | `null` | `5` | Columna D = 4 aunque la C esté oculta (la C se salta, no se renumera). |
| PLAN DE PAGOS!A3 | `"PLAN DE PAGOS"` | `"A3"` | `3` | `1` | `2` | `0` | `"Anticipo"` | `null` | `1` | Texto, estilo por omisión. |
| PLAN DE PAGOS!B3 | `"PLAN DE PAGOS"` | `"B3"` | `3` | `2` | `2` | `1` | `"1500.5"` | `null` | `2` | `<v>1500.5</v>`, `#,##0.00`. |
| PLAN DE PAGOS!D3 | `"PLAN DE PAGOS"` | `"D3"` | `3` | `4` | `2` | `3` | `"Tras la columna oculta"` | `null` | `1` | Columna 4 pese a la oculta C. |
| PLAN DE PAGOS!AA3 | `"PLAN DE PAGOS"` | `"AA3"` | `3` | `27` | `2` | `26` | `"Nota lejana"` | `null` | `6` | AA = 1×26 + 1 = 27 → columna0 26; `s="6"`. |
| PLAN DE PAGOS!A5 | `"PLAN DE PAGOS"` | `"A5"` | `5` | `1` | `4` | `0` | `"Fila oculta"` | `null` | `1` | La fila 5 está oculta (`hidden="1"`) pero conserva su número y su celda. |
| PLAN DE PAGOS!F11 | `"PLAN DE PAGOS"` | `"F11"` | `11` | `6` | `10` | `5` | `"100"` | `null` | `2` | Dato de la fórmula, `#,##0.00`. |
| PLAN DE PAGOS!F12 | `"PLAN DE PAGOS"` | `"F12"` | `12` | `6` | `11` | `5` | `"200"` | `"=F11*2"` | `2` | `<f>F11*2</f><v>200</v>`: la fórmula se muestra con `=` y el valor guardado es 100 × 2 = 200. Cae en `cellData[11][5]`. |
| AUX!A1 | `"AUX"` | `"A1"` | `1` | `1` | `0` | `0` | `"Hoja oculta"` | `null` | `1` | Hoja oculta, celda de texto por omisión. |

## Forma de `libro_minimo.json`

Es el cuerpo esperado de `POST /v1/libros/replica` para este libro (subido como `libro_minimo.xlsx`), con los
campos de `LibroVisual` (`adapters/hoja_empresa/visual.py`) tal como los serializa la API:

```text
{
  "nombre": "libro_minimo.xlsx",
  "hojas": [
    { "nombre": str, "visible": bool, "filas": int, "columnas": int,
      "anchos": { "<columna base 1>": "<ancho decimal en texto>" },
      "altos":  { "<fila base 1>": "<alto en puntos, decimal en texto>" },
      "ocultas_filas": [int], "ocultas_columnas": [int],
      "combinadas": ["A1:D1"], "fijas": "B3" | null,
      "celdas": [ { "ref": "F12", "fila": 12, "columna": 6, "mostrado": "200",
                    "formula": "=F11*2" | null, "estilo": int } ] } ],
  "estilos": [ { "relleno": "#RRGGBB" | null, "fuente": str | null, "tamano": "11" | null,
                 "negrita": bool, "cursiva": bool, "subrayado": bool, "color": "#RRGGBB" | null,
                 "alineacion_h": "left"|"center"|"right"|"justify" | null,
                 "alineacion_v": "top"|"center"|"bottom" | null, "ajustar_texto": bool,
                 "formato_numero": str,
                 "bordes": [arriba, derecha, abajo, izquierda] (cada uno "thin"|... | null) } ]
}
```

- Las claves de `anchos` y `altos` son **texto** (`"2"`), porque JSON no admite claves enteras; los valores son
  decimales en texto, nunca números.
- `bordes`, `ocultas_*`, `combinadas` y `celdas` son listas; `fijas` y los campos opcionales son `null` cuando
  no hay dato.
- `estilo` de cada celda es el índice en `estilos`.
- **`sha256` no está en el archivo**: depende de los bytes del `.xlsx` y no se puede escribir a mano. Las pruebas
  de Python lo comparan aparte con `hashlib.sha256(libro_minimo())`. Las de TypeScript no lo necesitan; si el tipo
  `LibroVisual` lo exige, deben rellenarlo con cualquier texto al cargar el JSON.
- El orden de `hojas` es el del libro, el de `celdas` es fila y luego columna, y el de `estilos` es el de
  primera aparición (ver arriba).
