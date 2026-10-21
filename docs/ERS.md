# Especificación de Requerimientos de Software (IEEE 830)

**Sistema de generación y auditoría de Análisis de Precios Unitarios multidominio**

> Estado: **completo, pendiente de revisión del tutor (compuerta G0, [docs/metodologia.md §2.2](metodologia.md#22-compuertas))**.
> Redactado en la Sesión 0.1 de [PLAN_DESARROLLO.md](../PLAN_DESARROLLO.md). Criterio de cierre de esa
> sesión: al menos 20 RF numerados, cada uno con prioridad y trazabilidad al caso de uso que lo origina,
> y su matriz de trazabilidad (PLAN_DESARROLLO.md, Sesión 0.1, «Cierre»). Resultado original:
> **31 RF** (sección 3.2) y matriz de la sección 4.
> Este documento no reproduce datos que tienen fuente única: enlaza [NORMAS.md](../NORMAS.md),
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
> RF‑64 (el siguiente número libre tras RF‑63; la reserva de UC‑09 sigue siendo RF‑32 vacante)); esta enmienda prevalece sobre la instrucción «numera desde RF‑32» de
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
> autoriza la enmienda del 2026‑09‑29 (spec del cierre,
> §2 y §10), con el visto bueno del tutor **pendiente**: si se niega, los commits de C6 se revierten
> (ruling C6‑10). Los demás cambios agregan campos a rutas y pantallas que ya existían.
> (1) UC‑01 1: el proyecto se crea por la API (INV‑086). (2) UC‑02 2a, 2b y 3a: el alta de los
> desconocidos elegidos, los rechazados aparte y las altas que 3a deshace (INV‑090). (3) UC‑05 y
> RF‑24: la importación del archivo de un tercero existe y RF‑24 deja de declarar alcance vigente
> (INV‑076). (4) UC‑06 4a: la justificación se registra ligada al rendimiento (INV‑093). (5) UC‑07 5
> declara su alcance vigente: los atípicos entran al informe de la versión revalorada (INV‑099).
> (6) RF‑02 extiende la recarga a esos atípicos. (7) §3.1 nombra las rutas, los campos y el archivo
> de entrada nuevos.

> **Enmienda del sprint final (Sesión SF0, compuerta GSF0, [PLAN_SF.md](../PLAN_SF.md); spec
> [2026-10-04-sprint-final-prototipo-design.md](especificaciones/2026-10-04-sprint-final-prototipo-design.md) §4):**
> se agregan UC‑13 a UC‑16, los RF‑44 a RF‑63 —para un total de **62 RF** y **quince UC**— y los
> requisitos no funcionales RNF‑11 a RNF‑13; se agrega el actor **gerente** (§2.3). Se enmiendan:
> UC‑01 1 (la interfaz crea proyectos, RF‑63; hasta C6 solo los creaba la API, INV‑086) y su fuente
> de cantidades nueva; UC‑02, UC‑04, UC‑11 y UC‑12 (§2.2); §2.4 y §2.6 (DXF e IFC2x3 e IFC 4 como
> entradas de planos); RF‑37, RF‑39 y RF‑42 (once pantallas); y la reserva de UC‑09: sus requisitos nuevos empezarán en RF‑64 (el siguiente número libre tras RF‑63; la reserva de UC‑09 sigue siendo RF‑32 vacante).
> Los RF nuevos quedan **sin implementar** hasta su fase (columna «Incremento»); el estado de cada uno
> vive solo en [plan_pruebas.md §8](plan_pruebas.md#8-especificación-de-casos-trazabilidad-rf--prueba).

> **Enmienda S4.0 (2026‑10‑11):** la reserva de UC‑09 queda resuelta con RF‑32 y RF‑90 a RF‑95 (maestro §9); RF‑64 pertenece a S1. Se agregan además UC‑09 y RNF‑18; se enmienda RNF‑08 (§3.3). Los conteos los calcula la meta (`scripts/meta_silice.py`), que comprueba la **presencia** de cada número.

> **Enmienda de Sílice 0.6.0 (S1; spec [S1](especificaciones/2026-10-11-silice-s1-moneda-reajuste-design.md) §3):** se agregan **UC‑17** (base de precios de la empresa e índices del BCV) y **UC‑18** (reajuste de la obra ejecutada), **RF‑64 a RF‑71** y **RNF‑14**; se enmiendan UC‑01 (moneda al crear), UC‑02 y UC‑15 (§2.2). Las referencias «§» de esos casos de uso y requisitos son al spec S1. Los conteos los calcula la meta (`scripts/meta_silice.py`), que comprueba la **presencia** de cada número.

> **Enmienda de Sílice 0.6.0 (S5‑1 adelantado; spec
> [S5](especificaciones/2026-10-11-silice-s5-producto-instalador-design.md) §4; maestro RV‑3, RV‑4, RV‑5):** se
> agregan **RF‑96** (migraciones con respaldo y vuelta atrás, en dos bases; abrir un caso solo con `preparar_base`
> y desde la carpeta de casos) y **RNF‑20** (cero deriva de esquema en cada destino). UC‑24, RF‑97 a RF‑99 y RNF‑19
> los agrega S5‑0 en la 1.0.0; hasta entonces RF‑96 cita UC‑24 por adelantado. En la 0.6.0 se cumplen de RF‑96 los
> criterios (a) para la base del caso, (b), (c), (d) y (e), y (f) con la base de la instalación sin tablas; el resto
> llega con S3 (`instalacion.db` con tablas) y S5‑2. Los conteos los calcula la meta (maestro §6.1).

> **Enmienda de Sílice 0.7.0 (S2; spec [S2](especificaciones/2026-10-11-silice-s2-presupuesto-vivo-design.md) §3):** se agregan **UC‑19** (registrar una valuación de obra) y **UC‑20** (controlar el avance y recuperar un retraso), **RF‑72 a RF‑79**, **RNF‑15** y las reglas externas **R13** y **R14** (§3.4); se enmiendan UC‑15, UC‑16 y UC‑18 (§2.2). Las referencias «§» de esos casos de uso y requisitos son al spec S2. Los conteos los calcula la meta (`scripts/meta_silice.py`, `scripts/meta_silice_s2.py`), que comprueba la **presencia** de cada número.

> **Enmienda de Sílice 0.8.0 (S3‑0; spec
> [S3](especificaciones/2026-10-11-silice-s3-auditor-paquete-design.md) §3; maestro RV‑7 a RV‑16, RV‑20,
> RV‑23):** se agregan **UC‑21 a UC‑23** (cuentas y sesión, entregar el paquete auditado, revisar un
> paquete o un presupuesto externo), **RF‑80 a RF‑89** y **RF‑100** (deseable: anomalías en las
> variaciones de precio, fase opcional S3‑6) y los requisitos no funcionales **RNF‑16** (seguridad) y
> **RNF‑17** (usabilidad de quien revisa y de quien administra); los actores *administrador de la
> instalación* y *herramienta externa* y los tres roles *arma*, *revisa* y *administrador* (§2.3).
> Se enmiendan UC‑05, UC‑12, UC‑14 y UC‑15 (§2.2), RF‑37, RF‑42 y RF‑43 (cuatro secciones del menú,
> visibles según el rol) y, **una sola vez**, RNF‑08 (las únicas credenciales son las cuentas locales;
> la redacción final con todas sus excepciones se consolida en S5‑0). Los RF y RNF nuevos quedan
> **sin implementar** hasta su fase (columna «Incremento»).

| Campo | Valor |
|---|---|
| Versión | 1.4 (enmienda del sprint final SF0; la 1.3 es la revisión C6, la 1.2 la C5, la 1.1 la C4 y la 1.0, del 2026‑08‑29) |
| Fecha | 2026‑10‑04 |
| Autor | [tesista] |
| Revisor | [tutor académico] |

---

> **Enmienda de Sílice 1.0.0 (S5‑0; spec S5 §4 y §10.3):** se agregan UC‑24, RF‑97 a RF‑99 y RNF‑19; RNF‑07 aclara que el instalador de Windows es el camino de usuario; RNF‑08 queda con su redacción final (dos excepciones declaradas y three.js incrustado). RF‑96 y RNF‑20 llegaron con la 0.6.0. Los conteos los calcula la meta (maestro §6.1).

**Enmienda de la ruta, sesión 4 (arenera; plan [PLAN_SESION_4_ARENERA.md](planes/PLAN_SESION_4_ARENERA.md)):** se agregan UC‑28 y UC‑29, RF‑127 a RF‑136 y RNF‑25. La arenera empieza por el inventario («cuánto hay y cuánto queda» de cada material) y por el reporte de la báscula; el costo horario de maquinaria espera a tener fuente verificada.

**Enmienda de la ruta, sesión 4 (historial de auditorías; plan [PLAN_SESION_4_HISTORIAL.md](planes/PLAN_SESION_4_HISTORIAL.md)):** se agregan UC‑30, RF‑142 a RF‑146 y RNF‑28. Eugenio decide que cada auditoría de «Libro de la empresa» se guarda (resumen y hallazgos, nunca el libro ni el PDF); UC‑25 deja de decir «nada se guarda» y lo dice solo del archivo.

## 1. Introducción

### 1.1 Propósito
Definir los requerimientos funcionales y no funcionales del sistema para que el tutor, el jurado y el
equipo de desarrollo compartan una única descripción verificable de lo que se construye.

### 1.2 Alcance
Ver [NORMAS.md §1](../NORMAS.md#1-qué-es-este-proyecto). Incluye: derivación trazable de cantidades,
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
(`docs/fuentes/`); [NORMAS.md](../NORMAS.md); [docs/metodologia.md](metodologia.md).

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
| UC‑13 | Levantar el espacio y los metrajes | SF0 (declarado), SF1–SF2 |
| UC‑14 | Importar un plano a la hoja | SF0 (declarado), SF5 |
| UC‑15 | Editar la hoja del proyecto | SF0 (declarado), SF3 |
| UC‑16 | Analizar el punto de equilibrio | SF0 (declarado), SF3 |
| UC‑17 | Mantener la base de precios de la empresa y los índices del BCV | S1‑2, S1‑3 (Sílice 0.6.0) |
| UC‑18 | Reajustar los precios de la obra ejecutada | S1‑4 (Sílice 0.6.0) |
| UC‑19 | Registrar una valuación de obra | S2‑1 (Sílice 0.7.0) |
| UC‑20 | Controlar el avance y recuperar un retraso | S2‑2, S2‑3 (Sílice 0.7.0) |
| UC‑09 | Armar el presupuesto con el asistente de IA | S4.2 a S4.3 (Sílice 0.9.0) |

**Enmienda S4.0 (2026‑10‑11):** UC‑09 queda definido en §2.2 y sus requisitos son RF‑32 y RF‑90 a RF‑95 (RF‑64 pertenece a S1). Lo que sigue es la historia de la reserva. UC‑09 queda vacante en este documento: [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md) (Sesión A0.1, aún no
ejecutada) lo reserva para «Generar presupuesto asistido desde las necesidades del usuario». UC‑10 y
UC‑11 se declararon en la Sesión P0.1 del sprint del prototipo AREN.IA (hoy Sílice)
([PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)); su implementación en `ui/composicion.py` y
`ui/paginas/componer.py` corresponde a las Fases P1 y P2 de ese plan
(`docs/bitacora/2026-09-16-sprint-prototipo.md`); ver RF‑33 a RF‑35 (§3.2). Esta sección no lleva estado: la prueba o el caso manual de cada paso y de cada flujo alternativo de **los quince** casos de uso,
y los pasos y flujos que el sistema no realiza, con su registro en el inventario, están en [plan_pruebas.md §8.1](plan_pruebas.md#8-especificación-de-casos-trazabilidad-rf--prueba) (INV‑032, INV‑033).

Los tipos citados en los flujos (`ItemComputo`, `ComposicionAPU`, `ResultadoAPU`, `Presupuesto`,
`Hallazgo`, `Rendimiento`) son los de [NORMAS.md §5](../NORMAS.md#5-contratos-de-interfaz-corecontracts),
implementados en `core/contracts/`.

#### UC‑01 — Elaborar presupuesto nuevo desde una fuente de cantidades

- **Actor principal:** proyectista / estimador. **Actor secundario:** administrador del catálogo.
- **Precondiciones:** el catálogo tiene partidas, insumos y una lista de precios vigente; existe una
  fuente de cantidades (IFC, CSV o tabla) de un dominio con adaptador registrado.
- **Flujo principal**
  1. El proyectista crea el proyecto y selecciona la fuente de cantidades y su dominio. El proyecto
     se crea por la API (`POST /proyectos`, desde C6, INV‑086): nombre único y no vacío; descripción
     y dominio opcionales, y el dominio, si se indica, es uno de `Dominio`. Ese dominio es
     informativo: nada lo compara después con el de la fuente. Desde el sprint final la interfaz
     también crea proyectos, con la misma regla de nombre (RF‑63, herramienta Proyecto); hasta
     entonces solo los creaba la API.
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
  - *2b. La fuente de cantidades es la hoja de metrajes (UC‑13):* el sistema toma las cantidades
    derivadas del espacio del proyecto como `ItemComputo` de origen REGLA y sigue en el paso 3; la
    hoja es una fuente de cantidades más y el flujo no cambia.
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
  - *Enmienda SF (spec §4.1):* sin cambios en su pantalla. La cotización de la hoja del proyecto
    (RF‑56, UC‑15) es un camino propio que conserva el plan y la curva; una lista global nueva
    cargada por este caso no pisa una cotización vigente del proyecto, que se aplica sobre ella.
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
  - *Enmienda SF (spec §4.1):* para los proyectos con espacio, el recálculo ante un cambio de
    dimensiones lo realiza la hoja del proyecto (UC‑15, RF‑52); RF‑20 (el diferencial) sigue sin
    implementarse y la hoja recalcula completo.
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
     ([NORMAS.md §7](../NORMAS.md#7-siete-reglas-de-verificación-coreverification-sesión-i4)).
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
  está hecho (compuerta G2, [NORMAS.md §8.1](../NORMAS.md#8-compuertas-y-criterios-de-degradación)).
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
  - *Enmienda SF (spec §4.1):* este caso sigue siendo el único camino para cambiar una composición
    **del catálogo**. La hoja del proyecto (UC‑15) edita una copia de la composición en la versión
    (DA‑SF‑7) y ofrece «promover al catálogo» por este caso.
- **Postcondiciones:** la composición vigente es la nueva; el rendimiento anterior queda en el
  histórico de la partida, distinguible del nuevo; ningún otro presupuesto ya emitido que reutilizó
  esta partida se altera retroactivamente.

#### UC‑12 — Recorrer la aplicación guiado desde el Inicio

- **Actor principal:** usuario nuevo / evaluador. **Actor secundario:** proyectista / estimador.
- **Precondiciones:** la aplicación está instalada y arrancada; el usuario no recibió explicación
  previa del sistema.
- **Flujo principal**
  1. El usuario abre la aplicación; el sistema muestra la pantalla de Inicio (RF‑36).
  2. El sistema muestra en la barra lateral, en solo lectura, el caso abierto y su estado (RF‑39) (barra superior desde SF4, RF‑60).
  3. El usuario confirma el archivo del caso o abre otro; el sistema lo fija para toda la sesión y
     ninguna otra pantalla vuelve a pedirlo (RF‑38).
  4. El usuario elige uno de los tres recorridos declarados (RF‑37).
  5. En cada pantalla del recorrido, el sistema indica en qué paso está y ofrece el paso siguiente
     (RF‑41) (barra superior desde SF4, RF‑60); el menú agrupa las pantallas por oficio y en el orden del trabajo (RF‑42).
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
  - *5b. El recorrido llega a la hoja del proyecto:* desde el sprint final los recorridos guiados
    incluyen la pantalla «Hoja del proyecto» (UC‑15), que forma parte de la sección Trabajo
    (RF‑37, RF‑42 y RF‑43).
- **Postcondiciones:** el usuario llegó al resultado del recorrido; la base solo cambió por las
  acciones que el propio usuario ejecutó (la siembra del paso 3a, guardar, elaborar).

#### UC‑13 — Levantar el espacio y los metrajes

- **Actor principal:** proyectista / estimador.
- **Precondiciones:** hay un proyecto abierto (UC‑01 1, RF‑63); el catálogo tiene las partidas de las
  especialidades cuyas cantidades se van a derivar; hay una lista de precios vigente.
- **Flujo principal**
  1. El proyectista declara en la hoja los ambientes del proyecto, con sus dimensiones.
  2. Declara las fuentes (por ejemplo, la acometida de agua, el tablero eléctrico o el rack) y los
     circuitos, y coloca los puntos de cada especialidad (puntos de agua, de datos, tomacorrientes,
     luminarias) dentro de su ambiente (RF‑44).
  3. Para cada punto declara su origen de medida —por ejemplo, plano acotado, medido en sitio o
     supuesto declarado— con la referencia que ese tipo exige (RF‑44).
  4. El sistema propone un recorrido para cada punto; el proyectista lo acepta o lo reemplaza declarando
     sus vértices (RF‑45).
  5. El sistema une los segmentos coincidentes, parte los solapes colineales y guarda los segmentos
     derivados, con sobrescritura opcional de diámetro y de empotrado (RF‑46).
  6. El sistema aplica las reglas de cantidades de la especialidad —agua (RF‑47), datos (RF‑48) o
     electricidad (RF‑49)— y produce los `ItemComputo` derivados, con la regla y los parámetros que los
     produjeron (RF‑03).
  7. El sistema audita el espacio con R8, R9 y R10 (RF‑61) y muestra los hallazgos junto a la fila que
     tocan.
  8. El proyectista guarda el levantamiento como parte de una versión del presupuesto (UC‑15, RF‑53).
- **Flujos alternativos**
  - *13a. Fila sin origen de medida:* se acepta en la versión; R8 la marca ERROR (RF‑44, RF‑61).
  - *13b. Punto fuera de su ambiente:* se acepta en la versión; R9 lo marca (RF‑61).
  - *4a. El usuario no declara vértices:* rige el recorrido propuesto y así se registra.
  - *6a. Regla sin fuente normativa verificada:* la cantidad se produce con el supuesto declarado y el
    informe lo registra.
- **Postcondiciones:** el espacio, sus orígenes de medida y las cantidades derivadas quedan en la hoja
  del borrador; toda cantidad derivada conserva `origen_id`, `origen_tipo` y su regla; nada se persiste
  hasta que el proyectista guarda (UC‑15).

#### UC‑14 — Importar un plano a la hoja

- **Actor principal:** proyectista / estimador.
- **Precondiciones:** hay un proyecto abierto; se dispone de un plano en DXF que sigue la convención de
  capas del sistema, o de un modelo IFC (IFC2x3 o IFC 4) con espacios, terminales y tableros.
- **Flujo principal**
  1. El proyectista elige el archivo (herramienta «Importar plano»).
  2. El sistema valida el archivo: tamaño, formato y, en el DXF, la unidad de dibujo (`$INSUNITS`).
  3. El sistema lee las entidades de la convención —en el DXF, por capa; en el IFC, `IfcSpace`,
     terminales y tableros— y las convierte en ambientes, fuentes y puntos de la hoja, cada una con su
     identificador de origen (el *handle* del DXF o el `GlobalId` del IFC) (RF‑50, RF‑51).
  4. El sistema produce el informe de importación (qué se importó, qué se omitió y por qué).
  5. El proyectista revisa el resultado en la hoja y completa lo que el plano no trae (por ejemplo,
     las alturas) como en UC‑13.
- **Flujos alternativos**
  - *14a. DXF sin `$INSUNITS`:* el sistema se detiene y pide la unidad; no importa nada mientras no se
    declare.
  - *14b. Entidades fuera de la convención:* van al informe de importación, no a la hoja.
  - *14c. Reimportar el mismo plano:* el sistema empareja por *handle* o `GlobalId` (como UC‑04 2a),
    actualiza las filas que cambiaron, agrega las nuevas y marca las filas que desaparecieron.
  - *14d. Archivo malformado o mayor de 20 MB:* se rechaza con un mensaje, sin *traceback* y sin
    escribir nada (RNF‑12).
  - *3a. IFC generado programáticamente:* el resultado hereda la salvedad de RNF‑09 y el informe la
    declara.
- **Postcondiciones:** las filas importadas están en la hoja del borrador con su identificador de
  origen y el informe de importación está disponible; ningún archivo subido sale de su carpeta
  (RNF‑12); el proyecto no cambia en la base hasta que se guarda una versión (UC‑15).

#### UC‑15 — Editar la hoja del proyecto

- **Actor principal:** proyectista / estimador.
- **Precondiciones:** existe **cualquier** presupuesto guardado del proyecto, con o sin espacio (el
  de la clínica, TI‑001 o uno importado por UC‑05).
- **Flujo principal**
  1. El proyectista abre el presupuesto en la pantalla «Hoja del proyecto».
  2. Edita las celdas de entrada de la pestaña que corresponda (metrajes, APU, cantidades, plan,
     precios, parámetros; spec §9.2). Las celdas calculadas están bloqueadas.
  3. El sistema recalcula y audita en el borrador, sin persistir: totales, curva, punto de equilibrio y
     columna Estado (RF‑52, RF‑55).
  4. El proyectista declara la fuente del cambio y su nombre como responsable, y guarda.
  5. El sistema crea una versión nueva con su informe, la instantánea de sus composiciones y de su
     espacio, y un `RegistroCambio` por cada celda cambiada (RF‑53).
- **Flujos alternativos**
  - *15a. Guardar sin fuente o sin responsable:* se rechaza y no se crea la versión (RF‑53).
  - *15b. Plan con una partida que no suma 1:* se rechaza (como UC‑01 6).
  - *15c. Salir con ediciones sin guardar:* el sistema avisa.
  - *15d. Restaurar una versión anterior N:* el sistema crea una versión nueva copia de N, con su
    `RegistroCambio`; N sigue existiendo (RF‑54).
  - *15e. Versión sin instantánea de composiciones (anterior a SF‑E6, o importada de UC‑05):* al
    abrirla, la hoja crea la instantánea desde el catálogo vigente y lo registra; si una partida no
    tiene composición en el catálogo, su APU queda en solo lectura.
  - *2a. El proyectista registra una cotización:* la cotización lleva su fuente, tiene alcance del
    proyecto y prevalece sobre la lista global para ese insumo hasta que se retire (RF‑56).
  - *2b. El proyectista cambia un parámetro del proyecto (por ejemplo, el FCAS):* se recalculan todos
    los APU de la versión y el cambio queda en el registro (RF‑57).
  - *5a. Exportar:* el proyectista exporta la hoja a Excel con fórmulas vivas, trazabilidad y auditoría
    (RF‑59).
- **Postcondiciones:** la versión anterior sigue cargando idéntica; la versión nueva conserva el plan y
  la curva salvo que el usuario los editara; cada cambio guardado tiene fuente, responsable y fecha;
  el historial solo crece.

#### UC‑16 — Analizar el punto de equilibrio

- **Actor principal:** proyectista / estimador, gerente.
- **Precondiciones:** existe un presupuesto guardado.
- **Flujo principal**
  1. El actor abre la pestaña «Punto de equilibrio» de la hoja del proyecto.
  2. El sistema calcula el punto de equilibrio con la definición del caso TI‑001: costos variables
     (CV) como la suma de cantidad por costo directo de cada partida, costos fijos (CF) como CV por
     la administración de los parámetros de la versión, margen m = (V − CV) / V con V el total del
     contrato, y PE = CF / m (RF‑58).
  3. El sistema ubica el PE en la curva: el primer período cuyo acumulado lo alcanza y la fracción
     de ese período.
  4. El actor cambia cualquier entrada de la hoja (UC‑15) y el punto de equilibrio se recalcula en el
     borrador.
- **Flujos alternativos**
  - *16a. Sin plan de trabajo:* se informa el PE sin ubicación en la curva.
  - *16b. Margen ≤ 0:* no existe punto de equilibrio y el sistema lo declara.
  - *16c. PE > V:* el sistema declara que no se alcanza dentro del contrato.
  - *2a. V = 0:* el análisis no es aplicable.
- **Postcondiciones:** el actor conoce el PE, su ubicación o la razón por la que no existe; el análisis
  no modifica el presupuesto.

#### UC‑17 — Mantener la base de precios de la empresa y los índices del BCV

- **Actor principal:** administrador del catálogo. **Secundario:** proyectista. Desde S3, rol
  *administrador* (valor por defecto de la pregunta P2 del spec maestro §10.3).
- **Precondiciones:** catálogo con insumos; archivos del BCV ya descargados en el equipo; lista de referencia
  MaPreX cargada (S1‑0, tarea 0.4).
- **Flujo principal**
  1. El administrador elige uno o varios archivos del BCV y declara la **fuente** (dirección de la página del
     BCV de donde los bajó) y la **fecha de descarga**.
  2. El sistema lee cada archivo **sin conexión**, valida formato, fuente y fechas (§7.2) y muestra el
     informe de importación sin escribir nada: series, fechas, filas leídas, rechazadas y provisionales.
  3. El administrador confirma; el sistema guarda los valores con la huella SHA‑256 del archivo.
  4. El administrador carga la lista de su empresa (CSV o XLSX: las cuatro columnas de UC‑02 y, opcionales,
     `fecha`, `fuente` y `referencia` por fila), declara la empresa (nombre y RIF, como texto hasta S3; RV‑6),
     moneda, fecha y fuente de la lista y la **lista base** que completa los insumos que la empresa no cotiza.
  5. El sistema crea la lista de empresa (§6.2) y audita sus precios con R11 y R12 a la fecha de evaluación
     declarada; muestra cada hallazgo con el dinero que representa.
- **Flujos alternativos**
  - *2a. Formato no reconocido:* se rechaza el archivo con un mensaje que nombra la etiqueta o la hoja que
    faltó, sin *traceback* y sin escribir nada.
  - *2b. Fecha fuera del período del archivo, repetida o posterior a la fecha de descarga:* la fila se
    rechaza y se reporta; las demás se procesan.
  - *2c. Archivo ya importado (misma huella):* se informa y no se escribe nada.
  - *2d. Valor revisado (un INPC provisional que cambió):* se guarda como una importación nueva; los estudios
    de reajuste anteriores siguen citando la importación que usaron.
  - *2e. Nombre de archivo fuera de los patrones conocidos* (el BCV usa nombres irregulares algunos años): se
    importa si el formato valida, con ADVERTENCIA en el informe.
  - *2f. Índice de insumos de la construcción con formato aún no documentado:* se carga la serie desde el CSV
    canónico de §7.3, con su fuente declarada.
  - *4a. Insumos desconocidos o unidad no equivalente:* como UC‑02 2a y 2b.
  - *4b. Moneda distinta de Bs o USD:* se rechaza la lista.
  - *5a. Insumo sin referencia MaPreX:* R11 no lo contrasta y lo cuenta en su hallazgo INFO «no contrastable».
- **Postcondiciones:** series con su importación y huella; lista de empresa inmutable, fuera de
  `lista_vigente`, con origen por precio; informe de R11 y R12 a la fecha de evaluación.

#### UC‑18 — Reajustar los precios de la obra ejecutada

- **Actor principal:** proyectista (quien arma). **Secundario:** gerente / administrador que revisa. Desde
  S3, rol *arma* (pregunta P2 del spec maestro §10.3, ratificada por Eugenio el 2026‑10‑11).
- **Precondiciones:** versión del contrato guardada; cláusula de reajuste declarada (§8.1); índices
  importados (UC‑17); para la comprobación directa, una versión revalorada por UC‑02 por período.
- **Flujo principal**
  1. El usuario abre la versión del contrato y su cláusula de reajuste.
  2. Declara, por período, las cantidades ejecutadas por partida con su **fuente** (número y fecha del acta o
     de la valuación). En la 0.6.0 las escribe a mano; desde la 0.7.0 el sistema las toma de las valuaciones
     **registradas** y no anuladas de S2, asignando cada valuación al período de la cláusula que contiene su
     fecha *hasta*, y el estudio cita cada valuación (§8.6, RV‑11, RV‑18).
  3. El sistema calcula la **escalatoria** de cada período con las restricciones de §8.2.
  4. El usuario elige, por período, la versión revalorada por UC‑02 que sirve de **comprobación directa**.
  5. El sistema muestra, por período y en total, los dos montos lado a lado, su diferencia, y cada monto en
     las dos monedas con la tasa de la fecha de cierre del período.
  6. El usuario guarda el estudio (fuente y responsable obligatorios) y lo exporta a Excel. El estudio lleva su
     **monto reconocido** por período: el del mecanismo de la cláusula; con `ambos`, el del mecanismo que la
     cláusula declara **pagadero** (`mecanismo_pagadero`, §8.1) y, si no lo declara, la escalatoria, con la
     comprobación como referencia (S1‑R20).
- **Flujos alternativos**
  - *3a. Período dentro del primer año (contrato de más de un año):* reajuste cero, con la nota «precios
    fijos el primer año (art. 134, a cotejar)».
  - *3b. Período que cruza el aniversario:* se rechaza y se pide partirlo; el sistema no prorratea.
  - *3c. Falta el índice de un mes:* ese período no se calcula y se declara; no se extrapola.
  - *3d. Índice provisional:* se calcula y se marca «provisional».
  - *3e. Excepción del primer año por ruptura del equilibrio económico:* el usuario la declara con
    justificación y fuente; el período se calcula y se marca «excepción declarada».
  - *3f. Lo ejecutado acumulado supera lo presupuestado de una partida:* **se guarda**, con un aviso en el
    estudio, y el reajuste se calcula sobre `min(Q, q)` (la parte que no excede lo presupuestado, §8.2); desde
    la 0.7.0 la valuación que lo produce ya lleva el ERROR de R13 (S2). Se alinea con R13 y con S2‑R8 (RV‑11);
    las variaciones de obra son de S2.
  - *4a. Sin versión revalorada para el período:* la comprobación directa queda «no disponible» y se muestra
    solo la escalatoria.
  - *5a. Proyecto en USD con índices en Bs:* ADVERTENCIA visible (§8.4).
  - *6a. La suma de reajustes supera el 10 % del monto original:* nota informativa sobre la opinión de la
    Comisión de Contrataciones, marcada INDICIO (artículo sin confirmar).
  - *6b. El último período del estudio es un mes que aún no cierra:* se guarda con estado **«parcial al corte»**
    y su fecha de corte; al cerrar el mes se guarda un estudio nuevo que lo **reemplaza** (fila nueva que cita al
    parcial; el parcial se conserva, solo‑agregar) (S1‑R21).
- **Postcondiciones:** estudio guardado con sus entradas, la importación de cada índice usado, sus
  resultados y su registro; la versión del contrato no cambia.

#### UC‑19 — Registrar una valuación de obra

- **Actor principal:** residente de obra (ERS §2.3; registra lo ejecutado). **Secundarios:** proyectista;
  administrador que revisa. El **inspector** no es usuario: su nombre es la fuente de la valuación.
- **Precondiciones:** versión del contrato guardada; **línea base de control** declarada (versión, perspectiva,
  calendario; RF‑72).
- **Flujo principal:** 1) el actor abre «Control de obra»; 2) escribe la valuación (número, período desde/hasta,
  fecha, inspector) y sus líneas (partida, cantidad del período, fecha de medición opcional), o la importa de
  Excel; 3) declara fuente y responsable; 4) el sistema la guarda **sin modificar ninguna anterior**, con su
  fecha de registro visible, corre R13 y R14 y emite el informe de control (principio 7); desde ese momento la
  valuación **cuenta**, sin otro paso (RV‑18, decidida por Eugenio el 2026‑10‑11: sin conformación); 5) el
  sistema calcula al corte (fecha *hasta*) el valor ganado, las alertas y la reproyección (UC‑20, pasos 1–3) con
  las valuaciones **registradas no anuladas**.
- **Flujos alternativos:** *2a* Excel malformado o columnas faltantes: se rechaza con mensaje y fila, sin
  *traceback*, sin escribir nada; *2b* cantidad negativa o no numérica: se rechaza la entrada (una corrección es
  una anulación, 4c); *4a* sin inspector o sin número: se guarda y R14 la marca ERROR; *4b* acumulado de una
  partida mayor que lo presupuestado o partida que el presupuesto no tiene: se guarda y R13 la marca ERROR, con el
  monto como impacto; el sistema ofrece registrar la **variación de obra** por la hoja (UC‑15, versión nueva con
  la cantidad cambiada) y declararla nueva línea base (RF‑72); *4c* anular una valuación: fila de anulación con
  fuente y responsable; la anulada se conserva y deja de contar; *4d* período solapado con otra valuación: R14
  ERROR; *4e* el cliente aún no aprobó la valuación: cuenta igual desde su registro; si no la aprueba, se anula
  (4c) y sale del valor ganado y de lo ejecutado que recibe S1 (riesgo aceptado, S2‑R14).
- **Postcondiciones:** valuación inmutable con su fuente y su fecha de registro; informe de control emitido;
  ningún presupuesto cambia.

#### UC‑20 — Controlar el avance y recuperar un retraso

- **Actor principal:** proyectista (quien arma). **Secundarios:** gerente y administrador que revisa (consultan).
- **Precondiciones:** línea base de control vigente (no invalidada por un cambio de moneda, RF‑72) y al menos
  una valuación registrada no anulada.
- **Flujo principal:** 1) el sistema calcula al corte PV, EV, AC y sus índices (RF‑75) y separa el desvío
  (RF‑76); 2) evalúa las alertas (RF‑77); 3) reproyecta término, costo final y PE (RF‑77) — pasos 1 a 3
  **siempre**, sin que se pidan; 4) a pedido, calcula las opciones de recuperación con su costo (RF‑78); 5) el
  usuario elige una, declara fuente y responsable; 6) el sistema crea una versión nueva con el plan de la opción,
  su curva y su informe, guarda la decisión con la foto de los indicadores y reproyecta (RF‑79).
