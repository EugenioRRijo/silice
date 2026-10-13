# Causas raíz de los errores en los presupuestos reales de ARENAZA

**Fecha:** 2026-10-13 · **Rama:** `inc/spec-1.5` · **Estado:** análisis terminado, insumo del spec de Silice 1.5

## Alcance y anonimato

Se analizaron los presupuestos que ARENAZA entregó y le aprobaron sus clientes: tres libros de Excel y dos PDF.
**Los libros de Excel no entran al repositorio** (los cubre `.gitignore`, ver abajo). Aquí se citan con un nombre
neutro y sin datos del cliente, del contratista, RIF, direcciones, rutas de red ni nombres de personas. La tabla que
une cada nombre neutro con su archivo real queda solo en el equipo de Eugenio.

| Nombre neutro | Qué es | Versiones | Subtotal sin IVA entregado (USD) |
|---|---|---|---|
| **Libro A** | Mantenimiento y reconstrucción de paredes de un apartamento | una | 9 955,65 |
| **Libro B** | Rehabilitación de paredes, frisos, carpintería y vigas de un piso | B-1 y B-2 (montos distintos) | 12 917,54 (B-1) y 16 491,80 (B-2) |
| **Libro C** | Rehabilitación de paredes, frisos y revestimientos de áreas comunes | C-1 (20:15) y C-2 (21:03); por la hora, C-1 es el borrador. Sus hojas que no son APU son idénticas | 24 311,92 (las dos) |
| **PDF 001** | Puntos WiFi de oficina | una | 1 109,29 |
| **PDF 002** | Puntos de red y CCTV con rack | una | 5 410,73 |

Los PDF ya estaban en el repositorio desde el 2026-08-26 (`data/samples/telecom/`). Sus errores aritméticos ya
figuran en `data/telecom/fuentes/README.md`, y el auditor ya detecta la diferencia de 80 m contra 90 m (regla R1).

**PDF entregados de los libros** (también confidenciales, en la carpeta local). Hay uno por libro y tres más:
"IR" (24 311,92, igual a C-1 y C-2: no se puede saber de cuál salió, porque sus valores son idénticos), "QA v1" (una
versión de julio, 14 542,09) y "RC". Este último imprime **dos** presupuestos: una "Opción B" (11 730,51) y la
"Opción definitiva" (15 451,69). Ninguno de los dos coincide con ningún Excel recibido. **Los PDF de B están cruzados
de nombre:** el que se llama como B-1 imprime los totales de B-2 y al revés.

**IVA y totales con IVA** (valores guardados en cada libro e impresos en su PDF; los usa como literales
`scripts/fusion_verificar.py`):

| Documento | Sin IVA | IVA 16 % | Total con IVA |
|---|---|---|---|
| Libro A | 9 955,65 | 1 592,90 | 11 548,55 |
| Libro B-1 | 12 917,54 | 2 066,81 | 14 984,34 |
| Libro B-2 | 16 491,80 | 2 638,69 | 19 130,49 |
| Libro C (C-1 y C-2) y PDF "IR" | 24 311,92 | 3 889,91 | 28 201,83 |
| PDF "QA v1" | 14 542,09 | 2 326,73 | 16 868,82 |
| PDF "RC", Opción B | 11 730,51 | — | 13 607,39 |
| PDF "RC", Opción definitiva | 15 451,69 | 2 472,27 | 17 923,97 |

Método: se leyeron todas las fórmulas, los nombres definidos, los estilos y los **valores guardados** de cada hoja
(openpyxl, `data_only`). Después se comparó cada referencia con la forma real de la hoja a la que apunta. Los PDF se
leyeron por coordenadas de palabra, no por texto plano. Los scripts del análisis son descartables y no se versionan.

## Cómo funcionan los libros

Los tres libros salen de la misma plantilla, en evolución. Son `.xlsx` **sin VBA**: toda la automatización está en
fórmulas y en unos 30 nombres definidos (`FCAS`, `ADMON`, `UTIL`, `IVA`, `HERR`, `FLETE`, `CAMION`, `VERT`,
`PRECIOS`, `LMAT`/`LMO`/`LEQ`, `SUBSINIVA`, `IVATOT`, `TOTALGEN`…).

