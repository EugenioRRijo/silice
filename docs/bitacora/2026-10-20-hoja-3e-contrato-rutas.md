# Hoja 3e: contrato de las rutas X1 (Excel) y P1 a P6 (importar plano)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-hoja-e` · **Base:** `dfc8719` · **Fuente:** diseño §3.1, §4.1, §4.6 y §6.4
(filas 3e-1 y 3e-2) y la página clásica `ui/paginas/hoja.py` (P:556-573 y P:1225-1385) sobre la copia `aplicacion/hoja.py`.
Se escribe ANTES de implementar. Si la implementación difiere, la bitácora de avance (`2026-10-20-hoja-3e-avance.md`) lo dice;
la fuente final es `docs/api.json`.

## Reglas comunes (las de E1 a E11; ver `2026-10-19-hoja-3c3-contrato-rutas.md`)

- Prefijo `/v1/hoja/borradores/{id}`; `id` = `^[A-Za-z0-9_-]{16,64}$`. Todo `Cache-Control: no-store` (también en los errores
  propios de la ruta; el 413 es del middleware `LimiteDeCuerpo` y no lo lleva).
- Solo cuenta con `EDITAR_HOJA` (rol `arma`): sin sesión 401; `rita` y `tomas` 403 «Su cuenta no tiene permiso para esta
  acción.»; con `X-Silice-Clave` 403 «La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve.».
  Las que escriben (P1 a P6) exigen `X-Silice-CSRF` y `Origin` propio. X1 es GET.
- Un borrador de otra ficha no existe: 404 «Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo
  que no guardó se perdió: abra la versión otra vez.». Un borrador abierto en otro caso: 409 «El caso cambió desde que abrió este
  borrador: ábralo de nuevo en el caso actual.».
- 503 si no se pudo leer el caso: «No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro
  programa.» (sin el `orig` del driver).
- Todo valor viaja como TEXTO. Los mensajes de dominio (`HojaInvalida`) son los de la clásica, idénticos; los 422 de FORMA llevan un
  mensaje fijo por ruta, sin repetir lo enviado (`RutaSinEco`).
- Una petición a la vez por borrador (su cerrojo, `vivo.cerrojo`). `rev` se comprueba ANTES que el contenido; si no coincide,
  409 «El borrador cambió en otra ventana: vuelva a cargarlo.».
- **La importación de un plano NO es parte del borrador** hasta fusionarla: vive aparte, en el servidor, por borrador
  (`(huella de la ficha, id)`), como `st.session_state[CLAVE_IMPORTACION]` de la clásica. Como mucho UNA importación por
  borrador (leer otro plano reemplaza la anterior). P1 a P4 **no cambian el borrador**: comprueban `rev` pero NO lo suben. Solo P5
  cambia el borrador y sube `rev` (con `hoja_borradores.reemplazar`).
- Los archivos del plano se guardan en una carpeta temporal propia de ese borrador (`tempfile`, prefijo `silice_planos_`); se
  borra (carpeta y archivos) al descartar el borrador (R4 o P6), al vencer, al ser expulsado por los topes, al olvidarse la ficha
  (cierre de sesión, cambio de caso) y tras fusionar. Nada se arma con texto del usuario: el nombre del archivo pasa por
  `aplicacion.subidas.guardar_subida` (nombre seguro, `..\..\x.dxf` se guarda como `x.dxf`, `CON.dxf` como `_CON.dxf`).

## X1 `GET /v1/hoja/borradores/{id}/excel` (3e-1)

Sin cuerpo ni `rev`. Responde 200 con el libro de `hoja.excel_de_hoja_en_bytes` armado como la clásica (P:556-573): el resultado
y el borrador vivos (`hoja_vista.calculo`); si el borrador tiene versión abierta (`vivo.abierta`), además `tabla_de_trazabilidad`,
`precios_de_version(..., fecha_evaluacion=hoy)` y `control.tablas_de_control` (las hojas «Trazabilidad», «Precios» y las de
control); sin versión abierta, solo las hojas del borrador.

- `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- `Content-Disposition: attachment; filename="hoja_{código}.xlsx"` con el código de la versión abierta ya pasado por el nombre
  seguro (un código con `"`, `\r`, `\n`, `/` o `\` no puede romper el encabezado); `hoja_borrador.xlsx` sin versión.
- `Cache-Control: no-store`.
- Errores propios: 422 `No se pudo preparar el Excel: {error}` si el libro lanza `ValueError` (paridad con P:571; el texto del
  error se repite como en la clásica); `SQLAlchemyError` → 503 con el mensaje fijo de arriba (no se repite `orig`).
- **No escribe nada** en la base ni en el borrador (`rev` no cambia, ninguna caché se invalida).
- Paridad: el libro tiene las mismas hojas, en el mismo orden, y las mismas cifras que el de `ui.hoja.excel_de_hoja_en_bytes`
  VIVO con OF-001 y con TI-001 (se compara el contenido de las celdas con `openpyxl`, no los bytes, que llevan marcas de tiempo).

