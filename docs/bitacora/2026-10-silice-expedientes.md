# Expedientes del núcleo de Sílice 0.6.0 (SL‑E1, SL‑E2, SL‑E3)

**Contenido de este archivo:** SL‑E1 (rama `inc/060-s1-1-nucleo`, fusionada) y SL‑E2 (rama
`inc/060-s1-3-nucleo`). SL‑E3 lo continúa en su propia rama (`inc/060-s1-4-nucleo`).

**Fecha:** 2026‑10‑11 · **Rama:** `inc/060-s1-1-nucleo` (sale de `origin/main` con S5‑1 y S1‑0 fusionados) ·
**Plan:** [PLAN_SILICE_060.md](../../PLAN_SILICE_060.md), sección C, tareas 4 y 5 ·
**Spec:** [2026-10-11-silice-s1-moneda-reajuste-design.md](../especificaciones/2026-10-11-silice-s1-moneda-reajuste-design.md)
§4 a §6 y §11 · **Bitácora de la versión:** [2026-10-silice-060.md](2026-10-silice-060.md).

Cada expediente sigue el método de C5 y C6
([2026-09-28-C5-expedientes.md](2026-09-28-C5-expedientes.md),
[2026-09-29-C6-expedientes.md](2026-09-29-C6-expedientes.md)) y de SF
([2026-10-sf-expedientes.md](2026-10-sf-expedientes.md)): la regla que lo motiva, por qué es genérico, el
diseño, la prueba que lo demuestra, el impacto y el costo si es erróneo. La prueba en rojo de cada pieza se
commitea **antes** que su implementación. Esta rama solo toca `core/`, `migraciones/`, `tests/` y `docs/`;
ningún contrato de `core/contracts/` cambia (NORMAS §5 y §9). La aprobación del tutor de los expedientes de
`core/` la declaró Eugenio el 2026‑10‑11: se fusiona con la CI verde.

## SL‑E1: moneda, tasa, origen por precio, conversión y erosión

- **Regla que lo motiva:** H‑D1 y RF‑64 a RF‑66 (spec S1 §1.1). Hoy un precio no dice su fecha ni su moneda
  original, una versión puede valorarse con una lista de otra moneda sin que nada lo impida, y no existe una
  serie de tasas fechadas con la que convertir ni medir cuánto valor perdió un precio en bolívares.
- **Por qué es genérico:** todo presupuesto tiene una moneda y todo precio una fecha, en cualquier dominio.
  Ningún nombre de este expediente es de una especialidad; la tasa es una serie fechada cualquiera y el
  organismo que la publica (BCV) solo aparece como dato (`organismo`) y como código de dos series de tasa.
- **Diseño:**
  1. Cinco tablas **aditivas** (ruling SF3‑E0) en `core/models/moneda.py`, módulo propio para no tocar
     `entidades.py`: `serie_indice`, `importacion_indice`, `valor_indice`, `moneda_proyecto`,
     `precio_origen`. Nacen con la revisión de Alembic `caso_0002_s1_moneda`, escrita a mano con la plantilla
     (`down_revision = caso_0001_base_0_5_0`, salida de `revision_head(Destino.CASO)`), con `op.create_table` y
     un `downgrade()` real. Ninguna altera una tabla existente.
  2. `core/catalog/indices.py`: series, importaciones idempotentes por huella SHA‑256 (una revisión de
     valores es otra importación; nunca se sobrescribe un valor guardado) y `tasa_aplicable` (S1‑R1: la de
     mayor fecha valor ≤ fecha del lado declarado; S1‑R2: más de 7 días naturales se rechaza, nunca se
     extrapola ni se usa una tasa vieja en silencio).
  3. `core/catalog/moneda.py`: `MONEDAS`, `convertir`, `TasaDeclarada` (valor, fecha y fuente, las tres
     obligatorias), `erosion` (`1 − T0/T1` sobre el valor, no sobre `P`), `erosion_por_indice` (columna
     aparte), `copiar_precios` y `convertir_lista`. Toda división con `localcontext(prec=28,
     ROUND_HALF_EVEN)` **dentro** de la función.
  4. `core/catalog/origen.py`: `OrigenEfectivo` y `origenes_efectivos`, la regla única de precedencia (la
     fila por precio prevalece; la lista es el respaldo de las bases anteriores); `OrigenPrecio` gana campos
     al final con valor por defecto; `crear_lista_de_proyecto` copia el origen de los precios no cotizados.
  5. `core/budget/moneda.py`: `moneda_del_proyecto`, `declarar_moneda` y `convertir_version`, que crea la
     versión por `guardar_presupuesto` (el único embudo, motivo `conversion`), una fila de `moneda_proyecto` y
     un `RegistroCambio` (objeto `moneda`, fuente = la tasa).
  6. `guardar_presupuesto` rechaza una lista de otra moneda (RF‑65) y una versión cuya moneda difiere de la
     declarada por el proyecto salvo que sea una conversión; `actualizar_precios` rechaza antes de escribir
     nada; `composiciones_revaloradas` gana `precio_sin_insumo` (por defecto conserva el precio, así que
     UC‑02 no cambia); `MOTIVOS_VERSION` gana `conversion` y `OBJETOS` gana `moneda`.
