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

### Tarea 2

1. **A qué valor vuelve el primer Esc.** · Al que tenía el campo al recibir el foco: en Componer no hay un valor
   «aceptado por el servidor» como en las celdas de la Hoja, y ese es el análogo (deshace lo escrito en esa visita). Vale
   para todo campo de texto del panel (cabecera, condiciones, filas de insumos, justificación); las listas desplegables y
   los botones cierran de una vez. · `alEntrar` y `alEsc` en `paginas/hoja/ComponerEnPanel.tsx`.
2. **Quién atiende Esc.** · El contenedor del panel, en la fase de captura, antes que el campo y que `PanelLateral`: así un
   «Código» con lo elegido no se borra antes de cerrar (habría sido otro Esc). Con la lista de sugerencias abierta deja
   pasar la tecla para que se cierre la lista. Solo lo que nace dentro del panel en el DOM: el Esc de «Precios distintos…»
   sigue siendo de su diálogo. `PanelLateral` no cambia: en las demás secciones su Esc es el de siempre. · Quitar
   `onKeyDownCapture` del contenedor.
3. **De vuelta en «Partida».** · Lo que se usó para componer ya no cuenta como elegido (`valorPropio.esEleccion: false`,
   prop nueva de `CampoConBusqueda`, `true` por omisión): el Esc siguiente cierra el diálogo, sin el paso intermedio de
   borrar el texto. Del panel al presupuesto quedan dos Esc, uno por capa visible (panel y diálogo). Lo escrito en el
   diálogo (cantidad, cálculo, nota) se pierde al cerrarlo, como antes con el tercer Esc. · `esEleccion: false` en
   `AgregarPartida.tsx`.
4. **Lo que preocupa.** · Restaurar el «Código» es como escribirlo: sus sugerencias se vuelven a buscar y, a los 300 ms,
   se abren otra vez (un Esc las cierra). Restaurar usa el `set` nativo del valor y un evento `input` para que React lo
   lea; si React cambiara su manera de seguir el valor, la prueba de restaurar lo notaría. · —
5. **Rojo (`d9f3f862`).** · Tres fallas de aserción: `expected <div role="dialog" …> to be null` (el segundo Esc borraba
   el texto de «Partida» y el diálogo seguía) y dos `expected null not to be null` (el primer Esc en un campo con cambios
   cerraba el panel). Pasaba ya «en un campo sin cambios, un solo Esc cierra el panel», que fija lo que no cambia. · —

### Tarea 3

1. **Qué rejillas.** · Las cinco de la página, no solo `section.silice-aprobar__envio` (la sospecha del cierre de F4): la
   de la página es la que toma el ancho de la tabla de partidas, y las de dentro lo heredarían. La prueba recorre toda regla
   con `display: grid` del CSS compilado, así que una rejilla nueva sin columna la hace caer. La tabla ya se desplazaba en
   su caja (`.silice-tabla`, `overflow-x: auto`). · Quitar `grid-template-columns` de `aprobar.scss`.
2. **Sin medida de navegador.** · El arreglo es el de H4, que la re-medida de F4 confirmó en Mercado; la medida de
   «Aprobar una versión» con «Muy grande» queda para la próxima pasada de navegador. · —
3. **Rojo (`0613d28b`).** · `expected [ '.silice-aprobar', '.silice-aprobar__envio, .silice-aprobar__panel',
   '.silice-aprobar__lista', '.silice-aprobar__rastro' ] to deeply equal []`. · —

### Tarea 4

1. **Dónde dice «Agregue la primera partida».** · Es la acción (`siguiente`) de una obra en elaboración sin ninguna versión
   guardada: el Resumen dice «Siguiente paso: Agregue la primera partida» y su botón lleva al Presupuesto, donde está
   «Agregar la primera partida». No se puso en `que_pasa`, que es «Te falta:» con fondo de precaución y describe un estado,
   no un paso. Una obra con versión guardada sigue con «Abrir el presupuesto». · `_EN_BLANCO` en `aplicacion/mesa.py`
   (o `que_pasa` con la acción «Abrir el presupuesto»).
2. **El nombre de la constante.** · `ABRIR_LA_HOJA` pasa a `ABRIR_EL_PRESUPUESTO` (lo importa también
   `aplicacion/hoja_partidas.py`); se suma `AGREGAR_LA_PRIMERA_PARTIDA`. · —
