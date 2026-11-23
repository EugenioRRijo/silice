# Segundo dossier: el método de diseñadores e ingenieros de front, y el diseño desde la tarea

Investigación del 2026-11-23, solo lectura sobre el repositorio. Es la base de una guía reutilizable de diseño y
construcción de interfaces (para Sílice y para otros proyectos).

**Qué no se repite.** Este dossier no repite los dos estudios anteriores; los cita así:

- «UX-01…UX-29»: reglas de `scratchpad/estudios_ux_dossier.md` (reglas cognitivas, formularios, botones, espacio,
  tablas, estados y guardias).
- «regla previa 1…12» y «E1…E9»: `.worktrees/s2mi2/docs/planes/2026-11-23-carga-cognitiva.md` (carga cognitiva en
  Reajuste, Riesgo y Control).

Aquí va lo que faltaba: **cómo trabajan** los autores (pasos que se pueden seguir), **cómo se diseña desde la tarea**,
**cómo se construye en React** para que una decisión no se olvide y **cómo se vigila**.

## Cómo leer las marcas

- **(abierta)**: la página o el PDF se leyó en esta investigación.
- **(registro)**: solo se vio el registro bibliográfico, una búsqueda o un resumen de terceros. Su contenido no se da por
  verificado más allá de lo que dice esa fuente.
- **[M] método**: pasos que otra persona puede seguir y repetir.
- **[O] opinión o estética**: preferencia razonada, sin procedimiento ni datos.

Las citas textuales van en el idioma original y entre comillas. Lo demás es paráfrasis.

## El caso que motiva el dossier

El dueño compuso una partida en Sílice y se perdió. En el árbol actual (`feature/carga-cognitiva`):

- `frontend-desktop/src/paginas/componer/Guardar.tsx:86-97`: al guardar, la pantalla muestra una notificación de éxito con
  el título «Guardado», el `mensaje` del servidor y los avisos. **No hay ninguna acción hacia el paso siguiente.**
- `frontend-desktop/src/paginas/componer/ComponerPartida.tsx:71-72`: solo cuando Componer se abre dentro del diálogo
  «Agregar partida» de la hoja, la partida guardada queda elegida para ponerle cantidad. Desde la pantalla suelta de
  Componer no hay camino al presupuesto.
- `frontend-desktop/src/comun/FranjaDelPaso.tsx:5-19`: **ya existe** la franja «Siguiente paso» con un único botón
  principal. La usan la hoja, Obras, Versiones y Archivos, pero Componer no.
- `frontend-desktop/src/paginas/componer/AvisoSinLista.tsx:25-26`: el antecedente documentado. En la prueba en vivo del
  2026-10-25, la falta de lista de precios «solo se supo al guardar, despues de llenar unos 40 campos». Fue el mismo tipo
  de fallo, un golfo de evaluación (§2.2) que se descubrió tarde.

Estas líneas salen de leer el código. El recorrido por el navegador queda pendiente de verificar.

---

## 1. El método de cada autor, en pasos

### 1.1 Adam Wathan y Steve Schoger, *Refactoring UI* (2018)

Fuentes:

- índice oficial del libro, https://www.refactoringui.com/ (abierta);
- notas de lectura de terceros, https://rjseymour66.github.io/webdev/refactoring-ui/ (abierta, pero **no es el libro**);
- «7 practical tips for cheating at design», Medium (403, no abierta).

**Pasos [M]**, según el índice. La parte 1, «Starting from Scratch», ordena:

1. «Start with a feature, not a layout»: diseñar una función concreta, no «la aplicación».
2. «Detail comes later»: baja fidelidad primero. La recomendación de **diseñar en escala de grises** y poner el color al
   final solo está verificada en las notas de terceros: «Design in grayscale first so you focus on space, contrast, and
   size». Otra fuente secundaria dice lo contrario, así que el texto exacto del libro queda **sin verificar**.
3. «Don't design too much»: no diseñar todos los casos antes de construir.
4. «Choose a personality».
5. «Limit your choices»: escalas fijas definidas antes.

**Jerarquía (parte 2).** Los capítulos dicen «Size isn't everything», «De-emphasize to emphasize», «Labels are a last
resort», «Balance weight and contrast» y «Separate visual hierarchy from document hierarchy». Las notas de terceros
resumen: tamaño, peso y color crean jerarquía; peso y color «do not disrupt layout».

**Espacio (parte 3).** «Establish a spacing and sizing system», «Start with too much white space», «Avoid ambiguous
spacing».

**Método frente a opinión.** Son **[M]** el orden (función → baja fidelidad → escalas fijas) y el sistema de espacio
definido de antemano. Son **[O]** «Choose a personality», «Use good fonts» y las sombras de dos partes. Los autores lo
llaman «Design with tactics, not talent»: son tácticas sueltas, no un proceso cerrado.

**Para Sílice.** El sistema de espacio ya existe: los tokens de Carbon (UX-22). Lo aprovechable es el **orden**: primero la
función, después la jerarquía con peso y color, y el color al final.

### 1.2 Emil Kowalski: ingeniería de diseño y pulido

Fuentes:

- «Great animations», https://emilkowal.ski/ui/great-animations (abierta);
- «Developing taste», https://emilkowal.ski/ui/developing-taste (abierta).

**Pasos [M]:**

1. Antes de animar, preguntar **para qué**: explicar una función, mostrar un cambio de estado o acompañar la entrada de
   un modal.
2. Preguntar **cuántas veces la verá** la persona: «consider how often the user will see it».
3. Si la acción se dispara con el teclado, **no animar**: «never animate keyboard initiated actions».
4. Si se anima: menos de 300 ms, *ease-out*, solo `transform` y `opacity`, interrumpible y con respeto a
   `prefers-reduced-motion`.
5. Para formar el criterio, **estudiar** las aplicaciones en vez de solo usarlas, y preguntar por qué algo se siente bien
   en lugar de clasificarlo como bueno o malo.

**[O]:** que hoy el producto que funciona sea «la base» y que lo que distingue sean el detalle y la calidad.

**Para Sílice.** La regla de frecuencia y teclado coincide con la ley de Jakob para usuarios de Excel (UX-06): en la hoja
y en el autocompletado no se anima nada. Encaja con `DESIGN.md` («animaciones solo de estado», según la regla previa).

### 1.3 Rauno Freiberg y las guías de interfaz de Vercel

Fuentes:

- «Invisible Details of Interaction Design», https://rauno.me/craft/interaction-design (abierta);
- «Web Interface Guidelines», https://vercel.com/design/guidelines (abierta). La página **no nombra autores**: remite al
  repositorio `vercel-labs` y agradece a varias personas. No se atribuye a Freiberg sin otra fuente.

**El método de Freiberg [M]:**

1. Grabar interfaces buenas y verlas **en cámara lenta**.
2. **Recrearlas** para construir intuición y vocabulario.
3. Construir prototipos y reflexionar sobre ellos: «great revelations surface from making something».
4. Explicar **por qué** funciona: «there must be a reason».

**Principios que salen de ese método:**

- reutilizar metáforas conocidas;
- respuesta inmediata;
- lo destructivo solo al soltar («Dismissing an app is destructive»);
- coherencia espacial;
- menos animación en lo frecuente: en un menú de órdenes de uso diario, «it does start to feel more like cognitive
  burden».

**Las guías de Vercel son reglas [M] comprobables:**

- Enter envía si el campo es el único control.
- Todo control tiene `<label>`.
- No bloquear lo que se teclea: aceptar la entrada y validar después.
- El botón de enviar queda habilitado hasta que empieza el envío.
- Actualización optimista con vuelta atrás o «Deshacer» si falla.
- Todo el flujo se opera con el teclado.
- El anillo de foco siempre se ve.
- Durante la carga, indicador y rótulo original.
- Lo destructivo pide confirmación o da «Deshacer».

**Para Sílice.** Casi todo coincide con UX-11, UX-16 y UX-18. Lo nuevo es **«no bloquear lo que se teclea»**: en un campo
numérico se acepta cualquier tecla y se avisa, en lugar de impedirla. Importa con la coma decimal, porque un campo que
rechaza la coma confunde a quien viene de Excel.

### 1.4 Brad Frost, *Atomic Design* (2016)

Fuentes:

- capítulo 2, https://atomicdesign.bradfrost.com/chapter-2/ (abierta);
- capítulo 4, https://atomicdesign.bradfrost.com/chapter-4/ (abierta);
- «A design system governance process», https://bradfrost.com/blog/post/a-design-system-governance-process/ (abierta).

**El modelo.** Átomos → moléculas → organismos → plantillas → páginas. Frost advierte: «Atomic design is not a linear
process». Es «a mental model» para ver la interfaz como un todo y como partes a la vez.

**El flujo de trabajo [M] (capítulo 4):**

1. **Inventario de interfaz.**
   - Juntar a todas las disciplinas.
   - Hacer capturas de «one instance of each unique UI pattern», en un tiempo fijo de 30 a 90 minutos.
   - Presentar por categoría y discutir los nombres («Naming things is hard»).
   - Decidir qué patrón se queda, cuál se va y cuáles se unen.
