# Acta de revisión — Capítulos II y IV (fase C4 del cierre)

**Fecha:** 2026-09-28 · **Versión revisada:** primera pasada sobre la rama `inc/cierre-C4-red` en
`737ddb7` (sobre `16efe9b`): el capítulo IV en `ffe4552` (`docs(tesis): capitulo iv con dieciseis
entidades y los estados de c3`) y el capítulo II con `referencias.md` en `737ddb7` (`docs(tesis):
capitulo ii alineado con d4 sobre la fuente del fcas`); segunda revisión sobre `inc/cierre-C4` en
`025a39e`, con todas las correcciones de la actualización de la documentación fusionadas ·
**Tutor:** revisión con la [lista de cotejo](../rubrica_tutor.md), previa a la del tutor académico
designado · **Tesista:** autor de los capítulos

La revisión aplica los criterios T1–T14 a los cambios en cuatro archivos:

- `docs/tesis/capitulos/02-marco-teorico.md`;
- `docs/tesis/capitulos/04-desarrollo.md`;
- `docs/tesis/capitulos/README.md`;
- `docs/tesis/referencias.md`.

La primera pasada mide esos cambios frente a `16efe9b` (`git diff 16efe9b..737ddb7 -- docs/tesis/`).
Atiende dos registros del inventario del cierre:

- **INV‑084:** el capítulo IV con dieciséis entidades, los estados de la corrección de la interfaz y
  el orden real del flujo 3a de UC‑01.
- **INV‑078:** el capítulo II, §2.3.2, alineado con la decisión D4 del
  [dossier de G0](../../dossier_g0.md).

Al final, el anexo B responde la observación que la segunda revisión del
[acta R2](R2-capitulo-4.md) remitió al capítulo II.

En la primera pasada, `scripts/meta_redaccion.py` dio 12/12. Su meta R4 ya lee los capítulos I, II y
IV, porque INV‑075 se cerró en la corrección de la interfaz. Además, se hicieron dos pruebas negativas
en memoria, sin modificar el repositorio:

- al quitar la marca de Chacin (2008), R6 falla;
- al quitar la entrada de Dodi Scovino y Salas Caraballo (2019), R5 falla.

Se contrastó también una muestra de 20 afirmaciones nuevas con las fuentes primarias, el código, las
pruebas, el inventario y la integración continua (anexo A, 1 a 20). Diecinueve se confirmaron y una
dio una discrepancia de presentación (T13.4).

**Severidad de las observaciones.**

- *Mayor:* exige corregir el capítulo antes de aprobarlo.
- *Menor:* el tesista la aplica o justifica por qué no la aplica.
- *De proceso:* afecta a otro archivo o a la herramienta, no al texto del capítulo.

## Primera pasada

