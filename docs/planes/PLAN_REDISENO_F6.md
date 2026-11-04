# Rediseño F6: espacios enrutados con barra superior propia — plan de construcción

> **Para quien ejecuta:** úsese superpowers:subagent-driven-development. Cada tarea la construye un subagente de
> Claude (`silice-frontend`; la Tarea 6 también `silice-backend` si Eugenio decide la ruta nueva) y la **arbitra
> Antigravity** con la skill `arbitro-independiente` (herramienta MCP `arbitrar_rama` o `agy -p … --sandbox`). El
> orquestador verifica cada hallazgo de Antigravity contra el código antes de devolver la tarea: un veredicto no es una
> orden. Las casillas (`- [ ]`) son para el seguimiento.

**Objetivo:** que cada área de Sílice (Inicio, la obra, Producción, Auditoría, Precios y la Cuenta) sea una ruta con su
cabecera y una barra superior con sus herramientas, y que ninguna pantalla quede alcanzable solo por Ctrl+K sin decidirlo.

**Arquitectura:** un registro único de espacios (`marco/espacios.ts`) dice qué pantalla de `shell/rutas.ts` vive en cada
espacio. Una sola pieza, `BarraDeEspacio`, pinta la barra superior de todos. El marco (`Marco.tsx`) gana las familias de
rutas y redirige las viejas. Las pantallas no se reescriben: se montan como hoy por su `id` (patrón estrangulador).

**Tecnología:** React 19 + TypeScript, `react-router` (HashRouter), `@carbon/react` g10, SCSS propio, Vitest + Testing
Library; Playwright para la pasada en navegador.

**Especificación:** [2026-11-04-rediseno-f6-espacios-design.md](../especificaciones/2026-11-04-rediseno-f6-espacios-design.md)
y su [maqueta](../especificaciones/2026-11-04-rediseno-f6-maqueta.html), ambas propuestas por Antigravity y aprobadas
por Eugenio el 2026-11-04. Este plan corrige tres puntos de la especificación (ver «Decisiones»). Ronda 1 de Antigravity: DEVUELTO con 4 mayores y 2 menores, todos verificados y aplicados. Ronda 2: **APROBADO**, con dos notas menores ya anotadas en sus tareas.

**Rama:** `feature/f6-espacios`, desde `main` después de fusionar #103, #104 y #102.

## Restricciones globales

- IBM Carbon g10, esquinas rectas, densidad `sm`; **sin Tailwind**; morado (`#8a3ffc`) solo para atípicos de ML
  (`frontend-desktop/DESIGN.md`).
- Un solo `h1` por pantalla; la barra superior de un espacio es `nav` con `aria-label`, no un segundo `h1`.
- Sin desplazamiento horizontal a 1056, 1366 y 1920 px con letra Normal, Grande y Muy grande.
- `src/paginas/sinJergaInterna.test.ts` en verde: palabras de quien usa el programa, ningún id interno a la vista.
- La interfaz **no calcula**: muestra cifras que da el servidor; contar elementos de una lista sí se permite.
- Coma decimal y punto de miles en toda cifra.
- `core/` intacto; ningún dato real (todo con la siembra ficticia de `start.py`).
- TDD con rojo visto y commit de la prueba aparte; asunto del commit en español y sin tildes.

## Decisiones (prudentes y reversibles; Eugenio puede cambiarlas)

| # | Tema | Lo que se hará |
|---|---|---|
| D1 | Las 18 pantallas sueltas (la especificación dice 14) | Producción: `produccion`, `existencias`, `costos`, `costo_tonelada`, `receta_planta`, `producir_mezcla`. Auditoría: `auditoria`, `libros`, `revisar`, `historial`. Precios: `precios_empresa`, `catalogo`, `componer`, `actualizacion`, `indices`, `simulador`, `reajuste`. Obra: `tablero` y `riesgo` como secciones nuevas (cada una con su módulo). Solo buscador, a propósito: `entregar` (se llega desde Aprobaciones) y `escenarios` |
| D2 | Panorama de la empresa (KPI y gráficos) | Solo con datos que la API ya da: cifras de la mesa y avance real contra plan por obra (`GET /v1/obras/resumen`), pendientes, últimas auditorías (conteos) y existencias y costo por tonelada. **Quedan fuera** hasta que Eugenio pida la ruta del servidor: la meta de la cartera, la curva S de la cartera, el anillo del APU de la cartera y el Δ en dinero de las auditorías |
| D3 | Alcance del panorama | La carpeta abierta, como la mesa de hoy; la cabecera lo dice («Carpeta activa: …») |
| D4 | Tamaño de letra | Sale de la barra superior y vive en `#/cuenta/preferencias`, como aprobó Eugenio; el atajo del menú de la cuenta se conserva |
| D5 | Ajustes de la instalación | `#/cuenta/:seccion` reparte las pestañas de Administración; quien no tiene el permiso no ve la pestaña |