```
PORTADA ─┐
INSUMOS (precios MT/MO/EQ + parámetros) ──VLOOKUP──> APU-nn (un análisis por partida)
MEDICIONES (cómputos) ──SUMIF──┐                          │ INDIRECT("'APU-"&nº&"'!G48")
                               └──> PRESUPUESTO <─────────┘
PRESUPUESTO ──> RESUMEN · CRONOGRAMA (Gantt + curva S) · CONTROL DE OBRA (avance, variaciones)
            ──> PLAN DE PAGOS (anticipo, retención, IVA) · GASTOS / CONTROL DE GASTOS
APU-nn ──AUX (oculta, INDIRECT a filas fijas)──> PROCURA (explosión de insumos)
```

Cálculo de un APU: MO = Σ jornales × FCAS ÷ rendimiento. Equipos = Σ costo/día ÷ rendimiento + herramientas (% de MO).
Transporte = flete × m³ de escombro ÷ capacidad del camión + m³ × tarifa del vertedero. CD = materiales + MO + equipos
+ transporte. Después se suman administración sobre CD, utilidad sobre (CD + administración) e IVA sobre el subtotal.
Todo está en USD: ningún libro tiene bolívares, tasa ni fecha de tasa.

## Hallazgos y su efecto en lo entregado

**Conclusión principal.** En las versiones finales, la hoja PRESUPUESTO de A y B **cuadra con sus APU**: cada P.U.
coincide con el de su hoja y cada desglose suma. Lo que está roto es casi todo lo que se calcula *después* del
presupuesto, y además dos cosas dentro de C. Los totales aprobados de A y B son coherentes. El de C tiene un error de
cálculo y un parámetro alterado a mano.

