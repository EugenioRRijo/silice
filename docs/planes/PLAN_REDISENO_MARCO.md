# Rediseño del marco (hasta F2): plan de implementación

> **Para agentes:** SUB-SKILL REQUERIDA: superpowers:subagent-driven-development (recomendada) o
> superpowers:executing-plans, tarea por tarea. Los pasos usan casillas (`- [ ]`). Cada tarea termina con su árbitro
> (MANUAL_ARBITRO) antes de abrir la siguiente. **Agentes de uno en uno**; menores agrupados; navegador solo al final.

**Objetivo:** cambiar el marco de Sílice (barra superior, barra lateral, ruteo por obra) por el diseño aprobado:
barra carbón con logo, árbol marfil con Pendientes / Obras / Empresa, la obra como espacio de trabajo y Ctrl+K,
dejando las pantallas actuales montadas dentro de las secciones (patrón estrangulador).

**Arquitectura:** el marco nuevo vive en `frontend-desktop/src/marco/` y reemplaza a los módulos de
`shell/` (selector de módulos, panel de área, accesos, selector de obra). Las páginas de `paginas/` no se tocan en esta
tanda: cada sección de la obra o entrada de Empresa monta una página existente por su `id` de `shell/rutas.ts`. El
servidor gana dos rutas de lectura (`GET /v1/tema`, `GET /v1/obras/todas`) sin tocar `core/`.

**Stack:** React 19 + TypeScript + Carbon 11 (tema g10) + react-router 7 (HashRouter) + Vitest; FastAPI + SQLAlchemy +
pytest. Dependencias nuevas solo de desarrollo: `knip`, `jscpd`.

**Especificación:** [docs/especificaciones/2026-10-26-rediseno-marco-obras-design.md](../especificaciones/2026-10-26-rediseno-marco-obras-design.md)

## Restricciones globales

- `core/` intacto. Nada de IA nueva.
- Nombre, logo y paleta de la empresa **nunca** en el repositorio (ni código, ni pruebas, ni commits, ni capturas).
  El repo lleva tema neutro; los valores de la empresa van en `data/tema/` (ignorado por git).
- Español de Venezuela; coma decimal y punto de miles en toda cifra visible.
- Anchos de referencia 1056, 1366 y 1910 px; escala de letra 1 / 1,25 / 1,5 vigente.
- Accesibilidad conservada: foco visible, Esc cierra lo que abre, regiones vivas, contraste AA (4,5:1 texto,
  3:1 bordes e iconos).
- Vocabulario del usuario: «obra», «sección», «pendiente», «empresa». Prohibido en textos visibles: «módulo»,
  «área», «página», «carpeta de trabajo» (salvo en Empresa > Carpetas, para el administrador), «Streamlit».
- Componente de más de 250 líneas exige una línea de razón en su cabecera.
- TDD: prueba en rojo vista antes del código; suite completa (`npm test`, `npm run lint`, `uv run --active pytest -q`)
  al cierre de F2.
- Duplicación (jscpd, una pasada TS/TSX): umbral fijo en 1 % (hoy 0,88 %). Si una tarea lo supera, la pieza común
  se extrae en esa misma tarea; el umbral no sube sin un ruling escrito en la bitácora.
- Commit al cerrar cada tarea; antes de cada commit, `git diff --cached --stat` para no arrastrar archivos ajenos.

## Foco de revisión

1. **Cuenta sin `CAMBIAR_CASO`**: el árbol solo muestra las obras de la carpeta abierta; nunca ofrece una obra que
   al abrirla daría 403. Prueba en Tarea 3 (servidor) y Tarea 6 (árbol).
2. **Obra borrada o carpeta que ya no existe** al abrir `#/obra/<carpeta>/<obra>/...` desde un enlace viejo: aviso
   «Esa obra ya no existe» y vuelta a Pendientes, sin pantalla en blanco. Prueba en Tarea 4.
3. **Dos pestañas en obras distintas**: la que pierde la obra muestra «Esta obra se abrió en otra pestaña» con
   «Retomar» y no envía escrituras mientras tanto. Prueba en Tarea 4.
