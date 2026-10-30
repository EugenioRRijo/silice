# Plan vial, fase A: decisiones de implementación

## Tarea 3: receta de la planta y consumos al producir mezcla

- **Componente propio solo en toneladas.** Un componente `propio` sale del inventario de la arenera,
  que mueve toneladas o m3; los litros (gasoil, aditivos) solo pueden ser `comprado`. Una receta con
  un propio en litros se rechaza.
- **`TOLERANCIA_MASA` en el registro de `produccion/fuentes.py`**, no en la `Constante` de
  `adapters/espacio/especialidades` que nombra el plan: RT-7 (`tests/unit/test_arquitectura.py:235`)
  prohíbe que `produccion/` importe `adapters/`. Es 0,02 t por t de mezcla, «supuesto declarado» que
  la empresa debe confirmar con su dosificación real.
- **Bajar `ins_0007_prod_receta` borra los movimientos `consumo`**, porque el `CHECK` anterior no los
  admite. Es lo que hacen todas las bajadas del repositorio (DA-S5-6): el downgrade nunca se ofrece
  al usuario, solo existe para las pruebas y el ensayo de migraciones.
- **Una sola regla de cuantización t a unidad de venta** (`produccion.inventario.de_toneladas`): en m3
  es toneladas / densidad con cuatro decimales y redondeo de mitad al par (`ROUND_HALF_EVEN`), la
  que ya usaba la importación de báscula; ahora la reutiliza (`_cantidad_de_despacho`). Oráculo a
  mano: 100 t de mezcla × 0,94 con agregado propio en m3 de densidad 1,7 consume 94 / 1,7 =
  55,29411... = 55,2941 m3. Sin densidad (o no positiva) es error que nombra el material.
- Una receta admite como máximo 50 componentes (422 si trae más).

## Tarea 4: costo por tonelada del período, guardado con sus entradas

- **Router dividido antes de empezar** (pedido del árbitro de la Tarea 3): costos, recetas y
  producciones pasan de `api/rutas/produccion.py` (900 líneas) a `api/rutas/produccion_planta.py`,
  con el mismo prefijo, etiqueta, puertas, `RutaSinCache` y orden de registro (justo después del de
  la arenera en `api.main`). Commit `refactor` aparte: `docs/api.json` quedó idéntico y las pruebas
  pasaron sin tocarlas. `_ahora` se quedó en `produccion.py` (las pruebas lo fijan allí); el módulo
  nuevo lo busca en su módulo en cada llamada. Las rutas de cálculo van al módulo nuevo.
- **Qué es mezcla**: un producto con receta registrada que rija al último día del período
  (`receta_vigente(producto, cierre)`); todo lo demás producido es agregado. La cantera se reparte
  solo entre los agregados (condición del árbitro: `producido_en_periodo` trae la mezcla, que no
  recibe cantera) y la planta, por tonelada, entre las mezclas.
- **Receta de cada producción (decisión del orquestador)**: cada entrada de mezcla del período usa
  la receta vigente **en su fecha** (`receta_vigente(producto, fecha)`), sin leer la `nota` del
  movimiento; una entrada de mezcla sin receta en su fecha es error que la nombra. La mezcla del
  período es `planta por t + Σ(t_r × componentes_r) / Σ t_r`; la instantánea guarda cada receta usada
  (id, componentes) con sus toneladas. Con una sola receta da exactamente sus componentes (no se
  pierden cifras al multiplicar y dividir por las mismas toneladas). Para eso se añadió
  `produccion.inventario.entradas_del_periodo` (una fila por entrada, con su fecha);
  `producido_en_periodo` ahora la suma y no cambia su resultado.
- **Guardas (Foco 2 ampliado)**: la suma de los montos vigentes en su moneda original se compara con
  cero **antes de convertir**: ninguno, todos anulados o todos en 0 dan «No hay costos registrados en
  AAAA-MM.» (un 0 en Bs de un sábado no pide tasa); sin entradas, «No hubo producción en AAAA-MM.».
  Además, para no publicar un costo cero ni dejar costos sin dueño: costos de cantera sin agregados
  producidos, agregados sin costos de cantera, costos de planta sin mezcla, una mezcla cuyo agregado
  propio no se produjo en el período (no se toma el costo de otro mes) y, al final, cualquier costo
  por tonelada que dé cero o menos. Todo antes de escribir.
