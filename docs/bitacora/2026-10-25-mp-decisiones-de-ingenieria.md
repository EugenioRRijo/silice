# Montar un presupuesto: decisiones de ingeniería de las tareas (2026-10-25)

Decisiones tomadas por los implementadores de `docs/planes/PLAN_MONTAR_PRESUPUESTO.md` que el plan no fijaba, anotadas a
pedido de sus árbitros. Las marcadas «por ratificar» esperan a Eugenio; las demás son de ingeniería y quedan como están.

## T9, rutas de la Hoja

- **Lista con que se valora.** El borrador en blanco nace en la moneda de la obra con la fecha de hoy. Se valora con
  `lista_para_el_proyecto` a la fecha del borrador, solo cuando hay partidas sin APU; vale para agregar y para editar el
  espacio. La conversión a la otra moneda se calcula y se deshace al editar; la escribe el guardado, en la misma transacción
  que la versión y a nombre de quien guarda. Sin tasa del BCV de los últimos 7 días, o sin lista para armar: 409 con el texto
  de MP-1, tanto al editar como al guardar. Dos oráculos de la 3d-1 (`tests/unit/test_api_hoja_guardado.py`) pasan de 422 a
  409 con ese texto. **Por ratificar.**
- **Código de la primera versión.** Se elige con `codigo` opcional en `/guardar` («VIV-001»); en las siguientes, 422 «El
  código se elige solo al guardar la primera versión; las siguientes siguen su numeración.».
- **Notas.** Viven en `mp_nota_medicion` (migración `caso_0012_mp_medicion`, que cuelga de `caso_0014_mp_aprobacion`; una nota
  por renglón de cada versión). Se escriben en la misma transacción que la versión (`hoja.guardar_version` y
  `crear_primera_version`, no `hoja_guardado.py:106` como decía el plan) y se recargan al abrirla. No entran en el sello de la
  cadena: son texto libre fuera del cálculo. **Por ratificar.** Las versiones creadas al restaurar, cotizar o convertir no
  copian las notas (deuda). No hay ruta para editar una nota: hay que quitar el renglón y agregarlo de nuevo (**por decidir**).
- **Errores nuevos.** `PartidaFueraDelCatalogo` → 404; `SinListaDeLaObra` → 409 (agregar, cualquier edición de un borrador
  en blanco y guardar).
- **Partida sin dominio** declarado: se presupuesta como obra civil.
- **`calculo` de la fila.** Solo en renglones «a-mano», con coma decimal, y no si su cantidad se escribió después a mano.
- **Fuente de la mesa.** `pendientes_sin_calculo` cuenta los hallazgos R1 de «cantidad manual sin regla» guardados con la
  versión vigente («3 cantidades escritas a mano sin cálculo en OB-001», acción «Abrir la Hoja»).
- Aviso para el árbitro: los dos oráculos ajustados de `test_api_hoja_guardado.py` y el registro `TABLA_5_7` de
  `test_aplicacion_hoja_lectura.py` cambiaron en el commit de implementación (no hubo forma de verlos en rojo sin stash).

### T9, ronda 2 (devuelta por dos MAYOR; corregida)

- La primera versión toma los precios de sus APU de la lista que declara (la de `lista_para_el_proyecto` al guardar: tasa
  del BCV y fecha del día de guardar), con `hoja.con_precios_de_la_lista`: si entre agregar y guardar llega una tasa más
  nueva (u otra lista para armar), tasa declarada y precios coinciden. Se conservan el rendimiento y las cantidades de cada
  línea del borrador (lo editable) y se cambia solo el precio; si las líneas del catálogo ya no son las mismas, el APU del
  catálogo entero. **Por ratificar** (la otra salida era guardar con la tasa con que se valoró, o 409).
- Agregar en una obra en la otra moneda ya no copia la lista entera para deshacerla: convierte en memoria solo los APU
  nuevos con `core.catalog.moneda.convertir` (la misma cuenta que `copiar_precios`), sin escribir nada; la lista convertida
  la escribe solo el guardado. Medido con 3.015 precios: de 1,5-1,9 s a 0,01-0,07 s por agregar.
  `valoracion_de_la_obra` (`aplicacion/listas_para_armar.py`) da la lista base y la tasa sin escribir;
  `lista_para_el_proyecto` la usa.
- Sin lista vigente a la fecha del borrador, pero con listas posteriores, la Hoja dice «Esta carpeta de trabajo no tiene
  lista de precios para armar vigente al dd/mm/aaaa: su primera lista rige desde el dd/mm/aaaa.». Solo en la Hoja
  (`valoracion_de_la_obra`); Componer conserva su mensaje (cambiarlo tocaría cuatro oráculos de T3).
- El código de la primera versión: `^[A-Za-z0-9._-]+$`, de 1 a 40; si no, 422 con el FORMA_GUARDAR de siempre, sin eco.
- `pendientes_sin_calculo` reusa `_versiones_vigentes`, `_plural` y `_pendiente` de la mesa (import diferido).
- La prueba de la fuente de calidad ya no la suma con monkeypatch: comprueba que está registrada una sola vez (la registró
  el orquestador en ec1b23a3; esa doble suma fue un error de integración).
- Menores tras la aprobación: guardar la primera versión responde 409 (sin escribir nada) si entre agregar y guardar la
  partida salió del catálogo, a un insumo le falta el precio en la lista o cambiaron las líneas de su APU (se perderían el
  rendimiento y las cantidades editadas: hay que quitarla y volver a agregarla); `plural`, `pendiente` y
  `versiones_vigentes` de la mesa son públicos.

## T10, buscador de partidas (aprobada en ronda 1)

- El oráculo del diseño §8.1 («`q=tub` devuelve solo LB-02-TUB») no se cumple con la línea base: LB-01-EXC dice «zanja de
  tubería». Por la regla 2 de §5.2 las dos son de rango 3 y el orden es [LB-01-EXC, LB-02-TUB]. La prueba usa ese oráculo.
- El modo local del campo (`opciones`) queda para el plan de autocompletado, como dice T10; `buscar` es obligatoria.
- Falta verificar en navegador la F0 de §4.3 (lista en portal con `enCelda` a 1056 px y letra al 150 %). Se hace antes de
  que una página use `enCelda`; T11 usa el campo en un diálogo.
- Menor cosmético pendiente: el 403 repite «Su cuenta» («Su cuenta no puede usar esta búsqueda. Su cuenta no tiene permiso…»).

## T11, la Hoja agrega y quita partidas

- **La cantidad del cálculo.** La interfaz no evalúa el cálculo (un solo intérprete, B3). Con la cantidad vacía, la ayuda
  dice que Sílice la toma del cálculo, y el servidor la calcula y la confirma. El plan pedía rellenarla al salir del campo.
  **Por ratificar** (la alternativa es una ruta que evalúe el cálculo antes de agregar).
- **El error de un 422 va a su campo** con `campoDelErrorDePartida`: «El cálculo…», «Escriba el cálculo…» y «Con cuatro
  decimales…» van a Cálculo; «La cantidad…» a Cantidad; la regla de las cifras va a Cálculo si alguna de sus cifras está
  mal escrita (el servidor lo lee primero) y si no a Cantidad. `leerCifra` solo valida. El 404 va a Partida y el 409 a un
  aviso del diálogo; con `rev` viejo, el borrador se vuelve a leer solo.
