# Sílice por módulos: plan de construcción

> **Para agentes:** SUB-SKILL OBLIGATORIA: superpowers:subagent-driven-development (implementador → árbitro por tarea, como
> mandan `docs/planes/MANUAL_SUBAGENTES_MIGRACION.md` y `docs/planes/MANUAL_ARBITRO.md`). Los pasos usan casillas (`- [ ]`).

**Meta:** que Sílice funcione como tres módulos (Auditoría, Presupuestos y obras, Producción) elegidos desde un sidebar oscuro que
se abre con «Sílice» o Esc, cada uno con su barra, su inicio y sus pantallas; obra en vez de carpeta en la barra; y la mesa de
control como inicio de Presupuestos y obras.

**Arquitectura:** a qué módulo y área pertenece cada pantalla vive solo en `src/shell/rutas.ts`; qué ve cada cuenta lo decide
`src/shell/navegacion.ts` (puro); el sidebar, la barra y la confirmación al salir son componentes del armazón (`src/shell/`). Las
preferencias por cuenta (último módulo, fijado, carpeta y obra) viven en `instalacion.db` (`mp_eleccion`). Las cifras y pendientes
de la mesa los calcula `aplicacion/mesa.py` (Decimal) y los sirve `api/rutas/obras.py`; el front solo formatea.

**Tecnología:** Python 3 + SQLAlchemy 2 + Alembic + FastAPI (`uv run --active`); React 19 + TypeScript + `@carbon/react` 1.117.0 +
`react-router` 7 (HashRouter) + Vitest/Testing Library; Playwright para Python (`uv run --active --with playwright`).

**Diseño:** `docs/especificaciones/2026-10-25-modulos-design.md` (APROBADO; **§12 manda sobre §1-§11**). Contexto:
`2026-10-25-barra-superior-design.md` (barra ya construida), `2026-10-25-montar-presupuesto-design.md` y su plan
`docs/planes/PLAN_MONTAR_PRESUPUESTO.md` (este plan le agrega al final «Cambios por el diseño de módulos (2026-10-25)»),
`2026-10-21-bienvenida-casos-proyectos-design.md` (BCP-5 §4.2-4.7, BCP-6 §5, pruebas F5-F11). El ejecutor lee el diseño y este plan.

## Choques del diseño con el código (verificados; propuesta en cada uno)

1. **Dependencias de MOD-3 (§10 dice «MOD-1, MP-2»).** §12.1 adelanta la Tarea 5 del plan de montar (tabla `mp_eleccion`) a MOD-0,
   y la parte de front de MP-2 (T6 carpetas BCP-5, T7 nuevo proyecto BCP-6) la absorbe MOD-3. *Propuesta:* MOD-3 depende de MOD-0,
   MOD-2 (confirmación) y de **MP T1 y T2** (moneda de la carpeta: `PUT /v1/carpeta/moneda` al crear carpeta, `GET /v1/carpeta`
   para proponer la moneda de la obra). T1 y T2 se adelantan a las olas M1 y M2. T6 y T7 quedan retiradas del plan de montar.
2. **La mesa necesita la moneda de la carpeta y la lista para armar** (`moneda_de_la_carpeta`, `describir` de MP T1), que §8
   pone «después» del armazón. Mismo arreglo: T1 va en la ola M1.
3. **`mp_eleccion.caso` era NOT NULL (T5)**: el módulo y el fijado se guardan antes de elegir carpeta. *Propuesta:* `caso` nulo
   (`NULL` = la carpeta por omisión de la instalación).
4. **No hay forma de «Volver a la carpeta de la empresa»:** la carpeta por omisión es la del proceso (`APU_BASE`), que puede no
   estar en `listar_casos()`, así que `POST /v1/casos/actual` no la acepta; `GET /v1/casos` no dice cuál es ni si la actual es la
   demostración (solo `GET /v1/casos/actual` trae `es_demostracion`). *Propuesta (MOD-3a):* `DELETE /v1/casos/actual` y dos campos
   nuevos en `GET /v1/casos`.
5. **«22 pantallas» (§9):** `inicio` deja de ser pantalla (redirige) y nacen tres inicios: 21 + 3 = **24 rutas** (26 con «Estudio
   de mercado» y «Aprobar una versión» del plan de montar). El recorrido funcional cambia su fila `inicio` por tres.
6. **`src/paginas/inicio/` es una carpeta compartida:** 15 pantallas importan `../inicio/useCarga` y `historial` usa
   `UltimasAuditorias`. *Propuesta:* la carpeta se queda; solo salen `index.tsx` e `Inicio.test.tsx` (pasan a `paginas/auditoria/` y
   `paginas/produccion/`).
7. **Los tres mosaicos de «Herramientas principales»** (`HERRAMIENTAS_PRINCIPALES`, `herramientasVisibles`, Inicio actual) existían
   porque las herramientas salieron de la navegación; con el sidebar sobran y son «tres tarjetas iguales». *Propuesta:* se retiran
   en MOD-1 (**decisión para Eugenio**, al final).
8. **Área de una sola pantalla:** `navegacion.ts` rotula el enlace con el título de la pantalla («Existencias de la arenera»); §3 y
   §12.4 nombran áreas («Auditar», «Paquetes», «Existencias») y el umbral de la barra se fija por número de áreas. *Propuesta:* el
   enlace lleva el **título del área** (rita ve «Obras» que abre el Tablero); el título de la pantalla queda en su h1.
9. **Esc hoy:** `Shell.tsx:147-157` escucha Esc en captura solo para la capa; `BarraSuperior` y `useDespliegue` hacen
   `stopPropagation` en React; la Hoja (`CampoDeCelda`, `TablaEditable`, `useDialogo`) y `Cuentas` manejan Esc sin detenerlo.
   *Propuesta:* un oyente de Esc en `document` (fase de burbuja) que ignora lo que vino de un campo, una tabla editable, un diálogo
   o un control desplegable (regla exacta en MOD-2).
10. **Azul de selección sobre `$background-inverse`:** `$border-interactive` (azul 60) sobre gris 80 da ~2,2:1 (< 3:1). *Propuesta:*
    la barra de selección del módulo activo usa `$link-inverse` (azul 40, ≥ 3:1) y además `aria-current` y seminegrita.
11. **El administrador no tiene `leer_proyecto`:** las dos rutas de la mesa le dan 403 y su inicio de Presupuestos y obras quedaría
    vacío. *Propuesta (§12.3, «lo de Mercado que administra»):* ve la lista de accesos de su módulo (Precios de la empresa, Índices
    del BCV) con su línea de ayuda.
12. **«Avance contra el plan … y los días» (§6):** el núcleo ya calcula el retraso por obra (`reproyeccion.termino −
    estado.dias_plan`, `core/budget/valor_ganado.py:846`). *Propuesta:* la cifra lleva debajo «N obra(s) atrasada(s); la más
    atrasada, X: d días hábiles».
13. **264 px fijos con letra Muy grande** dejarían los nombres en tres renglones. *Propuesta:* `calc(264px *
    var(--silice-escala-letra))`, coherente con el umbral escalado de §12.8.

## Restricciones globales

- `core/` intacto (`git diff <base>..HEAD -- core/` vacío). `seguridad/permisos.py` intacto en este plan (**los permisos no
  cambian**, §12.2). Árbol único `.worktrees/s2madm`, rama `inc/ruta-s2-mig-adm-empresa`; sin `git worktree add`, sin `.venv` ni
  `node_modules` nuevos, sin `npm install`, sin cambiar `package.json`; `uv run --active`.
- **Rutas:** las `#/<id>` existentes no cambian; nuevas `#/auditoria`, `#/obras`, `#/produccion`; `#/` y `#/inicio` redirigen al
  inicio del último módulo usado (o del primero visible).
- **Módulos, en este orden:** Auditoría («Revise presupuestos propios o de terceros»: Inicio · Auditar · Paquetes · Historial),
  Presupuestos y obras («Arme, apruebe y controle sus obras»: Inicio · Obras · Partidas · Mercado · Aprobaciones · Control),
  Producción («Existencias y báscula de la arenera»: Inicio · Existencias). Administración y Acerca de Sílice, fuera de los módulos,
  al pie del sidebar.
- **Visibilidad:** un área aparece si la cuenta puede usar al menos una de sus pantallas; un módulo, si puede usar al menos una
  pantalla **que no sea su inicio**; cada inicio exige que su módulo sea visible. Ninguna pantalla se pierde ni sale dos veces.
- **Sidebar:** oculto por omisión, encima del contenido con capa (`$overlay`) bajo la barra (que ocupa todo el ancho); fijado =
  franja de `calc(264px * var(--silice-escala-letra))` que **empuja**; fijado posible solo desde **1366 px (Normal), 1708 px
  (Grande), 2049 px (Muy grande)** (1366 × 1,25 y × 1,5); por debajo se comporta como oculto. Superficie `$background-inverse`, texto
  `$text-inverse`, sin animación, esquinas rectas.
- **Mesa:** columna de pendientes de **380 px**; tabla Carbon `sm`; «más de 90 días»; «Por aprobar» se marca desde **3 días
  hábiles**; «atrasada» si SPI < `ParametrosControl.spi_error` de la obra (0,90 por omisión).
- Dinero y cantidades: `Decimal` en Python, **texto** en la API (punto decimal), nunca `float`; el front no calcula ni redondea
  montos (`formatoEsVe`, `centesimasEsVe`, `fechaEsVe`); sin `Number()` sobre montos.
- **Front (cada tarea de front lo cumple y el árbitro lo juzga con D1/D2):** `frontend-desktop/DESIGN.md` y `PRODUCT.md` (Carbon g10,
  IBM Plex, esquinas rectas, densidad `sm`, sin sombras ni gradientes, azul solo en acción/foco/selección, sin morado, **sin
  animación**, un h1 `heading-04` por página, h2 `heading-compact-02`, 1366×768 y 1056 px sin desplazamiento horizontal con las tres
  letras) y las **reglas anti-«hecho por IA»**: ninguna cifra inventada (todo número sale de la API o de un oráculo a mano), nada de
  tres tarjetas iguales, cada bloque con sus estados vacío (que enseña qué hacer), carga (esqueleto con la forma final) y error
  (aviso en línea con el `detalle` de la API), textos revisados (español con tildes, lenguaje llano, «obra» y «carpeta de trabajo»
  en la interfaz —la API conserva `proyecto` y `caso`—, sin jerga UC-xx/RF-xx/MOD-x, sin rayas de adorno).
- **Migraciones (encajan con el plan de montar):** instalación `ins_0004_mod_eleccion` (MOD-0, `down_revision =
  "ins_0003_auditoria_libro"`; reemplaza a `ins_0004_mp_eleccion`); caso `caso_0011_mod_ficha_obra` (MOD-3a, `down_revision =
  "caso_0010_mp_carpeta"`). Las de caso del plan de montar desde la 0011 suben un número (tabla en su sección nueva).
