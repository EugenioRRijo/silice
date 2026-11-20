# Auditoría en paralelo — 2026-11-20

Canal entre Neon (Gemini, por `agy`, en solo lectura) y Claude (orquestador y verificador). Neon auditó el diff
`5f910132..main` sobre `main` 859f62b4 en tres áreas: **A** (`aplicacion/`), **B** (`api/rutas/` y `adapters/`) y **C**
(interfaz, `frontend-desktop/src/`). Un subagente de Claude verificó cada hallazgo contra el árbol y reprodujo en pruebas
fuera del repositorio los que salían baratos. Nada de datos de la empresa en esta tabla (NORMAS §1).

Veredictos: **confirmado** (se abre tarea), **falso positivo** (con la razón), **decisión** (dos conductas razonables;
el verificador propone una), **nota** (gravedad baja). En la columna «Nota» van la gravedad de Neon y la del verificador,
la rama de la unión que lo arregla y, si lo hay, su decisión del acta.

Los hallazgos de las tres áreas van a la rama que los arregla en el sprint 1120b; la unión está en
`union/sprint-1120b` (ver [ESTADO §2](../ESTADO.md)).

## Área A: `aplicacion/`

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| A1 | Neon | `aplicacion/simulador.py:63` y `:124-127`: precios indexados por `(descripcion, unidad)` sin normalizar la unidad nula ni incluir el tipo | Con un material y un equipo de la misma descripción, uno con unidad nula, el ordenado da `TypeError` (500); el equipo pisa a la mano de obra sin aviso. Reproducido | **confirmado** | MAYOR → MAYOR. `feature/depurar-logica-1120`; clave `(descripción, unidad o "", tipo)` (DS-106) |
| A2 | Neon | `aplicacion/hoja_guardado.py:339-348`: tras guardar el desglose, las partidas iguales a la base siguen en el borrador | Queda «1 cambio» tras guardar y el segundo Guardar responde 422 «Ese desglose ya está guardado.». Reproducido | **confirmado** | MAYOR → MAYOR. `feature/desperdicio-responsable` |
| A3 | Neon | `aplicacion/hoja_edicion.py:500-505`: «Aplicar» sin cambios mete trazas de 0 % en el borrador | Tapa el desglose que guarda Componer y, al guardar la versión siguiente, lo borra de la base. Reproducido | **confirmado** | MAYOR → MAYOR. `feature/desperdicio-responsable` (DS-99) |
| A4 | Neon | `aplicacion/control_tablas.py:55` y `aplicacion/control_hallazgos.py:169`: se asume que todo hallazgo cita `valuacion:` y que la clave no tiene `:` | `IndexError` (500) con un origen sin `:`; `"a-mano:1"` se imputa a la valuación 1; `VAL:01` sale «OK» con errores. Reproducido | **confirmado** | MAYOR → MAYOR. `feature/depurar-logica-1120` (DS-107) |
| A5 | Neon | `aplicacion/elaboracion.py:666-667` y `aplicacion/hoja_vial.py:323-324`: `nuevo` no se revalida dentro de `with vivo.cerrojo:` | Una edición concurrente del borrador nuevo se descarta si la llevada falla. Es el patrón de DS-58 (`libro_a_la_hoja.py:449`) | **confirmado** | MAYOR → MENOR. `feature/depurar-logica-1120` según el resumen; ver nota del acta sobre si la unión lo cubre |
| A6 | Neon | `aplicacion/hoja_plano.py:514-518`: el registro de importaciones cuenta las filas omitidas como entradas | «33 filas en el espacio» cuando entraron 3. Reproducido | **confirmado** | MENOR → MENOR. `feature/depurar-logica-1120` (DS-125) |
| A7 | Neon | `aplicacion/elaboracion.py:466-475` y `:511-524`: el borrador en blanco salta `_sin_valorar` | Entra una partida `PENDIENTE` sin el 409 `PartidasSinValorar`, y `agregar` devuelve `aviso=None` | **decisión** (el verificador propone la opción A) | MENOR → NOTA. `feature/depurar-logica-1120` (DS-105, opción A) |
| A8 | Neon | `aplicacion/libro_a_la_hoja.py:528-531`: `llevar_libro` relee `vivo.borrador` fuera del cerrojo | Precios y banderas `casa` de la respuesta pueden no corresponder a lo llevado | **confirmado** | MENOR → NOTA. `feature/depurar-logica-1120` |
| A9 | Neon | `aplicacion/plan_rendimientos.py:127` y `:306`: aviso «se le asignó 1 día» a una partida que no entra al plan | El aviso es falso y `tests/unit/test_plan_rendimientos.py` fijaba la frase | **confirmado** | MENOR → MENOR. `feature/depurar-logica-1120` |
| A10 | Neon | `aplicacion/hallazgos_pdf.py:119-127`: `dinero` no protege `Decimal` no finitos | No hay camino para `NaN` ni `Infinity`: los lectores lo descartan antes | **falso positivo** | MENOR → NOTA. Sin cambio |
| A11 | Neon | `aplicacion/hoja_partidas.py:416-417`: el atajo de exponente 0 va antes de validar la base | `desconocido**0` da «1» en vez de no ser cálculo. Reproducido | **confirmado** | MENOR → NOTA. `feature/depurar-logica-1120` |
| A12 | Neon | `aplicacion/revision.py:476` y `:484`: `str()` sobre campos del manifiesto | Con `"proyecto": null` el paquete pasa como `"None"` | **confirmado** (lectura) | MENOR → NOTA. `feature/depurar-logica-1120` |
| A13 | Neon | `aplicacion/presupuesto_pdf.py:576`: celdas de la tabla de APU sin `_limpio` | Un carácter de control sale como `\x00` en vez de «�»; no rompe el PDF | **confirmado parcial** | MENOR → NOTA. El resumen lo dice «sin defecto»: sin cambio de código, prueba de guarda (DS-109) |

