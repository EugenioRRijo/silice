# Dirección de UX: carga mental en Reajuste, Riesgo y Control

Informe de la revisión de solo lectura del 2026-11-23 sobre el árbol `.worktrees/s2mi2`, rama `feature/ui-aistudio-correcciones`.
Las rutas de `src/` son relativas a `frontend-desktop/`. Las del back (`api/`, `aplicacion/`) son relativas a la raíz. **`core/` no se toca en
ninguna instrucción**: en `core/` solo se leyó qué significan `indice`, `fin` y las fracciones del plan.

Prioridad: **P1** = abruma hoy, se hace primero · **P2** = mejora clara, después · **P3** = pulido o depende de algo más grande.
Cada instrucción dice si es **solo front** o si **necesita back**.

---

## 0. Qué dicen los estudios (y qué se toma de cada uno)

| # | Principio | Fuente | Qué se aplica aquí |
|---|---|---|---|
| E1 | **Carga extraña.** La memoria de trabajo es limitada. Todo lo que obliga a procesar sin ayudar a entender (buscar, recordar, combinar fuentes) le quita capacidad a la tarea real. | Sweller, J. (1988). «Cognitive load during problem solving: Effects on learning». *Cognitive Science* 12(2), 257-285. https://doi.org/10.1207/s15516709cog1202_4 · Whitenton, «Minimize Cognitive Load to Maximize Usability», NN/g, 2013: «every task you eliminate leaves more mental resources for the decisions that truly are essential». https://www.nngroup.com/articles/minimize-cognitive-load/ | Se quitan las decisiones que el sistema ya puede tomar y las cifras que no responden la pregunta. |
| E2 | **Atención dividida.** Cuando hay que juntar en la cabeza dos fuentes separadas (una cifra aquí y su significado en otro lado), la carga sube. Integrarlas la baja. | Chandler, P. y Sweller, J. (1991). «Cognitive Load Theory and the Format of Instruction». *Cognition and Instruction* 8(4), 293-332. https://doi.org/10.1207/s1532690xci0804_2 | La explicación de cada cifra va pegada a ella (en la columna o en la frase), no en el glosario. Dos tablas que responden lo mismo se unen. |
| E3 | **Divulgación progresiva.** Primero, lo que casi todos necesitan; lo avanzado, a pedido. Dos niveles como máximo. Un buen reparto mejora el aprendizaje, la velocidad y los errores. | Nielsen, «Progressive Disclosure», NN/g, 2006. https://www.nngroup.com/articles/progressive-disclosure/ · Carbon, *Forms pattern*: «Progressively disclose additional inputs only as they become relevant». https://carbondesignsystem.com/patterns/forms-pattern/ | Los campos que dependen de otro solo aparecen cuando aplican. Los parámetros de experto van a «Más opciones», de un solo nivel. |
| E4 | **Ley de Hick.** El tiempo de decisión crece con el número y la complejidad de las opciones. Conviene partir las tareas complejas y resaltar la opción recomendada. | Hick (1952) y Hyman (1953), resumidos en *Laws of UX*. https://lawsofux.com/hicks-law/ | Una rejilla de decenas de selectores iguales es el peor caso. Se reemplaza por una frase con la opción por omisión y un ajuste opcional. |
| E5 | **Valores por omisión.** La gente se queda con lo que viene puesto y lo toma como recomendación, así que el valor debe ser el más común y el correcto. | Nielsen, «The Power of Defaults», NN/g, 2005: «pre-populate fields with the most common value if you can determine it in advance». https://www.nngroup.com/articles/the-power-of-defaults/ · Carbon: «Good default values reduce cognitive load». | La parte fija R, el primer año, el responsable, la fuente del estudio y las simulaciones llegan precargados y se resumen en una frase con «Cambiar». |
| E6 | **Formularios: menos campos, orden lógico y estructura visible.** Cada campo que se quita ayuda. Los campos opcionales se eliminan o se marcan. Las reglas de formato se dicen antes. | Whitenton, «Website Forms Usability: Top 10 Recommendations», NN/g, 2016. https://www.nngroup.com/articles/web-form-design/ · Wang, «4 Principles to Reduce Cognitive Load in Forms», NN/g, 2025: «Forms are mental work». https://www.nngroup.com/articles/4-principles-reduce-cognitive-load/ · Wroblewski, «Web Application Form Design», 2005 (la acción principal pesa más y las secundarias menos), https://www.lukew.com/ff/entry.asp?1502, y su libro *Web Form Design: Filling in the Blanks* (Rosenfeld, 2008). | Reajuste pregunta en el orden de la cláusula, convierte en un sí o un no lo que casi siempre «no aplica» y deja un solo botón principal. |
| E7 | **Asistentes.** Sirven para tareas ocasionales o para quien no conoce el dominio. Muestran todos los pasos, ponen verbos concretos y reutilizan lo elegido la vez anterior. | Budiu, «Wizards: Definition and Design Recommendations», NN/g, 2017. https://www.nngroup.com/articles/wizards/ | Reajuste se queda en dos pasos y precarga la cláusula del último estudio guardado. |
| E8 | **Una tabla para buscar valores; un gráfico para ver la forma.** Toda cifra necesita contexto: unidad, comparación y meta. | Few, S., *Show Me the Numbers* (Analytics Press, 2004/2012). Capítulo 3, «Differing Roles of Tables and Graphs»: https://fenix.iseg.ulisboa.pt/downloadFile/1688983004260707/Few_2012_Chpt-3.pdf | «Índice 0,9500» y «Fin 41,05» no tienen unidad ni plan con qué compararse. La matriz de fracciones es en realidad un cronograma: se lee mejor como barras. |
| E9 | **IBCS SUCCESS, regla SAY («Convey a message»).** Cada página o tabla empieza por su mensaje. En la notación, el plan va en contorno, lo real en sólido y el pronóstico achurado. | IBCS Standards 1.2 (2021). https://ibcs.com/standards/ · Resumen de los grupos de reglas: https://en.wikipedia.org/wiki/International_Business_Communication_Standards · El repo ya lo adoptó en `DESIGN.md:80`. | Cada bloque de resultado abre con una frase que responde la pregunta, con la cifra del servidor. |

### Contrato de dirección (skill `ecc:frontend-design-direction`)