- Tablas nuevas en módulos `aplicacion/tablas_*.py` con su `MetaData` propio, sin clave foránea a `core.models`, migración con
  `_faltan(...)` como `migraciones/caso/versions/caso_0009_s3_paquete.py:25`.
- **Archivos compartidos (solo el orquestador, con el texto exacto que entrega el implementador):** `frontend-desktop/src/shell/rutas.ts`
  y `rutas.test.ts`, `api/main.py`, `tests/unit/test_api_acceso_por_ruta.py` (`TABLA`), `tests/unit/test_arquitectura.py`,
  `migraciones/metadatos.py` y `tests/unit/test_migraciones_metadatos.py`, los pinos de cabeza `ins_0003_auditoria_libro`
  (`tests/integration/test_migraciones.py:274,296`, `test_migracion_instalacion.py:41`, `test_migracion_produccion.py:49,88,91`,
  `test_migracion_auditoria_libro.py:72,139,142`, `test_preparar_base.py:251`, `test_respaldo.py:101`), `aplicacion/mesa.py::FUENTES`
  (una línea por fuente que agreguen tareas posteriores), `docs/api.json` (`scripts/exportar_openapi.py`), `CHANGELOG.md`,
  `docs/ERS.md`, `frontend-desktop/DESIGN.md` (solo MOD-5).
- Datos ficticios en todo lo versionado («Contratista Demo, C.A.», «Casa Demo», «Torre B», OB-S2 de `tests/fixtures/control_ob_s2.py`).
- TDD con rojo visto; prueba e implementación en commits separados (`test(...)… (rojo)` y luego `feat(...)`); asunto sin tildes;
  `git add <rutas propias>` y `git commit <rutas> -m ...`; trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` (o el
  modelo del implementador). Python con `-q -W error -p no:cacheprovider`; front `cd frontend-desktop && npx vitest run <ruta>`,
  `npm run lint`, `npm run build`. Sin push ni PR. Otros agentes trabajan en el árbol a la vez (regla de la coma decimal): nadie
  toca archivos fuera de su lista.

## Foco de revisión

Lo que más probablemente le pase a una persona; cada línea tiene su prueba en la tarea dueña:

1. **Perderse sin saber en qué módulo está:** entra por un marcador a `#/componer` con «Auditoría» como último módulo, o abre
   Administración → la barra dice «Presupuestos y obras» (o el último módulo, fuera de los módulos), el sidebar marca ese módulo con
   `aria-current` y la preferencia se actualiza (MOD-1 `moduloDeRuta`, MOD-2 sidebar).
2. **Esc que cierra o abre mal:** Esc escribiendo en un campo, editando una celda de la Hoja, con un `ComboBox` o un diálogo
   abiertos → no abre el sidebar; con un panel de área abierto → cierra solo el panel; con el recorrido activo → el recorrido sigue;
   con el sidebar en capa → lo cierra y el foco vuelve a «Sílice» (MOD-2).
3. **Trabajo perdido al cambiar de módulo:** Componer a medio llenar y clic en otro módulo, en un área de la barra, en un botón de
   la mesa, en «Cambiar carpeta…» o en «Probar con datos de demostración» → pide confirmación y «Quedarme» no navega; volver a la
   misma pantalla no pregunta; atrás/adelante del navegador no se intercepta (declarado, §12.5) (MOD-2, MOD-3b, MOD-4b).
4. **Rol que pierde una pantalla:** para ana, rita, admin y ana en modo entrega, la unión de las entradas de sus módulos más el
   pie del sidebar es **exactamente** su conjunto de pantallas visibles, cada una una vez; el último módulo guardado que ya no es
   visible cae al primero visible (MOD-1).
5. **Cifras sin meta o mal sumadas:** dos obras en Bs y una en USD con y sin tasa del BCV, ΣPV = 0, obra en ejecución sin
   valuaciones, un bloque con 403 → cada cifra lleva valor, meta y desviación calculados a mano; lo que no se puede sumar se
   muestra aparte; un 403 oculta el bloque, nunca lo pinta vacío (MOD-4a, MOD-4b).

---

## Orden y paralelismo

| Ola | Tareas (‖ = a la vez) | Archivos propios que no se cruzan |
|---|---|---|
| M1 | MOD-0 ‖ MP T1 ‖ MP T10 | MOD-0 `aplicacion/{tablas_eleccion,eleccion}.py`, `api/rutas/sesion.py`, `api/rutas/casos.py:118-144`, `src/api/tipos.ts`, `src/sesion/useSesion.ts`; T1 y T10 según su plan |
| M2 | MOD-1 ‖ MP T2 | MOD-1 `src/shell/{navegacion,BarraSuperior,Shell,recorrido}.*`, `src/paginas/{auditoria,obras,produccion}/**`, `src/paginas/inicio/index.tsx` (borrar); T2 `api/rutas/carpeta.py` |
| M3 | MOD-2 ‖ MOD-3a ‖ MOD-4a | MOD-2 `src/shell/{sidebar,sucio,salida,preferencias,useFijadoPosible}.ts`, `SidebarModulos*`, `DialogoSalida*`, `EnlaceSeguro.tsx`, `PanelDeArea.tsx`, `_umbrales.scss`, `shell.scss`, `MenuEnCapa*` (borrar), `BarraSuperior*`, `Shell.tsx`; MOD-3a `aplicacion/{tablas_obra,obras}.py`, `api/rutas/proyectos.py`, `api/rutas/casos.py` (rutas nuevas); MOD-4a `aplicacion/mesa.py`, `api/rutas/obras.py` |
| M4 | MOD-3b | `src/shell/{SelectorObra,MarcaDemostracion}*`, `src/shell/carpetas/**`, `src/shell/obras/**`, `Shell.tsx`, `contexto.tsx`, `Selectores.tsx`, `PanelCarpetaProyecto*` (borrar), `src/paginas/administracion/{index,CarpetasDeTrabajo}*`, una línea de `src/paginas/hoja/index.tsx` |
| M5 | MOD-4b | `src/paginas/obras/**` |
| M6 | MOD-5 | `scripts/recorrido_ux_playwright.py`, `scripts/recorrido_funcional.toml`, `frontend-desktop/DESIGN.md` (compartido), bitácora, manual |

Dependencias: MOD-1←MOD-0; MOD-2←MOD-1; MOD-3a←MOD-0, MP T1; MOD-3b←MOD-2, MOD-3a, MP T2; MOD-4a←MP T1; MOD-4b←MOD-3b, MOD-4a;
MOD-5←todas. MOD-1 y MOD-2 se integran juntas (entre las dos el cambio de módulo solo existe por dirección; no se le entrega a
Eugenio ese estado intermedio). Después de M6 sigue el plan de montar con los cambios de su sección final.

---

### Tarea MOD-0: Preferencias y elección por cuenta (backend)

**Archivos:**
- Crear: `aplicacion/tablas_eleccion.py`, `aplicacion/eleccion.py`, `migraciones/instalacion/versions/ins_0004_mod_eleccion.py`
- Modificar: `api/rutas/sesion.py` (`_cuerpo` :121 restaura y devuelve; rutas nuevas), `api/rutas/casos.py:129-145` (`elegir_caso`
  recuerda la carpeta), `frontend-desktop/src/api/tipos.ts` (`SesionRespuesta`), `frontend-desktop/src/sesion/useSesion.ts`
  (normaliza los campos nuevos)
- Prueba: `tests/unit/test_api_eleccion.py`, `tests/integration/test_migracion_eleccion.py`, ajuste en
  `frontend-desktop/src/sesion/useSesion.test.tsx`
- Compartidos: `METADATAS_INSTALACION` (`migraciones/metadatos.py`) y su prueba, pinos de cabeza → `ins_0004_mod_eleccion`,
  `TABLA` (dos filas), `docs/api.json`, `CHANGELOG.md`

**Interfaces:**
- Tabla `mp_eleccion` (instalación): `usuario_id Integer PK`, `caso String(255) NULL`, `proyecto String(120) NULL`,
  `modulo String(20) NULL`, `sidebar_fijado Boolean NOT NULL default false`, `fecha DateTime`.
- `aplicacion/eleccion.py`:
  ```python
  MODULOS = ("auditoria", "obras", "produccion")
  MENSAJE_MODULO = "Ese módulo no existe."
  @dataclass(frozen=True) class Eleccion: caso: str | None; proyecto: str | None; modulo: str | None; sidebar_fijado: bool
  def eleccion_de(sesion_ins: Session, usuario_id: int) -> Eleccion | None
  def recordar_caso(sesion_ins: Session, usuario_id: int, caso: str | None, ahora: datetime) -> None      # borra el proyecto
  def recordar_proyecto(sesion_ins: Session, usuario_id: int, proyecto: str | None, ahora: datetime) -> None
  def recordar_preferencias(sesion_ins: Session, usuario_id: int, *, modulo: str | None = None,
                            sidebar_fijado: bool | None = None, ahora: datetime) -> None   # None = no cambia; ValueError(MENSAJE_MODULO)
  ```
- `POST /v1/sesion` y `GET /v1/sesion` (vía `_cuerpo`) agregan `eleccion: {caso: str|null, proyecto: str|null, aviso: str|null}`
  y `preferencias: {modulo: str|null, sidebar_fijado: bool}`. Si `caso_web.elegido(huella)` es `None` y la elección recordada está en
  `listar_casos()`, hacen `caso_web.fijar`. Carpeta recordada que ya no existe → `caso: null` y `aviso` = «La carpeta de trabajo
  «{x}» ya no existe; se abrió la de siempre.» (`x` sin `.db`); obra que ya no existe en la carpeta → `proyecto: null`. Con contraseña
  temporal: `eleccion: null`, `preferencias: {modulo: null, sidebar_fijado: false}`.
- `PUT /v1/sesion/proyecto` (sesión completa, CSRF) cuerpo `{proyecto: str|null}` → 204.
- `PUT /v1/sesion/preferencias` (solo sesión completa con `exigir_sesion`, CSRF; la clave de API no tiene cuenta a la que
  recordar) cuerpo `{modulo?: str|null, sidebar_fijado?: bool}` → 204; 422 `MENSAJE_MODULO` sin repetir lo enviado (`RutaSinEco`).
- `SesionRespuesta` (front) gana `eleccion: { caso: string | null; proyecto: string | null; aviso: string | null } | null` y
  `preferencias: { modulo: "auditoria" | "obras" | "produccion" | null; sidebar_fijado: boolean }`; `useSesion` los normaliza a
  `null` / `{modulo: null, sidebar_fijado: false}` si la API no los trae.

