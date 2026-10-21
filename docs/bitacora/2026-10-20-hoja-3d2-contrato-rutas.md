# Hoja 3d-2: contrato de S2 a S6, versiones nuevas desde una guardada y la cadena (para el agente de front)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `6a7f6af1` · **Fuente:** diseño §4.5 (S2 a S6), §6.3 (fila 3d-2),
§4.1, §4.7 y §9 (P24, P31 a P33, P35). Se escribió ANTES de implementar. Si la implementación difiere, la bitácora de avance
(`2026-10-20-hoja-3d2-backend-avance.md`) lo dice; la fuente final es `docs/api.json`.

## Qué son

Las cuatro operaciones que la página clásica ofrece sobre una versión **guardada** y que crean otra versión (`ui/paginas/hoja.py`:
`_restaurar`, el formulario «Registrar una cotizacion», «Retirar una cotizacion» y `_moneda`), más la lectura de la cadena de sellos.
**No usan borrador:** actúan sobre el `proyecto` y la `version` que dice el cuerpo, en el caso de la ficha en ese momento. Cada una
devuelve el código de la versión nueva; el front la abre con R2 (`POST /borradores {proyecto, version}`). El front impide la acción con
cambios sin guardar (P:1946, 2081, 2201: es una regla de pantalla); el servidor no conoce los borradores de otra ficha y no la exige.

## Reglas comunes a S2 a S5 (iguales a S1 salvo lo dicho)

* Cookie de sesión `silice_sesion`, `X-Silice-CSRF` (el de la ficha) y `Origin` propio. **Solo con cuenta:** con `X-Silice-Clave`, 403
  `La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve.`
* Rol: S2, S3 y S4 `EDITAR_HOJA` (`arma`); **S5 `CONVERTIR_Y_REAJUSTAR`** (también `arma`; la matriz de `seguridad/permisos.py` es la única fuente).
  `rita` (revisa), `admin` y `tomas` (clave temporal): 403 `Su cuenta no tiene permiso para esta acción.`
* `Cache-Control: no-store` también en los errores propios de la ruta (el 413 es del middleware y no lo lleva).
* El responsable es SIEMPRE la persona de la sesión (`Nombre <login>`, RF-82): el cuerpo **no** trae `responsable` (`extra` prohibido).
* **Una sola transacción que empieza con `BEGIN IMMEDIATE`** (como S1): el código de la versión nueva (`siguiente_codigo`) se lee con el
  bloqueo de escritura ya tomado. Dos personas a la vez obtienen códigos distintos (nunca dos iguales); no hay «versión más nueva» que
  confirmar (crear la nueva vigente es justo el objeto de estas operaciones). Sesión envuelta en `con_anexos_de_cadena`: la cadena
  queda íntegra tras cada una. Todo o nada: ante cualquier error posterior a la validación, ninguna fila nueva.
* No hay borrador, así que no hay `rev` ni 409 «el caso cambió desde que abrió este borrador»: la operación actúa sobre el caso de la
  ficha **de ese momento** (si se cambió de caso, sobre el nuevo; si ahí no existe el proyecto, 404). Nunca escribe en dos bases.
* Montos: no hay montos en estas respuestas (el total de la versión nueva se lee con R2 al abrirla). Sin `float`.
* `proyecto` es el código de `/v1/proyectos` o el nombre (`resolver_proyecto`). `version` es el código de la versión de partida.

### Errores, en este orden de precedencia (S2 a S5)

| Código | Cuándo | `detalle` |
|---|---|---|
| 401 / 403 | sin sesión; rol (`rita`, `admin`, `tomas`); clave de API; CSRF; `Origin` | los de S1 |
| 422 | FORMA del cuerpo: campo ausente o de otro tipo, texto más largo que su tope, campo desconocido, `lado` fuera de `venta`/`compra`, `fecha` que no es una fecha `AAAA-MM-DD` real | FIJO por ruta, sin repetir lo enviado (abajo) |
| 404 | el proyecto no existe en este caso | `El proyecto «{proyecto}» no existe en este caso.` (como R1, R12 y R14) |
| 404 | el proyecto no tiene esa versión | `El proyecto '{P}' no tiene una version '{C}': elija una de la lista.` (H:1572; la clásica lo ofrecía en un selector) |
| 422 | un dato de dominio inválido (`HojaInvalida`): el texto del núcleo, **tal cual lo da la clásica y sin prefijo** | ver tabla por ruta; el front puede anteponer «No se guardó nada: » como P:1985 |
| 409 | `CatalogoIncompleto` del núcleo (no es un error de dato: falta una composición) | `No se guardó nada: {mensaje}` |
| 503 | la base no se pudo leer o escribir (incluido un cerrojo que SQLite no concede en 5 s) | `No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.` (sin SQL ni rutas) |
| 500 | una excepción inesperada: se deshace todo y FastAPI responde su 500 genérico | `Internal Server Error` (no es contrato: solo garantiza que no queda nada escrito) |
| 413 | cuerpo > 20 MiB | `El cuerpo de la peticion excede el maximo de 20 MiB.` |

