# Árbitro Claude xhigh: el desperdicio en la Hoja, el re-congelado y el lector (2026-11-13, ronda 1)

**Juzgado:** `git diff b19f8e27..c012bfa8` (`feature/hoja-desperdicio`). **Veredicto:** APROBADO CON CAMBIOS: 0
BLOQUEANTE, 0 MAYOR, 9 MENOR y 8 NOTA. **Aprobado si:** se aclara el hallazgo 1 (sin cifra real y con redacción neutra)
y se ponen al día CHANGELOG y ESTADO (hallazgo 2). Correcciones en `fix/arbitro-1113`, con prueba en rojo primero donde
cambia el comportamiento.

**Lo que corrió el árbitro:** 315 + 323 + 120 + 3 pruebas de Python de los módulos tocados y 98 de vitest, todas verdes;
`docs/api.json` regenerado idéntico; metas de datos 4/4; guardia del núcleo OK; `congelado.calcular()` igual a
`congelado.json`, la huella vieja recalculada en `d4e4b35d` igual a la del acta, y el árbol sintáctico de `hoja.py` y
`composicion.py` con las cadenas vaciadas igual al congelado: ninguna regla cambió. Cada commit rojo falla.

| # | Hallazgo | Respuesta |
|---|---|---|
| 1 | Una cifra del pie atribuida a un libro real (NORMAS §1) | Corregido: «p \| …» en el lector, el perfil, el manual y la prueba, sin atribución (`82289832`) |
| 2 | CHANGELOG y ESTADO decían lo contrario de la rama | Corregido: CHANGELOG (Agregado y Corregido) y ESTADO §2, §3 y §5.4 |
| 3 | La traza de la Hoja con una descripción con espacios en los bordes nunca casaba | Corregido: el emparejado recorta la traza como la fila (`6c6ccc40` rojo, `db88c6e5` verde) |
| 4 | El porcentaje se recortaba con `strip()` y no con los blancos de `aplicacion/cifras` | Corregido: `strip(BLANCOS)` (mismos commits) |
| 5 | «Cantidad con desperdicio» se escondía con «0,5» frente a «0,50» o «1234,5» frente a «1.234,5» | Corregido: compara como cifras con `leerCifra`, solo texto (`1c4ced61` rojo, `5f0e0585` verde) |
| 6 | Faltaban en la suite la atomicidad, la primera versión, el lado con vacías y texto, el perfil sin la clave y los porcentajes de frontera | Agregadas (`8e42c1e9`); pasan desde el principio: el comportamiento ya era correcto |
| 7 | Historia de TDD: fecha de un verde anterior a su rojo; un tramo rojo tras las tildes; dos pruebas corregidas en el verde | Declarado en `docs/bitacora/2026-11-13-desperdicio-en-la-hoja.md`; no se reescribe la historia |
| 8 | La bitácora decía que la traza se escribe «a nombre de quien guarda» | Corregido: la traza no lleva responsable; quien guarda queda en la versión |
| 9 | `desperdicios_por_fila` solo lo usaban las pruebas | Quitado; las pruebas usan `trazas_de_las_filas` (`db88c6e5`) |
| N | `FORMA_APU` no mencionaba el desperdicio | Corregido (`47bd1d73` rojo y su verde) |
| N | Tildes que quedan en `aplicacion/hoja.py` (422 de guardar) | Para el próximo re-congelado (ESTADO §5.5) |
| N | Materiales con dos columnas más a 1366 px y en el panel lateral | Falta la pasada en el navegador (ESTADO §4) |
| N | Dos líneas iguales, quitar el desglose con el mismo total, lectura sin cerrojo, `_a_la_izquierda` sin porcentaje, tildes en asuntos de commit | Aceptadas como están: documentadas, inocuas por el emparejado o con el mismo riesgo que ya tenía «derecha» |

## Ronda 2 (2026-11-13): DEVUELTO

