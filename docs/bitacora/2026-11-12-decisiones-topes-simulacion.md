# Decisiones de los topes: simulación y resultado (2026-11-12)

Eugenio pidió repasar las cuatro decisiones que dejó la rama `feature/topes-replica-listas`
([bitácora](2026-11-12-topes-replica-listas.md)), simular las opciones y quedarse con la mejor. Cada
caso corrió en su propio proceso sobre el código de `feature/tanda-2026-11-12`, con un tope de
120 s y la memoria pico medida. Los libros de los casos son construidos (openpyxl o XML a mano). Los
libros reales del equipo se pasaron también, **solo en local**: aquí no se cita ningún dato suyo; basta
decir que los seis quedaron dentro de los topes con mucho margen y que ninguna opción construida
rechaza ninguno.

Los tiempos se midieron con la suite completa corriendo a la vez: valen para comparar opciones, no
como cifra absoluta.

## 1. Las celdas combinadas cuentan para los topes de la réplica

| Caso | Opción A (construida: cuentan) | Opción B (no cuentan) |
|---|---|---|
| Título combinado A1:H1 | acepta | acepta |
| Combinada A1:A150000 (pasa la guardia: < 200.000 celdas combinadas) | **rechaza** con el aviso de filas de más | acepta y le declara al visor **150.000 filas** |
| Combinada A1:FZ1 (182 columnas) | **rechaza** con el aviso de la fila ancha | acepta y declara **182 columnas** |
| Combinada A1:XFD1048576 | la guardia la rechaza en 3 ms | igual |

**Decisión: A, como está.** `HojaVisual.filas` y `columnas` salen de `ws.max_row` y `ws.max_column`,
que incluyen las celdas cubiertas, así que con B el visor recibiría la hoja gigante que los topes
quieren evitar.

## 2. Las valuaciones pasan por la guardia

| Caso | Antes (sin guardia ni topes) | Ahora |
|---|---|---|
| .xlsx limpio | acepta | acepta |
| .xlsx con `vbaProject.bin` | **acepta** | rechaza (macros) |
| .xlsm sin macros | acepta | rechaza, como toda subida |
| Bomba de 3 millones de cadenas compartidas | **colgado más de 120 s** | rechaza en 3 ms |
| Hoja `Lineas` sin dimensión con A1048576 | recorre el millón de filas (0,59 s) | rechaza en 16 ms |

**Decisión: la guardia, como está.** La bomba de cadenas compartidas colgaba la importación de
valuaciones; F-D10 ya exige la guardia en toda subida de .xlsx, y el .xlsm se rechaza igual en las
listas, los presupuestos y el libro de la empresa.

## 3. Se recorren todas las hojas, no solo las que lee el núcleo

| Caso | Sin topes | A (construida: todas las hojas) | B (solo la hoja que lee el núcleo) |
|---|---|---|---|
| Lista + hoja «Historial» de 30.000 filas | acepta | rechaza | acepta |
| Lista + hoja oculta con A1048576 | acepta (el núcleo no la abre) | rechaza | acepta |
| Hoja activa con A1048576 | recorre el millón de filas | rechaza | rechaza |

B solo gana en libros con una hoja ajena al formato de más de 20.000 filas o de 100 columnas.
Ninguno de los libros reales tiene una así. A cambio, B obliga a que cada ruta repita qué hojas lee el
núcleo (la activa en las listas, `Datos`/`Presupuesto`/`APU`/`Insumos`/`Curva` en un presupuesto,
`Valuaciones`/`Lineas`/`Costos` en las valuaciones). Si una de esas listas se desfasa del núcleo, queda
un hueco de seguridad sin que nada lo avise.

**Decisión: A, como está.** Es la misma regla que el lector del libro conocido. El aviso nombra la
hoja y dice qué hacer: borrar lo que sobra.

## 4. Una lista de más de 20.000 filas se rechaza

| Filas de datos | A (tope de 20.000 filas, encabezado incluido) | B (tope de 200.000) |
|---|---|---|
| 5.000 | acepta, 2,9 s | acepta, 2,8 s |
| 19.999 | acepta, 12,3 s | acepta, 11,2 s |
| 20.000 | rechaza | acepta, 12,3 s |
| 50.000 | rechaza | acepta, **29,7 s** y 36 MB |
| 100.000 | rechaza | acepta, **60,4 s** y 70 MB |

Las listas de MaPreX del repositorio tienen 112 filas y son CSV, así que los topes no las tocan.

**Decisión: A, como está.** El costo lo pone el lector del núcleo, que no se toca. Con B, una lista de
100.000 filas tendría la petición un minuto entero.

**Lo único que cambia:** antes, el rechazo por tope de una lista o de un presupuesto llegaba como
«no se puede leer como libro de Excel (…)», aunque el libro sí se lee. Ahora sale el aviso del lector
tal cual: nombra el libro, la hoja y el tope, y dice qué borrar. «No se puede leer» queda solo para lo
que rechaza la guardia.

## 5. Las filas de hueco cuentan para el tope del libro

El agente de los índices del BCV encontró un libro que pasaba `MAX_CELDAS_LIBRO`. Tenía 1.000 hojas
sin `<dimension>`, cada una con una sola celda en A20000, y pesaba 466 KB. openpyxl entrega las filas
de hueco como tuplas vacías, que no sumaban nada a la cuenta, así que el libro costaba 20 millones
de filas: 12,1 s. Ahora cada fila entregada cuenta como una celda por lo menos
(`lector.filas_acotadas`). El mismo libro se rechaza en **3,0 s**, sin subir la memoria, con el
aviso de celdas de más.

Un libro legítimo no cambia: los reales tienen pocas decenas de hojas de unos cientos de filas. El
oráculo de `test_el_tope_del_libro_conocido_es_por_pasada_y_su_frontera_se_lee` cuenta ahora lo
mismo, sobre lo que entrega openpyxl.

Queda anotado y sin decidir otro hallazgo del mismo agente: el lector de la báscula no acota las
columnas de cada fila (`produccion/conectores/bascula.py`). La propuesta, `iter_rows(max_col=61)`,
cambia lo que se ve de un reporte ancho; la decide Eugenio.
