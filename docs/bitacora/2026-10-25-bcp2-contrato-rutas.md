# BCP-2 · contrato exacto de las rutas de carpetas de trabajo (C0 a C3)

Fecha: 2026-10-25 · Rama `inc/ruta-s2-mig-adm-empresa` · Implementador backend. Fuente: diseño
`docs/especificaciones/2026-10-21-bienvenida-casos-proyectos-design.md` (§4, §9, §16 9.1 y 9.2). Lo lee el
agente del front (BCP-5). Las desviaciones respecto del diseño están al final.

Las cuatro responden **siempre** con `Cache-Control: no-store` (también los errores). Todo error es
`{"detalle": "<texto fijo>"}` y ningún 422 repite lo enviado. Ninguna respuesta lleva una ruta absoluta.
Los `POST` exigen la cookie, `X-Silice-CSRF` y `Origin` propio (403 si faltan), como el resto de la interfaz.
Con la cookie de una contraseña temporal: 403 `Su contraseña es temporal: elija una propia antes de seguir.`
Sin cookie ni clave: 401. `GET /v1/casos` y `POST /v1/casos/actual` **no cambian**.

## C0 · `GET /v1/casos/actual` (cualquier rol; o la clave de API, que ve el caso del proceso)

200:

```json
{ "nombre": "silice.db", "ruta_relativa": "casos/silice.db",
  "ubicacion": "En la carpeta de datos de Sílice: casos/silice.db",
  "partidas": 0, "insumos": 0, "lista_vigente": null, "proyectos": 0, "proyectos_con_version": 0,
  "es_demostracion": false, "por_migrar": false, "error": null }
```

- Solo lectura: no crea el archivo (una carpeta aún no creada da todo en cero y `error: null`), no lo migra, no emite DDL.
- `ubicacion`: en el producto `En %LOCALAPPDATA%\Silice\datos\casos\x.db` (la variable, literal); en desarrollo,
  relativa a la carpeta del programa (`En data/casos/x.db`); si no, `En la carpeta de datos de Sílice: casos/x.db`;
  fuera de todo, `Fuera de la carpeta de datos de Sílice: x.db`.
- `es_demostracion`: por el **nombre** `demostracion.db` (sin distinguir mayúsculas ni la tilde).
- `proyectos_con_version`: proyectos con una versión vigente (no descartada).
- `error` (texto fijo o `null`):
  `No se pudo leer esta carpeta de trabajo: restaure un respaldo o elija otra.` ·
  `Otro programa tiene abierta esta carpeta de trabajo: ciérrelo y vuelva a intentarlo.` ·
  `Esta carpeta de trabajo se actualizará al abrirla; su resumen aparecerá entonces.` (con `por_migrar: true`) ·
  `Esta base (x.db) es de una versión más nueva de Sílice (revisión …). Instale esa versión o restaure el respaldo previo; no se modificó.`
- 503 `Esta sesión no trabaja sobre un archivo de Sílice: no hay carpeta de trabajo que resumir.` (solo si el proceso no usa SQLite).

## C1 · `POST /v1/casos` `{"nombre": "<texto ≤ 200>"}` (`CAMBIAR_CASO`: arma y administrador)

| Estado | Cuerpo |
|---|---|
| 201 | `{"nombre": "Obra_1.db", "ruta_relativa": "casos/Obra_1.db"}` (el nombre **final** saneado: `Obra*1` → `Obra_1.db`) |
| 409 | `Ya existe la carpeta de trabajo Obra.db: ábrala de la lista o elija otro nombre.` (sin distinguir mayúsculas; nombra la que ya existe) |
| 409 | `Ya hay 100 carpetas de trabajo: retire alguna antes de crear otra.` |
| 409 | `Hay otra creación de carpeta en curso: espere unos segundos y repita.` |
| 409 | con la clave de API: `Con la clave de API se trabaja en el caso del proceso (APU_BASE); el caso se elige por sesión desde la interfaz.` |
| 422 | forma del cuerpo (falta, no es texto, > 200): `Escriba el nombre de la carpeta de trabajo como texto de hasta 200 caracteres.` |
| 422 | nombre reservado: `Ese nombre está reservado para la demostración.` (`demostracion`, `Demostración`, `DEMOSTRACION.db`…) |
| 422 | forma del nombre (texto de la clásica, `operacion/base_datos.py`): `Elija un caso: el nombre no puede quedar vacío.` · `«x» es una ruta de red (UNC)…` · `…es una ruta absoluta…` · `…sale de la carpeta de casos (..).` · `…lleva carpetas…` · `…no puede llevar «:».` · `…es un nombre reservado de Windows: elija otro.` · `«x» no sirve como nombre de caso: use letras, números, espacios, guiones o puntos.` |
| 503 | `No se pudo preparar la carpeta de trabajo: no se guardó. Pruebe de nuevo; si sigue, avise al administrador.` |

