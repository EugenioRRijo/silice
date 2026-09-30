# Dossier de la compuerta G0 — revisión del tutor

Paquete único para la reunión de G0: qué documentos se someten a aprobación, en qué estado está
el sistema que los respalda y, sobre todo, **las nueve decisiones acumuladas** que las bitácoras
fueron elevando a esta compuerta, cada una con su contexto, su impacto y una recomendación.
Preparado el 2026‑08‑31, con el PLAN de desarrollo completo (20 de 20 sesiones) y ocho decisiones
(D1–D8); la D9 se agregó en la Sesión P0.1 del sprint del prototipo (2026‑09‑16).

## 1. Qué aprueba G0

Los tres entregables documentales de la Fase 0 ([NORMAS.md §8.3](../NORMAS.md)):

| Documento | Norma | Estado |
|---|---|---|
| [ERS.md](ERS.md) | IEEE 830 | completo; 31 RF y 9 RNF con matriz de trazabilidad al día |
| [modelo_datos.md](modelo_datos.md) | ER + decisiones | completo; implementado y probado desde I0.4 |
| [arquitectura.md](arquitectura.md) | vistas 4+1 | completo; la hipótesis central verificada empíricamente |

*Vigencia (2026‑09‑23):* la fila de la ERS describe el estado en G0 (2026‑08‑31) y no se reescribe;
tras la Sesión U0.1 del sprint de UI ([PLAN_UI.md](../PLAN_UI.md)) la ERS suma UC‑12 y llega a
**42 RF y 10 RNF**.

Los tres se escribieron en la Fase 0 y **el sistema completo se construyó después sobre ellos sin
que ninguna sesión los invalidara**: las actualizaciones posteriores fueron de trazabilidad
(marcar RF como cubiertos), nunca de fondo. Esa estabilidad es el mejor argumento a favor de
aprobarlos como están.

## 2. El sistema que los respalda, en cifras

Detalle y evidencia reproducible en [plan_pruebas.md](plan_pruebas.md) y
[calidad_iso25010.md](calidad_iso25010.md); aquí solo el resumen para la reunión:

- **Suite en verde** con advertencias como errores y 0 omitidas: 395 pruebas y cobertura de
  `core/` 98,05 % al preparar el dossier. La cifra vigente y su corrida de CI están en
  [plan_pruebas.md §10](plan_pruebas.md), su única fuente.
- **7 de 7 inconsistencias** de la línea base detectadas (indicador 1); exactitud frente a la
  línea base corregida: desviación 0,00 % (indicador 2).
- **Núcleo intacto**: `git diff --stat core/` vacío tras los adaptadores telecom, industrial y
  sistemas (indicador 4), vigilado en cada corrida por `tests/unit/test_arquitectura.py`.
- **Módulo predictivo**: técnica de reglas por compuerta G2 (< 50 registros por dominio), con
  MAPE 12,46 %, RMSE 5,10 USD, R² 0,9974 (indicador 5; [resultados_ml.md](resultados_ml.md)).
- **Desempeño**: 100 partidas revaloradas en 1,17 s (meta < 5 s).
- Los **ocho casos de uso** de G0 están implementados, con brechas declaradas: los RF que no están
  en verde, con la causa de cada uno, los enumera el resumen de [plan_pruebas.md §8](plan_pruebas.md),
  su fuente única (entre ellos, la importación del presupuesto de un tercero de UC‑05, INV‑076, y el
  diferencial de UC‑04, no implementado, INV‑011). No todos tienen pantalla: la capa que realiza
  cada uno la declara la [ERS §3.1](ERS.md) (INV‑030).

*Vigencia (2026‑09‑28, fase C4 del cierre):* esta sección decía «los ocho casos de uso operan de
extremo a extremo (UI, API y núcleo)», y no era cierto para UC‑04, UC‑06 y UC‑07, que no tenían
pantalla propia, ni para la importación de UC‑05; se corrigió junto con las cifras, que ahora
remiten a su fuente.

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

