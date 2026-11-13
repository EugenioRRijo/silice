# Editar el desperdicio en la Hoja: simulación y decisión (2026-11-13)

Lo que faltaba del punto 1 del diseño del presupuesto vial
([§4, opción B; §12; §13](../especificaciones/2026-11-03-presupuesto-vial-real-design.md)): la Hoja ya **muestra**
«0,50 + 4 %» en cada material con traza (commits `6a738e7c`..`5bac4b40`), pero no deja **editar** la neta y el porcentaje.
Componer sí los edita y guarda la traza en la misma transacción que la composición del catálogo.

## 1. La pregunta

La traza vive **por código de partida** en la base del caso (`aplicacion/tablas_desperdicio.py`: un guardado por partida,
solo inserción, manda el último) y se muestra en una línea solo si su descripción, unidad y cantidad son las de la traza.
La Hoja, en cambio, edita el APU **de una versión**: el borrador es una copia en memoria que se puede descartar y que, al
guardarse, es una versión nueva con su propia instantánea de composiciones (el catálogo no cambia;
`completar_composiciones` solo llena las partidas sin APU). ¿Dónde y cuándo se escribe la traza de lo que se edita en la
Hoja?

## 2. Simulación

Caso **ficticio**: la partida `VIA-01` tiene en el catálogo un ligante de 0,50 l con 4 % (0,52), guardado por Componer;
la versión 001 lo copió (0,52). En la Hoja, sobre la 001, se escribe 0,60 + 5 % (0,60 × 1,05 = 0,63, a mano). Se corrió un
guion con las funciones reales de `aplicacion/desperdicio.py` (`guardar_trazas`, `trazas_vigentes`, `con_desperdicio` para
la precarga de Componer y `desperdicios_por_fila` para la Hoja) sobre una base del caso en memoria. El guion y su salida
quedaron en el directorio temporal de la sesión; esta es la salida:

| Opción | Componer (catálogo, 0,52) | Hoja, versión 001 (0,52) | Hoja, versión 002 (0,63) | Al descartar el borrador |
|---|---|---|---|---|
| Antes de editar | 0,50 + 4 % | 0,50 + 4 % | — | — |
| **(a)** traza en el borrador, escrita al guardar la versión, **sin unión** | **pierde el desglose** | **pierde el desglose** | 0,60 + 5 % | nada escrito |
| **(a)** ídem, **unida a las vigentes** | 0,50 + 4 % | 0,50 + 4 % | 0,60 + 5 % | nada escrito |
| (a) con unión y después Componer vuelve a guardar `VIA-01` | 0,50 + 4 % | 0,50 + 4 % | sin desglose (se ve 0,63) | — |
| **(b)** traza escrita en cada edición | **pierde el desglose** (aunque el borrador se descarte) | **pierde el desglose** | 0,60 + 5 % de una versión que nunca existió | **la traza queda** |
| **(c)** «Editar en Componer» | cambia el **catálogo** a 0,63 | sigue con 0,52 (su instantánea) y **pierde el desglose** | — (la versión no cambia) | — |

## 3. Razonamiento

- **(b) se descarta.** Escribe en la base desde una ruta que hoy solo lee (`hoja_edicion`: «aquí no se escribe nada en la
  base») y sin fuente ni responsable; una edición que después se descarta deja una traza que desplaza la vigente, y cada
  pausa de 400 ms del editor sería una fila más en una tabla de solo inserción.
- **(c) se descarta.** No hace lo que se pide: Componer cambia la composición del **catálogo**, no el APU de la versión que
  se está presupuestando (la versión conserva su instantánea). Además deja en la Hoja la cantidad editable como producto,
  que es justo el riesgo de §12, y exige el permiso de editar el catálogo.
