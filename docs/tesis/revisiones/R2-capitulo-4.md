# Acta de revisión — Capítulo IV (fase Red del cierre)

**Fecha:** 2026-09-23 · **Versión revisada:** rama `inc/tesis-cap4` en `49ecde1`; el capítulo entra en
`e3897c0` (`docs(tesis): capitulo iv desarrollo de la propuesta`) y los cambios del guion y de las
cifras en `8db0682` (`docs(tesis): guion y cifras vigentes del plan de redaccion y tablero`) ·
**Tutor:** revisión con la [lista de cotejo](../rubrica_tutor.md), previa a la del tutor académico
designado · **Tesista:** autor del capítulo

La revisión aplica los criterios T1–T14 al archivo `docs/tesis/capitulos/04-desarrollo.md` y a los
cambios de `docs/tesis/plan_redaccion.md` y `docs/tesis/capitulos/README.md` frente a `main`
(`git diff main -- docs/tesis/`). El guion de referencia es el del
[esqueleto](../esqueleto_tesis.md) §1 y §2 y el de [plan_redaccion.md](../plan_redaccion.md) §2,
capítulo IV. Los criterios T1 y T7 se leen para este capítulo con su guion propio (no tiene
antecedentes ni objetivos que formular).

`scripts/meta_redaccion.py` dio 12/12 sobre esta versión, pero **no cubre el capítulo IV**: sus
metas R4–R8 leen solo `01-el-problema.md` y `02-marco-teorico.md` («voz impersonal en 2
capítulo(s)»). Por eso T5 y T8–T12 se verificaron a mano con búsquedas sobre el texto. Además, se
comprobó una muestra de 22 afirmaciones del capítulo contra el repositorio, la corrida de CI y las
bitácoras (anexo); 20 se confirmaron y dos dieron discrepancias que se recogen en T6.

**Severidad de las observaciones.** *Mayor*: exige corregir el capítulo antes de aprobarlo.
*Menor*: el tesista la aplica o justifica por qué no. *De proceso*: afecta a otro archivo o a la
herramienta, no al texto del capítulo.