4. **Archivo de tema roto** (JSON inválido, color que no es `#rrggbb`, logo de 5 MB o SVG): se usa el tema neutro
   y el servidor no falla. Prueba en Tarea 1.
5. **Cambiar de obra con cambios sin guardar** en la Hoja: se conserva la confirmación de salida que ya existe
   (`shell/salida.ts`, `shell/sucio.ts`). Prueba en Tarea 8.

---

## P0. Cierre del trabajo en pausa (antes de cualquier tarea)

En `.worktrees/s2madm` hay trabajo sin confirmar de seis encargos detenidos el 2026-10-26 (detalle en la memoria
«estado y traspaso»). Se cierran **uno a la vez**, cada uno con su árbitro, en este orden:

| # | Encargo | Archivos principales | Cierre |
|---|---|---|---|
| P0.1 | Menores de T26 y T16 juntos | `aplicacion/hoja.py`, `aplicacion/hoja_lineas_apu.py`, `api/rutas/hoja.py`, `paginas/hoja/AgregarLineaApu.tsx`, `paginas/hoja/ObjetivoDeMercado.tsx(.test)` | verde + commit + árbitro |
| P0.2 | T24 Procura | `paginas/control/{index,logica,PestanaValuaciones,PestanaProcura,procura}.ts(x)`, `control.scss`, `comun/TablaDensa.tsx` | ídem |
| P0.3 | T25 Precio del corte | `aplicacion/{control,causas,precios_declarados,tablas_corte}.py`, `api/rutas/{control,mercado}.py`, `migraciones/caso/versions/caso_0017_mp_corte.py`, pruebas `test_api_control_declarados`, `test_api_mercado` | ídem |
| P0.4 | T20 Aprobar | `paginas/aprobar/`, `Entregar.test.tsx`, `test_api_entregas.py`, `shell/rutas.test.ts`, `PorAprobar.test.tsx`, `Mesa.test.tsx` | ídem |
| P0.5 | Árbitro D-3 (visor) | sin código: solo veredicto | veredicto escrito en bitácora |

`data/instalacion.db-*` y `docs/manual_nuevo/` no se confirman (artefactos locales). Cada agente recibe: el `git diff`
de sus archivos, el texto de su tarea en `docs/planes/PLAN_MONTAR_PRESUPUESTO.md` y la regla de no tocar archivos de
otro encargo. Hecho P0, el árbol queda limpio salvo los artefactos locales.

---

### Tarea 1: Tema de la empresa (neutro en el repo, local en `data/tema/`)

**Archivos:**
- Crear: `aplicacion/tema.py`, `api/rutas/tema.py`
- Modificar: `api/main.py` (registrar el router), `.gitignore` (`data/tema/`)
- Crear: `frontend-desktop/src/marco/tema.ts`, `frontend-desktop/src/marco/useTema.ts`
- Modificar: `frontend-desktop/src/estilos/tokens.scss` (alias nuevos con valores neutros)
- Pruebas: `tests/unit/test_api_tema.py`, `frontend-desktop/src/marco/tema.test.ts`

**Interfaces:**
- Produce (servidor): `leer_tema(carpeta: Path) -> Tema` con `Tema(acento: str | None, marco: str | None,
  lateral: str | None, tiene_logo: bool)`; `GET /v1/tema` → `{"acento": str|null, "marco": str|null,
  "lateral": str|null, "tiene_logo": bool}` sin sesión (lo usa la pantalla de entrada); `GET /v1/tema/logo` → la
  imagen o 404.
- Produce (front): `aplicarTema(tema: TemaRespuesta, raiz: HTMLElement): void` que fija `--silice-acento`,
  `--silice-marco`, `--silice-lateral` solo para colores válidos; `useTema(): { logo: string | null }`.
- Alias neutros en `tokens.scss`: `--silice-marco: var(--cds-background-inverse)`,
  `--silice-acento: #{colors.$yellow-30}`, `--silice-lateral: #{colors.$warm-gray-10}`,
  `--silice-lateral-activo: #{colors.$warm-gray-20}`.

