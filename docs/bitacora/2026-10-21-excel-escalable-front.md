# Hoja de Excel escalable, frente (2026-10-21)

Decisión de Eugenio (2026-10-21): la hoja de Excel de la pantalla (Univer 1.0.3, visor del libro de la empresa) debe ser escalable: (A) seguir el control «Tamaño de
letra» (Normal 100 %, Grande 125 %, Muy grande 150 %) y (C) llevar además un control propio de zoom fino. Rama `inc/ruta-s2-mig-adm-empresa`. Solo `frontend-desktop/src/visor/`
y esta bitácora. Todo ficticio (el libro de la medición es `tests/fixtures/libro_visual.py`).

## Qué se hizo

- **API de Univer verificada en el paquete instalado** (no supuesta): `FWorksheet.zoom(razon)` y `getZoom()` (facade de `@univerjs/sheets-ui`), que ejecuta
  `sheet.command.set-zoom-ratio`; la facade recorta a 0,1 a 4 (el comando y la barra de Univer admiten 10 a 400 %). El zoom es **por hoja** (`worksheet.getConfig().zoomRatio`); un
  cambio solo redibuja la hoja activa y las demás lo toman al activarse. Univer trae su propia Ctrl + rueda (`SheetsZoomRenderController`, pasos de su propio cálculo), que se
  intercepta en captura para que haya una sola fuente de zoom.
- **Fórmula:** `zoom_efectivo = zoom_propio × factor` (factor 1, 1,25 o 1,5, leído de `dataset.siliceLetra`). Tope de Univer: 4. Con 300 % propio y «Muy grande» (4,5) el lienzo
  se dibuja a 400 % y el control lo dice («la hoja se dibuja al 400 % por el tamaño de letra (tope del lienzo)»).
- **Lógica pura** `zoomHoja.ts`: rango 50 a 300, paso 10, `ajustarZoom`, `factorDeLetra`, `razonEfectiva`, lectura y guardado en `localStorage` con clave propia
  `silice.zoom-hoja` (todo en try/catch; sin almacenamiento la hoja va al 100 %; solo se escribe cuando el usuario cambia el zoom, mostrar el control no escribe nada),
  `pasoDeRueda` (un gesto de ratón da un paso; un pellizco de trackpad acumula).
- **`useZoomHoja(visor)`**: estado del zoom propio, factor vigilado con un `MutationObserver` sobre `data-silice-letra` (cambio en vivo, sin recargar), y un efecto que le pide al
  visor la razón (`HojaVisor.fijarZoom`). **`useAtajosZoom(seccion, lienzo, acciones)`**: Ctrl + rueda sobre el lienzo (captura, no pasivo, `preventDefault` + `stopPropagation`),
  y Ctrl + «+» / «=» / «-» / «0» solo con el foco dentro de la sección de la hoja (el listener vive en la sección: con el foco fuera no se intercepta nada y el zoom del navegador queda
  intacto).
- **`ControlZoomHoja`** en la fila de las pestañas de la hoja: grupo «Zoom de la hoja», `−`, valor «100 %» en `<output role="status" aria-live="polite">`, `+` y «Restablecer»
  (botones de ícono de Carbon con nombre accesible y tooltip). En los topes el botón lleva `aria-disabled` (no `disabled`) para no perder el foco al llegar con el teclado. Si lo dibujado
  difiere del zoom propio (factor de letra o tope), el estado lo dice con texto oculto, no solo con el número.
- **Adaptador** (`adaptadorUniver.ts`): `crearHojaUniver(contenedor, libro, zoomInicial)`, `fijarZoom(razon)` (todas las hojas) y `zoomActual()`. `HojaVisor` y `CrearHojaVisor` ganan esos
  miembros; `hojaFalsa` los implementa. `UniverGrid` recibe `zoomInicial` por ref (solo cuenta al crear; los cambios llegan por `fijarZoom`, el lienzo no se recrea, así que no se
  pierden selección, desplazamiento ni hoja activa).
