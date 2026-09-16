# Capítulo II — Marco teórico

| Capítulo | Estado | Última revisión |
|---|---|---|
| II. Marco teórico | borrador completo, revisado con la lista de cotejo (Sesión R1.7) | 2026-09-15 |

## 2.1 Antecedentes de la investigación

La revisión de antecedentes se organizó en tres ámbitos, internacional, latinoamericano y nacional, y dentro del ámbito internacional en líneas temáticas: la cuantificación y la estimación de costos a partir de modelos BIM, el aprendizaje automático aplicado a costos, el procesamiento de lenguaje natural en textos técnicos de construcción y los modelos digitales con realimentación del activo. De cada trabajo se indica qué hizo y qué aporta a esta investigación. Las referencias se contrastaron con sus fuentes; las que conservan datos por confirmar llevan la marca correspondiente.

### 2.1.1 Ámbito internacional

#### Cuantificación y estimación de costos a partir de modelos BIM

Ma et al. (2011) [verificación pendiente] aplicaron y extendieron el estándar IFC para la estimación de costos en licitaciones de obra en China. Su aporte a esta investigación es mostrar que el formato abierto IFC puede adaptarse a las reglas de un sistema nacional de estimación, que es la decisión que aquí se adopta al tomar IFC como frontera entre el modelado y el cálculo del presupuesto venezolano.

Khosakitchalert et al. (2019) abordaron la mejora de la exactitud de la cuantificación basada en BIM para elementos compuestos. La necesidad misma de mejorar esa exactitud advierte, para esta investigación, que el uso de un modelo no garantiza por sí solo cantidades correctas: la exactitud depende de cómo se modelan los elementos, lo que justifica contrastar las cantidades extraídas con el cálculo manual antes de confiar en ellas.

Wahab y Wang (2021) compararon, elemento por elemento, la cuantificación basada en BIM con la cuantificación tradicional en dos dimensiones, a partir de la constatación de que la literatura no contaba con estudios suficientes para confirmar la superioridad de la primera. Para esta investigación el aporte es metodológico: la ventaja de automatizar el cómputo no se da por supuesta, se mide.

Yang et al. (2022) desarrollaron un modelo de estimación del costo de construcción basado en BIM y en un método paramétrico para la etapa de planificación arquitectónica, tras observar que las estimaciones por unidad de área no consideran otros factores y producen error. Aporta el antecedente de estimar a partir de los parámetros del modelo y no solo del área; esta investigación lleva ese principio a las cantidades de obra de cada partida.

Pishdad y Onungwa (2024) analizaron el uso de BIM‑5D para la estimación de costos, el control de costos y los pagos, y señalaron la falta de integración entre los modelos 5D, el seguimiento del avance y los sistemas de pago, así como la falta de estandarización en el uso de los elementos del modelo. Esas carencias fundamentan dos decisiones de la propuesta: conservar la procedencia de cada cantidad a lo largo de toda la cadena y asociar cada objeto del modelo con un código de partida normalizado.

#### Aprendizaje automático aplicado a costos de construcción

Elmousalami (2020) revisó el estado del arte de la inteligencia artificial y del modelado paramétrico en la estimación de costos de construcción. Su valor para esta investigación es servir de mapa de las técnicas disponibles, a partir del cual se justifica que la técnica se seleccione según los datos existentes.

Tayefeh Hashemi et al. (2020) [verificación pendiente] realizaron una revisión sistemática de las técnicas de aprendizaje automático empleadas para estimar y predecir costos de proyectos de construcción. Aporta el panorama contra el que se contrasta la decisión de degradar la técnica predictiva cuando los datos son escasos.

Kim et al. (2004) compararon modelos de estimación de costos de construcción basados en análisis de regresión, redes neuronales y razonamiento basado en casos. El antecedente respalda que la elección entre esas técnicas es una decisión empírica, dependiente de los datos disponibles, y no una preferencia previa; esta investigación formaliza esa dependencia como un criterio declarado antes de medir.

Huang y Hsieh (2020) predijeron el costo de la mano de obra asociada a BIM con bosques aleatorios y regresión lineal simple. El trabajo muestra la aplicación de un método de ensamble a un costo vinculado con proyectos BIM, familia de técnicas que la propuesta prevé cuando el volumen de datos lo permita.