- **Propósito:** cada pantalla responde **una** pregunta de obra: cuánto se reajusta, cuánto puede subir y qué partida termina tarde.
- **Público:** ingeniero o presupuestista de obra que lo usa de vez en cuando (el reajuste y el riesgo, una vez al mes o menos). No es una persona de software.
- **Tono:** utilitario, denso y en calma. Es Carbon g10 con carbón y dorado; **no se cambia la estética**.
- **Detalle memorable:** la *frase de respuesta*. Cada resultado abre con una oración en español llano que trae la cifra del servidor, y el detalle queda debajo, plegado.
- **Restricciones:** coma decimal y punto de miles, ninguna cifra calculada en el navegador (RB-2), un solo botón principal a la vista (`DESIGN.md`, «Ayuda de cada pantalla»), animaciones solo de estado (`DESIGN.md`, «Movimiento»), nada de tarjetas KPI (`DESIGN.md:4`; la verificación del backlog ya las descartó).
- **Plegado:** se usa el `<details>`/`<summary>` que ya existe en `riesgo/ResultadoDelRiesgo.tsx:84`, o `comun/QueEsEsto.tsx`. No hace falta inventar otro patrón. Con `<details>`, `toBeVisible()` de jest-dom distingue lo plegado, y eso sirve para probarlo.

**Estados de contenido** de las cuatro vistas. Ya existen, salvo donde se anota:

| Estado | Qué debe verse |
|---|---|
| Cargando | El esqueleto o el `InlineLoading` actual. Riesgo, al probar la precisión, avisa que tarda «cerca de medio minuto». |
| Vacío | El `EstadoVacio` actual, con el botón que lleva a resolverlo (backlog S8, «estados vacíos de Control»). |
| Error | El `detalle` de la API tal cual y el foco en el aviso (ya está así). |
| Parcial | Reajuste «preliminar»: la frase de respuesta lo dice **en la misma oración** que el monto, no en una nota aparte. |
| Éxito | La frase de respuesta y el foco en ella. |
| Permiso | Sin cambio: la cuenta sin permiso ve el aviso actual. |

---

## 1. Reajuste › «La cláusula de reajuste (a cotejar con la Gaceta)»

`src/paginas/reajuste/index.tsx:298-401`, `logica.ts`, y en el back `aplicacion/reajuste.py:280-325` y `api/rutas/reajuste.py`.

### Diagnóstico
El paso 1 muestra a la vez **14 controles y una tabla**. Al menos 6 no aplican en el caso común:
- el método pagadero y su fuente (`index.tsx:346`, `:354`) solo valen con «ambos»;
- la casilla de R (`:378`) solo vale si hay comprobación directa y R > 0;
- el primer año (`:329`) ya cae solo en el inicio del contrato (`logica.ts:176`);
- el responsable (`:376`) ya cae solo en el usuario (`api/rutas/reajuste.py:169`);
- la columna «Peso» solo vale con «Pesos fijos del contrato».

Eso contradice la divulgación progresiva (E3: «only as they become relevant») y multiplica las decisiones (E4). Además, **cada estudio se escribe desde cero**: la API no devuelve la última cláusula guardada (`api/rutas/reajuste.py:208-296`, sin esa ruta), aunque el estudio la guarda (`core/models/moneda.py:179`, `clausula_id`). El estudio de asistentes (E7) pide reutilizar lo elegido la vez anterior.

### La pregunta y la respuesta
- **Pregunta:** «¿Cuánto hay que reconocerle al contratista por la variación de precios en estos períodos, y es definitivo?»
- **Respuesta, lo primero que se ve tras calcular:** «Reajuste reconocido: **12.345,67 Bs** en 3 períodos. Es **definitivo**.» (o «Es **preliminar**: faltan índices publicados»). La cifra es el `Reconocido` de la fila `Total` que ya manda el servidor (`aplicacion/reajuste.py:624-636`).

### Rediseño

**R-1 · P1 · solo front. Los campos que dependen de otro aparecen solo cuando aplican.**
- «Método que rige para el pago» y «Fuente del método que rige» se renderizan **solo** con `mecanismo === "ambos"`. Si se cambia a otro método, `mecanismo_pagadero` y `fuente_pagadero` vuelven a `""`.
- La casilla de R en la comprobación directa se renderiza solo si el método es `comprobacion` o `ambos` **y** la parte fija no es «No». Además se pasa a «Más opciones de la cláusula» (R-3).
- La columna «Peso» de Componentes solo existe con `estructura === "declarada"`. Se filtra en `columnasDeComponente(...)` (`index.tsx:75`) con un parámetro nuevo. Con «por partida», la nota de `:385` dice: «Elija la serie de índices que sigue cada componente. Los pesos salen del presupuesto.»
- Se quita del rótulo «(solo si eligió comparar ambos)» (`index.tsx:346`): ya no hace falta.

**R-2 · P1 · solo front. Método, periodicidad y pesos con botones de opción.**
Cada una tiene 2 o 3 opciones fijas (`contexto.periodicidades`, `mecanismos`, `estructuras`). Un `RadioButtonGroup` las deja todas a la vista con su explicación, sin abrir un desplegable. Se mantienen los valores por omisión actuales (`logica.ts:98-102`).

**R-3 · P1 · solo front. Lo que ya trae un valor se resume en «Más opciones de la cláusula», plegado.**
La línea de resumen, siempre a la vista: «El primer año corre desde el inicio del contrato. El estudio queda a su nombre.» Dentro del pliegue:
- «Inicio del primer año de obra» (el campo actual de `:329`);
- «Responsable» (el campo actual de `:376`);
- la casilla de R en la comprobación directa (solo cuando aplica, según R-1).

**R-4 · P1 · solo front. R se pregunta primero con un sí o un no.**
Hoy se pide una fracción y su fuente aunque la respuesta más común sea «no hay parte fija».
- Pregunta (`RadioButtonGroup`): «¿La cláusula deja una parte del contrato sin reajustar?»
  - «No: se reajusta todo el monto». Es el valor por omisión.
  - «Sí: una parte queda fija».
