# Dossier de la compuerta G0 — revisión del tutor

Paquete único para la reunión de G0: qué documentos se someten a aprobación, en qué estado está
el sistema que los respalda y, sobre todo, **las ocho decisiones acumuladas** que las bitácoras
fueron elevando a esta compuerta, cada una con su contexto, su impacto y una recomendación.
Preparado el 2026‑08‑31, con el PLAN de desarrollo completo (20 de 20 sesiones).

## 1. Qué aprueba G0

Los tres entregables documentales de la Fase 0 ([CLAUDE.md §8.3](../CLAUDE.md)):

| Documento | Norma | Estado |
|---|---|---|
| [ERS.md](ERS.md) | IEEE 830 | completo; 31 RF y 9 RNF con matriz de trazabilidad al día |
| [modelo_datos.md](modelo_datos.md) | ER + decisiones | completo; implementado y probado desde I0.4 |
| [arquitectura.md](arquitectura.md) | vistas 4+1 | completo; la hipótesis central verificada empíricamente |

Los tres se escribieron en la Fase 0 y **el sistema completo se construyó después sobre ellos sin
que ninguna sesión los invalidara**: las actualizaciones posteriores fueron de trazabilidad
(marcar RF como cubiertos), nunca de fondo. Esa estabilidad es el mejor argumento a favor de
aprobarlos como están.

## 2. El sistema que los respalda, en cifras

Detalle y evidencia reproducible en [plan_pruebas.md](plan_pruebas.md) y
[calidad_iso25010.md](calidad_iso25010.md); aquí solo el resumen para la reunión:

- **395 pruebas en verde** con advertencias como errores; cobertura de `core/` 98,05 %.
- **7 de 7 inconsistencias** de la línea base detectadas (indicador 1); exactitud frente a la
  línea base corregida: desviación 0,00 % (indicador 2).
- **Núcleo intacto**: `git diff --stat core/` vacío tras los adaptadores telecom, industrial y
  sistemas (indicador 4), vigilado por 65 pruebas de arquitectura en cada corrida.
- **Módulo predictivo**: técnica de reglas por compuerta G2 (< 50 registros por dominio), con
  MAPE 12,46 %, RMSE 5,10 USD, R² 0,9974 (indicador 5; [resultados_ml.md](resultados_ml.md)).
- **Desempeño**: 100 partidas revaloradas en 1,17 s (meta < 5 s).
- Los **ocho casos de uso** operan de extremo a extremo (UI, API y núcleo).

## 3. Decisiones que esperan la validación del tutor

### D1. Regla R7 — `ConciliacionPresupuestoPlan`

Las Bases del anteproyecto listan **cinco** reglas de verificación; el diseño implementó siete.
R6 (criterio de depreciación) reproduce el hallazgo 7 del caso y no ha generado objeción; R7 es
la adición de fondo: comprueba que cada monto del plan de trabajo coincide con el de su partida.
Su valor empírico está demostrado — sobre el caso didáctico detecta las cinco discrepancias día a día
que explican la brecha de 11,11 USD del hallazgo 3 (bitácora de I4, «hallazgo adicional 9»).
**Si se rechaza:** cambian RF‑21/RF‑22, el indicador 1 pasa a contarse sobre seis reglas y la
raíz del hallazgo 3 queda sin regla que la explique. **Recomendación: aprobar.**

### D2. Regla candidata R8 — «precio uniforme del insumo»

Al persistir la línea base apareció un **octavo defecto** del caso: un mismo insumo con dos
precios distintos en la misma lista y fecha (bitácora de 0.2/I0.4; el esquema lo rechaza con
`UNIQUE` y lo carga como variantes para no ocultarlo). La regla propuesta lo reportaría con
severidad ADVERTENCIA. No cuenta para el indicador 1 (que queda en 7 de 7). **Opciones:**
aprobarla como octava regla (sesión corta, mismo patrón que R1–R7) o dejarla como hallazgo
documentado del modelo de datos. **Recomendación: aprobarla** — ya existe la evidencia y el
mecanismo (`ResumenCarga.variantes`) que la alimentaría.

### D3. Extensibilidad multidominio: ¿OE7 o resultado complementario?

La hipótesis central (núcleo intacto al agregar dominios) **no figura como objetivo en las
Bases**. Las dos opciones documentadas en [tesis/esqueleto_tesis.md §3](tesis/esqueleto_tesis.md):
(1) incorporarla como OE7 y ajustar título y alcance, o (2) mantenerla como resultado
complementario de OE3 y presentar los adaptadores como evidencia de mantenibilidad en el
capítulo V. Hay que decidirla **antes del anteproyecto formal**. La evidencia empírica ya existe
en ambos casos. **Recomendación: opción 1 (OE7)** — es el aporte más distintivo del trabajo y ya
está demostrado; dejarlo como nota lo subvendería.

### D4. Fuente primaria del FCAS (600 %)

El factor de costos asociados al salario (6,00) proviene de los APU del caso didáctico
(`data/linea_base/APUS_CLINICA.pdf`); falta la **cita normativa** venezolana (LOTTT y
contratación colectiva vigente) que lo respalde en el capítulo del marco teórico. No afecta al
software (es un parámetro, no una constante del motor). **Se pide al tutor:** orientación sobre
la fuente citable, o su aval para declararlo «parámetro del caso de estudio».

