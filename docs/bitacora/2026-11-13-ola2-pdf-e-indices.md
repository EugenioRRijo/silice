# Ola 2, línea 4: el presupuesto en PDF y los índices del BCV en USD (2026-11-13)

Rama `feature/presupuesto-pdf` (desde `e2dfe116`), árbol `.worktrees/s2m4`. Dos funciones que la prueba de punta a punta
pidió y Sílice no tenía ([ESTADO §5, punto 6](../ESTADO.md)): sacar el presupuesto en PDF y expresar los índices del BCV
en USD para el reajuste de un contrato en dólares. Todo es ficticio (OF-001, «Obra ficticia «El Ñandú»», «Contrato
ficticio en USD», FIC-INPC y tasas inventadas); el informe con datos reales vive **solo** en el equipo de Eugenio y de él
solo se tomaron los dos pedidos (sin una cifra ni un nombre). `core/` no cambia (`git diff e2dfe116 --stat -- core/`
vacío), ningún archivo congelado del experimento cambia y no se tocó nada de otra línea (el lector y el perfil del libro y
la agrupación por frente son de la línea 3; la pestaña APU, de la línea 2).

Las decisiones se **simularon** (guiones del scratchpad de la sesión, `ola2/l4/sim_pdf.py` y `ola2/l4/sim_usd.py`, con
datos ficticios) y son **provisionales**: Eugenio las ratifica. Requisitos: RF-213 y RF-214 en el [ERS](../ERS.md); manual:
§4.2, §9.4 y §9.5 de [manual_usuario.md](../manual_usuario.md).

## 1. El presupuesto en PDF (RF-213)

**Qué hay antes.** La Hoja exporta a Excel (`GET /v1/hoja/borradores/{id}/excel`, `aplicacion/hoja_exportar.py`); los
reportes viales, el reajuste y el control también dan Excel. No había ningún PDF del presupuesto («Exportar a PDF: no
existe»). Sí había una biblioteca de PDF en el proyecto: `reportlab` (extra `informes`, en la capa básica del instalador,
`instalador/manifiesto.toml`), que solo usaban los scripts de informes, y `pdfplumber` (extra `pdf`) para leer PDF.

**Qué hace.** «Descargar PDF», junto a «Descargar Excel» en la franja del Presupuesto (grupo «Exportar la hoja»), baja
`presupuesto_{versión}.pdf` del borrador vivo: el encabezado (obra, versión o «Borrador sin guardar», los cambios sin
guardar, la fecha del presupuesto, la de emisión, la moneda y el resumen de la auditoría); una tabla con número, código,
descripción, unidad, cantidad, precio unitario y total; el subtotal, el IVA (16 %, `aplicacion/impuestos.con_iva` sobre
el total exacto, como la pestaña) y el total con IVA; y después un APU por página: código y descripción, unidad y
rendimiento, los parámetros (FCAS, bono, administración y utilidad), las tablas de materiales, equipos y mano de obra con
su subtotal por unidad de partida y el cierre hasta el precio unitario. Con `?partida=AF-LLAVE` sale solo ese APU
(`apu_{versión}_{partida}.pdf`; 404 «La partida «X» no tiene un APU valorado en este borrador.»).

**Cómo.** `aplicacion/presupuesto_pdf.py` en dos pasos: `documento_de_la_hoja(vivo, hoy, partida=, agrupar=)` arma un
`DocumentoPdf` solo de textos con las vistas de la Hoja (`hoja_vista.resumen`, `vista_presupuesto`, `vista_apu`), bajo el
cerrojo del borrador (las cifras son de un mismo `rev`); los montos ya calculados por el servidor se escriben con coma
decimal y punto de miles (`aplicacion.cifras.texto_de_cifra`), las cantidades del APU exactas y los precios a dos
decimales, y los conceptos del cierre de `aplicacion/hoja.py` (congelado, sin tilde) se escriben con ella
(«+ Administración»). `pdf_en_bytes(documento)` lo dibuja con reportlab. La ruta va en `api/rutas/hoja_exportar.py` (sin
tocar `api/main.py`), con el acceso del Excel: una cuenta con `LEER_PROYECTO` y SU borrador; la clave de API, 403;
`no-store`; no escribe nada. Tiempo medido: OF-001 (30 partidas, 30 APU) 1,4 s y 105 KiB; un documento ficticio de 300
renglones y 300 APU, 307 páginas, 501 KiB y 4,8 s.

