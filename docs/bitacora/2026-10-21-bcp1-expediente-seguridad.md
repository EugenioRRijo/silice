# BCP-1 · expediente de seguridad: el reclamo del código de instalación (`seguridad/cuentas.py`)

Fecha: 2026-10-21 · Rama `inc/ruta-s2-mig-adm-empresa` · Base `82c0bab6`. NORMAS.md §9 y el diseño
`docs/especificaciones/2026-10-21-bienvenida-casos-proyectos-design.md` (H3, §3.3, §16 hallazgos 1 y 2).
**Aval:** Eugenio delegó y declaró que el tutor avala el cambio (sin acta). Lo juzga el árbitro.

## 1. Problema

`reclamar_instalacion` canjea un código de un solo uso por una cuenta de administrador. Antes de
este cambio leía `pendiente.usado` y `hay_usuarios` **sin tomar el bloqueo de escritura** (pysqlite no abre
una transacción en un `SELECT`) y marcaba `pendiente.usado = ahora` sin condición. Dos reclamos
simultáneos con logins distintos pasaban los dos la comprobación y creaban **dos administradores con un
solo código**. Hasta BCP-1 nadie lo podía provocar (la ruta no existía; la clásica era de una sola sesión);
con `POST /v1/primer-arranque/reclamo` es alcanzable por HTTP.

Además, tres huecos de la misma familia en el ciclo de vida del código:

- emitir un código no invalidaba los pendientes anteriores (varios códigos vivos a la vez);
- el código de restablecimiento no caducaba: un archivo olvidado valía para siempre;
- con un código vigente en la base y el archivo borrado, `preparar_primera_vez` devolvía `None` y nadie
  reescribía el archivo: la instalación quedaba sin forma de entrar.

## 2. Reproducción (pruebas `tests/unit/test_cuentas_carrera_reclamo.py`)

Dos hilos con barrera, cada uno con su sesión y su conexión a la misma `instalacion.db`, mismo código,
`Argon2` real. Sobre la base `82c0bab6` (sin el arreglo), tres corridas consecutivas:

| Escenario | Resultado sin el arreglo (3/3 corridas) |
|---|---|
| (a) con una fila previa en `intento_acceso` (un fallo anterior), logins `uno` y `dos` | **dos `ok`: dos administradores** con un solo código |
| (b) sin fila previa, logins distintos | `IntegrityError` (`UNIQUE intento_acceso.login_normalizado`): en la API, un **500** |
| (c) mismo login, con fila previa | `IntegrityError` (`UNIQUE usuario.login`): un 500 |
| (c) mismo login, sin fila previa | `IntegrityError` (`intento_acceso`): un 500 |
| defensa extra, con `_tomar_escritura` apagado | dos `ok` |

Con el bloqueo de escritura (`_tomar_escritura`, primer commit del arreglo) los cuatro primeros pasan 3/3
y solo la defensa extra queda en rojo, como se esperaba; con el `UPDATE` condicional pasan los cinco.
Por la API (`tests/unit/test_api_primer_arranque.py`, hilos con `TestClient`): `[201, 401]` y una sola
fila en `usuario`, con y sin fila previa.

## 3. Opciones

| Opción | Qué hace | Por qué sí / no |
|---|---|---|
| A. `_tomar_escritura` antes de leer | `BEGIN IMMEDIATE`: el segundo reclamo espera (`busy_timeout` de 5 s) y, al entrar, ve `usado` fijado | **Elegida.** Es el remedio que ya usan `cambiar_roles` y `desactivar` en el mismo archivo; sirve entre procesos (API, lanzador, orden `restablecer-administrador`) |
| B. Solo `UPDATE ... WHERE usado IS NULL` con `rowcount == 1` | atómico en la fila del código | **Elegida como defensa extra**, no sola: sin A la carrera (b) seguiría dando `IntegrityError` en el contador y habría trabajo (hash, filas) tirado |
| C. Cerrojo de proceso (`threading.Lock`) en la ruta | serializa dentro de un proceso | Descartada: no cubre al lanzador ni a la orden, y deja la corrección fuera de `seguridad/` |
| D. Constraint único en la base | p. ej. un índice parcial | Descartada: exige una migración de la base de la instalación; A + B no la necesitan |