Al persistir la línea base apareció **otro defecto** del caso, sin número propio (no es el
hallazgo adicional 8 de [linea_base.md §5](linea_base.md), la unidad del encofrado, ni el 9): un
mismo insumo con dos precios distintos en la misma lista y fecha (bitácora de 0.2/I0.4; el esquema lo rechaza con
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

**Actualización (Sesión P0.1, 2026‑09‑16).** Verificado contra fuente primaria: el FCAS del 600 %
**no tiene fuente normativa publicada**. No lo publican el Colegio de Ingenieros de Venezuela, la
Cámara Venezolana de la Construcción, COVENIN ni MaPreX — y la propia Convención Colectiva de
Trabajo para la Rama de la Industria de la Construcción (Gaceta Oficial N.º 6.752 Extraordinario,
6 de julio de 2023) no menciona el FCAS ni la expresión «costos asociados al salario»
(`docs/bitacora/2026-09-15-referencias-pendientes.md`). Los valores publicados que sí se
encontraron son un rango de **198 % a 293 %** (Chacin, 2008, trabajo de grado de la Universidad
Rafael Urdaneta, `docs/fuentes/Chacin_2008_FCAS_URU.pdf`) y de **78 % a 2 386 %** según qué
cláusulas se incluyan (Dodi Scovino y Salas Caraballo, 2019, trabajo de grado de la Universidad
José Antonio Páez, `docs/fuentes/Dodi_Salas_2019_FCAS_UJAP.pdf`, cálculo dominado por la
hiperinflación de 2018). **Recomendación (se mantiene y se refuerza): declararlo parámetro
configurable de la línea base del caso de estudio, no valor normativo**, citando el rango
publicado en el marco teórico.

**Hallazgo relacionado, a favor de la fórmula vigente del motor.** La Cláusula 20 de la misma
convención colectiva dice que el beneficio que respalda el bono de alimentación *«no tiene
carácter salarial, a ningún efecto legal o contractual»*
(`docs/fuentes/CCT_Construccion_GO_6752_Ext_2023-07-06.txt`, líneas 837‑840). El motor
(`core/costing/motor.py`) ya suma el bono aparte del bloque de sueldos y **no** lo multiplica por
`(1 + fcas)` (ver la fórmula de NORMAS.md §4: `bono × Σ cantidad`, fuera del paréntesis que sí
lleva FCAS). La decisión de diseño resulta estar normativamente respaldada; no requiere cambio.

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

### D9. Modalidad de mano de obra por linea (cambio a un contrato declarado estable)

RF‑34 (`docs/ERS.md`) exige que la modalidad de mano de obra se declare por línea: jornal o
destajo. La verificación contra el contrato
([bitácora de la Sesión P0.1](bitacora/2026-09-16-P0-hallazgo-destajo.md)) confirma que no se
puede expresar hoy: `LineaManoObra` (`core/contracts/apu.py`) solo modela `descripcion`,
`cantidad` y `sueldo`, sin campo que distinga una línea a destajo de una línea a jornal, y
`calcular_apu` (`core/costing/motor.py`) aplica `(1 + fcas)`, suma el bono por obrero y divide
entre el rendimiento a **toda** línea de `composicion.mano_obra` por igual. El destajo no es una
preferencia de interfaz: la LOTTT lo tipifica como forma de estipular el salario (artículo 114,
`docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt`, líneas 2276‑2283: *«se entenderá que el salario
ha sido estipulado por unidad de obra, por pieza o a destajo, cuando se toma en cuenta la obra
realizada por el trabajador o trabajadora, sin usar como medida el tiempo empleado para
ejecutarla»*) y la Convención Colectiva de Trabajo para la Rama de la Industria de la Construcción
la regula para el sector (cláusula 1, `docs/fuentes/CCT_Construccion_GO_6752_Ext_2023-07-06.txt`,
líneas 60‑65: *«es aquel que ejecuta su trabajo por metro, por unidad de obra, por pieza o por
tarea, cuyo salario o pago no podrá ser inferior al previsto en el Tabulador de Oficios y Salarios
que forma parte de esta Convención»*). `LineaManoObra` y `calcular_apu` están en la lista de
contratos congelados de NORMAS.md §5; por eso, en vez de parcharlos en silencio, la sesión P0.1 se
detuvo (NORMAS.md §9) y eleva el hallazgo aquí. No compromete la hipótesis central: una modalidad
salarial no es un dominio (NORMAS.md §1) y `scripts/guardia_nucleo.py` solo falla si un commit
toca `core/` junto con `adapters/` o `ml/`.

**Opciones:** (1) modalidad por línea dentro del contrato — `ModalidadManoObra` (`StrEnum`
`JORNAL`/`DESTAJO`) como campo nuevo, con valor por defecto, en `LineaManoObra`, y `calcular_apu`
separando la suma: jornal sigue la fórmula actual, destajo entra completo sin FCAS ni bono ni
división entre rendimiento; (2) sueldo sintético armado fuera del núcleo, con el precedente de
`scripts/seed_telecom.py` (líneas 81‑100, que despeja el `sueldo` de una `LineaManoObra` sintética
para alcanzar un total conocido) — no aplica aquí porque el destajo no tiene un total que despejar,
es una rama de cálculo distinta que el motor tendría que aplicar de todos modos; (3) no
implementarlo y declararlo limitación del prototipo — descartada porque deja RF‑34 sin cumplir y
bloquea permanentemente el caso de uso que lo motivó; (4) una cuarta categoría `subcontratos`
paralela a materiales/equipos/mano_obra — toca `core/` con más superficie que la opción 1 y
tergiversa la naturaleza jurídica del destajo, que la LOTTT clasifica como forma de estipular el
salario, no como subcontrato civil.

**Recomendación: opción 1.** Es aditiva y retrocompatible: con el valor por defecto
(`ModalidadManoObra.JORNAL`) ninguna composición existente cambia y la línea base
(`tests/fixtures/apu_linea_base.py`) reproduce el mismo precio unitario hasta el último decimal.
A implementar en la Fase P1 del sprint del prototipo (meta P4 de `scripts/meta_prototipo.py`).

**Riesgo declarado (auditoría de rama completa, 2026‑09‑23), sin cambio de código.** La modalidad
vive en la línea (`LineaManoObra.modalidad`), pero el precio vive en el insumo, identificado por
(tipo, descripción, unidad) (`core/catalog/repositorio.py::_resolver_insumo`) — la modalidad no es
parte de esa clave. Un obrero homónimo a jornal y a destajo (misma descripción, mismo tipo
`mano_obra`) comparte insumo, de modo que una actualización masiva de precios (UC‑02) o un
escenario (`core/budget/escenarios.py`, que empareja por `linea.descripcion`, líneas 154 y 166‑180)
le aplicaría el mismo precio a las dos modalidades, aunque una de ellas sea en realidad una tarifa
por unidad de obra y no un sueldo diario. Queda declarado como limitación del prototipo, pendiente
del aval del tutor junto con el resto de esta decisión.

## 4. Salvedades declaradas (informativas, no requieren decisión)

- **G1 con salvedad:** el adaptador IFC reproduce exacto el cálculo manual (0,224 m³), pero
  contra un modelo generado programáticamente. **Pedido concreto al tutor:** el export IFC 4 del
  mismo modelo desde dos herramientas reales (p. ej. Revit y Bonsai) para cerrar RNF‑09; la
  alternativa tabular ya existe y está documentada.
- **G2 cruzada por degradación:** < 50 registros por dominio → sistema de reglas con análisis de
  sensibilidad, **declarado como limitación**, no como logro ([resultados_ml.md](resultados_ml.md)).
- **RNF‑07:** al preparar el dossier, la instalación estaba verificada solo en Windows. *Vigencia
  (2026‑09‑28):* cumple desde el 2026‑09‑15; la integración continua verifica la instalación y la
  suite en Linux y Windows en cada PR ([calidad_iso25010.md §6](calidad_iso25010.md)).
- **Fuente ARENAZA inconsistente:** el tubo corrugado mide 80 m en los cómputos y 90 m en el
  presupuesto del mismo documento — candidata a caso de estudio de R7 en telecom (bitácora del
  sprint alpha). Útil para el capítulo de resultados.

## 5. Qué desbloquea G0

Con G0 aprobada: el anteproyecto formal (con la decisión D3 incorporada) y la redacción de los
capítulos sobre [tesis/esqueleto_tesis.md](tesis/esqueleto_tesis.md) con los indicadores ya
medidos. El instrumento de RNF‑04 (anexo A) ya no espera a G0: se aplica en la fase Med del cierre
([PLAN_CIERRE.md](../PLAN_CIERRE.md)) con su protocolo, [protocolo_rnf04.md](protocolo_rnf04.md).

---

## Anexo A. Instrumento de juicio de expertos (RNF‑04)

**Meta:** ≥ 4/5 en promedio. **Población sugerida:** 3–5 profesionales de costos u obra que no
hayan participado del proyecto. **Procedimiento:** entregar a cada experto el informe de
auditoría del caso de estudio (generado por el sistema, sin edición) y este cuestionario;
sin explicación previa del sistema — eso es exactamente lo que se mide. **Cómo se aplica** (desde
la fase C4 del cierre): [protocolo_rnf04.md](protocolo_rnf04.md) fija el número y el perfil de los
expertos, la versión exacta del informe (commit y huella SHA‑256), el procedimiento y la plantilla
de registro. El protocolo no cambia las ocho afirmaciones de este bloque.

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

### Bloque B. Recorrido de la interfaz (RNF‑10)

Agregado en la Sesión U0.2 de [PLAN_UI.md](../PLAN_UI.md). El cuestionario de arriba es el
**bloque A**: se conserva intacto y sigue siendo el instrumento de RNF‑04. El bloque B lo contesta
la persona que ejecutó el caso CP‑07 de [guion_prueba_arenia.md](guion_prueba_arenia.md), al
terminar y sin el observador mirando. **Su promedio es propio y nunca se promedia con el del
bloque A.** Misma escala: 1 = totalmente en desacuerdo · 3 = neutral · 5 = totalmente de acuerdo.

| # | Afirmación | Vigila | 1–5 |
|---|---|---|---|
| B1 | Al abrir la aplicación entendí para qué sirve y por dónde empezar | D‑1, D‑4 | |
| B2 | Los nombres del menú me dijeron qué hace cada pantalla sin abrirlas | D‑4 | |
| B3 | En todo momento supe sobre qué archivo de datos estaba trabajando | D‑2 | |
| B4 | Cuando no había datos, la aplicación me dijo qué pasaba y cómo salir | D‑3 | |
| B5 | Al terminar una pantalla supe cuál era el paso siguiente | D‑5 | |
| B6 | El orden de las pantallas se parece al orden en que se hace el trabajo | D‑6 | |
| B7 | Volvería a recorrer esto solo, sin que nadie me acompañara | global | |

Los códigos D‑1 a D‑6 son los defectos de orientación de la
spec del recorrido guiado, §1.
B4 solo se contesta en el escenario B de CP‑07 (base vacía); en el escenario A se anota «no aplica»
y el promedio se calcula sobre seis ítems.

Campo abierto: *¿en qué momento no supo qué hacer, y qué le habría ayudado?*

**Registro:** además de los ítems, **tiempo total** (min) y **número de preguntas al observador**;
promedio del bloque B, n, fecha, commit probado y escenario. El resultado se incorpora a
[calidad_iso25010.md §4](calidad_iso25010.md) como medición de RNF‑10.
