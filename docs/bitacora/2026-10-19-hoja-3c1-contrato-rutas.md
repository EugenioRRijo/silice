# Hoja 3c-1: contrato de la ruta de edición del espacio (E1) (para el agente de front)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Fuente:** diseño §3.1, §3.2, §4.1, §4.4 (E1) y §6.2
(fila 3c-1). Este documento se escribió ANTES de implementar. Si la implementación difiere, la bitácora de avance
(`2026-10-19-hoja-3c1-backend-avance.md`) lo dice; la fuente final es `docs/api.json`.

## Reglas comunes (como R1 a R14)

- Prefijo `/v1/hoja`; todo `Cache-Control: no-store` (también en errores propios de la ruta); errores `{"detalle": str}`.
- Solo cuenta con `EDITAR_HOJA` (rol `arma`): sin sesión 401; `rita` 403 «Su cuenta no tiene permiso para esta acción.»;
  `tomas` (contraseña temporal) 403; con `X-Silice-Clave` 403 «La hoja del proyecto se edita y se guarda con una cuenta;
  la clave de API no sirve.». Es un método que escribe: exige `X-Silice-CSRF` y `Origin` propio (403 si faltan).
- **Nada se escribe en la base en 3c**: la edición solo cambia el borrador en memoria del servidor. El guardado es 3d.
- Las celdas viajan SIEMPRE como texto (JSON string). La interfaz no convierte a número.

## E1 `PUT /v1/hoja/borradores/{id}/espacio` → `EdicionEspacioRespuesta`

`id`: el del borrador (R2), `^[A-Za-z0-9_-]{16,64}$`.

### Cuerpo

```
{ "rev": int,                                   # el rev que la persona vio (ResumenHoja.rev); entero >= 0
  "tablas": {                                   # las CINCO tablas completas; una ausente cuenta como vacía
    "origenes":  [ Fila, ... ],                 # <= 5000 filas
    "ambientes": [ Fila, ... ],                 # <= 1000
    "fuentes":   [ Fila, ... ],                 # <= 1000
    "puntos":    [ Fila, ... ],                 # <= 5000
    "tramos":    [ Fila, ... ] } }              # <= 20000   (vértices de recorridos)
Fila = { "<columna>": "<texto>" }               # clave = la `clave` de la columna de R5 (id, nombre, x0, ...)
```

- Cada texto de celda ≤ 500 caracteres. Una columna que falta cuenta como vacía; una columna desconocida se ignora
  (como la clásica). Máximo 40 columnas por fila y 64 caracteres por nombre de columna (tope de hardening).
- **Se manda la tabla completa**, no solo lo tocado (equivale al `data_editor` de la clásica: `espacio_desde_filas` recibe
  las cinco tablas). Lo que el editor no muestra (circuitos, sobrescrituras, recorridos propuestos) lo conserva el
  servidor de la base del borrador (`base=borrador.espacio`). Una fila totalmente en blanco no es un error y se ignora.
- Un nombre de tabla que no sea esas cinco es 422.

### Respuesta 200

```
{ "rev": int,                                   # el rev NUEVO (= resumen.rev); sube 1 si el borrador cambió
  "resumen": Resumen,                           # como R2/R3: total, cambios (vs la versión abierta), pendientes_catalogo,
                                                #   hallazgos, hay_plan, version_mas_nueva, guardado_como
  "espacio": VistaEspacioRespuesta }            # la misma forma que R5, ya recalculada con el borrador nuevo
```

- `resumen.cambios` es el conteo de `cambios_entre(versión abierta, borrador)` (la lista llega con E9, en 3c-3).
- `espacio.filas` es el espacio **canónico** del borrador (`filas_desde_espacio`): `2.500` vuelve como `2.5`. El front NO
  debe pisar lo que la persona está escribiendo con ese eco; es para re-sembrar al cambiar de pestaña o tras un 409.
- `espacio.estado` (Estado por fila), `espacio.derivadas`, `espacio.total`, `espacio.pendientes` y `espacio.vacio_mensaje`
  son los de R5. Las demás vistas (R6 a R11) se piden al montar su pestaña y ya leen el borrador nuevo.
