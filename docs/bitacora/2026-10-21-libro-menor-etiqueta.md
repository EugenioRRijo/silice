# Libro menor en verde, con etiqueta que no se puede ignorar (V-16, 2026-10-21)

Rama `inc/ruta-s2-mig-adm-empresa`. Decisión de Eugenio (2026-10-21): el libro menor que Sílice se queda en verde (V-16), pero un libro que omite costos
también sale menor y el verde puede significar «libro incompleto». Se añade una etiqueta pegada a la cifra. Todo ficticio (fixtures de `tests/fixtures/libros_empresa.py`).

## Qué sabe el comparador (investigación)

- El libro se compara con Sílice solo por **totales** (`fusion.proceso`: `totales_libro` contra `totales_silice`). No hay un cotejo partida a partida entre el libro
  y un original: una partida que falta por completo en el libro no tiene contraparte y nadie la ve.
- Sí queda un rastro **estructurado** de costos omitidos: la regla **L4** (`adapters/hoja_empresa/reglas.py`, «Componente fuera del total»): el costo directo de un APU
  deja fuera un componente (H1: el CD sin equipos) o no es la suma de sus componentes, y dice cuánto queda corta la partida. Cada hallazgo L4 trae como `celda` la
  del CD del APU (`APU-02!G36`) y cada partida conoce su `hoja_apu`; con eso se obtiene el número de partida sin leer el texto del hallazgo.
- No se usa L2 «partida sin APU»: no explica un libro menor (Sílice no puede recalcular esa partida y no mueve el total).
- Conclusión: la etiqueta es **informativa con datos** cuando hay L4 y **fija sin números** cuando no los hay. Una lista vacía NO prueba que el libro esté completo, y la
  etiqueta fija lo dice. No se tocó `core/` ni `seguridad/` (`git diff -- core/ seguridad/` vacío).

## Qué se hizo

**API** (`api/rutas/libros.py`, `docs/api.json`): campo aditivo `partidas_con_omision: list[int]` en `LibroAuditadoRespuesta` (números de partida con un L4, ordenados y
sin repetir), función `partidas_con_omision(resultado)`. Pruebas: libro con H1 da `[2]` (y su Δ es negativo); libro limpio y sobreprecio dan `[]`; un libro menor
**sin** L4 (P guardado de APU-01 = 14) da `[]` y no inventa nada. El contrato del historial (`test_la_respuesta_solo_suma_el_aviso_al_contrato`) suma el campo.

**Frente** (`frontend-desktop/src/indicadores/`):

- `esLibroMenor(delta, sentido)` (`ibcs.ts`): solo `sentido: "exactitud"` con delta negativo distinto de cero.
- `EtiquetaLibroMenor.tsx`: nota (`role="note"`) con ícono `WarningAltFilled` y texto. Con datos: «Libro menor: revise si omite N partidas (n.º 2, 5)» (las cinco
  primeras y «y K más»; espacio duro tras «n.º»). Sin datos: «Libro menor: puede deberse a partidas omitidas; revise antes de aceptar».
- `IndicadorFiori` la pone **dentro de la tarjeta, bajo la cifra y la variación**, y la suma al nombre accesible del grupo («Total general. Libro menor: …»). Sin botón de
  cierre, sin tooltip, sin clic. Aparece solo con libro menor: no con libro mayor, igual, ni con sentido costo o rendimiento.
- `FranjaIndicadores` y `Visor.tsx` (una línea) llevan `partidas_con_omision` de la API; `src/api/tipos.ts` la declara opcional (una API anterior no la trae y entonces sale
  la etiqueta fija).
- Forma distinta del verde simple: fondo `--silice-aviso-fondo` (yellow-10), franja de 4 px `--silice-aviso-borde` (yellow-50) e ícono de advertencia; texto en la tinta
  normal. Contraste calculado en `contrasteIbcs.test.ts`: texto 16,4:1 sobre el fondo (AA exige 4,5); franja e ícono 3,02:1 sobre el fondo de la etiqueta, 3,33:1 sobre
  blanco y 3,03:1 sobre gray-10 (WCAG 1.4.11, 3:1). Sin hexadecimales a mano: los dos tokens nuevos son colores de Carbon en `src/estilos/tokens.scss`.
