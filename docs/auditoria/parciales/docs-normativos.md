# Auditoría parcial — capa `docs` (documentos normativos)

Commit auditado: `cc2243c`. `HEAD` (`3b7645e`) solo difiere en `docs/auditoria/2026-09-inventario.md`,
que queda fuera del alcance, así que las líneas citadas valen para los dos. Criterios: spec
`docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md` §4, `CLAUDE.md` y
`docs/metodologia.md` §5.1. Las decisiones D1–D9 y las salvedades de `docs/dossier_g0.md` §4 cuentan
como riesgo ya rastreado. Cuando una fila las toca, solo reporta la incoherencia entre documentos, no
la decisión misma.

## 1. Archivos revisados (22 de 22)

CLAUDE.md
PLAN_ASISTENTE.md
PLAN_CIERRE.md
PLAN_DESARROLLO.md
PLAN_MULTIDOMINIO.md
PLAN_PROTOTIPO.md
PLAN_UI.md
README.md
docs/ERS.md
docs/README.md
docs/arquitectura.md
docs/calidad_iso25010.md
docs/dossier_g0.md
docs/guion_prueba_arenia.md
docs/linea_base.md
docs/manual_tecnico.md
docs/manual_usuario.md
docs/metodologia.md
docs/modelo_datos.md
docs/plan_pruebas.md
docs/protocolo_precios.md
docs/resultados_ml.md

## 2. Hallazgos

