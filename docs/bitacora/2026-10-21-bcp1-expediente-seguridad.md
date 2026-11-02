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
| 5 | Un archivo presente cuyo código ya no está vigente (p. ej. tras restaurar un respaldo anterior) no se reemite al arrancar | **resuelto el 2026-10-25 (§7):** sin cuentas se reemite; antes era residual (`asegurar_codigo` no tocaba un archivo existente) y le pasó a una persona de la empresa |
| 6 | El código del restablecimiento impreso en la consola de quien corre la orden | es la entrega del código a quien tiene el equipo; la API jamás lo imprime (lo comprueba la prueba del servidor real) |
| 7 | `python -m operacion restablecer-administrador` no tiene límite de uso | exige acceso al equipo; cada emisión invalida la anterior y queda en `evento_acceso` |

## 6. Verificación

Ver `docs/bitacora/2026-10-21-bcp1-backend-avance.md` (comandos y resultados reales de la corrida combinada).

## 7. Adenda 2026-10-25: el código rechazado a una persona de la empresa

### 7.1 Problema

Una persona de la empresa no pudo crear el primer administrador: el código de instalación que veía fue
rechazado. Causas confirmadas por lectura y reproducidas con un guion antes de tocar nada:

1. **Archivo rancio (defecto de esta rama, regresión frente a `main`).** `operacion/primer_arranque.asegurar_codigo`
   salía si `codigo_instalacion.txt` existía, sin mirar la base. Si `instalacion.db` se recreó, se borró o se
   restauró y el `.txt` quedó, el archivo (y la consola, que lo lee) mostraba un código cuya huella no está en la
   base: 401 siempre y 423 al quinto intento. Era el residual 5 de §5. En `main`, `preparar_primera_vez` emitía
   uno si no había ninguno vigente.
2. **Cifras fuera del alfabeto.** El alfabeto es base32 (`A-Z`, `2-7`); quien copia a mano escribe `0` por `O`,
   `1` por `I`, `8` por `B`. La normalización pasaba a mayúsculas y quitaba lo que no es letra o cifra, nada más.
3. **La línea entera de la consola pegada** («Código de instalación (un solo uso, …): XXXX-…», unos 97 caracteres):
   422 genérico por el tope de 64 del esquema, o 401 porque las letras del prefijo entraban en la huella.
4. El texto de la bienvenida («Son 20 letras y números») invitaba a escribir 0 y 1.

### 7.2 Cambios

- `seguridad/cuentas.py`
  - `preparar_primera_vez`, sin cuentas, emite (invalida los pendientes y reescribe el archivo) si falta el
    archivo **o si su código no es uno que la base aceptaría ahora** (`_archivo_lleva_un_codigo_vigente`: lee como
    mucho 1 KiB del archivo, calcula la huella con la misma normalización y busca una fila con `usado IS NULL` y,
    si es de restablecimiento, sin caducar). Con cuentas no toca nada, tampoco el archivo de un restablecimiento.
    Sigue tomando `_tomar_escritura` antes de mirar: el lanzador y el gancho `lifespan` no se pisan y la segunda
    llamada encuentra el archivo bueno (idempotente). El texto leído no se registra ni sale de la función.
  - `normalizar_codigo` (única normalización; la usa `_huella_codigo`): mayúsculas; `0→O`, `1→I`, `8→B`; si el texto
    trae **un único** grupo de cinco bloques de cuatro (separados por guion, también los guiones tipográficos,
    o por espacios), se usa ese grupo; si trae dos, no se adivina y se usa todo; al final, solo letras y cifras.
    No se traducen `l`/`L` (la `L` es letra del alfabeto) ni el `9` (no se parece a ninguna letra que falte).
  - `_caducado` sale de `reclamar_instalacion` para que el reclamo y la comprobación del archivo digan lo mismo.
- `operacion/primer_arranque.py`: `asegurar_codigo` ya no sale por el archivo; delega en `preparar_primera_vez`.
- `api/esquemas_bienvenida.py`: `codigo` admite hasta 256 caracteres (antes 64). Por encima, el mismo 422 fijo sin
  eco (`RutaSinEco`).
- Interfaz: «Son 20 caracteres en grupos de cuatro …: letras de la A a la Z y cifras del 2 al 7. Cópielo y péguelo
  abajo tal cual.» (bienvenida) y lo mismo en «Recuperar el acceso».

**No cambia:** el orden de validación (forma de usuario y contraseña antes del código), el bloqueo de 5 fallos
por 15 minutos con su contador global, el freno global, los mensajes, el borrado del código en pantalla tras un
error (§3.5 del diseño), la caducidad de 24 h del restablecimiento, ni que el código no se registre ni se
devuelva.

### 7.3 Por qué no debilita la seguridad

