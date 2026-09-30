# Auditoría parcial — capa `docs-tesis`

Commit auditado: `cc2243cd5a7efd3b20dc82fe586484a6ef01fea8`. Criterios: spec
`2026-09-23-plan-cierre-tesis-design.md` §4 (únicos principios y severidades
usados). Contexto obligatorio: `NORMAS.md` §1 (naturaleza ficticia de todos los APU) y
`docs/metodologia.md` §5.1 y §8. Las decisiones D1–D9 de `docs/dossier_g0.md` se toman como riesgo ya
rastreado y no se reportan como hallazgo. `docs/tesis/revisiones/2026-09-paquete-tutor.md` se revisó
igual que el resto, por ser nuevo.

## 1. Archivos revisados (10 de 10 de `git ls-files docs/tesis/`)

```
docs/tesis/capitulos/01-el-problema.md
docs/tesis/capitulos/02-marco-teorico.md
docs/tesis/capitulos/README.md
docs/tesis/esqueleto_tesis.md
docs/tesis/plan_redaccion.md
docs/tesis/referencias.md
docs/tesis/revisiones/2026-09-paquete-tutor.md
docs/tesis/revisiones/R1-capitulo-1.md
docs/tesis/revisiones/R1-capitulo-2.md
docs/tesis/rubrica_tutor.md
```

## 2. Hallazgos

| ID provisional | capa | principio | severidad | evidencia archivo:línea | hallazgo | corrección propuesta | fase destino |
|---|---|---|---|---|---|---|---|
| docs-tesis-01 | docs | Coherencia documental (cifras del sistema, `metodologia.md` §5.1) | importante | `docs/tesis/plan_redaccion.md:111` («ERS: 8 UC, 31 RF, 9 RNF») y `:131` («ocho pantallas, ocho UC»), frente a `docs/ERS.md:20` («42 RF») y `:517` («**42**») y `docs/ERS.md:421-422` (once UC: UC‑01 a UC‑08 y UC‑10 a UC‑12) y RNF‑10 en `docs/ERS.md:532` | El guión del capítulo IV (el primero que se va a redactar, `plan_redaccion.md` §2) todavía cita el conteo de la ERS en G0 (31/08): 8 UC, 31 RF, 9 RNF, ocho pantallas. Las Sesiones P0.1 y U0.1 (ya ejecutadas) llevaron la ERS vigente a 42 RF, 10 RNF y once UC (UC‑09 vacante) con diez pantallas (`docs/ERS.md` RF‑39). Quien redacte el capítulo IV con esta guía transcribiría cifras incorrectas a la tesis | Actualizar las dos líneas a los conteos vigentes de `docs/ERS.md` (42 RF, 10 RNF, once UC, diez pantallas), o agregar una nota de vigencia como la que ya recibieron `docs/calidad_iso25010.md` y `docs/dossier_g0.md` el 2026‑09‑23 (`docs/bitacora/2026-09-23-sprint-ui.md`, punto 7) | C4 |
| docs-tesis-02 | docs | Coherencia documental (cifras del sistema) | importante | `docs/tesis/plan_redaccion.md:96`, `:151` y `:195` («395 pruebas», «núcleo 98,05 %») | La tabla de cifras citables (§5, fuente única de la que deben salir las cifras de los capítulos) y el guión de los capítulos III y V siguen citando «395 pruebas» del cierre de UC‑08 (31/08). Los registros posteriores —ya en el propio repositorio— son 479 (`docs/plan_pruebas.md:219`, 14/09), 673 al cerrar el sprint del prototipo y 690 tras su auditoría de rama completa (`docs/bitacora/2026-09-16-sprint-prototipo.md:279`). `docs/calidad_iso25010.md:6-16` ya recibió una nota de vigencia el 2026‑09‑23 declarando obsoleta esta misma cifra; `plan_redaccion.md`, que es la fuente que un redactor de capítulo usaría primero, no la recibió | Actualizar la fila «Suite y cobertura» de §5 con la cifra vigente (o su fuente, la bitácora citada) y propagar el cambio a las dos menciones narrativas (§3, capítulos III y V), siguiendo el mismo patrón de nota de vigencia ya aplicado en `calidad_iso25010.md` | C4 |
| docs-tesis-03 | docs | Coherencia documental / DRY (`metodologia.md` §5.1, fila «fuentes únicas de verdad») | importante | `docs/tesis/plan_redaccion.md:150` («5 cumplen, 1 pendiente, 2 parciales») frente a `docs/calidad_iso25010.md:148-157` (tabla §9 vigente: 6 cumplen — incluida Portabilidad —, 1 pendiente —Usabilidad—, 1 parcial —Compatibilidad—) | El guión del capítulo V reproduce de memoria el resumen de veredictos ISO/IEC 25010 en vez de enlazarlo, y ya no coincide con la fuente única (`calidad_iso25010.md` §9): Portabilidad pasó de «parcial» a «cumple» cuando la CI verificó Linux (14‑15/09), lo que deja hoy 6/1/1 y no 5/1/2 | Corregir la cifra a 6 cumplen, 1 pendiente, 1 parcial, citando `calidad_iso25010.md` §9 en vez de reproducir el conteo | C4 |
| docs-tesis-04 | docs | Coherencia documental (`metodologia.md` §5.1) | importante | `docs/tesis/plan_redaccion.md:158-159` («Limitaciones = las salvedades del dossier §4, con nombre: G1 …, G2 …, RNF‑04 y RNF‑07 pendientes, RF‑16 acotado») frente a `docs/plan_pruebas.md:211` y `docs/calidad_iso25010.md:155` (RNF‑07 / Portabilidad: **cumple**, verificado en Windows y Linux por CI desde el 15/09) | El guión de «Conclusiones y recomendaciones» sigue instruyendo declarar RNF‑07 como limitación pendiente, salvedad que ya se cerró (CI en Linux) después de escrito el guión (31/08). Además omite las dos brechas que sí siguen abiertas hoy: RNF‑09 (parcial, IFC programático) y RNF‑10 (pendiente, CP‑07 en fase Med) | Quitar RNF‑07 de la lista de limitaciones nombradas y añadir RNF‑09 y RNF‑10 (con su fuente, `docs/calidad_iso25010.md` §9), para que el capítulo de conclusiones no repita una brecha ya cerrada ni omita las vigentes | C4 |
| docs-tesis-05 | docs | DRY / Citación T8 (`rubrica_tutor.md`) | menor | `docs/tesis/referencias.md:534` («año con sufijo «b», porque coexiste con la 56R‑08 del mismo autor y año») frente a `:521` (56R‑08 «deja de llevar el sufijo «2020a»: ya no coexisten dos obras del mismo autor y año», porque su año correcto es 2012) | La nota de corrección de la entrada «AACE International (2020)» quedó desactualizada: afirma que necesita el sufijo «b» por compartir año con la 56R‑08, pero la propia entrada de la 56R‑08 (más abajo en el mismo archivo) ya corrigió su año a 2012, con lo que ya no hay dos obras del mismo autor y año. El encabezado y las citas reales del capítulo II (`AACE International, 2020` y `AACE International, 2012`) no usan sufijo y están bien — la inconsistencia es solo la nota interna de `referencias.md`, no lo que llega al texto de la tesis | Borrar o corregir la frase «año con sufijo «b»…» de la entrada de 2020, dejando constancia de que el sufijo dejó de ser necesario cuando se corrigió el año de la 56R‑08 (Sesión R1.7) | C4 |