- **Flujos alternativos:** *1a* PV = 0 (corte antes de todo trabajo planificado): SPI «no aplica»; *1b* AC = 0:
  CPI «no aplica»; *1c* sin precios del corte (S1) para una partida: separación «no disponible» para ella;
  *1d* un costo real en otra moneda sin tasa aplicable (más de 7 días sin tasa, S1‑R2): el AC de ese costo queda
  «no disponible» y se declara con la lista de esos costos; AC y lo que depende de él (CV, CPI, consumo, EAC, VAC,
  PE proyectado) quedan «no disponible»; PV, EV, SV, SPI, precio y el término se calculan (REQ‑25); *3a* partida
  detenida (PV > 0, EV = 0): se reproyecta al ritmo global con ADVERTENCIA; *3b* SPI global = 0: término «no
  proyectable»; *4a* ninguna opción alcanza el término objetivo: se muestra la mejor y el retraso que queda; *4b*
  sin partidas por empezar: «partidas en paralelo» no aplica; *4c* partida sin mano de obra a jornal (solo destajo
  o sin mano de obra): «más cuadrillas» y «horas extra» dan «no aplica» tipado para ella (§4.6); *5a* el usuario
  no elige: nada cambia salvo lo de los pasos 1–3; *6a* sin fuente o responsable: se rechaza (como UC‑15a).
- **Postcondiciones:** la **línea base no cambia** (S2‑R3); la versión de la decisión es la vigente de la hoja.
#### UC‑09 — Armar el presupuesto con el asistente de IA

> Enmienda S4.0 (2026‑10‑11, spec [S4](especificaciones/2026-10-11-silice-s4-asistente-ia-design.md) §3.1): las referencias «§» de este caso de uso y de RF‑32, RF‑90 a RF‑95 y RNF‑18 son al spec S4.

- **Actor principal:** **quien arma** (proyectista o estimador; rol de S3)
- **Actores secundarios:** el **proveedor de IA** (sistema externo en modo nube, proceso local en modo local); el **administrador de la instalación**, que activa el asistente, registra la clave de IA de la empresa (solo desde el propio equipo, RV‑15) y fija el tope de costo
- **Precondiciones:** sesión iniciada con rol *quien arma* (S3); proyecto abierto en la hoja (UC‑15) en una versión que no esté en solo lectura; al menos un proveedor **disponible** (§5.3)
- **Disparador:** el usuario escribe su pedido en lenguaje natural («baño de 2 × 1,5 m con lavamanos, poceta y ducha; oficina contigua con 4 puntos de datos»)

**Flujo principal.**
1. El usuario abre el panel del asistente en la hoja, elige el proveedor (o queda el de la instalación) y ve la
   **vista previa de lo que se enviará** (§8.2) y la **estimación de costo** (§8.4).
2. Escribe el pedido y pulsa *Proponer*. El sistema abre una **sesión del asistente** (registro en `ia_*`, §5.5).
3. El modelo consulta el borrador y busca partidas con las herramientas de lectura (§6).
4. El modelo propone ambientes, fuentes, puntos, recorridos y partidas con las herramientas de propuesta. Cada
   llamada se **valida** (esquema Pydantic, validación semántica y construcción del modelo espacial, §7) antes de
   quedar como **propuesta pendiente**; una llamada inválida se devuelve al modelo con el motivo.
5. El sistema muestra las propuestas pendientes como un **diff del borrador**, y el resultado que tendrían: presupuesto,
   informe de auditoría completo y Estado por fila, calculados por el sistema sobre un borrador hipotético.
6. El usuario **acepta, edita o rechaza** cada propuesta. Las aceptadas entran al borrador con **origen «propuesta de
   IA»** (§5.4). El borrador se recalcula y se audita (RF‑52): el informe se genera siempre (NORMAS §2.7).
7. El usuario guarda la versión por el camino de siempre (UC‑15, RF‑53): `guardar_version` exige **fuente** (el
   sistema la prellena: «propuesta de IA, sesión N, proveedor y modelo») y **responsable** (el usuario que inició
   sesión). La IA nunca es responsable.

**Flujos alternos.**

| # | Condición | Comportamiento |
|---|---|---|
| 9a | modo nube sin conexión, sin clave de IA o con la clave de IA rechazada | el sistema lo dice con un mensaje claro y ofrece el modo local si está disponible; nunca reintenta en silencio con otro proveedor (RS4‑5) |
| 9b | modo local: el servicio de Ollama no responde o el modelo no está instalado | mensaje con lo que falta; el asistente queda inactivo; la hoja sigue funcionando a mano |
| 9c | una llamada no pasa la validación (§7) | no toca el borrador; el motivo vuelve al modelo como error de la herramienta; tras **3** rechazos seguidos de la misma herramienta la sesión se detiene y lo informa |
| 9d | una necesidad sin partida en el catálogo | el modelo la declara con `declarar_sin_partida`; queda en el informe de la sesión como pendiente (UC‑03 / RF‑16); **no se inventa** una partida |
| 9e | el proveedor rechaza el pedido (`refusal` en Claude) | se informa con la categoría si existe; las propuestas ya validadas se conservan |
| 9f | se alcanza el tope de turnos, de llamadas o de costo de la sesión (§8.4) | la sesión se detiene y conserva las propuestas válidas; el usuario puede abrir otra |
| 9g | el modelo pregunta (`preguntar_al_usuario`) | la pregunta se muestra como texto ajeno (`texto_seguro()`, RV‑14) con el rótulo «pregunta generada por la IA: no escriba contraseñas, claves ni precios»; el turno espera la respuesta, que pasa el filtro de secretos de §8.7 y entra al registro como parte del pedido (sus cifras se pueden citar, §7.3) |
| 9h | el usuario rechaza todo o cancela | el borrador queda idéntico al de antes de la sesión; el registro de la sesión se conserva |
| 9i | la versión abierta está en solo lectura (UC‑15e) | el asistente no se abre; se explica por qué |
| 9j | respuesta cortada por el límite de salida (`max_tokens`) o turno mal formado | el turno se descarta entero (no se aplican llamadas a medias) y se informa |

**Postcondiciones.** Nada se persiste en el presupuesto sin la confirmación y el guardado del usuario. Toda fila
aceptada cita su origen «propuesta de IA». El registro de la sesión (pedido, turnos, llamadas, validaciones,
decisiones, proveedor, modelo, uso y costo) queda guardado aunque no se guarde la versión.

#### UC existentes que se enmiendan