- **Moneda (Foco 1)**: cada costo en otra moneda se convierte con la tasa BCV del día exacto de su
  fecha (`equivalencia_del_dia`). El precio de lo comprado sale de la lista global vigente de la
  carpeta **al último día del período** (`Catalogo.lista_vigente`); si esa lista está en otra moneda,
  se convierte con la tasa del día de su `fecha_vigencia`, que es la fecha del precio. Las faltas de
  tasa de costos y de la lista se juntan en un solo `FaltanTasas` que nombra cada costo («costo n.º 7
  del 07/11/2026») y la lista; no se calcula ni guarda nada. Una regla igual para todo monto en otra
  moneda, también uno en 0 si hay otros costos.
- **Unidad de lo comprado**: la unidad del insumo en la lista debe ser la de la receta
  (`core.contracts.unidades.unidades_equivalentes`); si no, error que nombra el código y las dos
  unidades. Ojo: «ton» y «t» no son alias en la tabla del núcleo, así que una lista con «ton» se
  rechaza con ese mensaje, y lo mismo «lt» o «litro» frente a «l» (ver pregunta 17). Un insumo sin
  unidad en la lista se acepta.
- **Exacto y presentado**: toda operación con 28 cifras y mitad al par fijadas dentro de
  `produccion/costo.py` (no dependen del contexto del hilo; las mismas de
  `core.catalog.moneda.convertir`); se guarda así y se redondea solo al presentar (dos decimales,
  mitad hacia arriba). Constantes `CIFRAS_DEL_CALCULO`, `DECIMALES_AL_PRESENTAR` y `MAX_PESOS` en
  `produccion/fuentes.py`.
- **Instantánea**: JSON canónico (claves ordenadas, sin espacios, `ensure_ascii=False`), decimales
  como texto (`format(x, "f")`), fechas ISO, ids de costos, recetas y lista como enteros JSON (la
  prueba del rojo prohibía todo número y contradecía a la de la receta; se corrigió en un commit de
  prueba aparte antes del verde). Su huella es el SHA-256 del texto; no entran ni el usuario ni la
  hora, así el mismo cálculo da la misma huella. Recalcular inserta otra fila. Al leer un cálculo se
  comprueba la huella: si alguien cambió la instantánea, «fue alterado».
- **Reparto por pesos**: opcional (`pesos`, también en la API); los pesos deben cubrir exactamente
  los agregados producidos, ser mayores que cero (un peso cero daría un costo cero) y sumar 1 exacto.
- **`ultimo_calculo(producto)`**: el de mayor número que da costo a ese producto, sea del período que
  sea (la Tarea 5 publica un cálculo concreto, no éste).
- **API**: `POST /v1/produccion/calculos` y `GET /v1/produccion/calculos/{calculo_id}` con la puerta
  del router y la de costos (`REGISTRAR_COSTOS`: un cálculo lee los costos). La carpeta es la de la
  petición (`SesionDep`). Toda negativa es 422 con su mensaje (el manejador de `ValueError`); un
  cálculo inexistente, 404. Los esquemas se llaman `CalculoDeCosto*` y `CostoDeProducto` porque
  `CalculoRespuesta` ya existe en otra ruta (un nombre repetido renombra los dos en `docs/api.json`).
- **Del plan al código**: `CalculoGuardado` lleva además `usuario`, `registrado` e `instantanea` (con
  valor por omisión; la Tarea 5 usa `id`, `periodo` y `por_tonelada`).

### Tarea 4, ronda 2 (devolución del árbitro)

- **Columnas que la huella no cubre**: `periodo` y `moneda` de `prod_calculo` solo sirven para
  buscar; al leer un cálculo salen de la instantánea verificada y, si las columnas no dicen lo mismo,
  «fue alterado» (422 por la API). Antes, cambiar la columna `moneda` devolvía un cálculo en USD
  rotulado en Bs sin error. `usuario` y `registrado` siguen fuera de la huella a propósito (el mismo
  cálculo de dos personas da la misma huella).
- **Mezcla sin costos de planta (decisión del orquestador)**: se niega, simétrico a «agregados sin
  costos de cantera»: «No hay costos de planta en AAAA-MM para las mezclas MZ-1: …». Antes salía con
  planta 0 (MZ-1 a 38,70 en vez de 50,70).
