# Acta de revisión — Capítulo I (Sprint R1)

**Fecha:** 2026-09-15 · **Versión revisada:** commit de la Sesión R1.2
(`docs(tesis): capitulo i objetivos justificacion y delimitacion`) · **Tutor:** revisión con la
[lista de cotejo](../rubrica_tutor.md), previa a la del tutor académico designado · **Tesista:**
autor del capítulo

La revisión aplica los criterios T1–T14 al archivo `docs/tesis/capitulos/01-el-problema.md`.
Los criterios verificables en forma automática (T1, T5, T9–T12) se contrastaron además con
`scripts/meta_redaccion.py`, que dio R1, R2 y R4–R8 en OK sobre esta versión.

| Código | Veredicto | Observación del tutor | Respuesta del tesista |
|---|---|---|---|
| T1 | cumple | Están las cinco secciones del guion (planteamiento, formulación, objetivos, justificación, alcance y delimitación) y la tabla de estado. | Sin cambios. |
| T2 | cumple con observaciones | La Tabla 1.2 hace corresponder cada pregunta secundaria con un objetivo, pero OE1 (diagnóstico) y OE3 (base de datos y motor de costos) quedan asociados a la pregunta principal: ninguna pregunta secundaria los atiende. Es una debilidad heredada de las Bases del anteproyecto que un jurado puede señalar. | Se mantiene la redacción de las Bases, que es el insumo institucional, y la nota de la Tabla 1.2 declara la asociación y su motivo. Se lleva al tutor académico, junto con la decisión D3, la opción de formular dos preguntas secundarias para OE1 y OE3. |
| T3 | cumple con observaciones | Todos los objetivos empiezan con verbo en infinitivo y tienen producto. OE4 («con la técnica que permita la disponibilidad de datos») es menos medible que los demás, y el objetivo general de la variante A es extenso. | OE4 se conserva porque su criterio de medición existe y es verificable: la técnica la fija el conteo de registros por dominio con umbrales declarados antes de medir (compuerta G2). El objetivo general de la variante A se revisará si el tutor académico la elige. |
| T4 | cumple con observaciones | Las afirmaciones sobre la práctica se apoyan en literatura y en la documentación de los programas, pero **todas** las citas están pendientes de verificación. En particular, la comparación de tiempo y exactitud atribuida a Wahab y Wang (2022) y la afirmación sobre los programas de presupuesto deben confirmarse contra el contenido de las fuentes, no solo contra sus títulos. | Se verifica cada fuente en la Sesión R1.4. Si el contenido de una fuente no sostiene la afirmación, la oración se reescribe o se retira, y el cambio se registra en esta acta. |
| T5 | cumple | Los casos se presentan como didácticos: el de la clínica se declara ejercicio académico ficticio, y el de ARENAZA, segundo ejercicio académico. La prevalencia en obras reales se declara como limitación. | Sin cambios. |
| T6 | cumple con observaciones | Las magnitudes de la Tabla 1.1, el total de 1 586,61 USD y el 80/90 de ARENAZA están en la tabla de cifras citables, pero las dimensiones del caso (24 m de PVC de 4", tanquillas de 0,80 × 0,80 × 0,80 m, paredes de 0,10 m, cinco partidas) no lo están, aunque aparecen en §1.1.2 y en la Tabla 1.3. | **Corregido:** se agregó la fila «Dimensiones del caso didáctico» a `plan_redaccion.md` §5, con su fuente en `linea_base.md` §1. |
| T7 | cumple | Cada fuente citada en el planteamiento y en la justificación dice qué aporta al argumento: el ciclo del proyecto, la comparación entre procedimientos, el obstáculo de estandarización, el FCAS, las capacidades de los programas y la advertencia sobre redes neuronales con pocos datos. | Sin cambios. |
| T8 | cumple con observaciones | El formato autor‑año es correcto, las citas múltiples van en orden alfabético y «s.f.» se usa donde falta el año. La convención colectiva citada como autor corporativo debe ajustarse al formato APA 7 de documentos legales una vez verificada su referencia. | Se ajusta en la Sesión R1.4, cuando se confirme el período de vigencia y la fuente oficial. |
| T9 | cumple | Las 12 citas del capítulo tienen entrada en `referencias.md` (meta R5). | Sin cambios. |
| T10 | cumple | Toda cita de una referencia pendiente lleva la marca «[verificación pendiente]» (meta R6). | Sin cambios. |
| T11 | cumple | Voz impersonal en todo el capítulo (meta R4, con la detección ampliada a cualquier verbo en primera persona del plural). | Sin cambios. |
| T12 | cumple | Se usa BIM‑5D; «gemelo digital» aparece solo en lo que la investigación no comprende, con remisión al capítulo II (meta R8). | Sin cambios. |
| T13 | cumple con observaciones | El último párrafo de §1.1.3 reúne dos ideas distintas: lo que se requiere para resolver el problema y la limitación de los casos didácticos. | **Corregido:** el párrafo se dividió en dos, uno con la necesidad y otro con la limitación. |
| T14 | cumple | Lo excluido está declarado en §1.5.2: gemelo digital en sentido estricto, digitalización automática de planos, evaluación financiera, generalización estadística y validación con presupuestos reales. | Sin cambios. |

**Resultado:** aprobado en revisión, con dos correcciones aplicadas (T6, T13) y cuatro observaciones
respondidas: dos llevadas al tutor académico (T2, T3) y dos que se resuelven en la Sesión R1.4
(T4, T8). Ningún criterio quedó en «no cumple».

## Anexo — Resolución de T4 y T8 en la Sesión R1.4 (2026-09-15)

Se verificaron las referencias del capítulo con la API de Crossref y con búsquedas web; el detalle
por entrada está en `docs/tesis/referencias.md`. Cambios en el capítulo I:

- **Wahab y Wang.** El año registrado es 2021 y el título completo termina en «in construction cost
  estimation». Su resumen no afirma haber documentado diferencias de tiempo y exactitud: indica que
  la cuantificación se hace mayormente de forma manual o en 2D y que el artículo compara ambos
  procedimientos elemento por elemento. **La oración exageraba la fuente y se reescribió.**
- **Pishdad y Onungwa (2024).** Son dos autores, no «et al.». La cita se corrigió y la oración se
  ajustó al resumen: falta de integración entre los modelos BIM‑5D, el seguimiento del avance y los
  sistemas de pago, y falta de estandarización en el uso de los elementos del modelo. Se retiró la
  calificación de «obstáculo principal».
- **Programas de presupuesto.** La documentación de MaPreX e IP‑3 confirma las funciones citadas.
  Ninguna documentación consultada afirma ni niega una comprobación de cantidades contra la
  geometría, así que «no pueden comprobar» y «ninguno de ellos puede» **afirmaban más de lo
  verificable**. Ambas oraciones se reescribieron como «su documentación no describe». El autor pasó
  a ser IP-3 Software. La cita conserva la marca de pendiente porque la función de LuloWin solo se
  confirmó en páginas de terceros.
- **COVENIN.** La parte II corresponde a la norma 2000-2:1999, y la cita pasó a COVENIN (1999).
- **Convención colectiva (T8).** Se localizó la de 2023 (Gaceta Oficial Extraordinaria N.° 6.752),
  pero no su vigencia en fuente oficial. La cita y el formato de documento legal siguen pendientes, y
  el FCAS se mantiene como parámetro del caso de estudio.

Siguen marcadas como pendientes en el capítulo: Miranda Miranda (año de la edición), Tayefeh Hashemi
et al. (afirmación sin contrastar con el texto), Lulo Software, Colegio de Ingenieros de Venezuela
(fecha), COVENIN (título exacto de la edición de 1999) y la convención colectiva. T4 y T8 quedan
**resueltas en lo verificable**. El resto está declarado y no se cita sin marca.

## Anexo — Corrección derivada de la revisión del capítulo II (Sesión R1.7, 2026-09-15)

- **COVENIN (T8).** APA 7 exige que la primera cita de un autor corporativo introduzca su
  abreviatura. La primera cita del trabajo está en la Tabla 1.3, que pasó a «la Comisión Venezolana
  de Normas Industriales (COVENIN, 1999)»; las siguientes, en el capítulo II, usan «COVENIN (1999)».
  La revisión mostró además que la meta R5 rechazaba la forma parentética con corchetes, y se
  corrigió con una prueba nueva ([acta del capítulo II](R1-capitulo-2.md), T8).