2. **Dirección.**
   - Bocetos de baja fidelidad de qué va en cada pantalla y en qué orden.
   - Después, la dirección visual (*style tiles*).
   - El front marca los patrones desde el primer día.
3. **Construcción en el navegador**: «Once the designs are in the browser, they should stay in the browser».
4. **Cierre**: pruebas, documentación y lanzamiento.

**Gobernanza [M].** Los primeros pasos son: buscar primero el componente que ya existe; si no alcanza, hablar con el
equipo del sistema; y decidir si es un caso único o algo del sistema.

**Para Sílice.** El **inventario** es el paso que evita reinventar. Componer no usó `FranjaDelPaso`, que ya existía en
`comun/`. Un inventario de `comun/` antes de construir una pantalla lo habría encontrado.

### 1.5 Josh W. Comeau

Fuentes:

- «Accessible Animations in React», https://www.joshwcomeau.com/react/prefers-reduced-motion/ (abierta);
- «Understanding Layout Algorithms», https://www.joshwcomeau.com/css/understanding-layout-algorithms/ (abierta).

**Método [M].**

- **Una decisión transversal se encapsula en un hook.** `usePrefersReducedMotion` lee la consulta de medios, se suscribe a
  sus cambios y devuelve un booleano que todo el código de animación consulta.
- **Valor seguro por omisión**: «start without animations, and enable them if the user wishes».
- **Para la depuración de CSS, un modelo mental**: «CSS properties on their own are meaningless». Las propiedades son
  entradas de un algoritmo de disposición; cuando algo sorprende, «Our mental model is incomplete».

**Para Sílice.** Es el mismo patrón del §3: la preferencia de tamaño de letra ya vive en `comun/useTamanoDeLetra.ts`. La
decisión que no debe olvidarse (paso siguiente, valores por omisión) va en un hook o un componente, no repetida en cada
página.

### 1.6 El equipo de Linear

Fuentes:

- índice del Linear Method, https://linear.app/method (abierta);
- «Write issues not user stories», https://linear.app/method/write-issues-not-user-stories (abierta);
- «Build with users», https://linear.app/method/build-with-users (abierta);
- «How we redesigned the Linear UI», https://linear.app/now/how-we-redesigned-the-linear-ui (abierta);
- Karri Saarinen, «10 rules for crafting products that stand out», blog de Figma,
  https://www.figma.com/blog/karri-saarinens-10-rules-for-crafting-products-that-stand-out/ (abierta).

**El método del rediseño [M]:**

1. Concepto acotado a tres problemas. Saarinen dejó fuera la navegación porque ya no era solo de diseño.
2. Prototipos que funcionan.
3. **Pruebas de estrés** antes de implementar:
   - **entorno**: Electron y navegador; se probó desde «very condensed» hasta configuraciones espaciosas;
   - **apariencia**: color en LCH, con tres variables por tema en lugar de 98;
   - **jerarquía**: cada decisión se probó en cada tipo de vista (lista, tablero, dividida).
4. Detrás de una bandera, uso interno y despliegue por porcentaje de espacios de trabajo, en unas seis semanas.

**Principios.** Son **[O]** con algunos pasos:

- «The more specific your product's purpose, the better it will perform».
- «If you can't do everything well, start by doing less».
- La especificación es «the baseline, not the finish line».
- «we don't make decisions based on data or experiments—including A/B tests».
- Las historias de usuario son «an anti-pattern»: hay que escribir tareas en lenguaje llano y citar textual lo que dice
  el usuario.
- «users will project their needs from the context or product they currently see».

**Para Sílice.** Dos cosas aplican sin reservas:

- la **prueba de estrés por tipo de vista**: cada regla nueva se prueba en tabla, formulario, tablero, hoja y asistente,
  que son los tipos de UX-19;
- **citar textual al usuario** en el hallazgo: lo que dijo el dueño al perderse vale más que un resumen.

La advertencia de «Build with users» explica por qué el dueño, que viene de Excel, pide cosas de Excel: hay que leer la
necesidad detrás del pedido.

### 1.7 Don Norman, *The Design of Everyday Things* (1988, revisado en 2013)

Fuentes:

- «Signifiers, not affordances», jnd.org (publicado en *Interactions*, 2008), https://jnd.org/signifiers-not-affordances/
  (abierta);
- prefacio de la edición revisada, https://jnd.org/preface-design-of-everyday-things-revised-edition/ (abierta);
- resumen del libro, https://en.wikipedia.org/wiki/The_Design_of_Everyday_Things (abierta, fuente secundaria);
- NN/g, «The Two UX Gulfs: Evaluation and Execution», https://www.nngroup.com/articles/two-ux-gulfs-evaluation-execution/
  (abierta).

El libro no se abrió: lo que sigue sale del prefacio, del ensayo y de los resúmenes.

**Conceptos:**

- **Affordance**: qué permite hacer el objeto.
- **Significante**: la señal perceptible de qué se puede hacer y dónde: «Forget affordances: what people need, and what
  design must provide, are signifiers». En el prefacio: «Signifiers are of far more importance to designers than are
  affordances».
- **Mapeo**: la relación entre control y efecto; «natural» depende de la cultura.
- **Retroalimentación**: completa y continua sobre el resultado de la acción.
- **Modelo conceptual**: la imagen coherente de cómo funciona el sistema.
- **Restricciones**: lo que impide la acción equivocada.

**Siete etapas de la acción [M]** (según el resumen secundario):

1. formar la meta;
2. formar la intención;
3. especificar la acción;
4. ejecutarla;
5. percibir el estado;
6. interpretarlo;
7. evaluar el resultado.

**Los golfos.** Las etapas 2 a 4 cruzan el **golfo de ejecución** («the difference between the intentions and the
allowable actions»). Las etapas 5 a 7 cruzan el **golfo de evaluación**, que es pequeño «when the system provides
information about its state in a form that is easy to get». NN/g añade que los dos golfos dependen uno del otro: un plan
basado en una lectura errónea del estado falla, así que el de evaluación se arregla primero.

**El proceso de Norman [M].** El ciclo del diseño centrado en las personas: observación, ideación, prototipo y prueba
(prefacio).

**Para Sílice.** Al guardar, la pantalla responde «Guardado». La persona no puede interpretar **dónde quedó la partida ni
si ya está en el presupuesto**: es un golfo de evaluación. Y la acción siguiente no tiene significante en la pantalla: es
un golfo de ejecución. El §2.2 lo aplica paso a paso.

### 1.8 Jared Spool y Luke Wroblewski

**Spool** (todo en registro: el sitio de Center Centre / UIE rechazó la conexión durante la investigación):

- La brecha de conocimiento: una interfaz parece intuitiva cuando la distancia entre el **conocimiento actual** de la
  persona y el **conocimiento meta** que la interfaz exige es pequeña. Esa distancia se cierra de dos maneras: enseñando
  (sube el actual) o simplificando (baja el meta). Resúmenes en https://www.cmswire.com/cms/enterprise-20/jared-spool-on-creating-intuitive-designs-drupalcon-010477.php
  y https://www.creativebloq.com/netmag/jared-spool-usability-and-intuitive-design-3126409 (registro).
- Según esos resúmenes, Spool recomienda **observar a los usuarios con regularidad** (cada miembro del equipo, al menos
  dos horas cada seis semanas). La cifra no se verificó en una fuente de Spool.
- **[M]** si se acepta como procedimiento: medir la brecha observando, y decidir en cada caso si se enseña o se
  simplifica.

**Wroblewski**, «Obvious Always Wins», https://www.lukew.com/ff/entry.asp?1945 (abierta):

- «hiding critical parts of an application behind these kinds of menus could negatively impact usage»;
- «When critical parts of an application are made more visible, usage of them can increase».
- **[O]** con ejemplos de casos: no es un estudio con método publicado.

**Para Sílice.** Spool da el criterio para usuarios de Excel: su **conocimiento actual** es la hoja de cálculo. Cada cosa
que Sílice hace distinto de Excel agranda la brecha (UX-06). Wroblewski se cruza con la divulgación progresiva (regla
previa 2); la contradicción se resuelve en el §1.13.

### 1.9 Alan Cooper: personas y escenarios dirigidos por objetivos

Fuentes:

- «The Origin of Personas», boletín de Cooper, agosto de 2003, copiado en https://www.strehle.de/tim/?p=264 (abierta, es
  una copia);
- *About Face* (ediciones de 1995 a 2014) y *The Inmates Are Running the Asylum* (1999) (registro).

**Pasos [M]**, según su relato:

1. Entrevistar a los usuarios.
2. Agruparlos por **objetivos, tareas y nivel de destreza**: «three distinct groups, clearly differentiated by their
   goals, tasks, and skill levels».
3. Dar a cada grupo un arquetipo con nombre (Chuck, Cynthia y Rob).
4. Presentar todo el diseño desde el punto de vista de una persona: «From then on, I always presented design work using
   one of the personas».

La persona primaria y los escenarios dirigidos por objetivos son del libro (registro); no se citan aquí más allá de su
nombre.