- **La lista del buscador va dentro del diálogo, sin `enCelda`**, como pide la bitácora de T10. Falta medirlo en navegador.
- **El `rev` con que se agrega** sale de `esperarEnvios()` (nuevo y aditivo en `useEdicionDeSeccion`).
- **Quitar** usa `accionarEnOrden` con el `detalle` tal cual en el aviso de la sección, tras confirmar «¿Quitar X del
  presupuesto? Lo puede descartar antes de guardar.».
- **El editor del Presupuesto se vuelve a montar cuando cambian los renglones** (antes, una fila nueva no viajaba en
  `cuerpoDeCantidades` y una quitada podía viajar).
- **La pestaña inicial se fija una vez por obra** (Presupuesto si la obra no tiene espacio); cambiar de versión no la mueve.
- **`Resumen.espacio_vacio` es opcional en el tipo** (la API lo manda siempre).
- **F11 de MOD-3b corregido:** estados vacíos con «obra» y el selector de obra; el h1 sigue «Hoja del proyecto» (va con
  `rutas.ts`, compartido: se cambia en MOD-5b).
- **«Componer una partida nueva»** lleva a `/componer?codigo=X&volver=hoja` y se pierde lo escrito en el diálogo; Componer
  debe leer esos parámetros (encargado a T4). **Por decidir:** ¿preguntar antes de perder lo escrito?
- **Por decidir (Eugenio):** editar una nota (`PUT …/partidas/nota` con un campo en la fila) y avisar si el total cambia al
  guardar por una tasa nueva (que `/guardar` devuelva tasa y fecha usadas y el diálogo avise si difiere).

### T11, ronda 2 (devuelta por falta de pruebas que distingan; corregida)

- El `rev` de «Agregar partida» sale de `esperarEnvios()`: primero sale lo que esperaba la pausa y se espera lo que va en
  vuelo. Lo cubre una prueba con el PUT retenido (falla con la mutación del árbitro).
- Con un 409 por `rev` viejo, el diálogo relee el borrador y la vista, conserva lo escrito y lo dice; el segundo intento
  lleva el `rev` releído.
- El foco tras un error va al campo, o a la caja del diálogo, cuando los controles vuelven a estar habilitados (antes se
  intentaba con el campo deshabilitado y se perdía, también en el 422).
- El editor del Presupuesto ya no se vuelve a montar al agregar o quitar: se vuelve a sembrar (`resembrarCantidades` de
  `logicaSecciones.ts`) conservando lo tocado y no aceptado, y su aviso.
- Defecto del motor de edición (`useEdicionDeSeccion`): una acción como «Quitar» se repetía si la persona escribía mientras
  iba. Ahora solo la edición se repite y lo escrito sale después, una vez, con el `rev` que dejó la acción.
- Lo escrito en el diálogo es un formulario sucio (`useFormularioSucio("hoja", …)`): «Componer una partida nueva» pregunta
  antes de perderlo.
- Pendiente: `HojaExcel.test.tsx` («pide el libro… y no toca nada más») es inestable (un `GET …/vistas/espacio` tardío), ya
  antes de esta ronda; revisar si lo causa el `setPestana` durante el render de la ronda 1.
- Encargos finales (601e01c2, d610b54e): el reenvío de lo escrito mientras iba una acción (quitar) ya no borra, al
  aceptarse, el aviso de la acción fallida, y no sale tras un 401 ni con el borrador ausente. `HojaExcel` espera la vista de
  Espacio antes de contar las peticiones (la carrera era de la prueba desde 3e-1, no de T11).

## T12, Elaborar lleva a la Hoja

- **Cantidad de máquina.** En `POST /v1/hoja/llevar` la cantidad es la del cómputo (punto decimal, sin miles, sin signo ni
  exponente), como `POST /presupuestos/calcular`; el servidor la escribe con `texto_de_cifra` antes de `agregar`, así
  «1.125» es uno coma ciento veinticinco. `calculo` (opcional) sigue la regla de la Tarea 8 (coma).
- **Qué borrador.** El vivo más reciente de esa ficha y obra (aunque sea de una versión anterior a la vigente; la Hoja avisa
  al guardar); si no hay, uno nuevo sobre la vigente o en blanco en la moneda de la obra. Abrir la vigente escribe su
  instantánea si faltaba (UC-15e), como abrir la Hoja, y eso no se deshace si luego falla una partida.
- **Todo o nada.** Con el cerrojo del borrador tomado de punta a punta: el borrador abierto por llevar se descarta; uno que
  ya existía vuelve a su `borrador`, `rev` y caché exactos (se reasignan los campos del `BorradorVivo` bajo su cerrojo;
  `hoja_borradores` no tiene un «restaurar»: menor). Un 422 de cálculo lleva el código de la partida delante.
- **Elaborar con obra.** `CalculoPeticion.proyecto` (opcional): valora con `lista_para_el_proyecto` y la moneda de esa
  lista (se ignora `moneda`); la lista convertida no se confirma. Las dos rutas de calcular dependen ahora de `_QUIEN_EDITA`
  (misma acción) para firmar la conversión. Obra inexistente, 404 sin eco; sin lista o tasa, 409.
- **Front.** Los pendientes no se llevan (se dice cuántos); con obra no se escribe la moneda; si se cambia de obra tras
  elaborar, pide elaborar de nuevo. Tras llevar navega a `/hoja`, que ofrece retomar el borrador (abrirlo directo con
  `/hoja?borrador=<id>` se encarga a T11).
- **Por decidir (Eugenio):** las partidas llevadas llegan «a mano» sin cálculo, así que R1 avisará en cada una; ¿nota
  automática «Del cómputo de Elaborar» o traducir la regla del cómputo a un cálculo?
- Aviso para el árbitro: un oráculo de la prueba de T12 se corrigió en un commit de pruebas propio (63ab8dd0): al llevar a
  VIV-001 (con plan) el alta entra también en el plan (conducta de la Hoja), así que se cuentan solo los cambios de
  cantidad.

### T12, ronda 2 (devuelta por un MAYOR; corregida)

- Todo o nada sin expulsar a nadie: `llevar_a_la_hoja` valida todas las partidas (catálogo, cantidad y cálculo con
  `cantidad_y_regla`) y, si la obra no tiene versiones, la lista con que se valora (`valoracion_de_la_obra`, el 409) ANTES de
  registrar el borrador, porque registrar uno nuevo expulsa el menos usado de la ficha (`POR_FICHA`). Orden de los errores:
  partidas (404, 422) antes que la lista (409). Lo imprevisible (la base) después de registrar todavía descarta el borrador
  nuevo, y el expulsado en ese caso no vuelve (límite declarado).
- La restauración de un borrador que ya existía devuelve también su `tamano` (el registro lo vuelve a medir cada 20
  cambios); la caché de la vista no se exige igual: la llena el listado de borradores (rev 0).
- `/computos` escribe cantidades y parámetros en notación fija (`format(x, "f")`; `str` daba «1E-7», que `llevar` rechaza
  con el 422 de forma). El patrón de `llevar` sigue sin exponente.