| Código | Veredicto | Evidencia y observaciones del tutor | Respuesta del tesista |
|---|---|---|---|
| T1 | cumple con observaciones | Están las once secciones del guion de `plan_redaccion.md` (requerimientos, modelo de datos, arquitectura, motor, presupuesto y curva, UC‑02, adaptador civil, verificación, extensibilidad, ML, interfaz y API) y las nueve áreas del esqueleto §1, con la tabla de estado y la síntesis. **T1.1 (menor).** §4.3.1 dice que la arquitectura «se documentó con las vistas 4+1», pero el capítulo no recorre las vistas; solo §4.3.4 trata el proceso y el despliegue. Falta un párrafo que presente las cinco vistas (lógica, desarrollo, proceso, física y escenarios) y remita al anexo C, sin esperar a las figuras. **T1.2 (menor).** El capítulo no tiene figuras (Tabla 4.9). Se acepta en borrador porque la causa está registrada, pero la versión final no se aprueba sin al menos el diagrama de componentes y el entidad‑relación que exige el guion de figuras (`plan_redaccion.md` §1). | T1.1: aplicada. §4.3.1 abre con un párrafo que presenta las cinco vistas (escenarios, lógica, proceso, desarrollo y física), dice qué muestra cada una y remite al anexo C; §4.3.2–§4.3.4 se anuncian como su resumen. <br>T1.2: no aplicada en esta versión; aceptada para la final. Los diagramas de origen tienen desfases abiertos (INV‑029, INV‑057, INV‑058, INV‑061, INV‑070) que se corrigen en C4, y generarlos ahora llevaría esos errores a la tesis. La Tabla 4.10 (antes 4.9) dice ahora que la versión final no se aprueba sin el diagrama de componentes y el entidad‑relación. |
| T2 | cumple con observaciones | Las secciones responden de forma explícita las preguntas secundarias 1 (§4.7.2), 2 (§4.7.1), 3 (§4.10.3) y 4 (§4.8.2), con la misma numeración del capítulo I, y remiten la 5 al capítulo V. **T2.1 (menor).** El capítulo no nombra los objetivos OE1 a OE5 ni las fases de las Bases §8.2, aunque la matriz del esqueleto §2 le asigna OE1 (fixture de la línea base), OE2, OE3, OE4 y OE5, además del objetivo transversal. Conviene una tabla o un párrafo en la introducción que relacione cada sección con su objetivo, su fase y su producto: §4.2, §4.4 y §4.5 con OE3 (fase III); §4.7 con OE2 (fase II); §4.8 con OE5 (fase V); §4.10 con OE4 (fase IV); §4.4.2 con OE1. **T2.2 (menor).** El capítulo I formula una sexta pregunta secundaria para la variante A. §4.9 no la menciona. Debe decir que, si se elige la variante A (D3), esa sección aporta la evidencia de la pregunta 6. | T2.1: aplicada. La introducción tiene la subsección «Correspondencia con los objetivos» con la Tabla 4.1 (sección → objetivo → fase → producto), con la asignación del tutor y la del esqueleto §2; §4.4.2 nombra la línea base como producto del diagnóstico (OE1). Las tablas se renumeraron 4.1–4.11. <br>T2.2: aplicada. §4.9.2 dice que, en la variante A, la sección aporta la evidencia de la sexta pregunta secundaria del capítulo I y, en la B, un resultado complementario. |
| T3 | cumple | El capítulo no formula objetivos y no reformula ni contradice los del capítulo I. OE7 aparece solo como opción de la decisión D3, pendiente (§4.9.2 y Tabla 4.9). | |
| T4 | **no cumple** | **T4.1 (mayor).** §4.4.1 afirma que el FCAS no es un valor normativo «porque ninguna fuente venezolana lo publica». Eso contradice el capítulo II, §2.3.2: «Quien lo calcula y lo publica es el Colegio de Ingenieros de Venezuela». También contradice el enunciado de D4, que habla de la falta de cita **normativa** y cita los rangos publicados. Se debe reformular así: el valor de 600 % no tiene fuente normativa; el Colegio de Ingenieros publica factores de referencia; y la oración debe llevar su cita y remitir a §2.3.2. **T4.2 (mayor).** §4.6 justifica el orden de los incrementos con una afirmación sobre la práctica que no tiene cita: la actualización de precios es el caso de uso «que más se repite» «en la práctica presupuestaria». Hay que citar una fuente o presentarla como decisión de planificación del proyecto, sin afirmar la frecuencia. **T4.3 (menor).** §4.8.2 cierra con que la regla que produjo la cantidad es «un dato que un programa de presupuesto convencional no conserva». El capítulo I (§1.1) se limita a decir que la documentación funcional de esos programas no describe esa comprobación, y lo apoya en fuentes todavía pendientes. Hay que usar la misma formulación prudente y la misma cita. | T4.1: aplicada (§4.4.1). Nueva redacción: el 600 % proviene del caso didáctico y no tiene fuente normativa; la convención no define el factor; el Colegio de Ingenieros publica factores de referencia en sus guías y advierte que cada empresa calcule el suyo (Colegio de Ingenieros de Venezuela, 2018), con remisión a §2.3.2 y a D4. **Observación para el capítulo II, no corregida aquí:** §2.3.2 dice «Quien lo calcula y lo publica es el Colegio de Ingenieros de Venezuela», mientras que la actualización de D4 en `docs/dossier_g0.md` dice que el FCAS del 600 % no lo publica el CIV, y cita como valores publicados solo los rangos de Chacín (2008) y de Dodi Scovino y Salas Caraballo (2019), que el capítulo II no cita. La fuente que sostiene §2.3.2 (Colegio de Ingenieros de Venezuela, 2018) habla de factores referenciales de sus guías, no de un factor normativo. Conviene precisar «publica factores de referencia» y decidir si se citan los dos rangos, como pide D4. <br>T4.2: aplicada (§4.6). Se retiró la afirmación de frecuencia: el orden queda como decisión de planificación del proyecto, justificada porque el caso de uso ejercita el versionado y produce el historial que alimenta al módulo predictivo. No se encontró en el repositorio una fuente que sostenga la frecuencia. <br>T4.3: aplicada (§4.8.2). Usa la formulación del capítulo I (la documentación funcional de esos programas no describe esa comprobación), con la misma cita y la marca «[verificación pendiente]» por Lulo Software (s.f.). |
| T5 | cumple | La introducción declara que todos los APU y presupuestos son ejercicios académicos ficticios o casos construidos. Las notas de las Tablas 4.4 y 4.7 lo repiten caso por caso: la clínica, ARENAZA, `MNT-001` y `SIS-001`. Ningún pasaje presenta un caso como obra ejecutada. No hereda la expresión «el caso real» que aún conserva la ERS (criterio de RF‑07). MaPreX figura como referencia de precios publicada, que es lo que declara `NORMAS.md` §1. Se verificó a mano, porque la meta R7 no lee este capítulo (T11.1). | |
| T6 | cumple con observaciones | Las cifras de pruebas y cobertura citan su corrida, la [35950215309](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/35950215309). El revisor la consultó con `gh run view`: 735 aprobadas en Linux y en Windows, y un TOTAL del 98 % sobre `core/`. Las demás cifras coinciden con la tabla de `plan_redaccion.md` §5 y llevan su comando o su prueba (anexo). **T6.1 (menor).** §4.6 dice en presente que el recálculo de 100 partidas «tarda 1,17 s». Es una medición del 31/08/2026 ([bitácora F.2](../../bitacora/2026-08-31-F2-plan-pruebas.md)), anterior a C1, fase que cambió `elaborar`. El revisor la repitió el 23/09 con `uv run python scripts/medir_rnf03.py` en otra máquina y obtuvo 1,34 s; la meta de 5 s se sigue cumpliendo. Se debe fechar la medición y decir que depende del equipo, o volver a medir al congelar. **T6.2 (mayor).** §4.4.1 presenta la fórmula como si su «fuente única» fuera `NORMAS.md` §4, pero las líneas `mano_obra_destajo` y `bono × Σ obreros` (solo los obreros a jornal) no están allí: `NORMAS.md` §4 tiene solo la fórmula de jornal, con «bono × Σ cantidad». La fórmula que transcribe el capítulo es la del docstring de `core/costing/motor.py`, que el revisor confirmó. Hay que atribuirla al motor y a la [bitácora P0.1](../../bitacora/2026-09-16-P0-hallazgo-destajo.md), o registrar el desfase de `NORMAS.md` §4 en el inventario como se hizo con INV‑057 y señalarlo en la nota. El punto 4 del guion de `plan_redaccion.md` arrastra la misma atribución. **T6.3 (de proceso).** En `plan_redaccion.md` §5, el nuevo encabezado dice «Valores medidos el 31/08/2026 salvo que la fila indique otra fecha». Las filas nuevas no llevan fecha, así que quedan fechadas el 31/08 sin serlo: once UC y 42 RF incluyen UC‑12 y RF‑36 a RF‑43 de la Sesión U0.1; las nueve pantallas y las 18 rutas son de septiembre. Hay que poner la fecha en cada fila nueva. La fila «Presupuestos multidominio» nombra archivos pero no el comando (`uv run pytest tests/integration/test_presupuesto_arenaza.py …`). **T6.4 (menor).** §4.4.2 habla de «las cinco pruebas restantes», pero son cinco casos de una sola prueba parametrizada (`test_precio_unitario_reproduce_la_linea_base`). Debe decir «casos», como la tabla §5 («7 casos»). | T6.1: aplicada (§4.6 y fila «Recálculo masivo» de `plan_redaccion.md` §5): 1,17 s el 31/08/2026 en el equipo de desarrollo y 1,34 s en la repetición del 23/09/2026 en otro equipo, con cita a esta acta; se dice que la cifra depende del equipo y que se vuelve a medir al congelar. <br>T6.2: aplicada (§4.4.1, y Tabla 4.11). La fórmula se atribuye al docstring de `core/costing/motor.py` (líneas 3 a 13) y a la decisión D9, con la bitácora del hallazgo del destajo; el texto explica que `NORMAS.md` §4 solo tiene la parte de jornal y que ambas coinciden cuando no hay destajo. El desfase se registró como INV‑074 (C4) y el punto 4 del guion de `plan_redaccion.md` se corrigió. <br>T6.3: aplicada en `plan_redaccion.md` §5: cada fila nueva lleva su fecha o su corrida de CI, y la de presupuestos multidominio lleva el comando `uv run pytest tests/integration/test_presupuesto_arenaza.py …`. Al hacerlo se corrigió también «18 rutas» por «18 operaciones sobre 14 rutas» (anexo, afirmación 22), en el capítulo y en la tabla. <br>T6.4: aplicada (§4.4.2): «siete casos» y «cinco casos … de una misma prueba parametrizada, `test_precio_unitario_reproduce_la_linea_base`». |
| T7 | cumple | El capítulo no tiene antecedentes. Cada obra citada dice qué aporta a la decisión que sostiene: la similitud del coseno y la destilación multilingüe, al normalizador (Reimers y Gurevych, 2019 y 2020); el bosque de aislamiento, al detector (Liu et al., 2008); XGBoost, los bosques aleatorios y el razonamiento basado en casos, a la tabla de degradación de G2 (Chen y Guestrin, 2016; Breiman, 2001; Aamodt y Plaza, 1994); y AACE International (2012, 2020), al rango del contraste. | |
| T8 | cumple | Las citas usan el formato autor‑año: «y» con dos autores, «et al.» con tres o más (Liu et al., 2008) y «s.f.» en DataLaing. La 18R‑97 y la 56R‑08 se distinguen por año (2020 y 2012), igual que en `referencias.md` tras el anexo del acta del capítulo II. | |
| T9 | cumple con observaciones | Las ocho obras citadas tienen entrada en `referencias.md` y se comprobó una por una. **T9.1 (menor).** El capítulo nombra sin citarlas la norma IEEE 830 (§4.1.1), las vistas 4+1 (§4.3.1), la norma ISO/IEC 25010 (§4.1.3) y la legislación laboral en que se funda el destajo (§4.4.3). Ninguna tiene entrada en `referencias.md`. La Tabla 4.9 lo declara, y eso basta para el borrador. La versión final no se aprueba hasta que cada una tenga su entrada verificada y su cita, por ejemplo Kruchten (1995) para las 4+1 y el artículo de la ley laboral para el destajo. **T9.2 (menor).** §4.11.1 atribuye «la referencia de precios MaPreX de julio de 2026» a DataLaing (s.f.), cuya entrada es el programa MaPreX y no el listado de julio de 2026 que el sistema usa como dato (`data/precios/maprex_2026-07/`). Hay que agregar una entrada para el listado o reformular la oración para que la cita corresponda a lo citado. | T9.1: aplicada en parte. La LOTTT se verificó contra `docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.pdf` y su `.txt`, y contra `docs/fuentes/README.md` (Gaceta Oficial N.º 6.076 Extraordinario, 7 de mayo de 2012, Decreto N.º 8.938; artículo 114 leído). Entró en `referencias.md` como verificada y §4.4.3 la cita con el artículo. IEEE 830, Kruchten (4+1) e ISO/IEC 25010 entraron como **pendientes**: el repositorio solo las nombra y no contiene sus datos bibliográficos, que no se completan de memoria. Siguen nombradas sin cita, y la Tabla 4.10 lo declara. Quedan para la sesión de referencias antes de la versión final. <br>T9.2: aplicada (§4.11.1). La oración cita el programa (DataLaing, s.f.) y nombra los listados por su ruta (`data/precios/maprex_2026-07/`), sin atribuirles la cita. Se agregó en `referencias.md` una entrada **pendiente** para los listados, con los datos observados en los archivos (MaPreX 26.0.0.1, base `BDLaing08072026.mdb`, impresos el 13/07/2026); falta confirmar el autor institucional y el título de publicación. |
| T10 | cumple | Las ocho referencias que cita el capítulo están en estado «verificada» en `referencias.md`, y ninguna de las seis pendientes se cita. No hace falta la marca «[verificación pendiente]». | |
| T11 | cumple con observaciones | Se buscaron en el texto las formas de primera persona del plural: no aparece ninguna. El capítulo usa el pasado para lo que se hizo y el presente para lo que el sistema hace. **T11.1 (de proceso).** La meta automática no vigila este capítulo, y un 12/12 de `meta_redaccion.py` puede leerse como si lo hiciera. Antes de la próxima revisión, hay que extender R4 a R8 a `04-desarrollo.md`, con una prueba que primero falle, como se hizo con R5 en el acta del capítulo II. | T11.1: no aplicada: exige tocar el código de `scripts/meta_redaccion.py` y su prueba, fuera del alcance de la redacción. Registrada como INV‑075 (C3, importante), con la corrección propuesta: extender R4–R8 a todo capítulo presente, con una prueba que primero falle. Mientras tanto, esta versión se comprobó invocando las funciones de R4–R8 de `meta_redaccion.py` sobre `04-desarrollo.md` desde un script ad hoc, fuera del repositorio: voz impersonal, datos reales, «gemelo digital», citas y referencias pendientes, en OK. |
| T12 | cumple con observaciones | «Gemelo digital» no aparece. **T12.1 (menor).** Tampoco aparecen en el cuerpo «BIM‑5D» ni «sombra digital», aunque son los términos del título y del capítulo II y aunque el capítulo describe su realización. §4.7.2 debería decir que el adaptador IFC, junto con el motor, es la dimensión de costo del modelo BIM‑5D: cada cantidad queda ligada a su elemento por el `GlobalId`. §4.2 debería nombrar como sombra digital la línea que abre el rendimiento medido con su ejecución, como hace el capítulo II. | T12.1: aplicada. §4.7.2 dice que el adaptador IFC, junto con el motor, realiza la dimensión de costo del modelo BIM‑5D (cada cantidad ligada a su elemento por el `GlobalId`), con remisión a §2.2.2 y §2.2.3. §4.2 nombra como sombra digital la línea que abre el rendimiento medido con su ejecución, y aclara que el sistema no recibe esos datos de forma automática. |
| T13 | cumple con observaciones | Cada sección sigue el orden problema → decisión → evidencia que pide el guion, y la introducción anuncia el recorrido. **T13.1 (mayor).** El texto depende de un vocabulario interno del proyecto que no define para el lector de la tesis. Usa «fase C1/C3/C4 del cierre», «fase Red», «compuerta GC1», «Sesión P0.1/U1», «meta M9», «sprint del prototipo» y las decisiones «C1‑n», y cita unos treinta códigos INV‑xxx del inventario, a veces varios en un párrafo, como en §4.3.4 y §4.5.1. Un jurado no tiene cómo resolverlos. Hay que definir una vez esas nociones, en la introducción o en el capítulo III con remisión, y sacar los códigos INV del cuerpo: pueden ir a notas de tabla o a un anexo de desfases documentales, y el texto puede decir «desfase registrado en el inventario del cierre». **T13.2 (menor).** §4.1, §4.3, §4.4, §4.5, §4.7, §4.8, §4.9 y §4.11 empiezan directamente en su primera subsección, sin un párrafo que anuncie su hilo. Es la misma observación que T13 del acta del capítulo II. **T13.3 (menor).** §4.5.1 se contradice. Dice que, tras C1, «la interfaz, la API y los sembradores» pasan `plan=plan_secuencial` a `elaborar`, y el párrafo anterior dice que los tres sembradores de dominio siguen llamando a `generar_presupuesto` sin informe. Según INV‑069, el cuarto sitio era `scripts/seed_demo.py`; hay que nombrarlo. **T13.4 (menor).** El capítulo describe `main` en `f1dda36` y deja muchos puntos «para C2, C3 o C4». Cuando esas fases cierren, el texto quedará desfasado. La Tabla 4.9 debe tener una fila de «resincronización del capítulo con `v1.0-tesis`», además de las figuras. | T13.1: aplicada. La introducción define una sola vez las compuertas G0–G2, la auditoría de cierre con sus cuatro etapas de corrección y las decisiones D1–D9. El cuerpo ya no usa C1–C4, fase Red, GC1, M9, sesiones, «sprint», las decisiones C1‑n ni hashes de commits. Los códigos INV salieron del texto y quedaron en la Tabla 4.11 (sección → desfase o limitación → registro → etapa). Se conservaron los códigos formales de la especificación (UC, RF y RNF), las reglas R1–R7 y D1–D9, definidos en el texto. <br>T13.2: aplicada. §4.1, §4.3, §4.4, §4.5, §4.7, §4.8, §4.9, §4.10 y §4.11 abren con un párrafo que anuncia su hilo; se agregó también en §4.2, que empezaba directamente. <br>T13.3: aplicada (§4.5.1). Se nombran los cuatro sitios del protocolo: la pantalla de elaboración, la pantalla de composición, la ruta de la API y `scripts/seed_demo.py`. Se aclara que los tres sembradores de dominio nunca formaron parte de ese protocolo y siguen llamando a `generar_presupuesto`. <br>T13.4: aplicada. La Tabla 4.10 tiene la fila «Resincronización del capítulo con la versión congelada del software (`v1.0-tesis`)». |
| T14 | cumple con observaciones | El capítulo declara sus limitaciones: G1 con salvedad y RNF‑09 parcial; G2 por degradación; RF‑20 sin implementar; R6 a medias; contratos sin aval; y UC‑12 pendiente. No contradice lo excluido en §1.5.2. **T14.1 (menor).** §4.9.1 y §4.10.3 presentan resultados sobre casos didácticos o construidos: totales reproducidos, conteo de G2 y contraste AACE. Hay que recordar en esos puntos que no se generalizan estadísticamente y que la validación con presupuestos reales está fuera de alcance, con remisión a §1.5.2. | T14.1: aplicada. §4.9.1 y §4.10.3 recuerdan que los resultados vienen de casos didácticos o construidos, que no se generalizan estadísticamente y que no sustituyen la validación con presupuestos reales, fuera del alcance, con remisión a §1.5.2; la introducción lo declara para todo el capítulo. |

