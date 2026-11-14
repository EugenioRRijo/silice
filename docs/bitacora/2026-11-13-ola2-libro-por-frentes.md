# Ola 2, línea 3: el libro por frentes (2026-11-13)

Rama `feature/libro-por-frentes` (desde `e2dfe116`), árbol `.worktrees/s2m`. Encargo: los cuatro límites del lector que
dejó la prueba local del libro vial real ([bitácora](2026-11-13-libro-vial-real-local.md) §3) más elegir la hoja del
presupuesto aparte del perfil, y dos funciones nuevas: **llevar a la Hoja el libro auditado** y **agrupar el
presupuesto por frente**. Cada decisión se simuló con casos FICTICIOS (los del libro de
`tests/fixtures/libro_apu_por_hoja.py`, guiones en el scratchpad de la línea) y se eligió con el resultado a la vista.
Requisitos: RF-205 a RF-212 ([ERS](../ERS.md), enmienda del 2026-11-13, ola 2, línea 3). Manual: §12.5 y §12.6.
**`core/` no cambia** (`git diff e2dfe116 --stat -- core/` vacío) y ningún archivo congelado del experimento se tocó.
**Ningún dato del libro real** está en este repositorio: lo que dio la prueba local con él va solo en el informe de la
línea, fuera del repositorio (NORMAS §1).

Todas las decisiones son **provisionales, por ratificar** por Eugenio. Cómo revertir cada una: revertir sus commits
(tabla «Commits»), en orden inverso.

## D1. Varias hojas de presupuesto en un perfil (RF-205)

**Qué se decidió.** El perfil declara `presupuesto.hojas` (una por frente) o `presupuesto.hoja` (una), nunca las dos ni
repetidas. Con varias hojas, el P.U. de cada renglón se compara **en cada hoja** (AH5, que ahora dice la hoja) y la
cantidad de la cabecera del APU se compara **una vez con la suma** de las hojas que traen ese renglón (AH6 y AH11). Con
una hoja, todo es como antes (mismos mensajes).

**Cómo.** `perfil_apu_por_hoja._hojas_presupuesto`; `PerfilApuPorHoja.hojas_presupuesto` (la primera sigue en
`hoja_presupuesto`); `fusion/apu_por_hoja.py`: `_renglones` lee solo las hojas pedidas, `_enlace` y `_otra_obra` con
`_sumas`; `ResultadoApuPorHoja.renglones` (cada renglón con su hoja) y `hojas_presupuesto`. Archivos:
`adapters/hoja_empresa/perfil_apu_por_hoja.py`, `fusion/apu_por_hoja.py`, `api/rutas/libros.py`.

**Simulación** (`simular_frentes.py`): caso 1, un libro de APU para dos frentes (FRENTE A 60 % y B 40 %, que suman la
cantidad de la obra; el renglón 3 de verdad no casa); caso 2, un libro de APU de un solo frente comparado con dos hojas.

| Opción para AH6 con varias hojas | Caso 1 (AH6) | Caso 2 (AH6) | Lectura |
|---|---|---|---|
| O1, cada hoja contra la cabecera | 10 (9 falsos) | 5 | ruido en el caso normal |
| **O2, la suma de las hojas (elegida)** | **1 (el verdadero)** | **5** | avisa lo real y, en el caso 2, que el libro no es de todos los frentes |
| O3, no comparar cantidades | 0 | 0 | esconde el verdadero |

Descartadas: O1 y O3 (tabla); un patrón de nombres de hoja (`patron_hoja`): las hojas de frente no siguen un patrón
común y una lista explícita es lo que hacen S10 y Presto (el presupuesto declara sus títulos).

## D2. La segunda fila de impuesto (RF-206)

**Qué se decidió.** `porcentajes.otros_impuestos` (opcional) en el perfil: el lector la lee como las demás y la suma al
impuesto (`ApuLeido.impuesto` es el total; `otros_impuestos`, su parte). AH4 dice el total y las dos partes.
Archivos: `perfil_apu_por_hoja.py`, `lector_apu_por_hoja.py`, `modelo.py`, `fusion/apu_por_hoja.py`.

| Opción (APU 5 ficticio: impuesto 16 %, otros 2 %) | Resultado | Con una nota que repite el rótulo «Impuesto» |
|---|---|---|
| **(i) clave aparte (elegida)** | 18 % | 18 % |
| (ii) sumar toda fila que casa con las variantes de `impuesto` | 18 % | 34 % (doble cuenta) |
| (iii) no leerla (antes) | 16 % | 16 % (la segunda se ignora en silencio) |

