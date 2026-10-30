# Design

<!--
THESIS: el libro es la evidencia y la pantalla es una lente forense sobre él. Se rechaza el tablero de tarjetas
con KPI en grande y la hoja escondida detrás de un clic.
OWN-WORLD: IBM Carbon g10 nativo (paquete oficial @carbon/react), IBM Plex Sans y Mono, esquinas rectas,
divisores de 1 px, severidad con ícono, morado solo para atípicos, verde/rojo IBCS solo en cifras de variación.
STORY: el auditor suelta el libro, lo ve como en Excel con las celdas marcadas, toca un hallazgo, cae en su
celda y lee libro contra Sílice.
FIRST VIEWPORT: barra superior de 3 rem; franja de indicadores Fiori de 64 px como mínimo (crece con la etiqueta del libro menor); la hoja ocupa el resto a la izquierda;
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
  `--silice-escala-letra`. Con Grande y Muy grande el buscador de la barra superior queda en su ícono por debajo de 1536
  y 1920 px (véase «Marco»), y la cuenta queda en su círculo de iniciales. El texto de los gráficos de Carbon Charts
  también sigue la escala; el lienzo de la hoja de Excel (Univer) dibuja en píxeles y sigue la escala por el acercamiento propio de Univer (zoom efectivo = zoom propio de la hoja × factor de la letra, tope 400 %); la barra de la hoja trae su control de zoom (50 a 300 %). IBM Plex es la
  cara nativa de Carbon, que el brief fija: se aloja en el propio servidor, sin CDN.
- **Forma:** esquinas rectas (radio 0, como Carbon); separación con divisores de 1 px `$border-subtle` y espacio,
  no con tarjetas con sombra. Sin gradientes, sin sombras decorativas, sin vidrio. Única excepción a las esquinas rectas:
  la píldora de los contadores de la barra lateral (especificación 2026-10-26, §8 ter, aprobada por Eugenio) y el círculo
  de iniciales del botón de la cuenta (rediseño F3, D-F3-5).
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
- Real = relleno sólido; plan/meta = contorno; pronóstico = achurado (IBCS). El color de acción lo pone la empresa
  (rediseño F3, Tarea 4c; ver «Papeles del color» abajo): el botón principal es el **complementario** con texto blanco (el
  de Carbon), el complementario al 85 % con negro al pasar el ratón y al 70 % al pulsar, sin borde propio; los enlaces
  (subrayados), los bordes interactivos y la raya de la pestaña activa van también en `--silice-complementario` (sin él, el marco);
  los contadores de la barra lateral llevan su propio número y fondo (`--silice-contador-numero` y `--silice-contador-fondo`,
  sin ellos el marco y el lateral) y un contorno de 1 px del color del número. Vale en toda la aplicación (también
  bienvenida, entrar y recuperar acceso) y en los diálogos. El servidor avisa (`GET /v1/tema`, `avisos`) si el texto del
  botón (blanco sobre el complementario) no llega a 7:1 en sus tres estados, el complementario a 4,5:1 sobre el fondo, el
  blanco y el lateral, las iniciales de la cuenta (marco sobre acento) a 4,5:1 y el contador a 4,5:1 (número) y 3:1
  (contorno). El foco sigue siendo el azul de Carbon (`$focus`), y el tema neutro del repositorio usa el amarillo claro
  (`yellow-20`) y el gris de Carbon.

### Papeles del color (rediseño F3, Tarea 4c)

| Papel | Color | Dónde |
|---|---|---|
| **Precaución** | amarillo de Carbon (avisos) | notificaciones y avisos de Carbon, tal como vienen; nunca relleno de una acción |
| **Marca** | `--silice-acento` (ámbar) | raya bajo la barra superior, opción de tamaño de letra activa, iniciales de la cuenta |
| **Acción** | `--silice-complementario` | botón principal («Nueva obra» incluido), enlaces, bordes interactivos, raya de la pestaña activa, botón terciario |

- Regla de identidad: el acento **nunca** va solo como identidad; siempre junto al marco (`--silice-marco`) y al
  complementario. El ámbar solo es genérico del sector: en una empresa con otro color de acento, la identidad la llevan el
  marco y el complementario.
