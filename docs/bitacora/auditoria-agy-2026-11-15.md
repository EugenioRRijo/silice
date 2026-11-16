# Auditoría para depurar · 2026-11-15

Canal entre Antigravity (auditor) y Claude (orquestador), con el formato de
[auditoria-agy-2026-11-04.md](auditoria-agy-2026-11-04.md). Nada de datos de la empresa en esta tabla (NORMAS §1).

**Cómo se hizo.** Eugenio pidió que Hydrogen buscara en todo el código cosas para depurar, sin recorrer el programa
entero. El código se partió en áreas y Gemini `gemini-4-hydrogen-high` (por `agy`, en solo lectura) auditó cada una.
A cada encargo se le pasaron los 15 nodos más conectados de su área según el grafo del código (graphify, solo AST, rama
`origin/main` `5f910132`). Las dos áreas más grandes (`aplicacion/` y lectores) se cortaron a los 26 minutos sin
entregar nada y se relanzaron partidas en cuatro. Un subagente de Claude verificó cada informe contra el árbol
`feature/mejoras-ola2` (`7c8bfe6a`), reproduciendo los hallazgos cuando salía barato. Las correcciones van con prueba
en rojo primero, en un árbol por grupo de archivos.

Veredictos: **confirmado** (se abre tarea), **falso positivo** (con la razón), **dudoso**, **ya conocido** (con dónde
está anotado).

## Interfaz: la Hoja y las piezas comunes

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| H1 | agy | `paginas/hoja/useBorrador.ts:52,58,147`, `ProveedorDeLaHoja.tsx:121,144`: tras «Retomar borrador», «Descartar cambios» vuelve a pedir el borrador recién borrado | Reproducido con el arnés de `Retomar.test.tsx`: GET id-a, DELETE id-a, GET id-a, sin POST; pantalla «El borrador ya no está» | **confirmado, MAYOR** | Rama `feature/depurar-hoja` |
| H2 | agy | `paginas/hoja/useGuardado.ts:84-85`: «Guardar» con un PUT en vuelo manda la `rev` vieja | Lectura: se ignora lo que devuelve `esperarEnvios`; la rev se actualiza en un efecto posterior. Termina en un 409 y se recupera con «Recargar» | **confirmado, MENOR** (Hydrogen: MAYOR) | Rama `feature/depurar-hoja` |
| H3 | agy | `paginas/hoja/useEdicionDeSeccion.ts:192-195`: una acción tras un 422 borra el aviso del 422 | Lectura: `mandar(…, false)` hace `setError(null)`; contradice `PestanaPresupuesto.tsx:166` | **confirmado, MENOR** (Hydrogen: MAYOR) | Rama `feature/depurar-hoja` |
| H4 | agy | `marco/useObraDeLaRuta.ts:78-81`: un 401 al reintentar o al cambiar de obra no lleva a entrar de nuevo | Lectura: el `catch` no distingue el 401; `useObras.ts:51` y `Marco.tsx:134` sí lo hacen | **confirmado, MENOR** (Hydrogen: MAYOR) | Rama `feature/depurar-marco` |
| H5 | agy | `paginas/hoja/PresupuestoPorFrentes.tsx:90-92`: el renglón elegido no se invalida cuando desaparece | Lectura: el Select muestra la primera opción y se envía la clave vieja; el servidor responde 422 (no escribe nada) | **confirmado, MENOR** | Rama `feature/depurar-hoja` |
| H6 | agy | `marco/BarraLateral.tsx:31,161-166`: crear una obra no pregunta si hay un formulario sin guardar | Lectura: es la única navegación del marco que no usa `navegarSeguro` | **confirmado, MENOR** | Rama `feature/depurar-marco` |