- **Prueba que lo demuestra:** `tests/unit/test_moneda.py` (la memoria `tests/fixtures/memorias/s1_conversion.md`,
  cifras a 28 dígitos con un contexto global de 6 dígitos y el contraste 26,37 % contra 35,81 %);
  `tests/integration/test_indices.py` (sábado con la tasa del viernes, 7 días pasan y 8 se rechazan,
  misma huella no escribe, revisión como otra importación con la citada vigente);
  `tests/integration/test_conversion_version.py` (oráculo independiente: total convertido = total × T a ±0,01,
  la clínica y TI‑001, ida y vuelta, monedas mezcladas rechazadas al guardar y al revalorar, restaurar en la
  moneda vieja rechazado, tasa incompleta sin filas); `tests/integration/test_migracion_s1.py` (las tres
  bases de prueba de la 0.5.0 suben a `head`, ganan las tablas y conservan filas, total y huella); la prueba de
  deriva y de ida y vuelta de B (`tests/integration/test_migraciones.py`) sin cambios.
- **Impacto:** tablas aditivas con su revisión; `guardar_presupuesto` gana una validación que ningún dato
  existente incumple (toda base anterior está en USD, con listas en USD y sin `moneda_proyecto`); dos
  constantes ganan un valor; `OrigenPrecio` gana campos con valor por defecto, así que sus constructores
  existentes siguen válidos. El bloque de regresión (cinco APU, 7 de 7, R4, TI‑001, huellas de RNF‑04,
  cuatro hojas) no se mueve.
- **Costo si es erróneo:** si se prefiere convertir solo al presentar, se retira `convertir_version` y la
  moneda del proyecto pasa a ser una preferencia de vista (H‑D1 queda a medias). Si la regla de los 7 días es
  mala, es la constante `DIAS_MAXIMOS_SIN_TASA`; si el lado por defecto es otro, es `LADO_POR_DEFECTO`
  (S1‑R1, supuesto declarado). Si una tabla debe cambiar, es una revisión más de Alembic, no una tabla rehecha.

## SL‑E2: lista de empresa, lista de referencia, R11, R12 e instantánea de precios

**Fecha:** 2026‑10‑11 · **Rama:** `inc/060-s1-3-nucleo` (sale de `origin/main` con S1‑1 fusionado) ·
**Plan:** tareas 7 (SL‑E2a) y 8 (SL‑E2b) de la sección C · **Spec:** S1 §6 y §11.

- **Regla que lo motiva:** H‑D8, RF‑67 y RF‑68 (spec S1 §6). Una empresa tiene precios propios que no son los
  de la lista global, y esos precios envejecen y se alejan del mercado sin que nada lo advierta. Una lista
  global de empresa secuestraría `lista_vigente` (la resolvería para todo proyecto que no nombre otra), y la
  lista MaPreX en Bs, cargada solo para contrastar, también.
