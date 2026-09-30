# Manual de usuario — Sesión F.3

Guía de operación del sistema de generación y auditoría de Análisis de Precios Unitarios (APU)
para el proyectista. No hace falta saber programar: todo se opera desde la interfaz web local.
Qué es el sistema y por qué calcula como calcula está en [CLAUDE.md](../CLAUDE.md) y en la
[ERS](ERS.md); este manual solo explica **cómo usarlo**.

## 1. Requisitos e instalación

- Windows o Linux con **Python 3.12 o superior** y [uv](https://docs.astral.sh/uv/) instalados.
- Clonar o copiar la carpeta del proyecto y, dentro de ella, ejecutar:

```
uv sync --extra ui --extra api --extra civil --extra ml
```

No hay más pasos (RNF‑07). Notas:

- El extra `civil` instala `ifcopenshell` (modelos IFC); `ml` instala scikit‑learn y
  sentence‑transformers. Sin el extra correspondiente, esas funciones avisan que faltan en vez de
  fallar en silencio.
- La **primera** consulta de «Partidas similares» descarga el modelo de lenguaje y lo deja en
  caché local. Es la única conexión de red del sistema (RNF‑08); todo lo demás corre local.

## 2. Puesta en marcha

1. **Sembrar la base de datos** (una sola vez; crea `data/apu.db` con los cinco APU del caso de
   estudio):

   ```
   uv run python scripts/seed.py
   ```

   Los otros tres dominios tienen su propio catálogo, con precios publicados y fechados, cada uno en
   su base (opcional; cada comando imprime el presupuesto del dominio y su informe de auditoría):

   ```
   uv run python scripts/seed_telecom.py      # data/apu_telecom.db    presupuestos ARENAZA
   uv run python scripts/seed_industrial.py   # data/apu_industrial.db mantenimiento (precios MaPreX)
   uv run python scripts/seed_sistemas.py     # data/apu_sistemas.db   puntos de función (tabulador CIV)
   ```

   Para trabajar con uno de esos catálogos en la interfaz, el caso se abre una vez en **Inicio**
   (campo *Archivo del caso (SQLite)* y botón *Abrir este caso*); la barra lateral lo muestra bajo
   **Caso abierto** y todas las pantallas trabajan sobre él (por defecto, `data/apu.db`). También se
   puede arrancar la interfaz con la variable `ARENIA_CASO=<ruta>`. En la API, arrancar con la
   variable de entorno `APU_BASE` apuntando a esa base (por ejemplo
   `sqlite:///data/apu_telecom.db`). De dónde sale cada precio y con qué fecha: [manual técnico,
   sección 8.1](manual_tecnico.md#81-catálogos-por-dominio).

   **Dejar lista la aplicación para componer partidas (prototipo AREN.IA).** Una sola orden siembra
   la línea base de la clínica, tres partidas de demostración (`DEMO-01-INST`, `DEMO-02-VALV`,
   `DEMO-03-PRUEBA`) y el presupuesto de ejemplo `DEMO-001` con su informe de auditoría:

   ```
   uv run python scripts/seed_demo.py                                   # data/apu.db
   uv run python scripts/seed_demo.py --db data/prueba_arenia.db --reiniciar
   ```

   Es idempotente: repetirla no duplica nada. **`--reiniciar` borra la base antes de sembrarla**:
   úselo solo sobre una base de prueba, nunca sobre una con trabajo propio. Todo lo que siembra es
   un **caso didáctico** (ejercicio académico, no obra ejecutada ni precios cotizados; ver
   [CLAUDE.md §1](../CLAUDE.md)). Al terminar, la terminal muestra el total del presupuesto de
   ejemplo y la línea `Auditoria: 3 hallazgo(s), CUMPLE`.

2. **Abrir la interfaz** (se abre en el navegador, en el equipo local):

   ```
   uv run python -m streamlit run ui/app.py
   ```

   **Modo entrega.** Para mostrar solo la sección **Trabajo** (Inicio y las cinco pantallas que
   usa quien presupuesta: catálogo, componer, elaborar, actualizar precios e histórico) y omitir la
   sección **Investigacion** (escenarios, partidas similares, simulador y visor 3D), se arranca con
   la variable `ARENIA_MODO_ENTREGA` en `1` (exactamente `1`; cualquier otro valor la deja apagada):

   ```
   ARENIA_MODO_ENTREGA=1 uv run python -m streamlit run ui/app.py                  # bash
   $env:ARENIA_MODO_ENTREGA = "1"; uv run python -m streamlit run ui/app.py        # PowerShell
   ```

3. **API HTTP** (opcional, para integrar con otro software):

   ```
   uv run uvicorn api.main:app
   ```

   La documentación interactiva queda en `http://127.0.0.1:8000/docs`. Todos los montos viajan
   como **texto** (`"1586.61"`), nunca como número JSON: así no se pierde precisión decimal.

## 3. Las pantallas

La interfaz tiene diez pantallas en dos secciones del menú lateral, **Trabajo** e
**Investigacion** (en modo entrega, solo Trabajo; sección 2). Se abre en **Inicio**. Cada pantalla
muestra su título; las cinco que implementan un caso de uso de la ERS (componer, elaborar,
actualizar precios, escenarios y similares) muestran además su código como subtítulo. El Inicio y
el histórico, aunque la tabla los asocie a UC‑12 y UC‑02, no lo muestran. La barra lateral
muestra el caso abierto y su estado. Todas presentan los montos con dos decimales, pero **ningún
cálculo interno redondea**: el redondeo es solo de presentación.

| Sección | Pantalla | Caso de uso | Qué hace |
|---|---|---|---|
| Trabajo | **Inicio** | UC‑12 | Abrir el caso, cargar el de demostración si está vacío y elegir un recorrido guiado (sección 3.0) |
| Trabajo | **Catalogo de partidas e insumos** | consulta | Partidas e insumos con su precio vigente |
| Trabajo | **Componer una partida** | UC‑10 / UC‑11 | Armar a mano una partida nueva o editar una existente, presupuestarla y exportarla (sección 3.7) |
| Trabajo | **Elaborar un presupuesto** | UC‑01 | Extraer cantidades de una fuente por dominio y presupuestarlas (sección 3.1) |
| Trabajo | **Actualizar precios** | UC‑02 | Cargar una lista de precios nueva (CSV/XLSX) y revalorar un presupuesto guardado |
| Trabajo | **Historico de cambios de precio** | UC‑02 | Cambios de precio registrados, con filtros |
| Investigacion | **Escenarios de sensibilidad** | UC‑08 | Recalcular un presupuesto bajo supuestos («¿y si…?») sin alterarlo |
| Investigacion | **Partidas similares** | UC‑03 | Buscar en texto libre partidas parecidas para reutilizar su desglose |
| Investigacion | **Simulador de listas** | apoyo | Generar listas de precios de prueba, deterministas |
| Investigacion | **Visor 3D del modelo** | apoyo a UC‑01 | Ver el modelo IFC junto a la tabla elemento ↔ partida |

Con `ARENIA_CASO=<ruta>` la aplicación fija ese caso sin tener que abrirlo en el Inicio (la
aplicación sigue arrancando en el Inicio).

**Casos de uso sin pantalla propia.** La tabla cubre los casos de uso que tienen pantalla; los
demás se operan por otra capa (la correspondencia completa entre caso de uso y capa está en la
[ERS §3.1](ERS.md)). UC‑04, recalcular las cantidades ante un cambio de dimensiones, existe en el
adaptador civil (`adapters/civil/recalculo.py`) y no tiene pantalla ni ruta de la API. UC‑05 se ve
en el informe de auditoría que acompaña a todo presupuesto elaborado (sección 4). El presupuesto
de un tercero se importa solo por la API, sin pantalla (RF‑24, desde la fase C6; sección 3.4 bis).
UC‑01 también tiene un paso por la API: `POST /proyectos` crea el proyecto sobre el que luego se
elabora o se importa (la interfaz no crea proyectos).
Los rendimientos medidos de UC‑06 se registran por la API (sección 3.4), y las métricas y el
contraste completo de UC‑07 se generan con un script (sección 3.5); de los dos, la pantalla
**Componer una partida** ofrece una parte como ayudas: propone el rendimiento del histórico,
advierte si se aparta y contrasta el precio con la estimación por reglas (sección 3.7); **Elaborar
un presupuesto** propone también el rendimiento del histórico cuando a una partida le falta
(sección 3.1, paso 6). En UC‑01, el `.ifc` civil entra por la API (sección 3.1).

### 3.0 Inicio: el caso abierto y los recorridos guiados (UC‑12)

1. **El caso.** El campo *Archivo del caso (SQLite)* y el botón *Abrir este caso* fijan la base
   con que trabajan todas las pantallas durante la sesión; ninguna otra pantalla vuelve a pedir la
   ruta. Abrir una ruta que no existe no crea el archivo: la barra lateral dice «El archivo no
   existe todavia».
2. **El estado vacío.** Si el caso no existe todavía o no tiene partidas, el Inicio lo dice y
   ofrece **Cargar el caso de demostracion** (la línea base de la clínica, la demostración
   didáctica y su presupuesto auditado). La comprobación es solo sobre las **partidas**: una base
   que tenga insumos o listas de precios pero ninguna partida cuenta como vacía y también se le
   ofrece la carga. La carga **no borra nada**: nunca usa el reinicio de `scripts/seed_demo.py`, y
   repetirla no duplica lo sembrado; lo que ya hubiera en la base se conserva junto a lo
   sembrado. Si el caso ya tiene partidas, no se ofrece.
3. **Los recorridos.** Bajo *Que quiere hacer?* hay tres: *Ver la demostracion auditada*, *Armar
   un presupuesto* y *Actualizar precios*. Al elegir uno, el Inicio lista sus pasos; en cada
   pantalla del recorrido la barra lateral dice en qué paso está, qué hacer y cómo saber que
   terminó, y al pie aparece el botón **Siguiente: <paso>**, salvo en el último paso.

### 3.1 Elaborar un presupuesto (UC‑01)

1. Elegir el **dominio** (civil, telecom, industrial o sistemas) y el **archivo fuente**. Hay
   muestras listas en `data/samples/` (sección 6).
2. El adaptador del dominio extrae el **cómputo**: una tabla de cantidades donde cada fila
   declara de dónde salió (`origen_id`) y, si vino de una regla paramétrica, la expresión que la
   produjo. En esta pantalla todos los dominios se cargan en **CSV**; en el civil, el CSV pide
   asociar cada tipo de elemento a una partida del catálogo. El `.ifc`, que trae sus códigos de
   partida en el propio modelo, no entra por esta pantalla: entra por la API
   (`POST /computos/civil`) y se ve en el **Visor 3D del modelo**.

   **Si el archivo no se puede leer, no se presupuesta nada** y el mensaje nombra el archivo (sin
   la carpeta) y, si el problema es de una fila, la fila y la columna. Los mensajes son de esta
   forma:
   - *el archivo 'x.csv' es ilegible: no es un CSV de texto en UTF-8* (un binario, o un texto con
     otra codificación);
   - *el archivo 'x.csv' no es una fuente del dominio civil: faltan las columnas [...]* (la muestra
     de otro dominio, o un CSV al que le faltan columnas de su formato);
   - *el archivo 'x.csv', fila 'T-01': la columna 'a' esta vacia o no es numerica: ''* (una celda
     mal escrita; en telecom el mensaje dice además la línea del archivo);
   - para un `.ifc` (por la API o en el visor): *el archivo 'x.ifc' es ilegible: no es un modelo
     IFC (...)*, o *es ilegible como modelo IFC:* seguido del motivo (su cabecera STEP no se pudo
     interpretar, o declara un esquema IFC que `ifcopenshell` no soporta).

   **Límite de los `.ifc`.** Un `.ifc` con la cabecera correcta pero **truncado o con basura** en
   el cuerpo no se rechaza: `ifcopenshell` lo abre sin error y el cómputo sale vacío (o solo con
   los elementos que alcanzó a leer). Si un modelo que debería traer elementos da un cómputo vacío,
   revise el archivo.
3. Al presupuestar (**Elaborar presupuesto**), el sistema calcula cada precio unitario con la
   estructura venezolana (prestaciones, bono, administración y utilidad en cascada), arma el total
   y la curva de inversión **y audita el resultado siempre**: el informe aparece sin pedirlo, con
   el total del presupuesto, el **resumen por severidad** (cuántos hallazgos de cada severidad, o
   «Sin hallazgos»), las **reglas evaluadas** con su cuenta (sección 4) y el botón **Exportar a
   Excel**.
4. **Ítems sin partida (UC‑01 3a).** Si un ítem del cómputo tiene un código que el catálogo no
   tiene, el presupuesto **se elabora igual** con los demás y ese ítem queda **pendiente**: el
   informe lo declara con un hallazgo `PENDIENTE` y la pantalla lo lista en el bloque
   **Pendientes** (origen, código y descripción). **Después** de elaborar, la pantalla propone para
   cada pendiente las partidas del catálogo más parecidas a su descripción, con su puntaje de
   similitud. Si se elige una en el selector *Propuesta para <origen>* y se pulsa **Aplicar y
   volver a elaborar**, el ítem pasa a esa partida y el presupuesto se elabora de nuevo, ya sin ese
   pendiente. Si no se acepta ninguna, el ítem sigue pendiente y el informe lo sigue declarando.
   Si no se pudieron calcular las propuestas, el pendiente se lista igual, sin selector, y debajo
   aparece una leyenda con el tipo y el mensaje de la falla: `ImportError: …` cuando falta el extra
   `ml`; `OSError: …` cuando el modelo de lenguaje no se pudo descargar o leer (por ejemplo, la
   primera vez y sin red).
5. **Plan de trabajo (UC‑01, paso 6).** Debajo del informe está la tabla **Plan de trabajo**, con
   tres columnas: `periodo` (la etiqueta del período, por ejemplo «Semana 1»), `codigo_partida` y
   `fraccion` (la parte de la partida que se ejecuta en ese período, con punto decimal: `0.5`, no
   `0,5`). Cada fila dice qué fracción de una partida va en un período, y **las fracciones de cada
   partida suman 1**. La primera elaboración usa el plan por defecto, una partida por día, y la
   tabla viene precargada con él. Para repartir de otro modo, se edita la tabla (se pueden añadir
   y quitar filas) y se pulsa **Aplicar plan y volver a elaborar**: el presupuesto se elabora con
   ese plan, la curva de inversión sale de él (hoja *Curva* del Excel) y las reglas R2 y R7 lo
   auditan. Si alguna partida no suma exactamente 1, si el plan nombra una partida que el
   presupuesto no tiene, o si una fila está a medias o su fracción no es un número, la pantalla lo
   dice (con el número de fila cuando es de una fila) y deja a la vista el presupuesto anterior.
   Ojo: **al volver a elaborar sin el plan** (el botón **Elaborar presupuesto**, aceptar una
   propuesta del paso 4 o registrar un rendimiento del paso 6), el plan vuelve a una partida por
   día; si con eso se descartó un plan editado, la tabla lo avisa y hay que volver a aplicarlo.
6. **Rendimientos por declarar (UC‑01, flujo 3b).** Si una partida no tiene un rendimiento
   **estimado** vigente a la fecha del presupuesto (uno registrado con esa fecha o antes), el
   presupuesto no se elabora y aparece el bloque **Rendimientos por declarar**: para cada partida,
   el rendimiento que propone el histórico (el medido más reciente o, si no hay, el último
   estimado), con su tipo y su fecha, y la dispersión del histórico (observaciones, cuántas
   medidas y cuántas estimadas, media y rango). El selector *Tipo declarado del rendimiento de
   <partida>* **no trae ninguna opción marcada**: hay que declarar si es estimado o medido y pulsar
   **Registrar y volver a elaborar**.
   - Declarado **estimado**, el propuesto se registra en el catálogo con la fecha del presupuesto
     (sus condiciones dicen de dónde salió) y el presupuesto se elabora; si quedan otras partidas
     por declarar, el bloque pasa a la siguiente.
   - Declarado **medido**, no se registra nada: la elaboración solo usa rendimientos estimados, y
     la pantalla lo explica. Para usar ese valor, declárelo estimado.
   - Si la partida no tiene ningún rendimiento en el histórico, no hay propuesta: la pantalla remite
     a **Componer una partida** para declararlo con sus condiciones.
   - La propuesta sale de todo el histórico de la partida, sin mirar la fecha del presupuesto: con
     un presupuesto de fecha pasada, puede proponer un rendimiento posterior a esa fecha.
   - Si lo que falta es la **lista de precios** vigente a esa fecha (o un precio), el bloque no
     aparece: la pantalla muestra ese error.

### 3.2 Actualizar precios masivamente (UC‑02)

1. Preparar la lista nueva como CSV o XLSX con columnas `tipo,insumo,unidad,precio`
   (`tipo` ∈ material, equipo, mano_obra; ejemplo en `data/samples/precios/`).
2. Cargarla en la página: el sistema valida el archivo (si falta una columna o un precio no es
   un número, lo dice con archivo y fila), detecta qué insumos cambiaron y recalcula **todos**
   los APU afectados sin editar ninguna composición.

   **Dar de alta insumos desconocidos (UC‑02, flujo 2a).** Si el archivo trae insumos que el
   catálogo no conoce con ninguna unidad, al subirlo la pantalla avisa cuántos son y los nombra, y
   el campo **Dar de alta** los ofrece, **con ninguno elegido**. Elija antes de revalorar los que
   quiera crear: cada uno recibe un código nuevo (`MAT-NNN`, `EQU-NNN` o `MO-NNN`) y su precio entra
   **solo en la lista nueva**. Los demás se ignoran y no intervienen en el recálculo. Las filas
   cuyo insumo ya está con otra unidad no se ofrecen (flujo 2b: se rechazan). Límites: si elige
   dos filas del mismo insumo con precios distintos, el sistema lo rechaza y no escribe nada; y
   dos materiales con la misma descripción y unidades distintas se ofrecen los dos y, si se eligen
   ambos, quedan dos insumos homónimos con distinta unidad. Si el archivo o el caso no se pueden
   leer, el campo no aparece y el motivo sale al pulsar **Revalorar presupuesto**. Excepción conocida: un archivo `.xlsx` que no es un libro de Excel (corrupto o de otro formato con esa extensión) todavía no se captura y la página muestra el error de Python; conviene comprobar que el libro abre en Excel antes de subirlo.
3. Revisar el **comparativo** (precio unitario antes/después por partida, incidencia en el
   total) y el informe de auditoría de la versión nueva. Si algún insumo cambió de precio, la
   versión nueva ya quedó guardada con el código de la barra lateral; si ninguno cambió, no se
   guarda nada (UC‑02, flujo 3a; en ese caso **tampoco se guardan las altas elegidas**, porque un
   alta no es un cambio de precio: la página lo dice y las nombra). Debajo salen **tres avisos
   separados**: los insumos *dados de alta*, los *ignorados* (flujo 2a) y los *rechazados*
   (flujo 2b, otra unidad). El informe de la versión nueva puede traer hallazgos `ATIPICO`
   (ADVERTENCIA): precios de la lista nueva que se apartan del histórico de variaciones y que usa
   alguna partida del presupuesto. Solo aparecen si está instalado el extra `ml` y el histórico
   tiene al menos 8 variaciones; en otro caso no se marca ninguno y la pantalla no avisa de que no
   se evaluaron. Cada cambio queda en el histórico con precio anterior, nuevo,
   variación y fecha. Los ítems pendientes del presupuesto base (UC‑01 3a) pasan a la versión
   nueva como pendientes, aunque la lista nueva traiga su partida, y el informe los vuelve a
   declarar: valorarlos es UC‑01 (sección 3.1), no UC‑02.
4. **Descartar la versión (UC‑02, flujo 7a).** Debajo del informe aparece el botón **Descartar
   version**, solo si la última revaloración de esta sesión guardó una versión nueva: no aparece
   tras el flujo 3a ni para versiones guardadas antes. El botón **marca** la versión
   como descartada; no la borra: sigue guardada y se puede cargar como documento, y su historial
   de cambios de precio se conserva. La marca vale para la base del caso donde se guardó la
   versión, aunque después se abra otro caso. Tras pulsarlo, la página dice que la versión quedó
   descartada y el botón desaparece.

   Límites: la marca **no se deshace** desde la interfaz, y las demás páginas (histórico,
   escenarios) no la muestran. Solo se descarta la última versión guardada del proyecto, nunca
   el primer presupuesto, y una sola vez; en otro caso la página muestra el motivo. El sistema no
   guarda de qué presupuesto salió una versión, así que no distingue una versión revalorada de un
   segundo presupuesto elaborado aparte en el mismo proyecto: por eso el botón solo se ofrece para
   la versión que acaba de guardar esta página.

La decisión de guardar se toma con el número de **insumos afectados**, no con la variación del
total: una lista puede cambiar insumos que este presupuesto no usa (variación 0) y el cambio
sigue siendo real.

### 3.3 Reutilizar partidas (UC‑03)

Escribir la descripción en texto libre («excavación de zanja a mano», por ejemplo). El sistema
propone hasta **tres** partidas del catálogo con su puntaje de similitud (0 a 1; por debajo de
0,5 no propone). Al desplegar una propuesta se ven su desglose completo, su rendimiento y la
referencia a la partida de origen con el puntaje que la propuso. Si el desglose usa un insumo sin
precio en la lista vigente, la propuesta lo avisa («Desglose incompleto en la lista vigente…»,
con el insumo y la partida) y no muestra sus tablas (UC‑03, flujo 4a).

### 3.4 Rendimientos reales de obra (UC‑06)

Se registran por la API (`POST /ejecuciones` y las rutas de rendimientos): un rendimiento
**medido** exige la referencia a la ejecución de obra de la que salió — sin referencia, se
rechaza. Al consultar una partida, el sistema devuelve su histórico con dispersión (número de
observaciones, media, mínimo, máximo) y propone el valor más defendible. Si el valor introducido
se aparta del comportamiento observado, el sistema **advierte pero no impide** el registro.
`POST /partidas/{codigo}/rendimientos` acepta además el campo opcional `justificacion` (UC‑06,
flujo 4a): con advertencia, se registra ligada al rendimiento de esa misma petición y la respuesta
la devuelve; sin advertencia se ignora y la respuesta trae `justificacion: null`; con advertencia y
en blanco, responde 422 y no registra nada. Ninguna ruta ni pantalla la consulta después.

### 3.4 bis Importar el presupuesto de un tercero (UC‑05, RF‑24)

Solo por la API, sin pantalla: primero crear el proyecto (`POST /proyectos`, con `nombre`,
`descripcion` y `dominio` opcionales) y luego `POST /presupuestos/importar` con el libro XLSX y el
nombre del proyecto. El libro lleva las hojas `Datos`, `Presupuesto`, `APU`, `Insumos` y, opcional,
`Curva` (formato en el [manual técnico §9](manual_tecnico.md)). El sistema lo **valora con su motor**
sobre los APU del archivo (no lee los precios unitarios del autor), audita siempre las siete
reglas conservando las unidades que escribió el autor y guarda el presupuesto con su informe; el
informe y el libro salen por `GET /presupuestos/{codigo}/informe` y `…/excel`. Si algo falla no
queda nada escrito. Efecto que conviene saber: los APU del tercero quedan en el catálogo y la lista
«Importada: <archivo>» pasa a ser la lista vigente desde la fecha del presupuesto.

### 3.5 Contraste con el mercado (UC‑07)

`uv run python scripts/generar_resultados_ml.py` regenera [resultados_ml.md](resultados_ml.md):
la técnica de estimación que corresponde a los datos disponibles (hoy: sistema de reglas,
declarado como limitación), sus métricas (MAPE, RMSE, R²) y el contraste de cada precio
construido contra el estimado en el rango de la clase 3 de AACE.

### 3.6 Escenarios de sensibilidad (UC‑08)

En la página **Escenarios de sensibilidad** (UC‑08): elegir el presupuesto base, darle nombre al
escenario y declarar los supuestos — los cuatro parámetros de costo (precargados con los del base)
y/o una tabla de precios de ensayo por insumo (lo no mencionado conserva su precio vigente). Cada
escenario generado se suma a la tabla comparativa: el base en la primera fila y una fila por
escenario con su total y su variación absoluta y porcentual, descargable en CSV con los valores
exactos. El detalle por partida de cada escenario se despliega debajo, con el número de hallazgos
de la auditoría del escenario (que se genera siempre) y los insumos variados.

Límites: si el presupuesto base tiene ítems pendientes (UC‑01 3a), la página los lista en un aviso
al abrirlo. Los escenarios solo recalculan los renglones valorados: esos ítems no suman al total
del base ni al de ningún escenario, y la leyenda «Hallazgos de la auditoria del escenario: N» no
los cuenta, porque la auditoría del escenario no declara `PENDIENTE`. Es una limitación declarada:
que ese informe los declarase exigiría cambiar el núcleo, y la fase C4 del cierre no lo autoriza
(ruling C4‑3 de la [bitácora del cierre](bitacora/2026-09-23-cierre.md)).

El presupuesto base **nunca** se altera y ningún escenario se guarda: al cambiar de presupuesto
la comparación se descarta. Para convertir un escenario en presupuesto vigente se usa la
actualización de precios (UC‑02) con la lista correspondiente. Por software, la misma operación
está en `POST /presupuestos/{codigo}/escenarios` (API) y en `core.budget.generar_escenario`
(Python). La respuesta de la API lista los ítems pendientes del base en `pendientes_base`, cada uno
con `codigo_partida`, `descripcion`, `unidad`, `cantidad` (texto decimal exacto) y `origen_id`, sin
propuestas; la lista queda vacía si el base no tiene pendientes.

### 3.7 Componer o editar una partida a mano (UC‑10 y UC‑11, prototipo AREN.IA)

La página **Componer una partida** (UC‑10 / UC‑11) es el recorrido completo de quien presupuesta:
arma el análisis de precio de una partida, lo guarda en el catálogo, le asigna cantidades de obra y
sale con el presupuesto auditado y su Excel, sin cambiar de pantalla. Los casos de uso están en la
[ERS](ERS.md) (UC‑10 componer, UC‑11 editar; RF‑33 a RF‑35) y el diseño en la [spec del
prototipo](superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md). Para practicarlo paso
a paso con resultados esperados está el [guion de prueba manual](guion_prueba_arenia.md).

1. **Cabecera.** Código, descripción y unidad de la partida, su dominio (civil por defecto) y la
   fecha, que decide qué lista de precios está vigente. Si el código ya existe en el catálogo, lo
   que se guarde **edita** esa partida (UC‑11); si no existe, la **crea** (UC‑10).
2. **Las tres tablas de insumos: materiales, equipos y mano de obra.** Se añaden filas al pie de
   cada tabla y se escribe en las celdas:
   - *Materiales:* descripción, unidad, **consumo por unidad** de partida (incluye el desperdicio:
     1,05 si se pierde el 5 %) y precio.
   - *Equipos:* descripción, cantidad, precio y **depreciación** (la fracción del precio imputable
     a un día de uso, entre 0 y 1).
   - *Mano de obra:* descripción, cantidad de obreros, sueldo y **modalidad**: `jornal` (sueldo
     diario; recibe prestaciones y bono de alimentación y se reparte entre el rendimiento) o
     `destajo` (pago por unidad de obra, art. 114 de la LOTTT: en esta modalidad el «sueldo» es el
     precio por unidad de partida y entra completo al precio unitario, sin prestaciones ni bono).
     Vacía equivale a jornal. Una misma partida puede mezclar las dos.

   Junto a cada tabla hay un **buscador de la referencia MaPreX** (julio 2026): se escribe parte del
   nombre del insumo, se elige un resultado y se pulsa **Usar esta fila**. La fila se **añade al
   final** de la tabla ya rellena (con la referencia MaPreX que respalda el precio, y en equipos
   con su factor de depreciación).
   El precio sugerido **se puede editar** (RF‑35): MaPreX es una referencia de mercado, no la
   verdad. En equipos, el precio de MaPreX es el **valor del activo**, no una tarifa diaria: lo que
   lo lleva a costo diario es la depreciación.
3. **Rendimiento, con sus condiciones.** El campo *Rendimiento — unidades por día* es la producción
   diaria de la cuadrilla (no confundir con el consumo de material, que va en la tabla). Si la
   partida ya tiene historial, el campo viene precargado con el rendimiento propuesto (el medido
   más reciente o, si no hay ninguno, el último registrado). Las
   **Condiciones del rendimiento** son **obligatorias** (RF‑33): un rendimiento sin decir en qué
   condiciones se obtuvo (tipo de suelo, cuadrilla, equipo…) no es verificable, y el botón de
   guardar permanece deshabilitado hasta que se escriban.

   **Justificación de la advertencia (UC‑06, flujo 4a).** Cuando el rendimiento escrito se sale del
   rango observado y aparece la advertencia, se pinta debajo el campo **Justificacion de la
   advertencia (UC-06, flujo 4a)**, opcional. Si se escribe, se registra al guardar **ligada al
   rendimiento que registra ese guardado** y el aviso de éxito lo dice; si se deja en blanco, el
   rendimiento se guarda igual y se informa (la advertencia no impide). Si el guardado no registra
   un rendimiento nuevo (mismo valor y condiciones que el último estimado), la justificación no se
   registra y se avisa. El campo no aparece con el aviso del bosque de aislamiento (ayuda 3) solo.
4. **Desglose en vivo.** Mientras se escribe, la página recalcula materiales, equipos, mano de
   obra, costo directo, costo con administración y **precio unitario**, con la misma fórmula del
   resto del sistema. Si una fila está incompleta o mal escrita, un aviso dice en qué tabla, qué
   fila y qué campo.
5. **Las cuatro ayudas.** Todas **sugieren y ninguna bloquea**: el guardado nunca depende de ellas.
   1. *Partidas similares del catálogo:* propuestas de solo lectura a partir de la descripción;
      lo útil se copia a mano.
   2. *Precio atípico:* avisa si un precio se aparta del histórico de cambios de ese insumo; sin
      histórico, se abstiene.
   3. *Rendimiento atípico:* avisa si el rendimiento escrito se sale del rango observado para la
      partida (hacen falta al menos dos observaciones) y, con historial suficiente, añade la
      lectura del bosque de aislamiento.
   4. *Contraste con la estimación por reglas (AACE):* solo para partidas que ya existen; compara
      el precio construido con el estimado y dice si cae en el rango de la clase 3 de AACE. Para
      una partida nueva, la sección aparece con un aviso: la estimación por reglas parte del
      precio unitario anterior de la partida, que no existe, así que el contraste no es posible
      (UC‑07, flujo 3a).
6. **Guardar y editar.** **Guardar composicion** crea o reemplaza el desglose de la partida. Al
   editar, el rendimiento anterior **no se pisa**: si el valor o las condiciones cambiaron, se
   registra uno nuevo y el anterior queda en el histórico; si no cambió nada, no se añade ruido.
   Si no hay ninguna lista de precios vigente a la fecha de la cabecera, la página lo dice y no
   guarda.
7. **Cantidades de obra, con su origen.** En la tabla *Cantidades de obra* se elige una partida
   ya guardada, su cantidad y su **origen** (de qué plano, cómputo o medición sale). El origen es
   obligatorio: una cantidad sin origen no es trazable.
8. **Elaborar.** Con al menos una cantidad válida aparece **Elaborar y auditar** (código, fecha y
   moneda del presupuesto). El sistema arma el presupuesto, su curva de inversión con un plan de
   una partida por día y el informe de auditoría. Repartir el plan de trabajo y declarar un
   rendimiento que falta (flujo 3b) se hacen en **Elaborar un presupuesto** (sección 3.1, pasos 5
   y 6), no en esta página: aquí, si a una partida le falta el rendimiento, se muestra el mensaje
   del catálogo.
9. **El informe de auditoría** se muestra siempre, tenga hallazgos o no (sección 4), con el total
   del presupuesto y el recuento por severidad.
10. **Descarga en Excel.** El botón **Exportar a Excel** entrega el libro del presupuesto; su hoja
    de APU muestra la columna *Modalidad* de cada línea de mano de obra, para que un destajo no se
    lea como sueldo diario.

## 4. El informe de auditoría

Se genera **siempre** — no existe forma de obtener un presupuesto sin él. Ejecuta las siete
reglas R1–R7 (trazabilidad de cantidades, cierre exacto de la curva, coherencia de unidades,
correspondencia de especificaciones, balance volumétrico, criterio único de depreciación y
conciliación con el plan; detalle en [CLAUDE.md §7](../CLAUDE.md)). Cada hallazgo trae:

- **severidad** (el informe se ordena de mayor a menor);
- **descripción e impacto cuantificado** (cuánto dinero o cuánta cantidad está en juego);
- **los `origen_id` involucrados**, para ir directo a la fila del cómputo o del plan que lo causó.

Una regla que no pueda evaluarse (por ejemplo, R2 sin curva) aparece como hallazgo informativo y
no interrumpe a las demás. Sobre el caso de estudio, el sistema detecta las **7 de 7**
inconsistencias del presupuesto original.

**Cómo se lee en pantalla.** El informe tiene cuatro partes, en este orden:

1. La cabecera: «Hallazgos: N · Resultado: CUMPLE» o «NO CUMPLE».
2. **Resumen por severidad:** cuántos hallazgos hay de cada severidad.
3. **Reglas evaluadas:** una fila por cada regla que corrió (R1 a R7), con su nombre y cuántos
   hallazgos dio. Una regla con 0 **se verificó y no encontró nada**; así el informe dice qué
   comprobó aunque no haya hallazgos.
4. **Hallazgos:** la tabla, con la regla, la severidad, la **partida**, la descripción, el impacto y
   los valores observado y esperado.

Con **cero hallazgos**, el informe se emite igual: el resumen y la tabla dicen «Sin hallazgos.» y la
sección de reglas evaluadas lista las siete con 0.

Tres detalles de la tabla de reglas evaluadas:

- **«No aplicable» cuenta 1.** Si el presupuesto no tiene plan de trabajo, R2 y R7 no se pueden
  aplicar y cada una lo declara con un hallazgo informativo: por eso muestran 1 aunque no haya
  ningún defecto.
- **Los `PENDIENTE` no se enumeran.** El hallazgo `PENDIENTE` de un ítem sin partida (sección 3.1,
  paso 4) no es una de las siete reglas: lo declara la elaboración. Con pendientes, la suma de la
  tabla de reglas es menor que el «Hallazgos: N» de la cabecera, y la diferencia son exactamente
  los `PENDIENTE`, que sí están en la tabla de hallazgos.
- **Los `ATIPICO` tampoco se enumeran, y no cambian el veredicto.** El informe de una versión
  revalorada (sección 3.2) puede traer hallazgos `ATIPICO`, de severidad ADVERTENCIA: precios de la
  lista nueva atípicos frente al histórico. Como los `PENDIENTE`, no son una de las siete reglas: no
  cuentan en «Reglas evaluadas», sí en el «Hallazgos: N» de la cabecera y en la tabla de hallazgos.
- Las cuentas incluyen los hallazgos informativos, no solo los errores.

**La columna Partida.** La partida de cada hallazgo la declara la regla que lo emitió; no se
adivina. Es un **ancla** para ubicar el hallazgo, y la descripción da el detalle:

- una conciliación de R7 que abarca varias partidas se ancla en **la primera** de ellas en el orden
  del presupuesto, y R6 en **su primer código** (la partida del factor minoritario); en los dos
  casos la descripción nombra todas las partidas;
- la columna dice «-» cuando no hay una sola partida que nombrar: lo que es del presupuesto entero
  (el cierre de la curva de R2, las declaraciones «no aplicable», un período del plan que no nombra
  ninguna partida) o un hallazgo cuyo origen comparten varias partidas sin que ninguna regla lo haya
  declarado.

## 5. Exportar

- **Excel:** presupuesto y curva en un libro XLSX (desde la página de actualización, desde
  **Elaborar un presupuesto** o de **Componer una partida** tras elaborar, secciones 3.1 y 3.7, o
  `GET /presupuestos/{codigo}/excel` en la API). Las celdas presentan dos decimales; los totales del
  libro cuadran con los del sistema porque el redondeo es solo de celda. La hoja **Auditoria** es el
  informe: una fila por hallazgo en las columnas A a E (regla, severidad, descripción, impacto y
  orígenes) y, separadas por la columna F vacía, las **reglas evaluadas** en las columnas G a I
  (regla, nombre y número de hallazgos), con los mismos criterios de la sección 4. Sin hallazgos,
  la columna A trae solo el encabezado y G a I, las siete reglas con 0. La hoja no tiene columna de
  partida: esa está en el informe en pantalla.
- **Informe:** `GET /presupuestos/{codigo}/informe`.
- **Tabla de escenarios:** botón de descarga CSV en la página de escenarios (valores exactos,
  sin redondeo de presentación).

## 6. Archivos de muestra

| Archivo | Dominio | Para probar |
|---|---|---|
| `data/samples/tanquilla.ifc` | civil (IFC) | UC‑01 y visor 3D; cantidades exactas al cálculo manual |
| `data/samples/civil/tanquillas_y_zanja.csv` | civil (tabular) | UC‑01 con mapeo de códigos |
| `data/samples/telecom/topologia_arenaza.csv` | telecom | nodos y enlaces con reserva de cable |
| `data/samples/industrial/activos_planta.csv` | industrial | activos con frecuencia de intervención |
| `data/samples/sistemas/alcance_funcional.csv` | sistemas | módulos y puntos de función |
| `data/samples/precios/lista_2026-06-01.csv` | — | UC‑02 (sube cemento y arena) |

Cada carpeta trae su `README.md` con el formato exacto de columnas.

## 7. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| «instala el extra civil» al cargar un `.ifc` | Falta `ifcopenshell`: `uv sync --extra civil` |
| Error 409 «catálogo incompleto» | Falta la lista de precios vigente o un precio para una partida: revisar la lista de precios cargada o volver a sembrar (`scripts/seed.py`) |
| Error 409 con `rendimientos_por_declarar` en `POST /presupuestos` | Una partida no tiene rendimiento estimado vigente (UC‑01 3b): la respuesta trae, por partida, el rendimiento que propone el histórico con su dispersión. Registrarlo como estimado con `POST /partidas/{codigo}/rendimientos` (fecha no posterior a la del presupuesto) y volver a enviar el presupuesto; en la pantalla, el bloque **Rendimientos por declarar** (sección 3.1, paso 6) |
| «las fracciones del plan de trabajo deben sumar exactamente 1 por partida» | El plan de la tabla **Plan de trabajo** (o el campo `plan` de la API, que responde 422) no reparte entera alguna partida: corregir sus fracciones |
| Un `.ifc` da un cómputo vacío sin error | El archivo tiene la cabecera correcta pero el cuerpo truncado o dañado, o ningún elemento con `Pset_APU`: `ifcopenshell` no lo rechaza (límite declarado, sección 3.1) |
| La UI no encuentra datos | El caso abierto no tiene partidas: en **Inicio**, **Cargar el caso de demostracion**, o sembrar como en el paso 1 de la sección 2 |
| «Partidas similares» tarda la primera vez | Descarga única del modelo de lenguaje; después queda en caché |
| Un rendimiento medido se rechaza | Falta la referencia a la ejecución: es una invariante, no un error |
| Error «… precios distintos» al dar de alta en **Actualizar precios** (o 422 en `POST /listas-precios`) | Dos filas elegidas son el mismo insumo con precios distintos: dejar una sola o corregir el archivo. Nada se escribió |
| «Dar de alta» no aparece al subir la lista | El caso aún no existe, el archivo o la base no se pueden leer, o no hay insumos desconocidos; el motivo, si lo hay, sale al pulsar **Revalorar presupuesto** |
| 422 «justificacion … no puede estar vacia» en `POST /partidas/{codigo}/rendimientos` | Con advertencia, la justificación vino en blanco: enviar texto o no enviar el campo. El rendimiento no se registró |
| 404 en `POST /presupuestos/importar` | El proyecto no existe: crearlo con `POST /proyectos` |
| 422 en `POST /presupuestos/importar` | El archivo no es un libro XLSX legible o le faltan hojas, columnas o claves (el mensaje nombra archivo, hoja y fila); un código de partida ya está en el catálogo; el código de presupuesto ya existe en el proyecto; o la moneda no es exactamente la de la lista vigente. No quedó nada escrito |
| 422 en `POST /proyectos` | Nombre vacío o repetido, o un dominio distinto de civil, telecom, industrial o sistemas |
| 500 en `POST /presupuestos/{codigo}/actualizacion` con una lista que carga bien | Dos listas con el mismo nombre (por ejemplo, al cargar dos veces el archivo para ver los desconocidos): el nombre debe ser único |
| «Guardar composicion» no se puede pulsar | Faltan las condiciones del rendimiento (RF‑33): escribirlas |
| «no hay ninguna lista de precios vigente» al guardar | La base está vacía o la fecha es anterior a toda lista: sembrar con `scripts/seed_demo.py` o cambiar la fecha |
| La barra lateral no muestra el caso esperado bajo «Caso abierto» | Abrirlo en **Inicio** (*Archivo del caso (SQLite)* y *Abrir este caso*) o arrancar con `ARENIA_CASO=<ruta>`: recargar la página (F5) vuelve a la ruta de `ARENIA_CASO` o, sin ella, a `data/apu.db` |
