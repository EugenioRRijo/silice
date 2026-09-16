# `data/telecom/fuentes/` — presupuestos ARENAZA estructurados

Sesión M1.1 del [PLAN_MULTIDOMINIO.md](../../../PLAN_MULTIDOMINIO.md). Esta carpeta guarda la
estructuración renglón a renglón de los dos presupuestos ARENAZA (telecom). Son **ejercicios
académicos ficticios**, como el caso civil de la clínica (`data/linea_base/`): documentos con el
formato de la práctica, no presupuestos de una obra ejecutada ni precios reales
([CLAUDE.md §1](../../../CLAUDE.md)).

> **Errata (2026‑09‑15).** Las sesiones M1.1–M4.2 los trataron como «presupuestos reales» y
> «segunda línea base real». Esa afirmación queda corregida aquí y en la fuente única; las
> bitácoras de esas sesiones conservan la redacción de su fecha.

A diferencia de la carpeta `data/<dominio>/fuentes/` que describe
[`docs/protocolo_precios.md`](../../../docs/protocolo_precios.md) §1.3 (evidencia de campo de
cotizaciones sueltas: facturas, capturas, cotizaciones escaneadas), lo que se archiva aquí es la
transcripción completa de un presupuesto ya existente en el repositorio como evidencia primaria
(`data/samples/telecom/`), no una cotización nueva levantada en campo.

## Archivos

| Archivo | Contenido | Generado por |
|---|---|---|
| `presupuesto_1_arenaza.csv` | Los 14 renglones de la tabla "Presupuesto" de `Presupuesto_1_ARENAZA.pdf` (presupuesto 001) | `scripts/extraer_arenaza.py` |
| `presupuesto_2_arenaza.csv` | Los 26 renglones de la tabla "Presupuesto" de `Presupuesto_2_ARENAZA.pdf` (presupuesto 002) | `scripts/extraer_arenaza.py` |
| `lista_arenaza.csv` | Lista 1 de UC‑02 (Sesión M1.3): los 27 precios del ejercicio ARENAZA, vigencia declarada 18/05/2026 | `scripts/derivar_listas_telecom.py` |
| `lista_maprex_2026-07.csv` | Lista 2 de UC‑02 (Sesión M1.3): la referencia MaPreX de julio 2026 de los 5 insumos con equivalencia defendible, vigencia 09/07/2026 | `scripts/derivar_listas_telecom.py` |

**Cabecera exacta:** `renglon,descripcion,unidad,cantidad,precio_unitario,total,origen`, con
`origen = <pdf>:<pagina>:<renglon>` (página 1‑indexada: 1 = "Computos métricos", 2 =
"Presupuesto"; ambos PDF traen esas dos tablas por presupuesto).

**Vigencia:** ambos presupuestos están fechados **18/05/2026** en el propio PDF (presupuesto
001 y 002, "Computos métricos" 001 y 002). Es la fecha declarada de la fuente, no la fecha en
que se estructuró (2026‑09‑02).

**Totales verificados:** la suma de la columna `total` de `presupuesto_1_arenaza.csv` es
exactamente **1 109,29 USD**; la de `presupuesto_2_arenaza.csv`, exactamente **5 410,73 USD**.
Ambos coinciden con el renglón "TOTAL PRESUPUESTO" impreso en cada PDF. Ninguna fila fue omitida
ni ajustada para forzar el cierre: las 14 y 26 filas transcritas ya suman el total exacto (ver
`scripts/extraer_arenaza.py`, que además verifica programáticamente que cada total de renglón y
el total impreso aparecen en el texto extraído del PDF con PyMuPDF antes de escribir el CSV).

## Por qué se usa la tabla "Presupuesto" y no "Computos métricos"

Cada PDF trae dos tablas: "Computos métricos" (página 1: ítem, unidad, cantidad, sin precio) y
"Presupuesto" (página 2: ítem, unidad, cantidad, precio unitario, total). La cabecera exigida
por esta sesión (`...,precio_unitario,total,...`) solo la puede llenar la tabla "Presupuesto";
"Computos métricos" se usa exclusivamente para (a) completar una descripción que la tabla
"Presupuesto" trunca por ancho fijo de columna (por ejemplo "Switch Escritorio Gigabit De 10
Puertos" sin su sufijo "Con Poe De") y (b) registrar la discrepancia del tubo corrugado (ver
abajo).