## 3. Sin hallazgos

- **Datos ficticios presentados como reales.** Los capítulos I y II, el tablero de `capitulos/README.md`
  y `esqueleto_tesis.md` declaran explícitamente el caso de la clínica y el de ARENAZA como ejercicios
  académicos ficticios/didácticos, con la limitación de validación con presupuestos reales declarada en
  cada uno (`01-el-problema.md` §1.1.2, §1.5.2; `02-marco-teorico.md` §2.2.4, §2.3.1). Coincide con el
  criterio T5 de `rubrica_tutor.md`, ya verificado «cumple» en ambas actas de revisión.
- **Referencias: citas sin entrada.** Se contrastó cada cita de `01-el-problema.md` y
  `02-marco-teorico.md` contra `referencias.md`: las 36 entradas de la lista APA están citadas y no se
  encontró ninguna cita sin entrada (coincide con T9, ya corregido en la Sesión R1.7).
- **Referencias: entradas pendientes sin marcar.** Las cuatro entradas en estado «pendiente» (Miranda
  Miranda, Quiñones y Uzcátegui, Chacón y Cuervo, Lulo Software) llevan la marca «[verificación
  pendiente]» en todas sus citas dentro de los capítulos I y II (coincide con T10).
- **Matriz de trazabilidad del esqueleto (§2).** Las filas OE1–OE6, la fila transversal y la nota sobre
  OE7/D3 son consistentes entre sí y con `docs/metodologia.md` §7–§8 (mismos cinco indicadores, mismas
  fases I–VI); no se encontró una fase, sesión o indicador que contradiga otro documento.
- **Estado de las compuertas G1/G2 mencionado en capítulos y guión.** Todas las menciones a G1 y G2 en
  `plan_redaccion.md` y `esqueleto_tesis.md` llevan su salvedad («con su salvedad», «degradación
  declarada», «parcial») y no se encontró ninguna que las presente como cruzadas sin reserva.
- **DRY sobre datos de cálculo (FCAS, bono, administración, utilidad, los cinco APU).** Ninguna cifra de
  `core.contracts.apu.ParametrosCosto` ni de la línea base aparece reescrita con un valor distinto al de
  `tests/fixtures/apu_linea_base.py`; los capítulos y el plan de redacción la enlazan o la citan igual.
- **Contratos `core/contracts/`, motor de costos puro, `Decimal`, informe de auditoría siempre generado,
  SOLID.** No aplican a esta capa: `docs/tesis/` no contiene código.