- [ ] **Paso 1: pruebas en rojo** (`tests/unit/test_api_eleccion.py`, `con_cuenta`/`protegida` de `tests/fixtures/sesion_web.py`;
  carpetas `s1.db` y `s2.db` ficticias):
  - ana elige `s1.db` (`POST /v1/casos/actual`) y la obra `"7"` (`PUT /v1/sesion/proyecto`), sale y entra → la respuesta de
    `POST /v1/sesion` y la de `GET /v1/sesion` traen `eleccion == {"caso": "s1.db", "proyecto": "7", "aviso": None}` y
    `GET /v1/casos` dice `actual.nombre == "s1.db"` sin elegir de nuevo;
  - **reinicio de la API:** `caso_web.olvidar_todo()` + `dependencias.cerrar_motores()` con la misma ficha → `GET /v1/sesion`
    restaura `s1.db`;
  - se borra `s1.db` entre sesiones → `eleccion == {"caso": None, "proyecto": None, "aviso": "La carpeta de trabajo «s1» ya no
    existe; se abrió la de siempre."}`; ningún 500;
  - elegir `s2.db` borra la obra recordada (`proyecto: None`);
  - ana `PUT /v1/sesion/preferencias {"modulo": "obras", "sidebar_fijado": true}` → 204; `GET` → `preferencias == {"modulo":
    "obras", "sidebar_fijado": True}`; luego `{"sidebar_fijado": false}` → `{"modulo": "obras", "sidebar_fijado": False}` (el módulo
    no cambia);
  - `{"modulo": "tablero"}` → 422 con `MENSAJE_MODULO` y el cuerpo de la respuesta no contiene `"tablero"`;
  - rita guarda `{"modulo": "auditoria"}` y ana sigue con `"obras"` (por cuenta); admin sin preferencias → `{"modulo": None,
    "sidebar_fijado": False}`;
  - sin CSRF → 403 en las dos `PUT`; con contraseña temporal → `eleccion is None`.
  - `tests/integration/test_migracion_eleccion.py`: `upgrade` hasta `ins_0004_mod_eleccion` crea `mp_eleccion` con esas columnas
    (`caso` nulo); `downgrade` a `ins_0003_auditoria_libro` la quita; correr `upgrade` dos veces no falla (`_faltan`).
  - `useSesion.test.tsx`: una respuesta sin `eleccion` ni `preferencias` queda con `eleccion: null` y `preferencias: {modulo: null,
    sidebar_fijado: false}`.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_eleccion.py tests/integration/test_migracion_eleccion.py -q -W error
  -p no:cacheprovider` y `cd frontend-desktop && npx vitest run src/sesion/useSesion.test.tsx` → FALLAN (módulo y campos inexistentes).
- [ ] **Paso 3:** implementar (escritura en instalación con `sesion_instalacion_api()`, una transacción por petición; `PUT` con
  `exigir_sesion`).
- [ ] **Paso 4:** mismas órdenes + `tests/unit/test_api_casos.py tests/unit/test_api_sesion_web.py tests/unit/test_api_primer_arranque.py`
  y, con lo compartido aplicado por el orquestador, `tests/integration/test_migraciones.py tests/unit/test_api_acceso_por_ruta.py`
  → PASAN; `uv run --active ruff check` de lo tocado limpio.
- [ ] **Paso 5:** commits `test(api): eleccion y preferencias por cuenta (rojo)` / `feat(api): eleccion y preferencias por cuenta`.

### Tarea MOD-1: Registro por módulos, navegación por módulo e inicios

**Archivos:**
- Compartidos (los aplica el orquestador con el texto del implementador, antes del paso 2): `frontend-desktop/src/shell/rutas.ts`,
  `rutas.test.ts`
- Modificar: `src/shell/navegacion.ts`, `src/shell/BarraSuperior.tsx` (nombre del módulo; props), `src/shell/Shell.tsx` (redirecciones,
  módulo actual, preferencia), `src/shell/contexto.tsx` (`modulo`), `src/shell/recorrido.ts` (paso 1 en `auditoria`),
  `src/shell/MenuEnCapa.tsx` (recibe las entradas del módulo; se borra en MOD-2)
- Crear: `src/paginas/auditoria/index.tsx` (lo de auditar del Inicio actual: soltar el Excel, recorrido, últimas auditorías),
  `src/paginas/produccion/index.tsx` (`PanelArenera` de `../inicio/PanelArenera`), `src/paginas/obras/index.tsx` (h1 y accesos;
  MOD-4b le agrega la mesa), `src/shell/AccesosDelModulo.tsx`
- Borrar: `src/paginas/inicio/index.tsx`, `src/paginas/inicio/Inicio.test.tsx` (su contenido útil pasa a las pruebas nuevas)
- Prueba: `src/shell/navegacion.test.ts`, `src/shell/BarraSuperior.test.tsx`, `src/shell/Shell.test.tsx`, `src/App.test.tsx`,
  `src/shell/recorrido.test.tsx`, `src/shell/titulos.test.tsx`, `src/paginas/auditoria/Auditoria.test.tsx`,
  `src/paginas/produccion/Produccion.test.tsx`, `src/paginas/obras/Obras.test.tsx`

**Interfaces:**
- `rutas.ts`:
  ```ts
  export type ModuloId = "auditoria" | "obras" | "produccion";
  export interface AreaDef { id: string; titulo: string }
  export interface ModuloDef { id: ModuloId; titulo: string; enUnaLinea: string; areas: readonly AreaDef[] }
  export const MODULOS: readonly ModuloDef[];          // orden y textos de «Restricciones globales»
  // PaginaDef gana: ubicacion: { modulo: ModuloId; area: string } | null   (null = fuera de los módulos)
  export function visible(pagina: PaginaDef, acciones: readonly string[], modoEntrega: boolean, paginas?: readonly PaginaDef[]): boolean
  export function moduloDePagina(id: string, paginas?: readonly PaginaDef[]): ModuloId | null
  export function inicioDe(modulo: ModuloId, paginas?: readonly PaginaDef[]): PaginaDef
  export function modulosVisibles(acciones: readonly string[], modoEntrega: boolean, paginas?: readonly PaginaDef[]): ModuloDef[]
  export function fueraDeModulos(acciones: readonly string[], modoEntrega: boolean, paginas?: readonly PaginaDef[]): PaginaDef[]
  ```
  Áreas: auditoria `inicio, auditar, paquetes, historial` («Inicio», «Auditar», «Paquetes», «Historial»); obras `inicio, obras,
  partidas, mercado, aprobaciones, control`; produccion `inicio, existencias`. Pantallas nuevas: `{id:"auditoria", titulo:"Inicio de
  auditoría", enUnaLinea:"Suelte un Excel y vea las últimas auditorías", seccion:"Revisión", accion:null, ubicacion:{modulo:
  "auditoria", area:"inicio"}}`, `{id:"obras", titulo:"Inicio de presupuestos y obras", enUnaLinea:"Cifras, obras y pendientes de un
  vistazo", seccion:"Trabajo", accion:null, …area:"inicio"}`, `{id:"produccion", titulo:"Inicio de producción", enUnaLinea:"Lo que
  requiere atención en la arenera", seccion:"Trabajo", accion:null, …area:"inicio"}`; sale `inicio`. Orden de `PAGINAS` (manda el
  orden dentro de cada área): auditoria, libros (auditar), revisar (paquetes), historial (historial), obras, hoja, elaborar, tablero,
  entregar (obras), componer, catalogo, similares (partidas), precios_empresa, actualizacion, historico, indices, simulador
  (mercado), control, reajuste, escenarios (control), produccion, existencias (existencias), administracion, acerca (`null`).
  Se retiran `AREAS`, `GrupoDef`, `areasVisibles`, `HERRAMIENTAS_PRINCIPALES`, `herramientasVisibles` y `seccionesVisibles` (sin
  usos fuera de lo que se reescribe). Un inicio (`area === "inicio"`) es visible si su módulo tiene otra pantalla visible.
- `navegacion.ts` (la forma de `EntradaNav` y `GrupoNav` no cambia; cada panel lleva un solo grupo con `titulo: null`):
  ```ts
  export function navegacion(modulo: ModuloId, acciones: readonly string[], modoEntrega: boolean, paginas?: readonly PaginaDef[]): EntradaNav[]
  export function areaActual(pathname: string, entradas: readonly EntradaNav[]): string | null      // sin cambios
  export function moduloDeRuta(pathname: string, ultimo: ModuloId | null, paginas?: readonly PaginaDef[]): ModuloId | null
  export function moduloAlEntrar(preferido: ModuloId | null, acciones: readonly string[], modoEntrega: boolean, paginas?: readonly PaginaDef[]): ModuloId | null
  ```
  Un área con una pantalla visible es `enlace` **con el título del área** (choque 8); con varias, `panel` con el título del área.
- `BarraSuperior` props: `{ modulo: ModuloDef | null; entradas: readonly EntradaNav[]; derecha: ReactNode; menu: { abierto: boolean;
  alternar: () => void } }`; el nombre del módulo es texto (`<span class="silice-barra__modulo cds--type-heading-compact-01">`), no
  enlace (no es un tercer camino al inicio).
- `Aplicacion` (contexto) gana `modulo: ModuloId | null`.
- `export function AccesosDelModulo(props: { modulo: ModuloId }): JSX.Element` — las pantallas visibles del módulo (sin su inicio),
  agrupadas por área con un rótulo de texto por área, cada una enlace con su `enUnaLinea`; lista sencilla con divisores, no mosaicos.
- `Shell`: el índice `/`, `/inicio` y `*` hacen `<Navigate replace>` a `rutaDe(inicioDe(moduloAlEntrar(sesion.preferencias.modulo,
  …)))`; sin ningún módulo visible, a la primera de `fueraDeModulos`. El módulo actual es `moduloDeRuta(pathname, ultimo)`; cuando
  cambia y es distinto del guardado, `PUT /v1/sesion/preferencias {modulo}` (un 401 llama `alExpirar`; otro error no molesta a la
  persona). `data-modulo` del módulo actual en `.silice-marco`.

