# Hoja 3c-2: contrato de las rutas de edición E2 a E5 (para el agente de front)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `c8bbfc3` · **Fuente:** diseño §3.2, §4.1,
§4.4 (E2 a E5) y §6.2 (fila 3c-2). Se escribió ANTES de implementar. Si la implementación difiere, la bitácora de avance
(`2026-10-19-hoja-3c2-backend-avance.md`) lo dice; la fuente final es `docs/api.json`.

## Reglas comunes (idénticas a E1; ver `2026-10-19-hoja-3c1-contrato-rutas.md`)

- Prefijo `/v1/hoja/borradores/{id}`; `id` = `^[A-Za-z0-9_-]{16,64}$`. Todo `Cache-Control: no-store` (también en los errores
  propios de la ruta; el 413 es del middleware y no lo lleva).
- Solo cuenta con `EDITAR_HOJA` (rol `arma`): sin sesión 401; `rita` 403 «Su cuenta no tiene permiso para esta acción.»;
  `tomas` 403; con `X-Silice-Clave` 403 «La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no
  sirve.». Escriben: exigen `X-Silice-CSRF` y `Origin` propio.
- **Nada se escribe en la base**: solo cambia el borrador en memoria. El guardado es 3d.
- Todo valor viaja como TEXTO (JSON string); la interfaz no convierte a número. La coma decimal la decide el servidor con el
  mensaje de la clásica (`'2,5' no es un numero decimal valido`; D-8).
- Todas devuelven `{ "rev": int, "resumen": Resumen, "<vista>": ... }` con el borrador YA recalculado:
  `rev` = el rev NUEVO (= `resumen.rev`; sube 1 si el borrador cambió); `resumen` como R2/R3/E1 (total, `cambios` = conteo de
  `cambios_entre(versión abierta, borrador)`, `pendientes_catalogo`, `hallazgos`, `hay_plan`…). La vista es la de la pestaña que se
  edita, con la misma forma que su ruta de lectura. Las demás vistas se piden al montar su pestaña y ya leen el borrador nuevo.
- Si lo enviado deja el borrador igual, NO hay cambio: `rev` no sube y se responde 200 con el estado actual.
- Un cambio válido pasa por `completar_composiciones` (una partida nueva toma su APU del catálogo), como en la clásica.
- Concurrencia: una petición a la vez por borrador (su cerrojo). La comprobación de `rev`, la validación y el reemplazo ocurren
  dentro de él. Orden de bloqueos idéntico al de E1: cerrojo del borrador y, dentro, el del registro (nunca al revés).

### Errores comunes, en este orden de precedencia

| Código | Cuándo | `detalle` |
|---|---|---|
| 401 / 403 | sin sesión; rol; clave de API; CSRF/Origin | los de arriba |
| 422 | FORMA del cuerpo (ver cada ruta): `rev` ausente / no entero / negativo, un valor que no es texto o pasa de 500 caracteres, más filas que el tope, campo desconocido | un mensaje FIJO por ruta, **sin repetir lo enviado** |
| 404 | el borrador no existe para MI ficha | `Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.` |
| 409 | el caso cambió desde que se abrió | `El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual.` |
| 409 | el borrador ya se guardó (3d) | `Este borrador ya se guardó como la versión {c}; abra esa versión para seguir.` |
| 409 | `rev` distinto del vigente (se comprueba ANTES que el contenido) | `El borrador cambió en otra ventana: vuelva a cargarlo.` |
| 409 / 422 | específicos de la ruta (abajo) | ver cada ruta |
| 413 | cuerpo > 20 MiB (`LimiteDeCuerpo`) | `El cuerpo de la peticion excede el maximo de 20 MiB.` |
| 503 | no se pudo leer el caso | `No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.` |

Un 422 de DOMINIO lleva el mensaje de la clásica SIN sufijo; el front compone «{detalle}. La hoja sigue con {las últimas
cantidades válidas | los últimos parámetros válidos | el último plan válido}.». **El borrador no cambia y `rev` no sube.** Este 422
sí repite el valor escrito (paridad con la clásica; diseño §4.1).

## E2 `PUT /v1/hoja/borradores/{id}/cantidades` → `EdicionCantidadesRespuesta`

Cuerpo (`extra` prohibido):

```
{ "rev": int,
  "filas": [ { "clave": "<texto>", "cantidad": "<texto>" }, ... ] }     # <= 20000 filas; cada texto <= 500 caracteres
```

- `clave` es la de la fila de R6 (`partida|origen_id`, con `#2`, `#3` si se repite). Se mandan SOLO las filas tocadas.
- El servidor arma la tabla completa en el orden de `items_sin_escribir`: cada renglón no enviado conserva su cantidad vigente
  (la escrita a mano o la calculada), así `fila {n}` es la posición del renglón en el presupuesto, como en la clásica, aunque
  el cliente mande una sola fila.