- Con **No**, no se muestra ningún campo. `armarCuerpo` manda `r: "0"` y `fuente_r: "<fuente de la cláusula>: la cláusula no deja parte sin reajustar"`. `fuente_r` es obligatoria en `aplicacion/reajuste.py:310`, y así queda declarada con la misma fuente.
- Con **Sí**, aparecen dos campos:
  - «Parte fija (como la escribe la cláusula)». Ayuda: «Por ejemplo, 0,10.» Debajo, en vivo, la lectura con `aPorcentaje` + `formatoEsVe` (`comun/porcentaje.ts`): «0,10: el 10 % del monto queda fijo y el 90 % se reajusta.» El 90 % sí sería una cuenta del navegador, así que la frase va **sin** ese 90 %: «0,10: el 10 % del monto queda fijo.»
  - «¿Dónde lo dice?», precargado con la fuente de la cláusula y editable.
- En toda la pantalla, el nombre visible es «parte fija». La letra R solo aparece entre paréntesis en el detalle del resultado y en el Excel.
- *Decisión simulada* (regla de Eugenio del 2026-10-30): el texto automático de `fuente_r` con «No» se anota en `docs/ESTADO.md` §4 para que Eugenio lo ratifique.

**R-5 · P1 · solo front. El orden sigue al documento que la persona tiene en la mano.**
Grupos con un título que es una pregunta (E6):
1. «¿Qué contrato es?»: «Contrato y cláusula de reajuste». Es el campo `fuente` actual (`:375`), que se sube al principio. Ayuda: «Número del contrato, cláusula y fecha; por ejemplo, Contrato 045-2026, cláusula 12.»
2. «¿Cuándo empezó y cuánto dura?»: «Inicio del contrato» y «Duración (meses)».
3. «¿Cómo se reajusta?»: Método, Periodicidad, «Mes base de los índices» y, si aplica, el método que rige el pago.
4. «¿Qué parte queda fija?»: R-4.
5. «¿Qué índices sigue cada componente?»: Pesos y la tabla de Componentes.

Con esto, el caso común deja **8 controles a la vista** (antes, 14). El título h2 pasa a «1. La cláusula del contrato», y la nota bajo él dice: «Tenga a mano la cláusula de variación de precios. Copie lo que dice, tal cual.»

**R-6 · P1 · necesita back (chico). Precargar la última cláusula guardada de la obra.**
- Back:
  - en `aplicacion/reajuste.py`, una función `ultima_clausula(sesion, proyecto, version)` que lea la `ClausulaReajuste` del último `EstudioReajuste` de esa obra (`core/models/moneda.py:170`; solo lectura, el modelo no cambia) y la devuelva con las mismas claves de `ClausulaTextos` y sus componentes;
  - en `api/rutas/reajuste.py`, `GET /v1/reajuste/ultima-clausula?proyecto=&version=`, que responde con `{clausula, componentes, estudio, fecha_calculo}` o con `null`;
  - prueba de back: un estudio guardado vuelve con sus textos tal cual, y sin estudios vuelve `null`.
- Front: si llega, el formulario arranca con esa cláusula y aparece una franja informativa (no `FranjaDelPaso`, porque no hay paso pendiente): «Precargado con la cláusula del estudio n.º 12 (calculado el 03/10/2026). Revísela si el contrato cambió.» Lleva un botón terciario: «Empezar con la cláusula en blanco».

**R-7 · P1 · solo front. El resultado abre con la frase de respuesta.**
- Bajo el h2 «Resultado del reajuste» (sustituye a `ETIQUETA_RESULTADO`, `index.tsx:139`), un párrafo con `role="status"`:
  «Reajuste reconocido: {Reconocido de la fila Total} {moneda} en {n} períodos. {estado}».
  - `{n}` cuenta las filas sin la fila Total: es un conteo, no un monto.
  - `{estado}` es «Es definitivo.» o «Es preliminar: faltan índices publicados.» (`estadoDelEstudio`, `logica.ts:70`).
- Debajo, una lista de definición con los tres totales de la fila Total:
  - «Por la fórmula de índices (escalatoria)»: `Escalatoria`;
  - «Recalculando con precios nuevos (comprobación directa)»: `Comprobación`;
  - «Diferencia entre los dos métodos»: `Diferencia`.
  Si un total es «no disponible», la línea dice «no disponible: falta la versión con precios actualizados».
- La tabla por período queda a la vista. «En la otra moneda» (`index.tsx:476-481`) pasa a `<details>` con el resumen «Ver los montos en {otra moneda}».
- Avisos y marcas, igual que hoy.

**R-8 · P2 · solo front. Guardar sin volver a escribir.**
«Fuente del estudio» (`:499`) llega precargada con la fuente de la cláusula. «Responsable del estudio» (`:500`) se resume en la frase «Se guarda a su nombre de usuario», con el campo dentro de un `<details>` «Cambiar el responsable».

**R-9 · P2 · necesita back (chico). Tomar lo ejecutado de las valuaciones si existen.**
- Back: `hay_valuaciones: bool` en `ContextoRespuesta` (`api/rutas/reajuste.py:114`).
- Front: `con_valuaciones` arranca en `true` cuando la obra las tiene. El texto de `:426` pasa a «Tomar lo ejecutado de las valuaciones registradas (recomendado)».

**R-10 · P3 · solo front.** Sin cambios de diseño en el paso 2, salvo lo que ya trae el backlog («Anterior: la cláusula», «Calcular el reajuste»; backlog S8, `reajuste/index.tsx:443`). **No se duplica.**

### Textos exactos

