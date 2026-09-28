# Protocolo del juicio de expertos de RNF‑04 — el informe de auditoría sin formación previa

| Campo | Valor |
|---|---|
| Requisito | RNF‑04 de la [ERS §3.3](ERS.md#33-requisitos-no-funcionales-isoiec-25010): «el informe de auditoría se entiende sin formación previa»; métrica, juicio de expertos (Likert); meta, ≥ 4/5 |
| Instrumento | bloque A del [anexo A del dossier G0](dossier_g0.md): ocho afirmaciones en escala 1–5 y un campo abierto. **Este protocolo no lo cambia** |
| Escrito en | fase C4 del cierre, 2026‑09‑28 ([spec de cierre §5](superpowers/specs/2026-09-23-plan-cierre-tesis-design.md), fila C4) |
| Se ejecuta en | fase Med del cierre ([PLAN_CIERRE.md](../PLAN_CIERRE.md)) |
| Versión del protocolo | el commit que contiene este archivo; se anota en cada hoja de registro |

El anexo A dice **qué** se pregunta; este protocolo dice **a quién**, **sobre qué versión exacta
del informe**, **cómo** se aplica y **cómo se decide**, para que lo ejecute un tercero sin
consultar al autor. Está escrito antes de medir: el criterio de la sección 6 no se cambia después
de la primera respuesta (spec de cierre §5, fila Med: «ningún criterio se relaja tras medir»).

Las Bases del anteproyecto (`docs/fuentes/Bases_Anteproyecto_BIM5D_APU.docx`, §8.3) prevén el
juicio de expertos como «instrumento tipo Likert aplicado a un panel de tres a cinco ingenieros con
experiencia en costos de obra». RNF‑04 lo concreta sobre el informe de auditoría. RNF‑10 (la
interfaz) es otro requisito, con otro instrumento (bloque B y CP‑07), y su promedio nunca se mezcla
con este.

**Naturaleza de los datos.** El informe evaluado es el del caso didáctico de la clínica, un
ejercicio académico ficticio ([CLAUDE.md §1](../CLAUDE.md#1-qué-es-este-proyecto)); a los expertos
se les dice así.

## 1. El informe que se evalúa y su versión

**Qué informe.** El del caso de estudio que anuncia el anexo A: el presupuesto de la línea base con
sus siete inconsistencias (`tests/fixtures/presupuesto_auditado.py`,
`presupuesto_con_siete_inconsistencias`), auditado por el sistema (`core.verification.auditar`).
No se edita nada. **Se entrega en las dos formas en que el sistema lo presenta** (ruling del
controlador en la revisión de la pista D, fase C4), generadas del mismo commit y con la misma orden:

- **La forma de pantalla:** `informe_rnf04.md`, el texto que la aplicación pinta
  (`InformeAuditoria.a_markdown`, el mismo que muestran «Elaborar un presupuesto» y «Componer una
  partida»). Se muestra **renderizado**, con sus encabezados y tablas, en una vista previa de
  Markdown (por ejemplo, la de VS Code), o impreso desde esa vista.
- **La forma exportada:** `informe_rnf04.xlsx`, el libro de Excel de cuatro hojas
  (`core.budget.exportar_excel`): *Presupuesto*, *APU*, *Curva* y *Auditoria*. El informe es la
  hoja *Auditoria*; las otras tres son el presupuesto auditado, el contexto que un profesional
  tendría a mano.

**Qué trae cada forma, declarado antes de medir.** Las dos listan los mismos 14 hallazgos en el
mismo orden, pero no con las mismas columnas:

| Dato | Pantalla (`.md`) | Hoja *Auditoria* (`.xlsx`) |
|---|---|---|
| Resultado global («Hallazgos: 14 · Resultado: NO CUMPLE») | sí | no |
| Resumen por severidad | sí | no |
| Regla, severidad, descripción, impacto | sí | sí |
| Partida del hallazgo | sí | no |
| Observado y esperado | sí | no |
| Orígenes (`origen_id`) | no | sí |

Por eso **cada afirmación del anexo A se juzga sobre una forma fija** (columna «Se juzga sobre» de
la rúbrica, sección 7), y el cuestionario impreso la indica al margen de cada afirmación, sin
cambiar su texto:

| Afirmación | Se juzga sobre | Por qué |
|---|---|---|
| 1 Entender qué comprueba | las dos | es un juicio sobre el informe entero |
| 2 Severidad comprensible y bien asignada | las dos | las dos traen la severidad; la pantalla, además, su resumen |
| 3 Impacto cuantificado | la pantalla | solo ella trae, junto al impacto, lo observado y lo esperado («montos y cantidades en juego»); con la hoja sola, la afirmación se juzgaría con menos datos |
| 4 Orígenes para ubicar la fila | la hoja *Auditoria* | es la única que trae los `origen_id` |
| 5 Orden por severidad | la pantalla | trae el resultado global y el resumen por severidad que encabezan el orden; en la hoja el orden existe, pero sin ese encabezado |
| 6 Lenguaje apropiado | las dos | las descripciones son las mismas |
| 7 Decidir qué corregir y en qué orden | las dos, leídas juntas | decidir pide la partida y lo esperado (pantalla) y el origen de la fila (hoja) |
| 8 Confianza como complemento | las dos | es un juicio sobre el informe entero |

Así, ninguna afirmación se contesta sobre una forma que carece del dato que pregunta. El capítulo V
reporta esta asignación junto al resultado. En este informe la columna *Partida* de la pantalla es
fiable: cada `origen_id` de la fixture es único (`computo:<código>`), así que no le alcanza el
defecto de atribución de esa columna que el controlador registró en la revisión de C4 (M3), que
aparece cuando varias partidas comparten un mismo `origen_id`.

**Cómo se genera** (el observador, en la copia desechable de la sección 3, desde su raíz):

```
uv run python -c "from pathlib import Path; from tests.fixtures.presupuesto_auditado import presupuesto_con_siete_inconsistencias as p; from core.verification import auditar; from core.budget import exportar_excel; pr = p(); inf = auditar(pr); exportar_excel(pr, inf, Path('informe_rnf04.xlsx')); Path('informe_rnf04.md').write_text(inf.a_markdown(), encoding='utf-8', newline='\n')"
```

La orden escribe los dos archivos que se entregan: `informe_rnf04.md` (la forma de pantalla) y
`informe_rnf04.xlsx` (la forma exportada).

**La versión del informe** se fija con tres datos, que van en cada hoja de registro:

1. **El commit probado:** `git log -1 --oneline` en la copia desechable; un commit de `main` con su
   corrida de CI en verde, cuyo enlace también se anota. Por ejemplo, `ceb6b8e` tiene la corrida
   [36428464254](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36428464254)
   (push a `main`, en verde).
2. **La huella de la forma de pantalla** (que es también la del contenido del informe): SHA‑256 de
   `informe_rnf04.md` (en bash,
   `sha256sum informe_rnf04.md`; en PowerShell,
   `Get-FileHash informe_rnf04.md -Algorithm SHA256`). El texto no lleva fecha, así que la huella
   solo cambia si cambia el informe. Sobre el código de `ceb6b8e` (`main`) vale
   `9469aaf8ded7d8ba901b99060a80a12be60fc18d1c7152e850c98ec024ed0063` y el informe tiene **14
   hallazgos**: 1 CRITICO, 12 ERROR y 1 ADVERTENCIA. Si el commit probado da otra huella, se anota
   y se explica qué cambió antes de aplicar el instrumento.
3. **La huella de la forma exportada:** SHA‑256 de `informe_rnf04.xlsx`. El libro guarda su fecha
   de creación, así que su huella cambia en cada generación: por eso **se genera una sola vez** y
   todos los expertos reciben **esos mismos dos archivos** (las mismas dos huellas en todas las
   hojas de registro).

## 2. Los expertos

**Cuántos: n ≥ 3; se buscan 5.** Tres es el mínimo que fijan la spec de cierre (fila C4) y las
Bases (panel de tres a cinco); cinco, el máximo de las Bases, reduce el peso de un experto atípico
en el promedio. Con menos de tres respuestas válidas **no hay medición**: RNF‑04 sigue pendiente y
así se declara.

**Perfil (inclusión).** Ingeniero civil, arquitecto u otro profesional de la construcción con
**al menos tres años** elaborando, revisando o auditando presupuestos de obra o APU (el perfil de
las Bases: «ingenieros con experiencia en costos de obra»; se admite arquitecto o afín con esa misma
experiencia, y se anota).

**Exclusión** (cualquiera de estas condiciones excluye):

- el autor de la tesis;
- quien tenga **relación personal** con el autor: familia, pareja, amistad, o dependencia laboral o
  académica directa con él (spec de cierre §5, fila Med);
- quien haya participado en el proyecto, **incluidos el tutor académico y el tutor técnico**, que
  lo conocen; el tutor puede supervisar la aplicación, no responder;
- quien haya visto la aplicación, sus documentos o el informe antes de la sesión;
- quien haya participado en la medición del indicador 3 ([protocolo_indicador3.md](protocolo_indicador3.md))
  o en CP‑07: ya vio informes del sistema.

Cada experto firma, en su hoja de registro, la declaración de que no está en ninguno de esos casos.
Se registra su **perfil**, nunca su nombre: profesión, años de experiencia en costos, rol habitual
(elabora, revisa o audita presupuestos) y sector (público, privado, docencia). Participación
voluntaria; los datos se publican sin nombres.

## 3. Preparación (el observador)

1. **Copia desechable** del repositorio, nunca la copia de trabajo (como la sección 4 del
   [guion de prueba](guion_prueba_arenia.md)): `git worktree add ../tesis-rnf04 <commit>` y, dentro
   de ella, `uv sync`. El `<commit>` cumple lo dicho en la sección 1, punto 1.
2. Generar el informe **una sola vez** con la orden de la sección 1 y anotar las dos huellas.
3. Preparar para cada experto: las **dos formas** del informe, `informe_rnf04.md` renderizado y
   `informe_rnf04.xlsx` (o, si prefiere papel, la vista renderizada del `.md` y las cuatro hojas del
   libro, impresas, anotando que fue en papel); el **bloque A del anexo A impreso tal cual** (las
   ocho afirmaciones y el campo abierto, sin cambiar una palabra), con la forma sobre la que se
   juzga cada afirmación (tabla de la sección 1) anotada al margen; la hoja de rúbrica de la
   sección 7.
4. Borrar la copia desechable al terminar todas las sesiones:
   `git worktree remove ../tesis-rnf04`.

## 4. La sesión (una por experto, individual)

Presencial o a distancia; siempre **un experto a la vez** y sin comunicación entre expertos hasta
que todos hayan respondido.

**Consigna literal** (se lee o se envía tal cual, sin agregar nada):

> «Le entrego el informe de auditoría que un sistema produjo sobre un presupuesto de obra; el
> presupuesto es un ejercicio académico, no una obra ejecutada. El informe viene en dos formas: como
> se ve en la pantalla del sistema y como se exporta a Excel, en la hoja *Auditoria* del libro; las
> demás hojas del libro son el presupuesto auditado. Léalo como lo leería si se lo enviara un colega
> y, al terminar, marque su grado de acuerdo con cada afirmación del cuestionario; al margen de cada
> una se indica sobre qué forma contestarla. No hay respuestas correctas: lo que se evalúa es el
> informe, no a usted.»

**Reglas:**

1. **Sin explicación previa del sistema** (anexo A): ni qué hace, ni cómo se llaman sus reglas, ni
   qué significan sus columnas. Eso es exactamente lo que se mide.
2. El observador **no contesta preguntas sobre el contenido del informe**. Respuesta fija:
   «Responda con lo que el documento le permite entender». Anota cada pregunta: es un dato.
3. Sin límite de tiempo. Se anota el tiempo de lectura (desde la entrega hasta que empieza el
   cuestionario) y el total.
4. El experto contesta **a solas**; el observador no mira mientras lo hace.
5. Al terminar, el observador verifica que cada afirmación tenga **una** marca entre 1 y 5; si hay
   una en blanco o doble, pregunta una sola vez «¿quiere completar o corregir la afirmación N?»,
   sin sugerir valor. Lo que quede en blanco se anota como omitido.

## 5. Qué se registra

Por experto: las ocho puntuaciones, el campo abierto literal, el perfil, la declaración firmada,
la fecha, el medio (archivo o papel), los tiempos, las preguntas hechas al observador, el commit
probado, su corrida de CI, las dos huellas y la versión del protocolo (la hoja de la sección 7).

## 6. Criterio de decisión, declarado antes de medir

1. **Respuesta válida:** la de un experto que cumple la sección 2 y contestó al menos seis de las
   ocho afirmaciones. Una respuesta con más de dos omitidas se reporta y no entra en el promedio.
2. **Promedio del experto:** la media de sus afirmaciones contestadas.
3. **Promedio global:** la media de los promedios de los expertos válidos (cada experto pesa lo
   mismo, conteste siete u ocho afirmaciones).
4. **RNF‑04 CUMPLE si y solo si** hay al menos tres expertos válidos **y** el promedio global es
   **≥ 4,0**. En cualquier otro caso, **NO CUMPLE** (con tres o más válidos) o **sigue pendiente**
   (con menos de tres). Es la meta de la ERS (≥ 4/5) y la del anexo A («≥ 4/5 en promedio»), sin
   agregarle ni quitarle nada.
5. **Se reporta además, sin que cambie el veredicto:** el promedio por afirmación, con su mínimo y
   su máximo; el promedio de cada experto; las afirmaciones con promedio menor que 3, como hallazgos
   del informe para el capítulo V; y los campos abiertos, literales. Ningún experto válido se
   descarta después de ver su respuesta.

## 7. Plantilla de rúbrica

**Hoja por experto** (se entrega junto al bloque A impreso; las afirmaciones completas están en el
anexo A y aquí van con una etiqueta breve):

| Campo | Valor |
|---|---|
| Código del experto (`E01`…) | |
| Perfil: profesión · años en costos de obra · rol (elabora / revisa / audita) · sector | |
| Declaración: «No soy el autor ni tengo relación personal con él; no participé en el proyecto ni vi antes la aplicación, sus documentos o este informe; no participé en la medición del indicador 3 ni en CP‑07» (firma) | |
| Fecha · medio (archivo / papel) · presencial o a distancia | |
| Commit probado · corrida de CI en verde de ese commit | |
| SHA‑256 de `informe_rnf04.md` (pantalla) · SHA‑256 de `informe_rnf04.xlsx` (exportada) | |
| Versión del protocolo (commit que contiene este archivo) | |
| Tiempo de lectura (min) · tiempo total (min) | |
| Preguntas al observador (literal) | |

| # | Afirmación (etiqueta; texto completo en el anexo A) | Se juzga sobre | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|---|
| 1 | Entendí qué comprueba sin formación previa | las dos | | | | | |
| 2 | Severidad comprensible y bien asignada | las dos | | | | | |
| 3 | El impacto cuantificado permite dimensionar | pantalla (`.md`) | | | | | |
| 4 | Los orígenes permiten ubicar la fila | hoja *Auditoria* (`.xlsx`) | | | | | |
| 5 | El orden presenta primero lo que más importa | pantalla (`.md`) | | | | | |
| 6 | Lenguaje apropiado para un profesional de obra | las dos | | | | | |
| 7 | Permite decidir qué corregir y en qué orden | las dos, leídas juntas | | | | | |
| 8 | Confiaría en él como complemento de una revisión manual | las dos | | | | | |

Escala: 1 = totalmente en desacuerdo · 3 = neutral · 5 = totalmente de acuerdo.

Campo abierto (literal): *¿qué le falta o le sobra al informe para serle útil en su trabajo?*

| Resultado del experto | Valor |
|---|---|
| Afirmaciones contestadas (de 8) | |
| Promedio del experto | |
| ¿Respuesta válida? (sección 6, punto 1) | |

**Hoja consolidada:**

| Afirmación | E01 | E02 | E03 | E04 | E05 | Promedio | Mín | Máx |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |
| 2 | | | | | | | | |
| 3 | | | | | | | | |
| 4 | | | | | | | | |
| 5 | | | | | | | | |
| 6 | | | | | | | | |
| 7 | | | | | | | | |
| 8 | | | | | | | | |
| **Promedio del experto** | | | | | | | | |

Expertos válidos: n = ___ · **Promedio global = ___** · Veredicto de RNF‑04 (sección 6, punto 4):
CUMPLE / NO CUMPLE / sigue pendiente · Commit probado y huellas: ___

## 8. Amenazas a la validez y cómo se controlan

| Amenaza | Control |
|---|---|
| Complacencia con el autor | Exclusión por relación personal y participación; declaración firmada; consigna que dice que se evalúa el informe, no a la persona |
| Explicaciones que contaminan la medición | Consigna literal y respuesta fija a las preguntas de contenido |
| Expertos que se influyen entre sí | Sesiones individuales, sin comunicación hasta el final |
| Versiones distintas del informe | Un commit, una generación, dos huellas anotadas en cada hoja |
| Una forma del informe sin el dato que la afirmación pregunta | Se entregan las dos formas y cada afirmación declara, antes de medir, sobre cuál se juzga (sección 1) |
| Muestra pequeña | n ≥ 3 declarado como mínimo; el resultado se cita como juicio de un panel, no como muestra representativa |
| Criterio acomodado al resultado | Criterio de la sección 6 escrito antes de medir; nada se relaja después |

## 9. Dónde se registra el resultado

- Las hojas transcritas (sin nombres) y el veredicto: la bitácora de la fase Med.
- La interpretación: [calidad_iso25010.md §4 y §9](calidad_iso25010.md).
- La correspondencia RNF‑04 → verificación: la [ERS](ERS.md) y [plan_pruebas.md §9](plan_pruebas.md).
- La cifra citable, con n, perfil, fecha, commit y huella: la tabla de la sección 5 de
  [tesis/plan_redaccion.md](tesis/plan_redaccion.md#5-cifras-citables-y-cómo-regenerarlas).