#### Procesamiento de lenguaje natural en textos técnicos de construcción

Moon et al. (2022) desarrollaron un sistema automatizado de revisión de especificaciones de construcción mediante procesamiento de lenguaje natural. Para esta investigación, confirma que el texto técnico de la construcción puede tratarse de forma automática; aquí el mismo tipo de técnica se aplica a las descripciones de partidas para asociarlas con las del catálogo.

#### Gemelo digital y sombra digital en la construcción

Sacks et al. (2020) formularon la construcción con sistemas de información de gemelo digital a partir de BIM y de la producción lean, y observaron que en edificación e infraestructura el concepto sigue poco definido. Sepasgozar (2021) se propuso diferenciar el gemelo digital de la sombra digital y de otros modelos tridimensionales avanzados. Ambos trabajos aportan el marco con el que se delimita el alcance de esta investigación, desarrollado en las bases teóricas.

#### Síntesis del ámbito internacional

En los trabajos revisados, la cuantificación a partir de modelos BIM y el aprendizaje automático para costos se desarrollan como líneas separadas, y ninguno de ellos incorpora la verificación automática de consistencia entre el cómputo, el presupuesto y el plan de trabajo, ni la estructura de costos derivada de la normativa laboral venezolana. Ese es el espacio que ocupa esta investigación.

### 2.1.2 Ámbito latinoamericano

Rozo-Martínez y Tumay-Gamba (2024) [verificación pendiente] aplicaron la metodología BIM en su dimensión 5D a la gestión del costo de un proyecto de vivienda y compararon los presupuestos elaborados por el método tradicional con los obtenidos a partir del modelo, con el propósito de mostrar sus beneficios económicos para empresas pequeñas. Es el antecedente metodológico más próximo a esta investigación en cuanto a la comparación entre el presupuesto tradicional y el derivado del modelo; a diferencia de él, esta investigación incorpora la verificación automática de consistencia y la estructura de costos venezolana.

Carbonell Charchabal et al. (2026) estudiaron la integración de BIM en el sistema presupuestario cubano para el sector de la construcción. Encontraron que su implementación se encuentra en una fase inicial, limitada principalmente al modelado tridimensional por la complejidad del sistema presupuestario nacional, y destacan que asociar cada componente del modelo con su valor económico favorece la automatización del proceso presupuestario, la trazabilidad de los costos y la coherencia entre el diseño técnico y la estimación financiera. Su aporte es doble: muestra que un sistema presupuestario nacional con reglas propias exige adaptar BIM en lugar de adoptar los flujos internacionales tal como se ofrecen, situación análoga a la venezolana, y respalda la trazabilidad de los costos como beneficio central de la integración.

**Síntesis.** Los trabajos latinoamericanos revisados documentan la aplicación de BIM‑5D a la gestión del costo y la necesidad de adaptarlo a los sistemas presupuestarios nacionales, pero ninguno de ellos automatiza la verificación de consistencia del presupuesto.

### 2.1.3 Ámbito nacional

Quiñones y Uzcátegui (2023) [verificación pendiente] analizaron, en una revista de la Universidad de Los Andes, los beneficios de aplicar la metodología BIM a la optimización de recursos y de los procesos creativos y constructivos de un proyecto de edificación, con base en las buenas prácticas del Project Management Institute y a partir del caso de un conjunto residencial desarrollado en Múnich, Alemania. Su aporte es vincular BIM con la gestión del costo en el marco de la gerencia de proyectos, aunque su caso de estudio no corresponde al contexto normativo venezolano.

Chacón y Cuervo (s.f.) [verificación pendiente] elaboraron, en la Universidad de Carabobo, una guía multimedia para el modelado paramétrico de edificaciones con Revit, en la que comparan la metodología BIM con la metodología CAD tradicional desde la interoperabilidad y la parametrización. Aporta el antecedente nacional de la parametrización como ventaja del modelado BIM, que es la base del motor de reglas paramétricas con el que esta investigación deriva las cantidades de obra.

Garnica (s.f.) [verificación pendiente] propuso una metodología integral de gestión de construcción eficiente coordinada mediante BIM. Aporta el antecedente de concebir BIM como eje de coordinación de la gestión de la construcción, y no solo como herramienta de modelado.

