# Barra superior con panel explicado: plan de construcción

> **Para agentes:** SUB-SKILL OBLIGATORIA: superpowers:subagent-driven-development (implementador → árbitro por tarea, como
> manda `docs/planes/MANUAL_SUBAGENTES_MIGRACION.md` y `docs/planes/MANUAL_ARBITRO.md`). Los pasos usan casillas (`- [ ]`).

**Meta:** reemplazar el menú lateral de Sílice por una barra superior de Carbon con cinco áreas, un panel explicado por área,
carpeta de trabajo y proyecto siempre a la vista, y un recorrido con Playwright que pruebe que todas las herramientas funcionan.

**Arquitectura:** la lógica de qué se muestra vive en un módulo puro (`src/shell/navegacion.ts`) sobre los datos de
`src/shell/rutas.ts`; los componentes (`BarraSuperior`, `PanelDeArea`, `PanelCarpetaProyecto`, `MenuCuenta`, `MenuEnCapa`,
`ColumnaRecorrido`) solo la pintan. `Shell.tsx` cambia el montaje y conserva enrutado, foco al h1, avisos y recorrido.

**Tecnología:** React 19, TypeScript, `@carbon/react` 1.117.0 (`Header`, `HeaderNavigation`, `HeaderGlobalBar`,
`HeaderGlobalAction`, `HeaderPanel`, `HeaderMenuButton`, `SideNav`, `HeaderSideNavItems`), `react-router` 7 (HashRouter), Vitest +
Testing Library; Playwright para Python (`uv run --active --with playwright`).

**Diseño:** `docs/especificaciones/2026-10-25-barra-superior-design.md` (APROBADO por Eugenio, 2026-10-25). El ejecutor lee
el diseño y este plan.

## Restricciones globales

- Árbol único `.worktrees/s2madm`, rama `inc/ruta-s2-mig-adm-empresa`; sin `git worktree add`, sin `.venv` nuevo, sin
  `npm install`, sin cambiar `package.json`; `uv run --active` siempre.
- Archivos compartidos que solo aplica el orquestador: `src/shell/rutas.ts` y `rutas.test.ts`, `CHANGELOG.md`, `docs/ERS.md`.
- Carbon g10, IBM Plex, esquinas rectas, densidad `sm`, sin sombras ni gradientes, azul `$interactive` solo en acción, foco y
  selección, **sin morado**, **sin animación** (tampoco al abrir paneles).
- 1366×768 y 1056 px sin desplazamiento horizontal con letra Normal, Grande y Muy grande.
- Un solo h1 por página; el foco pasa al h1 al navegar (VD-7).
- Paneles: se abren con clic o Intro/Espacio, **nunca al pasar el ratón**; patrón *disclosure* de navegación (enlaces), no
  `role="menu"`.
- `aria-label="Menú principal"` en la navegación (se conserva el nombre del punto de referencia).
- Texto visible en español con tildes, sin jerga interna (UC-xx, RF-xx); «carpeta de trabajo» en lugar de «caso» en las cadenas
  del armazón; la API y el código conservan `caso`.
