# Rediseño del front, F4: la obra (Resumen, Presupuesto, Archivos y planos, Versiones). Plan de implementación

> **Para agentes:** SUB-SKILL REQUERIDA: superpowers:subagent-driven-development (recomendada) o
> superpowers:executing-plans, tarea por tarea. Los pasos usan casillas (`- [ ]`). Cada tarea termina con su árbitro
> (`docs/planes/MANUAL_ARBITRO.md`) antes de abrir la siguiente. **Agentes de uno en uno**; los menores se agrupan;
> el navegador se usa **una sola vez**, en la Tarea 14.

**Objetivo:** que las cuatro primeras secciones de la obra sigan el molde aprobado: cabecera con el estado de la obra,
pestañas, franja «Te falta / Siguiente paso» con un solo botón principal y tabla con las cifras en es-VE. Al hacerlo se
aplican las 25 bajas del inventario de F4, todas reversibles y anotadas.

**Arquitectura:** el marco gana un contexto de la obra abierta (`marco/obraAbierta.ts`). Lo provee `EspacioDeObra` y
lleva la carpeta, el número y la ficha de la obra, que es su fila de `GET /v1/obras/resumen`. La Hoja deja de ser dueña
de su borrador: `ProveedorDeLaHoja` lo abre una vez y lo comparten Presupuesto, Archivos y planos y Versiones, de modo
que pasar entre esas tres secciones no lo cierra. El Resumen se queda con la pantalla `obras`, ya reescrita (la mesa de
todas las obras se da de baja). Archivos y planos y Versiones pasan a ser pantallas propias (`paginas/archivos/`,
`paginas/versiones/`) y absorben el plano, Elaborar, la Trazabilidad y el selector de versión. El servidor solo añade
el registro de importaciones (tabla aditiva y una ruta de lectura) y pasa las **lecturas** de la Hoja de `editar_hoja`
a `leer_proyecto`, que ya existe, para que quien revisa vea las tres secciones en solo lectura (Tarea 2b, decisión de
Eugenio del 2026-10-31). `core/` no se toca.

**Stack:** React 19, TypeScript, Carbon 11 (g10), react-router 7 (HashRouter) y Vitest; FastAPI, SQLAlchemy, Alembic y
pytest. **Sin dependencias nuevas.**

**Especificación:** [docs/especificaciones/2026-10-26-rediseno-marco-obras-design.md](../especificaciones/2026-10-26-rediseno-marco-obras-design.md)
(§2.3, §2.5, §6.2 a §6.4, §7 F4, §8 ter). Hay que leerla junto con el **inventario de F4**, que es la base de este plan
y que Eugenio aprobó el 2026-10-30 con las recomendaciones de sus diez preguntas; las bajas quedan reversibles
(`docs/bitacora/2026-10-30-preguntas-para-eugenio.md`, sección «Rediseño del front, F4», fila 8). El inventario vive
fuera del repositorio, en el scratchpad de la sesión del orquestador
(`…/534c12db-7230-488e-bed6-164f72411677/scratchpad/INVENTARIO-F4.md`). Lo que el plan toma de él está copiado abajo, en
«Bajas aprobadas» y en cada tarea. La Tarea 0 sale del cierre de F3 (`docs/bitacora/2026-10-28-cierre-f3.md`, última
sección): Eugenio aprobó «plegar Empresa con letra grande para dar más alto al árbol».

## Restricciones globales

Las de `PLAN_REDISENO_MARCO.md` y `PLAN_REDISENO_F3.md` siguen vigentes: 1056/1366/1910 px con letra 1/1,25/1,5,
accesibilidad AA, vocabulario del usuario (la prueba `sinJergaInterna` lo vigila), 250 líneas por componente salvo con
una razón escrita en su cabecera, jscpd ≤ 1 % y commit por tarea con `git diff --cached --stat`. Además:

- **Nada que parezca hecho al reflejo.** Cada componente, hook o ruta nueva lleva en su cabecera una línea de **por
  qué existe**: qué tarea lo pide y quién más lo usa. Una pieza común en `comun/` se crea cuando aparece **la segunda
  vez** (§6.4), no antes. No entran dependencias nuevas ni componentes de Carbon que el proyecto no use ya, salvo que
  la tarea lo justifique por escrito. Los diálogos siguen siendo los propios del proyecto (RNF-22; no `ComposedModal`).
- **es-VE:** coma decimal y punto de miles en toda cifra visible y en toda entrada (`indicadores/formatoEsVe.ts`,
  `indicadores/cifraEscrita.ts`). La interfaz no calcula: solo formatea el texto que da la API (B3 del árbitro).
- **Carbon g10**, esquinas rectas, densidad `sm`, un solo h1 `heading-04` por pantalla y h2 `heading-compact-02`.
- **Papeles del color** (`frontend-desktop/DESIGN.md`, F3 Tarea 4c): la franja «Te falta» es **precaución**, con fondo
  `--silice-aviso-fondo` y borde `--silice-aviso-borde`. Su botón es la **acción**, el principal en el complementario.
  Esto sustituye el «botón amarillo» de la maqueta (§8 ter), que la 4c dejó atrás. Las filas afectadas usan el mismo
  `--silice-aviso-fondo` y nunca `--silice-acento`.
- **Un solo botón principal** (`kind="primary"`) por pantalla en cada estado. Cuando hay franja, el principal es el suyo.
- **Medir antes de borrar:** antes de cada commit de baja se corren `npm run muerto` y `npx knip --reporter compact` y
  la salida se anota (líneas, archivos y exportaciones sin uso, antes y después).
- **Bajas reversibles y anotadas:** cada baja va en **su propio commit** `refactor(<ámbito>): baja N, <qué>`, que solo
  quita (más lo mínimo para que compile), así que `git revert <sha>` la deshace. Por cada baja se añade una fila a la
  tabla «Rediseño del front, F4» de `docs/bitacora/2026-10-30-preguntas-para-eugenio.md` con el número, qué se quitó, el
  commit, dónde vive hoy la función y cómo volver (`git revert <sha>`, o `git checkout <sha>^ -- <rutas>` si después
  hubo cambios encima).
- **`core/` prohibido** (`git diff 51d3ceb4..HEAD -- core/` vacío). Nada de IA nueva.
- **Colores de la empresa nunca en archivos versionados.** Pruebas y documentos usan valores ficticios, como la Tarea 4c
  de F3. Este worktree no tiene `data/tema/`; el archivo local está en `.worktrees/s2madm/data/tema/tema.json`. Antes
  de **cada** commit:
  ```bash
  TEMA="C:/Users/euger/OneDrive/Escritorio/TESIS/.worktrees/s2madm/data/tema/tema.json"
  HEX="$SCRATCH/hex-empresa.txt"   # SCRATCH = el scratchpad de la sesión
  grep -oiE '#[0-9a-f]{6}' "$TEMA" | sort -u > "$HEX"
  test -s "$HEX" && { git diff --cached | grep -iqF -f "$HEX" && echo "HEX DE LA EMPRESA: NO CONFIRMAR" || echo "limpio"; }
  ```
  Solo `limpio` deja confirmar. Si el archivo no existe o sale vacío, se para y se avisa: no se confirma a ciegas.
- **Git:** `uv run --active` siempre. Prohibido `--amend`, `reset`, `stash`, `rebase`, `push`, `git add -A`/`.` y
  cambiar de rama. Se añade cada archivo por su ruta. Asunto en Conventional Commits, en español y **sin tildes**. La
  prueba en rojo va en su propio commit (`test(...)`) **antes** de la implementación (`feat(...)`/`refactor(...)`). Pie
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` u `Opus 5.5`, según el modelo de la tarea.
- **Migraciones:** la Tarea 10 añade `caso_0020`. Otra línea (el plan vial) puede crear su propia `caso_0020`. Antes
  de escribirla se mira la cabeza real (`alembic heads` sobre `migraciones/caso`) y, si choca, se renumera; al integrar,
  manda la cabeza de `main`.
- **Navegador:** solo en la Tarea 14 (perfil propio en el scratchpad, servidor en `127.0.0.1`, obras ficticias). Las
  capturas con el tema de la empresa no se versionan.

## Foco de revisión

1. **Cambios sin guardar al moverse entre Presupuesto, Archivos y planos y Versiones.** El borrador sigue abierto y no
   se pregunta nada. Salir hacia Resumen, Mercado u otra obra pide la confirmación que ya existe (`shell/salida.ts`).
   Prueba en la Tarea 3.
2. **Obra sin ninguna versión (borrador en blanco).** El Resumen dice «Te falta: agregue la primera partida». Versiones
   muestra su estado vacío sin errores. Archivos y planos importa sobre el borrador en blanco. Pruebas en las Tareas 2,
   5, 6 y 11.
3. **Cuenta que solo revisa (sin `editar_hoja`) y borrador de solo lectura.** Eugenio decidió el 2026-10-31 que quien
   revisa vea Presupuesto, Archivos y planos y Versiones **en solo lectura**. Las lecturas de la Hoja pasan a
   `leer_proyecto` (Tarea 2b) y las escrituras siguen exigiendo `editar_hoja`. En esas tres secciones no aparece ningún
   control de edición ni ninguna franja con una acción que daría 403. Con un borrador `solo_lectura`, el criterio es el
   mismo: nada de guardar, agregar ni enviar. Pruebas en las Tareas 2, 2b, 5, 6, 7, 8, 11 y 13.
4. **Letra «Muy grande» a 1366×768 y a 1056 px con el panel lateral abierto.** No hay desplazamiento horizontal: la
   tabla se desplaza dentro de su caja y, por debajo del umbral de la letra, el panel pasa por encima. Prueba de
   estructura en la Tarea 7; la medida real, en la Tarea 14.
5. **Versión abierta distinta de la vigente.** La cabecera dice «Versión abierta: VIV-001 (la vigente es VIV-002)»,
   la franja no ofrece «Enviar a aprobación» y Versiones marca cuál está abierta. Pruebas en las Tareas 3, 5 y 6.

## Bajas aprobadas (inventario §4) y dónde se aplica cada una

| # | Qué se quita | Tarea | Cómo queda cubierta la función |
|---|---|---|---|
| 1 | Botón «Nueva obra» arriba del Resumen | 2 | «Nueva obra» de la barra lateral |
| 2 | Tabla «Obras» de toda la carpeta | 2 | Árbol de obras; las cifras de la obra abierta, en el Resumen |
| 3 | Cifras sumadas de toda la carpeta, notas de conversión y «fuera de la suma» | 2 | **Pendiente de F5:** vuelven en Empresa (Eugenio, 2026-10-31; pregunta abierta 1) |
| 4 | Columna «Pendientes» de la mesa | 2 | Bandeja de F3; el Resumen muestra los de la obra |
| 5 | «Lo que puede hacer aquí» | 2 | Ctrl+K |
| 6 | «Cree su primera obra» y «Probar con datos de demostración» | 2 | Barra lateral; Empresa › Carpetas de trabajo; «Empieza aquí» (F6) |
| 7 | Título «Hoja de la obra» | 5 | Título «Presupuesto» |
| 8 | Aviso «Use el selector de obra de la cabecera» | 5 | Dentro de la obra siempre hay obra |
| 9 | Selector «Versión» de la Hoja | 6 | Versiones › «Abrir»; la cabecera dice la versión abierta |
| 10 | «Factores de la versión» dentro de APU | 5 | Pestaña «Ajustes de costo» |
| 11 | Botón «Crear plan secuencial» | 5 | «Plan desde los rendimientos»; la ruta del servidor se queda |
| 12 | «Total del presupuesto» repetido en Espacio y Parámetros | 5 | Total bajo la tabla de Partidas |
| 13 | Campo «Código del presupuesto» de Elaborar | 12 | El código de la obra |
| 14 | Campos «Moneda» y «Fecha» propios de Elaborar | 12 | La moneda y la lista de la carpeta (`GET /v1/carpeta`) |
| 15 | «Exportar a Excel» de Elaborar | 12 | «Descargar Excel» del Presupuesto |
| 16 | «Plan de trabajo» de Elaborar | 12 | Pestaña «Plan y equilibrio» |
| 17 | «Informe de auditoría» de Elaborar | 12 | Pestaña «Revisión» |
| 18 | Bloque «Presupuesto elaborado» | 12 | El resultado va directo a Partidas |
| 19 | Pantalla «Elaborar» | 12 | «Cargar cómputo» en Archivos y planos |
| 20 | Pantalla «Partidas similares» | 9 | «Parecidas a esta descripción» en «Agregar partida» |
| 21 | Botón «Volver a la Hoja» de Componer | 9 | Componer se abre en panel, sin salir de la obra |
| 22 | «Libro de la empresa» como parte de la obra | 11 | No cambia código: Archivos y planos no lo incluye y sigue en Empresa › Auditar |
| 23 | Pestaña «Equilibrio» separada | 5 | Pestaña «Plan y equilibrio» |
| 24 | Pestaña «Trazabilidad» de la Hoja | 6 | Sección Versiones |
| 25 | Texto largo de ayuda encima de cada pestaña | 5 | Catálogo `textos.ts`, tras un «¿Qué es esto?» plegado (F6 lo convierte en panel) |

Además, el inventario mueve cuatro cosas que no cuentan como baja: el Histórico de cambios de precio y las
cotizaciones van a Mercado (Tarea 13), el rastro de aprobaciones a Aprobaciones (Tarea 6) y el plano a Archivos y
planos (Tarea 11). Su commit de retiro también se anota en la tabla de la bitácora.

## Índice de tareas

| # | Tarea | Modelo | Tamaño | Bajas |
|---|---|---|---|---|
| 0 | Plegar «Empresa» con letra grande | Sonnet | S | — |
| 1 | Cabecera de la obra con su estado | Sonnet | S | — |
| 2 | Resumen de la obra y la franja del paso | Sonnet | M | 1-6 |
| 2b | La Hoja en solo lectura para quien revisa | Opus | L | — |
| 3 | La Hoja sube a la obra (`ProveedorDeLaHoja`) | Opus | L | — |
| 4 | Presupuesto: de nueve pestañas a seis | Sonnet | M | 7, 8, 10, 11, 12, 23, 25 |
| 5 | Presupuesto: franja, botón principal único y filas afectadas | Opus | M | — |
| 5b | Presupuesto: el IVA en pantalla | Sonnet | S | — |
| 6 | Versiones | Opus | L | 9, 24 |
| 7 | El APU de una partida en panel lateral | Opus | M | — |
| 8 | Un solo diálogo para las líneas del APU | Sonnet | M | — |
| 9 | «Agregar partida», puerta única (parecidas y componer en panel) | Opus | L | 20, 21 |
| 10 | Registro de importaciones de la obra (servidor) | Sonnet | M | — |
| 11 | Archivos y planos: el plano y el registro | Opus | L | 22 (sin código) |
| 12 | «Cargar cómputo» absorbe Elaborar | Opus | L | 13-19 |
| 13 | Mercado: histórico de precios y cotizaciones | Sonnet | M | — |
| 14 | Cierre de F4 | Opus (orquestador) y Sonnet (menores) | M | — |

Orden: 0 → 1 → 2 → 2b → 3 → 4 → 5 → 5b → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14. La 2b tiene que estar antes que la 3,
que hereda su `usePuedeEditarLaHoja`, y antes que toda tarea que añada controles de edición. La 3, antes que la 4 y que
la 11; la 5, antes que la 6, porque Versiones usa `useAprobacionDeVersion`; y la 10, antes que la 11.

**Regla para las tareas 4 a 13:** todo control nuevo que escriba (botón, celda editable, campo, diálogo) se pinta solo
si `puedeEditar` es verdadero (Tarea 2b), y cada una de esas tareas lleva su prueba «cuenta que revisa» (Foco 3).

---

### Tarea 0: Plegar «Empresa» con letra grande

**Modelo:** Sonnet. **Tamaño:** S. **Bajas:** ninguna.

En la pasada de navegador del cierre de F3, con letra «Muy grande» cabían 7 obras a 1366×768 y 4 a 1366×657, y la zona
Empresa ocupaba casi lo mismo que el árbol. Eugenio eligió plegar Empresa con letra Grande o Muy grande para darle ese
alto al árbol.

**Archivos:**
- Crear: `frontend-desktop/src/comun/useTamanoDeLetra.ts`. Por qué: la barra lateral necesita reaccionar al cambio de
  letra en vivo. `visor/useZoomHoja.ts` ya vigila ese atributo; la observación que comparten pasa a este hook y el
  visor la usa (segundo uso, §6.4).
- Modificar: `frontend-desktop/src/marco/BarraLateral.tsx`, `marco/BarraLateral.scss`, `visor/useZoomHoja.ts`.
- Pruebas: `marco/BarraLateral.test.tsx`, `comun/useTamanoDeLetra.test.ts`.

**Interfaces:**
- Produce: `useTamanoDeLetra(): TamanoDeLetra`. Arranca con `tamanoAplicado()` y se actualiza con un `MutationObserver`
  sobre `data-silice-letra` de `<html>`. `TamanoDeLetra` es el de `comun/preferenciaDeLetra.ts`.
- Regla: con letra `normal`, «Empresa» sigue siendo un `h2` sin botón, como hoy. Con `grande` o `muy-grande` es un
  desplegable de WAI-ARIA, `h2 > button` con `aria-expanded` y `aria-controls` hacia la lista. Arranca **plegado**,
  salvo que la ruta sea una entrada de Empresa (`entradaActiva !== null`): entonces arranca desplegado. Lo que la
  persona despliega o pliega se recuerda mientras la barra esté montada; no se guarda en el navegador (YAGNI).

- [ ] **Paso 1: pruebas rojas.**
  - `useTamanoDeLetra.test.ts`: `devuelve el tamaño puesto en la raíz` (con `data-silice-letra="grande"` da
    `"grande"`); `cambia cuando cambia el atributo` (se pone `muy-grande` y, en `waitFor`, devuelve `"muy-grande"`).
  - `BarraLateral.test.tsx`:
    - `con letra normal Empresa es un h2 sin botón y se ven sus entradas`: `getByRole("heading", {name: "Empresa"})`
      no contiene ningún `button` y están los cinco enlaces de `ENTRADAS_DE_EMPRESA`.
    - `con letra grande Empresa arranca plegada`: el botón «Empresa» tiene `aria-expanded="false"` y no hay ningún
      enlace «Precios y catálogo».
    - `al pulsar Empresa se despliega`: con clic, y también con Enter y con Espacio, queda `aria-expanded="true"`, se
      ven los cinco enlaces y `aria-controls` es el `id` de su lista.
    - `con una entrada de Empresa abierta arranca desplegada` (ruta `#/empresa/precios`, letra muy grande).
    - `pasar de normal a muy grande en vivo la pliega`.
    - Estructura del SCSS (patrón de `estilosMarco.test.ts`): el botón hereda la letra del título, tiene foco visible
      (`outline` con `--cds-focus`) y dentro de `con-letra-grande` mide al menos 1,5 rem de alto.
- [ ] **Paso 2:** `cd frontend-desktop && npx vitest run src/marco/BarraLateral.test.tsx src/comun/useTamanoDeLetra.test.ts`
  → FALLA.
- [ ] **Paso 3:** implementar. El chevron es el mismo de las obras (`ChevronDown`/`ChevronRight`, `aria-hidden`).
  `useZoomHoja` deja su `MutationObserver` y pasa a `const tamano = useTamanoDeLetra(); const factor = useMemo(() =>
  factorDeLetra(), [tamano]);`. Sus pruebas siguen verdes sin cambios.
- [ ] **Paso 4:** → PASA; `npx vitest run src/marco src/visor`; `npm run lint`; `npm run duplicado`.
- [ ] **Paso 5: commits.** `test(marco): empresa plegada con letra grande (rojo)` y luego `feat(marco): plegar empresa
  con letra grande`.

### Tarea 1: Cabecera de la obra con su estado

**Modelo:** Sonnet. **Tamaño:** S. **Bajas:** ninguna.

**Archivos:**
- Crear: `frontend-desktop/src/marco/obraAbierta.ts`. Por qué: Resumen, Presupuesto, Versiones y Archivos necesitan la
  carpeta y la obra de la ruta, y la ficha, sin volver a pedirlas. `marco/useFichaDeLaObra.ts`. `marco/EtapaDeObra.tsx`.
  Por qué: la palabra de la etapa con su ícono, en la cabecera y en las cifras del Resumen; reemplaza `Etapa` de
  `paginas/obras/TablaObras.tsx`. `marco/CabeceraDeObra.tsx`: lo que hoy es `ObraAbierta` dentro de
  `EspacioDeObra.tsx`.
- Modificar: `marco/EspacioDeObra.tsx`, `marco/marco.scss`, `api/tipos.ts` (allí pasan `Etapa`, `ObraFilaRespuesta` y
  `SiguienteRespuesta`, que hoy están en `paginas/obras/logica.ts`; se actualizan sus imports).
- Pruebas: `marco/CabeceraDeObra.test.tsx`, `marco/useFichaDeLaObra.test.tsx`.

**Interfaces:**
- Produce:
  ```ts
  export type FichaDeLaObra =
    | { estado: "cargando" } | { estado: "lista"; obra: ObraFilaRespuesta } | { estado: "sin_dato" };
  export function useFichaDeLaObra(obraId: number): FichaDeLaObra & { recargar: () => void }; // marco/useFichaDeLaObra.ts
  export interface ObraAbierta {
    carpeta: string | null; obraId: number; ficha: FichaDeLaObra; recargarFicha: () => void;
  }
  export const ContextoDeLaObra: React.Context<ObraAbierta | null>;                            // marco/obraAbierta.ts
  export function useObraAbierta(): ObraAbierta;            // lanza si se usa fuera de una obra
  export function EtapaDeObra(p: { etapa: Etapa; texto: string }): JSX.Element;
  ```
- `useFichaDeLaObra` lee `GET /v1/obras/resumen` (la carpeta ya está fijada en la sesión cuando la obra está «lista») y
  se queda con la fila `codigo === String(obraId)`. Un 403, un error o la falta de fila dan `sin_dato`, y un 401
  llama a `alExpirar`. La lectura se repite al cambiar de obra o al llamar a `recargar`, nunca al cambiar de sección.
- `EtapaDeObra` pone el ícono `aria-hidden` y siempre la palabra (`etapa_texto`): `en_elaboracion` → `Edit`,
  `en_aprobacion` → `Time`, `aprobada` → `CheckmarkOutline`, `en_ejecucion` → `InProgress`, `atrasada` →
  `WarningFilled`. Solo «atrasada» lleva color, el de la marca de hoy. Los cinco íconos están en
  `@carbon/icons-react`, que ya es dependencia.
- La cabecera, que no es un encabezado, lleva: el nombre; una lista con «Estado: <EtapaDeObra>» (solo con ficha
  `lista`) y «Versión: <código>»; y debajo `ListaDeLaCarpeta`. La versión es la vigente de `useObras`. La versión
  abierta en el borrador se añade en la Tarea 3.

- [ ] **Paso 1: pruebas rojas** (resumen simulado con tres obras ficticias, «Galpón Norte» con código `"3"`):
  - `muestra el estado de la obra en palabras`: el texto «Estado: En aprobación» está en la región «Obra abierta».
  - `obra atrasada lleva el ícono de advertencia junto a la palabra`: hay un `svg[aria-hidden="true"]` y el texto
    «Atrasada» dentro de la misma etiqueta.
  - `sin permiso o sin fila no dice el estado y la sección se monta igual`: con 403, y aparte con un resumen sin la
    obra 3, no aparece «Estado:» y sí el h1 de la sección.
  - `la ficha se pide una vez por obra`: pasar de `#/obra/empresa/3/resumen` a `#/obra/empresa/3/mercado` no repite
    `GET /v1/obras/resumen`; ir a la obra 4 sí lo repite.
  - `recargarFicha vuelve a pedir el resumen` (una sección de prueba lo llama).
  - `useObraAbierta fuera de una obra lanza un error con mensaje claro`.
- [ ] **Paso 2:** `npx vitest run src/marco` → FALLA.
- [ ] **Paso 3:** implementar. `EspacioDeObra` envuelve la sección en `ContextoDeLaObra.Provider`.
- [ ] **Paso 4:** → PASA; `npx vitest run src/marco src/paginas/obras`; lint; duplicado.
- [ ] **Paso 5: commits.** `test(marco): estado de la obra en la cabecera (rojo)` y luego `feat(marco): cabecera de
  la obra con su estado`.

### Tarea 2: Resumen de la obra y la franja del paso

**Modelo:** Sonnet. **Tamaño:** M. **Bajas:** 1, 2, 3, 4, 5 y 6.

**Archivos:**
- Modificar: `paginas/obras/index.tsx`, que pasa a ser el Resumen de la obra abierta; `paginas/obras/logica.ts` (se
  quedan los tipos que se usan y se añade `pasoDeLaObra`); `paginas/obras/obras.scss`; `paginas/pendientes/logica.ts`
  (se extrae `destinoDeLaAccion`); `shell/rutas.ts` (la pantalla `obras` pasa a llamarse «Resumen de la obra», con su
  `enUnaLinea`).
- Crear: `paginas/obras/textos.ts`; `comun/FranjaDelPaso.tsx` y `comun/FranjaDelPaso.scss`. Por qué la franja va en
  `comun/`: es el molde de toda sección (§2.3). Este es su primer uso y la Tarea 5 es el segundo; se crea aquí porque la
  especificación la fija como pieza común (§6.4, «franja Te falta»).
- Baja (commit aparte): `paginas/obras/CifrasMesa.tsx`, `ColumnaPendientes.tsx`, `LoQuePuedeHacer.tsx` y
  `TablaObras.tsx`; lo que solo usa la mesa en `logica.ts` (`bloquesPedidos`, `columnaDeLaMesa` y sus tipos;
  `pantallaVisible` se queda porque la usa la franja) y en `obras.scss`; las pruebas `Mesa.test.tsx`, `PorAprobar.test.tsx` y `Obras.test.tsx`; y la ruta de
  prueba `#/mesa` (`conLaMesa`). `paginas/obras/datosDePrueba` se queda, porque lo usa `shell/carpetas/Carpetas.test.tsx`.
- Pruebas: `paginas/obras/Resumen.test.tsx`, `paginas/obras/logica.test.ts`, `comun/FranjaDelPaso.test.tsx`,
  `paginas/pendientes/logica.test.ts`.

**Interfaces:**
- Consume: `useObraAbierta()` (Tarea 1), `usePendientes()` y `claveDeObra` (F3), `useNavegarSeguro`.
- Produce:
  ```ts
  export interface Paso { tipo: "falta" | "siguiente"; texto: string; accion: { texto: string; pagina: string } | null }
  export function pasoDeLaObra(obra: ObraFilaRespuesta): Paso | null;        // paginas/obras/logica.ts
  export function destinoDeLaAccion(carpeta: string | null, obraId: number, pagina: string): string; // pendientes/logica.ts
  export function FranjaDelPaso(p: {
    tipo: "falta" | "siguiente"; texto: string;
    accion?: { texto: string; alPulsar: () => void; deshabilitada?: boolean };
  }): JSX.Element;                                                            // comun/FranjaDelPaso.tsx
  ```
- `pasoDeLaObra`: con `que_pasa` da `falta`, con su texto y la acción `siguiente`. Sin `que_pasa` pero con `siguiente`
  da `siguiente`, con el texto de la acción. Sin ninguno de los dos, `null` (no se pinta franja). La pantalla solo
  pone el botón si la cuenta puede usar la pantalla de destino (`pantallaVisible(accion.pagina, acciones,
  modoEntrega)`); si no, la franja queda sin botón.
  `destinoDelPendiente(p)` pasa a delegar en `destinoDeLaAccion(p.carpeta, p.obra_id, p.accion.pagina)`, sin cambiar
  su comportamiento.
- `FranjaDelPaso` pinta una `section` con `aria-label="Siguiente paso"`. Escribe «Te falta:» o «Siguiente paso:» en
  seminegrita, luego el texto y, si hay acción, **un** `Button kind="primary" size="md"`. Con `falta` lleva el ícono
  `WarningAltFilled` `aria-hidden`; la palabra ya basta y el color no va solo. Fondo `--silice-aviso-fondo` y raya
  izquierda de 4 px `--silice-aviso-borde`, como la etiqueta de advertencia de DESIGN.md; colores forzados con borde
  propio.
- La pantalla tiene un h1 «Resumen», la franja y las cifras de **esta** obra en un `dl`: Total (con `formatoEsVe` y la
  moneda; el exacto en el texto accesible), Avance real contra plan (con el formato de hoy, `TablaObras.tsx:109-115`,
  que se mueve a `logica.ts`), Versión vigente y Etapa (`EtapaDeObra`). Al lado va el panel «Pendientes de esta obra»:
  `usePendientes()` filtrado por `claveDeObra(carpeta, obraId)`, cada uno con su botón `kind="tertiary"` que navega con
  `destinoDelPendiente`. Sin ninguno: «Nada pendiente por ahora».

- [ ] **Paso 1: pruebas rojas.**
  - `logica.test.ts`, una prueba por regla de `pasoDeLaObra`: con `que_pasa` y `siguiente` da `falta`; solo
    `siguiente` da `siguiente` con `texto` «Abrir la Hoja»; sin ninguno da `null`.
  - `pendientes/logica.test.ts`: `destinoDeLaAccion("Carpeta Sur.db", 3, "hoja")` →
    `"/obra/Carpeta%20Sur.db/3/presupuesto"`; con `"desconocida"` → `…/3/resumen`; con `"catalogo"` →
    `"/empresa/precios"`. Las pruebas de `destinoDelPendiente` siguen sin tocarse.
  - `FranjaDelPaso.test.tsx`: la región «Siguiente paso» dice «Te falta: Faltan 2 precios»; con acción hay **un**
    botón `.cds--btn--primary` y al pulsarlo se llama `alPulsar`; sin acción no hay botón; `deshabilitada` lo
    deshabilita; con `tipo="siguiente"` no hay ícono.
  - `Resumen.test.tsx`, con la obra 3 de «Carpeta Norte.db» abierta y un resumen ficticio de tres obras:
    - un solo h1, «Resumen»;
    - las cifras son las de la fila `codigo "3"`: Total «1.234.567,89 Bs» (a partir de `"1234567.89"`) y la etapa en
      palabras; los nombres de las otras dos obras no aparecen;
    - `que_pasa` «Faltan 2 precios» y `siguiente` `{texto: "Abrir la Hoja", pagina: "hoja"}`: la franja dice «Te
      falta: Faltan 2 precios» y su único botón, «Abrir la Hoja», navega a `/obra/Carpeta%20Norte.db/3/presupuesto`;
    - obra sin versiones (`version: null`, `que_pasa` «Sin partidas») da la franja «Te falta: …» (Foco 2);
    - de los pendientes de la obra 3 en Norte y de la obra 3 en Sur, solo se ven los de Norte;
    - sin pendientes: «Nada pendiente por ahora»;
    - sin dato (403 o sin fila): aviso «No hay datos de esta obra todavía.» y ninguna franja;
    - cuenta que revisa (sin `editar_hoja` ni `control_de_obra`), con `siguiente` «Registrar el avance» hacia
      `control`: ve las cifras y el texto de la franja, pero ningún botón. Con `siguiente` hacia `hoja`, el botón sí
      sale, porque desde la Tarea 2b ve Presupuesto en solo lectura (Foco 3);
    - en toda la pantalla hay como mucho un `.cds--btn--primary`;
    - no hay botón «Nueva obra», ni tabla «Obras», ni «Lo que puede hacer aquí», ni «Probar con datos de
      demostración» (bajas 1, 2, 5 y 6).
- [ ] **Paso 2:** `npx vitest run src/paginas/obras src/paginas/pendientes src/comun/FranjaDelPaso.test.tsx` → FALLA.
- [ ] **Paso 3:** implementar el Resumen y la franja, con los textos en `textos.ts`.
- [ ] **Paso 4:** → PASA; lint; duplicado. **Commits:** `test(resumen): resumen de la obra abierta (rojo)` y luego
  `feat(resumen): resumen de la obra con su franja`.
- [ ] **Paso 5: baja.** Medir (`npm run muerto`, `npx knip --reporter compact`). Quitar la mesa (la lista de
  «Archivos» de arriba). Comprobar que `npm run muerto` sale en 0 y que pasan `npx vitest run src/paginas src/marco
  src/shell`. **Commit** `refactor(resumen): baja 1 a 6, la mesa de todas las obras`, solo con las bajas. Anotar las
  seis filas en la bitácora. La 3 queda como **pendiente de F5**: Eugenio decidió el 2026-10-31 que las cifras vuelvan
  en Empresa (pregunta abierta 1).