En el plano institucional, el Colegio de Ingenieros de Venezuela presentó una propuesta de ley marco para un plan nacional de adopción de BIM (Colegio de Ingenieros de Venezuela, s.f.) [verificación pendiente], lo que sitúa la incorporación de BIM como un asunto de interés gremial en el país. Para esta investigación, ese interés respalda la pertinencia institucional de adaptar BIM‑5D a la estructura de costos venezolana, expuesta en la justificación institucional (sección 1.4.4).

**Síntesis y conclusión de la revisión.** En los trabajos revisados en los tres ámbitos no se localizó ninguno que aplique BIM‑5D a la generación y validación de análisis de precios unitarios con la estructura de costos venezolana, ni que integre el modelo geométrico, el aprendizaje automático, la codificación de partidas y la verificación automática de consistencia. Este vacío, acotado al conjunto revisado, es el que ocupa la investigación. La revisión se ampliará con los trabajos cuya referencia no pudo completarse, registrados como pendientes en la lista de referencias.

## 2.2 Bases teóricas

Las bases teóricas siguen la cadena del presupuesto que la investigación automatiza: el lugar de la estimación en el ciclo del proyecto, el modelo del que se derivan las cantidades y su nivel de integración con el activo, la estructura del análisis de precios unitarios, las técnicas de aprendizaje automático y de lenguaje natural que lo asisten y la verificación basada en reglas que lo audita.

### 2.2.1 El ciclo del proyecto y la estimación de costos

La gestión de proyectos de inversión organiza el proyecto en tres fases sucesivas: preinversión, inversión o ejecución, y operación (Miranda Miranda, s.f.) [verificación pendiente]. En la preinversión, durante los estudios de factibilidad y el diseño definitivo, se determina el presupuesto que servirá de referencia para las decisiones de inversión, contratación y control. La misma obra distingue los precios determinados por la estructura de costos de la empresa, los fijados por el mercado y los fijados con base en la competencia (Miranda Miranda, s.f.) [verificación pendiente].

Esa distinción es el puente teórico de la investigación. El análisis de precios unitarios construye un precio por estructura de costos: suma lo que cuestan los materiales, los equipos y la mano de obra necesarios para ejecutar una unidad de partida, y le agrega los gastos de administración y la utilidad. El precio de mercado, en cambio, es el que se observa en las referencias de precios publicadas. La propuesta automatiza el primero, lo verifica en su consistencia interna y lo contrasta con el segundo.

### 2.2.2 BIM y la dimensión de costos

El modelado de información de construcción (BIM) representa un proyecto como un conjunto de objetos con geometría y atributos, en lugar de un conjunto de dibujos. Su dimensión de costos, conocida como BIM‑5D, asocia esos objetos con la estimación de costos, el control de costos y los pagos del proyecto (Pishdad y Onungwa, 2024). Para la estimación, la ventaja teórica es que las cantidades de obra pueden obtenerse del propio modelo en lugar de medirse sobre planos, aunque la superioridad de esa cuantificación frente a la tradicional se examina elemento por elemento y no se da por supuesta (Wahab y Wang, 2021).

La confiabilidad del cómputo automático depende de cómo están modelados los elementos: incluso con un modelo BIM, los elementos compuestos exigen un tratamiento específico para que las cantidades sean exactas (Khosakitchalert et al., 2019). El grado de desarrollo con el que se modela cada elemento se describe mediante los niveles de desarrollo (LOD) de la especificación de BIMForum (2024) [verificación pendiente]. El nivel que debe alcanzar el modelo para que la extracción de cantidades sea confiable a efectos presupuestarios es, por eso, una de las preguntas de esta investigación.

El intercambio entre el programa de modelado y el cálculo del presupuesto se apoya en IFC, un formato abierto que puede extenderse para soportar la estimación de costos según las reglas de un sistema nacional (Ma et al., 2011) [verificación pendiente]. Adoptar IFC como frontera hace que el cómputo, el costeo y la verificación no dependan del programa con el que se construye el modelo.

### 2.2.3 BIM‑5D, sombra digital y gemelo digital

El término «gemelo digital» se emplea con frecuencia de forma imprecisa en la construcción. Sacks et al. (2020) formularon la construcción con sistemas de información de gemelo digital a partir de BIM y de la producción lean, y observaron que en edificación e infraestructura el concepto sigue poco definido. Sepasgozar (2021) presenta el gemelo digital como habilitador de la Industria 4.0 en la construcción, basado en la conexión de objetos mediante Internet de las cosas, y se propone diferenciarlo de la sombra digital y de otros modelos tridimensionales avanzados.