| Código | Veredicto | Evidencia y observaciones del tutor | Respuesta del tesista |
|---|---|---|---|
| T1 | cumple | Los dos capítulos conservan las secciones de su guion. El capítulo II solo cambia §2.2.4 y §2.3.2. El capítulo IV amplía §4.2, §4.5.1 y §4.6 y actualiza las Tablas 4.9 a 4.11, sin retirar ninguna sección. | — |
| T2 | cumple | Sin cambios en la correspondencia entre preguntas, objetivos y fases. La Tabla 4.1 sigue vigente. | — |
| T3 | cumple | Ningún cambio formula ni reformula objetivos. | — |
| T4 | cumple | §2.3.2 ya no atribuye al Colegio de Ingenieros de Venezuela el cálculo ni la publicación del factor de cada obra. Dice que el Colegio publica factores de referencia y que advierte que son ejemplos (Colegio de Ingenieros de Venezuela, 2018), dentro de la afirmación contrastada de su entrada. La variación del factor se sostiene con dos cálculos publicados, que el tutor contrastó con el texto. En Chacin (2008), el cuadro 2 da del 198 % al 293 %, y sus conclusiones explican que el factor disminuye con la duración de la obra. En Dodi Scovino y Salas Caraballo (2019), pp. 32‑33, los extremos son 78,63 % y 2 386,08 %. Las ampliaciones del capítulo IV no contienen afirmaciones sobre la práctica. | — |
| T5 | cumple | El 600 % se atribuye al caso didáctico en §2.2.4, §2.3.2 y §4.4.1. Ningún caso se presenta como real (R7 en OK). Los dos trabajos de grado se citan como cálculos publicados, no como datos del proyecto. | — |
| T6 | cumple con observaciones | Las cifras de la literatura llevan su cita y coinciden con la fuente. Los nombres de las pruebas, las funciones y las rutas que cita el capítulo IV existen (anexo A). **T6.1 (menor).** Las pruebas citadas en las puestas al día de §4.2, §4.5.1 y §4.6 se escribieron después de la corrida de referencia del capítulo (35950215309, 735 pruebas), así que esa corrida no las contiene. Hay que decir en «Convenciones» que se ejecutan en la corrida [36427904452](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36427904452), del 28/09/2026 (commit `308eca5`, en verde), sin cambiar las cifras de referencia hasta que se registren en `plan_redaccion.md` §5. Además, la oración «sin el extra de aprendizaje automático instalado, el pendiente se declara igual, sin propuestas» debe citar `tests/unit/test_ui_elaborar.py::test_sin_el_extra_el_pendiente_se_declara_sin_propuestas`. | T6.1: aplicada (`525133a`, `3ce6a5d`). Convenciones nombra la corrida 36427904452, su fecha, el commit `308eca5` y el PR #14, y extiende la oración a §4.7.3, que cita `tests/unit/test_recalculo_civil.py`. §4.5.1 cita la prueba pedida. Tras la fusión con la API de escenarios (`95d95c5`), Convenciones precisa además que esa prueba no figura en la corrida 36427904452 y que entra en la corrida con que se cierre la última etapa. |
| T7 | cumple | Los trabajos nuevos no son antecedentes: cada uno sostiene una afirmación concreta de las bases normativas, y el texto dice cuál. | — |
| T8 | cumple | «Chacin (2008)» y «Dodi Scovino y Salas Caraballo (2019)» siguen el formato autor‑año, con «y» para dos autores. La marca va detrás de la cita narrativa, como en Chacón y Cuervo (s.f.). **Recomendación S2.** Conviene dar en el texto la página de los datos puntuales, como recomienda APA 7: el cuadro 2 de Chacin y las pp. 32‑33 de Dodi Scovino y Salas Caraballo. | S2: aplicada (`72e0744`, `3ce6a5d`). Las citas quedan «(p. 77, cuadro 2)» y «(pp. 32‑33)». La p. 77 es la del índice de cuadros de la obra, porque el PDF no imprime números de página. La entrada de `referencias.md` registra que corresponde a la p. 75 del PDF. |
| T9 | cumple | Las dos citas nuevas tienen entrada en `referencias.md`. Cada entrada sigue el esquema de la lista: estado, verificación, afirmación contrastada y lo que falta. Usan además la forma APA de trabajo de grado que ya tienen Rozo‑Martínez y Tumay‑Gamba (2024) y Garnica Patiño (2017). La entrada de la convención colectiva dejó de atribuir el cálculo al Colegio de Ingenieros. | — |
| T10 | cumple con observaciones | Chacin (2008) está «pendiente» y se cita con la marca. Es la aplicación correcta de la convención, porque faltaba el registro del repositorio institucional. **T10.1 (menor).** Ese registro existe: `https://documentos.uru.edu/pdf/2301-08-02127.pdf`. Descargado el 2026‑09‑28, es idéntico byte a byte a `docs/fuentes/Chacin_2008_FCAS_URU.pdf` (SHA‑256 `bdcd6cd1…c5ab2`). Se pide completar la entrada con el repositorio y la URL, y pasarla a «verificada» con la identidad del hash. Hay que retirar también la marca en §2.3.2. Por último, hay que resolver el «Falta». El año es 2008, el de la portada, y la discrepancia con diciembre de 2007 (resumen y aprobación del tutor) queda como nota. La grafía es «Chacin», la del documento en minúsculas (p. 4 y cuadro 2). Si se decide mantenerla como pendiente, el «Falta» debe actualizarse, porque la URL ya no falta. | T10.1: aplicada (`72e0744`). La entrada queda «verificada» con el repositorio institucional de la URU, la URL, el SHA‑256 y el tamaño. El año (2008, con una nota sobre diciembre de 2007) y la grafía («Chacin») tienen campo propio. §2.3.2 cita sin marca. La grafía se unificó también en `dossier_g0.md` y en `docs/fuentes/README.md` (actualización de la documentación). |
| T11 | cumple | Sin primera persona en el texto nuevo (R4 en OK; también comprobado a mano). Se usa el pasado para lo hecho («se agregó», «se implementó», «lo cerraron») y el presente para lo que el sistema hace. | — |
| T12 | cumple | Los cambios no tocan BIM‑5D, la sombra digital ni el gemelo digital (R8 en OK). | — |
| T13 | **no cumple** | **T13.1 (mayor).** El capítulo IV se contradice en pasajes de estado. La fila de resincronización de la Tabla 4.10 basta para el contenido que todavía no se describe: Inicio, la composición separada y los flujos de UC‑04. No basta para oraciones que son falsas bajo la propia convención del capítulo. Esas oraciones asignan en futuro trabajo a etapas que la introducción declara concluidas el 24 y el 28 de septiembre, o afirman en presente lo que la Tabla 4.11 del mismo commit da por cerrado. Son estos lugares: §4.7.3, «tampoco lo están sus flujos alternativos… corresponden a la corrección de los adaptadores», frente a la Tabla 4.11, que dice «implementados en el adaptador civil»; §4.3.4, «esa página calcula…, persiste… y orquesta», frente a INV‑043 cerrado; §4.11.1, «su separación corresponde a la corrección de la interfaz» y UC‑12 «especificado y no implementado: corresponde a la corrección de la interfaz»; §4.1.2 y la Tabla 4.2, con RF‑36 a RF‑43 y UC‑12 «pendiente de implementación»; y las filas de INV‑043 e INV‑073 de la Tabla 4.11, con el desfase en presente junto al estado «cerrado» o «implementados». No hace falta reescribir. En cada lugar basta anclar el tiempo al 23 de septiembre, decir en una oración qué etapa lo implementó y remitir a la Tabla 4.10. Las dos filas de la Tabla 4.11 pasan a pasado, como ya se hizo con INV‑072. <br>**T13.2 (menor).** Cuando se fusione la actualización de la documentación, la API de escenarios declarará los pendientes del presupuesto base (`tests/integration/test_api_escenarios.py::test_los_escenarios_de_un_base_con_pendientes_los_declaran`), y la especificación redactará el flujo 3a en su orden real. Entonces quedarán falsas tres cosas: §4.5.1, las dos últimas filas de la Tabla 4.10 y la fila de INV‑083 de la Tabla 4.11. Hay que actualizarlas tras esa fusión, o fecharlas en pretérito al cierre de la corrección de la interfaz. Por otra parte, atribuir un cambio de la API a «la actualización de la documentación» confunde al lector. Conviene decir «la última etapa del cierre, que incluyó ese cambio de la API». <br>**T13.3 (menor).** «C3.1» y «C3.2» (§4.5.1 y §4.6) reintroducen en el cuerpo códigos internos que la observación T13.1 de R2 había retirado. Se pide un texto de enlace descriptivo: «expediente de la recarga con pendientes» y «expediente del descarte de versiones». <br>**T13.4 (menor).** §4.5.1 describe el comportamiento posterior a la corrección de la interfaz en «la pantalla "Elaborar presupuesto"», cuyo título vigente es «Elaborar un presupuesto» (`ui/app.py:109`). Se pide el nombre vigente o una mención sin comillas, como hace §4.6 con la pantalla de actualización. | T13.1: aplicada (`525133a`). §4.1.2, la Tabla 4.2 (fila UC‑12 y nota), §4.3.4, §4.7.3 y los dos pasajes de §4.11.1 quedan anclados a la versión del 23/09, dicen qué etapa lo implementó después y remiten a la Tabla 4.10. Las filas de INV‑043 e INV‑073 pasan a pretérito. <br>T13.2: aplicada tras fusionar las correcciones de la API y de la especificación (`95d95c5`). §4.5.1 fecha la reescritura de 3a de la especificación y el cambio de la API al 28/09/2026. Para el cambio de la API usa «la última etapa del cierre, que incluyó ese cambio de la API», con `pendientes_base` y su prueba. Se retiraron las dos filas de la Tabla 4.10. La fila de INV‑083 y la nota de la Tabla 4.11 declaran que exceden el corte del 28/09. `97173da` aplicó el mismo patrón a la nota de los contratos (§4.3.2) y a la fila de INV‑057. <br>T13.3: aplicada (`525133a`). <br>T13.4: aplicada (`525133a`). |
| T14 | cumple | La limitación nueva está declarada: el informe de auditoría de cada escenario no incluye los pendientes del base, porque exigiría modificar el núcleo. §4.6 declara también los dos límites del descarte. Nada contradice lo excluido en §1.5.2. | — |