## D3. Las hojas que no siguen el prefijo (RF-207)

**Qué se decidió.** Un solo AH12 (Información, en la A1 de la primera) que nombra las hojas del libro de APU que no
empiezan por el prefijo del perfil, sin leerlas (a lo sumo diez nombres y «y n más»). La regla del prefijo vive en un
solo sitio (`lector_apu_por_hoja.es_hoja_de_apu`). Archivos: `lector_apu_por_hoja.py`, `fusion/apu_por_hoja.py`;
`tests/unit/test_fusion_apu_por_hoja.py` (la prueba de las hojas huecas espera ahora el AH12 y sigue midiendo que no se
leen).

| Opción (libro con «Portada», «Partida 6» y 3 hojas huecas) | Hallazgos | Hojas que se leen de más |
|---|---|---|
| A, uno por hoja | 5 | 0 |
| **B, uno que las nombra (elegida)** | **1** | **0** |
| C, leerlas para ver si parecen un APU | 1 | 5 (rompe el tope P1: las hojas ajenas no se materializan) |

## D4. La hoja del presupuesto, aparte del perfil (RF-208)

**Qué se decidió.** `POST /v1/libros/hojas` dice los nombres de las hojas de un libro subido (guardia de siempre, sin
materializar celdas) y `POST /v1/libros/apu-por-hoja` acepta `hoja_presupuesto` (una vez por hoja), que manda sobre el
perfil; se comparan sin mayúsculas ni espacios de más. Una hoja que no está es 422 y dice las que hay. La pantalla, al
soltar el presupuesto, ofrece sus hojas con casillas y marca las del perfil que el libro tiene.
Archivos: `api/rutas/libros.py`, `fusion/apu_por_hoja.py`, `paginas/auditoria/AuditarApuPorHoja.tsx`.

| Opción | Errores para auditar el frente B de un libro de dos frentes | Perfiles necesarios |
|---|---|---|
| Antes (una hoja por perfil) | 0, pero hace falta un perfil por frente | uno por frente |
| Campo de texto con el nombre | 1 por cada nombre mal tecleado (422, ahora con las hojas que hay) | 1 |
| **Casillas con las hojas del libro (elegida)** | **0** | **1** |
| Detección automática (la hoja que más casa) | 0, pero 7 veces el tiempo y empates (simulada en E2E-2) | 1 |

## D5. Poner un perfil local desde la interfaz (RF-209)

**Qué se decidió.** «Cuenta › Empresa», bloque «Perfiles de los libros de la empresa» (`POST
/v1/admin/empresa/perfiles-libros`, acción `administrar_empresa`). El perfil se valida entero antes de escribirse (las
mismas reglas que al cargarlo), pesa a lo sumo 64 KiB, su nombre sale del JSON (minúsculas, cifras y «_»: nunca una
ruta), no pisa uno que ya está sin «Reemplazar» (409) y se escribe primero en un temporal y luego en su sitio
(`os.replace`). Archivos: `perfil_apu_por_hoja.instalar_perfil_apu_por_hoja`, `api/rutas/admin_empresa.py`,
`paginas/administracion/PerfilesDeLibros.tsx` e `index.tsx`.

| Opción: quién lo pone | Riesgo simulado |
|---|---|
| Quien arma (`editar_hoja`) | el perfil trae una expresión regular (`patron_banda`): una hostil, «(a+)+$» contra 25 caracteres, tardó 4,25 s por descripción en este equipo; cualquiera que arma podría frenar las auditorías de todos |
| **Quien administra la empresa (elegida)** | el mismo riesgo queda en la cuenta que ya decide la empresa y su clave de firma |
| Solo desde el propio equipo (`Sensible`) | excesivo: el perfil no es un secreto |

Y sobre pisar uno que ya está: **409 sin «Reemplazar»** (elegida) frente a reemplazar siempre (se perdería en silencio
el perfil de otro frente). Límite conocido: la lista de perfiles (`GET /v1/libros/perfiles-apu-por-hoja`) es del router
de libros (quien arma y quien revisa), así que la pantalla de quien administra dice el perfil puesto pero no los lista.

## D6. Llevar a la Hoja el libro auditado (RF-210)