## Interfaz: las demás páginas

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| P1 | agy | `paginas/riesgo/RiesgoDeLaObra.tsx:160,219-233`: al cambiar de versión sigue a la vista la proyección de la anterior | Reproducido: con VIA-002 elegida se ve el resultado de VIA-001, sin carrera | **confirmado, MAYOR** | Rama `feature/depurar-paginas-a` |
| P2 | agy | `paginas/control/PestanaValuaciones.tsx:304-320`: tras anular, el segundo «Anular» manda la valuación ya anulada | Reproducido: se ve la 10 y se manda dos veces la 11; el núcleo la rechaza («se anula una sola vez») | **confirmado, MENOR** (Hydrogen: MAYOR) | Rama `feature/depurar-paginas-a` |
| P3 | agy | `paginas/control/PestanaValuaciones.tsx:244-279`: el informe tardío de un archivo sale rotulado con el siguiente | Lectura: `elegir` sin turno, subida sin `deshabilitada` | **confirmado, MENOR** | Rama `feature/depurar-paginas-a` |
| P4 | agy | `paginas/produccion/CostoPorTonelada.tsx:81-148`: Mes y Moneda habilitados mientras calcula, sin turno | Lectura; el resultado tardío lleva su propio rótulo (no hay cifra falsa) | **confirmado, MENOR** | Rama `feature/depurar-paginas-a` |
| P5 | agy | `paginas/archivos/CargarComputo.tsx:108-188`: el dominio se puede cambiar con la extracción en vuelo | Lectura; Hydrogen exageró: no «se valora como civil» (el dominio no viaja), solo queda mal rotulado | **confirmado, MENOR** | Rama `feature/depurar-paginas-a` |
| P6 | agy | `paginas/existencias/PestanaImportar.tsx:67-137`: subida sin `deshabilitada` e `importar` sin turno | Lectura | **confirmado, MENOR** | Rama `feature/depurar-paginas-a` |
| P7 | agy | `paginas/auditoria/AuditarApuPorHoja.tsx:182-238`: las hojas marcadas no se reinician al cambiar de perfil | Lectura: lo marcado es lo que se envía; solo choca con el texto de ayuda | **dudoso** | Decisión de diseño; queda para Eugenio |
| P8 | agy | `paginas/auditoria/AuditarApuPorHoja.tsx:187-197`: la respuesta tardía de un presupuesto pinta sus hojas con otro | Lectura: `elegirPresupuesto` sin turno | **confirmado, MENOR** | Rama `feature/depurar-paginas-b` |
| P9 | agy | `paginas/reajuste/index.tsx:247-276`: un error viejo aparece sobre el formulario editado | Lectura; Hydrogen se equivocó de escenario (al cambiar de obra la página se vuelve a montar): pasa al editar con el cálculo en vuelo | **confirmado, MENOR** | Rama `feature/depurar-paginas-b` |
| P10 | agy | `paginas/aprobar/index.tsx:97-125`: un 500 del rastro se ve como «No hay versiones esperando dictamen» | Lectura; `Aprobar.test.tsx:491` solo cubre el 403 | **confirmado, MENOR** | Rama `feature/depurar-paginas-b` |
| P11 | agy | `paginas/indices/EnUsd.tsx:58-133`: «Revisar» habilitado mientras se guarda; permite una segunda confirmación | Lectura | **confirmado, MENOR** | Rama `feature/depurar-paginas-b` |
| P12 | agy | `paginas/actualizacion/index.tsx:170-289`: «Revalorar» durante un descarte; el aviso tardío nombra otra versión | Lectura | **confirmado, MENOR** | Rama `feature/depurar-paginas-b` |
| P13 | Claude (constructor de P8) | `paginas/auditoria/AuditarApuPorHoja.tsx`: «Auditar el libro de APU» sigue activo mientras se leen las hojas del presupuesto; la auditoría sale sin hojas marcadas y el servidor elige por el perfil | Lectura al corregir P8 | **confirmado, MENOR** | Pendiente: fuera del encargo de P8 |