| Dónde | Texto |
|---|---|
| h2 del paso 1 | 1. La cláusula del contrato |
| nota bajo el h2 | Tenga a mano la cláusula de variación de precios. Copie lo que dice, tal cual. |
| grupo 1 | ¿Qué contrato es? |
| campo `fuente` | Contrato y cláusula de reajuste. Ayuda: Número del contrato, cláusula y fecha; por ejemplo, Contrato 045-2026, cláusula 12. |
| grupo 2 | ¿Cuándo empezó y cuánto dura? |
| grupo 3 | ¿Cómo se reajusta? |
| opciones del método | Fórmula por índices (escalatoria): se multiplica lo ejecutado por la variación de los índices del BCV. / Recálculo con precios nuevos (comprobación directa): se vuelve a valorar lo ejecutado con los precios de cada período. / Comparar ambos métodos: se calculan los dos y usted dice cuál rige para el pago. |
| campo mes base | Mes base de los índices. Ayuda: El mes contra el que se comparan los índices; casi siempre es el mes de la oferta. Confírmelo en la cláusula. |
| grupo 4 | ¿Qué parte queda fija? |
| pregunta de R | ¿La cláusula deja una parte del contrato sin reajustar? |
| opciones | No: se reajusta todo el monto / Sí: una parte queda fija |
| campo R (con Sí) | Parte fija (como la escribe la cláusula). Ayuda: Por ejemplo, 0,10. Escriba con coma decimal. |
| lectura en vivo | 0,10: el 10 % del monto queda fijo. |
| campo fuente_r | ¿Dónde lo dice? |
| grupo 5 | ¿Qué índices sigue cada componente? |
| opciones de pesos | Calcularlos del presupuesto (recomendado) / Usar los pesos fijos del contrato |
| pliegue | Más opciones de la cláusula |
| resumen del pliegue | El primer año corre desde el inicio del contrato. El estudio queda a su nombre. |
| casilla R (en el pliegue) | Restar también la parte fija en la comprobación directa |
| precarga | Precargado con la cláusula del estudio n.º {id} (calculado el {dd/mm/aaaa}). Revísela si el contrato cambió. · Empezar con la cláusula en blanco |
| h2 del resultado | Resultado del reajuste |
| frase de respuesta | Reajuste reconocido: {monto} {moneda} en {n} períodos. Es definitivo. · (preliminar) …Es preliminar: faltan índices publicados. |
| pliegue de la otra moneda | Ver los montos en {otra moneda} |

### Pruebas (Vitest y Testing Library)
1. **Rojo primero, en `Reajuste.test.tsx`:**
   - con el método «Fórmula por índices», `queryByLabelText(/Método que rige para el pago/)` es `null`;
   - al elegir «Comparar ambos métodos», aparece;
   - con «No: se reajusta todo el monto», `queryByLabelText(/Parte fija/)` es `null` y el cuerpo que se manda a `/v1/reajuste/calcular` lleva `r: "0"` y `fuente_r` que empieza con la fuente escrita (en `logica.test.ts`, sobre `armarCuerpo`).
2. **Guardia de carga:** dentro de la sección del paso 1, los controles **visibles** (`getAllByRole("textbox"|"combobox"|"radiogroup"|"checkbox")` filtrados por `toBeVisible`) son 8 o menos en el caso por omisión. La frase de respuesta del resultado precede a la primera tabla (`compareDocumentPosition`) y trae el `Reconocido` de la fila Total formateado en es-VE.

---

## 2. Riesgo › «Serie que mueve cada insumo»

`src/paginas/riesgo/ParametrosDelRiesgo.tsx:70-120`, `RiesgoDeLaObra.tsx:250-300`, `logica.ts`. En el back: `aplicacion/riesgo/obra.py:295-372` y `api/rutas/riesgo.py`.

### Diagnóstico
La rejilla pone un `Select` por insumo (`ParametrosDelRiesgo.tsx:98-111`). En una obra mediana son decenas, todos con el mismo valor («Sin serie propia») y **antes** del botón «Proyectar». La persona lee eso como trabajo obligatorio. En realidad el valor por omisión es válido: en Bs el insumo sigue a la tasa del BCV, y en USD queda fijo (`ParametrosDelRiesgo.tsx:67-69`). Es el peor caso de Hick (E4) y una carga extraña pura (E1).

Además, «Parámetros comunes» (`:86-92`) pone a la vista la semilla, los meses de historia y las simulaciones, que son parámetros de experto con un valor recomendado (`logica.ts:141`). Eso contradice E3 y E5.

### La pregunta y la respuesta
- **Pregunta:** «¿Cuánto puede subir el presupuesto de esta obra si los precios siguen como venían, y cuánta reserva dejo?»
- **Respuesta, lo primero tras proyectar:** «En 8 de cada 10 simulaciones la obra no pasa de **{P80}**. Deje una reserva de **{reserva}** sobre el presupuesto base de **{total_base}**.» Las tres cifras ya llegan del servidor (`api/riesgo.ts:71-74`).

### Rediseño

**S-1 · P1 · solo front. La rejilla se pliega y se resume en una frase.**
- Orden de la pantalla: Versión → «Meses del plazo» → fecha de inicio (como campo solo si es obligatoria; si no, se resume en una frase) → **frase de las series** → botón principal «Proyectar el riesgo».
- La frase de las series se arma solo con la moneda (`insumos.moneda`) y los conteos de `mapa` y de `insumos.insumos + componentes`, que son conteos y no montos:
  - Bs y ninguna serie: «Cada insumo se moverá con la tasa del BCV (Bs por USD), porque ninguno tiene una serie propia. Es lo usual; si quiere afinar, elija la serie de los que más pesan.»
  - USD y ninguna serie: «En una obra en USD, un insumo sin serie no se mueve: así el resultado saldrá sin subida. Elija la serie de los insumos que más pesan.» Va con el ícono de aviso y su palabra, y el botón secundario «Elegir las series» abre el pliegue y lleva el foco al buscador. **Es la misma tarea** que la del backlog S8 «Riesgo avisa antes de proyectar sin series y lleva a elegirlas» (`RiesgoDeLaObra.tsx:259`): se construyen juntas.
  - Con series: «{n} de {total} insumos siguen una serie propia; los demás, la tasa del BCV.» En USD termina en «…; los demás quedan fijos.»
- La rejilla entera va a un `<details>` con el resumen «Elegir la serie de cada insumo (opcional)». Las notas de precarga (`nota`, `aviso`) y de mezclas (`:112-116`) quedan dentro, arriba.

**S-2 · P1 · solo front. Dentro del pliegue: buscar y aplicar a varios a la vez.**
- Un `Search` de Carbon, «Buscar insumo», filtra la lista por texto con `normalizar` de `comun/normalizar.ts`, sin tildes ni mayúsculas.
- Una fila de acción sobre la lista: el `Select` «Serie para los insumos mostrados» y el botón terciario «Aplicar a los {n} insumos mostrados». Llama a `alElegirSerie` por cada insumo filtrado. Es la acción de la persona, no un cálculo.
- La lista pasa a **una columna**: el rótulo es el insumo y el `Select` va en `size="sm"`. Así se lee de arriba abajo como una lista de materiales y no como una rejilla.
- Al pie: «Quitar todas las series» (terciario).
- Esto **no** es el «Proponer series» que el backlog descartó (no había función en el back). Aquí Sílice no propone nada: la persona elige y aplica en bloque.

