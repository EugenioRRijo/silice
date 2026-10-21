# Expediente de core VB-1: `texto_decimal` cuantiza a 28 decimales (el paquete firmado vuelve a ser revisable)

**Fecha:** 2026-10-21. **Rama:** `inc/ruta-s2-mig-adm-empresa`. **Hallazgo:** `docs/bitacora/2026-10-19-VB1-paquete-firmado-no-revisable.md`.
**Decisión de Eugenio (2026-10-21):** aceptó la recomendación del orquestador, opción (a). **Aval del tutor:** paso formal
**pendiente**; no bloquea el trabajo local (decisión de Eugenio), sí la fusión a `main` según el ruling de VB-1.

## Regla que lo motiva
RF-85 / SL-E8: lo que Entregar firma debe poder leerlo Revisar. El exportador (`core/budget/canonico.py::texto_decimal`)
escribía `format(valor, "f")`; el lector estricto (`PATRON_CIFRA` en `canonico.py:72` y `seguridad/json_estricto.py:22`)
admite como máximo 20 enteros y 28 decimales.

## Problema y causa raíz
`Decimal(1)/Decimal(12)` en el contexto por omisión (prec 28) es `0.08333333333333333333333333333`: 28 cifras
significativas, pero **29 decimales** porque empieza en `0.0…`. Todo cociente menor que 1 con cifras no terminales (equipos
= tarifa / rendimiento 12, por ejemplo) produce 29 o más decimales; el exportador los escribía, el lector los rechazaba
(«renglón 0.equipos: cifra fuera del patrón estricto», 422). Los valores mayores o iguales que 1 con 28 cifras significativas
no llegan a 29 decimales, por eso MIN-001 y la línea base nunca lo vieron.

## Es genérico
Afecta a cualquier presupuesto de cualquier especialidad con un costo o rendimiento fraccionario. No hay una sola línea
específica de una especialidad.

## Opciones
- **(a) Cuantizar a 28 decimales al exportar (elegida).** Ventajas: la guardia de seguridad (`json_estricto`, `PATRON_CIFRA`)
  no se toca; lo que ya cabía en el patrón sale **byte a byte igual**, así que ningún paquete, huella ni firma existente
  cambia; el cambio es una función. Riesgos: se firma un texto que difiere del `Decimal` del motor en menos de 5E-29 (ver
  más abajo); una versión sellada antes con 29 decimales cambia de huella al recalcular (ver «Compatibilidad»).
- **(b) Ensanchar el patrón a 29 o más decimales en los dos sitios.** Ventaja: no pierde dígitos. Riesgos: cambia una guardia
  de seguridad (y tendría que cambiarse en `core` y en `seguridad`, que `core` no puede importar), el siguiente cociente
  (`1/12` con prec mayor, un `Decimal` con exponente distinto) vuelve a romper en 30 decimales, y los lectores ya
  desplegados (otras instalaciones del revisor) seguirían rechazando lo nuevo. No resuelve la causa: el motor produce más
  dígitos de los que el formato promete.

## Por qué (a)
No cambia la guardia de seguridad; lo que ya se firmó sigue siendo válido (los paquetes ya emitidos se verifican con los
bytes que traen, y el verificador no recalcula `texto_decimal`); y el formato queda con la promesa que ya tenía («hasta 28
decimales»). La pérdida es la de un redondeo en el decimal 28.

## Modo de redondeo
`ROUND_HALF_EVEN`: es el que el núcleo fija para montos (`valor_ganado`, `reajuste`, `recuperacion`, `comparacion`:
`localcontext(prec=28, rounding=ROUND_HALF_EVEN)`; NORMAS §2). El exportador no introduce un modo nuevo. (`curva.py` y
`excel.py` usan HALF_UP, pero para presentar a 2 decimales, no para serializar.) La cuantización se hace en
`localcontext(prec=80)` porque 20 enteros + 28 decimales son 48 dígitos y `quantize` falla con `InvalidOperation` si el
contexto es de 28.

## Qué NO cambia (demostración)
1. **Lo que ya cabía sale idéntico.** `texto_decimal` solo actúa si `as_tuple().exponent < -28`; en otro caso devuelve
   `format(valor, "f")` exacto. Prueba: `test_todo_lo_que_ya_cabia_sale_identico_a_format_f` (escalas 0 a 28, signos, 20
   enteros) y `test_el_limite_del_patron_no_cambia` (`9`×20 + `.` + `9`×28 y su negativo no cambian).
