# Estado del proyecto

**Actualizado:** 2026-11-05 · lo mantiene el orquestador (Claude) al cerrar cada fase o al fusionar un PR.

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
| #105 `fix/reloj-pruebas-hoja` | Dos pruebas de la Hoja (R6, R7) que desde el 2026-11-05 caían por el reloj del equipo | Listo: Eugenio lo fusiona en GitHub; sin él, la CI de cualquier PR contra `main` cae |
| `feature/f6-espacios` | Rediseño F6 completo (§3) | Construido, arbitrado y con los hallazgos corregidos; PR a `main` para que Eugenio lo pruebe y lo fusione |
| `feature/autocompletado` | Autocompletado guiado (§3) | En curso: AC1, AC1b, AC2 y AC2c hechos; faltan AC3 y AC4 |
| #100 `feature/nucleo-alias-ton-litro` | Alias «ton»→t y «lt»/«litro»→l en el núcleo (expediente NUC-E1) | **No fusionar** sin el aval del tutor. Ya tiene `main` unido y el experimento recongelado con acta (`docs/bitacora/2026-11-04-recongelado-experimento.md` en su rama) |

Los `.worktrees/` son copias de ramas de trabajo y **no** describen el programa actual. El 2026-11-04 se quitaron 20 ya
fusionados; quedan 28 (ver §4). La rama de F6 vive en `.worktrees/s2m3`; la del autocompletado, en el checkout
principal.

## 3. Trabajo en curso

**Rediseño F6, espacios enrutados** ([plan](planes/PLAN_REDISENO_F6.md),
[seguimiento](bitacora/2026-11-04-f6-construccion.md)). T0–T9 hechas. La app abre en la **Vista general** (lo que
bloquea primero, la cartera separada por moneda, el avance contra el plan, las últimas auditorías y la arenera); la barra
lateral es plana; cada obra tiene su barra de secciones con subvistas; la Cuenta reúne preferencias (el tamaño de letra),
cuentas, empresa, carpetas, sistema y ayuda. Arbitrajes en [bitacora/arbitrajes/](bitacora/arbitrajes/): Antigravity
(Argon y Flash) en T1–T8 y, sin cuota de Argon ni de Opus en Antigravity, el **árbitro final fue un revisor de Claude con
esfuerzo xhigh** (decisión de Eugenio, 2026-11-05): aprobado con condiciones; sus dos mayores (los enlaces del contenido
a otra carpeta perdían el borrador sin preguntar; la cartera sumaba la demostración) y siete menores están corregidos con
su prueba en rojo primero.

Decisiones de Eugenio del 2026-11-05 dentro de F6:
- el conmutador de Presupuesto dice «Presupuesto | Componer»;
- **cabecera compacta del Presupuesto**: a 1366×768 con letra Normal la primera partida pasa de 1.069 px a 622 px;
- **quien revisa ve y abre las obras de todas las carpetas**: la acción nueva `abrir_carpeta` (abrir y listar) se separa
  de `cambiar_caso` (crear y subir carpetas, sin revisa); la carpeta abierta sigue siendo de cada sesión;
- los datos de la **demostración nunca se mezclan** con los reales: fuera de ella no se listan; dentro, solo los suyos.

**Autocompletado guiado** (pedido de Eugenio del 2026-10-21, auditoría del 2026-11-05). Reutiliza `CampoConBusqueda`.
- Hecho: descripción del insumo en Componer (insumos y oficios de mano de obra), con el precio de la lista con que arma
  la carpeta a la fecha de la composición, que no se copia si la moneda no coincide (AC1, AC1b); partida del contrato en
  Control y Reajuste y serie de índices en Reajuste, con rutas nuevas de solo lectura (AC2, AC2c).
- Falta: insumo en Escenarios y en el Simulador, que pide selección múltiple (AC3); unidades, moneda, proveedor y versión
  de comprobación (AC4).

## 4. Lo que espera a Eugenio

1. Fusionar el PR #105 en GitHub cuando su CI esté en verde.
2. Probar F6 en el navegador y fusionar su PR (merge commit).
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

1. **Tanda de detalles** (chicos, en paralelo):
   - vistos el 2026-11-04: la cantidad con punto en «Guardar versión», «del proyecto» por «de la obra», «1 versiones»,
     la hora con microsegundos, «Carpeta sin moneda declarada», «m3» y «m³»;
   - del video del 2026-11-01: 404 al abrir «Producir mezcla» (`useMezclas.ts`), «Sin cálculo» en las filas de tramos
     (`aplicacion/hoja_vista.py`), «Trayectorias por corte» bajo «Proyectar» (`RiesgoDeLaObra.tsx`) y botones sin nombre
     accesible en el Visor (3) y en Administración (2);
   - del árbitro final de F6: «Versión vigente» del Resumen también es la de la línea base cuando existe; la ayuda del
     «Total» de la cartera solo vive en la API; la columna «Estado» del Presupuesto queda cortada a 1366 px; la tabla
     apilada de la Vista general puede ir con rótulo y dato en una línea.
2. **Autocompletado** AC3 y AC4 (§3).
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
