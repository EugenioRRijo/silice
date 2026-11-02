# Coma decimal y punto de miles en todo lo que se teclea (2026-10-25)

**Decisión de Eugenio (2026-10-25), regla de producto:** «la coma para decimales y el punto para las decenas y
centenas (miles), para que no haya equivocaciones». Resuelve la decisión **D-8** de la Hoja
(`docs/especificaciones/2026-10-19-hoja-react-design.md`, que rechazaba la coma) y el riesgo de Componer, que con
`decimal_con_coma()` leía «1.000» como **uno** (un precio mil veces menor).

## La regla

Lo interpreta **un solo intérprete**, `aplicacion/cifras.py` (`cifra_escrita`, `texto_de_cifra`), sin `float`:

| Se acepta | Se rechaza (sin adivinar) |
|---|---|
| `0`, `1234`, `1234,5`, `0,005`, `-0,5`, `2,50` (conserva los decimales) | `2.5`, `1.23`, `0.12`, `0.123` (decimal anglosajón) |
| `1.234`, `1.000` (= mil), `12.345.678,9` (grupos de tres bien formados) | `1,234.5`, `1.2345`, `1.234.56`, `01.234`, `1,2,3` |
| blancos en los extremos | `1 234` (**el espacio de miles NO se acepta**: se confunde con dos cifras), `1 234` |
| | vacío (mensaje propio), `,5`, `5,`, `+5`, `NaN`, `Infinity`, `1e3`, `1_000`, cifras no ASCII |

Mensaje (con tildes, lenguaje llano): «Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles:
1.234,56.»; vacío: «Escriba un número. » + lo anterior. Ayuda junto a los campos: «Escriba los decimales con coma: 2,5;
el punto separa los miles: 1.234,56.» El cero negativo se lee como cero.

Oráculos: **una sola tabla escrita a mano**, `tests/fixtures/cifras_escritas.json` (30 aceptados, 47 rechazados, 11 de
escritura y 4 de escritura no canónica), que leen las dos pruebas: `tests/unit/test_aplicacion_cifras.py` y
`frontend-desktop/src/indicadores/cifraEscrita.test.ts`.

## Dónde se convierte (una vez por ruta, y por qué)

- **Rutas cuyo cuerpo es el texto de un campo tal como se tecleó** (Componer, las ediciones de la Hoja, las alturas del
  plano, el precio cotizado): lo interpreta `aplicacion/` **al recibir**, con `cifra_escrita`. Ya era así (D-8 lo
  proponía en el servidor) y es el servidor el que dice el error con la tabla, la fila y el campo. Lo que la API pone en
  esos campos editables (la precarga de Componer, la referencia MaPreX, las celdas de la Hoja) sale escrito con
  `texto_de_cifra`, para que una celda que nadie toca vuelva igual: «3.000» (tres, con tres decimales) se escribe
  «3,000» y nunca regresa como tres mil (prueba de ida y vuelta).
- **Rutas cuyo contrato ya es un decimal con punto** (control de obra, reajuste, escenarios, elaborar, existencias,
  asistente, simulador): el contrato **no cambia**; la pantalla lee lo tecleado con
  `src/indicadores/cifraEscrita.ts` (`leerCifra`) **antes de enviar**, muestra el error junto al campo y manda el
  decimal con punto. Es la misma regla, comprobada contra la misma tabla de oráculos.
- **No cambian** (texto de máquina, no tecleado): el JSON y los CSV de importación de terceros, el `.silice`, los
  libros, el Excel exportado, las respuestas de lectura de la API (la interfaz las formatea con `formatoEsVe`) y las
  propuestas del asistente de IA. Por eso `hoja.espacio_desde_filas` lee con la regla solo con `tecleado=True` (el
  editor); el asistente y el banco del experimento siguen con punto decimal: leer «1.125» m con la regla daría mil
  ciento veinticinco.

## Inventario

