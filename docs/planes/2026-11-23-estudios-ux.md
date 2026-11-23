# Dossier de estudios de UX para la skill interna de interfaz de Sílice

Investigación del 2026-11-23, solo lectura. Complementa el informe previo
`docs/planes/2026-11-23-carga-cognitiva.md` (árbol `.worktrees/s2mi2`), que ya trae nueve fuentes (E1 a E9: Sweller 1988,
Chandler y Sweller 1991, divulgación progresiva, Hick vía Laws of UX, valores por omisión, formularios de NN/g, asistentes,
Few cap. 3 e IBCS) y doce reglas. **Aquí no se repiten**: se citan como «E1…E9» y «regla previa 1…12» cuando hace falta.

## Cómo leer este dossier

Cada fuente lleva una marca del tipo de evidencia:

- **[E] empírica**: experimento, seguimiento ocular, simulación o datos medidos, con método publicado.
- **[X] experto**: opinión razonada de un especialista o de una consultora (NN/g, Baymard, Laws of UX), a veces apoyada en
  estudios propios que no publican el método completo.
- **[F] fabricante**: guía de un sistema de diseño o de una plataforma (IBM Carbon, Microsoft, Apple, GOV.UK).
- **[N] norma**: ISO o W3C.

Y una marca de verificación:

- **(abierta)**: se leyó la página o el PDF durante esta investigación.
- **(registro)**: solo se verificó el registro bibliográfico o un resumen (búsqueda, repositorio, resumen de terceros); el
  texto completo **no** se abrió. No se cita su contenido como verificado más allá de lo que dice el registro.

---

## 1. Reglas cognitivas