- [ ] **Paso 1: pruebas en rojo** (`front`; acciones de ana, rita y admin copiadas a mano de `ACCIONES_POR_ROL` de
  `Shell.test.tsx:67-88`, que salen de `seguridad/permisos.py`):
  - `rutas.test.ts`: `MODULOS.map(m => [m.id, m.areas.map(a => a.titulo)])` es exactamente el de «Restricciones globales»; cada
    `PaginaDef` con `ubicacion` apunta a un área existente de su módulo; solo `administracion` y `acerca` tienen `ubicacion: null`;
    cada módulo tiene exactamente un inicio; `enUnaLinea` de 1 a 60 caracteres sin `UC-`/`RF-`/`MOD-`.
  - `navegacion.test.ts`, oráculos escritos a mano (`[area, tipo, titulo]` y, en los paneles, los ids en orden):
    - ana, obras: `[inicio,enlace,"Inicio"]`, `[obras,panel,"Obras"]` = hoja, elaborar, tablero, entregar; `[partidas,panel]` =
      componer, catalogo, similares; `[mercado,panel]` = actualizacion, historico, simulador; `[control,panel]` = control, reajuste,
      escenarios (sin «Aprobaciones»: aún no tiene pantallas);
    - ana, obras, modo entrega: partidas = componer, catalogo; mercado = actualizacion, historico; control = control, reajuste;
    - rita, obras: `[inicio,enlace]`, `[obras,enlace,"Obras"]`→tablero, `[partidas,enlace,"Partidas"]`→catalogo,
      `[mercado,enlace,"Mercado"]`→historico; admin, obras: `[inicio,enlace]`, `[mercado,panel]` = precios_empresa, indices;
    - ana, auditoria: inicio, auditar→libros, historial→historial (sin «Paquetes»); rita, auditoria: inicio, auditar, paquetes→revisar,
      historial; ana y admin, produccion: inicio, existencias→existencias;
    - `modulosVisibles`: ana `["auditoria","obras","produccion"]`, rita `["auditoria","obras"]`, admin `["obras","produccion"]`;
    - **foco 4:** para ana, rita, admin y ana en modo entrega, los ids de todas las entradas de todos sus módulos más
      `fueraDeModulos` son, sin repetir, exactamente: ana `{auditoria, libros, historial, obras, hoja, elaborar, tablero, entregar,
      componer, catalogo, similares, actualizacion, historico, simulador, control, reajuste, escenarios, produccion, existencias,
      acerca}`; ana en modo entrega, el mismo sin `similares, simulador, escenarios`; rita `{auditoria, libros, revisar, historial,
      obras, tablero, catalogo, historico, acerca}`; admin `{obras, precios_empresa, indices, produccion, existencias,
      administracion, acerca}`;
    - `moduloAlEntrar("produccion", rita…) === "auditoria"`; `(null, admin…) === "obras"`; `("obras", ana…) === "obras"`;
      `(null, ana…) === "auditoria"`; con `[]` acciones → `null`;
    - **foco 1:** `moduloDeRuta("/componer", "auditoria") === "obras"`; `("/administracion", "produccion") === "produccion"`;
      `("/acerca", null) === null`; `("/auditoria", "obras") === "auditoria"`; `areaActual("/obras", entradasObras) === "inicio"`;
      `areaActual("/hoja", entradasObras) === "obras"`.
  - `BarraSuperior.test.tsx`: en `/hoja` se lee «Presupuestos y obras» junto a «Sílice» (no es enlace) y las áreas son «Inicio»,
    «Obras», «Partidas», «Mercado», «Control»; en `/libros` con rita, «Auditoría» y «Inicio», «Auditar», «Paquetes», «Historial».
  - `Shell.test.tsx`: `/` y `/inicio` con `preferencias.modulo = "obras"` → h1 «Inicio de presupuestos y obras»; con rita y
    `"produccion"` → «Inicio de auditoría»; ir de `/libros` a `/hoja` llama `PUT /v1/sesion/preferencias` con `{"modulo":"obras"}`
    una sola vez; ir a `/acerca` no la llama; `*` (ruta inexistente) redirige igual que `/`.
  - `Auditoria.test.tsx`: lo que probaba `Inicio.test.tsx` de auditar (soltar, «Auditar con recorrido guiado», «Auditar por mi
    cuenta», últimas auditorías, «Recorrido en curso… Seguir con el paso 2») con h1 «Inicio de auditoría»; no hay «Herramientas
    principales». `Produccion.test.tsx`: h1 «Inicio de producción» y el panel de la arenera con ana y admin. `Obras.test.tsx`: admin
    ve h1 «Inicio de presupuestos y obras» y los accesos «Precios de la empresa» e «Índices del BCV» con su línea de ayuda.
  - `recorrido.test.tsx`: el paso 1 de `RECORRIDO_AUDITAR` es `pagina: "auditoria"` y `pasoDeRuta(r, "/auditoria") === 0`.
- [ ] **Paso 2:** `cd frontend-desktop && npx vitest run src/shell src/paginas/auditoria src/paginas/produccion src/paginas/obras
  src/App.test.tsx` → FALLA.
- [ ] **Paso 3:** implementar (DESIGN.md y reglas anti-IA de «Restricciones globales»; el nombre del módulo se recorta con puntos
  suspensivos y el completo queda en `title`).
- [ ] **Paso 4:** `npx vitest run` (suite del front: hay pruebas de otras páginas que esperan «Inicio»), `npm run lint`,
  `npm run build` → PASAN.
- [ ] **Paso 5:** commits `test(front): navegacion por modulos e inicio de cada modulo (rojo)` / `feat(front): navegacion por
  modulos e inicio de cada modulo`.

### Tarea MOD-2: Sidebar de módulos, botón «Sílice», Esc, fijar/ocultar y confirmación al salir

**Archivos:**
- Crear: `src/shell/sidebar.ts` (almacén y regla de Esc), `src/shell/SidebarModulos.tsx` (+ `.scss`, `.test.tsx`),
  `src/shell/sucio.ts`, `src/shell/salida.ts`, `src/shell/DialogoSalida.tsx`, `src/shell/EnlaceSeguro.tsx`,
  `src/shell/preferencias.ts`, `src/shell/useFijadoPosible.ts`
- Modificar: `src/shell/BarraSuperior.tsx` (+ `.scss`: botón «Sílice» con ícono `Menu` en lugar de `HeaderMenuButton` + `HeaderName`;
  áreas con `EnlaceSeguro`), `src/shell/PanelDeArea.tsx` (`EnlaceSeguro`), `src/shell/Shell.tsx` (monta sidebar y `DialogoSalida`;
  quita el oyente de Esc de captura :147-157; clase `silice-marco--fijado`), `src/shell/_umbrales.scss` (mapas por módulo y de
  fijado), `src/shell/shell.scss` (retira `menu-en-capa` y las reglas de `.cds--side-nav`), `src/shell/sinClasica.test.ts`
- Borrar: `src/shell/MenuEnCapa.tsx`, `MenuEnCapa.scss`, `MenuEnCapa.test.tsx` (sus pruebas útiles pasan a `SidebarModulos.test.tsx`)
- Prueba: `src/shell/sidebar.test.ts`, `src/shell/SidebarModulos.test.tsx`, `src/shell/sucio.test.ts`, `src/shell/salida.test.tsx`,
  `src/shell/BarraSuperior.test.tsx`, `src/shell/Shell.test.tsx`

**Interfaces:**
- `sucio.ts`: `export function useFormularioSucio(id: string, sucio: boolean): void` (id = id de pantalla; se limpia al desmontar);
  `export function formulariosSucios(): string[]` (en orden de registro); `export function olvidarFormularios(): void`.
- `salida.ts`: `export type MotivoSalida = "salir" | "carpeta"`; `export function confirmarSalida(motivo: MotivoSalida, extras?:
  readonly string[]): Promise<boolean>` — resuelve `true` sin diálogo si no hay formularios sucios ni `extras`; si los hay, abre
  `DialogoSalida` con título «Cambios sin guardar» y el texto «Tiene cambios sin guardar en {lista}. Si sale de esta pantalla, se
  perderán.» (botones «Quedarme» / «Salir y descartar») o, con `"carpeta"`, «… Si cambia de carpeta, se perderán.» («Quedarme» /
  «Cambiar y descartar»). `{lista}` = títulos de las pantallas sucias (`paginaPorId`) y luego `extras`, unidos «A», «A y B», «A, B
  y C». «Salir/Cambiar y descartar» llama `olvidarFormularios()`. Diálogo propio (sin `Modal` de Carbon, como BCP-5 §4.7),
  `role="dialog" aria-modal="true"`, foco inicial en «Quedarme», foco atrapado, Esc = «Quedarme».
- `EnlaceSeguro.tsx`: `export function EnlaceSeguro(props: NavLinkProps & { to: string; alNavegar?: () => void }): JSX.Element` y
  `export function useNavegarSeguro(): (to: string) => Promise<boolean>` — si `to` no es la ruta actual y hay formularios sucios,
  `preventDefault`, `await confirmarSalida("salir")` y solo entonces `navigate(to)`. Lo usan la barra, el panel de área, el sidebar
  y los botones de la mesa.
- `preferencias.ts`: `export function guardarPreferencias(cambio: { modulo?: ModuloId; sidebar_fijado?: boolean }, alExpirar: () =>
  void): Promise<void>` (`PUT /v1/sesion/preferencias`; 401 → `alExpirar`; otro error se calla). `Shell` de MOD-1 pasa a usarla.
- `sidebar.ts`: `export function useSidebar(): { abierto: boolean; fijado: boolean }`, `abrirSidebar()`, `cerrarSidebar()`,
  `alternarSidebar()`, `fijarSidebar(fijo: boolean)` (almacén externo como `recorrido.ts`; el fijado inicial sale de
  `sesion.preferencias.sidebar_fijado`); `export function esEscParaElSidebar(e: KeyboardEvent): boolean` — `true` solo si
  `e.key === "Escape"`, `!e.defaultPrevented`, el destino no está dentro de `input, textarea, select, [contenteditable="true"],
  [role="grid"], [role="combobox"], [role="listbox"], [role="menu"], [role="dialog"]`, no hay ningún `[aria-modal="true"]` en el
  documento y ningún control de la barra está abierto (`header.silice-barra [aria-expanded="true"]`, salvo el propio «Sílice»).
- `useFijadoPosible.ts`: `export function useFijadoPosible(): boolean` — lee `--silice-fijado-posible` (`1`/`0`) de `<html>`, que pone
  `_umbrales.scss`; se recalcula en `resize` y al cambiar `data-silice-letra` (`MutationObserver`). Así el umbral vive solo en SCSS.
- `_umbrales.scss`: `$umbrales-por-modulo` (umbral en que la barra del módulo no cabe, por escala; valores de partida auditoria
  1055.98/1535.98/1919.98 px, obras 1279.98/1919.98/2559.98 px, produccion 1055.98/1279.98/1535.98 px; **los fija la medida de
  MOD-5**) con `@mixin barra-no-cabe($modulo, $escala)` sobre `html[data-silice-letra=…] .silice-marco[data-modulo=…]`;
  `$fijado-desde: ("normal": 1366px, "grande": 1708px, "muy-grande": 2049px)` que pone `--silice-fijado-posible: 1`. Se conserva
  `$umbrales-por-escala` (la columna del recorrido sigue pasando a franja como hoy).
