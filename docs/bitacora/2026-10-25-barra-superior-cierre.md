# Barra superior: recorrido visual de cierre (2026-10-25)

**Encargo:** Tarea 8 de `docs/planes/PLAN_BARRA_SUPERIOR.md` (diseño APROBADO
`docs/especificaciones/2026-10-25-barra-superior-design.md`, §8.2). Referencia: la corrida del mismo día con el menú lateral,
`docs/bitacora/2026-10-25-recorrido-ux-playwright.md`. Datos ficticios (cuentas de `tests/fixtures/sesion_web.py`, demostración de
`start.py`, libro limpio de `tests/fixtures/libros_empresa.py`); nada de `data/` ni datos reales.

## Herramienta

`scripts/recorrido_ux_playwright.py` gana, solo en el modo visual (el `--funcional` de la Tarea 9 no cambia):

- `--letras normal,grande,muy-grande` (por omisión, las tres): fija la preferencia antes de cargar, como `TamanoLetra`, y
  comprueba que `<html data-silice-letra>` quedó con ella (`letra_no_aplicada`).
- `duplicados_nav`: nombres repetidos dentro de la barra (áreas, enlaces directos y el contenido de cada panel abierto) y,
  por separado, dentro de la capa (rótulos de área y enlaces). Debe ser 0. Cuenta también un área que repite el nombre
  de su única pantalla («Inicio / Inicio»).
- `barra_cortada`: la cabecera con `scrollWidth > clientWidth`, algún botón o enlace suyo fuera de la ventana, o la última
  área montada sobre el lado derecho.
- `panel_fuera`: abre cada área de la barra y mide la caja de su panel contra la ventana; cuando la barra no cabe (letra
  Grande o Muy grande), abre la capa, espera a que termine su transición de 110 ms y exige que esté dentro, con ancho y
  con todos sus enlaces visibles.
- Inicio y Libro **con recorrido guiado en curso** (Inicio → soltar el libro → «Auditar con recorrido guiado»), para quien
  puede auditar (ana y rita): columna «Recorrido» visible, dentro de la ventana y sin tapar el contenido.
- axe: las violaciones se comparan con las de la referencia (`administracion`/`color-contrast`,
  `inicio`/`scrollable-region-focusable`); cualquier otra (pantalla, regla) cuenta como nueva.
- Sirve una copia de `frontend-desktop/dist` (una recompilación ajena a mitad de la corrida no la rompe).
- Una captura con cada panel abierto (o con la capa) en Inicio, por cuenta, ancho y letra, para el revisor de diseño.

Comprobado que los controles **se ponen en rojo**: inyectando en el navegador un rótulo «Inicio» repetido en la capa
(`duplicados_nav = 1`, «Inicio x2»), un panel corrido 900 px y la capa trasladada 1200 px (`panel_fuera`, con las tres
áreas y con «capa») y un botón de 900 px en la cabecera (`barra_cortada`, con letra Normal y Grande). Las funciones puras
(letras, axe nuevo, resumen) tienen pruebas en `tests/unit/test_recorrido_ux_playwright.py`.

```powershell
uv run --active --with playwright python -u scripts/recorrido_ux_playwright.py --salida <scratchpad>\barra_visual --sin-flujo
```

## Corrida (2026-10-25, interfaz compilada a las 17:29)

22 rutas × admin/ana/rita × 1366 y 1056 px × Normal/Grande/Muy grande = **396 mediciones**, más **24** con recorrido
(Inicio y Libro × ana/rita × 2 anchos × 3 letras): 420 en total, 446 capturas, axe en las 420. Se corrió con `--sin-flujo`
(los flujos de subida de la referencia no son criterio de esta tarea; la subida guiada queda cubierta por las filas con
recorrido).

| Control (criterio) | Normal | Grande | Muy grande | Con recorrido | Total |
|---|---|---|---|---|---|
| Mediciones (en el menú del rol) | 132 (64) | 132 (64) | 132 (64) | 24 (24) | 420 (216) |
| Error de carga (0) | 0 | 0 | 0 | 0 | 0 |
| En el menú sin exactamente un h1 (0) | 0 | 0 | 0 | 0 | 0 |
| Más de un h1 (0) | 0 | 0 | 0 | 0 | 0 |
| Desplazamiento horizontal (0) | 0 | 0 | 0 | 0 | 0 |
| Errores de consola (0) | 0 | 0 | 0 | 12 | 12 |
| Errores de red (0) | 0 | 0 | 0 | 0 | 0 |
| Letra no aplicada (0) | 0 | 0 | 0 | 0 | 0 |
| `duplicados_nav` (0) | 0 | 0 | 0 | 0 | 0 |
| `barra_cortada` (0) | 0 | 0 | 0 | 0 | 0 |
| `panel_fuera` (0) | 0 | 0 | 0 | 0 | 0 |
| Navegación medida como barra / capa | 132 / 0 | 0 / 132 | 0 / 132 | 8 / 16 | 140 / 280 |
| Con violaciones axe | 2 | 2 | 4 | 16 | 24 |
| Con violaciones axe **nuevas** (0) | 0 | 0 | 0 | 12 | 12 |
| Columna «Recorrido» no visible / tapa el contenido (0) | | | | 0 / 0 | |

