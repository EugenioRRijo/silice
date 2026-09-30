# Capítulo IV — Desarrollo de la propuesta

| Capítulo | Estado | Última revisión |
|---|---|---|
| IV. Desarrollo de la propuesta | borrador corregido tras la revisión con la lista de cotejo ([acta R2](../revisiones/R2-capitulo-4.md)) y puesto al día con la corrección de la interfaz y los scripts en las secciones 4.2, 4.5.1, 4.6 y 4.12, y con tres cambios de la última etapa del cierre en las secciones 4.3.2 y 4.5.1; aprobado en revisión ([acta C4](../revisiones/C4-capitulos-2-y-4.md)); pendiente la revisión del tutor académico; figuras, referencias por verificar y decisiones del tutor marcadas como pendientes en la sección 4.12 | 2026-09-28 |

Este capítulo describe el sistema desarrollado tal como existía en la rama principal del repositorio
al 23 de septiembre de 2026, una vez concluida la corrección del núcleo de cálculo que se describe
más abajo, con la puesta al día que se precisa en las convenciones del capítulo. Se sigue el orden
causal del plan de desarrollo: primero los requerimientos y el modelo
de datos, luego la arquitectura que los aloja, el motor de costos, el presupuesto con su curva, la
actualización de precios, el adaptador civil, la verificación, los adaptadores de otros dominios,
los módulos de aprendizaje automático y, al final, la interfaz y la API. Cada sección expone el
problema de diseño, la decisión que se tomó y la evidencia que la sostiene: una prueba automatizada,
un módulo del código o la bitácora de trabajo que la registró. Las bitácoras de `docs/bitacora/` son
la memoria de esas decisiones y se incorporan como anexo H.

### Correspondencia con los objetivos

La Tabla 4.1 relaciona cada sección con el objetivo específico que atiende, la fase de la
investigación en que se ubica y el producto verificable que entrega, según la matriz de
trazabilidad del [esqueleto de la tesis](../esqueleto_tesis.md) §2.

**Tabla 4.1**
*Secciones del capítulo, objetivos específicos y fases*

| Sección | Objetivo | Fase | Producto verificable |
|---|---|---|---|
| 4.4.2 Las pruebas antes que el motor | OE1 | I. Diagnóstico | línea base cuantificada del caso didáctico, fijada como oráculo de las pruebas |
| 4.7 Adaptador civil | OE2 | II. Modelado y extracción | reglas paramétricas trazables y adaptador IFC |
| 4.2 Modelo de datos · 4.4 Motor · 4.5 Presupuesto y curva · 4.6 Actualización de precios | OE3 | III. Base de datos y motor de costos | base de datos, motor de costos, presupuesto y curva |
| 4.10 Aprendizaje automático | OE4 | IV. Aprendizaje automático | módulos de normalización, detección de atípicos y estimación de precios |
| 4.8 Verificación | OE5 | V. Verificación | siete reglas de verificación y el informe de auditoría |
| 4.9 Extensibilidad | transversal; OE7 en la variante A de los objetivos | III y VI | adaptadores de telecomunicaciones, mantenimiento industrial y sistemas |
| 4.1 Requerimientos · 4.3 Arquitectura · 4.11 Interfaz y API | soporte de todos los objetivos | — | especificación, arquitectura, interfaz y API |

*Nota.* Elaboración propia a partir del esqueleto de la tesis, §2. El objetivo OE6 (evaluación) se
atiende en el capítulo V.

### Convenciones del capítulo

