# Rediseño del front, F3: bandeja de Pendientes y el marco como la maqueta (plan de implementación)

> **Para agentes:** SUB-SKILL REQUERIDA: superpowers:subagent-driven-development (recomendada) o
> superpowers:executing-plans, tarea por tarea. Los pasos usan casillas (`- [ ]`). Cada tarea termina con su árbitro
> (`MANUAL_ARBITRO.md`) antes de abrir la siguiente. **Agentes de uno en uno**; menores agrupados; navegador solo en
> la Tarea 5.

**Objetivo:** que Pendientes sea la bandeja de la maqueta aprobada (lista por urgencia a la izquierda, detalle con qué
hacer a la derecha, de todas las obras) y que el marco termine de parecerse a la maqueta: contadores en el árbol,
obras sin nombres técnicos de carpeta, color de acción de la empresa en vez del azul de Carbon y la cuenta con
iniciales.

**Arquitectura:** el servidor gana una ruta de lectura, `GET /v1/obras/pendientes/todas`, que corre las fuentes de
pendientes que ya existen (`aplicacion/mesa.py`, `FUENTES`) en cada carpeta visible, abierta en solo lectura, igual que
`GET /v1/obras/todas`. Así cubre lo que §8 bis pedía unir: la fuente «aprobar» de la mesa ya da, por carpeta, lo que
espera dictamen y lo devuelto, de modo que no hace falta mezclar en el front `/v1/obras/pendientes` con
`/v1/aprobaciones/pendientes`. El front gana la página `paginas/pendientes/` (la bandeja) y un hook común `usePendientes` que
leen la bandeja y la barra lateral. Resumen sigue montando la mesa actual hasta F4. Los colores salen de tokens: el
tema de la empresa reasigna los tokens interactivos de Carbon, sin sobrescribir componentes uno a uno.

**Stack:** React 19 + TypeScript + Carbon 11 (g10) + react-router 7 (HashRouter) + Vitest; FastAPI + SQLAlchemy +
pytest. Sin dependencias nuevas.

**Especificación:** [docs/especificaciones/2026-10-26-rediseno-marco-obras-design.md](../especificaciones/2026-10-26-rediseno-marco-obras-design.md)
(§2.1, §2.2, §2.7, §7 F3, §8 bis «Pendientes», §8 ter «Detalles visuales»). Diferencias con la maqueta:
`docs/bitacora/2026-10-27-cierre-f2-marco.md`, sección «Pendiente (F3 en adelante…)».

## Restricciones globales

Las de `PLAN_REDISENO_MARCO.md` siguen vigentes sin cambios (core intacto, marca de la empresa nunca al repo, es-VE con
coma decimal, 1056/1366/1910 px y letra 1/1,25/1,5, accesibilidad AA, vocabulario del usuario, 250 líneas por
componente, TDD con rojo visto, jscpd ≤ 1 %, commit por tarea con `git diff --cached --stat`). Además:

- `uv run --active` SIEMPRE (sin `--active` se crea un `.venv` dentro del worktree).
- Prohibido `--amend`, `reset`, `stash`, `rebase`, `push`, `git add -A`/`.`. Pie: `Co-Authored-By: Claude Sonnet 5.5
  <noreply@anthropic.com>` (u Opus si la tarea va con Opus).
- La API no cambia ninguna ruta existente; solo se añade la de la Tarea 1.

## Foco de revisión

1. **Cuenta que revisa sin `editar_hoja`** (rol «revisa»): ve solo lo que espera su dictamen, nunca «devuelta», precios
   ni calidad. Prueba en Tarea 1 (`alcance`) y Tarea 2 (la bandeja no ofrece acciones que darían 403).
2. **Carpeta ilegible o sin migrar** (base vieja sin tablas `mp_*`): sus pendientes no salen, la ruta da 200 y la
   bandeja dice «No se pudo leer 1 carpeta; sus pendientes no aparecen.»; nunca 503 ni bandeja en blanco. Prueba en
   Tareas 1 y 2.
