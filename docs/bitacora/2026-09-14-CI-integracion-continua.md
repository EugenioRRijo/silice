# Bitácora — Incremento CI (integración continua con GitHub Actions)

**Fechas:** 2026‑09‑14 (diseño) y 2026‑09‑15 (implementación y primeras corridas) · **Rama:**
`inc/CI-integracion-continua` (worktree `.claude/worktrees/ci-integracion`), apilada sobre
`worktree-sprint-multidominio` · **PR:** #2, con base en el PR #1 · **Spec:**
`docs/superpowers/specs/2026-09-14-ci-integracion-continua-design.md` · **Plan:**
`docs/superpowers/plans/2026-09-14-ci-integracion-continua.md`

## Objetivo

Verificar automáticamente cada PR y cada push a `main` sin instalar Linux en el equipo del autor.
Son cuatro garantías, elegidas por el usuario:

1. Suite y ruff en Linux sin pruebas omitidas.
2. Guardia del núcleo.
3. Cobertura de `core/` ≥ 80 % y artefactos reproducibles.
4. La suite también en Windows.

El motivo principal: RNF‑07 (portabilidad) estaba en «parcial» porque Linux nunca se había
verificado.

**Resultado:** las cuatro garantías corren y están en verde en el PR #2
([run 34969162933](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/34969162933)).
**RNF‑07 pasa a «cumple»** y portar no exigió ningún cambio de código ni de pruebas.

## TDD

1. **Guardia del núcleo.** RED: `ImportError: cannot import name 'guardia_nucleo'`. GREEN: 4 pruebas nuevas, más las 26 de `test_meta_alpha.py`, que reutiliza.
2. **Verificador de omitidas.** RED: `ImportError: cannot import name 'verificar_omitidas'`. GREEN: 5 pruebas. Ruff marcó N818 y la excepción pasó a llamarse `SinEvidenciaError`.

## Qué se creó

| Archivo | Contenido |
|---|---|
| `.github/workflows/ci.yml` | Job `calidad` (ruff + guardia, solo el grupo `dev`) y job `pruebas` en matriz Linux + Windows (todos los extras, `pytest -W error`, 0 omitidas; en Linux, cobertura de `core/` ≥ 80 % y reproducibles). Cachés de uv y del modelo de similitud, concurrencia que cancela corridas obsoletas, permisos de solo lectura |
| `scripts/guardia_nucleo.py` | `veredicto(base, *, base_existe, commits, ramas) -> (codigo, mensaje)` y CLI `--base`. Reutiliza `estado_nucleo_intacto`, `_commits_nucleo_intacto`, `_ramas_adaptador` y `_git` de `meta_alpha`. Sale con 0 si cumple, 1 si viola y 2 si la base es inválida |
| `scripts/verificar_omitidas.py` | `omitidas(xml) -> list[str]`, `SinEvidenciaError` y CLI. Reutiliza `_testcases` y `_resultado_de` de `meta_alpha`. Sale con 0 sin omitidas, 1 con alguna omitida y 2 sin evidencia |
| `tests/unit/test_guardia_nucleo.py` | 4 pruebas puras, sin git |
| `tests/unit/test_verificar_omitidas.py` | 5 pruebas con JUnit sintético |
| `.gitignore` | `reporte-pruebas.xml` |
| `docs/plan_pruebas.md` | §7 describe el pipeline; §9 lleva RNF‑07 a «cumple» con el enlace al run |
| `docs/calidad_iso25010.md` | §6 Portabilidad y la fila de §9 pasan a «cumple»; el resumen queda en seis características que cumplen |
| `docs/manual_tecnico.md` | §2: el comando local equivalente de cada paso de CI |

## Pruebas negativas (cada guardia muerde)

| Guardia | Caso | Esperado | Observado |
|---|---|---|---|
| Núcleo | `--base no-existe` | 2 | 2 («la base 'no-existe' no existe en este repositorio») |
| Núcleo | `--base worktree-sprint-multidominio` (rango real) | 0 | 0 (PENDIENTE: sin commits de `adapters/` ni `ml/`) |
| Núcleo | commit desechable `474e68c3` que toca `core/__init__.py` y `adapters/__init__.py`, en la rama `tmp/guardia-negativa` (borrada) | 1 | 1 («commits que tocan core/ junto a adapters/ o ml/: 474e68c3») |
| Omitidas | JUnit con una omitida | 1 | 1 (la lista con su motivo) |
| Omitidas | archivo inexistente | 2 | 2 |
| Reproducibles | `docs/api.json` alterado | `git diff --exit-code` → 1 | 1; restaurado con `git checkout` |

