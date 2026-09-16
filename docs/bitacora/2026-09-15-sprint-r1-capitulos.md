# Bitácora — Sprint R1 (capítulos I y II del trabajo de grado)

**Fecha:** 2026‑09‑15 · **Rama:** `inc/tesis-cap1-2` (worktree `.claude/worktrees/redaccion-cap1-2`)
· **Base:** etiqueta `r-base` (`fd1b706`, punta de `inc/PLAN-asistente`) ·
**Spec:** [2026-09-15-sprint-r1-capitulos-design.md](../superpowers/specs/2026-09-15-sprint-r1-capitulos-design.md)
· **Plan:** [2026-09-15-sprint-r1-capitulos.md](../superpowers/plans/2026-09-15-sprint-r1-capitulos.md)

## Objetivo

Redactar los capítulos I (El problema) y II (Marco teórico) con los roles de tesista y tutor: el
tesista redacta, el tutor revisa con la [lista de cotejo](../tesis/rubrica_tutor.md) T1–T14 y deja
un acta, y el tesista corrige y responde cada observación en ella.

**Resultado:** ambos capítulos en borrador completo y aprobados en revisión, sin criterios en
«no cumple» ([acta I](../tesis/revisiones/R1-capitulo-1.md),
[acta II](../tesis/revisiones/R1-capitulo-2.md)). Lista de referencias APA 7 con 36 entradas
citadas: 22 verificadas y 14 pendientes marcadas. Meta de redacción 12/12, suite de 544 pruebas en
verde con `-W error`, ruff limpio y `core/` sin cambios respecto de `r-base`.

## Decisiones del usuario

Detalladas en la spec §2.

| Código | Decisión |
|---|---|
| DR-1 | Todos los APU y presupuestos del repositorio son ejercicios académicos ficticios (clínica y ARENAZA) y se presentan como casos didácticos |
| DR-2 | Objetivos en dos variantes: A con OE7 (extensibilidad multidominio) y B sin él |
| DR-3 | Citación APA 7.ª edición, con una única lista en `docs/tesis/referencias.md` |
| DR-4 | La sesión de redacción pausada del 2026‑09‑01 se commiteó en la rama (`14d253b`) y `main` quedó limpio |
| DR-5 | Roles de tesista y tutor, con lista de cotejo T1–T14 y actas en `docs/tesis/revisiones/` |

## Desviación del orden de escritura

El [plan de redacción](../tesis/plan_redaccion.md) recomendaba IV → V → III → II → I. Empezar por
I y II fue decisión del usuario. Consecuencia registrada: dos remisiones apuntan a capítulos aún no
escritos. La justificación de la clase 3 de AACE con la madurez del caso va al capítulo III, y la
extensibilidad como resultado complementario (variante B), al capítulo V.

## Errata sobre la naturaleza de los datos

Al aprobar la spec, el usuario aclaró que los APU del repositorio «son ficticios, han sido
ejercicios de clases y no representan un valor real», ARENAZA incluido. Una búsqueda encontró 92
afirmaciones que presentaban esos datos como reales, en 25 archivos.

- **R1.0:** `CLAUDE.md` §1 pasó a ser la fuente única de la «Naturaleza de los datos». Se
  corrigieron `docs/linea_base.md`, `docs/tesis/capitulos/README.md`,
  `data/telecom/fuentes/README.md` (con nota de errata), `data/samples/README.md` y
  `docs/tesis/plan_redaccion.md`.
- **Pendiente como sesión propia:** el resto (ERS, planes, manuales, textos de
  `scripts/generar_resultados_ml.py`, spec del asistente y docstrings).
- Las bitácoras históricas no se reescriben: registran lo que se sabía en su fecha, y esta errata
  las corrige.

## Sesiones y commits

| Sesión | Commit | Contenido |
|---|---|---|
| — | `14d253b` | sesión de redacción pausada (DR-4) |
| — | `d108446`, `250cd86` | spec y plan del sprint |
| R1.0 | `0505597` | naturaleza de los datos, lista de cotejo, `referencias.md`, meta R1–R12 con pruebas |
| — | `65fe4e7` | fix: la meta detecta la primera persona en cualquier verbo |
| R1.1 | `df01b5a` | capítulo I: planteamiento y formulación |
| R1.2 | `8c26b19` | capítulo I: objetivos en dos variantes, justificación y delimitación |
| R1.3 | `35f2339` | acta del capítulo I |
| R1.4 | `1c6228e`, `fc51278` | referencias verificadas, ajustes del capítulo I y antecedentes del capítulo II |
| — | `36d4fb2` | fix: las citas de la meta no cruzan saltos de línea |
| R1.5 | `d2af176` | capítulo II: bases teóricas |
| R1.6 | `ca2353a` | capítulo II: bases normativas y definición de términos |
| R1.7 | este commit | acta del capítulo II con sus correcciones, tablero, bitácora |

## Verificación de referencias

**Método.** Se usó la API pública de Crossref, consultada con un script local con pausas entre
peticiones, y búsquedas web para los resúmenes y las fuentes sin DOI. Hubo tres incidencias:

