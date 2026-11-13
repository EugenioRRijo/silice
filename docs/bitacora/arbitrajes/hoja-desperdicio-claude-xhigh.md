# Árbitro Claude xhigh: el desperdicio en la Hoja, el re-congelado y el lector (2026-11-13, ronda 1)

**Juzgado:** `git diff b19f8e27..394c1217` (`feature/hoja-desperdicio`). **Veredicto:** APROBADO CON CAMBIOS: 0
BLOQUEANTE, 0 MAYOR, 9 MENOR y 8 NOTA. **Aprobado si:** se aclara el hallazgo 1 (sin cifra real y con redacción neutra)
y se ponen al día CHANGELOG y ESTADO (hallazgo 2). Correcciones en `fix/arbitro-1113`, con prueba en rojo primero donde
cambia el comportamiento.

**Lo que corrió el árbitro:** 315 + 323 + 120 + 3 pruebas de Python de los módulos tocados y 98 de vitest, todas verdes;
`docs/api.json` regenerado idéntico; metas de datos 4/4; guardia del núcleo OK; `congelado.calcular()` igual a
`congelado.json`, la huella vieja recalculada en `d4e4b35d` igual a la del acta, y el árbol sintáctico de `hoja.py` y
`composicion.py` con las cadenas vaciadas igual al congelado: ninguna regla cambió. Cada commit rojo falla.

| # | Hallazgo | Respuesta |
|---|---|---|
| 1 | Una cifra del pie atribuida a un libro real (NORMAS §1) | Corregido: «p \| …» en el lector, el perfil, el manual y la prueba, sin atribución (`b73e8e00`) |
| 2 | CHANGELOG y ESTADO decían lo contrario de la rama | Corregido: CHANGELOG (Agregado y Corregido) y ESTADO §2, §3 y §5.4 |
| 3 | La traza de la Hoja con una descripción con espacios en los bordes nunca casaba | Corregido: el emparejado recorta la traza como la fila (`424ed165` rojo, `ec6ee12a` verde) |
| 4 | El porcentaje se recortaba con `strip()` y no con los blancos de `aplicacion/cifras` | Corregido: `strip(BLANCOS)` (mismos commits) |
| 5 | «Cantidad con desperdicio» se escondía con «0,5» frente a «0,50» o «1234,5» frente a «1.234,5» | Corregido: compara como cifras con `leerCifra`, solo texto (`e20b19aa` rojo, `f6bb76d0` verde) |
| 6 | Faltaban en la suite la atomicidad, la primera versión, el lado con vacías y texto, el perfil sin la clave y los porcentajes de frontera | Agregadas (`a5a7ff9a`); pasan desde el principio: el comportamiento ya era correcto |
| 7 | Historia de TDD: fecha de un verde anterior a su rojo; un tramo rojo tras las tildes; dos pruebas corregidas en el verde | Declarado en `docs/bitacora/2026-11-13-desperdicio-en-la-hoja.md`; no se reescribe la historia |
| 8 | La bitácora decía que la traza se escribe «a nombre de quien guarda» | Corregido: la traza no lleva responsable; quien guarda queda en la versión |
| 9 | `desperdicios_por_fila` solo lo usaban las pruebas | Quitado; las pruebas usan `trazas_de_las_filas` (`ec6ee12a`) |
| N | `FORMA_APU` no mencionaba el desperdicio | Corregido (`a7d8746a` rojo y su verde) |
| N | Tildes que quedan en `aplicacion/hoja.py` (422 de guardar) | Para el próximo re-congelado (ESTADO §5.5) |
| N | Materiales con dos columnas más a 1366 px y en el panel lateral | Falta la pasada en el navegador (ESTADO §4) |
| N | Dos líneas iguales, quitar el desglose con el mismo total, lectura sin cerrojo, `_a_la_izquierda` sin porcentaje, tildes en asuntos de commit | Aceptadas como están: documentadas, inocuas por el emparejado o con el mismo riesgo que ya tenía «derecha» |