| Pantalla | Campo | Dónde se interpretaba | Cambio |
|---|---|---|---|
| Componer | rendimiento; cantidad, precio, depreciación, sueldo de cada fila | `aplicacion/composicion.py` `decimal_con_coma` (coma o punto; «1.000» = 1) | `cifra_escrita` al recibir; `decimal_con_coma` se retira. Mensaje: «En Equipos, fila 1 («Mezcladora»), la depreciación «0.005» no se entiende como número. Use la coma…» |
| Componer | precarga de una partida, fila de la referencia MaPreX, rendimiento propuesto, tablas de similares | `f"{valor:f}"` y `str(...)` (punto) | `texto_de_cifra` (coma decimal, punto de miles) |
| Componer | desglose, PU estimado, similares (lectura); aviso de guardado | texto de la API tal cual («2240.39») | `formatoEsVe` («2.240,39», el exacto en el `title`); el aviso dice «precio unitario 10,19» (el campo `precio_unitario` sigue con punto) |
| Hoja › Presupuesto | cantidad | `decimal_desde_texto` (punto; la coma era error) | `hoja.cifra_de_celda`; la vista la da con coma (`texto_editable`) |
| Hoja › APU | rendimiento, cantidad de cada línea | igual | igual (las líneas salen de `filas_desde_composicion`) |
| Hoja › APU | precio, depreciación, sueldo (solo lectura) | la pantalla les aplicaba `formatoEsVe` | llegan ya en es-VE (`texto_de_cifra`) y se muestran **tal cual**: una sola conversión (ronda 2, B3: «1.500» se veía «1,500») |
| Hoja › Parámetros | FCAS, bono, administración, utilidad | igual (`str(Decimal)` en la vista) | igual; la vista da «6,00», «0,15» |
| Hoja › Plan | fracción por período | igual | igual; la suma del aviso se dice con coma («suman 0,75») |
| Hoja › Espacio | x0, y0, largo, ancho, alto, x, y, z, pendiente | igual | igual, con `tecleado=True` |
| Hoja › Espacio | **vértices** «x,y,z; …» | punto decimal | **sin cambio (excepción declarada)**: la coma separa coordenadas; la ayuda lo dice |
| Hoja › Plano | altura de cada ambiente | `_altura` con `decimal_con_coma` | `cifra_escrita` («2.5» y «1.000» se rechazan) |
| Hoja › Precios | precio cotizado | `decimal_desde_texto` (punto) | `hoja.cifra_de_celda`; ayuda `AYUDA_CIFRAS` |
| Hoja › Cambiar moneda | tasa | se elige (venta/compra), no se teclea | sin cambio |
| Existencias | cantidad, existencia mínima, densidad, peso neto | `existencias/formato.ts` `leerCantidad` (coma o punto) | `leerCifra` antes de enviar; lectura con miles |
| Administración › Asistente | tope por sesión (USD) | se enviaba tal cual; el servidor (`asistente/administracion.py` `_tope`) cambiaba coma por punto («1.000» = 1) | el servidor lo lee con `cifra_escrita` (ronda 2, decisión del orquestador); la pantalla lo valida con `leerCifra` y lo manda **tal cual**; el valor de la API se edita con `textoParaEscribir` |
| Simulador | variación máxima (%) | `simulador/logica.ts` (exigía punto; aceptaba exponente) | `leerCifra` + tope 1000; precio de la tabla en es-VE |
| Control | parámetros (umbrales, eta, horas, recargo, penalización), Km, R, horas extra, cantidad de valuación, monto de costo | `aplicacion/control.py` `_decimal` (punto) | `leerCifra` antes de enviar; los valores actuales se editan con coma |
| Reajuste | R, peso de componente, cantidad ejecutada | `aplicacion/reajuste.py` `_decimal` (punto) | `leerCifra` antes de enviar |
| Escenarios | FCAS, bono, administración, utilidad, precio nuevo | `api/rutas/presupuestos.py` `decimal_desde_texto` (punto) | `leerCifra` antes de enviar; precargados con coma; totales en es-VE |
| Elaborar | fracción del plan de trabajo | `aplicacion/elaboracion.py` `plan_desde_filas` (punto) | `leerCifra` antes de enviar; el plan por omisión se ve «0,5» |
| Control, Reajuste, Simulador | enteros (días hábiles, día objetivo, meses, semilla, columna) | `int` | sin cambio: no son cifras decimales |
| Actualizar precios, Índices, Precios de la empresa, Catálogo, Histórico, Historial, Similares, Tablero, Revisar, Entregar, Libros, Inicio, Acerca, Bienvenida | — | no tienen cifras tecleadas | sin cambio |

