# Plan vial y de agregados, fase B (especialidad vial)

Tareas 7 a 11 en `inc/vial-agregados`, cada una con su árbitro. Decisiones del implementador y del orquestador:
filas 33 a 62 de `2026-10-30-preguntas-para-eugenio.md`.

| Tarea | Commits | Árbitro |
|---|---|---|
| 7 Tramos y cantidades (`adapters/vial/`) | 1da39d1c, 304ab337; r2 cb47357b, 40406ff4 | devuelta r1 (cifras laxas contra la coma decimal y el punto de miles; marcas sin `_` que R4 contaba), aprobada r2 |
| 8 Tramos por versión, API y pantalla | 31a90fc0, 3c50128c; r2 3ce5f7df, ca2e81a9 | devuelta r1 (versión nueva sin tramos), aprobada r2 con herencia al leer y solo la versión más reciente editable |
| 9 Reglas VR1 a VR7 | 5c631c66, 0e3d51d1 | aprobada r1 |
| 10 Conciliación CV1 a CV3 y reglas viales en la Hoja | b2514aea (plan), 133c50f7, 23120bcd | aprobada r1 |
| 11 Mutaciones viales y matriz de detección | 73f4fa15, 2f707cfb; r2 7c84b38a, 1dbc788a | devuelta r1 (EV4 «unidad» no ensayaba VR7), aprobada r2 |

## Menores del cierre

- Hechos: el mensaje de «1.234.567» ya no pregunta «¿miles o decimales?» y ofrece las dos formas del README de la
  muestra; prueba que ata `adapters/vial/tabular.BLANCOS` a `aplicacion/cifras.BLANCOS`; prueba que ata la descripción
  publicada del insumo propio a la que reconoce CV3; V-13 dice «a cotejar»; la fila 48 dice que una versión aprobada
  que ya no es la más reciente queda fija; la Tarea 21 cablea `calculos_usados` de CV3 (añadido al plan).
- Anotados sin cambio:
  - El asunto de cb47357b dice «35 de cifras»: el reparto real de sus 38 fallos fue 33 de cifras (13 mal escritas,
    1 ambigua y 19 de comparación), 1 de R4 y 4 de derivación. No se corrige: está prohibido reescribir commits.
  - Las pruebas de `formula_asfalto_de_receta` y `reglas_viales` (Tarea 9) entraron con el feat, sin rojo propio.
  - La prueba de rendimiento de `test_vial_derivacion.py` mide reloj: holgura amplia; vigilarla en la CI.
  - La herencia de tramos (`aplicacion/vial._vigente`) se ordena por id de presupuesto y hace una consulta por
    versión anterior sin tramos: si la Hoja renumerara versiones o molestara el coste, una sola consulta con
    `version_id IN (...)`.
  - VR6 trata todos los tramos de la obra como una sola vía (fila 53): una obra con dos vías daría solapes falsos.
  - La matriz de detección (Tarea 11) cubre 17 de 17 mutantes con VR1 a VR7 más CV2; con VR solas, que es lo que
    muestra la Hoja (fila 58), se escapan cuatro. Queda declarado en la prueba y en la fila 62.