3. **Pendiente de una obra de otra carpeta con la Hoja con cambios sin guardar**: el botón del detalle pasa por la
   confirmación de salida que ya existe (`shell/salida.ts`, `navegarSeguro`) antes de abrir la obra. Prueba en Tarea 2.
4. **Volver a Pendientes después de resolver algo**: la lista y los contadores se vuelven a pedir al entrar en
   `#/pendientes`; no queda el pendiente resuelto. Prueba en Tarea 2.
5. **Muchos pendientes** (200) a 1366 px: la lista se desplaza dentro de su columna, el detalle sigue a la vista y no
   hay desplazamiento horizontal. Prueba de estructura en Tarea 2; medida en navegador en Tarea 5.

## Decisiones por defecto (Eugenio puede cambiarlas; si no dice nada, se construye así)

- **D-F3-1 Urgencia por grupo:** «aprobar» y «compras» → **bloquea**; «precios» y «calidad» → **aviso**. Bloquea va
  primero. Dentro de cada urgencia: carpeta (la de la empresa primero, luego por nombre), grupo en el orden de `GRUPOS`
  y el orden de cada fuente. Las fuentes no dan fecha: «lo más antiguo arriba» (§8 bis) y la fecha visible de la
  maqueta quedan para cuando una fuente la tenga (no se inventa).
- **D-F3-2 Acción del pendiente → sección de la obra:** se deriva de `SECCIONES_DE_OBRA` y `ENTRADAS_DE_EMPRESA`
  (`hoja`→Presupuesto, `aprobar`→Aprobaciones, `mercado`→Mercado, `control`→Control, `catalogo`→Empresa › Precios y
  catálogo). Dos que aún no tienen sección propia van a la que las absorberá según §6.2: `actualizacion`→Mercado y
  `entregar`→Aprobaciones. Una página desconocida va al Resumen de la obra (nunca un enlace muerto).
- **D-F3-3 Árbol sin carpetas:** el árbol lista las obras por nombre, sin títulos de grupo por carpeta (§2.4: «la
  carpeta desaparece del uso diario»). Si dos obras se llaman igual, cada una muestra debajo, en letra secundaria, el
  nombre de su carpeta. El diálogo «Nueva obra» sigue diciendo dónde se creará.
- **D-F3-4 Color de acción** (superada por la Tarea 4b y luego por la 4c: la acción va en el complementario):
  botón principal con fondo `--silice-acento` y texto `--silice-marco`; enlaces, pestaña
  activa y bordes interactivos en `--silice-marco` (el ámbar sobre blanco da ~2,1:1 y no sirve para texto ni bordes).
  El foco visible se queda como está.
- **D-F3-5 Cuenta:** el botón de la cuenta es un círculo con las iniciales (fondo acento, texto marco) y conserva el
  nombre en su nombre accesible. **Los tres botones de tamaño de letra se quedan a la vista** en la barra (son la
  ayuda de presbicia; esconderlos en un menú la haría difícil de encontrar).

---

### Tarea 1: Pendientes de todas las carpetas (`GET /v1/obras/pendientes/todas`)

**Modelo:** Sonnet.

**Archivos:**
- Crear: `aplicacion/pendientes_todas.py`
- Modificar: `api/rutas/obras.py` (ruta nueva junto a `/todas`, reutiliza `_carpetas_visibles`)
- Prueba: `tests/unit/test_pendientes_todas.py` (lógica), `tests/unit/test_api_obras_pendientes_todas.py` (API)
- Registro: `docs/api.json` (truco de `git archive HEAD`), `CHANGELOG.md`, tabla de acceso por ruta
  (`tests/unit/test_api_acceso_por_ruta.py`) y guardias de clave si listan rutas.