- `enUnaLinea`: imperativo, **1 a 60 caracteres**.
- TDD con rojo visto; prueba y su implementación en commits separados; asunto sin tildes; termina en
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` (o el modelo del implementador).
- `core/` intacto.

## Foco de revisión

Lo que el diseño implica y ninguna prueba ejercitaría por sí sola; cada línea tiene su prueba en la tarea indicada:

1. Nombre de carpeta o proyecto muy largo (80 caracteres) → se recorta con puntos suspensivos, la barra no se desborda, el nombre
   completo está en el nombre accesible (Tarea 4).
2. Atrás/adelante del navegador con un panel de área abierto → el panel se cierra y el área actual se actualiza (Tarea 3).
3. Cambiar el tamaño de letra con un panel abierto → el panel se cierra (no queda flotando fuera de la barra) (Tarea 3).
4. Recorrido activo + panel de área abierto + Esc → Esc cierra solo el panel; el recorrido sigue (Tarea 6).
5. Cuenta sin ninguna página visible o en modo entrega → la barra no muestra áreas vacías y no falla (Tarea 2).

---

### Tarea 1: Datos de navegación en `rutas.ts` (orquestador)

**Archivos:**
- Modificar: `frontend-desktop/src/shell/rutas.ts` (`PaginaDef`, `PAGINAS`, `AreaDef`, `AREAS`, `HERRAMIENTAS_PRINCIPALES`,
  `herramientasVisibles`)
- Prueba: `frontend-desktop/src/shell/rutas.test.ts`

**Interfaces:**
- Produce: `PaginaDef.enUnaLinea: string`; `interface GrupoDef { titulo: string; paginas: readonly string[] }`;
  `AreaDef.grupos?: readonly GrupoDef[]` (solo en «mas»); `HerramientaPrincipal` pasa a `{ pagina: string }` y
  `HerramientaVisible` a `{ pagina: string; titulo: string; ayuda: string }` con `ayuda` = `enUnaLinea` de su página.

- [ ] **Paso 1: pruebas en rojo** en `rutas.test.ts`:
  - `test("cada pagina tiene una linea de 1 a 60 caracteres sin jerga")`: para cada `p` de `PAGINAS`,
    `p.enUnaLinea.length` entre 1 y 60, y `!/\b(UC|RF|RNF|BCP)-\d/.test(p.enUnaLinea)`.
  - `test("los grupos de Mas cubren exactamente sus paginas")`: los ids de `AREAS.find(a => a.id === "mas")!.grupos` aplanados
    son iguales (como conjunto y sin repetidos) a `paginas` de «mas»; los títulos de grupo son, en orden,
    `["Precios", "Obra", "Análisis", "Ajustes"]`.
  - `test("los grupos de Mas")`: Precios = `actualizacion, historico, precios_empresa, indices, reajuste`; Obra = `control`;
    Análisis = `escenarios, similares, simulador`; Ajustes = `administracion, acerca`.
  - `test("la ayuda de una herramienta principal es la linea de su pagina")`: para cada herramienta visible,
    `h.ayuda === paginaPorId(h.pagina)!.enUnaLinea`.
- [ ] **Paso 2:** `npx vitest run src/shell/rutas.test.ts` → FALLA (propiedad inexistente).
- [ ] **Paso 3:** agregar `enUnaLinea` a las 22 páginas. Base, de la maqueta aprobada: componer «Arme el análisis de precio de una
  partida», elaborar «Junte partidas y cantidades», hoja «El presupuesto completo, como en Excel», catalogo «Partidas e insumos
  guardados», tablero «Cómo va el proyecto de un vistazo», entregar «Prepare lo que se envía al cliente», libros «Suba un Excel y
  vea lo que no cuadra», existencias «Cuánto hay y cuánto queda de cada material»; las otras 14 las propone el orquestador con el
  mismo estilo. Agregar `grupos` a «mas» y derivar `ayuda` en `herramientasVisibles`.
- [ ] **Paso 4:** `npx vitest run src/shell` → PASA (las pruebas viejas de `herramientasVisibles` se ajustan solo en la forma).
- [ ] **Paso 5:** commit `feat(front): linea de ayuda por pantalla y grupos de Mas en rutas`.

### Tarea 2: Lógica pura de la navegación

**Archivos:**
- Crear: `frontend-desktop/src/shell/navegacion.ts`
- Prueba: `frontend-desktop/src/shell/navegacion.test.ts`

**Interfaces:**
- Consume: `areasVisibles`, `AREAS`, `visible`, `PaginaDef`, `rutaDe` (Tarea 1).
- Produce:
  ```ts
  export interface GrupoNav { titulo: string | null; paginas: PaginaDef[] }
  export type EntradaNav =
    | { tipo: "enlace"; area: string; titulo: string; pagina: PaginaDef }
    | { tipo: "panel"; area: string; titulo: string; grupos: GrupoNav[] };
  export function navegacion(acciones: readonly string[], modoEntrega: boolean, paginas?: readonly PaginaDef[]): EntradaNav[];
  export function areaActual(pathname: string, entradas: readonly EntradaNav[]): string | null;
  ```
  Un área con una sola página visible es `enlace` (su `titulo` es el de la página); con varias, `panel`. «mas» usa sus `grupos`
  (filtrados por visibilidad, sin grupos vacíos) y las huérfanas en un grupo `Otras` al final, solo si existen; las demás áreas
  tienen un único grupo con `titulo: null`.

- [ ] **Paso 1: pruebas en rojo:**
  - con todas las acciones de `PAGINAS` (calculadas en la prueba con
    `new Set(PAGINAS.flatMap(p => p.accion ? [p.accion] : []))`) y `modoEntrega=false`: `navegacion(...).map(e => [e.area, e.tipo])`
    es `[["inicio","enlace"],["auditar","panel"],["crear","panel"],["produccion","enlace"],["mas","panel"]]`;
  - **ninguna página aparece dos veces** en todas las entradas, con cada uno de estos juegos de acciones escritos a mano en la
    prueba: todas, `[]`, solo la acción de `libros`, todas con `modoEntrega=true`;
  - con `[]` y una página de prueba sin acción: solo la entrada `inicio` (y ninguna con grupos vacíos);
  - en modo entrega, ninguna página de la sección «Investigación» aparece;
  - las huérfanas: con una página extra `{id:"x", accion:null, …}` que no está en `AREAS`, «mas» termina con el grupo
    `{titulo:"Otras", paginas:[x]}`;
  - `areaActual("/componer", e) === "crear"`, `areaActual("/inicio", e) === "inicio"`, `areaActual("/nada", e) === null`.
- [ ] **Paso 2:** `npx vitest run src/shell/navegacion.test.ts` → FALLA (módulo inexistente).
- [ ] **Paso 3:** implementar `navegacion` y `areaActual` sobre `areasVisibles` (sin duplicar su filtrado).
- [ ] **Paso 4:** misma orden → PASA.
- [ ] **Paso 5:** commit `feat(front): navegacion por areas sin duplicados`.

### Tarea 3: Barra y panel de área (ancho normal)

**Archivos:**
- Crear: `frontend-desktop/src/shell/BarraSuperior.tsx`, `frontend-desktop/src/shell/PanelDeArea.tsx`, estilos en
  `frontend-desktop/src/shell/shell.scss` (bloque `.silice-barra*` y `.silice-panel-area*`)
- Prueba: `frontend-desktop/src/shell/BarraSuperior.test.tsx`

**Interfaces:**
- Consume: `navegacion`, `areaActual`, `EntradaNav` (Tarea 2).
- Produce: `export function BarraSuperior(props: { entradas: readonly EntradaNav[]; derecha: ReactNode; menu: { abierto: boolean; alternar: () => void } }): JSX.Element`
  — `Header` con `HeaderName href="#/"` «Sílice», `HeaderMenuButton` (para la capa, Tarea 5) y `HeaderNavigation
  aria-label="Menú principal"`; `derecha` va dentro de `HeaderGlobalBar`.
  `export function PanelDeArea(props: { id: string; grupos: readonly GrupoNav[]; alElegir: () => void }): JSX.Element`.

- [ ] **Paso 1: pruebas en rojo** (`MemoryRouter`, entradas de la Tarea 2 con todas las acciones):
  - un área `enlace` es un `link` con su título; un área `panel` es un `button` con `aria-expanded="false"` y `aria-controls`;
  - clic en «Crear» → `aria-expanded="true"`, aparece la región del panel con los enlaces de Crear, cada uno con su `enUnaLinea`
    visible; el foco está en el primer enlace;
  - Intro sobre «Crear» abre igual; Esc cierra y el foco vuelve al botón «Crear»;
  - clic fuera (en el `main`) cierra; abrir «Más» cierra «Crear» (un solo panel abierto);
  - «Más» muestra los subtítulos Precios, Obra, Análisis, Ajustes;
  - elegir «Componer una partida» navega a `/componer` y cierra el panel;
  - en `/componer` el botón «Crear» lleva la marca de actual (`aria-current` en el enlace del panel y clase
    `silice-barra__area--actual` en el botón);
  - **foco de revisión 2:** con el panel de Crear abierto, `navigate(-1)` (o cambiar `initialEntries` y `rerender`) cierra el
    panel y la marca de actual pasa al área nueva;
  - **foco de revisión 3:** con un panel abierto, cambiar `document.documentElement.dataset.siliceLetra` (lo que hace
    `TamanoLetra`) y despachar el evento que escucha la barra cierra el panel;
  - pasar el ratón por encima (`hover`) **no** abre nada.
- [ ] **Paso 2:** `npx vitest run src/shell/BarraSuperior.test.tsx` → FALLA.
- [ ] **Paso 3:** implementar. El panel es un `<div role="region" aria-label="<Área>">` con `<ul>` de enlaces `NavLink`, bajo su
  botón, `$layer-01`, borde 1 px `$border-subtle`, sin sombra, ancho máximo `40rem`, dos columnas solo con letra Normal y
  ancho ≥ 1056 px (CSS), recortado a la ventana. Para el cambio de letra: escuchar un `MutationObserver` sobre
  `data-silice-letra` de `<html>`.
- [ ] **Paso 4:** misma orden → PASA; `npm run lint`.
- [ ] **Paso 5:** commit `feat(front): barra superior con panel explicado por area`.

### Tarea 4: Lado derecho: carpeta y proyecto, cuenta

**Archivos:**
- Crear: `frontend-desktop/src/shell/PanelCarpetaProyecto.tsx`, `frontend-desktop/src/shell/MenuCuenta.tsx`
- Modificar: `frontend-desktop/src/shell/Selectores.tsx` (rótulo «Caso» → «Carpeta de trabajo»; `inline` → apilado),
  `frontend-desktop/src/shell/Shell.tsx:209` (aviso → «Ahora trabaja con la carpeta de trabajo «X». Si se reinicia la API,
  vuelve a la carpeta por defecto.» y título del aviso «Carpeta de trabajo cambiada»)
- Prueba: `frontend-desktop/src/shell/PanelCarpetaProyecto.test.tsx`, `MenuCuenta.test.tsx`; ajustar `Selectores.test.tsx`

**Interfaces:**
- Produce: `export function PanelCarpetaProyecto(props: { casos: CasosRespuesta | null; proyectos: ProyectoRespuesta[] | null; elegido: string | null; puedeCambiar: boolean; ocupado: boolean; alElegirCaso: (n: string) => void; alElegirProyecto: (c: string | null) => void }): JSX.Element`
  — un `HeaderGlobalAction` con el texto «<carpeta sin .db> · <proyecto o «Sin proyecto»>» que abre un `HeaderPanel` con
  `SelectorCaso` y `SelectorProyecto` apilados y un título «Carpeta y proyecto» (h2 no: rótulo de texto; un solo h1 por
  página). Deja un hueco `children?: ReactNode` al final del panel para BCP-5/6.
  `export function nombreDeCarpeta(nombre: string): string` (quita `.db` final).
  `export function MenuCuenta(props: { nombre: string; alSalir: () => void }): JSX.Element`.

- [ ] **Paso 1: pruebas en rojo:**
  - `nombreDeCarpeta("demo.db") === "demo"`, `nombreDeCarpeta("obra.v2.db") === "obra.v2"`, `nombreDeCarpeta("x") === "x"`;
  - el botón muestra «demo · Torre B»; sin proyecto elegido muestra «demo · Sin proyecto»; su nombre accesible es
    «Carpeta de trabajo: demo. Proyecto: Torre B. Cambiar»;
  - clic abre el panel con los selectores rotulados «Carpeta de trabajo» y «Proyecto»; Esc lo cierra y devuelve el foco;
  - **foco de revisión 1:** con una carpeta de 80 caracteres el botón tiene la clase `silice-contexto__texto` (con
    `text-overflow: ellipsis; max-inline-size: 18rem` en el SCSS) y el nombre accesible lleva el nombre completo;
  - `MenuCuenta`: muestra el nombre; su menú tiene solo «Salir»; «Salir» llama `alSalir`;
  - ninguna cadena visible del armazón contiene la palabra «caso» (`screen.queryByText(/\bcaso\b/i)` es `null` en los dos
    componentes y en el aviso).
- [ ] **Paso 2:** `npx vitest run src/shell/PanelCarpetaProyecto.test.tsx src/shell/MenuCuenta.test.tsx` → FALLA.
- [ ] **Paso 3:** implementar; con letra Grande/Muy grande o ancho < 1366 px el texto se oculta por CSS y queda el ícono
  `Folder` (el nombre accesible no cambia).
- [ ] **Paso 4:** misma orden y `src/shell/Selectores.test.tsx` → PASA.
- [ ] **Paso 5:** commit `feat(front): carpeta de trabajo y proyecto en la barra, menu de la cuenta`.

### Tarea 5: Capa en ancho estrecho o letra grande

**Archivos:**
- Crear: `frontend-desktop/src/shell/MenuEnCapa.tsx` (sustituye a `MenuLateral.tsx`, que se borra en la Tarea 7)
- Modificar: `frontend-desktop/src/shell/shell.scss` (mixin `menu-en-capa`: agrega `("normal", 1055.98px)`, oculta
  `.silice-barra__nav` y muestra el botón por debajo del umbral; los umbrales de Grande y Muy grande siguen en 1535.98 y
  1919.98 px)
- Prueba: `frontend-desktop/src/shell/MenuEnCapa.test.tsx`

**Interfaces:**
- Consume: `EntradaNav` (Tarea 2).
- Produce: `export function MenuEnCapa(props: { entradas: readonly EntradaNav[]; abierto: boolean; alCerrar: () => void; nombre?: string }): JSX.Element`
  — `SideNav aria-label="Menú principal (capa)" expanded={abierto} isPersistent={false}` con `HeaderSideNavItems`; cada área un
  grupo con su rótulo de texto y sus enlaces con `enUnaLinea`.

- [ ] **Paso 1: pruebas en rojo:** abierto, muestra todas las entradas de la Tarea 2 sin repetir ninguna página; cada enlace lleva
  su `enUnaLinea` como descripción (`aria-describedby`); elegir un enlace llama `alCerrar`; Esc llama `alCerrar`; con `nombre`
  muestra «Sesión de <nombre>» al pie.
- [ ] **Paso 2:** `npx vitest run src/shell/MenuEnCapa.test.tsx` → FALLA.
- [ ] **Paso 3:** implementar; el SCSS lo verifica la Tarea 8 (jsdom no evalúa media queries).
- [ ] **Paso 4:** misma orden → PASA.
- [ ] **Paso 5:** commit `feat(front): menu en capa por debajo del umbral de cada letra`.

### Tarea 6: Recorrido guiado como columna acoplada

**Archivos:**
- Crear: `frontend-desktop/src/shell/ColumnaRecorrido.tsx`
- Modificar: `frontend-desktop/src/shell/PanelRecorrido.tsx` (`alTerminar`: el foco va al h1 de la página, `#contenido h1`, ya
  no a un enlace del menú), `frontend-desktop/src/shell/shell.scss` (`.silice-con-recorrido` estrecha el `main` 16 rem;
  por debajo del umbral, la columna pasa a franja plegable bajo la barra)