- **Por qué es genérico:** cualquier empresa de cualquier especialidad tiene precios propios con fecha y
  fuente, y cualquier precio tiene una referencia contra la cual contrastarlo. Ningún nombre de este
  expediente es de una especialidad: la empresa es texto (`empresa_nombre`, `empresa_rif`, RV‑6), la
  referencia es "la lista de alcance `referencia`" (MaPreX es solo el dato que hoy la llena), y R11/R12
  hablan de precio, fecha, tasa y rango.
- **Diseño:**
  1. **Alcances.** `ALCANCE_EMPRESA = "empresa"` y `ALCANCE_REFERENCIA = "referencia"`, más
     `ALCANCES_FUERA_DE_VIGENTE = (proyecto, empresa, referencia)`. `Catalogo.lista_vigente` excluye los tres:
     una versión los referencia explícitamente (DA‑SF‑9). Sin el alcance `referencia`, la lista MaPreX en Bs,
     con fecha de vigencia posterior a la de la clínica, pasaría a ser la lista vigente de todo proyecto.
  2. **Tabla aditiva** `lista_empresa` (`core/models/moneda.py`; revisión `caso_0003_s1_lista_empresa`, a mano,
     `down_revision` = salida de `revision_head(Destino.CASO)` = `caso_0002_s1_moneda`, `create_table` solo de
     lo que falta, `downgrade()` real). La empresa es texto, una instantánea sin clave foránea a
     `instalacion.db`; el rango (−20 % / +30 %, S1‑R5) y el plazo (30 días, S1‑R6) se guardan por lista.
  3. **Lector.** `PrecioLeido` gana al final siete campos con valor por defecto (fecha, fuente, referencia,
     moneda, tasa, fecha de la tasa y su fuente) y el lector acepta siete columnas opcionales. Una cifra con
     coma decimal (`13.288,00`, `1,5`) se rechaza por fila con su número y el texto «use punto»; nunca se
     toma como otro número ni como cero. Una celda de texto en una columna numérica se rechaza igual.
  4. **`core/catalog/empresa.py`.** `precios_propios_desde`, `crear_lista_de_empresa` (copia de la base,
     convertida con su tasa si la moneda difiere, con los propios encima y su `PrecioOrigen`),
     `crear_lista_de_referencia`, `lista_de_referencia`, `es_heredado` (un precio es heredado si conserva el
     origen de la base) e `instantanea_de_lista`.
  5. **`core/verification/precios.py`.** R11 `PrecioFueraDeRango` y R12 `PrecioVencido` como reglas
     **externas** (S1‑R7): no entran en `REGLAS`, así la línea base sigue dando 7 de 7 y las huellas de
     RNF‑04 no se mueven. Cada regla guarda su `InstantaneaPrecios` con la **fecha de evaluación explícita**
     (nunca el reloj) y no lee el presupuesto que recibe. El desvío es `(p·T_ref)/(p_ref·T_p) − 1`, una sola
     división dentro de `localcontext(prec=28, ROUND_HALF_EVEN)`, sin cuantizar antes de comparar: el
     límite exacto pasa y un diezmilésimo más no. La reevaluación a otra fecha es solo en memoria: ninguna
     función de este expediente escribe ni reescribe `Hallazgo`. La erosión llega precalculada en
     `PrecioAuditado`, de modo que el módulo importa solo contratos y el motor (`calcular_apu`).
  6. **`instantanea_precios`** (`core/budget/instantanea.py`; el spec la ubicaba en `origen.py`, pero necesita
     las composiciones congeladas, que solo lee `core/budget`, y `core/catalog` no importa `core/budget`):
     el impacto de cada hallazgo se lleva al total de la versión con `calcular_apu` sobre sus composiciones
     y parámetros; una partida irreconstruible no entra. Sin versión (lista sola) el impacto es por unidad.
  7. **Un día sin tasa no revienta.** Sin tasa a la fecha del precio (más de 7 días, S1‑R2) R11 lo cuenta
     como no contrastable en su INFO y R12 vencido sale con impacto `None` diciendo «sin tasa».