## Foco de revisión

1. **Enlaces viejos** (`#/pendientes`, `#/empresa/<entrada>`, `#/<paginaId>?proyecto=…`, favoritos del navegador):
   redirigen a la ruta nueva conservando la consulta, nunca a una página en blanco (Tarea 3 y Tarea 6).
2. **Sin permiso o con el módulo apagado:** la pestaña no aparece y la dirección escrita a mano muestra el aviso de
   siempre, no una pantalla vacía (Tarea 2 y Tarea 3).
3. **Cambiar de obra con cambios sin guardar:** la barra lateral plana pregunta igual que hoy (`quedaEnLaHoja`)
   (Tarea 4).
4. **Salir desde la Cuenta con un borrador de la Hoja abierto:** sin el 401 de `DELETE /v1/hoja/borradores/{id}`, que
   ya se vio en vivo el 2026-11-04 (Tarea 5).
5. **Quien revisa** (solo la carpeta de la empresa): ni el panorama ni la barra lateral le ofrecen obras que no puede
   abrir (Tarea 6).
6. **Botones que viven fuera del marco** (pendientes, Resumen de la obra, recorridos guiados): cada uno lleva a la ruta
   nueva de su pantalla, no al Resumen de la obra por descarte (Tarea 3; ronda 1 de Antigravity).

---

### Tarea 1: Registro de espacios y oráculo de ubicación

**Archivos:**
- Crear: `frontend-desktop/src/marco/espacios.ts`
- Crear: `frontend-desktop/src/marco/espacios.test.ts`
- Modificar: `frontend-desktop/src/marco/secciones.ts` (secciones `tablero` y `riesgo`, D1)

**Interfaces:**
- Produce:
  - `type EspacioId = "produccion" | "auditoria" | "precios"`.
  - `interface HerramientaDef { id: string; titulo: string; pagina: string }`, donde `id` es el segmento de la ruta.
  - `ESPACIOS: Record<EspacioId, { titulo: string; herramientas: readonly HerramientaDef[] }>`.
  - `type CuentaId = "preferencias" | "cuentas" | "empresa" | "carpetas" | "sistema" | "ayuda"`.
  - `SECCIONES_DE_CUENTA: readonly { id: CuentaId; titulo: string }[]`.
  - `SOLO_BUSCADOR: readonly string[]`, con valor `["entregar", "escenarios"]`.
  - `rutaDeHerramienta(espacio: EspacioId, herramienta: string): string`, que devuelve `/<espacio>/<herramienta>`.
  - `rutaDeCuenta(seccion: CuentaId): string`.
  - `espacioDeLaPagina(paginaId: string)`, que devuelve `{ espacio: EspacioId; herramienta: string } | null`.
- `SeccionId` gana `"tablero" | "riesgo"`.

- [ ] **Paso 1: prueba roja.** Escribir `cada pantalla tiene exactamente un lugar`:
  - una lista escrita a mano con los 31 ids de `PAGINAS` (no derivada de `PAGINAS`: el oráculo no copia al código);
  - para cada id, cuenta en cuántos sitios aparece: secciones de obra, herramientas de los tres espacios, `SOLO_BUSCADOR`
    y las dos pantallas que monta la Cuenta (`administracion`, `acerca`);
  - `expect(conteo).toEqual(Object.fromEntries(ids.map((id) => [id, 1])))`.

  Escribir también `la ruta de una herramienta es /espacio/herramienta`:
  `expect(rutaDeHerramienta("precios", "catalogo")).toBe("/precios/catalogo")`.