| # | Regla | Qué dice | Estudio de origen | Tipo | Cómo se traduce en pantalla |
|---|---|---|---|---|---|
| C1 | Memoria de trabajo (Miller) | El alcance de la memoria inmediata se mide en *chunks*, no en bits, y ronda los siete; agrupar en unidades conocidas (*chunking*) aumenta lo que cabe. Miller mismo sospechaba que el siete era «una coincidencia pitagórica perniciosa». | Miller, G. A. (1956). «The magical number seven, plus or minus two». *Psychological Review* 63, 81-97. https://psychclassics.yorku.ca/Miller/ (abierta) | [E] | No se diseña con «7±2» como cupo: Miller no lo propuso como límite. Lo que sí vale es **agrupar**: campos en grupos con título, cifras con su unidad. |
| C2 | Memoria de trabajo (Cowan) | La capacidad real, cuando se impide repasar y agrupar, es de **tres a cinco chunks**; Cowan sostiene que «el límite menor es real». | Cowan, N. (2001). «The magical number 4 in short-term memory». *Behavioral and Brain Sciences* 24, 87-185. Universidad de Misuri. PDF del autor: https://memory.psych.missouri.edu/assets/doc/articles/2001/cowan-bbs-2001.pdf (abierta, resumen) | [E] | Lo que la persona debe **tener en la cabeza a la vez** (no lo que ve) no pasa de 4: por ejemplo, no se le pide recordar una cifra de otra pestaña para compararla con la actual. Si hay que comparar, las dos cifras van juntas en la misma vista. |
| C3 | Carga cognitiva: redundancia y atención dividida | Atención dividida: integrar fuentes separadas carga la memoria. Redundancia: repetir la misma información en dos formas (texto que repite lo que ya dice el gráfico o la tabla) **también** carga, sobre todo a quien ya conoce el dominio. | Chandler y Sweller (1991) ya está en el informe previo (E2). Revisión de 20 años: Sweller, van Merriënboer y Paas (2019), «Cognitive Architecture and Instructional Design: 20 Years Later», *Educational Psychology Review* 31, 261-292 (registro; el PDF de core.ac.uk y Springer devolvió 403). | [E] | La explicación va pegada a la cifra (E2), **pero una sola vez**: no se repite la misma frase en la ayuda del campo, en el `QueEsEsto` y en la nota de la tabla. |
| C4 | Inversión por pericia (*expertise reversal*) | Lo que ayuda al novato (texto explicativo integrado, pasos guiados) puede **perder eficacia o perjudicar** al experto, porque le obliga a procesar lo que ya sabe. | Kalyuga, Ayres, Chandler y Sweller (2003). «The Expertise Reversal Effect». *Educational Psychologist* 38(1), 23-31. doi:10.1207/s15326985ep3801_4. Registro: https://ro.uow.edu.au/edupapers/136 (registro). Antecedente: Kalyuga, Chandler y Sweller (1998), *Human Factors* 40, 1-17, con aprendices técnicos de ingeniería (registro). | [E] | Para los ingenieros de Sílice: la ayuda larga va **plegada** («¿Qué es esto?»), no en párrafos fijos sobre cada campo. La frase de respuesta es corta. Es la base teórica de ofrecer densidad y ayuda a pedido, no un solo nivel para todos. |
| C5 | Ley de Hick-Hyman | El tiempo de reacción crece con la información de las alternativas (≈ log₂ del número de opciones equiprobables); Hyman lo extendió a opciones de probabilidad desigual. Réplicas posteriores muestran que la pendiente depende de la compatibilidad estímulo-respuesta. | Hick, W. E. (1952). «On the rate of gain of information». *Quarterly Journal of Experimental Psychology* 4(1), 11-26. Hyman, R. (1953). «Stimulus information as a determinant of reaction time». *Journal of Experimental Psychology* 45(3), 188-196 (ambos registro). | [E] | Complementa E4: como la ley trata de **opciones desigualmente probables**, se resalta la opción más común (valor por omisión) y se ordena por frecuencia. Ojo: la ley vale para elegir entre opciones **conocidas**; no justifica partir un menú en submenús (eso añade pasos). |
| C6 | Ley de Fitts | Tiempo de movimiento MT = a + b·log₂(A/W + 1): más distancia (A) o menos ancho (W) del objetivo, más tiempo y más errores. ISO 9241-9 (hoy 9241-411) normaliza su medición. | MacKenzie, I. S. (1992). «Fitts' law as a research and design tool in human-computer interaction». *Human-Computer Interaction* 7, 91-139 (registro). MacKenzie, I. S. (2018). «Fitts' Law», en *Handbook of HCI*, Wiley, 349-370, York University: https://www.yorku.ca/mack/hhci2018.html (abierta). | [E] | El botón principal va **donde termina la tarea** (al pie del formulario, junto al último campo), no en la cabecera lejos del foco. Objetivos de 24 × 24 px como mínimo (WCAG 2.5.8, §3) y los iconos de fila de una tabla densa no se reducen por debajo de eso. |
| C7 | Reconocer antes que recordar | Reconocer es más fácil que recordar porque da más pistas de recuperación. | Budiu, R. «Memory Recognition and Recall in User Interfaces», NN/g, 15/01/2024. https://www.nngroup.com/articles/recognition-and-recall/ (abierta) | [X] sobre base [E] de la psicología de la memoria | Autocompletado con descripción en los campos de código (insumo, partida, serie); historial y «lo último usado»; nunca pedir un código de memoria. Las funciones se ven en menús con rótulo, no solo por atajo. |
| C8 | Gestalt: proximidad | Lo que está cerca se percibe como grupo, y puede **imponerse** al color o la forma. Un formulario de 12 campos en 3 grupos de 4 «parece simple» frente a un bloque de 12. | Harley, A. «Proximity Principle in Visual Design», NN/g, 02/08/2020. https://www.nngroup.com/articles/gestalt-proximity/ (abierta) | [X] | Etiqueta pegada a su campo y más espacio **entre** grupos que **dentro** de ellos; el título de sección más cerca de su contenido que del bloque anterior. No mezclar acciones ajenas en un mismo grupo de botones. |
| C9 | Gestalt: región común | Un contorno o un fondo compartido agrupa y es **más fuerte que la proximidad**; pero cada caja añade ruido: «probar primero con espacio en blanco». | Harley, A. «The Principle of Common Region», NN/g, 12/07/2020. https://www.nngroup.com/articles/common-region/ (abierta) | [X] | Primero se agrupa con espacio (`spacing` de Carbon); un `Tile` o un fondo solo si el espacio no alcanza. Nada de cajas dentro de cajas. |
| C10 | Gestalt: semejanza | Lo que comparte color, forma o tamaño se percibe como relacionado; el color de enlace solo para lo que se pulsa; el botón principal con un color propio. | Harley, A. «Similarity Principle in Visual Design», NN/g, 06/09/2020. https://www.nngroup.com/articles/gestalt-similarity/ (abierta) | [X] | El mismo ícono y el mismo rótulo para la misma acción en todas las pantallas; el azul de Carbon solo en lo interactivo; una cifra resaltada no comparte estilo con un enlace. |
| C11 | Posición serial | En el recuerdo libre, se recuerdan mejor los primeros elementos (primacía) y los últimos (recencia); la curva es una U. | Murdock, B. B. (1962). «The serial position effect of free recall». *Journal of Experimental Psychology* 64(5), 482-488 (registro). La página de NN/g sobre el efecto no se encontró (404). | [E] | Lo que más importa va **primero** (frase de respuesta, columna identificadora) y la acción de cierre **al final**; lo de menor uso, en medio o plegado. |
| C12 | Efecto Von Restorff (aislamiento) | Entre elementos homogéneos, el que difiere se recuerda más; usado en exceso, pierde valor. | Von Restorff, H. (1933), en alemán (registro vía https://www.wikipedia.org/wiki/Isolation_effect). Resumen: https://lawsofux.com/von-restorff-effect/ (registro) | [E] origen; [X] aplicación | Un solo elemento destacado por vista (el botón principal o la cifra de respuesta). Si todo se resalta (negrita, color, etiqueta), nada destaca. No se usa **solo** el color (WCAG 1.4.1). |
| C13 | Umbral de Doherty | La productividad sube cuando sistema y persona interactúan a un ritmo en que ninguno espera al otro; el informe fijó **400 ms** en lugar de los 2 s de antes. | Doherty, W. J. y Thadani, A. J. (1982). «The Economic Value of Rapid Response Time», IBM, GE20-0752 (registro; la copia de IBM dio error de certificado). Resumen: https://lawsofux.com/doherty-threshold/ (abierta). Relacionado: Nielsen, «Response Times: The 3 Important Limits» (0,1 s / 1 s / 10 s, basado en Miller 1968 y Card et al. 1991), NN/g, 1993 actualizado 2014: https://www.nngroup.com/articles/response-times-3-important-limits/ (abierta). | [E] (informe de empresa) y [X] | Editar una celda, filtrar o abrir un pliegue responde en < 0,4 s; si una acción pasa de 1 s, se ve un indicador; si pasa de 10 s, un porcentaje y un modo de cancelar (§6). |
| C14 | Ley de Jakob | Las personas pasan la mayor parte del tiempo en **otros** sistemas y esperan que el tuyo funcione igual; una «innovación» que la rompe suele costar más de lo que aporta. Nielsen la formuló en 2000. | Nielsen, J. «Jakob's Law of the Internet User Experience». https://jakobnielsenphd.substack.com/p/jakobs-law y video de NN/g https://nngroup.com/videos/jakobs-law-internet-ux/ (registro; el artículo de NN/g dio 404) | [X] | Para Sílice, «los otros sistemas» son **Excel y Windows**: Enter, Tab, Esc, Ctrl+Z, flechas y F2 se comportan como en Excel en el editor de hoja; la coma decimal y el punto de miles, como en la configuración regional de Venezuela. (Aplicación propia; no hay fuente sobre Excel en concreto.) |
| C15 | Ley de Tesler (conservación de la complejidad) | Toda tarea tiene un núcleo de complejidad que no se elimina: o lo absorbe el sistema o lo absorbe la persona. Tesler (Xerox PARC, mediados de los 80): mejor una semana más de ingeniería que un minuto más para millones de usuarios. | Laws of UX, https://lawsofux.com/teslers-law/ (abierta), que remite a la entrevista en Saffer, *Designing for Interaction* (registro). | [X] | Lo que Sílice puede deducir (fechas, responsable, pesos, mes base) lo deduce el servidor y se muestra como frase con «Cambiar» (regla previa 4). Pero la complejidad del dominio **no se esconde**: si la cláusula exige un dato, se pide con su explicación. |
| C16 | Olor de la información (*information scent*) | Las personas eligen un camino según su estimación (imperfecta) del valor que hay detrás, a partir de las pistas: el rótulo del enlace es «quizá el componente más importante». | Pirolli, P. y Card, S. K. (1999). «Information foraging». *Psychological Review* 106(4), 643-675, Xerox PARC (registro). Budiu, R. «Information Scent», NN/g, 02/02/2020: https://www.nngroup.com/articles/information-scent/ (abierta). | [E] origen; [X] aplicación | Rótulos de menú, pestaña y botón que dicen **qué hay detrás** en palabras de obra («Cuándo termina cada partida», no «Reproyección»); nada de «Ver más» ni «Detalles» solos; el resumen de un pliegue dice qué y cuántos («Ver las 12 partidas…»). |

---

## 2. Formularios

### 2.1 Evidencia

| Fuente | Tipo | Qué encontró o dice |
|---|---|---|
| Bargas-Avila, Brenzikofer, Roth, Tuch, Orsini y Opwis (2010b). «Simple but Crucial User Interfaces in the World Wide Web: Introducing 20 Guidelines for Usable Web Form Design», en *User Interfaces*, InTech, 1-10. Universidad de Basilea. Las 20 pautas se leyeron en la tabla 1 de Seckler, Heinz, Bargas-Avila, Opwis y Tuch (2014), «Designing Usable Web Forms: Empirical Evaluation of Web Form Improvement Guidelines», CHI 2014, Toronto: https://research.google.com/pubs/archive/42513.pdf (abierta) | [X] las pautas; [E] su validación | **Validación (Seckler 2014, N = 65, seguimiento ocular, formularios reales de empresas):** los formularios corregidos con las 20 pautas se completaron más rápido, con menos intentos de envío y menos movimientos oculares, y con más satisfacción. Las pautas que más pesaron, según los usuarios, fueron la 13 (decir el formato antes) y la 4 (separar obligatorios y opcionales). Pautas útiles para Sílice: 3 (formulario corto, nada innecesario); 5 (etiquetas encima); 6 (**una sola columna**, una pregunta por fila); 7 (ancho del campo según la respuesta); 10 (hasta **4 opciones, botones de opción**; más, desplegable); 11 (orden lógico, si no alfabético); 13 (formato exigido, dicho antes); 14 y 17 (error cortés, visible a la primera, en lenguaje conocido, que diga qué pasó y cómo corregirlo); 15 (**nunca borrar** lo ya escrito tras un error); 18 (deshabilitar el envío tras el primer clic); 19 (confirmación que diga **qué pasa después**); 20 (sin botón «Restablecer»). |
| Penzo, M. (2006). «Label Placement in Forms». *UXmatters*, 12/07/2006. https://www.uxmatters.com/mt/archives/2006/07/label-placement-in-forms.php (abierta) | [E] (seguimiento ocular, sin tamaño de muestra ni estadística publicados) | Etiquetas **encima** del campo: el salto etiqueta-campo bajó a ≈ 50 ms, frente a ≈ 500 ms con etiquetas a la izquierda alineadas a la izquierda; las alineadas a la derecha quedaron en medio (170 a 240 ms). Las etiquetas en negrita no ayudaron. Los desplegables atraen la primera fijación. Formularios de 4 campos sin diseño visual. |
| Das, S., McEwan, T. y Douglas, D. (2008). «Using eye-tracking to evaluate label alignment in online forms». NordiCHI 2008, ACM, 451-454. doi:10.1145/1463160.1463217. Registro: https://napier-repository.worktribe.com/output/232426/using-eye-tracking-to-evaluate-label-alignment-in-online-forms (registro) | [E] (muestra pequeña, una sola población) | Según el registro, **contradice** a Wroblewski y recomienda etiquetas **alineadas a la derecha**, al menos en formularios de varias columnas; las alineadas a la izquierda tardaron más. |
| Jarrett, C. y Gaffney, G. (2008). *Forms that Work: Designing Web Forms for Usability*. Morgan Kaufmann. https://shop.elsevier.com/books/forms-that-work/jarrett/978-1-55860-710-1 (registro) | [X] | Modelo de tres capas: **relación** (por qué se pregunta y quién pregunta), **conversación** (qué y en qué orden) y **apariencia**. La apariencia va al final: un formulario bonito con preguntas mal pensadas sigue fallando. |
| Wroblewski, L. (2009). «Inline Validation in Web Forms». *A List Apart* 291. https://alistapart.com/article/inline-validation-in-web-forms/ (abierta) | [E] (con Etre, N = 22, medidas repetidas) | La mejor validación en línea frente al control: +22 % de éxito, −22 % de errores, +31 % de satisfacción, −42 % de tiempo, −47 % de fijaciones. Validar **al salir del campo** fue 7 a 10 s más rápido que validar «mientras» se escribe; «antes y mientras» dio los peores errores y la peor satisfacción. Mensajes persistentes mejor que los que se desvanecen. |
| Carbon, *Forms pattern*. https://carbondesignsystem.com/patterns/forms-pattern/ (abierta) | [F] | Una columna por omisión («multicolumn forms are more prone to misinterpretation»), salvo 2 o 3 campos que van juntos en una línea. Etiquetas **solo arriba** («the only label arrangement currently offered»). Marcar solo la minoría: si casi todos son obligatorios, marcar «(opcional)»; si casi todos son opcionales, «(required)». Ayuda solo «when truly necessary». Validación al perder el foco. 32 px entre campos en página; 24 px en modales y paneles. Campos de 40 px de alto. |
| Baymard Institute, Scott, E. «Mark both required and optional fields», 02/10/2018. https://baymard.com/blog/required-optional-form-fields (abierta) | [X] con pruebas propias de usuarios (método no publicado) | Cuando solo se marcaban los opcionales, el 32 % de los participantes chocó con un error por saltarse un obligatorio; cuando solo se marcaban los obligatorios, algunos tomaron los opcionales por obligatorios. «All fields required» al principio casi nadie lo lee. Recomienda **marcar ambos**: asterisco en el obligatorio y «Opcional» junto a la etiqueta. |
| Sherwin, K. «Placeholders in Form Fields Are Harmful», NN/g, 11/05/2014. https://www.nngroup.com/articles/form-design-placeholders/ (abierta) | [X] | El texto de ejemplo dentro del campo desaparece al escribir, se confunde con un valor ya puesto («some users assume the placeholder text is a default value») y no todos los lectores de pantalla lo leen. Etiqueta y ayuda **fuera** del campo. |

### 2.2 Dónde se contradicen y qué conviene a Sílice

| Tema | Postura A | Postura B | Para Sílice |
|---|---|---|---|
| Ubicación de la etiqueta | Encima (Penzo 2006, Bargas-Avila pauta 5, Carbon) | A la derecha, alineada a la derecha, en formularios de varias columnas (Das et al. 2008) | **Encima.** Carbon solo ofrece esa, el formulario es de una columna (pauta 6) y la evidencia de Das es de muestra pequeña. |
| Marcar obligatorios u opcionales | Marcar solo la minoría (Carbon) | Marcar ambos (Baymard, con pruebas); marcar los obligatorios con asterisco (Bargas-Avila pauta 4) | **Marcar ambos**: la evidencia de usuarios pesa más que la guía. En la práctica, Sílice deja a la vista casi solo campos obligatorios (lo opcional va en «Más opciones», regla previa 2), así que el «(opcional)» aparece poco. |
| Cuándo validar | Al terminar todo, todos los errores juntos (Bargas-Avila pauta 16) | Al salir de cada campo (Wroblewski 2009, Carbon) | **Ambas, en capas:** formato al salir del campo; al pulsar el botón principal, un resumen arriba con enlaces a cada campo con error y el foco en el primero. Nunca validar mientras se escribe. |
| Un paso por página | «Start with one thing per page» (GOV.UK) | Evitar flujos rígidos y lineales en aplicaciones complejas (NN/g, Kaplan 2020) | Una página por tarea con grupos; el asistente solo para tareas ocasionales (E7). El propio GOV.UK admite unir páginas en servicios internos de uso repetido (§4). |

---

## 3. Botones

### 3.1 Lo que dice cada fuente

| Fuente | Tipo | Orden y alineación | Otras reglas |
|---|---|---|---|
| Nielsen, J. «OK-Cancel or Cancel-OK? The Trouble With Buttons», NN/g, 26/05/2008. https://www.nngroup.com/articles/ok-cancel-or-cancel-ok/ (abierta) | [X], **sin datos empíricos** | Windows: OK primero; Apple: OK al final. Recomienda **seguir la convención de la plataforma**: «more important than optimizing an individual dialog box». | Reconoce que ninguna elección causa catástrofes y que no vale la pena investigarlo más. |
| Microsoft, *Windows 7 Dialog Boxes*. https://learn.microsoft.com/en-us/windows/win32/uxguide/win-dialog-box (abierta) | [F] (guía de Windows 7, no actualizada) | Botones de confirmación **alineados a la derecha**, en una fila al pie; orden: OK/[Hacerlo]/Sí, [No hacerlo]/No, Cancelar, Aplicar, Ayuda. | Rótulo **específico** («Grabar CD», no «Aceptar»); «Cancelar» y «Cerrar» no se renombran; no confirmar los botones de confirmación; no deshabilitarlos. |
| Microsoft, *Command Buttons*. https://learn.microsoft.com/en-us/windows/win32/uxguide/ctrl-command-buttons (abierta) | [F] | Un solo botón por omisión por ventana. | «Select the safest… command to be the default»; **no** poner una acción destructiva como predeterminada salvo que se pueda deshacer; verbo en imperativo; puntos suspensivos si la orden pide más datos; puntero de espera si no es instantáneo. |
| Microsoft, *Dialog controls* (WinUI, Windows 11). https://learn.microsoft.com/en-us/windows/apps/design/controls/dialogs-and-flyouts/dialogs (abierta) | [F] | La acción «hacerlo» (Primary) **a la izquierda**; la segura (Close) **a la derecha**. | Al menos un botón seguro; Esc equivale al botón seguro; no usar diálogos para errores de validación de un campo. |
| Apple, *Human Interface Guidelines: Alerts*. https://developer.apple.com/design/human-interface-guidelines/alerts (la página no se pudo leer; se verificó por búsqueda en el `.md` de Apple) (registro) | [F] | Cancelar en el lado inicial (*leading*) de la fila; la acción por omisión al otro lado. | Estilo destructivo para lo que la persona no eligió deliberadamente; con acción destructiva, incluir Cancelar y considerar hacerlo predeterminado; no alertar en acciones comunes que se pueden deshacer. |
| IBM Carbon, *Button usage*. https://carbondesignsystem.com/components/button/usage/ (abierta) | [F] | **Página completa y formularios en la página:** principal **alineado a la izquierda** y a la izquierda del secundario. **Asistentes y diálogos:** principal **a la derecha**. Carbon advierte que esta guía cambió respecto a la anterior. | «Each page should have only one primary button», salvo flujos temporales. Secundario nunca solo. Barra de herramientas de tabla: el botón puede ser principal, pero si otro botón de la página ya lo es, se usa uno *ghost*. *Danger* para lo destructivo; nunca solo ícono. |
| IBM Carbon, *Modal usage*. https://carbondesignsystem.com/components/modal/usage/ (abierta) | [F] | Dos botones a todo el ancho, 50 % cada uno: **secundario a la izquierda, principal a la derecha**. Tres botones (raro): 25 % cada uno, alineados a la derecha, solo el de más a la derecha es principal. | Modal de peligro: el principal se reemplaza por *danger*. Foco inicial en el primer campo; foco atrapado. No usar modal para tareas repetidas ni para mensajes no críticos. |
| IBM Carbon, *Data table usage*. https://carbondesignsystem.com/components/data-table/usage/ (abierta) | [F] | La barra de herramientas va **sobre** la tabla y es para acciones globales; **hasta cinco** acciones; la barra de acciones en lote aparece arriba al seleccionar. | Paginación siempre abajo. |
| GOV.UK Design System, *Button*. https://design-system.service.gov.uk/components/button/ (abierta) | [F] | «Align the primary action button to the left edge of your form.» | Un solo botón principal: más de uno «makes it harder for users to know what to do next»; botón de advertencia (rojo) solo para consecuencias graves que no se deshacen, y **no** depender solo del rojo; texto que describe la acción; ignorar el segundo clic. |
| Material Design 3, *Dialogs*. https://m3.material.io/components/dialogs/guidelines | — | **No se pudo abrir** (la página solo devolvió el título; también falló m2.material.io). No se cita. | — |
| Nielsen, J. «Confirmation Dialogs Can Prevent User Errors — If Not Overused», NN/g, 18/02/2018. https://www.nngroup.com/articles/confirmation-dialog/ (abierta) | [X] | — | Confirmar solo lo que no se deshace; preferir **deshacer**; si se confirma a menudo, la gente deja de leer; botones que nombran el resultado («Borrar el archivo» / «Conservar el archivo»), no Sí/No; sin «Sí» por omisión. |
| W3C, WCAG 2.2, criterio 2.5.8 *Target Size (Minimum)*, nivel AA. https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html (abierta) | [N] | — | Objetivo de **24 × 24 px CSS** como mínimo, con excepciones (espaciado suficiente, control equivalente, enlace dentro de un texto, control del navegador, presentación esencial). El 2.5.5 (mejorado) pide 44 × 44 px. |
| MacKenzie (2018), ley de Fitts (C6) | [E] | — | Objetivos grandes y cercanos al último punto de atención son más rápidos y con menos errores. |

### 3.2 La contradicción del orden y qué conviene a Sílice

Hay **cuatro órdenes distintos** en las fuentes, y la única revisión que los compara (NN/g 2008) no trae datos, solo el
argumento de la coherencia:

1. Windows clásico (Win32): Aceptar a la izquierda, Cancelar a la derecha, ambos alineados a la derecha.
2. Windows 11 (WinUI): la acción a la izquierda y la segura a la derecha (igual que el clásico).
3. Apple: Cancelar al inicio, la acción al final.
4. Carbon: en un **modal** y en un **asistente**, la acción a la derecha (como Apple); en un **formulario de página**, la
   acción a la izquierda (como GOV.UK).

**Recomendación para Sílice** (Carbon en un navegador, sobre Windows, para gente de Excel):

- **Seguir Carbon en todas las vistas, sin excepciones.** La «plataforma» de una aplicación Carbon es Carbon, y lo que
  cuesta según NN/g es la **incoherencia**, no el orden en sí. Mezclar el orden de Windows en unos modales y el de Carbon
  en otros es lo único que se debe evitar.
- **Rótulos específicos** en el botón de acción («Guardar el estudio», «Borrar la partida»), como piden Microsoft, Apple y
  NN/g. Así la persona no depende de la posición para saber qué hace, y la diferencia con Windows se nota menos.
- **Teclado como en Windows:** Enter activa el principal (fuera de un área de texto) y Esc cierra el modal sin hacer nada.
  Es lo que la persona de Excel trae de serie (C14).
- En lo destructivo, el botón *danger* de Carbon, con texto que nombra la consecuencia; el foco inicial **no** va en el
  botón destructivo (Microsoft y Apple coinciden), y si se puede deshacer, no se confirma (NN/g 2018).

### 3.3 La acción siguiente

- Una sola acción principal por vista (Carbon, GOV.UK), y es **la siguiente que la persona debe hacer**.
- Al pie del formulario, pegada al último campo (Fitts, C6; Carbon *Forms*: «arrange primary and secondary buttons at the
  bottom of the form»). Si el formulario es más alto que la pantalla, la acción principal no debe quedar a dos pantallas de
  distancia sin aviso: NN/g encontró que el 57 % del tiempo de mirada cae en la primera pantalla y el 74 % en las dos
  primeras (§4.1).
- Tras guardar o calcular, la confirmación dice **qué pasa después** y ofrece el siguiente paso (Bargas-Avila pauta 19;
  Carbon *Notifications*: «Do not leave users without next steps»).
- Un estado vacío trae el botón que lo resuelve (NN/g, Kaplan 2021: «Provide direct pathways»; Carbon *Empty states*).

---

## 4. Espacio por tipo de vista

### 4.1 Evidencia general

| Fuente | Tipo | Qué dice |
|---|---|---|
| Fessenden, T. «Scrolling and Attention», NN/g, 15/04/2018. https://www.nngroup.com/articles/scrolling-and-attention/ (abierta) | [E] (120 participantes, más de 130.000 fijaciones, pantalla de 1920 × 1080) | El 57 % del tiempo de mirada queda sobre el pliegue (era 80 % en 2010); el 74 %, en las dos primeras pantallas; el 81 %, en las tres primeras. Más del 65 % se va al 40 % superior de la página. La caída tras el pliegue persiste aunque hoy se desplace más. |
| Pernice, K. «F-Shaped Pattern of Reading on the Web», NN/g, 12/11/2017. https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/ (abierta) | [E] (seguimiento ocular, más de 45 y 47 participantes en los mapas citados) | Sin pistas fuertes, se lee en F: las primeras líneas y las primeras palabras de cada línea. Otros patrones: **en capas** (solo títulos y subtítulos), salteado (busca números o palabras), marcado, de salto y de compromiso. La página **no** clasifica cuál es mejor; la defensa contra la F son los títulos que empiezan por la palabra informativa. |
| Shneiderman, B. (1996). «The Eyes Have It: A Task by Data Type Taxonomy for Information Visualizations». IEEE Symposium on Visual Languages, 336-343. Universidad de Maryland, TR 96-66: https://drum.lib.umd.edu/items/155a868e-fb83-4115-9899-9187ea8c0498 (abierta, resumen) | [X] (taxonomía) | «Overview first, zoom and filter, then details-on-demand», presentado por el autor como «a useful starting point», más siete tareas: vista general, acercar, filtrar, detalle a pedido, relacionar, historial y extraer. |
| Few, S. Definición de tablero (2004, «Dashboard Confusion») y *Information Dashboard Design* (2006): una sola pantalla con lo más importante para uno o más objetivos, para **vigilar de un vistazo**; en 2007 separó el tablero de la pantalla de análisis interactiva. Reseña de UXmatters: https://www.uxmatters.com/mt/archives/2007/04/book-review-information-dashboard-design.php (registro) | [X] | El tablero no es para explorar ni para consultar valores: es para vigilar. |
| Kaplan, K. «8 Design Guidelines for Complex Applications», NN/g, 08/11/2020. https://www.nngroup.com/articles/complex-application-design/ (abierta) | [X] | Las aplicaciones complejas sirven a novatos y expertos a la vez, y la mayoría de usuarios se estanca en un nivel medio. Pide **revelado por etapas** (opciones solo cuando son pertinentes), reducir el desorden sin quitar capacidad, enseñar los atajos en contexto y **evitar flujos rígidos y lineales**. |
| Carbon, *Data table*, tamaños de fila: xs 24, sm 32, md 40 (por omisión), lg 48 y xl 64 px. https://carbondesignsystem.com/components/data-table/usage/ (abierta) | [F] | xs «for highly dense layouts where maximizing information… is a priority»; md «the default»; xl solo con dos líneas por fila; el encabezado con el mismo tamaño que las filas. |
| Carbon, *2x Grid*. https://carbondesignsystem.com/elements/2x-grid/overview/ (abierta) | [F] | Unidad de 8 px; 16 columnas desde 1056 px; para contenido denso, usar las mini unidades; para contenido muy relacionado, una rejilla sin medianil. |
| Baymard, Scott, E. «Readability: The Optimal Line Length», 10/05/2022. https://baymard.com/blog/line-length-readability (abierta) | [X] (cita a Ruder, *Typographie*; webtypography.net; WCAG 1.4.8) | Texto corrido entre **50 y 75 caracteres** por línea; 80 como tope (WCAG 1.4.8, AAA); en CSS, ≈ `max-width: 70ch`. *Bringhurst no se abrió*; Baymard cita a Ruder y a webtypography.net, que lo resume. |
| Sunwall, E. «Tabs, Used Right», NN/g, 02/08/2024. https://www.nngroup.com/articles/tabs-used-right/ (abierta) | [X] | Pestañas para contenido largo con grupos claros, pocas y de importancia desigual (la primera es la que más se ve). **No** usarlas si hay que comparar contenido entre pestañas. Una sola fila, encima de su panel, con dos indicadores de selección. |
| Wang, H.-H. «Accordions on Desktop», NN/g, 30/07/2023. https://www.nngroup.com/articles/accordions-on-desktop/ (abierta) | [X] | Sirven cuando se necesitan **pocas** secciones; estorban cuando se necesita casi todo, cuando hay que comparar, cuando el contenido es escaso o está anidado, y al imprimir. Permitir abrir varias y ofrecer «Abrir todo». Lo crucial, fuera del pliegue. |
| GOV.UK Service Manual, *Structuring forms*. https://www.gov.uk/service-manual/design/form-structure (abierta) | [F], sin datos publicados | «Start with one thing per page.» Razones: entender qué se pide, enfocarse, orientarse en un proceso desconocido, recuperarse de errores. «User research will tell you when you can merge pages»; da como ejemplo un servicio interno con usuarios que «need to repeat and switch between tasks quickly». |
| Microsoft, *List/details*. https://learn.microsoft.com/en-us/windows/apps/design/controls/list-details (abierta) | [F] | Maestro-detalle: lista y detalle **lado a lado** desde 641 px de ancho; apilados por debajo. Sirve para «locate and prioritize a large collection» y trabajar yendo y viniendo entre elementos. |
| Laubheimer, P. «Data Tables: Four Major User Tasks», NN/g, 03/04/2022. https://www.nngroup.com/articles/data-tables/ (abierta) | [X] | Editar una fila: en el sitio solo en tablas estrechas; un **panel no modal** suele ser mejor que un modal porque deja ver la tabla. |

**Densidad para expertos:** no se encontró un estudio empírico de laboratorio que mida densidad frente a rendimiento en
aplicaciones de escritorio para expertos. La base disponible es teórica (inversión por pericia, C4), de experto (NN/g,
Kaplan 2020) y de fabricante (tamaños de fila de Carbon). Queda como **laguna**; la recomendación de abajo es una
inferencia de esas tres.

### 4.2 Recomendación por tipo de vista

| Tipo de vista | Disposición | Densidad | Dónde va la acción | Qué se pliega | Fuentes |
|---|---|---|---|---|---|
| **Formulario de captura** (Reajuste paso 1, Registrar existencias, Valuaciones) | Una columna; 2 o 3 campos en una línea solo si van juntos (inicio y duración). Grupos con un título que es una pregunta, y más aire entre grupos que dentro. Ancho del campo según la respuesta; ayudas de no más de ≈ 75 caracteres por línea. | Carbon por omisión (campos de 40 px; 32 px entre campos en página, 24 px en modal o panel). | Al pie, botón principal alineado a la izquierda y secundario a su derecha (Carbon *in-page forms*). | Lo opcional y lo que tiene valor recomendado, en un solo nivel de «Más opciones». | Bargas-Avila 3, 5, 6 y 7; Carbon *Forms*; C8; Baymard 2022; regla previa 2. |
| **Tabla de resultados** (Control, Mercado, Catálogo) | La frase de respuesta encima (regla previa 1); la tabla debajo, con el identificador legible en la primera columna y las columnas relacionadas juntas. | md (40 px) por omisión; sm (32 px) si la tabla es larga y la usan a diario. | Barra de herramientas sobre la tabla, hasta 5 acciones; acciones en lote al seleccionar; paginación abajo. | Columnas que no responden la pregunta: ocultables o en el detalle de la fila. | NN/g *Data tables*; Carbon *Data table*; §5. |
| **Tablero o resumen** (Tablero, Inicio) | Una pantalla, sin desplazarse, para **vigilar**: lo más importante arriba a la izquierda (F y 65 % de la mirada en el 40 % superior). Cada bloque con su frase y su enlace al detalle (vista general, luego detalle a pedido). | Media; nada de decoración (Tufte, §5). | Cada bloque lleva **su** enlace al detalle; no hay botón principal global. | El análisis va en su propia pantalla, no en el tablero (Few 2007). | Few; Shneiderman 1996; NN/g *Scrolling* y *F-pattern*; `DESIGN.md` (sin tarjetas KPI, según el informe previo). |
| **Editor tipo hoja de cálculo** (Hoja de presupuesto, Componer APU) | Encabezado y primera columna fijos; números a la derecha; selección y teclado como en Excel; edición de la fila en un panel lateral no modal cuando la fila tiene muchos campos. | La más densa: xs o sm (24 o 32 px), porque es la vista de uso diario del experto. Objetivos de 24 px como mínimo. | La acción de la celda es teclear; las acciones globales, en la barra superior. Deshacer en lugar de confirmar. | Las explicaciones, a pedido (C4); nada fijo encima de cada columna salvo el encabezado. | C13 (Doherty); C14 (Jakob); C7 (autocompletado); NN/g *Data tables*; Carbon; Nielsen 2018. |
| **Asistente por pasos** (Reajuste, primera instalación) | Solo para tareas **ocasionales** o desconocidas (E7). Todos los pasos visibles; se puede volver atrás sin perder lo escrito. Un paso por pantalla solo si cada paso tiene sentido por sí mismo (GOV.UK). | Carbon por omisión. | Principal **abajo a la derecha**, «Anterior» a su izquierda (Carbon: «in wizards… the primary action traditionally sits at the bottom right»). | Lo avanzado de cada paso, en «Más opciones». | E7; Carbon *Button*; GOV.UK; NN/g *Complex apps* (evitar flujos rígidos). |

**Pestañas, acordeones, asistente o una sola página:**

- **Una sola página con secciones** cuando la persona necesita casi todo o tiene que comparar (NN/g *Tabs* y *Accordions*).
- **Pestañas** cuando hay pocos grupos de importancia desigual que **no** se comparan entre sí; la más usada, primero.
- **Acordeón o `<details>`** cuando se necesitan pocas secciones de muchas; nunca uno dentro de otro.
- **Asistente** cuando la tarea es ocasional y su orden importa.
- **Maestro-detalle** cuando se recorre una colección y se trabaja sobre un elemento a la vez (lista de obras, de APU o de
  valuaciones), lado a lado en escritorio.

---

## 5. Tablas

| Regla | Fuente | Tipo | Nota |
|---|---|---|---|
| **Una tabla para consultar valores exactos; un gráfico para ver la forma.** | Few, cap. 3 (ya en el informe previo, E8). | [X] | No se repite; se usa como criterio para elegir. |
| **Números alineados a la derecha, con los mismos decimales en toda la columna**; el encabezado se alinea como sus datos; nunca centrado. | Guía de visualización de datos de la UE: https://data.europa.eu/apps/data-visualisation-guide/table-design-scannability (registro); Adobe Spectrum, *Table*: https://spectrum.adobe.com/page/table (registro); Few, *Show Me the Numbers*, citado por terceros (registro). | [X] / [F] | Ninguna se abrió entera; la regla es coherente en todas. Cifras **tabulares** (de ancho fijo). Con la coma decimal, alinear a la derecha con decimales fijos equivale a alinear en la coma. |
| **Encabezados (y la primera columna) fijos** si la tabla es más grande que la pantalla. | NN/g, Laubheimer 2022 (abierta). | [X] | — |
| **Rayas de cebra:** sin mejora significativa de exactitud ni de velocidad, y tampoco empeoran; el 46 % las prefirió. | Enders, J. «Zebra Striping: Does it Really Help?», *A List Apart* 258, 06/05/2008. https://alistapart.com/article/zebrastripingdoesithelp/ (abierta) | [E] (N = 244, una tabla de 15 × 9) | Carbon ofrece cebra; NN/g dice que bordes, cebra y resaltado al pasar el ratón ayudan a no perder la fila. **Para Sílice:** líneas de Carbon y resaltado de la fila por omisión; cebra solo en tablas anchas (muchas columnas o desplazamiento horizontal), donde Enders sospecha que el efecto sería mayor. |
| **Razón datos-tinta:** quitar la tinta que no representa datos (*chartjunk*). | Tufte, E. (1983). *The Visual Display of Quantitative Information* (registro; solo resúmenes de terceros, p. ej. https://data.europa.eu/apps/data-visualisation-guide/chart-junk-and-data-ink-origins). | [X] | La crítica académica dice que la relación no es lineal: minimizar sin criterio también daña. Se aplica a bordes, fondos y sombras de tablas, no a las etiquetas que dan contexto (unidad, plan). |
| **Columnas: títulos de una o dos palabras**; si son largos, dos líneas y luego recorte con la descripción completa al pasar el ratón. | Carbon *Data table* (abierta). | [F] | — |
| **Cuántas columnas como máximo:** ninguna fuente abierta da un número. | — | — | **Laguna.** Criterio que sí está respaldado: la tabla responde **una** pregunta (regla previa 1); lo que no sirve a esa pregunta se oculta (NN/g: ocultar y reordenar columnas «must be easy») o va al detalle de la fila. Propuesta operativa (inferencia, no fuente): si no cabe sin desplazamiento horizontal a 1366 px, se revisa. |
| **Filtrar y ordenar a la vista**, mostrando cuándo hay un filtro activo. | NN/g, Laubheimer 2022 (abierta). | [X] | Una tabla filtrada sin aviso parece una tabla con datos de menos. |
| **Densidad de fila** según el uso: md por omisión; xs o sm para el experto diario. | Carbon (abierta). | [F] | Ver §4.2. |

---

## 6. Estados y mensajes

| Tema | Fuente | Tipo | Qué dice |
|---|---|---|---|
| Mensajes de error | Neusesser, T. y Sunwall, E. «Error-Message Guidelines», NN/g, 14/05/2023. https://www.nngroup.com/articles/error-message-guidelines/ (abierta) | [X] | **Visibles:** cerca de su origen; con color, ícono y texto («Never use exclusively color»); gravedad proporcional (modal solo para lo grave); no adelantarse («presenting errors too early is a hostile pattern»). **Comunicación:** lenguaje llano, sin códigos; problema concreto («An error occurred» no sirve); remedio; sin culpar. **Eficiencia:** prevenir, **conservar lo escrito**, ofrecer correcciones probables. |
| Errores en formularios | Bargas-Avila pautas 13 a 17 (Seckler 2014, abierta). | [X] validado [E] | Formato dicho antes; error cortés, que diga qué y cómo; nunca borrar lo escrito; visible a la primera. |
| Tolerancia a errores | ISO 9241-110:2020, *Interaction principles*: idoneidad para la tarea, autodescripción, conformidad con las expectativas, aprendizaje, controlabilidad, **robustez ante errores de uso** (evitar, tolerar y recuperar) y compromiso del usuario. https://www.iso.org/standard/75258.html (**403**, no se abrió); lista verificada en https://en.wikipedia.org/wiki/ISO_9241 (abierta) y en el índice de la vista previa de ANSI (registro). | [N] | La norma completa es de pago; no se cita su texto. La aplicación (inferencia): prevenir antes que avisar, permitir deshacer, y que el error diga cómo salir. |
| Estados vacíos | Kaplan, K. «Designing Empty States in Complex Applications: 3 Guidelines», NN/g, 19/09/2021. https://www.nngroup.com/articles/empty-state-interface-design/ (abierta) | [X] | Decir el estado del sistema (un vacío total confunde, y «No hay registros» **mientras carga** es dañino); enseñar en contexto; dar el camino directo a la tarea clave. |
| Estados vacíos | Carbon, *Empty states pattern*. https://carbondesignsystem.com/patterns/empty-states-pattern/ (abierta) | [F] | Tipos: sin datos (primer uso), por acción (búsqueda sin resultados) y por error (permiso, configuración). Título y cuerpo; la acción es opcional pero recomendada. Título en positivo («Empiece agregando…» mejor que «No tiene…»); pocas palabras; sin jerga del producto. |
| Carga | Carbon, *Loading pattern*. https://carbondesignsystem.com/patterns/loading-pattern/ (abierta) | [F] | Esqueleto en la carga inicial de contenedores y tablas, unos segundos como mucho; `InlineLoading` cuando procesa un solo componente; carga a pantalla completa solo si toda la página procesa; si dura más de un momento, indicador de progreso. |
| Carga | Tankala, S. «Skeleton Screens 101», NN/g, 04/06/2023. https://www.nngroup.com/articles/skeleton-screens/ (abierta) · Sherwin, K. «Progress Indicators Make a Slow System Less Insufferable», NN/g, 26/10/2014. https://www.nngroup.com/articles/progress-indicators/ (abierta) · Nielsen, límites de 0,1, 1 y 10 s (C13). | [X] | Menos de 1 s: nada. De 2 a 10 s: indicador en bucle (o esqueleto si es la página entera). Más de 10 s: barra de porcentaje, estimación del tiempo y forma de cancelar. Sherwin cita un estudio de la Universidad de Nebraska-Lincoln en el que con barra se esperó en promedio **tres veces más** (sin autores nombrados). |
| Notificaciones | Carbon, *Notification pattern*. https://carbondesignsystem.com/patterns/notification-pattern/ (abierta) | [F] | En la región donde se trabaja y cerca de lo que trata; *inline* persiste hasta resolverse; *toast* sin acción se va solo; modal solo si es crítico; mensajes de no más de dos líneas; «Do not leave users without next steps». |
| Éxito | Bargas-Avila pauta 19 (abierta). | [X] | La confirmación dice qué pasará después. |
| Lenguaje claro | ISO 24495-1:2023, *Plain language — Part 1: Governing principles and guidelines*, ISO/TC 37. https://www.iso.org/standard/78907.html (**403**). Cuatro principios verificados en la Federación Internacional de Lenguaje Claro: https://www.iplfederation.org/iso-standard/ (registro): el lector obtiene lo que necesita (**pertinente**), lo encuentra fácilmente (**localizable**), lo entiende (**comprensible**) y puede usarlo (**utilizable**). | [N] | Se aplica a textos; los ejemplos son en inglés, pero vale para cualquier lengua escrita. |

**La acción siguiente siempre visible.** Las fuentes coinciden por caminos distintos: un solo principal que es el
siguiente paso (Carbon, GOV.UK), la confirmación que dice qué pasa después (Bargas-Avila 19), el estado vacío con su
camino directo (NN/g 2021, Carbon) y la notificación que nunca deja sin siguiente paso (Carbon). La regla para Sílice:
**en cada estado** (vacío, error, carga larga, éxito) hay una frase que dice qué pasó y **un** control que lleva al
siguiente paso.

---

## 7. Guardias automáticas y sus límites

| Fuente | Tipo | Qué dice | Límite |
|---|---|---|---|
| Deque, «Automated Testing Study Identifies 57 Percent of Digital Accessibility Issues» (2021). https://www.deque.com/blog/automated-testing-study-identifies-57-percent-of-digital-accessibility-issues (registro) | [E] del fabricante, autoinformado | Más de 2.000 auditorías, más de 13.000 páginas y casi 300.000 problemas: axe-core detectó el **57,38 %** del **volumen** de problemas; con pruebas guiadas, el 80,39 % (informe de 2022). | Lo publica el fabricante de axe. Mide volumen (los problemas frecuentes, como el contraste, pesan mucho), no tipos de barrera. |
| Duran, M. «What we found when we tested tools on the world's least-accessible webpage», GDS, 24/02/2017. https://accessibility.blog.gov.uk/2017/02/24/what-we-found-when-we-tested-tools-on-the-worlds-least-accessible-webpage/ (abierta) | [E] | 143 barreras sembradas en 19 categorías; 10 herramientas gratuitas: la mejor encontró el 37 % (41 % contando avisos de revisión manual), la peor el 17 %, y el 29 % no lo encontró ninguna. «Cannot be relied on, by themselves». | Prueba con fallos artificiales; mide **tipos** de barrera, no volumen. Por eso no contradice a Deque: miden cosas distintas. |
| Ngo, D. C. L., Teo, L. S. y Byrne, J. G. (2003). «Modelling interface aesthetics». *Information Sciences* 152, 25-46. doi:10.1016/S0020-0255(02)00404-8 (registro) | [E] | Catorce medidas calculables de la disposición (equilibrio, simetría, densidad, regularidad, etc.) para estimar la estética de una pantalla. | Predice **estética percibida**, no si la persona termina la tarea. |
| Reinecke, K. et al. (2013). «Predicting Users' First Impressions of Website Aesthetics with a Quantification of Perceived Visual Complexity and Colorfulness». CHI 2013, 2049-2058, Harvard. https://www.eecs.harvard.edu/~kgajos/papers/2013/reinecke13predicting.shtml (registro) | [E] | 548 voluntarios valoraron 450 sitios: complejidad visual y colorido calculados explican casi la mitad de la varianza del atractivo tras 500 ms; la complejidad pesa más. | Primera impresión, no uso sostenido; sitios web, no aplicaciones de trabajo. |
| Nielsen, J. «Why You Only Need to Test with 5 Users», NN/g, 18/03/2000, sobre Nielsen y Landauer (1993), INTERCHI. https://www.nngroup.com/articles/why-you-only-need-to-test-with-5-users/ (abierta) | [E] (modelo) y [X] | N(1 − (1 − L)ⁿ) con L ≈ 31 %: 5 usuarios encuentran ≈ 85 % de los problemas. Mejor **tres rondas de 5** que una de 15. Con grupos de usuarios distintos, 3 o 4 por grupo; para métricas cuantitativas, unos 20. | Supone usuarios parecidos y un L promedio. |
| Faulkner, L. (2003). «Beyond the five-user assumption». *Behavior Research Methods, Instruments & Computers* 35(3), 379-383. doi:10.3758/BF03195514 (registro) | [E] (simulación con muestras de 5 a 60) | Según la cita de terceros, un grupo cualquiera de 5 puede dejar sin ver casi la mitad de los problemas; cada usuario añadido mejora la probabilidad. | **Contradice** la lectura simple de Nielsen; NN/g responde que nunca recomendó una sola ronda de 5. |
| Brooke, J. (1986). «SUS: a "quick and dirty" usability scale», Digital Equipment Corporation; publicado en 1996 en *Usability Evaluation in Industry*, Taylor & Francis (registro, citado en la bibliografía de Seckler 2014). Bangor, Kortum y Miller (2008, 2009): escala de adjetivos; 68 como promedio (Sauro, MeasuringU) (registro, fuentes secundarias). | [E] (cuestionario validado) | 10 ítems, de 0 a 100; ≈ 68 es el promedio de muchos productos, no un aprobado. | Mide la percepción global; no dice **qué** falla. |
| Estado del repo | — | `frontend-desktop/package.json` (árbol `s2mi2`) trae Vitest 5 y Testing Library, pero **ni axe-core ni jest-axe ni vitest-axe**, y ningún complemento de ESLint de accesibilidad (solo `eslint-plugin-react-hooks`). | Hoy la accesibilidad no se vigila en la CI. |

**Lint de diseño:** no se encontró evidencia empírica publicada de que un *lint* de diseño (contar botones principales,
prohibir texto de ejemplo como etiqueta, contar controles) mejore la usabilidad medida. Lo que sí hay es evidencia de que
las comprobaciones automáticas **encuentran una parte** de los problemas (accesibilidad: del 17 al 57 % según cómo se
cuente) y de que las métricas de la disposición predicen la **estética percibida** (Ngo, Reinecke). Conclusión para la
skill: las guardias automáticas sirven para **que no vuelva a pasar** lo que ya se sabe que está mal (regresión), no para
demostrar que una pantalla es buena. Para eso hace falta gente: rondas de 5 presupuestistas por perfil (Nielsen), y el SUS
como número de seguimiento entre versiones, no como veredicto.

---

## 8. Borrador de reglas accionables para Sílice

Forma: **Hacer / No hacer / Por qué (fuente) / Cómo se comprueba**. «Auto» = prueba de Vitest y Testing Library o lint en la
CI; «Humano» = revisión de diseño o prueba con usuarios. Complementan las doce reglas previas; donde una amplía a otra, se
dice.

### Cognición y lenguaje

**UX-01 · Lo que hay que comparar va junto.**
- Hacer: si la persona necesita dos cifras para decidir (plan y real, antes y después), van en la misma vista y a la vista a la vez.
- No hacer: pedirle que recuerde una cifra de otra pestaña, otro paso o un modal cerrado.
- Por qué: la memoria de trabajo sostiene de 3 a 5 elementos (Cowan 2001, C2); las pestañas no sirven para comparar (NN/g *Tabs*).
- Cómo se comprueba: Humano (revisión: «¿qué tiene que recordar la persona para decidir?»).

**UX-02 · La explicación, una vez y a pedido.**
- Hacer: una línea pegada a la cifra (regla previa 7) y el detalle largo plegado en «¿Qué es esto?».
- No hacer: repetir la misma explicación en la ayuda del campo, en la nota de la tabla y en el pliegue; ni poner párrafos fijos sobre cada campo.
- Por qué: efecto de redundancia y de inversión por pericia (Sweller et al. 2019; Kalyuga et al. 2003, C3 y C4).
- Cómo se comprueba: Auto (una prueba que busca textos duplicados de más de N palabras dentro de una misma vista); Humano.

**UX-03 · El rótulo dice qué hay detrás, en palabras de obra.**
- Hacer: pestañas, menús, botones y pliegues con un rótulo que nombra el contenido o el resultado («Cuándo termina cada partida», «Ver las 12 partidas que van a tiempo»).
- No hacer: «Ver más», «Detalles», «Opciones», «Procesar» o nombres internos («Reproyección», «Delta»).
- Por qué: olor de la información (Pirolli y Card 1999; Budiu 2020, C16).
- Cómo se comprueba: Auto (lista de rótulos prohibidos en `getAllByRole('button'|'tab'|'link')` y en `<summary>`, ampliando `sinJergaInterna.test.ts`); Humano.

**UX-04 · Lenguaje claro en todo texto de pantalla.**
- Hacer: frases cortas, en voz activa, con la palabra informativa al principio; usted; la sigla, si hace falta, entre paréntesis después de la palabra (regla previa 10).
- No hacer: jerga de software («payload», «endpoint», «null»), fórmulas internas («V' = V») ni códigos de error a la vista.
- Por qué: ISO 24495-1:2023 (pertinente, localizable, comprensible, utilizable); NN/g *F-pattern* (las dos primeras palabras); NN/g *Error messages*.
- Cómo se comprueba: Auto (lista de términos prohibidos; títulos de más de N palabras); Humano (lectura por alguien de obra).

**UX-05 · Se reconoce, no se recuerda.**
- Hacer: autocompletado con código **y** descripción en todo campo que pide un código (insumo, partida, serie, obra); «últimos usados» arriba.
- No hacer: un campo de texto libre que exige escribir un código exacto de memoria.
- Por qué: reconocer es más fácil que recordar (Budiu 2024, C7); el dueño ya lo pidió (memoria del 2026-10-21).
- Cómo se comprueba: Auto (los campos de código son `ComboBox` o `FilterableMultiSelect`, no `TextInput`); Humano.

**UX-06 · Como en Excel y en Windows.**
- Hacer: en el editor de hoja, Enter baja, Tab va a la derecha, Esc cancela la edición, Ctrl+Z deshace y F2 edita; en los modales, Enter activa el principal y Esc cierra.
- No hacer: atajos propios que contradigan a Excel ni comportamientos «innovadores» de selección o desplazamiento.
- Por qué: ley de Jakob (Nielsen 2000, C14); Microsoft *Command buttons* (Enter y Esc).
- Cómo se comprueba: Auto (pruebas con `user-event` del teclado en la hoja y en los modales).

### Formularios

**UX-07 · Una columna, etiquetas encima.**
- Hacer: una pregunta por fila; 2 o 3 campos en una línea solo si van juntos; la etiqueta siempre encima y fuera del campo.
- No hacer: rejillas de varias columnas de campos sin relación; usar el texto de ejemplo (`placeholder`) como etiqueta.
- Por qué: Bargas-Avila pautas 5 y 6, validadas en Seckler et al. (2014, N = 65); Penzo (2006); Carbon *Forms*; NN/g *Placeholders* (2014).
- Cómo se comprueba: Auto (todo `textbox` y `combobox` tiene nombre accesible por `labelText`, no por `placeholder`); Humano (columnas).

**UX-08 · Agrupar con espacio y con un título que es una pregunta.**
- Hacer: grupos de pocos campos con un título-pregunta; más aire entre grupos que dentro; el orden del documento que la persona tiene en la mano (regla previa 11).
- No hacer: una sola lista larga de campos, ni cajas dentro de cajas para agrupar.
- Por qué: proximidad y región común (Harley 2020, C8 y C9); Jarrett y Gaffney (2008), la capa de «conversación».
- Cómo se comprueba: Humano.

**UX-09 · Hasta cuatro opciones, a la vista.**
- Hacer: con 2 a 4 opciones fijas, `RadioButtonGroup` con la recomendada primero y marcada; con más, desplegable o autocompletado ordenado por uso o por orden lógico.
- No hacer: un desplegable para «Sí / No», ni listas sin orden.
- Por qué: Bargas-Avila pautas 10 y 11; Hick-Hyman con opciones desiguales (C5); E5 (valores por omisión).
- Cómo se comprueba: Auto (un `Select` con 4 opciones o menos falla la prueba de la pantalla).

**UX-10 · Obligatorio y opcional, los dos marcados.**
- Hacer: «(opcional)» junto a la etiqueta del campo opcional, y el obligatorio con su marca; pocos opcionales a la vista (el resto en «Más opciones»).
- No hacer: confiar en un «Todos los campos son obligatorios» al principio.
- Por qué: Baymard (2018, pruebas de usuarios: el 32 % chocó con un error cuando solo se marcaban los opcionales); Bargas-Avila pauta 4. **Contradice a Carbon** (marcar solo la minoría): manda la evidencia de usuarios.
- Cómo se comprueba: Auto (todo campo no obligatorio lleva «(opcional)» en su nombre accesible).

**UX-11 · El formato, antes; el error, al salir del campo y en el resumen.**
- Hacer: decir el formato en la ayuda («Escriba con coma decimal: 0,10»); validar al salir del campo; al pulsar el principal, un resumen arriba con enlaces a cada error y el foco en el primero.
- No hacer: validar mientras se escribe; marcar en rojo un campo que la persona todavía no tocó.
- Por qué: Wroblewski (2009, −22 % de errores y −42 % de tiempo validando al salir); Bargas-Avila pautas 13 y 16; Carbon (validar al perder el foco); NN/g (no adelantar errores).
- Cómo se comprueba: Auto (escribir un valor malo no muestra error hasta el `blur`; enviar con errores pone el foco en el resumen).

**UX-12 · Un error no borra nada.**
- Hacer: tras un error de la API o de validación, todo lo escrito sigue ahí; el `detalle` del servidor se muestra tal cual y cerca del campo.
- No hacer: reiniciar el formulario ni cerrar el modal al fallar.
- Por qué: Bargas-Avila pauta 15; NN/g *Error messages* (conservar lo escrito); ISO 9241-110 (robustez ante errores).
- Cómo se comprueba: Auto (simular un 422 y comprobar que los valores siguen en los campos).

### Botones y acciones

**UX-13 · Un solo botón principal por vista, y es el siguiente paso.**
- Hacer: un `kind="primary"` por vista (o por modal abierto); los demás, secundarios, terciarios o *ghost*.
- No hacer: dos principales a la vista, ni un principal en la barra de la tabla si la página ya tiene uno.
- Por qué: Carbon *Button* («Each page should have only one primary button»); GOV.UK; Von Restorff (C12); ya está en `DESIGN.md` según el informe previo.
- Cómo se comprueba: Auto (contar los botones `cds--btn--primary` visibles por vista: 1 como máximo).

**UX-14 · El orden de Carbon en todas partes.**
- Hacer: en un formulario de página, el principal a la izquierda y el secundario a su derecha, al pie; en un modal y en un asistente, el secundario a la izquierda y el principal a la derecha.
- No hacer: mezclar el orden de Windows (Aceptar a la izquierda) en unos modales y el de Carbon en otros.
- Por qué: Carbon *Button* y *Modal*; NN/g 2008 (lo que cuesta es la incoherencia). **Contradice a Windows** (Microsoft Win32 y WinUI ponen la acción a la izquierda): se elige Carbon porque es la plataforma de la aplicación, y los rótulos específicos (UX-15) reducen el riesgo de confusión.
- Cómo se comprueba: Auto (en cada `Modal` y `ComposedModal`, el último botón del pie es el principal; en los formularios de página, el primero).

**UX-15 · El botón dice lo que hace.**
- Hacer: verbo e imperativo más objeto («Guardar el estudio», «Calcular el reajuste»); «Cancelar» se queda como «Cancelar».
- No hacer: «Aceptar», «OK», «Sí / No» o «Enviar» como botón de acción.
- Por qué: Microsoft *Dialog boxes* y *Command buttons*; Apple; NN/g *Confirmation dialogs*; GOV.UK.
- Cómo se comprueba: Auto (lista de rótulos prohibidos en botones principales).

**UX-16 · Lo destructivo: deshacer antes que preguntar.**
- Hacer: si se puede deshacer, se hace y se ofrece «Deshacer» en la notificación; si no se puede, modal de peligro de Carbon con el botón `danger` que nombra la consecuencia («Borrar la obra y sus 3 versiones») y el foco inicial en «Cancelar».
- No hacer: confirmar acciones rutinarias; poner lo destructivo como botón por omisión; depender solo del rojo.
- Por qué: Nielsen 2018 (el exceso de confirmaciones hace que no se lean); Microsoft (no hacer predeterminado lo destructivo); Apple; GOV.UK (no solo el color); Carbon *Danger*.
- Cómo se comprueba: Auto (en los modales de peligro, el foco inicial no está en el botón `danger`); Humano (¿es reversible?).

**UX-17 · Objetivos de 24 px y la acción cerca del final de la tarea.**
- Hacer: todo control pulsable mide 24 × 24 px como mínimo (también los iconos de fila en tablas xs); el principal va al pie, junto al último campo.
- No hacer: iconos de 16 px sin margen en tablas densas; el principal solo en la cabecera de un formulario largo.
- Por qué: WCAG 2.2, 2.5.8 (AA); ley de Fitts (MacKenzie 1992 y 2018, C6); Carbon *Forms*.
- Cómo se comprueba: Auto (axe con la regla `target-size`, si se instala; o una prueba en el navegador que mida `getBoundingClientRect`).

**UX-18 · Doble clic bloqueado y respuesta en menos de 0,4 s.**
- Hacer: el principal se deshabilita y muestra `InlineLoading` mientras se procesa; filtrar, editar una celda o abrir un pliegue responde en menos de 0,4 s.
- No hacer: permitir dos envíos; acciones sin respuesta visible durante más de 1 s.
- Por qué: Bargas-Avila pauta 18; GOV.UK (ignorar el segundo clic); Doherty y Thadani (1982); Nielsen (0,1 / 1 / 10 s), C13.
- Cómo se comprueba: Auto (un segundo clic durante la carga no genera una segunda llamada al `fetch` simulado).

### Espacio y vistas

**UX-19 · La forma de la vista sigue al tipo de tarea.**
- Hacer: elegir antes de diseñar uno de los cinco tipos (formulario de captura, tabla de resultados, tablero, editor de hoja o asistente) y aplicar su fila de §4.2.
- No hacer: un tablero que también es formulario, ni un asistente para una tarea diaria.
- Por qué: Few (el tablero vigila, no explora); E7 y GOV.UK (el asistente, para lo ocasional); NN/g *Complex apps* (sin flujos rígidos).
- Cómo se comprueba: Humano (el expediente de la pantalla declara su tipo).

**UX-20 · Lo importante, en la primera pantalla y arriba a la izquierda.**
- Hacer: la frase de respuesta y la acción principal caben en la primera pantalla a 1366 × 768; lo secundario, debajo o plegado.
- No hacer: empezar la vista con instrucciones largas, filtros o una tabla de parámetros antes de la respuesta.
- Por qué: NN/g *Scrolling and attention* (57 % de la mirada en la primera pantalla, 65 % en el 40 % superior); patrón en F; posición serial (C11).
- Cómo se comprueba: Auto (en la prueba del navegador, la frase de respuesta tiene `top` menor que la altura de la ventana); Humano.

**UX-21 · Pestañas solo si no hay que comparar; pliegues de un solo nivel.**
- Hacer: pestañas para grupos que se usan por separado; `<details>` o acordeón para pocas secciones de muchas, con un resumen que dice qué hay y cuántos; «Abrir todo» si son más de tres.
- No hacer: pestañas para cosas que se comparan; un pliegue dentro de otro; esconder en un pliegue lo que casi todos necesitan.
- Por qué: NN/g *Tabs* (2024) y *Accordions* (2023); E3 (dos niveles como máximo).
- Cómo se comprueba: Auto (ningún `<details>` contiene otro `<details>`; ninguna `TabList` dentro de un `TabPanel`).

**UX-22 · La densidad según el uso.**
- Hacer: md (40 px) por omisión; sm o xs en el editor de hoja y en las tablas de uso diario; los textos corridos con no más de ≈ 75 caracteres por línea.
- No hacer: tablas xl o tarjetas grandes para datos de trabajo; párrafos de ayuda a todo el ancho de la pantalla.
- Por qué: Carbon *Data table* (tamaños de fila); inversión por pericia (C4); Baymard (2022, 50 a 75 caracteres). Laguna: no hay estudio empírico de densidad para expertos (§4.1).
- Cómo se comprueba: Auto (prop `size` de `DataTable` según el tipo de vista; `max-width` en `ch` en los textos); Humano.

**UX-23 · Maestro-detalle para recorrer colecciones.**
- Hacer: lista a la izquierda y detalle a la derecha (lado a lado en escritorio) para obras, APU o valuaciones; editar una fila con muchos campos en un panel lateral no modal.
- No hacer: abrir un modal por cada fila que se quiere revisar o editar.
- Por qué: Microsoft *List/details*; NN/g *Data tables* (panel no modal mejor que modal); Carbon *Modal* (no usar modal para tareas repetidas).
- Cómo se comprueba: Humano.

### Tablas

**UX-24 · Una tabla, una pregunta, y los números a la derecha.**
- Hacer: frase de respuesta encima (regla previa 1); identificador legible en la primera columna; números a la derecha, cifras tabulares y los mismos decimales en la columna; el encabezado alineado como sus datos; la unidad en el encabezado.
- No hacer: centrar columnas; mezclar decimales en una columna; columnas que no responden la pregunta a la vista por omisión.
- Por qué: Few (cap. 3 y *Show Me the Numbers*); guía de datos de la UE; Adobe Spectrum; NN/g *Data tables*.
- Cómo se comprueba: Auto (toda columna numérica lleva la clase de alineación derecha; todas las celdas de una columna tienen los mismos decimales).

**UX-25 · Encabezado fijo, filtro visible y fila resaltada.**
- Hacer: encabezado (y primera columna si hay desplazamiento horizontal) fijos; filtros a la vista con aviso de «filtro activo»; resaltado de la fila al pasar el ratón; cebra solo en tablas anchas.
- No hacer: perder el encabezado al desplazarse; filtrar sin decirlo.
- Por qué: NN/g *Data tables*; Enders (2008, la cebra ni ayuda ni daña de forma significativa); Carbon.
- Cómo se comprueba: Auto (con un filtro aplicado, existe el texto del filtro activo); Humano (encabezado fijo en el navegador).

**UX-26 · Barra de herramientas corta y paginación abajo.**
- Hacer: hasta cinco acciones globales sobre la tabla; las acciones por fila, en el menú de la fila; las acciones en lote, en la barra que aparece al seleccionar; la paginación al pie.
- No hacer: más de cinco botones sobre la tabla; botones de fila que repiten las acciones globales.
- Por qué: Carbon *Data table* («Include up to five actions within the table toolbar»).
- Cómo se comprueba: Auto (contar los botones dentro de `TableToolbarContent`: 5 como máximo).

### Estados y mensajes

**UX-27 · Cada estado tiene su frase y su siguiente paso.**
- Hacer: vacío (qué falta y el botón que lo resuelve, título en positivo); cargando (esqueleto si es la página entera, `InlineLoading` si es un componente; más de 10 s, porcentaje y «Cancelar»); error (qué pasó, cómo corregirlo, cerca del origen, con ícono y texto); éxito (qué quedó hecho y qué sigue).
- No hacer: un panel en blanco; «No hay datos» mientras carga; «Ocurrió un error»; un *toast* que desaparece con un error que hay que corregir.
- Por qué: NN/g *Empty states* (2021), *Error messages* (2023), *Skeleton screens* (2023) y *Progress indicators* (2014); Carbon *Empty states*, *Loading* y *Notifications*; Bargas-Avila pautas 14, 17 y 19.
- Cómo se comprueba: Auto (por pantalla, una prueba por estado: con la API simulada vacía, lenta, con error y con éxito, se busca la frase y el control del siguiente paso).

**UX-28 · El error no depende solo del color.**
- Hacer: ícono, texto y color juntos; el mensaje enlazado al campo (`invalidText` de Carbon) y anunciado (`role="alert"` o región viva).
- No hacer: solo un borde rojo; mensajes solo en un *tooltip*.
- Por qué: NN/g *Error messages* («Never use exclusively color»); WCAG 1.4.1; Carbon *Notifications*.
- Cómo se comprueba: Auto (axe, si se instala; y una prueba de que el error tiene nombre accesible y rol).

### Guardias

**UX-29 · Las guardias automáticas evitan regresiones; la gente juzga.**
- Hacer: instalar axe en las pruebas de componentes (`vitest-axe` o `jest-axe`) y correrlo en cada pantalla; mantener las pruebas de conteo (controles visibles, botones principales, acciones de la barra, rótulos prohibidos); antes de cerrar un rediseño grande, una ronda con 5 presupuestistas y el SUS como número de seguimiento.
- No hacer: dar una pantalla por buena porque pasa axe y las pruebas; tomar el SUS como aprobado o reprobado.
- Por qué: Deque (57 % del volumen, autoinformado); GDS 2017 (del 17 al 41 % de los tipos de barrera, y el 29 % sin detectar); Nielsen y Landauer (1993) y Faulkner (2003); Brooke (1986). Hoy `frontend-desktop/package.json` (árbol `s2mi2`) no trae axe.
- Cómo se comprueba: Auto (el paquete existe y hay una prueba de axe por página); Humano (acta de la ronda con usuarios).

---

## 9. Contradicciones encontradas (resumen)

| Tema | Quién dice qué | Qué se elige para Sílice |
|---|---|---|
| Orden Aceptar / Cancelar | Windows Win32 y WinUI: la acción a la izquierda. Apple: Cancelar al inicio. Carbon: la acción a la derecha en modales y asistentes, y a la izquierda en formularios de página. NN/g: seguir la plataforma, sin datos. | El orden de Carbon, coherente en toda la aplicación, con rótulos específicos y teclado de Windows (UX-14 a UX-16). |
| Ubicación de la etiqueta | Encima (Penzo, Bargas-Avila, Carbon) frente a la derecha en formularios de varias columnas (Das et al. 2008). | Encima (UX-07). |
| Obligatorio u opcional | Carbon: marcar solo la minoría. Baymard: marcar ambos. Bargas-Avila: marcar los obligatorios. | Ambos (UX-10). |
| Cuándo mostrar errores | Bargas-Avila 16: al enviar, todos juntos. Wroblewski y Carbon: al salir del campo. | Las dos, en capas (UX-11). |
| Una cosa por página | GOV.UK: empezar con una cosa por página. NN/g: evitar flujos rígidos en aplicaciones complejas; el propio GOV.UK admite unir en servicios internos. | Una página por tarea con grupos; asistente solo para lo ocasional (UX-19). |
| Rayas de cebra | NN/g y Carbon: ayudan a seguir la fila. Enders (2008, N = 244): sin diferencia significativa. | Líneas y resaltado por omisión; cebra solo en tablas anchas (UX-25). |
| Cinco usuarios | Nielsen y Landauer: ≈ 85 % con 5. Faulkner: un grupo de 5 puede dejar ver casi la mitad. | Rondas repetidas de 5 por perfil, no una sola (UX-29). |
| Cobertura de las pruebas automáticas | Deque: 57 % (volumen). GDS: 17 a 41 % por herramienta (tipos). | No se contradicen: miden cosas distintas. Las dos dicen que no basta (UX-29). |
| 7±2 | La cultura popular de UX usa «7±2» como cupo de elementos en pantalla. Miller no lo propuso así; Cowan sitúa el límite en 3 a 5 chunks retenidos. | No se usa «7» como cupo de pantalla; el cupo de 8 controles visibles de la regla previa 2 es una decisión de diseño, no una cifra de Miller. |

## 10. Fuentes que no se pudieron abrir o lagunas

- **No abiertas** (403, error de certificado o página vacía): ISO 9241-110:2020 e ISO 24495-1:2023 en iso.org; Sweller,
  van Merriënboer y Paas (2019) en core.ac.uk y Springer; Cowan en Cambridge (sí se abrió el PDF del autor); Material
  Design 3 y 2 (*Dialogs*); Apple HIG *Alerts* (solo por búsqueda); el informe de IBM de Doherty y Thadani; el artículo de
  NN/g sobre la ley de Jakob y el de posición serial (404). El PDF de Shneiderman es una imagen escaneada; se usó el resumen
  del repositorio de la Universidad de Maryland.
- **Solo registro**: Hick (1952), Hyman (1953), Murdock (1962), Von Restorff (1933), Pirolli y Card (1999), MacKenzie
  (1992), Kalyuga et al. (1998 y 2003), Das et al. (2008), Jarrett y Gaffney (2008), Tufte (1983), Few (*Show Me the
  Numbers* e *Information Dashboard Design*), Bringhurst (no se buscó: Baymard cita a Ruder y a webtypography.net), Ngo et
  al. (2003), Reinecke et al. (2013), Faulkner (2003), Brooke (1986) y Bangor et al. (2008 y 2009).
- **Lagunas**: no se encontró un estudio empírico sobre densidad para usuarios expertos en aplicaciones de escritorio, ni
  sobre un número máximo de columnas por tabla, ni sobre la eficacia medida de un *lint* de diseño. No se encontró nada
  pertinente de CMU HCII ni de Stanford HCI en el tiempo de esta pasada (no se buscó a fondo).
