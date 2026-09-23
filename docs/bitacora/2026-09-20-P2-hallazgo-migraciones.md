# Bitácora — Hallazgo: el esquema cambió y no hay herramienta de migración (auditoría final P2)

**Fecha:** 2026‑09‑20 · **Rama:** `inc/PLAN-prototipo` (worktree `.claude/worktrees/prototipo`) ·
**Origen:** auditoría final de los commits `d7d0bab..0d4ff1f` (fase P2 del prototipo AREN.IA),
hallazgo 1.1 del paquete de arreglos
(`.superpowers/sdd/2026-09-20-prototipo-arenia-fase-p2-deudas-y-composicion/final-fix-package.md`).

## Qué pasó

La Tarea 1 de la fase P2 (commit `e6aeeb8`, "persiste la modalidad de mano de obra por linea")
añadió la columna `modalidad` a `composicion_apu` (`core/models/entidades.py:115`). El esquema de
este proyecto se crea con `Base.metadata.create_all` (`core/catalog/sesion.py:32`), y esa llamada
**nunca altera una tabla que ya existe**: solo crea las que faltan. El proyecto no tiene Alembic ni
ninguna otra herramienta de migración.

Resultado: toda base SQLite creada antes de ese commit —y en esta máquina, `data/apu.db` (generada
el 16/09/2026 por `scripts/seed.py`)— quedó con la forma antigua de `composicion_apu` (`id,
partida_id, insumo_id, cantidad, depreciacion, orden`, verificado con `PRAGMA table_info` en modo
solo lectura antes de esta bitácora). Esa ruta es el valor por defecto de las seis páginas de la
interfaz (`ui/paginas/catalogo.py`, `elaborar.py`, `escenarios.py`, `historico.py`, `similares.py`,
`actualizacion.py`, todas con `RUTA_BASE_POR_DEFECTO = "data/apu.db"`). Cada una llama a
`crear_esquema(motor)` al abrir, que tiene éxito y no hace nada porque la tabla ya existe, y la
primera lectura de cualquier composición lanza `OperationalError: no such column:
composicion_apu.modalidad`. Como las páginas atrapan `SQLAlchemyError`, quien usa el prototipo no ve
una traza: ve un `st.error` en una pantalla que el día anterior funcionaba.

## Por qué la suite no lo vio

`tests/integration/conftest.py` construye una base `sqlite://` en memoria y llama a `crear_esquema`
sobre ella **siempre desde cero**. Esa llamada ejercita `create_all` creando una tabla que todavía no
existe —el caso que sí funciona—, nunca el caso real del hallazgo: una tabla que ya existe con una
forma distinta a la que el modelo declara ahora. Los 598 casos de la suite, con `core/` al 98 % de
cobertura, pasaron en verde durante los seis commits de la fase P2 sin que ninguno tocara una base
persistente preexistente.

## La causa de fondo

El proyecto persiste con SQLAlchemy pero **no adoptó una herramienta de migración de esquema**.
`Base.metadata.create_all` es exactamente lo que su nombre dice: crea tablas ausentes. Es suficiente
para sembrar una base nueva (lo único que hasta ahora se le pedía) y **no es suficiente** para
evolucionar una base que ya tiene datos y cuyo modelo cambió — que es justo lo que pasó aquí por
primera vez en el proyecto.

## Las dos salidas cuando esto vuelva a pasar

1. **`ALTER TABLE … ADD COLUMN …`**, ejecutado a mano contra la base afectada. Es aditivo: conserva
   todas las filas existentes, que quedan con la columna nueva en `NULL`. El sistema debe saber leer
   ese `NULL` con el valor por defecto declarado (para `modalidad`, `core/catalog/mapeo.py:87‑89` lo
   hace: `NULL` se interpreta como `ModalidadManoObra.JORNAL`; ver la prueba
   `test_una_linea_sin_modalidad_persistida_vuelve_como_jornal` en
   `tests/integration/test_persistencia.py`, y la nota del punto 3.1 de este mismo paquete de
   arreglos sobre lo que esa prueba puede y no puede demostrar sin el `ALTER TABLE`).
2. **Volver a sembrar con `--reiniciar`.** Los cuatro sembradores (`scripts/seed.py`,
   `scripts/seed_industrial.py`, `scripts/seed_sistemas.py`, `scripts/seed_telecom.py`) aceptan
   `--db` para apuntar a una base distinta de la de producción y `--reiniciar` para recrearla desde
   cero. Es destructivo para esa base puntual, pero no exige tocar código.

En esta máquina se aplicó la opción 1 sobre `data/apu.db`, verificada en modo lectura antes y
después:

```
$ uv run --no-sync python -c "..."          # PRAGMA table_info antes: sin 'modalidad'
$ uv run --no-sync python -c "..."          # ALTER TABLE ... ADD COLUMN modalidad VARCHAR(10)
columna anadida
$ uv run --no-sync python -c "..."          # Catalogo(...).composicion('LB-01-EXC').codigo_partida
LB-01-EXC
```

`data/apu.db` está en `.gitignore` (`*.db`), así que esta reparación no viaja en ningún commit: es
un arreglo de esta máquina, y lo que sí se documenta con este commit es el hallazgo.

## La regla que queda para las sesiones siguientes

**Toda sesión que añada o cambie una columna de `core/models/entidades.py` declara en su propio
plan qué pasa con las bases ya creadas, antes de escribir el código** — igual que declara qué
prueba lo cubre. La pregunta a responder no es solo "¿el modelo nuevo es retrocompatible en
memoria?" (que es lo que la Tarea 1 sí verificó bien), sino "¿qué le pasa a un archivo `.db` que ya
existe en disco con el modelo viejo?".

## Trabajo futuro

Si los cambios de esquema se vuelven recurrentes —lo esperable a medida que el prototipo crezca
hacia P3‑P5 y hacia los adaptadores de dominio—, la decisión pendiente es adoptar Alembic (o una
herramienta equivalente de migraciones versionadas). Queda declarada aquí como trabajo futuro, no
como una omisión de esta sesión: mientras el proyecto tenga una sola base de trabajo por
desarrollador y los cambios de esquema sean ocasionales, `ALTER TABLE` manual y `--reiniciar` son
proporcionales al tamaño del problema.

## Estado al cierre

Hallazgo documentado, sin tocar `core/`. `data/apu.db` de esta máquina reparado de forma aditiva
(columna `modalidad` añadida, filas preexistentes conservadas con `NULL`). Nota de una línea añadida
en `README.md` junto a las instrucciones de `scripts/seed.py`. Ninguna prueba se modificó por este
hallazgo; ver el punto 3.1 del mismo paquete de arreglos para la corrección del docstring de
`test_una_linea_sin_modalidad_persistida_vuelve_como_jornal`, que hasta ahora describía una garantía
que el sistema no tenía.
