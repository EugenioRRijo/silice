# Barra superior con panel explicado y recorrido funcional de todas las herramientas: diseño

**Fecha:** 2026-10-25 · **Rama:** `inc/ruta-s2-mig-adm-empresa` (árbol `.worktrees/s2madm`) · **Estado:** PROPUESTO (por aprobar por Eugenio).
**Origen:** reunión con la empresa (2026-10-25) y sesión de diseño con Eugenio el mismo día. Insumo: recorrido con Playwright
`docs/bitacora/2026-10-25-recorrido-ux-playwright.md` (commit `a1b99a90`). Maqueta elegida: opción **C** («áreas con panel explicado»).

## 1. Intención

Eugenio no quiere el menú lateral: «ese menú lateral no me parece el adecuado para guardar todas las herramientas, un top bar
es lo que busco». Eligió, entre tres maquetas, una barra superior en la que cada área abre un **panel ancho** donde cada pantalla
lleva **una línea que dice para qué sirve**, pensada para quien no conoce el programa. A la vez pidió «solo que todas las
herramientas funcionen» y que el proyecto «no parezca vibecodeado»: elecciones técnicas con razón escrita, coherencia visual y de
vocabulario, nada genérico.

Hoy el menú lateral tiene defectos visibles que dan esa impresión (recorrido y lectura del código):
- «Libro de la empresa», «Componer una partida» y «Existencias de la arenera» salen **dos veces**: `MenuLateral.tsx:93-119` pinta
  `herramientasVisibles` y después `areasVisibles`, dos listas que nadie cruza.
- «Inicio» sale dos veces seguidas (el rótulo del área y su única página) más el logo: tres caminos a lo mismo.
- A 768 px de alto el menú de quien arma queda cortado.
- La carpeta de trabajo y el proyecto abiertos son dos `Select` pequeños en la cabecera; cada pantalla arranca en `silice.db` y
  «Sin proyecto» sin que se note.

## 2. Metas, no-metas y anti-metas

**Metas**
1. M1: navegación por **barra superior** de Carbon con cinco áreas (Inicio, Auditar, Crear, Producción, Más); el menú lateral
   desaparece en el ancho normal.
2. M2: cada área (salvo las de una sola pantalla) abre un **panel de área** con sus pantallas: título y una línea de ayuda en
   lenguaje llano. Cada pantalla aparece **una sola vez** en toda la navegación.
3. M3: la **carpeta de trabajo y el proyecto** abiertos se ven siempre en la barra, a la derecha, y se cambian desde ahí.
4. M4: **todas las herramientas funcionan**: un recorrido funcional con Playwright ejecuta la acción principal de cada pantalla
   con datos ficticios y falla si alguna no hace lo que promete (§8).
5. M5: nada se retira: las 22 pantallas, los permisos por acción, el modo entrega, el tamaño de letra, el recorrido guiado y las
   rutas (`#/<id>`) siguen igual.

**No-metas:** cambiar de enrutador (sigue `HashRouter`), tema oscuro, pantallas nuevas, cambiar permisos, renombrar pantallas (el
cambio de «Libro de la empresa» a «Auditar un presupuesto» es del diseño hermano `2026-10-25-auditar-un-presupuesto-design.md`;
esta barra solo muestra el título que diga `rutas.ts`), la aplicación de escritorio (pywebview) y el autocompletado.

**Anti-metas (sería un fracaso aunque funcione):** menús que se abren al pasar el ratón; animaciones decorativas; un mega menú con
aspecto de plantilla web; perder el foco o el teclado; que la carpeta o el proyecto queden escondidos; desplazamiento horizontal a
1366 o 1056 px; duplicar la línea de ayuda en dos lugares del código.

## 3. Restricciones

- Carbon g10, IBM Plex, esquinas rectas, densidad `sm`, sin sombras ni gradientes, azul `$interactive` solo en acción/foco/selección,
  sin morado, sin movimiento decorativo (`frontend-desktop/DESIGN.md`, `PRODUCT.md`).
- `@carbon/react` 1.117.0: existen `Header`, `HeaderNavigation`, `HeaderMenu`, `HeaderMenuItem`, `HeaderGlobalBar`,
  `HeaderGlobalAction`, `HeaderPanel`, `HeaderMenuButton`, `HeaderSideNavItems`, `SkipToContent`. El submenú de `HeaderMenu` mide
  12,5 rem (`_header.scss:370`): **no sirve** para un panel ancho con ayuda.
- `.cds--header__nav` se oculta por debajo de `lg` con una media query en rem del navegador que **no sigue** el tamaño de letra de
  Sílice (`src/estilos/app.scss:15` escala la raíz a 18,67 / 23,3 / 28 px).
