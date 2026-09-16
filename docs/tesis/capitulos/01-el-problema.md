# Capítulo I — El problema

| Capítulo | Estado | Última revisión |
|---|---|---|
| I. El problema | borrador completo, revisado en la Sesión R1.3 ([acta](../revisiones/R1-capitulo-1.md)); pendiente la revisión del tutor académico | 2026-09-15 |

## 1.1 Planteamiento del problema

### 1.1.1 La estimación de costos y la cadena que la sostiene

La estimación de costos articula la formulación técnica de un proyecto con su evaluación financiera. En el ciclo del proyecto, el presupuesto se determina durante la preinversión y se convierte en la referencia de las decisiones posteriores de inversión, contratación y control (Miranda Miranda, s.f.) [verificación pendiente]. Por esa posición en el ciclo, un error del presupuesto no se corrige en las fases siguientes: se propaga hacia el flujo de fondos y hacia los indicadores con los que se decide si el proyecto se ejecuta.

En el procedimiento tradicional, el presupuesto de obra resulta de una cadena de artefactos que deberían derivarse unos de otros: el plano, el cómputo métrico, el análisis de precios unitarios (APU), el presupuesto y el plan de trabajo con su curva de inversión. Cada eslabón se elabora en un soporte distinto, como el plano en un programa de dibujo, el cómputo en una hoja de cálculo y el APU en un programa especializado, y la información pasa de uno a otro por transcripción manual. La cuantificación sigue haciéndose mayormente de forma manual o sobre planos bidimensionales, y la literatura ha comenzado a compararla, elemento por elemento, con la cuantificación derivada de modelos de información de construcción (BIM) para establecer cuál de los dos procedimientos conviene (Wahab y Wang, 2021). En la dimensión de costos de esos modelos persisten, además, la falta de integración entre los modelos BIM‑5D, el seguimiento del avance y los sistemas de pago, y la falta de estandarización en el uso de los elementos del modelo (Pishdad y Onungwa, 2024).

En Venezuela, la estructura del APU añade condiciones que agravan la situación. El costo de la mano de obra incorpora el factor de costos asociados al salario (FCAS), elevado y variable por su dependencia de la convención colectiva vigente (Convención Colectiva de la Industria de la Construcción, s.f.) [verificación pendiente], a lo que se suman el bono de alimentación, los factores de depreciación de los equipos y, con la dolarización de hecho de la economía, la necesidad de operar en bolívares y en divisas. Los programas de presupuesto de uso regional resuelven estas particularidades del cálculo: incorporan el FCAS, los índices de precios del Banco Central de Venezuela, la conversión entre bolívares y dólares, el recálculo de los precios unitarios ante cambios de sus parámetros y la reconsideración de precios mediante fórmulas polinómicas (DataLaing, s.f.; IP-3 Software, s.f.; Lulo Software, s.f.) [verificación pendiente]. Sin embargo, trabajan con las cantidades que el usuario introduce en cada partida, y su documentación funcional no describe una comprobación de esas cantidades contra la geometría del proyecto.

### 1.1.2 Un caso didáctico: cómo se producen los errores

Para examinar el mecanismo del problema se empleó un caso didáctico: el presupuesto de la obra civil del sistema de drenaje de una clínica, con 24 m de tubería de PVC de 4", cuatro tanquillas de inspección de 0,80 × 0,80 × 0,80 m con paredes de 0,10 m, cinco partidas y un total de 1 586,61 USD. Se trata de un ejercicio académico ficticio: reproduce el contenido y el formato de un presupuesto elaborado por el procedimiento tradicional en Venezuela, pero no corresponde a una obra ejecutada y sus valores no son reales. Su utilidad, por tanto, no es estimar con qué frecuencia se equivoca la práctica, sino mostrar cómo aparecen errores que la revisión del presupuesto final no detecta.

La revisión del caso consistió en recalcular cada cantidad a partir de las dimensiones declaradas en su memoria de cálculo y en contrastar el resultado con los valores empleados en el cómputo, el presupuesto y el plan de trabajo. Se identificaron siete inconsistencias, resumidas en la Tabla 1.1.

