# Estado del proyecto

**Actualizado:** 2026-11-04 · lo mantiene el orquestador (Claude) al cerrar cada fase o al fusionar un PR.

Esta página es la **única fuente del estado actual**. Los planes de la raíz y de [planes/](planes/) y
la [bitácora](bitacora/) cuentan cómo se llegó aquí; si dicen otra cosa, manda esta página. Las cifras
de pruebas y de requisitos no se repiten aquí: viven en su fuente ([metodologia.md §5](metodologia.md)).

## 1. Qué hay en `main`

`main` = **el programa completo** desde el 2026-11-02 (PR #98) y, desde el 2026-11-04, **con el
rediseño F4** (PR #101, `fa47009d`: la obra por secciones y el Presupuesto en seis pestañas, probado en
vivo en Chromium antes de fusionar). Contiene:

- API FastAPI (`api/`) e interfaz React (`frontend-desktop/`) en un solo proceso Uvicorn. Streamlit y
  el Visor 3D se retiraron el 2026-10-21 (enmienda de [arquitectura.md](arquitectura.md)).
- Módulos Auditoría, Presupuestos y obras, y Producción (plan vial y de agregados completo).
- Instalador con huella SHA-256 firmada (Ed25519), primer administrador por código de instalación.

## 2. PR abiertos

| PR | Rama | Qué trae | Estado |
|---|---|---|---|
| #103 | `feature/disenos-f5` | La cadena tras F4, con sus commits en orden: Tarea 16c (ligante en la receta), manual de usuario F4 y diseños F5 (presupuesto vial, ventana de escritorio con pywebview) | Probado en vivo junto con #104; CI en curso. Va primero |
| #104 | `feature/f5-pulido` | Pulido F5, tandas 1 y 2; ya trae unida la cadena de #103 con el CHANGELOG resuelto | Probado en vivo; CI en curso. Va después de #103 |
| #102 | `docs/contexto-agentes` | `AGENTS.md`, este archivo, skills y puente MCP con Antigravity | Va al final, con este archivo al día |
| #100 | `feature/nucleo-alias-ton-litro` | Alias «ton»→t y «lt»/«litro»→l en el núcleo (expediente NUC-E1) | **No fusionar** sin el aval del tutor: cambia cómo se leen unidades ya guardadas y toca `core/contracts/unidades.py`, que está en `archivos_del_auditor` de `asistente/experimento/protocolo.json`: exige recongelar el experimento o falla `test_experimento_congelado_vigente.py` |

Los `.worktrees/` son copias de ramas de trabajo y **no** describen el programa actual. El 2026-11-04 se
quitaron 20 ya fusionados; quedan 28 (ver §3).

## 3. Lo que espera a Eugenio

1. Rediseño del marco: el **sidebar al estilo de módulos** y la **barra superior por obra** no se hicieron.
   Antigravity prepara un plan; el orquestador lo contrasta con
   [especificaciones/2026-10-25-modulos-design.md](especificaciones/2026-10-25-modulos-design.md) y con el marco
   actual antes de construir.
2. Decisiones ratificadas en bloque el 2026-11-04
   ([bitacora/2026-10-30-preguntas-para-eugenio.md](bitacora/2026-10-30-preguntas-para-eugenio.md)); quedan
   **a cotejar con el tutor** las que dependen de una fuente externa (IVSS, ligante, proxy de asfalto,
   tolerancia de receta, pintura, `t·km` y el IVA 16 %). Otra lista con datos de la empresa vive **solo en su
   equipo**.
3. Decidir si quien revisa debe ver las obras de todas las carpetas: hoy solo ve la de la empresa
   (`_carpetas_visibles` en `api/rutas/obras.py`, igual antes de F4), y un enlace a una obra de otra
   carpeta le dice «Esa obra ya no existe».
4. Worktrees que quedan (28): con bases o respaldos ignorados (en `.claude/worktrees/prototipo` hay una
   `data/apu.db` que conviene mirar), con cambios sin guardar o con ramas que no están en `main`. Lista
   en «Limpieza de worktrees TESIS (2026-11-03).md» de su Escritorio, sección «No tocados».
5. Revisar unas carpetas vacías que un agente dejó en `C:\c\Users\...` (no se borraron sin mirarlas).
6. Tesis: aval del tutor para lo que toca `core/` (PR #100), mediciones con personas (Med) y la
   respuesta de la Dirección de Investigación sobre la mención de publicación.

## 4. Trabajo técnico pendiente

- Menores vistos en la prueba en vivo del 2026-11-04 (no bloquean): la tabla de cambios de «Guardar
  versión» muestra la cantidad con punto decimal («24.5»); los avisos dicen «del proyecto» en vez de
  «de la obra»; «Cadena íntegra: 1 versiones»; el registro de cambios muestra la hora con microsegundos
  y nombres internos sin tilde («version», «creacion»); la cabecera de una obra nueva en una carpeta sin
  moneda dice «Carpeta sin moneda declarada» y no la moneda de la obra; «m3» en Aprobaciones y «m³» en
  la Hoja.
- Del recorrido en video del 2026-11-01 (confirmados por la auditoría del 2026-11-04 y, el 401, en
  vivo): 401 al cerrar sesión con la Hoja abierta (el desmontaje de `useBorrador.ts` borra el borrador
  después de `DELETE /v1/sesion`); 404 en consola al abrir «Producir mezcla» (`useMezclas.ts` pide la
  receta de todos los materiales activos); «Sin cálculo» en todas las filas de tramos
  (`aplicacion/hoja_vista.py` envía `calculo=None` para los tramos); «Trayectorias por corte» queda bajo
  «Proyectar» (`RiesgoDeLaObra.tsx`); botones sin nombre accesible en el Visor (3, del preset de
  Univer) y en Administración (2).
- Implementar los diseños de #103 cuando Eugenio responda sus preguntas; la ventana de escritorio exige
  enmendar RT-3 y RT-5, que todavía dicen Tauri.
- Asistente de IA: la tarea T20 espera autorización de gasto.

## 5. Auditorías en paralelo

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