- Un solo h1 por página (`src/shell/titulos.test.tsx`); el foco pasa al h1 al navegar (VD-7, `Shell.tsx:104-132`).
- 1366×768 y 1056 px sin desplazamiento horizontal con las tres letras (`PRODUCT.md:32-33`; spec de bienvenida §8).
- Estimación de ancho de la barra (logo + 5 áreas + lado derecho compacto de 4 botones de 3 rem): ~840 px (Normal), ~1050
  (Grande), ~1260 (Muy grande). Con los `Select` actuales en línea no cabe ni a 1366 px.
- `core/` no se toca. Commits, TDD y arbitraje según `docs/planes/MANUAL_SUBAGENTES_MIGRACION.md` y `MANUAL_ARBITRO.md`.

## 4. Lo que decidió Eugenio

- Barra superior en vez del menú lateral (opción C de la maqueta): áreas arriba; al pulsar un área, panel ancho con cada pantalla
  y una línea de para qué sirve.
- Carpeta de trabajo, proyecto y cuenta a la derecha de la barra (estaban en las tres maquetas y no los objetó).
- Ninguna pantalla se retira.
- El orden del trabajo: arreglos del código de instalación → **esta barra** → carpetas y proyectos (BCP-5..7) → «Auditar un
  presupuesto» → autocompletado → ventana de escritorio.

## 5. Cómo se ve y cómo se usa

### 5.1 La barra

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Sílice │ Inicio   Auditar ▾   Crear ▾   Producción   Más ▾ │        Obra Demo · Torre B ▾  │  Aa  │  Ana ▾ │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- Izquierda: `HeaderName` «Sílice» (lleva a Inicio) y la `HeaderNavigation` con `aria-label="Menú principal"` (se conserva el
  nombre del punto de referencia: las pruebas y los lectores de pantalla lo usan).
- Un área con **una sola pantalla visible** para la cuenta es un enlace directo (Inicio; Producción → Existencias). Así desaparece
  el «Inicio» repetido. Si un área queda con cero pantallas visibles, no se muestra.
- Un área con **varias pantallas** es un botón con chevron que abre su panel. El área de la pantalla actual se marca como actual
  (`aria-current="page"` en la pantalla del panel; borde inferior azul de 3 px en el área, como `isCurrentPage` de Carbon).
- Derecha (`HeaderGlobalBar`):
  1. **«Carpeta y proyecto»**: un botón de texto con el nombre de la carpeta y del proyecto (truncados con puntos suspensivos a
     un ancho máximo; el nombre completo en `aria-label` y en una descripción emergente). Abre un `HeaderPanel` con los dos
     selectores actuales (`SelectorCaso`, `SelectorProyecto`) en vertical, cada uno con su rótulo. Ahí mismo pondrán BCP-5 su
     «Carpetas de trabajo…» y BCP-6 su «Nuevo proyecto». Con letra Grande o Muy grande, o por debajo de 1366 px, el botón muestra
     solo el ícono de carpeta y el texto «Carpeta y proyecto» queda en su nombre accesible. «Sin proyecto» se muestra tal cual,
     para que se note.
  2. **Tamaño de letra** (`TamanoLetra`, sin cambios) como acción global.
  3. **Cuenta**: el nombre de la persona y un menú con «Salir». («Cambiar contraseña» voluntario queda fuera de esta fase: no hay
     pantalla dentro del armazón y sería un diálogo nuevo; la API `POST /v1/sesion/contrasena` ya lo admite para cuando se haga.)
- El nombre de la carpeta se muestra **sin la extensión** `.db` (`demo`, `silice`); un nombre legible distinto del archivo queda fuera.
- Debajo de la barra no hay una segunda franja de navegación (eso era la opción B).

### 5.2 El panel de área

```
            ┌────────────────────────────────────────────────────────────┐
  Crear ▾   │ Componer una partida          Elaborar un presupuesto      │
            │ Arme el análisis de precio    Junte partidas y cantidades   │
            │ de una partida                                              │
            │ Hoja del proyecto             Catálogo de partidas e insumos│
            │ El presupuesto completo,      Partidas e insumos guardados  │
            │ como en Excel                                               │
            │ Tablero del proyecto          Entregar paquete              │
            │ Cómo va el proyecto           Prepare lo que se envía       │
            └────────────────────────────────────────────────────────────┘
```