## API

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| A1 | agy | `api/rutas/produccion.py`, `vial.py`, `auditorias.py`: una sesión SQLite usada en otro hilo por `run_in_threadpool` | Reproducido: con SQLAlchemy 2.0.52 el dialecto ya pone `check_same_thread=False`; cada petición usa su sesión en serie | **falso positivo** | — |
| A2 | agy | `aplicacion/hoja_vista.py:397-414` (y `vista_plan`, `vista_parametros`, `vista_espacio`): las vistas releen el borrador fuera del cerrojo | Lectura: `calculo(vivo)` suelta el cerrojo; un `/quitar` en medio da `KeyError` → 500. Carrera estrecha | **confirmado, MENOR** (Hydrogen: MAYOR) | Rama `feature/depurar-api` |
| A3 | agy | `api/rutas/presupuestos.py:219,264,391`: tres rutas con cookie guardan «api (sin clave)» como autor (RF-82) | Lectura; el front no llama a esas rutas, solo una petición directa | **confirmado, MENOR** (Hydrogen: MAYOR) | Rama `feature/depurar-api` |
| A4 | agy | `api/rutas/presupuestos.py` (6 rutas) y `control.py:792`: escriben con BEGIN diferido en vez de `SesionDeEscrituraDep` | Reproducido: A lee, B escribe, A escribe → `database is locked` en 0,00 s, sin esperar `busy_timeout` | **confirmado, MAYOR** | Rama `feature/depurar-api` |
| A5 | agy | `api/rutas/computos.py:83`: `codigos` que no es un objeto JSON → 500 | Reproducido: `123`, `true` y `[1]` dan 500; `"ab"` y `null` dan 422 | **confirmado, MENOR** (Hydrogen: MAYOR) | Rama `feature/depurar-api` |
| A6 | agy | Routers `/v1/admin/*`, `revision.py`, `entregas.py`: los errores salen sin `Cache-Control: no-store` | Reproducido en los 5 routers: 401 y 403 sin la cabecera; los cuerpos no llevan secretos | **confirmado, MENOR** (Hydrogen: MAYOR) | Rama `feature/depurar-api` |
| A7 | agy | `api/rutas/obras.py:317-319`: compara carpetas sin `.resolve()` | Lectura: solo falla con un `APU_BASE` relativo escrito a mano; el producto lo resuelve siempre | **dudoso**; se corrige igual (una línea) | Rama `feature/depurar-api` |
| A8 | agy | `api/rutas/presupuestos.py:347-354`: el `.xlsx` temporal queda huérfano si falla la exportación | Lectura | **confirmado, MENOR** | Rama `feature/depurar-api` |
| A9 | agy | `api/rutas/control.py`: solo `partidas` traduce `SQLAlchemyError` a 503 | Lectura: inconsistencia; el docstring no promete 503 | **confirmado, MENOR** | Rama `feature/depurar-api`: un manejador común en `api/main.py` |
| A10 | agy | `api/rutas/control.py:110`: `corte=2026-11-06Basura` se acepta | Reproducido: 200 con `corte=2026-11-06` | **confirmado, MENOR** | Rama `feature/depurar-api` |
| A11 | agy | `api/rutas/presupuestos.py:398`: el 409 no hace `rollback` | Lectura: la sesión vive dentro de `abrir_sesion` y `close()` deshace lo que no se confirmó | **falso positivo** | — |