- Prueba: `frontend-desktop/src/shell/ColumnaRecorrido.test.tsx`; ajustar `PanelRecorrido.test.tsx`

**Interfaces:**
- Consume: `useRecorrido`, `terminarRecorrido` (`recorrido.ts`), `PanelRecorrido`.
- Produce: `export function ColumnaRecorrido(props: { paginas: readonly PaginaDef[]; acciones: readonly string[]; modoEntrega: boolean }): JSX.Element | null`
  y `export function BotonRecorrido(): JSX.Element | null` (para la barra: visible solo con un recorrido activo y la columna
  oculta). El estado «oculta» vive en `recorrido.ts` como `ocultarColumna(): void`, `mostrarColumna(): void`,
  `useColumnaOculta(): boolean` (mismo patrón de almacén externo).

- [ ] **Paso 1: pruebas en rojo:**
  - sin recorrido no se pinta nada; con `iniciarRecorrido(RECORRIDO_AUDITAR)` aparece la región «Recorrido» con sus pasos;
  - «Ocultar» la oculta y aparece `BotonRecorrido`; pulsarlo la muestra de nuevo;
  - «Terminar recorrido» llama `terminarRecorrido` y el foco va al h1 de la página;
  - navegar a otra ruta no la cierra;
  - **foco de revisión 4:** con la columna visible y un panel de área abierto (montar `BarraSuperior` y `ColumnaRecorrido`
    juntos), Esc cierra el panel de área y la columna sigue visible y el recorrido sigue en curso.
