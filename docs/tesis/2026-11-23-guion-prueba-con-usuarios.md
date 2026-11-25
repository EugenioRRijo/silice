# Guion de la prueba con usuarios (semana 1 del plan del consejo)

> Para Eugenio. Ningún dato de esta prueba entra al repositorio: las hojas llenas, los nombres y las grabaciones se
> quedan en el equipo (NORMAS §1). En la tesis se reportan cifras agregadas y citas sin nombre.

## Cómo encaja en el anteproyecto (v8)

- **Es una prueba formativa**: sirve para ajustar el prototipo durante el diagnóstico (fases 1 a 3). No reemplaza la
  evaluación del objetivo 4, que sigue siendo el cuasiexperimento cruzado de la fase 4.
- **El SUS no figura entre los 4 instrumentos del v8.** Para que sus resultados entren en la tesis, el v8 debe
  declararlo en la metodología como quinto instrumento. Es un cuestionario estandarizado: no se valida su contenido,
  pero se usa una versión en español publicada y validada (Sevilla-Gonzalez et al., 2020; verificada el 2026-11-24
  en [referencias.md](referencias.md)). Lo que sí deben validar los 3 expertos del v8 son las 3 tareas y la hoja de
  observación. La prueba de comprensión de las alertas (6 tarjetas y su hoja de registro, agregada el 2026-11-24) es
  otro instrumento propio: si su resultado entra en la tesis, la validan del mismo modo (**por confirmar con
  Eugenio**).
- **Separación de papeles (v8, §8):** los expertos que validan los instrumentos no participan en la medición. Por eso
  ningún participante de esta prueba puede ser uno de esos 3 expertos.

## Qué se quiere saber

1. Si un economista termina, **sin ayuda**, las tareas de todos los días en Sílice (eficacia).
2. Cuánto tarda y dónde se traba (eficiencia).
3. Qué tan usable le parece, medido con el cuestionario SUS (satisfacción).
4. Si entiende lo que dicen 6 alertas reales de Sílice y qué haría ante cada una (prueba de comprensión de las
   alertas).

Las tres primeras son las dimensiones de usabilidad de la norma ISO 9241-11: eficacia, eficiencia y satisfacción.

## Quiénes y cuántos

- Los 3 economistas que elaboran y revisan los presupuestos viales de la empresa del caso: es la población censal del
  v8. Con 5 personas se ve la mayoría de los problemas grandes (Nielsen y Landauer, 1993); con 3, se declara como límite.
  [docs/ESTADO.md](../ESTADO.md) §4 encarga conseguir 5 personas para el SUS: si se suman participantes que no son los
  3 economistas, se informan aparte (**por confirmar con Eugenio**).
- La medición de la auditoría es otro protocolo (errores sembrados y kappa de Cohen, v8 §8) y otra sesión.
- Sesión individual de unos 45 minutos, en el equipo de Eugenio, con Sílice abierto en una carpeta de demostración (datos
  ficticios).

## Quién conduce cada parte y en qué orden

| Orden | Parte | Quién la conduce |
|---|---|---|
| 1 | Consentimiento informado (hoja firmada) | Eugenio |
| 2 | Tareas T1 a T3 con la hoja de observación | Eugenio, autor del sistema (se declara como límite) |
| 3 | Prueba de comprensión de las 6 alertas (A1 a A6) | Una persona que no construyó Sílice ni es uno de los 3 expertos |
| 4 | Cuestionario SUS y pregunta final abierta | Lo responde el participante solo, sin ayuda |

## Antes de la sesión (Eugenio)

- [ ] Fusionar #138, #139 y #140, y abrir Sílice con la carpeta de demostración.
- [ ] Una hoja de observación impresa por participante (abajo), un cronómetro y el SUS impreso.
- [ ] Las 6 tarjetas de las alertas, copiadas de la pantalla real con la versión congelada, y una hoja de registro de
  la prueba de comprensión por participante.
- [ ] Confirmar a la persona que conduce la prueba de comprensión de las alertas.
- [ ] No explicar cómo se usa Sílice: la prueba mide si se entiende solo.

## Consentimiento (leer en voz alta)