**Punto de extensión del agrupado por frente** (lo construye la línea 3, no esta). `documento_de_la_hoja` recibe un
`Agrupador`: una función que reparte las filas de la vista en `(título, filas)`, en el orden en que se imprimen. Por
omisión, `sin_agrupar` (un solo grupo, sin título ni subtotal: el presupuesto de hoy). Con varios grupos, el servidor suma
el subtotal de cada uno con los totales **exactos** de sus filas y el dibujo pinta el título y «Subtotal de …»; la
numeración sigue de un grupo al otro. Probado con un agrupador ficticio por prefijo del código
(`test_el_agrupador_reparte_los_renglones_y_el_servidor_suma_cada_subtotal`) y con dos frentes dibujados
(`test_los_grupos_llevan_su_titulo_y_su_subtotal`). Para conectarlo: la ruta pasa `agrupar=` cuando el borrador tenga
frentes.

### D-PDF-1: la biblioteca

**Simulación** (`sim_pdf.py`: 60 renglones ficticios con tildes, «m³», una descripción con «<b>&</b>» y «≤», y una muy
larga; el texto se extrae con pdfplumber):

| Opción | Tiempo | Tamaño | Encabezado de la tabla en cada página | Cifras y tildes | «<b>&</b>» literal | Descripción larga |
|---|---|---|---|---|---|---|
| **reportlab** (platypus) | 0,2 a 0,4 s | 7 a 27 KiB | sí (`repeatRows`) | sí | sí (escapado) | se parte en líneas |
| matplotlib (`PdfPages` con `ax.table`) | 7,4 s | 33 KiB | solo si se pagina a mano | sí | no (lo toma como marcas) | se desborda de la celda |
| Imprimir desde el navegador (HTML) | — | — | depende del CSS de impresión | — | — | — |
| fpdf2, WeasyPrint | no instaladas | — | — | — | — | — |

**Se eligió reportlab**: ya está en el instalador (no se instala nada), hace tablas que se parten por página con el
encabezado repetido, parte el texto largo en la celda y no pasa por el navegador, así que el PDF se prueba en el
servidor extrayendo el texto. Es lo que usan los informes del proyecto (`scripts/informe_ti001.py`). matplotlib es para
gráficos: 20 veces más lento y sin texto que fluya. Imprimir desde el navegador dejaría el PDF a merced del motor de
impresión de WebView2 y no se podría probar sin un navegador; además formatearía en la interfaz. WeasyPrint pide GTK en
Windows y fpdf2 no está: no se instalan. **Cómo revertir:** `pdf_en_bytes` es la única función que conoce reportlab; otra
biblioteca la reemplaza con el mismo `DocumentoPdf`.

### D-PDF-2: la letra

| Opción | «≤» | tildes y «m³» | Tamaño | Notas |
|---|---|---|---|---|
| Helvetica (de la norma PDF) | no se dibuja | sí | 7 KiB | WinAnsi: ni «≤» ni «→» |
| **Vera** (la que trae reportlab, incrustada) | sí | sí | 27 KiB | licencia Bitstream Vera, libre; un carácter que no tiene sale como cuadro, sin romper |

**Se eligió Vera** (normal y negrita): las descripciones de los APU traen «≤», «≥» o «°» de vez en cuando y una letra que
no los dibuja los borra en silencio. No se agrega ningún archivo al repositorio: los `.ttf` vienen con reportlab. Un
control C0 o un sustituto suelto (que rompían el título y el pie: `UnicodeEncodeError` medido) pasan a U+FFFD, como en el
Excel (`_limpio`; mutante visto en rojo). **Cómo revertir:** `_LETRA = "Helvetica"`, `_NEGRITA = "Helvetica-Bold"`.

### D-PDF-3: qué lleva y en qué orden

| Opción | OF-001 | Lo que se entrega |
|---|---|---|
| **Un PDF: presupuesto y después un APU por página; `?partida=` para uno** | 32 páginas, 105 KiB, 1,4 s | lo que entregan S10 y Lulo: el presupuesto y el anexo «Análisis de precios unitarios» |
| Dos archivos (presupuesto, APU) | dos descargas | hay que juntarlos para enviar |
| Solo el presupuesto | 2 páginas | falta lo que la prueba pidió («el presupuesto y los APU») |

