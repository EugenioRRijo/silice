# Auditoría de la interfaz con la lista de señales de unslop (2026-11-17)

- **Fecha:** 2026-11-17
- **Rama y commit auditados:** `feature/mejoras-ola2`, `8edeb9ae` (`git -C .worktrees/s2m4 rev-parse --short HEAD`)
- **Código:** `.worktrees/s2m4/frontend-desktop/src`: 60 hojas SCSS y 400 archivos TS/TSX sin pruebas
- **Método:** auditoría por código, en solo lectura. Se usó la skill `unslop-interfaz` (su apartado «Uso en Silice» manda) con `references/signs.md` y `references/tokens.md`. Se buscó con grep y con guiones de Python de solo lectura sobre estilos, tokens, componentes y textos visibles (cadenas y texto JSX, sin comentarios). Cada hallazgo se cotejó con `frontend-desktop/DESIGN.md`: lo que DESIGN.md decide no se cuenta como hallazgo y se anota como «conforme a DESIGN.md».
- **Límite:** no se abrió el navegador. No se midieron contrastes ni alturas en pantalla, y no se vieron los textos que llegan de la API (`detalle`). Lo que solo se nota renderizado (densidad real, alineación de columnas, saltos de línea) queda para una pasada en el navegador.
- **Pantallas recorridas:** el marco (`src/marco`, `src/shell`), la bienvenida (`src/bienvenida`), la Vista general (`src/paginas/inicio`), el Presupuesto u Hoja (`src/paginas/hoja`), Componer (`src/paginas/componer`), Control (`src/paginas/control`), Auditoría (`src/paginas/auditoria`, `src/visor`), Precios (`precios_empresa`, `catalogo`, `indices`, `simulador`) y la Cuenta (`administracion`, `acerca`, `marco/EspacioDeCuenta.tsx`). También las piezas comunes (`src/comun`, `src/indicadores`, `src/severidad`, `src/estilos`) y, de paso, Archivos y planos, Mercado, Reajuste y Producción.

## Hallazgos

Las rutas son relativas a `frontend-desktop/src/`.

