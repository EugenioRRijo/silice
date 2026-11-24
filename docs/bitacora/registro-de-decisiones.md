# Registro de decisiones de Sílice

Este registro reúne las decisiones tomadas durante la construcción y depuración de Sílice para que usted
pueda avalar quién decidió qué y cuándo ante el jurado. Las decisiones numeradas como DS se simularon
durante sus ausencias bajo su regla del 2026-10-30, ampliada el 2026-11-12 (simular opciones, elegir la
mejor y documentar cómo revertirla), salvo DS-90 a DS-127, que el orquestador tomó con usted presente en el sprint
del 2026-11-20. Al firmar una fila pendiente usted la convierte en decisión suya; si no está de acuerdo,
tache la fila y escriba «revertir» para mandar a deshacerla según lo indicado en cada caso (el detalle
técnico completo está en [el acta de decisiones](2026-11-17-decisiones-simuladas.md)).

## Ya ratificadas

El 2026-11-18 usted ratificó en bloque las decisiones DS-1 a DS-58, incluida la DS-48h, con dos precisiones
propias: DS-3 quedó sustituida por la mejora de guardar solo el desglose del desperdicio sin crear versión
(DS-48a a DS-48i) y DS-23 dejó congelado el archivo principal de la Hoja hasta después del experimento.

| DS | Tema | Ratificada el |
|---|---|---|
| DS-1 a DS-5 | Depuración inicial y arbitraje de hallazgos (DS-3 sustituida luego por guardar solo el desglose en A.6). | 2026-11-18 |
| DS-6 a DS-12 | Reglas automáticas de orden interno: límites de tamaño, dependencias y control de ciclos. | 2026-11-18 |
| DS-13 a DS-24 | Formato y redondeo al alza al presentar cifras, búsqueda de obras y preservación del archivo congelado de la Hoja (DS-23). | 2026-11-18 |
| DS-25 a DS-33 | Manejo de bloqueos al guardar en la base, respuestas sin caché, mensajes claros y lectura de libros antes de bloquear. | 2026-11-18 |
| DS-34 a DS-41 | División de archivos extensos de presupuestos, Hoja y control en partes más manejables sin cambiar resultados. | 2026-11-18 |
| DS-42 a DS-47 | Controles sobre cómo se muestran cifras y clasificación de qué operaciones escriben en la carpeta del proyecto. | 2026-11-18 |
| DS-48a a DS-48g y DS-48i | Guardar solo el desglose del desperdicio sin crear versión nueva, cómo se cuenta y qué muestra la pantalla. | 2026-11-18 |
| DS-48h | Al guardar solo el desglose, avisar y pedir confirmación si otra persona guardó una versión más nueva mientras tanto. | 2026-11-18 |
| DS-49 a DS-58 | Cierre oportuno de bloqueos de escritura en la base y paso seguro del libro auditado a la Hoja. | 2026-11-18 |

## Por ratificar

Las filas siguientes esperan su firma o la indicación «revertir». Los números DS-118, DS-119, DS-123 y DS-124
no se usaron en el acta.