### Tarea 2b: La Hoja en solo lectura para quien revisa

**Modelo:** Opus. **Tamaño:** L. **Bajas:** ninguna.

**Por qué:** Eugenio decidió el 2026-10-31 que el rol «revisa» vea Presupuesto, Archivos y planos y Versiones en solo
lectura. Hoy todas las rutas de `api/rutas/hoja.py` exigen `editar_hoja`, incluso las de lectura: `LEER =
Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))` en la línea 254, y `CuentaDeLaHoja` para los borradores. La acción
de leer ya existe: `Accion.LEER_PROYECTO`, que tienen arma y revisa (`seguridad/permisos.py`). **No se crea ninguna
acción nueva** ni cambia la matriz de permisos.

Abrir un borrador no escribe nada en la base: vive en memoria, es de la ficha de cada cuenta (`_vivo` comprueba
`huella_ficha`) y se va solo. Por eso quien revisa puede abrir el suyo para ver las vistas calculadas, y todo lo que
lo cambia sigue exigiendo `editar_hoja`.

**Archivos:**
- Modificar: `api/rutas/hoja.py`, con la dependencia de lectura `VER = Depends(exigir_clave_o_sesion(Accion.LEER_PROYECTO))`
  y `CuentaQueVe = Annotated[SesionActiva, Depends(cuenta_con(Accion.LEER_PROYECTO, MENSAJE_SOLO_CUENTA))]`;
  `api/rutas/aprobaciones.py` (`GET /v1/aprobaciones?proyecto=` pasa a `LEER_PROYECTO`, porque Versiones lo lee);
  `tests/unit/test_api_acceso_por_ruta.py` (la `TABLA`); `docs/api.json` si cambia (con el truco de `git archive
  HEAD`); y `CHANGELOG.md`.
- Front: `shell/rutas.ts` (la pantalla `hoja` pasa a `accion: "leer_proyecto"`); `paginas/hoja/puedeEditar.ts`
  (nuevo); y los componentes de la Hoja que escriben, que se listan en las pruebas.
- Pruebas: `tests/unit/test_api_hoja_lectura_revisa.py` (nueva), `test_api_acceso_por_ruta.py` y
  `paginas/hoja/SoloLectura.test.tsx` (nueva).

**Interfaces:**
- Rutas que pasan a `LEER_PROYECTO`, y nada más:
  - con clave o sesión (`VER`): `GET /v1/hoja/versiones`, `/antes-y-despues`, `/precios`, `/precios/atipicos`,
    `/trazabilidad`, `/cadena` y `GET /v1/aprobaciones`;
  - solo con sesión (`CuentaQueVe`): `GET /v1/hoja/borradores`, `POST /v1/hoja/borradores`,
    `GET|DELETE /v1/hoja/borradores/{id}`, `GET /borradores/{id}/vistas/{espacio,presupuesto,apu,plan,equilibrio,parametros,auditoria}`,
    `GET /borradores/{id}/insumos`, `/cambios` y `/excel`.

  `DELETE` de un borrador propio es cerrar la consulta, no tocar datos. Con `reemplazar: true`, `POST
  /v1/hoja/borradores` solo descarta borradores de la propia ficha, y uno de quien revisa nunca tiene cambios.
- **Toda otra ruta de `/v1/hoja` sigue en `EDITAR_HOJA`** (`PUT`, los demás `POST`, guardar, plano, llevar, restaurar,
  cotizar y convertir). La ruta de la Tarea 10 nace en `LEER_PROYECTO`.
- Front:
  ```ts
  // paginas/hoja/puedeEditar.ts. Por qué: una sola regla para todos los controles que escriben en la Hoja y en las
  // secciones que la comparten; la Tarea 3 la expone como `HojaDeLaObra.puedeEditar`.
  export function puedeEditarLaHoja(acciones: readonly string[], base: Pick<BaseAbierta, "solo_lectura"> | null): boolean;
  export function usePuedeEditarLaHoja(base: Pick<BaseAbierta, "solo_lectura"> | null): boolean;   // lee la sesión
  ```
  El resultado es `acciones.includes("editar_hoja") && base?.solo_lectura !== true`. Sin `puedeEditar`, los controles
  que escriben **no se pintan** (no se dejan deshabilitados): una celda editable pasa a texto, igual que una celda de
  solo lectura de hoy. Encima de las pestañas, una nota (`role="note"`) dice «Está viendo este presupuesto en solo
  lectura.».

- [ ] **Paso 1: pruebas rojas del servidor.**
  - `test_api_acceso_por_ruta.py`: en la `TABLA`, las rutas de la lista de arriba pasan de `EDITAR` a `LEER` (que ya
    vale `{"arma", "revisa"}` en `ROLES`). Las demás de `/v1/hoja` siguen en `EDITAR`, con un comentario
    `# F4 2b: solo lectura para revisa`. `test_cada_ruta_exige_el_rol_de_su_accion` falla en rojo para esas rutas.
  - `test_api_hoja_lectura_revisa.py`, con una cuenta «revisa» y una obra ficticia con VIV-001 guardada:
    - `test_revisa_lee_las_versiones_y_la_trazabilidad`: 200 en `/versiones`, `/trazabilidad`, `/cadena` y
      `/precios`;
    - `test_revisa_abre_su_borrador_y_ve_las_vistas`: `POST /borradores` → 201 y las siete vistas → 200;
    - `test_revisa_no_escribe`: con ese mismo borrador, `PUT /cantidades`, `POST /partidas`, `POST /guardar`,
      `POST /plano`, `POST /v1/hoja/llevar` y `POST /versiones/restaurar` → 403, y el `rev` del borrador no cambia;
    - `test_el_administrador_no_ve_la_hoja`: un administrador puro → 403 en `/versiones` (no tiene `leer_proyecto`);
    - `test_revisa_no_ve_el_borrador_de_otra_ficha`: el `id` del borrador de quien arma → 404 para quien revisa;
    - `test_revisa_lee_las_aprobaciones_de_la_obra`: `GET /v1/aprobaciones?proyecto=` → 200.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_acceso_por_ruta.py tests/unit/test_api_hoja_lectura_revisa.py -q -W error -p no:cacheprovider`
  → FALLA.
- [ ] **Paso 3:** cambiar las dependencias de esas rutas (ninguna más) → PASA; `ruff check`; `git diff 51d3ceb4..HEAD --
  core/ seguridad/permisos.py` vacío. **Commits:** `test(hoja): lecturas de la hoja para quien revisa (rojo)` y luego
  `feat(hoja): las lecturas de la hoja exigen leer_proyecto`.
- [ ] **Paso 4: pruebas rojas del front** (`SoloLectura.test.tsx`, sesión con las acciones de «revisa»:
  `leer_proyecto`, `aprobar_version`, `revisar_paquete`, `ver_riesgo`):
  - `puedeEditarLaHoja`: arma con base normal → `true`; revisa → `false`; arma con `solo_lectura` → `false`;
  - el árbol ofrece «Presupuesto» a quien revisa;
  - en Presupuesto se ve la nota «Está viendo este presupuesto en solo lectura.» y la tabla con sus cifras en es-VE;
  - en ninguna pestaña hay botón «Agregar partida», «Quitar», «Volver a la calculada», «Guardar versión…»,
    «Guardar primera versión…», «Descartar cambios», «Agregar línea», «Cambiar insumo», «Usar este insumo», «Plan desde
    los rendimientos», «Crear plan secuencial», «Agregar fila», «Quitar fila», «Convertir la moneda…», «Registrar una
    cotización…», «Retirar una cotización…», «Restaurar una versión…», «Enviar a aprobación…» ni «Importar plano (DXF o
    IFC)»;
  - en ninguna pestaña hay un `textbox` ni un `spinbutton` sin `readonly` (los que existan son de búsqueda, como el de
    la partida en el APU, y van con `role="searchbox"`) y la tabla del espacio no se pinta como `role="grid"` editable;
  - sí están «Descargar Excel», «Ver en Auditoría» y la búsqueda de partida del APU (solo lee);
  - con la sesión de «arma», todos esos controles siguen ahí (las pruebas de la Hoja de hoy, verdes y sin cambios).
- [ ] **Paso 5:** `npx vitest run src/paginas/hoja src/shell src/marco` → FALLA; implementar con `usePuedeEditarLaHoja`
  en cada componente que escribe → PASA; lint; duplicado. **Commits:** `test(hoja): presupuesto en solo lectura para
  quien revisa (rojo)` y luego `feat(hoja): presupuesto en solo lectura para quien revisa`.

### Tarea 3: La Hoja sube a la obra (`ProveedorDeLaHoja`)

**Modelo:** Opus. **Tamaño:** L. **Bajas:** ninguna. Es una refactorización: lo que se ve no cambia, salvo la
versión abierta en la cabecera.

**Por qué:** Archivos y planos (el plano y el cómputo entran en el borrador) y Versiones («Abrir», «Guardar
versión…») trabajan sobre **el mismo borrador** que Presupuesto. Hoy `HojaDeProyecto` lo abre y, al desmontarse, lo
descarta si no tiene cambios (`useBorrador`). Sin subir ese estado, cambiar de sección cerraría el borrador y obligaría
a «Retomar».

**Archivos:**
- Crear: `paginas/hoja/ProveedorDeLaHoja.tsx`. El contexto y el hook se mueven allí desde `HojaDeProyecto`:
  `useOfertas`, `useVersiones`, `useBorrador`, retomar, `pedirVersion`, `useGuardadoDeLaPagina`, `alCrearVersion` y los
  diálogos de versión y de guardar.
- Modificar: `paginas/hoja/index.tsx`, que queda como el cuerpo de la sección y consume el contexto (debe bajar de
  585 líneas o declarar su razón); `marco/EspacioDeObra.tsx`; `marco/secciones.ts`; `marco/CabeceraDeObra.tsx`; la
  regla de salida del marco (`shell/salida.ts` o `marco/Marco.tsx`, donde hoy se decide si preguntar al cambiar de
  sección).
- Pruebas: `paginas/hoja/ProveedorDeLaHoja.test.tsx`, `marco/Marco.test.tsx`. Las 15 pruebas que montan `PaginaHoja`
  siguen verdes **sin cambiar ninguna aserción**.

**Interfaces:**
- Produce:
  ```ts
  export const SECCIONES_CON_HOJA: readonly SeccionId[] = ["presupuesto", "archivos", "versiones"]; // marco/secciones.ts
  export interface HojaDeLaObra {
    proyecto: string; nombreProyecto: string | null;
    versiones: { estado: "cargando" } | { estado: "listo"; datos: VersionesRespuesta } | { estado: "error"; error: unknown };
    codigo: string | null;                 // la versión abierta (null: borrador en blanco)
    estado: EstadoBorrador;                // el de useBorrador
    hayCambios: boolean;
    puedeEditar: boolean;                  // puedeEditarLaHoja(acciones, base) de la Tarea 2b
    ofrecidos: OfertaDeRetomar[]; retomar: (o: OfertaDeRetomar) => void; descartarOfrecidos: () => Promise<void>;
    pedirVersion: (codigo: string) => void; // con cambios, pregunta (DialogoDeVersion) como hoy
    refrescar: () => Promise<void>; aplicar: (r: Resumen) => void; reabrirNuevo: () => void;
    descartarCambios: () => Promise<void>;
    abrirGuardado: () => void;             // abre DialogoDeGuardar
    alCrearVersion: AlCrearVersion;
  }
  export function ProveedorDeLaHoja(p: { children: ReactNode }): JSX.Element;
  export function useHojaDeLaObra(): HojaDeLaObra;   // lanza fuera del proveedor
  ```
- `EspacioDeObra` monta `<ProveedorDeLaHoja key={clave de la obra}>` alrededor de la sección **solo** si
  `SECCIONES_CON_HOJA.includes(seccion.id)`, y siempre en la misma posición del árbol de React, para que pasar entre
  esas tres secciones no lo desmonte. En Resumen, Mercado, Aprobaciones y Control no se abre ningún borrador.
- `PaginaHoja` monta su propio proveedor solo si no hay uno encima (`useContext(ContextoDeLaHoja) === null`). Así las
  pruebas de la Hoja siguen montándola sola. La regla va comentada en el archivo.
- Parámetro de ruta `?version=<código>`: al llegar, el proveedor llama a `pedirVersion(código)` si es otra que la
  abierta y quita el parámetro (`setSearchParams` con `replace`). Lo usan Versiones («Abrir», Tarea 6) y Mercado
  (Tarea 13).
- Salida: pasar de una sección de `SECCIONES_CON_HOJA` a otra de la **misma** obra no pregunta. Cualquier otra salida
  con cambios pregunta como hoy.
- Cabecera: si `codigo` no es la vigente, la línea de versión dice «Versión abierta: VIV-001 (la vigente es VIV-002)»
  (Foco 5). Solo pasa dentro del proveedor; fuera de él, la cabecera de la Tarea 1 no cambia.

- [ ] **Paso 1: pruebas rojas** (`ProveedorDeLaHoja.test.tsx` con el servidor falso de las pruebas de la Hoja y
  `Marco.test.tsx`):
  - `abre el borrador una vez y lo conserva al pasar a Versiones y a Archivos`: un solo `POST /v1/hoja/borradores` y
    ningún `DELETE` al pasar de `…/presupuesto` a `…/versiones` y a `…/archivos`. Mientras esas dos pantallas no
    existan, la prueba usa pantallas de relleno que leen `useHojaDeLaObra().estado`.
  - `al ir al Resumen sin cambios descarta el borrador`: hay un `DELETE /v1/hoja/borradores/<id>`.
  - `al ir al Resumen con cambios conserva el borrador`: no hay `DELETE` y sí el diálogo «Cambios sin guardar».
  - `entre las secciones con hoja no pregunta, hacia Mercado sí` (Foco 1).
  - `en Resumen y Mercado no se abre ningún borrador`.
  - `?version=VIV-001 abre esa versión y quita el parámetro`: el siguiente `POST /v1/hoja/borradores` lleva
    `version: "VIV-001"` y la ruta queda sin `?version`; con cambios aparece primero el diálogo «Descartar los
    cambios».
  - `la cabecera dice la versión abierta cuando no es la vigente` (texto exacto de arriba).
- [ ] **Paso 2:** `npx vitest run src/paginas/hoja/ProveedorDeLaHoja.test.tsx src/marco/Marco.test.tsx` → FALLA.
- [ ] **Paso 3:** mover el estado al proveedor sin cambiar su lógica (las mismas funciones y los mismos efectos). El
  cuerpo de la Hoja solo consume el contexto.
- [ ] **Paso 4:** → PASA; `npx vitest run src/paginas/hoja src/marco src/shell` todo en verde, **sin** tocar las
  aserciones viejas (el informe lo confirma); lint; duplicado; muerto.
- [ ] **Paso 5: commits.** `test(hoja): el borrador vive en la obra (rojo)` y luego `refactor(hoja): proveedor de la
  hoja compartido por las secciones de la obra`.

### Tarea 4: Presupuesto, de nueve pestañas a seis

**Modelo:** Sonnet. **Tamaño:** M. **Bajas:** 7, 8, 10, 11, 12, 23 y 25.

**Archivos:**
- Modificar: `paginas/hoja/logica.ts` (`PESTANAS` pasa a definiciones con id; se va el comentario que cita
  `ui/paginas/hoja.py`, hallazgo 7 del inventario), `paginas/hoja/index.tsx`, `PestanaApu.tsx` (fuera los «Factores de
  la versión»), `PestanaPlan.tsx` (fuera «Crear plan secuencial» y, debajo, el equilibrio), `PestanaParametros.tsx`
  (fuera el total y la línea «Moneda del proyecto»; su comentario `ui/paginas/hoja.py:1680` también), `PestanaEspacio.tsx`
  (fuera el total), `PestanaPresupuesto.tsx` y `PestanaPrecios.tsx` (sus textos largos pasan al catálogo),
  `ProveedorDeLaHoja.tsx` (la pestaña vive en el proveedor), `shell/rutas.ts` (la pantalla `hoja` se titula
  «Presupuesto»).
- Crear: `paginas/hoja/textos.ts` (títulos y ayudas de las pestañas) y `comun/QueEsEsto.tsx`. Por qué: la baja 25 saca
  el texto largo de encima de cada pestaña, pero el texto se conserva tras un «¿Qué es esto?» plegado. Lo usan las
  siete pestañas, y F6 lo convertirá en el panel de ayuda. Usa `shell/useDespliegue.ts`, que ya existe (Esc cierra y
  devuelve el foco); el `Toggletip` de Carbon no se usa en el proyecto y no se ha comprobado con `npm run dist`.
- Pruebas: `paginas/hoja/logica.test.ts`, `paginas/hoja/Pestanas.test.tsx` (nueva) y `comun/QueEsEsto.test.tsx`; se
  ajustan las pruebas que buscaban pestañas por su nombre viejo, y el informe las lista.

**Interfaces:**
- Produce:
  ```ts
  export type PestanaId = "espacio" | "partidas" | "apu" | "plan" | "precios" | "revision" | "ajustes" | "trazabilidad";
  export interface PestanaDef { id: PestanaId; titulo: string }
  export const PESTANAS: readonly PestanaDef[];   // espacio, partidas, apu, plan, precios, revision, ajustes, trazabilidad
  export function pestanasVisibles(r: Pick<Resumen, "espacio_vacio">, espacioPedido: boolean): readonly PestanaDef[];
  export function pestanaInicial(r: Pick<Resumen, "espacio_vacio">): PestanaId;
  // en HojaDeLaObra (Tarea 3) se añaden:
  pestana: PestanaId; irAPestana: (id: PestanaId) => void; espacioPedido: boolean; pedirEspacio: () => void;
  export function QueEsEsto(p: { titulo: string; children: ReactNode }): JSX.Element;
  ```
- Títulos: «Espacio y metrajes», «Partidas», «Análisis de precio (APU)», «Plan y equilibrio», «Precios», «Revisión»,
  «Ajustes de costo» y «Trazabilidad». «Trazabilidad» se queda hasta la Tarea 6.
- «Espacio y metrajes» se ve si `espacio_vacio !== true` o si `espacioPedido` (pregunta abierta 3). `pestanaInicial` da
  `"espacio"` en el primer caso y `"partidas"` en el segundo.
- «Plan y equilibrio» monta `PestanaPlan` y debajo `PestanaEquilibrio`, con un h2 por bloque.
- «Ajustes de costo» es `PestanaParametros`, con «Convertir la moneda…», sin total y sin «Moneda del proyecto».
- La ayuda de la sección `versiones` en `marco/secciones.ts` pasa a «Las versiones guardadas del presupuesto y lo que
  cambió en cada una.» (pregunta 9 del inventario: comparar versiones no se construye).

- [ ] **Paso 1: pruebas rojas.**
  - `logica.test.ts`: `pestanasVisibles({espacio_vacio: true}, false)` da los ids `partidas, apu, plan, precios,
    revision, ajustes, trazabilidad`; con `false` empieza por `espacio`; con `(true, true)` también;
    `pestanaInicial({espacio_vacio: true})` → `"partidas"`.
  - `Pestanas.test.tsx`:
    - el h1 es «Presupuesto» y no aparece «Hoja de la obra» (baja 7);
    - el `tablist` «Secciones del presupuesto» tiene siete pestañas en una obra civil, con esos títulos en orden;
    - no existe el texto «Use el selector de obra de la cabecera» (baja 8);
    - en «Análisis de precio (APU)» no hay «Factores de la versión» (baja 10);
    - en «Plan y equilibrio» no hay botón «Crear plan secuencial» (baja 11) y se ven los h2 «Plan desde los
      rendimientos» y «Punto de equilibrio» (baja 23);
    - en «Ajustes de costo» y en «Espacio y metrajes» no aparece «Total del presupuesto» (baja 12) ni «Moneda del
      proyecto»;
    - encima de la tabla de «Partidas» no está el texto «los cambios se aplican cuando deja de escribir», que solo
      aparece tras pulsar «¿Qué es esto?» (baja 25);
    - «Ver en Revisión» de una fila lleva a la pestaña «Revisión» con el filtro (antes era «Ver en Auditoría»);
    - la pestaña elegida se conserva al ir a Versiones y volver (vive en el proveedor).
  - `QueEsEsto.test.tsx`: botón «¿Qué es esto?» con `aria-expanded="false"`; al pulsarlo se ve el texto; Esc lo cierra
    y el foco vuelve al botón.
- [ ] **Paso 2:** `npx vitest run src/paginas/hoja src/comun/QueEsEsto.test.tsx` → FALLA.
- [ ] **Paso 3:** implementar la estructura nueva, con los textos en el catálogo. Por ahora los bloques de las bajas
  10, 11 y 12 solo dejan de renderizarse; se borran en el paso 5.
- [ ] **Paso 4:** → PASA; lint; duplicado. **Commits:** `test(presupuesto): seis pestanas y textos en catalogo (rojo)`
  y luego `feat(presupuesto): seis pestanas, plan y equilibrio juntos, ajustes de costo`.
- [ ] **Paso 5: bajas.** Medir con knip y borrar el código que queda sin uso: el bloque de factores de `PestanaApu`, el
  botón y la llamada de «plan secuencial» del front (la ruta `POST /borradores/{id}/plan/secuencial` del servidor
  **no** se toca) y los totales repetidos. Un commit por grupo: `refactor(presupuesto): baja 10, factores dentro del
  apu`, `refactor(presupuesto): baja 11, crear plan secuencial` y `refactor(presupuesto): baja 12, totales repetidos`.
  Las bajas 7, 8, 23 y 25 ya quedaron en el commit `feat` porque no dejan código muerto. Las siete se anotan en la
  bitácora, con el commit donde ocurrió cada una.

### Tarea 5: Presupuesto, la franja, un solo botón principal y las filas afectadas

**Modelo:** Opus. **Tamaño:** M. **Bajas:** ninguna (son fusiones del inventario: estado vacío, «Hacer una versión
nueva», «Enviar a aprobación…» y la columna Estado).

**Archivos:**
- Crear: `paginas/hoja/pasoDelPresupuesto.ts` (lógica pura) y `paginas/hoja/useAprobacionDeVersion.ts`. Por qué: el
  estado de aprobación de la versión abierta lo necesitan la franja (aquí) y Versiones (Tarea 6). Sale de
  `AprobacionDeVersion.tsx`, que se queda solo con los diálogos de enviar y de retirar. Sus `NOMBRES` duplicados se
  cambian por `comun/aprobacion.ts`.
- Modificar: `paginas/hoja/index.tsx` (la franja va encima de las pestañas; `EstadoDelBorrador` se queda con el total y
  con «Descartar cambios», de tipo `ghost`), `AprobacionDeVersion.tsx`, `PestanaPresupuesto.tsx`, `EstadoDeFila.tsx` y
  `hoja.scss`.
- Pruebas: `paginas/hoja/pasoDelPresupuesto.test.ts`, `paginas/hoja/Franja.test.tsx`; se ajustan
  `AprobacionDeVersion.test.tsx` y `Guardar.test.tsx` donde buscaban el botón en su sitio viejo.

**Interfaces:**
- Consume: `useHojaDeLaObra()` (Tareas 3 y 4) y `FranjaDelPaso` (Tarea 2).
- Produce:
  ```ts
  export type AccionDelPresupuesto = "agregar_partida" | "guardar" | "ver_revision" | "version_nueva" | "enviar_a_aprobacion";
  export interface EntradaDelPaso {
    version: string | null; vigente: string | null; cambios: number; graves: number;   // graves = CRITICO + ERROR
    aprobacion: string | null;   // clave de comun/aprobacion.ts o null si no hay lectura
    puedeEditar: boolean;        // HojaDeLaObra.puedeEditar (Tarea 2b): editar_hoja y no solo_lectura
    puedeEnviar: boolean;        // puedeEditar y la lectura de aprobación no falló
  }
  export interface PasoDelPresupuesto { tipo: "falta" | "siguiente"; texto: string; accion: AccionDelPresupuesto | null }
  export function pasoDelPresupuesto(e: EntradaDelPaso): PasoDelPresupuesto | null;
  export type LecturaDeAprobacion =
    | { estado: "leyendo" } | { estado: "listo"; datos: EstadoDeAprobacion | null } | { estado: "fallo" };
  export function useAprobacionDeVersion(proyecto: string, version: string | null):
    LecturaDeAprobacion & { recargar: () => void };   // 403 o fallo -> "fallo"; version null -> listo con null
  ```
- Reglas de `pasoDelPresupuesto`, en este orden (la primera que se cumple gana). Los textos exactos van a `textos.ts`:
  1. `version === null && cambios === 0` → falta, «Agregue la primera partida», `agregar_partida`.
  2. `cambios > 0 || version === null` → siguiente, «Hay N cambios sin guardar», `guardar` (botón «Guardar versión…»
     o «Guardar primera versión…»).
  3. `graves > 0` → falta, «Hay N hallazgos graves: revíselos antes de enviar», `ver_revision`.
  4. `aprobacion === "devuelta"` → falta, «La versión V fue devuelta: corrija lo observado», `version_nueva`.
  5. `aprobacion === "en_aprobacion"` → siguiente, «La versión V espera dictamen», sin acción.
  6. `aprobacion` aprobada (`ESTADOS_APROBADOS`) → `null`.
  7. `version !== vigente` → `null`: solo la vigente se envía (Foco 5).
  8. Si no → siguiente, «Envíe la versión V a aprobación», `enviar_a_aprobacion`.
  Sin `puedeEditar`, las acciones `agregar_partida`, `guardar` y `version_nueva` pasan a `null` y el texto se queda
  (Foco 3). Sin `puedeEnviar`, también `enviar_a_aprobacion`.
- Filas afectadas: un renglón con algún hallazgo de severidad CRITICO, ERROR o ADVERTENCIA lleva la clase
  `silice-fila--afectada` (fondo `--silice-aviso-fondo`). La columna Estado conserva la severidad en palabra y su
  botón, que pasa a llamarse «Ver en Revisión».

- [ ] **Paso 1: pruebas rojas.**
  - `pasoDelPresupuesto.test.ts`: un caso por regla, con su texto y su acción exactos, además de `puedeEditar=false`
    en las reglas 1, 2 y 4 y `puedeEnviar=false` en la 8.
  - `Franja.test.tsx`:
    - borrador en blanco: la franja dice «Te falta: Agregue la primera partida» y su botón abre el diálogo «Agregar
      partida»;
    - con 2 cambios: «Siguiente paso: Hay 2 cambios sin guardar» y el botón «Guardar versión…» abre `DialogoDeGuardar`;
    - en cada estado (en blanco, con cambios, con graves, devuelta, en aprobación, aprobada) hay **como mucho un**
      `.cds--btn--primary` en la pantalla. «Agregar partida» sobre la tabla es `tertiary`;
    - devuelta: «Hacer una versión nueva» lleva a «Partidas» (lo que hacía `alHacerVersionNueva`);
    - «Enviar a aprobación…» abre el diálogo de envío con nota opcional, igual que hoy;
    - versión abierta distinta de la vigente: la franja no ofrece enviar;
    - borrador `solo_lectura`, y aparte una cuenta que revisa: la franja sale con su texto, pero sin botón de agregar,
      guardar, versión nueva ni enviar (Foco 3);
    - un renglón con un hallazgo ERROR tiene `silice-fila--afectada` y la palabra «Error» en su Estado; uno sin
      hallazgos no lleva la clase.
- [ ] **Paso 2:** → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** → PASA; `npx vitest run src/paginas/hoja`; lint; duplicado; muerto. **Commits:**
  `test(presupuesto): franja del paso y boton principal unico (rojo)` y luego `feat(presupuesto): franja del paso,
  boton principal unico y filas afectadas`.

### Tarea 5b: Presupuesto, el IVA en pantalla

**Modelo:** Sonnet. **Tamaño:** S. **Bajas:** ninguna. Decisión de Eugenio del 31/10/2026 (plan vial, Tarea 18): el
IVA del presupuesto se ve en la sección Presupuesto de F4. Se añadió el 02/11/2026, con la T18 ya unida a F4.

**Archivos:**
- Servidor: la vista `presupuesto` del borrador de la Hoja añade `impuestos` con `subtotal`, `iva`, `total` (texto
  decimal, dos cifras), `alicuota` («16») y `fuente` (la de `ALICUOTA_IVA`, «a cotejar con la Gaceta vigente»),
  calculados con `aplicacion/impuestos.con_iva` sobre el total de la vista. **No se toca `aplicacion/hoja.py`** (está
  en el congelado del experimento, acta del 31/10): el cálculo va en la capa de la API o en un módulo nuevo de
  `aplicacion/`. `docs/api.json` se regenera.
- Front: `PestanaPresupuesto.tsx` (o la pieza del total), `textos.ts`; prueba nueva `IvaDelPresupuesto.test.tsx`.

**Reglas:**
- Debajo de «Total del presupuesto» se leen «Subtotal», «IVA (16 %)» y «Total con IVA», con `Cifra` en es-VE y la
  moneda de la obra; la alícuota cita su fuente en la ayuda («¿Qué es esto?»), no en una nota suelta.
- Igual para quien arma y para quien revisa (es lectura). Sin borrador o sin partidas, no se pinta.
- El APU no cambia y el total del presupuesto sigue siendo el costo sin IVA (como en la T18).

- [ ] **Paso 1: pruebas rojas.** API: la vista trae `impuestos` con el oráculo 1.000,00 → 160,00 → 1.160,00 y uno con
  medio céntimo (mitad hacia arriba). Front: las tres cifras con coma decimal; quien revisa también las ve; sin
  partidas no aparecen.
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar. **Paso 4:** → PASA; `npx vitest run src/paginas/hoja`, lint,
  pytest de la vista. **Commits:** `test(presupuesto): IVA en pantalla (rojo)` y `feat(presupuesto): subtotal, IVA y
  total con IVA en Presupuesto`.

### Tarea 6: Versiones

**Modelo:** Opus. **Tamaño:** L. **Bajas:** 9 y 24. **Mueve:** el rastro de aprobaciones a Aprobaciones.

**Archivos:**
- Crear: `paginas/versiones/index.tsx`, `logica.ts`, `textos.ts` y `versiones.scss`, y
  `comun/PanelLateral.tsx` con su `.scss`. Por qué el panel va en `comun/`: lo usan el registro de cambios (aquí), el
  APU (Tarea 7), Componer (Tarea 9) y el informe de importación (Tarea 11). Es una región acoplada a la derecha, no
  modal, como la columna del recorrido; el inventario la pide en las cuatro secciones.
- Modificar: `shell/rutas.ts` (nueva pantalla `versiones`, acción `leer_proyecto`, la misma que exigen sus lecturas
  desde la Tarea 2b),
  `marco/secciones.ts`
  (`versiones.pagina = "versiones"`), `paginas/hoja/index.tsx` (fuera el selector «Versión» y la pestaña
  «Trazabilidad»), `paginas/hoja/logica.ts` (fuera `trazabilidad` de `PESTANAS`) y `paginas/aprobar/index.tsx` (gana el
  bloque «Rastro de la obra»).
- Mover: `paginas/hoja/RastroDeAprobaciones.tsx` a `paginas/aprobar/`; `PestanaTrazabilidad.tsx`, `EstadoDeLaCadena.tsx`
  y `RestaurarVersion.tsx` a `paginas/versiones/`. Se mueven con `git mv` y luego se adaptan, para que el historial los
  siga.
- Pruebas: `paginas/versiones/Versiones.test.tsx`, `paginas/versiones/logica.test.ts`, `comun/PanelLateral.test.tsx` y
  `paginas/aprobar/Aprobar.test.tsx`; `hoja/Versiones.test.tsx` y `TrazabilidadAprobaciones.test.tsx` se mudan con sus
  componentes.

**Interfaces:**
- Consume: `useHojaDeLaObra()`, en concreto `versiones`, `codigo`, `hayCambios`, `abrirGuardado`, `alCrearVersion` y el
  parámetro `?version` de la Tarea 3; `useAprobacionDeVersion` (Tarea 5); `FranjaDelPaso`; `GET /v1/aprobaciones?proyecto=`
  (estado de cada versión, solo con `editar_hoja`); `GET /v1/hoja/cadena`; `GET /v1/hoja/trazabilidad`.
- Produce:
  ```ts
  export function PanelLateral(p: {
    titulo: string; abierto: boolean; alCerrar: () => void; ancho?: "normal" | "ancho"; children: ReactNode;
  }): JSX.Element | null;
  export interface FilaDeVersion extends VersionFila { estado: string | null; abierta: boolean }
  export function filasDeVersiones(v: VersionesRespuesta, estados: Record<string, EstadoDeAprobacion> | null,
    abierta: string | null): FilaDeVersion[];                                   // paginas/versiones/logica.ts
  ```
- `PanelLateral` es un `aside` con `aria-labelledby` hacia su h2. Mide 24 rem (`normal`) o 40 rem (`ancho`) y se
  acopla a la derecha del contenido; por debajo del umbral de la letra (`por-debajo-del-umbral`) pasa por encima, con
  `inline-size: 100%` como máximo. Al abrirse, el foco va al h2; con Esc o «Cerrar» se cierra y el foco vuelve al
  control que lo abrió. Sin animación.
- La pantalla lleva el h1 «Versiones» y la franja: con `hayCambios`, «Siguiente paso: Hay N cambios sin guardar» con
  «Guardar versión…»; con la vigente en aprobación, «La versión V espera dictamen», sin botón. Encima de la tabla va
  el aviso de la cadena de sellos («Integridad verificada» o «Se rompió en la versión X»). La tabla tiene las columnas
  Versión, Fecha (`fechaEsVe`), Motivo, Sale de, Cambios, Estado de aprobación y Vigente; la versión abierta se marca
  con la palabra «abierta», no solo con color. Cada fila tiene «Abrir», que navega a
  `rutaDeObra(c, o, "presupuesto") + "?version=<código>"`, «Ver cambios», que abre el panel «Registro de cambios de la
  versión V», y «Restaurar…», que es el diálogo de hoy y solo aparece con `editar_hoja`.
- En Aprobaciones se añade el h2 «Rastro de la obra» con el `RastroDeAprobaciones` de hoy, para cuentas con
  `leer_proyecto`: desde la Tarea 2b, `GET /v1/aprobaciones` lo exige, así que quien revisa también lo ve.

- [ ] **Paso 1: pruebas rojas.**
  - `logica.test.ts`: `filasDeVersiones` combina el estado («devuelta» en VIV-001) y marca la abierta; con
    `estados = null` deja `estado: null` en todas.
  - `PanelLateral.test.tsx`: tiene rol `complementary` con el nombre de su h2; al abrirse, el foco está en el h2; Esc
    lo cierra y devuelve el foco al disparador; con `abierto=false` no pinta nada; estructura del SCSS, sin ancho fijo
    por debajo del umbral.
  - `Versiones.test.tsx`:
    - un h1 «Versiones» y una tabla con las siete columnas;
    - «Abrir» en VIV-001 navega a `/obra/empresa/3/presupuesto?version=VIV-001`;
    - «Ver cambios» abre el panel «Registro de cambios de la versión VIV-002» con las filas de la trazabilidad simulada;
    - con 3 cambios sin guardar, la franja dice «Hay 3 cambios sin guardar» y su botón abre «Guardar versión»;
    - una cadena rota da el aviso «Se rompió en la versión VIV-002» con su ícono;
    - una obra sin versiones muestra el estado vacío «Esta obra aún no tiene versiones guardadas.» y ningún error
      (Foco 2);
    - cuenta que revisa: ve la tabla con el estado de aprobación, «Abrir» y «Ver cambios», pero no «Restaurar…» ni
      «Guardar versión…», y la franja no tiene botón (Foco 3);
    - administrador puro (sin `leer_proyecto`): «Versiones» no aparece en el árbol;
    - si `GET /v1/aprobaciones` falla, la columna de estado queda vacía y el resto de la tabla se pinta, sin aviso de
      error que tape la tabla;
    - con VIV-001 abierta y VIV-002 vigente, la fila de VIV-001 dice «abierta» (Foco 5).
  - `hoja/Pestanas.test.tsx`: ya no hay combobox «Versión» (baja 9) ni pestaña «Trazabilidad» (baja 24).
  - `Aprobar.test.tsx`: con la sesión de «revisa» se ve el h2 «Rastro de la obra»; sin `leer_proyecto`, no.
  - `marco/secciones.test.ts`: `versiones` tiene `pagina: "versiones"` y aparece en el árbol.
- [ ] **Paso 2:** → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** → PASA; `npx vitest run src/paginas/versiones src/paginas/hoja src/paginas/aprobar src/comun src/marco`;
  lint; duplicado. **Commits:** `test(versiones): seccion versiones (rojo)` y luego `feat(versiones): seccion versiones
  con registro de cambios en panel`.
- [ ] **Paso 5: bajas.** Medir con knip. Quitar el selector, la pestaña y lo que quede sin uso. **Commit**
  `refactor(presupuesto): baja 9 y 24, selector de version y trazabilidad`. Anotar en la bitácora las bajas 9 y 24 y
  el traslado del rastro.

### Tarea 7: El APU de una partida en panel lateral

**Modelo:** Opus. **Tamaño:** M. **Bajas:** ninguna (fusión del inventario: «Buscar partida» con la tabla).

**Archivos:**
- Crear: `paginas/hoja/EditorDeApu.tsx`, el cuerpo de `PestanaApu` sin su lista de búsqueda: título, tablas por rubro,
  rendimiento, cierre, cifras y estado de la partida. Por qué: el mismo editor sirve en la pestaña y en el panel.
- Modificar: `PestanaApu.tsx` (lista de búsqueda y `EditorDeApu`; la partida elegida viene del proveedor),
  `PestanaPresupuesto.tsx` (el código de cada renglón pasa a ser un botón «Abrir el APU de <código>»),
  `ProveedorDeLaHoja.tsx` (gana `partidaElegida` y `elegirPartida`) y `hoja.scss`.
- Pruebas: `paginas/hoja/ApuEnPanel.test.tsx`. Las pruebas de `PestanaApu` siguen verdes.

**Interfaces:**
- Consume: `PanelLateral` (Tarea 6) y `useHojaDeLaObra()`.
- Produce: `EditorDeApu(p: { borrador: BorradorAbierto; partida: string; alAceptar: (r: Resumen) => void; alAusente:
  () => void }): JSX.Element`; en `HojaDeLaObra`, `partidaElegida: string | null` y `elegirPartida: (codigo: string |
  null) => void`.
- La pestaña APU y el panel comparten `partidaElegida`. Si se elige en uno, el otro lo muestra (pregunta abierta 4).

- [ ] **Paso 1: pruebas rojas.**
  - pulsar «Abrir el APU de E-01» en Partidas abre el panel «APU de E-01 · <descripción> · m³», sin cambiar de
    pestaña;
  - editar la cantidad de una línea en el panel manda el mismo `PUT /v1/hoja/borradores/<id>/apu/E-01` que la pestaña y
    actualiza el total bajo la tabla;
  - cerrar el panel (Esc) devuelve el foco al botón de esa fila;
  - con el panel abierto, ir a «Análisis de precio (APU)» muestra E-01 elegida;
  - cuenta que revisa: el panel se abre y muestra el APU con sus cifras, sin campos de cantidad ni de rendimiento
    editables y sin «Agregar línea» ni «Quitar» (Foco 3);
  - estructura (Foco 4): la caja de la tabla de Partidas tiene `overflow-x: auto` y el contenedor de la pestaña no
    fija ningún ancho mayor que el visible; con la clase de letra muy grande, el panel usa la regla de pasar por encima.
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar. **Paso 4:** → PASA; lint; duplicado. **Commits:**
  `test(presupuesto): apu en panel lateral (rojo)` y luego `feat(presupuesto): apu de la partida en panel lateral`.

### Tarea 8: Un solo diálogo para las líneas del APU

**Modelo:** Sonnet. **Tamaño:** M. **Bajas:** ninguna (fusión del inventario: «Cambiar insumo» con «Agregar línea»).

**Archivos:**
- Modificar: `paginas/hoja/AgregarLineaApu.tsx`, que pasa a ser `LineaDelApu.tsx` con dos modos y se renombra con
  `git mv`, y `EditorDeApu.tsx`.
- Baja de archivo (dentro del mismo commit `refactor`, porque la función sigue entera en el diálogo único):
  `paginas/hoja/CambioDeInsumo.tsx`, que se anota en la bitácora.
- Pruebas: `paginas/hoja/LineaDelApu.test.tsx`. Las aserciones de `LineasApu.test.tsx` y `EdicionApu.test.tsx` se
  conservan; solo cambia cómo se abre el diálogo.

**Interfaces:**
- Produce: `LineaDelApu(p: { modo: { tipo: "agregar" } | { tipo: "cambiar"; linea: LineaApu }; borrador: BorradorAbierto;
  partida: string; alAceptar: (r: Resumen) => void; alCerrar: () => void }): JSX.Element`. Usa las mismas rutas de hoy:
  `POST …/apu/{partida}/lineas` para agregar y `POST …/apu/{partida}/insumo` para cambiar.
- En `EditorDeApu`, cada línea tiene «Cambiar» y «Quitar», y hay un solo «Agregar línea». El título del diálogo dice
  «Agregar una línea» o «Cambiar el insumo de <línea>».

- [ ] **Paso 1: pruebas rojas:** en modo `cambiar` el diálogo trae el tipo de línea y la línea fijos y solo pide el
  insumo nuevo; al aceptar se manda el `POST …/insumo` con el cuerpo de hoy; en modo `agregar` se comporta como
  `AgregarLineaApu`; Esc cierra y el foco vuelve al botón que lo abrió; con una cuenta que revisa, `EditorDeApu` no
  pinta «Cambiar», «Quitar» ni «Agregar línea» (Foco 3).
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar. **Paso 4:** → PASA; lint; duplicado; muerto. **Commits:**
  `test(apu): un dialogo para las lineas (rojo)` y luego `refactor(apu): agregar y cambiar insumo en un solo dialogo`.

### Tarea 9: «Agregar partida», puerta única

**Modelo:** Opus. **Tamaño:** L. **Bajas:** 20 y 21.

**Archivos:**
- Crear: `paginas/componer/ComponerPartida.tsx`, el cuerpo de `componer/index.tsx` sin h1 ni navegación. Por qué: la
  misma composición sirve en la pantalla `componer`, que sigue alcanzable por Ctrl+K hasta F5, y en el panel ancho de
  «Agregar partida». `paginas/hoja/Parecidas.tsx`: la lista de propuestas de `similares/index.tsx` con un botón
  «Usar esta partida».
- Modificar: `paginas/hoja/AgregarPartida.tsx` (tres salidas: buscar en el catálogo, parecidas a esta descripción y
  componer nueva en panel; fuera la navegación a `/componer?…volver=hoja`, hallazgo 8 del inventario),
  `paginas/componer/index.tsx` (usa `ComponerPartida`), `paginas/componer/Guardar.tsx` (fuera «Volver a la Hoja» y el
  parámetro `volver`), `shell/rutas.ts` (fuera la pantalla `similares`).
- Baja (commit aparte): `paginas/similares/` (lo que no pasó a `Parecidas.tsx`) y su entrada en `PAGINAS`.
- Pruebas: `paginas/hoja/AgregarPartida.test.tsx` (se amplía), `paginas/hoja/Parecidas.test.tsx` y
  `paginas/componer/ComponerPartida.test.tsx`. Las aserciones de `componer/index.test.tsx` se conservan.

**Interfaces:**
- Consume: `PanelLateral` (`ancho="ancho"`) y el servicio de propuestas de `similares/index.tsx:133`, con la misma
  ruta y el mismo cuerpo.
- Produce: `ComponerPartida(p: { codigoInicial: string; nivelDelTitulo: 1 | 2; alGuardar: (codigo: string) => void;
  alCerrar?: () => void }): JSX.Element` y `Parecidas(p: { descripcion: string; alUsar: (codigo: string) => void }):
  JSX.Element`.
- Dentro del panel, Componer abre con el aviso (`role="note"`, siempre visible) «Esto cambia el catálogo de la
  empresa: la partida queda para todas las obras.». Al guardar, el panel se cierra y el diálogo «Agregar partida»
  queda con el código nuevo elegido.

- [ ] **Paso 1: pruebas rojas.**
  - en «Agregar partida», escribir «excavación de zanja» y pulsar «Buscar parecidas» lista las propuestas simuladas;
    «Usar esta partida» deja el código elegido en el campo Partida;
  - «Componer una partida nueva con el código «Z-99»» abre el panel «Componer una partida» **sin cambiar la ruta** (la
    ruta sigue en `…/presupuesto`), con el aviso del catálogo y el h2 del panel;
  - al guardar la composición, el panel se cierra, el foco vuelve al diálogo y el campo Partida dice «Z-99»;
  - en la pantalla `componer` sola ya no existe «Volver a la Hoja», ni con `?volver=hoja` (baja 21);
  - `shell/rutas.test.ts`: `paginaPorId("similares")` es `undefined` y el buscador no ofrece «Partidas similares»
    (baja 20).
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar. **Paso 4:** → PASA; lint; duplicado. **Commits:**
  `test(presupuesto): agregar partida puerta unica (rojo)` y luego `feat(presupuesto): parecidas y componer en panel
  dentro de agregar partida`.
- [ ] **Paso 5: bajas.** Medir con knip. **Commits:** `refactor(presupuesto): baja 20, pantalla partidas similares` y
  `refactor(componer): baja 21, volver a la hoja`. Anotar las dos en la bitácora.

### Tarea 10: Registro de importaciones de la obra (servidor)

**Modelo:** Sonnet. **Tamaño:** M. **Bajas:** ninguna.

**Por qué:** la pregunta 1 del inventario, aprobada, pide mostrar en Archivos y planos qué se importó (nombre, fecha,
quién y qué produjo) **sin guardar copia del archivo**. Hoy nada lo registra: el plano vive en memoria con su borrador
(`aplicacion/hoja_plano.py`) y el cómputo entra por `POST /v1/hoja/llevar`.

**Archivos:**
- Crear: `aplicacion/tablas_importaciones.py`, una tabla aditiva sin clave foránea a `core.models`, con el patrón de
  `aplicacion/tablas_vial.py`; `aplicacion/importaciones.py`; y
  `migraciones/caso/versions/caso_0020_hoja_importaciones.py` (cuelga de la cabeza real; ver «Migraciones»).
- Modificar: `aplicacion/hoja_borradores.py` (`BorradorVivo` gana `importaciones: tuple[ImportacionDeObra, ...] = ()`),
  `aplicacion/hoja_plano.py` (`fusionar` la anota), `aplicacion/elaboracion.py` (`llevar_a_la_hoja` la anota),
  `api/rutas/hoja_llevar.py` (el cuerpo gana `archivo: str | None`, de hasta 255 caracteres, sin rutas: solo el nombre),
  `aplicacion/hoja_guardado.py` (`guardar` inserta las importaciones del vivo con la versión nueva, en la **misma**
  transacción), `api/rutas/hoja.py` (ruta nueva), `docs/api.json` (con el truco de `git archive HEAD`), `CHANGELOG.md`
  y la tabla de acceso por ruta.
- Pruebas: `tests/unit/test_importaciones.py` y `tests/unit/test_api_hoja_importaciones.py`.

**Interfaces:**
- Produce:
  ```python
  TipoDeImportacion = Literal["plano", "computo"]

  @dataclass(frozen=True)
  class ImportacionDeObra:
      tipo: TipoDeImportacion
      archivo: str            # solo el nombre, nunca una ruta
      fecha_hora: datetime    # la del servidor
      usuario: str
      resumen: str            # «34 filas en el espacio; 2 sin reconocer» / «18 partidas llevadas; 1 pendiente»
      version: str | None     # la versión que la guardó; None = sigue en un borrador sin guardar
      guardada: bool

  def anotar(vivo: BorradorVivo, imp: ImportacionDeObra) -> BorradorVivo
  def registrar_al_guardar(sesion: Session, vivo: BorradorVivo, version_id: int) -> None   # sin commit
  def importaciones_de_la_obra(sesion: Session, proyecto: str, vivos: Iterable[BorradorVivo]) -> list[ImportacionDeObra]
  ```
  La ruta es `GET /v1/hoja/importaciones?proyecto=<código o nombre>` y devuelve `{"importaciones": [{"tipo", "archivo",
  "fecha_hora", "usuario", "resumen", "version": str|null, "guardada": bool}]}`, de la más nueva a la más vieja. Las no
  guardadas salen de los borradores vivos de la ficha para esa obra. Permiso: el `LEER` de `api/rutas/hoja.py`, que
  exige `leer_proyecto` desde la Tarea 2b, igual que `GET /v1/hoja/versiones`; quien revisa ve el registro. Lleva
  `Cache-Control: no-store`. En la `TABLA` de `test_api_acceso_por_ruta.py` entra como `LEER`.

- [ ] **Paso 1: pruebas rojas**, con una obra ficticia «Galpón Norte» y oráculos escritos a mano:
  - `test_fusionar_un_plano_lo_anota_en_el_borrador`: tras `fusionar`, `vivo.importaciones` trae el tipo `plano`, el
    nombre `planta.dxf` y el resumen con los conteos de la `Fusion`;
  - `test_llevar_un_computo_lo_anota`: con `archivo="computo.csv"`;
  - `test_guardar_registra_las_importaciones_con_la_version`: tras guardar VIV-002, la tabla tiene la fila con
    `version_id` de VIV-002;
  - `test_si_guardar_falla_no_queda_ninguna_fila` (todo o nada, C2);
  - `test_un_borrador_descartado_no_deja_registro`;
  - `test_lista_guardadas_y_sin_guardar`, ordenadas por fecha y hora descendente;
  - `test_el_nombre_no_lleva_rutas`: `archivo="C:/x/planta.dxf"` o con `..` da 422 sin eco;
  - API: forma de la respuesta, 401 sin sesión, `no-store` y que la clave de API solo lee;
  - la migración sube y baja sobre una base vacía, y una base con la tabla ya creada se adopta, como en `caso_0019`.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_importaciones.py tests/unit/test_api_hoja_importaciones.py -q -W error -p no:cacheprovider`
  → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** → PASA; `uv run --active ruff check` sobre los archivos tocados; `git diff 51d3ceb4..HEAD -- core/`
  vacío. **Commits:** `test(importaciones): registro de importaciones (rojo)` y luego `feat(importaciones): registro
  de importaciones de la obra`.