- **Pesos sin agregados producidos**: error en vez de ignorarlos y guardar «por pesos» sin validar.
- **Tope de pesos**: se prueba en el esquema `CalculoDeCostoEntrada` (50 entra, 51 no).
- **Regresión de la Tarea 1 corregida**: `test_api_sesion_web.py` fijaba la lista literal de
  acciones de arma sin `registrar_costos_produccion`, que la Tarea 1 le dio a propósito (lo pide el
  plan y la pantalla de existencias la usa). Se corrigió el oráculo, no el permiso.
- **Deuda anotada, no se toca ahora**: `api/rutas/produccion_planta.py` importa nombres privados de
  `api/rutas/produccion.py` (`_decimal`, `_fecha` y `_ahora` por el módulo). Lo limpio es un módulo de
  frontera común con nombres públicos; las pruebas fijan `api.rutas.produccion._ahora`, así que
  moverlo exige tocar esas pruebas.

## Tarea 5: publicar el costo propio al catálogo

- **Qué se publica**: un cálculo concreto, por su número (`calculo_guardado`: huella y columnas
  verificadas; uno alterado da 422 «fue alterado» y no se escribe nada). Su `periodo` y su `moneda`
  son los de la instantánea, nunca `ultimo_calculo`. La ruta `POST /v1/produccion/calculos/{id}/publicar`
  recibe `empresa_nombre` y `empresa_rif` (la empresa es texto, como en la lista de empresa de UC-17)
  y responde 201 con el id y el nombre de la lista. Cálculo inexistente: 404.
- **Valor exacto (decisión del orquestador, pregunta 18)**: el precio publicado es el `DecimalExacto`
  del cálculo, no el redondeado a dos decimales (el plan: se redondea solo al presentar). Con
  1.001 USD de cantera sobre 200 t el agregado queda en 5,005 y no en 5,01. Cambiarlo es una línea
  en `publicar_calculo` y una prueba.
- **Lista nueva cada vez, de alcance de empresa**: `crear_lista_de_empresa` escribe
  `ListaPreciosOrigen(alcance="empresa")`, que `lista_vigente` excluye (`ALCANCES_FUERA_DE_VIGENTE`).
  Está probado (nota 2 del árbitro de la T4): tras publicar, `lista_vigente` del 31/12 sigue siendo la
  de la carpeta y el cálculo de diciembre toma `CA-30` y `GO` de ella (`precios_comprados[..].lista.id`).
  Nada se sobrescribe: publicar dos veces el mismo cálculo da dos listas y un solo insumo.
- **Base y fecha**: la base es la lista global vigente de la carpeta al último día del período
  (`lista_base_del_periodo`; sin ella 422 «No hay lista de precios vigente…»). La lista y cada precio
  llevan como fecha ese último día. Si la base está en otra moneda que el cálculo, se lleva a la
  moneda del cálculo con la tasa BCV aplicable a esa fecha (`tasa_aplicable`, hasta 7 días antes,
  como UC-17); sin tasa, 422 y no se escribe nada.
- **Insumos propios (D-V-2)**: `AGP-<código>` para lo que la instantánea lista como agregado y
  `MZP-<código>` para el resto (mezclas), material en t; se dan de alta una vez. Un código de más de
  20 caracteres (el límite de `Insumo.codigo`; el material admite 40) se niega nombrándolo, y un
  insumo existente con otro tipo o unidad también. Con el código de material `MZ-1` el insumo es
  `MZP-MZ-1` (el plan citaba `MZP-01` suponiendo materiales llamados `01`).
- **Trazabilidad**: la fuente de cada precio es exactamente «Producción, período AAAA-MM, cálculo
  n.º N»; la de la lista añade quién publicó (cuenta del servidor), la hora del servidor y los
  primeros 16 caracteres de la huella. El cuerpo no lleva `ahora` ni usuario (si los trae, se
  ignoran).
- **Permiso**: acción nueva `publicar_costo_propio`, solo administrador; se exigen la del router
  (`OPERAR_ARENERA`) y ésta, así que arma y revisa reciben 403. La clave de API, como en el resto de
  `/v1/produccion`, también sirve. El oráculo de acciones de arma en `test_api_sesion_web.py` no
  cambia (arma no la tiene).
- **Confirmación**: el servicio no hace `commit`; la ruta confirma la carpeta del caso al final. Una
  negativa en medio no deja insumos ni listas a medias.
- **Ajuste en el verde**: dos oráculos del commit de prueba estaban mal escritos (el código largo del
  caso de prueba es una mezcla, o sea `MZP-…`; y el usuario guardado es el nombre completo de la
  cuenta) y se corrigieron junto con la implementación.