| UC | Enmienda |
|---|---|
| UC‑01 | Paso 1: al crear el proyecto (RF‑63) se **elige** la moneda (Bs o USD), sin valor por defecto en la interfaz. La API y `elaborar` conservan `"USD"` por defecto (líneas base intactas) |
| UC‑02 | Sin cambios de flujo. Su versión revalorada es la entrada de la comprobación directa (UC‑18). Revalorar con una lista de otra moneda se rechaza (SL‑E1) |
| UC‑15 | La pestaña Parámetros muestra y cambia la moneda (RF‑64); la pestaña Precios agrega moneda original, fecha del precio, tasa con fecha y fuente, erosión en dos monedas y el Estado de R11 y R12 |
| UC‑15 (S2) | Una variación de obra es una edición de cantidad (objeto `cantidad`) con su acta como fuente; el exceso que R13 marca se resuelve por esta vía (RF‑72) |
| UC‑16 (S2) | El punto de equilibrio de la versión se complementa con el PE proyectado de UC‑20 (RF‑77) |
| UC‑18 (S2) | Desde la 0.7.0 lo ejecutado por período viene de las valuaciones registradas no anuladas (RF‑72; RV‑11, RV‑18); en la 0.6.0 se escribe a mano; el paso 3f deja de rechazar el exceso sobre lo presupuestado y lo marca como R13 |

#### UC‑21 — Iniciar sesión y administrar cuentas y claves

- **Actor principal:** cualquier usuario (entrar); administrador de la instalación (administrar).
- **Precondiciones:** instalación con al menos un administrador, o código de instalación vigente (21a).
- **Flujo principal**
  1. El usuario abre Sílice; la pantalla de acceso pide usuario y contraseña. Si el cliente no es el propio equipo,
     muestra el aviso «Conexión sin cifrar» (§5.6).
  2. El sistema verifica la contraseña (Argon2), crea una **ficha de sesión nueva**, lee los roles de la base y
     muestra el menú que esos roles permiten.
  3. El administrador abre Administración: da de alta una persona con sus roles y una contraseña temporal, o cambia
     roles, desactiva, desbloquea o restablece una cuenta.
  4. El sistema registra cada acción en `evento_acceso` (sin secretos) y, al cambiar roles, desactivar o restablecer
     una cuenta, **cierra todas sus sesiones abiertas**.
  5. El usuario cierra sesión; la ficha queda cerrada.
- **Flujos alternativos**
  - *21a. Primera vez:* no hay usuarios; se crea el primer administrador con el código de instalación (§5.5).
  - *21b. Contraseña errónea o usuario inexistente:* «Usuario o contraseña incorrectos», el mismo mensaje y el mismo
    contador en los dos casos.
  - *21c. Cuenta bloqueada por intentos:* mensaje de §5.4; el mismo para un usuario inexistente.
  - *21d. Sesión expirada:* vuelve al acceso **conservando el borrador** para el mismo usuario.
  - *21e. Contraseña temporal:* obliga a cambiarla; al cambiarla se emite una ficha nueva.
  - *21f. El administrador desactiva, desbloquea o restablece una cuenta.*
  - *21g. El administrador genera, retira o revoca la clave de firma de la empresa* (solo desde el propio equipo).
  - *21h. Registra o revoca la clave pública de otra empresa,* con su huella comprobada (§7.3).
  - *21i. Muchos fallos seguidos desde cualquier pestaña:* freno global con espera progresiva (§5.4).
  - *21j. Operación sensible pedida desde otro equipo de la red* (firmar, generar o exportar la clave de firma,
    crear claves de API): se rechaza con «Esta operación solo se hace en el equipo donde está instalado Sílice».
- **Postcondiciones:** sesión vigente con usuario y roles leídos de la base; todo intento y toda acción de
  administración en `evento_acceso`; ningún secreto en claro en la base, en el registro ni en los mensajes.

#### UC‑22 — Entregar el paquete auditado

- **Actor principal:** quien arma. Para firmar hace falta la contraseña de la clave, que conoce **solo** el
  administrador (maestro §4.1, P1, ratificada por Eugenio el 2026‑10‑11): en una empresa pequeña es la misma
  persona con los dos roles, o el administrador la teclea.
- **Precondiciones:** versión guardada y sellada; clave de firma de la empresa activa (si no, 22a); cliente en el
  propio equipo para firmar (22e).
- **Flujo principal**
  1. Quien arma abre la pantalla **Entregar paquete** (sección Trabajo) y elige el proyecto y la
     versión.
  2. El sistema verifica la cadena del proyecto (22c) y muestra el resumen: total, hallazgos por severidad, cadena,
     empresa emisora y anexos que viajarán (espacio, reajuste, control, IA).
  3. El usuario elige, si quiere, el **destinatario** (una empresa registrada o un nombre) y escribe la contraseña
     de la clave.
  4. El sistema genera en memoria `presupuesto.json`, `informe.json`, `cadena.json` y los anexos, el manifiesto con
     su `paquete_id` y su `huella_anexos`, y la firma con separación de dominio (§8.1).
  5. El usuario descarga el `.silice`; el sistema guarda su SHA‑256, su `paquete_id`, la versión y el usuario en
     `evento_acceso`.
- **Flujos alternativos**
  - *22a. Sin clave de empresa:* se ofrece exportar **sin firma**, declarado en el paquete.
  - *22b. Contraseña de la clave errónea:* mensaje, no se escribe nada.
  - *22c. La cadena del proyecto está rota:* se rechaza la entrega y se dice en qué versión.
  - *22d. La versión tiene hallazgos ERROR:* se avisa y se entrega igual (el informe viaja).
  - *22e. Firma pedida desde otro equipo de la red:* se rechaza con el mensaje de 21j; se puede exportar sin firma.
  - *22f. El paquete excedería los límites de §8.4:* se rechaza con el motivo; no se genera un paquete que el
    revisor rechazaría.
- **Postcondiciones:** un `.silice` descargado; su SHA‑256 y su `paquete_id` en `evento_acceso`; la base del caso no
  cambia.

#### UC‑23 — Revisar un paquete o un presupuesto externo

- **Actor principal:** quien revisa. **Secundario:** herramienta externa (23e).
- **Precondiciones:** sesión con rol *revisa*, o clave de API vigente (23e).
- **Flujo principal**
  1. Quien revisa sube el `.silice` (o un Excel con el formato UC‑05, 23d).
  2. El sistema lo abre con límites (§8.4), verifica formato, integridad, autenticidad, cadena y anterioridad, y
     muestra el estado con el banner de versión (§8.3).
  3. El sistema reaudita en memoria con sus propias reglas y los anexos (§9, paso 3).
  4. Muestra la **diferencia entre versiones** y su costo frente a la entrega anterior o frente a su base de precios
     (§9, paso 4).
  5. Muestra quién cambió qué y, si quien revisa es también quien armó (usuario emisor o responsable de algún
     eslabón de la cadena del paquete), lo indica (§9, paso 5).
  6. Quien revisa registra su dictamen; el sistema lo guarda atado al SHA‑256 del archivo y con el estado de
     verificación de ese momento.
- **Flujos alternativos**
  - *23a. Sin firma o empresa no registrada:* **no verificado**, se audita igual.
  - *23b. Alterado (huella o firma no cuadran):* banner rojo, se audita igual para mostrar qué cambió.
  - *23c. El paquete es anterior a uno ya recibido o reescribe su historia* (§6.4).
  - *23d. Presupuesto externo en Excel (formato UC‑05):* solo se reaudita; «no contrastable» lo que no se puede
    verificar.
  - *23e. La herramienta externa manda el presupuesto por la API* y recibe el informe.
  - *23f. Formato o versión del paquete desconocidos:* se rechaza con mensaje.
  - *23g. El destinatario es otra empresa:* aviso ámbar «Este paquete se emitió para *X*».
  - *23h. El mismo archivo ya se recibió (mismo SHA‑256):* se abre el registro existente, no se duplica.
- **Postcondiciones:** `paq_recibido` con el SHA‑256 del archivo, su `paquete_id`, su estado y su cadena;
  `paq_dictamen` si se dictaminó, con quién revisó y si coincide con quien armó; nada escrito en el catálogo ni en las versiones del caso.

**UC existentes que se enmiendan por S3 (Sílice 0.8.0).**

**UC‑05** (el auditor puede auditar en memoria, sin persistir, desde la vista de revisión; la importación
persistente sigue igual); **UC‑14** (la importación del plano corre la auditoría de archivo DXF, el IDS del IFC y las
reglas R15 y R16); **UC‑15** (el responsable es el usuario de la sesión, no una caja de texto); **UC‑12** (los
recorridos se filtran por rol).

#### UC‑24 — Instalar, actualizar y operar Sílice en un equipo

- **Actor principal:** administrador de la instalación (S3). **Secundarios:** quien arma y quien revisa, que solo
  usan el acceso directo o el navegador.
- **Precondiciones:** Windows 10 22H2 u 11, x64; una cuenta de usuario (no hace falta que sea administradora); el
  instalador con su `SHA256SUMS` y la firma de este (§10.4).
