# Arreglos urgentes para la demostración del 1 de noviembre (rama inc/vial-arreglos-demo)

Origen: la pasada de navegador a 1366x768 del 31-10 (capturas en el directorio de trabajo de la sesión, `scratchpad/navegador/capturas/`).
Cada arreglo tiene su prueba, vista en rojo antes del arreglo. Todo en es-VE, solo tokens de Carbon (ningún color nuevo).

| # | Problema | Captura | Arreglo | Commit |
|---|----------|---------|---------|--------|
| 1 | Hoja › Presupuesto: cada fila medía ~10.000 px; el aviso largo del Estado quedaba a una letra por línea | 11_hoja, 11_hoja_completa | `.silice-hoja__estado-texto`: ancho mínimo 14 rem y a lo más 3 líneas (`line-clamp`); el texto completo sigue en el `title` de la fila. Se eligió porque no añade controles y no pierde información | e27c71c1 |
| 2 | «Tramos» no salía en la barra lateral hasta tener tramos; desde el buscador sin obra llevaba a Pendientes sin avisar | 08_buscador_tramos, 08b_obra_resumen, 09_tramos_vacio | «Tramos» es sección de toda obra mientras el módulo vial esté encendido (se retiran `soloVial` y `useObrasViales`). El buscador ya no ofrece la pantalla suelta «Tramos de la vía» sin obra: ofrece «Obra › Tramos» | 0319db18 |
| 3 | Auditoría: Impacto, Observado y Esperado con punto decimal; el código C-000.000.001 se partía | 11b_hoja_auditoria | `presentar: formatoEsVe` en las tres columnas; la partida va en un `span.silice-informe__codigo` con `white-space: nowrap` | 5dd18e85 |
| 4 | «fracción pintada 0.375» con punto | 09c_tramos_llevados | `adapters/vial/derivacion.py` formatea con la biblioteca estándar («0,375»). Ninguna prueba ni oráculo fijaba esa descripción; se añadió la prueba | d8a87f8a |
| 5 | Receta de la planta: «Producto (código)» buscaba en el catálogo de la carpeta y no hallaba las mezclas | 05_receta_escribiendo, 05c_receta_formulario | Los materiales de la arenera viven en la base de la instalación (no en la de la carpeta que lee `/v1/consulta`), así que no se añadió tabla en `aplicacion/consulta.py`: se usa `GET /v1/produccion/materiales`, que la pantalla ya pide, con filtro local (sin tildes, todas las palabras). Producto: `materiales_produccion`; componentes: materiales propios y, debajo, insumos del catálogo | 3d3efdfa, 04901688 |
| 6 | Diálogos «Registrar un costo» y «Registrar una receta nueva» cortados contra el pie sin señal de desplazamiento | 04b_costos_formulario, 05c_receta_formulario | El cuerpo de `MarcoDeDialogo` ya se desplazaba; ahora lleva sombras de desplazamiento (CSS puro, solo si hay más contenido). La fila del componente de la receta va en una línea (código, cantidad, unidad, tipo, Quitar) y «Quitar» queda alineado | d9bd1652 |
| 7 | Control › Valuaciones: «Total con IVA» cortada a la derecha | 21a_valuaciones | Relleno compacto (0,5 rem) en las celdas de las tablas de Control y cifras sin partir; si aun así no cupiera, `.silice-tabla` ya se desplaza dentro de su caja | 91f24249 |
| 8a | Unidades «m2»/«m3» en las tablas de Tramos | 10_tramos_llevados_ok | Se presentan «m²»/«m³» solo en la columna Unidad (`presentar`); el valor del servidor no cambia | 38d2814a |
| 8b | El foco del aviso verde se veía como una caja negra más ancha que el aviso | 09c_tramos_llevados | `AvisoConFoco` lleva `.silice-aviso-foco`: `fit-content` y anillo `--cds-focus` por dentro | 38d2814a |

## Notas

- No se tocó `core/`, `aplicacion/hoja.py`, `aplicacion/composicion.py` ni `asistente/experimento`, ni los archivos de «Llevar al presupuesto» (`aplicacion/hoja_vial.py`, `aplicacion/vial.py`, `api/rutas/vial.py`).
- No se verificó en navegador (no se abrió): las pruebas de CSS leen el fuente, como las demás del repositorio; conviene una mirada a 1366x768 en los ocho puntos antes de la demostración.
- Pendiente fuera de alcance: `#/tramos` escrito a mano sin obra sigue yendo a Pendientes (sin consulta en la dirección, `RutaVieja`); ya no se ofrece desde el buscador.

## Segunda pasada