El ensayo local del job `pruebas` completo, antes del push, dio 490 passed (232 s con cobertura),
0 omitidas, `core/` al 98 % y reproducibles sin diferencias.

## Corridas remotas

| Run | Commit | Resultado | Causa |
|---|---|---|---|
| 34968964083 | `edc8ec6` | **failure** en «Set up job» en los tres jobs (3 s) | `astral-sh/setup-uv@v10` no existe |
| 34969162933 | `fe70bf4` | **success** en los tres jobs | — |

Detalle del run verde:

| Job | Duración | Evidencia en el log |
|---|---|---|
| `calidad (ruff + guardia del nucleo)` | 21 s | 14 paquetes; ruff limpio; guardia «PENDIENTE: sin commits que toquen adapters/ o ml/ desde la base» |
| `pruebas (ubuntu-latest)` | 2 min 44 s | 108 paquetes instalados en 5,67 s; **490 passed in 42,56 s**; 0 omitidas; `core/` 1 740 líneas, 33 sin cubrir, **98 %**; `api.json` regenerado (56 214 bytes) y `resultados_ml.md` sin diferencias |
| `pruebas (windows-latest)` | 2 min 31 s | Windows Server 2025; 91 paquetes en 2,78 s; **490 passed in 70,33 s**; 0 omitidas |

En la primera corrida no hubo caché del modelo de similitud en ninguno de los dos sistemas: la
prueba de normalización lo descargó y aun así no se omitió. La caché se guarda al terminar el job.

## Hallazgos

1. **RNF‑07 verificado sin portar nada.** La suite completa pasó en Linux y en Windows Server 2025
   sin tocar código de producción ni pruebas. Confirma lo que `calidad_iso25010.md` §6 anticipaba
   por inspección («sin rutas codificadas ni dependencias del sistema operativo»), ahora con
   evidencia en cada cambio.
2. **El riesgo de torch con CUDA no se materializó.** El lock trae 15 paquetes `nvidia-*` para
   Linux, pero el job completo tardó menos de 3 minutos. No hace falta el índice CPU de PyTorch
   (spec §7), así que `uv.lock` queda intacto.
3. **No todas las acciones publican una etiqueta mayor flotante.** `actions/checkout` y
   `actions/cache` tienen `v7` y `v6`; `astral-sh/setup-uv` solo publica versiones exactas. La
   primera corrida falló por suponer el patrón; se corrigió fijando `v10.1.0` en el workflow, la
   spec y el plan, tras comprobar las etiquetas con la API de GitHub.
4. **Un rango inválido no debe pasar como vacío.** `_commits_nucleo_intacto` devuelve una lista
   vacía si git falla, y eso se leería como PENDIENTE, un verde falso. La guardia valida la base
   primero (salida 2); el caso quedó cubierto por prueba y por CLI.
5. **La guardia dio PENDIENTE en este PR**, que es lo correcto porque no incorpora dominios. Morderá
   en el primer PR que mezcle `core/` con `adapters/` o `ml/`: lo demuestra la prueba negativa con
   el commit desechable.

## Pendientes

- **En archivos vedados** (cambios sin commitear del usuario en el checkout principal): mencionar
  la integración continua en las convenciones de `CLAUDE.md` §3 y agregar la insignia de CI en
  `README.md`.
- **Del usuario:** reglas de protección de rama en GitHub que exijan los tres checks antes de
  fusionar (Settings → Branches), y fusionar el PR #1. Al fusionarlo, reorientar el PR #2 a
  `main`.
- **Heredados:** la matriz RF → prueba de `plan_pruebas.md` §8 no lista las pruebas del sprint
  multidominio ni las de CI, y las celdas de evidencia de `calidad_iso25010.md` §9 de fiabilidad y
  mantenibilidad (395/395, 98,05 %) conservan el corte de F.2.

## Estado final

- Ensayo local: 490 passed con `-W error`, 0 omitidas, ruff limpio,
  `git diff worktree-sprint-multidominio --stat -- core/` vacío.
- PR #2: `calidad`, `pruebas (ubuntu-latest)` y `pruebas (windows-latest)` en verde en `fe70bf4`.
  El commit de esta bitácora dispara una nueva corrida en el mismo PR.