- **Flujo principal**
  1. El administrador comprueba la huella del instalador contra `SHA256SUMS` y la firma de `SHA256SUMS` con la clave
     del proyecto (§10.4), ejecuta el asistente y elige los componentes (§7.2).
  2. El asistente copia el programa en `{app}` sin internet, crea los accesos directos y ejecuta
     `operacion migrar`: crea (o respalda y migra) `instalacion.db` y cada caso de `datos\casos\` (§6).
  3. El administrador abre «Sílice»: el lanzador prepara las bases, arranca en `127.0.0.1` y abre el navegador.
     Como no hay usuarios, deja el código de instalación en la carpeta de datos y en la consola.
  4. El administrador crea el primer administrador con ese código (UC‑21 de S3) y entra.
  5. Quien arma (o el administrador) elige un caso de la **lista** de `datos\casos\` o sube uno; si el caso no está
     en `head`, se migra con respaldo previo (§6.4 y §6.6).
  6. Opcional: el administrador activa la red local desde el equipo servidor, eligiendo la interfaz (§8.2), y la
     API (§8.3).
  7. Para actualizar, ejecuta el instalador de la versión siguiente: detiene Sílice, reemplaza el programa,
     respalda y migra las dos bases.
  8. Para parar, cierra la ventana de Sílice o usa «Detener Sílice».
- **Flujos alternativos**
  - *1a. La huella o la firma no coinciden:* no se instala; el manual dice a quién avisar.
  - *2a. Espacio en disco insuficiente:* el asistente lo dice antes de copiar.
  - *2b. Ya hay un Sílice en marcha:* el asistente lo detiene (`PrepareToInstall`) antes de copiar.
  - *3a. Ya hay un Sílice en marcha:* el acceso directo abre el navegador y no arranca otro.
  - *3b. El puerto está ocupado por otro programa:* mensaje con el puerto y cómo cambiarlo.
  - *3c. Base de la 0.5.0 con columnas que no cuadran (anterior a P2 o alterada a mano), no adoptable:* no se toca y
    se explica.
  - *3d. Base de una versión más nueva que el programa (bajó de versión):* no arranca y ofrece restaurar el respaldo
    previo.
  - *3e. La IP de la red local elegida ya no existe (la red cambió):* arranca solo en `127.0.0.1` y lo avisa.
  - *3f. Hay un túnel local conocido en ejecución (`cloudflared`, `ngrok`):* arranca y avisa que el túnel anula el
    filtro de IP y la regla de «solo desde este equipo» (§10.4).
  - *5a. Ruta UNC, absoluta o con `..`:* se rechaza sin crear ningún archivo.
  - *5b. Función de similitud sin su módulo:* la pantalla dice cuál módulo falta (RF‑97 g).
  - *6a. Activar la red local sin poder elevar permisos:* queda apagada y se explica.
  - *7a. Una migración falla:* las bases se restauran del juego de respaldo, Sílice no arranca y explica qué hacer.
  - *7b. Restaurar un juego de respaldo que trae `instalacion.db`:* Sílice lista los eventos de seguridad perdidos y
    exige que el administrador los revise antes de las operaciones sensibles (§6.5).
  - *8a. Desinstalar:* los datos quedan y el asistente dice dónde.
- **Postcondiciones:** programa en `{app}`; datos en `%LOCALAPPDATA%\Silice` con `instalacion.db` y los casos en
  `head` y un juego de respaldo por cada migración; red local y API en el estado configurado (apagadas por defecto);
  ninguna conexión saliente salvo el asistente en modo nube activado por el administrador; tras desinstalar, los
  datos y los respaldos siguen ahí.

> **Enmienda a UC‑12 y UC‑21 (Sílice 1.0.0):** los recorridos de UC‑12 parten del acceso directo, no de la terminal; el primer administrador de UC‑21 se crea con el código de instalación que el arranque deja en la carpeta de datos (spec S5 §4.1 y §8.1).

### 2.3 Características de los usuarios

| Actor | Descripción | UC principales |
|---|---|---|
| Proyectista / estimador | elabora y actualiza presupuestos | UC‑01, 02, 03, 04, 08, 10, 11, 13, 14, 15, 16 |
| Auditor | revisa presupuestos de terceros | UC‑05, 07 |
| Residente de obra | registra rendimientos medidos | UC‑06 |
| Administrador del catálogo | mantiene partidas, insumos y listas de precios | UC‑02, 03 |
| Gerente | decide sobre el presupuesto de un proyecto —no lo edita— y consulta el punto de equilibrio y los totales de la hoja | UC‑16 |
| Usuario nuevo / evaluador | abre la aplicación por primera vez —tribunal, tutor o presupuestista recién llegado— y necesita orientarse sin formación previa | UC‑12 |
| Administrador de la instalación | crea cuentas y les da roles; administra la clave de firma de la empresa, la empresa propia, las empresas registradas, la red local y las claves de la API; rol *administrador* | UC‑21 |
| Quien revisa | recibe el paquete de otra empresa o de otra área (administrador del contrato, cliente, ente contratante, auditor, gerente): lo verifica, lo reaudita, compara y dictamina; rol *revisa* | UC‑23 |
| Herramienta externa | un plugin o programa que llama a la API de Sílice con su **clave de API** y recibe el informe; sin rol | UC‑23 |

### 2.4 Restricciones
- Todo monto y cantidad en `Decimal` (NORMAS.md §2).
- El núcleo no depende de ningún dominio; los dominios entran por `AdaptadorDominio` (NORMAS.md §5).
- Procesamiento sobre IFC (IFC2x3 e IFC 4) y DXF, no sobre formatos nativos de modelado
  (independencia tecnológica). IFC y DXF son entradas de planos (UC‑14, RF‑50 y RF‑51); el DXF
  exige la convención de capas del sistema. No se leen planos en PDF ni escaneados.
- Codificación de partidas COVENIN 2000; estructura de costos según la Convención Colectiva vigente.
- Ejecución local en Windows/Linux con Python ≥ 3.12.

### 2.5 Suposiciones y dependencias
- Disponibilidad de la línea base auditada (existe) y de un modelo IFC de prueba: existe
  `data/samples/tanquilla.ifc`, generado programáticamente por `scripts/generar_tanquilla_ifc.py`, y
  la compuerta G1 se cruzó **con salvedad**: el adaptador civil IFC reproduce exacto el cálculo manual
  contra ese modelo, no contra un export de un modelador BIM
  ([bitácora de F.1](bitacora/2026-08-31-F1-api-3d.md)); falta la prueba con exports de al menos dos
  modeladores (RNF‑09).
- Volumen de registros históricos suficiente para el módulo predictivo (compuerta G2, NORMAS.md §8.1).
- Autorización de uso académico de una base de precios de referencia, o catálogo reducido propio.

### 2.6 Requisitos futuros
Sombra digital (avance real de obra vs curva planificada); multimoneda con factor de actualización;
reconocimiento de planos en PDF o escaneados (la importación de DXF e IFC ya no es futura: UC‑14).

---

## 3. Requisitos específicos

### 3.1 Interfaces externas
- **Usuario:** interfaz web local (Streamlit) con una pantalla de Inicio que lleva al usuario por
  recorridos guiados (UC‑12). No todos los casos de uso tienen pantalla: la tabla siguiente declara la
  capa que realiza cada uno (INV‑030). UC‑09 queda vacante (sección 2.2).
- **Software:** API REST (FastAPI) con esquema OpenAPI en `docs/api.json`.

| UC | Interfaz (pantalla del menú) | API REST | Solo biblioteca o script |
|---|---|---|---|
| UC‑01 | «Elaborar un presupuesto» (extrae, elabora con el plan de trabajo del proyectista, audita y descarga el Excel; propone el rendimiento que falta, flujo 3b) y el bloque de cantidades de «Componer una partida»; la interfaz no guarda el presupuesto; desde el sprint final lo guarda la hoja del proyecto (UC‑15) | `POST /proyectos` (paso 1, desde C6: nombre único y no vacío, `descripcion` y `dominio` opcionales, el dominio uno de `Dominio`; 201, o 422 sin crear nada; desde el sprint final la interfaz también crea proyectos, RF‑63), `POST /computos/{dominio}` y `POST /presupuestos` (elabora con el `plan` del proyectista, audita y guarda; sin rendimiento vigente, 409 con la propuesta, flujo 3b); `GET /presupuestos/{codigo}/excel` | — |
| UC‑02 | «Actualizar precios» (al subir el archivo lista los desconocidos y ofrece «Dar de alta», ninguno elegido, flujo 2a; revalora, guarda la versión y ofrece descartarla; avisa aparte de los dados de alta, los ignorados de 2a y los rechazados de 2b) e «Historico de cambios de precio» | `POST /listas-precios` (desde C6, el campo repetible `dar_de_alta` con descripciones del archivo, que eligen por identidad normalizada; la respuesta trae `dados_de_alta`, `ignorados` de 2a, `rechazados` de 2b y `desconocidos`, los dos últimos juntos; un alta de algo que no es desconocido del archivo, o dos filas elegidas del mismo insumo con precios distintos, es 422 sin escribir), `POST /presupuestos/{codigo}/actualizacion`, `GET /cambios-precio`; descartar una versión no tiene ruta. Por la API no hay vista previa del flujo 2a: el cliente elige en la misma carga a partir de su archivo y de `GET /insumos`, porque cargar para ver los desconocidos y volver a cargar deja dos listas. El nombre de la lista debe ser único: `…/actualizacion` la busca por nombre | — |
| UC‑03 | «Partidas similares» (solo lectura); ayuda de similares en «Componer una partida»; propuestas de los pendientes en «Elaborar un presupuesto» | propuestas de los pendientes en la respuesta de `POST /presupuestos` | — |
| UC‑04 | ninguna | ninguna | `adapters/civil/recalculo.py` (`recalcular`, `emparejar`), ejercido solo por las pruebas |
| UC‑05 | el informe se muestra al elaborar, al componer y al revalorar; no hay pantalla de auditoría de un presupuesto ajeno ni de importación (ruling C6‑3) | `POST /presupuestos/importar` (desde C6, RF‑24: multipart con `archivo` XLSX y `proyecto`; 201; 404 si el proyecto no existe; 422 si el archivo no es un libro legible o está mal formado, con archivo, hoja y fila, si un código de partida ya está en el catálogo, si el código de presupuesto se repite en el proyecto o si la moneda no es la de la lista vigente, comparada exacta; si falla, no deja nada escrito), `GET /presupuestos/{codigo}/informe` y la hoja de auditoría de `…/excel` | — |
| UC‑06 | «Componer una partida» propone el rendimiento del histórico, advierte al apartarse y, desde C6, registra la justificación de la advertencia por rango (flujo 4a); «Elaborar un presupuesto» lo propone en el flujo 3b de UC‑01; ninguna de las dos registra medidos | `POST /ejecuciones`, `GET /ejecuciones`, `GET /partidas/{codigo}/rendimientos`, `POST /partidas/{codigo}/rendimientos` (desde C6, el campo `justificacion`, flujo 4a: se registra solo con advertencia, ligada al rendimiento de la misma petición; con advertencia y en blanco, 422 sin registrar nada; la respuesta la devuelve y ninguna ruta la lee después) | — |
| UC‑07 | «Componer una partida» contrasta el precio con la estimación por reglas (clase 3 de AACE); para una partida nueva, avisa que el contraste no es posible (flujo 3a); desde C6, «Actualizar precios» incorpora los precios atípicos de la lista nueva al informe de la versión revalorada (paso 5, con su alcance vigente) | `POST /presupuestos/{codigo}/actualizacion` (desde C6, paso 5: los atípicos de la lista nueva entran como `ATIPICO` ADVERTENCIA al informe de la versión nueva, que sirve `GET /presupuestos/{codigo_nuevo}/informe`; con el extra `ml` y al menos 8 variaciones en el histórico) | `scripts/generar_resultados_ml.py` escribe `docs/resultados_ml.md` |
| UC‑08 | «Escenarios de sensibilidad» | `POST /presupuestos/{codigo}/escenarios` | — |
| UC‑10, UC‑11 | «Componer una partida» | ninguna | — |
| UC‑12 | «Inicio» y el marco común de las pantallas (`ui/app.py`) | ninguna | — |
| UC‑13, UC‑15, UC‑16 | «Hoja del proyecto» (pestañas Espacio y metrajes, APU, Presupuesto, Plan y curva, Punto de equilibrio, Precios, Parámetros, Auditoría y Trazabilidad) | ninguna: la API conserva sus rutas | — |
| UC‑17, UC‑18 | páginas «Índices», «Precios de la empresa» y «Reajuste» (Sílice 0.6.0) | ninguna | `adapters/bcv` (importación sin conexión) |
| UC‑14 | herramienta «Importar plano» de la barra superior (RF‑60) | ninguna | — |
- **Archivos de entrada:** IFC (IFC2x3 e IFC 4) y DXF de planos (UC‑14), IFC 4 (dominio civil), CSV de topología (telecom), registro de activos
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
asignado (RF‑64 (el siguiente número libre tras RF‑63; la reserva de UC‑09 sigue siendo RF‑32 vacante)). Esta enmienda prevalece sobre la instrucción «numera desde RF‑32» de
[PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md):78‑80, que queda desactualizada hasta que la Sesión A0.1
la corrija.

**Enmienda S4.0 (2026‑10‑11):** la reserva de UC‑09 queda resuelta con RF‑32 y RF‑90 a RF‑95 (maestro §9); RF‑64 pertenece a S1.

| RF | Enunciado | Prioridad | UC | Incremento | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑01 | El sistema calculará el precio unitario de una partida a partir de su composición y los parámetros de costo según la fórmula de NORMAS.md §4 | Esencial | UC‑01 | I0.3 | Los cinco precios unitarios de la línea base se reproducen con ± 0,01; los materiales no se dividen entre el rendimiento y la administración y la utilidad se aplican en cascada |
| RF‑02 | El sistema generará siempre el informe de auditoría al producir o cargar un presupuesto | Esencial | UC‑05 | I4 | Todo presupuesto elaborado o recargado trae su informe; sobre el presupuesto de prueba se detectan 7 de 7 inconsistencias, y el informe recargado declara los ítems pendientes del documento emitido y, en una versión revalorada, los precios atípicos que declaró su revaloración (UC‑07 5) |
| RF‑03 | Toda cantidad de obra conservará `origen_id`, `origen_tipo` y, si aplica, la regla que la produjo | Esencial | UC‑01, 04 | I0.1 | Ningún `ItemComputo` sin `origen_id`; un ítem de origen REGLA sin expresión se rechaza; los ítems que derivan de una regla llevan su expresión y sus parámetros, y todo hallazgo de partida referencia un origen trazable |
| RF‑04 | El sistema obtendrá las cantidades de obra invocando `AdaptadorDominio.extraer(fuente)`, sin que el núcleo conozca el dominio ni el formato de la fuente | Esencial | UC‑01 | I0.1, I3.1 | Ningún adaptador importa de `core` fuera de `core.contracts`; todo `ItemComputo` extraído trae `origen_id` y `origen_tipo`; el adaptador IFC usa el GlobalId como `origen_id` y reproduce el cálculo manual de la tanquilla (compuerta G1, cruzada con salvedad: sección 2.5) |
| RF‑05 | El sistema persistirá partidas, insumos, composiciones y rendimientos en SQLite; `scripts/seed.py` cargará la línea base en la base de datos, de modo que el presupuesto se reproduzca completo desde ella | Esencial | UC‑01 | I0.4 | Los cinco APU recuperados de la base dan los mismos precios unitarios que el fixture |
| RF‑06 | El sistema construirá el presupuesto asociando cada `ItemComputo` a su `ComposicionAPU`, calculando su `ResultadoAPU` y emitiendo una `PartidaPresupuestada` por ítem, con total por partida y total general | Esencial | UC‑01 | I0.5 | El presupuesto de la línea base corregida se reproduce partida por partida desde el catálogo persistido |
| RF‑07 | El sistema generará la curva de inversión de modo que su acumulado final sea exactamente igual al total del presupuesto | Esencial | UC‑01 | I0.5 | `total_curva == total` sin tolerancia (la curva del caso didáctico de la línea base, [NORMAS.md §1](../NORMAS.md#1-qué-es-este-proyecto), cerraba en 99,30 %) |
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
| RF‑37 | Los recorridos guiados se declararán una sola vez, en un módulo sin Streamlit ni base de datos, y el destino de cada paso será la ruta de una página registrada | Esencial | UC‑12 | U1 | Una sola declaración de recorridos, sin Streamlit ni base de datos; todo `paso.pagina` es la ruta de una página visible **para el rol de la sesión**, con y sin modo entrega (S3 filtra los pasos que el rol no ve); desde el sprint final los recorridos incluyen la pantalla «Hoja del proyecto» |
| RF‑38 | El archivo de la base se fijará una vez por sesión y todas las pantallas operarán sobre ese mismo caso; ninguna pantalla distinta del Inicio pedirá la ruta | Esencial | UC‑12 | U1 | Resolución sesión → entorno → constante, `RUTA_BASE_POR_DEFECTO` definida una sola vez en `ui/`, y ninguna página salvo el Inicio pide la ruta |
| RF‑39 | El sistema mostrará en toda pantalla, en solo lectura, el caso abierto y su estado: existencia del archivo, número de partidas, número de insumos y si hay lista de precios vigente | Esencial | UC‑12 | U1 | El estado es correcto sobre una base inexistente, vacía, sembrada e ilegible, sin traza, y el marco lo pinta en cada una de las once pantallas (diez hasta el sprint final, más la «Hoja del proyecto») |
| RF‑40 | Cuando el caso abierto no exista o no contenga partidas, el Inicio lo declarará y ofrecerá cargar el caso de demostración, sin exponer nunca la opción de reiniciar la base | Esencial | UC‑12 | U1 | Estado vacío, siembra, y ningún botón de sembrar con partidas; el literal del flag de reinicio no aparece en ningún archivo de `ui/` |
| RF‑41 | Cada pantalla del recorrido activo mostrará su paso siguiente y la posición del usuario en el recorrido, tomados de la declaración única de recorridos; una pantalla que no pertenezca a ningún recorrido no mostrará ninguno de los dos | Deseable | UC‑12 | U1 | `paso_siguiente` y la posición del recorrido salen de la declaración única; el botón «Siguiente» lleva a su destino y una pantalla fuera del recorrido no lo muestra |
| RF‑42 | El menú presentará cada pantalla con el nombre de su oficio, agrupada en cuatro secciones —Trabajo, Revisión, Investigación y Administración— en el orden del trabajo real, **visibles según el rol de la cuenta** (S3); el código del caso de uso permanecerá visible como subtítulo; desde el sprint final la «Hoja del proyecto» forma parte de la sección Trabajo | Deseable | UC‑12 | U1 | Secciones y orden sin Streamlit, con las once pantallas; ningún título lleva código de UC; el subtítulo «Caso de uso …» aparece en las cinco pantallas que tienen uno |
| RF‑43 | Con el modo entrega activo, ninguna pantalla de Trabajo **que el rol de la cuenta permita** quedará inaccesible | Esencial | UC‑12 | U1 | La sección Trabajo es idéntica con y sin modo entrega, y ningún paso de un recorrido sale de Trabajo; el modo entrega solo oculta Investigación |
| RF‑44 | La hoja de metrajes registrará ambientes, fuentes, puntos, recorridos y orígenes de medida (spec §6.2) | Esencial | UC‑13 | SF1 | Cada tipo de origen exige su referencia (spec §6.3); faltando una, la fila se acepta en la versión y R8 la marca ERROR *La hoja edita orígenes, ambientes, fuentes, puntos y vértices declarados; los circuitos y las sobrescrituras de segmento se conservan pero no se editan.* **Alcance vigente: parcial.** No editable en la hoja (circuitos, sobrescrituras de segmento y orden de la cadena solo se declaran al importar un plano o por la API); limitación vigente. |
| RF‑45 | El sistema propondrá un recorrido para cada punto (spec §6.4) y el usuario lo reemplazará declarando vértices | Esencial | UC‑13 | SF1 | Las longitudes del recorrido propuesto del baño de OF‑001 igualan la memoria de cálculo; un recorrido declarado sustituye al propuesto |
| RF‑46 | La geometría unirá los segmentos coincidentes, partirá los solapes colineales y guardará los segmentos derivados con sobrescritura opcional de diámetro y de empotrado (spec §6.5) | Esencial | UC‑13 | SF1 | Los solapes parciales de la memoria de cálculo dan la longitud unida esperada a ± 0,001 m *La sobrescritura de diámetro y de empotrado se guarda y se aplica.* **Alcance vigente: parcial.** No editable en la hoja (circuitos, sobrescrituras de segmento y orden de la cadena solo se declaran al importar un plano o por la API); limitación vigente. |
| RF‑47 | El sistema aplicará reglas de cantidades de **agua** (agua fría y drenaje), con fuente o supuesto declarado (spec §7.1) | Esencial | UC‑13 | SF1 | Las cantidades del baño de OF‑001 igualan la memoria de cálculo |
| RF‑48 | El sistema aplicará reglas de cantidades de **datos** (spec §7.2) | Esencial | UC‑13 | SF2 | Las cantidades de datos de OF‑001 igualan la memoria de cálculo |
| RF‑49 | El sistema aplicará reglas de cantidades de **electricidad**, con recorrido por circuito y orden de la cadena propuesto por vecino más cercano y editable (spec §7.3) | Esencial | UC‑13 | SF2 | Las cantidades eléctricas de OF‑001 igualan la memoria de cálculo *El orden de la cadena se declara en el modelo y se aplica.* **Alcance vigente: parcial.** No editable en la hoja (circuitos, sobrescrituras de segmento y orden de la cadena solo se declaran al importar un plano o por la API); limitación vigente. |
| RF‑50 | El sistema importará DXF con la convención de capas de spec §6.6.1, se detendrá si falta `$INSUNITS`, emitirá un informe de importación y reimportará por *handle*. La convención admite como atributos opcionales de los bloques de punto `ID`, `CATEGORIA`, `LLAVE`, `SUPERFICIE` y `AMBIENTE` (extensión RS‑16, pendiente de ratificar por Eugenio). Un circuito importado lleva conductores y puntos máximos supuestos y R8 lo advierte hasta que se declaren (RS‑17). La altura pendiente se reconoce por la marca `altura=pendiente` y el alto provisional de 2,5 m: un alto real de 2,5 m con la marca puesta sigue en ADVERTENCIA hasta `cargar_alturas` (falso positivo conocido, RS‑15). Rechaza el archivo de más de 20 MB o con más entidades que el tope (`MAX_ENTIDADES_DXF`) | Deseable | UC‑14 | SF5 | El DXF de OF‑001, con alturas cargadas, da las mismas cantidades derivadas que la hoja manual |
| RF‑51 | El sistema importará espacios, terminales y tableros desde IFC, con informe de importación y reimportación por `GlobalId` | Deseable | UC‑14 | SF5 | El IFC de prueba da las filas esperadas; hereda la salvedad de RNF‑09 si el archivo es programático. **Alcance vigente:** el IFC no trae fuentes ni circuitos, de modo que las filas importadas quedan sin ellos hasta que se declaren; y no infiere el drenaje (RS‑19) |
| RF‑52 | La hoja del proyecto editará las celdas de entrada de spec §9.2 y recalculará y auditará en el borrador sin persistir | Esencial | UC‑15 | SF3 | Una edición cambia totales, curva, PE y columna Estado sin crear versión |
| RF‑53 | Guardar creará una versión nueva con su informe, la instantánea de sus composiciones y de su espacio, y un `RegistroCambio` por celda cambiada; exigirá fuente del cambio y responsable | Esencial | UC‑15 | SF3 | Sin fuente o sin responsable se rechaza; la versión anterior sigue cargando idéntica. **Alcance vigente:** una fuente y un responsable por guardado, no por celda (H‑2); cada `RegistroCambio` hereda los del guardado |
| RF‑54 | Restaurar una versión N creará una versión nueva copia de N, con su `RegistroCambio`; el historial solo crece | Esencial | UC‑15 | SF3 | Tras restaurar, la versión nueva es igual a N y N sigue existiendo |
| RF‑55 | La columna Estado de cada fila mostrará el peor hallazgo que la toca y enlazará a su detalle | Esencial | UC‑15 | SF3 | Un error sembrado en una fila marca esa fila y ninguna otra |
| RF‑56 | Cada precio mostrará lista, referencia, fecha, moneda original y tasa con su fecha; una cotización se registrará con su fuente, con alcance del proyecto, y prevalecerá sobre la lista global para ese insumo hasta que se retire | Esencial | UC‑15, UC‑02, UC‑07 | SF3 | La cotización cambia solo ese insumo en ese proyecto; la versión resultante conserva el plan y la curva; una actualización global posterior por UC‑02 no la pisa |
| RF‑57 | Los parámetros del proyecto serán editables (los de `ParametrosCosto`: FCAS, administración, utilidad y los demás que ya define el contrato), con fuente | Esencial | UC‑15 | SF3 | Cambiar el FCAS recalcula todos los APU de la versión y queda en el registro |
| RF‑58 | El sistema calculará el punto de equilibrio y lo ubicará en la curva, con los casos límite de spec §9.4 | Esencial | UC‑16 | SF3 | TI‑001 da 28 586,76 USD en el Día 6 (literal de la bitácora); cada caso límite da su salida declarada |
| RF‑59 | El sistema exportará la hoja del proyecto a Excel con fórmulas vivas, hojas de la hoja, trazabilidad y auditoría (spec §9.5) | Esencial | UC‑15 | SF3 | Las fórmulas evaluadas dan los totales del sistema dentro de la tolerancia de spec §9.5 |
| RF‑60 | La interfaz tendrá una barra superior con navegación arriba y las herramientas de spec §10 | Esencial | todos | SF4 | AppTest: navegación arriba, modo entrega oculta Investigación, cada herramienta lleva a su acción |
| RF‑61 | El sistema ejecutará las reglas de auditoría R8, R9 y R10 (spec §8.2) | Esencial | UC‑13, UC‑15 | SF1–SF2 | Un error sembrado por condición, con valores frontera, se detecta *Hecho en SF2: R8, R9 y R10 con fronteras exactas; R10 da ADVERTENCIA mientras sus tres límites sean supuestos declarados; el máximo de puntos por circuito, aunque lo declare el usuario, también baja a ADVERTENCIA mientras el límite base sea supuesto. Limitación: R10 evalúa solo tramos de drenaje que declaran su pendiente (el recorrido propuesto de §6.4 no la trae), por lo que esa condición no se dispara con recorridos propuestos.* **Alcance vigente:** R10 no propone pendiente propia; sus tres límites (pendiente mínima, enlace máximo y máximo de puntos por circuito) son supuestos declarados y por eso bajan a ADVERTENCIA (RS‑11) |
| RF‑62 | Los hallazgos de reglas que no están en las siete se conservarán al recargar, revalorar, simular escenarios, importar y en la API (spec §8.4) | Esencial | UC‑05, UC‑15 | SF1 | El informe recargado de una versión con hoja es idéntico al emitido |
| RF‑63 | La interfaz creará proyectos con nombre único y no vacío | Esencial | UC‑01 | SF4 | Nombre vacío o repetido se rechaza con mensaje |
| RF‑64 | La moneda del proyecto (Bs o USD) se elige al crearlo; cambiarla crea una versión nueva **convertida** (motivo `conversion`), con la tasa fechada y su fuente, el bono de alimentación convertido, el plan conservado y un `RegistroCambio` (objeto `moneda`); la versión anterior no cambia | Esencial | UC‑01, UC‑15 | S1‑1 | total convertido = total ÷ tasa (de Bs a USD) o × tasa (de USD a Bs) a ± 0,01 en la presentación, para la clínica y TI‑001; la versión de origen recarga idéntica; sin tasa, sin fecha o sin fuente se rechaza. Desde la 0.7.0: si el proyecto tiene una línea base de control declarada (S2), la conversión la deja **invalidada** y hay que declararla de nuevo sobre la versión convertida (RV‑11; la prueba la escribe S2) |
| RF‑65 | Cada precio tiene moneda original, precio original, fecha, y, si se convirtió, tasa con su fecha y su fuente (§5.1); una versión solo se valora con una lista de **su** moneda | Esencial | UC‑15, UC‑17 | S1‑1 | la pestaña Precios muestra los seis datos por insumo; guardar una versión en Bs con una lista en USD se rechaza; las bases anteriores muestran el origen heredado de la lista |
| RF‑66 | La erosión de cada precio (§5.3) se muestra en Bs y en USD a una fecha de evaluación declarada, por insumo y por versión | Esencial | UC‑15, UC‑17 | S1‑1 | la memoria `s1_conversion.md` (§9.1) se reproduce con 28 dígitos y a ± 0,01 en la presentación |
| RF‑67 | La lista de una empresa es una lista de alcance `empresa`: copia de una lista base declarada con los precios propios (fecha, moneda y fuente por precio), inmutable, fuera de `lista_vigente`, usable para valorar una versión | Esencial | UC‑17 | S1‑3 | `lista_vigente` no la devuelve; un precio propio prevalece sobre el de la base; cada precio dice si es propio o heredado; la lista de una empresa no cambia la valoración de otra ni la de ningún proyecto que no la referencie |
| RF‑68 | Reglas **R11** (precio fuera de rango frente a MaPreX) y **R12** (precio vencido o sin trazabilidad de tasa) con la severidad de §6.3, el impacto en dinero y la fecha de evaluación en cada hallazgo | Esencial | UC‑17, UC‑15 | S1‑3 | conjunto **exacto** de hallazgos de la memoria `s1_precios_empresa.md` (regla, severidad, insumo, impacto a ± 0,01) a la fecha de evaluación que fija la memoria, con sus fronteras exactas (§9.1); reevaluar a otra fecha no reescribe ninguna fila guardada |
| RF‑69 | Importación sin conexión de la tasa (.xls trimestral), el INPC (.xls mensual) y el índice de insumos de la construcción, con validación de formato, fuente y fecha, informe previo, huella SHA‑256 e importaciones idempotentes | Esencial | UC‑17 | S1‑2 | el archivo real versionado de un trimestre da sus N hojas como N valores de compra y de venta del USD, y la primera, la última y una del medio dan los valores **transcritos a mano** en `FUENTE.md` (§9.3; incluye 858,02 / 860,18 Bs con fecha valor 01‑10‑2026); cada caso negativo de la fila RF‑69 de §9.2 se rechaza con su mensaje; reimportar la misma huella no escribe nada |
| RF‑70 | Reajuste por **fórmula escalatoria** (§8.3) con las restricciones del art. 134 de §8.2 («a cotejar») y la cláusula declarada (§8.1) | Esencial | UC‑18 | S1‑4 | la memoria `s1_reajuste.md` (estructura `declarada`) da 15 300,00 Bs en el período del ejemplo; la memoria `s1_reajuste_por_partida.md` (estructura `por_partida`, dos partidas) da K_A = 1,175, K_B = 1,185 y 10 298,34 Bs (§9.1.2); cada frontera de §9.2 da su salida declarada |
| RF‑71 | **Comprobación directa** (con la versión revalorada por UC‑02) lado a lado con la escalatoria, por período y total, en las dos monedas; el estudio se guarda con fuente y responsable y se exporta por `hojas_extra`. Con `ambos`, el monto reconocido es el del mecanismo pagadero de la cláusula, o la escalatoria si no lo declara; el estudio de un mes en curso se guarda «parcial al corte» y se reemplaza al cerrar el mes (§8.5). Desde la 0.7.0, lo ejecutado de cada período sale de las valuaciones registradas no anuladas de S2, citadas, asignadas por su fecha *hasta* (§8.6) | Esencial | UC‑18 | S1‑4 (0.7.0 para el último criterio) | la memoria da 16 000,00 Bs y una diferencia de −700,00 Bs; 18,00 y 18,82 USD a la tasa del ejemplo; la memoria por partida da 11 680,00 Bs y −1 381,66 Bs; el estudio recargado es idéntico al guardado; con la memoria `s1_reajuste.md` y `mecanismo` = `ambos`, el reconocido es 16 000,00 Bs si `mecanismo_pagadero` = `comprobacion` y 15 300,00 Bs (la escalatoria) si la cláusula no lo declara; un estudio guardado antes del cierre de su mes queda «parcial al corte» y el del cierre lo reemplaza sin borrarlo; lo ejecutado por encima de lo presupuestado se guarda con aviso y se reajusta sobre `min(Q, q)` (3f). **Criterio del puente (0.7.0, lo entrega RF‑72 de S2):** una valuación registrada con *hasta* = último día del mes cae en ese período y una con *hasta* = primer día del mes siguiente cae en el siguiente; una anulada no cuenta; el estudio cita el número de cada valuación usada |
| RF‑72 | El sistema registrará la **línea base de control** (versión, perspectiva *costo* o *precio*, fecha desde, fuente, responsable) y su **calendario** (fecha de inicio, días hábiles por período, feriados), y valuaciones con número, período, fecha, inspector y líneas por partida, que **cuentan desde su registro**, sin conformación (RV‑18; S2‑R14); las valuaciones no se editan ni se borran: se anulan con fuente, y la anulación es la única forma de sacarlas del cálculo. Entregará a S1 **lo ejecutado por período** (`ejecutado_por_periodo`, RV‑11): las valuaciones registradas no anuladas, cada una asignada entera al período mensual de la cláusula que contiene su fecha *hasta*, con la cantidad del período y la **cantidad reajustable** `min(Q acumulado al cierre, q) − min(Q acumulado al cierre anterior, q)`, con aviso cuando difieren. Un cambio de moneda del proyecto posterior a la línea base de control la **invalida** | Esencial | UC‑19 | S2‑1 | OB‑S2 se registra completa; editar o borrar una valuación no es posible por ninguna función de `core`; anular deja la anulada en la base y fuera del cálculo; cantidad negativa → `ValueError`; OB‑S2 entrega para noviembre de 2026 A 90 y B 60 (V‑01 y V‑02, registradas); una valuación anulada no entra; con una valuación registrada más de B 150 en noviembre, B entrega cantidad 210, reajustable 200 y el aviso, y R13 da ERROR; una valuación del 2026‑11‑30 al 2026‑12‑04 va entera a diciembre; tras convertir la moneda del proyecto, `instantanea_control` rechaza con «línea base invalidada: declárela de nuevo» |
| RF‑73 | El sistema importará valuaciones y costos reales desde un XLSX con las hojas y columnas de §6.2, con informe de importación; un archivo malformado se rechaza entero | Esencial (decisión H‑D5; cae solo si Eugenio lo acepta, REQ‑21) | UC‑19 | S2‑1 | el XLSX de OB‑S2 da las mismas valuaciones que la entrada a mano; cada malformación de §7.2 (fila RF‑73) da su mensaje sin *traceback* y sin escribir |
| RF‑74 | Al registrar, importar o anular, el sistema ejecutará **R13 y R14** (§3.4) sobre las valuaciones no anuladas y emitirá el informe de control | Esencial | UC‑19 | S2‑1 | la valuación sembrada V‑S de §7.1 da **exactamente** los seis hallazgos de §7.1 (regla, severidad, impacto); cada frontera de §7.3; R13 sobre una valuación de SIS‑001 (presupuesto de sistemas) da su conjunto exacto (ARQ‑H3) |
| RF‑75 | El sistema calculará al corte PV, EV, AC, SV, CV, SPI, CPI, BAC, EAC (dos métodos), VAC y la fecha estimada de término (dos métodos) con las fórmulas de §4.2, en la moneda del proyecto, con las valuaciones registradas no anuladas; los costos reales se convierten con la tasa de su fecha (S1) y, sin tasa aplicable, su AC queda «no disponible» y se declara | Esencial | UC‑20 | S2‑2 | OB‑S2 da los valores de §7.1 a ± 0,01 (montos) y ± 0,0001 (índices); las fechas, exactas; un costo real en Bs con más de 7 días sin tasa: AC, CV, CPI, consumo y EAC «no disponible» con ese costo listado, y PV, EV, SPI iguales a los de §7.1 (REQ‑25) |
| RF‑76 | El sistema hará la **separación del desvío de control** en **plazo** (SV), **precio** y **consumo** (§4.3; término cruzado en el consumo), con el método y la fuente del precio del corte (S1), y la identidad CV = precio + consumo será **exacta**. Es distinta de la «diferencia entre versiones» de S3 (RV‑10) | Esencial | UC‑20 | S2‑2 | OB‑S2: precio −60,00, consumo −20,00, CV −80,00; la identidad con `Decimal` da diferencia cero en OB‑S2 y en el generador de RNF‑15 |
| RF‑77 | Al registrar o anular una valuación, el sistema evaluará las **alertas** AL‑1 a AL‑6 con sus umbrales declarados (§4.5) y **reproyectará** plan, término, costo final y PE (§4.4, §4.7), sin que se pida | Esencial | UC‑19, UC‑20 | S2‑2 | OB‑S2: las alertas exactas de §7.1 en sus dos escenarios (sin reajuste y con el reajuste reconocido); término reproyectado 2026‑12‑02; plan reproyectado de §7.1; cada frontera de umbral de §7.3 |
| RF‑78 | A pedido, el sistema calculará las opciones **más cuadrillas, horas extra, partidas en paralelo y aceptar el retraso** (§4.6) desde el rendimiento y la cuadrilla del APU de cada partida, con su término, costo directo adicional, costo indirecto, EAC y PE, y la lista de supuestos usados con su naturaleza (fuente o supuesto declarado) | Esencial | UC‑20 | S2‑3 | OB‑S2: los cuatro resultados de §7.1 con el PE' de sus dos escenarios; horas extra nunca superan los límites de la LOTTT (§4.6.2); cada supuesto aparece en la salida; una partida de TI‑001 y una de SIS‑001 sin mano de obra a jornal (§4.6) dan «no aplica» tipado en cuadrillas y horas extra, sin división entre cero (ARQ‑H3) |
| RF‑79 | Elegir una opción creará una **versión nueva** (motivo `recuperacion`) con el plan de la opción, su curva y su informe, un `RegistroCambio` por fracción del plan que cambió y una `DecisionRecuperacion` con la foto de indicadores, opción y supuestos; fuente y responsable obligatorios; la línea base no cambia | Esencial | UC‑20 | S2‑3 | tras elegir «más cuadrillas» en OB‑S2: R2 y R7 sin hallazgos, la curva cierra en el total, los registros de §7.1, la decisión recarga idéntica y el SPI al mismo corte sigue en 0,80 |
| RF‑96 | **Migraciones con respaldo y vuelta atrás, en dos bases.** El esquema se versiona con Alembic en dos destinos, cada uno con su `alembic_version` y su lista `METADATAS` explícita: la **instalación** (`seguridad`) y el **caso** (`core.models`, `METADATA_ESPACIO`, `paquete`, `asistente`). La revisión base del caso es el esquema de la 0.5.0 y cada cambio posterior trae su revisión, desde la 0.6.0. Antes de aplicar cualquier revisión pendiente se respaldan **juntas** la instalación y los casos que se migran, en un juego con una sola ficha; si la migración falla, la base no queda modificada. Las bases de la 0.5.0 se adoptan. Un caso se abre solo con `preparar_base` y desde `datos\casos\` | Esencial | UC‑24 (S5‑0) | S5‑1 (0.6.0) | (a) una base vacía, una base de la 0.5.0 sin `alembic_version` y la base de prueba de cada versión 0.6.0…0.9.0 (generada en su compuerta con el código de su etiqueta) llegan a `head` y sus presupuestos recargan con el total literal, la huella del informe y las filas por tabla de su ficha; lo mismo para `instalacion.db` desde la 0.8.0; (b) cada base del juego de respaldo pasa `PRAGMA integrity_check` y su huella está en la ficha; (c) con un fallo inyectado en una revisión, la huella SHA‑256 de cada base tras el intento es igual a la de antes; (d) una base con revisión desconocida o no adoptable no se modifica (huella igual) y el mensaje dice qué hacer; (e) una ruta UNC, absoluta o con `..` se rechaza sin crear archivo, y `estado_caso` no emite DDL; (f) restaurar un juego con `instalacion.db` lista los eventos de seguridad perdidos y deja pendiente la revisión del administrador |
| RF‑97 | **Instalador para Windows.** Un `Silice-<versión>.exe` (básico) y un `Silice-<versión>-completo.exe` (con el módulo de similitud) instalan sin internet ni permisos de administrador: Python autónomo, dependencias y código según el manifiesto; crean el acceso directo «Sílice» que arranca y abre el navegador y «Detener Sílice»; la actualización detiene Sílice, reemplaza el programa y migra con respaldo; la desinstalación borra el programa y **conserva los datos** | Esencial (básico); Deseable (completo) | UC‑24 | S5‑3 (1.0.0) | prueba de humo de §11.2: (a) instalación silenciosa en una ruta con espacios y acentos; (b) salud `200` ≤ 60 s; (c) solo `127.0.0.1` escuchando y nada en `0.0.0.0` ni en `::`; (d) nada escrito en la carpeta del programa (inventario igual antes y después); (e) actualización con un juego de respaldo y las dos bases en `head`; (f) desinstalación sin carpeta de programa y con la carpeta de datos intacta; (g) sin el módulo de similitud, la pantalla de similares lo dice con su nombre; (h) `{app}\codigo` contiene exactamente lo del manifiesto: ni `tests/fixtures/` completo ni otro `.streamlit/config.toml` que el oficial |
| RF‑98 | **Operación segura por defecto.** Arranque y parada con una sola instancia; red local **apagada**, activable solo desde el equipo servidor con elevación, escuchando en la **IP explícita** de la interfaz elegida (nunca `0.0.0.0`) con regla de cortafuegos limitada a esa IP, a la subred local y al perfil Privado; API **apagada**, en la misma dirección, con clave en **todas** sus rutas salvo `/salud`, `TrustedHostMiddleware` y filtro de redes privadas (defensa adicional; el control es la clave); las operaciones sensibles solo desde el propio equipo y el aviso «sin cifrar» en la pantalla de acceso para clientes remotos (§8.2); registro de errores rotativo **sin secretos**; **ninguna conexión saliente salvo el asistente en modo nube activado por el administrador** (excepción de RNF‑08) | Esencial | UC‑24 | S5‑2 (1.0.0) | pruebas de §12: configuración por defecto; ninguna configuración produce `0.0.0.0` en la orden de Streamlit ni de Uvicorn; con la API activa, `401` sin clave en cada ruta del esquema, `403` desde una IP pública simulada y `400` con un `Host` ajeno; una operación sensible pedida desde una IP remota se rechaza; un registro con secretos sembrados no contiene ninguno; prueba de humo **con el asistente apagado**: **0** conexiones salientes desde el arranque hasta la parada (cortafuegos de salida, muestreo de conexiones, proxy testigo y navegador sin interfaz, §11.2) |
| RF‑99 | **Versión y registro de cambios.** Una sola fuente de la versión (`pyproject.toml`); la API, la pantalla «Acerca de» y el instalador la leen de ahí; «Acerca de» muestra además las revisiones de los dos esquemas, la carpeta de datos y los módulos instalados; `CHANGELOG.md` con una sección por versión; una etiqueta anotada por versión | Esencial | UC‑24 | S5‑0, S5‑2, S5‑4 (1.0.0) | `scripts/meta_silice.py --version <x>` (RV‑17): versión de `pyproject` = la de la API = la del instalador; sección del `CHANGELOG` para la versión en curso con fecha; en un *push* de etiqueta, la etiqueta (`v` + SemVer) coincide con `pyproject` normalizado (PEP 440) o la CI falla |
| RF‑80 | Cuentas locales con roles *arma*, *revisa* y *administrador de la instalación* (uno o varios por cuenta) y la matriz de §5.1; contraseñas con Argon2; el primer administrador se crea solo con el **código de instalación** de un solo uso, de al menos 100 bits | Esencial | UC‑21 | S3‑1 | sin código o con código usado se rechaza; el código tiene 20 caracteres base32; ninguna contraseña aparece en la base, en el registro de accesos ni en los mensajes; cada página y cada acción de la matriz rechaza un rol que no le corresponde aunque se llegue por URL |
| RF‑81 | Sesión propia en Streamlit: expira por inactividad (30 min) y por antigüedad (12 h); ficha nueva al entrar y al cambiar la contraseña; todas las sesiones de una cuenta se cierran al restablecerla, desactivarla o cambiar sus roles; roles leídos de la base en cada ejecución; bloqueo tras 5 intentos fallidos seguidos durante 15 min, con el mismo contador y mensaje para usuarios inexistentes; freno global con espera progresiva; cierre de sesión; varios usuarios a la vez sin mezclar estado | Esencial | UC‑21 | S3‑1 | reloj inyectado: 29:59 sigue, 30:00 expira; 4 fallos no bloquean, el 5.º sí, con un login existente y con uno inexistente; cambiar los roles en la base cambia el menú en la ejecución siguiente; dos sesiones AppTest con usuarios distintos no comparten borrador ni caso; prueba de concurrencia de §13.4 |
| RF‑82 | El responsable de todo `RegistroCambio`, de todo eslabón y de **todo campo `responsable`** de las tablas de S1 y S2 (`importacion_indice`, `moneda_proyecto`, `clausula_reajuste`, `estudio_reajuste`, `linea_base_control`, `valuacion`, `anulacion_valuacion`, `costo_real`, `decision_recuperacion`) es el **usuario autenticado**, congelado como `Nombre <login>` en el momento del cambio; la caja «Responsable» desaparece de la hoja y de las pantallas de S1 y S2 | Esencial | UC‑15, UC‑21 | S3‑1 | guardar, restaurar, cotizar, convertir, decidir una recuperación, crear la primera versión, asegurar la instantánea, importar índices, registrar valuaciones, anulaciones y costos reales registran al usuario de la sesión; una prueba recorre los metadatos y lista **toda** columna `responsable`: cada una tiene su prueba, y una columna nueva sin prueba hace fallar la lista; ningún camino de `ui/` pasa `"sistema"`; desactivar una cuenta no cambia sus registros |
| RF‑83 | Registro encadenado: cada versión nueva, que nace en el embudo `guardar_presupuesto`, se sella **al confirmar la transacción que la crea** (evento `before_commit`, §6.2) y en esa misma transacción, con un eslabón SHA‑256 que encadena su contenido, sus `RegistroCambio`, sus anexos y el eslabón anterior (§6); el sellado es una invariante de **todo** `MOTIVOS_VERSION` (incluidos `conversion` de S1 y `recuperacion` de S2) y del motivo vacío (versión sin origen); las versiones anteriores se sellan una vez de forma **retroactiva** y declarada; el sistema verifica la cadena | Esencial | UC‑15, UC‑22 | S3‑2 | una prueba recorre la tupla `MOTIVOS_VERSION` y el motivo vacío, y crea una versión de cada uno; otra enumera a **todos** los llamadores del embudo (§1.2) y falla si aparece uno nuevo sin prueba; cambiar un byte de una partida, de un registro, de un anexo o de un eslabón en la base rompe la cadena **en esa versión** y lo dice; una versión posterior al génesis sin eslabón es un error de cadena; confirmar una versión sin usuario se rechaza; guardar y recargar no cambia ninguna huella |
| RF‑84 | Clave de firma de la empresa Ed25519 generada en el equipo, con la privada **cifrada con su propia contraseña** por `seguridad/secretos.py` (Argon2id → AES‑GCM, maestro §4.4); huella corta legible (§7.2); registro de claves públicas de otras empresas con la comprobación de su huella; retiro (se destruye la privada) y revocación; separación de dominio en todo lo que se firma | Esencial | UC‑21 | S3‑3 | la privada nunca aparece sin cifrar en disco ni en el paquete; contraseña de clave errónea da `InvalidTag` y un mensaje sin traza; una contraseña de la lista corta de comunes se rechaza; la huella es la misma en las dos instalaciones; al retirar, la privada deja de existir en la base; una clave revocada deja de verificar |
| RF‑85 | Exportar el paquete auditado (§8): documento canónico (con moneda del proyecto y `precio_origen`), informe, cadena, anexos (`espacio`, `reajuste`, `control`, `ia`), manifiesto con `paquete_id`, `destinatario` opcional y `huella_anexos`, y firma; **sin Excel**; el emisor guarda el SHA‑256 de cada paquete exportado; firmar solo desde el propio equipo | Esencial | UC‑22 | S3‑3 | el paquete exportado se verifica como «Verificado» en otra base con la clave registrada; sin clave se exporta «sin firma» y así se declara; la cadena rota impide exportar; el SHA‑256 del archivo descargado está en `evento_acceso`; una firma pedida desde una IP que no es de bucle local se rechaza |
| RF‑86 | Importar y verificar un paquete: límites leídos con tope (§8.4), integridad (huellas del manifiesto), autenticidad (firma de una empresa registrada y no revocada, con separación de dominio), cadena, posición respecto de paquetes ya recibidos y banner de versión; **siempre** se reaudita con las reglas propias | Esencial | UC‑23 | S3‑4 | cada caso de §13.3 da su estado declarado, con las fronteras exactas de §8.4; un paquete no verificado se audita igual; ninguna entrada del ZIP sale de su carpeta ni excede los límites; el banner dice la versión y la última recibida |
| RF‑87 | Vista de revisión: estado de verificación, reauditoría con los anexos (R11–R14 recomputadas, R12 a la fecha de emisión), **diferencia entre versiones** y su costo (desvío por cantidad y por precio) frente a la entrega anterior y frente a la base de precios del revisor, Excel regenerado desde `presupuesto.json`, dictamen atado al SHA‑256 del archivo y aviso cuando quien revisa es quien armó (maestro §4.1, P2) | Esencial | UC‑23 | S3‑4 | con el par de presupuestos de la memoria de diferencias (§13.1) la vista da los montos de la memoria; R11–R14 del paquete de prueba dan el conjunto exacto de su memoria; el dictamen queda con usuario, fecha, SHA‑256 del archivo, estado de verificación y `revisor_armo`; con un paquete de la empresa propia, un revisor que es el usuario emisor o el `usuario` de un eslabón ve el aviso y su dictamen queda con `revisor_armo` = sí; otro revisor de la misma empresa, o un paquete de una empresa ajena, no lo ve |
| RF‑88 | APU de otras herramientas: Excel con el formato UC‑05 (plantilla descargable) auditado en memoria desde la vista de revisión, y ruta `POST /v1/auditorias` con **clave de API** que recibe el documento canónico (§6.1) y devuelve el informe; cuerpo limitado por un middleware; `TrustedHostMiddleware` | Esencial | UC‑23, UC‑05 | S3‑4 | Excel con partidas del catálogo se audita sin el rechazo de `importacion.py:208`; sin clave o con clave revocada, 401 sin auditar; cuerpo de 20 MiB pasa y de 20 MiB + 1 B da 413 sin leerlo entero; con clave, el informe coincide con el de la vista |
| RF‑89 | Auditoría de planos: auditoría de archivo DXF, requisitos IDS del IFC con `ifctester`, R15 (coherencia geométrica, `shapely`, severidad por condición), R16 (contraste entre dos fuentes, con el costo de la diferencia) y evaluación por **errores sembrados** con el protocolo de §13.5 | Esencial | UC‑14 | S3‑5 | cada error del catálogo sembrado se detecta con la regla o el ítem de informe declarados; cada fila de R15 y R16 cumple sus fronteras (§11.3, §11.4); OF‑001 limpio da el conjunto exacto escrito en S3‑0; la tasa de detección y las falsas alarmas cumplen la meta del protocolo: 100 % de lo detectable y 0 falsas alarmas (ratificada por Eugenio el 2026‑10‑11, pregunta P8 del maestro §10.3) |
| RF‑100 | Anomalías en variaciones de precio: sobre la serie fechada de precios de un insumo (listas de la empresa de S1, RF‑67, y listas MaPreX, cada precio con su fecha), llevada a USD con la tasa de cada precio (RF‑65) y reducida a variaciones entre puntos consecutivos, el sistema marca las variaciones atípicas como **ADVERTENCIA** (`CODIGO_ATIPICO`), **nunca ERROR**, reutilizando el detector existente `ml.anomaly.precios_atipicos` (Isolation Forest, `SEMILLA` = 42, `UMBRAL_ATIPICO` = −0,05, se abstiene con menos de `MINIMO_OBSERVACIONES` = 8 variaciones) | Deseable | UC‑17, UC‑23 | S3‑6 (construido en Sílice 1.1.0, ruta sesión 1) | serie sembrada de 10 precios (9 variaciones) con **un** atípico sembrado → el conjunto exacto de hallazgos es ese único punto, con severidad ADVERTENCIA; serie de 10 precios **sin** atípico → conjunto vacío; serie de 8 precios (7 variaciones) → abstención (vacío); ningún hallazgo de RF‑100 es ERROR ni bloquea guardar, exportar o firmar; sin el extra `ml` no hay hallazgo ni traza |
| RF‑32 | El asistente recibe un pedido en lenguaje natural sobre el proyecto abierto y responde **solo con propuestas** sobre el borrador de la hoja, mediante las herramientas de §6 | Esencial | UC‑09 | S4.2 (Sílice 0.9.0) | con el proveedor guionado (§10.1), un pedido produce propuestas pendientes y **ningún cambio** en el borrador hasta que el usuario acepta |
| RF‑90 | Una interfaz común de proveedor (`ProveedorIA`, §5.3) con dos implementaciones, Claude (API de Anthropic, uso de herramientas) y un modelo local por Ollama; elección por instalación y por sesión; si el proveedor elegido no está disponible, se ofrece el otro sin cambiar de proveedor a mitad de una sesión | Esencial | UC‑09 | S4.2 (Sílice 0.9.0) | **(a)** la interfaz común y el adaptador de Claude pasan las pruebas de contrato sobre respuestas grabadas; **(b)** el adaptador local pasa las **mismas** pruebas de contrato y, sin conexión, se ofrece el local (9a). Si la prueba exploratoria de S4.0 (§8.6) declara el modo local «solo para pruebas» o el orden de caída (§11) lo retira, (b) se enmienda con ruling registrado; no se da por cumplido en silencio. **Enmienda 1.1.0:** (b) queda **diferido** por decisión de Eugenio (RS-8, 2026-10-18: modo local en pausa) |
| RF‑91 | Cada llamada del modelo se valida antes de tocar el borrador: esquema Pydantic estricto, validación semántica y construcción del modelo espacial (§7); todo dato numérico de entrada trae **cita literal** del pedido o **supuesto declarado**; no existe campo de precio, total ni cantidad derivada | Esencial | UC‑09 | S4.1 (Sílice 0.9.0) | cada causa de rechazo de §7.4 tiene su prueba con el caso frontera; un número sin cita no entra |
| RF‑92 | Las propuestas quedan pendientes, el usuario las acepta, edita o rechaza una por una, y las aceptadas entran al borrador con **origen «propuesta de IA»**; el borrador se audita siempre con R1–R7 y las reglas externas que la tabla del maestro asigna a la hoja (RV‑9); guardar exige fuente y responsable humano | Esencial | UC‑09, UC‑15 | S4.1, S4.3 (Sílice 0.9.0) | una propuesta rechazada deja el borrador igual (comparación exacta); una aceptada aparece con su origen en la hoja, en el Estado y en el Excel; la versión guardada lleva el `RegistroCambio` con la fuente de la sesión |
| RF‑93 | Registro de cada sesión del asistente (`ia_*`): pedido, turnos, llamadas con su resultado de validación, decisiones del usuario, proveedor, modelo que respondió, uso de tokens y costo estimado | Esencial | UC‑09 | S4.2 (Sílice 0.9.0) | una sesión guionada deja exactamente las filas esperadas, en orden; la clave de IA de la empresa nunca aparece (RNF‑18) |
| RF‑94 | Privacidad y costo: vista previa de lo que se enviará, minimización (§8.1), modo local sin envío fuera del equipo, clave de IA de cada empresa protegida (§8.3), defensas ante texto ajeno (§8.7) y **tope de costo por sesión** (§8.4) | Esencial | UC‑09 | S4.2, S4.3 (Sílice 0.9.0) | la instantánea de lo enviado para el borrador de prueba coincide con la lista blanca de §8.1; con el proveedor guionado y precios de prueba, la sesión se detiene (9f) en el turno exacto en que el costo acumulado alcanza el tope, calculado a mano, y conserva las propuestas válidas; RNF‑18 |
| RF‑95 | El experimento de §9: banco de tareas de referencia congelado, corrida reproducible con los dos proveedores y cálculo de las métricas, que genera `docs/resultados_asistente.md` | Esencial | — (tesis, OE‑H2) | S4.0, S4.4 (Sílice 0.9.0) | el script de métricas, con corridas de prueba hechas a mano, da las cifras calculadas a mano (oráculo independiente, §10.1). **Enmienda 1.1.0:** cumplido en parte (ver la enmienda 1.1.0) |

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
| UC‑13 | RF‑44, RF‑45, RF‑46, RF‑47, RF‑48, RF‑49, RF‑61 | 7 (sin mínimo declarado; UC nuevo, Sesión SF0) |
| UC‑14 | RF‑50, RF‑51 | 2 (sin mínimo declarado; UC nuevo, Sesión SF0) |
| UC‑15 | RF‑52, RF‑53, RF‑54, RF‑55, RF‑56, RF‑57, RF‑59, RF‑61, RF‑62 | 9 (sin mínimo declarado; UC nuevo, Sesión SF0) |
| UC‑16 | RF‑58 | 1 (sin mínimo declarado; UC nuevo, Sesión SF0) |
| UC‑17 | RF‑65, RF‑66, RF‑67, RF‑68, RF‑69 | S1 (Sílice 0.6.0; la meta cuenta) |
| UC‑18 | RF‑70, RF‑71 | S1 (Sílice 0.6.0; la meta cuenta) |
| UC‑19 | RF‑72, RF‑73, RF‑74, RF‑77 | S2 (Sílice 0.7.0; la meta cuenta) |
| UC‑20 | RF‑75, RF‑76, RF‑77, RF‑78, RF‑79 | S2 (Sílice 0.7.0; la meta cuenta) |
| UC‑21 | Iniciar sesión y administrar cuentas y claves | S3‑0 (declarado), S3‑1, S3‑3 |
| UC‑22 | Entregar el paquete auditado | S3‑0 (declarado), S3‑3 |
| UC‑23 | Revisar un paquete o un presupuesto externo | S3‑0 (declarado), S3‑4 |
| UC‑09 | RF‑32, RF‑90, RF‑91, RF‑92, RF‑93, RF‑94, RF‑95 | S4 (Sílice 0.9.0; la meta cuenta) |
| Transversales | RF‑60 (todos los UC); RF‑63 y RF‑64 (UC‑01); RF‑64, RF‑65, RF‑66 y RF‑68 (también UC‑15); RF‑62 (también UC‑05); RF‑56 (también UC‑02 y UC‑07) | — |
| **Total** | RF‑01 … RF‑31, RF‑33 … RF‑63 y, desde Sílice 0.6.0, RF‑64 … RF‑71 y RF‑96 y, desde Sílice 0.7.0, RF‑72 … RF‑79 (RF‑32 vacante — reservado a UC‑09; RF‑03 traza a dos UC; RF‑33 y RF‑34 trazan a UC‑10 y UC‑11; RF‑56, RF‑61 y RF‑62 trazan a más de un UC) | **62** hasta el sprint final; desde Sílice 0.6.0 los cuenta la meta |

### 3.3 Requisitos no funcionales (ISO/IEC 25010)

| Característica | RNF | Métrica | Meta |
|---|---|---|---|
| Adecuación funcional | RNF‑01 exactitud del presupuesto frente a la línea base corregida | desviación % | dentro de clase 3 AACE |
| Fiabilidad | RNF‑02 reproducibilidad: el mismo presupuesto se reconstruye a la fecha de su lista de precios | comparación exacta | 100 % |
| Eficiencia de desempeño | RNF‑03 tiempo de recálculo masivo tras cambiar la lista de precios, medido en el equipo de desarrollo con SQLite local y sin exportación | segundos para N partidas | < 5 s con N ≤ 100 partidas |
| Usabilidad | RNF‑04 el informe de auditoría se entiende sin formación previa | juicio de expertos (Likert) | ≥ 4/5 |
| Mantenibilidad | RNF‑05 agregar un dominio no modifica `core/` | `git diff --stat core/`, `test_arquitectura.py` | vacío / verde |
| Mantenibilidad | RNF‑06 cobertura de pruebas del núcleo | pytest‑cov | ≥ 80 % |
| Portabilidad | RNF‑07 instalación con `uv sync` en Windows y Linux. Desde la 1.0.0 el camino de usuario es el instalador de Windows (RF‑97); `uv sync` sigue siendo el camino de desarrollo y el de Linux. | pasos manuales | 0 |
| Seguridad | RNF‑08 ejecución local: el sistema funciona sin conexión a internet; sus únicas credenciales son las cuentas locales de la instalación (S3), que no dependen de ningún servicio externo; los datos residen en archivos SQLite del equipo servidor (la base de la instalación y las de los casos). | credenciales versionadas, 0; conexiones fuera del equipo durante la operación, 0, con dos excepciones declaradas: (1) en el camino de desarrollo, la descarga inicial del modelo de `sentence-transformers` (I2), que se cachea localmente (el instalador completo lo trae incluido y corre con `HF_HUB_OFFLINE=1`); (2) el asistente de IA en modo nube, apagado por defecto, que solo activa el administrador de la instalación al registrar la clave de IA de la empresa y que envía al proveedor solo lo de la lista blanca de S4. La excepción de three.js se retiró: primero se sirvió desde el propio sistema y, desde el 2026-10-19, el Visor 3D que lo usaba ya no existe (retirado 2026-10-19, decisión de Eugenio, pendiente de ratificar por el tutor). | 0 y 0, con dos excepciones declaradas |
| Compatibilidad | RNF‑09 entrada IFC 4 de cualquier modelador | archivos de ≥ 2 herramientas (p. ej. Revit y Bonsai) | cantidades extraídas iguales al cálculo manual en ambos; la compuerta G1 (I3.1) se cruzó con salvedad sobre un modelo generado programáticamente (sección 2.5); faltan los exports de dos modeladores, y la alternativa declarada es la entrada tabular |
| Usabilidad | RNF‑10 capacidad de aprendizaje de la interfaz: una persona que nunca vio la aplicación llega sola del Inicio a un presupuesto en Excel con su hoja de auditoría | caso con persona CP‑07 ([guion_prueba_arenia.md](guion_prueba_arenia.md)) y bloque B del anexo A de [dossier_g0.md](dossier_g0.md) | en cada uno de los dos escenarios de CP‑07 (CP‑07 pasa solo si pasan ambos): sin ayuda, ≤ 20 min, bloque B ≥ 4,0 y ningún ítem < 3 |
| Eficiencia de desempeño | RNF‑11 en `ui.hoja`, sin Streamlit, desde aplicar una edición hasta tener presupuesto, informe y punto de equilibrio (sin persistir) para un proyecto de 500 puntos | mediana de cinco corridas tras una de calentamiento, con `scripts/medir_rnf11.py` (se crea en SF3) y un generador determinista versionado (`scripts/generar_hoja_prueba.py`, ya en SF0) | ≤ 2 s. El veredicto se toma en el equipo de desarrollo, como RNF‑03; la CI ejecuta el script en Linux y Windows y **registra** la cifra sin romper la corrida; todo se anota en plan_pruebas §10 |
| Seguridad | RNF‑12 ningún texto exportado se interpreta como fórmula (prefijos `=`, `+`, `-`, `@`, tabulador, retorno de carro) y un número negativo sigue siendo número; ningún archivo subido sale de su carpeta (`..\`, `../`, ruta absoluta, nombres reservados de Windows); un DXF o IFC de más de 20 MB, malformado o con más entidades o elementos que el tope (`MAX_ENTIDADES_DXF`, `MAX_ELEMENTOS_IFC`) se rechaza con un mensaje | pruebas por caso | 0 casos que se evalúen como fórmula o escapen de su carpeta; 100 % de los rechazos con mensaje y sin *traceback* |
| Usabilidad | RNF‑13 capacidad de uso de la hoja: en las condiciones de CP‑07, con el **mismo número y perfil** de participantes que CP‑07 pero **personas distintas**, cada caso de CP‑08 a CP‑11 se completa sin ayuda | guion de pruebas con personas, en la fase Med; consigna, paradas y criterio fijados antes de medir | ≤ 15 min por todos los participantes, bloque B ≥ 4,0 y ningún ítem < 3; veredicto por caso. El costo en participantes se suma al plan de Med |
| Fiabilidad | RNF‑14 reproducible y sin conexión: importar, convertir, auditar con R11/R12 y reajustar no hacen ninguna llamada de red; el mismo estudio de reajuste, con las mismas importaciones citadas, da el mismo resultado aunque después se importe una revisión de los índices | suite bajo la guardia de red única de `tests/conftest.py` (solo 127.0.0.1 y ::1) y recálculo del estudio tras importar una revisión | cero intentos de conexión a otro destino, guardia activa verificada por la meta; diferencia 0 exacta |
| Eficiencia de desempeño | RNF‑15 en `ui.control`, sin Streamlit, desde registrar una valuación hasta tener informe de control, indicadores, alertas y reproyección, y desde pedir las opciones hasta tener las cuatro, para una obra de 500 partidas, 52 períodos semanales y 26 valuaciones | mediana de cinco corridas tras una de calentamiento, con `scripts/medir_rnf15.py` y un generador determinista versionado (`scripts/generar_obra_control.py`) | ≤ 2 s en cada uno de los dos trabajos. El veredicto se toma en el equipo de desarrollo, como RNF‑03 y RNF‑11; la CI ejecuta el script en Linux y Windows y **registra** la cifra sin romper la corrida; la meta comprueba que el script corrió y dejó su cifra: sin cifra es FALLA, no OK (PRU‑H21) |
| Seguridad (confidencialidad) | RNF‑18 **(a)** En modo local, cero conexiones fuera del equipo: el anfitrión de Ollama debe ser de bucle local, comprobado por la **IP resuelta** (`127.0.0.0/8` o `::1`), no por el nombre; si no lo es, se trata como modo nube y se avisa. Se exige una **versión mínima** de Ollama, fijada en S4.0 (no tiene autenticación y ha tenido vulnerabilidades, SEG‑18). **(b)** En modo nube, solo viaja lo de la lista blanca de §8.1. **(c)** La clave de IA de la empresa nunca aparece en la base, en el registro `ia_*`, en los registros de la aplicación, en `st.session_state`, en el Excel ni en el paquete (incluido `anexos/ia.json`), y la pantalla nunca la muestra completa. **(d)** Ninguna prueba de la CI abre la red | pruebas por caso (§10.1): la guardia única de red de `tests/conftest.py` (RV‑17); búsqueda de la clave de prueba en todos esos destinos tras una sesión; instantánea de lo enviado; anfitrión cuyo nombre resuelve a una IP no local → tratado como nube | cero apariciones de la clave de IA; cero conexiones en la CI |
| Portabilidad | RNF‑19 Instalabilidad: artefactos comprimidos (los `.exe`) del instalador básico ≤ 150 MB y del completo ≤ 650 MB (1 MB = 10⁶ bytes); instalado, el básico ≤ 900 MB. Se instala sin internet y sin administrador en Windows 10 22H2 y 11 x64, en una ruta con espacios y caracteres no ASCII. Del acceso directo a la salud 200: ≤ 60 s en la CI y ≤ 20 s en el equipo de desarrollo. Actualizar conserva el 100 % de los datos de las dos bases | tamaño de los artefactos de la CI (falla si se pasa); prueba de humo; arranque medido (mediana de cinco, con fecha y los cinco valores en plan_pruebas §10); instalación en una cuenta estándar, a mano | cumplir los tres límites |
| Mantenibilidad | RNF‑20 cero deriva de esquema en cada destino: una base llevada a `head` por las migraciones es igual a la creada con `create_all` de sus `METADATAS`, la autogeneración de Alembic contra ella no propone cambios, toda `MetaData` con tablas está en la lista de su destino y cada revisión baja y vuelve a subir | `tests/integration/test_migraciones.py` en Linux y Windows en cada PR | deriva 0 en los dos destinos, desde la 0.6.0 |
| Seguridad | RNF‑16 Contraseñas de cuenta solo como Argon2 (parámetros por defecto de `argon2-cffi`, con semáforo); clave privada solo cifrada con `seguridad/secretos.py`; ningún secreto en registros, mensajes ni paquete; el 100 % de las alteraciones de §13.3 detectadas; ninguna página, acción ni ruta nueva accesible sin sesión, rol o clave; operaciones sensibles solo desde el propio equipo; límites del ZIP, del JSON y de la API (§8.4); texto ajeno siempre por `texto_seguro()`; mensajes sin traza | pruebas de §13.3 y §13.4; revisión por el encargo de seguridad con la tabla de amenazas (§12) | todas las pruebas de §13.3 y §13.4 del spec S3 en verde |
| Usabilidad | RNF‑17 En las condiciones de CP‑07, con personas que no son el autor: (a) quien revisa abre un paquete y dice su estado de verificación y quién lo emitió, sin ayuda, en ≤ 5 min; (b) encuentra las diferencias sembradas de CP‑R1 en ≤ 20 min; (c) quien administra registra la clave de otra empresa comprobando su huella por teléfono en ≤ 10 min; bloque B ≥ 4,0, ningún ítem < 3 | guion en Med, con consigna, paradas y criterio fijados antes de medir. El **indicador del administrador** (horizonte §6.1) no se reduce a RNF‑17: se mide con su propio protocolo de dos condiciones (§13.5 a) | bloque B ≥ 4,0 y ningún ítem < 3, en los tiempos de la medición |

### 3.4 Reglas de negocio
Fórmula de cálculo: [NORMAS.md §4](../NORMAS.md#4-especificación-del-cálculo-y-línea-base).
Reglas de verificación R1–R7: [NORMAS.md §7](../NORMAS.md#7-siete-reglas-de-verificación-coreverification-sesión-i4).
Criterios de degradación del módulo predictivo: [NORMAS.md §8.1](../NORMAS.md#8-compuertas-y-criterios-de-degradación).

#### Reglas nuevas R13 y R14 (Sílice 0.7.0, S2)

En `core/verification/valuaciones.py`; implementan `ReglaVerificacion` (contrato sin cambios), se construyen con
la **instantánea de control** (línea base, calendario, plan de la línea base, valuaciones no anuladas hasta el
corte: las mismas que cuentan para el valor ganado) y entran por
`reglas=` como R8–R12; **no** entran en `REGLAS` (el 7 de 7 y las huellas de RNF‑04 no se mueven). Sus hallazgos
citan en `origen_ids` la clave de la línea (`valuacion:<número>:<código>`) **y** el `origen_id` del ítem de la
partida, para que el informe atribuya la partida (C5.1).

**Contextos** (tabla única de reglas externas del maestro, RV‑9). R13–R14, con la instantánea de control como
entrada, corren: en la hoja y en «Control de obra» (corte = el que el usuario elige, por defecto la fecha *hasta*
de la última valuación); en la reauditoría del paquete de S3 §9, desde `anexos/control.json` (corte = el
declarado en el anexo); en `POST /v1/auditorias` y en el experimento de S4, según lo que fije esa tabla. Toda
reevaluación es **en memoria** y nunca reescribe filas guardadas (no cambia `huella_contenido`).

| Regla | Condición | Severidad | Impacto |
|---|---|---|---|
| **R13 Valuación dentro del presupuesto** | (a) acumulado no anulado de una partida > cantidad de la línea base | ERROR | exceso × unitario base |
| | (b) partida valuada que la línea base no tiene | ERROR | sin unitario: no se cuantifica y se declara |
| | (c) partida presupuestada que el plan de la línea base no programa en ningún período | ADVERTENCIA | — |
| **R14 Fuente y fechas de la valuación** | (a) falta número, inspector o fecha | ERROR | — |
| | (b) *desde* > *hasta*; o fecha de la valuación anterior a *hasta*; o *hasta* posterior al corte; o *desde* anterior al inicio del calendario | ERROR | — |
| | (c) período solapado con otra valuación no anulada; o número repetido | ERROR | — |
| | (d) fecha de medición de una línea fuera de [*desde*, *hasta*] | ERROR | — |
| | (e) números no consecutivos cuando siguen el patrón prefijo + número (`V-01`, `V-03`) | ADVERTENCIA | — |
| | (f) hueco de días hábiles entre dos valuaciones consecutivas | INFO | — |

R13 compara con la **línea base vigente al corte**: una variación registrada (versión nueva con la cantidad y
declarada línea base) es lo que la hace pasar. La igualdad exacta pasa (`≤`); no hay tolerancia de medición
(§11, pregunta 6). R13 sirve igual a un presupuesto de cualquier dominio: se prueba también sobre SIS‑001
(ARQ‑H3). En R14(f), un hueco es al menos un día hábil sin cubrir entre el *hasta* de una valuación y el *desde*
de la siguiente: de viernes a lunes no hay hueco.

---

## 4. Matriz de trazabilidad

La matriz traza cada caso de uso a sus requisitos, al incremento que los implementó y al indicador de la tesis. **Las pruebas que demuestran cada
RF, con su estado, están solo en [plan_pruebas.md §8](plan_pruebas.md#8-especificación-de-casos-trazabilidad-rf--prueba); la prueba o el caso
manual de cada paso y de cada flujo alternativo de los quince casos de uso, en su §8.1** (INV‑032, INV‑033). La columna «Incremento» registra solo
los incrementos del desarrollo, con el mismo criterio que la de §3.2; las fases del cierre (C1 a C5) que corrigieron un caso de uso no se anotan
aquí: cada corrección está en su fila del [inventario del cierre](auditoria/2026-09-inventario.md) y en la fila del paso en plan_pruebas §8.1.

| UC | RF | Incremento | Indicador de la tesis |
|---|---|---|---|
| UC‑01 | RF‑01, RF‑03, RF‑04, RF‑05, RF‑06, RF‑07, RF‑08, RF‑63, RF‑64 | I0.1, I0.3, I0.4, I0.5, I3.1, SF4, S1‑1 | 2, 3 |
| UC‑01 (transversal) | RF‑09 | I0.1, I5 | 4 |
| UC‑02 | RF‑10, RF‑11, RF‑12, RF‑13, RF‑14 | I0.4, I1 | 3 |
| UC‑03 | RF‑15, RF‑16, RF‑17 | I2 | 3 |
| UC‑04 | RF‑03, RF‑18, RF‑19, RF‑20 | I0.1, I3.2 | 2 |
| UC‑05 | RF‑02, RF‑21, RF‑22, RF‑23, RF‑24 | I4 | 1 |
| UC‑06 | RF‑25, RF‑26, RF‑27 | I0.1, I6.1, I6.2 | 2 |
| UC‑07 | RF‑28, RF‑29 | I6.1, I6.3 | 5 |
| UC‑08 | RF‑30, RF‑31 | cierre UC‑08 (2026‑08‑31) | 2 (apoyo) |
| UC‑10 | RF‑33, RF‑34, RF‑35 | P0.1 (declarado), P1–P4 ([PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)) | prototipo de entrega AREN.IA (hoy Sílice), fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis) |
| UC‑11 | RF‑33, RF‑34 | P0.1 (declarado), P1.2, P2.2 | prototipo de entrega AREN.IA (hoy Sílice), fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis) |
| UC‑12 | RF‑36, RF‑37, RF‑38, RF‑39, RF‑40, RF‑41, RF‑42, RF‑43 | U0.1 (declarado), U1 ([PLAN_UI.md](../PLAN_UI.md)) | fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis); aporta la medición de usabilidad de [calidad_iso25010.md §4](calidad_iso25010.md) |
| UC‑13 | RF‑44, RF‑45, RF‑46, RF‑47, RF‑48, RF‑49, RF‑61 | SF0 (declarado), SF1–SF2 ([PLAN_SF.md](../PLAN_SF.md)) | prototipo de entrega AREN.IA (hoy Sílice), fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis); la ausencia de cambios en `core/` al agregar datos y electricidad es evidencia del indicador 4 |
| UC‑14 | RF‑50, RF‑51 | SF0 (declarado), SF5 | prototipo de entrega AREN.IA (hoy Sílice), fuera de los cinco indicadores |
| UC‑15 | RF‑52, RF‑53, RF‑54, RF‑55, RF‑56, RF‑57, RF‑59, RF‑61, RF‑62, RF‑64, RF‑65, RF‑66, RF‑68, RF‑141 | SF0 (declarado), SF1, SF3, S1‑1, S1‑3, ruta S1 (1.1.0) | prototipo de entrega AREN.IA (hoy Sílice), fuera de los cinco indicadores |
| UC‑16 | RF‑58 | SF0 (declarado), SF3 | prototipo de entrega AREN.IA (hoy Sílice), fuera de los cinco indicadores |
| UC‑17 | RF‑65, RF‑66, RF‑67, RF‑68, RF‑69 | S1‑1 a S1‑3 (Sílice 0.6.0) | Sílice 0.6.0, fuera de los cinco indicadores |
| UC‑18 | RF‑70, RF‑71 | S1‑4 (Sílice 0.6.0) | Sílice 0.6.0, fuera de los cinco indicadores |
| UC‑19 | RF‑72, RF‑73, RF‑74, RF‑77 | S2‑1, S2‑2 (Sílice 0.7.0) | Sílice 0.7.0, fuera de los cinco indicadores |
| UC‑20 | RF‑75, RF‑76, RF‑77, RF‑78, RF‑79 | S2‑2, S2‑3 (Sílice 0.7.0) | Sílice 0.7.0, fuera de los cinco indicadores |
| UC‑09 | RF‑32, RF‑90, RF‑91, RF‑92, RF‑93, RF‑94, RF‑95 | S4.0 a S4.4 (Sílice 0.9.0) | Sílice 0.9.0, OE‑H2 (experimento del asistente), fuera de los cinco indicadores |
| Transversal | RF‑60 | SF4 | prototipo de entrega AREN.IA (hoy Sílice), fuera de los cinco indicadores |
| UC‑21 | RF‑80, RF‑81, RF‑82, RF‑84 | S3‑0 (declarado), S3‑1, S3‑3 | fuera de los cinco indicadores (seguridad de la entrega, S3) |
| UC‑22 | RF‑83, RF‑84, RF‑85 | S3‑0 (declarado), S3‑2, S3‑3 | fuera de los cinco indicadores (seguridad de la entrega, S3) |
| UC‑23 | RF‑86, RF‑87, RF‑88, RF‑89, RF‑100, RF‑141 | S3‑0 (declarado), S3‑4, S3‑5, S3‑6, ruta S1 (1.1.0) | indicador del administrador (horizonte §6.1) |
| UC‑26 | RF‑111, RF‑112, RF‑113, RF‑114, RF‑115, RF‑116, RF‑117, RF‑118 | ruta S2 (Sílice 1.2.0) | 1 (errores detectados, ahora ubicados sobre la hoja) |
| UC‑28 | RF‑127, RF‑128, RF‑129, RF‑135, RF‑136 | Sesión 4 de la ruta (Sílice 1.4.0) | fuera de los cinco indicadores (gestor de producción) |
| UC‑29 | RF‑130, RF‑131, RF‑132, RF‑133, RF‑134, RNF‑25 | Sesión 4 de la ruta (Sílice 1.4.0) | fuera de los cinco indicadores (gestor de producción) |
| UC‑30 | RF‑142, RF‑143, RF‑144, RF‑145, RF‑146, RNF‑28 | Sesión 4 de la ruta (historial; Sílice 1.2.0) | indicador 1 (errores detectados), como UC‑25 |

Correspondencia RNF → verificación: RNF‑01 y RNF‑02 se comprueban en UC‑01 y UC‑02 (RF‑06, RF‑14);
RNF‑03 en UC‑02 (RF‑11), con `scripts/medir_rnf03.py`; RNF‑04 con el juicio de expertos sobre el
informe de UC‑05, en la fase Med de [PLAN_CIERRE.md](../PLAN_CIERRE.md); RNF‑05 con RF‑09; RNF‑06 y
RNF‑07 en la integración continua; RNF‑08 por inspección del repositorio y de las dependencias;
RNF‑09 en la compuerta G1 (RF‑04); RNF‑10 con el caso con persona CP‑07, en la compuerta GU1b
(fase Med) de [PLAN_UI.md](../PLAN_UI.md); RNF‑11 en UC‑15 (RF‑52), con `scripts/medir_rnf11.py`
(SF3); RNF‑12 en UC‑14 y UC‑15 (RF‑50, RF‑51 y RF‑59), por pruebas por caso; RNF‑13 en UC‑13 a
UC‑16, con los casos con personas CP‑08 a CP‑11 de la fase Med; RNF‑14 en UC‑17 y UC‑18 (RF‑69, RF‑71), con la guardia de red única de la suite; RNF‑16 en UC‑21 a UC‑23 (RF‑80 a RF‑89), con las pruebas de seguridad de S3 (§13.3 y §13.4 del spec) y la revisión del encargo de seguridad; RNF‑17 en UC‑23, con los casos con personas CP‑R1 y CP‑R2 de la fase Med; RNF‑18 en UC‑09 (RF‑94), con las pruebas por caso de S4 y la misma guardia. RNF‑04 y RNF‑10 son requisitos
distintos, con mediciones distintas; RNF‑22 y RNF‑23 en UC‑26 (RF‑112 a RF‑118), con el trabajo `interfaz` de la CI y la verificación manual en el navegador (plan_pruebas §9). El resultado de cada verificación está en [plan_pruebas.md §9](plan_pruebas.md#9-trazabilidad-rnf--verificación).

La columna "Indicador" enlaza con [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis) y
con la matriz de [docs/tesis/esqueleto_tesis.md](tesis/esqueleto_tesis.md).

---

## Enmienda Sílice 1.5 (2026-10-13): libros de presupuesto de la empresa

Aprobada por Eugenio el 2026-10-13 ([spec 1.5](especificaciones/2026-10-13-silice-1.5-fusion-design.md),
[plan](../PLAN_SILICE_150.md), [bitácora](bitacora/2026-10-13-silice-150.md)). Enmienda **RF‑88/UC‑05**: además
del formato neutro, Sílice lee el libro de la empresa tal como es.

#### UC‑25 — Auditar y devolver el libro de presupuesto de la empresa

- **Actor principal:** quien arma o quien revisa (acción `LEER_PROYECTO`). **Secundario:** el administrador que
  importó las tasas del BCV y la lista de precios de la empresa.
- **Precondiciones:** un libro `.xlsx` de la empresa con la plantilla de su perfil (`adapters/hoja_empresa/perfiles/`);
  opcionalmente el PDF que se entregó y una versión anterior del libro.
- **Flujo principal**
  1. El usuario sube el libro en «Libro de la empresa» (o lo envía a `POST /v1/libros/auditoria`).
  2. Sílice comprueba el archivo (tamaño, ZIP, macros, celdas) y lo lee por rótulos y nombres definidos.
  3. Recalcula cada APU con el motor del núcleo, sin cambiarlo, y compara el P.U. con el escrito (F1).
  4. Aplica las reglas del libro L1‑L9, las del núcleo R1‑R7, y L10 o L11 si hay PDF.
  5. Muestra el resumen (total del libro frente al de Sílice), los hallazgos sobre la vista calcada, las alertas de
     precio en USD y Bs y la trazabilidad.
  6. El usuario descarga el libro devuelto: mismo aspecto, APU de forma uniforme, valores de Sílice, y las hojas
     AUDITORÍA, TRAZABILIDAD y ALERTAS USD‑Bs.
  7. Sílice guarda el resumen y los hallazgos de la auditoría en el historial de la instalación (UC‑30, RF‑142); el libro no.
- **Flujos alternativos**
  - *2a. Archivo rechazado* (macros, extensión, tamaño, combinadas o dimensiones desmedidas): mensaje claro; no se
    lee nada.
  - *2b. Libro que no se puede interpretar* (sin PRESUPUESTO, FCAS menor que 1): mensaje claro.
  - *1a. Solo un PDF simple* (sin Excel): Sílice aplica L10 y muestra los hallazgos, sin devolución; la revisión también queda en el historial, con el tipo `pdf`.
  - *5a. La instalación no tiene la tasa del BCV de la fecha:* las alertas en Bs dicen «no contrastable».
  - *7a. No se pudo guardar el historial:* el informe se muestra igual, con el aviso «No se pudo guardar el historial» (RF‑144).
- **Postcondiciones:** el libro y el PDF no se guardan, ni en la base ni en disco (F‑D9, RNF‑28); el resumen y los
  hallazgos de la auditoría sí quedan en el historial de la instalación (enmienda del historial, RF‑142 a RF‑144);
  el libro devuelto lleva el SHA‑256 del recibido.

| RF | Requisito | Fuente |
|---|---|---|
| RF‑101 | Leer el libro de la empresa por rótulos y nombres definidos, con la celda de origen de todo dato | F‑D3, F‑D6 |
| RF‑102 | Rechazar archivos peligrosos o desmedidos antes de leerlos | F‑D10 |
| RF‑103 | Recalcular cada APU con el motor del núcleo sin cambiarlo e informar F1 | F‑D1, §3 |
| RF‑104 | Reglas del libro L1‑L9 | §3 |
| RF‑105 | Reglas de PDF: L10 (PDF simple) y L11 (libro frente al PDF entregado) | §3 |
| RF‑106 | Alertas de precio en USD y Bs, con tasa BCV de la instalación y umbral configurable | §4, F‑D8 |
| RF‑107 | Libro calcado: mismo aspecto, APU uniformes, nombres definidos, sin `INDIRECT` ni `#REF!`, valores de Sílice | F‑D4, F‑D5 |
| RF‑108 | Hojas AUDITORÍA (hallazgos, reglas evaluadas y no evaluadas, cambios del calcado), TRAZABILIDAD y ALERTAS | §1, F‑D7 |
| RF‑109 | Página «Libro de la empresa» y rutas `/v1/libros` (auditoría, devolución, PDF) con clave de API | §5 |
| RF‑110 | Ningún libro real-confidencial se versiona; anonimizador para derivar casos | V‑D3, NORMAS §1 |