## Lo que encontró la depuración

- **Renglón no enviado del Presupuesto:** `hoja_edicion.editar_cantidades` rearma la tabla completa con los renglones
  que la persona no tocó; los escribía con `texto_numero` (punto decimal). Con la regla nueva, un «1.125» no tocado se
  habría leído como mil ciento veinticinco. Ahora usa `hoja.texto_editable` (lo mostró `test_e9_lista_cada_celda...`).
- **El asistente de IA y el banco del experimento** arman el espacio con `filas_desde_espacio` (punto decimal) y lo
  pasan por `espacio_desde_filas`: por eso la regla solo aplica con `tecleado=True` (el editor), con su prueba
  (`test_el_texto_de_maquina_del_espacio_sigue_con_punto_decimal`).
- **«3.000» frente a «3,000»:** la prueba 3c-B4 decía «3.000 es tres». Con la regla, «3,000» es tres y «3.000» es tres
  mil (`test_tres_mil_con_punto_de_miles_es_tres_mil_y_tres_coma_cero_es_tres`). La vista nunca pone «3.000» en una
  celda: la escribe «3,000» o «3».

`scripts/simular_corpus.py` teclea sus cantidades con coma (pasa por `composicion_desde_tablas`) y las filas de
`scripts/recorrido_funcional.toml` que escribían decimales con punto pasan a coma.

## Ronda 2 (árbitro)

- **B3, doble conversión:** las filas del APU de la Hoja llegan en es-VE y `PestanaApu` les volvía a aplicar
  `formatoEsVe` («1.500» → «1,500»). Decisión: en las rutas cuyo texto ya es es-VE (las tablas que arma
  `filas_desde_composicion`) la pantalla **no** formatea; en las que llegan con punto (`Monto`, cantidades calculadas)
  formatea una vez. Revisadas con grep las demás aplicaciones de `formatoEsVe` en Hoja, Componer y Similares: todas
  reciben texto con punto. `datosDePrueba.ts` pasa al contrato real (coma). La afirmación anterior de esta bitácora
  («la pantalla solo reenvía») era falsa para `PestanaApu`.
- **Similares:** sus tablas llegan en es-VE y `compararDecimales` no las lee: las columnas ya no se ordenan.
- **Blancos:** `str.strip()` y `String.trim()` recortaban conjuntos distintos. Ahora los dos lados recortan
  exactamente `BLANCOS` (espacio, tabulador, saltos, VT, FF, NBSP, NEL y BOM), fijado en el oráculo; «\u2028» y
  «\u3000» al borde se rechazan en los dos. `textoParaEscribir` quita el «+» y los ceros a la izquierda como
  `texto_de_cifra`; un exponente («1E+3») solo lo escribe el servidor. La API debe escribir sus decimales en
  notación fija (`format(x, "f")`): el tope del Asistente, las fracciones del plan de Elaborar y la depreciación de
  Similares usaban `str` y salían «1E-7» (mantenimiento posterior a la ronda 2, corregido con su prueba).
- **Similares (página):** la API manda punto en notación fija y la pantalla formatea una sola vez (`presentar`
  y el rendimiento y los puntajes en es-VE), como el desglose de Componer.
- **Tope del Asistente:** el servidor lo lee con `cifra_escrita` («1.000» es mil); `asistente` puede importar
  `aplicacion.cifras` (hoja sin dependencias; guardia de capas ajustada).

## Lo que queda para Eugenio

1. **Vértices** de los recorridos declarados: siguen «x,y,z» con punto decimal (la coma separa coordenadas). Propuesta:
   separar las coordenadas con espacio («0 0 0; 2,5 0 0») en un cambio aparte, con su migración de lo guardado.
2. **Espacio de miles** («1 234»): rechazado por defecto. Si se quiere aceptar, es una fila más en el oráculo.
3. Textos de lectura que el servidor arma con cifras dentro (cambios del borrador, trazabilidad, avisos de control)
   siguen con punto; la interfaz solo formatea cifras sueltas. `comun/Variacion.tsx` (columnas de variación de
   Escenarios) tampoco se tocó.
