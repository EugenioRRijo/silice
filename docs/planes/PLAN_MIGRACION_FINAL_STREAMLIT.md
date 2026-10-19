# Plan de la migración final: de Streamlit a la interfaz nueva (React + FastAPI)

Decisión de Eugenio (2026-10-19): completar la migración de **todas** las páginas Streamlit, con subagentes
orquestados y un **árbitro** que juzga cada entrega y la devuelve si no cumple la metodología del proyecto.
Orquesta la sesión principal. Documentos de apoyo: `MANUAL_SUBAGENTES_MIGRACION.md` (reglas de entorno, git, método),
`MANUAL_ARBITRO.md` (criterios y veredicto), `NORMAS.md`, `frontend-desktop/DESIGN.md` y `PRODUCT.md`.

## 1. Reglas generales

1. **Un solo árbol**: `.worktrees/s2madm`, rama `inc/ruta-s2-mig-adm-empresa`. Prohibido crear worktrees, `.venv` o
   `node_modules` (el disco va justo). `uv run --active` siempre.
2. **Cada entrega pasa por el ciclo** `implementar → árbitro → (DEVUELTO → corregir → árbitro)* → APROBADO → integrar`.
   Máximo 3 rondas; la 3.ª sin aprobar se escala al orquestador y se registra en `docs/bitacora/`.
3. **Archivos compartidos** (`api/main.py`, `rutas.ts` y su test, `tests/unit/test_api_acceso_por_ruta.py`,
   `tests/unit/test_arquitectura.py`, `CHANGELOG.md`, `docs/api.json`, `docs/ERS.md`, `package.json`): los edita el
   implementador **solo si su tarea lo declara**; si no, entrega el texto exacto y lo aplica el orquestador.
4. **Streamlit no se borra**: la interfaz clásica queda como respaldo hasta que Eugenio decida su retiro (decisión
   registrada, no tomada aquí). La meta es que cada página tenga su equivalente completo en la interfaz nueva.
5. `core/` intacto. Datos ficticios. Commits convencionales en español sin tildes en el asunto, uno por tarea, solo de
   las rutas propias (`git commit <rutas> -m ...`), con el `Co-Authored-By` del manual.
6. Un hallazgo que requiera decidir un requisito (ERS, tutor) se anota como «decisión para Eugenio» en el informe y se
   avanza con el criterio más conservador y reversible.

## 2. Olas

| Ola | Tareas | Concurrencia |
|---|---|---|
| 1 | **T1** integrar las ramas de la arenera y el historial | sola (merge grande en el árbol único) |
| 2a | **T2** Inicio y áreas · **T3** Historial de auditorías · **T4** variaciones atípicas · **T5** Empresas registradas | 4 en paralelo, carpetas disjuntas |
| 2b | **T6** pestaña Asistente de IA · **T7** Revisar un paquete · **T8** pulido de Reajuste y Control · **T9** calidad de pruebas | 4 en paralelo |
| 3 | **T10** Hoja del proyecto: 3a diseño → árbitro → 3b..3e implementación por rebanadas | rebanadas secuenciales |
| 4 | **T11** auditoría visual y suite completa · **T12** cierre y subida | orquestador |

## 3. Tareas

### T1 · Integrar las ramas de la arenera y el historial
- **Fuentes:** `inc/ruta-s4-existencias-react` (contiene `inc/ruta-s4-arenera`; 37 commits propios y migración
  `ins_0003`), el plan de la sesión 4 (`docs/planes/`, `docs/historial`...), la ERS (UC-28, UC-29, UC-30,
  RF-142 a RF-146, RNF-28).