**Resultado:** **requiere nueva revisión** (no aprobado en revisión). T4 queda en «no cumple» por dos
afirmaciones sobre la práctica sin respaldo, una de ellas contradicha por el capítulo II (T4.1 y
T4.2). Hay 20 observaciones: 4 mayores (T4.1, T4.2, T6.2 y T13.1), 14 menores y 2 de proceso (T6.3
y T11.1). Las decisiones que dependen del tutor académico se declaran pendientes y no se dan por
resueltas: G0, D1 a D9, AACE 18R‑97 o 56R‑08, INV‑001, INV‑002, INV‑006 y la numeración desde
RF‑44. Coinciden con el [paquete para el tutor](2026-09-paquete-tutor.md) y no requieren
observación.

## Anexo — Muestra de afirmaciones contrastadas con el repositorio

| # | Afirmación del capítulo | Comprobación | Resultado |
|---|---|---|---|
| 1 | Quince entidades en `core/models/entidades.py` (§4.2) | 15 clases que heredan de `Base` | confirmada |
| 2 | `DecimalExacto` persiste como texto de hasta 40 caracteres (§4.2) | `core/models/tipos.py`: `LONGITUD_DECIMAL = 40` | confirmada |
| 3 | Restricción `ck_rendimiento_medido_exige_ejecucion` (§4.2) | `core/models/entidades.py:145` | confirmada |
| 4 | `cargar_presupuesto` compara con tolerancia 1 × 10⁻⁶; prueba `test_precios_se_reconstruyen_a_fecha` (§4.2) | `core/budget/persistencia.py:42`; `tests/integration/test_persistencia.py:61` | confirmada |
| 5 | `test_arquitectura.py` reúne 66 casos, incluida `test_la_guardia_cubre_todo_paquete_…` (§4.3.3) | `pytest --collect-only`: 66; función en la línea 74 | confirmada |
| 6 | La CI ejecuta `scripts/guardia_nucleo.py` y compara `docs/api.json` (§4.3.3, §4.11.2) | `.github/workflows/ci.yml:71` y `:118-120` | confirmada |
| 7 | `test_costing.py`: siete casos y los nombres de las dos pruebas de los errores clásicos (§4.4.2) | tres funciones, una parametrizada por cinco | confirmada (véase T6.4) |
| 8 | Fórmula con destajo cuya fuente única es `NORMAS.md` §4 (§4.4.1) | las líneas de destajo están en el docstring de `core/costing/motor.py`, no en `NORMAS.md` §4 | **discrepancia** (T6.2) |
| 9 | `elaborar` devuelve `ResultadoElaboracion`; los tres sembradores llaman a `generar_presupuesto` (§4.5.1) | `core/budget/presupuesto.py:53,62,91`; `scripts/seed_{telecom,industrial,sistemas}.py` | confirmada |
| 10 | `PlanInvalido` y la corrección de `plan_secuencial` en `3c026da` (§4.5.2) | `core/budget/curva.py:35`; `git log 3c026da` | confirmada |
| 11 | Libro de Excel de cuatro hojas con `DECIMALES_PRESENTACION` (§4.5.3) | `core/budget/excel.py:26,46-48,64` | confirmada |
| 12 | UC‑02: +30,17025 USD/m³ en el PU y +50,082615 USD en el total (§4.6) | `tests/fixtures/actualizacion_uc02.py:22-30` | confirmada |
| 13 | Recálculo de 100 partidas en 1,17 s (§4.6) | bitácora F.2 (31/08); repetición del revisor el 23/09: 1,34 s | **discrepancia de fecha** (T6.1) |
| 14 | Las siete expresiones de la Tabla 4.5 | `adapters/civil/reglas.py:25-31`, idénticas | confirmada |
| 15 | Cinco copias del evaluador de expresiones (§4.8.2) | `core/verification/expresiones.py` y `adapters/{civil,telecom,industrial,sistemas}/evaluador.py` | confirmada |
| 16 | Cuatro severidades (§4.8.3) | `core/contracts/verificacion.py:14-18` | confirmada |
| 17 | Expresiones de telecom, industrial y sistemas (Tabla 4.7) | `adapters/*/adaptador.py` | confirmada |
| 18 | Totales multidominio con diferencia cero: 1 109,29, 5 410,73, 18 124,09 y 16 093,89 USD (§4.9.1) | igualdad exacta en `test_presupuesto_arenaza.py:95`; `TOTAL_ESPERADO` en las pruebas industrial y de sistemas | confirmada |
| 19 | `git diff m-base --stat -- core/` vacío; el prototipo tocó siete archivos de `core/` (§4.9.2) | bitácora multidominio:13,122; bitácora del prototipo:42 | confirmada |
| 20 | Modelo `paraphrase-multilingual-MiniLM-L12-v2` con umbral 0,5; semilla 42 y mínimo de 8 observaciones (§4.10) | `ml/normalization/normalizador.py:29,34`; `ml/anomaly/detector.py:40,43` | confirmada |
| 21 | Conteo de G2: 5, 40, 4 y 9 (§4.10.3) | `docs/resultados_ml.md:11-14` | confirmada |
| 22 | Nueve pantallas, cuatro de investigación; 18 rutas; 735 pruebas y 98 % en la corrida 35950215309; once UC y 42 RF (§4.1, §4.11, introducción) | `ui/app.py:91-101`; `docs/api.json` (18 operaciones en 14 rutas); registros de la CI (`735 passed` en ambos sistemas, TOTAL 98 %); recuento de la ERS | confirmada |