| # | Hallazgo | Dónde | ¿Cambia el total aprobado? | Causa |
|---|---|---|---|---|
| H1 | Los costos directos de la partida de mayor monto (alucobond, ~40 % de la obra) **omiten los equipos**: `CD = G12+G21` deja fuera `G29` (1,8257 USD/u) | C-2 APU-07 y C-1 APU-09 | **Sí:** faltan 205,92 USD sin IVA (238,87 con IVA) | C3 |
| H2 | La utilidad de esa misma partida está **escrita a mano en 2 %** (`F40 = 0,02`); las demás usan `=UTIL` (10 %). La cabecera dice "Utilidad 10%" | C-2 APU-07 y C-1 APU-09 | **Sí, si no fue intencional:** 761,62 USD sin IVA | C6 |
| H3 | RESUMEN da una composición del costo de 24 495,46 y un subtotal de 24 311,92: **la hoja misma no cuadra** por 183,53 (el equipo de H1, que está en el desglose pero no en el CD) | C, RESUMEN | No (es el síntoma visible de H1) | C3 |
| H4 | Los números de partida 6 y 7 están **duplicados**: hay filas con cantidad 0 que repiten el número (filas 19 y 22 frente a 23 y 24). En C ninguna hoja derivada busca por número, así que hoy no tiene efecto; es un riesgo para cualquier búsqueda futura | C-1 y C-2 | No | C2 |
| H5 | **Enlaces parcheados a mano por fila** (*corregido el 2026-10-13, ver errata*): en lugar de la fórmula de la plantilla, cada fila de PRESUPUESTO lee su APU con una referencia directa escrita a mano (`='APU-08'!G44`), atada al nombre de la hoja. Los valores guardados **sí** coinciden con sus fórmulas. Si la fila volviera a la fórmula de la plantilla (por número de partida) o se renombraran las hojas, en C-1 la partida 6 pasaría de 2 644,39 a 5 917,06 y la 7 de 9 710,63 a 0 (en C-2 no cambiaría nada) | C-1 y C-2 | No: es un riesgo, no un error del total | C2 |
| H6 | CRONOGRAMA lee el rendimiento siempre en `F28`, pero los APU lo tienen en F27, F32, F21 o F23. **En A todas las duraciones dan 0 ("0 semanas")**. En B, ocho partidas duran 0 (1-6, 15 y 16) y otras usan el rendimiento de otra celda (25 en vez de 150; 3 en vez de 15). La curva S, el avance planificado de CONTROL DE OBRA y la holgura quedan falseados | A, B | No (el cronograma es un anexo, pero se entregó) | C1, C3 |
| H7 | PROCURA (lista de compras) **no cuadra con el presupuesto**, y sus propias filas de verificación lo muestran: −6 969,49 en materiales, −4 861,47 en MO, −246,69 en equipos y **+191 309,86 en transporte** | B-2 (y A) | No, pero la lista de compras está mal | C1, C3 |
| H8 | AUX, que alimenta PROCURA, lee filas fijas de cada APU. Se salta líneas reales de insumos (hasta 12 en un APU), lee filas de encabezado ("Código") y toma el **flete en USD como si fueran m³ de escombro** (`G43` en vez de la celda del escombro). De ahí sale el +191 309,86: casi todo viene de APU-14 de B, donde `G43` vale 410 (el flete) y el escombro está en `G41` | A, B | No | C1, C3 |
| H9 | La columna REND. de PRESUPUESTO muestra 25 en las partidas 15 y 16, cuyo rendimiento real es 11 y 12 (lee `F21` en vez de `F23`) | B | No (solo se muestra) | C1 |
| H10 | `#REF!` en RESUMEN: 4 de 5 capítulos sin monto (A y B). También en CRONOGRAMA (C, 6, incluida la fila del alucobond) y en la plantilla APU-ejm (B, 3); CONTROL DE OBRA de C hereda 22 valores `#REF!` | A, B, C | No | C4 |
| H11 | Los nombres `MEDP1`…`MEDP11` apuntan a **otro libro en un servidor de la red de la empresa** | A, B | No (fuera de esa red, `#REF!`) | C5 |
| H12 | Medidas **escritas dentro de las fórmulas** (`=9.73*2.75`), un factor `0.28` sin explicación y un rendimiento fijo (`=G27/12`) en lugar de la celda de rendimiento | B (MEDICIONES), C (APU-07) | No en sí, pero no se pueden rastrear | C6 |
| H13 | Unidad y cantidad no concuerdan: "90 **metros**" a 99,75 da 299,25. El precio es por rollo (en el PDF 001 está escrito como texto: `3*99.75`). Coherente sería 3 rollos o 8 977,50 | PDF 001 y 002 | No (el monto es el que se quiso), pero el documento se contradice | C7 |
| H14 | "Total cómputos métricos" **suma metros con piezas** (119 y 156) | PDF 001 y 002 | No | C7 |
| H15 | Notas: "la mano de obra será el 50 % del presupuesto total", pero **no está en el TOTAL**. Un precio en amarillo "en veremos por los precios del señor…" se entrega como firme. Las notas de 001 están copiadas en 002 (misceláneos que 002 no tiene) | PDF 001 y 002 | **Sí: el total no incluye la mano de obra declarada** | C7 |
| H16 | Cómputos contra presupuesto en 002: además de 80/90 m, protector 3 contra 4, cajetín 10 contra 5, dos renglones de los cómputos que no se presupuestan y seis presupuestados que no están en los cómputos | PDF 002 | Indirecto | C7 |
| H17 | Aritmética de fila: 5 × 289,00 ≠ 1 446,65 y 7 × 42,99 ≠ 303,93 (+4,65). *Ya registrado en septiembre* | PDF 002 | Sí, +4,65 | C7 |
| H18 | En B-2, la utilidad del APU-09 está **escrita a mano en 30 %** (`G59 = G58*0.3`); B-1 usa `=UTIL` (10 %). El PDF definitivo "RC" también imprime el 30 % | B-2, APU-09 | **Sí, si no fue intencional:** 746,98 USD sin IVA de más frente al 10 % | C6 |

Cifras de H1: 1,82565 USD/u × 100,53 = 183,53 de CD. Con administración (×1,10) y utilidad de 2 % (×1,02) quedan en
205,92, y con IVA (×1,16) en 238,87. Cifra de H2: (10 % − 2 %) × 94,7004 × 100,53 = 761,62.

**Errata (2026-10-13, misma fecha).** La primera versión de H5 decía que el borrador C-1 tenía "valores guardados
que no corresponden a sus fórmulas" y que el total "cae 6 437,96 al recalcular". Era falso: el análisis inicial
supuso que todas las filas usaban la fórmula por número de partida, y en C las filas tienen referencias directas
puestas a mano. Lo detectó la regla al verificarse sobre los libros. Ningún libro tiene valores guardados
desactualizados. H5 queda corregido arriba y se informa como L2 (advertencia), no como L3.

**Correcciones del verificador de hechos (2026-10-13, revisión V5).** H1 y H2 están en APU-07 de C-2 y en APU-09 de
C-1. El efecto de H4 sobre CRONOGRAMA era falso y se quitó. En B duran 0 ocho partidas, no seis. El APU "estándar"
de C3 es el de 59 filas. En C también hay formato condicional. Se añadió H18 (utilidad del 30 % en B-2), que el
primer análisis no vio y que la regla L6 sí detectó.