- **Hacer:** `git merge inc/ruta-s4-existencias-react` en el árbol; resolver conflictos conservando lo de **ambos** lados:
  `api/main.py`, `docs/api.json` (regenerar), `CHANGELOG.md`, tablas de acceso, `ui/app.py` (ya sin visor 3D),
  `rutas.ts`, instalador/manifiesto, `docs/ERS.md` (**colisión de numeración**: la migración reservó RF-142–150; si los
  RF-142–146 del historial chocan, deja los del historial como están y renumera/reserva los de la migración con un
  ruling anotado), migraciones (una sola cabeza de Alembic; `ins_0003` en orden), conteos de páginas y de rutas.
  Quita `PENDIENTES_V4` de `tests/unit/test_front_rutas_api.py` (las rutas ya existen).
- **DoD:** merge commit único; `uv run --active alembic heads` con una cabeza; pytest -W error de las pruebas de la
  arenera, el historial, migraciones (`tests/integration/test_migraciones*.py`), `test_arquitectura*`,
  `test_api_acceso_por_ruta`, `test_front_rutas_api`, `test_manifiesto`; `npx vitest run src`, `npm run lint`,
  `npm run build` verdes. Informe con cada conflicto y cómo se resolvió.
- **Propietario de compartidos:** todos (es la integración).

### T2 · Inicio «panel del día», menú por 5 áreas y recorrido «Auditar un libro»
- **Fuentes:** `docs/especificaciones/2026-10-18-silice-ui-inicio-panel-del-dia-design.md` y el manual
  `C:\Users\euger\OneDrive\Escritorio\TESIS\docs\planes\MANUAL_INICIO_AREAS_Y_AUDITORIA_VISUAL.md` (checkout principal);
  el Inicio React ya existe (`src/paginas/inicio`, `PanelArenera`, `UltimasAuditorias`).
- **Hacer:** completar según el spec: barra superior por 5 áreas (Inicio / Auditar / Crear / Producción / Más) con
  descripciones, panel izquierdo con las tres herramientas del módulo, recorrido guiado «Auditar un libro de la
  empresa» (UC-26), conectar con las rutas reales de T1. Sin recargar páginas ya hechas.
- **Propias:** `src/shell/` (menú, cabecera, recorridos), `src/paginas/inicio/`. **Compartidos permitidos:** `rutas.ts`
  y su test. Depende de T1.

### T3 · Historial de auditorías (UC-30)
- **Fuentes:** ERS UC-30, RF-142 a RF-146, RNF-28; rutas `/v1/auditorias-libro*` (T1); la página no existe aún en
  Streamlit: se construye directamente en la interfaz nueva.
- **Hacer primero (parche RM-6, asignado tras el arbitraje de T1):** `api/rutas/libros.py` debe registrar en el historial el resultado de cada auditoria/PDF (`fusion.historial.registrar_resultado` y `registrar_resultado_pdf`), con TDD, sin cambiar el contrato de `/v1/libros/*`; ver `PLAN_SESION_4_HISTORIAL.md` §3. Añade `Cache-Control: no-store` a los GET de `/v1/auditorias-libro` y `/v1/produccion` con prueba.
- **Hacer:** página `src/paginas/historial/` (lista, filtros, detalle de una auditoría guardada, abrir el informe/PDF
  guardado si la API lo ofrece), registro en `rutas.ts`. Si falta una ruta, la añade en `api/rutas/` con su TDD.
- **Compartidos permitidos:** `rutas.ts`, `api/main.py` solo si añade router. Depende de T1.

### T4 · Variaciones atípicas (RF-100) en «Precios de la empresa»
- **Fuentes:** `ui/atipicos.py`, `ui/paginas/precios_empresa.py` (botón «Buscar variaciones atípicas de precio»),
  `tests/integration/test_atipicos.py`, `api/rutas/precios_empresa.py`.
- **Hacer:** mover `ui/atipicos.py` a `aplicacion/atipicos.py` con reexportación (RM-1), actualizar los tests de
  integración y la guardia de importadores; ruta `GET /v1/precios-empresa/listas/{id}/atipicos`; botón y tabla en la
  página React (`src/paginas/precios_empresa/`). Solo lectura: cualquier rol con acceso a la página.