**S-3 · P1 · solo front. Los parámetros de experto, a «Avanzado».**
- A la vista queda solo «Meses del plazo».
- Resumen visible: «Con 2.000 simulaciones sobre 36 meses de historia y semilla 1.» Las cifras salen de lo que está escrito en los campos.
- Dentro de un `<details>` «Avanzado: cómo se simula» van «Simulaciones a correr», «Semilla…», «Meses de historia» y «Simulaciones por fecha probada» (`RiesgoDeLaObra.tsx:279`).
- Si un campo plegado trae un error de lectura, el pliegue se abre solo y el foco va al campo, como hoy con `cajaDelError`.

**S-4 · P1 · solo front. El resultado abre con la frase de respuesta.**
- En `ResultadoDelRiesgo.tsx:46-60`, antes de la lista `dl`, un párrafo con el texto de arriba (`p80`, `reserva`, `total_base`). Las cifras salen con `monto()`, `logica.ts:178`.
- La `dl` sigue debajo como detalle. La reserva deja de ser el último renglón y queda en la frase. **Es la misma tarea** que la del backlog S8 «Riesgo: la reserva para el P80 como cifra de pantalla» (`ResultadoDelRiesgo.tsx:52`).
- La sección «Probar precisión con meses pasados» (`RiesgoDeLaObra.tsx:274-292`) baja **después** del resultado, con el h3 «¿Qué tan confiable es esta cuenta?» y el botón secundario «Probarla con meses pasados (tarda cerca de medio minuto)». Antes de proyectar no se muestra: no tiene sentido probar lo que todavía no se ha calculado.

**S-5 · P2 · solo front. Después de proyectar, «empiece por estos».**
`datos.contribucion` ya viene ordenada de mayor a menor (`api/riesgo.ts:75`). Dentro del pliegue de series, si hay una proyección, los insumos se ordenan por ese orden y los 5 primeros llevan una marca de texto: «Mueve más el total». Lo que no está en `contribucion` va después, en orden alfabético.

**S-6 · P2 · necesita back (chico). Agrupar por tipo.**
- Back: en `aplicacion/riesgo/obra.py:295` (`_descripciones`), que ya recorre `materiales`, `equipos` y `mano_obra`, devolver además `tipos: dict[str, "material" | "equipo" | "mano_obra"]`. En `api/rutas/riesgo.py`, agregarlo a la respuesta de `/insumos` como campo **nuevo y opcional**, para no romper a nadie.
- Front: la lista se agrupa bajo «Materiales ({n})», «Equipos ({n})» y «Mano de obra ({n})» (los rótulos de `comun/tiposDeInsumo.ts`). Cada grupo lleva su propio «Usar la misma serie para todos los {grupo}».

**S-7 · P3 · necesita back. Ordenar por peso antes de la primera proyección.**
El servidor manda el peso de cada insumo en el total base. Se ordena con él, sin que el navegador lo calcule.

### Textos exactos

| Dónde | Texto |
|---|---|
| botón principal | Proyectar el riesgo |
| frase de series (Bs, sin series) | Cada insumo se moverá con la tasa del BCV (Bs por USD), porque ninguno tiene una serie propia. Es lo usual; si quiere afinar, elija la serie de los que más pesan. |
| frase de series (USD, sin series) | En una obra en USD, un insumo sin serie no se mueve: así el resultado saldrá sin subida. Elija la serie de los insumos que más pesan. |
| frase de series (con series) | {n} de {total} insumos siguen una serie propia; los demás, la tasa del BCV. / …; los demás quedan fijos. |
| pliegue | Elegir la serie de cada insumo (opcional) |
| buscador | Buscar insumo |
| acción en bloque | Serie para los insumos mostrados · Aplicar a los {n} insumos mostrados · Quitar todas las series |
| marca (S-5) | Mueve más el total |
| pliegue avanzado | Avanzado: cómo se simula |
| resumen avanzado | Con {2.000} simulaciones sobre {36} meses de historia y semilla {1}. |
| frase de respuesta | En 8 de cada 10 simulaciones la obra no pasa de {P80}. Deje una reserva de {reserva} sobre el presupuesto base de {total_base}. |
| h3 de la prueba | ¿Qué tan confiable es esta cuenta? |
| botón de la prueba | Probarla con meses pasados (tarda cerca de medio minuto) |

### Pruebas
1. **En `RiesgoDeLaObra.test.tsx`:** con 12 insumos y sin abrir el pliegue, ningún `combobox` de serie es visible (`toBeVisible` falso), y la frase de Bs está en pantalla. En USD sin series, la frase de aviso y el botón «Elegir las series» abren el pliegue.
2. **Acción en bloque:** se busca «cemento», se elige una serie, se pulsa «Aplicar a los 2 insumos mostrados» y luego «Proyectar el riesgo». El `mapa` del cuerpo que recibe el `proyectarObra` simulado tiene exactamente esos dos insumos. La frase de respuesta precede a la `dl` del resultado.

---

## 3. Control › «Reproyección por partida»

`src/paginas/control/PestanasDeResultados.tsx:257-304`, `logica.ts:364`. En el back: `aplicacion/control_tablas.py:459-480`, `aplicacion/causas.py:103-126` y `api/rutas/control.py:699-779`.

### Qué significan hoy las cifras
Se leyó `core/budget/valor_ganado.py:641-660` y `:476-488`.
- **«Índice» 0,9500** = cantidad ejecutada ÷ cantidad que el plan pedía a la fecha de corte. Es decir: «lleva el 95 % de lo que el plan pedía a esta fecha». Sin avance propio, es el SPI de toda la obra.
- **«Fin (día hábil)» 41,05** = el día hábil, contado desde el inicio del calendario de la línea base, en que termina lo que le falta. Tiene decimales porque el ritmo es continuo.
- **Nota:** «detenida» = el plan ya pedía trabajo y no hay nada medido. «sin evidencia propia: SPI global» = todavía no le toca según el plan, y se supone el ritmo de toda la obra.

