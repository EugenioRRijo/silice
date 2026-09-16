# Acta de revisión — Capítulo II (Sprint R1)

**Fecha:** 2026-09-15 · **Versión revisada:** commit de la Sesión R1.6 (`ca2353a`,
`docs(tesis): capitulo ii bases normativas y terminos`) · **Tutor:** revisión con la
[lista de cotejo](../rubrica_tutor.md), previa a la del tutor académico designado · **Tesista:**
autor del capítulo

La revisión aplica los criterios T1–T14 al archivo `docs/tesis/capitulos/02-marco-teorico.md`.
Los criterios verificables en forma automática (T1, T5, T9–T12) se contrastaron además con
`scripts/meta_redaccion.py`, que dio R3–R8 en OK sobre esta versión. Las correcciones se aplicaron
en la Sesión R1.7 y la meta se volvió a correr sobre el resultado.

| Código | Veredicto | Observación del tutor | Respuesta del tesista |
|---|---|---|---|
| T1 | cumple | Están los antecedentes en los tres ámbitos, las bases teóricas, las bases normativas, la definición de términos y la tabla de estado. | Sin cambios. |
| T2 | cumple con observaciones | Las bases teóricas sostienen OE1 a OE4 y OE6: ciclo del proyecto y estructura del APU; BIM, IFC y LOD; COVENIN y FCAS; aprendizaje automático y lenguaje natural; clasificación de AACE. Pero OE5, la verificación automática de consistencia, que es el aporte central, no tenía base teórica: solo aparecía en la definición de términos. OE7 (variante A) tampoco tiene base. | **Corregido:** se agregó §2.2.7, «Verificación automática basada en reglas», con Eastman et al. (2009) y Solihin y Eastman (2015), ambas verificadas; la definición de «verificación de consistencia» remite a ella. La base de OE7 (núcleo cerrado y adaptadores) se redacta solo si el tutor académico elige la variante A (decisión D3). |
| T3 | cumple | El capítulo no formula objetivos. Se comprobó que no los reformula ni los contradice: COVENIN respalda OE3, y la clasificación de AACE, OE6. | Sin cambios. |
| T4 | cumple con observaciones | (a) La autorrevisión de la Sesión R1.6 ya había retirado dos afirmaciones que excedían sus fuentes: que un presupuesto derivado de un modelo tridimensional «corresponde» a la clase 3, cuando AACE determina la clase por la madurez de los entregables, y un alcance de la norma COVENIN que no figura en su título. (b) Queda sin justificar por qué el caso de estudio es de clase 3. (c) La 18R‑97 se formula para las industrias de proceso; para la edificación existe la 56R‑08, cuyo rango para la clase 3 no se ha contrastado. (d) Todos los antecedentes nacionales están pendientes de verificación, de modo que ese ámbito descansa hoy en fuentes sin confirmar. | (a) Consta en el commit de R1.6; sin cambios adicionales. (b) La justificación con la madurez de los entregables del caso corresponde al capítulo III, y §2.3.3 lo declara. (c) Se lleva al tutor académico la elección entre 18R‑97 y 56R‑08; mientras tanto, el sistema usa la 18R‑97 declarada en la ERS, y el capítulo lo dice. (d) Se completan en la sesión de referencias pendientes; entretanto, cada cita lleva su marca (T10). |
| T5 | cumple | El caso se nombra «caso didáctico» en §2.2.4 y §2.3.1, y ningún pasaje lo presenta como obra ejecutada (meta R7). | Sin cambios. |
| T6 | cumple | Las cifras del proyecto (FCAS 6,00, bono de 1,00 USD, administración del 15 %, utilidad del 10 %, umbrales de la compuerta G2 y extremos de −20 % y +30 %) están en la tabla de cifras citables. Las de la literatura (rangos y 80 % de AACE, cinco desarrollos y cuatro etapas de Eastman et al., cuatro clases de Solihin y Eastman) llevan su cita. | Sin cambios. |
| T7 | cumple con observaciones | Cada antecedente dice qué aporta, salvo el del Colegio de Ingenieros de Venezuela, que describe la propuesta de ley marco sin vincularla con este trabajo. | **Corregido:** se agregó la oración que la vincula con la justificación institucional (§1.4.4). |
| T8 | cumple con observaciones | (a) Dos obras de AACE International del mismo año exigen los sufijos 2020a y 2020b. (b) La primera cita del autor corporativo COVENIN, en el capítulo I, no introducía la abreviatura como exige APA 7. (c) La convención colectiva sigue sin formato de documento legal (observación arrastrada del acta del capítulo I). | (a) Aplicados en R1.6 por orden alfabético del título; sin cambios. (b) **Corregido** en la Tabla 1.3 del capítulo I, con anexo en su acta. La meta R5 rechazaba la forma parentética con corchetes; se corrigió con una prueba nueva que primero falló. (c) Se ajusta cuando se confirme la vigencia en la Gaceta Oficial. |
| T9 | cumple con observaciones | Las 49 citas del capítulo tienen entrada en `referencias.md` (meta R5), pero la lista contenía dos entradas que ningún capítulo cita (Franco et al., 2015, y la tesis de la PUCP), y APA 7 solo admite obras citadas. | **Corregido:** ambas pasaron a la sección «Consultadas y no citadas», fuera de la lista APA, que queda con 36 entradas, todas citadas. |
| T10 | cumple | Toda cita de una referencia pendiente lleva la marca «[verificación pendiente]» (meta R6). La prueba negativa sobre el capítulo real, retirar la marca de la 56R‑08, hizo fallar R6. | Sin cambios. |
| T11 | cumple | Voz impersonal en todo el capítulo (meta R4). | Sin cambios. |
| T12 | cumple | Se usan BIM‑5D y sombra digital. «Gemelo digital» aparece solo en el subtítulo de antecedentes que lo trata, en §2.2.3, donde se delimita, y en la definición de términos (meta R8). | Sin cambios. |
| T13 | cumple con observaciones | §2.2 y §2.3 empezaban directamente en su primera subsección, sin un párrafo que anuncie el orden, a diferencia de §2.1. | **Corregido:** se agregó a cada una un párrafo de apertura con el hilo de la sección. |
| T14 | cumple | El capítulo sitúa el gemelo digital fuera de alcance (Tabla 2.1 y §2.2.3) y no contradice lo excluido en §1.5.2. | Sin cambios. |

**Resultado:** aprobado en revisión, con cinco correcciones aplicadas (T2, T7, T8, T9, T13) y dos
observaciones llevadas al tutor académico: la elección entre 18R‑97 y 56R‑08 (T4) y la base de OE7
si se elige la variante A (T2). Ningún criterio quedó en «no cumple».
