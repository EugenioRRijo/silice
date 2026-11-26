# Registro con código de 20 caracteres (C9)

**Fecha:** 2026-11-26. **Estado:** diseño técnico de la fila C9 de
[plan-integracion-cara](../planes/2026-11-26-plan-integracion-cara.md), para construir con TDD y revisión de seguridad.

**Decisión de Eugenio (2026-11-26):** «creo que sera mejor que se registrara con su nombre y contraseña y al correo le
llegue un codigo de 20 letras para que se convierta en constructor o revisor, creo que el flujo es mas sano asi».

## 1. El flujo

1. **En la pantalla de entrada**, «Crear una cuenta» abre un formulario: nombre, correo, usuario y contraseña (con las
   mismas reglas de hoy, `validar_login` y `validar_contrasena`). Al enviarlo, Sílice guarda una **solicitud**, no una
   cuenta, y responde: «Su solicitud quedó registrada. Cuando el administrador la apruebe, le llegará un código de 20
   caracteres a su correo. Escríbalo en “Tengo un código”.»
2. **El administrador**, en Cuenta › Cuentas y permisos, ve la sección «Solicitudes» (nombre, usuario, correo y
   fecha). Por cada una elige el papel (**Arma presupuestos** o **Revisa**) y pulsa «Aprobar y generar el código», o
   «Rechazar».
3. **Sílice genera el código** (5 grupos de 4, un solo uso, vence en 7 días; se guarda solo su SHA-256) y lo muestra
   **una sola vez** al administrador, con «Copiar» y «Enviarlo por correo».
   - C9a: «Enviarlo por correo» abre el programa de correo del equipo con un `mailto:` ya escrito (destinatario, asunto
     y el código en el cuerpo). Sílice no sale a la red.
   - C9b (después): envío directo con el SMTP de la empresa en Cuenta › Empresa. Queda fuera de C9a; ver §5.
4. **La persona**, en la pantalla de entrada, pulsa «Tengo un código» y escribe su usuario, su contraseña y el código.
   Si los tres valen, Sílice crea la cuenta con el papel elegido, marca la solicitud como usada y abre la sesión.
5. **El ascenso a administrador** sigue como hoy: solo un administrador, desde Cuentas y permisos (`cambiar_roles`).

## 2. Por qué una solicitud y no una cuenta sin papel

`texto_de_roles` exige al menos un papel («una cuenta necesita al menos un rol») y toda la matriz de permisos supone
que quien tiene sesión tiene papel. Una cuenta sin papel sería un estado nuevo que cada pantalla tendría que
contemplar. Con una tabla aparte, la persona **no tiene cuenta ni sesión** hasta canjear el código. El estado ilegal
(una sesión sin papel) no se puede escribir.

## 3. Datos (migración `ins_0013_solicitud_cuenta`)

Tabla `solicitud_cuenta`:

| Columna | Tipo | Nota |
|---|---|---|
| `id` | int, clave | |
| `login` | str(60), único | normalizado; también se exige que no exista en `usuario` |
| `nombre` | str(120) | |
| `correo` | str(254) | validado por forma (una `@`, dominio con punto); no se verifica hasta canjear el código |
| `huella_clave` | str(200) | Argon2, como `usuario.huella_clave`; la contraseña nunca se guarda |
| `creada` | datetime | |
| `estado` | str(12) | `pendiente`, `aprobada`, `rechazada`, `usada` o `vencida` |
| `papel` | str(20), nulo | `arma` o `revisa`, lo fija el administrador al aprobar |
| `huella_codigo` | str(64), nulo | SHA-256 del código normalizado (`normalizar_codigo`) |
| `vence` | datetime, nulo | `aprobada` + 7 días |
| `resuelta_por` | str(120) | quién aprobó o rechazó |

Columna nueva `usuario.correo` (str(254), nulo, con valor por omisión `""` para las cuentas de hoy).

## 4. Reglas de seguridad

- **El código** reutiliza `ALFABETO_CODIGO`, `LONGITUD_CODIGO`, `normalizar_codigo`, `formato_codigo` y `secrets` de
  `seguridad/cuentas.py`: 20 caracteres base32 (100 bits), en grupos de 4. *Nota para Eugenio:* el alfabeto lleva
  letras y las cifras 2 a 7, como el código de instalación. «Solo letras» sería cambiar una constante.