- `SidebarModulos.tsx`:
  ```ts
  export function SidebarModulos(props: { modulos: readonly ModuloDef[]; actual: ModuloId | null; entradas: readonly EntradaNav[];
    fuera: readonly PaginaDef[]; abierto: boolean; fijado: boolean; fijadoPosible: boolean; alCerrar: () => void;
    alFijar: (fijo: boolean) => void; nombre: string }): JSX.Element | null
  ```
  Visible si `abierto` o (`fijado && fijadoPosible`). En capa: contenedor `role="dialog" aria-modal="true" aria-label="Módulos de
  Sílice"` + capa `$overlay` bajo la barra; fijado: `<nav aria-label="Módulos">` sin capa. Contenido: rótulo «Módulos»; un renglón por
  módulo (`EnlaceSeguro` a su inicio; nombre en `heading-03`, `enUnaLinea` en `helper-text`); el actual con `aria-current="page"`,
  seminegrita y barra de 4 px en `$link-inverse` (choque 10); la sección `silice-sidebar__areas` «Áreas de {módulo}» con las
  entradas del módulo (cada pantalla con su `enUnaLinea`), que el CSS solo muestra por debajo del umbral del módulo; al pie
  Administración y Acerca de Sílice (de `fuera`), «Sesión de {nombre}» y el botón «Fijar» (en capa, solo si `fijadoPosible`) u
  «Ocultar» (fijado). Fijado: `.silice-marco--fijado .silice-contenido { margin-inline-start: calc(264px *
  var(--silice-escala-letra)) }` (empuja).
- `BarraSuperior` props: `{ modulo: ModuloDef | null; entradas: readonly EntradaNav[]; derecha: ReactNode; sidebar: { abierto:
  boolean; visible: boolean; alternar: () => void } }`; el botón «Sílice» tiene `aria-expanded={visible}`, `aria-controls` al
  sidebar y nombre accesible «Sílice, abrir los módulos» / «Sílice, cerrar los módulos». Con el sidebar fijado y visible, pulsarlo
  lleva el foco al módulo actual del sidebar (no lo oculta: eso es «Ocultar»).

- [ ] **Paso 1: pruebas en rojo:**
  - `sidebar.test.ts` (`esEscParaElSidebar` con eventos armados a mano): `true` con destino `<main>`; `false` con destino `<input>`,
    `<textarea>`, una celda dentro de `role="grid"`, un `role="combobox"`, dentro de un `role="dialog"`; `false` si hay un
    `[aria-modal="true"]` en el documento, si un botón de `header.silice-barra` tiene `aria-expanded="true"`, si `defaultPrevented`,
    o si la tecla no es Escape.
  - `SidebarModulos.test.tsx` y `Shell.test.tsx` (ana, `MemoryRouter`):
    - oculto al empezar; clic en «Sílice» → aparece «Módulos de Sílice», `aria-expanded="true"`, el foco va a «Presupuestos y obras»
      (módulo de `/hoja`) que lleva `aria-current="page"`;
    - **foco 2:** con el foco en `<main>`, Esc lo abre; otro Esc lo cierra y el foco vuelve a «Sílice»; con el foco en un
      `<input>` de la página, Esc no lo abre y el `<input>` conserva el foco; con el panel de «Obras» abierto, el primer Esc cierra
      el panel (foco en «Obras») y el sidebar sigue cerrado, el segundo lo abre; con un recorrido activo, abrir y cerrar el sidebar
      con Esc deja `recorridoEnCurso()` distinto de `null`;
    - Tab desde el último elemento vuelve al primero y Mayús+Tab desde el primero va al último (foco atrapado en capa); clic en la
      capa lo cierra y devuelve el foco a «Sílice»;
    - elegir «Auditoría» navega a `/auditoria`, cierra el sidebar y el foco termina en el h1 «Inicio de auditoría» (VD-7);
    - «Fijar» llama `PUT /v1/sesion/preferencias {"sidebar_fijado":true}`, el marco gana `silice-marco--fijado`, el sidebar queda
      como `navigation "Módulos"` sin capa y el botón dice «Ocultar»; «Ocultar» llama `{"sidebar_fijado":false}` y desaparece;
    - con `preferencias.sidebar_fijado = true` y `--silice-fijado-posible: 0` en `<html>`, el sidebar no se pinta hasta pulsar
      «Sílice» y entonces sale en capa sin «Fijar»; con `1`, se pinta fijado al cargar; con el sidebar fijado y nada abierto, Esc no
      pinta ninguna capa;
    - la sección «Áreas de Presupuestos y obras» lista las mismas pantallas que la barra, cada título una sola vez dentro de
      `navigation "Módulos"` / el diálogo; el pie muestra «Acerca de Sílice» y no «Administración» (ana); con admin muestra las dos;
    - **foco 3:** con `useFormularioSucio("componer", true)` montado, elegir «Auditoría» abre «Cambios sin guardar» con «Tiene cambios
      sin guardar en Componer una partida. Si sale de esta pantalla, se perderán.»; «Quedarme» no navega y no llama a preferencias;
      «Salir y descartar» navega y `formulariosSucios()` queda vacío; lo mismo con el enlace del área «Mercado» de la barra y con un
      enlace del panel; volver a `/componer` estando en `/componer` no pregunta.
  - `sucio.test.ts`: registrar, desregistrar al desmontar, orden; `salida.test.tsx`: unión «A», «A y B», «A, B y C» con `extras`;
    sin nada sucio resuelve `true` sin pintar el diálogo; Esc en el diálogo = «Quedarme».
  - `sinClasica.test.ts`: la expresión de clases prohibidas incluye `silice-capa` y `cds--side-nav`.
- [ ] **Paso 2:** `cd frontend-desktop && npx vitest run src/shell` → FALLA.
- [ ] **Paso 3:** implementar (DESIGN.md y reglas anti-IA; sin animación de entrada; foco visible `$focus-inverse` dentro del
  sidebar; textos exactos de arriba).
- [ ] **Paso 4:** `npx vitest run` (suite del front), `npm run lint`, `npm run build` → PASAN.
- [ ] **Paso 5:** commits `test(front): sidebar de modulos, esc y confirmacion al salir (rojo)` / `feat(front): sidebar de modulos,
  esc y confirmacion al salir`.

### Tarea MOD-3a: Ficha de la obra y carpeta de la empresa (backend)

**Archivos:**
- Crear: `aplicacion/tablas_obra.py` (`METADATA_OBRA`), `aplicacion/obras.py`, `migraciones/caso/versions/caso_0011_mod_ficha_obra.py`
- Modificar: `api/rutas/proyectos.py` (`ProyectoNuevo` y `ProyectoDelCasoRespuesta` ganan `cliente`, `ubicacion`), `api/rutas/casos.py`
  (`CasosRespuesta` gana `empresa` y `es_demostracion`; ruta `DELETE /actual`)
- Prueba: `tests/unit/test_api_ficha_obra.py`, `tests/unit/test_api_casos_empresa.py`, `tests/integration/test_migracion_ficha_obra.py`
- Compartidos: `METADATAS_CASO` y su prueba, `TABLA` (una fila), `docs/api.json`, `CHANGELOG.md`

**Interfaces:**
- Tabla `ficha_obra` (caso): `proyecto_id Integer PK` (sin clave foránea a `core.models`), `cliente String(200) default ""`,
  `ubicacion String(200) default ""`.
- `aplicacion/obras.py`: `@dataclass(frozen=True) class FichaObra: cliente: str; ubicacion: str`;
  `def guardar_ficha(sesion: Session, proyecto_id: int, ficha: FichaObra) -> None`;
  `def fichas(sesion: Session) -> dict[int, FichaObra]` (sin fila → `FichaObra("", "")`).
- `POST /v1/proyectos` acepta `cliente: str = ""` y `ubicacion: str = ""` (`max_length=200`), guardados en la **misma transacción**
  que el proyecto; `GET /v1/proyectos` y la respuesta 201 traen `cliente` y `ubicacion`.
- `GET /v1/casos` → además `empresa: {nombre, ruta_relativa} | null` (la carpeta del proceso, la de omisión de la instalación) y
  `es_demostracion: bool` (la actual es `aplicacion.casos.es_demostracion`).
- `DELETE /v1/casos/actual` (`CAMBIAR_CASO`, sesión, CSRF) → 200 `CasoRespuesta` de la carpeta de la empresa: `caso_web.olvidar(huella)`
  y `recordar_caso(…, None, …)` (MOD-0); con la clave de API → 409 `MENSAJE_CON_CLAVE`.

- [ ] **Paso 1: pruebas en rojo:**
  - ana `POST /v1/proyectos {"nombre":"Casa Demo","moneda":"Bs","dominio":"civil","cliente":"Contratista Demo, C.A.","ubicacion":"Maracay"}`
    → 201 con `cliente` y `ubicacion` exactos; `GET /v1/proyectos` los repite; sin esos campos → `""` y `""`;
  - `cliente` de 201 caracteres → 422 y la respuesta no contiene el texto enviado;
  - **todo o nada:** con `aplicacion.obras.guardar_ficha` sustituido por una función que levanta `RuntimeError`, la petición
    falla y `GET /v1/proyectos` no lista «Casa Demo»;
  - `GET /v1/casos` → `empresa.nombre` es el del caso del proceso de la fixture y `es_demostracion` `false`; tras
    `POST /v1/casos/demostracion` y `POST /v1/casos/actual {"nombre":"demostracion.db"}` → `true`;
  - ana en `s1.db` → `DELETE /v1/casos/actual` → 200 con el nombre de la empresa; `GET /v1/casos` → `actual == empresa`;
    `GET /v1/sesion` → `eleccion.caso is None`; rita → 403; sin CSRF → 403; con clave → 409;
  - migración: `upgrade` hasta `caso_0011_mod_ficha_obra` crea `ficha_obra`; `downgrade` a `caso_0010_mp_carpeta` la quita; dos
    `upgrade` no fallan.
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_api_ficha_obra.py tests/unit/test_api_casos_empresa.py
  tests/integration/test_migracion_ficha_obra.py -q -W error -p no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** mismas órdenes + `tests/unit/test_api_proyectos*.py tests/unit/test_api_casos*.py` y, con lo compartido aplicado,
  `tests/integration/test_migraciones.py tests/unit/test_api_acceso_por_ruta.py` → PASAN; `ruff check` limpio.
- [ ] **Paso 5:** commits `test(api): ficha de la obra y carpeta de la empresa (rojo)` / `feat(api): ficha de la obra y carpeta de
  la empresa`.

### Tarea MOD-3b: Selector de obra, carpetas y «Nueva obra» (front; absorbe T6 y T7 del plan de montar)