**Resultado de la primera pasada:** **requiere nueva revisión**, acotada a T13.1 y a la respuesta de
las observaciones menores. T13 queda en «no cumple» por la contradicción interna del capítulo IV,
que es la observación mayor T13.1. Hay seis observaciones:

- una mayor: T13.1;
- cinco menores: T6.1, T10.1, T13.2, T13.3 y T13.4.

T13.2 depende de que se fusionen las otras correcciones de la actualización de la documentación. El
capítulo II no tiene observaciones mayores.

**Recomendaciones de la primera pasada (no bloquean la aprobación).**

- **S1.** §2.3.2 puede precisar que Chacin (2008) llama al factor «de prestaciones sociales», su
  denominación anterior, que el propio trabajo rotula «FCAS». Dodi Scovino y Salas Caraballo (2019,
  p. 2) registran la equivalencia: «mejor conocido como el porcentaje de prestaciones sociales».
  *Aplicada (`72e0744`).*
- **S2.** Véase T8. *Aplicada.*
- **S3.** En la próxima revisión del capítulo I conviene tomar la formulación de §2.3.2. En
  `01-el-problema.md:146`, «FCAS derivado de las cláusulas económicas…» es compatible con §2.3.2,
  porque se refiere al concepto y no al valor, pero conviene que diga «cuyo cálculo se apoya en las
  cláusulas…». *Queda para la revisión del capítulo I.*

## Respuesta del tesista

**Fecha:** 2026-09-28 · **Versión corregida:** `525133a`, `72e0744` y `3ce6a5d` (ronda 1), `95d95c5`
(T13.2, tras la fusión) y `97173da` (la nota de los contratos y la fila de INV‑057).

