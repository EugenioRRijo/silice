# Reglas de construcción de B1 (superficie Presupuesto), de lectura obligatoria

Eugenio pidió el 2026-11-25 aplicar **al pie de la letra** tres skills: la guía de Google (modern-web-guidance),
ui-ux-pro-max y ub-mode. Este archivo las junta para B1. Si una regla de aquí choca con NORMAS.md o con una decisión de
Eugenio, mandan ellas, y el choque se anota en el informe. **DESIGN.md NO manda en la cara de la reestructuración**
(Eugenio, 2026-11-26): se puede leer como referencia, y la cara nueva se decide aparte, ver §6.

## 0. Fuentes que se leen antes de escribir código
- **Diseño:**
  - `docs/bitacora/2026-11-25-acta-reestructuracion-front.md`, con los límites;
  - `docs/planes/2026-11-25-propuesta-ux-ui.md`, B.3, B.4 (pantalla 1) y B.5;
  - `frontend-desktop/DESIGN.md`.
- **Skills del proyecto:** `.agents/skills/interfaz-silice/SKILL.md`, que exige la ficha de 10 partes antes del código.
- **Guías de Google** (completas en
  `C:\Users\euger\AppData\Local\Temp\claude\d6f1b8a6cbbdf480\fc6271bc-da6b-42c2-a1eb-532f217176d0\scratchpad\guias-google\`):
  - `responsive-table.md`, `spatial-navigation.md`, `interactions-in-complex-layouts.md`;
  - `state-aware-sticky-headers.md`, `single-line-overflow.md`, `content-first-noise-reduction.md`;
  - `accessibility.md`, `dialog.md`, `html.md`, `forms.md`, `validate-input-after-interaction.md`;
  - `accessible-error-announcement.md`, `interest-triggered-tooltips.md`, `defer-rendering-heavy-content.md`, `spinner.md`.

  Cada cambio cita la guía que sigue.
- **Las piezas de B0** que se usan, en vez de crear otras:
  - `comun/Dialogo`, `Anunciador` (`useAnunciar`), `MontoExacto`, `CampoDeCifra`;
  - `useFocoEnPrimerError`, `recurso` (`useRecurso`, `invalidarRecursos`);
  - `api/cliente`, con `pedir(ruta, { leer })` y un analizador por recurso.

## 1. Guía de Google: reglas literales que aplican a B1
- **La tabla** (`responsive-table`):
  - «Use standard `<table>` elements with `<thead>`, `<tbody>`, and `<th>` elements».
  - «Apply `position: sticky` to both column headers and row headers».
  - «Use `@container` queries instead of `@media` queries».
  - «Keep long cell text on one line instead of letting columns shrink below legibility».
- **Teclado en la grilla** (`spatial-navigation`):
  - «Limit to composite widgets»: las flechas solo dentro de un `role="grid"`.
  - «The spatial container must expose a single tab stop», con roving tabindex: el activo con `tabindex="0"` y el
    resto con `-1`.
  - «Roving tabindex only works with screen readers when the container and items have appropriate composite-widget
    roles and states (e.g. grid/gridcell…)».
  - «If there is no focusable element in the pressed direction, **do not prevent default browser behavior**».
  - «Do not intercept the event when a modifier key is held, when `e.defaultPrevented` is already true, or when the
    innermost event target consumes arrow keys itself».
  - Al mover el foco, `scrollIntoView({ block: 'nearest', inline: 'nearest' })`.
- **Rendimiento al editar una celda** (`interactions-in-complex-layouts`): «performing a minor change to a single
  item—such as … editing a cell—can trigger a chain reaction of style and layout calculations». Se contiene con
  `content-visibility: auto` y containment por región, **después de medir**.
- **Encabezado fijo con el total** (`state-aware-sticky-headers`): la cabecera fija de la obra con el total sigue esa
  guía.
- **Texto largo en celdas** (`single-line-overflow`): «Use `overflow: hidden`, not `clip`». El texto completo se
  muestra a pedido.
- **Ruido** (`content-first-noise-reduction`):
  - «Don't move content while the user reads… don't open popovers the user didn't ask for».
  - Lo secundario va detrás de una revelación a pedido.
- **Accesibilidad** (`accessibility`):
  - «Don't use `title` as a naming mechanism».
  - «Centralize live regions»: se usa `useAnunciar`.
  - «Update single-page application (SPA) titles during page transitions»: ya lo hace el marco.
- **El inspector** (`dialog` y `html`): el inspector lateral **no es modal**. Si se hace con `<dialog>`, se abre con
  `show()` y no con `showModal()`, o se usa el `PanelLateral` actual.
- **Formularios** (`forms`): «DON'T disable submit buttons to block validation». La validación va con `CampoDeCifra`.

## 2. ui-ux-pro-max: lo que aplica
- **Estilo «Data-Dense Dashboard»:** «data tables, KPI cards, minimal padding, grid layout, space-efficient, maximum
  data visibility».
- Sus colores y su tipografía **son opciones** para el cambio de cara. Eugenio elige; las fuentes van empaquetadas en
  el repositorio, nunca desde Google Fonts, por la CSP sin conexión.
- **Checklist antes de entregar**, adaptado a Carbon (no hay Tailwind):
  - sin emojis como íconos: solo `@carbon/icons-react`;
  - `cursor: pointer` en todo lo que se pueda pulsar;
  - transiciones de 150 a 300 ms y `prefers-reduced-motion` respetado;
  - foco visible con `:focus-visible`, sin quitar `outline` sin dar una alternativa;
  - contraste de 4,5:1 como mínimo;
  - el color no es el único indicador: «Problemas» lleva texto y no solo un color;
  - `onKeyDown` junto a cada `onClick` en lo que no sea un botón nativo.
- **Reglas de UX y web con severidad alta o crítica:**
  - «Tab order matches visual order»;
  - «Use visible focus rings»;
  - «Define z-index scale system»;
  - «Use skeleton screens or spinners» (el esqueleto de la tabla con su cabecera, sin cifras inventadas);
  - «Virtualize Lists… for large datasets» (solo si la medición lo pide; ver `defer-rendering-heavy-content`).
- **React:**
  - «One concern per component»;
  - «Use stable IDs as keys», nunca el índice;
  - «memo for pure components with stable props».

## 3. ub-mode: cómo se trabaja
- **Primero que funcione:**
  - una decisión en un solo lugar;
  - el cambio más chico que resuelve;
  - la forma de los datos antes que la lógica.
- **TDD:**
  - la prueba en rojo antes del código, vista fallar por la razón esperada;
  - si una prueba honesta no es práctica, no se escribe una mala.
- **El dominio:**
  - estados ilegales imposibles (uniones discriminadas);
  - los datos se validan donde entran (`leer`) y adentro se confía;
  - la lógica de negocio en funciones puras: cada flujo con pasos es una máquina de estado
    `siguiente(estado, evento)` probada sin React.
- **Después, que quede bien:**
  - causa raíz, nunca un parche que esconda el error;
  - probar el comportamiento y no la implementación: «Si la prueba seguiría pasando cuando cada función no
    devolviera nada, tírala»;
  - **Mutator:** una mutación a mano por comportamiento, que debe hacer fallar una prueba. «Kill the survivors.
    Delete dead code.»
  - **Refactor:** fijar lo que hace el código, cambiar la estructura y probar que el comportamiento no cambió.
- **Práctica:**
  - el informe es una bitácora de cada acción y su motivo;
  - commits chicos, cada uno con el porqué, qué cambió y cómo se probó (los hace Claude).

## 4. Límites que no se negocian (acta)
- `core/`, los archivos sellados por `reglas-congeladas-2026-11-24` y `aplicacion/hoja.py` no cambian.
- Coma decimal y punto de miles, trato de usted y la cifra la calcula el servidor.
- Ningún dato real en las pruebas.
- No se corre `prettier --write`.
- Si un gancho bloquea un comando: reintentar idéntico una sola vez; si vuelve a bloquear, parar y reportar.

## 5. Movimiento (decisión de Eugenio, 2026-11-26; ver DESIGN.md › Movimiento)
- Solo movimiento funcional: el inspector entra desde su lado; el menú «Más acciones» y los diálogos aparecen con un
  fundido. Como máximo 2 elementos animados por vista, de 150 a 240 ms, con `ease-out` y solo `transform` y `opacity`.
  Nada anima al cargar la página y nada es decorativo.
- Movimiento reducido según la guía `motion`: la animación va dentro de
  `@media (prefers-reduced-motion: no-preference)`, y los cambios de color se conservan.
- Guías que se leen: `guias-google/motion.md`, `animate-to-from-top-layer.md` y `animate-element-entry-exit.md`.

## 6. La cara de la reestructuración (Eugenio, 2026-11-26)
«recuerda que la reestructuracion no hace caso al design.md, quiero una reestructuracion, un cambio de cara, la paleta
de colores puedes usarla de referencia para probrar otros colores».
- La paleta, la tipografía, la barra superior, la barra lateral, los botones y los widgets de hoy (DESIGN.md y
  `tokens.scss`) son **referencia**, no reglas.
- La cara nueva sale de propuestas que Eugenio elige. **Mientras no elija, los lotes de B1 usan solo tokens**
  (`--silice-*` y los de Carbon), nunca colores sueltos. Así, cambiar la cara después es cambiar los tokens, y no hay
  que rehacer las pantallas.
- **Lo que sigue valiendo:**
  - contraste WCAG AA;
  - la severidad nunca se dice solo con color;
  - las fuentes van empaquetadas;
  - el tema de la empresa (`/v1/tema`) tiene que seguir funcionando;
  - las decisiones D1 a D8;
  - el movimiento funcional.
