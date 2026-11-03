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
  de Carbon), el complementario al 85 % con negro al pasar el ratón y al 70 % al pulsar, sin borde propio; el botón
  terciario lleva contorno y texto en el complementario, se rellena de él con texto blanco al pasar el ratón y al 75 % con
  negro al pulsar; los enlaces (subrayados), los bordes interactivos y la raya de la pestaña activa van también en
  `--silice-complementario` (sin él, el marco);
  los contadores de la barra lateral llevan su propio número y fondo (`--silice-contador-numero` y `--silice-contador-fondo`,
  sin ellos el marco y el lateral) y un contorno de 1 px del color del número. Vale en toda la aplicación (también
  bienvenida, entrar y recuperar acceso) y en los diálogos. El servidor avisa (`GET /v1/tema`, `avisos`) si el texto del
  botón (blanco sobre el complementario) no llega a 7:1 en sus tres estados, el complementario a 4,5:1 sobre el fondo, el
  blanco y el lateral, las iniciales de la cuenta (marco sobre acento) a 4,5:1 y el contador a 4,5:1 (número) y 3:1
  (contorno). El foco sigue siendo el azul de Carbon (`$focus`), salvo en «Nueva obra»: contorno blanco de 2 px por dentro, porque el blanco es el único contorno cuyo
  contraste con el botón ya garantiza el servidor (7:1). El tema neutro del repositorio usa el amarillo claro
  (`yellow-20`) y el gris de Carbon.

### Papeles del color (rediseño F3, Tarea 4c)

| Papel | Color | Dónde |
|---|---|---|
| **Precaución** | amarillo de Carbon (avisos) | notificaciones y avisos de Carbon, tal como vienen; nunca relleno de una acción |
| **Marca** | `--silice-acento` (ámbar) | raya bajo la barra superior, opción de tamaño de letra activa en la barra superior (sobre fondo claro, como en Entrar, va en el complementario), iniciales de la cuenta |
| **Acción** | `--silice-complementario` | botón principal («Nueva obra» incluido), enlaces, bordes interactivos, raya de la pestaña activa, botón terciario |

- **Selección sobre fondo claro = complementario.** La raya de la opción activa del tamaño de letra es el acento en la barra
  superior (marco oscuro), pero en Entrar y en las demás pantallas sin marco el fondo es claro y el acento no llega a 3:1
  (WCAG 1.4.11): allí va en `--silice-complementario` (el servidor lo mide ≥ 4,5:1 sobre el fondo, el blanco y el lateral).
  Nunca queda en el azul de Carbon.
- Regla de identidad: el acento **nunca** va solo como identidad; siempre junto al marco (`--silice-marco`) y al
  complementario. El ámbar solo es genérico del sector: en una empresa con otro color de acento, la identidad la llevan el
  marco y el complementario.
- Ningún uso de `--silice-acento` puede ser el relleno de una acción, y ningún `--cds-button-*` puede apuntar al acento: el
  botón principal se confunde con el aviso amarillo de Carbon si comparten familia de color (hallazgo H3 del cierre de F3).

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
  derecha despliega, izquierda pliega; la obra abierta desplegada en sus secciones con una línea guía; el nombre de una obra
  se recorta a 2 líneas con puntos suspensivos y su `title` con el nombre completo aparece solo si de verdad está recortado,
  medido al pasar el ratón); y **Empresa** (Precios y catálogo, Auditar un presupuesto, Producción, Empresa y
  personas, Ayuda). Activo: fondo `--silice-lateral-activo` y raya de 3 px `--silice-marco`. Lo que la cuenta no puede
  usar no aparece. La cabecera de Obras y «Nueva obra» quedan fijas y el árbol tiene su propio
  desplazamiento. **Letra Grande o Muy grande:** filas y títulos se compactan (mixin `con-letra-grande` de `_umbrales.scss`: filas de 1,5 rem, títulos con menos
  relleno), Empresa se pliega (véase «Empresa plegada con letra grande»), la zona de obras conserva 10 rem como mínimo y,
  si aun así no cabe todo, se desplaza la barra entera. Nada desaparece: lo plegado se abre con un clic y los tres botones
  de tamaño de letra siguen.
- **La obra** (`EspacioDeObra.tsx`, ruta `#/obra/<carpeta>/<obra>/<sección>`): antes de montar la sección se fija la obra
  en la sesión; encima va la cabecera de la obra (véase «Cabecera de la obra»), que no es un encabezado: el único h1 es el
  de la sección. «Esa obra ya no existe» (con «Volver a Pendientes») y «Esta obra se abrió en otra pestaña» (con
  «Retomar») son pantallas con su h1. Sus secciones se describen en «Secciones de la obra».
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

