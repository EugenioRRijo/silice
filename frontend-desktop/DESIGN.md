# Design

<!--
THESIS: el libro es la evidencia y la pantalla es una lente forense sobre él. Se rechaza el tablero de tarjetas
con KPI en grande y la hoja escondida detrás de un clic.
OWN-WORLD: IBM Carbon g10 nativo (paquete oficial @carbon/react), IBM Plex Sans y Mono, esquinas rectas,
divisores de 1 px, severidad con ícono, morado solo para atípicos, verde/rojo IBCS solo en cifras de variación.
STORY: el auditor suelta el libro, lo ve como en Excel con las celdas marcadas, toca un hallazgo, cae en su
celda y lee libro contra Sílice.
FIRST VIEWPORT: cabecera de 48 px; franja de indicadores Fiori de 64 px como mínimo (crece con la etiqueta del libro menor); la hoja ocupa el resto a la izquierda;
panel de hallazgos de 320 px a la derecha (tabla Carbon `sm`).
FORM: gramática nativa de Carbon, fijada por el brief (RS-6); sin sorteo de direcciones.
-->

Fuente de verdad del aspecto de `frontend-desktop/`. Los valores exactos viven en `src/estilos/tokens.scss` y se
ajustan aquí cuando la construcción los fije.

## Sistema

- **Carbon oficial:** `@carbon/react` y `@carbon/styles` (Sass). No se recrea Carbon a mano ni se mezcla con otro
  sistema de componentes. Tema **g10** (claro): la escena es una laptop con luz variable, a veces en obra; el tema
  oscuro (g100) queda diferido.
- **Tipografía:** IBM Plex Sans para todo; IBM Plex Mono para referencias de celda (`PRESUPUESTO!F12`) y códigos de
  regla. Cifras con `font-variant-numeric: tabular-nums`, alineadas a la derecha. Escala productiva de Carbon
  (`body-compact-01` 14 px, `label-01` 12 px, `heading-03` 20 px para el valor de un indicador).
  **Tamaño base por presbicia (Eugenio, 2026-10-21):** la raíz mide 116,6667 % de la letra del navegador, así que el cuerpo de
  Carbon (14 px) sale a 16 px y la etiqueta más pequeña (12 px) a 14 px; todo va en rem. El control «Tamaño de letra» de la
  cabecera (Normal 100 %, Grande 125 %, Muy grande 150 %, guardado en el navegador) multiplica ese tamaño por la variable
  `--silice-escala-letra`. Con Grande y Muy grande el menú lateral pasa a ser capa (botón de la cabecera) por debajo de
  1536 y 1920 px, y la cabecera cede el nombre de la persona a los selectores. El texto de los gráficos de Carbon Charts
  también sigue la escala; el lienzo de la hoja de Excel (Univer) dibuja en píxeles y sigue la escala por el acercamiento propio de Univer (zoom efectivo = zoom propio de la hoja × factor de la letra, tope 400 %); la barra de la hoja trae su control de zoom (50 a 300 %). IBM Plex es la
  cara nativa de Carbon, que el brief fija: se aloja en el propio servidor, sin CDN.
- **Forma:** esquinas rectas (radio 0, como Carbon); separación con divisores de 1 px `$border-subtle` y espacio,
  no con tarjetas con sombra. Sin gradientes, sin sombras decorativas, sin vidrio.
- **Densidad:** la hoja replica la altura de fila del libro (24 px típica, `compact`); tablas de hallazgos en
  tamaño `sm` (32 px); controles táctiles de 48 px solo donde la ruta los pide (sesión 4).

## Color: dos semánticas que no se mezclan

| Semántica | Dónde | Tokens |
|---|---|---|
| **Severidad** (halos de la hoja, etiquetas de la lista) | celdas y filas de hallazgos | CRITICO `red-60` #da1e28 · ERROR `orange-50` #eb6200 · ADVERTENCIA `yellow-30` #f1c21b · INFO `blue-60` #0f62fe · atípico (RF-100) `purple-60` #8a3ffc · verificado `green-50` #24a148 |
| **Variación IBCS** | solo cifras Δ y Δ% de indicadores y gráficos | desfavorable `red-60` · favorable `green-50` en el ícono (3:1) y `green-60` en la cifra (4.5:1, AA) · sin variación `gray-70` |

- Cada severidad lleva su ícono de Carbon (`ErrorFilled`, `WarningFilled`, `WarningAltFilled`,
  `InformationFilled`) y su nombre en texto accesible; el amarillo no alcanza 3:1 sobre blanco, así que su
  identificación la da el ícono con glifo oscuro, nunca el borde solo.