- Si las tablas describen EXACTAMENTE el mismo espacio que ya tiene el borrador, no hay cambio: `rev` no sube y se
  responde 200 con el estado actual (como la clásica, que no hace nada si `nuevo == borrador`).
- Una partida nueva derivada por la edición toma su APU del catálogo del caso y desde entonces es parte de la copia de la
  versión (`completar_composiciones`, con la lista de precios de la versión abierta); una sin APU queda pendiente y
  `resumen.pendientes_catalogo` la cuenta.

### Errores (en este orden de precedencia)

| Código | Cuándo | `detalle` |
|---|---|---|
| 401 / 403 | sin sesión; rol; clave de API; CSRF/Origin | los de arriba |
| 422 | forma: `rev` ausente o no entero, una celda que no es texto o pasa de 500 caracteres, más filas que el tope, tabla desconocida | `Los datos del espacio no tienen la forma esperada: escriba cada celda como texto de hasta 500 caracteres y no pase de 5000 orígenes, 1000 ambientes, 1000 fuentes, 5000 puntos y 20000 vértices.` (fijo, **sin repetir lo enviado**) |
| 404 | el borrador no existe para MI ficha (nunca existió, venció, se descartó o es de otra ficha) | `Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.` |
| 409 | el caso cambió desde que se abrió el borrador | `El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual.` |
| 409 | el borrador ya se guardó (3d; hoy nunca ocurre) | `Este borrador ya se guardó como la versión {c}; abra esa versión para seguir.` |
| 409 | `rev` distinto del vigente (otra ventana lo cambió) | `El borrador cambió en otra ventana: vuelva a cargarlo.` — **nada cambia**; el front pide R3 (`GET /borradores/{id}`) para ver el `rev` actual y R5 para re-sembrar |
| 422 | dato de dominio inválido | el mensaje de la clásica, SIN el sufijo: `ambientes, fila 2: alto: '2,5' no es un numero decimal valido`. El front compone «{detalle}. La hoja sigue con el último borrador válido.» **El borrador no cambia y `rev` no sube.** Este 422 sí repite el valor escrito (paridad con la clásica; diseño §4.1) |
| 413 | cuerpo > 20 MiB (lo impone el middleware global `LimiteDeCuerpo`, no la ruta) | `El cuerpo de la peticion excede el maximo de 20 MiB.` (sin eco; esta respuesta no lleva `Cache-Control`, es del middleware) |
| 503 | no se pudo leer el caso | `No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.` |

Los mensajes de dominio (422) salen de `aplicacion.hoja.espacio_desde_filas` y van **sin tildes**, tal como los de la
clásica; los demás textos de arriba llevan tildes. Ejemplos de dominio, todos con la forma `{tabla}, fila {n}: {error}`
(tabla = `origenes de medida`, `ambientes`, `fuentes`, `puntos`, `vertices de recorridos`; `n` es la posición de la
fila en la tabla enviada, desde 1, contando las filas en blanco):

- `ambientes, fila 2: alto: '2,5' no es un numero decimal valido` (solo punto decimal)
- `puntos, fila 3: tipo: 'xx' no es un valor valido (...)`
- `vertices de recorridos, fila 1: recorrido_id: el tramo debe nombrar su recorrido`
- errores de referencia o de id duplicado (los del modelo `Espacio`), sin número de fila.

## Concurrencia

Cada borrador lleva un cerrojo: una petición a la vez por borrador; la comprobación de `rev`, la validación y el
reemplazo ocurren dentro de él. El front manda una sola petición en vuelo por borrador (la última edición gana) y, ante
un 409 de `rev`, recarga las semillas. La edición completa con dos hilos es 3c-3.

## Memoria

Cada 20 cambios aceptados el servidor vuelve a estimar el tamaño del borrador (deuda M5 de 3b-1); si el total del
proceso supera el tope, expulsa el más antiguo (nunca el que se está editando). El front no lo nota salvo que otro
borrador suyo ya no exista (404 con el texto de arriba).

## Lo que NO cambia

Rutas R1 a R14, `ui/*`, `core/`, `asistente/`. La hoja no se activa en el menú (`rutas.ts` intacto hasta 3d-2).