### Diagnóstico
Las dos cifras no tienen unidad ni plan con qué compararlas (Few, E8): 0,9500 no dice «más lenta», y 41,05 no es una fecha. La tabla repite las partidas de «Atraso por partida» (`:257-274`), dos bloques más arriba. Para saber qué partida termina tarde hay que cruzar tres bloques: el atraso, el término y la reproyección. Eso es atención dividida (E2).

### La pregunta y la respuesta
- **Pregunta:** «¿Qué partidas van a terminar tarde, cuándo y por qué?»
- **Respuesta primero:** «3 de 12 partidas terminarán después de su plan. La obra termina el {t.reproyectado}; el plan base decía {t.plan_base}.» El conteo sale de `calculo.atrasos.length` y del número de filas de la reproyección. Las fechas son los textos de `terminos` (`logica.ts:217`), que ya traen «día N (dd/mm/aaaa)».

### Rediseño

**C-1 · P1 · solo front. Una sola tabla, no dos.**
- Se unen «Atraso por partida» y «Reproyección por partida» en un bloque con el h2 **«Cuándo termina cada partida»**. La frase de respuesta va justo debajo.
- Columnas mientras no llegue el back (C-2):
  - «Partida»;
  - «Lleva de lo planificado» (`aPorcentaje(Indice)` → `formatoEsVe`, «95 %»);
  - «Días de atraso» (de `calculo.atrasos`, cruzado por código; vacío si no hay atraso);
  - «Qué pasa»: la causa del atraso o la nota traducida.
- Notas traducidas en el front (`logica.ts`, tabla de rótulos):
  - «detenida» → «Debió empezar y no tiene avance medido»;
  - «sin evidencia propia: SPI global» → «Aún no le toca: se supone el ritmo de toda la obra»;
  - vacío → «».
- Orden: primero las que tienen atraso, de más a menos días. Es un orden, no una cuenta.
- Sobre la tabla, la ayuda del encabezado «Lleva de lo planificado» (una línea pegada a la tabla, E2): «100 % = va al ritmo del plan. Menos de 100 %, va más lenta: 95 % quiere decir que hizo 95 de cada 100 unidades que el plan pedía a esta fecha.»
- Se **quita** la columna «Fin (día hábil)» hasta que llegue C-2: un día hábil con decimales no responde nada.
- El párrafo de `:270-273` se integra en la ayuda.

**C-2 · P1 · necesita back (chico, solo `aplicacion/` y `api/`). Fechas en vez de días hábiles, y la descripción.**
En `aplicacion/control_tablas.py:459` (`filas_de_reproyeccion`), a cada fila se le agregan:
- «Descripción»: la de la partida en el presupuesto;
- «Termina»: la fecha `dd/mm/aaaa` del día `techo_de_dias(p.fin)` con `dia_habil(...)`, como hace `dia_con_fecha` en `aplicacion/control.py:458`;
- «Según el plan»: la fecha del último período activo del plan por `dias_por_periodo`, la misma cuenta que `aplicacion/causas.py:115-119`. Se **extrae** a una función común para no duplicarla;
- «Días de atraso»: el mismo `dias` de `causas.atrasos`.
Con eso, el front deja de cruzar `atrasos` con la reproyección y la tabla final queda así:
**Partida · Descripción · Lleva de lo planificado · Termina · Según el plan · Días de atraso · Qué pasa.**
Las claves viejas («Indice», «Fin (dia habil)») se mantienen un tiempo para el Excel y las pruebas existentes (`Control.test.tsx:88`).

**C-3 · P2 · necesita back (chico). La diferencia de la obra en días.**
`terminos.atraso_dias` (entero, del servidor) para que la frase diga «…, {n} días hábiles después del plan base». El front no la calcula.

**C-4 · P2 · solo front. Detalle a pedido.**
Si hay más de 8 partidas con obra pendiente, se ven primero las atrasadas y el resto queda en `<details>` «Ver las {n} partidas que van a tiempo».

### Textos exactos

| Dónde | Texto |
|---|---|
| h2 | Cuándo termina cada partida |
| frase de respuesta | {a} de {n} partidas terminarán después de su plan. La obra termina el {día N (dd/mm/aaaa)}; el plan base decía {día M (dd/mm/aaaa)}. · (sin atrasos) Ninguna partida va a terminar después de su plan. |
| columna | Lleva de lo planificado |
| ayuda de la columna | 100 % = va al ritmo del plan. Menos de 100 %, va más lenta: 95 % quiere decir que hizo 95 de cada 100 unidades que el plan pedía a esta fecha. |
| columnas (con C-2) | Partida · Descripción · Lleva de lo planificado · Termina · Según el plan · Días de atraso · Qué pasa |
| notas | Debió empezar y no tiene avance medido · Aún no le toca: se supone el ritmo de toda la obra |
| pliegue | Ver las {n} partidas que van a tiempo |

### Pruebas
1. **En `Control.test.tsx`:** con la fila de prueba `Indice: "0.8000"`, la celda dice «80 %», no hay ninguna columna «Fin (día hábil)», hay un solo h2 de partidas (no «Atraso por partida» y «Reproyección por partida») y la frase de respuesta precede a la tabla.
2. **Back (pytest):** `filas_de_reproyeccion` devuelve «Termina» y «Según el plan» como fechas `dd/mm/aaaa` coherentes con `dia_con_fecha`, y «Días de atraso» igual a `causas.atrasos` para la misma partida. Es un oráculo cruzado: dos rutas de cálculo que deben coincidir.

---

## 4. Control › «Plan reproyectado»

`src/paginas/control/PestanasDeResultados.tsx:305-316` y, en el back, `aplicacion/control.py:471-481`.

### Qué es cada cifra hoy
Se leyó `core/budget/valor_ganado.py:525-587`. Cada casilla es la **fracción de la cantidad total de la partida** que se hace en ese período:
- hasta el corte es **lo medido**;
- después del corte es **lo proyectado** al ritmo actual.

Cada columna de partida suma 1. Por ejemplo, 0,2375 en la Semana 3 de G-0004 quiere decir «el 23,75 % de G-0004 se hace en la Semana 3».

