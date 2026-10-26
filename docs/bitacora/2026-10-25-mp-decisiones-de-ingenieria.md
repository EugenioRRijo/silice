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

## Migraciones del caso

Tres tareas a la vez colgaron su migración de `caso_0010_mp_carpeta`. El orden fijado es
`caso_0010_mp_carpeta → caso_0011_mod_ficha_obra → caso_0013_mp_mercado → caso_0014_mp_aprobacion`; `caso_0012` queda
para la medición (T9). Entre los commits 5411bf3e y 94e22a3c la cadena apunta a una revisión que todavía no estaba
confirmada; un `git bisect` en ese tramo debe saltarlos.