Elegido: **A + B**. El `UPDATE` va **antes** de crear o tocar la cuenta, de modo que una carrera perdida no
inserta nada (y si ocurriera, `rollback` y se trata como un código usado: cuenta el fallo y devuelve el
mismo 401).

## 4. Cambios en `seguridad/cuentas.py` (y por qué)

1. `reclamar_instalacion`: `_tomar_escritura` tras la espera del freno y antes de `_intento`; `UPDATE` atómico
   del código con `rowcount == 1` (si no, `rollback` y `ErrorDeAcceso(MENSAJE_CODIGO)` contado como fallo);
   `ValueError(MENSAJE_BASE_OCUPADA)` si el bloqueo vence (la ruta responde 503); si la forma de usuario o
   contraseña es mala, `rollback` (se suelta el bloqueo y no se gasta el código).
2. `emitir_codigo`: toma el bloqueo y **invalida los pendientes** (`usado = ahora`; el evento dice
   «reemplaza N pendiente(s)»). El archivo siempre lleva el último.
3. `preparar_primera_vez`: toma el bloqueo; sin cuentas emite si no hay código vigente **o si falta el
   archivo**; suelta el bloqueo si no escribe.
4. `emitir_codigo_de_restablecimiento`: toma el bloqueo antes de cerrar las sesiones de los administradores.
5. Caducidad: el código de **restablecimiento** sirve mientras `ahora - creado < 24 h` (a las 24:00 exactas
   ya no); el de la primera vez no caduca. Un código caducado es un código inválido (mismo 401, cuenta como fallo).
6. `ademas_arma` (D-2): solo para una cuenta **nueva**, da `arma,administrador`. No cambia nada más en un
   restablecimiento.
7. Evento de promoción: cuando el restablecimiento le agrega el rol administrador a una cuenta existente
   que no lo tenía, se registra un evento `cambio de roles` con «promovida a administrador por
   restablecimiento» (tipo ya existente: no cambia el catálogo de tipos ni la base). Sin el código.

No cambia: las constantes (5 fallos, 15 min, freno de 20 fallos en 10 min, 10 a 128 caracteres), el contador
**global** del código, la política de contraseñas, ni D-6 (el restablecimiento sigue reactivando y promoviendo
a cualquier login existente; ahora con caducidad, invalidación y rastro).

## 5. Riesgos y residuales

| # | Riesgo | Estado |
|---|---|---|
| 1 | El bloqueo de escritura se mantiene mientras se calcula el hash Argon2 (~0,1 s, hasta 64 MiB) | aceptado: es un reclamo en la vida de una instalación; el segundo espera hasta 5 s y, si vence, 503 «reintente» |
| 2 | Una escritura ajena que no termina deja al reclamo en 503 | es el comportamiento pedido (`MENSAJE_BASE_OCUPADA`); el código no se gasta |
| 3 | Un atacante local gasta los 5 intentos y bloquea 15 minutos el reclamo de todos (contador global) | heredado, aceptado en el diseño (R-B4); `restablecer-administrador` emite otro código |
| 4 | El archivo `codigo_instalacion.txt` en desarrollo cae en `data/`, dentro de OneDrive en este equipo, y se sincroniza | residual: es de un solo uso y se borra al canjearse; en el producto vive en `%LOCALAPPDATA%\Silice\datos` (por usuario de Windows, no sincronizada). `data/codigo_instalacion.txt` está en `.gitignore`. Endurecer ACL queda fuera (R-B5) |
| 5 | Un archivo presente cuyo código ya no está vigente (p. ej. tras restaurar un respaldo anterior) no se reemite al arrancar | residual: `asegurar_codigo` no toca un archivo existente (regla del diseño §3.1); el remedio es `restablecer-administrador` |
| 6 | El código del restablecimiento impreso en la consola de quien corre la orden | es la entrega del código a quien tiene el equipo; la API jamás lo imprime (lo comprueba la prueba del servidor real) |
| 7 | `python -m operacion restablecer-administrador` no tiene límite de uso | exige acceso al equipo; cada emisión invalida la anterior y queda en `evento_acceso` |

## 6. Verificación

Ver `docs/bitacora/2026-10-21-bcp1-backend-avance.md` (comandos y resultados reales de la corrida combinada).