Se aplicaron la observación mayor y las cinco menores, así como las recomendaciones S1 y S2. S3 queda
para el capítulo I. Se pide nueva revisión.

## Segunda revisión

**Fecha:** 2026-09-28 · **Versión revisada:** `inc/cierre-C4` en `025a39e`, con todas las
correcciones de la actualización de la documentación fusionadas · **Tutor:** el mismo revisor de la
primera pasada

Se comprobó cada respuesta en los capítulos, en `referencias.md` y en el código. Además, se
contrastaron con el árbol fusionado todas las afirmaciones en presente del capítulo IV sobre
documentos y código:

- la especificación;
- el modelo de datos;
- la arquitectura;
- `NORMAS.md`, §4 y §5;
- la API;
- la interfaz;
- `plan_redaccion.md` §5.

`meta_redaccion.py` sigue en 12/12: R4 lee tres capítulos, R5 da 74 citas con referencia y R6 queda
en OK sin la marca de Chacin. La corrida 36427904452 tiene conclusión `success` sobre `308eca5`.

### Comprobación de las respuestas

| Obs. | Respuesta | Comprobación del tutor | Dictamen |
|---|---|---|---|
| T6.1 | aplicada | Convenciones nombra la corrida, su commit y su PR. `test_sin_el_extra_el_pendiente_se_declara_sin_propuestas` existe (`tests/unit/test_ui_elaborar.py:378`), y la precisión sobre la prueba de la API es cierta. | aceptada; véase T6.2 |
| T10.1 | aplicada | La entrada tiene la URL, el hash, el tamaño, el año y la grafía. §2.3.2 cita sin marca y R6 sigue en OK. `dossier_g0.md` y `docs/fuentes/README.md` escriben «Chacin». | aceptada |
| T13.1 | aplicada | Los cinco lugares y las dos filas quedan anclados. El texto nuevo se comprobó en el código: `ui/composicion.py` llama a `calcular_apu`; `ui/elaboracion.py` contiene `elaborar_desde_catalogo` y `guardar_composicion`; y existe `tests/unit/test_recalculo_civil.py`. Ya no queda en el capítulo ninguna etapa concluida con trabajo en futuro. | aceptada |
| T13.2 | aplicada | La especificación redacta 3a en el orden real (`docs/ERS.md:147-150`). `pendientes_base` está en `api/esquemas.py:286` y `api/rutas/presupuestos.py:299`, y la prueba en `tests/integration/test_api_escenarios.py:105`. Se retiraron las filas de la Tabla 4.10 y la nota de la Tabla 4.11 declara sus dos excepciones. | aceptada; véase T13.5 |
| T13.3 | aplicada | El cuerpo no tiene códigos de etapa ni de registro fuera de la Tabla 4.11. | aceptada |
| T13.4 | aplicada | §4.5.1 dice «Elaborar un presupuesto». Las Tablas 4.2 y 4.9 conservan el nombre del 23/09, y eso es coherente con sus notas. | aceptada |
| S1, S2 | aplicadas | §2.3.2 recoge la denominación anterior. La p. 77 coincide con el índice de cuadros de Chacin (p. 9 del PDF). La cita de la p. 2 de Dodi Scovino y Salas Caraballo es literal. | aceptadas |

### Observaciones nuevas (derivadas de la fusión)