## P1 `POST /v1/hoja/borradores/{id}/plano` — leer un plano

`multipart/form-data`: `archivo` (el `.dxf` o `.ifc`) y `rev` (entero, campo de formulario). Pasos, en este orden de precedencia:
401/403 (sesión, rol, clave, CSRF, Origin) → 413 (cuerpo > 20 MiB, antes de llegar a la ruta; también chunked) → 422 de forma
(falta `archivo` o `rev`, `rev` no entero, más de un `archivo`) con el mensaje fijo `Suba un archivo de plano (DXF o IFC) y envíe el
rev del borrador.` → 404 → 409 caso → 409 `rev` → extensión (`hoja.formato_de_plano`, **ANTES de escribir nada**) → guardar con
`guardar_subida` → `hoja.leer_plano`.

- Extensión que no es `.dxf` ni `.ifc` (sin distinguir mayúsculas): 422 con el texto de la clásica
  `El archivo «{nombre}» no es un plano que se pueda importar. Suba un plano en formato DXF o IFC.`; la carpeta temporal queda
  vacía (no se escribió nada). El nombre se repite tal cual como en la clásica (paridad); se acepta porque es lo que la persona acaba
  de elegir.
- Falta el lector (`ImportError` → `HojaInvalida`): 422 con el texto de la clásica `Falta instalar el componente para leer
  planos {DXF|IFC}. Instale el extra «{planos|civil}» con el comando «uv sync --extra {planos|civil}» y vuelva a intentarlo.`
  (es texto de la clásica; el front lo muestra con su aviso; ver `VB-18` del informe de auditoría: la interfaz nueva puede reemplazar la
  parte del comando por «pídalo a quien instaló Sílice», solo en la vista).
- `ValueError`/`OSError` al guardar (nombre imposible, etc.): 422 `{error}. Renombre el archivo y vuelva a subirlo.` (P:1285).
- Un archivo corrupto NO es error de la ruta: `leer_plano` devuelve `RECHAZADA` con su mensaje y la respuesta es 200
  `estado: "rechazada"` (la persona ve el motivo y puede subir otro).
- Respuesta 200 `ImportacionRespuesta` (abajo). Deja la importación vigente del borrador (reemplaza la anterior y su archivo).

## P2 `POST …/plano/unidad` — reanudar con la unidad del dibujo

`{ "rev": int, "unidades": "<texto>" }` (`extra` prohibido). `unidades` debe ser una de `hoja.UNIDADES_DE_PLANO`
(`m`, `cm`, `mm`, `dm`, `in`, `ft`); otra → 422 fijo `Elija una unidad de la lista: m, cm, mm, dm, in o ft.`. Vuelve a leer el archivo
guardado con esa unidad (`hoja.leer_plano(ruta, unidades=...)`) y reemplaza la importación vigente. Sin importación vigente: 409
`Vuelva a subir el plano: ya no está disponible.` (P:1296). Responde `ImportacionRespuesta`.

## P3 `POST …/plano/alturas` — cargar las alturas pendientes

`{ "rev": int, "alturas": { "<id del ambiente>": "<texto>" } }` (`extra` prohibido; hasta 5 000 entradas; cada texto ≤ 500
caracteres). Usa `hoja.cargar_alturas_desde_texto(resultado, textos)`: una celda en blanco deja ese ambiente pendiente. **Todo o
nada:** si una es inválida, 422 con el texto de la clásica seguido de ` No se cargó ninguna altura.` (P:1344) y la importación
queda como estaba. Sin importación: 409 como P2. Responde `ImportacionRespuesta` con la importación actualizada.

## P4 `POST …/plano/circuitos` — declarar los circuitos supuestos

`{ "rev": int, "circuitos": { "<id>": ["<fase>", "<neutro>", "<tierra>", "<puntos>"] } }` (`extra` prohibido; hasta 5 000
entradas; cada lista de exactamente 4 textos ≤ 500 caracteres). Usa `hoja.declarar_circuitos_desde_texto`. **Todo o nada:** 422 con
el texto de la clásica seguido de ` No se declaró ningún circuito.` (P:1363). Sin importación: 409 como P2. Responde
`ImportacionRespuesta`.

## P5 `POST …/plano/fusionar` — fusionar con el espacio del borrador

`{ "rev": int }`. Usa `hoja.fusionar_plano(vivo.borrador, resultado)` y `hoja_borradores.reemplazar(huella, id, nuevo, rev)`
(sube `rev`, invalida la caché), y completa las composiciones como lo hace la edición del espacio (E1: misma función que usa
`editar_espacio`; ver `aplicacion/hoja_edicion.py`). La importación se descarta (estado y archivo).