**Interfaces:**
- Consume: `aplicacion.mesa.pendientes(sesion, hoy) -> list[GrupoPendientes]` (con `Pendiente.obra == str(id)`),
  `aplicacion.mesa.Siguiente`, `motor_solo_lectura` y `abrir_sesion` como en `obras_de_las_carpetas`, y
  `_carpetas_visibles(request, activa)` de `api/rutas/obras.py`.
- Produce:
  ```python
  Urgencia = Literal["bloquea", "aviso"]
  Alcance = Literal["todo", "por_aprobar"]
  URGENCIA_DEL_GRUPO: dict[str, Urgencia]  # D-F3-1

  @dataclass(frozen=True)
  class PendienteDeObra:
      carpeta: str | None   # el nombre con .db de /v1/obras/todas; None = la de la empresa
      obra_id: int
      obra: str             # nombre de la obra
      grupo: str            # clave de mesa.GRUPOS
      urgencia: Urgencia
      texto: str
      accion: Siguiente

  @dataclass(frozen=True)
  class PendientesDeTodas:
      items: tuple[PendienteDeObra, ...]
      carpetas_omitidas: int

  def pendientes_de_las_carpetas(
      carpetas: list[tuple[str | None, Path]], hoy: date, *, alcance: Alcance
  ) -> PendientesDeTodas
  ```
  `alcance="por_aprobar"` deja solo los de `accion.pagina == "aprobar"` («espera dictamen»).
  Ruta: `GET /v1/obras/pendientes/todas` → `{"pendientes": [{"carpeta": str|null, "obra_id": int, "obra": str,
  "grupo": str, "urgencia": "bloquea"|"aviso", "texto": str, "accion": {"texto": str, "pagina": str}}],
  "carpetas_omitidas": int}`. Permiso de la ruta: el de `/todas` (`LEER_PROYECTO`). Alcance: con `EDITAR_HOJA` →
  `"todo"`; si no, con `APROBAR_VERSION` → `"por_aprobar"`; si no → lista vacía. Carpetas: `_carpetas_visibles`.

- [ ] **Paso 1: pruebas rojas de la lógica** (`test_pendientes_todas.py`), con dos carpetas ficticias como en la
  Tarea 3 del plan de F2 («Carpeta Norte»: «Galpón», «Clínica»; «Carpeta Sur»: «Vialidad») y fuentes falsas puestas
  con `monkeypatch` sobre `aplicacion.mesa.FUENTES` (oráculo a mano):
  - `test_une_las_carpetas_y_pone_primero_lo_que_bloquea`: Norte/precios «Galpón: precios viejos», Sur/aprobar
    «V2 devuelta» → orden `[Sur·Vialidad·bloquea, Norte·Galpón·aviso]`.
  - `test_dentro_de_la_urgencia_carpeta_y_grupo`: dos «bloquea» de Norte (compras) y Sur (aprobar) → Norte primero.
  - `test_obra_id_y_nombre_de_la_obra`: `obra_id == 2` y `obra == "Galpón"` para un `Pendiente("2", "Galpón", …)`.
  - `test_carpeta_ilegible_se_omite_y_se_cuenta`: un `.db` corrupto → sus pendientes no salen, `carpetas_omitidas == 1`.
  - `test_alcance_por_aprobar_deja_solo_lo_que_espera_dictamen`.
  - `test_no_escribe`: la fecha de modificación de los `.db` no cambia y no aparecen `-wal`/`-shm`.
  - `test_con_las_fuentes_reales_una_devuelta_sale_como_bloquea` (sin `monkeypatch`, con un envío devuelto sembrado).
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_pendientes_todas.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar en `aplicacion/pendientes_todas.py`. Una carpeta que lanza `SQLAlchemyError` se omite,
  se cuenta y queda en el registro (como `obras_de_las_carpetas`). Sin aritmética nueva ni textos nuevos: el texto y
  la acción son los de la fuente.