- **Barra (letra Normal, 1366 y 1056):** los paneles de Auditar, Crear y Más quedan dentro de la ventana en sus 88
  mediciones de ana y rita (admin solo tiene «Más» como panel: 44 más), siempre a dos columnas. A 1056 px el panel de «Más»
  se corre a la izquierda y cabe.
- **Capa (Grande y Muy grande, a los dos anchos):** se abre con sus enlaces (18 de ana, 8 de rita, 6 de admin) todos
  visibles, 373 px de ancho con Grande y 448 px con Muy grande (16 rem), dentro de la ventana. «Inicio» y «Existencias de
  la arenera» salen una sola vez (corrección M6 de este encargo, abajo).
- **Recorrido:** con Normal es columna fija a la derecha y el contenido le cede su ancho; con Grande y Muy grande, franja
  bajo la barra encima del contenido. En las 24 mediciones, visible y sin tapar el contenido.
- Lo que ve cada rol no cambió: ana 18, rita 8, admin 6 pantallas. Tiempo hasta el primer h1 (rutas del menú, carga en
  frío): 327-783 ms, media 450 ms (referencia: 356-571, media 466).
- **H-8 sigue igual:** las 204 mediciones de rutas fuera del menú del rol (68 por letra, como en la referencia) muestran
  «Sin permiso» sin h1. No es de esta fase.

## Hallazgos

### Corregido en el armazón (TDD)

- **M6 (árbitro): la capa repetía el nombre de un área de una sola pantalla** («Inicio / Inicio», «Existencias de la arenera
  / Existencias de la arenera»), el doble que el diseño §1 quería quitar. Prueba en rojo en `MenuEnCapa.test.tsx` y
  corrección en `MenuEnCapa.tsx`: una entrada `tipo === "enlace"` se pinta sin rótulo, solo el enlace con su línea de
  ayuda. La corrida lo confirma (`duplicados_nav = 0` en las 280 mediciones en capa).

### De pantallas (anotados, no corregidos aquí)

- **V-1. Libro de la empresa, visor con un libro cargado: `aria-valid-attr-value` (axe, crítico, 1 nodo).** Las pestañas de
  hojas (`frontend-desktop/src/visor/Visor.tsx:358`, `Tabs`/`TabList` de Carbon sin `TabPanel`) llevan
  `aria-controls="…-tabpanel-0"` hacia un panel que no existe. Sale igual auditando «por mi cuenta» que con el recorrido
  (comprobado aparte): es del visor, no de la columna. No es una regresión medible: la referencia nunca pasó axe por el
  visor con un libro (sus 132 mediciones eran con la pantalla vacía, que sigue limpia). Son las 12 «nuevas» de la tabla.
- **V-2. Libro de la empresa, visor con un libro cargado: `pageerror` de Univer** `[redi]: Cannot find "u4" registered by
  any injector` (24 veces por carga). También sin recorrido: es del visor/Univer. La hoja se pinta y los hallazgos salen;
  la referencia no registraba la consola de los flujos de subida, así que no se sabe desde cuándo. Son los 12 «errores de
  consola» de la tabla.
- **V-3. `scrollable-region-focusable` en Inicio** (regla ya conocida, H-10 de la referencia, en rita a 1056): ahora sale a
  1056 px con Muy grande (ana y rita) y con el recorrido a 1056 con Normal y Muy grande; ya no sale en rita a 1056 Normal
  sin recorrido. Misma regla y pantalla: no cuenta como nueva, pero aparece en más combinaciones.
- `administracion` / `color-contrast` (H-10): igual que en la referencia, ahora en las tres letras.

## Límites

- Navegador sin interfaz (Chromium de Playwright); axe cubre parte de WCAG; el teclado y el foco de la barra los prueban las
  pruebas de Vitest, no este recorrido.
- La interfaz compilada incluía cambios sin confirmar de otro agente en `src/paginas/componer/` (trabajo en paralelo en el
  mismo árbol); no afectan a la barra.
- Modo entrega no recorrido (lo cubren las pruebas de `navegacion.test.ts` y `Shell.test.tsx`).

Salida: `recorrido.json`, `consola.txt` y `capturas/` en la carpeta del scratchpad (`barra_visual/`); no se versionan.