## Capa de aplicación: la Hoja y el libro

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| L1 | agy | `aplicacion/libro_a_la_hoja.py:221-248`: dos APU que difieren solo en el bono de alimentación dan `IndexError` | Reproducido con un guion; latente: hoy el lector fija el bono a cero | **confirmado, MENOR** | Rama `feature/depurar-hoja-aplicacion` |
| L2 | agy | `aplicacion/hoja_desperdicio.py:119-140`, `hoja_vista.py:618-631`: borrar el % del desperdicio no quita la traza vigente | Reproducido: con 0,8 + 25 %, enviar «1» y «» sigue mostrando 0,8 + 25 %. Variante del riesgo 1 aceptado en `2026-11-13-desperdicio-en-la-hoja.md` §3 | **confirmado, MENOR** | Después de `feature/depurar-api` (toca `hoja_vista.py`), junto con L3 |
| L3 | agy | `aplicacion/hoja_edicion.py:471-483`: cambiar solo el desglose (neta y %) no sube el `rev` y al guardar dice «No hay cambios» | Reproducido: tres PUT con la misma bruta dan siempre rev 0; guardar responde 422 | **confirmado, MENOR** | Junto con L2 |
| L4 | agy | `aplicacion/libro_a_la_hoja.py:419-458`: los renglones del espacio no cuentan como «ajenos» al comparar porcentajes | Lectura; la otra mitad (cantidades a mano que sobreviven) es el comportamiento general del programa | **confirmado en parte, MENOR** | Rama `feature/depurar-hoja-aplicacion` |
| L5 | agy | `aplicacion/hoja.py:1315-1339`: el plan acepta etiquetas de período repetidas | Reproducido; la API ya las rechaza (`api/esquemas_hoja.py:619-624`) | **congelado** | Próximo re-congelado con acta |
| L6 | agy | `aplicacion/hoja_borradores.py:253-276`: `reemplazar` escribe sobre un borrador ya descartado | Reproducido: con un `descartar` en medio, devuelve rev 1 y `listar` queda vacío | **confirmado, MENOR** | Rama `feature/depurar-hoja-aplicacion` |
| L7 | agy | `aplicacion/hoja.py:652-658`: un recorrido con puntos contradictorios se queda con el primero sin avisar | Lectura | **congelado** | Próximo re-congelado con acta |
| L8 | agy | `aplicacion/hoja.py:2265-2302`: guardar escribiría antes del `try` | Lectura: antes del `try` solo hay lecturas; quien llama deshace (`hoja_guardado.py:261-272`) | **falso positivo** | — |

## Lector de libros Excel y fusión

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| X1 | agy | `adapters/hoja_empresa/escritor/copia.py:354-380`: un JPEG truncado deja el lector de dimensiones en un bucle sin fin | Reproducido con un .xlsx ficticio que pasa la guardia: `copia._imagenes` colgado más de 5 s, sin tope | **confirmado, MAYOR** | Rama `feature/depurar-lector` |
| X2 | agy | `adapters/hoja_empresa/plantilla.py:201-202`, `reglas.py:1632-1636`: `=SUM(G1:G{n})` se expande sin cota | Medido: n=10⁷ → 29 s y 1 GiB; la guardia no mira el texto de las fórmulas | **confirmado, MAYOR** | Rama `feature/depurar-lector` |
| X3 | agy | `adapters/hoja_empresa/calculos.py:742`: una función con menos argumentos tumba la devolución | Reproducido con 7 fórmulas (`=IF()`, `=MOD(1)`…); responde 500 con mensaje fijo | **confirmado, MENOR** | Rama `feature/depurar-lector` |
| X4 | agy | `calculos.py:615-625`: un nombre definido que se refiere a sí mismo | Reproducido: `RecursionError`; 500 controlado | **confirmado, MENOR** | Rama `feature/depurar-lector` |
| X5 | agy | `calculos.py:1033-1040`: `FIND` con inicio 0 o negativo | Reproducido: devuelve 3; Excel da `#VALUE!` | **confirmado, MENOR** | Rama `feature/depurar-lector` |
| X6 | agy | `calculos.py:967`: `=TEXT("0","0000")` da «0» | Reproducido; solo el valor guardado (Excel recalcula al abrir) | **confirmado, MENOR** | Rama `feature/depurar-lector` |
| X7 | agy | `adapters/hoja_empresa/pdf.py:262-265`: un entero de 29 dígitos o más | Reproducido: `InvalidOperation`; 500 con mensaje fijo, no una cifra falsa | **confirmado, MENOR** | Rama `feature/depurar-lector` |
| X8 | agy | `escritor/devolucion.py:436-440`: el nombre de hoja «… (S)» no termina de desambiguarse | Reproducido: punto fijo en el paso 5; pasa al devolver un libro ya devuelto | **confirmado, MAYOR** | Rama `feature/depurar-lector` |
| X9 | agy | `calculos.py:988-991`: `=TEXT(5,"0,000")` sin separador de miles | Reproducido: «0005»; Excel da «0,005» | **confirmado, MENOR** | Rama `feature/depurar-lector` |
| X10 | agy | `escritor/devolucion.py`: una celda con fórmula quedaría sin calcular | Lectura: `_evaluar` asigna `calculado` a toda celda con fórmula antes de `_largas_a_valor` | **falso positivo** | — |
| X11 | agy | Claves de celda con comillas (`'O''Brien'!A1`) | Lectura: `clave()` las produce sin comillas | **falso positivo** | — |
| X12 | Claude (constructor de X8) | `escritor/devolucion.py` `_nombre_libre`: la colisión de nombres de hoja distingue mayúsculas y Excel no | Reproducido: una hoja «Alertas USD-Bs» da `DuplicateWorksheetName` y tumba la devolución | **confirmado, MENOR** | Rama `feature/depurar-lector` |