| # | Pantalla y archivo:línea | Señal | Evidencia | Pasada que lo corregiría y valor propuesto | Gravedad |
|---|---|---|---|---|---|
| 1 | Marco, barra lateral: `marco/BarraLateral.scss:28-29`, que se aplica a `marco/BarraLateral.tsx:144` («Obras») y `marco/ZonaDeCostos.tsx:34` («Costos y producción») | Etiqueta en MAYÚSCULAS con espaciado amplio | `text-transform: uppercase; letter-spacing: 0.32px;` en `.silice-marco-lateral__titulo`. DESIGN.md («Texto») prohíbe los «rótulos en mayúsculas espaciadas sobre cada sección». Es la primera señal que se ve en cada pantalla. | Pasada 5 (tipo): mayúscula inicial («Obras», «Costos y producción»), `letter-spacing: 0`, `label-01` en `--cds-text-secondary`; se conserva el relleno de 16 arriba y 8 abajo | alta |
| 2 | Archivos y planos, Cargar cómputo: `paginas/archivos/logicaComputo.ts:37-39` | Jerga técnica visible | «El catálogo no tiene partidas del **dominio** civil todavía (o **la base de datos** no se pudo leer; revise el mensaje de error de arriba, si lo hay): cargue primero un presupuesto civil (por ejemplo, **sembrando la línea base** en la **página** de Actualización)…». Usa jerga del programador y la palabra «página», que DESIGN.md no admite. | Pasada 4 (texto): «El catálogo aún no tiene partidas de obra civil. Cargue primero un presupuesto civil en Precios y catálogo.» Si hubo un error de lectura, se dice aparte con su `detalle` | alta |
| 3 | Archivos y planos: `paginas/archivos/logicaComputo.ts:141` y `:160` | Jerga técnica y código HTTP en un mensaje | «La API respondió con el estado ${estado}.» y «No se pudo hablar con el servidor de Sílice. Compruebe que la API esté encendida.» | Pasada 4: «No se pudo calcular. Intente de nuevo; si sigue fallando, cierre Sílice y ábralo otra vez.» y «Sílice no responde. Cierre Sílice y ábralo otra vez.» | media |
| 4 | Archivos y planos: `paginas/archivos/computo.scss:48` con `paginas/archivos/BloquesDelComputo.tsx:89` | Significado dado solo por el color (contra DESIGN.md) | Este aviso solo se distingue por una raya de 3 px en `--silice-sev-advertencia` (yellow-30), sin ícono. DESIGN.md dice que el amarillo no llega a 3:1 y que su identificación «la da el ícono… nunca el borde solo». | Pasada 2 (color): patrón de aviso de DESIGN.md, es decir `--silice-aviso-fondo`, raya de 4 px en `--silice-aviso-borde` (yellow-50) e ícono `WarningAltFilled` con la palabra «Aviso» | media |
| 5 | Hoja, Archivos, Control, Cuenta y Mercado: `paginas/hoja/hoja.scss:384, 433, 461`, `paginas/archivos/archivos.scss:22`, `paginas/control/control.scss:124`, `paginas/administracion/administracion.scss:78`, `paginas/mercado/mercado.scss:176` | Más de un acento en la interfaz cromática: raya lateral de color decorativa | 8 diálogos y bloques llevan `border-inline-start: 4px solid var(--silice-interactivo)`, que es el azul de Carbon (`--cds-interactive`, blue-60). DESIGN.md asigna la acción a `--silice-complementario` y reserva el azul para el foco y para la severidad INFO. Resultado: un tercer color de acción junto al complementario y al ámbar de la marca, que además puede leerse como INFO. | Pasada 2: quitar la raya (basta el borde de 1 px `--cds-border-subtle`) o pasarla a `--silice-complementario`. El foco sigue en `$focus` | media |
| 6 | Cuenta, Ayuda y acerca de Sílice: `paginas/acerca/index.tsx:93-94` | Palabra prohibida por DESIGN.md | Encabezado h3 y `aria-label` «Módulos». DESIGN.md («Marco»): «En los textos no se dice «módulo» ni «área»». La guardia `sinJergaInterna.test.ts` no lo atrapa porque solo vigila `marco/` y el armazón. | Pasada 4: «Componentes instalados» o «Especialidades instaladas» | media |
| 7 | Cuenta, Ayuda y acerca de Sílice: `paginas/acerca/index.tsx:100` | Píldora de color con verde «por ser positivo» | `<Tag size="sm" type={m.instalado ? "green" : "gray"}>`. DESIGN.md prohíbe el «verde por ser positivo» y no cuenta esta píldora entre las dos excepciones a las esquinas rectas. | Pasada 7 (detalles): texto llano «Instalado» o «No instalado» en la tinta secundaria, sin `Tag` | media |
| 8 | Reajuste: `paginas/reajuste/index.tsx:496` | Id interno como etiqueta visible | Opción del `Select` «Reemplaza al estudio parcial»: `` `${p.id} (calculado el …)` ``, es decir «12 (calculado el 01/10/2026)». La persona elige un número de base de datos. | Pasada 4: «Estudio parcial del 01/10/2026» (y la fuente o el responsable si hay dos del mismo día) | media |
| 9 | Mercado y Producción: `paginas/mercado/Observaciones.tsx:43, 92, 136`, `paginas/produccion/CalculosAnteriores.tsx:71`, `paginas/produccion/logicaPlanta.ts:141`, `paginas/vial/TramoConCantidades.tsx:39` | Ids internos en mensajes | «Observación n.º ${o.id} anulada…», «Abrir el cálculo n.º ${c.id}», «Cantidades del tramo ${tramo.id}». Si el número no se ve en la tabla, la persona no sabe a qué se refiere. | Pasada 4: nombrar por lo que la persona ve (fuente y fecha, período o nombre del tramo); el id solo si es una columna visible | baja |
| 10 | Cuenta, Especialidades, IA e instalación: `paginas/administracion/Asistente.tsx:181`, `paginas/administracion/ClavesApi.tsx:98` | Jerga técnica e inglés visible | «El nombre exacto de un modelo ya instalado en Ollama (el que muestra «ollama list»)…» y «Para qué es esta clave (por ejemplo, el plugin que la usa)». Es una pantalla de quien administra, pero la regla del español llano vale igual. | Pasada 4: «El nombre del modelo tal como aparece en Ollama» y «Para qué es esta clave (por ejemplo, el programa que la usa)» | baja |
| 11 | Hoja: `paginas/hoja/TablaEditable.tsx:58` | Jerga técnica | `title="Aún no se evalúa: se evalúa al aceptar el servidor la edición."`: habla del servidor y además lleva punto final en un título | Pasada 4: «Se revisa al aceptar el cambio» | baja |
| 12 | Bienvenida: `bienvenida/Bienvenida.tsx:26` y `:64` | Titular de saludo y voz en primera persona | El h1 dice «Bienvenida a Sílice». La nota dice «No encuentro el archivo.»: el programa habla como persona, y el resto de la app usa la tercera persona («Sílice dejó un código…»). No tiene exclamación ni emoji. | Pasada 4: h1 «Primera cuenta de Sílice» o «Crear la cuenta del administrador»; nota «Sílice no encuentra el archivo.» | baja |
| 13 | Bienvenida: `bienvenida/Bienvenida.tsx:54` y `:48` | Jerga técnica visible | `npm run dev` y la ruta `%LOCALAPPDATA%\Silice\datos\codigo_instalacion.txt`. El primero sale solo en modo desarrollo; la ruta es necesaria. | Ninguna para la ruta, que es necesaria. Para `npm run dev`, aceptable porque solo lo ve quien desarrolla | baja |
| 14 | Cuenta, Componer y Reajuste: `paginas/administracion/Cuentas.tsx:332, 334`, `paginas/componer/AvisoSinLista.tsx:54`, `paginas/componer/Guardar.tsx:97`, `paginas/componer/PanelDesglose.tsx:107`, `paginas/reajuste/index.tsx:482` | Títulos genéricos de notificación | 6 notificaciones titulan «Aviso», «Hecho» o «Listo» y dejan el contenido en el subtítulo. El título no dice qué pasó. | Pasada 4: el título nombra el hecho («Contraseña cambiada», «Lista para armar creada») o se omite y queda el texto | baja |
| 15 | Varias: 6 `titulo=` y 5 `title=` con punto final, por ejemplo `paginas/aprobar/index.tsx:125`, `paginas/entregar/index.tsx:76, 169, 176`, `paginas/administracion/index.tsx:92`, `paginas/reajuste/index.tsx:155, 181`, `paginas/control/PestanaLineaBase.tsx:145`, `paginas/administracion/ClavesApi.tsx:110`, `paginas/administracion/Instalacion.tsx:145` | Punto final en títulos; formato desigual | 11 de unos 257 títulos de aviso o estado vacío terminan en punto; los 246 restantes no | Pasada 4: sin punto final en el título; si hace falta una frase, va en `descripcion` o `subtitle` | baja |
| 16 | Varias: 21 cadenas con «...» (por ejemplo `paginas/actualizacion/index.tsx:292`, `paginas/archivos/CargarComputo.tsx:199, 233`, `paginas/auditoria/AuditarApuPorHoja.tsx:300, 480`, `paginas/indices/EnUsd.tsx:106, 136, 175`) frente a 63 con «…» | Dos formatos en un mismo tipo de texto | Cargas como «Guardando...» usan tres puntos; botones y campos usan el carácter «…» | Pasada 4: «…» (U+2026) en todos | baja |
| 17 | Diálogo de carpetas: `shell/carpetas/MarcoDeDialogo.scss:57` | Degradado (contra DESIGN.md) | `linear-gradient(to bottom, transparent, var(--cds-layer-accent-01))` como indicio de «hay más abajo». Es un paso de tono dentro de un solo neutro, que unslop admite, pero DESIGN.md dice «Sin gradientes». | Pasada 2: dejar solo el `border-block-end: 2px solid var(--cds-border-strong-01)`, que ya está, o pedir a Eugenio que anote la excepción en DESIGN.md | baja |
| 18 | Hoja: `paginas/hoja/hoja.scss:312` | Texto atenuado con opacidad | `.silice-hoja__sin-evaluar { opacity: 0.6 }`. Sobre el gris 10 de la capa, la tinta primaria al 60 % queda cerca del límite de 4,5:1 (sin medir en el navegador). | Pasada 2: `color: var(--cds-text-secondary)` en lugar de la opacidad | baja |
| 19 | Hoja y Cuenta: `paginas/hoja/hoja.scss:410`, `paginas/administracion/administracion.scss:82` | Color de severidad fuera de su semántica | Los diálogos de peligro usan `--silice-sev-critico` (el rojo de los halos) como raya. DESIGN.md: «dos semánticas que no se mezclan». | Pasada 2: el botón `danger` de Carbon basta para marcar el peligro; raya neutra o ninguna | baja |
| 20 | Marco, barra lateral: `marco/BarraLateral.scss:91-92` frente a `:100-103` | Estados de fila que se confunden | El hover y la fila activa comparten el mismo fondo (`--silice-lateral-activo`). La activa se distingue solo por la raya de 3 px y el peso 600, que además cambia el ancho del texto. | Pasada 7: hover con `--cds-layer-hover` (o el lateral 5 % más oscuro), sin cambio de peso en la activa (la raya y el fondo bastan) | baja |
| 21 | Vista general: `paginas/inicio/inicio.scss:55, 80, 85` | Jerarquía por peso, no por tamaño y color | En «Lo que requiere atención» van tres pesos 600 por fila (resumen, urgencia y obra), así que nada destaca | Pasada 5: 600 solo en la urgencia; la obra en 400 con la tinta primaria y la carpeta en la secundaria | baja |
| 22 | Gráficos (Control, Tablero, Riesgo): `comun/paletaGraficos.ts:5, 31` | Verde fuera de la variación IBCS | La tercera serie «real» y el quinto grupo toman `#198038` (green-60). DESIGN.md reserva el verde para Δ favorable y para «verificado». | Pasada 2: sustituir el verde por un gris más del ramp (`#6f6f6f`) o por un achurado | baja |
| 23 | Espaciado suelto: `comun/CampoConBusqueda.scss:67` (×2), `shell/carpetas/GestionCarpetas.scss:62`, `marco/BarraDeEspacio.scss:71, 100, 101`, `comun/Pildora.scss:14`, `indicadores/indicadores.scss:202` | Valores fuera de la escala de 4 px | Hay 0,375 rem (6 px), 0,625 rem (10 px) y 0,4375 rem (7 px, que centra la barra del plan). Todos son rellenos dentro de controles pequeños, que unslop tolera en pasos de 2 px. | Pasada 1: 0,25 o 0,5 rem en las pestañas y opciones; el 0,4375 rem del centrado se queda | baja |
| 24 | Cambiar contraseña: `sesion/CambiarContrasena.tsx:40` | Tamaño de título desigual | Es el único h1 en `heading-03`; los otros 43 usan `heading-04` | Pasada 5: `cds--type-heading-04` | baja |
| 25 | Auditoría, filtro de hallazgos: `visor/ListaHallazgos.tsx:250` | Píldora no listada en DESIGN.md | `SelectableTag` de Carbon, que trae `border-radius: 1rem` en `@carbon/styles` 1.116. Es la gramática nativa de Carbon, pero DESIGN.md solo exceptúa los contadores laterales y el círculo de iniciales. | Ninguna mientras se decide: o se anota la excepción en DESIGN.md o se pone `border-radius: 0`. Para Eugenio | baja |