- **Canje:** se busca la solicitud por **login** y se exige, en este orden, estado `aprobada`, `vence` > ahora, la
  huella del código y la contraseña (Argon2). Cualquier fallo da el mismo mensaje («El usuario, la contraseña o el
  código no son válidos») y cuenta en `IntentoAcceso` y en `FRENO`, como `autenticar`. Al canjear, en una sola
  transacción con `_tomar_escritura`: se crea el `Usuario` (`creado_por` = quien aprobó) y se pasa la solicitud a
  `usada`. Un segundo canje del mismo código falla.
- **Registro abierto:** como mucho 5 solicitudes pendientes por equipo cada hora, y 50 pendientes en total. Pasado ese
  límite: «Hay demasiadas solicitudes pendientes. Pida al administrador que revise las que hay.» La solicitud no da
  ningún permiso, así que el riesgo es de ruido, no de acceso.
- **Login ocupado:** si existe en `usuario` o en una solicitud `pendiente`/`aprobada`, se responde que ya está en uso,
  sin decir cuál de las dos.
- **Eventos** (`eventos.registrar`): `solicitud`, `solicitud aprobada`, `solicitud rechazada`, `codigo canjeado`,
  `codigo rechazado`. Nunca el código ni la contraseña en el detalle.
- **Vencidas:** al listar, las aprobadas con `vence` ≤ ahora pasan a `vencida`. El administrador puede volver a aprobar
  la solicitud y genera un código nuevo; el anterior deja de valer.
- **Red:** C9a no abre ninguna salida de red. El `mailto:` lo resuelve el programa de correo del equipo.

## 5. Fuera de C9a (C9b)

El envío directo por SMTP: servidor, puerto, usuario y TLS en Cuenta › Empresa. La contraseña del SMTP se pide al
enviar, o se guarda cifrada con `seguridad/secretos.py` atada a la clave de la empresa. Necesita su propia revisión de
seguridad, porque es la primera salida de red del servidor. Mientras no exista, el `mailto:` cumple «al correo le
llegue un código» sin guardar secretos.

## 6. Contrato de la API

| Ruta | Quién | Cuerpo / respuesta |
|---|---|---|
| `POST /v1/solicitudes` | cualquiera, sin sesión | `{nombre, correo, login, contrasena}` → 201 `{mensaje}`; 409 login en uso; 422 datos; 429 límite |
| `GET /v1/solicitudes` | `administrar_cuentas` | `{solicitudes: [{id, nombre, login, correo, creada, estado, papel, vence}]}` |
| `POST /v1/solicitudes/{id}/aprobar` | `administrar_cuentas` | `{papel}` → `{codigo: "XXXX-XXXX-XXXX-XXXX-XXXX", vence, mailto}` (la única vez que viaja el código) |
| `POST /v1/solicitudes/{id}/rechazar` | `administrar_cuentas` | → `{mensaje}` |
| `POST /v1/solicitudes/canjear` | cualquiera, sin sesión | `{login, contrasena, codigo}` → abre la sesión igual que `/v1/sesion` (misma cookie y misma respuesta); 401 genérico |

Cada ruta entra en la tabla de `tests/unit/test_api_acceso_por_ruta.py`.

## 7. Pruebas (antes del código)

- `tests/unit/test_seguridad_solicitudes.py`:
  - solicitar (login ocupado en `usuario` y en una solicitud; límites);
  - aprobar (solo administrador; papel válido; código de 20 con formato; huella guardada, código no);
  - rechazar;
  - canjear (bien; código ajeno; vencido a los 7 días exactos; usado dos veces; contraseña mala; mismo mensaje en
    todos los fallos; el freno cuenta);
  - re-aprobar invalida el código anterior.
- `tests/integration/test_api_solicitudes.py`: el contrato y los permisos de cada ruta.
- Front: `sesion/CrearCuenta.test.tsx` y `sesion/TengoUnCodigo.test.tsx` por rol y nombre; la sección Solicitudes en la
  prueba de Cuentas y permisos (aprobar muestra el código una vez, «Copiar» y el enlace `mailto:`).
- Mutantes a mano sobre la comparación de `vence`, el orden de las comprobaciones del canje y el estado `usada`.