- [ ] **Paso 4:** → PASA. **Commit** (`test(...)` antes, `feat(...)` después).
- [ ] **Paso 5: pruebas rojas de la API** (`test_api_obras_pendientes_todas.py`): forma de la respuesta; cuenta con
  `CAMBIAR_CASO` ve las dos carpetas y sin él solo la abierta; rol «revisa» solo «espera dictamen»; cuenta sin
  `EDITAR_HOJA` ni `APROBAR_VERSION` → `{"pendientes": [], "carpetas_omitidas": 0}`; carpeta ilegible → 200 con
  `carpetas_omitidas == 1`; sin sesión → 401; `Cache-Control: no-store`.
- [ ] **Paso 6:** → FALLA; implementar la ruta en `api/rutas/obras.py`, junto a `/todas` (el router no tiene rutas
  con parámetro, no hay choque); → PASA. `api.json`, CHANGELOG, tabla de acceso. **Commit.**

### Tarea 2: La bandeja de Pendientes

**Modelo:** Opus (pantalla nueva de entrada, foco y navegación entre carpetas).

**Archivos:**
- Crear: `frontend-desktop/src/marco/usePendientes.ts`, `frontend-desktop/src/paginas/pendientes/Bandeja.tsx`,
  `Bandeja.scss`, `logica.ts`, `Bandeja.test.tsx`, `logica.test.ts`; `frontend-desktop/src/api/tipos.ts` (tipos de la
  respuesta).
- Modificar: `frontend-desktop/src/marco/Marco.tsx` (`#/pendientes` monta la bandeja en vez de la mesa; el resultado
  de `usePendientes` viaja por el contexto del marco para que la barra lateral no pida otra vez),
  `frontend-desktop/src/marco/secciones.ts` (la derivación de D-F3-2, si cabe ahí mejor que en `logica.ts`).

**Interfaces:**
- Consume: `GET /v1/obras/pendientes/todas` (Tarea 1), `rutaDeObra`, `rutaDeEmpresa`, `SECCIONES_DE_OBRA`,
  `ENTRADAS_DE_EMPRESA` (`marco/secciones.ts`), `navegarSeguro` (`shell/navegarSeguro.ts`).
- Produce:
  ```ts
  export interface PendienteDeObra {
    carpeta: string | null; obra_id: number; obra: string; grupo: string;
    urgencia: "bloquea" | "aviso"; texto: string; accion: { texto: string; pagina: string };
  }
  export type EstadoPendientes =
    | { estado: "cargando" } | { estado: "error"; mensaje: string }
    | { estado: "listo"; pendientes: PendienteDeObra[]; carpetasOmitidas: number };
  export function usePendientes(): EstadoPendientes & { recargar: () => void };   // marco/usePendientes.ts
  export function destinoDelPendiente(p: PendienteDeObra): string;                // ruta del HashRouter (D-F3-2)
  export function contarPorObra(p: readonly PendienteDeObra[]): Map<string, number>; // clave `${carpeta ?? ""}|${obra_id}`
  ```
  `contarPorObra` y la clave las usa la Tarea 3.

- [ ] **Paso 1: pruebas rojas de la lógica** (`logica.test.ts`), una por fila de D-F3-2 (incluidas `actualizacion`,
  `entregar` y una página desconocida → Resumen) y `contarPorObra` con dos obras de carpetas distintas y el mismo id.