- [ ] **Paso 2:** correr `npx vitest run src/marco/espacios.test.ts`. Esperado: FALLA (el módulo no existe).
- [ ] **Paso 3:** implementar `espacios.ts` con el reparto de D1. Los títulos de las pestañas son los de la
  especificación §2. Segmento de ruta → pantalla, en este orden (la primera es la que abre el espacio):
  - Producción: `resumen`→`produccion`, `existencias`→`existencias`, `costos`→`costos`,
    `costo-tonelada`→`costo_tonelada`, `receta`→`receta_planta`, `mezcla`→`producir_mezcla`.
  - Auditoría: `subir`→`auditoria`, `libros`→`libros`, `revisar`→`revisar`, `historial`→`historial`.
  - Precios: `listas`→`precios_empresa`, `catalogo`→`catalogo`, `componer`→`componer`,
    `actualizar`→`actualizacion`, `indices`→`indices`, `simulador`→`simulador`, `reajuste`→`reajuste`.
- [ ] **Paso 4:** correr `npx vitest run src/marco`. Esperado: PASA, y también `sinJergaInterna.test.ts`.
- [ ] **Paso 5:** commits `test(marco): cada pantalla tiene un solo lugar (rojo)` y
  `feat(marco): registro de espacios y herramientas`.

### Tarea 2: `BarraDeEspacio`, la barra superior común

**Archivos:**
- Crear: `frontend-desktop/src/marco/BarraDeEspacio.tsx`, `BarraDeEspacio.test.tsx`
- Modificar: `frontend-desktop/src/marco/marco.scss` (o el SCSS del marco que corresponda)

**Interfaces:**
- Consume: `HerramientaDef` (Tarea 1), `usable` y `paginaPorId` (`shell/rutas.ts`), `useOferta` (`marco/oferta.ts`).
- Produce: `BarraDeEspacio({ etiqueta, pestanas, activa }: { etiqueta: string; pestanas: readonly { id: string; titulo: string; ruta: string }[]; activa: string })`.
  Pinta un `nav aria-label={etiqueta}` con enlaces (`Link`) y `aria-current="page"` en la activa. La raya inferior es
  de 3 px `--silice-complementario` y el contenedor lleva `flex-wrap: wrap`. **No filtra**: quien la llama le pasa solo
  lo usable.
- Produce: `pestanasUsables(herramientas, acciones, modoEntrega, apagados)`, que devuelve
  `{ id: string; titulo: string; ruta: string }[]`.

- [ ] **Paso 1: pruebas rojas.**
  - `marca la activa con aria-current`.
  - `una herramienta sin permiso no se ofrece`: `pestanasUsables` con acciones vacías no incluye `costos`, que exige
    `registrar_costos_produccion`.
  - `con el módulo apagado no se ofrece su herramienta`: con `apagados=["produccion"]`, cero pestañas de Producción.
  - `Tab recorre las pestañas en orden`.
- [ ] **Paso 2:** correr `npx vitest run src/marco/BarraDeEspacio.test.tsx`. Esperado: FALLA.
- [ ] **Paso 3:** implementar.
- [ ] **Paso 4:** correr `npx vitest run src/marco`. Esperado: PASA.
- [ ] **Paso 5:** commits rojo y verde.

### Tarea 3: Espacios de Producción, Auditoría y Precios, y redirecciones

**Archivos:**
- Crear: `frontend-desktop/src/marco/EspacioDeHerramientas.tsx`, `EspacioDeHerramientas.test.tsx`
- Modificar: `frontend-desktop/src/marco/Marco.tsx` (rutas `/:espacio/:herramienta` y redirecciones),
  `marco/secciones.ts` (`ENTRADAS_DE_EMPRESA` deja de tener `precios`, `auditoria` y `produccion`),
  `marco/busqueda.ts` (las herramientas se buscan con su ruta nueva), `marco/oferta.ts` (`conSitio` suma `ESPACIOS`,
  `SECCIONES_DE_CUENTA` y `SOLO_BUSCADOR`), `paginas/pendientes/logica.ts` (`destino` resuelve una pantalla de un espacio
  con `espacioDeLaPagina`), `shell/recorrido.ts` y `shell/PanelRecorrido.tsx` (`pasoDeRuta` y sus enlaces usan la
  ruta del espacio), y `marco/ubicar.ts` (título del documento para `/:espacio/:herramienta`)

**Interfaces:**
- Consume: `ESPACIOS`, `rutaDeHerramienta` y `espacioDeLaPagina` (Tarea 1), y `BarraDeEspacio` con `pestanasUsables`
  (Tarea 2).
- Produce:
  - `EspacioDeHerramientas({ espacio, pantalla }: { espacio: EspacioId; pantalla: (p: PaginaDef) => ReactNode })`.
    Pinta la cabecera del espacio (`titulo`, sin `h1`), la barra y la pantalla de la herramienta de la URL.
  - `PATRON_DE_HERRAMIENTA = "/:espacio/:herramienta"`.