«Gracias por ayudarme. Voy a probar el programa, no a usted: si algo no sale, es un problema del programa. Le voy a pedir
unas tareas; piense en voz alta mientras las hace. Yo no puedo ayudarle durante la tarea. Anoto tiempos y comentarios, sin
su nombre, y los resultados van en mi trabajo de grado solo como cifras generales. Puede parar cuando quiera. ¿Está de
acuerdo?»

## Las tareas

Se leen una a una. Cada una empieza con Sílice en la Vista general.

| # | Tarea (se lee así) | Termina cuando… | Tiempo máximo |
|---|---|---|---|
| T1 | «Abra la obra de demostración y vea cuánto cuesta su presupuesto.» | Lee el total en voz alta | 5 min |
| T2 | «Cree una partida nueva, por ejemplo un friso de pared, con al menos un material y la mano de obra, y déjela en el presupuesto de esta obra con una cantidad de 50.» | La fila aparece en el presupuesto con su cantidad | 15 min |
| T3 | «Diga si el presupuesto tiene algún problema que conviene revisar, y cuál.» | Nombra un hallazgo de Revisión o dice con razones que no hay | 5 min |

Si al llegar al tiempo máximo no terminó: se para, se anota «no terminó» y se sigue con la siguiente.

## Hoja de observación (una por participante)

Participante: E__ (nunca el nombre) · Fecha: ____ · Experiencia presupuestando: ____ años · ¿Usa Excel a diario? Sí / No

| Tarea | Resultado (sin ayuda / con una pista / no terminó) | Tiempo (min:s) | Dónde se trabó (pantalla y paso) | Lo que dijo (textual) |
|---|---|---|---|---|
| T1 | | | | |
| T2 | | | | |
| T3 | | | | |

Una «pista» solo se da si la persona está trabada más de 2 minutos, y se anota exactamente qué se dijo.

## Cuestionario SUS (al final, sin ayuda)

Marque del 1 (muy en desacuerdo) al 5 (muy de acuerdo).

| # | Afirmación | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 1 | Creo que me gustaría usar este programa con frecuencia. | | | | | |
| 2 | El programa me pareció innecesariamente complicado. | | | | | |
| 3 | El programa me pareció fácil de usar. | | | | | |
| 4 | Creo que necesitaría la ayuda de una persona con conocimientos técnicos para usarlo. | | | | | |
| 5 | Las funciones del programa están bien integradas. | | | | | |
| 6 | El programa me pareció muy inconsistente. | | | | | |
| 7 | Imagino que la mayoría de la gente aprendería a usarlo muy rápido. | | | | | |
| 8 | El programa me pareció muy difícil de usar. | | | | | |
| 9 | Me sentí muy seguro al usar el programa. | | | | | |
| 10 | Necesité aprender muchas cosas antes de poder usar el programa. | | | | | |

**Cómo se calcula** (Brooke, 1996):
- en los ítems impares, se resta 1 a la respuesta;
- en los pares, se calcula 5 menos la respuesta;
- se suman los 10 resultados y la suma se multiplica por 2,5.

El puntaje va de 0 a 100. Como referencia, el promedio publicado ronda 68 (Sauro y Lewis): por encima es mejor que el
promedio.

Pregunta final abierta: «¿Qué fue lo que más le costó?» (se anota textual).

## Después de la sesión

1. Pasar los tiempos, los resultados y el SUS a una planilla **local**, fuera del repositorio.
2. Cada vez que alguien se trabó, agregar una fila en la tabla de errores de `.agents/skills/interfaz-silice/SKILL.md` con
   la frase textual y sin el nombre. Si la regla se puede medir, se agrega a la guardia.
3. Semana 2: arreglar **solo** lo que falló en estas sesiones (plan del consejo), en orden de gravedad: primero lo que
   impidió terminar una tarea.

## Lo que va a la tesis

- Por tarea: el porcentaje que terminó sin ayuda, el tiempo mediano y los puntos donde se trabaron (Tabla 4.3 del
  [esqueleto del capítulo IV](2026-11-23-esqueleto-capitulo-resultados.md)).