**Tabla 1.1**
*Inconsistencias identificadas en el caso didáctico del sistema de drenaje*

| N.º | Elemento | Valor empleado | Valor esperado | Consecuencia |
|---|---|---|---|---|
| 1 | Encofrado | 5,92 m² por tanquilla (23,68 m² en total) | 4,48 m² por tanquilla (17,92 m² en total) | sobreestimación del 32 %; el valor 5,92 no se justifica en la memoria |
| 2 | Concreto | 0,415 m³ por tanquilla (1,66 m³ en total) | 0,224 m³ por tanquilla (0,896 m³ en total) | sobreestimación del 85 % en la partida de mayor precio unitario |
| 3 | Curva de inversión | cierra en 1 575,50 USD (99,30 %) | 1 586,61 USD (100 %) | 11,11 USD sin conciliar entre plan de trabajo y presupuesto |
| 4 | Unidades | cómputo de la tubería en metros | APU de la tubería por pieza | incompatibilidad dimensional entre el cómputo y el APU que lo consume |
| 5 | Diámetro | 3/4" en la memoria de cálculo | 4" en el proyecto y en el APU | error de transcripción que sobrevive sin validación cruzada |
| 6 | Relleno | 1,30 m³ | excavación menos concreto y tubería, ≈ 8,6 m³ | balance volumétrico incoherente |
| 7 | Depreciación | factor 0,03 para el vehículo en un APU y 1,00 en los demás | un factor por equipo con criterio declarado | regla de imputación de equipos no reproducible |

*Nota.* Elaboración propia a partir del ejercicio académico de la clínica; el detalle de cada valor está en el documento de línea base del sistema.

Ninguna de las siete inconsistencias se aprecia leyendo el presupuesto final: el total cuadra con la suma de sus partidas y cada precio unitario es aritméticamente correcto. Todas exigen rehacer el cómputo desde la geometría o contrastar entre sí documentos que el procedimiento tradicional mantiene separados. La transcripción del ejercicio mostró, además, dos hechos que refuerzan esa lectura: el encofrado se computó en metros cúbicos cuando su APU está expresado en metros cuadrados, y cada monto diario del plan de trabajo es menor que el de su partida, de modo que la suma de esas diferencias explica la brecha de 11,11 USD de la curva de inversión.

El fenómeno no es exclusivo de un tipo de obra. Un segundo ejercicio académico, correspondiente a una red de telecomunicaciones, presenta la misma patología en un solo documento: el tubo corrugado figura con 80 m en el cómputo métrico y con 90 m en el presupuesto. En ambos casos la discrepancia nace del mismo lugar, la transcripción manual entre dos tablas que deberían describir la misma cantidad.

### 1.1.3 Naturaleza del problema

Las inconsistencias del caso didáctico no se atribuyen a la impericia de quien elaboró el presupuesto. Comparten un origen estructural: la información se transfiere manualmente entre soportes que no se comunican, y no existe una instancia que verifique que el cómputo derive de la geometría del proyecto, que las unidades del cómputo coincidan con las del APU, que el criterio de depreciación de un equipo sea el mismo en todas las partidas ni que el presupuesto cierre contra su plan de trabajo.

El problema, en consecuencia, no es de cálculo sino de trazabilidad. La cadena que va del plano al presupuesto está interrumpida en varios puntos, y esa interrupción hace que los errores sean indetectables por los medios de revisión habituales, que examinan el documento final y no su procedencia. Los programas de presupuesto disponibles resuelven con solvencia la aritmética del APU; lo que su documentación no describe es la comprobación de que las cantidades que reciben correspondan a la geometría del proyecto.

Resolver este problema requiere un procedimiento en el que cada cantidad del presupuesto conserve su procedencia, de modo que pueda reevaluarse desde su origen; en el que las verificaciones de consistencia entre geometría, cómputo, APU, presupuesto y plan de trabajo se ejecuten de forma automática; y en el que el precio construido por estructura de costos pueda contrastarse con precios de referencia del mercado.

