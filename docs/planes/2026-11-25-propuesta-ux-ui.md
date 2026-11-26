# Propuesta de actualización de la UX y la UI del front de Sílice según la guía «modern-web-guidance» de Google

**Fecha:** 2026-11-25.

> **Enmienda del 2026-11-25 (decisión de Eugenio):** B se aplica **antes** de medir con personas, en las fases B0, B1,
> B4 y B2, con fecha tope el 2026-12-16 y la etiqueta `medicion-v1`. Se mide sobre la versión nueva, así que no se
> repite ningún SUS. B3 y el resto de B5 quedan para después de defender. Ver el
> [acta](../bitacora/2026-11-25-acta-reestructuracion-front.md). El texto de abajo es el de la propuesta original.

Fuentes: las 10 guías de Google leídas desde el disco (sin `npx`), el plan
`docs/planes/2026-11-25-plan-front-tras-medir.md`, los informes A a E de `docs/planes/auditoria-front-2026-11-25/`,
`frontend-desktop/DESIGN.md`, `disenar-desde-la-tarea` (SKILL.md y reglas.md), `interfaz-silice` y el guion de la prueba
con usuarios. Las citas `archivo:línea` salen de los informes A a E, que auditaron el árbol `.worktrees/s4`. Las que dicen
«lectura propia» las comprobé yo en ese mismo árbol (commit `8e57a8df`). Hay que confirmarlas otra vez contra `main`
antes de aplicar nada (AGENTS.md: un hallazgo vale en el árbol actual).

## Qué cambia para quien usa Sílice

1. Las ventanas que piden confirmar algo, como guardar una versión o agregar una partida, se abren siempre igual, se
   cierran con Esc y devuelven al presupuestista al botón que tocó.
2. El valor exacto de una cifra se abre con un clic o con el teclado, y siempre con coma decimal. Hoy algunas cifras lo
   muestran solo al pasar el ratón, y con punto.
3. Sílice marca un campo en rojo solo después de que la persona lo llena y sale de él, no mientras escribe. Al pulsar el
   botón principal, el cursor salta al primer dato que falta y le dice cómo corregirlo.
4. El botón principal ya no se queda gris sin explicación: se puede pulsar, y Sílice dice qué falta.
5. Al pasar de una pantalla a otra, quien usa lector de pantalla oye el nombre de la pantalla nueva. Un total que se
   recalcula ya no se repite en voz alta con cada tecla.
6. En las tablas largas, los encabezados y la primera columna quedan fijos al desplazarse. Las cifras con coma abren el
   teclado numérico en una pantalla táctil.
7. Lo que no se puede deshacer (anular una valuación o descartar escenarios) pide confirmación, con el cursor en
   «Cancelar».
8. Con la Propuesta B, además, el presupuesto muestra siempre su total y sus problemas al lado de las partidas, y la
   partida nueva se compone sin salir de la tabla.

## Cómo leer este documento

Primero van los principios, que valen para las dos propuestas. Después va la **Propuesta B (desde cero)**, que replantea
la navegación, las pantallas y el manejo de estado sin atarse a las skills de diseño del proyecto ni a los hooks actuales.
Luego va la **Propuesta A (incremental)**, que corrige el front de hoy pieza por pieza. Al final están lo que no se
recomienda, las contradicciones encontradas y la recomendación.

## Principios

1. **Lo nativo primero, y Carbon como piel.** Cuando el navegador ya trae el comportamiento (`<dialog>`, `popover`,
   `:user-invalid`), se usa eso y se viste con los tokens y las clases de Carbon. Guía `accessibility`: «Prefer HTML
   elements and attributes to ARIA».
2. **El error llega después de actuar, y el foco lo lleva.** Guía `validate-input-after-interaction`: «DO use
   `:user-invalid` to apply error styling only after interaction.»
3. **Un cambio, un anuncio, una sola región por página.** Guía `accessibility`: «Centralize live regions for
   non-visible announcements».
4. **Lo que se necesita para actuar va a la vista; lo opcional, a pedido.** Guía `interest-triggered-tooltips`:
   «**Inline content**: information most users need in order to act».
5. **Primero se mide y después se difiere.** Guía `defer-rendering-heavy-content`: «DO NOT apply this property to
   elements within the initial, above-the-fold viewport.»
6. **El teclado de Excel sin romper el de la plataforma.** Guía `spatial-navigation`: «If there is no focusable element
   in the pressed direction, do not prevent default browser behavior.»

---

## Propuesta B: desde cero

### B.1 Por qué replantear

Los informes no describen fallos sueltos. Describen una forma de construir que hace que el mismo fallo se repita:

- Doce diálogos modales hechos a mano, de tres implementaciones distintas. Ninguno usa `<dialog>` (E #14; B #3; C, fila
  1).