**Se eligió un PDF** con todo, y la ruta acepta `?partida=` para el APU de una partida (su botón iría en la pestaña APU,
que es de la línea 2: queda para después). Sale el **borrador vivo**, como el Excel, y el encabezado dice si tiene
cambios sin guardar; también trae el resumen de la auditoría («Auditoría de Sílice: sin hallazgos.» o «2 errores y 1
advertencia.»), para que nadie entregue un presupuesto con un hallazgo grave sin saberlo. **Cómo revertir:** en la ruta,
pasar `apus=()` al documento (o `partida`).

### D-PDF-4: el papel

| Opción | 150 renglones ficticios | Encabezado de la tabla en una línea | Ancho útil |
|---|---|---|---|
| **Carta** (21,59 × 27,94 cm) | 4 páginas | sí | 18,59 cm: caben las 7 columnas (18,5 cm) |
| A4 (21 × 29,7 cm) | 3 páginas | sí | 18,0 cm: la tabla se pasa 0,5 cm del margen |

**Se eligió carta**: es el tamaño de los documentos de oficina en Venezuela y las columnas caben en el margen. A4 pide
columnas más estrechas. **Cómo revertir:** cambiar `letter` por `A4` en `pdf_en_bytes` y recortar `anchos`.

**Commits:** `1da8b358` (rojo: 12 por `NotImplementedError` y 10 de la ruta por 404), `0bb77f6e` (verde), `78346458`
(rojo del front: 5) y el verde del front en `0bb77f6e`. Ajustes de las pruebas del rojo, declarados en el verde: la
descripción ficticia se acortó para leerla en una línea (pdfplumber lee renglón a renglón y una celda partida mezcla
columnas), 150 renglones en vez de 80 para tener tres páginas, y la prueba de caracteres raros se agregó con su mutante.

## 2. Los índices del BCV en USD (RF-214)

**Qué hay antes.** Los índices (UC-17: tasa, INPC, CSV) se guardan como series con su unidad (`indice_bs` para un índice
en bolívares). El reajuste (UC-18, `core/budget/reajuste.py`) calcula `Vpm = Vo·(Km−1)·(1−R)` en la moneda de la versión
del contrato; si es USD y un componente cita una serie `indice_bs`, solo advierte: «proyecto en USD con un índice en
bolívares: cuenta dos veces la devaluación (S1-R11)». No había forma de tener el índice en USD. Control y valuaciones no
usan índices: muestran cada monto en la otra moneda con la tasa del corte, y eso ya está; lo que faltaba es el reajuste.

**Qué hace.** En «Índices del BCV», la sección «Un índice en USD»: se elige un índice mensual en bolívares y la tasa
(venta por omisión, S1-R1; o compra), «Revisar» muestra la serie nueva (`BCV-INPC-GENERAL-USD`, o `…-USD-COMPRA`), cuántos
meses, la cuenta del primer y el último mes («276 ÷ 46,0000 = 6,000000») y los meses que no se pueden con su motivo, sin
escribir; «Guardar la serie en USD» la guarda. Después, la cláusula del reajuste la cita como cualquier serie y la
advertencia S1-R11 desaparece; si se cita la de Bs, la advertencia dice ahora la salida («Para un contrato en USD,
exprese el índice en USD en «Índices del BCV» y cite esa serie en la cláusula.»).

**Cómo.** `aplicacion/indices_usd.py`: `expresar_en_usd` (pura) hace la cuenta; `ver` y `guardar` la llevan a la base.
La serie nueva se guarda con `core.catalog.indices.registrar_importacion` como una importación más: unidad `indice_usd`,
periodicidad mensual, huella SHA-256 de lo que se guarda (la misma huella no escribe dos veces; una revisión del índice o
tasas nuevas dan otra huella y otra importación, como UC-17 2d), fuente «Derivada en Sílice: … ÷ el promedio del mes de
BCV-USD-VENTA…» e informe con las importaciones citadas y la cuenta de cada mes. Así el estudio de reajuste cita la
importación de la serie en USD y se recalcula igual (RNF-14) sin tocar el núcleo. `guardar` exige la huella que `ver`
mostró (409 «Los índices o las tasas cambiaron desde que lo revisó: revíselo de nuevo.»). Rutas al final de
`api/rutas/indices.py`, con el acceso del resto (`ADMINISTRAR_PRECIOS`; confirmar, solo una cuenta). La salida de la
advertencia: `aplicacion/reajuste.avisos_con_remedio`, en `api/rutas/reajuste.py`.