A partir de esa distinción, la investigación reconoce tres niveles, resumidos en la Tabla 2.1, y declara en cuál se ubica.

**Tabla 2.1**
*Niveles de integración entre el modelo y el activo*

| Nivel | Caracterización | Situación en esta investigación |
|---|---|---|
| BIM‑5D | Modelo paramétrico tridimensional con cómputo métrico automatizado, análisis de precios unitarios, presupuesto y curva de inversión asociados | Alcance obligatorio |
| Sombra digital | Lo anterior más la incorporación del avance medido en obra, con un flujo de información unidireccional del activo hacia el modelo | Alcance deseable: el registro de rendimientos medidos prepara esta realimentación |
| Gemelo digital | Lo anterior más instrumentación con sensores y realimentación bidireccional automática, que cierra un lazo de control entre el modelo y el activo | Fuera de alcance; línea de investigación futura |

*Nota.* Elaboración propia a partir de Sacks et al. (2020) y Sepasgozar (2021).

Con esta delimitación, el sistema desarrollado se denomina BIM‑5D. El término «gemelo digital» no se aplica al sistema, porque la investigación no instrumenta el activo ni cierra un lazo de control con él.

### 2.2.4 Estructura del análisis de precios unitarios en Venezuela

El análisis de precios unitarios descompone el precio de una unidad de partida en tres componentes de costo directo: materiales, equipos y mano de obra. En la práctica venezolana, la mano de obra se afecta con el factor de costos asociados al salario (FCAS), que expresa como porcentaje los costos que la contratación laboral añade al salario básico. Ese factor no es un valor único ni permanente, y los valores publicados en las guías referenciales del Colegio de Ingenieros de Venezuela son solo referenciales. Su cálculo se basa en las cláusulas económicas de la convención colectiva de la construcción (Colegio de Ingenieros de Venezuela, 2018) [verificación pendiente]. Los programas de presupuesto de uso regional lo incorporan a partir de sus bases de datos (DataLaing, s.f.).

La investigación adopta el siguiente modelo de cálculo, en el que el rendimiento se expresa en unidades de partida por día:

- **Materiales:** suma de cantidad por precio de cada material, sin dividir entre el rendimiento.
- **Equipos:** suma de cantidad por precio por factor de depreciación de cada equipo, dividida entre el rendimiento.
- **Mano de obra:** suma de cantidad por salario por (1 + FCAS) de cada categoría, más el bono de alimentación por el número de trabajadores, todo dividido entre el rendimiento.
- **Costo directo:** materiales más equipos más mano de obra.
- **Precio unitario:** costo directo por (1 + administración) y, sobre ese resultado, por (1 + utilidad).

Dos decisiones del modelo merecen explicitarse. La primera: los materiales no se dividen entre el rendimiento, porque su cantidad ya está referida a la unidad de partida, mientras que el costo diario de equipos y mano de obra sí debe repartirse entre las unidades producidas en el día. La segunda: la administración y la utilidad se aplican en cascada, es decir, la utilidad se calcula sobre el costo que ya incluye la administración, y no como suma de ambos porcentajes. En el caso didáctico, los parámetros son un FCAS de 6,00 (600 %), un bono de alimentación de 1,00 USD por trabajador y día, una administración del 15 % y una utilidad del 10 %. El FCAS se trata como parámetro del caso de estudio mientras no se confirme su fuente normativa.

### 2.2.5 Aprendizaje automático para la estimación de costos con datos escasos

La estimación de costos mediante aprendizaje automático cuenta con una revisión del estado del arte que abarca desde la inteligencia artificial hasta el modelado paramétrico (Elmousalami, 2020) y con revisiones sistemáticas de las técnicas empleadas (Tayefeh Hashemi et al., 2020) [verificación pendiente]. Entre las técnicas disponibles se encuentran la regresión, las redes neuronales y el razonamiento basado en casos, que ya se compararon para la estimación de costos de construcción (Kim et al., 2004). Los bosques aleatorios combinan numerosos árboles de decisión (Breiman, 2001); XGBoost es un sistema escalable de potenciación de árboles (Chen y Guestrin, 2016); y el razonamiento basado en casos resuelve un problema nuevo a partir de casos previos semejantes, con fundamentos metodológicos propios (Aamodt y Plaza, 1994).