### Diagnóstico
Es un cronograma presentado como una matriz de 10 × 12 cifras de cuatro decimales, sin unidad, sin separar lo medido de lo proyectado y sin el plan original al lado. Few (E8) diría que la pregunta es de forma (cuándo y cuánto se corre), no de buscar un valor. Además, IBCS (E9) y el propio `DESIGN.md:80` ya piden plan en contorno, real en sólido y pronóstico achurado.

### La pregunta y la respuesta
- **Pregunta:** «Si todo sigue a este ritmo, ¿cómo queda el calendario semana a semana?»
- **Respuesta primero:** «Con el ritmo actual, el trabajo llega hasta la {última etiqueta} (el plan base terminaba en la {etiqueta del plan}).» La última etiqueta es la de la última fila que manda el servidor. La del plan base necesita back (P-3); mientras no llegue, la frase termina en la primera parte.

### Rediseño

**P-1 · P1 · solo front. Se pliega, se traspone y se lee en por ciento.**
- La matriz entera va a `<details>` con el resumen «Ver el plan semana a semana (lo medido y lo que falta de cada partida)». Encima, a la vista, solo la frase de respuesta.
- Se **traspone** en la presentación: una fila por partida y una columna por período. El tiempo corre de izquierda a derecha, como en un cronograma.
- Cada casilla con `aPorcentaje` + `formatoEsVe`: «23,75 %». La casilla vacía queda vacía, sin «0».
- La leyenda va pegada a la tabla (E2): «Cada casilla es la parte de la partida que se hace en ese período: 23,75 % quiere decir casi la cuarta parte de su cantidad total. Hasta el corte es lo medido; después, lo proyectado a su ritmo actual.»
- El rótulo accesible de la tabla: «Plan reproyectado: parte de cada partida por período».

**P-2 · P2 · necesita back (chico). Separar lo medido de lo proyectado.**
- Back: `periodo_del_corte: int` en la respuesta de `/v1/control/...`. Es el número del último período medido, el que `reproyectar` ya conoce por `_corte`. Se calcula en `aplicacion/` a partir de `resultado.estado` y `calculo.dia`, sin tocar `core/`.
- Front: los encabezados dicen «Semana 4 · medida» y «Semana 7 · proyectada», y las columnas proyectadas llevan el fondo achurado de la notación IBCS (los tokens de pronóstico que ya existen; el color nunca va solo, porque el encabezado lo dice).

**P-3 · P2 · necesita back (chico). El plan base al lado.**
- Back: devolver por partida su `plan` base (las fracciones de `resultado.estado.partidas[].plan`) y la etiqueta del último período del plan base.
- Front: completa la frase de respuesta. En la fila de cada partida, la columna «Fin del plan» con la etiqueta del plan base.

**P-4 · P3 · solo front, con P-2 y P-3. Cronograma de barras en lugar de cifras.**
- Una barra por partida: plan base en **contorno**, lo medido en **sólido** y lo proyectado **achurado** (`DESIGN.md:80`). Las cifras de cada casilla quedan en la tabla plegada como respaldo exacto, como hacen los demás gráficos del repo (`DESIGN.md:32`: «cada gráfico ya trae su tabla de montos exactos»).
- Componente nuevo en `comun/` (para que Tablero y Recuperación también puedan usarlo), con la paleta de `comun/paletaGraficos.ts`.

### Textos exactos

| Dónde | Texto |
|---|---|
| h2 | Plan reproyectado |
| frase de respuesta | Con el ritmo actual, el trabajo llega hasta la {Semana 12} (el plan base terminaba en la {Semana 10}). |
| pliegue | Ver el plan semana a semana (lo medido y lo que falta de cada partida) |
| leyenda | Cada casilla es la parte de la partida que se hace en ese período: 23,75 % quiere decir casi la cuarta parte de su cantidad total. Hasta el corte es lo medido; después, lo proyectado a su ritmo actual. |
| encabezados (P-2) | {Semana 4} · medida / {Semana 7} · proyectada |
| columna (P-3) | Fin del plan |

### Pruebas
1. **En `Control.test.tsx`:** con un `plan` de prueba de 2 períodos × 2 partidas, la tabla plegada no es visible al entrar. Tras abrir «Ver el plan semana a semana», tiene una fila por partida (no por período) y la casilla `"0.2375"` dice «23,75 %».
2. La frase de respuesta nombra la etiqueta de la **última** fila que mandó el servidor (oráculo: el dato del simulado, no una constante del componente).

---

## 5. Reglas generales para el resto de Sílice

