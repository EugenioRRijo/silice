# Reparto de la migración entre sesiones de Claude Code (2026-10-18)

> Eugenio abre tres sesiones más para acelerar la migración del front ([PLAN_SESION_2B_MIGRACION.md](./PLAN_SESION_2B_MIGRACION.md)).
> Este documento dice **qué hace cada sesión, en qué carpetas y cuándo**. La sesión que orquesta la sesión 2
> (llamada aquí **S2-orq**) integra todo en la rama `inc/ruta-s2-mig` y es la única que fusiona ahí.

## 1. Quién hace qué

| Sesión | Ola | Páginas Streamlit | Worktrees / ramas propios |
|---|---|---|---|
| **S2-orq** (la de origen) | cierre de la sesión 2 (1.2.0), ola 0 (en curso), ola 1, ola 5 e integración | Catálogo, Histórico, Acerca de; Administración (sin el asistente), Similares, Simulador (Visor 3D retirado el 2026-10-19) | `.worktrees/s2`, `s2a`…`s2h`, `s2m`, `s2m1`, `s2m2`; ramas `inc/ruta-s2-*`, `inc/ruta-s2-mig`, `inc/ruta-s2-mig-backend-base`, `inc/ruta-s2-mig-shell` |
| **S2-A** | ola 2 | Actualizar precios (`ui/paginas/actualizacion.py`), Elaborar un presupuesto (`elaborar.py`), Escenarios (`escenarios.py`) | `.worktrees/s2ma*`; ramas `inc/ruta-s2-mig-a-*` |
| **S2-B** | ola 3 | Componer una partida (`componer.py`), Índices del BCV (`indices.py`), Precios de la empresa (`precios_empresa.py`), Inicio (`inicio.py`) | `.worktrees/s2mb*`; ramas `inc/ruta-s2-mig-b-*` |
| **S2-C** | ola 4 | Tablero (`tablero.py`), Control de obra (`control.py`), Entregar paquete (`entregar.py`), Reajuste (`reajuste.py`) | `.worktrees/s2mc*`; ramas `inc/ruta-s2-mig-c-*` |

**Nadie migra** (RM-6): Hoja del proyecto, Libro de la empresa, Revisar un paquete, pestaña Asistente de IA.

## 2. Archivos: dueño exclusivo y compartidos

| Recurso | Regla |
|---|---|
| Backend de cada página | archivo nuevo `api/rutas/<recurso>.py` + `tests/unit/test_api_<recurso>.py` (o `tests/integration/`), esquemas junto a la ruta |
| Lógica sacada de `ui/` | `aplicacion/<modulo>.py` + reexportación en `ui/<modulo>.py` (RM-1). Cada módulo de `ui/` tiene **un solo dueño**: S2-A `ui/elaboracion.py`, `ui/resultado.py`; S2-B `ui/composicion.py`, `ui/indices.py`, `ui/precios_empresa.py`, `ui/caso.py` (lógica sin Streamlit) y `ui/recorridos.py`; S2-C `ui/tablero.py`, `ui/control.py`, `ui/entrega.py`, `ui/reajuste.py`, `ui/graficos.py` (si se porta), `ui/estilo.py`. `ui/proyectos.py` ya lo movió la ola 0a. **`ui/hoja.py` no se mueve** (RM-6; lo usan `asistente/*` y la hoja): si una ola necesita una función de ahí, la pide a S2-orq |
| Frontend de cada página | `frontend-desktop/src/paginas/<pagina>/` (componente, lógica pura, pruebas). Nada fuera de esa carpeta salvo la línea de registro de la página |
| `api/rutas/presupuestos.py`, `api/rutas/listas.py` | **solo S2-A** (rutas aditivas; nada de cambiar el contrato con clave) |
| `api/main.py` | solo **agregar** las líneas de su router; al integrar las resuelve S2-orq |
| `tests/unit/test_arquitectura.py` | solo **agregar** líneas |
| `frontend-desktop/src/shell/rutas.ts` | cada sesión agrega **una línea por página** (el formato lo fija la ola 0b) |
| `package.json` / `package-lock.json` | **nadie** los cambia: la ola 0b ya agrega `react-router` y `@carbon/charts-react`. Si hace falta otra dependencia, se pide a S2-orq |
| `docs/api.json` | se **regenera** con `uv run python scripts/exportar_openapi.py`, nunca se fusiona a mano |
| `docs/ERS.md` | numeración reservada a la migración RF-147–RF-155 (ruling T1: RF-142–RF-146 son del historial): S2-A RF-147–RF-149, S2-B RF-150–RF-152, S2-C RF-153–RF-155 (solo si la página pide un requisito nuevo; reproducir una página no lo exige) |
| `CHANGELOG.md` | una línea por página bajo «Sin publicar»; al chocar se conservan las dos |

