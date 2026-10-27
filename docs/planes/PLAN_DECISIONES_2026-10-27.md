# Plan: decisiones de Eugenio del 2026-10-27 (T4, T24/T25, T16)

Fuente: respuestas de Eugenio del 2026-10-27 a las decisiones abiertas de `docs/bitacora/2026-10-25-mp-decisiones-de-ingenieria.md`
(T25 punto 2, T16 «en otra moneda… sin margen») y de la Tarea 4 de `PLAN_REDISENO_MARCO.md`. Mismas restricciones
globales que `PLAN_REDISENO_MARCO.md`: `core/` intacto, TDD con rojo visto, árbitro por tarea (`MANUAL_ARBITRO.md`),
un agente a la vez, sin navegador salvo al cierre.

## Lo que decidió Eugenio

1. **T4:** «el servidor debe aprobar»: al elegir una obra, el servidor comprueba que existe.
2. **T24/T25 (y T16):** «si llega una moneda distinta se hace la equivalencia, y tener en cuenta que un presupuesto va a
   tener diferentes audiciones con los socios y economistas de la empresa». Un precio en otra moneda **no se rechaza**:
   se convierte con la tasa del BCV, y la conversión queda a la vista y reconstruible para quien revise después.
3. Fecha de llegada como inicio del precio del corte (Procura) y casilla oculta mientras se confirma (Estudio de
   mercado): Eugenio no las objetó; quedan como están.

## Tarea D1: el servidor comprueba que la obra existe al elegirla

**Archivos:** `api/rutas/sesion.py` (`PUT /v1/sesion/proyecto`, `recordar_obra`), su prueba de API, `docs/api.json`,
`CHANGELOG.md`; en el front, solo si hace falta, `marco/useObraDeLaRuta.ts` (el estado `no_existe` ya existe).

- La obra pedida debe existir en la carpeta de la petición; si no, **404** con texto fijo «Esa obra ya no existe» (sin
  eco del identificador, `RutaSinEco`), y **no** se guarda la elección. Una obra que existe: igual que hoy.
- Reutilizar la comprobación existente (`_obra_sigue` u otra de `aplicacion/`), no escribir una nueva.
- Pruebas en rojo: obra inexistente → 404 y la elección recordada no cambia; obra borrada entre dos peticiones → 404;
  obra existente → 200 como antes. Front: el 404 lleva a «Esa obra ya no existe» (si ya lo hace, prueba que lo fije).

## Tarea D2: precio del corte en otra moneda se convierte con la tasa del BCV

**Archivos:** `aplicacion/control.py`, `aplicacion/tablas_corte.py` (y migración nueva si hace falta guardar la
conversión), `aplicacion/mercado.py`, `aplicacion/procura.py` o donde viva la casilla, `api/rutas/control.py`,
`api/rutas/mercado.py`, `api/rutas/procura.py`, sus pruebas, el front de las dos casillas y de la vista del corte,
`docs/api.json`, `CHANGELOG.md`, bitácora.

- Hoy un precio declarado en otra moneda que la obra da 409 (T25 punto 2). Pasa a **convertirse** con la tasa del BCV
  **de la fecha del precio** (la fecha declarada; en Procura, la fecha de llegada), con la misma regla, redondeo y fuente
  de tasa que ya usa la conversión de versiones y listas (`aplicacion/hoja.py` `convertir`,
  `aplicacion/listas_para_armar.py` `_tasa`): **no** se escribe otra aritmética de conversión.
- **Rastro para las revisiones (socios y economistas):** se guarda el precio original (monto y moneda), la tasa usada,
  la fecha de la tasa, su fuente y el resultado. Nada se sobrescribe (la tabla sigue siendo de solo inserción). La
  pantalla del corte y la de Procura muestran la equivalencia en una línea: «31,50 USD × 36,50 Bs/USD (BCV del
  20/10/2026) = 1.149,75 Bs», con coma decimal y punto de miles.
- Sin tasa del BCV para esa fecha: **409** con texto claro («No hay tasa del BCV del 20/10/2026 para convertir este precio
  a Bs. Cargue la tasa en Índices y vuelva a intentarlo.»), y no se guarda nada (todo o nada con la compra o la lista).
- Pruebas en rojo con oráculo a mano: USD→Bs y Bs→USD con una tasa sembrada; sin tasa → 409 y nada guardado; el rastro
  trae original, tasa, fecha y fuente; el unitario del corte usa el convertido; una versión sellada no cambia.

## Tarea D3: observaciones del estudio de mercado en otra moneda se citan convertidas

**Archivos:** `aplicacion/mercado.py`, `api/rutas/mercado.py`, el front del estudio de mercado, sus pruebas, api.json,
CHANGELOG.

- Hoy una observación en otra moneda no se cita y el objetivo en otra moneda sale «sin margen» (T16). Pasa a citarse
  **convertida** con la tasa del BCV de la fecha de la observación, con el mismo rastro y la misma línea de equivalencia
  que D2, reutilizando lo que D2 deje. Sin tasa para esa fecha: la observación sale con «sin tasa del BCV del
  dd/mm/aaaa» y no entra en las estadísticas (se cuenta aparte, como hoy `otras_monedas`).
- Pruebas en rojo con oráculo a mano: estadísticas con una observación convertida; observación sin tasa fuera y contada.

## Tarea D4: entregar sin aprobar queda rotulado y con la cadena rota se puede devolver (T20)

Eugenio decidió el 2026-10-27: (a) **avisar y rotular**: se puede entregar una versión no aprobada, pero el paquete y su
rastro lo dicen claramente; (b) con la **cadena de versiones rota se permite devolver** (devolver no certifica nada),
y aprobar (también «aprobada con observaciones») sigue bloqueado hasta reparar la cadena.

**Archivos:** `aplicacion/entregas.py` (o donde se arma el paquete y su evento), `aplicacion/aprobaciones.py`,
`api/rutas/entregas.py`, `api/rutas/aprobaciones.py`, el front de Entregar y de Aprobar, sus pruebas, api.json,
CHANGELOG, bitácora (cierra los «Por ratificar» de T20 punto 4 y del T18/T19 «cadena rota»).

- (a) Al entregar una versión que no es una aprobada, el paquete lleva en su portada/índice y en su manifiesto la marca
  «Versión NO aprobada» (con la fecha y, si la hay, la última aprobada que no se eligió), y el evento de la entrega lo
  registra. La pantalla lo avisa antes de confirmar. Una versión aprobada no lleva la marca. El manifiesto firmado
  cubre la marca (no se puede quitar sin romper la firma).
- (b) Con la cadena rota, `POST` del dictamen acepta **solo** «Devuelta» (con notas obligatorias, como hoy); «Aprobada» y
  «Aprobada con observaciones» siguen en 409 con el motivo. La pantalla Aprobar ofrece solo «Devolver» y dice por qué.
- Pruebas en rojo: paquete de una no aprobada lleva la marca en manifiesto y portada, y la de una aprobada no; la firma
  falla si se quita la marca; con cadena rota devolver da 200 y aprobar 409; el front muestra solo «Devolver».

Orden: D1 → D2 → D3 → D4 → menores agrupados → cierre (suite completa).
