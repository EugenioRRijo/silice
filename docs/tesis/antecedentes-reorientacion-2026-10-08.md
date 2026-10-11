# Antecedentes para la reorientación del sistema APU

Búsqueda hecha el 2026-10-08. Las marcas significan lo siguiente:

- **VERIFICADO**: abrí la fuente, o sus metadatos en Crossref (api.crossref.org/works/DOI), y el dato sale de ahí.
- **INDICIO**: solo lo vi en un resumen del buscador, en una transcripción no oficial o en una fuente secundaria.
- **NO ENCONTRADO**: lo busqué y no apareció.

Varios editores (MDPI, Emerald, preprints.org, MATEC, ASCE) devolvieron 403 al abrir la página. En esos casos verifiqué título, autores y resumen por Crossref; no leí el texto completo.

## 1. Modelos de lenguaje (LLM) para estimar costos, y verificación con reglas

| Trabajo | Qué hace | Qué le falta frente a (a) | Estado |
|---|---|---|---|
| Wu, Wang y Liu (2025). *CEQuest: Benchmarking Large Language Models for Construction Estimation*. arXiv:2508.16081 — https://arxiv.org/abs/2508.16081 | Banco de preguntas para comparar cinco LLM en lectura de planos y estimación. Concluye que tienen «considerable room for improvement». | Solo mide. No verifica las respuestas ni produce un presupuesto. | VERIFICADO |
| Ghimire, Kim, Stentz y Roy (2025). *State-of-the-Art Pre-Trained LLMs for Construction Cost Estimation Tasks…Modular Chain of Thought*. Preprints, DOI 10.20944/preprints202510.1060.v1 | Compara GPT-4o, LLaMA 3.2, Gemini 2.0 y Claude 3.5. Con cadena de razonamiento (CoT) la confianza sube del 64 % al 84 %. | Evalúa con métricas de texto (BLEU, ROUGE). No hay un motor determinista que audite. | VERIFICADO (Crossref) |
| Ghimire y Kim (2025). *Construction Cost Estimation: Existing Workflow, Burdens, and Proposed LLMs-Integrated Framework*. DOI 10.20944/preprints202512.0035.v1 | Propone un marco con IA generativa que incluye control de versiones. | Es conceptual; no implementa reglas. | VERIFICADO (Crossref) |
| Wu, Zhang, Xu et al. (2026). *An Agentic AI and LLM-Based Framework for Probabilistic Cost Estimation from Fragmented BIM Data*. Intelligent Infrastructure and Construction 2(8), DOI 10.3390/iic2030008 | Cuatro agentes con GPT-4 Turbo y Monte Carlo sobre BIM. Reporta 86,5 % de acierto en resolución de entidades. | El resumen no menciona verificación determinista. | VERIFICADO |
| Gatto, Cassandro, Mirarchi y Pavan (2024). *LLM based automatic relation between cost domain descriptions and IFC objects*. CIB W78 — https://re.public.polimi.it/handle/11311/1280791 | Mistral-7b asigna descripciones de costo a objetos IFC. | Solo clasifica; no arma el APU ni lo audita. | VERIFICADO |
| Borkowski y Buniewicz (2026). *Analysis of a LLM in the Process of Quantity Surveying and Cost Estimation Using Interoperable BIM Models*. SSRN, DOI 10.2139/ssrn.6805069 | El LLM mapea elementos IFC a un catálogo y calcula costos. Los autores reconocen que «expert monitoring remains essential». | La verificación queda en manos de una persona. | VERIFICADO (Crossref) |
| Castagnone y Nitti (2026). *A Neuro-Symbolic Framework for Ensuring Deterministic Reliability in AI-Assisted Structural Engineering: The SYNAPSE Architecture*. Buildings 16(534), DOI 10.3390/buildings16030534 | Es el antecedente más cercano a (a): el LLM delega «critical operations to deterministic external algorithms». Logra 94 % de acierto. | Es de cálculo estructural (3Muri), no de presupuestos ni APU. | VERIFICADO (Crossref) |