- [ ] **Paso 1: prueba roja del servidor** en `tests/unit/test_api_tema.py`:
  - `test_sin_carpeta_de_tema_devuelve_neutro`: sin `data/tema/` → `{"acento": None, "marco": None, "lateral": None, "tiene_logo": False}`.
  - `test_colores_validos_se_devuelven`: `tema.json` `{"acento": "#123abc", "marco": "#000000", "lateral": "#fafafa"}` → los tres tal cual.
  - `test_color_invalido_se_descarta`: `{"acento": "amarillo", "marco": "#12345"}` → ambos `None`, 200.
  - `test_json_roto_devuelve_neutro`: `tema.json` = `"{no"` → 200 y neutro.
  - `test_logo_png_se_sirve` (`logo.png` de 1×1) → 200, `image/png`; `test_logo_svg_no_se_sirve` → `tiene_logo` False y 404; `test_logo_mayor_de_512_kb_no_se_sirve` → ídem.
  - `test_tema_sin_sesion`: `GET /v1/tema` sin cookie → 200.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_tema.py -q` → FALLA (404 de la ruta).
- [ ] **Paso 3:** implementar `leer_tema` (formatos de logo admitidos: `logo.png`, `logo.jpg`, `logo.webp`; tope
  512 KB; color válido = `^#[0-9a-fA-F]{6}$`) y el router. La carpeta sale de la misma raíz de datos que usa
  `instalacion.db`.
- [ ] **Paso 4:** misma orden → PASA.
- [ ] **Paso 5: prueba roja del front** en `marco/tema.test.ts`: `aplicarTema` con `{acento:"#123abc", marco:null, ...}`
  fija solo `--silice-acento`; con `"rojo"` no fija nada; `useTema` con `tiene_logo: true` devuelve
  `"/v1/tema/logo"`, con `false` devuelve `null`.
- [ ] **Paso 6:** `cd frontend-desktop && npx vitest run src/marco/tema.test.ts` → FALLA; implementar; → PASA.
- [ ] **Paso 7:** en `data/tema/` de la instalación local (fuera del repo) dejar `tema.json` y `logo.png` de la empresa
  para la prueba de Eugenio. Verificar `git status` sin `data/tema/`.
- [ ] **Paso 8: commit** de los archivos de la tarea (sin `data/tema/`).

### Tarea 2: Guardias de código muerto y duplicación en la CI

**Archivos:**
- Modificar: `frontend-desktop/package.json` (devDependencies `knip`, `jscpd`; scripts `muerto`, `duplicado`),
  `frontend-desktop/scripts/verificar_licencias.mjs` si alguna licencia nueva no está permitida,
  `.github/workflows/ci.yml` (paso que corre ambos)
- Crear: `frontend-desktop/knip.json`, `frontend-desktop/.jscpd.json`, `docs/bitacora/2026-10-26-linea-base-front.md`

**Interfaces:** ninguna de código. Produce los comandos `npm run muerto` y `npm run duplicado`.

- [ ] **Paso 1:** `knip.json` con `entry` (`src/main.tsx`, `scripts/*.mjs`), `project` (`src/**/*.{ts,tsx}`),
  `ignoreDependencies` para lo que solo se usa desde SCSS (`@carbon/styles`, `@ibm/plex-sans`, `@ibm/plex-mono`) y
  `@carbon/charts` (par de `@carbon/charts-react`); `npm run muerto` = `knip --include files,dependencies,unlisted,unresolved`.
- [ ] **Paso 2:** `npm run muerto` → hoy debe señalar los 2 «unlisted» de pruebas (`@carbon/colors`, `@univerjs/core`)
  y el import roto de `paginas/aprobar/Aprobar.test.tsx` (si P0.4 no lo resolvió). Declararlos o arreglarlos hasta
  salida 0.
- [ ] **Paso 3:** `.jscpd.json` con `minLines: 8`, `threshold: 1`, ignorando `**/*.test.*`; `npm run duplicado` → salida 0
  (hoy 0,79 %).
