# Hoja 3d-1: contrato de S1, guardar el borrador como versión (para el agente de front)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `b73b2008` · **Fuente:** diseño §4.5 (S1), §3.1, §4.1,
§4.7, §6.3 (fila 3d-1) y §9 (P25 a P30, P34). Se escribió ANTES de implementar. Si la implementación difiere, la bitácora de avance
(`2026-10-20-hoja-3d1-backend-avance.md`) lo dice; la fuente final es `docs/api.json`.

## S1 `POST /v1/hoja/borradores/{id}/guardar`

Guarda el borrador vivo en la base del caso. **Es la primera ruta de la hoja que escribe versiones.** Con versión abierta crea la
versión nueva (`guardar_version`); con un borrador en blanco de un proyecto sin versiones crea la primera
(`crear_primera_version`, `primera: true`). Una sola ruta para las dos.

**Cabeceras (iguales a E1 a E11):** cookie de sesión `silice_sesion`, `X-Silice-CSRF` (el de la ficha) y `Origin` propio.
Solo con rol `arma` (`EDITAR_HOJA`); `Cache-Control: no-store` también en los errores propios de la ruta (el 413 es del middleware y
no lo lleva). El responsable de lo guardado es SIEMPRE la persona de la sesión (`Nombre <login>`, RF-82): el cuerpo no trae
`responsable`.

**Cuerpo** (`extra` prohibido):

```
{ "rev": int >= 0,                              # el rev que la pantalla vio (resumen.rev)
  "fuente": "<texto, hasta 300 caracteres>",     # por qué se cambia y con qué respaldo (o, en la primera versión, de dónde salen los datos)
  "confirmar_version_mas_nueva": bool = false }  # true: guardar aunque alguien guardó otra versión después
```

**200**

```
{ "codigo": "004",          # la versión creada
  "proyecto": str,          # nombre del proyecto
  "cambios": int,           # cuántos RegistroCambio quedaron (la primera versión: 1, el de creación)
  "total": { "texto": "2821.42", "exacto": "2821.4208…" },   # Monto; el de la vista de resumen justo antes de guardar
  "primera": bool,
  "mensaje": str }          # «Se guardó la versión 004 con 1 cambios registrados.» / «Se guardó la primera versión 001 del proyecto … (total …). Quedó registrada su creación, con su fuente y su responsable.»
```

(`texto` del `Monto` va con dos decimales y punto, como el resto de la hoja: `formatoEsVe` lo pone a la vista.)

Después de guardar, el borrador queda **cerrado**: `GET /borradores/{id}` devuelve `resumen.guardado_como = "004"` y toda edición
(E1 a E7) o nuevo guardado da 409 `Este borrador ya se guardó como la versión 004; abra esa versión para seguir.` El front abre la
versión nueva con R2 (`POST /borradores {proyecto, version: "004"}`).

### Errores, en este orden de precedencia

