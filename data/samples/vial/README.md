# Muestra vial: `via_ficticia.csv` (caso ficticio)

**Caso ficticio.** La vía, sus tramos, anchos, espesores, densidades, dosis y distancias son inventados para
probar el adaptador vial (`adapters/vial/`, plan vial, Tarea 7). No vienen de ninguna obra ni de ninguna
empresa; no sirven como referencia de diseño.

## Formato

Separador `;` y coma decimal (lo que exporta una hoja de cálculo en es-VE). El lector también acepta `,` como
separador (si la cabecera no trae `;`). Codificación UTF-8 (con o sin BOM).

Cifras (`adapters/vial/tabular.py`, `numero`), solo con cifras 0-9 y un «-» opcional:

- **Con coma**: la coma es el decimal y los puntos separan los miles de tres en tres: `7,30`, `1234,5`,
  `1.234,5`, `12.345.678,9` (la misma regla que `aplicacion/cifras.py`).
- **Sin coma**: el punto es el decimal: `7.30`, `0.123`, `850`.
- **Ambiguo**: un número sin coma con forma de miles (`1.234`) se rechaza con «escriba 1234 o 1,234»; con dos o
  más grupos (`1.234.567`) se pide escribirlo sin puntos (`1234567`) o con coma (`1.234.567,0`).
- Se rechazan, con la fila y la columna: `1,234.5`, `7.3,5`, `1.2345,6`, `1 234`, `1_000`, `1e3`, `+5`, `,5`, `5,`,
  `.5`, `5.` y las cifras que no son 0-9 ASCII.

Columnas, todas obligatorias en la cabecera:

`tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;espesor_m;densidad_t_m3;dosis_l_m2;lineas`

- Una fila por **capa** o por **línea de demarcación** de un tramo (`elemento` = `capa` o `demarcacion`).
- Las columnas del tramo (`progresiva_ini_km`, `progresiva_fin_km`, `ancho_m`, `distancia_planta_km`) se llenan
  en la primera fila del tramo; en las siguientes pueden ir vacías, y si se llenan deben coincidir.
- `distancia_planta_km` es opcional: sin ella no se calcula el transporte de la mezcla.
- Capa: `tipo` ∈ {`fresado`, `base_granular`, `subbase_granular`, `imprimacion`, `riego_adherencia`, `carpeta`,
  `bacheo`}. Espesor para fresado, base, sub-base, carpeta y bacheo; densidad compactada para la carpeta
  (obligatoria) y el bacheo (opcional); dosis para imprimación y riego de adherencia. Un dato que el tipo no usa
  se rechaza: nada se ignora en silencio.
- Demarcación: `tipo` ∈ {`continua`, `discontinua`} y `lineas` (entero ≥ 1).
- Columna **opcional** `asfalto_pct` (Tarea 16b): el porcentaje de asfalto que el proyecto pide a la mezcla de
  la carpeta o del bacheo (mayor que 0 y menor que 100; «6,5» es 6,5 %). Va en la partida de la mezcla y la
  regla VR2 lo compara con la fórmula de trabajo de la receta vigente de la planta. Un archivo sin esa columna
  se lee igual; en otra capa o en una demarcación se rechaza.
- Columnas **opcionales** de F5 vial (diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §6;
  un archivo sin ellas se lee igual y deriva lo mismo que antes):
  - `esponjamiento` (solo fresado): volumen suelto ÷ volumen en sitio, mayor o igual a 1 («1,25»). Sin valor por
    defecto: sin él no se deriva el transporte del fresado (m³ = volumen fresado × esponjamiento).
  - `limpieza` (solo imprimación y riego de adherencia): `sí` o `no`. Con `sí` se deriva la limpieza de la superficie
    (m², el área regada).
  - `medicion`: la otra unidad de la partida principal: `m2` en el fresado (fresado medido en área) y `t` en la
    carpeta (colocación medida en masa). Vacía, la de siempre (m³ y m²).
  - `area_m2` (solo demarcación `superficie`, obligatoria allí): el área de cada elemento (paso peatonal, línea de
    pare); `lineas` es el número de elementos iguales y la cantidad, área × número, en m².
  - `captafaros` (líneas continua o discontinua, o demarcación `captafaros`): el número de ojos de gato (entero
    ≥ 1). En una línea, la línea sigue dando sus metros y su pintura.
  - Demarcación de tipo `captafaros` (prueba de punta a punta del 2026-11-13): ojos de gato solos, sobre una línea
    que esta obra no pinta. `captafaros` obligatoria; `lineas` vacía (o 1). Da solo las unidades, sin línea ni
    pintura.
  - `suministro` (solo imprimación y riego de adherencia): `sí` o `no`. Con `sí`, el APU del riego ya trae el
    ligante («riego con suministro»): no se deriva la partida del ligante y la dosis pasa a ser opcional (si se
    escribe, VR3 sigue midiendo el residual). Vacía o `no`, la capa de siempre: dosis obligatoria y ligante
    derivado.
  - `transporte` (del tramo: se llena en su primera fila, como `distancia_planta_km`; si se repite en otra fila,
    debe coincidir): cómo mide la obra el transporte de la mezcla. Vacía (o `t·km`), en t·km, la de siempre;
    `banda`, en toneladas, con la distancia como banda en la descripción de la partida («más de 8 km y hasta
    10 km»). Con `banda` la partida en t se deriva aunque el tramo no declare la distancia, y VR4 compara las
    toneladas y, si hay distancia, si cae dentro de la banda (fuera de ella, ADVERTENCIA). Otro valor se
    rechaza con la fila.
  Las partidas sin geometría (movilización de equipos, en viajes, y señalización y control de tránsito, en días)
  están en el catálogo vial pero se ponen a mano en el presupuesto.
