# Paquete de decisiones para el tutor académico designado

**Fecha:** 2026‑09‑23 · **Prepara:** condición **F2** del cierre de la tesis
([spec §1](../../superpowers/specs/2026-09-23-plan-cierre-tesis-design.md#1-el-final-endpoint)): *«el
tutor académico designado validó lo que el proyecto decidió sin él»* — constancia en
`docs/tesis/revisiones/` de la compuerta G0 (validación retroactiva), de las nueve decisiones D1–D9 de
[docs/dossier_g0.md §3](../../dossier_g0.md#3-decisiones-que-esperan-la-validación-del-tutor) y de la
elección AACE 18R‑97 frente a 56R‑08. Este documento **no copia** el contenido de cada punto: lo enlaza
a su fuente (principio DRY, [metodologia.md §5](../../metodologia.md#5-dry)). Suma también, por ser
constancias que F2 necesita igual, T2/T3 del acta del capítulo I y la numeración de UC‑09.

**Regla general si el tutor rechaza un punto** (spec §1, párrafo de rechazo): se abre un expediente en
`docs/bitacora/` y la corrección entra como hallazgo del inventario vivo en la fase de la capa que le
corresponda; la línea base (`CLAUDE.md` §2 principio 5, y §4) solo cambia por decisión escrita del
tutor, con expediente previo. La columna «Si rechaza» de cada fila aplica esa regla al punto concreto;
cuando el propio dossier ya declara una consecuencia específica (D1), se usa esa.

## Puntos a decidir

| # | Pregunta al tutor | Opciones | Recomendación del proyecto | Desarrollado en | Fase del cierre que depende de la respuesta | Si rechaza |
|---|---|---|---|---|---|---|
| **G0** | ¿Aprueba retroactivamente, sin haberlos revisado antes de I0.3 ([metodologia.md §2.2](../../metodologia.md#22-compuertas)), los tres documentos de la Fase 0 que ya respaldan todo el sistema construido? | aprobar tal como están · aprobar con cambios · rechazar | aprobar — ningún incremento posterior los invalidó; las actualizaciones fueron de trazabilidad, nunca de fondo | [dossier_g0.md §1](../../dossier_g0.md#1-qué-aprueba-g0) (ERS, modelo de datos, arquitectura) | Congelamiento (F2 es condición de `v1.0-tesis`) | regla general: expediente en bitácora; los documentos de la Fase 0 se corrigen retroactivamente como hallazgo de C4, y lo que ya se construyó sobre ellos queda sujeto a revisión |
| **D1** | ¿Aprueba R7 (`ConciliacionPresupuestoPlan`) como regla de verificación de fondo, además de las cinco que listan las Bases del anteproyecto? | aprobar R7 · rechazarla y quedarse en seis reglas | aprobar | [dossier_g0.md#D1](../../dossier_g0.md#d1-regla-r7--conciliacionpresupuestoplan) | C1 (la regla vive en `core/verification/`) | cambian RF‑21/RF‑22; el indicador 1 se cuenta sobre seis reglas; la raíz del hallazgo 3 (línea base) queda sin regla que la explique (consecuencia propia del dossier) |
| **D2** | ¿Aprueba la regla candidata R8 («precio uniforme del insumo») como octava regla de verificación? | aprobarla como R8, mismo patrón que R1–R7 · dejarla solo como hallazgo documentado del modelo de datos | aprobarla — ya existen la evidencia y el mecanismo (`ResumenCarga.variantes`) que la alimentarían | [dossier_g0.md#D2](../../dossier_g0.md#d2-regla-candidata-r8--precio-uniforme-del-insumo) | C1 | no se implementa R8; el octavo defecto del caso queda solo como hallazgo documentado; el indicador 1 no cambia (sigue en 7 de 7) |
| **D3** | ¿La extensibilidad multidominio (núcleo intacto al agregar dominios) se incorpora como objetivo específico **OE7** propio, o queda como resultado complementario de OE3? | variante A: OE7, ajusta título y alcance · variante B: resultado complementario, capítulo V | variante A (OE7) — es el aporte más distintivo del trabajo y ya está demostrado empíricamente; dejarlo como nota lo subvendería | [dossier_g0.md#D3](../../dossier_g0.md#d3-extensibilidad-multidominio-oe7-o-resultado-complementario), [esqueleto_tesis.md §3](../esqueleto_tesis.md) | Red (spec §5: el capítulo I se redacta «tras D3») | (elige variante B) el título y el capítulo I no cambian; la evidencia multidominio pasa a resultado complementario del capítulo V; T2 y T3 (abajo) se cierran con la redacción de las Bases sin preguntas ni objetivo nuevos |
| **D4** | ¿Avala declarar el FCAS (600 %) parámetro configurable del caso de estudio, sin cita normativa venezolana, citando en el marco teórico los rangos publicados (198–293 % y 78–2 386 %)? | avalar esa declaración · orientar hacia otra fuente citable | avalar — verificado que ningún gremio, COVENIN ni la convención colectiva vigente publican el FCAS | [dossier_g0.md#D4](../../dossier_g0.md#d4-fuente-primaria-del-fcas-600-) | Red (capítulo II, marco teórico) | se abre expediente; la redacción del marco teórico espera la fuente que el tutor oriente antes de cerrarse |
| **D5** | ¿RF‑16 se acota en la ERS a la precarga de partidas ya implementada, o se implementa el flujo completo de creación de partidas? | acotar RF‑16 a la precarga · implementar el flujo de creación como incremento nuevo | el dossier no fija recomendación: pide decidirlo para que la ERS no prometa de más | [dossier_g0.md#D5](../../dossier_g0.md#d5-flujo-de-creación-de-partidas-rf16-y-familia) | C4 si se acota (ajuste de redacción de la ERS); si se implementa, es **capacidad nueva** fuera del límite de C0–C4 (spec §2) | entra como capacidad nueva: no se ejecuta en esta ronda de cierre salvo enmienda escrita de la spec por Eugenio (spec §2); queda como trabajo futuro |
| **D6** | ¿Valida que la postcondición de UC‑08 se cumple en memoria (promover un escenario equivale a UC‑02) sin persistir escenarios, o pide persistirlos? | validar el diseño actual, ajustando la redacción de la postcondición · pedir persistencia de escenarios como extensión | validar la decisión actual | [dossier_g0.md#D6](../../dossier_g0.md#d6-postcondición-de-uc08-escenarios-guardados) | C4 (ajuste de redacción de la postcondición de UC‑08 en la ERS) | capacidad nueva fuera del límite de C0–C4 (spec §2); persistir escenarios queda como trabajo futuro salvo enmienda |
| **D7** | ¿Aprueba la definición operativa de «rama de adaptador» de la meta M9 (agrega archivos bajo `adapters/` o `ml/` y no toca `core/`) tal como está? | aprobarla tal como está · redefinirla | aprobarla — vigiló ocho ramas sin falsos positivos | [dossier_g0.md#D7](../../dossier_g0.md#d7-alcance-de-la-meta-m9-rama-de-adaptador) | C4 (coherencia de la definición en la documentación) | se redefine «rama de adaptador» y se revisan retroactivamente las ramas ya evaluadas con la definición actual |
| **D8** | ¿Confirma «BIM‑5D» (no «gemelo digital») como terminología del sistema para el anteproyecto y la defensa? | confirmar BIM‑5D · usar otra terminología | (el dossier remite a [metodologia.md §9](../../metodologia.md#9-riesgos-que-gobiernan-las-compuertas): «gemelo digital» sería impreciso) confirmar BIM‑5D | [dossier_g0.md#D8](../../dossier_g0.md#d8-declaración-bim5d-no-gemelo-digital); ya usada en los capítulos I y II (T12 del acta, abajo) | Red (terminología de capítulos ya redactados) | se corrige la terminología en ERS, arquitectura y en los capítulos I y II ya redactados |
| **D9** | ¿Avala el campo aditivo `ModalidadManoObra` (`JORNAL`/`DESTAJO`, por defecto `JORNAL`) en `LineaManoObra` para que el motor calcule el destajo (art. 114 LOTTT) sin romper la línea base? | opción 1: campo aditivo en el contrato (recomendada) · opción 2: sueldo sintético fuera del núcleo (no aplica, el dossier lo descarta) · opción 3: no implementar, declarar limitación · opción 4: categoría `subcontratos` nueva | opción 1 — aditiva y retrocompatible; la línea base reproduce el mismo precio unitario hasta el último decimal | [dossier_g0.md#D9](../../dossier_g0.md#d9-modalidad-de-mano-de-obra-por-linea-cambio-a-un-contrato-declarado-estable) | C1 (cambia un contrato congelado de `core/contracts/`) | mientras el aval esté pendiente o sea negado, el hallazgo de RF‑34 queda **aceptado por decisión de arquitectura registrada** (spec §4, único estado reservado para contratos sin aval) y se declara limitación del prototipo; no bloquea F3 |
| **AACE** | ¿El caso de estudio se clasifica con AACE 18R‑97 (industrias de proceso, la que hoy usa la ERS) o con la 56R‑08 (específica de edificación; clase 3 más estricta: −5 %/−15 % y +10 %/+20 %, contra la holgura de la 18R‑97)? | mantener 18R‑97 · adoptar 56R‑08 | el acta no fija recomendación del proyecto: la elección y su justificación quedan explícitamente para el tutor (marco metodológico) | [R1-capitulo-2.md](R1-capitulo-2.md), criterio T4, y su anexo con las cifras de la 56R‑08 | Red (capítulo II §2.3.3, marco metodológico); también C4 si `calidad_iso25010.md` cita la clase | si se aparta de la 18R‑97 ya usada: se reescribe el capítulo II con los rangos de la 56R‑08 y se justifica por qué el caso de estudio es clase 3 bajo esa norma (T4 del acta del capítulo I lo deja pendiente, ver abajo) |
| **T2** | ¿Se mantiene la redacción de las Bases del anteproyecto —donde OE1 (diagnóstico) y OE3 (base de datos y motor) solo atan a la pregunta principal, sin pregunta secundaria propia— o se formulan dos preguntas secundarias nuevas para atenderlos? | mantener la redacción de las Bases, con la nota que ya declara la asociación · formular dos preguntas secundarias nuevas | el acta mantiene por defecto mientras se decide junto con D3 | [R1-capitulo-1.md](R1-capitulo-1.md), criterio T2 | Red (capítulo I, redacción final tras D3) | se reescribe la Tabla 1.2 del capítulo I con las preguntas secundarias nuevas antes de darlo por completo (F4) |
| **T3** | ¿OE4 («con la técnica que permita la disponibilidad de datos») y el objetivo general extenso de la variante A de D3 quedan como están, o se piden más medibles/concisos? | conservar OE4 tal como está; revisar el objetivo general de variante A solo si el tutor la elige · pedir una redacción más medible de OE4 | conservar OE4 — su criterio de medición ya lo fija la compuerta G2 | [R1-capitulo-1.md](R1-capitulo-1.md), criterio T3 | Red (capítulo I, junto con D3) | se reformulan OE4 y/o el objetivo general antes de cerrar el capítulo I (F4) |
| **UC‑09/RF‑44** | ¿Confirma que, al ejecutarse la Sesión A0.1 de `PLAN_ASISTENTE.md`, los requisitos de UC‑09 se numeren a partir de **RF‑44** (siguiente libre) en vez de RF‑32 como decía ese plan? | confirmar la numeración desde RF‑44, ya vigente en la ERS · volver a la numeración original desde RF‑32 | confirmar RF‑44 — RF‑32 es hoy la única reserva contigua: RF‑33 a RF‑43 ya los tomaron UC‑10, UC‑11 y UC‑12 | [ERS.md §2.2](../../ERS.md) (nota de la Sesión U0.1) y §3.2 | fuera del alcance de implementación del cierre (UC‑09 es trabajo futuro, spec §2); dentro del cierre solo afecta la coherencia de la numeración de la ERS vigente (C4) | si se vuelve a RF‑32 para todo UC‑09, colisiona con RF‑33 a RF‑43 ya asignados; habría que renumerar esos rangos y corregir de nuevo toda la ERS |

## Modelo de constancia

Una fila por punto, firmada por el tutor académico designado. F2 exige esta constancia en
`docs/tesis/revisiones/`; no la sustituye ninguna lista de cotejo automática.

| Punto | Veredicto (aprobado / aprobado con cambios / rechazado) | Observaciones | Fecha |
|---|---|---|---|
| G0 | | | |
| D1 | | | |
| D2 | | | |
| D3 | | | |
| D4 | | | |
| D5 | | | |
| D6 | | | |
| D7 | | | |
| D8 | | | |
| D9 | | | |
| AACE 18R‑97 / 56R‑08 | | | |
| T2 (acta capítulo I) | | | |
| T3 (acta capítulo I) | | | |
| UC‑09 desde RF‑44 | | | |

**Firma del tutor académico designado:** ______________________________ **Fecha:** ______________