**Archivos:**
- Crear: `src/shell/SelectorObra.tsx` (+ `.scss`, `.test.tsx`), `src/shell/MarcaDemostracion.tsx` (+ `.test.tsx`),
  `src/shell/carpetas/GestionCarpetas.tsx` (elegir, crear con moneda, subir, demostración: BCP-5 §4.3-4.7),
  `src/shell/carpetas/DialogoCarpetas.tsx`, `src/shell/carpetas/Carpetas.test.tsx`, `src/shell/obras/DialogoNuevaObra.tsx`,
  `src/shell/obras/NuevaObra.test.tsx`, `src/paginas/administracion/CarpetasDeTrabajo.tsx`
- Modificar: `src/shell/Shell.tsx` (lado derecho por módulo; estado inicial desde `sesion.eleccion`; `cambiarCarpeta` con
  `confirmarSalida("carpeta", …)`; aviso «Ahora trabaja con la carpeta de trabajo «X».» sin la frase del reinicio, que ya no es
  cierta), `src/shell/contexto.tsx`, `src/api/tipos.ts` (`ProyectoRespuesta` gana `cliente: string` y `ubicacion: string`;
  `CasosRespuesta` gana `empresa: CasoRespuesta | null` y `es_demostracion: boolean`), `src/shell/Selectores.tsx` (quedan `nombreDeCarpeta` y `rotuloDeProyecto` con «(sin versión
  guardada)»), `src/paginas/administracion/index.tsx` (pestaña «Carpetas de trabajo»), una línea de `src/paginas/hoja/index.tsx`
  (estado vacío de una obra sin versión, BCP-6 §5.2), `src/shell/sinClasica.test.ts`
- Borrar: `src/shell/PanelCarpetaProyecto.tsx`, `.scss`, `.test.tsx` (lo útil pasa a `SelectorObra.test.tsx`)
- Prueba: las nuevas, `src/shell/Shell.test.tsx`, `src/shell/Selectores.test.tsx`, `src/paginas/administracion/Administracion.test.tsx`

**Interfaces:**
- `Aplicacion` gana `elegirObra: (codigo: string | null) => void` (fija la obra y hace `PUT /v1/sesion/proyecto`) y
  `abrirNuevaObra: () => void`.
- ```ts
  export function SelectorObra(props: { obras: ProyectoRespuesta[] | null; elegida: string | null; enInicio: boolean;
    carpeta: string | null; puedeCambiarCarpeta: boolean; puedeCrearObra: boolean; alElegir: (codigo: string) => void;
    alNuevaObra: () => void; alCambiarCarpeta: () => void; pie?: ReactNode }): JSX.Element | null
  ```
  Solo en el módulo `obras`. Botón: «Todas las obras» en `/obras`; si no, «Obra: {nombre}» u «Obra: sin elegir»; nombre accesible
  «Obra: {nombre}. Cambiar obra»; recortado a 18 rem con el nombre completo en `title`. Panel (patrón `useDespliegue`): campo
  `Search` «Buscar obra» que filtra sin distinguir tildes ni mayúsculas por nombre, cliente y ubicación; lista de obras (nombre y,
  debajo, «cliente · ubicación» en `helper-text`), la elegida con `aria-current="true"`; «Nueva obra» (con `puedeCrearObra`); al pie
  «Carpeta: {carpeta} · Cambiar carpeta…» (el enlace solo con `puedeCambiarCarpeta`) y `pie` (hueco para `ListaDeLaCarpeta` de MP
  T4). Sin `leer_proyecto` pero con `cambiar_caso` (admin): el botón dice «Carpeta: {carpeta}» y el panel solo trae el pie. Sin las
  dos: `null`.
- `export function MarcaDemostracion(props: { activa: boolean; puedeVolver: boolean; alVolver: () => void }): JSX.Element | null` —
  en la barra de los tres módulos mientras `es_demostracion`: «Demostración» (texto e ícono, no solo color) que abre «Está viendo
  datos inventados.» y «Volver a la carpeta de la empresa» (`DELETE /v1/casos/actual`, con `confirmarSalida("carpeta")`).
- `export function GestionCarpetas(props: { alAbrir: (nombre: string) => void; conDemostracion: boolean }): JSX.Element` (la usan el
  diálogo y la pestaña de Administración); `export function DialogoCarpetas(props: { abierto: boolean; alCerrar: () => void;
  alAbrir: (nombre: string) => void; conDemostracion: boolean }): JSX.Element | null`. Crear: campo «Moneda de trabajo» (`Select`
  sin preselección, «Elija…», obligatorio) → `POST /v1/casos` → `POST /v1/casos/actual` → `PUT /v1/carpeta/moneda`.
- `export function DialogoNuevaObra(props: { abierto: boolean; alCerrar: () => void; alCrear: (obra: ProyectoRespuesta) => void }):
  JSX.Element | null` — Nombre (obligatorio), Cliente y Ubicación (opcionales), Tipo de obra (los de BCP-6 §5.2), Moneda (propuesta
  la de `GET /v1/carpeta`; sin moneda de carpeta, sin preselección y obligatoria); elegir la otra muestra «Esta obra se valorará
  convirtiendo los precios de la carpeta con la tasa del BCV del día.». `POST /v1/proyectos` y, al crear, `recargarProyectos` y
  `elegirObra(nueva.codigo)`.
- Cambiar de carpeta: extras de `confirmarSalida("carpeta", extras)` = «Hoja de {obra}» por cada borrador de `GET /v1/hoja/borradores`
  con `cambios > 0` (BCP-5 §4.6).

- [ ] **Paso 1: pruebas en rojo** (`fetch` simulado):
  - `SelectorObra`: en `/hoja` con la obra `"7"` «Casa Demo» → botón «Obra: Casa Demo», nombre «Obra: Casa Demo. Cambiar obra»; en
    `/obras` → «Todas las obras»; sin elegir → «Obra: sin elegir»; «maracay» filtra a «Casa Demo» y «TORRE» a «Torre B»; elegir
    «Torre B» llama `PUT /v1/sesion/proyecto {"proyecto":"8"}`; con 80 caracteres de nombre el texto tiene la clase de recorte y el
    nombre accesible el completo;
  - rita: lista y búsqueda, sin «Nueva obra» ni «Cambiar carpeta…»; admin (sin `leer_proyecto`, con `cambiar_caso`): botón
    «Carpeta: silice» y el panel con «Cambiar carpeta…» y sin lista; en los módulos `auditoria` y `produccion` no hay selector;
  - restaurar: `sesion.eleccion = {caso:"s1.db", proyecto:"7", aviso:null}` → en `/hoja` el botón dice «Obra: Casa Demo» sin elegir
    nada; con `aviso` se ve una vez y no vuelve al navegar;
  - **foco 3:** con `useFormularioSucio("componer", true)`, «Cambiar carpeta…» → elegir `s2.db` abre «Tiene cambios sin guardar en
    Componer una partida. Si cambia de carpeta, se perderán.»; «Quedarme» no llama `POST /v1/casos/actual`; con un borrador de
    «Casa Demo» con `cambios: 2` y nada sucio → «… en Hoja de Casa Demo …»; sin nada, cambia directo;
  - F5, F6, F7 y F9 del diseño BCP (§10.4) tal como están escritas, con «carpeta de trabajo»; crear sin moneda → «Elija la moneda de
    trabajo de la carpeta.» sin llamar a la API; crear con Bs → `POST /v1/casos`, `POST /v1/casos/actual`, `PUT /v1/carpeta/moneda
    {"moneda":"Bs"}` en ese orden;
  - `MarcaDemostracion`: con `es_demostracion: true` se ve «Demostración» en `/libros` y en `/hoja`; «Volver a la carpeta de la
    empresa» llama `DELETE /v1/casos/actual`; rita la ve sin el botón de volver;
  - `DialogoNuevaObra` (F10 adaptado): con `GET /v1/carpeta` `{moneda:"Bs"}` la moneda viene en «Bs»; elegir «USD» muestra el texto
    exacto; vacío → el mensaje de la API en línea; enviar → `POST /v1/proyectos` con `{"nombre":"Casa Demo","moneda":"Bs","dominio":
    "civil","descripcion":"","cliente":"Contratista Demo, C.A.","ubicacion":"Maracay"}` y luego el botón dice «Obra: Casa Demo»;
  - F11: obra sin versión → «(sin versión guardada)» y el estado vacío de la Hoja con el texto de BCP-6 §5.2;
  - Administración: admin ve la pestaña «Carpetas de trabajo» con la lista y «Crear», sin «Demostración» (no tiene `editar_hoja`);
  - ninguna cadena visible del selector, los diálogos ni la marca contiene `/\bcaso\b/i` ni `/\bproyecto\b/i`;
  - `sinClasica.test.ts` prohíbe `silice-contexto__`.
- [ ] **Paso 2:** `cd frontend-desktop && npx vitest run src/shell src/paginas/administracion src/paginas/hoja` → FALLA.
- [ ] **Paso 3:** implementar (DESIGN.md y reglas anti-IA; diálogos propios sin `Modal`, foco devuelto al cerrar).
- [ ] **Paso 4:** `npx vitest run`, `npm run lint`, `npm run build` → PASAN; `uv run --active pytest tests/unit/test_front_rutas_api.py
  -q -W error` → PASA (las rutas que llama el front existen).
- [ ] **Paso 5:** commits `test(front): selector de obra, carpetas y nueva obra (rojo)` / `feat(front): selector de obra, carpetas y
  nueva obra`.

### Tarea MOD-4a: Cifras, obras y pendientes de la mesa (backend)

**Archivos:**
- Crear: `aplicacion/mesa.py`, `api/rutas/obras.py`
- Prueba: `tests/unit/test_mesa.py` (puras y con base), `tests/unit/test_api_obras_resumen.py`
- Compartidos: `api/main.py` (`include_router(obras.router)`), `TABLA` (dos filas), `docs/api.json`, `CHANGELOG.md`

