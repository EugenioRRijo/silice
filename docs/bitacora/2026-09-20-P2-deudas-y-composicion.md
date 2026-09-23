# Bitácora — Sprint fase P2 del prototipo AREN.IA (deudas de P1 y composición pura)

**Fecha:** 2026‑09‑20 · **Rama:** `inc/PLAN-prototipo` (worktree `.claude/worktrees/prototipo`) ·
**Base del sprint:** etiqueta `p-base` (`471b3e2`) · **Rango:** `d7d0bab..0d4ff1f` (cuatro tareas) más
la tanda de arreglos de la auditoría final (`1ead3dc..c50cdf1` y este commit) ·
**Plan:** `docs/superpowers/plans/2026-09-20-prototipo-arenia-fase-p2-deudas-y-composicion.md` ·
**Spec vinculante:** `docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md` ·
**Ledger:** `.superpowers/sdd/2026-09-20-prototipo-arenia-fase-p2-deudas-y-composicion/progress.md`
(no viaja con la fusión: está en `.git/info/exclude`).

## Objetivo

Saldar dos deudas heredadas de la fase P1 (la modalidad de mano de obra no sobrevivía completa al
catálogo; RF‑33 solo se exigía en uno de los dos caminos de escritura) y construir `ui/composicion.py`,
las funciones puras que arman una `ComposicionAPU` a partir de las tres tablas de texto de la futura
pantalla de UC‑10 y UC‑11 (Sesión P2.2, todavía no construida).

**Resultado:** cuatro tareas completas, suite en verde, y una auditoría final que encontró un hallazgo
crítico de arquitectura (no de esta fase en particular, sino del proyecto: no hay herramienta de
migración de esquema) y cinco hallazgos importantes, documentados y corregidos en una tanda separada
(`docs/bitacora/2026-09-20-P2-hallazgo-migraciones.md` y los commits que preceden a este).

## Las dos deudas de P1, saldadas

