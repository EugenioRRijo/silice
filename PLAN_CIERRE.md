# PLAN_CIERRE — final, límite y corrección metodológica de la tesis

**Diseño que lo fundamenta (fuente única del final, del límite y de los criterios):**
2026-09-23-plan-cierre-tesis-design.md,
aprobado por Eugenio el 2026‑09‑23 tras dos rondas de los cuatro encargos. Este plan no repite sus
criterios: los enlaza.

**Planes detallados (uno por fase, se escriben al abrirla):**
- C0: 2026-09-23-cierre-c0-inventario.md
- C3: 2026-09-24-cierre-c3-interfaz-scripts.md,
  que ejecuta la fase U1 del plan de UI, 2026-09-23-ui-recorrido-guiado-u0-u1.md,
  enmendado al abrir C3 (spec §5 y §10)
- C1: 2026-09-23-cierre-c1-nucleo.md
- C2: 2026-09-24-cierre-c2-adaptadores-ml-api.md
- C4, C5, C6, Med, U2/U3: se planifican al cruzar la compuerta anterior, con el inventario ya aprobado.

**Bitácora:** `docs/bitacora/2026-09-23-cierre.md` (la crea la Tarea 1 de C0).

## El final y el límite

El proyecto termina cuando se cumplen **F1–F5** (spec §1). Hasta entonces el alcance funcional está
congelado (spec §2): solo entran correcciones del inventario aprobado, U1 y, si su condición se cumple,
U2 o U3.

## Fases

| Fase | Contenido | Rama | Compuerta |
|---|---|---|---|
| Previo | Fusionar el PR #8 (merge commit) y el PR de este plan (`inc/PLAN-cierre`) | — | decisión de Eugenio |
| **C0** | Inventario de todo el repositorio por capa, principio y severidad; paquete para el tutor | `inc/cierre-C0` | **GC0** |
| **C1** | Salvaguarda de `data/apu.db`, guardia de arquitectura sobre `scripts/`, hallazgos de `core/` | `inc/cierre-C1` | **GC1** |
| **C2** | Hallazgos de `adapters/`, `ml/` y `api/` | `inc/cierre-C2` | **GC2** |
| **C3** | U1 (Tareas 7–12) más los hallazgos de `ui/` y `scripts/` | `inc/cierre-C3` | **GC3 = GU1a** |
| **C4** | Documentación coherente, trazabilidad por paso de todos los UC, protocolos del indicador 3 y de RNF‑04 | `inc/cierre-C4` | **GC4** |
| **C5** | Corrección de los hallazgos de la matriz F5 (INV‑087, INV‑088, INV‑092 con RF‑21, INV‑095 y los menores promovidos de GC4); `core/` solo en los commits de INV‑092 e INV‑095, con expediente (enmienda del 2026‑09‑28, pendiente de ratificación) | `inc/cierre-C5` | **GC5** |
| **C6** | Los cinco en duda de GC5 (INV‑076 con RF‑24, INV‑086, INV‑090, INV‑093 con su tabla aditiva, INV‑099) y la prueba con los listados MaPreX de julio de 2026 y el tabulador CIV; `core/` solo en los cinco commits autorizados, cada uno con expediente; dos rutas nuevas, ninguna pantalla (enmienda del 2026‑09‑29; visto bueno del tutor pendiente) | `inc/cierre-C6` | **GC6** |
| **Med** | CP‑07, indicador 3, juicio de expertos; después de GC6, no en paralelo | `inc/cierre-Med` | **GM = GU1b** y más |
| **U2 / U3** | B si CP‑07 FALLA; C si Eugenio lo decide | `inc/cierre-U2` / `-U3` | GU2 / GU1a |
| **Congelamiento** | Etiqueta `v1.0-tesis` | `main` | **F3** |
| **Red** | Capítulos IV → V → III → conclusiones → introducción → I (tras D3); una sesión de redacción por cada una de código desde C1 | `inc/tesis-<cap>` | **F4** |

Criterios completos de cada compuerta: spec §5. Cada rama sale de `main` después de fusionar la
anterior; nunca se apilan (spec §6). Cada compuerta exige la aprobación de los cuatro encargos y la
ratificación de Eugenio de las decisiones tomadas en la fase.