- [ ] **Paso 4:** paso de CI que corre `npm run muerto` y `npm run duplicado`; `npm run licencias` en verde.
- [ ] **Paso 5:** bitácora con la línea base de la especificación §6.1 (36.250 / 40.255 / 4.608 líneas; 38
  exportaciones y 57 tipos sin uso) y las cifras tras esta tarea.
- [ ] **Paso 6: commit.**

### Tarea 3: Obras de todas las carpetas (`GET /v1/obras/todas`)

**Archivos:**
- Modificar: `aplicacion/proyectos.py` (función nueva), `api/rutas/obras.py` (ruta nueva)
- Prueba: `tests/unit/test_api_obras_todas.py`

**Interfaces:**
- Consume: la lista de carpetas que ya arma `api/rutas/casos.py::consultar_casos` y `proyectos_del_caso(sesion)`.
- Produce: `obras_de_las_carpetas(carpetas: list[tuple[str | None, Path]]) -> list[ObraDeCarpeta]` con
  `ObraDeCarpeta(carpeta: str | None, obra_id: int, obra: str, version_codigo: str | None)`. `carpeta` es el
  `nombre` que acepta `POST /v1/casos/actual`; `None` = la carpeta de la empresa (la del proceso, a la que se vuelve
  con `DELETE /v1/casos/actual`), que va primero. Orden: carpeta de la empresa, luego carpetas por nombre, y dentro
  de cada una obras por nombre (sin distinguir mayúsculas). `GET /v1/obras/todas` →
  `{"carpeta_actual": str|null, "obras": [{"carpeta": str|null, "carpeta_titulo": str, "obra_id": int, "obra": str,
  "version_codigo": str|null}]}`; `carpeta_titulo` es «Carpeta de la empresa» para `null` y el nombre sin `.db` en
  los demás casos (lo calcula el servidor). `carpeta` conserva el `.db` (es lo que acepta `POST /v1/casos/actual`) y
  así viaja en las rutas del front (`#/obra/Carpeta%20Norte.db/<id>/...`); la carpeta de la empresa se escribe
  `empresa`. Como `listar_casos` solo admite nombres terminados en `.db`, no hay choque posible con `empresa` y no
  hace falta ningún 422 (árbitro de la Tarea 3, ronda 1). Sin `CAMBIAR_CASO`, el front no llama a
  `POST /v1/casos/actual` si `carpeta == carpeta_actual`.

