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
  rechaza con ese mensaje (ver pregunta 17). Un insumo sin unidad en la lista se acepta.
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