- Componente propio `PanelDeArea` (no el submenú de `HeaderMenu`): superficie `$layer-01` sobre `$background`, borde de 1 px
  `$border-subtle`, sin sombra, esquinas rectas, alineado bajo su botón de área y recortado al ancho de la ventana. Dos columnas
  a partir de 1056 px con letra Normal; una columna en los demás casos. Ancho máximo ~40 rem.
- Cada entrada es un enlace (el título en `body-compact-01` semibold, la ayuda debajo en `helper-text-01` `$text-secondary`). La
  entrada de la pantalla actual lleva `aria-current="page"` y la barra izquierda azul de selección de Carbon.
- **«Más» agrupa por tema** con un subtítulo por grupo: *Precios* (Actualizar precios, Histórico de cambios de precio, Precios de la
  empresa, Índices del BCV, Reajuste de precios), *Obra* (Control de obra), *Análisis* (Escenarios de sensibilidad, Partidas
  similares, Simulador de listas), *Ajustes* (Administración, Acerca de Sílice). Las «huérfanas» (`areasVisibles`) siguen cayendo
  en «Más», en un grupo *Otras* que solo aparece si existe.
- **Se abre con clic o Intro/Espacio, nunca al pasar el ratón.** Un solo panel abierto a la vez. Se cierra con Esc (el foco vuelve
  al botón del área), con clic fuera, al elegir una pantalla o al abrir otra área. Teclado: al abrir, el foco va a la primera
  entrada; Tab y flechas recorren las entradas; el botón del área lleva `aria-expanded` y `aria-controls`. El patrón es un
  *disclosure* de navegación (WAI-ARIA APG «Disclosure Navigation Menu»), no un `role="menu"`: son enlaces de navegación.
- Sin animación de apertura.

### 5.3 La línea de ayuda: un solo lugar

Cada página de `PAGINAS` (`src/shell/rutas.ts:23-179`) gana el campo **`enUnaLinea: string`**: frase corta en imperativo, de
**60 caracteres como máximo** (cabe en una columna de ~20 rem del panel), sin jerga interna y con tildes. Es distinto del `queHace`
largo (hasta ~110 caracteres, tercera persona) que el diseño de bienvenida reserva para BCP-8 bajo el h1 y que espera su
validación D-9: son dos textos con dos usos, cada uno en un solo lugar, y esta fase **no espera** a D-9. Los de partida salen de
la maqueta aprobada y del `HERRAMIENTAS_PRINCIPALES.ayuda` actual (que pasa a leer `enUnaLinea`, para no duplicar); el
implementador propone los 22 y el árbitro revisa vocabulario (D1) y la prueba comprueba el tope de 60.
`AREAS` gana, para «Más», la lista de grupos (`grupos: {titulo, paginas}[]`); las demás áreas tienen un grupo implícito.
`rutas.ts` es archivo compartido: lo aplica el orquestador con el texto exacto que entregue el implementador.

### 5.4 Ancho estrecho y letra grande

Cuando la barra no cabe (umbral **por escala de letra**, con el mixin `menu-en-capa` que ya existe en `shell.scss:39-80`; los
umbrales actuales son 1536 y 1920 px para Grande y Muy grande, y para Normal 1056 px), las áreas pasan a un `HeaderMenuButton`
(«Abrir el menú») que despliega el `SideNav` en capa de Carbon con `HeaderSideNavItems`: áreas como grupos con las mismas
entradas, título y ayuda. Es el patrón de Carbon para esta situación y conserva el teclado y Esc actuales
(`Shell.tsx:134-145`). El lado derecho queda en sus tres botones de ícono. La medida de cierre es §8.2.

### 5.5 Lo que cambia de lugar

| Hoy | Con la barra |
|---|---|
| «Herramientas principales» arriba del menú lateral (`MenuLateral.tsx:93-105`) | Desaparece de la navegación (era el duplicado). Las tres herramientas se muestran como **tres mosaicos** en el Inicio (`herramientasVisibles` se conserva) |
| Panel del recorrido guiado dentro del SideNav (`MenuLateral.tsx:120-124`) | **Columna acoplada a la derecha** del contenido (no una capa encima): mientras haya un recorrido activo, el `main` se estrecha 16 rem y la columna «Recorrido» queda visible junto a la pantalla, como hoy junto al menú. No se cierra con clic fuera ni al abrir un panel de área o el de carpeta (no cuenta para «un solo panel abierto»). Se pliega con su botón «Ocultar» (queda un botón «Recorrido» en la barra para reabrirla) y termina con «Terminar recorrido». Por debajo del umbral de §5.4, la columna pasa a una franja plegable bajo la barra. Los recorridos visuales de §8.2 se miden con y sin recorrido activo |
| Nombre de la persona al pie del menú en capa con letra grande | Menú de la cuenta en la barra; en capa, al pie del SideNav como hoy |
| «Caso» en `SelectorCaso`, en el aviso «Ahora trabaja con el caso…» y demás cadenas visibles del armazón | **«Carpeta de trabajo»** (término D-1 del diseño de bienvenida, palabra de Eugenio). Esta fase adelanta el renombrado **solo en las cadenas del armazón** que toca (selectores, avisos, barra); el resto de pantallas sigue en BCP-9. La API y el código conservan `caso` |
| `DESIGN.md:73-76` (SideNav de 16 rem, cabecera de 48 px) | Se reescribe: barra superior, panel de área, umbrales por escala, cabecera de 3 rem |