- **Estilos** (`visor.scss`): `.visor__pestanas` (fila flex; las pestañas de Carbon ceden con `min-inline-size: 0` y desplazan por dentro; el control `flex: none`), `.zoom-hoja`,
  `.zoom-hoja__valor` (cifras tabulares), botón en su tope apagado con `--cds-text-disabled`. Sin hexadecimales a mano, sin transiciones propias (`prefers-reduced-motion` ya es global en `app.scss`).

## Dos fallos hallados al medir (no los veían las pruebas de jsdom)

1. **La razón pedida al abrir se perdía** (medido: con `silice.zoom-hoja=200` el lienzo salía a 100 %, y al pulsar «−» saltaba a 190 %). Univer deja la escena sin acercamiento tras armarse o
   redimensionarse aunque la configuración de la hoja diga otra cosa. Arreglo: el adaptador guarda la razón vigente y, en cada aviso de cambio (desplazamiento, comando, redimensión),
   compara con `scene.getAncestorScale()` y la vuelve a pedir si difiere. Verificado en el navegador (tabla de abajo).
2. **Los atajos nunca se enganchaban** (rojo en `Visor.test.tsx`): la sección y el lienzo aparecen cuando el libro termina de cargar, después del primer render, y los efectos con `ref.current`
   corrían con `null`. Ahora los elementos son estado (`ref={setSeccionHoja}`) y el efecto depende de ellos.

## Medición en navegador real

Chromium 151 de `ms-playwright` por el protocolo DevTools con Node 22 (sin instalar nada); perfil propio en el scratchpad; API `uvicorn` en `127.0.0.1:8010` (el 8000 lo tenía otro proceso ajeno, no se tocó)
con `SILICE_DATOS` temporal y el caso ficticio OF-001; cuenta `ana`; libro `libro_visual.xlsx` (PORTADA y PRESUPUESTO, Arial 10). Alto 768. Cierre por PID (API y Chromium), sin dejar puertos 8010 ni 9334 abiertos.
La escala dibujada sale de la posición de la barra azul del título dentro del propio canvas (proporcional al acercamiento: cabeceras y primera fila por la escala), no de lo que dice el estado.

| Ancho | Letra | Zoom propio | Esperado | Medido (eje Y / X) | Lienzo (px) | Texto de celda (px)* | Desborde horizontal de la página | Solape |
|---|---|---|---|---|---|---|---|---|
| 1366 | Normal | 100 | 1 | 1,000 / 1,000 | 693 x 440 | 13,3 | no (1366/1366) | no |
| 1366 | Normal | 300 | 3 | 3,000 / 3,000 | 693 x 440 | 40,0 | no | no |
| 1366 | Grande | 100 | 1,25 | 1,250 / 1,277 | 898 x 359 | 16,7 | no | no |
| 1366 | Grande | 300 | 3,75 | 3,750 / 3,769 | 898 x 359 | 50,0 | no | no |
| 1366 | Muy grande | 100 | 1,5 | 1,500 / 1,508 | 819 x 277 | 20,0 | no | no |
| 1366 | Muy grande | 300 | 4 (tope; sin tope 4,5) | 4,000 / 4,000 | 819 x 277 | 53,3 | no | no |
| 1056 | Normal | 100 | 1 | 1,000 / 1,000 | 418 x 440 | 13,3 | no (1056/1056) | no |
| 1056 | Normal | 300 | 3 | 3,000 / 3,000 | 418 x 440 | 40,0 | no | no |
| 1056 | Grande | 100 | 1,25 | 1,250 / 1,277 | 633 x 359 | 16,7 | no | no |
| 1056 | Grande | 300 | 3,75 | 3,750 / 3,769 | 633 x 359 | 50,0 | no | no |
| 1056 | Muy grande | 100 | 1,5 | 1,500 / 1,508 | 633 x 277 | 20,0 | no | no |
| 1056 | Muy grande | 300 | 4 (tope) | 4,000 / 4,000 | 633 x 277 | 53,3 | no | no |

\* Calculado como 13,33 px (Arial 10 pt del libro) × la escala medida; el canvas no expone el tamaño del texto. El eje X difiere hasta 2,8 % del Y por el redondeo del ancho de las cabeceras de Univer; el Y es exacto.