La elección entre esas técnicas depende del volumen de datos disponible. Por eso la investigación declara de antemano un criterio de degradación según el número de registros de análisis de precios unitarios por dominio: con más de 200 registros se emplea XGBoost, con bosques aleatorios como contraste; entre 50 y 200, razonamiento basado en casos; y con menos de 50, un sistema de reglas con análisis de sensibilidad, declarado como limitación. El desempeño se mide con tres métricas: el error porcentual absoluto medio (MAPE), la raíz del error cuadrático medio (RMSE) y el coeficiente de determinación (R²).

La detección de valores atípicos no necesita datos etiquetados. El método de bosque de aislamiento parte de que las anomalías son pocas y diferentes y, por eso, más fáciles de aislar: construye un conjunto de árboles de partición aleatoria, y cuanto más corto es el camino necesario para aislar una observación, mayor es su grado de anomalía (Liu et al., 2008). Esa propiedad lo hace aplicable a precios y rendimientos sin un histórico previamente clasificado.

### 2.2.6 Procesamiento de lenguaje natural para la normalización de partidas

Las descripciones de partidas se redactan libremente y varían entre proyectistas, mientras que un catálogo exige asociar cada descripción con un código único. Asociarlas es un problema de similitud semántica entre textos técnicos, dominio en el que el procesamiento de lenguaje natural ya se ha aplicado a la revisión de especificaciones de construcción (Moon et al., 2022).

Sentence-BERT modifica una red preentrenada para obtener representaciones vectoriales de oraciones con significado semántico, comparables mediante la similitud del coseno, y reduce drásticamente el tiempo necesario para encontrar las oraciones más parecidas en una colección (Reimers y Gurevych, 2019). Estas representaciones pueden extenderse a varios idiomas mediante destilación de conocimiento (Reimers y Gurevych, 2020), lo que permite trabajar con descripciones en español. La similitud del coseno entre dos vectores es el cociente entre su producto escalar y el producto de sus normas: vale 1 cuando apuntan en la misma dirección y disminuye a medida que se separan.

Para esta investigación, el enfoque tiene una ventaja de diseño decisiva: la asociación entre una descripción y las partidas del catálogo se obtiene comparando representaciones de un modelo ya entrenado, sin necesidad de un conjunto de datos etiquetado por el proyecto, lo que reduce la dependencia de datos del módulo en un contexto donde esos datos escasean.

### 2.2.7 Verificación automática basada en reglas

La comprobación automática de un modelo de construcción contra un conjunto de reglas tiene una tradición propia. Eastman et al. (2009) revisaron los sistemas de comprobación de reglas que evalúan diseños de edificaciones según diversos criterios, examinaron en detalle cinco desarrollos industriales que emplean modelos IFC como entrada y organizaron las capacidades funcionales de esos sistemas en cuatro etapas, que usaron como marco de comparación. Solihin y Eastman (2015) clasificaron las reglas en cuatro clases según su complejidad computacional y lo que exigen del entorno de ejecución: las dos primeras comprueban entidades y valores explícitos del diseño y atributos derivados simples; la tercera requiere estructuras de datos extendidas; y la cuarta, demostrar una solución cuando existen varias respuestas aceptables.

Esa clasificación permite ubicar las verificaciones de esta investigación. Cada una compara magnitudes que están explícitas en el presupuesto o que se derivan de él con operaciones simples: la unidad del cómputo frente a la del análisis de precios unitarios, el acumulado de la curva de inversión frente al total del presupuesto, el factor de depreciación de un mismo equipo en distintas partidas o el balance entre excavación, concreto, tubería y relleno. Se ubican, por tanto, en las dos primeras clases, lo que permite implementarlas como funciones deterministas sobre el presupuesto, sin un motor general de comprobación de reglas.

La diferencia con los sistemas revisados está en el objeto de la comprobación. Aquellos evalúan el diseño de la edificación según criterios de diversa índole; aquí se comprueba la consistencia entre el modelo, el cómputo métrico, el análisis de precios unitarios, el presupuesto y el plan de trabajo, de modo que cada hallazgo señala la cantidad o el monto que la produce.