- [ ] **Paso 1: prueba roja** con dos carpetas ficticias («Carpeta Norte» con obras «Galpón» y «Clínica»;
  «Carpeta Sur» con «Vialidad»):
  - `test_lista_obras_de_todas_las_carpetas`: con `CAMBIAR_CASO` → 3 obras, orden `Carpeta Norte/Clínica`,
    `Carpeta Norte/Galpón`, `Carpeta Sur/Vialidad`.
  - `test_sin_cambiar_caso_solo_la_carpeta_abierta`: cuenta sin `CAMBIAR_CASO` en «Carpeta Sur» → solo `Vialidad`.
  - `test_carpeta_ilegible_se_omite`: una carpeta con archivo SQLite corrupto → no aparece y la ruta da 200.
  - `test_no_escribe`: la fecha de modificación de los `.db` no cambia.
  - `test_sin_sesion_401`.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_obras_todas.py -q` → FALLA.
- [ ] **Paso 3:** implementar abriendo cada carpeta en solo lectura con el mismo motor que `version_vigente` y
  cerrándolo al terminar. Permiso de la ruta: `LEER`; el filtro por `CAMBIAR_CASO` se hace dentro.
- [ ] **Paso 4:** → PASA. Regenerar `api.json` con el truco de `git archive HEAD` (memoria) y añadir la ruta al
  oráculo de rutas si existe uno para `obras`.
- [ ] **Paso 5: commit.**

### Tarea 4: Ruteo por obra y vigilancia de pestañas

**Archivos:**
- Crear: `frontend-desktop/src/marco/secciones.ts`, `frontend-desktop/src/marco/useObraDeLaRuta.ts`,
  `frontend-desktop/src/marco/otraPestana.ts`
- Pruebas: `marco/secciones.test.ts`, `marco/useObraDeLaRuta.test.tsx`, `marco/otraPestana.test.ts`

**Interfaces:**
- Produce `SECCIONES_DE_OBRA: readonly SeccionDef[]` con `SeccionDef { id: SeccionId; titulo: string;
  pagina: string; ayuda: string }` y este reparto exacto (la `pagina` es el `id` de `shell/rutas.ts`):

  | id | titulo | pagina | pestañas que absorbe en F4 |
  |---|---|---|---|
  | `resumen` | Resumen | `obras` | — |
  | `presupuesto` | Presupuesto | `hoja` | elaborar, componer, similares |
  | `archivos` | Archivos y planos | `null` | (pantalla nueva en F4) |
  | `versiones` | Versiones | `null` | (hoy dentro de la Hoja; vista propia en F4) |
  | `aprobaciones` | Aprobaciones | `aprobar` | revisar, entregar |

  `pagina: string | null`; una sección con `null` no aparece en el árbol hasta que F4 le dé pantalla (nada de
  pantallas «próximamente»). `aprobar` lo registra P0.4. «Histórico de cambios de precio», «Índices del BCV»,
  «Precios de la empresa», «Actualizar precios» y «Simulador» quedan como pestañas de Precios y catálogo en F5; hasta
  entonces se alcanzan desde Ctrl+K.
  | `mercado` | Mercado | `mercado` | actualizacion |
  | `control` | Control de obra | `control` | tablero, reajuste, escenarios |

  `ayuda` es la frase «para qué sirve» de cada sección (≤ 90 caracteres), por ejemplo
  `presupuesto`: «Las partidas de la obra con sus cantidades, precios y APU.»
- Produce `ENTRADAS_DE_EMPRESA: readonly EntradaDef[]` (`{ id: EntradaId, titulo, pagina, ayuda }`) en este orden,
  con ids propios estables (no el id de la pantalla, que cambiará en F5/F6; enmienda del orquestador tras el árbitro
  de la Tarea 4): `precios` → Precios y catálogo (pantalla `catalogo`), `auditoria` → Auditar un presupuesto
  (`auditoria`), `produccion` → Producción (`existencias`), `personas` → Empresa y personas (`administracion`),
  `ayuda` → Ayuda (`acerca` hasta F6). La ruta es `#/empresa/<id>`.
- Produce rutas: `#/pendientes`, `#/obra/:carpeta/:obraId/:seccion`, `#/empresa/:entrada`;
  `rutaDeObra(carpeta: string | null, obraId: number, seccion: SeccionId): string` (`null` → `empresa`; codifica la carpeta con
  `encodeURIComponent`).
- Produce `useObraDeLaRuta(): EstadoObra` con `EstadoObra = { tipo: "cargando" } | { tipo: "lista"; carpeta: string;
  obraId: number; seccion: SeccionDef } | { tipo: "no_existe" } | { tipo: "en_otra_pestana"; retomar: () => void }`.
  Al entrar: si la carpeta difiere de la abierta, `POST /v1/casos/actual`; después `PUT /v1/sesion/proyecto`;
  solo entonces `lista`.
- Produce `otraPestana.ts`: `anunciarObra(carpeta, obraId)` y `escucharOtraPestana(cb)` sobre `BroadcastChannel("silice-obra")`
  (sin `BroadcastChannel` disponible, no hace nada).

- [ ] **Paso 1: pruebas rojas**:
  - `secciones.test.ts`: los 7 ids en ese orden; cada `pagina` no nula existe en `PAGINAS`; `archivos` y
    `versiones` tienen `pagina: null`; ningún `titulo`/`ayuda` contiene
    «módulo», «área», «página» ni «Streamlit»; `rutaDeObra("Carpeta Sur.db", 3, "presupuesto")` →
    `"/obra/Carpeta%20Sur.db/3/presupuesto"`.
  - `useObraDeLaRuta.test.tsx`: misma carpeta → solo `PUT /v1/sesion/proyecto {"proyecto":"3"}`; otra carpeta →
    `POST /v1/casos/actual` y luego el `PUT`, en ese orden; obra inexistente (404) → `no_existe`;
    sección desconocida → `no_existe`.
  - `otraPestana.test.ts`: con dos canales falsos, anunciar `("Norte", 1)` en uno hace que el otro, que tenía
    `("Sur", 3)`, reciba el aviso; anunciar la misma obra no avisa.