- [ ] **Paso 2: pruebas rojas de la bandeja** (`Bandeja.test.tsx`, con la respuesta simulada):
  - un solo `h1` «Pendientes» y el número total al lado («4 por hacer»);
  - la lista es una `ul` con un elemento por pendiente: texto, nombre de la obra y la urgencia en palabras («Bloquea» /
    «Aviso»; el color nunca va solo); el primero queda elegido al cargar;
  - elegir otro (clic, o flechas ↑/↓ con el foco en la lista) cambia el detalle; el detalle es una región con nombre
    «Detalle del pendiente» que muestra el texto, la obra y **un solo** botón principal con `accion.texto`;
  - el botón navega a `destinoDelPendiente` pasando por `navegarSeguro` (con la Hoja sucia, se ve el diálogo de salida
    y no se navega si se cancela);
  - lista vacía → «No tiene pendientes. Cuando una obra necesite algo de usted, aparecerá aquí.» (sin «Empieza
    aquí», que es de F6);
  - `carpetasOmitidas == 1` → aviso «No se pudo leer 1 carpeta; sus pendientes no aparecen.» (plural con 2);
  - error de la API → aviso con «Reintentar» que llama a `recargar`;
  - al volver a entrar en `#/pendientes` se pide otra vez (Foco de revisión 4);
  - estructura para el Foco 5: la columna de la lista tiene su propio desplazamiento (clase con `overflow-y: auto`
    probada con el patrón de `estilosMarco.test.ts`) y no hay ancho fijo mayor que la columna.
- [ ] **Paso 3:** `npx vitest run src/paginas/pendientes` → FALLA.
- [ ] **Paso 4:** implementar. Disposición a 1366: lista ~40 % a la izquierda, detalle a la derecha; a 1056 con letra
  1,5 la lista pasa arriba y el detalle debajo (umbral de `_umbrales.scss`, sin números nuevos). Carbon g10, esquinas
  rectas, sin animación. Textos en un catálogo `textos.ts` de la página (§6.4 «textos como datos»).
- [ ] **Paso 5:** → PASA; `npm run lint`; jscpd ≤ 1 %. **Commit** (`test` antes, `feat` después).

### Tarea 3: Contadores en la barra lateral y árbol sin carpetas

**Modelo:** Sonnet.

**Archivos:**
- Modificar: `frontend-desktop/src/marco/BarraLateral.tsx`, `BarraLateral.scss`, `BarraLateral.test.tsx`.
- Crear (solo si se usa en dos sitios, §6.4): `frontend-desktop/src/comun/Pildora.tsx`.

**Interfaces:**
- Consume: el estado de `usePendientes` por el contexto del marco y `contarPorObra` (Tarea 2).

- [ ] **Paso 1: pruebas rojas:**
  - «Pendientes» muestra una píldora con el total; con 0 no hay píldora; mientras carga o con error, tampoco (nunca
    un número falso). El nombre accesible del enlace es «Pendientes, 4 por hacer».
  - cada obra con pendientes muestra su píldora con su número (clave carpeta + id); la de 0, ninguna.
  - D-F3-3: con obras de dos carpetas no hay títulos de grupo por carpeta (`demo`, `of001`…); las obras salen por
    nombre; dos obras llamadas igual en carpetas distintas muestran debajo el nombre de su carpeta, y las demás no.
  - las pruebas del árbol que ya existen (`aria-level`, `aria-setsize`, foco, Nueva obra) siguen verdes; las que
    afirmaban los grupos por carpeta se reescriben a la regla nueva y el informe lo declara.
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar; píldora pequeña según §8 ter (no bloque). **Paso 4:** → PASA,
  lint. **Commit.**

### Tarea 4: Color de acción de la empresa y la cuenta con iniciales

**Modelo:** Sonnet.

**Archivos:**
- Modificar: `frontend-desktop/src/estilos/tokens.scss` o `marco/marco.scss` (reasignación de tokens de Carbon a los
  `--silice-*`), `frontend-desktop/src/shell/MenuCuenta.tsx`, `MenuCuenta.scss`, `MenuCuenta.test.tsx`,
  `frontend-desktop/src/marco/temaNeutro.test.ts` o `estilosMarco.test.ts`; servidor: el cálculo de avisos de
  contraste de `GET /v1/tema` (Tarea 1b de F2) y su prueba.