| RNF | Requisito |
|---|---|
| RNF‑21 | Límites de recursos al leer libros y PDF ajenos: tamaño, entradas, celdas combinadas, dimensión, presupuesto de celdas y de tiempo del evaluador, páginas del PDF (revisión de seguridad V5) |

Trazabilidad: UC‑25 → RF‑101 … RF‑110, RNF‑21 → Sílice 1.5 (sesiones V1‑V5) → indicadores 1 (errores
detectados) y del administrador (horizonte §6.1). Pruebas: en la auditoría final (regla del 2026-10-12, **derogada el
2026-10-18**: ver la enmienda 1.1.0 abajo); la aceptación local es `scripts/fusion_verificar.py`.

## Enmienda Sílice 1.1.0 (2026-10-18): ruta por sesiones, sesión 1

Origen: [ruta por sesiones](planes/RUTA_SESIONES.md) (decisiones RS-x de Eugenio) y
[plan de la sesión 1](planes/PLAN_SESION_1_ASISTENTE.md).

- **Pruebas obligatorias (RS-2).** Queda derogada la regla del 2026-10-12 («pruebas en la auditoría final»):
  todo trabajo nuevo se construye con TDD, `pytest -W error` y cero omitidas.
- **RF-100** se construye en esta versión (`ml/anomaly/series.py`, `ui/atipicos.py`, pestaña Precios de la hoja y
  lista de la empresa), con el oráculo a mano `tests/fixtures/memorias/atipicos_s3.md`.