El alcance de esta evidencia debe precisarse. La prevalencia de estos errores en obras reales no puede establecerse con casos didácticos y queda declarada como limitación de la investigación: los casos muestran el mecanismo, no su frecuencia.

## 1.2 Formulación del problema

A partir del planteamiento anterior, la investigación se orienta por la siguiente pregunta principal:

¿Cómo automatizar la cadena de trazabilidad desde el modelo geométrico tridimensional hasta el presupuesto de obra, de manera que los análisis de precios unitarios resultantes sean verificables en su consistencia interna y contrastables con precios de referencia del mercado venezolano?

De ella se derivan las siguientes preguntas secundarias:

1. ¿Qué nivel de desarrollo debe alcanzar el modelo tridimensional para que la extracción automática de cantidades sea confiable a efectos presupuestarios?
2. ¿Qué reglas paramétricas permiten derivar las cantidades de obra de las instalaciones sanitarias directamente de la geometría, sin intervención manual?
3. ¿Qué técnica de aprendizaje automático resulta más adecuada para clasificar partidas y estimar precios unitarios cuando la disponibilidad de datos es limitada?
4. ¿Qué verificaciones automáticas de consistencia pueden implementarse a partir del conocimiento geométrico que un programa de presupuesto convencional no posee?
5. ¿Qué grado de exactitud alcanza el presupuesto generado automáticamente frente al elaborado por el procedimiento tradicional, medido según las clases de estimación de AACE International?
6. ¿Puede extenderse el modelo a otros dominios de la ingeniería, como las telecomunicaciones, el mantenimiento industrial y los sistemas de información, sin modificar su núcleo de cálculo y de verificación? *(Esta pregunta corresponde a la variante A de los objetivos; en la variante B, la extensibilidad se examina como resultado complementario y no como pregunta de investigación.)*

## 1.3 Objetivos de la investigación

Los objetivos se presentan en dos variantes porque el alcance de la investigación depende de una decisión pendiente con la tutoría: si la extensibilidad del modelo a otros dominios de la ingeniería constituye un objetivo específico (variante A, con un OE7) o un resultado complementario del diseño (variante B). Ambas variantes comparten los seis objetivos específicos que se listan a continuación de ellas; la elección entre una y otra no altera su redacción.

### Variante A — la extensibilidad multidominio como objetivo

**Objetivo general.** Desarrollar un modelo BIM‑5D asistido por aprendizaje automático para la generación y validación de análisis de precios unitarios, extensible a otros dominios de la ingeniería sin modificar su núcleo, aplicado al caso didáctico de la obra civil del sistema de drenaje de una clínica.

**Objetivos específicos.** Los seis objetivos comunes (OE1 a OE6) y, además:

- **OE7.** Validar la extensibilidad del modelo a otros dominios de la ingeniería mediante adaptadores que no modifiquen su núcleo de cálculo y de verificación.

### Variante B — la extensibilidad como resultado complementario

**Objetivo general.** Desarrollar un modelo BIM‑5D asistido por aprendizaje automático para la generación y validación de análisis de precios unitarios en proyectos de instalaciones sanitarias, aplicado al caso didáctico de la obra civil del sistema de drenaje de una clínica.

**Objetivos específicos.** Los seis objetivos comunes (OE1 a OE6). En esta variante, la extensibilidad a otros dominios se presenta en el capítulo V como resultado complementario del diseño del núcleo de cálculo (OE3), sin constituir un objetivo de la investigación.

### Objetivos específicos comunes a ambas variantes

- **OE1.** Diagnosticar las inconsistencias del procedimiento tradicional de cómputo métrico, análisis de precios unitarios y presupuesto a partir de casos didácticos, estableciendo una línea base cuantificada de inconsistencias y de tiempos de elaboración.
- **OE2.** Estructurar el modelo tridimensional paramétrico del sistema de instalaciones sanitarias y su procedimiento de extracción automática de cantidades de obra en formato abierto IFC.
- **OE3.** Diseñar la base de datos de partidas, rendimientos e insumos bajo codificación COVENIN, incorporando de forma explícita las reglas de cálculo del factor de costos asociados al salario, el bono de alimentación y la depreciación de equipos.
- **OE4.** Implementar los módulos de aprendizaje automático para la normalización semántica de descripciones de partidas, la detección de valores atípicos y la estimación de precios unitarios con la técnica que permita la disponibilidad de datos.
- **OE5.** Desarrollar el sistema de verificación automática de consistencia entre geometría, cómputo métrico, análisis de precios unitarios, presupuesto y curva de inversión.
- **OE6.** Evaluar la exactitud y el desempeño del modelo frente al presupuesto de referencia corregido del caso didáctico y frente a precios de referencia publicados, empleando las clases de estimación de AACE International como marco de contraste.

