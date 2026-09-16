# Lista de cotejo del tutor — capítulos del trabajo de grado

Instrumento con el que el **tutor** revisa cada capítulo antes de darlo por aprobado en revisión.
El **tesista** redacta; el tutor aplica esta lista criterio por criterio y deja un acta en
`docs/tesis/revisiones/`; el tesista corrige y responde cada observación en la misma acta. La
aprobación del tutor académico designado por la institución se registra aparte y no la sustituye
este instrumento, que sirve para llegar a esa revisión con el capítulo ya depurado.

Diseño y alcance: [spec del Sprint R1](../superpowers/specs/2026-09-15-sprint-r1-capitulos-design.md)
§5. Convenciones de redacción: [plan_redaccion.md](plan_redaccion.md) §1.

## Escala

| Veredicto | Significado |
|---|---|
| **cumple** | el criterio se satisface sin observaciones |
| **cumple con observaciones** | se satisface, pero hay mejoras que el tesista debe responder (aplicarlas o justificar por qué no) |
| **no cumple** | el criterio no se satisface; el capítulo no se aprueba en revisión hasta corregirlo |

Un capítulo queda **aprobado en revisión** cuando ningún criterio está en «no cumple» y cada
observación tiene respuesta del tesista.

## Criterios

### Estructura y coherencia

| Código | Criterio | Qué mira el tutor |
|---|---|---|
| **T1** | Las secciones del guion están completas | Capítulo I: planteamiento, formulación, objetivos, justificación, alcance y delimitación. Capítulo II: antecedentes (internacional, latinoamericano, nacional), bases teóricas, bases normativas, definición de términos |
| **T2** | Pregunta, objetivos y fases se corresponden | Cada pregunta secundaria tiene un objetivo específico que la atiende y cada objetivo, una fase con producto (observación metodológica de las Bases §3.2). Ningún objetivo sin pregunta ni pregunta sin objetivo |
| **T3** | Objetivos bien formulados | Cada objetivo empieza con un verbo en infinitivo, describe un logro alcanzable dentro de la investigación y tiene un producto verificable; el general engloba a los específicos |

### Rigor y evidencia

| Código | Criterio | Qué mira el tutor |
|---|---|---|
| **T4** | Afirmaciones sobre la práctica con respaldo | Toda afirmación sobre cómo se presupuesta en la práctica, cuánto tiempo toma o qué errores ocurren se apoya en literatura citada; ninguna se sostiene solo en la opinión del autor |
| **T5** | Casos presentados como didácticos | Los APU y presupuestos del repositorio (clínica, ARENAZA, `MNT-001`, `SIS-001`) se presentan como casos didácticos o construidos, con su alcance declarado; ninguno se presenta como obra ejecutada ni como dato real (`CLAUDE.md` §1) |
| **T6** | Cifras del proyecto trazables | Toda cifra del proyecto coincide con la tabla de cifras citables de `plan_redaccion.md` §5; las cifras de la literatura llevan su cita |
| **T7** | Antecedentes con aporte explícito | Cada antecedente dice en una o dos oraciones qué aporta a **este** trabajo o qué vacío deja; no hay resúmenes sueltos |

### Citación (APA 7.ª edición)

| Código | Criterio | Qué mira el tutor |
|---|---|---|
| **T8** | Formato autor‑año | Citas narrativas «Apellido (año)» y parentéticas «(Apellido, año)»; «y» para dos autores; «et al.» desde la primera cita para tres o más |
| **T9** | Correspondencia cita‑referencia | Toda cita del capítulo tiene entrada en `referencias.md` y toda entrada usada se cita |
| **T10** | Referencias pendientes marcadas | Ninguna referencia en estado «pendiente» se cita sin la marca «[verificación pendiente]» |

### Redacción

| Código | Criterio | Qué mira el tutor |
|---|---|---|
| **T11** | Voz impersonal | Sin primera persona («nosotros», «nuestro», «hemos», «realizamos»); pasado para lo hecho, presente para lo que el sistema hace |
| **T12** | Terminología precisa | BIM‑5D y sombra digital; «gemelo digital» solo en su delimitación conceptual o en lo que no comprende la investigación |
| **T13** | Párrafos claros | Cada párrafo desarrolla una idea central; las transiciones entre secciones son explícitas; sin repetir textos de otros documentos del repositorio |

### Delimitación

| Código | Criterio | Qué mira el tutor |
|---|---|---|
| **T14** | Lo excluido está declarado | Gemelo digital en sentido estricto, digitalización automática de planos, evaluación financiera del proyecto, generalización estadística y validación con presupuestos reales se declaran fuera de alcance o como limitación |

## Plantilla de acta

Cada acta se guarda como `docs/tesis/revisiones/<sprint>-capitulo-<n>.md`:

```markdown
# Acta de revisión — Capítulo <n> (<sprint>)

**Fecha:** AAAA-MM-DD · **Versión revisada:** <commit> · **Tutor:** <rol> · **Tesista:** <rol>

| Código | Veredicto | Observación del tutor | Respuesta del tesista |
|---|---|---|---|
| T1 | cumple / cumple con observaciones / no cumple | ... | ... |
| ... | | | |
| T14 | | | |

**Resultado:** aprobado en revisión / requiere nueva revisión.
```
