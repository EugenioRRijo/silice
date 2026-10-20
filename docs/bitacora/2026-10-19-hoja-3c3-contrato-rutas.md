# Hoja 3c-3: contrato de las rutas E6 a E11 (para el agente de front)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `651f771` · **Fuente:** diseño §3.2, §4.1, §4.4
(E6 a E11) y §6.2 (fila 3c-3). Se escribió ANTES de implementar. Si la implementación difiere, la bitácora de avance
(`2026-10-19-hoja-3c3-backend-avance.md`) lo dice; la fuente final es `docs/api.json`.

## Reglas comunes (idénticas a E1 a E5; ver `2026-10-19-hoja-3c2-contrato-rutas.md`)

- Prefijo `/v1/hoja/borradores`; `id` = `^[A-Za-z0-9_-]{16,64}$`. Todo `Cache-Control: no-store` (también en los errores propios de
  la ruta; el 413 es del middleware y no lo lleva).
- Solo cuenta con `EDITAR_HOJA` (rol `arma`): sin sesión 401; `rita` 403 «Su cuenta no tiene permiso para esta acción.»; `tomas`
  403; con `X-Silice-Clave` 403 «La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve.». Las que
  escriben o crean (E6, E7, E11) exigen `X-Silice-CSRF` y `Origin` propio. Las de lectura (E8, E9, E10) son GET.
- **Nada se escribe en la base** (salvo la instantánea que ya escribe R2 al abrir): solo cambia el borrador en memoria.
- Todo valor viaja como TEXTO. La coma decimal la decide el servidor con el mensaje de la clásica.
- Las ediciones (E6, E7) devuelven `{ "rev": int, "resumen": Resumen, "apu": VistaApuRespuesta }` con el borrador YA recalculado:
  `rev` = el rev NUEVO (= `resumen.rev`); `apu` es la forma de R7 con `seleccionada` = la partida editada (si la partida no está
  entre las valoradas, R7 elige la primera, como siempre). Si lo enviado deja el borrador igual NO hay cambio: `rev` no sube y se
  responde 200 con el estado actual.
- Concurrencia: una petición a la vez por borrador (su cerrojo). `rev` se comprueba ANTES que el contenido. **Dos peticiones con
  el mismo `rev` (en la misma ruta o en rutas distintas): exactamente una gana (200) y la otra recibe 409 `El borrador cambió en
  otra ventana: vuelva a cargarlo.`** Orden de bloqueos: cerrojo del borrador y, dentro, el del registro (nunca al revés).

### Errores comunes de E6 y E7, en este orden de precedencia

| Código | Cuándo | `detalle` |
|---|---|---|
| 401 / 403 | sin sesión; rol; clave de API; CSRF/Origin | los de arriba |
| 422 | FORMA del cuerpo: `rev` ausente / no entero / negativo, un valor que no es texto o pasa de 500 caracteres, más líneas que el tope, campo desconocido | un mensaje FIJO por ruta, **sin repetir lo enviado** |
| 404 | el borrador no existe para MI ficha | `Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.` |
| 409 | el caso cambió desde que se abrió | `El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual.` |
| 409 | el borrador ya se guardó (3d) | `Este borrador ya se guardó como la versión {c}; abra esa versión para seguir.` |
| 409 | `rev` distinto del vigente | `El borrador cambió en otra ventana: vuelva a cargarlo.` |
| 413 | cuerpo > 20 MiB | `El cuerpo de la peticion excede el maximo de 20 MiB.` |
| 503 | no se pudo leer el caso | `No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.` |

Un 422 de DOMINIO lleva el mensaje de la clásica SIN sufijo; el front compone «{detalle}. La hoja sigue con el último APU válido.».
**El borrador no cambia y `rev` no sube.** Este 422 sí repite el valor escrito (paridad con la clásica; diseño §4.1).

## E6 `PUT /v1/hoja/borradores/{id}/apu/{partida}` → `EdicionApuRespuesta`

`partida` = el código de la partida (puede traer `/`, p. ej. `EL-TUB-EMT-3/4`: la ruta lo admite como segmento con barras; el front
lo manda con `encodeURIComponent`). Cuerpo (`extra` prohibido; los CINCO campos son obligatorios):