### Correspondencia entre preguntas, objetivos y fases

Cada objetivo específico atiende una pregunta de investigación y se materializa en una fase con un producto verificable, como se resume en la Tabla 1.2.

**Tabla 1.2**
*Correspondencia entre preguntas de investigación, objetivos específicos y fases*

| Pregunta | Objetivo | Fase | Producto verificable |
|---|---|---|---|
| Principal: establecer el punto de partida contra el que se mide la respuesta | OE1 | I. Diagnóstico | línea base cuantificada de inconsistencias del caso didáctico y registro de tiempos de elaboración |
| Secundaria 1: nivel de desarrollo del modelo | OE2 | II. Modelado y extracción | modelo IFC paramétrico y rutina de extracción de cantidades |
| Secundaria 2: reglas paramétricas que derivan las cantidades | OE2 | II. Modelado y extracción | reglas paramétricas trazables asociadas a cada cantidad |
| Principal: análisis de precios unitarios verificables | OE3 | III. Base de datos y motor de costos | base de datos de partidas y motor de costos con FCAS, bono y depreciación explícitos |
| Secundaria 3: técnica de aprendizaje automático con datos limitados | OE4 | IV. Aprendizaje automático | módulos de normalización, detección de atípicos y estimación de precios |
| Secundaria 4: verificaciones que aporta el conocimiento geométrico | OE5 | V. Verificación | sistema de auditoría automática y su informe |
| Secundaria 5: exactitud según AACE International | OE6 | VI. Evaluación | informe de resultados frente a la referencia corregida y a precios de referencia publicados |
| Secundaria 6 (solo variante A): extensibilidad a otros dominios | OE7 | transversal a las fases III y VI | adaptadores de telecomunicaciones, mantenimiento industrial y sistemas con el núcleo sin modificar |

*Nota.* Elaboración propia. OE1 y OE3 atienden la pregunta principal y no una secundaria: el diagnóstico fija la línea base contra la que se evalúa la respuesta, y la base de datos con su motor de costos es la condición para que los análisis de precios unitarios sean verificables.

## 1.4 Justificación

### 1.4.1 Justificación técnica

Las inconsistencias del caso didáctico son la consecuencia previsible de transcribir información de forma manual entre soportes desconectados. Un procedimiento que derive las cantidades de las reglas paramétricas del modelo haría imposibles por construcción seis de las siete: el encofrado, el concreto y el relleno no podrían adoptar valores ajenos a la geometría; la unidad y el diámetro se heredarían del objeto modelado; y la curva de inversión, generada a partir del propio presupuesto, cerraría por definición. La séptima, el criterio de depreciación de los equipos, no depende de la geometría y exige una regla de verificación que compare el mismo equipo entre partidas. El aporte técnico consiste, por tanto, en que la mayor parte de los errores deje de ser posible, en lugar de detectarse después de cometidos, y en que los restantes se detecten de forma automática.

### 1.4.2 Justificación metodológica

La investigación articula tres campos que la literatura ha desarrollado de manera predominantemente separada: la automatización del cómputo métrico a partir de modelos BIM, la aplicación del aprendizaje automático a la estimación de costos y la particularidad normativa y económica del análisis de precios unitarios en Venezuela. La revisión de antecedentes del capítulo II no identificó trabajos que integren los tres. A ello se suma una decisión de método: dado que la literatura advierte que las redes neuronales dependen fuertemente del volumen de datos y rinden mal con conjuntos pequeños (Tayefeh Hashemi et al., 2020) [verificación pendiente], la investigación declara de antemano los criterios con los que la técnica predictiva se degrada según los datos disponibles, en lugar de ajustarlos después de conocer los resultados.