## Adaptadores, BCV, operación e instalador

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| B1 | agy | `adapters/bcv/tasa.py:117-118`: si falta una cifra, la compra en M.E. se toma como Bs | Reproducido: entra una tasa de 1 Bs/USD sin rechazo ni aviso | **confirmado, MAYOR** | Rama `feature/depurar-bcv-operacion` |
| B2 | agy | `adapters/espacio/planos/dxf.py:683-700`: un recorrido entre dos puntos del mismo circuito se descarta con un mensaje falso | Reproducido: «un extremo coincide con varios puntos: no se adivina» | **confirmado, MENOR** | Rama `feature/depurar-planos` |
| B3 | agy | `planos/informe.py:397-436`, `dxf.py:717`: el id `REC-{handle}` choca entre dos DXF | Reproducido: el recorrido de C1 se pierde al fusionar el segundo plano | **confirmado, MAYOR** | Rama `feature/depurar-planos` |
| B4 | agy | `dxf.py:739-753`: la superficie depende del sentido en que se dibujó el tramo | Reproducido: un sentido da PARED y el otro PISO | **confirmado, MENOR** | Rama `feature/depurar-planos` |
| B5 | agy | `dxf.py:819` promete «Nunca lanza», pero un vértice NaN lanza | Reproducido (2 de 5 variantes); 422 genérico. La parte de `$INSUNITS` es falso positivo | **confirmado, MENOR** | Rama `feature/depurar-planos` |
| B6 | agy | `adapters/civil/ifc.py:158`: una cantidad IFC vacía | Reproducido: `InvalidOperation`; 422 sin GlobalId ni archivo | **confirmado, MENOR** | Rama `feature/depurar-bcv-operacion` |
| B7 | agy | `operacion/base_datos.py:529`: `subir_caso` respalda con el motivo de una migración | Lectura; sin llamadores de producción | **confirmado, MENOR** | Rama `feature/depurar-bcv-operacion` |
| B8 | agy | `operacion/base_datos.py:239-355`: una base con solo `alembic_version` se da por nueva | Reproducido; solo con una base manipulada | **confirmado, MENOR** | Rama `feature/depurar-bcv-operacion` |
| B9 | agy | `adapters/bcv/tasa.py:118-125`, `inpc.py:243`: NaN e infinito | Reproducido: el NaN da `InvalidOperation` y **el infinito se acepta como tasa** (celda `1e999`). La parte de `xlrd` es falso positivo | **confirmado, MENOR** | Rama `feature/depurar-bcv-operacion` |
| B10 | agy | `operacion/registro.py:29-35`: el tapado de secretos no reconoce JSON ni el repr de un dict | Reproducido: `{"password": "…"}` sale íntegro | **confirmado, MENOR** | Rama `feature/depurar-bcv-operacion` |
| B11 | agy | `operacion/eventos_perdidos.py:140-147`: marcar revisado un JSON ilegible lo sobrescribe y desbloquea | Lectura (SEG-12) | **confirmado, MENOR** | Rama `feature/depurar-bcv-operacion` |
| B12 | agy | `planos/informe.py:274,322-331`: el mismo plano con otro nombre deja estados contradictorios | Reproducido: «IMPORTADO, PENDIENTE, OMITIDO» en la misma fila | **confirmado, MENOR** | Rama `feature/depurar-planos` |