| Código | Veredicto | Observación del tutor | Respuesta del tesista |
|---|---|---|---|
| T6.2 | menor | La enmienda de `plan_redaccion.md` §5 de esta fase cambió dos filas a los valores del 28/09. «Suite y cobertura» pasó de 735 a 926 pruebas y a la corrida 36427904452. «Interfaz y API en `main`» pasó de nueve a diez pantallas, en `ceb6b8e`. El capítulo IV sigue citando 735 pruebas (Convenciones) y nueve pantallas (§4.11.1), como exige su corte del 23/09, y esas cifras ya no están en §5. La propia regla de §5 manda buscar los usos en los capítulos. Además, la oración de T6.1 («las cifras de referencia cambian cuando se registren en la tabla») quedó disparada sin que el capítulo cambiara. **Corrección:** las dos filas de §5 conservan el valor del 23/09 como referencia del capítulo IV, como ya hace la fila de las pruebas de arquitectura («66 en la verificación de GC1»). En Convenciones, la oración pasa a «las cifras de referencia del capítulo cambian al resincronizarlo (Tabla 4.10)». | Aplicada (`0f77206`). `plan_redaccion.md` §5 conserva el valor del 23/09 como referencia del capítulo IV, con el patrón de la fila de arquitectura. «Suite y cobertura» agrega «735 pruebas y 98 % en la corrida 35950215309 (2026‑09‑23), referencia del capítulo IV hasta su resincronización». «Interfaz y API en `main`» agrega «nueve pantallas en `f1dda36` (2026‑09‑23), referencia del capítulo IV». Se comprobó que `ui/app.py` define nueve entradas en `PAGINAS` en `f1dda36` y diez en `ceb6b8e`. En Convenciones, la oración pasa a «las cifras de referencia del capítulo cambian al resincronizarlo (Tabla 4.10)». La búsqueda de usos en los capítulos solo encuentra esas dos cifras, en Convenciones y en §4.11.1. |
| T13.5 | menor | El capítulo fecha tres cambios de la cuarta etapa: la API de escenarios, 3a en la especificación y la modalidad de mano de obra en `NORMAS.md` §5 y en la arquitectura. Sin embargo, la introducción y la tabla de estado hablan de dos. Además, esa misma etapa corrigió el 28/09 desfases que el capítulo sigue describiendo en presente y sin fecha. Son la nota de la Tabla 4.2 (§3.1 de la especificación), §4.1.4 (IFC, RF‑19, la matriz y la cabecera), §4.2 (el modelo «se declara aprobado»), §4.3.4 (G1, las dos copias del evaluador y `componer.py`), §4.4.1 (`NORMAS.md` §4 sin destajo) y §4.7.2. A estos pasajes se suman las filas de figuras y de resincronización de la Tabla 4.10 y las filas de INV‑026, 028, 029, 030, 058, 061, 063 y 074 de la Tabla 4.11. Con una lectura estricta del corte del 23/09, esos pasajes están anclados y no se contradicen. Por eso la observación es menor. Pero el fechado selectivo hace que se lean como actuales. Además, dos de esos pasajes no admiten la lectura estricta: «todavía dan» (§4.7.2) y la mezcla de presente y pretérito en la nota de la Tabla 4.2. §4.4.1 es el caso más visible: el lector acaba de leer en §4.3.2 que `NORMAS.md` se actualizó el 28/09. **Corrección:** (1) Convenciones: «tres cambios» en §4.3.2 y §4.5.1, más una oración que diga que la cuarta etapa corrigió además, ese día, los desfases documentales de §4.1.1, §4.1.4, §4.2, §4.3.4, §4.4.1 y §4.7.2, y que esas secciones los describen como estaban el 23/09. La tabla de estado se ajusta igual. (2) «todavía dan» pasa a «daban en esa versión», y «declara» (nota de la Tabla 4.2) a «declaraba en esa versión». (3) §4.4.1 y la fila de INV‑074 siguen el patrón de INV‑057: pretérito con la fecha, y la fila entra entre las excepciones de la nota de la Tabla 4.11. (4) Tabla 4.10: «cambiará otros puntos» pasa a «corrigió además…», y la fila de figuras pasa a «tenían desfases registrados, corregidos en la última etapa del cierre». | Aplicada (`0f77206`). (1) Convenciones: «De la cuarta, todavía en curso, el capítulo recoge tres cambios del 28 de septiembre», con la API de escenarios y 3a de UC‑01 (sección 4.5.1) y la modalidad de mano de obra en `NORMAS.md` y la arquitectura (sección 4.3.2). Sigue la oración de que esa etapa corrigió además, el mismo día, los desfases documentales de §4.1.1, §4.1.4, §4.2, §4.3.4, §4.4.1 y §4.7.2, que esas secciones describen como estaban el 23 de septiembre. La tabla de estado dice «tres cambios… en las secciones 4.3.2 y 4.5.1». (2) §4.7.2: «todavía dan» pasa a «daban en esa versión, la del 23 de septiembre». Nota de la Tabla 4.2: «declara» pasa a «declaraba en esa versión, la del 23 de septiembre», con «ofrecía». Se nombra la fecha junto a «esa versión» porque en los dos pasajes el demostrativo no tenía antecedente. (3) §4.4.1 pasa a pretérito anclado al 23/09 y termina con «la última etapa del cierre incorporó la fórmula con destajo a NORMAS.md §4 el 28 de septiembre de 2026». La fila de INV‑074 queda en pretérito con la fecha, y la nota de la Tabla 4.11 la exceptúa junto a INV‑057 e INV‑083. (4) Tabla 4.10: en la fila de resincronización, «cambiará otros puntos» pasa a «corrigió además los desfases documentales de las secciones citadas en las convenciones». En la de figuras, «tienen desfases registrados… generarlos ahora» pasa a «tenían desfases registrados (Tabla 4.11), corregidos en la última etapa del cierre; las figuras se generan de su versión corregida». Se comprobó en el árbol que las correcciones son del 28/09: `NORMAS.md` §4 con destajo (`2da8296`), §3.1 de la especificación (`b3c47dc`), G1 en la especificación (`1cf355a`), su cabecera (`9ecbd1b`), `modelo_datos.md` pendiente de G0 (`812c0e4`) y la arquitectura con G1 cruzada con salvedad, cinco copias del evaluador y `componer.py` que «pinta y confirma» (`540ff4e`). `docs/tesis/figuras/` sigue sin existir. |

### Dictamen