```
{ "rev": int,
  "rendimiento": "<texto>",
  "materiales": [ "<cantidad>", ... ],      # una por línea del APU, EN ORDEN; <= 500 líneas cada rubro; texto <= 500 caracteres
  "equipos":    [ "<cantidad>", ... ],
  "mano_obra":  [ "<cantidad>", ... ] }
```

- Solo cambian la cantidad de cada línea y el rendimiento (`composicion_con_cantidades` sobre la copia de la versión, DA-SF-7);
  descripción, unidad, precio y depreciación son los de la línea. Para quitar o agregar una línea se usa Componer, no la hoja.
- El número de cantidades de cada rubro debe ser el de líneas del APU; si no, 422 con el texto de la clásica
  `materiales: la tabla tiene 3 lineas y el APU 2; en la hoja solo se edita la cantidad de cada linea (para agregar o quitar una, use Componer)`.
  (En la práctica solo ocurre con un cliente con el APU desactualizado.)
- Un APU idéntico al vigente no es cambio (`rev` no sube).

Respuesta 200: `{ "rev": int, "resumen": Resumen, "apu": VistaApuRespuesta }`.

Errores propios:

| Código | `detalle` |
|---|---|
| 422 forma | `El APU no tiene la forma esperada: envíe el rendimiento y las cantidades de materiales, equipos y mano de obra, cada una como texto de hasta 500 caracteres, con no más de 500 líneas por rubro.` |
| 404 partida | (después de `rev`) `Esa partida no tiene APU en este borrador: vuelva a cargar la lista de partidas.` |
| 422 dominio | `materiales, fila 2: la cantidad no puede ser negativa` · `mano de obra, fila 1: cantidad: 'x' no es un numero decimal valido` (rótulos `materiales`, `equipos`, `mano de obra`) · `rendimiento: '0,5' no es un numero decimal valido` · el texto del modelo si el rendimiento es 0 o negativo |

## E7 `POST /v1/hoja/borradores/{id}/apu/{partida}/insumo` → `EdicionApuRespuesta`

Cuerpo (`extra` prohibido): `{ "rev": int, "tipo": "<texto>", "indice": int >= 0, "insumo": "<código del insumo>" }`.
`tipo` = `material`, `equipo` o `mano_obra`; `indice` = la línea (desde 0) del rubro. Toma del insumo descripción, unidad (solo
material) y precio (sueldo en mano de obra); **conserva la cantidad** (y la depreciación de un equipo).

Precedencia (después de `rev`): versión abierta → partida → contenido.

| Código | `detalle` |
|---|---|
| 422 forma | `El cambio de insumo no tiene la forma esperada: envíe tipo, indice (entero), insumo (código) y rev.` |
| 409 sin versión | `Abra una version guardada: los insumos se eligen de su lista de precios.` (borrador de un proyecto sin versiones) |
| 404 partida | como E6 |
| 422 dominio | `tipo de linea 'xx' desconocido; se espera uno de ('material', 'equipo', 'mano_obra')` · `la linea 5 no existe: el grupo material tiene 1 lineas` · `El insumo 'X' no esta en la lista de precios de la version 001 (o no es de tipo material): elijalo de la lista.` (el código se busca entre los insumos del tipo que la lista de la versión valora) |

## E8 `GET /v1/hoja/borradores/{id}/insumos?tipo=&texto=&limite=` → `InsumosHojaRespuesta`

Los insumos que se pueden elegir para una línea (`insumos_candidatos`): del `tipo` (obligatorio: `material`, `equipo`, `mano_obra`),
cuya descripción contiene `texto` (opcional, ≤ 500 caracteres; es el `ilike` de la
clásica: no ignora tildes) y que la lista de la versión valora, ordenados por descripción. `limite`: 1 a 301, por omisión 300; **301 se trata como
300** (el tope de la clásica, `LIMITE_INSUMOS`); se devuelven a lo sumo `limite` y `hay_mas` es verdadero si había más.

```
200 { "insumos": [ { "codigo": str, "descripcion": str, "unidad": str, "precio": Monto } ], "hay_mas": bool }
```

Errores: 409 sin versión abierta (`Abra una version guardada: los insumos se eligen de su lista de precios.`); 422 con `tipo`
ausente, desconocido o `limite` fuera de rango (`La búsqueda de insumos no tiene la forma esperada: indique tipo (material, equipo o mano_obra), un texto de hasta 500 caracteres y un límite de 1 a 301.`, fijo, sin eco). No lleva `rev`.