Los cambios del **Inicio** (un solo botón «Auditar un presupuesto», enlace al recorrido guiado, mosaicos de las tres herramientas
principales) y los textos de `RECORRIDO_AUDITAR` **no van en esta fase**: van en AP-6 del diseño hermano, cuando la pantalla ya se
llame «Auditar un presupuesto». En esta fase el Inicio no cambia, salvo que las tres herramientas principales, al salir de la
navegación, ya se muestran como mosaicos en el Inicio (para no perderlas).

## 6. Arquitectura del cambio (front)

- Archivos nuevos: `src/shell/BarraSuperior.tsx` (sustituye a `Cabecera.tsx` + `MenuLateral.tsx` en ancho normal),
  `src/shell/PanelDeArea.tsx`, `src/shell/PanelCarpetaProyecto.tsx`, `src/shell/MenuCuenta.tsx`, `src/shell/PanelRecorrido` se mueve
  a un `HeaderPanel`; lógica pura en `src/shell/navegacion.ts` (qué áreas son enlace y cuáles panel, grupos de «Más», pantalla
  actual) con su prueba. `MenuLateral.tsx` queda solo para la capa estrecha (o se reemplaza por `HeaderSideNavItems`; lo decide el
  implementador con la prueba de teclado de §8.1).
- `Shell.tsx`: cambia el montaje de cabecera y menú; conserva enrutado, foco al h1, `document.title`, Esc, avisos y recorrido.
- `rutas.ts` (compartido, orquestador): `queHace` en las 22 páginas y `grupos` en «Más». Se conservan `visible`, `areasVisibles`,
  `herramientasVisibles` (las pruebas de `rutas.test.ts` siguen valiendo).
- Sin dependencias nuevas.

## 7. Orden respecto de BCP-5..7 y del diseño hermano

Esta barra va **antes** de BCP-5: reescribe `Cabecera.tsx`, `Shell.tsx`, `MenuLateral.tsx`, `shell.scss` y el lugar de los
selectores, que BCP-5 y BCP-6 tocan. Con la barra hecha, BCP-5 pone «Carpetas de trabajo…» y BCP-6 «Nuevo proyecto» dentro de
`PanelCarpetaProyecto`; el `Toggletip` «?» de §7.2 del diseño de bienvenida va junto al título del panel. El renombrado de
«Libro de la empresa» lo hace el diseño hermano y la barra lo refleja sola.

## 8. Pruebas y criterio de aceptación

### 8.1 Unitarias (Vitest + Testing Library, rojo visto)

- `navegacion.ts`: con las acciones de ana, rita y admin y en modo entrega, qué áreas salen, cuáles son enlace directo, cuáles
  panel, y que **ninguna pantalla aparece dos veces** en toda la navegación (oráculo: conjuntos escritos a mano a partir de
  `PAGINAS` y los permisos de `tests/fixtures/sesion_web.py`).
- `BarraSuperior`: abrir un área con clic y con teclado; Esc cierra y devuelve el foco; clic fuera cierra; un solo panel abierto;
  `aria-expanded`/`aria-controls`/`aria-current`; elegir una pantalla navega y lleva el foco al h1; el área actual marcada.
- `PanelCarpetaProyecto`: muestra los nombres, cambia carpeta y proyecto con el flujo actual; «Sin proyecto» visible.
- Recorrido: el panel «Recorrido» se abre al empezar, persiste al navegar, Esc lo cierra sin terminarlo.
- Las ~23 pruebas que dependen del menú lateral (`Shell.test.tsx`, `App.test.tsx`, `Selectores.test.tsx`, `sinClasica.test.ts`) se
  reescriben contra la barra; ninguna se borra sin su equivalente.

### 8.2 Recorrido visual (Playwright, `scripts/recorrido_ux_playwright.py`)

