# Bitácora — Sesión I4 (las siete reglas de verificación y el informe de auditoría)

**Fecha:** 2026‑08‑29 · **Rama:** `inc/I4-verificacion` · **Compuertas cruzadas:** ninguna
**Indicador de la tesis:** 1 (siete de siete inconsistencias detectadas)

## Objetivo

Implementar `core/verification/`: las siete reglas de NORMAS.md §7 como clases `ReglaVerificacion`,
un informe que se genera siempre, y la prueba de aceptación crítica que reproduce el presupuesto
auditado y comprueba que el sistema detecta **7 de 7** sin que el núcleo conozca ningún dominio.

## Qué se hizo

| Archivo | Contenido |
|---|---|
| `core/verification/directivas.py` | Convención "una clave de `especificaciones` que empieza por `_` es una directiva para el núcleo": `PREFIJO_DIRECTIVA`, `CLAVE_BALANCE`, `CLAVE_TOLERANCIA`, `CLAVE_UNIDAD_ORIGINAL`, `es_directiva`, y el etiquetado de períodos `etiqueta_con_codigos` / `codigos_en_etiqueta` |
| `core/verification/expresiones.py` | Evaluador de AST restringido: `evaluar`, `nombres_de`, `codigos_de`, `sustituir_codigos`, `ExpresionInvalida(ValueError)`, `ParametroFaltante(KeyError)`. Las constantes se convierten con `Decimal(ast.get_source_segment(...))`, nunca vía `float` |
| `core/verification/texto.py` | Único lugar de normalización de texto: `normalizar_texto`, `tokens`, `es_numero`, `pares_numero_unidad`, más `formatear_decimal` (presentación) |
| `core/verification/reglas.py` | R1…R7 y `REGLAS` |
| `core/verification/informe.py` | `InformeAuditoria` (`por_severidad`, `por_regla`, `partida_de`, `cumple`, `a_markdown`) y `auditar(presupuesto, reglas=REGLAS)` |
| `tests/fixtures/computo_auditado.py` | `items_auditados()` y `composiciones_linea_base()` derivados de `apu_linea_base` |
| `tests/fixtures/presupuesto_auditado.py` | `items_con_trazas()`, `presupuesto_con_siete_inconsistencias()` y `presupuesto_corregido()` |
| `tests/unit/test_verification.py` | 63 pruebas: evaluador, texto, directivas, una por regla, informe |
| `tests/integration/test_auditoria_7_de_7.py` | La prueba de aceptación crítica (7/7), los hallazgos 8 y 9 y el presupuesto corregido |

Resultado sobre el presupuesto auditado: **14 hallazgos** (1 CRÍTICO, 12 ERROR, 1 ADVERTENCIA).
`esperadas <= detectadas` y `len(esperadas & detectadas) == 7`.

Commit: `feat(core): sistema de verificacion de consistencia`.

## Decisiones

| Decisión | Motivo |
|---|---|
| El núcleo tiene su propio evaluador de expresiones en vez de reutilizar `adapters/civil/evaluador.py` | `core/` no puede importar `adapters/` (NORMAS.md §2). Ver el hallazgo 1 |
| Las directivas se distinguen por el prefijo `_` en `especificaciones` | Es el único campo de texto libre del contrato; el prefijo permite que R4 (que compara especificaciones con el texto del APU) las ignore sin conocer sus nombres |
| El `impacto` de un hallazgo es siempre una magnitud **no negativa**; el sentido lo llevan `valor_observado` y `valor_esperado` | El brief pide `\|Δ\| × PU` en R1 y R5; aplicar el mismo criterio en R2 y R7 evita que la misma columna del informe signifique cosas distintas según la regla |
| R7 concilia **componentes conexas** del grafo período–partida, no filas sueltas | Una partida puede repartirse en varios períodos (el encofrado ocupa los días 3 y 4) y un período puede cubrir varias partidas |
| R7 no reporta nada si el presupuesto no declara curva | R2 ya lo informa; repetirlo como cinco advertencias "partida sin período" sería ruido |
| R1 advierte (no da error) ante una cantidad MANUAL sin regla, aunque declare `_balance` | El brief lo pide así, y es cierto: el 1,30 m3 del relleno se escribió a mano. Que además exista un balance lo verifica R5, que sí da error |
| El informe redondea a dos decimales solo en las columnas de la tabla; la descripción de cada hallazgo cita el valor exacto | NORMAS.md §2.3 redondea "únicamente al presentar", pero la trazabilidad (§2.6) exige conservar la evidencia sin perder dígitos |
| `partida_por_origen` registra `origen_id -> codigo` y también `codigo -> codigo` | R6 compara APU entre sí y solo puede referenciar códigos de partida, no `origen_id` de ítems. Ver el hallazgo 2 |
| `ExpresionInvalida` y `ParametroFaltante` llevan `# noqa: N818` | El proyecto escribe identificadores en español (NORMAS.md §3) y el sufijo `Error` que exige N818 es una convención inglesa. No se tocó `pyproject.toml` (archivo compartido) |

