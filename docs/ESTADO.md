# Estado del proyecto

**Actualizado:** 2026-11-04 · lo mantiene el orquestador (Claude) al cerrar cada fase o al fusionar un PR.

Esta página es la **única fuente del estado actual**. Los planes de la raíz y de [planes/](planes/) y
la [bitácora](bitacora/) cuentan cómo se llegó aquí; si dicen otra cosa, manda esta página. Las cifras
de pruebas y de requisitos no se repiten aquí: viven en su fuente ([metodologia.md §5](metodologia.md)).

## 1. Qué hay en `main`

`main` = **el programa completo** desde el 2026-11-02 (PR #98, `22ff8021`; antes PR #99 con VB-1 del
núcleo). Contiene:

- API FastAPI (`api/`) e interfaz React (`frontend-desktop/`) en un solo proceso Uvicorn. Streamlit y
  el Visor 3D se retiraron el 2026-10-21 (enmienda de [arquitectura.md](arquitectura.md)).
- Módulos Auditoría, Presupuestos y obras, y Producción (plan vial y de agregados completo).
- Instalador con huella SHA-256 firmada (Ed25519), primer administrador por código de instalación.

Lo que **no** está en `main` todavía: el rediseño F4, el pulido F5, la Tarea 16c, el manual nuevo y
los diseños de la ventana de escritorio y del presupuesto vial (sección 2).

## 2. Ramas vivas en GitHub

| Rama | PR | Qué trae | Estado |
|---|---|---|---|
| `feature/rediseno-f4` | #101 | La obra por secciones y el Presupuesto en seis pestañas | CI verde; **espera la prueba de Eugenio en navegador y su fusión** (merge commit) |
| `feature/f5-pulido` | — | Pulido F5, tandas 1 y 2 (CSV con coma decimal, Entregar sin callejón, textos) | Aprobada por el orquestador; PR después de fusionar #101 |
| `feature/vial-16c` | — | Tarea 16c: el ligante marcado en la receta de la planta | Aprobada; PR después de #101 |
| `feature/manual-f4` | — | Manual de usuario de la interfaz F4 (sale de `vial-16c`) | Hecho; al fusionar, sumarle los textos nuevos de F5 tanda 2 |
| `feature/disenos-f5` | — | Diseños: presupuesto vial y ventana de escritorio (pywebview); manual de instalación al día (sale de `manual-f4`) | Solo diseño; preguntas para Eugenio en cada especificación |
| `feature/nucleo-alias-ton-litro` | #100 | Alias «ton»→t y «lt»/«litro»→l en el núcleo (expediente NUC-E1) | **No fusionar** sin el aval del tutor: cambia cómo se leen unidades ya guardadas. Además toca `core/contracts/unidades.py`, que está en `archivos_del_auditor` de `asistente/experimento/protocolo.json`: fusionarla exige recongelar el experimento o falla `test_experimento_congelado_vigente.py` |

Orden propuesto de fusión: #101 → `vial-16c` → `manual-f4` → `disenos-f5` → `f5-pulido` (cada una
con su PR y la CI en verde). El checkout principal puede estar en una rama local de trabajo; los
`.worktrees/` son copias de ramas viejas y **no** describen el programa actual.

## 3. Lo que espera a Eugenio

1. Probar F4 en el navegador y fusionar el PR #101.
2. Responder o ratificar las decisiones tomadas en su ausencia:
   [bitacora/2026-10-30-preguntas-para-eugenio.md](bitacora/2026-10-30-preguntas-para-eugenio.md), los
   `bitacora/2026-10-31-preguntas-*.md` y la sección de preguntas de `docs/bitacora/2026-11-03-cierre-f4.md`
   (en la rama F4). Otra lista con datos de la empresa vive **solo en su equipo**.
3. Limpiar los worktrees viejos con la lista verificada que quedó en su Escritorio («Limpieza de
   worktrees TESIS (2026-11-03).md»); el agente no puede borrarlos. Hay 48 además del checkout
   principal y NORMAS §3 permite 3. En `.claude/worktrees/prototipo`
   hay una `data/apu.db` que conviene mirar antes.
4. Revisar unas carpetas vacías que un agente dejó en `C:\c\Users\...` (no se borraron sin mirarlas).
5. Tesis: aval del tutor para lo que toca `core/` (PR #100), mediciones con personas (Med) y la
   respuesta de la Dirección de Investigación sobre la mención de publicación.

## 4. Trabajo técnico pendiente

- F5: los hallazgos H6 y H10 del recorrido en navegador de F4, y el texto de `aplicacion/mesa.py`
  (H9 se arregló solo en el cliente).
- Del recorrido en video del 2026-11-01, abiertos también en `feature/f5-pulido` (los verificó la
  auditoría del 2026-11-04): 401 al cerrar sesión con la Hoja abierta (el desmontaje de
  `useBorrador.ts` borra el borrador después de `DELETE /v1/sesion`); 404 en consola al abrir
  «Producir mezcla» (`useMezclas.ts` pide la receta de todos los materiales activos); «Sin cálculo» en
  todas las filas de tramos (`aplicacion/hoja_vista.py` envía `calculo=None` para los tramos);
  «Trayectorias por corte» queda bajo «Proyectar» (`RiesgoDeLaObra.tsx`); botones sin nombre accesible
  en el Visor (3, del preset de Univer) y en Administración (2). Van en la rama de pulido, después de
  fusionar F4.
- Implementar los diseños de `feature/disenos-f5` cuando Eugenio responda sus preguntas; la ventana de
  escritorio exige enmendar RT-3 y RT-5, que todavía dicen Tauri.
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