Las 22 rutas × ana/rita/admin × 1366 y 1056 px × Normal/Grande/Muy grande: un h1, `scrollWidth <= clientWidth`, cero errores de
consola y red, axe sin violaciones nuevas, y además: ninguna entrada duplicada en la navegación, la barra no se corta, el panel de
área no se sale de la ventana.

### 8.3 Recorrido funcional: «que todas las herramientas funcionen» (M4)

**Alcance y compuerta.** El recorrido funcional es una entrega **propia** (rebanada BS-F), no una compuerta de la barra: la barra
se cierra con §8.1, §8.2 y §8.4. BS-F se construye en paralelo y su primera corrida produce la **lista de defectos** de las 22
pantallas, que se le muestra a Eugenio. Cada defecto se registra en `docs/bitacora/2026-10-2x-recorrido-funcional.md` con su dueño:
si es del armazón, se corrige en esta fase; si es de otra pantalla, se abre su arreglo (TDD, árbitro) como trabajo propio en el
orden de §4; si toca `core/`, se anota como bloqueo para el tutor y no se toca. Se permite sembrar **más datos ficticios** para
poder ejecutar cada acción: una clave de firma de prueba creada por el administrador ficticio, un paquete `.silice` generado en la
misma corrida por «Entregar» y consumido por «Revisar un paquete», y archivos de entrada ficticios para Índices del BCV y Actualizar
precios (de `tests/fixtures/**`). Las acciones que solo se permiten desde el propio equipo se corren con el servidor en
`127.0.0.1`, como ya hace el script.

El script gana un modo `--funcional` que, con la carpeta temporal sembrada con la demostración ficticia, ejecuta la **acción
principal** de cada pantalla con la cuenta que la puede usar y comprueba el **resultado visible** (no solo que la pantalla
cargue). La lista de acciones y su comprobación vive en un archivo de datos junto al script (una fila por pantalla: ruta, cuenta,
pasos, qué debe verse). Ejemplos: Componer → crear una partida nueva con código nuevo y guardarla → aparece en el catálogo;
Libro de la empresa / Auditar → subir el libro ficticio → aparece el informe; Hoja → guardar una versión → aparece en el
historial; Existencias → registrar un movimiento → cambia el saldo; Administración → crear una cuenta ficticia → aparece en la
lista; Entregar → generar el paquete → se descarga un archivo con su huella. El implementador completa las 22 filas leyendo cada
pantalla. **Una pantalla cuya acción principal falle es un defecto que se registra en la bitácora y se corrige**, no se omite. El
modo funcional corre al cerrar cada fase del orden de §4.

### 8.4 Cierre

`npm run lint`, `npm run build`, `npx vitest run` de lo tocado, los dos recorridos, `DESIGN.md` actualizado, línea de
`CHANGELOG.md`, árbitro con los criterios D1/D2 y revisor de diseño (`.claude/agents/silice-rev-diseno.md`).

## 9. Lo que queda al constructor

- Los 22 textos de `queHace` (con revisión del árbitro).
- Si la capa estrecha reutiliza `MenuLateral.tsx` o pasa a `HeaderSideNavItems`.
- La medida exacta del ancho máximo de los nombres truncados de carpeta y proyecto, siempre que §8.2 pase.
- El ícono de Carbon de cada acción global (de `@carbon/icons-react`, ya instalado).

## 10. Decisiones de ingeniería tomadas aquí (las ratifica Eugenio al leer)

1. Panel de área propio en vez del submenú de `HeaderMenu`: el de Carbon mide 12,5 rem y no admite la línea de ayuda.
2. Patrón *disclosure* de navegación (enlaces), no `role="menu"`: es lo que recomienda WAI-ARIA para menús de sitio.
3. Áreas de una sola pantalla como enlace directo (quita el «Inicio» repetido y un clic en Producción).
4. Carpeta y proyecto juntos en un panel, no dos `Select` en línea: en línea no caben ni a 1366 px.
5. Las herramientas principales salen de la navegación y pasan a mosaicos del Inicio (eran el duplicado).
6. «Más» agrupado en Precios, Obra, Análisis y Ajustes.
7. Línea corta del panel (`enUnaLinea`, ≤ 60) separada del texto largo de BCP-8 (`queHace`); cada una en un solo lugar.
8. Recorrido funcional como entrega propia (BS-F) que produce la lista de defectos; no bloquea la barra.
9. Recorrido guiado como columna acoplada que empuja el contenido, no como capa.
10. «Carpeta de trabajo» en las cadenas del armazón ya en esta fase (D-1 adelantado solo ahí).
11. Sin «Cambiar contraseña» voluntario en esta fase.
12. Cambios del Inicio y de `RECORRIDO_AUDITAR` en AP-6 del diseño hermano.
