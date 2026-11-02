# BCP-1 · contrato exacto de las rutas del primer arranque (P0 y P1)

Fecha: 2026-10-21 · Rama `inc/ruta-s2-mig-adm-empresa` · Implementador backend. Fuente: diseño
`docs/especificaciones/2026-10-21-bienvenida-casos-proyectos-design.md` (§3, §9, §16). Este archivo es lo que
lee el agente del front (BCP-4). Si el código se desvía, se anota al final en «Desviaciones».

Ambas rutas son **públicas** (sin clave de API ni cookie), **solo para el propio equipo**
(`aplicacion.equipo.ip_es_local(request.client.host)`; desde otra IP, 403) y todas sus respuestas, éxitos y
errores, llevan `Cache-Control: no-store`. No pertenecen a `exigir_clave_o_sesion`.

Todo error es `{"detalle": "<texto fijo>"}`. Ningún texto repite lo enviado.

## P0 · `GET /v1/primer-arranque`

| Estado | Cuerpo | Cuándo |
|---|---|---|
| 200 | `{"sin_cuentas": bool, "archivo_presente": bool, "modo": "producto" \| "desarrollo", "politica": {"minimo": 10, "maximo": 128}}` | siempre que se pida desde el propio equipo |
| 403 | `{"detalle": "Esta operación solo puede hacerse desde el propio equipo donde corre Sílice, no desde la red."}` | cliente remoto |
| 503 | `{"detalle": <texto de la base>}` | la base de la instalación no abre |

- Claves **exactas** y solo esas. Sin nombres de usuario, sin rutas, sin el código ni su huella, sin cantidad de cuentas.
- `politica.minimo` y `politica.maximo` salen de `seguridad.cuentas.MINIMO_CONTRASENA` y `MAXIMO_CONTRASENA`.
- `archivo_presente`: existe `codigo_instalacion.txt` en la carpeta de datos.
- `modo`: `producto` si es la instalación del instalador; `desarrollo` si no.
- El `GET` **nunca escribe** (el código se emite al arrancar, no al pedir esta ruta).

## P1 · `POST /v1/primer-arranque/reclamo`

Cuerpo JSON:

```json
{ "codigo": "str ≤ 64", "usuario": "str ≤ 120", "nombre": "str ≤ 120",
  "contrasena": "str ≤ 128", "tambien_arma": false }
```

(`tambien_arma` es opcional, por omisión `false`. No hay campo `repetida`: las dos contraseñas se comparan en el cliente.)

Orden de las comprobaciones (cada una antes de la siguiente; ninguna escribe hasta el reclamo):

1. **`Origin` presente y propio** (`http://<Host>`), si no 403 `La petición no viene de la interfaz de esta instalación.`
   A diferencia de `POST /v1/sesion`, aquí **la ausencia de `Origin` también es 403**.
2. **Propio equipo**: si no, 403 con el texto de P0.
   (1 y 2 son una dependencia de la ruta: corren **antes** de leer el cuerpo, así que un cuerpo inválido o un JSON roto
   desde fuera da 403 y nunca 422.)
3. **Forma del cuerpo**: tipo o longitud inválidos, falta un campo obligatorio → 422
   `Escriba el código, el usuario, el nombre y la contraseña como texto (la contraseña admite hasta 128 caracteres).`
4. **Forma de usuario y contraseña, ANTES de mirar el código**: 422 con el texto de política de `seguridad.cuentas`:
   - `El usuario son 3 a 40 caracteres: letras, números, punto o guion.`
   - `La contraseña debe tener al menos 10 caracteres.` / `La contraseña admite hasta 128 caracteres.` /
     `La contraseña no puede ser igual al usuario.` / `Esa contraseña es demasiado común; elija otra.`
   Un código bueno y uno malo con datos mal formados responden exactamente igual.
5. **El reclamo** (`seguridad.cuentas.reclamar_instalacion`, con el mismo freno global y el bloqueo de 5 fallos que el acceso):
   - 429 `Demasiados intentos fallidos en este equipo. Espere unos segundos y vuelva a probar.` con cabecera `Retry-After: <s>` (≥ 1).
   - 423 `Demasiados intentos fallidos. Espere 15 minutos o pida al administrador que desbloquee la cuenta.`
     (el quinto fallo seguido ya da 423; mientras dura, también el código correcto)
   - 401 `El código de instalación no es válido o ya se usó.` (código errado, ya usado, **caducado**, o sin nada que reclamar:
     el mismo texto con cuentas ya creadas y sin código de restablecimiento; no revela si hay cuentas)
   - 503 `La base está ocupada; reintente en unos segundos.` (otra escritura de la instalación no terminó) o el texto de la base.
6. **Éxito**: **201**, cuerpo `SesionRespuesta` (el mismo de `POST /v1/sesion`):
   `{login, nombre, roles, csrf, debe_cambiar_clave, acciones, modo_entrega}` y la cookie `silice_sesion` (`HttpOnly`,
   `SameSite=Strict`). `roles` = `["administrador"]`, o `["arma", "administrador"]` si `tambien_arma` (orden de `Rol`).
   El front guarda `csrf` con `fijarCsrf` como tras entrar. Si el navegador traía una ficha, se cierra.

El **código** (ni la contraseña) no vuelve en ninguna respuesta, no se escribe en el registro ni en `evento_acceso` y no
se imprime en la salida estándar. Con un código de restablecimiento sobre un usuario existente, ese usuario recupera
el acceso y gana el rol administrador (D-6); las cuentas ajenas no cambian.

## Qué emite el código y cuándo (para el texto de la bienvenida)

- Al arrancar Sílice (lanzador) y al arrancar la API (`lifespan`), si **no hay cuentas** y **no existe** `codigo_instalacion.txt`,
  se emite un código nuevo (invalida los anteriores) y se escribe el archivo. Idempotente.
- En el producto instalado el lanzador abre el archivo con el Bloc de notas la primera vez.
- Código de restablecimiento (`python -m operacion restablecer-administrador`): caduca **a las 24 horas** (a las 24:00 exactas
  ya no sirve); emitir uno invalida los pendientes anteriores.

## Desviaciones respecto del diseño

1. **Texto del 503 por la base de la instalación (`ErrorDeBase`)**: no se devuelve el texto de la base (puede traer rutas del servidor); es fijo:
   `No se pudo abrir la base de la instalación: avise al administrador del equipo.` El 503 por una escritura ajena que no termina sigue siendo
   `La base está ocupada; reintente en unos segundos.` (corrige la línea «o el texto de la base» de P0 y P1).
2. **La puerta (`Origin` y propio equipo) no es una dependencia de FastAPI sino un paso de la clase de ruta que corre antes de leer el cuerpo.**
   Es más fuerte que lo pedido: FastAPI lee el JSON antes de resolver las dependencias, así que con una dependencia un JSON roto desde fuera daba 422
   en lugar de 403. Resultado visible: cualquier cuerpo (vacío, roto, inválido) sin `Origin` propio o desde otra IP es 403; el `Origin` se mira antes que el equipo.
3. Cuerpo: `tambien_arma` es booleano estricto (`"si"` no se convierte) y todos los textos son estrictos (un número en `contrasena` es 422, no se pasa a texto).
4. El 422 de forma del cuerpo también cubre una contraseña de 129 o más caracteres: lleva el texto fijo del punto 3 (que dice «hasta 128»), no el de la política.
5. El restablecimiento sobre una cuenta ya existente deja un evento `cambio de roles` con «promovida a administrador por restablecimiento» (sin el código).