**Para Sílice.** La parte útil es **ordenar por objetivo y no por rasgos**: el objetivo de quien compone es tener la
partida con precio **en el presupuesto**, no «guardar un APU». Ver la contradicción con Intercom en el §1.13.

### 1.10 Jeff Patton: el mapa de historias de usuario

Fuente: «The new user story backlog is a map», https://jpattonassociates.com/the-new-backlog/ (abierta). El libro *User
Story Mapping* (O'Reilly, 2014) queda en registro.

**Pasos [M]:**

1. Arriba, las actividades grandes, de izquierda a derecha **en el orden del tiempo**: «I'm always imagining time moving
   left to right». Esa fila es la **columna vertebral**.
2. Debajo de cada actividad, sus tareas («costillas»); más arriba lo imprescindible y más abajo lo menos necesario.
3. El **esqueleto que camina**: la fila más alta es «the smallest possible system you could build that would give you end
   to end functionality».
4. Cortar entregas con carriles horizontales (cinta adhesiva en la pared).
5. Construir «left to right, and top to bottom».
6. **Recorrer el mapa con un usuario**: «I can walk the map from beginning to end with a user, stakeholder, or developer».

**Para Sílice.** El mapa muestra lo que una pantalla sola esconde: «componer» es **una costilla** de la actividad «armar el
presupuesto». Si la pantalla termina en la costilla y no vuelve a la columna vertebral, el recorrido se corta (§2.6).

### 1.11 IBM Enterprise Design Thinking (el proceso detrás de Carbon)

Fuentes:

- https://www.ibm.com/design/approach/design-thinking (abierta);
- materiales de 2016 a 2018 vistos solo por búsqueda (registro).

**Principios:**

- «A focus on user outcomes»: «We measure success by how well we fulfill human needs».
- «Restless reinvention»: «Everything is a prototype».
- «Diverse empowered teams».

**El bucle [M]:** observar, reflexionar y hacer, en continuo. «The only way to see an outcome is to make one».

**Las llaves [M]:**

- **Hills**: «concise statements of the goals we aim to help our users accomplish». El formato «Quién, Qué, Guau» aparece
  en materiales viejos (registro).
- **Playbacks**: revisiones periódicas con usuarios, interesados y equipo.
- **Sponsor users**: «real-world users that provide teams with deep expertise». Según materiales secundarios, son
  personas reales, no arquetipos (registro).

**Para Sílice.** El «hill» de la tarea es la frase que debe cumplir la pantalla: «Un presupuestista deja una partida nueva
con su precio en el presupuesto de la obra sin salir a buscarla». El dueño es el *sponsor user* natural, y cada playback
con él es la «prueba en vivo» que el repositorio ya hace.

### 1.12 GOV.UK: diseñar desde las necesidades del usuario

Fuentes:

- «Start by learning user needs», https://www.gov.uk/service-manual/user-research/start-by-learning-user-needs (abierta);
- «Government Design Principles», https://www.gov.uk/guidance/government-design-principles (abierta).

**Pasos [M]:**

1. Aprender quiénes son los usuarios, cómo hacen hoy la tarea y qué les frustra:
   - con evidencia existente (analítica, búsquedas);
   - entrevistando y **observando** a usuarios reales o probables;
   - hablando con el personal que los atiende.
2. Tratar como suposición toda opinión que no venga de usuarios: «Treat any opinions or suggestions that do not come from
   users as assumptions».
3. Escribir la necesidad: «As a… / I need… / So that…», con «When…» y «Because…» opcionales, en palabras que el usuario
   reconocería, y centrada en el problema y no en la solución.
4. Las necesidades son «high-level, broad in scope and stable over time»; después se parten en historias, y cada historia
   guarda el vínculo con su necesidad.

Los principios son 11 en la página (el último se añadió el 2025-04-02). El primero es «Start with user needs»; otros son
«Do the hard work to make it simple», «Iterate. Then iterate again» y «Be consistent, not uniform».

**Para Sílice.** La necesidad escrita con «para que» obliga a nombrar **el resultado fuera de la pantalla**, que es lo que
faltó en Componer (§2.4).

### 1.13 Dónde se contradicen y qué conviene a una app densa para usuarios de Excel

| Tema | Postura A | Postura B | Para Sílice |
|---|---|---|---|
| Datos y experimentos | Linear: no se decide con datos ni con A/B. | GOV.UK: «Design with data»; Spool y GOV.UK: observar a los usuarios con regularidad. | Sin A/B: hay pocos usuarios y no daría significancia. Sí hay **observación** de presupuestistas reales en cada ciclo (GOV.UK, Spool), con lo dicho citado textual (Linear). |
| Personas | Cooper: arquetipos por objetivos. | Intercom (Klement): las personas «artificially limit your product's audience because they focus on attributes rather than motivations» (§2.4). IBM: *sponsor users* reales. | Sin personas inventadas: **uno o dos usuarios reales** (IBM) y una **historia de trabajo** por tarea (Klement). De Cooper se toma el orden por objetivos. |
| Historias de usuario | Patton: el mapa de historias. GOV.UK: de la necesidad a la historia. | Linear: las historias son un antipatrón; se escriben tareas. | El formato da igual. Lo que no se negocia es **la cadena de tareas** (mapa y HTA) que dice qué viene después. |
| Espacio | Refactoring UI: «Start with too much white space». | Linear probó «very condensed»; Carbon xs y sm para lo denso (UX-22). | Los tokens de Carbon, con la densidad según el tipo de vista. «Mucho aire» vale para la primera exploración, no para la hoja de trabajo diario. |
| Visible o plegado | Wroblewski: «Obvious always wins». | Divulgación progresiva: «Más opciones» (regla previa 2). | Decide el **análisis de tareas** (§2.1): lo que está en el camino crítico de la tarea principal queda a la vista, incluido el paso siguiente; lo ocasional se pliega. |
| Animación y deleite | Comeau y Refactoring UI ponen el acento en el pulido y el detalle. | Kowalski y Freiberg: menos animación cuanto más frecuente; nada en lo que se dispara con el teclado. | Una herramienta de uso diario: **animación solo de estado**, nunca en el teclado (coincide con `DESIGN.md`). |
| De arriba abajo o de abajo arriba | Frost: átomos → páginas (aunque «not a linear process»). | Refactoring UI: empezar por la función. react.dev: partir la maqueta en cajas (§3). | **De la tarea a las piezas**: tarea → pantalla → componentes. El inventario de Frost se hace en medio, para reutilizar. |

---

## 2. El diseño desde la tarea, aplicado a «componer una partida y dejarla en el presupuesto»

### 2.1 Análisis jerárquico de tareas (HTA)

Fuentes:

- NN/g, «Task Analysis: Support Users in Achieving Their Goals», https://www.nngroup.com/articles/task-analysis/ (abierta);
- origen: Annett y Duncan (1967), «Task analysis and training design», *Occupational Psychology* 41 (registro);
- revisión: Stanton, N. A. (2006), «Hierarchical task analysis: Developments, applications, and extensions», *Applied
  Ergonomics* 37(1), 55-79 (registro).

**Pasos [M]** (NN/g):

1. Reunir información observando y hablando con usuarios en su contexto, sin fiarse solo de lo que dicen.
2. Partir de **una meta y un escenario**.
3. Descomponer en tareas y subtareas: «The number of levels of subtasks depends on the complexity of the process».
4. Escribir **planes**: en qué orden y bajo qué condiciones se hace cada paso.
5. Analizar el número de pasos, su frecuencia, la complejidad cognitiva y el tiempo.

**Aplicado a Sílice.** Esto es un borrador que hay que validar observando a un presupuestista.

```
0. Dejar una partida nueva, con su precio unitario, en el presupuesto de la obra
   1. Identificar la partida (código, descripción, unidad), del pliego o del cómputo
   2. Componer su precio
      2.1 Elegir los materiales y sus cantidades por unidad
      2.2 Elegir los equipos y su rendimiento
      2.3 Elegir la mano de obra y su rendimiento
      2.4 Revisar las condiciones (fecha, moneda, lista de precios)
   3. Revisar el desglose del precio unitario
   4. Guardar la composición en el catálogo de la obra
   5. Ponerla en la hoja de presupuesto con su cantidad
   6. Comprobar el total de la obra

Plan 0: 1 → 2 → 3 → 4 → 5 → 6.
  Si hay una partida parecida (Similares), en 2 se parte de ella.
  Si falta la lista de precios (AvisoSinLista), antes de 2 se crea la lista.
Plan 2: 2.1 a 2.3 en cualquier orden; 2.4 casi siempre se queda con el valor por omisión.
```

**Lo que el HTA deja ver antes de construir.** La meta 0 termina en el paso 5, pero la pantalla Componer cubre del 1 al 4.
**El borde de la pantalla corta la meta.** Cuando un borde de pantalla cae dentro de una meta, la pantalla tiene que
terminar con un significante hacia el paso que sigue (§2.7). El HTA también separa lo frecuente de lo ocasional:

- 2.1 a 2.3 se hacen siempre y van a la vista;
- 2.4 casi nunca se cambia y va a «Más opciones» con su valor por omisión (regla previa 4).

Esto es lo que resuelve la contradicción entre Wroblewski y la divulgación progresiva (§1.13).

### 2.2 Los golfos de Norman, paso a paso

Para cada paso del HTA, dos preguntas: ¿sabe la persona **qué hacer y con qué control** (ejecución)? ¿Sabe **qué pasó**
(evaluación)?

| Paso | Golfo de ejecución | Golfo de evaluación |
|---|---|---|
| 1 Identificar | Con unos 40 controles a la vista, ¿cuál es el primero? Hace falta un orden visual que empiece por código y descripción. | ¿El código ya existe? El autocompletado lo dice (UX-05). |
| 2 Componer | ¿Dónde se agrega un material? Hace falta un significante en cada tabla. | ¿Cuánto suma cada fila? Hace falta el desglose a la vista (paso 3). |
| 2.4 Condiciones | Si falta la lista, ¿qué se hace? `AvisoSinLista` lo dice al abrir, desde el 2026-10-25. | Antes se supo solo al guardar, después de 40 campos: un golfo de evaluación descubierto tarde. |
| 4 Guardar | El botón «Guardar composición» es claro. | **«Guardado»: ¿dónde?, ¿en el catálogo o en el presupuesto?, ¿ya está en la obra?** El estado no se puede interpretar. |
| 5 Poner en la hoja | **No hay ningún control en la pantalla.** La persona tiene que recordar que debe ir a la hoja y buscar la partida (recordar en vez de reconocer, UX-05). | — |

### 2.3 El recorrido cognitivo, aplicado

Fuentes:

- Wharton, C., Rieman, J., Lewis, C. y Polson, P. (1994), «The cognitive walkthrough method: A practitioner's guide», en
  Nielsen y Mack (eds.), *Usability Inspection Methods*, Wiley, 105-140 (registro: es la versión 3 del método; la copia de
  la Universidad de Waterloo dio 404);
- NN/g, «Evaluate Interface Learnability with Cognitive Walkthroughs», https://www.nngroup.com/articles/cognitive-walkthroughs/
  (abierta);
- Spencer, R. (2000), «The streamlined cognitive walkthrough method, working around social constraints encountered in a
  software development company», CHI 2000, 353-359, doi:10.1145/332040.332456. PDF:
  https://facweb.cdm.depaul.edu/cmiller/eval/p353-spencer.pdf (abierta; su tabla 3 resume el proceso de Wharton et al.).

**Entradas (Spencer, tabla 3, adaptada de Wharton):** identificación de los usuarios, tareas de muestra, la **secuencia de
acciones** de cada tarea y la descripción o implementación de la interfaz.

**Las cuatro preguntas por paso** (versión de NN/g del método de Wharton et al.):

1. «Will users try to achieve the right result?»
2. «Will users notice that the correct action is available?»
3. «Will users associate the correct action with the result they're trying to achieve?»
4. «After the action is performed, will users see that progress is made toward the goal?»

Un «no» en cualquiera marca el paso como fallido (NN/g).

**La versión abreviada de Spencer**, con dos preguntas y pensada para equipos con prisa:

1. «Will the user know what to do at this step?»
2. «If the user does the right thing, will they know that they did the right thing, and are making progress towards their
   goal?»

Spencer también fija reglas de la sesión: no rediseñar durante el recorrido (se anota y se sigue), desactivar la actitud
defensiva de forma explícita y anotar los problemas de aprendizaje, las ideas, los **huecos del diseño** y los problemas
del análisis de tareas.

**Usuario:** presupuestista que viene de Excel y conoce los APU, pero no Sílice. **Tarea:** la meta 0 del §2.1.

| # | Acción correcta | P1 ¿intenta el resultado correcto? | P2 ¿nota la acción? | P3 ¿asocia acción y resultado? | P4 ¿ve el progreso? | Veredicto |
|---|---|---|---|---|---|---|
| a | Escribir el código y la descripción | Sí | Depende del orden visual entre unos 40 controles | Sí | Sí, el autocompletado responde | Riesgo: revisar el orden |
| b | Agregar los materiales con su cantidad | Sí | Sí, si cada tabla tiene su botón | Sí | Sí, el desglose se actualiza | Pasa |
| c | Dejar las condiciones como vienen | **No sabe que puede dejarlas**: 2.4 a la vista parece trabajo obligatorio (Hick, E4) | — | — | — | Falla: plegar con su resumen |
| d | Pulsar «Guardar composición» | Sí | Sí, es el único principal | Sí | **«Guardado» no dice dónde quedó** | Falla P4 |
| e | Ir a la hoja y agregar la partida con su cantidad | Sí: la meta es el presupuesto | **No hay acción en la pantalla** | — | — | **Falla P2: no hay paso siguiente** |

Con Spencer, los pasos d y e fallan en la segunda pregunta («making progress towards their goal»). El hueco del diseño se
anota como tal: la especificación de Componer no dice cuál es la acción en el estado «guardado».

### 2.4 «Jobs to be done» y la historia de trabajo

Fuentes:

- Christensen Institute, «Jobs to Be Done», https://www.christenseninstitute.org/theory/jobs-to-be-done/ (abierta): «the
  progress they're trying to make as they strive toward a goal or aspiration within particular circumstances», con fuerzas
  funcionales, sociales y emocionales;
- Christensen, Hall, Dillon y Duncan (2016), «Know Your Customers' "Jobs to Be Done"», *Harvard Business Review*,
  https://hbr.org/2016/09/know-your-customers-jobs-to-be-done (registro: solo se vio la entrada);
- Intercom, «How we accidentally invented Job Stories», https://www.intercom.com/blog/accidentally-invented-job-stories/
  (abierta): formato «[ When _____ ] [ I want to _____ ] [ So I can _____ ]»;
- Klement, A., «Replacing the User Story with the Job Story» (registro).

**Pasos [M]:**

1. Escribir la circunstancia, que es el disparador.
2. Escribir la motivación.
3. Escribir el **resultado esperado**, que no es una función de la pantalla.

**Aplicado:**

> **Cuando** tengo una partida del pliego que no está en mi catálogo, **quiero** armar su precio con los insumos y
> rendimientos que uso, **para poder** ponerle su cantidad en el presupuesto y saber cuánto cuesta la obra.

La historia de trabajo muestra el defecto sin probar nada: el resultado («ponerle su cantidad en el presupuesto») **no
ocurre en Componer**. Si el resultado de la historia cae fuera de la pantalla, la pantalla debe llevar hasta él.

La necesidad al estilo GOV.UK dice lo mismo: «Necesito agregar al presupuesto una partida que no existe, para que el total
de la obra la incluya».

### 2.5 El mapa de recorrido

Fuente: NN/g, «Journey Mapping 101», https://www.nngroup.com/articles/journey-mapping-101/ (abierta):

- un actor por mapa;
- escenario y expectativas;
- fases;
- acciones, pensamientos y emociones (los pensamientos, idealmente con citas de la investigación);
- oportunidades.

Sirve para procesos de varios pasos en el tiempo.

| Fase | En Excel (lo que trae) | En Sílice hoy | Pensamiento (inferido; hay que confirmarlo con citas) | Oportunidad |
|---|---|---|---|---|
| Encontrar | Busca un APU parecido en otro libro | Similares, autocompletado | «¿Ya tengo algo así?» | Ya está |
| Componer | Copia filas y ajusta rendimientos | Tablas de insumos | «¿Qué de todo esto tengo que llenar?» | Plegar lo ocasional (§3c) |
| Guardar | Guardar el libro | «Guardar composición» | «¿Ya está?» | Frase de qué quedó y dónde |
| Llevar al presupuesto | Copia el precio unitario a la hoja del presupuesto | **Nada en la pantalla** | **«¿Y ahora?»**: aquí es donde el dueño se perdió | Paso siguiente con un botón (§3d) |
| Comprobar | Mira el total | Hoja de presupuesto | «¿Cuánto subió la obra?» | Que la hoja diga lo que cambió |

El mapa necesita la cita textual de lo que dijo el dueño al perderse (Linear, §1.6). Sin investigación, el mapa es una
hipótesis (NN/g y GOV.UK).

### 2.6 El mapa de historias de Sílice (Patton)

La columna vertebral, de izquierda a derecha:

> Abrir la obra → Cargar el cómputo → **Armar el presupuesto** → Revisar el total → Exportar o entregar

Debajo de «Armar el presupuesto» van sus costillas: agregar una partida que ya existe, **componer una partida nueva**,
ajustar cantidades y revisar parámetros. Lo que se ve en el mapa: **toda costilla vuelve a su actividad**. Componer debe
volver a «Armar el presupuesto» con la partida lista. Si se recorre el mapa con el dueño de principio a fin (Patton, paso 6),
el corte aparece en voz alta antes de escribir código.

### 2.7 Cómo se detecta, antes de construir, que una pantalla deja sin paso siguiente

Es una **prueba del paso siguiente** en cinco comprobaciones. Cada una sale de un método de arriba.

1. **Historia de trabajo** (§2.4): ¿el «para poder…» ocurre dentro de la pantalla? Si no, la pantalla tiene un destino
   obligatorio.
2. **Bordes en el HTA** (§2.1): se dibuja el borde de cada pantalla sobre el árbol. Todo borde que cae **dentro** de una
   meta necesita, en el estado final de la pantalla, un significante (botón o enlace) hacia el paso del otro lado.
3. **Recorrido cognitivo con el estado final incluido** (§2.3): el recorrido no termina en «Guardar». Se hace un paso más,
   el siguiente del HTA, y se le aplican las preguntas 2 y 4 (o las dos de Spencer).
4. **Tabla de estados** (UX-27): la fila «éxito» lleva tres columnas obligatorias: qué quedó hecho, dónde quedó y **cuál
   es el único control que lleva al paso siguiente**. Una celda vacía es un defecto de la especificación.
5. **Contrato en el código** (§3d): el tipo del estado «hecho» exige un `siguiente`; sin él no compila. La prueba comprueba
   que ese control está a la vista y tiene el foco.

Las comprobaciones 1 a 4 se hacen en papel, en minutos y antes de la primera línea de código. La 5 impide que vuelva a
pasar.

---

## 3. Los patrones de React para que una buena decisión se reutilice

### 3.1 Lo que dicen las fuentes

| Fuente | Qué aporta | Marca |
|---|---|---|
| react.dev, «Thinking in React», https://react.dev/learn/thinking-in-react | Cinco pasos [M]: (1) cajas alrededor de cada componente de la maqueta, con una sola responsabilidad: «If it ends up growing, it should be decomposed»; (2) versión estática sin estado; (3) el estado mínimo: «keep it DRY… compute everything else on-demand»; (4) el estado en el padre común más cercano; (5) flujo inverso con *callbacks*. | (abierta) |
| react.dev, «You Might Not Need an Effect», https://react.dev/learn/you-might-not-need-an-effect | Lo derivado se calcula al renderizar; el estado se reinicia con `key`; la lógica de un evento va en su manejador: «Use Effects only for code that should run *because* the component was displayed». El envío del formulario va en `handleSubmit`. Nada de cadenas de efectos. Se avisa al padre en el mismo evento. | (abierta) |
| Kent C. Dodds, «Compound Components with React Hooks», https://kentcdodds.com/blog/compound-components-with-react-hooks | Componentes que comparten estado implícito por contexto, como `<select>` y `<option>`; un hook de contexto que lanza un error si se usa fuera del padre. | (abierta) |
| Dodds, «How to give rendering control to users with prop getters», https://kentcdodds.com/blog/how-to-give-rendering-control-to-users-with-prop-getters | Una función que devuelve las props (ARIA y manejadores) y **compone** el `onClick` del usuario con el interno; por eso es mejor que un objeto que se esparce. | (abierta) |
| Dodds, «The State Reducer Pattern with React Hooks», https://kentcdodds.com/blog/the-state-reducer-pattern-with-react-hooks | El hook acepta un `reducer` que por omisión es el suyo y se exporta, con los `actionTypes` exportados: el caso común no configura nada. Advierte que el modo de actualizar pasa a ser parte de la API. | (abierta) |
| Dodds, «Inversion of Control», https://kentcdodds.com/blog/inversion-of-control | Contra el «apropcalypse» (una prop más por cada caso). Con un solo caso de uso, «avoid hasty abstractions» (AHA). | (abierta) |
| Dan Abramov, «Presentational and Container Components», nota de 2019, https://medium.com/@dan_abramov/smart-and-dumb-components-7ca2f9a7c7d0 | «I don't suggest splitting your components like this anymore»: los hooks separan la lógica sin partir en contenedor y presentación. | (registro: Medium dio 403; texto visto en una copia, por búsqueda) |
| Abramov, «Before You memo()», https://overreacted.io/before-you-memo/ | Bajar el estado al componente que lo usa y subir el contenido como `children`. | (abierta) |
| Radix Primitives, https://www.radix-ui.com/primitives/docs/overview/introduction | Componentes sin estilo que resuelven ARIA, foco y teclado según los patrones de WAI-ARIA. | (abierta) |
| React Aria (Adobe), https://react-aria.adobe.com/ | «style-free out of the box». Componentes de alto nivel y, si hace falta más control, «the low-level Hook-based API». | (abierta) |
| Testing Library, «Guiding Principles», https://testing-library.com/docs/guiding-principles, y prioridad de consultas, https://testing-library.com/docs/queries/about/#priority | «The more your tests resemble the way your software is used, the more confidence they can give you». `getByRole` primero, `getByLabelText` para formularios y `getByTestId` al final. | (abierta) |

**Qué se elige para Sílice y por qué.**

- **No se añade Radix ni React Aria.** Carbon ya trae los componentes accesibles con estilo. Sumar otra biblioteca sin
  estilo sería tecnología por reflejo (memoria del 2026-10-25, «que no parezca vibecodeado»).
- **Se toma la arquitectura sin estilo como idea**: la lógica en un hook, el comportamiento y el ARIA en *prop getters*, y
  la presentación en Carbon.
- **Se envuelve Carbon en componentes compuestos de la aplicación**, que imponen la decisión de diseño.
- **Se aplica AHA**: el patrón se extrae a `comun/` cuando el segundo o tercer caso lo pide. `FranjaDelPaso` y `TablaDensa`
  ya existen; se construye sobre ellas.
- **Pruebas por rol y nombre** (Testing Library). Cuando jsdom no recorre todos los estados, se suma una **prueba
  estática** que lee el código fuente, como ya hacen `src/paginas/sinJergaInterna.test.ts` y `src/comun/AnilloDeFoco.test.ts`.

Los cuatro esqueletos siguientes son orientativos: los nombres y las rutas se ajustan al construir, con TDD.

### 3.2 (a) Una cabecera de sección común

**Patrón:** componente compuesto `Seccion` con un **contexto de nivel**. La sección cuenta su nivel de título y la
cabecera lo lee. Hoy `ComponerPartida` recibe `nivelDelTitulo` a mano (h2 en la pantalla, h3 en el panel); con el
contexto, el nivel deja de pasarse a mano y de equivocarse.

```tsx
// comun/Seccion.tsx
import { createContext, useContext, type ReactNode } from "react";

const NivelDeSeccion = createContext<2 | 3 | 4 | null>(null);

function useNivel(): 2 | 3 | 4 {
  const nivel = useContext(NivelDeSeccion);
  if (nivel === null) throw new Error("Seccion.Cabecera solo puede ir dentro de <Seccion>");
  return nivel;
}

export function Seccion({ children }: { children: ReactNode }) {
  const padre = useContext(NivelDeSeccion);
  const nivel = padre === null ? 2 : (Math.min(padre + 1, 4) as 2 | 3 | 4);
  return (
    <NivelDeSeccion.Provider value={nivel}>
      <section className="silice-seccion">{children}</section>
    </NivelDeSeccion.Provider>
  );
}

Seccion.Cabecera = function Cabecera({ titulo, ayuda, accion }: {
  titulo: string;          // en palabras de obra (UX-03)
  ayuda?: ReactNode;       // va dentro de QueEsEsto, plegada (UX-02)
  accion?: ReactNode;      // a lo sumo un botón; el principal lo decide la página (UX-13)
}) {
  const Titulo = `h${useNivel()}` as const;
  return (
    <header className="silice-seccion__cabecera">
      <Titulo>{titulo}</Titulo>
      {ayuda}
      {accion}
    </header>
  );
};
```

**Prueba que obliga a usarlo:**

- **De comportamiento** (Vitest y Testing Library): `<Seccion><Seccion.Cabecera titulo="A"/><Seccion><Seccion.Cabecera
  titulo="B"/></Seccion></Seccion>` da `getByRole("heading", { level: 2, name: "A" })` y `{ level: 3, name: "B" }`.
  Fuera de `<Seccion>`, lanza el error.
- **Estática**, al estilo de `no-html-heading` de Atlassian (§5): se recorre `src/paginas/**/*.tsx` sin comentarios (la
  función `sinComentarios` de `sinJergaInterna.test.ts`) y se falla si aparece `<h2`, `<h3` o `<h4` literal. Las
  excepciones van en una lista con su motivo, igual que Polaris exige motivo en cada desactivación (§5).

### 3.3 (b) Una tabla que siempre lleva su frase de respuesta

**Patrón:** la **obligación va en el tipo**. `respuesta` es una prop requerida, de modo que la frase no se puede olvidar sin
que TypeScript falle. El componente envuelve `TablaDensa` y pone la frase **antes** de la tabla (regla previa 1, UX-24).

```tsx
// comun/TablaConRespuesta.tsx
import { TablaDensa, type ColumnaDensa, type FilaDensa } from "./TablaDensa";

interface Props {
  pregunta: string;            // nombre accesible de la tabla: qué pregunta responde
  respuesta: string;           // la frase, con la cifra que manda el servidor (RB-2); no se calcula aquí
  columnas: ColumnaDensa[];
  filas: FilaDensa[];
  cargando?: boolean;
  vacio?: { titulo: string; descripcion?: string };
}

export function TablaConRespuesta({ pregunta, respuesta, ...tabla }: Props) {
  if (import.meta.env.DEV && respuesta.trim() === "") {
    throw new Error(`La tabla «${pregunta}» necesita su frase de respuesta`);
  }
  return (
    <div className="silice-tabla-con-respuesta">
      {!tabla.cargando && <p className="silice-respuesta">{respuesta}</p>}
      <TablaDensa etiqueta={pregunta} {...tabla} />
    </div>
  );
}
```

**Prueba que obliga a usarlo:**

- **De comportamiento**: `const frase = screen.getByText(/terminarán después/)`,
  `const tabla = screen.getByRole("table", { name: "Cuándo termina cada partida" })` y
  `expect(frase.compareDocumentPosition(tabla) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()`. El oráculo sale del dato
  simulado de la API, no de una constante del componente (regla previa, Control).
- **Estática**, al estilo de `no-html-button` de Atlassian: en `src/paginas/` se prohíbe importar `DataTable` de
  `@carbon/react` y usar `TablaDensa` directamente, salvo una lista de excepciones con motivo, como el editor de hoja, que
  no es una tabla de resultados (UX-19).

### 3.4 (c) Un formulario con «Más opciones» plegadas y valores por omisión

**Patrón:** un **hook de formulario declarativo** con *prop getters* y *state reducer*, más un componente `MasOpciones`.

- Cada campo declara su valor por omisión, si va a la vista o plegado, de qué depende y cómo se describe en la frase de
  resumen.
- El *reducer* por omisión hace cumplir la regla previa 3: un campo dependiente que deja de aplicar vuelve a vacío.
- Una página puede sustituir el *reducer* (Dodds), pero solo si un segundo caso concreto lo pide (AHA).

```tsx
// comun/useFormulario.ts
type Valores = Record<string, string>;
export interface Campo<V extends Valores> {
  nombre: keyof V & string;
  omision: string;
  lugar: "a-la-vista" | "mas-opciones";
  aplica?: (v: V) => boolean;                 // regla previa 3
  describir?: (valor: string) => string;      // frase de resumen (regla previa 4)
}
type Accion = { tipo: "cambiar"; nombre: string; valor: string } | { tipo: "reiniciar" };

export function reducerPorOmision<V extends Valores>(campos: Campo<V>[]) {
  return (estado: V, accion: Accion): V => {
    if (accion.tipo === "reiniciar") return inicial(campos);
    const siguiente = { ...estado, [accion.nombre]: accion.valor } as V;
    for (const c of campos) if (c.aplica && !c.aplica(siguiente)) (siguiente as Valores)[c.nombre] = "";
    return siguiente;
  };
}

export function useFormulario<V extends Valores>(campos: Campo<V>[], opciones?: { reducer?: (s: V, a: Accion) => V }) {
  const [valores, despachar] = useReducer(opciones?.reducer ?? reducerPorOmision(campos), campos, inicial);
  const visibles = campos.filter((c) => !c.aplica || c.aplica(valores));
  const getCampoProps = (nombre: keyof V & string, propias: { onChange?: (v: string) => void } = {}) => ({
    id: `campo-${nombre}`,
    value: valores[nombre],
    onChange: (e: { target: { value: string } }) => {
      despachar({ tipo: "cambiar", nombre, valor: e.target.value });
      propias.onChange?.(e.target.value);     // se compone, no se pisa (prop getter)
    },
  });
  // Lo que se resume es lo plegado que sigue en su valor por omisión; se calcula al renderizar, sin efecto.
  const resumen = visibles
    .filter((c) => c.lugar === "mas-opciones" && valores[c.nombre] === c.omision && c.describir)
    .map((c) => c.describir!(c.omision))
    .join(" ");
  return { valores, getCampoProps, visibles, resumen, despachar };
}
```

```tsx
// comun/MasOpciones.tsx
export function MasOpciones({ titulo, resumen, abierta, children }: {
  titulo: string; resumen: string; abierta?: boolean; children: ReactNode;
}) {
  return (
    <>
      <p className="silice-resumen-omisiones">{resumen}</p>
      <details open={abierta}>
        <summary>{titulo}</summary>
        {children}
      </details>
    </>
  );
}
```

`abierta` se calcula en la página: es verdadera si algún campo plegado tiene un error. Así el pliegue se abre solo, como
pide el informe previo (S-3), sin un efecto que sincronice dos estados.

**Prueba que obliga a usarlo:**

- **Guardia de carga** (regla previa 12): en el caso por omisión, los controles visibles de la sección son 8 o menos:
  `getAllByRole("textbox" | "combobox" | "radio" | "checkbox").filter(el => el.checkVisibility?.() ?? true)`. Con
  `<details>`, `toBeVisible()` de jest-dom distingue lo plegado (informe previo).
- **Resumen**: el texto de `resumen` contiene la frase de cada omisión plegada, por ejemplo «Fecha de los precios: hoy».
- **Dependientes**: al cambiar el campo del que dependen, `queryByLabelText(/…/)` es `null` y el cuerpo que se envía lleva
  `""`.
- **Error plegado**: un 422 simulado sobre un campo de «Más opciones» deja el `<details>` abierto y el foco en ese campo.
- **Del reducer y del hook**: `reducerPorOmision` se prueba como función pura, sin DOM; `useFormulario` se prueba con
  `renderHook` de Testing Library (el resumen cambia cuando un campo plegado deja su valor por omisión).

### 3.5 (d) Un flujo de tarea que siempre termina mostrando el paso siguiente

**Patrón:** el estado del flujo es una **unión discriminada** y la fase `hecho` **exige** `siguiente`. Se suman un hook
`useFlujoDeTarea` y un componente `FinDeTarea` que reutiliza `FranjaDelPaso` (tipo `"siguiente"`).

- El envío va en el manejador del evento, no en un efecto (react.dev).
- El foco se mueve al botón **porque el componente se mostró**, y eso sí es trabajo de un efecto según react.dev.

```tsx
// comun/useFlujoDeTarea.ts
export interface PasoSiguiente { texto: string; rotulo: string; ir: () => void }
export type EstadoDelFlujo<R> =
  | { fase: "editando" }
  | { fase: "enviando" }
  | { fase: "error"; error: unknown }
  | { fase: "hecho"; resultado: R; siguiente: PasoSiguiente };   // sin `siguiente`, no compila

export function useFlujoDeTarea<D, R>(
  enviar: (datos: D) => Promise<R>,
  siguientePara: (resultado: R) => PasoSiguiente,                 // parámetro obligatorio: la decisión no se olvida
) {
  const [estado, setEstado] = useState<EstadoDelFlujo<R>>({ fase: "editando" });
  const ejecutar = async (datos: D) => {                          // se llama desde el manejador del botón
    if (estado.fase === "enviando") return;                       // doble clic (UX-18)
    setEstado({ fase: "enviando" });
    try {
      const resultado = await enviar(datos);
      setEstado({ fase: "hecho", resultado, siguiente: siguientePara(resultado) });
    } catch (error) {
      setEstado({ fase: "error", error });                        // lo escrito no se borra (UX-12)
    }
  };
  return { estado, ejecutar, volverAEditar: () => setEstado({ fase: "editando" }) };
}
```

```tsx
// comun/FinDeTarea.tsx
export function FinDeTarea({ queQuedo, siguiente }: { queQuedo: string; siguiente: PasoSiguiente }) {
  const boton = useRef<HTMLButtonElement>(null);
  useEffect(() => { boton.current?.focus(); }, []);              // se ejecuta porque se mostró (react.dev)
  return (
    <div role="status">
      <p>{queQuedo}</p>                                          {/* qué quedó y dónde */}
      <FranjaDelPaso tipo="siguiente" texto={siguiente.texto}
        accion={{ texto: siguiente.rotulo, alPulsar: siguiente.ir }} />
    </div>
  );
}
```

`FranjaDelPaso` necesitaría aceptar una `ref` o un `id` para el foco; ya acepta `id` en `accion`
(`FranjaDelPaso.tsx:12`). Mientras la franja esté a la vista, su botón es el único principal (UX-13).

**En Componer quedaría así** (ejemplo de textos):

- `queQuedo`: «La partida P-0123 quedó en el catálogo de la obra con un precio unitario de 1.234,56 Bs/m³.» Las cifras
  vienen del servidor.
- `siguiente`: «Póngale su cantidad en el presupuesto», con el botón «Agregar al presupuesto», que abre la hoja con el
  diálogo «Agregar partida» y la partida ya elegida. Ese camino ya existe: `ComponerPartida.tsx:71`.

**Prueba que obliga a usarlo:**

- **De comportamiento** (Testing Library con `user-event`): se llena lo mínimo, se pulsa «Guardar composición» con la API
  simulada en éxito y se comprueba:
  - `getByRole("status")` contiene el código y el precio que devolvió el simulado;
  - `getByRole("button", { name: "Agregar al presupuesto" })` existe y `toHaveFocus()`;
  - al pulsarlo, se llama a la navegación con la partida.
  - Con la API en error, no aparece la franja y los campos conservan sus valores.
- **Estática**: en `src/paginas/` se prohíbe `InlineNotification` con `kind="success"` fuera de `FinDeTarea`; todo éxito
  pasa por el componente que exige el paso siguiente. Las excepciones se listan con su motivo, por ejemplo un éxito que
  cierra un diálogo y devuelve a la tarea madre.
- **Del mapa de tareas** (el mapa de Patton escrito como datos): un archivo `tareas.ts` declara, por cada pantalla de
  tarea, su meta y la ruta de su paso siguiente. Una prueba recorre el arreglo y comprueba que **cada `siguiente` existe en
  el enrutador** y que ninguna tarea queda sin destino, salvo las que cierran la columna vertebral (Exportar).

---

## 4. *Hooked* (Nir Eyal, 2014), con sus límites

### 4.1 El modelo

Fuente: «How to Manufacture Desire», https://www.nirandfar.com/how-to-manufacture-desire/ (abierta). El libro *Hooked: How
to Build Habit-Forming Products* (Portfolio, 2014) queda en registro.

1. **Disparador** externo o interno: «the actuator of a behavior».
2. **Acción**: «the behavior designer makes the action as easy as possible».
3. **Recompensa variable**: «Variable schedules of reward are one of the most powerful tools that companies use to hook
   users».
4. **Inversión**: tiempo, datos o esfuerzo que mejoran el servicio «for the next go-around».

**El propio Eyal pone límites:**

- La **matriz de manipulación**, https://www.nirandfar.com/the-art-of-manipulation/ (abierta), pregunta «Will I use the
  product myself?» y «Will the product help users materially improve their lives?». Las respuestas dan cuatro cuadrantes:
  facilitador, vendedor ambulante, animador y traficante.
- La **prueba del arrepentimiento**: ¿lo haría la persona si supiera todo lo que sabe quien diseñó, y se arrepentiría?
  Vista en https://behavioralscientist.org/ask-behavioral-scientist-nir-eyal-regret-test-makes-good-ethics-good-business/
  (registro).

### 4.2 Las críticas

- **Brignull y deceptive.design.** Harry Brignull acuñó «dark patterns» hacia 2010 (registro, según Gray et al. y fuentes
  secundarias). El sitio dice «spreading awareness since 2010» y lista 18 tipos, https://www.deceptive.design/types
  (abierta). Algunos: *preselection*, *nagging*, *obstruction*, *hard to cancel*, *confirmshaming*, *fake urgency* y
  *addictive design* («exploits psychological vulnerabilities to encourage compulsive use»).
- **Gray, Kou, Battles, Hoggatt y Toombs (2018)**, «The Dark (Patterns) Side of UX Design», CHI 2018,
  doi:10.1145/3173574.3174108, PDF: https://par.nsf.gov/servlets/purl/10057203 (abierta). Reorganizan la tipología de
  Brignull en cinco estrategias: *nagging*, *obstruction*, *sneaking*, *interface interference* y *forced action*. Nagging,
  por ejemplo, es la «Redirection of expected functionality that persists beyond one or more interactions».
- **Mathur et al. (2019)**, «Dark Patterns at Scale», CSCW 2019, https://arxiv.org/abs/1907.07032 (abierta, resumen):
  rastrearon cerca de 53.000 páginas de unas 11.000 tiendas y hallaron 1.818 casos de 15 tipos, 183 sitios engañosos y 22
  terceros que venden patrones oscuros llave en mano.
- **McCarthy (2015)**, Thoughtworks, https://www.thoughtworks.com/en-us/insights/blog/addicted-industry-matures (abierta):
  el modelo de Eyal es «nearly identical to that used by casinos». Es una opinión, no un estudio.

### 4.3 Qué es legítimo en una herramienta de trabajo y qué no

| Parte del modelo | Uso legítimo en Sílice | Uso inapropiado | Por qué |
|---|---|---|---|
| Disparador externo | **El paso siguiente** al terminar una tarea (§3.5), con un botón. Un aviso cuando un dato de la persona cambia algo suyo (índices nuevos que vuelven preliminar un reajuste). | Notificaciones para «volver a la app», insistentes o sin tarea detrás (*nagging*). | El disparador sirve a la meta de la persona en el HTA, no a la métrica de uso (Gray: *nagging*). |
| Acción fácil | Valores por omisión **correctos y comunes** (E5), autocompletado y precarga de lo último (regla previa 5). | **Preselección** que empuja hacia lo que conviene al producto. | deceptive.design lista *preselection* como engaño, y NN/g defiende los valores por omisión (E5). La diferencia es **a quién sirve el valor**. En Sílice, la omisión es lo que la norma o la cláusula dicen que es común, y la frase lo declara con «Cambiar». |
| Recompensa | **Retroalimentación inmediata y predecible**: la frase con la cifra del servidor al terminar (regla previa 1), el desglose que se actualiza y «Deshacer». | **Recompensa variable** (rachas, insignias, sorpresas). | En una herramienta de trabajo el refuerzo es **saber que la tarea quedó bien** (golfo de evaluación de Norman). La recompensa variable entra en *addictive design*. |
| Inversión | El catálogo propio, las listas de precios y las cláusulas guardadas hacen la próxima obra más rápida. | Encerrar los datos para que salir cueste: exportación pobre o escondida (*obstruction*, *hard to cancel*). | La inversión es legítima si la persona **se la puede llevar**: Excel y PDF completos, que Sílice ya entrega. |
| Prueba ética | Matriz de Eyal: el equipo usaría Sílice y mejora el trabajo de la persona, así que es «facilitador». Prueba del arrepentimiento para cada empujón. | — | Es la prueba que propone el mismo Eyal; sirve como lista de control, no como garantía. |

---

## 5. Los sistemas de diseño como guardia

| Sistema | Qué hace cumplir y con qué | Fuente |
|---|---|---|
| **IBM Carbon** | Lista de comprobación para que un componente sea «Stable»: solo tokens de color, tipo y espacio («do not contain magic numbers»); contraste de 4,5:1 y 3:1; estados especificados (hover, foco, error…); WCAG AA; Equal Access Checker en cada estado complejo; prueba manual en JAWS, VoiceOver y NVDA; pruebas unitarias con jest y testing-library con al menos 80 % de cobertura; **una prueba de regresión visual (Percy) en la historia por omisión**; historia y documentación en Storybook y en el sitio. | https://carbondesignsystem.com/contributing/component-checklist (abierta) |
| Carbon (accesibilidad) | «Automated accessibility verification tests (AVT) are run for each change»; pruebas manuales «periodically»; etiqueta pública de estado por componente: probado, parcial, manual, no disponible, no probado. | https://carbondesignsystem.com/components/overview/accessibility-status (abierta) |
| Carbon (lint) | `stylelint-plugin-carbon-tokens`: obliga a usar tokens en color, espacio, tipo, movimiento y radio. | https://github.com/carbon-design-system/stylelint-plugin-carbon-tokens (abierta) |
| **GOV.UK** | Criterios para aceptar un componente: *useful* y *unique* con **evidencia** de uso en varios servicios; *usable* probado en investigación con usuarios, incluidas personas con discapacidad; *consistent*; *versatile*. «The Design System team reviews proposals». | https://design-system.service.gov.uk/community/contribution-criteria/ (abierta) |
| GOV.UK (componentes de publicación) | axe se corre contra cada ejemplo de la guía de componentes y **rompe la CI**. Percy corre en cada PR, pero «This isn't a mandatory check»: decide quien revisa. | https://docs.publishing.service.gov.uk/repos/govuk_publishing_components/testing-components.html (abierta) |
| GOV.UK (lecciones) | La guía de componentes y el vocabulario común dan coherencia. Las pruebas automáticas de accesibilidad detectan pronto, pero «can't cover every aspect», así que se mantienen las manuales. | Inside GOV.UK, 2018-02-15, https://insidegovuk.blog.gov.uk/2018/02/15/creating-tools-to-ensure-a-consistent-frontend-on-gov-uk/ (abierta) |
| **Shopify Polaris** | `stylelint-polaris`: «promote Polaris Design System adoption and coverage». Las reglas por categoría sirven para **medir la cobertura**. Cada desactivación de una regla de cobertura exige una descripción con el prefijo «polaris:». | README, https://github.com/Shopify/polaris/blob/main/stylelint-polaris/README.md (abierta). La medición y el prefijo, por búsqueda (registro). |
| **Atlassian** | `@atlaskit/eslint-plugin-design-system`: tokens en lugar de valores fijos; `no-html-button`, `no-html-anchor` y `no-html-heading` (usar los componentes del sistema); reglas de accesibilidad (`icon-label`, `use-modal-title`, `use-textfield-autocomplete` para WCAG 1.3.5); `no-deprecated-imports`; `prefer-primitives`, presentada como «Strictly used for education purposes and discoverability». | README 16.13.6, https://unpkg.com/@atlaskit/eslint-plugin-design-system@16.13.6/README.md (abierta) |
| **Brad Frost** (proceso) | Diez pasos de gobernanza: usar primero lo que existe, hablar con el equipo del sistema, decidir entre caso único y sistema, prototipo, revisión, construcción con pruebas, revisión final, documentación, versión y adopción con QA. | https://bradfrost.com/blog/post/a-design-system-governance-process/ (abierta) |

### Qué funciona, según quienes lo mantienen

1. **El lint se reserva para lo mecánico**: tokens, componentes prohibidos y etiquetas accesibles. Atlassian marca una regla
   como de «educación» y no de bloqueo. Polaris lo usa para **medir** la adopción. En los dos casos, la salida de
   emergencia **exige un motivo escrito**.
2. **Las pruebas de comportamiento y de accesibilidad bloquean la CI** (Carbon AVT, axe en GOV.UK). La **regresión visual
   ayuda a revisar, pero no bloquea** (GOV.UK).
3. **La revisión humana se hace contra criterios con evidencia**: usuarios reales en GOV.UK, la lista de «Stable» en
   Carbon y la revisión final con el equipo de producto en Frost.
4. **Laguna**: ninguna fuente publica una medida de cuánto mejora la usabilidad gracias al lint. Coincide con el primer
   dossier (UX-29): las guardias impiden regresiones y no prueban que una pantalla sea buena.

**Para Sílice.** El repositorio ya tiene la capa estática al estilo Atlassian: `sinJergaInterna.test.ts`, las pruebas de
estilos (`estilosComponer.test.ts`, `estilosBienvenida.test.ts`) y la prueba de coherencia de pestañas del commit
`aeda5ad2`. Faltan las reglas del §3:

- títulos solo con `Seccion`;
- tablas de resultados solo con `TablaConRespuesta`;
- éxito solo con `FinDeTarea`;
- el mapa de tareas.

Todas con una lista de excepciones con motivo, al modo de Polaris. Percy no conviene: es un servicio externo y Sílice es
local. Si algún día hay capturas, que sirvan de ayuda para revisar, no de compuerta (GOV.UK).

---

## 6. Borrador del método de trabajo (15 pasos)

Lo sigue un agente de IA antes y durante la construcción de **cualquier** pantalla, en cualquier proyecto. Los ejemplos
entre paréntesis son de Sílice. Cada paso dice qué deja escrito; si no deja nada, no se hizo.

**Antes de diseñar: la tarea**

1. **Escribir la historia de trabajo y la necesidad.** «Cuando…, quiero…, para poder…», más «Necesito… para que…»
   (Intercom y Klement; GOV.UK). El «para poder» nombra un resultado que la persona reconocería, no una función. *Deja:*
   dos frases. (El resultado es «ponerle cantidad en el presupuesto», no «guardar».)
2. **Ubicar la tarea en el mapa de historias.** ¿De qué actividad de la columna vertebral es costilla? ¿Qué paso viene
   antes y cuál después? (Patton). *Deja:* «viene de…» y «va a…».
3. **Hacer el análisis jerárquico de tareas.** Meta, subtareas y plan; frecuencia de cada subtarea y cuáles son del camino
   crítico (NN/g; Annett y Duncan). Validarlo observando a un usuario real o, al menos, citando lo que dijo (GOV.UK, Spool,
   Linear). *Deja:* el árbol con su plan.
4. **Dibujar el borde de la pantalla sobre el árbol.** Cada borde que cae dentro de una meta exige, en el estado final, un
   significante hacia el paso siguiente (Norman, golfo de ejecución). *Deja:* la lista de pasos siguientes obligatorios.
   Ninguna pantalla termina en «Guardado».

**Diseño: de la tarea a las piezas**

5. **Hacer el inventario de lo que ya existe** en el sistema de diseño y en `comun/` antes de crear algo (Frost: inventario
   y gobernanza, paso 1). *Deja:* qué se reutiliza y qué falta. (`FranjaDelPaso`, `TablaDensa`, `QueEsEsto`, `EstadoVacio`.)
6. **Elegir el tipo de vista y la pregunta que responde** (UX-19; regla previa 1; el «hill» de IBM). *Deja:* tipo, pregunta
   y forma de la frase de respuesta.
7. **Repartir los controles con el HTA.** El camino crítico va a la vista (8 decisiones o menos, regla previa 2); lo
   ocasional, a «Más opciones» con su valor por omisión resumido en una frase (Wroblewski frente a la divulgación
   progresiva, resuelto en el §1.13). *Deja:* la lista de controles visibles y plegados con sus omisiones.
8. **Hacer un boceto en escala de grises con contenido real**: primero la función, la jerarquía con peso y color antes que
   con tamaño, y el espacio solo con los tokens (Refactoring UI; Frost: contenido antes que estética). Después se dibujan
   las cajas de componentes, cada una con una sola responsabilidad (react.dev, paso 1). *Deja:* el boceto y el árbol de
   componentes.
9. **Hacer el recorrido cognitivo sobre el boceto**, con las cuatro preguntas en cada paso (o las dos de Spencer si hay
   prisa), **incluido un paso más allá del final** y los estados de error. No se rediseña durante el recorrido: se anotan
   los fallos, las ideas y los huecos (Wharton et al.; Spencer). *Deja:* la tabla de pasos con su veredicto, y cada fallo
   resuelto en el boceto.
10. **Hacer la tabla de estados**: cargando, vacío, error, parcial, éxito y permiso. Cada estado lleva qué pasó, dónde y
    **un** control al paso siguiente (UX-27; Carbon *Notifications*). Una celda vacía es un defecto. *Deja:* la tabla.

**Construcción**

11. **Escribir primero las pruebas en rojo**, por rol y nombre (Testing Library):
    - la frase de respuesta precede a la tabla;
    - controles visibles por omisión ≤ 8;
    - el estado de éxito muestra el paso siguiente con el foco;
    - con un error, lo escrito no se borra.

    Si la regla es nueva y transversal, se suma su guardia estática con lista de excepciones con motivo (Atlassian,
    Polaris). *Deja:* las pruebas fallando por la razón correcta.
12. **Construir en el orden de «Thinking in React»**:
    - versión estática;
    - estado mínimo en el padre común;
    - lo derivado se calcula al renderizar;
    - los eventos en sus manejadores, no en efectos;
    - los patrones del §3 (sección, tabla con respuesta, formulario con omisiones y flujo que termina en el paso siguiente).

    Una abstracción nueva va a `comun/` solo cuando la pide el segundo caso (Dodds, AHA). *Deja:* las pruebas en verde.
13. **Pulir con reglas, no con gusto.** Solo tokens; nada de animación en acciones frecuentes o de teclado; foco visible;
    Enter y Esc como en la plataforma; no bloquear lo que se teclea; doble envío bloqueado (Kowalski, Freiberg y Vercel;
    UX-06 y UX-18). *Deja:* el *diff* sin valores fijos ni animaciones nuevas.

**Verificación**

14. **Verificar con la máquina y recorrer el mapa.** Suite completa, lint y axe si está instalado. Después se repite el
    recorrido cognitivo **sobre la pantalla construida** y se camina la tarea de principio a fin, entrando y saliendo de la
    pantalla (Patton: «walk the map»; Linear: probar cada decisión en cada tipo de vista). *Deja:* la salida literal de
    las pruebas y el recorrido marcado.
15. **Probar con una persona real y aplicar la prueba ética.** Una sesión observada con el *sponsor user* (IBM) o una
    ronda de 5 (UX-29), con lo que dice citado textual (Linear). Cada empujón (omisión, aviso o recordatorio) pasa la
    prueba del arrepentimiento y no cae en ningún tipo de deceptive.design (§4). *Deja:* el acta con las citas y lo que se
    corrige en la siguiente vuelta del bucle observar, reflexionar y hacer (IBM).

---

## 7. Fuentes no abiertas y lagunas

**No abiertas:**

- «7 practical tips for cheating at design» (Medium, 403);
- el texto del libro *Refactoring UI* (solo el índice y notas de terceros);
- Abramov en Medium (403; nota de 2019 vista en una copia);
- el PDF de Wharton et al. (1994) en Waterloo (404; el proceso se leyó en la tabla 3 de Spencer);
- Center Centre / UIE de Spool (conexión rechazada);
- la página de Atlassian (vacía sin JavaScript; se leyó el README del paquete);
- npm (403);
- el artículo completo de HBR (solo la entrada);
- la entrada original de Klement (falló la carga; se usó la de Intercom).

**Solo registro:**

- *The Design of Everyday Things* (solo prefacio, ensayo y resumen);
- *About Face* y *The Inmates Are Running the Asylum*;
- *User Story Mapping*;
- Annett y Duncan (1967) y Stanton (2006);
- *Hooked*;
- la prueba del arrepentimiento;
- la fecha de 2010 de Brignull;
- el prefijo «polaris:» y la medición de cobertura de Polaris;
- el formato «Who, What, Wow» de IBM.

**Lagunas:**

- No se encontró una evaluación empírica que compare el recorrido cognitivo con pruebas de usuarios **en aplicaciones
  densas de escritorio**. Según una fuente secundaria (Wikipedia, vía búsqueda), la versión de Spencer tiene poca
  validación publicada.
- No se encontró un dato publicado del efecto del lint de diseño sobre la usabilidad.
- No hay una fuente sobre usuarios de Excel en concreto: la transferencia desde Excel se infiere de Spool (conocimiento
  actual) y de la ley de Jakob (primer dossier).