### Tarea 11: Archivos y planos, el plano y el registro

**Modelo:** Opus. **Tamaño:** L. **Bajas:** 22, sin código. **Mueve:** «Importar plano» deja la pestaña Espacio.

**Archivos:**
- Crear: `paginas/archivos/index.tsx`, `logica.ts`, `textos.ts`, `archivos.scss` y `SubirArchivo.tsx`, el diálogo propio
  «Subir plano o cómputo» que elige el flujo por la extensión: `.dxf` y `.ifc` van al plano y `.csv` al cómputo de la
  Tarea 12; mientras tanto, `.csv` responde «Pronto: cargar cómputo» **solo en la prueba**, nunca en pantalla.
- Mover: `paginas/hoja/ImportarPlano.tsx` y `logicaPlano.ts` (con `datosDePlano.ts` y `useImportacion.ts`) a
  `paginas/archivos/`, con `git mv`; fuera los comentarios `ui/paginas/hoja.py:1225-1485` y `COLUMNAS_DEL_INFORME de la
  clásica` (hallazgo 7). `ImportarPlano` pasa a ser el cuerpo del diálogo.
- Modificar: `PestanaEspacio.tsx` (fuera el bloque del plano y, en su lugar, un enlace «Importar un plano en Archivos y
  planos»), `shell/rutas.ts` (nueva pantalla `archivos`, acción `leer_proyecto`; subir exige `puedeEditar`) y
  `marco/secciones.ts`
  (`archivos.pagina = "archivos"`).
- Pruebas: `paginas/archivos/Archivos.test.tsx` y `logica.test.ts`. `ImportarPlano.test.tsx` y `PlanoEnHoja.test.tsx` se
  mudan; sus aserciones del flujo (unidad, alturas, circuitos, fusionar, descartar, informe) se conservan y el informe
  dice cuáles cambiaron solo de montaje.

**Interfaces:**
- Consume: `useHojaDeLaObra()` (el `id` del borrador, `refrescar`, `pedirEspacio` e `irAPestana`), `PanelLateral`,
  `FranjaDelPaso` y `GET /v1/hoja/importaciones` (Tarea 10).
- Produce: `filasDeImportaciones(r: ImportacionesRespuesta): FilaDensa[]`, con las columnas Nombre, Tipo («Plano .dxf»,
  «Plano .ifc», «Cómputo .csv»), Fecha y hora (es-VE), Quién, Qué produjo y Versión («sin guardar» cuando
  `guardada=false`).
- La pantalla lleva el h1 «Archivos y planos». La franja «Te falta: subir el plano o describir el espacio» sale
  solo si la persona pidió el espacio (`espacioPedido`) y sigue vacío (pregunta abierta 3); con ella, el botón principal
  es el de la franja. Sin franja, el principal es «Subir plano o cómputo». Debajo va la tabla del registro; elegir una
  fila abre el panel «Informe de la importación» con lo que el registro guardó (el resumen). El informe detallado de la
  importación **en curso** es el de hoy, dentro del diálogo. Al final va el enlace secundario «Describir el espacio a
  mano», que llama a `pedirEspacio()` y a `irAPestana("espacio")` y navega a Presupuesto.
- La baja 22 no cambia código: la pantalla no ofrece el libro ni las carpetas. Se anota en la bitácora con «sin
  commit».

- [ ] **Paso 1: pruebas rojas.**
  - un h1 «Archivos y planos» y una tabla con las filas del registro simulado (un plano guardado en VIV-002 y un
    cómputo «sin guardar»), con la fecha en es-VE;
  - «Subir plano o cómputo» es el único `.cds--btn--primary`; abre el diálogo y, con un `.dxf`, sigue el flujo del plano
    sobre el borrador del proveedor (`POST /v1/hoja/borradores/<id>/plano`);
  - fusionar refresca el borrador del proveedor (`refrescar`) y vuelve a pedir el registro: la fila nueva sale «sin
    guardar»;
  - ir a Presupuesto tras fusionar no abre otro borrador (sigue el mismo `id`);
  - el registro vacío dice «Todavía no se ha importado ningún archivo en esta obra.»;
  - en una obra en blanco, el plano se importa sobre el borrador en blanco (Foco 2);
  - cuenta que revisa: ve la tabla del registro y el panel del informe, pero no «Subir plano o cómputo», ni «Describir
    el espacio a mano», ni ninguna franja con botón; la pantalla no tiene `.cds--btn--primary` (Foco 3);
  - «Describir el espacio a mano» lleva a Presupuesto con la pestaña «Espacio y metrajes» visible y elegida;
  - en Espacio y metrajes ya no está el bloque «Importar plano (DXF o IFC)» y sí el enlace a Archivos y planos.
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar. **Paso 4:** → PASA; `npx vitest run src/paginas/archivos
  src/paginas/hoja src/marco`; lint; duplicado; muerto. **Commits:** `test(archivos): seccion archivos y planos (rojo)`
  y luego `feat(archivos): seccion archivos y planos con registro de importaciones`. Anotar en la bitácora el traslado
  del plano y la baja 22.

### Tarea 12: «Cargar cómputo» absorbe Elaborar

**Modelo:** Opus. **Tamaño:** L. **Bajas:** 13, 14, 15, 16, 17, 18 y 19.

**Archivos:**
- Crear: `paginas/archivos/CargarComputo.tsx` y `paginas/archivos/logicaComputo.ts`. Lo que sobrevive de
  `paginas/elaborar/` se mueve con `git mv` a `paginas/archivos/`: `tipos.ts`, las partes de `logica.ts` que se usan y
  los bloques «Códigos de partida (civil)», «Rendimientos por declarar» y «Pendientes».
- Modificar: `paginas/archivos/SubirArchivo.tsx` (`.csv` va a «Cargar cómputo»), `shell/rutas.ts` (fuera la pantalla
  `elaborar`).
- Baja (commit aparte): `paginas/elaborar/` (lo que no se movió), `PlanDeTrabajo.tsx`, `CODIGO_POR_DEFECTO`,
  `MONEDA_POR_DEFECTO`, `hoy()` si queda sin uso, el bloque «Presupuesto elaborado», «Exportar a Excel» e «Informe de
  auditoría».
- Pruebas: `paginas/archivos/CargarComputo.test.tsx` y `logicaComputo.test.ts`. De `Elaborar.test.tsx` y
  `Llevar.test.tsx` se mudan las aserciones de lo que se queda (extraer, partidas civiles, rendimientos, pendientes y
  llevar); las de lo que se va se borran con su baja y se listan en el informe.

**Interfaces:**
- Consume: `GET /v1/carpeta` (moneda y `lista.fecha`; reutiliza el tipo `CarpetaRespuesta`), el código de la obra
  (`useObraAbierta().obraId`), `POST /v1/computos/{dominio}`, la valoración que usa hoy Elaborar,
  `POST /v1/hoja/llevar` con `archivo` (Tarea 10) y `useHojaDeLaObra().refrescar`.
- Produce: `cuerpoDeValoracion(p: { proyecto: string; moneda: string; fecha: string; items: ItemComputo[]; seleccion:
  SeleccionCivil | null }): CuerpoCalculo` en `logicaComputo.ts`, el que hoy arma Elaborar, pero sin código, moneda ni
  fecha escritos a mano.
- El flujo, dentro del diálogo «Subir plano o cómputo»: el tipo de obra del archivo («Tipo de obra del archivo», civil
  por omisión; pregunta abierta 9) → «Extraer cómputo» → la tabla del cómputo extraído → «Códigos de partida (civil)»
  solo con dominio civil → **«Llevar al presupuesto»**, un solo paso que valora y, si quedan rendimientos por declarar
  o pendientes, los muestra para resolverlos antes de llevar. Al final se llama a `POST /v1/hoja/llevar` y a
  `refrescar()`, y se avisa «Se llevaron N partidas al presupuesto.» con el enlace «Ver en Partidas».
- Sin moneda o sin lista en la carpeta, la franja de la sección dice «Te falta: la carpeta no tiene lista de precios
  para armar» y «Llevar al presupuesto» queda deshabilitado con ese motivo.

- [ ] **Paso 1: pruebas rojas.**
  - `logicaComputo.test.ts`: `cuerpoDeValoracion` usa el código de la obra, la moneda «Bs» de la carpeta y la fecha de
    su lista (`"2026-10-26"`), nunca `"P-001"` ni `"USD"` (bajas 13 y 14).
  - `CargarComputo.test.tsx`:
    - un `.csv` abre «Cargar cómputo» con el tipo de obra civil elegido y **sin** campos «Código del presupuesto»,
      «Moneda» ni «Fecha»;
    - «Extraer cómputo» llama a `POST /v1/computos/civil` y muestra la tabla;
    - «Llevar al presupuesto» sin pendientes valora, llama a `POST /v1/hoja/llevar` con `archivo: "computo.csv"` y
      luego a `refrescar`, y el aviso dice «Se llevaron 18 partidas al presupuesto.»;
    - con rendimientos por declarar, los muestra y no lleva nada hasta registrarlos;
    - no existen «Exportar a Excel», «Plan de trabajo», «Informe de auditoría» ni «Presupuesto elaborado» (bajas 15
      a 18);
    - sin lista en la carpeta, el botón está deshabilitado y la franja dice el motivo;
    - `shell/rutas.test.ts`: `paginaPorId("elaborar")` es `undefined` (baja 19).
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar. **Paso 4:** → PASA; lint; duplicado. **Commits:**
  `test(archivos): cargar computo (rojo)` y luego `feat(archivos): cargar computo dentro de archivos y planos`.
- [ ] **Paso 5: bajas.** Medir con knip. **Commit** `refactor(archivos): baja 13 a 19, la pantalla elaborar` (solo
  quita). Anotar las siete en la bitácora; la 19 dice que la función vive en Archivos y planos › «Subir plano o
  cómputo».

### Tarea 13: Mercado, histórico de precios y cotizaciones

**Modelo:** Sonnet. **Tamaño:** M. **Bajas:** ninguna. **Mueve:** el Histórico y las cotizaciones a Mercado (preguntas
4 y 8 del inventario, aprobadas).

**Archivos:**
- Modificar: `paginas/mercado/index.tsx`, que gana las pestañas «Histórico de precios» y «Cotizaciones de la obra»;
  `paginas/historico/index.tsx`, que se vuelve el componente `HistoricoDePrecios`, sin h1 propio y con h2; su campo
  «Insumo» pasa a `comun/CampoConBusqueda.tsx` (autocompletado, decisión de Eugenio del 2026-10-21);
  `paginas/hoja/PestanaPrecios.tsx`, de donde salen «Registrar / Retirar una cotización…» y entra el enlace
  «Registrar una cotización en Mercado»; y `shell/rutas.ts`, de donde sale la pantalla `historico`.
- Mover: `paginas/historico/porcentaje.ts` a `comun/porcentaje.ts`, porque `paginas/historial/` lo importa (hallazgo 6
  del inventario); y `paginas/hoja/OperacionesDePrecios.tsx` a `paginas/mercado/`.
- Pruebas: `paginas/mercado/Mercado.test.tsx` (se amplía), `paginas/historico/Historico.test.tsx` (se muda a mercado) y
  `paginas/historial/*` (verde, sin cambios de aserción).

**Interfaces:**
- Las cotizaciones trabajan sobre la **versión vigente** de la obra (`GET /v1/hoja/versiones` → `vigente`; pregunta
  abierta 8). Al crear la versión nueva se avisa «Se creó la versión V con la cotización.» con el enlace «Abrirla en
  el Presupuesto» (`?version=V`, Tarea 3). La tabla de precios que necesita `OperacionesDePrecios` (`filas`) se lee con
  `rutaDePrecios(proyecto, vigente)`, como hoy la pestaña Precios.
- El insumo del histórico se elige con `CampoConBusqueda` sobre la lista de insumos que ya lee Mercado
  (`GET /insumos`, `paginas/mercado/logica.ts:202`, la misma carga de `EstudioDelLado.tsx`), y reemplaza a «Insumo
  (descripción exacta)». Al servidor se manda la descripción elegida, como hoy.

- [ ] **Paso 1: pruebas rojas:**
  - Mercado tiene las cuatro pestañas en orden («Lo que compramos», «Lo que cobramos», «Histórico de precios»,
    «Cotizaciones de la obra»);
  - en «Histórico de precios», elegir «Cemento gris» en el autocompletado y «Filtrar» pide el histórico con esa
    descripción y pinta la variación en es-VE («12,50 %»);
  - con una cuenta que revisa, «Cotizaciones de la obra» muestra las cotizaciones sin «Registrar una cotización…» ni
    «Retirar una cotización…», porque cotizar sigue exigiendo `editar_hoja` (Foco 3);
  - «Registrar una cotización…» manda `POST /v1/hoja/versiones/cotizar` con la versión vigente y el aviso enlaza a
    `…/presupuesto?version=V`;
  - en Presupuesto › Precios ya no hay «Registrar una cotización…» y sí el enlace a Mercado;
  - `paginaPorId("historico")` es `undefined`;
  - las pruebas de `historial` siguen verdes.
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar. **Paso 4:** → PASA; lint; duplicado; muerto. **Commits:**
  `test(mercado): historico y cotizaciones (rojo)` y luego `feat(mercado): historico de precios y cotizaciones de la
  obra`. Anotar los dos traslados en la bitácora.

### Tarea 14: Cierre de F4

**Modelo:** Sonnet para los menores; el orquestador (Opus) corre la suite y el navegador.

- [ ] **Paso 1:** un solo agente cierra los menores de los árbitros de las Tareas 0 a 13, con su árbitro.
- [ ] **Paso 2:** `frontend-desktop/DESIGN.md` gana cinco secciones: «Cabecera de la obra» (estado con ícono y
  palabra), «Franja del paso» (precaución con un solo botón de acción), «Panel lateral», «Filas afectadas» y «Empresa
  plegada con letra grande». Se corrige lo que haya quedado viejo, como «Hoja de la obra» o las nueve pestañas. Se añade
  CHANGELOG.
- [ ] **Paso 3:** se mide contra la línea base del §6.1, por sección: líneas TS/TSX de producto, pruebas y SCSS de
  `paginas/obras`, `hoja`, `elaborar`, `componer`, `similares`, `historico`, `archivos` y `versiones`, comparadas con
  el inventario §6 (13.326 líneas de producto y 1.036 de SCSS). Se miden también knip (0 archivos sin uso) y jscpd
  (≤ 1 %).
- [ ] **Paso 4:** suite completa: `uv run --active pytest -q -W error -p no:cacheprovider`, `npm test`, `npm run lint` y
  `npm run build`. Las fallas que ya estaban antes se listan aparte, con su causa.