En los doce casos: `scrollWidth == clientWidth` del documento, un solo `h1`, cero `role="alert"` vacíos, el canvas dentro de su lienzo, el control de zoom dentro de la sección de la hoja, las pestañas
sin solapar el control (a 1056 con Muy grande la pestaña «PRESUPUESTO» queda truncada con la flecha de desplazamiento de Carbon, por diseño), los tres botones sin solaparse entre sí (37, 47 y 56 px
de lado), la fila de pestañas sin desborde propio. **Desplazamiento** (rueda vertical y Mayús + rueda) mueve la hoja en los doce casos. **Selección**: un clic en el centro del lienzo dibuja la caja
azul de selección sobre el punto del clic en los doce casos. **Foco**: los tres botones reciben el foco, con el anillo de Carbon (`box-shadow` de 2 px; `outline: none`) y dentro de la ventana, en los doce casos.

**Atajos** (1366, Normal): Ctrl + rueda arriba 100 → 110, abajo → 100; Ctrl + «+» con el foco en un botón de la hoja → 110; Ctrl + «-» → 100; Ctrl + «0» → 100; Ctrl + «+» con el foco en el botón
«Normal» de la cabecera (fuera de la hoja) → el zoom propio no cambia (100). **Cambio en vivo** (con una celda seleccionada, sin recargar): Normal → Grande → Muy grande → Normal dio 1,25, 1,5 y 1,0 (eje Y),
el `<canvas>` es el mismo nodo (`mismoLienzo: true`) y la selección sigue dibujada (810, 197 y 628 píxeles azules; con Muy grande la caja queda recortada por el borde visible).

## Pruebas

Commits: `48649931` (lógica, hooks, control, `HojaVisor`) y `a4f3a35e` (integración en el visor, adaptador, estilos). Archivos nuevos: `zoomHoja.test.ts` (8 pruebas), `ControlZoomHoja.test.tsx` (7), `useZoomHoja.test.tsx` (13); ampliados: `Visor.test.tsx` (+5) y `visor.estilos.test.ts` (+4). `npx vitest run src/visor`: 11 archivos, 180 verdes. `npx vitest run src` completo: 130 archivos, 1899 verdes (386 s, con la máquina cargada por otros frentes). `npx eslint .` limpio, `tsc -b --noEmit` limpio, `npm run build` limpio, `npm run dist`: 161 archivos, 14 043 803 bytes, sin URLs externas. Rojo visto: `zoomHoja`, `ControlZoomHoja` y las cinco de `Visor.test.tsx` (cinco rojas antes de integrar; la de los atajos siguió roja por el fallo 2). No se vio rojo aparte en `useZoomHoja.test.tsx` ni en las de estilo (se escribieron junto con su implementación en el mismo paso).

## Hallazgos y no verificado

- **Lienzo bajo con letra grande (preexistente, fuera de esta tarea):** sobre la hoja hay una banda de unos 190 px (cabecera de la página, barra de fecha y archivo, franja de indicadores vacía) que a 768 de alto deja el lienzo en 440, 359 y
  277 px con Normal, Grande y Muy grande. Es utilizable (se desplaza, se selecciona), pero con Muy grande y zoom alto se ve poco a la vez. Si Eugenio lo quiere más amplio, hay que ajustar esa cabecera de la página (no es del visor).
- **Tope de Univer:** 300 % con «Muy grande» queda en 400 % (no 450 %). Si se quisiera más, no se puede con `FWorksheet.zoom` (la facade recorta a 4).
- No se probó con lector de pantalla, ni Firefox ni Edge, ni con el zoom del navegador combinado; Chromium sin cabeza no aplica el zoom del navegador a eventos de teclado sintéticos, así que «no pisar el zoom del navegador» se verificó por `preventDefault`
  (prueba unitaria) y por el valor del zoom propio, no viendo al navegador acercar.
- El texto de las celdas no se pudo leer del canvas; los píxeles de la tabla son cálculo sobre la escala medida. Las capturas están en el scratchpad (`zoom\run2`).
- El adaptador de Univer no tiene prueba de jsdom (Univer no dibuja allí): lo cubre la medición en navegador; el arreglo de «razón perdida» se verificó con la medición antes y después.

## Ronda 1 del árbitro (devuelto: A1, A2, A3 MAYOR; A5, A6 MENOR)

