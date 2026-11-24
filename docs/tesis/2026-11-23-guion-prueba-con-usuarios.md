# Guion de la prueba con usuarios (semana 1 del plan del consejo)

> Para Eugenio. Ningún dato de esta prueba entra al repositorio: las hojas llenas, los nombres y las grabaciones se
> quedan en el equipo (NORMAS §1). En la tesis se reportan cifras agregadas y citas sin nombre.

## Cómo encaja en el anteproyecto (v7, 2026-11-23)

- **Es una prueba formativa**: sirve para ajustar el prototipo durante el diagnóstico (fases 1 a 3). No reemplaza la
  evaluación del objetivo 4, que sigue siendo el cuasiexperimento cruzado de la fase 4.
- **El SUS no figura entre los 4 instrumentos del v7.** Para que sus resultados entren en la tesis, el v7 debe
  declararlo en la metodología como quinto instrumento. Es un cuestionario estandarizado: no se valida su contenido,
  pero se usa una versión en español publicada y validada (Sevilla-González y otros, 2020; **por verificar** antes de
  citarla). Lo que sí deben validar los 3 expertos del v7 son las 3 tareas y la hoja de observación.
- **Separación de papeles (v7, §8):** los expertos que validan los instrumentos no participan en la medición. Por eso
  ningún participante de esta prueba puede ser uno de esos 3 expertos.

## Qué se quiere saber

1. Si un economista termina, **sin ayuda**, las tareas de todos los días en Sílice (eficacia).
2. Cuánto tarda y dónde se traba (eficiencia).
3. Qué tan usable le parece, medido con el cuestionario SUS (satisfacción).

Son las tres dimensiones de usabilidad de la norma ISO 9241-11: eficacia, eficiencia y satisfacción.

## Quiénes y cuántos

- Los 3 economistas que elaboran y revisan los presupuestos viales de la empresa del caso: es la población censal del
  v7. Con 5 personas se ve la mayoría de los problemas grandes (Nielsen y Landauer, 1993); con 3, se declara como límite.
- La medición de la auditoría es otro protocolo (errores sembrados y kappa de Cohen, v7 §8) y otra sesión.
- Sesión individual de unos 45 minutos, en el equipo de Eugenio, con Sílice abierto en una carpeta de demostración (datos
  ficticios).

## Antes de la sesión (Eugenio)

- [ ] Fusionar #138, #139 y #140, y abrir Sílice con la carpeta de demostración.
- [ ] Una hoja de observación impresa por participante (abajo), un cronómetro y el SUS impreso.
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

- Por tarea: el porcentaje que terminó sin ayuda, el tiempo mediano y los puntos donde se trabaron.
- El SUS: el promedio y el rango.
- Los límites: 3 participantes, datos de demostración y un evaluador que también es autor del sistema.