- **Prueba que lo demuestra:** la memoria `tests/fixtures/memorias/s1_precios_empresa.md` (conjunto exacto de
  siete hallazgos a 2026‑10‑01 con sus impactos a ±0,01, Δ por unidad por lista, reevaluación a 2026‑10‑06
  que suma el R12 del agua sin tocar las filas guardadas); `tests/integration/test_lista_empresa.py`
  (`lista_vigente` no ve empresa ni referencia, propio prevalece y heredado se marca, dos empresas aisladas,
  coma decimal con fila, moneda ajena, insumo sin precio en la moneda de la lista);
  `tests/unit/test_reglas_precios.py` (fronteras 0,8000/0,7999/1,3000/1,3001 a la misma tasa, 30 días pasa y
  31 advierte, día sin tasa); la prueba de migración y de deriva RNF‑20 de B sin cambios.
- **Impacto:** `lista_vigente` excluye dos alcances más; el lector acepta columnas opcionales (un archivo con
  solo las cuatro columnas obligatorias se lee igual); `PrecioLeido` gana campos con valor por defecto; una
  tabla aditiva con su revisión. R11 y R12 quedan fuera de `REGLAS`. El bloque de regresión no se mueve.
- **Costo si es erróneo:** si R11/R12 debieran estar en `REGLAS`, se reanclan las huellas de RNF‑04 con
  ruling; si el rango o el plazo son malos, son parámetros por lista (`lista_empresa`) y constantes de
  `core/catalog/empresa.py`; si la lista de referencia debiera resolverse como vigente, se retira un alcance
  de `ALCANCES_FUERA_DE_VIGENTE`. Una tabla que deba cambiar es una revisión más de Alembic.

## SL‑E3: reajuste por escalatoria y por comprobación directa, estudio guardado y RNF‑14

**Fecha:** 2026‑10‑12 · **Rama:** `inc/060-s1-4-nucleo` (sale de `origin/main` con S1‑3 fusionado) ·
**Plan:** tareas 11 (SL‑E3a) y 12 (SL‑E3b) de la sección C · **Spec:** S1 §8 y §11.

- **Regla que lo motiva:** H‑D3, RF‑70 y RF‑71, y los artículos 133 y 134 de la LCP **según la transcripción**
  (todo «a cotejar con la Gaceta»). Un contrato de más de un año reajusta sus precios, y quien lo estudia
  necesita ver a la vez la fórmula escalatoria y la comprobación directa contra una versión revalorada, con su
  diferencia, en las dos monedas, y poder volver a abrir el estudio años después y obtener exactamente lo mismo.
- **Por qué es genérico:** la ley aplica a obras y servicios de cualquier dominio. Nada del módulo nombra una
  especialidad: la estructura sale de los tres montos del `ResultadoAPU` (materiales, equipos, mano de obra),
  las series de índices son texto con su unidad, la partida es un código y el contrato es una versión
  cualquiera. Ningún contrato de `core/contracts/` cambia: `ResultadoAPU` solo se lee.
