# MP-1, Tarea 1: moneda de la carpeta y lista para armar (2026-10-25)

Plan: `docs/planes/PLAN_MONTAR_PRESUPUESTO.md`, Tarea 1 (D-MP1: una moneda por carpeta). Código:
`aplicacion/tablas_carpeta.py` (`mp_carpeta`), `aplicacion/listas_para_armar.py`, migración
`caso_0010_mp_carpeta`. Pruebas: `tests/unit/test_listas_para_armar.py`,
`tests/integration/test_migracion_carpeta.py`. El árbitro la aprobó en la ronda 1; sus menores se cerraron
después (fecha fija, tasa con coma, conversión no exacta).

## Decisiones del implementador (para ratificar)

1. **`CarpetaConOtraMoneda(ValueError)`**, excepción nueva que no estaba en el plan: lleva el mensaje de T2
   («La carpeta de trabajo ya trabaja en {m}: para trabajar en {otra}, cree otra carpeta.») y T2 la traduce a 409.
   Declarar la moneda que la carpeta ya tiene no cambia nada (ni quién ni cuándo).
2. **«convertir» cuando la vigente ya está en la moneda de la carpeta:** `SinListaParaArmar` con «La lista vigente
   «{nombre}» ya está en {m}: no hay nada que convertir.»
3. **«maprex» sin moneda declarada ni listas:** la lista queda en la moneda de la referencia (Bs).
4. **Nombres:** al convertir, « en Bs» pasa a « en USD», o se agrega « en USD» («MaPreX julio 2026 en USD al
   25/10/2026», «Base en USD al 25/10/2026»). La lista de una obra se llama «{base} en USD al dd/mm/aaaa». Se
   reutiliza si coinciden obra, nombre, moneda, vigencia de la base, tasa y fecha de la tasa. No se usa
   `lista_base_id`, porque `convertir_lista` lo deja vacío a propósito.
5. **Quién la hizo** queda en el origen de la lista («…, por ana»). La tasa que escribe este módulo va con coma
   decimal y punto de miles («40,00 Bs/USD», `texto_de_cifra`). **Excepción:** el origen de la lista convertida
   de una obra empieza con el texto de `convertir_lista` del núcleo, que escribe «40.00 Bs/USD» con punto. El
   núcleo no se toca.
6. **Fecha:** `moneda_de_la_carpeta(sesion, fecha=None)` mira la lista vigente a `fecha` (hoy, sin fecha);
   `declarar_moneda_de_la_carpeta` usa `ahora.date()` y `lista_para_armar(fecha)` usa la vigente a esa fecha.
   Las pruebas pasan fechas fijas.
7. **Obra inexistente** en `lista_para_el_proyecto`: `ValueError` con «No hay ninguna obra «X» en esta carpeta de
   trabajo.» Es `ValueError` y no `SinListaParaArmar`, para que T9 los distinga.

**Conversión:** se usa la del núcleo, que trabaja con 28 dígitos significativos y ROUND_HALF_EVEN y no redondea a
centésimas. Por ejemplo, 100 Bs a 36,53 Bs/USD dan 2,737476047084588009854913770 USD.
