# Sesión 2b — Migración de las páginas Streamlit a la interfaz nueva (por olas)

> **Pedido:** Eugenio, 2026-10-18: «crea más subagentes para agilizar el trabajo con el front y migrarlo».
> **Base:** rama `inc/ruta-s2-visual` (sesión 2 con `main` 1.1.0 fusionado). **Inventario:** 21 páginas de
> `ui/app.py:136-179`, levantado por un subagente de exploración el 2026-10-18 (resumen en §2).
> **Cumple:** RT-4 de la ruta (Streamlit convive; las páginas se migran una a una; el retiro se decide en la
> sesión 6). No se retira ninguna página Streamlit en esta sesión.

## 1. Rulings del orquestador (ratificables)

| # | Ruling | Por qué | Costo si es erróneo |
|---|---|---|---|
| RM-1 | **Paquete nuevo `aplicacion/`** (capa de aplicación): cuando una página se migra, la lógica sin Streamlit que hoy vive en `ui/<x>.py` se **mueve** a `aplicacion/<x>.py` y `ui/<x>.py` queda como reexportación (`from aplicacion.<x> import *` explícito). `aplicacion/` no importa `streamlit`, `ui`, `api`, `scripts` ni `tests`; entra en `PAQUETES_FUERA_DEL_NUCLEO` con su regla en `tests/unit/test_arquitectura.py`. | `PROHIBIDOS_EN_API` impide a la API importar `ui/` (guardia transitiva); duplicar la lógica rompe DRY; `asistente/*` importa `ui.hoja` y la reexportación lo mantiene vivo. | Medio: mover módulos grandes cuesta; por eso se mueve solo lo que la ola necesita. |
| RM-2 | **Caso por sesión web.** La API guarda, en memoria del proceso, la ruta del caso elegido por cada ficha de sesión (`huella_ficha → caso`); sin elección, el de `APU_BASE` o el por defecto. Rutas `GET /v1/casos` (lista y actual) y `POST /v1/casos/actual` (exige `CAMBIAR_CASO`, CSRF). El motor se cachea **por ruta de caso**. Con clave de API, el caso sigue siendo el del proceso (como hoy). | Streamlit ya permite un caso por pestaña (`ui/caso.py`); un caso fijo por proceso rompería a dos personas de la red local en casos distintos. | Medio: al reiniciar la API la elección vuelve al caso por defecto (se informa en la pantalla). |
| RM-3 | **Acceso por ruta, no por router:** cada ruta antigua pasa de `CON_CLAVE` a `exigir_clave_o_sesion(<acción>)` con la acción de la página que la usa (GET de lectura → `LEER_PROYECTO`; escritura de la hoja → `EDITAR_HOJA`; listas y BCV → `ADMINISTRAR_PRECIOS`; etc.). Con clave, todo igual que hoy (regresión probada). | Un router mezcla lectura y escritura con roles distintos. | Bajo. |
| RM-4 | **«Solo desde el propio equipo» en la API:** dependencia `exigir_equipo_propio(sensible)` con `request.client.host` y `seguridad.red`, igual que `ui/sesion.exigir_local`; las operaciones `Sensible` (firmar, claves, carpeta de datos) la exigen además del rol. | Paridad con Streamlit (S3 §5.6). | Bajo: un proxy local la anula, como ya documenta `api/proteccion.py`. |
| RM-5 | **Librerías del front, un solo cambio de `package.json` (ola 0b):** `react-router` (navegación) y `@carbon/charts-react` (gráficos del tablero y la curva de control, Apache-2.0, del mismo sistema Carbon); versiones exactas publicadas hace ≥ 2 semanas; cada página se carga con `import()` para no inflar el arranque; el tope del `dist` (15 MB) no cambia. | Un sistema de diseño por proyecto (taste §2.A); gráficos con la gramática de Carbon. | Bajo. |
| RM-6 | **No se migran ahora** (otras sesiones las tocan): Hoja del proyecto (S1/S3), Libro de la empresa (es el visor de S2; S3 lo extiende), Revisar un paquete (S3 3.4 fija el dictamen), pestaña Asistente de IA de Administración (S1/S3). | Regla de la ruta §8: no chocar con otras sesiones. | Bajo. |

**Numeración de la ERS reservada (ruta §8):** los requisitos nuevos que traiga la migración toman **RF-142 a RF-150**
(hasta RF-141 está ocupado: S1 usa RF-141 y S2, RF-111 a RF-118). Si hacen falta más, se pide una reserva nueva en la
ruta antes de escribirlos; nunca se reutiliza un número.

## 2. Inventario resumido (21 páginas)

| Ola | Páginas | API hoy | Complejidad |
|---|---|---|---|
| 0 | marco: entrada completa (cambio de contraseña obligatorio), navegación por rol y modo entrega, caso y proyecto | parcial (`/v1/sesion`) | media |
| 1 | Catálogo, Histórico de precios, Acerca de | cubierta salvo Acerca | baja |
| 2 | Actualizar precios, Elaborar un presupuesto, Escenarios | casi cubierta | media |
| 3 | Componer una partida, Índices del BCV, Precios de la empresa, Inicio | por construir | alta / media |
| 4 | Tablero, Control de obra, Entregar paquete, Reajuste | por construir | alta |
| 5 | Administración (cuentas, empresa y firma, claves de API, instalación), Similares, Simulador (el Visor 3D se retiró el 2026-10-19) | por construir | muy alta / baja |
| — | Hoja, Libro de la empresa, Revisar, Asistente (RM-6) | — | fuera |