Todos los 422 de dominio llevan el texto de `aplicacion.hoja` (idéntico al de `ui.hoja`: la prueba de paridad compara cadena a cadena).

## S2 `POST /v1/hoja/versiones/restaurar`

Restaurar una versión anterior (RF-54): crea una versión nueva, copia de `version`, que pasa a ser la vigente. Nada se borra; su espacio
es el de la restaurada (no copia filas `esp_*`).

```
{ "proyecto": str (1..500), "version": str (1..500), "fuente": str (0..300) }       # extra prohibido
```

**200** `{ "codigo": "003", "proyecto": "<nombre>", "mensaje": "La versión 001 se restauró como la versión 003 (la vigente)." }`

422 FORMA: `La restauración no tiene la forma esperada: envíe proyecto, version y la fuente como texto de hasta 300 caracteres.`
422 de dominio: fuente vacía o en blanco → `la fuente del cambio es obligatoria: diga por que y con que respaldo`.
(La fuente vacía es un 422 de dominio, no de forma, como en la clásica: se escribe el motivo y el servidor lo juzga.)

## S3 `POST /v1/hoja/versiones/cotizar`

Cotizar un insumo para el proyecto (RF-56): crea la versión nueva, que referencia la lista del proyecto y conserva el plan y la curva.
Solo cambia ese insumo en ese proyecto; las demás cotizaciones se conservan; una previa del mismo insumo se reemplaza.

```
{ "proyecto": str, "version": str,
  "insumo": str (1..500),            # el CÓDIGO del insumo (el que da GET /v1/hoja/precios)
  "precio": str (0..500),            # decimal en texto, solo punto decimal; NUNCA número
  "proveedor": str (0..120), "numero": str (0..60),
  "fecha": "AAAA-MM-DD",             # la fecha de la cotización (cualquiera, como el selector de fecha de la clásica)
  "evidencia": str|null (0..90) }    # opcional: archivo, enlace o nota; null y ausente valen lo mismo
```

Los topes de `proveedor` (120) y `numero` (60) son el ancho de las columnas de `cotizacion`; el de `evidencia` (90) hace que la fuente
que arma el núcleo (`Cotizacion {numero} de {proveedor} ({fecha}). {evidencia}`, ≤ 300 como `RegistroCambio.fuente`) no se pase de 300
(SUPUESTO declarado, D-9).

**200** `{ "codigo": "002", "proyecto": "<nombre>", "mensaje": "Se guardó la versión 002 con la cotización de MAT-001." }` (el código del insumo es el recibido).

422 FORMA: `La cotización no tiene la forma esperada: envíe proyecto, version, insumo, precio (texto), proveedor, numero, fecha (AAAA-MM-DD) y, si quiere, la evidencia; cada texto con su tope.`
422 de dominio (el texto de la clásica, en el orden en que el núcleo los juzga; el precio se juzga primero):
`precio: '{x}' no es un numero decimal valido` · `precio: '{x}' no es un monto finito` · `el proveedor de la cotizacion es obligatorio` ·
`el numero de la cotizacion es obligatorio` · `la fuente del cambio es obligatoria…` (no ocurre: el núcleo la arma con proveedor y número) ·
`el precio cotizado debe ser un Decimal no negativo, no …` · `no hay ningun insumo con codigo '{c}'` · `la version '{v}' no usa el insumo {c}` ·
`el insumo {c} ya vale {p} en la lista de la version`.

## S4 `POST /v1/hoja/versiones/retirar-cotizacion`

Retirar la cotización de un insumo (con su registro): la versión nueva vuelve al precio de la lista base para ese insumo y conserva las
demás cotizaciones.

```
{ "proyecto": str, "version": str, "insumo": str (1..500), "motivo": str (0..300) }
```

**200** `{ "codigo": "003", "proyecto": "<nombre>", "mensaje": "Se guardó la versión 003 sin la cotización." }`

422 FORMA: `El retiro no tiene la forma esperada: envíe proyecto, version, insumo (código) y el motivo como texto de hasta 300 caracteres.`
422 de dominio: motivo en blanco → `la fuente del cambio es obligatoria: diga por que y con que respaldo`; `no hay ningun insumo con codigo '{c}'`;
`la version '{v}' no tiene cotizacion del insumo {c}`.