## Capa de aplicación: vial y costos

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| V1 | agy | `aplicacion/vial.py:459-463`: el nombre del CSV de tramos se usa para escribir el temporal | Reproducido con otra entrada: `"."*100 + ".csv"` se recorta a «....», que Windows resuelve como la carpeta temporal → `PermissionError` (500) | **confirmado, MENOR** | Rama `feature/depurar-control` |
| V2 | agy | `aplicacion/reportes_viales.py:323,352-354`: dos insumos con la misma descripción toman el origen del primero | Reproducido: ningún número cambia; sale mal el origen | **ya conocido** (T21-7, «gana el primero», `2026-10-31-preguntas-t21-reportes.md:16`) | Cambiarlo es una decisión de Eugenio |
| V3 | agy | `aplicacion/riesgo/proyeccion.py`: sin el percentil 50 falla el índice | Lectura: ningún llamador pasa `percentiles`; el valor por omisión es (50, 80) | **falso positivo** | — |
| V4 | agy | `aplicacion/precios_empresa.py:166-190`: dar de alta un mismo material con dos unidades | Reproducido: crea MAT-003 (saco) y MAT-004 (kg), el homónimo que `_separar` prohíbe | **confirmado en parte, MENOR** | Rama `feature/depurar-control` |
| V5 | agy | `aplicacion/plan_rendimientos.py:125-128,283-295`: una partida pendiente deja un hueco en los días del plan | Reproducido: el plan guardado empieza en «Dia 2» | **confirmado en parte, MENOR** | Rama `feature/depurar-control` |
| V6 | agy | `plan_rendimientos.py:259-265`: `int()` con miles de cifras | La API limita a 500 caracteres y responde con un mensaje claro | **falso positivo** | — |
| V7 | agy | `aplicacion/riesgo/obra.py:118-119`: división entre cero toneladas | Lectura: el cálculo rechaza todo producto con t ≤ 0 | **falso positivo** | — |
| V8 | agy | `aplicacion/computo_csv.py`: el CSV con coma no se normaliza | Es el diseño declarado en el módulo | **falso positivo** | — |
| V9 | agy | `aplicacion/similares.py`: cifras con punto | La API manda con punto y la pantalla las presenta con coma (`formatoEsVe`) | **falso positivo** | — |

## Capa de aplicación: obras, revisión y aprobaciones

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| R1 | agy | `aplicacion/revision.py:229,431`: un manifiesto con `archivos: []` | Reproducido: `KeyError 'emitido'`, que la API responde como 404 con el texto crudo | **confirmado, MENOR** | Rama `feature/depurar-revision` |
| R2 | agy | `aplicacion/revision.py:571-578`: un paquete registrado con un presupuesto ilegible bloquea las entregas siguientes | Reproducido: `presupuesto.json` = `{}` deja 1 fila en `paq_recibido` y todo paquete válido posterior de esa obra y ese emisor falla con 422 en `entrega_anterior`, para siempre | **confirmado, MAYOR** | Rama `feature/depurar-revision` |
| R3 | agy | `aplicacion/revision.py:300`, `paquete/verificar.py:135,152`: un `cadena.json` con otra forma | Reproducido: `AttributeError` → 500; el paquete ya quedó registrado | **confirmado, MENOR** | Rama `feature/depurar-revision` |
| R4 | agy | `aplicacion/entrega.py:118-122`: traga cualquier `SQLAlchemyError` y firma sin `anexos/ia.json` | Reproducido con «database is locked» y con una columna que falta | **confirmado, MENOR** | Rama `feature/depurar-revision` |
| R5 | agy | `aplicacion/indice_aprobaciones.py:78`: un evento huérfano | Ninguna ruta borra obras ni presupuestos; `_reflejar` captura y deshace | **falso positivo** | — |
| R6 | agy | `aplicacion/revision.py:270-346`: `declaracion_retroactiva` y `revisor_armo` con campos faltantes o de otro tipo | Reproducido: 404 con `'fecha_hora'` y 500 con `usuario: 123` | **confirmado, MENOR** | Rama `feature/depurar-revision` |
| R7 | agy | `aplicacion/aprobaciones.py:830-834`: el detalle de un envío sin eslabón | Responde 409 «no está sellada»: cierre seguro con mensaje claro | **falso positivo** | — |
| R8 | agy | `aplicacion/instalacion.py:47-53`: una ficha de respaldo corrupta | Reproducido: `[]` o `{"bases": null}` rompen con 500 `GET /v1/admin/instalacion` | **confirmado, MENOR** | Rama `feature/depurar-revision` |
| R9 | agy | `aplicacion/proyectos.py:77`: la URL de SQLite sin escapar | Solo la usan las pruebas | **falso positivo** | — |
| R10 | agy | `de_quien` con `limite <= 0` | Su único llamador usa el límite por omisión (20) | **falso positivo** | — |