| Código | Cuándo | `detalle` |
|---|---|---|
| 401 / 403 | sin sesión; rol (`rita`, `tomas`); clave de API (`X-Silice-Clave`); CSRF; `Origin` | los de E1 a E11 |
| 422 | FORMA: `rev` ausente/no entero/negativo, `fuente` ausente o no texto o de más de 300 caracteres, campo desconocido, `confirmar_version_mas_nueva` no booleano | FIJO, sin repetir lo enviado: `El guardado no tiene la forma esperada: envíe rev (entero) y la fuente como texto de hasta 300 caracteres.` |
| 404 | el borrador no existe para MI ficha | `Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.` |
| 409 | el caso cambió desde que se abrió | `El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual.` (no se escribe nada en ninguna base) |
| 409 | el borrador ya se guardó | `Este borrador ya se guardó como la versión {c}; abra esa versión para seguir.` |
| 409 | `rev` distinto del vigente | `El borrador cambió en otra ventana: vuelva a cargarlo.` |
| 422 | sin cambios (versión abierta) | `No hay cambios para guardar: edite alguna celda primero.` |
| 422 | `fuente` vacía o en blanco | versión: `Escriba la fuente del cambio: por que se cambia y con que respaldo.` · primera: `Escriba la fuente de la medida: de donde salen los datos (un plano, un acta).` |
| 422 | primera versión con la hoja vacía | `La hoja esta vacia: describa o importe el espacio antes de guardar la primera version.` |
| 409 | la versión abierta está en solo lectura | `Esta version esta en solo lectura: alguna de sus partidas ya no tiene composicion vigente en el catalogo, asi que recalcularla cambiaria sus precios.` |
| 409 | hay una versión más nueva y no se confirmó | `{ "detalle": "Otra persona guardó la versión {x} después de que usted abrió la {y}. Si guarda, su versión saldrá de la {y} y quedará como vigente sin lo de la {x}.", "version_mas_nueva": "{x}" }` (el único 409 con un segundo campo: el front ofrece «Guardar de todos modos» y reenvía con `confirmar_version_mas_nueva: true`) |
| 422 | primera versión: el proyecto ya tiene versiones (otra persona la creó), no hay lista vigente, la moneda de la lista no coincide | los textos de la clásica: `El proyecto 'P' ya tiene versiones: abra una y use Guardar version.` · `No hay una lista de precios vigente al dd/mm/aaaa: …` · `El proyecto 'P' esta en USD y la lista 'L' en VES: …` |
| 409 | otro `ValueError` o `CatalogoIncompleto` del núcleo | `No se guardó nada: {mensaje}` |
| 503 | la base no se pudo leer o escribir (incluido un cerrojo que SQLite no concede en 5 s) | `No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.` (sin SQL ni rutas) |
| 500 | una excepción inesperada (ni de dominio ni de la base): se deshace todo y FastAPI responde su 500 genérico, sin detalle | `Internal Server Error` (no es contrato: solo garantiza que no queda nada escrito) |
| 413 | cuerpo > 20 MiB | `El cuerpo de la peticion excede el maximo de 20 MiB.` |

**Todo o nada:** ante cualquier error posterior a la validación, ninguna fila nueva (versión, `RegistroCambio`, filas `esp_*`, eslabón
de la cadena). La carrera entre dos guardados se resuelve dentro de la base (BEGIN IMMEDIATE): exactamente uno gana.

## Diferencias deliberadas con la clásica (para el árbitro y para Eugenio)

- **D-5, versión más nueva:** la clásica guardaba «de la versión abierta» aunque ya existiera una más nueva (la nueva versión quedaba
  vigente sin lo de la otra persona). S1 lo comprueba **dentro de la transacción** y responde 409 salvo confirmación. La regla es la
  de `Resumen.version_mas_nueva`: la vigente de ahora es distinta de la versión abierta (también si se abrió a propósito una versión
  vieja: hay que confirmar). **AFINADA el 2026-10-21 (Eugenio, ola de decisiones):** la regla compara la vigente de AHORA con la
  vigente que había AL ABRIR el borrador (`BorradorVivo.vigente_al_abrir`, leída en R2 antes de abrir la versión). Abrir a propósito
  una versión vieja o descartada ya NO pide confirmar si nadie guardó entretanto, y el texto «Otra persona guardó la versión X…»
  es cierto. Una sola regla, `hoja_vista.version_mas_nueva`, para el resumen (`version_mas_nueva`) y para S1. Un borrador en blanco
  nunca avisa. El registro vive en memoria: tras un reinicio el borrador no existe (404) y no se «rehidrata».
- **Sin cambios:** la clásica deshabilitaba el botón y, si se forzaba, `guardar_version` devolvía `None` («No hay cambios para
  guardar.», nota informativa). S1 responde 422 con el texto del motivo de H:1802.
- **Errores de base:** el 503 no repite `error.orig` (C1). Un `ValueError`/`CatalogoIncompleto` va como 409 `No se guardó nada: …`.
- **Mensajes de éxito** con tildes (los compone el servidor, una sola copia).

## Lo que NO cambia

R1 a R14, E1 a E11, `ui/*`, `core/`, `asistente/`, `aplicacion/hoja.py`, `rutas.ts`. Restaurar, cotizar, retirar, convertir y la cadena
(S2 a S6) son 3d-2.