- Libro contra Sílice (decisión de Eugenio, V-16): el libro menor que Sílice es favorable (verde, flecha abajo) y el mayor,
  desfavorable (rojo, flecha arriba); la palabra «favorable» o «desfavorable» se ve siempre, el color no va solo.
- **Etiqueta de advertencia pegada** (V-16, Eugenio 2026-10-21): el verde del libro contra Sílice significa «el libro declara menos»,
  y un libro que omite costos también sale menor, así que ese verde no puede leerse como «todo bien». Cuando el indicador es de
  sentido «exactitud» con delta negativo lleva, **dentro de la misma tarjeta y bajo la cifra**, una nota (`role="note"`) con el
  ícono `WarningAltFilled`, texto en la tinta normal sobre `--silice-aviso-fondo` (yellow-10, 16,4:1) y franja de 4 px en
  `--silice-aviso-borde` (yellow-50, 3,02:1 como gráfico). Reglas del patrón: siempre visible (nunca tooltip, nunca tras un clic), sin
  botón de cerrar, ícono y texto juntos (nunca solo color), el texto baja de línea y no se recorta, conserva el color al imprimir
  (`print-color-adjust: exact`) y con colores forzados lleva borde propio. Es la descripción accesible del indicador
  (`aria-describedby`; el nombre sigue siendo el título): la lectora lo dice una vez, con la cifra. Aparece **solo** en ese caso (no con
  libro mayor, igual ni en los sentidos de costo o rendimiento) para no volverse papel tapiz.
  **Dos tamaños:** la etiqueta completa solo en «Total general» (o en el primer indicador menor si ese no lo es) y, en subtotal e IVA,
  un marcador de un renglón con el mismo ícono, los mismos tokens y la palabra «Libro menor». Con datos de la API
  (`partidas_con_omision`, partidas cuyo costo directo queda incompleto, regla L4) la completa dice «N partida(s) con costo directo
  incompleto (n.º …). Puede faltar además alguna partida; revise antes de aceptar»; sin ellos, la frase fija «puede deberse a partidas
  omitidas; revise antes de aceptar». El número cuenta partidas presentes con L4, nunca partidas ausentes (de esas el comparador no
  sabe nada). Ninguna acción se bloquea: es un acuse visible.
- La tarjeta del indicador es una columna de dos filas que bajan de línea (título y meta; cifra y variación): con la letra Muy
  grande la variación ya no desplaza a la cifra a 0 px. La franja de indicadores tiene un alto mínimo de 64 px y **crece** lo que
  pida la etiqueta (una línea más con el marcador, varias con la completa).
- Real = relleno sólido; plan/meta = contorno; pronóstico = achurado (IBCS). El acento de interacción es el azul
  de Carbon (`$interactive`) y solo en acciones, foco y selección.

## Marco

Cabecera de Carbon de 48 px (nombre de la persona, selectores de caso y de proyecto en tamaño `sm`, «Salir») y menú
lateral de 16 rem, fijo desde 1056 px de ancho y plegable con el botón de la cabecera por debajo. Cuatro secciones como
en Streamlit (Trabajo, Revisión, Investigación, Administración); dentro de cada una, primero las páginas migradas y,
bajo el rótulo «En la interfaz clásica», las que aún viven en Streamlit (una línea de 32 px, sin ser enlaces de esta
interfaz). Las que no puede ver la cuenta no aparecen; las que sí puede y no están migradas, sí.

## Movimiento

Ninguno decorativo (Eugenio, 2026-10-18). Solo las transiciones de estado propias de los componentes Carbon
(70-110 ms, `motion(standard, productive)`); los halos aparecen sin animación; nada anima al cargar la página;
`prefers-reduced-motion: reduce` quita incluso esas transiciones.

## Texto

Español llano y técnico. Etiquetas que nombran la cosa («Total del libro», «Total según Sílice», «Hallazgos»),
sin frases de marketing, sin rayas (—) como adorno, sin rótulos en mayúsculas espaciadas sobre cada sección.
Estados vacíos que enseñan qué hacer («Suelte aquí el libro .xlsx de la empresa»), errores con el `detalle` de la
API tal cual.

Los indicadores presentan en centésimas (RS2-12) y el valor exacto de los totales del libro y de Sílice está siempre a
un toque, en el tooltip accesible de cada indicador.

## Prohibido

Tarjetas con sombra para agrupar, íconos decorativos, puntos de color sin significado, gradientes, morado fuera de
los atípicos, verde por ser positivo, cifras redondeadas sin el exacto a la vista, animaciones de entrada.