## Capa de aplicación: control, precios y reajuste

Un hecho decide varias filas: `api/main.py:264` y `:270` responden 422 a todo `ValueError` y todo `ArithmeticError`, así que
los «escapa sin traducir → 500» de esas clases no producen un 500.

| # | Quién | Hallazgo (archivo:línea) | Evidencia | Veredicto | Nota |
|---|---|---|---|---|---|
| C1 | agy | `aplicacion/control.py:676`: el control a una fecha de corte toma la línea base vigente a la última valuación | Reproducido con OB-S2 y dos líneas base: con el corte en la primera salen los unitarios de la segunda (6,00 y 22,10 en vez de 5,00 y 20,00). **Cifra equivocada** | **confirmado, MAYOR** | Rama `feature/depurar-control` |
| C2 | agy | `aplicacion/reajuste.py:466`: un error de valuaciones escapa sin traducir | Reproducido: 422 «pida al menos un periodo» (sin tildes ni prefijo), no 500 | **falso positivo** (queda el texto) | — |
| C3 | agy | `aplicacion/control.py:855`: «VAC (USD) -> 'no disponible Bs'» | Reproducido con la tasa no disponible; solo el texto | **confirmado, MENOR** | Rama `feature/depurar-control` |
| C4 | agy | `aplicacion/control.py:497,1409`: un «0» se perdería por ser falso | Solo reciben textos; «0» no es falso | **falso positivo** | — |
| C5 | agy | `aplicacion/procura.py:429`: la unidad no se normaliza | El front devuelve la unidad que le dio la propia lista | **falso positivo** | — |
| C6 | agy | `aplicacion/control.py:723`: el objetivo «10.9» se trunca a 10 | Reproducido | **confirmado, MENOR** | Rama `feature/depurar-control` |
| C7 | agy | `aplicacion/mercado.py:662`: un importe de 28 cifras | Responde 422 genérico antes de escribir | **falso positivo** (queda el mensaje) | — |
| C8 | agy | `aplicacion/precios_declarados.py:181`: NaN o infinito | Los dos llamadores pasan por `cifra_escrita`, que solo acepta finitos | **falso positivo** | — |
| C9 | agy | `aplicacion/simulador.py:121-127`: dos insumos con la misma descripción y otra unidad | Reproducido: se pierde una fila sin aviso | **confirmado, MENOR** | **Decisión de Eugenio**: casar por (descripción, unidad) cambia el CSV de UC-02 |
| C10 | agy | `aplicacion/mercado.py`: código sin recortar | La API lo recorta antes | **falso positivo** | — |
| C11 | agy | `aplicacion/mesa.py:371-374`: tras convertir a Bs, la mesa muestra el total en USD con la etiqueta Bs | Reproducido; la obra no entra en las sumas | **confirmado, MENOR** | Rama `feature/depurar-control` |
| C12 | agy | `aplicacion/reajuste.py:606`: el Excel del reajuste no lleva el remedio de USD-Bs (RF-214) | Lectura: la respuesta HTTP sí lo lleva | **confirmado, MENOR** | Rama `feature/depurar-control` |