**Juzgado:** `394c1217..4b2371d2` (hashes de antes de la reescritura): correcciones de la ronda 1, la de Gemini Argon,
las tres líneas de la prueba de punta a punta (`docs/bitacora/2026-11-13-e2e-vial.md`, `…-e2e-precios.md`,
`…-e2e-front.md`), el ciclo de importación y la fusión de `componer/cliente.ts`. **Veredicto:** DEVUELTO solo por el
hallazgo 1 (datos); el código, aprobado: 1.369 pruebas de Python y 272 de vitest de lo tocado, cada commit rojo falla,
`core/` y los 50 archivos del auditor sin cambios, `docs/api.json` idéntico a `app.openapi()`, simulaciones recalculadas y
honestas.

| # | Hallazgo | Respuesta |
|---|---|---|
| 1 | BLOQUEANTE (NORMAS §1): una cifra del informe real seguía en la historia, escrita como expresión regular | Historia de `b19f8e27` en adelante reescrita con `filter-branch` (sin subir); grep tolerante a separadores sobre `git log -p`: 0; ramas, árboles temporales, respaldo y reflogs borrados; ningún commit viejo alcanzable |
| 2 | MENOR: la bitácora de la línea de front citaba hashes de antes de su primera reescritura | Todas las bitácoras con los hashes nuevos (`31d56ceb`) |
| 3 | MENOR: el acta y un mensaje repetían una cifra del pie atribuida a un libro real | Quitada de la historia en la misma reescritura y, en la ronda 3, también de esta fila y de un mensaje |
| 4 | MENOR: «Usarla como lista para armar» se mostraba a quien no puede armar | Solo con `editar_hoja`; a los demás se les dice quién la crea (`bba7bca7`) |
| 5 | MENOR: la tabla de insumos nuevos mostraba claves del servidor | «Mano de obra», «m³» (`bba7bca7`) |
| 6 | MENOR: faltaba «Recuperación» en el motivo de Versiones | Agregado (`bba7bca7`) |
| 7 | MENOR: CHANGELOG, ESTADO, ERS y manual de usuario sin las tres líneas | Al día, RF-190 a RF-195 (`40a8f10c`) |
| 8 | MENOR (DRY): `PREFIJO_TRAMO` definido dos veces y el origen escrito como literal | Ver la ronda 3 |
| N | El plan «Mes n» en la pestaña del plan y en Control; VR4 depende del perfil local; AH11 relajado sin declararlo en `2b436af1` | Anotadas en ESTADO §5, punto 6 (ronda 3, M3); la de `2b436af1` queda declarada aquí |

## Ronda 3 (2026-11-13): APROBADO CON CAMBIOS

**Juzgado:** la rama tras la reescritura, hasta la corrección del M8 de la ronda 2. **Veredicto:** 0 BLOQUEANTE, 0
MAYOR, 5 MENOR y 3 NOTA; el código, aprobado. Historia limpia: 228 blobs nuevos y 77 mensajes recorridos con una búsqueda
tolerante a separadores (con control positivo sobre la historia vieja); ninguna referencia alcanza la historia vieja;
`core/` y los archivos del auditor sin cambios; `docs/api.json` igual a la API; 681 pruebas de Python y 87 de vitest de
lo tocado; cada rojo falla por su razón.

| # | Hallazgo | Respuesta |
|---|---|---|
| 1 | La descripción de la corrección repetía la cifra del pie (un mensaje y una fila de esta acta) | Historia reescrita otra vez desde el padre de ese commit (mensaje y fila); 0 apariciones |
| 2 | Un hash de la historia vieja en la fila «N» de la ronda 2 | Puesto al día |
| 3 | La fila «N» decía que tres notas estaban en ESTADO §5, y no estaban | Anotadas en ESTADO §5, punto 6 |
| 4 | El CHANGELOG decía que `PREFIJO_TRAMO` vive en `hoja_partidas` | Dice que se define en `adapters/vial/modelo.py` y `hoja_partidas` lo reexporta |
| 5 | El manual decía que «Usarla como lista para armar» exige una carpeta sin lista, y el código no lo comprueba | Decisión simulada: se permite (la copia, con fecha de hoy, pasa a ser la vigente y así se renuevan los precios); el manual lo dice |
| N | Objetos viejos sueltos en el equipo; el rojo del M8 relajado en su verde (declarado); la cifra de 27 decimales sale de un precio público de MaPreX | Aceptadas; `git gc --prune=now` queda a decisión de Eugenio |