`precio_unitario` viene vacío en el PDF cuando `cantidad = 1` (el precio unitario es idéntico al
total y el autor no lo repite): en ese caso el CSV completa `precio_unitario` con el mismo
importe de `total` (dividir entre 1 no cambia el valor; no es un precio inventado, es el mismo
dato ya impreso en la otra columna).

## La inconsistencia registrada: 80 m vs 90 m del tubo corrugado (presupuesto 2, ítem 5)

El renglón "Tubo Corrugado Flexible 1 Pulgada" del **presupuesto 2** trae:

- **80 m** en la tabla "Computos métricos" (página 1, ítem 5, unidad "Metros").
- **90 m** en la tabla "Presupuesto" (página 2, ítem 5: "Tubo Corrugado Flexible 1 Pulgada 30
  MTS", precio unitario 99,75, total 299,25).

Es la misma discrepancia dentro del **mismo PDF**, no un desacuerdo entre dos fuentes distintas.
Esta sesión la **registra tal cual, sin corregirla**: es la segunda inconsistencia de fuente
primaria que documenta la tesis (la primera son las siete de la línea base civil,
`docs/linea_base.md`). `presupuesto_2_arenaza.csv` usa 90 (el valor de la tabla "Presupuesto",
la única con precio y total); el fixture `tests/fixtures/presupuestos_arenaza.py` expone ambos
valores en `TUBO_CORRUGADO` (`cantidad_computos = 80`, `cantidad_presupuesto = 90`) para que la
Sesión M1.3 (auditoría telecom) los compare con una regla de verificación.

**Nota:** el **presupuesto 1** no tiene esta inconsistencia — su propio tubo corrugado trae 90 m
en ambas tablas (ítem 3 de "Computos métricos" e ítem 3 de "Presupuesto"). Solo el presupuesto 2
la presenta.

En ambos presupuestos, el precio unitario del tubo corrugado (99,75 USD) está cotizado **por
tubo de 30 m**, no por metro: el propio PDF anota el cálculo como "3\*99,75" (3 tubos × 30 m = 90
m = 299,25 USD). Por eso `cantidad × precio_unitario` no reproduce `total` con una
multiplicación literal en ese renglón (90 × 99,75 ≠ 299,25): es una unidad de precio compuesta,
no un error de transcripción de esta sesión, y se conserva tal cual en el CSV y el fixture.

## Reconciliación de la suma: sin renglones omitidos ni ajustados

Antes de estructurar el CSV se verificó que la suma de los renglones de la tabla "Presupuesto"
de cada PDF, tal como se imprimen (sin recalcular ningún `total`), cierra exactamente con el
"TOTAL PRESUPUESTO" del PDF:

- Presupuesto 1: 82,68 + 157,99 + 299,25 + 5,00 + 10,00 + 90,00 + 211,21 + 9,99 + 10,00 + 25,25
  + 7,92 + 90,00 + 10,00 + 100,00 (renglón "Micelaneos") = **1 109,29** ✓
- Presupuesto 2: suma de los 26 renglones de la tabla "Presupuesto" = **5 410,73** ✓

No hizo falta omitir ni ajustar ningún renglón: la cifra cuadra con las 14 y 26 filas completas.
Sí se encontraron, al verificar dígito a dígito, dos discrepancias **internas** de renglón (no
relacionadas con el cierre del total, que sí cuadra) en el presupuesto 2:

| Renglón | Descripción | Cantidad × precio unitario | Total impreso | Diferencia |
|---|---|---|---|---|
| 14 | Camara Bullet Ip 4mp Intemperie | 5 × 289,00 = 1 445,00 | 1 446,65 | 1,65 |
| 18 | Conector Jack Coupler Ubiquiti Rj45 | 7 × 42,99 = 300,93 | 303,93 | 3,00 |

Ninguna de las dos se corrige: se transcriben los tres valores (`cantidad`, `precio_unitario`,
`total`) tal como los imprime el PDF, y es `total` el que entra en la suma verificada (no una
recomputación de `cantidad × precio_unitario`). No son la inconsistencia que esta sesión debe
registrar (esa es el 80/90 del tubo corrugado), pero tampoco se ocultan: quedan anotadas aquí y
en el docstring de `scripts/extraer_arenaza.py` y de
`tests/fixtures/presupuestos_arenaza.py`, con el mismo criterio de trazabilidad total de
CLAUDE.md §2 que ya aplican las siete inconsistencias de la línea base civil.

## Otras diferencias entre "Computos métricos" y "Presupuesto" (presupuesto 2)

Ya señaladas, en general, por `docs/bitacora/2026-08-29-I5-telecom.md` y
`docs/bitacora/2026-09-02-M0.1-protocolo.md`.

Además del tubo corrugado, el presupuesto 2 tiene otras dos filas cuya cantidad no coincide
entre ambas tablas del mismo PDF ("Protector De Voltaje Exceline": 3 en Computos métricos vs 4
en Presupuesto; "Cajetin Superficial 4x2...": 10 en Computos métricos vs 5 en Presupuesto), y
dos ítems que solo aparecen en Computos métricos ("Face Plate Blanco 4x2 2 Puertos", "Keystone
Jack Coupler Inserto Cat6") sin renglón equivalente en la tabla "Presupuesto". No se investigan
ni corrigen en esta sesión (fuera de su alcance, que es registrar el 80/90 del tubo corrugado);
quedan anotadas para quien trabaje la Sesión M1.3 (auditoría telecom) o revise la fuente
primaria con más detalle.

## Regenerar los CSV

```
uv run --with pymupdf python scripts/extraer_arenaza.py
```

El script relee los dos PDF, vuelve a verificar cada total contra el texto extraído y sobre-
escribe ambos CSV. Si algún total no aparece en el texto de la página correspondiente (el PDF
cambió, o hay un error en la transcripción curada del script), se detiene con un error explícito
en vez de escribir un CSV no verificado.

## Listas de precios canónicas para UC‑02 (Sesión M1.3)

La Sesión M1.3 (auditoría telecom y UC‑02 con las dos listas del dominio, compuerta GM1) añade a esta carpeta las dos
listas de precios del dominio en el formato canónico de UC‑02 (`tipo,insumo,unidad,precio`,
`core.catalog.precios.COLUMNAS_ARCHIVO`). Las genera `scripts/derivar_listas_telecom.py` y
**ninguna de las dos transcribe un precio**: la lista 1 sale de las composiciones de
`scripts/seed_telecom.py` (es decir, del fixture ARENAZA) y la lista 2 de
`data/precios/maprex_2026-07/referencia_telecom.csv` (Sesión M0.2).
`tests/unit/test_listas_telecom.py` comprueba que los CSV en disco son exactamente los derivados.

| Archivo | Lista | Vigencia | Filas | Fuente |
|---|---|---|---|---|
| `lista_arenaza.csv` | 1 — precios ARENAZA | **18/05/2026** (fecha impresa en los dos PDF) | 27 | Composiciones `TC-*` armadas desde el fixture |
| `lista_maprex_2026-07.csv` | 2 — referencia MaPreX jul‑2026 | **09/07/2026** (`fecha_vigencia` de `materiales.pdf` en `referencia_telecom.csv`) | 5 | `referencia_telecom.csv`, convertido desde Bs con la tasa 633,3644 Bs/USD (01/07/2026) |

Cargadas en ese orden por UC‑02 (`crear_lista_desde_archivo` y luego `registrar_cambios`)
producen el **primer histórico de `CambioPrecio` fuera del dominio civil**: cinco cambios
fechados el 09/07/2026 (`tests/integration/test_auditoria_arenaza.py`). Es un histórico entre los
precios de un ejercicio académico y una referencia publicada, no entre dos listas de mercado.

### Lista 1: qué entra y qué queda fuera

Entra todo insumo del catálogo telecom al que la fuente le da **un único precio unitario no
contradicho**: 27 de los 34 insumos que persiste `scripts/seed_telecom.py`, incluido el tubo
corrugado a 99,75 USD por tubo de 30 m bajo las dos descripciones con las que lo imprimen los
PDF. El script decide las exclusiones a partir de los datos (marca de ajuste, unidad, línea de
ajuste presente, más de un precio por clave), no de una lista de nombres:

| Insumo excluido | Motivo |
|---|---|
| Las dos líneas «Ajuste total impreso: …» (P2 renglones 14 y 18) | Artefactos de reproducción del total impreso, no insumos de mercado (obligación de la Sesión M1.2) |
| Micelaneos (P1 renglón 14) | Suma global sin cantidad ni precio unitario en el PDF |
| Camara Bullet Ip 4mp Intemperie (P2 renglón 14) y Conector Jack Coupler Ubiquiti Rj45 (P2 renglón 18) | El total impreso contradice cantidad × precio unitario en la fuente (ver «Reconciliación de la suma»): el PDF les da dos precios unitarios incompatibles y una lista canónica no elige uno en silencio |
| Organizador De Cables Individuales 20cm 100 Und (P1 renglón 6, P2 renglón 9) | Dos precios en la fuente para la misma descripción y unidad (18,00 y 19,00). UC‑02 aplica una fila a todas las variantes de esa descripción (`core.catalog.precios`, «Homónimos»): cualquiera de los dos sobrescribiría al otro y fabricaría un cambio de precio dentro de la misma fuente |

### Lista 2: correspondencia ARENAZA ↔ MaPreX

Solo entran las equivalencias defendibles, con un criterio de dos condiciones (una sola tabla:
`CORRESPONDENCIA` en `scripts/derivar_listas_telecom.py`): (a) la nota de la Sesión M0.2 declara
la fila MaPreX equivalente de ese insumo ARENAZA **sin salvedad de atributo** (no «cubre», no
«referencia de categoría», no «MaPreX no distingue…»); (b) la unidad de venta es la misma, o el
factor de conversión lo imprime la propia fuente ARENAZA.

| Insumo ARENAZA (lista 1) | Ref MaPreX | Descripción MaPreX | Factor | ARENAZA (USD) | MaPreX (USD) | Variación |
|---|---|---|---|---|---|---|
| Anillo E.m.t. 2 | `ELE033` | ANILLO EMT D=2" | 1 | 3,96 | 9,5364 | +140,8 % |
| Toma Doble Con Tierra 270 20a Con Placa Blanca | `ELA190` | TOMACORRIENTE DOBLE 1 FASE 20/30 A | 1 | 5,05 | 6,7947 | +34,5 % |
| Cajetin Plástico 4x2 Pvc Con Grapa Metálica. | `ELE654` | CAJETIN RECTANGULAR PVC 2" X 4" X 1/2" ELECT | 1 | 2,00 | 1,9073 | −4,6 % |
| Tubo Corrugado Flexible 1 Pulgada (tubo de 30 m) — P1 | `ELE906` | TUBO PVC ELECTRICIDAD CORRUGADO FLEXIBLE D= 1" (por metro) | 30 | 99,75 | 78,6751 | −21,1 % |
| Tubo Corrugado Flexible 1 Pulgada 30 MTS (tubo de 30 m) — P2 | `ELE906` | ídem | 30 | 99,75 | 78,6751 | −21,1 % |

El tubo corrugado es la **única conversión de unidad admitida**: ARENAZA lo cotiza por tubo de
30 m (el PDF imprime «30 MTS» y la aritmética «3\*99,75») y MaPreX por metro; el factor 30 lo
declara la fuente, no esta sesión. Es, además, el insumo del hallazgo 80/90 y el que la Sesión
M1.2 dejó explícitamente para este contraste. El precio se convierte desde bolívares con la tasa
y el redondeo de M0.2 (1 661,00 Bs/m × 30 = 49 830,00 Bs → 78,6751 USD); multiplicar el
`precio_usd` ya redondeado de la referencia (2,6225 × 30 = 78,6750) daría una diezmilésima
menos por el redondeo previo. El catálogo guarda el tubo bajo dos descripciones porque los dos
PDF lo imprimen distinto; ambas reciben el mismo precio MaPreX, y por eso el histórico registra
cinco cambios para cuatro correspondencias.

Fuera de la lista 2, y por qué (todas las demás filas de `referencia_telecom.csv` y todos los
demás insumos de la lista 1):

| Insumo ARENAZA | Fila MaPreX candidata | Por qué no entra |
|---|---|---|
| BOBINA CABLE UTP CAT 6 (300 M), Bobina Cable Utp Cat6 305 m Int, BOBINA CABLE UTP CAT 6 (300 M) Ext | `ELA006` (por metro) | M0.2 la anota como «cubre» (misma familia, distinta presentación); MaPreX no distingue interior/exterior. Convertible solo bajo el supuesto de que el precio por metro escala linealmente a la bobina |
| Conectores Rj45 Cat6 Utp Bolsa (100 unidades) | `ELC069` (por pieza) | M0.2 anota la salvedad «precio por pieza, no por bolsa de 100»; el PDF no imprime la aritmética del empaque como sí lo hace con el tubo. Convertible (×100) si el autor acepta el supuesto de empaque |
| Bosla Tirrap (100 unidades), Amarre Tiewrap Negro Plástico 20 Cm, Base Para Tirrap Tirraje 10 u | `QUI059` | «Cubre» genéricamente; ARENAZA no declara la medida del tirrap |
| Teipe Eléctrico Negro Cobra, Teipe Aislante Para Cableado Eléctrico | `ELF215` | «Cubre»; MaPreX no lista la marca ni la presentación |
| Guaya Guia Pasa Cable De Acero | `ACE894` (por metro) | Equivalente de categoría, pero ARENAZA no declara la longitud de la guaya: no hay factor de conversión |
| Cajetin Superficial 4x2 Hembra | `ELC066` | Salvedad de M0.2: «MaPreX no distingue '4x2' en cajetines de red» |
| Canaleta Plastica 40x40x2mts | `ELA553` | Sección distinta (1" / 25 mm) |
| Rack Fijo Onlink 12u | `ELC051` | Referencia de categoría (rack 4U de pared) |
| Switch Escritorio Gigabit De 10 Puertos Con Poe De, Switch Tp-link Tl-sg108 8 Puertos, Switch Tp-link 16 Puertos | `ELA633` | Referencia de categoría (único switch de marca en MaPreX: 48P 10/100 para rack) |
| Conector Jack Coupler Ubiquiti Rj45 | `ELC065` | Su insumo ARENAZA no está en la lista 1 (total impreso contradicho): no hay precio anterior que contrastar |
| Organizador De Cables Individuales 20cm 100 Und | `ELF449` | Su insumo ARENAZA no está en la lista 1 (dos precios en la fuente); además M0.2 anota «forma distinta» |
| Conector Rj-45 Ftp Cat6 Blindado 50 U | — | M0.2 no le asignó fila: el conector FTP blindado no es el `ELC069` UTP |
| Punto De Acceso Rap Ruijie, Mini Ups Spidertec 17600mah, Nvr Hikvision 7600, Cámara Domo Ip Hikvision 4mp, Camara Bullet Ip 4mp Intemperie, Protector De Voltaje Exceline | — | Sin equivalente en MaPreX (M0.2: «omitidos por marca/modelo, no por categoría») |
| — | `ELC057` patch panel, `EFO001` fibra óptica y fusionadora | Referencias de categoría de M0.2 sin insumo ARENAZA correspondiente |

### Regenerar y verificar las listas

```
uv run python scripts/derivar_listas_telecom.py              # reescribe los dos CSV e imprime el contraste
uv run python scripts/derivar_listas_telecom.py --verificar  # compara con los CSV en disco (sale con 1 si difieren)
```

No requiere PyMuPDF: no relee los PDF, deriva de datos ya estructurados en el repositorio.
