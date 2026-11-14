# Autocompletado guiado · Árbitro final de Claude, esfuerzo xhigh (2026-11-05): DEVUELTO

> Rama `feature/autocompletado`, diff `origin/main...HEAD` (base 076793b8, cabeza 03db4797). Agente nuevo, sin las
> conclusiones del orquestador. Respuesta literal en lo esencial (sin rutas absolutas del equipo); guardada por Claude.

**VEREDICTO: DEVUELTO.** La rama hace casi todo bien, pero tiene dos fallos de dinero comprobados con pruebas: en los
dos, Componer llena el precio de un insumo con el de otra lista o el de otro insumo, sin aviso. Es justo lo que AC1b
debía impedir, y ninguno está cubierto por las pruebas de la rama. Los dos tienen arreglo pequeño.

**Verificado:** `git diff origin/main...HEAD -- core/` vacío; `guardia_nucleo.py` sin queja; ruff y las pruebas nuevas
de Python en verde; eslint de los 12 archivos cambiados sin salida; pytest de test_openapi, test_api_acceso_por_ruta,
test_api_consulta, test_api_control, test_api_reajuste, test_aplicacion_consulta_precios y
test_consulta_unidades_y_proveedores en verde; vitest en tres tandas (9/86, 9/142, 6/106) en verde. Tres pruebas propias,
fuera del repositorio, con los componentes reales.

## Hallazgos verificados

**[BLOQUEANTE] El precio sale de la lista de otra fecha.** `paginas/componer/TablaInsumos.tsx:72-75` y
`comun/CampoConBusqueda.tsx:270-277`. El buscador se recrea al cambiar la «Fecha», pero el campo conserva los resultados
de la búsqueda anterior; `abrir()` los vuelve a mostrar si el texto es el mismo, y elegir llena el precio de la lista de
la fecha vieja. Salida: escribir «cemento» con 15/08, Tab, cambiar a 20/10, Flecha abajo y Enter →
`PEDIDAS: ["/v1/consulta/insumos?q=cemento&limite=8&detalle=true&para_armar_al=2026-08-15"]`,
`PRECIO CON FECHA 2026-10-20: 18,00` (esperado 25,50; una sola petición). Corrección: que la celda se vuelva a montar al
cambiar la fecha (`key` con fecha e índice) o un prop que vacíe la búsqueda guardada; decidir qué pasa con los precios
ya llenados al cambiar la fecha; prueba.

**[BLOQUEANTE] Elegir un segundo insumo sin precio deja el precio del primero.** `paginas/componer/autocompletado.ts:45`,
`tablas.ts:96-103`, `TablaInsumos.tsx:96-99`. `valoresAlElegir` no devuelve precio, `completarFila` solo junta las claves
que llegan y la marca de la fila no guarda qué celdas llenó el catálogo. Contra el diseño del 2026-10-21 §1.6
(`docs/especificaciones/2026-10-21-autocompletado-de-campos-design.md:54-57`: «nunca se mezclan en una misma fila»).
También al revés: un precio escrito por la persona se reemplaza sin aviso al elegir un insumo con precio
(`autocompletado.ts:50`). Salida: `TRAS ELEGIR ARENA: {"descripcion":"Arena ficticia","precio":"18,00","ayuda":null}`
(el 18,00 era del cemento). Corrección: la marca guarda el precio y la unidad que puso el catálogo; al elegir otro, si la
celda conserva el valor del catálogo se reemplaza o se vacía; si lo escribió la persona, se deja y la ayuda muestra el
del catálogo. Pruebas de dos elecciones seguidas y de un precio escrito antes de elegir.

**[MAYOR] En el panel «Componer una partida», Esc deshace solo la descripción.** `paginas/hoja/ComponerEnPanel.tsx:73-86`
frente a `TablaInsumos` (`escLimpia={false}`) y DESIGN.md:250. El panel restaura la celda en fase de captura; la unidad y
el precio llenados se quedan. Salida: `TRAS ESC: {"descripcion":"","unidad":"saco","precio":"18,00"}` y
`MEZCLA TRAS ESC: {"descripcion":"Arena ficticia","unidad":"saco","precio":"18,00"}`. Corrección: que el panel no
restaure un combobox que llena varias columnas (atributo) o que la tabla deshaga la fila entera; prueba en
AgregarPartida.test.tsx.