- [ ] **Paso 2:** `npx vitest run src/shell/ColumnaRecorrido.test.tsx src/shell/PanelRecorrido.test.tsx` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** misma orden → PASA.
- [ ] **Paso 5:** commit `feat(front): recorrido guiado en una columna acoplada`.

### Tarea 7: Montaje en `Shell.tsx`, mosaicos del Inicio y retiro del menú lateral

**Archivos:**
- Modificar: `frontend-desktop/src/shell/Shell.tsx` (sustituye `Cabecera` + `MenuLateral` por `BarraSuperior` +
  `MenuEnCapa` + `ColumnaRecorrido`; `derecha` = `PanelCarpetaProyecto`, `BotonRecorrido`, `TamanoLetra`, `MenuCuenta`),
  `frontend-desktop/src/paginas/inicio/index.tsx` (tres mosaicos `ClickableTile` con las `herramientasVisibles`: título y
  `ayuda`, debajo de la zona de auditar; nada más cambia en el Inicio)
- Borrar: `frontend-desktop/src/shell/MenuLateral.tsx`, `frontend-desktop/src/shell/Cabecera.tsx` (y `Cabecera.test.tsx`, cuyo
  contenido útil pasa a `BarraSuperior.test.tsx`), las reglas `.silice-menu__*` de `shell.scss`
