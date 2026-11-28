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

**Segunda decisión de Eugenio (2026-11-25, antes de medir): qué cuenta como «detectada».** Cuando el evaluador marca
las planillas, para el criterio del 50 % cuenta solo la falla que Sílice señaló **y** el evaluador confirmó como
verdadera. Así lo pide la frase sellada: «fallas que un experto independiente confirma». Las señaladas sin
confirmar se informan al lado. En la medición automática, sin evaluador, cuenta lo señalado, y la salida dice cuál de
las dos se evaluó. Surgió de la auditoría de Neon (Gemini) al código de medición.

**Cómo se revierte.** Con otra acta fechada, siempre antes de abrir los libros nuevos. Después de abrirlos no se
revierte.

## Enmienda del 2026-11-27: el ensayo se vuelve a medir

**Por qué.** La auditoría independiente de la lógica antes de `medicion-v1` (Claude Opus, solo lectura) halló que las
cifras del ensayo de esta acta ya no se reproducen: el «4 de 12 / 10 de 12» se midió con el inyector del commit
`890a6ed2`, y el inyector se corrigió después (`2951ba20`, 2026-11-25), que siembra algunas fallas en otras celdas.
Eugenio decidió volver a medir y documentar (2026-11-27: «Volver a medir y documentar»).

**Medición con el código de hoy** (herramientas en el commit `06ba7491`; el mismo libro **ficticio** generado con
`tests/fixtures/libros_empresa.py`, la taxonomía de plantilla, `--n 12 --semilla 7 --fecha 2026-11-25`):

| Modo | Comando | Resultado | Wilson 95 % |
|---|---|---|---|
| Todas a la vez (oficial) | `scripts/medir_inyeccion.py <libro> --taxonomia docs/tesis/taxonomia_fallas_plantilla.toml --n 12 --semilla 7 --fecha 2026-11-25` | 3 de 12 (25,0 %) | [8,9 %; 53,2 %] |
| Una por vez (secundaria) | el mismo con `--una-por-vez` | 11 de 12 (91,7 %) | [64,6 %; 98,5 %] |

Siguen sin ser resultados de la tesis: es un ensayo sobre un libro ficticio.

**Qué mide cada modo.** No cuentan «detectada» igual, y esta acta no lo decía:
- **Todas a la vez** pide un hallazgo nuevo **en la celda exacta** de la falla (sin evaluador): mide la
  **localización**.
- **Una por vez** cuenta **cualquier** hallazgo nuevo, en cualquier celda: mide la **reacción** del auditor a la falla.

Con evaluador, la columna «Detectado por hallazgo N°» de la clave corrige la localización. La decisión de esta acta
no cambia: la cifra oficial es la de todas a la vez.

**Un riesgo a la vista.** En este ensayo la cifra oficial (25 %) queda por debajo del umbral de fracaso del 50 %, como
ya quedaba la de antes (33 %). No decide nada: el criterio se aplica a la Fase 3, sobre libros nuevos y con la
taxonomía del tercero. Pero la diferencia entre localización y reacción (3 frente a 11 de 12) dice que buena parte
de las fallas producen un hallazgo en **otra** celda, y eso conviene mirarlo con el tutor antes de medir.

**Cómo se cita.** Toda cifra de detección se cita con el commit de las herramientas de medición con que se obtuvo.