- [ ] **Paso 2:** `npx vitest run src/marco` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** → PASA.
- [ ] **Paso 5: commit.**

### Tarea 5: Barra superior nueva

**Archivos:**
- Crear: `frontend-desktop/src/marco/BarraSuperior.tsx`, `marco/BarraSuperior.scss`, `marco/Migas.tsx`
- Prueba: `marco/BarraSuperior.test.tsx`

**Interfaces:**
- Consume: `useTema()` (Tarea 1), `SECCIONES_DE_OBRA` / `ENTRADAS_DE_EMPRESA` (Tarea 4), `MenuCuenta` y
  `TamanoLetra` existentes.
- Produce: `<BarraSuperior migas={Miga[]} alAbrirBuscador={() => void} nombre={string} alSalir={() => void} />` con
  `Miga = { texto: string; ruta?: string }`.

Aspecto (maqueta aprobada): fondo `var(--silice-marco)`, 48 px de alto, borde inferior de 3 px
`var(--silice-acento)`; a la izquierda el logo (`useTema().logo`, 28 px de alto; sin logo, el texto «Sílice»);
migas; a la derecha un botón ancho «Buscar… (Ctrl+K)», el tamaño de letra y la cuenta.

- [ ] **Paso 1: pruebas rojas**: con logo → `img` con `alt="Logo de la empresa"`; sin logo → texto «Sílice»;
  migas `[Mis obras, Clínica, Presupuesto]` → las dos primeras son enlaces y la última tiene `aria-current="page"`;
  clic en «Buscar…» y la tecla Ctrl+K llaman a `alAbrirBuscador`; a 1056 px el texto del buscador se reduce a
  icono con `aria-label="Buscar (Ctrl+K)"` (prueba de clase, no de píxeles).
- [ ] **Paso 2:** FALLA. **Paso 3:** implementar. **Paso 4:** PASA. **Paso 5: commit.**

### Tarea 6: Barra lateral marfil en árbol

**Archivos:**
- Crear: `frontend-desktop/src/marco/BarraLateral.tsx`, `marco/BarraLateral.scss`, `marco/useObras.ts`
- Modificar: `shell/obras/DialogoNuevaObra.tsx` (elegir carpeta cuando hay más de una)
- Prueba: `marco/BarraLateral.test.tsx`

**Interfaces:**
- Consume: `GET /v1/obras/todas` (Tarea 3), `SECCIONES_DE_OBRA`, `ENTRADAS_DE_EMPRESA`, `rutaDeObra` (Tarea 4),
  `usable(pagina, acciones, modoEntrega)` de `shell/rutas.ts`.
- Produce: `<BarraLateral obraAbierta={{carpeta, obraId} | null} seccion={SeccionId | null} />`;
  `useObras(): { obras: ObraDeCarpeta[]; recargar: () => void; estado: "cargando" | "lista" | "error" }`.

Aspecto: fondo `var(--silice-lateral)`, 236 px; zona 1 «Pendientes» (enlace a `#/pendientes`); zona 2 «Obras» con el
árbol (obra abierta desplegada con sus 7 secciones, línea guía a la izquierda; las demás plegadas; agrupadas por
carpeta solo si hay más de una carpeta) y **«Nueva obra» como botón vistoso** (Eugenio, 2026-10-26): ancho completo
de la barra, relleno `var(--silice-acento)` con texto `var(--silice-marco)` en seminegrita, icono `Add` de Carbon,
40 px de alto, siempre visible (fijo bajo la cabecera «Obras», no al final de una lista larga); con cuenta sin
permiso de crear obras no aparece; zona 3 «Empresa» con `ENTRADAS_DE_EMPRESA`.
Activo: fondo `var(--silice-lateral-activo)` y raya de 3 px `var(--silice-acento)`. Sin contadores en esta tanda
(llegan en F3).

