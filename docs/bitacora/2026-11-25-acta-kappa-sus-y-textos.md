# Acta: kappa experto–Sílice, personas del SUS y textos a la vista (2026-11-25)

Decisiones de Eugenio del 2026-11-25, tomadas **antes de abrir los libros nuevos y antes de la prueba con personas**.
Surgieron de contradicciones que encontró la revisión del capítulo IV (Argon, Gemini, y la corrección redactada por
Opus). El plan sellado ([plan no circular](../planes/2026-11-23-plan-auditoria-no-circular.md)) no cambia: estas
decisiones lo precisan, igual que la [acta de la cifra oficial](2026-11-25-cifra-oficial-de-deteccion.md).

## 1. Cómo se mide el kappa entre el experto y Sílice

**Problema.** El criterio de fracaso sellado dice «el kappa entre el experto y Sílice queda por debajo de 0,4», pero
ningún script lo calcula. `scripts/medir_auditoria_libro.py` comparaba con 0,4 el kappa entre dos planillas de
evaluadores, que mide otra cosa: el acuerdo entre personas.

**Decisión.** La unidad es la **partida** del presupuesto. Para cada partida del libro, el experto, en su revisión
ciega de la línea base humana, y Sílice, por sus hallazgos, dicen si la partida tiene o no un error que un
presupuestista corregiría. Con esa tabla de 2 × 2 se calcula el kappa de Cohen, que incluye las partidas sanas,
porque sin ellas el kappa no tiene sentido. Un hallazgo de Sílice cuenta para una partida cuando alguna de sus celdas
de origen está en esa partida o en el APU unido a ella. Un hallazgo que no se puede ubicar en ninguna partida
(RESUMEN, INSUMOS) se informa aparte y no entra en el kappa.

El kappa entre dos evaluadores, que mide la fiabilidad de las personas, se sigue informando por separado y **no** es un
criterio de fracaso.

## 2. Cuántas personas responden el SUS

**Decisión.** Cinco personas: los 3 economistas de la empresa y 2 personas que presupuestan pero no conocen Sílice.
Cinco es la cifra de referencia de Nielsen y Landauer (1993), y las dos personas nuevas muestran cómo usa el programa
alguien que llega por primera vez. Los resultados se informan por grupo (economistas y nuevos) y en conjunto.

## 3. Textos que rompen las reglas del proyecto, corregidos antes de la prueba

**Problema.** La auditoría del front del 2026-11-25 encontró textos que violan las reglas del proyecto y que la guardia
de la CI no detectó: tres frases en tuteo, decimales con punto en el texto emergente (`title`) de algunas cifras y
enteros sin punto de miles.

**Decisión.** Se corrigen **antes** de la prueba con personas, solo esos textos, sin cambiar ninguna lógica ni ninguna
pantalla. Es la corrección de un defecto respecto de reglas ya vigentes (trato de usted, coma decimal y punto de
miles), no una función nueva. El resto del plan del front espera a después de medir.

**Cómo se revierte.** Con otra acta fechada, siempre antes de abrir los libros nuevos y antes de la prueba con
personas.
