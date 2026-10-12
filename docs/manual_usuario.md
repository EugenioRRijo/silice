# Manual de usuario — Sesión F.3

Guía de operación del sistema de generación y auditoría de Análisis de Precios Unitarios (APU)
para el proyectista. No hace falta saber programar: todo se opera desde la interfaz web local.
Qué es el sistema y por qué calcula como calcula está en [NORMAS.md](../NORMAS.md) y en la
[ERS](ERS.md); este manual solo explica **cómo usarlo**.

## 1. Instalación

La forma normal de instalar Sílice es el instalador de Windows (`Silice-<versión>.exe`, o
`Silice-<versión>-completo.exe` con la similitud de partidas): no necesita permisos de
administrador ni internet. Compruebe su huella y su firma antes de ejecutarlo; todos los pasos, la
red local, los respaldos y los problemas frecuentes están en el
[manual de instalación](manual_instalacion.md).

Después de instalar, el acceso «Sílice» del menú Inicio abre la aplicación en el navegador. Para
detenerla, cierre la ventana minimizada «Sílice» o use «Detener Sílice».

### Instalación para desarrollo

Quien trabaja sobre el código (no el usuario final) sigue esta ruta; el entorno de desarrollo
completo está en el [manual técnico](manual_tecnico.md#2-entorno-de-desarrollo).

- Windows o Linux con **Python 3.12 o superior** y [uv](https://docs.astral.sh/uv/) instalados.
- Clonar o copiar la carpeta del proyecto y, dentro de ella, ejecutar:

```
uv sync --extra ui --extra api --extra civil --extra planos --extra ml
```

No hay más pasos (RNF‑07). Notas:

- El extra `ui` exige **Streamlit 1.62 o superior**: el menú superior (`position="top"`) no existe en versiones anteriores.
- El extra `planos` instala `ezdxf` (importar planos DXF en la hoja del proyecto) y `civil`,
  `ifcopenshell` (importar planos IFC); sin ellos, importar un plano avisa que falta el componente.
- El extra `civil` instala `ifcopenshell` (modelos IFC); `ml` instala scikit‑learn y
  sentence‑transformers. Sin el extra correspondiente, esas funciones avisan que faltan en vez de
  fallar en silencio.
- La **primera** consulta de «Partidas similares» descarga el modelo de lenguaje y lo deja en
  caché local. Es la única conexión de red del sistema (RNF‑08); todo lo demás corre local.

## 2. Puesta en marcha

Con el instalador no hace falta sembrar nada a mano; Inicio ofrece el caso de demostración.

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
   (lista *Casos de la carpeta de datos* y botón *Abrir este caso*; la base se copia antes a
   `data/casos/` con `uv run python -m operacion adoptar <ruta> --nombre <caso>`); la barra lateral lo muestra bajo
   **Caso abierto** y todas las pantallas trabajan sobre él (por defecto, `data/casos/silice.db`). También se
   puede arrancar la interfaz con la variable `SILICE_CASO=<ruta>`. En la API, arrancar con la
   variable de entorno `APU_BASE` apuntando a esa base (por ejemplo
   `sqlite:///data/apu_telecom.db`). De dónde sale cada precio y con qué fecha: [manual técnico,
   sección 8.1](manual_tecnico.md#81-catálogos-por-dominio).

> **Nombres de las variables.** Desde la 0.6.0 se llaman `SILICE_CASO` y `SILICE_MODO_ENTREGA`.
> Los nombres anteriores, `ARENIA_CASO` y `ARENIA_MODO_ENTREGA`, se aceptan como alias solo
> hasta la 0.6.0; si están las dos, manda la nueva (`ui/entorno.py`).

   **Dejar lista la aplicación para componer partidas.** Una sola orden siembra
   la línea base de la clínica, tres partidas de demostración (`DEMO-01-INST`, `DEMO-02-VALV`,
   `DEMO-03-PRUEBA`) y el presupuesto de ejemplo `DEMO-001` con su informe de auditoría:

   ```
   uv run python scripts/seed_demo.py                                   # data/apu.db
   uv run python scripts/seed_demo.py --db data/prueba_arenia.db --reiniciar
   ```

   Es idempotente: repetirla no duplica nada. **`--reiniciar` borra la base antes de sembrarla**:
   úselo solo sobre una base de prueba, nunca sobre una con trabajo propio. Todo lo que siembra es
   un **caso didáctico** (ejercicio académico, no obra ejecutada ni precios cotizados; ver
   [NORMAS.md §1](../NORMAS.md)). Al terminar, la terminal muestra el total del presupuesto de
   ejemplo y la línea `Auditoria: 3 hallazgo(s), CUMPLE`.

2. **Abrir la interfaz** (se abre en el navegador, en el equipo local):

   ```
   uv run python -m streamlit run ui/app.py
   ```

   **Modo entrega.** Para mostrar solo la sección **Trabajo** (Inicio y las cinco pantallas que
   usa quien presupuesta: catálogo, componer, elaborar, actualizar precios e histórico) y omitir la
   sección **Investigacion** (escenarios, partidas similares, simulador y visor 3D), se arranca con
   la variable `SILICE_MODO_ENTREGA` en `1` (exactamente `1`; cualquier otro valor la deja apagada):

   ```
   SILICE_MODO_ENTREGA=1 uv run python -m streamlit run ui/app.py                  # bash
   $env:SILICE_MODO_ENTREGA = "1"; uv run python -m streamlit run ui/app.py        # PowerShell
   ```

3. **API HTTP** (opcional, para integrar con otro software):

   ```
   uv run uvicorn api.main:app
   ```

   La documentación interactiva queda en `http://127.0.0.1:8000/docs`. Todos los montos viajan
   como **texto** (`"1586.61"`), nunca como número JSON: así no se pierde precisión decimal.

## 3. Las pantallas

La interfaz tiene once pantallas en dos secciones del **menú superior** (desde el sprint final
el menú va arriba, no a la izquierda), **Trabajo** e **Investigacion** (en modo entrega, solo
Trabajo; sección 2). Bajo el menú, en todas las pantallas, está la **barra de herramientas**
(sección 3.0 bis). Se abre en **Inicio**. Cada pantalla
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
| Trabajo | **Hoja del proyecto** | UC‑13 a UC‑16 | Describir el espacio en tablas o importar un plano, editar APU, precios y parámetros, ver el punto de equilibrio, guardar versiones con fuente, cotizar y exportar el Excel (sección 3.8) |
| Trabajo | **Actualizar precios** | UC‑02 | Cargar una lista de precios nueva (CSV/XLSX) y revalorar un presupuesto guardado |
| Trabajo | **Historico de cambios de precio** | UC‑02 | Cambios de precio registrados, con filtros |
| Investigacion | **Escenarios de sensibilidad** | UC‑08 | Recalcular un presupuesto bajo supuestos («¿y si…?») sin alterarlo |
| Investigacion | **Partidas similares** | UC‑03 | Buscar en texto libre partidas parecidas para reutilizar su desglose |
| Investigacion | **Simulador de listas** | apoyo | Generar listas de precios de prueba, deterministas |
| Investigacion | **Visor 3D del modelo** | apoyo a UC‑01 | Ver el modelo IFC junto a la tabla elemento ↔ partida |

Con `SILICE_CASO=<ruta>` la aplicación fija ese caso sin tener que abrirlo en el Inicio (la
aplicación sigue arrancando en el Inicio).

**Casos de uso sin pantalla propia.** La tabla cubre los casos de uso que tienen pantalla; los
demás se operan por otra capa (la correspondencia completa entre caso de uso y capa está en la
[ERS §3.1](ERS.md)). UC‑04, recalcular las cantidades ante un cambio de dimensiones, existe en el
adaptador civil (`adapters/civil/recalculo.py`) y no tiene pantalla ni ruta de la API. UC‑05 se ve
en el informe de auditoría que acompaña a todo presupuesto elaborado (sección 4). El presupuesto
de un tercero se importa solo por la API, sin pantalla (RF‑24, desde la fase C6; sección 3.4 bis).
UC‑01 también tiene un paso previo: crear el proyecto sobre el que luego se elabora o se importa.
Se hace con `POST /proyectos` en la API y, desde el sprint final, con la herramienta **Proyecto**
de la barra superior (RF‑63, sección 3.0 bis); las dos rechazan el nombre vacío o repetido.
Los rendimientos medidos de UC‑06 se registran por la API (sección 3.4), y las métricas y el
contraste completo de UC‑07 se generan con un script (sección 3.5); de los dos, la pantalla
**Componer una partida** ofrece una parte como ayudas: propone el rendimiento del histórico,
advierte si se aparta y contrasta el precio con la estimación por reglas (sección 3.7); **Elaborar
un presupuesto** propone también el rendimiento del histórico cuando a una partida le falta
(sección 3.1, paso 6). En UC‑01, el `.ifc` civil entra por la API (sección 3.1).

### 3.0 Inicio: el caso abierto y los recorridos guiados (UC‑12)

1. **El caso.** La lista *Casos de la carpeta de datos* y el botón *Abrir este caso* fijan la base con que trabajan
   todas las pantallas durante la sesión. Los casos viven en la carpeta de datos (`data/casos/` en desarrollo): se
   elige uno de la lista, se crea con un nombre (*Crear o subir un caso*) o se sube un `.db`. No hay campo con la
   ruta: una ruta de red, absoluta o con `..` se rechaza sin crear nada. Si el caso es de una versión anterior,
   Sílice lo respalda y lo actualiza al abrirlo.
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

### 3.0 bis La barra de herramientas y los proyectos (RF‑60, RF‑63)

Debajo del menú superior, y en el mismo lugar de todas las pantallas, hay una fila de herramientas.
La barra lateral queda para lo que ya mostraba: el caso abierto y el paso del recorrido activo.

| Herramienta | Qué hace |
|---|---|
| **Proyecto** | Muestra el caso abierto, el proyecto abierto y su versión vigente. Permite **crear** un proyecto nuevo y **abrir** uno del caso. |
| **Importar plano** | Lleva a la pestaña *Espacio y metrajes* de la hoja del proyecto con el bloque **Importar plano (DXF o IFC)** abierto (sección 3.8, «Importar un plano», UC‑14). La herramienta solo falta si la copia del programa está incompleta (no trae el paquete de importación de planos). Lo que falta de los componentes opcionales para leer el archivo se avisa al pulsar **Leer plano**, con el comando para instalarlo. |
| **Precios** | Lleva a la pestaña *Precios* de la hoja del proyecto: el origen de cada precio y las cotizaciones. |
| **Auditar** | Resume el informe de auditoría de la versión vigente del proyecto abierto: cuántos hallazgos y de qué severidad. El sistema audita siempre; el botón solo lo muestra. |
| **Guardar version** | Lleva a la hoja del proyecto con el panel **Guardar version y exportar a Excel** abierto: ahí se escriben la fuente y el responsable y se guarda (sección 3.8). |
| **Exportar Excel** | Lleva a la hoja del proyecto y prepara el libro de Excel de la hoja (no el de *Elaborar un presupuesto*); se descarga con **Descargar Excel** en el mismo panel. Archivo: `hoja_<código de la versión>.xlsx`. |
| **Recorrido guiado** | Sin recorrido elegido, lleva al Inicio para elegir uno. Con uno elegido dice **Retomar: <recorrido>** y lleva a su paso siguiente (o a su primer paso si usted está en otra pantalla). |

**Crear un proyecto.** Abra el desplegable **Proyecto**, escriba el nombre en *Nombre del proyecto
nuevo* y pulse **Crear proyecto**. El nombre debe ser **único en el caso** y **no vacío**: un nombre
en blanco se rechaza con «Escriba un nombre para el proyecto: no puede quedar vacio», y uno que ya
existe (aunque cambien las mayúsculas o los espacios sobrantes) con «Ya existe un proyecto llamado
…». Si el caso no existe todavía, el mensaje lo dice y no crea el archivo: ábralo o siémbrelo antes
en el Inicio. Al crearlo, el proyecto queda abierto; un proyecto nuevo aún no tiene versión
vigente («sin version guardada»), y la hoja del proyecto lo trata como un proyecto sin versiones:
se describe el espacio o se importa un plano y se guarda la **primera versión** con **Guardar
primera versión** (sección 3.8, «Guardar la primera versión»).

**Abrir un proyecto.** En el mismo desplegable, elija uno en *Abrir un proyecto del caso* y pulse
**Abrir**. La **versión vigente** es la última versión guardada del proyecto que no se descartó
(la que marca *vigente* el historial de la hoja). Al abrir un proyecto en la barra, la **Hoja del
proyecto** lo muestra abierto en su versión vigente.

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

### 3.7 Componer o editar una partida a mano (UC‑10 y UC‑11)

La página **Componer una partida** (UC‑10 / UC‑11) es el recorrido completo de quien presupuesta:
arma el análisis de precio de una partida, lo guarda en el catálogo, le asigna cantidades de obra y
sale con el presupuesto auditado y su Excel, sin cambiar de pantalla. Los casos de uso están en la
[ERS](ERS.md) (UC‑10 componer, UC‑11 editar; RF‑33 a RF‑35) y el diseño en la spec del
prototipo. Para practicarlo paso
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

### 3.8 Hoja del proyecto (UC‑13 a UC‑16)

La **Hoja del proyecto** es el borrador de un presupuesto de obra: se describe el espacio, el sistema
deriva las cantidades (agua, datos y electricidad), las valora con los APU del caso, las audita y las
guarda como **versiones** con su fuente y su responsable. Arriba, el selector **Proyecto** elige
**(borrador nuevo, sin guardar)** o un proyecto del caso, y **Version** elige cuál abrir (la vigente
viene marcada). Nueve pestañas; solo se ejecuta la que está abierta:

| Pestaña | Qué hace |
|---|---|
| **Espacio y metrajes** | Tablas editables de orígenes de medida, ambientes, fuentes, puntos y vértices de recorridos; el bloque **Importar plano (DXF o IFC)**; las **cantidades derivadas**; la columna **Estado** de cada fila (el peor hallazgo que la toca); el total y el informe de auditoría |
| **APU** | Elegir una partida y editar la **cantidad** de cada línea y el **rendimiento**, o cambiar el insumo de una línea. Se edita la **copia de esta versión**: el catálogo no cambia |
| **Presupuesto** | Un renglón por partida con su cantidad, precio unitario, total y Estado |
| **Plan y curva** | El reparto de las partidas por periodo y la curva de inversión |
| **Punto de equilibrio** | Ventas, costo variable, costo fijo, utilidad, el punto de equilibrio, su porcentaje de las ventas y el periodo en que se alcanza. Se **deriva** de los costos, los parámetros y el plan: se mueve al editarlos, no se escribe |
| **Precios** | De dónde sale el precio de cada insumo (lista, referencia, fecha, moneda, tasa) y las **cotizaciones**: registrar una (proveedor, número, fecha, responsable) crea una versión nueva; retirarla, otra |
| **Parámetros** | Factor de prestaciones (FCAS), bono de alimentación, administración y utilidad |
| **Auditoría** | El informe de auditoría del borrador (sección 4), con las reglas del espacio |
| **Trazabilidad** | El historial de versiones (cuál es la vigente, de cuál sale cada una), el registro de cada celda cambiada con su fuente, responsable y hora, y **Restaurar** una versión anterior (crea una versión nueva, copia de la elegida; nada se borra) |

**De dónde salen los precios.** Los precios de referencia del sistema salen de los listados
**MaPreX de julio de 2026** (materiales, equipos y mano de obra); un insumo que no viene de una lista aparece con el estado «Sin referencia». Los listados están en bolívares y el
sistema los convierte a dólares con la tasa **633,3644 Bs/USD del 01/07/2026**. En la pestaña
**Precios** cada insumo muestra la **lista** de la que sale, su **referencia** (*Ref*, el renglón del
listado), la **fecha** del precio, la **moneda** y la **tasa** usada. Si usted tiene una cotización
distinta, la registra con su fuente (proveedor, número y fecha): vale **solo para ese proyecto**, no
cambia la lista ni los demás proyectos, y se puede retirar para volver al precio de la lista. La
pestaña **Precios** solo se llena cuando hay una versión guardada: sin versión dice «Abra una version
guardada para ver el origen de sus precios». Son **referencias de julio de 2026**, no una lista vigente:
antes de usar un presupuesto para contratar, valide los precios con una ronda actual.

Una fila inválida muestra un mensaje que dice fila y campo, y la hoja sigue con el último borrador
válido. Mientras haya cambios sin guardar la hoja lo avisa, y cambiar de versión o de proyecto pide
confirmar que se descartan.

**Importar un plano (UC‑14).** Pulse **Importar plano** en la barra, o abra el bloque **Importar plano
(DXF o IFC)** en *Espacio y metrajes*.

1. Elija el archivo en el cuadro *Plano* (solo `.dxf` o `.ifc`) y pulse **Leer plano**. Si el dibujo no
   declara su unidad, el sistema lo dice y pide **Unidad del dibujo**: elíjala y pulse **Continuar con
   esta unidad**. Un archivo que no se puede leer se explica y no cambia nada.
2. Lea el **informe de la importación**: cuatro contadores (**Importado**, **No reconocido**,
   **Aproximado**, **Pendiente**) y una tabla con cada línea («En el plano», «Fila de la hoja», «Qué
   pasó»). Lo no reconocido no se adivina: queda en el informe.
3. En **Alturas pendientes** escriba en metros (por ejemplo `2,50`) la altura de cada ambiente que el
   plano no trae y pulse **Cargar alturas**; los que deje en blanco siguen pendientes y entran con
   2,5 m provisionales. En **Circuitos por declarar** confirme o corrija los conductores y los puntos
   máximos de los circuitos que el plano no trae (se supusieron) y pulse **Declarar circuitos**.
4. Pulse **Fusionar con el espacio del borrador**: las filas entran al **borrador**, nunca a una
   versión, y la auditoría las evalúa como a las demás. Reimportar el mismo plano actualiza las filas y
   marca las que ya no están. Para descartar sin fusionar, **Descartar la importación**.

Las filas importadas citan el plano como origen de medida: la auditoría deja de marcarlas como
supuestos. Nada queda guardado hasta que usted guarde una versión.

**Guardar una versión (UC‑15).** Con una versión abierta y cambios, el panel **Guardar version y
exportar a Excel** pide la **Fuente del cambio** (por qué y con qué respaldo) y el **Responsable**; sin
ellos el botón **Guardar version** está deshabilitado y su ayuda dice qué falta. Al guardar, cada celda
cambiada queda en el registro de la versión nueva. Sin cambios no hay nada que guardar, y una versión en
solo lectura (alguna partida ya no tiene APU vigente) no se puede guardar.

**Guardar la primera versión de un proyecto nuevo.** Un proyecto recién creado en la barra no tiene
versiones: la hoja lo dice con el aviso **Este proyecto aún no tiene versiones**. Describa el espacio
(o importe un plano) —lo que ya había escrito se conserva al elegir el proyecto—, abra el panel
**Guardar version y exportar a Excel**, escriba la **Fuente de la medida** (de dónde salen los datos:
un plano, un acta) y el **Responsable**, y pulse **Guardar primera versión**. La hoja guarda la `001`
y la abre. Decisiones que conviene conocer: los **precios** son los de la lista vigente a la fecha
del borrador (si el catálogo no tiene ninguna, el mensaje lo dice y no se guarda nada: cárguela
en *Actualizar precios*); los **parámetros** son los que muestra la pestaña *Parámetros* (los de la
aplicación mientras no los cambie; los puede editar después y guardar una versión nueva); si no
hay plan de trabajo se usa el **plan secuencial** (una partida por periodo), que puede editar en
*Plan y curva*; y la versión deja **un registro de creación** (pestaña *Trazabilidad*) con su fuente y
su responsable. Desde la segunda versión se usa **Guardar version**, como siempre.

**Exportar el Excel (UC‑16).** **Exportar Excel** de la barra, o **Preparar Excel** en el panel, genera el
libro de la hoja y **Descargar Excel** lo entrega (`hoja_<código>.xlsx`): las hojas de la hoja del
proyecto con sus fórmulas vivas, más una hoja por tabla del espacio. El libro se genera solo al pedirlo.

**Limitaciones del prototipo.** (1) Cerrar la pestaña del navegador con
cambios sin guardar los pierde: Streamlit no deja avisar. (2) Los datos de ejemplo (OF‑001) son un caso
construido, no una obra ejecutada.

### 3.9 Moneda, precios de la empresa, índices del BCV y reajuste (UC‑17 y UC‑18)

Desde la versión 0.6.0 cada proyecto tiene **su moneda** (Bs o USD), cada precio dice de dónde sale y
cuánto valor perdió, una empresa puede tener **su lista de precios**, el sistema lee los archivos del
**BCV** que usted descarga y calcula el **reajuste** de la obra ejecutada de dos maneras, lado a lado.
Nada de esto usa internet: el sistema lee lo que usted bajó.

**La moneda del proyecto.** Al crear un proyecto en la barra (**Proyecto**), elija la **Moneda del
proyecto**: Bs o USD. No tiene valor por defecto; sin elegirla, el proyecto no se crea. Una versión se
valora solo con una lista de su moneda: guardar o revalorar con una lista de otra moneda se rechaza y el
mensaje lo dice. En la pestaña **Parámetros** de la hoja verá la moneda del proyecto y el bloque
**Cambiar la moneda**: elija la moneda destino y la tasa del BCV (venta, por defecto, o compra), escriba
por qué se cambia y quién lo hace, y pulse **Convertir la version**. Se crea una **versión nueva**
convertida con la tasa del BCV de hoy (la de fecha valor más reciente que no pase de hoy); la versión
anterior no cambia. Si la última tasa importada tiene más de 7 días, no se convierte nada y el mensaje
lo dice: importe antes la tasa en **Indices del BCV**.

**De dónde sale cada precio.** La pestaña **Precios** de la hoja muestra, por insumo, la moneda y el
precio originales, la fecha del precio, la tasa con su fecha y su fuente, la fuente del precio, si es
**propio** o **heredado** de la lista base (en una lista de empresa) y la **erosión** a hoy: cuánto
valor perdió el precio, en USD, en Bs y en porcentaje. El porcentaje es la fracción del valor que se
perdió (1 − tasa del precio ÷ tasa de hoy), no la erosión en Bs dividida entre el precio. Ejemplo: un
precio de 1 000 Bs del 01/07/2026 (tasa 633,3644) evaluado al 01/10/2026 (tasa 860,18) perdió 0,42 USD,
que son 358,11 Bs, un **26,37 %** (no 35,81 %). Un precio en USD tiene erosión 0: el sistema no tiene un
índice de inflación en dólares y lo declara. Si hay una serie de índices cargada, la **erosión por
índice** va en su propia columna y no se suma a la otra. La columna **Estado** agrega los hallazgos de
R11 y R12 de hoy.

**Índices del BCV (UC‑17, pasos 1 a 3).** En la pantalla **Indices del BCV**:

1. Elija qué archivo es: la **tasa de referencia** (el `.xls` trimestral), el **INPC** (`.xls` mensual)
   o **una serie en CSV canónico**. Súbalo, escriba la dirección de la página del BCV de donde lo bajó
   (tiene que ser de `bcv.org.ve`) y la fecha de descarga, y pulse **Leer**.
2. Lea el **informe previo**: las series, cuántas filas se leyeron, cuántas se rechazaron y por qué
   (fecha repetida, fuera del trimestre, posterior a la descarga, valor no numérico…) y cuántas son
   provisionales. Todavía no se guardó nada.
3. Escriba el **responsable** y pulse **Confirmar la importacion**. El mismo archivo dos veces no
   escribe nada. Un INPC revisado por el BCV entra como una importación nueva: los estudios de reajuste
   ya guardados siguen usando la que citaron.

El **CSV canónico** sirve para el índice de insumos de la construcción (mientras su formato no esté
documentado) o para cualquier serie si el BCV cambia su formato: columnas
`serie,fecha,valor,provisional,fuente`, fechas `AAAA-MM-DD`, punto decimal, `si`/`no` en
`provisional` y la **fuente en cada fila**. Al confirmar, declare el nombre, el organismo, la unidad y la
periodicidad de cada serie.

**Precios de la empresa (UC‑17, pasos 4 y 5).** En la pantalla **Precios de la empresa**:

1. Pulse **Cargar la referencia MaPreX en Bs** (una vez por caso): los 111 precios de julio de 2026 en
   bolívares, con su Ref, contra los que se comparan los de la empresa.
2. Cree la lista: nombre y RIF de la empresa, **lista base** (la que completa los insumos que la empresa
   no cotiza), **moneda** (sin valor por defecto), fecha, fuente y el archivo (CSV o XLSX con las
   columnas `tipo`, `insumo`, `unidad`, `precio` y, opcionales, `fecha`, `fuente`, `referencia`,
   `moneda`, `tasa`, `fecha_tasa`, `fuente_tasa`). **Use punto decimal**: `13288.00`, nunca
   `13.288,00`; una cifra con coma se rechaza con su fila. Los insumos que el catálogo no conoce se
   listan y no entran. La lista de una empresa no es la lista vigente de nadie: solo la usa la versión
   que la elige, y no cambia la valoración de ningún otro proyecto.
3. Revise los **precios vencidos o fuera de rango** a la fecha de evaluación (hoy, por defecto). Sin
   versión, el impacto es por unidad de insumo; en la hoja de una versión es el dinero en su total.

| Regla | Qué marca | Severidad |
|---|---|---|
| **R11** Precio fuera de rango | el precio frente a su referencia MaPreX, los dos llevados a USD con la tasa de cada uno, fuera de −20 % / +30 %; exactamente −20 % o +30 % pasa | ADVERTENCIA por insumo, y **un** INFO que cuenta los insumos sin referencia o sin tasa a su fecha |
| **R12** Precio vencido o sin trazabilidad de tasa | un precio con más de 30 días a la fecha de evaluación (30 pasa), o convertido con una tasa sin fuente | ADVERTENCIA |
| **R12** | un precio convertido con una tasa **sin fecha**: no se puede reproducir | ERROR |

R11 y R12 no son parte de las siete reglas del informe de cada presupuesto (sección 4): se evalúan a una
fecha que usted ve, y volver a evaluar a otra fecha cambia lo que se muestra, nunca lo guardado.

**Reajuste de precios (UC‑18).** Abra el proyecto en la barra y vaya a **Reajuste de precios**:

1. Elija la **versión del contrato**.
2. Declare la **cláusula**: inicio y duración del contrato, desde cuándo corre el primer año,
   periodicidad, mecanismo (escalatoria, comprobación o ambos; con ambos, cuál es el **pagadero** y su
   fuente), estructura (**por partida**: los pesos salen del APU de cada partida; **declarada**: un peso
   por componente, que sumen exactamente 1), el **mes base** de los índices, **R** con su fuente (si el
   contrato no la trae, escriba 0 y dígalo), la fuente de la cláusula y el responsable. En la tabla de
   componentes escriba la serie importada de materiales, equipos y mano de obra.
3. Escriba los **períodos** (desde, hasta, la versión revalorada que sirve de comprobación y, si la hay,
   la excepción declarada) y lo **ejecutado** por período y partida, con su fuente (número y fecha del
   acta o de la valuación).
4. Pulse **Calcular**: ve por período y en total la **escalatoria**, la **comprobación directa**, su
   diferencia y el monto **reconocido**, en la moneda del proyecto y en la otra (con la tasa del cierre
   de cada período; la diferencia se convierte una sola vez). Nada se guarda todavía.
5. Escriba la fuente y el responsable y pulse **Guardar estudio**. Si el último período es un mes que
   aún no cierra, el estudio queda **«parcial al corte»**; al cerrar el mes, calcule otra vez y guárdelo
   eligiendo el parcial que **reemplaza** (una sola vez; el parcial no se borra).
6. **Preparar Excel** y **Descargar Excel**: el libro de la versión del contrato con las hojas
   **Reajuste** y **Ejecutado**.

Lo que el sistema decide solo, y le dice: un período anterior al aniversario de un contrato de más de un
año tiene reajuste 0 con la nota «precios fijos el primer año (art. 134, a cotejar)»; un período que
cruza el aniversario se rechaza (pártalo); si falta el índice de un mes, ese período no se calcula; un
índice provisional se marca; lo ejecutado por encima de lo presupuestado se guarda con aviso y se
reajusta solo hasta lo presupuestado; sin versión revalorada, la comprobación queda «no disponible»; un
proyecto en USD con índices en Bs lleva una ADVERTENCIA; si los reajustes superan el 10 % del monto
original sale una nota marcada INDICIO. Un estudio guardado no cambia aunque después se importe una
revisión de los índices: cita las importaciones que usó.

**Supuestos declarados, todos a cotejar con la Gaceta o con un experto.** El reajuste sigue una
transcripción de la ley, no la Gaceta Oficial; la fórmula `Vo · (Km − 1) · (1 − R)` es un INDICIO. Lo
que el sistema supone, para que usted lo vea y lo pueda discutir:

| # | Supuesto |
|---|---|
| S1‑R1 | La tasa para convertir es la de **venta** del BCV; se puede elegir compra |
| S1‑R2 | Tasa aplicable: la de fecha valor más reciente que no pase de la fecha; con más de 7 días sin tasa no se convierte |
| S1‑R3 | Cambiar la moneda crea una versión nueva convertida; nada se reescribe |
| S1‑R4 | La lista de una empresa no es la vigente de nadie: la usa la versión que la elige |
| S1‑R5 | R11: rango −20 % / +30 % por analogía con la clase 3 de AACE (no es una fuente de rango por insumo) |
| S1‑R6 | R12: un precio vence a los 30 días (supuesto sin fuente) |
| S1‑R7 | R11 y R12 no entran en las siete reglas del informe |
| S1‑R8 | La fórmula escalatoria `Vo · (Km − 1) · (1 − R)` es un INDICIO, a verificar |
| S1‑R9 | Primer año: solo en contratos de más de 12 meses; el período que cruza el aniversario se rechaza; la excepción por equilibrio económico se declara |
| S1‑R10 | El índice de un período es el del mes en que cierra; el mes base se declara |
| S1‑R11 | El reajuste se calcula en la moneda del contrato; USD con índice en Bs da ADVERTENCIA |
| S1‑R12 | Los `.xls` se leen con `xlrd` (extra `bcv`, incluido en la instalación básica) |
| S1‑R13 | Los archivos del BCV de prueba no vienen con el programa: cada empresa descarga los suyos |
| S1‑R14 | R no se aplica a la comprobación directa salvo que la cláusula lo diga |
| S1‑R15 | Las monedas se escriben `Bs` y `USD` |
| S1‑R16 | El desvío de R11 se calcula con una sola división y sin redondear antes de comparar |
| S1‑R17 | Lo ejecutado por encima de lo presupuestado se guarda con aviso y se reajusta hasta lo presupuestado |
| S1‑R18 | Desde la 0.7.0, cada valuación entra entera en el período que contiene su fecha *hasta* |
| S1‑R19 | El porcentaje de erosión es 1 − tasa del precio ÷ tasa de evaluación |
| S1‑R20 | Con «ambos», se reconoce el mecanismo pagadero de la cláusula; sin él, la escalatoria |
| S1‑R21 | El estudio de un mes en curso se guarda «parcial al corte» y se reemplaza una vez al cerrar el mes |

**Recorrido guiado.** En **Inicio**, «Moneda, precios de empresa y reajuste» lo lleva paso a paso por
**Indices del BCV**, **Precios de la empresa**, la **Hoja del proyecto** y **Reajuste de precios**.

### 3.10 Tablero del proyecto

Muestra de un vistazo la versión vigente del proyecto abierto. Las cuatro tarjetas son el total
del contrato, el costo directo, el punto de equilibrio y el resultado de la auditoría. Si el
proyecto tiene línea base y valuaciones, se agregan los anillos de avance físico, SPI y CPI, el
costo final estimado y la curva PV, EV y AC; si no, el tablero dice que falta. Debajo están el
desglose del costo por rubro, las partidas de mayor peso (las primeras que conviene cotizar) y el
comparativo de versiones. Solo lee: para cambiar algo, use la Hoja del proyecto.

### 3.11 APU en tres paneles

En la pestaña APU de la hoja, la columna izquierda lista las partidas valoradas y tiene un
buscador por código o descripción. La del centro muestra el APU de la partida elegida por rubro
(materiales, equipos y mano de obra), cada uno con su subtotal; se editan la cantidad de cada
línea y el rendimiento, y el insumo de una línea se cambia con un selector que busca al escribir.
La de la derecha tiene los factores de la versión (FCAS, bono, administración y utilidad) y el
cierre de la partida, del costo directo al precio unitario. Cada cambio recalcula al momento y la
barra superior indica cuántos cambios faltan por guardar.

## 4. El informe de auditoría

Se genera **siempre** — no existe forma de obtener un presupuesto sin él. Ejecuta las siete
reglas R1–R7 (trazabilidad de cantidades, cierre exacto de la curva, coherencia de unidades,
correspondencia de especificaciones, balance volumétrico, criterio único de depreciación y
conciliación con el plan; detalle en [NORMAS.md §7](../NORMAS.md)). Cada hallazgo trae:

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

**Reglas de precios (R11 y R12, desde la 0.6.0).** No son parte de las siete: se evalúan sobre la lista
de precios a una fecha de evaluación que se declara (en la hoja, hoy) y su impacto es dinero en el total
de la versión. Están en la sección 3.9.

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
| «Escriba un nombre para el proyecto» o «Ya existe un proyecto llamado …» al crear un proyecto | El nombre quedó en blanco o ya lo usa otro proyecto del caso: escribir otro, o abrir el existente con **Abrir** |
| **Guardar version** (o **Guardar primera versión**) de la hoja está deshabilitado | La ayuda del botón dice por qué: el borrador no pertenece a ningún proyecto (elija o cree uno), no hay cambios, falta la fuente o el responsable, o la versión está en solo lectura |
| **Guardar version** o **Exportar Excel** de la barra aparecen deshabilitados con «Todavía no está disponible…» | La hoja del proyecto no está instalada en esta copia: actualizar el repositorio |
| **Importar plano** no aparece en la barra | La copia del programa está incompleta: falta el paquete de importación de planos. Actualice o vuelva a descargar el repositorio. (No depende de los extras `planos` o `civil`: si faltan, la herramienta aparece y el aviso sale al pulsar **Leer plano**) |
| «Falta instalar el componente para leer planos DXF» (o IFC) al pulsar **Leer plano** | Falta el extra `planos` (DXF) o `civil` (IFC): ejecute `uv sync --extra planos` (DXF) o `uv sync --extra civil` (IFC) y vuelva a pulsar **Leer plano** |
| Un archivo subido se guarda con otro nombre (por ejemplo `_CON.csv`) | El nombre original era reservado en Windows (`CON`, `NUL`, `COM1`…) o traía caracteres no permitidos: se limpia para guardarlo, y el contenido no cambia |
| La barra lateral no muestra el caso esperado bajo «Caso abierto» | Abrirlo en **Inicio** (lista de casos y *Abrir este caso*) o arrancar con `SILICE_CASO=<ruta>`: recargar la página (F5) vuelve a la ruta de `SILICE_CASO` o, sin ella, a `data/casos/silice.db` |
| «… con mas de 7 dias naturales sin tasa no se convierte (S1-R2)» al convertir | No hay tasa del BCV importada en los 7 días anteriores: importe el archivo trimestral en **Indices del BCV** y vuelva a convertir |
| «… lleva coma; use punto como separador decimal» al cargar una lista o un CSV | El archivo usa coma decimal: escriba `13288.00`, no `13.288,00` ni `13288,00`. Nada se escribió |
| «… no es una direccion de bcv.org.ve» al leer un archivo del BCV | La dirección declarada no es del BCV: copie la de la página de donde bajó el archivo |
| «Elija la moneda del proyecto (Bs o USD)» al crear un proyecto | La moneda no tiene valor por defecto: elíjala en la barra y vuelva a pulsar **Crear proyecto** |
| «… una version solo se valora con una lista de su moneda (RF-65)» | La lista elegida (o la vigente) está en otra moneda que la versión: cree o elija una lista en la moneda del proyecto, o convierta la versión en **Parámetros** |
| «un parcial se reemplaza una sola vez (S1-R21)» | Ese estudio parcial ya tiene su estudio de cierre: no hace falta otro |
| Un período del reajuste dice «índice faltante: período no calculado» | Falta el índice del mes base o del mes de cierre de alguna serie: impórtelo en **Indices del BCV** y vuelva a calcular |