- Cobertura nueva: 2000 partidas aceptadas (`MAX_ITEMS`, importado de `api/esquemas_ola2.py`), el Excel de Elaborar con
  obra y la lista completa de cambios al llevar a VIV-001, igual a la de agregar a mano.
- El oráculo de la ronda 1 de T12 (el de la línea mal puesta en `test_api_hoja.py`) era del orquestador y se corrigió en
  `2e6a70c2`.
- «Llevar a la Hoja» abre la versión vigente con `hoja.abrir_version` (como R2) y queda registrado en el embudo de
  `tests/unit/test_arquitectura_s3.py` (`LLAMADORES`), con el responsable = la persona de la sesión (`520ab6f0`).

## T13, estudio de mercado (aprobada en ronda 1)

- `Estadisticas` lleva `dias` al final, para el texto «Sin observaciones en los últimos {dias} días.».
- `Propuesta.precio` va en céntimos. El precio de cobro se redondea **hacia arriba** cuando hace falta para no quedar bajo
  el piso (piso 125,001 → 125,01); `Propuesta.piso` queda exacto. **Por ratificar.**
- La razón de compra lleva la moneda y usa singular con una observación.
- Al registrar una observación: precio mayor que cero, fecha no posterior a hoy (las pasadas se aceptan sin límite, pero
  fuera de la ventana no cuentan; **por ratificar**), código existente (insumo en compras, partida en cobros), fuente
  obligatoria de hasta 200 caracteres, nota de hasta 500, y una carpeta sin moneda da `CarpetaSinMoneda`.
- La ventana es `hoy − dias <= fecha <= hoy` (el plan solo fijaba el límite inferior).
- Si la versión vigente de la obra está en otra moneda que la carpeta, el piso usa el bono de alimentación por omisión y
  los factores de la versión. **Por ratificar:** ¿bono por omisión o convertido con la tasa del BCV?
- Con el primer cuartil igual al piso la razón dice «por encima de su costo»; conviene «igual o por encima» (para T14).
- Menores para T14: `aplicacion/mercado.py` rearma a mano los parámetros de la versión (ya lo hace
  `_parametros_de_version` en `aplicacion/hoja.py`), duplica `_exigir_responsable` de `aplicacion/listas_para_armar.py` y
  recorta el responsable a 200 sin avisar; T14 valida `lado` y `fuente_tipo` en el esquema para que esos `ValueError` no
  lleguen a un 422 visible.

## T3, Componer guarda en la lista de hoy (aprobada en ronda 1)

- `guardar_composicion` recibe la sesión; decide primero el motivo y solo si va a escribir pide
  `lista_de_hoy(sesion, fecha, nueva_si_usada=False)`, así una cabecera rechazada no crea una lista que nadie usa.
- Componer escribe en la lista de hoy aunque una versión guardada ya la use (como manda el plan): solo agrega insumos o
  variantes nuevas, nunca cambia un precio existente. La «(2)» del mismo día solo la crea el estudio de mercado.
  **Por ratificar.**
- `precio_en_lista` del aviso es el del homónimo original (el de menor id) en la lista de hoy, no el de la variante más
  parecida. Una variante ya existente con el mismo precio tecleado no se avisa (el APU la usa). **Por ratificar** si debe
  avisarse «usará la variante existente».
- Prever con una cabecera distinta de la partida existente da `ComposicionInvalida` → 422, igual que `/guardar`.
- Con `lista_nueva`, `Prevision.lista.lista_id` es un id que no existe tras deshacer; está documentado y la API no lo
  expone (menor: pasarlo a `None`).
- Deuda para T4: `/guardar` conserva el 422 de Pydantic con eco; pasar el router entero a `RutaSinEco` junto con el front.
- Las bases creadas con `crear_esquema` que guardan composiciones necesitan `crear_esquema_carpeta`; las migradas no.
- `aplicacion/elaboracion.py:4-5` todavía nombra `ui/elaboracion.py`, que ya no existe.

### T14, ronda 2 (devuelta por un MAYOR; corregida)

- «Usar este precio» de compra ya no reescribe en el lugar una lista de hoy que otra cosa copió: `_usada`
  (`aplicacion/listas_para_armar.py`), consultada solo con `nueva_si_usada=True`, la da por usada si la usa una versión, si
  otra lista la tomó de base (`ListaPreciosOrigen.lista_base_id`, `ListaEmpresa.lista_base_id` o `lista_referencia_id`) o si
  una obra en la otra moneda la convirtió. La conversión se reconoce por la misma clave de nombre con que
  `lista_para_el_proyecto` la reutiliza (`_nombre_convertida`, una sola regla), porque `convertir_lista` deja
  `lista_base_id` vacío a propósito. Entonces se deriva «… (2)» (D-MP2) y la conversión siguiente sale con el precio nuevo;
  la anterior no cambia. Se descartó invalidar el reuso de la conversión: habría dejado dos listas con el mismo nombre.
  Componer (`nueva_si_usada=False`) no cambia.
- Las reglas que ve la persona son `ReglaDeMercado`; la API muestra su mensaje (y el de `CifraInvalida`), y cualquier otro
  `ValueError` sale como 422 con un texto fijo.
- No se cita una observación de otra moneda (ni anulada). Sí una de fuera de la ventana de 90 días: la persona puede ampliar
  la ventana, y una observación no anulada sigue siendo cierta.
- El precio objetivo (cobro) admite hasta 2 decimales (céntimos); compra y observaciones no tienen ese límite.
  **Por ratificar.**
- Encargo final: la conversión de alcance proyecto se reconoce por el número de su lista base, al principio de su
  `origen` («Convertida de la lista n.º {id}: »), y no por el nombre, que se recorta a 120 caracteres y con nombres largos
  confundía la lista de hoy con su «(2)». Lo usan el reuso de `lista_para_el_proyecto` y `_usada`; `core/` no cambia; las
  conversiones anteriores, sin marca, se rehacen una vez.

## T4, Componer dice la moneda

- Componer y el panel leen `GET /v1/carpeta`. «Precios en {moneda}» y los montos del desglose dicen la moneda («2.074,44
  Bs», una sola conversión, el exacto en el `title`); sin moneda conocida no se inventa.
- Choque con T2: el plan ofrece «Convertir la lista que tiene» solo si `lista` está en otra moneda que la carpeta, pero T2
  devolvía `lista: null` en ese caso; con la API real el botón nunca aparecía. Se corrige en `api/rutas/carpeta.py`
  (`_estado` devuelve la vigente de otra moneda en `lista`); ver la línea de cierre de T4 abajo.
- Cuándo hay cambios sin guardar en Componer: que la persona haya escrito algo, que haya datos y que no esté guardado; la
  URL y la precarga no cuentan.
- Guardar pasa primero por `POST /v1/composicion/prever`; con variantes, el diálogo `DialogoVariantes` (reusa
  `MarcoDeDialogo`) dice qué precio tecleado quedará como variante; «Volver» tiene el foco inicial.
- «Guardar composición» queda deshabilitado mientras la carpeta tenga aviso (antes respondía 409). **Por ratificar.**
- El montaje de `ListaDeLaCarpeta` en el `pie` de `SelectorObra` lo hizo T4 (commit `e4ac99b4`). El panel dice «Moneda de
  trabajo: Bs · Lista para armar: {nombre}, al {dd/mm/aaaa}»; con nombres derivados la fecha sale dos veces (**por
  decidir** si se quita el «, al …»).