- **Diseño:**
  1. **Funciones puras** en `core/budget/reajuste.py`: `coeficiente`, `coeficiente_de_partida`,
     `reajuste_escalatorio` (`Vpm = Vo·(Km−1)·(1−R)`, INDICIO S1‑R8), `reajuste_por_comprobacion` (R no se
     aplica salvo declaración, S1‑R14), `comparar_reajustes` y `calcular_estudio`. Toda división va dentro de
     `localcontext(prec=28, ROUND_HALF_EVEN)`; nada se redondea antes de presentar. La diferencia en la otra
     moneda es la diferencia en la moneda del proyecto convertida **una sola vez**, no la resta de dos
     importes ya convertidos (−1 381,66/850 = −1,63 USD, mientras que 12,12 − 13,74 = −1,62).
  2. **Cantidad reajustable** = `min(q_m, máx(0, Q − Σ q anteriores))`: lo ejecutado por encima de lo
     presupuestado se guarda, se reajusta solo hasta Q y lleva aviso (no se rechaza; R13 lo marca en 0.7.0).
     El reajuste es solo sobre lo ejecutado de cada período (art. 134), nunca sobre el saldo.
  3. **Primer año** (contrato > 12 meses): un período que cierra antes del aniversario de la fecha de
     referencia vale cero y lo dice; uno que lo cruza se rechaza (3b); la excepción declarada con
     justificación lo reajusta y queda marcada (3e). Un contrato de 12 meses o menos no tiene primer año fijo.
  4. **Monto reconocido** (S1‑R20): con `ambos`, el del `mecanismo_pagadero`; si no se declara, la
     escalatoria. Si el mecanismo reconocido no está disponible, el período no tiene monto reconocido y se
     declara; no se toma el otro. **Parcial al corte** (S1‑R21): un estudio cuyo último mes no ha cerrado se
     guarda así y se reemplaza una sola vez por uno cerrado que lo cita en `reemplaza_a`
     (`UniqueConstraint`), sin borrarlo.
  5. **Tablas aditivas** `clausula_reajuste`, `componente_clausula`, `estudio_reajuste`, `periodo_reajuste`
     y `ejecutado_periodo` (`core/models/moneda.py`; revisión `caso_0004_s1_reajuste` escrita a mano,
     `down_revision` = salida de `revision_head(Destino.CASO)` = `caso_0003_s1_lista_empresa`,
     `create_table` solo de lo que falta como las revisiones 0002 y 0003, `downgrade()` real). Un estudio
     guardado solo agrega filas: ni la versión del contrato ni ninguna tabla existente cambia.
  6. **RNF‑14.** El período guarda la importación de cada índice que usó, la tasa de su cierre y la versión de
     comprobación. `cargar_estudio` recalcula con **lo citado** (no con lo vigente) y exige igualdad exacta de
     escalatoria, comprobación y reconocido con lo guardado; una revisión posterior de un índice no lo mueve.
- **Prueba que lo demuestra:** las memorias `tests/fixtures/memorias/s1_reajuste.md` (Km 1,17; escalatoria
  15 300; comprobación 16 000; diferencia −700; 18,00 y 18,82 USD) y `s1_reajuste_por_partida.md` (K_A 1,175,
  K_B 1,185; 10 298,34 / 11 680,00 / −1 381,66 Bs; 12,12 / 13,74 / −1,63 USD; testigo declarada 9 785,88),
  cuyas cifras se escribieron a mano antes del código y no se recalculan con él;
  `tests/unit/test_reajuste.py` (fronteras de 1 000 y 1 000,001, primer año, aniversario, 12 meses, 3b, 3e,
  pesos que no suman 1, índice faltante, provisional, USD con índice en Bs, parcial al corte);
  `tests/integration/test_estudio_reajuste.py` (recarga idéntica y citada, RNF‑14 con una revisión posterior,
  parcial reemplazado una sola vez, sin fuente no se guarda); las pruebas de migración y de deriva RNF‑20 de
  B sin cambios.
- **Impacto:** módulo nuevo y cinco tablas aditivas con su revisión; no toca el motor, ni las versiones, ni
  los contratos, ni `REGLAS`. El bloque de regresión no se mueve. Quien abre una base anterior la migra con
  respaldo y la nueva revisión solo crea tablas vacías.
- **Costo si es erróneo:** si la Gaceta o un experto cambian la fórmula, se cambia una función pura y su
  memoria; si cambia el primer año, es un parámetro de la cláusula; si el reconocido debe ser otro, es la
  elección de `elegido` en `calcular_estudio`. Una tabla que deba cambiar es una revisión más de Alembic.
  Los estudios ya guardados no se reescriben: se rehacen guardando otro.