## E9 `GET /v1/hoja/borradores/{id}/cambios` → `CambiosHojaRespuesta`

```
200 { "rev": int, "cambios": [ { "objeto": str, "clave": str, "campo": str, "antes": str, "despues": str } ] }
```

La lista de `cambios_entre(versión abierta, borrador)` en el orden metraje, APU, cantidad, parámetro y plan; su longitud es
`resumen.cambios`. **Diferencia con el diseño:** el diseño dice `[Cambio]` (lista sola); se envuelve para llevar el `rev` con que se
calculó (el modal de guardar la compara con el que tiene). Los valores salen como los de la clásica (`antes`/`despues` = `valor_anterior`/`valor_nuevo`).

## E10 `GET /v1/hoja/borradores` → `BorradoresHojaRespuesta` (retomar tras recargar)

Los borradores de **mi** ficha abiertos en el caso de ahora, el usado más recientemente primero, sin los ya guardados:

```
200 { "borradores": [ { "id": str, "proyecto": str, "version": str|null, "cambios": int, "rev": int, "tocado": "AAAA-MM-DDTHH:MM:SS" } ] }
```

- Para retomar: `GET /borradores/{id}` (R3: `base`, `resumen` con el `rev` vigente) y las vistas R5 a R11 (tablas). No se necesita más.
- `proyecto` es el nombre; `version` es `null` en un borrador en blanco de un proyecto sin versiones. Ninguna fila de otra ficha aparece
  jamás. Lista vacía si no hay.
- Listar no renueva el plazo de ningún borrador.

## E11 `POST /v1/hoja/borradores` (R2) con `reemplazar` → 201 / 409 con `borrador_id`

El cuerpo de R2 gana un campo opcional: `{ "proyecto": str, "version": str|null, "reemplazar": bool = false }`.

- Si ya hay un borrador de MI ficha de esa misma `(proyecto, versión)` (el proyecto se compara por nombre; `version: null` es la
  versión «ninguna») **con cambios sin guardar** y `reemplazar` es falso: **409** y NO se abre nada ni se escribe nada:
  `{ "detalle": "Ya tiene un borrador de esta versión con {n} cambios sin guardar: retómelo o reemplácelo.", "borrador_id": "<id>" }`
  (`{n}` = 1 → «1 cambio»). `borrador_id` es el del más reciente con cambios.
- Con `reemplazar: true` se descartan los borradores de esa `(proyecto, versión)` de mi ficha y se abre uno nuevo (201, como R2). Si
  abrir falla (404 de la versión, etc.) el anterior queda intacto.
- Un borrador de la misma versión SIN cambios no estorba: se descarta en silencio y se abre el nuevo.
- **Cambiar de versión (o de proyecto) con un borrador abierto no descarta nada:** el borrador de la otra versión sigue vivo y
  aparece en E10 (tope de 4 por ficha; el más antiguo se descarta al pasar de 4, como siempre). La advertencia «Tiene {n} cambios sin
  guardar…» es de pantalla: el front la compone con `resumen.cambios`.
- Un borrador de otra ficha no cuenta (el aviso no confirma ids ajenos).

## Cierre de un MENOR heredado de 3c-2: E4 exige la matriz completa

`PUT …/plan` (E4) acepta hasta ahora una matriz con partidas desconocidas o sin las demás partidas (el plan quedaba parcial). Desde
3c-3 es **422** `plan: la matriz debe traer exactamente las partidas del presupuesto, una fila por cada una: vuelva a cargarla.`
cuando el conjunto de partidas (no vacías) de `filas` no es EXACTAMENTE el de las partidas valoradas del presupuesto (las filas de
R8). Va después de «ya hay plan», `rev` y «dos filas de la misma partida» y antes del 422 de las fracciones. Una fila con `partida`
vacía se sigue ignorando. (El diseño no contradice esto: §4.4 dice «la matriz es completa».)

## Lo que NO cambia

R1 a R14, E1 a E5 (salvo lo anterior), `ui/*`, `core/`, `asistente/`, `rutas.ts`. El guardado es 3d.