2. **Huella y firma de paquetes y fixtures existentes.** Un paquete válido solo contiene cifras que pasaron el patrón (≤ 28
   decimales), es decir, cifras que `texto_decimal` no toca. `HUELLA_EJEMPLO_V1` y los bytes de `ejemplo_v1`
   (`tests/unit/test_canonico.py`, `tests/integration/test_canonico.py`) siguen verdes sin tocarse; las pruebas de entrega,
   cadena, recibir y verificar también (conteos en el informe). Un paquete con cifras de 29 decimales **nunca fue
   importable**, así que no hay paquete revisable que cambie.
3. **Montos a 2 decimales.** El error máximo de la cuantización es 0,5E-28 (`test_la_diferencia_maxima_es_media_unidad…`).
   Un monto presentado a 2 decimales solo podría cambiar si el valor estuviera a menos de 5E-29 de un empate de centésimas.
   Cota honesta: no es imposible para un `Decimal` arbitrario de 28 cifras, pero sí para cualquier cociente `n/d` con `d ≤ 400`,
   que dista al menos `1/(200·d)` de un empate; el barrido determinista de `test_ningun_monto_a_dos_decimales_cambia…` (más de
   266 000 cocientes) no encuentra ninguno. Las líneas base (cinco APU ±0,01, 7 de 7, R4 de 3/4 pulg, TI-001 total/PU/PE,
   RNF-04, cuatro hojas de `exportar_excel`) no pasan por este camino con más de 28 decimales.
4. **Contrato estable.** `core/contracts/` no se toca.

## Impacto en la firma
Se firma el texto **cuantizado**: `presupuesto.json` (y su huella en el manifiesto y en el eslabón) lleva la cifra de 28
decimales; el verificador recalcula la huella del archivo recibido, no la del `Decimal`, y obtiene el mismo texto. Entregar
→ Revisar de un equipo `1/12` verifica la firma y `leer_documento` devuelve `0.0833333333333333333333333333`
(`tests/integration/test_vb1_entregar_revisar.py`).

## Compatibilidad: versiones selladas antes (cambio adicional en `core/budget/cadena.py`)
Hallazgo propio: la huella de contenido de cada eslabón se calcula con `documento()`, que usa `texto_decimal`. Una base que ya
selló una versión con una cifra de 29 decimales (la huella se calculó sobre el texto largo) vería, tras la corrección, un
«Cadena rota … su contenido no coincide con su huella»: una falsa alarma de manipulación. Para que esas bases abran
(NORMAS §9, migraciones compatibles) `verificar_cadena` acepta, **solo si la huella actual no coincide**, la huella calculada
en `canonico.formato_legado()` (serialización sin cuantizar). Una alteración real no coincide con ninguna de las dos
formas y se sigue detectando (`test_una_version_sellada_antes…`, con alteración posterior). `formato_legado` es un
contexto de solo transición, exportado pero no usado para escribir. Límite declarado: Entregar de una versión sellada antes
con 29 decimales produciría un `presupuesto.json` cuantizado cuya huella no es la sellada (`aplicacion/entrega.py` usa
`canonico.estructura`); se resuelve creando una versión nueva (que sella ya cuantizada) o con un cambio en `aplicacion/`,
fuera de este alcance; pendiente de decisión.

## Prueba que lo demuestra (rojo visto antes de implementar)
`tests/unit/test_canonico_cuantizacion.py` (cifras `1/12`, `1/15`, `1/3`, `2/3`, `1/7`, `1E-27`, `±1E-29`, empates a
`…5E-29` pares e impares, cero y cero negativo, 20 enteros + 29 decimales, negativos; oráculo con `fractions.Fraction`, no con
`Decimal.quantize`; barrido de propiedad determinista porque `hypothesis` no es dependencia) y
`tests/integration/test_vb1_entregar_revisar.py` (Entregar→Revisar de punta a punta, cadena, versión sellada antes).
Commit del rojo: ver el informe; 15 pruebas fallaban.

## Costo si es erróneo
Una cifra firmada que difiere en < 1E-28 del valor del motor: invisible a 2 decimales salvo el caso patológico del punto 3.
Si hubiera que revertir: se revierte el commit; los paquetes emitidos entre tanto (cuantizados) siguen siendo válidos para
cualquier lector. Una cifra con más de 20 enteros tras redondear (por ejemplo `99999999999999999999.99999999999999999999999999999`
→ `1E+20`) sigue siendo rechazada por el lector: falla fuerte, no en silencio; no es alcanzable con montos reales.

## Fuera de alcance, reportado
- Otros caminos `format(…, "f")` hacia JSON: `core/budget/decision.py`, `core/budget/valor_ganado.py`, `core/verification/valuaciones.py`
  (a revisar si alimentan JSON leído con `PATRON_CIFRA`); `api/rutas/{auditorias,auditorias_libro,control,entregas}.py` y
  `adapters/*` son de otros encargos y no se tocaron. Ver el informe.
- Aval del tutor: pendiente.