- **El espacio de códigos no cambia:** se siguen emitiendo 20 caracteres de `secrets.choice` sobre 32 símbolos
  (2^100). Las cifras traducidas (`0`, `1`, `8`) **no pueden aparecer** en un código emitido, así que ninguna
  huella guardada cambia (lo comprueba `test_la_huella_de_un_codigo_emitido_no_cambia` con un `hashlib` a mano).
- **Cada intento sigue comparando una sola huella.** La normalización es una función de lo enviado a un texto; no
  prueba variantes. Que más escrituras distintas lleven al mismo código no da más intentos: quien ataca tiene que
  adivinar los 100 bits igual, con 5 fallos por 15 minutos y el freno global, y solo desde el equipo propio.
- **Todo lo que antes se aceptaba se sigue aceptando con la misma huella.** Si lo enviado tenía exactamente las 20
  letras y cifras del código, el único grupo posible son esas mismas 20, y las traducciones no tocan letras.
- **Un código errado sigue dando el mismo 401 y cuenta** para el bloqueo (`_rechazar_codigo` no cambió).
- **La reemisión no abre un camino nuevo:** solo ocurre al arrancar (lanzador o `lifespan`, nunca en una petición)
  y solo sin cuentas, igual que la emisión de siempre; invalida los pendientes, como ya hacía `emitir_codigo`.
- El tope de 256 sigue acotando el cuerpo y el costo de la expresión regular: cada bloque es de largo fijo y los
  separadores no son letras ni cifras, así que no hay retroceso explosivo; medido con entradas malas de 256
  caracteres (solo espacios, guiones sueltos, bloques repetidos, letras no ASCII), menos de 0,2 ms por llamada.

### 7.4 Pruebas (rojo visto y luego verde)

- `tests/unit/test_aplicacion_primer_arranque.py`: archivo que la base no conoce → se reemplaza y el nuevo sirve;
  `instalacion.db` recreada con el `.txt` viejo → se reemite y el viejo da error; base restaurada con otro vigente →
  queda uno; archivo ilegible o vacío → se reemplaza; restablecimiento caducado sin cuentas → se reemplaza; archivo
  anotado a mano con el código vigente → no se toca; con cuentas, ni el archivo del restablecimiento ni uno ajeno se
  tocan. La prueba anterior «con un archivo ajeno no lo toca» (sin cuentas) **cambia de sentido**: era el defecto.
- `tests/unit/test_cuentas_codigo_tolerante.py` (nuevo): 0/1/8 por O/I/B, minúsculas, espacios, guion largo, la línea
  entera de la consola (con `\r\n`, con una nota, con palabras de cuatro letras alrededor) → aceptados; `L` y `9` no se
  traducen, un carácter cambiado, dos grupos o diez bloques → el mismo `ErrorDeAcceso` y el contador sube 1; cinco
  variantes erradas bloquean igual; el código de restablecimiento se lee igual, es de un solo uso y caduca igual;
  nada de lo escrito queda en `evento_acceso`.
- `tests/unit/test_api_primer_arranque.py`: por HTTP, cifras y línea entera → 201; 256 caracteres errados → 401 fijo
  sin eco y un fallo contado; 257 → 422 fijo sin eco (antes el caso era 65).
- `tests/unit/test_api_lifespan_primer_arranque.py`: arrancar la API con el código del archivo borrado de la base lo
  reemite, y arrancar otra vez no cambia nada.
- Front: `Bienvenida.test.tsx` y `RecuperarAcceso.test.tsx` comprueban el texto nuevo y que ya no dice «letras y números».

- **Robustez (observaciones del árbitro, 2026-10-25):** `emitir_codigo` escribe `codigo_instalacion.txt` de forma atómica (temporal en la misma carpeta + `os.replace`) con el bloqueo de escritura tomado y **antes** del `commit`; si escribir falla, `rollback` y base y archivo no divergen (dos arranques a la vez ya no dejan un archivo con un código invalidado). El lanzador lee el archivo con `leer_archivo_del_codigo` (1 KiB como mucho, `errors="replace"`; el mismo lugar que usa `_archivo_lleva_un_codigo_vigente`). Pruebas en `test_aplicacion_primer_arranque.py` y `test_lanzador.py`.

### 7.5 Residuales

| # | Riesgo | Estado |
|---|---|---|
| 8 | Si la persona ya llegó al 423 con el código rancio, el código nuevo también espera los 15 minutos (el contador es global y la reemisión no lo reinicia) | aceptado: no se toca el freno (pedido expreso); la pantalla ya dice que espere 15 minutos |
| 9 | Un código escrito solo con espacios y pegado detrás de otra palabra de cuatro letras («CODE ABCD EFGH …»): la racha tiene seis bloques y no se adivina cuál sobra | da el 401 de siempre (no se acepta nada que antes no se aceptara salvo lo de §7.2); con guiones, o con el prefijo de la consola, sí se encuentra |