- Las alertas: por cada una, cuántos la entendieron (sí, a medias o no), las acciones que dijeron que tomarían y las
  respuestas a «¿Qué alerta le faltó?», sin nombres (Tabla 4.3b).
- El SUS: el promedio y el rango, con la referencia publicada de 68.
- Los límites: 3 participantes, datos de demostración y que las tareas T1 a T3 las conduce el autor del sistema; la
  prueba de comprensión de las alertas, en cambio, la conduce una persona que no construyó Sílice.

## Prueba de comprensión de las alertas (2026-11-24)

Este bloque se aplica **después de las tareas T1 a T3 y antes del cuestionario SUS**, para saber si usted
comprende lo que dicen las alertas reales de Sílice y qué acción tomaría ante cada una (acta del consejo del
2026-11-24).

- **Quién la conduce:** una persona que **no construyó Sílice** ni escribió sus reglas o textos de pantalla
  (tampoco uno de los 3 expertos que validan los instrumentos). Así se evita que el autor aclare de más o guíe
  las respuestas.
- **Cómo se aplica:** se muestran las 6 alertas una por vez, tal como aparecen en pantalla (en el equipo de
  prueba o en tarjetas impresas). Quien conduce **no explica** el significado de ninguna alerta ni corrige lo
  que usted responda.
- **Duración de este bloque:** por confirmar con Eugenio antes de las sesiones.

### Las 6 alertas reales que se muestran

Los textos reproducen los formatos reales de pantalla de Sílice (`fusion/alertas.py`,
`aplicacion/nombres_reglas.py`, `adapters/hoja_empresa/reglas.py`, `adapters/hoja_empresa/reglas_calculo.py` y
la vista de causas raíz) sobre un **caso ficticio de demostración** (nunca datos reales de empresa). El umbral
de 5,00 % en las alertas de precio es el valor por omisión del programa.

1. **A1 · Sin fuente** (`fusion/alertas.py`):
   > **Sin fuente** · `MT-04`
   > la FUENTE de MT-04 dice «POR COTIZAR»: el precio (INSUMOS!E12) no se puede rastrear
2. **A2 · Base de la empresa** (`fusion/alertas.py`):
   > **Base de la empresa** · `MT-08`
   > el libro usa 18,00 USD; precio propio de la instalación 15,00 USD del 2026-10-15: +20,00 %, pasa del umbral
   > de 5,00 %
3. **A3 · USD-Bs** (`fusion/alertas.py`):
   > **USD-Bs** · `MT-08`
   > 900,00 Bs al 2026-10-01 (tasa 50,00) y 990,00 Bs al 2026-11-24 (tasa 55,00): +10,00 %, pasa del umbral de
   > 5,00 %
4. **A4 · Componente fuera del total (L4)** (`aplicacion/nombres_reglas.py`):
   > **APU-02!G36 · Error · Componente fuera del total (L4) · 1.265,00**
   > Costo directo de APU-02 (partida 2): la fórmula APU-02!G36 =SUM(G32:G34) deja fuera transporte y disposición
   > (APU-02!G35, 10 USD/u). El CD guardado es 90 USD/u y la suma de materiales, mano de obra, equipos y
   > transporte es 100 USD/u. Efecto: con administración (0,15) y utilidad (0,1) del APU y la cantidad 100, la
   > partida queda corta en 1.265,00 USD sin IVA.
5. **A5 · Referencia rota o externa (L5)** (`aplicacion/nombres_reglas.py`):
   > **RESUMEN!B4 · Error · Referencia rota o externa (L5)**
   > 2 fórmula(s) de RESUMEN con #REF! (la celda u hoja que citaban se borró): B4, B6. Efecto: esas celdas
   > muestran #REF! o un valor que ya no se puede rastrear.
6. **A6 · Causa raíz agrupada** (`Por causa raíz`, regla L1 `Referencia desalineada`):
   > **Error · 6 casos · Referencia desalineada (L1)**
   > PRESUPUESTO!F10 (partida 1) lee APU-01!E14 (valor 0) como rendimiento
   > Encontrado 0 · esperado 120