**Qué hace.** Desde la auditoría, «Llevar el libro a la Hoja de «obra»» (`POST /v1/hoja/libro`, solo una cuenta con
`editar_hoja`). La ruta audita el libro con `fusion.apu_por_hoja` (**el mismo lector y el mismo perfil: no hay un
segundo lector**) y pasa lo auditado a `aplicacion/libro_a_la_hoja.py` (que no importa `fusion`: la regla de capas). Ahí:

1. cada APU usado entra al catálogo por la misma puerta que Componer (`Catalogo.cargar_composicion` en la lista de
   `listas_para_armar.lista_de_hoy`); si el código ya está con la misma composición y los mismos precios, se reutiliza;
   si está con otra, entra como variante «-B», «-C»…; cada precio que puso el libro lleva su referencia «libro,
   HOJA!CELDA» (`core.catalog.origen.fijar_referencia`; un precio que ya tenía fuente la conserva);
2. cada renglón del presupuesto enlazado con su APU es un renglón TABULAR de la Hoja con la cantidad del presupuesto, el
   origen `libro:HOJA!CELDA` (la celda de la cantidad) y el frente (la hoja); sin presupuesto, uno por APU con la
   cantidad de su cabecera y el frente que se diga; lo que no tiene APU o cantidad no se lleva y se dice;
3. los porcentajes del libro (prestaciones como FCAS, administración, utilidad) pasan al borrador; hojas con juegos
   distintos son 422 y el mensaje dice en qué se apartan.

Todo o nada (el catálogo se deshace y el borrador vuelve a como estaba). La respuesta dice, por partida, el P.U. del
libro, el de la Hoja y si casan (`TOLERANCIA_PRECIO`). Se reutilizó: el informe de la auditoría (ahora
`ApuRecalculado` lleva la composición y los parámetros con que se recalculó, la cantidad de la cabecera y la celda del
precio de cada línea), `fusion.mapeo.composicion_de_apu_por_hoja`, el borrador de la obra de «llevar»
(`elaboracion.borrador_de_la_obra`, `hoja_edicion.cambiar_borrador`) y el registro de importaciones.
`crear_lista_desde_archivo` no sirve aquí: casa cada fila con un insumo que ya está en el catálogo (y pierde el equipo o
la mano de obra con unidad, expediente de precios del 2026-11-13), mientras que el libro trae insumos nuevos.

**Simulación** (pruebas de `tests/integration/test_api_hoja_libro.py` y conteo sobre dos libros ficticios, la obra A y
la obra B, cuyo APU 1 cuesta otro precio):

| Decisión | Opción | Resultado |
|---|---|---|
| Código que ya está con otro APU | rechazar (409) | la obra B no entra: 0 renglones |
| | **variante «-B» (elegida)** | 6 partidas en el catálogo (5 + VF-001-B); llevar otra vez la A no crea nada |
| | prefijar el frente en el código | 10 partidas (cada libro duplica las 5) y el código deja de ser el del libro |
| Moneda de los precios | suponer la de la carpeta | un libro en USD en una carpeta en Bs se valora como Bs, en silencio |
| | **la declara quien lleva; distinta de la carpeta, 409 (elegida)** | ningún precio cambia de moneda |
| | convertir con la tasa del BCV | el libro no dice la fecha de sus precios: la tasa sería inventada |
| A qué obra | **una obra sin versiones (elegida)** | los precios del libro quedan en la lista con que se guarda la primera versión |
| | una obra con versiones | la versión ya tiene su lista (inmutable): los APU nuevos no se podrían valorar |

**Segunda opinión** (Gemini `gemini-4-argon-medium` por `agy`, con solo la descripción ficticia de las tres opciones):
«de acuerdo» con la variante «-B» y la directiva `_frente`; señala dos riesgos: que el código de la variante depende
del orden en que se llevan los libros (la respuesta dice el código del libro, `codigo_libro`, pero el renglón no lo
guarda: queda como mejora, una directiva `_codigo_libro`) y que la igualdad del APU sea canónica (lo es: se compara el
`ComposicionAPU` del núcleo, con `Decimal` por su valor y las líneas en el orden canónico del catálogo).