## Hallazgos

1. **El evaluador de expresiones está duplicado**, como anticipó la bitácora de I3.2. `core/verification/expresiones.py` y `adapters/civil/evaluador.py` implementan el mismo recorrido de AST restringido. La regla de dependencia lo obliga: el núcleo no puede importar un adaptador, y el adaptador solo puede importar `core.contracts`. La duplicación es real y contraria al principio DRY. **Salida sin tocar los contratos:** la prueba `test_las_reglas_civiles_son_evaluables_por_el_nucleo` evalúa cada `REGLA_*` del adaptador civil con ambos evaluadores y exige el mismo `Decimal`, de modo que la divergencia se detecta el día que aparezca. **Candidato para el revisor de contratos:** mover el evaluador a `core.contracts.expresiones` (no depende de nada fuera de la biblioteca estándar, cumple la regla de los contratos) y que ambos lados lo importen. No se hizo aquí porque `core/contracts/` está congelado.

2. **Insuficiencia del contrato: `Hallazgo` no lleva `codigo_partida`.** Un hallazgo referencia `origen_ids`, y solo el presupuesto sabe qué partida produjo cada origen; además R6 compara APU entre sí y no tiene un `origen_id` de ítem que citar, solo códigos de partida. **Solución sin tocar el contrato:** `auditar` construye el índice `partida_por_origen` a partir de los ítems del presupuesto (registrando también la identidad `codigo -> codigo`) y `InformeAuditoria.partida_de(hallazgo)` resuelve la atribución. Si el contrato se revisara, el campo natural sería `Hallazgo.codigo_partida: str | None`.

3. **Insuficiencia del contrato: `PuntoCurva` no lleva `codigo_partida`.** R7 tiene que conciliar el plan de trabajo con el presupuesto sin saber qué partidas ejecuta cada período. **Solución sin tocar el contrato:** la convención de `core/verification/directivas.py`, que declara los códigos entre corchetes al final de la etiqueta (`"Dia 1 [LB-01-EXC, LB-02-TUB]"`), con `etiqueta_con_codigos` / `codigos_en_etiqueta` como par inverso. Si la etiqueta no los declara —como ocurre en la curva real del caso— R7 cae a la contención textual de la descripción de la partida en la del período, que es una heurística y puede fallar; por eso `core.budget` (Sesión I0.5) debería etiquetar sus períodos con `etiqueta_con_codigos`.

4. **Insuficiencia del contrato: el criterio de depreciación no es declarable.** NORMAS.md §7 define R6 como "un mismo insumo lleva el mismo factor en todos los APU **y el criterio está declarado**". `LineaEquipo` tiene `depreciacion` pero ningún campo donde declarar la regla de amortización que la justifica (vida útil, horas de uso, criterio contable). R6 verifica lo que sí puede —que el factor sea único por insumo— y lo dice en la descripción del hallazgo. La segunda mitad de la regla no es verificable con el contrato actual.

5. **`adapters/civil/tabular.py` genera el balance de relleno sin llaves**, en la forma `"LB-01-EXC - LB-04-CON - LB-02-TUB * 0.0081"`. `core.verification.expresiones.sustituir_codigos` espera `{LB-01-EXC}`, y sin llaves la expresión ni siquiera es analizable (`LB-01-EXC` se lee como una resta de tres nombres). Con ese balance, R5 emitiría un ERROR de "balance no evaluable" en vez de verificarlo. **No se corrigió aquí:** `adapters/` no es ruta exclusiva de esta tarea y el núcleo no debe adaptarse al adaptador. Es un arreglo de una línea en `tabular.py` (envolver cada código en llaves) que debería entrar en la siguiente sesión que toque el adaptador civil.

