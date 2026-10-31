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
| 6 | Versiones | Opus | L | 9, 24 |
| 7 | El APU de una partida en panel lateral | Opus | M | — |
| 8 | Un solo diálogo para las líneas del APU | Sonnet | M | — |
| 9 | «Agregar partida», puerta única (parecidas y componer en panel) | Opus | L | 20, 21 |
| 10 | Registro de importaciones de la obra (servidor) | Sonnet | M | — |
| 11 | Archivos y planos: el plano y el registro | Opus | L | 22 (sin código) |
| 12 | «Cargar cómputo» absorbe Elaborar | Opus | L | 13-19 |
| 13 | Mercado: histórico de precios y cotizaciones | Sonnet | M | — |
| 14 | Cierre de F4 | Opus (orquestador) y Sonnet (menores) | M | — |

Orden: 0 → 1 → 2 → 2b → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14. La 2b tiene que estar antes que la 3,
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