**Interfaces:**
- ```python
  @dataclass(frozen=True) class Siguiente: texto: str; pagina: str
  @dataclass(frozen=True) class ObraEnMesa:
      codigo: str; nombre: str; cliente: str; moneda: str; etapa: str   # "en_elaboracion"|"en_ejecucion"|"atrasada" (MP-4 agrega "en_aprobacion"|"aprobada")
      version: str | None; total: Decimal | None; corte: date | None; ev: Decimal | None; pv: Decimal | None; bac: Decimal | None
      spi: Decimal | None; retraso_dias: int | None; que_pasa: str | None; siguiente: Siguiente | None
  @dataclass(frozen=True) class Cifra: clave: str; titulo: str; actual: Decimal; meta: Decimal; delta: Decimal; delta_pct: Decimal | None; sentido: str; detalle: str | None
  @dataclass(frozen=True) class CifrasMesa: valor_ganado: Cifra | None; avance: Cifra | None; conversiones: tuple[Conversion, ...]; fuera_de_suma: tuple[str, ...]
  @dataclass(frozen=True) class Conversion: obra: str; moneda: str; tasa: Decimal; fecha: date
  @dataclass(frozen=True) class Pendiente: obra: str; obra_nombre: str; texto: str; accion: Siguiente
  @dataclass(frozen=True) class GrupoPendientes: clave: str; titulo: str; items: tuple[Pendiente, ...]
  FuentePendientes = Callable[[Session, date], list[Pendiente]]
  GRUPOS = (("aprobar", "Aprobar"), ("compras", "Compras"), ("precios", "Precios"), ("calidad", "Calidad"))
  FUENTES: dict[str, tuple[FuentePendientes, ...]]   # MOD-4a: precios = (precios_viejos, precios_sin_referencia); calidad = (hallazgos_graves, lista_vieja)
  def obras_de_la_mesa(sesion: Session, catalogo: Catalogo, hoy: date) -> list[ObraEnMesa]
  def cifras_de_la_mesa(obras: Sequence[ObraEnMesa], moneda: str | None, tasa: Callable[[date], Decimal | None]) -> CifrasMesa
  def pendientes(sesion: Session, hoy: date) -> list[GrupoPendientes]      # un grupo sale solo si tiene al menos una fuente registrada
  def dias_habiles_entre(desde: date, hasta: date) -> int                  # lunes a viernes d con desde < d <= hasta
  ```
- Reglas (`obras_de_la_mesa`): etapa `en_elaboracion` sin línea base vigente (`tiene_linea_base`); con línea base, `en_ejecucion`,
  y `atrasada` si `spi < parametros_actuales(…).spi_error`. EV, PV, BAC, SPI y corte salen de `calcular_el_control(sesion, proyecto,
  catalogo)` (núcleo, sin tocarlo) al `corte_por_defecto`; `retraso_dias = reproyeccion.termino − estado.dias_plan` si es > 0;
  `ControlInvalido` → EV/PV `None` y `que_pasa` = su mensaje. `que_pasa` antes de MP-7: atrasada → «Atrasada {d} días hábiles (SPI
  {spi con dos decimales y coma})»; en ejecución sin valuaciones → «Sin avance registrado»; si no, `None`. `siguiente`:
  en_elaboracion → («Abrir la Hoja», "hoja"); en_ejecucion → («Registrar el avance», "control"); atrasada → («Ver las alertas»,
  "control"). `total` = Σ `partida_presupuestada.total` de la versión de la línea base o, sin ella, de la vigente. `moneda` =
  `moneda_del_proyecto`.
- Reglas (`cifras_de_la_mesa`), sobre las obras `en_ejecucion`/`atrasada` con EV y PV: cada una se suma en `moneda`; otra moneda se
  convierte con `tasa(corte)` (Bs = USD × tasa; USD = Bs ÷ tasa) y se declara en `conversiones`; sin tasa va a `fuera_de_suma` y no se
  suma. `moneda is None` → la de las obras si todas comparten una; si no, todas a `fuera_de_suma`. Valor ganado: `actual` = ΣEV, `meta`
  = ΣPV, `delta` = ΣEV − ΣPV, `delta_pct` = delta ÷ ΣPV × 100 a 0,1 `ROUND_HALF_UP` (`None` si ΣPV = 0), `sentido` "rendimiento",
  montos a 0,01. Avance: `actual` = ΣEV ÷ ΣPV a 0,0001 `ROUND_HALF_UP`, `meta` = 1,0000, `delta` = actual − 1, `sentido` "rendimiento",
  `detalle` «{n} obra(s) atrasada(s); la más atrasada, {nombre}: {d} días hábiles» (o `None` sin atrasadas); `None` si ΣPV = 0. Sin
  ninguna obra sumada, las dos `None`.
- Fuentes de MOD-4a (sobre la versión vigente de cada obra y su `lista_precios`): `precios_viejos`: `hoy − lista.fecha_vigencia > 90`
  → «Precios de hace {d} días (lista «{nombre}» del {dd/mm/aaaa})», acción («Actualizar precios», "actualizacion");
  `precios_sin_referencia`: insumos de `linea_composicion_version` de la versión con `insumo_id` cuyo `PrecioInsumo` en esa lista no
  tiene `referencia_precio` ni `precio_origen` → «{n} precio(s) sin referencia en {versión}», («Ver el catálogo», "catalogo");
  `hallazgos_graves`: `hallazgo` de la versión con severidad `ERROR` o `CRITICO` → «{n} hallazgo(s) de error o críticos en
  {versión}», («Abrir la Hoja», "hoja"); `lista_vieja`: `describir(sesion, hoy).fecha − lista.fecha_vigencia > 90` (MP T1) → «La
  lista de {versión} es {d} días más vieja que la lista para armar.», («Actualizar precios», "actualizacion").
- Rutas (`prefix="/v1/obras"`, `RutaSinEco`): `GET /resumen` (`LEER`) → `{moneda, hoy, cifras: [{clave, titulo, actual, meta, delta,
  delta_pct, sentido, detalle}], conversiones: [{obra, moneda, tasa, fecha}], fuera_de_suma: [str], obras: [{codigo, nombre, cliente,
  etapa, etapa_texto, version, total, moneda, avance_real, avance_plan, que_pasa, siguiente: {texto, pagina}|null}]}` (montos como
  texto; `cifras` solo con las que no son `None`, en el orden valor ganado, avance; `avance_real` = EV ÷ BAC × 100 y `avance_plan` =
  PV ÷ BAC × 100 a 0,1; `etapa_texto` «En elaboración», «En ejecución», «Atrasada»). `GET /pendientes` (`EDITAR`) → `{grupos:
  [{clave, titulo, items: [{obra, obra_nombre, texto, accion: {texto, pagina}}]}]}`.

- [ ] **Paso 1: pruebas en rojo** (`tests/unit/test_mesa.py`; `hoy = 2026-10-25`; todo a mano):
  - `cifras_de_la_mesa`, carpeta Bs, A (Bs, EV 40.000,00, PV 50.000,00, SPI 0,80, umbral 0,90, retraso 3) y B (Bs, EV 30.000,00,
    PV 25.000,00, SPI 1,20): valor ganado `actual 70000.00`, `meta 75000.00`, `delta -5000.00`, `delta_pct -6.7`; avance `actual
    0.9333`, `meta 1.0000`, `delta -0.0667`, `detalle` «1 obra atrasada; la más atrasada, A: 3 días hábiles»;
  - **foco 5:** + C (USD, EV 100,00, PV 100,00, corte 2026-10-23) con `tasa(2026-10-23) = 40.00` → `actual 74000.00`, `meta
    79000.00`, `delta -5000.00`, SPI `0.9367`, `conversiones == (Conversion("C","USD",40.00,2026-10-23),)`; con `tasa` → `None` →
    los números de A+B y `fuera_de_suma == ("C",)`; solo C sin tasa → las dos cifras `None`; una obra con EV 0 y PV 0 → valor
    ganado `0.00/0.00/0.00`, `delta_pct None`, avance `None`; sin obras en ejecución → las dos `None`;
  - `dias_habiles_entre(2026-10-20, 2026-10-23) == 3`, `(2026-10-20, 2026-10-24) == 3`, `(2026-10-20, 2026-10-26) == 4`,
    `(2026-10-23, 2026-10-23) == 0`;
  - con base (OB-S2 de `tests/fixtures/control_ob_s2.py`: `sembrar`, `declarar_linea_base`, `registrar_v01_y_v02`; memoria
    `tests/fixtures/memorias/control_ob_s2.md`): `obras_de_la_mesa` → OB-S2 `etapa "atrasada"`, `ev 1200.00`, `pv 1500.00`, `bac
    4000.00`, `spi 0.8000`, `retraso_dias 3`, `que_pasa` «Atrasada 3 días hábiles (SPI 0,80)», `siguiente` («Ver las alertas»,
    "control"), `total` igual a Σ `partida_presupuestada.total` de OB-001 leída en la prueba con su propia consulta; un segundo
    proyecto sin línea base → `en_elaboracion`, («Abrir la Hoja», "hoja"); con línea base y sin valuaciones → `en_ejecucion`, «Sin
    avance registrado»;
  - fuentes, carpeta ficticia con «Casa Demo» versión CD-001 sobre la lista «Base» del 2026-06-01 y lista para armar «Nueva» del
    2026-10-01: «Precios de hace 146 días (lista «Base» del 01/06/2026)»; «La lista de CD-001 es 122 días más vieja que la lista
    para armar.»; con la lista del 2026-07-27 (90 días) no hay pendiente de precios y con la del 2026-07-26 (91) sí; 3 insumos en la
    versión, uno con `referencia_precio`, uno con `precio_origen`, uno sin nada → «1 precio sin referencia en CD-001»; 2 ERROR + 1
    CRITICO + 3 ADVERTENCIA → «3 hallazgos de error o críticos en CD-001»;
  - `pendientes` devuelve solo los grupos `precios` y `calidad`, en ese orden (aún no hay fuentes de aprobar ni compras).
  - `tests/unit/test_api_obras_resumen.py`: ana `GET /v1/obras/resumen` con OB-S2 en una carpeta cuya moneda es USD (la de su
    lista; sin conversión) → `moneda "USD"`, `cifras[0]` `{clave:"valor_ganado", actual:
    "1200.00", meta:"1500.00", delta:"-300.00", delta_pct:"-20.0", sentido:"rendimiento"}`, `cifras[1].actual == "0.8000"`, la obra
    con `avance_real "30.0"` y `avance_plan "37.5"`; rita → 200; admin → 403; ana `GET /v1/obras/pendientes` → 200; rita → 403;
    ningún monto es número JSON (todos `str`).
- [ ] **Paso 2:** `uv run --active pytest tests/unit/test_mesa.py tests/unit/test_api_obras_resumen.py -q -W error -p
  no:cacheprovider` → FALLA.
- [ ] **Paso 3:** implementar (el núcleo se usa tal cual; nada de `float`).
- [ ] **Paso 4:** misma orden + `tests/unit/test_api_control.py` y, con lo compartido aplicado, `tests/unit/test_api_acceso_por_ruta.py
  tests/unit/test_arquitectura.py` → PASAN; `ruff check` limpio.
- [ ] **Paso 5:** commits `test(mesa): cifras, obras y pendientes (rojo)` / `feat(mesa): cifras, obras y pendientes`.

### Tarea MOD-4b: Mesa de control (inicio de Presupuestos y obras)

**Archivos:**
- Crear: `src/paginas/obras/CifrasMesa.tsx`, `TablaObras.tsx`, `ColumnaPendientes.tsx`, `logica.ts`, `obras.scss`, `Mesa.test.tsx`,
  `logica.test.ts`