### Empresa plegada con letra grande

Rediseño F4, Tarea 0 (`marco/ZonaEmpresa.tsx`, `comun/useTamanoDeLetra.ts`). En el cierre de F3, con letra Muy grande
cabían 7 obras a 1366×768 y 4 a 1366×657, y Empresa ocupaba casi lo mismo que el árbol; Eugenio eligió plegarla.

- Con letra **Normal**, Empresa es un h2 con su lista, sin botón.
- Con **Grande** o **Muy grande**, el h2 lleva un botón desplegable (WAI-ARIA: `aria-expanded` y `aria-controls`, chevron
  a la derecha plegada y hacia abajo desplegada) que arranca **plegado**, salvo que la ruta sea una entrada de Empresa:
  entonces arranca abierto. Su alto pasa al árbol de obras.
- La decisión de plegar o desplegar vale para el tamaño de letra con que se tomó y no se recuerda entre sesiones
  (pregunta 13 del plan F4). Cambiar la letra en vivo la vuelve a evaluar (`useTamanoDeLetra` observa el atributo de la
  raíz).

### Cabecera de la obra

Rediseño F4, Tarea 1 (`marco/CabeceraDeObra.tsx`, `marco/EtapaDeObra.tsx`). Una región «Obra abierta» encima de la
sección, sin encabezado propio (el h1 es el de la sección):

- el nombre de la obra;
- **Estado:** la palabra que da el servidor (`etapa_texto`) con su ícono de Carbon delante, decorativo (`aria-hidden`):
  en elaboración `Edit`, en aprobación `Time`, aprobada `CheckmarkOutline`, en ejecución `InProgress` y atrasada
  `WarningFilled`. Solo la atrasada lleva color, y nunca va sin la palabra. Sin la ficha (cargando, sin permiso) no se
  dice nada;
- la versión: «Versión: V» (la vigente) o, si el borrador abierto sale de otra, «Versión abierta: V (la vigente es W)»;
- debajo, la moneda y la lista para armar de la carpeta.

La misma pieza `EtapaDeObra` pinta el estado en las cifras del Resumen y en la tabla de obras: no pueden divergir.

## Secciones de la obra

El árbol ofrece, por obra y según lo que la cuenta puede usar: Resumen, Presupuesto, Tramos (módulo vial), Archivos y
planos, Versiones, Aprobaciones, Mercado y Control de obra (`marco/secciones.ts`). Presupuesto, Archivos y planos y
Versiones comparten el borrador de la obra (`ProveedorDeLaHoja`): pasar de una a otra no lo cierra ni pregunta. Quien
solo revisa ve cada sección en solo lectura: lo que escribe no se pinta (no se deshabilita).

- **Resumen** (`paginas/obras/`): las cifras de la obra, su versión vigente y lo pendiente, con la franja del paso.
- **Presupuesto** (`paginas/hoja/`, h1 «Presupuesto»; antes «Hoja de la obra»): la franja del paso arriba, el estado del
  borrador y las pestañas «Partidas», «Análisis de precio (APU)», «Plan y equilibrio», «Precios», «Revisión» y «Ajustes de
  costo»; «Espacio y metrajes» va delante en una obra con espacio. Son seis en una obra civil y siete con espacio (antes,
  nueve). Cada pestaña tiene un solo «¿Qué es esto?» plegado con su ayuda; quien edita ve además, a la vista, cómo se
  escriben las cifras. El código de cada renglón con precio abre su APU en el panel lateral; «Agregar partida» busca en
  el catálogo, por parecido («Buscar parecidas», antes la pantalla Partidas similares) o compone una nueva en el panel,
  sin salir de la obra.
- **Archivos y planos** (`paginas/archivos/`): «Subir plano o cómputo» abre un diálogo modal con una sola zona de soltar
  que elige el flujo por la extensión: `.dxf` o `.ifc`, el plano; `.csv`, «Cargar cómputo», que absorbió la pantalla
  Elaborar y lleva las partidas al mismo borrador. Debajo, la tabla «Registro de importaciones» (fecha y hora, quién, qué
  produjo y la versión, o «sin guardar»); cada fila abre su informe en el panel lateral. Con la especialidad «edificación»
  apagada la sección sigue: la puerta se llama «Cargar cómputo» y solo acepta `.csv`.