| Código | Veredicto | Fundamento |
|---|---|---|
| T1 | cumple | Las secciones del guion siguen completas. Las figuras siguen siendo condición para la versión final (acta R2, T1.2). |
| T2 | cumple | Sin cambios. |
| T3 | cumple | Sin cambios. |
| T4 | cumple | §2.3.2 formula el FCAS como D4 y sostiene la variación con dos cálculos publicados, contrastados. |
| T5 | cumple | El 600 % es del caso didáctico, y ningún caso se presenta como real. |
| T6 | cumple con observaciones | Las cifras de la literatura llevan su cita y su página. Las pruebas citadas existen y su corrida está declarada. Queda T6.2 (menor). |
| T7 | cumple | Cada trabajo nuevo sostiene una afirmación concreta. |
| T8 | cumple | Formato autor‑año, con localizador en los datos puntuales. |
| T9 | cumple | Toda cita nueva tiene su entrada. |
| T10 | cumple | Chacin (2008) queda verificada contra el repositorio institucional. No se cita ninguna referencia pendiente sin marca. |
| T11 | cumple | Voz impersonal (R4 en OK y comprobación manual). |
| T12 | cumple | Sin cambios de terminología. |
| T13 | cumple con observaciones | T13.1 a T13.4 están resueltas y el capítulo ya no se contradice. Queda T13.5 (menor), que completa el fechado de la cuarta etapa. |
| T14 | cumple | Las limitaciones nuevas están declaradas. |

**Resultado de la segunda revisión:** ningún criterio está en «no cumple». Las seis observaciones de
la primera pasada están aplicadas y aceptadas, y lo mismo S1 y S2. Quedan dos observaciones menores
nuevas, T6.2 y T13.5, que surgieron al fusionar la actualización de la documentación y ya llevan el
texto de su corrección.

Según la rúbrica, los capítulos II y IV quedan **aprobados en revisión** cuando T6.2 y T13.5 tengan
respuesta del tesista. No se requiere una tercera revisión completa: basta que el tutor compruebe
esas dos respuestas.

Siguen abiertas, sin impedir esta aprobación, varias cosas:

- las figuras y las tres referencias pendientes del capítulo IV, que son condición para la versión
  final (acta R2);
- la resincronización con `v1.0-tesis` (Tabla 4.10);
- la recomendación S3, para el capítulo I;
- todas las decisiones del tutor académico: G0, D1–D9 y AACE. D4, en particular, se somete al tutor
  en §2.3.2 y en §4.4.1.

La corrección que el inventario propone para INV‑078 y para INV‑084 queda cumplida, salvo T6.2 y
T13.5 en INV‑084. Su cierre lo registra la compuerta de la actualización de la documentación. Esta
aprobación no sustituye la del tutor académico designado.

## Respuesta del tesista a la segunda revisión

**Fecha:** 2026-09-28 · **Versión corregida:** `0f77206` (`docs(tesis): capitulo iv fechado frente a lo
corregido en c4`)

Se aplicaron las dos observaciones menores nuevas, T6.2 y T13.5, con el texto de corrección que
proponía el tutor. Cada afirmación nueva del capítulo IV se contrastó con el repositorio. El
capítulo II no cambia en esta respuesta. `scripts/meta_redaccion.py` da 12/12 y
`scripts/meta_datos.py` da 3/3 sobre `0f77206`.

## Resultado

Ningún criterio está en «no cumple», y cada observación de las dos revisiones tiene respuesta del
tesista (T6.2 y T13.5 en `0f77206`).

**Resultado:** **aprobado en revisión** (capítulos II y IV).

Esta aprobación no sustituye la del tutor académico designado. Siguen abiertos, sin impedirla, los
puntos que enumera el dictamen de la segunda revisión.

**Nota posterior a la aprobación (2026‑09‑28, compuerta GC4).** `b0d3ef1` (`docs(tesis): capitulo iv
declara la segunda excepcion de rnf-08 (INV-077)`) cambió el capítulo IV después de este «aprobado en
revisión» (`1b6a73c`): agrega 4.1.3 a la lista de las Convenciones, declara la segunda excepción de
RNF‑08 (three.js) en la fila de la Tabla 4.3 y en su nota y en §4.10.1, y agrega la fila de INV‑077
a la Tabla 4.11 y a su nota. Es la discrepancia D‑7 de la lista de cotejo de GC4. Sigue el mismo
patrón de fechado que esta revisión aceptó para §4.4.1 e INV‑074, y lo comprobó el encargo de
requisitos de GC4. No reabre la aprobación.

## Anexo A — Muestra de afirmaciones contrastadas

Primera pasada (1 a 20) y segunda revisión (21 a 34).