1. **Una pantalla o un bloque, una pregunta. La primera línea es la respuesta**, en una frase con la cifra del servidor, y las tablas van debajo como respaldo. *IBCS SAY, «Convey a message» (https://ibcs.com/standards/); Few, cap. 3.*
2. **A la vista, 8 decisiones o menos por paso.** Lo demás va en un solo nivel de «Más opciones…» o «Avanzado: …», nunca en un pliegue dentro de otro. *Nielsen, Progressive Disclosure (NN/g 2006, dos niveles como máximo); ley de Hick (lawsofux.com).*
3. **Un campo que depende de otro solo existe cuando aplica.** No se deshabilita ni se rotula «(solo si…)», y al ocultarse vuelve a vacío. *Carbon Forms: «Progressively disclose additional inputs only as they become relevant».*
4. **Todo parámetro con valor recomendado viaja precargado y resumido en una frase visible** («Con 2.000 simulaciones…»), con su ajuste a un clic. *Nielsen, The Power of Defaults (NN/g 2005); Carbon: «Good default values reduce cognitive load».*
5. **Lo que se escribió la vez anterior vuelve precargado y se dice de dónde viene**, con salida para empezar en blanco. *Budiu, Wizards (NN/g 2017): reutilizar lo elegido antes.* Riesgo ya lo hace con el mapa de series (DS-90); falta en Reajuste y en otras pantallas.
6. **Ninguna cifra sin unidad y sin con qué compararla.** Una fracción se muestra en % y dice «de qué»; un día hábil, como fecha; un índice, como «lleva X % de lo planificado»; lo real, junto al plan. *Few, Show Me the Numbers; IBCS, notación del plan y lo real (`DESIGN.md:80`).*
7. **La explicación va pegada a la cifra** (ayuda de la columna o frase de la tabla) y no solo en «¿Qué es esto?» o en el glosario. *Chandler y Sweller (1991), efecto de atención dividida.*
8. **Si dos tablas responden la misma pregunta, se unen**; si una tabla no responde ninguna, se pliega. *Sweller (1988), carga extraña; Whitenton (NN/g 2013): «every task you eliminate…».*
9. **Las matrices y los detalles por período o por partida van plegados tras la frase**, con un resumen que dice qué hay y cuántos («Ver las 12 partidas…»). *NN/g, Progressive Disclosure.*
10. **Ninguna sigla sola como rótulo** (R, Km, SPI, CPI, EAC, P50, P80, V', FCAS). Primero la palabra («parte fija», «factor de escalatoria»), y la sigla entre paréntesis después o solo en el detalle y en el Excel. *Wang, 4 Principles to Reduce Cognitive Load in Forms (NN/g 2025): claridad y lenguaje llano.*
11. **Se pregunta en el orden del documento que la persona tiene en la mano** (contrato, acta o factura), y lo que casi siempre «no aplica» se pregunta con un sí o un no antes de pedir una cifra. *Whitenton, Top 10 Recommendations for Forms (NN/g 2016); Wroblewski, Web Form Design (2008).*
12. **La regla se vigila con pruebas.** Una prueba de componente por pantalla cuenta los controles visibles del paso por omisión (8 o menos), y `src/paginas/sinJergaInterna.test.ts` se amplía con una lista de siglas que no pueden ir solas en un `labelText` ni en un `titulo` de columna.

---

## 6. Otras pantallas que probablemente sufren lo mismo

Se miraron por encima con conteos de controles y búsqueda de siglas. Conviene confirmarlas una por una antes de construir.

| Pantalla | Archivo:línea | Síntoma | Regla |
|---|---|---|---|
| Control › «Calcular al corte» | `src/paginas/control/PestanasDeResultados.tsx:98-118` | Km y «Parte del contrato que no se reajusta (R)» como fracciones sueltas en la barra del corte. Es el mismo problema de R que en Reajuste. | 3, 6, 10 |
| Control › Valor ganado | `PestanasDeResultados.tsx:155` y `:160-164` | La nota «SPI y CPI, 1,00 o más…» va lejos de las cifras, en una tabla de indicadores sin frase de respuesta. | 1, 7, 10 |
| Control › Término y costo final | `PestanasDeResultados.tsx:277-293` y `aplicacion/control.py:488` | «Sin estudio de reajuste guardado: V' = V.» es fórmula interna a la vista. «EAC» en el rótulo. | 10 |
| Control › Recuperación | `PestanasDeResultados.tsx:390` y `:412-416` | «Día hábil objetivo» se pide como número de día hábil, no como fecha, y la tabla de opciones tiene 8 columnas sin frase de respuesta. | 1, 6 |
| Control › Valuaciones | `src/paginas/control/PestanaValuaciones.tsx:207-270` | 17 controles: 5 de cabecera y 5 por cada línea medida (cantidad, fecha, observación, causa…). | 2, 4, 9 |
| Control › Línea base | `src/paginas/control/PestanaLineaBase.tsx:155-177` y `:246-274` | «Días hábiles por período» y los feriados a mano, siempre visibles; «Parámetro a cambiar» con nombres internos. | 2, 4, 10 |
| Tablero | `src/paginas/tablero/index.tsx:135` | SPI y CPI explicados en una nota aparte. | 7, 10 |
| Presupuesto › Parámetros | `src/paginas/hoja/PestanaParametros.tsx:74` | «FCAS … 6,00 = 600 %» como fracción. | 6, 10 |
| Componer › Parámetros del precio | `src/paginas/componer/ParametrosDelPrecio.tsx:11` | Rótulo «FCAS» solo. | 10 |
| Precios de la empresa | `src/paginas/precios_empresa/index.tsx:287-308`; `CalculadoraFCAS.tsx` | 7 campos para crear una lista, todos visibles; el «Nombre (opcional)» no se pliega. | 2, 4, 5 |
| Riesgo › Prueba con meses pasados | `src/paginas/riesgo/ResultadoDelRiesgo.tsx:94-102` | Tres cifras que dicen lo mismo (cobertura, cubiertos y probados) sin una frase de veredicto. | 1, 8 |
| Existencias › Registrar | `src/paginas/existencias/PestanaRegistrar.tsx` | 9 controles. | 2, 3 |
| Producción › Costo del período | `src/paginas/produccion/FormularioDeCosto.tsx` | 7 controles. | 2, 4 |
| Mercado › Operaciones | `src/paginas/mercado/OperacionesDePrecios.tsx` | 7 controles. | 2, 4 |
| Índices del BCV | `src/paginas/indices/index.tsx` | 7 controles; el backlog S7 ya pide un solo botón principal. | 2 |

---

## 7. Coordinación con el backlog (`docs/planes/2026-11-22-backlog-ux.md`)

- **Se unen, para no duplicar:**
  - S-1 con «Riesgo avisa antes de proyectar sin series» (backlog S8);
  - S-4 con «La reserva para el P80 como cifra de pantalla» (S8);
  - R-10 deja a S8 «Reajuste: volver al paso anterior…» tal cual;
  - C-1 absorbe la tabla «Atraso por partida» (ese bloque deja de existir por separado).
- **No contradice lo descartado:** S-2 no «propone series» (la persona elige y aplica en bloque). Las frases de respuesta son párrafos, no las tarjetas KPI que el backlog descartó por `DESIGN.md:4`.
- **Archivos compartidos con el lote C del backlog** (`riesgo/RiesgoDeLaObra.tsx`, `control/PestanasDeResultados.tsx`): un solo constructor para Riesgo y otro para Control, después de que el lote C se una, para que no choquen.
- **Back pedido** (todo aditivo, en `aplicacion/` y `api/`, sin migración ni `core/`):
  - R-6: `GET /v1/reajuste/ultima-clausula`;
  - R-9: `hay_valuaciones`;
  - S-6: `tipos` en `/v1/riesgo/insumos`;
  - C-2: «Descripción», «Termina», «Según el plan» y «Días de atraso» en la reproyección;
  - C-3: `terminos.atraso_dias`;
  - P-2: `periodo_del_corte`;
  - P-3: el plan base por partida.
- **Decisión simulada que hay que anotar en `docs/ESTADO.md` §4:** el texto automático de `fuente_r` cuando la cláusula no deja parte fija (R-4).