- [ ] **Paso 1: pruebas rojas.**
  - `#/precios/catalogo monta el catálogo con su barra`.
  - `una herramienta sin permiso escrita a mano muestra el aviso de permiso` (el mismo texto que da hoy la pantalla).
  - `una herramienta que no existe lleva a la primera del espacio`.
  - Una tabla escrita a mano de redirecciones, que conserva `?…`:
    - `#/catalogo` → `#/precios/catalogo`;
    - `#/costos` → `#/produccion/costos`;
    - `#/empresa/precios` → `#/precios/catalogo` (un enlace viejo abre lo mismo que abría en F4);
    - `#/empresa/auditoria` → `#/auditoria/subir`;
    - `#/empresa/produccion` → `#/produccion/existencias`.
  - `un pendiente que lleva al catálogo abre #/precios/catalogo, no el Resumen de la obra` (`destino` de
    `paginas/pendientes/logica.ts` con `id: "catalogo"`).
  - `el recorrido guiado de la auditoría reconoce su paso en #/auditoria/libros` (`pasoDeRuta`).
  - `el título del documento de #/produccion/costos es «Costos del período»` (`ubicar`).
- [ ] **Paso 2:** correr `npx vitest run src/marco`. Esperado: FALLA.
- [ ] **Paso 3:** implementar. Las rutas de una sola pieza (`/<paginaId>`) que sean herramienta redirigen con
  `espacioDeLaPagina`. Las secciones de obra siguen con su redirección de hoy (`Marco.tsx:437-442`).
- Nota m2 de la ronda 2: `paginas/pendientes/logica.test.ts` usa `tablero` como pantalla sin sección; al volverse sección
  (Tarea 1) se cambia ese ejemplo por `escenarios`. `ABSORBIDAS` se queda igual: un pendiente de «actualizar precios»
  es de una obra y sigue abriendo su Mercado; la herramienta `actualizar` de Precios es para entrar directo.
- [ ] **Paso 4:** correr `npx vitest run src/marco src/shell src/paginas/pendientes src/paginas/sinJergaInterna.test.ts`.
  Esperado: PASA. La guardia de jerga revisa todo `src/marco/**`: ni «módulo», ni «área», ni «página» en textos a la
  vista.
- [ ] **Paso 5:** commits rojo y verde.

### Tarea 4: La obra con su barra debajo de la cabecera y la barra lateral plana

**Archivos:**
- Modificar: `frontend-desktop/src/marco/CabeceraDeObra.tsx`, `marco/EspacioDeObra.tsx`, `marco/BarraLateral.tsx`
  y sus pruebas

**Interfaces:**
- Consume: `BarraDeEspacio` (Tarea 2), `seccionesDeLaObra` y `rutaDeObra` (`marco/secciones.ts`, `marco/oferta.ts`) y
  `quedaEnLaHoja`.
- Produce: `BarraLateral` muestra, en este orden:
  - «Vista general», con la píldora de pendientes;
  - «Obras», en lista plana: una fila por obra, sin sub-árbol;
  - «Costos y producción», con «Auditar un presupuesto», «Precios y catálogo» y «Costos de producción».

  Al pulsar una obra se va a su misma sección si existe; si no, a `resumen`.

- [ ] **Paso 1: pruebas rojas.**
  - `la barra de la obra va justo debajo de su cabecera`; `Riesgo` desaparece con el módulo `riesgo` apagado y `Tramos`
    con `vial`; `Tablero` no tiene módulo: depende solo de `leer_proyecto` (nota m1 de la ronda 2).
  - `la barra lateral no tiene sub-árbol de secciones`.
  - `pulsar otra obra estando en Versiones abre Versiones de esa obra`.
  - `cambiar de obra con cambios sin guardar pregunta antes` (la misma confirmación de hoy).
- [ ] **Paso 2:** correr `npx vitest run src/marco`. Esperado: FALLA.
- [ ] **Paso 3:** implementar. `ProveedorDeLaHoja` sigue envolviendo las secciones con Hoja.
- [ ] **Paso 4:** correr `npx vitest run src/marco src/paginas/hoja`. Esperado: PASA.
- [ ] **Paso 5:** commits rojo y verde.

### Tarea 5: La Cuenta (`#/cuenta/:seccion`) y la barra de arriba sin migas