**Prueba de punta a punta** (`tests/unit/test_api_indices_usd.py`): el administrador importa por CSV el índice ficticio
(200 en enero de 2026, 276 en febrero de 2027) y las tasas (40 y 46 todos los días de cada mes), lo expresa en USD y
quien arma calcula el reajuste del contrato ficticio en USD (1.000 unidades a 100 USD, R = 0,10): con la serie en USD,
Km = (276 ÷ 46) ÷ (200 ÷ 40) = 1,2 y **18.000,00 USD** (828.000,00 Bs a 46), sin advertencia; con la de Bs, Km = 1,38,
**34.200,00 USD** y la advertencia con la salida. Las cuentas están a mano en `tests/fixtures/reajuste_usd.py`.

### D-USD-1: cómo llevar a USD un reajuste con índices en Bs

**Simulación** (`sim_usd.py`, ficticia): Vo = 1.000 USD, R = 0,10, un componente; dentro de cada mes la tasa sube
linealmente; el INPC del mes es el promedio de los precios en Bs de sus días. Caso A: precios estables en USD (en Bs suben
lo que se devalúa: el reajuste justo en USD es 0). Caso B: +5 % en USD (justo: 45 USD).

| Opción | Error, caso A | Error, caso B |
|---|---|---|
| D. El índice en Bs tal cual (hoy, con la advertencia) | +430,48 USD | +452,01 USD |
| C. Reajustar en Bs (Vo × tasa del mes base) y convertir con la tasa del cierre | +295,23 USD | +295,85 USD |
| **B. El índice ÷ la tasa (una serie en USD)** | ±0,28 a ±13 USD según la tasa (D-USD-2) | ±0,29 a ±14 USD |
| E. Un índice de EE. UU. (CPI o PPI del BLS) | — | — |

**Se eligió B**: es la única que quita la devaluación de la cuenta (el índice en USD es el de Bs deflactado por la tasa,
y Km queda como el cociente de dos precios en USD). D y C la cuentan una o dos veces. E se descarta: no lo publica el BCV,
la LCP pide los índices del órgano que los genera (arts. 133 y 134 de la LCP, Decreto 1.399, G.O. 6.154 Ext.,
19-11-2014, según la transcripción del [spec S1 §8](../especificaciones/2026-10-11-silice-s1-moneda-reajuste-design.md),
**a cotejar con la Gaceta**) y Sílice no tiene red (RNF-14). La práctica venezolana del reajuste por fórmula polinómica
usa índices del BCV en bolívares para contratos en bolívares; para un contrato en divisas la ley no dice cómo, y lo que
hace aquí es lo mínimo coherente con ella: los mismos índices y la misma tasa del mismo órgano.

### D-USD-2: la tasa de qué fecha

| La tasa de cada mes | Error, caso A | Error, caso B |
|---|---|---|
| Promedio de los días hábiles del mes | +1,57 | +1,65 |
| Promedio de todos los días del mes (ideal; el BCV no publica sábados ni domingos) | 0,00 | 0,00 |
| **Promedio de todos los días del mes, cada uno con su tasa aplicable (S1-R1)** | −0,28 | −0,29 |
| La del último día del mes | +12,45 | +13,07 |
| La del primer día del mes | −13,01 | −13,66 |

**Se eligió el promedio de todos los días con la tasa aplicable de cada uno**: el INPC es un índice de **todo el mes** (el
promedio de los precios del período) y la tasa que lo deflacta debe ser la del mismo período; un sábado vale la tasa del
viernes, que es la que rige ese día. Es la práctica de las cuentas internacionales (el FMI usa el promedio del período para
los flujos y los índices y la tasa de cierre solo para los saldos; la NIC 21, párr. 40, admite el promedio del mes para
las transacciones del mes: **a cotejar** con sus textos) y reutiliza las dos reglas de tasa de Sílice (S1-R1 y S1-R2) sin
una tercera. La tasa de un solo día (primero o último) mete la devaluación de dentro del mes en el índice: 13 USD de error
por cada 1.000. **Cómo revertir:** en `expresar_en_usd`, cambiar el promedio de `aplicables` por la tasa del día que se
quiera.

### D-USD-3: dónde vive la serie en USD