## Causas raíz

Dieciocho hallazgos salen de **siete causas**. La primera explica casi todos los del Excel.

**C1. Referencias por posición fija dentro de texto.** PRESUPUESTO, CRONOGRAMA y AUX leen los APU con
`INDIRECT("'APU-"&nº&"'!$G$48")`. La dirección es un *texto*, así que Excel no la corrige cuando se insertan o borran
filas. Cada APU crece o se achica según cuántos insumos lleve, y en estos libros hay **más de diez formas distintas de APU**
(de 41 a 81 filas). Así cualquier referencia fija termina apuntando a la celda equivocada. Prueba: la nota de la
propia plantilla dice "rendimiento (F28) y escombro (G43)", y en el APU-01 están en F27 y G42. La plantilla se
modificó después de escribir las hojas que la leen.

**C2. Parches manuales sobre C1.** Para compensar C1, en B y C se reescribió a mano la dirección de cada fila del
presupuesto (`G48`, `G50`, `G45`, `G44`… según la partida). El parche está atado al *nombre* de la hoja. Al renombrar
o reordenar los APU (C-1) o al reutilizar un número de partida (H4), el parche queda apuntando a otro lado y nada lo
avisa.

**C3. Hojas derivadas escritas para una sola forma de APU.** CRONOGRAMA, AUX y PROCURA suponen el APU "estándar" de
59 filas (APU-ejm): rendimiento en F28, insumos en filas 10-17/22-25/33-36, escombro en G43. Ninguna se rehízo cuando
aparecieron APU de otras formas. H1 es la misma causa dentro de un APU: se copió un bloque de equipos y la fórmula
del CD no se amplió para incluirlo.

**C4. Borrado de filas u hojas con referencias directas.** Al quitar capítulos del presupuesto o hojas de ejemplo,
las fórmulas que los citaban quedan en `#REF!` y nadie lo nota porque el total no cambia (H10).

**C5. Copia de hojas entre libros.** Al copiar una hoja desde otro libro, Excel arrastra sus nombres definidos con un
vínculo al libro de origen (H11).

**C6. Datos y decisiones metidos en fórmulas.** Medidas, factores, rendimientos y un parámetro global (la utilidad)
quedan escritos dentro de fórmulas sueltas, sin fuente ni marca de "valor manual" (H2, H12, H18). La convención "ámbar =
editable" existe, pero nada impide editar otra celda.

**C7. Documento sin modelo detrás (PDF).** Los PDF son tablas escritas a mano: no hay relación entre cómputos y
presupuesto, ni entre unidad, cantidad y precio. Por eso aparecen sumas de magnitudes distintas, precios pendientes
entregados como firmes y notas que contradicen el total (H13-H17).

**Por qué nadie lo vio.** Los controles que tienen los libros no pueden detectar estas causas. La columna VERIF.
comprueba que `P.U. = subtotal + utilidad` *de la misma fila*, así que da 0 aunque la fila lea otro APU. Las filas
"Dif. vs presupuesto" de PROCURA y la composición de RESUMEN **sí muestran el error** (H3, H7), pero en A y B solo PLAN DE
PAGOS tiene formato condicional: nada se pinta, nada bloquea y nada se informa.

## Qué significa para Silice

1. Silice debe **leer** estos libros por *rótulo y nombre definido*, nunca por celda fija. Debe reconstruir cada APU
   con su forma real y comparar lo que el libro dice contra lo que el libro calcula. Así detecta C1-C6 como hallazgos
   con su celda de origen.
2. Silice debe **devolver** el libro calcado (mismas hojas, colores, rótulos y fórmulas visibles) pero sin esas causas
   por construcción: APU de forma uniforme y referencias por nombre definido. Debe incluir una hoja de auditoría,
   trazabilidad y alertas, y valores guardados que coincidan con lo que calcula Silice (contra H5).
3. Las reglas nuevas que salen de aquí van al spec de Silice 1.5:
   - integridad de referencias;
   - `#REF!` y vínculos externos;
   - valor guardado contra fórmula;
   - parámetro global sobrescrito;
   - componente calculado que no entra en el total;
   - número de partida duplicado;
   - suma de unidades distintas;
   - unidad, cantidad y precio incoherentes;
   - precio pendiente sin fuente;
   - nota que contradice el total.