- Prueba: reescribir `Shell.test.tsx` (las ~17 que usan `menu()`), `App.test.tsx` (3), `Selectores.test.tsx` (2),
  `sinClasica.test.ts:33`; nueva en `src/paginas/inicio/Inicio.test.tsx`

- [ ] **Paso 1: pruebas en rojo:**
  - `Shell.test.tsx`: `navigation "Menú principal"` existe y contiene las áreas visibles del rol; ana, rita y admin (acciones de
    las pruebas existentes) ven las áreas esperadas; en modo entrega no aparece ninguna pantalla de Investigación; el foco pasa
    al h1 al navegar desde un panel; el aviso de cambio de carpeta dice «carpeta de trabajo»;
  - **ninguna página tiene dos enlaces dentro de una misma navegación**: dentro de `navigation "Menú principal"` y, por
    separado, dentro de `navigation "Menú principal (capa)"`, cada título de página aparece como enlace una sola vez
    (`within(nav).getAllByRole("link", { name: titulo })` de longitud 1);
  - `Inicio.test.tsx`: con las acciones de ana, tres mosaicos «Libro de la empresa», «Componer una partida», «Existencias de la
    arenera» con su ayuda; sin permisos para una, esa no aparece;
  - `sinClasica.test.ts`: la expresión de clases prohibidas incluye `silice-menu__`.