- **RF-90 (b), modo local con Ollama: diferido (RS-8).** Eugenio lo pone en pausa: el código existente no se retira,
  no recibe trabajo nuevo y su criterio (b) no se da por cumplido.
- **RF-95, experimento: cumplido en parte.** Hechos: el banco y el protocolo congelados y la medición controlada del
  auditor (`docs/resultados_asistente_controlado.json`: E1 0/24, E2 24/24, E3 0/24, E4 24/24, E5 0/24, E6 0/24,
  E7 24/24, E8 2/2), más las pruebas del comparador, las métricas, las mutaciones, la corrida y el congelado.
  Pendiente: la corrida real (`evaluar_asistente.py corrida --conjunto evaluacion`), **en pausa por RS-10** (Eugenio no
  autoriza el gasto por ahora); con RS-8, correrla solo con Claude es un apartamiento del protocolo, a ratificar.
- **E3 y E5 (RS-9, opción A de Eugenio).** La hipótesis previa del protocolo los daba por detectables (E3 por R9 y
  R10, E5 por R10) y la medición controlada da 0/24 en ambos. El diagnóstico descarta un defecto de la medición: E3
  mueve un punto 0,05 m **dentro** de su ambiente y E5 quita la fuente o el circuito de un punto, y ninguna regla
  exige ni puede ver eso. El protocolo **no se modifica**; el resultado se informa como **hipótesis previa
  falsada** y límite del método, junto a E1 y E6: el auditor verifica la coherencia interna del espacio y sus
  límites normativos, no que la posición, la fuente o el circuito de un punto sean los que el cliente pidió.
