# Especificación de Requerimientos de Software (IEEE 830)

**Sistema de generación y auditoría de Análisis de Precios Unitarios multidominio**

> Estado: **completo, pendiente de revisión del tutor (compuerta G0, [docs/metodologia.md §2.2](metodologia.md#22-compuertas))**.
> Redactado en la Sesión 0.1 de [PLAN_DESARROLLO.md](../PLAN_DESARROLLO.md). Criterio de cierre de esa
> sesión: al menos 20 RF numerados, cada uno con prioridad y trazabilidad al caso de uso que lo origina,
> y su matriz de trazabilidad (PLAN_DESARROLLO.md, Sesión 0.1, «Cierre»). Resultado original:
> **31 RF** (sección 3.2) y matriz de la sección 4.
> Este documento no reproduce datos que tienen fuente única: enlaza [CLAUDE.md](../CLAUDE.md),
> [docs/linea_base.md](linea_base.md) y [docs/metodologia.md](metodologia.md) (principio DRY,
> [metodologia.md §5](metodologia.md#5-dry)). Tras cruzar G0 quedan congelados los ocho casos de uso y
> sus requerimientos funcionales numerados.
> **Extensión posterior a G0 (Sesión P0.1, compuerta GP0, [PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)):**
> se agregan UC‑10 y UC‑11 y los RF‑33 a RF‑35, para un total de **34 RF**. El número **UC‑09** y el
> rango que arranca en **RF‑32** quedan vacantes/reservados: los reserva
> [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md) (Sesión A0.1, aún no ejecutada) para el asistente de
> presupuestos con IA; esta sesión continúa la numeración en UC‑10 y RF‑33 para no colisionar con esa
> reserva (enmendado en la Sesión U0.1, ver la nota siguiente).
> **Extensión del sprint de UI (Sesión U0.1, compuerta GU0, [PLAN_UI.md](../PLAN_UI.md)):** se
> agregan UC‑12, los RF‑36 a RF‑43 —para un total de **42 RF**— y el requisito no funcional
> RNF‑10. **La reserva de UC‑09 queda reducida a RF‑32 solamente:** RF‑33 a RF‑35 ya los tomó
> UC‑10/UC‑11, de modo que la reserva de un rango contiguo estaba rota antes de este sprint. Los
> demás requisitos de UC‑09 continuarán, al ejecutarse la Sesión A0.1 de
> [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md), a partir del siguiente al número más alto asignado (hoy
> RF‑44); esta enmienda prevalece sobre la instrucción «numera desde RF‑32» de
> PLAN_ASISTENTE.md:78‑80, que queda desactualizada hasta que A0.1 la corrija.
> **Revisión C4 (2026‑09‑28, fase C4 de [PLAN_CIERRE.md](../PLAN_CIERRE.md)):** sin UC, RF, RNF,
> pantalla ni ruta nuevos. (1) Los criterios de §3.2 quedan sin estado ni nombres de prueba, que
> viven solo en [plan_pruebas.md §8](plan_pruebas.md#8-especificación-de-casos-trazabilidad-rf--prueba);
> RF‑16, RF‑20, RF‑21 y RF‑24 declaran su **alcance vigente**. (2) §3.1 declara la capa que realiza
> cada caso de uso. (3) UC‑01 3a se reordena al comportamiento ratificado en C3‑10. (4) Se agrega el
> flujo UC‑02 4a, que aclara lo ratificado en C3‑8. (5) UC‑04 2b se reformula según C2‑6. Además,
> G1 figura cruzada con salvedad (§2.5, RF‑04, RNF‑09) y RNF‑08 declara la carga de three.js.
> **Revisión C5 (2026‑09‑28, fase C5 de [PLAN_CIERRE.md](../PLAN_CIERRE.md)):** sin UC, RF, RNF,
> pantalla ni ruta nuevos; el código de C5 corrige hallazgos sobre flujos que ya existían.
> (1) UC‑01 6 dice cómo distribuye el proyectista y cuál es el plan por defecto (INV‑087).
> (2) UC‑01 3b declara su alcance vigente: el tipo «medido» no se registra ni se usa, y la
> propuesta sale de todo el histórico, sin atarla a la fecha del presupuesto (INV‑088). (3) RF‑21
> deja de declarar alcance vigente: la prueba de la lista vacía de R2 y R4 y la del presupuesto
> sin hallazgos existen (INV‑092). (4) §3.1 nombra el plan, el 409 del flujo 3b y el aviso del
> flujo 3a de UC‑07 (INV‑094).
> **Revisión C6 (2026‑09‑29, fase C6 de [PLAN_CIERRE.md](../PLAN_CIERRE.md)):** sin UC, RF, RNF
> ni pantalla nuevos; **dos rutas nuevas**, `POST /proyectos` y `POST /presupuestos/importar`, que
> autoriza la enmienda del 2026‑09‑29 ([spec del cierre](superpowers/specs/2026-09-23-plan-cierre-tesis-design.md),
> §2 y §10), con el visto bueno del tutor **pendiente**: si se niega, los commits de C6 se revierten
> (ruling C6‑10). Los demás cambios agregan campos a rutas y pantallas que ya existían.
> (1) UC‑01 1: el proyecto se crea por la API (INV‑086). (2) UC‑02 2a, 2b y 3a: el alta de los
> desconocidos elegidos, los rechazados aparte y las altas que 3a deshace (INV‑090). (3) UC‑05 y
> RF‑24: la importación del archivo de un tercero existe y RF‑24 deja de declarar alcance vigente
> (INV‑076). (4) UC‑06 4a: la justificación se registra ligada al rendimiento (INV‑093). (5) UC‑07 5
> declara su alcance vigente: los atípicos entran al informe de la versión revalorada (INV‑099).
> (6) RF‑02 extiende la recarga a esos atípicos. (7) §3.1 nombra las rutas, los campos y el archivo
> de entrada nuevos.

| Campo | Valor |
|---|---|
| Versión | 1.3 (revisión C6; la 1.2 es la revisión C5, la 1.1 la C4 y la 1.0, del 2026‑08‑29) |
| Fecha | 2026‑09‑29 |
| Autor | [tesista] |
| Revisor | [tutor académico] |

---

## 1. Introducción

### 1.1 Propósito
Definir los requerimientos funcionales y no funcionales del sistema para que el tutor, el jurado y el
equipo de desarrollo compartan una única descripción verificable de lo que se construye.

### 1.2 Alcance
Ver [CLAUDE.md §1](../CLAUDE.md#1-qué-es-este-proyecto). Incluye: derivación trazable de cantidades,
costeo con estructura venezolana, presupuesto y curva, verificación automática, normalización semántica,
detección de anomalías y predicción de precios. Excluye: gemelo digital en sentido estricto,
digitalización automática de planos, evaluación financiera del proyecto de inversión.

### 1.3 Definiciones, acrónimos y abreviaturas

| Término | Definición |
|---|---|
| APU | Análisis de Precios Unitarios: desglose de materiales, equipos y mano de obra por unidad de partida |
| FCAS | Factor de Costos Asociados al Salario (prestaciones); en la línea base, 600 % |
| Bono de alimentación | Cestaticket; monto diario por obrero |
| Rendimiento | Unidades de partida ejecutadas por día |
| BIM‑5D | Modelo paramétrico 3D con cómputo, costo y plan de trabajo asociados |
| IFC | Industry Foundation Classes, formato abierto de intercambio BIM |
| COVENIN 2000 | Codificación venezolana de partidas de construcción |
| ItemComputo | Cantidad de obra trazable (`core.contracts`) |
| Adaptador de dominio | Componente que lee la fuente propia de un dominio y devuelve ItemComputo |
| Línea base | Presupuesto auditado del caso de estudio, [docs/linea_base.md](linea_base.md) |
| LOD | *Level of Development*: grado de definición geométrica y de información de un elemento del modelo BIM (LOD 100 conceptual … LOD 500 verificado en obra). Determina si una cantidad puede extraerse del modelo o debe declararse por regla; es la pregunta que resuelve la compuerta G1 |
| AACE clase 3 | Clase de estimado de la *Association for the Advancement of Cost Engineering* (RP 18R‑97) para un proyecto definido entre el 10 % y el 40 %: exactitud esperada entre −20 % y +30 %. Marco de contraste del indicador 2 |
| MAPE | *Mean Absolute Percentage Error*: media de \|(real − estimado)/real\|, en porcentaje. Métrica principal del módulo predictivo por ser independiente de la escala del precio |
| RMSE | *Root Mean Squared Error*: raíz de la media de los errores al cuadrado, en la unidad monetaria; penaliza los errores grandes |
| R² | Coeficiente de determinación: proporción de la varianza del precio explicada por el modelo (1 = ajuste perfecto, 0 = equivale a predecir la media) |
| CBR | *Case‑Based Reasoning*, razonamiento basado en casos: se estima el precio de una partida nueva por analogía con las más parecidas del histórico, con validación dejando uno fuera. Alternativa prevista cuando hay entre 50 y 200 registros por dominio |
| Isolation Forest | Algoritmo de detección de anomalías no supervisado: aísla observaciones raras con árboles de particiones aleatorias. No requiere datos etiquetados; se usa sobre precios unitarios y rendimientos |
| sentence‑transformers | Biblioteca de modelos que convierten un texto en un vector semántico. Con el modelo multilingüe `paraphrase-multilingual-MiniLM-L12-v2` permite comparar descripciones de partidas por similitud del coseno sin entrenamiento previo |
| Sombra digital | Réplica digital que se alimenta del estado real de la obra pero no actúa sobre ella. El sistema es BIM‑5D y, a lo sumo, sombra digital: **no** es un gemelo digital, que exige realimentación bidireccional en tiempo real ([metodologia.md §9](metodologia.md#9-riesgos-que-gobiernan-las-compuertas)) |

### 1.4 Referencias
IEEE 830‑1998; ISO/IEC 25010; COVENIN 2000; AACE RP 18R‑97; Bases del anteproyecto
(`docs/fuentes/`); [CLAUDE.md](../CLAUDE.md); [docs/metodologia.md](metodologia.md).

### 1.5 Visión general del documento
La sección 2 describe el producto y sus casos de uso; la sección 3 enumera los requerimientos; la
sección 4 los traza a los casos de uso y a las pruebas.

---

## 2. Descripción general

### 2.1 Perspectiva del producto
Sistema de escritorio/servidor local: núcleo Python con base SQLite, interfaz Streamlit y API FastAPI.
Recibe cantidades de obra de adaptadores de dominio (IFC, CSV, tablas) y listas de precios (CSV/Excel);
produce presupuesto, curva de inversión, informe de auditoría y exportación a Excel. Ver
[docs/arquitectura.md](arquitectura.md).

### 2.2 Funciones del producto (casos de uso)

| UC | Nombre | Incremento |
|---|---|---|
| UC‑01 | Elaborar presupuesto nuevo desde una fuente de cantidades | I0.5, I3.1 |
| UC‑02 | Actualizar masivamente los precios de un presupuesto existente | I1 |
| UC‑03 | Reutilizar partidas y desgloses de proyectos anteriores | I2 |
| UC‑04 | Recalcular ante cambio de alcance o dimensiones | I3.2 |
| UC‑05 | Auditar un presupuesto elaborado por un tercero | I4 |
| UC‑06 | Registrar y consultar rendimientos reales de obra ejecutada | I6.2 |
| UC‑07 | Contrastar el precio construido con el precio de mercado | I6.3 |
| UC‑08 | Generar escenarios de sensibilidad | F.1 |
| UC‑10 | Componer una partida | P0.1 (declarado), P1–P2 |
| UC‑11 | Editar una partida compuesta | P0.1 (declarado), P1–P2 |
| UC‑12 | Recorrer la aplicación guiado desde el Inicio | U0.1 (declarado), U1 |

UC‑09 queda vacante en este documento: [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md) (Sesión A0.1, aún no
ejecutada) lo reserva para «Generar presupuesto asistido desde las necesidades del usuario». UC‑10 y
UC‑11 se declararon en la Sesión P0.1 del sprint del prototipo AREN.IA
([PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)); su implementación en `ui/composicion.py` y
`ui/paginas/componer.py` corresponde a las Fases P1 y P2 de ese plan
(`docs/bitacora/2026-09-16-sprint-prototipo.md`); ver RF‑33 a RF‑35 (§3.2). Esta sección no lleva estado: la prueba o el caso manual de cada paso y de cada flujo alternativo de **los once** casos de uso,
y los pasos y flujos que el sistema no realiza, con su registro en el inventario, están en [plan_pruebas.md §8.1](plan_pruebas.md#8-especificación-de-casos-trazabilidad-rf--prueba) (INV‑032, INV‑033).

Los tipos citados en los flujos (`ItemComputo`, `ComposicionAPU`, `ResultadoAPU`, `Presupuesto`,
`Hallazgo`, `Rendimiento`) son los de [CLAUDE.md §5](../CLAUDE.md#5-contratos-de-interfaz-corecontracts),
implementados en `core/contracts/`.

#### UC‑01 — Elaborar presupuesto nuevo desde una fuente de cantidades

- **Actor principal:** proyectista / estimador. **Actor secundario:** administrador del catálogo.
- **Precondiciones:** el catálogo tiene partidas, insumos y una lista de precios vigente; existe una
  fuente de cantidades (IFC, CSV o tabla) de un dominio con adaptador registrado.
- **Flujo principal**
  1. El proyectista crea el proyecto y selecciona la fuente de cantidades y su dominio. El proyecto
     se crea por la API (`POST /proyectos`, desde C6, INV‑086): nombre único y no vacío; descripción
     y dominio opcionales, y el dominio, si se indica, es uno de `Dominio`. Ese dominio es
     informativo: nada lo compara después con el de la fuente. La interfaz no crea proyectos.
  2. El sistema invoca `AdaptadorDominio.extraer(fuente)` y obtiene una lista de `ItemComputo`, cada uno
     con `origen_id` y `origen_tipo`.
  3. El sistema asocia cada ítem a su partida del catálogo y recupera su `ComposicionAPU` y el
     rendimiento vigente.
  4. El motor de costos calcula el `ResultadoAPU` de cada partida con los `ParametrosCosto` del proyecto.
  5. El sistema arma el `Presupuesto`: una `PartidaPresupuestada` por ítem, con su total, y el total general.
  6. El proyectista distribuye las partidas en períodos; el sistema genera la curva de inversión y
     comprueba que el acumulado final iguale el total. Mientras el proyectista no distribuya, el
     sistema usa un plan por defecto de una partida por día; el proyectista lo reparte en la
     pantalla de elaboración o en el campo `plan` de `POST /presupuestos`, y un plan en que alguna
     partida no sume exactamente 1 se rechaza sin elaborar ni guardar (implementado en C5, INV‑087).
  7. El sistema ejecuta la verificación (UC‑05) y emite el informe de auditoría sin que se le solicite.
  8. El proyectista exporta presupuesto y curva a XLSX.
- **Flujos alternativos**
  - *2a. Fuente ilegible o de otro dominio:* el sistema rechaza la carga, no crea el presupuesto e indica
    el archivo y el elemento o fila que falló.
  - *3a. Ítem sin partida en el catálogo:* el sistema elabora el presupuesto sin él: el ítem queda
    pendiente, no suma al total y el informe lo declara. Después propone, para cada pendiente, las
    partidas más similares del catálogo (UC‑03); si el proyectista acepta una, el ítem pasa a esa
    partida y el presupuesto se vuelve a elaborar; si no acepta ninguna, el ítem sigue pendiente.
    (Orden vigente desde C3, dictamen C3‑10: la interfaz elabora primero y propone después.)
  - *3b. Partida sin rendimiento vigente:* el sistema propone el del histórico con su dispersión (UC‑06) y exige declarar
    si es estimado o medido. **Alcance vigente** (C5, INV‑088; dictamen C5‑4, pendiente de ratificación; INV‑100): vigente
    es un rendimiento estimado de fecha no posterior a la del presupuesto, el único que usa la elaboración. Declarado
    **estimado**, el propuesto se registra a la fecha del presupuesto, con su procedencia en las condiciones, y el
    presupuesto se vuelve a elaborar. En la pantalla, declarado **medido** no se registra ni se usa, y el sistema lo
    explica: usarlo tal cual exigiría cambiar la política del catálogo en `core/`, que el cierre no autoriza. La propuesta
    sale de todo el histórico de la partida (RF‑26), sin atarla a la fecha del presupuesto, así que en un presupuesto con
    fecha pasada puede proponer un rendimiento posterior a esa fecha (INV‑100). Si la partida no tiene ningún rendimiento
    que proponer, el sistema remite a «Componer una partida», donde se vuelve a declarar la composición con su rendimiento
    y sus condiciones (UC‑11, sin precarga: la precarga exige un rendimiento vigente). Por la API, `POST /presupuestos`
    responde 409 sin guardar nada, con la propuesta por partida (`null` si no hay ninguna); el tipo se declara registrando
    el rendimiento (UC‑06) y el presupuesto se vuelve a enviar. Un medido registrado así queda en el histórico, pero no
    desbloquea la elaboración. La falta de una lista de precios vigente no es este flujo: se informa como tal.
  - *6a. Sin plan de trabajo:* el presupuesto se emite sin curva y el informe registra que R2 no es aplicable.
  - *7a. Hallazgos de severidad `CRITICO`:* el presupuesto se emite igualmente, con esos hallazgos al frente
    del informe. La verificación audita, no bloquea.
- **Postcondiciones:** presupuesto persistido con referencia a la lista de precios que lo valoró; curva
  cerrada al 100 %; informe de auditoría persistido; toda cantidad conserva su origen.

#### UC‑02 — Actualizar masivamente los precios de un presupuesto existente

- **Actor principal:** administrador del catálogo. **Actor secundario:** proyectista.
- **Precondiciones:** existe un presupuesto valorado con una lista de precios; se dispone del archivo
  CSV/XLSX con la lista nueva.
- **Flujo principal**
  1. El administrador carga el archivo e indica su fecha de vigencia y su moneda.
  2. El sistema valida columnas, tipos y unidades, y convierte todo importe a `Decimal`.
  3. El sistema identifica los insumos cuyo precio difiere del vigente y las partidas donde participan.
  4. El sistema recalcula los APU afectados y produce una versión nueva del presupuesto, sin editar
     ninguna composición. La versión nueva se elabora **sin plan de trabajo**: `actualizar_precios`
     no recibe el plan guardado, ni por la pantalla ni por la API (UC‑01 6a), así que su informe
     declara R2 y R7 no aplicables (INFO). Vale también para un presupuesto importado (UC‑05): la
     versión revalorada no conserva la curva del tercero ni los hallazgos de curva y plan que
     traía su informe (R2 y R7); el informe del archivo importado, que no se modifica, sí los
     conserva (INV‑120).
  5. El sistema persiste un registro de cambio por insumo: precio anterior, precio nuevo, variación e
     incidencia por partida.
  6. El sistema muestra el informe comparativo por partida y total, en valor absoluto y porcentual.
  7. El usuario acepta la versión nueva o la descarta.
- **Flujos alternativos**
  - *2a. Insumos desconocidos en el archivo:* el sistema los lista y ofrece darlos de alta o ignorarlos; los
    ignorados no intervienen en el recálculo. Desde C6 (INV‑090), desconocida es la fila cuyo tipo y
    descripción (normalizada) no están en el catálogo con ninguna unidad. Al subir el archivo, la
    pantalla los lista a la vista, sin escribir nada, y los ofrece en «Dar de alta» sin ninguno
    elegido: el alta es solo por selección explícita, antes de revalorar (ruling C6‑7). Cada
    elegido se crea con un código nuevo de su tipo (`MAT‑NNN`, `EQU‑NNN`, `MO‑NNN`; solo los
    materiales guardan unidad) y su precio entra **solo** en la lista nueva. Un equipo o una mano
    de obra dado de alta con unidad en el archivo (por ejemplo, «dia») no la guarda: en la lista
    siguiente esa misma fila se reporta como rechazada por unidad (2b) y su precio no entra
    (INV‑121). Las filas elegidas del
    mismo insumo dan una sola alta; si sus precios difieren, el sistema lo rechaza sin escribir
    nada. **Límite declarado:** dos filas de material con la misma descripción desconocida y
    unidades distintas se ofrecen las dos, y si se eligen ambas nacen dos homónimos con distinta
    unidad, el caso que 2b evita para los insumos ya catalogados. Por la API no hay vista previa: el
    cliente elige en la misma carga (§3.1).
  - *2b. Unidad no equivalente a la del catálogo* (`unidades_equivalentes`): la fila se rechaza y se
    reporta; las demás se procesan. Desde C6, esa fila no se ofrece para el alta y se reporta
    aparte de los ignorados de 2a.
  - *3a. Ningún precio cambió:* no se crea versión nueva y se informa. En «Actualizar precios», las
    altas elegidas en 2a tampoco se guardan: se deshacen con la transacción y el aviso las nombra.
    Un alta no es un cambio de precio (el insumo nuevo solo tiene precio en la lista nueva), así que
    elegir altas en un archivo sin cambios de precio lleva a este flujo. Por la API, la carga
    (`POST /listas-precios`) ya confirmó la lista y sus altas, y el 409 de la revaloración no las
    deshace.
  - *4a. El presupuesto tiene ítems pendientes (UC‑01, flujo 3a):* la versión nueva los conserva y su
    informe los vuelve a declarar. Siguen pendientes aunque la lista nueva traiga su partida: valorarlos
    es UC‑01, no UC‑02 (aclaración de C4; comportamiento ratificado en el dictamen C3‑8).
  - *7a. El usuario descarta la versión:* se marca como descartada, pero el registro de cambios se conserva
    porque alimenta el histórico del módulo predictivo.
- **Postcondiciones:** versión nueva asociada a su lista de precios; histórico de cambios persistido; el
  presupuesto anterior sigue siendo reconstruible a su fecha.

#### UC‑03 — Reutilizar partidas y desgloses de proyectos anteriores

- **Actor principal:** proyectista. **Actor secundario:** administrador del catálogo.
- **Precondiciones:** el catálogo contiene partidas de proyectos anteriores; el modelo de similitud está
  disponible localmente.
- **Flujo principal**
  1. El proyectista escribe la descripción de la partida en texto libre.
  2. El sistema calcula su vector semántico y devuelve las tres partidas del catálogo con mayor similitud
     del coseno, cada una con su puntaje.
  3. El proyectista selecciona una.
  4. El sistema precarga su `ComposicionAPU` y su rendimiento, conservando la referencia a la partida de
     origen y el puntaje que la propuso.
  5. El proyectista ajusta cantidades o insumos y el sistema recalcula el precio unitario.
- **Flujos alternativos**
  - *2a. Ningún candidato supera el umbral de similitud declarado:* el sistema no propone nada y ofrece
    crear la partida desde cero.
  - *2b. Catálogo vacío (primer proyecto):* la propuesta se omite sin error.
  - *4a. El desglose recuperado usa insumos sin precio en la lista vigente:* se señalan y la partida queda
    incompleta hasta que se coticen.
- **Postcondiciones:** partida creada con trazabilidad a la partida de origen; el puntaje de similitud
  queda registrado como justificación de la reutilización.

#### UC‑04 — Recalcular ante cambio de alcance o dimensiones

- **Actor principal:** proyectista.
- **Precondiciones:** existe un presupuesto cuyas cantidades provienen de reglas paramétricas
  (`origen_tipo = REGLA`) o de un modelo IFC.
- **Flujo principal**
  1. El proyectista modifica un parámetro dimensional (ancho, altura, espesor) o el conteo de elementos.
  2. El sistema vuelve a evaluar las reglas afectadas y produce `ItemComputo` nuevos con la expresión y
     los parámetros que los generaron.
  3. El sistema recalcula las partidas afectadas y el total.
  4. El sistema regenera la curva y vuelve a ejecutar la verificación.
  5. El sistema muestra el diferencial contra la versión anterior: cantidad, precio unitario y total por
     partida.
- **Flujos alternativos**
  - *1a. El parámetro no participa en ninguna regla:* no hay recálculo y se informa.
  - *2a. La fuente es un modelo IFC y no reglas:* el sistema exige reimportar el modelo (UC‑01, paso 2) y
    empareja por `origen_id` (GlobalId) para conservar la correspondencia de las partidas.
  - *2b. Una regla produce una cantidad negativa o nula* (por ejemplo, relleno negativo): se rechaza el
    objeto entero (`origen_id`), no solo esa cantidad, y todos sus ítems conservan su valor anterior,
    para que un objeto nunca mezcle dimensiones viejas y nuevas; el rechazo se informa en el resultado
    del recálculo. La auditoría emite un hallazgo de R5 solo cuando el objeto rechazado es el relleno,
    que conservado deja de cuadrar con su balance; si es otro objeto, el relleno se rebalancea con las
    cantidades conservadas y R5 cuadra (INV‑073; dictamen C2‑6).
- **Postcondiciones:** versión nueva trazable, con la expresión que produjo cada cantidad; el diferencial
  queda registrado.

#### UC‑05 — Auditar un presupuesto elaborado por un tercero

- **Actor principal:** auditor.
- **Precondiciones:** hay un presupuesto propio del sistema, o un archivo tabular de un tercero con
  cantidades, unidades, APU y plan de trabajo. Desde C6 (INV‑076), ese archivo es un libro XLSX con
  las hojas `Datos`, `Presupuesto`, `APU`, `Insumos` y, opcional, `Curva`, cuyo formato fija
  `core/budget/importacion.py` y detalla el [manual técnico](manual_tecnico.md); el proyecto donde
  se guarda ya existe (UC‑01 1).
- **Flujo principal**
  1. El auditor selecciona el presupuesto o importa el archivo del tercero. La importación es por
     la API (`POST /presupuestos/importar`), sin pantalla (ruling C6‑3). Se rechaza **sin escribir
     nada**, nombrando el archivo y, si corresponde, la hoja y la fila, si el archivo está mal
     formado o no es un libro legible, si un código de partida del archivo ya está en el catálogo,
     si el proyecto ya tiene un presupuesto con ese código o si la moneda del archivo no es la de
     la lista vigente a su fecha (comparación exacta).
  2. El sistema construye el `Presupuesto` en memoria conservando las unidades escritas por el autor.
     El presupuesto importado se **valora con el motor** sobre los APU y los parámetros del propio
     archivo: el formato no trae los precios unitarios ni los totales del autor, así que un error
     aritmético en ellos no se audita de forma directa (solo asoma por R2 o R7 frente a su curva).
     El formato tampoco trae `origen_tipo`: un renglón con regla es `REGLA` y uno sin ella,
     `MANUAL` (flujo 2b).
  3. El sistema ejecuta las siete reglas R1–R7
     ([CLAUDE.md §7](../CLAUDE.md#7-siete-reglas-de-verificación-coreverification-sesión-i4)).
  4. Cada regla devuelve `Hallazgo` con severidad, descripción, impacto cuantificado y los `origen_id`
     involucrados.
  5. El sistema ordena los hallazgos por severidad descendente y emite el informe de auditoría.
  6. El auditor exporta el informe.
- **Flujos alternativos**
  - *2a. El archivo no trae plan de trabajo:* R2 y R7 se declaran no aplicables en el informe; las demás
    reglas se ejecutan igual.
  - *2b. Las cantidades no declaran regla ni origen:* R1 emite un hallazgo de trazabilidad ausente en vez
    de comparar contra una expresión inexistente.
  - *3a. Una regla no puede evaluarse por falta de datos:* se registra como hallazgo INFO "regla no
    evaluable" y la ejecución continúa; ninguna regla aborta el informe.
  - *5a. No hay hallazgos:* el informe se emite igualmente, declarando las siete reglas evaluadas y sin
    hallazgos.
- **Postcondiciones:** informe persistido y asociado al presupuesto; el presupuesto auditado no se
  modifica en ningún caso. Si se importó el archivo de un tercero: sus APU quedan en el catálogo con
  las condiciones «importado de <archivo> (presupuesto de un tercero, UC-05)», así que aparecen en
  UC‑03, en el histórico de rendimientos de UC‑06, entre las partidas de «Elaborar un presupuesto»
  y en el recuento por dominio con que la ayuda 4 de «Componer una partida» elige la técnica
  (compuerta G2);
  y la lista «Importada: <archivo>», que copia la vigente a la fecha del presupuesto, pasa a ser la
  **vigente desde esa fecha** para todo el caso (la que muestra el marco de las pantallas, RF‑39, y
  la que valora y referencia lo que se elabore o componga después, y la que copia la próxima lista
  que se cargue). Los importes no cambian, porque la copia es exacta, pero la procedencia de los
  datos propios posteriores apunta al archivo del tercero. **Limitación declarada** (N‑2 y N‑7 de
  la revisión de C6): excluir las listas importadas de la vigencia exige cambiar `core/`, fuera de
  C6. Revalorar el presupuesto importado (UC‑02) elabora la versión nueva sin plan de trabajo, así
  que no conserva la curva del tercero ni los hallazgos R2 y R7 de su informe (UC‑02, paso 4); el
  informe del archivo importado sí los conserva.

#### UC‑06 — Registrar y consultar rendimientos reales de obra ejecutada

- **Actor principal:** residente de obra (registro). **Actor secundario:** proyectista (consulta).
- **Precondiciones:** la partida existe en el catálogo y la ejecución es identificable (obra, tramo, fecha).
- **Flujo principal**
  1. El residente registra el rendimiento observado: partida, valor, condiciones, fecha y referencia a la
     ejecución.
  2. El sistema lo persiste como `TipoRendimiento.MEDIDO`, exigiendo esa referencia.
  3. Al crear o revisar un APU, el sistema propone el rendimiento del histórico de la partida y muestra su
     dispersión: número de observaciones, media, mínimo y máximo.
  4. Si el proyectista introduce un valor que se aparta del comportamiento observado, el sistema lo
     advierte sin impedir el registro.
  5. El sistema nunca mezcla estimados con medidos: cada APU declara de cuál procede su rendimiento.
- **Flujos alternativos**
  - *1a. Falta la referencia a la ejecución:* el registro se rechaza; un rendimiento medido sin ejecución
    no es auditable.
  - *3a. No hay histórico para la partida:* el sistema propone el rendimiento estimado del catálogo y lo
    rotula como tal.
  - *4a. El proyectista acepta la advertencia:* se registra su justificación junto al APU. Desde C6
    (INV‑093), la justificación es opcional y se registra **ligada al rendimiento que registra ese
    guardado**, no a la composición: tabla `justificacion_rendimiento`, con el texto de la
    advertencia aceptada y la fecha, a lo sumo una por rendimiento. En «Componer una partida», el
    campo aparece solo con la advertencia por rango de RF‑27 (el aviso del detector de anomalías no
    lo hace aparecer); sin texto se guarda igual y se informa, porque RF‑27 no impide; si el
    guardado no registra un rendimiento nuevo, la justificación no se registra y se avisa. Por la
    API viaja solo en la misma petición que registra el rendimiento (campo `justificacion` de
    `POST /partidas/{codigo}/rendimientos`) y acompaña a la advertencia de la respuesta (el rango y,
    con el extra `ml`, el veredicto del detector): sin advertencia se ignora y la respuesta la trae
    nula; con advertencia, una justificación en blanco es 422 y no se registra nada. Ninguna ruta
    ni pantalla la lee después: solo la devuelven la respuesta de ese `POST` y el aviso del guardado
    en la pantalla.
- **Postcondiciones:** histórico de rendimientos ampliado; todo APU es trazable al tipo y a la fuente de
  su rendimiento.

#### UC‑07 — Contrastar el precio construido con el precio de mercado

- **Actor principal:** auditor. **Actor secundario:** proyectista.
- **Precondiciones:** hay histórico de precios y de APU acumulado, y el conteo de registros por dominio
  está hecho (compuerta G2, [CLAUDE.md §8.1](../CLAUDE.md#8-compuertas-y-criterios-de-degradación)).
- **Flujo principal**
  1. El usuario selecciona una partida o un presupuesto completo.
  2. El sistema determina la técnica que corresponde al conteo de registros del dominio.
  3. El sistema estima el precio de referencia y reporta MAPE, RMSE y R² de la técnica empleada.
  4. El sistema contrasta el precio construido con el estimado y expresa la desviación en porcentaje.
  5. El sistema marca como atípicos los precios que se apartan del histórico y los incorpora al informe
     de auditoría. **Alcance vigente** (C6, INV‑099; ruling C6‑6): solo en el informe de la versión
     revalorada (UC‑02). «Actualizar precios» y `POST /presupuestos/{codigo}/actualizacion` pasan
     al núcleo el detector de `ml.anomaly`, que evalúa el histórico de variaciones de precio de
     **todos** los insumos (la ayuda 2 de «Componer una partida», en cambio, mira el del insumo).
     Cada cambio de la lista nueva que el detector marca y que usa alguna partida del presupuesto
     entra como hallazgo `ATIPICO` de severidad ADVERTENCIA, que cita los códigos de esas partidas
     (no `origen_id` de ítems de cómputo); queda persistido y se declara otra vez al recargar. El
     informe de un presupuesto elaborado (UC‑01) o importado (UC‑05), y el que muestra «Componer una
     partida», no los traen. Sin el extra `ml` (sin `scikit-learn`) o con menos de 8 variaciones en
     el histórico (`MINIMO_OBSERVACIONES`), no se marca ninguno, y el informe no dice que no se
     evaluaron. `ATIPICO` no es una de las siete reglas: no cuenta en «Reglas evaluadas» y, por su
     severidad, no cambia el veredicto.
- **Flujos alternativos**
  - *2a. Menos de 50 registros:* se emplea el sistema de reglas con análisis de sensibilidad y el
    resultado se rotula como limitación declarada.
  - *3a. Partida nueva sin análogas en el histórico:* no se estima y se informa que el contraste no es posible. **Alcance vigente**
    (C5, INV‑094): el sistema detecta 3a como partida sin PU anterior, porque la estimación por reglas parte de él; no busca análogas.
  - *4a. La desviación excede el rango de la clase 3 de AACE:* se emite un hallazgo de severidad
    ADVERTENCIA.
- **Postcondiciones:** estimación, métricas y desviación quedan registradas junto al presupuesto, con la
  técnica empleada declarada.

#### UC‑08 — Generar escenarios de sensibilidad

- **Actor principal:** proyectista.
- **Precondiciones:** existe un presupuesto base calculado.
- **Flujo principal**
  1. El proyectista define un escenario variando `ParametrosCosto` (FCAS, bono, administración, utilidad)
     o un conjunto de precios de insumos.
  2. El sistema recalcula el presupuesto completo con esos valores, sin alterar el base.
  3. El sistema muestra el total del escenario y su variación respecto del base, por partida y en conjunto.
  4. El proyectista compara varios escenarios en una tabla y la exporta.
- **Flujos alternativos**
  - *1a. Parámetro fuera de rango* (negativo, o depreciación fuera de (0, 1]): se rechaza por las
    invariantes de los contratos y el escenario no se crea.
  - *2a. El escenario altera precios de insumos:* se usa el mecanismo de UC‑02, pero sin persistir la
    lista como vigente.
  - *4a. El proyectista promueve un escenario a presupuesto:* se crea una versión nueva que registra el
    escenario del que proviene.
- **Postcondiciones:** escenarios guardados con sus parámetros; el presupuesto base permanece inalterado.

#### UC‑10 — Componer una partida

- **Actor principal:** proyectista / estimador.
- **Precondiciones:** el catálogo tiene insumos disponibles; hay una referencia de precios de mercado
  cargada (p. ej. MaPreX) para el buscador de apoyo; la partida no tiene composición previa.
- **Flujo principal**
  1. El proyectista declara el código, la descripción y la unidad de la partida.
  2. El proyectista arma la tabla de materiales: insumo, unidad, cantidad de consumo por unidad de
     partida y precio.
  3. El proyectista arma la tabla de equipos: insumo, cantidad, precio y factor de depreciación.
  4. El proyectista arma la tabla de mano de obra: insumo, cantidad, sueldo o precio por unidad
     instalada, y la modalidad de cada línea (jornal o destajo).
  5. El proyectista declara el rendimiento de la partida (unidades de partida por día) junto con sus
     condiciones.
  6. El sistema calcula el `ResultadoAPU` con `calcular_apu` sobre la composición en memoria y muestra
     el desglose y el precio unitario en vivo, sin necesidad de guardar.
  7. El proyectista guarda la composición.
  8. El sistema la persiste asociada a su rendimiento declarado y a sus condiciones.
- **Flujos alternativos**
  - *2a/3a/4a. Fila vacía en alguna tabla:* se descarta sin error.
  - *2b/3b/4b. El proyectista usa el buscador de la referencia de mercado:* el sistema propone
    descripción, unidad, precio y, para equipos, el factor de depreciación; el precio sugerido queda
    editable por quien presupuesta, porque la referencia de mercado no es verdad.
  - *5a. El rendimiento no se declara, o se declara sin sus condiciones:* el sistema no persiste la
    composición; el paso 7 queda bloqueado.
  - *7a. La partida ya existe con composición:* el sistema no crea una segunda composición; ofrece
    editar la existente (UC‑11).
- **Postcondiciones:** la partida queda persistida con su composición, su rendimiento y sus
  condiciones declaradas; el precio unitario es reproducible evaluando `calcular_apu` sobre lo
  guardado.

#### UC‑11 — Editar una partida compuesta

- **Actor principal:** proyectista / estimador.
- **Precondiciones:** la partida existe en el catálogo y tiene una composición y un rendimiento
  vigente.
- **Flujo principal**
  1. El proyectista abre la partida existente; el sistema precarga sus tres tablas de insumos y su
     rendimiento vigente con sus condiciones.
  2. El proyectista modifica insumos, cantidades, precios o la modalidad de alguna línea de mano de
     obra.
  3. El proyectista declara un rendimiento nuevo con sus condiciones.
  4. El sistema recalcula el desglose y el precio unitario en vivo sobre la composición modificada.
  5. El proyectista guarda.
  6. El sistema reemplaza la composición vigente: borra las líneas anteriores, registra el
     rendimiento nuevo y conserva el rendimiento anterior en el histórico de la partida.
- **Flujos alternativos**
  - *3a. El proyectista no declara un rendimiento nuevo con sus condiciones:* el sistema no permite
    guardar (misma regla que UC‑10, paso 5).
  - *6a. La partida no existe en el catálogo:* el sistema rechaza el reemplazo; ese caso es UC‑10, no
    UC‑11.
- **Postcondiciones:** la composición vigente es la nueva; el rendimiento anterior queda en el
  histórico de la partida, distinguible del nuevo; ningún otro presupuesto ya emitido que reutilizó
  esta partida se altera retroactivamente.

#### UC‑12 — Recorrer la aplicación guiado desde el Inicio

- **Actor principal:** usuario nuevo / evaluador. **Actor secundario:** proyectista / estimador.
- **Precondiciones:** la aplicación está instalada y arrancada; el usuario no recibió explicación
  previa del sistema.
- **Flujo principal**
  1. El usuario abre la aplicación; el sistema muestra la pantalla de Inicio (RF‑36).
  2. El sistema muestra en la barra lateral, en solo lectura, el caso abierto y su estado (RF‑39).
  3. El usuario confirma el archivo del caso o abre otro; el sistema lo fija para toda la sesión y
     ninguna otra pantalla vuelve a pedirlo (RF‑38).
  4. El usuario elige uno de los tres recorridos declarados (RF‑37).
  5. En cada pantalla del recorrido, el sistema indica en qué paso está y ofrece el paso siguiente
     (RF‑41); el menú agrupa las pantallas por oficio y en el orden del trabajo (RF‑42).
  6. El usuario completa el último paso y obtiene el resultado del recorrido (por ejemplo, el
     presupuesto en Excel con su hoja de auditoría).
- **Flujos alternativos**
  - *1a. Modo entrega activo:* el menú omite la sección Investigación; ninguna pantalla de Trabajo
    queda inaccesible (RF‑43).
  - *3a. El caso no existe o no tiene partidas:* el sistema lo declara y ofrece cargar el caso de
    demostración; nunca ofrece reiniciar la base (RF‑40).
  - *3b. El archivo no se puede leer como base de datos:* el sistema lo informa con un mensaje, sin
    traza, y el usuario abre otro.
  - *5a. El usuario abre una pantalla que no pertenece al recorrido activo:* el sistema no muestra
    paso siguiente en ella (RF‑41).
- **Postcondiciones:** el usuario llegó al resultado del recorrido; la base solo cambió por las
  acciones que el propio usuario ejecutó (la siembra del paso 3a, guardar, elaborar).

### 2.3 Características de los usuarios

| Actor | Descripción | UC principales |
|---|---|---|
| Proyectista / estimador | elabora y actualiza presupuestos | UC‑01, 02, 03, 04, 08, 10, 11 |
| Auditor | revisa presupuestos de terceros | UC‑05, 07 |
| Residente de obra | registra rendimientos medidos | UC‑06 |
| Administrador del catálogo | mantiene partidas, insumos y listas de precios | UC‑02, 03 |
| Usuario nuevo / evaluador | abre la aplicación por primera vez —tribunal, tutor o presupuestista recién llegado— y necesita orientarse sin formación previa | UC‑12 |

### 2.4 Restricciones
- Todo monto y cantidad en `Decimal` (CLAUDE.md §2).
- El núcleo no depende de ningún dominio; los dominios entran por `AdaptadorDominio` (CLAUDE.md §5).
- Procesamiento sobre IFC 4, no sobre formatos nativos de modelado (independencia tecnológica).
- Codificación de partidas COVENIN 2000; estructura de costos según la Convención Colectiva vigente.
- Ejecución local en Windows/Linux con Python ≥ 3.12.

### 2.5 Suposiciones y dependencias
- Disponibilidad de la línea base auditada (existe) y de un modelo IFC de prueba: existe
  `data/samples/tanquilla.ifc`, generado programáticamente por `scripts/generar_tanquilla_ifc.py`, y
  la compuerta G1 se cruzó **con salvedad**: el adaptador civil IFC reproduce exacto el cálculo manual
  contra ese modelo, no contra un export de un modelador BIM
  ([bitácora de F.1](bitacora/2026-08-31-F1-api-3d.md)); falta la prueba con exports de al menos dos
  modeladores (RNF‑09).
- Volumen de registros históricos suficiente para el módulo predictivo (compuerta G2, CLAUDE.md §8.1).
- Autorización de uso académico de una base de precios de referencia, o catálogo reducido propio.

### 2.6 Requisitos futuros
Sombra digital (avance real de obra vs curva planificada); multimoneda con factor de actualización;
reconocimiento de planos.

---

## 3. Requisitos específicos

### 3.1 Interfaces externas
- **Usuario:** interfaz web local (Streamlit) con una pantalla de Inicio que lleva al usuario por
  recorridos guiados (UC‑12). No todos los casos de uso tienen pantalla: la tabla siguiente declara la
  capa que realiza cada uno (INV‑030). UC‑09 queda vacante (sección 2.2).
- **Software:** API REST (FastAPI) con esquema OpenAPI en `docs/api.json`.

| UC | Interfaz (pantalla del menú) | API REST | Solo biblioteca o script |
|---|---|---|---|
| UC‑01 | «Elaborar un presupuesto» (extrae, elabora con el plan de trabajo del proyectista, audita y descarga el Excel; propone el rendimiento que falta, flujo 3b) y el bloque de cantidades de «Componer una partida»; la interfaz no guarda el presupuesto | `POST /proyectos` (paso 1, desde C6: nombre único y no vacío, `descripcion` y `dominio` opcionales, el dominio uno de `Dominio`; 201, o 422 sin crear nada; la interfaz no crea proyectos), `POST /computos/{dominio}` y `POST /presupuestos` (elabora con el `plan` del proyectista, audita y guarda; sin rendimiento vigente, 409 con la propuesta, flujo 3b); `GET /presupuestos/{codigo}/excel` | — |
| UC‑02 | «Actualizar precios» (al subir el archivo lista los desconocidos y ofrece «Dar de alta», ninguno elegido, flujo 2a; revalora, guarda la versión y ofrece descartarla; avisa aparte de los dados de alta, los ignorados de 2a y los rechazados de 2b) e «Historico de cambios de precio» | `POST /listas-precios` (desde C6, el campo repetible `dar_de_alta` con descripciones del archivo, que eligen por identidad normalizada; la respuesta trae `dados_de_alta`, `ignorados` de 2a, `rechazados` de 2b y `desconocidos`, los dos últimos juntos; un alta de algo que no es desconocido del archivo, o dos filas elegidas del mismo insumo con precios distintos, es 422 sin escribir), `POST /presupuestos/{codigo}/actualizacion`, `GET /cambios-precio`; descartar una versión no tiene ruta. Por la API no hay vista previa del flujo 2a: el cliente elige en la misma carga a partir de su archivo y de `GET /insumos`, porque cargar para ver los desconocidos y volver a cargar deja dos listas. El nombre de la lista debe ser único: `…/actualizacion` la busca por nombre | — |
| UC‑03 | «Partidas similares» (solo lectura); ayuda de similares en «Componer una partida»; propuestas de los pendientes en «Elaborar un presupuesto» | propuestas de los pendientes en la respuesta de `POST /presupuestos` | — |
| UC‑04 | ninguna | ninguna | `adapters/civil/recalculo.py` (`recalcular`, `emparejar`), ejercido solo por las pruebas |
| UC‑05 | el informe se muestra al elaborar, al componer y al revalorar; no hay pantalla de auditoría de un presupuesto ajeno ni de importación (ruling C6‑3) | `POST /presupuestos/importar` (desde C6, RF‑24: multipart con `archivo` XLSX y `proyecto`; 201; 404 si el proyecto no existe; 422 si el archivo no es un libro legible o está mal formado, con archivo, hoja y fila, si un código de partida ya está en el catálogo, si el código de presupuesto se repite en el proyecto o si la moneda no es la de la lista vigente, comparada exacta; si falla, no deja nada escrito), `GET /presupuestos/{codigo}/informe` y la hoja de auditoría de `…/excel` | — |
| UC‑06 | «Componer una partida» propone el rendimiento del histórico, advierte al apartarse y, desde C6, registra la justificación de la advertencia por rango (flujo 4a); «Elaborar un presupuesto» lo propone en el flujo 3b de UC‑01; ninguna de las dos registra medidos | `POST /ejecuciones`, `GET /ejecuciones`, `GET /partidas/{codigo}/rendimientos`, `POST /partidas/{codigo}/rendimientos` (desde C6, el campo `justificacion`, flujo 4a: se registra solo con advertencia, ligada al rendimiento de la misma petición; con advertencia y en blanco, 422 sin registrar nada; la respuesta la devuelve y ninguna ruta la lee después) | — |
| UC‑07 | «Componer una partida» contrasta el precio con la estimación por reglas (clase 3 de AACE); para una partida nueva, avisa que el contraste no es posible (flujo 3a); desde C6, «Actualizar precios» incorpora los precios atípicos de la lista nueva al informe de la versión revalorada (paso 5, con su alcance vigente) | `POST /presupuestos/{codigo}/actualizacion` (desde C6, paso 5: los atípicos de la lista nueva entran como `ATIPICO` ADVERTENCIA al informe de la versión nueva, que sirve `GET /presupuestos/{codigo_nuevo}/informe`; con el extra `ml` y al menos 8 variaciones en el histórico) | `scripts/generar_resultados_ml.py` escribe `docs/resultados_ml.md` |
| UC‑08 | «Escenarios de sensibilidad» | `POST /presupuestos/{codigo}/escenarios` | — |
| UC‑10, UC‑11 | «Componer una partida» | ninguna | — |
| UC‑12 | «Inicio» y el marco común de las pantallas (`ui/app.py`) | ninguna | — |
- **Archivos de entrada:** IFC 4 (dominio civil), CSV de topología (telecom), registro de activos
  (industrial), alcance funcional (sistemas), listas de precios CSV/XLSX y, desde C6, el
  presupuesto de un tercero (UC‑05): un XLSX con las hojas `Datos`, `Presupuesto`, `APU`, `Insumos`
  y `Curva` (opcional), cuyo formato detalla el [manual técnico](manual_tecnico.md); el sistema lo
  valora con su motor sobre los APU del archivo.
- **Archivos de salida:** presupuesto y curva en XLSX, informe de auditoría.

### 3.2 Requisitos funcionales

Cada RF es una afirmación comprobable, con prioridad (Esencial / Deseable / Opcional), el UC que lo
origina, el incremento que lo implementa y un criterio de aceptación.
Numeración: RF‑01 a RF‑03 se conservan como se escribieron en el esqueleto (son los tres requisitos
transversales del núcleo); de RF‑04 en adelante los requisitos van agrupados por caso de uso en orden
ascendente de UC. Los números no se reutilizan: si un RF se retira, su número queda vacante.
**RF‑32 queda vacante**: [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md) (Sesión A0.1, aún no ejecutada)
lo reserva para UC‑09. Los RF de UC‑10 y UC‑11 (Sesión P0.1 de
[PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)) continuaron en RF‑33, y los de UC‑12 (Sesión U0.1 de
[PLAN_UI.md](../PLAN_UI.md)) en RF‑36. La reserva es **de RF‑32 solamente**: los demás requisitos
de UC‑09 tomarán, al ejecutarse A0.1, la numeración a partir del siguiente al número más alto
asignado (hoy RF‑44). Esta enmienda prevalece sobre la instrucción «numera desde RF‑32» de
[PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md):78‑80, que queda desactualizada hasta que la Sesión A0.1
la corrija.

| RF | Enunciado | Prioridad | UC | Incremento | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑01 | El sistema calculará el precio unitario de una partida a partir de su composición y los parámetros de costo según la fórmula de CLAUDE.md §4 | Esencial | UC‑01 | I0.3 | Los cinco precios unitarios de la línea base se reproducen con ± 0,01; los materiales no se dividen entre el rendimiento y la administración y la utilidad se aplican en cascada |
| RF‑02 | El sistema generará siempre el informe de auditoría al producir o cargar un presupuesto | Esencial | UC‑05 | I4 | Todo presupuesto elaborado o recargado trae su informe; sobre el presupuesto de prueba se detectan 7 de 7 inconsistencias, y el informe recargado declara los ítems pendientes del documento emitido y, en una versión revalorada, los precios atípicos que declaró su revaloración (UC‑07 5) |
| RF‑03 | Toda cantidad de obra conservará `origen_id`, `origen_tipo` y, si aplica, la regla que la produjo | Esencial | UC‑01, 04 | I0.1 | Ningún `ItemComputo` sin `origen_id`; un ítem de origen REGLA sin expresión se rechaza; los ítems que derivan de una regla llevan su expresión y sus parámetros, y todo hallazgo de partida referencia un origen trazable |
| RF‑04 | El sistema obtendrá las cantidades de obra invocando `AdaptadorDominio.extraer(fuente)`, sin que el núcleo conozca el dominio ni el formato de la fuente | Esencial | UC‑01 | I0.1, I3.1 | Ningún adaptador importa de `core` fuera de `core.contracts`; todo `ItemComputo` extraído trae `origen_id` y `origen_tipo`; el adaptador IFC usa el GlobalId como `origen_id` y reproduce el cálculo manual de la tanquilla (compuerta G1, cruzada con salvedad: sección 2.5) |
| RF‑05 | El sistema persistirá partidas, insumos, composiciones y rendimientos en SQLite; `scripts/seed.py` cargará la línea base en la base de datos, de modo que el presupuesto se reproduzca completo desde ella | Esencial | UC‑01 | I0.4 | Los cinco APU recuperados de la base dan los mismos precios unitarios que el fixture |
| RF‑06 | El sistema construirá el presupuesto asociando cada `ItemComputo` a su `ComposicionAPU`, calculando su `ResultadoAPU` y emitiendo una `PartidaPresupuestada` por ítem, con total por partida y total general | Esencial | UC‑01 | I0.5 | El presupuesto de la línea base corregida se reproduce partida por partida desde el catálogo persistido |
| RF‑07 | El sistema generará la curva de inversión de modo que su acumulado final sea exactamente igual al total del presupuesto | Esencial | UC‑01 | I0.5 | `total_curva == total` sin tolerancia (la curva del caso didáctico de la línea base, [CLAUDE.md §1](../CLAUDE.md#1-qué-es-este-proyecto), cerraba en 99,30 %) |
| RF‑08 | El sistema exportará presupuesto y curva a XLSX, redondeando a dos decimales solo en la celda presentada y nunca en el cálculo | Deseable | UC‑01 | I0.5 | El libro se escribe completo, con sus cuatro hojas, y sus totales coinciden con los del presupuesto en memoria |
| RF‑09 | El sistema admitirá un dominio nuevo agregando un adaptador bajo `adapters/` que solo importe `core.contracts`, sin modificar `core/` | Esencial | UC‑01 | I5 | `git diff --stat core/` vacío tras I5; ningún adaptador importa de `core` fuera de `core.contracts`, y los adaptadores telecom, industrial y sistemas extraen sus muestras (indicador 4) |
| RF‑10 | El sistema cargará una lista de precios en CSV o XLSX, la validará (columnas, tipos y unidades) e identificará los insumos cuyo precio difiere del vigente y las partidas donde participan | Esencial | UC‑02 | I1 | La lista de prueba identifica exactamente los insumos modificados; los importes se leen como `Decimal` exacto y una fila con unidad no equivalente se rechaza sin detener las demás |
| RF‑11 | El sistema recalculará todos los APU afectados por la lista nueva y producirá una versión nueva del presupuesto sin editar ninguna composición | Esencial | UC‑02 | I1 | Las composiciones quedan idénticas y los precios unitarios cambian solo en las partidas afectadas |
| RF‑12 | El sistema persistirá cada cambio de precio con insumo, precio anterior, precio nuevo, variación porcentual, incidencia por partida y fecha | Esencial | UC‑02 | I1 | Un registro por insumo modificado, con su incidencia por partida, recuperable tras cerrar la sesión |
| RF‑13 | El sistema emitirá un informe comparativo entre la versión anterior y la nueva, por partida y total, en variación absoluta y porcentual | Esencial | UC‑02 | I1 | La suma de las variaciones por partida iguala la variación del total |
| RF‑14 | El sistema reconstruirá cualquier presupuesto con los precios vigentes en la fecha en que fue elaborado | Esencial | UC‑02 | I1 | La reconstrucción a la fecha original es idéntica al presupuesto emitido (RNF‑02) |
| RF‑15 | El sistema devolverá, para una descripción en texto libre, las tres partidas del catálogo más similares con su puntaje de similitud del coseno | Esencial | UC‑03 | I2 | A lo sumo tres propuestas, en orden descendente de puntaje, ninguna bajo `UMBRAL_POR_DEFECTO` |
| RF‑16 | Al aceptar una propuesta, el sistema precargará su composición y su rendimiento, conservando la referencia a la partida de origen y el puntaje que la propuso | Esencial | UC‑03 | I2 | La propuesta aceptada muestra su desglose, su rendimiento, el código de la partida de origen y el puntaje, y la partida nueva se persiste con esa referencia. **Alcance vigente:** la precarga existe; la persistencia de la referencia al origen y al puntaje no existe, y su alcance es la decisión D5 del tutor ([dossier_g0.md](dossier_g0.md#d5-flujo-de-creación-de-partidas-rf16-y-familia)); UC‑10 persiste partidas compuestas, sin esa referencia |
| RF‑17 | El sistema reconocerá al menos el 80 % de las partidas de un presupuesto conocido al normalizar sus descripciones | Esencial | UC‑03 | I2 | ≥ 80 % de la línea base parafraseada reconocida en el primer puesto |
| RF‑18 | El sistema derivará las cantidades del dominio civil de reglas paramétricas declaradas, registrando en cada `ItemComputo` la expresión evaluada y los parámetros usados | Esencial | UC‑04 | I3.2 | Con a = 0,80, h = 0,80, e = 0,10 el concreto da 0,224 m3 y el encofrado 4,48 m2, y ambos ítems traen `regla` y `parametros` |
| RF‑19 | Al modificar un parámetro dimensional o el conteo de elementos, el sistema reevaluará las reglas afectadas y recalculará cantidades, precios y curva sin intervención manual | Esencial | UC‑04 | I3.2 | Cambiar el ancho de la tanquilla altera solo las cantidades que dependen de él, y el recálculo se propaga a precios, curva y auditoría; se cumplen los flujos 1a, 2a y 2b de UC‑04 |
| RF‑20 | El sistema presentará el diferencial entre la versión anterior y la recalculada: cantidad, precio unitario y total por partida | Deseable | UC‑04 | I3.2 | Criterio previsto: la suma de los diferenciales por partida iguala la diferencia de totales. **Alcance vigente: no implementado**, declarado en limitaciones (INV‑011, fase C1 del cierre; decisión del 2026‑09‑23) |
| RF‑21 | El sistema ejecutará las siete reglas R1–R7 sobre cualquier `Presupuesto` y devolverá `Hallazgo` con severidad, descripción, impacto cuantificado y los `origen_id` involucrados | Esencial | UC‑05 | I4 | Cada regla detecta su inconsistencia con hallazgos completos (severidad, descripción, impacto y `origen_id`) y devuelve una lista vacía cuando el presupuesto cumple |
| RF‑22 | El sistema detectará las siete inconsistencias de la línea base sobre el presupuesto de prueba que las reproduce | Esencial | UC‑05 | I4 | 7 de 7 hallazgos sobre el presupuesto de prueba, uno por regla (indicador 1) |
| RF‑23 | El sistema ordenará el informe por severidad descendente y no modificará el presupuesto auditado; una regla que no pueda evaluarse se reportará como hallazgo INFO sin interrumpir a las demás | Esencial | UC‑05 | I4 | El presupuesto auditado es idéntico antes y después, el informe sale ordenado por severidad descendente y una regla sin datos da un hallazgo INFO sin abortar el informe |
| RF‑24 | El sistema importará un presupuesto de un tercero en formato tabular, conservando las unidades originales escritas por su autor, para poder auditarlo | Esencial | UC‑05 | I4 | La unidad escrita por el autor del archivo importado («mts») llega intacta a la regla R3 |
| RF‑25 | El sistema registrará rendimientos medidos con partida, valor, condiciones, fecha y referencia a la ejecución, y rechazará un rendimiento medido sin esa referencia | Esencial | UC‑06 | I6.2 | Un rendimiento medido sin referencia a una `Ejecucion` registrada se rechaza; con ella queda trazado por clave foránea |
| RF‑26 | Al componer un APU, el sistema propondrá el rendimiento del histórico de la partida con su dispersión (número de observaciones, media, mínimo y máximo) | Esencial | UC‑06 | I6.2 | Dispersión con número de observaciones, media, mínimo, máximo y desglose estimado‑medido; la propuesta prefiere el medido más reciente y declara siempre el tipo |
| RF‑27 | El sistema advertirá cuando el rendimiento introducido se aparte del comportamiento observado, sin impedir el registro | Esencial | UC‑06 | I6.1, I6.2 | Desviado → atípico, coherente → no, histórico corto → sin veredicto; un valor fuera del rango observado se registra igual, con la advertencia |
| RF‑28 | El sistema estimará el precio de mercado de una partida con la técnica que corresponda al conteo de registros del dominio y reportará MAPE, RMSE y R² de la técnica empleada | Esencial | UC‑07 | I6.3 | `docs/resultados_ml.md` con MAPE, RMSE, R² y la técnica que dicta el conteo de la compuerta G2 (indicador 5) |
| RF‑29 | El sistema contrastará el precio construido con el estimado, expresará la desviación en porcentaje y marcará como atípicos los precios que se aparten del histórico | Esencial | UC‑07 | I6.1, I6.3 | La desviación se expresa en porcentaje, fuera del rango de la clase 3 de AACE produce un `Hallazgo` ADVERTENCIA, y los precios que se apartan del histórico de variaciones se marcan como atípicos |
| RF‑30 | El sistema generará escenarios variando `ParametrosCosto` o precios de insumos y recalculará el presupuesto completo sin alterar el presupuesto base | Deseable | UC‑08 | F.1 | El presupuesto base y las composiciones quedan intactos, cada partida del escenario coincide con `calcular_apu` (el motor como verdad de terreno), nada se persiste y un parámetro fuera de rango se rechaza (flujo 1a) |
| RF‑31 | El sistema comparará varios escenarios entre sí y con el presupuesto base en una tabla exportable | Opcional | UC‑08 | F.1 | La tabla trae el base y una fila por escenario con total y variación absoluta y porcentual, con detalle por partida, y se exporta; en la interfaz, la página «Escenarios de sensibilidad» |
| RF‑33 | El sistema no persistirá una composición cuyo rendimiento no haya sido declarado explícitamente junto con sus condiciones | Esencial | UC‑10, 11 | P1.2, P2.2 | Sin condiciones del rendimiento, o sin rendimiento, no se persiste nada, ni por los dos caminos del catálogo (cargar y reemplazar) ni desde la pantalla; el botón «Guardar composicion» nace deshabilitado sin condiciones |
| RF‑34 | La modalidad de la mano de obra se declara por línea: jornal o destajo | Esencial | UC‑10, 11 | P1.1, P2.2 | Jornal y destajo conviven en una misma partida, se persisten, se leen y se exportan; una línea sin modalidad es jornal |
| RF‑35 | El precio sugerido desde la referencia de mercado es editable por quien presupuesta | Esencial | UC‑10 | P2.3 | El precio sugerido queda en un campo editable y `core.costing.calcular_apu` refleja el precio editado, no el sugerido |
| RF‑36 | La interfaz abrirá en la pantalla de Inicio, cualquiera que sea el orden del resto del menú | Esencial | UC‑12 | U1 | El Inicio es la página por defecto por identidad, no por posición, y la ruta vacía que Streamlit da a la página por defecto se traduce a `inicio` |
| RF‑37 | Los recorridos guiados se declararán una sola vez, en un módulo sin Streamlit ni base de datos, y el destino de cada paso será la ruta de una página registrada | Esencial | UC‑12 | U1 | Una sola declaración de recorridos, sin Streamlit ni base de datos; todo `paso.pagina` es la ruta de una página visible, con y sin modo entrega |
| RF‑38 | El archivo de la base se fijará una vez por sesión y todas las pantallas operarán sobre ese mismo caso; ninguna pantalla distinta del Inicio pedirá la ruta | Esencial | UC‑12 | U1 | Resolución sesión → entorno → constante, `RUTA_BASE_POR_DEFECTO` definida una sola vez en `ui/`, y ninguna página salvo el Inicio pide la ruta |
| RF‑39 | El sistema mostrará en toda pantalla, en solo lectura, el caso abierto y su estado: existencia del archivo, número de partidas, número de insumos y si hay lista de precios vigente | Esencial | UC‑12 | U1 | El estado es correcto sobre una base inexistente, vacía, sembrada e ilegible, sin traza, y el marco lo pinta en cada una de las diez pantallas |
| RF‑40 | Cuando el caso abierto no exista o no contenga partidas, el Inicio lo declarará y ofrecerá cargar el caso de demostración, sin exponer nunca la opción de reiniciar la base | Esencial | UC‑12 | U1 | Estado vacío, siembra, y ningún botón de sembrar con partidas; el literal del flag de reinicio no aparece en ningún archivo de `ui/` |
| RF‑41 | Cada pantalla del recorrido activo mostrará su paso siguiente y la posición del usuario en el recorrido, tomados de la declaración única de recorridos; una pantalla que no pertenezca a ningún recorrido no mostrará ninguno de los dos | Deseable | UC‑12 | U1 | `paso_siguiente` y la posición del recorrido salen de la declaración única; el botón «Siguiente» lleva a su destino y una pantalla fuera del recorrido no lo muestra |
| RF‑42 | El menú presentará cada pantalla con el nombre de su oficio, agrupada en dos secciones —Trabajo e Investigación— en el orden del trabajo real; el código del caso de uso permanecerá visible como subtítulo | Deseable | UC‑12 | U1 | Secciones y orden sin Streamlit; ningún título lleva código de UC; el subtítulo «Caso de uso …» aparece en las cinco pantallas que tienen uno |
| RF‑43 | Con el modo entrega activo, ninguna pantalla de Trabajo quedará inaccesible | Esencial | UC‑12 | U1 | La sección Trabajo es idéntica con y sin modo entrega, y ningún paso de un recorrido sale de Trabajo |

Los criterios de esta tabla son afirmaciones comprobables y no llevan estado. **La prueba que
demuestra cada criterio y su estado (verde, parcial, sin prueba o no implementado) viven una sola vez,
en [plan_pruebas.md §8](plan_pruebas.md#8-especificación-de-casos-trazabilidad-rf--prueba), y la prueba
o el caso manual de cada paso de cada caso de uso, en su §8.1** (INV‑032; la regla de fuentes únicas
es [metodologia.md §5](metodologia.md#5-dry)). Solo RF‑16 y RF‑20 declaran aquí su
**alcance vigente**, porque su criterio no se cumple entero; en los dos lo fija una decisión
registrada (D5 y la limitación de C1). RF‑21 lo declaró hasta la fase C5, en que la prueba que le
faltaba entró con INV‑092, y RF‑24 hasta la fase C6, en que la importación del archivo de un
tercero entró con INV‑076 (`POST /presupuestos/importar`, UC‑05 1 y 2).

Cobertura por caso de uso (mínimos exigidos por el criterio de cierre entre paréntesis):

| UC | RF | Cantidad |
|---|---|---|
| UC‑01 | RF‑01, RF‑03, RF‑04, RF‑05, RF‑06, RF‑07, RF‑08, RF‑09 | 8 (≥ 4) |
| UC‑02 | RF‑10, RF‑11, RF‑12, RF‑13, RF‑14 | 5 (≥ 4) |
| UC‑03 | RF‑15, RF‑16, RF‑17 | 3 (≥ 2) |
| UC‑04 | RF‑03, RF‑18, RF‑19, RF‑20 | 4 (≥ 3) |
| UC‑05 | RF‑02, RF‑21, RF‑22, RF‑23, RF‑24 | 5 (≥ 3) |
| UC‑06 | RF‑25, RF‑26, RF‑27 | 3 (≥ 3) |
| UC‑07 | RF‑28, RF‑29 | 2 (≥ 2) |
| UC‑08 | RF‑30, RF‑31 | 2 (≥ 2) |
| UC‑10 | RF‑33, RF‑34, RF‑35 | 3 (sin mínimo declarado; UC nuevo, Sesión P0.1) |
| UC‑11 | RF‑33, RF‑34 | 2 (sin mínimo declarado; UC nuevo, Sesión P0.1) |
| UC‑12 | RF‑36, RF‑37, RF‑38, RF‑39, RF‑40, RF‑41, RF‑42, RF‑43 | 8 (sin mínimo declarado; UC nuevo, Sesión U0.1) |
| **Total** | RF‑01 … RF‑31, RF‑33 … RF‑43 (RF‑32 vacante — reservado a UC‑09; RF‑03 traza a dos UC; RF‑33 y RF‑34 trazan a UC‑10 y UC‑11) | **42** |

### 3.3 Requisitos no funcionales (ISO/IEC 25010)

| Característica | RNF | Métrica | Meta |
|---|---|---|---|
| Adecuación funcional | RNF‑01 exactitud del presupuesto frente a la línea base corregida | desviación % | dentro de clase 3 AACE |
| Fiabilidad | RNF‑02 reproducibilidad: el mismo presupuesto se reconstruye a la fecha de su lista de precios | comparación exacta | 100 % |
| Eficiencia de desempeño | RNF‑03 tiempo de recálculo masivo tras cambiar la lista de precios, medido en el equipo de desarrollo con SQLite local y sin exportación | segundos para N partidas | < 5 s con N ≤ 100 partidas |
| Usabilidad | RNF‑04 el informe de auditoría se entiende sin formación previa | juicio de expertos (Likert) | ≥ 4/5 |
| Mantenibilidad | RNF‑05 agregar un dominio no modifica `core/` | `git diff --stat core/`, `test_arquitectura.py` | vacío / verde |
| Mantenibilidad | RNF‑06 cobertura de pruebas del núcleo | pytest‑cov | ≥ 80 % |
| Portabilidad | RNF‑07 instalación con `uv sync` en Windows y Linux | pasos manuales | 0 |
| Seguridad | RNF‑08 ejecución local: el sistema no requiere credenciales, no invoca servicios externos en tiempo de ejecución y los datos residen en un archivo SQLite del equipo del usuario | credenciales versionadas; llamadas de red durante la operación | 0 y 0, con dos excepciones declaradas: la descarga inicial del modelo de `sentence-transformers` (I2), del lado del servidor, que se cachea localmente; y la biblioteca three.js (`r128`), que el navegador descarga de `cdnjs.cloudflare.com` cada vez que se abre el Visor 3D (`URL_THREE_JS` en `ui/paginas/visor.py`), sin caché propia del sistema (INV‑077) |
| Compatibilidad | RNF‑09 entrada IFC 4 de cualquier modelador | archivos de ≥ 2 herramientas (p. ej. Revit y Bonsai) | cantidades extraídas iguales al cálculo manual en ambos; la compuerta G1 (I3.1) se cruzó con salvedad sobre un modelo generado programáticamente (sección 2.5); faltan los exports de dos modeladores, y la alternativa declarada es la entrada tabular |
| Usabilidad | RNF‑10 capacidad de aprendizaje de la interfaz: una persona que nunca vio la aplicación llega sola del Inicio a un presupuesto en Excel con su hoja de auditoría | caso con persona CP‑07 ([guion_prueba_arenia.md](guion_prueba_arenia.md)) y bloque B del anexo A de [dossier_g0.md](dossier_g0.md) | en cada uno de los dos escenarios de CP‑07 (CP‑07 pasa solo si pasan ambos): sin ayuda, ≤ 20 min, bloque B ≥ 4,0 y ningún ítem < 3 |

### 3.4 Reglas de negocio
Fórmula de cálculo: [CLAUDE.md §4](../CLAUDE.md#4-especificación-del-cálculo-y-línea-base).
Reglas de verificación R1–R7: [CLAUDE.md §7](../CLAUDE.md#7-siete-reglas-de-verificación-coreverification-sesión-i4).
Criterios de degradación del módulo predictivo: [CLAUDE.md §8.1](../CLAUDE.md#8-compuertas-y-criterios-de-degradación).

---

## 4. Matriz de trazabilidad

La matriz traza cada caso de uso a sus requisitos, al incremento que los implementó y al indicador de la tesis. **Las pruebas que demuestran cada
RF, con su estado, están solo en [plan_pruebas.md §8](plan_pruebas.md#8-especificación-de-casos-trazabilidad-rf--prueba); la prueba o el caso
manual de cada paso y de cada flujo alternativo de los once casos de uso, en su §8.1** (INV‑032, INV‑033). La columna «Incremento» registra solo
los incrementos del desarrollo, con el mismo criterio que la de §3.2; las fases del cierre (C1 a C5) que corrigieron un caso de uso no se anotan
aquí: cada corrección está en su fila del [inventario del cierre](auditoria/2026-09-inventario.md) y en la fila del paso en plan_pruebas §8.1.

| UC | RF | Incremento | Indicador de la tesis |
|---|---|---|---|
| UC‑01 | RF‑01, RF‑03, RF‑04, RF‑05, RF‑06, RF‑07, RF‑08 | I0.1, I0.3, I0.4, I0.5, I3.1 | 2, 3 |
| UC‑01 (transversal) | RF‑09 | I0.1, I5 | 4 |
| UC‑02 | RF‑10, RF‑11, RF‑12, RF‑13, RF‑14 | I0.4, I1 | 3 |
| UC‑03 | RF‑15, RF‑16, RF‑17 | I2 | 3 |
| UC‑04 | RF‑03, RF‑18, RF‑19, RF‑20 | I0.1, I3.2 | 2 |
| UC‑05 | RF‑02, RF‑21, RF‑22, RF‑23, RF‑24 | I4 | 1 |
| UC‑06 | RF‑25, RF‑26, RF‑27 | I0.1, I6.1, I6.2 | 2 |
| UC‑07 | RF‑28, RF‑29 | I6.1, I6.3 | 5 |
| UC‑08 | RF‑30, RF‑31 | cierre UC‑08 (2026‑08‑31) | 2 (apoyo) |
| UC‑10 | RF‑33, RF‑34, RF‑35 | P0.1 (declarado), P1–P4 ([PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)) | prototipo de entrega AREN.IA, fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis) |
| UC‑11 | RF‑33, RF‑34 | P0.1 (declarado), P1.2, P2.2 | prototipo de entrega AREN.IA, fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis) |
| UC‑12 | RF‑36, RF‑37, RF‑38, RF‑39, RF‑40, RF‑41, RF‑42, RF‑43 | U0.1 (declarado), U1 ([PLAN_UI.md](../PLAN_UI.md)) | fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis); aporta la medición de usabilidad de [calidad_iso25010.md §4](calidad_iso25010.md) |

Correspondencia RNF → verificación: RNF‑01 y RNF‑02 se comprueban en UC‑01 y UC‑02 (RF‑06, RF‑14);
RNF‑03 en UC‑02 (RF‑11), con `scripts/medir_rnf03.py`; RNF‑04 con el juicio de expertos sobre el
informe de UC‑05, en la fase Med de [PLAN_CIERRE.md](../PLAN_CIERRE.md); RNF‑05 con RF‑09; RNF‑06 y
RNF‑07 en la integración continua; RNF‑08 por inspección del repositorio y de las dependencias;
RNF‑09 en la compuerta G1 (RF‑04); RNF‑10 con el caso con persona CP‑07, en la compuerta GU1b
(fase Med) de [PLAN_UI.md](../PLAN_UI.md). RNF‑04 y RNF‑10 son requisitos distintos, con mediciones
distintas. El resultado de cada verificación está en [plan_pruebas.md §9](plan_pruebas.md#9-trazabilidad-rnf--verificación).

La columna "Indicador" enlaza con [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis) y
con la matriz de [docs/tesis/esqueleto_tesis.md](tesis/esqueleto_tesis.md).

---

## Apéndices
- A. Caso de estudio y línea base: [docs/linea_base.md](linea_base.md).
- B. Modelo de datos: [docs/modelo_datos.md](modelo_datos.md).
- C. Arquitectura: [docs/arquitectura.md](arquitectura.md).
