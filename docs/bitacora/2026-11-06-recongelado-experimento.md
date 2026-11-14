# Acta del re-congelado del experimento por la tanda de detalles (2026-11-06)

**Fecha:** 2026-11-06 · **Rama:** `feature/tanda-detalles` (`.worktrees/tanda`) · **Autoriza:** Eugenio, 2026-11-06
(a la pregunta del orquestador, eligió «Re-congelar con acta») · **Procedimiento:** el de las actas anteriores
(`2026-10-21-recongelado-del-experimento.md`, `2026-10-31-recongelado-experimento.md` y la del 2026-11-04 en la rama del
PR #100).

## Por qué

`tests/unit/test_experimento_congelado_vigente.py` falla con «auditor cambio desde el congelado»: de las 50 rutas de
`archivos_del_auditor` (`asistente/experimento/protocolo.json`) cambió una, `aplicacion/hoja.py`
(`git diff --stat 6a0e8bcf HEAD` de esas rutas, del protocolo, de `mutaciones.py` y de `tests/fixtures/asistente/tareas/`:
solo `aplicacion/hoja.py`, 20 líneas más y 17 menos). Las huellas `banco` y `protocolo` siguen iguales; solo cambia
`auditor`.

Cambia **solo** `asistente/experimento/congelado.json`.

## Por qué no afecta a lo que mide el experimento

- **Qué cambió en `hoja.py`.** Solo mensajes para la persona, en excepciones `HojaInvalida` y en el motivo para no crear
  la primera versión: «de la obra» en vez de «del proyecto» (D2), tildes («versión», «está vacía», «de dónde»,
  «quién», «créela»), «la barra lateral (Nueva obra)», y el plural correcto de «N línea(s)» (MENOR 7), que se arma con
  el ayudante nuevo `aplicacion/plural.py` (`plural(n, singular, en_plural)`, sin aritmética).
- **Comprobación.** Se comparó el árbol sintáctico de `hoja.py` en `6a0e8bcf` y en HEAD con todas las cadenas de texto
  vaciadas: la única diferencia es `from aplicacion.plural import plural` y sus dos llamadas dentro de los f-strings de
  dos mensajes de error (`_cantidades_de_tabla` y `cambiar_insumo`). Ninguna cifra, regla, rama ni valor devuelto cambió.
- **Dónde lo usa el experimento.** El experimento clasifica mutantes E1–E8 con `comparador.py` sobre las salidas del
  auditor; no compara el texto de los mensajes de `HojaInvalida`.

**Pruebas del experimento** en la rama (`tests/unit/test_experimento*.py`, `test_mutaciones_viales.py`,
`test_evaluar_asistente.py`): **119 verdes y 1 roja**, la roja es `test_experimento_congelado_vigente` (la que esta acta
resuelve).

## Huellas

| Huella | Congelado anterior (commit declarado `0b477eba`) | Re-congelado (2026-11-06) |
|---|---|---|
| `banco` | `29446b12ebf646d89ef9ccae3b597989e8787757e7fdf9a66024ff098aa3a0b2` | igual |
| `protocolo` | `e769c50778198e0ad354409b6ad8589b344bf4c73eae9c04f715f7fc9b075bb6` | igual |
| `auditor` | `63930d4b5e3b9528ca58dcb2ab68680bb9bbb47d19f4d3bafe8395706cdb22c6` | la que escriba `congelar` (ver el commit siguiente) |

El commit declarado en el nuevo `congelado.json` es el de esta acta.

**Nota para el PR #100.** Su rama re-congeló sobre `core/contracts/unidades.py`. Cuando se unan las dos, la huella del
auditor tendrá que volver a calcularse con los dos cambios juntos, con su acta.
