# Montar un presupuesto: decisiones de ingeniería de las tareas (2026-10-25)

Decisiones tomadas por los implementadores de `docs/planes/PLAN_MONTAR_PRESUPUESTO.md` que el plan no fijaba, anotadas a
pedido de sus árbitros. Las marcadas «por ratificar» esperan a Eugenio; las demás son de ingeniería y quedan como están.

## T10, buscador de partidas (aprobada en ronda 1)

- El oráculo del diseño §8.1 («`q=tub` devuelve solo LB-02-TUB») no se cumple con la línea base: LB-01-EXC dice «zanja de
  tubería». Por la regla 2 de §5.2 las dos son de rango 3 y el orden es [LB-01-EXC, LB-02-TUB]. La prueba usa ese oráculo.
- El modo local del campo (`opciones`) queda para el plan de autocompletado, como dice T10; `buscar` es obligatoria.
- Falta verificar en navegador la F0 de §4.3 (lista en portal con `enCelda` a 1056 px y letra al 150 %). Se hace antes de
  que una página use `enCelda`; T11 usa el campo en un diálogo.
- Menor cosmético pendiente: el 403 repite «Su cuenta» («Su cuenta no puede usar esta búsqueda. Su cuenta no tiene permiso…»).

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

## Migraciones del caso

Tres tareas a la vez colgaron su migración de `caso_0010_mp_carpeta`. El orden fijado es
`caso_0010_mp_carpeta → caso_0011_mod_ficha_obra → caso_0013_mp_mercado → caso_0014_mp_aprobacion`; `caso_0012` queda
para la medición (T9). Entre los commits 5411bf3e y 94e22a3c la cadena apunta a una revisión que todavía no estaba
confirmada; un `git bisect` en ese tramo debe saltarlos.