- Modificar: `src/paginas/obras/index.tsx` (de MOD-1), `src/paginas/obras/Obras.test.tsx`

**Interfaces:**
- `logica.ts`: los tipos de las respuestas de MOD-4a (`ResumenObrasRespuesta`, `CifraRespuesta` —la forma de
  `IndicadorRespuesta` más `detalle: string | null`—, `ObraFilaRespuesta`, `GrupoRespuesta`, `PendienteRespuesta`);
  `export type Bloque = "cifras" | "obras" | "pendientes" | "accesos"`; `export function bloquesPedidos(acciones:
  readonly string[]): Bloque[]` (cifras y obras con `leer_proyecto`, pendientes con `editar_hoja`, accesos si no hay ninguno de los
  otros); `export function etiquetaAvance(real: string | null, plan: string | null): string` («30,0 % de 37,5 %», o «Sin avance»);
  `export function gruposConItems(grupos: GrupoRespuesta[]): GrupoRespuesta[]` (quita los vacíos).
- Página: h1 «Inicio de presupuestos y obras»; «Nueva obra» (`kind="primary"`, solo con `editar_hoja`, abre `abrirNuevaObra()`);
  dos columnas `minmax(0, 1fr) 380px` cuando el contenedor tiene al menos 60 rem (consulta de contenedor), una sola debajo.
  Bloques, cada uno `section` con h2: «Cómo van las obras» (franja de `IndicadorFiori` con `rotuloMeta="Meta"`; debajo, las
  `conversiones` «C convertida a Bs con la tasa del BCV de 40,00 del 23/10/2026» y `fuera_de_suma` «Sin tasa del BCV: C no se
  sumó»), «Obras» (`TablaDensa`/Carbon `sm`: Obra —nombre y cliente—, Etapa —texto; «Atrasada» con `WarningFilled` y texto—,
  Avance, Total —`formatoEsVe` y moneda—, Qué pasa, Siguiente paso —botón `ghost sm`; la columna solo existe si alguna fila trae una
  acción cuya pantalla es visible para la cuenta—), «Pendientes» (columna de 380 px: grupos en el orden de la API, cada ítem con la
  obra, el texto y su botón), «Lo que puede hacer aquí» (`AccesosDelModulo`, solo si no se pidió ningún otro bloque).
- Cada bloque se pide por separado; **un 403 oculta el bloque** (no lo pinta vacío); otro error → `AvisoError` en línea en ese bloque
  y los demás siguen; cargando → `EsqueletoPagina`/esqueleto con la forma final (tres indicadores y filas). Sin obras: «Todavía no hay
  obras en esta carpeta de trabajo.» con «Cree su primera obra» (`abrirNuevaObra`) y «Probar con datos de demostración»
  (`POST /v1/casos/demostracion` y luego cambiar a `demostracion.db` por el `cambiarCarpeta` del armazón, que confirma); rita ve solo
  el texto. Todos los pendientes vacíos: «Nada pendiente por ahora.».
- «Siguiente paso» y la acción de un pendiente: `elegirObra(codigo)` y `useNavegarSeguro()(rutaDe({id: pagina}))`.

- [ ] **Paso 1: pruebas en rojo** (`fetch` simulado con las respuestas de MOD-4a; cifras de su prueba):
  - ana: «Valor ganado» muestra «70.000,00», meta «75.000,00» y la variación desfavorable con su palabra y flecha (no solo color);
    «Avance contra el plan» con «1 obra atrasada; la más atrasada, A: 3 días hábiles»; la conversión y el «Sin tasa del BCV: C no se
    sumó» con el texto exacto;
  - la tabla: OB-S2 con «Atrasada», «30,0 % de 37,5 %», el total en es-VE con su moneda, «Atrasada 3 días hábiles (SPI 0,80)» y el
    botón «Ver las alertas»; pulsarlo llama `PUT /v1/sesion/proyecto {"proyecto": <codigo>}` y navega a `/control`;
  - **foco 3:** con `useFormularioSucio("componer", true)` el botón pide «Cambios sin guardar» y «Quedarme» no navega ni elige obra;
  - pendientes: grupos «Precios» y «Calidad» con sus textos y botones; con todos los grupos vacíos, «Nada pendiente por ahora.»;
  - **foco 5:** rita → `/v1/obras/pendientes` no se pide (no tiene `editar_hoja`), cifras y obras sí, sin columna «Siguiente paso»
    ni «Nueva obra»; si `/v1/obras/resumen` responde 403, no hay h2 «Cómo van las obras» ni «Obras» (oculto, no vacío); admin →
    solo «Lo que puede hacer aquí» con «Precios de la empresa» e «Índices del BCV»; un 500 en pendientes muestra el aviso en esa
    columna y las cifras siguen;
  - sin obras (ana): el texto exacto y los dos botones; «Cree su primera obra» abre «Nueva obra»; «Probar con datos de
    demostración» llama `POST /v1/casos/demostracion`;
  - cargando: el esqueleto está y no hay cifras; un solo h1; ningún `Number(` en `src/paginas/obras/*.ts*` (prueba de fuente, como
    `sinJergaInterna.test.ts`).
- [ ] **Paso 2:** `cd frontend-desktop && npx vitest run src/paginas/obras` → FALLA.
- [ ] **Paso 3:** implementar (DESIGN.md y reglas anti-IA: la franja de cifras es una franja con divisores, no tres tarjetas
  sueltas; ninguna cifra fija en el código).
- [ ] **Paso 4:** misma orden, `npm run lint`, `npm run build` → PASAN.
- [ ] **Paso 5:** commits `test(front): mesa de control de las obras (rojo)` / `feat(front): mesa de control de las obras`.

### Tarea MOD-5: Recorridos, pulido de diseño con impeccable, DESIGN.md y manual

**Archivos:**
- Modificar: `scripts/recorrido_ux_playwright.py`, `scripts/recorrido_funcional.toml`, `src/shell/_umbrales.scss` (valores medidos),
  `frontend-desktop/DESIGN.md` §Marco (compartido), `CHANGELOG.md` (compartido)
- Crear: `docs/bitacora/2026-10-2x-modulos.md`, `docs/manual_nuevo/modulos.md` (capítulo; lo coordina el orquestador con quien
  lleva `docs/manual_nuevo/`)
- Prueba: los dos recorridos; arreglos que salgan del pulido, cada uno con su prueba en rojo en el archivo de la tarea dueña

- [ ] **Paso 1:** el script gana `--sidebar oculto,abierto,fijado` y recorre las 24 rutas por su módulo × ana/rita/admin × 1366 y
  1056 px × Normal/Grande/Muy grande; mide por captura: un h1, `scrollWidth <= clientWidth`, 0 errores de consola y red, axe sin
  violaciones nuevas frente a `docs/bitacora/2026-10-25-recorrido-ux-playwright.md`, `barra_cortada` (`header` con `scrollWidth >
  clientWidth`) falso, `panel_fuera` falso, `duplicados_nav` 0 (en barra y en el sidebar), y `sidebar_tapa` (fijado: el borde
  izquierdo de `main` es ≥ el borde derecho del sidebar) falso; `elegir_contexto` usa el selector de obra.
- [ ] **Paso 2:** con esas medidas fijar en `_umbrales.scss` el umbral de cada módulo y escala (el menor ancho en que la barra no se
  corta con el nombre de obra más largo de la siembra recortado) y anotar las cifras en la bitácora; volver a correr hasta que todo
  dé lo esperado.
- [ ] **Paso 3:** recorrido funcional: la fila `inicio` del TOML se cambia por `auditoria`, `obras` y `produccion` (acción principal:
  soltar el libro ficticio y ver el informe; crear una obra con «Nueva obra» y verla en la tabla; ver «Lo que requiere atención»),
  y cada fila entra **por el sidebar y el área de su módulo**, no por dirección; correr `--funcional` → todas las filas pasan o su
  defecto queda en la bitácora con dueño.
- [ ] **Paso 4:** pasada de diseño con las skills `impeccable critique` y luego `impeccable polish` (y `design-taste-frontend` como
  segunda mirada) sobre las capturas de los tres módulos: inicio de cada uno, sidebar en capa y fijado, mesa con datos, sin obras y
  con un bloque en error, con letra Normal y Muy grande. Cada hallazgo aceptado se corrige con TDD en el archivo de su tarea (árbitro
  incluido); los rechazados se anotan con su razón. Revisor de diseño (`.claude/agents/silice-rev-diseno.md`) al final.
- [ ] **Paso 5:** reescribir `DESIGN.md` §Marco (sidebar de módulos en capa y fijado, barra por módulo con «Sílice» y nombre del
  módulo, umbrales por módulo y de fijado, selector de obra, marca de demostración, mesa de control); capítulo del manual con
  capturas ficticias; línea de `CHANGELOG.md`.
- [ ] **Paso 6:** cierre de fase: `uv run --active pytest -q -W error -p no:cacheprovider` (suite completa), `npx vitest run`,
  `npm run lint`, `npm run build`, `ruff check scripts/recorrido_ux_playwright.py`, `git diff <base>..HEAD -- core/ seguridad/permisos.py`
  vacío.
- [ ] **Paso 7:** commits `test(front): recorridos por modulo` / `docs(front): diseno de los modulos, bitacora y manual`.

## Cierre

Árbitro por tarea (criterios A1-F1 de `MANUAL_ARBITRO.md`; D1 incluye las reglas anti-IA de «Restricciones globales»); el
orquestador aplica los compartidos de cada informe en el orden de las olas y corre `tests/unit/test_api_acceso_por_ruta.py`,
`tests/integration/test_migraciones.py` y `tests/unit/test_front_rutas_api.py` tras cada integración. Sin push ni PR.

## Decisiones que solo puede tomar Eugenio (las demás son de ingeniería y quedan registradas arriba)

1. Retirar los tres mosaicos de «Herramientas principales» (el sidebar hace su papel; choque 7).
2. Un área de una sola pantalla se rotula con el nombre del área (rita ve «Obras» y abre el Tablero; choque 8).
3. Módulo de una cuenta que nunca eligió: el primero visible en el orden Auditoría, Presupuestos y obras, Producción (ana y rita
   entran en Auditoría; el administrador en Presupuestos y obras). ¿Prefiere que quien arma entre en Presupuestos y obras?
4. Con el sidebar fijado, «Sílice» lleva el foco al sidebar en vez de ocultarlo, y Esc no hace nada (ya está a la vista).
5. La mesa del administrador muestra solo los accesos de Mercado (choque 11).
6. «Avance contra el plan» dice debajo cuántas obras van atrasadas y cuál va peor, en días hábiles (choque 12).
7. La marca «Demostración» se ve en la barra de los tres módulos, no solo en Presupuestos y obras.
