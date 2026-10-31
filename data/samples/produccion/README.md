# Muestra de producción: una cantera y una planta ficticias (caso ficticio)

**Caso ficticio.** La cantera, la planta, sus materiales, su producción, sus costos, su receta, los precios de lo
que compran, la vía y las series de precios de esta carpeta son **inventados** para la prueba de punta a punta del
plan vial (`tests/integration/test_vial_extremo_a_extremo.py`, Tarea 22). No vienen de ninguna empresa, cantera,
planta ni obra, ni de ninguna fuente pública; no sirven como referencia de costos ni de diseño.
Lo de la empresa no entra al repositorio: se usa solo en local.

## Archivos

| Archivo | Qué es | Cómo entra en Sílice |
|---|---|---|
| `materiales.csv` | Piedra picada `PC-19` y arena `AR-01` de la cantera; mezcla `MZ-C` de la planta (t) | `POST /v1/produccion/materiales` |
| `movimientos.csv` | Lo que la cantera produjo cada mes (entradas en t) | `POST /v1/produccion/movimientos` |
| `receta.csv` | La receta de `MZ-C`, vigente desde el 01/09/2026 | `POST /v1/produccion/recetas` |
| `producciones.csv` | La mezcla producida cada mes (consume la receta) | `POST /v1/produccion/producciones` |
| `costos.csv` | Costos de octubre y noviembre de 2026 por centro (cantera o planta), en USD y en Bs | `POST /v1/produccion/costos` |
| `lista_comprados.csv` | Lo que la planta compra: cemento asfáltico `CA-30` y gasoil `GO`, en USD | la lista de la carpeta (vigente desde el 01/09/2026) |
| `series.csv` | Tasa BCV (`usd_venta`), PPI del asfalto y gasoil, de noviembre de 2024 a noviembre de 2026 | «Índices», CSV canónico |
| `apu.csv` | Los APU de la movilización y de las 12 partidas viales que usa la vía, como se teclean en «Componer» (`;` y coma decimal) | `POST /v1/composicion/guardar` |
| `via.csv` | Los tramos de la vía (formato de `data/samples/vial/README.md`, con `asfalto_pct`) | `POST /v1/vial/tramos/importar` |

Cifras: en los CSV con `,` el punto es el decimal (lo que pide la API); en `apu.csv` y `via.csv`, con `;`, la coma es
el decimal y el punto separa los miles (lo que escribe una persona en la pantalla).

## Memoria de cálculo (a mano, escrita antes de correr la prueba)

### Costo por tonelada (reparto D-V-1: la cantera por tonelada producida; la planta a la mezcla)

Receta de `MZ-C` por tonelada: 0,55 t de `PC-19` y 0,40 t de `AR-01` propios; 0,05 t de `CA-30` a 600 USD/t
(30 USD) y 8 l de `GO` a 0,50 USD/l (4 USD), comprados. La fórmula de trabajo del asfalto es 0,05 × 100 = **5 %**.

| | Octubre de 2026 | Noviembre de 2026 |
|---|---|---|
| Cantera | 2.000 USD + 36.500 Bs ÷ 36,50 = 3.000 USD | 2.500 USD + 49.275 Bs ÷ 36,50 = 3.850 USD |
| Producido en la cantera | 300 + 200 = 500 t | 330 + 220 = 550 t |
| **Agregado** (`PC-19` y `AR-01`) | 3.000 ÷ 500 = **6 USD/t** | 3.850 ÷ 550 = **7 USD/t** |
| Planta | 4.000 USD ÷ 400 t = 10 USD/t | 5.500 USD ÷ 500 t = 11 USD/t |
| **Mezcla** `MZ-C` | 10 + 0,95 × 6 + 30 + 4 = **49,70 USD/t** | 11 + 0,95 × 7 + 30 + 4 = **51,65 USD/t** |

La nómina en Bs se convierte con la tasa del BCV del mismo día (36,50 Bs/USD el 06/10 y el 04/11). Sin esa tasa, el
cálculo se niega y nombra el costo (foco de revisión 1). Existencias: la mezcla de octubre consume 220 t de piedra y
160 t de arena; la de noviembre, 275 y 200: nunca falta material.

### Tramos (`via.csv`)