También se comprobó que existen los 24 enlaces relativos del capítulo, las pruebas y los scripts que
nombra, y los 24 códigos INV que cita en el inventario.

## Respuesta del tesista

**Fecha:** 2026-09-23 · **Versión corregida:** commits `abcc92e` (capítulo y referencias), `d97b79d`
(`plan_redaccion.md` §5 y guion), `5c354e8` (inventario: INV‑074 e INV‑075) y el commit de esta
respuesta, que incluye además el ajuste de lectura de la fórmula en §4.4.1.

Se aplicaron las cuatro observaciones mayores. De las catorce menores, doce se aplicaron por
completo; T9.1 se aplicó en parte, porque tres referencias no tienen datos verificables en el
repositorio y quedan pendientes; y T1.2 se aplaza a la versión final, con su motivo. De las dos de
proceso, T6.3 se aplicó y T11.1 quedó registrada como INV‑075, porque exige código de `scripts/`.
Queda una observación para el capítulo II (véase T4.1). Se pide nueva revisión.


## Segunda revisión

**Fecha:** 2026-09-23 · **Versión revisada:** `a30ac08` (capítulo en `abcc92e`, cifras en `d97b79d`,
inventario en `5c354e8`) · **Tutor:** el mismo revisor de la primera pasada

Se leyó cada respuesta y se comprobó en el capítulo, en `referencias.md`, en `plan_redaccion.md` §5,
en el inventario y en el código que cada observación marcada como aplicada lo está de verdad. En el
capítulo corregido se volvieron a buscar la primera persona, «gemelo digital», «real» o «reales» y
las citas, y cada cita se contrastó con su entrada y su estado. `meta_redaccion.py` sigue en 12/12,
pero sigue sin leer este capítulo (INV‑075).

