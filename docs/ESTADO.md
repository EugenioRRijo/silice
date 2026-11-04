# Estado del proyecto

**Actualizado:** 2026-11-04 · lo mantiene el orquestador (Claude) al cerrar cada fase o al fusionar un PR.

Esta página es la **única fuente del estado actual**. Los planes de la raíz y de [planes/](planes/) y
la [bitácora](bitacora/) cuentan cómo se llegó aquí; si dicen otra cosa, manda esta página. Las cifras
de pruebas y de requisitos no se repiten aquí: viven en su fuente ([metodologia.md §5](metodologia.md)).

## 1. Qué hay en `main`

`main` = **el programa completo** (PR #98, 2026-11-02) y, desde el 2026-11-04:
- **Rediseño F4** (PR #101, `fa47009d`): la obra por secciones y el Presupuesto en seis pestañas.
- **Tarea 16c, manual de usuario F4 y diseños F5** (PR #103, `7dcdc5c9`): el ligante en la receta de la planta, el
  manual nuevo y los diseños del presupuesto vial y de la ventana de escritorio (solo diseño).
- **Pulido F5, tandas 1 y 2** (PR #104, `febf6673`).

Los tres se probaron en vivo en Chromium con la siembra ficticia antes de fusionar. Contiene también la API FastAPI
(`api/`) y la interfaz React (`frontend-desktop/`) en un solo proceso Uvicorn (Streamlit y el Visor 3D se retiraron el
2026-10-21, enmienda de [arquitectura.md](arquitectura.md)), los módulos Auditoría, Presupuestos y obras, y Producción,
y el instalador con huella SHA-256 firmada.

## 2. PR y ramas abiertas

| PR o rama | Qué trae | Estado |
|---|---|---|
| #102 `docs/contexto-agentes` | `AGENTS.md`, este archivo, las skills y el puente MCP con Antigravity | Con `main` unido; va a fusionarse cuando su CI esté en verde |
| `docs/plan-f6` (sin PR) | Rediseño F6: plan, contrato de rutas y diseño visual de F6a | Diseño en curso; ver §3 |
| #100 `feature/nucleo-alias-ton-litro` | Alias «ton»→t y «lt»/«litro»→l en el núcleo (expediente NUC-E1) | **No fusionar** sin el aval del tutor. Ya tiene `main` unido y el experimento recongelado con acta (`docs/bitacora/2026-11-04-recongelado-experimento.md` en su rama) |

Los `.worktrees/` son copias de ramas de trabajo y **no** describen el programa actual. El 2026-11-04 se quitaron 20 ya
fusionados; quedan 28 (ver §4).

## 3. Rediseño F6 (espacios enrutados)

- **Orquesta esta sesión de Claude** (decisión de Eugenio, 2026-11-04); Antigravity hace el diseño visual y arbitra. Había
  dos planes (el de `docs/plan-f6` y uno T0–T9 de otra sesión de Claude que Antigravity tomó como base): se unifican en
  uno solo sobre `main`.
- **Decisiones de Eugenio (2026-11-04):**
  - totales de la cartera en la Vista general **separados por moneda** (Bs y USD), con una ruta nueva en el servidor;
  - las pantallas atadas a una obra pasan a **subvistas de su sección**: Reajuste, Escenarios y Tablero en Control de
    obra o Resumen; Actualizar precios en Mercado; Revisar un paquete y Entregar en Aprobaciones; Componer en
    Presupuesto. Precios y catálogo se queda con Precios de la empresa, Catálogo, Índices y Simulador;
  - **español llano** en todo texto visible;
  - el tamaño de letra pasa **solo a la Cuenta**;
  - se **enmienda** DESIGN.md y la especificación del 2026-10-26: la app abre en la **Vista general**, que pone primero
    lo que bloquea;
  - la rama de F6 se abre **desde `main`**, sin apilarla sobre ramas sin fusionar.

## 4. Lo que espera a Eugenio

1. Aprobar el plan unificado de F6 y su T0 (enmienda, mapa de las 31 pantallas y diseño visual) antes de construir.
2. Decidir si quien revisa debe ver las obras de todas las carpetas: hoy solo ve la de la empresa
   (`_carpetas_visibles` en `api/rutas/obras.py`), y un enlace a una obra de otra carpeta le dice «Esa obra ya no
   existe».
3. Decisiones ratificadas en bloque el 2026-11-04
   ([bitacora/2026-10-30-preguntas-para-eugenio.md](bitacora/2026-10-30-preguntas-para-eugenio.md)); quedan **a cotejar
   con el tutor** las que dependen de una fuente externa (IVSS, ligante, proxy de asfalto, tolerancia de receta,
   pintura, `t·km` y el IVA 16 %). Otra lista con datos de la empresa vive **solo en su equipo**.
4. Worktrees que quedan (28): con bases o respaldos ignorados (en `.claude/worktrees/prototipo` hay una `data/apu.db` que
   conviene mirar), con cambios sin guardar o con ramas que no están en `main`. Lista en «Limpieza de worktrees TESIS
   (2026-11-03).md» de su Escritorio, sección «No tocados».
5. Negar en el IDE de Antigravity la lectura de `docs/auditoria` y `data/confidencial` (en su línea de comandos ya está).
6. Revisar unas carpetas vacías que un agente dejó en `C:\c\Users\...`.
7. Tesis: aval del tutor para el PR #100, mediciones con personas (Med) y la respuesta de la Dirección de Investigación.

## 5. Trabajo técnico pendiente

- Menores vistos en la prueba en vivo del 2026-11-04 (no bloquean): la tabla de cambios de «Guardar versión» muestra la
  cantidad con punto decimal («24.5»); los avisos dicen «del proyecto» en vez de «de la obra»; «Cadena íntegra: 1
  versiones»; el registro de cambios muestra la hora con microsegundos y nombres internos sin tilde; la cabecera de una
  obra nueva en una carpeta sin moneda dice «Carpeta sin moneda declarada» y no la moneda de la obra; «m3» en
  Aprobaciones y «m³» en la Hoja.
- Del recorrido en video del 2026-11-01 (confirmados por la auditoría del 2026-11-04): 401 al cerrar sesión con la Hoja
  abierta (lo arregla la Cuenta de F6); 404 en consola al abrir «Producir mezcla» (`useMezclas.ts`); «Sin cálculo» en
  las filas de tramos (`aplicacion/hoja_vista.py`); «Trayectorias por corte» bajo «Proyectar» (`RiesgoDeLaObra.tsx`);
  botones sin nombre accesible en el Visor (3) y en Administración (2).
- El recorrido guiado de la auditoría no marca su paso 1 en `/empresa/auditoria` (deducido del código; F6 lo prueba y lo
  arregla con una ruta canónica por pantalla).
- Implementar los diseños de F5 (presupuesto vial, ventana de escritorio) cuando Eugenio responda sus preguntas; la
  ventana exige enmendar RT-3 y RT-5, que todavía dicen Tauri.
- Asistente de IA: la tarea T20 espera autorización de gasto.

## 6. Auditorías en paralelo

Cuando otro agente (por ejemplo, Antigravity) audita a la vez, sus hallazgos van a
`bitacora/auditoria-agy-AAAA-MM-DD.md` y el orquestador escribe al lado el veredicto (confirmado,
falso positivo o ya resuelto en una rama). Lista abierta:
[bitacora/auditoria-agy-2026-11-04.md](bitacora/auditoria-agy-2026-11-04.md).

En la otra dirección, el orquestador le encarga trabajo a Antigravity con el subagente
`silice-antigravity` (`.claude/agents/silice-antigravity.md`), que llama a
`agy -p "…" --sandbox </dev/null`, siempre en modo de solo lectura, o directamente con el servidor MCP
`antigravity` (`scripts/mcp_antigravity.py`, registrado en `.mcp.json`: herramientas
`encargar_a_antigravity` y `arbitrar_rama`). Los permisos de `agy` viven fuera del repositorio, en
`~/.gemini/antigravity-cli/settings.json`: `proceed-in-sandbox`, comandos de lectura permitidos y
lectura de `docs/auditoria` y `data/confidencial` negada (comprobado con un archivo ficticio).