### Conforme a DESIGN.md (no son hallazgos)

- **Rayas laterales de aviso de 4 px** en amarillo (`FranjaDelPaso.scss:17`, `indicadores.scss:156`, `MarcaDemostracion.scss:20`, `bienvenida.scss:36`) y **raya de 3 px de la fila activa**: son el patrón de aviso y de selección que fija DESIGN.md.
- **Contornos de los halos** (`visor/visor.scss:307, 311`, `box-shadow: inset`): es el segundo contorno oscuro del amarillo que pide DESIGN.md, no un brillo.
- **Radios:** 3 declaraciones en total, todas excepciones de DESIGN.md: `Pildora.scss:15`, el círculo de `MenuCuenta.scss:30` y `indicadores.scss:227` (radio 0).
- **Placeholder del buscador** «Buscar una obra, sección o pantalla…» (`marco/Buscador.tsx:113`): lo fija DESIGN.md.
- **Registro de tuteo:** «Te falta:» (`comun/FranjaDelPaso.tsx:25`) y «Empieza aquí» (`comun/ayuda/AyudaDeSilice.tsx:16, 60`) van en tú, mientras el resto de la app trata de usted («Su cuenta», «Cree», «Suelte»). Están fijados en DESIGN.md, así que no se cuentan; se anota la mezcla de registro para que Eugenio la confirme.
- **Botón principal «Nueva obra» en la barra lateral**, siempre a la vista: lo fija DESIGN.md («Marco»).
- **Morado** solo en `--silice-atipico` (`estilos/tokens.scss:52`), y los colores semánticos de severidad e IBCS vienen todos de tokens de Carbon.

