# Enmienda a NORMAS.md §3: worktrees, ramas cortas por fase y un carril de núcleo

**Estado:** RATIFICADA por Eugenio el 2026-10-11

| Campo | Valor |
|---|---|
| Origen | spec maestro de Sílice 1.0.0, §6.1, ruling RV‑2; plan de la 0.6.0, sección A, tarea A5 |
| Redacción | 2026‑10‑11 |
| Ratificación | Eugenio, 2026‑10‑11 («apruebo 1, 2 y 3»: worktrees, ramas cortas por fase y un solo carril de núcleo). La sección 2 se aplicó a NORMAS.md en el mismo PR; `tests/unit/test_enmienda_normas.py` exige que el estado de este documento y NORMAS concuerden |

## 1. Por qué

- NORMAS §3 decía: «Uno por sprint en `.worktrees/<nombre-corto>` … Solo coexisten el checkout principal y
  el worktree del sprint vigente».
- Sílice construye con carriles en paralelo (maestro §5, RV‑1): S1‑2 (`adapters/bcv`), S3‑1 (`seguridad`),
  S3‑5 (planos) y S4.0–S4.2 (`asistente`) avanzan junto al carril de núcleo. Con un solo worktree, cada carril
  obliga a cambiar de rama en el mismo directorio (con su `.venv`) o a romper la norma.
- La norma ya no se cumplía: el 2026‑10‑11, `git worktree list` mostraba el checkout principal y nueve worktrees
  más (sección 5).
- El daño que motivó la norma (`main` dos semanas desactualizado) lo evitan mejor las otras dos reglas: ramas
  cortas por fase que salen del `main` del momento y se fusionan al cruzar su compuerta, y un solo carril de
  núcleo abierto a la vez.

## 2. Texto aplicado (sustituye estas filas de la tabla de NORMAS §3)

| Convención | Regla |
|---|---|
| Ramas | `main` es la única rama de integración. Desde Sílice (0.6.0), ramas cortas por fase: cada una sale del `main` del momento (`origin/main`), recibe `main` a menudo, corre la CI en cada *push* y se fusiona al cruzar la compuerta de su fase, no al final de la versión. Nada se apila. Hay un solo carril de núcleo abierto a la vez (orden del maestro §6.1: S1‑1 → S1‑3 → S1‑4 → S2‑1 … S2‑3 → S3‑2); una rama `-nucleo` toca solo `core/`, `migraciones/`, `tests/` y `docs/`. Una rama que agrega archivos bajo `adapters/` sale de `main` sin núcleo pendiente |
| Worktrees | Como máximo tres worktrees vivos además del checkout principal, en `.worktrees/<nombre-corto>`: el del carril de núcleo y hasta dos de carriles sin núcleo. Se borra con `git worktree remove` al fusionar su rama (nunca con `--force`; si se niega, se revisa qué quedó sin guardar) |
| Fusión | Un PR por fase **contra `main`**, fusionado en cuanto la CI esté verde y la compuerta cruzada, con *merge commit* (`gh pr merge <n> --merge`, nunca *squash*: la meta comprueba que el commit de cada prueba precede al de su implementación). No acumular pilas: `gh pr merge` fusiona en la base *actual* del PR |
| Etiquetas | Una por compuerta cruzada y, desde Sílice, `vX.Y.Z` anotada en `main`, en orden numérico (`v0.6.0` antes que `v0.7.0` aunque un carril llegue antes) |
| Metas | Desde la 0.6.0, una sola meta: `scripts/meta_silice.py --version X --hasta FASE`; una fase se cruza con la meta en OK **y** la compuerta anotada en `docs/bitacora/`. Las metas `meta_<sprint>.py` anteriores quedan como registro |

## 3. Qué no cambia

Commits, sesiones, entorno, idioma y el resto de NORMAS. La regla de la sección 9 (detenerse antes de tocar
`core/` desde un adaptador) sigue igual; los cambios de núcleo siguen con expediente.

## 4. Cómo se comprueba

- `git worktree list | wc -l` ≤ 4 (principal + tres) al abrir cada fase; se anota en la bitácora de la fase.
- La meta (`C3`) falla si una fusión con *squash* borra el orden prueba → implementación.
- `scripts/guardia_nucleo.py` en la CI sigue separando ramas de núcleo y de adaptadores (M9).

## 5. Limpieza de los worktrees actuales (no ejecutada por este PR)

La ratificación cubre las tres reglas, no el borrado de worktrees: cada uno se retira solo con la orden
expresa de Eugenio. Todas las ramas de la tabla están contenidas en `origin/main`
(`git merge-base --is-ancestor <rama> origin/main`, 2026‑10‑11):

| Worktree | Rama | Propuesta |
|---|---|---|
| `TESIS` (principal) | `inc/spec-horizonte` | se queda; volver a `main` cuando Eugenio lo decida |
| `.claude/worktrees/prototipo` | `inc/PLAN-prototipo` | borrar |
| `.claude/worktrees/ui` | `inc/PLAN-ui` | borrar |
| `.worktrees/integ` | `inc/sf-integracion` | borrar |
| `.worktrees/sf` | `inc/sf3-nucleo` | borrar |
| `.worktrees/sf3` | `inc/sf3` | borrar |
| `.worktrees/sf4` | `inc/sf4` | borrar |
| `.worktrees/sf5` | `inc/sf5` | borrar |
| `.worktrees/silice` | `inc/silice` | borrar al fusionar el plan de la 0.6.0 |
| `.worktrees/nombre` | `inc/nombre-silice` | se usa en A1; se borra al fusionarla |

Orden por worktree: `git -C <ruta> status --short` (debe estar vacío) y luego `git worktree remove <ruta>`.