- Impresión y colores forzados: `print-color-adjust: exact` y, con `forced-colors: active`, borde propio.
- `DESIGN.md`: patrón «etiqueta de advertencia pegada».

**Defecto previo hallado y corregido** (era de esta zona y dejaba la etiqueta sin cifra al lado): con el tamaño de letra **Muy grande** la tarjeta del indicador era una
rejilla de dos columnas y la variación («favorable Δ -154,28 (-3,54 %)») dejaba **0 px** a la columna del título y la cifra: no se veían (ni siquiera con el libro limpio).
En Normal 1366 la cifra salía cortada («4.203,…»). Ahora cada par (título y meta; cifra y variación) es una fila flex que baja de línea si no cabe
(`.fiori-kpi__fila`), y la franja pasa de alto fijo de 4 rem a **alto mínimo** de 4 rem para que crezca lo que pida la etiqueta. Medido: cifra, título y variación sin
recorte en Normal, Grande y Muy grande, 1366 y 1056.

## Dónde se exporta o imprime el indicador (y la acción de aceptar)

- Búsqueda en `frontend-desktop/src` y en la API: **el indicador del libro no se exporta ni se imprime desde ningún sitio.** La interfaz no llama a `/v1/libros/devolucion`
  (el `.xlsx` calcado de la API trae las hojas AUDITORÍA, TRAZABILIDAD y ALERTAS, no los indicadores) ni hay `window.print` ni estilos de impresión. Por eso la
  etiqueta no tiene a dónde «salir»; lo que se hizo es que, si el navegador imprime la pantalla, el fondo y la franja se conservan (`print-color-adjust`). No se inventó una
  exportación nueva.
- No hay acción de aceptar, continuar o entregar basada en este indicador en el Visor de libros (la página «Entregar» trabaja con la versión de la Hoja, no con la auditoría
  del libro). No se creó un acuse artificial: la propia etiqueta es el acuse (siempre visible, sin bloquear nada).
- Si Eugenio quiere que el informe de auditoría descargable (Excel o PDF) lleve la etiqueta, hay que añadir el indicador al informe: es una decisión de contenido de
  `adapters/` (hoja AUDITORÍA), fuera de esta zona; queda como deuda.

## Medición en el navegador (Chromium 151 por DevTools, Node 22; API en 127.0.0.1:8000 con `SILICE_DATOS` temporal; fixtures ficticias)

Tres libros: con H1 (Δ −3,54 %, L4 en la partida 2), menor sin L4 (P de APU-01 = 14) y limpio. Normal, Grande y Muy grande, a 1366×768 y 1056×768.

- Ninguna corrida desborda (`scrollWidth == clientWidth`); la etiqueta queda dentro de su tarjeta (3 de 3), la letra de la etiqueta mide 14 px (Normal), 17,5 (Grande) y 21 (Muy
  grande); cifra, título y variación sin elipsis en las 18 combinaciones (3 tamaños, 2 anchos, 3 libros).
- Coste en altura, que Eugenio debe conocer: la franja pasa de 75 px (libro limpio, Normal 1366) a 138 px con la etiqueta de datos y 111 con la fija; a 1056 y Muy grande
  llega a 231 y 277 px, y el panel de la hoja se queda en 243 y 197 px de alto. Es el precio de una etiqueta que se lee completa a la letra más grande. Alternativa si pesa:
  la etiqueta solo en «Total general» (no en subtotal e IVA, que siempre salen menores a la vez); no se hizo porque el encargo pide la etiqueta en cada indicador verde.
- No verificado: lector de pantalla real (solo el nombre accesible calculado por Testing Library), impresión real a papel o PDF, Firefox y Edge.

## Pruebas

Rojo visto: API (3 pruebas, `KeyError: 'partidas_con_omision'`), `EtiquetaLibroMenor` (módulo inexistente), contraste y estilos (5 fallas), cableado del Visor (1 falla al quitar la
línea) y disposición (1 falla antes del SCSS). Conteos de la corrida final en el informe de la sesión.