## S5 `POST /v1/hoja/versiones/convertir`

Cambiar la moneda del proyecto (RF-64): crea una versión convertida con la tasa del BCV aplicable a **hoy** (la fecha la pone el
servidor; la tasa de los 7 días anteriores como máximo, S1-R1 y S1-R2). La actual no cambia. Acceso `CONVERTIR_Y_REAJUSTAR`.

```
{ "proyecto": str, "version": str,
  "moneda": str (1..20),                # "Bs" o "USD"; cualquier otro valor lo juzga el núcleo (422 de dominio)
  "lado": "venta" | "compra",           # la tasa del BCV; la clásica ofrece venta por omisión
  "fuente": str (0..300) }              # por qué se cambia la moneda
```

**200** `{ "codigo": "002", "proyecto": "<nombre>", "mensaje": "Se guardó la versión 002, convertida a Bs." }`

422 FORMA: `La conversión no tiene la forma esperada: envíe proyecto, version, moneda, lado (venta o compra) y la fuente como texto de hasta 300 caracteres.`
422 de dominio: **todo `ValueError` del núcleo va con el prefijo `No se convirtio nada: `** (como la clásica): sin tasa en los 7 días
(`No se convirtio nada: …`, el motivo de `TasaNoDisponible`), `No se convirtio nada: moneda 'EUR'; se espera Bs o USD (UC-17 4b)`,
`No se convirtio nada: la version 001 ya esta en USD`, `No se convirtio nada: la fuente del cambio es obligatoria: …`. No se escribe nada.

## S6 `GET /v1/hoja/cadena?proyecto=`

El estado de integridad de la cadena de sellos del proyecto (RF-83, `aplicacion.entrega.estado_de_la_cadena`): recalcula cada huella.
**Clave de API o sesión con `EDITAR_HOJA`**; solo lee (sesión común, sin `BEGIN IMMEDIATE`). `no-store`.

**200** `{ "integra": bool, "mensaje": str, "declaracion": str|null }`: `mensaje` es el de `core.budget.cadena.mensaje_de_cadena` (íntegra:
«La cadena de N versiones está íntegra…»; rota: «Cadena rota en la versión 002: …»); `declaracion` es el texto de selladas
retroactivamente («Versiones 001 a 004 selladas el …») o `null`.

404 `El proyecto «{proyecto}» no existe en este caso.` · 422 `proyecto` ausente o de más de 500 caracteres (FIJO: `Indique el proyecto
(código o nombre) de hasta 500 caracteres.`) · 503 el fijo de arriba.

## Diferencias deliberadas con la clásica (para el árbitro y para Eugenio)

* **404 para proyecto o versión inexistentes.** La clásica los elegía de un selector (no podía fallar); la API los resuelve y dice cuál falta.
* **Errores sin prefijo ni sufijo** (salvo S5, cuyo prefijo viene del propio `convertir`): la clásica componía `{error}. No se guardo nada.`
  (P:1985, 2005) y `No se restauro nada: {error}` (P:2151). El texto del núcleo va en `detalle` tal cual; el front compone el resto.
* **Sin `error.orig`:** un error de la base es el 503 fijo (C1). La clásica lo mostraba (P:216-221, 2151).
* **`CatalogoIncompleto` es 409 `No se guardó nada: …`:** en la clásica no se capturaba (la pantalla se caía).
* **Mensajes de éxito con tildes** («restauró», «guardó», «versión», «cotización»); los compone el servidor, una sola copia.
* **`fuente`, `motivo`, `proveedor`, `numero` y `evidencia` llevan tope** (300 / 300 / 120 / 60 / 90): la clásica no acotaba; SUPUESTO D-9.
* **S5 pide `CONVERTIR_Y_REAJUSTAR`** (la matriz); la clásica corría bajo `EDITAR_HOJA` de la página (hallazgo 5 del diseño). Hoy ambas son solo `arma`.
* **Respuesta con `proyecto`** además de `codigo` y `mensaje` (el diseño decía `{codigo, mensaje}`): es el nombre canónico que R2 acepta.
* **Carrera:** la clásica podía repetir el código si dos personas guardaban a la vez (violación de unicidad); la API serializa con `BEGIN IMMEDIATE`.

## Lo que NO cambia

R1 a R14, E1 a E11, S1, `ui/*`, `core/`, `asistente/`, `aplicacion/hoja.py`, `rutas.ts`. Excel y planos son 3e.
