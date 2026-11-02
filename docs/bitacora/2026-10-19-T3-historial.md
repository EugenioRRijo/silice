# T3 · Historial de auditorías: parche RM-6, `no-store` y página

**Fecha:** 2026-10-19 · **Plan:** `docs/planes/PLAN_MIGRACION_FINAL_STREAMLIT.md` (T3) · **Fuente del parche:**
`docs/planes/PLAN_SESION_4_HISTORIAL.md` §3 · **Requisitos:** UC-30, RF-142 a RF-146, RNF-28.

## Rulings

**T3-R1. Guardar el historial nunca tumba la auditoría (RF-144).** `POST /v1/libros/auditoria` y
`POST /v1/libros/pdf` calculan el informe y, antes de responder, lo anotan en `instalacion.db`. Si anotar
falla, la respuesta es 200 con el informe completo y el campo nuevo `aviso_historial` con el texto
«No se pudo guardar la auditoría en el historial.» (`null` si se guardó). Se atrapa `Exception` y no una lista
corta: lo que falla aquí (base bloqueada, disco lleno, base de la instalación sin abrir, el servicio que rechaza
un dato) es siempre un problema de anotar, no de auditar; el usuario ya tiene su informe y perderlo por una
anotación sería peor. El defecto de programación no se esconde: queda en el registro del servidor a nivel
ERROR. Alternativa descartada: responder 500 (rompe el contrato de `/v1/libros/*` y castiga al usuario por un
fallo que no es suyo).

**T3-R2. Qué lleva el registro del fallo.** Solo el tipo de la excepción (`OperationalError`), sin traza ni
mensaje: el texto de un error de SQL repite los parámetros del `INSERT`, es decir, el nombre del archivo y los
hallazgos (RNF-28, «sin el contenido del archivo»). Se paga con menos detalle al depurar; el tipo y la hora bastan
para ubicar el fallo, y la causa se reproduce con el mismo archivo.

**T3-R3. Transacción propia, todo o nada.** El guardado abre su sesión (`sesion_de_instalacion`) y confirma al
final; cualquier excepción la cierra sin confirmar, así que no queda una fila a medias. No usa
`SesionInstalacionDep` porque su fallo al abrir (503) se produce al resolver las dependencias, fuera del
`try` de la ruta, y sí tumbaría la auditoría. Corre en el hilo auxiliar (`run_in_threadpool`), como el resto
del trabajo bloqueante de la ruta.

**T3-R4. Usuario y reloj.** El usuario es la cuenta de la sesión web (`Nombre <login>`) o `USUARIO_API` con la
clave, como en `/v1/produccion`. La hora de la fila es la del servidor (`datetime.now()` sin microsegundos):
es lo único que lee el reloj, no entra en el informe y por eso la misma petición sigue dando el mismo informe.
`devolucion` y `replica` no registran nada (no son auditorías nuevas: `devolucion` repite una ya hecha).

**T3-R5. El contrato crece, no cambia.** Las respuestas de `/auditoria` y `/pdf` suman `aviso_historial`
(opcional, `null` por omisión); ninguna clave existente cambia. La pantalla «Libro de la empresa» no la muestra
todavía: dónde ponerla es de quien tenga esa página (decisión para Eugenio o la sesión que la toque).

**T3-R6. `no-store` sin tragarse la excepción (`api/sin_cache.py`).** `RutaSinCache` pone `Cache-Control:
no-store` en toda respuesta de `/v1/auditorias-libro` y `/v1/produccion`, incluidos 401, 403, 404 y 422. La
primera versión atrapaba la `HTTPException` y devolvía la respuesta desde la ruta (como `_RutaCuentas`); la
prueba `test_si_la_importacion_falla_a_medias_no_queda_nada` la delató: con la excepción atrapada, la
dependencia con `yield` de la sesión de `instalacion.db` ve una salida normal y **confirma** una importación a
medias. Ahora la ruta solo añade la cabecera a la excepción y la relanza para que el manejador de la aplicación
la formatee; el 422 de validación (que ocurre antes de escribir nada) sí se contesta desde la ruta.
Hallazgo aparte, no corregido por no ser de T3: `_RutaCuentas` (`api/rutas/cuentas.py`) y cualquier otra clase de
ruta que atrape `HTTPException` bajo una dependencia con `yield` que confirma al salir tienen el mismo riesgo;
conviene revisarlas (las de `SesionDep` no confirman al salir, así que el riesgo real es solo para
`SesionInstalacionDep`).

## Lo que la API ofrece a la página y lo que no

La lista (`GET /v1/auditorias-libro?limite=1..100`) trae `{id, archivo, fecha, tipo, errores, advertencias}` y el
detalle suma usuario, huella, fecha del libro, totales, informativos, atípicos y hallazgos compactos. **No hay
filtros en la API, no hay proyecto asociado a una auditoría (el libro de la empresa no pertenece a un proyecto) y
no se guarda el informe ni el PDF (RNF-28)**. Por eso la página filtra en el cliente por fecha, tipo y resultado
sobre las últimas 100, y no ofrece filtro por proyecto ni descarga del informe: sería inventar un dato que no
existe. Si Eugenio quiere filtro por proyecto o más de 100, es un cambio de requisito (ERS) y de esquema.