**[MAYOR] La lista no muestra precio, moneda ni fecha.** `comun/consulta.ts:53-66` (`secundaria: [s.valor, s.fuente]`).
`fecha_precio` y `moneda` llegan y no se muestran. El diseño (§1.6 y §3.4, líneas 54-57 y 286-297) pide precio con moneda
y fecha en cada resultado y «sin precio en la lista vigente». Corrección: código, unidad y «18,00 Bs · lista del
01/07/2026», o «sin precio en la lista para armar», o el aviso de moneda (`formatoEsVe`, `fechaEsVe`).

**[MENOR] Precio en notación científica.** `api/rutas/consulta.py:179` (`str(s.precio)`): `Decimal('1E+2')` y `0E+2`.
Corrección: `format(s.precio, "f")` con una prueba de 1E+2.

**[MENOR] Control valida con una lista que puede estar recortada.** `paginas/control/PestanaValuaciones.tsx:100-104`,
`aplicacion/control.py:300, 309`: bloquea si la partida no está en la línea base más reciente (`date.max`), mientras R13
juzga contra la vigente al corte; la lista se corta en 2000 sin decirlo. Corrección: `truncada` en la respuesta y no
bloquear cuando está recortada, o tomar el corte, o dejar que decida el servidor.

**[MENOR] Permiso de /v1/consulta/proveedores** (consulta.py:119): LEER_PROYECTO frente al EDITAR_HOJA del diseño (§12.2);
la razón del docstring es aceptable pero el desvío no consta; además ofrece proveedores de cotizaciones retiradas (el
diseño, §13, decía activas).

**[MENOR] Errores de las rutas nuevas de Control y Reajuste.** El 404 repite lo pedido (control.py:200, reajuste.py:233;
H-17 del diseño pedía un 404 fijo); las tres rutas no capturan SQLAlchemyError (500 genérico, no el 503 fijo de consulta).

**[MENOR] Accesibilidad.** El aviso de moneda va como ayuda de la celda del precio (TablaInsumos.tsx:182), fuera de la
región viva (WCAG 4.1.3). Sospechado: en SeleccionMultipleConBusqueda.tsx:124 la región viva aparece con su primer
mensaje y los lectores suelen no leerlo; montarla con el foco, como CampoConBusqueda.

**[MENOR] DRY y capas.** Cuatro copias nuevas de la normalización sin tildes (partidasDelContrato.ts:22, series.ts:16,
unidades.ts:21, proveedores.ts:20) además de la de logicaBusqueda.ts:114; `buscadorDePartidasDelContrato` y
`buscadorDeSeries` casi iguales; importaciones entre páginas que deberían ir por `comun/` (hoja→componer/CampoDeUnidad,
reajuste→control/CampoDePartida, actualizacion→hoja/logicaVersiones.MONEDAS); siguen cuatro MONEDAS en el front.

**[MENOR] TDD.** En 3859162c nacieron tres pruebas sin rojo; en 68bf9ea2 Simulador.test.tsx toma el texto esperado de
`motivoDeRechazo` (circular, aunque logica.test.ts conserva una regex a mano).

**[MENOR] Documentación.** DESIGN.md:250-251 recoge AC1 y AC3, no AC2 ni AC4; sin entrada en CHANGELOG ni enmienda del
ERS (§12.4 y §12.6 del diseño); el plan o la auditoría de AC1-AC4 no está en el repositorio.

**Sospechado:** TablaInsumos.tsx:77, las marcas por índice no se reinician si las filas cambian desde fuera; el aviso
sigue a la vista tras escribir el precio.

## Lo que está bien
`core/` intacto; /v1/consulta compatible hacia atrás; el servidor nunca manda un precio en otra moneda y el cliente lo
vuelve a comprobar; rutas nuevas GET de solo lectura; tabla de acceso al día, sin fugas entre proyectos; docs/api.json
al día; los props nuevos de CampoConBusqueda conservan el comportamiento por omisión; es-VE solo con texto; español llano.

## Sobre los hallazgos ya conocidos
Escenarios: un insumo elegido que no está en el presupuesto base también se ignora en silencio; propuesta sin tocar
`core/`: comparar `insumos_variados` con las filas enviadas y decir cuántos precios no cambiaron nada. Simulador: que la
API acepte también `list[str]`, sin romper el texto de hoy.