- Los dos agentes de verificación lanzados en segundo plano fallaron por el límite de gasto de la
  organización (HTTP 429), así que la verificación se hizo directamente.
- La consulta a Crossref desde la herramienta de lectura web estaba bloqueada.
- Crossref respondió 429 en ráfagas; se reintentó con pausas.

**Criterio.** Una entrada es «verificada» solo si se confirmaron los metadatos **y** se contrastó
toda afirmación que los capítulos le atribuyen. Lo demás se cita con «[verificación pendiente]».

**Afirmaciones que excedían su fuente** (reescritas o retiradas):
- Wahab y Wang no documentan diferencias de tiempo y exactitud.
- La documentación de los programas de presupuesto no afirma que «no pueden comprobar» cantidades
  contra la geometría.
- «Obstáculo principal» en Pishdad y Onungwa.
- La asignación de la clase 3 de AACE por el mero uso de un modelo tridimensional.
- Un alcance de la norma COVENIN que no figura en su título.

**Cifras del estado del arte que no se citan** porque no se localizó la fuente primaria: el 50–80 %
del tiempo del estimador atribuido a Franco et al. (2015) y la exactitud de BERT atribuida a Moon et
al.

**Metadatos corregidos:**
- Khosakitchalert et al.: año 2019.
- Pishdad y Onungwa: dos autores, 29, 525–548.
- Wahab y Wang: 2021.
- Huang y Hsieh: volumen 118.
- Ma et al.: páginas.
- Moon et al.: la revista es *Advanced Engineering Informatics*.
- IP‑3 Software como autor.
- COVENIN 2000‑2: año 1999.
- AACE International: 2020a (56R‑08) y 2020b (18R‑97).

**Revisión del capítulo II (R1.7).** Se incorporaron Eastman et al. (2009) y Solihin y Eastman
(2015), verificadas, como base teórica de la verificación automática (OE5). Franco et al. y la
tesis de la PUCP, no citadas, salieron de la lista APA a «Consultadas y no citadas».

**Pendientes (14):**
- AACE International (2020a): rango de la clase 3 en la 56R‑08.
- BIMForum (2024).
- COVENIN (1999): título exacto y asignación de unidades.
- Chacón y Cuervo (s.f.).
- Colegio de Ingenieros de Venezuela (2018 y s.f.).
- Convención colectiva: vigencia y formato de documento legal.
- Garnica (s.f.).
- Lulo Software (s.f.).
- Ma et al. (2011).
- Miranda Miranda (s.f.).
- Quiñones y Uzcátegui (2023).
- Rozo-Martínez y Tumay-Gamba (2024).
- Tayefeh Hashemi et al. (2020).

## Defectos de la meta hallados con pruebas negativas sobre documentos reales

Cada sesión alteró a propósito el capítulo real (quitar una referencia, una marca o una sección, o
insertar primera persona o «gemelo digital») y comprobó que la meta fallara. Así aparecieron cuatro
defectos que las pruebas sintéticas no mostraban. Cada uno se corrigió con una prueba que primero
falló:

| Sesión | Defecto | Corrección |
|---|---|---|
| R1.1 | La primera persona se detectaba con una lista cerrada: «empleamos» pasaba | detección de cualquier verbo en primera persona del plural, con exclusión de sustantivos como «tramos» (`65fe4e7`) |
| R1.4 | Los apellidos con guion (IP‑3, Rozo-Martínez) no encontraban su referencia | apellidos separados por espacios y guiones |
| R1.4 | La secuencia de nombres de una cita cruzaba saltos de línea («BIM\n\nMa et al.») | solo espacios y tabuladores entre nombres (`36d4fb2`) |
| R1.7 | R5 rechazaba la primera cita APA 7 de un autor corporativo con su abreviatura entre corchetes | los corchetes separan palabras como los espacios |

## Hallazgos para el tutor académico

- **D3:** variante A o B de los objetivos. Si es A, falta la base teórica de OE7 (acta II, T2).
- **Acta I, T2:** OE1 y OE3 atienden la pregunta principal y no una secundaria.
- **Acta I, T3:** OE4 es menos medible que los demás, y el objetivo general de la variante A es
  extenso.
- **AACE 18R‑97 o 56R‑08 (acta II, T4):**
  - El caso es de edificación, y la 56R‑08 es la práctica de ese sector.
  - Si se adopta, el cambio alcanza a la ERS (RF‑29 y el glosario) y al rango de `ml/prediction`, no
    a `core/`.
  - `CLAUDE.md` §8.1 fija «clase 3 de AACE» sin nombrar la práctica.
- **D4:** fuente del FCAS. Sigue como «parámetro del caso de estudio».

## Pendientes

1. Completar las 14 referencias pendientes.
2. Sesión de limpieza de las afirmaciones «real» restantes (ver Errata).
3. Justificar la clase 3 con la madurez del caso en el capítulo III.
4. Decisiones del tutor académico: D3, D4, AACE, T2 y T3 del capítulo I.
5. Fusión de las ramas apiladas (#1 → #2 → #3 → esta), a cargo del usuario.