Commits: `56b573f4` (A3 y A5) y `38a44645` (A1, A2 y A6).

- **A1, lo dibujado ahora se ve.** `ControlZoomHoja` muestra con texto visible, bajo el valor, «dibujado 125 %» (letra Grande o Muy grande) y «dibujado 400 % (tope)» (tope de Univer); el
  lector de pantalla sigue oyendo la frase completa en un texto oculto (el visible va `aria-hidden` para no leerlo dos veces). «Acercar» queda con `aria-disabled` también cuando subir no
  cambiaría lo dibujado (`puedeSubirZoom`: con Muy grande, de 270 % en adelante la razón ya es 4), y el hook lo respeta también por atajo. Medido a 1366 y 1056, Muy grande: «dibujado 150 %» con zoom 100 y
  «dibujado 400 % (tope)» con 300; texto de 21 px; Normal no muestra nada de más; sin desborde de página (1366/1366 y 1056/1056), sin solape entre pestañas y control; a 1056 con Muy grande y 300 % las
  pestañas se estrechan a 233 px y desplazan con sus flechas.
- **A2, rojo visto con mutaciones en un árbol ajeno** (`scratchpad\mut`: copia de `frontend-desktop` con `node_modules` por junction, fuera del repositorio; cada mutación se aplica y se restaura allí).
  `useZoomHoja.test.tsx`: sin `observe` del `MutationObserver` rojas las dos de cambio en vivo (hook y `Visor.test`); sin `disconnect` roja la de desmontaje; en lote (M3 a M12) 13 pruebas rojas: sin
  `preventDefault` de las teclas, rueda sin filtro de Ctrl, teclas en `document` (sin filtro de foco de la sección), sin quitar el oyente de teclado ni el de rueda, sin guardar, sin `deltaMode`, subir
  sin `puedeSubir`, sin pedirle la razón al visor, rueda sin captura. `visor.estilos.test.ts`: sin `min-inline-size: 0` en las pestañas, sin cifras tabulares, sin `cursor: not-allowed`, con un color a mano,
  sin `nowrap` en lo dibujado, sin `flex: none` y sin columna: rojas (4 más 1 de la mutación del color a mano; cada mutación del lote queda atribuida por el nombre de la prueba roja). Pruebas de desmontaje nuevas:
  `disconnect` del observador, `removeEventListener("keydown")` en la sección y `removeEventListener("wheel", …, { capture: true })` en el lienzo, y que tras desmontar ni la tecla ni la rueda llaman a las acciones.
- **A3, el reintento ya no puede ciclar.** La decisión vive en `debeReaplicarZoom` (pura, con prueba: escala igual, distinta, sin render, NaN, infinita y tope alcanzado) con `MAX_REINTENTOS_ZOOM = 3` por racha; `fijarZoom` reinicia
  el contador y una escala igual lo reinicia también. Medido en navegador con un build instrumentado fuera del repositorio (`scratchpad\inst`, con un contador de `aplicarZoom` y un modo que ejecuta el comando pero deja
  una escala que nunca iguala): un pedido de zoom da exactamente 4 aplicaciones (la pedida y 3 reintentos), 0 al desplazar durante 2 s y 0 en 3 s de reposo; con el contenedor de tamaño 0 (real) 1 aplicación y 0 en reposo.
- **A5:** `pasoDeRueda(acumulado, delta, deltaMode)` normaliza líneas (x40) y páginas (x800); prueba con el caso de Firefox (±3 líneas).
- **A6:** reindentado el `<div className="visor__pestanas">` de `Visor.tsx` sin cambiar conducta.

Verificación final de la ronda: `npx vitest run src`: 130 archivos, 1922 pruebas, 1915 verdes y 7 agotadas por la carga de la máquina (Administracion, Sensibles, Elaborar, Edicion, EdicionApu, HojaExcel); los seis
archivos reejecutados aislados: 142 verdes. `npx eslint src/visor` y `tsc -b --noEmit` limpios (`eslint .` marca un espacio irregular en `src/indicadores/EtiquetaLibroMenor.tsx`, de otro frente); `npm run build` y `npm run dist`
limpios (161 archivos, 14 044 965 bytes, sin URLs externas).