**Cifras.** Las cifras del proyecto salen de la tabla de cifras citables de
[plan_redaccion.md §5](../plan_redaccion.md). Las de pruebas y cobertura citan la corrida del
servicio de integración continua en la que se midieron, porque ese servicio, que ejecuta la suite
completa en Linux y en Windows en cada cambio, es la fuente de verdad de esas cifras
([metodologia.md §6](../../metodologia.md)). La corrida de referencia de este capítulo es la
[35950215309](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/35950215309), del
23 de septiembre de 2026: 735 pruebas aprobadas en ambos sistemas, ninguna omitida, y una cobertura
del 98 % sobre el núcleo. Las pruebas que citan las secciones puestas al día (4.2, 4.5.1 y 4.6) y
la sección 4.7.3 se escribieron después y se ejecutan en la corrida
[36427904452](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36427904452), del
28 de septiembre de 2026 (commit `308eca5`, PR #14), en verde; las cifras de referencia del capítulo
cambian al resincronizarlo (Tabla 4.10). La prueba de la operación de escenarios
de la API que cita la sección 4.5.1 se escribió en la última etapa del cierre y no figura en esa
corrida: entra en la corrida con que se cierre esa etapa.

**Compuertas.** El desarrollo se organizó con compuertas: criterios que debían cumplirse antes de
continuar, declarados de antemano y explicados en el capítulo III. Aquí se mencionan tres. La
compuerta G0 es la aprobación, por el tutor, de la especificación, el modelo de datos y la
arquitectura, y sigue pendiente. La compuerta G1 exigía que la extracción de cantidades desde un
modelo IFC coincidiera con el cálculo manual. La compuerta G2 elige la técnica predictiva según la
cantidad de datos disponibles.

**Auditoría de cierre.** Antes de congelar el software se auditó el repositorio completo, capa por
capa, y cada hallazgo quedó registrado en un [inventario](../../auditoria/2026-09-inventario.md) con
la etapa de corrección que le corresponde. Esas etapas son cuatro y se ejecutan en orden: la
corrección del núcleo de cálculo; la de los adaptadores, el aprendizaje automático y la API; la de
la interfaz y los scripts; y la actualización de la documentación. Las tres primeras concluyeron el
23, el 24 y el 28 de septiembre de 2026, respectivamente. El capítulo describe la versión del 23 de
septiembre, al concluir la primera. De las dos siguientes incorpora lo que cambió en el modelo de
datos y en los flujos alternativos de la elaboración (UC‑01), la actualización de precios (UC‑02) y
los escenarios (UC‑08), en las secciones 4.2, 4.5.1 y 4.6, y las Tablas 4.10 y 4.11 dan el estado de
cada pendiente al cerrar la tercera. De la cuarta, todavía en curso, el capítulo recoge tres cambios
del 28 de septiembre: la operación de escenarios de la API declara los pendientes del presupuesto
base y la especificación redacta el flujo 3a de UC‑01 en su orden real (sección 4.5.1), y la tabla
de contratos de `NORMAS.md` y la arquitectura muestran la modalidad de mano de obra (sección 4.3.2).
Esa etapa corrigió además, el mismo día, los desfases documentales que describen las secciones
4.1.1, 4.1.3, 4.1.4, 4.2, 4.3.4, 4.4.1 y 4.7.2: esas secciones los describen como estaban el 23 de
septiembre, y la Tabla 4.11 da su estado al cerrar la tercera etapa. El resto de lo que cambiaron la
segunda y la tercera se incorpora al resincronizar el capítulo con la versión congelada del
software (Tabla 4.10). Donde un documento del repositorio contradice al código, este capítulo describe el código y dice que el desfase está
registrado en el inventario, en lugar de heredarlo. Los códigos de esos registros no se usan en el
texto: la Tabla 4.11, al final del capítulo, relaciona cada desfase o limitación mencionada con su
registro.

**Decisiones del tutor.** Nueve decisiones de diseño, numeradas D1 a D9, esperan la validación del
tutor académico, junto con la aprobación de G0 y la elección de la práctica de clasificación de
AACE. El capítulo describe lo implementado y declara cada una como pendiente, con remisión al
[paquete de decisiones para el tutor](../revisiones/2026-09-paquete-tutor.md).

**Naturaleza de los datos.** Todos los análisis de precios unitarios y presupuestos que se
mencionan son ejercicios académicos ficticios o casos construidos para el proyecto
([NORMAS.md §1](../../../NORMAS.md)); ninguno de ellos es una obra ejecutada, y no se presentan como tal.
Los resultados sobre esos casos no se generalizan estadísticamente, y la validación
con presupuestos reales no forma parte del alcance de la investigación, como declara el capítulo I en
§1.5.2.

## 4.1 Requerimientos

Esta sección presenta qué debe hacer el sistema: el documento de requerimientos, los casos de uso,
los requerimientos funcionales con su criterio de aceptación, los no funcionales y el estado
documental de todos ellos frente al código.

### 4.1.1 El documento de requerimientos

Los requerimientos se especificaron con la estructura de la norma IEEE 830 y se recogen en la
[especificación de requerimientos](../../ERS.md) (anexo A). La especificación no reproduce los datos
que tienen fuente única: la fórmula de cálculo, las siete reglas de verificación y los criterios de
degradación del módulo predictivo se enlazan desde ella a `NORMAS.md`, y el caso de estudio, a
[linea_base.md](../../linea_base.md). Con ese criterio, un cambio en la fórmula o en una regla se hace
en un solo lugar.

La versión vigente declara once casos de uso, 42 requerimientos funcionales y diez requerimientos no
funcionales. El documento prevé congelar los ocho casos de uso originales al aprobarse la compuerta
G0, que sigue pendiente; los posteriores se agregaron por extensiones registradas en el propio
documento: UC‑10 y UC‑11, con los RF‑33 a RF‑35, durante el desarrollo del prototipo de composición
de partidas, y UC‑12, con los RF‑36 a RF‑43 y el RNF‑10, durante el diseño del recorrido guiado de la
interfaz. El número UC‑09 y el RF‑32 quedan vacantes, reservados para un asistente de presupuestos que
quedó como trabajo futuro; la numeración de ese asistente a partir de RF‑44 es una de las constancias
que se piden al tutor.

La Tabla 4.2 resume los casos de uso con su actor principal y la forma en que se accede a ellos en la
versión vigente.

**Tabla 4.2**
*Casos de uso del sistema y su realización en la versión vigente*

| UC | Nombre | Actor principal | Acceso en la versión vigente |
|---|---|---|---|
| UC‑01 | Elaborar presupuesto nuevo desde una fuente de cantidades | proyectista | interfaz (pantalla «Elaborar presupuesto») y API (`POST /presupuestos`) |
| UC‑02 | Actualizar masivamente los precios de un presupuesto existente | administrador del catálogo | interfaz y API |
| UC‑03 | Reutilizar partidas y desgloses de proyectos anteriores | proyectista | interfaz (pantalla «Partidas similares») |
| UC‑04 | Recalcular ante cambio de alcance o dimensiones | proyectista | funciones del núcleo y del adaptador civil, sin pantalla propia |
| UC‑05 | Auditar un presupuesto elaborado por un tercero | auditor | incluido en toda elaboración; informe por la interfaz y la API |
| UC‑06 | Registrar y consultar rendimientos medidos | residente de obra | API |
| UC‑07 | Contrastar el precio construido con el precio de mercado | auditor | script de resultados y ayudas de la pantalla de composición |
| UC‑08 | Generar escenarios de sensibilidad | proyectista | interfaz y API |
| UC‑10 | Componer una partida | proyectista | interfaz (pantalla «Componer partida») |
| UC‑11 | Editar una partida compuesta | proyectista | interfaz (pantalla «Componer partida») |
| UC‑12 | Recorrer la aplicación guiado desde el Inicio | usuario nuevo | especificado y pendiente en la versión del 23/09/2026; implementado después en la interfaz (pantalla de Inicio; Tabla 4.10) |

*Nota.* Elaboración propia a partir de `docs/ERS.md` §2.2 y de `ui/app.py`, `api/rutas/` y
`scripts/`. La columna de acceso describe el código. En su §3.1, la especificación declaraba en esa
versión, la del 23 de septiembre, que la interfaz ofrecía los once casos de uso, lo que el código no
confirmaba para UC‑04, UC‑06, UC‑07 y UC‑12; el desfase está registrado en el inventario (Tabla
4.11).

### 4.1.2 Requerimientos funcionales

Cada requerimiento funcional es una afirmación comprobable con prioridad (esencial, deseable u
opcional), el caso de uso que lo origina y un criterio de aceptación que nombra la prueba que lo
demuestra. Esa última columna es la decisión de fondo del documento: un requerimiento sin criterio
medible no se aceptó, y el criterio se escribió antes que la prueba. Por ejemplo, RF‑07 exige que el
acumulado final de la curva de inversión sea igual al total del presupuesto **sin tolerancia**, y
RF‑22 exige que el sistema detecte las siete inconsistencias de la línea base sobre un presupuesto de
prueba que las reproduce.

En la versión del 23 de septiembre, tres grupos de requerimientos no estaban cumplidos y así se
declaran:

- **RF‑20** (diferencial entre la versión anterior y la recalculada, deseable, UC‑04) no tiene
  implementación. Durante la corrección del núcleo se decidió declararlo «no implementado» en lugar
  de escribir un tercer comparador sin ningún módulo que lo usara
  ([bitácora del cierre](../../bitacora/2026-09-23-cierre.md)). Pasa a las limitaciones del trabajo.
- **RF‑36 a RF‑43** (UC‑12, recorrido guiado desde el Inicio) estaban especificados con sus pruebas
  nombradas y sin implementar. La corrección de la interfaz los implementó después; su descripción
  se incorpora al resincronizar el capítulo (Tabla 4.10).
- **RF‑16** (precarga de una partida propuesta con referencia a su origen y a su puntaje) tiene la
  precarga implementada, y la persistencia de la partida nueva se resolvió con la composición de
  UC‑10: su estado es parcial. El alcance de RF‑16 es la decisión D5 del tutor, pendiente.

### 4.1.3 Requerimientos no funcionales

Los diez requerimientos no funcionales se organizaron por características de la norma ISO/IEC 25010,
cada uno con su métrica y su meta. La Tabla 4.3 los lista; sus veredictos se presentan en el
capítulo V a partir de su fuente única, la evaluación de calidad de
[calidad_iso25010.md §9](../../calidad_iso25010.md).

**Tabla 4.3**
*Requerimientos no funcionales, métrica y meta*

| RNF | Característica | Requerimiento | Métrica y meta |
|---|---|---|---|
| RNF‑01 | Adecuación funcional | exactitud del presupuesto frente a la línea base corregida | desviación porcentual dentro de la clase 3 de AACE |
| RNF‑02 | Fiabilidad | el presupuesto se reconstruye a la fecha de su lista de precios | comparación exacta, 100 % |
| RNF‑03 | Eficiencia de desempeño | recálculo masivo tras cambiar la lista de precios | menos de 5 s con hasta 100 partidas |
| RNF‑04 | Usabilidad | el informe de auditoría se entiende sin formación previa | juicio de expertos, Likert ≥ 4/5 |
| RNF‑05 | Mantenibilidad | agregar un dominio no modifica `core/` | `git diff --stat core/` vacío y `test_arquitectura.py` en verde |
| RNF‑06 | Mantenibilidad | cobertura de pruebas del núcleo | ≥ 80 % |
| RNF‑07 | Portabilidad | instalación con `uv sync` en Windows y Linux | cero pasos manuales |
| RNF‑08 | Seguridad | ejecución local, sin credenciales ni servicios externos | cero y cero, con dos excepciones declaradas: la descarga inicial del modelo de similitud y la carga de three.js por el Visor 3D (esta, declarada el 28/09/2026; véase la nota) |
| RNF‑09 | Compatibilidad | entrada IFC 4 de cualquier modelador | cantidades iguales al cálculo manual con archivos de al menos dos herramientas |
| RNF‑10 | Usabilidad | una persona que nunca vio la aplicación llega sola del Inicio a un presupuesto en Excel con su hoja de auditoría | caso con persona CP‑07 en dos escenarios, sin ayuda y en 20 min o menos |

*Nota.* Elaboración propia a partir de `docs/ERS.md` §3.3. En la versión del 23 de septiembre, la fila
RNF‑08 de la especificación declaraba una sola excepción, la descarga del modelo de similitud
(sección 4.10.1). El Visor 3D ya cargaba entonces en el navegador la biblioteca three.js desde
`cdnjs.cloudflare.com` (`URL_THREE_JS` en `ui/paginas/visor.py`), cada vez que se abre y sin caché
propia del sistema, una llamada de red que la especificación no declaraba. La especificación la
declaró como segunda excepción el 28 de septiembre de 2026 (commit `1cf355a`;
[ERS §3.3](../../ERS.md#33-requisitos-no-funcionales-isoiec-25010), fila RNF‑08), sin incorporar la
biblioteca al repositorio; el desfase está registrado en el inventario (Tabla 4.11).

### 4.1.4 Estado documental de los requerimientos

La especificación acumuló desfases respecto del código a medida que avanzó el desarrollo. La
auditoría de cierre los registró y los asignó a la actualización de la documentación; el capítulo no
los hereda. Los más relevantes para lo que sigue son cuatro: la especificación da por pendiente la
extracción IFC, que existe (sección 4.7.2); el criterio de RF‑19 cita una prueba que no cambia el
ancho de la tanquilla, mientras que la prueba que sí lo hace se escribió durante la corrección del
núcleo (sección 4.7.3); la matriz de trazabilidad nombra en algunos casos pruebas que no verifican lo
afirmado; y el encabezado del documento contradice su propio conteo mínimo de requerimientos (Tabla
4.10). Ninguno de estos desfases altera el conteo vigente de 42 requerimientos funcionales, diez no
funcionales y once casos de uso, que es el que se cita.

## 4.2 Modelo de datos

El problema de esta sección es persistir el catálogo, los precios y los presupuestos sin perder ni
precisión ni historia. Se presentan las entidades y cuatro decisiones del modelo.

El modelo de datos está documentado en [modelo_datos.md](../../modelo_datos.md) (anexo B) y se
implementó con SQLAlchemy (`core/models/entidades.py`). Materializa en persistencia los contratos del
núcleo sin ampliarlos: dieciséis entidades agrupadas en catálogo (`Partida`, `Insumo`,
`ComposicionAPU`, `Rendimiento`, `Ejecucion`), precios y su historial (`ListaPrecios`, `PrecioInsumo`,
`CambioPrecio`, `IncidenciaCambio`) y proyecto, presupuesto y auditoría (`Proyecto`, `Presupuesto`,
`DescarteVersion`, `PartidaPresupuestada`, `PuntoCurva`, `ItemComputo`, `Hallazgo`). La decimosexta,
`DescarteVersion`, se agregó en la corrección de la interfaz para marcar la versión de un presupuesto
que el usuario descarta tras actualizar sus precios (sección 4.6). Su tabla, `descarte_version`, es
aditiva: la función que crea el esquema la agrega a una base existente sin tocar las otras quince, de
modo que no exige migrar los datos
(`tests/integration/test_persistencia.py::test_crear_esquema_agrega_descarte_version_a_una_base_existente`).
El documento del modelo se declara
aprobado, pero la compuerta G0, que debía aprobarlo junto con la especificación y la arquitectura,
sigue pendiente del tutor; el capítulo lo trata como documento pendiente de esa aprobación.

**Los montos se guardan como texto.** SQLite no tiene un tipo decimal nativo: su tipo numérico
almacena un valor de coma flotante y lo reconvierte pasando por `float`, lo que admite pérdida de
precisión. Como el proyecto exige `Decimal` en todo lo monetario y dimensional, se escribió el tipo
`DecimalExacto` (`core/models/tipos.py`), que persiste cada `Decimal` como texto de hasta 40
caracteres y lo devuelve idéntico. El costo aceptado es que ordenar o filtrar por importe en SQL sería
lexicográfico; ninguna consulta del sistema lo hace. El cambio a PostgreSQL sustituiría ese tipo por
uno numérico nativo sin tocar los modelos (decisión de arquitectura 7 de
[arquitectura.md](../../arquitectura.md)).

**El versionado es híbrido.** Un presupuesto responde dos preguntas distintas: qué se firmó y cuánto
costaría hoy. Para la primera, `PartidaPresupuestada` congela el resultado del análisis de precios de
cada renglón y la fila del presupuesto copia los cuatro parámetros de costo con que se valoró. Para la
segunda, el presupuesto referencia la lista de precios que lo valoró, y esa lista es inmutable desde
que un presupuesto la usa: actualizar precios crea una lista nueva con vigencia posterior y registra
las diferencias en `CambioPrecio`. Reconstruir un presupuesto a su fecha es valorarlo con la lista
vigente en esa fecha, y `cargar_presupuesto` (`core/budget/persistencia.py`) comprueba que el
recálculo coincida con la instantánea con una tolerancia de 1 × 10⁻⁶ antes de devolverla. La prueba
`tests/integration/test_persistencia.py::test_precios_se_reconstruyen_a_fecha` sostiene el RNF‑02. El
esquema no versiona, en cambio, las líneas de una composición: cambiar el desglose de una partida
altera lo que se reconstruye a fechas pasadas, aunque no los presupuestos ya emitidos, que están
congelados. Se declaró como limitación en el §5 del modelo.

**Un insumo no puede tener dos precios el mismo día.** Al cargar la línea base se encontraron cuatro
pares de insumos con la misma descripción y precios distintos en la misma fecha: el agua, la pala, la
cinta métrica y el nivel de mano ([modelo_datos.md §6](../../modelo_datos.md)). La restricción de
unicidad de la lista de precios no los admite, y el modelo tiene razón: es un defecto del presupuesto
de partida, del mismo tipo que el criterio de depreciación no uniforme. Para no alterar la línea base
ni ocultar el defecto, `Catalogo.cargar_composicion` crea una variante del insumo con un sufijo en el
código y la devuelve en `ResumenCarga.variantes`. Ese mecanismo es la semilla de una regla candidata
R8, «precio uniforme del insumo», cuya incorporación es la decisión D2 del tutor. Los documentos
fuente numeran este defecto como «octavo» y también numeran así otro distinto, el de la unidad del
encofrado; aquí se los nombra por su contenido para no heredar esa ambigüedad.

**Un rendimiento medido exige la ejecución de la que proviene.** El contrato distingue el rendimiento
estimado, que declara el proyectista, del medido, observado en obra. El modelo lleva esa distinción a
la base con una clave foránea a `Ejecucion` y una restricción de comprobación
(`ck_rendimiento_medido_exige_ejecucion`) que impide guardar un rendimiento medido sin la ejecución que
lo respalda. Un rendimiento medido sin procedencia no sería auditable. Esta es, además, la línea por la
que el sistema se abre a la sombra digital en el sentido del capítulo II (§2.2.3): un flujo de
información que va de la obra al modelo, sin actuar sobre ella. El sistema registra y consulta esos
rendimientos, pero no los recibe de forma automática desde la obra.

## 4.3 Arquitectura

Esta sección explica cómo se organizó el código para que el núcleo de cálculo no dependa de ningún
dominio. Presenta las vistas con que se documentó la arquitectura, los contratos que forman la
frontera del núcleo, las guardias automáticas que la vigilan y los desfases de la documentación de
arquitectura.

### 4.3.1 Núcleo cerrado y adaptadores abiertos

La arquitectura se documentó con las vistas 4+1 ([arquitectura.md](../../arquitectura.md), anexo C),
cinco vistas complementarias del mismo sistema. La vista de escenarios dibuja los casos de uso y el
paquete que realiza cada uno. La vista lógica muestra los contratos y las clases y funciones del
núcleo, con sus firmas. La vista de proceso fija el orden real de las llamadas en la elaboración y la
actualización de precios, y dónde empieza y termina una transacción. La vista de desarrollo es el
diagrama de componentes y sus dependencias de importación, que hace visible que agregar un adaptador
no toca el núcleo. La vista física describe el despliegue local en un solo equipo. Las secciones
4.3.2 a 4.3.4 resumen lo esencial de esas vistas; los diagramas quedan en el anexo C y su paso a
figuras de la tesis está pendiente (sección 4.12).

El estilo es de puertos y adaptadores: el paquete `core/contracts/` define los tipos que cruzan las
fronteras entre paquetes; los adaptadores de dominio (`adapters/`) y los módulos de aprendizaje
automático (`ml/`) los implementan o los consumen; la interfaz (`ui/`) y la API (`api/`) orquestan. El
motor de costos es una función pura y la verificación no depende del aprendizaje automático, de modo
que el resultado central del trabajo no queda sujeto a la disponibilidad de datos para entrenar
modelos.

La regla de dependencia es estricta: ninguna importación sale de `core/` hacia otro paquete del
proyecto, y los adaptadores y los módulos de `ml/` solo importan `core.contracts`. Esa regla es la
forma operativa de la hipótesis central: si un dominio nuevo se incorpora escribiendo un adaptador
que solo conoce los contratos, el núcleo no tiene que cambiar para recibirlo.

### 4.3.2 Los contratos como única frontera

La Tabla 4.4 enumera los contratos y su papel. Son clases de datos inmutables que validan sus
invariantes al construirse (cantidades no negativas, rendimiento positivo, depreciación en el
intervalo (0, 1], unidades normalizadas) y no dependen de nada fuera de la biblioteca estándar de
Python.

**Tabla 4.4**
*Contratos de interfaz del núcleo (`core/contracts/`)*

| Módulo | Tipos | Papel |
|---|---|---|
| `unidades.py` | `normalizar_unidad`, `unidades_equivalentes` | única tabla de alias de unidades; «pieza» y «m» siguen siendo distintas, lo que permite a R3 detectar la incoherencia del caso |
| `dominio.py` | `Dominio` | civil, telecomunicaciones, industrial y sistemas |
| `item_computo.py` | `OrigenTipo`, `ItemComputo` | una cantidad de obra con su procedencia: `origen_id`, `origen_tipo` y, si viene de una regla, la expresión y sus parámetros |
| `adaptador.py` | `AdaptadorDominio` | el puerto de entrada: `extraer(fuente) -> list[ItemComputo]` |
| `apu.py` | `LineaMaterial`, `LineaEquipo`, `ModalidadManoObra`, `LineaManoObra`, `ComposicionAPU`, `ParametrosCosto`, `ResultadoAPU`, `TipoRendimiento`, `Rendimiento` | entrada y salida del motor de costos |
| `presupuesto.py` | `PartidaPresupuestada`, `PuntoCurva`, `Presupuesto` | la forma en memoria del presupuesto y su curva, que es la entrada de toda regla de verificación |
| `verificacion.py` | `Severidad`, `Hallazgo`, `ReglaVerificacion` | el contrato de las reglas: `evaluar(presupuesto) -> list[Hallazgo]` |

*Nota.* Elaboración propia a partir de `core/contracts/`. `ModalidadManoObra` y el campo
`LineaManoObra.modalidad` se agregaron durante el desarrollo del prototipo de composición (sección
4.4.3). En la versión del 23 de septiembre, la tabla de contratos de `NORMAS.md` y el diagrama de la
arquitectura no los mostraban (desfase registrado, Tabla 4.11); la última etapa del cierre los
incorporó el 28 de septiembre de 2026 a la tabla de contratos
([NORMAS.md §5](../../../NORMAS.md#5-contratos-de-interfaz-corecontracts)) y a los contratos de la
vista lógica ([arquitectura, §2.1](../../arquitectura.md#21-contratos-corecontracts-estables)).

Los contratos se declararon estables, y la regla del proyecto ante una aparente insuficiencia es
detenerse y documentarla en la bitácora en lugar de modificarlos. Esa regla produjo un registro de
insuficiencias que se rodearon sin tocar los contratos ([arquitectura.md §6.1](../../arquitectura.md)):
`Hallazgo` no lleva el código de la partida, y el informe construye un índice de `origen_id` a partida
para atribuirlo; `PuntoCurva` tampoco lo lleva, y el enlace entre período y partida viaja en la
etiqueta del período, entre corchetes; `Presupuesto` no guarda los parámetros de costo, y la
persistencia los copia en la fila del presupuesto; y `LineaEquipo` no permite declarar el criterio de
amortización, de modo que R6 verifica solo la mitad verificable de su enunciado. Estas
insuficiencias son resultados de la investigación sobre el diseño de los contratos, no defectos
ocultos.

El contrato se modificó una sola vez por una necesidad de dominio, y se hizo con expediente. Durante
el prototipo de composición se comprobó que `LineaManoObra` no podía expresar una mano de obra
remunerada por unidad de obra, «a destajo», que el requerimiento RF‑34 exige declarar por línea
([bitácora del hallazgo del destajo](../../bitacora/2026-09-16-P0-hallazgo-destajo.md)). La solución
adoptada fue un campo aditivo con valor por defecto `JORNAL`, que conserva el constructor anterior y
deja la línea base intacta. Es la decisión D9, recomendada al tutor y pendiente de su aval. La
auditoría de cierre registró, además, tres hallazgos cuya corrección exige cambiar contratos: la
conversión de los campos enumerados de `Rendimiento` e `ItemComputo`, la exigencia de `Decimal` y de
signo en montos y parámetros, y un evaluador de expresiones único en `core.contracts`. Sin el aval del
tutor no se aplicaron: quedan aceptados por decisión de arquitectura registrada, con su expediente en
la [bitácora de expedientes](../../bitacora/2026-09-23-C1-expedientes.md) y su código en la Tabla 4.11.

### 4.3.3 Las guardias automáticas

La hipótesis central no se sostiene por revisión manual sino por dos guardias que corren en cada
cambio. La primera es `tests/unit/test_arquitectura.py`, que analiza el árbol sintáctico de cada
archivo y falla si un adaptador o un módulo de `ml/` importa de `core` algo distinto de
`core.contracts`, si `core/` importa cualquier paquete de primer nivel del proyecto o si
`core/contracts` depende de algo ajeno a la biblioteca estándar. Al concluir la corrección del núcleo
reunía 66 casos, incluida una prueba que exige que la guardia cubra todo paquete de primer nivel
fuera del núcleo (`test_la_guardia_cubre_todo_paquete_de_primer_nivel_fuera_del_nucleo`), agregada
durante esa corrección. La segunda guardia es `scripts/guardia_nucleo.py`, que la integración continua
ejecuta sobre el rango de cambios de cada solicitud de fusión y de cada fusión en la rama principal
(`.github/workflows/ci.yml`): falla si un mismo cambio toca `core/` junto con `adapters/` o `ml/`, o si
una rama que incorpora un dominio cambia `core/`. La definición operativa de «rama de adaptador» que
usa esa guardia es la decisión D7 del tutor, pendiente.

Una tercera protección vigila el entorno de pruebas: ninguna prueba puede crear ni modificar la base
de trabajo `data/apu.db`, y `tests/unit/test_salvaguarda.py` demuestra que esa salvaguarda falla cuando
debe.

### 4.3.4 Proceso, despliegue y lo que la arquitectura documentada no refleja

El sistema es de un solo proceso y un solo hilo, se ejecuta en el equipo del usuario y guarda todo en
un archivo SQLite. La transacción pertenece a quien llama: las funciones de persistencia del núcleo
envían los cambios a la base sin confirmarlos (`flush` y no `commit`), para que el presupuesto pueda
formar parte de una operación mayor, como la actualización de precios. Las dependencias se instalan
con `uv sync` y se separan en extras por capa (`civil`, `ml`, `ui`, `api`), de modo que el equipo de
quien presupuesta no necesita `ifcopenshell` ni las bibliotecas del modelo de similitud para operar el
núcleo.

El documento de arquitectura tiene desfases con el código que el capítulo no hereda, todos
registrados en el inventario y asignados a la actualización de la documentación o a la corrección de
la interfaz (Tabla 4.11). Sus vistas de escenarios y de desarrollo describen una versión temprana del
sistema y nombran funciones que ya no existen; su vista física da por abierta la compuerta G1 y por
ausente el modelo IFC de muestra; y declara dos copias del evaluador de expresiones cuando el código
tiene cinco. Además, afirma que la página de composición de partidas (`ui/paginas/componer.py`) solo
dibuja la pantalla, cuando en la versión del 23 de septiembre esa página calculaba el precio unitario
con `calcular_apu`, persistía la composición y orquestaba la elaboración del presupuesto. La
corrección de la interfaz llevó después el cálculo a `ui/composicion.py` y la persistencia y la
orquestación a `ui/elaboracion.py`; el reparto resultante se incorpora al resincronizar el capítulo
(Tabla 4.10). Por esa razón, las figuras que se derivarían de
los diagramas de la arquitectura quedan pendientes hasta su regeneración (sección 4.12).

## 4.4 Motor de costos

Esta sección presenta la función que calcula el precio unitario, la forma en que se probó antes de
escribirla y su extensión a la mano de obra a destajo.

### 4.4.1 La fórmula

El motor de costos es la función `calcular_apu(composicion, parametros) -> ResultadoAPU`
(`core/costing/motor.py`). No accede a la base de datos ni conserva estado: recibe una composición y
los parámetros de costo y devuelve el desglose y el precio unitario. Todo el cálculo se hace con
`Decimal` y sin redondeos intermedios; el redondeo a dos decimales ocurre solo al presentar. La
fórmula vigente es la que documenta el propio motor en su cadena de documentación
(`core/costing/motor.py`, líneas 3 a 13). Se reproduce a continuación con dos precisiones de lectura
que el código confirma: el bono se multiplica solo por los obreros de las líneas a jornal, y en las
líneas a destajo el campo `sueldo` contiene el precio por unidad de partida.

```
materiales         = Σ cantidad × precio
equipos            = Σ (cantidad × precio × depreciación) / rendimiento
mano_obra_jornal   = ( Σ cantidad × sueldo × (1 + FCAS) + bono × Σ obreros a jornal ) / rendimiento
mano_obra_destajo  = Σ cantidad × precio por unidad de partida
mano_obra          = mano_obra_jornal + mano_obra_destajo
costo_directo      = materiales + equipos + mano_obra
con_administracion = costo_directo × (1 + administración)
precio_unitario    = con_administracion × (1 + utilidad)
```

En la versión del 23 de septiembre, la especificación del cálculo en `NORMAS.md` §4, que el capítulo
II fundamenta en §2.2.4, contenía solo la parte de jornal: el bono se multiplicaba allí por la suma de
todas las cantidades de mano de obra y no existía la línea de destajo. Las dos líneas nuevas provienen
de la decisión D9, recomendada al tutor y pendiente de su aval
([bitácora del hallazgo del destajo](../../bitacora/2026-09-16-P0-hallazgo-destajo.md)). Con todas las
líneas a jornal ambas formulaciones coinciden, porque entonces los obreros a jornal son todos los
obreros. El desfase de `NORMAS.md` §4 quedó registrado en el inventario (Tabla 4.11), y la última
etapa del cierre incorporó la fórmula con destajo a
[NORMAS.md §4](../../../NORMAS.md#4-especificación-del-cálculo-y-línea-base) el 28 de septiembre de
2026.

Con los parámetros del caso didáctico (FCAS de 6,00, bono de alimentación de 1,00 USD por obrero y
día, administración del 15 % y utilidad del 10 %, en cascada), el motor reproduce los cinco precios
unitarios de la línea base, como muestra la Tabla 4.5. El FCAS de 600 % proviene del propio caso
didáctico y no tiene fuente normativa: la convención colectiva de la construcción no define ese
factor, y el Colegio de Ingenieros de Venezuela, que publica factores de referencia en sus guías,
advierte que son solo referencias y que cada empresa debe calcular el suyo para cada obra (Colegio de
Ingenieros de Venezuela, 2018; véase el capítulo II, §2.3.2). Por eso se trata como parámetro
configurable del caso de estudio. Avalar esa declaración es la decisión D4 del tutor.

**Tabla 4.5**
*Precios unitarios de la línea base que el motor reproduce*

| Partida | Unidad | Rendimiento (unidades/día) | Precio unitario (USD) |
|---|---|---|---|
| Excavación | m³ | 80 | 8,60 |
| Tubería PVC 4" | pieza | 100 | 10,19 |
| Encofrado de madera | m² | 16 | 33,24 |
| Vaciado de concreto | m³ | 8 | 242,64 |
| Relleno compactado | m³ | 8 | 52,58 |

*Nota.* Elaboración propia. Valores del caso didáctico de la clínica, ejercicio académico ficticio;
el desglose línea por línea está una sola vez en `tests/fixtures/apu_linea_base.py` y la tolerancia
de la prueba es de ± 0,01 USD sobre el precio unitario.

### 4.4.2 Las pruebas antes que el motor

El motor se escribió para pasar pruebas que ya existían y que no se modificaron. La línea base
verificada, transcrita del ejercicio de la clínica y fijada en `tests/fixtures/apu_linea_base.py`, es
el producto del diagnóstico (OE1) y se escribió antes que el código: `tests/unit/test_costing.py`
fallaba con `ImportError` hasta que se implementó `core/costing/`
([bitácora del motor](../../bitacora/2026-08-29-I0.3-motor.md)). La línea base funciona así como
oráculo: define el resultado correcto con independencia de la implementación.

Los siete casos de ese archivo vigilan de forma explícita los dos errores más probables al implementar
la fórmula. El primero es dividir los materiales entre el rendimiento: su cantidad ya está referida a
la unidad de partida, y solo el costo diario de equipos y mano de obra se reparte entre las unidades
producidas en el día. Lo vigila `test_los_materiales_no_se_dividen_entre_el_rendimiento`. El segundo
es sumar los porcentajes de administración y utilidad en lugar de encadenarlos. Lo vigila
`test_administracion_y_utilidad_se_aplican_en_cascada`. Los cinco casos restantes son una misma
prueba parametrizada, `test_precio_unitario_reproduce_la_linea_base`, que compara cada precio unitario
con el de la línea base.

### 4.4.3 La modalidad a destajo

La modalidad a destajo se incorporó al motor con la decisión D9 descrita en la sección 4.3.2. La
legislación laboral venezolana entiende que el salario se estipula a destajo cuando se toma en cuenta
la obra realizada por el trabajador, sin usar como medida el tiempo empleado para ejecutarla (Ley
Orgánica del Trabajo, los Trabajadores y las Trabajadoras, 2012, art. 114). En consecuencia, una línea
a destajo expresa un precio por unidad de partida y no un sueldo diario: entra completa al costo
directo, sin FCAS, sin bono de alimentación y sin dividirse entre el rendimiento. Con todas las líneas
en jornal, el resultado es idéntico al del motor anterior; la prueba
`tests/unit/test_costing_destajo.py::test_la_linea_base_no_se_mueve` lo garantiza en cada corrida.

## 4.5 Presupuesto y curva de inversión

Esta sección muestra cómo se arma el presupuesto a partir de las cantidades, cómo la curva de
inversión cierra en el total por construcción y cómo se exporta y persiste el resultado.

### 4.5.1 El informe viaja con el presupuesto

El paquete `core/budget/` arma el presupuesto a partir de las cantidades, las composiciones y los
parámetros de costo. La función de entrega es `elaborar` (`core/budget/presupuesto.py`): valora cada
ítem con el motor, añade la curva de inversión si hay un plan de trabajo y audita siempre el
resultado. Devuelve un `ResultadoElaboracion` que lleva el presupuesto **y** el informe de auditoría,
de modo que no existe una forma de entregar el uno sin el otro. La función intermedia
`generar_presupuesto` sigue siendo pública: `elaborar` la usa como paso previo y los tres sembradores
de dominio (`scripts/seed_telecom.py`, `scripts/seed_industrial.py` y `scripts/seed_sistemas.py`), que
cargan en la base los catálogos y presupuestos de ejemplo, todavía la llaman sin informe. Su
documentación declara que no tiene valor de entrega, y esa situación quedó entre las limitaciones.

La corrección del núcleo hizo de `elaborar` el único lugar del protocolo «presupuesto valorado, plan
de trabajo, curva y auditoría». Antes, ese protocolo estaba escrito en cuatro sitios: la pantalla de
elaboración, la pantalla de composición, la ruta de la API que crea presupuestos y el sembrador del
caso de demostración (`scripts/seed_demo.py`). Ahora los cuatro pasan `plan=plan_secuencial` a
`elaborar` y el núcleo resuelve el resto. Los tres sembradores de dominio no formaban parte de ese
protocolo, porque solo necesitan el presupuesto valorado para cargar el catálogo. La misma corrección
implementó el flujo alternativo 3a de UC‑01: un ítem cuya partida no tiene composición en el catálogo
ya no aborta la elaboración, sino que queda pendiente, no suma al total y el informe lo declara con un
hallazgo de severidad ERROR y código `PENDIENTE`. Ese hallazgo lo agrega la elaboración y no la
auditoría, porque solo la elaboración sabe qué ítems no pudo valorar; quien llame directamente a la
función de auditoría no lo ve.

En la versión del 23 de septiembre, la interfaz y la API pedían las composiciones al catálogo antes de
llamar a `elaborar`, y el catálogo lanza una excepción ante una partida desconocida, de modo que ese
flujo alternativo no se alcanzaba de punta a punta desde ellas. Las dos etapas de corrección
siguientes lo cerraron: ambas piden ahora solo las composiciones de las partidas que el catálogo
tiene y dejan el resto a `elaborar`. Hasta el 28 de septiembre de 2026, la especificación redactaba
el orden inverso: el sistema proponía primero las partidas similares y el ítem quedaba pendiente
solo si no se aceptaba ninguna. Ese día, la última etapa del cierre reescribió el flujo con el orden
real. El sistema **elabora primero y propone después**: el
presupuesto se elabora con los ítems que tienen partida, el informe declara los pendientes y solo
entonces se proponen, para cada pendiente, las partidas del catálogo más parecidas a su descripción,
con el mismo emparejamiento de la normalización semántica (sección 4.10.1) en la interfaz y en la
API. En la pantalla «Elaborar un presupuesto», aceptar una propuesta reasigna el ítem a la partida
elegida y vuelve a elaborar el presupuesto; si no se acepta ninguna, el ítem sigue pendiente y el
informe lo sigue declarando. En la API, `POST /presupuestos` responde con los pendientes y sus
propuestas, y aceptar una equivale a reenviar el ítem con la partida elegida. Sin el extra de
aprendizaje automático instalado, el pendiente se declara igual, sin propuestas
(`tests/unit/test_ui_elaborar.py::test_sin_el_extra_el_pendiente_se_declara_sin_propuestas`). Lo
sostienen además las
pruebas `tests/unit/test_ui_elaborar.py::test_el_item_sin_partida_queda_pendiente_con_sus_propuestas`,
`tests/unit/test_ui_elaborar.py::test_aceptar_una_propuesta_vuelve_a_elaborar_sin_pendientes` y
`tests/integration/test_api.py::test_un_item_sin_partida_queda_pendiente_por_http`.

Quedaba la recarga. Los pendientes no se guardaban, y al recargar un presupuesto su informe se
reconstruía con una auditoría nueva que no los conocía, de modo que un presupuesto emitido con un
hallazgo `PENDIENTE` podía recargarse con un informe conforme. La corrección de la interfaz lo cerró
con un cambio del núcleo, justificado en un expediente previo
([expediente de la recarga con pendientes](../../bitacora/2026-09-24-C3-expedientes.md)).
`guardar_presupuesto` guarda cada pendiente como un ítem de cómputo del presupuesto sin renglón y
exige que los pendientes y los hallazgos `PENDIENTE` del informe se correspondan uno a uno.
`cargar_elaboracion` (`core/budget/persistencia.py`) los recupera y los vuelve a declarar, de modo que
el informe recargado es el emitido
(`tests/integration/test_recarga_con_pendientes.py::test_la_recarga_devuelve_el_informe_emitido_con_sus_pendientes`).
Esa función la usan las operaciones de la API que devuelven el informe y el libro de un presupuesto
guardado, y la actualización de precios arrastra los pendientes a la versión nueva (sección 4.6). Un
presupuesto guardado antes de ese cambio no tiene sus pendientes persistidos, y su recarga no los
inventa.

Los escenarios de sensibilidad (sección 4.11.2) sufrían la misma pérdida por otra vía, porque
recalculan solo los renglones valorados del presupuesto base. La corrección de la interfaz hizo que la
pantalla de escenarios cargara el base con `cargar_elaboracion` y avisara de sus pendientes
(`tests/unit/test_ui_escenarios.py::test_el_escenario_de_un_base_con_pendientes_los_declara`). La
última etapa del cierre, que incluyó ese cambio de la API, hizo lo mismo el 28 de septiembre de 2026
en la operación de escenarios de la API: su respuesta lista los pendientes del base en `pendientes_base`,
y ningún escenario los recalcula ni los suma
(`tests/integration/test_api_escenarios.py::test_los_escenarios_de_un_base_con_pendientes_los_declaran`).
El informe de auditoría de cada escenario, en cambio, no los incluye: hacerlo exigiría
modificar otra vez el núcleo (`core/budget/escenarios.py`), y ese punto queda entre las limitaciones
del trabajo. Todos estos puntos están registrados en el inventario (Tabla 4.11).

### 4.5.2 La curva cierra por construcción

En el caso didáctico, la curva de inversión cerraba en 1 575,50 USD, el 99,30 % del total de
1 586,61 USD, y los montos diarios del plan de trabajo no coincidían con los de sus partidas. El
módulo `core/budget/curva.py` hace imposible ese error: el monto del último período no se calcula
sumando fracciones, sino restando del total del presupuesto lo ya repartido. Aunque los montos
anteriores se redondeen a centavos, el acumulado final es el total literal. Antes de calcular,
`generar_curva` valida el plan y lanza `PlanInvalido` si menciona una partida que el presupuesto no
tiene o si las fracciones de alguna partida no suman exactamente uno. La regla R2 comprueba la
identidad entre el acumulado y el total; este módulo la garantiza.

El plan secuencial (`plan_secuencial`) asigna un período a cada partida. Durante la corrección del
núcleo se encontró que asignaba un período por renglón y no por código, de modo que dos renglones de
la misma partida sumaban una fracción de dos y hacían fallar la curva de la muestra civil tabular; se
corrigió para agrupar por código de partida en el orden de su primera aparición. Las etiquetas de los
períodos llevan los códigos de las partidas entre corchetes, por ejemplo `Dia 1 [LB-01-EXC]`, que es la
convención con la que R7 concilia el plan con el presupuesto (sección 4.8).

Las pruebas `tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61` y
`tests/integration/test_presupuesto_linea_base.py` reproducen el total de la línea base corregida
desde el catálogo persistido, con la curva cerrada al 100 %.

### 4.5.3 Exportación y persistencia

`exportar_excel` (`core/budget/excel.py`) escribe un libro con cuatro hojas: presupuesto, análisis de
precios, curva y auditoría. Los montos se redondean a dos decimales solo en la celda presentada, nunca
en el cálculo (RF‑08), con el número de decimales importado de `DECIMALES_PRESENTACION`. La operación
de redondeo para presentar está escrita en tres lugares, dos del núcleo y uno de `ml/`, duplicación
que quedó entre las limitaciones. La persistencia vive en `core/budget/persistencia.py`, que junto con
`core/catalog/mapeo.py` son las dos únicas fronteras entre los modelos de la base de datos y los
contratos. `guardar_presupuesto` rechaza un informe cuyo código no sea el del presupuesto: atribuir
los hallazgos a otro documento falsearía la auditoría.

## 4.6 Actualización masiva de precios (UC‑02)

La actualización de precios fue el primer caso de uso que se implementó después del flujo básico de
elaboración, por decisión de planificación del proyecto: es el caso de uso que ejercita el versionado
del modelo de datos y el que produce el historial de cambios de precio que después alimenta al módulo
predictivo. El problema de diseño era recalcular todos los análisis afectados por una lista nueva sin
editar ninguna composición y sin perder la capacidad de reconstruir la versión anterior. La solución
([bitácora de la actualización de precios](../../bitacora/2026-08-29-I1-actualizacion-precios.md))
aplica el versionado híbrido de la sección 4.2.

`core/catalog/precios.py` lee la lista en CSV o XLSX con todas las columnas como texto y construye cada
`Decimal` desde ese texto, de modo que ningún importe pasa por `float`. Empareja cada fila con un insumo
del catálogo por tipo, descripción y unidad normalizadas, con las funciones únicas de normalización del
sistema, porque quien escribe la lista no conoce los códigos internos. Los insumos que el catálogo no
conoce se reportan y no se crean: darlos de alta es una decisión del administrador. La lista nueva
copia todos los precios de la vigente y sobrescribe los del archivo, de modo que vale por sí sola para
reconstruir cualquier análisis.

`actualizar_precios` (`core/budget/actualizacion.py`) carga el presupuesto guardado, lo revalora con la
lista nueva, lo elabora y audita de nuevo, persiste un `CambioPrecio` por insumo modificado y una
`IncidenciaCambio` por partida afectada, y devuelve el comparativo por partida y total. El registro de
cambios es idempotente para un par de listas, porque ese historial es el que después alimenta al
módulo predictivo, y un historial duplicado sesgaría sus estimaciones. En la prueba de UC‑02, subir el
cemento y la arena de la línea base solo mueve el renglón del concreto: su precio unitario aumenta
30,17025 USD/m³, que es el incremento de materiales multiplicado por 1,15 y por 1,10, y su total
aumenta 50,082615 USD sobre 1,66 m³ (`tests/fixtures/actualizacion_uc02.py`). Los otros cuatro
renglones no cambian.

El tiempo de recálculo se midió con `scripts/medir_rnf03.py`. El 31 de agosto de 2026, en el equipo
de desarrollo, la revaloración de 100 partidas tardó 1,17 s. Al repetir la medición el 23 de
septiembre de 2026 en otro equipo, después de los cambios de la corrección del núcleo, tardó 1,34 s
([acta de revisión R2](../revisiones/R2-capitulo-4.md), observación T6.1). La cifra depende del equipo;
en ambas mediciones se cumple la meta de 5 s del RNF‑03, que el capítulo V evalúa.

Si el presupuesto base tiene ítems pendientes (sección 4.5.1), la versión nueva los conserva como
pendientes y su informe los vuelve a declarar, porque valorarlos corresponde a UC‑01 y no a UC‑02
(`tests/integration/test_recarga_con_pendientes.py::test_revalorar_arrastra_los_pendientes_del_base`).

El flujo alternativo 7a de UC‑02, descartar la versión nueva conservando el registro de cambios,
estaba pendiente en la versión del 23 de septiembre y se implementó en la corrección de la interfaz.
Como exigía un dato persistido nuevo, requirió un segundo cambio del núcleo en esa etapa, también
justificado en un expediente previo
([expediente del descarte de versiones](../../bitacora/2026-09-24-C3-expedientes.md)).
La función `descartar_version` (`core/budget/actualizacion.py`) registra la marca en la tabla
`descarte_version` (sección 4.2), y la pantalla de actualización de precios ofrece el botón
«Descartar version» para la versión que acaba de guardar. Es una marca y no un borrado: la versión
sigue guardada y se puede cargar, y el registro de `CambioPrecio` e `IncidenciaCambio` se conserva,
porque alimenta al módulo predictivo. Solo se descarta la última versión guardada del proyecto, una
sola vez y nunca el primer presupuesto. Lo sostienen las pruebas
`test_descartar_la_version_nueva_la_marca_y_conserva_el_historial`,
`test_con_tres_versiones_solo_se_descarta_la_ultima`, `test_una_version_no_se_descarta_dos_veces` y
`test_el_presupuesto_base_nunca_se_descarta`, de `tests/integration/test_actualizacion_precios.py`.
Quedan dos límites declarados. El esquema no registra de qué presupuesto salió cada versión, de modo
que la función no distingue una versión revalorada de un segundo presupuesto elaborado aparte en el
mismo proyecto; por eso la interfaz ofrece el botón solo para la versión recién guardada. Y ninguna
pantalla ni operación de la API muestra todavía la marca.

Otros dos aspectos quedan abiertos. Como la lista identifica al insumo por su descripción, una fila
actualiza todas las variantes homónimas descritas en la sección 4.2. Y cuando el precio anterior es
cero, la variación registrada es cero, porque la columna no admite nulos.

## 4.7 Adaptador civil: reglas paramétricas y extracción IFC

Esta sección presenta cómo se derivan las cantidades del dominio civil: primero con reglas
paramétricas sobre una tabla, luego desde un modelo IFC, y cómo el sistema recalcula cuando cambia una
dimensión.

### 4.7.1 Reglas paramétricas trazables

El adaptador civil responde a la segunda pregunta secundaria de la investigación: qué reglas
paramétricas derivan las cantidades de la geometría sin intervención manual. Cada regla es una
expresión de texto con una sola copia en `adapters/civil/reglas.py` (Tabla 4.6), y cada cantidad que
produce es un `ItemComputo` de origen `REGLA` que registra la expresión evaluada y los parámetros
usados. Con esa información, el núcleo puede volver a evaluar la cantidad desde su origen, y esa
reevaluación es la que hace posible la regla R1.

**Tabla 4.6**
*Reglas paramétricas del dominio civil*

| Regla | Expresión | Unidad |
|---|---|---|
| `REGLA_CONCRETO_TANQUILLA` | `n * (a**2 - (a - 2*e)**2) * h` | m³ |
| `REGLA_ENCOFRADO_TANQUILLA` | `n * (4*a*h + 4*(a - 2*e)*h)` | m² |
| `REGLA_EXCAVACION_TANQUILLA` | `n * (a + 2*sobreancho)**2 * (h + espesor_fondo)` | m³ |
| `REGLA_EXCAVACION_ZANJA` | `longitud * ancho * profundidad` | m³ |
| `REGLA_TUBERIA` | `longitud * (1 + desperdicio)` | m |
| `REGLA_VOLUMEN_TUBERIA` | `longitud * 0.7854 * diametro**2` | m³ |
| `REGLA_RELLENO` | `excavacion - concreto - volumen_tuberia` | m³ |

*Nota.* Elaboración propia a partir de `adapters/civil/reglas.py`. El factor 0,7854 aproxima π/4 y
está declarado en la propia expresión.

Con el ancho exterior, la altura y el espesor de pared del caso (0,80, 0,80 y 0,10 m), la regla del
concreto da 0,224 m³ por tanquilla y la del encofrado 4,48 m² por tanquilla, que son los valores
corregidos de las dos primeras inconsistencias de la línea base (`tests/unit/test_reglas_civil.py`).
La excavación de la tanquilla necesita dos datos que la memoria de cálculo del caso no fija, el
sobreancho de excavación y el espesor de fondo; la muestra los declara como supuestos de 0,10 m cada
uno en `data/samples/civil/README.md`, en lugar de ocultarlos en el código.

El evaluador de expresiones (`adapters/civil/evaluador.py`) recorre el árbol sintáctico y admite solo
operaciones aritméticas, nombres de parámetros y constantes numéricas, que convierte a `Decimal`;
rechaza llamadas, atributos y valores lógicos. No usa `eval`. El adaptador tabular
(`adapters/civil/tabular.py`) alimenta las reglas desde un CSV con una fila por tanquilla o zanja y
agrega el relleno como balance de las demás cantidades, con la expresión del balance y su tolerancia
como directivas para R5. Los códigos de partida no son constantes del adaptador: los recibe de quien
lo llama, porque pertenecen al catálogo.

### 4.7.2 Extracción desde IFC y la compuerta G1

`AdaptadorCivilIFC` (`adapters/civil/ifc.py`) lee un modelo IFC con `ifcopenshell` y devuelve una
cantidad por cada elemento que declare el conjunto de propiedades `Pset_APU`, con el código de la
partida, su descripción y su unidad. La cantidad no se toma de cualquier propiedad numérica: se busca,
entre las cantidades IFC del elemento, la del tipo que corresponde a la unidad declarada (volumen para
m³, área para m², longitud para m y conteo para pieza). Así el adaptador no depende del nombre que el
productor del modelo dé a la cantidad. El `origen_id` de cada ítem es el `GlobalId` del elemento, lo
que traza la cantidad hasta la geometría de la que salió. Este adaptador, junto con el motor de
costos, realiza la dimensión de costo del modelo BIM‑5D en el sentido del capítulo II (§2.2.2 y
§2.2.3): cada cantidad del presupuesto queda ligada, por el `GlobalId`, al elemento del modelo que la
produjo, y cada precio, a la composición que lo calcula.

La compuerta G1 exigía que las cantidades extraídas del modelo de muestra coincidieran con el cálculo
manual; de lo contrario, el adaptador IFC se sustituiría por la entrada tabular. Se cruzó **con
salvedad**: el adaptador extrae de `data/samples/tanquilla.ifc` exactamente los 0,224 m³ de concreto
del cálculo manual, pero ese modelo lo generó por programa `scripts/generar_tanquilla_ifc.py` y no lo
exportó un modelador BIM ([bitácora de la API y la extracción IFC](../../bitacora/2026-08-31-F1-api-3d.md)).
Por esa razón el RNF‑09, que pide archivos de al menos dos herramientas, queda parcial, y ejercitar el
adaptador con modelos exportados por modeladores comerciales o libres es trabajo pendiente. La
especificación y la arquitectura daban en esa versión, la del 23 de septiembre, la extracción IFC por
pendiente (desfase registrado, Tabla 4.11); el código y las pruebas `tests/unit/test_adapter_civil_ifc.py` y
`tests/unit/test_generador_ifc.py` muestran que existe.

La primera pregunta secundaria de la investigación, sobre el nivel de desarrollo que necesita el
modelo, recibe aquí una respuesta parcial y operativa: el adaptador exige que cada elemento
presupuestable declare `Pset_APU` y una cantidad IFC del tipo de su unidad. Con un modelo generado por
programa, esa condición es suficiente para una extracción exacta; si lo es también con modelos de
modeladores comerciales depende de la prueba pendiente descrita en el párrafo anterior, y la respuesta
completa se presenta en el capítulo V.

### 4.7.3 Recalcular ante un cambio de alcance (UC‑04)

Como las cantidades conservan su expresión y sus parámetros, cambiar una dimensión y volver a elaborar
recalcula el presupuesto sin intervención manual. La prueba
`tests/unit/test_recalculo_uc04.py::test_uc04_recalcula_precios_curva_y_auditoria_al_cambiar_el_ancho`,
escrita durante la corrección del núcleo, cambia el ancho de las tanquillas y comprueba que cambian el
concreto, el encofrado y la excavación, y ninguna otra partida; que los ítems nuevos traen la
expresión y el parámetro cambiado; que la curva se regenera cerrando en el total nuevo; y que la
verificación se ejecuta de nuevo. El paso 5 de UC‑04, el diferencial por partida (RF‑20), no está
implementado (sección 4.1.2). En la versión del 23 de septiembre tampoco lo estaban sus flujos
alternativos: informar que un parámetro no participa en ninguna regla, emparejar por `GlobalId` al
reimportar un modelo IFC y conservar el valor anterior ante una cantidad negativa. La corrección de
los adaptadores los implementó después en `adapters/civil/recalculo.py`
(`tests/unit/test_recalculo_civil.py`); su descripción se incorpora al resincronizar el capítulo
(Tabla 4.10).

## 4.8 Verificación R1–R7 y el informe de auditoría

Esta sección presenta las siete reglas de verificación, la decisión que les permite verificar sin
conocer ningún dominio y la forma en que se gradúan y se informan sus hallazgos.

### 4.8.1 Una regla por inconsistencia

El paquete `core/verification/` implementa las siete reglas de verificación como clases que
implementan el contrato `ReglaVerificacion`. Cada una recibe un `Presupuesto` y devuelve una lista de
hallazgos con severidad, descripción, impacto cuantificado cuando corresponde y los `origen_id`
involucrados. La Tabla 4.7 relaciona cada regla con lo que comprueba y con la inconsistencia del caso
didáctico que detecta.

**Tabla 4.7**
*Reglas de verificación y su correspondencia con el caso didáctico*

| Regla | Clase | Qué comprueba | Inconsistencia del caso que detecta |
|---|---|---|---|
| R1 | `TrazabilidadGeometrica` | que cada cantidad derive de una regla declarada y coincida con su reevaluación | encofrado 5,92 frente a 4,48 m² por tanquilla; concreto 0,415 frente a 0,224 m³ por tanquilla |
| R2 | `CierreCurvaInversion` | que el acumulado de la curva sea el total del presupuesto | curva que cierra en 1 575,50 USD (99,30 %) frente a 1 586,61 USD |
| R3 | `CoherenciaDimensional` | que la unidad del cómputo sea equivalente a la del análisis de precios | tubería computada en «mts» con análisis por pieza |
| R4 | `CorrespondenciaEspecificaciones` | que diámetros, materiales y espesores del cómputo coincidan con el análisis | memoria con 3/4" en un sistema de 4" |
| R5 | `BalanceVolumetrico` | que el relleno sea la excavación menos el concreto y la tubería, dentro de una tolerancia declarada | relleno de 1,30 m³ frente a ≈ 8,6 m³ esperados |
| R6 | `CriterioDepreciacion` | que un mismo equipo lleve el mismo factor de depreciación en todos los análisis | vehículo con 0,03 en la tubería y 1,00 en los demás |
| R7 | `ConciliacionPresupuestoPlan` | que cada monto del plan de trabajo coincida con el de su partida | montos diarios menores que los de sus partidas, raíz de la brecha de R2 |

*Nota.* Elaboración propia a partir de `core/verification/reglas.py` y de
[linea_base.md §5](../../linea_base.md).

La prueba de aceptación crítica, `tests/integration/test_auditoria_7_de_7.py`, construye un
presupuesto de prueba que reproduce las siete inconsistencias
(`tests/fixtures/presupuesto_auditado.py`) y exige que el sistema las detecte todas. Es el indicador 1
de la tesis, 7 de 7, cuyo análisis corresponde al capítulo V. La misma prueba comprueba los dos
hallazgos adicionales de la transcripción (la unidad del encofrado, que detecta R3, y la conciliación
diaria del plan, que detecta R7), que todo hallazgo de partida referencie un origen trazable y que el
presupuesto corregido no tenga errores. Hoy el presupuesto de terceros se construye en memoria en esa
prueba: ni la interfaz ni la API ofrecen todavía una ruta para importar un presupuesto tabular ajeno.

### 4.8.2 El núcleo no conoce el dominio

La decisión de diseño más importante de la verificación es que la regla que produjo una cantidad y el
balance que la relaciona con otras son **datos del ítem**, no código del núcleo. La expresión viaja
en `ItemComputo.regla` con sus parámetros; el balance del relleno y su tolerancia, en las claves
`_balance` y `_tolerancia` de las especificaciones; la unidad tal como la escribió el autor, en
`_unidad_original`. El núcleo solo sabe evaluar aritmética (`core/verification/expresiones.py`) y leer
una convención de claves con prefijo (`core/verification/directivas.py`). Si R1 y R5 conocieran las
fórmulas del drenaje, el núcleo conocería el dominio civil y la hipótesis central sería falsa; con esta
decisión, un dominio nuevo declara sus expresiones y el núcleo las reevalúa sin una rama nueva. Esta
es la respuesta que el sistema da a la cuarta pregunta secundaria: las verificaciones que aporta el
conocimiento geométrico son posibles porque cada cantidad lleva consigo la regla que la produjo. La
documentación funcional de los programas de presupuesto de uso regional no describe una comprobación
de las cantidades contra la geometría del proyecto (DataLaing, s.f.; IP-3 Software, s.f.; Lulo
Software, s.f.) [verificación pendiente], como se expuso en el capítulo I (§1.1.1).

El precio de esa decisión es la duplicación del evaluador. El núcleo no puede importar un adaptador y
un adaptador solo puede importar los contratos, de modo que cada lado tiene el suyo: hoy existen cinco
copias, la del núcleo y una por adaptador. La prueba
`tests/unit/test_verification.py::test_las_reglas_civiles_son_evaluables_por_el_nucleo` evalúa cada
regla civil con el evaluador del adaptador y con el del núcleo y exige el mismo `Decimal`, de modo que
una divergencia se detecta el día que aparezca. La solución de fondo, un evaluador único en
`core.contracts`, cambia un contrato y espera el aval del tutor.

### 4.8.3 Severidad, impacto y el informe

El contrato define cuatro severidades: INFO, ADVERTENCIA, ERROR y CRÍTICO. Ninguna regla lanza
excepciones por los datos: a una regla que le falta un dato para evaluarse (un parámetro ausente, una
referencia de balance que no se resuelve) la informa como INFO «regla no evaluable»; un dato inválido
(una expresión mal escrita, un valor que no es `Decimal`) es un ERROR; y R2 y R7 se declaran «no
aplicables», también como INFO, cuando el presupuesto no trae plan de trabajo. Esa distinción entre el
dato ausente y el dato inválido se ajustó durante la corrección del núcleo para cumplir RF‑23 y los
flujos 2a y 3a de UC‑05: tratar también como INFO el dato inválido habría dejado como conforme un
presupuesto con datos corruptos. El impacto es siempre una magnitud no negativa, en la moneda del
presupuesto cuando la regla puede cuantificar dinero; el sentido de la desviación va en los valores
observado y esperado del hallazgo.

`auditar` (`core/verification/informe.py`) recorre las siete reglas, concatena sus hallazgos y
construye un `InformeAuditoria` inmutable que los ordena por severidad descendente, indexa cada
`origen_id` con su partida y se presenta en Markdown o en la hoja de auditoría del libro de Excel.
Como `elaborar` lo invoca siempre, el informe existe antes de que alguien lo pida.

Dos reglas dependen de decisiones del tutor. R7 es una decisión de diseño de este proyecto, porque las
Bases del anteproyecto listan cinco reglas; su valor empírico está en que explica la brecha de 11,11
USD de la curva, pero su aprobación como regla de fondo es la decisión D1. La regla candidata R8,
«precio uniforme del insumo», es la decisión D2 y no está implementada. R6 verifica, además, solo la
mitad de su enunciado, la unicidad del factor por equipo, porque el contrato no permite declarar el
criterio de amortización (sección 4.3.2).

## 4.9 Extensibilidad a otros dominios

Esta sección pone a prueba la hipótesis central: presenta los adaptadores de tres dominios que el
núcleo no conocía y la evidencia de que incorporarlos no cambió el núcleo.

### 4.9.1 Tres adaptadores sobre el mismo núcleo

Después del dominio civil se escribieron tres adaptadores para dominios que el núcleo no conocía:
telecomunicaciones, mantenimiento industrial y sistemas de información. Una etapa posterior, dedicada
al desarrollo multidominio, los completó con catálogos, presupuestos y auditorías propios
([bitácora del desarrollo multidominio](../../bitacora/2026-09-02-sprint-multidominio.md)). La Tabla
4.7 resume los cuatro adaptadores.

**Tabla 4.8**
*Adaptadores de dominio y sus fuentes*

| Adaptador | Fuente de cantidades | Origen de las cantidades | Regla declarada | Caso de aplicación |
|---|---|---|---|---|
| `adapters/civil` | CSV de tanquillas y zanja; modelo IFC | `REGLA` (tabular); `IFC` | las siete de la Tabla 4.6 | drenaje de la clínica, ejercicio académico ficticio |
| `adapters/telecom` | CSV de topología (nodos y enlaces) | `CSV` (nodos); `REGLA` (enlaces) | `longitud_m * (1 + reserva)` | dos presupuestos ARENAZA, ejercicios académicos ficticios |
| `adapters/industrial` | registro de activos con frecuencia de intervención | `REGLA` | `frecuencia_anual * horizonte_anios` | `MNT-001`, caso construido para el proyecto |
| `adapters/sistemas` | alcance funcional por módulo y caso de uso | `REGLA` | `4*entradas + 5*salidas + 4*consultas + 10*archivos + 7*interfaces` (puntos de función) | `SIS-001`, caso construido para el proyecto |

*Nota.* Elaboración propia a partir de `adapters/*/adaptador.py`, `adapters/civil/` y de la nota
sobre la naturaleza de los datos de `NORMAS.md` §1.

Cada adaptador subclasifica `AdaptadorDominio`, declara su dominio e implementa `extraer` devolviendo
ítems con un `origen_id` tomado de su fuente. Ninguno importa de `core` otra cosa que los contratos.
Con los catálogos del desarrollo multidominio, el sistema reproduce con diferencia cero los totales de
los dos presupuestos ARENAZA (1 109,29 y 5 410,73 USD) y elabora `MNT-001` (18 124,09 USD) y
`SIS-001` (16 093,89 USD); lo comprueban `tests/integration/test_presupuesto_arenaza.py`,
`tests/integration/test_presupuesto_industrial.py` y `tests/integration/test_presupuesto_sistemas.py`.
El caso de telecomunicaciones tiene, además, una inconsistencia propia que se presentó en el capítulo
I, el tubo corrugado con 80 m en el cómputo y 90 m en el presupuesto, y la regla R1 la detecta con su
`origen_id` sin que el núcleo sepa qué es un tubo corrugado
(`tests/integration/test_auditoria_arenaza.py`). Estos resultados demuestran que el mecanismo funciona
sobre cuatro casos didácticos o construidos; no se generalizan estadísticamente, y la validación
con presupuestos reales no forma parte del alcance (capítulo I, §1.5.2).

### 4.9.2 La evidencia de que el núcleo no cambió

Al terminar los tres adaptadores, una comprobación automática del plan de desarrollo verificó que
ninguna rama que incorporaba un adaptador había tocado `core/`, y al cerrar el desarrollo multidominio
la diferencia del núcleo entre el comienzo y el final de esa etapa quedó vacía con los cuatro dominios
poblados ([bitácora de la primera versión del sistema](../../bitacora/2026-08-29-sprint-alpha.md) y bitácora del
desarrollo multidominio). El núcleo sí cambió después, por dos motivos que no son la incorporación de
un dominio: el prototipo de composición modificó siete archivos de `core/` para la modalidad a destajo
y la composición de partidas, con el expediente de la decisión D9
([bitácora del prototipo](../../bitacora/2026-09-16-sprint-prototipo.md)), y la corrección del núcleo
resolvió los hallazgos que registró la auditoría de cierre. En ambos casos la guardia del núcleo
comprobó que ningún cambio mezclara `core/` con `adapters/` o `ml/`. La distinción importa para
interpretar el indicador 4: la hipótesis afirma que el núcleo no cambia **al agregar un dominio**, no
que el núcleo sea inmutable.

El costo de la extensibilidad es la duplicación ya descrita del evaluador de expresiones, que cada
adaptador reescribió con los operadores que su dominio necesita, y la de la función que interpreta las
especificaciones en los cuatro adaptadores tabulares, que quedó entre las limitaciones. La guía para
que un tercero escriba un adaptador nuevo está en el [manual técnico §4](../../manual_tecnico.md)
(anexo E). Si la extensibilidad se presenta como objetivo específico propio (OE7) o como resultado
complementario del diseño del núcleo es la decisión D3 del tutor. Si se elige la variante A de los
objetivos, esta sección aporta la evidencia de la sexta pregunta secundaria del capítulo I, sobre la
extensión del modelo a otros dominios sin modificar su núcleo; en la variante B, la misma evidencia se
presenta como resultado complementario. El desarrollo descrito es el mismo en ambos casos.

## 4.10 Módulos de aprendizaje automático

Los tres módulos de `ml/` reciben datos planos, no conocen la base de datos y solo pueden importar los
contratos del núcleo. La interfaz y la API los invocan con importación perezosa, de modo que el sistema
funciona sin el extra `ml`, y el núcleo nunca los importa. Esta sección presenta la normalización de
partidas, la detección de atípicos y la predicción de precios con su compuerta de degradación.

### 4.10.1 Normalización semántica de partidas (UC‑03)

`ml/normalization/normalizador.py` propone, para una descripción de partida escrita en texto libre, las
tres partidas del catálogo más parecidas. Vectoriza las descripciones con el modelo multilingüe
`paraphrase-multilingual-MiniLM-L12-v2` de la biblioteca `sentence-transformers`, que obtiene
representaciones de oraciones comparables por la similitud del coseno (Reimers y Gurevych, 2019) y las
extiende a varios idiomas por destilación de conocimiento (Reimers y Gurevych, 2020). No requiere datos
etiquetados ni entrenamiento. Por debajo de un umbral declarado de similitud de 0,5 no se propone nada,
y el usuario puede crear la partida desde cero. El umbral se calibró con la prueba de aceptación de
RF‑17, que exige reconocer en el primer puesto al menos el 80 % de las partidas de la línea base
parafraseadas
(`tests/unit/test_normalizacion.py::test_acepta_al_menos_80_por_ciento_del_presupuesto_conocido`); en
la corrida con que se cerró ese módulo reconoció las cinco
([bitácora de la normalización](../../bitacora/2026-08-31-I2-normalizacion.md)). El puntaje es un
número de coma flotante, y es la única excepción justificada a la regla del `Decimal`: es una
similitud adimensional, no una cantidad de obra ni un monto. La primera ejecución descarga el modelo y
lo guarda en la caché local, que es una de las dos excepciones declaradas del RNF‑08; la otra, la
biblioteca three.js que el navegador carga para el Visor 3D, se declaró el 28 de septiembre de 2026
([ERS §3.3](../../ERS.md#33-requisitos-no-funcionales-isoiec-25010), fila RNF‑08; nota de la
Tabla 4.3).

### 4.10.2 Detección de valores atípicos

`ml/anomaly/detector.py` aplica el bosque de aislamiento, que aísla las observaciones raras con árboles
de partición aleatoria (Liu et al., 2008), a dos usos: marcar las variaciones de precio que se apartan
del historial y juzgar si un rendimiento introducido se aparta del observado para su partida. El
bosque se ajusta con semilla fija para que el mismo historial produzca siempre el mismo veredicto, y
con menos de ocho observaciones el módulo se abstiene en lugar de emitir un juicio estadístico sobre un
puñado de números. La advertencia normativa del registro de rendimientos (RF‑27) no depende de este
módulo: la calcula el núcleo por rango observado, y la API responde con esa advertencia sin impedir
nunca el registro (`tests/integration/test_api_rendimientos.py`); el veredicto del bosque es un
complemento opcional.

### 4.10.3 Predicción de precios y la compuerta G2

La tercera pregunta secundaria pregunta qué técnica de aprendizaje automático conviene cuando los datos
son escasos. La investigación la respondió antes de conocer los datos, con la tabla de degradación de
la compuerta G2: más de 200 registros por dominio permiten potenciación de árboles con XGBoost (Chen y
Guestrin, 2016), contrastada con bosques aleatorios (Breiman, 2001); entre 50 y 200, razonamiento
basado en casos (Aamodt y Plaza, 1994); con menos de 50, un sistema de reglas con análisis de
sensibilidad declarado como limitación. `ml/prediction/reglas.py` convierte esa tabla en código en la
función `tecnica_para`.

El conteo de registros por dominio dio 5 en civil, 40 en telecomunicaciones, 4 en industrial y 9 en
sistemas ([resultados_ml.md](../../resultados_ml.md)). Todos quedan por debajo de 50, de modo que la
técnica es el sistema de reglas: el precio estimado de una partida es su precio base multiplicado por
uno más la media de las variaciones del historial de cambios de precio, y el análisis de sensibilidad
recorre la variación mínima y la máxima observadas. La regla no conoce la composición del análisis; su
error frente al motor de costos, que actúa como verdad de terreno, es lo que miden el MAPE, el RMSE y
el R² que el capítulo V presenta como resultado de la degradación declarada, no como logro del
aprendizaje automático. Esos conteos y métricas provienen de casos didácticos o construidos, no se
generalizan estadísticamente y no sustituyen la validación con presupuestos reales, que queda fuera
del alcance (capítulo I, §1.5.2). El contraste con el precio construido emite un hallazgo de severidad
ADVERTENCIA cuando la desviación sale del rango de la clase 3 que se adoptó, de −20 % a +30 %, tomado
de la práctica 18R‑97 (AACE International, 2020). Si el caso debe clasificarse con esa práctica o con
la 56R‑08, específica de edificación y más estricta (AACE International, 2012), es una decisión del
tutor que puede cambiar ese rango.

## 4.11 Interfaz y API

Esta sección presenta las dos vías de acceso al sistema: la interfaz gráfica para quien presupuesta y
la API para otros programas.

### 4.11.1 La interfaz

La interfaz es una aplicación Streamlit de varias páginas (`ui/app.py`) con nueve pantallas,
enumeradas en la Tabla 4.9. La interfaz llama al núcleo y a los adaptadores directamente, sin pasar por
la API. El modo entrega, activado con una variable de entorno, oculta las cuatro pantallas de
investigación y deja las de trabajo.

**Tabla 4.9**
*Pantallas de la interfaz*

| Pantalla | Caso de uso | Sección |
|---|---|---|
| Actualización de precios | UC‑02 | trabajo |
| Catálogo | consulta de partidas e insumos | trabajo |
| Componer partida | UC‑10 y UC‑11 | trabajo |
| Elaborar presupuesto | UC‑01, con la auditoría de UC‑05 incluida | trabajo |
| Histórico de precios | consulta de `CambioPrecio` | trabajo |
| Escenarios | UC‑08 | investigación |
| Partidas similares | UC‑03 | investigación |
| Simulador de listas | apoyo a UC‑02 | investigación |
| Visor 3D | visualización del modelo IFC | investigación |

*Nota.* Elaboración propia a partir de `ui/app.py` (`PAGINAS`), en la versión del 23 de septiembre
de 2026. La corrección de la interfaz agregó después la pantalla de Inicio (UC‑12), que se incorpora
al resincronizar el capítulo (Tabla 4.10).

La pantalla de composición permite declarar una partida con sus tablas de materiales, equipos y mano
de obra (con la modalidad por línea), ver el precio unitario en vivo calculado por el motor, apoyarse
en los listados de precios de julio de 2026 del programa MaPreX (DataLaing, s.f.), incorporados al
repositorio en `data/precios/maprex_2026-07/`, para sugerir descripciones y precios que siempre quedan
editables (RF‑35), y guardar la composición solo si el rendimiento se declaró con sus condiciones
(RF‑33). La lógica de composición se probó sin Streamlit en `ui/composicion.py`
(`tests/unit/test_composicion.py`) y la pantalla con el arnés de pruebas de Streamlit
(`tests/unit/test_ui_componer.py`). Como se señaló en la sección 4.3.4, en la versión del 23 de
septiembre esa pantalla concentraba además cálculo, persistencia y orquestación; la corrección de la
interfaz los separó después (Tabla 4.10).

El recorrido guiado desde una pantalla de Inicio (UC‑12), con el caso abierto visible en toda pantalla
y un paso siguiente en cada una, estaba especificado y sin implementar en la versión del 23 de
septiembre. La corrección de la interfaz lo implementó después; su descripción se incorpora al
resincronizar el capítulo (Tabla 4.10). Su medición con personas (RNF‑10, caso CP‑07) se hará después, en la etapa de mediciones con
usuarios.

### 4.11.2 La API

La API (`api/main.py`, FastAPI) expone 18 operaciones sobre 14 rutas, agrupadas en catálogo, cómputos
por dominio, listas de precios, presupuestos y rendimientos. Crear un presupuesto
(`POST /presupuestos`) elabora, audita y guarda en una sola operación; el informe se consulta en
Markdown y el libro en Excel por operaciones propias; la actualización de precios y los escenarios
tienen operaciones sobre el presupuesto; y el registro de ejecuciones y rendimientos medidos realiza
UC‑06, respondiendo con la advertencia de rango cuando corresponde. Los montos viajan siempre como
texto en la frontera JSON (`api/esquemas.py`), porque serializarlos como números los haría pasar por
`float`. El esquema OpenAPI se exporta a `docs/api.json` con `scripts/exportar_openapi.py`, y la
integración continua falla si el archivo publicado difiere del que genera el código
(`tests/unit/test_openapi.py` y el paso de artefactos reproducibles de `.github/workflows/ci.yml`).

Los escenarios de sensibilidad (UC‑08) se calculan en memoria y no se persisten: promover un escenario
a presupuesto equivale a la actualización de precios de UC‑02, que ya existe
([bitácora de los escenarios](../../bitacora/2026-08-31-UC08-escenarios.md)). Validar que ese diseño
cumple la postcondición de UC‑08 es la decisión D6 del tutor. Los casos de uso UC‑04, UC‑06 y UC‑07 no
tienen pantalla propia y se alcanzan por las funciones del núcleo, la API o los scripts.

## 4.12 Síntesis del capítulo y pendientes

El desarrollo produjo un núcleo que calcula, presupuesta y audita sin conocer ningún dominio, cuatro
adaptadores que le entregan cantidades trazables y tres módulos de aprendizaje automático que operan
en los márgenes sin condicionar el resultado central. Las decisiones de diseño que sostienen la
propuesta son pocas y se repiten a lo largo del capítulo: cada cantidad lleva su procedencia y la regla
que la produjo; el informe de auditoría viaja con el presupuesto; la curva cierra por construcción; los
precios se versionan sin editar lo emitido; y el núcleo solo se comunica con el resto a través de
contratos vigilados por pruebas. La evaluación de esas decisiones frente a los indicadores de la tesis
se presenta en el capítulo V.

La Tabla 4.10 reúne lo que el capítulo no pudo cerrar, con su motivo.

**Tabla 4.10**
*Pendientes del capítulo IV*

| Pendiente | Motivo | Dónde se resuelve |
|---|---|---|
| Figuras del capítulo: al menos el diagrama de componentes (vista de desarrollo) y el diagrama entidad‑relación; además, el diagrama de secuencia de la elaboración y capturas de la interfaz | Los diagramas de origen están en `docs/arquitectura.md` y `docs/modelo_datos.md`, que tenían desfases registrados (Tabla 4.11), corregidos en la última etapa del cierre; las figuras se generan de su versión corregida. `docs/tesis/figuras/` todavía no existe. La versión final no se aprueba sin las dos primeras | actualización de la documentación y una sesión de redacción posterior |
| Resincronización del capítulo con la versión congelada del software (`v1.0-tesis`) | El capítulo describe la versión del 23/09/2026, salvo lo que se puso al día en las secciones 4.2, 4.5.1 y 4.6. Las correcciones siguientes implementaron además la pantalla de Inicio con el recorrido guiado (UC‑12, RF‑36 a RF‑43), la separación de la pantalla de composición y los flujos alternativos de UC‑04 en el adaptador civil (`adapters/civil/recalculo.py`), que las secciones 4.1, 4.3.4, 4.7.3 y 4.11 mencionan sin describirlos, y la actualización de la documentación corrigió además los desfases documentales de las secciones citadas en las convenciones | sesión de redacción después del congelamiento |
| Aprobación de la especificación, el modelo de datos y la arquitectura (compuerta G0) | Depende del tutor académico designado | [paquete para el tutor](../revisiones/2026-09-paquete-tutor.md), punto G0 |
| Decisiones D1 (R7), D2 (R8), D3 (OE7), D4 (FCAS), D5 (RF‑16), D6 (UC‑08), D7 (rama de adaptador), D8 (BIM‑5D) y D9 (destajo) | Dependen del tutor; el capítulo describe lo implementado y declara la decisión como pendiente | [paquete para el tutor](../revisiones/2026-09-paquete-tutor.md) |
| Clasificación AACE 18R‑97 o 56R‑08 | Depende del tutor; afecta el rango del contraste de la sección 4.10.3 | [paquete para el tutor](../revisiones/2026-09-paquete-tutor.md), punto AACE |
| Tres cambios de contrato (enumerados, `Decimal` y signo, evaluador único), con el evaluador único también en los adaptadores | Cambian contratos estables y esperan el aval del tutor; la corrección de los adaptadores no los tocó por esa razón | [bitácora de expedientes](../../bitacora/2026-09-23-C1-expedientes.md) y paquete para el tutor |
| Citas de la norma IEEE 830, de las vistas 4+1 y de la norma ISO/IEC 25010 | Tienen entrada en `docs/tesis/referencias.md` como pendientes de verificar: el repositorio no contiene sus datos bibliográficos y no se completan de memoria | sesión de referencias antes de la versión final |

*Nota.* Elaboración propia a partir del [inventario del cierre](../../auditoria/2026-09-inventario.md)
y del paquete para el tutor.

La Tabla 4.11 conserva la trazabilidad de los desfases y limitaciones que el capítulo menciona sin
código, hacia su registro en el inventario de la auditoría de cierre.

**Tabla 4.11**
*Registro de los desfases y limitaciones mencionados en el capítulo*

| Sección | Desfase o limitación | Registro | Etapa que lo atiende |
|---|---|---|---|
| 4.1.1, 4.1.4 | La especificación promete en la interfaz los once casos de uso | INV‑030 | actualización de la documentación |
| 4.1.2 | RF‑16 tenía estados distintos en la especificación y el plan de pruebas | INV‑027 | actualización de la documentación |
| 4.1.2, 4.7.3 | RF‑20 no implementado; RF‑19 citaba una prueba que no existía | INV‑011 (cerrado en el código) | corrección del núcleo; documentos en la actualización de la documentación |
| 4.1.3, 4.10.1 | La especificación declaraba una sola excepción del RNF‑08 y el Visor 3D carga three.js desde un servidor externo | INV‑077 (declarada el 28/09/2026 en la fila RNF‑08 de la especificación; su estado final lo registra el cierre de la última etapa) | actualización de la documentación |
| 4.1.4 | La matriz de trazabilidad cita pruebas que no verifican lo afirmado | INV‑026 | actualización de la documentación |
| 4.1.4 | El encabezado de la especificación contradice su conteo mínimo | INV‑063 | actualización de la documentación |
| 4.1.4, 4.7.2 | Especificación y arquitectura dan la extracción IFC por pendiente | INV‑028 | actualización de la documentación |
| 4.2 | El modelo de datos se declara aprobado con G0 pendiente | INV‑061 | actualización de la documentación |
| 4.2 | Dos defectos distintos numerados como «octavo» | INV‑064 | actualización de la documentación |
| 4.3.2 | La tabla de contratos y el diagrama omitían la modalidad de mano de obra | INV‑057 (incorporada el 28/09/2026 a `NORMAS.md` §5 y a la arquitectura §2.1; su estado final lo registra el cierre de la última etapa) | actualización de la documentación |
| 4.3.2, 4.8.2 | Enumerados, `Decimal` y signo, y evaluador único en los contratos | INV‑001, INV‑002, INV‑006 (aceptados por decisión de arquitectura registrada) | aval del tutor |
| 4.3.3 | La guardia de arquitectura no cubría `scripts` ni `tests` | INV‑010 (cerrado) | corrección del núcleo |
| 4.3.3 | La salvaguarda de la base de trabajo | INV‑065 (cerrado) | corrección del núcleo |
| 4.3.4 | Vistas de escenarios y de desarrollo desactualizadas | INV‑029 | actualización de la documentación |
| 4.3.4, 4.8.2, 4.9.2 | La arquitectura declara dos copias del evaluador y hay cinco | INV‑058 | actualización de la documentación |
| 4.3.4, 4.11.1 | La página de composición calculaba, persistía y orquestaba | INV‑043 (cerrado), INV‑070 | corrección de la interfaz (la separación); actualización de la documentación (el reparto resultante) |
| 4.4.1 | `NORMAS.md` §4 no contenía la fórmula con destajo | INV‑074 (incorporada el 28/09/2026 a `NORMAS.md` §4; su estado final lo registra el cierre de la última etapa) | actualización de la documentación |
| 4.5.1 | `generar_presupuesto` pública y llamada sin informe por los sembradores | INV‑037 (a limitaciones) | — |
| 4.5.1 | Protocolo de elaboración en cuatro sitios | INV‑069 (cerrado) | corrección del núcleo |
| 4.5.1 | Ítem sin partida pendiente (UC‑01 3a) | INV‑013 (cerrado) | corrección del núcleo |
| 4.5.1 | El hallazgo `PENDIENTE` vive fuera de la auditoría | INV‑070 | actualización de la documentación |
| 4.5.1 | UC‑01 3a no se alcanzaba desde la interfaz y la API | INV‑072 (cerrado) | corrección de los adaptadores y la API; corrección de la interfaz |
| 4.5.1 | La recarga del informe perdía los ítems pendientes | INV‑080 (cerrado) | corrección de la interfaz, con un cambio del núcleo por expediente |
| 4.5.1 | Los escenarios de un presupuesto con pendientes no los declaraban | INV‑083 (la pantalla los declaró desde la corrección de la interfaz y la API desde el 28/09/2026; el informe del propio escenario, a limitaciones; su estado final lo registra el cierre de la última etapa) | corrección de la interfaz (la pantalla); la última etapa del cierre, que incluyó ese cambio de la API (la API) |
| 4.5.2 | `plan_secuencial` agrupaba por renglón | INV‑071 (cerrado) | corrección del núcleo |
| 4.5.3 | Redondeo de presentación escrito en tres lugares | INV‑038 (a limitaciones) | — |
| 4.2, 4.6 | Descartar la versión nueva de UC‑02 (flujo 7a) | INV‑015 (cerrado) | corrección de la interfaz, con un cambio del núcleo por expediente |
| 4.6 | Variación con precio anterior cero | INV‑004 (cerrado) | corrección del núcleo |
| 4.7.3 | Los flujos alternativos de UC‑04 no estaban implementados | INV‑073 (abierto: implementados en el adaptador civil; queda su documentación) | corrección de los adaptadores; actualización de la documentación |
| 4.8.3 | Dato ausente como INFO y dato inválido como ERROR | INV‑012 (cerrado) | corrección del núcleo |
| 4.9.2 | Interpretación de especificaciones duplicada en los adaptadores | INV‑041 (a limitaciones) | — |

*Nota.* Elaboración propia a partir del [inventario del cierre](../../auditoria/2026-09-inventario.md),
con los estados al cerrar la corrección de la interfaz y los scripts (28/09/2026), salvo las filas de
INV‑057, INV‑074, INV‑077 e INV‑083, que recogen además cambios de la última etapa del cierre. Cada hallazgo
cerrado lo fue en la etapa que indica la última columna; los detalles de cada corrección están en la
[bitácora del cierre](../../bitacora/2026-09-23-cierre.md).