3. **La corrección del cliente.** · Se fueron `TEXTOS_AL_DIA` y `textoDeLaAccion` (`paginas/pendientes/logica.ts`): el
   Resumen y la bandeja pintan el texto del servidor tal cual. Las pruebas de lo que ve la persona (`Resumen.test.tsx`,
   `Bandeja.test.tsx`, `pasoDeLaObra`) siguen pidiendo el botón «Abrir el presupuesto», ahora con el texto nuevo del
   servidor en su respuesta simulada; la prueba de la función quitada se fue con ella y entra una de la obra en blanco.
   Los escenarios inyectados de `test_pendientes_todas.py` y `test_api_obras_pendientes_todas.py` (datos de prueba, no
   texto del servidor) también dicen «Abrir el presupuesto», y `FranjaDelPaso.test.tsx` usa el mismo texto. · —
4. **`docs/api.json`.** · No cambia: el texto de la acción no está en el esquema. Regenerado dos veces con
   `scripts/exportar_openapi.py`: el mismo hash que el del repositorio (`13740494…736c8`). · —
5. **Visto y no tocado.** · `paginas/vial/Tramos.tsx` tiene un enlace «Abrir la Hoja de la obra» (el módulo vial, fuera
   de la mesa y de este punto). · Cambiar el texto y su prueba en `Tramos.test.tsx`.
6. **Rojo (`70b5241f`).** · Seis fallas de aserción: `texto: 'Abrir la Hoja' != 'Agregue la primera partida'` (la obra
   en blanco) y `Siguiente(texto='Abrir la Hoja', …) != Siguiente(texto='Abrir el presupuesto', …)` en `test_mesa.py`,
   `test_api_hoja_partidas.py` y `test_api_obras_resumen.py`. Para que el rojo fuera de aserción y no un
   `AttributeError`, el commit del rojo trae el esbozo `ABRIR_EL_PRESUPUESTO = ABRIR_LA_HOJA`. · —

## Tanda 2

Cinco defectos que encontró quien escribió el manual nuevo al describir el programa. Mismo método: una tarea por
punto, el rojo por aserción en un commit y el arreglo en otro, con los mismos límites de la tanda 1. Las decisiones van
al final, en «Decisiones de la tanda 2».

### Tarea 5. El CSV del cómputo con coma decimal

«Cargar cómputo» (`POST /computos/{dominio}`) pide punto decimal y columnas separadas por coma, al revés de la regla de
Eugenio (coma decimal y punto de miles en toda cifra); el CSV de tramos ya acepta la coma. Los lectores están en
`adapters/{civil,telecom,industrial,sistemas}/`, fuera del núcleo.

- **Regla (la de Excel en español).** Si la cabecera separa con punto y coma, las cifras van con coma decimal y punto de
  miles («1.234,56»), leídas con `aplicacion.cifras.cifra_escrita`, el único intérprete de la regla; si separa con coma,
  todo sigue como hoy (punto decimal), para no romper los archivos que ya existen.
- **Archivos.** `aplicacion/computo_csv.py` (nuevo: pasa un CSV con `;` a la forma de siempre, solo en las columnas
  numéricas del adaptador), `api/rutas/computos.py` (lo llama antes del adaptador), cada adaptador declara
  `COLUMNAS_NUMERICAS`, `paginas/archivos/CargarComputo.tsx` y `logicaComputo.ts` (la ayuda del formato) y los README
  de `data/samples/`.
- **Pruebas.** `tests/unit/test_computo_csv.py` (oráculos a mano: «1.234,56» → 1234.56; un archivo con `;` y otro con
  `,`; «2.5» con `;` se rechaza con el archivo, la fila y la columna), `tests/integration/test_api_computo_coma_decimal.py`
  (las cuatro muestras reescritas con `;` y coma decimal dan los mismos ítems que las de siempre) y
  `archivos/CargarComputo.test.tsx` (la ayuda se ve).
- **Criterios.** Rojo por aserción; `core/` y las muestras con coma sin cambios.

### Tarea 6. El pendiente «Entregar» lleva a donde se entrega