- [ ] **Paso 2:** `npx vitest run src/shell src/App.test.tsx src/paginas/inicio` → FALLA.
- [ ] **Paso 3:** montar, borrar lo retirado.
- [ ] **Paso 4:** `npx vitest run` (toda la suite del front), `npm run lint`, `npm run build` → PASA y limpio.
- [ ] **Paso 5:** commit `feat(front): la barra superior reemplaza al menu lateral`.

### Tarea 8: Recorrido visual ampliado y documentación

**Archivos:**
- Modificar: `scripts/recorrido_ux_playwright.py` (tres letras, controles nuevos), `frontend-desktop/DESIGN.md:73-76`,
  `CHANGELOG.md` (orquestador)

- [ ] **Paso 1:** agregar al script, por medición: `--letras normal,grande,muy-grande` (fija `data-silice-letra` como hace
  `TamanoLetra`), y los controles `duplicados_nav` (títulos repetidos entre los enlaces de `nav[aria-label="Menú principal"]`
  y su capa: debe ser 0), `barra_cortada` (`header` con `scrollWidth > clientWidth`: debe ser falso), `panel_fuera` (abrir cada
  área y comprobar que el `getBoundingClientRect()` del panel queda dentro de la ventana), y repetir Inicio y Libro con un
  recorrido activo.