- [ ] **Paso 1: pruebas rojas:**
  - estilos (patrón de `estilosMarco.test.ts`): bajo el marco, `--cds-button-primary` = `var(--silice-acento)`,
    `--cds-text-on-color` del botón principal = `var(--silice-marco)`, `--cds-link-primary`,
    `--cds-border-interactive` y la raya de la pestaña activa = `var(--silice-marco)`; `--cds-focus` no se toca.
  - servidor: un tema con acento y marco por debajo de 4,5:1 entre sí (p. ej. `#F1C21B` con `#777777`) da el aviso
    «El texto de los botones principales no se lee bien: …» (redacción en la línea de los avisos de 1b); el tema
    neutro (`#F1C21B` con `#393939`, ≈6,9:1, calculado a mano con la fórmula WCAG) no da aviso. Valores ficticios:
    los de la empresa no se escriben en el repositorio.
  - el tema neutro del repositorio pasa los mismos umbrales (sin aviso).
  - cuenta: el botón muestra las iniciales de la persona («Ana Pérez» → «AP»; «Ana» → «A»; espacios de sobra no
    cuentan), su nombre accesible sigue siendo «Cuenta de Ana Pérez», y el menú sigue abriendo y cerrando con Esc.
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar; `TamanoLetra` no se mueve (D-F3-5). **Paso 4:** → PASA, lint,
  pytest del tema. **Commit.**

### Tarea 4b: Paleta elegida por Eugenio y resumen de la bandeja (decisiones del 2026-10-28)

**Modelo:** Sonnet.

Eugenio probó combinaciones en un explorador local y eligió una paleta para su empresa. Sus valores viven **solo** en
`data/tema/tema.json` (el orquestador los pone en local); el repositorio lleva valores neutros y las **reglas**:

- **Color complementario** (clave nueva `complementario` del tema, token `--silice-complementario`, neutro =
  `var(--silice-marco)`): enlaces (`--cds-link-primary`) y borde interactivo / raya de la pestaña activa
  (`--cds-border-interactive`). Reemplaza al marco en esos dos tokens de la Tarea 4.
- **Botón principal más claro y con borde** (regla genérica, en el repo): reposo = `color-mix(in srgb,
  var(--silice-acento) 55%, white)`; al pasar el ratón = acento 85 % con blanco; al pulsar = el acento puro; borde de
  1 px = acento 50 % con marco. El texto sigue en `--silice-marco`.
- **Contadores con colores propios** (claves nuevas `contador_numero` y `contador_fondo`, tokens
  `--silice-contador-numero` / `--silice-contador-fondo`, neutros = marco y lateral): la píldora pinta el número y un
  contorno de 1 px del color del número sobre su fondo; deja de usar acento y marco.
- **Avisos del servidor** (`aplicacion/tema.py`, `_PARES` y la medida de mezclas): el par «marco sobre acento» se
  sustituye por tres — texto del botón en reposo, al pasar el ratón y al pulsar —, cada uno con mínimo **7:1**
  (decisión de Eugenio: legibilidad para vista cansada); borde del botón sobre el fondo ≥ 3:1; complementario sobre
  el fondo, sobre blanco y sobre el lateral ≥ 4,5:1 (el par «marco sobre fondo» de la Tarea 4 pasa al complementario);
  número del contador sobre su fondo ≥ 4,5:1 y su contorno sobre el lateral ≥ 3:1. Las proporciones de mezcla (55 %,
  85 %, 50 %) están en **un solo sitio por lado** y una prueba comprueba que el SCSS y Python usan las mismas.
- **Bandeja** (Eugenio: «el 4 por hacer es muy sutil», «va así»): se quita «N por hacer» junto al h1; encima de la
  lista va un resumen por urgencia con las mismas etiquetas de la lista: «2 bloquean · 2 avisos» (singular «1
  bloquea», «1 aviso»; un grupo en cero no se nombra; lista vacía, sin resumen).