Encontrado de paso (**expediente de `core/` propuesto, no aplicado**): `Catalogo.cargar_composicion` agrega cada
`PrecioInsumo` con `session.add` sin pasar por `lista.precios`, y `Catalogo.composicion` (vía `mapeo.a_composicion`)
lee esa colección. Si ya se cargó en la misma sesión (al comparar otra partida con la misma lista), la composición
recién cargada sale sin el precio de su insumo nuevo (`CatalogoIncompleto`). Regla propuesta: `_fijar_precio` agrega
el precio también a `lista.precios` (o expira la colección), como ya hace `reemplazar_composicion` con
`partida.composicion`. Es genérico (cualquier carga de dos APU con la misma lista en una sesión). Prueba en rojo
propuesta: cargar A, leer `composicion(A, lista=L)`, cargar B con un insumo nuevo y leer `composicion(B, lista=L)`.
Impacto: ninguno en los datos; hoy se esquiva expirando la colección en `aplicacion/libro_a_la_hoja.py`.

## D7. Dónde vive el frente de un renglón (RF-212)

**Qué se decidió.** Como la directiva `_frente` de `ItemComputo.especificaciones` (`aplicacion/frentes.py`): una clave
que empieza por «_» es una instrucción, no una especificación técnica (`core/verification/directivas.py`), así que R4
la ignora; viaja con el renglón y `core/budget/persistencia.py` la guarda y la devuelve con la versión.

| Opción | ¿Vuelve al abrir la versión? | ¿Cambia la clave del renglón? | Cambios |
|---|---|---|---|
| **Directiva `_frente` (elegida)** | sí (prueba `test_los_frentes_se_guardan_con_la_version_y_vuelven_al_abrirla`) | no | ninguno en `core/` ni en el esquema |
| Tabla aparte por (versión, clave) | sí, con una migración | no, pero «X\|o#2» se renumera al quitar un renglón y el frente se pierde | migración y sincronía al guardar |
| Codificarlo en `origen_id` | sí | sí: la cantidad escrita y la nota del renglón pierden su clave | rompe la trazabilidad (el origen es la celda) |

**Límite** (para el próximo re-congelado de `aplicacion/hoja.py`, de la línea 1): `cambios_entre` no ve un cambio de
frente; poner solo frentes en una versión ya guardada no habilita «Guardar» («No hay cambios»). En la primera versión
(altas) y junto con otro cambio, el frente sí se guarda. Propuesta: un `CambioEditado("frente", clave, "frente", antes,
después)` en `_cambios_de_cantidades`.

## D8. Agrupar el presupuesto por frente (RF-211)

**Qué se decidió.** `GET /v1/hoja/borradores/{id}/vistas/frentes`: el subtotal de cada frente (suma de cantidad × P.U.
de sus renglones; un renglón pendiente se cuenta aparte y no suma) y el total general (el del presupuesto), en el orden
en que aparece cada frente y con «Sin frente» al final; `PUT /v1/hoja/borradores/{id}/frentes` pone o quita el frente de
renglones propios. En la pestaña Presupuesto, «Ver el presupuesto por frente» (a pedido: la pestaña no pide la vista
hasta entonces, así no cambia la carga de siempre). La interfaz no calcula. En un router aparte
(`api/rutas/hoja_frentes.py`) para no tocar `api/rutas/hoja.py`.

| Opción de presentación | Lo que hacen S10, Presto y el Excel de la empresa | Resultado con el caso ficticio |
|---|---|---|
| Columna «Frente» en la tabla del presupuesto | Presto: una columna de capítulo | la tabla de partidas cambia de forma; sin subtotales |
| **Tabla de subtotales por frente, a pedido (elegida)** | S10 y Presto: presupuesto «por títulos» con subtotal y total general; el Excel de la empresa: una hoja por frente más un resumen | FRENTE A 2.814,68; FRENTE B 1.876,45; total 4.691,13 (a mano: 2.814,6756 + 1.876,4504) |
| Una pestaña nueva | — | una pestaña más para una tabla de tres columnas |

## Commits

| Paso | Rojo | Verde |
|---|---|---|
| 1, lector y perfil (D1 a D5), API | `f16650a0` | `67c3dbbc` |
| 1, pantalla (hojas y perfil local) | `92b0f222` | `0471efa9` |
| 2, llevar el libro a la Hoja (D6, D7), API | `9ca6f4d6` | `809eb6df` |
| 2, pantalla | `0fc2c35b` | `399027e0` |
| 3, por frente (D8), API | `4bf1e1eb` | `a4f52abd` |
| 3, pantalla | `8faed038` | el commit de documentos de esta bitácora |

Cierre: `ruff check` limpio en lo tocado; pruebas de los módulos tocados con `-W error`; `npm run lint` y
`npx vitest run` de las carpetas tocadas; `docs/api.json` regenerado (`scripts/exportar_openapi.py`).