## Área B: `api/` y `adapters/`

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| B1 | Neon | `api/rutas/control.py:304-316` y `:868-892`; `aplicacion/control_linea_base.py:292-293`: rutas que releen con la misma sesión después del `commit()` | Reabren una escritura `BEGIN IMMEDIATE`. Reproducido en `registrar_y_controlar` y en `linea-base`. La ruta de `elegir` (`aplicacion/control_calculo.py:110`) **no**: el verificador la marca falsa, sale del mapa de identidad | **confirmado en 2 de 3 rutas** | MAYOR → MENOR. `feature/depurar-api-1120` (patrón DS-70). DS-117 trata `elegir_opcion`; ver nota del acta |
| B2 | Neon | `api/rutas/reajuste.py:321`, `:324`, `:327`, `:342`; `aplicacion/reajuste.py:403`: `rollback()` en `_preparar`, bloqueo soltado y dos `ahora()` | Con otra escritura en medio, el estado de la respuesta puede ser «parcial» mientras se guarda «cerrado». La guarda S1-R21 del núcleo evita la corrupción (422) | **confirmado** | MAYOR → MENOR. `feature/depurar-api-1120` (DS-110, DS-115) |
| B3 | Neon | `adapters/espacio/planos/informe.py:440-443` y `:460-466`: `_de_antes` borra un `REC-<handle>` por la sola coincidencia del handle | Al importar `planta_alta.dxf` se borra el recorrido de `planta_baja.dxf`. Reproducido | **confirmado** | MAYOR → MENOR. `feature/depurar-api-1120` (DS-114) |
| B4 | Neon | `api/rutas/presupuestos.py:267` (antes de `:269-270`): la escritura se abre antes de guardar y validar el archivo subido | El caso queda bloqueado mientras se inspecciona un libro que luego se rechaza. Incoherente con DS-32 | **confirmado** | MAYOR → MENOR. `feature/depurar-api-1120` (DS-112) |
| B5 | Neon | `adapters/hoja_empresa/escritor/copia.py:358-361` y `:365-390`: `tamano_imagen` admite ancho o alto 0; el lector JPEG se desincroniza con relleno `0xFF` | Imagen con dimensión 0 → `ZeroDivisionError` (500) y se pierde la devolución. Reproducido: `tamano_imagen` da `(0, h)` | **confirmado** (otro mecanismo) | MAYOR → MENOR. `feature/depurar-api-1120`. El relleno `0xFF` queda fuera de alcance (ESTADO §5) |
| B6 | Neon | `adapters/espacio/planos/dxf.py:686-701`: polilínea sin vértices en una capa `REC-*` | `IndexError` (500); contradice el contrato «Nunca lanza» de `importar_dxf`. Reproducido | **confirmado** (POLYLINE) | MAYOR → MENOR. `feature/depurar-api-1120` |
| B7 | Neon | `api/rutas/indices.py:309-310`, `:401-404`, `:422-425`, `:599-602`: `sesion` antes de `SOLO_CUENTA` y de `ModuloRiesgo` | Con clave de API o módulo apagado, un caso roto da 503 en vez de 403 o 404 | **confirmado** | MENOR → NOTA. `feature/depurar-api-1120` (DS-116) |
| B8 | Neon | `api/rutas/indices.py:332-338` y `:475-482`: el 503 lleva `error.orig` (texto del motor SQLite) | Contra la regla C1 de la bitácora de rutas (`2026-10-20-hoja-3d1-contrato-rutas.md:79`) | **confirmado** | MENOR → NOTA. `feature/depurar-api-1120` (DS-113) |
| B9 | Neon | `api/rutas/admin_claves_api.py:79` y `:89`: `sesion_de_instalacion()` sin `escritura=True` antes de `SELECT` + `INSERT`/`UPDATE` | `test_v9` pasa: el `SQLITE_BUSY` que se temía no aparece en la prueba | **falso positivo** | MENOR → —. Sin cambio (DS-67 B, DS-68) |

