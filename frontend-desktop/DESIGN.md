# Design

<!--
THESIS: el libro es la evidencia y la pantalla es una lente forense sobre él. Se rechaza el tablero de tarjetas
con KPI en grande como sustituto de la evidencia, y la hoja escondida detrás de un clic. La app abre en la Vista general,
que pone primero lo que bloquea; la cartera va por moneda, sin sumar Bs con USD. La navegación va por espacios.
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
  también sigue la escala (los gráficos van sin su barra de herramientas: su `button` queda dentro de un `div role="button"`, defecto de la librería que axe anota como `nested-interactive`, con rótulos en inglés; cada gráfico ya trae su tabla de montos exactos); el lienzo de la hoja de Excel (Univer) dibuja en píxeles y sigue la escala por el acercamiento propio de Univer (zoom efectivo = zoom propio de la hoja × factor de la letra, tope 400 %); la barra de la hoja trae su control de zoom (50 a 300 %). IBM Plex es la
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
- **Ícono de advertencia = `--silice-sev-advertencia-icono` (`yellow-50`, #b28600), no el token de los halos.** El triángulo
  amarillo `yellow-30` medía 1,53:1 sobre el gris 10 del tema (rgb 244,244,244) y 1,69:1 sobre blanco: no llega al 3:1 que
  WCAG 1.4.11 pide a un gráfico (pasada en el navegador de F6, H1). El `yellow-50` da 3,03:1 sobre el gris 10 y 3,33:1 sobre
  blanco, sigue siendo ámbar (el mismo significado) y es el de la franja de la etiqueta del libro menor. Lo usan el ícono
  `.silice-sev--advertencia .silice-sev__icono` (Bandeja de Pendientes, «Lo que requiere atención», lista de hallazgos), el de
  la arenera y el de «queda poco» de existencias. **Los halos de la hoja siguen con `--silice-sev-advertencia` (`yellow-30`)**:
  llevan su segundo contorno oscuro (`visor.scss`). El atípico en morado cambia las dos variables a la vez
  (`MORADO_ATIPICO`). La palabra «Aviso» o «Advertencia» va siempre junto al ícono. Lo vigila
  `indicadores/contrasteAviso.test.ts`, que calcula las razones.
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

Una **barra superior** y, debajo, una **barra lateral plana** a la izquierda y el contenido (especificación
`docs/especificaciones/2026-10-26-rediseno-marco-obras-design.md`, enmendada por
`docs/especificaciones/2026-11-04-f6-enmienda.md`; código en `src/marco/`). La navegación va por **espacios** (véase
«Espacios»): la Vista general, cada obra y, para lo que es de toda la empresa, Producción, Auditoría y Precios; y la Cuenta.
En los textos no se dice «módulo» ni «área».

- **Barra superior** (`BarraSuperior.tsx`): 3 rem de alto, fondo `--silice-marco` con texto inverso y raya inferior de 3 px
  `--silice-acento`. Es fija al desplazar (`marco.scss`). A la izquierda, la marca «Sílice» (o el logo de la empresa), que
  lleva a la ruta índice `/` y de allí a la Vista general; al lado, «Carpeta activa: <carpeta>». **Sin migas**: la ubicación
  la dicen la barra lateral, la barra de cada espacio y el título de la pestaña del navegador (`ubicar.ts`). A la derecha, el
  botón **«Buscar una obra, sección o pantalla… (Ctrl+K)»**, un hueco para lo que pone `Marco` (la marca de la demostración y
  «Recorrido» cuando tocan) y el botón de la persona: un enlace a `#/cuenta/preferencias`, con el círculo de iniciales y el
  nombre; con letra Grande o Muy grande, solo el círculo, con el mismo nombre accesible; sin letras en el nombre, el ícono de
  persona. Salir de la sesión está en la Cuenta, no aquí.
- **Tamaño de letra:** dentro del marco vive **solo en la Cuenta**, «Pantalla y tamaño de letra» (`#/cuenta/preferencias`,
  `EspacioDeCuenta.tsx`), a un clic del botón de la persona (decisión de Eugenio, 2026-11-04). Antes de entrar en la sesión,
  la cabecera sin marco de `App.tsx` todavía muestra el control: es la única excepción.
- **Barra lateral** (`BarraLateral.tsx`): 14,75 rem, fondo `--silice-lateral`. Es fija bajo la barra superior, con su propio
  desplazamiento. Tres zonas, en este orden:
  1. **Vista general**, la primera entrada, con la píldora de pendientes si hay alguno. Es la entrada de la app (véase
     «Vista general»).
  2. **Obras**: lista plana, sin árbol. Cada obra es un enlace a su Resumen y lleva su píldora de pendientes; las obras de
     nombre repetido dicen su carpeta. «Nueva obra» va en la cabecera de la zona. Las secciones de la obra abierta no
     van aquí: van en la barra de la obra, bajo su cabecera (véase «Espacios»).
  3. **Costos y producción** (`ZonaDeCostos.tsx`): Auditar un presupuesto, Precios y catálogo y Costos de producción. Cada
     uno es un enlace a su espacio.

  Lo que la cuenta no puede usar no aparece. La Cuenta no tiene entrada en la barra lateral. Activo: fondo
  `--silice-lateral-activo` y raya de 3 px `--silice-marco`. **Letra Grande o Muy grande:** filas de 1,5 rem y títulos con
  menos relleno (mixin `con-letra-grande` de `_umbrales.scss`); Costos y producción se pliega (véase «Costos y producción
  plegado con letra grande»); si aun así no cabe todo, se desplaza la barra entera. Nada desaparece: lo plegado se abre con
  un clic.

- **La obra** (`EspacioDeObra.tsx`, ruta `#/obra/<carpeta>/<obra>/<sección>`): antes de montar la sección se fija la obra
  en la sesión; encima va la cabecera de la obra (véase «Cabecera de la obra»), que no es un encabezado: el único h1 es el
  de la sección. Una pantalla que la cuenta no puede usar (o de una especialidad apagada) la sustituye el aviso «Sin permiso»
  (o «Apagada»), que es el único h1 de la página (`marco/avisos.tsx`; `EstadoVacio` admite `nivel`); en la Cuenta, donde la
  página ya trae el h1 de la sección, baja a h2. «Esa obra ya no existe» (con «Volver a Pendientes») y «Esta obra se abrió en otra pestaña» (con
  «Retomar») son pantallas con su h1. Sus secciones se describen en «Secciones de la obra».
- **Buscador** (`Buscador.tsx`, `busqueda.ts`): diálogo propio con combobox y lista. Busca, en este orden, obras, sus secciones,
  las secciones de la Cuenta (también por su ayuda, así «personas» lleva a «Cuentas y permisos») y las herramientas de
  Producción, Auditoría y Precios (por su título o el nombre del espacio). Ocho resultados como máximo, sin rutas repetidas. Ctrl+K o el botón lo abren; Esc lo cierra y el foco vuelve al botón.
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
  pendiente y empresa; nunca «módulo», «área», «página» ni «carpeta de trabajo» (salvo Cuenta › Carpetas,
  para quien administra). Lo vigila `src/paginas/sinJergaInterna.test.ts`.

### Costos y producción plegado con letra grande

Rediseño F4, Tarea 0, y F6, Tarea 6 (`marco/ZonaDeCostos.tsx`). Antes era la zona Empresa; F6 la sustituyó por esta, con solo
sus tres espacios de la empresa. Con letra **Normal**, la zona es un encabezado con su lista, sin botón. Con **Grande** o
**Muy grande**, el encabezado lleva un botón desplegable (WAI-ARIA: `aria-expanded` y `aria-controls`) que arranca plegado,
salvo que la ruta sea de uno de sus tres espacios. Su alto pasa a la lista de obras. La decisión de plegar o desplegar vale
para el tamaño de letra con que se tomó y no se recuerda entre sesiones.

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

## Espacios

Rediseño F6 (`marco/espacios.ts`, `marco/BarraDeEspacio.tsx`, `marco/Marco.tsx`). Cada espacio tiene su familia de rutas y
una sola ruta canónica por pantalla (`rutaCanonica`); ningún enlace escribe una ruta a mano.

| Espacio | Ruta | Qué contiene |
|---|---|---|
| Inicio | `#/inicio/:vista` | la Vista general (`general`) y la bandeja de Pendientes (`pendientes`) |
| La obra | `#/obra/:carpeta/:obraId/:seccion/:subvista?` | las nueve secciones de la obra y sus subvistas |
| Producción | `#/produccion/:herramienta` | Resumen de arenera, Existencias, Costos del período, Costo por tonelada, Receta de la planta y Producir mezcla |
| Auditoría | `#/auditoria/:herramienta` | Subir y auditar Excel, Libro de la empresa e Historial de auditorías |
| Precios | `#/precios/:herramienta` | Precios de la empresa, Catálogo de partidas e insumos, Índices del BCV y Simulador de listas |
| Cuenta | `#/cuenta/:seccion` | las seis secciones de la Cuenta (abajo) |

**Barra de espacio.** Debajo de la cabecera de cada espacio va la barra de espacio (`BarraDeEspacio.tsx`): un `nav` con
`aria-label`, fondo `--cds-layer-01` y divisor inferior de 1 px `--cds-border-subtle`. Cada pestaña es un enlace a su ruta,
con `aria-current="page"` en la activa; no es un `tablist`. La pestaña activa lleva una raya inferior de 3 px en
`--silice-complementario`, que se distingue de las pestañas de Carbon. Cada pestaña mide 2,5 rem como mínimo (2 rem con letra
Grande o Muy grande). Tab las recorre en orden. Solo aparecen las herramientas que la cuenta puede usar; una herramienta
inaccesible no aparece. Al entrar en un espacio sin herramienta, se abre la primera que la cuenta sí puede usar.

**Subvistas de la obra.** Las secciones con pantallas dependientes muestran sus subvistas en un conmutador compacto
(`BarraDeEspacio` con `nivel="subvista"`, bajo la barra de secciones; `EspacioDeObra.tsx`). La primera de cada fila es la
pantalla principal de la sección:

| Sección | Subvistas |
|---|---|
| Resumen | «Resumen», «Tablero» |
| Presupuesto | «Presupuesto», «Componer» |
| Aprobaciones | «Aprobar», «Revisar un paquete», «Entregar» |
| Mercado | «Estudio», «Actualizar precios» |
| Control de obra | «Control», «Reajuste», «Escenarios» |

El conmutador de Presupuesto dice «Presupuesto | Componer», no «Partidas» (decisión de Eugenio, 2026-11-04).

**La Cuenta** (`EspacioDeCuenta.tsx`) tiene su barra con seis secciones: «Pantalla y tamaño de letra», «Cuentas y permisos»,
«Empresa y tema», «Carpetas», «Especialidades, IA e instalación» y «Ayuda y acerca de Sílice». Lo que la cuenta no puede
usar no aparece; «Carpetas» pide además `cambiar_caso`. **El h1 de cada sección dice lo mismo que su pestaña** (también la
Ayuda: «Ayuda y acerca de Sílice»; antes decía «Acerca de Sílice»). Una sección escrita a mano que la cuenta no puede usar
lleva su h1 y, debajo, el aviso «Sin permiso» en un h2.

**Direcciones que no existen.** Una dirección sin pantalla (el comodín de `Marco.tsx`, línea 423) lleva a la Vista general.
Las direcciones viejas se redirigen a su nuevo sitio (contrato de rutas, §2.4).

## Vista general

Rediseño F6, Tarea 8 (`paginas/inicio/index.tsx`, `paginas/inicio/CarteraYAvance.tsx`, `marco/EspacioDeInicio.tsx`). Es la
**entrada de la app**: la ruta índice lleva a `#/inicio/general` (`Marco.tsx`, línea 361), y la marca «Sílice» también
(por `/`). Así lo fijó Eugenio el 2026-11-04 y deja sin efecto lo que decía la especificación de 2026-10-26: la entrada ya no
es la bandeja de Pendientes (`docs/especificaciones/2026-11-04-f6-enmienda.md`). La bandeja sigue en `#/inicio/pendientes`, a
un clic en la barra del espacio, al lado de «Vista general». Toda cuenta ve las dos.

La cabecera del espacio dice «Vista general»; el único `h1` es el de la pantalla. Los bloques, en este orden:

0. **Empieza aquí** (F7, A4; `paginas/ayuda/BloqueEmpiezaAqui.tsx`), solo la primera vez y derivado de los datos, sin guardar
   nada en el navegador (`pasosDeEmpiezaAqui`): a quien administra mientras su cuenta sea la única activa (`GET /v1/cuentas`),
   a quien arma o solo revisa mientras no vea ninguna obra (una cartera con carpetas omitidas no cuenta como «sin obras»). Una
   lista numerada de pasos, cada uno con su enlace; **sin botones**: el único principal sigue siendo «Nueva obra» del estado
   vacío de la cartera. Al pie, «Ver las guías y el glosario».
1. **Lo que requiere atención.** Los primeros cinco pendientes de la bandeja, del más urgente al menos urgente. Lo que
   bloquea lleva el ícono de error y su palabra; el aviso, el ícono de advertencia y su palabra. Un enlace lleva a la bandeja
   con el total. Sin pendientes, una sola línea: «No tiene pendientes por hacer.» (`LoQueBloquea.tsx`).
2. **Cartera por moneda.** Una tarjeta por moneda presente (Bs y USD), cada una con la franja `FranjaDeCifras`: total vigente,
   obras y en ejecución. Bs y USD **nunca se suman ni se promedian**: el servidor agrupa por moneda
   (`aplicacion/resumen_todas.py`, `_por_moneda`) y la pantalla pinta cada fila tal cual (`CarteraYAvance.tsx`, `Cartera`).
   Se usa `FranjaDeCifras` y no `IndicadorFiori`, porque estas cifras no tienen meta ni variación; reusa las clases de
   `FranjaIndicadores`.
3. **Obras y avance contra el plan.** Una tabla con una fila por obra: el nombre (enlace a su Resumen, con la carpeta si es
   homónima), la etapa, el total y el avance. El avance dice «Real X % · Plan Y %» y lleva una barra: el real en relleno
   sólido y el plan en contorno, con las cifras al lado para que el color no vaya solo. Sin avance, «Sin avance»; sin versión,
   «Sin versión». Dentro de «Real 67,0 %» y de «Plan 76,7 %» van espacios duros (U+00A0): se lee igual, el «%» no cae solo en otra línea y el texto solo se parte en el «·».
   La barra da su alto en rem (`.fiori-kpi__barra`, 0,75 rem), así que crece con la letra; el contorno del plan es de 0,0625 rem.
   **Con letra grande, filas apiladas.** La caja de la tabla es un contenedor (`container-type: inline-size`, `silice-inicio__obras`):
   cuando mide menos de 42 rem (en rem, no en px: el umbral crece con la letra) cada obra se apila en un bloque con el nombre
   arriba y «Estado», «Total» y «Avance» con su etiqueta (`data-etiqueta`, la cabecera sigue ahí para los lectores de pantalla), y la
   columna de avance nunca queda fuera de la vista (a 1056 px con letra Muy grande la tabla de cuatro columnas pedía 1104 px
   y solo había 587). Si aun así algo se desplazara, la caja es la región que se desplaza: `role="region"`, `tabindex="0"`,
   nombre «…: desplazar horizontalmente» y el anillo de foco de Carbon, como las tablas de la hoja.
4. **Últimas auditorías.** Las cinco últimas auditorías guardadas, con su resultado en palabras («Sin errores ni
   advertencias», o cuántos errores y advertencias) y un enlace a Auditoría. Solo con `leer_proyecto`. Sin ninguna guardada, el
   vacío manda a Auditoría («Para auditar un presupuesto, vaya a Auditoría…») y no habla de soltar un Excel «arriba»: eso solo
   vale dentro de Auditoría (`UltimasAuditorias`, prop `desde`).
5. **Arenera.** Solo con `operar_arenera` y con la especialidad de producción encendida (`paginas/inicio/index.tsx`, línea 30).

La pantalla no calcula nada: cada cifra es la del servidor, solo formateada en es-VE (coma decimal, punto de miles). Cada
bloque pide sus datos por su cuenta; si uno falla, dice su error sin tumbar a los demás. Sin `leer_proyecto`, la cartera y el
avance no se pintan. Sin obras, el estado vacío: quien puede crear ve «Nueva obra»; quien solo revisa lee «No hay obras que su cuenta pueda ver»
(la Vista general reúne todas las carpetas que la cuenta puede abrir, no una).

## Secciones de la obra

Las nueve secciones de la obra van en su barra, bajo la cabecera (véase «Espacios»), en el orden de `marco/secciones.ts`
(líneas 21-31): Resumen, Presupuesto, Tramos, Archivos y planos, Versiones, Aprobaciones, Mercado, Control de obra y Riesgo.
Las que tienen subvistas las muestran en su conmutador. Cada cuenta ve solo las que puede usar. Presupuesto, Archivos y planos y
Versiones comparten el borrador de la obra (`ProveedorDeLaHoja`): pasar de una a otra no lo cierra ni pregunta. Quien
solo revisa ve cada sección en solo lectura: lo que escribe no se pinta (no se deshabilita).

- **Resumen** (`paginas/obras/`): las cifras de la obra, su versión («Versión de la línea base» o, sin ella, «Versión vigente») y lo pendiente, con la franja del paso.
- **Presupuesto** (`paginas/hoja/`, h1 «Presupuesto»; antes «Hoja de la obra»): una línea de estado bajo el h1 (versión,
  cambios, aprobación y total; `EstadoDelBorrador.tsx`), la franja del paso con «Descargar Excel» al lado y las pestañas «Partidas», «Análisis de precio (APU)», «Plan y equilibrio», «Precios», «Revisión» y «Ajustes de
  costo»; «Espacio y metrajes» va delante en una obra con espacio. Son seis en una obra civil y siete con espacio (antes,
  nueve). Cada pestaña tiene un solo «¿Qué es esto?» plegado con su ayuda; quien edita ve además, a la vista, cómo se
  escriben las cifras. El código de cada renglón con precio abre su APU en el panel lateral; «Agregar partida» busca en
  el catálogo, por parecido («Buscar parecidas», antes la pantalla Partidas similares) o compone una nueva en el panel,
  sin salir de la obra.
  Cabecera compacta (decisión de Eugenio, 2026-11-05; la primera partida pasó de 1.069 a 622 px a 1366×768 con letra Normal):
  una línea de estado (región «Estado del borrador», sin título propio: versión y cambios, «Aprobación» y total), una fila
  de acciones (el paso con su único botón principal y «Descargar Excel», terciario) y, en «Partidas», una barra de
  herramientas sobre la tabla («Agregar partida», cómo se escriben las cifras y «¿Qué es esto?», que abre su ayuda bajo la
  fila). Las regiones vivas vacías (`.silice-hoja__region-viva`) salen del flujo: cada una abría un hueco de la rejilla.
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

### Ayuda de cada pantalla

F7, A1 (`paginas/ayuda/AyudaDeLaPantalla.tsx`, textos en `paginas/ayuda/textos.ts`). Cada pantalla de la obra (secciones y
subvistas), de Producción, Auditoría y Precios y la bandeja de Pendientes lleva **un** «¿Qué es esto?»: el mismo `QueEsEsto`
plegado de las pestañas del Presupuesto, no otro patrón. Lo pone el marco (`EspacioDeObra`, `EspacioDeHerramientas`,
`EspacioDeInicio`) en una fila propia entre la barra de vistas y la pantalla, así que va justo encima del h1; la pantalla baja
su margen superior a 0,5 rem, como tras el conmutador de subvistas. La región se llama como el h1 de la pantalla, dice para qué
sirve y cuándo usarla y, al pie, enlaza su guía («Guía «…»») y los términos del glosario que la pantalla usa sin explicar.
Excepciones: el Presupuesto no lo lleva (cada pestaña trae el suyo) ni una pantalla que la cuenta no puede usar.

**La Ayuda de la Cuenta** (`paginas/ayuda/AyudaDeSilice.tsx`, dentro de «Ayuda y acerca de Sílice»): bajo el h1, el índice
«En esta ayuda» y tres partes con su h2, separadas por un divisor de 1 px: «Empieza aquí» (la primera vez y lo primero de cada
papel), «Guías por tarea» (un h3 por guía, pasos numerados) y «Glosario» (una lista de definición). Después, la versión del
programa y los recorridos guiados. Cada parte se enlaza con `#/cuenta/ayuda?tema=<parte>` y el enlace lleva el foco a ella (con
el enrutador de hash un ancla cambiaría la ruta). Los enlaces de la ayuda viven en el lienzo y preguntan antes de salir con
cambios sin guardar, como los de la barra de espacio.

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

- **No es un diálogo**: no atrapa el foco; se queda junto al contenido, como la columna del
  recorrido. Quien lo usa lo pone en `silice-con-panel` (contenido `minmax(0, 1fr)` a la izquierda y el panel a la
  derecha): las tablas del contenido se desplazan en su caja.
- Dos anchos: **24 rem** (normal: el informe de una importación) y **40 rem** (ancho: el APU, el registro de cambios y
  Componer).
- Separado por un borde de 1 px `--cds-border-subtle`, sin sombra ni animación.
- Al abrirse el foco va a su h2, con el contorno de foco visible; **Esc** (nacido dentro del panel y no usado ya por un
  campo) o **«Cerrar»** lo cierran y el foco vuelve al control que lo abrió (el último, si otra fila lo volvió a abrir).
- **Cuando no cabe junto al contenido** pasa por encima (clase `silice-panel-lateral--superpuesto`): lo decide el ancho
  real del contenedor, con cualquier letra, si no hay sitio para el panel, 1 rem de espacio y **32 rem** de contenido (a
  1366 px con letra Normal el panel ancho dejaba la tabla en 251 px). Va fijo bajo la barra superior, por encima de las
  columnas fijas de las tablas, opaco, a lo más del ancho de la ventana y con su propio desplazamiento: la página nunca se
  desplaza a lo ancho. Mientras tapa, **lo tapado queda `inert`** (Tab no llega a lo que no se ve) y se suelta al
  cerrarlo o al volver a caber; junto al contenido no se toca nada.
- **Componer en panel** va siempre por encima (modo `en-capa`, en la capa del diálogo «Agregar partida», por encima de su
  velo) y es la excepción del foco: atrapa Tab dentro del panel, porque el diálogo del que sale queda oculto debajo.
  **Esc en Componer** (pulido F5, H6): fuera de un campo, un Esc cierra el panel y el foco vuelve a «Partida»; en un campo
  de texto que cambió desde que recibió el foco, el primer Esc lo devuelve a ese valor (como las celdas de la Hoja) y el
  segundo cierra (en «Código», lo elegido de la lista cuenta como confirmado: lo tecleado después vuelve al código elegido y, con el código igual al elegido, Esc cierra); con una lista de sugerencias abierta, Esc la cierra primero. De vuelta en «Partida», lo que se usó para
  componer no cuenta como elegido: el Esc siguiente cierra el diálogo.
- **Descripción de los insumos en Componer** (AC1): cada celda «Descripción, fila N» es un `CampoConBusqueda` en celda (sin etiqueta a la vista ni botón «Borrar»; Esc con la lista cerrada no borra lo elegido) con las sugerencias de «insumos» (materiales y equipos) o «salarios_cct» (mano de obra); al elegir llena unidad y precio (con coma) y lo escrito aparte queda avisado con «Descripción propia: no viene del catálogo.». El precio es el de la lista para armar a la «Fecha» de la composición y llega en la misma respuesta (`detalle`, `para_armar_al`; AC1b); en otra moneda que la de la carpeta no se copia y la celda del precio o del sueldo lo dice como texto de ayuda («El catálogo lo tiene en USD; escriba el precio en Bs.»), también en la región viva del campo. Cada sugerencia dice «código · unidad · 18,00 Bs · lista del 01/07/2026 · material» o «sin precio en la lista para armar». La fila recuerda qué celdas llenó el catálogo: al elegir otro insumo, esas se reemplazan o se vacían y lo que escribió la persona no se pisa («El catálogo tiene 18,00 Bs; se conserva el precio que escribió.»). Si cambia la «Fecha» y con ella rige otra lista, un precio que llenó el catálogo se queda con el aviso «Precio de la lista del 01/07/2026; con la fecha 20/10/2026 rige la del 01/10/2026; revise.» (o «puede regir otra lista» si no se pudo comprobar), junto a «Fecha» se anuncia una vez cuántos precios hay que revisar y los resultados viejos no se pueden elegir. Solo cuenta como de la persona lo que tecleó (por valor: si la celda vuelve al valor que puso el catálogo, sigue siendo del catálogo). Al elegir otro insumo, lo que vino de la precarga o de MaPreX se reemplaza o se quita y se dice («Se cambió el precio 5,00 por el del catálogo, 18,00 Bs.»; «Se quitó el precio 5,00: este insumo no tiene precio en la lista.»); lo que puso el catálogo se reemplaza o se vacía sin aviso, porque la sugerencia elegida ya mostraba su precio o «sin precio en la lista para armar». En el panel de Componer, Esc no deja la fila a medias (`llenaOtrasCeldas`).
- **Origen de cada dato de la fila de insumos** (AC1, ronda 2): en Componer solo es «de la persona» lo que se tecleó en esa celda; lo que trajo la precarga de una partida guardada o «Usar esta fila» de MaPreX se reemplaza (o se quita) al elegir otro insumo del catálogo y la celda y la región viva lo dicen («Se cambió el precio 5,00 por el del catálogo, 18,00 Bs.»); el aviso de lista de otra fecha solo sale si la lista de la «Fecha» es otra y junto a «Fecha» se anuncia cuántos precios son de otra lista.
- **Origen de la descripción y la unidad de la cabecera** (D17, ronda 3): al elegir una partida del catálogo en «Código» siempre se ponen su descripción y su unidad (el servidor no deja guardar una partida existente con otra); si se reemplaza algo que la persona tecleó, o con lo que llegó la pantalla, una región viva bajo la cabecera lo dice: «Se cambió la descripción «X» por la del catálogo, «Y».» (igual para la unidad; si son ambas, unidas por un espacio). Lo vacío, lo que ya coincide y lo que puso el catálogo antes se reemplazan sin aviso. Cualquier otro cambio del código (teclear, «Usar … como código») vacía la descripción y la unidad que puso el catálogo y deja lo tecleado; si el código vuelve al elegido, se devuelven. Teclear en «Código» limpia el aviso. Vale en la pantalla y en el panel de la Hoja.
- **Descripción exacta de un insumo en Escenarios y Simulador** (AC3): «Insumo N» (precios de ensayo) es un `CampoConBusqueda` en celda y «Insumos» del Simulador una `SeleccionMultipleConBusqueda` (campo con búsqueda más etiquetas quitables, «Quitar X», Retroceso con el campo vacío quita la última, anuncio en región viva), ambos sobre `buscadorDeInsumosYOficios` (`insumos` y `salarios_cct` con `detalle`: se guarda la descripción, no la etiqueta con código). No hay «usar tal cual»: el cálculo y la simulación ignoran en silencio la descripción que no existe. En Escenarios lo escrito a mano se puede enviar y queda avisado, y la respuesta dice qué precios de ensayo no cambiaron nada (`precios_sin_insumo`, `precios_sin_cambio`); en el Simulador solo entra lo elegido y a la API va una lista (`list[str]`), así que una descripción con coma ya entra.
- **Partida, serie, unidad, moneda, versión y proveedor guiados** (AC2, AC4): «Partida» en Control (valuación y costo real) y en Reajuste sugiere solo las partidas de la versión del contrato (`GET /v1/control/partidas?corte=`, `GET /v1/reajuste/partidas`); en una valuación no se admite una fuera del contrato, salvo que la lista venga recortada (`truncada`), y en costo real sí. «Serie» sale de `GET /v1/reajuste/series`. «Unidad» (cabecera y materiales de Componer, insumo nuevo del APU) sugiere las unidades del catálogo agrupadas con el normalizador del núcleo (`GET /v1/consulta/unidades`) y admite una propia. «Moneda» de Actualizar precios y «Versión de comprobación» de Reajuste son `Select`. «Proveedor» al cotizar sugiere los de cotizaciones activas con su último uso (`GET /v1/consulta/proveedores`) y admite uno nuevo. En una celda, el campo va sin etiqueta a la vista ni botón «Borrar».

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