- Deuda de T3 cerrada: `RutaSinEco` en todo el router de Componer (`docs/api.json` no cambia).
- `?codigo=X&volver=hoja`: trae el código y, guardada la partida, ofrece el botón «Volver a la Hoja» (`useNavegarSeguro`).
- Choque con T2 resuelto (97aabf0f, 2ed1d765): `GET /v1/carpeta` da en `lista` la vigente aunque esté en otra moneda que la
  carpeta, con su propio `origen`, y el `aviso` sigue diciendo que hay que convertirla; así Componer ofrece «Convertir la
  lista que tiene» con la API real. `describir_vigente` es nueva en `aplicacion/listas_para_armar.py` (`describir` no cambia
  y la mesa la sigue usando); el oráculo de T2 cambió de nombre y de valor esperado. El esquema no cambia.
- Menores de la ronda 1 (4f8e5cf7, 7b6f12bb): desde MaPreX, `POST /v1/carpeta/lista-para-armar` responde 409 si la carpeta
  ya tiene lista para armar (en la ruta, no en `aplicacion/`, porque T1 conserva la numeración «(2)»); Componer vuelve a leer
  la carpeta ante un 409 y dice por qué desaparece el aviso. El panel y «Lista para armar creada» no repiten la fecha si el
  nombre ya la trae (**por ratificar**). Los docstrings de la carpeta dicen el sentido nuevo de `lista`.

## T8, partidas a mano

- **Tolerancia doble.** El plan pedía «|v − c| > 0,001, la tolerancia de R1», pero R1 (`core/verification/reglas.py:119-122,161`)
  compara en forma **relativa** (0,001 × el resultado; con resultado cero exige igualdad). La cantidad escrita coincide con el
  cálculo solo si cumple las dos: diferencia ≤ 0,001 **y** ≤ la tolerancia relativa de R1 (tomada de la instancia de
  `TrazabilidadGeometrica` en `REGLAS`). Con la absoluta sola, 0,5008 frente a «1/2» se aceptaba y R1 la marcaba luego como
  error. **Por ratificar.**
- **PRECISION_PERDIDA.** Sin cantidad, el resultado se guarda con cuatro decimales (la mitad hacia arriba, sin ceros a la
  derecha ni exponente); si ese redondeo deja de coincidir según la regla anterior («0,00005*1» → 0,0001), no se guarda y se
  pide escribir también la cantidad. **Por ratificar.**
- **El resultado en los mensajes** se dice con cuatro decimales, salvo que así se vea igual a la cantidad escrita (o a cero):
  entonces con todas sus cifras («El cálculo da 0,00005 y la cantidad es 0,0001…»).
  Desde el último menor: si no cabe en cuatro decimales y redondeado se vería igual a la cantidad (o a cero), se dice con 8
  cifras significativas, la mitad hacia arriba (1/30000 → «0,000033333333»), y con todas solo si aun así se viera igual.
- **Mensajes que el plan no fija:** «El cálculo no se puede hacer: revise los signos y los paréntesis.»; «El cálculo divide
  entre cero.» (también 0/0, que el `decimal` en C da como `InvalidOperation([DivisionUndefined])`); «El cálculo da X: una
  cantidad no puede ser negativa.»; «La cantidad no puede ser negativa.»; «El cálculo da una cifra demasiado grande para una
  cantidad.»; «El cálculo es demasiado largo: use a lo sumo 300 caracteres.»; «Escriba el cálculo, por ejemplo 6*3-2.»;
  «Esa fila ya no está en el presupuesto.». Se aceptan el «−» tipográfico y «x»/«×»; «**» y «//» se rechazan. El cálculo
  nunca se ejecuta: lo evalúa `core.verification.evaluar` (solo aritmética sobre el árbol sintáctico).
- **Negativos:** una cantidad negativa y un cálculo que da negativo se rechazan; «0*-1» se lee como 0.
- **Cambio de conducta del Asistente:** las partidas que propone entran en `items_base` y desde T8 cuentan como **altas**
  (antes guardar solo propuestas no guardaba nada; lo pide el diseño §5.3).