- **Propias:** `aplicacion/atipicos.py`, `ui/atipicos.py`, `api/rutas/precios_empresa.py`,
  `src/paginas/precios_empresa/`, tests de esos. **Compartidos:** `test_arquitectura.py` (solo añadir líneas),
  `docs/api.json` (regenerar).

### T5 · «Empresas registradas» (pestaña de Administración)
- **Fuentes:** `ui/paginas/administracion.py` (`_pestana_registradas`, `_cambiar_registrada`), `seguridad/empresas.py`
  (`registrar_empresa_ajena`, `retirar_ajena`, `revocar_ajena`, `firma.leer_clave_publica`).
- **Hacer:** `api/rutas/admin_empresas_registradas.py` (listar; leer y **previsualizar** un `.silice-clave` subido sin
  guardar; registrar con huella leída por otro canal; retirar con fecha; revocar con motivo o aviso firmado) con
  `administrar(Accion.ADMINISTRAR_EMPRESA)` (solo sesión), CSRF, subida con guardia y tope, `no-store`, errores con los
  mensajes de la clásica; pestaña `src/paginas/administracion/EmpresasRegistradas.tsx`, cablear en `index.tsx` y
  `logica.ts` (`migrada: true`). Patrón: `api/rutas/admin_empresa.py` y `Empresa.tsx`.
- **Compartidos permitidos:** `api/main.py` (router), tabla de acceso, `CHANGELOG.md`, `docs/api.json`.

### T6 · Pestaña «Asistente de IA» (Administración)
- **Fuentes:** `ui/paginas/administracion.py` (`pestana_asistente` y sus helpers), `asistente/administracion.py`,
  `asistente/clave.py`, `asistente/configuracion.py`, `asistente/instalacion.py`.
- **Hacer:** rutas `api/rutas/admin_asistente.py`: leer estado (activo, proveedor, modelos, tope de costo, clave
  registrada **enmascarada**, si el extra `ia` está), guardar configuración, registrar / reactivar / olvidar la clave de
  IA (`administrar_en_el_equipo(Sensible.CLAVE_DE_IA)`, secretos solo en el cuerpo, jamás devueltos, eco nulo, evento de
  seguridad por intento fallido de reactivar como en la clásica); pestaña React `Asistente.tsx`; sin gasto real: las
  pruebas usan dobles del almacén de credenciales. **No** migrar el panel de chat del asistente (otra pantalla).
- **Compartidos permitidos:** como T5. Patrón: `Empresa.tsx`, `ClavesApi.tsx`.

### T7 · Revisar un paquete
- **Fuentes:** `ui/paginas/revisar.py`, `ui/revision.py`, `paquete/`, `auditoria/` (reauditoría en memoria,
  `POST /v1/auditorias`), `api/rutas/auditorias.py`.
- **Hacer:** página `src/paginas/revisar/` con la misma funcionalidad: subir un `.silice` (guardia y tope), verificar
  firma y cadena, mostrar el resumen, los hallazgos y la reauditoría; lógica sin Streamlit a `aplicacion/revision.py`
  con reexportación; rutas nuevas en `api/rutas/revision.py` si hace falta. Lo que la clásica muestre, la nueva lo
  muestra (incluidos los mensajes de paquete rechazado).
- **Compartidos permitidos:** `rutas.ts`, `api/main.py`, tabla de acceso, `CHANGELOG.md`, `docs/api.json`.

### T8 · Pulido de Reajuste y Control (V-17 y V-26+)
- **Hacer:** Reajuste: fechas con el selector de fecha común (hoy texto AAAA-MM-DD), formulario agrupado (pasos o
  pestañas), español llano; Control: tablas de resultados con es-VE y el exacto accesible, cifras tabulares; quitar la
  ranura de cabecera del Shell si ya nadie la usa; «Periodo» → «Período» en toda la interfaz nueva.
