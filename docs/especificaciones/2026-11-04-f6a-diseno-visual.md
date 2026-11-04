# Especificación Visual de la Entrega F6a (Tareas 1 a 5): Rutas, Espacios y Barras

> **Autor:** Antigravity (diseño visual, según el reparto acordado con Claude el 2026-11-04; entregado por `agy -p`).
> **Revisado por Claude** contra el código de `feature/f5-pulido` (citas comprobadas: mensajes de `Marco.tsx:52-53`,
> guardia `sinJergaInterna.test.ts:48`, `h1` de Tablero y de Acerca, ancho de la barra lateral). **Conciliación con el
> [contrato de rutas](2026-11-04-f6a-contrato-de-rutas.md)**, que manda en permisos:
> - Se adopta de este diseño: la pestaña se llama **«Carpetas»** (la guardia prohíbe «carpeta de trabajo» en
>   `src/marco/`) y un espacio sin herramientas usables muestra el aviso de permiso existente, sin texto nuevo (§5.3).
> - Se corrige en este diseño: «Carpetas» exige `administrar_cuentas` **y** `cambiar_caso`, y «Especialidades, IA e
>   instalación» exige `administrar_cuentas` (§5.1 y §6.3 decían otra cosa; así se conservan los permisos de hoy).


**Rama objetivo:** `feature/f6-espacios`
**Plan de referencia:** [PLAN_REDISENO_F6.md](../../docs/planes/PLAN_REDISENO_F6.md#L64-L246)
**Sistema de diseño:** [DESIGN.md](../../frontend-desktop/DESIGN.md#L18-L145) y [tokens.scss](../../frontend-desktop/src/estilos/tokens.scss#L18-L95) (IBM Carbon `g10` oficial, esquinas rectas `border-radius: 0`, sin sombras ni animaciones decorativas, unidades en `rem` escaladas por `--silice-escala-letra`).

---

## 1. `BarraDeEspacio` (`src/marco/BarraDeEspacio.tsx` y `src/marco/marco.scss`)

Pieza horizontal común que pinta las pestañas enrutadas de cada espacio (`Producción`, `Auditoría`, `Precios`, `Obra`, `Cuenta` y, en F6b, `Inicio`). No filtra por su cuenta: recibe de [`pestanasUsables`](../../docs/planes/PLAN_REDISENO_F6.md#L116-L117) únicamente las pestañas que pasan [`usable`](../../frontend-desktop/src/shell/rutas.ts#L309-L313).

### 1.1. Estructura DOM y semántica WAI-ARIA
- **Contenedor:** `<nav aria-label={etiqueta} className="silice-barra-espacio">` (nunca un `role="tablist"`, porque cada pestaña navega a su propia URL con `<Link>` y monta una ruta completa, no un panel local oculto).
- **Elementos hijos:** enlaces `<Link to={p.ruta} aria-current={p.id === activa ? "page" : undefined} className="silice-barra-espacio__pestana">`.
- **Recorrido de teclado:** `Tab` recorre los enlaces en orden natural de lectura (sin `tabIndex={-1}` ni roving tabindex de árbol).

### 1.2. Medidas en `rem`, tipografía y tokens Carbon `g10`

| Propiedad | Valor exacto | Token / Fuente reutilizada |
|---|---|---|
| **Disposición del `<nav>`** | `display: flex; flex-wrap: wrap; align-items: stretch; gap: 0;` | [PLAN_REDISENO_F6.md](../../docs/planes/PLAN_REDISENO_F6.md#L112-L115) |
| **Relleno horizontal del `<nav>`** | `padding-inline: 1rem` | Alineado con `.silice-obra-abierta` ([marco.scss](../../frontend-desktop/src/marco/marco.scss#L182)) y `.silice-pagina` ([comun.scss](../../frontend-desktop/src/comun/comun.scss#L114)) |
| **Fondo del `<nav>`** | `background-color: var(--cds-layer-01)` | Continuidad visual bajo `.silice-obra-abierta` ([marco.scss](../../frontend-desktop/src/marco/marco.scss#L184)) |
| **Divisor inferior del `<nav>`** | `border-block-end: 1px solid var(--cds-border-subtle)` | Divisor estándar Carbon `g10` ([DESIGN.md](../../frontend-desktop/DESIGN.md#L33-L34), [marco.scss](../../frontend-desktop/src/marco/marco.scss#L183)) |
| **Alto de cada pestaña (`.silice-barra-espacio__pestana`)** | `min-block-size: 2.5rem` (y `min-block-size: 2rem` dentro de `@include u.con-letra-grande`) | Mismo blanco de puntero que los controles horizontales del marco ([BarraLateral.scss](../../frontend-desktop/src/marco/BarraLateral.scss#L79-L80), [BarraLateral.scss](../../frontend-desktop/src/marco/BarraLateral.scss#L190)) |
| **Relleno de cada pestaña** | `padding-block: 0.5rem; padding-inline: 0.75rem;` (`padding-block: 0.375rem; padding-inline: 0.625rem;` en `@include u.con-letra-grande`) | Escala productiva Carbon ([BarraSuperior.scss](../../frontend-desktop/src/marco/BarraSuperior.scss#L95)) |
| **Tipografía** | `@include type.type-style("body-compact-01")`; `white-space: nowrap; text-decoration: none;` | [DESIGN.md](../../frontend-desktop/DESIGN.md#L25-L27), [BarraLateral.scss](../../frontend-desktop/src/marco/BarraLateral.scss#L83-L84) |
| ** Estado inactivo** | `color: var(--cds-text-secondary); font-weight: 400; border-block-end: 3px solid transparent;` | Reserva los `3px` siempre para evitar desplazamiento vertical al activarse ([BarraLateral.scss](../../frontend-desktop/src/marco/BarraLateral.scss#L72-L81)) |
| **Estado `:hover` (inactiva)** | `background-color: var(--cds-layer-hover-01); color: var(--cds-text-primary);` | Token oficial de hover sobre `layer-01` ([MenuCuenta.scss](../../frontend-desktop/src/shell/MenuCuenta.scss#L70)) |
| **Estado activo (`[aria-current="page"]`)** | `color: var(--cds-text-primary); font-weight: 600; background-color: var(--cds-background); border-block-end: 3px solid var(--silice-complementario);` | Papel de color **Acción** sobre fondo claro ([DESIGN.md](../../frontend-desktop/DESIGN.md#L75-L76), [DESIGN.md](../../frontend-desktop/DESIGN.md#L91), [tokens.scss](../../frontend-desktop/src/estilos/tokens.scss#L48-L50)) |
| **Foco visible (`:focus-visible`)** | `outline: 2px solid var(--cds-focus); outline-offset: -2px;` | Anillo hacia adentro para no quedar cortado por bordes contiguos ([BarraLateral.scss](../../frontend-desktop/src/marco/BarraLateral.scss#L95-L98), [comun.scss](../../frontend-desktop/src/comun/comun.scss#L172-L175)) |

### 1.3. Comportamiento al hacer wrap a `1056 px` con letra `Muy grande` y con las 10 pestañas de una obra
- En `html[data-silice-letra="muy-grande"]`, `--silice-escala-letra` vale `1.5` ([preferenciaDeLetra.ts](../../frontend-desktop/src/comun/preferenciaDeLetra.ts#L21)) y la raíz vale `calc(116.6667% * 1.5)` = `175%` (`1 rem = 28 px` con navegador a `16 px`, [app.scss](../../frontend-desktop/src/estilos/app.scss#L14)).
- A `1056 px` de ventana, la barra lateral fija de `14.75rem` ocupa `413 px` (`14.75 * 28 px`), dejando `643 px` libres para `<main className="silice-contenido">` ([BarraLateral.scss](../../frontend-desktop/src/marco/BarraLateral.scss#L10)).
- Cuando una obra tiene sus **10 pestañas** activas (`Resumen`, `Presupuesto`, `Tramos`, `Archivos y planos`, `Versiones`, `Aprobaciones`, `Mercado`, `Control de obra`, `Tablero`, `Riesgo`), `flex-wrap: wrap` reparte las pestañas en 2 o 3 renglones dentro de `.silice-barra-espacio` sin generar jamás scroll horizontal ni ocultar pestañas tras botones de desbordamiento.
- Cada renglón conserva su `border-block-end: 3px solid transparent` (o `var(--silice-complementario)` en la activa), de modo que la raya activa acompaña siempre al texto de su pestaña aunque quede en la primera o segunda fila, y el borde inferior de `1px solid var(--cds-border-subtle)` del `<nav>` cierra limpiamente el bloque completo antes del lienzo de la pantalla.

---

## 2. Cabecera de cada espacio y regla de un solo `h1` por pantalla

Restricción global de [PLAN_REDISENO_F6.md](../../docs/planes/PLAN_REDISENO_F6.md#L29) y [DESIGN.md](../../frontend-desktop/DESIGN.md#L128-L131): **ninguna cabecera de espacio ni ninguna `BarraDeEspacio` usa `<h1>`**. El único `<h1>` de toda ruta es el que ya pinta la pantalla activa dentro del lienzo (al cual [`useFocoAlTitulo`](../../frontend-desktop/src/marco/Marco.tsx#L467-L478) y [`enfocarElTitulo`](../../frontend-desktop/src/marco/EspacioDeObra.tsx#L68) mueven el foco al navegar).

### 2.1. Cabecera de los 3 espacios de herramientas (`EspacioDeHerramientas.tsx`: Producción, Auditoría, Precios)
- **Elemento contenedor:** `<section aria-label={tituloDelEspacio} className="silice-espacio-cabecera">`.
- **Título visual del espacio (sin `h1`):** `<p className="silice-espacio-cabecera__titulo">` con `@include type.type-style("body-compact-02")`, `font-weight: 600`, `margin: 0`, `color: var(--cds-text-primary)` (idéntico a `.silice-obra-abierta__nombre` en [marco.scss](../../frontend-desktop/src/marco/marco.scss#L186-L190)).
- **Caja y bordes:** `padding: 0.75rem 1rem; background-color: var(--cds-layer-01); border-block-end: 1px solid var(--cds-border-subtle);` (reutilizando exactamente las medidas de `.silice-obra-abierta` en [marco.scss](../../frontend-desktop/src/marco/marco.scss#L177-L185)).
- **Justo debajo:** `<BarraDeEspacio etiqueta={tituloDelEspacio} pestanas={...} activa={...} />`.

### 2.2. Cabecera de la Obra (`CabeceraDeObra.tsx` + `BarraDeEspacio` en `EspacioDeObra.tsx`)
- Reutiliza íntegra [`CabeceraDeObra`](../../frontend-desktop/src/marco/CabeceraDeObra.tsx#L32-L48) con su clase `.silice-obra-abierta` ([marco.scss](../../frontend-desktop/src/marco/marco.scss#L177-L208)):
  - `<section aria-label="Obra abierta" className="silice-obra-abierta">`
  - `<p className="silice-obra-abierta__nombre">{nombre ?? \`Obra \${obraId}\`}</p>` (`body-compact-02`, `font-weight: 600`).
  - `<ul className="silice-obra-abierta__datos">` (`body-compact-01`, `color: var(--cds-text-secondary)`):
    - Si `ficha.estado === "lista"`: `Estado: <EtapaDeObra etapa={ficha.obra.etapa} texto={ficha.obra.etapa_texto} />` ([CabeceraDeObra.tsx](../../frontend-desktop/src/marco/CabeceraDeObra.tsx#L39-L43)).
    - Línea de versión (`lineaDeVersion`): `Versión: ${version ?? "sin versión guardada"}` o `Versión abierta: ${base.version} (la vigente es ${base.vigente})` ([CabeceraDeObra.tsx](../../frontend-desktop/src/marco/CabeceraDeObra.tsx#L21-L27)).
  - `<ListaDeLaCarpeta />` debajo (`helper-text-01`, `color: var(--cds-text-secondary)`): `Moneda: ${moneda} · Lista para armar: ${nombreConFecha(lista)}` ([ListaDeLaCarpeta.tsx](../../frontend-desktop/src/shell/ListaDeLaCarpeta.tsx#L38-L47)).
- **Justo debajo de `CabeceraDeObra`** (dentro de `ProveedorDeLaHoja` cuando `conHoja` es `true`, [EspacioDeObra.tsx](../../frontend-desktop/src/marco/EspacioDeObra.tsx#L162-L185)): `<BarraDeEspacio etiqueta="Secciones de la obra" pestanas={...} activa={seccion} />`.

### 2.3. Cabecera de la Cuenta (`EspacioDeCuenta.tsx`, `#/cuenta/:seccion`)
- **Elemento contenedor:** `<section aria-label="Cuenta" className="silice-cuenta-cabecera">`.
- **Medidas y tokens:** `display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.75rem 1.5rem; padding: 0.75rem 1rem; background-color: var(--cds-layer-01); border-block-end: 1px solid var(--cds-border-subtle);`.
- **Bloque izquierdo (identidad de la persona):**
  - Círculo de iniciales `.silice-cuenta__iniciales` reutilizado de [`MenuCuenta.tsx`](../../frontend-desktop/src/shell/MenuCuenta.tsx#L31-L37) y [`MenuCuenta.scss`](../../frontend-desktop/src/shell/MenuCuenta.scss#L22-L35): `inline-size: 1.75rem; block-size: 1.75rem; border-radius: 50%; background: var(--silice-acento); color: var(--silice-marco); font-weight: 600;` con clase `cds--type-label-01` (o ícono `<User size={16} />` si [`iniciales(nombre)`](../../frontend-desktop/src/shell/MenuCuenta.tsx#L15) devuelve cadena vacía).
  - Nombre de la persona en `<p className="silice-espacio-cabecera__titulo">` (`body-compact-02`, `font-weight: 600`, `color: var(--cds-text-primary)`): `{sesion.nombre}`.
  - Usuario y roles en `<p className="silice-cuenta-cabecera__detalle cds--type-body-compact-01">` (`color: var(--cds-text-secondary)`, `margin: 0`): `{sesion.login} · {rolesEnTexto(sesion.roles)}` (reutilizando [`rolesEnTexto`](../../frontend-desktop/src/paginas/administracion/logica.ts#L102-L104) o [`etiquetaDeRol`](../../frontend-desktop/src/paginas/administracion/logica.ts#L98-L100)).
- **Bloque derecho (acción de salida):**
  - Botón Carbon `<Button kind="tertiary" size="sm" onClick={alSalir}>Salir de la sesión</Button>` (con ícono `Logout` de `@carbon/icons-react`, como en [MenuCuenta.tsx](../../frontend-desktop/src/shell/MenuCuenta.tsx#L43-L46)). No usa `danger` primario para no competir con acciones destructivas ni violar la regla de un solo botón primario por pantalla ([DESIGN.md](../../frontend-desktop/DESIGN.md#L207-L208)).
- **Justo debajo:** `<BarraDeEspacio etiqueta="Secciones de la cuenta" pestanas={...} activa={seccion} />`.

### 2.4. Mapa exacto del único `<h1>` en cada espacio y ruta

En todas las pantallas el `<h1>` lleva la clase `cds--type-heading-04` (`28 px` base Carbon, escalado en `rem`).

#### A. Espacio de Obra (`#/obra/:carpeta/:obraId/:seccion`)
| Sección (`SeccionId`) | Pantalla (`pagina`) | Texto exacto del único `<h1>` | Fuente en el código |
|---|---|---|---|
| `resumen` | `obras` | `Resumen` | [paginas/obras/index.tsx:25](../../frontend-desktop/src/paginas/obras/index.tsx#L25) (`TEXTOS.titulo`) |
| `presupuesto` | `hoja` | `Presupuesto` | [paginas/hoja/index.tsx:384-386](../../frontend-desktop/src/paginas/hoja/index.tsx#L384-L386) (`TITULO`) |
| `tramos` | `tramos` | `Tramos de la vía` | [paginas/vial/Tramos.tsx:99](../../frontend-desktop/src/paginas/vial/Tramos.tsx#L99) |
| `archivos` | `archivos` | `Archivos y planos` | [paginas/archivos/index.tsx:34](../../frontend-desktop/src/paginas/archivos/index.tsx#L34) (`TEXTOS.titulo`) |
| `versiones` | `versiones` | `Versiones` | [paginas/versiones/index.tsx:45-47](../../frontend-desktop/src/paginas/versiones/index.tsx#L45-L47) (`T.titulo`) |
| `aprobaciones` | `aprobar` | `Aprobar una versión` | [paginas/aprobar/index.tsx:49](../../frontend-desktop/src/paginas/aprobar/index.tsx#L49) |
| `mercado` | `mercado` | `Estudio de mercado` | [paginas/mercado/index.tsx:50-52](../../frontend-desktop/src/paginas/mercado/index.tsx#L50-L52) |
| `control` | `control` | `Control de obra` | [paginas/control/index.tsx:87](../../frontend-desktop/src/paginas/control/index.tsx#L87) |
| `tablero` | `tablero` | `Tablero del proyecto` | [paginas/tablero/index.tsx:248](../../frontend-desktop/src/paginas/tablero/index.tsx#L248) |
| `riesgo` | `riesgo` | `Riesgo de la obra` | [paginas/riesgo/RiesgoDeLaObra.tsx:150](../../frontend-desktop/src/paginas/riesgo/RiesgoDeLaObra.tsx#L150) |

#### B. Espacio de Producción (`#/produccion/:herramienta`)
| Segmento (`id`) | Pantalla (`pagina`) | Texto exacto del único `<h1>` | Fuente en el código |
|---|---|---|---|
| `resumen` | `produccion` | `Inicio de producción` | [paginas/produccion/index.tsx:20](../../frontend-desktop/src/paginas/produccion/index.tsx#L20) |
| `existencias` | `existencias` | `Existencias de la arenera` | [paginas/existencias/index.tsx:60](../../frontend-desktop/src/paginas/existencias/index.tsx#L60) |
| `costos` | `costos` | `Costos del período` | [paginas/produccion/CostosDelPeriodo.tsx:79](../../frontend-desktop/src/paginas/produccion/CostosDelPeriodo.tsx#L79) |
| `costo-tonelada` | `costo_tonelada` | `Costo por tonelada` | [paginas/produccion/CostoPorTonelada.tsx:119-129](../../frontend-desktop/src/paginas/produccion/CostoPorTonelada.tsx#L119-L129) |
| `receta` | `receta_planta` | `Receta de la planta` | [paginas/produccion/RecetaPlanta.tsx:70](../../frontend-desktop/src/paginas/produccion/RecetaPlanta.tsx#L70) |
| `mezcla` | `producir_mezcla` | `Producir mezcla` | [paginas/produccion/ProducirMezcla.tsx:64](../../frontend-desktop/src/paginas/produccion/ProducirMezcla.tsx#L64) |

#### C. Espacio de Auditoría (`#/auditoria/:herramienta`)
| Segmento (`id`) | Pantalla (`pagina`) | Texto exacto del único `<h1>` | Fuente en el código |
|---|---|---|---|
| `subir` | `auditoria` | `Inicio de auditoría` | [paginas/auditoria/index.tsx:43](../../frontend-desktop/src/paginas/auditoria/index.tsx#L43) |
| `libros` | `libros` | `Libro de la empresa` | [paginas/libros/index.tsx:10](../../frontend-desktop/src/paginas/libros/index.tsx#L10) |
| `revisar` | `revisar` | `Revisar un paquete` | [paginas/revisar/index.tsx:15](../../frontend-desktop/src/paginas/revisar/index.tsx#L15) |
| `historial` | `historial` | `Historial de auditorías` | [paginas/historial/index.tsx:43-45](../../frontend-desktop/src/paginas/historial/index.tsx#L43-L45) |

#### D. Espacio de Precios (`#/precios/:herramienta`)
| Segmento (`id`) | Pantalla (`pagina`) | Texto exacto del único `<h1>` | Fuente en el código |
|---|---|---|---|
| `listas` | `precios_empresa` | `Precios de la empresa` | [paginas/precios_empresa/index.tsx:115](../../frontend-desktop/src/paginas/precios_empresa/index.tsx#L115) (`TITULO`) |
| `catalogo` | `catalogo` | `Catálogo de partidas e insumos` | [paginas/catalogo/index.tsx:41-43](../../frontend-desktop/src/paginas/catalogo/index.tsx#L41-L43) |
| `componer` | `componer` | `Componer una partida` | [paginas/componer/index.tsx:14](../../frontend-desktop/src/paginas/componer/index.tsx#L14) |
| `actualizar` | `actualizacion` | `Actualizar precios` | [paginas/actualizacion/index.tsx:181](../../frontend-desktop/src/paginas/actualizacion/index.tsx#L181) |
| `indices` | `indices` | `Índices del BCV` | [paginas/indices/index.tsx:142](../../frontend-desktop/src/paginas/indices/index.tsx#L142) |
| `simulador` | `simulador` | `Simulador de listas` | [paginas/simulador/index.tsx:92](../../frontend-desktop/src/paginas/simulador/index.tsx#L92) |
| `reajuste` | `reajuste` | `Reajuste de precios` | [paginas/reajuste/index.tsx:98](../../frontend-desktop/src/paginas/reajuste/index.tsx#L98) |

#### E. Espacio de la Cuenta (`#/cuenta/:seccion` — `EspacioDeCuenta.tsx`)
En `preferencias`, `cuentas`, `empresa`, `carpetas` y `sistema`, los subcomponentes de `paginas/administracion/` ([`Cuentas`](../../frontend-desktop/src/paginas/administracion/Cuentas.tsx#L295), [`Accesos`](../../frontend-desktop/src/paginas/administracion/Accesos.tsx#L34), [`Empresa`](../../frontend-desktop/src/paginas/administracion/Empresa.tsx#L144), [`EmpresasRegistradas`](../../frontend-desktop/src/paginas/administracion/EmpresasRegistradas.tsx#L193), [`CarpetasDeTrabajo`](../../frontend-desktop/src/paginas/administracion/CarpetasDeTrabajo.tsx#L36), [`Especialidades`](../../frontend-desktop/src/paginas/administracion/Especialidades.tsx#L51), [`Asistente`](../../frontend-desktop/src/paginas/administracion/Asistente.tsx#L165), [`ClavesApi`](../../frontend-desktop/src/paginas/administracion/ClavesApi.tsx#L79), [`Instalacion`](../../frontend-desktop/src/paginas/administracion/Instalacion.tsx#L122)) usan `<h2>` y `<h3>`. Por tanto, `EspacioDeCuenta.tsx` pinta `<h1 className="cds--type-heading-04">{seccionActiva.titulo}</h1>` al inicio del contenedor `<div className="silice-adm silice-pagina">` ([administracion/index.tsx](../../frontend-desktop/src/paginas/administracion/index.tsx#L68-L69)), **salvo en `ayuda`**, donde [`PaginaAcerca`](../../frontend-desktop/src/paginas/acerca/index.tsx#L58-L72) ya trae su propio `<h1 id="acerca-titulo" className="cds--type-heading-04">Acerca de Sílice</h1>` (o `EspacioDeCuenta` delega el `h1` de `ayuda` a `PaginaAcerca` para que nunca haya dos `h1`).

| Sección (`CuentaId`) | Texto exacto del único `<h1>` | Subcomponentes montados debajo (todos con `<h2>` / `<Layer>`) |
|---|---|---|
| `preferencias` | `Pantalla y tamaño de letra` | `<TamanoLetra />` ([TamanoLetra.tsx:8](../../frontend-desktop/src/comun/TamanoLetra.tsx#L8)) y datos de la cuenta |
| `cuentas` | `Cuentas y permisos` | `<Cuentas />` y `<Accesos />` ([administracion/index.tsx:33-40](../../frontend-desktop/src/paginas/administracion/index.tsx#L33-L40)) |
| `empresa` | `Empresa y tema` | `<AvisosDelTema />`, `<Empresa />` y `<EmpresasRegistradas />` ([administracion/index.tsx:23-36](../../frontend-desktop/src/paginas/administracion/index.tsx#L23-L36)) |
| `carpetas` | `Carpetas de trabajo` | `<CarpetasDeTrabajo />` ([administracion/index.tsx:47](../../frontend-desktop/src/paginas/administracion/index.tsx#L47)) |
| `sistema` | `Especialidades, IA e instalación` | `<Especialidades />` (si `activar_modulos`), `<Asistente />`, `<ClavesApi />` e `<Instalacion />` ([administracion/index.tsx:37-46](../../frontend-desktop/src/paginas/administracion/index.tsx#L37-L46)) |
| `ayuda` | `Acerca de Sílice` | `<PaginaAcerca />` ([acerca/index.tsx:50-99](../../frontend-desktop/src/paginas/acerca/index.tsx#L50-L99)) y bloque de inicio de recorridos guiados (`<h2>Recorridos guiados</h2>`, [shell/recorrido.ts:20](../../frontend-desktop/src/shell/recorrido.ts#L20)) |

---

## 3. Barra lateral plana (`src/marco/BarraLateral.tsx` y `src/marco/BarraLateral.scss`)

Conserva el contenedor `<aside className="silice-marco-lateral" aria-label="Barra lateral">` de `14.75rem` de ancho, fondo `var(--silice-lateral)` (`warm-gray-10`) y divisor derecho `1px solid var(--cds-border-subtle)` ([marco.scss:24-30](../../frontend-desktop/src/marco/marco.scss#L24-L30), [BarraLateral.scss:6-16](../../frontend-desktop/src/marco/BarraLateral.scss#L6-L16)).

### 3.1. Orden de las tres zonas
1. **Entrada superior («Vista general»):**
   - Enlace `<Link>` con clase `.silice-marco-lateral__fila.silice-marco-lateral__pendientes` ([BarraLateral.tsx:231-239](../../frontend-desktop/src/marco/BarraLateral.tsx#L231-L239)).
   - Texto visible: **`Vista general`** ([PLAN_REDISENO_F6.md:184](../../docs/planes/PLAN_REDISENO_F6.md#L184)). En F6a (antes de la Tarea 6) enlaza a `RUTA_DE_PENDIENTES` (o `RUTA_DE_INICIO` en cuanto entre la Tarea 6) y lleva a la derecha `<Pildora valor={total} />` cuando `total > 0`.
   - `aria-label`: `total > 0 ? \`Vista general, \${TEXTOS_PENDIENTES.porHacer(total)}\` : undefined` ([BarraLateral.tsx:234](../../frontend-desktop/src/marco/BarraLateral.tsx#L234)).
2. **Zona «Obras» (lista plana, sin sub-árbol):**
   - Se oculta entera si `estado === "sin_permiso"` ([BarraLateral.tsx:242](../../frontend-desktop/src/marco/BarraLateral.tsx#L242)).
   - Título `<h2 className="silice-marco-lateral__titulo">Obras</h2>` (`label-01`, `text-transform: uppercase`, `letter-spacing: 0.32px`, `color: var(--cds-text-secondary)`, [BarraLateral.scss:24-31](../../frontend-desktop/src/marco/BarraLateral.scss#L24-L31)).
   - Botón `<button type="button" className="silice-marco-boton-principal">`: `block-size: 2.5rem`, relleno `var(--cds-button-primary)` (`--silice-complementario`), texto `var(--cds-text-on-color)`, foco interno blanco `outline: 2px solid var(--cds-text-on-color); outline-offset: -4px;` ([BarraLateral.scss:184-220](../../frontend-desktop/src/marco/BarraLateral.scss#L184-L220)).
   - **Lista plana:** `<ul aria-label="Obras" className="silice-marco-lateral__arbol">` con elementos `<li><Link className="silice-marco-lateral__fila silice-marco-lateral__obra">`.
   - **Se eliminan:** el ícono `ChevronDown`/`ChevronRight`, el `<ul role="group" className="silice-marco-lateral__secciones">` y la línea guía izquierda (`.silice-marco-lateral__secciones` en [BarraLateral.scss:116-123](../../frontend-desktop/src/marco/BarraLateral.scss#L116-L123)).
   - **Destino del enlace de cada obra:** `rutaDeObra(o.carpeta, o.obra_id, seccion ?? "resumen")`. Si la persona ya está viendo una sección de obra (p. ej. `versiones`) y esa sección existe en `seccionesDeLaObra(oferta)`, el enlace apunta a esa misma sección de la otra obra; si no está en una obra, apunta a `"resumen"` ([PLAN_REDISENO_F6.md:188](../../docs/planes/PLAN_REDISENO_F6.md#L188)).
   - **Interior de la fila de obra:**
     - **Nombre largo:** `<NombreDeObra nombre={o.obra} />` ([NombreDeObra.tsx:6-16](../../frontend-desktop/src/marco/NombreDeObra.tsx#L6-L16)) con clase `.silice-marco-lateral__obra-nombre` (`-webkit-line-clamp: 2`, `overflow-wrap: anywhere`, [BarraLateral.scss:49-64](../../frontend-desktop/src/marco/BarraLateral.scss#L49-L64)). Solo añade `title={nombre}` si `scrollHeight > clientHeight` al pasar el ratón.
     - **Carpeta en homónimas:** si [`obrasConMismoNombre(visibles)`](../../frontend-desktop/src/marco/BarraLateral.tsx#L67) devuelve carpeta para esa clave, pinta debajo `<span className="silice-marco-lateral__de-carpeta">{carpeta}</span>` (`label-01`, `color: var(--cds-text-secondary)`, [BarraLateral.scss:66-70](../../frontend-desktop/src/marco/BarraLateral.scss#L66-L70)).
     - **Píldora de pendientes:** si `cuenta > 0`, pinta a la derecha `<Pildora valor={cuenta} />` ([Pildora.tsx:6-11](../../frontend-desktop/src/comun/Pildora.tsx#L6-L11), [Pildora.scss:5-21](../../frontend-desktop/src/comun/Pildora.scss#L5-L21): `min-inline-size: 1.25rem; block-size: 1.25rem; border-radius: 0.625rem; border: 1px solid var(--silice-contador-numero); background-color: var(--silice-contador-fondo); color: var(--silice-contador-numero);`).
3. **Grupo inferior «Costos y producción»:**
   - Reemplaza al bloque «Empresa» ([ZonaEmpresa.tsx](../../frontend-desktop/src/marco/ZonaEmpresa.tsx#L29-L62)) manteniendo su patrón de plegado con letra `Grande` o `Muy grande` (`useTamanoDeLetra`, `aria-expanded`, `aria-controls`, arrancando desplegado si la ruta activa pertenece a `produccion`, `auditoria` o `precios`, [DESIGN.md:147-158](../../frontend-desktop/DESIGN.md#L147-L158)).
   - Título `<h2 className="silice-marco-lateral__titulo">Costos y producción</h2>` (`aria-label="Costos y producción"` en el `<nav>`).
   - **Las 3 filas en este orden exacto** ([PLAN_REDISENO_F6.md:186](../../docs/planes/PLAN_REDISENO_F6.md#L186)), filtradas para ofrecer solo los espacios que tengan al menos una herramienta usable para la cuenta (`pestanasUsables(ESPACIOS[espacio].herramientas, ...).length > 0`):
     1. **`Auditar un presupuesto`** → enlaza a la primera herramienta usable de `auditoria` (por omisión `/auditoria/subir`).
     2. **`Precios y catálogo`** → enlaza a la primera herramienta usable de `precios` (por omisión `/precios/listas`, o `/precios/catalogo` si la cuenta no tiene `administrar_precios`).
     3. **`Costos de producción`** → enlaza a la primera herramienta usable de `produccion` (por omisión `/produccion/resumen`).

### 3.2. Estado activo, hover y foco en la barra lateral
- **Activo (`[aria-current="page"]`):**
  - En una obra: la fila de la obra lleva `aria-current="page"` cuando `clave === claveAbierta` (en cualquier sección de esa obra).
  - En `Costos y producción`: la fila del espacio lleva `aria-current="page"` cuando el primer segmento de la ruta coincide con su `EspacioId` (`/auditoria/*`, `/precios/*`, `/produccion/*`).
  - Estilo activo ([BarraLateral.scss:100-104](../../frontend-desktop/src/marco/BarraLateral.scss#L100-L104)): `background-color: var(--silice-lateral-activo); border-inline-start: 3px solid var(--silice-marco); font-weight: 600;`.
- **Hover (`:hover`):** `background-color: var(--silice-lateral-activo)` ([BarraLateral.scss:91-93](../../frontend-desktop/src/marco/BarraLateral.scss#L91-L93)).
- **Foco visible (`:focus-visible`):** `outline: 2px solid var(--cds-focus); outline-offset: -2px;` ([BarraLateral.scss:95-98](../../frontend-desktop/src/marco/BarraLateral.scss#L95-L98)).
- **Compactación con letra grande (`@include u.con-letra-grande`):** `.silice-marco-lateral__fila { min-block-size: 1.5rem; }`, `.silice-marco-lateral__obras { min-block-size: 10rem; }` ([BarraLateral.scss:225-247](../../frontend-desktop/src/marco/BarraLateral.scss#L225-L247)).

---

## 4. `BarraSuperior` nueva (`src/marco/BarraSuperior.tsx` y `src/marco/BarraSuperior.scss`)

Conserva su caja fija de `block-size: 3rem`, `padding-inline: 1rem`, `gap: 1rem`, `background-color: var(--silice-marco)`, `border-block-end: 3px solid var(--silice-acento)` y `color: var(--cds-text-inverse)` ([BarraSuperior.scss:10-20](../../frontend-desktop/src/marco/BarraSuperior.scss#L10-L20)). **Se retiran** `<Migas />` y `<TamanoLetra />` ([PLAN_REDISENO_F6.md:206-217](../../docs/planes/PLAN_REDISENO_F6.md#L206-L217)).

### 4.1. Elementos de izquierda a derecha
1. **Marca «Sílice» (o logo de la empresa) como enlace al Inicio:**
   - `<Link to={RUTA_DE_INICIO} className="silice-marco-barra__marca">` (en Tarea 5 apunta a `/inicio/general`, o a `RUTA_DE_PENDIENTES` hasta que Tarea 6 cambie la constante; el plan en [PLAN_REDISENO_F6.md:216](../../docs/planes/PLAN_REDISENO_F6.md#L216) pide enlazar a `/inicio/general`).
   - Si `logo` existe ([BarraSuperior.tsx:44-48](../../frontend-desktop/src/marco/BarraSuperior.tsx#L44-L48)): `<img src={logo} alt="Sílice — Ir al inicio" className="silice-marco-barra__logo" />` (`block-size: 1.75rem; inline-size: auto;`).
   - Sin `logo`: `<span className="silice-marco-barra__nombre">Sílice</span>` (`body-compact-01`, `font-weight: 600`, `color: var(--cds-text-inverse)`, `text-decoration: none`).
   - Hover y foco del enlace: `&:hover { background-color: var(--cds-background-inverse-hover); }`, `&:focus-visible { outline: 2px solid var(--cds-focus-inverse); outline-offset: 2px; }`.
2. **Carpeta activa (`silice-marco-barra__carpeta`):**
   - Muestra el nombre de la carpeta abierta: `<span className="silice-marco-barra__carpeta">Carpeta activa: {carpeta}</span>` (donde `{carpeta}` es el título o nombre sin `.db` que da el marco, p. ej. `tituloActual` de `useObras` o `casos?.actual.nombre.replace(/\.db$/, "") ?? "Carpeta de la empresa"`).
   - Estilo: `flex: 1 1 auto; min-inline-size: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--cds-text-inverse);` con `@include type.type-style("label-01")` ([BarraSuperior.scss:34-67](../../frontend-desktop/src/marco/BarraSuperior.scss#L34-L67)). Ocupa el espacio flexible central que antes ocupaban las migas para mantener el buscador y la cuenta anclados a la derecha.
3. **Buscador (`silice-marco-barra__buscar`):**
   - Conserva intacto el `<button type="button" className="silice-marco-barra__buscar" aria-keyshortcuts="Control+K" onClick={alAbrirBuscador}>` ([BarraSuperior.tsx:50-58](../../frontend-desktop/src/marco/BarraSuperior.tsx#L50-L58)) y sus reglas en [BarraSuperior.scss:86-123](../../frontend-desktop/src/marco/BarraSuperior.scss#L86-L123) y [BarraSuperior.scss:166-188](../../frontend-desktop/src/marco/BarraSuperior.scss#L166-L188) (`block-size: 2rem`, `flex: 0 1000 28rem`, `border: 1px solid var(--cds-border-strong-01)`, y colapso a ícono de `2rem × 2rem` bajo `@include u.por-debajo-del-umbral($escala)`).
4. **Ranura `extra` (`MarcaDemostracion` y `BotonRecorrido`):**
   - Se mantiene igual antes del botón de la persona ([Marco.tsx:333-338](../../frontend-desktop/src/marco/Marco.tsx#L333-L338)).
5. **Botón de la persona (enlace a `/cuenta/preferencias`):**
   - En el marco con rutas (`BarraSuperior.tsx`), reemplaza el desplegable por un enlace `<Link to="/cuenta/preferencias" aria-current={enCuenta ? "page" : undefined} aria-label={\`Cuenta de \${nombre}\`} title={nombre} className="cds--header__action silice-cuenta__boton">` (mientras que [`CabeceraSinMarco`](../../frontend-desktop/src/App.tsx#L25-L36) en pantallas previas al login conserva [`MenuCuenta`](../../frontend-desktop/src/shell/MenuCuenta.tsx#L15)).
   - Lleva adentro el círculo `.silice-cuenta__iniciales` (`1.75rem × 1.75rem`, `border-radius: 50%`, `background: var(--silice-acento)`, `color: var(--silice-marco)`) y `<span className="silice-cuenta__nombre cds--type-body-compact-01">{nombre}</span>` (sin `ChevronDown`).
   - Cuando la ruta activa es `/cuenta/*` (`aria-current="page"`), muestra `background-color: var(--cds-background-inverse-hover); border-block-end: 2px solid var(--silice-acento);` (igual que hacía `.silice-letra__opcion[aria-pressed="true"]` sobre el marco oscuro en [BarraSuperior.scss:142-145](../../frontend-desktop/src/marco/BarraSuperior.scss#L142-L145)).
   - Con letra `Grande` o `Muy grande`, o por debajo de `1365.98px`, `.silice-cuenta__nombre` se oculta (`display: none`, [MenuCuenta.scss:79-90](../../frontend-desktop/src/shell/MenuCuenta.scss#L79-L90)) y queda solo el círculo con el mismo `aria-label`.

---

## 5. Estados: sin permiso, módulo apagado, herramienta inexistente, carga y error

Ningún estado recurre a textos nuevos inventados ni deja una pantalla en blanco: todos reutilizan las piezas y constantes ya probadas en el repositorio.

### 5.1. Sin permiso
- **En `BarraDeEspacio` y `BarraLateral`:** [`pestanasUsables`](../../docs/planes/PLAN_REDISENO_F6.md#L116-L117) filtra con [`usable(pagina, acciones, modoEntrega, apagados)`](../../frontend-desktop/src/shell/rutas.ts#L309-L313); la pestaña sin permiso no se pinta. En `/cuenta/:seccion`, sin `administrar_cuentas` solo se ofrecen `preferencias` y `ayuda` (y `carpetas` si tiene `cambiar_caso`, [PLAN_REDISENO_F6.md:227-232](../../docs/planes/PLAN_REDISENO_F6.md#L227-L232)).
- **Si se escribe la dirección a mano en la URL (`#/produccion/costos`, `#/cuenta/cuentas`, etc.):**
  - La cabecera del espacio y `BarraDeEspacio` (con las pestañas que sí pueda usar la cuenta) se mantienen arriba.
  - En el lienzo se monta [`PantallaDeRuta`](../../frontend-desktop/src/marco/Marco.tsx#L402-L420), que pinta:
    ```tsx
    <div className="silice-pagina-aviso">
      <EstadoVacio titulo="Sin permiso" descripcion={MENSAJE_SIN_PERMISO} />
    </div>
    ```
    donde `MENSAJE_SIN_PERMISO` es `"Su cuenta no tiene permiso para esta pantalla o acción."` ([Marco.tsx:52](../../frontend-desktop/src/marco/Marco.tsx#L52)), o en una sección restringida de Cuenta sin `administrar_cuentas`, el `EstadoVacio` de [`PaginaAdministracion`](../../frontend-desktop/src/paginas/administracion/index.tsx#L71): `"Su cuenta no tiene permiso para administrar la instalación."`.
  - Medidas de `.silice-pagina-aviso`: `padding: 1rem; max-inline-size: 48rem;` ([marco.scss:100-103](../../frontend-desktop/src/marco/marco.scss#L100-L103)) y `.silice-vacio`: `padding: 2rem 1rem; max-inline-size: 40rem; gap: 0.5rem;` ([comun.scss:3-14](../../frontend-desktop/src/comun/comun.scss#L3-L14)).

### 5.2. Módulo apagado (`modulosApagados`)
- **En `BarraDeEspacio` y `BarraLateral`:** si el módulo de la pantalla (`produccion`, `vial`, `riesgo`) está en `modulosApagados`, `usable` devuelve `false` y la pestaña desaparece (si todas las herramientas de `produccion` quedan apagadas, la entrada `Costos de producción` tampoco aparece en la barra lateral). `Tablero` no tiene `modulo`, depende solo de `leer_proyecto` ([rutas.ts:103-109](../../frontend-desktop/src/shell/rutas.ts#L103-L109), [PLAN_REDISENO_F6.md:191-192](../../docs/planes/PLAN_REDISENO_F6.md#L191-L192)).
- **Si se escribe la URL a mano y la cuenta sí tendría permiso con el módulo encendido:** [`PantallaDeRuta`](../../frontend-desktop/src/marco/Marco.tsx#L405-L411) pinta:
  ```tsx
  <div className="silice-pagina-aviso">
    <EstadoVacio titulo="Apagada" descripcion={MENSAJE_APAGADA} />
  </div>
  ```
  donde `MENSAJE_APAGADA` es `"Esta función está apagada en esta instalación. Quien administra puede encenderla en Administración."` ([Marco.tsx:53](../../frontend-desktop/src/marco/Marco.tsx#L53)).

### 5.3. Herramienta o sección inexistente en la URL
- En `/<espacio>/<herramienta>`: si `<herramienta>` no existe en `ESPACIOS[espacio].herramientas`, redirige con `<Navigate to={rutaDeHerramienta(espacio, primeraHerramienta)} replace />` conservando `search` (`?…`), donde `primeraHerramienta` es la primera usable para la cuenta o, si ninguna es usable, la primera definida en `ESPACIOS[espacio].herramientas[0].id` (para que muestre el aviso de permiso/apagada en lugar de un bucle de redirección) ([PLAN_REDISENO_F6.md:152](../../docs/planes/PLAN_REDISENO_F6.md#L152)).
- En `/cuenta/<seccion>`: si `<seccion>` no es un `CuentaId` válido, redirige con `<Navigate to="/cuenta/preferencias" replace />`.

### 5.4. Carga
- Mientras carga el chunk perezoso (`Suspense`) o se fija la obra en la sesión: se pinta [`EsqueletoPagina`](../../frontend-desktop/src/comun/EsqueletoPagina.tsx#L5-L21) (`className="silice-esqueleto-pagina"`, `role="status"`, `aria-busy="true"`, `padding: 1.5rem 1rem`, `max-inline-size: 48rem`, `gap: 1rem`, [marco.scss:105-110](../../frontend-desktop/src/marco/marco.scss#L105-L110)).
- En `BarraLateral` mientras llegan las obras por primera vez: `<p className="silice-marco-lateral__aviso" role="status">Cargando obras…</p>` ([BarraLateral.tsx:214-217](../../frontend-desktop/src/marco/BarraLateral.tsx#L214-L217)).

### 5.5. Error
- **Fallo de red o API en el marco o dentro de una pantalla:** se pinta [`AvisoError`](../../frontend-desktop/src/comun/AvisoError.tsx#L14-L30) (`InlineNotification` de Carbon con `kind="error"`, `role="alert"`, `lowContrast`, mostrando el `detalle` de la API tal cual).
- **Fallo al cargar la lista de obras en `BarraLateral`:** `<div className="silice-marco-lateral__aviso" role="alert"><p>No se pudieron cargar las obras</p><button type="button" className="silice-marco-lateral__reintentar" onClick={recargar}>Reintentar</button></div>` ([BarraLateral.tsx:201-209](../../frontend-desktop/src/marco/BarraLateral.tsx#L201-L209)).
- **Avisos de obra de pantalla completa en `EspacioDeObra`:** conservan `.silice-obra-aviso` (`padding: 1.5rem 1rem; max-inline-size: 48rem; gap: 1rem;`, [EspacioDeObra.tsx:35-45](../../frontend-desktop/src/marco/EspacioDeObra.tsx#L35-L45), [marco.scss:211-222](../../frontend-desktop/src/marco/marco.scss#L211-L222)).
- **Excepción de renderizado en la pantalla:** la captura [`LimiteDeError`](../../frontend-desktop/src/marco/Marco.tsx#L360) sin tumbar la `BarraSuperior`, la `BarraLateral` ni la `BarraDeEspacio`.

---

## 6. Textos exactos de cada pestaña y cabecera (verificados contra `sinJergaInterna.test.ts`)

Todos los textos visibles en `src/marco/**` cumplen estrictamente las tres guardias de [`sinJergaInterna.test.ts`](../../frontend-desktop/src/paginas/sinJergaInterna.test.ts#L15-L105):
1. `JERGA = /\b(?:UC|RF|RNF)[-‑]\d|spec\s*§/` → **0 coincidencias**.
2. `VISIBLE_CON_TILDE = /módulo|área|página|carpeta de trabajo|streamlit/i` → **0 coincidencias** en archivos vigilados por `DEL_MARCO` ([sinJergaInterna.test.ts:48-64](../../frontend-desktop/src/paginas/sinJergaInterna.test.ts#L48-L64)).
   > **Atención obligatoria para Tarea 1 y Tarea 5:** como `DEL_MARCO` escanea automáticamente todos los `.ts`/`.tsx` de `src/marco/` y rechaza la frase `/carpeta de trabajo/i`, la pestaña `carpetas` de `SECCIONES_DE_CUENTA` en `src/marco/espacios.ts` debe titularse **`Carpetas`** (o **`Carpetas de la instalación`**), nunca `"Carpetas de trabajo"` dentro de `src/marco/`. Dentro de `src/paginas/administracion/CarpetasDeTrabajo.tsx` (que vive en `src/paginas/`, fuera de `DEL_MARCO`) el texto sí puede decir «Carpetas de trabajo» como señala [DESIGN.md:144-145](../../frontend-desktop/DESIGN.md#L144-L145).
3. `PANTALLA_RETIRADA = /página Elaborar|Siguiente paso: Elaborar|Elabore un presupuesto|«Partidas similares»|pestaña «Trazabilidad»|Hoja de la obra|barra superior \(Proyecto\)/` → **0 coincidencias**.

### 6.1. Tabla de textos exactos de `ESPACIOS` (`src/marco/espacios.ts`)

| Espacio (`EspacioId`) | Título de cabecera y `aria-label` de `BarraDeEspacio` | Segmento (`id`) | Texto exacto de la pestaña (`titulo`) | Pantalla (`pagina`) | Título del documento (`ubicar.ts`: `pagina.titulo`) |
|---|---|---|---|---|---|
| `produccion` | `Costos de producción` | `resumen` | `Resumen de arenera` | `produccion` | `Inicio de producción` |
| `produccion` | `Costos de producción` | `existencias` | `Existencias` | `existencias` | `Existencias de la arenera` |
| `produccion` | `Costos de producción` | `costos` | `Costos del período` | `costos` | `Costos del período` |
| `produccion` | `Costos de producción` | `costo-tonelada` | `Costo por tonelada` | `costo_tonelada` | `Costo por tonelada` |
| `produccion` | `Costos de producción` | `receta` | `Receta de la planta` | `receta_planta` | `Receta de la planta` |
| `produccion` | `Costos de producción` | `mezcla` | `Producir mezcla` | `producir_mezcla` | `Producir mezcla` |
| `auditoria` | `Auditar un presupuesto` | `subir` | `Subir y auditar Excel` | `auditoria` | `Inicio de auditoría` |
| `auditoria` | `Auditar un presupuesto` | `libros` | `Libro de la empresa` | `libros` | `Libro de la empresa` |
| `auditoria` | `Auditar un presupuesto` | `revisar` | `Revisar un paquete` | `revisar` | `Revisar un paquete` |
| `auditoria` | `Auditar un presupuesto` | `historial` | `Historial de auditorías` | `historial` | `Historial de auditorías` |
| `precios` | `Precios y catálogo` | `listas` | `Precios de la empresa` | `precios_empresa` | `Precios de la empresa` |
| `precios` | `Precios y catálogo` | `catalogo` | `Catálogo de partidas e insumos` | `catalogo` | `Catálogo de partidas e insumos` |
| `precios` | `Precios y catálogo` | `componer` | `Componer una partida` | `componer` | `Componer una partida` |
| `precios` | `Precios y catálogo` | `actualizar` | `Actualizar precios` | `actualizacion` | `Actualizar precios` |
| `precios` | `Precios y catálogo` | `indices` | `Índices del BCV` | `indices` | `Índices del BCV` |
| `precios` | `Precios y catálogo` | `simulador` | `Simulador de listas` | `simulador` | `Simulador de listas` |
| `precios` | `Precios y catálogo` | `reajuste` | `Reajuste de precios` | `reajuste` | `Reajuste de precios` |

### 6.2. Tabla de textos exactos de `SECCIONES_DE_OBRA` (`src/marco/secciones.ts`)
`aria-label` de `BarraDeEspacio`: **`Secciones de la obra`**.

| `SeccionId` | Texto exacto de la pestaña (`titulo`) | `pagina` | Texto exacto de `ayuda` (`secciones.ts`) |
|---|---|---|---|
| `resumen` | `Resumen` | `obras` | `La obra de un vistazo: sus cifras, su versión vigente y lo pendiente.` |
| `presupuesto` | `Presupuesto` | `hoja` | `Las partidas de la obra con sus cantidades, precios y APU.` |
| `tramos` | `Tramos` | `tramos` | `Los tramos de la vía con sus cantidades de obra.` |
| `archivos` | `Archivos y planos` | `archivos` | `Los planos y documentos de la obra.` |
| `versiones` | `Versiones` | `versiones` | `Las versiones guardadas del presupuesto y lo que cambió en cada una.` |
| `aprobaciones` | `Aprobaciones` | `aprobar` | `Las versiones que esperan dictamen y lo que se entregó al cliente.` |
| `mercado` | `Mercado` | `mercado` | `Los precios del mercado para los insumos de la obra, su histórico y las cotizaciones.` |
| `control` | `Control de obra` | `control` | `Lo avanzado en obra frente a lo planificado, con sus valuaciones.` |
| `tablero` | `Tablero` | `tablero` | `Cómo va la obra de un vistazo: costo directo, versiones y curva de avance.` |
| `riesgo` | `Riesgo` | `riesgo` | `Cuánto puede subir el presupuesto de la obra si cambian los precios.` |

### 6.3. Tabla de textos exactos de `SECCIONES_DE_CUENTA` (`src/marco/espacios.ts`)
`aria-label` de `BarraDeEspacio`: **`Secciones de la cuenta`**.

| `CuentaId` | Texto exacto de la pestaña (`titulo`) y del documento (`ubicar.ts`) | Quién la ve |
|---|---|---|
| `preferencias` | `Pantalla y tamaño de letra` | Toda cuenta con sesión activa |
| `cuentas` | `Cuentas y permisos` | Solo con acción `administrar_cuentas` |
| `empresa` | `Empresa y tema` | Solo con acción `administrar_cuentas` |
| `carpetas` | `Carpetas` *(libre de `/carpeta de trabajo/i` en `src/marco/`)* | Solo con acción `cambiar_caso` |
| `sistema` | `Especialidades, IA e instalación` | Solo con acción `administrar_cuentas` (o `activar_modulos`) |
| `ayuda` | `Ayuda y acerca de Sílice` | Toda cuenta con sesión activa |

---

> Esta adenda **manda** sobre las tablas anteriores donde difieren (§D). Revisada por Claude contra el código: los `h1`
> citados existen y las medidas salen de DESIGN.md.

## Adenda T0 (Antigravity, 2026-11-04): subvistas, Vista general y letra en la Cuenta

> **Documento que amplía y concilia:** [`2026-11-04-f6a-diseno-visual.md`](../../docs/especificaciones/2026-11-04-f6a-diseno-visual.md)
> **Contrato de referencia:** [`2026-11-04-f6a-contrato-de-rutas.md`](../../docs/especificaciones/2026-11-04-f6a-contrato-de-rutas.md) · **Enmienda:** [`2026-11-04-f6-enmienda.md`](../../docs/especificaciones/2026-11-04-f6-enmienda.md)

---

## A. Barra de Subvistas dentro de una Sección de Obra (`BarraDeEspacio` con `nivel="subvista"`)

### A.1. Mapa de secciones con subvistas y textos exactos (Contrato §2.1)

Cuando una sección de obra tiene subvistas definidas en `SUBVISTAS[seccion]`, `BarraDeEspacio` recibe `nivel="subvista"` y `etiqueta="Vistas de {tituloSeccion}"`:

| Sección (`SeccionId`) | `aria-label` de la barra (`nivel="subvista"`) | Subvistas (`id` → **Texto de la pestaña** → `pagina` en [`rutas.ts`](../../frontend-desktop/src/shell/rutas.ts)) | Texto exacto del único `<h1>` montado en el lienzo |
|---|---|---|---|
| `resumen` | `Vistas de Resumen` | 1. *(raíz)* → **`Resumen`** → `obras`<br>2. `tablero` → **`Tablero`** → `tablero` | `Resumen` ([`obras/index.tsx:25`](../../frontend-desktop/src/paginas/obras/index.tsx#L25)) \| `Tablero del proyecto` ([`tablero/index.tsx:248`](../../frontend-desktop/src/paginas/tablero/index.tsx#L248)) |
| `presupuesto` | `Vistas de Presupuesto` | 1. *(raíz)* → **`Partidas`** → `hoja`<br>2. `componer` → **`Componer`** → `componer` | `Presupuesto` ([`hoja/index.tsx:384`](../../frontend-desktop/src/paginas/hoja/index.tsx#L384)) \| `Componer una partida` ([`componer/index.tsx:14`](../../frontend-desktop/src/paginas/componer/index.tsx#L14)) |
| `aprobaciones` | `Vistas de Aprobaciones` | 1. *(raíz)* → **`Aprobar`** → `aprobar`<br>2. `revisar` → **`Revisar un paquete`** → `revisar`<br>3. `entregar` → **`Entregar`** → `entregar` | `Aprobar una versión` \| `Revisar un paquete` \| `Entregar paquete` |
| `mercado` | `Vistas de Mercado` | 1. *(raíz)* → **`Estudio`** → `mercado`<br>2. `actualizar` → **`Actualizar precios`** → `actualizacion` | `Estudio de mercado` \| `Actualizar precios` |
| `control` | `Vistas de Control de obra` | 1. *(raíz)* → **`Control`** → `control`<br>2. `reajuste` → **`Reajuste`** → `reajuste`<br>3. `escenarios` → **`Escenarios`** → `escenarios` | `Control de obra` \| `Reajuste de precios` \| `Escenarios de sensibilidad` |

- **Regla de omisión automática cuando hay $\le 1$ subvista usable:** Si tras filtrar con [`usable(pagina, acciones, modoEntrega, apagados)`](../../frontend-desktop/src/shell/rutas.ts#L309-L313) queda **una sola subvista usable** (por ejemplo, una cuenta con `leer_proyecto` pero sin `editar_hoja` en `Presupuesto` solo puede ver `Partidas`, nunca `Componer`), `BarraDeEspacio` con `nivel="subvista"` **devuelve `null` y no se pinta**.
- **Regla de sección cuya raíz no es usable pero una subvista sí lo es (Contrato §2.1):** En `Aprobaciones`, una cuenta con `revisar_paquete` pero sin `aprobar_version` entra directamente a `/obra/:c/:o/aprobaciones/revisar`; si solo `revisar` es usable, ve únicamente la pantalla `Revisar un paquete` bajo la pestaña activa `Aprobaciones` de la obra.

### A.2. Dónde va y cómo evita apilar tres barras sobre la Hoja (Univer) a `1366×768`

En [`PaginaHoja`](../../frontend-desktop/src/paginas/hoja/index.tsx#L334-L368) (`Presupuesto`) y en `Estudio de mercado` ya existe una barra de `<Tabs>` Carbon (`role="tablist"`, con 6 o 7 pestañas en Presupuesto y 4 en Mercado). Si la barra de subvistas se colocara como una segunda franja de ancho completo debajo de la barra de la obra, quedarían **tres barras horizontales apiladas** (`Barra de la obra` + `Barra de subvistas` + `TabList de Carbon`), restando `~40–56 px` adicionales de alto útil a la tabla/lienzo de la Hoja.

**Solución arquitectónica y visual (coste vertical = `0 px` adicionales en `1366×768`):**
1. La barra de la obra (`nivel="espacio"`, `etiqueta="Secciones de la obra"`) es la **única** barra de ancho completo bajo [`CabeceraDeObra`](../../frontend-desktop/src/marco/CabeceraDeObra.tsx) sobre `var(--cds-layer-01)`.
2. La barra de subvistas (`<BarraDeEspacio nivel="subvista" ... />`, clase `.silice-barra-espacio--subvista`) se monta **dentro de la franja superior del lienzo de la sección**, alineada en la misma fila horizontal (o inmediatamente al costado derecho) del encabezado de la sección mediante una envoltura `.silice-obra-cuerpo` en [`EspacioDeObra.tsx`](../../frontend-desktop/src/marco/EspacioDeObra.tsx):
   - En lugar de empujar todo el documento hacia abajo con una barra de `100%` de ancho y fondo gris, `.silice-barra-espacio--subvista` es un **conmutador segmentado compacto de navegación** (`inline-flex`, `align-self: flex-start`) situado en la cabecera del lienzo (`padding: 0.75rem 1rem 0; background-color: var(--cds-background);`).
   - En `Presupuesto` ([`hoja.scss:3-8`](../../frontend-desktop/src/paginas/hoja/hoja.scss#L3-L8)), cuando `.silice-barra-espacio--subvista` precede a `.silice-pagina`, la regla `.silice-barra-espacio--subvista + .silice-pagina` reduce su `padding-block-start` de `1.5rem` a `0.5rem`, absorbiendo la altura del conmutador dentro del propio margen superior que ya tenía la página (`1.5rem` = `28 px` en Normal, `42 px` en Muy grande). **El alto neto robado a la Hoja (Univer) respecto a una sección sin subvistas es exactamente `0rem` (`0 px`) cuando la barra cabe en 1 línea.**

### A.3. Diferenciación visual y semántica entre los 3 niveles de navegación

| Atributo | 1. Barra de la Obra (`BarraDeEspacio` `nivel="espacio"`) | 2. Barra de Subvistas (`BarraDeEspacio` `nivel="subvista"`) | 3. Pestañas Internas Carbon (`<Tabs><TabList>` en Presupuesto / Mercado) |
|---|---|---|---|
| **Semántica DOM** | `<nav aria-label="Secciones de la obra">` con `<Link aria-current="page">` | `<nav aria-label="Vistas de {seccion}">` con `<Link aria-current="page">` | `<div role="tablist" aria-label="Secciones del presupuesto">` con `<button role="tab" aria-selected>` |
| **Ubicación** | De borde a borde bajo `.silice-obra-abierta` | Cabecera del lienzo (`margin: 0.75rem 1rem 0; width: fit-content; max-inline-size: calc(100% - 2rem)`) | Cuerpo inferior de la página (debajo de `FranjaDelPresupuesto` y `EstadoDelBorrador`) |
| **Superficie de fondo** | Banda continua `var(--cds-layer-01)` (`#f4f4f4`) con divisor inferior `1px solid var(--cds-border-subtle)` | Conmutador enmarcado `border: 1px solid var(--cds-border-subtle)` sobre el lienzo blanco `var(--cds-background)` (`#ffffff`) | Línea Carbon `TabList` sobre `var(--cds-background)` |
| **Altura por ítem** | `min-block-size: 2.5rem` (`2rem` en `@include u.con-letra-grande`) | `min-block-size: 1.75rem` (`1.625rem` en `@include u.con-letra-grande`) | `2.5rem` nativo de `@carbon/react` |
| **Tipografía** | `body-compact-01` (`0.875rem`), `padding: 0.5rem 0.75rem` | `label-01` (`0.75rem`), `padding: 0.25rem 0.625rem`, `white-space: nowrap` | `body-compact-01` nativo de Carbon |
| **Separación entre ítems** | Sin borde vertical entre pestañas | Divisor vertical `border-inline-end: 1px solid var(--cds-border-subtle)` (`.silice-barra-espacio__pestana:last-child { border-inline-end: 0; }`) | `gap` / divisor de `cds--tabs` |
| **Estado inactivo** | `background: transparent; color: var(--cds-text-secondary); border-block-end: 3px solid transparent;` | `background-color: var(--cds-layer-01); color: var(--cds-text-secondary); border-block-start: 2px solid transparent;` | `color: var(--cds-text-secondary); border-block-end: 2px solid var(--cds-border-subtle);` |
| **Estado activo** | `background-color: var(--cds-background); color: var(--cds-text-primary); font-weight: 600; border-block-end: 3px solid var(--silice-complementario);` | `background-color: var(--cds-layer-selected-01); color: var(--cds-text-primary); font-weight: 600; border-block-start: 2px solid var(--silice-complementario);` | `color: var(--cds-text-primary); font-weight: 600; border-block-end: 2px solid var(--cds-border-interactive);` |

### A.4. Comportamiento a `1056 px` con letra `Muy grande` y presupuesto vertical a `1366×768`

1. **A `1056 px` con letra `Muy grande` (`1 rem = 28 px`, `<main>` = `643 px` libres):**
   - El caso más largo de subvistas es `Aprobaciones` (`Aprobar` · `Revisar un paquete` · `Entregar`, suma `~460 px` en `label-01` a `21 px` de fuente efectiva): **cabe en 1 sola fila** dentro de los `643 px` de `<main>`.
   - Si en un contenedor aún más estrecho o con zoom del navegador las opciones superan el ancho, `.silice-barra-espacio--subvista` tiene `display: inline-flex; flex-wrap: wrap;` y parte limpiamente a una segunda fila manteniendo su `border-block-start: 2px solid var(--silice-complementario)` en la activa, con **0 px de desbordamiento horizontal**.
2. **Presupuesto de alto en `1366×768` para la Hoja (`Presupuesto` → `Partidas`):**
   - **En letra `Normal` (`1 rem = 18.67 px`):**
     - `BarraSuperior`: `3rem` (`56 px`).
     - `CabeceraDeObra` compacta + `BarraDeEspacio` (`nivel="espacio"`, 9 secciones en 1 fila a `1366 px` porque `<main>` tiene `1366 - 275 = 1091 px`): `~62 px` + `47 px` = `109 px`.
     - `.silice-barra-espacio--subvista` (`Partidas | Componer`, `1.75rem` = `33 px`) + `.silice-pagina` con `padding-block-start: 0.5rem` (`9 px`): `42 px` (solo `14 px` más que el `padding-top: 1.5rem` = `28 px` que ya tenía `.silice-hoja`).
     - Quedan **`561 px` verticales libres** bajo la cabecera de navegación para el título, el estado del borrador y las partidas de la Hoja.
   - **En letra `Muy grande` (`1 rem = 28 px`, `<main>` = `953 px` libres a `1366×768`):**
     - Gracias a `@include u.con-letra-grande`, la barra de la obra usa `min-block-size: 2rem` (`56 px`) y la de subvistas `min-block-size: 1.625rem` (`45.5 px`), absorbiendo `1rem` (`28 px`) del `padding-block-start` de `.silice-hoja`. El contenedor general `.silice-contenido` desplaza verticalmente el documento completo sin recortar nunca la tabla de la Hoja.

---

## B. Vista General (`#/inicio/general`) y Bandeja (`#/inicio/pendientes`)

### B.1. Cabecera y barra del espacio Inicio (`EspacioDeInicio.tsx`)
- **Cabecera del espacio (`.silice-espacio-cabecera`):** `<section aria-label="Vista general" className="silice-espacio-cabecera"><p className="silice-espacio-cabecera__titulo">Vista general</p></section>` (sin `<h1>`, `body-compact-02`, `font-weight: 600`, `background-color: var(--cds-layer-01)`).
- **Barra del espacio (`BarraDeEspacio` con `nivel="espacio"` y `etiqueta="Inicio"`):**
  1. **`Vista general`** → `/inicio/general` (monta `Panorama` de `paginas/inicio/index.tsx`, cuyo único `<h1>` es `<h1 className="cds--type-heading-04" tabIndex={-1}>Vista general</h1>`).
  2. **`Pendientes`** → `/inicio/pendientes` (monta [`Bandeja`](../../frontend-desktop/src/paginas/pendientes/Bandeja.tsx), cuyo único `<h1>` es `<h1 className="cds--type-heading-04">Pendientes</h1>`).

### B.2. Orden obligatorio de los 4 bloques en `#/inicio/general`

Contenedor principal: `<div className="silice-pagina silice-inicio">`, con bloques `<section className="silice-inicio__bloque">` separados por `border-block-end: 1px solid var(--silice-divisor)` ([`inicio.scss:9-18`](../../frontend-desktop/src/paginas/inicio/inicio.scss#L9-L18)). Cada bloque maneja su propio estado de carga/error sin tumbar a los demás.

#### Bloque 1 (Arriba de todo): Lo que bloquea (`aria-labelledby="inicio-bloquea"`)
- **Título:** `<h2 id="inicio-bloquea" className="cds--type-heading-compact-02">Lo que requiere atención</h2>`.
- **Fuente de datos:** `usePendientes()` (que ya viene ordenado por la API con `urgencia === "bloquea"` primero, [`obras.py:352-355`](../../api/rutas/obras.py#L352-L355)).
- **Si hay pendientes (`pendientes.length > 0`):**
  - Pinta el resumen de urgencias (`TEXTOS.resumen(bloquea, aviso)` de [`pendientes/textos.ts:12-18`](../../frontend-desktop/src/paginas/pendientes/textos.ts#L12-L18), p. ej. `«2 bloquean · 1 aviso»`) en `label-01`.
  - Lista compacta (`.silice-inicio__urgentes`, máximo los primeros 5 ítems priorizando `urgencia === "bloquea"`): cada fila muestra el ícono y etiqueta de urgencia (`WarningFilled` en `--silice-sev-error` para `Bloquea`; `WarningAltFilled` en `--silice-sev-advertencia` para `Aviso`, nunca solo color), el nombre de la obra (con carpeta si es homónima), el texto del pendiente y a la derecha el enlace `<Link className="cds--link" to={rutaCanonica(p.accion.pagina, { carpeta: p.carpeta, obraId: p.obra_id })}>{p.accion.texto}</Link>` (si `usable` lo permite para la cuenta).
  - Pie del bloque: `<Link className="cds--link" to="/inicio/pendientes">Ir a la bandeja de pendientes ({formatoEsVe(String(total))})</Link>`.
- **Si `pendientes.length === 0`:**
  - Pinta una sola línea tranquila: `<p className="silice-inicio__nota cds--type-body-compact-01">No tiene pendientes por hacer.</p>`.

#### Bloque 2: Cartera de obras por moneda (`aria-labelledby="inicio-cartera"`)
- **Título:** `<h2 id="inicio-cartera" className="cds--type-heading-compact-02">Cartera por moneda</h2>`.
- **Fuente de datos:** `GET /v1/obras/resumen/todas` (Tarea T7).
- **Aviso de carpetas ilegibles:** Si `carpetas_omitidas.length > 0`, muestra `<InlineNotification kind="warning" lowContrast hideCloseButton title={TEXTOS.omitidas(carpetas_omitidas.length)} />`.
- **Regla inquebrantable de separación monetaria:** **Jamás se suman ni promedian `Bs` con `USD`.** Cada entrada de `por_moneda` (`moneda: "Bs" | "USD"`) se presenta en su propio bloque `.silice-cartera-moneda`.
- **Estructura visual de cada bloque `.silice-cartera-moneda` (reutilizando las clases de [`indicadores.scss`](../../frontend-desktop/src/indicadores/indicadores.scss#L19-L66)):**
  - Contenedor de rejilla `.silice-cartera-rejilla`: `display: grid; grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr)); gap: 1rem;`.
  - Cada moneda es un `<section className="silice-cartera-moneda" aria-label={`Cartera en ${fila.moneda}`}>` con `background: var(--cds-layer-01); border: 1px solid var(--silice-divisor);`:
    - **Cabecera de moneda (`.silice-cartera-moneda__titulo`):** `padding: 0.5rem 0.75rem; border-block-end: 1px solid var(--silice-divisor); font-weight: 600;` (`body-compact-01`): **`Obras en Bs`** o **`Obras en USD`**.
    - **Franja interna de 3 celdas tipo Fiori (`.franja-indicadores__lista`):**
      1. **Total presupuestado:** etiqueta `Total vigente` (`label-01`, `--silice-texto-secundario`) y cifra `<span className="fiori-kpi__actual cds--type-heading-03 silice-cifra">{formatoEsVe(fila.total)} {fila.moneda}</span>` (`tabular-nums`, sin redondear ni recalcular en el cliente).
      2. **Obras:** etiqueta `Obras` (`label-01`) y cifra `<span className="fiori-kpi__actual cds--type-heading-03 silice-cifra">{formatoEsVe(String(fila.obras))}</span>`.
      3. **En ejecución:** etiqueta `En ejecución` (`label-01`) y cifra `<span className="fiori-kpi__actual cds--type-heading-03 silice-cifra">{formatoEsVe(String(fila.en_ejecucion))}</span>`.
- **Los 3 casos de cardinalidad de monedas:**
  1. **Dos monedas (`por_moneda` trae `Bs` y `USD`):** se pintan las dos tarjetas `.silice-cartera-moneda` lado a lado en `.silice-cartera-rejilla` (a `1056 px` con letra `Muy grande`, `minmax(20rem, 1fr)` las apila automáticamente en 1 columna sin scroll horizontal).
  2. **Una sola moneda (`por_moneda` trae solo `Bs` o solo `USD`):** se pinta **únicamente** la tarjeta de esa moneda. No se muestra ninguna tarjeta vacía ni en `0,00` para la otra moneda.
  3. **Sin obras (`obras.length === 0` y `por_moneda.length === 0`):** los bloques 2 y 3 se unifican en un único `<EstadoVacio>`:
     - Si la cuenta puede crear obras (`acciones.includes("editar_hoja")`): `titulo="Aún no hay obras"`, `descripcion="Cree la primera obra para armar su presupuesto y seguir su avance."` con `<Button kind="tertiary" size="sm" onClick={abrirNuevaObra}>Nueva obra</Button>` (terciario si en el Bloque 1 hubiera un botón primario, o primario si no hay otro botón primario en pantalla).
     - Si la cuenta solo revisa (`!acciones.includes("editar_hoja")`): `titulo="No hay obras en esta carpeta"`, `descripcion="Cuando haya una obra registrada en las carpetas a las que tiene acceso, aparecerá aquí."`.

#### Bloque 3: Avance de las obras frente al plan (`aria-labelledby="inicio-obras"`)
- **Título:** `<h2 id="inicio-obras" className="cds--type-heading-compact-02">Obras y avance contra el plan</h2>`.
- **Tabla Carbon `size="sm"`** dentro de `<div className="silice-tabla">`:
  - Columnas: **`Obra`** | **`Estado`** | **`Total`** (`.silice-cifra`) | **`Avance ejecutado vs. plan`**.
  - **Celda `Obra`:** `<Link className="cds--link" to={rutaCanonica("obras", { carpeta: o.carpeta, obraId: o.obra_id })}>{o.nombre}</Link>` (más `· {carpeta}` si es homónima).
  - **Celda `Estado`:** `<EtapaDeObra etapa={o.etapa} texto={ETAPA_TEXTO[o.etapa]} />` ([`DESIGN.md:166-173`](../../frontend-desktop/DESIGN.md#L166-L173)).
  - **Celda `Total`:** `{o.total !== null ? `${formatoEsVe(o.total)} ${o.moneda}` : "Sin versión"}` (`tabular-nums`).
  - **Celda `Avance ejecutado vs. plan` (IBCS):**
    - Si `o.avance_real === null` o `o.avance_plan === null`: muestra `<span className="cds--type-body-compact-01" style={{ color: "var(--silice-texto-secundario)" }}>Sin avance</span>` ([`PLAN_REDISENO_F6.md:242`](../../docs/planes/PLAN_REDISENO_F6.md#L242)).
    - Si existen ambos: muestra `Real {formatoEsVe(o.avance_real)} % · Plan {formatoEsVe(o.avance_plan)} %` acompañado de la micro-barra IBCS reutilizada de [`.fiori-kpi__barra`](../../frontend-desktop/src/indicadores/indicadores.scss#L180-L204) (`block-size: 6px`, barra superior `.fiori-kpi__barra-real` con relleno sólido `var(--silice-texto)` y barra inferior `.fiori-kpi__barra-meta` con contorno `1px solid var(--silice-texto)` y fondo transparente).

#### Bloque 4: Últimas auditorías y Arenera
- `<section className="silice-inicio__bloque" aria-labelledby="inicio-auditorias">` con `<h2 id="inicio-auditorias" className="cds--type-heading-compact-02">Últimas auditorías</h2>`, [`<UltimasAuditorias carga={...} />`](../../frontend-desktop/src/paginas/inicio/UltimasAuditorias.tsx#L28) y enlace `<Link className="cds--link" to={rutaCanonica("auditoria")}>Ir a Auditoría</Link>`.
- Si `acciones.includes("operar_arenera") && !modulosApagados.includes("produccion")`: monta [`<PanelArenera carga={...} />`](../../frontend-desktop/src/paginas/inicio/PanelArenera.tsx#L111), cuyos enlaces internos usan `rutaCanonica("existencias")` (`/produccion/existencias`).

---

## C. Tamaño de Letra Solo en `Cuenta › Pantalla y tamaño de letra` (`#/cuenta/preferencias`)

1. **Retiro de `BarraSuperior.tsx`:**
   - Se elimina `<TamanoLetra />` de [`BarraSuperior.tsx`](../../frontend-desktop/src/marco/BarraSuperior.tsx) y sus reglas asociadas en `BarraSuperior.scss`.
   - En las pantallas **sin marco** previas a iniciar sesión (`CabeceraSinMarco` en `App.tsx`: Bienvenida, Entrar, Recuperar acceso), `<TamanoLetra />` **se mantiene** exactamente como hoy, usando `var(--silice-complementario)` para la raya activa sobre fondo claro ([`DESIGN.md:93-96`](../../frontend-desktop/DESIGN.md#L93-L96), [`2026-11-04-f6-enmienda.md:14`](../../docs/especificaciones/2026-11-04-f6-enmienda.md#L14)).
2. **Diseño de `#/cuenta/preferencias` en `EspacioDeCuenta.tsx`:**
   - **Acceso en 1 clic:** El botón de la persona en la esquina derecha de `BarraSuperior` es un `<Link to="/cuenta/preferencias">`.
   - **Único `<h1>` de la pantalla:** `<h1 className="cds--type-heading-04" tabIndex={-1}>Pantalla y tamaño de letra</h1>`.
   - **Contenido dentro de `<Layer>` (`.silice-cuenta-preferencias`):**
     - **Sub-bloque 1 — Tamaño de letra (`<section aria-labelledby="pref-letra-titulo">`):**
       - `<h2 id="pref-letra-titulo" className="cds--type-heading-compact-02">Tamaño de letra</h2>`
       - `<p className="cds--type-body-compact-01">Ajusta el tamaño de todos los textos, tablas y hojas en este navegador (Normal 100 %, Grande 125 %, Muy grande 150 %).</p>`
       - Reutiliza el componente existente [`<TamanoLetra />`](../../frontend-desktop/src/comun/TamanoLetra.tsx#L8-L34) (`role="group" aria-label="Tamaño de letra"`, tres botones con `aria-pressed`, estilos de [`.silice-letra` en `comun.scss:140-188`](../../frontend-desktop/src/comun/comun.scss#L140-L188) con `border: 1px solid var(--silice-divisor)` sobre `var(--cds-layer-01)` y raya inferior activa `2px solid var(--silice-complementario)`).
       - **Muestra de lectura en vivo (`.silice-cuenta-preferencias__muestra`):** caja con `padding: 0.75rem 1rem; background: var(--cds-layer-01); border-inline-start: 3px solid var(--silice-divisor);` que muestra una línea en `body-compact-01` y una cifra en `IBM Plex Mono` (`tabular-nums`): `Partida C-001 · Vaciado de concreto f'c 210 kgf/cm² — 242,64 USD/m³`, para comprobar al instante la legibilidad por presbicia sin salir de la pantalla.
     - **Sub-bloque 2 — Datos de la sesión activa (`<section aria-labelledby="pref-sesion-titulo">`):**
       - `<h2 id="pref-sesion-titulo" className="cds--type-heading-compact-02">Datos de la cuenta</h2>`
       - Lista `<dl>` con `Nombre` (`sesion.nombre`), `Usuario` (`sesion.login`) y `Rol` (`rolesEnTexto(sesion.roles)`).

---

## D. Conciliación de Tablas de [`2026-11-04-f6a-diseno-visual.md`](../../docs/especificaciones/2026-11-04-f6a-diseno-visual.md) con el Contrato v2

Se enmiendan las tablas §1.3, §2.4 y §6.1–§6.3 de [`2026-11-04-f6a-diseno-visual.md`](../../docs/especificaciones/2026-11-04-f6a-diseno-visual.md) para que coincidan exactamente con las decisiones de Eugenio y el [Contrato de Rutas v2](../../docs/especificaciones/2026-11-04-f6a-contrato-de-rutas.md):

1. **En Obra (9 secciones en la barra principal + 7 subvistas):**
   - `Tablero` sale de la barra principal de la obra y pasa a subvista de `Resumen` (`/obra/:c/:o/resumen/tablero`). La barra de la obra queda con **9 secciones** (`Resumen`, `Presupuesto`, `Tramos`, `Archivos y planos`, `Versiones`, `Aprobaciones`, `Mercado`, `Control de obra`, `Riesgo`).
2. **En Auditoría (3 herramientas en lugar de 4):**
   - `revisar` (`Revisar un paquete`) sale de `ESPACIOS.auditoria` y pasa a subvista de `Aprobaciones` en la obra (`/obra/:c/:o/aprobaciones/revisar`). `ESPACIOS.auditoria` queda con: `subir` (`Subir y auditar Excel`), `libros` (`Libro de la empresa`) e `historial` (`Historial de auditorías`).
3. **En Precios y catálogo (4 herramientas en lugar de 7):**
   - `componer`, `actualizar` y `reajuste` salen de `ESPACIOS.precios` y pasan a subvistas de `Presupuesto`, `Mercado` y `Control de obra` respectivamente. `ESPACIOS.precios` queda con: `listas` (`Precios de la empresa`), `catalogo` (`Catálogo de partidas e insumos`), `indices` (`Índices del BCV`) y `simulador` (`Simulador de listas`).
4. **En Cuenta (§5.1 y §6.3):**
   - `carpetas` (`Carpetas`) exige `administrar_cuentas` **y** `cambiar_caso`.
   - `sistema` (`Especialidades, IA e instalación`) exige `administrar_cuentas` (y dentro de ella, `<Especialidades />` exige además `activar_modulos`).

---