### Comprobación de las respuestas

| Obs. | Respuesta | Comprobación del tutor | Dictamen |
|---|---|---|---|
| T1.1 | aplicada | §4.3.1 abre con las cinco vistas, dice qué muestra cada una y remite al anexo C | aceptada |
| T1.2 | aplazada | La Tabla 4.10 condiciona la versión final al diagrama de componentes y al entidad‑relación. El motivo (desfases INV‑029, 057, 058, 061 y 070, que se corrigen en C4) es real y está registrado | justificación aceptada; condición para la versión final |
| T2.1 | aplicada | La Tabla 4.1 relaciona sección, objetivo, fase y producto; §4.4.2 nombra la línea base como producto de OE1 | aceptada; véase la recomendación S2 |
| T2.2 | aplicada | §4.9.2 remite a la sexta pregunta en la variante A y a un resultado complementario en la B | aceptada |
| T4.1 | aplicada | §4.4.1: el 600 % no tiene fuente normativa y el CIV publica factores de referencia (Colegio de Ingenieros de Venezuela, 2018, verificada), con remisión a §2.3.2 y a D4. Ya no contradice el capítulo II | aceptada |
| T4.2 | aplicada | §4.6 presenta el orden como decisión de planificación, con su motivo, y retira la afirmación de frecuencia | aceptada |
| T4.3 | aplicada | §4.8.2 usa la formulación del capítulo I, con las mismas tres citas (DataLaing e IP‑3, verificadas; Lulo, pendiente) y la marca «[verificación pendiente]» | aceptada |
| T6.1 | aplicada | §4.6 y la fila de §5 dan 1,17 s (31/08, equipo de desarrollo) y 1,34 s (23/09, otro equipo), y dicen que la cifra depende del equipo | aceptada; véase la recomendación S1 |
| T6.2 | aplicada | §4.4.1 atribuye la fórmula al docstring de `core/costing/motor.py`, líneas 3 a 13, que el tutor leyó. Precisa que el bono cuenta solo los obreros a jornal, lo que se confirma en `motor.py:45` y en `total_obreros`. Explica la diferencia con `NORMAS.md` §4 (INV‑074, en el inventario, C4). El guion de `plan_redaccion.md` también quedó corregido | aceptada |
| T6.3 | aplicada | Las filas nuevas de §5 llevan fecha o corrida, y la de los presupuestos multidominio lleva su comando. «18 operaciones sobre 14 rutas» coincide con `docs/api.json` | aceptada |
| T6.4 | aplicada | §4.4.2 habla de «siete casos» y de «cinco casos de una misma prueba parametrizada» | aceptada |
| T9.1 | aplicada en parte | La LOTTT entra verificada contra la Gaceta N.º 6.076 Extraordinario y se cita con su artículo 114. IEEE 830, las 4+1 (Kruchten) e ISO/IEC 25010 tienen entrada **pendiente** y siguen nombradas sin cita; la Tabla 4.10 lo declara. No completarlas de memoria es el criterio correcto | justificación aceptada para el borrador; condición para la versión final |
| T9.2 | aplicada | §4.11.1 cita el programa y nombra los listados por su ruta; los listados tienen entrada propia pendiente, que no se cita | aceptada |
| T11.1 | no aplicada; INV‑075 | Tocar `scripts/` queda fuera de una sesión de redacción, y el hallazgo tiene registro, corrección propuesta y etapa (C3). El tutor repitió a mano las búsquedas de R4 a R8 sobre la versión corregida: todas limpias | justificación aceptada |
| T12.1 | aplicada | §4.7.2 presenta el adaptador IFC y el motor como la dimensión de costo del BIM‑5D; §4.2 nombra la sombra digital y aclara que el sistema no recibe esos datos de forma automática | aceptada |
| T13.1 | aplicada | La introducción define una vez las compuertas, la auditoría de cierre y sus etapas, y las decisiones D1–D9. El cuerpo ya no usa C1–C4, GC1, M9, «sprint», «Sesión», las decisiones C1‑n, hashes ni códigos INV (solo quedan en los nombres de archivo de los enlaces), y la Tabla 4.11 conserva la trazabilidad | aceptada |
| T13.2 | aplicada | §4.1, §4.2, §4.3, §4.4, §4.5, §4.7, §4.8, §4.9, §4.10 y §4.11 abren con un párrafo de hilo | aceptada |
| T13.3 | aplicada | §4.5.1 nombra los cuatro sitios. El tutor comprobó que los cuatro pasan `plan=plan_secuencial` a `elaborar`: `ui/paginas/elaborar.py:234`, `ui/paginas/componer.py:808`, `api/rutas/presupuestos.py:91` y `scripts/seed_demo.py`. También comprobó que los sembradores de dominio siguen fuera del protocolo | aceptada |
| T13.4 | aplicada | La Tabla 4.10 tiene la fila de resincronización con `v1.0-tesis` | aceptada |
| T14.1 | aplicada | §4.9.1 y §4.10.3 y la introducción declaran que no hay generalización estadística y remiten a §1.5.2 | aceptada |