**Archivos:** `aplicacion/tema.py`, `api/rutas/tema.py` (si la respuesta gana claves), sus pruebas
(`tests/unit/test_tema_contraste.py`, `tests/unit/test_api_tema.py`), `frontend-desktop/src/marco/tema.ts` (+ prueba),
`frontend-desktop/src/estilos/tokens.scss`, `temaNeutro.test.ts`, `colorDeAccion.test.ts`, `cascadaDeAccion.test.ts`,
`frontend-desktop/src/comun/Pildora.scss` (+ prueba), `frontend-desktop/src/paginas/pendientes/` (Bandeja, textos,
pruebas), `docs/api.json` si cambia la API, `CHANGELOG.md`, `DESIGN.md`.

- [ ] **Paso 1: pruebas rojas** con oráculos a mano y **valores ficticios** (nunca los de la empresa): servidor (los
  tres estados del botón con 7:1, borde, complementario en tres fondos, contador, y que el tema neutro no avisa; un
  tema ficticio que falle cada par da su aviso exacto); front (`tema.ts` aplica las tres claves nuevas y rechaza lo
  que no es `#rrggbb`; cascada dentro y fuera de `.cds--g10` para enlace y pestaña con el complementario y para los
  tres estados y el borde del botón; píldora con los tokens del contador; resumen de la bandeja en sus casos).
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar. **Paso 4:** → PASA; pytest del tema, vitest de `src/marco
  src/estilos src/comun src/paginas/pendientes src/shell`, lint, build, duplicado, muerto. **Commits** (`test` antes de
  `feat`).

### Tarea 4c: La acción pasa al complementario; el acento queda para la marca (decisión del 2026-10-28)

**Modelo:** Sonnet.

En la pasada en navegador del cierre (hallazgo H3) Eugenio vio que el botón ámbar aclarado y los avisos amarillos de
Carbon se confunden («esto es lo que quiero evitar»). Decidió repartir los papeles: **amarillo = precaución** (los
avisos de Carbon se quedan como están), **ámbar = marca** (raya de la barra superior, logo, iniciales, selección) y
**complementario = acción**. Sus valores siguen **solo** en `data/tema/tema.json` (ya puestos en local por el
orquestador); el repositorio lleva las reglas y valores neutros. Sustituye el botón de la Tarea 4b y la D-F3-4.

- **Botón principal en el complementario con texto blanco** (regla genérica, en el repo): reposo =
  `var(--silice-complementario)`; al pasar el ratón = `color-mix(in srgb, var(--silice-complementario) 85%, black)`;
  al pulsar = complementario 70 % con negro. El texto vuelve al blanco de Carbon (`--cds-text-on-color` deja de
  reasignarse dentro del botón principal). Sin borde propio: el fondo oscuro ya se distingue del fondo de la página.
  «Nueva obra» (`.silice-marco-boton-principal`) sigue la misma regla y los mismos tres estados.
- **Se quita la regla de la Tarea 4b** (YAGNI): `$mezcla-reposo/-hover/-borde`, `--silice-boton-borde` y sus usos,
  `MEZCLAS` de `aplicacion/tema.py` y la prueba que compara las dos copias. Las nuevas proporciones (85 y 70 con
  negro) quedan, como antes, en **un solo sitio por lado** y la prueba de coincidencia SCSS/Python se reescribe para
  ellas.
- **Avisos del servidor** (`_PARES`): fuera los tres pares «marco sobre botón» y el borde del botón; entran «blanco
  sobre el botón» en reposo, al pasar el ratón y al pulsar, cada uno con mínimo **7:1** (misma frase que hoy para cada
  estado). Se quedan los del complementario sobre fondo, blanco y lateral (4,5:1) y los del contador. Las iniciales
  de la cuenta (texto marco sobre acento) pasan a un par propio de texto, 4,5:1: «Las iniciales de la cuenta no se
  leen bien sobre el color de acento».
- **El acento solo como marca**: revisar cada uso de `--silice-acento` y de `--cds-button-primary` en `src/`; ninguno
  puede quedar como relleno de una acción. Se listan en la bitácora con su papel.