| # | Afirmación | Comprobación | Resultado |
|---|---|---|---|
| 1 | Chacin: 198 % a 293 %; disminuye con la duración por los costos fijos (§2.3.2) | `docs/fuentes/Chacin_2008_FCAS_URU.pdf`, cuadro 2 (p. 75 del PDF), pp. 76 y 78 | confirmada |
| 2 | Chacin: convenciones 2003‑2006 y 2007‑2009; obras de 3, 6 y 12 meses | título, cuadro 2 | confirmada |
| 3 | Dodi Scovino y Salas Caraballo: 78,63 % (montos fijos) y 2 386,08 % (todas las cláusulas); convención 2016‑2018 y costos de 2018 | pp. 32‑33 impresas; objetivos («para el año 2018») | confirmada |
| 4 | Dodi Scovino: el archivo de la URL es idéntico a la copia archivada | el tutor lo descargó de riujap.ujap.edu.ve; SHA‑256 `2cb1909c…28ee` en ambos | confirmada |
| 5 | Chacin: registro del repositorio no localizado | `documentos.uru.edu/pdf/2301-08-02127.pdf`, idéntico (SHA‑256 `bdcd6cd1…c5ab2`) | superada (T10.1) |
| 6 | El CIV publica factores de referencia y advierte que son ejemplos (§2.3.2) | `referencias.md`, entrada del CIV (2018), afirmación contrastada | confirmada |
| 7 | Dieciséis entidades, con `DescarteVersion` (§4.2) | `core/models/entidades.py`: 16 clases `(Base)`, `DescarteVersion` en :303 | confirmada |
| 8 | La tabla `descarte_version` es aditiva y no exige migrar | `tests/integration/test_persistencia.py:640` | confirmada |
| 9 | La interfaz y la API piden solo las composiciones que existen | `api/rutas/presupuestos.py:84-93`; `ui/elaboracion.py:84-103` | confirmada |
| 10 | Un solo emparejamiento de propuestas en la interfaz y la API | `ml/normalization/normalizador.py:194`; `ui/elaboracion.py:185`; `api/rutas/presupuestos.py:343` | confirmada |
| 11 | La especificación redacta el orden inverso | `docs/ERS.md:139-140` (en `737ddb7`) | confirmada; superada por la corrección de la especificación (28) |
| 12 | Las pruebas de UC‑01 3a en la interfaz y la API | `tests/unit/test_ui_elaborar.py:138,157`; `tests/integration/test_api.py:356` | confirmada |
| 13 | La recarga devuelve el informe emitido; límite para presupuestos anteriores | `core/budget/persistencia.py:188-209`; `tests/integration/test_recarga_con_pendientes.py:177` | confirmada |
| 14 | La API usa `cargar_elaboracion` para el informe y el libro | `api/rutas/presupuestos.py:430-435` | confirmada |
| 15 | Revalorar arrastra los pendientes | `core/budget/actualizacion.py:133-134`; `tests/integration/test_recarga_con_pendientes.py:240` | confirmada |
| 16 | La pantalla de escenarios carga el base con sus pendientes | `ui/paginas/escenarios.py:98`; `tests/unit/test_ui_escenarios.py:78` | confirmada |
| 17 | Descarte: la última versión, una sola vez, nunca la primera; límite de la versión de origen; botón «Descartar version» | `core/budget/actualizacion.py:182-213`; `ui/paginas/actualizacion.py:321`; cuatro pruebas en `tests/integration/test_actualizacion_precios.py:724-763` | confirmada |
| 18 | Ninguna pantalla ni operación de la API muestra la marca | búsqueda de `DescarteVersion` en `ui/` y `api/`: sin resultados | confirmada |
| 19 | Las etapas concluyeron el 23, el 24 y el 28 de septiembre | `docs/bitacora/2026-09-23-cierre.md:250,503,937` | confirmada |
| 20 | Pantalla «Elaborar presupuesto» en la versión descrita en §4.5.1 | `ui/app.py:109`: «Elaborar un presupuesto» | **discrepancia** (T13.4); corregida |
| 21 | Chacin, p. 77, cuadro 2 (§2.3.2) | índice de cuadros, p. 9 del PDF: «Cuadro No. 2 … 77» | confirmada |
| 22 | Dodi Scovino y Salas Caraballo, p. 2: «mejor conocido como el porcentaje de prestaciones sociales» | PDF, p. 8 del archivo, con el número impreso 2 | confirmada |
| 23 | Corrida 36427904452, del 28/09, commit `308eca5`, en verde | `gh run view`: `success`, `headSha` `308eca5…` | confirmada |
| 24 | La prueba del pendiente sin el extra de aprendizaje automático | `tests/unit/test_ui_elaborar.py:378` | confirmada |
| 25 | El cálculo pasó a `ui/composicion.py`; la persistencia y la orquestación, a `ui/elaboracion.py` (§4.3.4) | `ui/composicion.py:43,57`; `ui/elaboracion.py`: `elaborar_desde_catalogo`, `guardar_composicion` | confirmada |
| 26 | Los flujos alternativos de UC‑04 se implementaron en `adapters/civil/recalculo.py` (§4.7.3) | archivo y `tests/unit/test_recalculo_civil.py`; bitácora del cierre :263-264, :396 | confirmada |
| 27 | La API de escenarios lista los pendientes en `pendientes_base` (§4.5.1) | `api/esquemas.py:286`; `api/rutas/presupuestos.py:299`; `tests/integration/test_api_escenarios.py:105` | confirmada |
| 28 | Desde el 28/09 la especificación redacta 3a en el orden real (§4.5.1) | `docs/ERS.md:147-150` | confirmada |
| 29 | `NORMAS.md` §5 y la arquitectura §2.1 muestran `ModalidadManoObra` (nota de §4.3.2) | `NORMAS.md:148`; `docs/arquitectura.md` | confirmada |
| 30 | La especificación declara en §3.1 que la interfaz ofrece los once casos de uso (nota de la Tabla 4.2, en presente) | `docs/ERS.md:443-458`: §3.1 declara la capa de cada UC | **desfasada tras la fusión** (T13.5) |
| 31 | La especificación y la arquitectura «todavía» dan la extracción IFC por pendiente (§4.7.2) | ERS :426-428 y RF‑04; arquitectura :866, :1236: G1 cruzada con salvedad | **desfasada tras la fusión** (T13.5) |
| 32 | `NORMAS.md` §4 no tiene la línea de destajo (§4.4.1) | `NORMAS.md:97-100` | **desfasada tras la fusión** (T13.5) |
| 33 | El modelo de datos «se declara aprobado» (§4.2); la arquitectura declara dos copias del evaluador (§4.3.4) | `docs/modelo_datos.md:3` (pendiente de G0); `docs/arquitectura.md:1314,1328` (cinco copias) | **desfasadas tras la fusión** (T13.5) |
| 34 | 735 pruebas y nueve pantallas coinciden con la tabla de cifras citables | `plan_redaccion.md` §5: 926 pruebas y diez pantallas (28/09) | **discrepancia** (T6.2) |