### Recomendaciones nuevas (no bloquean la aprobación)

- **S1.** §4.6 cita esta acta como fuente de la medición de 1,34 s. Un acta registra la revisión, no
  una medición; conviene citar el comando, la fecha y el equipo, o la fila de `plan_redaccion.md` §5,
  y dejar el acta fuera del texto de la tesis.
- **S2.** La Tabla 4.1 ubica §4.9 en las «fases III y VI». El esqueleto §2 no asigna una fase de las
  Bases al objetivo transversal («—»; sesiones I0.1 e I5). Hay que alinear la tabla con la matriz o
  corregir la matriz, para que no haya dos versiones.
- **S3.** La introducción remite al capítulo III la explicación de las compuertas y de la auditoría
  de cierre. Cuando se redacte ese capítulo, hay que comprobar que las define con los mismos nombres.

### Observación remitida al capítulo II

La respuesta a T4.1 señala algo que el tutor confirma. El capítulo II, en §2.3.2, dice que el CIV
«lo calcula y lo publica», y lo sostiene con una fuente que habla de factores **referenciales**. El
enunciado de D4 en el paquete para el tutor pide, además, citar los rangos publicados (198–293 % y
78–2 386 %), y el capítulo II no los cita: ni Chacín (2008) ni Dodi Scovino y Salas Caraballo (2019)
figuran en él ni en `referencias.md`. No afecta al dictamen de este capítulo, que ya formula el
punto con precisión. Se anota para un anexo del [acta del capítulo II](R1-capitulo-2.md).