## 3. Orden de trabajo de cada sesión

1. **Ya (sin esperar a la ola 0):** leer este documento, `PLAN_SESION_2B_MIGRACION.md`, `RUTA_SESIONES.md` §4 y §8,
   `NORMAS.md`, `frontend-desktop/PRODUCT.md` y `DESIGN.md`, y las páginas Streamlit de su ola con sus módulos
   de `ui/`. Escribir el **plan detallado de su ola** en `docs/planes/PLAN_MIGRACION_OLA_<N>.md` (archivos, contrato
   de cada ruta, pruebas con sus valores, paridad con la página Streamlit: mismos datos, validaciones y mensajes).
2. **Ya:** construir el **backend** de su ola (rutas nuevas, mover lógica a `aplicacion/`, pruebas TDD), con
   `exigir_clave_o_sesion(<acción>)` de `api/sesion_web.py` en cada ruta. El caso de la sesión web y la dependencia
   `exigir_equipo_propio` llegan con la ola 0a: escribir contra el contrato del plan 2b y ajustar al integrarla.
3. **Cuando S2-orq avise que la ola 0 está en `inc/ruta-s2-mig`** (marco del front, `src/comun/`, `rutas.ts`):
   `git merge inc/ruta-s2-mig` en sus ramas y construir las pantallas con los componentes comunes.
4. **Entregar por página o por grupo:** rama limpia con commits convencionales, `uv run ruff check .`, las pruebas
   tocadas en verde (`-W error`), `npm test`, `npm run lint`, `npm run build`, `npm run dist`; avisar a S2-orq (un
   mensaje con la rama y el resumen). S2-orq revisa, integra en `inc/ruta-s2-mig` y corre lo integrado.

## 4. Reglas comunes (de la ruta)

- `core/` intacto; `git diff origin/main -- core/` vacío; la guardia del núcleo en OK.
- TDD con rojo visto, `pytest -W error`, cero omitidas; la **suite completa** solo la corre S2-orq (la ruta prohíbe
  correrla en dos sesiones a la vez).
- Nunca `git stash` simple; nunca push a `main`; nunca fusionar en `inc/ruta-s2-mig` (eso es de S2-orq).
- Nada de libros reales al repo (`docs/auditoria/*.xlsx|pdf` y `data/confidencial/` son confidenciales).
- Subagentes con ficha, modelo y esfuerzo de la ruta §3 (`general-purpose` + «actúa según la ficha
  `.claude/agents/silice-<rol>.md`»); revisores `silice-rev-pruebas`, `silice-rev-seguridad` (si escribe o es
  sensible) y `silice-rev-diseno` con capturas a 1366×768.
- **Navegadores:** perfil propio (`--user-data-dir` en el scratchpad) y cerrar solo el PID propio; **prohibido**
  cerrar Edge o Chrome por nombre: Eugenio usa el equipo.
- Servidores de prueba solo en `127.0.0.1`, puertos libres; datos en una carpeta temporal, nunca en `data/`.
- Diseño: `frontend-desktop/DESIGN.md` manda (Carbon g10, esquinas rectas, densidad `sm`, dos semánticas de color,
  sin animación decorativa, montos exactos desde la API, 1366×768 sin desplazamiento horizontal).
- Las decisiones que cambian lo que se construye se anotan como ruling en el plan de la ola, con su costo.