- 200 `{ "rev": int, "resumen": Resumen, "fusion": ResumenDeFusionRespuesta, "informe": [FilaInforme], "mensaje": str }`.
  `rev` es el NUEVO (= `resumen.rev`). `mensaje` es el de la clásica (P:1367-1373):
  `Se fusionó «{archivo}» con el borrador de la hoja: {n} ambientes, {m} fuentes y {k} puntos. Revise las filas en las tablas de abajo;
  la auditoría las evalúa como a las demás. Todavía no se guardó ninguna versión: use Guardar versión cuando esté conforme.`
  (`n`, `m`, `k` = `resultado.filas['esp_ambientes' | 'esp_fuentes' | 'esp_puntos']`).
- `fusion` = `{ por_tipo: [{rotulo, cantidad}], filas_por_tabla: [{rotulo, cantidad}], origenes: int }` (`ResumenDeFusion`; el conteo
  NO se duplica: réplica de `test_ui_hoja_planos.py:265`). `informe` = `filas_del_informe` del informe de la fusión.
- Una importación `detenida` o `rechazada` NO se fusiona: 409 con el texto de la clásica
  `No se puede fusionar «{archivo}»: {motivo}` (H:2833). Sin importación: 409 como P2. Si el espacio resultante no es válido o la
  fusión falla por dominio, 422 con el texto de `HojaInvalida`; el borrador y `rev` no cambian.
- Dos P5 con el mismo `rev`: exactamente una gana (200) y la otra recibe 409 de `rev` (cerrojo del borrador).

## P6 `DELETE …/plano` — descartar la importación

Sin cuerpo. 204, idempotente (sin importación o con un borrador que existe, 204; con un borrador inexistente o ajeno, 404 como
las demás rutas del borrador). Borra el estado y los archivos temporales. No cambia el borrador ni `rev`.

## Esquemas

```
ImportacionRespuesta {
  estado: "importada" | "detenida" | "rechazada",
  archivo: str,                       # resultado.archivo
  mensaje: str,                       # resultado.mensaje ("" si no hay)
  pide_unidad: bool,                  # resultado.pide_unidad (estado "detenida")
  unidades: [str],                    # UNIDADES_DE_PLANO si pide_unidad, si no []
  conteos: [ { rotulo: str, cantidad: int } ],            # hoja.resumen_de_importacion(resultado)
  informe: [ { tipo: str, referencia: str, fila: str, mensaje: str } ],   # hoja.filas_del_informe (columnas renombradas)
  alturas_pendientes: [ { id: str, nombre: str } ],       # hoja.alturas_pendientes
  circuitos_supuestos: [ { id: str, fase: str, neutro: str, tierra: str, puntos: str } ],  # hoja.circuitos_supuestos (todo como texto)
  aviso_pendientes: str | null        # el texto de _AVISO_PENDIENTES si hay alturas pendientes o circuitos supuestos; si no, null
}
ResumenDeFusionRespuesta { por_tipo: [ { rotulo, cantidad } ], filas_por_tabla: [ { rotulo, cantidad } ], origenes: int }
FilaInforme              { tipo: str, referencia: str, fila: str, mensaje: str }
```

`aviso_pendientes` = «Si fusiona ahora, los ambientes sin altura entran con 2,5 m provisionales y los circuitos supuestos quedan
marcados en la auditoría. Puede cargarlos antes o corregirlos después en las tablas.» (P:1219). Los textos de ayuda de la pantalla
(`_AYUDA_PLANO`, `_AYUDA_CIRCUITOS`, rótulos de botones) son del front y se copian de la clásica con tildes (diseño §7.5).

## Seguridad (todas)

- Extensión `.dxf`/`.ifc` **antes** de escribir; nombre seguro; tope 20 MiB heredado de `LimiteDeCuerpo` (el cuerpo chunked ya
  responde 413 sin eco; **no se escribe un middleware nuevo**); `adapters/hoja_empresa/guardia.py` es solo de `.xlsx` y no aplica.
- Un DXF/IFC malicioso puede costar CPU y memoria al lector (`ezdxf`, `ifcopenshell`) dentro del tope de 20 MiB: la ruta no lo
  acota por tiempo; **se registra como riesgo en la bitácora de avance** (no se inventa un límite sin medirlo).
- Un plano y su importación son datos de la persona que los subió: nunca se mezclan entre fichas ni borradores (la clave del estado es
  `(huella, id)`); una prueba cruzada lo fija.
- Las carpetas temporales no dejan restos: una prueba comprueba que descartar, vencer, expulsar y fusionar las dejan vacías.

## Lo que NO cambia

R1 a R14, E1 a E11, `rutas.ts` (la Hoja se activa en 3d-2, de la otra sesión), `ui/*`, `core/`, `asistente/`, el guardado (3d).