Resultado: no encontré ningún trabajo que use un LLM para proponer un presupuesto o APU y que luego lo audite con reglas deterministas. Busqué combinaciones de «LLM + cost estimation + rule-based / neuro-symbolic / verification». La idea neurosimbólica sí está publicada en ingeniería estructural (SYNAPSE).

En el mercado venezolano existe además **OneEstimate** (https://oneestimate.ai/es/blog/apu-construccion-venezuela-2026). Dice que genera APU «en minutos» con precios de Venezuela y tiene «+10,700 APUs». Su página no describe cómo se verifica lo que produce la IA. Estado: VERIFICADO como texto de mercadeo; la capacidad real no está comprobada.

## 2. Valor ganado (EVM) con inflación o con dos monedas

- **Warszawski y Rosenfeld (1982).** *Financial Analysis under Inflation in Construction*. J. Construction Division 108:341-354, DOI 10.1061/JCCEAZ.0001046. Es análisis financiero bajo inflación; no trata el valor ganado. VERIFICADO (Crossref, sin resumen).
- **Gładysz y Kuchta (2008).** *Estimation of long-term project risk… combination of the earned value and present value methods*. Operations Research and Decisions 18(3). https://ord.pwr.edu.pl/Issues/2008/vol18/p103. VERIFICADO.
- **Fayad, Hussein, Maalouf y Haj-Ali (2019).** *An Improved Earned Value Analysis Tool for Mitigating Progress Risks in Long Duration Projects*. MATEC 281:05001, DOI 10.1051/matecconf/201928105001. Combina EVM con valor presente neto. VERIFICADO (Crossref).
- **Fayad et al. (2019).** *A New Approach for Complementing the Earned Value Method…*. New Challenges in Accounting and Finance. Ajusta el PV y el AC por inflación mediante el valor presente neto. https://ideas.repec.org/a/bco/ncafaa/v2y2019p11-18.html. VERIFICADO.
- **AACE 2019, EST-3252.** *Cost Estimating in Hyperinflation Economies*. https://www.pathlms.com/aace/courses/3165/video_presentations/136401. Trata la estimación de costos, no el control con valor ganado. VERIFICADO; el presentador no aparece en la página.
- **Separar desvío por precio y desvío por cantidad.** Es práctica conocida en EVM para materiales:
  - precio = (precio unitario de BCWP − precio unitario de ACWP) × cantidad de ACWP;
  - uso = (cantidad de BCWP − cantidad de ACWP) × precio unitario de BCWP.
  
  Fuente: Humphreys & Associates, https://blog.humphreys-assoc.com/evm-topic-material-earned-value-price-vs-usage-variance-analysis/. VERIFICADO; es un blog de consultoría, no un artículo arbitrado.
- **EVM con varias monedas.** Hay una presentación de AACE y un artículo de PMI («Using multiple currencies for global project costing»), pero ambos dieron 403. INDICIO.
- **Venezuela o Latinoamérica.** NO ENCONTRADO: ningún trabajo de valor ganado ajustado por inflación ni con bolívares y dólares a la vez. El repositorio Saber UCV solo tiene textos económicos sobre la hiperinflación (p. ej. Rojas Díaz 2021, https://saber.ucv.ve/jspui/handle/10872/20983) y una tesis de control de costos de 2013 (Figueroa, handle 10872/4591) que no se refiere a la inflación.

## 3. Compresión del cronograma a partir del rendimiento y la cuadrilla

- **Lee, Chijoo (2022).** *Evaluating construction delays using productivity-based resource reallocation for economic feasibility*. ECAM 30:1679-1696, DOI 10.1108/ECAM-09-2019-0503. Usa productividad, precio unitario y carga de trabajo de cada cuadrilla para calcular la duración que se puede reducir y el número de trabajadores necesario, con programación por metas. Es el antecedente más cercano a (c). VERIFICADO (Crossref).
- **Axworthy (1990).** *TR021: A Knowledge-Based Model of Time-Cost Tradeoff Analysis for Construction Schedules* (JANUS). Stanford CIFE, https://purl.stanford.edu/ry476dw6976. Usa tácticas genéricas de aceleración en lugar de datos numéricos. VERIFICADO.
- **Castañeda Vega, Daza Jaimes y Rincón Vargas (2024).** *Revisión de las técnicas de compresión de cronograma crashing y fast-tracking para proyectos de construcción*. U. Distrital (Colombia). https://repository.udistrital.edu.co/items/9073b117-0550-4155-95e6-457b9acf3a6b. VERIFICADO.
- **Nie y Gao (2015).** Modelos discretos multimodo de tiempo y costo, PeerJ Preprints, DOI 10.7287/peerj.preprints.1299v3. INDICIO (solo metadatos).

NO ENCONTRADO: un trabajo que obtenga las opciones de compresión directamente del rendimiento y la cuadrilla de un APU al estilo venezolano (COVENIN o MaPreX).

## 4. Norma venezolana sobre variación de precios

- **Decreto N° 1.399, Ley de Contrataciones Públicas.** Gaceta Oficial N° 6.154 Extraordinario del 19-11-2014. Leí la transcripción de https://pandectasdigital.blogspot.com/2016/05/decreto-n-1399-de-fecha-13-de-noviembre.html, que la marca «Vigente», y lo confirmé con lawinsider:
  - **Art. 133, «Variaciones de precios»:** las variaciones aprobadas «se reconocerán y pagarán… entre los cuales se señalan el calculado con base en las variaciones de índices incluidos en fórmulas escalatorias o el de comprobación directa».
  - **Art. 134, contratos de más de un año:** el contrato debe incluir «1. La estructura de costos por renglón o partida. 2. Los mecanismos de ajuste… 3. La periodicidad… 4. Los precios referenciales o índices… indicando… el órgano competente que los genere». Los precios quedan fijos el primer año «siempre y cuando no vulnere el equilibrio económico del contrato». En cada período solo se ajusta la obra ejecutada en ese período. En reconsideraciones, la fórmula escalatoria solo sirve para obras y servicios.
  - **Art. 59, «Presupuesto Base».**
  - **Disposición derogatoria única:** los actos normativos anteriores siguen vigentes «en tanto no contradigan». La transitoria tercera cita expresamente el Reglamento de 2009.
  
  Estado: VERIFICADO en una transcripción no oficial. Hay que cotejarlo con la Gaceta antes de citarlo en la tesis.
- **Atribución de la Comisión de Contrataciones.** Debe opinar sobre variaciones de precios que superen el 10 % del monto original. Un resumen la ubica en el art. 15, num. 14, y otro en el art. 14. INDICIO: el número de artículo está sin confirmar.
- **Ley de 2009** (G.O. 39.165, ya derogada). Su art. 110 hablaba de «fórmulas polinómicas»; la ley de 2014 dice «fórmulas escalatorias». VERIFICADO en la transcripción de tugacetaoficial.com.
- **Reglamento** (Decreto N° 6.708, G.O. N° 39.181 del 19-05-2009). Su existencia y su Gaceta constan en la propia ley de 2014. Los artículos sobre variaciones de precios NO están verificados: los PDF de OAS, Contraloría de Mérida, ALMCCS y Tradex estaban bloqueados. Un resumen del buscador habla de «arts. 140-142»; no lo usaría.
- **Ley o reglamento nuevos (2024-2026):** NO ENCONTRADO.
- **Norma COVENIN sobre reajuste o escalatoria:** NO ENCONTRADA.
- **Práctica.** Se usa la fórmula `Vpm = Vo(Km−1)(1−R)` (Scribd «ESCALATORIAS», https://es.scribd.com/document/797364489/ESCALATORIAS). INDICIO; el autor no se identifica.

## 5. Programas de presupuesto usados en Venezuela

- **LuloWin NG** (Lulo Software). El sitio oficial http://www.lulo.com.ve/LuloWin.htm estaba bloqueado por una verificación anti-bots. La ficha de e-construir.com dice «Hacer valuaciones y cuadros de cierre», presupuestos y análisis de precios. Un resumen del buscador menciona «reconsideraciones de precios». Estado: INDICIO, porque la fuente oficial no abrió. No se encontró nada sobre auditoría ni sobre control de avance con valor ganado.
- **DataLaing MaPreX** (https://datalaing.com/site/datalaing-maprex-4/). Ofrece APU y presupuesto «con fórmulas de cálculo», hojas de medición, exportación «en 2 Monedas», precios zonificados y 22 600 partidas. También tiene un Boletín Analítico sobre la inflación del sector. La página no dice nada de reconsideraciones, escalatorias, auditoría ni control de avance. VERIFICADO.
- **IP3:** NO ENCONTRADO. Probé ip3.com.ve, ip3software.com y varias búsquedas.
- **OneEstimate:** ver la sección 1.

## 6. BCV: tasa de cambio e INPC

Todo esto lo descargué y abrí el 2026-10-08. VERIFICADO.

- **Tasa diaria.** Aparece en la portada (https://www.bcv.org.ve/), con «Fecha Valor» del día hábil siguiente.
- **Serie de la tasa.** Está en https://www.bcv.org.ve/estadisticas/tipo-cambio-de-referencia-smc, en archivos **.xls** trimestrales (`/sites/default/files/EstadisticasGeneral/2_1_2{a,b,c,d}{AA}_smc.xls`).
  - Cada archivo trae **una hoja por día hábil**. El de 3T-2026 tiene 64 hojas, del 01-07 al 30-09.
  - Cada hoja da compra y venta en moneda extranjera por US$ y en Bs por moneda extranjera. Ejemplo: USD 858,02 / 860,18 Bs, fecha valor 01-10-2026.
  - Formato: una hoja por día; hay que consolidarlas para tener una serie.
- **Otra página.** https://www.bcv.org.ve/estadisticas/tipo-de-cambio-de-referencia-0 tiene archivos .xlsx (`2_1_1_tdc.xlsx` y otros). Abrí los enlaces, no el contenido de los archivos.
- **INPC.** Está en https://www.bcv.org.ve/estadisticas/consumidor, archivos .xls con series **mensuales** (p. ej. `4_5_1.xls`, variaciones por grupos desde 2014). El último mes publicado es septiembre de 2026; los datos de 2026 están marcados «(*)», o sea, provisionales. Fuente: BCV-INE.
- **Índice de precios de insumos de la construcción.** También lo publica el BCV, a nivel de productor y de mayorista, con periodicidad mensual, trimestral y anual: https://www.bcv.org.ve/estadisticas/insumos-de-la-construccion. Abrí los enlaces, no el contenido. Es el índice natural para una fórmula escalatoria.
- **Restricciones de acceso.**
  - El certificado TLS del BCV tiene la cadena incompleta. Los clientes de Node/WebFetch fallan con «unable to verify the first certificate»; curl en Windows sí entra.
  - No encontré una API oficial.
  - Algunos años tienen archivos separados con nombres irregulares.

## 7. Trabajos de grado venezolanos

- **Méndez P., Carlos E. (2018).** *Elaboración de unidades de construcción para el sistema eléctrico de la Ciudad Universitaria de Caracas*. TEG, UCV. https://saber.ucv.ve/jspui/handle/10872/17732. Crea un programa que genera APU y compara programas venezolanos existentes. Es el antecedente local más directo. VERIFICADO.
- **Angulo y Meléndez (2015)**, handle 10872/11405, y **Castillo y De La Cruz (2015)**, handle 10872/11614. Estudian costos de fundaciones (UCV); no hay software. VERIFICADO.
- **Figueroa P., Ana K. (2013).** *Control de Costos de Proyectos de Ingeniería Básica y de Detalle* (UCV, 10872/4591). VERIFICADO.
- **UCAB:** hay un PDF (biblioteca2.ucab.edu.ve, AAS0661) que menciona el APU con rendimiento de cuadrilla, pero no descargó. INDICIO.
- **USB, UNIMET, LUZ, USM:** NO ENCONTRADO. Los repositorios no salieron en las búsquedas y no los consulté uno por uno.
- **Fuera de Venezuela** hay tesis parecidas de software de APU, por ejemplo ESPE en Ecuador, http://repositorio.espe.edu.ec/xmlui/handle/21000/11260. INDICIO.

## ¿Dónde queda el aporte?

- **(a) LLM que propone y auditor de reglas que verifica.**
  - Ya existe: LLM para estimar costos (Ghimire, Wu, Borkowski) y la arquitectura neurosimbólica en estructuras (SYNAPSE 2026).
  - Parece nuevo: aplicarla a APU y presupuestos con reglas de auditoría deterministas. No hallé antecedentes, y es lo más defendible.
  - Riesgo: es un campo que se mueve muy rápido y pudo salir algo en 2026 que no encontré. OneEstimate ya vende «APU con IA» en Venezuela, así que la novedad tiene que estar en la verificación y la trazabilidad, no en «generar con IA». Además, evaluar la IA exige un conjunto de casos de referencia, y los APU del repositorio son ficticios.
- **(b) Presupuesto vivo: valor ganado que separa plazo y precio en Bs, con reajuste.**
  - Ya existe: separar precio y cantidad es práctica conocida en EVM, y el ajuste por valor presente también (Fayad 2019).
  - Parece nuevo: combinarlo con la fórmula escalatoria del art. 134 y con los índices de insumos de la construcción del BCV, en contexto de bolívares y dólares. No encontré nada así en Venezuela.
  - Riesgo: el Reglamento no está verificado, los datos 2026 del INPC son provisionales y el acceso al BCV no es estable. Necesita la revisión de un experto en contratación pública.
- **(c) Compresión del cronograma desde el rendimiento y la cuadrilla del APU.**
  - Ya existe: la idea central está en Lee (2022), y el crashing es un tema clásico.
  - Aporte posible: conectarlo con el APU venezolano, que ya trae rendimiento y cuadrilla. Es una aplicación, no un método nuevo.
  - Riesgo: suponer que el rendimiento crece en línea recta con la cuadrilla es falso (hay rendimientos decrecientes). Hay que declararlo como supuesto.
- **(d) Registro de cambios encadenado con SHA-256.**
  - Es técnica conocida: cadenas de hash, y blockchain en pagos de construcción (Hamledari y Fischer 2021, Automation in Construction, DOI 10.1016/j.autcon.2021.103926, VERIFICADO por Crossref).
  - Riesgo: aporte académico bajo; conviene presentarlo como requisito de integridad, no como contribución.
- **(e) Detección de anomalías en variaciones de precio.**
  - Ya existe en compras públicas: Isolation Forest, LOF y One-Class SVM (Araújo et al. 2024, LASDiGov, https://sol.sbc.org.br/index.php/wcge/article/view/29532), y modelado de precios antes de buscar valores atípicos (Soares et al. 2024, https://sol.sbc.org.br/index.php/sbbd_estendido/article/view/30804).
  - Riesgo: sin datos reales de precios venezolanos no se puede validar, y los datos del repositorio son ficticios. Si se mantiene, debería ser un complemento menor.

En síntesis, el núcleo defendible es (a) junto con (b): la IA propone, las reglas deterministas auditan y el valor ganado se reajusta según el art. 134 con índices del BCV. (c) es una aplicación valiosa; (d) y (e) son soporte.
