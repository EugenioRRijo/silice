# Design

<!--
THESIS: el libro es la evidencia y la pantalla es una lente forense sobre él. Se rechaza el tablero de tarjetas
con KPI en grande y la hoja escondida detrás de un clic.
OWN-WORLD: IBM Carbon g10 nativo (paquete oficial @carbon/react), IBM Plex Sans y Mono, esquinas rectas,
divisores de 1 px, severidad con ícono, morado solo para atípicos, verde/rojo IBCS solo en cifras de variación.
STORY: el auditor suelta el libro, lo ve como en Excel con las celdas marcadas, toca un hallazgo, cae en su
celda y lee libro contra Sílice.
FIRST VIEWPORT: cabecera de 48 px; franja de indicadores Fiori de 64 px; la hoja ocupa el resto a la izquierda;
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
  (`body-compact-01` 14 px, `label-01` 12 px, `heading-03` 20 px para el valor de un indicador). IBM Plex es la
  cara nativa de Carbon, que el brief fija: se aloja en el propio servidor, sin CDN.
- **Forma:** esquinas rectas (radio 0, como Carbon); separación con divisores de 1 px `$border-subtle` y espacio,
  no con tarjetas con sombra. Sin gradientes, sin sombras decorativas, sin vidrio.
- **Densidad:** la hoja replica la altura de fila del libro (24 px típica, `compact`); tablas de hallazgos en
  tamaño `sm` (32 px); controles táctiles de 48 px solo donde la ruta los pide (sesión 4).

## Color: dos semánticas que no se mezclan

| Semántica | Dónde | Tokens |
|---|---|---|
| **Severidad** (halos de la hoja, etiquetas de la lista) | celdas y filas de hallazgos | CRITICO `red-60` #da1e28 · ERROR `orange-50` #eb6200 · ADVERTENCIA `yellow-30` #f1c21b · INFO `blue-60` #0f62fe · atípico (RF-100) `purple-60` #8a3ffc · verificado `green-50` #24a148 |
| **Variación IBCS** | solo cifras Δ y Δ% de indicadores y gráficos | desfavorable `red-60` · favorable `green-50` · sin variación `gray-70` |

- Cada severidad lleva su ícono de Carbon (`ErrorFilled`, `WarningFilled`, `WarningAltFilled`,
  `InformationFilled`) y su nombre en texto accesible; el amarillo no alcanza 3:1 sobre blanco, así que su
  identificación la da el ícono con glifo oscuro, nunca el borde solo.
- Real = relleno sólido; plan/meta = contorno; pronóstico = achurado (IBCS). El acento de interacción es el azul
  de Carbon (`$interactive`) y solo en acciones, foco y selección.

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