| ID provisional | capa | principio | severidad | evidencia (archivo:línea) | hallazgo | corrección propuesta | fase destino |
|---|---|---|---|---|---|---|---|
| docs-normativos-01 | docs (cruza: tests, core) | trazabilidad | importante | docs/ERS.md:465-466; docs/plan_pruebas.md:146-147; tests/unit/test_reglas_civil.py:76-218 (12 pruebas, ninguna cambia el ancho); tests/unit/test_budget.py:79-222 (10 pruebas, ninguna suma diferenciales); `grep -r diferencial tests/` sin resultados | RF‑19 (sensibilidad al ancho) y RF‑20 (diferencial por partida) figuran «verde» con criterios que citan pruebas inexistentes | escribir las dos pruebas contra la función que realiza cada comportamiento; si RF‑20 no tiene implementación, declararlo sin cumplir. Mientras tanto, marcar ambos «sin prueba» en ERS §3.2/§4 y en plan_pruebas §8 | C1 |
| docs-normativos-02 | docs | coherencia documental | importante | docs/ERS.md:462 y :554 (RF‑16 «satisfecho por UC‑10») frente a docs/ERS.md:548; docs/plan_pruebas.md:144 y :170-173; docs/calidad_iso25010.md:27-29 y :150; docs/manual_tecnico.md:246 («persistencia pendiente», «parcial») | RF‑16 tiene dos estados contradictorios dentro de la ERS (filas UC‑10 y UC‑03 de la matriz) y entre la ERS y el plan de pruebas | fijar un único estado de RF‑16 y propagarlo; no reabre D5, que sigue decidiendo el alcance | C4 |
| docs-normativos-03 | docs (cruza: adapters) | coherencia documental | importante | docs/ERS.md:408, :450, :531, :545; docs/arquitectura.md:98, :619, :864, :881 (FastAPI «previsto en F.1»), diagrama :872-905 («tanquilla.ifc: PREVISTO», «G1 abierta») frente a adapters/civil/ifc.py:49, data/samples/tanquilla.ifc, tests/unit/test_adapter_civil_ifc.py y docs/plan_pruebas.md:51-54, :135, :213; docs/calidad_iso25010.md:139-144 | ERS y arquitectura dicen que la extracción IFC y `tanquilla.ifc` están pendientes y que G1 sigue abierta. En realidad existen `AdaptadorCivilIFC`, la muestra y su prueba, y el plan de pruebas y la evaluación de calidad dan G1 por cruzada con salvedad (RNF‑09 parcial) | pasar ERS §2.5, RF‑04, RNF‑09 y la matriz UC‑01, y arquitectura §1, §2.3 (añadir `AdaptadorCivilIFC`) y §5, al estado «G1 cruzada con salvedad»; la salvedad de dossier §4 no se reabre | C4 |
| docs-normativos-04 | docs | coherencia documental | importante | docs/arquitectura.md:46-82 y :96-105 (sin UC‑10/11/12; UC‑02 «en curso», UC‑03, UC‑07 y UC‑08 «pendiente»); :718 («Sesión I1, en curso»); :832 (a `core.budget` le faltan `actualizar_precios`, `generar_escenario` y `comparar_escenarios`); :836 (`normalizar`, `detectar_anomalias` y `predecir_precio` no existen en `ml/`: ml/normalization/normalizador.py:68, ml/anomaly/detector.py:83,103, ml/prediction/reglas.py:94,152); :837 («los ocho casos de uso») | La vista de casos de uso y la vista de desarrollo, entregables de G0, describen un sistema anterior a I1. El documento dice haber copiado sus firmas de los módulos (:6-7), pero nombra funciones que no existen | regenerar §1, §3.2 y §4 contra el código actual | C4 |
| docs-normativos-05 | docs (cruza: ui) | coherencia documental | importante | docs/ERS.md:421-423 («interfaz Streamlit con los once casos de uso»); docs/manual_usuario.md:91-105 (nueve páginas; ninguna para UC‑04, UC‑06 ni UC‑07), :143 (UC‑06 solo por API), :151 (UC‑07 solo por script); docs/calidad_iso25010.md:30-32 («la interfaz cumple lo que la ERS §3.1 promete») | La ERS promete en la interfaz once casos de uso que el producto no ofrece ahí. La evaluación de calidad lo da por cumplido | declarar en ERS §3.1 qué capa realiza cada UC (UI, API o script) y retirar la afirmación de calidad; no se agrega ninguna pantalla (spec §2) | C4 |
| docs-normativos-06 | docs | coherencia documental | importante | docs/plan_pruebas.md:32 («13 endpoints»; api/rutas define 18), :128 (392), :216-246 (479 pruebas del 2026‑09‑14; «`core/` tiene las mismas 1 740 líneas», anterior al cambio de `core/` de P1); docs/calidad_iso25010.md:47, :67, :120, :151 (395 y 490); docs/dossier_g0.md:32 (395); README.md:42 (alpha 0.1); `tests/` hoy tiene 562 funciones `test_` sin parametrizar | Las cifras de suite, cobertura y API son contradictorias entre documentos y están desfasadas. Solo la nota de vigencia de calidad (:8-18) lo reconoce; plan_pruebas §10, que calidad nombra como fuente única, no lo hace | volver a medir sobre una corrida de CI, registrarla solo en plan_pruebas §10 y enlazarla desde los demás documentos (metodologia §6, «La CI es la fuente de verdad de las cifras») | C4 |
| docs-normativos-07 | docs | DRY | importante | docs/ERS.md:447-488 (criterio con prueba y estado), docs/ERS.md:543-556 (matriz), docs/plan_pruebas.md:130-168, README.md:44-59; docs/metodologia.md:164-175 (§5.1 no asigna fuente a RF→prueba) | La correspondencia RF → prueba → estado está copiada en cuatro lugares y ya diverge (RF‑16, fila 02; RF‑04, fila 03). Un solo cambio de estado obliga a editar cuatro documentos | declarar en §5.1 a plan_pruebas §8 como fuente única de RF→prueba→estado: la ERS conserva el criterio sin estado y enlaza, y el README enlaza en lugar de copiar | C4 |
| docs-normativos-08 | docs | trazabilidad | importante | docs/plan_pruebas.md:181-199 (matriz por paso solo de UC‑12); docs/metodologia.md:123-126 (DoD: cada paso y cada flujo alternativo cita su prueba); docs/ERS.md:136-145, :210-215 (p. ej. UC‑01 3a, 3b y 6a; UC‑04 2b, sin prueba citada) | UC‑01 a UC‑11 no tienen matriz por paso: los pasos y flujos alternativos no citan ninguna prueba ni caso manual | ampliar plan_pruebas §8 a todos los UC (condición F5 de la spec) y marcar como hallazgo cada paso sin prueba | C4 |
| docs-normativos-09 | docs | coherencia documental | menor | docs/plan_pruebas.md:49-50; docs/dossier_g0.md:196; docs/manual_tecnico.md:246-248 («Linux para RNF‑07» pendiente) frente a docs/plan_pruebas.md:211 y docs/calidad_iso25010.md:117-125 (cumple por CI) | RNF‑07 en Linux figura como «pendiente» en tres lugares y como «cumple» en otros dos | retirar las menciones de pendiente; en dossier §4, una nota de vigencia | C4 |
| docs-normativos-10 | docs | coherencia documental (CLAUDE.md §6) | menor | CLAUDE.md:173 (`scripts/` solo lista seed.py; hay 23 scripts), :174-176 (`data/` omite `precios/`, `civil/`, `telecom/`, `industrial/`, `sistemas/` y las subcarpetas de `samples/`), :179 («costing (rojo hasta I0.3)»), :181 (`docs/` omite `auditoria/`, `superpowers/` y ocho documentos), :238-239 (estado esperado previo a I0.3) | El árbol de §6, fuente única de la estructura según metodologia §5.1, no coincide con el repositorio | actualizar el árbol y pasar a tiempo pasado el estado esperado anterior a I0.3 | C4 |
| docs-normativos-11 | docs | coherencia documental | menor | README.md:31-33 (UI «mínima: UC‑02»), :64-71 (ml «pendientes de la compuerta G2», api «Fase F», scripts: dos); docs/README.md:3-20 (índice sin PLAN_CIERRE, PLAN_UI, PLAN_PROTOTIPO, PLAN_ASISTENTE, guion_prueba_arenia.md ni protocolo_precios.md), :17 («D1–D8»), :20 (PLAN_MULTIDOMINIO «por ejecutar», aunque cerró 11/11 según PLAN_PROTOTIPO.md:3); docs/manual_tecnico.md:191-206 (tabla de scripts sin meta_datos, meta_redaccion ni meta_asistente) | El README raíz y el índice de la documentación están desfasados e incompletos | actualizar ambos índices y la tabla de scripts | C4 |
| docs-normativos-12 | docs | coherencia documental | menor | CLAUDE.md:137; docs/arquitectura.md:109-145 (§2.1 «definitivo») frente a core/contracts/apu.py:69, :94 | La tabla de contratos de CLAUDE §5 y el diagrama de contratos omiten `ModalidadManoObra` y `LineaManoObra.modalidad`, ya implementados. No reabre D9 | añadirlos a los dos documentos | C4 |
| docs-normativos-13 | docs (cruza: core, adapters) | DRY | menor | docs/arquitectura.md:930 (ADR 8) y :944 (§6.1: evaluador duplicado «núcleo / adaptador civil»); docs/manual_tecnico.md:95-96 (un `evaluador.py` por adaptador) frente a adapters/{civil,telecom,industrial,sistemas}/evaluador.py | La arquitectura declara dos copias del evaluador y hay cinco. El manual técnico enseña a crear otra por dominio | alinear ADR 8, §6.1 y la guía del manual con la corrección de código que se decida en C1/C2 (spec §4, «Hallazgos que cruzan capas») | C4 |
| docs-normativos-14 | docs (cruza: ui, api) | SOLID‑O (declaración) | menor | docs/manual_tecnico.md:137-139; ui/paginas/elaborar.py:46-48; api/rutas/computos.py:31-54; docs/arquitectura.md §4 (:770-854, sin mención) | Los puntos de composición que enumeran dominios solo se declaran en el manual técnico. El criterio O de la spec §4 exige declararlos en arquitectura.md | declararlos en arquitectura §4 (despacho de `elaborar.py`, de `computos.py` y los sembradores por dominio) | C4 |
| docs-normativos-15 | docs | datos ficticios (CLAUDE.md §1) | menor | docs/ERS.md:453 («el caso real cerraba en 99,30 %»); docs/protocolo_precios.md:117 («proviene de los APU reales del caso»; «Pendiente cita normativa», cuando D4 ya verificó que no existe, docs/dossier_g0.md:82-94) | Dos documentos llaman «real» al caso didáctico, y el protocolo no recoge el resultado de la verificación de D4 | escribir «caso didáctico» y enlazar la actualización de D4 | C4 |
| docs-normativos-16 | docs | coherencia documental | menor | docs/modelo_datos.md:3 («aprobado en la Sesión 0.2») frente a docs/README.md:9 y docs/ERS.md:5 («pendiente de revisión del tutor (G0)»); docs/modelo_datos.md:427-438 (cobertura de «ocho casos de uso», sin UC‑10/11/12) | El modelo de datos se declara aprobado mientras G0 sigue pendiente, y su cobertura por UC está desfasada | «completo, pendiente de G0»; añadir UC‑10, UC‑11 (composición y rendimiento con condiciones) y UC‑12 | C4 |
| docs-normativos-17 | docs | coherencia documental | menor | docs/metodologia.md:238 (indicador 3 nace en «Fase 6»); docs/calidad_iso25010.md:76 y docs/plan_pruebas.md:44 (RNF‑04 «en la Fase 6») frente a PLAN_DESARROLLO.md:517-519 (Fase 6 completa) y PLAN_CIERRE.md:31-32 (fase Med) | Las mediciones pendientes siguen asignadas a una fase ya cerrada | reasignarlas a Med con enlace a PLAN_CIERRE | C4 |
| docs-normativos-18 | docs | coherencia documental | menor | docs/ERS.md:7 («al menos 23 RF») frente a PLAN_DESARROLLO.md:79 («al menos 20 RF»); docs/dossier_g0.md:4 («las ocho decisiones») frente a D1–D9 (:44-186) | El criterio de cierre de la Sesión 0.1 y el recuento de decisiones del dossier no cuadran | unificar el criterio citando el PLAN; decir «nueve decisiones» | C4 |
| docs-normativos-19 | docs | coherencia documental | menor | docs/linea_base.md:81 (hallazgo 8 = unidad del encofrado) frente a docs/dossier_g0.md:56 («octavo defecto» = insumo con dos precios); docs/linea_base.md:94-96 («hasta entonces solo están corregidos encofrado y concreto», con I3.2 cerrada) | Dos defectos distintos llevan el número 8, y queda un estado previo a I3.2 | renumerar o nombrar el defecto de D2 sin ordinal; pasar el párrafo a tiempo pasado | C4 |
| docs-normativos-20 | docs (cruza: scripts) | coherencia documental | menor | docs/guion_prueba_arenia.md:57 (`seed_demo.py --reiniciar` sobre `data/apu.db` por defecto), :59-63 (la base aparte queda como variante 2b) | El camino principal del guion borra la base de trabajo por defecto. La variante segura queda como alternativa | hacer de `--db data/prueba_arenia.db` el camino principal (coherente con la salvaguarda de `data/apu.db` de C1) | C4 |
| docs-normativos-21 | docs | coherencia documental | menor | PLAN_ASISTENTE.md:1-20 frente a docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md:60 | PLAN_ASISTENTE no dice que quedó fuera del límite del proyecto (trabajo futuro) | añadir una nota de vigencia que enlace la spec §2 | C4 |
| docs-normativos-22 | docs | coherencia documental | menor | docs/calidad_iso25010.md:43 («con los tres RF no esenciales declarados arriba») frente a :25-29 (solo se declara RF‑16, que es esencial, ERS.md:462) | El veredicto cita tres RF que el texto no declara | corregir la frase al actualizar las cifras (fila 06) | C4 |

## 3. Principios sin hallazgos

- **Enlaces rotos:** sin hallazgos. Los 233 enlaces relativos de los 22 archivos resuelven, anclas
  incluidas. Las rutas entre comillas invertidas que no existen son artefactos futuros declarados
  (U1, PLAN_ASISTENTE) o bases generadas (`data/*.db`).
- **`Decimal` (principio 3), función pura (principio 4), informe siempre (principio 7), contratos
  inmutables (§5):** sin hallazgos. Ningún documento de la capa contradice estos principios; el código
  que los realiza es de otras capas.
- **SOLID S, L, I y D:** sin hallazgos en la capa `docs`. La única observación SOLID es la
  declaración O (fila 14).
- **Pruebas** (aserciones vacías, aislamiento, orden, red): sin hallazgos atribuibles a la capa
  `docs`. La ausencia de pruebas citadas se reporta como trazabilidad (filas 01 y 08).
