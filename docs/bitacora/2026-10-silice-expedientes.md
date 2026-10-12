# Expedientes del núcleo de Sílice 0.6.0 (SL‑E1, SL‑E2, SL‑E3)

**Contenido de este archivo:** SL‑E1 (esta rama). SL‑E2 y SL‑E3 lo continúan en sus propias ramas
(`inc/060-s1-3-nucleo`, `inc/060-s1-4-nucleo`).

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