**Archivos:**
- Crear: `frontend-desktop/src/marco/EspacioDeCuenta.tsx`, `EspacioDeCuenta.test.tsx`
- Modificar:
  - `frontend-desktop/src/marco/BarraSuperior.tsx`: quitar `TamanoLetra` y las migas; el botón de la persona lleva a
    `/cuenta/preferencias`.
  - `paginas/administracion/index.tsx`: exportar `CONTENIDOS` por id de pestaña, para montarlos por sección.
  - `paginas/hoja/useBorrador.ts`.
  - `sesion/useSesion.ts`.
  - `marco/Marco.tsx`: nuevas props de `BarraSuperior`, ruta `/cuenta/:seccion` y redirecciones (`#/empresa/personas`
    y `#/administracion` → `#/cuenta/cuentas`; `#/empresa/ayuda` y `#/acerca` → `#/cuenta/ayuda`).
  - `marco/ubicar.ts`: título del documento para `/cuenta/:seccion`.
  - `marco/secciones.ts`: `ENTRADAS_DE_EMPRESA` queda vacía y se retira junto con `ZonaEmpresa.tsx` si nadie más la
    usa.
  - En `BarraSuperior.tsx`, además: la marca «Sílice» enlaza a `/inicio/general` y la barra muestra la carpeta activa
    (especificación §1).

**Interfaces:**
- Consume: `SECCIONES_DE_CUENTA` y `rutaDeCuenta` (Tarea 1), `BarraDeEspacio` (Tarea 2), `TamanoLetra`, las pestañas
  de `paginas/administracion/logica.ts` y `paginas/acerca`.
- Produce: `EspacioDeCuenta()`. La cabecera lleva las iniciales, el nombre, el rol y el botón «Salir de la sesión». Las
  secciones se reparten así:
  - `preferencias`: `TamanoLetra` y datos de la cuenta;
  - `cuentas`: Cuentas y Accesos;
  - `empresa`: Empresa y clave de firma, y Empresas registradas;
  - `carpetas`: Carpetas de trabajo, solo con `cambiar_caso`;
  - `sistema`: Especialidades, Asistente de IA, Claves de API e Instalación;
  - `ayuda`: Acerca de Sílice y el inicio de los recorridos guiados (`shell/recorrido.ts`).

- [ ] **Paso 1: pruebas rojas.**
  - `sin administrar_cuentas la Cuenta solo ofrece Pantalla y tamaño de letra y Ayuda`.
  - `la barra de arriba no tiene migas ni tamaño de letra, y «Sílice» lleva al Inicio`.
  - `#/acerca y #/empresa/personas llevan a la Cuenta`.
  - `tras cambiar de carpeta se vuelve a #/cuenta/carpetas con el foco en la pestaña` (hoy lo hace
    `tomarVueltaACarpetas` en `paginas/administracion/index.tsx:61-65`).
  - `Salir con un borrador abierto no pide DELETE del borrador después de cerrar la sesión`: un mock de `fetch` que
    registra el orden. Esperado: ningún `DELETE /v1/hoja/borradores/…` después de `DELETE /v1/sesion`.
- [ ] **Paso 2:** correr `npx vitest run src/marco src/sesion src/paginas/hoja src/paginas/administracion`. Esperado:
  FALLA.
- [ ] **Paso 3:** implementar. Para el 401, el desmontaje de `useBorrador` no descarta si la sesión ya está cerrándose
  (bandera en `useSesion.salir` antes del `DELETE /v1/sesion`). No hace falta pedir nada más al servidor:
  `DELETE /v1/sesion` ya descarta los borradores de la ficha (`api/rutas/sesion.py:420` → `caso_web.olvidar` →
  `hoja_borradores.olvidar`, `api/caso_web.py:43-46`; corregido por Antigravity en la ronda 1).
- [ ] **Paso 4:** correr el mismo comando. Esperado: PASA.
- [ ] **Paso 5:** commits rojo y verde.

### Tarea 6: Inicio (`#/inicio/general` y `#/inicio/pendientes`)

**Archivos:**
- Crear: `frontend-desktop/src/paginas/inicio/Panorama.tsx`, `Panorama.test.tsx`, `marco/EspacioDeInicio.tsx`
- Modificar: `marco/Marco.tsx` (la ruta índice va a `/inicio/general` y `/pendientes` redirige a
  `/inicio/pendientes`), `marco/secciones.ts` (`RUTA_DE_INICIO`), `marco/usePendientes.ts` (recarga al volver a
  `/inicio/general` o `/inicio/pendientes`, no solo en `/pendientes`), `marco/EspacioDeObra.tsx:81` (su enlace a
  Pendientes) y `marco/ubicar.ts` (título para `/inicio/:vista`)