- **Propias:** `src/paginas/reajuste/`, `src/paginas/control/`, `src/shell/` (solo la ranura), `src/comun/` (solo si
  imprescindible; corre todos los tests).

### T9 · Calidad de pruebas
- **Hacer:** (1) estabilizar `src/paginas/componer/index.test.tsx` («el desglose se pide una sola vez, 300 ms…») con
  temporizadores falsos de Vitest, sin subir tiempos de espera; (2) los 2 errores de `ruff` que vienen de la base
  (`tests/unit/test_arquitectura_s2.py`, `tests/unit/test_ui_tablero.py` y los que `uv run --active ruff check .`
  liste); (3) las pruebas AppTest de Streamlit que agotan 3 s: subir el `default_timeout` en un único lugar común
  (fixture/conftest) y documentar por qué, sin tocar las pruebas una a una; (4) lector `.xls` real: documentar que la
  prueba con archivo real corre solo donde está `xlrd` **sin** skip (usa el `xlrd` falso ya existente para la lógica) y
  dejar el caso real en `docs/bitacora/` como verificación manual pendiente.
- **Propias:** `tests/`, `conftest.py`, y esas pruebas del front. No cambia comportamiento de producción.

### T10 · Hoja del proyecto (la mayor: `ui/paginas/hoja.py` 2308 líneas + `ui/hoja.py` 2835)
- **3a Diseño (primero, sin código):** documento `docs/especificaciones/2026-10-19-hoja-react-design.md` con: inventario
  de lo que hace la página clásica (lectura de la hoja, tablas editables, borrador fuera de widgets, estado aparte,
  validaciones, guardado con cadena/sello, exportación a Excel, asistente embebido que **no** se migra), contrato de
  API por rebanada, división en 3b..3e con pruebas por rebanada, riesgos y qué queda fuera. Lo juzga el árbitro como
  documento (criterios B4, B2, C1, D1 aplicados al diseño). Sin aprobación del diseño no hay código.
- **3b..3e Implementación** por rebanadas (lectura y navegación · edición y borrador · validación y estado · guardado,
  versiones y exportación), cada una con su ciclo implementador → árbitro. Lógica a `aplicacion/hoja*.py` con
  reexportación (`ui/hoja.py` no se mueve de golpe: solo lo que la rebanada necesite, y `asistente/*` lo sigue
  importando).

### T11 · Verificación final (orquestador)
Suite completa una sola vez (`uv run --active pytest -W error -p no:cacheprovider`, `npx vitest run src`, lint, build),
auditoría visual a 1366×768 con datos ficticios (incluye Elaborar y Reajuste con resultado, Entregar generando el
paquete, 1056 px, teclado, zona de soltar archivo), informe en `docs/bitacora/`.

### T12 · Cierre y subida
CHANGELOG y `api.json` al día, bitácora, push de la rama. El PR y la fusión a `main` los decide Eugenio salvo
autorización expresa; el retiro de Streamlit queda como decisión pendiente documentada.

## 4. Registro de ciclos (lo llena el orquestador)

| Tarea | Implementador | Ronda | Veredicto | SHA |
|---|---|---|---|---|
| T1 | subagente T1 | 1 | APROBADO (arbitro independiente) | e79e196 |
| T2 | subagente T2 | 1 | APROBADO; 6 menores corregidos | 70ffa25 |
| T3 | subagente T3 | 1 | APROBADO; 3 menores corregidos | d91ff44 |
| T4 a T8 | tesis-b9 con sus subagentes | 1 a 2 | APROBADO (arbitros independientes; T4 y T7 con una devolucion) | 3a1dda3 (fusionado en 275946c) |
| T10a (diseno de la Hoja) | subagente T10a | 3 + 1 | APROBADO POR EL ORQUESTADOR tras 3 rondas (3 MAYOR de texto, verificados por el) | 0e0427c |