### 1.4.3 Justificación práctica

El producto está orientado a oficinas de proyecto y a unidades de control de obra. La capa de verificación automática es independiente del resto del sistema, de modo que puede aplicarse a presupuestos elaborados por el procedimiento tradicional, lo que amplía su utilidad más allá del caso de estudio. Además, cada cantidad conserva su procedencia y cada hallazgo de la auditoría señala los elementos involucrados, lo que convierte la revisión de un presupuesto en una tarea reproducible y no dependiente del criterio de quien la ejecuta.

### 1.4.4 Justificación institucional

La incorporación de BIM en la práctica venezolana es incipiente, y el Colegio de Ingenieros de Venezuela ha impulsado una propuesta orientada a un plan nacional para su adopción (Colegio de Ingenieros de Venezuela, s.f.) [verificación pendiente]. La investigación se inscribe en esa dirección con un componente que los flujos BIM‑5D de uso internacional no resuelven de forma nativa: la articulación entre el modelo de información y la estructura de costos derivada de la normativa laboral venezolana.

## 1.5 Alcance y delimitación

### 1.5.1 Delimitación del objeto de estudio

La Tabla 1.3 resume las dimensiones que delimitan la investigación.

**Tabla 1.3**
*Delimitación de la investigación*

| Dimensión | Delimitación |
|---|---|
| Temática | Estimación de costos de obra civil asociada a instalaciones sanitarias. En la variante A de los objetivos se incluyen, además, los dominios de telecomunicaciones, mantenimiento industrial y sistemas de información como prueba de extensibilidad. |
| Caso de estudio | Caso didáctico del sistema de drenaje de una clínica: 24 m de tubería de PVC de 4" y cuatro tanquillas de inspección de 0,80 × 0,80 × 0,80 m con paredes de 0,10 m. |
| Partidas | Cinco: excavación, suministro e instalación de tubería, encofrado, vaciado de concreto y relleno compactado. |
| Normativa | Codificación de partidas según la Comisión Venezolana de Normas Industriales (COVENIN, 1999) [verificación pendiente]; FCAS según la convención colectiva de la industria de la construcción (Convención Colectiva de la Industria de la Construcción, s.f.) [verificación pendiente], tratado como parámetro del caso de estudio mientras no se confirme su fuente. |
| Temporal | Precios del caso didáctico con la fecha declarada en el ejercicio y referencia de precios MaPreX de julio de 2026 (DataLaing, s.f.) [verificación pendiente], expresados en dólares. |
| Tecnológica | El formato abierto IFC es la frontera entre el modelado y el procesamiento; el cómputo, el costeo y la verificación no dependen del programa con el que se modela. |

*Nota.* Elaboración propia.

### 1.5.2 Lo que la investigación no comprende

La delimitación de lo excluido es tan relevante como la de lo incluido, porque previene observaciones sobre alcance no cumplido:

- **Gemelo digital en sentido estricto.** No se instrumenta el activo con sensores ni se implementa una realimentación bidireccional automática. La distinción entre BIM‑5D, sombra digital y gemelo digital se desarrolla en el capítulo II.
- **Digitalización automática de planos.** El reconocimiento de símbolos en planos escaneados constituye un problema de investigación en sí mismo; el modelo se construye a partir de las dimensiones declaradas en la memoria de cálculo.
- **Evaluación financiera del proyecto de inversión.** El análisis de rentabilidad asociado al caso no forma parte del objeto de estudio.
- **Generalización estadística.** Con un diseño de caso único, los resultados no se extrapolan por inferencia estadística; su transferibilidad se apoya en la replicabilidad documentada del procedimiento.
- **Validación con presupuestos reales.** Los casos disponibles son didácticos: la exactitud se mide frente a la referencia corregida del caso y frente a precios de referencia publicados, no frente a obras ejecutadas. La validación con presupuestos reales queda como limitación hasta disponer de ellos.