- **RF-141 (nuevo, RS-11), regla R17 «Conexión de cada punto».**

  | RF | Requisito | Prioridad | UC | Incremento | Criterio de aceptación |
  |---|---|---|---|---|---|
  | RF‑141 | Todo punto que según su especialidad exige fuente (agua fría, drenaje, datos) o circuito (tomacorriente, iluminación) y no la tiene da un hallazgo **ADVERTENCIA** (`R17`, nunca ERROR) que nombra el punto y lo que le falta, en la hoja, al guardar, en el resultado hipotético del asistente y en la reauditoría; el usuario decide si corrige | Esencial | UC‑15, UC‑23 | Sílice 1.1.0 (ruta, sesión 1) | casos a mano con el conjunto exacto de hallazgos (`tests/unit/test_espacio_conexion.py`); sobre el banco de evaluación del experimento, R17 detecta los 24/24 mutantes E5 y da 0 avisos en las 12 referencias (`tests/unit/test_experimento_r17.py`); `congelado.verificar()` sigue en `[]` (`tests/unit/test_experimento_congelado_vigente.py`; el experimento no mide R17) |

- **Numeración reservada para la ruta** (para que las sesiones en paralelo no choquen): sesión 2 UC-26, RF-111 a
  RF-118, RNF-22 y RNF-23; sesión 3 UC-27, RF-119 a RF-126, RNF-24; sesión 4 UC-28 y UC-29, RF-127 a RF-136, RNF-25;
  sesión 5 RF-137 a RF-140, RNF-26 y RNF-27; la sesión 1 usa RF-141; el historial de auditorías de la sesión 4 toma UC-30, RF-142 a RF-146 y RNF-28; la migración de Streamlit (plan 2b) toma RF-147 a RF-155 (ruling T1, 2026-10-19: el historial conserva RF-142 a RF-146).

## Enmienda Sílice 1.2.0 (2026-10-18): interfaz nueva y visor de solo lectura

Ruta por sesiones, sesión 2 ([RUTA_SESIONES.md](planes/RUTA_SESIONES.md) §5; decisiones RS‑1 a RS‑7 de Eugenio y
rulings RT‑1 a RT‑9), [plan de la sesión](planes/PLAN_SESION_2_VISUAL.md) (rulings RS2‑1 a RS2‑15). Criterio de
diseño: IBM Carbon, SAP Fiori e IBCS (RS‑6), registrado en `frontend-desktop/PRODUCT.md` y `DESIGN.md`. La interfaz
Streamlit sigue siendo la principal (RT‑4). **Esta enmienda modifica dos requisitos anteriores:** RF‑98 (la API exige
clave en toda ruta salvo `/salud`; desde la 1.2.0 tampoco la llevan `/v1/sesion`, que se protege con la contraseña,
el freno y el bloqueo de UC‑21, ni `/app`, que es estático y sin secretos) y RF‑109 (las rutas `/v1/libros` aceptan
la clave de API **o** la sesión del navegador con un rol que arma o revisa; con la cabecera `X-Silice-Clave` se
comportan como en la 1.5). Todo lo demás se conserva.

#### UC‑26 — Auditar un libro en el visor

- **Actor principal:** el ingeniero de costos que audita (rol arma o revisa; acción `LEER_PROYECTO`).
- **Precondiciones:** la API de la instalación está encendida (`[api] activa = true`) y la persona tiene cuenta;
  un libro `.xlsx` de la empresa (la plantilla de UC‑25).
- **Flujo principal**
  1. La persona abre `/app/` en el navegador de su PC o de otra de la red local y entra con su cuenta.
  2. Suelta el libro y la fecha de devolución (hoy, por omisión).
  3. Sílice responde la réplica visual del libro (`POST /v1/libros/replica`) y su auditoría
     (`POST /v1/libros/auditoria`, UC‑25).
  4. La hoja se ve como en Excel (hojas, anchos, altos, combinadas, ocultas, formatos), sin poder editarse, con un
     halo de severidad e ícono sobre la celda de cada hallazgo y la franja de indicadores (libro frente a Sílice).
  5. Al tocar un hallazgo de la lista, la hoja va a su celda; al tocar una celda marcada, la lista resalta su hallazgo.