«Entregar» (una versión aprobada y sin entregar) lleva a Aprobaciones, que no tiene cómo entregar; «Entregar paquete»
solo se abre con Ctrl+K.

- **Archivos.** `paginas/aprobar/index.tsx` (y una pieza nueva para el bloque de la entrega).
- **Regla.** Dentro de la obra, Aprobaciones ofrece «Entregar paquete» (lleva a la pantalla `entregar`, con la obra ya
  elegida) a la cuenta que puede usar esa pantalla (`entregar_paquete`); a las demás no. El pendiente sigue llevando a
  Aprobaciones de su obra: la ruta de la obra es la que cambia de carpeta y fija la obra.
- **Pruebas.** `paginas/aprobar/EntregarDesdeAprobaciones.test.tsx` con el marco entero y el permiso real (`ACCIONES`
  de `datosDePrueba`, como `mercado/QuienRevisa.test.tsx`): quien arma va del pendiente a Aprobaciones y de ahí a
  «Entregar paquete»; quien revisa no ve el enlace.
- **Criterios.** Rojo por aserción.

### Tarea 7. Textos viejos: «Hoja de la obra» y «barra superior (Proyecto)»

- **Archivos.** `paginas/vial/Tramos.tsx` («Abrir la Hoja de la obra», «a la Hoja de la obra», «Guarde una en la
  Hoja»), `aplicacion/hoja_vial.py` (los avisos del servidor al llevar los tramos), `paginas/reajuste/index.tsx` (cómo se
  elige hoy una obra) y la guardia `paginas/sinJergaInterna.test.ts`.
- **Pruebas.** `sinJergaInterna.test.ts` caza «Hoja de la obra» y «barra superior (Proyecto)»; `vial/Tramos.test.tsx`,
  `vial/AvisoDeLlevar.test.tsx` y `reajuste/Reajuste.test.tsx` con el texto nuevo; en pytest, los avisos de
  `aplicacion/hoja_vial.py` dicen «Presupuesto».
- **Criterios.** Rojo por aserción en vitest y en pytest.

### Tarea 8. El recorrido de la auditoría dice lo que hace la pantalla

El paso 2 («Lea el resumen y los hallazgos», pantalla «Libro de la empresa») dice «Descargue el libro devuelto si lo
necesita», y el visor no tiene esa descarga.

- **Archivos.** `shell/recorrido.ts`.
- **Pruebas.** `shell/recorrido.test.tsx`: el paso 2 no pide descargar y dice cómo se ve la celda de un hallazgo.
- **Criterios.** Rojo por aserción.

### Tarea 9. Quién abre la demostración

Hoy solo se abre desde Administración › «Carpetas de trabajo» y solo si la cuenta, además de administrador, arma.

- **Qué se mira.** El código (`CarpetasDeTrabajo.tsx`, `POST /v1/casos/demostracion`) y la bitácora: si pedir `editar_hoja`
  es intencional, se deja y se explica; si es un descuido, basta ser administrador, con su prueba.

### Decisiones de la tanda 2

Formato: pregunta · lo que se hizo · cómo cambiarlo.

#### Tarea 5

1. **Dónde está el lector.** · Fuera del núcleo: cada adaptador tabular (`adapters/civil/tabular.py`,
   `adapters/telecom/adaptador.py`, `adapters/industrial/adaptador.py`, `adapters/sistemas/adaptador.py`) lee su CSV con
   `csv.DictReader` y `Decimal(celda)`. `core/` no se tocó. · —
2. **Dónde va la regla.** · En la capa de aplicación (`aplicacion/computo_csv.py`), que `POST /computos/{dominio}` llama
   antes del adaptador, y no copiada en cada adaptador: un adaptador solo importa `core.contracts` (NORMAS.md §2,
   `test_arquitectura.py`), así que no puede usar `aplicacion.cifras.cifra_escrita`, y el lector de tramos
   (`adapters/vial/tabular.numero`) no se puede importar desde otro adaptador. Así el intérprete de la regla sigue
   siendo uno (`cifra_escrita`, con su oráculo `tests/fixtures/cifras_escritas.json`). Cada adaptador solo declara sus
   `columnas_numericas` (las que lee como cifra); las demás celdas (código, descripción, especificaciones) pasan tal
   cual. · Copiar la regla en cada adaptador, como `numero` en vial, con una prueba contra el oráculo por copia.