- **Altas, bajas y repetidos:** un renglón que entra es un alta y uno que sale una baja, nunca a la vez con un cambio de
  cantidad; si quitar el primero de dos repetidos renombra el segundo («X|o#2» → «X|o»), se registra el cambio de cantidad de
  «X|o» y la baja de «X|o#2».
- **Notas solo no cuentan como cambio** (no habilitan guardar); guardarlas es de T9. **Por ratificar.**
- **Texto llano:** «La cantidad de X (Q U) se escribió a mano sin cálculo: escriba cómo se obtuvo si quiere que Sílice la
  pueda verificar.», con Q en es-VE.

## T15, página Estudio de mercado

- Buscador de insumos en el navegador: no hay una búsqueda de insumos en el servidor (la de T10 es de partidas). La página
  pide una vez `GET /insumos` (el catálogo de la carpeta, acción `leer_proyecto`) y filtra por palabras del código o la
  descripción, sin tildes ni mayúsculas (`buscadorDeInsumos` en `src/paginas/mercado/logica.ts`); si falla, la búsqueda
  siguiente la vuelve a pedir. Sirve para cientos de insumos. **Deuda:** `GET /v1/buscar/insumos` con el contrato de
  `/v1/buscar/partidas` (relevancia, límite por grupo, `hay_mas`) cuando el catálogo crezca.
- «de n observaciones» va bajo los cinco montos (mínimo, primer cuartil, mediana, promedio y máximo), no bajo n, donde
  sería redundante (el plan decía «cada una»).
- Compra: la observación que respalda el precio es opcional (selector con las de la moneda de la carpeta) y viaja como
  `observacion_id`. Cobro: se citan siempre todas las `estadisticas.ids` y se guarda sin confirmación (no hay partidas
  que cambien). **Por ratificar** si cobro debe pedir confirmación.
- Los avisos de éxito son texto neutro en una región `role="status"`, sin la notificación verde de Carbon («verde por
  ser positivo» está prohibido en DESIGN.md).
- El TextInput de Carbon 1.117 no enlaza su mensaje de error con el campo: con error, la página pone
  `aria-describedby="<id>-error-msg"` (como `CampoConBusqueda`).
- La ubicación (Presupuestos y obras › Mercado, la primera del área) es la del plan de módulos. **Por ratificar.**

### T15, ronda 2 (devuelta por un MAYOR; corregida)

- MAYOR: tras usar un precio escrito, el campo volvía a la propuesta y un segundo uso la mandaba sin aviso. Ahora la
  última propuesta vista y el texto «sin cambios» se guardan aparte: lo usado queda en el campo y la pantalla queda
  limpia; la propuesta solo reemplaza el campo si no hay nada propio sin usar.
- El ícono de «la competencia cobra menos que su costo» sale de la razón que manda la API (que compara los exactos),
  no de comparar cifras ya redondeadas en la página.
- Los montos ya no llevan `title` con el texto de la API con punto decimal.
- Elegir otro insumo o partida con un precio o una observación a medio escribir pasa por `confirmarSalida("salir")`
  (MOD-2); con «Quedarme» el buscador vuelve a decir lo que se estudia.
- Si usar el precio falla con un error que no es del campo, el foco va al aviso de error.
- Límites que quedan: «Ver estos días» descarta sin preguntar un precio escrito sin usar (el estudio se recarga), y
  «Salir y descartar» olvida todos los formularios registrados de la pantalla, también los de la otra pestaña
  (`olvidarFormularios` de MOD-2).
- D-4 (MOD-5): las rejillas del estudio de mercado usan `minmax(min(100%, …), 1fr)` y los campos de sus formularios se
  encogen con su columna (`min-inline-size: 0`, `max-inline-size: 100%`); la Fecha de «Anotar una observación» ya no saca la
  página de ancho a 1056 px con letra Grande y Muy grande; lo vigila `src/paginas/mercado/estilosMercado.test.ts` (falta
  volver a medirlo en navegador).
- Cierre: `tests/unit/test_front_razon_mercado.py` ata `RAZON_POR_DEBAJO` de `logica.ts` a la de `aplicacion/mercado.py`;
  `confirmarSalida` gana el motivo `"cambiar"` con consecuencia propia (aditivo en MOD-2), y el estudio de mercado lo usa al
  elegir otro insumo o partida («Si elige otro insumo o partida, se perderán.», «Cambiar y descartar»).

## T16, objetivo de mercado en la Hoja (aprobada en ronda 1)

1. **El margen lo calcula la API:** `GET /v1/mercado/objetivos` recibe `pu=CODIGO:monto,…` (exacto, con utilidad, sin
   IVA) y `moneda`; `margen` lleva una cifra decimal vía `margen()` de T13; −0,0 se dice 0,0. Vacío sin precio unitario,
   con uno ≤ 0 o en otra moneda (sin convertir). `pu` mal formado, una partida repetida con precios distintos (con el
   mismo precio se acepta) o `pu` sin `moneda` dan el 422 de forma.
2. **La celda** no repite «APU 2.074,44» y dice «1.980,00 · margen −4,6 %», «… · sin precio unitario, sin margen» o
   «31,50 USD · en otra moneda que la obra (Bs), sin margen». **Por ratificar.**
3. **El margen se compara con el precio exacto.** **Por ratificar.**
4. **El signo es la única marca**, sin color. **Por ratificar** si el negativo va en rojo IBCS con ícono.
5. **Hoja grande por tandas:** `partidas` ≤ 2.000 y `pu` ≤ 4.000 caracteres por pedido.
6. **Si falla la lectura**, la Hoja sigue y lo dice bajo la tabla.
7. Tres pruebas que fijaban las columnas del Presupuesto ganan «Objetivo de mercado».
8. Árbitro (ronda 1): esos tres oráculos se cambiaron después del feat (1b536fcb, 2f0d25e3) y quedaron en rojo en la
   historia entre a40054d5 y 2f0d25e3; en adelante, el oráculo de una columna nueva va en el commit rojo. Menores encargados:
   margen viejo visible mientras llega la respuesta nueva, ayuda sin `aria-describedby`, consulta cuadrática por render
   (front); `InvalidOperation` con un `pu` absurdo y mensaje propio del 422 de `pu` (con T25).
   **Cerrados** los tres del front: la columna queda vacía y sin error mientras llega la respuesta a otros precios, la ayuda describe la cabecera (`aria-describedby`) y la consulta se arma una vez por filas (`useMemo`, conjunto en vez de `includes`); además, el error va en una región `role="status"` montada vacía.
   Desvío del método: el commit `2346a6bb` mezcló prueba y código sin rojo visto (no se reescribe). Ronda 2 (árbitro, MAYOR): `descripcion` pisaba el `aria-describedby` de orden de Carbon en toda columna ordenable; ahora solo se pasa en columnas no ordenables (Carbon no expone su id), con pruebas en `src/comun` (rojo en su commit). Lo oculto por el tipo (depreciación, modalidad, unidad) ya no ensucia el diálogo de agregar línea.

## T17, eventos de aprobación (aprobada en ronda 1)

- «Aprobada con observaciones» cuenta como aprobada: no se reenvía y vale para `ultima_aprobada` (Entregar y Control).
  **Por ratificar.**
- Una versión retirada se puede volver a enviar y al hacerlo retira la pendiente (el diseño solo prohíbe reenviar la
  devuelta). **Por ratificar.**
- `fases` muestra cada envío con su desenlace, retiros incluidos («VIV-001 retirada → VIV-002 aprobada con observaciones»).
- `ultima_aprobada` es la del último dictamen que aprobó en el tiempo, no la de número más alto. **Por ratificar.**
- Choque entre dos sesiones: en SQLite WAL llega `OperationalError` («database is locked», `SQLITE_BUSY_SNAPSHOT`), no
  `IntegrityError`; se trata como choque, se deshace, se relee y se valida una vez más. Si vuelve a chocar: «Otra persona
  registró un movimiento de aprobación de esta obra al mismo tiempo: vuelva a intentarlo.»
- Límite declarado: borrar el último evento, o reescribir la cola recalculando las huellas, no se detecta (no hay ancla
  externa; igual que la cadena del núcleo).
- `armo` se calcula en todo evento comparando el `<login>` de quien actúa con el del eslabón de la versión.
- Menores para T18: usar `abrir_sesion_de_escritura` (BEGIN IMMEDIATE) en las rutas que envían y dictaminan, para que el
  segundo dictamen reciba siempre el mensaje del plan; filtrar el choque por `sqlite_errorname` (`SQLITE_BUSY*`,
  `SQLITE_LOCKED*`) en vez del texto; normalizar o rechazar un `ahora` con zona horaria antes de calcular la huella; reusar
  `json_canonico`/`huella` de `core/budget/canonico.py` o dejar escrito por qué no.

## T14, rutas del estudio de mercado

- Anular una observación deja un contraasiento: una fila que copia la observación, dice «Anula la observación n.º X.», quién
  y cuándo, y se anula a sí misma; la original queda con `anulada_por` = id de esa fila. **Por ratificar.**
- «Usar este precio» de compra el mismo día: si ninguna versión usa la lista de hoy se reescribe en el lugar; si ya la usa
  una, se crea «… (2)» (D-MP2).
- Piso y precio con utilidad se muestran en céntimos con la mitad hacia arriba; la propuesta de cobro, hacia arriba (piso
  125,004 → «piso 125,00» y «propuesta 125,01»).
- Ventana de días de 1 a 3.650; `objetivos` devuelve el último precio aunque esté en otra moneda y dice cuál.
- El origen del precio dice quién lo hizo («Estudio de mercado: observación n.º {id}, por {responsable}»).
- No registra `CambioPrecio` al usar un precio de compra (ese historial es del cambio entre listas, UC-02) ni borra la
  `ReferenciaPrecio` del precio cambiado.
- `parametros_de_version` vive en `aplicacion/parametros_de_costo.py` (Hoja y mercado); `aplicacion/reajuste.py:638` y
  `aplicacion/tablero.py:113` todavía arman `ParametrosCosto` a mano (deuda).
- `pendientes_de_mercado` importa `aplicacion.mesa` dentro de la función para evitar el import circular con `FUENTES`.

## T18, rutas de aprobación

- El detalle de un envío (`GET /v1/aprobaciones/{envio_id}`) se lee de los renglones y los hallazgos guardados de la
  versión (lo que su sello cubre), no con `abrir_version`, que escribe la instantánea. Desviación consciente del plan: el
  detalle es de solo lectura y no abre borrador.
- Columnas del índice de la instalación (`mp_indice_aprobacion`): `proyecto` es el código de la obra (el de
  `GET /v1/proyectos`), y se agregan `obra` (su nombre), `nota` (la del envío), `notas` y `armo` (los del dictamen).
- `/pendientes` y `/mias` devuelven listas (no un objeto con la lista dentro).
- Con la clave de API (sin cuenta), `/mias`, `/abrir` y `/dictamen` responden 403: son de una persona.
- `/abrir` responde 404 sin eco («No se encontró ese envío.») si la carpeta no existe o el nombre trae rutas o `..`; la
  sesión no cambia. La carpeta de la empresa se recuerda como caso nulo (la de siempre).
- El reflejo del índice tolera fallos: si no se puede escribir, la respuesta no cambia (manda la carpeta) y queda un aviso
  en el registro; los GET que leen el índice reflejan antes la carpeta abierta, así que lo reponen.
- Fuente «aprobar» de la mesa: solo el último envío de cada obra; las notas de una devuelta se juntan (espacios y saltos
  seguidos cuentan como uno) y se cortan a 80 letras con «…». **Por ratificar.**
- `hallazgos.error` del detalle cuenta los de severidad error y crítico.
- Clases de error: `NoSeEncontro` → 404, `DatosInvalidos` → 422, otra `AprobacionInvalida` → 409.
- Una hora con zona horaria se RECHAZA (`ValueError` antes de escribir), no se normaliza. **Por ratificar.**
- Envío y dictamen usan `BEGIN IMMEDIATE`; el choque se reconoce por `sqlite_errorname` (`SQLITE_BUSY*`,
  `SQLITE_LOCKED*`), no por el texto; la huella usa `json_canonico` y `huella` de `core/budget/canonico.py`.
- **Duda para Eugenio:** quien revisa (rita) no tiene `cambiar_caso`, así que al volver a entrar no vuelve a la carpeta
  que abrió desde un envío (la elección recordada solo se restaura a quien puede cambiar de carpeta).
- Ronda de menores: el reflejo del índice tolera cualquier fallo después de confirmar la carpeta (aviso en el registro, la
  próxima lectura lo repone). El detalle de un envío lista también los ítems pendientes, sin precio. El detalle trae la
  cadena de versiones recalculada como en Trazabilidad y el dictamen se rechaza con 409 si está rota. Enviar una versión de
  una cadena rota todavía se permite: solo se bloquea el dictamen. La mesa reusa la acción «Ver el envío».
- Ronda 3: una versión de una cadena de versiones rota tampoco se envía (409), para no dejar envíos atascados que nadie
  puede dictaminar. El total del detalle con pendientes se verifica con `sqlite3`. El fallo del reflejo queda probado en el
  registro. **Por decidir (Eugenio):** con la cadena rota, ¿permitir al menos devolver?; una versión antigua sin sellar
  rompe la cadena y bloquea el dictamen de todas (igual que Trazabilidad y la entrega).

## T21, plan desde los rendimientos

1. **Cantidad 0 en la Hoja.** `plan_por_rendimientos` deja fuera la partida, como manda el plan; pero la curva del núcleo
   exige que cada partida valorada sume 1, así que `plan_del_borrador` la pone entera (monto 0) en el último período (no
   alarga el plan como haría `ajustar_plan` con un «Día n+1»). **Por ratificar.**
2. **«La anterior» de una paralela** es la anterior que entró al plan; una con cantidad 0 no cuenta. Si es la primera, empieza
   en 0.
3. **Cuadrillas:** texto con un entero de 1 a 99, sin separadores ni ceros a la izquierda; el tope de 99 es arbitrario.
   **Por ratificar.**
4. **Tope de 500 períodos:** el de la matriz (`EdicionPlan`); más allá el plan no se podría editar. El mensaje sugiere
   semanas o más cuadrillas.
5. **Varios renglones del mismo código** suman su cantidad: una sola duración, como en `plan_secuencial`.
6. **Rehacer el plan** reemplaza la matriz entera (la pantalla avisa «lo que haya repartido a mano se reemplaza») y no pide
   confirmación; el mismo plan no sube el `rev`. **Por decidir** si debe confirmar con un plan repartido a mano.
7. **Sin plan, el front no lista partidas** (`vista_plan` no las trae): se manda una cuadrilla por partida; con el plan
   hecho, la persona ajusta cada una.
8. **Para T27:** `paralelas_del_plan` sigue la letra del plan y también marca como paralela una partida encadenada que
   empieza en el mismo período que la anterior (con duraciones de medio día y, en semanas, es lo habitual).
9. La primera versión sin plan guarda el plan desde los rendimientos en vez de una partida por día (`crear_primera_version`
   usa `con_plan_por_rendimientos`); ningún oráculo dependía de «una partida por día» (choque 10).

### T21, ronda 2 (devuelta por un MAYOR de accesibilidad; corregida)

- Un residuo negativo solo puede salir en partidas muy largas (el error de redondeo, igual en cada período entero, se
  acumula). Solo en ese caso la partida se reparte con el acumulado cuantizado (fracción = acumulado cuantizado − el del
  período anterior); así se conservan los oráculos del plan (0,042557 en el Día 51 de OBRA-05) y ninguna fracción queda
  negativa. Las fracciones 0 no entran al reparto.
- Las cuadrillas van en `CampoTexto`, sin región viva vacía en cada fila (guardia `regionesVivasVacias`).
- «1 período» en singular.
- Los avisos son una sola región viva (`InlineNotification role="status"`) con el nombre «Avisos del plan» por
  `aria-labelledby` (Carbon reserva `aria-label` para el botón de cerrar).

## T22, causas de retraso (aprobada en ronda 1)

1. **Orden de los atrasos:** el del presupuesto (el de la reproyección). La mesa toma el primero, que suele ser la partida
   que origina el atraso (en la vivienda, OBRA-02 por la compra tardía y no OBRA-05, que va 16 días tarde solo por el SPI
   global). **Por ratificar.**
2. **Partidas sin avance propio:** entran con el `fin` que les da el núcleo con el SPI global, con «sin causa declarada».
3. **Qué causas cuentan:** la última declarada (por orden de registro) en las valuaciones no anuladas con «hasta» hasta el
   corte; la de una valuación posterior al corte no cuenta.
4. **Rechazo sin eco:** una causa desconocida es un `ValueError` con texto fijo («La causa del retraso no está en la lista
   de causas.») y deshace la valuación entera. Una causa que no es texto da el 422 por omisión de FastAPI (el router de
   control no es `RutaSinEco`); no se cambió para no tocar el 422 de todas las rutas de control (deuda).
5. **La lista de causas la da la API** (`GET /v1/control/valuaciones`, `causas`); la causa vacía viaja `null`.
6. **Base sin la tabla:** se lee sin causas; la tabla se crea al guardar la primera.
7. **Mesa:** OB-S2 pasa de «Atrasada 3 días hábiles (SPI 0,80)» a «OB-A atrasada 2 días: sin causa declarada»; el detalle
   de la cifra de avance sigue diciendo los días hábiles de la obra (3). El texto dice «días» y cuenta días hábiles.
   **Por ratificar.**
8. Dos oráculos de `Control.test.tsx` cambian por el contrato: el cuerpo de las líneas lleva `causa: null`.
9. Árbitro (ronda 1): oráculos de atraso rehechos a mano con `_proyectar_partida`. Menores que pasan a T25: el router de
   control repite lo enviado en el 422 (`causa`, `cantidad`, `observacion`) → `RutaSinCache`+`RutaSinEco` en todo el router;
   `aplicacion/causas.py` repite el filtro de `para_el_valor_ganado()`. **Por decidir (Eugenio):** si se muestran las
   partidas atrasadas solo por el SPI global (sin avance propio).

## T23, procura con fechas (aprobada en ronda 1)

1. **Vale la primera fecha de cada evento** (primer pedido, primera recepción); no se comparan cantidades (entregas
   parciales). **Por ratificar.**
2. **Una recepción cuenta también como pedido.**
3. **Al corte solo cuenta lo ocurrido hasta el corte.**
4. **El aviso cubre fechas de calendario** desde `pedir − 2 días hábiles` (con feriados) hasta el día anterior a `pedir`.
5. **Sin alerta** (el plan no la fija): pedido después de la fecha límite pero antes de necesitarse, y material sin
   recibir pasada la fecha en que se necesitaba. **Por decidir (Eugenio):** «{insumo} no ha llegado».
6. **Causa sugerida:** se compara la primera recepción con el primer día de esa partida en el plan de la línea base vigente,
   no con el `se_necesita` del material; un material no recibido no sugiere causa. `CAUSA_COMPRA_TARDIA` es constante propia.
7. **Línea base:** la procura y la mesa usan la última declarada; sin línea base, la versión vigente sin fechas y con aviso.
8. **Plazo:** entero de 0 a 365 días hábiles, por obra y material; se reemplaza sin dejar constancia. **Por ratificar.**
9. **Precio de la compra** en la moneda de la carpeta (409 sin moneda); solo la recepción con precio crea observación.
10. **Cantidad exacta** en la API («126.0»).
11. **Texto «{insumo} no está pedido»** tal como lo fija el plan; propuesta «no se ha pedido». **Por decidir.**
12. `POST /compras` y `PUT /plazos` devuelven 204.
13. Fechas en los textos con `%d/%m/%Y` (`aplicacion/cifras.py` no tiene formateador de fechas).
14. Oráculo corregido después del rojo (3040d9e6): la clave primaria `id` de `mp_compra` es NOT NULL; era un supuesto de la
    base de pruebas.
15. Árbitro (ronda 1): fronteras y fechas de la mesa recalculadas a mano (al 02/11 «Pida Material de Tuberia de drenaje
    antes del 04/11/2026.»). Una recepción con precio de un material sin código de catálogo se guarda sin observación de
    mercado y sin avisarlo. El `precio` de la recepción es unitario. Menores que pasan a T24: exponer `causa_sugerida`,
    prueba de la mesa al 02/11, descripción del precio y `monkeypatch` sobrante.

## T19, enviar y dictamen en la mesa (aprobada en ronda 1)

1. Quien arma también ve en su grupo «Aprobar» los envíos de OTRAS carpetas (de `GET /v1/aprobaciones/pendientes`); los
   de la carpeta abierta los dice ya `/v1/obras/pendientes`. **Por ratificar.**
2. Quien solo revisa ve la columna Pendientes con un único grupo «Aprobar».
3. «Abrir» de otra carpeta usa `abrirCarpeta(nombre, undefined, abrirCon)`: misma pregunta
   (`confirmarSalida("carpeta", borradores)`), `POST /v1/aprobaciones/abrir` en vez de `POST /v1/casos/actual`, relectura
   de la carpeta y aviso; luego navega a `/aprobar?envio=`. Uno de la carpeta abierta no llama a `/abrir`.
4. El aviso «Ahora trabaja con la carpeta…» se cierra al llegar a /aprobar: T20 debe decir de qué carpeta es el envío.
5. «Ver el envío» de `/v1/obras/pendientes` y de la tabla no trae `envio_id`: T20 debe resolver el envío pendiente de la
   obra elegida.
6. «Por aprobar» con `IndicadorFiori`: Δ son días hábiles de espera, no actual − meta; marca «Hay versiones esperando
   dictamen desde hace días: revíselas pronto.» **Por ratificar.**
7. Hoja: un 5xx al leer el estado lo dice; un 403 o 404 no dice nada; «Retirada · …» es la sexta etiqueta y permite
   volver a enviar.
8. `abrirCarpeta` gana un tercer parámetro opcional (`abrirCon`) en `useCarpetaDeTrabajo.ts` y `contexto.tsx`
   (compatible).
9. Menores del árbitro (adceb0af rojo, 9759890c): la barra dice la carpeta del envío abierto; «Por aprobar» se sostiene
   aunque el resumen de obras dé 403 o falle; `nombreDeResponsable` vive en `src/comun/responsable.ts`; en el grupo
   «Aprobar» toda fila dice «Abrir el envío» y las de la carpeta abierta salen del índice (total, quién, cuándo y su envío)
   en lugar del «espera dictamen» de la API, que solo queda si el índice no está. `Retomar.test.tsx` no se reprodujo
   (32/32 cuatro veces): probablemente se corrió con cambios a medias de T26 en el árbol.

## T26, líneas del APU de la versión

- **Altas y bajas de líneas.** Las líneas de cada rubro se alinean por su descripción (`difflib.SequenceMatcher`): la que
  sale es `baja` y la que entra `alta`, clave `{partida}|{tipo}|{n}` (n desde 1 en su rubro). El oráculo del plan
  («OBRA-02|material|5») no cabe en la vivienda: OBRA-02 tiene un material y la línea nueva es la 2.ª.
- **Solo en una versión guardada** (409 propio): la primera versión exige que cada APU tenga las líneas del catálogo
  (`con_precios_de_la_lista`), así que en un borrador en blanco no se ofrece.
- **Insumo del catálogo:** precio de la lista de la versión; lo tecleado no cuenta. **Insumo nuevo:** descripción ≤ 300,
  unidad ≤ 20; equipo con depreciación (0, 1]; mano de obra jornal o destajo. Un insumo ya presente en el rubro se rechaza
  («edítelo en la tabla»). Se aceptan cantidad 0 y precio 0. **Por ratificar.**
- Los mensajes empiezan por el campo y no repiten lo tecleado; la pantalla ubica el error por ese inicio.
- Al guardar, el núcleo resuelve el insumo de cada línea por tipo y descripción: una línea nueva sin homónimo queda con
  `insumo_id` nulo y su precio no lo pisa una revaloración; un «insumo nuevo» con la misma descripción que uno del catálogo
  se liga a él. **Por decidir.**
- **Antes y después:** por partida cambiada respecto de la línea base vigente, cada una sola: costo directo unitario,
  duración y término por rendimientos (T21, una cuadrilla, las paralelas del plan base) y punto de equilibrio con
  `equilibrio_proyectado`. **Por ratificar.** La ruta va en `/v1/hoja/antes-y-despues` (`editar_hoja`) porque T22 editaba
  `api/rutas/control.py`; se monta en Control › Recuperación.
- **Edición mientras se quita:** la tabla del APU queda deshabilitada (fieldset) hasta la respuesta; agregar usa un diálogo
  modal y `esperarEnvios`; tras aceptar, lo editado se vuelve a sembrar sin tocar `useEdicionDeSeccion`.
- Corrección: los cambios del borrador ya no pierden ni corren las líneas de un APU cuando cambia su número (antes se
  emparejaban por posición). La ayuda del APU decía «la coma no se acepta» (contradecía la regla del 2026-10-25): corregida.
- **Menores del árbitro de T26, cerrados** (pruebas en rojo: `ca7e0d75`): líneas homónimas (se alinean primero enteras, con cantidad y precio, y luego por descripción), versión en otra moneda que la línea base (`MonedasDistintas`: el antes y después lo dice en vez de mezclar montos) y el diálogo de agregar línea como formulario sucio con solo la unidad, la depreciación o la modalidad.

## MOD-4a, mesa de control (aprobada en la ronda 2)

1. **Corte sin valuaciones.** El corte de una obra con línea base es el «hasta» de su última valuación no anulada; sin
   valuaciones, `hoy` (el día del servidor). Si con ese corte el control no se puede calcular (la línea base rige más
   tarde), la obra queda «En ejecución» con «Sin avance registrado». Si el plan ya empezó y no hay valuaciones, el SPI es
   0: «Atrasada (SPI 0,00)», sin días, y entra en la suma con EV 0. **Por decidir (Eugenio):** contarla así o como «Sin
   avance registrado».
2. **Texto fijo en vez del mensaje del núcleo (desvío consciente de la letra del plan).** Con valuaciones, un
   `ControlInvalido` dice «No se pudo calcular el avance; ábralo en Control para ver el motivo.»; el mensaje del núcleo
   sale sin tildes y con fechas ISO. EV y PV quedan vacíos y el siguiente paso es «Registrar el avance».
3. **Fecha de la tasa.** Una obra en la otra moneda se convierte con `tasa_aplicable` al corte (a lo sumo 7 días antes).
   La conversión declara `fecha` (el corte) y `fecha_tasa` (la fecha valor de la tasa). La firma de `cifras_de_la_mesa`
   recibe `Callable[[date], TasaDelBcv | None]` en vez de `Decimal | None`. Sin tasa de los últimos 7 días, la obra va a
   `fuera_de_suma`.
4. **Moneda del resumen.** La de la carpeta; sin ella, la común de las obras en ejecución; `null` si no se sumó nada.
5. **Versión y total.** Los de la versión de la línea base; sin línea base, los de la vigente. Los pendientes miran la
   vigente.
6. **«Sin referencia».** Insumos de la composición congelada con fila de precio en la lista de la versión y sin
   `referencia_precio` ni `precio_origen`.
7. **Atrasadas fuera de la suma.** El detalle de «Avance contra el plan» cuenta todas las atrasadas, también las que no se
   sumaron por falta de tasa. Los enteros de los textos llevan punto de miles.
8. Aviso: cuando se integre la fuente «cantidades sin cálculo» (T9), el oráculo del grupo «Calidad» de
   `tests/unit/test_api_obras_resumen.py` debe actualizarse.

## MOD-4b, mesa de control (front)

1. **Dos cifras en el esqueleto.** La API sirve hoy como mucho dos (valor ganado y avance); el esqueleto dibuja esa forma
   con `CIFRAS_DEL_RESUMEN = 2` (`src/paginas/obras/CifrasMesa.tsx`), que sube a tres cuando exista «Por aprobar» (§12.6).
2. **Columna de pendientes a `calc(380px * var(--silice-escala-letra))`.** Mide 380 px con letra Normal y crece con la
   escala, como el sidebar fijado (choque 13). Dos columnas por consulta de contenedor desde 60 rem; el rem de la consulta
   es el de la raíz, que sigue la escala. **Por ratificar** (MOD-5 mide 1056 y 1366 px con las tres letras).
3. **Accesos si todo da 403.** Si todos los bloques pedidos resultan prohibidos, la mesa muestra «Lo que puede hacer
   aquí» en vez de quedar solo con el h1. Sin columnas vacías: la de obras solo existe si el resumen no dio 403 y la
   rejilla solo tiene dos columnas con las dos (ronda 2).
4. **El aviso de un fallo del resumen va una sola vez, en «Obras».** Cifras y obras salen de la misma respuesta; la
   franja no se pinta. Con cero obras tampoco se pinta la franja: el vacío del bloque de obras enseña qué hacer.
5. **«Nueva obra» de la cabecera se oculta en el vacío**, donde «Cree su primera obra» hace lo mismo (sin dos botones
   principales iguales). **Por ratificar.**
6. **«Ver el envío» (pantalla `aprobar`) no se ofrece mientras esa pantalla no esté en `rutas.ts`.** Un botón de la mesa
   (siguiente paso o acción de un pendiente) solo aparece si su pantalla existe y es visible para la cuenta; la columna
   «Siguiente paso» solo existe si alguna fila trae uno. Cuando se registre `aprobar` (T20), aparece sola. Las etapas
   `en_aprobacion` y `aprobada` se leen con su `etapa_texto`.
7. **Conversión con la fecha de la tasa.** «C convertida a Bs con la tasa del BCV de 40,00 del 22/10/2026» usa
   `fecha_tasa`, no el corte.
8. **Ronda 2: la mesa sigue a la obra recién creada.** `alCrearObra` del armazón no vuelve a montar la página; la mesa
   lo resuelve sola: si la obra elegida (`proyecto`) no está en la tabla ya cargada, se vuelve a montar y pide de nuevo
   resumen y pendientes, una sola vez por obra. Elegir una obra que ya está en la tabla no repite la lectura.
9. **Ronda 2: la demostración pregunta antes de estrenarse** (`abrirCarpeta(nombre, preparar)`): con «Quedarme» no hay
   `POST /v1/casos/demostracion`.
10. **Ronda 2: accesibilidad.** La línea de las atrasadas es la descripción del grupo de su cifra (`IndicadorFiori` gana
    `idDescripcion` opcional); el botón de un pendiente se describe con su obra y su texto.
11. **Fuera de `src/paginas/obras/**`**, dos props opcionales y compatibles: `AccesosDelModulo` gana `titulo` («Lo que
    puede hacer aquí») e `IndicadorFiori` gana `idDescripcion`.
12. **Decisiones para Eugenio:** quien revisa (rita) no ve el grupo «Aprobar» porque `/v1/obras/pendientes` exige
    `editar_hoja`; la cifra «Por aprobar» (§12.6) no la sirve todavía `GET /v1/obras/resumen`.

## Migraciones del caso

Tres tareas a la vez colgaron su migración de `caso_0010_mp_carpeta`. El orden fijado es
`caso_0010_mp_carpeta → caso_0011_mod_ficha_obra → caso_0013_mp_mercado → caso_0014_mp_aprobacion`; `caso_0012` queda
para la medición (T9). Entre los commits 5411bf3e y 94e22a3c la cadena apunta a una revisión que todavía no estaba
confirmada; un `git bisect` en ese tramo debe saltarlos.
