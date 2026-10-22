# Manual de los subagentes: migración final, bloque B (T4 a T9)

Lo lee cada subagente **antes de tocar nada**. Orquesta y arbitra la sesión `tesis-b9` («el orquestador»). El
orquestador es también el **árbitro**: nada se da por terminado hasta que él dicta `APROBADO`.

Documentos que debes leer (solo lectura; los dos primeros están en otro árbol, no los edites):
1. `C:\Users\euger\OneDrive\Escritorio\TESIS\.worktrees\s2madm\docs\planes\PLAN_MIGRACION_FINAL_STREAMLIT.md` (tu tarea
   está en §3 con su número T).
2. `C:\Users\euger\OneDrive\Escritorio\TESIS\.worktrees\s2madm\docs\planes\MANUAL_ARBITRO.md` (con qué te va a juzgar;
   escribe pensando en esos criterios A1 a F1).
3. `docs/planes/MANUAL_SUBAGENTES_MIGRACION.md` (reglas de entorno, git y método de backend y frontend, informe final).
   **Rige todo lo que este manual no cambie.**
4. `NORMAS.md`, `frontend-desktop/DESIGN.md` y `PRODUCT.md`.

## 1. Cambios respecto del manual de la migración

1. **Tu árbol es este:** `C:\Users\euger\OneDrive\Escritorio\TESIS\.worktrees\s2m4`, rama `inc/ruta-s2-mig-final-b`.
   No toques `.worktrees\s2madm` ni `.worktrees\s2m` (los usa otra sesión). Nada de `git worktree add`, `.venv` ni
   `node_modules`.
2. **Archivos compartidos.** Solo los edita el implementador cuya tarea lo declara. Esta es la regla de reparto en
   este bloque, para que dos agentes no escriban el mismo archivo a la vez:

   | Archivo | Quién lo edita |
   |---|---|
   | `api/main.py`, `tests/unit/test_api_acceso_por_ruta.py`, `tests/unit/test_arquitectura.py` | nadie directamente: entrega el **texto exacto** (líneas a añadir) en tu informe; lo aplica el orquestador |
   | `CHANGELOG.md`, `docs/api.json`, `docs/ERS.md` | nadie: texto exacto en el informe; `api.json` lo regenera el orquestador |
   | `frontend-desktop/src/paginas/administracion/index.tsx` y `logica.ts` | solo el agente de **T5+T6** |
   | `frontend-desktop/src/shell/rutas.ts` y su test | solo el agente de **T7** (añade `cargar` de `revisar`) |
   | `src/comun/`, `src/shell/` | solo el agente de **T8** y solo lo que su tarea nombra |
3. **Confirma antes de empezar** que tu tarea no está ya hecha: lee el estado actual del código (la rama ya trae los
   arreglos V-20 de tildes). Si lo que pide la tarea ya existe, dilo en el informe y no lo rehagas.
4. **Decisión que cambie un requisito** (ERS, tutor, retiro de Streamlit): no la tomes. Anótala como «decisión para
   Eugenio» y sigue con lo más conservador y reversible.
5. Si una prueba AppTest de Streamlit agota 3 s, anótalo y no lo arregles (lo hace T9).

## 2. Cómo se trabaja una tarea (el orquestador te juzga con esto)

1. **Rojo primero.** Escribe la prueba, córrela y copia en tu informe la línea que muestra que **falla**. Después el
   código. Oráculos a mano (de la página clásica, la ERS o `core`), nunca copiados de la salida del código.
2. **Un commit por tarea terminada**, solo de tus rutas (`git add <rutas>` y `git commit <rutas> -m ...`), asunto
   convencional en español **sin tildes**, cierre `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. El
   commit de la prueba no puede ir después del de su implementación: si los separas, la prueba va primero.
3. **Paridad:** lo que la página clásica valida y dice, la nueva lo valida y lo dice con las mismas palabras. Una
   diferencia deliberada se declara en el informe con su motivo.
4. **Seguridad:** secretos solo en el cuerpo de la petición, jamás devueltos, jamás en `localStorage`, eco nulo en los
   422 (`RutaSinEco`), CSRF/Origin, subidas con guardia y tope, `no-store` si hay datos sensibles.
5. **Interfaz:** montos como texto desde la API (nunca `Number`/`parseFloat` sobre dinero), formato es-VE con
   `src/indicadores/formatoEsVe.ts`, español con tildes y sin jerga interna, Carbon g10, 1366×768 sin desplazamiento
   horizontal.
6. **Corre y pega** la salida real de: tus pruebas con `-W error` (`uv run --active pytest <archivos> -q -W error -p
   no:cacheprovider`), `uv run --active ruff check <tus archivos>`, y en `frontend-desktop`: `npx vitest run <ruta>`,
   `npm run lint`, `npm run build`. Si algo falla, lo dices con la salida; no afirmas verde sin haberlo corrido.
7. `git diff -- core/` vacío.

## 3. Ciclo con el árbitro

`implementar → informe → árbitro → (DEVUELTO → corregir en el mismo commit lógico o uno nuevo → árbitro)* → APROBADO`.
El árbitro de cada entrega es un **subagente nuevo** (distinto del implementador y del orquestador) que juzga con
`MANUAL_ARBITRO.md` y dicta el veredicto; el orquestador lo contrasta con una comprobación propia antes de dar la
tarea por aprobada. Cada ronda y su veredicto se registran. Los routers nuevos van en **una línea aparte** en el
texto que entregas para `api/main.py`; si tu tarea necesita un RF nuevo, **pídelo** en el informe y no lo escribas en
`docs/ERS.md`. Máximo **3 rondas**. El árbitro devuelve una lista numerada con archivo y línea; **solo** corriges eso (más lo que
ese cambio obligue), no rehaces el resto. Cuando respondas a una devolución, indica por cada punto el SHA que lo
corrige y la prueba que lo cubre.

## 4. Reparto de tareas de este bloque

| Agente | Tareas | Modelo | Carpetas propias |
|---|---|---|---|
| A | **T4** variaciones atípicas | Opus | `aplicacion/atipicos.py`, `ui/atipicos.py`, `api/rutas/precios_empresa.py`, `src/paginas/precios_empresa/`, sus pruebas |
| B | **T5** y luego **T6** (administración) | Opus | `api/rutas/admin_empresas_registradas.py`, `api/rutas/admin_asistente.py`, `src/paginas/administracion/`, sus pruebas |
| C | **T7** revisar un paquete | Opus | `aplicacion/revision.py`, `ui/revision.py`, `api/rutas/revision.py`, `src/paginas/revisar/`, `rutas.ts`, sus pruebas |
| D | **T8** pulido de Reajuste y Control | Sonnet | `src/paginas/reajuste/`, `src/paginas/control/`, `src/shell/` (solo la ranura), `src/comun/` (solo si es imprescindible) |
| E | **T9** calidad de pruebas | Sonnet | no arranca todavía: solo cuando `tesis-8d` avise que su T1 (arenera) está integrada y su rama se fusione en esta |

## 5. Informe final (lo pide el manual de la migración, con una línea más)

Los cinco puntos del §5 de `MANUAL_SUBAGENTES_MIGRACION.md` y, al final: «**Ya estaba hecho / no pude:**» con lo que
la tarea pedía y no hiciste, y el motivo.