- [ ] **Paso 1: pruebas rojas**:
  - árbol con 3 obras de 2 carpetas → dos grupos con el nombre de la carpeta; con 1 carpeta → sin grupos.
  - obra abierta desplegada con sus 5 secciones con pantalla (las de `pagina: null` no salen); la activa con
    `aria-current="page"`.
  - una sección o entrada cuya `pagina` no es `usable` para la cuenta no se muestra (cuenta sin `editar_hoja` no ve
    «Presupuesto» si `hoja` lo exige).
  - error de `GET /v1/obras/todas` → «No se pudieron cargar las obras» con «Reintentar»; sin obras → «Todavía no hay
    obras» y «+ Nueva obra».
  - teclado: flechas arriba/abajo recorren, derecha despliega, izquierda pliega (patrón `tree` de WAI-ARIA).
  - «Nueva obra» es un `button` con clase de botón principal del marco, está antes del árbol en el orden del DOM y
    no se renderiza sin el permiso de crear obras; el contraste texto/fondo del tema neutro es ≥ 4,5:1.
  - `DialogoNuevaObra` con 2 carpetas pide la carpeta (por omisión la abierta); con 1, no.
- [ ] **Paso 2:** FALLA. **Paso 3:** implementar. **Paso 4:** PASA. **Paso 5: commit.**

### Tarea 7: Buscador Ctrl+K

**Archivos:**
- Crear: `frontend-desktop/src/marco/Buscador.tsx`, `marco/buscador.ts`
- Prueba: `marco/buscador.test.ts`, `marco/Buscador.test.tsx`

**Interfaces:**
- Consume: `useObras()`, `SECCIONES_DE_OBRA`, `ENTRADAS_DE_EMPRESA`, `rutaDeObra`.
- Produce: `resultadosDe(texto: string, obras: ObraDeCarpeta[]): Resultado[]` con
  `Resultado = { texto: string; detalle: string; ruta: string }`, máximo 8; `<Buscador abierto alCerrar />`.

Coincidencia sin acentos ni mayúsculas, por palabras («clin pres» encuentra «Clínica Las Mercedes › Presupuesto»).
Orden: obras, después secciones de obras, después entradas de Empresa, después las páginas de `PAGINAS` usables
que aún no tienen sitio en el árbol (Histórico, Índices, Simulador…), para que nada quede inalcanzable en esta tanda.

- [ ] **Paso 1: pruebas rojas**: `resultadosDe("clin", …)` → primero «Clínica Las Mercedes»; `"clin pres"` →
  «Clínica Las Mercedes › Presupuesto» con su ruta; `"precios"` → «Precios y catálogo»; `""` → las 5 obras más
  recientes de la lista; nunca más de 8. Componente: Esc cierra y devuelve el foco al botón; Enter navega a la ruta
  del primero; flechas mueven la selección (`role="listbox"`).
- [ ] **Paso 2:** FALLA. **Paso 3:** implementar sobre `ComposedModal` de Carbon. **Paso 4:** PASA. **Paso 5: commit.**

### Tarea 8: Montaje del marco y retiro de los módulos

**Archivos:**
- Crear: `frontend-desktop/src/marco/Marco.tsx`, `marco/marco.scss`
- Modificar: `frontend-desktop/src/App.tsx` (monta `Marco` en vez de `Shell`), `shell/rutas.ts` (quitar `MODULOS`,
  `ubicacion`, `en()`, `inicioDe`, `modulosVisibles`; conservar `PAGINAS`, `usable`, `paginaPorId`)
- Borrar (con sus pruebas y estilos): `shell/SidebarModulos.*`, `shell/AccesosDelModulo.*`, `shell/PanelDeArea.tsx`,
  `shell/SelectorObra.*`, `shell/Selectores.*`, `shell/BarraSuperior.*`, `shell/sidebar.*`, `shell/useFijadoPosible.*`,
  `shell/anchoBotonesBarra.test.ts` y lo que `npm run muerto` señale tras el cambio