> **Antes de imprimir las tarjetas:** los 6 textos de arriba son el formato de cada alerta, con cifras de ejemplo.
> Se copian tal cual de la pantalla real del caso de demostración, con la versión congelada de Sílice
> (`reglas-congeladas-2026-11-24`), para que la persona lea exactamente lo que el programa muestra.

### Preguntas

Para cada una de las 6 alertas se hacen dos preguntas, sin pistas:

1. «¿Qué le está diciendo?»
2. «¿Qué haría ahora?»

Al terminar las 6 alertas se hace una tercera pregunta abierta:

3. «¿Qué alerta le faltó?»

### Hoja de registro (antes del SUS)

Participante: E__ (nunca el nombre) · Fecha: ____ · Conduce: ____

| Alerta | Lo entendió (sí / a medias / no) | Qué haría | Cita textual |
|---|---|---|---|
| A1 · Sin fuente | | | |
| A2 · Base de la empresa | | | |
| A3 · USD-Bs | | | |
| A4 · Componente fuera del total (L4) | | | |
| A5 · Referencia rota o externa (L5) | | | |
| A6 · Causa raíz (L1, 6 casos) | | | |

**Respuesta a «¿Qué alerta le faltó?» (cita textual):**

Anotación: __________________________________________________________________________________________

Una vez cerrado este registro, usted pasa a llenar el **cuestionario SUS** (sección anterior), sin ayuda.

## Consentimiento informado (2026-11-24)

> Hoja de una página para entregar y firmar antes de empezar la sesión. Se archiva en papel o en una carpeta
> local fuera del repositorio, separada de las hojas de observación.

**Consentimiento informado para participar en una prueba de uso de Sílice**
**Trabajo de grado — Universidad Santa María (USM)**

Le invitamos a participar en una sesión individual de evaluación del programa **Sílice**, desarrollado como
parte del trabajo de grado en la Universidad Santa María (USM). Antes de decidir, lea esta información con
calma y haga todas las preguntas que considere necesarias.

- **¿Qué se hace en la sesión?** Vamos a evaluar el programa, **no a usted ni su trabajo**. Usted realizará
  tres tareas breves en Sílice usando una obra de demostración con datos ficticios, leerá seis alertas tal como
  las muestra el sistema para indicar qué entiende y qué haría, y llenará un cuestionario corto sobre facilidad
  de uso (SUS). Quien conduce la sesión le pedirá pensar en voz alta y anotará tiempos y comentarios.
- **¿Cuánto dura?** Aproximadamente 45 minutos (ajuste final por el bloque de alertas: por confirmar con
  Eugenio).
- **Participación voluntaria:** su participación es totalmente voluntaria. Puede decidir no participar sin que
  esto le traiga ningún inconveniente.
- **Derecho a retirarse:** usted puede hacer una pausa, dejar cualquier pregunta sin responder o retirarse en
  cualquier momento, sin dar explicaciones y sin ninguna consecuencia. Si decide retirarse, sus anotaciones se
  eliminan de inmediato.
- **Privacidad y confidencialidad:** durante esta sesión **no se usan ni se graban datos reales de ninguna
  empresa ni nombres propios**. Todas las tareas se hacen con datos ficticios. Sus respuestas se registran bajo
  un código anónimo (por ejemplo, E1, E2), separado de esta hoja de consentimiento.
- **Uso de la información:** las respuestas, los tiempos y las citas anónimas se emplearán únicamente para el
  trabajo de grado en la Universidad Santa María (USM), donde se reportarán solo como cifras agregadas y citas
  sin nombre. Ningún dato personal ni hoja llena se sube a repositorios ni se comparte fuera del estudio.
- **Contacto para dudas:** si tiene preguntas antes, durante o después de la sesión, puede dirigirse a los
  autores del trabajo de grado, **Eugenio** y **Nicolaz** (correo o teléfono: por confirmar con Eugenio).

**Declaración de consentimiento**

He leído la información anterior, he podido hacer preguntas y acepto participar de manera voluntaria en esta
sesión bajo las condiciones descritas.

Nombre y apellido: __________________________________________________

Firma: ______________________________________________________________

Fecha: ________________________

Quien conduce la sesión (nombre y firma): ___________________________
