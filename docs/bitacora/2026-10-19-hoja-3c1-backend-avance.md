# Hoja 3c-1: avance del backend (E1, edición del espacio) y verificación

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `647c67e`
El contrato exacto de la ruta está en `2026-10-19-hoja-3c1-contrato-rutas.md` (escrito antes de implementar).

## Parejas prueba → implementación (rojo visto primero)

| Pareja | Prueba | Implementación |
|---|---|---|
| Contrato de E1 | `6464aae` (docs, antes de codificar) | — |
| Paridad `espacio_desde_filas` / `completar_composiciones` con `ui.hoja` vivo | `4828653` (caracterización: la copia ya existía, **pasa a la primera**) | — |
| Re-estimación del tamaño cada 20 cambios (M5 de 3b-1) | `93d49b1` (rojo: 5 de 6 fallan, la otra es una guarda que ya pasaba; el mensaje del commit dice «4 de 6» por error, el dato bueno es este) | `1648288` |
| E1 `PUT /v1/hoja/borradores/{id}/espacio` | `e3f6080` (rojo: la ruta no existía, 404 en todas) | ver `git log` (commit `feat(api): edicion del espacio E1`) |

## Ajustes de prueba hechos tras ver el resultado (declarados)

- `test_e1_en_un_proyecto_sin_versiones…` y `…sin_apu_en_el_catalogo…`: la primera corrida dio 422 «el punto 'LZ1' cita un
  circuito inexistente: 'C2'» (un borrador en blanco no tiene circuitos; se declaran al importar un plano). Fue un error de
  mi prueba, no del código: ahora envía las tablas de OF-001 sin `circuito_id` (`_sin_circuitos`) y compara contra las
  partidas que el propio espacio deriva (más de 20), no contra 30.
- `test_e1_un_cuerpo_de_mas_de_20_mib…`: el diseño (3c-B17) pide 413 también con el cuerpo por partes. En la aplicación real
  da **400** «There was an error parsing the body» (FastAPI convierte la excepción con que `LimiteDeCuerpo` corta la lectura
  antes de que el middleware conteste). Con `Content-Length` declarado sí da 413 con el texto exacto. La prueba del cuerpo por
  partes acepta 400 o 413 (el cuerpo se corta, no se repite lo enviado y el borrador no cambia). **Hallazgo para el
  orquestador:** el arreglo está en `api/proteccion.py` (archivo compartido que no toco): marcar en `recibir` que se excedió el
  tope y, en `enviar`, sustituir por el 413 cualquier respuesta que empiece después.
- Sanidad de las pruebas (mutaciones con el código restaurado después): sin la comprobación de `rev` falla el orden «rev antes
  que el contenido» (la comprobación del registro la sigue cubriendo, doble defensa); sin `completar_composiciones` fallan las
  dos pruebas de B9 que usan un catálogo con la partida.

## Diferencias y límites declarados

- **Respuesta de E1:** `{rev, resumen, espacio}` (`espacio` = la forma de R5). `resumen.cambios` es el conteo; la lista de
  cambios es E9 (3c-3), no se adelantó.
- **Edición idéntica:** si las tablas describen el mismo espacio, `rev` no sube (como la clásica, `nuevo == borrador`).
- **Errores de base o `CatalogoIncompleto`:** la clásica avisaba y seguía con el borrador sin completar; la API responde 503/409
  y deja el borrador intacto (más estricto).
- **Hardening añadido:** máximo 40 columnas por fila y 64 caracteres por nombre de columna (no está en el diseño).
- **422 de forma de E1** lleva un mensaje propio (menciona los topes) en lugar de `MENSAJE_FORMA`; también lo recibe un `id`
  mal formado en esa ruta. 422 se resuelve antes que 404/409 (FastAPI valida el cuerpo antes de entrar a la ruta).
- **413:** la respuesta del middleware no lleva `Cache-Control`.
- **No hecho aquí (otras sub-rebanadas):** 3c-B18 (medición, es de 3c-3), `rev` con dos hilos (3c-3), E2 a E11.
- La edición de una versión de solo lectura se acepta (el candado es de guardar), como en la clásica.
