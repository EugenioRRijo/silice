# Acta del segundo re-congelado del experimento del 2026-11-13 (`aplicacion/hoja.py`)

**Fecha:** 2026-11-13 · **Rama:** `feature/recongelado-hoja` (`.worktrees/s2m3`, desde `e2dfe116`) · **Autoriza:**
Eugenio, 2026-11-13, con estas palabras: «hazlas tú, todo el pendiente, te doy permiso» (autorizó hacer todo el trabajo
pendiente, incluido un nuevo re-congelado del experimento para `aplicacion/hoja.py`, que ESTADO §5, puntos 5 y 6, dejaba
«para el próximo re-congelado») · **Procedimiento:** el de las actas anteriores
(`2026-10-21-recongelado-del-experimento.md`, `2026-10-31-recongelado-experimento.md`,
`2026-11-06-recongelado-experimento.md`, [2026-11-13-recongelado-experimento.md](2026-11-13-recongelado-experimento.md) y la
del 2026-11-04 en la rama del PR #100): un solo re-congelado al final, con el árbol limpio y en un commit aparte.

## Por qué

`tests/unit/test_experimento_congelado_vigente.py` falla con «auditor cambio desde el congelado»: de las 50 rutas de
`archivos_del_auditor` (`asistente/experimento/protocolo.json`) cambió una, `aplicacion/hoja.py`
(`git diff --stat dcb3c0a5 HEAD` de esas rutas, del protocolo, de `mutaciones.py`, de `tests/fixtures/asistente/tareas/` y
de `core/`: solo `aplicacion/hoja.py`, 64 líneas más y 25 menos, todas del commit `f79ad096`). Las huellas `banco` y
`protocolo` siguen iguales; solo cambia `auditor`.

Cambia **solo** `asistente/experimento/congelado.json`. `mutaciones.py`, `protocolo.json` y `banco.py` no se tocan, ni las
tareas del banco, ni `core/` (`git diff --stat e2dfe116 HEAD -- core/` vacío).

## Qué cambió en `hoja.py`

Lo que ESTADO §5 dejó para este re-congelado (decisiones y simulaciones en
[2026-11-13-ola2-recongelado-y-plan.md](2026-11-13-ola2-recongelado-y-plan.md)):

1. **`_estado_de_precio` mira la fuente declarada de cada precio (D-17).** Nuevo `_fuentes_heredadas`: por insumo, el
   `origen` de cada lista que tiene su precio sin `PrecioOrigen` propio. «Sin referencia ni cotización: el precio no tiene
   fuente» sale solo si el precio tampoco trae una fuente declarada (la de su `PrecioOrigen` que no sea ese texto
   heredado). `precios_de_version` hace una consulta más para pasarle esas fuentes.
2. **`con_plan_por_rendimientos` usa `plan_que_cabe`** (días, semanas, meses, como la ruta del producto,
   `hoja_guardado._con_plan_que_cabe`); si ni en meses cabe, `HojaInvalida` con la salida (antes salía
   `PlanDemasiadoLargo`, un `ValueError`, sin convertir). El import pasa de `plan_del_borrador` a `PlanDemasiadoLargo,
   plan_que_cabe`.
3. **`estado_de_items`** no reparte por partida un hallazgo que ya cita uno de los renglones (E2E-3f).
4. **Tildes**: «+ Administración» y «= Con administración» del cierre del APU; los dos 422 de guardar («por qué se
   cambia y con qué respaldo», «quién lo hace»); y los demás mensajes que quedaban: `_enum` («válido»), `_vertices`
   («vértices… o más»), `cambiar_insumo` («línea»), `plan_desde_filas` («fracción», «repártala entre los períodos»),
   `_altura` («válida», «número») y `_entero` y `declarar_circuitos_desde_texto` («número», «más», «escribió»,
   «máximos»).

**Comprobación.** Árbol sintáctico de `hoja.py` en `dcb3c0a5` (el commit declarado en el congelado anterior) y en HEAD:
con los textos, cambian `_altura`, `_entero`, `_enum`, `_estado_de_precio`, `_fuentes_heredadas`, `_vertices`,
`cambiar_insumo`, `con_plan_por_rendimientos`, `declarar_circuitos_desde_texto`, `estado_de_items`, `filas_de_cierre`,
`motivo_para_no_guardar`, `plan_desde_filas`, `precios_de_version` y dos imports; **con todas las cadenas vaciadas**
cambian solo `_estado_de_precio`, `_fuentes_heredadas`, `precios_de_version`, `con_plan_por_rendimientos`,
`estado_de_items` y los imports (guion `ast_diff.py` del scratchpad de la ola 2).

## Por qué no altera lo que mide el experimento

- **Lo que mide.** El experimento clasifica mutantes E1–E8 con `comparador.py` sobre los hallazgos del auditor:
  `asistente/experimento/ejecucion.py::auditor_de_la_hoja` devuelve `hoja.elaborar_borrador(borrador).elaboracion.informe.hallazgos`.
  Ese informe lo arma `core.budget.elaborar` dentro de `elaborar_hoja`, **antes** de `estado_de_items`, que solo lee el
  informe para el Estado de la pantalla (`ResultadoHoja.estado_items`) y no lo cambia; el experimento no lee
  `estado_items`. `precios_de_version`, `_estado_de_precio`, `con_plan_por_rendimientos` (solo
  `crear_primera_version`), `filas_de_cierre`, `motivo_para_no_guardar` y los mensajes de error no están en su camino:
  el banco construye espacios válidos con `espacio_desde_filas` y el comparador no compara el texto de `HojaInvalida`.
- **Medido, no solo razonado.** El guion `huella_auditor.py` (scratchpad de la ola 2) corre, sin IA y sin red, la
  medición controlada del protocolo (semilla 20261011, 24 mutantes por tipo, las referencias del conjunto de
  evaluación) y calcula una huella SHA-256 de todos los hallazgos (regla, severidad, descripción, orígenes e impacto) de
  cada referencia y de cada mutante. En una exportación de `e2dfe116` (`git archive`, sin el cambio) y en esta rama con el
  cambio da lo mismo:

  | Medida | `e2dfe116` (congelado anterior) | Esta rama |
  |---|---|---|
  | Detección E1 / E2 / E3 / E4 | 0/24 · 24/24 · 0/24 · 24/24 | igual |
  | Detección E5 / E6 / E7 / E8 | 0/24 · 0/24 · 24/24 · 2/2 | igual |
  | Huella de los hallazgos | `7bd36ff721da6e60040e73874a1d9a2c70b1dd8b0b15f7591aaa65150e43de45` | igual |

  (E3 y E5 en 0/24 es el resultado ya informado como hipótesis previa falsada, decisión de Eugenio del 2026-10-18.)

**Pruebas del experimento** en la rama, antes de re-congelar (`tests/unit/test_experimento*.py`,
`test_mutaciones_viales.py`, `test_evaluar_asistente.py`): 119 verdes y 1 roja (al pie); la roja es
`test_experimento_congelado_vigente` (la que esta acta resuelve), con «auditor cambio desde el congelado».

## Huellas

| Huella | Congelado anterior (commit declarado `dcb3c0a5`) | Re-congelado (2026-11-13, segundo) |
|---|---|---|
| `banco` | `29446b12ebf646d89ef9ccae3b597989e8787757e7fdf9a66024ff098aa3a0b2` | igual |
| `protocolo` | `e769c50778198e0ad354409b6ad8589b344bf4c73eae9c04f715f7fc9b075bb6` | igual |
| `auditor` | `18fc3b4ac2d0e309fb8e2f280c4cc3322336ef2af4a5ce37fb2f7d704297408a` | `a1de80205cb7731f74a2b05ac41afbb23c4262e17eb9d63e2a4f924d24037194` |

El commit declarado en el nuevo `congelado.json` es el de esta acta.

## Cómo se re-congela y cómo se revierte

`congelar(<commit de esta acta>)` de `asistente/experimento/congelado.py`, con el árbol limpio y en un commit aparte:
`chore(experimento): segundo re-congelado con acta (2026-11-13)`. Revertir: revertir ese commit y `f79ad096` (vuelve
`hoja.py` y su huella `18fc3b4a…`); las pruebas de `f79ad096`/`da399c05` habría que revertirlas también.

**Nota para el PR #100.** Su rama re-congeló sobre `core/contracts/unidades.py`. Cuando se unan, la huella del auditor
tendrá que volver a calcularse con los cambios juntos, con su acta.

## Pruebas del experimento antes de re-congelar

**120 pruebas, 119 verdes y 1 roja** (`1 failed, 119 passed in 91.37s`); la roja es
`test_experimento_congelado_vigente::test_los_archivos_del_auditor_siguen_como_se_congelaron`. Después del
re-congelado, esa prueba pasa (commit siguiente).
