# Pulido F5 del front: plan corto

Rama `feature/f5-pulido` (base `83989afe`, cabeza de F4, PR #101). Cuatro puntos que el cierre de F4 dejó para F5
(`docs/bitacora/2026-11-03-cierre-f4.md`, «Pasada de navegador y arreglos», y la decisión 6 de la Tarea 9 en
`docs/planes/PLAN_REDISENO_F4.md`). Una tarea por punto, cada una con su rojo por aserción en un commit y el arreglo en
otro. Sin tocar `core/`, `aplicacion/hoja.py`, `aplicacion/composicion.py` ni `asistente/experimento`; sin navegador.

## Tarea 1. El código al componer, con búsqueda guiada

Eugenio no es experto: el «Código» de Componer es texto libre y le resulta ambiguo (pidió autocompletado guiado, como
MaPreX, el 2026-10-21). Y en «Agregar partida», una descripción escrita en «Partida» se ofrece como código.

- **Archivos.** `paginas/componer/CampoDelCodigo.tsx` (nuevo: el campo con búsqueda, su regla de formato y su ayuda),
  `paginas/componer/codigo.ts` (nuevo: `esCodigoValido`, `pareceCodigo`, textos), `paginas/componer/ComponerPartida.tsx`
  (usa el campo; `descripcionInicial`; no deja guardar con un código mal formado), `paginas/componer/Guardar.tsx`
  (`codigoInvalido`), `paginas/hoja/AgregarPartida.tsx` y `paginas/hoja/ComponerEnPanel.tsx` (componer con una
  descripción: el panel abre con ella y el código vacío).
- **Búsqueda.** El campo es `comun/CampoConBusqueda` con dos grupos: las partidas del catálogo
  (`GET /v1/buscar/partidas`, la misma búsqueda de «Partida») y las partidas viales de Sílice
  (`GET /v1/consulta/partidas_viales`). Elegir deja el código; si «Descripción» o «Unidad» están vacías, las llena con
  las de la partida del catálogo elegida. Sigue valiendo escribir uno propio («Usar «X» como código»).
- **Formato.** Un código empieza por letra o cifra y sigue con letras sin tilde, cifras, punto, guion o guion bajo, sin
  espacios, hasta 64 (el `PATRON_CODIGO` de `api/esquemas_ola2.py` sin el espacio). Mal formado: el campo lo dice en
  rojo con el porqué y el ejemplo, y «Guardar composición» espera. La ayuda está siempre a la vista.
- **Pruebas.** `componer/CampoDelCodigo.test.tsx` (sugerencias de los dos grupos, elegir, propio, formato),
  `componer/codigo.test.ts`, `componer/ComponerPartida.test.tsx` (guardar espera con un código mal formado) y
  `hoja/AgregarPartida.test.tsx` (una descripción abre el panel con «Descripción» llena y «Código» vacío). Las de
  `componer/index.test.tsx` se conservan sin cambios.
- **Criterios.** Rojo por aserción visto antes del cambio; `componer/index.test.tsx` intacto y verde; «Z-99» y
  «OBRA-99» siguen componiéndose con su código.

## Tarea 2. Cerrar Componer con un solo Esc (H6)

Hoy, desde el panel, hacen falta tres Esc para volver al presupuesto: el panel, el texto de «Partida» (lo usado para
componer contaba como elegido y Esc lo borraba) y el diálogo. Y un Esc dentro de un campo de Componer con algo escrito
cierra el panel y pierde lo compuesto.

- **Archivos.** `paginas/hoja/ComponerEnPanel.tsx` (el Esc del panel), `comun/CampoConBusqueda.tsx`
  (`valorPropio.esEleccion`), `paginas/hoja/AgregarPartida.tsx`, `frontend-desktop/DESIGN.md` («Panel lateral»).
- **Regla.** Fuera de un campo (título, botones, tablas), un Esc cierra el panel y el foco vuelve a «Partida». Dentro de
  un campo de texto cuyo valor cambió desde que entró el foco, el primer Esc lo restaura (como las celdas de la Hoja) y
  el segundo cierra. Con una lista de sugerencias abierta, Esc la cierra primero, como siempre. Lo usado para componer
  no cuenta como elegido: de vuelta en «Partida», el Esc siguiente cierra el diálogo.
- **Pruebas.** `hoja/AgregarPartida.test.tsx`: un Esc desde el título; desde un campo sin cambios; restaurar y cerrar
  desde un campo con cambios; del panel al presupuesto en dos Esc.
- **Criterios.** Rojo por aserción; la prueba vieja «Esc cierra el panel sin guardar…» sigue igual.

## Tarea 3. «Aprobar una versión» sin desborde con letra «Muy grande» (H10)

La pasada midió 1576 px a 1056 y 1366 con «Muy grande». La misma causa que H4: rejillas sin columna declarada que toman
el ancho mínimo de la tabla más ancha.

- **Archivos.** `paginas/aprobar/aprobar.scss`.
- **Pruebas.** `paginas/aprobar/estilosAprobar.test.ts` (nuevo): con la hoja compilada con Sass, cada rejilla de la
  página (`.silice-aprobar`, `__envio`, `__panel`, `__lista`, `__rastro`) declara `grid-template-columns: minmax(0, 1fr)`.
- **Criterios.** Rojo por aserción; la página no tiene ninguna rejilla sin columna que ceda.

## Tarea 4. El texto de la mesa en el servidor (H9)

`aplicacion/mesa.py` dice «Abrir la Hoja»; el cliente lo corrige en `textoDeLaAccion`.

- **Archivos.** `aplicacion/mesa.py` (`ABRIR_EL_PRESUPUESTO`, `AGREGAR_LA_PRIMERA_PARTIDA`), `aplicacion/hoja_partidas.py`
  (importa la constante renombrada), `frontend-desktop/src/paginas/pendientes/logica.ts` (fuera `TEXTOS_AL_DIA` y
  `textoDeLaAccion`), `paginas/obras/logica.ts`, `paginas/obras/index.tsx`, `paginas/pendientes/Bandeja.tsx`.
- **Pruebas (pytest).** `tests/unit/test_mesa.py` (la acción dice «Abrir el presupuesto»; una obra sin versión dice
  «Agregue la primera partida»), y los oráculos con el texto viejo en `test_api_hoja_partidas.py`,
  `test_api_obras_pendientes_todas.py`, `test_api_obras_resumen.py` y `test_pendientes_todas.py`. En el front, las
  pruebas de lo que se ve (Resumen, Bandeja, `obras/logica.test.ts`) pasan a recibir el texto nuevo del servidor y siguen
  diciendo «Abrir el presupuesto».
- **Criterios.** Rojo por aserción en pytest; `docs/api.json` regenerado y reproducible (dos veces, mismo hash).

## Decisiones

Formato: pregunta · lo que se hizo · cómo cambiarlo.

### Tarea 1

1. **Qué cuenta como código en «Agregar partida».** · Lo escrito con forma de código y con alguna cifra («Z-99»,
   «OBRA-99», «C-000.000.001»); «zanja», «Excavacion» o «excavación de zanja» son descripciones: la opción dice «Componer
   una partida nueva con la descripción «…»» y el panel abre con «Descripción» llena y «Código» vacío. · `pareceCodigo`
   en `paginas/componer/codigo.ts` (p. ej. quitar la exigencia de la cifra).
2. **La forma del código.** · El `PATRON_CODIGO` del servidor (`api/esquemas_ola2.py`) sin el espacio: el código de una
   partida con espacios se confunde con una descripción. Solo en el cliente; el servidor no cambia. · `FORMA_DEL_CODIGO`
   en `codigo.ts`.
3. **Cuándo se reclama el formato.** · Mientras se escribe el campo es una búsqueda (se puede buscar «excavación»): el
   error sale al dejar el campo y, mientras el código esté mal formado, «Guardar composición» espera con la nota «Para
   guardar, corrija el código de la cabecera…». Con el error a la vista Carbon cambia la ayuda por el error, así que el
   error trae su propio ejemplo y cómo buscar. Uno mal formado no se ofrece «tal cual». · `revisado` en
   `CampoDelCodigo.tsx`; `codigoInvalido` en `Guardar.tsx`.
4. **Dónde se busca.** · En las partidas del catálogo (la búsqueda de «Partida», sin filtrar por tipo de obra, para no
   proponer un código que ya existe en otro) y en las partidas viales de Sílice. Elegir del catálogo llena «Descripción» y
   «Unidad» solo si están vacías (y carga sus tablas, como al teclear un código que existe). Si una de las dos búsquedas
   falla, la otra se ofrece igual; un 401 cierra la sesión. · `buscadorDeCodigos` en `CampoDelCodigo.tsx`.
5. **Pregunta para Eugenio: proponer un código libre nuevo.** · No se propone el siguiente código libre de una serie
   (haría falta una ruta del servidor que lo calcule); el campo propone los códigos que ya existen y deja escribir uno
   propio con forma de código. · Una ruta `GET /v1/composicion/codigo-libre` y un grupo más en `buscadorDeCodigos`.
6. **Un selector de `componer/index.test.tsx`.** · En «un dato mal escrito no borra el último desglose», dos
   `getByLabelText("Código")` pasan a `getByRole("combobox", { name: "Código" })`: con las sugerencias abiertas, la lista
   también se llama «Código». No cambia ninguna aserción. En `ComponerPartida.test.tsx` cambió el texto esperado de la
   ayuda del código (ahora dice también cómo se busca). · —
7. **Rojo (`671fc402`).** · 20 fallas, todas de aserción: `expected true to be false` (la regla, con un esbozo que todo
   lo acepta), `Unable to find an accessible element with the role "combobox" and name "Código"`, `Unable to find
   role="option" and name "Componer una partida nueva con la descripción «excavación de zanja»"` y
   `toHaveAccessibleDescription` / `toHaveValue` sin el valor esperado. · —