## 2.3 Bases normativas

Las bases normativas reúnen las tres referencias que fijan, respectivamente, cómo se codifican y miden las partidas, de dónde procede el costo laboral que entra en cada análisis de precios unitarios y contra qué marco se juzga la exactitud de una estimación.

### 2.3.1 Norma COVENIN 2000‑2: especificaciones, codificación y mediciones

La norma venezolana COVENIN 2000, en su parte II dedicada a las edificaciones, establece las especificaciones, la codificación y los criterios de medición de las partidas de construcción (COVENIN, 1999) [verificación pendiente]. Para esta investigación cumple dos funciones. En primer lugar, ofrece la codificación normalizada contra la que se asocian las descripciones de partidas redactadas libremente. En segundo lugar, fija la unidad de medida de cada partida, de modo que una discrepancia entre la unidad del cómputo métrico y la unidad del análisis de precios unitarios constituye una inconsistencia verificable, como la que presenta el caso didáctico con la tubería medida en metros y analizada por pieza.

### 2.3.2 Convención colectiva de la industria de la construcción

La convención colectiva de trabajo de la industria de la construcción establece las cláusulas económicas de la relación laboral en el sector y es la base sobre la que se calcula el FCAS (Colegio de Ingenieros de Venezuela, 2018) [verificación pendiente]. La más reciente localizada corresponde a 2023, publicada en Gaceta Oficial Extraordinaria, y se aplica a las empresas afiliadas a las cámaras de la construcción (Convención Colectiva de la Industria de la Construcción, s.f.) [verificación pendiente].

Mientras no se confirme su período de vigencia en la fuente oficial, esta investigación no deriva el valor del FCAS de la convención: lo trata como un parámetro del caso de estudio, explícito y modificable, en coherencia con la advertencia, recogida en la sección 2.2.4, de que el FCAS no es un valor único ni permanente. Esa decisión mantiene el modelo de cálculo válido para cualquier convención vigente, porque el factor entra como dato y no como constante del cálculo.

### 2.3.3 Clasificación de estimaciones de costos de AACE International

La práctica recomendada 18R‑97 de AACE International clasifica las estimaciones de costos en cinco clases. Lo que determina la clase es la madurez de la definición del proyecto, que se juzga por el estado de sus entregables clave de planificación y diseño y no por un porcentaje de avance; cada clase asocia, además, un uso típico, una metodología y un rango de exactitud (AACE International, 2020b). La clase 3 corresponde a una definición de entre el 10 % y el 40 % y a la autorización o el control del presupuesto. Su rango típico de exactitud va de −10 % a −20 % en el extremo inferior y de +10 % a +30 % en el superior; la misma práctica advierte que el rango debe determinarse mediante el análisis de riesgo del proyecto específico y que, con una contingencia adecuadamente tratada, cerca del 80 % de los proyectos cae dentro de los rangos indicados (AACE International, 2020b).

La investigación adopta la clase 3 como marco de contraste externo, declarado de antemano: sin una clase declarada, una desviación no podría calificarse como aceptable o inaceptable. El sistema emplea los extremos de su rango, −20 % y +30 %. Como la clase la determina la madurez de los entregables, que el cómputo se derive de un modelo tridimensional no basta para asignarla; la asignación debe justificarse con la madurez de los entregables del caso de estudio, justificación que corresponde al marco metodológico.

La 18R‑97 se formula para las industrias de proceso. AACE International mantiene una práctica específica para la edificación y la construcción general, la 56R‑08 (AACE International, 2020a) [verificación pendiente], cuyo ámbito corresponde al del caso de estudio. Mientras no se contraste el rango que esa práctica asigna a la clase 3, el contraste se realiza con el de la 18R‑97, que es el declarado en la especificación de requisitos del sistema.

## 2.4 Definición de términos

Los términos se definen en el sentido en que se emplean en esta investigación; cuando un concepto se desarrolla en las secciones anteriores, se indica dónde.