- [ ] **Paso 5: la única pasada en navegador** (script de capturas de F3 adaptado, perfil propio, obras ficticias,
  tema neutro y, solo en local, el de la empresa), a 1056, 1366 y 1910 px con letra 1 y 1,5, y además 1366×657 con
  «Muy grande»:
  - Empresa plegada: cuántas obras caben ahora en el árbol, comparado con las 7 y 4 del cierre de F3;
  - el Resumen de una obra en ejecución y el de una en blanco;
  - el Presupuesto en cada estado de la franja, con el panel del APU abierto y Componer en panel;
  - Versiones con el registro abierto;
  - Archivos y planos con el diálogo de subir;
  - Mercado › Histórico.
  Se comprueba: un solo h1 y un solo botón principal por vista; nada de desplazamiento horizontal (Foco 4); la franja
  con su ícono y su palabra; las filas afectadas con su severidad en texto; y el foco al abrir y cerrar cada panel. Las
  capturas se quedan en el scratchpad.
- [ ] **Paso 6:** bitácora `docs/bitacora/<fecha>-cierre-f4.md`: qué se hizo, las cifras antes y después, las capturas
  citadas por nombre, la tabla de las 25 bajas con su commit (la misma de `preguntas-para-eugenio`) y lo pendiente para
  F5. **Commit** `docs(bitacora): cierre de f4`.

## Fuera de esta tanda

- El rediseño visual de Aprobaciones, Mercado (más allá de las dos pestañas de la Tarea 13) y Control de obra: es el
  resto de F4 según §7 y queda para un plan aparte, con su propio inventario.
- **Pendiente de F5 (Eugenio, 2026-10-31):** las cifras de valor ganado sumadas de toda la carpeta, con sus notas de
  conversión y «fuera de la suma», que la baja 3 quita del Resumen, vuelven en Empresa. El plan de F5 parte del commit
  de esa baja (`git checkout <sha>^ -- frontend-desktop/src/paginas/obras/CifrasMesa.tsx` y lo que use) y las monta en
  la entrada de Empresa que corresponda.
- F5 Empresa (Componer queda alcanzable por Ctrl+K hasta que Precios y catálogo lo aloje), F6 Ayuda (el
  «¿Qué es esto?» de la Tarea 4 pasa a panel con guías; «Empieza aquí» recoge lo de la baja 6) y F7, el retiro final de
  las rutas viejas (`/hoja`, `/componer`) y del enlace `to="/hoja"` de `paginas/vial/Tramos.tsx`, que hoy funciona por la
  redirección del marco.
- Comparar dos versiones (pregunta 9 del inventario).
- Guardar copia de los archivos importados (pregunta 1): solo se registra.

## Preguntas abiertas (para Eugenio; cada una con la decisión tomada, prudente y reversible)

| # | Pregunta | Lo que se hará | Cómo cambiarlo |
|---|---|---|---|
| 1 | La baja 3 quita las cifras de valor ganado sumadas de toda la carpeta, que no son de una obra. ¿Dónde las quiere ver? | **Respondida por Eugenio (2026-10-31):** se quitan de la carpeta en F4 (commit revertible de la Tarea 2) y vuelven en F5, en Empresa. Queda como pendiente de F5 en «Fuera de esta tanda». | — |
| 2 | El Resumen y la cabecera leen `GET /v1/obras/resumen`, que calcula todas las obras de la carpeta, y se quedan con una. ¿Pesa? | Se usa así: es la ruta que ya existe y se lee una vez por obra, no por sección | Ruta `GET /v1/obras/{id}/ficha` en `api/rutas/obras.py` que filtre antes de calcular, y cambiar solo `useFichaDeLaObra` |
| 3 | No hay una marca de «obra de instalaciones» (el proyecto no guarda dominio). ¿Cuándo se ve «Espacio y metrajes»? | Cuando el espacio no está vacío, o después de «Describir el espacio a mano» en Archivos y planos (dura mientras la obra esté abierta) | `pestanasVisibles` en `paginas/hoja/logica.ts` (mostrarla siempre, o leer un dominio si el servidor lo da) |
| 4 | §3.2 pide la pestaña APU y además el APU en panel desde la fila. ¿Las dos? | Las dos, con el mismo `EditorDeApu` y la partida elegida en común | Quitar la pestaña de `PESTANAS` (el panel se queda) |
| 5 | Registro de importaciones: lo importado se registra al **guardar la versión**. ¿Y lo que nunca se guarda? | Lo importado y no guardado sale como «sin guardar» mientras viva el borrador; si el borrador se descarta, no deja rastro (no llegó a ninguna versión) | Escribir la fila al fusionar o llevar, con `version = null`, en `aplicacion/importaciones.py` |
| 6 | La baja 11 quita el botón «Crear plan secuencial» (el inventario dudaba). | Fuera el botón; la ruta del servidor se queda, así que volver es solo de front | `git revert` del commit de la baja 11 |
| 7 | El Histórico de cambios de precio deja de alcanzarse con Ctrl+K sin una obra abierta (ahora vive en Mercado de cada obra). | Se acepta: la pregunta 4 lo mandó a Mercado | Devolver la entrada `historico` a `PAGINAS` (una línea) mientras F5 decide su sitio en Precios y catálogo |
| 8 | Desde Mercado, ¿sobre qué versión se cotiza? | Sobre la vigente, y se ofrece abrir la versión nueva en el Presupuesto | Pasar la versión abierta del borrador, si la hay, en `paginas/mercado/OperacionesDePrecios.tsx` |
| 9 | «Cargar cómputo»: una obra civil no necesita elegir el tipo, pero el proyecto no dice el suyo. | Selector «Tipo de obra del archivo», con civil por omisión | Quitar el selector si el servidor da el dominio de la obra |
| 10 | «¿Qué es esto?» llega antes de F6. | Desplegable propio con `useDespliegue` (ya existe), en vez del `Toggletip` de Carbon, que el proyecto no usa y no está probado con `npm run dist` | F6 lo cambia por el panel de ayuda; o usar el `Toggletip` si pasa `npm run dist` |
| 11 | Íconos de la etapa (pregunta 10 del inventario: palabra con ícono). | Elaboración `Edit`, aprobación `Time`, aprobada `CheckmarkOutline`, ejecución `InProgress`, atrasada `WarningFilled`; solo la atrasada lleva color | La tabla de `marco/EtapaDeObra.tsx` |
| 12 | El aviso «Instantánea de la versión» (el inventario dudaba de él). | Se queda tal como está | Quitarlo en `paginas/hoja/index.tsx` si no sirve |
| 13 | «Empresa» plegada: ¿se recuerda entre sesiones? | No: arranca plegada con letra Grande o Muy grande, salvo con una entrada de Empresa abierta | Guardarlo junto al tamaño de letra en `comun/preferenciaDeLetra.ts` |
| 14 | La migración `caso_0020` puede chocar con la línea vial. | Se renumera según la cabeza real al escribirla y otra vez al integrar | — |
| 15 | La «franja amarilla con un solo botón amarillo» de la maqueta frente a los papeles del color de la Tarea 4c de F3. | La franja es precaución (fondo amarillo claro) y su botón es la acción (complementario, texto blanco) | Las clases de `comun/FranjaDelPaso.scss` |
| 16 | Todas las rutas de la Hoja exigían `editar_hoja`, incluso las de lectura, así que quien revisa no habría visto Presupuesto, Archivos y planos ni Versiones. ¿Las debe ver? | **Respondida por Eugenio (2026-10-31):** sí, en solo lectura. Tarea 2b: las lecturas pasan a `leer_proyecto` (acción que ya existe), las escrituras siguen en `editar_hoja` y el front no pinta controles de edición sin `puedeEditar` | — |

## Decisiones de la Tarea 0

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **¿Qué cuenta como «letra grande»?** · Todo lo que no sea `normal`: `grande` y `muy-grande`, los mismos dos tamaños que ya compactan la barra (`con-letra-grande` en `marco/_umbrales.scss`). Una sola condición (`tamano !== "normal"`) evita que la barra y el SCSS discrepen. · Cambiar `empresaPlegable` en `marco/BarraLateral.tsx`.
2. **¿Cómo se observa el tamaño de letra?** · `useTamanoDeLetra` con `useSyncExternalStore` sobre un `MutationObserver` de `data-silice-letra`. El atributo es una fuente externa a React; así no hay un primer pintado con un tamaño y un segundo con otro, y la regla `react-hooks/set-state-in-effect` del proyecto no se salta. El plan decía «estado inicial y observador»; el resultado visible es el mismo. · Volver a `useState` más `useEffect` en `comun/useTamanoDeLetra.ts`.
3. **`useZoomHoja` y el `useMemo` del plan.** · El plan pedía `useMemo(() => factorDeLetra(), [tamano])`, pero ESLint marca `tamano` como dependencia innecesaria (no se usa dentro). Se llama a `useTamanoDeLetra()` solo para suscribirse (el hook se vuelve a pintar al cambiar) y `factorDeLetra()` se lee directo: es una búsqueda en un arreglo de tres elementos. · Cambiar la línea en `visor/useZoomHoja.ts`.
4. **¿Qué pasa con lo que la persona abrió o cerró cuando cambia la letra?** · La decisión se guarda con el tamaño con que se tomó (`{tamano, abierta}`) y deja de valer al cambiarlo; vuelve a mandar el arranque (plegada, o abierta si hay una entrada de Empresa abierta). El alto disponible cambió y la decisión previa ya no responde a él. No se usa un efecto para borrarla (misma regla de lint). · Dejar un `useState<boolean | null>` simple si se prefiere que la decisión sobreviva al cambio.
5. **Plegado = no pintar la lista.** · Plegada, la `ul` no está en el DOM (no solo oculta): así sus enlaces salen del orden de tabulación y del árbol de accesibilidad sin más código, y `aria-controls` apunta a una lista que existe solo cuando `aria-expanded` es verdadero. · Pintarla siempre con `hidden`.
6. **Con letra normal nada cambia.** · Sigue siendo un `h2` sin botón, con sus cinco entradas. Un botón que no pliega nada sería un control que engaña.
7. **Foco y tamaño del botón.** · El botón hereda `font`, `color`, `text-transform` y `letter-spacing` del título (no parece otro control), usa el contorno de foco `--cds-focus` de las demás filas y con letra grande no baja de 1,5 rem, la misma altura mínima de las filas compactadas. · Reglas `.silice-marco-lateral__empresa-boton` en `marco/BarraLateral.scss`.
8. **Chevron.** · El mismo par `ChevronDown`/`ChevronRight` de las obras (16 px, `aria-hidden`): abierto mira hacia abajo, cerrado a la derecha, igual que el árbol.
9. **Sin guardar en el navegador.** · La decisión vive en el estado de la barra (YAGNI, ya anotado en la pregunta 13).
10. **`npm run duplicado` no se pudo correr.** · `jscpd` no está instalado en este `node_modules` (el comando no se reconoce); no se instaló nada nuevo. Queda para la corrida del árbitro o de la Tarea 14.

## Decisiones de la Tarea 1

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Menores de la Tarea 0.** · `ZonaEmpresa.tsx` se lleva el bloque de Empresa (hook de letra, estado `{tamano, abierta}` tipado como `TamanoDeLetra`, `h2` y lista) y recibe `entradas`, `entradaActiva` e `idBase`; `BarraLateral` queda en 276 líneas y conserva su razón de cabecera, ahora con la mención a `ZonaEmpresa`. Las pruebas de Empresa se quedan en `BarraLateral.test.tsx` (pasan sin relajarse; prueban la barra montada, que es lo que ve la persona). · Mover el `describe` a `ZonaEmpresa.test.tsx`.
2. **`useFichaDeLaObra(obraId, carpeta)` recibe la carpeta.** · El plan lo firmaba solo con `obraId`, pero dos carpetas pueden tener el mismo número de obra: pasar de la obra 1 de una carpeta a la obra 1 de otra no habría repetido la lectura y la cabecera habría dicho el estado de la otra. La clave de la lectura es `[carpeta, obraId]`. · Quitar el parámetro (aceptando ese caso borde).
3. **Mientras llega la ficha de otra obra no se enseña la anterior.** · El resultado guardado lleva su clave y solo vale si es la de la obra abierta; en una recarga (`recargar`) sí se conserva la ficha, para que la cabecera no parpadee. · Guardar solo el último resultado sin clave.
4. **Una fila sin `etapa_texto` es `sin_dato`.** · El estado se dice con las palabras del servidor; sin ellas no se inventa una (misma regla que un 403 o la falta de fila). Es defensivo: el servidor siempre las manda. · Quitar la comprobación de `typeof` en `useFichaDeLaObra`.
5. **`EtapaDeObra` con su propia hoja (`EtapaDeObra.scss`).** · Las clases `silice-etapa` salen de `paginas/obras/obras.scss` (`silice-mesa__etapa`) y viven con el componente, que ahora usan la cabecera y la tabla de obras (y el Resumen de la Tarea 2). `Mesa.test.tsx` cambia el selector `.silice-mesa__etapa` por `.silice-etapa` y su cuenta de lecturas de `GET /v1/obras/resumen` pasa de 1 a 2: la mesa y la ficha de la cabecera, una por obra (es el diseño de esta tarea; la Tarea 2 da de baja la mesa). · Revertir el commit y volver a la clase vieja.
6. **La cabecera se parte en dos.** · `CabeceraDeObra.tsx` solo pinta (nombre, «Estado: …», «Versión: …» y la lista de la carpeta); `EspacioDeObra.tsx` conserva `ObraDeLaRuta`, que lee la ficha, arma el `ContextoDeLaObra` y el `ContextoAplicacion` que ya armaba. El valor del contexto no se memoiza: cambia solo cuando esa pieza se vuelve a pintar. · Memoizar `abierta` si una sección pesada lo pide.
7. **La versión es la vigente de `useObras`** (la de `ObraDeCarpeta.version_codigo`), no la de la ficha; la versión abierta en el borrador se añade en la Tarea 3. · Leer `ficha.obra.version`.
8. **Tipos movidos.** · `Etapa`, `ObraFilaRespuesta` y `SiguienteRespuesta` pasan de `paginas/obras/logica.ts` a `api/tipos.ts`; `logica.ts` y `TablaObras.tsx` actualizan sus imports.
9. **Rojo por módulos ausentes.** · Las pruebas rojas fallaron al no existir `obraAbierta`, `useFichaDeLaObra` ni el nuevo `EspacioDeObra`; el rojo es de importación, no de aserción. `npm run duplicado` no se corrió (sigue sin `jscpd` en este `node_modules`, ver Tarea 0, decisión 10).

## Bajas aplicadas

Formato: baja · qué se quitó · commit · dónde vive hoy la función · cómo volver. `knip` no está instalado en este `node_modules` (no se instaló nada): la medida se hizo con `grep` de importaciones y con `npm run lint` (eslint y tsc) en 0. Antes: `paginas/obras/` con 2.427 líneas en 12 archivos; después, 7 archivos.

| # | Qué se quitó | Commit | Dónde vive hoy | Cómo volver |
|---|---|---|---|---|
| 1 | Botón «Nueva obra» de la cabecera del Resumen (ya no estaba en `index.tsx` desde el commit `b62d3679`, que reescribió la página) | `023c4416` (los archivos) y `b62d3679` (la página) | «Nueva obra» de la barra lateral | `git revert 023c4416` y `git checkout b62d3679^ -- frontend-desktop/src/paginas/obras/index.tsx` |
| 2 | `TablaObras.tsx`: tabla «Obras» de toda la carpeta | `023c4416` | Árbol de obras; cifras de la obra abierta en el Resumen | `git revert 023c4416` |
| 3 | `CifrasMesa.tsx`, notas de conversión y «fuera de la suma» (y `textoConversion`, `textoFueraDeSuma`, tipos de cifras) | `023c4416` | **Pendiente de F5:** vuelven en Empresa | `git revert 023c4416` |
| 4 | `ColumnaPendientes.tsx`, `columnaDeLaMesa`, `gruposDeLaMesa` y los tipos de «Aprobar» | `023c4416` | Bandeja de F3; el Resumen muestra los pendientes de la obra | `git revert 023c4416` |
| 5 | `LoQuePuedeHacer.tsx` y su hoja | `023c4416` | Ctrl+K | `git revert 023c4416` |
| 6 | «Cree su primera obra» y «Probar con datos de demostración» (`PrimerosPasos`) | `b62d3679` (salió con la página) | Barra lateral; Empresa › Carpetas de trabajo; «Empieza aquí» (F6) | `git checkout b62d3679^ -- frontend-desktop/src/paginas/obras/index.tsx` |

Las seis van en un solo commit de baja (`023c4416`) porque el plan lo pide así para esta tarea y porque la mesa es una sola pieza: las bajas 1, 5 y 6 ya habían salido de la página en el commit de la implementación. No es posible deshacer una baja suelta con `git revert`; se deshace el grupo. Las pruebas de la mesa (`Mesa`, `PorAprobar`, `Obras`) se quitaron con ella. Tras `git revert 023c4416`, la mesa vuelve a existir pero ya no está montada (la pantalla `obras` es el Resumen).

### Tarea 4 (2026-10-31)

Mismo formato. Las 7, 8, 10, 11 y 12 van cada una en su commit, **antes** del `feat` (así `git revert` devuelve la función entera y no un bloque muerto); la 23 y la 25 van con el `feat` (ver «Decisiones de la Tarea 4», punto 1).

| Baja | Qué se quitó | Commit | Dónde vive hoy | Cómo volver |
|---|---|---|---|---|
| 7 | Título «Hoja de la obra» (h1, `rutas.ts`, diálogo de salida) | `bc11a3c3` | Título «Presupuesto» | `git revert bc11a3c3` |
| 8 | Aviso «Use el selector de obra de la cabecera para abrir su hoja» (sin obra ahora solo dice «Elija una obra») | `da1b03b3` | Dentro de la obra siempre hay obra | `git revert da1b03b3` |
| 10 | Bloque «Factores de la versión» de la pestaña APU, `FactoresDeLaVersion` y la variante `compacto` de los ajustes | `963f6485` | Pestaña «Ajustes de costo» | `git revert 963f6485` |
| 11 | Botón «Crear plan secuencial» y su llamada (`crearPlan`, `rutaDePlanSecuencial`); la ruta del servidor no se toca | `04569ebb` | «Plan desde los rendimientos» | `git revert 04569ebb` |
| 12 | «Total del presupuesto» de Espacio y de Parámetros, la línea «Moneda del proyecto» y la propiedad `moneda` de `PestanaParametros` | `b41c38b9` | Total bajo la tabla de «Partidas» | `git revert b41c38b9` |
| 23 | Pestaña «Punto de equilibrio» separada (ahora es el bloque de debajo del plan) | `b0f976d6` (con el feat) | Pestaña «Plan y equilibrio» | `git revert b0f976d6` (deshace el feat entero) |
| 25 | Texto largo de ayuda encima de cada pestaña | `b0f976d6` (con el feat) | `paginas/hoja/textos.ts`, tras «¿Qué es esto?» (`comun/QueEsEsto.tsx`) | igual que la 23 |

### Tarea 12 (2026-11-02)

Las siete van en un commit (`969ad67f`), más `7cf1358f`, que quita tres aserciones de Componer que miraban el enlace a Elaborar; son piezas de una sola pantalla que se va entera. `knip` y `jscpd` no están instalados: se midió con `grep` y `npm run lint` en 0 (`paginas/elaborar/`: 1.958 líneas en 6 archivos, fuera; `logicaComputo.ts` de 259 a 178 líneas y `tipos.ts` de 121 a 96).

| Baja | Qué se quitó | Commit | Dónde vive hoy | Cómo volver |
|---|---|---|---|---|
| 13 | Campo «Código del presupuesto» de Elaborar y `CODIGO_POR_DEFECTO` («P-001») | `969ad67f` | El código de la obra (`cuerpoDeValoracion`) | `git revert 7cf1358f 969ad67f` |
| 14 | Campos «Moneda» y «Fecha» propios de Elaborar, `MONEDA_POR_DEFECTO` («USD») y `hoy()` | `969ad67f` | La moneda de la carpeta y la fecha de su lista (`GET /v1/carpeta`) | igual que la 13 |
| 15 | «Exportar a Excel» de Elaborar (`POST /presupuestos/calcular/excel` ya no se llama; la ruta del servidor se queda) | `969ad67f` | «Descargar Excel» del Presupuesto | igual que la 13 |
| 16 | «Plan de trabajo» de Elaborar (`PlanDeTrabajo.tsx`, `FilaPlan`, los períodos «Día N») | `969ad67f` | Pestaña «Plan y equilibrio» | igual que la 13 |
| 17 | «Informe de auditoría» de Elaborar (y el veredicto) | `969ad67f` | Pestaña «Revisión» | igual que la 13 |
| 18 | Bloque «Presupuesto elaborado» (total, severidades, tabla de partidas y «Llevar a la Hoja de la obra», `LlevarALaHoja.tsx`) | `969ad67f` | El resultado va directo a «Partidas» | igual que la 13 |
| 19 | Pantalla «Elaborar un presupuesto» (`paginas/elaborar/`, su entrada en `shell/rutas.ts`, el enlace de Componer y la fila del recorrido funcional) | `969ad67f` y `7cf1358f` | Archivos y planos › «Subir plano o cómputo» › «Cargar cómputo» | igual que la 13 |

## Decisiones de la Tarea 2

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Rojo por aserción.** · Las pruebas rojas (`72adbd4e`) usan stubs mínimos de `FranjaDelPaso`, `pasoDeLaObra` y `destinoDeLaAccion` y la página antigua: fallan por `Unable to find ... "Siguiente paso"`, `expected null to deeply equal {...}` y `expected '' to be '/obra/Carpeta%20Sur.db/3/presupuesto'`, no por una importación ausente. `pedir` se simula con una respuesta vacía para que la mesa antigua no caiga antes de la aserción. · —
2. **Una lectura del resumen por obra abierta.** · `Resumen.test.tsx` monta `EspacioDeObra` con la página real y cuenta las llamadas a `GET /v1/obras/resumen`: una, y los nombres de las otras obras no aparecen. La página no pide nada por su cuenta. · —
3. **`pasoDeLaObra` con «qué pasa» vacío.** · Un texto vacío cuenta como ausente (`if (obra.que_pasa)`), igual que `null`. · Comparar con `!== null`.
4. **Pendientes.** · Se filtran con `claveDeObra(carpeta, obraId)` (la carpeta cuenta). Cada uno es una fila con su texto y un botón `tertiary` `sm`; el botón navega con `useNavegarSeguro`, que pregunta si hay formularios sin guardar. No se usa `elegirObra` ni `confirmarSalida` aparte: el destino es una ruta de la propia obra. · —
5. **Total.** · Se muestra con `textoTotal` (`formatoEsVe`), sin recortar decimales, así que el texto visible ya es el exacto; no hay un segundo texto accesible. · Pasar a `centesimasEsVe` con el exacto en `title`.
6. **Cifras como lista de definiciones.** · `dl` dentro de un `div role="group"` etiquetado «Cifras de la obra»: la pareja nombre y valor la leen bien los lectores de pantalla; la rejilla `auto-fit` baja a una columna con letra grande sin desplazamiento horizontal. · —
7. **Título del registro.** · La pantalla `obras` pasa a «Resumen de la obra» (`shell/rutas.ts`) con otra línea para Ctrl+K. Dos pruebas ajenas se adaptan: `titulos.test.tsx` da a cada página un contexto de obra (cargando) y `Marco.test.tsx` espera el nuevo título. · —
8. **Cuenta que revisa.** · La prueba cubre el botón ausente hacia `control`. El caso «hacia `hoja` sí sale el botón» depende de que la Tarea 2b ponga `hoja` en `leer_proyecto`; hoy `hoja` exige `editar_hoja`, así que no se probó. Queda anotado en el propio test. · Añadirlo en la Tarea 2b.
9. **Commit de la implementación con pruebas de la mesa en rojo.** · Entre `b62d3679` y `023c4416` las pruebas de la mesa antigua fallan (la página ya es el Resumen); el commit de la baja las quita. Cada commit se puede revertir, pero `b62d3679` solo es verde junto con `023c4416`. · —
10. **Herramientas.** · `knip` y `jscpd` no están en este `node_modules`; no se corrieron `npm run muerto` ni `npm run duplicado`. Verificación: `vitest` de `src/paginas/obras src/paginas/pendientes src/marco src/shell src/comun` (739 verdes) y `npm run lint` en 0. · —
11. **`conLaMesa` y `RUTA_DE_LA_MESA`.** · Se quedan en `shell/obras/datosDePrueba.tsx` porque `Marco.test.tsx` los sigue usando con pantallas de mentira (no con la mesa real). El plan los daba por retirados. · Retirarlos junto con esas pruebas del marco.
12. **`scripts/recorrido_ux_playwright.py`** sigue buscando clases `silice-mesa__*` que ya no existen; el guion es de auditoría visual y no forma parte de la CI. No se tocó (fuera del alcance). · Actualizarlo en la Tarea 14.

## Decisiones de la Tarea 2b

Formato: pregunta · lo que se hizo · cómo cambiarlo.

### Clasificación de las rutas de la Hoja

Se revisó cada ruta de `api/rutas/hoja.py`, `hoja_exportar.py`, `hoja_llevar.py`, `hoja_plano.py` y la lectura de
`aprobaciones.py`. «Escribe» quiere decir: cambia el borrador vivo (su `rev`), escribe en la base del caso o deja
archivos en el servidor. Las sesiones de lectura (`SesionDep`) no confirman nada al cerrarse (`Session.close` deshace),
así que una lectura solo escribiría si llamara a `commit` en algún punto de su camino; se buscó cada `commit` de
`aplicacion/hoja*.py`, `aprobaciones.py`, `atipicos.py`, `control.py` y `entrega.py`.

| Ruta | Acción | Qué hace | Por qué |
|---|---|---|---|
| `GET /v1/hoja/versiones` | LEER | lee el historial | sin `commit` |
| `GET /v1/hoja/antes-y-despues` | LEER | compara con la línea base | sin `commit` (`hoja_lineas_apu` no confirma) |
| `GET /v1/hoja/precios` | LEER | evalúa R11 y R12 a hoy | en memoria (S1 §4.3) |
| `GET /v1/hoja/precios/atipicos` | LEER | busca variaciones | sin `commit` ni archivos (`aplicacion/atipicos.py`) |
| `GET /v1/hoja/trazabilidad` | LEER | historial y registros | sin `commit` |
| `GET /v1/hoja/cadena` | LEER | recalcula cada huella | solo lee (`entrega.estado_de_la_cadena`) |
| `GET /v1/hoja/borradores` | LEER, solo cuenta | lista los borradores de **su** ficha | memoria; listar no renueva el plazo |
| `POST /v1/hoja/borradores` | LEER, solo cuenta | abre un borrador de **su** ficha | **escribe la instantánea UC-15e** si falta (ver la decisión 1) |
| `GET /v1/hoja/borradores/{id}` | LEER, solo cuenta | base y resumen | memoria; otra ficha, 404 |
| `DELETE /v1/hoja/borradores/{id}` | LEER, solo cuenta | cierra **su** borrador | memoria; uno ajeno es 204 y no se cierra |
| `GET …/vistas/{espacio,presupuesto,apu,plan,equilibrio,parametros,auditoria}` | LEER, solo cuenta | vistas calculadas | memoria |
| `GET …/insumos` | LEER, solo cuenta | candidatos de la lista de la versión | solo lee |
| `GET …/cambios` | LEER, solo cuenta | diferencia con la versión abierta | memoria |
| `GET …/excel` | LEER, solo cuenta | arma el libro en memoria y lo devuelve | no escribe ni la base, ni el borrador, ni un archivo (`aplicacion/hoja_exportar.py`) |
| `GET /v1/aprobaciones?proyecto=` | LEER | rastro, fases y estados de la obra | solo lee; no llama a `_reflejar` (el índice de la instalación) |
| `PUT …/espacio`, `/cantidades`, `/parametros`, `/plan` | EDITAR | cambian el borrador | sube el `rev` |
| `POST …/plan/secuencial`, `/plan/rendimientos` | EDITAR | rehacen el plan del borrador | sube el `rev` |
| `POST …/partidas`, `/partidas/quitar` | EDITAR | agregan o quitan renglones | sube el `rev` |
| `PUT …/apu/{partida}`, `POST …/insumo`, `…/lineas`, `…/lineas/quitar` | EDITAR | cambian el APU de la copia | sube el `rev` |
| `POST …/guardar` | EDITAR | guarda la versión | escribe en la base (`BEGIN IMMEDIATE`) |
| `POST …/plano`, `/plano/unidad`, `/plano/alturas`, `/plano/circuitos`, `/plano/fusionar` | EDITAR | importan un plano | escriben en una carpeta temporal del servidor; fusionar cambia el borrador |
| `DELETE …/plano` | EDITAR | descarta la importación | borra su carpeta temporal; quien revisa no puede importar, así que no tiene nada que descartar |
| `POST /v1/hoja/llevar` | EDITAR | lleva cantidades al borrador | cambia el borrador |
| `POST /v1/hoja/versiones/restaurar`, `/cotizar`, `/retirar-cotizacion` | EDITAR | crean una versión | escriben en la base |
| `POST /v1/hoja/versiones/convertir` | CONVERTIR_Y_REAJUSTAR | crea una versión en otra moneda | escribe en la base (sin cambio) |
| `GET /v1/aprobaciones/mias`, `POST /v1/aprobaciones` | EDITAR | lo de quien envía | sin cambio |

1. **`POST /v1/hoja/borradores` escribe en la base.** · Abrir una versión sin instantánea (clínica, TI-001, importadas)
   la crea: composiciones, plan inferido y un `RegistroCambio` a nombre de quien abre, y `aplicacion.hoja.abrir_version`
   lo confirma (`sesion.commit()`). Que quien revisa firme ese registro no es inocuo. Como `aplicacion/hoja.py` es la
   copia del congelado y no se toca, la guardia va en la API: sin `editar_hoja`, la ruta corre dentro de
   `api.sin_escribir.sin_escribir(sesion)` (eventos `before_flush` y `do_orm_execute` de esa sesión), que lanza
   `EscrituraNegada` antes de que nada llegue a la base; la ruta deshace y responde 409 «Esta versión todavía no se
   puede ver en solo lectura: quien arma el presupuesto tiene que abrirla una vez para prepararla.». No hay carrera: la
   guardia es de la sesión, no una comprobación previa. Con la instantánea ya hecha (lo normal: toda versión guardada
   por la Hoja la tiene), abrir no escribe nada y quien revisa la ve. Prueba:
   `test_revisa_no_crea_la_instantanea_al_abrir` (compara las filas de todas las tablas, antes y después). · Dejar la ruta en EDITAR (y
   quien revisa no ve nada), o abrir sin instantánea en memoria si `aplicacion` ofreciera esa variante.
2. **Lo que la guardia no cubre.** · Solo lo que pasa por la sesión. Una escritura por `connection().exec_driver_sql`
   no la vería; el camino de `abrir_version` no la usa (se revisó `core/budget/instantanea.py`: todo es `session.add`).
   · Una guardia de conexión (`PRAGMA query_only`) no sirve: `abrir_version` confirma a mitad y la conexión vuelve al
   pool.
3. **El mensaje de la clave de API no cambia.** · Las rutas «solo cuenta» de lectura usan el mismo
   `MENSAJE_SOLO_CUENTA` («se edita y se guarda con una cuenta»): las pruebas de hoy lo fijan y el texto sigue siendo
   cierto para la Hoja. · Otro texto en `CuentaQueVe`.
4. **Pruebas viejas que decían 403 para quien revisa.** · Seis archivos fijaban la regla anterior en rutas que ahora son
   de lectura (`test_api_hoja.py`, `test_api_hoja_apu_retomar.py`, `test_api_hoja_conversion_cadena.py`,
   `test_api_hoja_exportar.py`, `test_api_hoja_lineas_apu.py`, y `test_api_aprobaciones.py`). Se cambiaron en el commit
   del rojo, con la decisión de Eugenio citada, y el 403 que comprobaban pasa al administrador puro, que sigue sin
   `leer_proyecto`. · —
5. **Dónde vive la prueba nueva.** · `tests/integration/test_api_hoja_lectura_revisa.py`, como pidió el encargo (el plan
   decía `tests/unit/`). · Moverla.
6. **`usePuedeEditarLaHoja` en cada componente que escribe, con la base por prop.** · Cada pestaña que escribe (Espacio,
   APU con sus factores, Presupuesto, Plan, Parámetros, Precios, Trazabilidad) y `AprobacionDeVersion` recibe `base`
   (opcional) y llama al hook; la sesión la lee siempre el hook, así que sin `editar_hoja` nada se pinta aunque falte
   la prop. Sin prop solo se pierde el `solo_lectura` de la base (las pruebas que montan una pestaña suelta, con una
   sesión de arma, no cambian). `CampoDeCelda` y `TablaEditable` no deciden: reciben `soloLectura`. · La Tarea 3 lo
   pasa a `HojaDeLaObra.puedeEditar`.