## Área C: interfaz (`frontend-desktop/src/`)

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| C1 | Neon | `paginas/hoja/useEdicionDeSeccion.ts:205-207`: `accionarEnOrden` da por bueno el aceptado de una vuelta anterior | Borra el rechazo 422 y pisa lo tecleado. Reproducido en `verif_c/verifC1.test.tsx` | **confirmado** | MAYOR → MAYOR. `feature/depurar-front-1120` (DS-101) |
| C2 | Neon | `paginas/versiones/index.tsx:90`: título fijo «Versión guardada» al guardar solo el desglose | El aviso dice «Versión guardada» aunque no se creó versión | **confirmado** | MENOR → MENOR. `feature/depurar-front-1120` (DS-102) |
| C3 | Neon | `paginas/indices/SeriesViales.tsx:161-213` (y `:111-146`): controles activos durante el POST | El resultado de un envío aparece bajo otra serie o archivo | **confirmado** | MENOR → MENOR. `feature/depurar-front-1120` (DS-103, DS-103b) |
| C4 | Neon | `paginas/existencias/DialogoAnularConteo.tsx:40-77`: se puede cerrar mientras la anulación está en vuelo | El error de la API se pierde si el diálogo se desmonta | **decisión** (el verificador propone la opción A) | MENOR → MENOR. Sin cambio: A, dejar igual que `DialogoAnular` (DS-100) |
| C5 | Neon | `paginas/control/PestanaValuaciones.tsx:180-181`: `setRegistro(null)` va después de la validación temprana | El aviso verde de la valuación anterior queda junto a los errores nuevos. Reproducido en `verif_c/verifC5.test.tsx` | **confirmado** | MENOR → MENOR. `feature/depurar-front-1120` (sin DS en el resumen) |
| C6 | Neon | `paginas/indices/index.tsx:249` con `marco/useModulos.ts:10`: `apagados` vale `[]` mientras carga | Con `riesgo` apagado, `SeriesViales` se monta antes de saber el módulo, pide la serie, recibe 404 y muestra un error transitorio | **confirmado** | MENOR → MENOR. `feature/depurar-front-1120` (DS-104) |
| C7 | Neon | `sesion/FormularioDeContrasena.tsx:34-46`: sin guardia contra doble envío | El botón `disabled` y el vaciado de React evitan el segundo envío | **falso positivo** | MENOR → —. Sin cambio |

## Compuertas por rama (revisión de Neon antes de unir)

Cada rama tuvo su propia revisión de Neon (alta) antes de unirla. Son independientes de la auditoría de arriba.