- **DESIGN.md** (`frontend-desktop/DESIGN.md`): una sección «Papeles del color» con el reparto de arriba y la regla de
  identidad: el acento nunca va solo como identidad, siempre junto al marco y al complementario (el ámbar solo es
  genérico del sector). Se corrige lo que DESIGN.md diga hoy del botón aclarado.
- El acento neutro del repo (yellow-20) **no se cambia** en esta tarea.

**Archivos:** `frontend-desktop/src/estilos/tokens.scss`, `marco/BarraLateral.scss`, `marco/colorDeAccion.test.ts`,
`marco/temaNeutro.test.ts`, `estilos/cascadaDeAccion.test.ts`, `aplicacion/tema.py`, `tests/unit/test_tema_contraste.py`,
`tests/unit/test_api_tema.py` (si fija avisos), `frontend-desktop/DESIGN.md`, `CHANGELOG.md`, bitácora del cierre de F3.

- [ ] **Paso 1: pruebas rojas** con oráculos calculados a mano con la fórmula WCAG y **valores ficticios** (nunca los
  de la empresa): servidor (tema neutro sin avisos; un complementario ficticio claro que deja el blanco por debajo de
  7:1 en reposo da exactamente ese aviso; uno que solo falla al pasar el ratón no puede existir —oscurecer sube el
  contraste con blanco—, así que se prueba que el aviso de cada estado sale cuando corresponde; iniciales por debajo
  de 4,5:1 dan su aviso; los avisos de borde y de «marco sobre botón» ya no salen nunca); front (cascada dentro y fuera
  de `.cds--g10`: los tres estados del botón con el complementario y el texto blanco; `--silice-boton-borde` ya no
  existe; «Nueva obra» con los mismos tokens; coincidencia de proporciones SCSS/Python).
- [ ] **Paso 2:** → FALLA. **Paso 3:** implementar. **Paso 4:** → PASA; pytest del tema, vitest de `src/marco
  src/estilos src/comun src/shell src/paginas/pendientes`, lint, build, duplicado, muerto. **Commits** (`test` antes de
  `feat`).

### Tarea 5: Cierre de F3

**Modelo:** Sonnet para los menores; el orquestador corre la suite y el navegador.

- [ ] **Paso 1:** un solo agente cierra los menores que dejen los árbitros de las Tareas 1-4 y los pendientes sueltos
  anotados en la memoria (los 4 del árbitro de los menores del plan de decisiones), con su árbitro.
- [ ] **Paso 2:** suite completa: `uv run --active pytest -q -W error -p no:cacheprovider`, `npm test`,
  `npm run lint`. Las fallas que ya estaban antes se listan aparte, con su causa.
- [ ] **Paso 3:** **única pasada en navegador** (perfil propio en el scratchpad, servidor en `127.0.0.1`, obras
  ficticias, tema neutro y, en local, el de la empresa), a 1056/1366/1910 con letra 1 y 1,5: Pendientes con lista y
  detalle, el árbol con contadores, una obra en Presupuesto. Se compara con la maqueta aprobada y se comprueba:
  - si la franja gris que se vio encima de la barra superior en las capturas de T8 es del programa o de la captura
    (si es del programa, se arregla con su prueba);
  - que la celda del objetivo convertido de D3b no provoque desplazamiento horizontal a 1366;
  - que no haya desplazamiento horizontal en ninguna vista.
  Las capturas con el tema de la empresa se quedan en el scratchpad (nunca al repo).
- [ ] **Paso 4:** bitácora `docs/bitacora/<fecha>-cierre-f3.md` (qué se hizo, capturas citadas por nombre,
  pendientes para F4), CHANGELOG. **Commit.**

## Fuera de esta tanda

F4 la obra (Resumen, Presupuesto y la franja «Te falta», Archivos y planos, Versiones), F5 Empresa, F6 Ayuda («Empieza
aquí» en la bandeja vacía de una cuenta nueva), F7 retiro final. Filtros de la bandeja («Todas las obras», «Urgentes
primero») y fecha por pendiente: cuando una fuente dé la fecha y el inventario lo justifique.
