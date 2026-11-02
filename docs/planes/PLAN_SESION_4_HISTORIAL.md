# Plan de la sesión 4: historial de auditorías de «Libro de la empresa»

> Sesión 4 de la [ruta](RUTA_SESIONES.md). Enmienda de la ERS: UC‑30, RF‑142 a RF‑146 y RNF‑28.
> Estado al 2026‑10‑18: servicio, migración y rutas de lectura **construidos**; la ruta que escribe
> (`api/rutas/libros.py`) **queda como parche descrito aquí** (RM‑6).

## 1. Decisión

Eugenio decide que cada auditoría de «Libro de la empresa» se guarda: el resumen y los hallazgos
compactos. **Nunca** se guarda el libro ni el PDF; solo su nombre sin ruta y su huella SHA‑256
(RNF‑28). Repetir una auditoría deja otra fila; no se deduplica por huella.

## 2. Lo construido

| Pieza | Dónde |
|---|---|
| Tabla `auditoria_libro` (sin columna binaria) | `fusion/historial_modelo.py`, migración `migraciones/instalacion/versions/ins_0003_auditoria_libro.py` |
| Servicio sin FastAPI | `fusion/historial.py`: `registrar_auditoria`, `registrar_resultado` (libro), `registrar_resultado_pdf` (PDF simple), `listar`, `detalle` |
| Rutas de lectura | `api/rutas/auditorias_libro.py`: `GET /v1/auditorias-libro` (`limite` 1 a 100, 20 por omisión) y `GET /v1/auditorias-libro/{id}` |
| Tope de hallazgos | 500 por auditoría; pasado el tope `recortado` es verdadero y los conteos siguen siendo los de todos |

El servicio solo hace `flush`: confirmar o deshacer es de quien lo llama.

## 3. RM‑6: el parche pendiente en `api/rutas/libros.py`

**Por qué queda aparte.** La página «Libro de la empresa» y su ruta las tocan otras sesiones (S2 y S3;
ver RM‑6 de [PLAN_SESION_2B_MIGRACION.md](PLAN_SESION_2B_MIGRACION.md)). Para no chocar, la sesión 4
entrega el servicio y las rutas de lectura, y deja el parche descrito para quien tenga libre ese archivo.

**Qué hace el parche.** En `POST /v1/libros/auditoria` y `POST /v1/libros/pdf`, después de calcular el
informe y **antes de responder**:

1. Abrir una transacción propia (`SesionDep`) y llamar a `registrar_resultado(sesion, r, usuario=..., ahora=...)`
   en la ruta del libro, o a `registrar_resultado_pdf(sesion, r, usuario=..., nombre_archivo=nombre, ahora=...)`
   en la del PDF. Es el mismo `registrar_auditoria` que usa el servicio, con los hallazgos ya compactados.
2. Confirmar. Si guardar falla (cualquier excepción), **no tumbar la auditoría** (RF‑144): deshacer, dejar el
   fallo en el registro del servidor (sin el contenido del archivo) y responder 200 con el informe. La
   respuesta lleva un campo que la pantalla traduce en el aviso «No se pudo guardar el historial».
3. `usuario` sale de la cuenta cuando hay sesión web y es `USUARIO_API` cuando entra la clave, igual que en
   `api/rutas/produccion.py` (`_usuario`).
4. Los archivos no se escriben en disco en ningún punto del camino (RNF‑28).

**Cierre del parche.** Pruebas en rojo primero (`tests/integration/test_api_libros.py` o el archivo de
rutas de libros que exista): con el guardado forzado a fallar, ambas rutas responden 200 con el informe y el
registro lleva el fallo; con el guardado sano, la fila aparece en `GET /v1/auditorias-libro`. Después
actualizar la fila de RF‑144 y RNF‑28 en [plan_pruebas.md](../plan_pruebas.md) de «por aplicar» a «cumple».

## 4. Fuera de alcance

- La pantalla del historial (la consume la página Inicio de la migración; no se construye aquí).
- Borrar o exportar el historial: no hay requisito.
- Guardar el contenido de los archivos: prohibido por RNF‑28.

## 5. Pruebas

Las de los servicios y las rutas de lectura ya existen y están listadas en la sección 8.0g de
[plan_pruebas.md](../plan_pruebas.md). Este documento lo comprueba
`tests/unit/test_documentos_historial_auditorias.py`.
