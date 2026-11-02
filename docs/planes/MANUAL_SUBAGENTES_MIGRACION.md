# Manual de los subagentes de la migración (ola final)

Lo lee cada subagente antes de tocar nada. Lo orquesta la sesión principal («el orquestador»), que es la única que
toca los archivos compartidos, integra y corre las verificaciones finales.

## 1. Reglas de entorno (no negociables)

1. **Un solo árbol de trabajo:** `C:\Users\euger\OneDrive\Escritorio\TESIS\.worktrees\s2madm` (rama
   `inc/ruta-s2-mig-adm-empresa`). Varios subagentes trabajan a la vez en él, cada uno en **sus propias carpetas**.
   **Prohibido** `git worktree add`, clonar, copiar el repo, crear `.venv` o `node_modules` (Eugenio prohibió consumir
   más disco: la carpeta TESIS pesa ~20 GB).
2. **Python:** siempre `uv run --active ...` (usa la `.venv` común; sin `--active`, `uv` crea una de 276 MB).
   **Front:** `cd frontend-desktop` y `npx vitest run <ruta>`, `npm run lint`, `npm run build` (`node_modules` ya está
   enlazado por junction; no ejecutes `npm install` ni cambies `package.json` / `package-lock.json`).
3. **Git:** nunca `git stash`, `git add -A`, `git add .`, `git commit -a`, `git reset`, `git checkout -- <archivo ajeno>`
   ni `git clean`. Añade **solo tus rutas** (`git add <rutas>`) y confirma con `git commit <rutas> -m "..."`. Si falla
   por `index.lock`, espera unos segundos y reintenta. **Sin push, sin PR.** Un commit por tarea terminada
   (convencional: `feat(api): ...`, `feat(front): ...`, `test(...)`), terminado en:
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
4. **Datos:** todo ficticio («Contratista Demo, C.A.», `J-00000000-0`, `MIN-001`…). Nunca libros, nombres de empresa ni
   cifras reales en nada versionado.
5. **Navegador** (solo si el encargo lo pide): perfil propio en el scratchpad, servidor solo en `127.0.0.1`, cierre
   solo por tu PID; **prohibido** cerrar Chrome/Edge por nombre (Eugenio usa el equipo).
6. **Suite completa:** no la corras. Corre solo las pruebas de lo que tocas, con `-W error`. Las pruebas AppTest de
   Streamlit (`test_ui_*`) agotan su espera de 3 s en este equipo y fallan también sin cambios: anótalo, no lo
   «arregles».

## 2. Archivos: tuyos y compartidos

- **Tuyos** (los de tu encargo): se indican en tu brief. Dentro de ellos haces lo que haga falta.
- **Compartidos (NO los edites):** `api/main.py`, `frontend-desktop/src/shell/rutas.ts` y su test,
  `tests/unit/test_api_acceso_por_ruta.py`, `tests/unit/test_arquitectura.py`, `CHANGELOG.md`, `docs/api.json`,
  `docs/ERS.md`, `package.json`. En tu informe final entrega el **texto exacto** de lo que hay que añadir en cada uno
  (líneas, filas de la tabla, `include_router`, línea de `cargar`, línea de CHANGELOG). El orquestador lo aplica.
- Nunca modifiques `core/` (`git diff -- core/` debe quedar vacío).

## 3. Método (backend)

1. Lee la página Streamlit y sus módulos de `ui/`. Reglas **RM-1**: la lógica sin Streamlit pasa a
   `aplicacion/<modulo>.py` y `ui/<modulo>.py` queda como reexportación explícita
   (`from aplicacion.x import nombre as nombre`). `aplicacion/` no importa `streamlit`, `ui`, `api`, `scripts` ni `tests`.
   La API no importa `ui`, `scripts` ni `tests`.
2. Ruta nueva `api/rutas/<recurso>.py`; esquemas junto a la ruta; montos y decimales **como texto** (nunca float);
   mensajes de error **idénticos** a los de la página clásica (paridad). Acceso con
   `exigir_clave_o_sesion(<Accion>)` de `api/sesion_web.py` (la `Accion` es la de tu brief). Si la ruta recibe
   archivos, reutiliza `api/archivos.py` y `adapters/hoja_empresa/guardia.py` (como `api/rutas/listas.py`). El 422
   no debe repetir lo enviado (`api/sin_eco.py`: `RutaSinEco`, `sin_eco`). Operaciones sensibles →
   `exigir_equipo_propio` (`api/sesion_web.py`).
3. **TDD con rojo visto:** escribe la prueba (`tests/unit/test_api_<recurso>.py`), córrela y **comprueba que falla**,
   luego implementa. Oráculos escritos a mano desde la página clásica, la ERS o `core`; ninguno sale del código bajo
   prueba. Patrones: `tests/unit/test_api_entregas.py`, `tests/unit/test_api_admin.py` y los fixtures de
   `tests/fixtures/sesion_web.py`.
4. Cubre fronteras, errores esperados, permisos por rol (ana arma, rita revisa, admin administra; ver
   `tests/fixtures/sesion_web.py`), CSRF y que ningún secreto o dato sensible vuelva en un error.
5. `uv run --active ruff check <tus archivos>` y `ruff format <tus archivos>` limpios.

## 4. Método (frontend)

1. Lee `frontend-desktop/PRODUCT.md`, `DESIGN.md` y `README.md`. Mira cómo están hechas
   `src/paginas/similares/`, `src/paginas/historico/` y `src/paginas/administracion/` (patrón, `useCarga`,
   `pedir`, `TablaDensa`, `AvisoError`, `DescargaArchivo`, `SubidaArchivo`, `EsqueletoPagina`, `useAplicacion()`).
2. Carpeta `src/paginas/<pagina>/` con `index.tsx` (`export default`, sin props), lógica pura en `logica.ts` con su
   prueba, componentes y su `*.test.tsx`. **Carbon g10, esquinas rectas, densidad `sm`, sin animación decorativa,
   montos tal como llegan de la API** (la interfaz no calcula ni redondea), 1366×768 sin desplazamiento horizontal.
3. Pruebas con Vitest + Testing Library (`fetch` simulado, como `Simulador.test.tsx`). Comprueba también que una
   contraseña o secreto escrito no queda en pantalla ni en `localStorage`.
4. Antes de entregar: `npx vitest run src/paginas/<pagina>`, `npm run lint`, `npm run build`.

## 5. Informe final (obligatorio, breve, en español)

1. Qué hiciste y qué **no** (con motivo).
2. Archivos creados y modificados (rutas) y el SHA de cada commit.
3. Pruebas corridas y su resultado real (si algo falla, dilo con la salida).
4. **Texto exacto para los archivos compartidos** (sección 2).
5. Dudas o decisiones que necesiten a Eugenio.
No afirmes que algo pasa sin haberlo corrido.