- **Flujos alternativos**
  - *1a. Credenciales malas o cuenta bloqueada:* 401 o 423 con el mensaje de UC‑21, sin sesión.
  - *1b. La cuenta debe cambiar su contraseña:* 403 sin cookie; se le indica hacerlo en la interfaz clásica.
  - *1c. Freno global de intentos fallidos (RS2‑11):* 429 con `Retry-After`; la pantalla dice cuántos segundos esperar.
    El intento frenado no prueba la contraseña ni suma fallo a la cuenta.
  - *2a. Archivo rechazado o libro no interpretable:* el mensaje de UC‑25 (2a, 2b), sin réplica. La pantalla no
    envía un archivo que no sea `.xlsx`.
  - *4a. Un hallazgo sin celda ubicable* (la celda no es una referencia A1, su hoja no existe en el libro o está
    oculta): aparece en la lista, en el grupo «Sin celda en el libro».
  - *4b. Un hallazgo en una fila o columna oculta:* queda en la lista y no se dibuja halo, porque la celda no se ve.
  - *Sesión vencida* (30 min de inactividad o 12 h): ante el primer 401 la pantalla vuelve a la entrada con el aviso
    «Su sesión venció»; el libro abierto se conserva en memoria y reaparece al volver a entrar con la misma cuenta
    (con otra cuenta se descarta).
- **Postcondiciones:** el libro no se guarda ni se modifica y la réplica no escribe nada (F‑D9). La auditoría deja
  su resumen y sus hallazgos en el historial (UC‑25, UC‑30). La base de la instalación guarda además la ficha de
  sesión y el registro de accesos (UC‑21).

| RF | Requisito | Prioridad | UC | Incremento | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑111 | Réplica visual del libro (`POST /v1/libros/replica`): hojas en orden y visibilidad, anchos, altos, combinadas, filas y columnas ocultas, paneles fijos y, por celda con valor o estilo propio, el valor guardado como texto decimal exacto (campo `mostrado`), la fórmula, el código de formato de número y el estilo, con coordenadas de Excel (base 1). Las celdas cubiertas por una combinada no se listan salvo que traigan valor o borde propio (RS2‑10). Un libro de más de 200 000 celdas se rechaza con 422 | Esencial | UC‑26 | Sílice 1.2.0 (ruta, sesión 2) | El libro del oráculo (`tests/fixtures/replica/`, escrito a mano) reproduce su tabla celda por celda en Python (`test_replica_oraculo.py`), en la API (`test_api_replica_oraculo.py`) y en la conversión del front (`aUniver.test.ts`); un libro de 200 001 celdas da 422 (`test_visual_libro.py`) |
| RF‑112 | La interfaz nueva se sirve en `/app` como archivos estáticos sin secretos, con CSP `default-src 'self'`, sin `unsafe-eval`; excepciones declaradas: `style-src 'unsafe-inline'` (Univer inyecta estilos) e `img-src data: blob:`; más `nosniff` y `Referrer-Policy: no-referrer` | Esencial | UC‑26 | Sílice 1.2.0 (ruta, sesión 2) | Pruebas de `/app` (`test_api_interfaz.py`): CSP exacta, sin clave en el HTML, 404 claro si no está compilada |
| RF‑113 | Acceso del navegador por cuenta: `POST/GET/DELETE /v1/sesion` con cookie `HttpOnly` y `SameSite=Strict`, sin `Secure` (la red local va por HTTP; límite declarado, se revisa en la sesión 5; RS2‑6); token anti‑CSRF recalculable desde la cookie (RS2‑4) en `X-Silice-CSRF` y `Origin` propio en toda escritura con cookie; rol con `LEER_PROYECTO` (arma o revisa) en las rutas de libros (RS2‑5); la clave de API sigue para integraciones. Las credenciales pasan por el control de UC‑21: 401 mala, 423 bloqueada, 403 si debe cambiar la contraseña (sin cookie), 429 con `Retry-After` si el freno global lo pide, sin dormir el hilo y sin contar fallo (RS2‑11); el 422 no repite lo enviado. Sesión: 30 min de inactividad o 12 h | Esencial | UC‑26 | Sílice 1.2.0 (ruta, sesión 2) | `test_api_sesion_web.py`: sin cookie 401; sin CSRF u `Origin` ajeno o ausente 403; administrador sin arma ni revisa 403; 429 con `Retry-After` y sin intento contado; con clave, igual que en la 1.5 |
| RF‑114 | Visor de solo lectura en lienzo (Univer, solo Apache‑2.0) con el aspecto de RF‑111: los números se muestran con el código de formato de Excel de la celda y los separadores de es‑VE (RS2‑14) | Esencial | UC‑26 | Sílice 1.2.0 (ruta, sesión 2) | No se puede editar ninguna celda (verificación manual: sin barras ni menú contextual, doble clic sin efecto); la conversión a coordenadas, estilos y formatos del lienzo está en un solo módulo con prueba (`aUniver.test.ts`, `formatoNumero.test.ts`): `1738.407` con `#,##0.00` se ve `1.738,41` |
| RF‑115 | Halo de severidad con ícono y texto accesible sobre la celda de cada hallazgo, alineado al desplazar, acercar y cambiar de hoja; la celda de una fila o columna oculta no lleva halo | Esencial | UC‑26 | Sílice 1.2.0 (ruta, sesión 2) | `halos.test.ts`, `CapaHalos.test.tsx`, `Visor.test.tsx`; verificación manual a 1366×768 (desplazar, acercar, cambiar de hoja), con capturas en la bitácora |
| RF‑116 | Indicadores Fiori (valor, meta, Δ, Δ%) calculados por la API con `Decimal` (campo `indicadores`: «Subtotal sin IVA», «IVA» y «Total general», los presentes en los dos totales). Actual = total del libro; meta = total de Sílice. Son presentación (RS2‑12, NORMAS §2.3): actual, meta, Δ y Δ% van en centésimas con redondeo al par, calculados desde los valores exactos, que siguen en `totales_libro` y `totales_silice`; un Δ de menos de medio centavo es «sin variación» (Δ `0.00` y Δ% `0.00`, sin signo); Δ% es nulo si la meta es cero o no cabe en la precisión. (**Superado por la decisión V-16 de Eugenio (2026-10-21): libro menor = favorable.** Para el libro contra Sílice, `delta = actual − meta`: negativo (libro menor que Sílice) es favorable (verde), positivo (libro mayor) es desfavorable (rojo) y cero es neutro. Riesgo aceptado y declarado: un libro que omite costos puede salir en verde.) Texto anterior, conservado por trazabilidad: sentido «exactitud» (RS2‑13, a ratificar por Eugenio): la meta es el valor correcto de Sílice, así que toda desviación del libro, por encima o por debajo, es desfavorable (rojo) y «sin variación» es neutro (gris); el color nunca depende del signo y la flecha, con su texto accesible, dice si el libro declara más o menos que Sílice. El valor exacto de los totales del libro y de Sílice está siempre en el tooltip accesible de cada indicador | Esencial | UC‑26 | Sílice 1.2.0 (ruta, sesión 2) | `indicadores_de` y las rutas (`tests/unit/test_api_libros_replica.py`, `tests/integration/test_api_libros.py`): libro limpio sin variación, sobreprecio sembrado y libro bajo el costo de Sílice (ambos desfavorables), meta cero con Δ% nulo, redondeo al par, ruido menor que medio centavo sin variación, montos sin notación científica; `semanticaIbcs` con sentido «exactitud» y el tooltip con el exacto (`frontend-desktop/src/indicadores/ibcs.test.ts`, `IndicadorFiori.test.tsx`) |
| RF‑117 | El instalador lleva la interfaz compilada y el flujo de la CI la compila con Node 22 antes de construir | Esencial | UC‑26 | Sílice 1.2.0 (ruta, sesión 2) | `test_instalador_interfaz.py` y `test_manifiesto.py`: el manifiesto declara el `dist` y la construcción falla con mensaje claro si falta o está vacío; el instalador básico sigue ≤ 150 MB (RNF‑19, medido por `instalador.yml`) |
| RF‑118 | Lista de hallazgos filtrable por severidad y sincronizada con la hoja (tocar uno lleva la hoja a su celda; tocar una celda marcada resalta su hallazgo); los hallazgos sin celda ubicable se listan aparte en «Sin celda en el libro» | Esencial | UC‑26 | Sílice 1.2.0 (ruta, sesión 2) | `ListaHallazgos.test.tsx` (filtro, texto de severidad, salto a la celda, teclado), `halos.test.ts` (`sinCelda`), `Visor.test.tsx` |

| RNF | Requisito | Verificación |
|---|---|---|
| RNF‑22 | Sin red externa ni secretos en el navegador: CSP sin `unsafe-eval` ni anfitriones externos; fuentes IBM Plex alojadas; ninguna URL se consulta a otro anfitrión (el `dist` solo contiene los textos y espacios de nombres de la lista blanca de `scripts/verificar_dist.mjs`, que ninguna rutina pide a la red); nada en `localStorage` ni `sessionStorage` (el token anti‑CSRF solo vive en memoria); sin telemetría; ningún script de instalación de npm (`.npmrc` con `ignore-scripts=true`, RS2‑15: el de Carbon envía telemetría a IBM); dependencias de producción con licencias permisivas (MIT, Apache‑2.0, BSD, ISC, 0BSD, OFL‑1.1, BlueOak‑1.0.0, CC0‑1.0, Python‑2.0, MIT‑0; MPL‑2.0 y CC‑BY‑4.0 solo de desarrollo) y sin `@univerjs-pro` | Trabajo `interfaz` de la CI: `npm run licencias`, `npm run dist`; `test_api_interfaz.py`; `Entrar.test.tsx` |
| RNF‑23 | Usabilidad y accesibilidad: WCAG 2.1 AA (texto 4,5:1, gráficos 3:1, el color nunca solo, teclado); 1366×768 sin desplazamiento horizontal de la página; `prefers-reduced-motion` respetado; sin animación propia (solo las transiciones de estado de Carbon, ≤ 110 ms, anuladas con `prefers-reduced-motion`); `dist` ≤ 15 000 000 bytes sin comprimir | Tamaño: `npm run dist` (automático). Resto: revisión manual con la lista de `DESIGN.md` y el detector de impeccable, capturas a 1366×768 y 1920×1080 en la bitácora; sin prueba automática de contraste ni de teclado |

Trazabilidad: UC‑26 → RF‑111 … RF‑118, RNF‑22, RNF‑23 → ruta sesión 2 (Sílice 1.2.0) → indicador 1 (errores
detectados, ahora ubicados sobre la hoja). Pruebas por requisito: [plan_pruebas.md §8.0f](plan_pruebas.md).

#### UC‑28 — Saber cuánto hay y cuánto queda de cada material de la arenera

- **Actor principal:** quien arma o el administrador (acción `OPERAR_ARENERA`). **Secundario:** quien pesa en la
  báscula de salida.
- **Precondiciones:** los materiales están registrados con su unidad de venta (`m3` o `t`), su existencia mínima y,
  si se venden en m³ y se pesan en t, su densidad aparente (dato de la empresa; no hay valor por defecto).
- **Flujo principal**
  1. El usuario registra una entrada de producción, un despacho o un conteo físico de un material.
  2. Sílice guarda el movimiento con su fecha, su origen (manual o báscula) y quién lo registró.
  3. El tablero muestra por material la existencia a una fecha (Σ entradas − Σ despachos ± ajustes) frente a la
     mínima, con la alerta «queda poco» cuando la existencia es menor o igual que la mínima.
- **Flujos alternativos**
  - *1a. Conteo distinto de lo registrado:* se guarda el ajuste (diferencia con signo); si no hay diferencia, no se
    guarda nada.
  - *1b. Despacho que deja la existencia negativa:* se registra igual (el camión salió) y el tablero lo marca
    «falta registrar producción o conteo».
  - *1c. Cantidad cero o negativa, o código repetido:* mensaje claro; no se guarda.
- **Postcondiciones:** los movimientos quedan en la base de la instalación; ningún cálculo usa una cifra sin fuente.

#### UC‑29 — Importar el reporte de la báscula

- **Actor principal:** quien arma o el administrador (acción `OPERAR_ARENERA`).
- **Precondiciones:** un reporte `.xlsx` o `.csv` de la báscula de salida y los materiales ya registrados.
- **Flujo principal**
  1. El usuario sube el reporte e indica la fecha de referencia (hoy) y, si el encabezado no la trae, la unidad
     del peso (kg o t).
  2. Sílice comprueba el archivo, detecta las columnas (ticket, fecha, placa, cliente, material, bruto, tara,
     neto) y la unidad del peso.
  3. Valida cada pesaje: lo coherente se registra como despacho; lo dudoso va a la bandeja «Pesajes sospechosos».
  4. Muestra cuántos se registraron, cuántos ya estaban y cuántos esperan revisión.
  5. El usuario resuelve (con los valores corregidos) o descarta cada pesaje sospechoso.
- **Flujos alternativos**
  - *2a. Archivo rechazado* (macros, extensión, tamaño, filas o columnas desmedidas): mensaje claro; no se lee nada.
  - *2b. Faltan columnas o la unidad del peso:* se pide el mapeo o la unidad; no se importa nada.
  - *3a. Reimportar el mismo reporte:* no se duplica nada.
- **Postcondiciones:** los despachos y la bandeja quedan en la base de la instalación; el reporte original no se
  guarda.

| RF | Requisito |
|---|---|
| RF‑127 | Materiales de la arenera: código, nombre, unidad de venta (`m3` o `t`), densidad aparente (dato de la empresa, sin valor por defecto) y existencia mínima |
| RF‑128 | Movimientos de producción (entrada), despacho y ajuste por conteo; existencia = Σ entradas − Σ despachos ± ajustes, por material y fecha |
| RF‑129 | Tablero «cuánto hay y cuánto queda» con la alerta «queda poco» (existencia ≤ mínima) y la señal de existencia negativa |
| RF‑130 | Importar reportes de báscula `.xlsx` y `.csv` con detección de columnas, del separador decimal y de la unidad del peso; sin unidad no se importa |
| RF‑131 | Validar cada pesaje (tara ≥ bruto, neto ≠ bruto − tara, fecha futura o ilegible, número ambiguo, ticket repetido, material desconocido o sin densidad) y enviar lo dudoso a la bandeja «Pesajes sospechosos» |
| RF‑132 | Reimportar el mismo reporte no duplica despachos ni sospechosos |
| RF‑133 | Resolver (con valores corregidos) o descartar un pesaje sospechoso, con quién y cuándo |
| RF‑134 | Rutas `/v1/produccion/*` con clave de API; las cantidades viajan como texto |
| RF‑135 | Pantalla «Existencias de la arenera» con permiso por rol (acción `OPERAR_ARENERA`) |
| RF‑136 | Registro de constantes con el estado de su fuente; los reportes reales de báscula nunca se versionan |

| RNF | Requisito |
|---|---|
| RNF‑25 | Límites de recursos al leer reportes de báscula ajenos: 20 MiB, 100 000 filas, 60 columnas, solo lectura |

Trazabilidad: UC‑28 → RF‑127 … RF‑129, RF‑135 y RF‑136; UC‑29 → RF‑130 … RF‑134, RNF‑25 → Sílice 1.4.0 (sesión 4 de
la [ruta](planes/RUTA_SESIONES.md)). Fuera de los cinco indicadores de la tesis. Pruebas: oráculo a mano en
`tests/fixtures/bascula/ORACULO.md` y `tests/unit/test_produccion_inventario.py`.

## Enmienda Sílice 1.2.0 (2026-10-18): historial de auditorías de «Libro de la empresa»

Sesión 4 de la [ruta](planes/RUTA_SESIONES.md), [plan del historial](planes/PLAN_SESION_4_HISTORIAL.md). Decisión de
Eugenio (2026-10-18): **cada auditoría se guarda**; se guarda el resumen y los hallazgos, **nunca el libro ni el PDF**.
Cambia la regla F‑D9 de la 1.5 («no hay tablas nuevas»): hay una, `auditoria_libro`, en la base de la instalación.

#### UC‑30 — Consultar el historial de auditorías

- **Actor principal:** quien arma o quien revisa (acción `LEER_PROYECTO`) o una integración con clave de API.
- **Precondiciones:** se corrió al menos una auditoría de UC‑25 (de un libro o de un PDF simple).
- **Flujo principal**
  1. El usuario abre el historial (el Inicio muestra las últimas cinco; la pantalla «Historial de auditorías» muestra
     la lista completa).
  2. Sílice responde las auditorías de la instalación, la más reciente primero, con su archivo, su fecha y hora, su
     tipo (`libro` o `pdf`) y su cuenta de errores y de advertencias.
  3. Al elegir una, muestra su resumen (quién, cuándo, huella SHA‑256, fecha y totales del libro y de Sílice, conteos
     por severidad) y sus hallazgos, en solo lectura.
- **Flujos alternativos**
  - *2a. Aún no hay auditorías:* la lista llega vacía y se dice cómo empezar.
  - *3a. La auditoría no existe:* mensaje claro (404).
  - *3b. La auditoría tuvo más de 500 hallazgos:* se muestran los primeros 500 y el aviso de que se recortó; los
    conteos son los de todos.
- **Postcondiciones:** solo lectura. Para volver a trabajar sobre el libro hay que subirlo otra vez: no se conserva.

| RF | Requisito | Criterio de aceptación |
|---|---|---|
| RF‑142 | Cada auditoría correcta de «Libro de la empresa» (libro o PDF simple) guarda **una fila nueva** en `auditoria_libro` de `instalacion.db`, sin deduplicar por SHA‑256 (repetirla es un hecho): usuario, fecha y hora, tipo, nombre y SHA‑256 del archivo, fecha del libro, total del libro y total de Sílice (texto decimal exacto; nulos en un PDF) y conteos por severidad (`errores`, `advertencias`, `informativos`, `atipicos`) | `tests/integration/test_historial_auditorias.py`: la fila guardada coincide con la escrita a mano, repetir deja dos filas, un PDF va sin totales ni fecha del libro |
| RF‑143 | Los hallazgos se guardan **compactos** (regla, hoja, celda, severidad y mensaje, y nada más), a lo sumo 500 por auditoría; pasado el tope se guardan los primeros 500, `recortado` es verdadero y los conteos siguen siendo los de todos | 503 hallazgos dan 500 guardados, `recortado` y 503 en el conteo; con exactamente 500 no se recorta |
| RF‑144 | Un fallo al guardar el historial **no tumba la auditoría**: el informe se responde igual, el fallo queda en el registro del servidor y la pantalla avisa «No se pudo guardar el historial» | Con el guardado forzado a fallar, `POST /v1/libros/auditoria` y `/pdf` responden 200 con el informe y el registro lleva el fallo (pruebas de la tarea que aplica el parche de [PLAN_SESION_4_HISTORIAL.md](planes/PLAN_SESION_4_HISTORIAL.md)) |
| RF‑145 | `GET /v1/auditorias-libro?limite=N` (1 a 100, 20 por omisión) responde la lista de `{id, archivo, fecha, tipo, errores, advertencias}`, la más reciente primero, con la fecha en ISO con hora; clave de API o cuenta que arma o revisa | `tests/integration/test_api_auditorias_libro.py`: claves literales, orden, límites, 422 fuera de rango, 401 sin credenciales, 403 al administrador solo |
| RF‑146 | `GET /v1/auditorias-libro/{id}` responde el resumen completo y los hallazgos compactos; los montos como texto; 404 si no existe | Igual archivo de pruebas: detalle exacto de una auditoría sembrada, nulos de un PDF y 404 |

| RNF | Requisito |
|---|---|
| RNF‑28 | **Nunca se conserva el libro ni el PDF** auditados: ni sus bytes, ni una copia temporal; de ellos solo queda el nombre del archivo (sin ruta) y su SHA‑256. La tabla no tiene columna binaria y el mensaje de cada hallazgo se corta a 500 caracteres |

Trazabilidad: UC‑25 → RF‑142 … RF‑144 y RNF‑28 (el guardado de cada auditoría); UC‑30 → RF‑142 … RF‑146 y
RNF‑28 → Sílice 1.2.0 (sesión 4 de la ruta). Pruebas: `tests/integration/test_migracion_auditoria_libro.py`,
`tests/integration/test_historial_auditorias.py`, `tests/integration/test_api_auditorias_libro.py` y
`tests/unit/test_documentos_historial_auditorias.py`. Modelo de datos: [modelo_datos.md §10](modelo_datos.md).

## Apéndices
- A. Caso de estudio y línea base: [docs/linea_base.md](linea_base.md).
- B. Modelo de datos: [docs/modelo_datos.md](modelo_datos.md).
- C. Arquitectura: [docs/arquitectura.md](arquitectura.md).
