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

## Suite completa del cierre (2026-10-31, sobre eddfab91)

- Pytest: una regresión de la Tarea 8: `METADATA_VIAL` no estaba en `METADATAS_CASO`, y `test_migraciones` (deriva cero
  contra `create_all`, autogeneración sin cambios y «ninguna metadata suelta») quedaba en rojo. Corregida en 58c634ac.
- No son de la rama (las mismas del cierre de la fase A): `test_experimento_congelado_vigente`,
  `test_huellas_rnf04::test_huella_del_contenido_del_libro` y `test_r11_los_hallazgos_son_los_de_la_memoria[TI-001]`
  (R12 por el reloj).
- Vitest: 3253 de 3253. Lint (eslint + tsc): limpio. `ruff check .`: limpio.

## Árbitro de cierre de la fase B (ronda 1, cabeza 49759e24): devuelta

- MAYOR: VR1, VR2, VR4, VR5 y VR7 casan por el `origen_id` «tramo:…», que ninguna partida del producto llevaba. En la
  Hoja solo funcionaban VR3 y VR6, y la prueba de la Hoja fabricaba el presupuesto con `derivar_tramos`. Se arregla
  con un camino de producto (no solo anotarlo): la **Tarea 8b** «Llevar los tramos al presupuesto», añadida al plan,
  con la fila 63 en las preguntas. La Tarea 22 queda obligada a recorrer ese camino.
- MENOR 2: los topes de tramos, capas y líneas no se aplicaban al importar el CSV. Entra en la Tarea 8b (regla 5).
- MENOR 3: las reglas viales quedaban congeladas al abrir la versión. La Tarea 8b las rearma al llevar, y el resto
  queda anotado en la fila 63.
- Verificado por el árbitro: unas 984 pruebas de la fase en verde; arquitectura, migración y `ruff` limpios; `core/`
  intacto; experimento congelado intacto; `docs/api.json` idéntico; front 271 de 271 y lint limpio.

## Tarea 8b: llevar los tramos al presupuesto

| Tarea | Commits | Árbitro |
|---|---|---|
| 8b Llevar los tramos al presupuesto | 4e2fa742 (plan), 6fc6c9bd, 29b3c67a; r2 8e6eea6d, 54f22f49 | devuelta r1 (el botón llevaba los tramos de la versión del borrador sin decirlo), aprobada r2 |

- r2: el cuerpo trae `{proyecto, version}`. Si el borrador es de otra versión, 409 sin llevar nada; el aviso nombra la
  versión; módulo `aplicacion/hoja_vial.py`; `elaboracion.version_del_borrador_de_la_obra` y
  `hoja_edicion.cambiar_borrador` públicas; `VersionInexistente` → 409. Filas 63 a 72.
- Menor del árbitro r2 hecho: la fila 72 ya no dice que una versión aprobada se lleva a un borrador de otra.
- Menor aceptado sin cambio: `test_un_borrador_abierto_de_otra_version_da_409_y_no_cambia` no compara `tocado`, que
  renueva la lectura de la vista. Compara id, versión, `rev`, cambios y filas, y la unitaria compara el borrador entero.

## Árbitro de cierre de la fase B (ronda 2, cabeza 7d741861): APROBADA

- El MAYOR de la r1 quedó resuelto con la Tarea 8b: VR1 y VR4 se disparan desde la interfaz, y VR3 y VR6 ya se
  disparaban. Los menores 2 y 3 también quedaron resueltos.
- MENOR nuevo, hecho: las filas 63 y 70 declaran que VR2, VR5 y VR7 no se alcanzan desde la interfaz, y cómo cambiarlo.
  El reporte de la Tarea 22 y la tesis no deben decir «VR1 a VR7 en el producto».
- Verificado por el árbitro: pruebas de la fase, migraciones y arquitectura en verde; `ruff` limpio; front 418 de 418 y
  lint limpio; `core/` intacto; `docs/api.json` idéntico.

**Fase B cerrada.**