| DS | Qué se decidió | Se revierte con | Firma | Fecha |
|---|---|---|---|---|
| DS-59 | Cada conteo físico cierra las fechas anteriores o iguales de ese material y no permite movimientos previos ni conteos con fecha futura. | Quitar el bloqueo de fechas anteriores en inventario. | | |
| DS-60 | La revisión de referencias circulares entre recetas revisa todas las versiones guardadas, no solo la vigente. | Revisar ciclos solo en la receta vigente. | | |
| DS-61 | El sistema rechaza valuaciones con fecha posterior a hoy y limita el corte por defecto al día actual. | Quitar el rechazo de fechas futuras en valuaciones. | | |
| DS-62 | El archivo exportado de Escenarios usa formato para Excel en español: punto y coma, coma decimal y dos decimales. | Volver al formato anterior del archivo de Escenarios. | | |
| DS-63 | Una partida sin precios en la lista entra como «Pendiente» con aviso de qué falta; llevar cómputos sigue siendo todo o nada. | Volver a bloquear el alta con error. | | |
| DS-64 | El cálculo de reglas evalúa las potencias en el orden matemático correcto y limita la longitud de las fórmulas. | Revertir el cambio en el código. | | |
| DS-65 | Un pendiente de otra carpeta abre esa carpeta si usted tiene permiso; si no, quita el enlace y explica el motivo. | Quitar la apertura automática de carpeta. | | |
| DS-66 | El cambio de la propia contraseña tiene su propia sección llamada «Contraseña» dentro de Cuenta. | Mover el formulario a otra sección. | | |
| DS-67 | La base general del programa toma bloqueo inmediato de escritura solo cuando una operación lo solicita de forma expresa. | Quitar esa regla en la base general. | | |
| DS-68 | Solo toman bloqueo de escritura en la base general las acciones que realmente guardan allí, sin frenar el resto. | Volver al criterio anterior por tipo de acción. | | |
| DS-69 | Las cifras exactas enviadas a la pantalla salen completas, sin notación científica ni redondeo previo. | Revertir el cambio en el código. | | |
| DS-70 | Las operaciones que leen datos para responder arman su respuesta antes de confirmar el guardado; si fallan, no guardan nada. | Revertir el cambio en el código. | | |
| DS-71 | El índice general de aprobaciones se actualiza justo después de guardar la carpeta, sin bloquear ambas bases a la vez. | Revertir el cambio en el código. | | |
| DS-72 | Solo se puede anular el último conteo físico vigente de cada material, con un ajuste compensatorio y motivo obligatorio. | Quitar la anulación y su cambio de base. | | |
| DS-73 | Cuando una mezcla usa otra mezcla del mismo mes, se calcula primero la mezcla base y luego la compuesta. | Revertir el cambio en el código. | | |
| DS-74 | Los gráficos de barras horizontales del Tablero muestran los datos en el mismo orden de su tabla, con el mayor arriba. | Quitar la inversión de orden en Tablero. | | |
| DS-75 | El desglose del desperdicio se rotula en formato legible sin tocar el archivo congelado de la Hoja (ampliado en DS-97). | Revertir el cambio en el código. | | |
| DS-76 | Las fechas en las tablas densas se presentan en formato legible corto en lugar del formato técnico completo. | Revertir el cambio en el código. | | |
| DS-77 | El informe PDF de hallazgos vuelve a auditar el libro cargado para incluir cada hallazgo y celda igual que en pantalla. | Quitar el generador del informe PDF. | | |
| DS-78 | Descargar el informe PDF de hallazgos no agrega una fila duplicada en el historial de auditorías. | Revertir el cambio en el código. | | |
| DS-79 | El botón de descarga del PDF va en el Visor, junto a los hallazgos, desactivado si no hay auditoría. | Quitar el botón de descarga del Visor. | | |
| DS-80 | La fecha de emisión del informe PDF toma el reloj del servidor y no el del navegador. | Revertir el cambio en el código. | | |
| DS-81 | La asociación de series a insumos en Riesgo se declara en pantalla sin cambiar la base (ampliado en DS-90). | Sin reversión indicada (ampliado en DS-90). | | |
| DS-82 | Las series de precios de la demostración se corren automáticamente en meses enteros hasta el mes anterior a hoy. | Quitar el ajuste de fechas en la demostración. | | |
| DS-83 | La obra de demostración incluye cantidades pequeñas de asfalto y gasoil para mostrar Riesgo sin alterar sus indicadores de Control. | Desactivar esos insumos en la demostración. | | |
| DS-84 | Las series de precios viales se cargan en una sección dentro de Índices del BCV, junto a las demás series. | Quitar esa sección de Índices del BCV. | | |
| DS-85 | La carga de una serie vial se hace en un solo paso, todo o nada, rechazando el archivo entero si falla. | No indicada en el acta. | | |
| DS-86 | Se carga una sola serie vial por archivo para mantener una fuente y una fecha claras en cada importación. | No indicada en el acta. | | |
| DS-87 | Cargar series viales exige tener activo el módulo Riesgo y no permite guardar mediante clave externa, solo consultar. | Quitar la exigencia del módulo Riesgo. | | |
| DS-88 | Al cargar una serie vial, indicar la fuente y la fecha es obligatorio para poder citarla en informes. | Revertir el cambio en el código. | | |
| DS-89 | Riesgo muestra el enlace para cargar series en Índices del BCV únicamente cuando el cálculo avisa que falta una serie. | Quitar el enlace condicional en Riesgo. | | |
| DS-90 | El mapa de series de Riesgo se guarda por versión; si falta, hereda el último de la obra, salvo elección manual. | Revertir el cambio en el código. | | |
| DS-91 | El mapa de series de Riesgo se guarda solo tras un cálculo válido, conservando el último registro y sin duplicar lo igual. | Revertir el cambio en el código. | | |
| DS-92 | En Riesgo se filtran con aviso las series inválidas, se precargan series sin historia y se valida que coincida la moneda. | Revertir el cambio en el código. | | |
| DS-93 | Solo una cuenta con permiso para ver Riesgo puede guardar el mapa de series; con clave externa queda prohibido. | Revertir el cambio en el código. | | |
| DS-94 | Al guardar un mapa propio de Riesgo desaparecen las notas de precarga, los guardados van en orden y se valida el módulo. | Revertir el cambio en el código. | | |
| DS-95 | Se registra quién guardó el desglose del desperdicio desde Componer, la Hoja o un libro llevado; con clave externa queda vacío. | Revertir el cambio en el código. | | |
| DS-96 | El dato de quién guardó el desglose del desperdicio aparece bajo Materiales como texto de ayuda. | Revertir el cambio en el código. | | |
| DS-97 | El nombre del insumo en el rótulo del desglose aparece solo en la lista al guardar; Versiones y Revisar siguen sin él. | Revertir el cambio en el código. | | |
| DS-98 | Las estructuras de datos del desperdicio pasan a archivos propios para reducir el tamaño de los archivos extensos. | Revertir el cambio en el código. | | |
| DS-99 | Criterio de «Aplicar sin cambios» en el desperdicio (ver acta). | Revertir el cambio en el código. | | |
| DS-100 | El diálogo para anular un conteo físico se mantiene igual al diálogo general de anulación, sin cambios de código. | Sin cambio de código que revertir. | | |
| DS-101 | Si falla el último guardado en una secuencia de acciones, la pantalla no se cierra y deja el error visible. | Revertir el cambio en el código. | | |
| DS-102 | Un aviso común informa «Desglose guardado» cuando solo se guardó el desglose del desperdicio sin crear versión nueva. | Revertir el cambio en el código. | | |
| DS-103 | Los campos quedan deshabilitados durante la importación y el aviso previo se borra en cuanto se cambia algún dato. | Revertir el cambio en el código. | | |
| DS-103b | El aviso tras cargar una serie vial muestra su nombre legible en lugar de su código interno. | Revertir el cambio en el código. | | |
| DS-104 | La pantalla distingue cuándo terminó de leer los módulos activos y deja el estado sin definir hasta entonces (ver acta). | Revertir el cambio en el código. | | |
| DS-105 | Un borrador creado en blanco también avisa si tiene partidas sin precio asignado. | Revertir el cambio en el código. | | |
| DS-106 | El Simulador identifica insumos por nombre, unidad y tipo, manteniendo en una sola fila los homónimos del mismo tipo. | Revertir el cambio en el código. | | |
| DS-107 | En Control, cuando varias claves de valuación coinciden al inicio del texto, gana la coincidencia más larga. | Revertir el cambio en el código. | | |
| DS-108 | En Planos, sin filas omitidas se conservan las cifras por tabla; si hubo omitidas, se muestra el total cargado y el omitido. | Revertir el cambio en el código. | | |
| DS-109 | No se modifica el PDF tras comprobar que sale idéntico; se agrega solo una prueba de respaldo. | Sin cambio de código que revertir. | | |
| DS-110 | En Reajuste, el cálculo previo y el guardado se hacen bajo un mismo bloqueo y con una sola hora de referencia. | Revertir el cambio en el código. | | |
| DS-111 | En Control, si falla el cálculo al corte tras registrar, se deshace todo; un fallo al describir la línea base da error interno. | Revertir el cambio en el código. | | |
| DS-112 | Subir un libro dañado sobre una obra inexistente responde error de archivo inválido, igual que en DS-32. | Revertir el cambio en el código. | | |
| DS-113 | Un fallo de la base devuelve un mensaje fijo de servicio no disponible sin detalles internos, también en Control. | Revertir el cambio en el código. | | |
| DS-114 | En Planos, un elemento previo solo se sustituye si coincide en punto y circuito; si no, se conservan ambos y el informe avisa. | Revertir el cambio en el código. | | |
| DS-115 | Si Reajuste falla, deshace todo y suelta el bloqueo cuando él inició la operación; si no, deshace solo su parte. | Revertir el cambio en el código. | | |
| DS-116 | La consulta de series viales verifica primero el permiso y el módulo activo antes de abrir la base de la carpeta. | Revertir el cambio en el código. | | |
| DS-117 | Al elegir una opción de recuperación en Control, el código de versión se lee antes de confirmar el guardado. | Revertir el cambio en el código. | | |
| DS-120 | El rótulo «Guardado por» en el desglose del desperdicio solo se muestra cuando todo lo visible coincide con lo guardado. | Revertir el cambio en el código. | | |
| DS-121 | El borrador del desperdicio registra únicamente los cambios reales respecto a lo guardado en la base. | Revertir el cambio en el código. | | |
| DS-122 | Tras guardar solo el desglose del desperdicio, la vista de APU se recarga automáticamente para mostrar los datos actualizados. | Revertir el cambio en el código. | | |
| DS-125 | El conteo de filas de un plano cuenta solo filas del plano y, si no entró ninguna, indica qué cambió. | Revertir el cambio en el código. | | |
| DS-126 | Los elementos leídos de un plano se separan recorriendo el informe en orden, sin duplicar la lista interna de clasificación. | Revertir el cambio en el código. | | |
| DS-127 | El registro de desgloses del desperdicio y su responsable no se incluye por ahora en el paquete exportado del proyecto. | Revertir el cambio en el código. | | |