### D5. Flujo de creación de partidas (RF‑16 y familia)

El hallazgo más recurrente del proyecto (I2, I6, F.2): la persistencia de RF‑16 (guardar una
partida nueva creada desde una propuesta similar) espera un **flujo de creación de partidas**
que ningún caso de uso implementado ofrece — hoy las partidas nacen del seed o de la carga de
composiciones. **Opciones:** implementarlo como incremento corto post‑PLAN, o acotar RF‑16 en la
ERS a la precarga (que ya funciona) y declarar la creación como trabajo futuro.
**Recomendación:** decidirlo aquí para que la ERS aprobada no prometa de más.

### D6. Postcondición de UC‑08 («escenarios guardados»)

UC‑08 está implementado en las tres capas y **nada se persiste por diseño**: promover un
escenario es exactamente UC‑02 con la lista nueva (decisión documentada en la bitácora del
cierre de UC‑08). La postcondición del caso de uso en la ERS dice «escenarios guardados con sus
parámetros» y hoy se satisface en memoria durante la comparación. **Se pide:** validar la
decisión (y de paso ajustar la redacción de la postcondición), o pedir persistencia de
escenarios como extensión. **Recomendación: validar la decisión actual.**

### D7. Alcance de la meta M9 («rama de adaptador»)

La meta automatizada M9 del sprint alpha define «rama de adaptador» como la que agrega archivos
bajo `adapters/` o `ml/` y exige que no toque `core/`. Es la formalización operativa de la
hipótesis; el alcance de esa definición quedó por validar (bitácora del sprint alpha).
**Recomendación: aprobar la definición tal como está** — ya vigiló ocho ramas sin falsos
positivos.

### D8. Declaración «BIM‑5D», no «gemelo digital»

Riesgo documentado en [metodologia.md §9](metodologia.md): el término «gemelo digital» sería
impreciso para este sistema (no hay sincronización bidireccional con la obra). ERS y
arquitectura lo declaran como BIM‑5D (a lo sumo «sombra digital»). **Se pide:** confirmar esa
terminología para el anteproyecto y la defensa.

## 4. Salvedades declaradas (informativas, no requieren decisión)

- **G1 con salvedad:** el adaptador IFC reproduce exacto el cálculo manual (0,224 m³), pero
  contra un modelo generado programáticamente. **Pedido concreto al tutor:** el export IFC 4 del
  mismo modelo desde dos herramientas reales (p. ej. Revit y Bonsai) para cerrar RNF‑09; la
  alternativa tabular ya existe y está documentada.
- **G2 cruzada por degradación:** < 50 registros por dominio → sistema de reglas con análisis de
  sensibilidad, **declarado como limitación**, no como logro ([resultados_ml.md](resultados_ml.md)).
- **RNF‑07:** instalación verificada en Windows; la corrida en Linux sigue pendiente.
- **Fuente ARENAZA inconsistente:** el tubo corrugado mide 80 m en los cómputos y 90 m en el
  presupuesto del mismo documento — candidata a caso de estudio de R7 en telecom (bitácora del
  sprint alpha). Útil para el capítulo de resultados.

## 5. Qué desbloquea G0

Con G0 aprobada: el anteproyecto formal (con la decisión D3 incorporada), la aplicación del
instrumento de RNF‑04 (anexo A) y la redacción de los capítulos sobre
[tesis/esqueleto_tesis.md](tesis/esqueleto_tesis.md) con los indicadores ya medidos.

---

## Anexo A. Instrumento de juicio de expertos (RNF‑04)

**Meta:** ≥ 4/5 en promedio. **Población sugerida:** 3–5 profesionales de costos u obra que no
hayan participado del proyecto. **Procedimiento:** entregar a cada experto el informe de
auditoría del caso de estudio (generado por el sistema, sin edición) y este cuestionario;
sin explicación previa del sistema — eso es exactamente lo que se mide.

Escala: 1 = totalmente en desacuerdo · 3 = neutral · 5 = totalmente de acuerdo.

| # | Afirmación | 1–5 |
|---|---|---|
| 1 | Entendí qué comprueba el informe sin necesitar formación previa sobre el sistema | |
| 2 | La severidad de cada hallazgo (error / advertencia / información) es comprensible y está bien asignada | |
| 3 | El impacto cuantificado (montos y cantidades en juego) me permite dimensionar cada hallazgo | |
| 4 | Las referencias de origen (`origen_id`) me permitirían ubicar la fila del cómputo o del plan que causó el hallazgo | |
| 5 | El orden del informe (severidad descendente) presenta primero lo que más importa | |
| 6 | El lenguaje del informe es apropiado para un profesional de obra (ni críptico ni trivial) | |
| 7 | Con este informe podría decidir qué corregir del presupuesto y en qué orden | |
| 8 | Confiaría en este informe como complemento de una revisión manual | |

Campo abierto: *¿qué le falta o le sobra al informe para serle útil en su trabajo?*

**Registro:** promedio por ítem y global, n de expertos, fecha y versión del informe evaluado;
el resultado se incorpora a [calidad_iso25010.md §4](calidad_iso25010.md) y al capítulo de
resultados.