## Conteos globales (grep sobre `src`, sin pruebas)

| Señal | Cuenta |
|---|---|
| Degradados (`gradient(`) | 1 en 1 archivo (`MarcoDeDialogo.scss:57`, tono neutro) |
| Texto con degradado (`background-clip: text`) | 0 |
| Brillos o sombras de color (`box-shadow` / `drop-shadow` / `text-shadow` / `filter`) | 0 decorativas (2 `box-shadow: inset` funcionales en `visor.scss`) |
| `backdrop-filter` / `blur(` (vidrio) | 0 |
| Emojis como íconos o en etiquetas | 0 (las flechas ↑ ↓ → aparecen en comentarios y en un ejemplo, «Cemento Portland → 18,50») |
| Signos de exclamación en textos visibles («¡» o «!» al final) | 0 |
| Palabras infladas (potente, revolucionario, mágico, increíble, sin esfuerzo, impulsado por IA, inteligente, la mejor) | 0 |
| Insignias «Nuevo», «Beta», «PRO» | 0 |
| Etiquetas en MAYÚSCULAS con espaciado | 1 regla (`BarraLateral.scss:28`) que se aplica a 2 títulos |
| `transition: all` / `transition-all` | 0 (la única `transition` es `none`, en `prefers-reduced-motion`) |
| Animaciones en bucle (`@keyframes`, pulse, ping, shimmer) | 0 |
| Escalas en hover (`scale(`) | 0 |
| Valores de espaciado fuera de la escala de 4 px | 8 en 6 archivos (todos de 6, 7 o 10 px dentro de controles) |
| Declaraciones de `border-radius` | 3, todas conformes; además 2 `Tag` de Carbon con forma de píldora |
| Pesos 700-900 | 0. Peso 600: 29 declaraciones en 17 archivos. Fuentes cargadas: 300, 400, 600 |
| Hex escritos a mano | 0 fuera de `var(…, #fallback)` (16 respaldos en 6 archivos) y la paleta de gráficos (`paletaGraficos.ts`, 6 colores) |
| Acento azul de Carbon como raya decorativa | 8 rayas en 5 archivos |
| `tabular-nums` | 19 declaraciones en 14 archivos, más la clase global `.silice-cifra` (`estilos/app.scss:33`) |
| Formato inglés de cifras (`toLocaleString`, `Intl.NumberFormat`, `en-US`) | 0. 2 `toFixed`, los dos pasados por `formatoEsVe` (`archivos/logicaComputo.ts:92`, `componer/Similares.tsx:16`) |
| Celdas numéricas sin clase de cifra | 0 encontradas por patrón |
| Ids internos en textos visibles | 7 lugares en 6 archivos |
| Títulos con punto final | 11 de unos 257 |
| «...» frente a «…» | 21 frente a 63 |
| Rayas (—) como adorno | 0 (las rayas que hay son valores vacíos o rangos) |
| Íconos | un solo juego (`@carbon/icons-react`, 36 importaciones); tamaños: 33 de 16 px, 2 de 20 px, 1 de 12 px (en el halo) |

