# Hoja 3b-1: abrir una versión sin instantánea rompe la cadena, también en la clásica (decisión para Eugenio)

**Fecha:** 2026-10-19 · **Detectado por:** el implementador de 3b-1 y confirmado por el árbitro (ronda 1).

## Hallazgo
La cláusula de 3b-B11 del diseño (§6.1: «tras R2 sobre una versión sin instantánea,
`estado_de_la_cadena(...).integra` es verdadero») **es inviable bajo el Plan C**. `abrir_version` (la de
`ui/hoja.py`, copiada tal cual a `aplicacion/hoja.py`) llama a `asegurar_instantanea`, que escribe un
`RegistroCambio` (objeto `apu`, campo `instantanea`, `version_resultante_id` = la versión abierta) sobre una versión
que ya tiene su eslabón (o que no lo tiene). `core.budget.cadena.verificar_cadena` recalcula la huella de los registros de
la versión y ya no coincide. Pasa **igual en la página clásica**: la copia solo reproduce el comportamiento.

| Caso | Estado de la cadena después de abrir (literal) |
|---|---|
| versión sellada, sin instantánea | `Cadena rota en la versión 001: su registro de cambios no coincide con su huella; alguien cambió la base fuera del sistema. Revíselo con el administrador antes de entregar un paquete.` |
| versión sin sello (anterior a la cadena) | `Cadena rota en la versión 001: no tiene eslabón; alguien cambió la base fuera del sistema. Revíselo con el administrador antes de entregar un paquete.` |

En el caso sellado, la cadena ya estaba rota **antes** de abrir (borrar la instantánea cambia el contenido sellado); el
único escenario realista es una versión de antes de la cadena, que queda «sin eslabón» hasta su primer guardado
(sellado retroactivo).

## Reproductor mínimo
`tests/unit/test_api_hoja.py::test_r2_sobre_una_version_sin_instantanea_deja_la_cadena_como_la_deja_la_clasica`
(prueba de **caracterización**: pasa porque describe el comportamiento actual). Copia OF-001, le borra la instantánea
(`tests.fixtures.hoja_en_base.borrar_instantanea`), abre con `ui.hoja.abrir_version`, con `aplicacion.hoja.abrir_version` y
con `POST /v1/hoja/borradores`, y afirma que las tres dejan el mismo `estado_de_la_cadena` (los literales de arriba).

## Decisión
- Bajo Plan C la copia debe seguir idéntica a la clásica y `ui/hoja.py` está congelado (RS-9): **no se corrige aquí**.
- **Para Eugenio:** es un posible defecto de la clásica (abrir una versión vieja deja la cadena sin integridad hasta
  guardar). Corregirlo tocaría `ui/hoja.py` (congelado) o `core/budget/instantanea.py` (decisión del tutor).
- La cláusula de 3b-B11 queda como «inviable bajo Plan C, ver esta bitácora».

## Diferencias y límites declarados de 3b-1 (menores del árbitro)
- **M1 · versión por omisión.** `aplicacion/hoja_vista.version_por_omision` toma, entre las no descartadas (o todas si todas
  lo están), la vigente y, si no hay, la **última no descartada** (lo que fija 3b-B5). La clásica (P:417-421) toma la
  vigente aunque no esté en la lista y, si no está, cae al primer elemento. Diferencia deliberada (DV, §9.3).
- **M4 · DELETE con `keepalive`.** El diseño (3b-F15) pide el `DELETE` del borrador al desmontar «con `keepalive`»;
  `api/cliente.ts` (`pedir`) no lo soporta y no es de este encargo. El `DELETE` se manda igual (la petición no se cancela
  al desmontar la página); solo se perdería si el navegador cierra la pestaña. Un borrador que quede se va solo a las 8 h.
- **M5 · tamaño del borrador.** `Registro.reemplazar` no vuelve a estimar `tamano` cada 20 cambios (diseño §3.1); 3b-1 no
  edita, así que el tamaño es el de la apertura. Se hace en 3c junto con la edición.
- **Medida de respaldo.** TI-001 trae un `mappingproxy` que `pickle` no serializa: la estimación del tamaño cae a un
  recorrido de objetos (`_recorrido`), declarado en `aplicacion/hoja_borradores.py`.
- **Cambio de caso (3b-B28).** `caso_web.fijar` olvida los borradores de la ficha, así que tras `POST /v1/casos/actual` R3
  da 404 y R4 204; el 409 con mensaje fijo es la defensa en profundidad y se prueba forzando el cambio sin pasar por `fijar`.
- **3b-B14.** `tomas` (contraseña temporal) no puede abrir borradores; la prueba cruzada usa dos fichas de `ana`.