7. **«No se pinta», no «deshabilitado».** · Una celda pasa a su texto tal como lo da la API (ya en es-VE); una lista
   cerrada del espacio muestra su rótulo; la columna «Quitar» y «Acciones» desaparecen. Los textos de ayuda que hablan de
   editar («Se edita la cantidad…», «Reparta cada partida…») tampoco salen para quien no edita. · —
8. **Objetivos de mercado.** (Reemplazada por la 15.) · `GET /v1/mercado/objetivos` exige `editar_hoja`: para quien revisa daría 403 y un aviso de
   error. `useObjetivosDeMercado` gana `activo` (por omisión, verdadero) y sin permiso no pide nada ni pinta la columna.
   · Pasar la ruta a `leer_proyecto` si Eugenio quiere que quien revisa vea el objetivo.
9. **Un borrador de solo lectura en manos de quien arma.** (Lo de las acciones sobre la versión guardada lo reemplaza la
   16.) · El plan aplica la misma regla («nada de guardar, agregar ni
   enviar»): ya no hay «Guardar versión…» que abría un diálogo deshabilitado, sino la nota «Está viendo este presupuesto
   en solo lectura. Esta versión no se puede guardar: alguna partida ya no tiene composición vigente en el catálogo.»
   (`CAUSA_SOLO_LECTURA`, la misma frase del diálogo, en `logicaGuardar.ts`). La prueba de `Guardar.test.tsx` que
   comprobaba el diálogo deshabilitado cambia a esto. Restaurar, cotizar, retirar, convertir y enviar también se ocultan
   con esa base, aunque obren sobre la versión guardada: es la regla del plan. · Dejar `base` fuera de esos cinco.
10. **Pruebas de registro que cambian con la decisión.** · `shell/rutas.test.ts` (la acción de `hoja`), `pendientes/Bandeja.test.tsx` (el ejemplo de «acción que la cuenta no puede usar» pasa de la Hoja a «Actualizar precios») y
    `marco/BarraLateral.test.tsx` (quien revisa ve Resumen, Presupuesto y Aprobaciones) fijaban `editar_hoja`. · —
11. **Rojo por aserción.** · Servidor: la tabla de acceso (21 rutas, `403` donde se esperaba pasar) y la prueba nueva
    (`403 == 201`, `{versiones: 403, …} == {versiones: 200, …}`, `(403, …) == (409, …)`, `403 == 404`). Interfaz:
    `puedeEditar.ts` del rojo es un stub con la regla de hoy (todo editable), así que fallan por aserción
    (`expected true to be false`, `Unable to find role="note"`, botones de escritura presentes en «Espacio y metrajes»,
    una petición a `/v1/mercado/objetivos`, sin botón «Abrir la Hoja» en el Resumen). · —
12. **Oráculo corregido en el verde.** · `test_rita_no_envia_ni_tiene_versiones_propias` esperaba 200 en el rojo, pero
    rita está en la carpeta de la empresa y la obra vive en `vivienda.db`: pasa el acceso y responde 404. El commit del
    verde lo corrige (el 200 de quien revisa lo prueba `test_revisa_lee_las_aprobaciones_de_la_obra`). · —
13. **Prueba que ya fallaba.** · `test_api_hoja.py::test_r11_los_hallazgos_son_los_de_la_memoria[TI-001]` falla igual
    antes y después de esta tarea (sale un R12 además del R11): depende de la fecha de hoy (R12 evalúa la erosión de
    los precios de TI-001 a hoy). No es de esta tarea; queda para quien la fijó. · Fijar `_hoy` en esa prueba.
14. **Verificación.** · Servidor: `test_api_acceso_por_ruta.py`, `test_api_hoja_lectura_revisa.py`, los doce
    `test_api_hoja*.py`, `test_api_aprobaciones.py` y `test_arquitectura*.py` con `-W error`: 1558 verdes y 3 rojos en la
    primera corrida (api.json sin regenerar, el oráculo de la decisión 12 y la prueba de la decisión 13); tras
    regenerar y corregir, los dos primeros verdes (48 verdes en la nueva corrida de esos archivos). `ruff check .` limpio;
    `git diff c1f436b2 -- core/` vacío; `aplicacion/` sin tocar. Interfaz: `npx vitest run` completo, 3250 pruebas,
    verdes salvo `PlanoEnHoja` «Fusionar» (verde suelta; se cae por tiempo con la máquina cargada) y la de `Bandeja`
    de la decisión 10, ya corregida; `npm run lint` en 0. `knip` y `jscpd` siguen sin estar instalados. · —

### Ronda tras el árbitro (aprobada la tarea; Eugenio respondió las dos decisiones abiertas)

15. **Objetivo de mercado para quien revisa (Eugenio, 2026-10-31).** · Se rastreó `GET /v1/mercado/objetivos` hasta
    `aplicacion/`: `aplicacion.mercado.objetivos` hace dos `select` y `convertir_o_sin_tasa` llama a
    `tasa_del_dia.equivalencia_del_dia`, que lee `core.catalog.indices.tasa_aplicable` (un `select`); ninguna escribe
    ni confirma, y la ruta usa la sesión de lectura. La ruta pasa a `LEER_PROYECTO` (la TABLA de acceso cambia y
    `test_api_mercado.py` gana `test_los_objetivos_los_lee_quien_revisa_y_no_el_administrador`, que cuenta las filas
    de `PrecioObjetivo` antes y después). En la interfaz, `useObjetivosDeMercado` pierde el parámetro `activo`: la
    columna sale para todos. · Volver a `EDITAR_HOJA` en `api/rutas/mercado.py` y la línea de la TABLA.
16. **Acciones sobre la versión guardada (Eugenio, 2026-10-31).** · Restaurar, Registrar y Retirar una cotización,
    Convertir y Enviar a aprobación obran sobre la versión guardada, no sobre el borrador: su regla es solo el permiso.
    Precios, Trazabilidad y el «Enviar» de `AprobacionDeVersion` llaman a `usePuedeEditarLaHoja(null)` (solo la sesión;
    Precios y Trazabilidad ya no reciben `base`); Convertir pide `convertir_y_reajustar` en la sesión (además del
    `puede_convertir` que da la API), no `editar_hoja`. «Hacer una versión nueva a partir de esta» sigue con la regla
    completa: lleva a editar el borrador. Para quien revisa siguen ocultas. Pruebas: «con un borrador de solo lectura,
    las acciones sobre la versión guardada sí se ofrecen» (arma) y «tampoco ve las acciones sobre la versión guardada»
    (revisa). · Volver a pasar `base` a esas tres.
17. **Guardia `sin_escribir` más estricta (menor 1 del árbitro).** · Antes un texto que empezara por `WITH` o `PRAGMA`
    pasaba, así que `WITH x AS (SELECT 1) INSERT …` y `PRAGMA user_version = 7` escribían. Ahora una sentencia de
    SQLAlchemy pasa solo si `estado.is_select` (también un `WITH` armado con `cte()`), y un texto SQL solo si empieza por
    `SELECT` o `EXPLAIN`, o es un `PRAGMA` sin `=`; todo lo demás, también un `WITH` escrito como texto, se niega (lo más
    prudente: el camino de `abrir_version` no usa texto). Prueba propia: `tests/unit/test_sin_escribir.py` (insert
    Core, `INSERT` y `DELETE` con `text`, `WITH…INSERT`, `PRAGMA` con asignación con y sin espacios, el volcado de un
    objeto nuevo, las lecturas que pasan y la sesión que vuelve a escribir al salir). · —
18. **Menor 3.** · La decisión 1 decía «byte a byte»; la prueba compara las filas de todas las tablas (`_volcado`). · —

## Decisiones de la Tarea 3

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **El marco volvía a montar la obra en cada sección.** · `Marco.tsx` envolvía las rutas en `LimiteDeError` con `key`
   igual al `pathname`, así que cambiar de sección desmontaba `EspacioDeObra` entero: el proveedor no habría sobrevivido,
   y además se repetían `PUT /v1/sesion/proyecto` y `GET /v1/obras/resumen` (lo que la Tarea 1 prometía no se cumplía en
   el marco real; sus pruebas montan `EspacioDeObra` solo). Ahora la clave del contenido es la obra
   (`claveDelContenido`: `obra|<carpeta>|<obra>`) y `EspacioDeObra` pone su propio `LimiteDeError` (con `key` = sección)
   y su `Suspense` alrededor de la sección: un fallo de una sección se sigue reiniciando al cambiar de sección, y mientras
   llega la pantalla perezosa la cabecera queda a la vista. Prueba: `Marco.test.tsx`, «cambiar de sección dentro de la
   misma obra no vuelve a fijar la obra ni a leer su ficha». · Volver a `key={`${ubicacion.pathname}|${generacion}`}` en
   `Marco.tsx` (y el proveedor se perdería al cambiar de sección).
2. **Dónde va el proveedor.** · En `ObraDeLaRuta`, dentro del `ContextoAplicacion` de la obra (lo necesita para el
   proyecto), con `key={JSON.stringify([carpeta, obraId])}`, y envuelve la cabecera y la sección. Solo en
   `SECCIONES_CON_HOJA` y solo con `leer_proyecto` (la acción de la pantalla `hoja` y de sus lecturas desde la 2b): sin
   ella la sección dice «Sin permiso» y el proveedor solo daría 403. · `conHoja` en `marco/EspacioDeObra.tsx`.
3. **La cabecera dentro del proveedor.** · Así lee la versión abierta. Consecuencia: al cruzar entre una sección con Hoja
   y otra sin ella la cabecera se vuelve a montar y `ListaDeLaCarpeta` relee `GET /v1/carpeta` (antes de esta tarea se
   releía en cada cambio de sección). Entre las tres secciones con Hoja no se vuelve a montar. · Dejar la cabecera fuera
   y subir la versión abierta como estado de `ObraDeLaRuta`.
4. **De dónde sale «Versión abierta».** · Del borrador: `base.version` y `base.vigente`, cuando las dos existen y
   difieren; si no, la línea de la Tarea 1 («Versión: <vigente de la lista de obras>»). No se compara con `useObras`
   porque tras guardar esa lista queda vieja hasta recargarla y diría una vigente que ya no lo es. · `lineaDeVersion` en
   `marco/CabeceraDeObra.tsx`.
5. **La regla de salida.** · `shell/sucio.ts` gana un tercer parámetro, `conservaAlIrA(destino)`, y
   `formulariosSucios(destino)` deja fuera lo que sobrevive al ir allí; `confirmarSalida` recibe el `destino` (cuarto
   parámetro). El proveedor registra la pantalla `hoja` mientras hay cambios, solo dentro de una obra, con
   `quedaEnLaHoja(destino, carpeta, obra)` (`marco/secciones.ts`). Lo usan el marco (barra lateral, migas, buscador:
   `alClicAntes` e `irSeguro`) y `useNavegarSeguro` (lo usará «Abrir» de Versiones). Los demás formularios (un
   «Agregar partida» a medio llenar) siguen preguntando también entre secciones con Hoja, porque esos sí se pierden. Fuera
   de una obra (la Hoja montada sola) no se registra nada, como antes. · Quitar `conservaAlIrA` del registro en
   `ProveedorDeLaHoja.tsx`.
6. **Qué pasa con el borrador al salir.** · Sin cambios se descarta (`DELETE`), como al salir de la Hoja; con cambios se
   pregunta «Cambios sin guardar» y, si la persona sale, el borrador se conserva en el servidor y la Hoja ofrece
   retomarlo al volver (E10), como antes. Cambiar de obra o de carpeta desmonta el proveedor (su `key` y la del marco):
   es la misma salida. El texto del diálogo («Si sale de esta pantalla, se perderán.») es el que ya existía; no es del todo
   exacto porque se pueden retomar. · Pasar una `consecuencia` propia a `confirmarSalida` desde el marco.
7. **La interfaz crece un poco respecto del plan.** · `codigo` admite `undefined` (aún no se sabe: se leen las versiones o
   se espera la respuesta a la oferta de retomar); se añaden `descartando`, `falloAlDescartar`, `existente`, `exito`,
   `quitarExito` (el cuerpo los pinta) e `inerte` (hay un diálogo de la Hoja abierto: Versiones lo necesitará para su
   contenido). `versiones` toma la lista fresca de `useVersiones` y pasa un 403 o un 404 a `error`, como hacía la Hoja.
   · `HojaDeLaObra` en `ProveedorDeLaHoja.tsx`.
8. **Lo que se movió y lo que no.** · Al proveedor, sin cambiar la lógica: `useCarga` de versiones, `useOfertas`,
   `useVersiones`, `useBorrador`, retomar, `pedirVersion`, `useGuardadoDeLaPagina`, los efectos de `visibilitychange` y
   `beforeunload`, `DialogoDeGuardar`, `DialogoDeVersion` y el anfitrión de los diálogos de operaciones
   (`ContextoDeDialogos`). El orden de los hooks es el mismo, así que el de las peticiones también. En el cuerpo se quedan
   la pestaña, el filtro de Auditoría y la pestaña inicial: la Tarea 4 sube la pestaña al proveedor; hasta entonces, ir a
   Versiones y volver deja la pestaña inicial. · —
9. **`useOfertas` en su propio archivo.** · El plan lo ponía en el proveedor, que ya pasa de 250 líneas (350, con su razón
   en la cabecera). `paginas/hoja/index.tsx` baja de 610 a 433 líneas y declara su razón (el reparto de las nueve
   pestañas, que reordena la Tarea 4). · Pegarlo en `ProveedorDeLaHoja.tsx`.
10. **`PaginaHoja` monta su propio proveedor solo si no hay uno encima.** · `useContext(ContextoDeLaHoja) === null`; sin
    obra (`proyecto === null`) sigue «Elija una obra», sin proveedor. El suyo no lleva `key`: cuando la prueba cambia el
    proyecto, la lógica movida lo maneja igual que antes. · —
11. **`?version=` solo dentro de un enrutador.** · `VersionDeLaRuta` se monta si `useInRouterContext()`, porque las
    pruebas de la Hoja la montan sin enrutador. Llama al `pedirVersion` del último dibujo (por referencia, para que el
    efecto dependa solo del parámetro) y quita el parámetro con `setSearchParams(…, { replace: true })`. · —
12. **Estilos y peso del marco.** · El proveedor importa `hoja.scss`: los diálogos de guardar y de versión son suyos y
    Versiones o Archivos y planos los abrirán sin que la Hoja se haya cargado. Así el CSS de la Hoja (todas sus clases
    llevan el prefijo `silice-hoja`) y el código del proveedor van en el paquete del marco, no en el perezoso de la Hoja.
    · Cargar el proveedor de forma perezosa si el paquete del marco pesa.
13. **Pruebas.** · `ProveedorDeLaHoja.test.tsx` monta el marco entero con la Hoja real en Presupuesto. Archivos y planos y
    Versiones tienen `pagina: null` hasta las Tareas 6 y 11: la prueba simula `marco/secciones` (`vi.mock`) para darles la
    pantalla de la Hoja y pinta, según la sección de la ruta, la Hoja o una pantalla de relleno que lee el contexto con
    `useContext` (no con `useHojaDeLaObra`, que lanzaría) para que el rojo falle por lo que dice. Sus botones «Simular dos
    cambios» (llama a `aplicar`) y «Guardar desde aquí» (`abrirGuardado`) usan la interfaz del proveedor. Hay una prueba
    más que las del plan: «Guardar versión…» desde otra sección manda el `rev` al día (riesgo del 409 «El borrador
    cambió»), y otra que va al Presupuesto de otra obra (el proveedor se vuelve a montar: `DELETE` del de esta y `POST` del
    de aquella). · —
14. **Rojo por aserción (`b4e018eb`).** · Con el esbozo del contexto: 9 fallas, todas de aserción: `expected { fijadas: 2,
    fichas: 2 } to deeply equal { fijadas: 1, fichas: 1 }`; `expected 'borrador: sin hoja' to be 'borrador: listo'` (seis
    pruebas: Versiones no tenía borrador); `expected '/obra/empresa/7/presupuesto?version=001' to be
    '/obra/empresa/7/presupuesto'`; y la cabecera sin «Versión abierta: 001 (la vigente es 002)». Tres pasaban ya en rojo
    porque fijan lo que no debe cambiar: «al ir al Resumen sin cambios descarta el borrador», «en Resumen y Mercado no se
    abre ningún borrador» y «con la vigente abierta, la cabecera dice la versión como antes». · —
15. **Oráculo corregido en el verde.** · La prueba «con cambios, “Abrir la 001”…» buscaba `role="dialog"` para «Descartar
    los cambios», pero `DialogoDeVersion` es `alertdialog` (así lo prueba `Retomar.test.tsx`); en rojo no llegaba a esa
    línea. Se corrigió el rol en el commit del verde. · —
16. **Verificación.** · `npx vitest run src/paginas/hoja src/marco src/shell src/paginas/obras`: 70 archivos, 1186 de 1187
    verdes en la corrida completa; la que cayó es `PlanoEnHoja` «con una edición del espacio en la pausa, “Fusionar” no se
    puede pulsar» por tiempo (4979 ms con la máquina cargada, el mismo caso de la Tarea 2b), verde al repetirla sola (4 de
    4). `Edicion.test.tsx` pasó en la corrida completa. Además `aprobar/Aprobar`, `componer/Moneda`,
    `control/PestanaProcura`, `mercado/Mercado`, `src/paginas/pendientes` y `src/comun` (usan `sucio`, `salida` o el
    marco): 342 verdes. Las pruebas que montan `PaginaHoja` no cambiaron: el diff de pruebas desde `341ee6da` son solo
    `ProveedorDeLaHoja.test.tsx` (nueva) y una prueba añadida a `Marco.test.tsx`. `npm run lint` en 0. `knip` y `jscpd`
    siguen sin estar en este `node_modules`: no se corrieron `npm run muerto` ni `npm run duplicado`. Sin servidor tocado.
    `git diff 341ee6da -- core/ aplicacion/` vacío. · —
17. **Lo que queda para otras tareas.** · Si se cambia de carpeta con cambios en el borrador abierto, el diálogo puede
    nombrar el mismo borrador dos veces («Hoja de la obra» por el registro y «Hoja de <obra>» por `hojasConCambios`).
    Tras guardar, la cabecera no relee la ficha ni la lista de obras (`recargarFicha`, `recargarProyectos`): la Tarea 5 o
    la 6 pueden llamarlas desde `alCrearVersion`. · —

### Ronda 2 (el árbitro la devolvió por un mayor)

18. **La ficha quedaba vieja (mayor).** · Al no volver a montarse la obra por sección (decisión 1), nadie relee
    `GET /v1/obras/resumen`: tras guardar la primera versión el Resumen seguía en «sin versión» y «Te falta…», y tras
    enviar a aprobación seguía «En elaboración». Ahora:
    - `useGuardadoDeLaPagina` gana `alCrearseVersion`, que corre con cada versión creada (guardar, restaurar, cotizar,
      retirar y convertir: todas pasan por `alCrearVersion`). El proveedor le da `recargarLaObra`, que llama a
      `recargarFicha()` del `ContextoDeLaObra` (si hay obra) y a `recargarProyectos()` (la línea «Versión:» sale de la
      lista de obras).
    - `AprobacionDeVersion`, al enviar, llama a `recargarFicha()` (si hay obra; montada sola, nada).
    - Decisión del orquestador: entrar al Resumen desde otra sección vuelve a leer la ficha (ajuste durante el render en
      `ObraDeLaRuta`, que conoce la sección); mientras llega se ve la anterior (Tarea 1, decisión 3). Cubre lo que cambie
      desde Aprobaciones o Control. Montar la obra directamente en el Resumen sigue siendo una sola lectura.
    Pruebas: `Marco.test.tsx` (Resumen, Mercado, Resumen: una obra fijada y dos lecturas de la ficha);
    `ProveedorDeLaHoja.test.tsx` (moverse entre Presupuesto, Versiones y Archivos no relee; «Guardar desde aquí» relee la
    ficha y la lista de obras, y al entrar al Resumen hay otra lectura y la cabecera dice «Versión: 003»);
    `AprobacionDeVersion.test.tsx` («dentro de una obra, enviar vuelve a leer la ficha de la obra»). · Quitar
    `alCrearseVersion` del proveedor o el ajuste de `ObraDeLaRuta`.
19. **El diálogo de salida cuando solo está el borrador (menor 2).** · El tercer parámetro de `useFormularioSucio` pasa a
    ser un objeto `EnElServidor` (`conservaAlIrA`): marca un trabajo que vive en el servidor. `confirmarSalida` calcula
    `retomable` (motivo «salir», sin extras y todo lo que cuenta es `EnElServidor`; `soloTrabajoEnElServidor` en
    `shell/sucio.ts`) y `DialogoSalida` dice entonces «Sus cambios quedan guardados para retomarlos al volver.» con el
    botón «Salir» (sin «descartar»). Al cambiar de carpeta no es retomable (el servidor olvida los borradores) y sigue
    «Cambiar y descartar»; con cualquier otro formulario sucio, también el texto de antes. La prueba «al ir al Resumen con
    cambios…» cambió su oráculo en el rojo de esta ronda. · `CONSECUENCIA_RETOMABLE` en `shell/DialogoSalida.tsx`.
20. **Lo escrito en la pausa (menor 3).** · Prueba nueva: escribir una cantidad en Presupuesto, ir enseguida a Versiones
    (sale el `PUT …/cantidades` al desmontarse la pestaña y el proveedor recibe el resumen con un cambio) y luego al
    Resumen: pregunta y no hay `DELETE`. Para que pregunte, la prueba espera a que el `PUT` haya salido: si se pulsa
    Resumen antes de que el servidor conteste, el marco aún no sabe que hay cambios y no pregunta, aunque el borrador
    tampoco se descarta (`descartarSiNoQuedanCambios` espera los envíos). Ya funcionaba; en rojo cayó solo por el botón
    «Salir» de la decisión 19.
21. **Límite de error de fuera de la sección (menor 4).** · `LimiteDeError` gana `reinicio`: con `getDerivedStateFromProps`
    olvida el error antes de pintar con otro `reinicio`; sin error no vuelve a montar nada. El marco le da
    `reinicio={pathname}` al límite que envuelve las rutas (con la `key` de la obra): un fallo de la cabecera o del
    proveedor se olvida al navegar sin volver a montarlos cuando no fallaron. Prueba propia: `shell/LimiteDeError.test.tsx`
    (se olvida al cambiar, se queda con el mismo, no vuelve a montar sin error). · —
22. **Rojo de la ronda (`8bf8aa30`).** · 6 fallas, todas de aserción: `expected { fijadas: 1, fichas: 1 } to deeply equal
    { fijadas: 1, fichas: 2 }`; `expected { aviso: true, contenido: false } to deeply equal { aviso: false, contenido:
    true }`; `expected "vi.fn()" to be called 1 times, but got 0 times`; la descripción del diálogo sin «Sus cambios quedan
    guardados…»; `expected 1 to be 2` (lecturas de la ficha tras guardar); y sin botón «Salir» en el diálogo. `npm run lint`
    pasó en el rojo (`reinicio` ya estaba declarado, sin uso).
23. **Lo que cambia de la primera ronda.** · La decisión 6 queda así: con solo el borrador sucio el diálogo ya no dice «se
    perderán» (decisión 19). Lo de la decisión 17 sobre la cabecera tras guardar queda resuelto por la 18; lo del nombre
    repetido al cambiar de carpeta sigue igual. · —
24. **Verificación de la ronda.** · `npx vitest run src/paginas/hoja src/marco src/shell src/paginas/obras
    src/paginas/pendientes src/comun`: 99 archivos, 1450 de 1451 verdes; la que cayó es otra vez `PlanoEnHoja` «“Fusionar”
    no se puede pulsar» por tiempo (4918 ms), verde al repetirla sola (4 de 4). `npm run lint` en 0. Grep de los colores
    de la empresa: limpio. Sin servidor tocado; `core/` y `aplicacion/` sin cambios. · —

## Decisiones de la Tarea 4

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Orden de los commits y bajas que salen con el feat.** · El plan decía «feat primero (los bloques dejan de pintarse) y bajas después», pero eso deja código muerto entre dos commits y hace que `git revert` de una baja no devuelva la función. Se hizo al revés: rojo (`dac451ec`), bajas 7, 8, 10, 11 y 12 (cada una quita pantalla y código y arregla las pruebas que la nombraban) y al final el `feat` (`b0f976d6`). Las bajas **23** (fusionar «Punto de equilibrio» en «Plan y equilibrio») y **25** (los textos largos al catálogo, tras «¿Qué es esto?») son estructura, no borrado: salen con el `feat`. · Revertir el `feat` entero.
2. **El rojo de las bajas 10, 11 y 12 no se ve por aserción hasta el `feat`.** · Sus pruebas navegan a «Análisis de precio (APU)», «Plan y equilibrio» y «Ajustes de costo», que no existen antes del `feat`; la aserción de ausencia solo se alcanza después. Las de las bajas 7, 8, 12 (Espacio), 25 y «Ver en Revisión» sí caen por aserción. Cada baja se verificó con las pruebas viejas que la nombraban (`EdicionApu`, `Edicion3c2`, `Vistas3b3`...).
3. **Títulos en `logica.ts`, ayudas en `textos.ts`.** · El plan pedía los dos en el catálogo; los títulos ya viven en `PESTANAS` (los usan la lista de pestañas, `pestanasVisibles` y las pruebas) y duplicarlos habría dado dos fuentes. `textos.ts` solo lleva la explicación, con dos partes: `general` (cualquiera) y `alEditar` (cómo se escribe y cuándo se aplica; solo si `puedeEditar`, para que quien revisa no lea instrucciones de controles que no ve). · Mover los títulos a `textos.ts`.
4. **`AyudaDePestana` y `usePestanaDeLaHoja`, dos piezas que el plan no nombra.** · La primera evita repetir en siete pestañas el reparto `general`/`alEditar` y el nombre de la región; la segunda saca del proveedor (ya en 364 líneas) un estado con regla propia: la pestaña con que abre cada obra, la que sigue vigente si la elegida desapareció, y `espacioPedido`. · Pegarlas en `ProveedorDeLaHoja.tsx` y en cada pestaña.
5. **Las pestañas solo se pintan con el borrador abierto.** · Antes la lista se veía siempre, con paneles vacíos; ahora «Espacio y metrajes» depende de `espacio_vacio`, que llega con el borrador, y pintar la lista para quitar una pestaña después sería parpadeo. Las pruebas que buscaban una pestaña antes de que cargara esperan ahora a «Estado del borrador». · Quitar la condición `estado.estado === "listo"` en `CuerpoDeLaHoja`.
6. **«Ver en Revisión».** · Cambió el rótulo del botón de cada fila y su `aria-label` («Ver en Revisión: Fuente F1»). El contexto se sigue llamando `ContextoAuditoria` (nombre interno, no se ve).
7. **Baja 8: qué dice sin obra.** · Solo «Elija una obra»: el «selector de obra de la cabecera» ya no existe y dentro de una obra siempre hay obra. No se inventó otra instrucción.
8. **Pregunta para Eugenio: la ayuda de cómo escribir cifras (coma decimal) queda plegada.** · Antes `AYUDA_CIFRAS` estaba siempre visible junto a los campos; ahora hay que pulsar «¿Qué es esto?». El plan lo pide (baja 25), pero la regla de la coma es de Eugenio (2026-10-25) y cada campo ya da un error claro si se escribe un punto decimal. Si prefiere verla siempre, basta sacar esa frase de `alEditar` y pintarla bajo la tabla. · `textos.ts`.
9. **Menor 1 del árbitro de la Tarea 3 (la línea «Estado:» vieja).** · `PanelDictamen` llama a `recargarFicha()` tras registrar el dictamen. En Control toda escritura pasa por `cambiar` en `paginas/control/index.tsx` (línea base, parámetros, valuaciones —registrar, importar, anular—, costos, procura y elegir recuperación), así que se llama allí una sola vez y no en `PestanaLineaBase`, `PestanaValuaciones` y `PestanasDeResultados` por separado. Con una escritura rechazada no se llama. Sin obra abierta (pantalla sola) no hay ficha. Rojo `d7e56728`, fix `92106c12`. · Llamarla desde cada pestaña.
10. **Rojo (por aserción) del menor 1.** · `expected "vi.fn()" to be called 1 times, but got 0 times` en el dictamen, la línea base, la valuación y la recuperación; las dos pruebas de «escritura rechazada» pasan en rojo porque fijan lo que no debe cambiar.
11. **Pruebas viejas que cambiaron** (solo nombres de pestaña, textos plegados y servidores falsos): `AgregarPartida`, `AprobacionDeVersion`, `Edicion`, `Edicion3c2`, `EdicionApu`, `Guardar`, `Hoja`, `LineasApu`, `Retomar`, `SoloLectura`, `Versiones`, `Vistas` y `Vistas3b3` (todas en `paginas/hoja`), y fuera de la Hoja `Marco`, `Bandeja`, `ListaDeLaCarpeta`, `rutas` y `salida` (solo «Hoja de la obra» pasa a «Presupuesto»). Los servidores falsos de `Edicion3c2` y `Vistas` ahora contestan `vistas/equilibrio`, porque «Plan y equilibrio» lo pide junto con el plan. Salieron las pruebas de lo dado de baja: factores del APU (`EdicionApu`) y cuatro de «Crear plan secuencial» (`Edicion3c2`).
12. **Verificación.** · `npx vitest run src/paginas/hoja src/marco src/shell src/paginas/obras src/paginas/aprobar src/paginas/control src/comun src/paginas/pendientes`: 109 archivos, 1587 verdes (`Edicion` y `PlanoEnHoja` pasaron en la corrida completa). `npm run lint` en 0. `knip` y `jscpd` no están instalados. Colores de la empresa: limpio en cada commit. Sin servidor tocado; `core/`, `aplicacion/hoja.py`, `aplicacion/composicion.py` y `asistente/experimento` intactos.
13. **Lo que preocupa.** · (a) El punto 8 (ayuda de cifras plegada). (b) «Trazabilidad» sigue sin «¿Qué es esto?» hasta la Tarea 6. (c) «Plan y equilibrio» pide dos vistas al abrirse (`plan` y `equilibrio`). (d) La descripción del estado vacío («Agregue las partidas en «Presupuesto»…») nombra la sección, no la pestaña «Partidas».