- El 401 se maneja en unos 110 sitios de 86 archivos (E #2), y `pedir<T>` hace `as T` en 184 llamadas (E #1).
- Hay siete o más variantes de «cargar y descartar la respuesta vieja» (B #7; E #11).
- El estado de las pantallas grandes es frágil: `ComponerPartida` tiene 630 líneas y unos 25 estados (B #1), y
  `useEdicionDeSeccion` guarda 6 banderas mutables (A #3).
- El filtro de Control se pierde al cambiar de pestaña (B #4, confirmado en el navegador el 2026-11-25).
- La obra tiene 16 pantallas en 9 secciones, más 6 o 7 pestañas dentro del Presupuesto (DESIGN.md, «Espacios» y
  «Secciones de la obra»). Para leer el total (T1) y decir si hay problemas (T3), la persona cruza secciones y pestañas
  distintas: el total está en la línea de estado y los hallazgos en la pestaña «Revisión».

### B.2 Lo que no cambia (son NORMAS, no skills)

- Coma decimal y punto de miles en toda entrada y salida.
- Trato de usted.
- Los libros de la empresa y lo derivado de ellos nunca salen del equipo.
- La lógica de negocio y las cifras las calcula el servidor. La interfaz no calcula montos ni veredictos: el «CUMPLE /
  NO CUMPLE» de `aprobar/logica.ts:78-105` (D #1) pasa al servidor.
- Sílice corre en WebView2, el Chromium de Edge, con una CSP estricta.

### B.3 Mapa de navegación nuevo

La idea es pasar de una navegación por secciones a una por tareas. Una obra tiene tres superficies de trabajo, no 16
pantallas.

| Nivel | Hoy (DESIGN.md) | Propuesta B | Tarea que sirve |
|---|---|---|---|
| Entrada | Inicio: «Vista general» y «Pendientes» (dos subvistas) | **Inicio**, una sola pantalla: «Lo que bloquea» (la lista completa, no los 5 primeros) y «Obras», con el total por moneda y el avance | Saber por dónde empezar |
| Obra › 1 | Resumen, Tablero, Presupuesto (6 o 7 pestañas), Componer, Tramos, Archivos y planos, Mercado, Actualizar precios | **Presupuesto**: la tabla de partidas, el total fijo en la cabecera, la columna «Problemas» y un inspector lateral (APU de la partida, precios y cotizaciones, componer, tramos). «Traer datos» (plano, cómputo, lista de precios) es un menú de la cabecera | T1, T2, T3 |
| Obra › 2 | Control (con sus pestañas), Reajuste, Escenarios, Riesgo | **Ejecución al corte**: una página con la barra de corte (fecha, precios, factor de escalatoria y parte que no se reajusta) guardada en la URL, y debajo, con enlaces de salto, «Avance y valuaciones», «Valor ganado», «Alertas», «Reajuste», «Recuperación», «Riesgo» y «Escenarios» | Controlar la obra |
| Obra › 3 | Versiones, Aprobar, Revisar un paquete, Entregar | **Versiones y entregas**: la cadena de versiones como maestro-detalle (la lista a la izquierda y el detalle con «Ver cambios», «Pedir aprobación» y «Entregar» a la derecha) | Cerrar y entregar |
| Empresa | Auditoría (3 herramientas), Precios (4) y Producción (6) | **Auditar un libro** (un solo flujo: soltar el `.xlsx`, ver el libro y sus hallazgos, guardar el dictamen; el historial va debajo), **Precios y catálogo** y **Producción**, que se quedan como hoy | Auditar un libro Excel (A1 a A6) |
| Cuenta | Seis secciones | Igual | — |

La ruta lleva el estado que la persona espera conservar: la obra, la superficie, la partida elegida y el corte. Con eso,
«atrás» funciona y un cambio de vista no borra el filtro. Al cambiar de ruta, el foco va al `h1`, el título de la ventana
cambia y el anunciador dice el nombre de la pantalla. Guía `accessibility`: «Update single-page application (SPA) titles
during page transitions».

### B.4 Pantallas clave

**1. Presupuesto de la obra (T1, T2 y T3).**
- **Qué ve.** Arriba, fija, la cabecera de la obra: el nombre, el estado, la versión y el **total con su moneda**, con
  el valor exacto en un «toggletip». A su lado va un solo botón principal, el paso siguiente («Guardar versión» o «Pedir
  aprobación»). Debajo, la tabla de partidas: código, descripción, unidad, cantidad, precio y total, con las cifras a la
  derecha. A la derecha, la columna «Problemas (n)», con los hallazgos de la Revisión agrupados por causa y redactados
  por el servidor como «Qué pasa / Qué hacer». Al elegir un problema, el foco va a la celda o a la partida que lo causa.
  El APU de una partida se abre en el inspector, que no es modal.
- **Qué hace.** Lee el total sin cambiar de pestaña (T1). Edita celdas como en Excel: las flechas mueven, Enter o F2
  editan y Esc restaura. Abre una partida, agrega otra (pantalla 2) o recorre los problemas (T3).
- **Estados:**
  - cargando: el esqueleto de la tabla con la cabecera, sin cifras inventadas;
  - vacío: «Esta obra aún no tiene partidas», con «Agregar la primera partida» como principal y «Traer un cómputo
    (.csv)» como secundario;
  - error: el `AvisoError` con el detalle del servidor y «Reintentar», sin perder lo escrito;
  - parcial: las partidas sin precio llevan la fila afectada, y «Problemas» las cuenta;
  - éxito al guardar: la cabecera dice «Versión 4 guardada, con su fuente» y el principal pasa a «Pedir aprobación».
- **Guías.**
  - `responsive-table`: «Apply `position: sticky` to both column headers and row headers.»
  - `spatial-navigation`: «The spatial container must expose a single tab stop to sequential Page Tab navigation.»
  - `dialog`, regla 2, para el inspector: «Use for find bars, inspectors, palettes and compose panes that are still
    dialogs semantically.»

**2. Agregar o componer una partida (T2).**
- **Qué ve.** Al pie de la tabla, la fila «+ Partida», con un campo de búsqueda por código y descripción y las
  «parecidas» primero. Si la partida no existe, la última sugerencia dice «Componer «friso de pared»». Esa opción abre el
  inspector en modo «Componer», un panel no modal con «Cerrar» a la vista, donde se cargan los insumos con autocompletado.
  La cantidad se escribe en la propia fila, con `inputmode="decimal"`.
- **Qué hace.** Elige o compone la partida y escribe 50 en Cantidad. Hoy, en cambio, se abre un diálogo y encima un
  panel «en capa» con su propia trampa de foco (DESIGN.md, «Componer en panel»).
- **Estados:**
  - cargando: la búsqueda indica que está buscando sin una región viva (accesibilidad: no anunciar estados de espera);
  - vacío: «No hay partidas con ese texto», con «Componer «…»»;
  - error de un campo: aparece al salir del campo y el foco va al primero al confirmar;
  - éxito: la fila queda en la tabla con su cantidad, el foco queda en su celda Cantidad y el anunciador dice una vez
    «Partida agregada. Total actualizado».
- **Guías.**
  - `forms`: «DO use `inputmode` to optimize on-screen keyboards».
  - `accessible-error-announcement`: «after a failed submit, move focus to the first invalid field».
  - `dialog`: «DO include a visible close button in every non-modal dialog.»

**3. Auditar un libro (las alertas A1 a A6).**
- **Qué ve.** Una zona para soltar el archivo y, una vez soltado, el libro en el visor (Univer) a la izquierda y los
  hallazgos a la derecha, agrupados por causa raíz por omisión (como en A6). Cada hallazgo muestra su celda, la severidad
  con ícono y palabra, «Qué pasa» y «Qué hacer». El servidor manda esos dos campos con un código estable, así que la
  pantalla ya no parte la prosa con expresiones regulares (D #12 y #13).
- **Estados:**
  - cargando: el avance de la lectura con `<progress>`;
  - vacío: «Suelte aquí el libro .xlsx de la empresa»;
  - error: el detalle del servidor y «Elegir otro archivo»;
  - éxito: «N hallazgos en M causas», con «Guardar el dictamen» como principal.
- **Guías.**
  - `spinner`: «Using the native `<progress>` element as the semantic foundation.»
  - `accessibility`: «Don't use live regions for interstitial states».

**4. Ejecución al corte (controlar la obra).**
- **Qué ve.** La barra de corte con su botón «Calcular al corte». Debajo, en una sola página, las secciones con enlaces
  de salto, no pestañas: lo que hay que comparar va junto (UX-01). Las tablas tienen la frase de respuesta encima, los
  encabezados fijos y el apilado por contenedor cuando la ventana se estrecha. Las valuaciones son un maestro-detalle, y
  «Anular» pide confirmación en un `<dialog>` con el foco en «Cancelar».
- **Qué arregla.** El corte vive en la URL, así que no se pierde al ir y volver, que es el defecto confirmado de B #4.
- **Estados:**
  - sin línea base: «Declare primero la línea base de control», con su botón;
  - sin valuaciones: «Registre la primera valuación», con su botón;
  - error: el detalle del servidor y la barra intacta;
  - éxito: la frase de respuesta («Al 13/11/2026 la obra va 4,2 % atrasada») sobre cada tabla.
- **Guías.**
  - `responsive-table`: «Use `@container` queries instead of `@media` queries.»
  - `dialog`: «DO put `autofocus` on the safe action (such as Cancel or Keep) in a destructive confirmation.»

**5. Inicio.**
- **Qué ve.** «Lo que bloquea», con cada fila como enlace directo a la celda, la partida o el corte que lo causa, y
  «Obras» con su total por moneda (Bs y USD nunca se suman).
- **Estados:**
  - cargando: el esqueleto por bloque;
  - vacío sin obras: «Crear la primera obra»;
  - sin pendientes: «No tiene pendientes por hacer.»;
  - error de un bloque: su aviso, sin tumbar a los demás.
- **Guía.** `accessibility`: «Place all content within landmarks».

### B.5 Arquitectura del front

Las pantallas pasan a ser vistas puras: reciben datos ya validados y emiten eventos. Los datos viven en una **capa de
recursos** con caché por clave, `AbortController`, deduplicación e invalidación tras cada escritura. Se construye sobre
`pedir(ruta, { leer })`, con un analizador por recurso en la frontera. El 401 se resuelve una sola vez en
`api/cliente.ts`, y los errores llegan con un código estable, no con prosa. Cada flujo con pasos (guardar versión,
importar un plano, editar una sección, calcular al corte) es una **máquina de estado explícita**: una unión discriminada
y una función pura `siguiente(estado, evento)` en TypeScript, probada sin React. No se agregan dependencias: la capa de
recursos se escribe en casa, unas 200 líneas, sobre el modelo de `vial/useTramos.ts`. Una librería de caché ahorraría ese
código, pero `npm run dist` ya rechazó el Modal de Carbon por una URL en su archivo (RNF-22, `DialogoDeVersion.tsx:16`),
y una dependencia nueva corre el mismo riesgo. Las piezas de plataforma son pocas y comunes:
- `Dialogo`, sobre `<dialog>`;
- `Inspector`, sobre `<dialog popover="manual">` o el `PanelLateral` actual;
- `Anunciador`, una región `polite` y otra `assertive` para toda la aplicación;
- `MontoExacto`, sobre el `Toggletip` de Carbon;
- `CampoDeCifra`, con `inputmode="decimal"`, `:user-invalid` y `aria-invalid` sincronizado;
- `Grilla`, con `role="grid"`, tabindex itinerante y la edición con F2 o Enter.

Ninguna de estas decisiones de datos y estado sale de las 10 guías de Google, que no tratan ese tema. Se apoyan en
NORMAS (el servidor calcula) y en ub-mode («una decisión en un lugar»). La guía `accessibility` sí respalda el
anunciador único: «Many frameworks ship their own announcer abstraction — use it.»

```
 WebView2 (Chromium de Edge)
 ┌──────────────────────────────────────────────────────────────────────┐
 │ Rutas (hash): /obra/:carpeta/:id/{presupuesto|ejecucion|versiones}   │
 │   ?partida=…&corte=…&km=…&r=…   ← el estado que debe sobrevivir      │
 │        │                                                             │
 │        ▼                                                             │
 │ Vistas puras (JSX)  ──eventos──►  Máquinas de estado (TS puro)       │
 │        ▲                              │                              │
 │        │ datos validados              ▼ órdenes                      │
 │ Capa de recursos: caché por clave, AbortController, invalidación     │
 │        │  pedir(ruta, { leer: analizadorDelRecurso })                │
 │        ▼                                                             │
 │ api/cliente: CSRF, 401 → sesión (una vez), error {campo, codigo}     │
 │                                                                      │
 │ Piezas: Dialogo · Inspector · Anunciador · MontoExacto ·             │
 │         CampoDeCifra · Grilla      (vestidas con Carbon g10)         │
 └──────────────────────────────┬───────────────────────────────────────┘
                                ▼
          FastAPI (un proceso Uvicorn): cifras, veredictos, códigos
```

### B.6 ¿Se queda IBM Carbon?

**Sí.** Al presupuestista no le aporta nada visible cambiar de sistema. Carbon ya da densidad (tablas `sm` y `xs`), la
tipografía Plex, los tokens con contraste medido (`contrasteAviso.test.ts`) y el tema de la empresa. Migrar 51.000 líneas
costaría L y no resolvería ningún problema de los informes: los diálogos fallan porque se hicieron a mano, no por culpa
de Carbon.

Lo que sí cambia es la frontera. Para los overlays, la validación y los anuncios se usa el navegador (principio 1). Para
la tabla editable se usa una `Grilla` propia, porque el `DataTable` de Carbon con un `TextInput` en cada celda deja cada
celda como una parada de Tab: la matriz del Plan tiene cientos (A #11). Para leer se siguen usando `DataTable` y
`TablaDensa`.

Lo que se pierde es la anatomía exacta del `Modal` de Carbon (cabecera, pie y animación), que se imita con sus clases y
tokens.

### B.7 Costo por fases y riesgo

| Fase | Qué | Esfuerzo | Toca T1 a T3 |
|---|---|---|---|
| B0 | Base: `api/cliente` con 401 único y analizadores, capa de recursos, `Dialogo`, `Anunciador`, foco y título al navegar, `MontoExacto` y `CampoDeCifra`. Es la misma Fase 1 de la Propuesta A | M | Sí (diálogos de T2, total de T1) |
| B1 | Superficie Presupuesto: `Grilla`, columna «Problemas», inspector y componer en la fila | L | Sí, a fondo (T1, T2 y T3) |
| B2 | Auditar un libro como un solo flujo, con códigos del servidor en los hallazgos | M | No (sí las alertas A1 a A6) |
| B3 | Ejecución al corte en una página, con el estado en la URL | L | No |
| B4 | Versiones y entregas en maestro-detalle, e Inicio unificado | M | Inicio, sí (todas las tareas parten de ahí) |
| B5 | Redirigir las rutas viejas, retirar pantallas, actualizar el manual, las guías de ayuda y las guardias | M | Indirecto |

**Riesgo: alto.**
- B1 cambia la forma en que se hacen T1, T2 y T3. Los resultados del SUS de antes y de después no serían comparables, y
  habría que repetir la ronda completa.
- Cada página tiene entre 28 y 47 pruebas de comportamiento que se reescriben en parte.
- Hay que actualizar `comun/arquitectura.test.ts`, `guardiaInterfaz.test.ts` y `sinRutasAMano.test.ts`, el manual y los
  recorridos guiados.
- El calendario de la tesis (plan del consejo, 4 semanas) no tiene espacio para B1 ni B3 antes de defender.
- Los servidores de `aplicacion/` tendrían que devolver códigos estables (D #12 y #13), y eso requiere cambios en el
  backend.

### B.8 Qué se reutiliza del front actual

- `api/cliente.ts`, con su CSRF, ampliado.
- `indicadores/formatoEsVe.ts`.
- Carbon g10, los tokens y la tipografía.
- El visor Univer y su adaptador.
- `TablaDensa`, para leer.
- `PanelLateral`, como base del inspector.
- `FranjaDelPaso`, `EstadoVacio`, `AvisoError` y `EsqueletoPagina`.
- `CampoConBusqueda`, con su lógica extraída a un hook.
- Los modelos `vial/useTramos.ts` (capa de recursos) e `indices/SeriesViales.tsx` (formulario).
- La CSP.
- Las guardias de interfaz.
- La mayor parte de la lógica pura (`logica.ts`) y sus pruebas.

---

## Propuesta A: incremental

Son diez cambios, ordenados por su efecto en la persona. Cada uno es independiente y cabe en un PR.

### A1. Un solo diálogo modal sobre `<dialog>` y `showModal()`

- **Hoy.**
  - Seis diálogos de la Hoja son `div role="dialog"` con `position: fixed`, dos trampas de foco y dos políticas de Esc
    (A #1, #4 y #5: `DialogoDeVersion.tsx:25-34`, `DialogoDeGuardar.tsx:154-162`, `AgregarPartida.tsx:236-243` y
    `useDialogo.ts:177-183`).
  - Hay doce en todo `src` (B #3).
  - La confirmación de `Cuentas.tsx:68-141` declara `aria-modal` pero deja operables la barra lateral y la cabecera (C,
    fila 1).
- **Propuesta.**
  - Un componente `comun/Dialogo` sobre `<dialog>`, abierto con `showModal()`, con el título en `aria-labelledby` y
    `autofocus` en el primer campo o en «Cancelar» si la acción es destructiva.
  - Mientras se envía, un `cancel` con `preventDefault()` impide cerrarlo.
  - El CSS de la guía: `overscroll-behavior: contain` en `dialog:modal` y `::backdrop`.
  - Se borran `useDialogo`, `useAtraparFoco`, el `inert` manual y `devolverFocoA`.
  - Antes de migrar, una prueba de contrato común fija el foco inicial, Esc, el bloqueo durante el envío y el retorno del
    foco (plan, punto 1.3).
- **Guía `dialog`:** «DON'T add `role="dialog"`, `aria-modal`, a focus trap, `inert` toggling or an `Esc` handler.» y
  «DON'T write code to return focus on close. The browser returns it to the invoker.»
- **Con Carbon.** El `<dialog>` lleva las clases y los tokens de Carbon (la tipografía de encabezado, `Button` en el pie
  con el orden de Carbon: el secundario a la izquierda y el principal a la derecha, según UX-14). No usa el `Modal` de
  Carbon, que RNF-22 rechaza.
- **Baseline.** La guía no da el estado de `<dialog>` ni de `showModal()`. Las piezas que sí lo traen son `closedby`
  («Limited availability», Chrome y Edge 134) y `overscroll-behavior` («Limited availability», Chrome y Edge 144):
  progresivas, y en WebView2 actual funcionan. Las Invoker Commands (`command` y `commandfor`) son «Newly available»: se
  pueden usar en WebView2, o abrir con `showModal()` desde React, que es lo que se propone.
- **Esfuerzo:** M (la pieza es S; la migración de los 12 diálogos, M).
- **Toca T1 a T3:** sí, T2 («Agregar partida»). **Repetir el SUS.**

### A2. El valor exacto, a un clic y con coma (no en `title`)

- **Hoy.**
  - El valor exacto va en `title`, que solo ve el ratón, y además en un texto oculto repetido en cada cifra (A #15:
    `Cifra.tsx:8-12`, `EstadoDeFila.tsx:26,35`).
  - En varios sitios sale crudo, con punto decimal: «1250.5000» (B #5: `comun/TablaDensa.tsx:84-86`,
    `PanelDesglose.tsx:51`; D #34: `tablero/index.tsx:41`).
  - Hay 4 mecanismos distintos (D #6).
  - En el árbol hay 76 `title={` fuera de las pruebas (conteo propio con grep).
- **Propuesta.**
  - Un `comun/MontoExacto`: la cifra redondeada a la vista y un botón «i», un *toggletip*, que abre el exacto formateado
    con `formatoEsVe`, sin redondear y con coma.
  - En los totales (el de la cabecera, T1), el exacto va a la vista, en línea.
  - En las tablas, el exacto va en el detalle de la fila, no en cada celda.
  - El `title` desaparece de las cifras.
- **Guías.**
  - `accessibility`: «Don't use `title` as a naming mechanism: The value of this attribute is only displayed on mouse
    hover, and cannot be displayed or otherwise accessed using the keyboard in any browser.»
  - `interest-triggered-tooltips`: el toggletip es para información que la persona «may well want but most don't need
    every time, such as why a field is required, how a total was computed».
- **Con Carbon.** Se usa el `Toggletip` de `@carbon/react` (ya se usa `Tooltip` en `IndicadorFiori.tsx`), con su propio
  posicionamiento. No se usan `interestfor` ni `popover="hint"` nativos.
- **Baseline.** Las tres piezas nativas son «Limited availability» según la guía: las Interest invokers (Edge 149),
  `popover="hint"` (Edge 151) y el Anchor positioning (Edge 157, de noviembre de 2026). Por eso se queda Carbon, que no
  necesita respaldo.
- **Esfuerzo:** M.
- **Toca T1 a T3:** sí, T1 (el total). **Repetir el SUS.**

### A3. Validar al salir del campo, llevar el foco al primer error y no deshabilitar el principal

- **Hoy.**
  - Los formularios con `noValidate` no llevan el foco al primer campo inválido (B #8; C, fila 4).
  - El simulador marca errores mientras se escribe (D #20).
  - Hay botones principales deshabilitados para validar (B #22): en «Guardar versión», `disabled={motivo !== null || …}`
    (`DialogoDeGuardar.tsx:267`, lectura propia).
- **Propuesta.**
  - Un `comun/CampoDeCifra` y un ajuste en `CampoTexto`: estilo de error con `:user-invalid`, `aria-invalid="false"`
    hasta que el campo sea inválido, y el mensaje enlazado en `aria-describedby` solo mientras se muestra.
  - Un hook `useFocoEnPrimerError`, copiado de `indices/SeriesViales.tsx`.
  - En un formulario largo, un resumen de errores con un enlace a cada campo.
  - El principal queda habilitado y dice qué falta al pulsarlo. Después de un envío válido se deshabilita, para evitar el
    doble clic (UX-18).
- **Guías.**
  - `forms`: «DON'T disable submit buttons to block validation; let users submit and highlight errors.»
  - `accessible-error-announcement`: «Set `aria-invalid="false"` until `:user-invalid` matches, rather than leaving the
    attribute unset.»
  - `validate-input-after-interaction`: «DO say how to fix the error when you know how».
- **Con Carbon.** Se mantienen `invalid` e `invalidText` de los `TextInput` de Carbon. Esas propiedades las activa el
  estado «tocado» que da el mismo puente de `:user-invalid`; no se pinta un segundo borde propio.
- **Baseline.** `:user-invalid` es «Widely available» desde el 2023-11-02.
- **Esfuerzo:** M.
- **Toca T1 a T3:** sí, T2 («Agregar partida» y Componer). **Repetir el SUS.**

### A4. Un anunciador por página y nada de anuncios ruidosos

- **Hoy.**
  - `aria-live="polite"` está sobre el total, que cambia en cada pausa de 400 ms (A #16: `EstadoDelBorrador.tsx:30`).
  - Hay regiones vivas que envuelven tablas enteras (D #19: `actualizacion/index.tsx:299-312`,
    `escenarios/index.tsx:381-441`).
  - Hay anuncios dobles (C, fila 45).
  - Una cortina de 340 ms anuncia «Cargando…» sin que haya carga (E #15: `ModeTransitionOverlay.tsx:70`).
  - «Guardando la versión…» va en una región viva (`DialogoDeGuardar.tsx:210-212`, lectura propia).
- **Propuesta.**
  - Un `comun/Anunciador` con una región `polite` y otra `assertive` para toda la aplicación.
  - Las pantallas lo llaman con frases cortas: «Total actualizado», «Revaloración lista: 3 partidas cambiaron».
  - Se quitan las regiones del total, de las tablas y de la cortina.
  - Los anuncios se coordinan con la apertura de diálogos.
- **Guía `accessibility`:** «Centralize live regions for non-visible announcements» y «Don't use live regions for
  interstitial states like "Loading…" or "Updating…" unless they're meaningfully informative».
- **Con Carbon.** Las `InlineNotification` de Carbon conservan su `role`, y se quita el `aria-live` del contenedor que las
  envuelve.
- **Baseline.** Es ARIA, sin estado Baseline en la guía. Funciona en WebView2.
- **Esfuerzo:** S.
- **Toca T1 a T3:** sí, T1 (el total ya no se anuncia solo). **Repetir el SUS** junto con A1 a A3.

### A5. Al cambiar de pantalla: foco al `h1`, título y anuncio; y la navegación dentro de `<nav>`

- **Hoy.**
  - El foco solo pasa al `h1` si «se perdió». Al navegar con un enlace de la barra lateral, el lector de pantalla no se
    entera (E #5: `Marco.tsx:687-699`, `focoAlTitulo.ts:6-9`).
  - Con la barra lateral desplegada, las obras no están en un `<nav>` (E #6: `BarraLateral.tsx:141-146, 201-250`).
- **Propuesta.**
  - En cada navegación que no sea `REPLACE`: `document.title` con la pantalla primero, el foco al `h1` (`tabindex="-1"`)
    y una línea en el anunciador.
  - `<nav aria-label="Obras y espacios">` en las dos ramas de la barra.
- **Guía `accessibility`:** «Update single-page application (SPA) titles during page transitions» y «Use one `<main>`
  landmark per page».
- **Con Carbon.** No hay conflicto: el `h1` ya usa las clases de tipografía de Carbon.
- **Baseline.** HTML básico.
- **Esfuerzo:** S.
- **Toca T1 a T3:** sí, todas parten de la Vista general. **Repetir el SUS.**

### A6. Teclado en las tablas editables: `inputmode`, IME y una grilla de verdad en el Plan

- **Hoy.**
  - Solo «Cantidad» de Agregar partida lleva `inputMode="decimal"` (A #13; B #21; C, fila 41).
  - Enter se intercepta sin mirar `isComposing` (A #14: `CampoDeCelda.tsx:58-69`, `TablaEditable.tsx:145-154`).
  - La matriz del Plan pinta una caja de texto por celda, y cada una es una parada de Tab (A #11:
    `PestanaPlan.tsx:380-417`).
- **Propuesta.**
  - `inputMode="decimal"` en todas las cifras con coma, mediante `CampoDeCifra`.
  - `if (e.nativeEvent.isComposing) return;` al interceptar Enter.
  - En la matriz del Plan, `role="grid"` con tabindex itinerante: una sola parada de Tab, las flechas mueven entre
    celdas, y Enter o F2 editan (UX-06).
  - Dentro de una celda en edición, las flechas mueven el cursor. La guía manda no interceptarlas cuando el objetivo es
    editable.
- **Guías.**
  - `forms`: «DO use `inputmode` to optimize on-screen keyboards» y «DO check `KeyboardEvent.isComposing` before
    treating the `Enter` key as a submit action».
  - `spatial-navigation`: «Roving tabindex only works with screen readers when the container and items have appropriate
    composite-widget roles and states (e.g. grid/gridcell, listbox/option)».
- **Con Carbon.** Las celdas siguen siendo `TextInput` `sm` de Carbon dentro de la grilla. Lo nuevo es el contenedor.
- **Baseline.** `inputmode` y `isComposing` son HTML y DOM básicos. `checkVisibility()`, que usa el algoritmo de la
  guía, funciona en Chromium.
- **Esfuerzo:** M.
- **Toca T1 a T3:** sí, T2 (la cantidad 50 se escribe en una celda). **Repetir el SUS.**

### A7. Tablas: encabezados fijos, `th scope` y apilado por contenedor

- **Hoy.**
  - La tabla del desglose de Componer no tiene `<thead>` ni `<th scope="row">` (B #23: `PanelDesglose.tsx:45-57`).
  - Las tablas de Control y de Mercado pierden el contexto al desplazarse. Solo la Vista general apila por contenedor
    (DESIGN.md, «Vista general», punto 3).
- **Propuesta.**
  - `position: sticky` en `thead` y en la primera columna (`tbody th`).
  - `th scope="col"` y `th scope="row"`.
  - Un envoltorio con `role="region"`, `tabindex="0"` y nombre.
  - Apilado con `@container` y etiquetas en `::before` en las tablas que viven en el panel lateral.
- **Guías.**
  - `responsive-table`: «Apply `position: sticky` to both column headers and row headers.»
  - `accessibility`: «Do use the `scope` attribute on `<th>` elements».
- **Con Carbon.** Se usa `TableHeader scope="row"` de Carbon y el `sticky` sobre `DataTable`, con el fondo
  `--cds-layer` en la celda fija.
- **Baseline.** La guía no da el estado de `sticky` ni de `@container`. Los dos funcionan en el Chromium de WebView2.
- **Esfuerzo:** S-M.
- **Toca T1 a T3:** sí, T2 (el desglose de Componer). **Repetir el SUS.**

### A8. Rendimiento: diferir lo que está bajo el pliegue, después de medir

- **Hoy.** Hay tablas sin tope ni paginación: la matriz del Plan (A #11), el histórico de precios (B #16:
  `HistoricoDePrecios.tsx:29-36`), el catálogo (D #21: `catalogo/index.tsx:58-77`) y una `TablaDensa` por tramo (D #29).
- **Propuesta.**
  - Medir con un caso grande y ficticio antes de tocar.
  - Luego, `content-visibility: auto` con `contain-intrinsic-size: auto none auto <alto estimado>` en las filas o los
    bloques que están fuera de la primera pantalla.
  - En el catálogo, además, `useDeferredValue`.
  - Después, probar el recorrido con el teclado.
- **Guía `defer-rendering-heavy-content`:** «You MUST pair `content-visibility: auto` with `contain-intrinsic-size`.» y
  «Test linear navigation across off-screen boundaries using keyboard alone.»
- **Con Carbon.** Se aplica con clases propias (`.silice-fila-diferida`) sobre filas de `DataTable`, sin tocar Carbon.
- **Baseline.** `content-visibility` es «Newly available» (Chrome y Edge 108). En WebView2 funciona. Donde no lo hay, se
  ignora y solo se pierde la ganancia.
- **Esfuerzo:** M.
- **Toca T1 a T3:** no.

### A9. Esperas que se ven: texto en el botón y un spinner que respeta el movimiento reducido

- **Hoy.** «Generar escenario» y «Calcular la mejora» solo se deshabilitan, sin texto ni indicador: un cálculo de unos
  segundos parece un botón roto (D #23: `escenarios/index.tsx:373`, `riesgo/MejoraDeLaEstimacion.tsx:143`).
- **Propuesta.**
  - El botón dice «Generando…» y lleva al lado el `InlineLoading` de Carbon.
  - En una espera larga de una página entera, `<progress>` sin `value`.
  - Con `prefers-reduced-motion`, el giro se hace más lento en vez de detenerse.
  - Nada de esto va en una región viva.
- **Guía `spinner`:** «Using the native `<progress>` element as the semantic foundation» y «Slow down the animation
  significantly rather than stopping it entirely, so the user still knows that the process is active.»
- **Con Carbon.** Para las acciones se queda `InlineLoading`. El `<progress>` nativo, vestido con los tokens de Carbon,
  solo se usa si hace falta una espera de página.
- **Baseline.** `@property` es «Newly available». `background-clip: border-area` es «Limited availability» (Edge 150), y
  la guía da como respaldo `mask-image`.
- **Esfuerzo:** S.
- **Toca T1 a T3:** no.

### A10. Confirmar lo irreversible y no perder el foco

- **Hoy.**
  - «Anular» una valuación se hace con un clic (B #11: `PestanaValuaciones.tsx:401-408`).
  - «Descartar escenarios» se hace con un clic (D #25: `escenarios/index.tsx:413-423`).
  - El foco cae en `body` al confirmar o cancelar «Revocar» (C, fila 5: `ClavesApi.tsx:208-222`) y al cerrar el detalle
    del Historial (D #18).
- **Propuesta.**
  - Confirmación con el `Dialogo` de A1: el botón `danger` nombra la consecuencia («Anular la valuación n.º 7») y el foco
    inicial va a «Cancelar».
  - El detalle del Historial pasa al panel lateral, que devuelve el foco.
- **Guías.**
  - `dialog`: «DO put `autofocus` on the safe action (such as Cancel or Keep) in a destructive confirmation.»
  - `accessibility`: «Manage focus correctly to and from updated content».
- **Con Carbon.** `Button kind="danger"` y el orden de Carbon.
- **Baseline.** Igual que A1.
- **Esfuerzo:** S.
- **Toca T1 a T3:** no.

### Ficha de pantalla 1: diálogo «Guardar versión» (Presupuesto)

1. **Historia de trabajo.** Cuando termino de cambiar el presupuesto, quiero dejar una versión con la fuente del cambio,
   para poder pedir su aprobación y saber que lo de hoy no se pierde.
2. **De dónde viene y a dónde va.** Viene de la línea de estado del Presupuesto («N cambios sin guardar»). Va a «Pedir
   aprobación», el principal de la cabecera, con el foco en él.
3. **Quién la usa y qué sabe.** El presupuestista que domina el oficio y la persona nueva. «Fuente del cambio» lleva un
   ejemplo («Acta de obra n.º 12 del 20/11/2026»), y la explicación larga va en «¿Qué es esto?».
4. **Camino crítico.** Leer el resumen y el total, escribir la fuente y guardar. Lo ocasional: revisar la lista de
   cambios, o resolver un conflicto de versión.
5. **Tipo de vista y pregunta.** Formulario de captura corto, en un modal (UX-23). Responde: «¿Qué voy a guardar y con
   qué respaldo?».
6. **Reparto de controles.**
   - A la vista (4): el total, con el exacto en línea; «Fuente del cambio»; «Cancelar»; «Guardar versión».
   - En «Ver los N cambios» (plegado): la lista de cambios y «Responsable: …», con la frase «Se guardan todos los
     cambios; responsable: <usuario>».
7. **Punto de partida.** La fuente se propone vacía, pero ofrece las últimas fuentes usadas en la obra, para reconocer en
   vez de recordar (UX-05).
8. **Tabla de estados.**

   | Estado | Qué ve | Paso siguiente |
   |---|---|---|
   | Abierto | El resumen, el total y la fuente con el foco | «Guardar versión» |
   | Fuente vacía al pulsar | El error bajo el campo: «Escriba la fuente del cambio, por ejemplo un acta»; el foco en el campo | Escribirla |
   | Enviando | El botón dice «Guardando la versión…»; Esc y Cancelar bloqueados con `cancel`; sin región viva | Esperar |
   | Versión más nueva | Aviso «Hay una versión más nueva», con «Abrir la versión V», «Recargar el borrador» y «Guardar de todos modos» (`danger`) | Elegir una opción |
   | Error del servidor | El detalle tal cual; lo escrito queda | «Guardar versión» de nuevo |
   | Éxito | El diálogo se cierra; la cabecera dice «Versión 4 guardada»; el anunciador lo dice una vez | El foco en «Pedir aprobación» |
   | Sin permiso | El botón no aparece; la línea de estado dice «Solo lectura» | — |

   El aviso de error ocupa un espacio reservado sobre la fila de botones. Así no empuja «Cancelar» ni «Guardar» bajo el
   puntero. Guía `dialog`: «DON'T let the confirmation move controls under the pointer.»
9. **Supuestos de negocio.** Que la fuente sea obligatoria en toda versión que no sea solo un desglose sale del código
   actual (`motivoParaNoGuardar`). Tiene que confirmarlo Eugenio.
10. **Pruebas que lo fijan.**
    - Abre con `showModal()`.
    - El foco inicial está en «Fuente del cambio».
    - Esc cierra, salvo mientras se envía.
    - Con la fuente vacía, el botón está habilitado y al pulsarlo el foco va al campo.
    - Un 422 no borra la fuente.
    - Tras el éxito, el foco queda en «Pedir aprobación».
    - Hay 8 controles o menos a la vista.
    - El `h1` del diálogo existe y es único dentro de él.

### Ficha de pantalla 2: resultados de Control al corte

1. **Historia de trabajo.** Cuando llega una valuación, quiero ver al corte cómo va la obra contra el plan y qué alertas
   hay, para poder decidir si reproyecto o propongo una recuperación.
2. **De dónde viene y a dónde va.** Viene de «Valuaciones» (registrar la del mes). Va a «Recuperación: elegir una
   opción», o a «Reajuste» si los precios subieron.
3. **Quién la usa y qué sabe.** El ingeniero de control y el economista. El factor de escalatoria (Km) y la parte que no
   se reajusta (R) son jerga: cada uno lleva su palabra, un ejemplo («1,15») y la ayuda a pedido.
4. **Camino crítico.** Elegir el corte, calcular y leer la frase de respuesta y las alertas. Lo ocasional: los precios
   revalorados, Km, R y la fuente.
5. **Tipo de vista y pregunta.** Tabla de resultados. Responde: «¿Cómo va la obra al <corte>?», con la frase («Va 4,2 %
   atrasada y 1,8 % sobre el costo») encima de cada tabla.
6. **Reparto de controles.**
   - A la vista (3): «Fecha de corte», «Calcular al corte» y los enlaces de salto a las secciones.
   - En «Más opciones»: «Precios actualizados al corte», «Versión revalorada», Km, R y «Documento que los respalda», con
     la frase «Sin precios revalorados; sin escalatoria. Cambiar».
7. **Punto de partida.** El último corte calculado. El corte vive en la URL (`?corte=…&km=…&r=…`), así que ir a otra
   sección y volver lo conserva (corrige B #4).
8. **Tabla de estados.**

   | Estado | Qué ve | Paso siguiente |
   |---|---|---|
   | Cargando | El esqueleto de las tablas bajo la barra, que sigue a la vista | — |
   | Sin línea base | «Declare primero la línea base de control» | «Declarar la línea base» |
   | Sin valuaciones | «Registre la primera valuación para ver el control» | «Registrar una valuación» |
   | Error | El detalle del servidor bajo la barra, con lo escrito intacto | «Calcular al corte» |
   | Éxito | La frase de respuesta, las tablas con encabezados fijos y las alertas con ícono y palabra | «Recuperación: elegir una opción» (`FranjaDelPaso`) |
   | Sin permiso | El aviso «Sin permiso» como único `h1` | — |

9. **Supuestos de negocio.** Que «corte vacío» equivalga a «la última valuación» sale de la etiqueta actual. Que la
   frase use porcentajes con un decimal es una decisión de presentación por confirmar con Eugenio.
10. **Pruebas que lo fijan.**
    - «El corte sobrevive al cambiar de sección»: la prueba que hoy falta (B #4).
    - La frase de respuesta precede a cada tabla.
    - Con Km o R mal escritos, el error sale al salir del campo y el foco va al primero al calcular.
    - Los controles a la vista son 8 o menos.
    - El éxito muestra el paso siguiente.

### Orden de aplicación de A y las pruebas de cada fase

El orden es coherente con el plan del front: primero la base común (puntos 1.1 a 1.6), y en cada paso una prueba en rojo
antes del código.

| Fase | Cambios | Qué la fija |
|---|---|---|
| 0 | Ninguno: fijar el comportamiento | La prueba de contrato del diálogo (foco inicial, Esc, bloqueo durante el envío, retorno del foco), corrida contra los 12 diálogos actuales; la prueba de que el corte sobrevive al cambiar de pestaña |
| 1, la base | Las piezas `Dialogo` (A1), `Anunciador` (A4), `MontoExacto` (A2), `CampoDeCifra` y `useFocoEnPrimerError` (A3), y el foco y el título al navegar (A5). Va junto con los puntos 1.1 (401 único) y 1.4 (`useConsulta`) del plan | Pruebas unitarias de cada pieza; axe (`vitest-axe`, que hoy no está en `package.json`) en las piezas |
| 2 | Migrar las pantallas: primero las de T1 a T3 (la cabecera del Presupuesto, Agregar partida, Componer y Guardar versión) y después el resto. Incluye A10 | La prueba de contrato en verde en cada diálogo migrado; «un error no borra nada» (UX-12); el éxito con paso siguiente |
| 3 | Tablas y teclado (A6 y A7) | Pruebas con `user-event`: una sola parada de Tab en la grilla, las flechas mueven, Enter con `isComposing` no salta de fila, `th scope` presente |
| 4 | Rendimiento y esperas (A8 y A9) | Medición antes y después con un caso ficticio grande; el recorrido de la grilla con el teclado; el giro lento con movimiento reducido |
| 5 | Medir otra vez | Ronda de 5 personas y SUS, porque las fases 1 a 3 cambian T1 y T2 |

## Lo que NO se recomienda

- **`interestfor` y `popover="hint"` para los valores exactos.** La guía los da como «Limited availability» (Edge 149 y
  151). El Anchor positioning, que necesitan para quedar pegados a la cifra, es de Edge 157 (noviembre de 2026). En
  WebView2 dependería de que el runtime ya esté en esa versión. El `Toggletip` de Carbon resuelve lo mismo hoy.
- **`:user-valid` con borde verde.** La guía lo ofrece como opcional, pero DESIGN.md prohíbe el «verde por ser
  positivo», y el verde en Sílice es variación IBCS.
- **`closedby="any"` (cerrar al tocar fuera) en los diálogos con datos.** Un clic fuera perdería la fuente escrita. Se
  deja el cierre por omisión (Esc) y se cuida el cambio no guardado en `cancel`, como manda la guía: «Keep the
  unsaved-changes guard in a `cancel` handler, not in `closedby="none"` alone».
- **El apilado en tarjetas de la guía de tablas para la tabla de partidas.** El presupuestista compara filas como en
  Excel. El apilado solo sirve en el panel lateral y en la Vista general.
- **Atajos de una letra (`h`, `j`, `k`, `l`) en la grilla.** La guía lo desaconseja: «Avoid adding single-character
  shortcuts».
- **`content-visibility` en la primera pantalla o en la tabla de partidas de una obra pequeña.** Retrasa lo que se ve
  primero.
- **El spinner con `conic-gradient` de la guía como pieza nueva.** Carbon ya trae `InlineLoading`, y un spinner propio
  sería una segunda pieza para lo mismo.
- **Botones de 48 px en todo el escritorio.** Contradice la densidad de Sílice (24 a 32 px). Se cumple el mínimo de
  24 px y se sube a 48 solo con `@media (pointer: coarse)`.

## Contradicciones entre las guías de Google y las reglas del proyecto

| # | Guía de Google | Regla del proyecto | Qué se propone |
|---|---|---|---|
| 1 | `dialog` y `accessibility`: `<dialog>` nativo con `showModal()` | Carbon es el sistema de diseño, pero su `Modal` lo rechaza RNF-22 (`DialogoDeVersion.tsx:16`), así que hoy los diálogos se hacen a mano | No hay conflicto real con Carbon: un `<dialog>` vestido con sus clases y tokens. Se pierde la anatomía exacta del `Modal` |
| 2 | `accessibility`: «Don't use `title` as a naming mechanism… cannot be… accessed using the keyboard» | DESIGN.md: el exacto «a un toque, en el tooltip accesible». En el código, 76 `title={`, algunos con punto decimal. `mercado/Cifras.tsx:6-8` dice lo contrario (B #5): dos decisiones opuestas | El exacto en un `Toggletip`, o en línea en los totales, siempre con `formatoEsVe` (A2) |
| 3 | `dialog`: «DO use a level-1 heading for the main heading in modal dialogs» | DESIGN.md:343: «En cada sección: un solo h1». Los diálogos de hoy usan `h2` | `h1` dentro del diálogo. La guardia y las pruebas cuentan los `h1` fuera de un `dialog[open]`. **Lo decide Eugenio** |
| 4 | `validate-input-after-interaction`: «DO optionally use `:user-valid` to give a green "success" indicator» | DESIGN.md, «Prohibido»: «verde por ser positivo» | No usar `:user-valid` |
| 5 | `spinner`: con movimiento reducido, girar más lento, «rather than stopping it entirely» | DESIGN.md, «Movimiento»: `prefers-reduced-motion: reduce` «quita incluso esas transiciones» | El spinner no es decorativo: se hace la excepción de girar lento. **Lo decide Eugenio** |
| 6 | `forms`: «DO ensure tap targets are at least `48px`» frente a `accessibility`: «at least 24x24 CSS pixels» | DESIGN.md: filas de 24 px y tablas `sm` de 32 px; 48 px solo donde la ruta lo pide. UX-17: 24 px | 24 px de mínimo (WCAG 2.5.8) y 48 px con `pointer: coarse` |
| 7 | `forms`: «Expose 2 to 5 mutually exclusive options as visible radio buttons» | UX-09: botones de opción «hasta cuatro» | Diferencia menor. Se queda UX-09 y se acepta 5 si la quinta es la omisión |
| 8 | `spatial-navigation`: «The spatial container must expose a single tab stop» | UX-06: «Tab va a la derecha», como en Excel | En la matriz del Plan, una parada y las flechas (A6). En «Partidas», **decidirlo con la medición**: Tab como en Excel o una parada. Se registra para Eugenio |
| 9 | `spinner`: el `<progress>` nativo como base | Carbon `InlineLoading` | Se queda `InlineLoading` en las acciones; `<progress>` solo en las esperas de página |
| 10 | `dialog`: el botón destructivo «first in a right-aligned row» para que no se mueva nada | UX-14: en un modal, el secundario a la izquierda y el principal a la derecha | Son compatibles: «Guardar de todos modos» va a la izquierda de la fila sin desplazar «Cancelar» ni el principal, en un espacio reservado |

## Recomendación

**Una mezcla, en este orden:**

1. **Después de medir, y en todo caso, la base común:** la Fase 1 de A, que es la misma B0. Corrige defectos que nadie
   discute (el foco, los anuncios, el punto decimal en `title`, el filtro de Control) sin cambiar la forma de las tareas,
   y deja las piezas que B también necesita. Luego, las fases 2 a 4 de A.
2. **De la Propuesta B, solo lo que la medición pida.** Si en T3 las personas no encuentran «Revisión», se adelanta la
   columna «Problemas» del Presupuesto. Si en T2 se traban con el diálogo y el panel en capa, se adelanta «componer en la
   fila con el inspector». Si nadie se traba, no se toca la forma.
3. **La Propuesta B completa, después de defender la tesis.** Su riesgo es alto, cuesta L en B1 y B3, y cambia T1 a T3:
   invalidaría la comparación del SUS dentro del calendario del consejo.

Todo esto se aplica después de la medición con personas. Si un cambio toca T1, T2 o T3, se repite el SUS con la misma
ronda de 5 personas.

### Modern Web Guidance

- **`accessibility`**: el valor exacto sale del `title` y pasa a un `Toggletip` de Carbon, porque el `title` no llega al
  teclado («Don't use `title` as a naming mechanism»). También respalda un anunciador único para toda la aplicación, en
  vez de regiones sueltas («Centralize live regions for non-visible announcements»).
- **`accessible-error-announcement`**: `aria-invalid="false"` desde el inicio y foco al primer error al enviar, también
  en los formularios con `noValidate` («Set `aria-invalid="false"` until `:user-invalid` matches, rather than leaving
  the attribute unset.»).
- **`defer-rendering-heavy-content`**: se mide antes de diferir y no se aplica a la tabla de partidas ni a la primera
  pantalla, solo a las filas bajo el pliegue y siempre con su tamaño estimado («You MUST pair `content-visibility: auto`
  with `contain-intrinsic-size`.»).
- **`dialog`**: se borran las trampas de foco y los manejadores de Esc, en vez de unificarlos («DON'T add
  `role="dialog"`, `aria-modal`, a focus trap, `inert` toggling or an `Esc` handler.»). En Propuesta B, el inspector y
  Componer son diálogos no modales de la regla 2, no un modal sobre otro modal («Use for find bars, inspectors, palettes
  and compose panes that are still dialogs semantically.»).
- **`forms`**: el botón principal deja de deshabilitarse para validar, contra el patrón actual de «Guardar versión»
  («DON'T disable submit buttons to block validation; let users submit and highlight errors.»).
- **`interest-triggered-tooltips`**: el valor exacto es un toggletip y no un tooltip, porque es algo que se quiere a
  veces y no un detalle prescindible. Se usa el de Carbon, porque las piezas nativas son «Limited availability» («information users may well want but most don't need every time,
  such as why a field is required, how a total was computed»).
- **`responsive-table`**: encabezados fijos de fila y de columna en las tablas de resultados, y apilado por contenedor
  solo en el panel lateral, no en la tabla de partidas («Apply `position: sticky` to both column headers and row
  headers.»).
- **`spatial-navigation`**: la matriz del Plan pasa de cientos de paradas de Tab a una sola, con flechas; dentro de una
  celda en edición no se interceptan las flechas («The spatial container must expose a single tab stop to sequential
  Page Tab navigation.»).
- **`spinner`**: con movimiento reducido el indicador gira lento en vez de desaparecer, aunque choca con DESIGN.md y lo
  decide Eugenio («Slow down the animation significantly rather than stopping it entirely, so the user still knows that
  the process is active.»).
- **`validate-input-after-interaction`**: el error aparece al salir del campo, y se descarta a propósito el verde de
  `:user-valid` por la regla IBCS del proyecto («DO use `:user-invalid` to apply error styling only after
  interaction.»).