## Decisiones de Eugenio en persona

| Decisión | Fecha | Dónde consta |
|---|---|---|
| Ratificar en bloque las respuestas del acta de preguntas del 2026-10-30, dejando para cotejar con el tutor las que dependen de fuentes externas (IVSS, ligante, asfalto, tolerancia de receta, pintura, t·km e IVA 16 %). | 2026-11-04 | docs/ESTADO.md §4, punto 3 |
| Posponer el asistente de IA (T20) para después, sin gasto por ahora. | 2026-11-05 | docs/ESTADO.md §4, punto 5 |
| Autorizar la fusión de los PR #105, #106, #108 (con #107) y la ola 2 (#109), y ratificar por delegación las decisiones de F5, D-01 a D-36, la ola 2 y la prueba de punta a punta. | 2026-11-13 | docs/ESTADO.md §4, puntos 1, 4 y 11 |
| Presentar las cifras redondeadas al alza (dos decimales, mitad hacia arriba) en la franja de indicadores de libros y demás presentaciones de la interfaz, sin cambiar los cálculos exactos. | 2026-11-17 | docs/ESTADO.md §4, punto 13 |
| Aprobar A.6 (PR #121): guardar solo el desglose del desperdicio escribe sus trazas sin crear versión nueva, dejando sin efecto DS-3. | 2026-11-18 | docs/ESTADO.md §4, punto 14; docs/bitacora/2026-11-17-decisiones-simuladas.md |
| Mantener congelado el archivo principal de la Hoja (`aplicacion/hoja.py`) para el experimento y postergar su división (tarea 4.4) hasta el próximo recongelado. | 2026-11-18 | docs/ESTADO.md §4, punto 14; docs/bitacora/2026-11-17-decisiones-simuladas.md |
| Aprobar P7 (PR #120): cambiar de perfil del libro reinicia las hojas marcadas; y C9 (PR #119): identificar por descripción más unidad. | 2026-11-18 | docs/ESTADO.md §4, punto 14 |
| Ratificar las decisiones simuladas DS-1 a DS-58 (incluida DS-48h) y autorizar la fusión de la pila #110 a #122. | 2026-11-18 | docs/ESTADO.md §4, punto 14; docs/bitacora/2026-11-17-decisiones-simuladas.md |
| Conservar el informe PDF de hallazgos en el Visor, nombrar el botón solo «Descargar PDF» y añadir debajo una línea que explique qué archivo baja. | 2026-11-19 | docs/bitacora/2026-11-17-decisiones-simuladas.md; docs/ESTADO.md §1 y §5, punto 9 |
| Autorizar el inicio del sprint 1120b en el orden propuesto y delegar las decisiones operativas bajo la metodología del proyecto (DS-90 a DS-127, por ratificar). | 2026-11-20 | docs/ESTADO.md §4, punto 15; docs/bitacora/2026-11-17-decisiones-simuladas.md |
| Pedir un plan de evaluación más robusta y no circular para la auditoría (evaluado por un consejo independiente) y autorizar la fusión de #142 con pruebas en verde. | 2026-11-23 | docs/planes/2026-11-23-plan-auditoria-no-circular.md; docs/ESTADO.md §2 |
| Elegir la opción A para la carga cognitiva manteniendo el rótulo congelado de la Hoja (PR #140) y autorizar la fusión de #140 y #141. | 2026-11-23 | docs/ESTADO.md §1 |
| Instalar LibreOffice 26.8.3 como oráculo independiente de recálculo en vez de Excel para que cualquiera pueda repetir la medición (Excel queda como comparación eventual). | 2026-11-24 | docs/planes/2026-11-23-plan-auditoria-no-circular.md |

Firma de Eugenio: ______ Fecha: ______
