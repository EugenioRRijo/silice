# Estado del proyecto

**Actualizado:** 2026-11-06 · lo mantiene el orquestador (Claude) al cerrar cada fase o al fusionar un PR.

Esta página es la **única fuente del estado actual**. Los planes de la raíz y de [planes/](planes/) y
la [bitácora](bitacora/) cuentan cómo se llegó aquí; si dicen otra cosa, manda esta página. Las cifras
de pruebas y de requisitos no se repiten aquí: viven en su fuente ([metodologia.md §5](metodologia.md)).

## 1. Qué hay en `main`

`main` = **el programa completo** (PR #98, 2026-11-02) y, desde el 2026-11-04:
- **Rediseño F4** (PR #101, `fa47009d`): la obra por secciones y el Presupuesto en seis pestañas.
- **Tarea 16c, manual de usuario F4 y diseños F5** (PR #103, `7dcdc5c9`): el ligante en la receta de la planta, el
  manual nuevo y los diseños del presupuesto vial y de la ventana de escritorio (solo diseño).
- **Pulido F5, tandas 1 y 2** (PR #104, `febf6673`).
- **Contexto para agentes y puente con Antigravity** (PR #102, `076793b8`): `AGENTS.md`, esta página y las skills.

Se probaron en vivo en Chromium con la siembra ficticia antes de fusionar. Contiene también la API FastAPI (`api/`) y
la interfaz React (`frontend-desktop/`) en un solo proceso Uvicorn (Streamlit y el Visor 3D se retiraron el 2026-10-21,
enmienda de [arquitectura.md](arquitectura.md)), los módulos Auditoría, Presupuestos y obras, y Producción, y el
instalador con huella SHA-256 firmada.

## 2. PR y ramas abiertas

| PR o rama | Qué trae | Estado |
|---|---|---|
| #105 `fix/reloj-pruebas-hoja` | Dos pruebas de la Hoja (R6, R7) que desde el 2026-11-05 caían por el reloj del equipo | CI en verde: Eugenio lo fusiona; sin él, la CI de cualquier PR contra `main` cae |
| #106 `feature/f6-espacios` | Rediseño F6 completo (§3) | Arbitrado y corregido; espera la prueba de Eugenio en el navegador y la fusión |
| #107 `feature/autocompletado` | Autocompletado guiado AC1–AC4 (§3) | Árbitro xhigh: aprobado en la ronda 4; espera #105 (r6/r7) y la prueba de Eugenio |
| `feature/tanda-detalles` | Tanda de detalles D1–D16 (§3), sobre F6 y el autocompletado unidos | En arbitraje; sin PR hasta que se fusionen #106 y #107 |
| #100 `feature/nucleo-alias-ton-litro` | Alias «ton»→t y «lt»/«litro»→l en el núcleo (expediente NUC-E1) | **No fusionar** sin el aval del tutor. Ya tiene `main` unido y el experimento recongelado con acta (`docs/bitacora/2026-11-04-recongelado-experimento.md` en su rama) |

Los `.worktrees/` son copias de ramas de trabajo y **no** describen el programa actual. F6 vive en `.worktrees/s2m3`, el
autocompletado en el checkout principal y la tanda en `.worktrees/tanda`; cada tarea de la tanda tuvo su árbol
`.worktrees/td-*` (autorización de Eugenio del 2026-11-06), que se quita al cerrar la fase.

## 3. Trabajo en curso

**Rediseño F6, espacios enrutados** (PR #106; [plan](planes/PLAN_REDISENO_F6.md),
[seguimiento](bitacora/2026-11-04-f6-construccion.md)). La app abre en la **Vista general**; barra lateral plana; cada
obra con su barra de secciones; la Cuenta reúne preferencias, cuentas, empresa, carpetas, sistema y ayuda. Árbitro final
de Claude xhigh: aprobado con condiciones, ya corregidas. Decisiones de Eugenio del 2026-11-05: «Presupuesto | Componer»,
cabecera compacta del Presupuesto, quien revisa ve y abre las obras de todas las carpetas (`abrir_carpeta`), y la
demostración nunca se mezcla con las carpetas de la empresa (fuera de ella no se lista).

**Autocompletado guiado** (PR #107; [plan](planes/PLAN_AUTOCOMPLETADO.md)): AC1–AC4 hechos (Componer con el precio de la
lista con que arma la carpeta, Control, Reajuste, Escenarios, Simulador, unidades, moneda, proveedor y versión de
comprobación); RF-167, RF-168 y RNF-29 en el ERS.

**Tanda de detalles D1–D16** ([plan](planes/PLAN_TANDA_DETALLES.md),
[arbitraje](bitacora/arbitrajes/tanda-detalles-claude-xhigh.md)). Construida el 2026-11-06 en cinco líneas en paralelo.
La ronda 1 del árbitro xhigh la devolvió con 2 MAYOR (D10 rompía la flecha izquierda de las pestañas; D16 seguía
mezclando la partida con Esc) y 13 MENOR; los dos MAYOR y los MENOR 1–11 están corregidos con prueba en rojo primero (el
12 es historia de commits y no se reescribe). Gemini Flash construyó solo parte de los parches: con la máquina cargada
agotó su tiempo varias veces y esas tareas las hicieron subagentes de Claude con TDD. Notas: la frase «Cadena íntegra: N
versiones» de `core/` sigue igual y la concordancia se corrige en `aplicacion/texto_cadena.py` hasta que el tutor avale
tocar el núcleo.

## 4. Lo que espera a Eugenio

1. Fusionar en GitHub, en este orden y con merge commit: #105 (CI verde), #106 (F6) y #107 (autocompletado), cada
   uno después de probarlo en el navegador. Claude no puede fusionar: el control de permisos de Claude Code lo bloquea.
2. Probar la tanda de detalles en el navegador, en especial la columna «Estado» del Presupuesto a 1366 px (D13) y la
   tabla apilada de la Vista general (D14), que jsdom no mide.
3. Decisiones ratificadas en bloque el 2026-11-04
   ([bitacora/2026-10-30-preguntas-para-eugenio.md](bitacora/2026-10-30-preguntas-para-eugenio.md)); quedan **a cotejar
   con el tutor** las que dependen de una fuente externa (IVSS, ligante, proxy de asfalto, tolerancia de receta,
   pintura, `t·km` y el IVA 16 %). Otra lista con datos de la empresa vive **solo en su equipo**.
4. Responder las preguntas de los diseños de F5 (presupuesto vial, §10 de su especificación; ventana de escritorio) para
   poder construirlos.
5. El asistente de IA (T20): «luego» (2026-11-05), sin gasto por ahora.
6. Worktrees que quedan (28): con bases o respaldos ignorados (en `.claude/worktrees/prototipo` hay una `data/apu.db` que
   conviene mirar), con cambios sin guardar o con ramas que no están en `main`. Lista en «Limpieza de worktrees TESIS
   (2026-11-03).md» de su Escritorio, sección «No tocados».
7. Negar en el IDE de Antigravity la lectura de `docs/auditoria` y `data/confidencial` (en su línea de comandos ya está).
8. Revisar unas carpetas vacías que un agente dejó en `C:\c\Users\...`.
9. Tesis: aval del tutor para el PR #100, mediciones con personas (Med) y la respuesta de la Dirección de Investigación.

## 5. Trabajo técnico pendiente (orden recomendado)

Plan detallado, con el protocolo de trabajo con Gemini Flash por `agy` (Flash construye el parche, Claude lo aplica con
TDD y lo audita; árbitro de Claude xhigh en cada compuerta): [planes/PLAN_TANDA_DETALLES.md](planes/PLAN_TANDA_DETALLES.md).

1. **Tanda de detalles**: construida (§3); falta cerrar su arbitraje.
2. **Autocompletado**: completo (PR #107).
3. **F7 Ayuda**: «¿Qué es esto?» en cada sección, guías por tarea, glosario y «Empieza aquí» (con la primera entrada y el
   primer administrador desde la interfaz).
4. **F8 Cierre del rediseño**: retirar las redirecciones viejas; poner al día `scripts/recorrido_ux_playwright.py`, que
   aún navega por el menú de módulos retirado (modos de pantallas, `--funcional` y `--umbrales`); pasada única en
   navegador a 1056/1366/1920; comparación de líneas contra la línea base; el tamaño del front (14,4 MB de 15).
5. Implementar los diseños de F5 (presupuesto vial, ventana de escritorio) cuando Eugenio responda sus preguntas; la
   ventana exige enmendar RT-3 y RT-5, que todavía dicen Tauri.

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