## 3. Reglas para trabajar en paralelo

- Worktrees `.worktrees/s2m*`, ramas `inc/ruta-s2-mig-<tema>` desde `inc/ruta-s2-visual`; se integran en
  `inc/ruta-s2-mig` (rama de la migración) con merge commit.
- **Una carpeta por página:** frontend `frontend-desktop/src/paginas/<pagina>/`; backend `api/rutas/<recurso>.py`
  nuevo y `tests/unit/test_api_<recurso>.py`. Esquemas nuevos junto a su ruta, nunca en `api/esquemas.py`.
- **Archivos compartidos con dueño serial por ola:** `api/main.py` (solo agregar líneas),
  `tests/unit/test_arquitectura.py` (solo agregar), `package.json`/`package-lock.json` (solo la ola 0b),
  `frontend-desktop/src/shell/rutas.ts` (cada página agrega su línea al integrar), `docs/api.json` (se regenera
  al integrar, nunca a mano), `CHANGELOG.md`.
- Cada página nueva: TDD (Vitest + RTL; pytest `-W error`), `DESIGN.md` manda, misma paridad funcional que la
  página Streamlit (mismos datos, mismas validaciones, mismos mensajes), sin calcular montos en el navegador.
- Revisión por ola: `silice-rev-pruebas` + `silice-rev-seguridad` (si hay escritura o sensibles) +
  `silice-rev-diseno` con capturas a 1366×768.

## 4. Olas y tareas

### Ola 0 (en paralelo 0a y 0b; contrato fijado aquí)

**0a · backend (`silice-backend`, Opus high):** RM-1 (crear `aplicacion/` vacío con su regla de arquitectura),
RM-2, RM-3 (todas las rutas existentes), RM-4, y `GET /v1/proyectos` (lista con código, nombre, versión vigente,
reusa `ui/proyectos.py` movido a `aplicacion/proyectos.py`), `POST /v1/sesion/contrasena` (cambio obligatorio:
`{actual, nueva}`, reusa `seguridad.cuentas.cambiar_contrasena`; quita el 403 «cambie su contraseña en la interfaz
clásica» y en su lugar `POST /v1/sesion` responde 200 con `debe_cambiar_clave: true` y una cookie que solo sirve
para `/v1/sesion/contrasena` y `DELETE /v1/sesion`).
Contrato:
- `GET /v1/casos` → `{actual: {nombre, ruta_relativa}, casos: [{nombre, ruta_relativa}]}` (sin rutas absolutas).
- `POST /v1/casos/actual` `{nombre}` → 200 con el actual; 403 sin `CAMBIAR_CASO`; 404 si no existe.
- `GET /v1/proyectos` → `[{codigo, nombre, version_vigente: int | null, actualizado: str | null}]`.
- `GET /v1/sesion` y `POST /v1/sesion` agregan `debe_cambiar_clave: bool` y `acciones: [str]` (las `Accion` que
  permite su rol, para que el front arme el menú sin repetir la matriz).

**0b · frontend (`silice-frontend`, Sonnet high):** RM-5 (dependencias), `src/shell/` (Carbon `Header` +
`SideNav` con secciones Trabajo, Revisión, Investigación y Administración según `acciones` y el modo entrega
`SILICE_MODO_ENTREGA` que la API informa en `GET /v1/sesion`), `src/shell/rutas.ts` (registro de páginas con
carga perezosa), selector de caso y de proyecto en la cabecera, pantalla de cambio de contraseña obligatorio,
`src/comun/` (tabla de datos densa Carbon `sm` con montos exactos alineados a la derecha, subida de archivo,
descarga de archivo, aviso de error con `detalle`, estado vacío, esqueleto). El visor de la sesión 2 pasa a ser la
página «Libro de la empresa».

### Ola 1 (tras 0a y 0b): Catálogo, Histórico, Acerca de · 3 subagentes `silice-frontend` + `silice-backend` para `GET /v1/acerca`

### Ola 2: Actualizar precios, Elaborar, Escenarios · 1 backend (dueño de `presupuestos.py` y `listas.py`) + 3 frontend

### Ola 3: Componer, Índices del BCV, Precios de la empresa, Inicio · 1 backend por router + 1 frontend por página

### Ola 4: Tablero, Control de obra, Entregar, Reajuste · ídem; un solo dueño de los gráficos

### Ola 5: Administración (sin la pestaña del asistente), Similares, Simulador

> **Visor 3D retirado el 2026-10-19 (decisión de Eugenio):** la página era ilustración, cargaba three.js y contradecía el RNF-08; ya no se migra y se eliminó de Streamlit y del registro del front (quedan 20 páginas; 17 en modo entrega). El adaptador IFC sigue vivo.

Cada ola tiene su plan detallado de tareas (archivos, contrato y pruebas) escrito por el orquestador antes de
despacharla, con lo que deje la ola anterior.
