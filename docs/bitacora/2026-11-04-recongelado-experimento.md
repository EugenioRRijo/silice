# Acta del re-congelado del experimento por NUC-E1 (2026-11-04)

**Fecha:** 2026-11-04 · **Rama:** `feature/nucleo-alias-ton-litro` (PR #100, worktree `.worktrees/sf`) · **Autoriza:**
Eugenio, 2026-11-04 («El #100 necesita el aval del tutor y, además, volver a congelar el experimento»). ·
**Procedimiento:** el de las actas anteriores (`2026-10-21-recongelado-del-experimento.md` y
`2026-10-31-recongelado-experimento.md`).

**El PR #100 sigue sin fusionarse hasta que el tutor avale el expediente NUC-E1** (cambio en `core/`). Este acta solo deja
el experimento listo para ese día.

## Por qué

`tests/unit/test_experimento_congelado_vigente.py` falla con «auditor cambio desde el congelado»: de las 50 rutas de
`archivos_del_auditor` (`asistente/experimento/protocolo.json`), cambió una, `core/contracts/unidades.py`, con los alias
de NUC-E1 (`31440fcc`): «l», «lt», «lts», «litro», «litros» → `l` y «t», «tn», «ton», «tonelada», «toneladas» → `t`. Las
huellas `banco` y `protocolo` siguen iguales; solo cambia `auditor`.

Cambia **solo** `asistente/experimento/congelado.json`. `mutaciones.py`, `protocolo.json`, `banco.py` y las tareas del
banco (`tests/fixtures/asistente/tareas/`) no se tocan (`git diff 0b477eba HEAD` de esas rutas, vacío).

## Por qué no afecta a las mutaciones del experimento

- **Qué cambia en el código.** `normalizar_unidad` devuelve una unidad desconocida tal cual (en minúsculas y sin espacios
  de más). Por eso «t» y «l» ya eran equivalentes a sí mismas antes del alias, y lo único que cambia es la equivalencia de
  un par en el que aparezca «tn», «ton», «tonelada(s)», «lt», «lts» o «litro(s)».
- **Dónde lo usa el experimento.** `comparador.py` (E1 contra E2) y `mutaciones.py` (E1 elige otra partida de unidad
  equivalente y E2 una unidad incompatible de `UNIDADES_INCOMPATIBLES = ("kg", "dia", "m2", "m3", "m", "pieza",
  "punto")`, sin ninguna de esas grafías).
- **Comprobación empírica.** Con la semilla del protocolo (20261011) y `n_por_tipo_de_mutacion` 24, se generaron todos
  los mutantes E1 a E8 sobre las referencias de evaluación y el catálogo de las pruebas (`codigos_y_unidades()`), y se
  clasificaron con `comparar`. Se hizo dos veces: con los alias y quitándolos en memoria de `_ALIAS`, lo que equivale al
  núcleo anterior. Resultado: **170 mutantes, misma huella SHA-256 de la clasificación**
  (`605fd81e6b2ad2d19693fe34c874a73a664d50d8c610af30c4fbfd5218ccbbcc`) en las dos corridas. Las unidades distintas del banco
  y del catálogo son 4 y ninguna usa una grafía de NUC-E1.

**Pruebas del experimento** sobre la rama con `main` unido (`0846eeeb`): `tests/unit/test_experimento*.py`,
`test_mutaciones_viales.py`, `test_evaluar_asistente.py`, `test_prueba_real_asistente.py` y
`test_unidades_tonelada_litro.py`: **147 verdes y 1 roja**, la roja es `test_experimento_congelado_vigente` (la que este acta
resuelve).

## Huellas

| Huella | Congelado anterior (commit declarado `0b477eba`) | Re-congelado (2026-11-04) |
|---|---|---|
| `banco` | `29446b12ebf646d89ef9ccae3b597989e8787757e7fdf9a66024ff098aa3a0b2` | igual |
| `protocolo` | `e769c50778198e0ad354409b6ad8589b344bf4c73eae9c04f715f7fc9b075bb6` | igual |
| `auditor` | `63930d4b5e3b9528ca58dcb2ab68680bb9bbb47d19f4d3bafe8395706cdb22c6` | la que escriba `congelar` (ver el commit siguiente) |

El commit declarado en el nuevo `congelado.json` es el de esta acta.

## Cómo se re-congela

`congelar(<commit del acta>)` de `asistente/experimento/congelado.py`, en un commit aparte:
`chore(experimento): re-congelado con acta (2026-11-04)`.