3. **Qué regla con punto y coma.** · La estricta de Eugenio (`cifra_escrita`): «1.234» es mil doscientos treinta y
   cuatro y «2.5» se rechaza con el archivo, la fila, la columna y la regla. El CSV de tramos, en cambio, acepta el
   punto decimal («7.30») también con `;` y rechaza «1.234» por ambiguo; aquí el separador ya dice cuál es la regla.
   · Tolerar el punto decimal con `;` como en tramos (`numero`), a costa de que «1.234» siga siendo ambiguo.
4. **Con coma, nada cambia.** · Un CSV separado por coma no se toca (ni se copia): las muestras y los archivos que ya
   existen se leen igual, con punto decimal. · —
5. **Lo demás del archivo con `;`.** · Se admite la marca UTF-8 que pone Excel (`utf-8-sig`); un archivo que no es
   UTF-8 (el «CSV» de Excel en ANSI) se rechaza con su nombre, como antes; una fila con más celdas que la cabecera, con
   su número de fila. La copia se escribe en una carpeta propia del directorio temporal (`tempfile.mkdtemp`), con el
   nombre del archivo, que los adaptadores usan en sus mensajes. · —
6. **La ayuda.** · «Cargar cómputo» dice, bajo «Tipo de obra del archivo», cómo van las cifras con cada separador
   (`AYUDA_DEL_CSV` en `paginas/archivos/logicaComputo.ts`). No hay plantilla descargable del cómputo; el formato está
   en `data/samples/README.md` (párrafo nuevo) y en el README de cada muestra, que siguen con coma. · Agregar una
   plantilla descargable con `;` (hoy no la hay para ningún dominio).
7. **`docs/api.json`.** · Cambia una línea: la descripción de `POST /computos/{dominio}` (el docstring de la ruta).
   Regenerado dos veces con `scripts/exportar_openapi.py`, el mismo hash (`6b874bd3…19d52`). · —
8. **Rojo (`b72a2f62`, `472619d8`).** · pytest: 19 fallas de aserción (`assert WindowsPath('…/subida/computo.csv') ==
   …/leida/computo.csv`, `assert [{'id;a;h;lon…': …}] == [{'id': 'Z-01', …}]`, `Failed: DID NOT RAISE ValueError` y,
   por la API, `AssertionError` con «faltan las columnas […]» para las cuatro muestras con `;`). vitest: `Unable to
   find an element with the text: Si el archivo separa las columnas con punto y coma…`. Para que fuera de aserción y no
   un `ImportError`, el rojo trae el esbozo `a_la_forma_de_siempre`, que devuelve la ruta tal cual. · —

#### Tarea 6

1. **Adónde lleva el pendiente.** · Sigue llevando a Aprobaciones de su obra (`ABSORBIDAS` de
   `paginas/pendientes/logica.ts`, D-F3-2, sin cambios): la ruta de la obra es la que cambia de carpeta y fija la obra
   en la sesión, y la pantalla `entregar` no está bajo la obra (llevar directo a `#/entregar` abriría la entrega en la
   carpeta que estuviera abierta, no en la del pendiente). Aprobaciones, dentro de la obra, ofrece ahora «Entregar al
   cliente» con el enlace «Entregar paquete» (`paginas/aprobar/EntregaDeLaObra.tsx`), que abre con esa obra elegida
   (la toma de la sesión). · Hacer de `entregar` una sección de la obra (otra entrada del árbol).
2. **A quién.** · A la cuenta que puede usar la pantalla `entregar` (`usable`, la regla del árbol y del buscador:
   `entregar_paquete`); a las demás no se les pinta. La bandeja y el Resumen ya ofrecían el botón «Entregar» solo si la
   cuenta puede usar la pantalla de la acción, así que quien revisa no ve ni el botón del pendiente ni el enlace. · —
3. **Rojo (`6e0cb317`).** · `Unable to find role="link" and name "Entregar paquete"` (ana, del pendiente a
   Aprobaciones). Pasaban ya, como guardias, la de los permisos (`usable`) y la de quien revisa sin el enlace. · —

#### Tarea 7