**Interfaces:**
- Consume:
  - `GET /v1/obras/resumen` (`cifras`, `obras[].avance_real` y `obras[].avance_plan`, `conversiones`,
    `fuera_de_suma`);
  - `usePendientes`;
  - `UltimasAuditorias` y `PanelArenera` (`paginas/inicio/`);
  - `IndicadorFiori` y `ibcs.ts` (`src/indicadores/`);
  - `GraficoCarbon` y `PALETA_GRAFICOS` (`src/comun/`).
- Produce: `Panorama()`, en tres franjas:
  1. Indicadores: cifras de la mesa, pendientes (bloquean y avisos, contados de la lista) y auditorías recientes
     (errores y advertencias).
  2. Avance real contra plan por obra, como barras IBCS: real relleno `#161616`, plan en contorno `#8d8d8d`.
  3. Últimas auditorías y existencias de la arenera, con «Ir a Auditoría» e «Ir a Producción».

- [ ] **Paso 1: pruebas rojas.**
  - `las cifras son las del servidor, sin recalcular`: un mock de `/v1/obras/resumen` con `actual: "334570.5"`; la
    pantalla muestra `334.570,50`.
  - `una obra sin avance no dibuja barra y lo dice` («Sin avance»).
  - `quien revisa sin obras ve el estado vacío, no un error`.
  - `#/pendientes lleva a #/inicio/pendientes`.
  - `volver al Inicio desde una obra recarga los pendientes` (lo resuelto en la obra no queda viejo).
  - `un bloque que falla no tumba los demás` (el patrón de `useCarga` de `paginas/inicio`).
- [ ] **Paso 2:** correr `npx vitest run src/paginas/inicio src/marco`. Esperado: FALLA.
- [ ] **Paso 3:** implementar con D2 y D3. Ningún número se calcula en el cliente salvo contar elementos.
- [ ] **Paso 4:** correr el mismo comando y `npm run lint`. Esperado: PASA.
- [ ] **Paso 5:** commits rojo y verde.

### Tarea 7: Cierre de F6

**Archivos:**
- Modificar:
  - `frontend-desktop/DESIGN.md`: espacios, barra de espacio y panorama;
  - `CHANGELOG.md`;
  - `scripts/recorrido_ux_playwright.py` y `scripts/recorrido_funcional.toml`: rutas nuevas;
  - `docs/manual_usuario.md`: las rutas y las capturas que cambian;
  - `docs/ESTADO.md`.
- Crear: `docs/bitacora/2026-11-XX-cierre-f6.md`

- [ ] **Paso 1:** suite completa:
  - `uv run --active pytest -W error -q`: 0 fallas, 0 omitidas;
  - `npx vitest run --maxWorkers=3`, `npm run lint` y `npm run build`;
  - `node scripts/verificar_dist.mjs`.
- [ ] **Paso 2:** pasada en Chromium visible con la siembra ficticia (el guion de vivo del 2026-11-04):
  - las 4 familias de rutas a 1056, 1366 y 1920 px con las 3 letras;
  - un `h1` por pantalla, sin desplazamiento horizontal y sin errores de consola de la app;
  - como ana, rita y admin.
- [ ] **Paso 3:** Antigravity arbitra la rama entera (`arbitrar_rama feature/f6-espacios main`) y el orquestador
  dictamina cada hallazgo.
- [ ] **Paso 4:** PR a `main`. Eugenio prueba y fusiona.

## Árbitro por tarea

| Paso | Quién |
|---|---|
| Construir | Subagente de Claude, con la tarea entera y las skills `metodologia-silice` y `front-carbon-fiori-ibcs` |
| Arbitrar | Antigravity: `arbitrar_rama(rama, base, foco="Tarea N de docs/planes/PLAN_REDISENO_F6.md")` |
| Decidir | El orquestador verifica cada hallazgo con el código: confirmado → vuelve al constructor; falso positivo → se anota en `docs/bitacora/auditoria-agy-AAAA-MM-DD.md` con la razón |
| Rondas | Hasta 3; en la tercera, lo que siga abierto se escala a Eugenio |