Origen: la pasada de confirmación a 1366x768 (`scratchpad/navegador/capturas2/`). Pruebas por aserción antes de cada arreglo (salvo donde se indica); solo tokens de Carbon, sin hex nuevos; ni Python ni `core/` tocados.

| # | Problema | Arreglo y por qué | Commit |
|---|----------|-------------------|--------|
| 1 | Control › Valuaciones: 1.403 px en una caja de 1.016; «Total con IVA» cortada, «Período» en 3 líneas | Dos medidas juntas. (a) El período se lee «02/11 a 06/11/2026» (el año una sola vez; el texto completo queda en el `title`) y ninguna celda de la tabla se parte (`white-space: nowrap`): quita las 2 y 3 líneas por fila y deja las nueve columnas en una línea. Se eligió acortar el período y no quitar columnas porque no se pierde ningún dato. (b) Si aun así no cupiera, `.silice-tabla` pide barra de desplazamiento de ancho normal con colores del tema (`scrollbar-width: auto`, `scrollbar-color`): la barra superpuesta del sistema era la que no se notaba. No se hizo sombra de borde: las celdas opacas la taparían (mismo fallo que el diálogo) | 873852f9 |
| 2 | Diálogo «Registrar un costo»: «Fuente» tapado por el pie sin señal | La sombra era fondo del cuerpo y el campo blanco la tapaba. Ahora el cuerpo va dentro de una zona (`.silice-dialogo__zona`) y, mientras queda contenido debajo (medido al pintar, al desplazar y al cambiar de tamaño), una gradiente `::after` de 2 rem al pie, sin ratón, pinta encima (equivale al `hasScrollingContent` de Carbon, que no se usa porque el marco no usa su Modal, RNF-22). Además barra visible con colores del tema. Receta nueva: el «Código» del componente era de tamaño pequeño (32 px) junto a campos de 40 px (de ahí los 10 px) y ahora es `md` (`CampoDeConsulta` acepta `tamano`); Unidad y Tipo tienen mínimo de 11 rem, para que «Elija la unidad» no salga recortado | df17fec5 |
| 3 | Hoja: «C-000.000.001» partido en dos líneas; m2/m3 | La celda de partida lleva `.silice-hoja__codigo` (nowrap). `unidadEscrita` pasó de `TramoConCantidades` a `comun/unidades.ts` y la usan Tramos y la columna Unidad de la Hoja (solo presentación) | b2ba0e63 |
| 4 | Aviso del 409 de Llevar: unas 20 líneas, códigos partidos | `AvisoDeLlevar` (solo front, el texto del servidor no cambia): la primera frase, luego «Qué hacer:» resaltado (negrita y borde de 4 px con `--cds-support-error`), luego las frases en párrafos y las enumeraciones «Encabezado: a; b; c.» (3 o más) como lista; cada código «C-…» va en un trozo nowrap. Un aviso corto, sin «Qué hacer» ni lista, queda como un párrafo con el texto tal cual. No se pidió al servidor que devolviera la estructura (fuera de esta noche) | 32e23557 |
| 5a | Auditoría: Descripción muy estrecha | La celda lleva `.silice-informe__descripcion` con ancho mínimo de 18 rem | 012acb8e |
| 5b | Foco de «Abrir la Hoja de la obra» con recuadro del ancho del aviso | NO se hizo: sin navegador no se pudo ver de dónde sale el recuadro y un arreglo a ciegas podía empeorarlo. `.silice-aviso-foco` ya es `fit-content`; queda para mirar en el navegador | - |

Notas de método: la prueba del código de la Hoja (`estilosCodigo.test.ts`) y la de `AvisoDeLlevar` se escribieron con el módulo o la regla aún por crear (rojo por importación o aserción de la Hoja en `Edicion.test.tsx`, que sí falló por aserción); la medición real a 1366 px sigue siendo cosa del navegador.

## Tercera y cuarta pasada (31-10, noche)

- Confirmados en el navegador a 1366×768: filas de la Hoja, «Tramos» en toda obra, coma decimal en la auditoría,
  «0,375» y m²/m³, autocompletado de la receta, códigos en una línea en la Hoja y el aviso ordenado de Llevar.
- Llevar en DEMO-001: con las partidas compuestas hoy, 409 sin llevar nada; con las 15 partidas compuestas al
  20/09/2026, 20 renglones con precio, 0 PENDIENTE y CUMPLE.
- Valuaciones: el arreglo de la segunda pasada ensanchaba la página (1.507 px). Corregido en 454655f9: los hijos de
  la rejilla de Control se encogen y la tabla se desplaza en su caja. El diálogo de costo usa ahora una gradiente
  gris con raya; la blanca no se veía.
- Pendiente de mirar en un Chrome o Edge normal: el Chromium sin pantalla no dibuja barras de desplazamiento.