- Los errores nombran el archivo y la **fila** tal como la ve una hoja de cálculo (la cabecera es la fila 1).

## Memoria de cálculo (a mano, escrita antes del código)

Longitud = (progresiva final − inicial) × 1000. Área = longitud × ancho.

**T1** (0 a 1,2 km: 1200 m; ancho 7,30 m; planta a 15 km). Área = 1200 × 7,30 = **8760 m²**.

| Capa / línea | Cuenta | Cantidad |
|---|---|---|
| 1 fresado, e = 0,05 | 8760 × 0,05 | **438 m³** |
| 2 riego de adherencia, 0,40 l/m² | área | **8760 m²** |
| | 8760 × 0,40 | **3504 l** |
| 3 carpeta, e = 0,05, d = 2,35 | área | **8760 m²** |
| | 8760 × 0,05 = 438 m³; 438 × 2,35 | **1029,3 t** |
| | 1029,3 × 15 | **15439,5 t·km** |
| demarcación 1, continua, 2 líneas | 1200 × 2 | **2400 m** |
| | pintura: 2400 × 0,0365 | **87,6 l** |
| demarcación 2, discontinua, 1 línea | 1200 × 1 × 0,375 | **450 m** |
| | pintura: 450 × 0,0365 | **16,425 l** |

**T2** (1,2 a 2,0 km: 800 m; ancho 6,50 m; planta a 18 km). Área = 800 × 6,50 = **5200 m²**.

| Capa | Cuenta | Cantidad |
|---|---|---|
| 1 sub-base granular, e = 0,25 | 5200 × 0,25 | **1300 m³** |
| 2 base granular, e = 0,20 | 5200 × 0,20 | **1040 m³** |
| 3 imprimación, 1,20 l/m² | área | **5200 m²** |
| | 5200 × 1,20 | **6240 l** |
| 4 carpeta, e = 0,04, d = 2,30 | área | **5200 m²** |
| | 5200 × 0,04 = 208 m³; 208 × 2,30 | **478,4 t** |
| | 478,4 × 18 | **8611,2 t·km** |

**T3** (2,0 a 2,05 km: 50 m; ancho 3,00 m; planta a 18 km). Área = 50 × 3 = 150 m².

| Capa | Cuenta | Cantidad |
|---|---|---|
| 1 bacheo, e = 0,10, d = 2,30 | 150 × 0,10 | **15 m³** |
| | 15 × 2,30 | **34,5 t** |
| | 34,5 × 18 | **621 t·km** |

En total, 20 cantidades. La fracción pintada de la línea discontinua (0,375: 3 m pintados de cada 8 m) es un
**supuesto declarado** (`FRACCION_PINTADA_DISCONTINUA`), no una norma. La pintura de cada línea (Tarea 16b) usa
0,0365 l por m de línea de 10 cm: 36,5 l por km, el punto medio del rango de VR5 (`PINTURA_POR_DEFECTO_L_KM`,
V-17, supuesto declarado, a cotejar con la ficha del producto); el modelo no trae el ancho de la línea y se
supone 10 cm (V-14).

## Códigos de partida

Los códigos tienen la forma de la norma de carreteras (`C-xxx.xxx.xxx`, COVENIN 2000-1:1987, Parte I), pero
los números son **provisionales** (`C-000.000.001` en adelante) y están **a cotejar** con el texto de la norma:
no se tomaron de ella (ver `docs/fuentes/2026-10-30-fuentes-plan-vial.md` §3).

## `series_ficticias.csv` (series de precios, datos FICTICIOS)

**Datos ficticios.** Las dos series (`CEMENTO_ASFALTICO_PPI` y `GASOIL_USD`), de octubre de 2023 a septiembre de
2026 (36 meses), son inventadas para probar `aplicacion/riesgo/series.py` (plan vial, Tarea 12) y la proyección del
riesgo. **No son** el PPI de asfalto de FRED/BLS ni el precio del gasoil de ninguna Gaceta, ni vienen de ninguna
empresa; cada fila lo dice en su columna `fuente`. Sirven para la forma, no para el valor.

Formato: el CSV canónico de series (`serie,fecha,valor,provisional,fuente`; punto decimal; fecha `AAAA-MM-DD`,
primer día del mes). El PPI se declara **índice** (proxy internacional, solo se usa su variación mensual); el gasoil
es una serie en **escalones** (precio administrado, «a cotejar en la Gaceta»). Las series reales se importan solo
en local, nunca al repositorio.