Además, en la primera pasada se comprobó lo siguiente:

- las 27 filas de la Tabla 4.11 coinciden con el estado del inventario;
- existe `adapters/civil/recalculo.py`;
- siguen existiendo cinco copias del evaluador.

En la segunda revisión se comprobó que la búsqueda de futuros asignados a etapas concluidas («corresponde a», «se implementará», «pendiente de implementación») ya no da resultados en el capítulo IV.

## Anexo B — Respuesta a la observación remitida por R2 al capítulo II

La segunda revisión del [acta R2](R2-capitulo-4.md), en su «Observación remitida al capítulo II»,
señaló tres puntos del capítulo II. Esa observación recoge la respuesta a su T4.1 y quedó registrada
como INV‑078. Se responde aquí porque el [acta del capítulo II](R1-capitulo-2.md) es anterior a esa
observación.

1. **«Quien lo calcula y lo publica es el Colegio de Ingenieros de Venezuela».** Resuelto. §2.3.2
   dice ahora que el factor no tiene un valor normativo publicado y que el Colegio no calcula ni
   publica el de cada obra. Según §2.3.2, el Colegio publica factores de referencia en sus guías y
   advierte dos cosas: que son ejemplos de los valores probables y que cada empresa debe calcular el
   suyo (Colegio de Ingenieros de Venezuela, 2018). Es la formulación de §4.4.1 y la de D4 en el
   [dossier de G0](../../dossier_g0.md). La entrada de la convención colectiva en `referencias.md` se
   corrigió en el mismo sentido.
2. **Citar los rangos publicados que pide el enunciado de D4.** Resuelto. §2.3.2 cita dos trabajos.
   Chacin (2008, p. 77, cuadro 2) da valores entre el 198 % y el 293 % según la convención y la
   duración de la obra. Chacin lo llama factor de prestaciones sociales, su denominación anterior.
   Dodi Scovino y Salas Caraballo (2019, pp. 32‑33) dan valores entre el 78,63 % y el 2 386,08 %
   según las cláusulas incluidas. Son los rangos del paquete para el tutor (198–293 % y 78–2 386 %),
   con la precisión de la fuente. El tutor los contrastó con el texto de ambos trabajos (anexo A, 1 a
   3, 21 y 22).
3. **Entradas en `referencias.md`.** Resuelto. Las dos entradas están **verificadas**. Dodi Scovino y
   Salas Caraballo (2019) lo está porque el archivo de su repositorio es idéntico a la copia
   archivada. Chacin (2008) lo está porque el registro del repositorio institucional de la URU es
   idéntico byte a byte a la copia archivada (T10.1). El año y la grafía quedaron resueltos en la
   entrada, y §2.3.2 la cita sin marca.

Con esto, el capítulo II deja de tratar el FCAS como un dato cuya fuente normativa «falta confirmar»
(§2.2.4). Lo trata como un parámetro del caso de estudio, explícito y modificable, que es la
recomendación de D4. La decisión sigue siendo del tutor académico, y §2.3.2 lo declara: «Avalar esa
declaración es una decisión que se somete al tutor académico». La corrección que el inventario
propone para INV‑078 queda cumplida. Su cierre lo registra la compuerta de la actualización de la
documentación.