| Opción | El estudio guardado | `core/` | Traza |
|---|---|---|---|
| **Una serie guardada como importación** | cita la importación en USD y recalcula igual (RNF-14) | sin cambios | huella, fuente, informe con las importaciones de origen y la cuenta de cada mes |
| Convertir al vuelo dentro del reajuste | habría que guardar qué tasas usó | cambia `core/budget/reajuste.py` (expediente y tutor) | en el estudio |
| Un CSV armado a mano e importado | cita un CSV | sin cambios | ninguna: la cuenta queda fuera de Sílice |

**Se eligió la serie guardada.** No exige expediente de `core/`. **Cómo revertir:** borrar la serie `…-USD` y citar la
de Bs (la advertencia vuelve).

### D-USD-4: un mes con días sin tasa

| Opción (febrero con tasas solo el 1 y el 15) | Resultado |
|---|---|
| **No se expresa y se dice cuáles días faltan** | «02/2027: del 09/02/2027 al 14/02/2027, del 23/02/2027 al 28/02/2027 no hay tasa del BCV de los 7 días anteriores (S1-R2)» |
| Promediar las tasas que haya | (14 × 40 + 14 × 54) ÷ 28 = 47, con 12 días cubiertos por una tasa de más de una semana |
| Interpolar entre tasas | inventa tasas que el BCV no publicó |

**Se eligió no expresarlo**: es S1-R2 (con más de 7 días sin tasa no se convierte), la misma regla que el resto de
Sílice. El administrador importa las tasas que faltan y vuelve a revisar. **Cómo revertir:** subir
`DIAS_MAXIMOS_SIN_TASA` en la comparación de `expresar_en_usd` (no en el núcleo).

**Commits:** `1345b45c` (rojo: 13 por `NotImplementedError` y 8 de la API por 404), `ee8fc801` (rojo del front: 8) y
`04f38ed6` (verde). Ajuste del rojo, declarado en el verde: el oráculo de «días sin tasa» decía solo del 9 al 14; la tasa
del 15 cubre hasta el 22 y faltan también del 23 al 28 (el código tenía razón; se corrigió el oráculo, escrito a mano).
Mutante visto en rojo: `>` por `>=` en el tope de 7 días.

## 3. Segunda opinión (Gemini por `agy`)

- **Argon** (`gemini-4-argon-medium`, solo la tabla de D-USD-2): «De acuerdo». El promedio calendario con la tasa
  vigente es «la solución técnica más limpia»; el residuo es la covarianza dentro del mes; FMI y NIC 21 piden el promedio
  del período para índices y flujos. Citó además el Convenio Cambiario N.° 1 (vigencia de la tasa del viernes el fin de
  semana) y el art. 141 del Reglamento de la LCP: **no verificados**, no se usan. Alternativa que mencionó para obras
  privadas: reajustar en Bs y convertir a la tasa del pago (la opción C, que la simulación descarta para un contrato con
  base en USD).
- **Hydrogen** (`gemini-4-hydrogen-high`, revisión de solo lectura de los dos módulos, leídos con `git show` en
  `04f38ed6`): **un hallazgo verdadero**, ya corregido (§5); en `indices_usd.py`, las rutas `/en-usd/*` y `exportar_pdf`,
  ninguno. Ningún modelo agotó el tiempo.

## 4. Lo que queda

- El botón «PDF de este APU» en la pestaña APU (la ruta ya acepta `?partida=`): la pestaña es de la línea 2.
- Conectar el agrupado por frente de la línea 3 al PDF: pasar su agrupador a `documento_de_la_hoja` en la ruta.
- Una segunda fila de impuesto (ESTADO §5, punto 5) entraría como otra `LineaDeCierre` de `totales`.
- `core/`: nada. Ningún expediente.

## 5. Revisión de Hydrogen: las cifras del APU en el PDF

**Hallazgo** (`aplicacion/presupuesto_pdf.py`, `_celda`): las celdas del APU ya vienen en es-VE
(`composicion.filas_desde_composicion` usa `texto_de_cifra`) y se leían con `Decimal`: «1.000» (mil) se leía uno y salía
«1,000» y «1,00», y «10,5» no se podía leer y salía sin sus dos decimales. Las pruebas no lo veían porque OF-001 no
tiene ninguna cifra de miles en sus APU. **Comprobado** con la prueba que propuso, en rojo
(`('1,000', '1,00') != ('1.000', '1.000,00')`), y corregido leyendo con `aplicacion.cifras.cifra_escrita`
(`test_las_cifras_del_apu_se_leen_con_coma_decimal_y_punto_de_miles`). Commits: `d1ee7338` (rojo) y `d105f092` (verde).