## Decisiones de la Tarea 5

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Enviar con un borrador de solo lectura.** · El plan define `puedeEnviar` como «`puedeEditar` y la lectura no falló» y su prueba pedía la franja sin «Enviar a aprobación…» con un borrador `solo_lectura`. Eso choca con la decisión 16 de la Tarea 2b (Eugenio, 2026-10-31, posterior al texto de esta tarea): enviar obra sobre la versión **guardada** y su regla es solo el permiso. Se siguió a Eugenio: `puedeEnviar` = `editar_hoja` en la sesión (`usePuedeEditarLaHoja(null)`) y una lectura de la aprobación que no falló. Con un borrador de solo lectura quien arma ve «Envíe la versión V a aprobación» con su botón; agregar, guardar y «Hacer una versión nueva» no salen. Quien revisa no ve ninguno. · `puedeEnviar: puedeEditar && …` en `paginas/hoja/FranjaDelPresupuesto.tsx`.
2. **Dónde va la franja.** · Arriba de todo en el cuerpo de la Hoja (tras los avisos «Versión guardada» e «Instantánea»), antes de la aprobación, del estado del borrador y de las pestañas: «encima de las pestañas» se cumple y queda como en el Resumen, lo primero que se lee. · Mover `<FranjaDelPresupuesto>` en `paginas/hoja/index.tsx`.
3. **Una pieza que el plan no nombra: `FranjaDelPresupuesto.tsx`.** · La franja y la aprobación de la versión comparten la lectura (`useAprobacionDeVersion`), el diálogo de enviar (lo abre el botón de la franja) y el aviso («Se envió…», «Corrija y guarde…»). Esta pieza los junta y se monta con `key` por obra y versión, como antes `AprobacionDeVersion`. `AprobacionDeVersion` queda sin botones y sin estado propio: la etiqueta, las notas, el aviso y el diálogo de enviar, y usa `comun/aprobacion.ts` en vez de sus `NOMBRES`. El plan habla de un «diálogo de retirar»: no existía (retirar lo hace el servidor al enviar otra versión), así que no hay nada que dejar. · Pegar la franja en `index.tsx` y pasar el estado por props.
4. **El botón de la regla 1.** · «Agregar la primera partida», no «Agregar partida»: el terciario de encima de la tabla ya se llama así y dos botones con el mismo nombre en la misma pantalla no se distinguen con lector de pantalla. Abre el mismo diálogo: el cuerpo va a «Partidas» y le pasa `pedirAgregar`; la pestaña lo abre en cuanto tiene la vista y lo marca atendido (`alAtenderAgregar`), así que volver a la pestaña no lo abre otra vez. · `textoDelBoton` en `paginas/hoja/textos.ts`.
5. **El botón de la regla 3.** · «Ir a Revisión» (el plan no lo nombra; «Ver en Revisión» es el de cada fila). Lleva a la pestaña sin filtro. Solo lee, así que también sale para quien revisa y con un borrador de solo lectura. · `textoDelBoton` y `DEL_BORRADOR` en `pasoDelPresupuesto.ts`.
6. **Singular y cifras.** · «Hay 1 cambio sin guardar» y «Hay 1 hallazgo grave: revíselo antes de enviar»; el número va con `formatoEsVe`. `graves` cuenta CRITICO y ERROR de `resumen.hallazgos` (los totales que da la API; ADVERTENCIA no cuenta). · `TEXTOS_DEL_PASO` en `textos.ts`.
7. **Mientras se lee la aprobación.** · Las reglas 1 a 3 no dependen de ella y salen enseguida; las demás esperan (`necesitaLaAprobacion`), para no adelantar «Envíe…» y quitarlo un instante después en una versión aprobada. · Quitar la condición en `FranjaDelPresupuesto.tsx`.
8. **Qué es un fallo de la lectura.** · Todo error (también 403 y 404, que antes no decían nada) es «fallo»: la región dice «No se pudo leer el estado de aprobación de esta versión.» y la franja dice «Envíe…» sin botón. Sin saber el estado no se ofrece enviar: podría estar ya aprobada. Un 401 avisa además al marco. · En `useAprobacionDeVersion.ts`, devolver `listo` con `null` para 403 y 404.
9. **Con cambios sin guardar ya no se ofrece enviar.** · La regla 2 gana a la 8: el paso es guardar. Antes «Enviar a aprobación…» estaba también con cambios y el diálogo avisaba que no viajaban; esa prueba de `AprobacionDeVersion.test.tsx` cambió a «la franja pide guardar antes». El aviso del diálogo se queda (no se alcanza desde la franja; es defensivo y deja volver atrás sin tocar el diálogo). · Cambiar el orden de las reglas en `pasoDelPresupuesto.ts`.
10. **Guardar.** · El botón de la franja conserva el id `hoja-guardar-version` (a él vuelve el foco al cancelar el diálogo, `useGuardadoDeLaPagina`); el de enviar es `hoja-enviar-a-aprobacion`. Un borrador en blanco **sin** cambios ya no ofrece «Guardar primera versión…»: la regla 1 pide antes la primera partida. «Descartar cambios» (fantasma) se queda en el estado del borrador con el total. · `IDS` en `FranjaDelPresupuesto.tsx`; la condición en `EstadoDelBorrador`.
11. **«Hacer una versión nueva».** · Es el botón de la franja (antes «Hacer una versión nueva a partir de esta», dentro de la aprobación); lleva a «Partidas» y deja el aviso «Corrija y guarde: será una versión nueva.» en la región de la aprobación, como antes.
12. **Filas afectadas.** · `TablaDensa` y `TablaPaginada` ganan `claseDeFila` (opcional; solo lo usa Partidas). `silice-fila--afectada` pinta `--silice-aviso-fondo` también en la celda fija de la izquierda; INFO no afecta. La severidad sigue en palabra en el Estado y con contraste forzado el fondo se va y la palabra queda. Las tablas del Espacio no se tocaron: el plan habla del renglón del presupuesto. · `esFilaAfectada` en `pasoDelPresupuesto.ts`.
13. **Menor de la Tarea 4 (decisión 8): la ayuda de las cifras.** · `AYUDA_CIFRAS` sale de `alEditar` y `AyudaDePestana` la pinta a la vista, bajo «¿Qué es esto?», en las pestañas con cifras que se escriben (Espacio, Partidas, APU, Plan y Ajustes: campo `cifras` del catálogo), solo con `puedeEditar`. La nota de los vértices (x,y,z con punto) sigue plegada. Pruebas en `Pestanas.test.tsx`. · `cifras: false` en `textos.ts`.
14. **Arnés corregido en el verde.** · `Franja.test.tsx` monta la Hoja dentro de un `MemoryRouter`: el diálogo «Agregar partida» usa `useNavigate` (como en `AgregarPartida.test.tsx`). En rojo la prueba no llegaba a abrirlo.
15. **Rojo por aserción (`93727d1c`).** · `pasoDelPresupuesto.ts` del rojo era un esbozo con los tipos: `expected null to deeply equal { tipo: 'falta', …(2) }`, `expected 0 to be 3`; en la Hoja, `Unable to find role="region" and name "Siguiente paso"`, `expected <button id="_r_bi_-enviar" …> to be null` (versión distinta de la vigente), la fila sin `silice-fila--afectada` y la ayuda de cifras sin hallar a la vista. Pasaban ya en rojo, porque fijan lo que no debe cambiar: las reglas 6 y 7 (`null`), «Agregar partida» terciario, aprobada sin franja, en aprobación sin principal, la lectura que no adelanta «Envíe…», la que falla sin enviar y que quien revisa no ve la ayuda de cifras.
16. **Pruebas viejas que cambiaron.** · Dos de `AprobacionDeVersion.test.tsx`: la de los cambios sin guardar (punto 9) y la de la devuelta (el botón está en la franja y se llama «Hacer una versión nueva»). Ninguna otra.
17. **Herramientas.** · `knip` y `jscpd` siguen sin estar en este `node_modules`: no se corrieron `npm run muerto` ni `npm run duplicado`.
18. **Verificación.** · Rojo `93727d1c`, verde `31fa941a`. `npx vitest run src/paginas/hoja src/marco src/shell src/paginas/obras src/paginas/aprobar`: 78 archivos, 1339 verdes. Una corrida anterior, más amplia (además `src/comun` y `src/paginas/pendientes`, con la máquina cargada), dio 1616 de 1618: cayeron `PlanoEnHoja` «“Fusionar” no se puede pulsar» (el caso de tiempo conocido) y `Retomar` «lee el borrador vivo…», que falló en 396 ms; las dos pasan solas (`Retomar`, 3 de 3). `npm run lint` (eslint y tsc) en 0. Colores de la empresa: limpio en cada commit. `core/`, `aplicacion/` y `asistente/` sin tocar; sin servidor.
19. **Lo que preocupa.** · (a) El punto 1 contradice la letra del plan a favor de la decisión de Eugenio; conviene que el árbitro lo confirme. (b) El punto 9: quien quería enviar una versión guardada teniendo cambios a medias ya no puede sin guardarlos o descartarlos. (c) `Retomar` cayó una vez bajo carga sin ser un tiempo agotado; no se repitió. (d) Un 403 o un 404 de las aprobaciones ahora se dice («No se pudo leer…»), punto 8.

### Ronda 2 (el árbitro la devolvió por un mayor)

20. **El orden de las reglas 3 a 7 no estaba fijado (mayor).** · Cada caso de esas reglas partía de «guardada» y de la vigente abierta, así que seis mutantes que cambian el orden (la 3 tras la 4, la 5 o la 6; la 7 antes de la 3, la 4 o la 5) pasaban las 29 pruebas. `pasoDelPresupuesto.test.ts` gana «precedencia de las reglas 3 a 7»: graves con devuelta, en aprobación y aprobada (gana la 3), graves con otra versión abierta (gana la 3), devuelta y en aprobación con otra versión abierta (ganan la 4 y la 5), cada una con su resultado exacto escrito a mano. El código ya cumplía: no hubo rojo ni fix. Los seis mutantes, aplicados en una copia del scratchpad, ahora caen (1, 2, 3, 3, 2 y 1 pruebas, en ese orden); p. ej. la 3 tras la 4 da `expected { tipo: 'falta', …(2) } to deeply equal …` con `"accion": "version_nueva"` en lugar de `"ver_revision"`. · —
21. **Foco 3 y la letra de la Tarea 5 (menor 1).** · El Foco 3 (más arriba, «Con un borrador `solo_lectura`, el criterio es el mismo: nada de guardar, agregar ni enviar») y la regla de `puedeEnviar` de la Tarea 5 quedan matizados por la decisión 16 de la Tarea 2b (Eugenio, 2026-10-31): con un borrador de solo lectura, quien tiene `editar_hoja` sí envía, porque enviar obra sobre la versión guardada; agregar, guardar y hacer una versión nueva siguen fuera. Quien revisa no envía nunca. Es lo que hace el código desde `31fa941a` (punto 1). · Volver a `puedeEnviar: puedeEditar && …` en `FranjaDelPresupuesto.tsx` si Eugenio cambia la decisión 16.

## Decisiones de la Tarea 5b

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Dónde se calcula el IVA.** · La vista sale de `aplicacion/hoja_vista.vista_presupuesto` (no de `aplicacion/hoja.py`), pero la dataclass `VistaPresupuesto` es de `aplicacion/` y no se tocó: el IVA se suma en la capa de la API, en `vista_presupuesto_a_respuesta` (`api/esquemas_hoja.py`), con `aplicacion.impuestos.con_iva` y la misma `impuestos_a_respuesta` de `GET /presupuestos/{codigo}`. Como esa función sirve a `GET …/vistas/presupuesto` y a la respuesta de editar cantidades (`PUT …/cantidades`), las dos traen `impuestos`, y la pantalla no queda vieja tras una edición. · Mover el cálculo a un módulo de `aplicacion/` si el experimento se descongela.
2. **Sobre qué cifra.** · Sobre el total exacto (`Monto.exacto`), no sobre el texto de dos decimales: 0,034 de total da IVA 0,01, y sobre el texto (0,03) saldría 0,00. Una prueba lo fija. · —
3. **La alícuota viaja como fracción.** · El plan decía `alicuota` «16»; la forma que ya usan `GET /presupuestos/{codigo}` y `GET /v1/control/valuaciones` es `"0.16"` (`ImpuestosRespuesta`), y se siguió esa para no tener dos formas. La pantalla la pasa a «16 %» con `porcentajeDeAlicuota` (de `paginas/control/logica.ts`, importada: es una sola función, no se duplicó). · Cambiar `ImpuestosRespuesta` afectaría también a Presupuestos y a Control.
4. **`impuestos` siempre presente.** · El campo es obligatorio en el esquema (con total 0,00 da 0,00 · 0,00 · 0,00); «sin partidas, no se pinta» lo decide la pantalla por `filas.length`. Cambia `docs/api.json` (regenerado). · Hacerlo `null` sin partidas en `vista_presupuesto_a_respuesta`.
5. **Dónde se ve y qué lleva.** · Una sección «IVA del presupuesto» debajo de «Total del presupuesto» (`IvaDelPresupuesto.tsx`), con tres líneas («Subtotal», «IVA (16 %)», «Total con IVA»; la última en el cuerpo del total). La fuente de la alícuota va en el **único** «¿Qué es esto?» de «Partidas» (`AyudaDePestana` gana `extra`; `parrafosDeAyudaDelIva`): «Alícuota: 16 %. Fuente: …». Primero se hizo un segundo «¿Qué es esto?» dentro de la sección, pero rompía 6 pruebas viejas que buscan «el» botón y dos botones con el mismo nombre no se distinguen con lector de pantalla; la prueba roja de la fuente cambió de sitio en el verde (de la región «IVA» a la región «Partidas»). Las cifras van con `formatoEsVe` y la moneda de la obra, sin el «valor exacto» de `Cifra` (el servidor ya las manda a dos decimales). · Hacer un segundo botón en `IvaDelPresupuesto.tsx` y arreglar las pruebas de `Pestanas` y `Edicion3c2`.
6. **Solo en «Partidas».** · El total del presupuesto se pinta en esa pestaña; el IVA va debajo de él. El total de la barra de estado del borrador no lleva IVA. · —
7. **Fixtures.** · `vistaPresupuesto()` de `datosDePrueba.ts` gana `impuestos` (2.703,86 → 432,62 → 3.136,48, a mano); `AgregarPartida.test.tsx` y `ObjetivoDeMercado.test.tsx` arman la vista a mano y llevan un `impuestos` mínimo con IVA 0,00 solo para el tipo: no lo leen. · —
8. **Lo que preocupa.** · (a) La fuente del IVA queda en la ayuda de toda la pestaña, arriba, lejos de la cifra. (b) La alícuota y su fuente son las de la T18 (16 %, «a cotejar con la Gaceta vigente»); no se cotejó con la Gaceta.

## Decisiones de la Tarea 6

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Orden de los commits.** · Rojo de la interfaz (`2ea4050a`) y del servidor (`fc3b46c7`), el verde del servidor (`ff5c3c91`), las bajas (24 en `fbc4a812`, 9 en `e699e27b`), el traslado con `git mv` (`26cbce77`, que además corrige las importaciones relativas de los archivos movidos y quita sus tres rutas de la prueba estática de `hoja/Versiones.test.tsx`; ronda 2, punto 23) y la sección (`a98d98b9`), como pidió el orquestador y como la Tarea 4. El plan decía «feat primero» y un solo commit «baja 9 y 24»: van en dos para que cada una se deshaga sola. Entre `e699e27b` y `a98d98b9` el Presupuesto no tiene selector ni Trazabilidad y Versiones aún es un esbozo; cada commit compila. Cómo volver de cada baja: tabla «Tarea 6» de la bitácora. · —
2. **Dónde quedaron los archivos movidos.** · La baja 24 solo desmonta la pestaña; `PestanaTrazabilidad`, `EstadoDeLaCadena`, `RestaurarVersion` y `RastroDeAprobaciones` se quedan sin montar hasta `26cbce77`, que los mueve con `git mv` (`PestanaTrazabilidad` pasa a `versiones/RegistroDeCambios.tsx`; `RastroDeAprobaciones` y su prueba `TrazabilidadAprobaciones.test.tsx`, a `aprobar/`) para que el historial los siga; el `feat` los adapta. · —
3. **«Se rompió en la versión X» sin leer el texto del servidor.** · La cadena solo decía la versión rota dentro de `mensaje`. `GET /v1/hoja/cadena` gana `rota_en` (el código de `resultado.fallo` de `core.budget.cadena`, que no se toca; `null` si está íntegra): `EstadoDeLaCadena` de `aplicacion/entrega.py` lo lleva con `None` por omisión (sus otros usos no cambian) y `CadenaHojaRespuesta` lo publica; `docs/api.json` regenerado. Seis pruebas de `test_api_hoja_conversion_cadena.py` que comparaban el JSON entero lo incluyen. Si una respuesta rota no lo trae, el aviso dice «Se rompió la cadena de sellos». · Leer la versión del `mensaje` en la interfaz (frágil) o quitar el campo.
4. **Qué versiones lista la tabla.** · Todas (ronda 2, punto 20): el historial solo crece (RF-54). La descartada lleva la palabra «descartada» junto al código, tiene «Ver cambios» y, con permiso, «Restaurar…», pero no «Abrir», salvo que todas lo estén: `FilaDeVersion` gana `seAbre`, que sale de `versionesOfrecidas` (la regla del proveedor), porque con una descartada «Abrir» la pediría y el proveedor abriría `por_omision` sin decir nada. · Volver a `versionesOfrecidas(v.versiones)` en `filasDeVersiones` (esconde las descartadas: lo que el árbitro devolvió).
5. **Una octava columna, «Acciones».** · Las siete del plan llevan datos; «Abrir», «Ver cambios» y «Restaurar…» van en una columna propia (botones fantasma `sm`, con un nombre accesible que dice la versión: «Abrir VIV-001», «Ver cambios de VIV-001», «Restaurar VIV-001…»). · —
6. **«Restaurar…» en cada fila.** · Es el diálogo de hoy con la versión de la fila ya elegida (el selector del diálogo sigue). Se ofrece también en la vigente, como antes (el diálogo las ofrecía todas). Su regla es solo el permiso (decisión 16 de la Tarea 2b): con un borrador de solo lectura quien arma restaura. Con cambios sin guardar no sale en ninguna fila y una sola línea dice «Guarde o descarte los cambios pendientes antes de restaurar otra versión.» (antes era un aviso en la pestaña). · Ocultarlo en la fila vigente: condición en `TablaDeVersiones` (`paginas/versiones/index.tsx`).
7. **Adónde vuelve el foco tras abrir o guardar una versión.** · Volvía al selector «Versión», que salió con la baja 9. Ahora va al h1 de la sección que comparte el borrador (`ID_DEL_TITULO`, `hoja-titulo`, en Presupuesto y en Versiones), también tras «Seguir editando» y cuando el botón de guardar ya no está. · Otro destino en `useGuardadoDeLaPagina.ts`.
8. **Cómo cambian de versión las pruebas de la Hoja.** · Por la ruta, como «Abrir»: `paginas/hoja/rutaDePrueba.tsx` (solo lo importan las pruebas) envuelve la Hoja en un enrutador de memoria (`conEnrutador`), pide `?version=` (`pedirVersionPorLaRuta`) y lee la versión abierta en el estado del borrador (`versionAbierta`). Cambiaron `Hoja`, `Guardar`, `Retomar`, `AprobacionDeVersion` y `Versiones` (de la Hoja); el inerte se mira en la región «Estado del borrador». · —
9. **El rastro de la obra en Aprobaciones.** · Se pinta debajo del envío solo dentro de una obra (hay `ContextoDeLaObra`) y con `leer_proyecto`, para el proyecto de la sesión (la obra abierta), no el del envío que se mira. Fuera de una obra (`#/aprobar` viejo) no sale: así la búsqueda sin `?envio=` sigue sin pedir el rastro a quien no edita (su prueba no cambió). El h2 pasa de «Aprobaciones» a «Rastro de la obra» y sus estilos van a `aprobar.scss`. · La condición `enLaObra` en `paginas/aprobar/index.tsx`.
10. **La franja.** · Las dos reglas son «Siguiente paso» (orientan; ninguna es una precaución). Los textos son los del Presupuesto (`TEXTOS_DEL_PASO`); el botón, «Guardar versión…» («Guardar primera versión…» con el borrador en blanco), sale solo con `puedeEditar` y con el id `hoja-guardar-version`, al que vuelve el foco al cancelar. Los cambios ganan a la vigente en aprobación. · `pasoDeVersiones` en `paginas/versiones/logica.ts`.
11. **Si no se leen las aprobaciones.** · La columna queda vacía, la tabla entera se pinta y debajo una línea de ayuda (no una alerta) dice «No se pudo leer el estado de aprobación de las versiones.». La lectura la comparte `useEstadosDeAprobacion` con `useAprobacionDeVersion` (`useLecturaDeAprobaciones`, en el mismo archivo): no hay una segunda forma de pedirla. · Quitar la línea en `index.tsx`.
12. **El aviso de la cadena.** · Sin h2 propio: es la región «Cadena de sellos» con el título corto y su ícono, el texto del servidor y, si la hay, la declaración de las selladas. Sus estilos pasan de `hoja.scss` a `versiones.scss`. · —
13. **Lo que la sección pinta además.** · El aviso «Versión guardada» del proveedor (tras guardar o restaurar desde aquí) y, sin proveedor (una dirección vieja fuera de una obra), «Elija una obra». Con un diálogo de la Hoja abierto la sección entera, panel incluido, queda inerte. El panel del registro es el ancho (40 rem) y Esc devuelve el foco a «Ver cambios de V». · —
14. **Pruebas que no tuvieron rojo.** · `comun/PanelLateral.test.tsx` ya cubría lo que el plan pide (Tarea 7). Pasaban en rojo, porque fijan lo que no debe cambiar: en Aprobar «sin `leer_proyecto` no se ve ni se pide» y en la lógica «sin cambios y sin la vigente en aprobación no hay paso». Se mudaron en el `feat`, sin rojo, la de la cadena con otra forma y la estática (sin `Number` ni `parseFloat`) de los archivos movidos. · —
15. **Rojo por aserción (`2ea4050a`, `fc3b46c7`).** · Con esbozos de `versiones/logica.ts` (devuelve `[]` y `null`) y de `versiones/index.tsx` (solo el h1): 31 fallas de 92, todas de aserción, p. ej. `expected [] to deeply equal [ { codigo: 'VIV-002', …(8) }, …(1) ]`, `Unable to find role="table" and name "Versiones de la obra"`, `Unable to find role="region" and name "Cadena de sellos"`, `Unable to find role="heading" and name "Rastro de la obra"`, `expected <select id="hoja-version" …(2)>…(1)</select> to be null` (baja 9), `expected <button …(7)>…(1)</button> to be null` (baja 24) y `expected null to be 'versiones'`. Servidor: `assert {'integra': F...racion': None} == {'integra': F...ta_en': '002'}` (seis pruebas). · —
16. **Pruebas viejas que cambiaron.** · Por la baja 24: `Hoja` (siete pestañas), `logica`, `Pestanas`, `SoloLectura` (sin «Trazabilidad»; Restaurar sale de la lista de acciones sobre la versión guardada), `Vistas3b3` (salen sus siete pruebas de Trazabilidad; las del registro se mudaron a `versiones/Versiones.test.tsx`) y `hoja/Versiones` (salen restaurar, la cadena y la fila de Trazabilidad del 3e-3). Por la baja 9: la decisión 8. Por la sección: `marco/BarraLateral` (una sección más en el árbol), `busqueda` (el orden se mira sin el módulo vial, porque la obra y sus secciones ya llenaban los ocho resultados; «Versiones» se encuentra en cada obra), `oferta`, `secciones`, `shell/rutas` (33 pantallas) y `ProveedorDeLaHoja` (Versiones recibe también la pantalla de relleno). · —
17. **Herramientas.** · `knip` y `jscpd` siguen sin estar en este `node_modules`: no se corrieron `npm run muerto` ni `npm run duplicado`; la medida de las bajas está en la bitácora. · —
18. **Verificación.** · `npx vitest run src/paginas/hoja src/marco src/shell src/comun src/paginas/obras src/paginas/aprobar src/paginas/versiones`: 112 archivos, 1593 de 1594 verdes; cayó por tiempo (20 s, con la máquina cargada) `Edicion` «topes: “Agregar fila” se cierra en el tope…» (mil filas), verde suelta; `Edicion` entero ya había pasado solo. `npm run lint` (eslint y `tsc -b --noEmit`) en 0. Servidor, con `-W error`: `test_api_hoja_conversion_cadena.py`, `test_entrega.py`, `test_api_hoja_lectura_revisa.py`, `test_api_acceso_por_ruta.py`, `test_openapi.py` y `test_aplicacion_hoja_versiones.py` verdes; `ruff check .` limpio; `docs/api.json` reproducible (`test_openapi`). Colores de la empresa: limpio en cada commit. `core/`, `aplicacion/hoja.py`, `aplicacion/composicion.py` y `asistente/experimento` intactos. · —
19. **Lo que preocupa.** · (a) «Abrir» con cambios sin guardar lleva al Presupuesto y allí pregunta «Descartar los cambios»; con «Seguir editando» la persona queda en Presupuesto, no vuelve a Versiones. (b) Con una oferta de retomar pendiente, Versiones no abre borrador y ninguna fila sale «abierta» hasta resolverla en Presupuesto. (c) Un 403 o un 404 de las aprobaciones también deja la columna vacía con la línea de ayuda. (d) El ancho de la tabla de ocho columnas junto al panel de 40 rem a 1366 px se mide en el navegador en la Tarea 14. · —

### Ronda 2 (el árbitro la devolvió por un mayor)

20. **Las descartadas no se veían en ninguna parte (mayor).** · `filasDeVersiones` usaba `versionesOfrecidas` y escondía las descartadas (la decisión 4 de la primera ronda), pero la pestaña «Trazabilidad» de la baja 24 las listaba todas y su «Restaurar» las ofrecía todas: el historial solo crece (RF-54). Se perdían tres cosas: (a) la descartada no se veía, aunque el aviso de descartar (`paginas/actualizacion/logica.ts`) dice que «sigue guardada como documento y su historial de cambios se conserva»; (b) no se podía restaurar desde la interfaz, que es la única manera de deshacer un descarte (el servidor sí lo permite); (c) con la cadena rota en una descartada, «Se rompió en la versión X» nombraba una X que no estaba en la tabla. Ahora `filasDeVersiones` devuelve todo el historial; la fila descartada dice «VIV-000 (descartada)» (palabra, con el gris de `--cds-text-secondary` solo de acompañante), no tiene «Abrir» salvo que todas lo estén (`seAbre`), sí «Ver cambios» y, solo con permiso, «Restaurar…»; los `codigos` del diálogo de restaurar son los de todas las filas. · `filasDeVersiones` en `paginas/versiones/logica.ts` y la columna de acciones de `TablaDeVersiones` en `paginas/versiones/index.tsx`.
21. **Rojo de la ronda (`9b23a168`).** · 7 fallas, todas de aserción. Lógica: `expected [ { codigo: 'VIV-002', …(8) }, …(1) ] to deeply equal [ { codigo: 'VIV-002', …(9) }, …(2) ]` (falta la descartada y `seAbre`) y la misma forma en «combina el estado» y «si todas están descartadas». Pantalla: `expected [ 'VIV-002 (abierta)', 'VIV-001' ] to deeply equal [ Array(3) ]` y, en restaurar, la cadena rota en VIV-000 y quien revisa, `expected [ 'VIV-002 (abierta)', 'VIV-001' ] to include 'VIV-000 (descartada)'`. `npm run lint` pasó en el rojo. Las pruebas nuevas: en `logica.test.ts`, la descartada aparece con `descartada: true` y `seAbre: false` y, si todas lo están, todas con `seAbre: true`; en `Versiones.test.tsx`, la fila descartada sin «Abrir VIV-000» y con «Ver cambios de VIV-000» (abre su registro) y «Restaurar VIV-000…»; el diálogo ofrece VIV-002, VIV-001 y VIV-000 y manda `version: "VIV-000"`; la cadena rota en VIV-000 con VIV-000 en la tabla; y quien revisa ve la descartada y su «Ver cambios», sin «Restaurar…» ni «Abrir». · —
22. **Lo que cambia de la primera ronda.** · La decisión 4 queda como arriba. `FilaDeVersion` gana un campo (`seAbre`) frente a la firma de la sección «Interfaces» de la Tarea 6. La prueba vieja «las descartadas no se ofrecen» de `logica.test.ts` se reemplazó por las dos de la ronda; las de `pasoDeVersiones` solo ganan `seAbre: true` en sus filas armadas a mano. · Quitar `seAbre` y decidir «Abrir» en la tabla con `versionesOfrecidas`.
23. **La frase de la decisión 1.** · Decía que `26cbce77` movía «sin tocar el contenido»; sí lo toca: corrige las importaciones relativas de `EstadoDeLaCadena`, `RegistroDeCambios` (antes `PestanaTrazabilidad`) y `RestaurarVersion` y de la prueba del rastro (`RastroDeAprobaciones.tsx` pasó sin cambios), y quita sus rutas de la prueba estática de `hoja/Versiones.test.tsx`. Corregida arriba. · —
24. **Verificación de la ronda.** · Arreglo en `aad7c670`. `npx vitest run src/paginas/versiones src/paginas/hoja src/paginas/aprobar src/marco src/shell`: 80 archivos, 1361 de 1361 verdes (`src/paginas/versiones` sola: 35 de 35). `npm run lint` (eslint y `tsc -b --noEmit`) en 0, también en el rojo. Sin servidor tocado; `core/` y `aplicacion/` sin cambios; sin navegador. · —

## Decisiones de la Tarea 7

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **`PanelLateral` llega antes que la Tarea 6.** · La Tarea 7 lo consume y la 6 aún no está hecha, así que se creó aquí `comun/PanelLateral.tsx` (con su `.scss` y `PanelLateral.test.tsx`) con la firma exacta de la Tarea 6: `aside` con `aria-labelledby` hacia su h2, 24 rem o 40 rem (`ancho`), foco al h2 al abrirse, Esc o «Cerrar» lo cierran y el foco vuelve al disparador; por debajo del umbral de cada letra pasa por encima (`position: fixed` bajo la barra, `inline-size: min(24rem | 40rem, 100%)` y `max-inline-size: 100%`). El contenedor común es `silice-con-panel` (`minmax(0, 1fr) auto`). La Tarea 6 lo usa tal cual y solo añade lo suyo. · Si la Tarea 6 lo necesita distinto, se cambia en `comun/PanelLateral.tsx`; sus pruebas fijan lo que el plan pide.
2. **El disparador del foco.** · Se recuerda al abrir **y** al cambiar de título con el panel abierto (otra fila lo abrió), salvo que el foco ya estuviera dentro del panel: así Esc devuelve el foco a la última fila que lo abrió, no a la primera. Si el disparador ya no está en la página (se cambió de pestaña), no se mueve el foco. · Los dos efectos de `PanelLateral.tsx`.
3. **Esc dentro del panel.** · Cierra solo si la tecla nació dentro del panel en el DOM (un diálogo abierto desde el panel se pinta en el anfitrión del proveedor y su Esc no debe cerrar el panel) y si ningún control la usó ya (`defaultPrevented`): en un campo de cantidad Esc devuelve el valor aceptado (`CampoDeCelda`), como en la pestaña. Para cerrar desde un campo: Tab fuera y Esc, o «Cerrar». · `alTeclear` en `PanelLateral.tsx`.
4. **Dónde vive `partidaElegida`.** · En `usePestanaDeLaHoja` (se esparce en `HojaDeLaObra` como la pestaña), no escrito dentro de `ProveedorDeLaHoja`: es estado de navegación del Presupuesto, como la pestaña, y así el proveedor no cambia mientras la Tarea 5 trabaja en paralelo. Va con su obra: la elegida en otra obra no vale (la Hoja montada sola cambia de obra sin volver a montarse). · Mover el `useState` al proveedor.
5. **Abierto o cerrado no se recuerda.** · Que el panel esté abierto es estado de `PestanaPresupuesto`: al ir a otra pestaña se cierra (la pestaña se desmonta, y lo escrito que esperaba la pausa sale al desmontarse, como siempre), y al volver a «Partidas» no se abre solo. La partida sigue elegida: la pestaña APU la muestra. · Subir `enPanel` al proveedor.
6. **Solo los renglones con precio abren su APU.** · `GET …/vistas/apu?partida=X` con una X que no está entre las partidas valoradas devuelve, sin avisar, el APU de la primera de la lista (`aplicacion/hoja_vista.vista_apu`), así que una fila «Pendiente» habría abierto el APU de otra partida. Esas filas dejan el código como texto. Además `EditorDeApu` comprueba que el detalle sea el de la partida pedida y, si no, dice «X no tiene análisis de precio en este presupuesto.» en vez de editar otro. El botón sale también para quien revisa (es lectura). · La condición `f.pu_texto === ""` de la columna «Partida» en `PestanaPresupuesto.tsx`.
7. **El título del panel sale de la fila.** · «APU de E-01 · <descripción del renglón> · m³» (la unidad con `unidadEscrita`, como la tabla), que es lo que la persona acaba de pulsar; la descripción del APU puede ser más larga. Dentro del panel el editor no repite su h2 (`conTitulo={false}`). · Construir el título con `detalle.descripcion` en `PanelDeApu.tsx`.
8. **El editor en dos capas.** · `EditorDeApu({ borrador, partida, alAceptar, alAusente })` es la firma del plan: lee el APU de esa partida y lo usa el panel. Por dentro pinta `EditorDelDetalle`, que recibe el detalle ya leído y es lo que usa la pestaña APU, porque su vista trae la lista y la partida en una sola lectura (con la firma del plan la pestaña habría pedido el APU dos veces y cambiado el número de lecturas que fijan sus pruebas). `alRecargarBorrador` y `alReabrir` salen del proveedor (`refrescar`, `reabrirNuevo`, los mismos que les da `index.tsx`). `TablaDelRubro` pasó a su archivo; `EditorDeApu.tsx` queda en 364 líneas con su razón en la cabecera. · —
9. **Editar en el panel relee la tabla.** · Cada edición aceptada en el panel pasa el resumen a la página (`aplicar`) y vuelve a leer la vista del presupuesto, para que el precio, el total del renglón y «Total del presupuesto» no queden viejos: una lectura más por edición. · Quitar `alRelectura` de `alAceptarDelApu` en `PestanaPresupuesto.tsx`.
10. **Cambios en archivos de la Tarea 5 (en paralelo).** · `PestanaPresupuesto.tsx`: dos imports, un campo de `PropsContenido`, un parámetro de `EditorDePresupuesto`, la celda de «Partida» y la función exportada `PestanaPresupuesto` (envuelve la vista y el panel en `silice-con-panel`); `ContenidoPresupuesto` no se tocó. `hoja.scss`: un bloque `.silice-hoja__apu-en-panel` justo después de `.silice-hoja__apu-centro`, no al final. `index.tsx`, `AprobacionDeVersion.tsx` y `EstadoDeFila.tsx` sin tocar. · —
11. **Rojo por aserción (`c64ffc55`).** · Con un esbozo de `PanelLateral` que no pinta y un `.scss` vacío: 18 fallas, todas de aserción, p. ej. `AssertionError: el código de E-01 es el botón «Abrir el APU de E-01»: expected null not to be null` (las ocho de `ApuEnPanel`), `el panel «APU de E-01»: expected null not to be null`, `el botón «Cerrar»: expected null not to be null` y `la regla de muy-grande por debajo de 1919.98px: expected '' to match /position:\s*fixed/`. Pasaba en rojo solo «cerrado no pinta nada» (fija lo que no debe cambiar). En el verde se cambió una sola cosa de las pruebas, sin tocar oráculos: en `ApuEnPanel.test.tsx` la ruta del `.scss` va en una variable (con el literal, Vite reescribe el `new URL` como recurso: `TypeError: The URL must be of scheme file`), como ya hace `componer/estilosComponer.test.ts`. · —
12. **Verificación.** · `npx vitest run src/paginas/hoja src/marco src/shell src/comun`: 104 archivos, 1456 de 1457 verdes; la que cayó es otra vez `PlanoEnHoja` «“Fusionar” no se puede pulsar» por tiempo (4144 ms), verde al repetirla sola. Las pruebas de la pestaña APU (`EdicionApu`, `LineasApu`) y el código sin partir (`Edicion`) pasan sin cambios. `npm run lint` (eslint y `tsc -b --noEmit`) en 0. `knip` y `jscpd` siguen sin estar en este `node_modules`. Colores de la empresa: limpio en cada commit. `core/`, `aplicacion/hoja.py`, `aplicacion/composicion.py` y `asistente/experimento` intactos; sin servidor tocado.
13. **Lo que preocupa.** · (a) El ancho real del panel de 40 rem junto a la tabla a 1366 px con letra normal (no pasa por encima: el umbral normal es 1056 px) deja unos 40 rem a la tabla, que se desplaza en su caja; se mide en la Tarea 14. (b) Por debajo del umbral el panel fijo tapa la tabla entera; se cierra con «Cerrar» o Esc. (c) Desde un campo de cantidad Esc no cierra (devuelve el valor): es coherente con la pestaña, pero hay que salir del campo primero. (d) La unión con la Tarea 5: ver la decisión 10.