**Deuda 1 — la modalidad a destajo no sobrevivía el viaje por el catálogo.** La decisión D9
(`docs/bitacora/2026-09-16-P0-hallazgo-destajo.md`) había añadido `ModalidadManoObra` al contrato en
la fase P1, pero `core/catalog/mapeo.py` solo construía tres campos por línea de mano de obra
(descripción, cantidad, sueldo): una composición con una línea a destajo se guardaba y volvía a leer
como si fuera jornal, con FCAS y bono aplicados a un precio que el artículo 114 de la LOTTT define
precisamente como el que no usa el tiempo como medida. Saldada en la Tarea 1 (commit `e6aeeb8`, "fix
(catalog): persiste la modalidad de mano de obra por linea"): columna `modalidad` nueva en
`core/models/entidades.py::ComposicionAPU`, y `LineaCatalogo`, `lineas_de`, `a_modelo_lineas` y
`a_composicion` (`core/catalog/mapeo.py`) actualizados para llevarla en los dos sentidos. Es
precisamente este cambio de esquema el que resultó no llegar a las bases ya sembradas — ver
`docs/bitacora/2026-09-20-P2-hallazgo-migraciones.md`.

**Deuda 2 — RF‑33 solo se exigía en uno de los dos caminos.** `reemplazar_composicion` ya exigía
`condiciones` desde P1, pero `cargar_composicion` la aceptaba con un valor por defecto silencioso
(`a_modelo_rendimiento_estimado(..., condiciones: str = "")`) que solo `scripts/seed.py` evitaba
declarando las condiciones "por fuera"; los otros tres sembradores (`seed_industrial`, `seed_sistemas`,
`seed_telecom`) y `medir_rnf03` dejaban `condiciones=''` en la base sin que nada lo impidiera. Cuando
la pantalla de UC‑10 llame a `cargar_composicion` en la Sesión P2.2, habría heredado ese silencio.
Saldada en la Tarea 2 (commit `c5434a6`, "fix(catalog): rf-33 tambien al crear una partida nueva"):
`condiciones` pasó a ser obligatorio en `cargar_composicion` y en `a_modelo_rendimiento_estimado`, sin
valor por defecto, y los cuatro sembradores y `medir_rnf03` se ajustaron a declararlas explícitamente.

## Los ocho rulings del controlador

El escaneo previo del plan y las revisiones de tarea dejaron ocho decisiones registradas en el
ledger, cada una con su coste si resultara equivocada:

1. **Orden de tareas 1 → 2** (no invertirlo), pese a que la Tarea 1 deja una llamada a
   `cargar_composicion` de cuatro argumentos que la Tarea 2 rompe al hacer `condiciones` obligatorio.
   *Coste si está equivocado:* una prueba en rojo entre las dos tareas, que la propia suite de la
   Tarea 2 detecta en su verificación de cierre.
2. **La deuda 2 es real**, aunque el docstring de `a_modelo_rendimiento_estimado` argumentara que
   `cargar_composicion` ya declaraba las condiciones "por fuera": eso solo lo hacía `scripts/seed.py`,
   no los otros tres sembradores. *Coste si está equivocado:* cinco llamadores tocados y una firma
   pública cambiada en una rama sin fusionar; revertir es un `git revert` de un commit.
3. **No añadir `ui` a la parametrización estricta de `test_arquitectura.py`** que solo permite importar
   `core.contracts`: esa regla es de los adaptadores (CLAUDE.md §2), no de la interfaz, que ya está
   vigilada por otra prueba menos estricta. *Coste si está equivocado:* la interfaz queda vigilada por
   una regla menos estricta de lo que el plan de sesiones imaginaba; se corrige añadiendo la
   parametrización en cualquier sesión futura.
4. **`item_desde_cantidad` recibe `dominio` como sexto parámetro**, no cinco como enumeraba el plan de
   sesiones, porque `ItemComputo` lo exige sin valor por defecto. *Coste si está equivocado:* un
   parámetro de más en una función que todavía no tiene llamadores fuera de sus propias pruebas.
5. **La prueba de la guarda de RF‑33 se corrige para contar también `models.Partida`** antes y después
   de la llamada, no solo `ComposicionAPU`: sin ese conteo, la prueba pasaría igual si la guarda se
   moviera después de crear la partida, y no demostraría la invariante de "sin partida huérfana" que
   justifica que la guarda vaya primero. *Coste si está equivocado:* dos asserts de más en una prueba
   de integración.
6. **La firma obsoleta de `a_modelo_rendimiento_estimado` en `docs/arquitectura.md`** (tres argumentos,
   ya son cuatro) se traslada fuera del ciclo de arreglos de la Tarea 2, a la Tarea 3, que es la
   documental. *Coste si está equivocado:* una línea obsoleta en un diagrama si la Tarea 3 no la
   recoge — no ocurrió: la Tarea 3 corrigió tres firmas obsoletas, no una.
7. **La contradicción de la §3.6 del spec** (seguía diciendo que `reemplazar_composicion` estaba
   "todavía no implementada", cuatro párrafos después de que la propia Tarea 3 afirmara lo contrario en
   §3.3) se corrige poniendo el estado al día, sin reescribir el razonamiento de diseño de la sección.
   *Coste si está equivocado:* un párrafo del spec en presente en vez de en futuro; se revierte con un
   edit.
8. **Autorización explícita de `git commit --amend`** sobre la punta de la rama, para corregir un
   asunto de commit que se contradecía a sí mismo, porque no estaba empujada (origin seguía en
   `8100dad`) y el historial de este repositorio es evidencia de la tesis. *Coste si está equivocado:*
   ninguno sobre el árbol, verificado con `git diff` vacío entre el commit original y el enmendado.

## La revisión por tarea, suspendida a mitad de sprint

El usuario instruyó, a mitad del sprint: «trata de no re-revisar a menos que sea estrictamente
necesario, las revisiones serán pautadas para una auditoría». Las Tareas 1, 2 y 3 ya habían pasado por
revisor y, en el caso de la Tarea 3, por una segunda ronda tras un hallazgo. La Tarea 4
(`ui/composicion.py`, commit `0d4ff1f`) se implementó **sin revisor**, verificada solo por el
controlador con lo objetivo: suite en verde con `-W error`, ruff limpio, meta `--hasta P2` en 7/8, y
`git diff` vacío contra `core/contracts/`.

**La auditoría final midió el coste de esa decisión.** De los cinco hallazgos IMPORTANTE de la tanda
de arreglos (`.superpowers/sdd/2026-09-20-prototipo-arenia-fase-p2-deudas-y-composicion/final-fix-package.md`,
puntos 2.1, 2.2, 2.3, 3.1 y 3.2), **tres están en la única tarea que no pasó por revisor**: los mensajes
de error sin identidad de fila (2.1), la fila con datos pero sin descripción que se colaba al catálogo
(2.2), y la contradicción entre `_fila_vacia` y la coerción con `str()` frente a los centinelas
`None`/NaN de `st.data_editor` (2.3). Los otros dos (3.1, 3.2) son documentales y preexistían a la
suspensión de revisiones. Los tres de la Tarea 4 quedaron corregidos, con pruebas nuevas, en el commit
`fix(ui): los mensajes de error dicen que fila y que campo` de esta misma tanda.

## Meta del sprint al cerrar

`scripts/meta_prototipo.py --hasta P2`: **7/8** metas OK (P1–P7), con **P8 en PENDIENTE** — es correcto
y esperado: P8 exige que `ui.paginas.componer` esté listado en `tests/unit/test_ui_importable.py`, y esa
página es la Sesión P2.2, que este sprint no construye (solo P2.1, las funciones puras). Sobre las doce
metas totales del sprint del prototipo (`P1`–`P12`), el estado es **7/12**: las fases P0 y P1 completas,
más P7 de la fase P2. Quedan pendientes P8 (la pantalla), P9 (prueba de extremo a extremo), y las fases
P3–P5 (flujo completo, pruebas de interfaz, cierre), que reciben su propio plan.

## Commits de esta tanda de arreglos

| Commit | Contenido |
|---|---|
| `1ead3dc` | `fix(datos)`: hallazgo de migraciones documentado; `README.md` con la nota de una línea |
| `6048c08` | `fix(ui)`: mensajes de error con fila y campo, descripción obligatoria, `None`/NaN normalizados |
| `c50cdf1` | `docs(modelo)`: columna `modalidad` en el modelo de datos; `reemplazar_composicion` en los dos listados de arquitectura; ERS con los archivos reales de RF‑33 y RF‑34 |
| (este commit) | `docs(bitacora)`: esta bitácora |

## Estado al cierre

Las cuatro tareas del plan de sesiones y los cuatro commits de la tanda de arreglos, completos. La
reparación de `data/apu.db` en esta máquina (aditiva, `ALTER TABLE`) no viaja en ningún commit por
estar en `.gitignore`; su verificación de lectura está en
`docs/bitacora/2026-09-20-P2-hallazgo-migraciones.md`. Pendiente para la sesión siguiente: P2.2 (la
pantalla), P2.3 (buscador MaPreX) y P2.4, con su propio plan.