6. **`pytest.importorskip("core.budget")` no salta nada.** El paquete `core/budget/__init__.py` ya existe (vacío) desde el esqueleto del Sprint 0, así que se importa sin error. La prueba del presupuesto corregido añade `if not hasattr(budget, "generar_curva"): pytest.skip(...)`. Se activará sola cuando la Sesión I0.5 exponga `plan_secuencial` y `generar_curva`; las firmas que asume `presupuesto_corregido()` son las del brief y deben confirmarse al fusionar.

7. **R7 sigue siendo decisión de diseño de este proyecto.** Las Bases del anteproyecto listan cinco reglas; R6 y R7 son adiciones. **R7 se valida con el tutor en esta sesión.** Sobre el caso real detecta las cinco discrepancias día a día que explican la brecha de 11,11 USD del hallazgo 3 (el hallazgo adicional 9), así que su valor empírico está demostrado.

## Impedimentos

Ninguno bloqueante. `core/` no se tocó fuera de `core/verification/`; ningún contrato se modificó.
`tests/unit/test_arquitectura.py` sigue verde (40 pruebas), la suite completa queda en 202 pruebas
verdes y 1 omitida (la del presupuesto corregido, a la espera de `core.budget`), con `ruff check .`
y `ruff format --check .` limpios y sin advertencias en la salida de pytest.

## Ronda 1 (revisión de calidad)

La revisión encontró dos rutas de datos donde una regla podía lanzar una excepción en vez de
producir un hallazgo, incumpliendo el requisito del brief ("ninguna regla lanza excepciones por
datos"). Ambas se corrigieron con un cambio mínimo, sin tocar la forma pública de nada.

1. **`expresiones.py:120‑136` (`_evaluar_binario`): el `try/except ArithmeticError` solo envolvía
   `Div` y `Pow`.** `Add`, `Sub` y `Mult` retornaban antes de llegar al `try`, así que un
   `decimal.Overflow` (subclase de `ArithmeticError`) producido por una constante extrema —por
   ejemplo `evaluar("1e999999 * 1e999999", {})`— se propagaba sin convertirse en
   `ExpresionInvalida`. Como `TrazabilidadGeometrica._verificar_regla` y
   `BalanceVolumetrico._verificar` solo capturan `(ExpresionInvalida, ParametroFaltante)`, un
   `ItemComputo.regla` o un `_balance` con esa forma hacía reventar `auditar()` en vez de producir
   un hallazgo ERROR. **Corrección:** se movió el despacho completo de los cinco operadores dentro
   del mismo `try`, de modo que cualquier `ArithmeticError` —no solo división entre cero o potencia
   no representable— sale como `ExpresionInvalida`.

2. **`reglas.py` (`BalanceVolumetrico._tolerancia`): `Decimal(declarada)` acepta `"nan"`,
   `"Infinity"` y `"-0.05"`, valores que `except InvalidOperation` no atrapa** porque la
   construcción del `Decimal` no falla; fallan (o mienten) después, al comparar en
   `_dentro_de_tolerancia`. Con `"nan"` la comparación lanzaba `decimal.InvalidOperation`
   directamente; con `"-0.05"` la regla marcaba ERROR en todo balance sin emitir la ADVERTENCIA que
   el propio código pretendía (una tolerancia negativa vuelve la comparación siempre falsa).
   **Corrección:** tras construir el `Decimal`, se exige `tolerancia.is_finite() and tolerancia >=
   0`; si no se cumple, cae al mismo aviso ADVERTENCIA ya escrito para la tolerancia no numérica,
   sin duplicar el mensaje.

**Pruebas añadidas** (TDD, RED confirmado contra el código sin corregir y GREEN contra el corregido,
ambas evidencias en el reporte de esta ronda): `test_el_evaluador_convierte_el_desbordamiento_en_expresion_invalida`
(parametrizada con Add/Sub/Mult desbordados), `test_r1_reporta_una_regla_que_desborda_en_vez_de_reventar_auditar`,
`test_r5_reporta_un_balance_que_desborda_en_vez_de_reventar_auditar` y
`test_r5_cae_a_la_tolerancia_del_sistema_si_la_declarada_es_nan_infinita_o_negativa` (parametrizada
con `"nan"`, `"Infinity"`, `"-0.05"`).

No se tocó nada más: ni la forma de `reglas.py`, ni los Minor diferidos a la revisión final, ni
ningún archivo fuera de las rutas exclusivas de esta tarea.