### Dictamen

| Código | Veredicto | Fundamento |
|---|---|---|
| T1 | cumple con observaciones | Las secciones del guion están completas y las 4+1 se recorren. Queda T1.2 (figuras) como condición para la versión final |
| T2 | cumple | La Tabla 4.1 y §4.9.2 cierran la correspondencia entre preguntas, objetivos y fases (S2 es de forma) |
| T3 | cumple | Sin cambios |
| T4 | cumple | Las tres afirmaciones se corrigieron. No quedan afirmaciones sobre la práctica sin respaldo |
| T5 | cumple | La naturaleza de los datos se declara en la introducción y en cada tabla de casos |
| T6 | cumple | Cada cifra tiene fecha y comando o corrida; la fórmula tiene su fuente verificable (S1 es de forma) |
| T7 | cumple | Sin cambios; la cita del CIV y la de la LOTTT dicen qué sostienen |
| T8 | cumple | Las citas nuevas (CIV 2018, LOTTT 2012, art. 114, y la cita múltiple del capítulo I) siguen el formato autor‑año |
| T9 | cumple con observaciones | Toda cita tiene entrada. IEEE 830, las 4+1 e ISO/IEC 25010 siguen nombradas sin cita, con entrada pendiente, como condición para la versión final |
| T10 | cumple | La única referencia pendiente que se cita, Lulo Software, lleva la marca; las entradas pendientes nuevas no se citan |
| T11 | cumple | Voz impersonal, comprobada a mano. La cobertura automática queda en INV‑075 |
| T12 | cumple | BIM‑5D y sombra digital en su sentido; «gemelo digital» no aparece |
| T13 | cumple | Terminología interna definida o retirada, cada sección con su párrafo de apertura, §4.5.1 coherente y resincronización prevista |
| T14 | cumple | Lo excluido está declarado donde se presentan resultados sobre los casos |

**Resultado de la segunda revisión:** **aprobado en revisión**. Ningún criterio está en «no
cumple» y las 20 observaciones de la primera pasada tienen respuesta: 17 aplicadas, T9.1 aplicada en
parte, y T1.2 y T11.1 con justificación aceptada. Siguen abiertas, sin impedir esta aprobación, las
figuras (T1.2) y las tres referencias pendientes (T9.1), que son condición para la versión final;
INV‑074 (C4) e INV‑075 (C3); las recomendaciones S1–S3; la observación remitida al capítulo II; y
todas las decisiones del tutor académico (G0, D1–D9, AACE, INV‑001, INV‑002 e INV‑006), que el
capítulo declara pendientes. Esta aprobación no sustituye la del tutor académico designado.