- **Versiones** (`paginas/versiones/`): la región «Cadena de sellos» (íntegra, o rota en la versión V, con su ícono)
  encima de la tabla «Versiones de la obra» (versión, fecha, motivo, de cuál sale, cambios, estado de aprobación, vigente y
  acciones). La abierta dice «abierta» y la descartada «descartada», en palabra. «Abrir» lleva al Presupuesto con esa
  versión; «Ver cambios» abre el registro de cambios en el panel lateral ancho; «Restaurar…» abre su diálogo con la versión
  de la fila elegida. Antes era la pestaña «Trazabilidad» y el selector «Versión» de la Hoja.
- **Mercado** (`paginas/mercado/`, h1 «Estudio de mercado») con cuatro pestañas de Carbon: «Lo que compramos» y «Lo que
  cobramos» (anotar observaciones y usar precios; solo con `editar_hoja`), «Histórico de precios» (h2, filtros por insumo
  y fechas, «Filtrar» secundario; antes, una pantalla suelta) y «Cotizaciones de la obra» (la tabla con el rastro de la
  conversión; «Registrar una cotización…» y «Retirar una cotización…» crean una versión desde la vigente y se avisa con el
  enlace para abrirla en el Presupuesto). Las dos últimas se montan al elegirlas. Quien revisa ve solo esas dos, sin
  controles que escriban.

En cada sección: un solo h1, un solo botón principal a la vista (con un diálogo abierto, el del diálogo; el de detrás pasa
a secundario) y nada de desplazamiento horizontal a 1056, 1366 y 1910 px con las tres letras.

### Franja del paso

`comun/FranjaDelPaso.tsx` (Tareas 2 y 5 de F4). Es el molde de toda sección: dice **un solo** paso, arriba, antes de lo
demás, y su botón es **el único principal** de la pantalla mientras está a la vista. Sin acción posible para la cuenta,
la franja solo informa.

- **«Te falta:»** es una precaución: fondo `--silice-aviso-fondo`, raya izquierda de 4 px `--silice-aviso-borde` e ícono
  `WarningAltFilled`; la palabra dice lo que es y el color no va solo. Con contraste forzado el fondo se va y queda un
  borde propio.
- **«Siguiente paso:»** solo orienta: una línea entre divisores de 1 px, sin ícono ni fondo.
- El botón es el principal de Carbon (complementario con texto blanco, véase «Papeles del color»); con un diálogo de la
  pantalla abierto pasa a secundario (`enSegundoPlano`). Texto y botón bajan de línea si no caben: la franja no ensancha
  la página con letra grande.
- La región se llama «Siguiente paso» para la lectora en los dos tipos.

### Panel lateral

`comun/PanelLateral.tsx` (Tareas 6 y 7 de F4). Un `aside` acoplado a la derecha del contenido, nombrado por su h2: el APU
de una partida, el registro de cambios de una versión, Componer y el informe de una importación.

- **No es un diálogo**: no atrapa el foco ni deja la página inerte; se queda junto al contenido, como la columna del
  recorrido. Quien lo usa lo pone en `silice-con-panel` (contenido `minmax(0, 1fr)` a la izquierda y el panel a la
  derecha): las tablas del contenido se desplazan en su caja.
- Dos anchos: **24 rem** (normal: el informe de una importación) y **40 rem** (ancho: el APU, el registro de cambios y
  Componer).
- Separado por un borde de 1 px `--cds-border-subtle`, sin sombra ni animación.
- Al abrirse el foco va a su h2, con el contorno de foco visible; **Esc** (nacido dentro del panel y no usado ya por un
  campo) o **«Cerrar»** lo cierran y el foco vuelve al control que lo abrió (el último, si otra fila lo volvió a abrir).
- **Por debajo del umbral de la letra** (`marco/_umbrales.scss`) pasa por encima del contenido, fijo bajo la barra
  superior, a lo más del ancho de la ventana y con su propio desplazamiento. Componer en panel es la excepción: atrapa
  Tab dentro del panel, porque el diálogo «Agregar partida» del que sale queda oculto debajo.

### Filas afectadas

Tarea 5 de F4 (`claseDeFila` de `TablaDensa` y `TablaPaginada`; `esFilaAfectada` en `paginas/hoja/pasoDelPresupuesto.ts`).
En «Partidas», el renglón con un hallazgo CRITICO, ERROR o ADVERTENCIA lleva la clase `silice-fila--afectada`: fondo de
precaución `--silice-aviso-fondo` en todas sus celdas, también en la celda fija de la izquierda. INFO no afecta. Nunca es
el acento ni un color de severidad suelto: la severidad se sigue diciendo **en palabra** en la columna «Estado», con su
ícono. Con contraste forzado el fondo se va y la palabra queda.

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
