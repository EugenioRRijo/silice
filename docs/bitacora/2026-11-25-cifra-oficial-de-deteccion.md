# Acta: cuál cifra de detección cuenta para el criterio de fracaso (2026-11-25)

**Por qué hace falta.** El criterio de fracaso sellado en la etiqueta `reglas-congeladas-2026-11-24`
([plan no circular](../planes/2026-11-23-plan-auditoria-no-circular.md), «Criterio de fracaso») dice «detecta
menos del 50 % de las fallas que inyectó el tercero», pero no dice cómo se siembran. El ensayo general del
2026-11-25, con un libro **ficticio** y la taxonomía de plantilla (semilla 7, n = 12), dio dos cifras muy distintas:

| Modo | Cómo se mide | Ensayo ficticio |
|---|---|---|
| Todas a la vez | `scripts/medir_inyeccion.py` con las 12 fallas en el mismo libro, recalculado y trasplantado | 4 de 12 |
| Una por vez | `scripts/medir_inyeccion.py --una-por-vez`: cada falla sola contra el libro limpio | 10 de 12 |

Estas cifras son de un libro ficticio y **no** son resultados de la tesis.

**Decisión de Eugenio (2026-11-25, antes de medir los libros nuevos).** La cifra oficial es la de **todas a la vez**.
Es la más estricta, se parece más a un libro real con varios errores juntos y es la misma que ven los evaluadores en
las planillas. La de **una por vez** se informa al lado como cifra secundaria, con su propio intervalo de Wilson, y no
decide el fracaso.

**Alcance.** Esta acta aclara el criterio y no lo cambia: el umbral del 50 %, el del 40 % de falsos positivos y el del
kappa 0,4 siguen como están sellados. El texto sellado del plan no se edita; esta entrada fechada es la aclaración
que pide la guía del tercero («si cambiara, se registra con fecha y motivo»). La medición del 2026-11-24 en el libro
de desarrollo, que comparó con el umbral el modo de una por vez (plan, «Segunda medición»), queda como historia del
desarrollo, igual que antes.

**Cómo se revierte.** Con otra acta fechada, siempre antes de abrir los libros nuevos. Después de abrirlos no se
revierte.