- **Administración.** Porcentaje que se aplica sobre el costo directo para cubrir los gastos generales de la empresa. En el modelo de cálculo precede a la utilidad, que se calcula sobre el costo que ya la incluye (sección 2.2.4).
- **Análisis de precios unitarios (APU).** Descomposición del precio de una unidad de partida en materiales, equipos y mano de obra, más administración y utilidad; construye un precio por estructura de costos (secciones 2.2.1 y 2.2.4).
- **Aprendizaje automático.** Conjunto de técnicas que ajustan un modelo a partir de datos para estimar, clasificar o detectar patrones sin programar cada regla de forma explícita (sección 2.2.5).
- **BIM (modelado de información de construcción).** Representación de un proyecto como un conjunto de objetos con geometría y atributos, en lugar de un conjunto de dibujos (sección 2.2.2).
- **BIM‑5D.** Dimensión de costos de BIM, que asocia los objetos del modelo con la estimación, el control de costos y los pagos; nivel en el que se ubica el sistema desarrollado (secciones 2.2.2 y 2.2.3).
- **Bono de alimentación.** Monto que se paga por trabajador y por día, y que en el modelo de cálculo se suma al costo diario de la mano de obra antes de dividir entre el rendimiento (sección 2.2.4).
- **Clase de estimación.** Categoría de la clasificación de AACE International que se determina por la madurez de la definición del proyecto y a la que se asocia un rango típico de exactitud (sección 2.3.3).
- **Cómputo métrico.** Medición de las cantidades de obra de cada partida, en la unidad que establece su codificación.
- **Costo directo.** Suma de los costos de materiales, equipos y mano de obra de una unidad de partida.
- **Curva de inversión.** Representación del gasto acumulado del presupuesto a lo largo del plan de trabajo; cierra en el total del presupuesto cuando el plan es consistente con él.
- **Depreciación de equipos.** Factor mayor que cero y no mayor que uno con el que se imputa a una partida la fracción del costo de un equipo que le corresponde; un mismo equipo debe llevar el mismo factor en todas las partidas.
- **Factor de costos asociados al salario (FCAS).** Porcentaje que expresa los costos que la contratación laboral añade al salario básico y que afecta el costo de la mano de obra; no es un valor único ni permanente (secciones 2.2.4 y 2.3.2).
- **Gemelo digital.** Modelo de un activo conectado con él mediante instrumentación y con realimentación bidireccional automática, que cierra un lazo de control; queda fuera del alcance de esta investigación (sección 2.2.3).
- **IFC.** Formato abierto de intercambio de modelos de información de construcción, que en esta investigación separa el modelado del cálculo del presupuesto (sección 2.2.2).
- **Métricas de desempeño.** El error porcentual absoluto medio (MAPE), la raíz del error cuadrático medio (RMSE) y el coeficiente de determinación (R²), con los que se evalúa la estimación de precios (sección 2.2.5).
- **Nivel de desarrollo (LOD).** Grado de desarrollo con el que se modela la geometría y la información de un elemento del modelo (sección 2.2.2).
- **Normalización semántica de partidas.** Asociación de una descripción de partida redactada libremente con las partidas del catálogo mediante la similitud entre sus representaciones vectoriales (sección 2.2.6).
- **Partida.** Unidad de obra con código, descripción y unidad de medida, sobre la que se construye un análisis de precios unitarios.
- **Rendimiento.** Cantidad de unidades de partida que se producen por día; divide el costo diario de equipos y mano de obra, pero no el de los materiales (sección 2.2.4).
- **Similitud del coseno.** Cociente entre el producto escalar de dos vectores y el producto de sus normas; vale 1 cuando los vectores apuntan en la misma dirección (sección 2.2.6).
- **Sombra digital.** Modelo que incorpora el avance medido en obra con un flujo de información unidireccional del activo hacia el modelo; alcance deseable de esta investigación (sección 2.2.3).
- **Trazabilidad.** Propiedad por la cual cada cantidad del presupuesto conserva su procedencia, de modo que puede reevaluarse desde su origen.
- **Utilidad.** Porcentaje que se aplica sobre el costo que ya incluye la administración para obtener el precio unitario (sección 2.2.4).
- **Valor atípico.** Observación que se aparta del comportamiento del resto de los datos; en esta investigación, un precio o un rendimiento que se aleja de su histórico (sección 2.2.5).
- **Verificación de consistencia.** Comprobación automática de que magnitudes relacionadas entre sí, como la geometría, el cómputo, el análisis de precios unitarios, el presupuesto y la curva de inversión, concuerdan según reglas declaradas (sección 2.2.7).