## Decisiones de la Tarea 8

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Firma de `LineaDelApu`.** · El plan la da con `borrador: BorradorAbierto` y `alAceptar: (r: Resumen)`. Se conservaron las props de hoy (`id`, `moneda`, `anfitrion`, `revActual`, `alAusente`, `alReleer`) porque el editor del detalle no tiene el borrador entero (la pestaña APU le pasa `id` y `moneda`) y el anfitrión, el `rev` y la relectura salen de su motor de edición; `alAceptar` recibe `{ resumen, grupo, descripcion, cantidad }` (lo que ya recibía `alAgregada`), porque agregar necesita resembrar la cantidad de la línea nueva. Se añaden `modo` y `alCerrar` (antes `alCancelar`). · Cambiar las props en `LineaDelApu.tsx` y su uso en `EditorDeApu.tsx`.
2. **`LineaApu`.** · El plan nombra el tipo sin definirlo: es el que ya usaba «Quitar» (`grupo`, `indice`, `descripcion`, `boton`), pasado a `logicaApu.ts`; `PorQuitar` desaparece. · —
3. **Foco al cerrar.** · `useDialogoDeOperacion` solo recuerda un botón (el de «Agregar línea»). En modo cambiar el foco vuelve al «Cambiar» de la línea con `useFocoAlCerrar` (el mismo camino que «Quitar»), tanto con Esc o «Cancelar» como tras aceptar. · `alCerrarElDialogo` y `alAceptada` en `EditorDeApu.tsx`.
4. **Qué pide el modo cambiar.** · Solo el insumo, con el mismo buscador de agregar pero sin «Insumo nuevo»: el servidor exige que el insumo esté en la lista de precios de la versión. Al elegir se ve su precio de lista. Sin elegir, el error dice «Elija un insumo de la lista de precios de la versión.» Se pierde la lista corta de hasta 300 candidatos de antes: el buscador pide 2 letras como mínimo y muestra 8 por grupo con «Ver más resultados». · Pasar `valorPropio` en modo cambiar, o bajar `minimoDeLetras`.
5. **Errores del cambio.** · Antes un 422 o un 409 del cambio salían en el aviso del APU (sin la frase «La hoja sigue con el último APU válido»); ahora salen dentro del diálogo, que sigue abierto con la elección, como los de agregar. Un 409 por `rev` viejo relee el borrador y dice «puede cambiar el insumo otra vez». · `aceptar` en `LineaDelApu.tsx`.
6. **Dos botones por línea.** · «Cambiar» y «Quitar» son dos columnas (ghost `sm`), con `aria-label` «Cambiar el insumo de <línea>, <rubro> fila <n>». Salen en el mismo caso que «Quitar»: con permiso y en una versión guardada. · Una sola columna «Acciones» en `TablaDelRubro.tsx`.
7. **Pruebas que cambiaron.** · `EdicionApu`: el bloque de cambio de insumo se reescribió para abrirlo con «Cambiar» de la línea; salieron las pruebas del tipo y la línea elegibles, del rubro sin líneas (ahora: no hay «Cambiar») y la de más de 300 candidatos (la cubre `CampoConBusqueda`). `LineasApu`: el diálogo se llama «Agregar una línea». `SoloLectura`: la lista de controles que escriben pide «Cambiar el insumo de». `ApuEnPanel`: una prueba más con el cambio en el panel. En el commit del rojo una aserción de «sin coincidencias» buscaba un texto que el buscador no pinta; se corrigió en el `refactor` (no cambió ningún oráculo de cifras).
8. **Archivos de otras tareas.** · No se tocó ninguno de los de la Tarea 5. Queda sin uso la clase `.silice-hoja__insumo-cuerpo` de `hoja.scss`; no se quitó para no chocar con la unión. · Borrarla al unir.
9. **250 líneas.** · `LineaDelApu.tsx` queda en 399 (razón en su cabecera: un formulario con dos modos que comparten estado, errores y foco) y `EditorDeApu.tsx` en 388 (razón ya escrita). `ConfirmarQuitarLinea` salió a su archivo. · —
10. **Verificación.** · Rojo (`f6ffced4`, 6 fallas de aserción en `LineaDelApu` y 30 más en las pruebas adaptadas, p. ej. `Unable to find an accessible element with the role "dialog" and name "Agregar una línea"` y `AssertionError: ./LineaDelApu.tsx: expected [ './AgregarLineaApu.tsx', … ] to include './LineaDelApu.tsx'`). Verde (`4ca6b4d0`): `npx vitest run src/paginas/hoja src/comun`, 69 archivos, 965 verdes; `npm run lint` en 0; `knip` y `jscpd` no están instalados (se buscó con `grep` que nada nombre `CambioDeInsumo`, `AgregarLineaApu` ni `PorQuitar`). Colores de la empresa: limpio en cada commit. `core/`, `aplicacion/hoja.py`, `aplicacion/composicion.py` y `asistente/experimento` intactos.
11. **Lo que preocupa.** · (a) El punto 4: quien cambiaba un insumo recorriendo una lista corta ahora debe escribir al menos dos letras. (b) El panel de 24 rem con dos botones más por fila de APU hace la tabla más ancha: se mide en la Tarea 14. (c) La unión con la Tarea 5 (`hoja.scss`).


## Decisiones de la Tarea 9

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Orden de los commits.** · Rojo (`ea8bb0e6`), traslado de la lógica de «Partidas similares» con `git mv` (`f1ddce51`: `similares/logica.ts` y su prueba pasan a `hoja/logicaParecidas.ts` y `hoja/logicaParecidas.test.ts`; solo se corrigen importaciones), baja 20 (`91a15420`), baja 21 (`80e7e754`) y la puerta única (`436a339b`), como las Tareas 4 y 6. Entre las bajas y el `feat` el diálogo no ofrece parecidas y «Componer una partida nueva» todavía navega a `/componer` (sin «Volver»); cada commit compila y pasa `npm run lint`. Cómo volver de cada baja: tabla «Tarea 9» de la bitácora. · —
2. **Dónde se escribe lo que se busca por parecido.** · En el mismo campo «Partida» (con sugerencias), no en un segundo campo de texto libre: quien no encuentra la partida por código escribe cómo se describe y pulsa «Buscar parecidas» (terciario, debajo del campo, deshabilitado en blanco). La ayuda lo dice y el «¿No la encuentra?» de la lista nombra las dos salidas. · Un campo propio dentro de `Parecidas.tsx`.
3. **Qué entregan «Usar esta partida» y el guardado de Componer.** · El plan firmaba `alUsar(codigo)` y `alGuardar(codigo)`; entregan `{codigo, descripcion, unidad}` (`PartidaParecida`, `PartidaCompuesta`). Así el campo «Partida» dice «código · descripción», como al elegir del catálogo, y la cantidad dice su unidad («Cantidad (m3)»): guía a quien no es experto (pedido de Eugenio del 2026-10-21). La prueba del plan «el campo Partida dice «Z-99»» quedó «Z-99 · Zanja ficticia»; una parecida sin desglose no trae unidad y la cantidad no la dice. · Volver a `(codigo: string)` en las dos firmas.
4. **Dónde se pinta el panel de Componer y qué pasa con el diálogo.** · En la capa del diálogo (su anfitrión), no junto a la tabla: con el diálogo abierto la página está inerte, y el diálogo tiene que seguir para volver con la partida. Mientras se compone, el diálogo queda montado pero oculto (`hidden`, con `.silice-hoja__dialogo[hidden] { display: none }` porque su `display: grid` le ganaría): una tarea a la vista y un solo botón principal («Guardar composición»). El fondo pasa a `--con-panel` (panel a la derecha, a todo el alto) y baja de z-index 9000 a 8400, para que «Precios distintos a los de la lista» (`MarcoDeDialogo`, 8500), que se abre desde el panel, quede encima; «Cambios sin guardar» (9000) y las listas de los buscadores (9100) siguen arriba. Una prueba de estructura lo fija. · Dejar el diálogo visible e inerte a la izquierda (`silice-con-panel` en el fondo), con dos principales a la vista.
5. **Pregunta para Eugenio: cerrar el panel descarta lo compuesto sin preguntar.** · Esc o «Cerrar» cierran el panel y lo escrito en Componer se pierde, como cerrar el diálogo pierde lo escrito en él; lo escrito en el diálogo (cantidad, cálculo, nota) sigue, y el foco vuelve a «Partida». «Componer una partida nueva» ya no pregunta «Cambios sin guardar» (no se sale de la obra); la prueba vieja de «Quedarme» se reemplazó. · Pedir confirmación en `cerrarComponer` (`AgregarPartida.tsx`) si `formulariosSucios()` incluye `componer`.
6. **Pregunta para Eugenio: el código al componer.** · El panel abre con el código elegido y el campo sigue editable (el plan dice `codigoInicial`); el campo «Código» de Componer (pantalla y panel) gana la ayuda «Con este código la partida queda en el catálogo de la empresa, por ejemplo «E-411» o uno propio. Si ya existe, se cargan sus tablas.». No se volvió un buscador guiado: las aserciones de `componer/index.test.tsx` se conservan y la pantalla se muda a Precios y catálogo en F5. Queda abierto: si en «Partida» se escribe una descripción («excavación de zanja»), la opción sigue diciendo «Componer una partida nueva con el código «excavación de zanja»». Propuesta para F5: con espacios, abrir el panel con esa descripción y el código vacío. · `valorPropio` en `AgregarPartida.tsx` y `CampoTexto id="componer-codigo"` en `ComponerPartida.tsx`.
7. **`nivelDelTitulo`.** · Es el nivel del título que encabeza la composición; sus bloques van uno por debajo: h2 en la pantalla (bajo su h1) y h3 en el panel (bajo su h2), con las tablas de insumos en h3 o h4. `Guardar`, `PanelDesglose`, `Similares` y `TablaInsumos` ganan `nivel` opcional con su valor de antes por omisión. El `alCerrar` opcional del plan no se añadió: el panel ya tiene «Cerrar» y nadie lo usaría. · —
8. **Piezas y tamaños.** · `ComponerPartida.tsx` (494 líneas, razón en su cabecera: es el cuerpo entero de la pantalla de antes, con sus cinco lecturas en vivo y el guardado en dos pasos) y `index.tsx` queda en 18; `AgregarPartida.tsx` pasa de 341 a 371 (razón añadida: junta los diálogos de agregar y quitar y el foco que comparten). Una pieza que el plan no nombra, `ComponerEnPanel.tsx` (28 líneas: el panel, el aviso `role="note"` con el fondo de precaución y la composición), para no engordar el diálogo. `ComponerPartida` entra en el paquete de la Hoja por importación directa (no `React.lazy`). · `React.lazy` en `ComponerEnPanel.tsx` si el paquete pesa.
9. **Cómo se ven las parecidas.** · Dentro del diálogo, bajo «Partida»: el título «N propuestas, de mayor a menor similitud» (h3), una lista «Partidas parecidas» con el puntaje, el código y la descripción de cada una, «Usar esta partida» (terciario; nombre accesible «Usar esta partida: FIC-01») y su análisis plegado («Ver el análisis de FIC-01»), con las tablas en es-VE. Se quitaron los h3 de cada tabla de la pantalla vieja (las tablas llevan su nombre) y el esqueleto de página («Buscando partidas parecidas…» en una línea). `AYUDA` de `logicaParecidas.ts` cambió de texto y `AVISO_SIN_DESCRIPCION` salió (sin uso). Elegir una parecida lleva el foco a «Cantidad». · `Parecidas.tsx`.
10. **Rojo por aserción (`ea8bb0e6`).** · Con esbozos de `Parecidas` y `ComponerPartida` que no pintan nada: 27 fallas, todas de aserción, p. ej. `Unable to find an accessible element with the role "button" and name "Buscar parecidas"`, `Unable to find role="complementary" and name "Componer una partida"`, `Unable to find a label with the text of: Código`, `expected { id: 'similares', …(5) } to be undefined`, `expected [ { …(3) } ] to deeply equal []` (el buscador aún ofrecía «Partidas similares»), `expected document not to contain element, found <button …>` («Volver a la Hoja») y `expected '.silice-hoja {…' to match /\.silice-hoja__dialogo\[hidden\]…/`. Pasaba ya en rojo «cuenta que revisa: no hay puerta» (fija lo que no debe cambiar). Una era un oráculo errado: el modo entrega no pasa de 30 a 29, porque «Partidas similares» era de Investigación y ya no se veía en entrega; se corrigió en el commit de la baja 20. En el verde cambiaron dos selectores, no oráculos: la lista de parecidas cuenta solo sus hijos directos (el acordeón de cada propuesta es otra lista) y «un solo botón principal» se mira en la capa del diálogo (detrás, en la página inerte, sigue el de la franja). · —
11. **Pruebas viejas que cambiaron.** · `AgregarPartida.test.tsx`: salen las dos de la navegación a `/componer?codigo=OBRA-99&volver=hoja` (una de ellas con «Quedarme»), sustituidas por las del panel; la ubicación se pinta fuera de las rutas. `Moneda.test.tsx`: la de `?volver=hoja` ahora dice que no hay «Volver a la Hoja», y se fue la ruta ficticia de la Hoja que solo usaba ella. `shell/rutas.test.ts` (32 pantallas) y `marco/busqueda.test.ts` (no ofrece «Partidas similares»). Las de `componer/index.test.tsx` no cambiaron. · —
12. **Menor fuera de lo mío, sin tocar.** · `instalador/navegador.py` (la prueba de humo de la CI, que solo mira que nada salga de 127.0.0.1) sigue cargando `#/similares`, que ahora redirige a Pendientes: la prueba sigue valiendo, pero carga una pantalla menos. Cambiarla toca `tests/unit/test_humo_piezas.py`. · Cambiar `#/similares` por otra pantalla en los dos archivos.
13. **Verificación.** · `npx vitest run src/paginas/hoja src/paginas/versiones src/marco src/shell src/comun src/paginas/componer`: 123 archivos, 1658 de 1658 verdes; `src/paginas/sinJergaInterna.test.ts` y `mercado/sinCalculo.test.ts` verdes. `npm run lint` (eslint y `tsc -b --noEmit`) en 0 en cada commit. Sin servidor tocado (sin pytest ni `api.json`: las rutas no cambian). Colores de la empresa: limpio en cada commit. `core/`, `aplicacion/hoja.py`, `aplicacion/composicion.py` y `asistente/experimento` intactos; sin navegador. · —
14. **Lo que preocupa.** · (a) El panel ancho de 40 rem con la composición entera (tres tablas de insumos de cinco o seis columnas) es estrecho: las tablas se desplazan en su caja; se mide en la Tarea 14. (b) El punto 5: lo compuesto se pierde al cerrar el panel. (c) El z-index 8400 del fondo con panel depende de que `MarcoDeDialogo` siga en 8500. (d) La línea B (Tarea 12) quitará Elaborar: el «Siguiente paso: Elaborar un presupuesto» de `Guardar.tsx` sigue y habrá que decidir qué dice en la pantalla `componer`; en el panel no se ve (se cierra al guardar). (e) El punto 6 sigue abierto. · —
15. **Ronda 2: el foco queda dentro del panel de Componer (WCAG 2.4.3).** · El árbitro devolvió la tarea: mientras se compone, el diálogo está `hidden` (su trampa de foco ya no recibe teclas), `PanelLateral` no atrapa el foco (y así sigue, porque en las Tareas 6 y 7 no es modal) y el velo del fondo tapa la página, de modo que Tab o Mayús+Tab desde «Cerrar» llevaban a controles tapados. `ComponerEnPanel` envuelve el panel en un contenedor `display: contents` (no cambia la maquetación) con `useAtraparFoco`: Tab y Mayús+Tab circulan solo dentro del panel; Mayús+Tab desde el título (foco inicial, fuera del orden de tabulación) va al último. `enfocables` se exporta de `useAtraparFoco.ts` sin cambiar su comportamiento. «Precios distintos a los de la lista» (8500, con su Esc) sigue encima: sus teclas llegan al contenedor por el árbol de React, pero el foco no es el primero ni el último del panel y la trampa no actúa. Dos pruebas nuevas en `AgregarPartida.test.tsx` (Tab/Mayús+Tab desde «Cerrar»; Mayús+Tab desde el título); caen al quitar la trampa (comprobado). Pendiente menor: quitar `focoPendiente.current = ID_PARTIDA` de `cerrarComponer` no hace caer ninguna prueba en jsdom, porque `PanelLateral` ya devuelve el foco al disparador (el mismo campo «Partida») al cerrarse y ambos caminos dan el mismo resultado observable; la línea cubre el navegador, donde el campo estaba oculto. · Quitar el contenedor de `ComponerEnPanel`.