- [ ] **Paso 2:** correr `uv run --active --with playwright python -u scripts/recorrido_ux_playwright.py --salida <scratchpad>/barra`
  → las 22 rutas × ana/rita/admin × 1366 y 1056 × tres letras: un h1, sin desplazamiento horizontal, 0 errores de consola y
  red, `duplicados_nav = 0`, `barra_cortada = false`, `panel_fuera = false`, axe sin violaciones nuevas frente a
  `docs/bitacora/2026-10-25-recorrido-ux-playwright.md`.
- [ ] **Paso 3:** reescribir `DESIGN.md` §marco (barra superior, panel de área, umbrales por escala, cabecera de 3 rem, columna
  del recorrido) y la línea de `CHANGELOG.md`.
- [ ] **Paso 4:** `ruff check scripts/recorrido_ux_playwright.py` limpio.
- [ ] **Paso 5:** commit `docs(front): diseno de la barra superior y recorrido visual ampliado`; bitácora con las cifras.

### Tarea 9: Recorrido funcional (BS-F): que todas las herramientas funcionen

**Archivos:**
- Crear: `scripts/recorrido_funcional.toml` (una fila por pantalla), `docs/bitacora/2026-10-2x-recorrido-funcional.md`
- Modificar: `scripts/recorrido_ux_playwright.py` (modo `--funcional`)

**Interfaces:**
- Formato de cada fila del TOML: `[[pantalla]] ruta = "componer"`, `cuenta = "ana"`, `pasos = [ { accion = "llenar", rotulo =
  "Código", valor = "DEMO-F01" }, { accion = "pulsar", nombre = "Guardar" }, … ]`, `espera = { texto = "…" }` o
  `espera = { descarga = true }`. Acciones admitidas: `llenar`, `elegir`, `pulsar`, `subir` (ruta de `tests/fixtures/**`),
  `ir`. La siembra adicional (clave de firma ficticia, paquete generado por Entregar y consumido por Revisar, archivos de
  Índices del BCV y de Actualizar precios) la hace el script antes de las filas, con datos de `tests/fixtures/**`.

- [ ] **Paso 1:** escribir las 22 filas leyendo cada pantalla (la acción principal y el resultado visible que la prueba).
- [ ] **Paso 2:** correr `--funcional`; anotar en la bitácora, por pantalla: pasó / falló, la salida, y el dueño del defecto
  (armazón → se corrige en este plan; otra pantalla → trabajo propio con TDD y árbitro; `core/` → bloqueo para el tutor).
- [ ] **Paso 3:** corregir los defectos del armazón y volver a correr hasta que las filas del armazón pasen.
- [ ] **Paso 4:** entregar a Eugenio la lista de defectos de las demás pantallas (resumen en la bitácora).
- [ ] **Paso 5:** commit `test(front): recorrido funcional de las 22 pantallas` (más los de cada arreglo).

## Cierre

Árbitro por tarea (criterios A1-F1); al final, revisor de diseño (`.claude/agents/silice-rev-diseno.md`) sobre las capturas de la
Tarea 8; `npx vitest run`, `npm run lint`, `npm run build`; línea de `CHANGELOG.md`; memoria y bitácora al día. Sin push ni PR.
