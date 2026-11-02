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

## Contrato de las rutas (lo que consume el front)

Esquemas: `api/esquemas_ola2.py`, `api/esquemas_informe.py`, `api/esquemas.py`. Errores: `{ "detalle": str }`
(404 no existe, 409 conflicto, 422 dato inválido); el 409 de `calcular` puede traer además
`rendimientos_por_declarar`. Las peticiones que escriben llevan `X-Silice-CSRF` (lo pone `pedir`).

- `GET /presupuestos` → `[{codigo, total, proyecto}]`.
- `POST /listas-precios/vista-previa` (multipart `archivo`) → `{desconocidos:[{descripcion,tipo,unidad,precio,etiqueta}], motivo}`.
- `POST /presupuestos/revalorar` (multipart: `archivo, proyecto, codigo, codigo_nuevo, nombre, moneda, fecha_vigencia`,
  `dar_de_alta` repetido) → `RevaloracionRespuesta` (resumen, filas del comparativo, dados_de_alta, ignorados,
  rechazados, version_guardada|null, avisos[{nivel,texto}], informe).
- `POST /presupuestos/{codigo}/descartar?proyecto=` → `{codigo, descartada, fecha}`.
- `GET /presupuestos/{codigo}/excel?proyecto=` → xlsx de la versión guardada.
- `POST /computos/{dominio}` (multipart `archivo`, `codigos` JSON para civil) → ítems extraídos (ya existía).
- `GET /partidas` (ya existía) → catálogo; el civil elige códigos de las partidas de dominio civil.
- `POST /presupuestos/calcular` `{codigo, fecha, moneda, items[], plan?[{periodo,codigo_partida,fraccion}]}` →
  `CalculoRespuesta`; `POST /presupuestos/calcular/excel` (mismo cuerpo) → xlsx;
  `POST /presupuestos/calcular/declarar-rendimiento` `{codigo_partida, tipo, fecha}` → rendimiento registrado.
- `GET /presupuestos/{codigo}/escenarios/base?proyecto=` → `{codigo, proyecto, moneda, total, parametros, pendientes_base}`.
- `POST /presupuestos/{codigo}/escenarios?proyecto=` `{escenarios:[{nombre, fcas?, bono_alimentacion?, administracion?, utilidad?, precios:{}}]}`
  → `EscenariosRespuesta`; `POST .../escenarios/csv` (mismo cuerpo) → CSV exacto.

## Revisiones de la ola (2026-10-18)

Dictámenes de `silice-rev-pruebas` (aprueba con correcciones), `silice-rev-seguridad` (rechazaba por H1) y
`silice-rev-diseno` (aprueba con correcciones). Cerrado en esta rama:

- Seguridad: H1 (código con ruta en el libro de Excel: nombre fijo en el temporal, código con patrón), H2 (nombre de
  descarga saneado), H3 (CSV de escenarios sin fórmulas), H4 (topes: 2000 ítems, 5000 filas de plan, 20 escenarios, 1000
  precios, propuestas solo para los 50 primeros pendientes), H5 (importe desmesurado → 422), H6 (errores de base sin SQL),
  H8 (servidor de Vite solo en 127.0.0.1). Pruebas en `tests/integration/test_api_ola2_seguridad.py`.
- Pruebas: hallazgos 1–13 en `tests/integration/test_api_ola2_revision.py` (usuario sellado, plan conservado, curva del
  plan, informe exacto, aceptar propuesta con total exacto, parámetros congelados, CSV exacto, descarte, rollback, detector,
  altas, rendimientos).
- Diseño: severidad con icono y nombre, variación de costo con IBCS (flecha, color y texto), cabeceras en español, tildes y
  sin códigos de especificación, informe con jerarquía, plan de trabajo sobre el pliegue, selectores civiles sin
  preselección, detalle de escenarios a ancho completo, densidad `sm`, confirmación al descartar.

Deuda anotada (no bloquea): H7 sellar con el identificador de la clave de API en vez de «api (sin clave)»;
`POST /presupuestos` no guarda el plan en `PlanVersion` (la revaloración conserva el plan solo de versiones que sí lo
tienen); duplicación de `_elegidos`; hallazgos 15–17 de pruebas y 12–15 de diseño (dropzone común, alineación de
cabeceras numéricas, contraste y foco medidos en pantalla, error por campo en Elaborar).