| Rama (árbol) | Hallazgos de Neon | MAYOR | Confirmados | Falsos positivos | Estado |
|---|---|---|---|---|---|
| `feature/depurar-front-1120` (s2m5) | 6 | 0 | 6 | 0 | confirmados y corregidos |
| `feature/riesgo-mapa-guardado` (s2m3) | 11 | 3 (bajados a MENOR) | 10 | 1 (el 8b: `Presupuesto.proyecto_id` es NOT NULL) | 10 corregidos |
| `feature/depurar-logica-1120` (s2mi2) | 6 | 1 (bajado a MENOR) | 6 (4 de código, 2 pruebas reforzadas con mutante) | 0 | confirmados y corregidos |
| `feature/desperdicio-responsable` (s2m4) | 8 | 3 | 8 | 0 | confirmados y corregidos |
| `feature/depurar-api-1120` (s4g) | 8 | 1 (hueco de prueba de DS-111) | sin cifra en el resumen | sin cifra en el resumen | en corrección al redactar el resumen; la unión ya la trae (`3f700942`) |

## Los 10 detalles del 2026-11-04

Lista de la prueba en vivo del 2026-11-04 (ESTADO §5). Neon (medium) contrastó cada punto con el árbol de `main`
859f62b4. Los diez están resueltos.

| # | Quién | Punto del 2026-11-04 | Evidencia (archivo:línea) | Veredicto | Nota |
|---|---|---|---|---|---|
| 1 | Neon | La tabla de «Guardar versión» muestra el punto decimal | `frontend-desktop/src/paginas/hoja/DialogoDeGuardar.tsx:96-97` → `frontend-desktop/src/comun/presentarCambio.ts:126-134` → `frontend-desktop/src/indicadores/formatoEsVe.ts:53-55` | **resuelto** | Coma decimal |
| 2 | Neon | Avisos con «del proyecto» | Sin textos visibles en `api/`, `aplicacion/` ni `frontend-desktop/src/`; `api/rutas/hoja.py:132` dice «La hoja de la obra…» | **resuelto** | |
| 3 | Neon | «Cadena íntegra: 1 versiones» | `aplicacion/texto_cadena.py:10-14` devuelve «Cadena íntegra: 1 versión» | **resuelto** | |
| 4 | Neon | Registro de cambios con microsegundos y nombres internos | `frontend-desktop/src/paginas/versiones/RegistroDeCambios.tsx:31-53`; `frontend-desktop/src/indicadores/formatoEsVe.ts:71-76`; `frontend-desktop/src/comun/rotulos.ts:7-104` | **resuelto** | |
| 5 | Neon | Cabecera de obra nueva sin la moneda de la obra | `frontend-desktop/src/marco/CabeceraDeObra.tsx:36,48` → `frontend-desktop/src/shell/ListaDeLaCarpeta.tsx:60-64` | **resuelto** | |
| 6 | Neon | «m3» en Aprobaciones y «m³» en la Hoja | `frontend-desktop/src/paginas/aprobar/index.tsx:260` con `frontend-desktop/src/comun/unidades.ts:3-5` | **resuelto** | |
| 7 | Neon | 404 en consola al abrir «Producir mezcla» | `frontend-desktop/src/paginas/produccion/useMezclas.ts:26-33` (recetas en lote con `recetasVigentes`); `api/rutas/produccion_planta.py:425-434` | **resuelto** | |
| 8 | Neon | «Sin cálculo» en las filas de tramos | `aplicacion/hoja_vista.py:397,454`; `frontend-desktop/src/paginas/hoja/logica.ts:652` | **resuelto** | Dice «Sale de los tramos» |
| 9 | Neon | «Trayectorias por corte» bajo «Proyectar» | `frontend-desktop/src/paginas/riesgo/RiesgoDeLaObra.tsx:203-235` | **resuelto** | |
| 10 | Neon | Botones sin nombre accesible en el Visor (3) y en Administración (2) | `frontend-desktop/src/visor/ControlZoomHoja.tsx:27-72`; `frontend-desktop/src/visor/CapaHalos.tsx:71-76`; `frontend-desktop/src/paginas/administracion/index.tsx:84-110` | **resuelto** | Falso positivo en origen para los botones de Carbon; los propios tienen nombre |

## Arbitraje final del sprint

El árbitro Claude xhigh dio la unión `union/sprint-1120b` por **aprobada con correcciones**: el docstring E501 de
`tests/integration/test_migracion_apu_desperdicio.py` y la guía de migraciones (`04180142`), y las pruebas de la fila
«Proyectar» de F8 restauradas (`e7f7c2dd`). Las decisiones del sprint están en
[el acta del 2026-11-17](2026-11-17-decisiones-simuladas.md#sprint-1120b-2026-11-20).