- Un valor IGUAL al calculado deja de ser «escrito» (vuelve a ser del sistema; atajo «Volver a la calculada»). Escribir un valor
  distinto saca el renglón del cálculo del sistema (DA-SF-5): R8 lo marca ADVERTENCIA y queda en el registro de la versión.
- Una `clave` que no es de ningún renglón, o repetida en `filas`: 422 `Las cantidades enviadas no corresponden a los renglones
  del presupuesto: vuelva a cargarlo.` (diferencia declarada: la clásica la ignoraba en silencio).

Respuesta 200: `{ "rev": int, "resumen": Resumen, "presupuesto": VistaPresupuestoRespuesta }` (la forma de R6).

Errores propios:

| Código | `detalle` |
|---|---|
| 422 forma | `Las cantidades no tienen la forma esperada: envíe cada renglón como clave y cantidad en texto de hasta 500 caracteres, con no más de 20000 renglones.` |
| 422 dominio | `presupuesto, fila {n} ({partida}): cantidad: '{texto}' no es un numero decimal valido` (o `... no es un monto finito`), o `presupuesto, fila {n} ({partida}): la cantidad no puede ser negativa; escriba cero o una cantidad positiva` |

## E3 `PUT /v1/hoja/borradores/{id}/parametros` → `EdicionParametrosRespuesta`

Cuerpo (`extra` prohibido; los CUATRO campos son obligatorios):

```
{ "rev": int, "fcas": "<texto>", "bono_alimentacion": "<texto>", "administracion": "<texto>", "utilidad": "<texto>" }
```

Un cambio válido recalcula todos los APU y el total.

Respuesta 200: `{ "rev": int, "resumen": Resumen, "parametros": VistaParametrosRespuesta }` (la forma de R10: campos como texto
exacto, `moneda_proyecto`, `total`, `puede_convertir`).

| Código | `detalle` |
|---|---|
| 422 forma | `Los parámetros no tienen la forma esperada: envíe fcas, bono_alimentacion, administracion y utilidad, cada uno como texto de hasta 500 caracteres.` |
| 422 dominio | `parametros: {campo}: '{texto}' no es un numero decimal valido` (p. ej. `parametros: utilidad: 'mucho' no es un numero decimal valido`) |

## E4 `PUT /v1/hoja/borradores/{id}/plan` → `EdicionPlanRespuesta`

Cuerpo (`extra` prohibido):

```
{ "rev": int,
  "etiquetas": [ "<periodo>", ... ],                      # 1 a 500, DISTINTAS entre sí, nunca "partida"; las de R8
  "filas": [ { "partida": "<código>", "valores": { "<etiqueta>": "<fracción en texto>" } }, ... ] }   # <= 5000 filas
```

- La matriz es completa (una fila por partida, como la clásica). Una celda ausente o vacía vale 0; una clave de `valores` que no
  esté en `etiquetas` se ignora. Una fila con `partida` vacía se ignora. Cada partida debe sumar EXACTAMENTE 1 y ninguna
  fracción puede ser negativa.
- Dos filas con la misma `partida`: 422 `plan: una partida aparece en más de una fila; deje una sola fila por partida.`
  (diferencia declarada; protege la suma).

Respuesta 200: `{ "rev": int, "resumen": Resumen, "plan": VistaPlanRespuesta }` (la forma de R8: matriz y curva recalculada).

| Código | `detalle` |
|---|---|
| 422 forma | `El plan no tiene la forma esperada: envíe periodos distintos (de 1 a 500) y cada fracción como texto de hasta 500 caracteres, con no más de 5000 partidas.` |
| 409 | el borrador no tiene plan: `Esta versión no tiene plan de trabajo: cree primero el plan secuencial.` (se comprueba después de `rev` y antes del contenido) |
| 422 dominio | `plan, partida {c}: {etiqueta}: '{texto}' no es un numero decimal valido`; `plan, partida {c}: la fraccion de {etiqueta} no puede ser negativa`; `plan, partida {c}: las fracciones suman {x} y deben sumar exactamente 1; repartala entre los periodos hasta completar 1` |

## E5 `POST /v1/hoja/borradores/{id}/plan/secuencial` → `EdicionPlanRespuesta`

Cuerpo: `{ "rev": int }` (`extra` prohibido). Crea el plan secuencial (una partida por periodo, al 100 %, en el orden del
presupuesto) para un borrador SIN plan. Respuesta 200 como E4.

| Código | `detalle` |
|---|---|
| 422 forma | `La petición debe traer el rev del borrador, un número entero.` |
| 409 | ya tiene plan: `Esta versión ya tiene plan de trabajo: edítelo en la matriz del plan.` (después de `rev`) |

## Lo que NO cambia

R1 a R14, E1, `ui/*`, `core/`, `asistente/`, `rutas.ts`. E6 a E11 son 3c-3.