- Mover: de `shell/Shell.tsx` a `marco/Marco.tsx` lo que sigue vigente (límite de error, diálogo de salida,
  marca de demostración, avisos, expiración de sesión)
- Mover (no borrar): `shell/_umbrales.scss` → `marco/_umbrales.scss`, porque lo usan `marco/BarraSuperior.scss` y
  `shell/ColumnaRecorrido.scss`. Se conservan `$umbrales-por-escala` y `por-debajo-del-umbral`; se quita
  `$umbrales-por-modulo` solo si su único usuario (`shell/shell.scss`) se borra en esta tarea. Actualizar los `@use`
  y la ruta que lee `estilos/estilosLetra.test.ts`.
- Prueba: `marco/Marco.test.tsx` (las pruebas de `Shell.test.tsx` que sigan aplicando se mueven aquí)

**Interfaces:**
- Consume: todo lo anterior.
- Produce: redirecciones de las rutas viejas: `#/inicio` y `#/` → `#/pendientes`; `#/<pagina>` de una sección de obra →
  la misma sección de la obra abierta en la sesión (o `#/pendientes` si no hay obra); `#/<pagina>` de Empresa →
  `#/empresa/<id de la entrada cuya pagina es esa>` (`#/catalogo` → `#/empresa/precios`, `#/administracion` →
  `#/empresa/personas`, `#/acerca` → `#/empresa/ayuda`, `#/existencias` → `#/empresa/produccion`); las demás
  pantallas sin sitio en el árbol (histórico, índices, simulador…) siguen en su ruta vieja y se alcanzan por Ctrl+K.
  `#/pendientes` muestra por ahora la página `obras` (la mesa actual) hasta F3.

- [ ] **Paso 1: pruebas rojas** en `Marco.test.tsx`:
  - `#/` y `#/inicio` acaban en `#/pendientes`; `#/hoja` con obra 3 abierta en «Carpeta Sur.db» acaba en
    `#/obra/Carpeta%20Sur.db/3/presupuesto`; `#/catalogo` acaba en `#/empresa/precios`; `#/simulador` sigue en
    `#/simulador` dentro del marco nuevo.
  - dentro de una sección se ve la cabecera de la obra (nombre, moneda, versión) y la página montada.
  - con cambios sin guardar en la Hoja, elegir otra obra en el árbol pide confirmar (reusa `sucio.ts`/`salida.ts`);
    «Cancelar» deja la ruta igual.
  - `en_otra_pestana` muestra «Esta obra se abrió en otra pestaña» y «Retomar»; mientras tanto la página no se monta.
  - `no_existe` muestra «Esa obra ya no existe» y un enlace a Pendientes.
  - ningún texto visible del marco contiene «módulo», «área» ni «Streamlit» (amplía `sinJergaInterna.test.ts`).
- [ ] **Paso 2:** FALLA.
- [ ] **Paso 3:** implementar el montaje, las redirecciones y el borrado; mover a `marco/` lo vigente de `Shell.tsx`.
- [ ] **Paso 4:** `npm test`, `npm run lint`, `npm run muerto`, `npm run duplicado` → todo en verde.
- [ ] **Paso 5:** `uv run --active pytest -q` → verde (cierre de fase).
- [ ] **Paso 6:** una sola pasada en navegador (1056, 1366, 1910 px; letra 1 y 1,5) con capturas en el scratchpad,
  con el tema de la empresa local, para que Eugenio lo vea. Las capturas no se versionan.
- [ ] **Paso 7:** bitácora del cierre de F2 con las líneas antes/después; CHANGELOG; **commit**.

---

## Fuera de esta tanda

F3 Pendientes (bandeja real y contadores), F4 secciones de la obra con rework visual, F5 Empresa, F6 Ayuda, F7 retiro
final y guardia completa anti-Streamlit. El inventario de botones (F1) se prepara en paralelo como documento para
Eugenio, sin agentes de código: `docs/rediseno/INVENTARIO.md`, una tabla por página con botón · qué hace · beneficio
para el usuario · destino (se queda / se fusiona / se mueve / se quita).
