# Ola 2 de la migración — Actualizar precios, Elaborar un presupuesto, Escenarios (S2-A)

> Reparto: [REPARTO_SESIONES_MIGRACION.md](./REPARTO_SESIONES_MIGRACION.md). Marco: [PLAN_SESION_2B_MIGRACION.md](./PLAN_SESION_2B_MIGRACION.md).
> Base de las ramas: `inc/ruta-s2-mig-backend-base` (ola 0a) + `inc/ruta-s2-mig` (marco del front).
> Paridad con Streamlit: mismos datos, validaciones y mensajes; los montos llegan de la API como texto.

## Rulings de la ola (ratificables)

| # | Ruling | Costo si es erróneo |
|---|---|---|
| RA-1 | «Sembrar la línea base» de Actualizar precios **no se migra**: la API no importa `scripts/`. La base se prepara sola al abrir el caso. | Bajo |
| RA-2 | Sin versión guardada (UC-02 3a) no hay libro de Excel: el libro se baja de la versión guardada con `GET /presupuestos/{codigo}/excel`. | Bajo |
| RA-3 | Elaborar migra el modo de Streamlit, **solo calcular** (no guarda). Guardar en un proyecto sigue siendo `POST /presupuestos`. | Bajo |
| RA-4 | El informe de auditoría viaja como **JSON** (`InformeAuditoriaRespuesta`), no como Markdown: el front lo dibuja en celdas de texto plano (SEG-3). | Bajo |
| RA-5 | Aceptar una propuesta de similar es del front (cambia `codigo_partida` del ítem pendiente y vuelve a calcular), como en `ui.elaboracion.aceptar_propuesta`. | Bajo |
| RA-6 | Los CSV de escenarios y el libro de Elaborar se generan por rutas sin estado que recalculan con el mismo cuerpo. | Bajo |

## Backend (S2-A es dueño de `presupuestos.py`, `listas.py`, `ui/elaboracion.py`, `ui/resultado.py`)

Todas con `exigir_clave_o_sesion`; `EDITAR_HOJA` salvo lo indicado. Esquemas en módulos nuevos
(`api/esquemas_informe.py`, `api/esquemas_ola2.py`).

| Ruta | Acción | Qué hace |
|---|---|---|
| `POST /listas-precios/vista-previa` | EDITAR | `insumos_desconocidos` sin escribir; `{desconocidos, motivo}` |
| `POST /presupuestos/revalorar` | EDITAR | UC-02 completo (lista + `actualizar_precios` + commit si hubo cambio de precio) |
| `POST /presupuestos/{codigo}/descartar` | EDITAR | `descartar_version` (UC-02 7a) |
| `POST /presupuestos/calcular` | EDITAR | UC-01 sin guardar: total, partidas, severidades, informe JSON, pendientes con propuestas, plan por defecto; 409 con rendimientos por declarar (3b) |
| `POST /presupuestos/calcular/excel` | EDITAR | el libro del mismo cálculo |
| `POST /presupuestos/calcular/declarar-rendimiento` | EDITAR | `declarar_rendimiento` (3b) |
| `GET /presupuestos/{codigo}/escenarios/base` | LEER | parámetros congelados y pendientes del base |
| `POST /presupuestos/{codigo}/escenarios/csv` | EDITAR | tabla de RF-31 con `Decimal` exactos |
| `GET /presupuestos` | LEER | suma `proyecto` (aditivo) |

Lógica sin Streamlit: `ui/elaboracion.py` → `aplicacion/elaboracion.py` (reexportación en `ui/`); depende de
`aplicacion/composicion.py` (S2-B).

## Frontend (`src/paginas/actualizacion`, `elaborar`, `escenarios`)

Una carpeta por página, con `src/comun/`; una línea por página en `src/shell/rutas.ts`.

## Cierre por página

Pruebas (pytest `-W error`, Vitest), `ruff`, `npm run lint/build/dist`, una línea en `CHANGELOG.md`.