- **(a) es la correcta y la más simple, con unión.** Es la misma forma que Componer (la neta y el porcentaje se escriben, el
  servidor calcula la cantidad y la traza se escribe en la transacción de lo que se guarda) y la misma que ya usan las
  importaciones del borrador (`BorradorVivo.importaciones`, escritas con la versión). Descartar no deja nada; guardar
  escribe la traza a nombre de quien guarda, en la misma transacción que la versión (todo o nada). La **unión** es
  necesaria porque la traza vive por partida: sin ella, la edición de una versión dejaría sin desglose al catálogo y a
  las demás versiones.
- **Quién revisa** no edita (403, como cualquier edición del APU) y sigue viendo el desglose de la base y, en el borrador
  que abre, el mismo que verá quien guarde.
- **Desincronización.** La regla de siempre la impide: la traza del borrador solo se muestra y se guarda si la línea
  sigue siendo la que resultó (si luego se escribe otra cantidad o se cambia el insumo, deja de casar y no se guarda).
- **Archivos congelados.** (a) no toca `aplicacion/hoja.py` ni `aplicacion/composicion.py`: el cálculo va en
  `aplicacion/hoja_desperdicio.py` (nuevo), sobre `composicion_con_cantidades` sin cambiarla.

**Segunda opinión** (agy, `gemini-4-argon-medium`, encargo corto con este caso): «De acuerdo. La opción (a) con unión es la
única que respeta la atomicidad del borrador (frente a b, que contamina la base al descartar) y el aislamiento entre
versión y catálogo (frente a c, que muta el catálogo al editar un presupuesto)». Señaló tres riesgos, que se tratan así:

1. *Colisión de la misma cantidad con otro desglose* (0,40 + 30 % y 0,50 + 4 % dan los dos 0,52): en la unión manda el
   más nuevo, el del borrador (`hoja_desperdicio.unir` deja la vigente de la misma descripción, unidad y cantidad). Los dos
   desgloses son aritméticamente ciertos para 0,52; la versión 001 pasaría a mostrar el nuevo. Es un caso raro y se acepta.
2. *Asimetría con Componer*: si Componer vuelve a guardar la partida, su guardado manda y la versión de la Hoja deja de
   mostrar el desglose (se ve la cantidad, que sigue siendo correcta; nunca un desglose falso). Componer no se cambia: su
   «manda el último» es lo que hace que quitar un desperdicio en Componer lo quite de verdad. Es el **límite conocido**; si
   molesta, la solución es una traza por versión (una columna aditiva en `apu_desperdicio_guardado`, o la opción A del
   diseño si el tutor quiere el concepto en el núcleo).
3. *Acumulación*: la unión no poda, pero no crece por repetición (una traza por descripción, unidad y cantidad) y una traza
   que no casa con ninguna línea no se muestra.

## 4. Decisión

**Opción (a) con unión**, construida en `feature/hoja-desperdicio` el 2026-11-13. Reversible: todo vive en
`aplicacion/hoja_desperdicio.py`, `hoja_edicion.editar_apu` (parámetro `desperdicios`), `BorradorVivo.desperdicios` y una
llamada en `hoja_guardado`.

- E6 (`PUT /v1/hoja/borradores/{id}/apu/{partida}`) acepta `desperdicios`, un porcentaje por material («» sin
  desperdicio). Con uno no vacío ni cero, la cantidad escrita es la neta y el servidor guarda `neta × (1 + porcentaje /
  100)`, exacta; un porcentaje mal escrito es 422 «materiales, fila N: el desperdicio «…» …», que la Hoja liga a su campo.
- La vista del APU trae, por fila con traza, `neta` y `porcentaje` además del texto: siembran los campos.
- La pestaña APU edita, en Materiales, la cantidad (neta, si hay porcentaje) y «Desperdicio (%)», y muestra «Cantidad con
  desperdicio», la que calculó el servidor.

Es una decisión del orquestador con Eugenio ausente (como las de F5): queda **provisional**, por ratificar, y anotada en
§13 del diseño.