| Tramo | Capa o línea | Cuenta | Cantidad |
|---|---|---|---|
| T1 (0 a 1,0 km; 7,00 m; planta a 20 km), área 7.000 m² | riego de adherencia 0,30 l/m² | área; 7.000 × 0,30 | 7.000 m²; 2.100 l |
| | carpeta e = 0,05, d = 2,40, asfalto 6,5 % | área; 7.000 × 0,05 × 2,40; × 20 | 7.000 m²; **840 t**; 16.800 t·km |
| | línea continua, 2 líneas | 1.000 × 2; × 0,0365 | 2.000 m; **73 l** |
| T2 (1,0 a 1,5 km; 7,00 m; planta a 20 km), área 3.500 m² | base granular e = 0,20 | 3.500 × 0,20 | 700 m³ |
| | imprimación 1,00 l/m² | área; 3.500 × 1,00 | 3.500 m²; 3.500 l |
| | carpeta e = 0,05, d = 2,40 | área; 3.500 × 0,05 × 2,40; × 20 | 3.500 m²; 420 t; **8.400 t·km** |
| T3 (1,6 a 1,65 km; 3,00 m; planta a 20 km), área 150 m² | bacheo e = 0,10, d = 2,40 | 150 × 0,10; × 2,40; × 20 | 15 m³; 36 t; 720 t·km |

16 cantidades. A propósito, la vía trae tres avisos de diseño que la auditoría debe ver: el asfalto de T1 (6,5 %)
está a 1,5 puntos de la fórmula (5 %) → **VR2**; el riego de T1 deja 0,30 × 1,0 kg/l × 1.000 × 0,60 = 180 g/m² de
ligante residual, bajo el mínimo de 200 → **VR3**; entre T2 (termina en 1,5) y T3 (empieza en 1,6) hay un hueco de
0,1 km → **VR6**. La prueba además escribe a mano 800 t en la mezcla de T1 (**VR1**), 8.000 t·km en el transporte de
T2 (**VR4**) y 40 l de pintura en T1, 40 ÷ 2 km = 20 l/km, bajo 29 (**VR5**); luego los corrige y guarda.

### Presupuesto (V-002, en USD)

Solo materiales, así el precio unitario es materiales × (1 + 0,15) × (1 + 0,10) = materiales × 1,265.

| Partida | Cantidad | Material por unidad | Costo directo |
|---|---|---|---|
| MOV-01 movilización | 1 u | 2.000 | 2.000,00 |
| C-000.000.002 base granular | 700 m³ | 2,2 t de piedra a 6 = 13,20 | 9.240,00 |
| C-000.000.004 imprimación | 3.500 m² | 0,40 | 1.400,00 |
| C-000.000.005 ligante de imprimación | 3.500 l | 0,80 | 2.800,00 |
| C-000.000.006 riego de adherencia | 7.000 m² | 0,40 | 2.800,00 |
| C-000.000.007 ligante del riego | 2.100 l | 0,80 | 1.680,00 |
| C-000.000.008 carpeta | 10.500 m² | 1,50 | 15.750,00 |
| C-000.000.009 mezcla de la carpeta | 1.260 t | 51,65 | 65.079,00 |
| C-000.000.010 bacheo | 15 m³ | 25 | 375,00 |
| C-000.000.011 mezcla del bacheo | 36 t | 51,65 | 1.859,40 |
| C-000.000.012 línea continua | 2.000 m | 0,10 | 200,00 |
| C-000.000.014 transporte | 25.920 t·km | 0,25 | 6.480,00 |
| C-000.000.015 pintura | 73 l | 6 | 438,00 |
| **Costo directo** | | | **110.101,40** |

Total = 110.101,40 × 1,265 = **139.278,271**; IVA 16 % = 22.284,52 (sobre 139.278,27); con IVA **161.562,79**.
La base granular usa la piedra al precio de octubre (6 USD/t) y el último cálculo publicado (noviembre, n.º 2) dice 7:
la conciliación lo señala (**CV3**).

### Riesgo, comprobación y mejora

El PPI del asfalto sube **10 % exacto cada mes** (valores enteros `11^i × 10^(24−i)`), el gasoil queda en 0,50 USD/l
y la tasa en 36,50 Bs/USD: todas las trayectorias dan lo mismo y el resultado se hace a mano. Con 6 meses y gasto
uniforme, el factor del asfalto es (1,1 + 1,21 + 1,331 + 1,4641 + 1,61051 + 1,771561) ÷ 6 = 1,4145285. La mezcla se
recalcula con su receta: solo sus 30 USD de asfalto se mueven, así sube 30 × 0,4145285 = 12,435855 USD/t. Con
1.260 + 36 = 1.296 t y × 1,265, el aumento es 1.296 × 12,435855 × 1,265 = **20.387,8381212** USD:
P50 = P80 = 139.278,271 + 20.387,8381212 = **159.666,1091212**; la reserva es ese aumento. 25 meses de serie dan 24
variaciones: la proyección usa las 24; la comprobación hacia atrás tiene 24 − 12 − 6 + 1 = **7 cortes**, todos
dentro (cobertura 100 %).

Mejora de la estimación con un costo final real **inventado** de 160.000 USD: error del presupuesto original
(160.000 − 139.278,27) ÷ 160.000 = 12,95 %; error de la estimación de Sílice (160.000 − 159.666,11) ÷ 160.000 =
0,21 %; mejora 12,74 puntos.