**No la abre**: el front llama después a `POST /v1/casos/actual` con el `nombre` devuelto (DV-BCP-6).

## C2 · `POST /v1/casos/subida` (`CAMBIAR_CASO`), `multipart/form-data`

Campos: `archivo` (obligatorio, **uno solo**) y `nombre` (opcional, ≤ 200; si falta o está en blanco, se usa la
última parte del nombre del archivo: `..\..\x.db` → `x.db`).

| Estado | Cuerpo |
|---|---|
| 201 | `{"nombre": "obra.db", "ruta_relativa": "casos/obra.db", "aviso": null}`; `aviso` = `Se actualizó el archivo a la versión actual de Sílice; quedó un respaldo previo.` si hubo que migrarlo |
| 409 | `Ya hay una carpeta de trabajo llamada Obra.db: cambie el nombre antes de subirla.`; el tope; «en curso»; la clave (textos de C1) |
| 413 | en la práctica lo responde el tope del cuerpo de la API: `El cuerpo de la peticion excede el maximo de 20 MiB.` (el front muestra el suyo, «El archivo pasa de 20 MiB.») |
| 422 | forma (sin `archivo`, dos `archivo`, `archivo` que no es un archivo, `nombre` > 200): `Envíe un solo archivo .db en el campo «archivo» y, si quiere, un nombre de hasta 200 caracteres.` |
| 422 | sin firma SQLite: `«x.db» no es una base de Sílice (SQLite): no se guardó.` |
| 422 | SQLite pero no válida (rota, de otro programa, con disparadores, vistas o tablas virtuales, sin las tablas de un caso, la base de la instalación): `El archivo no es una carpeta de trabajo de Sílice válida: no se guardó.` |
| 422 | de un Sílice más nuevo: `Esta base (x.db) es de una versión más nueva de Sílice (revisión …). Instale esa versión o restaure el respaldo previo; no se modificó.` |
| 422 | sin `nombre` y con un nombre de archivo vacío o inservible: `El archivo no trae un nombre utilizable: escriba un nombre para la carpeta de trabajo.` |
| 422 | nombre reservado o de forma inválida (textos de C1; el `nombre` del formulario pasa por las mismas reglas que al crear) |
| 503 | el de C1 |

Un archivo rechazado no deja nada en la carpeta de datos. Subir **nunca** reemplaza una carpeta existente.

## C3 · `POST /v1/casos/demostracion` (`EDITAR_HOJA`: solo arma), sin cuerpo

| Estado | Cuerpo |
|---|---|
| 201 | `{"nombre": "demostracion.db", "ruta_relativa": "casos/demostracion.db"}` (la creó; tarda unos segundos, hasta 120 s) |
| 200 | el mismo cuerpo: ya existía con los datos de ejemplo (no se toca) |
| 409 | `Ya existe demostracion.db, pero sin los datos de ejemplo: para volver a crearla, el administrador la retira de la carpeta de datos con Sílice cerrado.` |
| 409 | el tope (texto de C1); con la clave de API (texto de C1) |
| 503 | `No se pudo preparar la demostración. Pruebe de nuevo; si sigue, avise al administrador.` |
| 503 | `Hay otra creación de carpeta en curso: espere unos segundos y repita.` |

No abre la demostración ni toca la carpeta abierta: el front ofrece «Abrirla ahora» (`POST /v1/casos/actual`).
Los datos son ficticios (clínica didáctica: cinco partidas `LB-*`, tres `DEMO-*`, presupuesto `DEMO-001`).

## Permisos (S8)

| Cuenta | C0 | C1 | C2 | C3 |
|---|---|---|---|---|
| `rita` (revisa) | 200 | 403 | 403 | 403 |
| `ana` (arma) | 200 | 201 | 201 | 201 / 200 |
| `admin` (administrador) | 200 | 201 | 201 | **403** |
| clave de API | 200 (caso del proceso) | 409 | 409 | 409 |

## Desviaciones respecto del diseño

1. **C3 con la salida del hijo inválida → 503**, no 422 (es falla del servidor, no de la persona); el 422 «no es
   válida» de la tabla de §9 queda solo para C2.
2. **C3 con `demostracion.db` existente sin partidas → 409** con texto propio (nunca se pisa); el diseño no decía qué hacer.
3. **El 409 de «ya existe» nombra la carpeta que ya está** (`Obra.db`), no lo que se tecleó (`OBRA`), y usa el término
   «carpeta de trabajo» (D-1 pendiente; si Eugenio elige otra palabra, se cambia en `aplicacion/casos.py`).
4. **C0 sin archivo de proceso → 503** con texto fijo (el diseño solo listaba 503 sin texto).