1. **El nombre vigente.** · «Presupuesto» (`frontend-desktop/DESIGN.md`: «Presupuesto (`paginas/hoja/`, h1
   «Presupuesto»; antes «Hoja de la obra»)»). En Tramos: «Se llevaron N renglones de V al Presupuesto de la obra.»,
   el enlace «Abrir el presupuesto» (el texto de la acción de la mesa, H9) y «Guarde una en el Presupuesto para cargar
   sus tramos.». El enlace sigue apuntando a `/hoja`, que el marco lleva al Presupuesto de la obra abierta. · —
2. **Los avisos del servidor.** · `aplicacion/hoja_vial.py` (el 409 de un borrador de otra versión, sus tres casos, y
   el de las partidas que no se pueden valorar) dice «el Presupuesto de la obra» y «en el Presupuesto»; sus oráculos en
   `test_aplicacion_vial_llevar.py` y `test_api_vial_llevar.py` cambian con él, y entra una prueba del caso del borrador
   en blanco, que no tenía. El texto simulado de `vial/AvisoDeLlevar.test.tsx` sigue al del servidor. `docs/api.json`
   no cambia. · —
3. **Reajuste.** · «Elija una obra en «Obras» de la barra lateral, o búsquela con Ctrl+K, para reajustar sus precios.»
   · —
4. **La guardia.** · `PANTALLA_RETIRADA` de `sinJergaInterna.test.ts` caza también «Hoja de la obra» y «barra superior
   (Proyecto)» fuera de un comentario en `src/paginas`. «la Hoja» suelta no se caza: sigue en comentarios y en nombres
   internos (`ProveedorDeLaHoja`). · Ampliarla a «la Hoja» si se quiere retirar del todo del texto visible.
5. **Rojo (`20508f1a`).** · vitest, cinco: `expected [ 'reajuste/index.tsx', …(1) ] to deeply equal []` (la guardia:
   Reajuste y Tramos), tres `Unable to find an element with the text: Se llevaron 18 renglones de VIA-002 al
   Presupuesto de la obra.` (y sus variantes) y `Unable to find … Elija una obra en «Obras»…`. pytest, seis:
   `AssertionError: assert 'La Hoja de l...lva a llevar.' == 'El Presupues...lva a llevar.'` y las dos de «No se llevó
   nada…». · —

#### Tarea 8

1. **Qué hace el visor.** · «Libro de la empresa» no descarga nada: muestra el libro con los hallazgos, y elegir uno de
   la lista lleva a su celda marcada. El paso 2 dice ahora «Elija un hallazgo de la lista para ver su celda marcada en
   el libro.» en lugar de «Descargue el libro devuelto si lo necesita.». · Agregar al visor la descarga del libro con
   sus marcas, si se quiere ofrecer.
2. **Rojo (`a5c64572`).** · `AssertionError: expected 'Compare el total del libro con el que…' not to match
   /descarg/i`. · —

#### Tarea 9

1. **¿Es intencional?** · Pedir `editar_hoja` para estrenar la demostración, sí: es la decisión D-3 de Eugenio en
   `docs/especificaciones/2026-10-21-bienvenida-casos-proyectos-design.md` («demostración = `EDITAR_HOJA` (solo arma,
   como la clásica). Consecuencia: el administrador sin rol «arma» […] **no** puede estrenar la demostración»), con
   `POST /v1/casos/demostracion` en `EDITAR_HOJA` y la prueba B16 («`admin` 403»). Que además haga falta ser
   administrador, no: quedó así al juntarse dos cambios. MOD-3b mudó «Carpetas de trabajo» a Administración (que pide
   `administrar_cuentas`), y la baja 6 de F4 quitó «Probar con datos de demostración» del Resumen, la entrada que
   tenía quien arma, y la dio por cubierta con «Empresa › Carpetas de trabajo» y con «Empieza aquí» de F6, que todavía
   no existe (`docs/planes/PLAN_REDISENO_F4.md`, «Bajas aprobadas», fila 6). · No se cambió nada: «que baste ser
   administrador» desharía D-3, que es de Eugenio. Pregunta para él: ¿la demostración vuelve ya para quien arma (una
   entrada fuera de Administración, o la que traiga «Empieza aquí» en F6), o se le da también al administrador
   (`CAMBIAR_CASO`, la alternativa que D-3 deja escrita)?
