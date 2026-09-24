# Capítulo IV — Desarrollo de la propuesta

| Capítulo | Estado | Última revisión |
|---|---|---|
| IV. Desarrollo de la propuesta | borrador completo (fase Red del cierre); pendiente la revisión con la lista de cotejo y la del tutor académico; figuras y decisiones del tutor marcadas como pendientes en la sección 4.12 | 2026-09-23 |

Este capítulo describe el sistema tal como existe en la rama `main` después de la fase C1 del cierre
(commit `f1dda36`, fusión del PR #11). Se sigue el orden causal del plan de desarrollo: primero los
requerimientos y el modelo de datos, luego la arquitectura que los aloja, el motor de costos, el
presupuesto con su curva, la actualización de precios, el adaptador civil, la verificación, los
adaptadores de otros dominios, los módulos de aprendizaje automático y, al final, la interfaz y la
API. Cada sección expone el problema de diseño, la decisión que se tomó y la evidencia que la
sostiene: una prueba automatizada, un módulo del código o la bitácora de la sesión que la registró.
Las bitácoras de `docs/bitacora/` son la memoria de esas decisiones y se incorporan como anexo H.

Dos reglas gobiernan el capítulo. La primera es que las cifras del proyecto salen de la tabla de
cifras citables de [plan_redaccion.md §5](../plan_redaccion.md) y que las de pruebas y cobertura
citan la corrida de integración continua en la que se midieron, porque la integración continua es
la fuente de verdad de esas cifras ([metodologia.md §6](../../metodologia.md)). La corrida de
referencia es la del PR #11
([35950215309](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/35950215309)):
735 pruebas aprobadas en Linux y en Windows, ninguna omitida, y una cobertura del 98 % sobre `core/`.
La segunda regla es que, donde un documento del repositorio contradice al código, el capítulo
describe el código y señala la contradicción con su registro en el
[inventario del cierre](../../auditoria/2026-09-inventario.md), en lugar de heredarla.

Todos los análisis de precios unitarios y presupuestos que se mencionan son ejercicios académicos
ficticios o casos construidos para el proyecto, y ninguno corresponde a una obra ejecutada
([CLAUDE.md §1](../../../CLAUDE.md)). Las decisiones que dependen del tutor académico se declaran
como pendientes y remiten al [paquete de decisiones para el tutor](../revisiones/2026-09-paquete-tutor.md).

## 4.1 Requerimientos

### 4.1.1 El documento de requerimientos

Los requerimientos se especificaron en la Sesión 0.1 con la estructura de la norma IEEE 830 y se
recogen en la [especificación de requerimientos](../../ERS.md) (anexo A). La especificación no
reproduce los datos que tienen fuente única: la fórmula de cálculo, las siete reglas de verificación
y los criterios de degradación del módulo predictivo se enlazan desde ella a `CLAUDE.md`, y el caso
de estudio, a [linea_base.md](../../linea_base.md). Con ese criterio, un cambio en la fórmula o en una
regla se hace en un solo lugar.

La versión vigente declara once casos de uso, 42 requerimientos funcionales y diez requerimientos no
funcionales. El documento prevé congelar los ocho casos de uso originales al cruzar la compuerta G0,
que sigue pendiente del tutor; los casos de uso posteriores se agregaron por extensiones registradas
en el propio documento: UC‑10 y UC‑11, con los RF‑33 a RF‑35,
en la Sesión P0.1 del sprint del prototipo, y UC‑12, con los RF‑36 a RF‑43 y el RNF‑10, en la Sesión
U0.1 del sprint de interfaz. El número UC‑09 y el RF‑32 quedan vacantes, reservados para el asistente
de presupuestos que describe `PLAN_ASISTENTE.md` y que quedó como trabajo futuro. La numeración de ese
asistente a partir de RF‑44 es una de las constancias que se piden al tutor.

La Tabla 4.1 resume los casos de uso con su actor principal, el incremento que los implementó y la
forma en que se accede a ellos en `main`.

**Tabla 4.1**
*Casos de uso del sistema y su realización en la versión vigente*

| UC | Nombre | Actor principal | Incremento | Acceso en `main` |
|---|---|---|---|---|
| UC‑01 | Elaborar presupuesto nuevo desde una fuente de cantidades | proyectista | I0.5, I3.1 | interfaz (pantalla «Elaborar presupuesto») y API (`POST /presupuestos`) |
| UC‑02 | Actualizar masivamente los precios de un presupuesto existente | administrador del catálogo | I1 | interfaz y API |
| UC‑03 | Reutilizar partidas y desgloses de proyectos anteriores | proyectista | I2 | interfaz (pantalla «Partidas similares») |
| UC‑04 | Recalcular ante cambio de alcance o dimensiones | proyectista | I3.2 | funciones del núcleo y del adaptador civil, sin pantalla propia |
| UC‑05 | Auditar un presupuesto elaborado por un tercero | auditor | I4 | incluido en toda elaboración; informe por la interfaz y la API |
| UC‑06 | Registrar y consultar rendimientos medidos | residente de obra | I6.2 | API |
| UC‑07 | Contrastar el precio construido con el precio de mercado | auditor | I6.3 | script de resultados y ayudas de la pantalla de composición |
| UC‑08 | Generar escenarios de sensibilidad | proyectista | F.1 | interfaz y API |
| UC‑10 | Componer una partida | proyectista | P1–P2 | interfaz (pantalla «Componer partida») |
| UC‑11 | Editar una partida compuesta | proyectista | P1–P2 | interfaz (pantalla «Componer partida») |
| UC‑12 | Recorrer la aplicación guiado desde el Inicio | usuario nuevo | U1 | declarado; pendiente de implementación (fase C3) |

*Nota.* Elaboración propia a partir de `docs/ERS.md` §2.2 y de `ui/app.py`, `api/rutas/` y
`scripts/`. La columna de acceso describe el código; la especificación declara en su §3.1 que la
interfaz ofrece los once casos de uso, lo que el código no confirma para UC‑04, UC‑06, UC‑07 y UC‑12
(hallazgo INV‑030 del inventario, asignado a la fase C4).

### 4.1.2 Requerimientos funcionales

Cada requerimiento funcional es una afirmación comprobable con prioridad (esencial, deseable u
opcional), el caso de uso que lo origina, el incremento que lo implementa y un criterio de aceptación
que nombra la prueba que lo demuestra. Esa última columna es la decisión de fondo del documento: un
requerimiento sin criterio medible no se aceptó, y el criterio se escribió antes que la prueba. Por
ejemplo, RF‑07 exige que el acumulado final de la curva de inversión sea igual al total del
presupuesto **sin tolerancia**, y RF‑22 exige que el sistema detecte las siete inconsistencias de la
línea base sobre un presupuesto de prueba que las reproduce.

Tres grupos de requerimientos no están cumplidos en `main` y así se declaran:

- **RF‑20** (diferencial entre la versión anterior y la recalculada, deseable, UC‑04) no tiene
  implementación. La fase C1 decidió declararlo «no implementado» en lugar de escribir un tercer
  comparador sin llamador (decisión C1‑7 de la [bitácora del cierre](../../bitacora/2026-09-23-cierre.md),
  ratificada el 2026‑09‑23). Pasa a las limitaciones del trabajo.
- **RF‑36 a RF‑43** (UC‑12, recorrido guiado desde el Inicio) están declarados con sus pruebas
  nombradas, pero su implementación pertenece a la fase C3 del cierre, que se ejecuta como la Sesión
  U1 del [plan de interfaz](../../../PLAN_UI.md).
- **RF‑16** (precarga de una partida propuesta con referencia a su origen y a su puntaje) tiene la
  precarga implementada; la persistencia de la partida nueva se resolvió con la composición de UC‑10,
  pero la especificación y el plan de pruebas le asignan estados distintos (INV‑027). El alcance de
  RF‑16 es la decisión D5 del tutor, pendiente.

### 4.1.3 Requerimientos no funcionales

Los diez requerimientos no funcionales se organizaron por características de la norma ISO/IEC 25010,
cada uno con su métrica y su meta. La Tabla 4.2 los lista; sus veredictos se presentan en el
capítulo V a partir de la fuente única, la evaluación de calidad de
[calidad_iso25010.md §9](../../calidad_iso25010.md).

**Tabla 4.2**
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
| RNF‑08 | Seguridad | ejecución local, sin credenciales ni servicios externos | cero y cero, con la descarga inicial del modelo de similitud como excepción declarada |
| RNF‑09 | Compatibilidad | entrada IFC 4 de cualquier modelador | cantidades iguales al cálculo manual con archivos de al menos dos herramientas |
| RNF‑10 | Usabilidad | una persona que nunca vio la aplicación llega sola del Inicio a un presupuesto en Excel con su hoja de auditoría | caso con persona CP‑07 en dos escenarios, sin ayuda y en 20 min o menos |

*Nota.* Elaboración propia a partir de `docs/ERS.md` §3.3.

### 4.1.4 Estado documental de los requerimientos

La especificación acumuló desfases respecto del código a medida que avanzaron los incrementos. La
auditoría del cierre los registró y los asignó a la fase C4, de documentación; el capítulo no los
hereda. Los más relevantes para lo que sigue son cuatro. La especificación da por pendiente la
extracción IFC y el archivo `tanquilla.ifc`, que existen desde la Sesión F.1 (INV‑028, sección 4.7).
El criterio de RF‑19 cita una prueba que no cambia el ancho de la tanquilla; la prueba que sí lo hace
se escribió en C1 (INV‑011, sección 4.7). La matriz de trazabilidad nombra en algunos casos pruebas
que no verifican lo afirmado (INV‑026). Y el encabezado del documento contradice su propio conteo
mínimo de requerimientos (INV‑063). Ninguno de estos desfases altera el conteo vigente de 42
requerimientos funcionales, diez no funcionales y once casos de uso, que es el que se cita.

## 4.2 Modelo de datos

El modelo de datos se diseñó en la Sesión 0.2 ([modelo_datos.md](../../modelo_datos.md), anexo B) y se
implementó con SQLAlchemy en la Sesión I0.4 (`core/models/entidades.py`). Materializa en persistencia
los contratos del núcleo sin ampliarlos: quince entidades agrupadas en catálogo (`Partida`, `Insumo`,
`ComposicionAPU`, `Rendimiento`, `Ejecucion`), precios y su historial (`ListaPrecios`,
`PrecioInsumo`, `CambioPrecio`, `IncidenciaCambio`) y proyecto, presupuesto y auditoría (`Proyecto`,
`Presupuesto`, `PartidaPresupuestada`, `PuntoCurva`, `ItemComputo`, `Hallazgo`). El documento del
modelo se declara «aprobado en la Sesión 0.2», pero la compuerta G0, que debía aprobarlo junto con la
especificación y la arquitectura, sigue pendiente del tutor (INV‑061); el capítulo lo trata como
documento pendiente de esa aprobación. Cuatro decisiones del modelo merecen exponerse.

**Los montos se guardan como texto.** SQLite no tiene un tipo decimal nativo: su tipo numérico
almacena un valor de coma flotante y lo reconvierte pasando por `float`, lo que admite pérdida de
precisión. Como el principio 3 del proyecto exige `Decimal` en todo lo monetario y dimensional, se
escribió el tipo `DecimalExacto` (`core/models/tipos.py`), que persiste cada `Decimal` como texto de
hasta 40 caracteres y lo devuelve idéntico. El costo aceptado es que ordenar o filtrar por importe en
SQL sería lexicográfico; ninguna consulta del sistema lo hace. El cambio a PostgreSQL sustituiría ese
tipo por uno numérico nativo sin tocar los modelos (ADR 7 de [arquitectura.md](../../arquitectura.md)).

**El versionado es híbrido.** Un presupuesto responde dos preguntas distintas: qué se firmó y cuánto
costaría hoy. Para la primera, `PartidaPresupuestada` congela el resultado del análisis de precios de
cada renglón y la fila del presupuesto copia los cuatro parámetros de costo con que se valoró. Para
la segunda, el presupuesto referencia la lista de precios que lo valoró, y esa lista es inmutable
desde que un presupuesto la usa: actualizar precios crea una lista nueva con vigencia posterior y
registra las diferencias en `CambioPrecio`. Reconstruir un presupuesto a su fecha es valorarlo con la
lista vigente en esa fecha, y `cargar_presupuesto` (`core/budget/persistencia.py`) comprueba que el
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
encofrado (INV‑064); aquí se los nombra por su contenido para no heredar esa ambigüedad.

**Un rendimiento medido exige la ejecución de la que proviene.** El contrato distingue el rendimiento
estimado, que declara el proyectista, del medido, observado en obra. El modelo lleva esa distinción a
la base con una clave foránea a `Ejecucion` y una restricción de comprobación
(`ck_rendimiento_medido_exige_ejecucion`) que impide guardar un rendimiento medido sin la ejecución que
lo respalda. Un rendimiento medido sin procedencia no sería auditable, y esa es la condición que hace
posible, a futuro, alimentar el sistema con el avance medido de una obra.

## 4.3 Arquitectura

### 4.3.1 Núcleo cerrado y adaptadores abiertos

La arquitectura se documentó con las vistas 4+1 en la Sesión 0.3
([arquitectura.md](../../arquitectura.md), anexo C). El estilo es de puertos y adaptadores: el paquete
`core/contracts/` define los tipos que cruzan las fronteras entre paquetes; los adaptadores de dominio
(`adapters/`) y los módulos de aprendizaje automático (`ml/`) los implementan o los consumen; la
interfaz (`ui/`) y la API (`api/`) orquestan. El motor de costos es una función pura y la
verificación no depende del aprendizaje automático, de modo que el resultado central del trabajo no
queda sujeto a la disponibilidad de datos para entrenar modelos (ADR 5).

La regla de dependencia es estricta: ninguna importación sale de `core/` hacia otro paquete del
proyecto, y los adaptadores y los módulos de `ml/` solo importan `core.contracts`. Esa regla es la
forma operativa de la hipótesis central: si un dominio nuevo se incorpora escribiendo un adaptador
que solo conoce los contratos, el núcleo no tiene que cambiar para recibirlo.

### 4.3.2 Los contratos como única frontera

La Tabla 4.3 enumera los contratos y su papel. Son clases de datos inmutables que validan sus
invariantes al construirse (cantidades no negativas, rendimiento positivo, depreciación en el
intervalo (0, 1], unidades normalizadas) y no dependen de nada fuera de la biblioteca estándar de
Python.

**Tabla 4.3**
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
`LineaManoObra.modalidad` se agregaron en el sprint del prototipo (sección 4.4); la tabla de contratos
de `CLAUDE.md` y el diagrama de la arquitectura todavía no los muestran (INV‑057, fase C4).

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

El contrato se modificó una sola vez por una necesidad de dominio, y se hizo con expediente. En la
Sesión P0.1 se comprobó que `LineaManoObra` no podía expresar una mano de obra remunerada por unidad
de obra, «a destajo», que el requerimiento RF‑34 exige declarar por línea
([bitácora P0.1](../../bitacora/2026-09-16-P0-hallazgo-destajo.md)). La solución adoptada fue un campo
aditivo con valor por defecto `JORNAL`, que conserva el constructor anterior y deja la línea base
intacta. Es la decisión D9, recomendada al tutor y pendiente de su aval. Tres hallazgos de la auditoría
del cierre también piden cambiar contratos: la conversión de los campos enumerados en
`Rendimiento` e `ItemComputo` (INV‑001), la exigencia de `Decimal` y de signo en montos y parámetros
(INV‑002) y un evaluador de expresiones único en `core.contracts` (INV‑006). Sin el aval del tutor no
se aplicaron: quedan como *aceptados por decisión de arquitectura registrada*, con su expediente en la
[bitácora de C1](../../bitacora/2026-09-23-C1-expedientes.md).

### 4.3.3 Las guardias automáticas

La hipótesis central no se sostiene por revisión manual sino por dos guardias que corren en cada
cambio. La primera es `tests/unit/test_arquitectura.py`, que analiza el árbol sintáctico de cada
archivo y falla si un adaptador o un módulo de `ml/` importa de `core` algo distinto de
`core.contracts`, si `core/` importa cualquier paquete de primer nivel del proyecto o si
`core/contracts` depende de algo ajeno a la biblioteca estándar. En la verificación de la compuerta
GC1 reunía 66 casos, incluida una prueba que exige que la guardia cubra todo paquete de primer nivel
fuera del núcleo (`test_la_guardia_cubre_todo_paquete_de_primer_nivel_fuera_del_nucleo`), agregada al
cerrar INV‑010. La segunda guardia es `scripts/guardia_nucleo.py`, que la integración continua ejecuta
en su trabajo de calidad sobre el rango de commits de cada PR y de cada fusión en `main`
(`.github/workflows/ci.yml`): falla si un commit toca `core/` junto con `adapters/` o `ml/`, o si una
rama que incorpora un dominio cambia `core/`. La definición operativa de «rama de adaptador» que usa
esa guardia es la decisión D7 del tutor, pendiente.

Una tercera protección, más reciente, vigila el entorno de pruebas: ninguna prueba puede crear ni
modificar la base de trabajo `data/apu.db`, y `tests/unit/test_salvaguarda.py` demuestra que esa
salvaguarda falla cuando debe (cierre de INV‑065 en C1).

### 4.3.4 Proceso, despliegue y lo que la arquitectura documentada no refleja

El sistema es de un solo proceso y un solo hilo, se ejecuta en el equipo del usuario y guarda todo en
un archivo SQLite (ADR 9). La transacción pertenece a quien llama: las funciones de persistencia del
núcleo hacen `flush` y no `commit`, para que el presupuesto pueda formar parte de una operación mayor,
como la actualización de precios. Las dependencias se instalan con `uv sync` y se separan en extras
por capa (`civil`, `ml`, `ui`, `api`), de modo que el equipo de quien presupuesta no necesita
`ifcopenshell` ni las bibliotecas del modelo de similitud para operar el núcleo.

El documento de arquitectura tiene tres desfases con el código que el capítulo no hereda. Sus vistas
de casos de uso y de desarrollo describen un sistema anterior a la Sesión I1 y nombran funciones que
no existen (INV‑029); su vista física da por abierta la compuerta G1 y por ausente `tanquilla.ifc`
(INV‑028); y su ADR 8 declara dos copias del evaluador de expresiones cuando el código tiene cinco
(INV‑058). Además, afirma que la página `ui/paginas/componer.py` «solo pinta», cuando esa página
calcula el precio unitario con `calcular_apu`, persiste la composición y orquesta la elaboración del
presupuesto (INV‑043 e INV‑070). Los cuatro hallazgos están asignados a las fases C3 y C4. Por esa
razón, las figuras de este capítulo que se derivarían de los diagramas de la arquitectura quedan
pendientes hasta su regeneración (sección 4.12).

## 4.4 Motor de costos

### 4.4.1 La fórmula

El motor de costos es la función `calcular_apu(composicion, parametros) -> ResultadoAPU`
(`core/costing/motor.py`). No accede a la base de datos ni conserva estado: recibe una composición y
los parámetros de costo y devuelve el desglose y el precio unitario. Todo el cálculo se hace con
`Decimal` y sin redondeos intermedios; el redondeo a dos decimales ocurre solo al presentar. La
fórmula, cuya fuente única es `CLAUDE.md` §4 y que el capítulo II fundamenta, es la siguiente:

```
materiales         = Σ cantidad × precio
equipos            = Σ (cantidad × precio × depreciación) / rendimiento
mano_obra_jornal   = ( Σ cantidad × sueldo × (1 + FCAS) + bono × Σ obreros ) / rendimiento
mano_obra_destajo  = Σ cantidad × precio por unidad de partida
costo_directo      = materiales + equipos + mano_obra_jornal + mano_obra_destajo
con_administracion = costo_directo × (1 + administración)
precio_unitario    = con_administracion × (1 + utilidad)
```

Con los parámetros del caso didáctico (FCAS de 6,00, bono de alimentación de 1,00 USD por obrero y
día, administración del 15 % y utilidad del 10 %, en cascada), el motor reproduce los cinco precios
unitarios de la línea base, como muestra la Tabla 4.4. El FCAS se trata como parámetro configurable
del caso de estudio y no como valor normativo, porque ninguna fuente venezolana lo publica; avalar esa
declaración es la decisión D4 del tutor.

**Tabla 4.4**
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
verificada, transcrita del ejercicio de la clínica y fijada en `tests/fixtures/apu_linea_base.py`, se
escribió antes que el código, y `tests/unit/test_costing.py` fallaba con `ImportError` hasta que la
Sesión I0.3 implementó `core/costing/` ([bitácora I0.3](../../bitacora/2026-08-29-I0.3-motor.md)). La
línea base funciona así como oráculo: define el resultado correcto con independencia de la
implementación.

Las siete pruebas de ese archivo vigilan de forma explícita los dos errores más probables al
implementar la fórmula. El primero es dividir los materiales entre el rendimiento: su cantidad ya está
referida a la unidad de partida, y solo el costo diario de equipos y mano de obra se reparte entre las
unidades producidas en el día. Lo vigila `test_los_materiales_no_se_dividen_entre_el_rendimiento`. El
segundo es sumar los porcentajes de administración y utilidad en lugar de encadenarlos. Lo vigila
`test_administracion_y_utilidad_se_aplican_en_cascada`. Las cinco pruebas restantes comparan cada
precio unitario con el de la línea base.

### 4.4.3 La modalidad a destajo

La modalidad a destajo se incorporó al motor en el sprint del prototipo con la decisión D9 descrita en
la sección 4.3.2. Una línea a destajo expresa un precio por unidad de partida, no un sueldo diario:
entra completa al costo directo, sin FCAS, sin bono de alimentación y sin dividirse entre el
rendimiento. Con todas las líneas en jornal, el resultado es idéntico al del motor anterior; la prueba
`tests/unit/test_costing_destajo.py::test_la_linea_base_no_se_mueve` lo garantiza en cada corrida. La
bitácora de la Sesión P0.1 funda la modalidad en la legislación laboral venezolana; esa fuente
normativa no figura todavía en la lista de referencias de la tesis y queda marcada como pendiente en
la sección 4.12.

## 4.5 Presupuesto y curva de inversión

### 4.5.1 El informe viaja con el presupuesto

El paquete `core/budget/` arma el presupuesto a partir de las cantidades, las composiciones y los
parámetros de costo. La función de entrega es `elaborar` (`core/budget/presupuesto.py`): valora cada
ítem con el motor, añade la curva de inversión si hay un plan de trabajo y audita siempre el
resultado. Devuelve un `ResultadoElaboracion` que lleva el presupuesto **y** el informe de auditoría,
de modo que no existe una forma de entregar el uno sin el otro (principio 7 de `CLAUDE.md` §2). La
función intermedia `generar_presupuesto` sigue siendo pública: `elaborar` la usa como paso previo y
los tres sembradores de dominio (`scripts/seed_telecom.py`, `scripts/seed_industrial.py` y
`scripts/seed_sistemas.py`) todavía la llaman sin informe. Su documentación declara que no tiene
valor de entrega, y el hallazgo quedó entre las limitaciones (INV‑037).

La fase C1 hizo de `elaborar` el único lugar del protocolo «presupuesto valorado, plan de trabajo,
curva y auditoría». Antes de C1, la interfaz, la API y los sembradores escribían ese protocolo cada uno
por su cuenta, en cuatro sitios; ahora pasan `plan=plan_secuencial` y el núcleo resuelve el resto
(INV‑069, decisión C1‑3). La misma fase implementó el flujo alternativo 3a de UC‑01: un ítem cuya
partida no tiene composición en el catálogo ya no aborta la elaboración, sino que queda pendiente, no
suma al total y el informe lo declara con un hallazgo de severidad ERROR y código `PENDIENTE`
(INV‑013, decisión C1‑2). Ese hallazgo lo agrega la elaboración y no la auditoría, porque solo la
elaboración sabe qué ítems no pudo valorar; quien llame a `auditar` directamente no lo ve, lo que queda
registrado en INV‑070. Por otra parte, la interfaz y la API todavía piden las composiciones al
catálogo antes de llamar a `elaborar`, y el catálogo lanza una excepción ante una partida desconocida,
de modo que ese flujo alternativo aún no se alcanza de punta a punta desde ellas (INV‑072, fases C2 y
C3).

### 4.5.2 La curva cierra por construcción

En el caso didáctico, la curva de inversión cerraba en 1 575,50 USD, el 99,30 % del total de
1 586,61 USD, y los montos diarios del plan de trabajo no coincidían con los de sus partidas. El
módulo `core/budget/curva.py` hace imposible ese error: el monto del último período no se calcula
sumando fracciones, sino restando del total del presupuesto lo ya repartido. Aunque los montos
anteriores se redondeen a centavos, el acumulado final es el total literal. Antes de calcular,
`generar_curva` valida el plan y lanza `PlanInvalido` si menciona una partida que el presupuesto no
tiene o si las fracciones de alguna partida no suman exactamente uno. La regla R2 comprueba la
identidad entre el acumulado y el total; este módulo la garantiza.

El plan secuencial (`plan_secuencial`) asigna un período a cada partida. En C1 se encontró que asignaba
un período por renglón y no por código, de modo que dos renglones de la misma partida sumaban una
fracción de dos y hacían fallar la curva de la muestra civil tabular; se corrigió para agrupar por
código de partida en el orden de su primera aparición (INV‑071, commit `3c026da`). Las etiquetas de los
períodos llevan los códigos de las partidas entre corchetes, por ejemplo `Dia 1 [LB-01-EXC]`, que es la
convención con la que R7 concilia el plan con el presupuesto (sección 4.8).

Las pruebas `tests/unit/test_budget.py::test_presupuesto_reproduce_1586_61` y
`tests/integration/test_presupuesto_linea_base.py` reproducen el total de la línea base corregida
desde el catálogo persistido, con la curva cerrada al 100 %.

### 4.5.3 Exportación y persistencia

`exportar_excel` (`core/budget/excel.py`) escribe un libro con cuatro hojas: presupuesto, análisis de
precios, curva y auditoría. Los montos se redondean a dos decimales solo en la celda presentada,
nunca en el cálculo (RF‑08), con el número de decimales importado de `DECIMALES_PRESENTACION`. La
operación de redondeo para presentar está escrita en tres lugares, dos del núcleo y uno de `ml/`,
duplicación que quedó entre las limitaciones (INV‑038). La
persistencia vive en `core/budget/persistencia.py`, que junto con `core/catalog/mapeo.py` son las dos
únicas fronteras entre los modelos de la base de datos y los contratos (ADR 12). `guardar_presupuesto`
rechaza un informe cuyo código no sea el del presupuesto: atribuir los hallazgos a otro documento
falsearía la auditoría.

## 4.6 Actualización masiva de precios (UC‑02)

El primer caso de uso de valor percibido fue la actualización de precios, porque en la práctica
presupuestaria es el que más se repite. El problema de diseño era recalcular todos los análisis
afectados por una lista nueva sin editar ninguna composición y sin perder la capacidad de reconstruir
la versión anterior. La solución, implementada en la Sesión I1
([bitácora I1](../../bitacora/2026-08-29-I1-actualizacion-precios.md)), aplica el versionado híbrido de
la sección 4.2.

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
renglones no cambian. El recálculo de 100 partidas tarda 1,17 s frente a la meta de 5 s del RNF‑03,
medición que se reproduce con `scripts/medir_rnf03.py` y que el capítulo V evalúa.

Tres aspectos quedan abiertos. El flujo 7a, descartar la versión nueva conservando el registro de
cambios, es una subtarea de la fase C3 (INV‑015). Como la lista identifica al insumo por su
descripción, una fila actualiza todas las variantes homónimas descritas en la sección 4.2. Y cuando el
precio anterior es cero, la variación registrada es cero, porque la columna no admite nulos (decisión
C1‑4).

## 4.7 Adaptador civil: reglas paramétricas y extracción IFC

### 4.7.1 Reglas paramétricas trazables

El adaptador civil responde a la segunda pregunta secundaria de la investigación: qué reglas
paramétricas derivan las cantidades de la geometría sin intervención manual. Cada regla es una
expresión de texto con una sola copia en `adapters/civil/reglas.py` (Tabla 4.5), y cada cantidad que
produce es un `ItemComputo` de origen `REGLA` que registra la expresión evaluada y los parámetros
usados. Con esa información, el núcleo puede volver a evaluar la cantidad desde su origen, y esa
reevaluación es la que hace posible la regla R1.

**Tabla 4.5**
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
que traza la cantidad hasta la geometría de la que salió.

La compuerta G1 exigía que las cantidades extraídas del modelo de muestra coincidieran con el cálculo
manual; de lo contrario, el adaptador IFC se sustituiría por la entrada tabular. Se cruzó en la Sesión
F.1 **con salvedad**: el adaptador extrae de `data/samples/tanquilla.ifc` exactamente los 0,224 m³ de
concreto del cálculo manual, pero ese modelo lo generó por programa `scripts/generar_tanquilla_ifc.py`
y no lo exportó un modelador BIM ([bitácora F.1](../../bitacora/2026-08-31-F1-api-3d.md)). Por esa razón
el RNF‑09, que pide archivos de al menos dos herramientas, queda parcial, y ejercitar el adaptador con
modelos exportados por modeladores comerciales o libres es trabajo pendiente. La especificación y la
arquitectura todavía dan la extracción IFC por pendiente (INV‑028); el código y las pruebas
`tests/unit/test_adapter_civil_ifc.py` y `tests/unit/test_generador_ifc.py` muestran que existe.

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
escrita en C1 para cerrar INV‑011, cambia el ancho de las tanquillas y comprueba que cambian el
concreto, el encofrado y la excavación, y ninguna otra partida; que los ítems nuevos traen la
expresión y el parámetro cambiado; que la curva se regenera cerrando en el total nuevo; y que la
verificación se ejecuta de nuevo. El paso 5 de UC‑04, el diferencial por partida (RF‑20), no está
implementado (sección 4.1.2), y tampoco lo están sus flujos alternativos: informar que un parámetro no
participa en ninguna regla, emparejar por `GlobalId` al reimportar un modelo IFC y conservar el valor
anterior ante una cantidad negativa (INV‑073, fases C2 y C4).

## 4.8 Verificación R1–R7 y el informe de auditoría

### 4.8.1 Una regla por inconsistencia

El paquete `core/verification/` implementa las siete reglas de verificación como clases que
implementan el contrato `ReglaVerificacion`. Cada una recibe un `Presupuesto` y devuelve una lista de
hallazgos con severidad, descripción, impacto cuantificado cuando corresponde y los `origen_id`
involucrados. La Tabla 4.6 relaciona cada regla con lo que comprueba y con la inconsistencia del caso
didáctico que detecta.

**Tabla 4.6**
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

La decisión de diseño más importante de la verificación es la ADR 8: la regla que produjo una cantidad
y el balance que la relaciona con otras son **datos del ítem**, no código del núcleo. La expresión viaja
en `ItemComputo.regla` con sus parámetros; el balance del relleno y su tolerancia, en las claves
`_balance` y `_tolerancia` de las especificaciones; la unidad tal como la escribió el autor, en
`_unidad_original`. El núcleo solo sabe evaluar aritmética (`core/verification/expresiones.py`) y leer
una convención de claves con prefijo (`core/verification/directivas.py`). Si R1 y R5 conocieran las
fórmulas del drenaje, el núcleo conocería el dominio civil y la hipótesis central sería falsa; con esta
decisión, un dominio nuevo declara sus expresiones y el núcleo las reevalúa sin una rama nueva. Esta
es la respuesta que el sistema da a la cuarta pregunta secundaria: las verificaciones que aporta el
conocimiento geométrico son posibles porque cada cantidad lleva consigo la regla que la produjo, un
dato que un programa de presupuesto convencional no conserva.

El precio de esa decisión es la duplicación del evaluador. El núcleo no puede importar un adaptador y
un adaptador solo puede importar los contratos, de modo que cada lado tiene el suyo: hoy existen cinco
copias, la del núcleo y una por adaptador. La prueba
`tests/unit/test_verification.py::test_las_reglas_civiles_son_evaluables_por_el_nucleo` evalúa cada
regla civil con el evaluador del adaptador y con el del núcleo y exige el mismo `Decimal`, de modo que
una divergencia se detecta el día que aparezca. La solución de fondo, un evaluador único en
`core.contracts`, cambia un contrato y espera el aval del tutor (INV‑006).

### 4.8.3 Severidad, impacto y el informe

El contrato define cuatro severidades: INFO, ADVERTENCIA, ERROR y CRÍTICO. Ninguna regla lanza
excepciones por los datos: a una regla que le falta un dato para evaluarse (un parámetro ausente, una
referencia de balance que no se resuelve) la informa como INFO «regla no evaluable»; un dato inválido
(una expresión mal escrita, un valor que no es `Decimal`) es un ERROR; y R2 y R7 se declaran «no
aplicables», también como INFO, cuando el presupuesto no trae plan de trabajo. Esa distinción entre el
dato ausente y el dato inválido se ajustó en C1 para cumplir RF‑23 y los flujos 2a y 3a de UC‑05
(INV‑012, decisión C1‑1): tratar también como INFO el dato inválido habría dejado como conforme un
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

### 4.9.1 Tres adaptadores sobre el mismo núcleo

La Sesión I5 puso a prueba la hipótesis central escribiendo tres adaptadores para dominios que el
núcleo no conocía: telecomunicaciones, mantenimiento industrial y sistemas de información. El sprint
multidominio los completó después con catálogos, presupuestos y auditorías propios
([bitácora del sprint multidominio](../../bitacora/2026-09-02-sprint-multidominio.md)). La Tabla 4.7
resume los cuatro adaptadores.

**Tabla 4.7**
*Adaptadores de dominio y sus fuentes*

| Adaptador | Fuente de cantidades | Origen de las cantidades | Regla declarada | Caso de aplicación |
|---|---|---|---|---|
| `adapters/civil` | CSV de tanquillas y zanja; modelo IFC | `REGLA` (tabular); `IFC` | las siete de la Tabla 4.5 | drenaje de la clínica, ejercicio académico ficticio |
| `adapters/telecom` | CSV de topología (nodos y enlaces) | `CSV` (nodos); `REGLA` (enlaces) | `longitud_m * (1 + reserva)` | dos presupuestos ARENAZA, ejercicios académicos ficticios |
| `adapters/industrial` | registro de activos con frecuencia de intervención | `REGLA` | `frecuencia_anual * horizonte_anios` | `MNT-001`, caso construido para el proyecto |
| `adapters/sistemas` | alcance funcional por módulo y caso de uso | `REGLA` | `4*entradas + 5*salidas + 4*consultas + 10*archivos + 7*interfaces` (puntos de función) | `SIS-001`, caso construido para el proyecto |

*Nota.* Elaboración propia a partir de `adapters/*/adaptador.py`, `adapters/civil/` y de la nota
sobre la naturaleza de los datos de `CLAUDE.md` §1.

Cada adaptador subclasifica `AdaptadorDominio`, declara su dominio e implementa `extraer` devolviendo
ítems con un `origen_id` tomado de su fuente. Ninguno importa de `core` otra cosa que los contratos.
Con los catálogos del sprint multidominio, el sistema reproduce con diferencia cero los totales de los
dos presupuestos ARENAZA (1 109,29 y 5 410,73 USD) y elabora `MNT-001` (18 124,09 USD) y `SIS-001`
(16 093,89 USD); lo comprueban `tests/integration/test_presupuesto_arenaza.py`,
`tests/integration/test_presupuesto_industrial.py` y `tests/integration/test_presupuesto_sistemas.py`.
El caso de telecomunicaciones tiene, además, una inconsistencia propia que se presentó en el capítulo I,
el tubo corrugado con 80 m en el cómputo y 90 m en el presupuesto, y la regla R1 la detecta con su
`origen_id` sin que el núcleo sepa qué es un tubo corrugado
(`tests/integration/test_auditoria_arenaza.py`).

### 4.9.2 La evidencia de que el núcleo no cambió

Tras la Sesión I5, la meta M9 del sprint alpha verificó que ninguna rama de adaptador había tocado
`core/`, y al cierre del sprint multidominio `git diff m-base --stat -- core/` quedó vacío con los
cuatro dominios poblados ([bitácora del sprint alfa](../../bitacora/2026-08-29-sprint-alpha.md) y del
sprint multidominio). El núcleo sí cambió después, por dos motivos que no son la incorporación de un
dominio: el sprint del prototipo modificó siete archivos de `core/` para la modalidad a destajo y la
composición de partidas, con el expediente de la decisión D9
([bitácora del prototipo](../../bitacora/2026-09-16-sprint-prototipo.md)), y la fase C1 corrigió los
hallazgos del núcleo que registró la auditoría. En ambos casos la guardia del núcleo comprobó que
ningún commit mezclara cambios de `core/` con cambios de `adapters/` o `ml/`. La distinción importa
para interpretar el indicador 4: la hipótesis afirma que el núcleo no cambia **al agregar un dominio**,
no que el núcleo sea inmutable.

El costo de la extensibilidad es la duplicación ya descrita del evaluador de expresiones, que cada
adaptador reescribió con los operadores que su dominio necesita, y la de la función que interpreta las
especificaciones en los cuatro adaptadores tabulares (INV‑041, a limitaciones). La guía para que un
tercero escriba un adaptador nuevo está en el
[manual técnico §4](../../manual_tecnico.md) (anexo E). Si la extensibilidad se presenta como objetivo
específico propio (OE7) o como resultado complementario del diseño del núcleo es la decisión D3 del
tutor; este capítulo describe el mismo desarrollo en ambos casos.

## 4.10 Módulos de aprendizaje automático

Los tres módulos de `ml/` reciben datos planos, no conocen la base de datos y solo pueden importar los
contratos del núcleo. La interfaz y la API los invocan con importación perezosa, de modo que el sistema
funciona sin el extra `ml`, y el núcleo nunca los importa.

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
la corrida de cierre de la Sesión I2 reconoció las cinco
([bitácora I2](../../bitacora/2026-08-31-I2-normalizacion.md)). El
puntaje es un número de coma flotante, y es la única excepción justificada a la regla del `Decimal`:
es una similitud adimensional, no una cantidad de obra ni un monto. La primera ejecución descarga el
modelo y lo guarda en la caché local, que es la excepción declarada del RNF‑08.

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
aprendizaje automático. El contraste con el precio construido emite un hallazgo de severidad
ADVERTENCIA cuando la desviación sale del rango de la clase 3 que se adoptó, de −20 % a +30 %, tomado
de la práctica 18R‑97 (AACE International, 2020). Si el caso debe clasificarse con esa práctica o con
la 56R‑08, específica de edificación y más estricta (AACE International, 2012), es una decisión del
tutor que puede cambiar ese rango.

## 4.11 Interfaz y API

### 4.11.1 La interfaz

La interfaz es una aplicación Streamlit de varias páginas (`ui/app.py`) con nueve pantallas,
enumeradas en la Tabla 4.8. La interfaz llama al núcleo y a los adaptadores directamente, sin pasar por
la API. El modo entrega, activado con una variable de entorno, oculta las cuatro pantallas de
investigación y deja las de trabajo.

**Tabla 4.8**
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

*Nota.* Elaboración propia a partir de `ui/app.py` (`PAGINAS`).

La pantalla de composición, construida en el sprint del prototipo, permite declarar una partida con sus
tablas de materiales, equipos y mano de obra (con la modalidad por línea), ver el precio unitario en
vivo calculado por el motor, apoyarse en la referencia de precios MaPreX de julio de 2026 (DataLaing, s.f.) para sugerir descripciones y
precios que siempre quedan editables (RF‑35) y guardar la composición solo si el rendimiento se declaró
con sus condiciones (RF‑33). La lógica de composición se probó sin Streamlit en `ui/composicion.py`
(`tests/unit/test_composicion.py`) y la pantalla con el arnés de pruebas de Streamlit
(`tests/unit/test_ui_componer.py`). Como se señaló en la sección 4.3.4, esa pantalla concentra además
cálculo, persistencia y orquestación; su separación está asignada a la fase C3 (INV‑043).

El recorrido guiado desde una pantalla de Inicio (UC‑12), con el caso abierto visible en toda pantalla
y un paso siguiente en cada una, está especificado y no implementado: es la Sesión U1, que la fase C3
ejecuta. Su medición con personas (RNF‑10, caso CP‑07) corresponde a la fase de mediciones del cierre.

### 4.11.2 La API

La API (`api/main.py`, FastAPI) expone 18 rutas agrupadas en catálogo, cómputos por dominio, listas de
precios, presupuestos y rendimientos. Crear un presupuesto (`POST /presupuestos`) elabora, audita y
guarda en una sola operación; el informe se consulta en Markdown y el libro en Excel por rutas propias;
la actualización de precios y los escenarios tienen rutas de presupuesto; y el registro de ejecuciones
y rendimientos medidos realiza UC‑06, respondiendo con la advertencia de rango cuando corresponde. Los
montos viajan siempre como texto en la frontera JSON (`api/esquemas.py`), porque serializarlos como
números los haría pasar por `float`. El esquema OpenAPI se exporta a `docs/api.json` con
`scripts/exportar_openapi.py`, y la integración continua falla si el archivo publicado difiere del que
genera el código (`tests/unit/test_openapi.py` y el paso de artefactos reproducibles de
`.github/workflows/ci.yml`).

Los escenarios de sensibilidad (UC‑08) se calculan en memoria y no se persisten: promover un escenario
a presupuesto equivale a la actualización de precios de UC‑02, que ya existe
([bitácora UC‑08](../../bitacora/2026-08-31-UC08-escenarios.md)). Validar que ese diseño cumple la
postcondición de UC‑08 es la decisión D6 del tutor. Los casos de uso UC‑04, UC‑06 y UC‑07 no tienen
pantalla propia y se alcanzan por las funciones del núcleo, la API o los scripts (INV‑030).

## 4.12 Síntesis del capítulo y pendientes

El desarrollo produjo un núcleo que calcula, presupuesta y audita sin conocer ningún dominio, cuatro
adaptadores que le entregan cantidades trazables y tres módulos de aprendizaje automático que operan
en los márgenes sin condicionar el resultado central. Las decisiones de diseño que sostienen la
propuesta son pocas y se repiten a lo largo del capítulo: cada cantidad lleva su procedencia y la regla
que la produjo; el informe de auditoría viaja con el presupuesto; la curva cierra por construcción; los
precios se versionan sin editar lo emitido; y el núcleo solo se comunica con el resto a través de
contratos vigilados por pruebas. La evaluación de esas decisiones frente a los indicadores de la tesis
se presenta en el capítulo V.

La Tabla 4.9 reúne lo que el capítulo no pudo cerrar, con su motivo.

**Tabla 4.9**
*Pendientes del capítulo IV*

| Pendiente | Motivo | Dónde se resuelve |
|---|---|---|
| Figuras del capítulo: diagrama de componentes (vista de desarrollo), diagrama entidad‑relación, diagrama de secuencia de la elaboración y capturas de la interfaz | Los diagramas de origen están en `docs/arquitectura.md` y `docs/modelo_datos.md`, que tienen desfases registrados (INV‑029, INV‑057, INV‑058, INV‑061, INV‑070); generarlos ahora llevaría esos desfases a la tesis. `docs/tesis/figuras/` todavía no existe | fase C4 (regeneración de la arquitectura y del modelo de datos) y una sesión de redacción posterior |
| Aprobación de los documentos de la Fase 0 (compuerta G0) | Depende del tutor académico designado | [paquete para el tutor](../revisiones/2026-09-paquete-tutor.md), punto G0 |
| Decisiones D1 (R7), D2 (R8), D3 (OE7), D4 (FCAS), D5 (RF‑16), D6 (UC‑08), D7 (rama de adaptador), D8 (BIM‑5D) y D9 (destajo) | Dependen del tutor; el capítulo describe lo implementado y declara la decisión como pendiente | [paquete para el tutor](../revisiones/2026-09-paquete-tutor.md) |
| Clasificación AACE 18R‑97 o 56R‑08 | Depende del tutor; afecta el rango del contraste de la sección 4.10.3 | [paquete para el tutor](../revisiones/2026-09-paquete-tutor.md), punto AACE |
| Contratos de INV‑001, INV‑002 e INV‑006 | Cambian contratos estables y esperan el aval del tutor | [expedientes de C1](../../bitacora/2026-09-23-C1-expedientes.md) y paquete para el tutor |
| Referencias de la norma IEEE 830, de las vistas 4+1, de la norma ISO/IEC 25010 y de la norma laboral que funda la modalidad a destajo | Se nombran en el capítulo, pero no tienen entrada verificada en `docs/tesis/referencias.md`, y no se completan de memoria | sesión de referencias antes de la revisión del capítulo |
| Recorrido guiado (UC‑12, RF‑36 a RF‑43) y separación de la pantalla de composición | Código pendiente | fase C3 |
| Flujos alternativos de UC‑04, UC‑01 3a de punta a punta y evaluador único en los adaptadores | Código pendiente | fase C2 (y C3 para la interfaz) |

*Nota.* Elaboración propia a partir del [inventario del cierre](../../auditoria/2026-09-inventario.md)
y del paquete para el tutor.