- Ningún uso de `--silice-acento` ni de `--cds-button-primary*` puede ser el relleno de una acción: el botón principal se
  confunde con el aviso amarillo de Carbon si comparten familia de color (hallazgo H3 del cierre de F3).

## Marco

Una **barra superior** y, debajo, una **barra lateral en árbol** a la izquierda y el contenido (especificación
`docs/especificaciones/2026-10-26-rediseno-marco-obras-design.md`; código en `src/marco/`). La navegación va por obras y
pendientes, no por herramientas: nada de módulos ni áreas.

- **Barra superior** (`BarraSuperior.tsx`): 3 rem de alto (sigue la escala de letra), fondo `--silice-marco` con texto
  inverso y raya inferior de 3 px `--silice-acento`; queda fija al desplazar. A la izquierda el logo de la empresa (o
  «Sílice»); luego las **migas** (`Mis obras / <obra> / <sección>`, `Empresa / <entrada>`, `Pendientes` o el título de la
  pantalla; la última con `aria-current`); a la derecha el botón **«Buscar… (Ctrl+K)»**, la marca de la demostración y
  «Recorrido» cuando tocan, el tamaño de letra y la cuenta (un círculo con las iniciales —primera y última palabra—, el
  nombre y un menú con «Salir»; con letra Grande o Muy grande, solo el círculo, con el mismo nombre accesible; sin letras en
  el nombre, el ícono de persona).
- **Barra lateral** (`BarraLateral.tsx`): 14,75 rem, fondo `--silice-lateral`, fija al desplazar el contenido y con su
  propio desplazamiento. Tres zonas: **Pendientes**; **Obras**, con «Nueva obra» como botón principal fijo bajo su
  cabecera (relleno `--silice-complementario`, texto blanco) y el árbol de obras (patrón `tree` de WAI-ARIA: flechas,
  derecha despliega, izquierda pliega; agrupado por carpeta solo si hay más de una; la obra abierta desplegada en sus
  secciones con una línea guía); y **Empresa** (Precios y catálogo, Auditar un presupuesto, Producción, Empresa y
  personas, Ayuda). Activo: fondo `--silice-lateral-activo` y raya de 3 px `--silice-marco`. Lo que la cuenta no puede
  usar no aparece.
- **La obra** (`EspacioDeObra.tsx`, ruta `#/obra/<carpeta>/<obra>/<sección>`): antes de montar la sección se fija la obra
  en la sesión; encima va la cabecera de la obra (nombre, moneda, versión y la lista para armar de su carpeta), que no es
  un encabezado: el único h1 es el de la sección. «Esa obra ya no existe» (con «Volver a Pendientes») y «Esta obra se
  abrió en otra pestaña» (con «Retomar») son pantallas con su h1.
- **Buscador** (`Buscador.tsx`): diálogo propio con combobox y lista (obras, sus secciones, Empresa y las pantallas sin
  sitio en el árbol). Ctrl+K o el botón lo abren; Esc lo cierra y el foco vuelve al botón.
- **Salir sin perder trabajo:** elegir otra obra, sección o entrada en el marco con cambios sin guardar pregunta
  («Cambios sin guardar»); si la obra está en otra carpeta, también nombra los borradores de la Hoja que se perderían.
  Atrás y adelante del navegador no se interceptan.
- **Umbrales por letra:** viven solo en `src/marco/_umbrales.scss` (mixin `por-debajo-del-umbral`, 1056, 1536 y 1920 px
  para Normal, Grande y Muy grande), porque la consulta en rem de Carbon no sigue la letra de Sílice. Por debajo, el
  buscador queda en su ícono y la columna del recorrido pasa a franja.
- **Recorrido guiado:** con un recorrido en curso, la columna «Recorrido» queda **acoplada a la derecha** (16 rem, bajo la
  barra) y el contenido le cede ese ancho; no es una capa. «Ocultar» la pliega (queda el botón «Recorrido» en la barra) y
  «Terminar recorrido» la quita. Por debajo del umbral de la letra pasa a franja plegable bajo la barra.
- 1366×768 y 1056 px sin desplazamiento horizontal con las tres letras. Los textos del marco dicen obra, sección,
  pendiente y empresa; nunca «módulo», «área», «página» ni «carpeta de trabajo» (salvo Empresa › Carpetas de trabajo,
  para quien administra). Lo vigila `src/paginas/sinJergaInterna.test.ts`.

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