## Veredicto por pantalla

| Pantalla | Veredicto | Por qué |
|---|---|---|
| Marco (barra superior, barra lateral, barra de espacio, buscador) | pulido ligero | Rótulos en mayúsculas espaciadas (#1), hover igual al activo (#20) y pasos de 6 y 10 px en las pestañas (#23). Lo demás es Carbon plano, con un solo acento de marca. |
| Bienvenida | pulido ligero | Título de saludo y voz en primera persona (#12), jerga solo en modo desarrollo (#13). Sin exclamaciones ni adornos. |
| Vista general | pulido ligero | Jerarquía por peso en «Lo que requiere atención» (#21). Cifras en es-VE, Bs y USD por separado, sin tarjetas con sombra. |
| Presupuesto (Hoja) | pulido ligero | Rayas azules en los diálogos (#5), rojo de severidad en el diálogo de peligro (#19), opacidad como atenuado (#18) y «servidor» en un título (#11). |
| Componer | sin señales | Solo títulos genéricos «Aviso» o «Listo» (#14). |
| Control | pulido ligero | Raya azul en el diálogo de procura (#5); verde en la tercera serie de los gráficos (#22). |
| Auditoría (visor y lista de hallazgos) | sin señales | Severidad con ícono y palabra, halos conformes. Solo la píldora del filtro está por decidir (#25). |
| Precios (empresa, catálogo, índices, simulador) | sin señales | No se encontró ninguna señal. |
| Cuenta | pulido ligero | «Módulos» (#6), píldora verde (#7), jerga de Ollama y «plugin» (#10), títulos genéricos (#14) y rayas azules (#5). |
| Archivos y planos (de paso) | pulido ligero, el más cargado | Jerga de programador y «página» (#2, #3) y aviso amarillo sin ícono (#4). |
| Piezas comunes y tokens | sin señales | Tokens solo de Carbon, sin hex a mano, sin movimiento, `prefers-reduced-motion` global. |

## Veredicto general

Sílice no está vibecodeada. Faltan casi todas las señales fuertes de unslop: degradados de color, texto con degradado, brillos, emojis, exclamaciones, palabras infladas, insignias, animaciones en bucle, `transition: all` y pesos de 700 a 900. Tampoco hay cifras en formato inglés. Lo que queda es pulido ligero en dos frentes. El primero es el color: las rayas azules de Carbon en los diálogos meten un tercer acento junto al complementario y al ámbar. El segundo es el texto: algo de jerga de programador en Archivos y planos y en la Cuenta, ids internos y títulos genéricos. La única señal que se nota a primera vista en todas las pantallas son los rótulos en mayúsculas espaciadas de la barra lateral, que además contradicen DESIGN.md. Según el paso 3 de unslop toca el modo pulido: corregir solo lo listado, sin cambiar paleta, tipografía ni disposición.

---

Lista de señales de unslop, de Damir Sokolovsky, CC BY 4.0.