## Decisiones de la Tarea 10

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **«En la misma transacción» sin tocar `aplicacion/hoja.py`.** · `hoja.guardar_version` y `hoja.crear_primera_version` confirman por su cuenta (`sesion.commit()`), así que `hoja_guardado.guardar` no puede insertar después sin abrir otra transacción. `importaciones.con_la_version(sesion, vivo)` engancha un `before_commit` a la sesión mientras dura la llamada: antes de confirmar vacía la sesión, toma el `id` de la versión nueva (el mayor `presupuesto.id` de la obra por encima del que había antes) e inserta las filas. Si el insert falla, falla el `commit` y las dos funciones deshacen todo (prueba `test_si_guardar_falla_no_queda_ninguna_fila`). · Quitar el `with` en `aplicacion/hoja_guardado.py` y llamar a `registrar_al_guardar` después de guardar (dos transacciones: una caída entre ambas dejaría la versión sin registro).
2. **Quién figura como «usuario».** · El mismo texto que ya usa el responsable de la versión (`activa.usuario`, p. ej. «Ana <ana>»), no el login suelto. `fusionar` gana `usuario` (con `""` por omisión para no romper a quien lo llama sin ruta) y la ruta del plano se lo pasa. · `api/rutas/hoja_plano.py` y `aplicacion/hoja_plano.fusionar`.
3. **Qué dice el resumen.** · Plano: «33 filas en el espacio» con las filas importadas de la fusión y «; N sin reconocer» solo si hay (el ejemplo del plan siempre lo mostraba). Cómputo: «18 partidas llevadas»; el «1 pendiente» del ejemplo del plan no existe en el llevar (todo o nada: no hay partidas pendientes), así que no se escribe. Singular y plural correctos («1 fila», «1 partida llevada»). · `resumen_de_plano` y `resumen_de_computo` en `aplicacion/importaciones.py`.
4. **Llevar sin `archivo`.** · No se registra nada (el campo es opcional para no romper a Elaborar, que aún no lo manda; la Tarea 12 lo manda). Con `archivo`, solo se anota si entraron todas las partidas. · `archivo=None` por omisión en `elaboracion.llevar_a_la_hoja`; exigirlo en `LlevarALaHoja`.
5. **Qué es un nombre sin ruta.** · De 1 a 255 caracteres, sin `/`, `\`, `:` ni caracteres de control, y no solo `.` o `..` ni en blanco. Un 422 sin eco con el texto de forma de siempre (no repite lo enviado). El plano toma el nombre con que el servidor lo guardó (`ruta.name`, ya sin ruta); si no fuera presentable se anota «plano». · `nombre_de_archivo` en `aplicacion/importaciones.py`.
6. **Borradores que salen en el registro.** · Los vivos de mi ficha, de esa obra, en el caso de ahora y aún sin guardar. Con la clave de API no hay ficha, así que ve solo las guardadas. Leer no crea la tabla (una base sin migrar lista solo lo sin guardar). · `listar_importaciones` en `api/rutas/hoja.py`.
7. **Hora.** · La del servidor, sin zona (como el resto de fechas y horas de la base), y en la respuesta a segundos (`2026-10-31T14:05:09`). Las filas se ordenan por la hora completa. · `fecha_hora` en `api/esquemas_hoja.py`.
8. **Tabla y migración.** · `caso_0020_hoja_importaciones` cuelga de `caso_0019_vial_tramos`, la única cabeza al escribirla; si la línea vial renumera, se renumera al integrar (pregunta 14). `version_id` es el `id` del presupuesto sin clave foránea (patrón de `tablas_vial`). Solo inserción. · Renumerar el archivo y su `revision`/`down_revision`.
9. **Lo que preocupa.** · (a) `git diff 51d3ceb4..HEAD -- core/` no está vacío: dos archivos (`core/budget/equilibrio.py`, `core/verification/precios.py`, cuatro líneas) vienen de antes de esta tarea; no se tocó nada de `core/`. (b) Un guardado que confirma dos veces (no ocurre hoy) escribiría el registro solo en el primer `commit` que ve una versión nueva. (c) El registro de un borrador se pierde si la API se reinicia, igual que el borrador (D-2).

## Decisiones de la Tarea 11

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Tres commits de código en vez de dos.** · Primero un `refactor` que solo mueve con `git mv` (`d8ca1a07`: `ImportarPlano`, `logicaPlano`, `datosDePlano`, `useImportacion`, `plano.scss` y sus cuatro pruebas a `paginas/archivos/`, cambiando solo rutas de importación); luego el rojo (`4b3e4a04`), un segundo rojo con tres oráculos de estructura que el primero no vio (`2e712862`) y el `feat` (`bcb0cae1`). Así el `feat` muestra el cambio y no la mudanza. · —
2. **Una sola zona de soltar, en el diálogo.** · `SubirArchivo` tiene la zona de soltar y elige el flujo por la extensión (`flujoDelArchivo`); `ImportarPlano` ya no tiene la suya ni el botón plegable «Importar plano (DXF o IFC)»: recibe el archivo elegido (`archivo`) y conserva «Leer plano». Cerrar el diálogo no descarta nada: la importación vive en el servidor y se ve al volver a abrirlo. · Volver a poner `SubidaArchivo` dentro de `ImportarPlano`.
3. **`.csv` antes de la Tarea 12.** · La pantalla no acepta `.csv` (no hay pantallas «pronto»): `SubirArchivo` gana `cuerpoDelComputo?: (archivo) => ReactNode` y solo con él acepta `.csv` y le pasa el archivo. La prueba le da un cuerpo «Pronto: cargar cómputo (…)»; la Tarea 12 le pasa `CargarComputo`. · La prop en `SubirArchivo.tsx`.
4. **Un solo principal a la vista con el diálogo abierto.** · El diálogo es modal (el contenido de la sección queda `inert`), pero el botón de detrás se sigue viendo bajo el velo; para que la regla se cumpla contando todos los `.cds--btn--primary` del documento, mientras el diálogo está abierto el «Subir plano o cómputo» de la sección pasa a `secondary`, y el de la franja también (`FranjaDelPaso` gana `accion.enSegundoPlano`). Dentro, «Leer plano» es principal solo si no hay una importación que seguir (o fue rechazada); con la unidad pendiente lo es «Continuar con esta unidad» y con la importación lista, «Fusionar». · Contar solo lo que no está `inert` y dejar los botones de detrás como estaban.
5. **Con franja, el botón es el de la franja.** · Con la franja «Te falta: subir el plano o describir el espacio» (espacio pedido y vacío), su acción es «Subir plano o cómputo» y el botón suelto de la sección no se pinta: dos botones que abren lo mismo serían ruido. · Pintar los dos (el suelto como secundario).
6. **El diálogo no se cierra con algo en vuelo.** · `ImportarPlano` avisa con `alOcuparse` mientras hay una petición en vuelo (desde «Fusionar», hasta que termina la relectura del borrador); entonces «Cerrar» está deshabilitado y Esc no cierra. Antes `alOcuparse` solo bloqueaba las tablas del espacio al fusionar (`useImportacion` pierde esa opción y el parámetro `bloqueaElEspacio`). · `ocupado` en `SubirArchivo.tsx`.
7. **Lo que se quitó con el traslado.** · El plano y las tablas del espacio ya no están nunca en la misma pantalla, así que salieron `ocupadoPorEdicion`, el `fieldset` que deshabilitaba las tablas mientras se fusionaba (ahora un `div` con `.silice-hoja__tablas-espacio`, en `hoja.scss`), `ROTULO_IMPORTAR`, `ETIQUETA_DE_SUBIDA` y las citas a `ui/paginas/hoja.py` (hallazgo 7). Pruebas retiradas por eso: «con una edición del espacio en curso no se fusiona» (`ImportarPlano.test`) y las dos de la pausa en `PlanoEnHoja.test` («Fusionar» no se pulsa con una edición en vuelo; las tablas no se editan mientras se fusiona). · `git revert bcb0cae1`.
8. **Pruebas que cambiaron solo de montaje.** · `ImportarPlano.test.tsx` monta `SubirArchivo` (en `document.body`) en vez de `ImportarPlano`; se conservan todas las aserciones del flujo (unidad, alturas, circuitos, fusionar, descartar, informe, errores, foco). Cambiaron de forma: «plegado al montar» y «el título del bloque es un h2» pasan a «al abrirse no pide nada: diálogo modal con su h2 y el foco adentro»; las cuatro que miraban `aria-expanded` del bloque miran ahora si está el informe; «abrir el bloque no mueve el foco» pasa a «Esc o «Cerrar» cierran»; «al fusionar avisa a la página que ocupa el espacio» pasa a «el diálogo no se cierra hasta que la relectura termina». Se añadieron «un solo botón principal en cada paso» (4) y «el flujo se elige por la extensión» (3). `PlanoEnHoja.test.tsx` monta Archivos y planos y la Hoja bajo un mismo proveedor y conserva la de «tras fusionar, el total y las tablas son los nuevos». · —
9. **El título del panel.** · «Informe de la importación de <archivo>», no solo «Informe de la importación»: así el panel se vuelve a anunciar (el foco va a su h2) al elegir otra fila. Muestra Tipo, Fecha y hora, Quién, Qué produjo y Versión, y la frase «Es el resumen que guardó el registro. El informe detallado se ve al importar el archivo.». Se elige la importación misma (no su lugar), así que la relectura tras fusionar no cambia lo que muestra el panel. · `TEXTOS.informe` en `paginas/archivos/textos.ts`.
10. **«Edificación» apagada.** · La pantalla `archivos` es del módulo `edificacion` (`shell/rutas.ts`): `ofertaDe` la quita del árbol y del buscador y el marco la corta por enlace directo, como a las demás. **Pregunta para Eugenio:** la Tarea 12 lleva «Cargar cómputo» (un `.csv`, también de obras civiles y viales) a esta sección; con «edificación» apagada esa entrada se pierde. · Quitar `modulo` de la entrada y, en la pantalla, no ofrecer el plano con el módulo apagado.
11. **El Resumen y los módulos apagados.** · `pantallaVisible` ya aceptaba los apagados, pero el Resumen no se los pasaba: ahora la franja no ofrece el botón hacia una pantalla de un módulo apagado (prueba con «Tramos» y vial apagado). · `paginas/obras/index.tsx`.
12. **Quién ve cada cosa.** · Quien revisa (o un borrador de solo lectura) ve el registro y el panel: ni «Subir plano o cómputo», ni la franja, ni «Describir el espacio a mano», ni el enlace de la pestaña Espacio. Con borradores sin guardar que esperan decisión, la sección no ofrece subir: dice que se retomen o descarten en Presupuesto (con el enlace), sin repetir aquí la oferta de retomar (que lleva un botón principal por borrador). Si el borrador deja de estar, el diálogo se cierra y la sección ofrece «Abrir de nuevo». · `EstadoDelBorrador` en `paginas/archivos/index.tsx`.
13. **Los enlaces piden un enrutador.** · El enlace de la pestaña Espacio y los de Archivos y planos solo se pintan dentro de una obra **y** de un enrutador (`useInRouterContext`): `AprobacionDeVersion.test` monta la Hoja con obra y sin enrutador, y un `Link` suelto rompía. · —
14. **Pruebas fuera de la sección que cambiaron con ella.** · `secciones`, `BarraLateral` (siete secciones, quien revisa ve Archivos y planos, el recorrido con flechas, los niveles), `busqueda` (la de orden se mide con edificación apagada: con el tope de ocho resultados la sección nueva dejaba fuera las entradas de Empresa; y ya no dice que «archivos» no se encuentra), `useObraDeLaRuta` (la sección sin pantalla es ahora `versiones`), `oferta` (edificación apagada quita Archivos y planos y nada más), `rutas` (33 y 30 pantallas, `archivos` de edificación), `SoloLectura` (Espacio ya no tiene el bloque), `ProveedorDeLaHoja` (`ligeras` da su relleno también a `archivos`) y `Resumen`. Dos ajustes de forma en el rojo para que fallara por aserción y no por `TypeError`: `campoDeArchivo` comprueba que el campo exista y `rutas.test` usa `?.`. · —
15. **Archivos de la línea A.** · `paginas/hoja/index.tsx` y `PestanaPresupuesto.tsx` no se tocaron. Sí: `ProveedorDeLaHoja.test.tsx` (una línea, `ligeras`), `hoja.scss` (un bloque tras `.silice-hoja__editable`), `PestanaEspacio.tsx` y `comun/FranjaDelPaso.tsx` (una prop opcional). La cabecera de `ProveedorDeLaHoja.test.tsx` sigue diciendo que Archivos y planos aún no tiene pantalla; se deja para no chocar con la Tarea 6. · Corregirla al unir.
16. **Rojo por aserción.** · `4b3e4a04`, con esbozos de `index`, `logica` y `SubirArchivo`: 103 fallas, todas de aserción, p. ej. `AssertionError: el campo de archivo del diálogo: expected null not to be null` (las del flujo del plano, que montan el diálogo), `Unable to find role="button" and name "Subir plano o cómputo"`, `expected [] to deeply equal [ { id: 'importacion-0', …(6) }, …(1) ]`, `expected undefined to be 'edificacion'`, `expected [ … ] to have a length of 33 but got 32` y, en el Resumen, el botón «Ver los tramos» presente con vial apagado (`expected <button …> to be null`). `2e712862`: tres oráculos de estructura (`BarraLateral`, `busqueda`, `rutas`) que el primer rojo no cambió; al correr el código del verde con los oráculos viejos dieron 7 fallas de aserción (`expected [ 'Resumen', 'Presupuesto', …(5) ] to deeply equal [ …(4) ]`, `expected -1 to be greater than 7`, el registro con 33 en vez de 32). Los oráculos nuevos no se corrieron aparte contra el código sin el `feat` (habría que cambiar de árbol, y eso está prohibido): los de `BarraLateral` y `rutas` fallan allí porque nombran «Archivos y planos», que sin el `feat` no está en el registro ni en el árbol; el de `busqueda` (con edificación apagada) pasa también sin el `feat`: fija lo que no cambia. · —
17. **Verificación.** · `npx vitest run src/paginas/hoja src/paginas/obras src/paginas/archivos src/paginas/pendientes src/marco src/shell src/comun src/paginas/sinJergaInterna.test.ts` tras el `feat`: 113 archivos, 1592 de 1593 verdes; la que cayó es `Edicion` «topes: «Agregar fila» se cierra en el tope…» por tiempo (20 s con la máquina cargada), verde al repetirla sola (y `Edicion.test.tsx` entero, 32 de 32). En la corrida anterior al arreglo de la decisión 13 cayeron además `AprobacionDeVersion` «dentro de una obra, enviar vuelve a leer la ficha» (el `Link` sin enrutador; arreglado) y la misma de `Edicion`. `PlanoEnHoja` y `Retomar` pasaron en la corrida completa. `npm run lint` (eslint y `tsc -b --noEmit`) en 0. `knip` y `jscpd` no están instalados: no se corrieron `npm run muerto` ni `npm run duplicado` (se buscó con `grep` que nada nombre lo quitado). Sin servidor tocado (`git diff 67971de1..HEAD -- core/ aplicacion/ api/ asistente/` vacío), así que ni pytest ni ruff ni `api.json`. Colores de la empresa: limpio en cada commit. · —
18. **Lo que preocupa.** · (a) La decisión 10: con «edificación» apagada, el cómputo de la Tarea 12 se quedaría sin sitio. (b) La decisión 4: que el botón de detrás cambie a secundario mientras el diálogo está abierto se ve bajo el velo; se mide en la Tarea 14. (c) El diálogo de 64 rem con el informe de 48 líneas a 1366×768 con letra «Muy grande»: se desplaza por dentro, pero se mide en la Tarea 14. (d) Una edición del espacio que aún va en vuelo al llegar a Archivos y planos puede hacer que la primera lectura del plano dé 409 por `rev` viejo; el flujo ya lo trata («Recargar el borrador»). (e) La unión con la línea A en `ProveedorDeLaHoja.test.tsx`, `hoja.scss` y `FranjaDelPaso.tsx`.

## Decisiones de la Tarea 12

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **«Edificación» apagada. Pregunta para Eugenio** (decisión del orquestador sobre la decisión 10 de la Tarea 11; reversible). · «Archivos y planos» deja de ser del módulo «edificación»: la entrada `archivos` de `shell/rutas.ts` ya no declara `modulo`, así que la sección se ofrece siempre, en el árbol y en el buscador. Con edificación apagada solo cambia lo de dentro: la puerta se llama «Cargar cómputo» (botón y diálogo), la subida acepta solo `.csv` («Suelte aquí el cómputo .csv, o haga clic para elegirlo»), no hay flujo del plano ni franja del espacio ni «Describir el espacio a mano», y ningún texto del diálogo dice «plano». Es la regla de la T19 del plan vial: edificación apaga los planos y el espacio, no los cómputos. El Resumen no cambió: ningún paso del servidor apunta a `archivos` ni a `elaborar` (`aplicacion/mesa.py`), y su franja ya no ofrecía pantallas de un módulo apagado (Tarea 11, decisión 11). El nombre de la sección y su ayuda en el árbol siguen hablando de planos; **¿quiere otro nombre con edificación apagada (por ejemplo «Archivos»)?** · Volver atrás: poner otra vez `modulo: "edificacion"` en la entrada `archivos` de `shell/rutas.ts` y devolver los oráculos de `rutas.test.ts`, `oferta.test.ts`, `busqueda.test.ts` y `Archivos.test.tsx` (`git show e5aeeb71^:<ruta>` los tiene); `conPlano` en `paginas/archivos/index.tsx` puede quedarse.
2. **Orden y número de commits.** · Mudanza (`0aea6490`, solo `git mv` de `tipos.ts` y de `logica.ts`, ahora `logicaComputo.ts`, con su prueba), rojo (`e5aeeb71`), bajas (`969ad67f`, más `7cf1358f` con tres aserciones de Componer que miraban el enlace a Elaborar y se escaparon del primero) y `feat` (`416a151d`), como pidió el orquestador (bajas antes del `feat`). Las siete bajas van en un commit, como dice el paso 5 del plan: son piezas de una sola pantalla que se va entera (como las 1 a 6 de la Tarea 2). · `git revert 7cf1358f 969ad67f` devuelve la pantalla Elaborar (sus importaciones ya apuntan a `paginas/archivos/`); las bajas sueltas, con `git checkout 969ad67f^ -- <rutas>`.
3. **Qué se movió y qué se reescribió.** · Con `git mv` se movieron `tipos.ts` y `logica.ts` (ahora `logicaComputo.ts`, con `logicaComputo.test.ts`). Los tres bloques que se quedan («Códigos de partida (civil)», «Rendimientos por declarar» y «Pendientes») vivían dentro del `index.tsx` de 632 líneas de Elaborar, junto con lo que se daba de baja: moverlo entero para borrar tres cuartas partes habría escondido la baja. Se reescribieron en `paginas/archivos/BloquesDelComputo.tsx` con el mismo comportamiento; el original está en `0aea6490:frontend-desktop/src/paginas/elaborar/index.tsx`. · —
4. **`cuerpoDeValoracion` sin `seleccion`.** · La interfaz del plan la traía, pero los códigos civiles viajan a `POST /computos/civil` (la extracción), no a `POST /presupuestos/calcular`, así que no entran en el cuerpo. El código del presupuesto y `proyecto` son el código de la obra que usa el proveedor (`useHojaDeLaObra().proyecto`, el mismo número que `useObraAbierta().obraId`; esta última lanza fuera de la obra y Archivos y planos también se monta sola). La moneda es la de la carpeta y la fecha la de su lista (`listaParaValorar`). · `cuerpoDeValoracion` en `paginas/archivos/logicaComputo.ts`.
5. **«Llevar al presupuesto», un solo paso.** · Valora y, si no hay nada que resolver, lleva. Con rendimientos por declarar muestra el bloque y no lleva nada: «Registrar el rendimiento» lo declara con la fecha de la lista y lo quita del bloque, pero **no lleva solo**: la persona vuelve a pulsar «Llevar al presupuesto» (escribir en el borrador pide un acto explícito). Con pendientes muestra sus propuestas: «Aplicar la propuesta» cambia el código del ítem en pantalla y lo quita del bloque, y «Llevar al presupuesto» vuelve a valorar; «Llevar sin los pendientes» (secundario) lleva el resto, como hacía Elaborar («los pendientes no se llevan»), y no sale si ningún otro ítem se puede llevar. · Para que siga solo tras registrar o aplicar, llamar a `llevar()` al final de `registrar` y `aplicar` en `CargarComputo.tsx`.
6. **Los códigos civiles van antes de «Extraer cómputo».** · El plan los nombra después de la tabla, pero `POST /computos/civil` los necesita para extraer (como en Elaborar). · —
7. **La franja de la lista vive en el diálogo.** · «Te falta: la carpeta no tiene lista de precios para armar» sale dentro de «Cargar cómputo», sin botón, porque `GET /v1/carpeta` solo se lee al cargar un cómputo y solo importa para llevar; extraer se sigue pudiendo. Mientras la carpeta carga, «Llevar al presupuesto» también está deshabilitado. · Leer la carpeta en `paginas/archivos/index.tsx` y pasar la franja a la sección.
8. **Nombres del tipo de obra.** · «Civil», «Telecomunicaciones», «Industrial» y «Sistemas» en lugar de las claves (`civil`, `telecom`…), que Elaborar mostraba tal cual. · `NOMBRE_DEL_DOMINIO` en `logicaComputo.ts`.
9. **Después de llevar.** · Aviso con `role="status"` «Se llevaron N partidas al presupuesto.» (o «Se llevó 1 partida…») y el enlace «Ver en Partidas», que lleva a Presupuesto con esa pestaña elegida (`irAPestana("partidas")`). «Llevar al presupuesto» desaparece para ese cómputo (repetirlo duplicaría los renglones); elegir otro archivo o extraer de nuevo empieza de cero. Se vuelven a leer el registro (`alLlevar` → `registro.recargar`) y el borrador (`refrescar`), y el diálogo no se cierra hasta que termina esa relectura, como tras fusionar un plano. · `CargarComputo.tsx`.
10. **Un solo principal en el diálogo.** · «Extraer cómputo» hasta que hay cómputo; luego «Llevar al presupuesto» (y «Extraer cómputo» pasa a secundario). «Aplicar la propuesta» y «Registrar el rendimiento» son terciarios; «Llevar sin los pendientes», secundario. Con un `.csv` elegido no se monta el flujo del plano, así que «Leer plano» no compite. · —
11. **Lo que salió con las bajas.** · `Elaborar.test.tsx` (35 pruebas) y `Llevar.test.tsx` (4) se borraron con la baja 19; de `logicaComputo.test.ts` salieron 4 de 14 (`filasIguales`, los dos de los períodos «Día N» y el veredicto). Se mudaron a `CargarComputo.test.tsx`: los selectores civiles sin preselección, el relleno, catálogo civil vacío, otro tipo de obra sin códigos, el error al extraer, el 409 de rendimientos con su propuesta y su dispersión, registrar sin tipo, el 422 al declarar medido, el rendimiento sin propuesta, los pendientes con propuestas y falla, aplicar una propuesta, llevar sin los pendientes y el error del llevar con su detalle. Se fueron con su baja: los valores por omisión de código, moneda y fecha (13 y 14), «Exportar a Excel» (15), las once del plan de trabajo (16), el informe y el veredicto (17), el total, las severidades, la tabla de partidas, «Sin hallazgos», «Elaborando…» y «un error al elaborar borra el resultado» (18), y «sin obra no aparece el botón» y «otra obra pide elaborar de nuevo» (19: dentro de la obra siempre hay obra). Los dos de «un 401 avisa a la sesión» no se mudaron: `CargarComputo` llama a `alExpirar` en `ocupar` como el resto de la interfaz, sin prueba propia. También salieron el enlace «Siguiente paso: Elaborar un presupuesto» de Componer (apuntaba a una pantalla que ya no existe; fuera de la obra Componer no ofrece siguiente paso) y la fila `elaborar` de `scripts/recorrido_funcional.toml`. · `git revert 7cf1358f 969ad67f`.
12. **Pruebas fuera de la sección que cambiaron.** · `rutas.test.ts` (32 y 29 pantallas, `elaborar` no existe, `archivos` sin módulo y usable con edificación apagada), `oferta.test.ts` (con edificación apagada se ofrece todo igual), `busqueda.test.ts` (la prueba de orden apaga «vial» en lugar de «edificación» para seguir cabiendo en ocho; pasa antes y después del `feat`: corrige su premisa), `Archivos.test.tsx` (con edificación apagada la sección está en el árbol y se abre), `logica.test.ts` (la firma `{ plano, computo }` y el caso sin planos), tres de Componer y el comentario del conteo en `tests/unit/test_recorrido_ux_playwright.py` (32 de nuevo: más `archivos`, menos `elaborar`). · —
13. **Rojo por aserción.** · `e5aeeb71`, con esbozos de `cuerpoDeValoracion` (todavía el cuerpo de Elaborar) y de `extensionesDeSubida`/`etiquetaDeSubida` (la firma nueva, sin mirar `plano`): 32 fallas, todas de aserción o de elemento que no está: 18 veces `Unable to find a label with the text of: Tipo de obra del archivo`, 3 `Unable to find role="button" and name "Cargar cómputo"`, `Unable to find role="treeitem" and name "Archivos y planos"`, `Unable to find role="table" and name "Registro de importaciones"` (quien revisa con edificación apagada: el marco cortaba la sección), `expected { codigo: 'P-001', …(3) } to deeply equal { codigo: '7', …(4) }`, `expected { id: 'elaborar', …(5) } to be undefined`, `expected 'edificacion' to be undefined`, `expected [ '.dxf', '.ifc', '.csv' ] to deeply equal [ '.csv' ]`, `expected [ 'resumen', 'presupuesto', …(4) ] to include 'archivos'` y los conteos 33/32 y 30/29. Dos ajustes de forma en el `feat`: `getByText` de la etiqueta de la zona de soltar encontraba dos nodos (el botón y la etiqueta oculta) y pasó a `getByRole("button")`; «Cerrar» habilitado se espera con `waitFor` (el diálogo espera la relectura). · —
14. **Verificación.** · Tras el `feat`, en tres corridas: `npx vitest run src/paginas/archivos src/paginas/obras src/paginas/componer src/paginas/sinJergaInterna.test.ts`, 23 archivos y 272 de 272 (dos de Componer cayeron antes de `7cf1358f` y pasan después: 12 archivos, 90 de 90); `src/marco src/shell src/comun`, 66 archivos y 719 de 719; `src/paginas/hoja`, 35 archivos y 655 de 655. No cayó ninguna por tiempo. `npm run lint` (eslint y `tsc -b --noEmit`) en 0. `uv run --active ruff check` y `ruff format --check` de `tests/unit/test_recorrido_ux_playwright.py`: limpios; su pytest, 1 falla que ya estaba (ver 16 a). Servidor sin tocar (`git diff 856f8c96..HEAD -- core/ aplicacion/ api/ asistente/` vacío), así que ni `api.json` ni más pytest. `knip` y `jscpd` no están instalados: se midió con `grep` (nada nombra ya `paginas/elaborar`, `CODIGO_POR_DEFECTO`, `PlanDeTrabajo`, `LlevarALaHoja`, `silice-elaborar` ni `filasDePartidas`) y con el conteo de líneas: `paginas/elaborar/` tenía 1.958 líneas en 6 archivos y desaparece; `logicaComputo.ts` pasa de 259 a 178 líneas con la baja y `tipos.ts` de 121 a 96. Colores y nombre de la empresa: limpio en cada commit. · —
15. **Archivos de la línea A.** · No se tocaron `paginas/hoja/index.tsx`, `PestanaPresupuesto.tsx` ni Versiones. Fuera de `paginas/archivos/` cambiaron `shell/rutas.ts`, `rutas.test.ts`, `marco/oferta.test.ts`, `marco/busqueda.test.ts`, Componer (`Guardar.tsx`, el comentario de `index.tsx` y tres pruebas), `scripts/recorrido_funcional.toml` y el comentario de la prueba de Python. · —
16. **Lo que preocupa.** · (a) `test_el_recorrido_funcional_tiene_una_fila_por_pantalla_y_ninguna_de_mas` sigue en rojo, como ya estaba en `856f8c96`: faltan filas para `archivos` (Tarea 11) y `tramos` (plan vial, T8). Esta tarea quitó la de `elaborar`, que sobraba; no se escribieron las que faltan porque el recorrido aún entra por el menú de módulos de antes (se ajusta en F7) y no se pueden comprobar sin navegador. (b) `POST /v1/hoja/llevar` usa el borrador vivo **más reciente** de la ficha y la obra; si la persona tiene otro más nuevo de la misma obra (otra ventana), las partidas van a ese y `refrescar` no las muestra. La ruta devuelve `borrador_id`, pero el front no lo compara con el del proveedor. (c) El rendimiento se declara con la fecha de la lista de la carpeta, no con la de hoy (Elaborar usaba la fecha del formulario, hoy por omisión): coincide con la fecha con que se valora. (d) El diálogo de 64 rem con la tabla del cómputo de siete columnas, a 1366×768 con letra «Muy grande»: se mide en la Tarea 14. (e) Con edificación apagada, el h3 «Cargar cómputo» repite el h2 del diálogo.

## Decisiones de la Tarea 13

Formato: pregunta · lo que se hizo · cómo cambiarlo.

1. **Orden de los commits.** · `83f73c50` solo mueve (`git mv`: `porcentaje.ts` a `comun/`, `OperacionesDePrecios.tsx` y el histórico a `paginas/mercado/`) y arregla las rutas de importación; `d45037df` es el rojo; el `feat` hace el resto. `AlCrearVersion` pasó de `OperacionesDePrecios` a `hoja/logicaVersiones.ts` (seis archivos de la Hoja cambian solo esa línea de importación). · Revertir el `feat`.
2. **Dónde vive el histórico.** · `paginas/mercado/HistoricoDePrecios.tsx` (no `paginas/historico/`, que desaparece), con h2 y sin h1. Su botón «Filtrar» pasa a secundario: Mercado ya tiene sus propios principales y la regla es uno por pantalla. Se pide a `GET /cambios-precio` igual que antes. · Archivo propio, un cambio de `kind`.
3. **Las pestañas nuevas se montan al elegirlas.** · Carbon pinta todos los paneles; el histórico repite el nombre «Insumo» de la pestaña «Lo que compramos» y las cotizaciones leen la API. Con `Tabs.onChange` solo se monta la pestaña elegida. · Quitar la condición en `mercado/index.tsx`.
4. **Variación del histórico.** · Se lee «12,50 %» (unidad en la celda) y la columna se llama «Variación», no «Variación (%)». · `presentar` en `HistoricoDePrecios.tsx`.
5. **Mercado sigue pidiendo `editar_hoja`; el histórico, antes `leer_proyecto`, deja de verlo quien solo revisa.** · **Corregido en la ronda 2 (punto 15).** Lo que se anotó en la ronda 1: la entrada «Estudio de mercado» de `shell/rutas.ts` exige `editar_hoja`, así que quien revisa no llega a Mercado ni, por tanto, al histórico ni a las cotizaciones en pantalla (la prueba de cuenta que revisa monta la página directamente). No se tocó el permiso (el plan no lo pide). Si quiere que quien revisa vea estas dos pestañas, hay que bajar `mercado` a `leer_proyecto` y que las dos primeras (que anotan y usan precios) no pinten sus controles sin `editar_hoja`. · `shell/rutas.ts` y `EstudioDelLado`.
6. **Cotizaciones sin cambios sin guardar.** · **Corregido en la ronda 2 (punto 17).** Lo que se anotó en la ronda 1: Mercado no tiene el borrador de la Hoja, así que `OperacionesDePrecios` recibe `cambios={0}` y no dice «guarde o descarte primero los N cambios pendientes». Cotizar parte de la versión guardada vigente, no del borrador; si hay cambios sin guardar en Presupuesto, siguen en el borrador (salir de Presupuesto ya pregunta, Tarea 3). La prueba vieja de ese aviso en Precios salió con el botón. · Pasar `hoja.cambios` si Mercado pasa a vivir dentro de `ProveedorDeLaHoja`.
7. **Aviso al crear la versión.** · El texto es de la interfaz («Se creó la versión V con la cotización.» o «… sin la cotización.»), no el `mensaje` del servidor como en Precios (decía «Se guardó la versión V con la cotización de X.»), porque así lo fija el plan. Tras crearla se vuelve a leer todo (`key`): la vigente pasa a ser V y la tabla muestra sus cotizaciones. No se abre la versión sola, como hacía la Hoja: se enlaza «Abrirla en el Presupuesto» (`?version=V`). El enlace solo sale dentro de una obra y de un enrutador. · `CotizacionesDeLaObra.tsx`.
8. **Qué es una «cotización de la obra».** · Los insumos de la versión vigente con cotización propia (`cotizacion` no vacía en `GET /v1/hoja/precios`). La tabla repite el rastro de la decisión de la conversión (moneda original, precio original, tasa con su valor exacto, fecha de la tasa y su fuente) con los textos que da el servidor; la interfaz no convierte ni redondea. Sin obra elegida dice «Elija una obra…»; sin versión vigente, «Esta obra aún no tiene versiones guardadas.». · `COLUMNAS` en `CotizacionesDeLaObra.tsx`.
9. **Diálogos de las operaciones.** · Siguen siendo los de la Hoja (`DialogoDeOperacion`, `useDialogoDeOperacion`), que necesitan un anfitrión fuera del contenido inerte: `PantallaConDialogos` (en `CotizacionesDeLaObra.tsx`) envuelve toda la pantalla de Mercado, pestañas incluidas, con el mismo contexto de la Hoja. Se importa `hoja.scss` desde `OperacionesDePrecios.tsx` para que los diálogos tengan estilo sin haber visitado la Hoja. · Una pieza común en `comun/` cuando una tercera pantalla lo use.
10. **El enlace en Precios.** · «Registrar una cotización en Mercado» solo con `editar_hoja`, dentro de una obra y de un enrutador; `PestanaPrecios` pierde las propiedades `cambios` y `alCrearVersion` (dos líneas menos en `hoja/index.tsx`). · `PestanaPrecios.tsx`.
11. **Pruebas que salieron o cambiaron.** · De `hoja/Versiones.test.tsx` salieron las del aviso de cambios en Precios, las 12 de «registrar» y las 3 de «retirar», y el caso «Precios» del cierre por panel (queda Trazabilidad); `SoloLectura.test.tsx` ya no espera los dos botones en Precios. Se mudaron a `mercado/Cotizaciones.test.tsx` (13): tabla con rastro, cuenta que revisa, sin versiones, sin obra, registrar (cuerpo y aviso con enlace), retirar, rechazo 422, 409 y 403, orden de «falta algo», inerte/foco/Esc y la prueba estática. No se mudaron: el 401 (el patrón común de `alExpirar`), 404 y 503, la petición en vuelo, `evidencia` y Tab atrapado; son del diálogo, que no cambió. `rutas.test.ts` (31 y 28 pantallas) y `busqueda.test.ts` ya no tienen `historico`. · —
12. **Rojo por aserción.** · `d45037df`, con `export const HistoricoDePrecios = PaginaHistorico` provisional para que el import no fuera lo que fallara: 21 fallas. Ejemplos literales: `AssertionError: expected [ 'Lo que compramos', …(1) ] to deeply equal [ 'Lo que compramos', …(3) ]` (cuatro pestañas), `expected { id: 'historico', …(5) } to be undefined`, `expected [ …(32) ] to deeply equal [ …(31) ]`, `expected <button …(2)></button> to be null` («Registrar una cotización…» sigue en Precios), `Unable to find an element with the text: 6,25 %`, `Unable to find an accessible element with the role "tab" and name "Cotizaciones de la obra"` y `Unable to find an accessible element with the role "combobox" and name "Insumo"`. · —
13. **Fuera de lo que pedía el plan.** · Salió la fila `historico` de `scripts/recorrido_funcional.toml` (la pantalla ya no existe) y `tests/unit/test_recorrido_ux_playwright.py` cuenta 31 rutas. Sigue en rojo, como ya estaba, `test_el_recorrido_funcional_tiene_una_fila_por_pantalla_y_ninguna_de_mas` por las filas que faltan de `archivos` y `tramos`. No se escribió la del histórico en Mercado: el recorrido aún entra por el menú de antes (F7) y no se puede comprobar sin navegador. · —
14. **Lo que preocupa.** · (a) El punto 5: quien revisa no llega a Mercado (corregido en la ronda 2). (b) Las cotizaciones leen `GET /v1/hoja/precios`, que evalúa «a la fecha del servidor»; la tabla repite los textos del servidor sin reetiquetar. (c) El histórico no filtra por «insumo elegido» si se escribe sin elegir: el texto suelto no se envía (lo escrito es una búsqueda). (d) `Tabs` de Carbon con cuatro pestañas a 1056 px y letra «Muy grande»: se mide en la Tarea 14. (e) `hoja.scss` entra completo en el bloque de Mercado, sin romper nada pero más pesado de lo necesario.

### Ronda 2 de la Tarea 13 (2026-11-02)

Defecto mayor del revisor: en la base (`bf36af98`) la pantalla `historico` pedía `leer_proyecto` y quien revisa la veía; tras la ronda 1 el histórico solo vivía dentro de `mercado`, que pedía `editar_hoja`, y quien revisa ya no llegaba ni al histórico ni a las cotizaciones. La prueba de la cuenta que revisa montaba la página sin pasar por el permiso. El plan no aprobaba esa pérdida. Commits: `f88db989` (rojo), `81a99f61` (arreglo) y este.

15. **Mercado en lectura para quien revisa.** · `mercado` pasa a `leer_proyecto` en `shell/rutas.ts`, así que se ofrece a quien arma y a quien revisa en el árbol de la obra, en el buscador (Ctrl+K) y en la ruta. Sin `editar_hoja` la página pinta solo «Histórico de precios» y «Cotizaciones de la obra», esta última sin «Registrar» ni «Retirar» (ya lo hacía `CotizacionesDeLaObra`); la nota de cabecera dice lo que esa cuenta puede hacer («Vea cómo cambiaron los precios de los insumos y las cotizaciones de la obra.»). «Lo que compramos» y «Lo que cobramos» no se le pintan (regla de la Tarea 2b: no se deshabilita, no se pinta): anotan observaciones y usan precios, y su lectura, `GET /v1/mercado/{lado}/{codigo}`, exige `editar_hoja`, así que sin escribir tampoco tendrían nada que mostrar. Las pestañas salen de una lista (`PESTANAS` en `mercado/index.tsx`) filtrada por la cuenta; las dos nuevas siguen montándose al elegirlas (punto 3). · Volver a `editar_hoja` en `shell/rutas.ts` (y las dos pruebas del punto 19).
16. **El servidor no cambió.** · Las lecturas que usan las dos pestañas ya aceptaban `leer_proyecto` (TABLA de `tests/unit/test_api_acceso_por_ruta.py`): `GET /cambios-precio`, `GET /insumos`, `GET /v1/hoja/versiones` y `GET /v1/hoja/precios`. Mercado no lee `GET /v1/mercado/objetivos` (lo lee la Hoja; ya es `leer_proyecto` desde la 2b). El estudio de cada lado y todo lo que escribe sigue en `editar_hoja`. Por eso no se tocaron ni la TABLA ni `docs/api.json`. · —
17. **Cotizar con cambios sin guardar en el Presupuesto (revisión de la decisión 6).** · Lo que pasaba: con cambios sin guardar en el borrador de la 002, registrar una cotización desde Mercado creaba la 003 desde la 002 guardada. Los cambios no se perdían, pero quedaban sin aviso en un borrador de la 002. Al volver, la Hoja decía «La versión vigente ahora es la 003» y, al guardar, pedía confirmar con «Otra persona guardó la versión 003…» (había sido la misma persona). Si confirmaba, la versión nueva salía de la 002 con los cambios y **sin la cotización**. Arreglo prudente: la pestaña lee los borradores que el servidor conserva de esta ficha (`GET /v1/hoja/borradores` con `useOfertas` de la Hoja, los mismos que la Hoja ofrece retomar) y pasa a `OperacionesDePrecios` la suma de los cambios de los de esta obra. Con alguno, no se ofrece cotizar ni retirar y se dice «Cotizar crea una versión nueva desde la guardada: guarde o descarte primero los N cambios pendientes. Están en el Presupuesto de esta obra.», como hacía Precios (la clásica, P:1946). Mientras se leen los borradores no se ofrece nada; si la lectura falla, se ofrece como antes. Quien revisa no lee los borradores. · Volver a `cambios={0}` en `CotizacionesDeLaObra.tsx`.
18. **Pendientes: la pantalla de la acción también cuenta.** · Al bajar `mercado`, el pendiente «Actualizar precios» (pantalla `actualizacion`, `editar_hoja`), que lleva a Mercado porque Mercado absorberá esa pantalla (D-F3-2), se le ofrecía como botón a quien revisa. Lo detectó una prueba que ya existía en `pendientes/Bandeja.test.tsx` («una acción que su cuenta no puede usar no se ofrece como botón»). La bandeja exige ahora la pantalla donde se llega **y** la de la acción, la misma regla de la franja del Resumen (`pantallaVisible`). De paso, el pendiente «Entregar» (`entregar_paquete`, lleva a Aprobaciones) ya no se ofrece como botón a quien no puede entregar; antes bastaba con poder abrir Aprobaciones. · `Bandeja.tsx`.
19. **Pruebas.** · Nueva `mercado/QuienRevisa.test.tsx` (5) con las acciones por rol escritas a mano desde `seguridad/permisos.py` (`ACCIONES` de `shell/obras/datosDePrueba.tsx`, que vigila `test_front_acciones_por_rol.py`) y el marco entero. Con las de quien revisa, `mercado` es usable, está en la oferta y el buscador da «Casa Demo › Mercado»; desde la ruta de la obra, el árbol tiene «Mercado», hay dos pestañas, el histórico se lee y las cotizaciones salen sin «Registrar», sin «Retirar» y sin ningún `POST`. Con las de quien arma salen las cuatro pestañas y las dos operaciones, como en la ronda 1. `mercado/Cotizaciones.test.tsx` gana 2: los borradores con cambios de esta obra impiden cotizar y lo dicen; los que no tienen cambios o son de otra obra, no. Cambiaron su premisa `rutas.test.ts` (`mercado` con `leer_proyecto`) y `BarraLateral.test.tsx` (quien revisa ve «Mercado» en el árbol). · —
20. **Rojo por aserción.** · `f88db989`: fallan 4 de 5 y la de quien arma pasa (no debía cambiar). Literales: `AssertionError: expected false to be true // Object.is equality` (`usable`), `Unable to find role="treeitem" and name "Mercado"`, `Unable to find role="tab" and name "Histórico de precios"` y `Unable to find role="tab" and name "Cotizaciones de la obra"`. Las dos del punto 17 se escribieron antes del arreglo y se vieron en rojo (1 de 14: `Unable to find an element with the text: Cotizar crea una versión nueva desde la guardada: guarde o descarte primero los 3 cambios pendientes. Están en el Presupuesto de esta obra.`). Van en el commit del arreglo porque los tres commits ya estaban fijados. La del punto 18 cayó con `AssertionError: expected <button …(2)></button> to be null` antes de arreglar `Bandeja.tsx`. · —
21. **Verificación.** · Tras el arreglo: `npx vitest run src/paginas/mercado src/marco src/shell src/comun src/paginas/hoja src/paginas/pendientes src/paginas/obras`, 116 archivos y 1.529 de 1.529; `npm run lint` (eslint y `tsc -b --noEmit`) en 0. pytest con `-W error`: `test_api_acceso_por_ruta.py`, `test_api_mercado.py` y `test_openapi.py`, 311 de 311; `test_recorrido_ux_playwright.py` y `test_front_acciones_por_rol.py`, verdes salvo la falla que ya estaba (punto 13). `ruff check .` limpio. `git diff 5a9af8ad..HEAD -- api core aplicacion asistente docs/api.json` vacío. · —
22. **Lo que preocupa.** · (a) Cualquier borrador con cambios de la obra en esta ficha impide cotizar, aunque sea de una versión vieja que la persona ya no piensa guardar: tiene que retomarlo o descartarlo en el Presupuesto (la Hoja se lo ofrece). Es lo prudente; si molesta, se puede limitar a los borradores de la versión vigente. (b) Los borradores se leen al abrir la pestaña. Si se guarda o se descarta en otra ventana, el aviso no cambia hasta volver a abrirla. (c) La línea de la pantalla en el buscador («Compare precios del mercado y elija los suyos») sigue hablando de elegir precios, también para quien revisa: `enUnaLinea` es una sola por pantalla y no depende de la cuenta. (d) Sigue en rojo `test_el_recorrido_funcional_tiene_una_fila_por_pantalla_y_ninguna_de_mas`, como antes (punto 13).

### Ronda 3 de la Tarea 13 (2026-11-02)

23. **Cobertura recuperada.** · El commit `21d50f47` borró de `hoja/Versiones.test.tsx` las pruebas de cotizar y no se mudaron, aunque el código (`OperacionesDePrecios`, `DialogoDeOperacion`, `useOperacion`) sigue vivo. `mercado/Cotizaciones.test.tsx` gana 6 (20 en total) con los oráculos de la base `bf36af98`: un 401 llama a `alExpirar`; una sola petición en vuelo (todo deshabilitado, Esc no cierra, el error no se pierde); 404 y 503 tal cual; la evidencia viaja tal cual; Tab y Mayús+Tab no salen del diálogo. Solo pruebas. Mutaciones: sin `alExpirar()` cae la del 401; con el diálogo cerrable en vuelo o sin `disabled` en «Cotizar» cae la de la petición en vuelo; quitar solo la guarda `enVuelo` de `useOperacion` no hace caer ninguna, porque el botón deshabilitado ya impide el segundo envío (la guarda es una segunda capa).
